"""Wear Calculator wire wear record endpoints."""
import inspect
import json
from hashlib import sha256
from datetime import date
from dataclasses import asdict, replace
from typing import Dict, List, Literal, Optional

from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel, Field

from app.core.calculation.wear_records import (
    WireWearRecordInput,
    WireWearSaveRequest,
    WireWearSaveResult,
    WireWearValidationError,
    build_wire_wear_sync_package,
    build_workbench_excel,
    build_workbench_summary,
    delete_wire_wear_record,
    import_wire_wear_sync_package,
    query_wire_wear_records,
    save_wire_wear_records,
    update_wire_wear_record,
)
from app.core.config import get_config_dir
from app.core.database import get_database
from app.core.metadata import MetadataManager
from app.core.calculation.wear_cycle_aggregation import preview_digest
from app.core.calculation.wear_cycle_analytics import build_dashboard, build_projection, build_remaining_life
from app.core.calculation.wear_cycle_io import (
    SyncPreviewMismatchError,
    SyncValidationError,
    apply_sync_import,
    build_excel_report,
    build_sync_package,
    preview_sync_import,
)
from app.core.calculation.wear_cycle_application import (
    BackupCreationError,
    ChangeSetOrigin,
    apply_change_set_with_backup,
)
from app.core.calculation.wear_historical_import import (
    HistoricalWorkbookError,
    StaleHistoricalPreviewError,
    discover_historical_workbook,
    preview_historical_workbook,
)
from app.core.calculation.wear_cycle_metadata import (
    MetadataResolutionError,
    MetadataValidationError,
    load_line_metadata,
    natural_key,
    normalize_cycle_date,
    normalize_line_identity,
    normalize_line_group,
    normalize_tension_length,
    resolve_canonical_tl,
)
from app.core.calculation.wear_cycle_repository import (
    AddOperation,
    ChangeOperationError,
    ChangeSet,
    DeleteCellOperation,
    DeleteRowOperation,
    DuplicateBusinessKeyError,
    EditOperation,
    IncompleteCycleError,
    StaleDataVersionError,
    StaleRecordError,
    WearCycleRepositoryError,
    build_workbench as build_cycle_workbench,
    current_data_version,
    list_committed_records,
    save_analysis_cycle,
)
from app.core.calculation.wear_cycle_types import BusinessKey
from app.core.calculation.wear_record_candidates import (
    WearRecordCandidate,
    classify_wear_record_candidates,
)
from app.api.endpoints.calculation import (
    _build_complete_cycle_preview,
    _parse_accepted_conflict_ids,
    _read_complete_cycle_uploads,
)

router = APIRouter(prefix="/calculation/wear-records")


def _load_cycle_metadata(line_group: str, line_class: str | None = None):
    line, normalized_class = normalize_line_identity(line_group, line_class)
    filename = "EAL metadata.xlsx" if line == "EAL" else "TML metadata.xlsx"
    manager = MetadataManager(config_path=get_config_dir() / filename)
    return load_line_metadata(manager, line, normalized_class)


def _load_identity_metadata(line_group: str, line_class: str):
    """Keep existing EAL/TML loader seams while adding explicit LMC context."""
    return (
        _load_cycle_metadata(line_group)
        if line_class == line_group
        else _load_cycle_metadata(line_group, line_class)
    )


def _cycle_metadata_fingerprints() -> dict[str, str]:
    config_dir = get_config_dir()
    return {
        line: sha256((config_dir / f"{line} metadata.xlsx").read_bytes()).hexdigest()
        for line in ("EAL", "TML")
        if (config_dir / f"{line} metadata.xlsx").exists()
    }


def _sync_metadata():
    return {
        (line, line_class): tuple(_load_identity_metadata(line, line_class))
        for line, line_class in (("EAL", "EAL"), ("EAL", "LMC"), ("TML", "TML"))
    }


def _historical_metadata():
    return tuple(
        interval
        for metadata in _sync_metadata().values()
        for interval in metadata
    )


async def _read_historical_workbook(file: UploadFile) -> bytes:
    filename = str(file.filename or "")
    if not filename.lower().endswith(".xlsx"):
        raise HistoricalWorkbookError("historical workbook must use the .xlsx format")
    workbook_bytes = await file.read()
    if not workbook_bytes:
        raise HistoricalWorkbookError("historical workbook is empty")
    return workbook_bytes


