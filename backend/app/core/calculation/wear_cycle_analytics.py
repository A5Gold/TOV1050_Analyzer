"""All-history analytics for committed wire-wear cycle records."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
import math
from typing import Iterable, Mapping, Sequence

import numpy as np

from app.core.calculation.wear_calculator import calculate_wear_percentage


_DAYS_PER_YEAR = 365.2425
_MAX_WIRE_THICKNESS_MM = 13.2


@dataclass(frozen=True)
class HistoryPoint:
    cycle_date: date
    avg_wear_min: float
    wear_percentage: float


@dataclass(frozen=True)
class TrendResult:
    status: str
    observation_count: int
    mm_per_year: float | None
    wear_percent_per_year: float | None
    r_squared: float | None
    thickness_slope: float | None
    thickness_intercept: float | None
    first_cycle_date: date | None
    latest_cycle_date: date | None

    @property
    def percent_per_year(self) -> float | None:
        """Short alias used by the cycle analytics contract."""
        return self.wear_percent_per_year


def _parse_date(value: object) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _finite_float(value: object) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return result if math.isfinite(result) else None


def _history_points(records: Iterable[Mapping[str, object]]) -> list[HistoryPoint]:
    points: list[HistoryPoint] = []
    for record in records:
        thickness = _finite_float(record.get("avg_wear_min"))
        wear_percentage = _finite_float(record.get("wear_percentage"))
        if thickness is None:
            continue
        try:
            cycle_date = _parse_date(record.get("cycle_date"))
        except (TypeError, ValueError, OverflowError):
            continue
        points.append(HistoryPoint(
            cycle_date,
            thickness,
            wear_percentage if wear_percentage is not None
            else calculate_wear_percentage(thickness),
        ))
    return points


def fit_tl_trend(points: Sequence[HistoryPoint]) -> TrendResult:
    """Fit remaining thickness over elapsed years, using one mean per date."""
    by_date: dict[date, list[HistoryPoint]] = {}
    for point in points:
        if not math.isfinite(point.avg_wear_min):
            continue
        by_date.setdefault(point.cycle_date, []).append(point)
    dates = sorted(by_date)
    if len(dates) < 2:
        return TrendResult(
            "insufficient_data", len(dates), None, None, None, None, None,
            dates[0] if dates else None, dates[-1] if dates else None,
        )

    first_date = dates[0]
    elapsed_years = np.array([(item - first_date).days / _DAYS_PER_YEAR for item in dates])
    thicknesses = np.array(
        [np.mean([point.avg_wear_min for point in by_date[item]]) for item in dates]
    )
    try:
        slope, intercept = np.polyfit(elapsed_years, thicknesses, 1)
    except (FloatingPointError, TypeError, ValueError, np.linalg.LinAlgError):
        return TrendResult(
            "insufficient_data", len(dates), None, None, None, None, None,
            first_date, dates[-1],
        )
    if not math.isfinite(float(slope)) or not math.isfinite(float(intercept)):
        return TrendResult(
            "insufficient_data", len(dates), None, None, None, None, None,
            first_date, dates[-1],
        )
    fitted = slope * elapsed_years + intercept
    ss_res = float(np.sum((thicknesses - fitted) ** 2))
    ss_tot = float(np.sum((thicknesses - float(np.mean(thicknesses))) ** 2))
    r_squared = 1.0 if ss_tot == 0 else 1.0 - ss_res / ss_tot
    if not math.isfinite(r_squared):
        r_squared = None
    mm_per_year = -float(slope)
    if mm_per_year <= 0:
        return TrendResult(
            "non_positive_rate", len(dates), None, None, r_squared,
            float(slope), float(intercept), first_date, dates[-1],
        )

    start_wear = calculate_wear_percentage(float(intercept))
    next_wear = calculate_wear_percentage(float(intercept + slope))
    return TrendResult(
        "eligible", len(dates), mm_per_year, next_wear - start_wear, r_squared,
        float(slope), float(intercept), first_date, dates[-1],
    )


def _latest_record(
    records: Sequence[Mapping[str, object]],
) -> Mapping[str, object] | None:
    candidates: list[tuple[date, Mapping[str, object]]] = []
    for record in records:
        if _finite_float(record.get("avg_wear_min")) is None:
            continue
        try:
            candidates.append((_parse_date(record.get("cycle_date")), record))
        except (TypeError, ValueError, OverflowError):
            continue
    return max(candidates, key=lambda item: item[0])[1] if candidates else None


def _trend_row(
    line_group: str,
    line_class: str,
    tension_length: str,
    records: Sequence[Mapping[str, object]],
) -> dict:
    latest = _latest_record(records)
    trend = fit_tl_trend(_history_points(records))
    latest_thickness = _finite_float(latest.get("avg_wear_min")) if latest else None
    latest_wear = _finite_float(latest.get("wear_percentage")) if latest else None
    if latest_wear is None and latest_thickness is not None:
        latest_wear = calculate_wear_percentage(latest_thickness)
    return {
        "line_group": line_group,
        "line_class": line_class,
        "tension_length": tension_length,
        "track": latest.get("track") if latest else None,
        "from_m": _finite_float(latest.get("from_m")) if latest else None,
        "to_m": _finite_float(latest.get("to_m")) if latest else None,
        "latest_cycle_date": str(latest["cycle_date"]) if latest else None,
        "latest_avg_wear_min": latest_thickness,
        "latest_wear_percentage": latest_wear,
        "wear_rate_percent_per_year": trend.wear_percent_per_year,
        "percent_per_year": trend.percent_per_year,
        "wear_rate_mm_per_year": trend.mm_per_year,
        "observation_count": trend.observation_count,
        "r_squared": trend.r_squared,
        "trend_status": trend.status,
        "_trend": trend,
        "_latest": latest,
        # Keep existing clients functional while they adopt the explicit rate names.
        "wear_percent_per_year": trend.wear_percent_per_year,
        "wear_mm_per_year": trend.mm_per_year,
        "record_count": trend.observation_count,
    }


def _group_by_tl(
    records: Iterable[Mapping[str, object]],
    line_group: str,
) -> dict[tuple[str, str], list[Mapping[str, object]]]:
    grouped: dict[tuple[str, str], list[Mapping[str, object]]] = {}
    for record in records:
        if str(record.get("line_group", "")).upper() == line_group:
            line_class = str(record.get("line_class") or line_group).upper()
            tension_length = str(record.get("tension_length") or "").strip()
            if tension_length:
                grouped.setdefault((line_class, tension_length), []).append(record)
    return grouped


def build_dashboard(records: Iterable[Mapping[str, object]], line_group: str | None = None) -> dict:
    line = (line_group or "ALL").upper()
    if line not in {"EAL", "TML", "ALL"}:
        raise ValueError("line_group must be ALL, EAL, or TML")
    record_list = list(records)
    lines = ("EAL", "TML") if line == "ALL" else (line,)
    rows = [
        _trend_row(current_line, line_class, tension_length, history)
        for current_line in lines
        for (line_class, tension_length), history
        in _group_by_tl(record_list, current_line).items()
    ]
    max_rows = [row for row in rows if row["trend_status"] == "eligible"]
    min_rows = [row for row in max_rows if float(row["wear_rate_mm_per_year"]) > 0]
    current_rows = sorted(
        (row for row in rows if row["latest_wear_percentage"] is not None),
        key=lambda row: row["latest_wear_percentage"],
        reverse=True,
    )[:5]
    return {
        "top_max_rate": sorted(max_rows, key=lambda row: row["wear_rate_mm_per_year"], reverse=True)[:5],
        "top_min_rate": sorted(min_rows, key=lambda row: row["wear_rate_mm_per_year"])[:5],
        "top_current_wear": current_rows,
    }


def build_projection(
    records: Iterable[Mapping[str, object]],
    threshold_mm: float,
    as_of: date,
    horizon_years: int = 30,
) -> dict:
    if not 0 < threshold_mm <= _MAX_WIRE_THICKNESS_MM:
        raise ValueError(f"threshold_mm must be between 0 and {_MAX_WIRE_THICKNESS_MM}")
    if horizon_years < 1:
        raise ValueError("horizon_years must be positive")

    threshold_percentage = calculate_wear_percentage(threshold_mm)
    record_list = list(records)
    start_year = as_of.year + 1
    end_year = as_of.year + horizon_years
    output = {
        "threshold_mm": threshold_mm,
        "threshold_percentage": threshold_percentage,
        "years": horizon_years,
        "horizon_years": horizon_years,
        "line_groups": {},
    }
    for line in ("EAL", "TML"):
        buckets = [{"year": year, "count": 0, "records": []} for year in range(start_year, end_year + 1)]
        group = {
            "year_buckets": buckets,
            "already_at_threshold": [],
            "insufficient_data": [],
            "non_positive_rate": [],
            "outside_horizon": [],
        }
        for (line_class, tension_length), history in _group_by_tl(record_list, line).items():
            row = _trend_row(line, line_class, tension_length, history)
            trend: TrendResult = row.pop("_trend")
            latest = row.pop("_latest")
            latest_thickness = row["latest_avg_wear_min"]
            if latest is None or latest_thickness is None:
                row["trend_status"] = "insufficient_data"
                group["insufficient_data"].append(row)
                continue
            if latest_thickness <= threshold_mm:
                row["trend_status"] = "already_at_threshold"
                group["already_at_threshold"].append(row)
                continue
            if trend.status == "insufficient_data":
                group["insufficient_data"].append(row)
                continue
            if trend.status == "non_positive_rate":
                group["non_positive_rate"].append(row)
                continue
            if (
                trend.thickness_slope is None
                or trend.thickness_intercept is None
                or trend.first_cycle_date is None
            ):
                row["trend_status"] = "insufficient_data"
                group["insufficient_data"].append(row)
                continue
            elapsed_years = (threshold_mm - trend.thickness_intercept) / trend.thickness_slope
            crossing_days = elapsed_years * _DAYS_PER_YEAR
            if not math.isfinite(crossing_days):
                row["trend_status"] = "insufficient_data"
                group["insufficient_data"].append(row)
                continue
            days_from_as_of = (
                trend.first_cycle_date - as_of
            ).days + crossing_days
            if days_from_as_of > horizon_years * _DAYS_PER_YEAR + 366:
                row["trend_status"] = "outside_horizon"
                row["projected_crossing_date"] = None
                row["projected_year"] = None
                row["years_to_threshold"] = days_from_as_of / _DAYS_PER_YEAR
                group["outside_horizon"].append(row)
                continue
            try:
                crossing_date = trend.first_cycle_date + timedelta(days=crossing_days)
            except (OverflowError, ValueError):
                row["trend_status"] = "outside_horizon"
                row["projected_crossing_date"] = None
                row["projected_year"] = None
                row["years_to_threshold"] = None
                group["outside_horizon"].append(row)
                continue
            row["projected_crossing_date"] = crossing_date.isoformat()
            row["projected_year"] = crossing_date.year
            row["years_to_threshold"] = max(0.0, (crossing_date - as_of).days / _DAYS_PER_YEAR)
            if crossing_date <= as_of:
                row["trend_status"] = "already_at_threshold"
                group["already_at_threshold"].append(row)
                continue
            if start_year <= crossing_date.year <= end_year:
                bucket = buckets[crossing_date.year - start_year]
                bucket["records"].append(row)
                bucket["count"] += 1
        output["line_groups"][line] = group
    return output


def build_remaining_life(
    records: Iterable[Mapping[str, object]],
    threshold_mm: float,
    as_of: date,
) -> dict:
    """Build remaining-life rows and sampled curves from the fitted TL trends."""
    if not 0 < threshold_mm <= _MAX_WIRE_THICKNESS_MM:
        raise ValueError(f"threshold_mm must be between 0 and {_MAX_WIRE_THICKNESS_MM}")
    record_list = list(records)
    rows: list[dict] = []
    for line in ("EAL", "TML"):
        for (line_class, tension_length), history in _group_by_tl(record_list, line).items():
            row = _trend_row(line, line_class, tension_length, history)
            trend: TrendResult = row.pop("_trend")
            latest = row.pop("_latest")
            latest_thickness = row.get("latest_avg_wear_min")
            status = trend.status
            crossing_date = None
            remaining_days = None
            curve: list[dict] = []
            if latest is None or latest_thickness is None:
                status = "insufficient_data"
            elif latest_thickness <= threshold_mm:
                status = "already_at_threshold"
                remaining_days = 0
                curve = [{"date": as_of.isoformat(), "remaining_days": 0}]
            elif status == "eligible" and trend.thickness_slope is not None and trend.thickness_intercept is not None and trend.first_cycle_date is not None:
                elapsed = (threshold_mm - trend.thickness_intercept) / trend.thickness_slope
                days = elapsed * _DAYS_PER_YEAR
                if math.isfinite(days):
                    try:
                        crossing_date = trend.first_cycle_date + timedelta(days=days)
                        remaining_days = max(0, (crossing_date - as_of).days)
                    except (OverflowError, ValueError):
                        status = "insufficient_data"
                else:
                    status = "insufficient_data"
                if crossing_date is not None and crossing_date <= as_of:
                    status = "already_at_threshold"
                    remaining_days = 0
                elif crossing_date is not None and crossing_date > as_of:
                    span_days = (crossing_date - as_of).days
                    step = max(1, span_days // 24)
                    point_day = 0
                    while point_day < span_days:
                        point_date = as_of + timedelta(days=point_day)
                        curve.append({"date": point_date.isoformat(), "remaining_days": max(0, span_days - point_day)})
                        point_day += step
                    curve.append({"date": crossing_date.isoformat(), "remaining_days": 0})
            if status != "eligible":
                curve = [] if status != "already_at_threshold" else curve
            row.update({
                "trend_status": status,
                "projected_crossing_date": crossing_date.isoformat() if crossing_date else None,
                "remaining_days": remaining_days,
                "curve": curve,
            })
            rows.append(row)
    defaults: list[dict] = []
    for line in ("EAL", "TML"):
        eligible = [r for r in rows if r["line_group"] == line and r["trend_status"] == "eligible" and r["remaining_days"] is not None]
        if eligible:
            defaults.append(min(eligible, key=lambda r: r["remaining_days"]))
    return {"threshold_mm": threshold_mm, "rows": rows, "default_rows": defaults}
