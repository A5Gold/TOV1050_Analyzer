from datetime import date
import json
import math

import pytest

from app.core.calculation.wear_cycle_analytics import (
    HistoryPoint,
    build_dashboard,
    build_projection,
    build_remaining_life,
    fit_tl_trend,
)
from app.core.calculation.wear_calculator import calculate_wear_percentage


def _record(
    line_group: str,
    tension_length: str,
    cycle_date: str,
    thickness: float,
    line_class: str | None = None,
) -> dict:
    return {
        "line_group": line_group,
        "line_class": line_class or line_group,
        "tension_length": tension_length,
        "cycle_date": cycle_date,
        "avg_wear_min": thickness,
        "wear_percentage": 10.0 + (12.0 - thickness),
        "track": "UP",
        "from_m": 100.0,
        "to_m": 200.0,
    }


def test_fit_tl_trend_uses_mean_per_date_and_all_history():
    trend = fit_tl_trend(
        [
            HistoryPoint(date(2024, 1, 1), 12.0, 10.0),
            HistoryPoint(date(2025, 1, 1), 11.1, 10.9),
            HistoryPoint(date(2025, 1, 1), 10.9, 11.1),
            HistoryPoint(date(2026, 1, 1), 10.0, 12.0),
        ]
    )

    assert trend.status == "eligible"
    assert trend.observation_count == 3
    assert trend.latest_cycle_date == date(2026, 1, 1)
    assert trend.mm_per_year == pytest.approx(1.0, abs=0.02)
    assert trend.wear_percent_per_year == pytest.approx(
        calculate_wear_percentage(11.0) - calculate_wear_percentage(12.0), abs=0.02
    )
    assert trend.r_squared == pytest.approx(1.0)


def test_fit_tl_trend_marks_insufficient_and_non_positive_rates():
    insufficient = fit_tl_trend([HistoryPoint(date(2026, 1, 1), 11.0, 10.0)])
    non_positive = fit_tl_trend(
        [
            HistoryPoint(date(2025, 1, 1), 10.0, 10.0),
            HistoryPoint(date(2026, 1, 1), 11.0, 9.0),
        ]
    )

    assert insufficient.status == "insufficient_data"
    assert insufficient.mm_per_year is None
    assert non_positive.status == "non_positive_rate"
    assert non_positive.mm_per_year is None
    assert non_positive.wear_percent_per_year is None


def test_fit_tl_trend_ignores_non_finite_points_and_returns_null_rate():
    trend = fit_tl_trend([
        HistoryPoint(date(2025, 1, 1), math.nan, math.nan),
        HistoryPoint(date(2026, 1, 1), 11.0, 10.0),
    ])

    assert trend.status == "insufficient_data"
    assert trend.observation_count == 1
    assert trend.mm_per_year is None
    assert trend.wear_percent_per_year is None


def test_dashboard_accepts_none_as_all_and_ranks_minimum_by_positive_mm_rate():
    records = [
        _record("EAL", "1", "2024-01-01", 12.0),
        _record("EAL", "1", "2025-01-01", 11.0),
        _record("EAL", "2", "2024-01-01", 7.0),
        _record("EAL", "2", "2025-01-01", 6.5),
        _record("TML", "1", "2024-01-01", 12.0),
        _record("TML", "1", "2025-01-01", 10.0),
    ]

    dashboard = build_dashboard(records, None)

    assert {row["line_group"] for row in dashboard["top_current_wear"]} == {"EAL", "TML"}
    assert dashboard["top_min_rate"][0]["tension_length"] == "2"
    assert (
        dashboard["top_min_rate"][0]["percent_per_year"]
        == dashboard["top_min_rate"][0]["wear_rate_percent_per_year"]
    )


def test_dashboard_ranks_maximum_by_mm_loss_rate_not_nonlinear_wear_percentage():
    records = [
        _record("EAL", "fast-mm", "2024-01-01", 13.0),
        _record("EAL", "fast-mm", "2025-01-01", 12.0),
        _record("EAL", "fast-percent", "2024-01-01", 8.0),
        _record("EAL", "fast-percent", "2025-01-01", 7.5),
    ]

    dashboard = build_dashboard(records, "EAL")

    assert dashboard["top_max_rate"][0]["tension_length"] == "fast-mm"


def test_dashboard_and_projection_do_not_mix_eal_and_lmc_trends():
    records = [
        _record("EAL", "28", "2024-01-01", 12.0, "EAL"),
        _record("EAL", "28", "2025-01-01", 11.0, "EAL"),
        _record("EAL", "28", "2024-01-01", 10.0, "LMC"),
        _record("EAL", "28", "2025-01-01", 9.8, "LMC"),
    ]

    dashboard = build_dashboard(records, "EAL")
    dashboard_rows = dashboard["top_max_rate"]
    projection = build_projection(records, threshold_mm=9.0, as_of=date(2025, 6, 1))
    projected_rows = [
        row
        for bucket in projection["line_groups"]["EAL"]["year_buckets"]
        for row in bucket["records"]
    ]

    assert {(row["line_class"], row["observation_count"]) for row in dashboard_rows} == {
        ("EAL", 2),
        ("LMC", 2),
    }
    assert {row["line_class"] for row in projected_rows} == {"EAL", "LMC"}


