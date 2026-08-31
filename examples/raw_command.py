"""Sends a raw command string, and works with RDO. Only these two
features.

send_raw() is for a command that hasn't been wrapped into a method
yet, or for trying something out right after extending the KAREL
driver: it skips the package's encoding/parsing and just sends the
string, returning the message content. RDO is a separate numbering
space for digital outputs, a different signal from DO.
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
print("▶ FANUC raw command and generic RDO test (raw_command.py)")
print(BAR)

print(
    "send_raw() skips the package's encoding/parsing, sends the string\n"
    "directly and returns the message content, for trying out a command\n"
    "not wrapped into a method yet. RDO is a digital output numbering\n"
    "space separate from DO; this operates RDO number 1 directly."
)

section("Variant 1", "send_raw sends the same command as get_curpos()")
print("  sending: send_raw('curpos')")
raw_result = robot.send_raw("curpos")
print(f"  result: {raw_result}")

section("Variant 2", "Read RDO[1]")
print(f"  RDO number upper bound (depends on driver version): {robot.max_rdo_num}")
before_rdo = robot.get_rdo(1)
print(f"  result: RDO[1] = {before_rdo}")

section("Variant 3", "Set RDO[1], read it back to confirm")
print("  sending: set_rdo(1, True)")
robot.set_rdo(1, True)
print(f"  result: RDO[1] = {robot.get_rdo(1)}")

print(f"\n{BAR}")

robot.disconnect()
