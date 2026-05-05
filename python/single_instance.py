"""Single-instance coordination for Test Assist."""

from __future__ import annotations

import time

from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket


class SingleInstanceManager(QObject):
    """
    Keep only one running instance.

    Startup behavior:
    1) If another instance exists, send it a `QUIT` command.
    2) Wait briefly for it to exit.
    3) Bind a local server for this instance.
    """

    quit_requested = Signal()

    def __init__(self, server_name: str = "test-assist-single-instance") -> None:
        super().__init__()
        self._server_name = server_name
        self._server: QLocalServer | None = None

    def acquire(self) -> bool:
        """Acquire singleton ownership for this process."""
        self._request_existing_quit()
        # Rapid restarts can leave the local server endpoint briefly busy.
        # Retry for a short period so relaunch works reliably.
        for _ in range(20):
            if self._start_server():
                return True
            time.sleep(0.12)
        return False

    def close(self) -> None:
        if self._server is not None:
            self._server.close()
            self._server.deleteLater()
            self._server = None

    def _request_existing_quit(self) -> None:
        """Ask previous instance (if any) to quit before we start."""
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
            payload = bytes(sock.readAll()).decode("utf-8", errors="ignore").strip().upper()
            if payload == "QUIT":
                self.quit_requested.emit()
            sock.disconnectFromServer()
