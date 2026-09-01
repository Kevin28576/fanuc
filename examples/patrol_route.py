"""A complete multi-point patrol route. Only this one feature.

Builds a small loop of waypoints relative to wherever the robot
currently is (safe regardless of position, same trick home_position.py
and move_sequence.py use), runs them in order with move_joint() and
move_pose() directly (not the generic move()), and returns to the
starting position. Demonstrates velocity, cnt_val (continuous-path
blending vs. an exact stop), and linear motion together in one
coherent sequence, not a single isolated nudge.
"""

from fanuc import FanucRobot

BAR = "=" * 60


def section(title: str, desc: str) -> None:
    print(f"\n[{title}]  {desc}")


robot = FanucRobot(model="ER-4iA", host="127.0.0.1")
robot.connect()

print(BAR)
print("▶ FANUC patrol route (patrol_route.py)")
print(BAR)

print(
    "Runs a small loop of waypoints, all defined relative to the current\n"
    "position so this is safe to run regardless of where the robot\n"
    "actually is. Confirm the robot's surroundings are clear before\n"
    "running; the loop stays within a few degrees/centimeters of the\n"
    "starting position."
)

section("Variant 1", "Record the starting position")
start_joints = robot.get_curjpos().to_list()
start_pose = robot.get_curpos().to_list()
print(f"  starting joints: {start_joints}")
print(f"  starting pose:   {start_pose}")

section("Variant 2", "Build the route (joint waypoints, relative to start)")
corner_a = list(start_joints)
corner_a[0] += 5.0  # J1 +5 deg
corner_b = list(start_joints)
corner_b[0] += 5.0
corner_b[4] -= 5.0  # J1 +5 deg, J5 -5 deg
corner_c = list(start_joints)
corner_c[4] -= 5.0  # J5 -5 deg
route = [
    ("corner A (J1 +5)", corner_a),
    ("corner B (J1 +5, J5 -5)", corner_b),
    ("corner C (J5 -5)", corner_c),
    ("back to start", start_joints),
]
for label, values in route:
    print(f"  {label}: {values}")

section("Variant 3", "Run the joint waypoints (CNT blending between them, FINE on the last)")
for i, (label, values) in enumerate(route, 1):
    is_last = i == len(route)
    cnt_val = 0 if is_last else 50  # FINE (exact stop) only on the final waypoint
    print(f"  [{i}] {label}")
    print(f"  sending: move_joint({values}, velocity=25, cnt_val={cnt_val})")
    robot.move_joint(values, velocity=25, cnt_val=cnt_val)
print(f"  done, joints: {robot.get_curjpos().to_list()}")

section("Variant 4", "One Cartesian leg (move_pose, linear interpolation)")
nudged_pose = list(start_pose)
nudged_pose[2] += 20.0  # Z +20mm, straight up
print(f"  sending: move_pose({nudged_pose}, velocity=20, linear=True)")
robot.move_pose(nudged_pose, velocity=20, linear=True)
print(f"  sending: move_pose({start_pose}, velocity=20, linear=True)  # back down")
robot.move_pose(start_pose, velocity=20, linear=True)
print(f"  done, pose: {robot.get_curpos().to_list()}")

print(f"\n{BAR}")

robot.disconnect()
