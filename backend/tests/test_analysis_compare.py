import pytest
from fastapi.testclient import TestClient
import pandas as pd
import io
from app.main import app

client = TestClient(app)

def create_mock_excel(data, sheet_name="Low Height"):
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)
    output.seek(0)
    return output


class TestAnalysisCompare:
    def test_load_combined_df_mixed_case_columns(self):
        """
        Test that load_combined_df handles mixed case columns correctly
        (e.g., 'Exception Type' vs 'exception type') without duplicate column errors.
        """
        # File 1: PascalCase headers (New Format)
        data1 = {
            "ID": ["E1"],
            "Exception Type": ["Low Height"],
            "MaxValue": [5000],
            "MaxLocation": [100],
            "Length": [10],
            "FromM": [90],
            "ToM": [110],
            "level": ["L2"]
        }
        file1 = create_mock_excel(data1)
        
        # File 2: PascalCase headers (New Format)
        data2 = {
            "ID": ["E1"], # Same ID -> Repeated
            "Exception Type": ["Low Height"],
            "MaxValue": [5000],
            "MaxLocation": [100],
            "Length": [10],
            "FromM": [90],
            "ToM": [110],
            "level": ["L2"]
        }
        file2 = create_mock_excel(data2)

        files = [
            ('files', ('20260209_EAL_UP_Mainline.xlsx', file1, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')),
            ('files', ('20260208_EAL_UP_Mainline.xlsx', file2, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'))
        ]

        response = client.post("/api/analyze/compare", files=files)
        
        # Should not return 500 Internal Server Error
        assert response.status_code == 200, f"Response text: {response.text}"
        res = response.json()
        assert res["status"] == "success"
        
        # Should find repeated exception
        assert "Low Height" in res["repeated"]
        assert len(res["repeated"]["Low Height"]) == 1
        assert res["repeated"]["Low Height"][0]["id"] == "E1"

    def test_load_combined_df_legacy_format(self):
        """
        Test that legacy format (snake_case) still works.
        """
        # File 1: snake_case headers (Old Format)
        data1 = {
            "id": ["E2"],
            "exception type": ["Stagger Left"],
            "maxValue": [300],
            "maxLocation": [200],
            "length": [5],
            "FromM": [190],
            "ToM": [210],
            "level": ["L2"]
        }
        file1 = create_mock_excel(data1, sheet_name="Stagger Left")
        
        # File 2: snake_case headers (Old Format)
        data2 = {
            "id": ["E2"],
            "exception type": ["Stagger Left"],
            "maxValue": [300],
            "maxLocation": [200],
            "length": [5],
            "FromM": [190],
            "ToM": [210],
            "level": ["L2"]
        }
        file2 = create_mock_excel(data2, sheet_name="Stagger Left")

        files = [
            ('files', ('20260209_EAL_UP_Mainline.xlsx', file1, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')),
            ('files', ('20260208_EAL_UP_Mainline.xlsx', file2, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'))
        ]

        response = client.post("/api/analyze/compare", files=files)
        
        assert response.status_code == 200
        res = response.json()
        assert res["status"] == "success"
        assert "Stagger Left" in res["repeated"]
        assert len(res["repeated"]["Stagger Left"]) == 1
