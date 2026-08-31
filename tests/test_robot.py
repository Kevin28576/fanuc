"""FanucRobot tests that don't already live in test_protocol.py
(gripper timing) or test_cli.py.

Two techniques:

- For connect()/disconnect()/_send()'s own logic, mock
  ``robot._transport`` (MappdkTransport is already tested for real in
  test_transport.py, no need to re-test it here through a second
  layer of indirection).
- For everything above that (get_curpos, move, the register/gripper
  methods, ...), mock ``robot._send`` directly and check the command
  string it was called with plus how the canned response gets parsed.
  This is the same level ``_send`` sits at in the class: below it is
  "how bytes get to the controller" (transport.py's job, tested
  separately), above it is "what each method means" (this file's job).
"""

from __future__ import annotations

import pytest

from fanuc import FanucRobot
from fanuc.exceptions import ConnectionError_, UnreachableError, UnsupportedCommandError
from fanuc.types import Alarm


class _FakeTransport:
    """Stands in for robot._transport in connect()/_send() tests."""

    def __init__(self, greeting="0:success", send_responses=None, connect_error=None):
        self.greeting = greeting
        self.send_responses = list(send_responses or [])
        self.connect_error = connect_error
        self.connect_calls = 0
        self.send_calls = []
        self.reconnect_calls = 0
        self.disconnect_calls = 0
        self.host = "127.0.0.1"
        self.port = 18735
        self.connected = False

    def connect(self):
        self.connect_calls += 1
        if self.connect_error is not None:
            raise self.connect_error
        self.connected = True
        return self.greeting

    def disconnect(self):
        self.disconnect_calls += 1
        self.connected = False

    def reconnect(self):
        self.reconnect_calls += 1
        self.connected = True
        return self.greeting

    def send(self, command, is_complete=None):
        self.send_calls.append(command)
        if not self.send_responses:
            raise AssertionError("FakeTransport.send called more times than scripted")
        response = self.send_responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


# -- connect / disconnect / _send --------------------------------------------

def test_connect_detects_extended_driver():
    robot = FanucRobot()
    robot._transport = _FakeTransport(send_responses=["0:fanuc-driver 0.2.0"])

    robot.connect()

    assert robot.extended is True
    assert robot.driver_version == "fanuc-driver 0.2.0"


def test_connect_detects_upstream_driver():
    robot = FanucRobot()
    robot._transport = _FakeTransport(send_responses=[UnsupportedCommandError("wrong-command")])

    robot.connect()

    assert robot.extended is False
    assert robot.driver_version is None


def test_max_rdo_num_capped_on_upstream_driver():
    robot = FanucRobot(max_rdo=32)
    robot.extended = False
    assert robot.max_rdo_num == 9  # legacy upstream cap

    robot.extended = True
    assert robot.max_rdo_num == 32


def test_disconnect_delegates_to_transport():
    robot = FanucRobot()
    robot._transport = _FakeTransport()
    robot.disconnect()
    assert robot._transport.disconnect_calls == 1


def test_connected_property_reflects_transport():
    robot = FanucRobot()
    fake = _FakeTransport()
    robot._transport = fake
    assert robot.connected is False
    fake.connected = True
    assert robot.connected is True


def test_repr_shows_model_and_state():
    robot = FanucRobot(model="ER-4iA")
    robot._transport = _FakeTransport()
    assert "disconnected" in repr(robot)
    robot._transport.connected = True
    assert "connected" in repr(robot)
    assert "ER-4iA" in repr(robot)


def test_context_manager_connects_and_disconnects():
    robot = FanucRobot()
    fake = _FakeTransport(send_responses=[UnsupportedCommandError("wrong-command")])
    robot._transport = fake

    with robot as r:
        assert r is robot
        assert fake.connect_calls == 1
    assert fake.disconnect_calls == 1


