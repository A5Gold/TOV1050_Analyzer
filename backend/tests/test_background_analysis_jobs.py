from pathlib import Path
from threading import Event
from unittest.mock import Mock
import asyncio

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.endpoints import analysis as api
from app.core.background_jobs import JobManager, JobCancelled, JobCapacityError, JobExpired


@pytest.fixture
def manager(tmp_path, monkeypatch):
    service = JobManager(tmp_path / "jobs")
    monkeypatch.setattr(api, "JOBS", service)
    yield service
    service.close()


def test_single_worker_queue_and_cooperative_cancel(manager):
    entered, release = Event(), Event()

    def busy(context):
        entered.set()
        assert release.wait(3)
        context.check_cancelled()
        return {"analysis_revision": "one"}

    one = manager.submit("analysis", "a", lambda: busy)
    assert entered.wait(2)
    two = manager.submit("analysis", "b", lambda: lambda ctx: {"analysis_revision": "two"})
    with pytest.raises(JobCapacityError):
        manager.submit("analysis", "c", lambda: pytest.fail("must reject before capture"))
    assert manager.cancel_job(two["job_id"], "b")["status"] == "cancelled"
    manager.submit("analysis", "c", lambda: lambda ctx: {"analysis_revision": "three"})
    assert manager.cancel_job(one["job_id"], "a")["status"] == "cancelling"
    with pytest.raises(JobCapacityError):
        manager.submit("analysis", "d", lambda: None)
    release.set()
    manager.jobs[one["job_id"]].future.result(timeout=3)
    assert manager.get(one["job_id"], "a").status == "cancelled"


def test_api_status_responsive_and_session_scoped(manager, monkeypatch):
    entered, release = Event(), Event()

    def analyze(request, progress, publish):
        progress("reading", 10, 100, "rows")
        entered.set()
        assert release.wait(3)
        return publish(lambda: {"analysis_revision": "revision-a", "status": "success"})

    monkeypatch.setattr(api, "_analyze_sync", analyze)
    with TestClient(app) as client:
        response = client.post("/api/analysis/jobs", json={
            "file_path": "test.csv", "line": "TWL", "track": "UT", "section": "Mainline",
            "date_str": "20260907", "client_session_id": "a",
        })
        assert response.status_code == 202
        job_id = response.json()["job_id"]
        assert entered.wait(2)
        try:
            status = client.get(f"/api/jobs/{job_id}", params={"client_session_id": "a"})
            assert status.status_code == 200
            assert status.json()["stage_percent"] == 10
            assert client.get(f"/api/jobs/{job_id}", params={"client_session_id": "b"}).status_code == 404
            assert client.get(f"/api/jobs/{job_id}/result", params={"client_session_id": "a"}).status_code == 409
            assert client.get(f"/api/jobs/{job_id}/download", params={"client_session_id": "a"}).status_code == 409
        finally:
            release.set()
        manager.jobs[job_id].future.result(timeout=3)
        assert client.get(f"/api/jobs/{job_id}/result", params={"client_session_id": "a"}).json()["analysis_revision"] == "revision-a"


def test_export_pins_revision_and_download_lease(manager, monkeypatch):
    frame = pd.DataFrame({"Chainage": [12.5, 12.5], "height1": [1., 3.]})
    entered, release = Event(), Event()
    blocker = manager.submit("analysis", "block", lambda: lambda ctx: (
        entered.set(), release.wait(3), {"analysis_revision": "block"})[-1])
    assert entered.wait(2)
    state = {"analysis_revision": "old", "raw_df": frame, "results": {"Low Height": []},
             "params": {"line": "TWL", "track": "UT", "section": "Mainline", "session": "Mainline",
                        "date_str": "20260907", "station_start": "CEN", "station_end": "TSW"}}
    monkeypatch.setattr(api, "ANALYSIS_SESSIONS", {"a": state})
    observed = []

    def writer(results, chart_df, output_path, progress, **kwargs):
        observed.append((chart_df, results))
        progress("finalizing")
        Path(output_path).write_bytes(b"report")
        return output_path

    monkeypatch.setattr(api, "export_analysis_report", writer)
    with TestClient(app) as client:
        body = {"client_session_id": "a", "analysis_revision": "wrong", "chart_data_mode": "raw"}
        assert client.post("/api/export/report/jobs", json=body).status_code == 409
        body["analysis_revision"] = "old"
        response = client.post("/api/export/report/jobs", json=body)
        assert response.status_code == 202
        job_id = response.json()["job_id"]
        api.ANALYSIS_SESSIONS["a"] = dict(state, analysis_revision="new", raw_df=frame * 10)
        release.set()
        manager.jobs[job_id].future.result(timeout=3)
        assert observed[0][0] is frame
        assert client.get(f"/api/jobs/{job_id}/download", params={"client_session_id": "b"}).status_code == 404
        download = client.get(f"/api/jobs/{job_id}/download", params={"client_session_id": "a"})
        assert download.content == b"report"
        assert manager.jobs[job_id].downloads == 0
        job = manager.acquire_download(job_id, "a")
        manager.ttl_seconds = 0
        manager.cleanup()
        assert job.path.exists()
        manager.release_download(job)
        assert not job.path.exists()
        with pytest.raises(JobExpired):
            manager.get(job_id, "a")


