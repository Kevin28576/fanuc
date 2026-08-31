"""Protocol layer tests. No ROBOGUIDE, no real hardware needed.

Expected strings are checked against driver/mappdk_cmd.kl and
driver/mappdk_ext.kl.
"""

import time

import pytest

from fanuc import protocol as p
from fanuc.exceptions import (
    CommandError,
    MotionSetupError,
    ProtocolError,
    UnreachableError,
    UnsupportedCommandError,
)
from fanuc.types import Joints, Pose


# -- Encoding ----------------------------------------------------------------

def test_move_joint_format():
    """Checked against the fixed-width parsing rule in mappdk_cmd.kl."""
    cmd = p.encode_move("joint", [0, 0, 0, 0, -90, 0], velocity=25,
                        acceleration=100, cnt_val=0, linear=False)
    head, *vals = cmd.split(":")
    assert head == "movej"
    assert cmd.startswith("movej:0025:0100:000:0:6:")
    assert len(vals) == 5 + 6
    # each number is a sign plus 13 characters
    assert all(len(v) == 14 for v in vals[5:])
    # the 13-character width is 6 integer digits + decimal point + 6 fraction digits
    assert vals[5] == "+000000.000000"
    assert vals[9] == "-000090.000000"


def test_move_pose_linear():
    cmd = p.encode_move("pose", [290, 0, 210, -180, 0, 0], linear=True)
    assert cmd.startswith("movep:0025:0100:000:1:6:")


@pytest.mark.parametrize("bad,exc", [
    ({"cnt_val": 101}, ValueError),
    ({"cnt_val": -1}, ValueError),
    ({"velocity": 10000}, ValueError),
])
def test_move_rejects_out_of_range(bad, exc):
    with pytest.raises(exc):
        p.encode_move("joint", [0] * 6, **bad)


def test_move_rejects_unknown_type():
    with pytest.raises(ValueError):
        p.encode_move("linear", [0] * 6)


def test_move_rejects_too_many_axes():
    """The axis count is sent as a single character in mappdk_cmd.kl,
    so more than 9 axes can't be expressed."""
    with pytest.raises(ValueError):
        p.encode_move("joint", [0] * 10)


def test_rdo_rejects_two_digits_on_legacy_driver():
    """The upstream driver reads the number with SUB_STR(cmd, 8, 1);
    10 and above gets truncated to its first digit.

    Upstream doesn't check this, so it would silently operate on the
    wrong RDO. This project's driver fixes that, but a connection to
    the upstream driver still needs to reject it.
    """
    legacy = p.MAX_RDO_NUM_LEGACY
    with pytest.raises(ValueError, match="1-9"):
        p.encode_get_rdo(10, max_num=legacy)
    with pytest.raises(ValueError):
        p.encode_set_rdo(12, True, max_num=legacy)


def test_rdo_encoding():
    assert p.encode_get_rdo(7) == "getrdo:7"
    assert p.encode_set_rdo(7, True) == "setrdo:7:true"
    assert p.encode_set_rdo(7, False) == "setrdo:7:false"


def test_dout_zero_padded():
    """DOUT numbers are zero-padded to 5 digits, per mappdk_cmd.kl."""
    assert p.encode_get_dout(1) == "getdout:00001"
    assert p.encode_set_dout(42, True) == "setdout:00042:true"


def test_sysvar_encoding():
    assert p.encode_set_sys_var("$SHELL_CFG.$JOB_BUSY", True) == \
        "setsysvar:$SHELL_CFG.$JOB_BUSY:T"


def test_colon_rejected_in_names():
    """A colon in a name would break the protocol's framing, so it
    must be rejected before it's ever sent."""
    with pytest.raises(ValueError):
        p.encode_call_prog("PROG:1")
    with pytest.raises(ValueError):
        p.encode_set_sys_var("$A:B", True)


# -- Decoding ------------------------------------------------------------

def test_parse_success():
    assert p.parse_response("0:success") == "success"


def test_parse_message_containing_colon():
    """Upstream uses resp.split(":") with no limit, so this kind of
    response would crash it outright."""
    assert p.parse_response("0:a:b:c") == "a:b:c"


@pytest.mark.parametrize("msg,exc", [
    ("position-is-not-reachable", UnreachableError),
    ("R[81]-was-not-set", MotionSetupError),
    ("PR[81]-was-not-set", MotionSetupError),
    ("wrong-command", UnsupportedCommandError),
    ("something-else", CommandError),
])
def test_error_mapping(msg, exc):
    with pytest.raises(exc):
        p.parse_response(f"1:{msg}")


def test_error_carries_command():
    with pytest.raises(CommandError) as info:
        p.parse_response("1:position-is-not-reachable", command="movej:...")
    assert info.value.command == "movej:..."
    assert info.value.message == "position-is-not-reachable"


