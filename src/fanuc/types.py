"""Coordinate types.

Upstream's get_curpos() returns list[float], so callers have to
remember whether index 3 is W or P. This wraps that in named fields
while keeping sequence behavior, so the original unpacking style still
works.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator, Sequence, overload

from ._i18n import bi


@dataclass(frozen=True)
class Pose:
    """Cartesian position (World frame).

    Units: X/Y/Z in mm, W/P/R in degrees.
    """

    x: float
    y: float
    z: float
    w: float
    p: float
    r: float
    #: External axes. None on the ER-4iA; here for mechanisms with a
    #: turntable or travel axis.
    ext: tuple[float, ...] = field(default_factory=tuple)

    LABELS = ("X", "Y", "Z", "W", "P", "R")

    @classmethod
    def from_list(cls, vals: Sequence[float]) -> "Pose":
        if len(vals) < 6:
            raise ValueError(bi(
                f"直角座標需要至少 6 個值，收到 {len(vals)} 個",
                f"cartesian pose needs at least 6 values, got {len(vals)}",
            ))
        x, y, z, w, p, r = (float(v) for v in vals[:6])
        return cls(x, y, z, w, p, r, ext=tuple(float(v) for v in vals[6:]))

    def to_list(self) -> list[float]:
        return [self.x, self.y, self.z, self.w, self.p, self.r, *self.ext]

    def __iter__(self) -> Iterator[float]:
        return iter(self.to_list())

    def __len__(self) -> int:
        return 6 + len(self.ext)

    @overload
    def __getitem__(self, idx: int) -> float: ...
    @overload
    def __getitem__(self, idx: slice) -> list[float]: ...

    def __getitem__(self, idx: int | slice) -> float | list[float]:
        return self.to_list()[idx]

    def format(self) -> str:
        return _format_labelled(self.LABELS, self.to_list(), ext_prefix="E")


@dataclass(frozen=True)
class Joints:
    """Joint position, in degrees.

    Supports mechanisms with 6+ axes; ``values`` is ordered J1..Jn.
    """

    values: tuple[float, ...]

    @classmethod
    def from_list(cls, vals: Sequence[float]) -> "Joints":
        return cls(tuple(vals))

    def to_list(self) -> list[float]:
        return list(self.values)

    def __iter__(self) -> Iterator[float]:
        return iter(self.values)

    def __len__(self) -> int:
        return len(self.values)

    @overload
    def __getitem__(self, idx: int) -> float: ...
    @overload
    def __getitem__(self, idx: slice) -> tuple[float, ...]: ...

    def __getitem__(self, idx: int | slice) -> float | tuple[float, ...]:
        return self.values[idx]

    @property
    def labels(self) -> tuple[str, ...]:
        return tuple(f"J{i}" for i in range(1, len(self.values) + 1))

    def format(self) -> str:
        return _format_labelled(self.labels, self.to_list())


@dataclass(frozen=True)
class Alarm:
    """One alarm entry, as returned by ``FanucRobot.get_alarm()``.

    Only ever the current/most recent entry; see ``get_alarm()``'s
    docstring for why there's no way to read older ones.
    """

    #: Alarm code, e.g. 3048 for PROG-048.
    code: int
    #: Severity as reported by the controller.
    severity: int
    #: Cause code. Meaning not cross-referenced against a FANUC alarm
    #: code table; treat it as an opaque number for now.
    cause_code: int
    #: Raw timestamp from the controller (KAREL's ERR_DATA TIME
    #: output). Its epoch/unit hasn't been verified against real
    #: documentation; don't do date arithmetic on it without
    #: checking it against a known alarm's actual time first.
    time: int
    #: Name of the program running when the alarm occurred, empty if
    #: none.
    program: str
    #: The alarm message text.
    message: str


@dataclass(frozen=True)
class JointViolation:
    """Detail of one axis exceeding the static limit table. Diagnostic
    only, not a safety determination."""

    axis: str
    value: float
    lower: float
    upper: float

    def _zh(self) -> str:
        return f"{self.axis}={self.value:.2f} 超出 {self.lower:.2f}~{self.upper:.2f}"

    def _en(self) -> str:
        return f"{self.axis}={self.value:.2f} out of {self.lower:.2f}~{self.upper:.2f}"

    def __str__(self) -> str:
        return bi(self._zh(), self._en())


@dataclass(frozen=True)
class JointCheckResult:
    """Return value of ``FanucRobot.check_joint()``.

    ``ok`` is the sole source of truth for legality, coming from the
    controller's ``J_IN_RANGE`` (see driver/mappdk_ext.kl), which also
    accounts for mechanical-coupling limits like J2/J3.

    ``violations`` is only meaningful when ``ok`` is False: it's a
    per-axis diagnostic against the static limit table, hinting at
    "which axis is probably the cause". That table only covers
    per-axis ranges and can't capture coupling limits, so
    ``violations`` has two possible states:
    - non-empty: at least one axis is outside its own static range,
      likely the actual cause
    - empty: every axis is within its own range, meaning this is a
      pure coupling limit (e.g. J2/J3): the table can't point to
      which axis
    """

    ok: bool
    values: tuple[float, ...]
    violations: tuple[JointViolation, ...] = ()

    def __bool__(self) -> bool:
        return self.ok

    def describe(self) -> str:
        if self.ok:
            return bi("合法", "valid")
        if not self.violations:
            return bi(
                "不合法（每一軸單獨看都在範圍內，可能是機構耦合限制，例如 J2/J3）",
                "invalid (every axis is within its own range, likely a mechanical coupling limit, e.g. J2/J3)",
            )
        zh = "、".join(v._zh() for v in self.violations)
        en = ", ".join(v._en() for v in self.violations)
        return bi(f"不合法：{zh}", f"invalid: {en}")


def _format_labelled(
    labels: Sequence[str], values: Sequence[float], ext_prefix: str | None = None
) -> str:
    """Pairs values with axis names for display. Extra values are
    treated as external axes."""
    lines = [
        f"  {name:<3} = {val:>10.3f}"
        for name, val in zip(labels, values)
    ]
    if ext_prefix and len(values) > len(labels):
        for i, val in enumerate(values[len(labels):], start=1):
            lines.append(f"  {ext_prefix}{i:<2} = {val:>10.3f}")
    return "\n".join(lines)
