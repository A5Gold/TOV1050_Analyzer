"""
Tests for MetadataManager data cleaning logic.

Issue 4 (Phase 10.10 Post-Bug): TML DN Stagger 異常未生成
- 根因: TML metadata.xlsx 的 Track Type ToM 欄位含有千分位逗號 (e.g., '81,410.9')
- pd.to_numeric(errors='coerce') 無法解析含逗號的字串，導致全部變成 NaN
- _extract_interval_data() 在 dropna() 後回傳空 DataFrame

TDD Approach:
1. RED: Write tests for comma-containing numeric strings
2. GREEN: Implement comma removal before pd.to_numeric
3. REFACTOR: Clean up if needed
"""
import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch
import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.metadata import MetadataManager


class TestExtractIntervalDataWithCommas:
    """Tests for _extract_interval_data handling of comma-containing numbers"""

    @pytest.fixture
    def mock_metadata_manager(self, tmp_path):
        """Create a mock MetadataManager with a fake Excel file"""
        # Create a minimal Excel file for testing
        excel_path = tmp_path / "test_metadata.xlsx"
        
        # Create test data with comma-containing numbers (simulating TML DN issue)
        test_df = pd.DataFrame({
            'Track Type FromM': [81215.0, 81300.0, 81400.0],
            'Track Type ToM': ['81,410.9', '81,500.5', '81,600.0'],  # Commas in numbers!
            'Track Type': ['Tangent', 'Curve', 'Tangent'],
        })
        
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            test_df.to_excel(writer, sheet_name='TML DN', index=False)
            # Also create threshold sheet (required by MetadataManager)
            pd.DataFrame({'Class': ['both'], 'Exc Type': ['Normal']}).to_excel(
                writer, sheet_name='threshold', index=False
            )
        
        return MetadataManager(excel_path)

    def test_extract_interval_handles_comma_in_numbers(self, mock_metadata_manager):
        """
        數值欄位含千分位逗號時應該能正確解析
        
        問題: '81,410.9' -> pd.to_numeric -> NaN (失敗)
        期望: '81,410.9' -> 移除逗號 -> 81410.9 (成功)
        """
        result = mock_metadata_manager._extract_interval_data(
            sheet_name='TML DN',
            start_col='Track Type FromM',
            end_col='Track Type ToM',
            value_cols=['Track Type']
        )
        
        # Should NOT be empty (was empty before fix due to NaN from comma parsing)
        assert not result.empty, (
            "_extract_interval_data should handle comma-containing numbers. "
            "Got empty DataFrame - commas likely caused NaN values."
        )
        
        # Should have 3 rows (all data preserved)
        assert len(result) == 3, f"Expected 3 rows, got {len(result)}"
        
        # Check that Track Type values are preserved
        assert 'Track Type' in result.columns
        assert 'Tangent' in result['Track Type'].values

    def test_extract_interval_preserves_normal_numbers(self, mock_metadata_manager):
        """
        正常數值 (無逗號) 應該繼續正常工作
        """
        result = mock_metadata_manager._extract_interval_data(
            sheet_name='TML DN',
            start_col='Track Type FromM',
            end_col='Track Type ToM',
            value_cols=['Track Type']
        )
        
        # Check the IntervalIndex was created correctly
        assert hasattr(result, 'index')
        assert isinstance(result.index, pd.IntervalIndex)
        
        # Verify interval values are correct
        # First interval should be approximately [81215, 81410.9]
        first_interval = result.index[0]
        assert first_interval.left == pytest.approx(81215.0, rel=1e-3)
        assert first_interval.right == pytest.approx(81410.9, rel=1e-3)

    @pytest.fixture
    def mock_metadata_manager_overlap(self, tmp_path):
        """Create a mock MetadataManager with comma-containing Overlap data"""
        excel_path = tmp_path / "test_metadata_overlap.xlsx"
        
        # Simulate Overlap ToM with commas (same issue as Track Type)
        test_df = pd.DataFrame({
            'Overlap FromM': [81000.0, 82000.0],
            'Overlap ToM': ['81,500.5', '82,500.0'],  # Commas!
            'Overlap': ['OVL-A', 'OVL-B'],
            'Tension Length': [100, 150],
        })
        
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            test_df.to_excel(writer, sheet_name='TML DN', index=False)
            pd.DataFrame({'Class': ['both'], 'Exc Type': ['Normal']}).to_excel(
                writer, sheet_name='threshold', index=False
            )
        
        return MetadataManager(excel_path)

    def test_extract_interval_handles_comma_in_overlap(self, mock_metadata_manager_overlap):
        """
        Overlap 欄位含千分位逗號時也應該能正確解析
        """
        result = mock_metadata_manager_overlap._extract_interval_data(
            sheet_name='TML DN',
            start_col='Overlap FromM',
            end_col='Overlap ToM',
            value_cols=['Overlap', 'Tension Length']
        )
        
        assert not result.empty, "Should handle comma-containing Overlap ToM values"
        assert len(result) == 2


class TestNumericCleaningEdgeCases:
    """Edge case tests for numeric data cleaning"""

    @pytest.fixture
    def mock_metadata_manager_edge_cases(self, tmp_path):
        """Create metadata with various edge cases"""
        excel_path = tmp_path / "test_metadata_edge.xlsx"
        
        test_df = pd.DataFrame({
            'Track Type FromM': [
                1000.0,      # Normal float
                '2,000.5',   # Comma in number
                '3000',      # String without comma
                ' 4,500.0 ', # With whitespace
                np.nan,      # NaN value
            ],
            'Track Type ToM': [
                1100.0,
                '2,100.5',
                '3100',
                ' 4,600.0 ',
                5000.0,  # This row should be dropped due to NaN in FromM
            ],
            'Track Type': ['T1', 'T2', 'T3', 'T4', 'T5'],
        })
        
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            test_df.to_excel(writer, sheet_name='TEST', index=False)
            pd.DataFrame({'Class': ['both'], 'Exc Type': ['Normal']}).to_excel(
                writer, sheet_name='threshold', index=False
            )
        
        return MetadataManager(excel_path)

    def test_handles_mixed_formats(self, mock_metadata_manager_edge_cases):
        """
        應該能處理混合格式: float, string, comma-string, whitespace
        """
        result = mock_metadata_manager_edge_cases._extract_interval_data(
            sheet_name='TEST',
            start_col='Track Type FromM',
            end_col='Track Type ToM',
            value_cols=['Track Type']
        )
        
        # Should have 4 rows (5th row dropped due to NaN in FromM)
        assert len(result) == 4, f"Expected 4 rows (one NaN row dropped), got {len(result)}"

    def test_handles_whitespace_around_commas(self, mock_metadata_manager_edge_cases):
        """
        數值周圍有空白時應該能正確處理
        """
        result = mock_metadata_manager_edge_cases._extract_interval_data(
            sheet_name='TEST',
            start_col='Track Type FromM',
            end_col='Track Type ToM',
            value_cols=['Track Type']
        )
        
        # Find the interval containing 4500.0
        for interval in result.index:
            if interval.left > 4000 and interval.left < 5000:
                # Should be approximately [4500, 4600]
                assert interval.left == pytest.approx(4500.0, rel=1e-2)
                assert interval.right == pytest.approx(4600.0, rel=1e-2)
                break
        else:
            pytest.fail("Could not find interval starting around 4500")
