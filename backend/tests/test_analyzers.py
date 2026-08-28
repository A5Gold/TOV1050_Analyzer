import pytest
import pandas as pd
import numpy as np
from app.core.analyzers import ExceptionDetector

class TestTrackClassification:
    """Tests for Story 1.3: IntervalTree Track Classification"""

    def test_class_mapping(self, mock_metadata_manager):
        """Test AC2 & AC3: IntervalTree maps Chainage -> Section (Class)"""
        detector = ExceptionDetector(mock_metadata_manager)
        
        # Prepare DataFrame with Chainage
        # 100100.50 -> Should be in 100000-100200 -> Mainline
        df = pd.DataFrame({
            'Chainage': [100100.50, 100300.00],
            'height1': [5000, 5000]
        })
        
        # Override mock for this specific test if needed, but conftest mock should suffice
        # conftest: Mainline [100000, 100200]
        
        # Run internal mapping method (since analyze calls it)
        # We can also call analyze but that does more stuff. 
        # Testing _map_class_info directly is more unit-test style.
        
        df_mapped = detector._map_class_info(df, 'EAL', 'UP', 'Mainline')
        
        assert 'Class' in df_mapped.columns
        assert df_mapped.iloc[0]['Class'] == 'Mainline'
        # 100300 is outside 100000-100200 mock range -> Should be NaN or 'both'/default
        # Logic says fillna('both') or similar
        assert df_mapped.iloc[1]['Class'] == 'both'

    def test_track_type_mapping_interval_tree(self, mock_metadata_manager):
        """Test AC2 & AC3: IntervalTree maps Chainage -> TrackType"""
        detector = ExceptionDetector(mock_metadata_manager)
        
        # conftest: Tangent [100000, 100100], Curve [100100, 100200]
        df = pd.DataFrame({
            'Chainage': [100050.00, 100150.00, 100250.00]
        })
        
        df_mapped = detector._map_track_info(df, 'EAL', 'Mainline', 'UP')
        
        assert 'Track Type' in df_mapped.columns
        assert df_mapped.iloc[0]['Track Type'] == 'Tangent'
        assert df_mapped.iloc[1]['Track Type'] == 'Curve'
        assert pd.isna(df_mapped.iloc[2]['Track Type']) # Outside ranges

    def test_overlapping_intervals_logic(self, mock_metadata_manager):
        """Test Priority Logic in Interval Mapping (Shortest Interval Wins)"""
        detector = ExceptionDetector(mock_metadata_manager)
        
        # Manually construct an overlapping scenario
        # Large interval: 0-1000 (Type A)
        # Small interval: 400-600 (Type B) -> Point 500 should be Type B
        
        info_df = pd.DataFrame({
            'Type': ['Type A', 'Type B']
        })
        info_df.index = pd.IntervalIndex.from_arrays(
            [0, 400], [1000, 600], closed='left'
        )
        
        df = pd.DataFrame({'Chainage': [500]})
        
        detector._apply_mapping(df, info_df, ['Type'])
        
        assert df.iloc[0]['Type'] == 'Type B'


