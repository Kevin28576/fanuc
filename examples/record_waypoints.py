"""Manually jog the robot with the teach pendant, press Enter to record
the current joint angles, save as waypoints.json.

Only this one feature: read position, write a file. Never sends any
motion command to the robot, safe to jog by hand. The resulting
waypoints.json can be fed directly into examples/move_sequence.py.

Controls:

    Enter         record the current position
    u then Enter  remove the last recorded waypoint
    q then Enter  finish, write the file
"""

import json
import sys

from fanuc import FanucRobot

BAR = "=" * 60

robot = FanucRobot(model="ER-4iA", host="127.0.0.1")
robot.connect()

print(BAR)
print("▶ FANUC waypoint recording test (record_waypoints.py)")
print(BAR)
print(
    "Jog the robot to the position you want with the teach pendant, press\n"
    "Enter to record it. This only reads position and writes a file, never\n"
    "sends any motion command to the robot. u then Enter removes the last\n"
    "one, q then Enter finishes and writes the file."
)

waypoints: list[dict[str, object]] = []

while True:
    raw = input(f"\n[{len(waypoints) + 1}] > ").strip().lower()

    if raw == "q":
        break

    if raw == "u":
        if waypoints:
            removed = waypoints.pop()
            print(f"  removed: {removed['label']}")
        else:
            print("  nothing to remove")
        continue

    if raw:
        print("  didn't understand that, press Enter to record, or type u / q")
        continue

    values = robot.get_curjpos().to_list()
    label = f"waypoint-{len(waypoints) + 1}"
    waypoints.append({"label": label, "type": "joint", "values": values, "velocity": 25})
    print(f"  recorded {label}: " + " ".join(f"{v:.1f}" for v in values))

robot.disconnect()

if not waypoints:
    print(f"\nno waypoints recorded, not writing a file.\n\n{BAR}")
    sys.exit(0)

with open("waypoints.json", "w", encoding="utf-8") as f:
    json.dump(waypoints, f, ensure_ascii=False, indent=2)

print(f"\n{len(waypoints)} waypoints written to waypoints.json")
print("replay: python examples/move_sequence.py")
print(f"\n{BAR}")
