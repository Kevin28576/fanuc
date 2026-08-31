"""Exception hierarchy. Upstream has a single FanucError, so a dropped
connection and an unreachable position look identical and can't be
handled differently."""

from __future__ import annotations

from ._i18n import bi


class FanucError(Exception):
    """Base class for every exception this package raises.

    Kept under this name for compatibility with upstream fanucpy's
    ``except FanucError``.
    """


class ConnectionError_(FanucError):
    """Transport-layer failure: couldn't connect, dropped, or timed out.
    Handling: reconnect; the command itself was fine."""


class ProtocolError(FanucError):
    """Malformed response, or an unknown response code. Usually a driver
    version mismatch; reconnecting won't help."""


class CommandError(FanucError):
    """The controller explicitly reported the command failed (code 1).

    Attributes:
        message: the raw error the controller returned, e.g.
            ``position-is-not-reachable``.
        command: the command string that triggered it, for debugging.
    """

    def __init__(self, message: str, command: str | None = None):
        self.message = message
        self.command = command
        if command is None:
            detail = message
        else:
            detail = f"{message} ({bi('指令', 'command')}: {command})"
        super().__init__(detail)


class UnreachableError(CommandError):
    """Target is outside the work envelope or has no valid pose,
    corresponding to ``position-is-not-reachable``. Fix the target
    value; retrying won't help."""


class MotionSetupError(CommandError):
    """The driver couldn't write a motion parameter register,
    corresponding to ``R[81..83]``/``PR[81]-was-not-set``.

    Usually means another program in the workcell is holding those
    registers; resolve the conflict on the controller side.
    """


class UnsupportedCommandError(CommandError):
    """The driver doesn't recognize this command, corresponding to
    ``wrong-command``. Either the driver version is old, or the
    feature needs the extended KAREL driver."""
