import io
import os
import sys
from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app


client = TestClient(app)


def _make_stagger_excel_bytes() -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        pd.DataFrame(
            [
                {
                    "ID": "A1",
                    "Run Date": "2026-05-01",
                    "Level": "L1",
                    "Exception Type": "Stagger Left",
                    "Track": "UP",
                    "MaxLocation": 121000.0,
                    "MaxValue": 122.0,
                    "Line": "EAL",
                }
            ]
        ).to_excel(writer, sheet_name="Summary", index=False)
        pd.DataFrame(
            [
                {
                    "Chainage": 120900.0,
                    "WHGT1": 5300.0,
                    "WHGT2": 5310.0,
                    "WHGT3": 5320.0,
                    "WHGT4": 5330.0,
                    "STG1": 90.0,
                    "STG2": 91.0,
                    "STG3": 92.0,
                    "STG4": 93.0,
                },
                {
                    "Chainage": 121000.0,
                    "WHGT1": 5400.0,
                    "WHGT2": 5390.0,
                    "WHGT3": 5380.0,
                    "WHGT4": 5410.0,
                    "STG1": 120.0,
                    "STG2": 118.0,
                    "STG3": 122.0,
                    "STG4": 121.0,
                },
                {
                    "Chainage": 121120.0,
                    "WHGT1": 5500.0,
                    "WHGT2": 5490.0,
                    "WHGT3": 5480.0,
                    "WHGT4": 5470.0,
                    "STG1": 80.0,
                    "STG2": 81.0,
                    "STG3": 82.0,
                    "STG4": 83.0,
                },
            ]
        ).to_excel(writer, sheet_name="ChartData", index=False)
    return buf.getvalue()


def _make_exception_report_bytes() -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        pd.DataFrame(
            [
                {
                    "Run Date": "2026-05-01",
                    "Line": "EAL",
                    "Track": "UP",
                    "Section": "Mainline",
                    "Task No": "U2",
                    "St. Start": "FOT",
                    "St. End": "TAP",
                    "ID": "A1",
                    "FromM": 113498.0,
                    "ToM": 113500.0,
                    "Length": 2.0,
                    "Exception Type": "Stagger Left",
                    "MaxValue": 122.0,
                    "MaxLocation": 113498.5,
                    "Overlap": None,
                    "Tension Length": "H01",
                    "Track Type": "Tangent",
                    "Level": "L1",
                    "Landmark": None,
                    "Class": None,
                }
            ]
        ).to_excel(writer, sheet_name="Summary", index=False)
        pd.DataFrame(
            [
                {
                    "task_run_date": "20260501",
                    "line": "EAL",
                    "track": "UP",
                    "Section": "Mainline",
                    "task_no": "U2",
                    "station_start": "FOT",
                    "station_end": "TAP",
                    "Chainage": 113498.0,
                    "height1": 5300.0,
                    "height2": 5301.0,
                    "height3": 5302.0,
                    "height4": 5303.0,
                    "stagger1": -107.97,
                    "stagger2": -107.50,
                    "stagger3": -107.20,
                    "stagger4": -107.10,
                    "wear1": 11.87,
                    "wear2": None,
                    "wear3": None,
                    "wear4": None,
                    "Track Type": "Tangent",
                    "Overlap": None,
                    "Tension Length": "H01",
                    "Landmark": None,
                    "Class": None,
                    "height_min": 5300.0,
                    "height_max": 5303.0,
                    "wear_min": 11.87,
                    "wear_max": 11.87,
                    "stg_max": -107.10,
                    "stg_min": -107.97,
                }
            ]
        ).to_excel(writer, sheet_name="ChartData", index=False)
    return buf.getvalue()


def _make_repeated_excel_bytes() -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        pd.DataFrame(
            [
                {
                    "ID": "A1",
                    "FromM": 113498.0,
                    "ToM": 113500.0,
                    "Run Date": "2026-05-02",
                    "MaxValue": 122.0,
                    "MaxLocation": 113499.0,
                    "Exception Type": "Wire Wear",
                    "Level": "L2",
                }
            ]
        ).to_excel(writer, sheet_name="Summary", index=False)
    return buf.getvalue()