@pytest.mark.parametrize("resp", ["", "garbage", "9:unknown-code", "x:y"])
def test_malformed_responses(resp):
    with pytest.raises(ProtocolError):
        p.parse_response(resp)


def test_parse_pose():
    msg = "x=290.000,y=0.000,z=210.000,w=-180.000,p=0.000,r=0.000"
    assert p.parse_pose(msg) == [290.0, 0.0, 210.0, -180.0, 0.0, 0.0]


def test_parse_joints_filters_none():
    """The driver returns j=none for an axis that doesn't exist, per
    mappdk_cmd.kl."""
    msg = "j=0.000,j=0.000,j=0.000,j=0.000,j=-90.000,j=0.000,j=none,j=none"
    assert p.parse_joints(msg) == [0.0, 0.0, 0.0, 0.0, -90.0, 0.0]


def test_parse_rejects_garbage_fields():
    with pytest.raises(ProtocolError):
        p.parse_pose("x=abc,y=0")
    with pytest.raises(ProtocolError):
        p.parse_pose("noequalsign")


# -- Types ------------------------------------------------------------------

def test_pose_roundtrip_and_unpacking():
    pose = Pose.from_list([290, 0, 210, -180, 0, 0])
    x, y, z, w, pp, r = pose  # keeps upstream's sequence-unpacking style
    assert (x, z, w) == (290.0, 210.0, -180.0)
    assert pose.to_list() == [290.0, 0.0, 210.0, -180.0, 0.0, 0.0]
    assert pose.x == 290.0


def test_pose_with_external_axis():
    pose = Pose.from_list([1, 2, 3, 4, 5, 6, 7])
    assert pose.ext == (7.0,)
    assert len(pose) == 7
    assert "E1" in pose.format()


def test_pose_rejects_short_input():
    with pytest.raises(ValueError):
        Pose.from_list([1, 2, 3])


def test_joints_labels():
    joints = Joints.from_list([0, 0, 0, 0, -90, 0])
    assert joints.labels == ("J1", "J2", "J3", "J4", "J5", "J6")
    assert "J5" in joints.format()


# -- port constants -----------------------------------------------------------

def test_port_constants():
    """Ports must match the driver source; this test catches any
    accidental drift."""
    assert p.DEFAULT_PORT == 18735   # mappdk_server.kl
    assert p.LOGGER_PORT == 18736    # mappdk_logger.kl


# -- Extended command encoding ------------------------------------------------

def test_reg_encoding():
    """Numbers are zero-padded to 5 digits, same convention as DOUT
    (mappdk_ext.kl's GET_NUMREG)."""
    assert p.encode_get_reg(1) == "getreg:00001"
    assert p.encode_get_preg(81) == "getpreg:00081"
    assert p.encode_get_din(3) == "getdin:00003"


def test_set_reg_preserves_int_vs_float():
    """The driver decides integer vs. real register from whether the
    value has a decimal point, so the type must be preserved."""
    assert p.encode_set_reg(1, 5) == "setreg:00001:5"
    assert p.encode_set_reg(1, 5.0) == "setreg:00001:5.000000"
    assert p.encode_set_reg(1, -2.5) == "setreg:00001:-2.500000"


def test_set_reg_rejects_bool():
    with pytest.raises(TypeError):
        p.encode_set_reg(1, True)


def test_set_preg_uses_move_value_format():
    cmd = p.encode_set_preg(81, [290, 0, 210, -180, 0, 0])
    head, num, *vals = cmd.split(":")
    assert head == "setpreg"
    assert num == "00081"
    assert len(vals) == 6
    assert all(len(v) == 14 for v in vals)
    assert vals[0] == "+000290.000000"


def test_set_preg_requires_six_values():
    with pytest.raises(ValueError):
        p.encode_set_preg(81, [1, 2, 3])


def test_sysvar_and_misc_encoding():
    assert p.encode_ver() == "ver"
    assert p.encode_get_alarm() == "getalarm"
    assert p.encode_get_sys_var("$MCR.$GENOVERRIDE") == "getsysvar:$MCR.$GENOVERRIDE"


# -- Extended commands: numeric system variable / string register / joint-type position register --
#
# These driver-side routines haven't been verified on real hardware yet
# (see docs/protocol.md); this only tests the offline encoding/decoding
# logic itself.

def test_set_sys_var_num_encoding():
    assert p.encode_set_sys_var_num("$MCR.$GENOVERRIDE", 50) == \
        "setsysvarnum:$MCR.$GENOVERRIDE:50"
    assert p.encode_set_sys_var_num("$SOME.$VAR", 1.5) == \
        "setsysvarnum:$SOME.$VAR:1.500000"


