"""Command-line interface.

    python -m fanuc connect set --host 192.168.1.10 --model ER-4iA
    python -m fanuc pos
    python -m fanuc watch -i 0.2
    python -m fanuc io get rdo 7
    python -m fanuc move joint 0 0 0 0 -90 0 --confirm

Connection flags (--host/--port/--model/...) can be set once with
``connect set`` instead of repeating them on every call; see
``_load_saved_config``.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, cast
import time

from . import __version__
from ._i18n import bi
from .exceptions import ConnectionError_, FanucError
from .robot import FanucRobot

#: Optional dependency (the `complete` extra). None means shell TAB
#: completion is simply unavailable; every other CLI feature works
#: the same either way. Typed as Any (argcomplete ships no stubs)
#: rather than relying on a type: ignore, which would flip between
#: used/unused depending on whether argcomplete happens to be
#: installed in whatever environment mypy runs in.
argcomplete: Any
try:
    import argcomplete as _argcomplete
    argcomplete = _argcomplete
except ImportError:
    argcomplete = None

#: Cursor home + clear screen. Redraws in place, no scrolling.
CLEAR = "\033[H\033[J"

#: Fields ``connect set`` can save and every other subcommand reads
#: defaults from. Each is (argparse flag name without --, hardcoded
#: fallback, type constructor for reading it back off the CLI/JSON).
_CONFIG_FIELDS: tuple[tuple[str, object, type], ...] = (
    ("host", "127.0.0.1", str),
    ("port", 18735, int),
    ("model", "ER-4iA", str),
    ("timeout", 60.0, float),
    ("ee_type", "RDO", str),
    ("ee_num", 7, int),
    ("gripper_travel", None, str),
)


def _config_path() -> Path:
    """Where ``connect set`` persists saved connection defaults.

    ``FANUC_CONFIG_PATH`` overrides this, mainly for tests; otherwise
    it's a fixed file under the user's home directory, shared across
    all projects/shells on the machine.
    """
    override = os.environ.get("FANUC_CONFIG_PATH")
    if override:
        return Path(override)
    return Path.home() / ".fanuc" / "config.json"


def _load_saved_config() -> dict[str, Any]:
    """Reads back whatever ``connect set`` last saved, or {} if
    nothing has been saved (or the file is unreadable/corrupt; a
    broken config file shouldn't block every other command)."""
    path = _config_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _save_config(values: dict[str, Any]) -> None:
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(values, ensure_ascii=False, indent=2), encoding="utf-8")


# --------------------------------------------------------------------------
# Shared
# --------------------------------------------------------------------------

def _add_connection_args(ap: argparse.ArgumentParser) -> None:
    saved = _load_saved_config()

    def default(field: str, fallback: object) -> Any:
        return saved.get(field, fallback)

    ap.add_argument("--host", default=default("host", "127.0.0.1"),
                    help=bi("控制器 IP（預設 127.0.0.1，ROBOGUIDE 固定此值；"
                            "可用 connect set 存起來就不用每次都給）",
                            "controller IP (default 127.0.0.1, fixed for ROBOGUIDE; "
                            "save it once with connect set instead of repeating)"))
    ap.add_argument("--port", type=int, default=default("port", 18735),
                    help=bi("MAPPDK server port（預設 18735）", "MAPPDK server port (default 18735)"))
    ap.add_argument("--model", default=default("model", "ER-4iA"),
                    help=bi("機型名稱，僅供顯示", "model name, display only"))
    ap.add_argument("--timeout", type=float, default=default("timeout", 60.0),
                    help=bi("socket 逾時秒數（預設 60）", "socket timeout in seconds (default 60)"))
    ap.add_argument("--ee-type", default=default("ee_type", "RDO"), choices=["RDO", "DO"],
                    help=bi("末端執行器輸出型態（預設 RDO）", "end effector output type (default RDO)"))
    ap.add_argument("--ee-num", type=int, default=default("ee_num", 7),
                    help=bi("末端執行器輸出編號（預設 7）", "end effector output number (default 7)"))
    ap.add_argument("--gripper-travel", default=default("gripper_travel", None),
                    help=bi("夾爪開闔一次要花多久，如 '2s'、'100ms'。沒給就不會設定末端輸出，"
                            "watch/status 也就不會顯示夾爪狀態",
                            "how long the gripper takes to open/close, e.g. '2s', '100ms'. "
                            "Without it, the end effector output isn't configured and "
                            "watch/status won't show gripper state"))
    ap.add_argument("-v", "--verbose", action="store_true", help=bi("顯示除錯日誌", "show debug logs"))


