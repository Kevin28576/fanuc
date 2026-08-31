# Debugging notes: extended command development history

Pitfalls hit while developing the extended commands, kept around for
reference when adding new commands later, or revisiting these
conclusions.

## Alarm history can't be read

The original idea was to mirror the "numbered" approach `getpreg`/
`getjpreg` use, letting `getalarm:nnn` specify which historical alarm
to read (`ERR_DATA`'s first parameter formally looks like an input
sequence number). Real-hardware testing disproved this: parsing the
sequence number itself worked fine (echoed back during debugging,
1, 2, 5, 8, 9 all matched exactly what was sent), but no matter what
number was given, `ERR_DATA` returned the same entry every time.
Cross-checking against the TP's alarm history screen, entries 5, 8,
and 9 were "reset", `SRVO-003`, and `SYST-039` respectively, which
didn't match the `PROG-048` read back at all. Testing with these
values, this parameter to `ERR_DATA` doesn't look like it selects a
history index; what it's actually for isn't clear. The TP clearly uses
a different mechanism to page through alarm history, and this driver
hasn't found an equivalent access method yet, not ruling out that it's
just not found rather than confirmed impossible. **This approach has
since been removed**; anyone continuing to try, this is the known
sticking point. For full alarm history, go directly to the TP's
`报警` → `履历` screen for now.

### `ERR_DATA` rewrites the parameter passed in

A real pitfall hit along the way: `ERR_DATA`'s first parameter
formally looks like an input, but after the call it gets rewritten by
`ERR_DATA` itself (observed becoming something like an internal alarm
count, e.g. 1447). Early on, a `FOR` loop variable was passed directly
as this parameter; after one call the loop variable was corrupted,
ending the loop after a single iteration and throwing in a stray
semicolon that shouldn't have been there. The fix was to copy the loop
variable into a separate variable each iteration and pass that copy to
`ERR_DATA`, letting it mutate the copy while the loop variable itself
stays untouched.

This pitfall isn't specific to `ERR_DATA`: any KAREL built-in
function's parameter, unless verified to be pure input, shouldn't be
passed a control-flow variable (a loop counter and the like) directly.
This lesson still holds even though `ERR_DATA` itself turned out to be
a dead end for now, kept here for the next time a different built-in
function is used.

## `getjpreg` hung in its first version

The first version hung outright during real-hardware testing (no
response received). Comparing against the already-verified
`GET_CURJPOS` (`mappdk_cmd.kl`) found the cause: `GET_CURJPOS` calls
`CNV_JPOS_REL(jpos, joint_vals, status)` with the generic `JOINTPOS`
type, where the third parameter is a status code, not an axis count.
The first version wrongly declared it as `JOINTPOS6` and treated the
third parameter as an axis count, both wrong. After matching
`GET_CURJPOS`'s approach exactly (`JOINTPOS`, the `status` semantics,
using `UNINIT()` to tell which array entries are real axes),
real-hardware verification across multiple position-register values
read and wrote correctly, round-tripped consistently, and never hung
again. `setjpreg` uses the reverse conversion (`CNV_REL_JPOS`), and its
approach matched `MOVEJ`/`CHECK_JOINT` from the start, so it never had
a problem.

---
*Last updated: 2026-08-31*
