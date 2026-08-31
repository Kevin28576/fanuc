"""直接送原始指令字串,跟操作 RDO。只示範這兩個功能。

send_raw() 是給還沒包成方法、或自己擴充 KAREL driver 後要先試試看
的指令用的,跳過套件的編碼/解析,直接送字串、拿回訊息內容。RDO 是
機器人數位輸出的另一組編號空間,跟 DO 是不同的訊號。
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
print("▶ FANUC 原始指令與通用 RDO 測試 (raw_command.py)")
print(BAR)

print(
    "send_raw() 跳過套件的編碼/解析，直接送字串、拿回訊息內容，給還沒\n"
    "包成方法的指令試用。RDO 是獨立於 DO 之外的另一組數位輸出編號，\n"
    "這裡直接操作 1 號 RDO。"
)

section("變體 1", "send_raw 送出跟 get_curpos() 一樣的指令")
print("  送出: send_raw('curpos')")
raw_result = robot.send_raw("curpos")
print(f"  結果: {raw_result}")

section("變體 2", "讀取 RDO[1]")
print(f"  RDO 編號上限（依 driver 版本而定）: {robot.max_rdo_num}")
before_rdo = robot.get_rdo(1)
print(f"  結果: RDO[1] = {before_rdo}")

section("變體 3", "設定 RDO[1]，再讀回確認")
print("  送出: set_rdo(1, True)")
robot.set_rdo(1, True)
print(f"  結果: RDO[1] = {robot.get_rdo(1)}")

print(f"\n{BAR}")

robot.disconnect()
