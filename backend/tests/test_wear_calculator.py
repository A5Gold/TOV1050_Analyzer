"""Tests for wear_calculator module - Task 3 rewrite (TDD)"""
import pytest
import math
import pandas as pd
import time
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.calculation.excel_parser import ChartDataRecord
from app.core.calculation.wear_calculator import (
    WearResult,
    calculate_wear_percentage,
    calculate_wear_statistics,
    calculate_average_wear,
)


# --- calculate_wear_percentage ------------------------------------------------

def test_wear_percentage_zero_returns_zero():
    assert calculate_wear_percentage(0.0) == 0.0

def test_wear_percentage_full_wire():
    assert calculate_wear_percentage(13.2) == pytest.approx(0.0, abs=1.0)

def test_wear_percentage_half_worn():
    result = calculate_wear_percentage(6.6)
    assert 40.0 <= result <= 60.0

def test_wear_percentage_out_of_range():
    assert calculate_wear_percentage(0.1) == 100.0

def test_wear_percentage_returns_float_rounded():
    result = calculate_wear_percentage(10.0)
    assert isinstance(result, float)
    assert result == round(result, 2)

def test_wear_percentage_non_negative():
    for r in [1.0, 3.0, 6.6, 10.0, 12.0, 13.2]:
        assert calculate_wear_percentage(r) >= 0.0


def test_calculate_wear_statistics_uses_sample_sd_and_none_for_singleton():
    assert calculate_wear_statistics([11.8, 11.4]) == (11.6, pytest.approx(0.28))
    assert calculate_wear_statistics([11.8]) == (11.8, None)


def test_calculate_wear_statistics_remains_finite_for_large_equal_values():
    mean, sample_sd = calculate_wear_statistics([1e308, 1e308])
    assert mean == 1e308
    assert sample_sd == 0.0
    assert math.isfinite(mean)
    assert math.isfinite(sample_sd)


def test_calculate_wear_statistics_rejects_unrepresentable_sample_sd():
    with pytest.raises(ValueError, match="finite"):
        calculate_wear_statistics([1.7e308, -1.7e308])


# --- WearResult ---------------------------------------------------------------

def test_wear_result_is_immutable():
    r = WearResult(
        tension_length='H02', from_m=1000.0, to_m=1500.0,
        line='EAL', track='UP', section='S1', cycle_date='2026-02-01',
        avg_wear_min=10.5, sd=0.2, wear_percentage=15.0,
        dates=('2026-01-01', '2026-02-01'),
        record_points=(10.5, 10.3),
    )
    with pytest.raises((AttributeError, TypeError)):
        r.tension_length = 'H04'

def test_wear_result_fields():
    r = WearResult(
        tension_length='H02', from_m=1000.0, to_m=1500.0,
        line='EAL', track='UP', section='S1', cycle_date='2026-01-01',
        avg_wear_min=10.5, sd=0.2, wear_percentage=15.0,
        dates=('2026-01-01',),
        record_points=(10.5,),
    )
    assert r.tension_length == 'H02'
    assert r.avg_wear_min == pytest.approx(10.5)


# --- calculate_average_wear ---------------------------------------------------

@pytest.fixture
def sample_records():
    return [
        ChartDataRecord(task_run_date='2026-01-01', line='EAL', track='UP', section='S1', task_no='T01', station_start='1000', station_end='1050', tension_length='H02', chainage=1000.0, wear_min=10.5, track_type='Tangent', overlap=None),
        ChartDataRecord(task_run_date='2026-01-01', line='EAL', track='UP', section='S1', task_no='T01', station_start='1000', station_end='1050', tension_length='H02', chainage=1050.0, wear_min=10.3, track_type='Tangent', overlap=None),
        ChartDataRecord(task_run_date='2026-02-01', line='EAL', track='UP', section='S1', task_no='T01', station_start='1000', station_end='1050', tension_length='H02', chainage=1000.0, wear_min=10.1, track_type='Tangent', overlap=None),
        ChartDataRecord(task_run_date='2026-01-01', line='EAL', track='UP', section='S1', task_no='T02', station_start='2000', station_end='2100', tension_length='H04', chainage=2000.0, wear_min=10.8, track_type='Curve', overlap='Y'),
    ]

