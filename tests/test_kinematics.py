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
