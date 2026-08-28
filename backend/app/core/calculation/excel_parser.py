"""
Excel parser for Exception Report files.
Parses Wire Wear sheet and ChartData sheet.
"""
from dataclasses import dataclass
from typing import Optional, List, Tuple
import io
import logging
import pandas as pd
from openpyxl import load_workbook

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WireWearRecord:
    run_date: str
    exception_id: str
    tension_length: str
    from_m: float
    to_m: float
    max_value: float
    level: str
    action: Optional[str]
    max_location: float = 0.0


@dataclass(frozen=True)
class ChartDataRecord:
    task_run_date: str
    line: Optional[str]
    track: Optional[str]
    section: Optional[str]
    task_no: str
    station_start: str
    station_end: str
    tension_length: str
    chainage: float
    wear_min: float
    track_type: str
    overlap: Optional[str]


@dataclass(frozen=True)
class RepeatedSummaryRecord:
    exception_id: str   # Column 'ID'
    from_m: float       # Column 'FromM'
    to_m: float         # Column 'ToM'
    run_date: str       # Column 'RUN DATE'
    max_value: float    # Column 'MaxValue'
    max_location: float # Column 'MaxLocation'
    exception_type: str # Column 'Exception Type'
    level: str          # Column 'Level'


def _normalize_identifier(val) -> str:
    """Normalize Excel IDs so numeric-looking values compare consistently."""
    if val is None:
        return ''
    if not isinstance(val, str) and pd.isna(val):
        return ''
    if isinstance(val, int):
        return str(val)
    if isinstance(val, float) and val.is_integer():
        return str(int(val))
    s = str(val).strip()
    if s.endswith('.0') and s[:-2].isdigit():
        return s[:-2]
    return s


def _normalize_date(val) -> str:
    """Convert any date-like value to YYYY-MM-DD string."""
    if pd.isna(val) if not isinstance(val, str) else False:
        return ''
    if hasattr(val, 'strftime'):
        return val.strftime('%Y-%m-%d')
    s = str(val).strip()
    # Handle "2026-01-30 00:00:00" style
    if ' ' in s:
        s = s.split(' ')[0]
    # Handle compact integer style: 20251201 → 2025-12-01
    if len(s) == 8 and s.isdigit():
        s = f'{s[:4]}-{s[4:6]}-{s[6:]}'
    return s


def _derive_run_date_from_identifier(identifier: str) -> str:
    normalized = _normalize_identifier(identifier)
    prefix = normalized[:8]
    if len(prefix) == 8 and prefix.isdigit():
        return _normalize_date(prefix)
    return ''


def parse_wire_wear_sheet(df: pd.DataFrame) -> List[WireWearRecord]:
    """Parse Wire Wear sheet into WireWearRecord list."""
    records = []
    col_run_date = _find_column(df, 'Run Date', 'RUN DATE', 'run_date')
    col_id = _find_column(df, 'ID')
    col_tension_length = _find_column(df, 'Tension Length', 'tension_length')
    col_from_m = _find_column(df, 'FromM', 'From')
    col_to_m = _find_column(df, 'ToM', 'To')
    col_max_value = _find_column(df, 'MaxValue', 'Max Value', 'max_value', 'maxvalue')
    col_max_location = _find_column(df, 'MaxLocation', 'Max Location', 'max_location', 'maxlocation')
    col_level = _find_column(df, 'Level', 'level')
    col_action = _find_column(df, 'ACTION', 'Action', 'action')

    def _float_or_zero(value) -> float:
        if value is None or (not isinstance(value, str) and pd.isna(value)):
            return 0.0
        try:
            return float(str(value).strip().replace(',', ''))
        except (TypeError, ValueError):
            return 0.0

    for _, row in df.iterrows():
        exception_id = _normalize_identifier(_get_val(row, col_id))
        action_raw = _get_val(row, col_action)
        action = None if action_raw is None or pd.isna(action_raw) else str(action_raw).strip() or None
        run_date = _normalize_date(_get_val(row, col_run_date))
        if not run_date:
            run_date = _derive_run_date_from_identifier(exception_id)

        records.append(WireWearRecord(
            run_date=run_date,
            exception_id=exception_id,
            tension_length=str(_get_val(row, col_tension_length) or '').strip(),
            from_m=_float_or_zero(_get_val(row, col_from_m)),
            to_m=_float_or_zero(_get_val(row, col_to_m)),
            max_value=_float_or_zero(_get_val(row, col_max_value)),
            max_location=_float_or_zero(_get_val(row, col_max_location)),
            level=str(_get_val(row, col_level) or '').strip(),
            action=action,
        ))
    return records


