"""Average wire wear calculator for the Calculation Module."""
import math
import logging
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple
from collections import defaultdict

import pandas as pd

from app.core.calculation.excel_parser import ChartDataRecord

logger = logging.getLogger(__name__)

_WIRE_RADIUS = 6.6
_CROSS_SECTION = 120.0


@dataclass(frozen=True)
class WearResult:
    tension_length: str
    from_m: float
    to_m: float
    line: str
    track: str
    section: str
    cycle_date: str
    avg_wear_min: float
    sd: float
    wear_percentage: float
    dates: Tuple[str, ...]
    record_points: tuple


def calculate_wear_percentage(mean_remaining: float) -> float:
    if mean_remaining == 0.0:
        return 0.0
    r = mean_remaining
    R = _WIRE_RADIUS
    try:
        cos_arg = max(-1.0, min(1.0, (r - R) / R))
        theta = math.acos(cos_arg)
        worn_area = theta * R ** 2 - R * math.sin(theta) * (r - R)
        wear = (worn_area / _CROSS_SECTION) * 100.0
        return round(min(100.0, max(0.0, wear)), 2)
    except (ValueError, ZeroDivisionError):
        return 100.0


def calculate_wear_statistics(values: Sequence[float]) -> tuple[float, Optional[float]]:
    """Return a rounded mean and sample SD for wear measurements."""
    if not values:
        raise ValueError("at least one wear measurement is required")
    numeric_values = tuple(float(value) for value in values)
    if any(not math.isfinite(value) for value in numeric_values):
        raise ValueError("wear measurements must be finite")

    scale = max(abs(value) for value in numeric_values)
    if scale == 0.0:
        mean = 0.0
        sample_sd = 0.0 if len(numeric_values) > 1 else None
    else:
        scaled_values = tuple(value / scale for value in numeric_values)
        scaled_mean = math.fsum(scaled_values) / len(scaled_values)
        mean = scale * scaled_mean
        sample_sd = None
        if len(scaled_values) > 1:
            scaled_variance = math.fsum(
                (value - scaled_mean) ** 2 for value in scaled_values
            ) / (len(scaled_values) - 1)
            sample_sd = scale * math.sqrt(scaled_variance)

    if not math.isfinite(mean) or (
        sample_sd is not None and not math.isfinite(sample_sd)
    ):
        raise ValueError("wear statistics must be finite")
    return round(mean, 2), round(sample_sd, 2) if sample_sd is not None else None


def calculate_average_wear(
    records: List[ChartDataRecord],
    tl_lookup: Optional[pd.DataFrame] = None,
) -> List[WearResult]:
    if not records:
        return []

    normalized_lookup = None
    lookup_segments = None
    if tl_lookup is not None and not tl_lookup.empty:
        normalized_lookup = tl_lookup.copy()
        normalized_lookup['from_m'] = pd.to_numeric(normalized_lookup['from_m'], errors='coerce')
        normalized_lookup['to_m'] = pd.to_numeric(normalized_lookup['to_m'], errors='coerce')
        normalized_lookup = normalized_lookup.dropna(subset=['from_m', 'to_m', 'tension_length'])
        lookup_segments = [
            {
                'from_m': float(row['from_m']),
                'to_m': float(row['to_m']),
                'tension_length': str(row['tension_length']).strip(),
                'track_type': str(row.get('track_type', '') or '').strip().casefold(),
            }
            for _, row in normalized_lookup.iterrows()
        ]

    def resolve_segments(rec: ChartDataRecord) -> List[dict]:
        if lookup_segments:
            matches = [
                segment for segment in lookup_segments
                if segment['from_m'] <= rec.chainage <= segment['to_m']
            ]
            if matches:
                if rec.track_type:
                    track_type = str(rec.track_type).strip().casefold()
                    typed = [segment for segment in matches if segment['track_type'] == track_type]
                    if typed:
                        matches = typed
                return [
                    {
                        'tension_length': segment['tension_length'],
                        'from_m': round(segment['from_m'], 2),
                        'to_m': round(segment['to_m'], 2),
                    }
                    for segment in matches
                ]

        return [
            {
                'tension_length': tl.strip(),
                'from_m': None,
                'to_m': None,
            }
            for tl in str(rec.tension_length).split(',')
            if tl.strip()
        ]

    expanded: List[dict] = []
    for rec in records:
        for seg in resolve_segments(rec):
            expanded.append({
                'task_run_date': rec.task_run_date,
                'line': rec.line,
                'track': rec.track,
                'section': rec.section,
                'chainage': rec.chainage,
                'wear_min': rec.wear_min,
                'tension_length': seg['tension_length'],
                'from_m': seg['from_m'],
                'to_m': seg['to_m'],
            })

    groups: dict = defaultdict(list)
    for rec in expanded:
        key = (rec['line'], rec['tension_length'])
        groups[key].append(rec)

    results: List[WearResult] = []
    for (line, tl), recs in groups.items():
        date_groups: dict = defaultdict(list)
        for rec in recs:
            date_groups[rec['task_run_date']].append(rec['wear_min'])

        sorted_dates = tuple(sorted(date_groups.keys()))
        record_points = tuple(
            calculate_wear_statistics(date_groups[d])[0] for d in sorted_dates
        )

        all_wear = [rec['wear_min'] for rec in recs]
        avg, sample_sd = calculate_wear_statistics(all_wear)
        sd = sample_sd if sample_sd is not None else 0.0
        chainages = [rec['chainage'] for rec in recs]

        from_values = [rec['from_m'] for rec in recs if rec['from_m'] is not None]
        to_values = [rec['to_m'] for rec in recs if rec['to_m'] is not None]

        resolved_from = round(min(from_values), 2) if from_values else round(min(chainages), 2)
        resolved_to = round(max(to_values), 2) if to_values else round(max(chainages), 2)
        tracks = sorted({str(rec['track'] or '').strip() for rec in recs if str(rec['track'] or '').strip()})
        sections = sorted({str(rec['section'] or '').strip() for rec in recs if str(rec['section'] or '').strip()})
        output_track = 'Siding' if len(tracks) > 1 else (tracks[0] if tracks else '')
        output_section = 'Mixed' if len(sections) > 1 else (sections[0] if sections else '')

        results.append(WearResult(
            tension_length=tl,
            from_m=resolved_from,
            to_m=resolved_to,
            line=line,
            track=output_track,
            section=output_section,
            cycle_date=sorted_dates[-1] if sorted_dates else '',
            avg_wear_min=avg,
            sd=sd,
            wear_percentage=calculate_wear_percentage(avg),
            dates=sorted_dates,
            record_points=record_points,
        ))
    return results
