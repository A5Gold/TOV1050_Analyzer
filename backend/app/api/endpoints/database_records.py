"""
TOV640 Analyzer - Database Records API Router
==============================================
API endpoints for Database Record module (manual persistence).

Sub-module 1: Exception Records (Single Run) - DEPRECATED (2026-01-31)
- All endpoints return deprecation warnings or 410 Gone status

Sub-module 2: Repeated Exception Records (Enhanced 2026-01-31)
- POST   /api/database/repeated-records                - Save repeated records
- GET    /api/database/repeated-records                - Query repeated records
- PATCH  /api/database/repeated-records/{record_id}   - Update workflow fields (13 fields supported)
- DELETE /api/database/repeated-records/{record_id}   - Delete record
- GET    /api/database/repeated-records/export        - Export to Excel
- POST   /api/database/repeated-records/import        - Import from Excel (NEW)
- POST   /api/database/repeated-records/check-1-year  - Check 1 year records (NEW)

Version: 1.1
Date: 2026-01-31
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import pandas as pd
import io
import logging
from datetime import datetime, timedelta

from app.core.database import (
    get_database,
    # Sub-module 1 (DEPRECATED)
    save_exception_records_batch,
    query_exception_records,
    delete_exception_record,
    export_exception_records_to_df,
    # Sub-module 2 (Active)
    save_repeated_records_batch,
    query_repeated_records,
    count_repeated_records,
    get_repeated_record_section_counts,
    update_repeated_record_workflow,
    delete_repeated_record,
    export_repeated_records_to_df,
    # New functions (2026-01-31)
    check_1_year_records,
    import_repeated_records_from_data,
)
from app.core.check_1_year_rules import evaluate_recurrence, append_recurrence_ids, target_version, parse_date

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================


class SaveRepeatedRecordsRequest(BaseModel):
    """Request model for saving repeated records (Sub-module 2)."""
    line: str
    track: str
    date_str: str
    repeated_exceptions: List[Dict[str, Any]]
    task_no: Optional[str] = None
    station_start: Optional[str] = None
    station_end: Optional[str] = None
    saved_by: Optional[str] = None
    latest_file_name: Optional[str] = None
    comparison_files: Optional[List[str]] = None
    task_run_date: Optional[str] = None  # NEW: Phase 8.1 (2026-02-01)
    approved_recurrence_links: List[Dict[str, Any]] = []


class UpdateRepeatedRecordRequest(BaseModel):
    """Request model for updating repeated record workflow fields.
    
    Enhanced (2026-01-31): Now supports 13 workflow fields including:
    - Initial Check: action, check_date, checked_by, check_result, remarks
    - Site Verification: verify_deadline, verify_date, verify_result, verified_by
    - Final Adjustment: adjust_deadline, adjust_date, adjust_result, adjusted_by
    - Reoccurrence: reoccurrence_id
    """
    # Initial Check
    action: Optional[str] = None
    check_date: Optional[str] = None
    checked_by: Optional[str] = None
    check_result: Optional[str] = None
    remarks: Optional[str] = None
    # Site Verification (NEW)
    verify_deadline: Optional[str] = None
    verify_date: Optional[str] = None
    verify_result: Optional[str] = None
    verified_by: Optional[str] = None
    # Final Adjustment (NEW)
    adjust_deadline: Optional[str] = None
    adjust_date: Optional[str] = None
    adjust_result: Optional[str] = None
    adjusted_by: Optional[str] = None
    # Reoccurrence (NEW)
    reoccurrence_id: Optional[str] = None


class ImportRecordsRequest(BaseModel):
    """Request model for importing records from Excel data."""
    records: List[Dict[str, Any]]
    line: str
    track: str
    date_str: str


class ImportRecordsResponse(BaseModel):
    """Response model for import operation."""
    status: str
    message: str
    created_count: int
    updated_count: int
    error_count: int


class Check1YearRequest(BaseModel):
    """Request model for Check 1 Year Record feature."""
    exceptions: List[Dict[str, Any]]
    line: str
    track: str
    current_date: Optional[str] = None  # FIX #6: Fallback date for exceptions without task_run_date
    section: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None


class Check1YearResponse(BaseModel):
    """Response model for Check 1 Year Record feature."""
    status: str
    message: str
    match_count: int
    exceptions: List[Dict[str, Any]]
    checked_count: int = 0
    auto_verified_count: int = 0
    review_required_count: int = 0
    keep_monitoring_count: int = 0
    unmatched_count: int = 0
    skipped_count: int = 0
    review_proposals: List[Dict[str, Any]] = []


class RepeatedRecordSectionCountsResponse(BaseModel):
    """Complete repeated-record section navigation counts."""
    all: int
    mainline: int
    rac: int
    low_s1: int
    lmc: int
    unknown: int


class RecordsListResponse(BaseModel):
    """Response model for records list."""
    status: str
    total: int
    section_counts: RepeatedRecordSectionCountsResponse
    records: List[Dict[str, Any]]


class SaveSuccessResponse(BaseModel):
    """Response model for save operation."""
    status: str
    message: str
    saved_count: int
    filtered_mock_count: Optional[int] = None


class SuccessResponse(BaseModel):
    """Generic success response."""
    status: str
    message: str


# =============================================================================
# SUB-MODULE 2: REPEATED EXCEPTION RECORDS
# =============================================================================

@router.post("/database/repeated-records", response_model=SaveSuccessResponse)
async def save_repeated_records(request: SaveRepeatedRecordsRequest) -> SaveSuccessResponse:
    """
    Save repeated exception records from History Compare to database.
    
    **Important:** Records with IDs starting with 'mock-' are automatically filtered out.
    
    **Request body:**
    - `line`: Line code (EAL/TML)
    - `track`: Track (UP/DOWN)
    - `date_str`: Latest analysis date (YYYYMMDD)
    - `repeated_exceptions`: List of repeated exception records
    
    **Optional fields:**
    - `task_no`: Task number
    - `station_start`, `station_end`: Station range
    - `saved_by`: User identifier
    - `latest_file_name`: Name of the latest Excel file
    - `comparison_files`: List of files used in comparison
    """
    try:
        if not request.repeated_exceptions:
            raise HTTPException(
                status_code=400,
                detail="No repeated exceptions to save."
            )
        
        db = get_database()
        with db.get_connection() as conn:
            # Validate every unique review target before any current-record write.
            # This keeps a stale proposal from partially committing a batch.
            target_links: Dict[int, List[Dict[str, Any]]] = {}
            for link in request.approved_recurrence_links:
                try:
                    record_id = int(link["target_record_id"])
                except (KeyError, TypeError, ValueError) as exc:
                    raise HTTPException(status_code=422, detail="approved_recurrence_links.target_record_id must be an integer") from exc
                target_links.setdefault(record_id, []).append(link)
            target_rows: Dict[int, Any] = {}
            for record_id, links in target_links.items():
                row = conn.execute("SELECT * FROM saved_repeated_exceptions WHERE record_id = ?", (record_id,)).fetchone()
                if row is None:
                    raise HTTPException(status_code=409, detail=f"Repeated record {record_id} no longer exists; rerun Check 1 Year.")
                actual_version = target_version(dict(row))
                expected_versions = {str(link.get("target_version") or "") for link in links}
                if expected_versions != {actual_version}:
                    raise HTTPException(status_code=409, detail=f"Repeated record {record_id} changed after Check 1 Year; rerun Check 1 Year.")
                target_rows[record_id] = row
            result = save_repeated_records_batch(
                conn=conn,
                line=request.line,
                track=request.track,
                date_str=request.date_str,
                repeated_exceptions=request.repeated_exceptions,
                task_no=request.task_no,
                station_start=request.station_start,
                station_end=request.station_end,
                saved_by=request.saved_by,
                latest_file_name=request.latest_file_name,
                comparison_files=request.comparison_files,
                task_run_date=request.task_run_date  # NEW: Phase 8.1 (2026-02-01)
            )
            expected_saved = sum(
                1
                for exception in request.repeated_exceptions
                if str(exception.get("exception_id") or exception.get("id") or "")
                and not str(exception.get("exception_id") or exception.get("id") or "").lower().startswith("mock-")
                and "MOCK_DATA" not in str(exception.get("exception_id") or exception.get("id") or "").upper()
            )
            if result["saved_count"] != expected_saved:
                raise RuntimeError(
                    f"Repeated record transaction saved {result['saved_count']} of {expected_saved} real records"
                )
            # Approved review links are part of the same transaction as the
            # current records. Append all IDs once per target and de-duplicate.
            for record_id, links in target_links.items():
                ids = [link.get("exception_id") for link in links]
                value = append_recurrence_ids(target_rows[record_id]["reoccurrence_id"], ids)
                conn.execute("UPDATE saved_repeated_exceptions SET reoccurrence_id = ? WHERE record_id = ?", (value, record_id))
        
        saved_count = result['saved_count']
        filtered_mock_count = result['filtered_mock_count']
        
        if saved_count == 0:
            raise HTTPException(
                status_code=400,
                detail=f"No real exceptions to save. Filtered {filtered_mock_count} mock data records."
            )
        
        logger.info(f"Saved {saved_count} repeated records, filtered {filtered_mock_count} mock data")
        
        return SaveSuccessResponse(
            status="success",
            message=f"Saved {saved_count} repeated records",
            saved_count=saved_count,
            filtered_mock_count=filtered_mock_count
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving repeated records: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Phase 10.10 - Bug 1.3: Distinct Values for Dynamic Dropdown Filters
# =============================================================================

@router.get("/database/repeated-records/distinct-values")
async def get_distinct_field_values(
    field: str = Query(..., description="Field name to get distinct values for"),
    line: Optional[str] = Query(None, description="Optional line filter"),
):
    """
    Get distinct non-null values for a field from saved_repeated_exceptions.
    Used for populating dynamic dropdown filters (e.g., Task Number).
    
    Allowed fields: task_no, line, track, section, level, exception_type, 
                    action, station_start, station_end
    """
    from app.core.database import get_distinct_values, ALLOWED_DISTINCT_FIELDS

    if field not in ALLOWED_DISTINCT_FIELDS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid field '{field}'. Allowed fields: {', '.join(sorted(ALLOWED_DISTINCT_FIELDS))}"
        )

    try:
        db = get_database()
        with db.get_connection() as conn:
            values = get_distinct_values(conn, field, line=line)

        return {
            "status": "success",
            "field": field,
            "values": values,
            "count": len(values),
        }
    except Exception as e:
        logger.error(f"Error getting distinct values for {field}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Phase 12 Bug 4: Line Counts API
# =============================================================================

@router.get("/database/repeated-records/counts")
async def get_repeated_record_counts():
    """
    Get record counts grouped by line (EAL/TML).
    Used for Tab count indicators in LineTabPanel.
    Returns counts for all lines regardless of current filter.
    """
    from app.core.database import get_line_counts

    try:
        db = get_database()
        with db.get_connection() as conn:
            counts = get_line_counts(conn)

        return {
            "status": "success",
            "counts": counts,
        }
    except Exception as e:
        logger.error(f"Error getting line counts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/database/repeated-records", response_model=RecordsListResponse)
async def get_repeated_records(
    line: Optional[str] = Query(None, description="Filter by line"),
    track: Optional[str] = Query(None, description="Filter by track"),
    section: Optional[str] = Query(None, description="Filter by section (Mainline/RAC/LOW S1/LMC/Unknown)"),
    level: Optional[str] = Query(None, description="Filter by level (L1/L2/L3)"),
    action: Optional[str] = Query(None, description="Filter by action status"),
    exception_type: Optional[str] = Query(None, description="Filter by exception type"),
    task_number: Optional[str] = Query(None, description="Filter by task number"),
    date_from: Optional[str] = Query(None, description="Start date (YYYYMMDD)"),
    date_to: Optional[str] = Query(None, description="End date (YYYYMMDD)"),
    date_type: Optional[str] = Query(None, description="Date field to filter (saved_at or task_run_date)"),
    # BUG 10.9.1-4 FIX: Add Chainage filter parameters
    chainage_from: Optional[float] = Query(None, description="Chainage range start (meters)"),
    chainage_to: Optional[float] = Query(None, description="Chainage range end (meters)"),
    limit: int = Query(1000, ge=1, le=5000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Pagination offset")
) -> RecordsListResponse:
    """
    Query saved repeated exception records with optional filters.
    
    **Filters:**
    - `line`, `track`, `section`: Location filters
    - `level`: Severity level (L1/L2/L3)
    - `action`: Workflow action status (Keep monitoring, Calculation, Verify on site, etc.)
    - `exception_type`: Type of exception
    - `task_number`: Task number filter
    - `date_from`, `date_to`: Date range (YYYYMMDD)
    - `date_type`: Which date field to use (saved_at or task_run_date)
    - `chainage_from`, `chainage_to`: Chainage range filter (partial overlap logic)
    """
    try:
        filters: Dict[str, Any] = {}
        if line:
            filters['line'] = line
        if track:
            filters['track'] = track
        if section:
            filters['section'] = section
        if level:
            filters['level'] = level
        if action:
            filters['action'] = action
        if exception_type:
            filters['exception_type'] = exception_type
        if task_number:
            filters['task_number'] = task_number
        if date_from:
            filters['date_from'] = date_from
        if date_to:
            filters['date_to'] = date_to
        if date_type:
            filters['date_type'] = date_type
        # BUG 10.9.1-4 FIX: Pass Chainage filters to query function
        if chainage_from is not None:
            filters['chainage_from'] = chainage_from
        if chainage_to is not None:
            filters['chainage_to'] = chainage_to
        
        db = get_database()
        with db.get_connection() as conn:
            if not conn.in_transaction:
                conn.execute("BEGIN")
            records = query_repeated_records(
                conn,
                filters=filters if filters else None,
                limit=limit,
                offset=offset
            )
            total = count_repeated_records(conn, filters=filters if filters else None)
            section_counts = get_repeated_record_section_counts(
                conn,
                filters=filters if filters else None,
            )
        
        return RecordsListResponse(
            status="success",
            total=total,
            section_counts=section_counts,
            records=records
        )
    
    except Exception as e:
        logger.error(f"Error querying repeated records: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/database/repeated-records/{record_id}", response_model=SuccessResponse)
async def update_repeated_record(
    record_id: int,
    request: UpdateRepeatedRecordRequest
) -> SuccessResponse:
    """
    Update workflow fields for a repeated exception record.
    
    **Allowed fields:**
    - `action`: Follow-up action (Keep monitoring, Calculation, Verify on site, etc.)
    - `check_date`: Date of check (YYYY-MM-DD)
    - `checked_by`: Person who checked
    - `check_result`: Calculation result (Pass/Fail/N/A)
    - `remarks`: Additional notes
    
    Note: `last_updated` is automatically set by database trigger.
    """
    try:
        # Convert to dict and filter None values
        updates = {k: v for k, v in request.model_dump().items() if v is not None}
        
        if not updates:
            raise HTTPException(
                status_code=400,
                detail="No fields to update. Provide at least one field."
            )
        
        db = get_database()
        with db.get_connection() as conn:
            success = update_repeated_record_workflow(conn, record_id, updates)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Repeated record not found: {record_id}"
            )
        
        logger.info(f"Updated repeated record {record_id}: {list(updates.keys())}")
        
        return SuccessResponse(
            status="success",
            message=f"Updated repeated record {record_id}"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating repeated record: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Feature-002: Batch Update Endpoint
# =============================================================================

class BatchUpdateItem(BaseModel):
    """Single record update in a batch operation."""
    record_id: int
    action: Optional[str] = None
    check_date: Optional[str] = None
    checked_by: Optional[str] = None
    check_result: Optional[str] = None
    remarks: Optional[str] = None
    verify_deadline: Optional[str] = None
    verify_date: Optional[str] = None
    verified_by: Optional[str] = None
    verify_result: Optional[str] = None
    adjust_deadline: Optional[str] = None
    adjust_date: Optional[str] = None
    adjusted_by: Optional[str] = None
    adjust_result: Optional[str] = None
    reoccurrence_id: Optional[str] = None


class BatchUpdateRequest(BaseModel):
    """Request for batch updating multiple repeated exception records."""
    updates: List[BatchUpdateItem]


class BatchUpdateResponse(BaseModel):
    """Response for batch update operation."""
    status: str
    updated_count: int
    message: Optional[str] = None


@router.post("/database/repeated-records/batch-update", response_model=BatchUpdateResponse)
async def batch_update_repeated_records(request: BatchUpdateRequest) -> BatchUpdateResponse:
    """
    Batch update multiple repeated exception records.
    
    **Feature-002:** Enables batch save for RepeatedRecordTable edits.
    Updates `last_updated` timestamp on all modified records via database trigger.
    
    **Request Body:**
    - `updates`: Array of record updates, each containing `record_id` and fields to update
    
    **Returns:**
    - `status`: "success" or "error"
    - `updated_count`: Number of records successfully updated
    """
    try:
        if not request.updates:
            return BatchUpdateResponse(
                status="success",
                updated_count=0,
                message="No updates provided"
            )
        
        db = get_database()
        updated_count = 0
        
        with db.get_connection() as conn:
            for update_item in request.updates:
                # Convert to dict and filter None values (except record_id)
                updates = {
                    k: v for k, v in update_item.model_dump().items() 
                    if v is not None and k != 'record_id'
                }
                
                if not updates:
                    continue
                
                success = update_repeated_record_workflow(
                    conn, 
                    update_item.record_id, 
                    updates
                )
                
                if success:
                    updated_count += 1
        
        logger.info(f"Batch updated {updated_count} records out of {len(request.updates)} requested")
        
        return BatchUpdateResponse(
            status="success",
            updated_count=updated_count,
            message=f"Successfully updated {updated_count} records"
        )
    
    except Exception as e:
        logger.error(f"Error batch updating records: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/database/repeated-records/{record_id}", response_model=SuccessResponse)
async def delete_repeated_record_endpoint(record_id: int) -> SuccessResponse:
    """
    Delete a repeated exception record by ID.
    
    **Warning:** This action cannot be undone.
    """
    try:
        db = get_database()
        with db.get_connection() as conn:
            success = delete_repeated_record(conn, record_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Repeated record not found: {record_id}"
            )
        
        logger.info(f"Deleted repeated record: {record_id}")
        
        return SuccessResponse(
            status="success",
            message=f"Repeated record deleted: {record_id}"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting repeated record: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/database/repeated-records/export")
async def export_repeated_records(
    line: Optional[str] = Query(None),
    track: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    level: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None)
):
    """
    Export repeated exception records to Excel file (Follow-up Action Master List).
    
    Applies the same filters as the GET endpoint.
    Returns an Excel file (.xlsx) as a downloadable attachment.
    """
    try:
        filters: Dict[str, Any] = {}
        if line:
            filters['line'] = line
        if track:
            filters['track'] = track
        if action:
            filters['action'] = action
        if level:
            filters['level'] = level
        if date_from:
            filters['date_from'] = date_from
        if date_to:
            filters['date_to'] = date_to
        
        db = get_database()
        with db.get_connection() as conn:
            df = export_repeated_records_to_df(conn, filters if filters else None)
        
        # Generate Excel file
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            if df.empty:
                # Create empty DataFrame with headers
                empty_df = pd.DataFrame(columns=[
                    'record_id', 'exception_id', 'exception_type', 'level',
                    'from_m', 'to_m', 'action', 'check_date', 'checked_by',
                    'line', 'track', 'date_str', 'saved_at'
                ])
                empty_df.to_excel(writer, sheet_name='Follow-up Action Master List', index=False)
            else:
                df.to_excel(writer, sheet_name='Follow-up Action Master List', index=False)
        
        output.seek(0)
        
        # Generate filename - Phase 11 Issue 5: New naming format
        today = datetime.now().strftime("%Y%m%d_%H%M%S")
        line_part = line or "All"
        filename = f"{today}_{line_part} Exception Follow-up Master List.xlsx"
        
        return StreamingResponse(
            output,
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={'Content-Disposition': f'attachment; filename="{filename}"'}
        )
    
    except Exception as e:
        logger.error(f"Error exporting repeated records: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# NEW ENDPOINTS (2026-01-31): IMPORT AND CHECK 1 YEAR RECORD
# =============================================================================

@router.post("/database/repeated-records/import", response_model=ImportRecordsResponse)
async def import_repeated_records(request: ImportRecordsRequest) -> ImportRecordsResponse:
    """
    Import repeated exception records from Excel data.
    
    Uses Merge/Update strategy:
    - If record exists (by composite key): Update workflow fields
    - If record does not exist: Insert as new record
    
    Matching Logic:
    - Composite key: exception_id + line + track + date_str
    
    **Request body:**
    - `records`: List of record dictionaries from parsed Excel
    - `line`: Default line code if not in records
    - `track`: Default track if not in records
    - `date_str`: Default date if not in records
    
    **Returns:**
    - `created_count`: Number of new records created
    - `updated_count`: Number of existing records updated
    - `error_count`: Number of failed records
    """
    try:
        if not request.records:
            raise HTTPException(
                status_code=400,
                detail="No records to import. The records list is empty."
            )
        
        db = get_database()
        with db.get_connection() as conn:
            result = import_repeated_records_from_data(
                conn=conn,
                records=request.records,
                line=request.line,
                track=request.track,
                date_str=request.date_str
            )
        
        total_processed = result['created_count'] + result['updated_count'] + result['error_count']
        logger.info(f"Import completed: {result['created_count']} created, {result['updated_count']} updated, {result['error_count']} errors")
        
        return ImportRecordsResponse(
            status="success",
            message=f"Imported {total_processed} records: {result['created_count']} created, {result['updated_count']} updated",
            created_count=result['created_count'],
            updated_count=result['updated_count'],
            error_count=result['error_count']
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error importing repeated records: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/database/repeated-records/check-1-year", response_model=Check1YearResponse)
async def check_1_year_record(request: Check1YearRequest) -> Check1YearResponse:
    """
    Check repeated exceptions against database records from the past 1 year.
    
    **Logic:**
    For each repeated exception in the request:
    1. **Location Match**: Check if MaxLocation falls between DB record's FromM and ToM
    2. **Time Match (Look-back)**: Check if DB record date is within 1 year before current date
       Formula: (Current_Date - 1 Year) <= DB_Record_Date <= Current_Date
    
    **If both conditions match:**
    - Sets `action` to "No action Required (Verified within 1 year)"
    - Sets `reoccurrence_id` to the matched DB record's ID
    
    **Important:**
    - Does NOT overwrite existing `check_result` values
    - Only modifies exceptions where `action` is empty or "Pending"
    
    **Request body:**
    - `exceptions`: List of exception dictionaries from ComparisonDataGrid
    - `line`: Line code (EAL/TML)
    - `track`: Track (UP/DOWN)
    
    **Returns:**
    - `match_count`: Number of exceptions that matched database records
    - `exceptions`: Updated list with action and reoccurrence_id populated where matched
    """
    try:
        if not request.exceptions:
            raise HTTPException(
                status_code=400,
                detail="No exceptions to check. The exceptions list is empty."
            )
        
        db = get_database()
        with db.get_connection() as conn:
            date_from = parse_date(request.date_from) if request.date_from else None
            date_to = parse_date(request.date_to) if request.date_to else None
            if request.date_from and date_from is None or request.date_to and date_to is None:
                raise HTTPException(status_code=422, detail="date_from/date_to must use YYYYMMDD, YYYY-MM-DD, or YYYY/MM/DD")
            if date_from and date_to and date_from > date_to:
                raise HTTPException(status_code=422, detail="date_from must not be later than date_to")
            if date_from or date_to:
                filter_start = date_from or datetime.min
                filter_end = date_to or datetime.max
                has_effective_window = False
                for exception in request.exceptions:
                    exception_date = parse_date(
                        exception.get("task_run_date") or exception.get("date_str") or request.current_date
                    )
                    if exception_date is not None and max(
                        exception_date - timedelta(days=365), filter_start
                    ) <= min(exception_date, filter_end):
                        has_effective_window = True
                        break
                if not has_effective_window:
                    raise HTTPException(status_code=422, detail="date filter has no effective 365-day window for the supplied exceptions")
            rows = [dict(row) for row in conn.execute(
                "SELECT * FROM saved_repeated_exceptions WHERE line = ? AND track = ?",
                (request.line, request.track),
            ).fetchall()]
            results = [evaluate_recurrence(
                exception, rows, line=request.line, track=request.track,
                current_date=request.current_date, section_filter=request.section,
                date_from=request.date_from, date_to=request.date_to,
            ) for exception in request.exceptions]
            # Only automatic outcomes write back. Reoccurrence IDs are appended
            # idempotently and every target is updated once per Check transaction.
            grouped: Dict[int, List[str]] = {}
            for result in results:
                if result["status"] == "auto_verified" and result.get("target_record_id"):
                    grouped.setdefault(int(result["target_record_id"]), []).append(str(result["exception"].get("id") or result["exception"].get("exception_id") or ""))
            for record_id, ids in grouped.items():
                current = conn.execute("SELECT reoccurrence_id FROM saved_repeated_exceptions WHERE record_id = ?", (record_id,)).fetchone()
                if current is None:
                    continue
                value = append_recurrence_ids(current["reoccurrence_id"], ids)
                conn.execute("UPDATE saved_repeated_exceptions SET reoccurrence_id = ? WHERE record_id = ?", (value, record_id))
            # Automatic writebacks update last_updated. Refresh review proposal
            # versions after those writes so Save to DB can use a valid guard.
            for result in results:
                record_id = result.get("target_record_id")
                if result.get("status") == "review_required" and record_id:
                    refreshed = conn.execute(
                        "SELECT * FROM saved_repeated_exceptions WHERE record_id = ?",
                        (int(record_id),),
                    ).fetchone()
                    if refreshed is not None:
                        result["target_version"] = target_version(dict(refreshed))
            updated_exceptions = []
            proposals = []
            for result in results:
                row = dict(result["exception"])
                row["check_1_year_status"] = result["status"]
                if result.get("reason"):
                    row["check_1_year_reason"] = result["reason"]
                if result["status"] == "review_required":
                    row["proposed_action"] = result.get("proposed_action")
                    row["proposed_reoccurrence_id"] = result.get("proposed_reoccurrence_id")
                    proposal = {key: result.get(key) for key in ("target_record_id", "target_exception_id", "target_version", "observed_action", "proposed_action", "proposed_reoccurrence_id")}
                    proposal["exception_id"] = row.get("id") or row.get("exception_id")
                    proposals.append(proposal)
                updated_exceptions.append(row)
        counts = {status: sum(1 for result in results if result["status"] == status) for status in ("auto_verified", "review_required", "keep_monitoring", "unmatched", "skipped")}
        match_count = counts["auto_verified"] + counts["review_required"]
        
        logger.info(f"Check 1 year: {match_count} matches found for {request.line}/{request.track}")
        
        return Check1YearResponse(
            status="success",
            message=f"Found {match_count} matches out of {len(request.exceptions)} exceptions",
            match_count=match_count,
            exceptions=updated_exceptions,
            checked_count=len(updated_exceptions),
            auto_verified_count=counts["auto_verified"],
            review_required_count=counts["review_required"],
            keep_monitoring_count=counts["keep_monitoring"],
            unmatched_count=counts["unmatched"],
            skipped_count=counts["skipped"],
            review_proposals=proposals,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking 1 year records: {e}")
        raise HTTPException(status_code=500, detail=str(e))