def test_send_without_auto_reconnect_propagates_connection_error():
    robot = FanucRobot(auto_reconnect=False)
    robot._transport = _FakeTransport(send_responses=[ConnectionError_("dropped")])
    with pytest.raises(ConnectionError_):
        robot._send("curpos")


def test_send_with_auto_reconnect_retries_once():
    robot = FanucRobot(auto_reconnect=True)
    robot._transport = _FakeTransport(
        send_responses=[ConnectionError_("dropped"), "0:x=1.000,y=0,z=0,w=0,p=0,r=0"]
    )
    result = robot._send("curpos")
    assert result == "x=1.000,y=0,z=0,w=0,p=0,r=0"
    assert robot._transport.reconnect_calls == 1


def test_send_raw_passes_the_string_through_unmodified(monkeypatch):
    robot = FanucRobot()
    calls = []
    monkeypatch.setattr(robot, "_send", lambda cmd, retry=True: calls.append((cmd, retry)) or "ok")
    assert robot.send_raw("some:raw:command") == "ok"
    assert calls == [("some:raw:command", False)]


# -- position / power ------------------------------------------------------------

def test_get_curpos(monkeypatch):
    robot = FanucRobot()
    monkeypatch.setattr(robot, "_send", lambda *a, **kw: "x=1.000,y=2.000,z=3.000,w=4.000,p=5.000,r=6.000")
    pose = robot.get_curpos()
    assert pose.to_list() == [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]


def test_get_curjpos(monkeypatch):
    robot = FanucRobot()
    monkeypatch.setattr(robot, "_send", lambda *a, **kw: "j=0.000,j=-30.000,j=0.000,j=0.000,j=-90.000,j=0.000")
    joints = robot.get_curjpos()
    assert joints.to_list() == [0.0, -30.0, 0.0, 0.0, -90.0, 0.0]


def test_get_ins_power_converts_kw_to_w(monkeypatch):
    robot = FanucRobot()
    monkeypatch.setattr(robot, "_send", lambda *a, **kw: "0.175")
    assert robot.get_ins_power() == pytest.approx(175.0)


# -- motion -----------------------------------------------------------------------

def test_move_sends_the_encoded_command(monkeypatch):
    robot = FanucRobot()
    seen = {}

    def _fake_send(cmd, is_complete=None, retry=True):
        seen["cmd"] = cmd
        seen["retry"] = retry
        return "success"

    monkeypatch.setattr(robot, "_send", _fake_send)
    result = robot.move("joint", [0, 0, 0, 0, -90, 0], velocity=50)
    assert result == "success"
    assert seen["cmd"].startswith("movej:0050:")
    assert seen["retry"] is False  # motion commands are never auto-resent


def test_move_joint_and_move_pose_are_aliases(monkeypatch):
    robot = FanucRobot()
    calls = []
    monkeypatch.setattr(robot, "move", lambda move_type, vals, **kw: calls.append((move_type, vals)))
    robot.move_joint([1, 2, 3, 4, 5, 6])
    robot.move_pose([10, 20, 30, 40, 50, 60])
    assert calls == [("joint", [1, 2, 3, 4, 5, 6]), ("pose", [10, 20, 30, 40, 50, 60])]


def test_move_home_uses_configured_home_joints(monkeypatch):
    robot = FanucRobot(home_joints=[1, 2, 3, 4, 5, 6])
    calls = []
    monkeypatch.setattr(robot, "move", lambda move_type, vals, **kw: calls.append((move_type, vals)))
    robot.move_home()
    assert calls == [("joint", [1.0, 2.0, 3.0, 4.0, 5.0, 6.0])]


def test_move_continue_on_error_returns_the_error_instead_of_raising(monkeypatch):
    robot = FanucRobot()

    def _boom(cmd, is_complete=None, retry=True):
        raise UnreachableError("position-is-not-reachable")

    monkeypatch.setattr(robot, "_send", _boom)
    result = robot.move("pose", [9999, 0, 0, 0, 0, 0], continue_on_error=True)
    assert "position-is-not-reachable" in result