def test_set_sys_var_num_rejects_bool():
    with pytest.raises(TypeError):
        p.encode_set_sys_var_num("$X", True)


def test_sreg_encoding():
    assert p.encode_get_sreg(1) == "getsreg:00001"
    assert p.encode_set_sreg(1, "hello") == "setsreg:00001:hello"


def test_sreg_rejects_colon_in_value():
    with pytest.raises(ValueError):
        p.encode_set_sreg(1, "a:b")


def test_jpreg_encoding():
    assert p.encode_get_jpreg(81) == "getjpreg:00081"

    cmd = p.encode_set_jpreg(81, [0, -30, 0, 0, -90, 0])
    head, num, nj, *vals = cmd.split(":")
    assert head == "setjpreg"
    assert num == "00081"
    assert nj == "6"
    assert len(vals) == 6
    assert vals[0] == "+000000.000000"
    assert vals[1] == "-000030.000000"


def test_jpreg_rejects_empty_or_too_many():
    with pytest.raises(ValueError):
        p.encode_set_jpreg(81, [])
    with pytest.raises(ValueError):
        p.encode_set_jpreg(81, [0] * 10)


def test_rdo_limit_is_conservative_by_default():
    """The default cap lives in MAX_RDO_NUM.

    Accessing an RDO the controller doesn't have aborts MAPPDK_SERVER
    (PRIO-002), so the default is a conservative 8; anyone who needs
    more has to raise it themselves.
    """
    assert p.MAX_RDO_NUM == 8
    assert p.encode_get_rdo(8) == "getrdo:8"
    with pytest.raises(ValueError):
        p.encode_get_rdo(9)
    # once raised, multi-digit numbers can be sent; the driver parses any digit count
    assert p.encode_get_rdo(12, max_num=32) == "getrdo:12"


# -- Extended command decoding -------------------------------------------------

def test_parse_number_keeps_type():
    assert p.parse_number("5") == 5
    assert isinstance(p.parse_number("5"), int)
    assert p.parse_number("5.000000") == 5.0
    assert isinstance(p.parse_number("5.000000"), float)


def test_parse_number_rejects_garbage():
    with pytest.raises(ProtocolError):
        p.parse_number("abc")


def test_parse_alarm():
    code, sev, cause, time_val, prog, text = p.parse_alarm(
        "id=11,sev=2,cause=5,time=123456,prog=MYPROG,msg=SRVO-002 Teach pendant E-stop"
    )
    assert (code, sev, cause, time_val, prog) == (11, 2, 5, 123456, "MYPROG")
    assert text == "SRVO-002 Teach pendant E-stop"


def test_parse_alarm_message_may_contain_commas():
    """The message sits in the last field, so only the first five
    commas are split on."""
    *_, text = p.parse_alarm("id=1,sev=0,cause=0,time=0,prog=,msg=A, B, C")
    assert text == "A, B, C"


def test_parse_alarm_rejects_malformed():
    with pytest.raises(ProtocolError):
        p.parse_alarm("id=1,sev=2")


def test_parse_alarm_strips_trailing_replacement_char():
    """The KAREL side truncates the message byte-wise with SUB_STR,
    which under GB18030 can cut a multi-byte character in half; the
    leftover invalid bytes decode to U+FFFD, and this should be
    stripped so users never see a stray replacement character."""
    *_, text = p.parse_alarm("id=3048,sev=0,cause=0,time=0,prog=,msg=PROG-048 运行时放开�")
    assert text == "PROG-048 运行时放开"
    assert "�" not in text


def test_command_sets_are_disjoint():
    assert not (p.LEGACY_COMMANDS & p.EXTENDED_COMMANDS)
    assert p.SUPPORTED_COMMANDS == p.LEGACY_COMMANDS | p.EXTENDED_COMMANDS


def test_check_joint_encoding():
    cmd = p.encode_check_joint([0, 0, 0, 0, -90, 0])
    assert cmd.startswith("chkjnt:6:")
    head, n, *vals = cmd.split(":")
    assert n == "6"
    assert len(vals) == 6
    assert all(len(v) == 14 for v in vals)


def test_check_joint_rejects_empty():
    with pytest.raises(ValueError):
        p.encode_check_joint([])


def test_check_joint_rejects_too_many_axes():
    with pytest.raises(ValueError):
        p.encode_check_joint([0] * 10)


# -- JointCheckResult / JointViolation --------------------------------------

def test_joint_check_result_bool_and_describe():
    from fanuc.types import JointCheckResult, JointViolation

    from fanuc._i18n import bi

    ok = JointCheckResult(ok=True, values=(0, 0, 0, 0, -90, 0))
    assert bool(ok) is True
    assert ok.describe() == bi("合法", "valid")

    v = JointViolation("J2", 150.0, -110.0, 120.0)
    assert "J2=150.00" in str(v)
    assert "120.00" in str(v)

    bad = JointCheckResult(ok=False, values=(0, 150, 0, 0, -90, 0),
                           violations=(v,))
    assert bool(bad) is False
    assert "J2=150.00" in bad.describe()

    bad_coupling = JointCheckResult(ok=False, values=(0, 0, 0, 0, -90, 0))
    assert bi("耦合", "coupling") in bad_coupling.describe()