def test_calculate_average_wear_groups_by_tl(sample_records):
    results = calculate_average_wear(sample_records)
    tls = {r.tension_length for r in results}
    assert tls == {'H02', 'H04'}

def test_calculate_average_wear_avg_wear_min(sample_records):
    results = calculate_average_wear(sample_records)
    h02 = next(r for r in results if r.tension_length == 'H02')
    expected_avg = (10.5 + 10.3 + 10.1) / 3
    assert h02.avg_wear_min == pytest.approx(expected_avg, abs=0.01)

def test_calculate_average_wear_dates_sorted(sample_records):
    results = calculate_average_wear(sample_records)
    h02 = next(r for r in results if r.tension_length == 'H02')
    assert h02.dates == ('2026-01-01', '2026-02-01')

def test_calculate_average_wear_record_points(sample_records):
    results = calculate_average_wear(sample_records)
    h02 = next(r for r in results if r.tension_length == 'H02')
    # record_points: mean wear_min per unique date, sorted by date
    assert len(h02.record_points) == 2

def test_calculate_average_wear_wear_percentage_range(sample_records):
    results = calculate_average_wear(sample_records)
    for r in results:
        assert 0.0 <= r.wear_percentage <= 100.0

def test_calculate_average_wear_empty():
    assert calculate_average_wear([]) == []

def test_calculate_average_wear_from_to_m(sample_records):
    results = calculate_average_wear(sample_records)
    h02 = next(r for r in results if r.tension_length == 'H02')
    assert h02.from_m == pytest.approx(1000.0)
    assert h02.to_m == pytest.approx(1050.0)


def test_calculate_average_wear_assigns_tension_length_by_metadata_interval():
    records = [
        ChartDataRecord(
            task_run_date='2026-01-01',
            line='TML',
            track='UP',
            section='Mainline',
            task_no='T01',
            station_start='1000',
            station_end='1050',
            tension_length='WRONG',
            chainage=1010.0,
            wear_min=10.5,
            track_type='Tangent',
            overlap=None,
        ),
        ChartDataRecord(
            task_run_date='2026-01-01',
            line='TML',
            track='UP',
            section='Mainline',
            task_no='T01',
            station_start='1000',
            station_end='1050',
            tension_length='WRONG',
            chainage=1060.0,
            wear_min=10.3,
            track_type='Tangent',
            overlap=None,
        ),
    ]
    tl_lookup = pd.DataFrame([
        {'from_m': 1000.0, 'to_m': 1049.99, 'tension_length': 'H01', 'track_type': 'Tangent', 'overlap': ''},
        {'from_m': 1050.0, 'to_m': 1099.99, 'tension_length': 'H02', 'track_type': 'Tangent', 'overlap': ''},
    ])

    results = calculate_average_wear(records, tl_lookup=tl_lookup)

    assert {r.tension_length for r in results} == {'H01', 'H02'}