def _build_robot(args: argparse.Namespace) -> FanucRobot:
    gripper_travel = getattr(args, "gripper_travel", None)
    return FanucRobot(
        host=args.host,
        port=args.port,
        model=args.model,
        # Only configures the end effector output when gripper_travel is
        # given: FanucRobot requires the two together, and the CLI has no
        # safe default travel time to make up on the user's behalf.
        ee_DO_type=args.ee_type if gripper_travel else None,
        ee_DO_num=args.ee_num if gripper_travel else None,
        gripper_travel=gripper_travel,
        timeout=args.timeout,
        auto_reconnect=getattr(args, "reconnect", False),
    )


def _status_block(robot: FanucRobot) -> str:
    """Builds the display content for one full status read.

    Only shows gripper state if the end effector output was actually
    configured (needs --gripper-travel); otherwise get_gripper() would
    just raise.
    """
    pose = robot.get_curpos()
    joints = robot.get_curjpos()

    lines = [
        bi("直角座標 (World, mm / deg):", "cartesian pose (World, mm / deg):"),
        pose.format(),
        "",
        bi("關節座標 (deg):", "joint pose (deg):"),
        joints.format(),
    ]
    if robot.ee_DO_type is not None:
        gripper_label = bi("夾爪", "gripper")
        status_label = bi("狀態", "status")
        lines += ["", f"{gripper_label} ({robot.ee_DO_type}[{robot.ee_DO_num}]) {status_label}: "
                      f"{robot.get_gripper()}"]
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Subcommands
# --------------------------------------------------------------------------

def cmd_pos(args: argparse.Namespace) -> int:
    with _build_robot(args) as robot:
        print(bi(f"已連線: {robot.model} @ {robot.host}:{robot.port}",
                 f"connected: {robot.model} @ {robot.host}:{robot.port}") + "\n")
        print(_status_block(robot))
    return 0


def cmd_watch(args: argparse.Namespace) -> int:
    if args.interval <= 0:
        print(bi("[錯誤] --interval 必須大於 0", "[error] --interval must be > 0"), file=sys.stderr)
        return 2

    if sys.platform == "win32":
        # Empty command, no shell work actually happens; os.system("")
        # is the standard trick for making an older Windows console
        # process ANSI escapes, as a side effect of the call. Every
        # other platform's terminal already handles ANSI natively, so
        # this is gated to win32 instead of paying for a pointless
        # shell spawn on every "fanuc watch" run elsewhere.
        os.system("")

    with _build_robot(args) as robot:
        header = bi(f"已連線: {robot.model} @ {robot.host}:{robot.port}",
                    f"connected: {robot.model} @ {robot.host}:{robot.port}")
        count = 0
        started = time.monotonic()
        try:
            while True:
                count += 1
                elapsed = time.monotonic() - started
                body = _status_block(robot)
                status_line = bi(
                    f"更新 #{count}  已執行 {elapsed:6.1f}s  間隔 {args.interval}s   (Ctrl+C 結束)",
                    f"update #{count}  elapsed {elapsed:6.1f}s  interval {args.interval}s   (Ctrl+C to stop)",
                )
                sys.stdout.write(CLEAR + header + f"\n{status_line}\n\n" + body + "\n")
                sys.stdout.flush()
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\n" + bi("已停止。", "stopped."))
    return 0


def cmd_io(args: argparse.Namespace) -> int:
    with _build_robot(args) as robot:
        if args.io_action == "get":
            if args.kind == "rdo":
                print(robot.get_rdo(args.number))
            else:
                print(robot.get_dout(args.number))
        else:
            value = args.value.lower() in ("1", "true", "on", "yes")
            if args.kind == "rdo":
                robot.set_rdo(args.number, value)
            else:
                robot.set_dout(args.number, value)
            print(f"{args.kind.upper()}[{args.number}] = {value}")
    return 0


