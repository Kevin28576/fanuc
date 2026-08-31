"""Command string encoding/decoding.

Doesn't touch sockets, pure string in/out, so it's testable offline.
Format mirrors the KAREL side in mappdk_cmd.kl.

    send:     <command>[:<param>...]\\n
    receive:  <code>:<message>

Code 0 is success, 1 is failure.
"""

from __future__ import annotations

from typing import Sequence

from ._i18n import bi
from .exceptions import (
    CommandError,
    MotionSetupError,
    ProtocolError,
    UnreachableError,
    UnsupportedCommandError,
)

#: Command terminator. The driver splits commands on newlines and also
#: uses it to frame responses.
TERMINATOR = "\n"

#: Main server's port (mappdk_server.kl:29, server tag S8).
DEFAULT_PORT = 18735

#: Second connection's port (mappdk_logger.kl:27, server tag S7).
#:
#: MAPPDK_LOGGER is named "logger" but is actually a copy of
#: MAPPDK_SERVER, with the exact same command set; the only
#: differences are the tag, the port, and not setting UFRAME/UTOOL. It
#: exists to provide a second, independent connection: the driver is
#: synchronous, so the main connection is stuck once it sends a motion
#: command until the move finishes, and this connection can be used to
#: query position in the meantime.
LOGGER_PORT = 18736

SUCCESS_CODE = 0
ERROR_CODE = 1

#: Command set supported by upstream fanucpy's driver, taken from
#: HANDLE_CMD in mappdk_cmd.kl.
LEGACY_COMMANDS = frozenset({
    "curpos",
    "curjpos",
    "ins_pwr",
    "movej",
    "movep",
    "mappdkcall",
    "getrdo",
    "setrdo",
    "getdout",
    "setdout",
    "setsysvar",
    "exit",
})

#: Commands this project adds, implemented in driver/mappdk_ext.kl.
#: Requires loading this project's compiled .pc; the upstream driver
#: replies wrong-command.
EXTENDED_COMMANDS = frozenset({
    "ver",
    "getreg",
    "setreg",
    "getpreg",
    "setpreg",
    "getdin",
    "getsysvar",
    "getalarm",
    "chkjnt",
    "chkpos",
    "setsysvarnum",
    "getsreg",
    "setsreg",
    "getjpreg",
    "setjpreg",
})

SUPPORTED_COMMANDS = LEGACY_COMMANDS | EXTENDED_COMMANDS

#: Version string prefix for this project's driver (VER_INFO in
#: driver/mappdk_ext.kl).
DRIVER_NAME = "fanuc-driver"

#: Fixed zero-padded width for number fields. DOUT follows upstream's
#: convention; the extension commands use the same width.
DOUT_WIDTH = 5
REG_WIDTH = 5

#: Driver error message -> corresponding exception class.
#: Classified by how the caller should handle it, not by the surface
#: text of the error.
_ERROR_MAP: dict[str, type[CommandError]] = {
    "position-is-not-reachable": UnreachableError,
    "R[81]-was-not-set": MotionSetupError,
    "R[82]-was-not-set": MotionSetupError,
    "R[83]-was-not-set": MotionSetupError,
    "PR[81]-was-not-set": MotionSetupError,
    "wrong-command": UnsupportedCommandError,
}

#: Upstream driver's RDO number limit.
#:
#: Upstream reads a single character with SUB_STR(cmd, 8, 1)
#: (mappdk_cmd.kl's GET_RDO / SET_RDO), so numbers 10 and above get
#: truncated to their first digit and silently operate on the wrong
#: RDO without an error. This project's driver reads to the end of the
#: string and doesn't have that problem, but still has to enforce this
#: limit when talking to an upstream driver.
MAX_RDO_NUM_LEGACY = 9

#: Default RDO number limit.
#:
#: Deliberately conservative. Accessing an RDO the controller doesn't
#: have throws PRIO-002 (wrong port number) and aborts the entire
#: MAPPDK_SERVER, requiring a TP RESET and restart to recover. KAREL
#: can't guard against this on its own (GET_PORT_VAL needs the io_rdo
#: constant, and adding the IOSETUP environment would push the
#: directive+environment count past ktrans's limit), so this is
#: enforced here instead.
#:
#: The ER-4iA has 8. For a robot with more, pass a higher max_rdo when
#: constructing FanucRobot.
MAX_RDO_NUM = 8


