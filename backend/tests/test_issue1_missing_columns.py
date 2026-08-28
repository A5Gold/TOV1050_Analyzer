"""
Phase 11 Issue 1: Tests for missing columns and content per field-mapping-spec.md Section 12.

Tests cover:
- 12.3: Exception Report Excel ChartData sheet includes all 31 columns
- 12.4/12.5: RepeatedExceptionFinder preserves level and task run data columns
- 12.6/12.7: Database export column order (adjust_result before adjusted_by)
"""
import io
import pandas as pd
import pytest
from unittest.mock import patch

from app.core.exporter import ExcelExporter
from app.core.repeated_finder import RepeatedExceptionFinder


class TestSection12_3_ChartDataSheet:
    """12.3: ChartData sheet should include all columns matching Catenary Report."""

    def test_chartdata_includes_task_run_data_columns(self):
        """ChartData sheet must include Task Run Data columns #1-#7."""
        chart_df = pd.DataFrame({
            'task_run_date': ['20260101', '20260101'],
            'line': ['EAL', 'EAL'],
            'track': ['UP', 'UP'],
            'Section': ['Mainline', 'Mainline'],
            'task_no': ['U1', 'U1'],
            'station_start': ['HUH', 'HUH'],
            'station_end': ['RAC', 'RAC'],
            'Chainage': [100.0, 101.0],
            'height1': [5300, 5310],
            'height2': [5200, 5210],
            'height3': [5100, 5110],
            'height4': [5000, 5010],
            'stagger1': [200, 210],
            'stagger2': [100, 110],
            'stagger3': [50, 60],
            'stagger4': [30, 40],
            'wear1': [1.0, 1.1],
            'wear2': [2.0, 2.1],
            'wear3': [3.0, 3.1],
            'wear4': [4.0, 4.1],
            'Track Type': ['Normal', 'Normal'],
            'Overlap': ['No', 'No'],
            'Tension Length': ['1500', '1500'],
            'Landmark': ['LM1', 'LM1'],
            'Class': ['A', 'A'],
            'height_min': [5000, 5010],
            'height_max': [5300, 5310],
            'wear_min': [1.0, 1.1],
            'wear_max': [4.0, 4.1],
            'stg_max': [200, 210],
            'stg_min': [30, 40],
        })

        results = {'Low Height': pd.DataFrame({
            'id': ['exc-1'],
            'exception type': ['Low Height'],
            'FromM': [100.0],
            'ToM': [101.0],
            'length': [1.0],
            'maxValue': [5000],
            'maxLocation': [100.5],
            'level': ['L1'],
        })}

        excel_bytes = ExcelExporter.export_report(results, chart_df=chart_df)
        excel_file = pd.ExcelFile(io.BytesIO(excel_bytes.read()))

        assert 'ChartData' in excel_file.sheet_names
        chart_sheet = pd.read_excel(excel_file, sheet_name='ChartData')

        # Verify Task Run Data columns exist (#1-#7)
        expected_task_cols = [
            'task_run_date', 'line', 'track', 'Section',
            'task_no', 'station_start', 'station_end',
        ]
        for col in expected_task_cols:
            assert col in chart_sheet.columns, f"Missing column: {col}"

        # Verify metadata columns exist (#21-#25)
        expected_meta_cols = ['Track Type', 'Overlap', 'Tension Length', 'Landmark', 'Class']
        for col in expected_meta_cols:
            assert col in chart_sheet.columns, f"Missing column: {col}"

        # Verify computed columns exist (#26-#31)
        expected_computed = ['height_min', 'height_max', 'wear_min', 'wear_max', 'stg_max', 'stg_min']
        for col in expected_computed:
            assert col in chart_sheet.columns, f"Missing column: {col}"

    def test_chartdata_column_order_matches_catenary(self):
        """ChartData columns should follow CATENARY_COLUMNS order."""
        chart_df = pd.DataFrame({
            'Chainage': [100.0],
            'height1': [5300],
            'stagger1': [200],
            'wear1': [1.0],
            'task_run_date': ['20260101'],
            'line': ['EAL'],
            'track': ['UP'],
            'Section': ['Mainline'],
            'task_no': ['U1'],
            'station_start': ['HUH'],
            'station_end': ['RAC'],
        })

        results = {'Low Height': pd.DataFrame({
            'id': ['exc-1'],
            'exception type': ['Low Height'],
            'FromM': [100.0],
            'ToM': [101.0],
            'length': [1.0],
            'maxValue': [5000],
            'maxLocation': [100.5],
            'level': ['L1'],
        })}

        excel_bytes = ExcelExporter.export_report(results, chart_df=chart_df)
        chart_sheet = pd.read_excel(io.BytesIO(excel_bytes.read()), sheet_name='ChartData')

        cols = list(chart_sheet.columns)
        # task_run_date should come before Chainage
        assert cols.index('task_run_date') < cols.index('Chainage')
        # Chainage should come before height1
        assert cols.index('Chainage') < cols.index('height1')


