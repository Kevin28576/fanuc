# Prerequisites

One-time setup for the ROBOGUIDE virtual controller. The setup lives
in the workcell, so after this only MAPPDK needs starting on each
boot, no need to redo any of this.

The TP menus are labeled in Simplified Chinese; wording varies a bit
by version (e.g. `装载` vs `加载`). System variable names are always
in English, never translated.

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

How to check: `菜单` → `下页` → `状态` → `版本识别` → press `ORDER FI`.

Faster check: whether `一览` → `类型` has a `KAREL程序` entry; if so,
R632 is installed.

If either option is missing, do a Serialize / robot options update on
this robot in ROBOGUIDE, and add both options in the virtual robot
edit wizard. There's no way around this step; without the options
installed, nothing after this works.

Confirmed both? Continue to [server tags](server-tags.md).

---
*Last updated: 2026-08-31*
