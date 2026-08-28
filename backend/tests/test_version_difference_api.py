import io

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from app.api.endpoints import analysis, version_difference
from app.main import app


client = TestClient(app)
EXCEL_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _workbook(
    *,
    marker: float = 0.0,
    include_chart: bool = True,
    metrics=("height", "stagger", "wear"),
) -> io.BytesIO:
    output = io.BytesIO()
    chainage = np.arange(100.0, 135.0, 0.25)
    chart = pd.DataFrame({"Chainage": chainage, "Marker": marker})
    for metric_index, metric in enumerate(metrics):
        for channel in range(1, 5):
            chart[f"{metric}{channel}"] = (
                np.sin((chainage + marker) / (3 + channel))
                + metric_index * 20
                + channel
            )

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        pd.DataFrame({"ID": [f"E-{marker}"]}).to_excel(
            writer, sheet_name="Low Height", index=False
        )
        if include_chart:
            chart.to_excel(writer, sheet_name="ChartData", index=False)
    output.seek(0)
    return output


def _file(filename: str, content: io.BytesIO):
    return filename, content, EXCEL_MEDIA_TYPE


def test_two_files_return_one_previous_1_comparison_in_explicit_role_order():
    response = client.post(
        "/api/analyze/version-difference",
        files={
            "latest": _file("20260101_named_older.xlsx", _workbook(marker=0.0)),
            "previous_1": _file("20261231_named_newer.xlsx", _workbook(marker=1.0)),
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["latest_file"] == "20260101_named_older.xlsx"
    assert len(payload["comparisons"]) == 1
    comparison = payload["comparisons"][0]
    assert comparison["key"] == "previous_1"
    assert comparison["previous_file"] == "20261231_named_newer.xlsx"
    assert comparison["metrics"]["height"]["status"] == "ready"


def test_three_files_align_each_previous_cycle_independently(monkeypatch):
    calls = []

    def fake_build(latest_chart, previous_chart):
        calls.append((latest_chart["Marker"][0], previous_chart["Marker"][0]))
        return {
            "status": "ready",
            "reason": None,
            "step_m": 0.25,
            "max_shift_m": 50.0,
            "metrics": {},
        }

    monkeypatch.setattr(version_difference, "build_aligned_comparison", fake_build)
    response = client.post(
        "/api/analyze/version-difference",
        files={
            "latest": _file("latest.xlsx", _workbook(marker=10.0)),
            "previous_1": _file("previous-1.xlsx", _workbook(marker=20.0)),
            "previous_2": _file("previous-2.xlsx", _workbook(marker=30.0)),
        },
    )

    assert response.status_code == 200
    assert calls == [(10.0, 20.0), (10.0, 30.0)]
    comparisons = response.json()["comparisons"]
    assert [item["key"] for item in comparisons] == ["previous_1", "previous_2"]
    assert [item["previous_file"] for item in comparisons] == [
        "previous-1.xlsx",
        "previous-2.xlsx",
    ]


def test_five_files_align_each_previous_cycle_in_explicit_role_order(monkeypatch):
    calls = []

    def fake_build(latest_chart, previous_chart):
        calls.append((latest_chart["Marker"][0], previous_chart["Marker"][0]))
        return {
            "status": "ready",
            "reason": None,
            "step_m": 0.25,
            "max_shift_m": 50.0,
            "metrics": {},
        }

    monkeypatch.setattr(version_difference, "build_aligned_comparison", fake_build)
    response = client.post(
        "/api/analyze/version-difference",
        files={
            "latest": _file("latest.xlsx", _workbook(marker=10.0)),
            "previous_1": _file("previous-1.xlsx", _workbook(marker=20.0)),
            "previous_2": _file("previous-2.xlsx", _workbook(marker=30.0)),
            "previous_3": _file("previous-3.xlsx", _workbook(marker=40.0)),
            "previous_4": _file("previous-4.xlsx", _workbook(marker=50.0)),
        },
    )

    assert response.status_code == 200
    assert calls == [
        (10.0, 20.0),
        (10.0, 30.0),
        (10.0, 40.0),
        (10.0, 50.0),
    ]
    comparisons = response.json()["comparisons"]
    assert [item["key"] for item in comparisons] == [
        "previous_1",
        "previous_2",
        "previous_3",
        "previous_4",
    ]
    assert [item["previous_file"] for item in comparisons] == [
        "previous-1.xlsx",
        "previous-2.xlsx",
        "previous-3.xlsx",
        "previous-4.xlsx",
    ]


def test_optional_gap_preserves_the_previous_cycle_key():
    response = client.post(
        "/api/analyze/version-difference",
        files={
            "latest": _file("latest.xlsx", _workbook(marker=10.0)),
            "previous_1": _file("previous-1.xlsx", _workbook(marker=20.0)),
            "previous_3": _file("previous-3.xlsx", _workbook(marker=40.0)),
        },
    )

    assert response.status_code == 200
    comparisons = response.json()["comparisons"]
    assert [item["key"] for item in comparisons] == ["previous_1", "previous_3"]
    assert [item["previous_file"] for item in comparisons] == [
        "previous-1.xlsx",
        "previous-3.xlsx",
    ]


def test_missing_previous_chartdata_is_a_partial_result():
    response = client.post(
        "/api/analyze/version-difference",
        files={
            "latest": _file("latest.xlsx", _workbook()),
            "previous_1": _file("previous-1.xlsx", _workbook(marker=1.0)),
            "previous_2": _file(
                "previous-2.xlsx", _workbook(marker=2.0, include_chart=False)
            ),
        },
    )

    assert response.status_code == 200
    comparisons = response.json()["comparisons"]
    assert comparisons[0]["status"] == "ready"
    assert comparisons[1]["status"] == "unavailable"
    assert "previous_2" in comparisons[1]["reason"]
    assert comparisons[1]["metrics"]["height"]["difference"] == [[], [], [], []]


def test_missing_metric_only_marks_that_metric_unavailable():
    response = client.post(
        "/api/analyze/version-difference",
        files={
            "latest": _file("latest.xlsx", _workbook(metrics=("height", "wear"))),
            "previous_1": _file(
                "previous-1.xlsx", _workbook(marker=1.0, metrics=("height", "wear"))
            ),
        },
    )

    assert response.status_code == 200
    metrics = response.json()["comparisons"][0]["metrics"]
    assert metrics["height"]["status"] == "ready"
    assert metrics["stagger"]["status"] == "unavailable"
    assert metrics["wear"]["status"] == "ready"


def test_latest_without_chartdata_returns_role_specific_422():
    response = client.post(
        "/api/analyze/version-difference",
        files={
            "latest": _file("latest.xlsx", _workbook(include_chart=False)),
            "previous_1": _file("previous-1.xlsx", _workbook()),
        },
    )

    assert response.status_code == 422
    assert "latest" in response.json()["detail"]
    assert "ChartData" in response.json()["detail"]


def test_corrupt_and_unsupported_workbooks_identify_the_affected_role():
    corrupt = client.post(
        "/api/analyze/version-difference",
        files={
            "latest": _file("latest.xlsx", io.BytesIO(b"not an excel workbook")),
            "previous_1": _file("previous-1.xlsx", _workbook()),
        },
    )
    unsupported = client.post(
        "/api/analyze/version-difference",
        files={
            "latest": _file("latest.xlsx", _workbook()),
            "previous_1": ("previous-1.csv", io.BytesIO(b"a,b\n1,2"), "text/csv"),
        },
    )

    assert corrupt.status_code == 400
    assert "latest" in corrupt.json()["detail"]
    assert unsupported.status_code == 400
    assert "previous_1" in unsupported.json()["detail"]


def test_endpoint_does_not_use_history_compare_state_or_repeated_finder(monkeypatch):
    sentinel_results = pd.DataFrame({"id": ["unchanged"]})
    sentinel_files = ["unchanged.xlsx"]
    sentinel_params = {"date_str": "unchanged"}
    monkeypatch.setattr(analysis, "LAST_COMPARE_RESULTS", sentinel_results)
    monkeypatch.setattr(analysis, "LAST_COMPARE_FILES", sentinel_files)
    monkeypatch.setattr(analysis, "LAST_ANALYSIS_PARAMS", sentinel_params)

    class ForbiddenRepeatedFinder:
        def __init__(self):
            raise AssertionError("Version Difference must not invoke repeated matching")

    monkeypatch.setattr(analysis, "RepeatedExceptionFinder", ForbiddenRepeatedFinder)
    response = client.post(
        "/api/analyze/version-difference",
        files={
            "latest": _file("latest.xlsx", _workbook()),
            "previous_1": _file("previous-1.xlsx", _workbook(marker=1.0)),
        },
    )

    assert response.status_code == 200
    assert analysis.LAST_COMPARE_RESULTS is sentinel_results
    assert analysis.LAST_COMPARE_FILES is sentinel_files
    assert analysis.LAST_ANALYSIS_PARAMS is sentinel_params
