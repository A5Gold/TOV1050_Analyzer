"""
TOV640 Analyzer - Database Module Unit Tests
=============================================
Tests for DatabaseManager and all CRUD operations.

Test Coverage:
- Database initialization and schema creation
- Thread-safe singleton pattern
- All CRUD functions for Stateful Transformation
- All CRUD functions for Database Record Module (Sub-module 1 & 2)
- Trigger verification
- Error handling (constraints, foreign keys)
"""

import pytest
import sqlite3
import tempfile
import threading
import time
import os
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.database import (
    DatabaseManager,
    get_database,
    # System metadata
    get_system_metadata,
    set_system_metadata,
    get_db_version,
    # Stateful - Sessions
    generate_session_id,
    save_analysis_session,
    save_exceptions_from_analysis,
    get_sessions,
    get_session_by_id,
    get_session_exceptions,
    update_exception_status,
    # Sub-module 1
    save_exception_records_batch,
    query_exception_records,
    delete_exception_record,
    export_exception_records_to_df,
    # Sub-module 2
    save_repeated_records_batch,
    query_repeated_records,
    update_repeated_record_workflow,
    delete_repeated_record,
    export_repeated_records_to_df,
    # Reports
    save_report_record,
    # Utilities
    get_exception_summary_by_date,
    get_pending_critical_exceptions,
    get_pending_repeated_exceptions,
    count_exception_records,
    count_repeated_records,
    # Phase 10.10 - Bug 1.3
    get_distinct_values,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def temp_db_path(tmp_path):
    """Create a temporary database path."""
    return str(tmp_path / "test_analysis.db")


@pytest.fixture
def db_manager(temp_db_path):
    """Create a fresh DatabaseManager instance for each test."""
    # Reset singleton before each test
    DatabaseManager.reset_instance()
    
    # Create new instance with temp path
    manager = DatabaseManager(db_path=temp_db_path)
    
    yield manager
    
    # Cleanup
    manager.close()
    DatabaseManager.reset_instance()


@pytest.fixture
def sample_session_data():
    """Sample session data for testing."""
    return {
        'line': 'EAL',
        'section': 'Mainline',
        'track': 'UP',
        'date_str': '20260130',
        'raw_data_file_path': 'C:/data/test.datac',
        'raw_data_file_name': 'test.datac',
        'raw_data_file_size': 1024000,
        'task_no': 'TASK-001',
        'station_start': 'HUH',
        'station_end': 'LOW',
    }


@pytest.fixture
def sample_exceptions():
    """Sample exception data for testing."""
    return {
        'Low Height': [
            {
                'id': 'exc-001',
                'exception type': 'Low Height',
                'level': 'L1',
                'FromM': 100500,
                'ToM': 100600,
                'length': 100,
                'maxValue': 4450,
                'maxLocation': 100550,
                'Track Type': 'Tangent',
                'Overlap': None,
                'Tension Length': '1500',
                'Landmark': 'KM100',
                'Class': 'Mainline',
                'Threshold Value': 4500,
                'Section': 'Mainline',
            },
            {
                'id': 'exc-002',
                'exception type': 'Low Height',
                'level': 'L2',
                'FromM': 100700,
                'ToM': 100750,
                'length': 50,
                'maxValue': 4520,
                'maxLocation': 100720,
                'Track Type': 'Curve',
                'Overlap': 'OL-001',
                'Tension Length': None,
                'Landmark': 'KM100.7',
                'Class': 'Mainline',
                'Threshold Value': 4550,
                'Section': 'Mainline',
            },
        ],
        'Stagger Left': [
            {
                'id': 'exc-003',
                'exception type': 'Stagger Left',
                'level': 'L1',
                'FromM': 101000,
                'ToM': 101050,
                'length': 50,
                'maxValue': 250,
                'maxLocation': 101025,
                'Track Type': 'Tangent',
                'Overlap': None,
                'Tension Length': '1500',
                'Landmark': 'KM101',
                'Class': 'Mainline',
                'Threshold Value': 200,
                'Section': 'Mainline',
            },
        ],
    }


@pytest.fixture
def sample_repeated_exceptions():
    """Sample repeated exception data for testing (including mock data)."""
    return [
        {
            'id': 'rep-001',
            'exception type': 'Low Height',
            'level': 'L1',
            'FromM': 100500,
            'ToM': 100600,
            'length': 100,
            'maxValue': 4450,
            'maxLocation': 100550,
            'Track Type': 'Tangent',
            'Overlap': None,
            'Class': 'Mainline',
            'Section': 'Mainline',
            'Previous 1': 'prev1-001',
            'Previous 2': 'prev2-001',
            'repeat_count': 3,
            'action': 'Keep monitoring',
        },
        {
            'id': 'rep-002',
            'exception type': 'Stagger Left',
            'level': 'L2',
            'FromM': 101000,
            'ToM': 101050,
            'length': 50,
            'maxValue': 220,
            'maxLocation': 101025,
            'Track Type': 'Curve',
            'Overlap': None,
            'Class': 'Mainline',
            'Section': 'Mainline',
            'Previous 1': 'prev1-002',
            'Previous 2': None,
            'repeat_count': 2,
            'action': 'Pending',
        },
        # MOCK_DATA - should be filtered out
        {
            'id': 'mock-001',
            'exception type': 'Wire Wear',
            'level': 'L3',
            'FromM': 102000,
            'ToM': 102100,
            'length': 100,
            'maxValue': 8,
            'maxLocation': 102050,
            'Track Type': 'Tangent',
            'Class': 'Mainline',
            'Section': 'Mainline',
            'Previous 1': None,
            'Previous 2': None,
            'repeat_count': 2,
        },
        {
            'id': 'mock-another-test',
            'exception type': 'High Height',
            'level': 'L2',
            'FromM': 103000,
            'ToM': 103100,
            'length': 100,
            'maxValue': 5880,
            'maxLocation': 103050,
            'Track Type': 'Tangent',
            'Class': 'Mainline',
            'Section': 'Mainline',
        },
    ]


# =============================================================================
# TEST: DATABASE INITIALIZATION
# =============================================================================

class TestDatabaseInitialization:
    """Tests for database initialization and schema creation."""
    
    def test_database_creates_file(self, db_manager, temp_db_path):
        """Test that database file is created."""
        assert Path(temp_db_path).exists()
    
    def test_schema_creates_all_tables(self, db_manager):
        """Test that all 7 tables are created."""
        expected_tables = [
            'analysis_sessions',
            'exceptions',
            'exception_history',
            'reports',
            'system_metadata',
            'saved_repeated_exceptions',
            'schema_migrations',
        ]
        
        with db_manager.get_connection() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
            tables = [row['name'] for row in cursor.fetchall()]
        
        for table in expected_tables:
            assert table in tables, f"Table '{table}' not found"
    
    def test_schema_creates_views(self, db_manager):
        """Test that all 4 views are created."""
        expected_views = [
            'v_sessions_with_stats',
            'v_pending_critical_exceptions',
            'v_repeated_exception_summary_by_date',
            'v_pending_repeated_exceptions',
        ]
        
        with db_manager.get_connection() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='view' ORDER BY name"
            )
            views = [row['name'] for row in cursor.fetchall()]
        
        for view in expected_views:
            assert view in views, f"View '{view}' not found"
    
    def test_schema_creates_indexes(self, db_manager):
        """Test that indexes are created (at least 15)."""
        with db_manager.get_connection() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
            )
            indexes = cursor.fetchall()
        
        assert len(indexes) >= 15, f"Expected at least 15 indexes, got {len(indexes)}"
    
    def test_system_metadata_initialized(self, db_manager):
        """Test that system_metadata has default values."""
        with db_manager.get_connection() as conn:
            schema_version = get_system_metadata(conn, 'schema_version')
            db_version = get_db_version(conn)
        
        assert schema_version == '1.7'
        assert db_version >= 1

    def test_migration_adds_repeated_record_columns(self, temp_db_path):
        """Legacy DBs missing 1.1 columns should be migrated on init."""
        conn = sqlite3.connect(temp_db_path)
        conn.execute("""
            CREATE TABLE saved_repeated_exceptions (
                record_id INTEGER PRIMARY KEY AUTOINCREMENT,
                exception_id TEXT NOT NULL,
                exception_type TEXT NOT NULL,
                level TEXT NOT NULL,
                from_m REAL NOT NULL,
                to_m REAL NOT NULL,
                length REAL,
                max_value REAL,
                max_location REAL,
                track_type TEXT,
                overlap TEXT,
                tension_length TEXT,
                landmark TEXT,
                class TEXT,
                threshold_value REAL,
                section TEXT,
                previous_1 TEXT,
                previous_2 TEXT,
                repeat_count INTEGER DEFAULT 2,
                action TEXT,
                check_date TEXT,
                checked_by TEXT,
                check_result TEXT,
                remarks TEXT,
                line TEXT NOT NULL,
                track TEXT NOT NULL,
                date_str TEXT NOT NULL,
                task_no TEXT,
                station_start TEXT,
                station_end TEXT,
                latest_file_name TEXT,
                comparison_files TEXT,
                saved_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                saved_by TEXT,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(exception_id, line, track, date_str)
            )
        """)
        conn.execute("""
            CREATE TABLE system_metadata (
                key TEXT PRIMARY KEY,
                value TEXT,
                description TEXT,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                description TEXT
            )
        """)
        conn.execute("INSERT INTO system_metadata (key, value) VALUES ('schema_version', '1.0')")
        conn.commit()
        conn.close()

        DatabaseManager.reset_instance()
        manager = DatabaseManager(db_path=temp_db_path)

        with manager.get_connection() as migrated_conn:
            cursor = migrated_conn.execute("PRAGMA table_info(saved_repeated_exceptions)")
            columns = {row['name'] for row in cursor.fetchall()}

        required_columns = {
            'reoccurrence_id',
            'verify_deadline',
            'verify_date',
            'verify_result',
            'verified_by',
            'adjust_deadline',
            'adjust_date',
            'adjust_result',
            'adjusted_by',
        }
        assert required_columns.issubset(columns)

        manager.close()
        DatabaseManager.reset_instance()
    
    def test_wal_mode_enabled(self, db_manager):
        """Test that WAL mode is enabled."""
        with db_manager.get_connection() as conn:
            cursor = conn.execute("PRAGMA journal_mode")
            mode = cursor.fetchone()[0]
        
        assert mode.lower() == 'wal'
    
    def test_foreign_keys_enabled(self, db_manager):
        """Test that foreign keys are enabled."""
        with db_manager.get_connection() as conn:
            cursor = conn.execute("PRAGMA foreign_keys")
            enabled = cursor.fetchone()[0]
        
        assert enabled == 1


