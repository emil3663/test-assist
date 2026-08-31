"""Tests for the manual "Check for updates" feature.

No test here may touch the network. parse_latest_release() and is_newer()
are pure functions with no I/O; UpdateChecker.interpret() is the seam between
a network reply and those two functions, so it can be driven with a literal
(succeeded, payload) pair instead of a real - or substituted - QNetworkReply.
"""

from __future__ import annotations

import json

from update_check import UpdateChecker, is_newer, parse_latest_release


# ── parse_latest_release ─────────────────────────────────────────────────────

def _payload(**fields) -> bytes:
    return json.dumps(fields).encode("utf-8")


def test_parse_latest_release_reads_tag_and_url():
    result = parse_latest_release(_payload(tag_name="v1.3.0", html_url="https://example.test/1.3.0"))
    assert result == ("v1.3.0", "https://example.test/1.3.0")


def test_parse_latest_release_rejects_malformed_json():
    assert parse_latest_release(b"{not json") is None


def test_parse_latest_release_rejects_an_empty_payload():
    assert parse_latest_release(b"") is None


def test_parse_latest_release_rejects_a_missing_tag_name():
    assert parse_latest_release(_payload(html_url="https://example.test")) is None


def test_parse_latest_release_rejects_a_non_object_payload():
    assert parse_latest_release(b"[1, 2, 3]") is None
    assert parse_latest_release(b'"just a string"') is None


def test_parse_latest_release_rejects_a_non_string_tag_name():
    assert parse_latest_release(_payload(tag_name=110, html_url="https://example.test")) is None


def test_parse_latest_release_tolerates_a_missing_html_url():
    result = parse_latest_release(_payload(tag_name="v1.3.0"))
    assert result == ("v1.3.0", "")


# ── is_newer ──────────────────────────────────────────────────────────────────

def test_is_newer_true_when_a_newer_release_exists():
    assert is_newer("1.2.0", "1.3.0") is True


def test_is_newer_false_for_the_same_version():
    assert is_newer("1.2.0", "1.2.0") is False


def test_is_newer_false_for_an_older_release_never_offers_a_downgrade():
    assert is_newer("1.2.0", "1.1.0") is False


def test_is_newer_strips_a_leading_v_from_either_side():
    assert is_newer("1.2.0", "v1.3.0") is True
    assert is_newer("v1.2.0", "1.3.0") is True
    assert is_newer("v1.2.0", "v1.2.0") is False


def test_is_newer_compares_integer_tuples_not_strings():
    """A plain string compare puts "1.10.0" below "1.9.0" - it must not."""
    assert is_newer("1.9.0", "1.10.0") is True
    assert is_newer("1.10.0", "1.9.0") is False


def test_is_newer_false_on_an_unparseable_current_version():
    assert is_newer("not-a-version", "1.2.0") is False


def test_is_newer_false_on_an_unparseable_latest_version():
    assert is_newer("1.2.0", "not-a-version") is False


def test_is_newer_false_on_an_empty_string():
    assert is_newer("", "1.2.0") is False
    assert is_newer("1.2.0", "") is False


# ── UpdateChecker.interpret (the network/pure-function seam) ─────────────────

def test_interpret_reports_failure_when_the_request_did_not_succeed():
    result = UpdateChecker.interpret(False, b"", "1.2.0")
    assert result.ok is False


def test_interpret_reports_failure_on_an_unparseable_payload():
    result = UpdateChecker.interpret(True, b"not json", "1.2.0")
    assert result.ok is False


def test_interpret_reports_up_to_date():
    result = UpdateChecker.interpret(True, _payload(tag_name="v1.2.0", html_url="https://x"), "1.2.0")
    assert result.ok is True
    assert result.is_newer is False


def test_interpret_reports_a_newer_release_with_a_bare_version_and_the_url():
    result = UpdateChecker.interpret(
        True, _payload(tag_name="v1.3.0", html_url="https://example.test/releases/v1.3.0"), "1.2.0"
    )
    assert result.ok is True
    assert result.is_newer is True
    assert result.latest_version == "1.3.0"
    assert result.html_url == "https://example.test/releases/v1.3.0"


def test_interpret_never_reports_a_downgrade_as_an_update():
    result = UpdateChecker.interpret(True, _payload(tag_name="v1.0.0", html_url="https://x"), "1.2.0")
    assert result.ok is True
    assert result.is_newer is False
