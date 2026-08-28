"""
Tests for backend/app/core/config.py - Unified config path resolution.

Phase E: Portable .exe Config Fix (P0)
TDD: Tests for get_config_dir() and get_default_db_path().
"""

import os
import sys
import pytest
from pathlib import Path
from unittest.mock import patch


class TestGetConfigDir:
    """Tests for get_config_dir() function."""

    def test_returns_config_path_env_when_set(self, tmp_path):
        """Priority 1: CONFIG_PATH env variable should be used when set and exists."""
        from app.core.config import get_config_dir

        config_dir = tmp_path / "custom_config"
        config_dir.mkdir()

        with patch.dict(os.environ, {"CONFIG_PATH": str(config_dir)}):
            result = get_config_dir()
            assert result == config_dir

    def test_falls_back_when_config_path_env_not_exists(self, tmp_path):
        """CONFIG_PATH env set but directory doesn't exist should fall back."""
        from app.core.config import get_config_dir

        fake_path = str(tmp_path / "nonexistent_config")

        with patch.dict(os.environ, {"CONFIG_PATH": fake_path}), \
             patch.object(sys, 'frozen', False, create=True):
            result = get_config_dir()
            # Should NOT return the nonexistent env path
            assert result != Path(fake_path)

    def test_falls_back_to_portable_path_when_frozen(self, tmp_path):
        """Priority 2: When frozen, use relative path from executable."""
        from app.core.config import get_config_dir

        # Simulate: resources/backend/backend_server.exe
        backend_dir = tmp_path / "resources" / "backend"
        backend_dir.mkdir(parents=True)
        exe_path = backend_dir / "backend_server.exe"
        exe_path.touch()

        # Create config dir at resources/config/
        config_dir = tmp_path / "resources" / "config"
        config_dir.mkdir(parents=True)

        env_clean = {k: v for k, v in os.environ.items() if k != "CONFIG_PATH"}
        with patch.dict(os.environ, env_clean, clear=True), \
             patch.object(sys, 'frozen', True, create=True), \
             patch.object(sys, 'executable', str(exe_path)):
            result = get_config_dir()
            assert result == config_dir

    def test_falls_back_to_meipass_when_frozen_no_portable(self, tmp_path):
        """Priority 3: When frozen and no portable config, use _MEIPASS."""
        from app.core.config import get_config_dir

        backend_dir = tmp_path / "no_config_here" / "backend"
        backend_dir.mkdir(parents=True)
        exe_path = backend_dir / "backend_server.exe"
        exe_path.touch()

        # Create _MEIPASS config
        meipass_dir = tmp_path / "meipass_bundle"
        meipass_config = meipass_dir / "config"
        meipass_config.mkdir(parents=True)

        env_clean = {k: v for k, v in os.environ.items() if k != "CONFIG_PATH"}
        with patch.dict(os.environ, env_clean, clear=True), \
             patch.object(sys, 'frozen', True, create=True), \
             patch.object(sys, 'executable', str(exe_path)), \
             patch.object(sys, '_MEIPASS', str(meipass_dir), create=True):
            result = get_config_dir()
            assert result == meipass_config

    def test_falls_back_to_dev_path_when_not_frozen(self):
        """Priority 4: Development mode uses path relative to source file."""
        from app.core.config import get_config_dir

        env_clean = {k: v for k, v in os.environ.items() if k != "CONFIG_PATH"}
        with patch.dict(os.environ, env_clean, clear=True), \
             patch.object(sys, 'frozen', False, create=True):
            result = get_config_dir()
            # Should return a Path ending with 'config'
            assert isinstance(result, Path)
            assert result.name == "config"


class TestGetDefaultDbPath:
    """Tests for get_default_db_path() function."""

    def test_returns_db_path_env_when_set(self, tmp_path):
        """Priority 1: DB_PATH env variable should be used when set."""
        from app.core.config import get_default_db_path

        db_file = tmp_path / "custom_data" / "analysis.db"

        with patch.dict(os.environ, {"DB_PATH": str(db_file)}):
            result = get_default_db_path()
            assert result == db_file
            # Should create parent directory
            assert db_file.parent.exists()

    def test_falls_back_to_portable_path_when_frozen(self, tmp_path):
        """Priority 2: When frozen with portable marker, use exe-relative path."""
        from app.core.config import get_default_db_path

        backend_dir = tmp_path / "backend"
        backend_dir.mkdir(parents=True)
        exe_path = backend_dir / "backend_server.exe"
        exe_path.touch()

        # Create portable.txt marker
        portable_marker = backend_dir / "portable.txt"
        portable_marker.write_text("Portable mode marker")

        env_clean = {k: v for k, v in os.environ.items() if k != "DB_PATH"}
        with patch.dict(os.environ, env_clean, clear=True), \
             patch.object(sys, 'frozen', True, create=True), \
             patch.object(sys, 'executable', str(exe_path)):
            result = get_default_db_path()
            expected = backend_dir / "data" / "analysis.db"
            assert result == expected

    def test_falls_back_to_appdata_when_not_frozen(self, tmp_path):
        """Priority 3: Standard mode uses APPDATA path."""
        from app.core.config import get_default_db_path

        env_clean = {k: v for k, v in os.environ.items() if k != "DB_PATH"}
        env_clean["APPDATA"] = str(tmp_path)
        with patch.dict(os.environ, env_clean, clear=True), \
             patch.object(sys, 'frozen', False, create=True):
            result = get_default_db_path()
            expected = tmp_path / "TOV1050_Analyzer" / "data" / "analysis.db"
            assert result == expected