# --------------------------------------------------------------------------
# Encoding
# --------------------------------------------------------------------------

def encode_curpos() -> str:
    return "curpos"


def encode_curjpos() -> str:
    return "curjpos"


def encode_ins_pwr() -> str:
    return "ins_pwr"


def encode_exit() -> str:
    return "exit"


def encode_call_prog(prog_name: str) -> str:
    """Calls a TP program on the controller."""
    name = prog_name.strip()
    if not name:
        raise ValueError(bi("程式名稱不可為空", "program name cannot be empty"))
    if ":" in name:
        raise ValueError(bi(
            f"程式名稱不可含冒號，會破壞協定框界: {prog_name!r}",
            f"program name cannot contain ':', it breaks protocol framing: {prog_name!r}",
        ))
    return f"mappdkcall:{name}"


def encode_move(
    move_type: str,
    vals: Sequence[float],
    velocity: int = 25,
    acceleration: int = 100,
    cnt_val: int = 0,
    linear: bool = False,
) -> str:
    """Builds a movej / movep command.

    Number format follows the driver's fixed-width rules
    (mappdk_cmd.kl:163 onward): velocity and acceleration are 4 digits
    each, CNT is 3 digits, motion type is 1 digit, axis count is 1
    digit, followed by each value as "sign + 13-character fixed-point
    number" (14 characters total).

    Args:
        move_type: ``joint``/``movej`` for joint space,
            ``pose``/``movep`` for Cartesian space.
        vals: target values. Joint angles per axis, or XYZWPR for
            Cartesian.
        velocity: percent or mm/s, depending on move type.
        acceleration: percent or mm/s^2.
        cnt_val: CNT value 0-100. 0 means exact stop (FINE).
        linear: linear interpolation.
    """
    cmd = _normalise_move_type(move_type)

    velocity = int(velocity)
    acceleration = int(acceleration)
    cnt_val = int(cnt_val)

    if not 0 <= velocity <= 9999:
        raise ValueError(bi(f"速度須為 0-9999，收到 {velocity}", f"velocity must be 0-9999, got {velocity}"))
    if not 0 <= acceleration <= 9999:
        raise ValueError(bi(f"加速度須為 0-9999，收到 {acceleration}", f"acceleration must be 0-9999, got {acceleration}"))
    if not 0 <= cnt_val <= 100:
        raise ValueError(bi(f"CNT 值須為 0-100，收到 {cnt_val}", f"cnt_val must be 0-100, got {cnt_val}"))
    if not vals:
        raise ValueError(bi("目標值不可為空", "vals cannot be empty"))
    if len(vals) > 9:
        # Axis count is sent as a single character (mappdk_cmd.kl:197)
        raise ValueError(bi(f"目標值最多 9 個，收到 {len(vals)} 個", f"at most 9 values, got {len(vals)}"))

    parts = [
        cmd,
        f"{velocity:04}",
        f"{acceleration:04}",
        f"{cnt_val:03}",
        str(int(linear)),
        str(len(vals)),
    ]
    parts.extend(_encode_value(v) for v in vals)
    return ":".join(parts)


def _normalise_move_type(move_type: str) -> str:
    if move_type in ("joint", "movej"):
        return "movej"
    if move_type in ("pose", "movep"):
        return "movep"
    raise ValueError(bi(
        f"動作型態須為 joint/movej 或 pose/movep，收到 {move_type!r}",
        f"move_type must be joint/movej or pose/movep, got {move_type!r}",
    ))


def _encode_value(val: float) -> str:
    """Fixed-point format: sign + 13 characters, e.g. ``+00000290.000000``."""
    body = f"{abs(float(val)):013.6f}"
    sign = "+" if val >= 0 else "-"
    return sign + body