def test_calculate_average_wear_merges_same_tension_length_across_metadata_segments():
    records = [
        ChartDataRecord(
            task_run_date='2026-01-01',
            line='EAL',
            track='UP',
            section='Mainline',
            task_no='U2',
            station_start='FOT',
            station_end='TAP',
            tension_length='33',
            chainage=113560.0,
            wear_min=11.1,
            track_type='Curve',
            overlap='Y',
        ),
        ChartDataRecord(
            task_run_date='2026-01-01',
            line='EAL',
            track='UP',
            section='Mainline',
            task_no='U2',
            station_start='FOT',
            station_end='TAP',
            tension_length='33',
            chainage=114350.0,
            wear_min=11.5,
            track_type='Curve',
            overlap='Y',
        ),
    ]
    tl_lookup = pd.DataFrame([
        {'from_m': 113547.95, 'to_m': 113612.90, 'tension_length': '33', 'track_type': '', 'overlap': 'Y'},
        {'from_m': 114309.00, 'to_m': 114376.45, 'tension_length': '33', 'track_type': '', 'overlap': 'Y'},
    ])

    results = calculate_average_wear(records, tl_lookup=tl_lookup)

    assert len(results) == 1
    merged = results[0]
    assert merged.tension_length == '33'
    assert merged.from_m == pytest.approx(113547.95)
    assert merged.to_m == pytest.approx(114376.45)
    assert merged.avg_wear_min == pytest.approx(11.3, abs=0.01)


def test_calculate_average_wear_merges_same_tl_across_tracks_and_metadata_segments():
    records = [
        ChartDataRecord(
            task_run_date='2026-01-27',
            line='TML',
            track='UP',
            section='Mainline',
            task_no='U1',
            station_start='WKS',
            station_end='TAW',
            tension_length='M10',
            chainage=1005.0,
            wear_min=10.0,
            track_type='Tangent',
            overlap=None,
        ),
        ChartDataRecord(
            task_run_date='2026-01-27',
            line='TML',
            track='UP',
            section='Mainline',
            task_no='U1',
            station_start='WKS',
            station_end='TAW',
            tension_length='M10',
            chainage=1110.0,
            wear_min=11.0,
            track_type='Tangent',
            overlap=None,
        ),
        ChartDataRecord(
            task_run_date='2026-02-06',
            line='TML',
            track='DN',
            section='Mainline',
            task_no='D1',
            station_start='TAW',
            station_end='WKS',
            tension_length='M10',
            chainage=1008.0,
            wear_min=12.0,
            track_type='Tangent',
            overlap=None,
        ),
        ChartDataRecord(
            task_run_date='2026-02-06',
            line='TML',
            track='DN',
            section='Mainline',
            task_no='D1',
            station_start='TAW',
            station_end='WKS',
            tension_length='M10',
            chainage=1115.0,
            wear_min=13.0,
            track_type='Tangent',
            overlap=None,
        ),
    ]
    tl_lookup = pd.DataFrame([
        {'from_m': 1000.0, 'to_m': 1010.0, 'tension_length': 'M10', 'track_type': 'Tangent', 'overlap': ''},
        {'from_m': 1100.0, 'to_m': 1120.0, 'tension_length': 'M10', 'track_type': 'Tangent', 'overlap': ''},
    ])

    results = calculate_average_wear(records, tl_lookup=tl_lookup)

    assert len(results) == 1
    merged = results[0]
    assert merged.tension_length == 'M10'
    assert merged.track == 'Siding'
    assert merged.section == 'Mainline'
    assert merged.from_m == pytest.approx(1000.0)
    assert merged.to_m == pytest.approx(1120.0)
    assert merged.avg_wear_min == pytest.approx(11.5, abs=0.01)
    assert merged.dates == ('2026-01-27', '2026-02-06')
    assert merged.record_points == (10.5, 12.5)


def test_calculate_average_wear_merges_same_tl_across_track_and_section():
    records = [
        ChartDataRecord(
            task_run_date='2026-01-27',
            line='TML',
            track='UP',
            section='Mainline',
            task_no='U1',
            station_start='WKS',
            station_end='TAW',
            tension_length='M10',
            chainage=1005.0,
            wear_min=10.0,
            track_type='Tangent',
            overlap=None,
        ),
        ChartDataRecord(
            task_run_date='2026-01-27',
            line='TML',
            track='DN',
            section='Mainline',
            task_no='D1',
            station_start='TAW',
            station_end='WKS',
            tension_length='M10',
            chainage=1008.0,
            wear_min=12.0,
            track_type='Tangent',
            overlap=None,
        ),
        ChartDataRecord(
            task_run_date='2026-01-27',
            line='TML',
            track='UP',
            section='Depot',
            task_no='D2',
            station_start='TAW',
            station_end='WKS',
            tension_length='M10',
            chainage=1009.0,
            wear_min=13.0,
            track_type='Tangent',
            overlap=None,
        ),
    ]

    results = calculate_average_wear(records)

    identities = {(result.track, result.section, result.tension_length) for result in results}
    assert identities == {('Siding', 'Mixed', 'M10')}
    assert results[0].avg_wear_min == pytest.approx((10.0 + 12.0 + 13.0) / 3, abs=0.01)


