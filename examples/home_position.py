"""How the home pose is configured. Only this one feature.

The pose move_home() goes to isn't hardcoded; it's decided by the
home_joints parameter when constructing FanucRobot. Without it, the
package's built-in default is used (limits.DEFAULT_HOME_JOINTS, the
official home pose for this ER-4iA verification unit, read off
ROBOGUIDE's "Current Position" panel). Bring your own home_joints when
switching robots, don't copy this one.
"""

from fanuc import FanucRobot
from fanuc.limits import DEFAULT_HOME_JOINTS

BAR = "=" * 60


def section(title: str, desc: str) -> None:
    print(f"\n[{title}]  {desc}")


print(BAR)
print("▶ FANUC home pose configuration test (home_position.py)")
print(BAR)

print(
    "The pose move_home() goes to is decided by the home_joints parameter\n"
    "when constructing FanucRobot, not hardcoded. Without it, the package's\n"
    "built-in default is used; bring your own home_joints when switching\n"
    "robots, don't copy this verification unit's numbers."
)

section("Variant 1", "No home_joints given, uses the built-in default")
robot_default = FanucRobot(model="ER-4iA", host="127.0.0.1")
print(f"  home_joints = {list(robot_default.home_joints)}")
print(f"  equals the package's built-in limits.DEFAULT_HOME_JOINTS = {list(DEFAULT_HOME_JOINTS)}")

section("Variant 2", "Custom home_joints at construction time")
custom_home = [10, -20, 0, 0, -70, 0]
robot_custom = FanucRobot(model="ER-4iA", host="127.0.0.1", home_joints=custom_home)
print(f"  sending: FanucRobot(..., home_joints={custom_home})")
print(f"  home_joints = {list(robot_custom.home_joints)}")

section("Variant 3", "Actually move to home (using that custom robot object)")
robot_custom.connect()
before = robot_custom.get_curjpos().to_list()
print(f"  joint angles before: {before}")
print("  sending: move_home()")
robot_custom.move_home(velocity=25)
after = robot_custom.get_curjpos().to_list()
print(f"  joint angles after: {after}")
robot_custom.disconnect()

print(f"\n{BAR}")
