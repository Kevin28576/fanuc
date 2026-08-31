"""Calls a program on the TP and waits for it to finish. Only this one
feature.

call_prog() blocks until that TP program finishes before returning,
same as move(). Which program runs and what it does is entirely up to
the actual TP program on the controller; this package has no say in
that, so confirm it on the TP yourself before running this.

This example deliberately doesn't call any real program: testing it
once with a nonexistent program name apparently caused MAPPDK_SERVER
to abort, needing a TP RESET to bring back up. That risk is higher
than expected, so this only prints an explanation and never actually
sends call_prog(). To try it for real, uncomment the
CALL_A_REAL_PROGRAM block below and replace it with a program name
that actually exists on your controller and whose content you've
confirmed is safe.
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
print("▶ FANUC call TP program test (call_prog.py)")
print(BAR)

print(
    "call_prog(prog_name) calls a program on the TP and waits for it to\n"
    "finish, a blocking call just like move(). This example never actually\n"
    "calls anything: testing with a nonexistent program name apparently\n"
    "made MAPPDK_SERVER abort, needing a TP RESET to recover, a bigger risk\n"
    "than expected, so this just explains the usage in text."
)

section("Variant 1", "Explanation only, nothing is actually called")
print("  usage: robot.call_prog('program name')")
print("  behavior: blocks until that TP program finishes, returns a completion message")
print("  caution: the package never checks whether the program name exists or")
print("           is safe to run; confirm it on the TP yourself before calling")

# --- to actually try this yourself, uncomment below and use a real,
#     confirmed-safe program name ---
# CALL_A_REAL_PROGRAM = "your program name"
# print(f"\n  sending: call_prog({CALL_A_REAL_PROGRAM!r})")
# result = robot.call_prog(CALL_A_REAL_PROGRAM)
# print(f"  done: {result}")

print(f"\n{BAR}")

robot.disconnect()