def test_move_without_continue_on_error_raises(monkeypatch):
    robot = FanucRobot()

    def _boom(cmd, is_complete=None, retry=True):
        raise UnreachableError("position-is-not-reachable")

    monkeypatch.setattr(robot, "_send", _boom)
    with pytest.raises(UnreachableError):
        robot.move("pose", [9999, 0, 0, 0, 0, 0])


def test_call_prog(monkeypatch):
    robot = FanucRobot()
    seen = {}

    def _fake_send(cmd, retry=True):
        seen["cmd"] = cmd
        return "success"

    monkeypatch.setattr(robot, "_send", _fake_send)
    assert robot.call_prog("MY_PROG") == "success"
    assert seen["cmd"] == "mappdkcall:MY_PROG"


# -- I/O (no extended driver needed) ----------------------------------------------

def test_get_set_rdo(monkeypatch):
    robot = FanucRobot()
    monkeypatch.setattr(robot, "_send", lambda *a, **kw: "1")
    assert robot.get_rdo(7) == 1

    seen = {}
    def _fake_send(cmd, retry=True):
        seen["cmd"] = cmd
        return "success"

    monkeypatch.setattr(robot, "_send", _fake_send)
    robot.set_rdo(7, True)
    assert seen["cmd"] == "setrdo:7:true"


def test_get_set_dout(monkeypatch):
    robot = FanucRobot()
    monkeypatch.setattr(robot, "_send", lambda *a, **kw: "0")
    assert robot.get_dout(1) == 0

    seen = {}
    def _fake_send(cmd, retry=True):
        seen["cmd"] = cmd
        return "success"

    monkeypatch.setattr(robot, "_send", _fake_send)
    robot.set_dout(1, False)
    assert seen["cmd"] == "setdout:00001:false"


def test_set_sys_var(monkeypatch):
    robot = FanucRobot()
    seen = {}
    def _fake_send(cmd, retry=True):
        seen["cmd"] = cmd
        return "success"

    monkeypatch.setattr(robot, "_send", _fake_send)
    robot.set_sys_var("$SHELL_CFG.$JOB_BUSY", True)
    assert seen["cmd"] == "setsysvar:$SHELL_CFG.$JOB_BUSY:T"


# -- extended-driver-only methods --------------------------------------------

@pytest.fixture
def extended_robot():
    robot = FanucRobot()
    robot.extended = True
    return robot


def test_extended_methods_reject_upstream_driver():
    robot = FanucRobot()
    robot.extended = False
    with pytest.raises(UnsupportedCommandError):
        robot.get_reg(1)


def test_get_set_reg(extended_robot, monkeypatch):
    monkeypatch.setattr(extended_robot, "_send", lambda *a, **kw: "5.000000")
    assert extended_robot.get_reg(1) == 5.0

    seen = {}
    def _fake_send(cmd, retry=True):
        seen["cmd"] = cmd
        return "success"

    monkeypatch.setattr(extended_robot, "_send", _fake_send)
    extended_robot.set_reg(1, 100)
    assert seen["cmd"] == "setreg:00001:100"


def test_get_set_preg(extended_robot, monkeypatch):
    monkeypatch.setattr(extended_robot, "_send", lambda *a, **kw: "x=1.000,y=2.000,z=3.000,w=4.000,p=5.000,r=6.000")
    assert extended_robot.get_preg(81).to_list() == [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]

    seen = {}
    def _fake_send(cmd, retry=True):
        seen["cmd"] = cmd
        return "success"

    monkeypatch.setattr(extended_robot, "_send", _fake_send)
    extended_robot.set_preg(81, [1, 2, 3, 4, 5, 6])
    assert seen["cmd"].startswith("setpreg:00081:")


def test_get_din(extended_robot, monkeypatch):
    monkeypatch.setattr(extended_robot, "_send", lambda *a, **kw: "1")
    assert extended_robot.get_din(1) == 1


