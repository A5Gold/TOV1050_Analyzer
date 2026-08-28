"""
L2 wire wear trend analyzer.
Analyzes L2-level wire wear exceptions across multiple inspection dates.
"""
import math
from dataclasses import dataclass
from datetime import date, datetime
from typing import List, Dict, Optional

import numpy as np
import pandas as pd

from app.core.calculation.excel_parser import WireWearRecord, ChartDataRecord, RepeatedSummaryRecord


L2_THRESHOLD: float = 10.2
TOLERANCE: float = 0.2
CYCLE_DAYS: Dict[str, int] = {'EAL': 30, 'TML': 90, 'LMC': 90, 'RAC': 30, 'LOW S1': 30}


def calculate_trend(days: List[float], values: List[float]):
    """Linear regression on (days, values), ignoring None and NaN. Returns (slope, intercept)."""
    pairs = [(d, v) for d, v in zip(days, values) if v is not None and not (isinstance(v, float) and math.isnan(v))]
    if len(pairs) < 2:
        return (0.0, float(pairs[0][1]) if pairs else 0.0)
    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    slope, intercept = np.polyfit(xs, ys, 1)
    return (float(slope), float(intercept))


def calculate_trend_points(slope: float, intercept: float, base_day: float, n: int) -> List[float]:
    """Return n trend values at base_day, base_day+1, ..., clamped to >= 0, rounded to 2dp."""
    return [max(0.0, round(slope * (base_day + i) + intercept, 2)) for i in range(n)]


def determine_recommendation(max_val: float, trd_pt: float):
    """Return (logic_1, logic_2, recommendation) based on threshold/tolerance rules."""
    logic_1 = trd_pt <= L2_THRESHOLD
    logic_2 = abs(max_val - trd_pt) > TOLERANCE
    if not logic_1:
        rec = 'no action required'
    elif logic_2:
        rec = 'verify on site'
    else:
        rec = 'confirmed valid L2'
    return (logic_1, logic_2, rec)


@dataclass
class TrendResult:
    tension_length: str
    from_m: float
    to_m: float
    level: str
    dates: List[str]            # task_run_dates sorted newest first
    record_points: List[Optional[float]]  # avg_wear_min per date; None when no data for that date
    trend_points: List[float]   # fitted values at same dates
    trend_next: float           # projected value at next inspection
    logic_1: bool               # trend_next <= 10.2
    logic_2: bool               # |record_points[0] - trend_next| > 0.2
    recommendation: str
    exception_id: str = ''
    task_run_date: str = ''
    line: str = ''
    track: str = ''
    section: str = ''
    task_no: str = ''
    station_start: str = ''
    station_end: str = ''
    max_value: float = 0.0
    max_location: float = 0.0


def _parse_date(s: str) -> date:
    """Parse date string supporting multiple formats. Returns None for empty/unparseable strings."""
    if not s or not s.strip():
        return None
    for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%Y/%m/%d'):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            continue
    return None


