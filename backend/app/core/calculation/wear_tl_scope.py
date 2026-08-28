"""Line-specific tension-length scope classification for wear cycles."""

from enum import Enum
import re
from typing import Any


class TensionLengthScope(str, Enum):
    MAINLINE = "MAINLINE"
    SIDING = "SIDING"
    UNKNOWN = "UNKNOWN"


_U_SLASH_BASES = frozenset({7, 8, 31, 36})
_U_SLASH_SUFFIXES = frozenset({1, 2})

_TML_MAINLINE_SERIES = {
    "M": (1, 33),
    "D": (1, 60),
    "U": (1, 55),
    "K": (1, 16),
}
_TML_SIDING_SERIES = {
    "MX": (1, 11),
    "MD": (1, 22),
    "PT": (1, 2),
    "CT": (1, 3),
    "KX": (1, 7),
    "X": (1, 29),
    "MP": (24, 24),
    "EM": (1, 1),
}
_TML_SIDING_EXACT = frozenset(
    {"W1-1", "27A", "101", "102", "103", "NEUTRAL SECTION"}
)

_EAL_MAINLINE_SERIES = {
    "H": (1, 52),
    "D": (1, 31),
    "U": (1, 55),
    "K": (1, 16),
    "L": (1, 20),
}
_EAL_MAINLINE_EXACT = frozenset(
    {"H23D", "H26D", "69B", "70A", "T2", "T3", "X36", "X37", "X50", "X53", "X54"}
)
_EAL_SIDING_SERIES = {"HX": (2, 2), "EM": (1, 1)}
_EAL_SIDING_EXACT = frozenset({"D32", "D33", "NEUTRAL SECTION"})


def _numbered_series(identity: str, ranges: dict[str, tuple[int, int]]) -> bool:
    match = re.fullmatch(r"([A-Z]+)(\d+)", identity)
    if match is None:
        return False
    prefix, raw_number = match.groups()
    bounds = ranges.get(prefix)
    if bounds is None:
        return False
    number = int(raw_number)
    return bounds[0] <= number <= bounds[1]


def _u_slash_variant(identity: str) -> bool:
    match = re.fullmatch(r"U0*(\d+)/(\d+)", identity)
    return bool(
        match
        and int(match.group(1)) in _U_SLASH_BASES
        and int(match.group(2)) in _U_SLASH_SUFFIXES
    )


def _numeric_identity(identity: str, lower: int, upper: int) -> bool:
    return bool(re.fullmatch(r"\d+", identity)) and lower <= int(identity) <= upper


def _classify_tml(identity: str) -> TensionLengthScope:
    if identity in _TML_SIDING_EXACT or _numbered_series(identity, _TML_SIDING_SERIES):
        return TensionLengthScope.SIDING
    if (
        _u_slash_variant(identity)
        or _numbered_series(identity, _TML_MAINLINE_SERIES)
        or _numeric_identity(identity, 1, 74)
    ):
        return TensionLengthScope.MAINLINE
    return TensionLengthScope.UNKNOWN


def _classify_eal(identity: str) -> TensionLengthScope:
    if identity in _EAL_MAINLINE_EXACT:
        return TensionLengthScope.MAINLINE
    if identity in _EAL_SIDING_EXACT or _numbered_series(identity, _EAL_SIDING_SERIES):
        return TensionLengthScope.SIDING
    if re.fullmatch(r"LX0*[1-9]\d*", identity):
        return TensionLengthScope.SIDING
    x_match = re.fullmatch(r"X0*(\d+)", identity)
    if x_match is not None and 1 <= int(x_match.group(1)) <= 39:
        return TensionLengthScope.SIDING
    if (
        _u_slash_variant(identity)
        or _numbered_series(identity, _EAL_MAINLINE_SERIES)
        or _numeric_identity(identity, 1, 76)
    ):
        return TensionLengthScope.MAINLINE
    return TensionLengthScope.UNKNOWN


def classify_tension_length_scope(
    line_group: Any,
    tension_length: Any,
) -> TensionLengthScope:
    """Classify a TL identity without changing its canonical or displayed value."""
    if not isinstance(line_group, str):
        raise ValueError("line group must be EAL or TML")
    line = line_group.strip().upper()
    if line not in {"EAL", "TML"}:
        raise ValueError("line group must be EAL or TML")
    identity = "" if tension_length is None else str(tension_length).strip().upper()
    return _classify_eal(identity) if line == "EAL" else _classify_tml(identity)
