"""動作前先問控制器合不合法/到不到得了。只示範這一個功能。"""

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
print("▶ FANUC 可達性檢查測試 (check_reachability.py)")
print(BAR)

print(
    "動作前先問控制器合不合法/到不到得了，不會真的送出動作指令，不會讓\n"
    "機器人移動。check_joint() 走控制器內建的 J_IN_RANGE，連 J2/J3 機構\n"
    "耦合限制都算進去；check_pose() 走跟 movep 同一套 CHECK_EPOS 判斷。"
)

section("變體 1", "關節角度合法的情況")
joint_vals = [45, -20, 15, 0, -45, 90]
print(f"  送出: {joint_vals}")
result = robot.check_joint(joint_vals)
print(f"  合法嗎: {result.ok}")
print(f"  說明  : {result.describe()}")

section("變體 2", "關節角度不合法的情況（故意給超出範圍的角度）")
bad_joint_vals = [45, -200, 15, 0, -45, 90]
print(f"  送出: {bad_joint_vals}")
bad = robot.check_joint(bad_joint_vals)
print(f"  合法嗎: {bad.ok}")
print(f"  說明  : {bad.describe()}")

section("變體 3", "直角座標到得了的情況（用機器人目前位置，一定到得了）")
here_vals = robot.get_curpos().to_list()
print(f"  送出: {here_vals}")
reachable = robot.check_pose(here_vals)
print(f"  到得了嗎: {reachable}")

section("變體 4", "直角座標到不了的情況")
pose_vals = [400, 50, -100, -180, 0, 0]
print(f"  送出: {pose_vals}")
unreachable = robot.check_pose(pose_vals)
print(f"  到得了嗎: {unreachable}")

print(f"\n{BAR}")

robot.disconnect()