def encode_get_rdo(rdo_num: int, max_num: int = MAX_RDO_NUM) -> str:
    _check_rdo(rdo_num, max_num)
    return f"getrdo:{rdo_num}"


def encode_set_rdo(rdo_num: int, val: bool, max_num: int = MAX_RDO_NUM) -> str:
    _check_rdo(rdo_num, max_num)
    return f"setrdo:{rdo_num}:{_bool_str(val)}"


def _check_rdo(rdo_num: int, max_num: int = MAX_RDO_NUM) -> None:
    if not isinstance(rdo_num, int) or isinstance(rdo_num, bool):
        raise TypeError(bi(f"RDO 編號須為整數，收到 {rdo_num!r}", f"RDO number must be int, got {rdo_num!r}"))
    if not 1 <= rdo_num <= max_num:
        hint_zh, hint_en = "", ""
        if max_num == MAX_RDO_NUM_LEGACY:
            hint_zh = "。控制器上是上游版本的 driver，只取單一字元，編號 10 以上會被截斷成第一位數。載入本專案的 driver 可解除此限制"
            hint_en = ". Controller is running the upstream driver, which only reads one digit; numbers >= 10 get truncated. Load this project's driver to lift the limit"
        raise ValueError(bi(
            f"RDO 編號須為 1-{max_num}，收到 {rdo_num}{hint_zh}",
            f"RDO number must be 1-{max_num}, got {rdo_num}{hint_en}",
        ))


def encode_get_dout(dout_num: int) -> str:
    _check_dout(dout_num)
    return f"getdout:{dout_num:0{DOUT_WIDTH}d}"


def encode_set_dout(dout_num: int, val: bool) -> str:
    _check_dout(dout_num)
    return f"setdout:{dout_num:0{DOUT_WIDTH}d}:{_bool_str(val)}"


def _check_dout(dout_num: int) -> None:
    if not isinstance(dout_num, int) or isinstance(dout_num, bool):
        raise TypeError(bi(f"DOUT 編號須為整數，收到 {dout_num!r}", f"DOUT number must be int, got {dout_num!r}"))
    if not 1 <= dout_num <= 99999:
        raise ValueError(bi(f"DOUT 編號須為 1-99999，收到 {dout_num}", f"DOUT number must be 1-99999, got {dout_num}"))


def encode_set_sys_var(sys_var: str, val: bool) -> str:
    """Sets a boolean system variable. The driver's SET_SYS_VAR only
    handles T/F; numeric variables need the extension command."""
    name = sys_var.strip()
    if not name:
        raise ValueError(bi("系統變數名稱不可為空", "sys_var name cannot be empty"))
    if ":" in name:
        raise ValueError(bi(f"系統變數名稱不可含冒號: {sys_var!r}", f"sys_var name cannot contain ':': {sys_var!r}"))
    return f"setsysvar:{name}:{'T' if val else 'F'}"


def _bool_str(val: bool) -> str:
    return "true" if val else "false"


# --------------------------------------------------------------------------
# Extension commands (driver/mappdk_ext.kl)
#
# Upstream doesn't have these; they need this project's compiled .pc.
# Connecting to an upstream driver raises UnsupportedCommandError.
# --------------------------------------------------------------------------

def encode_ver() -> str:
    """Queries the driver version, used to decide which commands are
    available."""
    return "ver"


def encode_get_reg(reg_num: int) -> str:
    """Reads numeric register R[n]."""
    _check_reg(reg_num, "R")
    return f"getreg:{reg_num:0{REG_WIDTH}d}"


def encode_set_reg(reg_num: int, value: float | int) -> str:
    """Writes numeric register R[n]. The driver decides which kind to
    write based on whether the value has a decimal point; 1 and 1.0
    are different, no normalization is done."""
    _check_reg(reg_num, "R")
    if isinstance(value, bool):
        raise TypeError(bi("暫存器值不可為布林，請用 0/1 或 set_rdo", "register value cannot be bool, use 0/1 or set_rdo"))
    if isinstance(value, int):
        val_str = str(value)
    else:
        val_str = f"{float(value):.6f}"
    return f"setreg:{reg_num:0{REG_WIDTH}d}:{val_str}"


