"""Tests for trend_analyzer module - Task 4 rewrite (TDD)"""
import pytest
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.calculation.excel_parser import ChartDataRecord
from app.core.calculation.trend_analyzer import (
    TrendResult,
    calculate_trend,
    calculate_trend_points,
    determine_recommendation,
    analyze_trend,
    L2_THRESHOLD,
    TOLERANCE,
)


# ─── calculate_trend ──────────────────────────────────────────────────────────

def test_calculate_trend_basic():
    """Known linear data"""
    days = [0, 30, 60, 90]
    values = [9.0, 9.3, 9.6, 9.9]
    slope, intercept = calculate_trend(days, values)
    assert slope == pytest.approx(0.01, abs=0.001)
    assert intercept == pytest.approx(9.0, abs=0.1)

def test_calculate_trend_single_point():
    slope, intercept = calculate_trend([0], [9.5])
    assert slope == pytest.approx(0.0)
    assert intercept == pytest.approx(9.5)

def test_calculate_trend_empty():
    slope, intercept = calculate_trend([], [])
    assert slope == pytest.approx(0.0)
    assert intercept == pytest.approx(0.0)

def test_calculate_trend_ignores_nan():
    import math
    days = [0, 30, 60, 90]
    values = [9.0, float('nan'), 9.6, 9.9]
    slope, intercept = calculate_trend(days, values)
    assert not math.isnan(slope)


# ─── calculate_trend_points ───────────────────────────────────────────────────

def test_calculate_trend_points_count():
    points = calculate_trend_points(0.01, 9.0, base_day=0, n=6)
    assert len(points) == 6

def test_calculate_trend_points_no_negative():
    points = calculate_trend_points(-1.0, 1.0, base_day=0, n=6)
    for p in points:
        assert p >= 0.0

def test_calculate_trend_points_rounded():
    points = calculate_trend_points(0.01, 9.0, base_day=0, n=3)
    for p in points:
        assert p == round(p, 2)


# ─── determine_recommendation ─────────────────────────────────────────────────

def test_recommendation_no_action():
    logic_1, logic_2, rec = determine_recommendation(10.5, L2_THRESHOLD + 0.5)
    assert logic_1 is False
    assert rec == 'no action required'

def test_recommendation_verify_on_site():
    max_val = 10.0
    trd_pt = L2_THRESHOLD - 0.5
    logic_1, logic_2, rec = determine_recommendation(max_val, trd_pt)
    assert logic_1 is True
    if abs(max_val - trd_pt) > TOLERANCE:
        assert rec == 'verify on site'

def test_recommendation_confirmed_valid():
    trd_pt = L2_THRESHOLD - 0.5
    max_val = trd_pt + TOLERANCE * 0.5
    logic_1, logic_2, rec = determine_recommendation(max_val, trd_pt)
    assert logic_1 is True
    assert logic_2 is False
    assert rec == 'confirmed valid L2'


# ─── TrendResult ──────────────────────────────────────────────────────────────

def test_trend_result_has_required_fields():
    r = TrendResult(
        tension_length='H02', from_m=1000.0, to_m=1100.0,
        level='L2',
        dates=['2026-01-01', '2026-02-01'],
        record_points=[10.0, 9.9],
        trend_points=[10.0, 9.9],
        trend_next=9.8, logic_1=True, logic_2=False,
        recommendation='confirmed valid L2',
    )
    assert r.tension_length == 'H02'
    assert r.level == 'L2'
    assert r.trend_next == pytest.approx(9.8)
    assert len(r.trend_points) == 2


# ─── analyze_trend ────────────────────────────────────────────────────────────

from app.core.calculation.excel_parser import WireWearRecord
from app.core.calculation.excel_parser import RepeatedSummaryRecord

@pytest.fixture
def multi_date_wire_wear():
    return [
        WireWearRecord('2026-02-01', 'W001', 'H02', 1000.0, 1050.0, 10.1, 'L2', None),
    ]

@pytest.fixture
def multi_date_chart_data():
    return {
        '2026-01-01': [
            ChartDataRecord('2026-01-01', 'EAL', 'UP', '', 'T01', '1000', '1050', 'H02', 1000.0, 10.5, 'Tangent', None),
            ChartDataRecord('2026-01-01', 'EAL', 'UP', '', 'T01', '1000', '1050', 'H02', 1050.0, 10.3, 'Tangent', None),
        ],
        '2026-02-01': [
            ChartDataRecord('2026-02-01', 'EAL', 'UP', '', 'T01', '1000', '1050', 'H02', 1000.0, 10.1, 'Tangent', None),
            ChartDataRecord('2026-02-01', 'EAL', 'UP', '', 'T01', '1000', '1050', 'H02', 1050.0, 9.9,  'Tangent', None),
        ],
    }

