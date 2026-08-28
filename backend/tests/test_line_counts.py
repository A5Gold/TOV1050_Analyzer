"""
Phase 12 - Bug 4: Line Counts API Tests
========================================
Tests for get_line_counts() function and /api/database/repeated-records/counts endpoint.

Bug: Inactive tab count always shows 0 because lineCounts is computed from
store's repeatedRecords which only contains current line's data.
Fix: New counts API endpoint that returns counts grouped by line.
"""

import pytest
import sqlite3
import tempfile
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.database import (
    DatabaseManager,
    save_repeated_records_batch,
    get_line_counts,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def temp_db_path(tmp_path):
    return str(tmp_path / "test_line_counts.db")


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
def sample_eal_exceptions():
    """Sample EAL repeated exceptions."""
    return [
        {
            'id': f'eal-exc-{i:03d}',
            'exception type': 'Low Height',
            'level': 'L1',
            'FromM': 100000 + i * 100,
            'ToM': 100100 + i * 100,
            'length': 100,
            'maxValue': 4450,
            'maxLocation': 100050 + i * 100,
            'Track Type': 'Tangent',
            'Section': 'Mainline',
            'action': 'Pending',
        }
        for i in range(5)
    ]


@pytest.fixture
def sample_tml_exceptions():
    """Sample TML repeated exceptions."""
    return [
        {
            'id': f'tml-exc-{i:03d}',
            'exception type': 'High Height',
            'level': 'L2',
            'FromM': 200000 + i * 100,
            'ToM': 200100 + i * 100,
            'length': 100,
            'maxValue': 5900,
            'maxLocation': 200050 + i * 100,
            'Track Type': 'Curve',
            'Section': 'Mainline',
            'action': 'Keep monitoring',
        }
        for i in range(3)
    ]


# =============================================================================
# TESTS
# =============================================================================

class TestGetLineCounts:
    """Tests for get_line_counts function."""

    def test_empty_database_returns_zero_counts(self, db_connection):
        """Empty database should return {EAL: 0, TML: 0}."""
        counts = get_line_counts(db_connection)
        assert counts['EAL'] == 0
        assert counts['TML'] == 0

    def test_eal_only_data(self, db_connection, sample_eal_exceptions):
        """With only EAL data, EAL count > 0 and TML count = 0."""
        save_repeated_records_batch(
            db_connection, line='EAL', track='UP',
            date_str='20260210', repeated_exceptions=sample_eal_exceptions
        )
        counts = get_line_counts(db_connection)
        assert counts['EAL'] == 5
        assert counts['TML'] == 0

    def test_both_lines_have_correct_counts(self, db_connection, sample_eal_exceptions, sample_tml_exceptions):
        """Both EAL and TML should have correct counts."""
        save_repeated_records_batch(
            db_connection, line='EAL', track='UP',
            date_str='20260210', repeated_exceptions=sample_eal_exceptions
        )
        save_repeated_records_batch(
            db_connection, line='TML', track='UP',
            date_str='20260210', repeated_exceptions=sample_tml_exceptions
        )
        counts = get_line_counts(db_connection)
        assert counts['EAL'] == 5
        assert counts['TML'] == 3

    def test_counts_with_filters(self, db_connection, sample_eal_exceptions, sample_tml_exceptions):
        """Counts should respect optional filters."""
        save_repeated_records_batch(
            db_connection, line='EAL', track='UP',
            date_str='20260210', repeated_exceptions=sample_eal_exceptions
        )
        save_repeated_records_batch(
            db_connection, line='TML', track='UP',
            date_str='20260210', repeated_exceptions=sample_tml_exceptions
        )
        # Filter by action='Pending' — only EAL records have this
        counts = get_line_counts(db_connection, filters={'action': 'Pending'})
        assert counts['EAL'] == 5
        assert counts['TML'] == 0

    def test_counts_returns_dict_with_both_keys(self, db_connection):
        """Result should always contain both EAL and TML keys."""
        counts = get_line_counts(db_connection)
        assert 'EAL' in counts
        assert 'TML' in counts
        assert isinstance(counts['EAL'], int)
        assert isinstance(counts['TML'], int)
