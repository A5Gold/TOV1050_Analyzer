"""
Tests for MetadataManager.get_tension_length_lookup() - Task 1
TDD: Write tests first (RED), then implement (GREEN)
"""
import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch
from pathlib import Path
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.metadata import MetadataManager


# ─── Unit tests using mocked _load_sheet ───────────────────────────────────────

@pytest.fixture
def mock_eal_up_sheet():
    """Minimal EAL UP sheet with Overlap and Tension Length columns"""
    return pd.DataFrame({
        'Overlap FromM': [94977.0, 95356.0, 95559.0],
        'Overlap ToM':   [95355.9, 95558.9, 95800.0],
        'Overlap':       [np.nan,  'Y',     np.nan],
        'Tension Length':['H02',   'H02, H04', 'H04'],
        'Track Type':    ['Tangent','Curve',   'Tangent'],
    })


@pytest.fixture
def mm_with_mock_sheet(mock_eal_up_sheet):
    """MetadataManager with _load_sheet mocked to return EAL UP data"""
    mm = MagicMock(spec=MetadataManager)
    mm._load_sheet.return_value = mock_eal_up_sheet.copy()
    mm.get_tension_length_lookup = MetadataManager.get_tension_length_lookup.__get__(mm)
    mm._aggregate_tension_lengths = MetadataManager._aggregate_tension_lengths.__get__(mm)
    mm._get_sheet_name_for_calc = MetadataManager._get_sheet_name_for_calc.__get__(mm)
    mm._sort_tension_lengths = MetadataManager._sort_tension_lengths.__get__(mm)
    return mm


def test_get_tension_length_lookup_returns_dataframe_with_required_columns(mm_with_mock_sheet):
    """RED -> GREEN: get_tension_length_lookup must return DataFrame with 5 required columns"""
    result = mm_with_mock_sheet.get_tension_length_lookup('EAL', 'UP', 'Mainline')
    assert isinstance(result, pd.DataFrame)
    for col in ['from_m', 'to_m', 'tension_length', 'track_type', 'overlap']:
        assert col in result.columns, f"Missing column: {col}"
    assert len(result) > 0, "Result must not be empty"


def test_aggregate_tension_lengths_single_tl(mm_with_mock_sheet):
    """Single TL row maps directly to the Overlap interval"""
    df = pd.DataFrame({
        'Overlap FromM': [94977.0],
        'Overlap ToM':   [95355.9],
        'Overlap':       [np.nan],
        'Tension Length':['H02'],
        'Track Type':    ['Tangent'],
    })
    result = mm_with_mock_sheet._aggregate_tension_lengths(df)
    assert len(result) == 1
    assert result.iloc[0]['tension_length'] == 'H02'
    assert result.iloc[0]['from_m'] == pytest.approx(94977.0)
    assert result.iloc[0]['to_m'] == pytest.approx(95355.9)


def test_aggregate_tension_lengths_multiple_tl_splits_interval(mm_with_mock_sheet):
    """Multiple TLs in one row must split the Overlap interval evenly"""
    df = pd.DataFrame({
        'Overlap FromM': [95356.0],
        'Overlap ToM':   [95558.9],
        'Overlap':       ['Y'],
        'Tension Length':['H02, H04'],
        'Track Type':    ['Curve'],
    })
    result = mm_with_mock_sheet._aggregate_tension_lengths(df)
    assert len(result) == 2
    tls = list(result['tension_length'])
    assert 'H02' in tls
    assert 'H04' in tls
    total = result['to_m'].max() - result['from_m'].min()
    assert total == pytest.approx(95558.9 - 95356.0, abs=0.1)


def test_aggregate_tension_lengths_skips_nan_from_to(mm_with_mock_sheet):
    """Rows with NaN Overlap FromM/ToM must be skipped"""
    df = pd.DataFrame({
        'Overlap FromM': [np.nan, 94977.0],
        'Overlap ToM':   [np.nan, 95355.9],
        'Overlap':       [np.nan, np.nan],
        'Tension Length':['H01',  'H02'],
        'Track Type':    ['Tangent', 'Tangent'],
    })
    result = mm_with_mock_sheet._aggregate_tension_lengths(df)
    assert len(result) == 1
    assert result.iloc[0]['tension_length'] == 'H02'


def test_aggregate_tension_lengths_skips_nan_tl(mm_with_mock_sheet):
    """Rows with NaN Tension Length must be skipped"""
    df = pd.DataFrame({
        'Overlap FromM': [94977.0],
        'Overlap ToM':   [95355.9],
        'Overlap':       [np.nan],
        'Tension Length':[np.nan],
        'Track Type':    ['Tangent'],
    })
    result = mm_with_mock_sheet._aggregate_tension_lengths(df)
    assert len(result) == 0


