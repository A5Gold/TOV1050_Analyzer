"""
L2 wire wear trend analyzer.
Analyzes L2-level wire wear exceptions across multiple inspection dates.
"""
import math
from dataclasses import dataclass
from functools import lru_cache
from datetime import date, datetime
from typing import List, Dict, Optional

import numpy as np
import pandas as pd

from app.core.calculation.excel_parser import WireWearRecord, ChartDataRecord, RepeatedSummaryRecord
from app.core.report_context import (
    ReportContext, ReportContextError, ensure_compatible_scopes, normalize_report_row,
    validate_algorithm_compatibility,
)


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
    branch: str = ''
    direction: str = ''
    algorithm_status: str = 'unknown'


def _parse_date(s: str) -> date:
    """Parse date string supporting multiple formats. Returns None for empty/unparseable strings."""
    if not s or not s.strip():
        return None
    for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%Y/%m/%d', '%Y%m%d'):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            continue
    return None


def analyze_trend(
    wire_wear_records: List[WireWearRecord],
    chart_data_by_date: Dict[str, List[ChartDataRecord]],
    line: str = '',
    repeated_records: Optional[List[RepeatedSummaryRecord]] = None,
) -> List[TrendResult]:
    """
    Analyze L2 wire wear trend across multiple inspection dates.

    Args:
        wire_wear_records: Wire Wear rows (typically from the latest Excel)
        chart_data_by_date: {task_run_date: [ChartDataRecord]} for all uploaded Excels
        line: Optional explicit identity for old reports that have no line cells.
        repeated_records: Optional Wire Wear L2 rows from n_Repeated Exception Report Summary sheet.
            When provided (Case B), only IDs present in both repeated report and wire wear sheet are analyzed.
            When None (Case A), existing logic applies — latest-cycle L2 with blank ACTION.

    Returns:
        List of TrendResult, one per qualifying L2 tension length.
    """
    def _normalize_id(value: str) -> str:
        return str(value or '').strip()

    @lru_cache(maxsize=512)
    def _scope(raw_line, branch, direction, section):
        return normalize_report_row({'line': raw_line, 'branch': branch,
                                     'track': direction, 'section': section}, source='Trend')

    def identity(record):
        return _scope(str(getattr(record, 'line', '') or line or ''),
                      str(getattr(record, 'branch', '') or ''),
                      str(getattr(record, 'direction', '') or getattr(record, 'track', '') or ''),
                      str(getattr(record, 'section', '') or ''))

    shared = ensure_compatible_scopes(
        [identity(record) for record in wire_wear_records]
        + [identity(record) for records in chart_data_by_date.values() for record in records],
        source='Trend uploads',
    )
    algorithm_known = validate_algorithm_compatibility({
        ReportContext(algorithm=record.algorithm, algorithm_mode=record.algorithm_mode)
        for records in chart_data_by_date.values() for record in records
    })

    def compatible(candidate, measurement):
        left, right = identity(candidate), identity(measurement)
        if any(a and b and a != b for a, b in zip(left.scope, right.scope)):
            return False
        if candidate.section and measurement.section and candidate.section.strip().casefold() != measurement.section.strip().casefold():
            return False
        if candidate.tension_length and measurement.tension_length:
            candidate_tls = {value.strip() for value in candidate.tension_length.split(',') if value.strip()}
            measurement_tls = {value.strip() for value in measurement.tension_length.split(',') if value.strip()}
            if not candidate_tls.intersection(measurement_tls):
                return False
        if _parse_date(candidate.run_date) == _parse_date(measurement.task_run_date):
            if candidate.source_id and measurement.source_id and candidate.source_id != measurement.source_id:
                return False
            if candidate.task_no and measurement.task_no and candidate.task_no != measurement.task_no:
                return False
        return candidate.from_m <= measurement.chainage <= candidate.to_m

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

    results: List[TrendResult] = []

    for rec in l2_records:
        # Build min(wear_min) within rec.from_m..rec.to_m per date, keyed by exception_id
        exc_date_min: Dict[str, float] = {}
        for run_date, records in chart_data_by_date.items():
            matching = [r for r in records if compatible(rec, r) and math.isfinite(r.wear_min)]
            tasks = {r.task_no for r in matching if r.task_no}
            sources = {r.source_id for r in matching if r.source_id}
            sections = {r.section.strip().casefold() for r in matching if r.section}
            if len(tasks) > 1 or len(sources) > 1 or len(sections) > 1:
                raise ReportContextError(f'Trend candidate {rec.exception_id}: multiple acquisitions overlap its span on {run_date}; compare each acquisition separately.',
                                         'AMBIGUOUS_REPORT_ACQUISITION')
            exc_date_min[run_date] = min(r.wear_min for r in matching) if matching else None

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
        if not values or values[0] is None:
            continue

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

        # Acquisition metadata comes from the candidate's own Summary. Legacy
        # blanks may only be filled from its own date/scope/span, never the
        # first uploaded TL or another inspection date.
        same_run = [r for records in chart_data_by_date.values() for r in records
                    if _parse_date(r.task_run_date) == _parse_date(rec.run_date)
                    and compatible(rec, r)
                    and (not rec.task_no or not r.task_no or rec.task_no == r.task_no)]
        meta = {}
        for field in ('track', 'section', 'task_no', 'station_start', 'station_end'):
            own = getattr(rec, field, '')
            if own:
                meta[field] = own
                continue
            candidates = {getattr(r, field, '') for r in same_run if getattr(r, field, '')}
            if len(candidates) > 1:
                raise ReportContextError(f'Trend candidate {rec.exception_id}: ambiguous {field} within its acquisition span')
            meta[field] = next(iter(candidates), '')
        scope = identity(rec)
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
            line=scope.line or shared.line,
            branch=scope.branch or shared.branch,
            direction=scope.direction or shared.direction,
            algorithm_status='verified' if algorithm_known else 'unknown',
            track=meta.get('track', ''),
            section=meta.get('section', ''),
            task_no=meta.get('task_no', ''),
            station_start=meta.get('station_start', ''),
            station_end=meta.get('station_end', ''),
            max_value=rec.max_value,
            max_location=repeated_max_location.get(_normalize_id(rec.exception_id), rec.max_location),
        ))

    return results
