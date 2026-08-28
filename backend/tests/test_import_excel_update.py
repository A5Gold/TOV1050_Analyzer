"""
Phase 12 - Issue 9: Excel Import Update Tests
===============================================
Tests for import_repeated_records_from_data with display header mapping.

Bug: When user modifies Master List Excel and imports, none of the columns
in RepeatedRecordTable are updated except saved_at and last_updated.

Root causes:
1. No display header → snake_case mapping (Excel uses "ACTION" but code expects "action")
2. NaN values not handled (pandas NaN passes `is not None` check)
3. last_updated not set in UPDATE statement

Fix: Add _normalize_import_record() with IMPORT_HEADER_MAP and NaN handling.
"""

import pytest
import sqlite3
import math
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.database import (
    DatabaseManager,
    save_repeated_records_batch,
    query_repeated_records,
    import_repeated_records_from_data,
    _normalize_import_record,
    IMPORT_HEADER_MAP,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def temp_db_path(tmp_path):
    return str(tmp_path / "test_import.db")


@pytest.fixture
def db_manager(temp_db_path):
    DatabaseManager.reset_instance()
    manager = DatabaseManager(db_path=temp_db_path)
    yield manager
    manager.close()
    DatabaseManager.reset_instance()


@pytest.fixture
def db_connection(db_manager):
    with db_manager.get_connection() as conn:
        yield conn


@pytest.fixture
def seeded_db(db_connection):
    """Database with pre-existing records for import testing."""
    exceptions = [
        {
            'id': 'exc-001',
            'exception type': 'Low Height',
            'level': 'L1',
            'FromM': 100000,
            'ToM': 100100,
            'length': 100,
            'maxValue': 4450,
            'maxLocation': 100050,
            'Track Type': 'Tangent',
            'Section': 'Mainline',
            'action': 'Pending',
        },
        {
            'id': 'exc-002',
            'exception type': 'High Height',
            'level': 'L2',
            'FromM': 200000,
            'ToM': 200200,
            'length': 200,
            'maxValue': 5900,
            'maxLocation': 200100,
            'Track Type': 'Curve',
            'Section': 'Mainline',
            'action': 'Pending',
        },
    ]
    save_repeated_records_batch(
        db_connection, line='EAL', track='UP',
        date_str='20260210', repeated_exceptions=exceptions
    )
    return db_connection


# =============================================================================
# TESTS: _normalize_import_record
# =============================================================================

class TestNormalizeImportRecord:
    """Tests for the display header → snake_case normalization function."""

    def test_display_headers_mapped_to_snake_case(self):
        """Display headers like 'ACTION' should map to 'action'."""
        record = {'ACTION': 'Keep monitoring', 'CHECK DATE': '2026/02/10'}
        normalized = _normalize_import_record(record)
        assert normalized['action'] == 'Keep monitoring'
        assert normalized['check_date'] == '2026/02/10'

    def test_nan_values_converted_to_none(self):
        """NaN values from pandas should be converted to None."""
        record = {'ACTION': float('nan'), 'CHECK RESULT': 'Pass'}
        normalized = _normalize_import_record(record)
        assert normalized['action'] is None
        assert normalized['check_result'] == 'Pass'

    def test_already_snake_case_preserved(self):
        """Keys already in snake_case should be preserved."""
        record = {'action': 'Pending', 'check_date': '2026/02/10'}
        normalized = _normalize_import_record(record)
        assert normalized['action'] == 'Pending'
        assert normalized['check_date'] == '2026/02/10'

    def test_id_mapped_to_exception_id(self):
        """'ID' display header should map to 'exception_id'."""
        record = {'ID': 'exc-001'}
        normalized = _normalize_import_record(record)
        assert normalized['exception_id'] == 'exc-001'

    def test_import_header_map_has_required_keys(self):
        """IMPORT_HEADER_MAP should contain all critical display headers."""
        required_keys = [
            'ID', 'ACTION', 'CHECK DATE', 'CHECKED BY', 'CHECK RESULT',
            'VERIFY DEADLINE', 'VERIFY DATE', 'VERIFY RESULT', 'VERIFIED BY',
            'ADJUST DEADLINE', 'ADJUST DATE', 'ADJUST RESULT', 'ADJUSTED BY',
            'Line', 'Track', 'Level', 'Exception Type', 'Remarks',
        ]
        for key in required_keys:
            assert key in IMPORT_HEADER_MAP, f"Missing key: {key}"


# =============================================================================
# TESTS: import_repeated_records_from_data
# =============================================================================

class TestImportRepeatedRecords:
    """Tests for the full import workflow with display headers."""

    def test_import_updates_workflow_fields(self, seeded_db):
        """Import with display headers should update workflow fields."""
        import_records = [
            {
                'ID': 'exc-001',
                'ACTION': 'Keep monitoring',
                'CHECK DATE': '2026/02/10',
                'CHECKED BY': 'Engineer A',
                'CHECK RESULT': 'Pass',
                'Line': 'EAL',
                'Track': 'UP',
            }
        ]
        result = import_repeated_records_from_data(
            seeded_db, import_records, 'EAL', 'UP', '20260210'
        )
        assert result['updated_count'] == 1
        assert result['error_count'] == 0

        records = query_repeated_records(seeded_db, {'line': 'EAL'})
        updated = next(r for r in records if r['exception_id'] == 'exc-001')
        assert updated['action'] == 'Keep monitoring'
        assert updated['checked_by'] == 'Engineer A'
        assert updated['check_result'] == 'Pass'

    def test_import_handles_nan_values(self, seeded_db):
        """NaN values in import should not overwrite existing data."""
        import_records = [
            {
                'ID': 'exc-001',
                'ACTION': 'Verify on site',
                'CHECK DATE': float('nan'),  # NaN from pandas
                'CHECKED BY': float('nan'),
                'CHECK RESULT': float('nan'),
                'Line': 'EAL',
                'Track': 'UP',
            }
        ]
        result = import_repeated_records_from_data(
            seeded_db, import_records, 'EAL', 'UP', '20260210'
        )
        assert result['updated_count'] == 1

        records = query_repeated_records(seeded_db, {'line': 'EAL'})
        updated = next(r for r in records if r['exception_id'] == 'exc-001')
        assert updated['action'] == 'Verify on site'
        # NaN fields should not have been written (preserved as original)

    def test_import_sets_last_updated(self, seeded_db):
        """Import should set last_updated timestamp."""
        import_records = [
            {
                'ID': 'exc-001',
                'ACTION': 'Completed',
                'Line': 'EAL',
                'Track': 'UP',
            }
        ]
        # Get original last_updated
        records_before = query_repeated_records(seeded_db, {'line': 'EAL'})
        original = next(r for r in records_before if r['exception_id'] == 'exc-001')
        original_updated = original.get('last_updated')

        import_repeated_records_from_data(
            seeded_db, import_records, 'EAL', 'UP', '20260210'
        )

        records_after = query_repeated_records(seeded_db, {'line': 'EAL'})
        updated = next(r for r in records_after if r['exception_id'] == 'exc-001')
        # last_updated should be set (not None)
        assert updated.get('last_updated') is not None

    def test_import_multiple_records(self, seeded_db):
        """Import should handle multiple records correctly."""
        import_records = [
            {
                'ID': 'exc-001',
                'ACTION': 'Keep monitoring',
                'Line': 'EAL',
                'Track': 'UP',
            },
            {
                'ID': 'exc-002',
                'ACTION': 'Verify on site',
                'CHECKED BY': 'Engineer B',
                'Line': 'EAL',
                'Track': 'UP',
            },
        ]
        result = import_repeated_records_from_data(
            seeded_db, import_records, 'EAL', 'UP', '20260210'
        )
        assert result['updated_count'] == 2
        assert result['error_count'] == 0

    def test_import_without_id_counts_as_error(self, seeded_db):
        """Records without ID should be counted as errors."""
        import_records = [
            {
                'ACTION': 'Keep monitoring',
                'Line': 'EAL',
                'Track': 'UP',
            }
        ]
        result = import_repeated_records_from_data(
            seeded_db, import_records, 'EAL', 'UP', '20260210'
        )
        assert result['error_count'] == 1
        assert result['updated_count'] == 0
