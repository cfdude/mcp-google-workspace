import logging

from core.log_formatter import SuppressStatelessTransportTerminationFilter


def _record(name: str, message: str, level: int = logging.INFO) -> logging.LogRecord:
    return logging.LogRecord(
        name=name,
        level=level,
        pathname=__file__,
        lineno=1,
        msg=message,
        args=(),
        exc_info=None,
    )


def test_stateless_transport_none_termination_log_is_suppressed():
    log_filter = SuppressStatelessTransportTerminationFilter()

    assert not log_filter.filter(
        _record("mcp.server.streamable_http", "Terminating session: None")
    )


def test_transport_termination_with_real_session_is_not_suppressed():
    log_filter = SuppressStatelessTransportTerminationFilter()

    assert log_filter.filter(
        _record("mcp.server.streamable_http", "Terminating session: session-123")
    )


def test_unrelated_none_message_is_not_suppressed():
    log_filter = SuppressStatelessTransportTerminationFilter()

    assert log_filter.filter(_record("auth.google_auth", "Terminating session: None"))
