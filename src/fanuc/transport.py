"""Socket send/receive.

Only cares about strings in and out; doesn't care what a command
means.

The driver responds with WRITE comm_file (resp) (mappdk_server.kl:68),
with no terminator character; framing relies on TCP packet
boundaries. Upstream calls recv() exactly once, so a response split
across packets gets read half-finished.

Here the caller passes an is_complete predicate: once data arrives, it
asks whether that's enough yet, and keeps reading if not. Deciding
completeness is the protocol layer's job; this module only executes
it. That also avoids waiting out an extra timeout on every call, so
watch mode's refresh rate isn't affected.

Outgoing commands need a trailing newline, since the driver's
READ comm_file(cmd) reads line by line.
"""

from __future__ import annotations

import logging
import socket
from types import TracebackType
from typing import Callable, Optional, Type

from ._i18n import bi
from .exceptions import ConnectionError_, ProtocolError
from .protocol import TERMINATOR

logger = logging.getLogger(__name__)

#: Buffer size for a single recv(). The driver's response string is
#: capped at STRING[254].
BUFFER_SIZE = 1024


def _default_complete(text: str) -> bool:
    """Minimal completeness check: at least a response code and its
    separating colon."""
    return ":" in text


class MappdkTransport:
    """A TCP connection to a MAPPDK server.

    Args:
        host: controller IP. Always 127.0.0.1 for the ROBOGUIDE virtual
            controller.
        port: MAPPDK server port.
        timeout: socket timeout in seconds. Motion commands block until
            the move completes, so the default must exceed the slowest
            expected move.
        encoding: encoding for send/receive. Commands themselves are
            ASCII, but alarm messages the controller returns carry text
            in the controller's interface language: GB18030 for a
            Simplified Chinese controller. GB18030 is ASCII-compatible,
            so an English controller decodes fine too.
    """

    def __init__(
        self,
        host: str,
        port: int,
        timeout: float = 60.0,
        encoding: str = "gb18030",
    ):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.encoding = encoding
        self._sock: Optional[socket.socket] = None

    # -- connection management ---------------------------------------------

    @property
    def connected(self) -> bool:
        return self._sock is not None

    def connect(self) -> str:
        """Opens the connection and reads the driver's greeting.

        The driver proactively sends ``0:success`` at the end of
        OPEN_COMM (mappdk_comm.kl:54); this must be read off first or a
        later command would mistake it for its own response.

        Returns:
            The raw greeting string.
        """
        if self._sock is not None:
            raise ConnectionError_(bi("連線已經建立，請先 disconnect()", "already connected, call disconnect() first"))

        try:
            sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        except OSError as exc:
            raise ConnectionError_(bi(
                f"無法連線到 {self.host}:{self.port} -> {exc}",
                f"cannot connect to {self.host}:{self.port} -> {exc}",
            )) from exc

        sock.settimeout(self.timeout)
        # Small packets like position queries are latency-sensitive;
        # disable Nagle's algorithm.
        try:
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except OSError:  # unsupported on a handful of platforms, harmless
            logger.debug(bi("無法設定 TCP_NODELAY", "cannot set TCP_NODELAY"), exc_info=True)

        self._sock = sock
        logger.debug(f"已連線 {self.host}:{self.port} / connected {self.host}:{self.port}")

        return self._recv(_default_complete)

    def disconnect(self) -> None:
        """Closes the connection. Safe to call repeatedly."""
        if self._sock is None:
            return
        try:
            self._sock.close()
        except OSError:
            logger.debug(bi("關閉 socket 時發生例外", "exception while closing socket"), exc_info=True)
        finally:
            self._sock = None
            logger.debug(bi("已中斷連線", "disconnected"))

    def reconnect(self) -> str:
        """Rebuilds the connection after a disconnect."""
        self.disconnect()
        return self.connect()

    # -- send/receive --------------------------------------------------------

    def send(
        self,
        command: str,
        is_complete: Callable[[str], bool] | None = None,
    ) -> str:
        """Sends one command and returns the raw response string.

        Args:
            command: command string without the terminator.
            is_complete: predicate for whether the bytes received so far
                form a complete response. Defaults to checking for a
                colon; commands that need a stricter check (e.g. curpos
                should have 6 fields) get one from the protocol layer.
        """
        sock = self._require_sock()
        payload = (command.strip() + TERMINATOR).encode(self.encoding)

        try:
            sock.sendall(payload)
        except OSError as exc:
            self.disconnect()
            raise ConnectionError_(bi(f"送出指令失敗: {exc}", f"failed to send command: {exc}")) from exc

        return self._recv(is_complete or _default_complete)

    def _recv(self, is_complete: Callable[[str], bool]) -> str:
        """Keeps receiving until ``is_complete`` says so.

        ``is_complete`` is reliable for responses with a fixed field
        count (curpos, curjpos, ...), but not for ones that end in
        arbitrary-length text (alarm messages, string registers): the
        default ``_default_complete`` only checks for a colon, and if
        the message is long enough to land right on a TCP packet
        boundary, whatever comes after the colon may not have arrived
        yet when it gets judged "done". The leftover bytes then get
        picked up by the *next* command's _recv, showing up as a
        fragment stuck onto the front of that response.

        So once ``is_complete`` says done, this doesn't return right
        away; it does one more read with a short timeout to confirm
        there's nothing left. In the normal case (everything arrived in
        one packet) this step costs almost nothing; when the response
        really was split across packets, it gives the rest a chance to
        arrive.
        """
        sock = self._require_sock()
        chunks: list[bytes] = []

        while True:
            try:
                data = sock.recv(BUFFER_SIZE)
            except socket.timeout as exc:
                self.disconnect()
                raise ConnectionError_(bi(
                    f"等待回應逾時（{self.timeout}s）。動作指令會阻塞到動作完成，必要時調高 timeout",
                    f"timed out waiting for response ({self.timeout}s). Motion commands block "
                    "until the move finishes, raise timeout if needed",
                )) from exc
            except OSError as exc:
                self.disconnect()
                raise ConnectionError_(bi(f"接收回應失敗: {exc}", f"failed to receive response: {exc}")) from exc

            if not data:
                # Peer closed the connection. Usually means MAPPDK on
                # the TP was aborted.
                self.disconnect()
                raise ConnectionError_(bi(
                    "連線被控制器關閉。請確認 TP 上的 MAPPDK 仍在執行",
                    "connection closed by the controller. Check that MAPPDK is still running on the TP",
                ))

            chunks.append(data)
            text = b"".join(chunks).decode(self.encoding, errors="replace")

            if is_complete(text):
                trailing = self._drain(sock)
                if not trailing:
                    return text.strip()
                chunks.append(trailing)
                text = b"".join(chunks).decode(self.encoding, errors="replace")
                # More data arrived; loop back and re-check completeness
                # against the updated text instead of trusting the
                # earlier is_complete result.

            if len(text) > BUFFER_SIZE * 4:
                self.disconnect()
                raise ProtocolError(bi(
                    f"回應過長且無法判定結束: {text[:120]!r}...",
                    f"response is too long and end cannot be determined: {text[:120]!r}...",
                ))

    def _drain(self, sock: socket.socket) -> bytes:
        """Reads once more with a short timeout to confirm nothing is
        still sitting in the socket buffer.

        The timeout is deliberately short: in the normal case, data in
        the same TCP packet has already arrived, so this just gives
        bytes that were "delivered but not yet recv()'d" a chance --
        it's not waiting for the controller to compute anything more.
        """
        original_timeout = sock.gettimeout()
        try:
            sock.settimeout(0.05)
            return sock.recv(BUFFER_SIZE)
        except socket.timeout:
            return b""
        except OSError:
            return b""
        finally:
            sock.settimeout(original_timeout)

    def _require_sock(self) -> socket.socket:
        if self._sock is None:
            raise ConnectionError_(bi("尚未連線，請先呼叫 connect()", "not connected, call connect() first"))
        return self._sock

    # -- context manager --------------------------------------------------

    def __enter__(self) -> "MappdkTransport":
        self.connect()
        return self

    def __exit__(
        self,
        exc_type: Type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.disconnect()

    def __repr__(self) -> str:
        state = "connected" if self.connected else "disconnected"
        return f"<MappdkTransport {self.host}:{self.port} {state}>"
