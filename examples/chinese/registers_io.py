"""讀寫暫存器跟系統變數。只示範這一個功能。

R[n]、PR[n]、SR[n]、關節型位置暫存器、DI[n]、系統變數。
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
print("▶ FANUC 暫存器/系統變數測試 (registers_io.py)")
print(BAR)

print(
    "讀寫暫存器跟系統變數,涵蓋 R[n]、PR[n]、SR[n]、關節型位置暫存器、\n"
    "DI[n]、系統變數。"
)

section("變體 1", "整數暫存器 R[n]")
print("  送出: set_reg(1, 100)")
robot.set_reg(1, 100)
print(f"  結果: R[1] = {robot.get_reg(1)}")

section("變體 2", "同一個 R[n]，帶小數點就寫成實數")
print("  送出: set_reg(1, 1.5)")
robot.set_reg(1, 1.5)
print(f"  結果: R[1] = {robot.get_reg(1)}")

section("變體 3", "位置暫存器 PR[n]（直角座標）")
pr_vals = [290, 0, 210, -180, 0, 0]
print(f"  送出: set_preg(81, {pr_vals})")
robot.set_preg(81, pr_vals)
print("  結果: PR[81] =")
for line in robot.get_preg(81).format().splitlines():
    print(f"    {line}")

section("變體 4", "字串暫存器 SR[n]")
print('  送出: set_sreg(1, "hello")')
robot.set_sreg(1, "hello")
print(f"  結果: SR[1] = {robot.get_sreg(1)}")

section("變體 5", "位置暫存器 PR[n]（關節型）")
jpr_vals = [0, -30, 0, 0, -90, 0]
print(f"  送出: set_jpreg(90, {jpr_vals})")
robot.set_jpreg(90, jpr_vals)
print("  結果: PR[90]（關節型）=")
for line in robot.get_jpreg(90).format().splitlines():
    print(f"    {line}")

section("變體 6", "數位輸入 DI[n]（只讀）")
print(f"  結果: DI[1] = {robot.get_din(1)}")

section("變體 7", "系統變數與速度倍率（只讀）")
print(f"  結果: $MCR.$GENOVERRIDE = {robot.get_sys_var('$MCR.$GENOVERRIDE')}")
print(f"  結果: 速度倍率 = {robot.get_override()}%")

print(f"\n{BAR}")

robot.disconnect()
