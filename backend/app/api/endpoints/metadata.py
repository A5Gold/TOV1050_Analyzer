from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Dict, Any, Optional
from pathlib import Path
import os
import sys
import logging
from app.core.metadata_service import MetadataService
from app.core.config import get_config_dir

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()

def get_metadata_service():
    """Dependency injection for MetadataService with enhanced error logging."""
    try:
        config_dir = get_config_dir()
        logger.info(f"Initializing MetadataService with config_dir: {config_dir.absolute()}")
        return MetadataService(config_dir)
    except Exception as e:
        logger.error(f"Failed to initialize MetadataService: {e}", exc_info=True)
        raise

@router.get("/metadata/{filename}/sheets")
async def get_sheet_names(
    filename: str,
    service: MetadataService = Depends(get_metadata_service)
):
    """Get list of sheet names from Excel configuration file."""
    try:
        logger.info(f"GET /metadata/{filename}/sheets - Starting request")
        sheets = service.get_sheet_names(filename)
        logger.info(f"GET /metadata/{filename}/sheets - Success. Sheets: {sheets}")
        return sheets
    except FileNotFoundError as e:
        # Enhanced error with absolute path for debugging
        config_dir = get_config_dir()
        attempted_path = config_dir / filename
        error_detail = f"Configuration file not found: {attempted_path.absolute()}"
        logger.error(f"GET /metadata/{filename}/sheets - FileNotFoundError: {error_detail}")
        logger.error(f"Config directory: {config_dir.absolute()}, exists: {config_dir.exists()}")
        
        # List available files in config directory for debugging
        if config_dir.exists():
            try:
                available_files = list(config_dir.glob("*.xlsx"))
                logger.error(f"Available .xlsx files in config dir: {[f.name for f in available_files]}")
            except Exception as list_err:
                logger.error(f"Failed to list config directory: {list_err}")
        
        raise HTTPException(status_code=404, detail=error_detail)
    except Exception as e:
        logger.error(f"GET /metadata/{filename}/sheets - Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/metadata/{filename}")
async def get_metadata(
    filename: str, 
    sheet_name: str = Query("threshold", description="Sheet name to fetch"),
    service: MetadataService = Depends(get_metadata_service)
):
    """Get metadata from a specific sheet in Excel configuration file."""
    try:
        logger.info(f"GET /metadata/{filename}?sheet_name={sheet_name} - Starting request")
        data = service.get_metadata(filename, sheet_name=sheet_name)
        logger.info(f"GET /metadata/{filename}?sheet_name={sheet_name} - Success. Rows: {len(data)}")
        return data
    except FileNotFoundError as e:
        # Enhanced error with absolute path for debugging
        config_dir = get_config_dir()
        attempted_path = config_dir / filename
        error_detail = f"Configuration file not found: {attempted_path.absolute()}"
        logger.error(f"GET /metadata/{filename} - FileNotFoundError: {error_detail}")
        logger.error(f"Config directory: {config_dir.absolute()}, exists: {config_dir.exists()}")
        
        # List available files in config directory for debugging
        if config_dir.exists():
            try:
                available_files = list(config_dir.glob("*.xlsx"))
                logger.error(f"Available .xlsx files in config dir: {[f.name for f in available_files]}")
            except Exception as list_err:
                logger.error(f"Failed to list config directory: {list_err}")
        
        raise HTTPException(status_code=404, detail=error_detail)
    except ValueError as e:
        logger.error(f"GET /metadata/{filename} - ValueError: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"GET /metadata/{filename} - Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/metadata/{filename}")
async def update_metadata(
    filename: str, 
    payload: List[Dict[str, Any]], 
    sheet_name: str = Query("threshold", description="Sheet name to update"),
    service: MetadataService = Depends(get_metadata_service)
):
    """Update metadata in a specific sheet of Excel configuration file."""
    try:
        logger.info(f"POST /metadata/{filename}?sheet_name={sheet_name} - Starting update. Rows: {len(payload)}")
        result = service.save_configuration(filename, payload, sheet_name=sheet_name)
        logger.info(f"POST /metadata/{filename} - Success. Backup: {result.get('backup', 'N/A')}")
        return result
    except ValueError as e:
        logger.error(f"POST /metadata/{filename} - ValueError: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        # Enhanced error with absolute path for debugging
        config_dir = get_config_dir()
        attempted_path = config_dir / filename
        error_detail = f"Configuration file not found: {attempted_path.absolute()}"
        logger.error(f"POST /metadata/{filename} - FileNotFoundError: {error_detail}")
        raise HTTPException(status_code=404, detail=error_detail)
    except Exception as e:
        logger.error(f"POST /metadata/{filename} - Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
