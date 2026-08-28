"""
Phase 12 Section 9 — Bug 1: Check 1 Year E2E Data Flow Tests
=============================================================
Tests using UAT real data format to verify check_1_year_records
correctly matches exceptions against database records.

Root cause: Frontend was not passing task_run_date, section, and action
in the correct format to check_1_year_records.

These tests simulate the exact data format from the UAT example tables.
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
    return str(tmp_path / "test_check_1_year_e2e.db")


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
def uat_db_records(db_connection):
    """Insert UAT database records matching Section 9 example data."""
    db_records = [
        {'id': '20251110_EAL_UP_LH37', 'exception type': 'Low Height',
         'FromM': 100817.25, 'ToM': 100958.75, 'maxLocation': 100817.25,
         'section': 'Mainline', 'level': 'L1'},
        {'id': '20251110_EAL_UP_SL1', 'exception type': 'Stagger Left',
         'FromM': 100372.5, 'ToM': 100376.25, 'maxLocation': 100374,
         'section': 'Mainline', 'level': 'L1'},
        {'id': '20251110_EAL_UP_SL5', 'exception type': 'Stagger Left',
         'FromM': 100678.25, 'ToM': 100682.75, 'maxLocation': 100681,
         'section': 'Mainline', 'level': 'L1'},
        {'id': '20251110_EAL_UP_SR1', 'exception type': 'Stagger Right',
         'FromM': 100884, 'ToM': 100902, 'maxLocation': 100886,
         'section': 'Mainline', 'level': 'L1'},
        {'id': '20251110_EAL_UP_W51', 'exception type': 'Wire Wear',
         'FromM': 103279.5, 'ToM': 103279.5, 'maxLocation': 103279.5,
         'section': 'Mainline', 'level': 'L1'},
    ]
    save_repeated_records_batch(
        db_connection, line='EAL', track='UP',
        date_str='20251110',
        repeated_exceptions=db_records,
    )
    return db_records


# =============================================================================
# TEST: UAT Real Data Format — task_run_date missing (current bug)
# =============================================================================

class TestCheck1YearUATDataFlow:
    """Tests using UAT real data format to verify matching logic."""

    def test_matches_with_task_run_date_provided(self, db_connection, uat_db_records):
        """Should match when task_run_date is provided in exception data.
        
        UAT Example: 20251201_EAL_UP_LH71 (maxLocation=100829.25) should match
        DB record 20251110_EAL_UP_LH37 (FromM=100817.25, ToM=100958.75).
        """
        exceptions = [{
            'id': '20251201_EAL_UP_LH71',
            'exception type': 'Low Height',
            'level': 'L1',
            'maxLocation': 100829.25,
            'FromM': 100817.25,
            'ToM': 100957.5,
            'section': 'Mainline',
            'task_run_date': '20251201',
            'action': 'Pending',
        }]

        result = check_1_year_records(db_connection, exceptions, 'EAL', 'UP')
        assert result[0]['action'] == 'No action required (Verified within 1 year)'
        assert result[0]['reoccurrence_id'] == '20251110_EAL_UP_LH37'

    def test_no_match_without_task_run_date(self, db_connection, uat_db_records):
        """Should NOT match when task_run_date is missing (current bug).
        
        This test documents the current broken behavior — exceptions without
        task_run_date are skipped because the date comparison cannot be performed.
        """
        exceptions = [{
            'id': '20251201_EAL_UP_LH71',
            'exception type': 'Low Height',
            'level': 'L1',
            'maxLocation': 100829.25,
            'FromM': 100817.25,
            'ToM': 100957.5,
            'section': 'Mainline',
            # task_run_date is MISSING — this is the bug
            'action': 'Pending',
        }]

        result = check_1_year_records(db_connection, exceptions, 'EAL', 'UP')
        # Without task_run_date, the function skips this exception
        assert result[0]['action'] == 'Pending'

    def test_matches_with_current_date_fallback(self, db_connection, uat_db_records):
        """Should match when current_date is provided as fallback for missing task_run_date.
        
        This is the FIX: check_1_year_records should accept an optional current_date
        parameter and use it as fallback when exception has no task_run_date.
        """
        exceptions = [{
            'id': '20251201_EAL_UP_LH71',
            'exception type': 'Low Height',
            'level': 'L1',
            'maxLocation': 100829.25,
            'FromM': 100817.25,
            'ToM': 100957.5,
            'section': 'Mainline',
            # task_run_date is MISSING
            'action': 'Pending',
        }]

        # FIX: Pass current_date as fallback
        result = check_1_year_records(
            db_connection, exceptions, 'EAL', 'UP',
            current_date='20251201'
        )
        assert result[0]['action'] == 'No action required (Verified within 1 year)'
        assert result[0]['reoccurrence_id'] == '20251110_EAL_UP_LH37'

    def test_multiple_uat_records_match(self, db_connection, uat_db_records):
        """Should match multiple exceptions from UAT data against DB records."""
        exceptions = [
            {
                'id': '20251201_EAL_UP_LH71',
                'exception type': 'Low Height',
                'level': 'L1',
                'maxLocation': 100829.25,
                'section': 'Mainline',
                'task_run_date': '20251201',
                'action': 'Pending',
            },
            {
                'id': '20251201_EAL_UP_SL2',
                'exception type': 'Stagger Left',
                'level': 'L1',
                'maxLocation': 100373.25,
                'section': 'Mainline',
                'task_run_date': '20251201',
                'action': 'Pending',
            },
            {
                'id': '20251201_EAL_UP_SR0',
                'exception type': 'Stagger Right',
                'level': 'L1',
                'maxLocation': 100894.5,
                'section': 'Mainline',
                'task_run_date': '20251201',
                'action': 'Pending',
            },
        ]

        result = check_1_year_records(db_connection, exceptions, 'EAL', 'UP')
        
        matched_count = sum(
            1 for exc in result
            if exc.get('action') == 'No action required (Verified within 1 year)'
        )
        assert matched_count == 3, f"Expected 3 matches, got {matched_count}"

    def test_section_from_each_row_not_global_filter(self, db_connection, uat_db_records):
        """Should use section from each exception row, not a global filter.
        
        Bug: Frontend was passing filterSection (from dialog) instead of
        each row's own section value.
        """
        exceptions = [
            {
                'id': '20251201_EAL_UP_LH71',
                'exception type': 'Low Height',
                'level': 'L1',
                'maxLocation': 100829.25,
                'section': 'Mainline',  # Row-level section
                'task_run_date': '20251201',
                'action': 'Pending',
            },
            {
                'id': '20251201_EAL_UP_LH_RAC',
                'exception type': 'Low Height',
                'level': 'L1',
                'maxLocation': 100829.25,
                'section': 'RAC',  # Different section — should NOT match Mainline DB records
                'task_run_date': '20251201',
                'action': 'Pending',
            },
        ]

        result = check_1_year_records(db_connection, exceptions, 'EAL', 'UP')
        
        # First exception (Mainline) should match
        assert result[0]['action'] == 'No action required (Verified within 1 year)'
        # Second exception (RAC) should NOT match (no RAC records in DB)
        assert result[1]['action'] == 'Pending'

    def test_action_field_name_compatibility(self, db_connection, uat_db_records):
        """Should handle both 'action' and 'current_action' field names.
        
        Bug: Frontend was sending 'current_action' but backend reads 'action'.
        """
        exceptions = [{
            'id': '20251201_EAL_UP_LH71',
            'exception type': 'Low Height',
            'level': 'L1',
            'maxLocation': 100829.25,
            'section': 'Mainline',
            'task_run_date': '20251201',
            'current_action': 'Pending',  # Frontend format
            # 'action' is NOT present
        }]

        result = check_1_year_records(db_connection, exceptions, 'EAL', 'UP')
        assert result[0]['action'] == 'No action required (Verified within 1 year)'


# =============================================================================
# TEST: Import last_updated timezone comparison
# =============================================================================

class TestImportLastUpdatedTimezone:
    """Bug 2: Import should correctly compare last_updated across timezones.
    
    Excel exports last_updated in UTC+8 format (2026/02/10 01:23:59).
    DB stores last_updated in UTC format (2026-02-09 17:23:59).
    These represent the SAME moment — import should recognize this and skip.
    """

    def _insert_record_with_last_updated(self, conn, exc_id, last_updated_utc, action='Keep monitoring'):
        """Helper: Insert a record and set last_updated bypassing trigger.
        
        Uses DROP/CREATE trigger trick to set exact last_updated value.
        """
        save_repeated_records_batch(
            conn, line='EAL', track='UP',
            date_str='20251110',
            repeated_exceptions=[{
                'id': exc_id,
                'exception type': 'Low Height',
                'level': 'L1',
                'FromM': 100000, 'ToM': 110000,
                'maxLocation': 105000,
                'section': 'Mainline',
                'action': action,
            }],
        )
        # Temporarily drop trigger, update, then recreate
        conn.execute("DROP TRIGGER IF EXISTS trg_repeated_update_timestamp")
        conn.execute(
            "UPDATE saved_repeated_exceptions SET last_updated = ? WHERE exception_id = ?",
            (last_updated_utc, exc_id)
        )
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS trg_repeated_update_timestamp
            AFTER UPDATE ON saved_repeated_exceptions
            FOR EACH ROW
            BEGIN
                UPDATE saved_repeated_exceptions 
                SET last_updated = CURRENT_TIMESTAMP 
                WHERE record_id = NEW.record_id;
            END
        """)
        conn.commit()

    def test_skip_when_excel_and_db_same_moment_different_tz(self, db_connection):
        """Should skip update when Excel UTC+8 and DB UTC represent same moment."""
        from app.core.database import import_repeated_records_from_data

        # DB stores UTC time: 2026-02-09 17:23:59
        self._insert_record_with_last_updated(
            db_connection, 'tz-test-001', '2026-02-09 17:23:59'
        )

        # Import with Excel UTC+8 time (same moment as DB UTC)
        records = [{
            'ID': 'tz-test-001',
            'Exception Type': 'Low Height',
            'Level': 'L1',
            'FromM': 100000, 'ToM': 110000,
            'ACTION': 'Calculation',
            'Last Updated': '2026/02/10 01:23:59',  # UTC+8 = same moment as DB UTC
        }]

        result = import_repeated_records_from_data(
            db_connection, records, 'EAL', 'UP', '20251110'
        )

        # Should skip because Excel and DB represent the same moment
        assert result['skipped_count'] == 1
        assert result['updated_count'] == 0

    def test_update_when_excel_genuinely_newer(self, db_connection):
        """Should update when Excel last_updated is genuinely newer than DB."""
        from app.core.database import import_repeated_records_from_data

        # DB stores UTC time: 2026-02-08 10:00:00
        self._insert_record_with_last_updated(
            db_connection, 'tz-test-002', '2026-02-08 10:00:00'
        )

        # Import with genuinely newer Excel time (UTC+8)
        # 2026/02/10 01:23:59 UTC+8 = 2026-02-09 17:23:59 UTC > 2026-02-08 10:00:00 UTC
        records = [{
            'ID': 'tz-test-002',
            'Exception Type': 'Low Height',
            'Level': 'L1',
            'FromM': 100000, 'ToM': 110000,
            'ACTION': 'Calculation',
            'Last Updated': '2026/02/10 01:23:59',  # Genuinely newer
        }]

        result = import_repeated_records_from_data(
            db_connection, records, 'EAL', 'UP', '20251110'
        )

        assert result['updated_count'] == 1
        assert result['skipped_count'] == 0

    def test_skip_when_excel_older_than_db(self, db_connection):
        """Should skip when Excel last_updated is older than DB."""
        from app.core.database import import_repeated_records_from_data

        # DB stores UTC time: 2026-02-11 10:00:00
        self._insert_record_with_last_updated(
            db_connection, 'tz-test-003', '2026-02-11 10:00:00'
        )

        # Import with older Excel time
        # 2026/02/10 01:23:59 UTC+8 = 2026-02-09 17:23:59 UTC < 2026-02-11 10:00:00 UTC
        records = [{
            'ID': 'tz-test-003',
            'Exception Type': 'Low Height',
            'Level': 'L1',
            'FromM': 100000, 'ToM': 110000,
            'ACTION': 'Keep monitoring',
            'Last Updated': '2026/02/10 01:23:59',  # Older than DB
        }]

        result = import_repeated_records_from_data(
            db_connection, records, 'EAL', 'UP', '20251110'
        )

        assert result['skipped_count'] == 1
        assert result['updated_count'] == 0