def _parse_selected_sheets(value: str) -> list[str]:
    try:
        selected = json.loads(value)
    except json.JSONDecodeError as exc:
        raise HistoricalWorkbookError("selected_sheets must be a JSON array") from exc
    if not isinstance(selected, list) or not all(isinstance(item, str) for item in selected):
        raise HistoricalWorkbookError("selected_sheets must be a JSON array of sheet names")
    return selected


def _metadata_catalog(
    line_group: str,
    tension_length: str = "",
    line_class: str | None = None,
) -> list[dict]:
    line, normalized_class = normalize_line_identity(line_group, line_class)
    metadata = _load_identity_metadata(line, normalized_class)
    names = sorted({item.tension_length for item in metadata}, key=natural_key)
    if tension_length.strip():
        requested_tl = normalize_tension_length(tension_length)
        names = [name for name in names if name == requested_tl]
    catalog = []
    for name in names:
        canonical = resolve_canonical_tl(
            line, name, metadata, line_class=normalized_class
        )
        catalog.append(
            {
                "line_group": line,
                "line_class": normalized_class,
                "tension_length": canonical.tension_length,
                "track": canonical.track,
                "from_m": float(canonical.from_m),
                "to_m": float(canonical.to_m),
                "interval_count": len(canonical.intervals),
                "intervals": [
                    {
                        "track": interval.track,
                        "from_m": float(interval.from_m),
                        "to_m": float(interval.to_m),
                    }
                    for interval in canonical.intervals
                ],
            }
        )
    return catalog


def _business_key(payload: dict) -> BusinessKey:
    line_group, line_class = normalize_line_identity(
        payload.get("line_group"), payload.get("line_class")
    )
    return BusinessKey(
        line_group,
        normalize_cycle_date(payload.get("cycle_date")),
        str(payload.get("tension_length", "")),
        line_class,
    )


def _change_set(payload: dict) -> ChangeSet:
    operations = payload.get("operations")
    if not isinstance(operations, list) or not operations:
        raise MetadataValidationError("operations must be a non-empty array")
    converted = []
    for operation in operations:
        if not isinstance(operation, dict):
            raise MetadataValidationError("each operation must be an object")
        kind = operation.get("kind")
        if kind == "add":
            converted.append(AddOperation(_business_key(operation.get("key", {})), operation.get("avg_wear_min")))
        elif kind == "edit":
            converted.append(EditOperation(
                _business_key(operation.get("key", {})),
                operation.get("avg_wear_min"),
                str(operation.get("expected_updated_at", "")),
            ))
        elif kind == "delete_cell":
            converted.append(DeleteCellOperation(
                _business_key(operation.get("key", {})),
                str(operation.get("expected_updated_at", "")),
            ))
        elif kind == "delete_row":
            line_group, line_class = normalize_line_identity(
                operation.get("line_group"), operation.get("line_class")
            )
            converted.append(DeleteRowOperation(
                line_group,
                normalize_cycle_date(operation.get("cycle_date")),
                line_class,
            ))
        else:
            raise MetadataValidationError(f"unsupported change kind: {kind}")
    return ChangeSet(converted)


class WireWearRecordInputModel(BaseModel):
    tension_length: str
    from_m: float
    to_m: float
    avg_wear_min: float
    sd: float = 0
    wear_percentage: float


class WireWearSaveRequestModel(BaseModel):
    line_group: Literal["EAL", "TML"]
    line_class: Literal["EAL", "LMC", "TML"]
    track: str
    section: str
    cycle_date: str
    source_file_names: List[str] = Field(default_factory=list)
    saved_by: Optional[str] = None
    records: List[WireWearRecordInputModel]


class WireWearSaveResponse(BaseModel):
    saved_count: int
    updated_count: int
    duplicate_count: int
    duplicates: List[dict]


class WireWearRecordsResponse(BaseModel):
    records: List[dict]


