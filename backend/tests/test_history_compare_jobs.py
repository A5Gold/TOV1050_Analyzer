import io
import time
from pathlib import Path

from fastapi.testclient import TestClient
from openpyxl import Workbook, load_workbook
import pytest

from app.main import app
from app.api.endpoints import analysis
from app.core.background_jobs import JobManager
from app.core.history_report_reader import read_history_report, read_chart_window


def workbook(*, identifier="x", height=3800, chart_rows=1, auxiliary=True, algorithm="median_v1"):
    book = Workbook(write_only=True)
    columns = ["ID", "Exception Type", "MaxValue", "MaxLocation", "FromM", "ToM", "Length",
               "Level", "Line", "Track", "Section"]
    values = [identifier, "Low Height", height, 100., 99., 101., 2., "L2", "TWL", "UT", "MAINLINE"]
    for title in ("Summary", "Low Height"):
        sheet = book.create_sheet(title)
        sheet.append(columns)
        sheet.append(values)
    if auxiliary:
        for title in ("MetadataEvidence", "MetadataBoundaryReview", "ExceptionProvenance"):
            sheet = book.create_sheet(title)
            sheet.append(columns)
            sheet.append(["fake", "High Height", 9000, 100, 99, 101, 2, "L1", "TWL", "UT", "MAINLINE"])
    chart = book.create_sheet("ChartData")
    chart.append(["Chainage", "height1", "line", "track", "Section"])
    for index in range(chart_rows):
        chart.append([float(index), height + index % 13, "TWL", "UT", "MAINLINE"])
    meta = book.create_sheet("_Metadata")
    meta.append(["key", "value"])
    meta.append(["algorithm", algorithm])
    meta.append(["chart_data_mode", "chainage_median"])
    output = io.BytesIO()
    book.save(output)
    return output.getvalue()


@pytest.fixture
def jobs(monkeypatch, tmp_path):
    manager = JobManager(tmp_path / "jobs")
    monkeypatch.setattr(analysis, "JOBS", manager)
    yield manager
    manager.close()


def submit(client, first, second, session="a"):
    return client.post("/api/analyze/compare/jobs", params={"client_session_id": session}, files=[
        ("files", ("20260907_TWL_UT_MAINLINE_CEN_TSW_Exception_Report.xlsx", first)),
        ("files", ("20260630_TWL_UT_MAINLINE_CEN_TSW_Exception_Report.xlsx", second)),
    ])


def ready(client, job_id, session="a"):
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        response = client.get(f"/api/jobs/{job_id}", params={"client_session_id": session})
        assert response.status_code == 200, response.text
        state = response.json()
        if state["status"] in {"ready", "failed", "cancelled"}:
            return state
        time.sleep(.01)
    pytest.fail("comparison job did not complete")


def test_background_compare_excludes_auxiliary_and_keeps_result_small(jobs):
    with TestClient(app) as client:
        response = submit(client, workbook(chart_rows=6000), workbook(chart_rows=6000))
        assert response.status_code == 202, response.text
        job_id = response.json()["job_id"]
        assert ready(client, job_id)["status"] == "ready"
        result = client.get(f"/api/jobs/{job_id}/result", params={"client_session_id": "a"}).json()
        assert result["stats"]["total"] == 1
        assert set(result["repeated"]) == {"Low Height"}
        assert result["chart_data"] == [None, None]
        assert result["metadata"]["line"] == "TWL"
        assert len(str(result)) < 10000
        chart = client.get(f"/api/analyze/compare/jobs/{job_id}/chart",
                           params={"client_session_id": "a", "cycle": 0, "from_m": 90, "to_m": 110})
        assert chart.status_code == 200, chart.text
        assert chart.json()["chart_data"]["Chainage"] == list(range(90, 111))
        assert len(client.get(f"/api/analyze/compare/jobs/{job_id}/chart",
                              params={"client_session_id": "a"}).json()["chart_data"]["Chainage"]) <= 5000
        assert client.get(f"/api/jobs/{job_id}/result", params={"client_session_id": "b"}).status_code == 404
        assert client.get(f"/api/analyze/compare/jobs/{job_id}/chart",
                          params={"client_session_id": "b"}).status_code == 404


