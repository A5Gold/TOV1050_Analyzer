"""Calculation API endpoints."""
import io
import inspect
import json
import logging
import math as _math
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import asdict, replace
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from openpyxl.utils.exceptions import InvalidFileException

from app.core.calculation.excel_parser import (
    ChartDataRecord,
    WireWearRecord,
    load_repeated_summary_sheet,
    parse_exception_report,
    parse_repeated_report,
    parse_stagger_chart_data_sheet,
)
from app.core.calculation.stagger_metadata import load_stagger_metadata
from app.core.calculation.stagger_selector import select_stagger_candidates
from app.core.calculation.stagger_service import compute_stagger_result_for_record
from app.core.calculation.trend_analyzer import analyze_trend
from app.core.calculation.wear_calculator import calculate_average_wear
from app.core.calculation.wear_cycle_aggregation import build_cycle_preview, preview_digest
from app.core.calculation.wear_cycle_metadata import (
    MetadataValidationError,
    SegmentDetectionError,
    build_measurement_resolution_index,
    detect_segments,
    load_line_metadata,
    normalize_cycle_date,
    normalize_line_group,
    normalize_section,
    normalize_tension_length,
    resolve_measurement_tension_length,
    section_for_segments,
)
from app.core.calculation.wear_cycle_repository import current_data_version
from app.core.calculation.wear_cycle_types import ParsedWearSource, RawWearMeasurement
from app.core.calculation.wear_tl_scope import (
    TensionLengthScope,
    classify_tension_length_scope,
)
from app.core.config import get_config_dir
from app.core.database import get_database
from app.core.metadata import MetadataManager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/calculation")

MAX_WEAR_UPLOAD_FILES = 24
MAX_WEAR_FILE_BYTES = 32 * 1024 * 1024
MAX_WEAR_TOTAL_BYTES = 128 * 1024 * 1024
MAX_WEAR_ZIP_UNCOMPRESSED_BYTES = 512 * 1024 * 1024
MAX_WEAR_ZIP_COMPRESSION_RATIO = 100.0
MAX_WEAR_ARCHIVE_MEMBERS = 2048
MAX_WEAR_WORKBOOK_XML_BYTES = 4 * 1024 * 1024

_EXPECTED_WEAR_FORMAT_ERRORS = (
    zipfile.BadZipFile,
    InvalidFileException,
    pd.errors.EmptyDataError,
    pd.errors.ParserError,
    KeyError,
)


def _sanitize(obj):
    """Recursively replace float NaN/Inf with None for JSON safety."""
    if isinstance(obj, float) and (_math.isnan(obj) or _math.isinf(obj)):
        return None
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    return obj


def _metadata_manager(line_group: str) -> MetadataManager:
    filename = "EAL metadata.xlsx" if line_group == "EAL" else "TML metadata.xlsx"
    return MetadataManager(config_path=get_config_dir() / filename)


def _parse_accepted_conflict_ids(raw_value: str) -> set[str]:
    try:
        values = json.loads(raw_value or "[]")
    except json.JSONDecodeError as exc:
        raise MetadataValidationError("accepted_conflict_ids must be a JSON array") from exc
    if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
        raise MetadataValidationError("accepted_conflict_ids must be a JSON array of strings")
    return set(values)


