"""Post-check an existing ready History job; never starts servers or regenerates reports.

The API must already use the explicitly named isolated database under outputs/.
Only that isolated database receives a save; SQLite reopen uses mode=ro.
"""
import argparse
import io
import json
from pathlib import Path
import sqlite3
import time
import urllib.parse
import urllib.request

from openpyxl import load_workbook


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--expected-db", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/validation-2026-11-03/history-postchecks"))
    args = parser.parse_args()
    workspace = Path(__file__).resolve().parents[1]
    expected = args.expected_db.resolve(strict=True)
    if not expected.is_relative_to(workspace / "outputs"):
        raise ValueError("Postchecks require an isolated DB inside this workspace's outputs directory")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    request_timings = []

    def request(route, params=None, body=None, binary=False):
        started = time.perf_counter()
        url = args.base_url.rstrip("/") + "/api" + route
        if params:
            url += "?" + urllib.parse.urlencode(params, doseq=True)
        data = None if body is None else json.dumps(body, ensure_ascii=False).encode()
        req = urllib.request.Request(url, data=data,
                                     headers={"Content-Type": "application/json"} if data else {})
        with urllib.request.urlopen(req, timeout=60) as response:
            raw = response.read()
        request_timings.append({"route": route, "seconds": round(time.perf_counter() - started, 3)})
        return raw if binary else json.loads(raw)

    diagnostic = request("/diagnostics")
    if Path(diagnostic["database_path"]).resolve(strict=True) != expected:
        raise ValueError("Active API database differs from --expected-db; no save was attempted")
    identity = {"client_session_id": args.session_id}
    state = request(f"/jobs/{args.job_id}", identity)
    if state["status"] != "ready" or state["kind"] != "history_compare":
        raise ValueError(f"Existing History job must be ready: {state}")
    result = request(f"/jobs/{args.job_id}/result", identity)
    rows = [row for group in result["repeated"].values() for row in group]
    if not rows:
        raise ValueError("No repeated exceptions available for detail/export/save validation")
    first = rows[0]
    lower, upper = float(first["FromM"]) - 5, float(first["ToM"]) + 5
    overviews = []
    details = []
    for cycle in range(len(result["chain_order"])):
        prefix = f"Previous {cycle}_" if cycle else ""
        preserve = [first[prefix + key] for key in ("FromM", "ToM", "maxLocation") if prefix + key in first]
        overview = request(f"/analyze/compare/jobs/{args.job_id}/chart", {
            **identity, "cycle": cycle, "max_points": 5000, "preserve_m": preserve,
        })
        assert overview["chart_data"] and overview["chart_data"]["Chainage"]
        assert len(overview["chart_data"]["Chainage"]) <= 5000
        overviews.append(overview["chart_resolution"])
        detail = request(f"/analyze/compare/jobs/{args.job_id}/chart", {
            **identity, "cycle": cycle, "from_m": lower, "to_m": upper,
            "max_points": 5000, "preserve_m": preserve,
        })
        signals = detail["chart_data"]
        if signals is None or not signals["Chainage"]:
            raise AssertionError(f"Cycle {cycle}: expected nonempty detail data")
        assert len(signals["Chainage"]) <= 5000
        assert all(lower <= value <= upper for value in signals["Chainage"])
        assert all(len(values) == len(signals["Chainage"]) for values in signals.values())
        peak = float(first[prefix + "maxLocation"])
        if lower <= peak <= upper:
            assert min(abs(value - peak) for value in signals["Chainage"]) <= .001
        details.append(detail["chart_resolution"])
    export = request("/export/compare", {**identity, "job_id": args.job_id}, binary=True)
    export_path = args.output_dir / "comparison.xlsx"
    export_path.write_bytes(export)
    book = load_workbook(io.BytesIO(export), read_only=True, data_only=True)
    try:
        cells = {str(value) for sheet in book for row in sheet.values for value in row if value is not None}
        assert {str(row["id"]) for row in rows} <= cells
    finally:
        book.close()
    metadata = result["metadata"]
    payload = {key: metadata.get(key) for key in (
        "line", "track", "session", "date_str", "task_no", "station_start", "station_end")}
    payload.update(repeated_exceptions=rows, latest_file_name=result["chain_order"][0],
                   comparison_files=result["chain_order"], task_run_date=metadata["date_str"])
    saved = request("/database/repeated-records", body=payload)
    queried = request("/database/repeated-records", {
        "line": metadata["line"], "track": metadata["track"],
        "session": metadata["session"], "limit": 5000})
    ids = {str(row["id"]) for row in rows}
    assert ids <= {str(row["exception_id"]) for row in queried["records"]}
    # A fresh read-only connection verifies committed rows without closing or
    # restarting the live backend/Electron process or its SQLite connection.
    with sqlite3.connect(expected.as_uri() + "?mode=ro", uri=True) as reopened:
        reopened.row_factory = sqlite3.Row
        for source in rows:
            matches = reopened.execute(
                "SELECT * FROM saved_repeated_exceptions WHERE exception_id=? AND line=?",
                (source["id"], metadata["line"])).fetchall()
            assert len(matches) == 1
            record = matches[0]
            for target, field in (("from_m", "FromM"), ("to_m", "ToM"),
                                  ("max_value", "maxValue"), ("max_location", "maxLocation")):
                assert abs(float(record[target]) - float(source[field])) <= 1e-9
    evidence = {"status": "passed", "job_id": args.job_id,
                "database_path": str(expected), "repeated_rows": len(rows),
                "overviews": overviews, "details": details, "export_bytes": len(export), "save": saved,
                "api_query_total": queried["total"], "read_only_sqlite_reopen": True,
                "cached_request_timings": request_timings}
    (args.output_dir / "validation.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False))


if __name__ == "__main__":
    main()
