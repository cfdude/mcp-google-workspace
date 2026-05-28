"""Tests for ``core.log_formatter`` log-directory resolution."""

import logging
import os

import pytest

from core import log_formatter


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch):
    """Ensure each test starts with the relevant env vars unset."""
    monkeypatch.delenv("WORKSPACE_MCP_LOG_DIR", raising=False)
    monkeypatch.delenv("WORKSPACE_MCP_STATELESS_MODE", raising=False)
    yield


def test_resolve_log_dir_defaults_to_home_workspace_mcp_logs(monkeypatch):
    monkeypatch.setattr(os.path, "expanduser", lambda p: "/home/user" if p == "~" else p)

    resolved = log_formatter._resolve_log_dir()

    assert resolved == os.path.join("/home/user", ".google_workspace_mcp", "logs")


def test_resolve_log_dir_honors_workspace_mcp_log_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("WORKSPACE_MCP_LOG_DIR", str(tmp_path))

    resolved = log_formatter._resolve_log_dir()

    assert resolved == str(tmp_path)


def test_resolve_log_dir_expands_user_home_in_env_value(monkeypatch):
    monkeypatch.setenv("WORKSPACE_MCP_LOG_DIR", "~/custom-logs")
    monkeypatch.setattr(
        os.path,
        "expanduser",
        lambda p: "/home/user/custom-logs" if p == "~/custom-logs" else p,
    )

    resolved = log_formatter._resolve_log_dir()

    assert resolved == "/home/user/custom-logs"


def test_configure_file_logging_writes_into_override_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("WORKSPACE_MCP_LOG_DIR", str(tmp_path))

    logger_name = "tests.log_formatter.override"
    target_logger = logging.getLogger(logger_name)
    # Drop any prior handlers so we don't leak state between tests
    for handler in list(target_logger.handlers):
        target_logger.removeHandler(handler)

    try:
        assert log_formatter.configure_file_logging(logger_name) is True
        expected_path = tmp_path / "mcp_server_debug.log"
        assert expected_path.exists()
        file_handlers = [
            h for h in target_logger.handlers if isinstance(h, logging.FileHandler)
        ]
        assert any(
            os.path.abspath(h.baseFilename) == os.path.abspath(str(expected_path))
            for h in file_handlers
        )
    finally:
        for handler in list(target_logger.handlers):
            handler.close()
            target_logger.removeHandler(handler)


def test_configure_file_logging_disabled_in_stateless_mode(monkeypatch, tmp_path):
    monkeypatch.setenv("WORKSPACE_MCP_LOG_DIR", str(tmp_path))
    monkeypatch.setenv("WORKSPACE_MCP_STATELESS_MODE", "true")

    assert log_formatter.configure_file_logging("tests.log_formatter.stateless") is False
    assert not (tmp_path / "mcp_server_debug.log").exists()
