"""Derived channel means; never used as detector input or to replace raw data."""
from __future__ import annotations

import numpy as np
import pandas as pd


CHANNELS = tuple(f"{kind}{index}" for kind in ("height", "stagger", "wear") for index in range(1, 5))
SAMPLE_COUNTER_COLUMNS = ("SampleCount", "SampleCount [n.]")
# Only context/metadata identify a group; source row and measurement counters do not.
_IDENTITY_NAMES = {
    "line", "track", "section", "session", "session_id", "task_no", "task_run_date",
    "station_start", "station_end", "class", "track type", "overlap", "tension length",
    "landmark", "source_file", "source_filename", "metadata_segment_id", "segment_id",
}


def aggregate_chainage(frame: pd.DataFrame, *, progress=None):
    """Return means/statistics grouped by exact metre coordinate, context and pass.

    A strictly decreasing sample counter starts a new pass. Both the canonical
    ``SampleCount`` and native CSV ``SampleCount [n.]`` columns are supported;
    canonical takes precedence if both are present. Coordinate direction is
    deliberately irrelevant: repeated nonadjacent coordinates may share a group.
    Source ranges describe provenance bounds, not a contiguous membership claim.
    """
    if "Chainage" not in frame:
        raise ValueError("Chainage is required for chainage aggregation")
    channels = [name for name in CHANNELS if name in frame]
    if progress:
        progress("aggregating_chainage", 0, len(channels), "channels")
    size = len(frame)
    keys = pd.DataFrame({"Chainage": pd.to_numeric(frame["Chainage"], errors="coerce").to_numpy()})
    for column in frame:
        if column.lower() in _IDENTITY_NAMES:
            keys[column] = frame[column].to_numpy()
    counter_column = next((name for name in SAMPLE_COUNTER_COLUMNS if name in frame), None)
    counts = pd.to_numeric(frame[counter_column] if counter_column else pd.Series(np.nan, index=frame.index), errors="coerce")
    counts = counts.replace([np.inf, -np.inf], np.nan)
    passes = counts.ffill().diff().lt(0).cumsum().to_numpy(dtype=np.int64)
    keys["_pass"] = passes
    # Invalid coordinates remain individual rows instead of merging unrelated samples.
    keys["_invalid"] = np.where(np.isfinite(keys["Chainage"]), -1, np.arange(size))
    group_ids = keys.groupby(list(keys.columns), sort=False, dropna=False).ngroup().to_numpy(dtype=np.int64)
    positions = pd.DataFrame({"group": group_ids, "position": np.arange(size)})
    grouped = positions.groupby("group", sort=False)
    first = grouped["position"].first().to_numpy(dtype=int)
    last = grouped["position"].last().to_numpy(dtype=int)
    derived = frame.iloc[first].copy().reset_index(drop=True)
    derived["group_id"] = np.arange(len(first), dtype=np.int64)
    derived["pass_id"] = passes[first]
    derived["sample_count"] = grouped.size().to_numpy()
    source_rows = frame["source_row_number"].to_numpy() if "source_row_number" in frame else np.arange(1, size + 1)
    derived["source_row_first"] = source_rows[first]
    derived["source_row_last"] = source_rows[last]
    if counter_column:
        derived["SampleCount_first"] = frame[counter_column].to_numpy()[first]
        derived["SampleCount_last"] = frame[counter_column].to_numpy()[last]
        # SampleCount itself remains the first original counter, never an average.
    for index, column in enumerate(channels, 1):
        values = pd.to_numeric(frame[column], errors="coerce").to_numpy(dtype=float, na_value=np.nan)
        finite = pd.Series(np.where(np.isfinite(values), values, np.nan))
        stats = finite.groupby(group_ids, sort=False).agg(["mean", "min", "max", "count"])
        derived[column] = stats["mean"].to_numpy()
        for statistic in ("min", "max", "count"):
            derived[f"{column}_{statistic}"] = stats[statistic].to_numpy()
        if progress:
            progress("aggregating_chainage", index, len(channels), "channels")
    for kind, prefix in (("stagger", "stg"), ("height", "height"), ("wear", "wear")):
        selected = [name for name in channels if name.startswith(kind)]
        if selected:
            derived[f"{prefix}_min"] = derived[selected].min(axis=1)
            derived[f"{prefix}_max"] = derived[selected].max(axis=1)
    return derived, {
        "aggregation": "chainage_mean", "aggregation_version": "exact_chainage_channel_mean_v1", "raw_points": size,
        "grouped_points": len(derived), "grouping_columns": list(keys.columns[:-2]),
        "pass_rule": "finite sample counter decrease", "sample_counter_column": counter_column,
        "source_row_unit": "source row number or one-based retained row",
    }
