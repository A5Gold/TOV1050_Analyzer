"""
TOV640 Analyzer - Phase 7 E2E Integration Tests
================================================
End-to-end tests for all 5 core scenarios of Phase 7:
1. Stateful 自動持久化
2. Database Record - Sub-module 1 (Exception Records)
3. Database Record - Sub-module 2 + MOCK_DATA 過濾
4. Excel 同步工作流
5. Performance validation

Version: 1.0
Date: 2026-01-30
"""

import pytest
import pandas as pd
import numpy as np
import tempfile
import time
import os
from pathlib import Path
from unittest.mock import MagicMock, patch
from io import BytesIO
from fastapi.testclient import TestClient

# Import modules
from app.main import app
from app.core.database import (
    DatabaseManager,
    save_analysis_session,
    save_exceptions_from_analysis,
    get_session_by_id,
    get_session_exceptions,
    save_exception_records_batch,
    query_exception_records,
    save_repeated_records_batch,
    query_repeated_records,
    update_repeated_record_workflow,
    count_exception_records,
    count_repeated_records,
)
from app.core.exporter import ExcelExporter


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def temp_db_path(tmp_path):
    """Create a temporary database path for testing."""
    db_path = tmp_path / "test_e2e.db"
    yield str(db_path)
    DatabaseManager.reset_instance()


@pytest.fixture
def db_manager(temp_db_path):
    """Initialize database manager with temp database."""
    DatabaseManager.reset_instance()
    db = DatabaseManager(temp_db_path)
    yield db
    DatabaseManager.reset_instance()


@pytest.fixture
def sample_exceptions():
    """Sample exception data for testing."""
    return {
        'Low Height': [
            {
                'id': 'exc-001',
                'exception type': 'Low Height',
                'level': 'L1',
                'FromM': 100000,
                'ToM': 100050,
                'length': 50,
                'maxValue': 4450,
                'maxLocation': 100025,
                'Track Type': 'Tangent',
                'Overlap': None,
                'Tension Length': None,
                'Landmark': 'Milestone 100',
                'Class': 'Mainline',
                'Threshold Value': 4500,
                'Section': 'Mainline',
            },
            {
                'id': 'exc-002',
                'exception type': 'Low Height',
                'level': 'L2',
                'FromM': 101000,
                'ToM': 101100,
                'length': 100,
                'maxValue': 4550,
                'maxLocation': 101050,
                'Track Type': 'Curve',
                'Overlap': 'OL-A',
                'Tension Length': '1500m',
                'Landmark': None,
                'Class': 'SCL',
                'Threshold Value': 4600,
                'Section': 'Mainline',
            },
        ],
        'High Height': [
            {
                'id': 'exc-003',
                'exception type': 'High Height',
                'level': 'L1',
                'FromM': 102000,
                'ToM': 102080,
                'length': 80,
                'maxValue': 5750,
                'maxLocation': 102040,
                'Track Type': 'Tangent',
                'Overlap': None,
                'Tension Length': None,
                'Landmark': None,
                'Class': 'Mainline',
                'Threshold Value': 5700,
                'Section': 'Mainline',
            },
        ],
    }


