import pandas as pd
import numpy as np

from app.core.chart_sampling import build_chart_payload


def test_envelope_keeps_isolated_extrema_and_requested_chainage():
    frame = pd.DataFrame(
        {
            "Chainage": list(range(10)),
            "height1": [1, 1, 1, 1, 99, 1, 1, 1, 1, 1],
            "stagger1": [0, 0, -40, 0, 0, 0, 0, 0, 0, 0],
            "wear1": [3] * 10,
        }
    )
    payload, resolution = build_chart_payload(
        frame,
        frame.columns,
        max_points=3,
        preserve_chainage=[8],
    )

    assert resolution["source_points"] == 10
    assert resolution["strategy"] == "min_max_envelope"
    assert 99 in payload["height1"]
    assert -40 in payload["stagger1"]
    assert 8 in payload["Chainage"]


def test_small_frames_remain_raw_for_zoom_detail():
    frame = pd.DataFrame({"Chainage": [100, 101], "height1": [5, 6]})
    payload, resolution = build_chart_payload(frame, frame.columns, max_points=6000, from_m=101, to_m=101)

    assert payload == {"Chainage": [101], "height1": [6]}
    assert resolution["strategy"] == "raw"


def test_point_budget_counts_rows_and_ignores_provenance_extrema():
    rng = np.random.default_rng(23)
    frame = pd.DataFrame({"Chainage": np.arange(1200), "height1": rng.normal(size=1200)})
    baseline, _ = build_chart_payload(frame, frame.columns, max_points=120)
    frame["height1_source_row"] = rng.permutation(np.arange(1200))
    frame["height1_valid_count"] = rng.integers(1, 11, size=1200)
    payload, resolution = build_chart_payload(frame, frame.columns, max_points=120)
    assert payload["Chainage"] == baseline["Chainage"]
    assert resolution["returned_points"] <= 120
    assert resolution["bucket_count"] == 30


def test_preserves_specific_group_at_duplicate_chainage():
    frame = pd.DataFrame({
        "Chainage": [8.] * 100, "group_id": np.arange(100),
        "height1": [1.] * 100,
    })
    payload, _ = build_chart_payload(frame, frame.columns, max_points=8, preserve_group_ids=[57])
    assert 57 in payload["group_id"]


def test_preserves_segment_edges_and_nonfinite_gap_edges():
    frame = pd.DataFrame({
        "Chainage": np.arange(100), "segment_id": [None] * 35 + [1] * 65,
        "height1": [1.] * 43 + [np.nan, np.inf, -np.inf] + [1.] * 54,
    })
    payload, resolution = build_chart_payload(frame, frame.columns, max_points=8)
    assert {34, 35, 42, 43, 45, 46}.issubset(payload["Chainage"])
    for chainage in (43, 45):
        assert payload["height1"][payload["Chainage"].index(chainage)] is None
    assert resolution["mandatory_points"] >= 8


def test_nonfinite_chainage_is_excluded_and_values_json_safe():
    frame = pd.DataFrame({"Chainage": [1, 2, np.inf], "height1": [np.inf, -np.inf, 1.]})
    payload, _ = build_chart_payload(frame, frame.columns)
    assert payload == {"Chainage": [1., 2.], "height1": [None, None]}


def test_nullable_chainage_and_measurements_do_not_mutate_source():
    frame = pd.DataFrame({
        "Chainage": pd.Series([1, None, 3], dtype="Float64"),
        "height1": pd.Series([None, 2, 3], dtype="Float64"),
    })
    before = frame.copy(deep=True)
    payload, _ = build_chart_payload(frame, frame.columns, from_m=0, to_m=3)
    assert payload == {"Chainage": [1., 3.], "height1": [None, 3.]}
    pd.testing.assert_frame_equal(frame, before)