def test_calculate_average_wear_merges_same_tl_across_tracks_sessions_and_dates_for_upload_batch():
    records = [
        ChartDataRecord(
            task_run_date='2026-07-01',
            line='EAL',
            track='UP',
            section='Mainline',
            task_no='U1',
            station_start='FOT',
            station_end='UNI',
            tension_length='42',
            chainage=1005.0,
            wear_min=10.0,
            track_type='Tangent',
            overlap=None,
        ),
        ChartDataRecord(
            task_run_date='2026-07-03',
            line='EAL',
            track='DN',
            section='RAC',
            task_no='D2',
            station_start='UNI',
            station_end='FOT',
            tension_length='42',
            chainage=1110.0,
            wear_min=9.4,
            track_type='Curve',
            overlap=None,
        ),
        ChartDataRecord(
            task_run_date='2026-07-02',
            line='EAL',
            track='UP',
            section='LMC',
            task_no='LMC',
            station_start='FOT',
            station_end='UNI',
            tension_length='42',
            chainage=1215.0,
            wear_min=9.7,
            track_type='Tangent',
            overlap=None,
        ),
    ]
    tl_lookup = pd.DataFrame([
        {'from_m': 1000.0, 'to_m': 1010.0, 'tension_length': '42', 'track_type': 'Tangent', 'overlap': ''},
        {'from_m': 1100.0, 'to_m': 1120.0, 'tension_length': '42', 'track_type': 'Curve', 'overlap': ''},
        {'from_m': 1200.0, 'to_m': 1230.0, 'tension_length': '42', 'track_type': 'Tangent', 'overlap': ''},
    ])

    results = calculate_average_wear(records, tl_lookup=tl_lookup)

    assert len(results) == 1
    merged = results[0]
    assert merged.tension_length == '42'
    assert merged.track == 'Siding'
    assert merged.section == 'Mixed'
    assert merged.cycle_date == '2026-07-03'
    assert merged.from_m == pytest.approx(1000.0)
    assert merged.to_m == pytest.approx(1230.0)
    assert merged.avg_wear_min == pytest.approx(9.7)
    assert merged.sd == pytest.approx(0.3)
    assert merged.dates == ('2026-07-01', '2026-07-02', '2026-07-03')
    assert merged.record_points == (10.0, 9.7, 9.4)


def test_calculate_average_wear_uses_precomputed_metadata_segments_for_large_inputs():
    records = [
        ChartDataRecord(
            task_run_date='2026-04-13',
            line='TML',
            track='UP',
            section='Mainline',
            task_no='U1',
            station_start='WKS',
            station_end='TAW',
            tension_length='M32',
            chainage=81200.0 + (index % 300),
            wear_min=10.0 + (index % 10) / 100,
            track_type='Tangent',
            overlap=None,
        )
        for index in range(5000)
    ]
    tl_lookup = pd.DataFrame([
        {
            'from_m': 81200.0 + (index * 10),
            'to_m': 81209.99 + (index * 10),
            'tension_length': f'M{index:02d}',
            'track_type': 'Tangent',
            'overlap': '',
        }
        for index in range(30)
    ])

    start = time.perf_counter()
    results = calculate_average_wear(records, tl_lookup=tl_lookup)
    elapsed = time.perf_counter() - start

    assert elapsed < 2.0
    assert len(results) == 30
