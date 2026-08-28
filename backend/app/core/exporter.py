import pandas as pd
import io
from typing import Dict, Any, List, Optional
from datetime import datetime

# =============================================================================
# Bug 10.6-2: Date Formatting Constants and Functions
# =============================================================================

# Columns that should be formatted as YYYY/MM/DD
DATE_COLUMNS = [
    'check_date', 'verify_date', 'adjust_date',
    'verify_deadline', 'adjust_deadline', 'task_run_date'
]

# Columns that should be formatted as YYYY/MM/DD HH:mm:ss
DATETIME_COLUMNS = ['saved_at', 'last_updated']


def format_date_for_excel(value) -> str | None:
    """
    Bug 10.6-2: Convert date to YYYY/MM/DD format for Excel export.
    Handles ISO format strings (YYYY-MM-DDTHH:mm:ss.000Z) and datetime objects.
    """
    if pd.isna(value) or value is None:
        return None
    
    if isinstance(value, str):
        if not value.strip():
            return None
        try:
            # Handle ISO format: 2026-02-15T16:00:00.000Z
            dt = pd.to_datetime(value)
            return dt.strftime('%Y/%m/%d')
        except Exception:
            return value
    
    if isinstance(value, datetime):
        return value.strftime('%Y/%m/%d')
    
    if hasattr(value, 'strftime'):  # Handle other datetime-like objects
        return value.strftime('%Y/%m/%d')
    
    return str(value) if value else None


def format_datetime_for_excel(value) -> str | None:
    """
    Bug 10.6-2: Convert datetime to YYYY/MM/DD HH:mm:ss format for Excel export.
    """
    if pd.isna(value) or value is None:
        return None
    
    if isinstance(value, str):
        if not value.strip():
            return None
        try:
            dt = pd.to_datetime(value)
            return dt.strftime('%Y/%m/%d %H:%M:%S')
        except Exception:
            return value
    
    if isinstance(value, datetime):
        return value.strftime('%Y/%m/%d %H:%M:%S')
    
    if hasattr(value, 'strftime'):
        return value.strftime('%Y/%m/%d %H:%M:%S')
    
    return str(value) if value else None


