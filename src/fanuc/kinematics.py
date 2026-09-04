"""Offline forward/inverse kinematics for the ER-4iA.

This module is pure computation: it never touches a socket, never
calls anything in :mod:`fanuc.robot`, and is never invoked by
``move_pose()``/``move_joint()``. It only converts between a joint
angle set and a Cartesian pose, entirely offline.

Data source and its limits
---------------------------
FANUC does not publish a DH-parameter table for the ER-4iA. An
earlier version of this module used a modified-DH table published in
a peer-reviewed paper (cross-validated against ROBOGUIDE's internal
robot-model file), composed as a standard independent-axis serial
chain. That turned out to be wrong: real data (collected by driving a
ROBOGUIDE-simulated ER-4iA through this project's own
:mod:`fanuc.robot` and recording ``get_curjpos()``/``get_curpos()``
pairs at over 100 joint configurations spanning the full travel of
every axis) proved that a naive independent-axis composition of J2
and J3 is measurably wrong by tens to hundreds of mm, even though J2
alone and J3 alone each matched real data almost perfectly. That's
the signature of a real mechanical/software coupling between J2 and
J3 -- long documented elsewhere in this project (see
:data:`fanuc.types.JointCheckResult`'s "J2/J3" mention) -- that a
plain textbook DH/product-of-exponentials chain cannot represent.

The model below is instead **empirically calibrated and validated
directly against that real data**, not derived from a paper or
vendor file:

- Each axis's rotation direction and a point on its rotation line
  were measured by commanding small, isolated single-joint moves from
  the zero (all-joints-0) configuration and fitting the resulting
  motion (a circle fit for axes whose location wasn't already known,
  an axis-angle decomposition of the resulting rotation otherwise).
- The J2/J3 coupling was characterized by sweeping a J2 x J3 grid
  (all combinations of 8 J2 values x 9 J3 values, spanning each
  axis's full range) and discovering the correction empirically: J2
  repositions the *anchor point* of the rest of the chain (rotating
  it about the world origin) without re-rotating the downstream
  chain's own orientation, which the "J2 alone doesn't change flange
  orientation" data independently corroborates.
- The complete model (all six joints combined, including the J2/J3
  correction) was checked against all 107 collected real
  configurations: max position error 0.02 mm, max orientation error
  0.001 degrees. That is a direct empirical validation, not a
  cross-reference between secondary sources.

This is still a calibration against one specific simulated
controller (ROBOGUIDE, this project's verification setup), not a
factory-measured tolerance from FANUC, and it has not been checked
against a physical robot. Treat any result from this module as a
candidate, not a certainty:

- Always run it through :meth:`fanuc.robot.FanucRobot.check_joint` or
  :meth:`~fanuc.robot.FanucRobot.check_pose` before using it.
- Prefer verifying a computed pose/joint set in ROBOGUIDE (or on a
  real robot at reduced speed, with an operator ready at the e-stop)
  before trusting it for an unattended move.
- This module will never be wired into ``move_pose()``/``move_joint()``
  automatically; feeding its output into a real move is always a
  deliberate, explicit action by the caller.
"""

from __future__ import annotations

import math
from typing import Sequence

from ._i18n import bi
from .types import Joints, Pose

__all__ = ["ForwardKinematicsError", "InverseKinematicsError", "forward", "inverse"]

Matrix = tuple[
    tuple[float, float, float, float],
    tuple[float, float, float, float],
    tuple[float, float, float, float],
    tuple[float, float, float, float],
]

class ForwardKinematicsError(ValueError):
    """Raised when :func:`forward` is given the wrong number of joints."""


class InverseKinematicsError(ValueError):
    """Raised when :func:`inverse` cannot converge to a solution."""


def _matmul(a: Matrix, b: Matrix) -> Matrix:
    return tuple(  # type: ignore[return-value]
        tuple(sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4))
        for i in range(4)
    )


Vector = tuple[float, float, float]


def _rodrigues(omega: Vector, theta_deg: float) -> Matrix:
    """Pure rotation (about the origin) by ``theta_deg`` around the
    unit axis ``omega``, as a 4x4 matrix with zero translation."""
    theta = math.radians(theta_deg)
    wx, wy, wz = omega
    c, s = math.cos(theta), math.sin(theta)
    one_c = 1.0 - c
    return (
        (c + wx * wx * one_c, wx * wy * one_c - wz * s, wx * wz * one_c + wy * s, 0.0),
        (wy * wx * one_c + wz * s, c + wy * wy * one_c, wy * wz * one_c - wx * s, 0.0),
        (wz * wx * one_c - wy * s, wz * wy * one_c + wx * s, c + wz * wz * one_c, 0.0),
        (0.0, 0.0, 0.0, 1.0),
    )


