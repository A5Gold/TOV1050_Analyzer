from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from pathlib import Path
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Union
import io
import re
import urllib.parse
import logging

from app.core.data_ingestion import DataLoader
from app.core.tov1050_contract import (
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
from app.core.repeated_finder import RepeatedExceptionFinder

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()

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
    tov1050_lines = {"AEL", "TCL", "DRL", "ISL", "KTL", "TKL", "TWL"}
    # TOV1050 exports must always carry the selected session and station range.
    if str(line).strip().upper() in tov1050_lines and not session:
        raise ValueError("TOV1050 export requires an explicit session")
    if str(line).strip().upper() in tov1050_lines and (not station_start or not station_end):
        raise ValueError("TOV1050 export requires station_start and station_end")

    # TOV1050 format is selected when a session is present.
    if session:
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
LAST_COMPARE_RESULTS = pd.DataFrame()
LAST_COMPARE_FILES = []
LAST_ANALYSIS_PARAMS = {} # Store context for file naming

# Define Request Model
class AnalyzeRequest(BaseModel):
    file_path: str
    line: str      # e.g., "EAL", "TML"
    section: str   # e.g., "Mainline", "LMC"
    track: str     # e.g., "UP", "DN"
    date_str: str  # e.g., "20251212"
    session: Optional[str] = None  # Mainline, PL, or TKS
    # Optional fields for custom file naming
    task_no: Optional[str] = None        # e.g., "U1", "D3", "S1"
    station_start: Optional[str] = None  # e.g., "HUH", "LOW"
    station_end: Optional[str] = None    # e.g., "RAC", "SHA"

class GenerateExportRequest(BaseModel):
    data: List[Dict[str, Any]]
    metadata: Optional[Dict[str, Any]] = {}

class GenerateAnalysisReportRequest(BaseModel):
    exceptions: Dict[str, Any]
    chart_data: Optional[Dict[str, List[Any]]] = None
    params: Dict[str, Any]

# Define Paths - Handle both development and PyInstaller frozen modes
import sys
from app.core.config import get_config_dir

CONFIG_DIR = get_config_dir()
logger.info(f"[Analysis] CONFIG_DIR initialized: {CONFIG_DIR.absolute()}")

@router.post("/analyze")
async def analyze_data(request: AnalyzeRequest):
    """
    Core Analysis Endpoint.
    Loads data, applies metadata mapping, and detects exceptions.
    """
    global LAST_ANALYSIS_RESULTS, LAST_RAW_DF, LAST_ANALYSIS_PARAMS
    
    # 1. Validate Paths
    data_path = Path(request.file_path)
    if not data_path.exists():
        raise HTTPException(status_code=404, detail=f"Data file not found: {request.file_path}")
    
    is_tov1050 = request.line.strip().upper() in {"AEL", "TCL", "DRL", "ISL", "KTL", "TKL", "TWL"}
    try:
        if is_tov1050:
            session = normalize_session(request.session or request.section or "Mainline")
            metadata_track_sheet(session, request.track)
        else:
            session = request.session or request.section or "Mainline"
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
    LAST_ANALYSIS_PARAMS = {
        **request.model_dump(),
        "session": session,
        "station_start": station_start,
        "station_end": station_end,
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
        # 2. Initialize Components
        loader = TOV1050DataLoader() if is_tov1050 else DataLoader()
        meta_mgr = TOV1050MetadataManager(metadata_file) if is_tov1050 else MetadataManager(metadata_file)
        detector = ExceptionDetector(meta_mgr)

        # 3. Load & Process Data
        df = loader.load_data(str(data_path))
        
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

        # TOV1050 has no Track column in the raw CSV; preserve the selected
        # direction as context for the copied detector/exporter contract.
        if is_tov1050:
            df['Track'] = request.track
        
        # 4. Run Analysis
        results, boundary_df = detector.analyze(
            df, 
            line=request.line, 
            section=session,
            track=request.track,
            date_str=request.date_str,
            task_no=request.task_no,
            station_start=station_start,
            station_end=station_end
        )
        
        # Cache results for export
        LAST_ANALYSIS_RESULTS = results
        LAST_RAW_DF = df
        
        # 5. Format Response
        def df_to_records(d: pd.DataFrame):
            return d.replace({np.nan: None}).to_dict(orient='records')
        
        formatted_results = {
            k: df_to_records(v) for k, v in results.items()
        }
        
        formatted_boundaries = df_to_records(boundary_df)
        
        # 6. Prepare Chart Data (Column-oriented for Plotly performance)
        # Phase 10.10.I: Inject Task Run Data into DataFrame for Catenary Report export
        task_run_cols = {
            'task_run_date': request.date_str,
            'line': request.line,
            'track': request.track,
            'Section': session,
            'task_no': request.task_no,
            'station_start': station_start,
            'station_end': station_end,
        }
        for col, val in task_run_cols.items():
            if col not in df.columns:
                df[col] = val

        plot_cols = ['Chainage']
        plot_cols += [c for c in df.columns if 'height' in c]
        plot_cols += [c for c in df.columns if 'stagger' in c]
        plot_cols += [c for c in df.columns if 'wear' in c]
        # Phase 10.10.I: 新增 metadata 和 computed 欄位
        metadata_cols = ['Track Type', 'Overlap', 'Tension Length', 'Landmark', 'Class']
        plot_cols += [c for c in metadata_cols if c in df.columns]
        computed_cols = ['stg_max', 'stg_min']
        plot_cols += [c for c in computed_cols if c in df.columns]
        
        # Phase 10.10.I: Add Task Run Data columns
        plot_cols += [c for c in task_run_cols.keys() if c in df.columns]
        
        valid_plot_cols = [c for c in plot_cols if c in df.columns]
        # De-duplicate
        valid_plot_cols = list(dict.fromkeys(valid_plot_cols))
        
        chart_data = df[valid_plot_cols].replace({np.nan: None}).to_dict(orient='list')

        return {
            "status": "success",
            "params": {**request.model_dump(), "session": session, "station_start": station_start, "station_end": station_end},
            "exceptions": formatted_results,
            "boundaries": formatted_boundaries,
            "chart_data": chart_data,
            "cleaning_summary": getattr(loader, "last_cleaning_summary", None),
        }

    except HTTPException:
        # Re-raise HTTPException as-is (preserves 400, 404, etc.)
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
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

        # Helper to load all sheets into one DF
        async def load_combined_df(file: UploadFile) -> pd.DataFrame:
            content = await file.read()
            await file.seek(0) 
            excel = pd.ExcelFile(io.BytesIO(content))
            
            dfs = []
            for sheet in excel.sheet_names:
                if sheet in ['Summary', 'Previous', 'Comparison Report', 'ChartData']: continue
                
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
        
        # Try to infer params from the newest file (Slot 1)
        try:
            latest_name = file_names[0]
            parts = latest_name.split('_')
            if len(parts) >= 4:
                LAST_ANALYSIS_PARAMS = {
                    'date_str': parts[0],
                    'line': parts[1],
                    'track': parts[2],
                    'section': parts[3] # Approximation
                }
        except:
            pass
        
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
            "chart_data": all_charts # Return List of chart data
        }

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
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
            session=p.get('session')
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
    if not LAST_ANALYSIS_RESULTS:
        raise HTTPException(status_code=400, detail="No analysis results available. Run analysis first.")
    
    try:
        excel_file = ExcelExporter.export_report(LAST_ANALYSIS_RESULTS, chart_df=LAST_RAW_DF)
        
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
            session=p.get('session')
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

@router.post("/export/report/generate")
async def generate_report_from_data(request: GenerateAnalysisReportRequest):
    """
    Generate Analysis Report from frontend data (Stateful-Safe).
    """
    try:
        # Convert chart_data back to DataFrame if present
        chart_df = None
        if request.chart_data:
            chart_df = pd.DataFrame(request.chart_data)
        
        # Generate Excel
        excel_file = ExcelExporter.export_report(request.exceptions, chart_df=chart_df)
        
        # Construct Filename from params using conditional naming logic
        p = request.params
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
            session=p.get('session')
        )
        
        # Encode filename
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
    if LAST_RAW_DF.empty:
        raise HTTPException(status_code=400, detail="No raw data available. Run analysis first.")
        
    try:
        csv_file = ExcelExporter.export_raw_csv(LAST_RAW_DF)
        
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
        return StreamingResponse(csv_file, headers=headers, media_type='text/csv')
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
    chart_data: Union[Dict[str, List[Any]], List[Dict[str, Any]]]
    params: Dict[str, Any]


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
    # BUG 10.8-2: Check for empty data (both formats)
    if not request.chart_data:
        raise HTTPException(status_code=400, detail="No data provided for export.")
    
    # Handle empty dict for column-oriented format
    if isinstance(request.chart_data, dict) and len(request.chart_data) == 0:
        raise HTTPException(status_code=400, detail="No data provided for export.")
    
    try:
        # BUG 10.8-2: Handle both column-oriented and row-oriented formats
        # Both formats can be passed directly to pd.DataFrame()
        df = pd.DataFrame(request.chart_data)
        
        # Export to CSV
        csv_file = ExcelExporter.export_raw_csv(df)
        
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
        
        return StreamingResponse(csv_file, headers=headers, media_type='text/csv')
        
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.error(f"[BUG 10.7-2] Raw export failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
