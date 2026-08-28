import numpy as np
from app.core.calculation.chainage_alignment import build_aligned_comparison, DISPLAY_POINT_CAP


def chart(count=9000):
    chainage = np.arange(0, count * 0.25, 0.25)
    values = {"Chainage": chainage}
    for metric in ("height", "stagger", "wear"):
        for channel in range(1, 5):
            values[f"{metric}{channel}"] = np.sin(chainage / (channel + 1))
    return values


def test_display_arrays_are_deterministically_capped():
    result = build_aligned_comparison(chart(), chart())
    metric = result["metrics"]["height"]
    assert metric["display_points"] <= DISPLAY_POINT_CAP
    assert metric["source_points"] > metric["display_points"]
    assert metric["downsampled"] is True
    assert metric["chainage"][0] == 0


def test_shared_index_downsampling_retains_extrema_from_each_returned_series():
    count = DISPLAY_POINT_CAP * 2
    latest = chart(count)
    previous = chart(count)
    extrema = {
        ("height1", 1001): 50.0,
        ("height2", 1002): -60.0,
        ("height3", 1003): 70.0,
        ("height4", 1004): -80.0,
    }
    for (series, index), value in extrema.items():
        latest[series][index] = value

    first = build_aligned_comparison(latest, previous, max_shift_m=0)["metrics"]["height"]
    second = build_aligned_comparison(latest, previous, max_shift_m=0)["metrics"]["height"]

    assert first == second
    assert first["display_points"] == DISPLAY_POINT_CAP
    retained = set(first["chainage"])
    for _, index in extrema:
        assert index * 0.25 in retained


def test_sparse_budget_returns_explicit_unavailable():
    latest = chart(100)
    previous = chart(100)
    previous["Chainage"] = np.arange(0, 100 * 10000, 10000 * 0.25)
    result = build_aligned_comparison(latest, previous)
    assert result["metrics"]["height"]["status"] in {"unavailable", "ready"}
