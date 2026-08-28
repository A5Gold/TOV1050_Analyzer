"""
Tests for RepeatedExceptionFinder column standardization.

Issue 2 (Phase 10.10 Post-Bug): History Compare 新/舊 Excel 格式不相容
- 新格式使用 PascalCase: ID, Exception Type, MaxValue, MaxLocation, Length
- 舊格式使用小寫: id, exception type, maxValue, maxLocation, length
- _standardize_columns() 需要處理兩種格式

TDD Approach:
1. RED: Write tests for new column mapping
2. GREEN: Implement the mapping
3. REFACTOR: Clean up if needed
"""
import pytest
import pandas as pd
import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.repeated_finder import RepeatedExceptionFinder


@pytest.fixture
def finder():
    """RepeatedExceptionFinder instance"""
    return RepeatedExceptionFinder()


class TestStandardizeColumns:
    """Tests for _standardize_columns method - Issue 2 fix"""

    def test_standardize_new_format_id_to_lowercase(self, finder):
        """
        新格式 'ID' 應該映射到 'id'
        """
        df = pd.DataFrame({
            'ID': ['EXC001', 'EXC002'],
            'FromM': [1000.0, 2000.0],
            'ToM': [1100.0, 2100.0],
        })
        
        result = finder._standardize_columns(df)
        
        assert 'id' in result.columns, "ID should be mapped to id"
        assert 'ID' not in result.columns, "Original ID column should be renamed"
        assert result['id'].tolist() == ['EXC001', 'EXC002']

    def test_standardize_new_format_exception_type(self, finder):
        """
        新格式 'Exception Type' 應該映射到 'exception type'
        """
        df = pd.DataFrame({
            'id': ['EXC001'],
            'Exception Type': ['Low Height'],
            'FromM': [1000.0],
            'ToM': [1100.0],
        })
        
        result = finder._standardize_columns(df)
        
        assert 'exception type' in result.columns, "Exception Type should be mapped to exception type"
        assert result['exception type'].iloc[0] == 'Low Height'

    def test_standardize_new_format_max_value(self, finder):
        """
        新格式 'MaxValue' 應該映射到 'maxValue' (保持 camelCase)
        """
        df = pd.DataFrame({
            'id': ['EXC001'],
            'FromM': [1000.0],
            'ToM': [1100.0],
            'MaxValue': [4450.5],
        })
        
        result = finder._standardize_columns(df)
        
        assert 'maxValue' in result.columns, "MaxValue should be mapped to maxValue"
        assert result['maxValue'].iloc[0] == 4450.5

    def test_standardize_new_format_max_location(self, finder):
        """
        新格式 'MaxLocation' 應該映射到 'maxLocation' (保持 camelCase)
        """
        df = pd.DataFrame({
            'id': ['EXC001'],
            'FromM': [1000.0],
            'ToM': [1100.0],
            'MaxLocation': [1050.0],
        })
        
        result = finder._standardize_columns(df)
        
        assert 'maxLocation' in result.columns, "MaxLocation should be mapped to maxLocation"
        assert result['maxLocation'].iloc[0] == 1050.0

    def test_standardize_new_format_length(self, finder):
        """
        新格式 'Length' 應該映射到 'length' (保持小寫)
        """
        df = pd.DataFrame({
            'id': ['EXC001'],
            'FromM': [1000.0],
            'ToM': [1100.0],
            'Length': [100.0],
        })
        
        result = finder._standardize_columns(df)
        
        assert 'length' in result.columns, "Length should be mapped to length"
        assert result['length'].iloc[0] == 100.0

    def test_standardize_mixed_format(self, finder):
        """
        同時處理新格式和舊格式欄位
        """
        df = pd.DataFrame({
            'ID': ['EXC001'],  # New format
            'Exception Type': ['Low Height'],  # New format
            'FromM': [1000.0],  # Same in both
            'ToM': [1100.0],  # Same in both
            'maxValue': [4450.5],  # Already in old format (should be preserved)
            'maxLocation': [1050.0],  # Already in old format
        })
        
        result = finder._standardize_columns(df)
        
        assert 'id' in result.columns
        assert 'exception type' in result.columns
        assert 'maxValue' in result.columns  # Should be preserved
        assert 'maxLocation' in result.columns  # Should be preserved

    def test_standardize_preserves_old_format(self, finder):
        """
        舊格式欄位應該保持不變
        """
        df = pd.DataFrame({
            'id': ['EXC001'],
            'exception type': ['Low Height'],
            'FromM': [1000.0],
            'ToM': [1100.0],
            'maxValue': [4450.5],
            'maxLocation': [1050.0],
            'length': [100.0],
        })
        
        result = finder._standardize_columns(df)
        
        # All columns should remain unchanged
        assert 'id' in result.columns
        assert 'exception type' in result.columns
        assert 'maxValue' in result.columns
        assert 'maxLocation' in result.columns
        assert 'length' in result.columns

    def test_standardize_legacy_format(self, finder):
        """
        舊的 legacy 格式映射應繼續運作 (startM, endM)
        """
        df = pd.DataFrame({
            'id': ['EXC001'],
            'startM': [1000.0],  # Legacy column
            'endM': [1100.0],  # Legacy column
            'exception type': ['Low Height'],
        })
        
        result = finder._standardize_columns(df)
        
        assert 'FromM' in result.columns, "startM should be mapped to FromM"
        assert 'ToM' in result.columns, "endM should be mapped to ToM"


