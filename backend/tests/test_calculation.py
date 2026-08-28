"""Consolidated unit tests for the calculation module.

Covers:
- excel_parser: parse_wire_wear_sheet, parse_chart_data_sheet
- wear_calculator: calculate_wear_percentage, calculate_average_wear
- trend_analyzer: analyze_trend (no-action and recommendation logic)
"""
import pytest
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.metadata import MetadataManager
from app.core.calculation.excel_parser import (
    WireWearRecord,
    ChartDataRecord,
    parse_wire_wear_sheet,
    parse_chart_data_sheet,
    parse_stagger_chart_data_sheet,
)
from app.core.calculation.wear_calculator import (
    calculate_wear_percentage,
    calculate_average_wear,
)
from app.core.calculation.trend_analyzer import analyze_trend


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def wire_wear_df():
    return pd.DataFrame({
        'Run Date':       ['2026-01-01', '2026-01-01'],
        'ID':             ['W001', 'W002'],
        'Tension Length': ['H02', 'H04'],
        'FromM':          [1000.0, 2000.0],
        'ToM':            [1100.0, 2100.0],
        'MaxValue':       [10.5, 10.8],
        'Level':          ['L2', 'L1'],
        'ACTION':         [None, 'Keep monitoring'],
    })


@pytest.fixture
def chart_data_df():
    return pd.DataFrame({
        'task_run_date':  ['2026-01-01', '2026-01-01', '2026-02-01'],
        'Tension Length': ['H02', 'H02', 'H04'],
        'Chainage':       [1000.0, 1050.0, 2000.0],
        'wear_min':       [10.3, 10.5, float('nan')],
        'Track Type':     ['Tangent', 'Tangent', 'Curve'],
        'Overlap':        [None, None, 'Y'],
    })


@pytest.fixture
def chart_records_two_dates():
    """Two inspection dates for H02 — used in trend tests."""
    return [
        ChartDataRecord('2026-01-01', 'EAL', 'UP', '', 'T01', '1000', '1050', 'H02', 1000.0, 10.5, 'Tangent', None),
        ChartDataRecord('2026-01-01', 'EAL', 'UP', '', 'T01', '1000', '1050', 'H02', 1050.0, 10.3, 'Tangent', None),
        ChartDataRecord('2026-02-01', 'EAL', 'UP', '', 'T01', '1000', '1050', 'H02', 1000.0, 10.1, 'Tangent', None),
        ChartDataRecord('2026-02-01', 'EAL', 'UP', '', 'T01', '1000', '1050', 'H02', 1050.0, 9.9,  'Tangent', None),
    ]


# ─── parse_wire_wear_sheet ─────────────────────────────────────────────────────

def test_parse_wire_wear_sheet(wire_wear_df):
    records = parse_wire_wear_sheet(wire_wear_df)
    assert len(records) == 2
    assert all(isinstance(r, WireWearRecord) for r in records)
    assert records[0].exception_id == 'W001'
    assert records[0].tension_length == 'H02'
    assert records[0].level == 'L2'
    assert records[0].action is None
    assert records[1].action == 'Keep monitoring'


def test_parse_wire_wear_sheet_preserves_max_location_field():
    df = pd.DataFrame({
        'Run Date': ['2026-03-01'],
        'ID': ['W100'],
        'Tension Length': ['H02'],
        'FromM': [1000.0],
        'ToM': [1100.0],
        'MaxValue': [9.06],
        'MaxLocation': [1033.5],
        'Level': ['L2'],
        'ACTION': [None],
    })

    records = parse_wire_wear_sheet(df)

    assert records[0].max_location == pytest.approx(1033.5)


def test_parse_wire_wear_sheet_empty():
    df = pd.DataFrame(
        columns=['Run Date', 'ID', 'Tension Length', 'FromM', 'ToM', 'MaxValue', 'Level', 'ACTION']
    )
    assert parse_wire_wear_sheet(df) == []


# ─── parse_chart_data_sheet ────────────────────────────────────────────────────

def test_parse_chart_data_sheet(chart_data_df):
    """Rows with NaN wear_min must be dropped; valid rows parsed correctly."""
    records = parse_chart_data_sheet(chart_data_df)
    # H04 row has NaN wear_min — should be dropped
    assert len(records) == 2
    assert all(isinstance(r, ChartDataRecord) for r in records)
    assert records[0].task_run_date == '2026-01-01'
    assert records[0].tension_length == 'H02'
    assert records[0].wear_min == pytest.approx(10.3)