def test_get_sys_var_and_override(extended_robot, monkeypatch):
    monkeypatch.setattr(extended_robot, "_send", lambda *a, **kw: "100")
    assert extended_robot.get_sys_var("$MCR.$GENOVERRIDE") == 100
    assert extended_robot.get_override() == 100


def test_get_alarm(extended_robot, monkeypatch):
    monkeypatch.setattr(
        extended_robot, "_send",
        lambda *a, **kw: "id=11,sev=2,cause=5,time=123456,prog=MYPROG,msg=SRVO-002 Teach pendant E-stop",
    )
    alarm = extended_robot.get_alarm()
    assert alarm == Alarm(code=11, severity=2, cause_code=5, time=123456, program="MYPROG",
                          message="SRVO-002 Teach pendant E-stop")


def test_set_sys_var_num(extended_robot, monkeypatch):
    seen = {}
    def _fake_send(cmd, retry=True):
        seen["cmd"] = cmd
        return "success"

    monkeypatch.setattr(extended_robot, "_send", _fake_send)
    extended_robot.set_sys_var_num("$MCR.$GENOVERRIDE", 50)
    assert seen["cmd"] == "setsysvarnum:$MCR.$GENOVERRIDE:50"


def test_get_set_sreg(extended_robot, monkeypatch):
    monkeypatch.setattr(extended_robot, "_send", lambda *a, **kw: "hello")
    assert extended_robot.get_sreg(1) == "hello"

    seen = {}
    def _fake_send(cmd, retry=True):
        seen["cmd"] = cmd
        return "success"

    monkeypatch.setattr(extended_robot, "_send", _fake_send)
    extended_robot.set_sreg(1, "hello")
    assert seen["cmd"] == "setsreg:00001:hello"


def test_get_set_jpreg(extended_robot, monkeypatch):
    monkeypatch.setattr(
        extended_robot, "_send",
        lambda *a, **kw: "j=0.000,j=-30.000,j=0.000,j=0.000,j=-90.000,j=0.000",
    )
    assert extended_robot.get_jpreg(90).to_list() == [0.0, -30.0, 0.0, 0.0, -90.0, 0.0]

    seen = {}
    def _fake_send(cmd, retry=True):
        seen["cmd"] = cmd
        return "success"

    monkeypatch.setattr(extended_robot, "_send", _fake_send)
    extended_robot.set_jpreg(90, [0, -30, 0, 0, -90, 0])
    assert seen["cmd"].startswith("setjpreg:00090:6:")


def test_check_joint_legal(extended_robot, monkeypatch):
    monkeypatch.setattr(extended_robot, "_send", lambda *a, **kw: "1")
    result = extended_robot.check_joint([0, -30, 0, 0, -90, 0])
    assert bool(result) is True
    assert result.violations == ()


def test_check_joint_illegal_with_a_diagnosable_axis(extended_robot, monkeypatch):
    monkeypatch.setattr(extended_robot, "_send", lambda *a, **kw: "0")
    result = extended_robot.check_joint([0, 200, 0, 0, -90, 0])  # J2's real limit is way under 200
    assert bool(result) is False
    assert len(result.violations) == 1
    assert result.violations[0].axis == "J2"


def test_check_joint_illegal_pure_coupling_limit(extended_robot, monkeypatch):
    """J_IN_RANGE says illegal, but every axis is individually within
    the static table's range: a pure mechanical-coupling limit the
    table can't diagnose, violations should honestly come back empty
    rather than guessing an axis."""
    monkeypatch.setattr(extended_robot, "_send", lambda *a, **kw: "0")
    result = extended_robot.check_joint([0, 0, 0, 0, -90, 0])
    assert bool(result) is False
    assert result.violations == ()