def _validate_wear_zip_declarations(filename: str, content: bytes) -> None:
    stream = io.BytesIO(content)
    if not zipfile.is_zipfile(stream):
        logger.warning("Wear upload %s is not an OOXML ZIP workbook", filename)
        raise MetadataValidationError(f"Invalid wear upload: {filename}")
    stream.seek(0)
    with zipfile.ZipFile(stream) as archive:
        members = archive.infolist()
    if len(members) > MAX_WEAR_ARCHIVE_MEMBERS:
        raise HTTPException(
            status_code=413,
            detail=f"Wear upload {filename} exceeds the archive member limit.",
        )
    uncompressed = sum(member.file_size for member in members)
    compressed = sum(member.compress_size for member in members)
    if uncompressed > MAX_WEAR_ZIP_UNCOMPRESSED_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Wear upload {filename} exceeds the uncompressed size limit.",
        )
    for member in members:
        if member.file_size == 0 and member.compress_size == 0:
            continue
        member_ratio = member.file_size / max(member.compress_size, 1)
        if member_ratio > MAX_WEAR_ZIP_COMPRESSION_RATIO:
            raise HTTPException(
                status_code=413,
                detail=f"Wear upload {filename} exceeds the compression ratio limit.",
            )
    ratio = uncompressed / max(compressed, 1)
    if ratio > MAX_WEAR_ZIP_COMPRESSION_RATIO:
        raise HTTPException(
            status_code=413,
            detail=f"Wear upload {filename} exceeds the compression ratio limit.",
        )
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            workbook_info = archive.getinfo("xl/workbook.xml")
            if workbook_info.file_size > MAX_WEAR_WORKBOOK_XML_BYTES:
                raise MetadataValidationError("workbook metadata is too large")
            workbook_xml = archive.read(workbook_info)
        workbook_root = ET.fromstring(workbook_xml)
    except (KeyError, ET.ParseError, zipfile.BadZipFile, MetadataValidationError) as exc:
        logger.warning("Invalid workbook structure for %s", filename, exc_info=exc)
        raise MetadataValidationError(f"Invalid wear upload: {filename}") from exc

    workbook_namespace = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    sheet_names = {
        sheet.attrib.get("name")
        for sheet in workbook_root.findall(f".//{{{workbook_namespace}}}sheet")
    }
    if not {"Wire Wear", "ChartData"}.issubset(sheet_names):
        logger.warning("Wear upload %s is missing required worksheets", filename)
        raise MetadataValidationError(f"Invalid wear upload: {filename}")


async def _read_complete_cycle_uploads(
    files: List[UploadFile],
) -> list[tuple[str, bytes]]:
    if len(files) > MAX_WEAR_UPLOAD_FILES:
        raise HTTPException(status_code=413, detail="Too many wear upload files.")

    total_bytes = 0
    payloads = []
    for upload in files:
        filename = upload.filename or "upload.xlsx"
        remaining_total = MAX_WEAR_TOTAL_BYTES - total_bytes
        read_limit = min(MAX_WEAR_FILE_BYTES, remaining_total) + 1
        content = await upload.read(read_limit)
        if len(content) > MAX_WEAR_FILE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"Wear upload {filename} exceeds the file size limit.",
            )
        if len(content) > remaining_total:
            raise HTTPException(
                status_code=413,
                detail="Wear uploads exceed the total compressed size limit.",
            )
        total_bytes += len(content)
        payloads.append((filename, content))
    return payloads


def _parse_complete_cycle_source(
    filename: str,
    content: bytes,
    line_group: str,
    metadata=(),
) -> ParsedWearSource:
    try:
        _wire_wear, chart_data = parse_exception_report(content)
    except _EXPECTED_WEAR_FORMAT_ERRORS as exc:
        logger.warning("Invalid wear upload %s", filename, exc_info=exc)
        raise MetadataValidationError(f"Invalid wear upload: {filename}") from exc

    source_fields = [
        value
        for record in chart_data
        for value in (
            record.line,
            record.track,
            record.section,
            record.task_no,
            record.station_start,
            record.station_end,
        )
    ]
    segments = detect_segments(line_group, filename, source_fields)
    source_section = section_for_segments(line_group, segments)
    measurements = []
    source_chainages = []
    for record in chart_data:
        track = str(record.track or "").strip().upper()
        raw_section = str(record.section or "").strip()
        raw_tension_length = str(record.tension_length or "").strip()
        raw_chainage = record.chainage
        try:
            if track not in ("UP", "DN"):
                raise MetadataValidationError("measurement track must be UP or DN")
            acquisition_date = normalize_cycle_date(record.task_run_date)
            chainage = Decimal(str(raw_chainage))
            wear_min = float(record.wear_min)
            source_chainages.append(chainage)
            measurement_section = (
                normalize_section(line_group, raw_section) if raw_section else source_section
            )
            if measurement_section != source_section:
                raise MetadataValidationError(
                    f"measurement section {measurement_section} conflicts with "
                    f"source segments {list(segments)} ({source_section})"
                )
            if not raw_tension_length:
                continue
            tension_length = resolve_measurement_tension_length(
                line_group,
                track,
                chainage,
                metadata,
                raw_tension_length,
                section=measurement_section,
            )
            scope = classify_tension_length_scope(line_group, tension_length)
            if scope is TensionLengthScope.SIDING:
                continue
            if scope is TensionLengthScope.UNKNOWN:
                raise MetadataValidationError(
                    f"{line_group} has unknown tension length {tension_length!r} "
                    f"from source signature {raw_tension_length!r}"
                )
            measurement = RawWearMeasurement(
                acquisition_date=acquisition_date,
                line_group=line_group,
                track=track,
                task_no=str(record.task_no or ""),
                station_start=str(record.station_start or ""),
                station_end=str(record.station_end or ""),
                chainage=chainage,
                wear_min=wear_min,
                tension_length=tension_length,
            )
        except (MetadataValidationError, InvalidOperation, OverflowError, TypeError, ValueError) as exc:
            raise MetadataValidationError(
                f"Invalid wear measurement in {filename}: TL {raw_tension_length or '<blank>'}, "
                f"section {raw_section or '<blank>'}, track {track or '<blank>'}, "
                f"chainage {raw_chainage}: {exc}"
            ) from exc
        measurements.append(measurement)
    if not measurements:
        raise MetadataValidationError(f"No wear measurements found in {filename}")
    return ParsedWearSource(
        filename,
        ",".join(segments),
        min(source_chainages),
        max(source_chainages),
        tuple(measurements),
    )


