from __future__ import annotations

from app.core.calculation.stagger_types import ResolvedMeasurements


def _nearest_row(
    chart_rows: list[dict[str, object]],
    target_chainage: float | None,
) -> dict[str, object] | None:
    if target_chainage is None:
        return None
    return min(
        chart_rows,
        key=lambda row: abs(float(row["chainage"]) - target_chainage),
    )


def resolve_measurements(
    chart_rows: list[dict[str, object]],
    chi: float,
    spt_a: float | None,
    spt_b: float | None,
) -> ResolvedMeasurements:
    row_a = _nearest_row(chart_rows, spt_a)
    row_i = _nearest_row(chart_rows, chi)
    row_b = _nearest_row(chart_rows, spt_b)

    return ResolvedMeasurements(
        hgt_a=max(row_a["heights"]) if row_a else None,
        hgt_i=max(row_i["heights"]) if row_i else None,
        hgt_b=max(row_b["heights"]) if row_b else None,
        stg_a=max(row_a["staggers"]) if row_a else None,
        stg_i=max(row_i["staggers"]) if row_i else None,
        stg_b=max(row_b["staggers"]) if row_b else None,
    )
