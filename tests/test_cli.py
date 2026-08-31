"""CLI tests. Offline: FanucRobot.connect/disconnect are monkeypatched
out so nothing ever touches a real socket, matching the technique
already used for the gripper/MotionTracer tests in
test_protocol.py -- patch the specific methods a given command needs,
call fanuc.cli.main() with an explicit argv list, and check stdout
(via capsys) and the return code.
"""

import json

import pytest

from fanuc import FanucRobot
from fanuc._i18n import bi
from fanuc.cli import build_parser, main
from fanuc.exceptions import ConnectionError_, UnsupportedCommandError
from fanuc.types import Alarm, Joints, JointCheckResult, Pose


@pytest.fixture(autouse=True)
def _isolated_config(tmp_path, monkeypatch):
    """Every test gets its own throwaway config file, so nothing here
    ever reads or writes the real ~/.fanuc/config.json."""
    monkeypatch.setenv("FANUC_CONFIG_PATH", str(tmp_path / "config.json"))


@pytest.fixture(autouse=True)
def _no_real_connection(monkeypatch):
    """connect()/disconnect() never touch a socket in any test here;
    individual tests patch whichever read/write methods they exercise
    on top of this."""
    monkeypatch.setattr(FanucRobot, "connect", lambda self: None)
    monkeypatch.setattr(FanucRobot, "disconnect", lambda self: None)


# -- connect set/show/clear --------------------------------------------------

def test_config_path_falls_back_to_home_dir_without_env_override(monkeypatch):
    from pathlib import Path

    from fanuc.cli import _config_path

    monkeypatch.delenv("FANUC_CONFIG_PATH", raising=False)
    assert _config_path() == Path.home() / ".fanuc" / "config.json"


def test_connect_show_before_anything_saved(capsys):
    assert main(["connect", "show"]) == 0
    assert bi("還沒存過連線設定", "no connection settings saved yet") in capsys.readouterr().out


def test_connect_set_then_show_roundtrip(capsys):
    assert main(["connect", "set", "--host", "192.168.1.10", "--port", "9999"]) == 0
    capsys.readouterr()  # discard the "saved to ..." message

    assert main(["connect", "show"]) == 0
    out = capsys.readouterr().out
    assert "host = 192.168.1.10" in out
    assert "port = 9999" in out