class TestLMCThresholdFallback:
    """Tests for LMC threshold fallback mechanism"""
    
    def test_lmc_threshold_fallback_to_both(self):
        """
        When Class='LMC' is not defined in threshold sheet,
        should fallback to Class='both' (Mainline standard)
        """
        # Setup detector (metadata_manager not needed for threshold lookup test)
        detector = ExceptionDetector(None)
        
        # Sample data with LMC class
        sample_df = pd.DataFrame({
            'Class': ['LMC', 'LMC', 'LMC'],
            'Chainage': [5000, 5100, 5200]
        })
        
        # Mock thresholds: only 'both' exists, no 'LMC' entry for 'Low Height'
        mock_thresholds = pd.DataFrame([
            {
                'Exc Type': 'Low Height',
                'Class': 'both',
                'Track Type': 'both',
                'Low Height L1': 4500.0,
                'Low Height L2': 4600.0
            }
        ])
        
        # Execute
        result = detector._get_vectorized_threshold(
            sample_df, mock_thresholds, 'Low Height', 'Low Height L1'
        )
        
        # Verify: Should use 'both' value (4500) for all rows
        assert result.notna().all(), "Should fallback to 'both' when LMC not defined"
        assert (result == 4500.0).all(), "Should use 'both' threshold value"
    
    def test_lmc_threshold_uses_lmc_when_available(self):
        """
        When LMC threshold exists, should use it (not fallback to 'both')
        """
        detector = ExceptionDetector(None)
        
        sample_df = pd.DataFrame({
            'Class': ['LMC', 'LMC', 'LMC'],
            'Chainage': [5000, 5100, 5200]
        })
        
        # Mock thresholds: both 'both' and 'LMC' exist
        mock_thresholds = pd.DataFrame([
            {
                'Exc Type': 'Low Height',
                'Class': 'both',
                'Track Type': 'both',
                'Low Height L1': 4500.0,
                'Low Height L2': 4600.0
            },
            {
                'Exc Type': 'Low Height',
                'Class': 'LMC',
                'Track Type': 'both',
                'Low Height L1': 4400.0,  # Different from 'both'
                'Low Height L2': 4550.0
            }
        ])
        
        result = detector._get_vectorized_threshold(
            sample_df, mock_thresholds, 'Low Height', 'Low Height L1'
        )
        
        # Should use LMC-specific value (4400), not 'both' (4500)
        assert (result == 4400.0).all(), "Should use LMC threshold when available"
    
    def test_lmc_threshold_preserves_nan_when_defined(self):
        """
        When LMC class is defined but value is NaN, preserve NaN (don't fallback).
        This indicates the exception type should not be detected for this class.
        """
        detector = ExceptionDetector(None)
        
        sample_df = pd.DataFrame({
            'Class': ['LMC', 'LMC'],
            'Chainage': [5000, 5100]
        })
        
        # Mock thresholds: LMC exists but value is NaN
        mock_thresholds = pd.DataFrame([
            {
                'Exc Type': 'Low Height',
                'Class': 'both',
                'Track Type': 'both',
                'Low Height L1': 4500.0
            },
            {
                'Exc Type': 'Low Height',
                'Class': 'LMC',
                'Track Type': 'both',
                'Low Height L1': np.nan  # Explicitly NaN
            }
        ])
        
        result = detector._get_vectorized_threshold(
            sample_df, mock_thresholds, 'Low Height', 'Low Height L1'
        )
        
        # Should preserve NaN (not fallback to 'both')
        assert result.isna().all(), "Should preserve NaN when LMC is defined with NaN value"


# =============================================================================
# Phase 10.10 - Bug 2: Computed Columns (row_val split) (TDD)
# =============================================================================

