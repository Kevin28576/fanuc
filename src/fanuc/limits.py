"""Reference table of the controller's soft limits, used only for
per-axis diagnostics when chkjnt fails.

This table is **not** the source of truth for legality; that's the
controller's built-in J_IN_RANGE (see CHECK_JOINT in
driver/mappdk_ext.kl). J_IN_RANGE also accounts for mechanical-coupling
limits like J2/J3; this table only has per-axis ranges and can't
capture coupling.

These numbers were read straight off the TP (MENU -> SYSTEM -> Axis
Motion Range), not summarized from a datasheet, and not guessed from a
system variable. GET_VAR against $PARAM_GROUP[1].$LOWERLMT / $UPPERLMT and
several variants was tried; none of them worked on V9.4099. There's
currently no known programmatic way to query whatever backs that
screen, hence this fallback of reading it once and hard-coding it.

The numbers only apply to the ER-4iA controller used for verification.
A different robot (even the same model with tuned parameters) may
differ; pass your own joint_limits_deg to FanucRobot() or
move_sequence.py to override this default when switching robots.
"""

from __future__ import annotations

#: Read from the TP's System -> Axis Motion Range screen on 2026-08-30,
#: ER-4iA, controller V9.4099. Cross-checked against the datasheet's
#: (R3_ER-4iA.pdf) total sweep angles per axis: J1 340°, J2 230°,
#: J3 402.29°, J4 380°, J5 240°, J6 720°; all match.
DEFAULT_JOINT_LIMITS_DEG: dict[str, tuple[float, float]] = {
    "J1": (-170.00, 170.00),
    "J2": (-110.00, 120.00),
    "J3": (-122.29, 280.00),
    "J4": (-190.00, 190.00),
    "J5": (-120.00, 120.00),
    "J6": (-360.00, 360.00),
}

#: Official default home pose, read from ROBOGUIDE's Current Position
#: panel, ER-4iA. Same caveat as the limit table: only applies to the
#: verification controller, specify your own when switching robots.
DEFAULT_HOME_JOINTS: tuple[float, ...] = (0.0, -30.0, 0.0, 0.0, -90.0, 0.0)