def test_default_joint_limits_match_datasheet_totals():
    """Total swing angles checked against the datasheet
    (R3_ER-4iA.pdf); watch this relationship when changing them."""
    from fanuc.limits import DEFAULT_JOINT_LIMITS_DEG as L

    expected_span = {
        "J1": 340.0, "J2": 230.0, "J3": 402.29,
        "J4": 380.0, "J5": 240.0, "J6": 720.0,
    }
    for axis, span in expected_span.items():
        lo, hi = L[axis]
        assert round(hi - lo, 2) == span


def test_check_pose_encoding():
    cmd = p.encode_check_pose([290, 0, 210, -180, 0, 0])
    head, *vals = cmd.split(":")
    assert head == "chkpos"
    assert len(vals) == 6
    assert all(len(v) == 14 for v in vals)


def test_check_pose_requires_six_values():
    with pytest.raises(ValueError):
        p.encode_check_pose([1, 2, 3])


# -- RobotApp ----------------------------------------------------------------
#
# RobotApp's interface mirrors upstream fanucpy: the subclass takes a
# FanucRobot instance in __init__, connect/disconnect are _main()'s own
# responsibility, and run() only wraps exceptions. Tests use a fake
# object in place of a real Robot, no socket, no real hardware needed.

class _FakeRobot:
    """A fake Robot that only records what was called, never touches a socket."""

    def __init__(self, fail_connect: Exception | None = None):
        self._fail_connect = fail_connect
        self.connected = False
        self.disconnect_called = False

    def connect(self):
        if self._fail_connect:
            raise self._fail_connect
        self.connected = True

    def disconnect(self):
        self.disconnect_called = True


def test_robot_app_success():
    from fanuc.app import RobotApp

    class Echo(RobotApp):
        def __init__(self, robot):
            self.robot = robot

        def configure(self):
            self.value = 42

        def _main(self, **kwargs):
            self.robot.connect()
            try:
                return self.value
            finally:
                self.robot.disconnect()

    robot = _FakeRobot()
    app = Echo(robot)
    app.configure()
    result = app.run()

    assert bool(result) is True
    assert result.ok is True
    assert result.message == "success"
    assert result.result == 42
    assert robot.connected is True
    assert robot.disconnect_called is True


def test_robot_app_connect_failure():
    from fanuc.app import RobotApp
    from fanuc.exceptions import ConnectionError_

    class NeverRuns(RobotApp):
        def __init__(self, robot):
            self.robot = robot

        def configure(self):
            pass

        def _main(self, **kwargs):
            self.robot.connect()
            try:
                raise AssertionError("should never get here after a connect failure")
            finally:
                self.robot.disconnect()

    robot = _FakeRobot(fail_connect=ConnectionError_("can't connect"))
    result = NeverRuns(robot).run()

    assert bool(result) is False
    assert "can't connect" in result.message
    # the try block was never entered on a connect failure, so finally never ran either
    assert robot.disconnect_called is False


def test_robot_app_main_failure_still_disconnects():
    from fanuc.app import RobotApp
    from fanuc.exceptions import UnreachableError

    class Boom(RobotApp):
        def __init__(self, robot):
            self.robot = robot

        def configure(self):
            pass

        def _main(self, **kwargs):
            self.robot.connect()
            try:
                raise UnreachableError("unreachable")
            finally:
                self.robot.disconnect()

    robot = _FakeRobot()
    result = Boom(robot).run()

    assert bool(result) is False
    assert "unreachable" in result.message
    assert robot.disconnect_called is True


def test_robot_app_non_fanuc_error_propagates():
    """A bug in the task's own logic (not a robot-communication
    problem) should never be swallowed."""
    from fanuc.app import RobotApp

    class BadCode(RobotApp):
        def __init__(self, robot):
            self.robot = robot

        def configure(self):
            pass

        def _main(self, **kwargs):
            return {}["missing-key"]

    with pytest.raises(KeyError):
        BadCode(_FakeRobot()).run()


# -- Home ---------------------------------------------------------------

def test_default_home_matches_roboguide_panel():
    """Read off ROBOGUIDE's "Current Position" panel on 2026-08-30, ER-4iA."""
    from fanuc.limits import DEFAULT_HOME_JOINTS
    assert DEFAULT_HOME_JOINTS == (0.0, -30.0, 0.0, 0.0, -90.0, 0.0)


