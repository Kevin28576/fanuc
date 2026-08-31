"""home 姿態怎麼設定。只示範這一個功能。

move_home() 移動到的姿態不是寫死的，是建構 FanucRobot 時的
home_joints 參數決定的。不指定的話，用套件內建的預設值
（limits.DEFAULT_HOME_JOINTS，這台驗證機 ER-4iA 的官方 home 姿態，
讀自 ROBOGUIDE 的「目前位置」面板），換機器人時記得帶自己的
home_joints，不要照抄。
"""

from fanuc import FanucRobot
from fanuc.limits import DEFAULT_HOME_JOINTS

BAR = "=" * 60


def section(title: str, desc: str) -> None:
    print(f"\n[{title}]  {desc}")


print(BAR)
print("▶ FANUC home 姿態設定測試 (home_position.py)")
print(BAR)

print(
    "move_home() 移動到的姿態由建構 FanucRobot 時的 home_joints 參數\n"
    "決定，不是寫死的。不指定就用套件內建的預設值，換機器人時記得帶\n"
    "自己的 home_joints，不要照抄這台驗證機的數字。"
)

section("變體 1", "不指定 home_joints，用內建預設值")
robot_default = FanucRobot(model="ER-4iA", host="127.0.0.1")
print(f"  home_joints = {list(robot_default.home_joints)}")
print(f"  等於套件內建的 limits.DEFAULT_HOME_JOINTS = {list(DEFAULT_HOME_JOINTS)}")

section("變體 2", "建構時自訂 home_joints")
custom_home = [10, -20, 0, 0, -70, 0]
robot_custom = FanucRobot(model="ER-4iA", host="127.0.0.1", home_joints=custom_home)
print(f"  送出: FanucRobot(..., home_joints={custom_home})")
print(f"  home_joints = {list(robot_custom.home_joints)}")

section("變體 3", "實際移動到 home（用自訂的那個機器人物件）")
robot_custom.connect()
before = robot_custom.get_curjpos().to_list()
print(f"  移動前關節角度: {before}")
print("  送出: move_home()")
robot_custom.move_home(velocity=25)
after = robot_custom.get_curjpos().to_list()
print(f"  移動後關節角度: {after}")
robot_custom.disconnect()

print(f"\n{BAR}")
