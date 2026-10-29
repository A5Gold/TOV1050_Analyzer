from pathlib import Path
import gc
import time
import weakref

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.endpoints import analysis as api
from app.core.chart_cache import ChartSource, WindowCache
from app.core.chart_sampling import build_chart_payload, MEASUREMENT_COLUMNS
from app.core.chart_thresholds import build_threshold_segments


def snapshot(frame, revision="r"):
    return {"analysis_mode": "median", "analysis_revision": revision,
            "analysis_df": frame, "results": {}, "params": {"line": "TWL"}}


def test_negative_padding_reversed_and_empty_viewports(monkeypatch):
    state = snapshot(pd.DataFrame({"Chainage": [0., 100., 200.], "height1": [1., 2., 3.]}))
    state["threshold_segments"] = [{"from_m": 0., "to_m": 200., "metric": "height",
                                    "exception_type": "Low Height", "level": "L1", "value": 3.}]
    monkeypatch.setattr(api, "ANALYSIS_SESSIONS", {"a": state})
    with TestClient(app) as client:
        def detail(start, end):
            return client.get("/api/analyze/chart-data", params={"client_session_id": "a",
                "analysis_revision": "r", "from_m": start, "to_m": end, "max_points": 12000})
        response = detail(-919.1600784073908, 16073.0195179871)
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["chart_domain"] == {"from_m": 0., "to_m": 200.}
        assert result["chart_resolution"]["from_m"] == 0.
        assert result["chart_resolution"]["to_m"] == 200.
        assert detail(200, 100).json()["chart_data"]["Chainage"] == [100., 200.]
        assert detail(200, 200).json()["chart_data"]["Chainage"] == [200.]
        empty = detail(-200, -100).json()
        assert empty["chart_data"]["Chainage"] == []
        assert empty["chart_resolution"]["strategy"] == "empty"
        assert empty["threshold_segments"] == []
        for value in ("nan", "inf", "-inf"):
            assert detail(value, 100).status_code == 422


def test_prepared_window_retains_acquisition_order_and_does_not_reconvert_full_frame(monkeypatch):
    frame = pd.DataFrame({"Chainage": [3., 2., 1., 1., 2., 3.],
                          "height1": [30., 20., 10., 11., 21., 31.],
                          "segment_id": [0, 0, 0, 1, 1, 1]})
    source = ChartSource(frame, frame.columns, numeric_columns=MEASUREMENT_COLUMNS)
    original = pd.to_numeric
    sizes = []
    def observe(values, *args, **kwargs):
        sizes.append(len(values))
        return original(values, *args, **kwargs)
    monkeypatch.setattr(pd, "to_numeric", observe)
    payload, resolution = build_chart_payload(source, source.columns, from_m=2, to_m=2)
    assert payload["height1"] == [20., 21.]
    assert payload["segment_id"] == [0, 1]
    assert max(sizes) == 2
    assert resolution["source_points"] == 2


def test_threshold_lines_use_detector_fallback_nan_and_signed_stagger_without_exceptions():
    frame = pd.DataFrame({"Chainage": [0., 1., 2., 3., 4., 5.],
                          "Class": ["Undefined", "Undefined", "Open", "Open", "Tunnel", "Tunnel"],
                          "Track Type": ["Tangent"] * 4 + ["Curve"] * 2})
    thresholds = pd.DataFrame([
        {"Exc Type": "Low Height", "Class": "both", "Track Type": "both", "Low Height L1": 3900.},
        {"Exc Type": "Low Height", "Class": "Open", "Track Type": "both", "Low Height L1": np.nan},
        {"Exc Type": "Wire Wear", "Class": "both", "Track Type": "both", "Wire Wear L1": 10.},
        {"Exc Type": "Stagger Left", "Class": "both", "Track Type": "Tangent", "Stagger L1": 400.},
        {"Exc Type": "Stagger Left", "Class": "both", "Track Type": "Curve", "Stagger L1": 450.},
        {"Exc Type": "Stagger Right", "Class": "both", "Track Type": "Tangent", "Stagger L1": 400.},
        {"Exc Type": "Stagger Right", "Class": "both", "Track Type": "Curve", "Stagger L1": 450.},
    ])
    lines = build_threshold_segments(frame, thresholds)
    low = [s for s in lines if s["exception_type"] == "Low Height"]
    assert [(s["from_m"], s["to_m"], s["value"]) for s in low] == [(0., 1., 3900.), (4., 5., 3900.)]
    assert not any(s["exception_type"] == "Wire Wear" and s["level"] == "L2" for s in lines)
    assert {s["value"] for s in lines if s["metric"] == "stagger"} == {-450., -400., 400., 450.}


