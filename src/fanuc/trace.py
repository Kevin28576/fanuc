"""Motion trajectory recording.

The driver is synchronous and blocking (see protocol.py's docstring):
once the main connection sends a motion command, that socket is stuck
until the move finishes, and position can't be queried on the same
connection during that time. This uses a background thread on a
separate connection to the logger (S7), polling position while the
main connection's motion command is in flight, recording the actual
path taken.

Usage::

    from fanuc import MotionTracer, FanucRobot

    mover = FanucRobot(host="127.0.0.1")
    mover.connect()

    with MotionTracer(host="127.0.0.1") as tracer:
        tracer.start()
        mover.move_pose([400, 50, -100, -180, 0, 0])
        samples = tracer.stop()

    mover.disconnect()

    for s in samples:
        print(f"{s.t:.3f}s  X={s.pose.x:.1f}")
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from types import TracebackType
from typing import Type

from ._i18n import bi
from .exceptions import ConnectionError_, FanucError
from .protocol import LOGGER_PORT
from .robot import FanucRobot, _parse_duration
from .types import Pose

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TraceSample:
    """One trajectory sample."""

    #: Seconds relative to when start() was called.
    t: float
    pose: Pose


class MotionTracer:
    """Polls position on a separate connection (defaults to
    logger/S7) in the background to record a motion trajectory.

    A separate connection from the FanucRobot issuing motion commands,
    usually pointed at the same controller's logger port
    (``protocol.LOGGER_PORT``), so it can keep querying position while
    the main connection is stuck inside move().

    Args:
        host: controller IP.
        port: defaults to ``LOGGER_PORT`` (S7), kept separate from the
            main connection. If your application never issues motion
            commands at the same time, this can point at the main port
            instead and just poll on it.
        interval: sampling interval, a string with a unit, e.g.
            ``"20ms"``, ``"0.05s"``. A shorter interval gives a finer
            trajectory but puts more query load on the controller.
        model: model name, display only.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = LOGGER_PORT,
        interval: str = "20ms",
        model: str = "FANUC",
    ):
        self._robot = FanucRobot(host=host, port=port, model=model)
        self._interval_s = _parse_duration(interval, "interval")
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._samples: list[TraceSample] = []
        self._start_time: float | None = None
        #: Exception recorded when the background thread's query fails;
        #: stop() re-raises it. Not raised directly in the background
        #: thread, since the main thread would never see it there --
        #: recording would just quietly stop early with no clue why.
        self._error: FanucError | None = None

    def connect(self) -> None:
        """Connects to the logger/S7 port.

        On failure, adds a hint pointing at MAPPDK_LOGGER specifically:
        a plain connection-refused message doesn't tell the caller
        which of the two KAREL programs to check, and this is the one
        connection in the package where that's not obvious from the
        port number alone.
        """
        try:
            self._robot.connect()
        except ConnectionError_ as exc:
            raise ConnectionError_(bi(
                f"{exc}\n"
                f"這條是 logger（S7，port {self._robot.port}）連線，"
                "請確認 TP 上的 MAPPDK_LOGGER 有在跑，不是 MAPPDK_SERVER（S8）。",
                f"{exc}\n"
                f"this is the logger connection (S7, port {self._robot.port}); "
                "check that MAPPDK_LOGGER is running on the TP, not MAPPDK_SERVER (S8).",
            )) from exc

    def disconnect(self) -> None:
        self._robot.disconnect()

    def __enter__(self) -> "MotionTracer":
        self.connect()
        return self

    def __exit__(
        self,
        exc_type: Type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.disconnect()

    def start(self) -> None:
        """Starts background polling. Call connect() first."""
        self._samples = []
        self._error = None
        self._stop_event.clear()
        self._start_time = time.monotonic()
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def _poll_loop(self) -> None:
        assert self._start_time is not None
        while not self._stop_event.is_set():
            try:
                pose = self._robot.get_curpos()
            except FanucError as exc:
                # Stop recording on a connection problem. Not raised
                # here in the background thread; stored instead so
                # stop() can re-raise it.
                logger.warning(bi("軌跡記錄查詢失敗，提前停止", "trace query failed, stopping early") + "：%s", exc)
                self._error = exc
                return
            t = time.monotonic() - self._start_time
            self._samples.append(TraceSample(t=t, pose=pose))
            self._stop_event.wait(self._interval_s)

    def stop(self) -> list[TraceSample]:
        """Stops background polling and returns every sample recorded
        during this run.

        If the background thread's query failed partway through, this
        re-raises that exception. The samples collected are usually
        still meaningful (a partial trajectory), but the caller should
        know recording didn't run to completion.
        """
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None
        if self._error is not None:
            raise self._error
        return list(self._samples)
