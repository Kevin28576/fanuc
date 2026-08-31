"""Robot API.

Method names match upstream fanucpy (get_curpos, move, gripper, etc.),
so old code runs with just an import change. Also adds a context
manager, auto-reconnect, named coordinate types, and exception
classification.
"""

from __future__ import annotations

import logging
import re
import time
from types import TracebackType
from typing import Any, Callable, Literal, Sequence, Type

from . import limits, protocol as p
from ._i18n import bi
from .exceptions import ConnectionError_, FanucError, UnsupportedCommandError
from .transport import MappdkTransport
from .types import Alarm, JointCheckResult, Joints, JointViolation, Pose

logger = logging.getLogger(__name__)

#: Duration string format: "2s", "0.5s", "100ms", a number plus a
#: unit, whitespace allowed in between. "ms" must be matched before
#: "s", otherwise "100ms" gets misread by the "s" rule first.
_DURATION_RE = re.compile(r"^\s*([0-9]*\.?[0-9]+)\s*(ms|s)\s*$")


def _parse_duration(value: str, what: str) -> float:
    """Converts a string like ``"2s"``, ``"100ms"`` into seconds.

    Only accepts a string with a unit, not a bare number: a missing
    or wrong unit is a common source of bugs, better to force it to be
    explicit.
    """
    if not isinstance(value, str):
        raise TypeError(bi(
            f"{what} 要是帶單位的字串，例如 '2s'、'100ms'，收到 {value!r}",
            f"{what} must be a string with a unit, e.g. '2s', '100ms', got {value!r}",
        ))
    m = _DURATION_RE.match(value)
    if not m:
        raise ValueError(bi(
            f"{what} 格式不對：{value!r}。要用數字加單位，例如 '2s'、'0.5s'、'100ms'",
            f"{what} format is invalid: {value!r}. Use a number plus unit, e.g. '2s', '0.5s', '100ms'",
        ))
    num, unit = m.groups()
    seconds = float(num)
    return seconds / 1000 if unit == "ms" else seconds

#: Controller resources the driver overwrites. Numbers are hard-coded
#: in mappdk_server.kl's CONST and in mappdk_cmd.kl's motion routines;
#: update this alongside any change there.
#:
#: uframe / utool are set when MAPPDK_SERVER starts, not at move time.
RESERVED = {
    "uframe": 8,
    "utool": 1,
    "velocity_reg": 81,
    "acceleration_reg": 82,
    "cnt_reg": 83,
    "position_reg": 81,
}


