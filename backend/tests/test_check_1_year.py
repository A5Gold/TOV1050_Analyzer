"""
Phase 12 - Bug 2.2: Check 1 Year Record Algorithm Fix Tests
=============================================================
Tests for check_1_year_records with 5 bug fixes:
1. Missing section comparison
2. Missing exception_type comparison
3. Wrong date field (date_str vs task_run_date)
4. Not writing back to DB (reoccurrence_id)
5. Overwriting reoccurrence_id instead of appending

Legacy reference: docs/archive/functions.py find_repeated (L888-1080) + db_update (L1149-1340)
"""

import pytest
import sqlite3
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.database import (
    DatabaseManager,
    save_repeated_records_batch,
    check_1_year_records,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def temp_db_path(tmp_path):
    return str(tmp_path / "test_check_1_year.db")


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
# FIX #1 + #2: Section and Exception Type comparison
# =============================================================================

class TestCheck1YearSectionAndTypeMatch:
    """Bug fix: check_1_year should match on section + exception_type."""

    def test_matches_with_same_section_and_type(self, db_connection):
        """Should match when line/track/section/exception_type all match."""
        save_repeated_records_batch(
            db_connection, line='EAL', track='UP',
            date_str='20250301',
            repeated_exceptions=[{
                'id': 'db-001',
                'exception type': 'Low Height',
                'level': 'L1',
                'FromM': 100000, 'ToM': 110000,
                'maxLocation': 105000,
                'section': 'Mainline',
                'action': 'Keep monitoring',
            }],
        )

        exceptions = [{
            'id': 'exc-001',
            'exception type': 'Low Height',
            'level': 'L1',
            'FromM': 102000, 'ToM': 108000,
            'maxLocation': 105500,
            'section': 'Mainline',
            'task_run_date': '20260210',
            'action': 'Pending',
        }]

        result = check_1_year_records(db_connection, exceptions, 'EAL', 'UP')
        assert result[0]['action'] == 'No action required (Verified within 1 year)'
        assert 'db-001' in result[0].get('reoccurrence_id', '')

    def test_no_match_different_exception_type(self, db_connection):
        """Should NOT match when exception_type differs."""
        save_repeated_records_batch(
            db_connection, line='EAL', track='UP',
            date_str='20250301',
            repeated_exceptions=[{
                'id': 'db-002',
                'exception type': 'Low Height',
                'level': 'L1',
                'FromM': 100000, 'ToM': 110000,
                'maxLocation': 105000,
                'section': 'Mainline',
            }],
        )

        exceptions = [{
            'id': 'exc-002',
            'exception type': 'Stagger Left',
            'level': 'L1',
            'FromM': 102000, 'ToM': 108000,
            'maxLocation': 105000,
            'section': 'Mainline',
            'task_run_date': '20260210',
            'action': 'Pending',
        }]

        result = check_1_year_records(db_connection, exceptions, 'EAL', 'UP')
        assert result[0]['action'] == 'Pending'

    def test_no_match_different_section(self, db_connection):
        """Should NOT match when section differs."""
        save_repeated_records_batch(
            db_connection, line='EAL', track='UP',
            date_str='20250301',
            repeated_exceptions=[{
                'id': 'db-003',
                'exception type': 'Low Height',
                'level': 'L1',
                'FromM': 100000, 'ToM': 110000,
                'maxLocation': 105000,
                'section': 'Mainline',
            }],
        )

        exceptions = [{
            'id': 'exc-003',
            'exception type': 'Low Height',
            'level': 'L1',
            'FromM': 102000, 'ToM': 108000,
            'maxLocation': 105000,
            'section': 'RAC',
            'task_run_date': '20260210',
            'action': 'Pending',
        }]

        result = check_1_year_records(db_connection, exceptions, 'EAL', 'UP')
        assert result[0]['action'] == 'Pending'


# =============================================================================
# FIX #3: Date field — use task_run_date instead of date_str
# =============================================================================

class TestCheck1YearDateField:
    """Bug fix: should use task_run_date for date comparison."""

    def test_uses_task_run_date_for_matching(self, db_connection):
        """Should use task_run_date from exception, not date_str."""
        save_repeated_records_batch(
            db_connection, line='EAL', track='UP',
            date_str='20250601',
            task_run_date='2025/06/01',
            repeated_exceptions=[{
                'id': 'db-date-001',
                'exception type': 'Low Height',
                'level': 'L1',
                'FromM': 100000, 'ToM': 110000,
                'maxLocation': 105000,
                'section': 'Mainline',
            }],
        )

        exceptions = [{
            'id': 'exc-date-001',
            'exception type': 'Low Height',
            'level': 'L1',
            'FromM': 102000, 'ToM': 108000,
            'maxLocation': 105000,
            'section': 'Mainline',
            'task_run_date': '20260210',
            'action': 'Pending',
        }]

        result = check_1_year_records(db_connection, exceptions, 'EAL', 'UP')
        assert result[0]['action'] == 'No action required (Verified within 1 year)'

    def test_no_match_when_db_record_older_than_1_year(self, db_connection):
        """Should NOT match when DB record is older than 1 year."""
        save_repeated_records_batch(
            db_connection, line='EAL', track='UP',
            date_str='20240101',
            repeated_exceptions=[{
                'id': 'db-date-002',
                'exception type': 'Low Height',
                'level': 'L1',
                'FromM': 100000, 'ToM': 110000,
                'maxLocation': 105000,
                'section': 'Mainline',
            }],
        )

        exceptions = [{
            'id': 'exc-date-002',
            'exception type': 'Low Height',
            'level': 'L1',
            'FromM': 102000, 'ToM': 108000,
            'maxLocation': 105000,
            'section': 'Mainline',
            'task_run_date': '20260210',
            'action': 'Pending',
        }]

        result = check_1_year_records(db_connection, exceptions, 'EAL', 'UP')
        assert result[0]['action'] == 'Pending'


# =============================================================================
# FIX #4: Write back to database
# =============================================================================

class TestCheck1YearDatabaseWriteback:
    """Bug fix: should write reoccurrence_id back to DB."""

    def test_updates_database_reoccurrence_id(self, db_connection):
        """Should write reoccurrence_id to the matched DB record."""
        save_repeated_records_batch(
            db_connection, line='EAL', track='UP',
            date_str='20250301',
            repeated_exceptions=[{
                'id': 'db-wb-001',
                'exception type': 'Low Height',
                'level': 'L1',
                'FromM': 100000, 'ToM': 110000,
                'maxLocation': 105000,
                'section': 'Mainline',
            }],
        )

        exceptions = [{
            'id': 'exc-wb-001',
            'exception type': 'Low Height',
            'level': 'L1',
            'FromM': 102000, 'ToM': 108000,
            'maxLocation': 105000,
            'section': 'Mainline',
            'task_run_date': '20260210',
            'action': 'Pending',
        }]

        check_1_year_records(db_connection, exceptions, 'EAL', 'UP')

        cursor = db_connection.execute(
            "SELECT reoccurrence_id FROM saved_repeated_exceptions "
            "WHERE exception_id = 'db-wb-001'"
        )
        row = cursor.fetchone()
        assert row is not None
        assert row['reoccurrence_id'] is not None
        assert row['reoccurrence_id'] != ''
        assert 'exc-wb-001' in row['reoccurrence_id']


# =============================================================================
# FIX #5: Append reoccurrence_id instead of overwrite
# =============================================================================

class TestCheck1YearAppendReoccurrence:
    """Bug fix: should append to existing reoccurrence_id, not overwrite."""

    def test_appends_to_existing_reoccurrence_id(self, db_connection):
        """Should append new ID to existing reoccurrence_id (comma-separated)."""
        save_repeated_records_batch(
            db_connection, line='EAL', track='UP',
            date_str='20250301',
            repeated_exceptions=[{
                'id': 'db-app-001',
                'exception type': 'Low Height',
                'level': 'L1',
                'FromM': 100000, 'ToM': 110000,
                'maxLocation': 105000,
                'section': 'Mainline',
                'reoccurrence_id': 'old-id-1, old-id-2',
            }],
        )

        exceptions = [{
            'id': 'exc-app-001',
            'exception type': 'Low Height',
            'level': 'L1',
            'FromM': 102000, 'ToM': 108000,
            'maxLocation': 105000,
            'section': 'Mainline',
            'task_run_date': '20260210',
            'action': 'Pending',
        }]

        check_1_year_records(db_connection, exceptions, 'EAL', 'UP')

        cursor = db_connection.execute(
            "SELECT reoccurrence_id FROM saved_repeated_exceptions "
            "WHERE exception_id = 'db-app-001'"
        )
        row = cursor.fetchone()
        reoccurrence = row['reoccurrence_id']
        assert 'old-id-1' in reoccurrence
        assert 'old-id-2' in reoccurrence
        assert 'exc-app-001' in reoccurrence

    def test_sets_reoccurrence_id_when_empty(self, db_connection):
        """Should set reoccurrence_id when DB record has no existing value."""
        save_repeated_records_batch(
            db_connection, line='EAL', track='UP',
            date_str='20250301',
            repeated_exceptions=[{
                'id': 'db-app-002',
                'exception type': 'Low Height',
                'level': 'L1',
                'FromM': 100000, 'ToM': 110000,
                'maxLocation': 105000,
                'section': 'Mainline',
            }],
        )

        exceptions = [{
            'id': 'exc-app-002',
            'exception type': 'Low Height',
            'level': 'L1',
            'FromM': 102000, 'ToM': 108000,
            'maxLocation': 105000,
            'section': 'Mainline',
            'task_run_date': '20260210',
            'action': 'Pending',
        }]

        check_1_year_records(db_connection, exceptions, 'EAL', 'UP')

        cursor = db_connection.execute(
            "SELECT reoccurrence_id FROM saved_repeated_exceptions "
            "WHERE exception_id = 'db-app-002'"
        )
        row = cursor.fetchone()
        assert row['reoccurrence_id'] == 'exc-app-002'


# =============================================================================
# Edge cases
# =============================================================================

class TestCheck1YearEdgeCases:
    """Edge case tests for check_1_year_records."""

    def test_skips_non_pending_actions(self, db_connection):
        """Should skip exceptions with non-Pending action."""
        save_repeated_records_batch(
            db_connection, line='EAL', track='UP',
            date_str='20250301',
            repeated_exceptions=[{
                'id': 'db-edge-001',
                'exception type': 'Low Height',
                'level': 'L1',
                'FromM': 100000, 'ToM': 110000,
                'maxLocation': 105000,
                'section': 'Mainline',
            }],
        )

        exceptions = [{
            'id': 'exc-edge-001',
            'exception type': 'Low Height',
            'level': 'L1',
            'FromM': 102000, 'ToM': 108000,
            'maxLocation': 105000,
            'section': 'Mainline',
            'task_run_date': '20260210',
            'action': 'Keep monitoring',
        }]

        result = check_1_year_records(db_connection, exceptions, 'EAL', 'UP')
        assert result[0]['action'] == 'Keep monitoring'

    def test_excludes_self_match(self, db_connection):
        """Should not match exception against itself in DB."""
        save_repeated_records_batch(
            db_connection, line='EAL', track='UP',
            date_str='20260210',
            repeated_exceptions=[{
                'id': 'exc-self-001',
                'exception type': 'Low Height',
                'level': 'L1',
                'FromM': 100000, 'ToM': 110000,
                'maxLocation': 105000,
                'section': 'Mainline',
            }],
        )

        exceptions = [{
            'id': 'exc-self-001',
            'exception type': 'Low Height',
            'level': 'L1',
            'FromM': 102000, 'ToM': 108000,
            'maxLocation': 105000,
            'section': 'Mainline',
            'task_run_date': '20260210',
            'action': 'Pending',
        }]

        result = check_1_year_records(db_connection, exceptions, 'EAL', 'UP')
        assert result[0]['action'] == 'Pending'

    def test_empty_exceptions_list(self, db_connection):
        """Should return empty list for empty input."""
        result = check_1_year_records(db_connection, [], 'EAL', 'UP')
        assert result == []

    def test_no_db_records_returns_unchanged(self, db_connection):
        """Should return exceptions unchanged when no DB records exist."""
        exceptions = [{
            'id': 'exc-nodb-001',
            'exception type': 'Low Height',
            'level': 'L1',
            'FromM': 102000, 'ToM': 108000,
            'maxLocation': 105000,
            'section': 'Mainline',
            'task_run_date': '20260210',
            'action': 'Pending',
        }]

        result = check_1_year_records(db_connection, exceptions, 'EAL', 'UP')
        assert result[0]['action'] == 'Pending'

    def test_location_outside_range_no_match(self, db_connection):
        """Should NOT match when maxLocation is outside DB record range."""
        save_repeated_records_batch(
            db_connection, line='EAL', track='UP',
            date_str='20250301',
            repeated_exceptions=[{
                'id': 'db-loc-001',
                'exception type': 'Low Height',
                'level': 'L1',
                'FromM': 100000, 'ToM': 110000,
                'maxLocation': 105000,
                'section': 'Mainline',
            }],
        )

        exceptions = [{
            'id': 'exc-loc-001',
            'exception type': 'Low Height',
            'level': 'L1',
            'FromM': 200000, 'ToM': 210000,
            'maxLocation': 205000,
            'section': 'Mainline',
            'task_run_date': '20260210',
            'action': 'Pending',
        }]

        result = check_1_year_records(db_connection, exceptions, 'EAL', 'UP')
        assert result[0]['action'] == 'Pending'

    def test_returns_exception_id_not_record_id(self, db_connection):
        """Reoccurrence_id on the exception should be the DB exception_id, not record_id."""
        save_repeated_records_batch(
            db_connection, line='EAL', track='UP',
            date_str='20250301',
            repeated_exceptions=[{
                'id': 'db-rid-001',
                'exception type': 'Low Height',
                'level': 'L1',
                'FromM': 100000, 'ToM': 110000,
                'maxLocation': 105000,
                'section': 'Mainline',
            }],
        )

        exceptions = [{
            'id': 'exc-rid-001',
            'exception type': 'Low Height',
            'level': 'L1',
            'FromM': 102000, 'ToM': 108000,
            'maxLocation': 105000,
            'section': 'Mainline',
            'task_run_date': '20260210',
            'action': 'Pending',
        }]

        result = check_1_year_records(db_connection, exceptions, 'EAL', 'UP')
        assert result[0]['reoccurrence_id'] == 'db-rid-001'