def _make_repeated_excel_without_stagger_bytes() -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        pd.DataFrame(
            [
                {
                    "TASK RUN DATA": "2026-05-02",
                    "Unnamed: 1": "EAL",
                    "Unnamed: 2": "UP",
                    "Unnamed: 3": "Mainline",
                    "Unnamed: 4": "U2",
                    "Unnamed: 5": "FOT",
                    "Unnamed: 6": "TAP",
                    "EXCEPTION": "Wire Wear",
                    "Unnamed: 8": "W63",
                    "Unnamed: 9": 113498.0,
                    "Unnamed: 10": 113500.0,
                    "Unnamed: 11": 2.0,
                    "Unnamed: 12": "Wire Wear",
                    "Unnamed: 13": 122.0,
                    "Unnamed: 14": 113499.0,
                    "Unnamed: 15": None,
                    "Unnamed: 16": "H01",
                    "Unnamed: 17": "Tangent",
                    "Unnamed: 18": "L2",
                    "Unnamed: 19": None,
                    "Unnamed: 20": None,
                    "Unnamed: 21": None,
                    "INITIAL CHECK": None,
                    "Unnamed: 23": None,
                    "Unnamed: 24": None,
                    "Unnamed: 25": None,
                    "SITE VERIFICATION (IF ANY)": None,
                    "Unnamed: 27": None,
                    "Unnamed: 28": None,
                    "Unnamed: 29": None,
                    "FINAL ADJUSTMENT (IF ANY)": None,
                    "Unnamed: 31": None,
                    "Unnamed: 32": None,
                    "Unnamed: 33": None,
                }
            ]
        ).to_excel(writer, sheet_name="Summary", index=False)
    return buf.getvalue()


def test_stagger_endpoint_returns_summary_results(monkeypatch):
    from app.api.endpoints import calculation
    from app.core.calculation.stagger_metadata import RangeValue, SupportPoint

    monkeypatch.setattr(
        calculation,
        "load_stagger_metadata",
        lambda line, workbook_path=None, config_dir=None: {
            "supports": {
                "EAL": {
                    "up": [
                        SupportPoint(line="EAL", track="up", chainage=120900.0),
                        SupportPoint(line="EAL", track="up", chainage=121020.0),
                        SupportPoint(line="EAL", track="up", chainage=121120.0),
                    ]
                }
            },
            "wind_factor": {
                "EAL": {
                    "kr": {
                        "up": [RangeValue(0.0, 999999.0, 1.2)],
                        "down": [RangeValue(0.0, 999999.0, 1.2)],
                    },
                    "ke": {
                        "up": [RangeValue(0.0, 999999.0, 1.1)],
                        "down": [RangeValue(0.0, 999999.0, 1.1)],
                    },
                    "kh": {
                        "up": [RangeValue(0.0, 999999.0, 1.0)],
                        "down": [RangeValue(0.0, 999999.0, 1.0)],
                    },
                }
            },
            "constants": {"tension": 13.8},
        },
    )

    response = client.post(
        "/api/calculation/stagger",
        files=[
            (
                "file",
                (
                    "stagger.xlsx",
                    _make_stagger_excel_bytes(),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ),
            )
        ],
    )

    assert response.status_code == 200
    body = response.json()
    assert "results" in body
    assert body["results"][0]["id"] == "A1"
    assert body["results"][0]["trace_available"] is True


def test_stagger_endpoint_accepts_exception_report_chartdata_headers(monkeypatch):
    from app.api.endpoints import calculation
    from app.core.calculation.stagger_metadata import RangeValue, SupportPoint

    monkeypatch.setattr(
        calculation,
        "load_stagger_metadata",
        lambda line, workbook_path=None, config_dir=None: {
            "supports": {
                "EAL": {
                    "up": [
                        SupportPoint(line="EAL", track="up", chainage=113490.0),
                        SupportPoint(line="EAL", track="up", chainage=113500.0),
                        SupportPoint(line="EAL", track="up", chainage=113510.0),
                    ]
                }
            },
            "wind_factor": {
                "EAL": {
                    "kr": {"up": [RangeValue(0.0, 999999.0, 1.2)], "down": [RangeValue(0.0, 999999.0, 1.2)]},
                    "ke": {"up": [RangeValue(0.0, 999999.0, 1.1)], "down": [RangeValue(0.0, 999999.0, 1.1)]},
                    "kh": {"up": [RangeValue(0.0, 999999.0, 1.0)], "down": [RangeValue(0.0, 999999.0, 1.0)]},
                }
            },
            "constants": {"tension": 13.8},
        },
    )

    response = client.post(
        "/api/calculation/stagger",
        files=[
            (
                "file",
                (
                    "20260301_EAL_U2_FOT-TAP_Exception_Report.xlsx",
                    _make_exception_report_bytes(),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ),
            )
        ],
    )

    assert response.status_code == 200
    body = response.json()
    assert body["results"][0]["id"] == "A1"
    assert body["traces"][0]["trace_status"] == "complete"


