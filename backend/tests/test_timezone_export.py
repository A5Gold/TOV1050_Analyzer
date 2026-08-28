"""
Phase 12 - Issue 8: Timezone Export Tests
==========================================
Tests for _format_datetime_for_export UTC → UTC+8 conversion.

Bug: saved_at/last_updated shows UTC time instead of UTC+8 (Hong Kong time).
Example: Computer time 10/02/2026 01:23:59, Excel shows 09/02/2026 17:23:59.
Fix: Convert UTC to UTC+8 in _format_datetime_for_export.
"""

import pytest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.database import _format_datetime_for_export


class TestFormatDatetimeUtcToHk:
    """Tests for UTC → UTC+8 timezone conversion in datetime export."""

    def test_iso_format_utc_to_hk(self):
        """UTC 2026-02-09T17:23:59 should display as 2026/02/10 01:23:59 (UTC+8)."""
        result = _format_datetime_for_export('2026-02-09T17:23:59')
        assert result == '2026/02/10 01:23:59'

    def test_iso_format_with_z_suffix(self):
        """UTC with Z suffix should also convert to UTC+8."""
        result = _format_datetime_for_export('2026-02-09T17:23:59Z')
        assert result == '2026/02/10 01:23:59'

    def test_iso_format_with_utc_offset(self):
        """UTC with +00:00 offset should convert to UTC+8."""
        result = _format_datetime_for_export('2026-02-09T17:23:59+00:00')
        assert result == '2026/02/10 01:23:59'

    def test_sqlite_format_utc_to_hk(self):
        """SQLite default format (YYYY-MM-DD HH:MM:SS) assumed UTC, convert to UTC+8."""
        result = _format_datetime_for_export('2026-02-09 17:23:59')
        assert result == '2026/02/10 01:23:59'

    def test_midnight_utc_becomes_morning_hk(self):
        """UTC midnight should become 08:00 HK time."""
        result = _format_datetime_for_export('2026-02-10T00:00:00')
        assert result == '2026/02/10 08:00:00'

    def test_late_night_utc_crosses_date(self):
        """UTC 16:00+ should cross to next day in HK time."""
        result = _format_datetime_for_export('2026-02-09T16:00:00')
        assert result == '2026/02/10 00:00:00'

    def test_none_returns_empty(self):
        """None input should return empty string."""
        assert _format_datetime_for_export(None) == ''

    def test_empty_string_returns_empty(self):
        """Empty string should return empty string."""
        assert _format_datetime_for_export('') == ''

    def test_invalid_format_returns_original(self):
        """Invalid format should return original value."""
        result = _format_datetime_for_export('not-a-date')
        assert result == 'not-a-date'

    def test_date_only_returns_original(self):
        """Date-only string should return original (no time to convert)."""
        result = _format_datetime_for_export('2026-02-09')
        assert result == '2026-02-09'
