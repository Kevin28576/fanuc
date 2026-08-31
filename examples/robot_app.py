"""The RobotApp task framework, written the way it'd look as a
repeatable task callable by a scheduler or a web API.

Only this one feature: the configure() / _main() / run() lifecycle,
and how AppResult is used. The task body is deliberately trivial
(returns to the current position once).
"""

from fanuc import FanucRobot, RobotApp

BAR = "=" * 60


class GoHomeApp(RobotApp):
    def __init__(self, robot: FanucRobot):
        self.robot = robot

    def configure(self) -> None:
        pass  # static setup, no connection; this task has no parameters to set

    def _main(self, **kwargs: object) -> str:
        self.robot.connect()
        try:
            before = self.robot.get_curpos()
            print("  sending: move_home()")
            self.robot.move_home()
            after = self.robot.get_curpos()
            return f"before={before.to_list()} -> after={after.to_list()}"
        finally:
            self.robot.disconnect()


if __name__ == "__main__":
    print(BAR)
    print("▶ FANUC RobotApp task framework test (robot_app.py)")
    print(BAR)

    print(
        "Demonstrates the RobotApp lifecycle: configure() does static setup,\n"
        "_main() is the task body, run() wraps connection errors into an\n"
        "AppResult, returning the result on success or the error message on\n"
        "failure, so the caller never has to wrap it in try/except.\n"
        "move_home() moves to whatever pose the home_joints parameter\n"
        "decided at construction; this uses the default, see\n"
        "examples/home_position.py."
    )

    robot = FanucRobot(
        model="ER-4iA",
        host="127.0.0.1",
    )
    app = GoHomeApp(robot)
    app.configure()
    result = app.run()

    if result:
        print(f"\ndone: {result.result}")
    else:
        print(f"\nfailed:\n{result.message}")

    print(f"\n{BAR}")
