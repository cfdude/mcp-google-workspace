"""Tool risk annotations served to MCP hosts (#1248).

Sending mail is destructive; downloading a Drive file to local disk is not
read-only. Hosts that gate on these hints must see accurate values.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest

from core.server import server

import gmail.gmail_tools  # noqa: F401 -- registration side effect
import gdrive.drive_tools  # noqa: F401 -- registration side effect


@pytest.mark.asyncio
async def test_send_gmail_message_is_destructive():
    tool = await server.get_tool("send_gmail_message")
    assert tool.annotations.model_dump()["destructive_hint"] is True


@pytest.mark.asyncio
async def test_drive_download_url_is_not_read_only():
    tool = await server.get_tool("get_drive_file_download_url")
    assert tool.annotations.model_dump()["read_only_hint"] is False
