"""Benchmark the TOV1050 loader, full-fidelity detector, and chart payload.

The generated CSV is temporary and is deleted after the run.  The benchmark
does not write any runtime metadata or alter source workbooks.
"""

from __future__ import annotations

import csv
import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.analyzers import ExceptionDetector
from app.core.chart_sampling import build_chart_payload
from app.core.tov1050_data_ingestion import TOV1050DataLoader


ROWS = 900_000
HEADERS = [
    "Line", "Km", "HeightWire1 [mm]", "HeightWire2 [mm]", "HeightWire3 [mm]", "HeightWire4 [mm]",
    "StaggerWire1 [mm]", "StaggerWire2 [mm]", "StaggerWire3 [mm]", "StaggerWire4 [mm]",
    "WearWire1 [mm]", "WearWire2 [mm]", "WearWire3 [mm]", "WearWire4 [mm]",
]


class _BenchmarkMetadata:
    def get_exception_boundaries(self, *_args):
        return pd.DataFrame({"Class": ["Open"]}, index=pd.IntervalIndex.from_tuples([(0.0, 1_000_000.0)]))

    def get_track_type_intervals(self, *_args):
        return pd.DataFrame({"Track Type": ["Tangent"]}, index=pd.IntervalIndex.from_tuples([(0.0, 1_000_000.0)]))

    def get_boundaries_for_plot(self, *_args):
        return pd.DataFrame({"Class": ["Open"], "FromM": [0.0], "ToM": [1_000_000.0]})

    def get_overlap_intervals(self, *_args):
        return pd.DataFrame()

    def get_landmark_intervals(self, *_args):
        return pd.DataFrame()

    def get_all_thresholds(self):
        return pd.DataFrame([
            {"Class": "Open", "Track Type": "Tangent", "Exc Type": "Low Height", "Low Height L1": 4500, "Low Height L2": 4600},
            {"Class": "Open", "Track Type": "Tangent", "Exc Type": "High Height", "High Height L1": 6000, "High Height L2": 5900},
            {"Class": "Open", "Track Type": "Tangent", "Exc Type": "Wire Wear", "Wire Wear L1": 50, "Wire Wear L2": 75},
            {"Class": "Open", "Track Type": "Tangent", "Exc Type": "Stagger Left", "Stagger L1": 300, "Stagger L2": 250, "Stagger L3": 200},
            {"Class": "Open", "Track Type": "Tangent", "Exc Type": "Stagger Right", "Stagger L1": 300, "Stagger L2": 250, "Stagger L3": 200},
        ])


def _rss_bytes() -> int | None:
    try:
        import psutil
        return int(psutil.Process(os.getpid()).memory_info().rss)
    except ImportError:
        if os.name != "nt":
            return None
        import ctypes
        class Counters(ctypes.Structure):
            _fields_ = [("cb", ctypes.c_ulong), ("page_fault_count", ctypes.c_size_t),
                        ("peak_working_set", ctypes.c_size_t), ("working_set", ctypes.c_size_t),
                        ("quota_peak_paged", ctypes.c_size_t), ("quota_paged", ctypes.c_size_t),
                        ("quota_peak_nonpaged", ctypes.c_size_t), ("quota_nonpaged", ctypes.c_size_t),
                        ("pagefile", ctypes.c_size_t), ("peak_pagefile", ctypes.c_size_t)]
        counters = Counters()
        counters.cb = ctypes.sizeof(Counters)
        handle = ctypes.windll.kernel32.GetCurrentProcess()
        psapi = ctypes.WinDLL("psapi")
        psapi.GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.POINTER(Counters), ctypes.c_ulong]
        psapi.GetProcessMemoryInfo.restype = ctypes.c_int
        if psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
            return int(counters.peak_working_set)
        return None


def _write_csv(path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(HEADERS)
        for index in range(ROWS):
            km = 1.0 + index / 1000.0
            writer.writerow(["ISL", f"{km:.3f}", 5000, 5001, 4999, 5000, 0, 0, 0, 0, 100, 100, 100, 100])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="tov1050-benchmark-") as directory:
        path = Path(directory) / "20260902_ISL_UT_SHO_AWE.csv"
        generation_start = time.perf_counter()
        _write_csv(path)
        generation_seconds = time.perf_counter() - generation_start

        loader = TOV1050DataLoader(chunk_size=50_000)
        load_start = time.perf_counter()
        frame = loader.load_data(path)
        load_seconds = time.perf_counter() - load_start

        detector = ExceptionDetector(_BenchmarkMetadata())
        detect_start = time.perf_counter()
        results, boundaries = detector.analyze(frame, "ISL", "Mainline", "UT", "20260902")
        detect_seconds = time.perf_counter() - detect_start

        chart_start = time.perf_counter()
        payload, chart_meta = build_chart_payload(
            frame,
            ["Chainage", "height1", "height2", "stagger1", "wear1"],
            max_points=6000,
        )
        chart_seconds = time.perf_counter() - chart_start
        payload_bytes = len(json.dumps(payload, separators=(",", ":")).encode("utf-8"))

        exception_rows = sum(len(value) for value in results.values() if isinstance(value, pd.DataFrame))
        peak_rss = _rss_bytes()

        report = {
            "rows_generated": ROWS,
            "rows_retained": len(frame),
            "generation_seconds": round(generation_seconds, 3),
            "load_seconds": round(load_seconds, 3),
            "load_rows_per_second": round(len(frame) / load_seconds, 1),
            "detect_seconds": round(detect_seconds, 3),
            "detect_rows_per_second": round(len(frame) / detect_seconds, 1),
            "chart_seconds": round(chart_seconds, 3),
            "chart_metadata": chart_meta,
            "chart_payload_bytes": payload_bytes,
            "exception_rows": exception_rows,
            "boundary_rows": len(boundaries),
            "cleaning_summary": loader.last_cleaning_summary,
            "peak_rss_bytes": peak_rss,
            "detector_input_rows": len(frame),
            "raw_detector_parity": exception_rows == 0 and len(frame) == loader.last_cleaning_summary["retained_row_count"],
        }
        serialized = json.dumps(report, indent=2)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(serialized + "\n", encoding="utf-8")
        print(serialized)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