@pytest.fixture
def sample_repeated_with_mock():
    """Sample repeated exception data including MOCK_DATA."""
    return [
        # Real data
        {
            'id': 'rep-001',
            'exception type': 'Low Height',
            'level': 'L1',
            'FromM': 100000,
            'ToM': 100050,
            'length': 50,
            'maxValue': 4450,
            'maxLocation': 100025,
            'Track Type': 'Tangent',
            'Overlap': None,
            'Tension Length': None,
            'Landmark': None,
            'Class': 'Mainline',
            'Threshold Value': 4500,
            'Section': 'Mainline',
            'Previous 1': 'prev-001',
            'Previous 2': 'prev-002',
            'action': 'Keep monitoring',
        },
        {
            'id': 'rep-002',
            'exception type': 'High Height',
            'level': 'L2',
            'FromM': 102000,
            'ToM': 102080,
            'length': 80,
            'maxValue': 5750,
            'maxLocation': 102040,
            'Track Type': 'Curve',
            'Overlap': None,
            'Tension Length': None,
            'Landmark': None,
            'Class': 'SCL',
            'Threshold Value': 5700,
            'Section': 'RAC',
            'Previous 1': 'prev-003',
            'Previous 2': None,
            'action': 'Calculation',
        },
        # MOCK_DATA - should be filtered
        {
            'id': 'mock-001',
            'exception type': 'Wire Wear',
            'level': 'L1',
            'FromM': 0,
            'ToM': 100,
            'length': 100,
            'maxValue': 8.0,
            'maxLocation': 50,
            'Track Type': 'Tangent',
            'Overlap': None,
            'Tension Length': None,
            'Landmark': None,
            'Class': 'both',
            'Threshold Value': 6.0,
            'Section': 'Mainline',
            'Previous 1': 'mock-prev-001',
            'Previous 2': None,
            'action': 'Pending',
        },
        {
            'id': 'MOCK_DATA_002',
            'exception type': 'Stagger Left',
            'level': 'L2',
            'FromM': 0,
            'ToM': 200,
            'length': 200,
            'maxValue': 320,
            'maxLocation': 100,
            'Track Type': 'Tangent',
            'Overlap': None,
            'Tension Length': None,
            'Landmark': None,
            'Class': 'both',
            'Threshold Value': 300,
            'Section': 'Mainline',
            'Previous 1': None,
            'Previous 2': None,
            'action': 'Pending',
        },
    ]


# =============================================================================
# SCENARIO 1: STATEFUL 自動持久化
# =============================================================================

class TestScenario1StatefulAutoPersistence:
    """E2E tests for Stateful auto-persistence workflow."""
    
    def test_full_analysis_workflow_persists_to_database(self, db_manager, sample_exceptions):
        """
        E2E Scenario 1: Complete analysis → auto-persist → retrieve workflow.
        
        Steps:
        1. Create analysis session
        2. Save exceptions to database
        3. Retrieve session and verify data
        4. Update exception status
        5. Verify status change recorded in history
        """
        with db_manager.get_connection() as conn:
            # Step 1: Save analysis session
            session_data = {
                'line': 'EAL',
                'section': 'Mainline',
                'track': 'UP',
                'date_str': '20260130',
                'task_no': 'U1A',
                'station_start': 'HUH',
                'station_end': 'TAP',
            }
            session_id = save_analysis_session(conn, session_data)
            assert session_id is not None
            assert len(session_id) == 36  # UUID format
            
            # Step 2: Save exceptions
            saved_count = save_exceptions_from_analysis(
                conn, session_id, sample_exceptions
            )
            assert saved_count == 3  # 2 Low Height + 1 High Height
            
            # Step 3: Retrieve and verify
            session = get_session_by_id(conn, session_id)
            assert session is not None
            assert session['line'] == 'EAL'
            assert session['section'] == 'Mainline'
            assert session['total_exceptions'] == 3
            assert session['l1_count'] == 2
            assert session['l2_count'] == 1
            
            # Step 4: Get session exceptions
            exceptions = get_session_exceptions(conn, session_id)
            assert len(exceptions) == 3
            
            # Verify exception data
            low_height_excs = [e for e in exceptions if e['exception_type'] == 'Low Height']
            assert len(low_height_excs) == 2
            
            # Step 5: Update exception status
            from app.core.database import update_exception_status
            exc_id = exceptions[0]['id']
            success = update_exception_status(
                conn, exc_id, 
                status='in_progress',
                notes='Investigation started',
                assigned_to='Engineer A'
            )
            assert success
            
            # Verify status updated
            updated_exc = [e for e in get_session_exceptions(conn, session_id) 
                          if e['id'] == exc_id][0]
            assert updated_exc['current_status'] == 'in_progress'


