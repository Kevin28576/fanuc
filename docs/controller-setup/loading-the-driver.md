# Loading the driver

The files to upload are all in [driver/upload/](../../driver/upload/),
5 of them total; no need to go up a level to `driver/` for the `.kl`
source, that's for people editing the code, and can't be uploaded to
the controller directly.

| File | What it is |
| --- | --- |
| `mappdk_server.pc` | main server |
| `mappdk_logger.pc` | second connection (skip this if you don't need S7) |
| `mappdk.ls` | TP main program, starts the two above |
| `mappdk_move.ls` | used by motion commands |
| `mappdk_movel.ls` | used by linear motion commands |

## Files go into UD1:

`Robot_1\UD1\` under the workcell directory is the **UD1:** device
inside the virtual controller, effectively a permanently-plugged-in
USB drive. No real USB, no FTP needed; just copy the files in
`driver/upload/` into `Robot_1\UD1\`.

If ROBOGUIDE is already open, the workcell needs reopening before the
newly copied files show up.

## Loading from the TP

`MENU` → `FILE` → `FILE` → `UTIL` → `Set Device` → select `UD1:` →
move the cursor to the filename → `ENTER` → `LOAD`. Answer YES when
asked whether to overwrite.

**Load the two `.pc` files first, then the three `.ls` files.** Doing
it out of order doesn't break anything, but keeping this order makes
it less likely to miss a file.

### `.ls` won't load

`.ls` is ASCII source, and needs the **ASCII Upload (R507)** option;
without it you'll see `File Load Error` or `Option Not Installed`.

Without that option, use ROBOGUIDE's own translator instead (its
interface is English, unaffected by the TP's language): Cell Browser
→ `FanucRobot Controller` → `Programs` → right-click → **Load
Program** → select the `.ls` file, and ROBOGUIDE automatically
translates it to `.tp` and loads it.

## Confirming it loaded

`SELECT` → `Type` → `ALL` should show:

```
MAPPDK           [MAPPDK MAIN]
MAPPDK_LOGGER  PC
MAPPDK_MOVE
MAPPDK_MOVEL
MAPPDK_SERVER  PC
```

(No `MAPPDK_LOGGER` line if S7 wasn't loaded; that's expected.)

Entries marked `PC` are compiled KAREL and only show up under the
`KAREL Programs` category; the rest are TP programs and show up under
`TP Programs`.

Done loading? Continue to [running it](running.md).

---
*Last updated: 2026-08-31*
