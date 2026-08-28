"""
Tests for MetadataManager boundary logic, especially EAL line section handling.
"""
import pytest
import pandas as pd
from pathlib import Path
import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.metadata import MetadataManager


@pytest.fixture
def metadata_path():
    """Path to actual metadata file"""
    # Try to find the metadata file
    possible_paths = [
        Path(r"c:\Smart Maintanence\TOV640_Analyzer\config\EAL metadata.xlsx"),
        Path(__file__).parent.parent.parent / "config" / "EAL metadata.xlsx",
        Path("../config/EAL metadata.xlsx"),
    ]
    
    for p in possible_paths:
        if p.exists():
            return p
    
    pytest.skip("Metadata file not found")


@pytest.fixture
def metadata_manager(metadata_path):
    """MetadataManager instance with actual metadata"""
    return MetadataManager(metadata_path)


def test_eal_rac_section_uses_mainline_logic(metadata_manager):
    """
    RAC section should use Mainline boundaries (exclude LMC only).
    Test fails if RAC filters for Class='RAC' specifically.
    """
    df, start_col, end_col = metadata_manager._get_boundary_df('EAL', 'UP Track', 'RAC')
    
    # RAC section MUST have boundaries (should not be empty)
    # If it's empty, it means the code is filtering for non-existent 'RAC' class
    assert not df.empty, "RAC section should have boundaries (should use Mainline logic, not filter for 'RAC' class)"
    
    # Should NOT contain LMC class
    assert 'LMC' not in df['Class'].values, "RAC should exclude LMC class"
    
    # Should contain SCL or EAL classes (Mainline-like boundaries)
    available_classes = set(df['Class'].unique())
    expected_classes = {'SCL', 'EAL'}  # Non-LMC classes from Exception Boundarys
    assert available_classes & expected_classes, f"RAC should have Mainline classes, got: {available_classes}"


def test_eal_low_section_uses_mainline_logic(metadata_manager):
    """
    LOW section should use Mainline boundaries (exclude LMC only).
    """
    df, start_col, end_col = metadata_manager._get_boundary_df('EAL', 'UP Track', 'LOW')
    
    # Should use Mainline logic (exclude LMC)
    if not df.empty:
        assert 'LMC' not in df['Class'].values, "LOW should exclude LMC class"


def test_eal_lmc_section_filters_correctly(metadata_manager):
    """
    LMC section should only contain LMC class boundaries.
    """
    df, start_col, end_col = metadata_manager._get_boundary_df('EAL', 'UP Track', 'LMC')
    
    # Should only have LMC class (or be empty if no LMC boundaries defined)
    if not df.empty:
        assert (df['Class'] == 'LMC').all(), "LMC section should only contain LMC class"


def test_eal_mainline_section_excludes_lmc(metadata_manager):
    """
    Mainline section should exclude LMC class boundaries.
    """
    df, start_col, end_col = metadata_manager._get_boundary_df('EAL', 'UP Track', 'Mainline')
    
    if not df.empty:
        assert 'LMC' not in df['Class'].values, "Mainline should exclude LMC class"
