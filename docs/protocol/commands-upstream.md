# Upstream commands

Taken from `HANDLE_CMD` in `mappdk_cmd.kl`, compatible with the
original fanucpy upstream driver; works even without this project's
extended driver loaded.

| Command | Params | Response | Method |
| --- | --- | --- | --- |
| `curpos` | none | `x=..,y=..,z=..,w=..,p=..,r=..` | `get_curpos()` |
| `curjpos` | none | `j=..,j=..` (a nonexistent axis is `j=none`) | `get_curjpos()` |
| `ins_pwr` | none | kW | `get_ins_power()` |
| `movej` | see [wire format](wire-format.md#motion-command-field-widths) | `success` | `move("joint", ...)` |
| `movep` | see [wire format](wire-format.md#motion-command-field-widths) | `success` | `move("pose", ...)` |
| `mappdkcall` | `:<program name>` | `success` | `call_prog()` |
| `getrdo` | `:<n>` | `0` / `1` | `get_rdo()` |
| `setrdo` | `:<n>:<true\|false>` | `success` | `set_rdo()` |
| `getdout` | `:<5-digit zero-padded>` | `0` / `1` | `get_dout()` |
| `setdout` | `:<5-digit zero-padded>:<true\|false>` | `success` | `set_dout()` |
| `setsysvar` | `:<var name>:<T\|F>` | `success` | `set_sys_var()` |
| `exit` | none | `success`, then disconnects | via `disconnect()` |

`setsysvar` only accepts booleans (`T`/`F`); numeric system variables
need the extended command `setsysvarnum`, see
[extended commands](commands-extended.md).

---
*Last updated: 2026-08-31*