class WireWearUpdateRequestModel(BaseModel):
    line_group: Optional[Literal["EAL", "TML"]] = None
    line_class: Optional[Literal["EAL", "LMC", "TML"]] = None
    track: Optional[str] = None
    section: Optional[str] = None
    cycle_date: Optional[str] = None
    tension_length: Optional[str] = None
    from_m: Optional[float] = None
    to_m: Optional[float] = None
    avg_wear_min: Optional[float] = None
    sd: Optional[float] = None
    wear_percentage: Optional[float] = None
    source_file_names: Optional[List[str]] = None
    saved_by: Optional[str] = None


class WireWearCandidateRowModel(BaseModel):
    row_id: Optional[str] = None
    tension_length: object = None
    avg_wear_min: object = None
    tension_length_cell: Optional[str] = None
    avg_wear_min_cell: Optional[str] = None
    excluded: bool = False


class WireWearCandidatePreviewRequestModel(BaseModel):
    line_class: Literal["EAL", "LMC", "TML"]
    cycle_date: str
    rows: List[WireWearCandidateRowModel]


def _to_core_request(payload: WireWearSaveRequestModel) -> WireWearSaveRequest:
    return WireWearSaveRequest(
        line_group=payload.line_group,
        line_class=payload.line_class,
        track=payload.track,
        section=payload.section,
        cycle_date=payload.cycle_date,
        source_file_names=payload.source_file_names,
        saved_by=payload.saved_by,
        records=[
            WireWearRecordInput(
                tension_length=record.tension_length,
                from_m=record.from_m,
                to_m=record.to_m,
                avg_wear_min=record.avg_wear_min,
                sd=record.sd,
                wear_percentage=record.wear_percentage,
            )
            for record in payload.records
        ],
    )


