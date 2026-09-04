"""Tests for the offline forward/inverse kinematics module.

These only check internal self-consistency (fk(ik(pose)) ~= pose,
ik(fk(joints)) ~= joints) and basic error handling. They cannot
verify the link geometry against a real robot; see kinematics.py's
module docstring for that caveat.
"""

import math

import pytest

from fanuc.kinematics import (
    ForwardKinematicsError,
    InverseKinematicsError,
    forward,
    inverse,
)
from fanuc.types import Joints, Pose


def test_forward_zero_pose_is_deterministic() -> None:
    pose = forward(Joints((0.0, 0.0, 0.0, 0.0, 0.0, 0.0)))
    assert isinstance(pose, Pose)
    # Same input always gives the same output (pure computation).
    pose2 = forward([0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    assert pose.to_list() == pose2.to_list()


def test_forward_wrong_joint_count_raises() -> None:
    with pytest.raises(ForwardKinematicsError):
        forward([0.0, 0.0, 0.0])


def test_forward_accepts_plain_sequence_and_joints_equally() -> None:
    vals = (10.0, -20.0, 30.0, 0.0, 45.0, -10.0)
    assert forward(vals).to_list() == forward(Joints(vals)).to_list()


@pytest.mark.parametrize(
    "joints",
    [
        (0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
        (10.0, -15.0, 20.0, 5.0, -30.0, 45.0),
        (-45.0, 30.0, -10.0, 0.0, 60.0, -90.0),
        (90.0, -20.0, 40.0, -30.0, 20.0, 15.0),
    ],
)
def test_inverse_recovers_forward_joints(joints: tuple[float, ...]) -> None:
    pose = forward(joints)
    solved = inverse(pose, seed=joints)
    check = forward(solved)
    assert math.dist((check.x, check.y, check.z), (pose.x, pose.y, pose.z)) < 1e-2
    for a, b in zip((check.w, check.p, check.r), (pose.w, pose.p, pose.r)):
        diff = abs((a - b + 180.0) % 360.0 - 180.0)
        assert diff < 1e-2


def test_inverse_round_trip_from_zero_seed() -> None:
    target_joints = (15.0, -10.0, 5.0, 20.0, -25.0, 30.0)
    pose = forward(target_joints)
    solved = inverse(pose)
    check = forward(solved)
    assert math.dist((check.x, check.y, check.z), (pose.x, pose.y, pose.z)) < 1e-2


def test_inverse_wrong_seed_length_raises() -> None:
    pose = forward((0.0,) * 6)
    with pytest.raises(InverseKinematicsError):
        inverse(pose, seed=[0.0, 0.0])


def test_inverse_unreachable_pose_raises() -> None:
    # Far outside the ~550mm reach: numerically guaranteed to never
    # converge within the iteration budget.
    unreachable = Pose(1_000_000.0, 1_000_000.0, 1_000_000.0, 0.0, 0.0, 0.0)
    with pytest.raises(InverseKinematicsError):
        inverse(unreachable, max_iterations=5)


def test_inverse_accepts_plain_sequence_pose() -> None:
    pose = forward((5.0, 5.0, 5.0, 5.0, 5.0, 5.0))
    solved = inverse(list(pose.to_list()), seed=(5.0, 5.0, 5.0, 5.0, 5.0, 5.0))
    assert len(solved) == 6


def test_never_imports_networking_modules() -> None:
    # Structural guardrail: kinematics.py must stay pure computation,
    # never reach for the socket/transport/robot layer.
    import fanuc.kinematics as k

    src = open(k.__file__, encoding="utf-8").read()
    for forbidden in ("import socket", "from .transport", "from .robot", "from . import robot"):
        assert forbidden not in src


# Real (joints, pose) pairs collected from a live ROBOGUIDE-simulated
# ER-4iA via fanuc.robot.FanucRobot (get_curjpos()/get_curpos()), not
# derived from any paper or vendor file -- ground truth, not a model
# cross-reference. A representative sample of the 107 configurations
# this module's forward-kinematics model was calibrated and validated
# against (max 0.02mm / 0.001deg error across the full set); see the
# module docstring.
_REAL_ROBOGUIDE_SAMPLES: tuple[tuple[tuple[float, ...], tuple[float, ...]], ...] = (
    ((0.0, -30.0, 0.0, 0.0, -90.0, 0.0), (160.0, 0.0, 175.167, -180.0, 0.0, 0.0)),
    ((45.0, -20.0, 20.0, 10.0, -70.0, 15.0), (164.629, 148.476, 309.616, 156.791, -35.025, 67.415)),
    ((-60.0, -30.0, 0.0, 0.0, -90.0, 0.0), (80.0, -138.564, 175.167, 180.0, 0.0, -60.0)),
    ((0.0, 90.0, 0.0, 0.0, -90.0, 0.0), (550.0, 0.0, -50.0, -180.0, 0.0, 0.0)),
    ((-30.0, 40.0, -40.0, -30.0, -100.0, -60.0), (324.194, -147.373, -9.836, 139.881, 44.896, -115.909)),
    ((10.0, 10.0, 10.0, 10.0, 10.0, 10.0), (386.742, 70.336, 349.864, 44.109, -61.789, 144.109)),
    ((0.0, 90.0, -100.0, 0.0, 0.0, 0.0), (217.183, 0.0, -358.004, -180.0, 10.0, 0.0)),
    ((0.0, -60.0, 60.0, 0.0, 0.0, 0.0), (-62.487, 0.0, 451.769, -0.0, -30.0, 180.0)),
    ((0.0, -90.0, 60.0, 0.0, 0.0, 0.0), (-97.321, 0.0, 321.769, -0.0, -30.0, 180.0)),
    ((0.0, 110.0, -100.0, 0.0, 0.0, 0.0), (201.503, 0.0, -446.929, -180.0, 10.0, 0.0)),
    ((0.0, -30.0, 200.0, 0.0, 0.0, 0.0), (-461.449, 0.0, 83.245, -180.0, 70.0, 0.0)),
    ((0.0, -30.0, 90.0, 0.0, 0.0, 0.0), (-150.0, 0.0, 585.167, -0.0, 0.0, -180.0)),
)


@pytest.mark.parametrize("joints,real_pose", _REAL_ROBOGUIDE_SAMPLES)
def test_forward_matches_real_roboguide_data(joints: tuple[float, ...], real_pose: tuple[float, ...]) -> None:
    got = forward(joints)
    assert math.dist((got.x, got.y, got.z), real_pose[:3]) < 0.1
    for got_a, real_a in zip((got.w, got.p, got.r), real_pose[3:]):
        diff = abs((got_a - real_a + 180.0) % 360.0 - 180.0)
        assert diff < 0.1


def test_home_joints_forward_kinematics_is_reachable_by_inverse() -> None:
    # fanuc.limits.DEFAULT_HOME_JOINTS is a real, verified posture
    # (read off ROBOGUIDE's Current Position panel on the actual
    # ER-4iA used for this project). Round-tripping it is a sanity
    # check that this module's joint ordering/units line up with the
    # rest of the project, not just with itself.
    from fanuc.limits import DEFAULT_HOME_JOINTS

    pose = forward(DEFAULT_HOME_JOINTS)
    solved = inverse(pose, seed=DEFAULT_HOME_JOINTS)
    check = forward(solved)
    assert math.dist((check.x, check.y, check.z), (pose.x, pose.y, pose.z)) < 1e-2