def encode_get_preg(reg_num: int) -> str:
    """Reads position register PR[n]."""
    _check_reg(reg_num, "PR")
    return f"getpreg:{reg_num:0{REG_WIDTH}d}"


def encode_set_preg(reg_num: int, vals: Sequence[float]) -> str:
    """Writes position register PR[n]. Same format as movep; the
    driver keeps the current configuration and only overwrites
    XYZWPR."""
    _check_reg(reg_num, "PR")
    if len(vals) != 6:
        raise ValueError(bi(
            f"位置暫存器需要 6 個值（XYZWPR），收到 {len(vals)} 個",
            f"position register needs 6 values (XYZWPR), got {len(vals)}",
        ))
    body = ":".join(_encode_value(v) for v in vals)
    return f"setpreg:{reg_num:0{REG_WIDTH}d}:{body}"


def _check_reg(reg_num: int, kind: str) -> None:
    if not isinstance(reg_num, int) or isinstance(reg_num, bool):
        raise TypeError(bi(f"{kind} 編號須為整數，收到 {reg_num!r}", f"{kind} number must be int, got {reg_num!r}"))
    if not 1 <= reg_num <= 99999:
        raise ValueError(bi(f"{kind} 編號須為 1-99999，收到 {reg_num}", f"{kind} number must be 1-99999, got {reg_num}"))


def encode_get_din(din_num: int) -> str:
    """Reads digital input DI[n]."""
    if not isinstance(din_num, int) or isinstance(din_num, bool):
        raise TypeError(bi(f"DI 編號須為整數，收到 {din_num!r}", f"DI number must be int, got {din_num!r}"))
    if not 1 <= din_num <= 99999:
        raise ValueError(bi(f"DI 編號須為 1-99999，收到 {din_num}", f"DI number must be 1-99999, got {din_num}"))
    return f"getdin:{din_num:0{DOUT_WIDTH}d}"


def encode_get_sys_var(sys_var: str) -> str:
    """Reads a numeric system variable, e.g. ``$MCR.$GENOVERRIDE``."""
    name = sys_var.strip()
    if not name:
        raise ValueError(bi("系統變數名稱不可為空", "sys_var name cannot be empty"))
    if ":" in name:
        raise ValueError(bi(f"系統變數名稱不可含冒號: {sys_var!r}", f"sys_var name cannot contain ':': {sys_var!r}"))
    return f"getsysvar:{name}"


def encode_get_alarm() -> str:
    """Reads the most recent alarm.

    There's no way to read older entries: live testing showed
    ``ERR_DATA``'s sequence-number parameter doesn't actually select
    which historical entry to read, it always returns the same current
    entry regardless of what's passed in. See docs/protocol.md for the
    full account.
    """
    return "getalarm"


def encode_check_joint(vals: Sequence[float]) -> str:
    """Checks whether a set of joint angles is within the controller's
    soft limits, without actually moving.

    Uses KAREL's built-in J_IN_RANGE, which also accounts for
    mechanical-coupling limits like J2/J3, more accurate than
    maintaining a per-axis limit table, at the cost of not being able
    to query the actual limit values.
    """
    if not vals:
        raise ValueError(bi("關節值不可為空", "joint values cannot be empty"))
    if len(vals) > 9:
        raise ValueError(bi(f"最多 9 軸，收到 {len(vals)} 個", f"at most 9 axes, got {len(vals)}"))
    body = ":".join(_encode_value(v) for v in vals)
    return f"chkjnt:{len(vals)}:{body}"


def encode_check_pose(vals: Sequence[float]) -> str:
    """Checks whether a Cartesian position is reachable, without
    actually moving.

    Uses the same CHECK_EPOS as movep, a built-in already exercised in
    production. Always 6 values (XYZWPR), external axes not supported.
    """
    if len(vals) != 6:
        raise ValueError(bi(
            f"直角座標需要 6 個值（XYZWPR），收到 {len(vals)} 個",
            f"cartesian pose needs 6 values (XYZWPR), got {len(vals)}",
        ))
    body = ":".join(_encode_value(v) for v in vals)
    return f"chkpos:{body}"


