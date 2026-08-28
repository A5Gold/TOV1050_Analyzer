import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.calculation.stagger_metadata import RangeValue, SupportPoint
from app.core.calculation.stagger_types import SelectedSummaryRecord


def test_compute_stagger_result_for_record_returns_summary_and_trace():
    from app.core.calculation.stagger_service import compute_stagger_result_for_record

    record = SelectedSummaryRecord(
        id="A1",
        line="EAL",
        track="up",
        exception_type="Stagger Left",
        max_location=121000.0,
    )
    supports = [
        SupportPoint(line="EAL", track="up", chainage=120900.0),
        SupportPoint(line="EAL", track="up", chainage=121020.0),
        SupportPoint(line="EAL", track="up", chainage=121120.0),
    ]
    chart_rows = [
        {
            "chainage": 120900.0,
            "heights": [5300.0, 5310.0, 5320.0, 5330.0],
            "staggers": [90.0, 91.0, 92.0, 93.0],
        },
        {
            "chainage": 121000.0,
            "heights": [5400.0, 5390.0, 5380.0, 5410.0],
            "staggers": [120.0, 118.0, 122.0, 121.0],
        },
        {
            "chainage": 121120.0,
            "heights": [5500.0, 5490.0, 5480.0, 5470.0],
            "staggers": [80.0, 81.0, 82.0, 83.0],
        },
    ]
    metadata = {
        "supports": {"EAL": {"up": supports}},
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
    }

    summary, trace = compute_stagger_result_for_record(
        record=record,
        chart_rows=chart_rows,
        metadata=metadata,
        case_type="A",
    )

    assert summary.id == "A1"
    assert summary.trace_available is True
    assert summary.overall_result in {"pass", "fail"}
    assert summary.remark == ["Case A", "ChartData A/I/B uses nearest-row assumption", "HeightCorrection defaulted to 0.0"]
    assert trace["case_type"] == "A"
    assert trace["k_eq"] == pytest.approx(1.32)
    assert trace["assumptions"] == {
        "chartdata_mapping": "nearest-row",
        "height_correction": "defaulted_to_zero",
    }
    assert trace["reference"]["spt_i"] == 121020.0
    assert trace["measurements"]["stg_i"] == 122.0
    assert trace["spans"]["ai"]["result"] in {"pass", "fail", "pass_short_circuit"}


def test_compute_stagger_result_for_record_returns_partial_trace_when_support_neighbors_missing():
    from app.core.calculation.stagger_service import compute_stagger_result_for_record

    record = SelectedSummaryRecord(
        id="A2",
        line="EAL",
        track="up",
        exception_type="Stagger Left",
        max_location=121010.0,
    )
    metadata = {
        "supports": {
            "EAL": {
                "up": [
                    SupportPoint(line="EAL", track="up", chainage=121000.0),
                    SupportPoint(line="EAL", track="up", chainage=121100.0),
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

    summary, trace = compute_stagger_result_for_record(
        record=record,
        chart_rows=[],
        metadata=metadata,
        case_type="A",
    )

    assert summary.overall_result == "n/a"
    assert summary.trace_available is False
    assert "Incomplete support references for stagger span computation" in summary.remark
    assert trace["trace_status"] == "partial"
    assert trace["reference"]["spt_a"] is None
    assert trace["reference"]["spt_i"] == 121000.0
    assert trace["reference"]["spt_b"] == 121100.0
    assert trace["spans"] == {}


def test_compute_stagger_result_for_record_returns_na_when_support_list_is_empty():
    from app.core.calculation.stagger_service import compute_stagger_result_for_record

    record = SelectedSummaryRecord(
        id="A3",
        line="EAL",
        track="up",
        exception_type="Stagger Left",
        max_location=121010.0,
    )
    metadata = {
        "supports": {"EAL": {"up": []}},
        "wind_factor": {
            "EAL": {
                "kr": {"up": [RangeValue(0.0, 999999.0, 1.2)], "down": [RangeValue(0.0, 999999.0, 1.2)]},
                "ke": {"up": [RangeValue(0.0, 999999.0, 1.1)], "down": [RangeValue(0.0, 999999.0, 1.1)]},
                "kh": {"up": [RangeValue(0.0, 999999.0, 1.0)], "down": [RangeValue(0.0, 999999.0, 1.0)]},
            }
        },
        "constants": {"tension": 13.8},
    }

    summary, trace = compute_stagger_result_for_record(
        record=record,
        chart_rows=[],
        metadata=metadata,
        case_type="A",
    )

    assert summary.overall_result == "n/a"
    assert summary.trace_available is False
    assert "Incomplete support references for stagger span computation" in summary.remark
    assert trace["trace_status"] == "partial"
    assert trace["reference"] == {
        "chi": 121010.0,
        "spt_a": None,
        "spt_i": None,
        "spt_b": None,
    }
    assert trace["spans"] == {}
