"""Reads a list of waypoints and runs them in order. Only this one
feature.

Checks every waypoint up front (joint waypoints go through check_joint
to ask the controller whether they're legal, without actually moving),
and only proceeds if everything checks out. Waypoints live in
waypoints.json, format:

    [
      {"label": "home",     "type": "joint", "values": [0,0,0,0,-90,0]},
      {"label": "approach", "type": "pose",  "values": [300,0,250,-180,0,0],
       "velocity": 20, "linear": true}
    ]

Waypoints recorded with examples/record_waypoints.py can be fed
straight into this. Without that file, this builds a demo from the
current joint angles instead, safe regardless of where the robot is.
"""

import json
import sys
from pathlib import Path
from typing import Any

from fanuc import FanucRobot

BAR = "=" * 60


def section(title: str, desc: str) -> None:
    print(f"\n[{title}]  {desc}")


robot = FanucRobot(model="ER-4iA", host="127.0.0.1")
robot.connect()

print(BAR)
print("▶ FANUC waypoint sequence test (move_sequence.py)")
print(BAR)

print(
    "Reads a list of waypoints and runs them in order. Before running,\n"
    "every joint waypoint goes through check_joint; if any step is\n"
    "illegal, the whole batch is blocked and nothing runs. pose waypoints\n"
    "have no equivalent preflight check, and are honestly listed as\n"
    "\"can't preflight\"."
)

waypoints_file = Path("waypoints.json")
if waypoints_file.exists():
    waypoints: list[dict[str, Any]] = json.loads(waypoints_file.read_text(encoding="utf-8"))
    print(f"\nread {waypoints_file}, {len(waypoints)} waypoints.")
else:
    here_joints = robot.get_curjpos().to_list()
    here_pose = robot.get_curpos().to_list()
    nudged = list(here_joints)
    nudged[0] += 5.0  # J1 nudged 5 degrees, for the demo, safe regardless of where the robot is
    waypoints = [
        {"label": "J1 nudged 5 degrees", "type": "joint", "values": nudged, "velocity": 25},
        {"label": "current cartesian position (demonstrates the pose type)", "type": "pose", "values": here_pose, "velocity": 25},
        {"label": "back to the original joint angles", "type": "joint", "values": here_joints, "velocity": 25},
    ]
    print(f"\n{waypoints_file} not found, using the built-in demo ({len(waypoints)} waypoints, ends back at the original position).")

section("Variant 1", "Preflight check (runs every joint waypoint through check_joint)")
for i, wp in enumerate(waypoints, 1):
    label = wp.get("label", f"waypoint-{i}")
    print(f"  sending: check_joint({wp['values']})" if wp["type"] == "joint" else f"  [{i}] {label}  (pose, can't preflight)")
    if wp["type"] != "joint":
        continue
    result = robot.check_joint(wp["values"])
    if not result.ok:
        print(f"  [{i}] {label}  illegal: {result.describe()}")
        sys.exit(1)
    print(f"  [{i}] {label}  legal")

section("Variant 2", "Run the waypoints in order")
for i, wp in enumerate(waypoints, 1):
    label = wp.get("label", f"waypoint-{i}")
    move_kwargs = {
        "velocity": wp.get("velocity", 25),
        "acceleration": wp.get("acceleration", 100),
        "cnt_val": wp.get("cnt", 0),
        "linear": wp.get("linear", False),
    }
    print(f"  [{i}] {label}")
    print(f"  sending: move({wp['type']!r}, {wp['values']}, {move_kwargs})")
    robot.move(wp["type"], wp["values"], **move_kwargs)
    print(f"  done, current position: {robot.get_curpos().to_list()}")

print(f"\n{BAR}")

robot.disconnect()