def test_missing_raw_never_uses_overview_or_another_session(manager, monkeypatch):
    monkeypatch.setattr(api, "ANALYSIS_SESSIONS", {})
    monkeypatch.setattr(api, "LAST_RAW_DF", pd.DataFrame({"Chainage": [99]}))
    with TestClient(app) as client:
        assert client.post("/api/export/report/jobs", json={
            "client_session_id": "missing", "analysis_revision": "x"}).status_code == 410
        assert client.post("/api/export/report/generate", json={
            "client_session_id": "missing", "exceptions": {}, "params": {},
            "chart_data": {"Chainage": [1]}}).status_code == 410
        assert client.get("/api/analyze/chart-data", params={
            "client_session_id": "missing", "analysis_revision": "x"}).status_code == 410
        assert client.post("/api/export/raw/generate", json={
            "client_session_id": "missing", "params": {},
            "chart_data": {"Chainage": [1]}}).status_code == 410


def test_failure_releases_capacity_and_removes_incomplete_file(manager):
    def fail(context):
        context.output_path().write_bytes(b"incomplete")
        raise ValueError("writer failed")
    created = manager.submit("export", "a", lambda: fail, "revision")
    job = manager.jobs[created["job_id"]]
    job.future.result(timeout=3)
    assert job.status == "failed" and job.error == "writer failed"
    assert not (manager.directory / f"{job.job_id}.xlsx").exists()
    next_job = manager.submit("analysis", "a", lambda: lambda ctx: {"analysis_revision": "ok"})
    manager.jobs[next_job["job_id"]].future.result(timeout=3)
    assert manager.get(next_job["job_id"], "a").status == "ready"


@pytest.mark.parametrize("cancelled", [False, True])
def test_locked_incomplete_artifact_retries_without_retaining_capacity(manager, monkeypatch, cancelled):
    original_unlink = Path.unlink
    locked = set()
    def unlink(path, *args, **kwargs):
        if path in locked:
            raise PermissionError("file is locked")
        return original_unlink(path, *args, **kwargs)
    monkeypatch.setattr(Path, "unlink", unlink)
    def fail(context):
        path = context.output_path()
        path.write_bytes(b"incomplete")
        locked.add(path)
        raise JobCancelled() if cancelled else ValueError("writer failed")
    created = manager.submit("export", "a", lambda: fail)
    job = manager.jobs[created["job_id"]]
    job.future.result(timeout=3)
    path = manager.directory / f"{job.job_id}.xlsx"
    assert job.status == ("cancelled" if cancelled else "failed")
    assert job.finished_at is not None
    assert path in manager.pending_deletions and path.exists()
    assert manager.get(job.job_id, "a") is job
    entered, release = Event(), Event()
    def busy(context):
        entered.set()
        assert release.wait(3)
        return {"analysis_revision": "next"}
    try:
        next_job = manager.submit("analysis", "b", lambda: busy)
        assert entered.wait(2)
        queued = manager.submit("analysis", "c", lambda: lambda ctx: {"analysis_revision": "queued"})
        manager.cancel_job(queued["job_id"], "c")
    finally:
        release.set()
    manager.jobs[next_job["job_id"]].future.result(timeout=3)
    locked.clear()
    manager.cleanup()
    assert not path.exists() and path not in manager.pending_deletions


