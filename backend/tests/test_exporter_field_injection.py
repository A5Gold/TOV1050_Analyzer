"""
Test Suite: Issue 1 Phase A2 - Exception Report Field Injection

These tests verify that Task Run Data fields (task_run_date, line, track, task_no, 
station_start, station_end) are correctly injected into exception records before export.

Reference: docs/field-mapping-spec.md Section 12.3
"""

import pytest
import pandas as pd
import io
from unittest.mock import MagicMock, patch

from app.core.exporter import ExcelExporter


class TestExceptionReportFieldInjection:
    """
    Tests for verifying Task Run Data fields are present in Exception Report export.
    
    Issue 1 Phase A2: Catenary/Exception Report 欄位補全
    """
    
    def test_export_report_includes_task_run_data_fields_in_summary(self):
        """
        Verify that Summary sheet includes Task Run Data fields.
        Reference: Section 12.3 - Fields 1-7 should exist in Summary.
        """
        # Arrange: Create mock exception data with Task Run Data fields injected
        mock_exceptions = {
            'Low Height': pd.DataFrame([{
                'task_run_date': '20260209',
                'line': 'EAL',
                'track': 'UP',
                'Section': 'Mainline',
                'task_no': 'U1',
                'station_start': 'HUH',
                'station_end': 'RAC',
                'id': 'LH-001',
                'FromM': 1000.0,
                'ToM': 1100.0,
                'length': 100.0,
                'exception type': 'Low Height',
                'maxValue': 5200,
                'maxLocation': 1050.0,
                'Overlap': '',
                'Tension Length': '',
                'Track Type': 'Tangent',
                'level': 'L1',
                'Landmark': '',
                'Class': 'A',
                'Threshold Value': 5250,
            }])
        }
        
        # Act
        excel_bytes = ExcelExporter.export_report(mock_exceptions)
        
        # Assert: Read the exported Excel and verify columns
        excel_bytes.seek(0)
        with pd.ExcelFile(excel_bytes) as xls:
            summary_df = pd.read_excel(xls, sheet_name='Summary')
            
            # Verify Task Run Data columns exist (using display headers)
            expected_headers = ['Run Date', 'Line', 'Track', 'Section', 
                               'Task No', 'St. Start', 'St. End']
            for header in expected_headers:
                assert header in summary_df.columns, \
                    f"Expected column '{header}' not found in Summary sheet. " \
                    f"Found columns: {summary_df.columns.tolist()}"
            
            # Verify data values are populated
            # Note: Excel may read numeric-looking strings as numbers
            assert str(summary_df['Run Date'].iloc[0]) == '20260209'
            assert summary_df['Line'].iloc[0] == 'EAL'
            assert summary_df['Track'].iloc[0] == 'UP'
    
    def test_export_report_includes_task_run_data_in_individual_sheets(self):
        """
        Verify that individual exception type sheets also include Task Run Data.
        """
        # Arrange
        mock_exceptions = {
            'Wire Wear': pd.DataFrame([{
                'task_run_date': '20260209',
                'line': 'TML',
                'track': 'DN',
                'Section': 'RAC',
                'task_no': 'D2',
                'station_start': 'LOW',
                'station_end': 'SHA',
                'id': 'WW-001',
                'FromM': 2000.0,
                'ToM': 2050.0,
                'length': 50.0,
                'exception type': 'Wire Wear',
                'maxValue': 8.5,
                'maxLocation': 2025.0,
                'Overlap': 'Y',
                'Tension Length': '1500',
                'Track Type': 'Curve',
                'level': 'L2',
                'Landmark': 'Platform',
                'Class': 'B',
                'Threshold Value': 8.0,
            }])
        }
        
        # Act
        excel_bytes = ExcelExporter.export_report(mock_exceptions)
        
        # Assert
        excel_bytes.seek(0)
        with pd.ExcelFile(excel_bytes) as xls:
            # Read Wire Wear sheet
            ww_df = pd.read_excel(xls, sheet_name='Wire Wear')
            
            # Verify Task Run Data columns exist
            assert 'Run Date' in ww_df.columns
            assert 'Line' in ww_df.columns
            assert 'Track' in ww_df.columns
            
            # Verify data values
            assert ww_df['Line'].iloc[0] == 'TML'
            assert ww_df['Section'].iloc[0] == 'RAC'
    
    def test_export_report_handles_missing_optional_fields(self):
        """
        Verify that export handles None values for optional Task Run Data fields.
        (task_no, station_start, station_end are optional per spec)
        """
        # Arrange: Data with missing optional fields
        mock_exceptions = {
            'High Height': pd.DataFrame([{
                'task_run_date': '20260209',
                'line': 'EAL',
                'track': 'UP',
                'Section': 'Mainline',
                'task_no': None,  # Optional - can be None
                'station_start': None,  # Optional
                'station_end': None,  # Optional
                'id': 'HH-001',
                'FromM': 3000.0,
                'ToM': 3100.0,
                'length': 100.0,
                'exception type': 'High Height',
                'maxValue': 5450,
                'maxLocation': 3050.0,
                'Overlap': '',
                'Tension Length': '',
                'Track Type': 'Tangent',
                'level': 'L1',
                'Landmark': '',
                'Class': 'A',
                'Threshold Value': 5400,
            }])
        }
        
        # Act - should not raise
        excel_bytes = ExcelExporter.export_report(mock_exceptions)
        
        # Assert
        excel_bytes.seek(0)
        with pd.ExcelFile(excel_bytes) as xls:
            summary_df = pd.read_excel(xls, sheet_name='Summary')
            
            # Required fields should be present
            assert summary_df['Line'].iloc[0] == 'EAL'
            
            # Optional fields should exist as columns (even if None)
            assert 'Task No' in summary_df.columns
            assert 'St. Start' in summary_df.columns
            assert 'St. End' in summary_df.columns