# =============================================================================
# SCENARIO 2: DATABASE RECORD - SUB-MODULE 1
# =============================================================================

@pytest.mark.skip(reason="Sub-module 1 is deprecated")
class TestScenario2DatabaseRecordSubModule1:
    """E2E tests for Database Record Sub-module 1 (Exception Records)."""
    
    def test_save_query_export_workflow(self, client, db_manager, sample_exceptions):
        """
        E2E Scenario 2: Save → Query → Filter → Export workflow.
        
        Steps:
        1. Save exception records via API
        2. Query with various filters
        3. Verify filtering works correctly
        4. Export to Excel and verify format
        """
        # Step 1: Save exception records
        save_response = client.post(
            "/api/database/exception-records",
            json={
                'line': 'EAL',
                'track': 'UP',
                'section': 'Mainline',
                'date_str': '20260130',
                'task_no': 'U1A',
                'station_start': 'HUH',
                'station_end': 'TAP',
                'exceptions': sample_exceptions,
            }
        )
        assert save_response.status_code == 200
        result = save_response.json()
        assert result['status'] == 'success'
        assert result['saved_count'] == 3
        
        # Step 2: Query all records
        query_response = client.get("/api/database/exception-records")
        assert query_response.status_code == 200
        records = query_response.json()['records']
        assert len(records) >= 3
        
        # Step 3: Query with filters
        # Filter by level
        filter_response = client.get(
            "/api/database/exception-records?level=L1"
        )
        assert filter_response.status_code == 200
        l1_records = filter_response.json()['records']
        assert all(r['level'] == 'L1' for r in l1_records)
        
        # Filter by line
        filter_response = client.get(
            "/api/database/exception-records?line=EAL"
        )
        assert filter_response.status_code == 200
        eal_records = filter_response.json()['records']
        assert all(r['line'] == 'EAL' for r in eal_records)
        
        # Step 4: Export to Excel
        export_response = client.get(
            "/api/database/exception-records/export?line=EAL"
        )
        assert export_response.status_code == 200
        assert 'application/vnd.openxmlformats' in export_response.headers['content-type']
        
        # Verify Excel content
        excel_data = BytesIO(export_response.content)
        df = pd.read_excel(excel_data, sheet_name='Exception Records')
        assert len(df) >= 3
        assert 'exception_type' in df.columns
        assert 'level' in df.columns
    
    def test_delete_exception_record(self, client, db_manager, sample_exceptions):
        """Test deletion of exception records."""
        # Save records first
        save_response = client.post(
            "/api/database/exception-records",
            json={
                'line': 'TML',
                'track': 'DN',
                'section': 'Mainline',
                'date_str': '20260130',
                'exceptions': sample_exceptions,
            }
        )
        assert save_response.status_code == 200
        
        # Get records
        query_response = client.get("/api/database/exception-records?line=TML")
        records = query_response.json()['records']
        assert len(records) > 0
        
        # Delete first record
        record_id = records[0]['id']
        delete_response = client.delete(f"/api/database/exception-records/{record_id}")
        assert delete_response.status_code == 200
        
        # Verify deleted
        verify_response = client.get("/api/database/exception-records?line=TML")
        remaining = verify_response.json()['records']
        assert all(r['id'] != record_id for r in remaining)


# =============================================================================
# SCENARIO 3: DATABASE RECORD - SUB-MODULE 2 + MOCK_DATA 過濾
# =============================================================================