def test_parse_chart_data_sheet_dropna():
    df = pd.DataFrame({
        'task_run_date':  ['2026-01-01', '2026-01-01'],
        'Tension Length': ['H02', 'H04'],
        'Chainage':       [1000.0, 2000.0],
        'wear_min':       [10.3, float('nan')],
        'Track Type':     ['Tangent', 'Curve'],
        'Overlap':        [None, None],
    })
    records = parse_chart_data_sheet(df)
    assert len(records) == 1
    assert records[0].tension_length == 'H02'


def test_parse_chart_data_sheet_keeps_optional_defaults_when_columns_missing():
    df = pd.DataFrame({
        'task_run_date': ['2026-01-01'],
        'Tension Length': ['H02'],
        'Chainage': [1000.0],
        'wear_min': [10.3],
        'Track Type': ['Tangent'],
        'Overlap': [''],
    })

    records = parse_chart_data_sheet(df)

    assert records[0].line is None
    assert records[0].track is None
    assert records[0].section is None
    assert records[0].task_no == ''
    assert records[0].station_start == ''
    assert records[0].station_end == ''
    assert records[0].overlap is None


def test_parse_stagger_chart_data_sheet_extracts_chainage_and_channels():
    df = pd.DataFrame({
        'Chainage': [121000.0],
        'WHGT1': [5400.0],
        'WHGT2': [5390.0],
        'WHGT3': [5380.0],
        'WHGT4': [5410.0],
        'STG1': [120.0],
        'STG2': [118.0],
        'STG3': [122.0],
        'STG4': [121.0],
    })

    rows = parse_stagger_chart_data_sheet(df)

    assert rows[0]['chainage'] == 121000.0
    assert rows[0]['heights'] == [5400.0, 5390.0, 5380.0, 5410.0]
    assert rows[0]['staggers'] == [120.0, 118.0, 122.0, 121.0]


def test_metadata_manager_public_methods_keep_dataframe_shapes(tmp_path):
    metadata_path = tmp_path / 'metadata.xlsx'

    threshold_df = pd.DataFrame([
        {'Class': 'both', 'Track Type': 'both', 'Exc Type': 'Stagger L1', 'min': 480.0, 'max': None},
        {'Class': 'both', 'Track Type': 'both', 'Exc Type': 'Stagger L2', 'min': 400.0, 'max': None},
        {'Class': 'both', 'Track Type': 'both', 'Exc Type': 'Low Height L1', 'min': None, 'max': 4475.0},
    ])
    overlap_df = pd.DataFrame([
        {
            'Overlap FromM': '1,000.0',
            'Overlap ToM': '1,100.0',
            'Overlap': 'Y',
            'Tension Length': 'H02',
            'Track Type': 'Tangent',
        }
    ])
    boundary_df = pd.DataFrame([
        {'Line': 'EAL', 'Class': 'EAL', 'UP Track FromM': 1000.0, 'UP Track ToM': 1100.0, 'DN Track FromM': 2000.0, 'DN Track ToM': 2100.0}
    ])

    with pd.ExcelWriter(metadata_path, engine='openpyxl') as writer:
        threshold_df.to_excel(writer, sheet_name='threshold', index=False)
        overlap_df.to_excel(writer, sheet_name='EAL UP', index=False)
        boundary_df.to_excel(writer, sheet_name='Exception Boundarys', index=False)

    manager = MetadataManager(metadata_path)

    thresholds = manager.get_all_thresholds()
    overlaps = manager.get_overlap_intervals('EAL', 'Mainline', 'UP')
    boundaries = manager.get_boundaries_for_plot('EAL', 'UP Track', 'Mainline')

    assert isinstance(thresholds, pd.DataFrame)
    assert {'Class', 'Track Type', 'Exc Type'}.issubset(thresholds.columns)
    assert set(thresholds['Exc Type']) == {'Stagger Left', 'Stagger Right', 'Low Height'}

    assert isinstance(overlaps, pd.DataFrame)
    assert list(overlaps.columns) == ['Overlap', 'Tension Length']
    assert isinstance(overlaps.index, pd.IntervalIndex)
    assert overlaps.iloc[0]['Tension Length'] == 'H02'

    assert isinstance(boundaries, pd.DataFrame)
    assert list(boundaries.columns) == ['Class', 'FromM', 'ToM']
    assert boundaries.iloc[0].to_dict() == {'Class': 'EAL', 'FromM': 1000.0, 'ToM': 1100.0}


# ─── calculate_wear_percentage ─────────────────────────────────────────────────

def test_calculate_wear_percentage_zero():
    assert calculate_wear_percentage(0.0) == 0.0


def test_calculate_wear_percentage_full_wire():
    # 13.2 mm = full diameter, essentially no wear
    result = calculate_wear_percentage(13.2)
    assert result == pytest.approx(0.0, abs=1.0)


