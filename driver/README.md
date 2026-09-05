# driver/

Source and compiled output for the KAREL programs that run on the
controller. Just want to load the driver onto the controller and not
touch the code? Go straight to [upload/](upload/README.md), you don't
need anything else in this directory.

## What's in here

Only two files are real programs (a `PROGRAM` entry point); everything
else is a shared routine pulled in with `%INCLUDE`, and doesn't build
into anything on its own:

| File | What it is |
| --- | --- |
| `mappdk_server.kl` | Main program, becomes `MAPPDK_SERVER` (S8, port 18735) |
| `mappdk_logger.kl` | Main program, becomes `MAPPDK_LOGGER` (S7, port 18736); nearly identical to server, just a second connection so queries and motion commands don't block each other |
| `mappdk_cmd.kl` | Command dispatch logic (`HANDLE_CMD`) both main programs `%INCLUDE` |
| `mappdk_ext.kl` | This project's extension commands (`getreg`, `getalarm`, `chkjnt`, and so on) |
| `mappdk_comm.kl` | Shared socket open/close and send/receive logic |
| `mappdk_utils.kl` | Other shared helpers |

`mappdk_server.kl` and `mappdk_logger.kl` each `%INCLUDE` the four
files above and compile into two separate `.pc` files. Changing any of
the included files means recompiling both main programs.

## Compiling after a code change

The compiled `.pc` is what the controller actually understands; the
`.kl` source can't be uploaded directly.

**The `ktrans` version must match the controller's system software
version** (`MENU` -> `NEXT` -> `STATUS` -> `Version ID`, the "Default
Personality" line, e.g. `V9.30P/22`) -- not just "close enough". A
`.pc` compiled with the wrong version fails on the controller with an
`INTP-320 Unassigned built-in` error, even when the option it needs
(KAREL, User Socket Messaging) is genuinely installed; that error
looks exactly like a missing-option problem but isn't one, and cost a
real debugging session to track down (see
[CHANGELOG.md](../CHANGELOG.md) if it's not obvious which entry).

`ktrans.exe` ships every version it knows how to target -- run it with
no arguments to list them (`Installed versions of WinOLPC:` in its
output) -- and `/ver` picks one explicitly:

```
cd driver
"C:\Program Files (x86)\FANUC\WinOLPC\bin\ktrans.exe" mappdk_server.kl /ver V9.30-1
"C:\Program Files (x86)\FANUC\WinOLPC\bin\ktrans.exe" mappdk_logger.kl /ver V9.30-1
```

(this project's main verification setup uses `V9.40-1` against a
ROBOGUIDE V9.4099 virtual controller; use whichever version string
matches your actual controller instead). Run this from an actual
Windows shell (PowerShell/cmd) -- Git Bash rewrites a leading `/ver`
into a bogus file path before `ktrans.exe` ever sees it. It'll also
complain about `Unable to find 'robot.ini'` while running; that's
expected, ignore it.

The output `.pc` lands in whatever directory the command ran from,
which is why the steps above start with `cd driver`. Once compiled,
copy the two new `.pc` files into the matching version subfolder
under `upload/` (create one if your version isn't there yet):

```
copy mappdk_server.pc mappdk_logger.pc upload\v9.30\
```

Then follow [upload/README.md](upload/README.md) to upload them to
the controller again.

## Server tag / port are hardcoded in the source

To change the tag or port used for the connection, edit
`SERVER_TAG_NUM` and `PORT_NUMBER` in the `CONST` block of
`mappdk_server.kl`/`mappdk_logger.kl`, then recompile as above. The
tag configured on the controller's TP has to match this, or the
socket won't open; getting the port right doesn't mean the tag is
right too, both need checking. Details in
[controller setup](../docs/controller-setup/server-tags.md).

## Adding a new command

Steps, and the pitfalls in the environment setup, are in
[docs/protocol/extending-the-driver.md](../docs/protocol/extending-the-driver.md).

---
*Last updated: 2026-09-05*