class FanucRobot:
    """A MAPPDK connection to a FANUC controller.

    Example::

        with FanucRobot(host="127.0.0.1") as robot:
            print(robot.get_curpos().format())

    Args:
        host: controller IP. Always 127.0.0.1 for the ROBOGUIDE virtual
            controller.
        port: MAPPDK server port. Upstream's default of 18375 is a
            typo; the driver actually uses 18735 (mappdk_server.kl:29).
            Pass ``protocol.LOGGER_PORT`` (18736) to connect to the
            second connection, used to query position while a move is
            in progress.
        model: model name, display and logging only.
        ee_DO_type: end effector output type, ``RDO`` or ``DO``.
        ee_DO_num: end effector output number. Used for a
            single-signal gripper: one True/False signal maps
            directly to open/close. Tied to the actual wiring; it
            differs by gripper and by wiring scheme, there's no
            "default that's just right" number; see
            ``ee_open_num``/``ee_close_num`` below.
        ee_open_num: the "open" signal number for a dual-signal
            gripper (e.g. a pneumatic gripper like the SCHUNK EGP,
            where open and close are two independent signals, not one
            signal's polarity). When given together with
            ``ee_close_num``, ``gripper()`` switches to the two-signal
            protocol and ``ee_DO_num`` is ignored.
        ee_close_num: the "close" signal number for a dual-signal
            gripper.
        gripper_travel: how long the gripper actually takes to open or
            close, a string with a unit, e.g. ``"2s"``, ``"0.5s"``,
            ``"100ms"``; doesn't accept a bare number, a missing or
            wrong unit is a common source of bugs, better to force it
            explicit. ``gripper()`` waits this long after sending the
            signal before returning, so that by the time the caller's
            next action runs (e.g. moving away with a part), the
            gripper has actually finished.
            This is a different thing from ``GRIPPER_REST_S``:
            ``GRIPPER_REST_S`` is the electrical rest time between
            signal changes, roughly the same across this class of
            pneumatic gripper; travel time is how long the jaws
            physically take to move, which depends on gripper size, air
            pressure, and stroke length, different for every unit,
            with no universally safe default. **Once any gripper output
            is configured (``ee_DO_num`` or
            ``ee_open_num``/``ee_close_num``), this value is required
            and omitting it raises immediately**: check your
            gripper's datasheet, or measure a real open/close cycle,
            and fill in the actual number.
        timeout: socket timeout in seconds. Motion commands block
            until the move completes.
        auto_reconnect: automatically reconnect and resend once if the
            connection drops. Only safe for query commands; motion
            commands are never auto-resent, to avoid running the same
            move twice.
        encoding: alarm messages the controller returns use the
            controller interface language's encoding: GB18030 for a
            Simplified Chinese controller. Use shift_jis for a Japanese
            one.
        max_rdo: RDO number upper bound, defaults to 8 (how many the
            ER-4iA has). Accessing an RDO the controller doesn't have
            aborts MAPPDK_SERVER, requiring a TP RESET and restart, so
            it's better to keep this conservative.
        joint_limits_deg: static per-axis limit table used for
            diagnostics when ``check_joint()`` fails, defaulting to the
            real numbers read off the TP on the verification ER-4iA
            (see ``limits.DEFAULT_JOINT_LIMITS_DEG``). Diagnostic aid
            only, not the source of truth for legality; pass your own
            controller's actual numbers when switching robots.
        home_joints: the joint angles ``move_home()`` moves to,
            defaulting to the official home pose read from ROBOGUIDE's
            "当前位置" panel (see ``limits.DEFAULT_HOME_JOINTS``). Pass
            your own home pose when switching robots.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = p.DEFAULT_PORT,
        model: str = "FANUC",
        ee_DO_type: str | None = None,
        ee_DO_num: int | None = None,
        ee_open_num: int | None = None,
        ee_close_num: int | None = None,
        gripper_travel: str | None = None,
        timeout: float = 60.0,
        auto_reconnect: bool = False,
        encoding: str = "gb18030",
        max_rdo: int = p.MAX_RDO_NUM,
        joint_limits_deg: dict[str, tuple[float, float]] | None = None,
        home_joints: Sequence[float] | None = None,
    ):
        self.model = model
        self.ee_DO_type = ee_DO_type
        self.ee_DO_num = ee_DO_num
        self.ee_open_num = ee_open_num
        self.ee_close_num = ee_close_num

        gripper_configured = (
            ee_DO_num is not None
            or (ee_open_num is not None and ee_close_num is not None)
        )
        if gripper_configured and gripper_travel is None:
            raise ValueError(bi(
                "設定了夾爪輸出（ee_DO_num 或 ee_open_num/ee_close_num）"
                "但沒有指定 gripper_travel。每顆夾爪開闔一次要花多久都不一樣，"
                "沒有安全預設值，請對照規格書或實測填寫，格式如 '2s'、'100ms'",
                "gripper output is configured (ee_DO_num or ee_open_num/ee_close_num) "
                "but gripper_travel is missing. Travel time varies per gripper with no safe "
                "default; check the datasheet or measure it, e.g. '2s', '100ms'",
            ))
        #: Raw string (something like ``"2s"``), None when no gripper
        #: is configured.
        self.gripper_travel = gripper_travel
        #: Internal value parsed into seconds; gripper() actually
        #: passes this to time.sleep().
        self._gripper_travel_s = (
            _parse_duration(gripper_travel, "gripper_travel")
            if gripper_travel is not None else None
        )

        #: Timestamp (time.monotonic()) of the last gripper signal
        #: write, used by _write_gripper_signal() to track the gap
        #: between writes; see that method's docstring.
        self._last_gripper_write: float | None = None
        self.auto_reconnect = auto_reconnect
        self._max_rdo = max_rdo
        self.joint_limits_deg = (
            dict(joint_limits_deg) if joint_limits_deg is not None
            else dict(limits.DEFAULT_JOINT_LIMITS_DEG)
        )
        self.home_joints = (
            tuple(home_joints) if home_joints is not None
            else limits.DEFAULT_HOME_JOINTS
        )
        #: Driver version string; None for the upstream driver
        #: (detected in connect()).
        self.driver_version: str | None = None
        #: Whether the controller is running this project's extended
        #: driver.
        self.extended: bool = False
        self._transport = MappdkTransport(
            host=host, port=port, timeout=timeout, encoding=encoding)

    # -- connection ---------------------------------------------------------

    @property
    def host(self) -> str:
        return self._transport.host

    @property
    def port(self) -> int:
        return self._transport.port

    @property
    def connected(self) -> bool:
        return self._transport.connected

    def connect(self) -> None:
        greeting = self._transport.connect()
        # The greeting is also <code>:<message>; a parse failure means
        # the peer isn't a MAPPDK server.
        p.parse_response(greeting, command="<connect>")
        self._detect_driver()
        driver = self.driver_version or bi("上游版本", "upstream driver")
        logger.info(f"已連線 {self.model} @ {self.host}:{self.port}（driver: {driver}）"
                    f" / connected {self.model} @ {self.host}:{self.port} (driver: {driver})")

    def _detect_driver(self) -> None:
        """Asks the driver version to decide whether extension
        commands are usable.

        The upstream driver doesn't recognize ver and replies
        wrong-command. Checking this up front lets later calls to
        extension methods give a direct reason, and also decides which
        RDO number limit to apply.
        """
        try:
            self.driver_version = p.parse_version(
                self._send(p.encode_ver(), retry=False)
            )
            self.extended = True
        except UnsupportedCommandError:
            self.driver_version = None
            self.extended = False

    @property
    def max_rdo_num(self) -> int:
        """RDO number upper bound.

        The smaller of max_rdo and what the driver supports. The
        upstream driver only reads a single character, so it's capped
        at 9 when connected to that version.
        """
        if self.extended:
            return self._max_rdo
        return min(self._max_rdo, p.MAX_RDO_NUM_LEGACY)

    def _require_extended(self, feature: str) -> None:
        if not self.extended:
            raise UnsupportedCommandError(bi(
                f"{feature} 需要本專案擴充的 driver，控制器上目前是上游版本。"
                "請載入 driver/ 目錄編譯出的 .pc，見 docs/zh/controller-setup.md",
                f"{feature} requires this project's extended driver; the controller is "
                "running the upstream driver. Load the .pc built from driver/, "
                "see docs/controller-setup.md",
            ), command=feature)

    def disconnect(self) -> None:
        self._transport.disconnect()

    def __enter__(self) -> "FanucRobot":
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
        return f"<FanucRobot {self.model} {self.host}:{self.port} {state}>"

    # -- command send/receive ------------------------------------------------

    def _send(
        self,
        command: str,
        is_complete: Callable[[str], bool] | None = None,
        retry: bool = True,
    ) -> str:
        """Sends a command and returns the message content on success.

        Args:
            retry: allow reconnecting and resending if the connection
                drops. Motion commands must pass False.
        """
        try:
            raw = self._transport.send(command, is_complete=is_complete)
        except ConnectionError_:
            if not (self.auto_reconnect and retry):
                raise
            logger.warning(bi("連線中斷，重連後重送", "connection dropped, reconnecting and resending") + ": %s", command)
            self._transport.reconnect()
            raw = self._transport.send(command, is_complete=is_complete)

        return p.parse_response(raw, command=command)

    def send_raw(self, command: str) -> str:
        """Sends an arbitrary command string, for trying out new
        commands after extending the KAREL driver.

        Returns:
            The message content on success.
        """
        return self._send(command, retry=False)

    # -- position queries -----------------------------------------------------

    def get_curpos(self) -> Pose:
        """Reads the current Cartesian position (TCP in World frame)."""
        msg = self._send("curpos", is_complete=_complete_fields(6))
        return Pose.from_list(p.parse_pose(msg))

    def get_curjpos(self) -> Joints:
        """Reads the current joint angles."""
        msg = self._send("curjpos", is_complete=_complete_joints)
        return Joints.from_list(p.parse_joints(msg))

    def get_ins_power(self) -> float:
        """Reads instantaneous power consumption.

        Returns:
            Watts. The driver reports kW; this converts to W to match
            upstream's behavior.
        """
        msg = self._send(p.encode_ins_pwr())
        return p.parse_power_kw(msg) * 1000

    # -- motion ---------------------------------------------------------------

    def move(
        self,
        move_type: Literal["joint", "pose", "movej", "movep"],
        vals: Sequence[float],
        velocity: int = 25,
        acceleration: int = 100,
        cnt_val: int = 0,
        linear: bool = False,
        continue_on_error: bool = False,
    ) -> str:
        """Moves the robot, blocking until the move completes.

        Motion commands are never auto-reconnected/resent, to avoid
        running the same move twice.

        Args:
            move_type: ``joint`` for joint space, ``pose`` for
                Cartesian space.
            vals: target values.
            velocity: percent or mm/s.
            acceleration: percent or mm/s^2.
            cnt_val: CNT value 0-100, 0 means exact stop.
            linear: linear interpolation.
            continue_on_error: when True, turns a failure reported by
                the controller into a return value instead of an
                exception.
        """
        cmd = p.encode_move(
            move_type,
            vals,
            velocity=velocity,
            acceleration=acceleration,
            cnt_val=cnt_val,
            linear=linear,
        )
        logger.info(f"移動 {move_type} 目標={list(vals)} 速度={velocity}"
                    f" / move {move_type} target={list(vals)} velocity={velocity}")

        if continue_on_error:
            try:
                return self._send(cmd, retry=False)
            except FanucError as exc:
                logger.warning(bi("動作失敗（已忽略）", "move failed (ignored)") + ": %s", exc)
                return str(exc)
        return self._send(cmd, retry=False)

    def move_joint(self, vals: Sequence[float], **kwargs: Any) -> str:
        """Joint-space move. Alias for ``move("joint", ...)``."""
        return self.move("joint", vals, **kwargs)

    def move_pose(self, vals: Sequence[float], **kwargs: Any) -> str:
        """Cartesian move. Alias for ``move("pose", ...)``."""
        return self.move("pose", vals, **kwargs)

    def move_home(self, **kwargs: Any) -> str:
        """Moves to ``home_joints`` (given when constructing
        FanucRobot, defaults to the official home pose)."""
        return self.move("joint", list(self.home_joints), **kwargs)

    def call_prog(self, prog_name: str) -> str:
        """Runs a TP program on the controller, blocking until it
        finishes."""
        return self._send(p.encode_call_prog(prog_name), retry=False)

    # -- I/O --------------------------------------------------------------

    def get_rdo(self, rdo_num: int) -> int:
        """Reads an RDO. The number limit depends on the driver
        version, see max_rdo_num."""
        msg = self._send(p.encode_get_rdo(rdo_num, self.max_rdo_num))
        return p.parse_int(msg, f"RDO[{rdo_num}]")

    def set_rdo(self, rdo_num: int, val: bool) -> str:
        """Sets an RDO."""
        return self._send(
            p.encode_set_rdo(rdo_num, val, self.max_rdo_num), retry=False)

    def get_dout(self, dout_num: int) -> int:
        """Reads a DO."""
        msg = self._send(p.encode_get_dout(dout_num))
        return p.parse_int(msg, f"DO[{dout_num}]")

    def set_dout(self, dout_num: int, val: bool) -> str:
        """Sets a DO."""
        return self._send(p.encode_set_dout(dout_num, val), retry=False)

    def set_sys_var(self, sys_var: str, val: bool) -> str:
        """Sets a boolean system variable. Numeric variables need the
        extended driver."""
        return self._send(p.encode_set_sys_var(sys_var, val), retry=False)

    # -- registers and status (needs the extended driver) --------------------

    def get_reg(self, reg_num: int) -> float | int:
        """Reads R[n]. Returns int for an integer register, float for
        a real one."""
        self._require_extended("get_reg")
        msg = self._send(p.encode_get_reg(reg_num))
        return p.parse_number(msg, f"R[{reg_num}]")

    def set_reg(self, reg_num: int, value: float | int) -> str:
        """Writes R[n]. int writes an integer register, float writes a
        real one.

        1 and 1.0 have different effects; that's the driver's
        behavior.
        """
        self._require_extended("set_reg")
        return self._send(p.encode_set_reg(reg_num, value), retry=False)

    def get_preg(self, reg_num: int) -> Pose:
        """Reads position register PR[n]."""
        self._require_extended("get_preg")
        msg = self._send(p.encode_get_preg(reg_num), is_complete=_complete_fields(6))
        return Pose.from_list(p.parse_pose(msg))

    def set_preg(self, reg_num: int, vals: Sequence[float]) -> str:
        """Writes PR[n], needs 6 values (XYZWPR).

        The driver keeps the current position's configuration and only
        overwrites these six values.
        """
        self._require_extended("set_preg")
        return self._send(p.encode_set_preg(reg_num, vals), retry=False)

    def get_din(self, din_num: int) -> int:
        """Reads DI[n]. The upstream driver can only read DO."""
        self._require_extended("get_din")
        msg = self._send(p.encode_get_din(din_num))
        return p.parse_int(msg, f"DI[{din_num}]")

    def get_sys_var(self, sys_var: str) -> float | int:
        """Reads a numeric system variable, e.g.
        ``$MCR.$GENOVERRIDE``."""
        self._require_extended("get_sys_var")
        msg = self._send(p.encode_get_sys_var(sys_var))
        return p.parse_number(msg, sys_var)

    def get_override(self) -> int:
        """Reads the speed override (%)."""
        return int(self.get_sys_var("$MCR.$GENOVERRIDE"))

    def get_alarm(self) -> Alarm:
        """Reads the most recent alarm.

        No known way to read older entries yet: live testing showed
        passing different values into ``ERR_DATA``'s sequence-number
        parameter always returned the same current entry (verified by
        cross-checking against the TP's alarm history screen, which
        clearly has distinct entries at different positions). This may
        just be the wrong usage rather than a hard limit. See
        docs/protocol.md for the full account.
        """
        self._require_extended("get_alarm")
        msg = self._send(p.encode_get_alarm())
        code, severity, cause_code, time_val, program, message = p.parse_alarm(msg)
        return Alarm(
            code=code,
            severity=severity,
            cause_code=cause_code,
            time=time_val,
            program=program,
            message=message,
        )

    def set_sys_var_num(self, sys_var: str, value: float | int) -> str:
        """Writes a numeric system variable.

        A different command from :meth:`set_sys_var`, which can only
        write booleans.
        """
        self._require_extended("set_sys_var_num")
        return self._send(p.encode_set_sys_var_num(sys_var, value), retry=False)

    def get_sreg(self, reg_num: int) -> str:
        """Reads string register SR[n]."""
        self._require_extended("get_sreg")
        return self._send(p.encode_get_sreg(reg_num))

    def set_sreg(self, reg_num: int, value: str) -> str:
        """Writes string register SR[n]."""
        self._require_extended("set_sreg")
        return self._send(p.encode_set_sreg(reg_num, value), retry=False)

    def get_jpreg(self, reg_num: int) -> Joints:
        """Reads a joint-type position register.

        ``get_preg`` only returns Cartesian coordinates; use this if
        the register stores a joint position instead.
        """
        self._require_extended("get_jpreg")
        msg = self._send(p.encode_get_jpreg(reg_num), is_complete=_complete_joints)
        return Joints.from_list(p.parse_joints(msg))

    def set_jpreg(self, reg_num: int, vals: Sequence[float]) -> str:
        """Writes a joint-type position register."""
        self._require_extended("set_jpreg")
        return self._send(p.encode_set_jpreg(reg_num, vals), retry=False)

    def check_joint(self, vals: Sequence[float]) -> JointCheckResult:
        """Checks whether a set of joint angles is within the
        controller's soft limits, without actually moving.

        Legality comes from KAREL's built-in J_IN_RANGE (CHECK_JOINT in
        driver/mappdk_ext.kl), the controller's own logic, which also
        accounts for mechanical-coupling limits like J2/J3. This part
        is never wrong; it's the sole source of truth.

        On failure, ``joint_limits_deg`` is additionally checked per
        axis; the returned ``violations`` is only a "probably this
        axis" diagnostic hint, not the source of truth. If J_IN_RANGE
        says invalid but every axis is individually within range,
        ``violations`` will be empty, meaning it's a pure coupling
        limit.

        Returns:
            A JointCheckResult, usable directly as a bool
            (``if robot.check_joint(...)``), or inspect
            ``.violations``/``.describe()`` for diagnostic detail.
        """
        self._require_extended("check_joint")
        msg = self._send(p.encode_check_joint(vals))
        ok = msg.strip() == "1"

        violations: tuple[JointViolation, ...] = ()
        if not ok:
            found = []
            for i, v in enumerate(vals, 1):
                axis = f"J{i}"
                bounds = self.joint_limits_deg.get(axis)
                if bounds is None:
                    continue
                lower, upper = bounds
                if not (lower <= v <= upper):
                    found.append(JointViolation(axis, v, lower, upper))
            violations = tuple(found)

        return JointCheckResult(ok=ok, values=tuple(vals), violations=violations)

    def check_pose(self, vals: Sequence[float]) -> bool:
        """Checks whether a Cartesian position is reachable, without
        actually moving.

        Uses the same CHECK_EPOS as ``move_pose()`` for reachability
        (CHECK_POSE in driver/mappdk_ext.kl), a built-in already
        exercised by movep in production, not something new and
        untested.

        No per-axis diagnostic here: an unreachable Cartesian position
        is usually due to no inverse-kinematics solution or a
        configuration conflict, and can't be broken down per axis the
        way joint angles can.
        """
        self._require_extended("check_pose")
        msg = self._send(p.encode_check_pose(vals))
        return msg.strip() == "1"

    # -- end effector -------------------------------------------------------
    #
    # Both wiring schemes are supported:
    #   single-signal: one output's True/False maps directly to open/close.
    #   dual-signal: open and close are independent outputs (e.g. a
    #       pneumatic gripper like the SCHUNK EGP), not one signal's
    #       polarity, and switching between them needs a minimum rest
    #       time; switching too fast can damage the gripper's internal
    #       electronics. This is a real, common constraint of pneumatic
    #       grippers, not a rule this package invented. Which scheme is
    #       used depends on whether ee_DO_num or
    #       ee_open_num/ee_close_num was given when constructing
    #       FanucRobot.

    #: Minimum rest time between dual-signal gripper writes.
    #: Taken from the SCHUNK EGP series gripper's open/close command
    #: manual: sending two commands back to back too quickly can damage
    #: the internal electronics; the documented minimum is 15ms, this
    #: uses 20ms for a little margin. Other gripper models may spec a
    #: different value; adjust to match your gripper's manual.
    GRIPPER_REST_S = 0.02

    def _write_gripper_signal(self, num: int, value: bool) -> None:
        """Writes a gripper signal, first making sure at least
        ``GRIPPER_REST_S`` has passed since the last write.

        The rest time governs the gap between signal changes, not the
        steps within a single call: if it were only enforced inside
        gripper() itself (clear the old signal, rest, set the new one),
        two separate calls (e.g. gripper(True) immediately followed by
        gripper(False)) would still switch too fast at the boundary
        between them: the first call just set some signal True, and the
        very next call sets it back False right after, with no rest in
        between. This tracks a "global last write time" instead, so
        every pair of signal writes is at least GRIPPER_REST_S apart,
        whether within the same call or across separate calls.
        """
        if self._last_gripper_write is not None:
            elapsed = time.monotonic() - self._last_gripper_write
            remaining = self.GRIPPER_REST_S - elapsed
            if remaining > 0:
                time.sleep(remaining)
        self._set_ee_do(num, value)
        self._last_gripper_write = time.monotonic()

    def _set_ee_do(self, num: int, value: bool) -> str:
        if self.ee_DO_type == "RDO":
            return self.set_rdo(num, value)
        if self.ee_DO_type == "DO":
            return self.set_dout(num, value)
        raise ValueError(bi(
            f"ee_DO_type 須為 RDO 或 DO，收到 {self.ee_DO_type!r}",
            f"ee_DO_type must be RDO or DO, got {self.ee_DO_type!r}",
        ))

    def _get_ee_do(self, num: int) -> int:
        if self.ee_DO_type == "RDO":
            return self.get_rdo(num)
        if self.ee_DO_type == "DO":
            return self.get_dout(num)
        raise ValueError(bi(
            f"ee_DO_type 須為 RDO 或 DO，收到 {self.ee_DO_type!r}",
            f"ee_DO_type must be RDO or DO, got {self.ee_DO_type!r}",
        ))

    def _require_ee_configured(self) -> None:
        if self.ee_DO_type is None:
            raise ValueError(bi(
                "未設定末端執行器輸出。建構 FanucRobot 時請指定 ee_DO_type"
                "（RDO 或 DO），並依接法指定 ee_DO_num（單訊號）或"
                " ee_open_num/ee_close_num（雙訊號）",
                "end effector output not configured. Pass ee_DO_type (RDO or DO) when "
                "constructing FanucRobot, plus ee_DO_num (single-signal) or "
                "ee_open_num/ee_close_num (dual-signal)",
            ))

    @property
    def _dual_signal_gripper(self) -> bool:
        return self.ee_open_num is not None and self.ee_close_num is not None

    def _dual_signal_pins(self) -> tuple[int, int] | None:
        """Returns ``(open_num, close_num)`` for a dual-signal setup,
        otherwise None.

        Split into this small helper for type narrowing: mypy can't
        infer from the ``_dual_signal_gripper`` property that
        ``self.ee_open_num``/``self.ee_close_num`` are non-None at the
        call site, so returning them as local variables is what lets
        the rest of the code get a properly narrowed ``int`` instead of
        ``int | None``.
        """
        if self.ee_open_num is not None and self.ee_close_num is not None:
            return self.ee_open_num, self.ee_close_num
        return None

    def gripper(self, value: bool) -> None:
        """Opens or closes the gripper, waiting ``gripper_travel``
        before returning so the gripper finishes its stroke.

        Dual-signal setup (both ``ee_open_num``/``ee_close_num``
        given):
            Sets the other signal False first, rests ``GRIPPER_REST_S``
            seconds, then sets the target signal True. The order and
            rest time follow the SCHUNK EGP's open/close command
            manual, not an arbitrary design.

        Single-signal setup (only ``ee_DO_num``):
            Sets the signal directly to ``value``.

        After sending the signal and before returning, this also waits
        ``gripper_travel`` (the gripper's actual travel time, required
        when constructing FanucRobot), so that by the time this
        function returns, the gripper has genuinely finished
        opening/closing, and the caller's next action (e.g. moving away
        with a part) doesn't happen while it's still mid-stroke.
        """
        self._require_ee_configured()

        pins = self._dual_signal_pins()
        if pins is not None:
            open_num, close_num = pins
            if value:  # close
                self._write_gripper_signal(open_num, False)
                self._write_gripper_signal(close_num, True)
            else:  # open
                self._write_gripper_signal(close_num, False)
                self._write_gripper_signal(open_num, True)
        else:
            if self.ee_DO_num is None:
                raise ValueError(bi(
                    "設定了 ee_DO_type 但沒有 ee_DO_num，也沒有"
                    " ee_open_num/ee_close_num，不知道要控制哪個輸出",
                    "ee_DO_type is set but neither ee_DO_num nor "
                    "ee_open_num/ee_close_num is given, don't know which output to drive",
                ))
            self._set_ee_do(self.ee_DO_num, value)

        assert self._gripper_travel_s is not None  # guaranteed set above whenever configured
        time.sleep(self._gripper_travel_s)

    def gripper_reset(self) -> None:
        """Resets a gripper alarm (dual-signal setup only).

        Per the SCHUNK EGP's state table, both the open and close
        signals True at the same time means "reset alarm", not "open
        and close simultaneously".

        Waits ``gripper_travel`` before returning, same as
        :meth:`gripper`: resetting is itself a physical action the
        gripper takes time to complete, so the same guarantee applies:
        by the time this returns, the gripper has actually finished.
        """
        self._require_ee_configured()
        pins = self._dual_signal_pins()
        if pins is None:
            raise ValueError(bi(
                "gripper_reset() 只適用雙訊號接法（ee_open_num/ee_close_num）",
                "gripper_reset() only applies to the dual-signal setup (ee_open_num/ee_close_num)",
            ))
        open_num, close_num = pins
        self._write_gripper_signal(open_num, True)
        self._write_gripper_signal(close_num, True)

        assert self._gripper_travel_s is not None  # guaranteed set above whenever configured
        time.sleep(self._gripper_travel_s)

    def get_gripper(self) -> str | int:
        """Reads the gripper's current state.

        Dual-signal setup: returns one of ``"open"``, ``"closed"``,
        ``"idle"``, ``"reset"``, per the SCHUNK EGP's state table.
        Single-signal setup: returns the raw 0/1.
        """
        self._require_ee_configured()

        pins = self._dual_signal_pins()
        if pins is not None:
            open_num, close_num = pins
            open_bit = self._get_ee_do(open_num)
            close_bit = self._get_ee_do(close_num)
            return {
                (0, 0): "idle",
                (1, 0): "open",
                (0, 1): "closed",
                (1, 1): "reset",
            }[(open_bit, close_bit)]

        if self.ee_DO_num is None:
            raise ValueError(bi("設定了 ee_DO_type 但沒有 ee_DO_num", "ee_DO_type is set but ee_DO_num is missing"))
        return self._get_ee_do(self.ee_DO_num)


# --------------------------------------------------------------------------
# Response completeness checks
#
# The driver's response has no terminator, so completeness can only be
# judged from content. These predicates are handed to the transport
# layer, which uses them to know when to keep reading.
# --------------------------------------------------------------------------

def _complete_fields(n: int) -> Callable[[str], bool]:
    """The response should contain n comma-separated fields, or be an
    error message."""

    def check(text: str) -> bool:
        if not text.startswith("0:"):
            return ":" in text  # an error response has no field structure
        return text.count(",") >= n - 1

    return check


def _complete_joints(text: str) -> bool:
    """Axis count varies by mechanism; at least 6 axes are expected."""
    if not text.startswith("0:"):
        return ":" in text
    return text.count(",") >= 5