def test_interleaved_session_export_uses_own_job(jobs):
    with TestClient(app) as client:
        first = submit(client, workbook(identifier="a", height=3800), workbook(), "a").json()["job_id"]
        assert ready(client, first, "a")["status"] == "ready"
        second = submit(client, workbook(identifier="b", height=3900), workbook(), "b").json()["job_id"]
        assert ready(client, second, "b")["status"] == "ready"
        for session, job_id, value in (("a", first, 3800), ("b", second, 3900)):
            response = client.get("/api/export/compare", params={"job_id": job_id, "client_session_id": session})
            assert response.status_code == 200, response.text
            book = load_workbook(io.BytesIO(response.content), read_only=True, data_only=True)
            try:
                rows = list(book.active.values)
                assert any(value in row for row in rows[1:])
            finally:
                book.close()


def test_expiry_cleans_source_and_numeric_cache(jobs):
    with TestClient(app) as client:
        job_id = submit(client, workbook(), workbook()).json()["job_id"]
        assert ready(client, job_id)["status"] == "ready"
        artifacts = list(jobs.get(job_id, "a").artifacts)
        assert len(artifacts) == 4 and all(path.exists() for path in artifacts)
        jobs.ttl_seconds = 0
        jobs.cleanup()
        assert not any(path.exists() for path in artifacts)
        assert client.get(f"/api/jobs/{job_id}", params={"client_session_id": "a"}).status_code == 410


def test_numeric_cache_window_matches_xml_and_keeps_extrema(tmp_path):
    path = tmp_path / "report.xlsx"
    path.write_bytes(workbook(chart_rows=12000))
    read_history_report(path, path.name, cache_chart=True)
    cached, resolution = read_chart_window(path, 0, 12000, max_points=100)
    assert resolution["returned_points"] <= 100
    assert cached["Chainage"][0] == 0 and cached["Chainage"][-1] == 11999
    assert min(cached["height1"]) == 3800 and max(cached["height1"]) == 3812
    path.with_suffix(".chart.bin").unlink()
    xml, _ = read_chart_window(path, 0, 12000, max_points=100)
    assert cached == xml


def test_failed_scope_validation_has_actionable_error_and_cleans_artifacts(jobs):
    book = load_workbook(io.BytesIO(workbook()))
    book["ChartData"].append([1., 3800., "AEL", "UT", "MAINLINE"])
    changed = io.BytesIO()
    book.save(changed)
    with TestClient(app) as client:
        job_id = submit(client, changed.getvalue(), workbook()).json()["job_id"]
        state = ready(client, job_id)
        assert state["status"] == "failed"
        assert state["error_code"] == "INCOMPATIBLE_REPORT_SCOPE"
        assert "incompatible line" in state["error"]
        assert not any(path.exists() for path in jobs.get(job_id, "a").artifacts)


def test_individual_exception_sheet_scope_is_checked_without_summary_or_chart(tmp_path):
    from app.core.report_context import ReportContextError
    book = Workbook()
    sheet = book.active
    sheet.title = "Low Height"
    sheet.append(["ID", "Exception Type", "MaxValue", "MaxLocation", "FromM", "ToM", "Line", "Track", "Section"])
    sheet.append(["a", "Low Height", 3500, 100, 99, 101, "TWL", "UT", "Mainline"])
    sheet.append(["b", "Low Height", 3500, 100, 99, 101, "ISL", "UT", "Mainline"])
    path = tmp_path / "mixed.xlsx"
    book.save(path)
    with pytest.raises(ReportContextError, match="incompatible line"):
        read_history_report(path, path.name)


def test_incompatible_algorithm_rejected_before_decoding_large_chart(jobs, monkeypatch):
    import app.core.history_report_reader as reader
    monkeypatch.setattr(reader, "iter_chart_rows", lambda *args: pytest.fail("ChartData must not be read"))
    with TestClient(app) as client:
        response = submit(client, workbook(algorithm="raw_v1"), workbook(algorithm="median_v1"))
        state = ready(client, response.json()["job_id"])
        assert state["status"] == "failed"
        assert state["error_code"] == "INCOMPATIBLE_REPORT_ALGORITHM"


def test_chart_envelope_preserves_internal_missing_measurements(tmp_path):
    path = tmp_path / "gaps.xlsx"
    book = Workbook()
    sheet = book.active
    sheet.title = "ChartData"
    sheet.append(["Chainage", "height1"])
    for index in range(201):
        sheet.append([index, None if index == 5 else float(index)])
    book.save(path)
    chart, resolution = read_chart_window(path, 0, 200, max_points=100)
    assert resolution["returned_points"] <= 100
    assert None in chart["height1"]
    assert min(value for value in chart["height1"] if value is not None) == 0
    assert max(value for value in chart["height1"] if value is not None) == 200
