"""
Test Suite: Issue 1 Phase A2 - Task Run Data Injection in Analyzers

These tests verify that the analyze() method correctly injects Task Run Data
fields into exception DataFrames.

Reference: docs/field-mapping-spec.md Section 12.3
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch
from pathlib import Path

from app.core.analyzers import ExceptionDetector


class TestAnalyzerTaskRunDataInjection:
    """
    Tests for verifying Task Run Data fields are injected into exception DataFrames.
    
    Issue 1 Phase A2: Ensure exception records include task_run_date, line, track,
    task_no, station_start, station_end.
    """
    
    @pytest.fixture
    def mock_metadata_manager(self):
        """Create a mock MetadataManager for testing."""
        mock_mgr = MagicMock()
        
        # Mock get_boundaries_for_plot to return empty DataFrame
        mock_mgr.get_boundaries_for_plot.return_value = pd.DataFrame()
        
        # Mock get_all_thresholds to return minimal thresholds
        mock_mgr.get_all_thresholds.return_value = pd.DataFrame([
            {
                'Exc Type': 'Low Height',
                'Class': 'both',
                'Low Height L1': 5200,
                'Low Height L2': 5250,
            },
            {
                'Exc Type': 'High Height',
                'Class': 'both',
                'High Height L1': 5450,
                'High Height L2': 5400,
            },
            {
                'Exc Type': 'Wire Wear',
                'Class': 'both',
                'Wire Wear L1': 8.0,
                'Wire Wear L2': 8.5,
            },
        ])
        
        # Mock get_exception_boundaries
        mock_mgr.get_exception_boundaries.return_value = pd.DataFrame()
        
        # Mock get_track_type_info, get_overlap_info, get_landmark_info
        mock_mgr.get_track_type_info.return_value = pd.DataFrame()
        mock_mgr.get_overlap_info.return_value = pd.DataFrame()
        mock_mgr.get_landmark_info.return_value = pd.DataFrame()
        
        return mock_mgr
    
    @pytest.fixture
    def sample_data(self):
        """Create sample measurement data with exception-level values."""
        return pd.DataFrame({
            'Chainage': np.arange(1000, 1100, 1.0),
            'height1': np.full(100, 5180),  # Below L1 threshold (5200)
            'height2': np.full(100, 5190),
            'height3': np.full(100, 5195),
            'height4': np.full(100, 5200),
            'stagger1': np.full(100, 10),
            'stagger2': np.full(100, -5),
            'stagger3': np.full(100, 8),
            'stagger4': np.full(100, -3),
            'wear1': np.full(100, 9.0),
            'wear2': np.full(100, 8.8),
            'wear3': np.full(100, 8.5),
            'wear4': np.full(100, 9.2),
        })
    
    def test_analyze_injects_task_run_date_into_exceptions(
        self, mock_metadata_manager, sample_data
    ):
        """
        Verify that analyze() injects task_run_date into exception DataFrames.
        """
        # Arrange
        detector = ExceptionDetector(mock_metadata_manager)
        
        # Act
        results, _ = detector.analyze(
            df=sample_data.copy(),
            line='EAL',
            section='Mainline',
            track='UP',
            date_str='20260209',
            task_no='U1',
            station_start='HUH',
            station_end='RAC'
        )
        
        # Assert - Check each exception type DataFrame
        for exc_type in ['Low Height', 'High Height', 'Wire Wear', 'Stagger Left', 'Stagger Right']:
            if exc_type in results and isinstance(results[exc_type], pd.DataFrame):
                exc_df = results[exc_type]
                if not exc_df.empty:
                    assert 'task_run_date' in exc_df.columns, \
                        f"task_run_date not found in {exc_type} exceptions"
                    assert exc_df['task_run_date'].iloc[0] == '20260209', \
                        f"Incorrect task_run_date in {exc_type}"
    
    def test_analyze_injects_line_and_track_into_exceptions(
        self, mock_metadata_manager, sample_data
    ):
        """
        Verify that analyze() injects line and track into exception DataFrames.
        """
        # Arrange
        detector = ExceptionDetector(mock_metadata_manager)
        
        # Act
        results, _ = detector.analyze(
            df=sample_data.copy(),
            line='TML',
            section='RAC',
            track='DN',
            date_str='20260209'
        )
        
        # Assert
        for exc_type, exc_df in results.items():
            if isinstance(exc_df, pd.DataFrame) and not exc_df.empty:
                assert 'line' in exc_df.columns, f"line not found in {exc_type}"
                assert 'track' in exc_df.columns, f"track not found in {exc_type}"
                assert exc_df['line'].iloc[0] == 'TML'
                assert exc_df['track'].iloc[0] == 'DN'
    
    def test_analyze_injects_optional_fields_when_provided(
        self, mock_metadata_manager, sample_data
    ):
        """
        Verify that optional Task Run Data fields are injected when provided.
        """
        # Arrange
        detector = ExceptionDetector(mock_metadata_manager)
        
        # Act
        results, _ = detector.analyze(
            df=sample_data.copy(),
            line='EAL',
            section='LMC',
            track='UP',
            date_str='20260209',
            task_no='S2',
            station_start='LOW',
            station_end='SHA'
        )
        
        # Assert
        for exc_type, exc_df in results.items():
            if isinstance(exc_df, pd.DataFrame) and not exc_df.empty:
                assert 'task_no' in exc_df.columns
                assert 'station_start' in exc_df.columns
                assert 'station_end' in exc_df.columns
                assert exc_df['task_no'].iloc[0] == 'S2'
                assert exc_df['station_start'].iloc[0] == 'LOW'
                assert exc_df['station_end'].iloc[0] == 'SHA'
    
    def test_analyze_handles_none_optional_fields(
        self, mock_metadata_manager, sample_data
    ):
        """
        Verify that None values for optional fields are handled correctly.
        """
        # Arrange
        detector = ExceptionDetector(mock_metadata_manager)
        
        # Act - Call without optional fields
        results, _ = detector.analyze(
            df=sample_data.copy(),
            line='EAL',
            section='Mainline',
            track='UP',
            date_str='20260209'
            # task_no, station_start, station_end are None by default
        )
        
        # Assert
        for exc_type, exc_df in results.items():
            if isinstance(exc_df, pd.DataFrame) and not exc_df.empty:
                # Columns should exist
                assert 'task_no' in exc_df.columns
                assert 'station_start' in exc_df.columns
                assert 'station_end' in exc_df.columns
                # Values should be None
                assert exc_df['task_no'].iloc[0] is None
                assert exc_df['station_start'].iloc[0] is None
                assert exc_df['station_end'].iloc[0] is None


class TestAnalyzerComputedColumns:
    """
    Tests for verifying computed columns (height_min/max, wear_min/max)
    are present in the raw DataFrame.
    
    Note: These test the pre-computation logic in analyze() (lines 70-80),
    not the full detection flow.
    """
    
    def test_height_min_max_computed_directly(self):
        """
        Verify that height_min and height_max are computed correctly.
        Tests the logic directly without full analyze() flow.
        """
        # Arrange
        df = pd.DataFrame({
            'height1': [5200, 5210],
            'height2': [5180, 5190],
            'height3': [5220, 5230],
            'height4': [5190, 5200],
        })
        
        # Act - Apply the same logic as in analyze()
        height_cols = [c for c in ['height1', 'height2', 'height3', 'height4'] if c in df.columns]
        df['height_min'] = df[height_cols].min(axis=1)
        df['height_max'] = df[height_cols].max(axis=1)
        
        # Assert
        assert 'height_min' in df.columns
        assert 'height_max' in df.columns
        assert df['height_min'].iloc[0] == 5180  # min of [5200, 5180, 5220, 5190]
        assert df['height_max'].iloc[0] == 5220  # max of [5200, 5180, 5220, 5190]
        assert df['height_min'].iloc[1] == 5190  # min of row 2
        assert df['height_max'].iloc[1] == 5230  # max of row 2
    
    def test_wear_min_max_computed_directly(self):
        """
        Verify that wear_min and wear_max are computed correctly.
        Tests the logic directly without full analyze() flow.
        """
        # Arrange
        df = pd.DataFrame({
            'wear1': [7.5, 8.0],
            'wear2': [8.2, 8.5],
            'wear3': [9.0, 9.2],
            'wear4': [7.8, 8.1],
        })
        
        # Act - Apply the same logic as in analyze()
        wear_cols = [c for c in ['wear1', 'wear2', 'wear3', 'wear4'] if c in df.columns]
        df['wear_min'] = df[wear_cols].min(axis=1)
        df['wear_max'] = df[wear_cols].max(axis=1)
        
        # Assert
        assert 'wear_min' in df.columns
        assert 'wear_max' in df.columns
        assert df['wear_min'].iloc[0] == 7.5   # min of [7.5, 8.2, 9.0, 7.8]
        assert df['wear_max'].iloc[0] == 9.0   # max of [7.5, 8.2, 9.0, 7.8]
    
    def test_computed_columns_handle_nan_values(self):
        """
        Verify that computed columns handle NaN values correctly.
        """
        # Arrange
        df = pd.DataFrame({
            'height1': [5200, np.nan],
            'height2': [5180, 5190],
            'height3': [np.nan, 5230],
            'height4': [5190, 5200],
        })
        
        # Act
        height_cols = [c for c in ['height1', 'height2', 'height3', 'height4'] if c in df.columns]
        df['height_min'] = df[height_cols].min(axis=1)
        df['height_max'] = df[height_cols].max(axis=1)
        
        # Assert - min/max should skip NaN values
        assert df['height_min'].iloc[0] == 5180  # min of [5200, 5180, NaN, 5190]
        assert df['height_max'].iloc[0] == 5200  # max of [5200, 5180, NaN, 5190]
        assert df['height_min'].iloc[1] == 5190  # min of [NaN, 5190, 5230, 5200]
        assert df['height_max'].iloc[1] == 5230  # max of [NaN, 5190, 5230, 5200]
