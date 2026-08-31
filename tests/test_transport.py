"""MappdkTransport tests.

Two techniques, picked per scenario:

- A real loopback TCP server (127.0.0.1, an OS-assigned port) for the
  happy paths and the split-packet bug this module exists to fix --
  these need an actual socket round trip to mean anything, mocking
  send/recv would just be testing the mock.
- A hand-rolled fake socket (``FakeSocket``) standing in for
  ``transport._sock`` for the error paths (timeout, peer close, a
  response that never terminates) that are impractical to provoke
  deterministically over a real socket without flaky timing.

Neither needs ROBOGUIDE or a real controller.
"""

from __future__ import annotations

import socket
import threading
import time

import pytest

from fanuc.exceptions import ConnectionError_, ProtocolError
from fanuc.transport import BUFFER_SIZE, MappdkTransport


# -- a real loopback server ----------------------------------------------------

class _FakeMappdkServer:
    """A one-connection TCP server standing in for MAPPDK_SERVER.

    Sends ``greeting`` immediately on accept (mirroring the driver's
    own unsolicited ``0:success``), then for each command line it
    reads, replies with the next entry in ``responses`` -- each entry
    is either bytes (written in one shot) or a list of byte chunks
    (written as separate ``sendall`` calls with a short sleep between
    them, to simulate a response split across TCP packets).
    """

    def __init__(self, responses, greeting=b"0:success"):
        self._responses = list(responses)
        self._greeting = greeting
        self._listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._listener.bind(("127.0.0.1", 0))
        self._listener.listen(1)
        self.port = self._listener.getsockname()[1]
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        # Loops accepting connections (not just one), so tests that
        # disconnect and reconnect get a fresh greeting each time,
        # same as a real MAPPDK_SERVER staying up across reconnects.
        # Ends when self._listener is closed (close() -> accept()
        # raises OSError).
        while True:
            try:
                conn, _ = self._listener.accept()
            except OSError:
                return
            with conn:
                conn.sendall(self._greeting)
                for response in self._responses:
                    # one command per line; read until the newline the
                    # protocol layer's TERMINATOR adds
                    buf = b""
                    while not buf.endswith(b"\n"):
                        chunk = conn.recv(BUFFER_SIZE)
                        if not chunk:
                            return
                        buf += chunk
                    chunks = response if isinstance(response, list) else [response]
                    for chunk in chunks:
                        conn.sendall(chunk)
                        if len(chunks) > 1:
                            time.sleep(0.01)

    def close(self):
        self._listener.close()
        self._thread.join(timeout=2)


@pytest.fixture
def fake_server():
    servers = []

    def _make(responses, greeting=b"0:success"):
        server = _FakeMappdkServer(responses, greeting)
        servers.append(server)
        return server

    yield _make
    for server in servers:
        server.close()


def test_connect_reads_the_greeting(fake_server):
    server = fake_server(responses=[])
    transport = MappdkTransport("127.0.0.1", server.port, timeout=2)

    greeting = transport.connect()

    assert greeting == "0:success"
    assert transport.connected is True
    transport.disconnect()


def test_connect_twice_is_rejected_without_touching_the_network(fake_server):
    server = fake_server(responses=[])
    transport = MappdkTransport("127.0.0.1", server.port, timeout=2)
    transport.connect()

    with pytest.raises(ConnectionError_):
        transport.connect()

    transport.disconnect()


def test_connect_refused(monkeypatch):
    # Port 9 (the "discard" service) is reliably unassigned/refused in
    # this environment; already relied on elsewhere in this project's
    # own manual testing.
    transport = MappdkTransport("127.0.0.1", 9, timeout=1)
    with pytest.raises(ConnectionError_):
        transport.connect()
    assert transport.connected is False


def test_send_requires_a_connection_first():
    transport = MappdkTransport("127.0.0.1", 9999)
    with pytest.raises(ConnectionError_):
        transport.send("curpos")


def test_send_round_trip(fake_server):
    server = fake_server(responses=[b"0:x=1.000,y=2.000\n"])
    transport = MappdkTransport("127.0.0.1", server.port, timeout=2)
    transport.connect()

    result = transport.send("curpos")

    assert result == "0:x=1.000,y=2.000"
    transport.disconnect()


def test_send_reassembles_a_response_split_across_packets(fake_server):
    """The actual bug this module exists to fix: a response arriving
    in two TCP packets used to get truncated at the first one (the
    default is_complete only checks for a colon, which the first
    packet already satisfies). _drain's short extra read has to catch
    the second packet before send() returns."""
    server = fake_server(responses=[[b"0:AB", b"CD\n"]])
    transport = MappdkTransport("127.0.0.1", server.port, timeout=2)
    transport.connect()

    result = transport.send("getsreg:00001")

    assert result == "0:ABCD"
    transport.disconnect()


