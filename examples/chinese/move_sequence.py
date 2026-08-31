"""讀一串點位，依序執行。只示範這一個功能。

先把全部點位過一遍（關節點位用 check_joint 問控制器合不合法，不會真的
動），確認沒問題才依序執行。點位放在 waypoints.json，格式：

    [
      {"label": "home",     "type": "joint", "values": [0,0,0,0,-90,0]},
      {"label": "approach", "type": "pose",  "values": [300,0,250,-180,0,0],
       "velocity": 20, "linear": true}
    ]

用 examples/record_waypoints.py 錄的點位可以直接拿來跑。沒有這個檔案
時，用目前的關節角度回原位置一次當內建示範，不管機器人在哪都安全。
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
print("▶ FANUC 點位序列執行測試 (move_sequence.py)")
print(BAR)

print(
    "讀一串點位，依序執行。執行前會用 check_joint 把全部關節點位過一遍，\n"
    "任何一步不合法就整批擋下，不執行任何動作。pose 型別的點位沒有對應\n"
    "的預檢指令，會如實列為「無法預檢」。"
)

waypoints_file = Path("waypoints.json")
if waypoints_file.exists():
    waypoints: list[dict[str, Any]] = json.loads(waypoints_file.read_text(encoding="utf-8"))
    print(f"\n讀到 {waypoints_file}，共 {len(waypoints)} 個點位。")
else:
    here_joints = robot.get_curjpos().to_list()
    here_pose = robot.get_curpos().to_list()
    nudged = list(here_joints)
    nudged[0] += 5.0  # J1 擺動 5 度，示範用，不管機器人在哪都安全
    waypoints = [
        {"label": "J1 擺動 5 度", "type": "joint", "values": nudged, "velocity": 25},
        {"label": "目前直角座標（示範 pose 型別）", "type": "pose", "values": here_pose, "velocity": 25},
        {"label": "回原本關節角度", "type": "joint", "values": here_joints, "velocity": 25},
    ]
    print(f"\n沒有找到 {waypoints_file}，改用內建示範（{len(waypoints)} 個點位，跑完會回到原本位置）。")

section("變體 1", "執行前檢查（用 check_joint 把全部關節點位過一遍）")
for i, wp in enumerate(waypoints, 1):
    label = wp.get("label", f"waypoint-{i}")
    print(f"  送出: check_joint({wp['values']})" if wp["type"] == "joint" else f"  [{i}] {label}  (pose，無法預檢)")
    if wp["type"] != "joint":
        continue
    result = robot.check_joint(wp["values"])
    if not result.ok:
        print(f"  [{i}] {label}  不合法: {result.describe()}")
        sys.exit(1)
    print(f"  [{i}] {label}  合法")

section("變體 2", "依序執行動作")
for i, wp in enumerate(waypoints, 1):
    label = wp.get("label", f"waypoint-{i}")
    move_kwargs = {
        "velocity": wp.get("velocity", 25),
        "acceleration": wp.get("acceleration", 100),
        "cnt_val": wp.get("cnt", 0),
        "linear": wp.get("linear", False),
    }
    print(f"  [{i}] {label}")
    print(f"  送出: move({wp['type']!r}, {wp['values']}, {move_kwargs})")
    robot.move(wp["type"], wp["values"], **move_kwargs)
    print(f"  完成，目前位置: {robot.get_curpos().to_list()}")

print(f"\n{BAR}")

robot.disconnect()
