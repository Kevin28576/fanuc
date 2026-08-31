# These are the files that actually get loaded onto the controller

All 5 of them, nothing else needed from the level above:

| File | Becomes, once loaded on UD1: | Load order |
| --- | --- | --- |
| `mappdk_server.pc` | `MAPPDK_SERVER` (KAREL program) | 1 |
| `mappdk_logger.pc` | `MAPPDK_LOGGER` (KAREL program) | 1 |
| `mappdk.ls` | `MAPPDK` (TP program, starts the two above when run) | 2 |
| `mappdk_move.ls` | `MAPPDK_MOVE` (used by motion commands) | 2 |
| `mappdk_movel.ls` | `MAPPDK_MOVEL` (used by linear motion commands) | 2 |

Order: load the two `.pc` files first, then the three `.ls` files. Full
steps (TP operation, the ROBOGUIDE translator, common errors) are in
[docs/controller-setup/loading-the-driver.md](../../docs/controller-setup/loading-the-driver.md).

A `.pc` is compiled output, not source; it can't be edited directly.
To change behavior, edit the matching `.kl` one level up, recompile,
and overwrite the old `.pc` here with the new one. Steps are in
[driver/README.md](../README.md).

---
*Last updated: 2026-08-31*
