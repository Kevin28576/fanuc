"""雙訊號夾爪控制。只示範這一個功能。

夾爪是雙訊號接法（SCHUNK EGP 小型零件夾爪，接在 EE Pinout），開、合各是
獨立的 RDO，不是同一條訊號的正反。RO7/RO8 這組對應已經在實機上確認過：
RO7=ON、RO8=OFF 是開，RO7=OFF、RO8=ON 是關。換夾爪、換接線方式的話
這組編號要照你自己的接線說明書重新確認，不要照抄。

gripper_travel 是「未驗證」的佔位值，不是量過的真實數字，夾爪送出
開/合訊號後，實際爪子要花多久才走完行程，沒有通用的安全預設值，套件
會強制要求這個參數，就是不讓這種數字被隨便帶過。正式使用前務必照你
夾爪的規格書，或用碼表實際量一次開闔動作，換成真實數字。
"""

from fanuc import FanucRobot

BAR = "=" * 60


def section(title: str, desc: str) -> None:
    print(f"\n[{title}]  {desc}")


robot = FanucRobot(
    model="ER-4iA",
    host="127.0.0.1",
    ee_DO_type="RDO",
    ee_open_num=7,
    ee_close_num=8,
    gripper_travel="0.1s",  # 見檔案開頭說明，正式使用前請換成量過的真實值
)
robot.connect()

print(BAR)
print("▶ FANUC 夾爪控制測試 (gripper_control.py)")
print(BAR)

print(
    "開、合、重置、讀狀態。雙訊號接法（開、合各是獨立的 RDO），RO7/RO8\n"
    "這組編號是這台驗證環境實測確認的，換夾爪、換接線方式要照你自己的\n"
    "說明書重新確認。"
)

section("變體 1", "讀取目前狀態")
print(f"  結果: {robot.get_gripper()}")

section("變體 2", "合起夾爪")
print("  送出: gripper(True)")
print(f"  等待 gripper_travel（{robot.gripper_travel}）後才返回，確保夾爪真的走完行程")
robot.gripper(True)
print(f"  結果: {robot.get_gripper()}")

section("變體 3", "開啟夾爪")
print("  送出: gripper(False)")
print(f"  等待 gripper_travel（{robot.gripper_travel}）後才返回，確保夾爪真的走完行程")
robot.gripper(False)
print(f"  結果: {robot.get_gripper()}")

section("變體 4", "重置夾爪（開合訊號同時 True，清警報用）")
print("  送出: gripper_reset()")
print(f"  等待 gripper_travel（{robot.gripper_travel}）後才返回，確保重置動作真的做完")
robot.gripper_reset()
print(f"  結果: {robot.get_gripper()}")

print(f"\n{BAR}")

robot.disconnect()
