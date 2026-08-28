"""
Unified config path resolution for TOV1050 Analyzer backend.

Phase E: Portable .exe Config Fix (P0)

Provides centralized path resolution for:
- CONFIG_PATH: Location of metadata Excel files
- DB_PATH: Location of SQLite database

Priority order for config:
1. CONFIG_PATH environment variable (set by Electron)
2. Relative to executable (Portable Production)
3. PyInstaller bundle (_MEIPASS)
4. Development mode (relative to source)

Priority order for DB:
1. DB_PATH environment variable (set by Electron)
2. Portable mode (exe dir with portable.txt marker)
3. Standard APPDATA path
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def get_config_dir() -> Path:
    """
    Locate config directory with priority:
    1. CONFIG_PATH environment variable (set by Electron)
    2. Relative to executable (Portable Production): ../../config from backend_server.exe
    3. PyInstaller bundle: _MEIPASS/config
    4. Development: relative to source file -> project root/config
    """
    # Priority 1: Environment variable
    env_path = os.environ.get('CONFIG_PATH')
    if env_path:
        p = Path(env_path)
        if p.exists():
            logger.info(f"Using CONFIG_PATH env: {p}")
            return p
        logger.warning(f"CONFIG_PATH env set but not found: {p}")

    is_frozen = getattr(sys, 'frozen', False)
    if is_frozen:
        # Priority 2: Relative to exe
        portable_dir = Path(sys.executable).parent.parent / "config"
        if portable_dir.exists():
            logger.info(f"Using portable config: {portable_dir}")
            return portable_dir
        # Priority 3: PyInstaller bundle
        bundle_dir = Path(sys._MEIPASS) / "config"
        if bundle_dir.exists():
            logger.info(f"Using bundle config: {bundle_dir}")
            return bundle_dir
        return portable_dir
    else:
        # Priority 4: Development
        dev_dir = Path(__file__).resolve().parents[3] / "config"
        logger.info(f"Using dev config: {dev_dir}")
        return dev_dir


def _is_portable_mode() -> bool:
    """Check if running as portable exe with marker file."""
    if getattr(sys, 'frozen', False):
        exe_dir = Path(sys.executable).parent
        return (exe_dir / 'portable.txt').exists()
    return False


def _get_portable_data_dir() -> Optional[Path]:
    """Get portable data directory if in portable mode."""
    if _is_portable_mode():
        return Path(sys.executable).parent / 'data'
    return None


def get_default_db_path() -> Path:
    """
    Determine the default database path with priority:
    1. DB_PATH environment variable (set by Electron)
    2. Portable mode (exe dir / data / analysis.db)
    3. Standard APPDATA path
    """
    # Priority 1: DB_PATH environment variable
    env_path = os.environ.get('DB_PATH')
    if env_path:
        p = Path(env_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Using DB_PATH env: {p}")
        return p

    # Priority 2: Portable mode
    portable_dir = _get_portable_data_dir()
    if portable_dir:
        logger.info("Using portable mode DB")
        return portable_dir / 'analysis.db'

    # Priority 3: Standard APPDATA
    appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
    return Path(appdata) / 'TOV1050_Analyzer' / 'data' / 'analysis.db'