# =============================================================================
# TEST: SINGLETON PATTERN
# =============================================================================

class TestSingletonPattern:
    """Tests for thread-safe singleton pattern."""
    
    def test_singleton_returns_same_instance(self, temp_db_path):
        """Test that multiple calls return the same instance."""
        DatabaseManager.reset_instance()
        
        db1 = DatabaseManager(db_path=temp_db_path)
        db2 = DatabaseManager()
        db3 = get_database()
        
        assert db1 is db2
        assert db2 is db3
        
        DatabaseManager.reset_instance()
    
    def test_thread_safe_initialization(self, temp_db_path):
        """Test that concurrent initialization is thread-safe."""
        DatabaseManager.reset_instance()
        
        instances = []
        errors = []
        
        def create_instance():
            try:
                instance = DatabaseManager(db_path=temp_db_path)
                instances.append(instance)
            except Exception as e:
                errors.append(e)
        
        threads = [threading.Thread(target=create_instance) for _ in range(10)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(errors) == 0, f"Errors during initialization: {errors}"
        assert len(set(id(i) for i in instances)) == 1, "Multiple instances created"
        
        DatabaseManager.reset_instance()


# =============================================================================
# TEST: STATEFUL TRANSFORMATION - SESSIONS
# =============================================================================

class TestStatefulSessions:
    """Tests for analysis session CRUD operations."""
    
    def test_save_analysis_session(self, db_manager, sample_session_data):
        """Test saving a new analysis session."""
        with db_manager.get_connection() as conn:
            session_id = save_analysis_session(conn, sample_session_data)
        
        assert session_id is not None
        assert len(session_id) == 36  # UUID format
    
    def test_get_session_by_id(self, db_manager, sample_session_data):
        """Test retrieving a session by ID."""
        with db_manager.get_connection() as conn:
            session_id = save_analysis_session(conn, sample_session_data)
            session = get_session_by_id(conn, session_id)
        
        assert session is not None
        assert session['line'] == 'EAL'
        assert session['track'] == 'UP'
        assert session['date_str'] == '20260130'
    
    def test_get_sessions_with_filters(self, db_manager, sample_session_data):
        """Test querying sessions with filters."""
        with db_manager.get_connection() as conn:
            # Save multiple sessions
            save_analysis_session(conn, sample_session_data)
            
            tml_session = sample_session_data.copy()
            tml_session['line'] = 'TML'
            save_analysis_session(conn, tml_session)
            
            # Query with filter
            eal_sessions = get_sessions(conn, filters={'line': 'EAL'})
            all_sessions = get_sessions(conn)
        
        assert len(eal_sessions) == 1
        assert len(all_sessions) == 2
    
    def test_save_exceptions_from_analysis(self, db_manager, sample_session_data, sample_exceptions):
        """Test saving exceptions during analysis."""
        with db_manager.get_connection() as conn:
            session_id = save_analysis_session(conn, sample_session_data)
            count = save_exceptions_from_analysis(conn, session_id, sample_exceptions)
        
        assert count == 3  # 2 Low Height + 1 Stagger Left
    
    def test_get_session_exceptions(self, db_manager, sample_session_data, sample_exceptions):
        """Test retrieving exceptions for a session."""
        with db_manager.get_connection() as conn:
            session_id = save_analysis_session(conn, sample_session_data)
            save_exceptions_from_analysis(conn, session_id, sample_exceptions)
            
            exceptions = get_session_exceptions(conn, session_id)
            l1_exceptions = get_session_exceptions(conn, session_id, filters={'level': 'L1'})
        
        assert len(exceptions) == 3
        assert len(l1_exceptions) == 2
    
    def test_update_exception_status(self, db_manager, sample_session_data, sample_exceptions):
        """Test updating exception status."""
        with db_manager.get_connection() as conn:
            session_id = save_analysis_session(conn, sample_session_data)
            save_exceptions_from_analysis(conn, session_id, sample_exceptions)
            
            # Update status
            result = update_exception_status(
                conn, 'exc-001', 
                status='in_progress', 
                notes='Under investigation',
                assigned_to='Engineer A'
            )
            
            # Verify
            exceptions = get_session_exceptions(conn, session_id, filters={'current_status': 'in_progress'})
        
        assert result is True
        assert len(exceptions) == 1
        assert exceptions[0]['notes'] == 'Under investigation'


# =============================================================================
# TEST: SUB-MODULE 1 - EXCEPTION RECORDS
# =============================================================================

@pytest.mark.skip(reason="Sub-module 1 is deprecated")
class TestSubModule1ExceptionRecords:
    """Tests for Sub-module 1: Exception Records (Single Run)."""
    
    def test_save_exception_records_batch(self, db_manager, sample_exceptions):
        """Test batch saving exception records."""
        # Flatten exceptions
        flat_exceptions = []
        for exc_list in sample_exceptions.values():
            flat_exceptions.extend(exc_list)
        
        with db_manager.get_connection() as conn:
            count = save_exception_records_batch(
                conn,
                line='EAL',
                track='UP',
                section='Mainline',
                date_str='20260130',
                exceptions=flat_exceptions,
                task_no='TASK-001'
            )
        
        assert count == 3
    
    def test_query_exception_records_with_filters(self, db_manager, sample_exceptions):
        """Test querying with various filters."""
        flat_exceptions = []
        for exc_list in sample_exceptions.values():
            flat_exceptions.extend(exc_list)
        
        with db_manager.get_connection() as conn:
            save_exception_records_batch(
                conn, line='EAL', track='UP', section='Mainline',
                date_str='20260130', exceptions=flat_exceptions
            )
            
            # Query with different filters
            all_records = query_exception_records(conn)
            l1_records = query_exception_records(conn, filters={'level': 'L1'})
            low_height_records = query_exception_records(conn, filters={'exception_type': 'Low Height'})
            location_records = query_exception_records(conn, filters={
                'from_m_min': 100600,
                'from_m_max': 101100
            })
        
        assert len(all_records) == 3
        assert len(l1_records) == 2
        assert len(low_height_records) == 2
        assert len(location_records) == 2  # exc-002 and exc-003
    
    def test_delete_exception_record(self, db_manager, sample_exceptions):
        """Test deleting a single record."""
        flat_exceptions = []
        for exc_list in sample_exceptions.values():
            flat_exceptions.extend(exc_list)
        
        with db_manager.get_connection() as conn:
            save_exception_records_batch(
                conn, line='EAL', track='UP', section='Mainline',
                date_str='20260130', exceptions=flat_exceptions
            )
            
            # Delete one record
            result = delete_exception_record(conn, 'exc-001')
            remaining = query_exception_records(conn)
        
        assert result is True
        assert len(remaining) == 2
    
    def test_export_exception_records_to_df(self, db_manager, sample_exceptions):
        """Test exporting to DataFrame."""
        flat_exceptions = []
        for exc_list in sample_exceptions.values():
            flat_exceptions.extend(exc_list)
        
        with db_manager.get_connection() as conn:
            save_exception_records_batch(
                conn, line='EAL', track='UP', section='Mainline',
                date_str='20260130', exceptions=flat_exceptions
            )
            
            df = export_exception_records_to_df(conn)
        
        assert len(df) == 3
        assert 'exception_type' in df.columns
        assert 'level' in df.columns
    
    def test_unique_constraint_prevents_duplicates(self, db_manager, sample_exceptions):
        """Test that UNIQUE constraint prevents duplicate saves."""
        flat_exceptions = []
        for exc_list in sample_exceptions.values():
            flat_exceptions.extend(exc_list)
        
        with db_manager.get_connection() as conn:
            # Save twice with same data
            count1 = save_exception_records_batch(
                conn, line='EAL', track='UP', section='Mainline',
                date_str='20260130', exceptions=flat_exceptions
            )
            count2 = save_exception_records_batch(
                conn, line='EAL', track='UP', section='Mainline',
                date_str='20260130', exceptions=flat_exceptions
            )
            
            total = query_exception_records(conn)
        
        assert count1 == 3
        assert count2 == 3  # Replaced existing
        assert len(total) == 3  # No duplicates


# =============================================================================
# TEST: SUB-MODULE 2 - REPEATED EXCEPTIONS
# =============================================================================

class TestSubModule2RepeatedExceptions:
    """Tests for Sub-module 2: Repeated Exceptions & Follow-up Action."""
    
    def test_save_repeated_records_filters_mock_data(self, db_manager, sample_repeated_exceptions):
        """Test that MOCK_DATA is automatically filtered."""
        with db_manager.get_connection() as conn:
            result = save_repeated_records_batch(
                conn,
                line='EAL',
                track='UP',
                date_str='20260130',
                repeated_exceptions=sample_repeated_exceptions
            )
        
        assert result['saved_count'] == 2  # Only real data
        assert result['filtered_mock_count'] == 2  # mock-001 and mock-another-test
    
    def test_query_repeated_records_with_action_filter(self, db_manager, sample_repeated_exceptions):
        """Test querying with action filter."""
        with db_manager.get_connection() as conn:
            save_repeated_records_batch(
                conn, line='EAL', track='UP', date_str='20260130',
                repeated_exceptions=sample_repeated_exceptions
            )
            
            all_records = query_repeated_records(conn)
            pending_records = query_repeated_records(conn, filters={'action': 'Pending'})
            monitoring_records = query_repeated_records(conn, filters={'action': 'Keep monitoring'})
        
        assert len(all_records) == 2
        assert len(pending_records) == 1
        assert len(monitoring_records) == 1
    
    def test_update_repeated_record_workflow(self, db_manager, sample_repeated_exceptions):
        """Test updating workflow fields."""
        with db_manager.get_connection() as conn:
            save_repeated_records_batch(
                conn, line='EAL', track='UP', date_str='20260130',
                repeated_exceptions=sample_repeated_exceptions
            )
            
            records = query_repeated_records(conn)
            record_id = records[0]['record_id']
            
            # Update workflow fields
            result = update_repeated_record_workflow(conn, record_id, {
                'action': 'Verify on site',
                'check_date': '2026-02-15',
                'checked_by': 'Engineer B',
                'check_result': 'Pass',
                'remarks': 'Verified OK'
            })
            
            updated = query_repeated_records(conn)
            updated_record = [r for r in updated if r['record_id'] == record_id][0]
        
        assert result is True
        assert updated_record['action'] == 'Verify on site'
        assert updated_record['checked_by'] == 'Engineer B'
        assert updated_record['check_result'] == 'Pass'
    
    def test_delete_repeated_record(self, db_manager, sample_repeated_exceptions):
        """Test deleting a repeated record."""
        with db_manager.get_connection() as conn:
            save_repeated_records_batch(
                conn, line='EAL', track='UP', date_str='20260130',
                repeated_exceptions=sample_repeated_exceptions
            )
            
            records = query_repeated_records(conn)
            record_id = records[0]['record_id']
            
            result = delete_repeated_record(conn, record_id)
            remaining = query_repeated_records(conn)
        
        assert result is True
        assert len(remaining) == 1
    
    def test_export_repeated_records_to_df(self, db_manager, sample_repeated_exceptions):
        """Test exporting repeated records to DataFrame."""
        with db_manager.get_connection() as conn:
            save_repeated_records_batch(
                conn, line='EAL', track='UP', date_str='20260130',
                repeated_exceptions=sample_repeated_exceptions
            )
            
            df = export_repeated_records_to_df(conn)
        
        assert len(df) == 2
        # Phase 10.10-F: Columns are now renamed to display headers
        assert 'ACTION' in df.columns
        assert 'CHECK DATE' in df.columns
        assert 'CHECK RESULT' in df.columns
        # Verify column order starts with Task Run Data
        assert list(df.columns[:3]) == ['Run Date', 'Line', 'Track']


class TestRepeatedRecordQueryAggregates:
    """List, total, and section counts must share one filter scope."""

    @staticmethod
    def _seed_records(conn):
        records = [
            {
                'id': 'scope-mainline', 'exception type': 'Low Height', 'level': 'L1',
                'FromM': 100.0, 'ToM': 120.0, 'Class': 'A', 'Overlap': 'No',
                'action': 'Keep monitoring', 'Section': 'Mainline',
                'line': 'EAL', 'track': 'UP', 'date': '20260110', 'task_no': 'TASK-A',
            },
            {
                'id': 'scope-rac', 'exception type': 'Stagger Left', 'level': 'L2',
                'FromM': 200.0, 'ToM': 220.0, 'Class': 'B', 'Overlap': 'Yes',
                'action': 'Calculation', 'Section': 'RAC',
                'line': 'EAL', 'track': 'DN', 'date': '20260210', 'task_no': 'TASK-B',
            },
            {
                'id': 'scope-low', 'exception type': 'Wire Wear', 'level': 'L3',
                'FromM': 300.0, 'ToM': 330.0, 'Class': 'C', 'Overlap': 'No',
                'action': 'Pending', 'Section': 'LOW',
                'line': 'EAL', 'track': 'UP', 'date': '20260310', 'task_no': 'TASK-C',
            },
            {
                'id': 'scope-low-s1', 'exception type': 'Low Height', 'level': 'L1',
                'FromM': 400.0, 'ToM': 430.0, 'Class': 'A', 'Overlap': 'No',
                'action': 'Keep monitoring', 'Section': 'LOW S1',
                'line': 'EAL', 'track': 'UP', 'date': '20260410', 'task_no': 'TASK-D',
            },
            {
                'id': 'scope-lmc', 'exception type': 'High Height', 'level': 'L2',
                'FromM': 500.0, 'ToM': 520.0, 'Class': 'B', 'Overlap': 'Yes',
                'action': 'Calculation', 'Section': 'LMC',
                'line': 'EAL', 'track': 'UP', 'date': '20260510', 'task_no': 'TASK-E',
            },
            {
                'id': 'scope-null', 'exception type': 'Low Height', 'level': 'L1',
                'FromM': 600.0, 'ToM': 620.0, 'Class': 'A', 'Overlap': 'No',
                'action': 'Pending', 'Section': None,
                'line': 'EAL', 'track': 'UP', 'date': '20260610', 'task_no': 'TASK-F',
            },
            {
                'id': 'scope-unknown', 'exception type': 'Low Height', 'level': 'L1',
                'FromM': 700.0, 'ToM': 720.0, 'Class': 'A', 'Overlap': 'No',
                'action': 'Pending', 'Section': 'Depot',
                'line': 'EAL', 'track': 'UP', 'date': '20260710', 'task_no': 'TASK-G',
            },
            {
                'id': 'scope-tml', 'exception type': 'Low Height', 'level': 'L1',
                'FromM': 800.0, 'ToM': 820.0, 'Class': 'A', 'Overlap': 'No',
                'action': 'Keep monitoring', 'Section': 'Mainline',
                'line': 'TML', 'track': 'UP', 'date': '20260810', 'task_no': 'TASK-H',
            },
        ]

        for record in records:
            save_repeated_records_batch(
                conn,
                line=record.pop('line'),
                track=record.pop('track'),
                date_str=record['date'],
                task_run_date=record.pop('date'),
                task_no=record.pop('task_no'),
                repeated_exceptions=[record],
            )

        conn.execute(
            "UPDATE saved_repeated_exceptions SET saved_at = '2026-01-15' "
            "WHERE exception_id = 'scope-mainline'"
        )
        conn.execute(
            "UPDATE saved_repeated_exceptions SET saved_at = '2026-07-15' "
            "WHERE exception_id != 'scope-mainline'"
        )

    def test_count_is_not_limited_or_offset(self, db_manager):
        with db_manager.get_connection() as conn:
            self._seed_records(conn)

            first_page = query_repeated_records(conn, limit=2)
            second_page = query_repeated_records(conn, limit=2, offset=2)
            total = count_repeated_records(conn)

        assert len(first_page) == 2
        assert len(second_page) == 2
        assert total == 8

    @pytest.mark.parametrize(
        ('filters', 'expected_ids'),
        [
            ({'line': 'TML'}, {'scope-tml'}),
            ({'track': 'DN'}, {'scope-rac'}),
            ({'level': 'L3'}, {'scope-low'}),
            ({'action': 'Calculation'}, {'scope-rac', 'scope-lmc'}),
            ({'exception_type': 'Wire Wear'}, {'scope-low'}),
            ({'class': 'C'}, {'scope-low'}),
            ({'overlap': 'Yes'}, {'scope-rac', 'scope-lmc'}),
            ({'task_number': 'TASK-E'}, {'scope-lmc'}),
            (
                {'date_type': 'task_run_date', 'date_from': '2026-04-01', 'date_to': '2026-04-30'},
                {'scope-low-s1'},
            ),
            ({'chainage_from': 315.0, 'chainage_to': 410.0}, {'scope-low', 'scope-low-s1'}),
            ({'from_m_min': 700.0}, {'scope-unknown', 'scope-tml'}),
            ({'to_m_max': 120.0}, {'scope-mainline'}),
            ({'task_run_date_from': '20260801'}, {'scope-tml'}),
            ({'saved_at_date': '2026-01-15'}, {'scope-mainline'}),
            ({'section': 'LOW S1'}, {'scope-low', 'scope-low-s1'}),
            ({'section': 'Unknown'}, {'scope-null', 'scope-unknown'}),
        ],
    )
    def test_list_and_count_share_every_predicate(self, db_manager, filters, expected_ids):
        with db_manager.get_connection() as conn:
            self._seed_records(conn)

            records = query_repeated_records(conn, filters=filters, limit=100)
            total = count_repeated_records(conn, filters=filters)

        assert {record['exception_id'] for record in records} == expected_ids
        assert total == len(expected_ids)

    def test_section_counts_exclude_only_the_active_section(self, db_manager):
        from app.core.database import get_repeated_record_section_counts

        filters = {'line': 'EAL', 'track': 'UP', 'section': 'LMC'}
        with db_manager.get_connection() as conn:
            self._seed_records(conn)

            records = query_repeated_records(conn, filters=filters, limit=100)
            total = count_repeated_records(conn, filters=filters)
            section_counts = get_repeated_record_section_counts(conn, filters=filters)

        assert [record['exception_id'] for record in records] == ['scope-lmc']
        assert total == 1
        assert section_counts == {
            'all': 6,
            'mainline': 1,
            'rac': 0,
            'low_s1': 2,
            'lmc': 1,
            'unknown': 2,
        }
        assert section_counts['all'] == sum(
            count for key, count in section_counts.items() if key != 'all'
        )

    def test_empty_scope_returns_zero_counts(self, db_manager):
        from app.core.database import get_repeated_record_section_counts

        filters = {'line': 'NONEXISTENT'}
        with db_manager.get_connection() as conn:
            self._seed_records(conn)

            assert query_repeated_records(conn, filters=filters, limit=2) == []
            assert count_repeated_records(conn, filters=filters) == 0
            assert get_repeated_record_section_counts(conn, filters=filters) == {
                'all': 0,
                'mainline': 0,
                'rac': 0,
                'low_s1': 0,
                'lmc': 0,
                'unknown': 0,
            }


# =============================================================================
# TEST: TRIGGERS
# =============================================================================

class TestTriggers:
    """Tests for database triggers."""
    
    def test_status_change_creates_history(self, db_manager, sample_session_data, sample_exceptions):
        """Test that status changes are recorded in exception_history."""
        with db_manager.get_connection() as conn:
            session_id = save_analysis_session(conn, sample_session_data)
            save_exceptions_from_analysis(conn, session_id, sample_exceptions)
            
            # Change status
            update_exception_status(conn, 'exc-001', 'in_progress')
            update_exception_status(conn, 'exc-001', 'resolved')
            
            # Check history
            cursor = conn.execute(
                "SELECT * FROM exception_history WHERE exception_id = ? ORDER BY changed_at",
                ('exc-001',)
            )
            history = cursor.fetchall()
        
        assert len(history) == 2
        assert history[0]['old_status'] == 'pending'
        assert history[0]['new_status'] == 'in_progress'
        assert history[1]['old_status'] == 'in_progress'
        assert history[1]['new_status'] == 'resolved'
    
    def test_session_stats_updated_on_exception_insert(self, db_manager, sample_session_data, sample_exceptions):
        """Test that session statistics are updated when exceptions are inserted."""
        with db_manager.get_connection() as conn:
            session_id = save_analysis_session(conn, sample_session_data)
            save_exceptions_from_analysis(conn, session_id, sample_exceptions)
            
            session = get_session_by_id(conn, session_id)
        
        assert session['total_exceptions'] == 3
        assert session['l1_count'] == 2
        assert session['l2_count'] == 1
        assert session['l3_count'] == 0
    
    def test_db_version_increments(self, db_manager, sample_session_data):
        """Test that db_version increments on data changes."""
        with db_manager.get_connection() as conn:
            initial_version = get_db_version(conn)
            
            # Insert session (should trigger version increment)
            save_analysis_session(conn, sample_session_data)
            
            new_version = get_db_version(conn)
        
        assert new_version > initial_version


# =============================================================================
# TEST: THREAD SAFETY
# =============================================================================

@pytest.mark.skip(reason="Sub-module 1 is deprecated")
class TestThreadSafety:
    """Tests for concurrent database operations."""
    
    def test_concurrent_writes(self, db_manager, sample_exceptions):
        """Test that concurrent writes don't cause issues."""
        flat_exceptions = []
        for exc_list in sample_exceptions.values():
            flat_exceptions.extend(exc_list)
        
        errors = []
        success_count = [0]
        lock = threading.Lock()
        
        def write_records(thread_id):
            try:
                with db_manager.get_connection() as conn:
                    # Modify IDs to make them unique per thread
                    thread_exceptions = []
                    for exc in flat_exceptions:
                        new_exc = exc.copy()
                        new_exc['id'] = f"{exc['id']}-thread{thread_id}"
                        thread_exceptions.append(new_exc)
                    
                    count = save_exception_records_batch(
                        conn,
                        line='EAL',
                        track='UP',
                        section='Mainline',
                        date_str=f'2026013{thread_id}',
                        exceptions=thread_exceptions
                    )
                    
                    with lock:
                        success_count[0] += count
            except Exception as e:
                errors.append((thread_id, e))
        
        # Run concurrent writes
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(write_records, i) for i in range(5)]
            for future in as_completed(futures):
                future.result()
        
        assert len(errors) == 0, f"Errors: {errors}"
        assert success_count[0] == 15  # 3 exceptions * 5 threads
    
    def test_concurrent_reads(self, db_manager, sample_exceptions):
        """Test that concurrent reads work correctly."""
        flat_exceptions = []
        for exc_list in sample_exceptions.values():
            flat_exceptions.extend(exc_list)
        
        # Insert initial data
        with db_manager.get_connection() as conn:
            save_exception_records_batch(
                conn, line='EAL', track='UP', section='Mainline',
                date_str='20260130', exceptions=flat_exceptions
            )
        
        results = []
        errors = []
        
        def read_records():
            try:
                with db_manager.get_connection() as conn:
                    records = query_exception_records(conn)
                    results.append(len(records))
            except Exception as e:
                errors.append(e)
        
        # Run concurrent reads
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(read_records) for _ in range(10)]
            for future in as_completed(futures):
                future.result()
        
        assert len(errors) == 0
        assert all(r == 3 for r in results)