def encode_set_sys_var_num(sys_var: str, value: float | int) -> str:
    """Writes a numeric system variable. A different command from
    :func:`encode_set_sys_var`, which only writes booleans."""
    name = sys_var.strip()
    if not name:
        raise ValueError(bi("系統變數名稱不可為空", "sys_var name cannot be empty"))
    if isinstance(value, bool):
        raise TypeError(bi("數值系統變數不可為布林，請用 encode_set_sys_var", "numeric sys_var cannot be bool, use encode_set_sys_var"))
    if isinstance(value, int):
        val_str = str(value)
    else:
        val_str = f"{float(value):.6f}"
    return f"setsysvarnum:{name}:{val_str}"


def encode_get_sreg(reg_num: int) -> str:
    """Reads string register SR[n]."""
    _check_reg(reg_num, "SR")
    return f"getsreg:{reg_num:0{REG_WIDTH}d}"


def encode_set_sreg(reg_num: int, value: str) -> str:
    """Writes string register SR[n]."""
    _check_reg(reg_num, "SR")
    if ":" in value:
        raise ValueError(bi(
            f"字串暫存器的值不可含冒號，會破壞協定框界: {value!r}",
            f"SR value cannot contain ':', it breaks protocol framing: {value!r}",
        ))
    return f"setsreg:{reg_num:0{REG_WIDTH}d}:{value}"


def encode_get_jpreg(reg_num: int) -> str:
    """Reads a joint-type position register. ``getpreg`` only returns
    Cartesian coordinates; use this if the register stores a joint
    position instead."""
    _check_reg(reg_num, "PR")
    return f"getjpreg:{reg_num:0{REG_WIDTH}d}"


def encode_set_jpreg(reg_num: int, vals: Sequence[float]) -> str:
    """Writes a joint-type position register."""
    _check_reg(reg_num, "PR")
    if not vals:
        raise ValueError(bi("關節值不可為空", "joint values cannot be empty"))
    if len(vals) > 9:
        raise ValueError(bi(f"最多 9 軸，收到 {len(vals)} 個", f"at most 9 axes, got {len(vals)}"))
    body = ":".join(_encode_value(v) for v in vals)
    return f"setjpreg:{reg_num:0{REG_WIDTH}d}:{len(vals)}:{body}"


# --------------------------------------------------------------------------
# Decoding
# --------------------------------------------------------------------------

def parse_response(resp: str, command: str | None = None) -> str:
    """Splits ``<code>:<message>`` apart, raising the matching
    exception on failure.

    Upstream uses ``resp.split(":")`` with no split-count limit, so a
    response message containing a colon crashes it with an unpacking
    mismatch; this limits the split to one.

    Returns:
        The message content on success (without the response code).
    """
    text = resp.strip()
    if not text:
        raise ProtocolError(bi("控制器回應為空", "controller response is empty"))

    code_str, sep, msg = text.partition(":")
    if not sep:
        raise ProtocolError(bi(f"回應缺少分隔冒號: {resp!r}", f"response is missing the ':' separator: {resp!r}"))

    try:
        code = int(code_str)
    except ValueError:
        raise ProtocolError(bi(f"回應碼不是整數: {resp!r}", f"response code is not an integer: {resp!r}")) from None

    if code == SUCCESS_CODE:
        return msg
    if code == ERROR_CODE:
        exc_type = _ERROR_MAP.get(msg, CommandError)
        raise exc_type(msg, command)
    raise ProtocolError(bi(f"未知的回應碼 {code}: {resp!r}", f"unknown response code {code}: {resp!r}"))


def parse_pose(msg: str) -> list[float]:
    """Parses ``x=...,y=...,z=...,w=...,p=...,r=...``."""
    return _parse_labelled(msg, bi("直角座標", "cartesian pose"))