def _build_complete_cycle_preview(
    *,
    file_payloads: list[tuple[str, bytes]],
    line_group: str,
    cycle_date: str | None,
    accepted_conflict_ids: set[str],
):
    line = normalize_line_group(line_group)
    if cycle_date is not None:
        normalize_cycle_date(cycle_date)
    for filename, content in file_payloads:
        _validate_wear_zip_declarations(filename, content)
    metadata = load_line_metadata(_metadata_manager(line), line)
    resolution_index = build_measurement_resolution_index(line, metadata)
    sources = []
    for filename, content in file_payloads:
        sources.append(
            _parse_complete_cycle_source(
                filename,
                content,
                line,
                metadata=resolution_index,
            )
        )
    return build_cycle_preview(
        line_group=line,
        requested_cycle_date=cycle_date,
        sources=sources,
        metadata=metadata,
        accepted_conflict_ids=accepted_conflict_ids,
    )


def _complete_cycle_response(preview, expected_data_version: int) -> dict:
    records = []
    for record in preview.records:
        row = asdict(record)
        key = row.pop("key")
        records.append({**key, **row, "interval_count": len(record.intervals)})
    return _sanitize(
        {
            "line_group": preview.line_group,
            "cycle_date": preview.cycle_date,
            "records": records,
            "segments": [asdict(item) for item in preview.segments],
            "conflicts": [asdict(item) for item in preview.conflicts],
            "unresolved": list(preview.unresolved),
            "blocking_reasons": list(preview.blocking_reasons),
            "can_save": preview.can_save,
            "preview_digest": preview_digest(preview),
            "expected_data_version": expected_data_version,
        }
    )


