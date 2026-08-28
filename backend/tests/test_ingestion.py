import pytest
import pandas as pd
import numpy as np
from app.core.data_ingestion import DataLoader

class TestFileIngestion:
    """Tests for Story 1.2: File Ingestion Service"""

    def test_load_datac_file_success(self, tmp_path, mock_datac_content):
        """Test AC2: Backend parses .datac file to Pandas DataFrame"""
        # Create a dummy .datac file
        file_path = tmp_path / "test.datac"
        file_path.write_text(mock_datac_content, encoding="utf-8")
        
        loader = DataLoader()
        df = loader.load_data(str(file_path))
        
        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert len(df) == 3
        # Check standard columns mapping
        assert 'stagger1' in df.columns
        assert 'height1' in df.columns
        assert 'Line' in df.columns
        assert df.iloc[0]['Line'] == 'EAL'

    def test_chainage_calculation(self, tmp_path, mock_datac_content):
        """Test AC4: Chainage is calculated/verified"""
        file_path = tmp_path / "test.datac"
        file_path.write_text(mock_datac_content, encoding="utf-8")
        
        loader = DataLoader()
        df = loader.load_data(str(file_path))
        
        # KM=100, LOCATION=100.50 -> 100100.50
        assert 'Chainage' in df.columns
        assert df.iloc[0]['Chainage'] == 100100.50
        assert df.iloc[1]['Chainage'] == 100100.55
        
    def test_numeric_conversion_and_cleaning(self, tmp_path):
        """Test AC3: Data cleaning and numeric conversion"""
        # Create dirty data
        dirty_content = """KM;LOCATION;LINE;TRACK;STG1c;WHGT1c
        100;100.50;EAL;UP; 10 ; 5300
        100;100.60;EAL;UP; xx ; 5300
        """
        file_path = tmp_path / "dirty.datac"
        file_path.write_text(dirty_content, encoding="utf-8")
        
        loader = DataLoader()
        df = loader.load_data(str(file_path))
        
        assert df.iloc[0]['stagger1'] == 10  # Stripped and converted
        assert pd.isna(df.iloc[1]['stagger1']) # 'xx' becomes NaN

    def test_utf8_bom_file_handling(self, tmp_path, mock_datac_content):
        """Test: Files with UTF-8 BOM are parsed correctly.
        
        Windows applications often save files with UTF-8 BOM (Byte Order Mark).
        The BOM bytes (EF BB BF) should not corrupt the first column name.
        """
        file_path = tmp_path / "bom.datac"
        # Write file with UTF-8 BOM prefix
        bom_bytes = bytes([0xEF, 0xBB, 0xBF])  # Explicit BOM bytes
        file_path.write_bytes(bom_bytes + mock_datac_content.encode('utf-8'))
        
        loader = DataLoader()
        df = loader.load_data(str(file_path))
        
        # The KM column should be recognized correctly (not '\xef\xbb\xbfKM')
        assert 'KM' in df.columns, f"Expected 'KM' column, got: {df.columns.tolist()}"
        # Chainage should be calculated correctly
        assert 'Chainage' in df.columns, "Chainage column should be present"
        assert df.iloc[0]['Chainage'] == 100100.50

    def test_missing_km_column_returns_no_chainage(self, tmp_path):
        """Test: Missing KM column means Chainage cannot be calculated."""
        # Create file without KM column
        content_no_km = """LOCATION;LINE;TRACK;STG1c;WHGT1c
100.50;EAL;UP;10;5300
100.55;EAL;UP;15;5301
"""
        file_path = tmp_path / "no_km.datac"
        file_path.write_text(content_no_km, encoding="utf-8")
        
        loader = DataLoader()
        df = loader.load_data(str(file_path))
        
        # KM column should not exist
        assert 'KM' not in df.columns
        # Chainage should NOT be calculated
        assert 'Chainage' not in df.columns
