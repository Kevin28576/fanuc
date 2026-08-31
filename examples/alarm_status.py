"""Reads the alarm. Only this one feature."""

from fanuc import FanucRobot

BAR = "=" * 60


def section(title: str, desc: str) -> None:
    print(f"\n[{title}]  {desc}")


def field(key: str, value: object) -> None:
    print(f"  • {key:<11}: {value}")


robot = FanucRobot(
    model="ER-4iA",
    host="127.0.0.1",
)
robot.connect()

print(BAR)
print("▶ FANUC alarm reading test (alarm_status.py)")
print(BAR)

print(
    "Reads the most recent alarm. get_alarm() returns a named Alarm type\n"
    "with 6 fields at once: code, severity, cause code, timestamp, the\n"
    "program running when it fired, and the message. Only the \"most\n"
    "recent\" one is readable. Testing showed passing different sequence\n"
    "numbers into ERR_DATA always returns the same entry; there's currently\n"
    "no known way to pick which historical alarm to read, though that may\n"
    "just be a wrong usage rather than a hard limit. See docs/protocol.md\n"
    "for details."
)

section("Variant 1", "Read the full content (all 6 Alarm fields)")
alarm = robot.get_alarm()
field("Code", alarm.code)
field("Severity", alarm.severity)
field("Cause Code", alarm.cause_code)
field("Time", f"{alarm.time} (treat as opaque)")
field("Program", alarm.program or "(none)")
field("Message", alarm.message)

section("Variant 2", "Just the code and message, as one summary line")
print(f"  [{alarm.code}] severity {alarm.severity}  {alarm.message}")

print(f"\n{BAR}")

robot.disconnect()