def test_stagger_endpoint_infers_line_from_filename_when_summary_has_no_line_column(monkeypatch):
    from app.api.endpoints import calculation
    from app.core.calculation.stagger_metadata import RangeValue, SupportPoint
    from dataclasses import dataclass

    captured: dict[str, str] = {}

    @dataclass
    class FakeSummary:
        id: str
        trace_available: bool = True

    def fake_load_stagger_metadata(line, workbook_path=None, config_dir=None):
        captured["line"] = line
        return {
            "supports": {
                "EAL": {
                    "up": [
                        SupportPoint(line="EAL", track="up", chainage=113490.0),
                        SupportPoint(line="EAL", track="up", chainage=113500.0),
                        SupportPoint(line="EAL", track="up", chainage=113510.0),
                    ]
                }
            },
            "wind_factor": {
                "EAL": {
                    "kr": {"up": [RangeValue(0.0, 999999.0, 1.2)], "down": [RangeValue(0.0, 999999.0, 1.2)]},
                    "ke": {"up": [RangeValue(0.0, 999999.0, 1.1)], "down": [RangeValue(0.0, 999999.0, 1.1)]},
                    "kh": {"up": [RangeValue(0.0, 999999.0, 1.0)], "down": [RangeValue(0.0, 999999.0, 1.0)]},
                }
            },
            "constants": {"tension": 13.8},
        }

    def fake_compute_stagger_result_for_record(record, chart_rows, metadata, case_type):
        return FakeSummary(id=record.id), {"trace_status": "complete", "case_type": case_type}

    monkeypatch.setattr(calculation, "load_stagger_metadata", fake_load_stagger_metadata)
    monkeypatch.setattr(calculation, "compute_stagger_result_for_record", fake_compute_stagger_result_for_record)

    report_path = (
        Path(__file__).resolve().parents[2]
        / "docs"
        / "test data"
        / "EAL"
        / "Cycle 8"
        / "20260613_EAL_U3_TAP-LOW_Exception_Report.xlsx"
    )

    response = client.post(
        "/api/calculation/stagger",
        files=[
            (
                "file",
                (
                    "20260613_EAL_U3_TAP-LOW_Exception_Report.xlsx",
                    report_path.read_bytes(),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ),
            )
        ],
    )

    assert response.status_code == 200
    assert captured["line"] == "EAL"


def test_stagger_endpoint_uses_case_b_when_repeated_report_uploaded(monkeypatch):
    from app.api.endpoints import calculation
    from app.core.calculation.stagger_metadata import RangeValue, SupportPoint

    monkeypatch.setattr(
        calculation,
        "load_stagger_metadata",
        lambda line, workbook_path=None, config_dir=None: {
            "supports": {
                "EAL": {
                    "up": [
                        SupportPoint(line="EAL", track="up", chainage=113490.0),
                        SupportPoint(line="EAL", track="up", chainage=113500.0),
                        SupportPoint(line="EAL", track="up", chainage=113510.0),
                    ]
                }
            },
            "wind_factor": {
                "EAL": {
                    "kr": {"up": [RangeValue(0.0, 999999.0, 1.2)], "down": [RangeValue(0.0, 999999.0, 1.2)]},
                    "ke": {"up": [RangeValue(0.0, 999999.0, 1.1)], "down": [RangeValue(0.0, 999999.0, 1.1)]},
                    "kh": {"up": [RangeValue(0.0, 999999.0, 1.0)], "down": [RangeValue(0.0, 999999.0, 1.0)]},
                }
            },
            "constants": {"tension": 13.8},
        },
    )

    response = client.post(
        "/api/calculation/stagger",
        files=[
            (
                "file",
                (
                    "20260301_EAL_U2_FOT-TAP_Exception_Report.xlsx",
                    _make_exception_report_bytes(),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ),
            ),
            (
                "repeated_file",
                (
                    "20260301_EAL_U2_FOT-TAP_Exception_Report_3_Repeated.xlsx",
                    _make_repeated_excel_bytes(),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ),
            ),
        ],
    )

    assert response.status_code == 200
    body = response.json()
    assert body["results"][0]["remark"][0] == "Case B"
    assert body["traces"][0]["case_type"] == "B"