class TestCatenaryReportFieldInjection:
    """
    Tests for verifying Catenary Report includes computed columns.
    
    Issue 1 Phase A2: height_min/max, wear_min/max in Catenary Report
    Reference: Section 12.1
    """
    
    def test_export_catenary_report_includes_computed_columns(self):
        """
        Verify that Catenary Report includes height_min/max and wear_min/max.
        These columns should be pre-computed by analyzers.py.
        """
        # Arrange: DataFrame with all required columns
        mock_df = pd.DataFrame([{
            'Chainage': 1000.0,
            'height1': 5200, 'height2': 5220, 'height3': 5180, 'height4': 5250,
            'stagger1': 10, 'stagger2': -5, 'stagger3': 15, 'stagger4': -10,
            'wear1': 8.0, 'wear2': 8.5, 'wear3': 7.5, 'wear4': 9.0,
            'Track Type': 'Tangent',
            'Overlap': '',
            'Tension Length': '1500',
            'Landmark': 'Station',
            'Class': 'A',
            # Computed columns (from analyzers.py)
            'height_min': 5180,
            'height_max': 5250,
            'wear_min': 7.5,
            'wear_max': 9.0,
            'stg_max': 15,
            'stg_min': -10,
        }])
        
        # Act
        csv_bytes = ExcelExporter.export_catenary_report(mock_df)
        
        # Assert
        csv_bytes.seek(0)
        result_df = pd.read_csv(csv_bytes)
        
        # Verify computed columns are included
        expected_columns = ['height_min', 'height_max', 'wear_min', 'wear_max', 
                           'stg_max', 'stg_min']
        for col in expected_columns:
            assert col in result_df.columns, \
                f"Expected computed column '{col}' not found in Catenary Report"
        
        # Verify values are correct
        assert result_df['height_min'].iloc[0] == 5180
        assert result_df['height_max'].iloc[0] == 5250
        assert result_df['wear_min'].iloc[0] == 7.5
        assert result_df['wear_max'].iloc[0] == 9.0
    
    def test_export_catenary_report_column_order(self):
        """
        Verify that Catenary Report exports columns in the correct order.
        Reference: Section 12.1 column order
        """
        # Arrange
        mock_df = pd.DataFrame([{
            'Chainage': 1000.0,
            'height1': 5200, 'height2': 5220, 'height3': 5180, 'height4': 5250,
            'stagger1': 10, 'stagger2': -5, 'stagger3': 15, 'stagger4': -10,
            'wear1': 8.0, 'wear2': 8.5, 'wear3': 7.5, 'wear4': 9.0,
            'Track Type': 'Tangent',
            'Overlap': '',
            'Tension Length': '1500',
            'Landmark': 'Station',
            'Class': 'A',
            'height_min': 5180,
            'height_max': 5250,
            'wear_min': 7.5,
            'wear_max': 9.0,
            'stg_max': 15,
            'stg_min': -10,
        }])
        
        # Act
        csv_bytes = ExcelExporter.export_catenary_report(mock_df)
        
        # Assert
        csv_bytes.seek(0)
        result_df = pd.read_csv(csv_bytes)
        
        # First column should be Run Date (Task Run Data group)
        # Phase 12 Issue 3: Missing columns are now filled, so all 31 cols present
        assert result_df.columns[0] == 'Run Date'
        
        # Chainage should be column #8
        assert result_df.columns[7] == 'Chainage'
        
        # height1-4 should come before stagger1-4
        height_idx = result_df.columns.tolist().index('height1')
        stagger_idx = result_df.columns.tolist().index('stagger1')
        assert height_idx < stagger_idx, "height columns should come before stagger columns"


class TestExportReportColumnOrder:
    """
    Tests for verifying Exception Report exports columns in the correct order.
    Reference: Section 12.3
    """
    
    def test_report_columns_match_spec_order(self):
        """
        Verify REPORT_COLUMNS matches Section 12.3 specification.
        """
        # Expected order per Section 12.3
        expected_order = [
            'task_run_date', 'line', 'track', 'Section',
            'task_no', 'station_start', 'station_end',
            'id', 'FromM', 'ToM', 'length',
            'exception type', 'maxValue', 'maxLocation',
            'Overlap', 'Tension Length', 'Track Type',
            'level', 'Landmark', 'Class', 'Threshold Value',
        ]
        
        # Assert
        assert ExcelExporter.REPORT_COLUMNS == expected_order, \
            f"REPORT_COLUMNS order does not match spec. " \
            f"Expected: {expected_order}, Got: {ExcelExporter.REPORT_COLUMNS}"
