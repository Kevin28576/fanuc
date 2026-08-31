"""Reads the current position, prints both the pose and joint angles.
Only this one feature.

The CLI has the same feature (`fanuc pos`, `fanuc watch`); this is for
people who want to see the Python API call directly.
"""

from fanuc import FanucRobot

BAR = "=" * 60


def section(title: str, desc: str) -> None:
    print(f"\n[{title}]  {desc}")


robot = FanucRobot(
    model="ER-4iA",
    host="127.0.0.1",
    ee_DO_type="RDO",
    ee_DO_num=7,
    gripper_travel="1s",
)
robot.connect()

print(BAR)
print("▶ FANUC read current position test (read_position.py)")
print(BAR)

print(
    "Reads the pose (Pose) and joint angles (Joints) once, then\n"
    "demonstrates two ways to get their values (formatted string, direct\n"
    "unpacking)."
)

section("Variant 1", "Read pose and joint angles (formatted output)")
pose = robot.get_curpos()
joints = robot.get_curjpos()
print("  pose:")
for line in pose.format().splitlines():
    print(f"    {line}")
print("  joints:")
for line in joints.format().splitlines():
    print(f"    {line}")

section("Variant 2", "Pose can be unpacked directly, or turned into a list")
x, y, z, w, p, r = pose
print(f"  unpacked: X={x:.1f} Y={y:.1f} Z={z:.1f} W={w:.1f} P={p:.1f} R={r:.1f}")
print(f"  to_list(): {pose.to_list()}")

print(f"\n{BAR}")

robot.disconnect()
