"""
TOV640 Analyzer - Auto-Persistence Tests
=========================================
Tests for Task 2.3: Stateful Transformation - Auto-Persistence

Following TDD principles:
1. Write failing tests first (RED)
2. Implement minimal code to pass (GREEN)
3. Refactor as needed

Version: 1.0
Date: 2026-01-30
"""

import pytest
import pandas as pd
import numpy as np
import tempfile
import os
from pathlib import Path
from unittest.mock import MagicMock, patch
from io import BytesIO

# Import modules to test
from app.core.analyzers import ExceptionDetector
from app.core.exporter import ExcelExporter
from app.core.database import (
    DatabaseManager,
    get_session_by_id,
    get_session_exceptions,
    get_db_version,
    get_system_metadata,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def temp_db_path(tmp_path):
    """Create a temporary database path for testing."""
    db_path = tmp_path / "test_analysis.db"
    yield str(db_path)
    # Cleanup
    DatabaseManager.reset_instance()


@pytest.fixture
def mock_metadata_manager_with_thresholds():
    """Mock MetadataManager that returns valid thresholds for detection."""
    mm = MagicMock()
    
    # Mock boundaries for Class mapping
    mm.get_exception_boundaries.return_value = pd.DataFrame({
        'Class': ['Mainline']
    }, index=pd.IntervalIndex.from_arrays([100000.0], [100200.0]))
    
    # Mock Track Types
    mm.get_track_type_intervals.return_value = pd.DataFrame({
        'Track Type': ['Tangent']
    }, index=pd.IntervalIndex.from_arrays([100000.0], [100200.0]))
    
    # Mock Thresholds with proper column names
    thresholds = pd.DataFrame([
        {
            'Exc Type': 'Low Height',
            'Class': 'both',
            'Track Type': 'both',
            'Low Height L1': 4500.0,
            'Low Height L2': 4600.0
        },
        {
            'Exc Type': 'High Height',
            'Class': 'both',
            'Track Type': 'both',
            'High Height L1': 5700.0,
            'High Height L2': 5650.0
        },
        {
            'Exc Type': 'Wire Wear',
            'Class': 'both',
            'Track Type': 'both',
            'Wire Wear L1': 6.0,
            'Wire Wear L2': 7.0
        },
        {
            'Exc Type': 'Stagger Left',
            'Class': 'both',
            'Track Type': 'Tangent',
            'Stagger L1': 300.0,
            'Stagger L2': 280.0,
            'Stagger L3': 260.0
        },
        {
            'Exc Type': 'Stagger Right',
            'Class': 'both',
            'Track Type': 'Tangent',
            'Stagger L1': 300.0,
            'Stagger L2': 280.0,
            'Stagger L3': 260.0
        }
    ])
    mm.get_all_thresholds.return_value = thresholds
    
    mm.get_boundaries_for_plot.return_value = pd.DataFrame()
    mm.get_overlap_intervals.return_value = pd.DataFrame()
    mm.get_landmark_intervals.return_value = pd.DataFrame()
    
    return mm


@pytest.fixture
def sample_data_with_exceptions():
    """Create sample data that will trigger exceptions."""
    return pd.DataFrame({
        'Chainage': [100050.0, 100060.0, 100070.0, 100080.0],
        'height1': [4400.0, 4450.0, 4500.0, 5100.0],  # First 3 below threshold
        'height2': [4420.0, 4460.0, 4510.0, 5110.0],
        'height3': [4410.0, 4455.0, 4505.0, 5105.0],
        'height4': [4405.0, 4458.0, 4508.0, 5108.0],
        'stagger1': [50.0, 55.0, 60.0, 65.0],
        'stagger2': [52.0, 57.0, 62.0, 67.0],
        'stagger3': [48.0, 53.0, 58.0, 63.0],
        'stagger4': [51.0, 56.0, 61.0, 66.0],
        'wear1': [10.0, 10.5, 11.0, 11.5],
        'wear2': [10.2, 10.7, 11.2, 11.7],
        'wear3': [10.1, 10.6, 11.1, 11.6],
        'wear4': [10.15, 10.65, 11.15, 11.65],
    })


# =============================================================================
# SECTION 1: ANALYZER AUTO-PERSISTENCE TESTS (Task 2.3.2 / 2.3.3)
# =============================================================================

class TestAnalyzerAutoPersistence:
    """
    Tests for automatic persistence of analysis results to database.
    
    Requirement: When analyze() completes, results should be saved to:
    - analysis_sessions table
    - exceptions table
    """
    
    def test_analyze_returns_session_id_in_results(
        self, 
        mock_metadata_manager_with_thresholds, 
        sample_data_with_exceptions,
        temp_db_path
    ):
        """
        Test that analyze() returns a session_id in the results.
        
        Expected: results dict should contain 'session_id' key.
        """
        # Setup
        detector = ExceptionDetector(mock_metadata_manager_with_thresholds)
        
        # Act - Run analysis with database persistence
        results, boundary_df = detector.analyze(
            df=sample_data_with_exceptions,
            line='EAL',
            section='Mainline',
            track='UP',
            date_str='20260130'
        )
        
        # Assert - session_id should be in results
        assert 'session_id' in results or hasattr(detector, 'last_session_id'), \
            "analyze() should return or store a session_id for persistence tracking"
    
    def test_analyze_with_auto_save_persists_session(
        self,
        mock_metadata_manager_with_thresholds,
        sample_data_with_exceptions,
        temp_db_path
    ):
        """
        Test that analyze() with auto_save=True persists session to database.
        
        Expected: Session should exist in analysis_sessions table.
        """
        # Setup - Initialize database
        db = DatabaseManager(temp_db_path)
        detector = ExceptionDetector(mock_metadata_manager_with_thresholds)
        
        # Act - Run analysis with auto_save
        results, boundary_df = detector.analyze(
            df=sample_data_with_exceptions,
            line='EAL',
            section='Mainline',
            track='UP',
            date_str='20260130',
            auto_save=True,  # New parameter
            db_manager=db    # New parameter for dependency injection
        )
        
        # Assert - Session should be saved
        session_id = results.get('session_id') or detector.last_session_id
        assert session_id is not None, "Session ID should be generated"
        
        with db.get_connection() as conn:
            session = get_session_by_id(conn, session_id)
        
        assert session is not None, "Session should be saved to database"
        assert session['line'] == 'EAL'
        assert session['track'] == 'UP'
        assert session['section'] == 'Mainline'
        assert session['date_str'] == '20260130'
    
    def test_analyze_with_auto_save_persists_exceptions(
        self,
        mock_metadata_manager_with_thresholds,
        sample_data_with_exceptions,
        temp_db_path
    ):
        """
        Test that analyze() with auto_save=True persists exceptions to database.
        
        Expected: Exceptions from analysis should exist in exceptions table.
        """
        # Setup
        db = DatabaseManager(temp_db_path)
        detector = ExceptionDetector(mock_metadata_manager_with_thresholds)
        
        # Act - Run analysis with auto_save
        results, boundary_df = detector.analyze(
            df=sample_data_with_exceptions,
            line='EAL',
            section='Mainline',
            track='UP',
            date_str='20260130',
            auto_save=True,
            db_manager=db
        )
        
        # Count total exceptions in results
        total_exc_in_results = 0
        for exc_type, exc_data in results.items():
            if exc_type == 'session_id':
                continue
            if isinstance(exc_data, pd.DataFrame) and not exc_data.empty:
                total_exc_in_results += len(exc_data)
        
        # Assert - Exceptions should be saved
        session_id = results.get('session_id') or detector.last_session_id
        
        with db.get_connection() as conn:
            saved_exceptions = get_session_exceptions(conn, session_id)
        
        assert len(saved_exceptions) == total_exc_in_results, \
            f"All {total_exc_in_results} exceptions should be saved to database"
    
    def test_analyze_without_auto_save_does_not_persist(
        self,
        mock_metadata_manager_with_thresholds,
        sample_data_with_exceptions,
        temp_db_path
    ):
        """
        Test that analyze() without auto_save=True does NOT persist to database.
        
        Expected: No session or exceptions saved when auto_save is False/missing.
        """
        # Setup
        db = DatabaseManager(temp_db_path)
        detector = ExceptionDetector(mock_metadata_manager_with_thresholds)
        
        # Act - Run analysis WITHOUT auto_save
        results, boundary_df = detector.analyze(
            df=sample_data_with_exceptions,
            line='EAL',
            section='Mainline',
            track='UP',
            date_str='20260130',
            auto_save=False,  # Explicitly disabled
            db_manager=db
        )
        
        # Assert - No session should be saved (session_id not set or sessions table empty)
        session_id = results.get('session_id')
        
        if session_id:
            with db.get_connection() as conn:
                session = get_session_by_id(conn, session_id)
            assert session is None, "Session should NOT be saved when auto_save=False"
    
    def test_analyze_auto_save_backwards_compatible(
        self,
        mock_metadata_manager_with_thresholds,
        sample_data_with_exceptions
    ):
        """
        Test that analyze() is backwards compatible (works without new parameters).
        
        Expected: Original API (without auto_save, db_manager) still works.
        """
        detector = ExceptionDetector(mock_metadata_manager_with_thresholds)
        
        # Act - Original API call (no new parameters)
        results, boundary_df = detector.analyze(
            df=sample_data_with_exceptions,
            line='EAL',
            section='Mainline',
            track='UP',
            date_str='20260130'
        )
        
        # Assert - Should not raise, should return valid results
        assert 'Low Height' in results
        assert isinstance(results['Low Height'], pd.DataFrame)
    
    def test_analyze_with_file_info_persists_metadata(
        self,
        mock_metadata_manager_with_thresholds,
        sample_data_with_exceptions,
        temp_db_path
    ):
        """
        Test that file metadata (name) is persisted with session.
        
        Note: v_sessions_with_stats view only includes raw_data_file_name for performance.
        Full file info (path, size) is stored in analysis_sessions table but not exposed in view.
        """
        # Setup
        db = DatabaseManager(temp_db_path)
        detector = ExceptionDetector(mock_metadata_manager_with_thresholds)
        
        # Act
        results, _ = detector.analyze(
            df=sample_data_with_exceptions,
            line='EAL',
            section='Mainline',
            track='UP',
            date_str='20260130',
            auto_save=True,
            db_manager=db,
            raw_data_file_path='C:/data/test.datac',
            raw_data_file_name='test.datac',
            raw_data_file_size=1024
        )
        
        # Assert - Check view data (raw_data_file_name)
        session_id = results.get('session_id') or detector.last_session_id
        with db.get_connection() as conn:
            session = get_session_by_id(conn, session_id)
        
        assert session['raw_data_file_name'] == 'test.datac'
        
        # Also verify full data is stored in table (query directly)
        with db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT raw_data_file_path, raw_data_file_size FROM analysis_sessions WHERE id = ?",
                (session_id,)
            )
            row = cursor.fetchone()
        
        assert row['raw_data_file_path'] == 'C:/data/test.datac'
        assert row['raw_data_file_size'] == 1024


