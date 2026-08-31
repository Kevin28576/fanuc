"""Reads and writes registers and system variables. Only this one
feature.

R[n], PR[n], SR[n], the joint-type position register, DI[n], system
variables.
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
print("▶ FANUC registers/system variables test (registers_io.py)")
print(BAR)

print(
    "Reads and writes registers and system variables, covering R[n],\n"
    "PR[n], SR[n], the joint-type position register, DI[n], and system\n"
    "variables."
)

section("Variant 1", "Numeric register R[n]")
print("  sending: set_reg(1, 100)")
robot.set_reg(1, 100)
print(f"  result: R[1] = {robot.get_reg(1)}")

section("Variant 2", "Same R[n], a decimal point writes it as a real")
print("  sending: set_reg(1, 1.5)")
robot.set_reg(1, 1.5)
print(f"  result: R[1] = {robot.get_reg(1)}")

section("Variant 3", "Position register PR[n] (Cartesian)")
pr_vals = [290, 0, 210, -180, 0, 0]
print(f"  sending: set_preg(81, {pr_vals})")
robot.set_preg(81, pr_vals)
print("  result: PR[81] =")
for line in robot.get_preg(81).format().splitlines():
    print(f"    {line}")

section("Variant 4", "String register SR[n]")
print('  sending: set_sreg(1, "hello")')
robot.set_sreg(1, "hello")
print(f"  result: SR[1] = {robot.get_sreg(1)}")

section("Variant 5", "Position register PR[n] (joint type)")
jpr_vals = [0, -30, 0, 0, -90, 0]
print(f"  sending: set_jpreg(90, {jpr_vals})")
robot.set_jpreg(90, jpr_vals)
print("  result: PR[90] (joint type) =")
for line in robot.get_jpreg(90).format().splitlines():
    print(f"    {line}")

section("Variant 6", "Digital input DI[n] (read-only)")
print(f"  result: DI[1] = {robot.get_din(1)}")

section("Variant 7", "System variable and override speed (read-only)")
print(f"  result: $MCR.$GENOVERRIDE = {robot.get_sys_var('$MCR.$GENOVERRIDE')}")
print(f"  result: override = {robot.get_override()}%")

print(f"\n{BAR}")

robot.disconnect()
