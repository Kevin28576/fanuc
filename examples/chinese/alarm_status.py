"""讀警報。只示範這一個功能。"""

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
print("▶ FANUC 警報讀取測試 (alarm_status.py)")
print(BAR)

print(
    "讀最近一筆警報。get_alarm() 回傳具名的 Alarm 型別，一次給 6 個欄位：\n"
    "代碼、嚴重度、原因代碼、時間戳、發生時的程式名稱、訊息內容。只能讀\n"
    "「最近一筆」。實測傳不同序號進去 ERR_DATA，回來的都是同一筆，目前看\n"
    "下來沒辦法指定讀第幾筆歷史警報，但不排除是還沒找到正確用法，細節見\n"
    "docs/zh/protocol.md。"
)

section("變體 1", "讀取完整內容（Alarm 的全部 6 個欄位）")
alarm = robot.get_alarm()
field("Code", alarm.code)
field("Severity", alarm.severity)
field("Cause Code", alarm.cause_code)
field("Time", f"{alarm.time} (視為不透明數字)")
field("Program", alarm.program or "(無)")
field("Message", alarm.message)

section("變體 2", "只取常用的代碼跟訊息，組成一行摘要")
print(f"  [{alarm.code}] 嚴重度 {alarm.severity}  {alarm.message}")

print(f"\n{BAR}")

robot.disconnect()