def test_expired_locked_report_retries_after_download_release(manager, monkeypatch):
    def export(context):
        context.output_path().write_bytes(b"report")
        context.job.path = context.output_path()
        return None
    created = manager.submit("export", "a", lambda: export)
    job = manager.jobs[created["job_id"]]
    job.future.result(timeout=3)
    manager.acquire_download(job.job_id, "a")
    original_unlink = Path.unlink
    locked = {job.path}
    def unlink(path, *args, **kwargs):
        if path in locked:
            raise PermissionError("report is locked")
        return original_unlink(path, *args, **kwargs)
    monkeypatch.setattr(Path, "unlink", unlink)
    manager.ttl_seconds = 0
    manager.cleanup()
    assert job.job_id in manager.jobs and not manager.pending_deletions
    manager.release_download(job)
    assert job.path.exists() and job.path in manager.pending_deletions
    with pytest.raises(JobExpired):
        manager.get(job.job_id, "a")
    locked.clear()
    manager.cleanup()
    assert not job.path.exists() and not manager.pending_deletions


def test_app_lifespan_cancels_running_and_queued_jobs(manager):
    entered, stopped = Event(), Event()
    def running(context):
        entered.set()
        assert context.job.cancel.wait(3)
        stopped.set()
        context.check_cancelled()
    with TestClient(app) as client:
        assert client.get("/api/health").status_code == 200
        first = manager.submit("analysis", "a", lambda: running)
        assert entered.wait(2)
        second = manager.submit("analysis", "b", lambda: lambda ctx: pytest.fail("queued work must not run"))
        first_job, second_job = manager.jobs[first["job_id"]], manager.jobs[second["job_id"]]
    assert manager.closed and stopped.is_set()
    assert first_job.status == second_job.status == "cancelled"
    assert not manager.jobs and not manager.directory.exists()


def test_app_lifespan_can_restart_closed_manager(manager):
    manager.ttl_seconds = 123
    manager.execution_timeout_seconds = 456
    with TestClient(app):
        assert api.JOBS is manager
    with TestClient(app) as client:
        restarted = api.JOBS
        assert restarted is not manager and not restarted.closed
        assert restarted.ttl_seconds == 123
        assert restarted.execution_timeout_seconds == 456
        assert client.get("/api/health").status_code == 200
    assert restarted.closed and not restarted.directory.exists()


@pytest.mark.parametrize("error", [ValueError("chart failed"), JobCancelled()])
def test_analysis_failure_or_cancel_preserves_previous_success(monkeypatch, error):
    previous = {"analysis_revision": "previous", "raw_df": pd.DataFrame({"Chainage": [99.]})}
    monkeypatch.setattr(api, "ANALYSIS_SESSIONS", {"a": previous})
    monkeypatch.setattr(api, "LAST_RAW_DF", previous["raw_df"])
    monkeypatch.setattr(Path, "exists", lambda _: True)
    loader = Mock()
    loader.load_data.return_value = pd.DataFrame({"Chainage": [1.], "height1": [2.]})
    monkeypatch.setattr(api, "DataLoader", lambda: loader)
    monkeypatch.setattr(api, "MetadataManager", Mock())
    detector = Mock()
    detector.analyze.return_value = ({}, pd.DataFrame())
    monkeypatch.setattr(api, "ExceptionDetector", lambda _: detector)
    monkeypatch.setattr(api, "build_chart_payload", Mock(side_effect=error))
    request = api.AnalyzeRequest(file_path="dummy.datac", line="EAL", section="Mainline",
                                 track="UP", date_str="20260907", client_session_id="a", chart_data_mode="raw")
    with pytest.raises((api.HTTPException, JobCancelled)):
        api._analyze_sync(request)
    assert api.ANALYSIS_SESSIONS["a"] is previous
    assert api.LAST_RAW_DF is previous["raw_df"]


def test_detail_requires_current_revision(manager, monkeypatch):
    monkeypatch.setattr(api, "ANALYSIS_SESSIONS", {"a": {
        "analysis_revision": "current", "raw_df": pd.DataFrame({"Chainage": [1.]})}})
    with TestClient(app) as client:
        for revision in (None, "old"):
            params = {"client_session_id": "a"}
            if revision:
                params["analysis_revision"] = revision
            assert client.get("/api/analyze/chart-data", params=params).status_code == 409


def test_execution_timeout_is_cooperative_and_releases_only_on_exit(tmp_path):
    service = JobManager(tmp_path / "timeout", execution_timeout_seconds=1)
    entered, release = Event(), Event()
    try:
        def work(context):
            context.output_path().write_bytes(b"partial")
            context.job.started_at -= 10
            entered.set()
            assert release.wait(3)
            context.progress("writing_rows", 1, 10, "rows")
        first = service.submit("export", "a", lambda: work)
        assert entered.wait(2)
        service.submit("analysis", "b", lambda: lambda ctx: {"analysis_revision": "b"})
        with pytest.raises(JobCapacityError):
            service.submit("analysis", "c", lambda: None)
        release.set()
        job = service.jobs[first["job_id"]]
        job.future.result(timeout=3)
        assert job.status == "failed" and "exceeded 1 seconds" in job.error
        assert not (service.directory / f"{job.job_id}.xlsx").exists()
    finally:
        release.set()
        service.close()


