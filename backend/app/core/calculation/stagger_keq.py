from __future__ import annotations

from app.core.calculation.stagger_metadata import RangeValue


def _lookup_range_value(chainage: float, ranges: list[RangeValue]) -> float:
    for item in ranges:
        if item.start <= chainage <= item.end:
            return item.value
    raise ValueError(f"No support factor range for chainage {chainage}")


def _support_factor(chainage: float, kr: list[RangeValue], ke: list[RangeValue], kh: list[RangeValue]) -> float:
    return (
        _lookup_range_value(chainage, kr)
        * _lookup_range_value(chainage, ke)
        * _lookup_range_value(chainage, kh)
    )


def calculate_eal_keq(
    track: str,
    spt_a: float,
    spt_i: float,
    spt_b: float,
    kr_by_track: dict[str, list[RangeValue]],
    ke_by_track: dict[str, list[RangeValue]],
    kh_by_track: dict[str, list[RangeValue]],
) -> dict[str, float]:
    track_key = track.lower()
    kr = kr_by_track[track_key]
    ke = ke_by_track[track_key]
    kh = kh_by_track[track_key]

    k_a = _support_factor(spt_a, kr, ke, kh)
    k_i = _support_factor(spt_i, kr, ke, kh)
    k_b = _support_factor(spt_b, kr, ke, kh)
    k_ai_max = max(k_a, k_i)
    k_ib_max = max(k_i, k_b)

    return {
        "k_a": k_a,
        "k_i": k_i,
        "k_b": k_b,
        "k_ai_max": k_ai_max,
        "k_ib_max": k_ib_max,
        "k_eq": max(k_ai_max, k_ib_max),
    }


def calculate_tml_keq(
    chi: float,
    boundary: float,
    above: float,
    below_or_equal: float,
) -> float:
    return above if chi > boundary else below_or_equal