def test_calculate_wear_percentage_range():
    for r in [1.0, 6.6, 10.0, 12.0]:
        result = calculate_wear_percentage(r)
        assert 0.0 <= result <= 100.0


def test_calculate_wear_percentage_returns_rounded_float():
    result = calculate_wear_percentage(10.0)
    assert isinstance(result, float)
    assert result == round(result, 2)


# ─── calculate_average_wear ────────────────────────────────────────────────────

def test_calculate_average_wear(chart_records_two_dates):
    results = calculate_average_wear(chart_records_two_dates)
    assert len(results) == 1
    h02 = results[0]
    assert h02.tension_length == 'H02'
    expected_avg = (10.5 + 10.3 + 10.1 + 9.9) / 4
    assert h02.avg_wear_min == pytest.approx(expected_avg, abs=0.01)
    assert 0.0 <= h02.wear_percentage <= 100.0


def test_calculate_average_wear_empty():
    assert calculate_average_wear([]) == []


def test_calculate_average_wear_from_to_m(chart_records_two_dates):
    results = calculate_average_wear(chart_records_two_dates)
    h02 = results[0]
    assert h02.from_m == pytest.approx(1000.0)
    assert h02.to_m == pytest.approx(1050.0)


# ─── analyze_trend: no action required ────────────────────────────────────────

def test_analyze_trend_no_action():
    """When trend_next > L2_THRESHOLD (10.2), recommendation is 'no action required'."""
    # Values are high (11.x) and increasing — trend_next will exceed 10.2
    wire_wear = [
        WireWearRecord('2026-02-01', 'W001', 'H02', 1000.0, 1100.0, 11.5, 'L2', None),
    ]
    chart_data_by_date = {
        '2026-01-01': [
            ChartDataRecord('2026-01-01', 'EAL', 'UP', '', 'T01', '1000', '1100', 'H02', 1000.0, 11.0, 'Tangent', None),
        ],
        '2026-02-01': [
            ChartDataRecord('2026-02-01', 'EAL', 'UP', '', 'T01', '1000', '1100', 'H02', 1000.0, 11.5, 'Tangent', None),
        ],
    }
    results = analyze_trend(wire_wear, chart_data_by_date, line='EAL')
    assert len(results) == 1
    assert results[0].logic_1 is False
    assert results[0].recommendation == 'no action required'


# ─── analyze_trend: recommendation logic ──────────────────────────────────────

def test_analyze_trend_recommendation():
    """Decreasing trend crossing below 10.2 with large delta → 'verify on site'."""
    wire_wear = [
        WireWearRecord('2026-02-01', 'W001', 'H02', 1000.0, 1100.0, 10.1, 'L2', None),
    ]
    chart_data_by_date = {
        '2026-01-01': [
            ChartDataRecord('2026-01-01', 'EAL', 'UP', '', 'T01', '1000', '1100', 'H02', 1000.0, 10.5, 'Tangent', None),
        ],
        '2026-02-01': [
            ChartDataRecord('2026-02-01', 'EAL', 'UP', '', 'T01', '1000', '1100', 'H02', 1000.0, 10.1, 'Tangent', None),
        ],
    }
    results = analyze_trend(wire_wear, chart_data_by_date, line='EAL')
    assert len(results) == 1
    r = results[0]
    assert r.logic_1 is True
    assert r.recommendation in ('verify on site', 'confirmed valid L2')


def test_analyze_trend_filters_l2_no_action_only():
    """Records with action set or non-L2 level must be excluded."""
    wire_wear = [
        WireWearRecord('2026-02-01', 'W001', 'H02', 1000.0, 1100.0, 10.1, 'L2', 'Done'),
        WireWearRecord('2026-02-01', 'W002', 'H04', 2000.0, 2100.0, 10.8, 'L1', None),
    ]
    chart_data_by_date = {
        '2026-01-01': [
            ChartDataRecord('2026-01-01', 'EAL', 'UP', '', 'T01', '1000', '1100', 'H02', 1000.0, 10.5, 'Tangent', None),
            ChartDataRecord('2026-01-01', 'EAL', 'UP', '', 'T02', '2000', '2100', 'H04', 2000.0, 10.8, 'Curve', None),
        ],
        '2026-02-01': [
            ChartDataRecord('2026-02-01', 'EAL', 'UP', '', 'T01', '1000', '1100', 'H02', 1000.0, 10.1, 'Tangent', None),
            ChartDataRecord('2026-02-01', 'EAL', 'UP', '', 'T02', '2000', '2100', 'H04', 2000.0, 10.9, 'Curve', None),
        ],
    }
    results = analyze_trend(wire_wear, chart_data_by_date, line='EAL')
    assert results == []


def test_analyze_trend_empty():
    assert analyze_trend([], {}, line='EAL') == []