def parse_chart_data_sheet(df: pd.DataFrame, fallback_task_run_date: str = '') -> List[ChartDataRecord]:
    """Parse ChartData sheet into ChartDataRecord list.

    Supports both:
    - current format with an explicit ``wear_min`` column
    - legacy format with per-channel ``wear1``..``wear4`` columns, from which
      ``wear_min`` is derived as the minimum non-null channel value
    """
    records = []
    col_task_run_date = _find_column(df, 'task_run_date', 'task run date', 'RUN DATE', 'Run Date')
    col_line = _find_column(df, 'line', 'Line')
    col_track = _find_column(df, 'track', 'Track')
    col_section = _find_column(df, 'Section', 'section')
    col_task_no = _find_column(df, 'task_no', 'Task No')
    col_station_start = _find_column(df, 'station_start', 'St. Start')
    col_station_end = _find_column(df, 'station_end', 'St. End')
    col_tension_length = _find_column(df, 'Tension Length', 'tension_length')
    col_chainage = _find_column(df, 'Chainage', 'chainage')
    col_track_type = _find_column(df, 'Track Type', 'track_type')
    col_overlap = _find_column(df, 'Overlap', 'overlap')
    wear_channel_columns = [
        column_name for column_name in ('wear1', 'wear2', 'wear3', 'wear4') if column_name in df.columns
    ]

    for _, row in df.iterrows():
        wear_min_raw = row.get('wear_min', None)
        if wear_min_raw is None or (not isinstance(wear_min_raw, str) and pd.isna(wear_min_raw)):
            channel_values = []
            for column_name in wear_channel_columns:
                channel_value = row.get(column_name, None)
                if channel_value is None or (not isinstance(channel_value, str) and pd.isna(channel_value)):
                    continue
                channel_values.append(float(channel_value))
            wear_min_raw = min(channel_values) if channel_values else None

        if wear_min_raw is None or (not isinstance(wear_min_raw, str) and pd.isna(wear_min_raw)):
            continue

        overlap_raw = _get_val(row, col_overlap)
        overlap = None if (not isinstance(overlap_raw, str) and pd.isna(overlap_raw)) else (None if overlap_raw == '' else str(overlap_raw))
        line_raw = _get_val(row, col_line)
        track_raw = _get_val(row, col_track)
        section_raw = _get_val(row, col_section)
        task_run_date = _normalize_date(_get_val(row, col_task_run_date))
        if not task_run_date:
            task_run_date = fallback_task_run_date

        def _str_or_empty(val) -> str:
            if val is None:
                return ''
            if not isinstance(val, str) and pd.isna(val):
                return ''
            return str(val).strip()

        records.append(ChartDataRecord(
            task_run_date=task_run_date,
            line=None if (line_raw is None or (not isinstance(line_raw, str) and pd.isna(line_raw))) else str(line_raw),
            track=None if (track_raw is None or (not isinstance(track_raw, str) and pd.isna(track_raw))) else str(track_raw),
            section=None if (section_raw is None or (not isinstance(section_raw, str) and pd.isna(section_raw))) else str(section_raw),
            task_no=_str_or_empty(_get_val(row, col_task_no)),
            station_start=_str_or_empty(_get_val(row, col_station_start)),
            station_end=_str_or_empty(_get_val(row, col_station_end)),
            tension_length=str(_get_val(row, col_tension_length) or '').strip(),
            chainage=float(_get_val(row, col_chainage) or 0),
            wear_min=float(wear_min_raw),
            track_type=str(_get_val(row, col_track_type) or '').strip(),
            overlap=overlap,
        ))
    return records