def test_projection_uses_shared_threshold_and_synchronized_bucket_records():
    records = [
        _record("EAL", "1", "2024-01-01", 12.0),
        _record("EAL", "1", "2025-01-01", 11.0),
        _record("EAL", "2", "2024-01-01", 8.0),
        _record("EAL", "2", "2025-01-01", 7.5),
        _record("TML", "1", "2025-01-01", 12.0),
    ]

    projection = build_projection(records, threshold_mm=10.0, as_of=date(2025, 6, 1))
    eal = projection["line_groups"]["EAL"]

    assert projection["threshold_mm"] == 10.0
    assert projection["threshold_percentage"] > 0
    assert eal["already_at_threshold"][0]["tension_length"] == "2"
    assert eal["insufficient_data"] == []
    bucketed = [record for bucket in eal["year_buckets"] for record in bucket["records"]]
    assert [record["tension_length"] for record in bucketed] == ["1"]
    assert sum(bucket["count"] for bucket in eal["year_buckets"]) == len(bucketed)


def test_projection_reports_fitted_crossing_before_as_of_in_already_threshold_list():
    records = [
        _record("EAL", "1", "2024-01-01", 12.0),
        _record("EAL", "1", "2025-01-01", 11.0),
    ]

    projection = build_projection(records, threshold_mm=10.5, as_of=date(2026, 7, 1))
    eal = projection["line_groups"]["EAL"]

    assert eal["already_at_threshold"][0]["tension_length"] == "1"
    assert eal["already_at_threshold"][0]["projected_crossing_date"] < "2026-07-01"
    assert all(bucket["count"] == 0 for bucket in eal["year_buckets"])


def test_remaining_life_classifies_statuses_and_defaults_to_worst_eligible_curve():
    records = [
        _record("EAL", "slow", "2024-01-01", 12.0),
        _record("EAL", "slow", "2025-01-01", 11.5),
        _record("EAL", "fast", "2024-01-01", 12.0),
        _record("EAL", "fast", "2025-01-01", 10.0),
        _record("EAL", "flat", "2024-01-01", 10.0),
        _record("EAL", "flat", "2025-01-01", 10.5),
        _record("TML", "one-point", "2025-01-01", 11.0),
    ]

    result = build_remaining_life(records, threshold_mm=10.2, as_of=date(2026, 1, 1))
    by_tl = {row["tension_length"]: row for row in result["rows"]}

    assert by_tl["slow"]["trend_status"] == "eligible"
    assert by_tl["slow"]["remaining_days"] is not None
    assert by_tl["slow"]["curve"][-1]["remaining_days"] == 0
    assert by_tl["fast"]["trend_status"] == "already_at_threshold"
    assert by_tl["fast"]["remaining_days"] == 0
    assert by_tl["flat"]["trend_status"] == "non_positive_rate"
    assert by_tl["one-point"]["trend_status"] == "insufficient_data"
    assert [row["tension_length"] for row in result["default_rows"]] == ["slow"]


def test_remaining_life_ignores_empty_and_non_finite_records():
    result = build_remaining_life([
        {"line_group": "EAL", "tension_length": "empty", "cycle_date": None, "avg_wear_min": None},
        {"line_group": "TML", "tension_length": "nan", "cycle_date": "2025-01-01", "avg_wear_min": float("nan")},
    ], threshold_mm=10.2, as_of=date(2026, 1, 1))

    assert result["threshold_mm"] == 10.2
    assert {row["tension_length"] for row in result["rows"]} == {"empty", "nan"}
    assert all(row["trend_status"] == "insufficient_data" for row in result["rows"])
    assert result["default_rows"] == []


def test_projection_keeps_extreme_crossing_outside_horizon_json_safe():
    records = [
        _record("EAL", "slow", "2024-01-01", 12.0),
        _record("EAL", "slow", "2025-01-01", 11.999999),
        {
            "line_group": "EAL",
            "line_class": "EAL",
            "tension_length": "invalid",
            "cycle_date": "2025-01-01",
            "avg_wear_min": math.nan,
            "wear_percentage": math.inf,
        },
    ]

    projection = build_projection(records, threshold_mm=10.2, as_of=date(2026, 8, 8))
    eal = projection["line_groups"]["EAL"]

    assert eal["outside_horizon"][0]["tension_length"] == "slow"
    assert eal["outside_horizon"][0]["projected_crossing_date"] is None
    assert eal["insufficient_data"][0]["tension_length"] == "invalid"
    json.dumps(projection, allow_nan=False)


def test_projection_empty_and_in_horizon_crossing_are_serializable():
    assert build_projection([], threshold_mm=10.2, as_of=date(2026, 8, 8))[
        "line_groups"
    ]["EAL"]["year_buckets"]

    records = [
        _record("EAL", "soon", "2025-01-01", 12.0),
        _record("EAL", "soon", "2026-01-01", 11.0),
    ]
    projection = build_projection(records, threshold_mm=10.2, as_of=date(2025, 1, 1))
    bucketed = [
        record
        for bucket in projection["line_groups"]["EAL"]["year_buckets"]
        for record in bucket["records"]
    ]

    assert bucketed[0]["tension_length"] == "soon"
    assert bucketed[0]["projected_crossing_date"] is not None
    json.dumps(projection, allow_nan=False)
