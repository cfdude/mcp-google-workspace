"""
Unit tests for _correct_time_format_for_api defensive input normalization.

Covers the case where LLM-driven MCP clients double-encode JSON string args,
passing values like '"2026-05-15T00:00:00Z"' with literal quotes inside the
string, or the literal string "null"/"None" instead of omitting the param.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from gcalendar.calendar_tools import _correct_time_format_for_api


@pytest.mark.parametrize("empty", [None, "", "   "])
def test_empty_returns_none(empty):
    assert _correct_time_format_for_api(empty, "time_min") is None


@pytest.mark.parametrize(
    "sentinel", ['"null"', '"NULL"', "'null'", "null", "None", '"none"', "  null  "]
)
def test_null_sentinel_returns_none(sentinel):
    # Some clients pass the literal string "null"/"None" instead of omitting the param.
    assert _correct_time_format_for_api(sentinel, "time_min") is None


def test_plain_date_only_normalizes_to_rfc3339_utc():
    assert (
        _correct_time_format_for_api("2026-05-15", "time_min") == "2026-05-15T00:00:00Z"
    )


def test_double_quoted_date_only_is_stripped():
    # The value the LLM emitted as `time_min: "2026-05-15"` ended up double-encoded
    # into a string containing the literal quote characters.
    assert (
        _correct_time_format_for_api('"2026-05-15"', "time_min")
        == "2026-05-15T00:00:00Z"
    )


def test_single_quoted_date_only_is_stripped():
    assert (
        _correct_time_format_for_api("'2026-05-15'", "time_min")
        == "2026-05-15T00:00:00Z"
    )


def test_double_quoted_rfc3339_is_stripped():
    # Real failure mode observed in the wild: timeMin arrived as the string
    # `"2026-05-15T00:00:00Z"` with quotes inside the value, producing
    # `timeMin=%222026-05-15T00:00:00Z%22` on the Calendar API request URL,
    # which returns HTTP 400 Bad Request.
    out = _correct_time_format_for_api('"2026-05-15T00:00:00Z"', "time_min")
    assert out == "2026-05-15T00:00:00Z"


def test_whitespace_and_quotes_combined_are_stripped():
    out = _correct_time_format_for_api('  "2026-05-15T10:30:00Z"  ', "time_min")
    assert out == "2026-05-15T10:30:00Z"


def test_unquoted_rfc3339_passes_through():
    # Regression: well-formed values must not be mangled.
    out = _correct_time_format_for_api("2026-05-15T10:30:00Z", "time_min")
    assert out == "2026-05-15T10:30:00Z"