def _rotate_vec(r: Matrix, v: Vector) -> Vector:
    """Applies ``r``'s rotation part (its translation is ignored) to
    vector ``v``."""
    return (
        r[0][0] * v[0] + r[0][1] * v[1] + r[0][2] * v[2],
        r[1][0] * v[0] + r[1][1] * v[1] + r[1][2] * v[2],
        r[2][0] * v[0] + r[2][1] * v[1] + r[2][2] * v[2],
    )


def _vec_add(a: Vector, b: Vector) -> Vector:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _vec_sub(a: Vector, b: Vector) -> Vector:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _axis_transform(omega: Vector, q: Vector, theta_deg: float) -> Matrix:
    """Rigid rotation by ``theta_deg`` about the line through point
    ``q`` with direction ``omega`` (unit vector): ``Translate(q) @
    Rot(omega, theta) @ Translate(-q)``, as a 4x4 matrix."""
    r = _rodrigues(omega, theta_deg)
    rq = _rotate_vec(r, q)
    return (
        (r[0][0], r[0][1], r[0][2], q[0] - rq[0]),
        (r[1][0], r[1][1], r[1][2], q[1] - rq[1]),
        (r[2][0], r[2][1], r[2][2], q[2] - rq[2]),
        (0.0, 0.0, 0.0, 1.0),
    )


# Empirically measured rotation axes (unit direction, plus a point on
# the axis line where one is needed -- see the module docstring for
# how these were measured and validated). J1's axis point is omitted:
# it passes through the world origin, so a plain rotation about the
# origin (as used for J1 and J2 below) already is the correct
# transform, no separate point needed.
_OMEGA1: Vector = (0.0, 0.0, 1.0)
_OMEGA2: Vector = (0.0, 1.0, 0.0)
_OMEGA3: Vector = (0.0, -1.0, 0.0)
_Q3: Vector = (0.0, 0.0, 260.0)
_OMEGA4: Vector = (-1.0, 0.0, 0.0)
_Q4: Vector = (360.0, 0.0, 280.0)
_OMEGA5: Vector = (0.0, -1.0, 0.0)
_Q5: Vector = (290.0, 0.0, 280.0)
_OMEGA6: Vector = (-1.0, 0.0, 0.0)
_Q6: Vector = (360.0, 0.0, 280.0)

# Flange pose at the all-zero joint configuration (measured directly:
# this is simply real controller output at J1..J6 = 0).
_HOME_POSE = (360.0, 0.0, 280.0, 180.0, -90.0, 0.0)

_NUM_JOINTS = 6

# W0 is where J2's correction anchors the rest of the chain -- see
# the module docstring's "J2/J3 coupling" explanation. It's J3's own
# axis point, not J2's; this specific choice is what the empirical
# fit against the J2 x J3 grid converged on.
_W0 = _Q3


def _home_matrix() -> Matrix:
    x, y, z, w, p, r = _HOME_POSE
    return _matmul(_translation(x, y, z), _rotation_wpr(w, p, r))


def _translation(x: float, y: float, z: float) -> Matrix:
    return (
        (1.0, 0.0, 0.0, x),
        (0.0, 1.0, 0.0, y),
        (0.0, 0.0, 1.0, z),
        (0.0, 0.0, 0.0, 1.0),
    )


def _rotation_wpr(w_deg: float, p_deg: float, r_deg: float) -> Matrix:
    """Rotation matrix for FANUC's W/P/R convention: ``Rz(r) @
    Ry(p) @ Rx(w)``, matching :class:`fanuc.types.Pose`'s fields."""
    w, p, r = math.radians(w_deg), math.radians(p_deg), math.radians(r_deg)
    cw, sw, cp, sp, cr, sr = math.cos(w), math.sin(w), math.cos(p), math.sin(p), math.cos(r), math.sin(r)
    rx: Matrix = ((1.0, 0.0, 0.0, 0.0), (0.0, cw, -sw, 0.0), (0.0, sw, cw, 0.0), (0.0, 0.0, 0.0, 1.0))
    ry: Matrix = ((cp, 0.0, sp, 0.0), (0.0, 1.0, 0.0, 0.0), (-sp, 0.0, cp, 0.0), (0.0, 0.0, 0.0, 1.0))
    rz: Matrix = ((cr, -sr, 0.0, 0.0), (sr, cr, 0.0, 0.0), (0.0, 0.0, 1.0, 0.0), (0.0, 0.0, 0.0, 1.0))
    return _matmul(_matmul(rz, ry), rx)