def parse_joints(msg: str) -> list[float]:
    """Parses ``j=...,j=...``. The driver returns ``j=none`` for axes
    that don't exist; those get filtered out."""
    parts = [p for p in msg.split(",") if p.strip() and p.strip() != "j=none"]
    return _parse_pairs(parts, bi("關節座標", "joint pose"))


def _parse_labelled(msg: str, what: str) -> list[float]:
    parts = [p for p in msg.split(",") if p.strip()]
    return _parse_pairs(parts, what)


def _parse_pairs(parts: list[str], what: str) -> list[float]:
    vals: list[float] = []
    for part in parts:
        _, sep, raw = part.partition("=")
        if not sep:
            raise ProtocolError(f"{what} {bi('欄位缺少等號', 'field is missing =')}: {part!r}")
        try:
            vals.append(float(raw))
        except ValueError:
            raise ProtocolError(f"{what} {bi('數值無法解析', 'value cannot be parsed')}: {part!r}") from None
    if not vals:
        raise ProtocolError(f"{what} {bi('回應沒有任何數值', 'response has no values')}")
    return vals


def parse_int(msg: str, what: str = "數值") -> int:
    try:
        return int(msg.strip())
    except ValueError:
        raise ProtocolError(f"{what} {bi('無法解析為整數', 'cannot be parsed as int')}: {msg!r}") from None


def parse_power_kw(msg: str) -> float:
    """The driver reports instantaneous power in kW."""
    try:
        return float(msg.strip())
    except ValueError:
        raise ProtocolError(bi(f"功率值無法解析: {msg!r}", f"power value cannot be parsed: {msg!r}")) from None


def parse_alarm(msg: str) -> tuple[int, int, int, int, str, str]:
    """Parses ``id=<code>,sev=<severity>,cause=<cause_code>,time=<time>,
    prog=<program>,msg=<message>``.

    The message may itself contain commas, so the driver puts it in
    the last field; this only splits on the first five commas.

    Returns:
        (code, severity, cause_code, time, program, message)
    """
    parts = msg.split(",", 5)
    if len(parts) != 6:
        raise ProtocolError(bi(f"警報回應格式不符: {msg!r}", f"alarm response format is invalid: {msg!r}"))

    fields = {}
    for part in parts:
        key, sep, raw = part.partition("=")
        if not sep:
            raise ProtocolError(bi(f"警報欄位缺少等號: {part!r}", f"alarm field is missing '=': {part!r}"))
        fields[key.strip()] = raw

    try:
        code = int(fields["id"].strip())
        severity = int(fields["sev"].strip())
        cause_code = int(fields["cause"].strip())
        time_val = int(fields["time"].strip())
    except (KeyError, ValueError):
        raise ProtocolError(bi(f"警報回應欄位無法解析: {msg!r}", f"alarm response field cannot be parsed: {msg!r}")) from None

    program = fields.get("prog", "").strip()
    message = _strip_truncated_char(fields.get("msg", "").strip())
    return code, severity, cause_code, time_val, program, message


def _strip_truncated_char(text: str) -> str:
    """Drops a trailing U+FFFD replacement character.

    The driver's KAREL side truncates long alarm messages by byte
    position, not by character (SUB_STR counts bytes under GB18030,
    where a Chinese character takes 2 bytes). That can cut a
    multi-byte character in half, leaving a dangling invalid byte;
    this module's transport decodes with errors="replace", turning
    that into U+FFFD. Stripping it avoids showing a stray "�" at the
    end of a truncated message.
    """
    return text[:-1] if text.endswith("�") else text


def parse_number(msg: str, what: str = "數值") -> float | int:
    """Parses a register or system variable value.

    The driver returns an integer register without a decimal point and
    a real one with, so the type is preserved here; otherwise
    writing it back could change the register's type.
    """
    text = msg.strip()
    try:
        if "." in text or "e" in text.lower():
            return float(text)
        return int(text)
    except ValueError:
        raise ProtocolError(f"{what} {bi('無法解析為數值', 'cannot be parsed as a number')}: {msg!r}") from None


def parse_version(msg: str) -> str:
    """Parses ``ver``'s response, e.g. ``fanuc-driver 0.2.0``."""
    return msg.strip()
