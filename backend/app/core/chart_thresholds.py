"""Threshold lines resolved by the detector, independent of exception selection."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .analyzers import ExceptionDetector


def build_threshold_segments(frame, thresholds, detector=None):
    """Capture signed threshold runs from the already mapped analysis frame.

    Undefined classes inherit 'both' only through the detector's resolver;
    explicitly configured NaN levels remain absent. Context/gap/pass changes
    split runs, so the chart never draws a threshold across unrelated passes.
    """
    if (frame.empty or "Chainage" not in frame or "Class" not in frame
            or not isinstance(thresholds, pd.DataFrame) or thresholds.empty):
        return []
    detector = detector or ExceptionDetector(None)
    positions = pd.to_numeric(frame["Chainage"], errors="coerce").to_numpy(dtype=float, na_value=np.nan)
    changes = np.zeros(len(frame), dtype=bool)
    changes[0] = True
    for column in ("Class", "Track Type", "segment_id", "pass_id"):
        if column not in frame:
            continue
        values = frame[column].reset_index(drop=True)
        previous = values.shift()
        same = values.eq(previous) | (values.isna() & previous.isna())
        changes |= ~same.fillna(False).to_numpy(dtype=bool)
    if "source_row_number" in frame:
        source = pd.to_numeric(frame["source_row_number"], errors="coerce").to_numpy(dtype=float, na_value=np.nan)
        changes[1:] |= np.diff(source) != 1
    invalid = ~np.isfinite(positions)
    changes |= invalid
    changes[1:] |= invalid[:-1]
    starts = np.flatnonzero(changes)
    ends = np.r_[starts[1:], len(frame)]
    context = frame.iloc[starts].reset_index(drop=True)
    bounds = []
    for start, end in zip(starts, ends):
        values = positions[start:end]
        finite = values[np.isfinite(values)]
        bounds.append((float(finite.min()), float(finite.max())) if len(finite) else None)

    output = []
    for metric, exception_type, levels in (
        ("height", "Low Height", ("L1", "L2")),
        ("height", "High Height", ("L1", "L2")),
        ("wear", "Wire Wear", ("L1", "L2")),
        ("stagger", "Stagger Left", ("L1", "L2", "L3")),
        ("stagger", "Stagger Right", ("L1", "L2", "L3")),
    ):
        for level in levels:
            bound = f"Stagger {level}" if metric == "stagger" else f"{exception_type} {level}"
            if metric == "stagger":
                resolved = np.full(len(context), np.nan)
                if "Track Type" in context:
                    for track_type in ("Tangent", "Curve"):
                        values = detector._get_vectorized_threshold(context, thresholds, exception_type, bound,
                                                                    track_type=track_type)
                        mask = context["Track Type"].eq(track_type).to_numpy()
                        resolved[mask] = values.to_numpy(dtype=float, na_value=np.nan)[mask]
                # Right-hand detector uses -threshold; left uses +threshold.
                if exception_type == "Stagger Right":
                    resolved = -resolved
            else:
                resolved = detector._get_vectorized_threshold(context, thresholds, exception_type, bound)
            for domain, value in zip(bounds, resolved):
                if domain is not None and np.isfinite(value):
                    output.append({"from_m": domain[0], "to_m": domain[1], "metric": metric,
                                   "exception_type": exception_type, "level": level, "value": float(value)})
    return output


def clip_threshold_segments(segments, from_m=None, to_m=None):
    if from_m is not None and to_m is not None and from_m > to_m:
        return []
    output = []
    for segment in segments:
        start = segment["from_m"] if from_m is None else max(segment["from_m"], from_m)
        end = segment["to_m"] if to_m is None else min(segment["to_m"], to_m)
        if start <= end:
            output.append({**segment, "from_m": start, "to_m": end})
    return output
