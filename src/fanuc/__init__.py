"""Control FANUC robots from Python.

    cli        command line
    robot      FanucRobot class
    app        RobotApp task framework
    trace      motion trajectory recording (background thread + second connection)
    protocol   command string encoding/decoding
    transport  socket
    types      Pose / Joints / Alarm
    exceptions exceptions

Usage:

    from fanuc import FanucRobot

    with FanucRobot(host="127.0.0.1", ee_DO_type="RDO", ee_DO_num=7) as robot:
        print(robot.get_curpos().format())

For a repeatable task, use RobotApp; see app.py or
examples/robot_app.py.

To record the actual path taken during a move, use MotionTracer --
see trace.py or examples/trace_motion.py.
"""

from .app import AppResult, RobotApp
from .exceptions import (
    CommandError,
    ConnectionError_,
    FanucError,
    MotionSetupError,
    ProtocolError,
    UnreachableError,
    UnsupportedCommandError,
)
from .protocol import DEFAULT_PORT, LOGGER_PORT
from .robot import RESERVED, FanucRobot
from .trace import MotionTracer, TraceSample
from .transport import MappdkTransport
from .types import Alarm, Joints, Pose

__version__ = "1.1.5"

__all__ = [
    "FanucRobot",
    "RobotApp",
    "AppResult",
    "MotionTracer",
    "TraceSample",
    "RESERVED",
    "DEFAULT_PORT",
    "LOGGER_PORT",
    "MappdkTransport",
    "Pose",
    "Joints",
    "Alarm",
    "FanucError",
    "ConnectionError_",
    "ProtocolError",
    "CommandError",
    "UnreachableError",
    "MotionSetupError",
    "UnsupportedCommandError",
    "__version__",
]
