"""Generate TOV1050 median exception reports and compare their real contents.

All generated files live under outputs/. Reference CSV, reports and config are
read-only; the app's own analysis, report job and History reader are exercised.
"""
from pathlib import Path
from types import SimpleNamespace
import gc
import hashlib
import json
import os
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/validation-2026-11-03/median-report-followup"
OUT.mkdir(parents=True, exist_ok=True)
os.environ["DB_PATH"] = str(OUT / "isolated.db")
sys.path.insert(0, str(ROOT / "backend"))

from app.api.endpoints import analysis as api
from app.core.history_report_reader import iter_chart_rows, read_chart_window
from app.core.report_context import load_report_preflight, metadata_values


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


references = [ROOT / "config/DRL metadata.xlsx",
              *(ROOT / "02 Output Document/TWL" / f"{date}_TWL_UT_MAINLINE_CEN_TSW_Exception_Report.xlsx"
                for date in ("20260907", "20260630"))]
reference_sha = {str(path): sha(path) for path in references}
reports = []
records = []
for date, expected_chart, expected_exceptions in (("20260907", 83963, 289),
                                                  ("20260630", 83244, 330)):
    source = ROOT / "00 Reference Document/Raw data/TWL" / f"{date}_TWL_UT.csv"
    references.append(source)
    fingerprint = sha(source)
    reference_sha[str(source)] = fingerprint
    tick = time.perf_counter()
    print(f"START {date}", flush=True)
    request = api.AnalyzeRequest(file_path=str(source), line="TWL", section="Mainline", track="UT",
        date_str=date, station_start="CEN", station_end="TSW", client_session_id=f"median-{date}")
    response = api._analyze_sync(request)
    state = api.ANALYSIS_SESSIONS[request.client_session_id]
    analysis_seconds = time.perf_counter() - tick
    chart = api._report_chart_frame(state)
    assert chart is state["analysis_df"]
    assert len(chart) == expected_chart, (date, len(chart), expected_chart)
    assert sum(len(frame) for frame in state["results"].values()) == expected_exceptions
    report = OUT / f"{date}_TWL_UT_MAINLINE_CEN_TSW_Exception_Report.xlsx"
    job = SimpleNamespace(path=None, filename=None)
    context = SimpleNamespace(progress=lambda *args: None, output_path=lambda: report,
                              check_cancelled=lambda: None, job=job)
    api._export_job_work(state, "chainage_median")(context)
    assert job.path == report and job.filename == report.name
    book = load_report_preflight(report)
    try:
        metadata = metadata_values(book)
        summary = iter(book["Summary"].values)
        headers = next(summary)
        assert all(key in headers for key in ("Overlap", "Tension Length", "Landmark"))
        summary_rows = sum(1 for _ in summary)
    finally:
        book.close()
    chart_rows = sum(1 for _ in iter_chart_rows(report, {"chainage"}))
    assert chart_rows == expected_chart
    assert summary_rows == expected_exceptions
    assert metadata["detection_algorithm"] == "cleaned_raw_signed_stagger_v1"
    assert metadata["detection_data_mode"] == "cleaned_raw"
    assert metadata["export_data_mode"] == "chainage_median"
    assert int(metadata["chart_row_count"]) == expected_chart
    assert int(metadata["raw_row_count"]) == response["aggregation_metadata"]["detection_points"]
    assert sha(source) == fingerprint
    record = {"date": date, "source_sha256": fingerprint, "source_unchanged": True,
              "report": str(report), "report_sha256": sha(report), "report_bytes": report.stat().st_size,
              "raw_rows": int(metadata["raw_row_count"]), "chart_rows": chart_rows,
              "summary_rows": summary_rows, "counts": {key: len(frame) for key, frame in state["results"].items()},
              "analysis_seconds": round(analysis_seconds, 3),
              "analyze_export_read_seconds": round(time.perf_counter() - tick, 3)}
    records.append(record)
    reports.append(report)
    (OUT / "validation.json").write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"END {date}: ChartData={chart_rows}, Summary={summary_rows}, {record['analyze_export_read_seconds']}s", flush=True)
    api._release_chart_cache(state)
    api.ANALYSIS_SESSIONS.clear()
    api.LAST_ANALYSIS_SNAPSHOT = None
    api.LAST_ANALYSIS_RESULTS = {}
    del state, response, chart
    gc.collect()

compare_start = time.perf_counter()
comparison_job = SimpleNamespace(work={})
comparison_context = SimpleNamespace(progress=lambda *args: None, job=comparison_job)
comparison = api._compare_history_files(reports, [path.name for path in reports], comparison_context)
assert comparison["stats"]["total"] == 15, comparison["stats"]
assert [item["chart_rows"] for item in comparison["metrics"]["reports"]] == [83963, 83244]
domain = comparison["chart_domains"][0]
chart_payload, resolution = read_chart_window(comparison_job.work["history_paths"][0], *domain,
                                              max_points=5000)
assert resolution["returned_points"] <= 5000
record = {"history_compare_seconds": round(time.perf_counter() - compare_start, 3),
          "history_stats": comparison["stats"], "history_metrics": comparison["metrics"],
          "overview_points": resolution["returned_points"],
          "algorithm_provenance": comparison["algorithm_provenance"],
          "references_unchanged": all(sha(path) == reference_sha[str(path)] for path in references)}
records.append(record)
(OUT / "validation.json").write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"HISTORY: {comparison['stats']}, {record['history_compare_seconds']}s", flush=True)
