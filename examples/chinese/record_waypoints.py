"""用示教器手動移動機器人,按 Enter 記錄目前的關節角度,存成 waypoints.json。

只示範這一個功能:讀位置、寫檔。不會送任何動作指令給機器人,可以放心
手動移動。存出來的 waypoints.json 可以直接讓 examples/move_sequence.py
拿去跑。

操作:

    Enter        記錄目前位置
    u 再 Enter   刪掉剛剛記的最後一筆
    q 再 Enter   結束,寫檔
"""

import json
import sys

from fanuc import FanucRobot

BAR = "=" * 60

robot = FanucRobot(model="ER-4iA", host="127.0.0.1")
robot.connect()

print(BAR)
print("▶ FANUC 點位錄製測試 (record_waypoints.py)")
print(BAR)
print(
    "用示教器把機器人移到想要的位置,按 Enter 記錄。這支只讀位置、寫檔,\n"
    "不會送任何動作指令給機器人。u 再 Enter 刪掉上一筆,q 再 Enter 結束並寫檔。"
)

waypoints: list[dict[str, object]] = []

while True:
    raw = input(f"\n[{len(waypoints) + 1}] > ").strip().lower()

    if raw == "q":
        break

    if raw == "u":
        if waypoints:
            removed = waypoints.pop()
            print(f"  已刪除: {removed['label']}")
        else:
            print("  沒有可以刪的")
        continue

    if raw:
        print("  沒聽懂,直接按 Enter 記錄,或輸入 u / q")
        continue

    values = robot.get_curjpos().to_list()
    label = f"waypoint-{len(waypoints) + 1}"
    waypoints.append({"label": label, "type": "joint", "values": values, "velocity": 25})
    print(f"  已記錄 {label}: " + " ".join(f"{v:.1f}" for v in values))

robot.disconnect()

if not waypoints:
    print(f"\n沒有記錄到任何點位,不寫檔。\n\n{BAR}")
    sys.exit(0)

with open("waypoints.json", "w", encoding="utf-8") as f:
    json.dump(waypoints, f, ensure_ascii=False, indent=2)

print(f"\n共 {len(waypoints)} 筆,已寫入 waypoints.json")
print("重播: python examples/move_sequence.py")
print(f"\n{BAR}")
