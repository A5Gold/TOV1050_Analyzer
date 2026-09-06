"""Chart-only level-of-detail sampling.

Detection always runs on the complete frame. This module reduces only the
payload sent to Plotly and keeps extrema/provenance rows so isolated spikes
remain visible in an overview chart.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping

import numpy as np
import pandas as pd


def build_chart_payload(
    frame: pd.DataFrame,
    columns: Iterable[str],
    *,
    max_points: int = 6000,
    from_m: float | None = None,
    to_m: float | None = None,
    preserve_chainage: Iterable[float] = (),
) -> tuple[dict[str, list[Any]], dict[str, Any]]:
    """Return a column-oriented chart payload and resolution metadata.

    ``max_points`` is a target, not a hard cap: extrema rows are always kept.
    The returned rows retain their original source index in the metadata when
    the caller includes such a column, and all source values remain untouched.
    """

    selected_columns = list(dict.fromkeys(column for column in columns if column in frame.columns))
    preserve_values = list(preserve_chainage)
    if "Chainage" not in selected_columns or "Chainage" not in frame.columns:
        return {}, {"source_points": 0, "returned_points": 0, "strategy": "none"}

    working = frame[selected_columns]
    chainage = pd.to_numeric(working["Chainage"], errors="coerce")
    mask = chainage.notna()
    if from_m is not None:
        mask &= chainage >= float(from_m)
    if to_m is not None:
        mask &= chainage <= float(to_m)
    positions = np.flatnonzero(mask.to_numpy())
    source_points = int(len(positions))
    if source_points == 0:
        return {column: [] for column in selected_columns}, {
            "source_points": 0,
            "returned_points": 0,
            "strategy": "empty",
            "from_m": from_m,
            "to_m": to_m,
        }

    keep: set[int] = set()
    if source_points <= max_points:
        keep.update(positions.tolist())
        strategy = "raw"
        bucket_count = source_points
    else:
        bucket_count = max(1, int(max_points))
        strategy = "min_max_envelope"
        numeric_columns = [
            column
            for column in selected_columns
            if column != "Chainage" and any(token in column.lower() for token in ("height", "stagger", "wear"))
        ]
        for bucket in range(bucket_count):
            start = (bucket * source_points) // bucket_count
            end = ((bucket + 1) * source_points) // bucket_count
            bucket_positions = positions[start:end]
            if len(bucket_positions) == 0:
                continue
            keep.add(int(bucket_positions[0]))
            keep.add(int(bucket_positions[-1]))
            for column in numeric_columns:
                values = pd.to_numeric(working.iloc[bucket_positions][column], errors="coerce").to_numpy(dtype=float)
                finite = np.flatnonzero(np.isfinite(values))
                if len(finite):
                    keep.add(int(bucket_positions[int(finite[np.argmin(values[finite])])]))
                    keep.add(int(bucket_positions[int(finite[np.argmax(values[finite])])]))

    chainage_values = chainage.to_numpy(dtype=float)
    for requested in preserve_values:
        try:
            value = float(requested)
        except (TypeError, ValueError):
            continue
        candidate_positions = positions[np.argsort(np.abs(chainage_values[positions] - value))]
        if len(candidate_positions):
            keep.add(int(candidate_positions[0]))

    ordered = np.array(sorted(keep), dtype=int)
    payload = working.iloc[ordered].replace({np.nan: None}).to_dict(orient="list")
    return payload, {
        "source_points": source_points,
        "returned_points": int(len(ordered)),
        "bucket_count": bucket_count,
        "strategy": strategy,
        "from_m": from_m,
        "to_m": to_m,
        "preserved_chainage_count": len(preserve_values),
    }
