"""RobotApp 任務框架，寫成可重複執行、被排程器或 Web API 呼叫的樣子。

只示範這一個功能：`configure()` / `_main()` / `run()` 這個生命週期，
跟 `AppResult` 怎麼用。任務內容故意寫得很單純（回目前位置一次）。
"""

from fanuc import FanucRobot, RobotApp

BAR = "=" * 60


class GoHomeApp(RobotApp):
    def __init__(self, robot: FanucRobot):
        self.robot = robot

    def configure(self) -> None:
        pass  # 靜態設定，不連線；這個任務沒有參數可設

    def _main(self, **kwargs: object) -> str:
        self.robot.connect()
        try:
            before = self.robot.get_curpos()
            print("  送出: move_home()")
            self.robot.move_home()
            after = self.robot.get_curpos()
            return f"before={before.to_list()} -> after={after.to_list()}"
        finally:
            self.robot.disconnect()


if __name__ == "__main__":
    print(BAR)
    print("▶ FANUC RobotApp 任務框架測試 (robot_app.py)")
    print(BAR)

    print(
        "示範 RobotApp 的生命週期：configure() 做靜態設定、_main() 是任務\n"
        "本體、run() 負責連線例外都包成 AppResult，成功回傳結果、失敗回傳\n"
        "錯誤訊息，呼叫端不用自己包 try/except。move_home() 移動到哪個\n"
        "姿態是建構 FanucRobot 時的 home_joints 參數決定的，這裡用預設值，\n"
        "詳見 examples/home_position.py。"
    )

    robot = FanucRobot(
        model="ER-4iA",
        host="127.0.0.1",
    )
    app = GoHomeApp(robot)
    app.configure()
    result = app.run()

    if result:
        print(f"\n完成: {result.result}")
    else:
        print(f"\n失敗:\n{result.message}")

    print(f"\n{BAR}")
