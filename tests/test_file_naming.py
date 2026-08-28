
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.api.endpoints import analysis
from unittest.mock import patch
import pandas as pd

client = TestClient(app)

def test_export_report_filename_format():
    """
    Test that the export report endpoint returns the correct filename format:
    {Date}_{Line}_{Track}_{Section}_Exception_Report.xlsx
    """
    # Mock global state
    mock_params = {
        'date_str': '20251104',
        'line': 'EAL',
        'track': 'DN',
        'section': 'LMC'
    }
    
    mock_results = {'dummy': [{'id': 1}]}
    mock_raw = pd.DataFrame({'col1': [1, 2]})

    with patch.object(analysis, 'LAST_ANALYSIS_RESULTS', mock_results), \
         patch.object(analysis, 'LAST_RAW_DF', mock_raw), \
         patch.object(analysis, 'LAST_ANALYSIS_PARAMS', mock_params):
         
        response = client.get("/api/export/report")
        
        assert response.status_code == 200
        content_disp = response.headers["content-disposition"]
        expected_filename = "20251104_EAL_DN_LMC_Exception_Report.xlsx"
        
        assert expected_filename in content_disp
        assert f'filename="{expected_filename}"' in content_disp

def test_export_raw_filename_format():
    """
    Test that the export raw endpoint returns the correct filename format:
    {Date}_{Line}_{Track}_{Section}_Catenary_Report.csv
    """
    # Mock global state
    mock_params = {
        'date_str': '20251104',
        'line': 'EAL',
        'track': 'DN',
        'section': 'LMC'
    }
    
    mock_raw = pd.DataFrame({'col1': [1, 2]})

    with patch.object(analysis, 'LAST_RAW_DF', mock_raw), \
         patch.object(analysis, 'LAST_ANALYSIS_PARAMS', mock_params):
         
        response = client.get("/api/export/raw")
        
        assert response.status_code == 200
        content_disp = response.headers["content-disposition"]
        expected_filename = "20251104_EAL_DN_LMC_Catenary_Report.csv"
        
        assert expected_filename in content_disp
        assert f'filename="{expected_filename}"' in content_disp

def test_generate_report_filename_format():
    """
    Test the generate report endpoint (POST) which takes params in body.
    """
    payload = {
        "exceptions": {"dummy": []},
        "chart_data": {"Chainage": [100]},
        "params": {
            "date_str": "20251104",
            "line": "EAL",
            "track": "DN",
            "section": "LMC"
        }
    }
    
    response = client.post("/api/export/report/generate", json=payload)
    
    assert response.status_code == 200
    content_disp = response.headers["content-disposition"]
    expected_filename = "20251104_EAL_DN_LMC_Exception_Report.xlsx"
    
    assert expected_filename in content_disp
