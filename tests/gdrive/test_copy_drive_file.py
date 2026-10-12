"""Tests for copy_drive_file copy_comments passthrough (issue #1206)."""
import os
import sys
from unittest.mock import AsyncMock, Mock, patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from gdrive.drive_tools import copy_drive_file


def _unwrap(tool):
    fn = tool.fn if hasattr(tool, "fn") else tool
    while hasattr(fn, "__wrapped__"):
        fn = fn.__wrapped__
    return fn


def _service():
    service = Mock()
    service.files().copy().execute = Mock(
        return_value={
            "id": "copy-1",
            "name": "Copy of Doc",
            "mimeType": "application/vnd.google-apps.document",
            "webViewLink": "https://docs.google.com/document/d/copy-1/edit",
        }
    )
    return service


def _patch_resolvers():
    return (
        patch(
            "gdrive.drive_tools.resolve_drive_item",
            new=AsyncMock(return_value=("file-1", {"name": "Doc"})),
        ),
        patch(
            "gdrive.drive_tools.resolve_folder_id",
            new=AsyncMock(return_value="root"),
        ),
    )


@pytest.mark.asyncio
async def test_copy_comments_true_reaches_files_copy():
    raw = _unwrap(copy_drive_file)
    service = _service()
    item_patch, folder_patch = _patch_resolvers()
    with item_patch, folder_patch:
        await raw(
            service,
            user_google_email="you@gmail.com",
            file_id="file-1",
            copy_comments=True,
        )
    assert service.files().copy.call_args.kwargs["copyComments"] is True


@pytest.mark.asyncio
async def test_copy_comments_defaults_to_false():
    raw = _unwrap(copy_drive_file)
    service = _service()
    item_patch, folder_patch = _patch_resolvers()
    with item_patch, folder_patch:
        await raw(
            service,
            user_google_email="you@gmail.com",
            file_id="file-1",
        )
    assert service.files().copy.call_args.kwargs["copyComments"] is False