def test_get_sheet_name_for_calc_eal_up_mainline(mm_with_mock_sheet):
    assert mm_with_mock_sheet._get_sheet_name_for_calc('EAL', 'UP', 'Mainline') == 'EAL UP'


def test_get_sheet_name_for_calc_eal_dn_mainline(mm_with_mock_sheet):
    assert mm_with_mock_sheet._get_sheet_name_for_calc('EAL', 'DN', 'Mainline') == 'EAL DN'


def test_get_sheet_name_for_calc_eal_up_rac(mm_with_mock_sheet):
    assert mm_with_mock_sheet._get_sheet_name_for_calc('EAL', 'UP', 'RAC') == 'RAC UP'


def test_get_sheet_name_for_calc_eal_dn_rac(mm_with_mock_sheet):
    assert mm_with_mock_sheet._get_sheet_name_for_calc('EAL', 'DN', 'RAC') == 'RAC DN'


def test_get_sheet_name_for_calc_low_s1(mm_with_mock_sheet):
    assert mm_with_mock_sheet._get_sheet_name_for_calc('EAL', 'UP', 'LOW S1') == 'LOW S1'


def test_get_sheet_name_for_calc_lmc_up(mm_with_mock_sheet):
    assert mm_with_mock_sheet._get_sheet_name_for_calc('EAL', 'UP', 'LMC') == 'LMC UP'


def test_get_sheet_name_for_calc_tml_up(mm_with_mock_sheet):
    assert mm_with_mock_sheet._get_sheet_name_for_calc('TML', 'UP', 'Mainline') == 'TML UP'


def test_get_sheet_name_for_calc_tml_dn(mm_with_mock_sheet):
    assert mm_with_mock_sheet._get_sheet_name_for_calc('TML', 'DN', 'Mainline') == 'TML DN'


def test_sort_tension_lengths_h_prefix_first(mm_with_mock_sheet):
    """H-prefix TLs should sort before numeric and X/T/D/M/L prefixes"""
    df = pd.DataFrame({
        'from_m': [1.0, 2.0, 3.0],
        'to_m':   [2.0, 3.0, 4.0],
        'tension_length': ['X36', 'H02', 'T3'],
        'track_type': ['Tangent'] * 3,
        'overlap': [''] * 3,
    })
    result = mm_with_mock_sheet._sort_tension_lengths(df)
    assert result.iloc[0]['tension_length'] == 'H02'


def test_sort_tension_lengths_h_numeric_order(mm_with_mock_sheet):
    """H02 should come before H06"""
    df = pd.DataFrame({
        'from_m': [1.0, 2.0],
        'to_m':   [2.0, 3.0],
        'tension_length': ['H06', 'H02'],
        'track_type': ['Tangent'] * 2,
        'overlap': [''] * 2,
    })
    result = mm_with_mock_sheet._sort_tension_lengths(df)
    assert result.iloc[0]['tension_length'] == 'H02'
    assert result.iloc[1]['tension_length'] == 'H06'


# ─── Integration test (requires actual metadata file) ──────────────────────────

@pytest.fixture
def real_metadata_manager():
    possible_paths = [
        Path(r"C:\MTR\TOV640\TOV640_Analyzer\config\EAL metadata.xlsx"),
        Path(__file__).parent.parent.parent / "config" / "EAL metadata.xlsx",
    ]
    for p in possible_paths:
        if p.exists():
            return MetadataManager(p)
    pytest.skip("EAL metadata.xlsx not found")


def test_tension_length_lookup_not_empty_for_eal_up(real_metadata_manager):
    """Integration: EAL UP Mainline must return non-empty lookup table"""
    result = real_metadata_manager.get_tension_length_lookup('EAL', 'UP', 'Mainline')
    assert isinstance(result, pd.DataFrame)
    assert len(result) > 0
    for col in ['from_m', 'to_m', 'tension_length', 'track_type', 'overlap']:
        assert col in result.columns


def test_tension_length_lookup_eal_dn(real_metadata_manager):
    """Integration: EAL DN Mainline must return non-empty lookup table"""
    result = real_metadata_manager.get_tension_length_lookup('EAL', 'DN', 'Mainline')
    assert len(result) > 0


def test_tension_length_lookup_from_less_than_to(real_metadata_manager):
    """Integration: All from_m must be less than to_m"""
    result = real_metadata_manager.get_tension_length_lookup('EAL', 'UP', 'Mainline')
    assert (result['from_m'] < result['to_m']).all(), "All from_m must be < to_m"