@router.post("/cycles")
async def save_cycle(
    files: List[UploadFile] = File(...),
    line_group: str = Form(...),
    line_class: Optional[str] = Form(default=None),
    cycle_date: str = Form(...),
    accepted_conflict_ids: str = Form(default="[]"),
    expected_preview_digest: Optional[str] = Form(default=None),
    preview_digest_value: Optional[str] = Form(default=None, alias="preview_digest"),
    expected_data_version: int = Form(...),
):
    try:
        line, normalized_class = normalize_line_identity(line_group, line_class)
        normalize_cycle_date(cycle_date)
        accepted_ids = _parse_accepted_conflict_ids(accepted_conflict_ids)
        file_payloads = await _read_complete_cycle_uploads(files)
        preview = _build_complete_cycle_preview(
            file_payloads=file_payloads,
            line_group=line,
            cycle_date=cycle_date,
            accepted_conflict_ids=accepted_ids,
        )
        if inspect.isawaitable(preview):
            preview = await preview
        supplied_digest = expected_preview_digest or preview_digest_value
        if not supplied_digest:
            raise HTTPException(status_code=422, detail="preview_digest is required")
        rebuilt_digest = preview_digest(preview)
        if rebuilt_digest != supplied_digest:
            raise HTTPException(status_code=409, detail="wear preview changed; run preview again")
        preview = replace(preview, line_class=normalized_class)
        db = get_database()
        with db.get_connection() as conn:
            saved = save_analysis_cycle(
                conn,
                preview,
                expected_data_version=expected_data_version,
            )
        response = asdict(saved)
        response["wire_wear_data_version"] = response.pop("data_version")
        return response
    except HTTPException:
        raise
    except (DuplicateBusinessKeyError, StaleDataVersionError, StaleRecordError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (IncompleteCycleError, MetadataValidationError, MetadataResolutionError) as exc:
        detail = {"message": str(exc)}
        if isinstance(exc, IncompleteCycleError):
            detail["blocking_reasons"] = list(exc.blocking_reasons)
        raise HTTPException(status_code=422, detail=detail) from exc
    except WearCycleRepositoryError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/changes")
async def apply_changes(payload: dict):
    try:
        change_set = _change_set(payload)
        identities = {
            normalize_line_identity(operation.key.line_group, operation.key.line_class)
            for operation in change_set.operations
            if hasattr(operation, "key")
        } | {
            normalize_line_identity(operation.line_group, operation.line_class)
            for operation in change_set.operations
            if isinstance(operation, DeleteRowOperation)
        }
        metadata = tuple(
            interval
            for line, line_class in sorted(identities)
            for interval in _load_identity_metadata(line, line_class)
        )
        db = get_database()
        with db.get_connection() as conn:
            expected_data_version = payload.get("expected_data_version")
            result = apply_change_set_with_backup(
                conn,
                change_set,
                metadata,
                db_path=db.db_path,
                origin=payload.get("origin", ChangeSetOrigin.MANUAL.value),
                expected_data_version=(
                    int(expected_data_version)
                    if expected_data_version is not None
                    else None
                ),
            )
        response = asdict(result)
        response["wire_wear_data_version"] = response.pop("data_version")
        return response
    except BackupCreationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ChangeOperationError as exc:
        status = 409 if isinstance(exc.cause, (StaleRecordError, DuplicateBusinessKeyError)) else 422
        raise HTTPException(
            status_code=status,
            detail={"operation_index": exc.operation_index, "message": exc.detail},
        ) from exc
    except StaleDataVersionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (MetadataValidationError, MetadataResolutionError, WearCycleRepositoryError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/historical/discover")
async def discover_historical(file: UploadFile = File(...)):
    try:
        workbook_bytes = await _read_historical_workbook(file)
        return discover_historical_workbook(workbook_bytes).to_dict()
    except HistoricalWorkbookError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/historical/preview")
async def preview_historical(
    file: UploadFile = File(...),
    selected_sheets: str = Form(...),
):
    try:
        workbook_bytes = await _read_historical_workbook(file)
        selected = _parse_selected_sheets(selected_sheets)
        db = get_database()
        with db.get_connection() as conn:
            data_version = current_data_version(conn)
            preview = preview_historical_workbook(
                conn,
                workbook_bytes,
                selected,
                _historical_metadata(),
                data_version,
            )
        return preview.to_dict()
    except StaleHistoricalPreviewError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (
        HistoricalWorkbookError,
        MetadataValidationError,
        MetadataResolutionError,
        WearCycleRepositoryError,
        ValueError,
        TypeError,
    ) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/candidates/preview")
async def preview_candidates(payload: WireWearCandidatePreviewRequestModel):
    try:
        line_group = "TML" if payload.line_class == "TML" else "EAL"
        line, line_class = normalize_line_identity(line_group, payload.line_class)
        cycle_date = normalize_cycle_date(payload.cycle_date).isoformat()
        metadata = _load_identity_metadata(line, line_class)
        candidates = [
            WearRecordCandidate(
                line_group=line,
                line_class=line_class,
                cycle_date=cycle_date,
                tension_length=row.tension_length,
                avg_wear_min=row.avg_wear_min,
                source_type="manual",
                source_row=index + 1,
                tension_length_cell=row.tension_length_cell or f"A{index + 1}",
                avg_wear_min_cell=row.avg_wear_min_cell or f"B{index + 1}",
                original_value=row.avg_wear_min,
                excluded=row.excluded,
                row_id=row.row_id or str(index + 1),
            )
            for index, row in enumerate(payload.rows)
        ]
        db = get_database()
        with db.get_connection() as conn:
            return classify_wear_record_candidates(conn, candidates, metadata).to_dict()
    except (MetadataValidationError, MetadataResolutionError, WearCycleRepositoryError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/metadata-preview")
async def metadata_preview(
    line_group: str = Query(...),
    line_class: Optional[str] = Query(default=None),
    tension_length: str = Query(default=""),
):
    try:
        line, normalized_class = normalize_line_identity(line_group, line_class)
        catalog = _metadata_catalog(line, tension_length, normalized_class)
    except (MetadataValidationError, MetadataResolutionError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if tension_length.strip() and not catalog:
        raise HTTPException(status_code=422, detail="unknown tension length")
    return {"line_group": line, "line_class": normalized_class, "catalog": catalog}


@router.post("", response_model=WireWearSaveResponse)
async def save_records(
    payload: WireWearSaveRequestModel,
    overwrite: bool = Query(default=False),
    check_only: bool = Query(default=False),
):
    db = get_database()
    try:
        with db.get_connection() as conn:
            if check_only:
                result = save_wire_wear_records(conn, _to_core_request(payload), overwrite=False)
                if not result.duplicate_count:
                    conn.rollback()
                    result = WireWearSaveResult(0, 0, 0, [])
            else:
                result = save_wire_wear_records(conn, _to_core_request(payload), overwrite=overwrite)
    except WireWearValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if result.duplicate_count and not overwrite:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Wire wear records already exist for this line/class/track/section/date/tension length.",
                "duplicate_count": result.duplicate_count,
                "duplicates": result.duplicates,
            },
        )
    return WireWearSaveResponse(**result.__dict__)


@router.get("", response_model=WireWearRecordsResponse)
async def list_records(
    line_group: Optional[Literal["EAL", "TML"]] = None,
    line_class: Optional[Literal["EAL", "LMC", "TML"]] = None,
    track: Optional[str] = None,
    section: Optional[str] = None,
    tension_length: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    filters = {
        "line_group": line_group,
        "line_class": line_class,
        "track": track,
        "section": section,
        "tension_length": tension_length,
        "date_from": date_from,
        "date_to": date_to,
    }
    db = get_database()
    try:
        with db.get_connection() as conn:
            records = query_wire_wear_records(conn, filters)
    except WireWearValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return WireWearRecordsResponse(records=records)


@router.post("/manual", response_model=WireWearSaveResponse)
async def add_manual_records(payload: WireWearSaveRequestModel):
    db = get_database()
    try:
        with db.get_connection() as conn:
            result = save_wire_wear_records(conn, _to_core_request(payload), overwrite=False)
    except WireWearValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if result.duplicate_count:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Wire wear records already exist for this line/class/track/section/date/tension length.",
                "duplicate_count": result.duplicate_count,
                "duplicates": result.duplicates,
            },
        )
    return WireWearSaveResponse(**result.__dict__)


@router.get("/workbench")
async def workbench(
    line_group: Literal["EAL", "TML"] = "EAL",
    line_class: Optional[Literal["EAL", "LMC", "TML"]] = None,
    tension_length_query: str = "",
    selected_tension_length: Optional[str] = None,
    summary_only: bool = False,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    db = get_database()
    try:
        with db.get_connection() as conn:
            result = build_cycle_workbench(
                conn,
                line_group,
                tension_length_query,
                date_from,
                date_to,
                line_class,
                selected_tension_length,
                summary_only,
            )
            _, normalized_class = normalize_line_identity(line_group, line_class)
            legacy = None if summary_only or selected_tension_length else build_workbench_summary(
                conn,
                {
                    "line_group": line_group,
                    "line_class": normalized_class,
                    "date_from": date_from,
                    "date_to": date_to,
                },
            )
        try:
            catalog_query = selected_tension_length or tension_length_query
            catalog = _metadata_catalog(line_group, catalog_query, normalized_class)
        except (MetadataValidationError, MetadataResolutionError, OSError):
            catalog = []
        result["catalog"] = catalog
        result["selected_tension_length"] = selected_tension_length
        result["summary_only"] = summary_only
        result["wire_wear_data_version"] = result.pop("data_version")
        # Retain the legacy read-only keys while clients move to the cycle matrix contract.
        if legacy is not None:
            result.update({key: value for key, value in legacy.items() if key not in result})
        return result
    except (WireWearValidationError, MetadataValidationError, WearCycleRepositoryError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/export")
async def export_records(
    line_group: Literal["EAL", "TML"] = "EAL",
    line_class: Optional[Literal["EAL", "LMC", "TML"]] = None,
):
    _, normalized_class = normalize_line_identity(line_group, line_class)
    db = get_database()
    with db.get_connection() as conn:
        content = build_workbench_excel(
            conn, {"line_group": line_group, "line_class": normalized_class}
        )
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="wire-wear-records-{line_group}.xlsx"'},
    )


@router.get("/export.xlsx")
async def export_cycle_report(
    line_group: Optional[Literal["EAL", "TML"]] = None,
    line_class: Optional[Literal["EAL", "LMC", "TML"]] = None,
    cycle_date: Optional[str] = None,
):
    try:
        db = get_database()
        with db.get_connection() as conn:
            content = build_excel_report(
                conn, line_group=line_group, line_class=line_class, cycle_date=cycle_date,
                metadata_fingerprint=_cycle_metadata_fingerprints(),
            )
    except (MetadataValidationError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    suffix = "-".join(value for value in (line_class or line_group, cycle_date) if value) or "all"
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="wire-wear-cycle-{suffix}.xlsx"'},
    )


@router.get("/sync.json")
async def export_cycle_sync(source_workstation: str = Query(default="TOV640 Analyzer")):
    db = get_database()
    with db.get_connection() as conn:
        package = build_sync_package(
            conn, source_workstation=source_workstation,
            metadata_fingerprint=_cycle_metadata_fingerprints(),
        )
    return JSONResponse(content=package, headers={"Content-Disposition": 'attachment; filename="wear-cycle-sync.json"'})


@router.post("/sync/preview")
async def preview_cycle_sync(package: dict):
    try:
        db = get_database()
        with db.get_connection() as conn:
            preview = preview_sync_import(
                conn, package, _sync_metadata(), metadata_fingerprint=_cycle_metadata_fingerprints(),
            )
        return asdict(preview)
    except (SyncValidationError, MetadataValidationError, MetadataResolutionError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/sync/apply")
async def apply_cycle_sync(payload: dict):
    try:
        db = get_database()
        with db.get_connection() as conn:
            result = apply_sync_import(
                conn,
                source_package=payload.get("source_package"),
                preview_digest=str(payload.get("preview_digest", "")),
                expected_data_version=int(payload.get("expected_data_version")),
                metadata=_sync_metadata(), metadata_fingerprint=_cycle_metadata_fingerprints(),
                conflict_decisions=payload.get("conflict_decisions"),
                db_path=db.db_path,
            )
        result["wire_wear_data_version"] = result.pop("data_version")
        return result
    except BackupCreationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (StaleDataVersionError, SyncPreviewMismatchError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (SyncValidationError, MetadataValidationError, MetadataResolutionError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/sync/export")
async def export_sync_package(
    source_label: str = Query(default="TOV640 Analyzer"),
    include_repeated: bool = Query(default=False),
):
    db = get_database()
    with db.get_connection() as conn:
        package = build_wire_wear_sync_package(
            conn,
            source_label=source_label,
            include_repeated=include_repeated,
            metadata_dir=get_config_dir(),
        )
    return JSONResponse(
        content=package,
        headers={"Content-Disposition": 'attachment; filename="wire-wear-sync-package.json"'},
    )


@router.post("/sync/import")
async def import_sync_package(file: UploadFile = File(...)):
    try:
        content = await file.read()
        package = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid sync package JSON.") from exc

    db = get_database()
    try:
        with db.get_connection() as conn:
            return import_wire_wear_sync_package(conn, package, db_path=db.db_path)
    except WireWearValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.patch("/{record_id}")
async def update_record(record_id: int, payload: WireWearUpdateRequestModel):
    updates = {key: value for key, value in payload.model_dump().items() if value is not None}
    db = get_database()
    try:
        with db.get_connection() as conn:
            success = update_wire_wear_record(conn, record_id, updates)
    except WireWearValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not success:
        raise HTTPException(status_code=404, detail=f"Wire wear record not found: {record_id}")
    return {"status": "success", "message": f"Wire wear record updated: {record_id}"}


@router.delete("/{record_id}")
async def delete_record(record_id: int):
    db = get_database()
    with db.get_connection() as conn:
        success = delete_wire_wear_record(conn, record_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Wire wear record not found: {record_id}")
    return {"status": "success", "message": f"Wire wear record deleted: {record_id}"}


@router.get("/dashboard")
async def dashboard(
    line_group: Literal["ALL", "EAL", "TML"] = Query(default="ALL"),
) -> Dict[str, dict]:
    db = get_database()
    with db.get_connection() as conn:
        records = list_committed_records(conn)
    lines = ("EAL", "TML") if line_group == "ALL" else (line_group,)
    return {"line_groups": {line: build_dashboard(records, line) for line in lines}}


@router.get("/projection")
async def projection(
    threshold_mm: float = Query(default=10.2, gt=0, le=13.2),
):
    db = get_database()
    with db.get_connection() as conn:
        return build_projection(list_committed_records(conn), threshold_mm, date.today())


@router.get("/remaining-life")
async def remaining_life(
    threshold_mm: float = Query(default=10.2, gt=0, le=13.2),
):
    db = get_database()
    with db.get_connection() as conn:
        return build_remaining_life(list_committed_records(conn), threshold_mm, date.today())
