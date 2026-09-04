"""Offline forward/inverse kinematics for the ER-4iA.

This module is pure computation: it never touches a socket, never
calls anything in :mod:`fanuc.robot`, and is never invoked by
``move_pose()``/``move_joint()``. It only converts between a joint
angle set and a Cartesian pose, entirely offline.

Data source and its limits
---------------------------
FANUC does not publish a DH-parameter table for the ER-4iA. The
official Operator's Manual (B-83574EN) only has motion-envelope and
installation-clearance drawings, not link geometry. The link offsets
used here instead come from ROBOGUIDE's own internal robot-model file
(``er4ia.xml``, under ROBOGUIDE's ``FRVRC Media`` install data) -- the
same data ROBOGUIDE itself uses to simulate this robot. The
translation magnitudes it contains (260, 20, 290, 70 mm) match values
that also appear in the manual's Fig 3.2(a) operating-space drawing,
which is the closest thing available to independent cross-validation.

What is NOT independently verified is the *rotation* convention used
to compose those offsets (this module assumes FANUC's usual W/P/R
extrinsic-XYZ convention, matching :class:`fanuc.types.Pose`) and the
exact joint zero-offset/sign relationship between this model and what
the controller reports via ``get_curjpos()``. Treat any result from
this module as a candidate, not a certainty:

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


def _translation(x: float, y: float, z: float) -> Matrix:
    return (
        (1.0, 0.0, 0.0, x),
        (0.0, 1.0, 0.0, y),
        (0.0, 0.0, 1.0, z),
        (0.0, 0.0, 0.0, 1.0),
    )


def _rotation_wpr(w_deg: float, p_deg: float, r_deg: float) -> Matrix:
    """Rotation matrix for FANUC's W/P/R convention: extrinsic
    rotation about the fixed X axis by W, then fixed Y by P, then
    fixed Z by R -- i.e. ``Rz(R) @ Ry(P) @ Rx(W)``, matching
    :class:`fanuc.types.Pose`'s W/P/R fields."""
    w, p, r = math.radians(w_deg), math.radians(p_deg), math.radians(r_deg)
    cw, sw = math.cos(w), math.sin(w)
    cp, sp = math.cos(p), math.sin(p)
    cr, sr = math.cos(r), math.sin(r)
    rx: Matrix = (
        (1.0, 0.0, 0.0, 0.0),
        (0.0, cw, -sw, 0.0),
        (0.0, sw, cw, 0.0),
        (0.0, 0.0, 0.0, 1.0),
    )
    ry: Matrix = (
        (cp, 0.0, sp, 0.0),
        (0.0, 1.0, 0.0, 0.0),
        (-sp, 0.0, cp, 0.0),
        (0.0, 0.0, 0.0, 1.0),
    )
    rz: Matrix = (
        (cr, -sr, 0.0, 0.0),
        (sr, cr, 0.0, 0.0),
        (0.0, 0.0, 1.0, 0.0),
        (0.0, 0.0, 0.0, 1.0),
    )
    return _matmul(_matmul(rz, ry), rx)


def _rotation_z(deg: float) -> Matrix:
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return (
        (c, -s, 0.0, 0.0),
        (s, c, 0.0, 0.0),
        (0.0, 0.0, 1.0, 0.0),
        (0.0, 0.0, 0.0, 1.0),
    )


@dataclass(frozen=True)
class _Link:
    """One joint's fixed transform from its parent joint frame, at
    the zero posture, taken from ROBOGUIDE's er4ia.xml ``SETGN``
    entries. The joint itself then rotates about its own local Z
    axis (KAREL/ROBOGUIDE's SETAXS convention) by the joint's angle.
    """

    dx: float
    dy: float
    dz: float
    w: float
    p: float
    r: float


# From er4ia.xml (ROBOGUIDE V9.40, robots/lrm200id/er4ia.xml), the
# base->J1->J2->...->J6->flange SETGN chain. MOUNT_LOC (base plate to
# J1 origin) is folded into _BASE.
_BASE = _Link(0.0, 0.0, 330.0, 0.0, 0.0, 0.0)
_LINKS: tuple[_Link, ...] = (
    _Link(0.0, 0.0, 0.0, 0.0, 0.0, 0.0),  # J1, relative to base
    _Link(0.0, 0.0, 0.0, 90.0, 0.0, 0.0),  # J2, relative to J1
    _Link(0.0, 260.0, 0.0, 0.0, 0.0, 90.0),  # J3, relative to J2
    _Link(20.0, 0.0, 0.0, -90.0, 0.0, 0.0),  # J4, relative to J3
    _Link(0.0, 0.0, -290.0, 90.0, 0.0, 0.0),  # J5, relative to J4
    _Link(0.0, -70.0, 0.0, -90.0, 0.0, 0.0),  # J6, relative to J5
)
_FLANGE = _Link(0.0, 0.0, 0.0, 180.0, 0.0, 0.0)  # tool flange, relative to J6

_NUM_JOINTS = len(_LINKS)


def _link_transform(link: _Link) -> Matrix:
    return _matmul(_translation(link.dx, link.dy, link.dz), _rotation_wpr(link.w, link.p, link.r))


def _fk_matrix(joint_deg: Sequence[float]) -> Matrix:
    t = _link_transform(_BASE)
    for link, theta in zip(_LINKS, joint_deg):
        t = _matmul(t, _link_transform(link))
        t = _matmul(t, _rotation_z(theta))
    t = _matmul(t, _link_transform(_FLANGE))
    return t


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
