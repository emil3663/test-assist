"""Manual "Check for updates" support.

Design constraints, not preferences: manual only - no on-launch poll, no
telemetry, no auto-download - because this is a QA tool that runs on
corporate machines, and an app that phones out on every launch is what gets
it banned from the estate. The user presses a button or nothing happens.

The parsing and comparison below are pure - no I/O - so they can be tested
with literal payloads. All network I/O lives in UpdateChecker, which uses
QNetworkAccessManager (already bundled; QtNetwork ships for
single_instance.py's QLocalServer) rather than a blocking call, so a slow or
absent network cannot freeze the UI.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from PySide6.QtCore import QObject, QUrl
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

RELEASES_URL = "https://api.github.com/repos/emil3663/test-assist/releases/latest"
REQUEST_TIMEOUT_MS = 5000


def parse_latest_release(payload: bytes) -> tuple[str, str] | None:
    """Extract (tag_name, html_url) from a GitHub releases/latest response.

    Returns None - never raises - on anything unparseable: malformed JSON, an
    empty payload, a non-object response, or a missing/non-string tag_name. A
    network response is never trustworthy input.
    """
    try:
        data = json.loads(payload)
    except (json.JSONDecodeError, UnicodeDecodeError, TypeError):
        return None

    if not isinstance(data, dict):
        return None

    tag_name = data.get("tag_name")
    if not isinstance(tag_name, str) or not tag_name:
        return None

    html_url = data.get("html_url")
    if not isinstance(html_url, str):
        html_url = ""

    return tag_name, html_url


def _parse_version(version: str) -> tuple[int, ...] | None:
    version = version.strip()
    if version[:1] in ("v", "V"):
        version = version[1:]
    parts = version.split(".")
    if not parts or not all(p.isdigit() for p in parts):
        return None
    return tuple(int(p) for p in parts)


def is_newer(current: str, latest: str) -> bool:
    """True only if latest is a strictly greater version than current.

    Compares integer tuples, not strings, so "1.10.0" sorts above "1.9.0" -
    a plain string compare would get that backwards. A leading "v" is
    stripped from either side. Returns False - never raises - on anything
    unparseable, and never reports a downgrade as an update.
    """
    current_parts = _parse_version(current)
    latest_parts = _parse_version(latest)
    if current_parts is None or latest_parts is None:
        return False

    width = max(len(current_parts), len(latest_parts))
    current_padded = current_parts + (0,) * (width - len(current_parts))
    latest_padded = latest_parts + (0,) * (width - len(latest_parts))
    return latest_padded > current_padded


@dataclass
class UpdateResult:
    """Outcome of a single check, already interpreted - the UI layer never
    touches a QNetworkReply or JSON directly."""

    ok: bool
    is_newer: bool = False
    latest_version: str = ""
    html_url: str = ""


class UpdateChecker(QObject):
    """Drives one "Check for updates" request at a time.

    Owns no UI. check() takes a plain callback so the caller (the launcher)
    decides what a result looks like on screen; this class's job ends at
    producing an UpdateResult.
    """

    def __init__(self, manager: QNetworkAccessManager, current_version: str, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._manager = manager
        self._current_version = current_version

    def check(self, on_result) -> None:
        """Issue the request. on_result is called exactly once, with an
        UpdateResult, whether the request succeeds, fails, or times out."""
        request = QNetworkRequest(QUrl(RELEASES_URL))
        request.setTransferTimeout(REQUEST_TIMEOUT_MS)
        # GitHub's API requires a User-Agent or it answers 403.
        request.setRawHeader(b"User-Agent", b"TestAssist-UpdateCheck")
        reply = self._manager.get(request)

        def _finished() -> None:
            result = self.interpret(
                reply.error() == QNetworkReply.NetworkError.NoError,
                bytes(reply.readAll()),
                self._current_version,
            )
            reply.deleteLater()
            on_result(result)

        reply.finished.connect(_finished)

    @staticmethod
    def interpret(succeeded: bool, payload: bytes, current_version: str) -> UpdateResult:
        """The seam between network I/O and the pure functions above - not
        itself I/O, so a test can drive it with a literal payload instead of
        a real (or substituted) QNetworkReply."""
        if not succeeded:
            return UpdateResult(ok=False)

        parsed = parse_latest_release(payload)
        if parsed is None:
            return UpdateResult(ok=False)

        tag_name, html_url = parsed
        latest_version = tag_name[1:] if tag_name[:1] in ("v", "V") else tag_name
        return UpdateResult(
            ok=True,
            is_newer=is_newer(current_version, tag_name),
            latest_version=latest_version,
            html_url=html_url,
        )