def test_disconnect_is_safe_to_call_when_not_connected():
    transport = MappdkTransport("127.0.0.1", 9999)
    transport.disconnect()  # must not raise
    assert transport.connected is False


def test_disconnect_is_safe_to_call_twice(fake_server):
    server = fake_server(responses=[])
    transport = MappdkTransport("127.0.0.1", server.port, timeout=2)
    transport.connect()
    transport.disconnect()
    transport.disconnect()  # must not raise
    assert transport.connected is False


def test_reconnect_closes_then_reopens(fake_server):
    server = fake_server(responses=[])
    transport = MappdkTransport("127.0.0.1", server.port, timeout=2)
    transport.connect()

    greeting = transport.reconnect()

    assert greeting == "0:success"
    assert transport.connected is True
    transport.disconnect()


def test_context_manager_connects_and_disconnects(fake_server):
    server = fake_server(responses=[])
    with MappdkTransport("127.0.0.1", server.port, timeout=2) as transport:
        assert transport.connected is True
    assert transport.connected is False


def test_repr_shows_connection_state(fake_server):
    server = fake_server(responses=[])
    transport = MappdkTransport("127.0.0.1", server.port, timeout=2)
    assert "disconnected" in repr(transport)
    transport.connect()
    assert "connected" in repr(transport)
    transport.disconnect()


# -- error paths, via a fake socket object ------------------------------------

class FakeSocket:
    """Stands in for transport._sock: recv()/sendall() play back a
    scripted sequence (bytes, or an exception instance to raise), so
    the error paths in _recv/_drain/send can be hit deterministically
    without racing a real socket's timing."""

    def __init__(self, recv_sequence=(), fail_sendall=None):
        self._recv_sequence = list(recv_sequence)
        self._fail_sendall = fail_sendall
        self._timeout = None
        self.sent: list[bytes] = []
        self.closed = False

    def sendall(self, data):
        if self._fail_sendall is not None:
            raise self._fail_sendall
        self.sent.append(data)

    def recv(self, bufsize):
        if not self._recv_sequence:
            raise AssertionError("FakeSocket.recv called more times than scripted")
        item = self._recv_sequence.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    def close(self):
        self.closed = True

    def settimeout(self, value):
        self._timeout = value

    def gettimeout(self):
        return self._timeout

    def setsockopt(self, *args, **kwargs):
        pass


def _connected_transport(recv_sequence=(), fail_sendall=None):
    """A transport that believes it's connected, without any real
    socket underneath -- for exercising _recv/_drain/send's error
    branches directly."""
    transport = MappdkTransport("127.0.0.1", 9999)
    transport._sock = FakeSocket(recv_sequence, fail_sendall)
    return transport


def test_recv_timeout_disconnects_and_raises():
    transport = _connected_transport(recv_sequence=[socket.timeout()])
    with pytest.raises(ConnectionError_):
        transport.send("curpos")
    assert transport.connected is False


def test_recv_os_error_disconnects_and_raises():
    transport = _connected_transport(recv_sequence=[OSError("boom")])
    with pytest.raises(ConnectionError_):
        transport.send("curpos")
    assert transport.connected is False


def test_peer_closing_the_connection_disconnects_and_raises():
    transport = _connected_transport(recv_sequence=[b""])
    with pytest.raises(ConnectionError_):
        transport.send("curpos")
    assert transport.connected is False


def test_response_that_never_completes_raises_protocol_error():
    # never contains a colon, so is_complete never returns True; once
    # accumulated text exceeds BUFFER_SIZE * 4 this gives up rather
    # than reading forever
    chunks = [b"x" * BUFFER_SIZE for _ in range(5)]
    transport = _connected_transport(recv_sequence=chunks)
    with pytest.raises(ProtocolError):
        transport.send("curpos")
    assert transport.connected is False


def test_send_failure_disconnects_and_raises():
    transport = _connected_transport(fail_sendall=OSError("broken pipe"))
    with pytest.raises(ConnectionError_):
        transport.send("curpos")
    assert transport.connected is False


def test_send_uses_a_custom_is_complete_predicate():
    """A predicate stricter than the default (colon present) keeps
    reading until it's satisfied, not just until the first colon."""
    # the trailing socket.timeout() stands in for _drain's "confirmed
    # nothing else is coming" read, once is_complete is finally satisfied
    transport = _connected_transport(recv_sequence=[b"0:a", b",b,c\n", socket.timeout()])

    def needs_three_fields(text):
        return text.count(",") >= 2

    result = transport.send("curjpos", is_complete=needs_three_fields)
    assert result == "0:a,b,c"
