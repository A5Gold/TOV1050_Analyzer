import pytest
import pandas as pd
from pathlib import Path
import time
from app.core.metadata_service import MetadataService

def test_backup_reliability(tmp_path):
    # Setup dummy excel
    d = {'col1': [1, 2], 'col2': [3, 4]}
    df = pd.DataFrame(data=d)
    f = tmp_path / "test.xlsx"
    df.to_excel(f, index=False)
    
    service = MetadataService(config_dir=tmp_path)
    
    # 1. Test Backup Format (.xlsx)
    # create_backup should return path to new backup
    backup_path_str = service.create_backup("test.xlsx")
    backup_path = Path(backup_path_str)
    
    assert backup_path.exists()
    assert backup_path.suffix == ".xlsx" # Expect .xlsx (Plan requirement)
    assert "backups" in str(backup_path.parent)
    
    # 2. Test Atomic Save (Behavioral check)
    # We simulate a save and ensure the file is updated correctly and backup exists
    new_data = [
        {"Exc Type": "Low Height", "Low Height L1": 4500, "Low Height L2": 4600, "Low Height L3": 4700}
    ]
    
    # This will implicitly test validation if we don't mock it, which is fine.
    # We use valid data.
    result = service.save_configuration("test.xlsx", new_data)
    assert result["status"] == "success"
    assert "backup" in result
    
    # Verify file content updated
    updated_df = pd.read_excel(f, sheet_name='threshold')
    assert len(updated_df) == 1
    assert updated_df.iloc[0]["Low Height L1"] == 4500

def test_get_metadata_sheets(tmp_path):
    # Setup multi-sheet excel
    f = tmp_path / "multi.xlsx"
    with pd.ExcelWriter(f) as writer:
        pd.DataFrame({'A': [1]}).to_excel(writer, sheet_name='threshold', index=False)
        pd.DataFrame({'B': [2], 'Class': ['LMC'], 'UP Track FromM': [0], 'UP Track ToM': [100]}).to_excel(writer, sheet_name='Exception Boundarys', index=False)
        
    service = MetadataService(config_dir=tmp_path)
    
    # Test get specific sheet
    # We want to support sheet_name argument
    data = service.get_metadata("multi.xlsx", sheet_name="Exception Boundarys")
    
    assert len(data) == 1
    assert data[0]['B'] == 2

def test_get_sheet_names(tmp_path):
    # Setup multi-sheet excel
    f = tmp_path / "sheets.xlsx"
    with pd.ExcelWriter(f) as writer:
        pd.DataFrame({'A': [1]}).to_excel(writer, sheet_name='Sheet1', index=False)
        pd.DataFrame({'B': [2]}).to_excel(writer, sheet_name='Sheet2', index=False)
        
    service = MetadataService(config_dir=tmp_path)
    
    sheets = service.get_sheet_names("sheets.xlsx")
    assert "Sheet1" in sheets
    assert "Sheet2" in sheets
    assert len(sheets) == 2

def test_get_metadata_normalizes_sheet_name(tmp_path):
    f = tmp_path / "normalize.xlsx"
    with pd.ExcelWriter(f) as writer:
        pd.DataFrame({'A': [1]}).to_excel(writer, sheet_name='LOW S1', index=False)

    service = MetadataService(config_dir=tmp_path)
    data = service.get_metadata("normalize.xlsx", sheet_name="low  s1")

    assert len(data) == 1
    assert data[0]['A'] == 1

def test_save_configuration_clears_existing_wire_wear_l2_on_reload(tmp_path):
    f = tmp_path / "wire_wear.xlsx"
    existing_data = [
        {"Class": "both", "Track Type": "both", "Exc Type": "Wire Wear", "Wire Wear L1": 7.24, "Wire Wear L2": 10.2},
        {"Class": "SCL", "Track Type": "both", "Exc Type": "Wire Wear", "Wire Wear L1": 5.8, "Wire Wear L2": 8.16},
    ]
    with pd.ExcelWriter(f) as writer:
        pd.DataFrame(existing_data).to_excel(writer, sheet_name='threshold', index=False)

    service = MetadataService(config_dir=tmp_path)
    replacement_data = [
        {"Class": "both", "Track Type": "both", "Exc Type": "Wire Wear", "Wire Wear L1": 7.24, "Wire Wear L2": None},
        {"Class": "SCL", "Track Type": "both", "Exc Type": "Wire Wear", "Wire Wear L1": 5.8, "Wire Wear L2": None},
    ]

    service.save_configuration("wire_wear.xlsx", replacement_data)
    reloaded = service.get_metadata("wire_wear.xlsx")

    by_class = {row["Class"]: row for row in reloaded if row["Exc Type"] == "Wire Wear"}
    assert by_class["both"].get("Wire Wear L2") is None
    assert by_class["SCL"].get("Wire Wear L2") is None

def test_validation_logic_stagger():
    service = MetadataService(config_dir=Path("."))
    
    # Stagger (Max Limit / Abs Mode): L1 > L2 > L3
    valid_row = {
        "Exc Type": "Stagger Left",
        "Stagger L1": 450,
        "Stagger L2": 400,
        "Stagger L3": 350
    }
    assert service.validate_row(valid_row) == True
    
    invalid_row = {
        "Exc Type": "Stagger Left",
        "Stagger L1": 300,
        "Stagger L2": 400,
        "Stagger L3": 350
    }
    assert service.validate_row(invalid_row) == False

def test_validation_logic_low_height():
    service = MetadataService(config_dir=Path("."))
    
    # Low Height (Min Limit): L1 < L2 < L3
    valid_row = {
        "Exc Type": "Low Height",
        "Low Height L1": 4500,
        "Low Height L2": 4600,
        "Low Height L3": 4700
    }
    assert service.validate_row(valid_row) == True
    
    invalid_row = {
        "Exc Type": "Low Height",
        "Low Height L1": 4800,
        "Low Height L2": 4600,
        "Low Height L3": 4700
    }
    assert service.validate_row(invalid_row) == False
