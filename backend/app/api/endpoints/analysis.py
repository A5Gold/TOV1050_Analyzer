from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File, Query
from fastapi.responses import StreamingResponse, FileResponse
from starlette.concurrency import run_in_threadpool
from starlette.background import BackgroundTask
from pydantic import BaseModel
from pathlib import Path
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Union
import io
import json
import re
import urllib.parse
import logging
import threading
import uuid
import os
import hashlib
import time
from functools import partial
import anyio
from copy import deepcopy
from typing import Literal
from app.core.background_jobs import (JobManager, JobCancelled, JobTimedOut, JobCapacityError, JobMissing, JobExpired, JobNotReady)

from app.core.data_ingestion import DataLoader
from app.core.tov1050_contract import (
    LINE_WORKBOOKS,
    build_output_filename,
    metadata_workbook_for,
    metadata_track_sheet,
    normalize_session,
    parse_input_filename,
)
from app.core.tov1050_data_ingestion import TOV1050DataLoader
from app.core.tov1050_metadata import TOV1050MetadataManager
from app.core.metadata import MetadataManager
from app.core.analyzers import ExceptionDetector
from app.core.exporter import ExcelExporter
from app.core.tov1050_report_export import export_analysis_report
from app.core.repeated_finder import RepeatedExceptionFinder
from app.core.chart_sampling import build_chart_payload, MEASUREMENT_COLUMNS, normalize_chart_window
from app.core.chart_cache import ChartSource, WindowCache
from app.core.chart_thresholds import build_threshold_segments, clip_threshold_segments
from app.core.report_context import (ReportContextError, read_report_context,
                                     ensure_compatible_scopes, validate_algorithm_compatibility)
from app.core.line_registry import normalize_context, normalize_line

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()


def _download_body(stream, line):
    """Avoid a thread-pool handoff per CSV line or binary newline."""
    if str(line).strip().upper() in LINE_WORKBOOKS:
        return iter(lambda: stream.read(64 * 1024), b"")
    return stream

# Utility Function: Conditional File Naming
def generate_filename(
    date_str: str,
    line: str,
    track: str,
    section: str,
    file_type: str,
    file_count: Optional[int] = None,
    task_no: Optional[str] = None,
    station_start: Optional[str] = None,
    station_end: Optional[str] = None,
    session: Optional[str] = None,
) -> str:
    """
    Generate filename with conditional naming logic.
    
    Logic:
    - Condition A (Default): If ANY of the optional fields are missing -> Use Track + Section
    - Condition B (Custom): If ALL optional fields provided -> Use Task Number + Station Range
    
    Args:
        date_str: Date in YYYYMMDD format
        line: Line code (e.g., "EAL", "TML")
        track: Track code (e.g., "UP", "DN")
        section: Section code (e.g., "Mainline", "LMC")
        file_type: One of 'raw', 'report', 'repeated'
        file_count: File count for repeated reports (required if file_type='repeated')
        task_no: Optional task number (e.g., "U1", "D3")
        station_start: Optional station start code (e.g., "HUH", "LOW")
        station_end: Optional station end code (e.g., "RAC", "SHA")
    
    Returns:
        Formatted filename string
    
    Examples:
        >>> generate_filename("20260127", "EAL", "UP", "Mainline", "report")
        "20260127_EAL_UP_Mainline_Exception_Report.xlsx"
        
        >>> generate_filename("20260127", "EAL", "UP", "Mainline", "report", 
        ...                   task_no="U1", station_start="HUH", station_end="RAC")
        "20260127_EAL_U1_HUH-RAC_Exception_Report.xlsx"
    """
    tov1050_lines = LINE_WORKBOOKS
    # Accept legacy UI direction aliases when generating a filename.
    if str(line).strip().upper() in tov1050_lines:
        track = {"UP": "UT", "DN": "DT"}.get(str(track).strip().upper(), track)
    # TOV1050 exports must always carry the selected session and station range.
    if str(line).strip().upper() in tov1050_lines and not session:
        raise ValueError("TOV1050 export requires an explicit session")
    if str(line).strip().upper() in tov1050_lines and (not station_start or not station_end):
        raise ValueError("TOV1050 export requires station_start and station_end")

    # TOV1050 format is selected when a session is present.
    if session and str(line).strip().upper() in tov1050_lines:
        artifact = {
            'raw': 'Catenary_Report',
            'report': 'Exception_Report',
            'repeated': f'Exception_Report_{file_count}_Repeated' if file_count is not None else 'Exception_Report_Repeated',
        }.get(file_type)
        if artifact is None:
            raise ValueError(f"Unknown file_type: {file_type}")
        extension = 'csv' if file_type == 'raw' else 'xlsx'
        return build_output_filename(
            date_str=date_str,
            line=line,
            track=track,
            session=session,
            station_start=station_start,
            station_end=station_end,
            artifact=artifact,
            extension=extension,
        )

    # Condition check: Use custom mode only if ALL three optional fields are provided
    use_custom_mode = all([task_no, station_start, station_end])
    
    if use_custom_mode:
        # Condition B: Custom Mode (Task Number + Station Range)
        middle_part = f"{task_no}_{station_start.upper()}-{station_end.upper()}"
    else:
        # Condition A: Default Mode (Track + Section)
        middle_part = f"{track}_{section}"
    
    # Build filename based on file type
    if file_type == 'raw':
        return f"{date_str}_{line}_{middle_part}_Catenary_Report.csv"
    elif file_type == 'report':
        return f"{date_str}_{line}_{middle_part}_Exception_Report.xlsx"
    elif file_type == 'repeated':
        if file_count is None:
            raise ValueError("file_count is required for repeated report type")
        return f"{date_str}_{line}_{middle_part}_Exception_Report_{file_count}_Repeated.xlsx"
    else:
        raise ValueError(f"Unknown file_type: {file_type}. Must be 'raw', 'report', or 'repeated'")

# Global Cache for Single-User Desktop App
LAST_ANALYSIS_RESULTS = {}
LAST_RAW_DF = pd.DataFrame()
LAST_ANALYSIS_SNAPSHOT = None
LAST_ANALYSIS_SOURCE_PATH: Optional[str] = None
LAST_COMPARE_RESULTS = pd.DataFrame()
LAST_COMPARE_FILES = []
LAST_ANALYSIS_PARAMS = {} # Store context for file naming
LAST_METADATA_CAPABILITIES = None

# Per-tab analysis state.  The desktop UI supplies ``client_session_id`` for
# every analysis request; keeping raw frames and parameters under that key
# prevents a later tab from replacing the data used by an earlier tab's
# detail chart or legacy GET export.  The LAST_* globals remain as a backward
# compatible fallback for API clients that predate this contract.
ANALYSIS_SESSIONS: dict[str, dict[str, Any]] = {}
MAX_ANALYSIS_SESSIONS = 8
STATE_LOCK = threading.RLock()
JOBS = JobManager(
    ttl_seconds=float(os.environ.get("TOV1050_JOB_TTL_SECONDS", "3600")),
    execution_timeout_seconds=(float(os.environ["TOV1050_JOB_TIMEOUT_SECONDS"])
                               if os.environ.get("TOV1050_JOB_TIMEOUT_SECONDS") else None),
)
DETAIL_LIMITER = anyio.CapacityLimiter(1)
RAW_CHART_TTL_SECONDS = 120


def _session_key(client_session_id: Optional[str]) -> str:
    return str(client_session_id or "default")


def _state_for(client_session_id: Optional[str]) -> Optional[dict[str, Any]]:
    if not client_session_id:
        return None
    return ANALYSIS_SESSIONS.get(_session_key(client_session_id))

# Define Request Model
class AnalyzeRequest(BaseModel):
    file_path: str
    line: str      # e.g., "EAL", "TML"
    section: str   # e.g., "Mainline", "LMC"
    track: str     # e.g., "UP", "DN"
    date_str: str  # e.g., "20251212"
    session: Optional[str] = None  # Mainline, PL, or TKS
    branch: Optional[str] = None
    # Optional fields for custom file naming
    task_no: Optional[str] = None        # e.g., "U1", "D3", "S1"
    station_start: Optional[str] = None  # e.g., "HUH", "LOW"
    station_end: Optional[str] = None    # e.g., "RAC", "SHA"
    # Frontend analysis-tab identity.  This is distinct from the railway
    # metadata ``session`` (Mainline/PL/TKS).
    client_session_id: Optional[str] = None
    analysis_mode: Literal["median", "raw_overview"] = "median"
    chart_data_mode: Literal["raw", "chainage_mean", "chainage_median"] = "chainage_median"