# =============================================================================
# TEST: ERROR HANDLING
# =============================================================================

class TestErrorHandling:
    """Tests for error handling and constraints."""
    
    def test_foreign_key_constraint(self, db_manager):
        """Test that foreign key constraints are enforced."""
        with db_manager.get_connection() as conn:
            # Try to insert exception with non-existent session_id
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute("""
                    INSERT INTO exceptions (id, session_id, exception_type, level, from_m, to_m)
                    VALUES ('test-exc', 'non-existent-session', 'Low Height', 'L1', 100, 200)
                """)
    
    def test_level_check_constraint(self, db_manager, sample_session_data):
        """Test that level CHECK constraint is enforced."""
        with db_manager.get_connection() as conn:
            session_id = save_analysis_session(conn, sample_session_data)
            
            # Try to insert exception with invalid level
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute("""
                    INSERT INTO exceptions (id, session_id, exception_type, level, from_m, to_m)
                    VALUES ('test-exc', ?, 'Low Height', 'L4', 100, 200)
                """, (session_id,))
    
    def test_cascade_delete(self, db_manager, sample_session_data, sample_exceptions):
        """Test that deleting session cascades to exceptions."""
        with db_manager.get_connection() as conn:
            session_id = save_analysis_session(conn, sample_session_data)
            save_exceptions_from_analysis(conn, session_id, sample_exceptions)
            
            # Verify exceptions exist
            exceptions_before = get_session_exceptions(conn, session_id)
            assert len(exceptions_before) == 3
            
            # Delete session
            conn.execute("DELETE FROM analysis_sessions WHERE id = ?", (session_id,))
            
            # Verify exceptions are deleted
            cursor = conn.execute(
                "SELECT COUNT(*) FROM exceptions WHERE session_id = ?",
                (session_id,)
            )
            count = cursor.fetchone()[0]
        
        assert count == 0


