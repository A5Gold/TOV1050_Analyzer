"""Exercise History's HTTP job routes with the new median exception reports."""
from pathlib import Path
import hashlib
import json
import os
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/validation-2026-11-03/median-report-followup"
os.environ["DB_PATH"] = str(OUT / "isolated.db")
sys.path.insert(0, str(ROOT / "backend"))

from fastapi.testclient import TestClient
from app.main import app
from app.api.endpoints import analysis as api
from app.core.background_jobs import JobManager


reports = [OUT / f"{date}_TWL_UT_MAINLINE_CEN_TSW_Exception_Report.xlsx"
           for date in ("20260907", "20260630")]
before = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in reports}
manager = JobManager(OUT / "http-jobs")
original_manager = api.JOBS
api.JOBS = manager
session = "median-http-validation"
try:
    with TestClient(app) as client:
        started = time.perf_counter()
        with reports[0].open("rb") as first, reports[1].open("rb") as second:
            response = client.post("/api/analyze/compare/jobs", params={"client_session_id": session},
                files=[("files", (reports[0].name, first)), ("files", (reports[1].name, second))])
        assert response.status_code == 202, response.text
        job_id = response.json()["job_id"]
        submit_seconds = time.perf_counter() - started
        print(f"HTTP job {job_id} submitted in {submit_seconds:.3f}s", flush=True)
        status_seconds = []
        while time.perf_counter() - started < 300:
            tick = time.perf_counter()
            response = client.get(f"/api/jobs/{job_id}", params={"client_session_id": session})
            assert response.status_code == 200, response.text
            state = response.json()
            status_seconds.append(time.perf_counter() - tick)
            if state["status"] in {"ready", "failed", "cancelled"}:
                break
            time.sleep(.5)
        assert state["status"] == "ready", state
        compare_seconds = time.perf_counter() - started
        response = client.get(f"/api/jobs/{job_id}/result", params={"client_session_id": session})
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["stats"]["total"] == 15, result["stats"]
        response = client.get(f"/api/analyze/compare/jobs/{job_id}/chart",
                              params={"client_session_id": session, "cycle": 0})
        assert response.status_code == 200, response.text
        overview = response.json()["chart_resolution"]
        assert overview["returned_points"] <= 5000
        response = client.get("/api/export/compare", params={"job_id": job_id,
                                                               "client_session_id": session})
        assert response.status_code == 200, response.text
        (OUT / "median-http-repeated.xlsx").write_bytes(response.content)
    assert all(hashlib.sha256(path.read_bytes()).hexdigest() == before[str(path)] for path in reports)
    record = {"job_id": job_id, "submit_seconds": round(submit_seconds, 3),
              "compare_seconds": round(compare_seconds, 3), "status_p95_seconds": round(
                  sorted(status_seconds)[min(int(len(status_seconds) * .95), len(status_seconds) - 1)], 3),
              "stats": result["stats"], "metrics": result.get("metrics"),
              "overview_points": overview["returned_points"], "source_unchanged": True,
              "comparison_export_bytes": len(response.content)}
    (OUT / "http-validation.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"HTTP ready: {result['stats']}, {compare_seconds:.3f}s", flush=True)
finally:
    api.JOBS = original_manager
    manager.close()
