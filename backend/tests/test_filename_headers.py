import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.api.endpoints import analysis
import pandas as pd
import urllib.parse

client = TestClient(app)

def test_export_raw_filename_with_params():
    # Setup global state (simulate some data to avoid 400 error)
    analysis.LAST_RAW_DF = pd.DataFrame({'col': [1, 2]})
    # Clear global params to ensure we are not using them
    analysis.LAST_ANALYSIS_PARAMS = {}

    # Call with query params
    response = client.get("/api/export/raw?date_str=20250101&line=TEST&track=UP&section=Main")
    
    assert response.status_code == 200
    cd = response.headers["content-disposition"]
    print(f"Content-Disposition: {cd}")
    # Expect: 20250101_TEST_UP_Main_Catenary_Report.csv
    expected_filename = "20250101_TEST_UP_Main_Catenary_Report.csv"
    assert expected_filename in cd

def test_export_raw_filename_fallback():
    # Setup global state
    analysis.LAST_RAW_DF = pd.DataFrame({'col': [1, 2]})
    # Set global params
    analysis.LAST_ANALYSIS_PARAMS = {
        'date_str': '20241231',
        'line': 'OLD',
        'track': 'DN',
        'section': 'S1'
    }
    
    # Call WITHOUT query params
    response = client.get("/api/export/raw")
    
    assert response.status_code == 200
    cd = response.headers["content-disposition"]
    expected_filename = "20241231_OLD_DN_S1_Catenary_Report.csv"
    assert expected_filename in cd