# =============================================================================
# TEST: UTILITY FUNCTIONS
# =============================================================================

@pytest.mark.skip(reason="Sub-module 1 is deprecated")
class TestUtilityFunctions:
    """Tests for utility functions."""
    
    def test_count_exception_records(self, db_manager, sample_exceptions):
        """Test counting exception records."""
        flat_exceptions = []
        for exc_list in sample_exceptions.values():
            flat_exceptions.extend(exc_list)
        
        with db_manager.get_connection() as conn:
            save_exception_records_batch(
                conn, line='EAL', track='UP', section='Mainline',
                date_str='20260130', exceptions=flat_exceptions
            )
            
            total = count_exception_records(conn)
            l1_count = count_exception_records(conn, filters={'level': 'L1'})
        
        assert total == 3
        assert l1_count == 2
    
    def test_get_pending_critical_exceptions(self, db_manager, sample_session_data, sample_exceptions):
        """Test getting pending L1 exceptions."""
        with db_manager.get_connection() as conn:
            session_id = save_analysis_session(conn, sample_session_data)
            save_exceptions_from_analysis(conn, session_id, sample_exceptions)
            
            pending = get_pending_critical_exceptions(conn)
        
        assert len(pending) == 2  # 2 L1 exceptions
        assert all(p['level'] == 'L1' for p in pending)
    
    def test_get_exception_summary_by_date(self, db_manager, sample_exceptions):
        """Test getting summary by date."""
        flat_exceptions = []
        for exc_list in sample_exceptions.values():
            flat_exceptions.extend(exc_list)
        
        with db_manager.get_connection() as conn:
            save_exception_records_batch(
                conn, line='EAL', track='UP', section='Mainline',
                date_str='20260130', exceptions=flat_exceptions
            )
            
            summary = get_exception_summary_by_date(conn)
        
        assert len(summary) == 1
        assert summary[0]['total_count'] == 3
        assert summary[0]['l1_count'] == 2


