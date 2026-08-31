"""Minimal demo.

Connect, read state, move a bit, read/write DOUT. Confirm the robot's
surroundings are clear before running.
"""

from fanuc import FanucRobot

BAR = "=" * 60


def section(title: str, desc: str) -> None:
    print(f"\n[{title}]  {desc}")


robot = FanucRobot(
    model="ER-4iA",
    host="127.0.0.1",
    port=18735,
    ee_DO_type="RDO",
    ee_DO_num=7,
    gripper_travel="1s",  # unverified placeholder, replace with a measured real value before real use
)

robot.connect()

print(BAR)
print("▶ FANUC minimal demo (demo.py)")
print(BAR)

print(
    "Connect, read state, move a bit, read/write DOUT. Confirm the robot's\n"
    "surroundings are clear before running; this nudges J1 a little and\n"
    "moves it back."
)

section("Variant 1", "Read the current state")
cur_pos = robot.get_curpos()
cur_jpos = robot.get_curjpos()
print(f"  cartesian: {cur_pos.to_list()}")
print(f"  joints: {cur_jpos.to_list()}")

section("Variant 2", "Move a bit in joint space (J1 + 0.5 deg)")
target = cur_jpos.to_list()
target[0] += 0.5
print(f"  sending: move('joint', {target}, velocity=25, acceleration=100, cnt_val=0, linear=False)")
robot.move("joint", target, velocity=25, acceleration=100, cnt_val=0, linear=False)
cur_pos = robot.get_curpos()
cur_jpos = robot.get_curjpos()
print(f"  done, cartesian: {cur_pos.to_list()}")
print(f"  done, joints: {cur_jpos.to_list()}")

section("Variant 3", "Read/write digital output DO[1]")
print(f"  before: DO[1] = {robot.get_dout(1)}")
print("  sending: set_dout(1, True)")
robot.set_dout(1, True)
print(f"  result: DO[1] = {robot.get_dout(1)}")

print(f"\n{BAR}")

robot.disconnect()
