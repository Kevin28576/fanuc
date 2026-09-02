# Prerequisites

One-time setup for the ROBOGUIDE virtual controller. The setup lives
in the workcell, so after this only MAPPDK needs starting on each
boot, no need to redo any of this.

The TP's menu language follows whatever the controller is set to.
This document assumes English menus; the Traditional Chinese version
of this document ([開始之前](../zh/controller-setup/prerequisites.md))
assumes Traditional Chinese menus instead, matching that TP's actual
setting.

> [!NOTE]
> The English menu labels quoted throughout this document are filled
> in from general knowledge of FANUC's standard TP interface, not
> checked against a real English-mode TP screen. Wording (and in a
> few places, the exact menu path) may not match yours exactly; if
> something doesn't line up, the labels are the part to distrust
> first.

System variable names are always in English, never translated,
regardless of the TP's menu language.

## The controller runs two servers

| Program | tag | port | purpose |
| --- | --- | --- | --- |
| `MAPPDK_SERVER` | S8 | 18735 | main connection; motion, I/O, and position queries all go through this |
| `MAPPDK_LOGGER` | S7 | 18736 | second connection, only needed when querying position while moving |

Same command set on both, the only differences are tag and port, plus
the logger not clearing the TP screen or setting UFRAME/UTOOL. The
driver is synchronous and blocking: once the main connection sends a
motion command, it's stuck until the move finishes, and position can't
be queried during that time. If your program needs to record a
trajectory in real time while moving (the kind of thing
`examples/trace_motion.py` does), that's when the second connection is
needed; for plain reading/writing of position, registers, and I/O, S7
isn't needed at all, and every S7-related step in this document can be
skipped.

## Confirm the controller options

Need both of these:

- **R632**: KAREL
- **R648**: User Socket Messaging

How to check: `MENU` → `NEXT` → `STATUS` → `Version ID` → press `ORDER FI`.

Faster check: whether `SELECT` → `Type` has a `KAREL Programs` entry;
if so, R632 is installed.

If either option is missing, do a Serialize / robot options update on
this robot in ROBOGUIDE, and add both options in the virtual robot
edit wizard. There's no way around this step; without the options
installed, nothing after this works.

## `PRIO-230 Ethernet Adapter error`

If `OPEN_COMM` fails with this alarm when `MAPPDK_SERVER`/`MAPPDK_LOGGER`
first tries to open its socket, it means the controller's networking
side isn't ready for `R648` to actually talk over Ethernet, not a bug
in this project's driver. Recheck, in order:

1. **R648 (User Socket Messaging) is actually installed**, not just
   R632; the two options are easy to conflate since both matter here,
   but only R648 covers the socket-level communication this alarm is
   about.
2. **On real hardware** (this doesn't apply to the ROBOGUIDE virtual
   controller): the controller's Ethernet interface is physically
   connected and has an IP address configured (`MENU` → `SETUP` →
   `Host Comm` → `TCP/IP`). A robot fresh out of the box, or one
   that's never had its network settings touched, commonly hits this.
3. **The port isn't already in use** by another server tag or a
   stale connection from a previous run that never closed cleanly;
   `AUX` → `ABORT` and a `RESET` (see [running the
   driver](running.md)) clears most of these.

This alarm has been reported against upstream fanucpy too
([torayeff/fanucpy#35](https://github.com/torayeff/fanucpy/issues/35)),
consistent with it being a controller-side prerequisite rather than
something either driver's KAREL code can fix.

Confirmed both? Continue to [server tags](server-tags.md).

---
*Last updated: 2026-08-31*
