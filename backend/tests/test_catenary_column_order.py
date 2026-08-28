"""
Test Catenary Report CSV Column Order (Issue 3)
================================================
Verify CATENARY_COLUMNS 31-column order and ensure DataFrame
contains all columns even when some are missing from input.

Phase 12 Task 6: TDD — RED → GREEN → REFACTOR
"""
import io
import pytest
import pandas as pd
from app.core.exporter import ExcelExporter


EXPECTED_COLUMN_COUNT = 31

EXPECTED_HEADERS = [
    'Run Date', 'Line', 'Track', 'Section', 'Task No', 'St. Start', 'St. End',
    'Chainage',
    'height1', 'height2', 'height3', 'height4',
    'stagger1', 'stagger2', 'stagger3', 'stagger4',
    'wear1', 'wear2', 'wear3', 'wear4',
    'Track Type', 'Overlap', 'Tension Length', 'Landmark', 'Class',
    'height_min', 'height_max', 'wear_min', 'wear_max',
    'stg_max', 'stg_min',
]


def _make_full_catenary_df(n_rows: int = 3) -> pd.DataFrame:
    """Create a test DataFrame with all 31 CATENARY_COLUMNS."""
    data = {}
    for col in ExcelExporter.CATENARY_COLUMNS:
        if col in ('line', 'track', 'Section', 'Track Type', 'Overlap',
                   'Tension Length', 'Landmark', 'Class'):
            data[col] = ['test'] * n_rows
        else:
            data[col] = [1.0] * n_rows
    return pd.DataFrame(data)


def _make_partial_catenary_df(n_rows: int = 3) -> pd.DataFrame:
    """Create a test DataFrame missing computed columns (#26-31)."""
    partial_cols = ExcelExporter.CATENARY_COLUMNS[:25]  # Only #1-25
    data = {}
    for col in partial_cols:
        if col in ('line', 'track', 'Section', 'Track Type', 'Overlap',
                   'Tension Length', 'Landmark', 'Class'):
            data[col] = ['test'] * n_rows
        else:
            data[col] = [1.0] * n_rows
    return pd.DataFrame(data)


class TestCatenaryColumnOrder:
    """Tests for Catenary Report CSV column order and completeness."""

    def test_catenary_columns_count(self):
        """CATENARY_COLUMNS should define exactly 31 columns."""
        assert len(ExcelExporter.CATENARY_COLUMNS) == EXPECTED_COLUMN_COUNT

    def test_full_dataframe_column_order(self):
        """With all columns present, CSV should have 31 columns in correct order."""
        df = _make_full_catenary_df()
        output = ExcelExporter.export_catenary_report(df)
        output.seek(0)
        result_df = pd.read_csv(output)

        assert list(result_df.columns) == EXPECTED_HEADERS
        assert len(result_df.columns) == EXPECTED_COLUMN_COUNT

    def test_partial_dataframe_fills_missing_columns(self):
        """When computed columns are missing, they should be filled with empty/NaN
        and still appear in the output with correct order and count."""
        df = _make_partial_catenary_df()
        output = ExcelExporter.export_catenary_report(df)
        output.seek(0)
        result_df = pd.read_csv(output)

        assert len(result_df.columns) == EXPECTED_COLUMN_COUNT
        assert list(result_df.columns) == EXPECTED_HEADERS

    def test_column_order_matches_spec(self):
        """Column order should match spec: Task Run Data → Chainage → 
        height → stagger → wear → metadata → computed."""
        cols = ExcelExporter.CATENARY_COLUMNS
        # Task Run Data: #1-7
        assert cols[0:7] == [
            'task_run_date', 'line', 'track', 'Section',
            'task_no', 'station_start', 'station_end',
        ]
        # Chainage: #8
        assert cols[7] == 'Chainage'
        # Height: #9-12
        assert cols[8:12] == ['height1', 'height2', 'height3', 'height4']
        # Stagger: #13-16
        assert cols[12:16] == ['stagger1', 'stagger2', 'stagger3', 'stagger4']
        # Wear: #17-20
        assert cols[16:20] == ['wear1', 'wear2', 'wear3', 'wear4']
        # Metadata: #21-25
        assert cols[20:25] == ['Track Type', 'Overlap', 'Tension Length', 'Landmark', 'Class']
        # Computed: #26-31
        assert cols[25:31] == ['height_min', 'height_max', 'wear_min', 'wear_max', 'stg_max', 'stg_min']

    def test_empty_dataframe_returns_headers_only(self):
        """Empty DataFrame should still produce CSV with correct headers."""
        df = pd.DataFrame(columns=ExcelExporter.CATENARY_COLUMNS)
        output = ExcelExporter.export_catenary_report(df)
        output.seek(0)
        result_df = pd.read_csv(output)

        assert list(result_df.columns) == EXPECTED_HEADERS
        assert len(result_df) == 0

    def test_extra_columns_are_excluded(self):
        """Extra columns not in CATENARY_COLUMNS should be excluded from output."""
        df = _make_full_catenary_df()
        df['extra_col'] = 'should_not_appear'
        df['another_extra'] = 999

        output = ExcelExporter.export_catenary_report(df)
        output.seek(0)
        result_df = pd.read_csv(output)

        assert 'extra_col' not in result_df.columns
        assert 'another_extra' not in result_df.columns
        assert len(result_df.columns) == EXPECTED_COLUMN_COUNT