class TestScenario3MockDataFiltering:
    """E2E tests for Database Record Sub-module 2 with MOCK_DATA filtering."""
    
    def test_mock_data_filtered_on_save(self, client, db_manager, sample_repeated_with_mock):
        """
        E2E Scenario 3: Save repeated records with MOCK_DATA filtering.
        
        Steps:
        1. Submit data containing both real and mock records
        2. Verify mock data is filtered out
        3. Query and verify only real data saved
        4. Test workflow field editing
        5. Export and verify
        """
        # Step 1: Save repeated records (includes mock data)
        save_response = client.post(
            "/api/database/repeated-records",
            json={
                'line': 'EAL',
                'track': 'UP',
                'date_str': '20260130',
                'task_no': 'U1A',
                'station_start': 'HUH',
                'station_end': 'TAP',
                'repeated_exceptions': sample_repeated_with_mock,  # 4 records, 2 mock
            }
        )
        assert save_response.status_code == 200
        result = save_response.json()
        assert result['status'] == 'success'
        assert result['saved_count'] == 2  # Only 2 real records
        assert result.get('filtered_mock_count', 0) == 2  # 2 mock filtered
        
        # Step 2: Query and verify no mock data
        query_response = client.get("/api/database/repeated-records")
        assert query_response.status_code == 200
        records = query_response.json()['records']
        
        # Verify no mock data saved
        for record in records:
            assert not record['exception_id'].startswith('mock-')
            assert 'MOCK_DATA' not in record['exception_id']
        
        # Step 3: Test workflow field editing
        if len(records) > 0:
            record_id = records[0]['record_id']
            
            # Update action
            update_response = client.patch(
                f"/api/database/repeated-records/{record_id}",
                json={
                    'action': 'Verify on site',
                    'check_date': '2026-02-01',
                    'checked_by': 'Engineer A',
                    'check_result': 'Pass',
                    'remarks': 'Verified on site, no action needed',
                }
            )
            assert update_response.status_code == 200
            
            # Verify update
            verify_response = client.get("/api/database/repeated-records")
            updated_record = next(
                r for r in verify_response.json()['records'] 
                if r['record_id'] == record_id
            )
            assert updated_record['action'] == 'Verify on site'
            assert updated_record['checked_by'] == 'Engineer A'
            assert updated_record['check_result'] == 'Pass'
        
        # Step 4: Export Follow-up Action Master List
        export_response = client.get("/api/database/repeated-records/export")
        assert export_response.status_code == 200
        assert 'Exception Follow-up Master List' in export_response.headers.get(
            'content-disposition', ''
        )
    
    def test_only_mock_data_returns_400(self, client, db_manager):
        """Test that submitting only mock data returns 400 error."""
        mock_only_data = [
            {
                'id': 'mock-only-001',
                'exception type': 'Wire Wear',
                'level': 'L1',
                'FromM': 0,
                'ToM': 100,
                'length': 100,
                'maxValue': 8.0,
                'maxLocation': 50,
                'Track Type': 'Tangent',
                'Overlap': None,
                'Tension Length': None,
                'Landmark': None,
                'Class': 'both',
                'Threshold Value': 6.0,
                'Section': 'Mainline',
            },
        ]
        
        response = client.post(
            "/api/database/repeated-records",
            json={
                'line': 'EAL',
                'track': 'UP',
                'date_str': '20260130',
                'repeated_exceptions': mock_only_data,
            }
        )
        assert response.status_code == 400
        assert 'mock' in response.json()['detail'].lower()


# =============================================================================
# SCENARIO 4: EXCEL 同步工作流
# =============================================================================

