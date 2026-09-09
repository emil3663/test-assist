"""Single-instance coordination for Test Assist."""

from __future__ import annotations

import time
from enum import Enum

from PySide6.QtCore import QCoreApplication, QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket


class AcquireOutcome(Enum):
    """What the caller should do after calling SingleInstanceManager.acquire()."""

    STARTED = "started"        # No running instance took the request; start a UI.
    HANDED_OFF = "handed_off"  # A running instance took the request; start nothing.
    FAILED = "failed"          # Neither handoff nor becoming the instance worked.


class SingleInstanceManager(QObject):
    """
    Keep only one running instance - handing a second launch off to the
    first rather than replacing it.

    Startup behavior:
    1) If another instance is reachable, hand the request (a file to open,
       or a plain "come to front") off to it and stop - nothing here starts
       a UI. This is what a second "Open with -> Test Assist" launch, or a
       second plain launch, both should do: reuse the running app in-place
       rather than silently killing whatever the user was doing in it.
    2) If handoff fails or times out - the running instance is hung, not
       merely busy - fall back to the old behavior: send it QUIT, wait
       briefly, then become the instance ourselves. A hung instance must
       still be recoverable by relaunching.
    3) If nothing was running at all, step 1 fails immediately (nothing to
       connect to) and step 2 is a no-op, so this reduces to a plain first
       launch.
    """

    quit_requested = Signal()
    show_requested = Signal()
    open_requested = Signal(str)

    # How long a running instance gets to acknowledge a handoff before it is
    # treated as hung rather than merely slow. Generous enough for a real
    # instance (acknowledged before any potentially-slow image load even
    # starts - see _on_new_connection), short enough that a genuinely dead
    # process does not make a relaunch feel stuck.
    _HANDOFF_ACK_TIMEOUT_MS = 800

    def __init__(self, server_name: str = "test-assist-single-instance") -> None:
        super().__init__()
        self._server_name = server_name
        self._server: QLocalServer | None = None

    def acquire(self, open_path: str | None = None) -> AcquireOutcome:
        """Acquire singleton ownership for this process, or hand the
        request off to a running instance instead.

        `open_path` is the file (if any) this launch was asked to open -
        e.g. via "Open with" - forwarded to a running instance as `OPEN:
        <path>`, or sent as a plain `SHOW` if there is nothing to open.
        """
        if self._handoff_to_existing(open_path):
            return AcquireOutcome.HANDED_OFF

        self._request_existing_quit()
        # Rapid restarts can leave the local server endpoint briefly busy.
        # Retry for a short period so relaunch works reliably.
        for _ in range(20):
            if self._start_server():
                return AcquireOutcome.STARTED
            time.sleep(0.12)
        return AcquireOutcome.FAILED

    def close(self) -> None:
        if self._server is not None:
            self._server.close()
            self._server.deleteLater()
            self._server = None

    def _handoff_to_existing(self, open_path: str | None) -> bool:
        """Try to hand this launch off to an already-running instance.

        Returns True only once the running instance has acknowledged the
        request - a connection with no reply (or none at all) is exactly
        the "nothing running" or "hung" cases the caller must fall back
        from, not a successful handoff.
        """
        sock = QLocalSocket(self)
        sock.connectToServer(self._server_name)
        if not sock.waitForConnected(200):
            return False

        command = f"OPEN:{open_path}" if open_path else "SHOW"
        sock.write(command.encode("utf-8"))
        sock.flush()
        sock.waitForBytesWritten(200)
        # Found necessary by testing two instances in one process (as the
        # test suite does): without an explicit pump here, the write above
        # can sit undelivered until something else happens to process
        # events, which reads as a spurious handoff timeout even though a
        # real second, independently-running process would not need it.
        QCoreApplication.processEvents()

        acknowledged = sock.waitForReadyRead(self._HANDOFF_ACK_TIMEOUT_MS)
        reply = bytes(sock.readAll()).strip() if acknowledged else b""
        sock.disconnectFromServer()
        return reply == b"OK"

    def _request_existing_quit(self) -> None:
        """Fallback only: ask a previous instance to quit, for when a
        handoff was not acknowledged (see _handoff_to_existing) - a hung
        instance, or one old enough not to understand SHOW/OPEN, may still
        understand QUIT and let a relaunch recover cleanly."""
        sock = QLocalSocket(self)
        sock.connectToServer(self._server_name)
        if not sock.waitForConnected(200):
            return

        sock.write(b"QUIT")
        sock.flush()
        sock.waitForBytesWritten(200)
        sock.disconnectFromServer()

        # Give the old process a brief moment to shut down cleanly.
        deadline = time.time() + 2.0
        while time.time() < deadline:
            probe = QLocalSocket(self)
            probe.connectToServer(self._server_name)
            if not probe.waitForConnected(80):
                break
            probe.disconnectFromServer()
            time.sleep(0.08)

    def _start_server(self) -> bool:
        if self._server is not None:
            self._server.close()
            self._server.deleteLater()
            self._server = None

        QLocalServer.removeServer(self._server_name)

        self._server = QLocalServer(self)
        self._server.newConnection.connect(self._on_new_connection)
        return self._server.listen(self._server_name)

    def _on_new_connection(self) -> None:
        if self._server is None:
            return
        while self._server.hasPendingConnections():
            sock = self._server.nextPendingConnection()
            if sock is None:
                continue
            sock.waitForReadyRead(100)
            payload = bytes(sock.readAll()).decode("utf-8", errors="ignore").strip()
            command = payload.upper()

            if command == "QUIT":
                self.quit_requested.emit()
            elif command == "SHOW":
                # Acknowledged before emitting: the connected slot may show
                # a window or (for OPEN, below) a validation dialog, and the
                # sender must not wait on that to learn the handoff itself
                # succeeded.
                self._ack(sock)
                self.show_requested.emit()
            elif command.startswith("OPEN:"):
                path = payload[len("OPEN:"):]
                self._ack(sock)
                self.open_requested.emit(path)

            sock.disconnectFromServer()

    @staticmethod
    def _ack(sock: QLocalSocket) -> None:
        sock.write(b"OK")
        sock.flush()
        sock.waitForBytesWritten(200)
