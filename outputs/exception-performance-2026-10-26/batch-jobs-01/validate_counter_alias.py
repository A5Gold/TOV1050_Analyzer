"""Supplement the running batch without editing its script or event log.

Default: read only the CSV counter column, apply the loader's first/last-100
trim, and count resets. --verify-retained additionally loads/aggregates each
complete cleaned frame after the HTTP benchmark, with no XLSX generation.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))
from app.core.chainage_aggregation import aggregate_chainage, SAMPLE_COUNTER_COLUMNS
from app.core.tov1050_data_ingestion import TOV1050DataLoader


def describe(counters):
    values = pd.to_numeric(counters, errors="coerce").replace([np.inf, -np.inf], np.nan)
    resets = values.ffill().diff().lt(0)
    indices = np.flatnonzero(resets.to_numpy())
    return {"rows": len(values), "finite_counters": int(np.isfinite(values).sum()),
            "decreases": len(indices), "decrease_positions_zero_based": indices[:100].tolist(),
            "first_counter": None if values.empty else values.iloc[0],
            "last_counter": None if values.empty else values.iloc[-1]}


def retained_oracle(raw, derived):
    column = next(name for name in SAMPLE_COUNTER_COLUMNS if name in raw)
    counter = pd.to_numeric(raw[column], errors="coerce").replace([np.inf, -np.inf], np.nan)
    passes = counter.ffill().diff().lt(0).cumsum().to_numpy()
    context = [name for name in raw if name.lower() in {
        "line", "track", "section", "session", "session_id", "task_no", "task_run_date",
        "station_start", "station_end", "class", "track type", "overlap", "tension length",
        "landmark", "source_file", "source_filename", "metadata_segment_id", "segment_id"}]
    keys = raw[["Chainage", *context]].copy().reset_index(drop=True)
    keys["_pass"] = passes
    ids = keys.groupby(list(keys), sort=False, dropna=False).ngroup().to_numpy()
    position = pd.Series(np.arange(len(raw)))
    first = position.groupby(ids, sort=False).first().to_numpy()
    last = position.groupby(ids, sort=False).last().to_numpy()
    np.testing.assert_array_equal(derived["pass_id"], passes[first])
    np.testing.assert_array_equal(derived["SampleCount_first"], raw[column].to_numpy()[first])
    np.testing.assert_array_equal(derived["SampleCount_last"], raw[column].to_numpy()[last])
    np.testing.assert_array_equal(derived["source_row_first"], raw.source_row_number.to_numpy()[first])
    np.testing.assert_array_equal(derived["source_row_last"], raw.source_row_number.to_numpy()[last])
    np.testing.assert_array_equal(derived["sample_count"], np.bincount(ids))
    for channel in [f"{kind}{i}" for kind in ("height", "stagger", "wear") for i in range(1, 5)]:
        numeric = pd.to_numeric(raw[channel], errors="coerce").replace([np.inf, -np.inf], np.nan)
        expected = numeric.groupby(ids, sort=False).agg(["mean", "min", "max", "count"])
        for statistic in ("mean", "min", "max", "count"):
            target = channel if statistic == "mean" else f"{channel}_{statistic}"
            np.testing.assert_allclose(derived[target], expected[statistic], rtol=1e-13, atol=1e-9, equal_nan=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify-retained", action="store_true")
    args = parser.parse_args()
    reports = []
    for size in ("partial", "full"):
        started = time.perf_counter()
        path = ROOT / f"00 Reference Document/Raw data/TWL/test file {size}.csv"
        header = pd.read_csv(path, nrows=0, encoding="utf-8-sig").columns
        column = next(name for name in SAMPLE_COUNTER_COLUMNS if name in header)
        counter = pd.read_csv(path, usecols=[column], dtype=str, keep_default_na=False, encoding="utf-8-sig")[column]
        leading = min(100, len(counter))
        trailing = min(100, max(len(counter) - leading, 0))
        trimmed = counter.iloc[leading:len(counter) - trailing]
        report = {"size": size, "counter_column": column, "source": str(path),
                  "raw": describe(counter), "trimmed": describe(trimmed),
                  "trimmed_leading": leading, "trimmed_trailing": trailing,
                  "counter_only_seconds": time.perf_counter() - started,
                  "interpretation": "No decreases in trim-only counters proves no reset in any further retained subset; otherwise exact retained verification is required."}
        if args.verify_retained:
            loader = TOV1050DataLoader()
            raw = loader.load_data(path)
            original = pd.util.hash_pandas_object(raw, index=True).to_numpy()
            derived, metadata = aggregate_chainage(raw)
            retained_oracle(raw, derived)
            np.testing.assert_array_equal(pd.util.hash_pandas_object(raw, index=True).to_numpy(), original)
            report["retained"] = describe(raw[column])
            report["aggregation"] = metadata
            report["retained_validation"] = "passed all channel mean/min/max/count, counter/source ranges, passes, sample counts and unchanged raw"
        reports.append(report)
        print(json.dumps(report, ensure_ascii=False, default=lambda value: value.item()), flush=True)
    destination = Path(__file__).parent / ("counter-alias-retained.json" if args.verify_retained else "counter-alias-audit.json")
    with destination.open("x", encoding="utf-8") as output:
        json.dump(reports, output, ensure_ascii=False, indent=2, default=lambda value: value.item())


if __name__ == "__main__":
    main()
