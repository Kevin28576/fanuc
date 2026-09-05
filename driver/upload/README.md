# These are the files that actually get loaded onto the controller

## Pick your controller's software version first

A `.pc` is compiled by `ktrans`, and its bytecode is tied to the
system software version it was compiled against -- a `.pc` compiled
with the wrong version's `ktrans` fails on the controller with an
`INTP-320 Unassigned built-in` error (or similar), even though the
`.kl` source is identical and the option needed (KAREL, User Socket
Messaging) is actually installed. Check the controller's version
first (`MENU` -> `NEXT` -> `STATUS` -> `Version ID`, the "Default
Personality" line, e.g. `V9.30P/22`), then use the matching
subfolder:

| Subfolder | Compiled with | Verified against |
| --- | --- | --- |
| `v9.40/` | `ktrans /ver V9.40-1` | ROBOGUIDE virtual controller V9.4099 (this project's main verification setup) |
| `v9.30/` | `ktrans /ver V9.30-1` | A real ER-4iA controller running V9.30P/22 |

No subfolder for your exact version? Recompile from source -- see
[driver/README.md](../README.md#compiling-after-a-code-change) -- the
`.kl` source is identical across versions, only the `ktrans` target
changes.

## What's in each version's folder, plus the shared files

All of these, nothing else needed from the level above:

| File | Becomes, once loaded on UD1: | Load order |
| --- | --- | --- |
| `<version>/mappdk_server.pc` | `MAPPDK_SERVER` (KAREL program) | 1 |
| `<version>/mappdk_logger.pc` | `MAPPDK_LOGGER` (KAREL program) | 1 |
| `mappdk.ls` | `MAPPDK` (TP program, starts the two above when run) | 2 |
| `mappdk_move.ls` | `MAPPDK_MOVE` (used by motion commands) | 2 |
| `mappdk_movel.ls` | `MAPPDK_MOVEL` (used by linear motion commands) | 2 |

The three `.ls` files are plain TP program listings, not compiled by
`ktrans`, so they're version-independent and shared across every
`ktrans` target -- no per-version copies needed.

Order: load the two `.pc` files first, then the three `.ls` files. Full
steps (TP operation, the ROBOGUIDE translator, common errors) are in
[docs/controller-setup/loading-the-driver.md](../../docs/controller-setup/loading-the-driver.md).

A `.pc` is compiled output, not source; it can't be edited directly.
To change behavior, edit the matching `.kl` one level up, recompile
with each version of `ktrans` you need, and overwrite the old `.pc`
files under the matching subfolder here. Steps are in
[driver/README.md](../README.md).

---
*Last updated: 2026-09-05*
