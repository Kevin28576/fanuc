"""完整的多點位巡邏路線。只示範這一個功能。

用「相對於機器人目前位置」的方式組出一小段巡邏路線（安全，不管機器人
現在在哪裡都能跑，跟 home_position.py、move_sequence.py 用的是同一招），
直接用 move_joint()、move_pose()（不是通用的 move()）依序執行，最後
回到起點。同一段裡示範 velocity、cnt_val（連續路徑混合 vs. 精確停止）
跟直線動作，是一段完整、連貫的動作，不是單一一次小幅微調。
"""

from fanuc import FanucRobot

BAR = "=" * 60


def section(title: str, desc: str) -> None:
    print(f"\n[{title}]  {desc}")


robot = FanucRobot(model="ER-4iA", host="127.0.0.1")
robot.connect()

print(BAR)
print("▶ FANUC 巡邏路線 (patrol_route.py)")
print(BAR)

print(
    "跑一小段巡邏路線，所有點位都是相對於目前位置定義的，所以不管機器人\n"
    "現在在哪裡都能安全執行。跑之前先確認機器人周圍淨空；整段路線都在\n"
    "起點附近幾度/幾公分的範圍內。"
)

section("變體 1", "記錄起點位置")
start_joints = robot.get_curjpos().to_list()
start_pose = robot.get_curpos().to_list()
print(f"  起點關節角度: {start_joints}")
print(f"  起點直角座標: {start_pose}")

section("變體 2", "組出路線（關節點位，相對於起點）")
corner_a = list(start_joints)
corner_a[0] += 5.0  # J1 +5 度
corner_b = list(start_joints)
corner_b[0] += 5.0
corner_b[4] -= 5.0  # J1 +5 度, J5 -5 度
corner_c = list(start_joints)
corner_c[4] -= 5.0  # J5 -5 度
route = [
    ("角點 A (J1 +5)", corner_a),
    ("角點 B (J1 +5, J5 -5)", corner_b),
    ("角點 C (J5 -5)", corner_c),
    ("回到起點", start_joints),
]
for label, values in route:
    print(f"  {label}: {values}")

section("變體 3", "執行關節點位（中間用 CNT 混合，最後一點才精確停止）")
for i, (label, values) in enumerate(route, 1):
    is_last = i == len(route)
    cnt_val = 0 if is_last else 50  # 只有最後一個點用 FINE（精確停止）
    print(f"  [{i}] {label}")
    print(f"  送出: move_joint({values}, velocity=25, cnt_val={cnt_val})")
    robot.move_joint(values, velocity=25, cnt_val=cnt_val)
print(f"  完成，關節角度: {robot.get_curjpos().to_list()}")

section("變體 4", "一段直角座標動作（move_pose，直線內插）")
nudged_pose = list(start_pose)
nudged_pose[2] += 20.0  # Z +20mm，直直往上
print(f"  送出: move_pose({nudged_pose}, velocity=20, linear=True)")
robot.move_pose(nudged_pose, velocity=20, linear=True)
print(f"  送出: move_pose({start_pose}, velocity=20, linear=True)  # 再往下回去")
robot.move_pose(start_pose, velocity=20, linear=True)
print(f"  完成，直角座標: {robot.get_curpos().to_list()}")

print(f"\n{BAR}")

robot.disconnect()