def test_robot_home_joints_defaults_and_override():
    from fanuc import FanucRobot
    from fanuc.limits import DEFAULT_HOME_JOINTS

    r = FanucRobot()
    assert r.home_joints == DEFAULT_HOME_JOINTS

    r2 = FanucRobot(home_joints=[1, 2, 3, 4, 5, 6])
    assert r2.home_joints == (1, 2, 3, 4, 5, 6)


# -- Dual-signal gripper ----------------------------------------------------
#
# These tests also take over time.monotonic to simulate a fake clock:
# sleep(s) advances the fake clock by s seconds, while get_rdo/set_rdo
# never let time pass. That's what makes it possible to precisely assert
# "was there enough of a gap (GRIPPER_REST_S) between two signal writes",
# including across two separate calls -- exactly the bug this version
# fixes: the old implementation only rested within a single gripper()
# call, so two separate calls back to back (e.g. gripper(True) then
# gripper(False)) had no protection at all at the seam between them.

class _FakeClock:
    def __init__(self):
        self.now = 0.0

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


def _patch_clock(monkeypatch):
    clock = _FakeClock()
    monkeypatch.setattr(time, "monotonic", clock.monotonic)
    monkeypatch.setattr(time, "sleep", clock.sleep)
    return clock


def test_dual_signal_gripper_close_sequence(monkeypatch):
    """Closing: clear open first, rest a full GRIPPER_REST_S, then set close."""
    from fanuc import FanucRobot

    _patch_clock(monkeypatch)
    calls = []

    r = FanucRobot(ee_DO_type="RDO", ee_open_num=7, ee_close_num=8, gripper_travel="500ms")
    monkeypatch.setattr(r, "set_rdo",
                        lambda n, v: calls.append((time.monotonic(), n, v)))

    r.gripper(True)

    assert [(n, v) for _, n, v in calls] == [(7, False), (8, True)]
    t_open, t_close = calls[0][0], calls[1][0]
    assert t_close - t_open >= FanucRobot.GRIPPER_REST_S


def test_dual_signal_gripper_open_sequence(monkeypatch):
    from fanuc import FanucRobot

    _patch_clock(monkeypatch)
    calls = []

    r = FanucRobot(ee_DO_type="RDO", ee_open_num=7, ee_close_num=8, gripper_travel="500ms")
    monkeypatch.setattr(r, "set_rdo",
                        lambda n, v: calls.append((time.monotonic(), n, v)))

    r.gripper(False)

    assert [(n, v) for _, n, v in calls] == [(8, False), (7, True)]
    t_close, t_open = calls[0][0], calls[1][0]
    assert t_open - t_close >= FanucRobot.GRIPPER_REST_S


def test_dual_signal_gripper_rest_spans_separate_calls(monkeypatch):
    """Regression test: the seam right after gripper(True) followed
    immediately by gripper(False) needs a rest too.

    This is a bug that actually happened: the old implementation only
    protected within a single call (clear signal, rest, set signal);
    the seam between two separate calls had no rest at all. The
    previous call had just set close to True, and the very next call
    immediately set it back to False, with the two writes happening
    almost simultaneously -- violating the datasheet's requirement
    that back-to-back commands too close together can damage the
    internal electronics.
    """
    from fanuc import FanucRobot

    _patch_clock(monkeypatch)
    calls = []

    r = FanucRobot(ee_DO_type="RDO", ee_open_num=7, ee_close_num=8, gripper_travel="500ms")
    monkeypatch.setattr(r, "set_rdo",
                        lambda n, v: calls.append((time.monotonic(), n, v)))

    r.gripper(True)
    r.gripper(False)   # no delay inserted, called right back to back

    # 8 (close) is set True at the end of gripper(True), then set back
    # to False at the start of gripper(False); these two writes must
    # be at least GRIPPER_REST_S apart, and being split across two
    # separate calls must not skip that.
    close_writes = [(t, v) for t, n, v in calls if n == 8]
    assert len(close_writes) == 2
    (t_true, v_true), (t_false, v_false) = close_writes
    assert (v_true, v_false) == (True, False)
    assert t_false - t_true >= FanucRobot.GRIPPER_REST_S

    # for good measure, check every adjacent write pair (regardless of
    # which signal) meets the spacing requirement.
    for (t1, _, _), (t2, _, _) in zip(calls, calls[1:]):
        assert t2 - t1 >= FanucRobot.GRIPPER_REST_S - 1e-9


