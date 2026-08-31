# Error messages

When the driver responds with code `1`, the message content maps to
an exception class on the Python side.

| Message | Exception | Meaning |
| --- | --- | --- |
| `position-is-not-reachable` | `UnreachableError` | out of range or no solution for that pose |
| `R[81]-was-not-set` etc. | `MotionSetupError` | couldn't write a motion parameter register |
| `PR[81]-was-not-set` | `MotionSetupError` | couldn't write the position register |
| `wrong-command` | `UnsupportedCommandError` | driver doesn't recognize it |
| `cannot-convert-joint-vals` | `CommandError` | joint value conversion failed |
| `cannot-get-ins_pwr` | `CommandError` | couldn't read power |
| `cannot-get-reg` `cannot-set-reg` | `CommandError` | register access failed |
| `cannot-get-preg` `cannot-set-preg` | `CommandError` | position register access failed |
| `cannot-get-sysvar` `cannot-set-sysvar` | `CommandError` | variable doesn't exist or type mismatch |
| `cannot-get-sreg` `cannot-set-sreg` | `CommandError` | string register access failed |
| `cannot-get-jpreg` `cannot-set-jpreg` | `CommandError` | joint-type position register access failed |
| everything else | `CommandError` | catch-all |

---
*Last updated: 2026-08-31*
