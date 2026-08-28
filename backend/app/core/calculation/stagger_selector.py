from __future__ import annotations

import pandas as pd

from app.core.calculation.stagger_types import SelectedSummaryRecord


ALLOWED_LEVELS = {"L1", "L2"}
ALLOWED_TYPES = {"Stagger Left", "Stagger Right"}


def _normalize_track(value: object) -> str:
    raw = str(value or "").strip().lower()
    if raw in {"down", "dn"}:
        return "down"
    return "up"


def _normalize_id(value: object) -> str:
    if value is None:
        return ""
    if not isinstance(value, str) and pd.isna(value):
        return ""
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    text = str(value).strip()
    if text.endswith(".0") and text[:-2].isdigit():
        return text[:-2]
    return text


def _find_column(df: pd.DataFrame, *names: str) -> str | None:
    columns = {str(column).strip().lower(): column for column in df.columns}
    for name in names:
        match = columns.get(name.lower())
        if match is not None:
            return match
    return None


def _get_value(row: pd.Series, column: str | None, default: object = None) -> object:
    if column is None:
        return default
    value = row.get(column, default)
    if not isinstance(value, str) and pd.isna(value):
        return default
    return value


def _float_or_none(value: object) -> float | None:
    if value is None:
        return None
    if not isinstance(value, str) and pd.isna(value):
        return None
    try:
        return float(str(value).strip().replace(",", ""))
    except (TypeError, ValueError):
        return None


def select_stagger_candidates(
    summary_df: pd.DataFrame, repeated_summary_df: pd.DataFrame | None = None
) -> list[SelectedSummaryRecord]:
    repeated_by_id: dict[str, pd.Series] = {}
    source_df = summary_df.copy()
    if repeated_summary_df is not None:
        repeated_id_col = _find_column(repeated_summary_df, "ID")
        repeated_level_col = _find_column(repeated_summary_df, "Level", "level")
        repeated_type_col = _find_column(
            repeated_summary_df,
            "Exception Type",
            "Exception_Type",
            "exception_type",
        )
        if repeated_id_col is None:
            source_df = summary_df.iloc[0:0].copy()
        else:
            for _, row in repeated_summary_df.iterrows():
                repeated_id = _normalize_id(_get_value(row, repeated_id_col, ""))
                if not repeated_id:
                    continue
                if repeated_level_col is not None and str(_get_value(row, repeated_level_col, "")).strip() not in ALLOWED_LEVELS:
                    continue
                if repeated_type_col is not None and str(_get_value(row, repeated_type_col, "")).strip() not in ALLOWED_TYPES:
                    continue
                repeated_by_id[repeated_id] = row
        if repeated_by_id:
            source_id_col = _find_column(summary_df, "ID")
            if source_id_col is not None:
                source_df = summary_df[summary_df[source_id_col].map(_normalize_id).isin(repeated_by_id.keys())].copy()
            else:
                source_df = summary_df.iloc[0:0].copy()

    selected: list[SelectedSummaryRecord] = []
    repeated_max_location_col = _find_column(
        repeated_summary_df,
        "MaxLocation",
        "Max Location",
        "max_location",
    ) if repeated_summary_df is not None else None

    col_run_date = _find_column(summary_df, "Run Date", "RUN DATE", "run_date")
    col_line = _find_column(summary_df, "Line")
    col_track = _find_column(summary_df, "Track")
    col_section = _find_column(summary_df, "Section")
    col_task_no = _find_column(summary_df, "Task No", "task_no")
    col_station_start = _find_column(summary_df, "St. Start", "station_start")
    col_station_end = _find_column(summary_df, "St. End", "station_end")
    col_id = _find_column(summary_df, "ID")
    col_from_m = _find_column(summary_df, "FromM", "From")
    col_to_m = _find_column(summary_df, "ToM", "To")
    col_length = _find_column(summary_df, "Length")
    col_type = _find_column(summary_df, "Exception Type", "exception_type")
    col_max_value = _find_column(summary_df, "MaxValue", "Max Value", "max_value")
    col_max_location = _find_column(summary_df, "MaxLocation", "Max Location", "max_location")
    col_overlap = _find_column(summary_df, "Overlap")
    col_tension_length = _find_column(summary_df, "Tension Length", "tension_length")
    col_track_type = _find_column(summary_df, "Track Type", "track_type")
    col_level = _find_column(summary_df, "Level")
    col_landmark = _find_column(summary_df, "Landmark")
    col_class = _find_column(summary_df, "Class")
    col_threshold_value = _find_column(summary_df, "Threshold Value", "threshold_value")

    for _, row in source_df.iterrows():
        level = str(_get_value(row, col_level, "")).strip()
        exception_type = str(_get_value(row, col_type, "")).strip()
        if level not in ALLOWED_LEVELS or exception_type not in ALLOWED_TYPES:
            continue

        record_id = _normalize_id(_get_value(row, col_id, ""))
        max_location = _float_or_none(_get_value(row, col_max_location, 0.0)) or 0.0
        chi_source = "exception_report"
        if repeated_by_id and record_id in repeated_by_id:
            repeated_row = repeated_by_id[record_id]
            repeated_max_location = _float_or_none(_get_value(repeated_row, repeated_max_location_col))
            if repeated_max_location is not None:
                max_location = repeated_max_location
                chi_source = "n_repeated"

        selected.append(
            SelectedSummaryRecord(
                id=record_id,
                run_date=None if _get_value(row, col_run_date) is None else str(_get_value(row, col_run_date)),
                line="" if _get_value(row, col_line) is None else str(_get_value(row, col_line)),
                track=_normalize_track(_get_value(row, col_track)),
                section=None if _get_value(row, col_section) is None else str(_get_value(row, col_section)),
                task_no=None if _get_value(row, col_task_no) is None else str(_get_value(row, col_task_no)),
                station_start=None if _get_value(row, col_station_start) is None else str(_get_value(row, col_station_start)),
                station_end=None if _get_value(row, col_station_end) is None else str(_get_value(row, col_station_end)),
                from_m=_float_or_none(_get_value(row, col_from_m)),
                to_m=_float_or_none(_get_value(row, col_to_m)),
                length=_float_or_none(_get_value(row, col_length)),
                tension_length=None if _get_value(row, col_tension_length) is None else str(_get_value(row, col_tension_length)),
                overlap=None if _get_value(row, col_overlap) is None else str(_get_value(row, col_overlap)),
                track_type=None if _get_value(row, col_track_type) is None else str(_get_value(row, col_track_type)),
                level=level,
                landmark=None if _get_value(row, col_landmark) is None else str(_get_value(row, col_landmark)),
                asset_class=None if _get_value(row, col_class) is None else str(_get_value(row, col_class)),
                threshold_value=_float_or_none(_get_value(row, col_threshold_value)),
                exception_type=exception_type,
                max_value=_float_or_none(_get_value(row, col_max_value)),
                max_location=float(max_location),
                chi_source=chi_source,
            )
        )

    return selected