def test_dual_signal_gripper_state_table(monkeypatch):
    """Checked against the SCHUNK EGP datasheet's state table, not
    guessed combinations."""
    from fanuc import FanucRobot

    r = FanucRobot(ee_DO_type="RDO", ee_open_num=7, ee_close_num=8, gripper_travel="500ms")

    for open_bit, close_bit, expected in [
        (0, 0, "idle"),
        (1, 0, "open"),
        (0, 1, "closed"),
        (1, 1, "reset"),
    ]:
        bits = {7: open_bit, 8: close_bit}
        monkeypatch.setattr(r, "get_rdo", lambda n, bits=bits: bits[n])
        assert r.get_gripper() == expected


def test_single_signal_gripper_unchanged(monkeypatch):
    """With only ee_DO_num given, it takes the original single-signal
    path with no signal-switch rest, but still has to wait
    gripper_travel after sending, for the gripper to finish moving."""
    from fanuc import FanucRobot

    calls = []
    monkeypatch.setattr(time, "sleep",
                        lambda s: calls.append(("sleep", s)))

    r = FanucRobot(ee_DO_type="RDO", ee_DO_num=7, gripper_travel="500ms")
    monkeypatch.setattr(r, "set_rdo", lambda n, v: calls.append(("set", n, v)))

    r.gripper(True)

    assert calls == [("set", 7, True), ("sleep", 0.5)]


def test_gripper_requires_configuration():
    from fanuc import FanucRobot

    r = FanucRobot()
    with pytest.raises(ValueError):
        r.gripper(True)


def test_gripper_reset_requires_dual_signal():
    from fanuc import FanucRobot

    r = FanucRobot(ee_DO_type="RDO", ee_DO_num=7, gripper_travel="500ms")
    with pytest.raises(ValueError):
        r.gripper_reset()


def test_gripper_travel_required_when_gripper_configured():
    """Configuring a gripper output without giving a travel time has
    to fail right at construction, not wait until it's actually used,
    and it can't be papered over with a guessed default."""
    from fanuc import FanucRobot

    with pytest.raises(ValueError, match="gripper_travel"):
        FanucRobot(ee_DO_type="RDO", ee_DO_num=7)

    with pytest.raises(ValueError, match="gripper_travel"):
        FanucRobot(ee_DO_type="RDO", ee_open_num=7, ee_close_num=8)

    # with no gripper output configured at all, gripper_travel isn't required
    FanucRobot(ee_DO_type="RDO")
    FanucRobot()


def test_gripper_waits_travel_time_after_signal(monkeypatch):
    """After sending the signal, it has to wait a full gripper_travel
    before returning, to make sure the gripper actually finished moving."""
    from fanuc import FanucRobot

    _patch_clock(monkeypatch)
    calls = []

    r = FanucRobot(ee_DO_type="RDO", ee_open_num=7, ee_close_num=8,
              gripper_travel="800ms")
    monkeypatch.setattr(r, "set_rdo",
                        lambda n, v: calls.append((time.monotonic(), n, v)))

    t0 = time.monotonic()
    r.gripper(True)
    t1 = time.monotonic()

    assert t1 - t0 >= 0.8 + FanucRobot.GRIPPER_REST_S


def test_gripper_reset_also_waits_travel_time(monkeypatch):
    """gripper_reset() should wait a full gripper_travel before
    returning too, same as gripper(), to make sure the reset actually
    finished."""
    from fanuc import FanucRobot

    _patch_clock(monkeypatch)

    r = FanucRobot(ee_DO_type="RDO", ee_open_num=7, ee_close_num=8,
              gripper_travel="800ms")
    monkeypatch.setattr(r, "set_rdo", lambda n, v: None)

    t0 = time.monotonic()
    r.gripper_reset()
    t1 = time.monotonic()

    assert t1 - t0 >= 0.8 + FanucRobot.GRIPPER_REST_S


# -- Duration string parsing --------------------------------------------------

def test_parse_duration_seconds_and_ms():
    from fanuc.robot import _parse_duration

    assert _parse_duration("2s", "x") == 2.0
    assert _parse_duration("0.5s", "x") == 0.5
    assert _parse_duration("100ms", "x") == 0.1
    assert _parse_duration("1500ms", "x") == 1.5
    assert _parse_duration(" 2 s ", "x") == 2.0  # whitespace allowed


def test_parse_duration_ms_not_matched_by_s_rule():
    """"100ms" must not get matched by the "s" rule first and parsed as 100 seconds."""
    from fanuc.robot import _parse_duration

    assert _parse_duration("100ms", "x") == 0.1
    assert _parse_duration("100ms", "x") != 100.0


def test_parse_duration_rejects_bare_number():
    """Deliberately rejects a bare number; a missing or wrong unit is a common mistake."""
    from fanuc.robot import _parse_duration

    with pytest.raises(ValueError):
        _parse_duration("2", "x")


# -- MotionTracer --------------------------------------------------------------
#
# Same technique as the gripper tests above: the FanucRobot MotionTracer
# builds internally never actually connects; connect/disconnect/get_curpos
# are monkeypatched directly, testing only the polling and sample-collection
# logic itself.

