# Extending the driver

Read this when adding a new command to the driver, or weighing
whether to touch the KAREL source at all.

## Steps for adding a command

1. Add a ROUTINE in `driver/mappdk_ext.kl`
2. Add a dispatch branch in `HANDLE_CMD` in `driver/mappdk_cmd.kl`
3. If it uses a new built-in function, `mappdk_server.kl` and
   `mappdk_logger.kl` need a matching `%ENVIRONMENT`. The environment
   files are under WinOLPC's `Versions/V940-1/support`; grepping there
   finds which `.ev` a given function lives in
4. `cd driver` and run ktrans; the output `.pc` lands in the current
   directory. Copy it over the old file in `driver/upload/`, then load
   it from the TP, steps in
   [driver/README.md](../../driver/README.md)
5. Add `encode_*` / `parse_*` to `protocol.py`, add a method to
   `robot.py`
6. Add a format test to `tests/test_protocol.py`, no real hardware
   needed

To try a command out first, `robot.send_raw()` sends a raw string
directly, no need to wrap it into a method right away.

## The `%ENVIRONMENT` pitfalls

There are two.

First: as soon as any one is declared, ktrans stops auto-loading the
default extended environments, and things like `$GROUP`,
`CALL_PROGLIN`, `MSG_CONNECT` suddenly can't be found; everything
actually used has to be listed explicitly. But `CORE` and `SYSTEM` are
loaded by default, and declaring either of them again gets
`Cannot load environment file, program already exists`.

Second: there's an upper bound on the total count of directives plus
environments. It's currently 5 directives (`%STACKSIZE`,
`%NOLOCKGROUP`, `%NOPAUSE`, `%ALPHABETIZE`, `%COMMENT`) against 7
environments, already at the edge. Adding one more environment
produces the seemingly unrelated
`Id must be defined before this use. Id: IO_RDO`. Removing any one
directive or environment makes it pass, so it's not any particular
combination that's broken. Adding another environment means first
deciding which directive can be dropped.

This limit is also why the RDO access-range check lives in Python
rather than KAREL, see
[driver limits](driver-limits.md#rdo-out-of-range-aborts-the-whole-server).

## Not done yet (deferred)

**Motion abort, pause, resume**: evaluated, deferred. Unlike
"query/data" commands like reading and writing registers, this needs
cross-task control over the `MAPPDK_SERVER` currently executing a
motion (KAREL's `PAUSE`/`ABORT <program name>` cross-task syntax), and
the exact usage hasn't been verified; getting it wrong could leave the
robot stopped mid-motion or trigger a safety system, a much higher
cost than a register read/write mistake, not something to try on real
hardware with a "guess, compile, hang, RESET" approach. Restarting
this needs verified KAREL cross-task control documentation or an
example first, not something field trial-and-error can solve reliably
on its own.

Writing numeric system variables, string register `SR[n]`, and the
joint-type position register are already in `mappdk_ext.kl`
(`setsysvarnum`/`getsreg`/`setsreg`/`getjpreg`/`setjpreg`, see
[extended commands](commands-extended.md)), all verified on real
hardware. Reading alarm history was tried; the `ERR_DATA` approach
hasn't found a working method yet, and it's fallen back to reading
only the most recent alarm, see
[debugging notes](debugging-notes.md#alarm-history-cant-be-read).

---
*Last updated: 2026-08-31*