def analyze_trend(
    wire_wear_records: List[WireWearRecord],
    chart_data_by_date: Dict[str, List[ChartDataRecord]],
    line: str = 'EAL',
    repeated_records: Optional[List[RepeatedSummaryRecord]] = None,
) -> List[TrendResult]:
    """
    Analyze L2 wire wear trend across multiple inspection dates.

    Args:
        wire_wear_records: Wire Wear rows (typically from the latest Excel)
        chart_data_by_date: {task_run_date: [ChartDataRecord]} for all uploaded Excels
        line: 'EAL', 'TML', or 'LMC' — determines next inspection cycle days
        repeated_records: Optional Wire Wear L2 rows from n_Repeated Exception Report Summary sheet.
            When provided (Case B), only IDs present in both repeated report and wire wear sheet are analyzed.
            When None (Case A), existing logic applies — latest-cycle L2 with blank ACTION.

    Returns:
        List of TrendResult, one per qualifying L2 tension length.
    """
    def _normalize_id(value: str) -> str:
        return str(value or '').strip()

    # Determine which L2 Wire Wear exceptions to analyze
    if repeated_records is not None:
        # Case B: filter by ID match between repeated report and latest-cycle wire wear sheet
        repeated_ids = {_normalize_id(r.exception_id) for r in repeated_records}
        l2_records = [
            r for r in wire_wear_records
            if r.level == 'L2' and not r.action and _normalize_id(r.exception_id) in repeated_ids
        ]
        if l2_records:
            latest_run_date = max(r.run_date for r in l2_records)
            l2_records = [r for r in l2_records if r.run_date == latest_run_date]
    else:
        # Case A: existing logic — latest-cycle L2 with blank ACTION
        l2_records = [
            r for r in wire_wear_records
            if r.level == 'L2' and not r.action
        ]
        if l2_records:
            latest_run_date = max(r.run_date for r in l2_records)
            l2_records = [r for r in l2_records if r.run_date == latest_run_date]

    repeated_max_location: Dict[str, float] = {}
    if repeated_records is not None:
        for record in repeated_records:
            repeated_max_location[_normalize_id(record.exception_id)] = record.max_location

    # Collect per-TL metadata from ChartDataRecord
    tl_meta: Dict[str, dict] = {}
    for records in chart_data_by_date.values():
        for r in records:
            tl = r.tension_length.strip()
            if tl and tl not in tl_meta:
                tl_meta[tl] = {
                    'track': r.track or '',
                    'section': r.section or '',
                    'task_no': r.task_no or '',
                    'station_start': r.station_start or '',
                    'station_end': r.station_end or '',
                }

    results: List[TrendResult] = []

    for rec in l2_records:
        # Build min(wear_min) within rec.from_m..rec.to_m per date, keyed by exception_id
        exc_date_min: Dict[str, float] = {}
        for run_date, records in chart_data_by_date.items():
            matching = [
                r.wear_min for r in records
                if rec.from_m <= r.chainage <= rec.to_m
            ]
            exc_date_min[run_date] = min(matching) if matching else None

        if not exc_date_min:
            continue

        # Filter out dates that cannot be parsed
        parseable = [(d, _parse_date(d)) for d in exc_date_min.keys()]
        parseable = [(d, pd_) for d, pd_ in parseable if pd_ is not None]
        if not parseable:
            continue

        parseable.sort(key=lambda x: x[1], reverse=True)
        sorted_dates = [d for d, _ in parseable]
        ordinals = [pd_.toordinal() for _, pd_ in parseable]
        values = [exc_date_min[d] for d in sorted_dates]

        # Drop None values before regression
        valid_pairs = [(o, v) for o, v in zip(ordinals, values) if v is not None]
        if not valid_pairs:
            continue

        valid_ordinals = [o for o, _ in valid_pairs]
        valid_values = [v for _, v in valid_pairs]

        if len(valid_pairs) >= 2:
            slope, intercept = np.polyfit(valid_ordinals, valid_values, 1)
        else:
            slope, intercept = 0.0, float(valid_values[0])

        trend_pts = [round(float(slope * o + intercept), 3) for o in ordinals]

        logic_1 = trend_pts[0] <= L2_THRESHOLD
        logic_2 = abs(values[0] - trend_pts[0]) > TOLERANCE

        if not logic_1:
            recommendation = 'no action required'
        elif logic_2:
            recommendation = 'verify on site'
        else:
            recommendation = 'confirmed valid L2'

        meta = tl_meta.get(rec.tension_length, {})
        results.append(TrendResult(
            tension_length=rec.tension_length,
            from_m=rec.from_m,
            to_m=rec.to_m,
            level='L2',
            dates=sorted_dates,
            record_points=values,
            trend_points=trend_pts,
            trend_next=trend_pts[0],
            logic_1=logic_1,
            logic_2=logic_2,
            recommendation=recommendation,
            exception_id=rec.exception_id or '',
            task_run_date=sorted_dates[0] if sorted_dates else '',
            line=line,
            track=meta.get('track', ''),
            section=meta.get('section', ''),
            task_no=meta.get('task_no', ''),
            station_start=meta.get('station_start', ''),
            station_end=meta.get('station_end', ''),
            max_value=rec.max_value,
            max_location=repeated_max_location.get(_normalize_id(rec.exception_id), rec.max_location),
        ))

    return results