class TestFindRepeatedWithNewFormat:
    """Integration tests for find_repeated with new Excel format"""

    def test_find_repeated_new_format_vs_new_format(self, finder):
        """
        兩個新格式 Excel 應該能正確比對
        """
        # Latest (new format)
        df_latest = pd.DataFrame({
            'ID': ['20260201_EAL_UP_LH0'],
            'Exception Type': ['Low Height'],
            'FromM': [1000.0],
            'ToM': [1100.0],
            'MaxValue': [4450.0],
            'MaxLocation': [1050.0],
            'Length': [100.0],
        })
        
        # Previous (new format)
        df_previous = pd.DataFrame({
            'ID': ['20260115_EAL_UP_LH0'],
            'Exception Type': ['Low Height'],
            'FromM': [1000.0],
            'ToM': [1100.0],
            'MaxValue': [4452.0],
            'MaxLocation': [1048.0],
            'Length': [100.0],
        })
        
        result = finder.find_repeated(df_latest, df_previous, 'Previous 1')
        
        # Should find repeated exception
        assert not result.empty, "Should find repeated exception with new format"
        assert 'Previous 1' in result.columns
        assert result['Previous 1'].iloc[0] == '20260115_EAL_UP_LH0'

    def test_find_repeated_new_format_vs_old_format(self, finder):
        """
        新格式 Excel 與舊格式 Excel 應該能正確比對 (向後相容)
        """
        # Latest (new format)
        df_latest = pd.DataFrame({
            'ID': ['20260201_EAL_UP_LH0'],
            'Exception Type': ['Low Height'],
            'FromM': [1000.0],
            'ToM': [1100.0],
            'MaxValue': [4450.0],
            'MaxLocation': [1050.0],
            'Length': [100.0],
        })
        
        # Previous (old format)
        df_previous = pd.DataFrame({
            'id': ['20260115_EAL_UP_LH0'],
            'exception type': ['Low Height'],
            'FromM': [1000.0],
            'ToM': [1100.0],
            'maxValue': [4452.0],
            'maxLocation': [1048.0],
            'length': [100.0],
        })
        
        result = finder.find_repeated(df_latest, df_previous, 'Previous 1')
        
        # Should find repeated exception (backward compatible)
        assert not result.empty, "Should find repeated exception (new vs old format)"
        assert 'Previous 1' in result.columns

    def test_find_repeated_returns_empty_on_missing_columns(self, finder):
        """
        缺少必要欄位時應該返回空 DataFrame
        """
        df_latest = pd.DataFrame({
            'ID': ['EXC001'],
            # Missing FromM, ToM, maxLocation, maxValue
        })
        
        df_previous = pd.DataFrame({
            'ID': ['EXC002'],
        })
        
        result = finder.find_repeated(df_latest, df_previous, 'Previous 1')
        
        assert result.empty, "Should return empty DataFrame when required columns are missing"
