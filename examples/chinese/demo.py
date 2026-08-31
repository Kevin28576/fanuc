"""最小示範。

連線、讀狀態、動一小段、讀寫 DOUT。跑之前確認機器人四周淨空。
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
    gripper_travel="1s",  # 未驗證的佔位值，正式使用前請換成量過的真實值
)

robot.connect()

print(BAR)
print("▶ FANUC 最小示範 (demo.py)")
print(BAR)

print(
    "連線、讀狀態、動一小段、讀寫 DOUT。跑之前確認機器人四周淨空，\n"
    "會小幅擺動 J1 再擺回去。"
)

section("變體 1", "讀取目前狀態")
cur_pos = robot.get_curpos()
cur_jpos = robot.get_curjpos()
print(f"  直角座標: {cur_pos.to_list()}")
print(f"  關節角度: {cur_jpos.to_list()}")

section("變體 2", "在關節空間動一小段（J1 加 0.5 度）")
target = cur_jpos.to_list()
target[0] += 0.5
print(f"  送出: move('joint', {target}, velocity=25, acceleration=100, cnt_val=0, linear=False)")
robot.move("joint", target, velocity=25, acceleration=100, cnt_val=0, linear=False)
cur_pos = robot.get_curpos()
cur_jpos = robot.get_curjpos()
print(f"  完成，直角座標: {cur_pos.to_list()}")
print(f"  完成，關節角度: {cur_jpos.to_list()}")

section("變體 3", "讀寫數位輸出 DO[1]")
print(f"  原本: DO[1] = {robot.get_dout(1)}")
print("  送出: set_dout(1, True)")
robot.set_dout(1, True)
print(f"  結果: DO[1] = {robot.get_dout(1)}")

print(f"\n{BAR}")

robot.disconnect()
