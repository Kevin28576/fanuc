"""Reads the instantaneous power draw. Only this one feature.

The $MOR_GRP.$INS_PWR system variable the driver reads is in kW;
get_ins_power() already converts it to W.
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
print("▶ FANUC instantaneous power reading test (power_reading.py)")
print(BAR)

print(
    "Reads the instantaneous power draw; the driver returns kW, and\n"
    "get_ins_power() already converts it to W."
)

section("Variant 1", "Read the power draw once")
watts = robot.get_ins_power()
print(f"  result: {watts} W")

section("Variant 2", "Read a few times in a row, the value moves with load")
for i in range(3):
    print(f"  [{i + 1}] {robot.get_ins_power()} W")

print(f"\n{BAR}")

robot.disconnect()
