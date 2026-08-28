"""Runtime diagnostics endpoints."""
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter

from app.core.config import get_config_dir
from app.core.database import get_database, is_portable_mode

router = APIRouter(prefix="/diagnostics")


@router.get("")
async def diagnostics() -> Dict[str, Any]:
    db_path = get_database().db_path.resolve()
    config_dir = get_config_dir().resolve()
    return {
        "database_path": str(db_path),
        "database_directory": str(db_path.parent),
        "config_directory": str(config_dir),
        "mode": "portable" if is_portable_mode() else "standard",
        "packaging": {
            "recommended_target": "dir",
            "current_target": "dir",
            "writable_data_root": str(db_path.parent),
            "portable_database_pattern": str(Path("<packaged app root>") / "data" / "analysis.db"),
            "single_exe_note": (
                "Single exe packages must store SQLite data in an external writable folder such as %APPDATA%; "
                "embedded executable resources are not a database storage location."
            ),
        },
    }
