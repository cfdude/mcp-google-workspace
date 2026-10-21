"""Tests for the streamable-http startup port probe in main.py."""

import os
import socket
import sys
import time

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import main  # noqa: E402

pytestmark = pytest.mark.skipif(
    os.name == "nt", reason="TIME_WAIT bind semantics differ on Windows"
)


def _listener(port: int = 0) -> socket.socket:
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", port))
    srv.listen()
    return srv


def test_port_with_live_listener_is_not_free():
    srv = _listener()
    try:
        port = srv.getsockname()[1]
        assert main._http_port_conflict("127.0.0.1", port) is not None
    finally:
        srv.close()


def test_port_with_live_listener_is_not_free_when_probing_all_interfaces():
    srv = _listener()
    try:
        port = srv.getsockname()[1]
        assert main._http_port_conflict("0.0.0.0", port) is not None
    finally:
        srv.close()


def test_port_left_in_time_wait_by_a_stopped_server_is_free():
    # A server that closes its accepted connections first (what a restarting
    # HTTP server does) leaves them in TIME_WAIT on its own port. uvicorn binds
    # with SO_REUSEADDR and starts fine, so the probe must not report it busy.
    srv = _listener()
    port = srv.getsockname()[1]
    client = socket.create_connection(("127.0.0.1", port))
    conn, _ = srv.accept()
    conn.close()
    srv.close()
    time.sleep(0.1)
    client.close()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as plain:
        with pytest.raises(OSError):
            plain.bind(("127.0.0.1", port))

    assert main._http_port_conflict("127.0.0.1", port) is None


def test_unused_port_is_free():
    srv = _listener()
    port = srv.getsockname()[1]
    srv.close()
    assert main._http_port_conflict("127.0.0.1", port) is None
