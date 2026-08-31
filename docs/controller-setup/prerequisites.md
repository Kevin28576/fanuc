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

Confirmed both? Continue to [server tags](server-tags.md).

---
*Last updated: 2026-08-31*
