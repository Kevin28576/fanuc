"""Dual-signal gripper control. Only this one feature.

The gripper is wired dual-signal (a SCHUNK EGP small-parts gripper, on
the EE Pinout): open and close are independent RDOs, not the same
signal inverted. The RO7/RO8 mapping has been confirmed on real
hardware: RO7=ON, RO8=OFF is open; RO7=OFF, RO8=ON is close. Reconfirm
this numbering against your own wiring sheet when switching grippers
or wiring, don't copy it blindly.

gripper_travel is an "unverified" placeholder, not a measured real
number. How long the gripper actually takes to finish opening/closing
after the signal is sent has no universal safe default, so the
package requires this parameter explicitly rather than letting such a
number slip through unnoticed. Replace it with your gripper's spec
sheet value, or a stopwatch-measured real number, before real use.
"""

from fanuc import FanucRobot

BAR = "=" * 60


def section(title: str, desc: str) -> None:
    print(f"\n[{title}]  {desc}")


robot = FanucRobot(
    model="ER-4iA",
    host="127.0.0.1",
    ee_DO_type="RDO",
    ee_open_num=7,
    ee_close_num=8,
    gripper_travel="0.1s",  # see file header, replace with a measured real value before real use
)
robot.connect()

print(BAR)
print("▶ FANUC gripper control test (gripper_control.py)")
print(BAR)

print(
    "Open, close, reset, read state. Dual-signal wiring (open and close\n"
    "are independent RDOs); the RO7/RO8 numbering was confirmed on this\n"
    "verification setup, reconfirm against your own wiring sheet when\n"
    "switching grippers or wiring."
)

section("Variant 1", "Read the current state")
print(f"  result: {robot.get_gripper()}")

section("Variant 2", "Close the gripper")
print("  sending: gripper(True)")
print(f"  waiting for gripper_travel ({robot.gripper_travel}) before returning, to make sure the gripper actually finished moving")
robot.gripper(True)
print(f"  result: {robot.get_gripper()}")

section("Variant 3", "Open the gripper")
print("  sending: gripper(False)")
print(f"  waiting for gripper_travel ({robot.gripper_travel}) before returning, to make sure the gripper actually finished moving")
robot.gripper(False)
print(f"  result: {robot.get_gripper()}")

section("Variant 4", "Reset the gripper (both signals True at once, clears alarms)")
print("  sending: gripper_reset()")
print(f"  waiting for gripper_travel ({robot.gripper_travel}) before returning, to make sure the reset actually finished")
robot.gripper_reset()
print(f"  result: {robot.get_gripper()}")

print(f"\n{BAR}")

robot.disconnect()
