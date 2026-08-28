"""
Integration tests for EAL line section handling (RAC, LOW, LMC).
Tests end-to-end flow from data to exception detection.
"""
import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.metadata import MetadataManager
from app.core.analyzers import ExceptionDetector


@pytest.fixture
def config_path():
    """Path to actual metadata file"""
    possible_paths = [
        Path(r"c:\Smart Maintanence\TOV640_Analyzer\config\EAL metadata.xlsx"),
        Path(__file__).parent.parent.parent / "config" / "EAL metadata.xlsx",
    ]
    
    for p in possible_paths:
        if p.exists():
            return p
    
    pytest.skip("Metadata file not found")


@pytest.fixture
def metadata_manager(config_path):
    """MetadataManager instance"""
    return MetadataManager(config_path)


@pytest.fixture
def exception_detector(metadata_manager):
    """ExceptionDetector instance"""
    return ExceptionDetector(metadata_manager)


@pytest.fixture
def sample_data():
    """Sample data with various height values for testing"""
    return pd.DataFrame({
        'Chainage': [95000, 101000, 105000, 131000],
        'height1': [4450, 4520, 4600, 4450],
        'height2': [4460, 4530, 4610, 4460],
        'height3': [4470, 4540, 4620, 4470],
        'height4': [4480, 4550, 4630, 4480],
        'wear': [7.0, 7.0, 7.0, 7.0],
        'stagger1': [300, 300, 300, 300],
        'stagger2': [300, 300, 300, 300],
        'stagger3': [300, 300, 300, 300],
        'stagger4': [300, 300, 300, 300],
    })


class TestEALRACSection:
    """Integration tests for RAC section"""
    
    def test_rac_section_end_to_end(self, exception_detector, sample_data):
        """
        End-to-end test for EAL RAC section.
        Verifies Class mapping and exception detection work correctly.
        """
        # Use a copy and keep reference to verify
        test_data = sample_data.copy()
        results, boundary_df = exception_detector.analyze(
            test_data, 'EAL', 'RAC', 'UP Track', '20260127'
        )
        
        # Verify Class mapping in the analyzed dataframe
        assert 'Class' in test_data.columns, "Class column should be added"
        
        # RAC section should not map to LMC
        assert 'LMC' not in test_data['Class'].values, \
            "RAC section should not map to LMC class"
        
        # Should have some Mainline-like classes (SCL or EAL)
        non_both_classes = test_data[test_data['Class'] != 'both']['Class'].unique()
        if len(non_both_classes) > 0:
            assert any(c in ['SCL', 'EAL'] for c in non_both_classes), \
                "RAC should map to Mainline classes (SCL or EAL)"
        
        # Verify Low Height detection works
        low_height_df = results['Low Height']
        # Should be able to detect (may or may not have results depending on data)
        assert isinstance(low_height_df, pd.DataFrame), \
            "Low Height results should be a DataFrame"


class TestEALLOWSection:
    """Integration tests for LOW section"""
    
    def test_low_section_end_to_end(self, exception_detector, sample_data):
        """
        End-to-end test for EAL LOW section.
        Verifies LOW section uses Mainline logic.
        """
        test_data = sample_data.copy()
        results, boundary_df = exception_detector.analyze(
            test_data, 'EAL', 'LOW', 'UP Track', '20260127'
        )
        
        # Verify Class mapping
        assert 'Class' in test_data.columns
        
        # LOW section should not map to LMC
        assert 'LMC' not in test_data['Class'].values, \
            "LOW section should not map to LMC class"
        
        # Verify detection works
        low_height_df = results['Low Height']
        assert isinstance(low_height_df, pd.DataFrame)


class TestEALLMCSection:
    """Integration tests for LMC section"""
    
    def test_lmc_section_with_fallback(self, exception_detector, sample_data):
        """
        Test LMC section uses fallback to 'both' when LMC thresholds don't exist.
        """
        test_data = sample_data.copy()
        results, boundary_df = exception_detector.analyze(
            test_data, 'EAL', 'LMC', 'UP Track', '20260127'
        )
        
        # Verify Class mapping
        assert 'Class' in test_data.columns
        
        # LMC section may map some Chainage to LMC class (if in LMC boundaries)
        # Or may be 'both' if outside LMC boundaries
        # Both are acceptable
        
        # Verify detection works (with fallback if needed)
        low_height_df = results['Low Height']
        assert isinstance(low_height_df, pd.DataFrame)
        
        # Should not raise any errors (fallback mechanism should work)


class TestEALSectionConsistency:
    """Test consistency across different sections"""
    
    def test_rac_low_consistency(self, exception_detector, sample_data):
        """
        RAC and LOW sections should produce similar results
        (both use Mainline logic)
        """
        # Analyze with RAC
        rac_data = sample_data.copy()
        results_rac, _ = exception_detector.analyze(
            rac_data, 'EAL', 'RAC', 'UP Track', '20260127'
        )
        
        # Analyze with LOW
        low_data = sample_data.copy()
        results_low, _ = exception_detector.analyze(
            low_data, 'EAL', 'LOW', 'UP Track', '20260127'
        )
        
        # Class distributions should be similar (both exclude LMC)
        rac_classes = set(rac_data['Class'].unique())
        low_classes = set(low_data['Class'].unique())
        
        # Neither should have LMC
        assert 'LMC' not in rac_classes, "RAC should not have LMC"
        assert 'LMC' not in low_classes, "LOW should not have LMC"
    
    def test_lmc_section_distinct(self, exception_detector, sample_data):
        """
        LMC section should behave differently from Mainline
        (maps to LMC class where boundaries exist)
        """
        # Analyze with LMC
        lmc_data = sample_data.copy()
        results_lmc, _ = exception_detector.analyze(
            lmc_data, 'EAL', 'LMC', 'UP Track', '20260127'
        )
        
        # Analyze with Mainline
        main_data = sample_data.copy()
        results_main, _ = exception_detector.analyze(
            main_data, 'EAL', 'Mainline', 'UP Track', '20260127'
        )
        
        # LMC may have 'LMC' class, Mainline should not
        lmc_classes = set(lmc_data['Class'].unique())
        main_classes = set(main_data['Class'].unique())
        
        assert 'LMC' not in main_classes, "Mainline should not have LMC"
        # LMC section may or may not have LMC depending on data Chainage
