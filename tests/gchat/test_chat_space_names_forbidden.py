"""Unit tests for how space naming treats a 403 from spaces.members.list."""

import json
from unittest.mock import Mock

import httplib2
import pytest
from googleapiclient.errors import HttpError

from gchat import chat_helpers
from gchat.chat_helpers import _name_spaces

DM_A = {"name": "spaces/A", "spaceType": "DIRECT_MESSAGE"}
DM_B = {"name": "spaces/B", "spaceType": "DIRECT_MESSAGE"}
B_MEMBERSHIPS = {
    "memberships": [
        {"member": {"type": "HUMAN", "name": "users/111"}},
        {"member": {"type": "HUMAN", "name": "users/222"}},
    ]
}
RESOURCE_FORBIDDEN = {
    "error": {
        "code": 403,
        "message": (
            "Permission denied to perform the requested action on the "
            "specified resource, or the resource doesn't exist."
        ),
        "status": "PERMISSION_DENIED",
    }
}
SCOPE_FORBIDDEN = {
    "error": {
        "code": 403,
        "message": "Request had insufficient authentication scopes.",
        "status": "PERMISSION_DENIED",
        "details": [
            {
                "@type": "type.googleapis.com/google.rpc.ErrorInfo",
                "reason": "ACCESS_TOKEN_SCOPE_INSUFFICIENT",
                "domain": "googleapis.com",
            }
        ],
    }
}
RATE_LIMITED = {
    "error": {
        "code": 429,
        "message": "Quota exceeded.",
        "status": "RESOURCE_EXHAUSTED",
    }
}
RESOURCE_FORBIDDEN_WITH_DETAILS = {
    "error": {
        "code": 403,
        "message": "Permission denied on resource spaces/A.",
        "status": "PERMISSION_DENIED",
        "details": [
            {
                "@type": "type.googleapis.com/google.rpc.ErrorInfo",
                "reason": "IAM_PERMISSION_DENIED",
                "domain": "iam.googleapis.com",
            },
            {
                "@type": "type.googleapis.com/google.rpc.LocalizedMessage",
                "locale": "en-US",
                "message": "You do not have permission to access this space.",
            },
        ],
    }
}


@pytest.fixture(autouse=True)
def _clear_name_cache():
    chat_helpers._sender_name_cache.clear()
    yield
    chat_helpers._sender_name_cache.clear()


def _http_error(body):
    status = body["error"]["code"]
    return HttpError(httplib2.Response({"status": status}), json.dumps(body).encode())


def _request(result=None, error=None):
    request = Mock()
    if error is not None:
        request.execute.side_effect = error
    else:
        request.execute.return_value = result
    return request


def _people_service():
    people_service = Mock()
    people_service.people().get.side_effect = lambda **kw: _request(
        {"resourceName": "people/111"}
    )
    people_service.people().getBatchGet.side_effect = lambda **kw: _request(
        {
            "responses": [
                {
                    "requestedResourceName": "people/222",
                    "person": {"names": [{"displayName": "Other Person"}]},
                }
            ]
        }
    )
    return people_service


def _chat_service(space_a_error):
    chat_service = Mock()

    def list_members(parent, **kw):
        if parent == "spaces/A":
            return _request(error=space_a_error)
        return _request(B_MEMBERSHIPS)

    chat_service.spaces().members().list.side_effect = list_members
    return chat_service


@pytest.mark.asyncio
async def test_name_spaces_keeps_naming_after_a_per_space_403():
    chat_service = _chat_service(_http_error(RESOURCE_FORBIDDEN))

    labels = await _name_spaces(chat_service, _people_service(), [DM_A, DM_B])

    assert labels["spaces/A"] == "Direct message"
    assert labels["spaces/B"] == "Other Person"


@pytest.mark.asyncio
async def test_name_spaces_stops_after_a_scope_403():
    chat_service = _chat_service(_http_error(SCOPE_FORBIDDEN))

    labels = await _name_spaces(chat_service, _people_service(), [DM_A, DM_B])

    assert labels == {"spaces/A": "Direct message", "spaces/B": "Direct message"}
    assert chat_service.spaces().members().list.call_count == 1


@pytest.mark.asyncio
async def test_name_spaces_stops_after_a_429():
    chat_service = _chat_service(_http_error(RATE_LIMITED))

    labels = await _name_spaces(chat_service, _people_service(), [DM_A, DM_B])

    assert labels == {"spaces/A": "Direct message", "spaces/B": "Direct message"}
    assert chat_service.spaces().members().list.call_count == 1


@pytest.mark.asyncio
async def test_name_spaces_keeps_naming_after_a_403_with_another_error_reason():
    chat_service = _chat_service(_http_error(RESOURCE_FORBIDDEN_WITH_DETAILS))

    labels = await _name_spaces(chat_service, _people_service(), [DM_A, DM_B])

    assert labels["spaces/A"] == "Direct message"
    assert labels["spaces/B"] == "Other Person"
    assert chat_service.spaces().members().list.call_count == 2