def cmd_move(args: argparse.Namespace) -> int:
    if not args.confirm:
        print(bi(
            "[拒絕執行] 這道指令會讓機器人實際移動。\n確認周邊淨空、速度設定合適之後，加上 --confirm 再執行一次。",
            "[refused] this command will move the robot. Confirm clearance and speed, then add --confirm to run it.",
        ), file=sys.stderr)
        return 2

    with _build_robot(args) as robot:
        before = robot.get_curpos()
        print(bi("移動前", "before") + f":\n{before.format()}\n")
        robot.move(
            args.move_type,
            args.values,
            velocity=args.velocity,
            acceleration=args.acceleration,
            cnt_val=args.cnt,
            linear=args.linear,
        )
        after = robot.get_curpos()
        print(bi("移動後", "after") + f":\n{after.format()}")
    return 0


def cmd_call(args: argparse.Namespace) -> int:
    if not args.confirm:
        print(bi(
            "[拒絕執行] 執行 TP 程式可能造成機器人移動。\n確認無誤後加上 --confirm 再執行一次。",
            "[refused] running a TP program may move the robot. Confirm, then add --confirm to run it.",
        ), file=sys.stderr)
        return 2
    with _build_robot(args) as robot:
        print(robot.call_prog(args.program))
    return 0


