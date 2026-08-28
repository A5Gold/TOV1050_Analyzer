import math

import numpy as np
import pytest

from app.core.calculation.chainage_alignment import build_aligned_comparison


def make_chart(chainage, value_at_chainage, *, metrics=("height", "stagger", "wear")):
    chart = {"Chainage": list(chainage)}
    for metric_index, metric in enumerate(metrics):
        for channel in range(1, 5):
            chart[f"{metric}{channel}"] = [
                value_at_chainage(float(x), metric_index, channel) for x in chainage
            ]
    return chart


def signal(x, metric_index, channel):
    return 20 * metric_index + 3 * channel + math.sin(x / 3.7) + 0.2 * math.cos(x / 1.9 + channel)


def test_recovers_known_positive_shift_and_is_order_independent():
    latest_chainage = np.arange(100.0, 175.0, 0.25)
    previous_chainage = latest_chainage - 2.5
    latest = make_chart(latest_chainage, signal)
    previous = make_chart(previous_chainage, lambda x, metric, channel: signal(x + 2.5, metric, channel))

    ascending = build_aligned_comparison(latest, previous)
    descending = build_aligned_comparison(
        {key: list(reversed(value)) for key, value in latest.items()},
        {key: list(reversed(value)) for key, value in previous.items()},
    )

    for metric in ("height", "stagger", "wear"):
        assert ascending["metrics"][metric]["shift_m"] == pytest.approx(2.5)
        assert descending["metrics"][metric]["shift_m"] == pytest.approx(2.5)
        assert descending["metrics"][metric]["difference"] == ascending["metrics"][metric]["difference"]


def test_difference_keeps_four_channels_separate():
    chainage = np.arange(0.0, 50.0, 0.25)
    latest = make_chart(chainage, lambda x, metric, channel: x + channel * 10)
    previous = make_chart(chainage, lambda x, metric, channel: x + channel * 10 - channel)

    result = build_aligned_comparison(latest, previous, max_shift_m=0)["metrics"]["height"]

    assert result["status"] == "ready"
    assert len(result["difference"]) == 4
    for channel, values in enumerate(result["difference"], start=1):
        assert {round(value, 8) for value in values if value is not None} == {float(channel)}


def test_null_nan_infinity_and_gap_remain_missing():
    chainage = np.arange(0.0, 50.0, 0.25)
    latest = make_chart(chainage, signal)
    previous = make_chart(chainage, signal)
    latest["height1"][40] = None
    latest["height1"][41] = np.nan
    previous["height1"][42] = np.inf
    previous["height1"][43] = -np.inf

    result = build_aligned_comparison(latest, previous, max_shift_m=0)["metrics"]["height"]
    assert result["status"] == "ready"
    assert result["difference"][0][40:44] == [None, None, None, None]
    assert all(value == pytest.approx(0) for value in result["difference"][0][44:48])


def test_duplicate_tick_uses_mean_of_finite_values():
    chainage = list(np.arange(0.0, 50.0, 0.25))
    latest = make_chart(chainage, signal)
    previous = make_chart(chainage, signal)
    duplicate_index = 20
    for key in list(latest):
        if key == "Chainage":
            latest[key].append(latest[key][duplicate_index])
        else:
            latest[key].append(latest[key][duplicate_index] + 2)

    result = build_aligned_comparison(latest, previous, max_shift_m=0)["metrics"]["height"]
    tick_index = result["chainage"].index(chainage[duplicate_index])
    assert result["difference"][0][tick_index] == pytest.approx(1.0)


def test_normalized_rmse_is_invariant_to_metric_units():
    chainage = np.arange(0.0, 75.0, 0.25)
    latest = make_chart(chainage, signal, metrics=("height",))
    previous = make_chart(
        chainage,
        lambda x, metric, channel: signal(x, metric, channel) + 0.3 * math.sin(x * 1.7 + channel),
        metrics=("height",),
    )
    scaled_latest = {key: ([value * 100 for value in values] if key != "Chainage" else values) for key, values in latest.items()}
    scaled_previous = {key: ([value * 100 for value in values] if key != "Chainage" else values) for key, values in previous.items()}

    original = build_aligned_comparison(latest, previous, max_shift_m=0)["metrics"]["height"]
    scaled = build_aligned_comparison(scaled_latest, scaled_previous, max_shift_m=0)["metrics"]["height"]

    assert scaled["rmse"] == pytest.approx(original["rmse"] * 100)
    assert scaled["normalized_rmse"] == pytest.approx(original["normalized_rmse"])


def test_coverage_guard_rejects_low_overlap_exact_match():
    rng = np.random.default_rng(12345)
    chainage = np.arange(0.0, 200.0, 0.25)
    values = rng.normal(size=len(chainage))
    latest = {"Chainage": chainage.tolist()}
    previous = {"Chainage": chainage.tolist()}
    for metric in ("height", "stagger", "wear"):
        for channel in range(1, 5):
            latest[f"{metric}{channel}"] = values.tolist()
            shifted = np.zeros_like(values)
            shifted[:600] = values[200:]
            shifted[600:] = rng.normal(size=200)
            previous[f"{metric}{channel}"] = shifted.tolist()

    result = build_aligned_comparison(latest, previous)["metrics"]["height"]

    assert result["status"] == "ready"
    assert result["shift_m"] != pytest.approx(50.0)
    assert result["valid_points"] >= 4 * 640


def test_deterministic_tie_break_prefers_zero_shift():
    chainage = np.arange(0.0, 75.0, 0.25)
    latest = make_chart(chainage, lambda x, metric, channel: 5.0)
    previous = make_chart(chainage, lambda x, metric, channel: 5.0)

    result = build_aligned_comparison(latest, previous)["metrics"]["height"]
    assert result["shift_m"] == 0.0


def test_insufficient_overlap_is_unavailable():
    chainage = np.arange(0.0, 20.0, 0.25)
    latest = make_chart(chainage, signal)
    previous = make_chart(chainage, signal)

    result = build_aligned_comparison(latest, previous)["metrics"]["height"]
    assert result["status"] == "unavailable"
    assert "100 paired points" in result["reason"]


def test_partial_metric_unavailable_does_not_hide_ready_metrics():
    chainage = np.arange(0.0, 50.0, 0.25)
    latest = make_chart(chainage, signal, metrics=("height", "wear"))
    previous = make_chart(chainage, signal, metrics=("height", "wear"))

    result = build_aligned_comparison(latest, previous, max_shift_m=0)
    assert result["status"] == "ready"
    assert result["metrics"]["height"]["status"] == "ready"
    assert result["metrics"]["stagger"]["status"] == "unavailable"
    assert result["metrics"]["wear"]["status"] == "ready"
