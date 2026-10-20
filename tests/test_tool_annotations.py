"""Risk annotations advertised for tools with side effects (#1248)."""

import pytest

import gdrive.drive_tools  # noqa: F401
import gmail.gmail_tools  # noqa: F401
from core.server import server


@pytest.mark.asyncio
async def test_send_gmail_message_is_destructive():
    tool = await server.get_tool("send_gmail_message")
    assert tool.annotations.read_only_hint is False
    assert tool.annotations.destructive_hint is True


@pytest.mark.asyncio
async def test_drive_download_url_writes_new_local_file_per_call():
    tool = await server.get_tool("get_drive_file_download_url")
    assert tool.annotations.read_only_hint is False
    assert tool.annotations.idempotent_hint is False
