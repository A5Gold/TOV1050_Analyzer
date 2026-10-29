"""Chart-only level-of-detail sampling.

Detection always runs on the complete analysis frame. This module reduces only the
payload sent to Plotly and keeps extrema/provenance rows so isolated spikes
remain visible in an overview chart.
"""

from __future__ import annotations

from typing import Any, Iterable

import numpy as np
import pandas as pd

from .chart_cache import ChartSource


MEASUREMENT_COLUMNS = {
    *(f"{kind}{channel}" for kind in ("height", "stagger", "wear") for channel in range(1, 5)),
    "height_min", "height_max", "stg_min", "stg_max", "wear_min", "wear_max",
}


def build_chart_payload(
    frame: pd.DataFrame | ChartSource,
    columns: Iterable[str],
    *,
    max_points: int = 6000,
    from_m: float | None = None,
    to_m: float | None = None,
    preserve_chainage: Iterable[float] = (),
    preserve_group_ids: Iterable[Any] = (),
    progress=None,
) -> tuple[dict[str, list[Any]], dict[str, Any]]:
    """Return a column-oriented chart payload and resolution metadata.

    ``max_points`` targets returned rows, not the number of envelope buckets.
    Explicitly preserved groups and discontinuities may exceed that target.
    The returned rows retain their original source index in the metadata when
    the caller includes such a column, and all source values remain untouched.
    """

    selected_columns = list(dict.fromkeys(column for column in columns if column in frame.columns))
    preserve_values = list(preserve_chainage)
    preserve_groups = list(preserve_group_ids)
    if "Chainage" not in selected_columns or "Chainage" not in frame.columns:
        return {}, {"source_points": 0, "returned_points": 0, "strategy": "none"}

    # Convert/index once per revision at the caller. Decode only the viewport,
    # not every measurement/provenance column of the complete source frame.
    if isinstance(frame, ChartSource):
        frame = frame.window(from_m, to_m)
    working = frame[selected_columns]
    chainage = pd.to_numeric(working["Chainage"], errors="coerce")
    chainage_values = chainage.to_numpy(dtype=float, na_value=np.nan)
    mask = np.isfinite(chainage_values)
    if from_m is not None:
        mask &= chainage_values >= float(from_m)
    if to_m is not None:
        mask &= chainage_values <= float(to_m)
    positions = np.flatnonzero(mask)
    source_points = int(len(positions))
    if source_points == 0:
        return {column: [] for column in selected_columns}, {
            "source_points": 0,
            "returned_points": 0,
            "strategy": "empty",
            "from_m": from_m,
            "to_m": to_m,
        }

    # A direct (noncached) caller also slices before converting measurements.
    working = working.iloc[positions].reset_index(drop=True)
    frame = frame.iloc[positions].reset_index(drop=True)
    chainage_values = chainage_values[positions]
    positions = np.arange(source_points)
    numeric_columns = [column for column in selected_columns if column in MEASUREMENT_COLUMNS]
    numeric_values = {
        column: pd.to_numeric(working[column], errors="coerce").to_numpy(dtype=float, na_value=np.nan)
        for column in numeric_columns
    }
    keep: set[int] = set()
    if source_points <= max_points:
        keep.update(positions.tolist())
        strategy = "raw"
        bucket_count = source_points
    else:
        # Each bucket contributes at most first/last plus two extrema per
        # channel. Provenance/count columns never influence the selection.
        bucket_count = max(1, int(max_points) // (2 + 2 * len(numeric_columns)))
        strategy = "min_max_envelope"
        for bucket in range(bucket_count):
            if progress and bucket % 100 == 0:
                progress("preparing_chart", bucket, bucket_count, "buckets")
            start = (bucket * source_points) // bucket_count
            end = ((bucket + 1) * source_points) // bucket_count
            bucket_positions = positions[start:end]
            if len(bucket_positions) == 0:
                continue
            keep.add(int(bucket_positions[0]))
            keep.add(int(bucket_positions[-1]))
            for column in numeric_columns:
                values = numeric_values[column][bucket_positions]
                finite = np.flatnonzero(np.isfinite(values))
                if len(finite):
                    keep.add(int(bucket_positions[int(finite[np.argmin(values[finite])])]))
                    keep.add(int(bucket_positions[int(finite[np.argmax(values[finite])])]))

    # Retain both sides of every segment boundary and null/nonfinite run.
    # Otherwise an overview could drop the only null row and connect values
    # across a missing measurement even though the detail correctly has a gap.
    mandatory: set[int] = {int(positions[0]), int(positions[-1])}
    if "segment_id" in frame:
        segments = frame["segment_id"].iloc[positions].reset_index(drop=True)
        same = segments.eq(segments.shift()) | (segments.isna() & segments.shift().isna())
        changes = np.flatnonzero(~same.fillna(False).to_numpy(dtype=bool))
        changes = changes[changes > 0]
        for offset in changes:
            mandatory.update((int(positions[offset - 1]), int(positions[offset])))
    for values in numeric_values.values():
        valid = np.isfinite(values[positions])
        for offset in np.flatnonzero(valid[1:] != valid[:-1]) + 1:
            mandatory.update((int(positions[offset - 1]), int(positions[offset])))
    if preserve_groups and "group_id" in frame:
        mandatory.update(positions[frame["group_id"].iloc[positions].isin(preserve_groups).to_numpy()].tolist())
    keep.update(mandatory)

    for requested in preserve_values:
        try:
            value = float(requested)
        except (TypeError, ValueError):
            continue
        if np.isfinite(value):
            keep.add(int(positions[np.argmin(np.abs(chainage_values[positions] - value))]))

    ordered = np.array(sorted(keep), dtype=int)
    payload = working.iloc[ordered].replace({np.nan: None, np.inf: None, -np.inf: None}).to_dict(orient="list")
    if progress:
        progress("preparing_chart", bucket_count, bucket_count, "buckets")
    return payload, {
        "source_points": source_points,
        "returned_points": int(len(ordered)),
        "bucket_count": bucket_count,
        "strategy": strategy,
        "from_m": from_m,
        "to_m": to_m,
        "preserved_chainage_count": len(preserve_values),
        "preserved_group_count": len(preserve_groups),
        "mandatory_points": len(mandatory),
        "target_points": int(max_points),
    }


def normalize_chart_window(domain, from_m=None, to_m=None):
    """Finite viewport bounds, sorted and clipped without inventing samples."""
    for value in (from_m, to_m):
        if value is not None and not np.isfinite(value):
            raise ValueError("Chart range bounds must be finite numbers")
    if from_m is not None and to_m is not None and from_m > to_m:
        from_m, to_m = to_m, from_m
    if domain is None:
        return from_m, to_m, True
    start = domain["from_m"] if from_m is None else max(float(from_m), domain["from_m"])
    end = domain["to_m"] if to_m is None else min(float(to_m), domain["to_m"])
    return start, end, start > end


def build_mean_chart_payload(frame: pd.DataFrame, columns: Iterable[str], **sampling_kwargs):
    """Build the mean overview with raw range statistics and source provenance."""
    from .chainage_aggregation import aggregate_chainage, CHANNELS

    derived, aggregation = aggregate_chainage(frame, progress=sampling_kwargs.get("progress"))
    statistics = [f"{channel}_{stat}" for channel in CHANNELS for stat in ("min", "max", "count")]
    provenance = ["group_id", "pass_id", "sample_count", "source_row_first", "source_row_last",
                  "SampleCount_first", "SampleCount_last"]
    payload, resolution = build_chart_payload(derived, [*columns, *statistics, *provenance], **sampling_kwargs)
    return payload, {**resolution, **aggregation, "display_mode": "chainage_mean"}
