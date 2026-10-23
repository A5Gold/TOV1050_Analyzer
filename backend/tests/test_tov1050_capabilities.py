from pathlib import Path
import pytest
from app.core.tov1050_metadata import TOV1050MetadataManager
from app.core.tov1050_capabilities import TensionLengthInterval, sweep_approved_intervals, MetadataCapabilityError

CONFIG = Path(__file__).resolve().parents[2] / "config"


def test_native_points_are_not_physical_intervals():
    manager = TOV1050MetadataManager(CONFIG / "ISL metadata.xlsx")
    points = manager.get_bracket_points("ISL", "Mainline", "UT")
    cr = points[points.tension_length == "CR289"]
    assert len(cr) == 31
    assert (cr.chainage_m.min(), cr.chainage_m.max()) == (99731, 99991)
    assert cr.source_excel_row.notna().all()
    assert cr.source_workbook.str.endswith("TOV1050 TL-BK No.xlsx").all()
    capabilities = manager.get_capabilities("ISL", "Mainline", "UT")
    assert capabilities["overlap_state"] == "unknown"
    assert capabilities["capabilities"]["bracket_points"]["status"] == "available"
    assert capabilities["capabilities"]["tension_length_intervals"]["status"] == "unavailable"
    for method in (manager.get_tension_length_lookup, manager.get_tension_length_source_rows):
        with pytest.raises(MetadataCapabilityError, match="ISL metadata.xlsx/ISL/Mainline/UT"):
            method("ISL", "UT", "Mainline")


def test_legal_colocation_and_landmarks_preserve_multiplicity():
    manager = TOV1050MetadataManager(CONFIG / "LAR_AEL metadata.xlsx")
    points = manager.get_bracket_points("AEL", "Mainline", "UT")
    at = points[points.chainage_m == 24540]
    assert {"303-013", "307-001"}.issubset(set(at.bracket))
    assert set(points.classification) <= {"normal", "termination"}
    landmarks = manager.get_landmark_points("AEL", "Mainline", "UT")
    assert not set(landmarks.classification) - {"landmark"}


def tl(start, end, name):
    return TensionLengthInterval(start, end, name, "test-approved", f"engineering:{name}")


def test_sweep_preserves_contact_triple_overlap_unknown_and_single_point():
    atoms = sweep_approved_intervals([tl(0, 2, "A"), tl(2, 4, "B"), tl(2, 3, "C"), tl(2, 2, "D"), tl(5, 6, "E"), tl(1, 3, "F")])
    contact = next(x for x in atoms if x.from_m == x.to_m == 2)
    assert contact.active_tension_lengths == ("A", "B", "C", "D", "F")
    assert contact.closed == "both"
    span = next(x for x in atoms if (x.from_m, x.to_m) == (2, 3))
    assert span.active_tension_lengths == ("B", "C", "F")
    assert span.closed == "neither"
    gap = next(x for x in atoms if (x.from_m, x.to_m) == (4, 5))
    assert gap.state == "unknown" and gap.active_tension_lengths == ()
    assert atoms[0].state == "known_non_overlap"
    with pytest.raises(ValueError, match="approval"):
        TensionLengthInterval(0, 1, "A", "", "source")


def test_tks_isolated_from_mainline():
    tks = TOV1050MetadataManager(CONFIG / "TKS metadata.xlsx")
    assert not tks.get_bracket_points("TKL", "TKS", "DT").empty
    with pytest.raises(ValueError, match="not found"):
        tks.get_bracket_points("TKL", "Mainline", "DT")


@pytest.mark.parametrize("route", ["/wear", "/upload"])
def test_wear_consumers_reject_unapproved_tov1050_geometry(monkeypatch, route):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.api.endpoints import calculation
    from app.core.calculation.excel_parser import ChartDataRecord
    record = ChartDataRecord("2026-10-23", "AEL", "UT", "Mainline", "", "SHO", "AWE", "303", 24540, 11, "Curve", None)
    monkeypatch.setattr(calculation, "parse_exception_report", lambda _: ([], [record]))
    monkeypatch.setattr(calculation, "get_config_dir", lambda: CONFIG)
    app = FastAPI()
    app.include_router(calculation.router)
    response = TestClient(app).post("/calculation"+route, data={"line":"AEL"}, files={"files":("report.xlsx",b"parser-mocked","application/octet-stream")})
    assert response.status_code == 422
    assert "LAR_AEL metadata.xlsx/AEL/Mainline/UT" in response.json()["detail"]
    assert "missing approved TensionLengthInterval" in response.json()["detail"]


def test_required_drl_missing_direction_stops_before_detector(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.api.endpoints import analysis
    monkeypatch.setattr(analysis,"CONFIG_DIR",CONFIG)
    app=FastAPI()
    app.include_router(analysis.router)
    sample=CONFIG.parent / "docs/TOV1050_Migration/Raw data/AEL/20260822_AEL_UT_SHO_AWE.csv"
    response=TestClient(app).post("/analyze",json=dict(file_path=str(sample),line="DRL",track="DT",section="Mainline",date_str="20261023"))
    assert response.status_code == 400
    assert "DRL metadata.xlsx/DRL/Mainline/DT" in response.json()["detail"]
    assert "track_intervals" in response.json()["detail"]