def _infer_stagger_line(summary_df: pd.DataFrame, filename: str, candidate_records: List[object]) -> str:
    allowed_lines = {"EAL", "TML"}

    for record in candidate_records:
        candidate = str(getattr(record, "line", "") or "").strip().upper()
        if candidate in allowed_lines:
            return candidate

    columns = {str(column).strip().lower(): column for column in summary_df.columns}
    for logical_name in ("line", "class"):
        actual_column = columns.get(logical_name)
        if actual_column is None:
            continue
        values = {
            str(value).strip().upper()
            for value in summary_df[actual_column].dropna().tolist()
            if str(value).strip()
        }
        matching = values & allowed_lines
        if len(matching) == 1:
            return next(iter(matching))

    upper_filename = str(filename or "").upper()
    for candidate in allowed_lines:
        if f"_{candidate}_" in upper_filename or upper_filename.startswith(f"{candidate}_"):
            return candidate

    return ""


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.post("/wear")
async def upload_wear(
    files: List[UploadFile] = File(...),
    line_group: Optional[str] = Form(default=None),
    cycle_date: Optional[str] = Form(default=None),
    accepted_conflict_ids: str = Form(default="[]"),
    line: str = Form(default=""),
    track: str = Form(default=""),
    section: str = Form(default="Mainline"),
):
    """Multiple files (same Line, different Section/Track/Date) -> average wear results."""
    if line_group is not None:
        try:
            file_payloads = await _read_complete_cycle_uploads(files)
            preview = _build_complete_cycle_preview(
                file_payloads=file_payloads,
                line_group=line_group,
                cycle_date=cycle_date,
                accepted_conflict_ids=_parse_accepted_conflict_ids(accepted_conflict_ids),
            )
            if inspect.isawaitable(preview):
                preview = await preview
            if any(
                reason in preview.blocking_reasons
                for reason in ("cycle_date_invalid", "unknown_segment", "unresolved_tension_length")
            ):
                raise HTTPException(
                    status_code=422,
                    detail={
                        "blocking_reasons": list(preview.blocking_reasons),
                        "unresolved": list(preview.unresolved),
                    },
                )
            db = get_database()
            with db.get_connection() as conn:
                data_version = current_data_version(conn)
            return _complete_cycle_response(preview, data_version)
        except HTTPException:
            raise
        except (MetadataValidationError, SegmentDetectionError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    all_chart_data: List[ChartDataRecord] = []

    for f in files:
        try:
            file_bytes = await f.read()
            _, chart_data = parse_exception_report(file_bytes)
            all_chart_data.extend(chart_data)
        except Exception as exc:
            logger.error("Failed to parse %s: %s", f.filename, exc)
            raise HTTPException(status_code=422, detail=f"Failed to parse {f.filename}: {exc}")

    def record_identity(rec: ChartDataRecord) -> tuple:
        rec_line = (line or rec.line or "").strip().upper()
        rec_track = (rec.track or track or "").strip()
        rec_section = (rec.section or section or "Mainline").strip()
        return (rec_line, rec_track, rec_section, rec.chainage)

    chainage_date_map: dict = {}
    for rec in all_chart_data:
        key = record_identity(rec)
        existing = chainage_date_map.get(key)
        if existing is None or rec.task_run_date > existing:
            chainage_date_map[key] = rec.task_run_date

    deduped_chart_data = [
        rec for rec in all_chart_data if rec.task_run_date == chainage_date_map[record_identity(rec)]
    ]

    latest_date = max(chainage_date_map.values()) if chainage_date_map else None
    grouped_chart_data: Dict[tuple[str, str, str], List[ChartDataRecord]] = {}
    for rec in deduped_chart_data:
        rec_line, rec_track, rec_section, _chainage = record_identity(rec)
        grouped_chart_data.setdefault((rec_line, rec_track, rec_section), []).append(rec)

    wear_results = []
    for (group_line, group_track, group_section), records in grouped_chart_data.items():
        tl_lookup = None
        if group_line and group_track:
            try:
                config_dir = get_config_dir()
                filename = "EAL metadata.xlsx" if group_line == "EAL" else "TML metadata.xlsx"
                mgr = MetadataManager(config_path=config_dir / filename)
                tl_lookup = mgr.get_tension_length_lookup(group_line, group_track, group_section)
            except Exception as exc:
                logger.warning(
                    "Could not build tl_lookup for %s/%s/%s: %s",
                    group_line,
                    group_track,
                    group_section,
                    exc,
                )
        wear_results.extend(calculate_average_wear(records, tl_lookup=tl_lookup))

    return {
        "date": latest_date or "",
        "wear_results": [asdict(r) for r in wear_results],
    }


@router.post("/upload")
async def upload_combined(
    files: List[UploadFile] = File(...),
    line: str = Form(default="EAL"),
):
    """Combined endpoint: returns both wear_results and trend_results."""
    all_wire_wear: List[WireWearRecord] = []
    chart_data_by_date: Dict[str, List[ChartDataRecord]] = {}

    for f in files:
        try:
            file_bytes = await f.read()
            wire_wear, chart_data = parse_exception_report(file_bytes)
            all_wire_wear.extend(wire_wear)
            for rec in chart_data:
                chart_data_by_date.setdefault(rec.task_run_date, []).append(rec)
        except Exception as exc:
            logger.error("Failed to parse %s: %s", f.filename, exc)
            raise HTTPException(status_code=422, detail=f"Failed to parse {f.filename}: {exc}")

    latest_date = max(chart_data_by_date.keys()) if chart_data_by_date else None
    latest_chart_data = chart_data_by_date.get(latest_date, []) if latest_date else []
    wear_results = calculate_average_wear(latest_chart_data)

    try:
        trend_results = analyze_trend(all_wire_wear, chart_data_by_date, line=line)
    except Exception as exc:
        logger.error("Trend analysis failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Trend analysis failed: {exc}")

    return _sanitize(
        {
            "wear_results": [asdict(r) for r in wear_results],
            "trend_results": [asdict(r) for r in trend_results],
        }
    )


@router.post("/trend")
async def upload_trend(
    files: List[UploadFile] = File(...),
    line: str = Form(default="EAL"),
    repeated_file: Optional[UploadFile] = File(None),
):
    """Multiple files across dates -> L2 trend analysis."""
    all_wire_wear: List[WireWearRecord] = []
    chart_data_by_date: Dict[str, List[ChartDataRecord]] = {}

    for f in files:
        try:
            file_bytes = await f.read()
            wire_wear, chart_data = parse_exception_report(file_bytes)
            all_wire_wear.extend(wire_wear)
            for rec in chart_data:
                chart_data_by_date.setdefault(rec.task_run_date, []).append(rec)
        except Exception as exc:
            logger.error("Failed to parse %s: %s", f.filename, exc)
            raise HTTPException(status_code=422, detail=f"Failed to parse {f.filename}: {exc}")

    repeated_records = None
    if repeated_file is not None:
        try:
            repeated_bytes = await repeated_file.read()
            repeated_records = parse_repeated_report(repeated_bytes)
        except Exception as exc:
            logger.error("Failed to parse repeated file %s: %s", repeated_file.filename, exc)
            raise HTTPException(
                status_code=422,
                detail=f"Failed to parse repeated file {repeated_file.filename}: {exc}",
            )

    try:
        trend_results = analyze_trend(
            wire_wear_records=all_wire_wear,
            chart_data_by_date=chart_data_by_date,
            line=line,
            repeated_records=repeated_records,
        )
    except Exception as exc:
        logger.error("Trend analysis failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Trend analysis failed: {exc}")

    return _sanitize(
        {
            "trend_results": [asdict(r) for r in trend_results],
        }
    )


@router.post("/stagger")
async def upload_stagger(
    file: UploadFile = File(...),
    repeated_file: Optional[UploadFile] = File(None),
):
    try:
        file_bytes = await file.read()
        workbook = pd.read_excel(
            io.BytesIO(file_bytes),
            sheet_name=["Summary", "ChartData"],
        )
        summary_df = workbook["Summary"]
        chart_rows = parse_stagger_chart_data_sheet(workbook["ChartData"])

        repeated_summary_df = None
        if repeated_file is not None:
            repeated_bytes = await repeated_file.read()
            repeated_summary_df = load_repeated_summary_sheet(repeated_bytes)

        fallback_records = select_stagger_candidates(summary_df=summary_df, repeated_summary_df=None)
        selected_records = select_stagger_candidates(
            summary_df=summary_df,
            repeated_summary_df=repeated_summary_df,
        )
        line = _infer_stagger_line(
            summary_df=summary_df,
            filename=file.filename or "",
            candidate_records=selected_records or fallback_records,
        )
        if line:
            fallback_records = [replace(record, line=line) for record in fallback_records]
            selected_records = [replace(record, line=line) for record in selected_records]
        metadata = load_stagger_metadata(line=line)
    except Exception as exc:
        logger.error("Failed to parse stagger workbook %s: %s", file.filename, exc)
        raise HTTPException(status_code=422, detail=f"Failed to parse stagger workbook {file.filename}: {exc}")

    try:
        results = []
        traces = []
        warnings = []

        if repeated_file is None:
            case_type = "A"
            records_to_process = fallback_records
        else:
            case_type = "B"
            records_to_process = selected_records
            if repeated_summary_df is None:
                warnings.append(
                    "Case B requested, but the n_Repeated summary could not be loaded. No fallback to Case A was applied."
                )
            elif not selected_records:
                warnings.append(
                    "Case B requested, but no stagger IDs from the n_Repeated summary matched the Exception Report summary. No fallback to Case A was applied."
                )

        for record in records_to_process:
            summary, trace = compute_stagger_result_for_record(
                record=record,
                chart_rows=chart_rows,
                metadata=metadata,
                case_type=case_type,
            )
            results.append(asdict(summary))
            traces.append(trace)

        if not results:
            warnings.append("No stagger results yet.")
    except Exception as exc:
        logger.error("Stagger calculation failed for %s: %s", file.filename, exc)
        raise HTTPException(status_code=500, detail=f"Stagger calculation failed: {exc}")

    return _sanitize(
        {
            "results": results,
            "traces": traces,
            "warnings": warnings,
        }
    )
