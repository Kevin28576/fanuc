"""呼叫 TP 上的程式，等它跑完。只示範這一個功能。

call_prog() 會阻塞直到那支 TP 程式執行完畢才返回,跟 move() 一樣是
同步呼叫。跑的是哪支程式、程式裡做了什麼完全由控制器上實際存在的
TP 程式決定,這支套件管不到,示範前務必自己去 TP 上確認過。

這支範例故意不實際呼叫任何程式:曾經用一個不存在的程式名稱做示範,
結果疑似讓 MAPPDK_SERVER 中止,需要 TP RESET 才能重新啟動,風險比
預期的高,所以這裡只做文字說明,不會真的送出 call_prog()。要自己
試的話,把下面 CALL_A_REAL_PROGRAM 那段的註解拿掉,換成控制器上
實際存在、確認過內容安全的 TP 程式名稱。
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
print("▶ FANUC 呼叫 TP 程式測試 (call_prog.py)")
print(BAR)

print(
    "call_prog(prog_name) 呼叫 TP 上的程式並等它跑完，跟 move() 一樣是\n"
    "阻塞式呼叫。這支範例不會真的呼叫任何程式：用不存在的程式名稱\n"
    "測試時，疑似讓 MAPPDK_SERVER 中止，需要 TP RESET 才能重開，風險\n"
    "比預期高，所以只做文字說明。"
)

section("變體 1", "純說明，不實際呼叫")
print("  用法: robot.call_prog('程式名稱')")
print("  行為: 阻塞直到那支 TP 程式跑完才返回，回傳值是完成訊息")
print("  注意: 程式名稱是否存在、內容是否安全，套件完全不檢查，")
print("        自己去 TP 上確認過才呼叫")

# --- 要自己實際測試的話,取消下面這段註解,換成真實、確認過安全的程式名稱 ---
# CALL_A_REAL_PROGRAM = "你的程式名稱"
# print(f"\n  送出: call_prog({CALL_A_REAL_PROGRAM!r})")
# result = robot.call_prog(CALL_A_REAL_PROGRAM)
# print(f"  完成: {result}")

print(f"\n{BAR}")

robot.disconnect()