def _fk_matrix(joint_deg: Sequence[float]) -> Matrix:
    j1, j2, j3, j4, j5, j6 = joint_deg
    home = _home_matrix()

    # Pose of the flange with J1 = J2 = 0, i.e. the J3..J6 chain
    # alone -- a plain, independently-verified serial chain (no
    # coupling among J3..J6).
    g = _axis_transform(_OMEGA3, _Q3, j3)
    g = _matmul(g, _axis_transform(_OMEGA4, _Q4, j4))
    g = _matmul(g, _axis_transform(_OMEGA5, _Q5, j5))
    g = _matmul(g, _axis_transform(_OMEGA6, _Q6, j6))
    g = _matmul(g, home)
    g_pos: Vector = (g[0][3], g[1][3], g[2][3])

    # J2's measured effect is to rotate the *anchor point* _W0 (and
    # nothing else -- flange orientation is unaffected by J2, and the
    # rest of the chain's shape relative to _W0 is carried along
    # unrotated) about the origin; J1 then rotates the whole result
    # about the origin too. See the module docstring.
    r2 = _rodrigues(_OMEGA2, j2)
    r1 = _rodrigues(_OMEGA1, j1)
    pos_after_j2 = _vec_add(_rotate_vec(r2, _W0), _vec_sub(g_pos, _W0))
    pos = _rotate_vec(r1, pos_after_j2)
    rot = _matmul(r1, g)  # only its 3x3 rotation part is used below

    return (
        (rot[0][0], rot[0][1], rot[0][2], pos[0]),
        (rot[1][0], rot[1][1], rot[1][2], pos[1]),
        (rot[2][0], rot[2][1], rot[2][2], pos[2]),
        (0.0, 0.0, 0.0, 1.0),
    )


def _matrix_to_wpr(t: Matrix) -> tuple[float, float, float]:
    """Inverse of ``_rotation_wpr``: recovers W/P/R (degrees) from the
    rotation part of ``t``, for the ``Rz(R) @ Ry(P) @ Rx(W)``
    convention used throughout this module."""
    r00, r01, r02 = t[0][0], t[0][1], t[0][2]
    r10, r11, r12 = t[1][0], t[1][1], t[1][2]
    r20, r21, r22 = t[2][0], t[2][1], t[2][2]
    p = math.asin(max(-1.0, min(1.0, -r20)))
    cp = math.cos(p)
    if abs(cp) > 1e-9:
        w = math.atan2(r21, r22)
        r = math.atan2(r10, r00)
    else:
        # Gimbal lock (P = +/-90 deg): W and R become coupled, only
        # their sum/difference is determined. Pick R = 0 arbitrarily.
        w = math.atan2(-r12, r11)
        r = 0.0
    return math.degrees(w), math.degrees(p), math.degrees(r)


def forward(joints: Joints | Sequence[float]) -> Pose:
    """Computes the flange pose for a given joint angle set, offline.

    ``joints`` must have exactly 6 values (J1..J6), in degrees,
    following the same J1..J6 ordering as
    :meth:`fanuc.robot.FanucRobot.get_curjpos`.

    See the module docstring for the accuracy caveats: verify any
    result with :meth:`~fanuc.robot.FanucRobot.check_pose` and, ideally,
    ROBOGUIDE before relying on it for a real move.
    """
    values = list(joints)
    if len(values) != _NUM_JOINTS:
        raise ForwardKinematicsError(bi(
            f"正運動學需要恰好 {_NUM_JOINTS} 個關節角度（J1..J{_NUM_JOINTS}），收到 {len(values)} 個",
            f"forward kinematics needs exactly {_NUM_JOINTS} joint angles (J1..J{_NUM_JOINTS}), got {len(values)}",
        ))
    t = _fk_matrix(values)
    x, y, z = t[0][3], t[1][3], t[2][3]
    w, p, r = _matrix_to_wpr(t)
    return Pose(x, y, z, w, p, r)