# =============================================================================
# SECTION 2: EXPORTER METADATA SHEET TESTS (Task 2.3.4 / 2.3.5)
# =============================================================================

class TestExporterMetadataSheet:
    """
    Tests for hidden metadata sheet in Excel exports.
    
    Requirement: export_report() should add a hidden "_Metadata" sheet with:
    - session_id
    - db_version
    - export_timestamp
    - schema_version
    """
    
    def test_export_report_includes_metadata_sheet(self, temp_db_path):
        """
        Test that export_report() includes a _Metadata sheet.
        """
        # Setup - Sample results
        results = {
            'Low Height': pd.DataFrame([{
                'id': 'test-001',
                'exception type': 'Low Height',
                'level': 'L1',
                'FromM': 100.0,
                'ToM': 200.0,
                'length': 100.0,
                'maxValue': 4400.0,
                'maxLocation': 150.0,
                'Track Type': 'Tangent',
                'Overlap': None,
                'Tension Length': None,
                'Landmark': None,
                'Class': 'Mainline',
                'Section': 'Mainline',
                'Threshold Value': 4500.0
            }])
        }
        
        metadata = {
            'session_id': 'test-session-123',
            'db_version': 42,
            'export_timestamp': '2026-01-30T10:30:00',
            'schema_version': '1.0'
        }
        
        # Act
        output = ExcelExporter.export_report(
            results,
            metadata=metadata  # New parameter
        )
        
        # Assert - Read the Excel and check for _Metadata sheet
        output.seek(0)
        with pd.ExcelFile(output, engine='openpyxl') as xlsx:
            sheet_names = xlsx.sheet_names
        
        assert '_Metadata' in sheet_names, "Export should include _Metadata sheet"
    
    def test_export_report_metadata_sheet_contains_required_fields(self, temp_db_path):
        """
        Test that _Metadata sheet contains required fields.
        """
        # Setup
        results = {
            'Low Height': pd.DataFrame()
        }
        
        metadata = {
            'session_id': 'session-abc-123',
            'db_version': 99,
            'export_timestamp': '2026-01-30T15:45:00',
            'schema_version': '1.0.0'
        }
        
        # Act
        output = ExcelExporter.export_report(results, metadata=metadata)
        
        # Assert
        output.seek(0)
        with pd.ExcelFile(output, engine='openpyxl') as xlsx:
            metadata_df = pd.read_excel(xlsx, sheet_name='_Metadata')
        
        # Check columns
        assert 'key' in metadata_df.columns
        assert 'value' in metadata_df.columns
        
        # Check values
        keys = metadata_df['key'].tolist()
        assert 'session_id' in keys
        assert 'db_version' in keys
        assert 'export_timestamp' in keys
        assert 'schema_version' in keys
        
        # Verify values
        meta_dict = dict(zip(metadata_df['key'], metadata_df['value']))
        assert meta_dict['session_id'] == 'session-abc-123'
        assert str(meta_dict['db_version']) == '99'
    
    def test_export_report_metadata_sheet_is_hidden(self, temp_db_path):
        """
        Test that _Metadata sheet is hidden by default.
        """
        import openpyxl
        
        # Setup
        results = {'Low Height': pd.DataFrame()}
        metadata = {
            'session_id': 'test',
            'db_version': 1,
            'export_timestamp': '2026-01-30T00:00:00',
            'schema_version': '1.0'
        }
        
        # Act
        output = ExcelExporter.export_report(results, metadata=metadata)
        
        # Assert - Check sheet visibility using openpyxl
        output.seek(0)
        wb = openpyxl.load_workbook(output)
        meta_sheet = wb['_Metadata']
        
        assert meta_sheet.sheet_state == 'hidden', "_Metadata sheet should be hidden"
    
    def test_export_report_without_metadata_backwards_compatible(self):
        """
        Test that export_report() works without metadata parameter (backwards compatible).
        """
        # Setup
        results = {
            'Low Height': pd.DataFrame([{
                'id': 'test-001',
                'exception type': 'Low Height',
                'level': 'L1',
                'FromM': 100.0,
                'ToM': 200.0
            }])
        }
        
        # Act - Call without metadata parameter
        output = ExcelExporter.export_report(results)
        
        # Assert - Should not raise and should produce valid Excel
        output.seek(0)
        with pd.ExcelFile(output, engine='openpyxl') as xlsx:
            sheet_names = xlsx.sheet_names
        
        assert 'Summary' in sheet_names
        # _Metadata sheet is optional when metadata not provided
    
    def test_export_report_metadata_includes_app_version(self, temp_db_path):
        """
        Test that metadata sheet includes application version.
        """
        # Setup
        results = {'Low Height': pd.DataFrame()}
        metadata = {
            'session_id': 'test',
            'db_version': 1,
            'export_timestamp': '2026-01-30T00:00:00',
            'schema_version': '1.0',
            'app_version': '2.0.0'
        }
        
        # Act
        output = ExcelExporter.export_report(results, metadata=metadata)
        
        # Assert
        output.seek(0)
        with pd.ExcelFile(output, engine='openpyxl') as xlsx:
            metadata_df = pd.read_excel(xlsx, sheet_name='_Metadata')
        
        keys = metadata_df['key'].tolist()
        assert 'app_version' in keys


