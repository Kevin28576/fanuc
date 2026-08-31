"""讀取瞬時功率。只示範這一個功能。

$MOR_GRP.$INS_PWR 這顆系統變數，driver 讀到的原始單位是 kW，
get_ins_power() 已經幫忙換算成 W。
"""

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
print("▶ FANUC 瞬時功率讀取測試 (power_reading.py)")
print(BAR)

print(
    "讀取瞬時功率，driver 回傳的原始單位是 kW，get_ins_power() 已經\n"
    "換算成 W。"
)

section("變體 1", "讀取一次瞬時功率")
watts = robot.get_ins_power()
print(f"  結果: {watts} W")

section("變體 2", "連續讀幾次，數值會隨負載變動")
for i in range(3):
    print(f"  [{i + 1}] {robot.get_ins_power()} W")

print(f"\n{BAR}")

robot.disconnect()