def parse_stagger_chart_data_sheet(df: pd.DataFrame) -> list[dict]:
    """Parse stagger ChartData rows into chainage plus height/stagger channels.

    Supports both:
    - legacy stagger workbook headers: WHGT1..4 / STG1..4
    - Exception Report ChartData headers: height1..4 / stagger1..4
    """
    columns = {str(column).strip().lower(): column for column in df.columns}
    chainage_col = columns.get('chainage')
    if chainage_col is None:
        raise KeyError('Chainage')

    def _resolve_channel_columns(*prefixes: str) -> list[str]:
        for prefix in prefixes:
            resolved = [columns.get(f'{prefix}{index}'.lower()) for index in range(1, 5)]
            if all(resolved):
                return [str(column) for column in resolved]
        raise KeyError(f'{prefixes[0]}1')

    height_columns = _resolve_channel_columns('WHGT', 'height')
    stagger_columns = _resolve_channel_columns('STG', 'stagger')

    def _numeric_values(row: pd.Series, column_names: list[str]) -> list[float]:
        values: list[float] = []
        indexed_values: list[float | None] = []
        for column_name in column_names:
            value = row.get(column_name)
            if pd.isna(value):
                indexed_values.append(None)
                continue
            numeric = float(value)
            values.append(numeric)
            indexed_values.append(numeric)
        return values, indexed_values

    rows: list[dict] = []
    for _, row in df.iterrows():
        chainage_value = row.get(chainage_col)
        if pd.isna(chainage_value):
            continue

        heights, height_channels = _numeric_values(row, height_columns)
        staggers, stagger_channels = _numeric_values(row, stagger_columns)
        if not heights or not staggers:
            continue

        rows.append(
            {
                'chainage': float(chainage_value),
                'heights': heights,
                'staggers': staggers,
                'height_channels': height_channels,
                'stagger_channels': stagger_channels,
            }
        )
    return rows


def parse_exception_report(file_bytes: bytes) -> Tuple[List[WireWearRecord], List[ChartDataRecord]]:
    """Parse full Exception Report Excel, return (wire_wear_records, chart_data_records)."""
    try:
        return _parse_exception_report_streaming(file_bytes)
    except Exception as exc:
        logger.info("Streaming parser failed; falling back to pandas parser: %s", exc)
        xl = pd.ExcelFile(io.BytesIO(file_bytes))
        wire_wear = parse_wire_wear_sheet(xl.parse('Wire Wear'))
        fallback_task_run_date = next((record.run_date for record in wire_wear if record.run_date), '')
        chart_data = parse_chart_data_sheet(
            xl.parse('ChartData'),
            fallback_task_run_date=fallback_task_run_date,
        )
        return wire_wear, chart_data


def _parse_exception_report_streaming(file_bytes: bytes) -> Tuple[List[WireWearRecord], List[ChartDataRecord]]:
    workbook = load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
    try:
        if 'Wire Wear' not in workbook.sheetnames or 'ChartData' not in workbook.sheetnames:
            raise KeyError('Wire Wear or ChartData')

        wire_rows = _sheet_to_records(workbook['Wire Wear'])
        wire_wear = parse_wire_wear_sheet(pd.DataFrame(wire_rows))
        fallback_task_run_date = next((record.run_date for record in wire_wear if record.run_date), '')
        chart_data = _parse_chart_data_sheet_streaming(
            workbook['ChartData'],
            fallback_task_run_date=fallback_task_run_date,
        )
        return wire_wear, chart_data
    finally:
        workbook.close()