def cmd_reg(args: argparse.Namespace) -> int:
    with _build_robot(args) as robot:
        if args.reg_action == "get":
            print(robot.get_reg(args.number) if args.kind == "r"
                  else robot.get_preg(args.number).format())
        else:
            if args.kind == "r":
                value = float(args.value) if "." in args.value else int(args.value)
                robot.set_reg(args.number, value)
                print(f"R[{args.number}] = {value}")
            else:
                vals = [float(v) for v in args.value.split(",")]
                robot.set_preg(args.number, vals)
                print(f"PR[{args.number}] = {vals}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Shows the driver version, override speed, and the most recent
    alarm in one shot."""
    with _build_robot(args) as robot:
        print(bi("機型    ", "model  ") + f" : {robot.model}")
        print(bi("連線    ", "address") + f" : {robot.host}:{robot.port}")
        driver = robot.driver_version or bi("上游版本（無擴充指令）", "upstream driver (no extended commands)")
        print(bi("driver  ", "driver ") + f" : {driver}")

        if not robot.extended:
            print("\n" + bi(
                "載入本專案的 driver 後可顯示速度倍率與警報狀態。",
                "load this project's driver to show override and alarm status.",
            ))
            return 0

        print(bi("速度倍率", "override") + f" : {robot.get_override()} %")
        alarm = robot.get_alarm()
        sev_label = bi("嚴重度", "severity")
        print(bi("最近警報", "last alarm") + f" : [{alarm.code}] {sev_label} {alarm.severity}  {alarm.message}")
    return 0


def cmd_din(args: argparse.Namespace) -> int:
    with _build_robot(args) as robot:
        print(robot.get_din(args.number))
    return 0


def cmd_chkjnt(args: argparse.Namespace) -> int:
    with _build_robot(args) as robot:
        result = robot.check_joint(args.values)
        print(result.describe())
    return 0 if result.ok else 1


def cmd_chkpos(args: argparse.Namespace) -> int:
    with _build_robot(args) as robot:
        ok = robot.check_pose(args.values)
        print(bi("到得了", "reachable") if ok else bi("到不了", "unreachable"))
    return 0 if ok else 1


def cmd_power(args: argparse.Namespace) -> int:
    with _build_robot(args) as robot:
        print(f"{robot.get_ins_power():.1f} W")
    return 0


def cmd_connect(args: argparse.Namespace) -> int:
    if args.connect_action == "show":
        saved = _load_saved_config()
        if not saved:
            print(bi("還沒存過連線設定。", "no connection settings saved yet."))
            return 0
        print(bi(f"設定檔: {_config_path()}", f"config file: {_config_path()}"))
        for field, fallback, _ in _CONFIG_FIELDS:
            print(f"  {field} = {saved.get(field, fallback)}")
        return 0

    if args.connect_action == "clear":
        path = _config_path()
        if path.exists():
            path.unlink()
        print(bi("已清除連線設定，之後都會用內建預設值。",
                 "connection settings cleared; commands go back to the built-in defaults."))
        return 0

    # set
    values = {
        "host": args.host,
        "port": args.port,
        "model": args.model,
        "timeout": args.timeout,
        "ee_type": args.ee_type,
        "ee_num": args.ee_num,
        "gripper_travel": args.gripper_travel,
    }
    _save_config(values)
    print(bi(f"已存到 {_config_path()}，之後的指令不用再帶這些連線參數：",
             f"saved to {_config_path()}, no need to repeat these on later commands:"))
    for field, _, _ in _CONFIG_FIELDS:
        print(f"  {field} = {values[field]}")
    return 0


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="fanuc",
        description=bi("與 FANUC 機器人通訊的工具集（MAPPDK 協定）",
                       "tools for talking to a FANUC robot (MAPPDK protocol)"),
    )
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = ap.add_subparsers(dest="command", required=True)

    p_pos = sub.add_parser("pos", help=bi("讀取目前位置", "read the current position"))
    _add_connection_args(p_pos)
    p_pos.set_defaults(func=cmd_pos)

    p_watch = sub.add_parser("watch", help=bi("即時持續顯示位置", "continuously display position"))
    _add_connection_args(p_watch)
    p_watch.add_argument("-i", "--interval", type=float, default=0.5,
                         help=bi("更新間隔秒數（預設 0.5）", "refresh interval in seconds (default 0.5)"))
    p_watch.add_argument("--reconnect", action="store_true",
                         help=bi("連線中斷時自動重連", "auto-reconnect if the connection drops"))
    p_watch.set_defaults(func=cmd_watch)

    p_io = sub.add_parser("io", help=bi("讀寫數位 I/O", "read/write digital I/O"))
    _add_connection_args(p_io)
    p_io.add_argument("io_action", choices=["get", "set"])
    p_io.add_argument("kind", choices=["rdo", "do"])
    p_io.add_argument("number", type=int)
    p_io.add_argument("value", nargs="?", default="false",
                      help=bi("set 時的值：true/false、1/0、on/off", "value for set: true/false, 1/0, on/off"))
    p_io.set_defaults(func=cmd_io)

    p_move = sub.add_parser("move", help=bi("移動機器人（需 --confirm）", "move the robot (needs --confirm)"))
    _add_connection_args(p_move)
    p_move.add_argument("move_type", choices=["joint", "pose"])
    p_move.add_argument("values", type=float, nargs="+", help=bi("目標值", "target values"))
    p_move.add_argument("--velocity", type=int, default=25)
    p_move.add_argument("--acceleration", type=int, default=100)
    p_move.add_argument("--cnt", type=int, default=0, help=bi("CNT 值 0-100", "CNT value 0-100"))
    p_move.add_argument("--linear", action="store_true", help=bi("直線內插", "linear interpolation"))
    p_move.add_argument("--confirm", action="store_true",
                        help=bi("確認要讓機器人實際移動", "confirm the robot should actually move"))
    p_move.set_defaults(func=cmd_move)

    p_call = sub.add_parser("call", help=bi("執行控制器上的 TP 程式（需 --confirm）",
                                            "run a TP program on the controller (needs --confirm)"))
    _add_connection_args(p_call)
    p_call.add_argument("program", help=bi("TP 程式名稱", "TP program name"))
    p_call.add_argument("--confirm", action="store_true")
    p_call.set_defaults(func=cmd_call)

    p_reg = sub.add_parser("reg", help=bi("讀寫暫存器（需擴充 driver）", "read/write registers (needs the extended driver)"))
    _add_connection_args(p_reg)
    p_reg.add_argument("reg_action", choices=["get", "set"])
    p_reg.add_argument("kind", choices=["r", "pr"], help=bi("r=數值暫存器 pr=位置暫存器", "r=numeric register pr=position register"))
    p_reg.add_argument("number", type=int)
    p_reg.add_argument("value", nargs="?", default="0",
                       help=bi("set 時的值。pr 用逗號分隔的 6 個數字",
                               "value for set. For pr, 6 comma-separated numbers"))
    p_reg.set_defaults(func=cmd_reg)

    p_din = sub.add_parser("din", help=bi("讀取數位輸入 DI[n]（需擴充 driver）", "read digital input DI[n] (needs the extended driver)"))
    _add_connection_args(p_din)
    p_din.add_argument("number", type=int)
    p_din.set_defaults(func=cmd_din)

    p_chkjnt = sub.add_parser(
        "chkjnt", help=bi("檢查關節角度是否在軟限位內，不會真的移動（需擴充 driver）",
                          "check whether joint angles are within the soft limits, without moving (needs the extended driver)"))
    _add_connection_args(p_chkjnt)
    p_chkjnt.add_argument("values", type=float, nargs="+", help=bi("J1..Jn 角度", "J1..Jn angles"))
    p_chkjnt.set_defaults(func=cmd_chkjnt)

    p_chkpos = sub.add_parser(
        "chkpos", help=bi("檢查直角座標位置到不到得了，不會真的移動（需擴充 driver）",
                          "check whether a Cartesian position is reachable, without moving (needs the extended driver)"))
    _add_connection_args(p_chkpos)
    p_chkpos.add_argument("values", type=float, nargs=6,
                          metavar=("X", "Y", "Z", "W", "P", "R"))
    p_chkpos.set_defaults(func=cmd_chkpos)

    p_status = sub.add_parser("status", help=bi("顯示 driver 版本、速度倍率與最近警報",
                                                "show the driver version, override speed, and last alarm"))
    _add_connection_args(p_status)
    p_status.set_defaults(func=cmd_status)

    p_power = sub.add_parser("power", help=bi("讀取瞬時消耗功率", "read instantaneous power consumption"))
    _add_connection_args(p_power)
    p_power.set_defaults(func=cmd_power)

    p_connect = sub.add_parser(
        "connect", help=bi("存/看/清除連線設定，之後的指令不用再帶 --host/--port/--model",
                           "save/show/clear connection settings so later commands don't need --host/--port/--model"))
    connect_sub = p_connect.add_subparsers(dest="connect_action", required=True)

    p_connect_set = connect_sub.add_parser("set", help=bi("存起來", "save"))
    _add_connection_args(p_connect_set)
    p_connect_set.set_defaults(func=cmd_connect)

    p_connect_show = connect_sub.add_parser("show", help=bi("看目前存的值", "show the current saved values"))
    p_connect_show.set_defaults(func=cmd_connect)

    p_connect_clear = connect_sub.add_parser("clear", help=bi("清除，之後改用內建預設值", "clear, back to the built-in defaults"))
    p_connect_clear.set_defaults(func=cmd_connect)

    return ap


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    if argcomplete is not None:
        # A no-op on a normal run; only does anything when invoked by
        # the shell's completion machinery (checks for COMP_LINE/etc.
        # itself), so this is safe to call unconditionally whenever
        # argcomplete is installed.
        argcomplete.autocomplete(parser)
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if getattr(args, "verbose", False) else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    try:
        # args.func is set dynamically by argparse's set_defaults(func=...);
        # mypy can't infer the return type is int, so this makes it
        # explicit rather than sprinkling in an arbitrary cast.
        return cast(int, args.func(args))
    except ConnectionError_ as exc:
        print(bi("[錯誤]", "[error]") + f" {exc}", file=sys.stderr)
        print(bi(
            "請確認 ROBOGUIDE 虛擬控制器已開啟，且 TP 上的 MAPPDK 正在執行。設定步驟見 docs/zh/controller-setup.md。",
            "check that the ROBOGUIDE virtual controller is open and MAPPDK is running on the TP. See docs/controller-setup.md.",
        ), file=sys.stderr)
        return 1
    except FanucError as exc:
        # A command-level error's message already explains the cause;
        # tacking on a connection hint here would just confuse.
        print(bi("[錯誤]", "[error]") + f" {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n" + bi("已中斷。", "interrupted."), file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
