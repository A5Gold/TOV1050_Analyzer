from __future__ import annotations

AIR_DENSITY_FACTOR = 0.6137
DRAG_FACTOR = 0.8
SHAPE_FACTOR = 1.08
REFERENCE_WIND_SPEED = 34.3
AREA_FACTOR = 0.0132


def calculate_b_value(span: float, k_eq: float, tension: float) -> float:
    return (
        AIR_DENSITY_FACTOR
        * DRAG_FACTOR
        * SHAPE_FACTOR
        * (REFERENCE_WIND_SPEED * k_eq) ** 2
        * AREA_FACTOR
        * span**2
        / (32 * tension)
    )


def calculate_p_value(stg_x: float, stg_i: float) -> float:
    return abs((stg_x + stg_i) / 2)


def calculate_s_value(stg_x: float, stg_i: float) -> float:
    return abs(stg_x - stg_i)


def calculate_e_value(s_value: float, b_value: float) -> float:
    if b_value <= 0:
        return 0.0
    return s_value**2 / (16 * b_value)


def calculate_allowable_value(
    b_value: float,
    e_value: float,
    height_correction: float,
) -> float:
    return 505 - (b_value + e_value) - height_correction


def is_short_circuit_pass(s_value: float, b_value: float) -> bool:
    return s_value >= 4 * b_value