def test_mean_export_passes_statistics_and_provenance(manager, monkeypatch):
    raw = pd.DataFrame({"Chainage": [12.5, 12.5, 13.], "height1": [1., 3., 8.]})
    results = {"Low Height": pd.DataFrame({"maxValue": [1.]})}
    snapshot = {"analysis_revision": "rev", "raw_df": raw, "results": results,
                "params": {"line": "TWL", "track": "UT", "section": "Mainline", "session": "Mainline",
                           "date_str": "20260907", "station_start": "CEN", "station_end": "TSW"}}
    observed = {}
    def writer(actual_results, chart_df, chart_statistics_df, metadata, output_path, **kwargs):
        observed.update(chart=chart_df, statistics=chart_statistics_df, metadata=metadata, results=actual_results)
        Path(output_path).write_bytes(b"report")
    monkeypatch.setattr(api, "export_analysis_report", writer)
    created = manager.submit("export", "a", lambda: api._export_job_work(snapshot, "chainage_mean"), "rev")
    job = manager.jobs[created["job_id"]]
    job.future.result(timeout=3)
    assert job.status == "ready", job.error
    assert observed["chart"]["height1"].tolist() == [2., 8.]
    assert observed["chart"] is observed["statistics"]
    assert observed["results"] is results
    assert observed["metadata"]["raw_row_count"] == 3
    assert observed["metadata"]["grouped_row_count"] == 2
    assert job.filename.endswith("_ChainageMean.xlsx")
    assert raw.height1.tolist() == [1., 3., 8.]


def test_download_interrupt_releases_lease(manager, tmp_path):
    report = tmp_path / "report.xlsx"
    report.write_bytes(b"report")
    released = []
    response = api._LeasedFileResponse(report)
    response._release = lambda: released.append(True)
    async def receive():
        return {"type": "http.request"}
    async def send(message):
        if message["type"] == "http.response.body":
            raise ConnectionError("client disconnected")
    with pytest.raises(ConnectionError):
        asyncio.run(response({"type": "http", "method": "GET", "headers": []}, receive, send))
    assert released == [True]


def test_publish_and_cancellation_have_atomic_order(manager):
    committed, release = Event(), Event()
    def work(context):
        result = context.publish(lambda: {"analysis_revision": "committed"})
        committed.set()
        assert release.wait(3)
        return result
    created = manager.submit("analysis", "a", lambda: work)
    assert committed.wait(2)
    try:
        assert manager.cancel_job(created["job_id"], "a")["status"] == "running"
    finally:
        release.set()
    job = manager.jobs[created["job_id"]]
    job.future.result(timeout=3)
    assert job.status == "ready"
    assert job.result == {"analysis_revision": "committed"}


def test_close_cancels_queued_work_and_drops_captured_frames(tmp_path):
    import weakref
    import gc
    service = JobManager(tmp_path / "closing")
    entered = Event()
    def running(context):
        entered.set()
        assert context.job.cancel.wait(3)
        context.check_cancelled()
    service.submit("analysis", "a", lambda: running)
    assert entered.wait(2)
    raw = pd.DataFrame({"Chainage": [1.]})
    reference = weakref.ref(raw)
    def capture(frame):
        return lambda context: {"analysis_revision": str(len(frame))}
    service.submit("analysis", "b", lambda: capture(raw))
    del raw
    assert reference() is not None
    service.close()
    gc.collect()
    assert reference() is None
    assert not service.directory.exists()
    assert not service.jobs