def _make_lowercase_catenary_df() -> pd.DataFrame:
    """Create a test DataFrame with lowercase column names as produced by analyzers.py."""
    return pd.DataFrame({
        'task_run_date': ['20260210'],
        'line': ['EAL'],
        'track': ['UP'],
        'section': ['Mainline'],          # lowercase (canonical: Section)
        'task_no': ['U1'],
        'station_start': ['HUH'],
        'station_end': ['LOW'],
        'Chainage': [1000.0],
        'height1': [5200], 'height2': [5210], 'height3': [5220], 'height4': [5230],
        'stagger1': [100], 'stagger2': [110], 'stagger3': [120], 'stagger4': [130],
        'wear1': [10.5], 'wear2': [10.6], 'wear3': [10.7], 'wear4': [10.8],
        'track_type': ['Tangent'],         # lowercase (canonical: Track Type)
        'overlap': ['No'],                 # lowercase (canonical: Overlap)
        'tension_length': ['TL-001'],      # lowercase (canonical: Tension Length)
        'landmark': ['KM10'],              # lowercase (canonical: Landmark)
        'class': ['Standard'],             # lowercase (canonical: Class)
        'height_min': [5200], 'height_max': [5230],
        'wear_min': [10.5], 'wear_max': [10.8],
        'stg_max': [130], 'stg_min': [100],
    })


class TestCatenaryColumnAliases:
    """Bug 4.1: Tests for lowercase/mixed-case column name normalization."""

    def test_catenary_export_with_lowercase_columns(self):
        """DataFrame with lowercase column names should produce correct CSV
        with all 31 columns populated (not NaN)."""
        df = _make_lowercase_catenary_df()
        output = ExcelExporter.export_catenary_report(df)
        output.seek(0)
        result_df = pd.read_csv(output)

        assert len(result_df.columns) == EXPECTED_COLUMN_COUNT
        assert list(result_df.columns) == EXPECTED_HEADERS
        # The aliased columns must contain actual data, not NaN
        assert result_df['Section'].iloc[0] == 'Mainline'
        assert result_df['Track Type'].iloc[0] == 'Tangent'
        assert result_df['Overlap'].iloc[0] == 'No'
        assert result_df['Tension Length'].iloc[0] == 'TL-001'
        assert result_df['Landmark'].iloc[0] == 'KM10'
        assert result_df['Class'].iloc[0] == 'Standard'

    def test_catenary_export_with_mixed_case_columns(self):
        """DataFrame with some uppercase and some lowercase columns should
        produce all columns populated."""
        df = _make_lowercase_catenary_df()
        # Override some to canonical case (mixed scenario)
        df = df.rename(columns={'section': 'Section', 'overlap': 'Overlap'})
        output = ExcelExporter.export_catenary_report(df)
        output.seek(0)
        result_df = pd.read_csv(output)

        assert len(result_df.columns) == EXPECTED_COLUMN_COUNT
        assert result_df['Section'].iloc[0] == 'Mainline'
        assert result_df['Overlap'].iloc[0] == 'No'
        assert result_df['Track Type'].iloc[0] == 'Tangent'
        assert result_df['Tension Length'].iloc[0] == 'TL-001'

    def test_catenary_export_strict_31_columns(self):
        """Output CSV from lowercase-column DataFrame must have exactly 31 columns."""
        df = _make_lowercase_catenary_df()
        output = ExcelExporter.export_catenary_report(df)
        output.seek(0)
        result_df = pd.read_csv(output)

        assert len(result_df.columns) == EXPECTED_COLUMN_COUNT

    def test_catenary_export_column_aliases_complete(self):
        """All known aliases must be mapped in CATENARY_COLUMN_ALIASES."""
        aliases = ExcelExporter.CATENARY_COLUMN_ALIASES
        expected_aliases = {
            'section': 'Section',
            'track_type': 'Track Type',
            'overlap': 'Overlap',
            'tension_length': 'Tension Length',
            'landmark': 'Landmark',
            'class': 'Class',
        }
        for alias, canonical in expected_aliases.items():
            assert alias in aliases, f"Missing alias: {alias}"
            assert aliases[alias] == canonical

    def test_catenary_export_preserves_data_values(self):
        """Data values must not be lost during column normalization."""
        df = _make_lowercase_catenary_df()
        output = ExcelExporter.export_catenary_report(df)
        output.seek(0)
        result_df = pd.read_csv(output)

        # Verify non-aliased columns are also intact
        assert str(result_df['Run Date'].iloc[0]) == '20260210'
        assert result_df['Line'].iloc[0] == 'EAL'
        assert result_df['Track'].iloc[0] == 'UP'
        assert result_df['Chainage'].iloc[0] == 1000.0
        assert result_df['height1'].iloc[0] == 5200
        assert result_df['stagger1'].iloc[0] == 100
        assert result_df['wear1'].iloc[0] == 10.5
        # Verify aliased columns have real data
        assert result_df['Section'].iloc[0] == 'Mainline'
        assert result_df['Track Type'].iloc[0] == 'Tangent'