class TestScenario4ExcelSyncWorkflow:
    """E2E tests for Excel export with metadata."""
    
    def test_export_contains_metadata_sheet(self, db_manager, sample_exceptions):
        """
        E2E Scenario 4: Excel export includes hidden metadata sheet.
        
        Steps:
        1. Create analysis session
        2. Export to Excel with metadata
        3. Verify hidden _Metadata sheet exists
        4. Verify metadata content
        """
        with db_manager.get_connection() as conn:
            # Step 1: Create session
            session_data = {
                'line': 'EAL',
                'section': 'Mainline',
                'track': 'UP',
                'date_str': '20260130',
            }
            session_id = save_analysis_session(conn, session_data)
            
            # Step 2: Export with metadata
            from app.core.database import get_db_version
            db_version = get_db_version(conn)
            
            metadata = {
                'session_id': session_id,
                'db_version': db_version,
                'app_version': '1.0.0',
            }
            
            # Create sample results
            results = {
                'Low Height': pd.DataFrame(sample_exceptions['Low Height']),
                'High Height': pd.DataFrame(sample_exceptions['High Height']),
            }
            
            excel_output = ExcelExporter.export_report(
                results=results,
                chart_df=None,
                metadata=metadata,
            )
            
            # Step 3: Verify hidden metadata sheet
            # export_report returns BytesIO directly
            excel_file = excel_output
            excel_file.seek(0)
            
            # Read all sheets
            xl = pd.ExcelFile(excel_file)
            sheet_names = xl.sheet_names
            
            assert '_Metadata' in sheet_names, "Metadata sheet should exist"
            
            # Step 4: Verify metadata content
            meta_df = pd.read_excel(excel_file, sheet_name='_Metadata')
            # Column names are lowercase in the actual implementation
            assert 'key' in meta_df.columns or 'Key' in meta_df.columns
            
            # Get the actual key column name
            key_col = 'key' if 'key' in meta_df.columns else 'Key'
            keys = meta_df[key_col].tolist()
            assert 'session_id' in keys
            assert 'db_version' in keys
            assert 'app_version' in keys


# =============================================================================
# SCENARIO 5: PERFORMANCE VALIDATION
# =============================================================================

@pytest.mark.skip(reason="Sub-module 1 is deprecated")
class TestScenario5Performance:
    """Performance validation tests."""
    
    def test_query_performance_1000_records(self, db_manager):
        """Test query performance with 1000 records < 300ms."""
        with db_manager.get_connection() as conn:
            # Insert 1000 records
            for i in range(100):  # 10 batches of 100
                exceptions = [
                    {
                        'id': f'perf-{i}-{j}',
                        'exception type': 'Low Height',
                        'level': ['L1', 'L2', 'L3'][j % 3],
                        'FromM': 100000 + (i * 100) + j,
                        'ToM': 100000 + (i * 100) + j + 10,
                        'length': 10,
                        'maxValue': 4450 + j,
                        'maxLocation': 100000 + (i * 100) + j + 5,
                        'Track Type': 'Tangent',
                        'Overlap': None,
                        'Tension Length': None,
                        'Landmark': None,
                        'Class': 'Mainline',
                        'Threshold Value': 4500,
                        'Section': 'Mainline',
                    }
                    for j in range(10)
                ]
                
                save_exception_records_batch(
                    conn=conn,
                    line='EAL',
                    track='UP',
                    section='Mainline',
                    date_str=f'202601{i%28+1:02d}',
                    exceptions=exceptions,
                )
            
            # Measure query time
            start = time.time()
            records = query_exception_records(conn, {})
            query_time = (time.time() - start) * 1000  # ms
            
            assert len(records) >= 1000, f"Expected 1000+ records, got {len(records)}"
            assert query_time < 300, f"Query took {query_time:.0f}ms, expected < 300ms"
    
    def test_save_performance_100_records(self, db_manager):
        """Test save performance with 100 records < 1s."""
        with db_manager.get_connection() as conn:
            exceptions = [
                {
                    'id': f'save-perf-{j}',
                    'exception type': 'High Height',
                    'level': ['L1', 'L2'][j % 2],
                    'FromM': 200000 + j * 10,
                    'ToM': 200000 + j * 10 + 5,
                    'length': 5,
                    'maxValue': 5750 + j,
                    'maxLocation': 200000 + j * 10 + 2,
                    'Track Type': 'Curve',
                    'Overlap': None,
                    'Tension Length': None,
                    'Landmark': None,
                    'Class': 'SCL',
                    'Threshold Value': 5700,
                    'Section': 'RAC',
                }
                for j in range(100)
            ]
            
            start = time.time()
            saved_count = save_exception_records_batch(
                conn=conn,
                line='TML',
                track='DN',
                section='Mainline',
                date_str='20260130',
                exceptions=exceptions,
            )
            save_time = time.time() - start
            
            assert saved_count == 100, f"Expected 100 saved, got {saved_count}"
            assert save_time < 1.0, f"Save took {save_time:.2f}s, expected < 1s"
    
    def test_api_response_time(self, client, db_manager, sample_exceptions):
        """Test API response time < 500ms."""
        # Populate some data first
        client.post(
            "/api/database/exception-records",
            json={
                'line': 'EAL',
                'track': 'UP',
                'section': 'Mainline',
                'date_str': '20260130',
                'exceptions': sample_exceptions,
            }
        )
        
        # Measure API response time
        start = time.time()
        response = client.get("/api/database/exception-records")
        response_time = (time.time() - start) * 1000  # ms
        
        assert response.status_code == 200
        assert response_time < 500, f"API took {response_time:.0f}ms, expected < 500ms"