def test_connect_set_writes_valid_json(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    monkeypatch.setenv("FANUC_CONFIG_PATH", str(config_path))

    assert main(["connect", "set", "--model", "ER-4iA"]) == 0

    data = json.loads(config_path.read_text(encoding="utf-8"))
    assert data["model"] == "ER-4iA"
    assert data["host"] == "127.0.0.1"  # untouched fields keep their defaults


def test_connect_clear_removes_the_file(tmp_path, monkeypatch, capsys):
    config_path = tmp_path / "config.json"
    monkeypatch.setenv("FANUC_CONFIG_PATH", str(config_path))
    main(["connect", "set", "--host", "10.0.0.1"])
    assert config_path.exists()

    assert main(["connect", "clear"]) == 0
    assert not config_path.exists()
    capsys.readouterr()

    # and later commands go back to the built-in default, not the
    # cleared value
    assert main(["connect", "show"]) == 0
    assert bi("還沒存過連線設定", "no connection settings saved yet") in capsys.readouterr().out


def test_connect_clear_when_nothing_saved_does_not_error(tmp_path, monkeypatch):
    monkeypatch.setenv("FANUC_CONFIG_PATH", str(tmp_path / "does-not-exist.json"))
    assert main(["connect", "clear"]) == 0


def test_saved_config_is_picked_up_as_the_default(capsys):
    """A saved host should show up as --host's default on a later,
    unrelated command, without passing --host again."""
    main(["connect", "set", "--host", "10.20.30.40"])
    capsys.readouterr()

    args = build_parser().parse_args(["pos"])
    assert args.host == "10.20.30.40"


def test_corrupt_config_file_falls_back_to_defaults(tmp_path, monkeypatch, capsys):
    config_path = tmp_path / "config.json"
    config_path.write_text("{not valid json", encoding="utf-8")
    monkeypatch.setenv("FANUC_CONFIG_PATH", str(config_path))

    assert main(["connect", "show"]) == 0
    assert bi("還沒存過連線設定", "no connection settings saved yet") in capsys.readouterr().out


# -- --version ----------------------------------------------------------------

def test_version_flag_exits_zero(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["--version"])
    assert exc_info.value.code == 0
    assert "fanuc" in capsys.readouterr().out


# -- pos / watch ----------------------------------------------------------------

def test_cmd_pos_without_gripper_configured(monkeypatch, capsys):
    monkeypatch.setattr(FanucRobot, "get_curpos", lambda self: Pose.from_list([1, 2, 3, 4, 5, 6]))
    monkeypatch.setattr(FanucRobot, "get_curjpos", lambda self: Joints.from_list([0, 0, 0, 0, -90, 0]))

    assert main(["pos"]) == 0
    out = capsys.readouterr().out
    assert bi("已連線", "connected") in out
    assert bi("夾爪", "gripper") not in out  # --gripper-travel wasn't given


def test_cmd_pos_with_gripper_configured(monkeypatch, capsys):
    monkeypatch.setattr(FanucRobot, "get_curpos", lambda self: Pose.from_list([1, 2, 3, 4, 5, 6]))
    monkeypatch.setattr(FanucRobot, "get_curjpos", lambda self: Joints.from_list([0, 0, 0, 0, -90, 0]))
    monkeypatch.setattr(FanucRobot, "get_gripper", lambda self: "open")

    assert main(["pos", "--gripper-travel", "500ms"]) == 0
    assert bi("夾爪", "gripper") in capsys.readouterr().out


def test_cmd_watch_rejects_non_positive_interval(capsys):
    assert main(["watch", "-i", "0"]) == 2
    assert bi("必須", "must be") in capsys.readouterr().err


def test_cmd_watch_stops_cleanly_on_ctrl_c(monkeypatch, capsys):
    monkeypatch.setattr(FanucRobot, "get_curpos", lambda self: Pose.from_list([0, 0, 0, 0, 0, 0]))
    monkeypatch.setattr(FanucRobot, "get_curjpos", lambda self: Joints.from_list([0, 0, 0, 0, 0, 0]))

    def _sleep_then_interrupt(seconds):
        raise KeyboardInterrupt

    monkeypatch.setattr("time.sleep", _sleep_then_interrupt)

    assert main(["watch", "-i", "0.01"]) == 0
    assert bi("已停止", "stopped") in capsys.readouterr().out


# -- io ------------------------------------------------------------------------

def test_cmd_io_get_rdo(monkeypatch, capsys):
    monkeypatch.setattr(FanucRobot, "get_rdo", lambda self, n: 1)
    assert main(["io", "get", "rdo", "7"]) == 0
    assert capsys.readouterr().out.strip() == "1"


def test_cmd_io_get_do(monkeypatch, capsys):
    monkeypatch.setattr(FanucRobot, "get_dout", lambda self, n: 0)
    assert main(["io", "get", "do", "1"]) == 0
    assert capsys.readouterr().out.strip() == "0"


def test_cmd_io_set_do(monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(FanucRobot, "set_dout", lambda self, n, v: calls.append((n, v)))
    assert main(["io", "set", "do", "1", "true"]) == 0
    assert calls == [(1, True)]
    assert "DO[1] = True" in capsys.readouterr().out


def test_cmd_io_set_rdo(monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(FanucRobot, "set_rdo", lambda self, n, v: calls.append((n, v)))
    assert main(["io", "set", "rdo", "7", "false"]) == 0
    assert calls == [(7, False)]
    assert "RDO[7] = False" in capsys.readouterr().out


# -- move / call: the --confirm gate --------------------------------------------

def test_cmd_move_refuses_without_confirm(monkeypatch, capsys):
    called = []
    monkeypatch.setattr(FanucRobot, "move", lambda self, *a, **kw: called.append((a, kw)))
    assert main(["move", "joint", "0", "0", "0", "0", "-90", "0"]) == 2
    assert called == []
    assert bi("拒絕", "refused") in capsys.readouterr().err


def test_cmd_move_runs_with_confirm(monkeypatch, capsys):
    monkeypatch.setattr(FanucRobot, "get_curpos", lambda self: Pose.from_list([0, 0, 0, 0, 0, 0]))
    called = []
    monkeypatch.setattr(FanucRobot, "move", lambda self, *a, **kw: called.append((a, kw)))

    assert main(["move", "joint", "0", "0", "0", "0", "-90", "0", "--confirm"]) == 0
    assert called == [(("joint", [0.0, 0.0, 0.0, 0.0, -90.0, 0.0]),
                       {"velocity": 25, "acceleration": 100, "cnt_val": 0, "linear": False})]


def test_cmd_call_refuses_without_confirm(monkeypatch, capsys):
    called = []
    monkeypatch.setattr(FanucRobot, "call_prog", lambda self, name: called.append(name))
    assert main(["call", "MY_PROG"]) == 2
    assert called == []


def test_cmd_call_runs_with_confirm(monkeypatch, capsys):
    monkeypatch.setattr(FanucRobot, "call_prog", lambda self, name: "success")
    assert main(["call", "MY_PROG", "--confirm"]) == 0
    assert "success" in capsys.readouterr().out


# -- reg -------------------------------------------------------------------------

def test_cmd_reg_get_r(monkeypatch, capsys):
    monkeypatch.setattr(FanucRobot, "get_reg", lambda self, n: 42)
    assert main(["reg", "get", "r", "1"]) == 0
    assert capsys.readouterr().out.strip() == "42"


def test_cmd_reg_set_r_integer_vs_real(monkeypatch):
    calls = []
    monkeypatch.setattr(FanucRobot, "set_reg", lambda self, n, v: calls.append(v))
    main(["reg", "set", "r", "1", "5"])
    main(["reg", "set", "r", "1", "5.5"])
    assert calls == [5, 5.5]
    assert isinstance(calls[0], int)
    assert isinstance(calls[1], float)


def test_cmd_reg_get_pr(monkeypatch, capsys):
    monkeypatch.setattr(FanucRobot, "get_preg", lambda self, n: Pose.from_list([1, 2, 3, 4, 5, 6]))
    assert main(["reg", "get", "pr", "81"]) == 0
    assert "1.000" in capsys.readouterr().out


def test_cmd_reg_set_pr(monkeypatch):
    calls = []
    monkeypatch.setattr(FanucRobot, "set_preg", lambda self, n, vals: calls.append((n, vals)))
    main(["reg", "set", "pr", "81", "1,2,3,4,5,6"])
    assert calls == [(81, [1.0, 2.0, 3.0, 4.0, 5.0, 6.0])]


# -- din / chkjnt / chkpos / power ----------------------------------------------

def test_cmd_din(monkeypatch, capsys):
    monkeypatch.setattr(FanucRobot, "get_din", lambda self, n: 0)
    assert main(["din", "1"]) == 0
    assert capsys.readouterr().out.strip() == "0"


def test_cmd_chkjnt_legal_returns_zero(monkeypatch):
    result = JointCheckResult(ok=True, values=(0, 0, 0, 0, -90, 0))
    monkeypatch.setattr(FanucRobot, "check_joint", lambda self, vals: result)
    assert main(["chkjnt", "0", "0", "0", "0", "-90", "0"]) == 0


def test_cmd_chkjnt_illegal_returns_one(monkeypatch):
    result = JointCheckResult(ok=False, values=(0, 200, 0, 0, -90, 0))
    monkeypatch.setattr(FanucRobot, "check_joint", lambda self, vals: result)
    assert main(["chkjnt", "0", "200", "0", "0", "-90", "0"]) == 1


def test_cmd_chkpos_reachable_returns_zero(monkeypatch, capsys):
    monkeypatch.setattr(FanucRobot, "check_pose", lambda self, vals: True)
    assert main(["chkpos", "100", "0", "100", "-180", "0", "0"]) == 0
    assert bi("到得了", "reachable") in capsys.readouterr().out


def test_cmd_chkpos_unreachable_returns_one(monkeypatch):
    monkeypatch.setattr(FanucRobot, "check_pose", lambda self, vals: False)
    assert main(["chkpos", "9999", "0", "0", "0", "0", "0"]) == 1


def test_cmd_power(monkeypatch, capsys):
    monkeypatch.setattr(FanucRobot, "get_ins_power", lambda self: 123.456)
    assert main(["power"]) == 0
    assert "123.5 W" in capsys.readouterr().out


# -- status ----------------------------------------------------------------------

def test_cmd_status_upstream_driver(monkeypatch, capsys):
    # driver_version/extended are set inside connect() on a real run
    # (via the ver-command version check), not class attributes, so
    # they're set here the same way: by overriding connect() to set
    # them on self, not by patching the class attribute directly
    # (which __init__ would just overwrite again anyway).
    def _connect_as_upstream(self):
        self.driver_version = None
        self.extended = False

    monkeypatch.setattr(FanucRobot, "connect", _connect_as_upstream)
    assert main(["status"]) == 0
    out = capsys.readouterr().out
    assert "ER-4iA" in out
    assert "%" not in out  # upstream driver: no override percentage printed


def test_cmd_status_extended_driver(monkeypatch, capsys):
    def _connect_as_extended(self):
        self.driver_version = "fanuc-driver 0.2.0"
        self.extended = True

    monkeypatch.setattr(FanucRobot, "connect", _connect_as_extended)
    monkeypatch.setattr(FanucRobot, "get_override", lambda self: 100)
    monkeypatch.setattr(
        FanucRobot, "get_alarm",
        lambda self: Alarm(code=0, severity=0, cause_code=0, time=0, program="", message="reset"),
    )
    assert main(["status"]) == 0
    out = capsys.readouterr().out
    assert "100" in out
    assert "reset" in out


# -- main()'s exception handling --------------------------------------------

def test_main_reports_connection_error(monkeypatch, capsys):
    def _boom(self):
        raise ConnectionError_("cannot connect to 127.0.0.1:18735")

    monkeypatch.setattr(FanucRobot, "connect", _boom)
    assert main(["pos"]) == 1
    err = capsys.readouterr().err
    assert "cannot connect" in err
    assert "controller-setup" in err  # the hint pointing at setup docs


def test_main_reports_fanuc_error_without_connection_hint(monkeypatch, capsys):
    def _boom(self):
        raise UnsupportedCommandError("wrong-command", command="getreg:00001")

    monkeypatch.setattr(FanucRobot, "get_reg", lambda self, n: _boom(self))
    assert main(["reg", "get", "r", "1"]) == 1
    err = capsys.readouterr().err
    assert "wrong-command" in err
    assert "controller-setup" not in err  # command-level errors don't get the connection hint


def test_main_reports_keyboard_interrupt(monkeypatch, capsys):
    def _boom(self):
        raise KeyboardInterrupt

    monkeypatch.setattr(FanucRobot, "get_curpos", _boom)
    assert main(["pos"]) == 130