# =============================================================================
# TEST: PERFORMANCE
# =============================================================================

@pytest.mark.skip(reason="Sub-module 1 is deprecated")
class TestPerformance:
    """Basic performance tests."""
    
    def test_query_performance_1000_records(self, db_manager):
        """Test that querying 1000 records completes in reasonable time."""
        # Generate 1000 test records
        exceptions = []
        for i in range(1000):
            exceptions.append({
                'id': f'perf-exc-{i:04d}',
                'exception type': 'Low Height',
                'level': ['L1', 'L2', 'L3'][i % 3],
                'FromM': 100000 + i * 10,
                'ToM': 100000 + i * 10 + 5,
                'length': 5,
                'maxValue': 4500 + i,
                'maxLocation': 100000 + i * 10 + 2,
                'Track Type': 'Tangent',
                'Class': 'Mainline',
                'Section': 'Mainline',
            })
        
        with db_manager.get_connection() as conn:
            save_exception_records_batch(
                conn, line='EAL', track='UP', section='Mainline',
                date_str='20260130', exceptions=exceptions
            )
            
            # Time the query
            start = time.time()
            records = query_exception_records(conn, limit=1000)
            elapsed = time.time() - start
        
        assert len(records) == 1000
        assert elapsed < 0.3, f"Query took {elapsed:.3f}s, expected < 0.3s"
    
    def test_batch_insert_performance(self, db_manager):
        """Test that batch inserting 100 records is fast."""
        exceptions = []
        for i in range(100):
            exceptions.append({
                'id': f'batch-exc-{i:03d}',
                'exception type': 'Stagger Left',
                'level': 'L2',
                'FromM': 100000 + i * 100,
                'ToM': 100000 + i * 100 + 50,
                'length': 50,
                'maxValue': 200,
                'maxLocation': 100000 + i * 100 + 25,
                'Track Type': 'Curve',
                'Class': 'Mainline',
                'Section': 'Mainline',
            })
        
        with db_manager.get_connection() as conn:
            start = time.time()
            count = save_exception_records_batch(
                conn, line='EAL', track='UP', section='Mainline',
                date_str='20260130', exceptions=exceptions
            )
            elapsed = time.time() - start
        
        assert count == 100
        assert elapsed < 1.0, f"Batch insert took {elapsed:.3f}s, expected < 1.0s"


