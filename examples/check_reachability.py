"""Asks the controller whether a move is legal/reachable before sending
it. Only this one feature."""

from fanuc import FanucRobot

BAR = "=" * 60


def section(title: str, desc: str) -> None:
    print(f"\n[{title}]  {desc}")


robot = FanucRobot(
    model="ER-4iA",
    host="127.0.0.1",
)
robot.connect()

print(BAR)
print("▶ FANUC reachability check test (check_reachability.py)")
print(BAR)

print(
    "Asks the controller whether a move is legal/reachable before actually\n"
    "sending it; never sends a motion command, never moves the robot.\n"
    "check_joint() uses the controller's built-in J_IN_RANGE, which\n"
    "accounts for mechanical-coupling limits like J2/J3 too; check_pose()\n"
    "uses the same CHECK_EPOS logic as movep."
)

section("Variant 1", "Legal joint angles")
joint_vals = [45, -20, 15, 0, -45, 90]
print(f"  sending: {joint_vals}")
result = robot.check_joint(joint_vals)
print(f"  legal: {result.ok}")
print(f"  detail: {result.describe()}")

section("Variant 2", "Illegal joint angles (deliberately out of range)")
bad_joint_vals = [45, -200, 15, 0, -45, 90]
print(f"  sending: {bad_joint_vals}")
bad = robot.check_joint(bad_joint_vals)
print(f"  legal: {bad.ok}")
print(f"  detail: {bad.describe()}")

section("Variant 3", "Reachable Cartesian position (the robot's current position, always reachable)")
here_vals = robot.get_curpos().to_list()
print(f"  sending: {here_vals}")
reachable = robot.check_pose(here_vals)
print(f"  reachable: {reachable}")

section("Variant 4", "Unreachable Cartesian position")
pose_vals = [400, 50, -100, -180, 0, 0]
print(f"  sending: {pose_vals}")
unreachable = robot.check_pose(pose_vals)
print(f"  reachable: {unreachable}")

print(f"\n{BAR}")

robot.disconnect()
