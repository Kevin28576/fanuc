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

- **KAREL** (commonly R632)
- **User Socket Messaging** (commonly R648)

The exact option number isn't fixed across every controller/software
bundle -- confirmed in the field on a real ER-4iA (V9.30P/22) where
User Socket Messaging showed up as **R636**, not R648. Match by the
option's *name*, not the number: `MENU` → `NEXT` → `STATUS` →
`Version ID` → press `ORDER FI` lists every installed option with its
description text next to the number.

Faster check for KAREL specifically: whether `SELECT` → `Type` has a
`KAREL Programs` entry; if so, the KAREL option is installed. There's
no equivalent shortcut for User Socket Messaging -- it doesn't get its
own program category, so the `ORDER FI` list (or the symptom in
"`INTP-320 Unassigned built-in`" below) is the only way to tell.

If either option is missing, do a Serialize / robot options update on
this robot in ROBOGUIDE, and add both options in the virtual robot
edit wizard. There's no way around this step; without the options
installed, nothing after this works.

## `PRIO-230 Ethernet Adapter error`

If `OPEN_COMM` fails with this alarm when `MAPPDK_SERVER`/`MAPPDK_LOGGER`
first tries to open its socket, it means the controller's networking
side isn't ready for `R648` to actually talk over Ethernet, not a bug
in this project's driver. Recheck, in order:

1. **User Socket Messaging is actually installed**, not just KAREL;
   the two options are easy to conflate since both matter here, but
   only User Socket Messaging covers the socket-level communication
   this alarm is about.
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

## `INTP-320 Unassigned built-in`

Looks exactly like a missing option (both KAREL and User Socket
Messaging are the usual first suspects), but confirmed in the field
to have a different cause entirely: **the `.pc` was compiled with the
wrong `ktrans` version for this controller.**

A compiled `.pc`'s bytecode is tied to the specific system software
version `ktrans` targeted; loading it onto a controller running a
different version can make a perfectly ordinary built-in (this
project hit it on `MSG_DISCO`, called from
[`driver/mappdk_comm.kl`](../../driver/mappdk_comm.kl)) come back as
"unassigned", even though every required option genuinely is
installed. The alarm names the exact line
(`INTP-320 (MAPPDK_SERVER, 51) ...`), which is what makes it look
like a real code bug rather than a version mismatch -- checking the
`.kl` source at that line only shows an ordinary, correctly-written
built-in call.

Check the controller's actual system software version first (`MENU`
→ `NEXT` → `STATUS` → `Version ID`, the "Default Personality" line,
e.g. `V9.30P/22` -- not the Boot Monitor line further down, which can
show a different version number on the same controller). Then
recompile with a matching `ktrans /ver` (see
[driver/README.md](../../driver/README.md#compiling-after-a-code-change))
and upload the result from the matching subfolder under
[`driver/upload/`](../../driver/upload/) instead of assuming last
time's `.pc` still applies.

Confirmed both options, and the `.pc` you're loading matches this
controller's actual version? Continue to [server
tags](server-tags.md).

---
*Last updated: 2026-09-05*