class ReportJobRequest(BaseModel):
    client_session_id: str
    analysis_revision: str
    chart_data_mode: Literal["raw", "chainage_mean", "chainage_median"] = "chainage_median"

class GenerateExportRequest(BaseModel):
    data: List[Dict[str, Any]]
    metadata: Optional[Dict[str, Any]] = {}

class GenerateAnalysisReportRequest(BaseModel):
    exceptions: Dict[str, Any]
    chart_data: Optional[Dict[str, List[Any]]] = None
    params: Dict[str, Any]
    client_session_id: Optional[str] = None

# Define Paths - Handle both development and PyInstaller frozen modes
import sys
from app.core.config import get_config_dir

CONFIG_DIR = get_config_dir()
logger.info(f"[Analysis] CONFIG_DIR initialized: {CONFIG_DIR.absolute()}")


def _chart_columns(frame: pd.DataFrame) -> list[str]:
    """Keep the existing chart contract while centralising column selection."""
    columns = ["Chainage"]
    columns += [column for column in frame.columns if "height" in column.lower()]
    columns += [column for column in frame.columns if "stagger" in column.lower()]
    columns += [column for column in frame.columns if "wear" in column.lower()]
    columns += [column for column in ("Track Type", "Overlap", "Tension Length", "Landmark", "Class") if column in frame.columns]
    columns += [column for column in ("stg_max", "stg_min") if column in frame.columns]
    columns += [column for column in ("task_run_date", "line", "branch", "track", "Section", "task_no", "station_start", "station_end") if column in frame.columns]
    columns += [c for c in frame.columns if c in ("source_row_number", "SampleCount", "group_id", "pass_id", "segment_id", "sample_count", "source_row_first", "source_row_last") or c.endswith(("_source_row", "_sample_counter", "_valid_count"))]
    return list(dict.fromkeys(columns))


def _exception_chainages(results: dict[str, pd.DataFrame], boundaries: pd.DataFrame) -> list[float]:
    values: list[float] = []
    for frame in results.values():
        for column in ("FromM", "ToM", "maxLocation"):
            if column in frame.columns:
                values.extend(pd.to_numeric(frame[column], errors="coerce").dropna().tolist())
    for column in ("FromM", "ToM", "UP Track FromM", "UP Track ToM", "DN Track FromM", "DN Track ToM"):
        if column in boundaries.columns:
            values.extend(pd.to_numeric(boundaries[column], errors="coerce").dropna().tolist())
    return values


def _exception_group_ids(results: dict[str, pd.DataFrame]) -> list[Any]:
    """Return compact sample groups that must remain visible in an overview."""
    values: list[Any] = []
    for frame in results.values():
        if not isinstance(frame, pd.DataFrame) or "peak_group_id" not in frame.columns:
            continue
        values.extend(frame["peak_group_id"].dropna().tolist())
    return values

