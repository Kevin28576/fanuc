"""記錄一段移動的實際軌跡。只示範這一個功能。

主連線(S8)下 movej 會卡住直到動作完成,這段時間查不了位置,所以用
MotionTracer 開一條獨立連線(S7/logger)背景輪詢,跟移動同時進行,記錄下
實際走過的軌跡,存成 CSV。

跑之前確認機器人四周淨空,會小幅擺動 J1 再擺回去。
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
print("▶ FANUC 移動軌跡記錄測試 (trace_motion.py)")
print(BAR)

print(
    "movej 在主連線(S8)上會卡住直到動作完成,查不了位置,所以另開一條\n"
    "獨立連線(S7/logger)背景輪詢,跟移動同時進行,記錄實際走過的軌跡。\n"
    "會小幅擺動 J1 再擺回去,跑之前確認機器人四周淨空。"
)

here = mover.get_curjpos().to_list()
target = list(here)
target[0] += 10.0  # J1 擺動 10 度,示範用,不管機器人在哪都安全

section("變體 1", "背景輪詢中執行移動")
print(f"  送出: move('joint', {target}, velocity=15)")
tracer.start()
mover.move("joint", target, velocity=15)
samples = tracer.stop()
print(f"  完成，記錄到 {len(samples)} 筆取樣")

section("變體 2", "回原位")
print(f"  送出: move('joint', {here}, velocity=15)")
mover.move("joint", here, velocity=15)
print("  完成")

tracer.disconnect()
mover.disconnect()

print(f"\n寫入 trace.csv（共 {len(samples)} 筆取樣）")
with open("trace.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["t", "x", "y", "z", "w", "p", "r"])
    for s in samples:
        writer.writerow([f"{s.t:.3f}", s.pose.x, s.pose.y, s.pose.z,
                         s.pose.w, s.pose.p, s.pose.r])

print(f"\n{BAR}")