def test_analyze_trend_groups_by_tl(multi_date_wire_wear, multi_date_chart_data):
    results = analyze_trend(multi_date_wire_wear, multi_date_chart_data, line='EAL')
    tls = {r.tension_length for r in results}
    assert 'H02' in tls

def test_analyze_trend_needs_l2_no_action():
    """TL with action set must be excluded."""
    wire_wear = [WireWearRecord('2026-02-01', 'W001', 'H04', 2000.0, 2100.0, 10.8, 'L2', 'Done')]
    chart_data = {
        '2026-01-01': [ChartDataRecord('2026-01-01', 'EAL', 'UP', '', 'T02', '2000', '2100', 'H04', 2000.0, 10.8, 'Curve', 'Y')],
        '2026-02-01': [ChartDataRecord('2026-02-01', 'EAL', 'UP', '', 'T02', '2000', '2100', 'H04', 2000.0, 10.9, 'Curve', 'Y')],
    }
    results = analyze_trend(wire_wear, chart_data, line='EAL')
    assert all(r.tension_length != 'H04' for r in results)

def test_analyze_trend_record_points_sorted(multi_date_wire_wear, multi_date_chart_data):
    results = analyze_trend(multi_date_wire_wear, multi_date_chart_data, line='EAL')
    h02 = next(r for r in results if r.tension_length == 'H02')
    assert '2026-01-01' in h02.dates
    assert '2026-02-01' in h02.dates
    assert len(h02.record_points) == 2

def test_analyze_trend_trend_points_count(multi_date_wire_wear, multi_date_chart_data):
    results = analyze_trend(multi_date_wire_wear, multi_date_chart_data, line='EAL')
    h02 = next(r for r in results if r.tension_length == 'H02')
    assert len(h02.trend_points) == 2

def test_analyze_trend_recommendation_valid(multi_date_wire_wear, multi_date_chart_data):
    results = analyze_trend(multi_date_wire_wear, multi_date_chart_data, line='EAL')
    h02 = next(r for r in results if r.tension_length == 'H02')
    assert h02.recommendation in ('confirmed valid L2', 'verify on site', 'no action required')

def test_analyze_trend_empty():
    assert analyze_trend([], {}, line='EAL') == []


def test_analyze_trend_without_repeated_report_keeps_max_location_empty():
    wire_wear = [
        WireWearRecord('2026-02-01', 'W001', 'H02', 1000.0, 1050.0, 10.1, 'L2', None, 1000.0),
    ]
    chart_data = {
        '2026-02-01': [
            ChartDataRecord('2026-02-01', 'EAL', 'UP', '', 'T01', '1000', '1050', 'H02', 1000.0, 10.1, 'Tangent', None),
        ],
    }

    results = analyze_trend(wire_wear, chart_data, line='EAL')

    assert len(results) == 1
    assert results[0].max_value == pytest.approx(10.1)
    assert results[0].max_location == pytest.approx(1000.0)


def test_analyze_trend_with_repeated_report_uses_max_location_from_repeated_report():
    wire_wear = [
        WireWearRecord('2026-02-01', 'W001', 'H02', 1000.0, 1050.0, 10.1, 'L2', None, 1000.0),
    ]
    chart_data = {
        '2026-02-01': [
            ChartDataRecord('2026-02-01', 'EAL', 'UP', '', 'T01', '1000', '1050', 'H02', 1000.0, 10.1, 'Tangent', None),
        ],
    }
    repeated = [
        RepeatedSummaryRecord('W001', 1000.0, 1050.0, '2026-02-01', 10.1, 1033.5, 'Wire Wear', 'L2'),
    ]

    results = analyze_trend(wire_wear, chart_data, line='EAL', repeated_records=repeated)

    assert len(results) == 1
    assert results[0].max_location == pytest.approx(1033.5)


def test_analyze_trend_with_empty_repeated_report_returns_no_results():
    wire_wear = [
        WireWearRecord('2026-02-01', 'W001', 'H02', 1000.0, 1050.0, 10.1, 'L2', None),
        WireWearRecord('2026-02-01', 'W002', 'H03', 1100.0, 1150.0, 10.0, 'L2', None),
    ]
    chart_data = {
        '2026-02-01': [
            ChartDataRecord('2026-02-01', 'EAL', 'UP', '', 'T01', '1000', '1050', 'H02', 1000.0, 10.1, 'Tangent', None),
            ChartDataRecord('2026-02-01', 'EAL', 'UP', '', 'T01', '1100', '1150', 'H03', 1100.0, 10.0, 'Tangent', None),
        ],
    }

    results = analyze_trend(wire_wear, chart_data, line='EAL', repeated_records=[])

    assert results == []