class TestComputedColumns:
    """Test that analyze() pre-computes separate height/wear/stagger columns
    instead of using a single overwritten row_val."""

    @pytest.fixture
    def proper_metadata_manager(self, mock_metadata_manager):
        """Fix conftest mock to use proper threshold column names."""
        proper_thresholds = pd.DataFrame([
            {'Exc Type': 'Low Height', 'Class': 'both', 'Track Type': 'both',
             'Low Height L1': 4500.0, 'Low Height L2': 4600.0},
            {'Exc Type': 'High Height', 'Class': 'both', 'Track Type': 'both',
             'High Height L1': 5900.0, 'High Height L2': 5800.0},
            {'Exc Type': 'Wire Wear', 'Class': 'both', 'Track Type': 'both',
             'Wire Wear L1': 6.0, 'Wire Wear L2': 8.0},
            {'Exc Type': 'Stagger Left', 'Class': 'both', 'Track Type': 'Tangent',
             'Stagger L1': 400.0, 'Stagger L2': 350.0, 'Stagger L3': 300.0},
            {'Exc Type': 'Stagger Right', 'Class': 'both', 'Track Type': 'Tangent',
             'Stagger L1': 400.0, 'Stagger L2': 350.0, 'Stagger L3': 300.0},
        ])
        mock_metadata_manager.get_all_thresholds.return_value = proper_thresholds
        return mock_metadata_manager

    def test_analyze_computes_height_min_max(self, proper_metadata_manager):
        """After analyze(), the DataFrame should have height_min and height_max columns."""
        detector = ExceptionDetector(proper_metadata_manager)

        df = pd.DataFrame({
            'Chainage': [100050.0, 100060.0, 100070.0],
            'height1': [5200.0, 5100.0, 5300.0],
            'height2': [5210.0, 5090.0, 5310.0],
            'height3': [5190.0, 5110.0, 5290.0],
            'height4': [5205.0, 5095.0, 5305.0],
            'stagger1': [10.0, 20.0, 15.0],
            'stagger2': [11.0, 21.0, 16.0],
            'stagger3': [12.0, 22.0, 17.0],
            'stagger4': [13.0, 23.0, 18.0],
            'wear1': [12.0, 11.0, 10.0],
            'wear2': [12.5, 11.5, 10.5],
            'wear3': [13.0, 12.0, 11.0],
            'wear4': [13.5, 12.5, 11.5],
        })

        results, _ = detector.analyze(df, 'EAL', 'Mainline', 'UP', '20260201')

        # Verify computed columns exist in the DataFrame
        assert 'height_min' in df.columns, "height_min should be pre-computed"
        assert 'height_max' in df.columns, "height_max should be pre-computed"

        # Verify values are correct
        # Row 0: height1-4 = [5200, 5210, 5190, 5205] → min=5190, max=5210
        assert df.iloc[0]['height_min'] == 5190.0
        assert df.iloc[0]['height_max'] == 5210.0

    def test_analyze_computes_wear_min_max(self, proper_metadata_manager):
        """After analyze(), the DataFrame should have wear_min and wear_max columns."""
        detector = ExceptionDetector(proper_metadata_manager)

        df = pd.DataFrame({
            'Chainage': [100050.0],
            'height1': [5200.0], 'height2': [5200.0],
            'height3': [5200.0], 'height4': [5200.0],
            'stagger1': [10.0], 'stagger2': [10.0],
            'stagger3': [10.0], 'stagger4': [10.0],
            'wear1': [8.0], 'wear2': [9.5],
            'wear3': [7.0], 'wear4': [10.0],
        })

        results, _ = detector.analyze(df, 'EAL', 'Mainline', 'UP', '20260201')

        assert 'wear_min' in df.columns, "wear_min should be pre-computed"
        assert 'wear_max' in df.columns, "wear_max should be pre-computed"

        # wear1-4 = [8, 9.5, 7, 10] → min=7, max=10
        assert df.iloc[0]['wear_min'] == 7.0
        assert df.iloc[0]['wear_max'] == 10.0

    def test_analyze_computes_stg_max_min(self, proper_metadata_manager):
        """After analyze(), the DataFrame should have stg_max and stg_min columns."""
        detector = ExceptionDetector(proper_metadata_manager)

        df = pd.DataFrame({
            'Chainage': [100050.0],
            'height1': [5200.0], 'height2': [5200.0],
            'height3': [5200.0], 'height4': [5200.0],
            'stagger1': [-150.0], 'stagger2': [200.0],
            'stagger3': [-50.0], 'stagger4': [100.0],
            'wear1': [12.0], 'wear2': [12.0],
            'wear3': [12.0], 'wear4': [12.0],
        })

        results, _ = detector.analyze(df, 'EAL', 'Mainline', 'UP', '20260201')

        assert 'stg_max' in df.columns, "stg_max should exist"
        assert 'stg_min' in df.columns, "stg_min should exist"

        # stagger1-4 = [-150, 200, -50, 100] → max=200, min=-150
        assert df.iloc[0]['stg_max'] == 200.0
        assert df.iloc[0]['stg_min'] == -150.0

    def test_computed_columns_not_overwritten_by_detection(self, proper_metadata_manager):
        """height_min/max and wear_min/max should NOT be overwritten by _detect_scalar calls."""
        detector = ExceptionDetector(proper_metadata_manager)

        df = pd.DataFrame({
            'Chainage': [100050.0, 100060.0],
            'height1': [5200.0, 5100.0],
            'height2': [5210.0, 5090.0],
            'height3': [5190.0, 5110.0],
            'height4': [5205.0, 5095.0],
            'stagger1': [10.0, 20.0],
            'stagger2': [11.0, 21.0],
            'stagger3': [12.0, 22.0],
            'stagger4': [13.0, 23.0],
            'wear1': [8.0, 7.0],
            'wear2': [9.0, 8.0],
            'wear3': [10.0, 9.0],
            'wear4': [11.0, 10.0],
        })

        results, _ = detector.analyze(df, 'EAL', 'Mainline', 'UP', '20260201')

        # After all detections run, computed columns should still have correct values
        # Row 0: height min=5190, max=5210
        assert df.iloc[0]['height_min'] == 5190.0
        assert df.iloc[0]['height_max'] == 5210.0

        # Row 0: wear min=8, max=11
        assert df.iloc[0]['wear_min'] == 8.0
        assert df.iloc[0]['wear_max'] == 11.0

        # row_val should NOT exist (replaced by specific columns)
        assert 'row_val' not in df.columns, "row_val should no longer exist"
