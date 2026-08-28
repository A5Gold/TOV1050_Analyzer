from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from app.main import app
from app.api.endpoints.metadata import get_metadata_service

client = TestClient(app)

MOCK_METADATA = [
    {"Class": "Mainline", "Exc Type": "Low Height", "Low Height L1": 4500, "Low Height L2": 4600}
]

def test_get_metadata():
    mock_service = MagicMock()
    mock_service.get_metadata.return_value = MOCK_METADATA
    
    app.dependency_overrides[get_metadata_service] = lambda: mock_service
    
    response = client.get("/api/metadata/EAL%20metadata.xlsx")
    
    assert response.status_code == 200
    assert response.json() == MOCK_METADATA
    
    app.dependency_overrides = {}

def test_update_metadata_success():
    mock_service = MagicMock()
    mock_service.save_configuration.return_value = {"status": "success", "backup": "path/to/backup.bak"}
    
    app.dependency_overrides[get_metadata_service] = lambda: mock_service
    
    response = client.post("/api/metadata/EAL%20metadata.xlsx", json=MOCK_METADATA)
    
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    
    app.dependency_overrides = {}

def test_update_metadata_validation_error():
    mock_service = MagicMock()
    mock_service.save_configuration.side_effect = ValueError("Validation failed")
    
    app.dependency_overrides[get_metadata_service] = lambda: mock_service
    
    response = client.post("/api/metadata/EAL%20metadata.xlsx", json=MOCK_METADATA)
    
    assert response.status_code == 400
    assert "Validation failed" in response.json()["detail"]
    
    app.dependency_overrides = {}

def test_get_sheet_names():
    mock_service = MagicMock()
    mock_service.get_sheet_names.return_value = ["Sheet1", "Sheet2"]
    
    app.dependency_overrides[get_metadata_service] = lambda: mock_service
    
    response = client.get("/api/metadata/EAL%20metadata.xlsx/sheets")
    
    assert response.status_code == 200
    assert response.json() == ["Sheet1", "Sheet2"]
    
    app.dependency_overrides = {}