def test_mean_detail_reuses_revision_cache_and_preserves_full_pass_ids(monkeypatch):
    from app.core import chainage_aggregation
    raw = pd.DataFrame({"Chainage": [10., 11., 10., 11.], "height1": [1., 3., 5., 7.],
                        "SampleCount": [4, 5, 0, 1]})
    first = {"analysis_revision": "one", "raw_df": raw}
    second = {"analysis_revision": "two", "raw_df": raw.assign(height1=[10., 30., 50., 70.])}
    aggregate = Mock(wraps=chainage_aggregation.aggregate_chainage)
    monkeypatch.setattr(chainage_aggregation, "aggregate_chainage", aggregate)
    monkeypatch.setattr(api, "ANALYSIS_SESSIONS", {"a": first, "b": second})
    api._snapshot_chart_payload(first, "chainage_mean")  # Same path as initial analysis.
    cached = first["mean_chart_frame"]
    with TestClient(app) as client:
        def detail(session, revision, start, end):
            response = client.get("/api/analyze/chart-data", params={
                "client_session_id": session, "analysis_revision": revision,
                "chart_data_mode": "chainage_mean", "from_m": start, "to_m": end})
            assert response.status_code == 200, response.text
            return response.json()["chart_data"]
        assert detail("a", "one", 10, 10)["height1"] == [1., 5.]
        assert detail("a", "one", 11, 11)["pass_id"] == [0, 1]
        assert aggregate.call_count == 1
        assert first["mean_chart_frame"] is cached
        assert detail("b", "two", 10, 10)["height1"] == [10., 50.]
        assert aggregate.call_count == 2
        assert second["mean_chart_frame"] is not cached
    pd.testing.assert_frame_equal(raw, pd.DataFrame({
        "Chainage": [10., 11., 10., 11.], "height1": [1., 3., 5., 7.], "SampleCount": [4, 5, 0, 1]}))


def test_concurrent_detail_cache_misses_are_serial_and_leave_event_loop_responsive(monkeypatch):
    from app.core import chainage_aggregation
    original = chainage_aggregation.aggregate_chainage
    entered, release = Event(), Event()
    calls = []
    def aggregate(frame, **kwargs):
        calls.append(frame)
        entered.set()
        assert release.wait(3)
        return original(frame, **kwargs)
    raw = pd.DataFrame({"Chainage": [1., 1., 2.], "height1": [2., 4., 6.]})
    snapshot = {"analysis_revision": "rev", "raw_df": raw}
    monkeypatch.setattr(chainage_aggregation, "aggregate_chainage", aggregate)
    monkeypatch.setattr(api, "ANALYSIS_SESSIONS", {"a": snapshot})
    monkeypatch.setattr(api, "DETAIL_LIMITER", api.anyio.CapacityLimiter(1))
    async def run():
        async def detail(start, end):
            return await api.get_chart_data(from_m=start, to_m=end, max_points=500, file_path=None,
                line=None, client_session_id="a", analysis_revision="rev", chart_data_mode="chainage_mean")
        one = asyncio.create_task(detail(1, 1))
        assert await asyncio.to_thread(entered.wait, 2)
        two = asyncio.create_task(detail(2, 2))
        await asyncio.sleep(0)  # Let the second request queue on the limiter.
        assert len(calls) == 1  # Event loop can run while the first aggregate is blocked.
        release.set()
        return await asyncio.gather(one, two)
    try:
        outputs = asyncio.run(run())
    finally:
        release.set()
    assert [output["chart_data"]["height1"] for output in outputs] == [[3.], [6.]]
    assert len(calls) == 1


@pytest.mark.parametrize("legacy_get", [False, True])
def test_raw_csv_generation_keeps_event_loop_responsive(monkeypatch, legacy_get):
    raw = pd.DataFrame({"Chainage": [1.], "height1": [2.]})
    params = {"line": "TWL", "track": "UT", "section": "Mainline", "session": "Mainline",
              "date_str": "20260907", "station_start": "CEN", "station_end": "TSW"}
    monkeypatch.setattr(api, "ANALYSIS_SESSIONS", {"a": {"raw_df": raw}})
    monkeypatch.setattr(api, "LAST_RAW_DF", raw)
    monkeypatch.setattr(api, "LAST_ANALYSIS_PARAMS", params)
    entered, release = Event(), Event()
    def csv_writer(frame):
        entered.set()
        assert release.wait(3)
        assert frame is raw
        return api.io.BytesIO(b"Chainage,height1\n1,2\n")
    monkeypatch.setattr(api.ExcelExporter, "export_raw_csv", csv_writer)
    async def run():
        request = api.ExportRawRequest(client_session_id="a", params=params)
        endpoint = (api.export_raw_data(date_str=None, line=None, track=None, section=None)
                    if legacy_get else api.export_raw_data_generate(request))
        task = asyncio.create_task(endpoint)
        assert await asyncio.to_thread(entered.wait, 2)
        release.set()  # This runs on the event loop while CSV writing is blocked.
        return await task
    try:
        response = asyncio.run(run())
    finally:
        release.set()
    assert response.status_code == 200
