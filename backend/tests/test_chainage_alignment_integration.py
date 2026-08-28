from pathlib import Path

import pandas as pd
import pytest

from app.core.calculation.chainage_alignment import build_aligned_comparison


@pytest.mark.slow
def test_real_eal_u2_reports_produce_explainable_alignment():
    data_dir = (
        Path(__file__).resolve().parents[2]
        / "docs"
        / "test data"
        / "EAL"
        / "Version Test"
        / "EAL U2"
    )
    paths = [
        data_dir / "20260729_EAL_U2_FOT-TAP_Exception_Report.xlsx",
        data_dir / "20260730_EAL_U2new_FOT-TAP_Exception_Report.xlsx",
    ]
    if not all(path.exists() for path in paths):
        pytest.skip("EAL U2 Version Test reports are not available")

    charts = [
        pd.read_excel(path, sheet_name="ChartData").replace({pd.NA: None}).to_dict(orient="list")
        for path in paths
    ]
    result = build_aligned_comparison(charts[0], charts[1])

    assert result["status"] == "ready"
    assert result["step_m"] == 0.25
    for metric in ("height", "stagger", "wear"):
        metric_result = result["metrics"][metric]
        assert metric_result["status"] in {"ready", "unavailable"}
        if metric_result["status"] == "ready":
            assert -50 <= metric_result["shift_m"] <= 50
            assert metric_result["valid_points"] >= 100
            assert metric_result["overlap_length"] >= 25
        else:
            assert metric_result["reason"]