class TestSection12_4_5_LevelAndTaskRunData:
    """12.4/12.5: RepeatedExceptionFinder must preserve level and task run data."""

    def _make_df(self, ids, extra_cols=None):
        """Helper to create exception DataFrames."""
        data = {
            'id': ids,
            'exception type': ['Low Height'] * len(ids),
            'FromM': [100.0] * len(ids),
            'ToM': [110.0] * len(ids),
            'maxValue': [5000] * len(ids),
            'maxLocation': [105.0] * len(ids),
            'length': [10.0] * len(ids),
        }
        if extra_cols:
            data.update(extra_cols)
        return pd.DataFrame(data)

    def test_level_preserved_in_repeated_results(self):
        """Level column must be preserved through find_repeated."""
        finder = RepeatedExceptionFinder()
        latest = self._make_df(['exc-1'], {'level': ['L1']})
        previous = self._make_df(['exc-2'])

        result = finder.find_repeated(latest, previous, 'Previous 1')

        assert not result.empty
        assert 'level' in result.columns
        assert result.iloc[0]['level'] == 'L1'

    def test_task_run_data_preserved_in_repeated_results(self):
        """Task run data columns must be preserved through find_repeated."""
        finder = RepeatedExceptionFinder()
        latest = self._make_df(['exc-1'], {
            'task_run_date': ['20260101'],
            'line': ['EAL'],
            'track': ['UP'],
            'task_no': ['U1'],
            'station_start': ['HUH'],
            'station_end': ['RAC'],
        })
        previous = self._make_df(['exc-2'])

        result = finder.find_repeated(latest, previous, 'Previous 1')

        assert not result.empty
        for col in ['task_run_date', 'line', 'track', 'task_no', 'station_start', 'station_end']:
            assert col in result.columns, f"Missing column: {col}"
        assert result.iloc[0]['task_run_date'] == '20260101'
        assert result.iloc[0]['line'] == 'EAL'
        assert result.iloc[0]['task_no'] == 'U1'


class TestSection12_6_7_ColumnOrder:
    """12.6/12.7: adjust_result must come before adjusted_by in export."""

    def test_database_export_adjust_column_order(self):
        """export_repeated_records_to_df: adjust_result before adjusted_by."""
        from app.core.database import export_repeated_records_to_df
        import sqlite3

        conn = sqlite3.connect(':memory:')
        conn.row_factory = sqlite3.Row

        # Create table
        conn.execute("""
            CREATE TABLE saved_repeated_exceptions (
                record_id INTEGER PRIMARY KEY AUTOINCREMENT,
                exception_id TEXT, exception_type TEXT, level TEXT,
                from_m REAL, to_m REAL, length REAL,
                max_value REAL, max_location REAL,
                track_type TEXT, overlap TEXT, tension_length TEXT,
                landmark TEXT, class TEXT, threshold_value REAL, section TEXT,
                previous_1 TEXT, previous_2 TEXT, repeat_count INTEGER,
                reoccurrence_id TEXT,
                action TEXT, check_date TEXT, checked_by TEXT,
                check_result TEXT, remarks TEXT,
                verify_deadline TEXT, verify_date TEXT,
                verify_result TEXT, verified_by TEXT,
                adjust_deadline TEXT, adjust_date TEXT,
                adjust_result TEXT, adjusted_by TEXT,
                line TEXT, track TEXT, date_str TEXT,
                task_run_date TEXT, task_no TEXT,
                station_start TEXT, station_end TEXT,
                latest_file_name TEXT, comparison_files TEXT,
                saved_by TEXT, saved_at DATETIME, last_updated DATETIME
            )
        """)

        conn.execute("""
            INSERT INTO saved_repeated_exceptions (
                exception_id, exception_type, level, from_m, to_m,
                adjust_result, adjusted_by,
                line, track, date_str
            ) VALUES (
                'exc-1', 'Low Height', 'L1', 100.0, 110.0,
                'Completed', 'John',
                'EAL', 'UP', '20260101'
            )
        """)
        conn.commit()

        df = export_repeated_records_to_df(conn)
        cols = list(df.columns)

        # ADJUST RESULT should come before ADJUSTED BY
        assert 'ADJUST RESULT' in cols
        assert 'ADJUSTED BY' in cols
        assert cols.index('ADJUST RESULT') < cols.index('ADJUSTED BY')

        conn.close()


class TestCatenaryReportHeaders:
    """Catenary Report CSV should use display headers for task run data."""

    def test_catenary_report_uses_display_headers(self):
        """export_catenary_report should rename task_run_date to Run Date etc."""
        df = pd.DataFrame({
            'task_run_date': ['20260101'],
            'line': ['EAL'],
            'track': ['UP'],
            'Section': ['Mainline'],
            'task_no': ['U1'],
            'station_start': ['HUH'],
            'station_end': ['RAC'],
            'Chainage': [100.0],
            'height1': [5300],
            'stagger1': [200],
            'wear1': [1.0],
        })

        output = ExcelExporter.export_catenary_report(df)
        csv_content = output.read().decode('utf-8')
        header_line = csv_content.split('\n')[0]

        assert 'Run Date' in header_line
        assert 'St. Start' in header_line
        assert 'St. End' in header_line
        assert 'Task No' in header_line