# =============================================================================
# PORTABLE MODE TESTS
# =============================================================================

class TestPortableMode:
    """Tests for portable mode detection and path resolution."""
    
    def test_is_portable_mode_returns_false_in_dev(self):
        """Test that is_portable_mode returns False in development environment."""
        from app.core.database import is_portable_mode
        # In development (not frozen), should always return False
        assert is_portable_mode() is False
    
    def test_get_portable_data_dir_returns_none_in_dev(self):
        """Test that get_portable_data_dir returns None in development."""
        from app.core.database import get_portable_data_dir
        # In development (not frozen), should return None
        assert get_portable_data_dir() is None
    
    def test_get_default_db_path_uses_appdata_in_dev(self):
        """Test that get_default_db_path uses AppData in development."""
        from app.core.database import get_default_db_path
        
        db_path = get_default_db_path()
        
        # Should contain AppData path structure
        path_str = str(db_path)
        assert 'TOV1050_Analyzer' in path_str
        assert 'data' in path_str
        assert path_str.endswith('analysis.db')
    
    def test_get_default_db_path_structure(self):
        """Test the structure of the default database path."""
        from app.core.database import get_default_db_path
        
        db_path = get_default_db_path()
        
        # Verify it's a Path object
        assert isinstance(db_path, Path)
        
        # Verify the filename
        assert db_path.name == 'analysis.db'
        
        # Verify parent directory name
        assert db_path.parent.name == 'data'
    
    def test_portable_mode_mock_frozen(self, tmp_path):
        """Test portable mode detection with mocked frozen state."""
        import sys
        from unittest.mock import patch
        from app.core.database import is_portable_mode, get_portable_data_dir, get_default_db_path
        
        # Create a mock portable.txt file
        mock_exe_dir = tmp_path
        portable_marker = mock_exe_dir / 'portable.txt'
        portable_marker.write_text('Portable Mode')
        
        mock_exe = mock_exe_dir / 'app.exe'
        
        # Mock sys.frozen and sys.executable using patch
        # Note: We test the logic directly without reload to avoid test isolation issues
        with patch.object(sys, 'frozen', True, create=True):
            with patch.object(sys, 'executable', str(mock_exe)):
                # Test is_portable_mode
                assert is_portable_mode() is True
                
                # Test get_portable_data_dir
                portable_dir = get_portable_data_dir()
                assert portable_dir is not None
                assert portable_dir == mock_exe_dir / 'data'
                
                # Test get_default_db_path
                default_path = get_default_db_path()
                assert default_path == mock_exe_dir / 'data' / 'analysis.db'
    
    def test_portable_mode_without_marker_file(self, tmp_path):
        """Test that portable mode is False when marker file doesn't exist."""
        import sys
        from unittest.mock import patch
        from app.core.database import is_portable_mode
        
        # No portable.txt file created
        mock_exe_dir = tmp_path
        mock_exe = mock_exe_dir / 'app.exe'
        
        # Mock sys.frozen and sys.executable
        with patch.object(sys, 'frozen', True, create=True):
            with patch.object(sys, 'executable', str(mock_exe)):
                # Should be False because no portable.txt
                assert is_portable_mode() is False