class ExcelExporter:
    # Phase 10.10-F: Strict column order per spec 12.3 (matches ExceptionTable frontend)
    REPORT_COLUMNS = [
        # Task Run Data (#1-#7)
        'task_run_date', 'line', 'track', 'Section',
        'task_no', 'station_start', 'station_end',
        # Exception Details (#8-#21)
        'id', 'FromM', 'ToM', 'length',
        'exception type', 'maxValue', 'maxLocation',
        'Overlap', 'Tension Length', 'Track Type',
        'level', 'Landmark', 'Class', 'Threshold Value',
    ]

    # Phase 10.10-F: Excel-friendly display headers for REPORT_COLUMNS
    REPORT_HEADERS = {
        'task_run_date': 'Run Date',
        'line': 'Line',
        'track': 'Track',
        'Section': 'Section',
        'task_no': 'Task No',
        'station_start': 'St. Start',
        'station_end': 'St. End',
        'id': 'ID',
        'FromM': 'FromM',
        'ToM': 'ToM',
        'length': 'Length',
        'exception type': 'Exception Type',
        'maxValue': 'MaxValue',
        'maxLocation': 'MaxLocation',
        'Overlap': 'Overlap',
        'Tension Length': 'Tension Length',
        'Track Type': 'Track Type',
        'level': 'Level',
        'Landmark': 'Landmark',
        'Class': 'Class',
        'Threshold Value': 'Threshold Value',
    }

    @staticmethod
    def _reorder_columns(df: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
        """
        Reorder DataFrame columns to match the target list.
        Add missing columns as empty.
        Remove extra columns not in the list.
        """
        if df.empty:
            return pd.DataFrame(columns=columns)
            
        # Add missing columns
        for col in columns:
            if col not in df.columns:
                df[col] = None
                
        # Return only the requested columns in order
        return df[columns]

    @staticmethod
    def export_report(
        results: Dict[str, Any], 
        chart_df: pd.DataFrame = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> io.BytesIO:
        """
        Export analysis results to an Excel file.
        Structure:
        - Summary: All exceptions combined, strictly ordered
        - Individual sheets for each exception type
        - ChartData: Raw data for plotting (Optional)
        - _Metadata: Hidden sheet with export metadata (Optional)
        
        Args:
            results: Dictionary of exception DataFrames by type
            chart_df: Optional DataFrame with chart data
            metadata: Optional dictionary with export metadata:
                - session_id: str
                - db_version: int
                - export_timestamp: str
                - schema_version: str
                - app_version: str (optional)
        """
        output = io.BytesIO()
        
        # Prepare Summary DataFrame
        all_exceptions = []
        for exc_type, data in results.items():
            if isinstance(data, list): # handle list of dicts
                df = pd.DataFrame(data)
            elif isinstance(data, pd.DataFrame):
                df = data
            else:
                continue
                
            if not df.empty:
                # Ensure 'exception type' exists if not present
                if 'exception type' not in df.columns:
                    df['exception type'] = exc_type
                all_exceptions.append(df)
        
        if all_exceptions:
            summary_df = pd.concat(all_exceptions, ignore_index=True)
        else:
            summary_df = pd.DataFrame(columns=ExcelExporter.REPORT_COLUMNS)

        # Apply column ordering
        summary_df = ExcelExporter._reorder_columns(summary_df, ExcelExporter.REPORT_COLUMNS)

        # Phase 10.10-F: Apply display headers for Excel export
        summary_df = summary_df.rename(columns=ExcelExporter.REPORT_HEADERS)

        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Write Summary
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Write Individual Sheets
            for exc_type, data in results.items():
                if isinstance(data, pd.DataFrame):
                    df = data
                else:
                    df = pd.DataFrame(data)
                
                # Apply ordering
                df = ExcelExporter._reorder_columns(df, ExcelExporter.REPORT_COLUMNS)
                # Phase 10.10-F: Apply display headers
                df = df.rename(columns=ExcelExporter.REPORT_HEADERS)
                
                # Sheet name limitation (31 chars)
                sheet_name = exc_type[:31] 
                df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            # Write ChartData if available
            # Phase 11 Issue 1 (12.3): ChartData uses same column order as
            # Catenary Report (CATENARY_COLUMNS) so all 31 columns are present.
            if chart_df is not None and not chart_df.empty:
                ordered_cols = [
                    c for c in ExcelExporter.CATENARY_COLUMNS
                    if c in chart_df.columns
                ]
                chart_df[ordered_cols].to_excel(
                    writer, sheet_name='ChartData', index=False
                )
            
            # Write hidden _Metadata sheet if metadata provided
            if metadata:
                ExcelExporter._write_metadata_sheet(writer, metadata)

        output.seek(0)
        return output

    @staticmethod
    def _write_metadata_sheet(writer: pd.ExcelWriter, metadata: Dict[str, Any]) -> None:
        """
        Write a hidden _Metadata sheet with key-value pairs.
        
        Args:
            writer: ExcelWriter instance
            metadata: Dictionary of metadata key-value pairs
        """
        # Convert metadata dict to DataFrame with key-value columns
        meta_rows = []
        for key, value in metadata.items():
            meta_rows.append({'key': key, 'value': str(value)})
        
        meta_df = pd.DataFrame(meta_rows)
        meta_df.to_excel(writer, sheet_name='_Metadata', index=False)
        
        # Hide the sheet
        worksheet = writer.sheets['_Metadata']
        worksheet.sheet_state = 'hidden'

    # Bug 4.1: Alias map for lowercase/snake_case column names from analyzers.py
    CATENARY_COLUMN_ALIASES = {
        'section': 'Section',
        'track_type': 'Track Type',
        'overlap': 'Overlap',
        'tension_length': 'Tension Length',
        'landmark': 'Landmark',
        'class': 'Class',
    }

    # Phase 10.10: Catenary Report column order (spec 12.1 / 12.3)
    # #1-7: Task Run Data, #8: Chainage, #9-20: measurements,
    # #21-25: metadata, #26-31: computed min/max
    CATENARY_COLUMNS = [
        # Task Run Data (#1-#7)
        'task_run_date', 'line', 'track', 'Section',
        'task_no', 'station_start', 'station_end',
        # Measurement Data (#8-#20)
        'Chainage',
        'height1', 'height2', 'height3', 'height4',
        'stagger1', 'stagger2', 'stagger3', 'stagger4',
        'wear1', 'wear2', 'wear3', 'wear4',
        # Metadata (#21-#25)
        'Track Type', 'Overlap', 'Tension Length', 'Landmark', 'Class',
        # Computed (#26-#31)
        'height_min', 'height_max', 'wear_min', 'wear_max',
        'stg_max', 'stg_min',
    ]

    # Display headers for Catenary/ChartData columns
    CATENARY_HEADERS = {
        'task_run_date': 'Run Date',
        'line': 'Line',
        'track': 'Track',
        'Section': 'Section',
        'task_no': 'Task No',
        'station_start': 'St. Start',
        'station_end': 'St. End',
    }

    @staticmethod
    def export_catenary_report(df: pd.DataFrame) -> io.BytesIO:
        """
        Export Catenary Report (raw data + computed columns) to CSV.
        
        Phase 12 Issue 3: Ensures all 31 CATENARY_COLUMNS are present.
        Missing columns are filled with empty values to maintain strict order.
        """
        output = io.BytesIO()

        # Bug 4.1 Fix: Normalize column names before reordering
        rename_map = {}
        for alias, canonical in ExcelExporter.CATENARY_COLUMN_ALIASES.items():
            if alias in df.columns and canonical not in df.columns:
                rename_map[alias] = canonical
        if rename_map:
            df = df.rename(columns=rename_map)

        # Phase 12 Issue 3: Fill missing columns with NaN to ensure all 31 present
        for col in ExcelExporter.CATENARY_COLUMNS:
            if col not in df.columns:
                df = df.assign(**{col: pd.NA})

        export_df = df[ExcelExporter.CATENARY_COLUMNS].rename(columns=ExcelExporter.CATENARY_HEADERS)
        export_df.to_csv(output, index=False)
        output.seek(0)
        return output

    @staticmethod
    def export_raw_csv(df: pd.DataFrame) -> io.BytesIO:
        """
        Export raw cleaned data to CSV.
        (Legacy method - use export_catenary_report for ordered output)
        """
        output = io.BytesIO()
        df.to_csv(output, index=False)
        output.seek(0)
        return output

    @staticmethod
    def export_history_compare(
        df: pd.DataFrame, 
        file_names: List[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> io.BytesIO:
        """
        Export history comparison to Excel with TWO sheets:
        1. "Summary": Detailed comparison report with Multi-Row Headers (Legacy FR-15).
           Contains only the Latest ID.
        2. "Previous": ID Cross-reference table.
           Columns: ID (Latest), Previous 1, Previous 2, ...
        3. "_Metadata": Hidden sheet with export metadata (Optional)
        
        Args:
            df (DataFrame): Data containing 'Previous X' columns.
            file_names (List[str]): List of filenames in chain order.
            metadata (Dict): Optional export metadata for traceability.
        """
        output = io.BytesIO()
        
        # Ensure df is not empty to avoid errors
        if df.empty:
             df = pd.DataFrame(columns=[
                 'task_run_date', 'line', 'track', 'Section',
                 'task_no', 'station_start', 'station_end',
                 'id', 'FromM', 'ToM', 'length', 'exception type', 'maxValue', 
                 'maxLocation', 'Overlap', 'Tension Length', 'Track Type', 'level',
             ])

        # --- Sheet 1: Summary (Multi-Row Header) ---

        # Detect Previous columns early for correct column ordering
        prev_cols = [c for c in df.columns if c.startswith('Previous ') and len(c.split(' ')) == 2 and c.split(' ')[1].isdigit()]
        prev_cols.sort(key=lambda x: int(x.split(' ')[1]))

        # 1. Define the MultiIndex Header Structure
        # Phase 10.10-F: Reordered per spec 12.5, added Line/Track/Section
        columns = [
            # TASK RUN DATA Group (7 cols)
            ('TASK RUN DATA', 'RUN DATE'),
            ('TASK RUN DATA', 'LINE'),
            ('TASK RUN DATA', 'TRACK'),
            ('TASK RUN DATA', 'SECTION'),
            ('TASK RUN DATA', 'TASK NO'),
            ('TASK RUN DATA', 'STATION START'),
            ('TASK RUN DATA', 'STATION END'),
            
            # EXCEPTION Group (11 cols)
            ('EXCEPTION', 'ID'),
            ('EXCEPTION', 'FromM'),
            ('EXCEPTION', 'ToM'),
            ('EXCEPTION', 'Length'),
            ('EXCEPTION', 'Exception Type'),
            ('EXCEPTION', 'MaxValue'),
            ('EXCEPTION', 'MaxLocation'),
            ('EXCEPTION', 'Overlap'),
            ('EXCEPTION', 'Tension Length'),
            ('EXCEPTION', 'Track Type'),
            ('EXCEPTION', 'Level'),
            # Dynamic Previous columns (within EXCEPTION group)
            *[('EXCEPTION', pc) for pc in prev_cols],
            # Reoccurrence ID and Remarks (within EXCEPTION group)
            ('EXCEPTION', 'Reoccurrence ID'),
            ('EXCEPTION', 'Remarks'),

            # INITIAL CHECK Group (4 cols)
            ('INITIAL CHECK', 'ACTION'),
            ('INITIAL CHECK', 'CHECK DATE'),
            ('INITIAL CHECK', 'CHECKED BY'),
            ('INITIAL CHECK', 'CHECK RESULT'),
            
            # SITE VERIFICATION Group (4 cols)
            ('SITE VERIFICATION (IF ANY)', 'VERIFY DEADLINE'),
            ('SITE VERIFICATION (IF ANY)', 'VERIFY DATE'),
            ('SITE VERIFICATION (IF ANY)', 'VERIFY RESULT'),
            ('SITE VERIFICATION (IF ANY)', 'VERIFIED BY'),
            
            # FINAL ADJUSTMENT Group (4 cols)
            ('FINAL ADJUSTMENT (IF ANY)', 'ADJUST DEADLINE'),
            ('FINAL ADJUSTMENT (IF ANY)', 'ADJUST DATE'),
            ('FINAL ADJUSTMENT (IF ANY)', 'ADJUST RESULT'),
            ('FINAL ADJUSTMENT (IF ANY)', 'ADJUSTED BY'),
        ]
        
        multi_index = pd.MultiIndex.from_tuples(columns)
        summary_df = pd.DataFrame(index=df.index, columns=multi_index)
        
        # Map columns
        # Phase 10.10-F: Reordered per spec 12.5, added Line/Track/Section
        mapping = {
            # Task Run Data (7 cols)
            'task_run_date': ('TASK RUN DATA', 'RUN DATE'),
            'line': ('TASK RUN DATA', 'LINE'),
            'track': ('TASK RUN DATA', 'TRACK'),
            'Section': ('TASK RUN DATA', 'SECTION'),
            'task_no': ('TASK RUN DATA', 'TASK NO'),
            'station_start': ('TASK RUN DATA', 'STATION START'),
            'station_end': ('TASK RUN DATA', 'STATION END'),
            
            # Exception Data (11 cols)
            'id': ('EXCEPTION', 'ID'),
            'FromM': ('EXCEPTION', 'FromM'),
            'ToM': ('EXCEPTION', 'ToM'),
            'length': ('EXCEPTION', 'Length'),
            'exception type': ('EXCEPTION', 'Exception Type'),
            'maxValue': ('EXCEPTION', 'MaxValue'),
            'maxLocation': ('EXCEPTION', 'MaxLocation'),
            'Overlap': ('EXCEPTION', 'Overlap'), 
            'Tension Length': ('EXCEPTION', 'Tension Length'),
            'Track Type': ('EXCEPTION', 'Track Type'),
            'level': ('EXCEPTION', 'Level'),
            'reoccurrence_id': ('EXCEPTION', 'Reoccurrence ID'),
            'remarks': ('EXCEPTION', 'Remarks'),

            # Workflow Columns
            'action': ('INITIAL CHECK', 'ACTION'),
            'check_date': ('INITIAL CHECK', 'CHECK DATE'),
            'checked_by': ('INITIAL CHECK', 'CHECKED BY'),
            'check_result': ('INITIAL CHECK', 'CHECK RESULT'),
            
            'verify_deadline': ('SITE VERIFICATION (IF ANY)', 'VERIFY DEADLINE'),
            'verify_date': ('SITE VERIFICATION (IF ANY)', 'VERIFY DATE'),
            'verify_result': ('SITE VERIFICATION (IF ANY)', 'VERIFY RESULT'),
            'verified_by': ('SITE VERIFICATION (IF ANY)', 'VERIFIED BY'),
            
            'adjust_deadline': ('FINAL ADJUSTMENT (IF ANY)', 'ADJUST DEADLINE'),
            'adjust_date': ('FINAL ADJUSTMENT (IF ANY)', 'ADJUST DATE'),
            'adjust_result': ('FINAL ADJUSTMENT (IF ANY)', 'ADJUST RESULT'),
            'adjusted_by': ('FINAL ADJUSTMENT (IF ANY)', 'ADJUSTED BY'),
        }

        # Add dynamic Previous column mappings
        for pc in prev_cols:
            mapping[pc] = ('EXCEPTION', pc)

        # Bug 10.6-2: Apply date formatting during column mapping
        for input_col, output_loc in mapping.items():
            if input_col in df.columns:
                if input_col in DATE_COLUMNS:
                    # Format as YYYY/MM/DD
                    summary_df[output_loc] = df[input_col].apply(format_date_for_excel)
                elif input_col in DATETIME_COLUMNS:
                    # Format as YYYY/MM/DD HH:mm:ss
                    summary_df[output_loc] = df[input_col].apply(format_datetime_for_excel)
                else:
                    summary_df[output_loc] = df[input_col]

        # --- Write to Excel ---
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Summary Sheet
            summary_df.to_excel(writer, sheet_name='Summary', index=True)
            
            worksheet = writer.sheets['Summary']
            
            # 1. Delete the first column (Index)
            worksheet.delete_cols(1)
            
            # 2. Fix Merged Cells (Row 1) - Re-apply merges after column deletion
            # Phase 12 Bug 2.4: Clear all Row 1 merges safely
            ranges_to_remove = [
                r for r in worksheet.merged_cells.ranges if r.min_row == 1
            ]
            for r in ranges_to_remove:
                worksheet.merged_cells.remove(r)
            
            # After removing merge ranges, Row 1 cells are still MergedCell objects
            # whose .value is read-only. Replace Row 1 entirely with fresh cells.
            worksheet.delete_rows(1)
            worksheet.insert_rows(1)
                
            # Apply correct merges — Phase 12 Bug 2.4: Dynamic merge positions
            # Columns are now dynamic due to Previous + Reoccurrence ID + Remarks in EXCEPTION group
            # A-G: TASK RUN DATA (7 cols)
            # H onwards: EXCEPTION (11 base + N previous + reoccurrence_id + remarks)
            # Then: INITIAL CHECK (4), SITE VERIFICATION (4), FINAL ADJUSTMENT (4)
            
            task_run_data_count = 7
            # Count EXCEPTION group columns (base 11 + prev_cols + reoccurrence_id + remarks)
            exception_base_count = 11
            prev_count = len(prev_cols)
            # +1 for reoccurrence_id, +1 for remarks
            exception_total = exception_base_count + prev_count + 2
            initial_check_count = 4
            site_verification_count = 4
            final_adjustment_count = 4
            
            # TASK RUN DATA: cols 1-7
            trd_start = 1
            trd_end = task_run_data_count
            worksheet.cell(row=1, column=trd_start).value = "TASK RUN DATA"
            worksheet.merge_cells(
                start_row=1, start_column=trd_start, end_row=1, end_column=trd_end)
            
            # EXCEPTION: cols 8 to 8+exception_total-1
            exc_start = trd_end + 1
            exc_end = exc_start + exception_total - 1
            worksheet.cell(row=1, column=exc_start).value = "EXCEPTION"
            worksheet.merge_cells(
                start_row=1, start_column=exc_start, end_row=1, end_column=exc_end)
            
            # INITIAL CHECK: next 4 cols
            ic_start = exc_end + 1
            ic_end = ic_start + initial_check_count - 1
            worksheet.cell(row=1, column=ic_start).value = "INITIAL CHECK"
            worksheet.merge_cells(
                start_row=1, start_column=ic_start, end_row=1, end_column=ic_end)
            
            # SITE VERIFICATION: next 4 cols
            sv_start = ic_end + 1
            sv_end = sv_start + site_verification_count - 1
            worksheet.cell(row=1, column=sv_start).value = "SITE VERIFICATION (IF ANY)"
            worksheet.merge_cells(
                start_row=1, start_column=sv_start, end_row=1, end_column=sv_end)
            
            # FINAL ADJUSTMENT: next 4 cols
            fa_start = sv_end + 1
            fa_end = fa_start + final_adjustment_count - 1
            worksheet.cell(row=1, column=fa_start).value = "FINAL ADJUSTMENT (IF ANY)"
            worksheet.merge_cells(
                start_row=1, start_column=fa_start, end_row=1, end_column=fa_end)
            
            # Center Align Row 1
            from openpyxl.styles import Alignment
            center_align = Alignment(horizontal='center', vertical='center')
            for start_col in [trd_start, exc_start, ic_start, sv_start, fa_start]:
                worksheet.cell(row=1, column=start_col).alignment = center_align

            # 3. Clean up potential index name row (Row 3)
            # Assuming row 3 is blank/redundant due to index=True
            if worksheet['A3'].value is None and worksheet['B3'].value is None:
                 worksheet.delete_rows(3)

            # Phase 12 Bug 2.4: Previous sheet merged into Summary — no separate sheet

            # Adjust widths - Phase 12: Extended for merged Previous + Reoccurrence ID + Remarks
            for sheet_name in ['Summary']:
                if sheet_name in writer.sheets:
                    ws = writer.sheets[sheet_name]
                    total_cols = len(columns)
                    for col in range(1, total_cols + 2): 
                        col_letter = chr(64 + col) if col <= 26 else f"A{chr(64 + col - 26)}"
                        try:
                            ws.column_dimensions[col_letter].width = 15
                        except Exception:
                            pass
            
            # Write hidden _Metadata sheet if metadata provided
            if metadata:
                ExcelExporter._write_metadata_sheet(writer, metadata)
                
        output.seek(0)
        return output