def test_check_pose(extended_robot, monkeypatch):
    monkeypatch.setattr(extended_robot, "_send", lambda *a, **kw: "1")
    assert extended_robot.check_pose([100, 0, 100, -180, 0, 0]) is True

    monkeypatch.setattr(extended_robot, "_send", lambda *a, **kw: "0")
    assert extended_robot.check_pose([9999, 0, 0, 0, 0, 0]) is False


# -- end effector edge cases not covered by the gripper timing tests -----------

def test_set_ee_do_rejects_an_unknown_ee_do_type():
    robot = FanucRobot()
    robot.ee_DO_type = "bogus"  # bypasses the constructor's validation on purpose
    with pytest.raises(ValueError):
        robot._set_ee_do(1, True)


def test_get_ee_do_rejects_an_unknown_ee_do_type():
    robot = FanucRobot()
    robot.ee_DO_type = "bogus"
    with pytest.raises(ValueError):
        robot._get_ee_do(1)


def test_gripper_without_any_output_number_configured():
    """ee_DO_type set but neither ee_DO_num nor ee_open_num/
    ee_close_num: gripper_travel isn't required in this state (no
    output is actually configured yet per __init__'s check), but
    gripper() itself has nothing to drive and should say so clearly."""
    robot = FanucRobot(ee_DO_type="RDO")
    with pytest.raises(ValueError):
        robot.gripper(True)


def test_get_gripper_without_any_output_number_configured():
    robot = FanucRobot(ee_DO_type="RDO")
    with pytest.raises(ValueError):
        robot.get_gripper()


def test_gripper_and_get_gripper_use_the_do_output_type(monkeypatch):
    """The dual-branch _set_ee_do/_get_ee_do also has a DO path
    (RDO is the only one exercised by test_protocol.py's gripper
    timing tests)."""
    robot = FanucRobot(ee_DO_type="DO", ee_DO_num=3, gripper_travel="0ms")
    seen = {}

    def _fake_send(cmd, retry=True):
        seen["set_cmd"] = cmd
        return "success"

    monkeypatch.setattr(robot, "_send", _fake_send)
    robot.gripper(True)
    assert seen["set_cmd"].startswith("setdout:")

    monkeypatch.setattr(robot, "_send", lambda *a, **kw: "1")
    assert robot.get_gripper() == 1


def test_dual_signal_gripper_property():
    dual = FanucRobot(ee_DO_type="RDO", ee_open_num=7, ee_close_num=8, gripper_travel="500ms")
    assert dual._dual_signal_gripper is True

    single = FanucRobot(ee_DO_type="RDO", ee_DO_num=7, gripper_travel="500ms")
    assert single._dual_signal_gripper is False


def test_check_joint_ignores_an_axis_without_a_limit_table_entry(extended_robot, monkeypatch):
    """A 7th axis (external axis, e.g. a turntable) has no entry in
    joint_limits_deg; the per-axis diagnostic must skip it instead of
    raising a KeyError, leaving the table-covered axes as the only
    possible diagnosis."""
    monkeypatch.setattr(extended_robot, "_send", lambda *a, **kw: "0")
    result = extended_robot.check_joint([0, 200, 0, 0, -90, 0, 999])
    assert bool(result) is False
    assert len(result.violations) == 1
    assert result.violations[0].axis == "J2"


# -- module-level completeness predicates --------------------------------------

def test_complete_fields_predicate():
    from fanuc.robot import _complete_fields

    check = _complete_fields(3)
    assert check("0:1,2,3") is True
    assert check("0:1,2") is False
    assert check("1:some-error") is True  # error responses short-circuit as complete
    assert check("no-colon-yet") is False


def test_complete_joints_predicate():
    from fanuc.robot import _complete_joints

    assert _complete_joints("0:j=0,j=0,j=0,j=0,j=0,j=0") is True
    assert _complete_joints("0:j=0,j=0") is False
    assert _complete_joints("1:some-error") is True
    assert _complete_joints("no-colon-yet") is False