def test_stagger_endpoint_falls_back_to_case_a_when_repeated_has_no_stagger_candidates(monkeypatch):
    from app.api.endpoints import calculation
    from app.core.calculation.stagger_metadata import RangeValue, SupportPoint

    monkeypatch.setattr(
        calculation,
        "load_stagger_metadata",
        lambda line, workbook_path=None, config_dir=None: {
            "supports": {
                "EAL": {
                    "up": [
                        SupportPoint(line="EAL", track="up", chainage=113490.0),
                        SupportPoint(line="EAL", track="up", chainage=113500.0),
                        SupportPoint(line="EAL", track="up", chainage=113510.0),
                    ]
                }
            },
            "wind_factor": {
                "EAL": {
                    "kr": {"up": [RangeValue(0.0, 999999.0, 1.2)], "down": [RangeValue(0.0, 999999.0, 1.2)]},
                    "ke": {"up": [RangeValue(0.0, 999999.0, 1.1)], "down": [RangeValue(0.0, 999999.0, 1.1)]},
                    "kh": {"up": [RangeValue(0.0, 999999.0, 1.0)], "down": [RangeValue(0.0, 999999.0, 1.0)]},
                }
            },
            "constants": {"tension": 13.8},
        },
    )

    response = client.post(
        "/api/calculation/stagger",
        files=[
            (
                "file",
                (
                    "20260301_EAL_U2_FOT-TAP_Exception_Report.xlsx",
                    _make_exception_report_bytes(),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ),
            ),
            (
                "repeated_file",
                (
                    "20260301_EAL_U2_FOT-TAP_Exception_Report_3_Repeated.xlsx",
                    _make_repeated_excel_without_stagger_bytes(),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ),
            ),
        ],
    )

    assert response.status_code == 200
    body = response.json()
    assert body["results"] == []
    assert body["traces"] == []
    assert any("Case B" in warning for warning in body["warnings"])


def test_stagger_endpoint_returns_no_results_when_repeated_ids_do_not_match_exception_summary(monkeypatch):
    from app.api.endpoints import calculation
    from app.core.calculation.stagger_metadata import RangeValue, SupportPoint

    monkeypatch.setattr(
        calculation,
        "load_stagger_metadata",
        lambda line, workbook_path=None, config_dir=None: {
            "supports": {
                "EAL": {
                    "up": [
                        SupportPoint(line="EAL", track="up", chainage=113490.0),
                        SupportPoint(line="EAL", track="up", chainage=113500.0),
                        SupportPoint(line="EAL", track="up", chainage=113510.0),
                    ]
                }
            },
            "wind_factor": {
                "EAL": {
                    "kr": {"up": [RangeValue(0.0, 999999.0, 1.2)], "down": [RangeValue(0.0, 999999.0, 1.2)]},
                    "ke": {"up": [RangeValue(0.0, 999999.0, 1.1)], "down": [RangeValue(0.0, 999999.0, 1.1)]},
                    "kh": {"up": [RangeValue(0.0, 999999.0, 1.0)], "down": [RangeValue(0.0, 999999.0, 1.0)]},
                }
            },
            "constants": {"tension": 13.8},
        },
    )

    mismatched_repeated = io.BytesIO()
    with pd.ExcelWriter(mismatched_repeated, engine="openpyxl") as writer:
        pd.DataFrame(
            [
                {
                    "ID": "B9",
                    "Run Date": "2026-05-02",
                    "MaxValue": 122.0,
                    "MaxLocation": 113499.0,
                    "Exception Type": "Stagger Left",
                    "Level": "L2",
                }
            ]
        ).to_excel(writer, sheet_name="Summary", index=False)

    response = client.post(
        "/api/calculation/stagger",
        files=[
            (
                "file",
                (
                    "20260301_EAL_U2_FOT-TAP_Exception_Report.xlsx",
                    _make_exception_report_bytes(),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ),
            ),
            (
                "repeated_file",
                (
                    "20260301_EAL_U2_FOT-TAP_Exception_Report_3_Repeated.xlsx",
                    mismatched_repeated.getvalue(),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ),
            ),
        ],
    )

    assert response.status_code == 200
    body = response.json()
    assert body["results"] == []
    assert body["traces"] == []
    assert any("Case B" in warning for warning in body["warnings"])


def test_stagger_endpoint_returns_results_for_real_u3_exception_report():
    report_path = (
        Path(__file__).resolve().parents[2]
        / "docs"
        / "test data"
        / "EAL"
        / "Cycle 8"
        / "20260613_EAL_U3_TAP-LOW_Exception_Report.xlsx"
    )

    response = client.post(
        "/api/calculation/stagger",
        files=[
            (
                "file",
                (
                    report_path.name,
                    report_path.read_bytes(),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ),
            )
        ],
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["results"]) > 0