def test_raw_mmap_avoids_retained_frame_and_releases_after_ttl():
    raw = pd.DataFrame({"Chainage": [3., 2., 1.], "height1": [30., 20., 10.],
                        "Class": ["Open", "Open", None]})
    reference = weakref.ref(raw)
    source = ChartSource(raw, raw.columns, numeric_columns=MEASUREMENT_COLUMNS, disk=True, ttl=.05)
    directory = Path(source.directory.name)
    del raw
    gc.collect()
    assert reference() is None
    # Explicitly expire instead of relying on timing-sensitive sleeps.
    source.last_access = time.monotonic() - 1
    source._expire()
    assert source.closed and not directory.exists()


def test_raw_hot_cache_validates_source_stat_without_reread_or_hash(tmp_path, monkeypatch):
    path = tmp_path / "raw.csv"
    path.write_text("source")
    frame = pd.DataFrame({"Chainage": [1., 2.], "height1": [3., 4.]})
    source = ChartSource(frame, frame.columns, numeric_columns=MEASUREMENT_COLUMNS, disk=True)
    state = {"analysis_mode": "raw_overview", "analysis_revision": "r", "source_path": str(path),
             "source_sha256": api._file_digest(path), "source_stat": api._source_stat(path),
             "params": {}, "chart_sources": {"raw": source}, "chart_domain": source.domain}
    monkeypatch.setattr(api, "ANALYSIS_SESSIONS", {"a": state})
    monkeypatch.setattr(api, "_reload_overview_source", lambda _: pytest.fail("hot viewport reread source"))
    original_digest = api._file_digest
    digests = []
    monkeypatch.setattr(api, "_file_digest", lambda p: (digests.append(p), original_digest(p))[1])
    with TestClient(app) as client:
        params = {"client_session_id": "a", "analysis_revision": "r", "chart_data_mode": "raw",
                  "from_m": 1, "to_m": 2}
        assert client.get("/api/analyze/chart-data", params=params).status_code == 200
        assert client.get("/api/analyze/chart-data", params=params).status_code == 200
        assert not digests
        path.write_text("changed")
        response = client.get("/api/analyze/chart-data", params=params)
        assert response.status_code == 409 and source.closed
        assert len(digests) == 1


def test_window_cache_is_bounded_and_revision_isolated(monkeypatch):
    frame = pd.DataFrame({"Chainage": np.arange(100.), "height1": np.arange(100.)})
    first, second = snapshot(frame, "one"), snapshot(frame.assign(height1=99.), "two")
    for start in range(20):
        api._snapshot_chart_payload(first, "chainage_median", from_m=start, to_m=start + 1)
    assert len(first["chart_windows"].items) == 8
    assert first["chart_windows"].bytes <= first["chart_windows"].max_bytes
    payload, _ = api._snapshot_chart_payload(second, "chainage_median", from_m=1, to_m=2)
    assert payload["height1"] == [99., 99.]
    cache = WindowCache(max_entries=2, max_bytes=8)
    cache.put("too-large", ({"x": [1., 2.]}, {}))
    assert not cache.items


