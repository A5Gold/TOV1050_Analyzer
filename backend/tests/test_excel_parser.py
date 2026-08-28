"""Tests for excel_parser module - Task 0 TDD"""
import pytest
import pandas as pd
import io
import sys, os
from pathlib import Path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.calculation.excel_parser import (
    WireWearRecord,
    ChartDataRecord,
    RepeatedSummaryRecord,
    parse_wire_wear_sheet,
    parse_chart_data_sheet,
    parse_exception_report,
    parse_repeated_summary_sheet,
)


# ─── WireWearRecord ────────────────────────────────────────────────────────────

def test_wire_wear_record_fields():
    r = WireWearRecord(
        run_date='2026-01-01', exception_id='W001',
        tension_length='H02', from_m=1000.0, to_m=1100.0,
        max_value=10.5, level='L2', action=None,
    )
    assert r.tension_length == 'H02'
    assert r.action is None

def test_wire_wear_record_is_immutable():
    r = WireWearRecord(
        run_date='2026-01-01', exception_id='W001',
        tension_length='H02', from_m=1000.0, to_m=1100.0,
        max_value=10.5, level='L2', action=None,
    )
    with pytest.raises((AttributeError, TypeError)):
        r.exception_id = 'changed'


# ─── ChartDataRecord ───────────────────────────────────────────────────────────

def test_chart_data_record_fields():
    r = ChartDataRecord(
        task_run_date='2026-01-01', line=None, track=None, section=None,
        task_no='T001', station_start='1000', station_end='1100',
        tension_length='H02', chainage=1050.0, wear_min=10.3,
        track_type='Tangent', overlap=None,
    )
    assert r.wear_min == 10.3

def test_chart_data_record_is_immutable():
    r = ChartDataRecord(
        task_run_date='2026-01-01', line=None, track=None, section=None,
        task_no='T001', station_start='1000', station_end='1100',
        tension_length='H02', chainage=1050.0, wear_min=10.3,
        track_type='Tangent', overlap=None,
    )
    with pytest.raises((AttributeError, TypeError)):
        r.wear_min = 99.0


# ─── parse_wire_wear_sheet ─────────────────────────────────────────────────────

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

def test_parse_wire_wear_sheet_returns_records(wire_wear_df):
    records = parse_wire_wear_sheet(wire_wear_df)
    assert len(records) == 2
    assert all(isinstance(r, WireWearRecord) for r in records)

def test_parse_wire_wear_sheet_fields(wire_wear_df):
    records = parse_wire_wear_sheet(wire_wear_df)
    assert records[0].exception_id == 'W001'
    assert records[0].tension_length == 'H02'
    assert records[0].from_m == pytest.approx(1000.0)
    assert records[0].level == 'L2'
    assert records[0].action is None
    assert records[1].action == 'Keep monitoring'

def test_parse_wire_wear_sheet_normalizes_numeric_like_ids():
    df = pd.DataFrame({
        'Run Date': ['2026-01-01'],
        'ID': [1001.0],
        'Tension Length': ['H02'],
        'FromM': [1000.0],
        'ToM': [1100.0],
        'MaxValue': [10.5],
        'Level': ['L2'],
        'ACTION': [None],
    })

    records = parse_wire_wear_sheet(df)

    assert records[0].exception_id == '1001'


def test_parse_wire_wear_sheet_preserves_max_location_from_wire_wear_sheet():
    df = pd.DataFrame({
        'Run Date': ['2026-03-01'],
        'ID': ['20260301_EAL_U2_FOT-TAP_W63'],
        'Tension Length': ['35'],
        'FromM': [114644.0],
        'ToM': [114644.5],
        'MaxValue': [9.06],
        'MaxLocation': [114644.5],
        'Level': ['L2'],
        'ACTION': [None],
    })

    records = parse_wire_wear_sheet(df)

    # This test documents the input source contains MaxLocation and must remain available downstream.
    assert df.loc[0, 'MaxLocation'] == pytest.approx(114644.5)

def test_parse_wire_wear_sheet_empty():
    df = pd.DataFrame(columns=['Run Date','ID','Tension Length','FromM','ToM','MaxValue','Level','ACTION'])
    records = parse_wire_wear_sheet(df)
    assert records == []


# ─── parse_chart_data_sheet ────────────────────────────────────────────────────

@pytest.fixture
def chart_data_df():
    return pd.DataFrame({
        'task_run_date':  ['2026-01-01', '2026-01-01', '2026-02-01'],
        'Tension Length': ['H02', 'H02', 'H04'],
        'Chainage':       [1000.0, 1050.0, 2000.0],
        'wear_min':       [10.3, 10.5, 10.1],
        'Track Type':     ['Tangent', 'Tangent', 'Curve'],
        'Overlap':        [None, None, 'Y'],
    })

def test_parse_chart_data_sheet_returns_records(chart_data_df):
    records = parse_chart_data_sheet(chart_data_df)
    assert len(records) == 3
    assert all(isinstance(r, ChartDataRecord) for r in records)