def _file_digest(path):
    digest = hashlib.sha256()
    if not Path(path).exists():
        # Unit-test loaders may provide an in-memory frame while mocking Path.exists.
        return hashlib.sha256(str(Path(path)).encode()).hexdigest()
    try:
        with open(path, "rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError:
        return hashlib.sha256(str(Path(path)).encode()).hexdigest()
    return digest.hexdigest()


def _snapshot_frame(snapshot):
    frame = snapshot.get("analysis_df", snapshot.get("raw_df"))
    return frame if isinstance(frame, pd.DataFrame) else pd.DataFrame()


def _assert_reportable(snapshot):
    if snapshot.get("analysis_mode") == "raw_overview":
        raise HTTPException(status_code=403, detail="Raw overview does not support exception report export")


def _validate_chart_mode(snapshot, mode):
    if snapshot.get("analysis_mode"):
        expected = "raw" if snapshot["analysis_mode"] == "raw_overview" else "chainage_median"
        if mode != expected:
            raise HTTPException(status_code=409, detail=f"This analysis uses {expected}; import again to change mode")


def _reload_overview_source(snapshot):
    path = Path(snapshot["source_path"])
    if not path.exists() or _file_digest(path) != snapshot["source_sha256"]:
        raise HTTPException(status_code=409, detail="Source file changed; import it again")
    params = snapshot["params"]
    is_csv = params.get("line") in LINE_WORKBOOKS and path.suffix.lower() != ".datac"
    frame = (TOV1050DataLoader() if is_csv else DataLoader()).load_data(str(path))
    if _file_digest(path) != snapshot["source_sha256"]:
        raise HTTPException(status_code=409, detail="Source file changed during reading; import it again")
    snapshot["source_stat"] = _source_stat(path)
    # A cold raw detail must preserve the same chart context as its overview.
    # Never infer it from the device's display line (e.g. RED LINE).
    if snapshot.get("metadata_path"):
        metadata_path = Path(snapshot["metadata_path"])
        if _file_digest(metadata_path) != snapshot.get("metadata_sha256"):
            raise HTTPException(status_code=409, detail="Metadata changed; import it again")
        manager = (TOV1050MetadataManager(metadata_path) if params.get("line") in LINE_WORKBOOKS
                   else MetadataManager(metadata_path))
        detector = ExceptionDetector(manager)
        session = params.get("session") or params.get("section")
        frame = detector._map_class_info(frame, params["line"], params["track"], session)
        frame = detector._map_track_info(frame, params["line"], session, params["track"])
        for column, value in {"line": params["line"], "branch": params.get("branch"), "track": params["track"], "Section": session,
                              "task_no": params.get("task_no"), "station_start": params.get("station_start"),
                              "station_end": params.get("station_end"), "task_run_date": params.get("date_str")}.items():
            frame[column] = value
        if _file_digest(metadata_path) != snapshot.get("metadata_sha256"):
            raise HTTPException(status_code=409, detail="Metadata changed during reading; import it again")
    _validate_raw_source(snapshot)
    return frame


def _source_stat(path):
    try:
        value = Path(path).stat()
        return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns
    except OSError as exc:
        raise HTTPException(status_code=409, detail="Source file unavailable; import it again") from exc


def _validate_raw_source(snapshot):
    """Cheap on every cache hit; a stat change requires a digest recheck."""
    if "source_sha256" not in snapshot:
        return  # Backwards-compatible in-memory/legacy snapshots.
    path = Path(snapshot["source_path"])
    current = _source_stat(path)
    if current != snapshot.get("source_stat"):
        if _file_digest(path) != snapshot["source_sha256"]:
            _release_chart_cache(snapshot)
            raise HTTPException(status_code=409, detail="Source file changed; import it again")
        snapshot["source_stat"] = current


def _release_chart_cache(snapshot):
    for source in snapshot.pop("chart_sources", {}).values():
        source.close()
    snapshot.pop("chart_windows", None)


def close_chart_caches():
    """Release temporary mmap files when the embedded server shuts down."""
    with STATE_LOCK:
        snapshots = list(ANALYSIS_SESSIONS.values())
    for snapshot in snapshots:
        with snapshot.setdefault("chart_lock", threading.RLock()):
            _release_chart_cache(snapshot)


def _snapshot_chart_payload(snapshot, mode, *, progress=None, request_ticket=None, queued_at=None, **sampling_kwargs):
    # A snapshot owns its cache/lock. Different tabs cannot share mutable state.
    with STATE_LOCK:
        lock = snapshot.setdefault("chart_lock", threading.RLock())
    with lock:
        started = time.monotonic()
        payload, resolution = _snapshot_chart_payload_locked(snapshot, mode, progress=progress,
                                                            request_ticket=request_ticket, **sampling_kwargs)
        if queued_at is not None:
            resolution = {**resolution, "server_queue_ms": 1000 * (started - queued_at),
                          "server_sampling_ms": 1000 * (time.monotonic() - started)}
        return payload, resolution


def _snapshot_chart_payload_locked(snapshot, mode, *, progress=None, request_ticket=None, **sampling_kwargs):
    """Cache one full derived chart per revision, before applying detail windows.

    Detail callers use DETAIL_LIMITER to serialize cache misses. Grouping the
    complete raw frame first preserves pass IDs and nonadjacent memberships.
    """
    _validate_chart_mode(snapshot, mode)
    def check_current():
        if request_ticket is not None and snapshot.get("chart_request_ticket") != request_ticket:
            raise HTTPException(status_code=409, detail={"code": "CHART_REQUEST_SUPERSEDED",
                                                        "message": "A newer chart viewport was requested"})
    check_current()
    is_raw = snapshot.get("analysis_mode") == "raw_overview"
    if is_raw:
        _validate_raw_source(snapshot)
    overview = sampling_kwargs.get("from_m") is None and sampling_kwargs.get("to_m") is None
    if overview and snapshot.get("overview_payload") is not None:
        return snapshot["overview_payload"], snapshot["overview_resolution"]
    aggregation = None
    sources = snapshot.setdefault("chart_sources", {})
    source = sources.get(mode)
    if source is not None and source.closed:
        sources.pop(mode)
        snapshot.pop("chart_windows", None)
        source = None
    frame = None
    if source is None:
        frame = _reload_overview_source(snapshot) if is_raw else _snapshot_frame(snapshot)
    columns = list(source.columns) if source is not None else _chart_columns(frame)
    if mode == "chainage_mean" and "analysis_mode" not in snapshot:
        frame = snapshot.get("mean_chart_frame")
        aggregation = snapshot.get("mean_chart_metadata")
        if frame is None:
            from app.core.chainage_aggregation import aggregate_chainage, CHANNELS
            derived, aggregation = aggregate_chainage(snapshot["raw_df"], progress=progress)
            statistics = [f"{channel}_{stat}" for channel in CHANNELS for stat in ("min", "max", "count")]
            provenance = ["group_id", "pass_id", "sample_count", "source_row_first", "source_row_last",
                          "SampleCount_first", "SampleCount_last"]
            selected = list(dict.fromkeys(c for c in [*columns, *statistics, *provenance] if c in derived))
            frame = derived[selected]
            snapshot["mean_chart_frame"], snapshot["mean_chart_metadata"] = frame, aggregation
        columns = frame.columns
    if source is None:
        source = ChartSource(frame, columns, numeric_columns=MEASUREMENT_COLUMNS,
                             disk=is_raw, ttl=RAW_CHART_TTL_SECONDS, lifecycle_lock=snapshot["chart_lock"])
        sources[mode] = source
        snapshot["chart_domain"] = source.domain
    from_m, to_m, empty = normalize_chart_window(source.domain, sampling_kwargs.get("from_m"), sampling_kwargs.get("to_m"))
    sampling_kwargs.update(from_m=from_m, to_m=to_m)
    key = (mode, from_m, to_m, sampling_kwargs.get("max_points", 6000))
    windows = snapshot.setdefault("chart_windows", WindowCache())
    cached = windows.get(key)
    if cached is not None:
        source.last_access = time.monotonic()
        check_current()
        return cached
    def chart_progress(*args):
        check_current()
        if progress:
            progress(*args)
    payload, resolution = build_chart_payload(source, columns, progress=chart_progress, **sampling_kwargs)
    if aggregation is not None:
        resolution.update(aggregation)
        resolution["display_mode"] = "chainage_mean"
    if snapshot.get("analysis_mode"):
        resolution["window_source_points"] = resolution["source_points"]
        resolution.update(display_mode=mode, **snapshot.get("aggregation_metadata", {}))
    resolution["chart_domain"] = source.domain
    if is_raw:
        _validate_raw_source(snapshot)
    check_current()
    if overview:
        snapshot["overview_payload"], snapshot["overview_resolution"] = payload, resolution
    else:
        windows.put(key, (payload, resolution))
    return payload, resolution


def _analyze_sync(request: AnalyzeRequest, progress=None, publish=None):
    """
    Core Analysis Endpoint.
    Loads data, applies metadata mapping, and detects exceptions.
    """
    global LAST_ANALYSIS_RESULTS, LAST_RAW_DF, LAST_ANALYSIS_PARAMS, LAST_ANALYSIS_SOURCE_PATH
    global LAST_METADATA_CAPABILITIES
    
    # 1. Validate Paths
    data_path = Path(request.file_path)
    if not data_path.exists():
        raise HTTPException(status_code=404, detail=f"Data file not found: {request.file_path}")
    
    source_context = {"line": request.line, "track": request.track,
                      "section": request.section, "session": request.session, "branch": request.branch}
    try:
        parent = normalize_line(request.line)
        identity = normalize_context(parent, branch=request.branch, direction=request.track,
                                     section=request.session or request.section)
        if not identity.branch or not identity.direction:
            raise ValueError("Analysis requires an explicit valid branch/section and direction")
        # Explicit session and Section must agree about the branch. Geographical
        # EAL RAC/LOW subdivisions keep their existing Section-specific rules.
        normalize_context(parent, branch=identity.branch, direction=request.track, section=request.section)
        is_tov1050 = parent in LINE_WORKBOOKS
        if is_tov1050:
            session = identity.legacy_session
            metadata_track_sheet(session, identity.wire_track)
        else:
            session = request.section or identity.legacy_session
        request = request.model_copy(update={"line": parent, "track": identity.wire_track,
                                             "branch": identity.branch, "session": session})
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # The form is the source of truth for TOV1050 context.  Real-world CSV
    # exports often have operational basenames (for example
    # ``20260817_022959_olpar.csv``) that are not report filenames.  Parse a
    # canonical basename only as a best-effort fallback for omitted fields.
    parsed_name = None
    if is_tov1050:
        try:
            parsed_name = parse_input_filename(data_path)
        except ValueError:
            logger.info("Ignoring non-canonical input basename: %s", data_path.name)
    station_start = request.station_start or (parsed_name.station_start if parsed_name else None)
    station_end = request.station_end or (parsed_name.station_end if parsed_name else None)
    # Cache the normalized context so every export uses the same inferred
    # session and station range as the analysis response.
    normalized_params = {
        **request.model_dump(),
        "session": session,
        "section": session if is_tov1050 else request.section,
        "station_start": station_start,
        "station_end": station_end,
        "branch": identity.branch, "direction": identity.direction,
        "source_context": source_context,
    }
    try:
        metadata_file = (
            metadata_workbook_for(request.line, session, CONFIG_DIR)
            if is_tov1050
            else CONFIG_DIR / f"{request.line} metadata.xlsx"
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not metadata_file.exists():
        raise HTTPException(status_code=404, detail=f"Metadata file not found: {metadata_file}")

    try:
        source_sha256, metadata_sha256 = _file_digest(data_path), _file_digest(metadata_file)
        # 2. Initialize Components
        loader = TOV1050DataLoader() if is_tov1050 and data_path.suffix.lower() != ".datac" else DataLoader()
        meta_mgr = TOV1050MetadataManager(metadata_file) if is_tov1050 else MetadataManager(metadata_file)
        detector = ExceptionDetector(meta_mgr)

        # 3. Load & Process Data
        if progress:
            progress("reading")
        df = (loader.load_data(str(data_path), progress=progress)
              if is_tov1050 and data_path.suffix.lower() != ".datac" and progress
              else loader.load_data(str(data_path)))
        
        # 3.1 Validate required columns
        if df.empty:
            raise HTTPException(
                status_code=400, 
                detail="The data file is empty or all rows were filtered out. Please check the file format."
            )
        
        if 'Chainage' not in df.columns:
            if not is_tov1050:
                missing_cols = [column for column in ('KM', 'LOCATION') if column not in df.columns]
                if missing_cols:
                    raise HTTPException(status_code=400, detail=f"The data file is missing required columns: {', '.join(missing_cols)}")
            raise HTTPException(status_code=400, detail="The data file has no valid Km values for Chainage.")

        # Form context is authoritative for both CSV and datac. Keep source
        # labels for diagnostics; they must never select metadata or reports.
        for column, selected, source in (
            ("Line", request.line, "source_line"),
            ("Track", request.track, "source_track"),
        ):
            if column in df.columns:
                df[source] = df[column].copy()
            df[column] = selected
            df[column.lower()] = selected

        metadata_capabilities = (
            meta_mgr.get_capabilities(request.line, session, request.track)
            if is_tov1050 else None
        )
        if metadata_capabilities:
            missing_required = [name for name in ("thresholds", "class_intervals", "track_intervals")
                                if metadata_capabilities["capabilities"][name]["status"] != "available"]
            if missing_required:
                raise ValueError(f"{metadata_file.name}/{request.line}/{session}/{request.track}: "
                                 f"required metadata unavailable: {', '.join(missing_required)}")
            meta_mgr.require_measurement_coverage(df['Chainage'], request.line, session, request.track)
        
        # Map context before reduction so different metadata intervals never merge.
        if progress:
            progress("metadata_mapping", 0, 2, "steps")
        mapped = detector._map_class_info(df, request.line, request.track, session)
        # A few legacy integrations provide a detector double that does not
        # return the frame from its mapping hook.  Keep the loaded frame in
        # that case; the production detector always returns a DataFrame.
        if isinstance(mapped, pd.DataFrame):
            df = mapped
        if progress:
            progress("metadata_mapping", 1, 2, "steps")
        mapped = detector._map_track_info(df, request.line, session, request.track)
        if isinstance(mapped, pd.DataFrame):
            df = mapped
        task_run_cols = {
            'task_run_date': request.date_str, 'line': request.line, 'track': request.track,
            'branch': identity.branch,
            'Section': session, 'task_no': request.task_no,
            'station_start': station_start, 'station_end': station_end,
        }
        for col, val in task_run_cols.items():
            df[col] = val
        source_points = len(df)
        mode = "raw" if request.analysis_mode == "raw_overview" else "chainage_median"
        normalized_params.update(analysis_mode=request.analysis_mode, chart_data_mode=mode)
        aggregation_metadata = {}
        if request.analysis_mode == "median":
            from app.core.chainage_reduction import reduce_chainage
            df, aggregation_metadata = reduce_chainage(df, progress=progress)
            results, boundary_df = detector.analyze(
                df, line=request.line, section=session, track=request.track,
                date_str=request.date_str, task_no=request.task_no,
                station_start=station_start, station_end=station_end,
                metadata_mapped=True,
                **({"progress": progress} if progress else {}))
        else:
            results = {}
            boundary_df = meta_mgr.get_boundaries_for_plot(request.line, request.track, session)
        if _file_digest(data_path) != source_sha256 or _file_digest(metadata_file) != metadata_sha256:
            raise HTTPException(status_code=409, detail="Source or metadata changed during analysis; import again")
        aggregation_metadata.update(source_sha256=source_sha256, metadata_sha256=metadata_sha256,
                                    source_points=source_points, representative_points=len(df),
                                    analysis_mode=request.analysis_mode)
        source_path = str(data_path.resolve())
        revision = uuid.uuid4().hex
        snapshot = {
            "results": results, "source_path": source_path, "source_sha256": source_sha256,
            "params": normalized_params, "metadata_capabilities": metadata_capabilities,
            "analysis_revision": revision, "analysis_mode": request.analysis_mode,
            "aggregation_metadata": aggregation_metadata,
            "metadata_path": str(metadata_file.resolve()), "metadata_sha256": metadata_sha256,
            "source_stat": _source_stat(data_path) if data_path.is_file() else None,
            "threshold_segments": build_threshold_segments(df, meta_mgr.get_all_thresholds()),
            "chart_lock": threading.RLock(),
        }
        if request.analysis_mode == "median":
            snapshot["analysis_df"] = df
            # Compatibility alias: this is the compact representative frame,
            # never the discarded full source frame.
            snapshot["raw_df"] = df
        else:
            # Only this local variable holds the complete raw frame.
            payload, resolution = build_chart_payload(df, _chart_columns(df), progress=progress)
            resolution.update(display_mode="raw", **aggregation_metadata)
            snapshot["overview_payload"], snapshot["overview_resolution"] = payload, resolution
            source = ChartSource(df, _chart_columns(df), numeric_columns=MEASUREMENT_COLUMNS,
                                 disk=True, ttl=RAW_CHART_TTL_SECONDS, lifecycle_lock=snapshot["chart_lock"])
            snapshot["chart_sources"] = {"raw": source}
            snapshot["chart_domain"] = source.domain
            resolution["chart_domain"] = source.domain
            del df

        # 5. Format Response
        def df_to_records(d: pd.DataFrame):
            return d.replace({np.nan: None}).to_dict(orient='records')
        
        formatted_results = {
            k: df_to_records(v) for k, v in results.items()
        }
        
        formatted_boundaries = df_to_records(boundary_df)
        
        # 6. Prepare Chart Data (Column-oriented for Plotly performance)
        # Phase 10.10.I: Inject Task Run Data into DataFrame for Catenary Report export
        if progress:
            progress("preparing_chart")
        chart_data, chart_resolution = _snapshot_chart_payload(
            snapshot, mode,
            preserve_chainage=_exception_chainages(results, boundary_df),
            preserve_group_ids=_exception_group_ids(results),
            **({"progress": progress} if progress else {}),
        )

        response = {
            "status": "success",
            "analysis_revision": revision,
            "analysis_mode": request.analysis_mode, "chart_view": mode,
            "aggregation_metadata": aggregation_metadata,
            "params": normalized_params,
            "exceptions": formatted_results,
            "boundaries": formatted_boundaries,
            "chart_data": chart_data,
            "chart_resolution": chart_resolution,
            "client_session_id": request.client_session_id,
            "cleaning_summary": getattr(loader, "last_cleaning_summary", None),
            "metadata_capabilities": metadata_capabilities,
            "chart_domain": snapshot.get("chart_domain"),
            "threshold_segments": snapshot.get("threshold_segments", []),
        }

        def commit():
            global LAST_ANALYSIS_RESULTS, LAST_RAW_DF, LAST_ANALYSIS_PARAMS, LAST_ANALYSIS_SOURCE_PATH
            global LAST_METADATA_CAPABILITIES, LAST_ANALYSIS_SNAPSHOT
            with STATE_LOCK:
                client_key = _session_key(request.client_session_id)
                # Published frames are immutable. Jobs retain old versions by reference.
                previous = ANALYSIS_SESSIONS.pop(client_key, None)
                if previous:
                    _release_chart_cache(previous)
                ANALYSIS_SESSIONS[client_key] = snapshot
                while len(ANALYSIS_SESSIONS) > MAX_ANALYSIS_SESSIONS:
                    _release_chart_cache(ANALYSIS_SESSIONS.pop(next(iter(ANALYSIS_SESSIONS))))
                LAST_ANALYSIS_RESULTS, LAST_RAW_DF = results, pd.DataFrame()
                LAST_ANALYSIS_SNAPSHOT = snapshot
                LAST_ANALYSIS_SOURCE_PATH, LAST_ANALYSIS_PARAMS = source_path, normalized_params
                LAST_METADATA_CAPABILITIES = metadata_capabilities
            return response
        return publish(commit) if publish else commit()

    except (JobCancelled, JobTimedOut):
        if "snapshot" in locals():
            _release_chart_cache(snapshot)
        raise
    except HTTPException:
        if "snapshot" in locals():
            _release_chart_cache(snapshot)
        # Re-raise HTTPException as-is (preserves 400, 404, etc.)
        raise
    except ValueError as e:
        if "snapshot" in locals():
            _release_chart_cache(snapshot)
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        if "snapshot" in locals():
            _release_chart_cache(snapshot)
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze")
async def analyze_data(request: AnalyzeRequest):
    return await run_in_threadpool(_analyze_sync, request)


def _require_snapshot(client_session_id, analysis_revision):
    if not client_session_id:
        raise HTTPException(status_code=422, detail="client_session_id is required")
    with STATE_LOCK:
        state = _state_for(client_session_id)
        if state is None or (_snapshot_frame(state).empty and state.get("analysis_mode") != "raw_overview"):
            raise HTTPException(status_code=410, detail="Analysis expired; run analysis again")
        if not analysis_revision or state.get("analysis_revision") != analysis_revision:
            raise HTTPException(status_code=409, detail="Analysis revision changed; use the completed analysis version")
        return state


def _job_error(exc):
    codes = {JobCapacityError: 429, JobMissing: 404, JobExpired: 410, JobNotReady: 409}
    raise HTTPException(status_code=codes[type(exc)], detail=str(exc)) from exc


@router.post("/analysis/jobs", status_code=202)
async def create_analysis_job(request: AnalyzeRequest):
    if not request.client_session_id or not request.client_session_id.strip():
        raise HTTPException(status_code=422, detail="client_session_id is required")
    try:
        return JOBS.submit("analysis", request.client_session_id,
                           lambda: lambda context: _analyze_sync(
                               request.model_copy(deep=True), context.progress, context.publish))
    except JobCapacityError as exc:
        _job_error(exc)


def _export_job_work(snapshot, mode):
    # No frame copy: completed analysis frames/results are immutable. Holding
    # this version pins it independently of session eviction or replacement.
    params = deepcopy(snapshot["params"])
    capabilities = deepcopy(snapshot.get("metadata_capabilities"))
    revision = snapshot["analysis_revision"]
    _assert_reportable(snapshot)
    _validate_chart_mode(snapshot, mode)
    raw_df, results = _snapshot_frame(snapshot), snapshot["results"]

    def work(context):
        context.progress("exporting", 0, len(raw_df), "rows")
        chart_df, statistics = raw_df, None
        metadata = {"analysis_revision": revision, "chart_data_mode": mode,
                    "raw_row_count": len(raw_df), **snapshot.get("aggregation_metadata", {})}
        metadata.update({key: params.get(key) for key in ("line", "branch", "direction", "track", "section",
                         "session", "date_str", "task_no", "station_start", "station_end") if params.get(key) is not None})
        if capabilities:
            metadata.update(metadata_capabilities=json.dumps(capabilities, ensure_ascii=False),
                            enrichment_version="tov640-first-nonempty-v1")
        if mode == "chainage_mean" and "analysis_mode" not in snapshot:
            from app.core.chainage_aggregation import aggregate_chainage
            chart_df, aggregation_metadata = aggregate_chainage(raw_df, progress=context.progress)
            statistics = chart_df
            metadata.update(aggregation_metadata)
            metadata["grouped_row_count"] = len(chart_df)
        output = context.output_path()
        export_analysis_report(results, chart_df=chart_df, metadata=metadata,
                               line=params.get("line", ""), output_path=output,
                               chart_statistics_df=statistics, progress=context.progress)
        context.check_cancelled()
        filename = generate_filename(
            date_str=params.get("date_str", "UnknownDate"), line=params.get("line", "UnknownLine"),
            track=params.get("track", "UnknownTrack"), section=params.get("section", "UnknownSection"),
            file_type="report", task_no=params.get("task_no"), station_start=params.get("station_start"),
            station_end=params.get("station_end"), session=params.get("session") or params.get("section"))
        if mode == "chainage_mean":
            filename = f"{Path(filename).stem}_ChainageMean.xlsx"
        context.job.path, context.job.filename = output, filename
        return {"analysis_revision": revision, "chart_data_mode": mode, "filename": filename}
    return work


@router.post("/export/report/jobs", status_code=202)
async def create_report_job(request: ReportJobRequest):
    try:
        def capture():
            with STATE_LOCK:
                snapshot = _require_snapshot(request.client_session_id, request.analysis_revision)
                return _export_job_work(snapshot, request.chart_data_mode)
        return JOBS.submit("export", request.client_session_id, capture, request.analysis_revision)
    except JobCapacityError as exc:
        _job_error(exc)


@router.get("/jobs/{job_id}")
async def get_job(job_id: str, client_session_id: str = Query(..., min_length=1)):
    try:
        with JOBS.lock:
            return JOBS.describe(JOBS.get(job_id, client_session_id))
    except (JobMissing, JobExpired) as exc:
        _job_error(exc)


@router.get("/jobs/{job_id}/result")
async def get_job_result(job_id: str, client_session_id: str = Query(..., min_length=1)):
    try:
        with JOBS.lock:
            job = JOBS.get(job_id, client_session_id)
            if job.status != "ready":
                raise JobNotReady(job.error or "Job has not completed")
            return job.result
    except (JobMissing, JobExpired, JobNotReady) as exc:
        _job_error(exc)


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str, client_session_id: str = Query(..., min_length=1)):
    try:
        return JOBS.cancel_job(job_id, client_session_id)
    except (JobMissing, JobExpired) as exc:
        _job_error(exc)


class _LeasedFileResponse(FileResponse):
    async def __call__(self, scope, receive, send):
        try:
            await super().__call__(scope, receive, send)
        finally:
            self._release()


@router.get("/jobs/{job_id}/download")
async def download_job(job_id: str, client_session_id: str = Query(..., min_length=1)):
    try:
        job = JOBS.acquire_download(job_id, client_session_id)
        response = _LeasedFileResponse(job.path, filename=job.filename,
                                      media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response._release = lambda: JOBS.release_download(job)
        return response
    except (JobMissing, JobExpired, JobNotReady) as exc:
        _job_error(exc)


@router.get("/analyze/chart-data")
async def get_chart_data(
    from_m: Optional[float] = Query(default=None, allow_inf_nan=False),
    to_m: Optional[float] = Query(default=None, allow_inf_nan=False),
    max_points: int = Query(default=6000, ge=500, le=100000),
    file_path: Optional[str] = Query(default=None),
    line: Optional[str] = Query(default=None),
    client_session_id: Optional[str] = Query(default=None),
    analysis_revision: Optional[str] = Query(default=None),
    chart_data_mode: Literal["raw", "chainage_mean", "chainage_median"] = Query(default="chainage_median"),
):
    """Return a higher-resolution chart window for the selected analysis tab.

    The desktop UI keeps multiple analysis results in separate tabs while the
    legacy backend cache stores only the most recent raw frame.  When a tab's
    source differs from that cache, reload its CSV locally so detail requests
    cannot display another tab's data.
    """
    try:
        from_m, to_m, _ = normalize_chart_window(None, from_m, to_m)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    state = _state_for(client_session_id)
    if client_session_id and state is None:
        raise HTTPException(status_code=410, detail="Analysis expired; run analysis again")
    if analysis_revision is not None:
        state = _require_snapshot(client_session_id, analysis_revision)
    elif state and state.get("analysis_revision"):
        raise HTTPException(status_code=409, detail="analysis_revision is required for this analysis")
    if state and state.get("analysis_mode"):
        _validate_chart_mode(state, chart_data_mode)
        key = (chart_data_mode, from_m, to_m, max_points)
        with STATE_LOCK:
            if state.get("chart_request_key") != key:
                state["chart_request_key"] = key
                state["chart_request_ticket"] = state.get("chart_request_ticket", 0) + 1
            ticket = state["chart_request_ticket"]
        payload, resolution = await anyio.to_thread.run_sync(
            partial(_snapshot_chart_payload, state, chart_data_mode, max_points=max_points,
                    from_m=from_m, to_m=to_m, request_ticket=ticket, queued_at=time.monotonic(),
                    preserve_chainage=_exception_chainages(state.get("results", {}), pd.DataFrame()),
                    preserve_group_ids=_exception_group_ids(state.get("results", {}))), limiter=DETAIL_LIMITER)
        _require_snapshot(client_session_id, analysis_revision)
        if state.get("chart_request_ticket") != ticket:
            raise HTTPException(status_code=409, detail={"code": "CHART_REQUEST_SUPERSEDED",
                                                        "message": "A newer chart viewport was requested"})
        return _chart_response(state, analysis_revision, payload, resolution)
    source_df = _snapshot_frame(state) if state is not None else LAST_RAW_DF
    cached_source_path = state.get("source_path") if state is not None else LAST_ANALYSIS_SOURCE_PATH
    if file_path and analysis_revision is None:
        requested_path = Path(file_path).resolve()
        cached_path = Path(cached_source_path).resolve() if cached_source_path else None
        if cached_path != requested_path:
            if not requested_path.exists():
                raise HTTPException(status_code=404, detail=f"Data file not found: {file_path}")
            is_tov1050 = (line or "").strip().upper() in LINE_WORKBOOKS
            loader = TOV1050DataLoader() if is_tov1050 else DataLoader()
            try:
                source_df = loader.load_data(str(requested_path))
            except Exception as exc:
                raise HTTPException(status_code=400, detail=f"Unable to load chart data: {exc}") from exc

    if source_df.empty:
        raise HTTPException(status_code=409, detail="No completed analysis is available")
    snapshot = state if state is not None and source_df is _snapshot_frame(state) else {"raw_df": source_df}
    chart_data, chart_resolution = await anyio.to_thread.run_sync(
        partial(_snapshot_chart_payload, snapshot, chart_data_mode, max_points=max_points,
                from_m=from_m, to_m=to_m, preserve_chainage=(), queued_at=time.monotonic()),
        limiter=DETAIL_LIMITER)
    return _chart_response(snapshot, analysis_revision, chart_data, chart_resolution)


def _chart_response(snapshot, revision, payload, resolution):
    return {"status": "success", "analysis_revision": revision, "chart_data": payload,
            "chart_resolution": resolution, "chart_domain": snapshot.get("chart_domain"),
            "threshold_segments": clip_threshold_segments(snapshot.get("threshold_segments", []),
                                                            resolution.get("from_m"), resolution.get("to_m"))}


@router.post("/analyze/chart-cache/release")
async def release_chart_cache(request: ReportJobRequest):
    snapshot = _require_snapshot(request.client_session_id, request.analysis_revision)
    with STATE_LOCK:
        snapshot["chart_request_ticket"] = snapshot.get("chart_request_ticket", 0) + 1
        snapshot.pop("chart_request_key", None)
    def release():
        with snapshot.setdefault("chart_lock", threading.RLock()):
            _release_chart_cache(snapshot)
    await run_in_threadpool(release)
    return {"status": "success"}


@router.post("/analyze/compare")
async def compare_history(files: List[UploadFile] = File(...)):
    """
    Compare multiple uploaded Analysis Reports using the "Chain Comparison" (Iterative) Method.
    """
    global LAST_COMPARE_RESULTS, LAST_COMPARE_FILES, LAST_ANALYSIS_PARAMS

    if not files or len(files) < 2:
        raise HTTPException(status_code=400, detail="Please upload at least 2 files to compare.")
    
    try:
        # 1. Sort files by date (Descending: Newest -> Oldest)
        def get_date(filename):
            match = re.search(r'(\d{8})', filename)
            return match.group(1) if match else "00000000"
        
        sorted_files = sorted(files, key=lambda f: get_date(f.filename), reverse=True)
        file_names = [f.filename for f in sorted_files]
        print(f"Comparing chain (Newest -> Oldest): {file_names}")

        def context_from_bytes(content, filename):
            from openpyxl import load_workbook
            workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
            sections = set()
            class ObservedSheet:
                def __init__(self, sheet):
                    self.sheet = sheet

                def iter_rows(self, **kwargs):
                    rows = self.sheet.iter_rows(**kwargs)
                    headers = next(rows, ())
                    yield headers
                    section_column = next((i for i, value in enumerate(headers)
                                           if str(value).strip().lower() == "section"), None)
                    for row in rows:
                        if section_column is not None and section_column < len(row) and row[section_column]:
                            sections.add(str(row[section_column]).strip().upper())
                        yield row

            class ObservedWorkbook:
                sheetnames = workbook.sheetnames

                def __getitem__(self, name):
                    return ObservedSheet(workbook[name])
            try:
                context = read_report_context(ObservedWorkbook(), filename, include_chart=True)
                if len(sections) > 1:
                    raise ReportContextError(f"{filename}: multiple Section values; compare each section separately.",
                                             "INCOMPATIBLE_REPORT_SCOPE")
                return context
            finally:
                workbook.close()

        contexts = []
        for uploaded in sorted_files:
            content = await uploaded.read()
            await uploaded.seek(0)
            contexts.append(await run_in_threadpool(context_from_bytes, content, uploaded.filename or ""))
        report_context = ensure_compatible_scopes(contexts, source="History Comparison")
        known_sections = {context.section.strip().upper() for context in contexts if context.section}
        if len(known_sections) > 1:
            raise ReportContextError("History Comparison: incompatible Section. Compare each section separately.",
                                     "INCOMPATIBLE_REPORT_SCOPE")
        algorithms_verified = validate_algorithm_compatibility(contexts)

        # Helper to load all sheets into one DF
        async def load_combined_df(file: UploadFile) -> pd.DataFrame:
            content = await file.read()
            await file.seek(0) 
            excel = pd.ExcelFile(io.BytesIO(content))
            
            dfs = []
            for sheet in excel.sheet_names:
                if sheet in ['Summary', 'Previous', 'Comparison Report', 'ChartData',
                             'ExceptionProvenance', 'ChainageStatistics'] or sheet.startswith('_'):
                    continue
                
                df = pd.read_excel(excel, sheet_name=sheet)
                if df.empty: continue
                
                # Phase 10.10.I: Normalize column names BEFORE checking for 'exception type'
                # This prevents "The column label 'exception type' is not unique" error
                column_renames = {
                    'ID': 'id',
                    'Exception Type': 'exception type',
                    'MaxValue': 'maxValue',
                    'MaxLocation': 'maxLocation',
                    'Length': 'length',
                    'Level': 'level',
                    'Run Date': 'task_run_date',
                    'Line': 'line',
                    'Track': 'track',
                    'Task No': 'task_no',
                    'St. Start': 'station_start',
                    'St. End': 'station_end',
                }
                df = df.rename(columns={k: v for k, v in column_renames.items() if k in df.columns})
                
                if 'exception type' not in df.columns:
                    df['exception type'] = sheet
                
                dfs.append(df)
            
            if not dfs:
                return pd.DataFrame()
            return pd.concat(dfs, ignore_index=True)

        async def load_chart_data(file: UploadFile) -> Optional[Dict[str, List]]:
            content = await file.read()
            await file.seek(0)
            excel = pd.ExcelFile(io.BytesIO(content))
            
            if 'ChartData' in excel.sheet_names:
                df = pd.read_excel(excel, sheet_name='ChartData')
                return df.replace({np.nan: None}).to_dict(orient='list')
            return None

        finder = RepeatedExceptionFinder()
        
        # 2. Initialize Accumulator with the Newest File (Index 0)
        accumulator_df = await load_combined_df(sorted_files[0])
        
        # Load Chart Data for ALL files
        all_charts = []
        for f in sorted_files:
            c_data = await load_chart_data(f)
            all_charts.append(c_data) # Can be None

        if accumulator_df.empty:
            return {"status": "success", "repeated": {}, "message": "Newest file is empty"}

        # 3. Chain Iteration
        for i in range(1, len(sorted_files)):
            prev_file = sorted_files[i]
            prev_df = await load_combined_df(prev_file)
            
            if prev_df.empty:
                accumulator_df = pd.DataFrame()
                break
            
            # Perform intersection with Newest as Base, Previous as Target
            # Label the matched ID as "Previous {i}"
            col_label = f"Previous {i}"
            accumulator_df = finder.find_repeated(accumulator_df, prev_df, new_id_label=col_label)
            
            # Survival Check
            if accumulator_df.empty:
                break
        
        # Cache for Export
        LAST_COMPARE_RESULTS = accumulator_df
        LAST_COMPARE_FILES = file_names
        
        # Workbook identity is authoritative; filename is only the reader's
        # validated fallback. Unknown legacy fields remain unknown.
        latest = contexts[0]
        LAST_ANALYSIS_PARAMS = {
            'date_str': latest.run_date, 'line': latest.line, 'track': latest.track,
            'section': latest.section, 'session': latest.legacy_session, 'branch': latest.branch,
            'task_no': latest.task_no, 'station_start': latest.station_start, 'station_end': latest.station_end,
        }
        
        # 4. Process Results & Stats
        final_results = {}
        stats_breakdown = {}
        
        if not accumulator_df.empty:
            # Group by exception type
            for exc_type, group in accumulator_df.groupby('exception type'):
                # Stats
                stats_breakdown[exc_type] = len(group)
                
                # Replace NaNs
                recs = group.replace({np.nan: None}).to_dict(orient='records')
                final_results[exc_type] = recs

        # Calculate Total
        total_count = sum(stats_breakdown.values())

        return {
            "status": "success",
            "repeated": final_results,
            "stats": {
                "total": total_count,
                "breakdown": stats_breakdown
            },
            "chain_order": file_names,
            "chart_data": all_charts,
            "context": {"line": report_context.line, "branch": report_context.branch,
                         "direction": report_context.direction, "section": report_context.section},
            "algorithm_provenance": "verified" if algorithms_verified else "unknown",
        }

    except ReportContextError as exc:
        raise HTTPException(status_code=422, detail=exc.detail()) from exc
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/export/compare/generate")
async def generate_compare_report(request: GenerateExportRequest):
    """
    Generate Excel report from frontend data (WYSIWYG).
    """
    try:
        # 1. Convert list of dicts to DataFrame
        df = pd.DataFrame(request.data)
        
        # 2. Determine Filename
        date_s = "UnknownDate"
        line = "UnknownLine"
        track = "UnknownTrack"
        section = "UnknownSection"

        # Try to get from Metadata first
        if request.metadata:
            passed_filename = request.metadata.get('filename')
            if passed_filename:
                parts = passed_filename.split('_')
                if len(parts) >= 3:
                    date_s = parts[0]
                    line = parts[1]
                    track = parts[2]
                    if len(parts) >= 4 and 'Exception' not in parts[3]:
                        section = parts[3]
            
            if 'date_str' in request.metadata: date_s = request.metadata['date_str']
            if 'line' in request.metadata: line = request.metadata['line']
            if 'track' in request.metadata: track = request.metadata['track']
            if 'section' in request.metadata: section = request.metadata['section']

        # Extract optional fields for custom naming
        task_no = request.metadata.get('task_no') if request.metadata else None
        station_start = request.metadata.get('station_start') if request.metadata else None
        station_end = request.metadata.get('station_end') if request.metadata else None

        # Fallback
        if not request.metadata or date_s == "UnknownDate":
            if not df.empty:
                first_row = df.iloc[0]
                for col in ['check_date', 'verify_date', 'adjust_date', 'DATE']:
                    if col in first_row and first_row[col]:
                        val = str(first_row[col])
                        date_s = val.replace('-', '').replace('/', '')[:8] 
                        break

        # Calculate file count from columns (Previous X) + 1 (Latest)
        prev_cols = [c for c in df.columns if c.startswith('Previous ') and 'ID' in c or (len(c.split(' '))==2 and c.split(' ')[1].isdigit())]
        # De-duplicate if needed, but columns are unique.
        # Actually, best proxy for file count is max previous index + 1
        max_prev = 0
        for col in df.columns:
            if col.startswith('Previous '):
                parts = col.split(' ')
                if len(parts) >= 2 and parts[1].isdigit():
                    idx = int(parts[1])
                    if idx > max_prev: max_prev = idx
        
        file_count = max_prev + 1
        if file_count == 1 and not any(c.startswith('Previous') for c in df.columns):
            # Fallback if no previous columns found (shouldn't happen in compare export)
            file_count = 1 

        filename = generate_filename(
            date_str=date_s,
            line=line,
            track=track,
            section=section,
            file_type='repeated',
            file_count=file_count,
            task_no=task_no,
            station_start=station_start,
            station_end=station_end,
            session=request.metadata.get('session') if request.metadata else None,
        )

        # 3. Generate Excel
        excel_file = ExcelExporter.export_history_compare(df, file_names=[])
        
        encoded_filename = urllib.parse.quote(filename)
        
        headers = {
            'Content-Disposition': f'attachment; filename="{filename}"; filename*=utf-8\'\'{encoded_filename}'
        }
        return StreamingResponse(
            excel_file, 
            headers=headers, 
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/export/compare")
async def export_compare_report():
    """
    Download the last comparison result.
    """
    if LAST_COMPARE_RESULTS.empty:
        raise HTTPException(status_code=400, detail="No comparison results available. Run comparison first.")
    
    try:
        excel_file = ExcelExporter.export_history_compare(LAST_COMPARE_RESULTS, LAST_COMPARE_FILES)
        
        p = LAST_ANALYSIS_PARAMS
        date_s = p.get('date_str', 'UnknownDate')
        line = p.get('line', 'UnknownLine')
        track = p.get('track', 'UnknownTrack')
        section = p.get('section', 'UnknownSection')
        count = len(LAST_COMPARE_RESULTS) # Row count
        file_count = len(LAST_COMPARE_FILES) # File count
        
        filename = generate_filename(
            date_str=date_s,
            line=line,
            track=track,
            section=section,
            file_type='repeated',
            file_count=file_count,
            task_no=p.get('task_no'),
            station_start=p.get('station_start'),
            station_end=p.get('station_end'),
            session=(p.get('session') or (p.get('section') if str(line).strip().upper() in LINE_WORKBOOKS else None))
        )
        encoded_filename = urllib.parse.quote(filename)
        
        headers = {
            'Content-Disposition': f'attachment; filename="{filename}"; filename*=utf-8\'\'{encoded_filename}'
        }
        return StreamingResponse(excel_file, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/export/report")
async def export_report():
    """
    Download the last analysis result.
    """
    if LAST_ANALYSIS_SNAPSHOT:
        _assert_reportable(LAST_ANALYSIS_SNAPSHOT)
    if not LAST_ANALYSIS_RESULTS:
        raise HTTPException(status_code=400, detail="No analysis results available. Run analysis first.")
    
    try:
        report_metadata = ({
            "metadata_capabilities": json.dumps(LAST_METADATA_CAPABILITIES, ensure_ascii=False),
            "enrichment_version": "tov640-first-nonempty-v1",
        } if LAST_METADATA_CAPABILITIES else None)
        if LAST_ANALYSIS_SNAPSHOT:
            report_metadata = {**(report_metadata or {}), **LAST_ANALYSIS_SNAPSHOT.get("aggregation_metadata", {})}
        excel_file = export_analysis_report(LAST_ANALYSIS_RESULTS, chart_df=(_snapshot_frame(LAST_ANALYSIS_SNAPSHOT) if LAST_ANALYSIS_SNAPSHOT else LAST_RAW_DF),
                                           metadata=report_metadata, line=LAST_ANALYSIS_PARAMS.get('line', ''))
        
        p = LAST_ANALYSIS_PARAMS
        date_s = p.get('date_str', 'UnknownDate')
        line = p.get('line', 'UnknownLine')
        track = p.get('track', 'UnknownTrack')
        section = p.get('section', 'UnknownSection')
        
        filename = generate_filename(
            date_str=date_s,
            line=line,
            track=track,
            section=section,
            file_type='report',
            task_no=p.get('task_no'),
            station_start=p.get('station_start'),
            station_end=p.get('station_end'),
            session=p.get('session') or p.get('section')
        )
        encoded_filename = urllib.parse.quote(filename)
        
        headers = {
            'Content-Disposition': f'attachment; filename="{filename}"; filename*=utf-8\'\'{encoded_filename}'
        }
        return StreamingResponse(_download_body(excel_file, line), headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/export/report/generate")
async def generate_report_from_data(request: GenerateAnalysisReportRequest):
    """
    Generate Analysis Report from frontend data (Stateful-Safe).
    """
    try:
        # Prefer the complete raw frame captured for this analysis tab.  The
        # chart payload is intentionally downsampled for rendering and must
        # not become the report's raw ChartData.
        chart_df = None
        state = _state_for(request.client_session_id)
        if state is not None:
            _assert_reportable(state)
            chart_df = _snapshot_frame(state)
        elif request.client_session_id:
            raise HTTPException(status_code=410, detail="Analysis expired; run analysis again before exporting")
        elif request.chart_data:
            chart_df = pd.DataFrame(request.chart_data)
        
        # Generate Excel
        report_metadata = None
        if state and state.get("metadata_capabilities"):
            report_metadata = {
                "metadata_capabilities": json.dumps(state["metadata_capabilities"], ensure_ascii=False),
                "enrichment_version": "tov640-first-nonempty-v1",
            }
        if state:
            report_metadata = {**(report_metadata or {}), **state.get("aggregation_metadata", {})}
        export_params = {**(state.get("params", {}) if state else {}), **request.params}
        excel_file = await run_in_threadpool(export_analysis_report, state["results"] if state else request.exceptions, chart_df=chart_df,
                                             metadata=report_metadata, line=export_params.get('line', ''))
        
        # Construct Filename from params using conditional naming logic
        p = export_params
        date_s = p.get('date_str', 'UnknownDate')
        line = p.get('line', 'UnknownLine')
        track = p.get('track', 'UnknownTrack')
        section = p.get('section', 'UnknownSection')
        
        filename_args = dict(
            date_str=date_s,
            line=line,
            track=track,
            section=section,
            file_type='report',
            task_no=p.get('task_no'),
            station_start=p.get('station_start'),
            station_end=p.get('station_end'),
            session=(p.get('session') or (p.get('section') if str(line).strip().upper() in LINE_WORKBOOKS else None)),
        )
        try:
            filename = generate_filename(**filename_args)
        except ValueError as exc:
            # Stateful exports normally carry the station range captured at
            # import.  Legacy callers may submit only line/track/section;
            # preserve their export by using the documented default name.
            if "requires station_start and station_end" not in str(exc):
                raise
            # TOV1050's canonical name requires a station range.  If a
            # legacy caller omitted it, emit the same safe default shape used
            # by the non-TOV exporter instead of failing after the workbook
            # has already been generated.
            filename = f"{date_s}_{line}_{track}_{section}_Exception_Report.xlsx"
        
        # Encode filename
        encoded_filename = urllib.parse.quote(filename)
        
        headers = {
            'Content-Disposition': f'attachment; filename="{filename}"; filename*=utf-8\'\'{encoded_filename}'
        }
        return StreamingResponse(
            _download_body(excel_file, line),
            headers=headers, 
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/export/raw")
async def export_raw_data(
    date_str: Optional[str] = Query(None),
    line: Optional[str] = Query(None),
    track: Optional[str] = Query(None),
    section: Optional[str] = Query(None)
):
    """
    Download the last cleaned raw data.
    """
    if LAST_ANALYSIS_SNAPSHOT:
        _assert_reportable(LAST_ANALYSIS_SNAPSHOT)
    # Keep the legacy global cache usable for callers that populated it
    # directly (older clients and integrations do not publish a snapshot).
    # A committed analysis clears LAST_RAW_DF, so a non-empty value here is
    # an explicit legacy export source and must take precedence over any
    # stale snapshot left by an earlier request.
    export_frame = (LAST_RAW_DF if isinstance(LAST_RAW_DF, pd.DataFrame) and not LAST_RAW_DF.empty
                    else _snapshot_frame(LAST_ANALYSIS_SNAPSHOT) if LAST_ANALYSIS_SNAPSHOT
                    else LAST_RAW_DF)
    if export_frame.empty:
        raise HTTPException(status_code=400, detail="No data available. Run analysis first.")
        
    try:
        csv_file = await run_in_threadpool(ExcelExporter.export_raw_csv, export_frame)
        
        p = LAST_ANALYSIS_PARAMS.copy()
        
        # Override if params provided
        if date_str: p['date_str'] = date_str
        if line: p['line'] = line
        if track: p['track'] = track
        if section: p['section'] = section
        
        date_s = p.get('date_str', 'UnknownDate')
        line_val = p.get('line', 'UnknownLine')
        track_val = p.get('track', 'UnknownTrack')
        section_val = p.get('section', 'UnknownSection')
        
        filename = generate_filename(
            date_str=date_s,
            line=line_val,
            track=track_val,
            section=section_val,
            file_type='raw',
            task_no=p.get('task_no'),
            station_start=p.get('station_start'),
            station_end=p.get('station_end'),
            session=p.get('session')
        )
        encoded_filename = urllib.parse.quote(filename)
        
        headers = {
            'Content-Disposition': f'attachment; filename="{filename}"; filename*=utf-8\'\'{encoded_filename}'
        }
        return StreamingResponse(_download_body(csv_file, LAST_ANALYSIS_PARAMS.get('line', '')), headers=headers, media_type='text/csv')
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# BUG 10.7-2 FIX: POST endpoint for raw data export
# This endpoint accepts data directly from the frontend, solving the issue where
# multi-tab export uses the wrong data due to global variable overwrite.
#
# BUG 10.8-2 FIX: Accept both column-oriented and row-oriented chart_data formats
# - Column-oriented (from /analyze): {"Chainage": [100, 101], "height1": [5000, 5100]}
# - Row-oriented (alternative): [{"Chainage": 100, "height1": 5000}, ...]
# =============================================================================

class ExportRawRequest(BaseModel):
    """
    Request model for POST /export/raw/generate endpoint.
    
    BUG 10.8-2 FIX: Accept both formats:
    - Column-oriented (Dict[str, List]): {"col1": [v1, v2], "col2": [v3, v4]}
    - Row-oriented (List[Dict]): [{"col1": v1, "col2": v3}, {"col1": v2, "col2": v4}]
    """
    # Optional for session-scoped exports.  The preferred contract is to send
    # client_session_id and let the backend retrieve the complete raw frame;
    # chart_data remains a backwards-compatible fallback for older clients.
    chart_data: Optional[Union[Dict[str, List[Any]], List[Dict[str, Any]]]] = None
    params: Dict[str, Any]
    client_session_id: Optional[str] = None


@router.post("/export/raw/generate")
async def export_raw_data_generate(request: ExportRawRequest):
    """
    Export raw data to CSV using data provided in the request body.
    
    BUG 10.7-2 FIX: This endpoint solves the multi-tab export issue where the
    global LAST_RAW_DF variable is overwritten by subsequent analysis calls.
    Instead of using global state, this endpoint accepts the data directly
    from the frontend, ensuring each tab exports its own data.
    
    BUG 10.8-2 FIX: Now accepts both column-oriented and row-oriented formats.
    
    Request body (column-oriented - from /analyze endpoint):
    {
        "chart_data": {"Chainage": [100, 101], "height1": [5000, 5100]},
        "params": { ... }
    }
    
    Request body (row-oriented - alternative):
    {
        "chart_data": [{"Chainage": 100, "height1": 5000}, ...],
        "params": { ... }
    }
    
    Returns:
        StreamingResponse with CSV file
    """
    try:
        # Prefer the complete raw frame captured for this analysis tab.  The
        # frontend chart payload may be envelope-sampled, so it is only a
        # backward-compatible fallback when no tab state exists.
        state = _state_for(request.client_session_id)
        if state is not None and not _snapshot_frame(state).empty:
            _assert_reportable(state)
            df = _snapshot_frame(state)
        elif state and state.get("analysis_mode") == "raw_overview":
            raise HTTPException(status_code=403, detail="CSV export is disabled in raw overview")
        elif request.client_session_id:
            raise HTTPException(status_code=410, detail="Analysis expired; run analysis again before exporting")
        else:
            # BUG 10.8-2: Check for empty fallback data (both formats)
            if request.client_session_id is None and request.chart_data is None:
                # Preserve the validation contract for legacy clients that do
                # not provide either a tab identity or payload.
                raise HTTPException(status_code=422, detail="chart_data is required for legacy export")
            if not request.chart_data:
                raise HTTPException(status_code=400, detail="No data provided for export.")
            if isinstance(request.chart_data, dict) and len(request.chart_data) == 0:
                raise HTTPException(status_code=400, detail="No data provided for export.")
            # BUG 10.8-2: Handle both column-oriented and row-oriented formats
            # Both formats can be passed directly to pd.DataFrame()
            df = pd.DataFrame(request.chart_data)
        
        # Export to CSV
        csv_file = await run_in_threadpool(ExcelExporter.export_raw_csv, df)
        
        # Extract parameters for filename generation
        p = request.params
        date_s = p.get('date_str', 'UnknownDate')
        line_val = p.get('line', 'UnknownLine')
        track_val = p.get('track', 'UnknownTrack')
        section_val = p.get('section', 'UnknownSection')
        
        # Generate filename using the provided parameters
        filename = generate_filename(
            date_str=date_s,
            line=line_val,
            track=track_val,
            section=section_val,
            file_type='raw',
            task_no=p.get('task_no'),
            station_start=p.get('station_start'),
            station_end=p.get('station_end'),
            session=p.get('session')
        )
        
        encoded_filename = urllib.parse.quote(filename)
        
        headers = {
            'Content-Disposition': f'attachment; filename="{filename}"; filename*=utf-8\'\'{encoded_filename}'
        }
        
        logger.info(f"[BUG 10.7-2] Raw export generated: {filename} with {len(df)} rows")
        
        return StreamingResponse(_download_body(csv_file, line_val), headers=headers, media_type='text/csv')
        
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.error(f"[BUG 10.7-2] Raw export failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
