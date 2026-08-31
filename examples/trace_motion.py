"""Records the actual trajectory of a move. Only this one feature.

On the main connection (S8), movej blocks until the move finishes, so
position can't be queried during that time. This uses MotionTracer to
open a separate connection (S7/logger) that polls in the background
while the move is in flight, recording the actual path taken, and
saves it as a CSV.

Confirm the robot's surroundings are clear before running; this
nudges J1 a little and moves it back.
"""

import csv

from fanuc import FanucRobot, MotionTracer

BAR = "=" * 60


def section(title: str, desc: str) -> None:
    print(f"\n[{title}]  {desc}")


mover = FanucRobot(model="ER-4iA", host="127.0.0.1")
tracer = MotionTracer(model="ER-4iA", host="127.0.0.1", port=18736, interval="20ms")

mover.connect()
tracer.connect()

print(BAR)
print("▶ FANUC motion trajectory recording test (trace_motion.py)")
print(BAR)

print(
    "movej blocks on the main connection (S8) until the move finishes, so\n"
    "position can't be queried; this opens a separate connection\n"
    "(S7/logger) that polls in the background while the move is in\n"
    "flight, recording the actual path taken. This nudges J1 a little and\n"
    "moves it back, confirm the robot's surroundings are clear first."
)

here = mover.get_curjpos().to_list()
target = list(here)
target[0] += 10.0  # J1 nudged 10 degrees, for the demo, safe regardless of where the robot is

section("Variant 1", "Move while polling in the background")
print(f"  sending: move('joint', {target}, velocity=15)")
tracer.start()
mover.move("joint", target, velocity=15)
samples = tracer.stop()
print(f"  done, recorded {len(samples)} samples")

section("Variant 2", "Move back")
print(f"  sending: move('joint', {here}, velocity=15)")
mover.move("joint", here, velocity=15)
print("  done")

tracer.disconnect()
mover.disconnect()

print(f"\nwriting trace.csv ({len(samples)} samples)")
with open("trace.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["t", "x", "y", "z", "w", "p", "r"])
    for s in samples:
        writer.writerow([f"{s.t:.3f}", s.pose.x, s.pose.y, s.pose.z,
                         s.pose.w, s.pose.p, s.pose.r])

print(f"\n{BAR}")