def test_parse_chart_data_sheet_fields(chart_data_df):
    records = parse_chart_data_sheet(chart_data_df)
    assert records[0].task_run_date == '2026-01-01'
    assert records[0].tension_length == 'H02'
    assert records[0].chainage == pytest.approx(1000.0)
    assert records[0].wear_min == pytest.approx(10.3)
    assert records[2].overlap == 'Y'

def test_parse_chart_data_sheet_drops_nan_wear_min():
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

def test_parse_chart_data_sheet_empty():
    df = pd.DataFrame(columns=['task_run_date','Tension Length','Chainage','wear_min','Track Type','Overlap'])
    records = parse_chart_data_sheet(df)
    assert records == []


def test_parse_chart_data_sheet_derives_wear_min_from_legacy_wear_channels():
    df = pd.DataFrame({
        'task_run_date': ['2026-01-16', '2026-01-16'],
        'Tension Length': ['35', '35'],
        'Chainage': [114644.0, 114644.5],
        'wear1': [10.8, 10.2],
        'wear2': [10.4, None],
        'wear3': [10.6, 10.1],
        'wear4': [None, 10.5],
        'Track Type': ['Curve', 'Curve'],
        'Overlap': [None, None],
    })

    records = parse_chart_data_sheet(df)

    assert len(records) == 2
    assert records[0].wear_min == pytest.approx(10.4)
    assert records[1].wear_min == pytest.approx(10.1)


# ─── parse_exception_report ────────────────────────────────────────────────────

def _make_excel_bytes():
    """Build a minimal in-memory Excel with Wire Wear + ChartData sheets."""
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as writer:
        pd.DataFrame({
            'Run Date': ['2026-01-01'],
            'ID': ['W001'],
            'Tension Length': ['H02'],
            'FromM': [1000.0],
            'ToM': [1100.0],
            'MaxValue': [10.5],
            'Level': ['L2'],
            'ACTION': [None],
        }).to_excel(writer, sheet_name='Wire Wear', index=False)
        pd.DataFrame({
            'task_run_date': ['2026-01-01'],
            'Tension Length': ['H02'],
            'Chainage': [1050.0],
            'wear_min': [10.3],
            'Track Type': ['Tangent'],
            'Overlap': [None],
        }).to_excel(writer, sheet_name='ChartData', index=False)
    return buf.getvalue()

def test_parse_exception_report_returns_tuple():
    data = _make_excel_bytes()
    result = parse_exception_report(data)
    assert isinstance(result, tuple)
    assert len(result) == 2

def test_parse_exception_report_wire_wear_records():
    data = _make_excel_bytes()
    wire_wear, chart_data = parse_exception_report(data)
    assert len(wire_wear) == 1
    assert wire_wear[0].exception_id == 'W001'

def test_parse_exception_report_chart_data_records():
    data = _make_excel_bytes()
    wire_wear, chart_data = parse_exception_report(data)
    assert len(chart_data) == 1
    assert chart_data[0].wear_min == pytest.approx(10.3)


def test_parse_exception_report_reads_real_wire_wear_rows_from_lowercase_u3_report():
    report_path = Path(__file__).resolve().parents[2] / 'docs' / 'test data' / 'EAL' / 'Cycle 8' / '20260613_EAL_U3_TAP-LOW_Exception_Report.xlsx'

    wire_wear, chart_data = parse_exception_report(report_path.read_bytes())

    assert len(wire_wear) > 0
    assert any(record.level == 'L2' for record in wire_wear)
    assert any(record.run_date == '2026-06-13' for record in wire_wear)
    assert any(record.exception_id.startswith('20260613_EAL_') for record in wire_wear)
    assert len(chart_data) > 0


def test_parse_repeated_summary_sheet_accepts_varied_column_names():
    df = pd.DataFrame({
        'Id': ['W001'],
        'From': [1000.0],
        'To': [1050.0],
        'Run Date': ['2026-02-01'],
        'Max Value': [10.1],
        'Max Location': [1033.5],
        'Exception Type': ['Wire Wear'],
        'Level': ['L2'],
    })

    records = parse_repeated_summary_sheet(df)

    assert records == [
        RepeatedSummaryRecord(
            exception_id='W001',
            from_m=1000.0,
            to_m=1050.0,
            run_date='2026-02-01',
            max_value=10.1,
            max_location=1033.5,
            exception_type='Wire Wear',
            level='L2',
        )
    ]


def test_parse_repeated_summary_sheet_normalizes_numeric_like_ids():
    df = pd.DataFrame({
        'ID': [1001.0],
        'FromM': [1000.0],
        'ToM': [1050.0],
        'RUN DATE': ['2026-02-01'],
        'MaxValue': [10.1],
        'MaxLocation': [1033.5],
        'Exception Type': ['Wire Wear'],
        'Level': ['L2'],
    })

    records = parse_repeated_summary_sheet(df)

    assert records[0].exception_id == '1001'
