import numpy as np
import pandas as pd
import pytest

from app.core.chainage_aggregation import aggregate_chainage
from app.core.chart_sampling import build_mean_chart_payload, build_chart_payload


@pytest.mark.parametrize("count", [2, 10, 11])
def test_finite_channel_statistics_and_original_frame_are_preserved(count):
    frame = pd.DataFrame({"Chainage": [100.125] * count,
                          "height1": np.arange(count, dtype=float),
                          "stagger1": [float("inf"), float("nan")] + [None] * (count - 2),
                          "wear1": [float("-inf"), 12] + [None] * (count - 2),
                          "SampleCount": range(40, 40 + count),
                          "source_row_number": range(200, 200 + count)})
    original = frame.copy(deep=True)
    mean, metadata = aggregate_chainage(frame)
    pd.testing.assert_frame_equal(frame, original)
    assert len(mean) == 1
    row = mean.iloc[0]
    assert row.height1 == (count - 1) / 2
    assert (row.height1_min, row.height1_max, row.height1_count) == (0, count - 1, count)
    assert pd.isna(row.stagger1) and row.stagger1_count == 0
    assert pd.isna(row.stagger1_min) and pd.isna(row.stagger1_max)
    assert row.wear1 == 12 and row.wear1_count == 1
    assert row.SampleCount_first == 40 and row.SampleCount_last == 39 + count
    assert row.source_row_first == 200 and row.source_row_last == 199 + count
    assert row.sample_count == count
    assert metadata["raw_points"] == count and metadata["grouped_points"] == 1


def test_metadata_context_and_counter_pass_boundaries_with_nonadjacent_revisits():
    frame = pd.DataFrame({"Chainage": [1, 2, 1, 1, 1, 1], "height1": [1, 2, 5, 7, 9, 11],
                          "Class": ["A", "A", "A", "B", "A", "A"],
                          "track": ["UT", "UT", "UT", "UT", "DT", "UT"],
                          "SampleCount": [10, 11, 12, 13, 14, 1]})
    mean, _ = aggregate_chainage(frame)
    assert mean.height1.tolist() == [3, 2, 7, 9, 11]
    assert mean.source_row_first.tolist() == [1, 2, 4, 5, 6]
    assert mean.source_row_last.tolist() == [3, 2, 4, 5, 6]
    assert mean.pass_id.tolist() == [0, 0, 0, 0, 1]
    no_counter, _ = aggregate_chainage(frame.drop(columns=["SampleCount"]))
    assert no_counter.iloc[0].height1 == pytest.approx(17 / 3)


def test_channel_derived_extrema_and_raw_spike_survive_mean_overview_sampling():
    frame = pd.DataFrame({"Chainage": np.repeat(np.arange(40), 10), "height1": [4500.] * 400,
                          "height2": [4600.] * 400, "stagger1": [0.] * 400})
    frame.loc[173, "height1"] = 5000
    frame.loc[173, "stagger1"] = 1000
    original = frame.copy(deep=True)
    mean, _ = aggregate_chainage(frame)
    assert mean.loc[17, "height_max"] == 4600
    assert mean.loc[17, "stg_max"] == 100
    payload, resolution = build_mean_chart_payload(frame, ["Chainage", "height1", "stagger1"], max_points=2)
    selected = payload["Chainage"].index(17)
    assert payload["height1_max"][selected] == 5000
    assert payload["stagger1_max"][selected] == 1000
    assert payload["sample_count"][selected] == 10
    assert resolution["raw_points"] == 400 and resolution["grouped_points"] == 40
    assert resolution["aggregation"] == "chainage_mean"
    assert resolution["aggregation_version"] == "exact_chainage_channel_mean_v1"
    pd.testing.assert_frame_equal(frame, original)


def test_nearest_chainage_tie_uses_first_source_position_and_keeps_source_order():
    frame = pd.DataFrame({"Chainage": [4, 1, 3, 0], "height1": [1, 1, 1, 1]})
    payload, _ = build_chart_payload(frame, frame.columns, max_points=1, preserve_chainage=[2, np.nan])
    assert payload["Chainage"] == [4, 1, 0]


def test_empty_and_invalid_coordinate_rows_do_not_merge():
    frame = pd.DataFrame({"Chainage": [np.nan, np.nan], "height1": [1., 3.]})
    mean, _ = aggregate_chainage(frame)
    assert mean.height1.tolist() == [1, 3]
    empty, metadata = aggregate_chainage(frame.iloc[:0])
    assert empty.empty and metadata["grouped_points"] == 0


@pytest.mark.parametrize("counter", ["SampleCount", "SampleCount [n.]"])
def test_native_csv_counter_alias_splits_resets_and_preserves_ranges(counter):
    frame = pd.DataFrame({"Chainage": [1., 1., 1., 1., 2., 1.],
                          "height1": [2., 4., 20., 30., 50., 40.],
                          counter: ["100", "101", "1", "2", "3", "4"],
                          "source_row_number": [201, 202, 203, 204, 205, 206]})
    original = frame.copy(deep=True)
    mean, metadata = aggregate_chainage(frame)
    assert mean.height1.tolist() == [3., 30., 50.]
    assert mean.pass_id.tolist() == [0, 1, 1]
    assert mean.SampleCount_first.tolist() == ["100", "1", "3"]
    assert mean.SampleCount_last.tolist() == ["101", "4", "3"]
    assert mean.source_row_first.tolist() == [201, 203, 205]
    assert mean.source_row_last.tolist() == [202, 206, 205]
    assert mean.sample_count.tolist() == [2, 3, 1]
    assert metadata["sample_counter_column"] == counter
    pd.testing.assert_frame_equal(frame, original)


def test_nonfinite_sample_counters_do_not_create_passes_and_canonical_takes_precedence():
    frame = pd.DataFrame({"Chainage": [1.] * 5, "height1": range(5),
                          "SampleCount": [10., np.inf, np.nan, 11., 1.],
                          "SampleCount [n.]": [5, 4, 3, 2, 1]})
    mean, metadata = aggregate_chainage(frame)
    assert mean.pass_id.tolist() == [0, 1]
    assert mean.sample_count.tolist() == [4, 1]
    assert metadata["sample_counter_column"] == "SampleCount"