# =============================================================================
# Phase 10.10 - Bug 1.3: get_distinct_values (TDD)
# =============================================================================

class TestGetDistinctValues:
    """Test get_distinct_values function for dynamic dropdown filters."""

    def test_get_distinct_task_no_values(self, db_manager):
        """Should return unique task_no values from saved_repeated_exceptions."""
        with db_manager.get_connection() as conn:
            # Insert test data with different task_no values
            save_repeated_records_batch(
                conn, 'EAL', 'UP', '20260201',
                [
                    {'id': 'exc-1', 'exception type': 'Low Height', 'level': 'L1',
                     'FromM': 100000, 'ToM': 100100, 'length': 100,
                     'maxValue': 4500, 'maxLocation': 100050},
                    {'id': 'exc-2', 'exception type': 'Low Height', 'level': 'L2',
                     'FromM': 100200, 'ToM': 100300, 'length': 100,
                     'maxValue': 4550, 'maxLocation': 100250},
                ],
                task_no='U1', station_start='HUH', station_end='RAC'
            )
            save_repeated_records_batch(
                conn, 'EAL', 'UP', '20260202',
                [
                    {'id': 'exc-3', 'exception type': 'Low Height', 'level': 'L1',
                     'FromM': 100400, 'ToM': 100500, 'length': 100,
                     'maxValue': 4480, 'maxLocation': 100450},
                ],
                task_no='U2', station_start='RAC', station_end='LOW'
            )

            # Call get_distinct_values
            values = get_distinct_values(conn, 'task_no')

            assert isinstance(values, list)
            assert 'U1' in values
            assert 'U2' in values
            assert len(values) == 2

    def test_get_distinct_values_with_line_filter(self, db_manager):
        """Should filter distinct values by line."""
        with db_manager.get_connection() as conn:
            save_repeated_records_batch(
                conn, 'EAL', 'UP', '20260201',
                [{'id': 'exc-1', 'exception type': 'Low Height', 'level': 'L1',
                  'FromM': 100000, 'ToM': 100100, 'length': 100,
                  'maxValue': 4500, 'maxLocation': 100050}],
                task_no='U1'
            )
            save_repeated_records_batch(
                conn, 'TML', 'DN', '20260201',
                [{'id': 'exc-2', 'exception type': 'Low Height', 'level': 'L1',
                  'FromM': 200000, 'ToM': 200100, 'length': 100,
                  'maxValue': 4500, 'maxLocation': 200050}],
                task_no='D1'
            )

            # Filter by EAL only
            values = get_distinct_values(conn, 'task_no', line='EAL')

            assert 'U1' in values
            assert 'D1' not in values

    def test_get_distinct_values_excludes_null(self, db_manager):
        """Should not include None/NULL values in results."""
        with db_manager.get_connection() as conn:
            save_repeated_records_batch(
                conn, 'EAL', 'UP', '20260201',
                [{'id': 'exc-1', 'exception type': 'Low Height', 'level': 'L1',
                  'FromM': 100000, 'ToM': 100100, 'length': 100,
                  'maxValue': 4500, 'maxLocation': 100050}],
                task_no=None  # No task number
            )

            values = get_distinct_values(conn, 'task_no')

            assert None not in values
            assert '' not in values

    def test_get_distinct_values_invalid_field(self, db_manager):
        """Should return empty list for invalid field names (SQL injection protection)."""
        with db_manager.get_connection() as conn:
            values = get_distinct_values(conn, 'nonexistent_column')

            assert values == []

    def test_get_distinct_values_sorted(self, db_manager):
        """Should return values in sorted order."""
        with db_manager.get_connection() as conn:
            save_repeated_records_batch(
                conn, 'EAL', 'UP', '20260201',
                [{'id': 'exc-1', 'exception type': 'Low Height', 'level': 'L1',
                  'FromM': 100000, 'ToM': 100100, 'length': 100,
                  'maxValue': 4500, 'maxLocation': 100050}],
                task_no='U3'
            )
            save_repeated_records_batch(
                conn, 'EAL', 'UP', '20260202',
                [{'id': 'exc-2', 'exception type': 'Low Height', 'level': 'L1',
                  'FromM': 100200, 'ToM': 100300, 'length': 100,
                  'maxValue': 4480, 'maxLocation': 100250}],
                task_no='U1'
            )

            values = get_distinct_values(conn, 'task_no')

            assert values == ['U1', 'U3']


