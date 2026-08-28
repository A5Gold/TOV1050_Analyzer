"""
TOV640 Analyzer - Sessions API Router
======================================
Stateful Transformation API endpoints for managing historical analysis sessions.

Endpoints:
- GET /api/sessions - Query analysis sessions list
- GET /api/sessions/{session_id} - Get single session details
- GET /api/sessions/{session_id}/exceptions - Get session exceptions list
- PATCH /api/exceptions/{exception_id}/status - Update exception status

Version: 1.0
Date: 2026-01-30
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, field_validator
from typing import Dict, List, Optional, Any, Literal
import logging

from app.core.database import (
    get_database,
    get_sessions,
    get_session_by_id,
    get_session_exceptions,
    update_exception_status,
)

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()

# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class UpdateExceptionStatusRequest(BaseModel):
    """Request model for updating exception status."""
    status: Literal['pending', 'in_progress', 'resolved', 'deferred', 'false_positive']
    notes: Optional[str] = None
    assigned_to: Optional[str] = None
    resolved_by: Optional[str] = None
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v: str) -> str:
        allowed = ['pending', 'in_progress', 'resolved', 'deferred', 'false_positive']
        if v not in allowed:
            raise ValueError(f"status must be one of: {', '.join(allowed)}")
        return v


class SessionResponse(BaseModel):
    """Response model for session data."""
    status: str
    session: Dict[str, Any]


class SessionsListResponse(BaseModel):
    """Response model for sessions list."""
    status: str
    total: int
    sessions: List[Dict[str, Any]]


class ExceptionsListResponse(BaseModel):
    """Response model for exceptions list."""
    status: str
    total: int
    exceptions: List[Dict[str, Any]]


class SuccessResponse(BaseModel):
    """Generic success response."""
    status: str
    message: str


# =============================================================================
# API ENDPOINTS
# =============================================================================

@router.get("/sessions", response_model=SessionsListResponse)
async def list_sessions(
    line: Optional[str] = Query(None, description="Filter by line (EAL/TML)"),
    track: Optional[str] = Query(None, description="Filter by track (UP/DOWN)"),
    section: Optional[str] = Query(None, description="Filter by section"),
    date_from: Optional[str] = Query(None, description="Filter by start date (YYYYMMDD)"),
    date_to: Optional[str] = Query(None, description="Filter by end date (YYYYMMDD)"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=500, description="Maximum results (1-500)"),
    offset: int = Query(0, ge=0, description="Pagination offset")
) -> SessionsListResponse:
    """
    Query historical analysis sessions with optional filters.
    
    Returns a paginated list of sessions with exception statistics.
    
    **Filters:**
    - `line`: Filter by line code (e.g., 'EAL', 'TML')
    - `track`: Filter by track (e.g., 'UP', 'DOWN')
    - `section`: Filter by section (e.g., 'Mainline', 'LMC')
    - `date_from`: Start date in YYYYMMDD format
    - `date_to`: End date in YYYYMMDD format
    - `status`: Session status filter
    
    **Pagination:**
    - `limit`: Max 500 results per request
    - `offset`: Skip N results
    """
    try:
        # Build filters dict
        filters: Dict[str, Any] = {}
        if line:
            filters['line'] = line
        if track:
            filters['track'] = track
        if section:
            filters['section'] = section
        if date_from:
            filters['date_from'] = date_from
        if date_to:
            filters['date_to'] = date_to
        if status:
            filters['status'] = status
        
        # Query database
        db = get_database()
        with db.get_connection() as conn:
            sessions = get_sessions(
                conn, 
                filters=filters if filters else None,
                limit=limit,
                offset=offset
            )
        
        return SessionsListResponse(
            status="success",
            total=len(sessions),
            sessions=sessions
        )
    
    except Exception as e:
        logger.error(f"Error querying sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str) -> SessionResponse:
    """
    Get detailed information for a single analysis session.
    
    Returns session metadata along with exception statistics from the view.
    
    **Response includes:**
    - Session metadata (line, track, section, date_str, etc.)
    - Exception counts by level (l1_count, l2_count, l3_count)
    - Total exception count
    - Session status and timestamps
    """
    try:
        db = get_database()
        with db.get_connection() as conn:
            session = get_session_by_id(conn, session_id)
        
        if not session:
            raise HTTPException(
                status_code=404, 
                detail=f"Session not found: {session_id}"
            )
        
        return SessionResponse(
            status="success",
            session=session
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/exceptions", response_model=ExceptionsListResponse)
async def get_exceptions_for_session(
    session_id: str,
    level: Optional[str] = Query(None, description="Filter by level (L1/L2/L3)"),
    exception_type: Optional[str] = Query(None, description="Filter by exception type"),
    current_status: Optional[str] = Query(None, description="Filter by current status")
) -> ExceptionsListResponse:
    """
    Get all exceptions for a specific analysis session.
    
    **Filters:**
    - `level`: Exception severity (L1/L2/L3)
    - `exception_type`: Type of exception (e.g., 'Low Height', 'Stagger Left')
    - `current_status`: Processing status (pending/in_progress/resolved/etc.)
    
    **Response includes:**
    - Full exception details (type, level, location, values)
    - Current workflow status
    - Assignment information
    - Notes and history
    """
    try:
        # First verify session exists
        db = get_database()
        with db.get_connection() as conn:
            session = get_session_by_id(conn, session_id)
            
            if not session:
                raise HTTPException(
                    status_code=404,
                    detail=f"Session not found: {session_id}"
                )
            
            # Build filters
            filters: Dict[str, Any] = {}
            if level:
                filters['level'] = level
            if exception_type:
                filters['exception_type'] = exception_type
            if current_status:
                filters['current_status'] = current_status
            
            # Query exceptions
            exceptions = get_session_exceptions(
                conn, 
                session_id, 
                filters=filters if filters else None
            )
        
        return ExceptionsListResponse(
            status="success",
            total=len(exceptions),
            exceptions=exceptions
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting exceptions for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/exceptions/{exception_id}/status", response_model=SuccessResponse)
async def update_exception_workflow_status(
    exception_id: str,
    request: UpdateExceptionStatusRequest
) -> SuccessResponse:
    """
    Update the workflow status of an exception.
    
    **Status values:**
    - `pending`: Not yet addressed
    - `in_progress`: Currently being worked on
    - `resolved`: Issue has been fixed
    - `deferred`: Postponed for later
    - `false_positive`: Not a real issue
    
    **Optional fields:**
    - `notes`: Add notes about the status change
    - `assigned_to`: Assign to a specific person/team
    - `resolved_by`: Record who resolved the issue (when status=resolved)
    
    **Side effects:**
    - Automatically records timestamp changes
    - Creates history record in exception_history table (via trigger)
    - Sets resolved_at when status changes to 'resolved'
    """
    try:
        db = get_database()
        with db.get_connection() as conn:
            success = update_exception_status(
                conn,
                exception_id=exception_id,
                status=request.status,
                notes=request.notes,
                assigned_to=request.assigned_to,
                resolved_by=request.resolved_by
            )
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Exception not found: {exception_id}"
            )
        
        logger.info(f"Updated exception {exception_id} status to {request.status}")
        
        return SuccessResponse(
            status="success",
            message=f"Exception status updated to '{request.status}'"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating exception {exception_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
