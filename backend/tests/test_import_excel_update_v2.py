"""
Phase 12 - Issue 9: Excel Import Row-Level last_updated Comparison Tests
=========================================================================
Tests for import_repeated_records_from_data with row-level last_updated comparison.

Bug: User modifies Master List Excel and imports, but fields are always overwritten
regardless of whether the Excel data is newer or older than DB data.

Fix: Add row-level last_updated comparison (方案 B):
- If Excel last_updated > DB last_updated → update (Excel is newer)
- If Excel last_updated <= DB last_updated → skip (DB is newer)
- If no last_updated in Excel → always update (backward compatible)
"""

import pytest
import sqlite3
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.database import (
    DatabaseManager,
    save_repeated_records_batch,
    import_repeated_records_from_data,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def temp_db_path(tmp_path):
    return str(tmp_path / "test_import_v2.db")


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


# =============================================================================
# Test: Display header mapping works correctly
# =============================================================================

class TestImportDisplayHeaders:
    """Import with Excel display headers should correctly map to DB fields."""

    def test_updates_workflow_fields_with_display_headers(self, db_connection):
        """Import with Excel display headers should update workflow fields."""
        save_repeated_records_batch(
            db_connection, line='EAL', track='UP',
            date_str='20260210',
            repeated_exceptions=[{
                'id': 'exc-001',
                'exception type': 'Low Height',
                'level': 'L1',
                'FromM': 100000, 'ToM': 100100,
                'action': 'Pending',
            }],
        )

        import_records = [{
            'ID': 'exc-001',
            'ACTION': 'Keep monitoring',
            'CHECK DATE': '2026/02/10',
            'CHECKED BY': 'Engineer A',
            'CHECK RESULT': 'Pass',
            'Line': 'EAL', 'Track': 'UP',
            'Run Date': '2026/02/10',
        }]
        result = import_repeated_records_from_data(
            db_connection, import_records, 'EAL', 'UP', '20260210')

        assert result['updated_count'] >= 1

        cursor = db_connection.execute(
            "SELECT action, checked_by FROM saved_repeated_exceptions "
            "WHERE exception_id = 'exc-001'"
        )
        row = cursor.fetchone()
        assert row['action'] == 'Keep monitoring'
        assert row['checked_by'] == 'Engineer A'


# =============================================================================
# Test: Row-level last_updated comparison
# =============================================================================

class TestImportRowLevelLastUpdated:
    """Import should compare last_updated per row to decide update vs skip."""

    def test_older_excel_does_not_overwrite_db(self, db_connection):
        """Import with OLDER last_updated should NOT overwrite DB values."""
        save_repeated_records_batch(
            db_connection, line='EAL', track='UP',
            date_str='20260210',
            repeated_exceptions=[{
                'id': 'exc-010',
                'exception type': 'Low Height',
                'level': 'L1',
                'FromM': 100000, 'ToM': 100100,
                'action': 'Keep monitoring',
                'checked_by': 'DB User',
            }],
        )

        import_records_old = [{
            'ID': 'exc-010',
            'ACTION': 'Pending',
            'CHECKED BY': 'Excel User Old',
            'Line': 'EAL', 'Track': 'UP',
            'Last Updated': '2026/02/09 10:00:00',
        }]
        result = import_repeated_records_from_data(
            db_connection, import_records_old, 'EAL', 'UP', '20260210')

        assert result.get('skipped_count', 0) >= 1

        cursor = db_connection.execute(
            "SELECT action, checked_by FROM saved_repeated_exceptions "
            "WHERE exception_id = 'exc-010'"
        )
        row = cursor.fetchone()
        assert row['action'] == 'Keep monitoring'
        assert row['checked_by'] == 'DB User'

    def test_newer_excel_overwrites_db(self, db_connection):
        """Import with NEWER last_updated should overwrite DB values."""
        save_repeated_records_batch(
            db_connection, line='EAL', track='UP',
            date_str='20260210',
            repeated_exceptions=[{
                'id': 'exc-011',
                'exception type': 'Low Height',
                'level': 'L1',
                'FromM': 100000, 'ToM': 100100,
                'action': 'Pending',
            }],
        )

        # Set DB last_updated to an old time
        db_connection.execute("""
            UPDATE saved_repeated_exceptions
            SET last_updated = '2026-02-08 10:00:00'
            WHERE exception_id = 'exc-011'
        """)
        db_connection.commit()

        import_records_new = [{
            'ID': 'exc-011',
            'ACTION': 'Calculation',
            'CHECKED BY': 'Excel User New',
            'Line': 'EAL', 'Track': 'UP',
            'Last Updated': '2099/12/31 23:59:59',
        }]
        result = import_repeated_records_from_data(
            db_connection, import_records_new, 'EAL', 'UP', '20260210')

        assert result['updated_count'] >= 1

        cursor = db_connection.execute(
            "SELECT action, checked_by FROM saved_repeated_exceptions "
            "WHERE exception_id = 'exc-011'"
        )
        row = cursor.fetchone()
        assert row['action'] == 'Calculation'
        assert row['checked_by'] == 'Excel User New'

    def test_no_last_updated_always_updates(self, db_connection):
        """Import without Last Updated column should always update (backward compatible)."""
        save_repeated_records_batch(
            db_connection, line='EAL', track='UP',
            date_str='20260210',
            repeated_exceptions=[{
                'id': 'exc-012',
                'exception type': 'Low Height',
                'level': 'L1',
                'FromM': 100000, 'ToM': 100100,
                'action': 'Pending',
            }],
        )

        import_records = [{
            'ID': 'exc-012',
            'ACTION': 'Verify on site',
            'Line': 'EAL', 'Track': 'UP',
        }]
        result = import_repeated_records_from_data(
            db_connection, import_records, 'EAL', 'UP', '20260210')

        assert result['updated_count'] >= 1

        cursor = db_connection.execute(
            "SELECT action FROM saved_repeated_exceptions "
            "WHERE exception_id = 'exc-012'"
        )
        row = cursor.fetchone()
        assert row['action'] == 'Verify on site'

    def test_skipped_count_in_result(self, db_connection):
        """Result should include skipped_count for rows skipped due to older Excel."""
        save_repeated_records_batch(
            db_connection, line='EAL', track='UP',
            date_str='20260210',
            repeated_exceptions=[{
                'id': 'exc-013',
                'exception type': 'Low Height',
                'level': 'L1',
                'FromM': 100000, 'ToM': 100100,
                'action': 'Keep monitoring',
            }],
        )

        import_records = [{
            'ID': 'exc-013',
            'ACTION': 'Pending',
            'Line': 'EAL', 'Track': 'UP',
            'Last Updated': '2026/02/09 10:00:00',
        }]
        result = import_repeated_records_from_data(
            db_connection, import_records, 'EAL', 'UP', '20260210')

        assert 'skipped_count' in result
        assert result['skipped_count'] >= 1
