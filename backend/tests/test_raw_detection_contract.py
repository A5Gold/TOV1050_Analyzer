"""Detector and exports must never consume chart representatives."""
import io
from unittest.mock import MagicMock

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook

from app.api.endpoints import analysis as api
from app.main import app
from app.core.report_context import read_report_context, validate_algorithm_compatibility, ReportContextError


def test_raw_samples_keep_gaps_passes_and_context_without_reduction():
    from app.core.chainage_reduction import annotate_raw_samples
    raw = pd.DataFrame({"Chainage": [100.] * 5, "height1": [5., 6., 7., 8., 9.],
        "source_row_number": [1, 2, 4, 5, 6], "SampleCount": [10, 11, 12, 1, 2],
        "Class": ["A", "A", "A", "A", "B"]})
    labeled = annotate_raw_samples(raw)
    assert labeled["height1"].tolist() == raw["height1"].tolist()
    assert labeled["segment_id"].tolist() == [0, 0, 1, 2, 3]
    assert labeled["pass_id"].tolist() == [0, 0, 0, 1, 1]
    assert "segment_id" not in raw


@pytest.mark.parametrize("line", ["TML", "TWL"])
def test_detector_sees_spike_hidden_by_chart_median(tmp_path, monkeypatch, line):
    raw = pd.DataFrame({"Chainage": [100., 100., 100., 101.],
                        "height1": [5000., 6000., 5000., 5000.],
                        "Class": ["Open"] * 4, "Track Type": ["Tangent"] * 4})
    source = tmp_path / "test.datac"
    source.write_text("source")
    (tmp_path / f"{line} metadata.xlsx").write_text("metadata")
    meta, detector, loader = MagicMock(), MagicMock(), MagicMock()
    meta.get_all_thresholds.return_value = pd.DataFrame()
    meta.get_capabilities.return_value = {"capabilities": {name: {"status": "available"}
        for name in ("thresholds", "class_intervals", "track_intervals")}}
    meta.map_approved_enrichment.side_effect = lambda frame, *args: frame
    meta.enrichment_evidence.return_value = {"Overlap": "Y", "Tension Length": "TL1; TL2", "Landmark": "Station"}
    detector._map_class_info.side_effect = lambda frame, *args: frame
    detector._map_track_info.side_effect = lambda frame, *args: frame
    seen = []
    def analyze(frame, **kwargs):
        seen.append(frame.copy())
        return {"High Height": pd.DataFrame({"maxLocation": [100.], "maxValue": [6000.]})}, pd.DataFrame()
    detector.analyze.side_effect = analyze
    loader.load_data.return_value = raw
    monkeypatch.setattr(api, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(api, "DataLoader", lambda: loader)
    monkeypatch.setattr(api, "MetadataManager", lambda _: meta)
    monkeypatch.setattr(api, "TOV1050MetadataManager", lambda _: meta)
    monkeypatch.setattr(api, "ExceptionDetector", lambda _: detector)
    monkeypatch.setattr(api, "ANALYSIS_SESSIONS", {})
    response = api._analyze_sync(api.AnalyzeRequest(file_path=str(source), line=line,
        section="Mainline", track="DN", date_str="20260410", client_session_id="raw-contract"))
    state = api.ANALYSIS_SESSIONS["raw-contract"]
    assert seen[0]["height1"].tolist() == [5000., 6000., 5000., 5000.]
    assert state["analysis_df"]["height1"].tolist() == [5000., 5000.]
    assert state["raw_df"] is state["analysis_df"]
    assert response["aggregation_metadata"]["detection_points"] == 4
    assert response["aggregation_metadata"]["representative_points"] == 2
    assert response["aggregation_metadata"]["detection_data_mode"] == "cleaned_raw"
    if line == "TWL":
        peak = response["exceptions"]["High Height"][0]
        assert peak["Overlap"] == "Y"
        assert peak["Tension Length"] == "TL1; TL2"
        assert peak["Landmark"] == "Station"
    api._release_chart_cache(state)


@pytest.mark.parametrize("endpoint", ["/api/export/report/generate", "/api/export/raw/generate"])
def test_session_export_reloads_complete_source_once(endpoint, monkeypatch):
    raw = pd.DataFrame({"Chainage": [100.] * 3, "height1": [5000., 6000., 5000.]})
    state = {"analysis_mode": "median", "source_path": "source.datac", "analysis_revision": "r",
             "analysis_df": raw.iloc[:1], "results": {}, "params": {"line": "TML"}}
    calls, exports = [], []
    def reload(snapshot):
        calls.append(snapshot)
        return raw
    def export(*args, **kwargs):
        exports.append(kwargs.get("chart_df", args[0] if args else None))
        return io.BytesIO(b"export")
    monkeypatch.setattr(api, "ANALYSIS_SESSIONS", {"raw-contract": state})
    monkeypatch.setattr(api, "_reload_cleaned_source", reload)
    monkeypatch.setattr(api, "export_analysis_report", export)
    monkeypatch.setattr(api.ExcelExporter, "export_raw_csv", export)
    with TestClient(app) as client:
        response = client.post(endpoint, json={"client_session_id": "raw-contract", "exceptions": {},
            "chart_data": {"height1": [1]}, "params": {"line": "TML"}})
    assert response.status_code == 200, response.text
    assert calls == [state]
    assert exports[0] is raw


def test_raw_detection_provenance_blocks_legacy_median_comparison():
    def context(metadata):
        workbook = Workbook()
        sheet = workbook.create_sheet("_Metadata")
        sheet.append(["key", "value"])
        for key, value in metadata.items():
            sheet.append([key, value])
        return read_report_context(workbook)
    chart_metadata = {"aggregation_version": "same_chainage_median_sample_v1", "aggregation": "chainage_median"}
    old = context(chart_metadata)
    new = context({**chart_metadata, "detection_algorithm": "cleaned_raw_signed_stagger_v1",
                   "detection_data_mode": "cleaned_raw"})
    assert new.algorithm == "cleaned_raw_signed_stagger_v1"
    assert new.algorithm_mode == "cleaned_raw"
    assert validate_algorithm_compatibility([new, new])
    with pytest.raises(ReportContextError, match="different analysis algorithms"):
        validate_algorithm_compatibility([old, new])


def test_report_median_chart_keeps_raw_detection_algorithm_compatible():
    def context(export_mode):
        workbook = Workbook()
        sheet = workbook.create_sheet("_Metadata")
        sheet.append(["key", "value"])
        for key, value in {"detection_algorithm": "cleaned_raw_signed_stagger_v1",
                           "detection_data_mode": "cleaned_raw",
                           "export_data_mode": export_mode}.items():
            sheet.append([key, value])
        return read_report_context(workbook)
    assert validate_algorithm_compatibility([context("cleaned_raw"), context("chainage_median")])
