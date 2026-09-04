"""Offline forward/inverse kinematics for the ER-4iA.

This module is pure computation: it never touches a socket, never
calls anything in :mod:`fanuc.robot`, and is never invoked by
``move_pose()``/``move_joint()``. It only converts between a joint
angle set and a Cartesian pose, entirely offline.

Data source and its limits
---------------------------
FANUC does not publish a DH-parameter table for the ER-4iA. The link
geometry below is the modified (Craig-convention) Denavit-Hartenberg
table published as Table 2 of Chen et al., "Digital twin-based
self-learning decision-making framework for industrial robots in
manufacturing", The International Journal of Advanced Manufacturing
Technology (2025), doi:10.1007/s00170-025-15844-w -- a peer-reviewed
paper built around a real ER-4iA plus its ROBOGUIDE digital twin.

That table is corroborated by two independent sources already in this
project, not just taken on faith:

- Every one of its non-zero translation values (d1=330, a2=260,
  a3=20, d4=290, d6=70 mm) matches the base->J1->...->J6 offset chain
  in ROBOGUIDE's own internal robot-model file (``er4ia.xml``, under
  ROBOGUIDE's ``FRVRC Media`` install data) -- the data ROBOGUIDE
  itself uses to simulate this exact robot.
- Its per-axis joint limits match :data:`fanuc.limits.DEFAULT_JOINT_LIMITS_DEG`,
  which were read directly off a real ER-4iA controller's TP panel
  (J1/J4/J5/J6 match exactly, J3 matches to within a rounding digit).

What is still NOT independently verified is the *tool-flange
orientation* convention (the fixed rotation from the DH chain's frame
6 to the flange orientation :class:`fanuc.types.Pose`'s W/P/R
describes) and the exact joint zero-offset/sign relationship between
this model and what the controller reports via ``get_curjpos()``. The
X/Y/Z position this module computes rests on the corroborated
translation values above and is comparatively trustworthy; the W/P/R
orientation rests on an unverified assumption and should be treated
with more caution. Treat any result from this module as a candidate,
not a certainty:

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
from dataclasses import dataclass
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

_IDENTITY: Matrix = (
    (1.0, 0.0, 0.0, 0.0),
    (0.0, 1.0, 0.0, 0.0),
    (0.0, 0.0, 1.0, 0.0),
    (0.0, 0.0, 0.0, 1.0),
)


class ForwardKinematicsError(ValueError):
    """Raised when :func:`forward` is given the wrong number of joints."""


class InverseKinematicsError(ValueError):
    """Raised when :func:`inverse` cannot converge to a solution."""


def _matmul(a: Matrix, b: Matrix) -> Matrix:
    return tuple(  # type: ignore[return-value]
        tuple(sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4))
        for i in range(4)
    )


def _dh_transform(alpha_prev_deg: float, a_prev: float, d: float, theta_deg: float) -> Matrix:
    """One modified/Craig-convention DH link transform:
    ``Rx(alpha_prev) @ Tx(a_prev) @ Rz(theta) @ Tz(d)``."""
    alpha, theta = math.radians(alpha_prev_deg), math.radians(theta_deg)
    ca, sa = math.cos(alpha), math.sin(alpha)
    ct, st = math.cos(theta), math.sin(theta)
    return (
        (ct, -st, 0.0, a_prev),
        (st * ca, ct * ca, -sa, -sa * d),
        (st * sa, ct * sa, ca, ca * d),
        (0.0, 0.0, 0.0, 1.0),
    )


@dataclass(frozen=True)
class _DhRow:
    """One row of the ER-4iA's modified DH table (Chen et al. 2025,
    Table 2 -- see the module docstring). ``theta_offset`` is the
    constant added to the joint's commanded angle to get the DH
    ``theta_i`` (only J2 has a nonzero offset, -90 deg, in that
    table)."""

    alpha_prev: float
    a_prev: float
    d: float
    theta_offset: float


# Chen et al. 2025, Table 2 ("modified Denavit-Hartenberg parameters
# of FANUC ER-4iA"), cross-validated against ROBOGUIDE's er4ia.xml
# and this project's own limits.py -- see the module docstring.
_DH_TABLE: tuple[_DhRow, ...] = (
    _DhRow(alpha_prev=0.0, a_prev=0.0, d=330.0, theta_offset=0.0),  # link 1
    _DhRow(alpha_prev=-90.0, a_prev=0.0, d=0.0, theta_offset=-90.0),  # link 2
    _DhRow(alpha_prev=0.0, a_prev=260.0, d=0.0, theta_offset=0.0),  # link 3
    _DhRow(alpha_prev=-90.0, a_prev=20.0, d=290.0, theta_offset=0.0),  # link 4
    _DhRow(alpha_prev=90.0, a_prev=0.0, d=0.0, theta_offset=0.0),  # link 5
    _DhRow(alpha_prev=-90.0, a_prev=0.0, d=70.0, theta_offset=0.0),  # link 6
)

# Fixed rotation from the DH chain's frame 6 to the tool flange
# orientation that fanuc.types.Pose's W/P/R describes. Carried over
# from the er4ia.xml SETGN chain's FP node; unlike the translation
# values above, this specific rotation has no independent
# cross-validation -- see the module docstring's orientation caveat.
_FLANGE_ROTATION_W_DEG = 180.0

_NUM_JOINTS = len(_DH_TABLE)


def _fk_matrix(joint_deg: Sequence[float]) -> Matrix:
    t = _IDENTITY
    for row, commanded in zip(_DH_TABLE, joint_deg):
        t = _matmul(t, _dh_transform(row.alpha_prev, row.a_prev, row.d, commanded + row.theta_offset))
    w = math.radians(_FLANGE_ROTATION_W_DEG)
    cw, sw = math.cos(w), math.sin(w)
    flange_rx: Matrix = (
        (1.0, 0.0, 0.0, 0.0),
        (0.0, cw, -sw, 0.0),
        (0.0, sw, cw, 0.0),
        (0.0, 0.0, 0.0, 1.0),
    )
    return _matmul(t, flange_rx)


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
    closed-form solution attempted here, since this robot's axes
    don't reduce to a textbook spherical-wrist geometry from the
    offsets in ``er4ia.xml``. ``seed`` is the starting joint guess
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