def test_motion_tracer_collects_samples(monkeypatch):
    """Uses an unbounded counter for the fake positions, not a fixed-
    length list: a finite iterator here is a real trap, since if the
    background thread polls faster than the test expects and runs it
    dry, next() raises StopIteration *inside the polling thread*,
    which used to escape uncaught and crash the thread with a stray
    traceback printed straight to stderr instead of failing the test
    cleanly (see test_motion_tracer_survives_unexpected_exception,
    which pins down that this is now handled)."""
    from itertools import count

    from fanuc import MotionTracer
    from fanuc.types import Pose

    tracer = MotionTracer(interval="1ms")
    monkeypatch.setattr(tracer._robot, "connect", lambda: None)
    monkeypatch.setattr(tracer._robot, "disconnect", lambda: None)

    positions = count(10.0, 10.0)
    monkeypatch.setattr(
        tracer._robot, "get_curpos",
        lambda: Pose(x=next(positions), y=0, z=0, w=0, p=0, r=0),
    )

    with tracer:
        tracer.start()
        time.sleep(0.05)
        samples = tracer.stop()

    assert len(samples) >= 2
    assert [s.pose.x for s in samples] == sorted(s.pose.x for s in samples)
    assert all(s.t >= 0 for s in samples)


def test_motion_tracer_requires_connect_before_start(monkeypatch):
    """Calling start() without connect() first fails on the first
    query during polling; the error has to be retrievable through
    stop(), not silently vanish inside the background thread."""
    from fanuc import MotionTracer
    from fanuc.exceptions import ConnectionError_

    tracer = MotionTracer(interval="1ms")

    def _boom():
        raise ConnectionError_("not connected")

    monkeypatch.setattr(tracer._robot, "get_curpos", _boom)

    tracer.start()
    time.sleep(0.02)
    with pytest.raises(ConnectionError_):
        tracer.stop()


def test_motion_tracer_survives_unexpected_exception(monkeypatch, capsys):
    """The polling thread's except clause has to catch more than just
    FanucError. A bug in the query path (or, as happened in practice,
    a test double that runs dry mid-poll) must come back through
    stop() like any other failure, not crash the background thread
    with an uncaught traceback that threading prints straight to
    stderr with no way for the caller to notice."""
    from fanuc import MotionTracer

    tracer = MotionTracer(interval="1ms")

    def _boom():
        raise StopIteration("simulating an exhausted test double, or any non-FanucError bug")

    monkeypatch.setattr(tracer._robot, "get_curpos", _boom)

    tracer.start()
    time.sleep(0.02)
    with pytest.raises(StopIteration):
        tracer.stop()

    # and nothing was printed straight to stderr by the threading
    # module along the way -- the exception was actually caught, not
    # left to crash the thread.
    assert "Exception in thread" not in capsys.readouterr().err


def test_motion_tracer_stop_without_start_returns_empty():
    from fanuc import MotionTracer

    tracer = MotionTracer(interval="1ms")
    assert tracer.stop() == []


def test_motion_tracer_connect_failure_hints_at_s7(monkeypatch):
    """When connecting to S7/logger fails, the error message should
    name MAPPDK_LOGGER specifically, separate from the generic message
    shared with the S8 connection -- otherwise the user has no idea
    which program to check on the TP."""
    from fanuc import MotionTracer
    from fanuc.exceptions import ConnectionError_

    tracer = MotionTracer(port=18736)

    def _boom():
        raise ConnectionError_("cannot connect to 127.0.0.1:18736 -> connection refused")

    monkeypatch.setattr(tracer._robot, "connect", _boom)

    with pytest.raises(ConnectionError_) as exc_info:
        tracer.connect()

    message = str(exc_info.value)
    assert "cannot connect to 127.0.0.1:18736" in message  # original error kept
    assert "MAPPDK_LOGGER" in message                      # the added hint
    assert "18736" in message


def test_motion_tracer_rejects_bare_interval():
    """interval needs a unit too, same rule as gripper_travel."""
    from fanuc import MotionTracer

    with pytest.raises(ValueError):
        MotionTracer(interval="20")


def test_parse_duration_rejects_garbage():
    from fanuc.robot import _parse_duration

    for bad in ("", "abc", "2sec", "s", "-2s"):
        with pytest.raises(ValueError):
            _parse_duration(bad, "x")


def test_parse_duration_rejects_non_string():
    from fanuc.robot import _parse_duration

    with pytest.raises(TypeError):
        _parse_duration(2.0, "x")


def test_gripper_travel_string_parsed_correctly():
    """The string given when constructing FanucRobot gets parsed into
    seconds correctly, and the internal wait actually uses that value."""
    from fanuc import FanucRobot

    r = FanucRobot(ee_DO_type="RDO", ee_DO_num=7, gripper_travel="250ms")
    assert r.gripper_travel == "250ms"          # original string kept
    assert r._gripper_travel_s == 0.25           # parsed into seconds internally