def _sheet_to_records(sheet) -> list[dict]:
    rows = sheet.iter_rows(values_only=True)
    headers = next(rows, None)
    if headers is None:
        return []
    header_names = [str(header).strip() if header is not None else '' for header in headers]
    records = []
    for row in rows:
        if row is None or not any(value is not None for value in row):
            continue
        records.append({
            header: row[index] if index < len(row) else None
            for index, header in enumerate(header_names)
            if header
        })
    return records


def _parse_chart_data_sheet_streaming(sheet, fallback_task_run_date: str = '') -> List[ChartDataRecord]:
    rows = sheet.iter_rows(values_only=True)
    headers = next(rows, None)
    if headers is None:
        return []

    columns = {
        str(column).strip().lower(): index
        for index, column in enumerate(headers)
        if column is not None and str(column).strip()
    }

    def _find_index(*names: str) -> int | None:
        for name in names:
            index = columns.get(name.lower())
            if index is not None:
                return index
        return None

    col_task_run_date = _find_index('task_run_date', 'task run date', 'RUN DATE', 'Run Date')
    col_line = _find_index('line', 'Line')
    col_track = _find_index('track', 'Track')
    col_section = _find_index('Section', 'section')
    col_task_no = _find_index('task_no', 'Task No')
    col_station_start = _find_index('station_start', 'St. Start')
    col_station_end = _find_index('station_end', 'St. End')
    col_tension_length = _find_index('Tension Length', 'tension_length')
    col_chainage = _find_index('Chainage', 'chainage')
    col_track_type = _find_index('Track Type', 'track_type')
    col_overlap = _find_index('Overlap', 'overlap')
    col_wear_min = _find_index('wear_min')
    wear_channel_indexes = [
        index for column_name in ('wear1', 'wear2', 'wear3', 'wear4')
        if (index := columns.get(column_name)) is not None
    ]

    if col_chainage is None:
        raise KeyError('Chainage')

    def _row_value(row: tuple, index: int | None):
        if index is None or index >= len(row):
            return None
        value = row[index]
        return None if value is None else value

    def _str_or_empty(value) -> str:
        if value is None:
            return ''
        return str(value).strip()

    def _optional_str(value) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text if text else None

    records: List[ChartDataRecord] = []
    for row in rows:
        wear_min_raw = _row_value(row, col_wear_min)
        if wear_min_raw is None:
            channel_values = [
                float(value)
                for index in wear_channel_indexes
                if (value := _row_value(row, index)) is not None
            ]
            wear_min_raw = min(channel_values) if channel_values else None

        chainage_raw = _row_value(row, col_chainage)
        if wear_min_raw is None or chainage_raw is None:
            continue

        task_run_date = _normalize_date(_row_value(row, col_task_run_date)) or fallback_task_run_date
        overlap = _optional_str(_row_value(row, col_overlap))
        records.append(ChartDataRecord(
            task_run_date=task_run_date,
            line=_optional_str(_row_value(row, col_line)),
            track=_optional_str(_row_value(row, col_track)),
            section=_optional_str(_row_value(row, col_section)),
            task_no=_str_or_empty(_row_value(row, col_task_no)),
            station_start=_str_or_empty(_row_value(row, col_station_start)),
            station_end=_str_or_empty(_row_value(row, col_station_end)),
            tension_length=_str_or_empty(_row_value(row, col_tension_length)),
            chainage=float(chainage_raw),
            wear_min=float(wear_min_raw),
            track_type=_str_or_empty(_row_value(row, col_track_type)),
            overlap=overlap,
        ))
    return records


def _find_column(df: pd.DataFrame, *names: str) -> str | None:
    """Case-insensitive column lookup. Returns the first matching column name or None."""
    cols = {str(c).strip().lower(): c for c in df.columns}
    for name in names:
        if name.lower() in cols:
            return cols[name.lower()]
    return None


