# Extended commands

Added by this project in `driver/mappdk_ext.kl`; needs this project's
compiled `.pc` loaded to work. The upstream driver replies
`wrong-command` for these.

| Command | Params | Response | Method |
| --- | --- | --- | --- |
| `ver` | none | `fanuc-driver 0.2.0` | sent automatically on connect |
| `getreg` | `:<5-digit zero-padded>` | number | `get_reg()` |
| `setreg` | `:<5-digit zero-padded>:<value>` | `success` | `set_reg()` |
| `getpreg` | `:<5-digit zero-padded>` | same as `curpos` | `get_preg()` |
| `setpreg` | `:<5-digit zero-padded>:<6 values>` | `success` | `set_preg()` |
| `getdin` | `:<5-digit zero-padded>` | `0` / `1` | `get_din()` |
| `getsysvar` | `:<var name>` | number | `get_sys_var()` |
| `getalarm` | none | `id=..,sev=..,cause=..,time=..,prog=..,msg=..` | `get_alarm()` |
| `chkjnt` | `:<axis count>:<N values>` | `0` / `1` | `check_joint()` |
| `chkpos` | `:<6 values>` | `0` / `1` | `check_pose()` |
| `setsysvarnum` | `:<var name>:<value>` | `success` | `set_sys_var_num()` |
| `getsreg` | `:<5-digit zero-padded>` | string | `get_sreg()` |
| `setsreg` | `:<5-digit zero-padded>:<value>` | `success` | `set_sreg()` |
| `getjpreg` | `:<5-digit zero-padded>` | same as `curjpos` | `get_jpreg()` |
| `setjpreg` | `:<5-digit zero-padded>:<axis count>:<N values>` | `success` | `set_jpreg()` |

## Real-hardware verification status

`setsysvarnum`, `getsreg`/`setsreg`, `getjpreg`/`setjpreg` have all
been verified on real hardware and are safe to use. `getalarm` can
only read the most recent alarm, not history, details below.

## `setreg` / `getreg`

Whether the value has a decimal point decides whether it's written as
an integer or real register, so `1` and `1.0` are different. The
Python side distinguishes them with `int` / `float` and doesn't
normalize.

## `setpreg` / `getpreg`

Same value format as `movep`. The driver keeps the current position's
configuration and only overwrites the six XYZWPR values. If the
configuration was never initialized, later motion can fail to find a
solution.

## `getsysvar`

Tries reading as an integer first, then as a real on failure. Override
speed, UFRAME/UTOOL numbers, and the like all go through this instead
of a dedicated routine per variable.

## `getalarm`

**Can only read the most recent alarm, not history.** `ERR_DATA`'s
parameter formally looks like an input sequence number, but testing
showed passing different numbers in always returns the same entry; the
full debugging story behind this is in
[debugging notes](debugging-notes.md#alarm-history-cant-be-read). That
approach has since been removed; to see full alarm history, go
directly to the TP's `報警` → `履歷` screen for now.

The message can contain commas, so it's the last field, and parsing
only splits on the first five commas. `ERR_DATA` returns 7 fields at
once; besides code/severity/message, `cause` (cause code), `time`
(timestamp), and `prog` (the program running when it fired) come
along too, and `FanucRobot.get_alarm()` returns them as a named
`Alarm` type. `time`'s actual unit and epoch haven't been checked
against official documentation; treat it as an opaque number, don't
use it for date arithmetic. Example at
[examples/alarm_status.py](../../examples/alarm_status.py).

## `chkjnt`

Uses KAREL's built-in `J_IN_RANGE`, not a self-maintained table of
angle limits. The upside is it accounts for mechanical-coupling limits
like J2/J3 too, since it's the controller's own judgment logic; the
downside is it can only answer "is this position legal", not what the
actual limit values are. A pure query, never moves the robot.

`J_IN_RANGE` needs the `JOINTPOS6` type, not the generic `JOINTPOS`, or
it throws `INTP-311 參數還沒有設定`, and does so by hanging the
entire server, with no response and no connection error (the Python
side just times out). The `MOVEJ` routine has always used `JOINTPOS6`,
so this follows the same convention and never had trouble.

`J_IN_RANGE` only returns legal or not, never which axis. When
`FanucRobot.check_joint()` fails, it separately compares each axis
against `fanuc.limits.DEFAULT_JOINT_LIMITS_DEG`; that table is a
diagnostic aid only, not the source of legality, `J_IN_RANGE` is. The
two can disagree: every axis checks out on its own but `J_IN_RANGE`
still says illegal, meaning it's a pure mechanical-coupling limit
(e.g. J2/J3) the table can't capture, and `check_joint()`'s result
honestly reports that no violating axis was found rather than making
one up.

## `chkpos`

Uses the same `CHECK_EPOS` that `movep` (`MOVEP` in `mappdk_cmd.kl`)
uses to judge reachability, a built-in already verified in production
by movep, not something new and untested, so this one didn't need an
incident first to find the right usage the way `chkjnt` did. The
difference is it only computes the inverse kinematics of the target
point itself, without simulating the whole path; two endpoints that
are each reachable can still fail partway through a linear-interpolated
path due to a configuration switch, and `chkpos` can't catch that.

## `getjpreg` / `setjpreg`

The first version hung outright during real-hardware testing; the fix
is in [debugging notes](debugging-notes.md#getjpreg-hung-in-its-first-version).

---
*Last updated: 2026-08-31*
