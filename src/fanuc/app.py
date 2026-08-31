"""Task framework for repeatable robot programs.

Interface matches upstream fanucpy's RobotApp:

    https://github.com/torayeff/fanucpy/blob/main/src/fanucpy/robotapp.py

A subclass takes an already-constructed (but not yet connected)
FanucRobot in ``__init__`` and stores it as ``self.robot``; connecting,
moving, and cleanup all happen inside ``_main()``; whether and when
to connect/disconnect is entirely up to the subclass. ``run()`` only
wraps the result or exception, so it's convenient to call from a
scheduler or web API without letting an exception blow through.

Differences from upstream:
    - ``run()`` only swallows ``FanucError``, not every exception. A
      programming bug (``TypeError``, ``KeyError``, etc.) should still
      propagate: swallowing it just buries the problem, making it
      harder to find in production.
    - Returns a named ``AppResult`` instead of a bare tuple, so fields
      are harder to mix up, and it can be used directly as a bool.
"""

from __future__ import annotations

import traceback
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from ._i18n import bi
from .exceptions import FanucError


@dataclass
class AppResult:
    """Return value of ``RobotApp.run()``, usable directly as a bool."""

    ok: bool
    message: str
    result: Any = None

    def __bool__(self) -> bool:
        return self.ok


class RobotApp(ABC):
    """Base class for a robot task, interface matching upstream
    fanucpy's RobotApp.

    Subclasses must implement:
        ``configure()``: static setup before the task starts (reading
            config, computing parameters), no connecting, no
            touching the robot.
        ``_main(**kwargs)``: the actual task body, including
            connecting, moving, and cleanup.

    Usage::

        class MyApp(RobotApp):
            def __init__(self, robot):
                self.robot = robot

            def configure(self):
                pass

            def _main(self, **kwargs):
                self.robot.connect()
                try:
                    ...
                    return "done"
                finally:
                    self.robot.disconnect()

        app = MyApp(FanucRobot(host="127.0.0.1"))
        app.configure()
        result = app.run()
        if not result:
            print(result.message)
    """

    @abstractmethod
    def configure(self) -> None:
        raise NotImplementedError(bi("子類別必須實作 configure()", "subclass must implement configure()"))

    @abstractmethod
    def _main(self, **kwargs: Any) -> Any:
        raise NotImplementedError(bi("子類別必須實作 _main()", "subclass must implement _main()"))

    def run(self, **kwargs: Any) -> AppResult:
        """Runs ``_main()``, wrapping the result or exception into an
        ``AppResult``.

        Only swallows ``FanucError`` (connection, protocol, and motion
        failures; errors talking to the robot), not other
        exceptions: a programming bug should still propagate;
        swallowing it just makes it harder to find in production.
        """
        try:
            result = self._main(**kwargs)
            return AppResult(ok=True, message="success", result=result)
        except FanucError as exc:
            message = "".join(
                traceback.TracebackException.from_exception(exc).format()
            )
            return AppResult(ok=False, message=message)