# =============================================================================
# Phase 10.10 - Bug 1.5: Date Filter Format Handling (TDD)
# =============================================================================

class TestDateFilterFormat:
    """Test that date filters work with both YYYY-MM-DD and YYYYMMDD formats."""

    def test_query_with_hyphenated_date_from(self, db_manager):
        """query_repeated_records should handle YYYY-MM-DD date_from."""
        with db_manager.get_connection() as conn:
            save_repeated_records_batch(
                conn, 'EAL', 'UP', '20260201',
                [{'id': 'exc-1', 'exception type': 'Low Height', 'level': 'L1',
                  'FromM': 100000, 'ToM': 100100, 'length': 100,
                  'maxValue': 4500, 'maxLocation': 100050}],
                task_no='U1', task_run_date='20260201'
            )
            save_repeated_records_batch(
                conn, 'EAL', 'UP', '20260115',
                [{'id': 'exc-2', 'exception type': 'Low Height', 'level': 'L1',
                  'FromM': 100200, 'ToM': 100300, 'length': 100,
                  'maxValue': 4480, 'maxLocation': 100250}],
                task_no='U2', task_run_date='20260115'
            )

            # Filter by task_run_date >= 2026-02-01 (YYYY-MM-DD from HTML input)
            results = query_repeated_records(
                conn,
                filters={
                    'date_from': '2026-02-01',
                    'date_type': 'task_run_date',
                },
                limit=100
            )

            # Should only return the 20260201 record, not the 20260115 one
            assert len(results) == 1
            assert results[0]['exception_id'] == 'exc-1'

    def test_query_with_compact_date_from(self, db_manager):
        """query_repeated_records should still handle YYYYMMDD date_from."""
        with db_manager.get_connection() as conn:
            save_repeated_records_batch(
                conn, 'EAL', 'UP', '20260201',
                [{'id': 'exc-1', 'exception type': 'Low Height', 'level': 'L1',
                  'FromM': 100000, 'ToM': 100100, 'length': 100,
                  'maxValue': 4500, 'maxLocation': 100050}],
                task_run_date='20260201'
            )

            results = query_repeated_records(
                conn,
                filters={
                    'date_from': '20260201',
                    'date_type': 'task_run_date',
                },
                limit=100
            )

            assert len(results) == 1

    def test_query_with_date_range(self, db_manager):
        """query_repeated_records should handle date range with YYYY-MM-DD."""
        with db_manager.get_connection() as conn:
            for day in ['20260110', '20260201', '20260215', '20260301']:
                save_repeated_records_batch(
                    conn, 'EAL', 'UP', day,
                    [{'id': f'exc-{day}', 'exception type': 'Low Height', 'level': 'L1',
                      'FromM': 100000, 'ToM': 100100, 'length': 100,
                      'maxValue': 4500, 'maxLocation': 100050}],
                    task_run_date=day
                )

            results = query_repeated_records(
                conn,
                filters={
                    'date_from': '2026-02-01',
                    'date_to': '2026-02-28',
                    'date_type': 'task_run_date',
                },
                limit=100
            )

            # Should only return Feb records (20260201, 20260215)
            assert len(results) == 2
            exc_ids = {r['exception_id'] for r in results}
            assert 'exc-20260201' in exc_ids
            assert 'exc-20260215' in exc_ids


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
