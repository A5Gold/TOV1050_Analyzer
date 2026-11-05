"""Validate the approved raw detector/export contract on supplied files.

All reports and the database are isolated under outputs/. Source files are read
only. The application's exporter is exercised unchanged, not a test writer.
"""
from pathlib import Path
import os
import sys
import json
import gc
import hashlib
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/validation-2026-11-03/raw-integration"
OUT.mkdir(parents=True, exist_ok=True)
os.environ["DB_PATH"] = str(OUT / "isolated.db")
sys.path.insert(0, str(ROOT / "backend"))
from app.api.endpoints import analysis as api
from app.core.tov1050_report_export import export_analysis_report
from app.core.history_report_reader import iter_chart_rows
from app.core.report_context import load_report_preflight, metadata_values


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


records = []
for date in ("20260907", "20260630"):
    path = ROOT / "00 Reference Document/Raw data/TWL" / f"{date}_TWL_UT.csv"
    fingerprint = sha(path)
    tick = time.perf_counter()
    print(f"START {date}", flush=True)
    request = api.AnalyzeRequest(file_path=str(path), line="TWL", section="Mainline", track="UT",
        date_str=date, station_start="CEN", station_end="TSW", client_session_id=f"raw-{date}")
    response = api._analyze_sync(request)
    state = api.ANALYSIS_SESSIONS[request.client_session_id]
    analysis_seconds = time.perf_counter() - tick
    frame = api._export_frame(state)
    assert len(frame) == response["aggregation_metadata"]["detection_points"]
    assert len(frame) > len(state["analysis_df"])
    report = OUT / f"{date}_TWL_UT_MAINLINE_CEN_TSW_Exception_Report.xlsx"
    export_analysis_report(state["results"], chart_df=frame, line="TWL", output_path=report,
        metadata={**state["aggregation_metadata"], **state["params"]})
    expected_rows = len(frame)
    del frame
    book = load_report_preflight(report)
    try:
        metadata = metadata_values(book)
        assert metadata["detection_algorithm"] == "cleaned_raw_signed_stagger_v1"
        summary = iter(book["Summary"].values)
        headers = next(summary)
        assert all(column in headers for column in ("Overlap", "Tension Length", "Landmark"))
        summary_count = sum(1 for _ in summary)
        assert summary_count == sum(len(value) for value in state["results"].values())
    finally:
        book.close()
    chart_count = sum(1 for _ in iter_chart_rows(report, {"chainage"}))
    assert chart_count == expected_rows, (chart_count, expected_rows)
    assert sha(path) == fingerprint
    record = {"source": str(path), "source_sha256": fingerprint, "source_unchanged": True,
        "report": str(report), "report_sha256": sha(report), "chart_rows": chart_count,
        "summary_rows": summary_count, "counts": {k: len(v) for k, v in state["results"].items()},
        "analysis_seconds": analysis_seconds, "total_seconds": time.perf_counter() - tick,
        "provenance": response["aggregation_metadata"]}
    records.append(record)
    (OUT / "validation.json").write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"END {date}: {record['counts']}, ChartData={chart_count}, {record['total_seconds']:.1f}s", flush=True)
    api._release_chart_cache(state)
    api.ANALYSIS_SESSIONS.clear()
    api.LAST_ANALYSIS_SNAPSHOT = None
    api.LAST_ANALYSIS_RESULTS = {}
    del state, response
    gc.collect()