def test_median_export_job_keeps_algorithm_and_omits_filename_suffix(tmp_path, monkeypatch):
    from app.core.background_jobs import JobManager
    frame = pd.DataFrame({"Chainage": [1.], "height1": [2.]})
    state = snapshot(frame)
    state["params"] = {"line": "TWL", "track": "UT", "section": "Mainline", "session": "Mainline",
                       "station_start": "CEN", "station_end": "TSW", "date_str": "20260907"}
    state["aggregation_metadata"] = {"algorithm": "same_chainage_median_sample_v1", "source_points": 10,
                                     "representative_points": 1}
    captured = []
    def export(results, **kwargs):
        captured.append(kwargs)
        Path(kwargs["output_path"]).write_bytes(b"test-workbook")
    monkeypatch.setattr(api, "export_analysis_report", export)
    service = JobManager(tmp_path / "jobs")
    try:
        result = service.submit("export", "a", lambda: api._export_job_work(state, "chainage_median"))
        job = service.jobs[result["job_id"]]
        job.future.result(timeout=5)
        assert job.filename == "20260907_TWL_UT_MAINLINE_CEN_TSW_Exception_Report.xlsx"
        assert captured[0]["chart_df"] is frame
        assert captured[0]["metadata"]["algorithm"] == "same_chainage_median_sample_v1"
        assert captured[0]["metadata"]["source_points"] == 10
    finally:
        service.close()


def test_latest_viewport_skips_obsolete_queued_work(monkeypatch):
    import asyncio
    from threading import Event
    state = snapshot(pd.DataFrame({"Chainage": [1., 2.], "height1": [3., 4.]}))
    monkeypatch.setattr(api, "ANALYSIS_SESSIONS", {"a": state})
    monkeypatch.setattr(api, "DETAIL_LIMITER", api.anyio.CapacityLimiter(1))
    original = api._snapshot_chart_payload
    entered, release = Event(), Event()
    def blocked(*args, **kwargs):
        if kwargs.get("from_m") == 1.:
            entered.set()
            assert release.wait(3)
        return original(*args, **kwargs)
    monkeypatch.setattr(api, "_snapshot_chart_payload", blocked)
    async def run():
        async def get(start):
            return await api.get_chart_data(from_m=start, to_m=start, max_points=500,
                file_path=None, line=None, client_session_id="a", analysis_revision="r",
                chart_data_mode="chainage_median")
        one = asyncio.create_task(get(1.))
        assert await asyncio.to_thread(entered.wait, 2)
        two = asyncio.create_task(get(2.))
        await asyncio.sleep(0)
        release.set()
        return await asyncio.gather(one, two, return_exceptions=True)
    try:
        old, latest = asyncio.run(run())
    finally:
        release.set()
    assert old.status_code == 409
    assert old.detail["code"] == "CHART_REQUEST_SUPERSEDED"
    assert latest["chart_data"]["Chainage"] == [2.]


def test_raw_expiry_cold_load_and_explicit_release_are_revision_guarded(tmp_path, monkeypatch):
    path = tmp_path / "source.csv"
    path.write_text("source")
    frame = pd.DataFrame({"Chainage": [1., 2.], "height1": [3., 4.]})
    reads = []
    def reload(_):
        reads.append(True)
        return frame.copy()
    state = {"analysis_mode": "raw_overview", "analysis_revision": "r", "source_path": str(path),
             "source_sha256": api._file_digest(path), "source_stat": api._source_stat(path), "params": {}}
    monkeypatch.setattr(api, "_reload_overview_source", reload)
    monkeypatch.setattr(api, "ANALYSIS_SESSIONS", {"a": state})
    api._snapshot_chart_payload(state, "raw", from_m=1, to_m=2)
    source = state["chart_sources"]["raw"]
    source.last_access = time.monotonic() - 121
    source._expire()
    api._snapshot_chart_payload(state, "raw", from_m=1, to_m=2)
    assert len(reads) == 2
    assert "raw_df" not in state and "analysis_df" not in state
    replacement = state["chart_sources"]["raw"]
    with TestClient(app) as client:
        assert client.post("/api/analyze/chart-cache/release", json={
            "client_session_id": "a", "analysis_revision": "wrong"}).status_code == 409
        assert not replacement.closed
        assert client.post("/api/analyze/chart-cache/release", json={
            "client_session_id": "a", "analysis_revision": "r"}).status_code == 200
        assert replacement.closed
        assert not state.get("chart_sources")
    path.unlink()
    with pytest.raises(api.HTTPException) as error:
        api._snapshot_chart_payload(state, "raw", from_m=1, to_m=2)
    assert error.value.status_code == 409