# -- Remaining encoders not otherwise exercised above -------------------------

def test_encode_curpos_curjpos_ins_pwr_exit():
    assert p.encode_curpos() == "curpos"
    assert p.encode_curjpos() == "curjpos"
    assert p.encode_ins_pwr() == "ins_pwr"
    assert p.encode_exit() == "exit"


def test_encode_call_prog_rejects_empty_name():
    with pytest.raises(ValueError):
        p.encode_call_prog("   ")


def test_move_rejects_out_of_range_acceleration_and_cnt():
    with pytest.raises(ValueError):
        p.encode_move("joint", [0], acceleration=10000)
    with pytest.raises(ValueError):
        p.encode_move("joint", [0], cnt_val=101)


def test_move_rejects_empty_vals():
    with pytest.raises(ValueError):
        p.encode_move("joint", [])


# -- Pose / Joints sequence protocol -------------------------------------------

def test_pose_getitem_index_and_slice():
    pose = Pose(1, 2, 3, 4, 5, 6)
    assert pose[0] == 1
    assert pose[1:3] == [2, 3]


def test_joints_iter_len_and_getitem():
    joints = Joints((10.0, 20.0, 30.0))
    assert list(iter(joints)) == [10.0, 20.0, 30.0]
    assert len(joints) == 3
    assert joints[1] == 20.0
    assert joints[0:2] == (10.0, 20.0)


def test_check_rdo_rejects_non_int():
    with pytest.raises(TypeError):
        p.encode_get_rdo(True)  # bool is an int subclass, must still be rejected
    with pytest.raises(TypeError):
        p.encode_get_rdo("1")  # type: ignore[arg-type]


def test_check_dout_rejects_non_int_and_out_of_range():
    with pytest.raises(TypeError):
        p.encode_get_dout(True)
    with pytest.raises(ValueError):
        p.encode_get_dout(0)
    with pytest.raises(ValueError):
        p.encode_get_dout(100000)


def test_set_sys_var_rejects_empty_name():
    with pytest.raises(ValueError):
        p.encode_set_sys_var("   ", True)


def test_check_reg_rejects_non_int_and_out_of_range():
    with pytest.raises(TypeError):
        p.encode_get_reg(True)
    with pytest.raises(ValueError):
        p.encode_get_reg(0)
    with pytest.raises(ValueError):
        p.encode_get_reg(100000)


def test_encode_get_din_rejects_non_int_and_out_of_range():
    with pytest.raises(TypeError):
        p.encode_get_din(True)
    with pytest.raises(ValueError):
        p.encode_get_din(0)
    with pytest.raises(ValueError):
        p.encode_get_din(100000)


def test_encode_get_sys_var_rejects_empty_name_and_colon():
    with pytest.raises(ValueError):
        p.encode_get_sys_var("   ")
    with pytest.raises(ValueError):
        p.encode_get_sys_var("bad:name")


def test_encode_set_sys_var_num_rejects_empty_name():
    with pytest.raises(ValueError):
        p.encode_set_sys_var_num("   ", 1)


def test_parse_pairs_rejects_a_response_with_no_values():
    with pytest.raises(ProtocolError):
        p._parse_labelled("", "cartesian pose")


def test_parse_int_rejects_garbage():
    with pytest.raises(ProtocolError):
        p.parse_int("not-a-number")


def test_parse_power_kw_rejects_garbage():
    with pytest.raises(ProtocolError):
        p.parse_power_kw("not-a-number")


def test_parse_alarm_rejects_a_field_missing_the_equals_sign():
    with pytest.raises(ProtocolError):
        p.parse_alarm("id=1,sev=2,cause=3,time=4,prog=P,BADFIELD")


def test_parse_alarm_rejects_a_non_numeric_field():
    with pytest.raises(ProtocolError):
        p.parse_alarm("id=x,sev=2,cause=3,time=4,prog=P,msg=hello")


def test_robot_app_abstract_method_stub_bodies():
    """configure()/_main() are abstract, but each still has a body (a
    NotImplementedError raise) rather than a bare ``...``, in case a
    subclass calls super().configure()/super()._main() by mistake
    instead of overriding it outright."""
    from fanuc.app import RobotApp

    class Incomplete(RobotApp):
        def __init__(self, robot):
            self.robot = robot

        def configure(self):
            super().configure()

        def _main(self, **kwargs):
            super()._main()

    robot = _FakeRobot()
    app = Incomplete(robot)
    with pytest.raises(NotImplementedError):
        app.configure()
    with pytest.raises(NotImplementedError):
        app._main()