def _get_val(row: pd.Series, col: str) -> any:
    """Get value from row by column name, returning None for NaN."""
    if col is None:
        return None
    return row.get(col, None)


def parse_repeated_summary_sheet(df: pd.DataFrame) -> List[RepeatedSummaryRecord]:
    """Parse Summary sheet of n_Repeated Exception Report.
    Filters rows where Exception Type = 'Wire Wear' and Level = 'L2'.
    Column names are matched case-insensitively to handle varied formats.
    """
    records = []
    # Case-insensitive column mapping
    col_id = _find_column(df, 'ID')
    col_from = _find_column(df, 'FromM', 'From')
    col_to = _find_column(df, 'ToM', 'To')
    col_run_date = _find_column(df, 'RUN DATE', 'Run Date', 'Run_Date', 'run_date')
    col_max_val = _find_column(df, 'MaxValue', 'Max Value', 'max_value', 'maxvalue')
    col_max_loc = _find_column(df, 'MaxLocation', 'Max Location', 'max_location', 'maxlocation')
    col_exc_type = _find_column(df, 'Exception Type', 'Exception_Type', 'exception_type')
    col_level = _find_column(df, 'Level', 'level')

    if col_id is None or col_exc_type is None:
        logger.warning(
            f"parse_repeated_summary_sheet: essential columns not found. "
            f"Available columns: {df.columns.tolist()}"
        )
        return records

    for _, row in df.iterrows():
        exc_type = str(_get_val(row, col_exc_type) or '').strip()
        level = str(_get_val(row, col_level) or '').strip()
        if exc_type != 'Wire Wear' or level != 'L2':
            continue

        def _float(val) -> float:
            if val is None or (isinstance(val, float) and pd.isna(val)):
                return 0.0
            try:
                s = str(val).strip().replace(',', '')
                return float(s)
            except (ValueError, TypeError):
                return 0.0

        records.append(RepeatedSummaryRecord(
            exception_id=_normalize_identifier(_get_val(row, col_id)),
            from_m=_float(_get_val(row, col_from)),
            to_m=_float(_get_val(row, col_to)),
            run_date=_normalize_date(_get_val(row, col_run_date)),
            max_value=_float(_get_val(row, col_max_val)),
            max_location=_float(_get_val(row, col_max_loc)),
            exception_type=exc_type,
            level=level,
        ))
    return records


def load_repeated_summary_sheet(file_bytes: bytes) -> pd.DataFrame:
    """Load the Summary-like sheet from an n_Repeated workbook with resilient header detection."""
    xl = pd.ExcelFile(io.BytesIO(file_bytes))
    sheet_names = xl.sheet_names

    target = 'Summary' if 'Summary' in sheet_names else sheet_names[0]
    df = xl.parse(target)
    if _find_column(df, 'ID') is None:
        df = xl.parse(target, header=1)
    if _find_column(df, 'ID') is None:
        for sheet in sheet_names:
            df = xl.parse(sheet)
            if _find_column(df, 'ID') is not None:
                logger.info(f"parse_repeated_report: found ID column in sheet '{sheet}'")
                break
            df = xl.parse(sheet, header=1)
            if _find_column(df, 'ID') is not None:
                logger.info(f"parse_repeated_report: found ID column in sheet '{sheet}' with header=1")
                break
        else:
            logger.warning(
                f"parse_repeated_report: no sheet found with 'ID' column. "
                f"Available sheets: {sheet_names}"
            )
    return df


def parse_repeated_report(file_bytes: bytes) -> List[RepeatedSummaryRecord]:
    """Parse n_Repeated Exception Report Excel, return Wire Wear L2 rows from Summary sheet."""
    return parse_repeated_summary_sheet(load_repeated_summary_sheet(file_bytes))