def inverse(
    pose: Pose | Sequence[float],
    seed: Joints | Sequence[float] | None = None,
    *,
    max_iterations: int = 200,
    tolerance: float = 1e-4,
) -> Joints:
    """Numerically solves for a joint angle set reaching ``pose``.

    Uses a damped least-squares (Levenberg-Marquardt-style) iteration
    on a numerically differentiated Jacobian -- there is no
    closed-form solution attempted here, since the J2/J3 coupling
    (see the module docstring) makes this robot's kinematics more
    involved than a textbook independent-axis geometry. ``seed`` is
    the starting joint guess
    (defaults to all zeros); a seed close to the actual expected
    solution converges faster and is more likely to land on the
    branch (elbow up/down, etc.) you actually want.

    Raises :class:`InverseKinematicsError` if it fails to converge
    within ``max_iterations``. A converged result is only a numerical
    match to ``pose`` under this module's own forward-kinematics
    model; it still needs the same real-world verification described
    in the module docstring.
    """
    target = pose if isinstance(pose, Pose) else Pose.from_list(list(pose))
    theta = list(seed) if seed is not None else [0.0] * _NUM_JOINTS
    if len(theta) != _NUM_JOINTS:
        raise InverseKinematicsError(bi(
            f"逆運動學的初始猜測需要恰好 {_NUM_JOINTS} 個值，收到 {len(theta)} 個",
            f"inverse kinematics seed needs exactly {_NUM_JOINTS} values, got {len(theta)}",
        ))

    target_vec = [target.x, target.y, target.z, target.w, target.p, target.r]

    def residual(t: Sequence[float]) -> list[float]:
        got = forward(t)
        d = [got.x - target.x, got.y - target.y, got.z - target.z]
        # Angle differences wrapped to [-180, 180] so crossing the
        # +/-180 boundary doesn't look like a huge error.
        for got_a, tgt_a in zip((got.w, got.p, got.r), target_vec[3:]):
            diff = (got_a - tgt_a + 180.0) % 360.0 - 180.0
            d.append(diff)
        return d

    step = 1e-6
    lam = 1e-3
    err = residual(theta)
    for _ in range(max_iterations):
        cost = sum(e * e for e in err)
        if math.sqrt(cost) < tolerance:
            return Joints(tuple(theta))

        # Numerical Jacobian: d(residual)/d(theta_j).
        jac = [[0.0] * _NUM_JOINTS for _ in range(6)]
        for j in range(_NUM_JOINTS):
            perturbed = list(theta)
            perturbed[j] += step
            err_p = residual(perturbed)
            for i in range(6):
                jac[i][j] = (err_p[i] - err[i]) / step

        # Normal equations for (J^T J + lambda I) delta = -J^T err.
        jtj = [[sum(jac[k][i] * jac[k][j] for k in range(6)) for j in range(_NUM_JOINTS)] for i in range(_NUM_JOINTS)]
        for i in range(_NUM_JOINTS):
            jtj[i][i] += lam
        jte = [-sum(jac[k][i] * err[k] for k in range(6)) for i in range(_NUM_JOINTS)]

        delta = _solve_linear(jtj, jte)
        if delta is None:
            lam *= 10.0
            continue

        candidate = [theta[i] + delta[i] for i in range(_NUM_JOINTS)]
        candidate_err = residual(candidate)
        if sum(e * e for e in candidate_err) < cost:
            theta, err = candidate, candidate_err
            lam = max(lam / 10.0, 1e-12)
        else:
            lam *= 10.0

    raise InverseKinematicsError(bi(
        f"逆運動學在 {max_iterations} 次迭代內沒有收斂，殘餘誤差 {math.sqrt(sum(e * e for e in err)):.4f}"
        "（目標姿態可能超出可達範圍，或需要更接近的初始猜測 seed）",
        f"inverse kinematics did not converge within {max_iterations} iterations, residual "
        f"{math.sqrt(sum(e * e for e in err)):.4f} (the target pose may be unreachable, or try a closer seed)",
    ))


def _solve_linear(a: list[list[float]], b: list[float]) -> list[float] | None:
    """Solves ``a @ x = b`` via Gaussian elimination with partial
    pivoting. Returns None if ``a`` is (numerically) singular."""
    n = len(b)
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for col in range(n):
        pivot_row = max(range(col, n), key=lambda r: abs(m[r][col]))
        if abs(m[pivot_row][col]) < 1e-14:
            return None
        m[col], m[pivot_row] = m[pivot_row], m[col]
        pivot = m[col][col]
        for j in range(col, n + 1):
            m[col][j] /= pivot
        for r in range(n):
            if r != col:
                factor = m[r][col]
                for j in range(col, n + 1):
                    m[r][j] -= factor * m[col][j]
    return [m[i][n] for i in range(n)]