@pytest.mark.parametrize("line,section,track,expected_track,expected_session,expected_branch", [
    ("DRL", "UT", "DN", "DT", "Mainline", "UT"),
    ("DRL", "PL", "UP", "UT", "PL", "PL"),
    ("EAL", "LMC", "DT", "DN", "LMC", "LMC"),
    ("EAL", "RAC", "UT", "UP", "RAC", "Mainline"),
    ("EAL", "LOW S1", "DT", "DN", "LOW S1", "Mainline"),
    ("TML", "Mainline", "DT", "DN", "Mainline", "Mainline"),
    ("TKL", "TKS", "DOWN", "DT", "TKS", "TKS"),
])
def test_analysis_registry_normalizes_wire_context_and_keeps_legacy_sections(
        tmp_path, monkeypatch, line, section, track, expected_track, expected_session, expected_branch):
    from unittest.mock import MagicMock
    raw = pd.DataFrame({"Chainage": [100., 101.], "height1": [5000., 5001.],
                        "Line": ["device label"] * 2, "Track": ["device direction"] * 2,
                        "Class": ["Open"] * 2, "Track Type": ["Tangent"] * 2})
    source = tmp_path / "test.datac"
    source.write_text("source")
    for name in (f"{line} metadata.xlsx", "TKS metadata.xlsx"):
        (tmp_path / name).write_text("metadata")
    meta = MagicMock()
    meta.get_all_thresholds.return_value = pd.DataFrame()
    meta.get_capabilities.return_value = {"capabilities": {name: {"status": "available"}
        for name in ("thresholds", "class_intervals", "track_intervals")}}
    detector = MagicMock()
    detector._map_class_info.side_effect = lambda frame, *args: frame
    detector._map_track_info.side_effect = lambda frame, *args: frame
    detector.analyze.return_value = ({}, pd.DataFrame())
    loader = MagicMock()
    loader.load_data.return_value = raw
    monkeypatch.setattr(api, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(api, "DataLoader", lambda: loader)
    monkeypatch.setattr(api, "TOV1050DataLoader", lambda: loader)
    monkeypatch.setattr(api, "MetadataManager", lambda _: meta)
    monkeypatch.setattr(api, "TOV1050MetadataManager", lambda _: meta)
    monkeypatch.setattr(api, "ExceptionDetector", lambda _: detector)
    monkeypatch.setattr(api, "ANALYSIS_SESSIONS", {})
    result = api._analyze_sync(api.AnalyzeRequest(file_path=str(source), line=line, section=section,
        track=track, date_str="20261029", client_session_id="context"))
    params = result["params"]
    assert params["track"] == expected_track
    assert params["session"] == expected_session
    assert params["branch"] == expected_branch
    assert params["source_context"]["track"] == track
    assert params["source_context"]["section"] == section
    assert result["chart_data"]["Section"] == [expected_session] * 2
    assert result["chart_data"]["branch"] == [expected_branch] * 2
    assert api.ANALYSIS_SESSIONS["context"]["analysis_df"]["source_track"].tolist() == ["device direction"] * 2


def test_unknown_analysis_line_cannot_fall_through_to_legacy_metadata(tmp_path):
    source = tmp_path / "test.datac"
    source.write_text("source")
    with pytest.raises(api.HTTPException) as error:
        api._analyze_sync(api.AnalyzeRequest(file_path=str(source), line="UNKNOWN", section="Mainline",
                                            track="UP", date_str="20261029"))
    assert error.value.status_code == 400
    assert "Unsupported parent line" in error.value.detail


def test_legacy_report_filename_with_session_does_not_use_tov1050_builder():
    assert api.generate_filename("20260410", "TML", "DN", "Mainline", "report", session="Mainline") == (
        "20260410_TML_DN_Mainline_Exception_Report.xlsx")
