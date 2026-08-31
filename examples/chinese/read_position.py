"""讀目前位置，姿態跟關節角度都印出來。只示範這一個功能。

CLI 也有一樣的功能（`fanuc pos`、`fanuc watch`），這支是給要直接看
Python API 怎麼呼叫的人看的。
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
print("▶ FANUC 讀取目前位置測試 (read_position.py)")
print(BAR)

print(
    "只示範讀取這一個功能：姿態（Pose）跟關節角度（Joints）都讀一次，\n"
    "再示範兩種取值方式（格式化字串、直接解包）。"
)

section("變體 1", "讀取姿態與關節角度（格式化輸出）")
pose = robot.get_curpos()
joints = robot.get_curjpos()
print("  pose:")
for line in pose.format().splitlines():
    print(f"    {line}")
print("  joints:")
for line in joints.format().splitlines():
    print(f"    {line}")

section("變體 2", "Pose 可以直接解包，也可以轉成 list")
x, y, z, w, p, r = pose
print(f"  解包: X={x:.1f} Y={y:.1f} Z={z:.1f} W={w:.1f} P={p:.1f} R={r:.1f}")
print(f"  to_list(): {pose.to_list()}")

print(f"\n{BAR}")

robot.disconnect()