# =============================================================================
# SECTION 3: INTEGRATION TESTS
# =============================================================================

class TestAutoPersistenceIntegration:
    """
    Integration tests for the full auto-persistence workflow.
    """
    
    def test_full_workflow_analyze_and_export_with_metadata(
        self,
        mock_metadata_manager_with_thresholds,
        sample_data_with_exceptions,
        temp_db_path
    ):
        """
        Test complete workflow: analyze with auto_save, then export with metadata.
        """
        # Setup
        db = DatabaseManager(temp_db_path)
        detector = ExceptionDetector(mock_metadata_manager_with_thresholds)
        
        # Step 1: Analyze with auto_save
        results, boundary_df = detector.analyze(
            df=sample_data_with_exceptions,
            line='EAL',
            section='Mainline',
            track='UP',
            date_str='20260130',
            auto_save=True,
            db_manager=db
        )
        
        session_id = results.get('session_id') or detector.last_session_id
        
        # Step 2: Get db version
        with db.get_connection() as conn:
            db_version = get_db_version(conn)
        
        # Step 3: Export with metadata
        export_results = {k: v for k, v in results.items() if k != 'session_id'}
        metadata = {
            'session_id': session_id,
            'db_version': db_version,
            'export_timestamp': '2026-01-30T10:00:00',
            'schema_version': '1.0'
        }
        
        output = ExcelExporter.export_report(export_results, metadata=metadata)
        
        # Step 4: Verify export contains session metadata
        output.seek(0)
        with pd.ExcelFile(output, engine='openpyxl') as xlsx:
            meta_df = pd.read_excel(xlsx, sheet_name='_Metadata')
        
        meta_dict = dict(zip(meta_df['key'], meta_df['value']))
        assert meta_dict['session_id'] == session_id
        assert str(meta_dict['db_version']) == str(db_version)
    
    def test_history_compare_export_with_metadata(self, temp_db_path):
        """
        Test that export_history_compare also supports metadata.
        """
        # Setup
        compare_data = pd.DataFrame([{
            'id': 'test-001',
            'FromM': 100.0,
            'ToM': 200.0,
            'length': 100.0,
            'exception type': 'Low Height',
            'maxValue': 4400.0,
            'maxLocation': 150.0,
            'Landmark': None,
            'Tension Length': None,
            'Track Type': 'Tangent',
            'level': 'L1',
            'Previous 1': 'prev-001',
            'Previous 2': None
        }])
        
        metadata = {
            'session_id': 'history-session-456',
            'db_version': 10,
            'export_timestamp': '2026-01-30T12:00:00',
            'schema_version': '1.0',
            'comparison_files': ['file1.xlsx', 'file2.xlsx', 'file3.xlsx']
        }
        
        # Act
        output = ExcelExporter.export_history_compare(
            compare_data,
            file_names=['file1.xlsx', 'file2.xlsx', 'file3.xlsx'],
            metadata=metadata
        )
        
        # Assert
        output.seek(0)
        with pd.ExcelFile(output, engine='openpyxl') as xlsx:
            sheet_names = xlsx.sheet_names
        
        assert '_Metadata' in sheet_names, "History compare export should include metadata sheet"