# =============================================================================
# FULL WORKFLOW INTEGRATION TEST
# =============================================================================

@pytest.mark.skip(reason="Sub-module 1 is deprecated")
class TestFullWorkflowIntegration:
    """Complete end-to-end workflow integration test."""
    
    def test_complete_workflow(self, client, db_manager, sample_exceptions, sample_repeated_with_mock):
        """
        Complete E2E workflow testing all components together:
        
        1. Analyze and auto-persist session
        2. Save exception records to database
        3. Save repeated records (with mock filtering)
        4. Query and filter data
        5. Update workflow fields
        6. Export both record types
        7. Verify all operations
        """
        # === Phase 1: Stateful Session ===
        with db_manager.get_connection() as conn:
            session_data = {
                'line': 'EAL',
                'section': 'Mainline',
                'track': 'UP',
                'date_str': '20260130',
            }
            session_id = save_analysis_session(conn, session_data)
            saved_count = save_exceptions_from_analysis(conn, session_id, sample_exceptions)
            assert saved_count == 3
        
        # === Phase 2: Save Exception Records ===
        save_exc_response = client.post(
            "/api/database/exception-records",
            json={
                'line': 'EAL',
                'track': 'UP',
                'section': 'Mainline',
                'date_str': '20260130',
                'source_session_id': session_id,
                'exceptions': sample_exceptions,
            }
        )
        assert save_exc_response.status_code == 200
        
        # === Phase 3: Save Repeated Records (with mock filtering) ===
        save_rep_response = client.post(
            "/api/database/repeated-records",
            json={
                'line': 'EAL',
                'track': 'UP',
                'date_str': '20260130',
                'repeated_exceptions': sample_repeated_with_mock,
            }
        )
        assert save_rep_response.status_code == 200
        assert save_rep_response.json()['saved_count'] == 2  # Mock filtered
        
        # === Phase 4: Query and Filter ===
        exc_records = client.get("/api/database/exception-records?level=L1").json()['records']
        rep_records = client.get("/api/database/repeated-records").json()['records']
        
        assert len(exc_records) > 0
        assert len(rep_records) == 2
        
        # === Phase 5: Update Workflow Fields ===
        if len(rep_records) > 0:
            record_id = rep_records[0]['record_id']
            update_response = client.patch(
                f"/api/database/repeated-records/{record_id}",
                json={'action': 'No action required', 'check_result': 'N/A'}
            )
            assert update_response.status_code == 200
        
        # === Phase 6: Export ===
        exc_export = client.get("/api/database/exception-records/export")
        rep_export = client.get("/api/database/repeated-records/export")
        
        assert exc_export.status_code == 200
        assert rep_export.status_code == 200
        
        # === Phase 7: Final Verification ===
        # Verify exception records export
        exc_df = pd.read_excel(BytesIO(exc_export.content))
        assert len(exc_df) > 0
        
        # Verify repeated records export
        rep_df = pd.read_excel(BytesIO(rep_export.content))
        assert len(rep_df) == 2  # Only real data
        
        print("✓ Complete E2E workflow passed successfully!")
