"""
TOV1050 Analyzer - Database Manager Module
==========================================
Provides thread-safe SQLite connection management and CRUD operations
for Stateful Transformation and Database Record modules.

Version: 1.1
Date: 2026-01-30

Supports:
- Standard mode: Data stored in %APPDATA%/TOV1050_Analyzer/data/
- Portable mode: Data stored in exe directory when portable.txt marker exists
"""

import sqlite3
import sys
import threading
import logging
import os
import uuid
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime
from typing import Dict, List, Optional, Any, Generator

import pandas as pd

from .config import get_config_dir
from .database_record_seed import seed_database_records as seed_database_record_assets

# Configure logging
logger = logging.getLogger(__name__)


def _normalize_date_to_compact(date_str: str) -> str:
    """
    Normalize date string to YYYYMMDD compact format.
    Handles YYYY-MM-DD, YYYY/MM/DD, and YYYYMMDD inputs.
    
    Bug 10.10-3: HTML date input sends YYYY-MM-DD, DB stores YYYYMMDD.
    """
    if not date_str:
        return date_str
    # Remove hyphens and slashes
    compact = date_str.replace('-', '').replace('/', '')
    # Validate it looks like YYYYMMDD
    if len(compact) == 8 and compact.isdigit():
        return compact
    # Return original if can't normalize
    return date_str


def is_portable_mode() -> bool:
    """
    Check if the application is running in portable mode.
    
    Portable mode is detected when:
    1. Running as a frozen executable (PyInstaller)
    2. A 'portable.txt' marker file exists in the exe directory
    
    Returns:
        True if portable mode, False otherwise
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        exe_dir = Path(sys.executable).parent
        portable_marker = exe_dir / 'portable.txt'
        return portable_marker.exists()
    return False


def get_portable_data_dir() -> Optional[Path]:
    """
    Get the portable data directory if in portable mode.
    
    Returns:
        Path to portable data directory, or None if not in portable mode
    """
    if is_portable_mode():
        exe_dir = Path(sys.executable).parent
        return exe_dir / 'data'
    return None


def get_default_db_path() -> Path:
    """
    Determine the default database path based on execution mode.

    Priority:
    1. DB_PATH environment variable (set by Electron)
    2. Portable mode: <exe_dir>/data/analysis.db
    3. Standard mode: %APPDATA%/TOV1050_Analyzer/data/analysis.db

    Returns:
        Path to the database file
    """
    # Priority 1: DB_PATH environment variable
    env_path = os.environ.get('DB_PATH')
    if env_path:
        p = Path(env_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Using DB_PATH env: {p}")
        return p

    # Priority 2: Portable mode
    portable_dir = get_portable_data_dir()
    if portable_dir:
        logger.info("Running in PORTABLE mode")
        return portable_dir / 'analysis.db'

    # Priority 3: Standard mode: AppData
    appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
    return Path(appdata) / 'TOV1050_Analyzer' / 'data' / 'analysis.db'


class DatabaseManager:
    """
    Singleton SQLite connection manager with thread-safe operations.
    
    Features:
    - Thread-safe singleton pattern
    - WAL mode for better concurrency
    - Foreign key enforcement
    - Context manager for automatic transaction handling
    - Connection pooling via thread-local storage
    """
    
    _instance: Optional['DatabaseManager'] = None
    _lock: threading.Lock = threading.Lock()
    _initialized: bool = False
    
    def __new__(cls, db_path: Optional[str] = None, *, seed_database_records: Optional[bool] = None) -> 'DatabaseManager':
        """Thread-safe singleton implementation."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, db_path: Optional[str] = None, *, seed_database_records: Optional[bool] = None):
        """
        Initialize database manager.
        
        Args:
            db_path: Custom database path. If not provided, uses:
                     - Portable mode: <exe_dir>/data/analysis.db
                     - Standard mode: %APPDATA%/TOV1050_Analyzer/data/analysis.db
        """
        # Prevent re-initialization
        if DatabaseManager._initialized:
            return
        
        with DatabaseManager._lock:
            if DatabaseManager._initialized:
                return
            
            # Determine database path
            if db_path:
                self._db_path = Path(db_path)
            else:
                self._db_path = get_default_db_path()
            # TOV1050 starts with an empty records database. The copied TOV640
            # EAL/TML seed is intentionally opt-in for legacy regression tests
            # and migration tooling, never an implicit product default.
            self._seed_database_records = (
                False if seed_database_records is None else seed_database_records
            )
            
            # Ensure directory exists
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Thread-local storage for connections
            self._local = threading.local()
            
            # Initialize database
            self._init_database()
            
            DatabaseManager._initialized = True
            
            mode = "PORTABLE" if is_portable_mode() else "STANDARD"
            logger.info(f"DatabaseManager initialized in {mode} mode: {self._db_path}")
    
    @property
    def db_path(self) -> Path:
        """Return the database file path."""
        return self._db_path
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local connection."""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            conn = sqlite3.connect(
                str(self._db_path),
                check_same_thread=False,
                timeout=30.0
            )
            conn.row_factory = sqlite3.Row  # Enable column name access
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA synchronous = NORMAL")
            conn.execute("PRAGMA cache_size = -64000")  # 64MB cache
            self._local.connection = conn
        return self._local.connection
    
    def _init_database(self) -> None:
        """Initialize database schema from schema.sql."""
        schema_path = Path(__file__).parent / 'schema.sql'
        
        if not schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {schema_path}")
        
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        
        conn = self._get_connection()
        try:
            conn.execute("BEGIN")
            self._apply_repeated_records_migration(conn)
            self._apply_wire_wear_records_migration(conn)
            self._apply_wire_wear_cycle_records_migration(conn)
            self._execute_schema_statements(conn, schema_sql)
            if self._seed_database_records:
                seed_result = seed_database_record_assets(conn, get_config_dir())
                if seed_result.status == "seeded":
                    logger.info(
                        "Seeded %s built-in database records",
                        seed_result.inserted_count,
                    )
            conn.commit()
            logger.info("Database schema initialized successfully")

            # Packaged builds may contain an approved Wire Wear seed.  Apply it
            # only after schema setup has committed so the sync transaction can
            # create its own atomic boundary.  The import is intentionally lazy
            # to keep database module imports free of calculation cycles.
            seed_path = get_config_dir() / "wire-wear-seed.json"
            if getattr(sys, "frozen", False) and seed_path.is_file():
                try:
                    from .calculation.wear_cycle_seed import (
                        initialize_seed_if_empty,
                        metadata_fingerprints,
                    )
                    from .calculation.wear_cycle_metadata import load_line_metadata
                    from .metadata import MetadataManager

                    config_dir = get_config_dir()
                    metadata = {}
                    for line, line_class in (("EAL", "EAL"), ("EAL", "LMC"), ("TML", "TML")):
                        filename = "EAL metadata.xlsx" if line == "EAL" else "TML metadata.xlsx"
                        manager = MetadataManager(config_path=config_dir / filename)
                        metadata[(line, line_class)] = tuple(
                            load_line_metadata(manager, line, None if line == line_class else line_class)
                        )
                    result = initialize_seed_if_empty(
                        conn,
                        seed_path,
                        metadata,
                        metadata_fingerprint=metadata_fingerprints(config_dir),
                        db_path=self._db_path,
                    )
                    logger.info("Wire Wear seed initialization result: %s", result.status)
                except Exception:
                    # Seed failure must not make the rest of the application
                    # unavailable; the initializer also rolls back its writes.
                    logger.exception("Wire Wear seed initialization failed during startup")
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to initialize schema: {e}")
            raise

    @staticmethod
    def _execute_schema_statements(conn: sqlite3.Connection, schema_sql: str) -> None:
        statement_buffer: List[str] = []
        for line in schema_sql.splitlines(keepends=True):
            stripped = line.strip()
            if not statement_buffer and (not stripped or stripped.startswith("--")):
                continue

            statement_buffer.append(line)
            statement = "".join(statement_buffer)
            if sqlite3.complete_statement(statement):
                conn.execute(statement)
                statement_buffer.clear()

        if statement_buffer:
            raise sqlite3.OperationalError("Incomplete SQL statement at end of schema")

    def _table_exists(self, conn: sqlite3.Connection, table_name: str) -> bool:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
            (table_name,)
        )
        return cursor.fetchone() is not None

    def _apply_repeated_records_migration(self, conn: sqlite3.Connection) -> None:
        """
        Migration 1.1: Ensure saved_repeated_exceptions has 9 workflow columns.
        This fixes legacy DBs created before 2026-01-31.
        """
        if not self._table_exists(conn, 'saved_repeated_exceptions'):
            return

        cursor = conn.execute("PRAGMA table_info(saved_repeated_exceptions)")
        existing_columns = {row['name'] for row in cursor.fetchall()}
        required_columns = [
            'session',
            'reoccurrence_id',
            'verify_deadline',
            'verify_date',
            'verify_result',
            'verified_by',
            'adjust_deadline',
            'adjust_date',
            'adjust_result',
            'adjusted_by',
            'task_run_date',  # NEW: Phase 8.1 (2026-02-01)
        ]

        missing_columns = [col for col in required_columns if col not in existing_columns]
        if not missing_columns:
            return

        for column in missing_columns:
            conn.execute(f"ALTER TABLE saved_repeated_exceptions ADD COLUMN {column} TEXT")

        # Ensure indexes for new columns (safe if already present)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_repeated_reoccurrence ON saved_repeated_exceptions(reoccurrence_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_repeated_verify_deadline ON saved_repeated_exceptions(verify_deadline)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_repeated_adjust_deadline ON saved_repeated_exceptions(adjust_deadline)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_repeated_task_run_date ON saved_repeated_exceptions(task_run_date)")

        # Record migration metadata when possible
        if self._table_exists(conn, 'schema_migrations'):
            conn.execute(
                "INSERT OR IGNORE INTO schema_migrations (version, description) VALUES (?, ?)",
                (
                    '1.2',
                    'Add task_run_date column to saved_repeated_exceptions for Task Run Data group'
                )
            )
        if self._table_exists(conn, 'system_metadata'):
            set_system_metadata(conn, 'schema_version', '1.2')
            set_system_metadata(conn, 'last_migration', '1.2')

    def _apply_wire_wear_records_migration(self, conn: sqlite3.Connection) -> None:
        """Migration 1.3: Ensure Wear Calculator wire wear records table exists."""
        if self._table_exists(conn, "wire_wear_records"):
            cursor = conn.execute("PRAGMA table_info(wire_wear_records)")
            existing_columns = {row["name"] for row in cursor.fetchall()}
            required_columns = {
                "record_id",
                "line_group",
                "line_class",
                "track",
                "section",
                "cycle_date",
                "tension_length",
                "from_m",
                "to_m",
                "avg_wear_min",
                "sd",
                "wear_percentage",
                "source_file_names",
                "saved_by",
                "created_at",
                "updated_at",
            }
            expected_unique = [
                "line_group",
                "line_class",
                "track",
                "section",
                "cycle_date",
                "tension_length",
            ]
            unique_matches = False
            for index_row in conn.execute("PRAGMA index_list(wire_wear_records)").fetchall():
                if not index_row["unique"]:
                    continue
                columns = [
                    info["name"]
                    for info in conn.execute(f"PRAGMA index_info({index_row['name']})").fetchall()
                ]
                if columns == expected_unique:
                    unique_matches = True
                    break

            if required_columns.issubset(existing_columns) and unique_matches:
                return

            self._rebuild_wire_wear_records_table(conn, existing_columns)
        else:
            self._create_wire_wear_records_table(conn)

        conn.execute("CREATE INDEX IF NOT EXISTS idx_wire_wear_line_group ON wire_wear_records(line_group)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_wire_wear_line_class ON wire_wear_records(line_class)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_wire_wear_records_cycle_date ON wire_wear_records(cycle_date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_wire_wear_tension_length ON wire_wear_records(tension_length)")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_wire_wear_group_tl_date "
            "ON wire_wear_records(line_group, tension_length, cycle_date)"
        )
        if self._table_exists(conn, "schema_migrations"):
            conn.execute(
                "INSERT OR IGNORE INTO schema_migrations (version, description) VALUES (?, ?)",
                ("1.3", "Add wire_wear_records table for Wear Calculator saved cycle records"),
            )
        if self._table_exists(conn, "system_metadata"):
            set_system_metadata(conn, "schema_version", "1.3")
            set_system_metadata(conn, "last_migration", "1.3")

    def _migrate_normalized_wire_wear_line_class(self, conn: sqlite3.Connection) -> None:
        """Rebuild the normalized wear graph while preserving cycle identifiers."""
        required_tables = (
            "wire_wear_cycles",
            "wire_wear_cycle_records",
            "wire_wear_cycle_segments",
            "wire_wear_conflict_decisions",
            "wire_wear_deletion_tombstones",
        )
        if not all(self._table_exists(conn, table) for table in required_tables):
            return
        identity_tables = {
            "wire_wear_cycles": (
                ("line_group", "line_class", "cycle_date"),
                ("line_group", "cycle_date"),
            ),
            "wire_wear_cycle_records": (
                ("line_group", "line_class", "cycle_date", "tension_length"),
                ("line_group", "cycle_date", "tension_length"),
            ),
            "wire_wear_deletion_tombstones": (
                ("line_group", "line_class", "cycle_date", "tension_length"),
                ("line_group", "cycle_date", "tension_length"),
            ),
        }
        columns_by_table = {
            table: {
                row["name"]
                for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
            }
            for table in required_tables
        }

        def unique_shapes(table: str) -> set[tuple[str, ...]]:
            shapes: set[tuple[str, ...]] = set()
            for index in conn.execute(f"PRAGMA index_list({table})").fetchall():
                if not index["unique"]:
                    continue
                columns = tuple(
                    row["name"]
                    for row in conn.execute(
                        f"PRAGMA index_info({index['name']})"
                    ).fetchall()
                )
                shapes.add(columns)
            return shapes

        if all(
            "line_class" in columns_by_table[table]
            and expected in unique_shapes(table)
            and legacy not in unique_shapes(table)
            for table, (expected, legacy) in identity_tables.items()
        ):
            return

        legacy_suffix = "_pre_line_class"
        for table in required_tables:
            conn.execute(f"DROP TABLE IF EXISTS {table}{legacy_suffix}")
        conn.execute("ALTER TABLE wire_wear_cycles RENAME TO wire_wear_cycles_pre_line_class")
        conn.execute("ALTER TABLE wire_wear_cycle_records RENAME TO wire_wear_cycle_records_pre_line_class")
        conn.execute("ALTER TABLE wire_wear_cycle_segments RENAME TO wire_wear_cycle_segments_pre_line_class")
        conn.execute("ALTER TABLE wire_wear_conflict_decisions RENAME TO wire_wear_conflict_decisions_pre_line_class")
        conn.execute("ALTER TABLE wire_wear_deletion_tombstones RENAME TO wire_wear_deletion_tombstones_pre_line_class")

        conn.execute("""
            CREATE TABLE wire_wear_cycles (
                cycle_id INTEGER PRIMARY KEY AUTOINCREMENT,
                line_group TEXT NOT NULL CHECK(line_group IN ('EAL', 'TML')),
                line_class TEXT NOT NULL CHECK(line_class IN ('EAL', 'LMC', 'TML')),
                cycle_date TEXT NOT NULL,
                source_type TEXT NOT NULL CHECK(source_type IN ('analysis', 'manual', 'sync')),
                acquisition_date_from TEXT,
                acquisition_date_to TEXT,
                completeness_state TEXT NOT NULL CHECK(completeness_state IN ('complete', 'incomplete')),
                source_lineage TEXT NOT NULL DEFAULT '[]',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(line_group, line_class, cycle_date)
            )
        """)
        conn.execute("""
            CREATE TABLE wire_wear_cycle_records (
                record_id INTEGER PRIMARY KEY AUTOINCREMENT,
                cycle_id INTEGER NOT NULL,
                line_group TEXT NOT NULL CHECK(line_group IN ('EAL', 'TML')),
                line_class TEXT NOT NULL CHECK(line_class IN ('EAL', 'LMC', 'TML')),
                cycle_date TEXT NOT NULL,
                tension_length TEXT NOT NULL,
                track TEXT NOT NULL CHECK(track IN ('UP', 'DN', 'Siding')),
                from_m REAL NOT NULL,
                to_m REAL NOT NULL,
                avg_wear_min REAL NOT NULL,
                wear_percentage REAL NOT NULL,
                measurement_sd REAL,
                physical_intervals TEXT NOT NULL DEFAULT '[]',
                source_lineage TEXT NOT NULL DEFAULT '[]',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(line_group, line_class, cycle_date, tension_length),
                FOREIGN KEY (cycle_id) REFERENCES wire_wear_cycles(cycle_id) ON DELETE CASCADE
            )
        """)
        conn.execute("""
            CREATE TABLE wire_wear_cycle_segments (
                segment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                cycle_id INTEGER NOT NULL,
                segment_name TEXT NOT NULL,
                is_present INTEGER NOT NULL CHECK(is_present IN (0, 1)),
                coverage_percentage REAL NOT NULL,
                diagnostic_gaps TEXT NOT NULL DEFAULT '[]',
                source_file_names TEXT NOT NULL DEFAULT '[]',
                acquisition_date_from TEXT,
                acquisition_date_to TEXT,
                UNIQUE(cycle_id, segment_name),
                FOREIGN KEY (cycle_id) REFERENCES wire_wear_cycles(cycle_id) ON DELETE CASCADE
            )
        """)
        conn.execute("""
            CREATE TABLE wire_wear_conflict_decisions (
                decision_id INTEGER PRIMARY KEY AUTOINCREMENT,
                cycle_id INTEGER NOT NULL,
                measurement_identity TEXT NOT NULL,
                source_values TEXT NOT NULL,
                selected_wear_min REAL NOT NULL,
                accepted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(cycle_id, measurement_identity),
                FOREIGN KEY (cycle_id) REFERENCES wire_wear_cycles(cycle_id) ON DELETE CASCADE
            )
        """)
        conn.execute("""
            CREATE TABLE wire_wear_deletion_tombstones (
                tombstone_id INTEGER PRIMARY KEY AUTOINCREMENT,
                line_group TEXT NOT NULL CHECK(line_group IN ('EAL', 'TML')),
                line_class TEXT NOT NULL CHECK(line_class IN ('EAL', 'LMC', 'TML')),
                cycle_date TEXT NOT NULL,
                tension_length TEXT NOT NULL,
                deleted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                source_package_id TEXT,
                UNIQUE(line_group, line_class, cycle_date, tension_length)
            )
        """)

        cycle_line_class_expr = (
            "line_class"
            if "line_class" in columns_by_table["wire_wear_cycles"]
            else "CASE WHEN UPPER(line_group) = 'TML' THEN 'TML' ELSE 'EAL' END"
        )
        conn.execute(f"""
            INSERT INTO wire_wear_cycles (
                cycle_id, line_group, line_class, cycle_date, source_type,
                acquisition_date_from, acquisition_date_to, completeness_state,
                source_lineage, created_at, updated_at
            )
            SELECT cycle_id, line_group, {cycle_line_class_expr}, cycle_date, source_type,
                   acquisition_date_from, acquisition_date_to, completeness_state,
                   source_lineage, created_at, updated_at
            FROM wire_wear_cycles_pre_line_class
        """)
        record_line_class_expr = (
            "records.line_class"
            if "line_class" in columns_by_table["wire_wear_cycle_records"]
            else (
                "cycles.line_class"
                if "line_class" in columns_by_table["wire_wear_cycles"]
                else "CASE WHEN UPPER(records.line_group) = 'TML' THEN 'TML' ELSE 'EAL' END"
            )
        )
        conn.execute(f"""
            INSERT INTO wire_wear_cycle_records (
                record_id, cycle_id, line_group, line_class, cycle_date, tension_length,
                track, from_m, to_m, avg_wear_min, wear_percentage, measurement_sd,
                physical_intervals, source_lineage, created_at, updated_at
            )
            SELECT records.record_id, records.cycle_id, records.line_group,
                   {record_line_class_expr}, records.cycle_date, records.tension_length,
                   records.track, records.from_m, records.to_m, records.avg_wear_min,
                   records.wear_percentage, records.measurement_sd,
                   records.physical_intervals, records.source_lineage,
                   records.created_at, records.updated_at
            FROM wire_wear_cycle_records_pre_line_class AS records
            JOIN wire_wear_cycles_pre_line_class AS cycles
              ON cycles.cycle_id = records.cycle_id
        """)
        conn.execute("INSERT INTO wire_wear_cycle_segments SELECT * FROM wire_wear_cycle_segments_pre_line_class")
        conn.execute("INSERT INTO wire_wear_conflict_decisions SELECT * FROM wire_wear_conflict_decisions_pre_line_class")
        tombstone_line_class_expr = (
            "line_class"
            if "line_class" in columns_by_table["wire_wear_deletion_tombstones"]
            else "CASE WHEN UPPER(line_group) = 'TML' THEN 'TML' ELSE 'EAL' END"
        )
        conn.execute(f"""
            INSERT INTO wire_wear_deletion_tombstones (
                tombstone_id, line_group, line_class, cycle_date, tension_length,
                deleted_at, source_package_id
            )
            SELECT tombstone_id, line_group, {tombstone_line_class_expr}, cycle_date, tension_length,
                   deleted_at, source_package_id
            FROM wire_wear_deletion_tombstones_pre_line_class
        """)
        for table in reversed(required_tables):
            conn.execute(f"DROP TABLE {table}{legacy_suffix}")

    def _apply_wire_wear_cycle_records_migration(self, conn: sqlite3.Connection) -> None:
        """Migrations 1.5-1.7: normalize wear storage and expand line identity."""
        if self._table_exists(conn, "wire_wear_cycle_records"):
            existing_columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(wire_wear_cycle_records)").fetchall()
            }
            if "sd" in existing_columns or "cycle_id" not in existing_columns:
                conn.execute("DROP TABLE wire_wear_cycle_records")

        self._migrate_normalized_wire_wear_line_class(conn)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS wire_wear_cycles (
                cycle_id INTEGER PRIMARY KEY AUTOINCREMENT,
                line_group TEXT NOT NULL CHECK(line_group IN ('EAL', 'TML')),
                line_class TEXT NOT NULL CHECK(line_class IN ('EAL', 'LMC', 'TML')),
                cycle_date TEXT NOT NULL,
                source_type TEXT NOT NULL CHECK(source_type IN ('analysis', 'manual', 'sync')),
                acquisition_date_from TEXT,
                acquisition_date_to TEXT,
                completeness_state TEXT NOT NULL CHECK(completeness_state IN ('complete', 'incomplete')),
                source_lineage TEXT NOT NULL DEFAULT '[]',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(line_group, line_class, cycle_date)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS wire_wear_cycle_segments (
                segment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                cycle_id INTEGER NOT NULL,
                segment_name TEXT NOT NULL,
                is_present INTEGER NOT NULL CHECK(is_present IN (0, 1)),
                coverage_percentage REAL NOT NULL,
                diagnostic_gaps TEXT NOT NULL DEFAULT '[]',
                source_file_names TEXT NOT NULL DEFAULT '[]',
                acquisition_date_from TEXT,
                acquisition_date_to TEXT,
                UNIQUE(cycle_id, segment_name),
                FOREIGN KEY (cycle_id) REFERENCES wire_wear_cycles(cycle_id) ON DELETE CASCADE
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS wire_wear_cycle_records (
                record_id INTEGER PRIMARY KEY AUTOINCREMENT,
                cycle_id INTEGER NOT NULL,
                line_group TEXT NOT NULL CHECK(line_group IN ('EAL', 'TML')),
                line_class TEXT NOT NULL CHECK(line_class IN ('EAL', 'LMC', 'TML')),
                cycle_date TEXT NOT NULL,
                tension_length TEXT NOT NULL,
                track TEXT NOT NULL CHECK(track IN ('UP', 'DN', 'Siding')),
                from_m REAL NOT NULL,
                to_m REAL NOT NULL,
                avg_wear_min REAL NOT NULL,
                wear_percentage REAL NOT NULL,
                measurement_sd REAL,
                physical_intervals TEXT NOT NULL DEFAULT '[]',
                source_lineage TEXT NOT NULL DEFAULT '[]',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(line_group, line_class, cycle_date, tension_length),
                FOREIGN KEY (cycle_id) REFERENCES wire_wear_cycles(cycle_id) ON DELETE CASCADE
            )
        """)
        record_columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(wire_wear_cycle_records)").fetchall()
        }
        if "physical_intervals" not in record_columns:
            conn.execute(
                "ALTER TABLE wire_wear_cycle_records "
                "ADD COLUMN physical_intervals TEXT NOT NULL DEFAULT '[]'"
            )
        conn.execute("""
            CREATE TABLE IF NOT EXISTS wire_wear_conflict_decisions (
                decision_id INTEGER PRIMARY KEY AUTOINCREMENT,
                cycle_id INTEGER NOT NULL,
                measurement_identity TEXT NOT NULL,
                source_values TEXT NOT NULL,
                selected_wear_min REAL NOT NULL,
                accepted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(cycle_id, measurement_identity),
                FOREIGN KEY (cycle_id) REFERENCES wire_wear_cycles(cycle_id) ON DELETE CASCADE
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS wire_wear_deletion_tombstones (
                tombstone_id INTEGER PRIMARY KEY AUTOINCREMENT,
                line_group TEXT NOT NULL CHECK(line_group IN ('EAL', 'TML')),
                line_class TEXT NOT NULL CHECK(line_class IN ('EAL', 'LMC', 'TML')),
                cycle_date TEXT NOT NULL,
                tension_length TEXT NOT NULL,
                deleted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                source_package_id TEXT,
                UNIQUE(line_group, line_class, cycle_date, tension_length)
            )
        """)
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_wire_wear_cycle_identity "
            "ON wire_wear_cycle_records(line_group, line_class, cycle_date, tension_length)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_wire_wear_cycle_tl_history "
            "ON wire_wear_cycle_records(line_group, line_class, tension_length, cycle_date)"
        )
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_wire_wear_parent_cycle "
            "ON wire_wear_cycles(line_group, line_class, cycle_date)"
        )
        if self._table_exists(conn, "schema_migrations"):
            conn.execute(
                "INSERT OR IGNORE INTO schema_migrations (version, description) VALUES (?, ?)",
                (
                    "1.5",
                    "Normalize complete-cycle wire wear storage",
                ),
            )
            conn.execute(
                "INSERT OR IGNORE INTO schema_migrations (version, description) VALUES (?, ?)",
                ("1.6", "Preserve multi-interval wire wear metadata"),
            )
            conn.execute(
                "INSERT OR IGNORE INTO schema_migrations (version, description) VALUES (?, ?)",
                ("1.7", "Add required line_class to normalized wire wear identity"),
            )
        if self._table_exists(conn, "system_metadata"):
            set_system_metadata(conn, "schema_version", "1.7")
            set_system_metadata(conn, "last_migration", "1.7")
            conn.execute(
                """
                INSERT OR IGNORE INTO system_metadata (key, value, description)
                VALUES ('wire_wear_data_version', '0', 'Wire wear data version for sync')
                """
            )

    def _create_wire_wear_records_table(self, conn: sqlite3.Connection) -> None:
        """Create the current wire wear records table."""
        conn.execute("""
            CREATE TABLE IF NOT EXISTS wire_wear_records (
                record_id INTEGER PRIMARY KEY AUTOINCREMENT,
                line_group TEXT NOT NULL CHECK(line_group IN ('EAL', 'TML')),
                line_class TEXT NOT NULL CHECK(line_class IN ('EAL', 'LMC', 'TML')),
                track TEXT NOT NULL,
                section TEXT NOT NULL,
                cycle_date TEXT NOT NULL,
                tension_length TEXT NOT NULL,
                from_m REAL NOT NULL,
                to_m REAL NOT NULL,
                avg_wear_min REAL NOT NULL,
                sd REAL NOT NULL DEFAULT 0,
                wear_percentage REAL NOT NULL,
                source_file_names TEXT,
                saved_by TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(line_group, line_class, track, section, cycle_date, tension_length)
            )
        """)

    def _rebuild_wire_wear_records_table(self, conn: sqlite3.Connection, existing_columns: set[str]) -> None:
        """Rebuild legacy wire wear records tables to the current identity schema."""
        conn.execute("DROP TABLE IF EXISTS wire_wear_records_legacy")
        conn.execute("ALTER TABLE wire_wear_records RENAME TO wire_wear_records_legacy")
        self._create_wire_wear_records_table(conn)

        def expr(column: str, fallback: str = "NULL") -> str:
            return column if column in existing_columns else fallback

        raw_line_group = expr("line_group", "'EAL'")
        raw_line_class = expr("line_class", raw_line_group)
        raw_section = expr("section", "'Mainline'")
        line_group_expr = (
            f"CASE "
            f"WHEN UPPER(COALESCE({raw_line_class}, {raw_line_group}, '')) = 'LMC' THEN 'EAL' "
            f"WHEN UPPER(COALESCE({raw_line_class}, {raw_line_group}, '')) = 'TML' THEN 'TML' "
            f"WHEN UPPER(COALESCE({raw_line_group}, '')) = 'TML' THEN 'TML' "
            f"ELSE 'EAL' END"
        )
        line_class_expr = (
            f"CASE "
            f"WHEN UPPER(COALESCE({raw_line_class}, {raw_line_group}, '')) = 'LMC' "
            f"     OR UPPER(COALESCE({raw_section}, '')) = 'LMC' THEN 'LMC' "
            f"WHEN UPPER(COALESCE({raw_line_class}, {raw_line_group}, '')) = 'TML' "
            f"     OR UPPER(COALESCE({raw_line_group}, '')) = 'TML' THEN 'TML' "
            f"ELSE 'EAL' END"
        )
        legacy_count = conn.execute("SELECT COUNT(*) AS count FROM wire_wear_records_legacy").fetchone()["count"]
        conn.execute(
            f"""
            INSERT OR IGNORE INTO wire_wear_records (
                line_group, line_class, track, section, cycle_date,
                tension_length, from_m, to_m, avg_wear_min, sd,
                wear_percentage, source_file_names, saved_by, created_at, updated_at
            )
            SELECT
                {line_group_expr},
                {line_class_expr},
                {expr("track", "''")},
                COALESCE({expr("section", "'Mainline'")}, 'Mainline'),
                {expr("cycle_date", "''")},
                {expr("tension_length", "''")},
                {expr("from_m", "0")},
                {expr("to_m", "0")},
                {expr("avg_wear_min", "0")},
                COALESCE({expr("sd", "0")}, 0),
                {expr("wear_percentage", "0")},
                {expr("source_file_names")},
                {expr("saved_by")},
                COALESCE({expr("created_at", "CURRENT_TIMESTAMP")}, CURRENT_TIMESTAMP),
                COALESCE({expr("updated_at", "CURRENT_TIMESTAMP")}, CURRENT_TIMESTAMP)
            FROM wire_wear_records_legacy
            """
        )
        migrated_count = conn.execute("SELECT COUNT(*) AS count FROM wire_wear_records").fetchone()["count"]
        if migrated_count < legacy_count:
            conn.execute("DROP TABLE IF EXISTS wire_wear_records_migration_conflicts")
            conn.execute(
                """
                CREATE TABLE wire_wear_records_migration_conflicts AS
                SELECT * FROM wire_wear_records_legacy
                """
            )
            logger.warning(
                "Wire wear records migration preserved %s legacy rows in "
                "wire_wear_records_migration_conflicts after %s rows migrated",
                legacy_count,
                migrated_count,
            )
        conn.execute("DROP TABLE wire_wear_records_legacy")
    
    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """
        Context manager for database operations with automatic commit/rollback.
        
        Usage:
            with db.get_connection() as conn:
                conn.execute("INSERT INTO ...")
        """
        conn = self._get_connection()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error, rolled back: {e}")
            raise
    
    def close(self) -> None:
        """Close thread-local connection."""
        if hasattr(self._local, 'connection') and self._local.connection:
            self._local.connection.close()
            self._local.connection = None
    
    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton instance (for testing purposes)."""
        with cls._lock:
            if cls._instance is not None:
                cls._instance.close()
            cls._instance = None
            cls._initialized = False


# =============================================================================
# SECTION 1: SYSTEM METADATA FUNCTIONS
# =============================================================================

def get_system_metadata(conn: sqlite3.Connection, key: str) -> Optional[str]:
    """
    Get a system metadata value by key.
    
    Args:
        conn: Database connection
        key: Metadata key (e.g., 'db_version', 'schema_version')
    
    Returns:
        Value as string, or None if not found
    """
    cursor = conn.execute(
        "SELECT value FROM system_metadata WHERE key = ?",
        (key,)
    )
    row = cursor.fetchone()
    return row['value'] if row else None


def set_system_metadata(conn: sqlite3.Connection, key: str, value: str, description: Optional[str] = None) -> bool:
    """
    Set a system metadata value.
    
    Args:
        conn: Database connection
        key: Metadata key
        value: Metadata value
        description: Optional description
    
    Returns:
        True if successful
    """
    if description:
        conn.execute(
            """INSERT OR REPLACE INTO system_metadata (key, value, description, updated_at) 
               VALUES (?, ?, ?, CURRENT_TIMESTAMP)""",
            (key, value, description)
        )
    else:
        conn.execute(
            """UPDATE system_metadata SET value = ?, updated_at = CURRENT_TIMESTAMP 
               WHERE key = ?""",
            (value, key)
        )
    return True


def get_db_version(conn: sqlite3.Connection) -> int:
    """Get current database version number."""
    version = get_system_metadata(conn, 'db_version')
    return int(version) if version else 0


# =============================================================================
# SECTION 2: STATEFUL TRANSFORMATION - SESSIONS
# =============================================================================

def generate_session_id() -> str:
    """Generate a unique session ID."""
    return str(uuid.uuid4())


def save_analysis_session(
    conn: sqlite3.Connection,
    session_data: Dict[str, Any]
) -> str:
    """
    Save a new analysis session.
    
    Args:
        conn: Database connection
        session_data: Dictionary containing:
            - line: str (required)
            - section: str (required)
            - track: str (required)
            - date_str: str (required)
            - raw_data_file_path: str (optional)
            - raw_data_file_name: str (optional)
            - raw_data_file_size: int (optional)
            - task_no: str (optional)
            - station_start: str (optional)
            - station_end: str (optional)
    
    Returns:
        Session ID (UUID string)
    """
    session_id = session_data.get('id') or generate_session_id()
    
    conn.execute("""
        INSERT INTO analysis_sessions (
            id, line, section, track, date_str,
            raw_data_file_path, raw_data_file_name, raw_data_file_size,
            task_no, station_start, station_end,
            status, analyzed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'completed', CURRENT_TIMESTAMP)
    """, (
        session_id,
        session_data['line'],
        session_data['section'],
        session_data['track'],
        session_data['date_str'],
        session_data.get('raw_data_file_path'),
        session_data.get('raw_data_file_name'),
        session_data.get('raw_data_file_size'),
        session_data.get('task_no'),
        session_data.get('station_start'),
        session_data.get('station_end'),
    ))
    
    logger.info(f"Saved analysis session: {session_id}")
    return session_id


def save_exceptions_from_analysis(
    conn: sqlite3.Connection,
    session_id: str,
    exceptions: Dict[str, List[Dict[str, Any]]]
) -> int:
    """
    Save exceptions from an analysis result (auto-persistence).
    
    Args:
        conn: Database connection
        session_id: Parent session ID
        exceptions: Dictionary of exception lists by type
            e.g., {'Low Height': [...], 'Stagger Left': [...]}
    
    Returns:
        Number of exceptions saved
    """
    saved_count = 0
    
    for exc_type, exc_list in exceptions.items():
        for exc in exc_list:
            try:
                exc_id = exc.get('id') or str(uuid.uuid4())
                
                conn.execute("""
                    INSERT OR IGNORE INTO exceptions (
                        id, session_id, exception_type, level,
                        from_m, to_m, length, max_value, max_location,
                        track_type, overlap, tension_length, landmark,
                        class, threshold_value, section
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    exc_id,
                    session_id,
                    exc.get('exception type', exc_type),
                    exc.get('level', 'L3'),
                    exc.get('FromM', 0),
                    exc.get('ToM', 0),
                    exc.get('length'),
                    exc.get('maxValue'),
                    exc.get('maxLocation'),
                    exc.get('Track Type'),
                    exc.get('Overlap'),
                    str(exc.get('Tension Length', '')) if exc.get('Tension Length') else None,
                    exc.get('Landmark'),
                    exc.get('Class'),
                    exc.get('Threshold Value'),
                    exc.get('Section'),
                ))
                saved_count += 1
            except sqlite3.Error as e:
                logger.error(f"Failed to save exception {exc.get('id')}: {e}")
    
    logger.info(f"Saved {saved_count} exceptions for session {session_id}")
    return saved_count


def get_sessions(
    conn: sqlite3.Connection,
    filters: Optional[Dict[str, Any]] = None,
    limit: int = 100,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    Query analysis sessions with optional filters.
    
    Args:
        conn: Database connection
        filters: Optional filter dictionary:
            - line: str
            - track: str
            - section: str
            - date_from: str (YYYYMMDD)
            - date_to: str (YYYYMMDD)
            - status: str
        limit: Maximum number of results
        offset: Pagination offset
    
    Returns:
        List of session dictionaries
    """
    query = """
        SELECT * FROM v_sessions_with_stats
        WHERE 1=1
    """
    params: List[Any] = []
    
    if filters:
        if filters.get('line'):
            query += " AND line = ?"
            params.append(filters['line'])
        
        if filters.get('track'):
            query += " AND track = ?"
            params.append(filters['track'])
        
        if filters.get('section'):
            query += " AND section = ?"
            params.append(filters['section'])
        
        if filters.get('date_from'):
            query += " AND date_str >= ?"
            params.append(filters['date_from'])
        
        if filters.get('date_to'):
            query += " AND date_str <= ?"
            params.append(filters['date_to'])
        
        if filters.get('status'):
            query += " AND status = ?"
            params.append(filters['status'])
    
    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    cursor = conn.execute(query, params)
    rows = cursor.fetchall()
    
    return [dict(row) for row in rows]


def get_session_by_id(conn: sqlite3.Connection, session_id: str) -> Optional[Dict[str, Any]]:
    """Get a single session by ID."""
    cursor = conn.execute(
        "SELECT * FROM v_sessions_with_stats WHERE id = ?",
        (session_id,)
    )
    row = cursor.fetchone()
    return dict(row) if row else None


def get_session_exceptions(
    conn: sqlite3.Connection,
    session_id: str,
    filters: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Get all exceptions for a specific session.
    
    Args:
        conn: Database connection
        session_id: Session ID
        filters: Optional filters (level, exception_type, current_status)
    
    Returns:
        List of exception dictionaries
    """
    query = "SELECT * FROM exceptions WHERE session_id = ?"
    params: List[Any] = [session_id]
    
    if filters:
        if filters.get('level'):
            query += " AND level = ?"
            params.append(filters['level'])
        
        if filters.get('exception_type'):
            query += " AND exception_type = ?"
            params.append(filters['exception_type'])
        
        if filters.get('current_status'):
            query += " AND current_status = ?"
            params.append(filters['current_status'])
    
    query += " ORDER BY from_m ASC"
    
    cursor = conn.execute(query, params)
    rows = cursor.fetchall()
    
    return [dict(row) for row in rows]


def update_exception_status(
    conn: sqlite3.Connection,
    exception_id: str,
    status: str,
    notes: Optional[str] = None,
    assigned_to: Optional[str] = None,
    resolved_by: Optional[str] = None
) -> bool:
    """
    Update exception status and related fields.
    
    Args:
        conn: Database connection
        exception_id: Exception ID
        status: New status (pending/in_progress/resolved/deferred/false_positive)
        notes: Optional notes
        assigned_to: Optional assignee
        resolved_by: Optional resolver (for 'resolved' status)
    
    Returns:
        True if successful
    """
    # Build update query dynamically
    updates = ["current_status = ?"]
    params: List[Any] = [status]
    
    if notes is not None:
        updates.append("notes = ?")
        params.append(notes)
    
    if assigned_to is not None:
        updates.append("assigned_to = ?")
        params.append(assigned_to)
    
    if status == 'resolved':
        updates.append("resolved_at = CURRENT_TIMESTAMP")
        if resolved_by:
            updates.append("resolved_by = ?")
            params.append(resolved_by)
    
    params.append(exception_id)
    
    query = f"UPDATE exceptions SET {', '.join(updates)} WHERE id = ?"
    
    cursor = conn.execute(query, params)
    return cursor.rowcount > 0


# =============================================================================
# SECTION 3: DATABASE RECORD - SUB-MODULE 1 (EXCEPTION RECORDS) - DEPRECATED
# =============================================================================
# NOTE: Sub-module 1 has been DEPRECATED and REMOVED as of 2026-01-31.
# The saved_exception_records table and related functions are no longer used.
# All exception record storage is now handled via Sub-module 2 (Repeated Exceptions).
# These stub functions are kept for backward compatibility but will log warnings.

def save_exception_records_batch(
    conn: sqlite3.Connection,
    line: str,
    track: str,
    section: str,
    date_str: str,
    exceptions: List[Dict[str, Any]],
    task_no: Optional[str] = None,
    station_start: Optional[str] = None,
    station_end: Optional[str] = None,
    saved_by: Optional[str] = None,
    source_session_id: Optional[str] = None
) -> int:
    """DEPRECATED: Sub-module 1 has been removed. Returns 0."""
    logger.warning("save_exception_records_batch is DEPRECATED. Sub-module 1 has been removed.")
    return 0


def query_exception_records(
    conn: sqlite3.Connection,
    filters: Optional[Dict[str, Any]] = None,
    limit: int = 1000,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """DEPRECATED: Sub-module 1 has been removed. Returns empty list."""
    logger.warning("query_exception_records is DEPRECATED. Sub-module 1 has been removed.")
    return []


def delete_exception_record(conn: sqlite3.Connection, record_id: str) -> bool:
    """DEPRECATED: Sub-module 1 has been removed. Returns False."""
    logger.warning("delete_exception_record is DEPRECATED. Sub-module 1 has been removed.")
    return False


def export_exception_records_to_df(
    conn: sqlite3.Connection,
    filters: Optional[Dict[str, Any]] = None
) -> pd.DataFrame:
    """DEPRECATED: Sub-module 1 has been removed. Returns empty DataFrame."""
    logger.warning("export_exception_records_to_df is DEPRECATED. Sub-module 1 has been removed.")
    return pd.DataFrame()


# =============================================================================
# SECTION 4: DATABASE RECORD - SUB-MODULE 2 (REPEATED EXCEPTIONS)
# =============================================================================

# =============================================================================
# FIELD COMPATIBILITY HELPER
# =============================================================================

def get_field(exc: Dict[str, Any], *keys, default: Any = None) -> Any:
    """
    Multi-format field getter for backward compatibility.
    
    Frontend may send data with different field name formats:
    - snake_case: exception_type, from_m, max_value
    - PascalCase: FromM, ToM, Overlap
    - camelCase: maxValue, maxLocation
    - Space format: 'exception type', 'Track Type'
    
    This function tries each key in order and returns the first match.
    
    Args:
        exc: Exception dictionary
        *keys: Field names to try (in priority order)
        default: Default value if no key found
        
    Returns:
        Field value or default
        
    Example:
        exc_type = get_field(exc, 'exception_type', 'exception type', default='')
        from_m = get_field(exc, 'from_m', 'FromM', default=0)
    """
    for key in keys:
        if key in exc and exc[key] is not None:
            return exc[key]
    return default


def save_repeated_records_batch(
    conn: sqlite3.Connection,
    line: str,
    track: str,
    date_str: str,
    repeated_exceptions: List[Dict[str, Any]],
    task_no: Optional[str] = None,
    station_start: Optional[str] = None,
    station_end: Optional[str] = None,
    saved_by: Optional[str] = None,
    latest_file_name: Optional[str] = None,
    comparison_files: Optional[List[str]] = None,
    task_run_date: Optional[str] = None  # NEW: Phase 8.1 (2026-02-01)
    ,session: str = 'Mainline'
) -> Dict[str, int]:
    """
    Batch save repeated exception records (Sub-module 2).
    Automatically filters out MOCK_DATA (id starts with 'mock-').
    
    Enhanced (2026-01-31): Now includes 9 additional workflow columns:
    - reoccurrence_id: Link to historical record
    - Site Verification: verify_deadline, verify_date, verify_result, verified_by
    - Final Adjustment: adjust_deadline, adjust_date, adjust_result, adjusted_by
    
    Enhanced (2026-02-01): Added task_run_date column.
    
    Args:
        conn: Database connection
        line: Line identifier
        track: Track identifier
        date_str: Latest analysis date
        repeated_exceptions: List of repeated exception dictionaries
        task_no: Optional task number
        station_start: Optional start station
        station_end: Optional end station
        saved_by: Optional user identifier
        latest_file_name: Name of latest Excel file
        comparison_files: List of file names used in comparison
        task_run_date: Task run date (ISO format, auto-set from Save to DB action)
    
    Returns:
        Dictionary with 'saved_count' and 'filtered_mock_count'
    """
    import json
    
    saved_count = 0
    filtered_mock_count = 0
    
    comparison_files_json = json.dumps(comparison_files) if comparison_files else None
    
    # Bug-004 Debug: Log first exception structure
    if repeated_exceptions:
        first_exc = repeated_exceptions[0]
        logger.info(f"Saving batch of {len(repeated_exceptions)} records. First record sample keys: {list(first_exc.keys())}")
        logger.info(f"First record sample ID: {first_exc.get('id', 'MISSING')}")

    for exc in repeated_exceptions:
        # M5 FIX: Use get_field for multi-format compatibility (id, exception_id)
        exc_id = get_field(exc, 'exception_id', 'id', default='')
        
        # Filter out MOCK_DATA (check both 'mock-' prefix and 'MOCK_DATA' substring)
        if not exc_id or exc_id.lower().startswith('mock-') or 'MOCK_DATA' in exc_id.upper():
            filtered_mock_count += 1
            continue
        
        try:
            # M5 FIX: Use get_field for all fields that may come in different formats
            # This ensures backward compatibility with both snake_case and legacy formats
            tension_length_raw = get_field(exc, 'tension_length', 'Tension Length', default=None)
            tension_length_val = str(tension_length_raw) if tension_length_raw is not None else None
            
            conn.execute("""
                INSERT OR REPLACE INTO saved_repeated_exceptions (
                    exception_id, exception_type, level, from_m, to_m, length,
                    max_value, max_location, track_type, overlap,
                    tension_length, landmark, class, threshold_value, section,
                    previous_1, previous_2, repeat_count,
                    reoccurrence_id,
                    action, check_date, checked_by, check_result, remarks,
                    verify_deadline, verify_date, verify_result, verified_by,
                    adjust_deadline, adjust_date, adjust_result, adjusted_by,
                    line, track, session, date_str, task_run_date, task_no, station_start, station_end,
                    latest_file_name, comparison_files, saved_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                exc_id,
                get_field(exc, 'exception_type', 'exception type', default=''),
                get_field(exc, 'level', default='L3'),
                get_field(exc, 'from_m', 'FromM', default=0),
                get_field(exc, 'to_m', 'ToM', default=0),
                get_field(exc, 'length', default=None),
                get_field(exc, 'max_value', 'maxValue', default=None),
                get_field(exc, 'max_location', 'maxLocation', default=None),
                get_field(exc, 'track_type', 'Track Type', default=None),
                get_field(exc, 'overlap', 'Overlap', default=None),
                tension_length_val,
                get_field(exc, 'landmark', 'Landmark', default=None),
                get_field(exc, 'class', 'Class', default=None),
                get_field(exc, 'threshold_value', 'Threshold Value', default=None),
                get_field(exc, 'section', 'Section', default=None),
                get_field(exc, 'previous_1', 'Previous 1', default=None),
                get_field(exc, 'previous_2', 'Previous 2', default=None),
                get_field(exc, 'repeat_count', default=2),
                get_field(exc, 'reoccurrence_id', default=None),
                get_field(exc, 'action', default=None),
                get_field(exc, 'check_date', default=None),
                get_field(exc, 'checked_by', default=None),
                get_field(exc, 'check_result', default=None),
                get_field(exc, 'remarks', default=None),
                get_field(exc, 'verify_deadline', default=None),
                get_field(exc, 'verify_date', default=None),
                get_field(exc, 'verify_result', default=None),
                get_field(exc, 'verified_by', default=None),
                get_field(exc, 'adjust_deadline', default=None),
                get_field(exc, 'adjust_date', default=None),
                get_field(exc, 'adjust_result', default=None),
                get_field(exc, 'adjusted_by', default=None),
                line,
                track,
                session,
                date_str,
                task_run_date,
                task_no,
                station_start,
                station_end,
                latest_file_name,
                comparison_files_json,
                saved_by,
            ))
            saved_count += 1
        except sqlite3.Error as e:
            logger.error(f"Failed to save repeated record {exc_id}: {e}")
    
    logger.info(f"Saved {saved_count} repeated records, filtered {filtered_mock_count} mock data")
    
    return {
        'saved_count': saved_count,
        'filtered_mock_count': filtered_mock_count
    }


_REPEATED_RECORD_SECTION_SQL = """
CASE
    WHEN section IS NULL OR TRIM(section) = '' THEN 'unknown'
    WHEN UPPER(TRIM(section)) LIKE '%LOW%' THEN 'low_s1'
    WHEN UPPER(TRIM(section)) = 'MAINLINE' THEN 'mainline'
    WHEN UPPER(TRIM(section)) = 'RAC' THEN 'rac'
    WHEN UPPER(TRIM(section)) = 'LMC' THEN 'lmc'
    ELSE 'unknown'
END
""".strip()


def _canonical_repeated_record_section(section: str) -> Optional[str]:
    """Return the canonical section key for a supported section filter."""
    normalized = section.strip().lower()
    if 'low' in normalized:
        return 'low_s1'
    if normalized in {'mainline', 'rac', 'lmc', 'unknown'}:
        return normalized
    return None


def _build_repeated_record_predicates(
    filters: Optional[Dict[str, Any]] = None,
    *,
    include_section: bool = True,
) -> tuple[str, List[Any]]:
    """Build the shared parameterized WHERE clause for repeated records."""
    clauses = ["1=1"]
    params: List[Any] = []
    filters = filters or {}

    for key, column in (
        ('line', 'line'),
        ('track', 'track'),
        ('session', 'session'),
        ('level', 'level'),
        ('exception_type', 'exception_type'),
        ('class', 'class'),
        ('overlap', 'overlap'),
        ('action', 'action'),
    ):
        if filters.get(key):
            clauses.append(f"{column} = ?")
            params.append(filters[key])

    if include_section and filters.get('section'):
        section = str(filters['section'])
        canonical_section = _canonical_repeated_record_section(section)
        if canonical_section is None:
            clauses.append("section = ?")
            params.append(filters['section'])
        else:
            clauses.append(f"({_REPEATED_RECORD_SECTION_SQL}) = ?")
            params.append(canonical_section)

    if filters.get('task_number'):
        clauses.append("task_no LIKE ?")
        params.append(f"%{filters['task_number']}%")

    date_type = filters.get('date_type', 'saved_at')
    if filters.get('date_from'):
        date_from_val = _normalize_date_to_compact(filters['date_from'])
        if date_type == 'task_run_date':
            clauses.append("task_run_date >= ?")
        else:
            clauses.append("DATE(saved_at) >= ?")
            date_from_val = filters['date_from']
        params.append(date_from_val)

    if filters.get('date_to'):
        date_to_val = _normalize_date_to_compact(filters['date_to'])
        if date_type == 'task_run_date':
            clauses.append("task_run_date <= ?")
        else:
            clauses.append("DATE(saved_at) <= ?")
            date_to_val = filters['date_to']
        params.append(date_to_val)

    for key, operator, column in (
        ('from_m_min', '>=', 'from_m'),
        ('from_m_max', '<=', 'from_m'),
        ('to_m_min', '>=', 'to_m'),
        ('to_m_max', '<=', 'to_m'),
    ):
        if filters.get(key) is not None:
            clauses.append(f"{column} {operator} ?")
            params.append(filters[key])

    if filters.get('chainage_from') is not None and filters.get('chainage_to') is not None:
        clauses.extend(("from_m <= ?", "to_m >= ?"))
        params.extend((filters['chainage_to'], filters['chainage_from']))
    elif filters.get('chainage_from') is not None:
        clauses.append("to_m >= ?")
        params.append(filters['chainage_from'])
    elif filters.get('chainage_to') is not None:
        clauses.append("from_m <= ?")
        params.append(filters['chainage_to'])

    if filters.get('task_run_date_from'):
        clauses.append("task_run_date >= ?")
        params.append(filters['task_run_date_from'])
    if filters.get('task_run_date_to'):
        clauses.append("task_run_date <= ?")
        params.append(filters['task_run_date_to'])
    if filters.get('saved_at_date'):
        clauses.append("DATE(saved_at) = ?")
        params.append(filters['saved_at_date'])

    return f"WHERE {' AND '.join(clauses)}", params


def query_repeated_records(
    conn: sqlite3.Connection,
    filters: Optional[Dict[str, Any]] = None,
    limit: int = 1000,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """Query saved repeated exception records with a bounded result set."""
    where_clause, params = _build_repeated_record_predicates(filters)
    query = (
        f"SELECT * FROM saved_repeated_exceptions {where_clause} "
        "ORDER BY saved_at DESC LIMIT ? OFFSET ?"
    )
    cursor = conn.execute(query, [*params, limit, offset])
    return [dict(row) for row in cursor.fetchall()]


def update_repeated_record_workflow(
    conn: sqlite3.Connection,
    record_id: int,
    updates: Dict[str, Any]
) -> bool:
    """
    Update workflow fields for a repeated exception record.
    
    Enhanced (2026-01-31): Now supports all workflow fields including:
    - Initial Check: action, check_date, checked_by, check_result, remarks
    - Site Verification: verify_deadline, verify_date, verify_result, verified_by
    - Final Adjustment: adjust_deadline, adjust_date, adjust_result, adjusted_by
    - Reoccurrence: reoccurrence_id
    
    Args:
        conn: Database connection
        record_id: Record ID (integer)
        updates: Dictionary of field updates
    
    Returns:
        True if successful
    """
    allowed_fields = [
        # Initial Check
        'action', 'check_date', 'checked_by', 'check_result', 'remarks',
        # Site Verification (NEW)
        'verify_deadline', 'verify_date', 'verify_result', 'verified_by',
        # Final Adjustment (NEW)
        'adjust_deadline', 'adjust_date', 'adjust_result', 'adjusted_by',
        # Reoccurrence (NEW)
        'reoccurrence_id'
    ]
    
    set_clauses = []
    params: List[Any] = []
    
    for field in allowed_fields:
        if field in updates:
            set_clauses.append(f"{field} = ?")
            params.append(updates[field])
    
    if not set_clauses:
        return False
    
    # Note: last_updated is handled by trigger
    query = f"UPDATE saved_repeated_exceptions SET {', '.join(set_clauses)} WHERE record_id = ?"
    params.append(record_id)
    
    cursor = conn.execute(query, params)
    return cursor.rowcount > 0


def delete_repeated_record(conn: sqlite3.Connection, record_id: int) -> bool:
    """
    Delete a repeated exception record.
    
    Args:
        conn: Database connection
        record_id: Record ID to delete
    
    Returns:
        True if record was deleted
    """
    cursor = conn.execute(
        "DELETE FROM saved_repeated_exceptions WHERE record_id = ?",
        (record_id,)
    )
    return cursor.rowcount > 0


def _format_date_for_export(value: Optional[str]) -> str:
    """
    Format date string to YYYY/MM/DD format for Excel export.
    Feature-004: Consistent date formatting.
    """
    if not value:
        return ''
    
    # Handle YYYYMMDD format
    if len(value) == 8 and '-' not in value and '/' not in value:
        return f"{value[:4]}/{value[4:6]}/{value[6:8]}"
    
    # Handle ISO format or other date strings
    try:
        from datetime import datetime
        # Try parsing common formats
        for fmt in ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%Y/%m/%d']:
            try:
                dt = datetime.strptime(value[:19] if 'T' in value else value[:10], fmt[:len(value[:19] if 'T' in value else value[:10])])
                return dt.strftime('%Y/%m/%d')
            except ValueError:
                continue
        return value
    except Exception:
        return value


def _format_datetime_for_export(value: Optional[str]) -> str:
    """
    Format datetime string to YYYY/MM/DD HH:mm:ss format for Excel export.
    Converts UTC timestamps to UTC+8 (Hong Kong time).
    
    Phase 12 Issue 8 Fix: SQLite stores UTC via datetime('now').
    Display must show UTC+8 to match user's local time.
    """
    if not value:
        return ''
    
    try:
        from datetime import datetime, timezone, timedelta
        HK_TZ = timezone(timedelta(hours=8))
        
        # Handle ISO format (contains 'T')
        if 'T' in value:
            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            dt_hk = dt.astimezone(HK_TZ)
            return dt_hk.strftime('%Y/%m/%d %H:%M:%S')
        
        # Handle SQLite default format "YYYY-MM-DD HH:MM:SS" (assumed UTC)
        if ' ' in value and len(value) >= 19:
            dt = datetime.strptime(value[:19], '%Y-%m-%d %H:%M:%S')
            dt = dt.replace(tzinfo=timezone.utc)
            dt_hk = dt.astimezone(HK_TZ)
            return dt_hk.strftime('%Y/%m/%d %H:%M:%S')
        
        return value
    except Exception:
        return value


def export_repeated_records_to_df(
    conn: sqlite3.Connection,
    filters: Optional[Dict[str, Any]] = None
) -> pd.DataFrame:
    """
    Export repeated exception records to pandas DataFrame for Excel export.
    
    Args:
        conn: Database connection
        filters: Optional filters
    
    Returns:
        DataFrame with all matching records
    """
    records = query_repeated_records(conn, filters, limit=100000, offset=0)
    
    if not records:
        return pd.DataFrame()
    
    df = pd.DataFrame(records)
    
    # Feature-004: Format date columns to YYYY/MM/DD
    date_columns = ['check_date', 'verify_deadline', 'verify_date', 
                    'adjust_deadline', 'adjust_date', 'task_run_date']
    for col in date_columns:
        if col in df.columns:
            df[col] = df[col].apply(_format_date_for_export)
    
    # Feature-004: Format date_str to YYYY/MM/DD
    if 'date_str' in df.columns:
        df['date_str'] = df['date_str'].apply(_format_date_for_export)
    
    # Feature-004: Format datetime columns to YYYY/MM/DD HH:mm:ss
    datetime_columns = ['saved_at', 'last_updated']
    for col in datetime_columns:
        if col in df.columns:
            df[col] = df[col].apply(_format_datetime_for_export)
    
    # Phase 10.10-F: Reorder columns per spec 12.7 (matches Database Frontend 12.6)
    export_columns = [
        # Task Run Data (#1-#7)
        'task_run_date', 'line', 'track', 'session', 'section',
        'task_no', 'station_start', 'station_end',
        # Exception Details (#8-#22)
        'exception_id', 'from_m', 'to_m', 'length',
        'exception_type', 'max_value', 'max_location',
        'overlap', 'tension_length', 'track_type', 'level',
        'previous_1', 'previous_2', 'reoccurrence_id', 'remarks',
        # Initial Check (#23-#26)
        'action', 'check_date', 'checked_by', 'check_result',
        # Site Verification (#27-#30)
        'verify_deadline', 'verify_date', 'verify_result', 'verified_by',
        # Final Adjustment (#31-#34)
        'adjust_deadline', 'adjust_date', 'adjust_result', 'adjusted_by',
        # Database (#35-#36)
        'saved_at', 'last_updated',
    ]
    
    # Only include columns that exist
    df = df[[c for c in export_columns if c in df.columns]]
    
    # Phase 10.10-F: Rename columns to user-friendly display headers per spec 12.7
    display_headers = {
        'task_run_date': 'Run Date',
        'line': 'Line',
        'track': 'Track',
        'session': 'Session',
        'section': 'Section',
        'task_no': 'Task Number',
        'station_start': 'Station Start',
        'station_end': 'Station End',
        'exception_id': 'ID',
        'from_m': 'FromM',
        'to_m': 'ToM',
        'length': 'Length',
        'exception_type': 'Exception Type',
        'max_value': 'MaxValue',
        'max_location': 'MaxLocation',
        'overlap': 'Overlap',
        'tension_length': 'Tension Length',
        'track_type': 'Track Type',
        'level': 'Level',
        'previous_1': 'Previous 1',
        'previous_2': 'Previous 2',
        'reoccurrence_id': 'Reoccurrence ID',
        'remarks': 'Remarks',
        'action': 'ACTION',
        'check_date': 'CHECK DATE',
        'checked_by': 'CHECKED BY',
        'check_result': 'CHECK RESULT',
        'verify_deadline': 'VERIFY DEADLINE',
        'verify_date': 'VERIFY DATE',
        'verify_result': 'VERIFY RESULT',
        'verified_by': 'VERIFIED BY',
        'adjust_deadline': 'ADJUST DEADLINE',
        'adjust_date': 'ADJUST DATE',
        'adjust_result': 'ADJUST RESULT',
        'adjusted_by': 'ADJUSTED BY',
        'saved_at': 'Saved At',
        'last_updated': 'Last Updated',
    }
    df = df.rename(columns=display_headers)
    
    return df


# =============================================================================
# SECTION 5: REPORT TRACKING
# =============================================================================

def save_report_record(
    conn: sqlite3.Connection,
    session_id: str,
    report_type: str,
    file_name: str,
    file_path: Optional[str] = None,
    file_size: Optional[int] = None,
    generated_by: Optional[str] = None,
    include_charts: bool = True,
    include_metadata: bool = True
) -> int:
    """
    Record a report generation event.
    
    Args:
        conn: Database connection
        session_id: Related session ID
        report_type: Report type (excel, pdf, csv, json)
        file_name: Generated file name
        file_path: Full file path (optional)
        file_size: File size in bytes (optional)
        generated_by: User who generated the report
        include_charts: Whether charts were included
        include_metadata: Whether metadata sheet was included
    
    Returns:
        Report record ID
    """
    db_version = get_db_version(conn)
    schema_version = get_system_metadata(conn, 'schema_version')
    
    cursor = conn.execute("""
        INSERT INTO reports (
            session_id, report_type, file_name, file_path, file_size,
            generated_by, include_charts, include_metadata,
            db_version_at_export, schema_version
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        session_id,
        report_type,
        file_name,
        file_path,
        file_size,
        generated_by,
        1 if include_charts else 0,
        1 if include_metadata else 0,
        db_version,
        schema_version,
    ))
    
    return cursor.lastrowid


# =============================================================================
# SECTION 6: UTILITY FUNCTIONS
# =============================================================================

def get_exception_summary_by_date(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """Get exception statistics grouped by date."""
    cursor = conn.execute("SELECT * FROM v_exception_summary_by_date")
    rows = cursor.fetchall()
    return [dict(row) for row in rows]


def get_pending_critical_exceptions(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """Get all pending L1 exceptions."""
    cursor = conn.execute("SELECT * FROM v_pending_critical_exceptions")
    rows = cursor.fetchall()
    return [dict(row) for row in rows]


def get_pending_repeated_exceptions(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """Get all pending repeated exceptions requiring follow-up."""
    cursor = conn.execute("SELECT * FROM v_pending_repeated_exceptions")
    rows = cursor.fetchall()
    return [dict(row) for row in rows]


def count_exception_records(conn: sqlite3.Connection, filters: Optional[Dict[str, Any]] = None) -> int:
    """DEPRECATED: Sub-module 1 has been removed. Returns 0."""
    logger.warning("count_exception_records is DEPRECATED. Sub-module 1 has been removed.")
    return 0


def count_repeated_records(conn: sqlite3.Connection, filters: Optional[Dict[str, Any]] = None) -> int:
    """Count repeated exception records with optional filters."""
    where_clause, params = _build_repeated_record_predicates(filters)
    query = f"SELECT COUNT(*) FROM saved_repeated_exceptions {where_clause}"
    cursor = conn.execute(query, params)
    return cursor.fetchone()[0]


def get_repeated_record_section_counts(
    conn: sqlite3.Connection,
    filters: Optional[Dict[str, Any]] = None,
) -> Dict[str, int]:
    """Count canonical sections while retaining all section navigation options."""
    where_clause, params = _build_repeated_record_predicates(
        filters,
        include_section=False,
    )
    query = f"""
        SELECT {_REPEATED_RECORD_SECTION_SQL} AS section_key, COUNT(*) AS count
        FROM saved_repeated_exceptions
        {where_clause}
        GROUP BY section_key
    """
    counts = {
        'all': 0,
        'mainline': 0,
        'rac': 0,
        'low_s1': 0,
        'lmc': 0,
        'unknown': 0,
    }
    for row in conn.execute(query, params).fetchall():
        counts[row['section_key']] = row['count']
    counts['all'] = sum(count for key, count in counts.items() if key != 'all')
    return counts


# =============================================================================
# SECTION 6: CHECK 1 YEAR RECORD FEATURE (NEW 2026-01-31)
# =============================================================================

def _parse_date_flexible(value: str):
    """Parse date string from various formats (YYYYMMDD, YYYY-MM-DD, YYYY/MM/DD).

    Args:
        value: Date string to parse

    Returns:
        datetime object or None if parsing fails
    """
    from datetime import datetime

    if not value:
        return None

    # Strip whitespace and take only date portion
    clean_value = value.strip()[:10]

    formats = ['%Y%m%d', '%Y-%m-%d', '%Y/%m/%d']
    for fmt in formats:
        try:
            return datetime.strptime(clean_value, fmt)
        except ValueError:
            continue
    return None


def _parse_datetime_flexible(value: str):
    """Parse datetime string from various formats for last_updated comparison.

    Supported formats:
    - YYYY/MM/DD HH:mm:ss (Excel export format — assumed UTC+8)
    - YYYY-MM-DD HH:MM:SS (SQLite format — assumed UTC)
    - ISO format with T separator (assumed UTC)

    Args:
        value: Datetime string to parse

    Returns:
        datetime object or None if parsing fails
    """
    from datetime import datetime

    if not value or not isinstance(value, str):
        return None

    clean_value = value.strip()

    datetime_formats = [
        '%Y/%m/%d %H:%M:%S',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%dT%H:%M:%S',
    ]
    for fmt in datetime_formats:
        try:
            return datetime.strptime(clean_value[:19], fmt)
        except ValueError:
            continue
    return None


def _parse_datetime_as_utc(value: str, is_utc8: bool = False):
    """Parse datetime string and normalize to UTC for consistent comparison.

    Excel exports last_updated in UTC+8 (Hong Kong time).
    DB stores last_updated in UTC (SQLite CURRENT_TIMESTAMP).
    This function normalizes both to UTC for accurate comparison.

    Args:
        value: Datetime string to parse
        is_utc8: If True, treat the parsed time as UTC+8 and convert to UTC

    Returns:
        datetime object in UTC, or None if parsing fails
    """
    from datetime import datetime, timedelta

    HK_UTC_OFFSET_HOURS = 8

    parsed = _parse_datetime_flexible(value)
    if parsed is None:
        return None

    if is_utc8:
        return parsed - timedelta(hours=HK_UTC_OFFSET_HOURS)

    return parsed


def _is_excel_datetime_format(value: str) -> bool:
    """Check if a datetime string is in Excel export format (YYYY/MM/DD HH:mm:ss).

    Excel exports use '/' separator and are in UTC+8 timezone.
    DB uses '-' separator or 'T' separator and is in UTC.

    Args:
        value: Datetime string to check

    Returns:
        True if the format matches Excel export (UTC+8)
    """
    if not value or not isinstance(value, str):
        return False
    return '/' in value.strip()[:10]


def check_1_year_records(
    conn: sqlite3.Connection,
    exceptions: List[Dict[str, Any]],
    line: str,
    track: str,
    current_date: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Check if repeated exceptions match database records within the past 1 year.

    Match conditions (ALL must be satisfied):
    1. Line + Track (SQL WHERE)
    2. Section must match (FIX #1)
    3. Exception Type must match (FIX #2)
    4. MaxLocation falls between DB record's FromM and ToM
    5. DB record date is within 1 year before current exception date

    On match:
    - Set ACTION = "No action required (Verified within 1 year)"
    - Set exception's reoccurrence_id to matched DB exception_id
    - Append current exception ID to DB record's reoccurrence_id (FIX #4, #5)
    - Write back to database (FIX #4)

    Uses task_run_date with date_str fallback, then current_date fallback (FIX #3, #6).

    Args:
        conn: Database connection
        exceptions: List of exception dictionaries from ComparisonDataGrid
        line: Line identifier (EAL/TML)
        track: Track identifier (UP/DOWN)
        current_date: Optional fallback date when exceptions lack task_run_date (FIX #6)

    Returns:
        List of exceptions with updated action and reoccurrence_id fields
    """
    from datetime import datetime, timedelta

    ACTION_VERIFIED = 'No action required (Verified within 1 year)'
    DAYS_IN_YEAR = 365

    # FIX #1/#2: Include section and exception_type in SELECT for comparison
    cursor = conn.execute("""
        SELECT record_id, exception_id, from_m, to_m,
               task_run_date, date_str, action, exception_type,
               level, section, reoccurrence_id
        FROM saved_repeated_exceptions
        WHERE line = ? AND track = ?
        ORDER BY task_run_date DESC, date_str DESC
    """, (line, track))

    db_records = cursor.fetchall()

    if not db_records:
        logger.info(f"No database records found for {line}/{track}")
        return exceptions

    db_records_list = [dict(row) for row in db_records]

    updated_exceptions = []
    match_count = 0

    for exc in exceptions:
        updated_exc = dict(exc)  # Immutable: create a copy

        # Skip if already has a non-empty action that's not "Pending"
        # FIX #6: Support both 'action' and 'current_action' field names
        current_action = exc.get('action', '') or exc.get('current_action', '')
        if current_action and current_action != 'Pending':
            updated_exceptions.append(updated_exc)
            continue

        max_location = exc.get('maxLocation') or exc.get('max_location')
        if max_location is not None:
            try:
                max_location = float(max_location)
            except (ValueError, TypeError):
                max_location = None
        # FIX #3 + #6: Prefer task_run_date, fallback to date_str, then current_date
        exc_date_str = (
            exc.get('task_run_date', '')
            or exc.get('date_str', '')
            or (current_date or '')
        )
        exc_section = (exc.get('section', '') or exc.get('Section', '') or '').strip()
        exc_type = exc.get('exception type', '') or exc.get('exception_type', '')

        if max_location is None or not exc_date_str:
            updated_exceptions.append(updated_exc)
            continue

        exc_date = _parse_date_flexible(str(exc_date_str))
        if exc_date is None:
            updated_exceptions.append(updated_exc)
            continue

        one_year_ago = exc_date - timedelta(days=DAYS_IN_YEAR)

        match_found = False
        matched_record_id = None
        matched_exception_id = None
        matched_existing_reoccurrence = None

        for db_rec in db_records_list:
            # Exclude self-match
            if db_rec.get('exception_id') == exc.get('id'):
                continue

            # FIX #2: Compare exception_type
            db_type = db_rec.get('exception_type', '')
            if db_type != exc_type:
                continue

            # FIX #1: Compare section (empty matches empty)
            db_section = (db_rec.get('section', '') or '').strip()
            exc_section_clean = (exc_section or '').strip()
            if db_section != exc_section_clean:
                continue

            try:
                db_from_m = float(db_rec.get('from_m', 0) or 0)
                db_to_m = float(db_rec.get('to_m', 0) or 0)
            except (ValueError, TypeError):
                continue
            # FIX #3: Prefer task_run_date over date_str for DB record
            db_date_str = db_rec.get('task_run_date', '') or db_rec.get('date_str', '')

            if not db_date_str:
                continue

            db_date = _parse_date_flexible(str(db_date_str))
            if db_date is None:
                continue

            location_match = db_from_m <= max_location <= db_to_m
            time_match = one_year_ago <= db_date <= exc_date

            if location_match and time_match:
                match_found = True
                matched_record_id = db_rec.get('record_id')
                matched_exception_id = db_rec.get('exception_id')
                matched_existing_reoccurrence = db_rec.get('reoccurrence_id', '') or ''
                break

        logger.debug(
            f"Exception {exc.get('id')}: type={exc_type}, section={exc_section}, "
            f"max_location={max_location}, date={exc_date_str}, match_found={match_found}"
        )

        if match_found and matched_record_id:
            updated_exc['action'] = ACTION_VERIFIED
            updated_exc['reoccurrence_id'] = str(matched_exception_id)
            match_count += 1

            # FIX #4: Write back to database
            exc_id_to_append = exc.get('id', '')
            if exc_id_to_append:
                # FIX #5: Append to existing reoccurrence_id, not overwrite
                if matched_existing_reoccurrence:
                    new_reoccurrence = f"{matched_existing_reoccurrence}, {exc_id_to_append}"
                else:
                    new_reoccurrence = exc_id_to_append

                conn.execute("""
                    UPDATE saved_repeated_exceptions
                    SET reoccurrence_id = ?
                    WHERE record_id = ?
                """, (new_reoccurrence, matched_record_id))

            logger.debug(
                f"Match found: exception {exc.get('id')} at {max_location}m "
                f"matched DB record {matched_exception_id} (record_id={matched_record_id})"
            )

        updated_exceptions.append(updated_exc)

    conn.commit()
    logger.info(f"Check 1 year records: {match_count} matches found out of {len(exceptions)} exceptions")

    return updated_exceptions


def import_repeated_records_from_data(
    conn: sqlite3.Connection,
    records: List[Dict[str, Any]],
    line: str,
    track: str,
    date_str: str
    ,session: str = 'Mainline'
) -> Dict[str, int]:
    """
    Import repeated exception records from parsed Excel data.
    Uses Merge/Update strategy with row-level last_updated comparison.

    Matching Logic:
    - Primary: exception_id + line + track + date_str (composite key)

    Update Logic (Phase 12 Fix):
    - If Excel has last_updated AND DB has last_updated:
      - Excel newer → update DB with Excel values
      - Excel older or equal → skip (preserve DB values)
    - If Excel has no last_updated → always update (backward compatible)

    Args:
        conn: Database connection
        records: List of record dictionaries from Excel
        line: Default line if not in record
        track: Default track if not in record
        date_str: Default date if not in record

    Returns:
        Dictionary with 'created_count', 'updated_count', 'skipped_count', 'error_count'
    """
    created_count = 0
    updated_count = 0
    skipped_count = 0
    error_count = 0

    for rec in records:
        try:
            # Normalize display headers → snake_case + clean NaN
            rec = _normalize_import_record(rec)

            rec_line = rec.get('line', line)
            rec_track = rec.get('track', track)
            rec_session = rec.get('session', session) or session
            rec_date_raw = rec.get('task_run_date', '') or rec.get('date_str', '') or date_str
            rec_date = _normalize_date_to_compact(str(rec_date_raw))
            exc_id = rec.get('exception_id', '')

            if not exc_id:
                error_count += 1
                continue

            # Check if record exists by composite key
            # Try both YYYYMMDD and YYYY/MM/DD formats for matching
            rec_date_alt = f"{rec_date[:4]}/{rec_date[4:6]}/{rec_date[6:8]}" if len(rec_date) == 8 and rec_date.isdigit() else rec_date
            cursor = conn.execute("""
                SELECT record_id, last_updated
                FROM saved_repeated_exceptions
                WHERE exception_id = ? AND line = ? AND track = ? AND session = ?
                AND (date_str = ? OR date_str = ?)
            """, (exc_id, rec_line, rec_track, rec_session, rec_date, rec_date_alt))

            existing = cursor.fetchone()

            if existing:
                record_id = existing['record_id']
                db_last_updated = existing['last_updated']

                # Row-level last_updated comparison (Phase 12 Fix)
                # FIX: Timezone-aware comparison — Excel is UTC+8, DB is UTC
                excel_last_updated = rec.get('last_updated')
                if excel_last_updated and db_last_updated:
                    excel_last_updated_str = str(excel_last_updated)
                    db_last_updated_str = str(db_last_updated)

                    excel_is_utc8 = _is_excel_datetime_format(excel_last_updated_str)
                    excel_dt = _parse_datetime_as_utc(excel_last_updated_str, is_utc8=excel_is_utc8)
                    db_dt = _parse_datetime_as_utc(db_last_updated_str, is_utc8=False)

                    if excel_dt and db_dt and excel_dt <= db_dt:
                        # Excel version is older or same → skip this row
                        skipped_count += 1
                        continue

                # Excel is newer OR no last_updated in Excel → update
                update_fields = [
                    'action', 'check_date', 'checked_by', 'check_result', 'remarks',
                    'verify_deadline', 'verify_date', 'verify_result', 'verified_by',
                    'adjust_deadline', 'adjust_date', 'adjust_result', 'adjusted_by',
                    'reoccurrence_id'
                ]

                set_clauses = []
                params = []

                for field in update_fields:
                    if field in rec and rec[field] is not None:
                        set_clauses.append(f"{field} = ?")
                        params.append(rec[field])

                if set_clauses:
                    query = f"UPDATE saved_repeated_exceptions SET {', '.join(set_clauses)} WHERE record_id = ?"
                    params.append(record_id)
                    conn.execute(query, params)

                updated_count += 1
            else:
                # Insert new record
                conn.execute("""
                    INSERT INTO saved_repeated_exceptions (
                        exception_id, exception_type, level, from_m, to_m, length,
                        max_value, max_location, track_type, overlap,
                        tension_length, landmark, class, threshold_value, section,
                        previous_1, previous_2, repeat_count,
                        reoccurrence_id,
                        action, check_date, checked_by, check_result, remarks,
                        verify_deadline, verify_date, verify_result, verified_by,
                        adjust_deadline, adjust_date, adjust_result, adjusted_by,
                        line, track, session, date_str
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    exc_id,
                    rec.get('exception_type', ''),
                    rec.get('level', 'L3'),
                    rec.get('from_m', 0),
                    rec.get('to_m', 0),
                    rec.get('length'),
                    rec.get('max_value'),
                    rec.get('max_location'),
                    rec.get('track_type'),
                    rec.get('overlap'),
                    rec.get('tension_length'),
                    rec.get('landmark'),
                    rec.get('class'),
                    rec.get('threshold_value'),
                    rec.get('section'),
                    rec.get('previous_1'),
                    rec.get('previous_2'),
                    rec.get('repeat_count', 2),
                    rec.get('reoccurrence_id'),
                    rec.get('action'),
                    rec.get('check_date'),
                    rec.get('checked_by'),
                    rec.get('check_result'),
                    rec.get('remarks'),
                    rec.get('verify_deadline'),
                    rec.get('verify_date'),
                    rec.get('verify_result'),
                    rec.get('verified_by'),
                    rec.get('adjust_deadline'),
                    rec.get('adjust_date'),
                    rec.get('adjust_result'),
                    rec.get('adjusted_by'),
                    rec_line,
                    rec_track,
                    rec_session,
                    rec_date,
                ))
                created_count += 1

        except sqlite3.Error as e:
            logger.error(f"Failed to import record {rec.get('exception_id', 'unknown')}: {e}")
            error_count += 1

    logger.info(
        f"Import complete: {created_count} created, {updated_count} updated, "
        f"{skipped_count} skipped, {error_count} errors"
    )

    return {
        'created_count': created_count,
        'updated_count': updated_count,
        'skipped_count': skipped_count,
        'error_count': error_count,
    }


# =============================================================================
# CONVENIENCE FUNCTION FOR QUICK ACCESS
# =============================================================================
# Phase 10.10 - Bug 1.3: Dynamic Filter Values
# =============================================================================

# Allowed fields for get_distinct_values (SQL injection protection)
ALLOWED_DISTINCT_FIELDS = frozenset({
    'task_no', 'line', 'track', 'section', 'level',
    'exception_type', 'action', 'station_start', 'station_end',
})


def get_distinct_values(
    conn: sqlite3.Connection,
    field: str,
    line: str = None,
) -> List[str]:
    """
    Get distinct non-null values for a field from saved_repeated_exceptions.
    Used for populating dynamic dropdown filters.
    
    Args:
        conn: Database connection
        field: Column name (must be in ALLOWED_DISTINCT_FIELDS)
        line: Optional line filter (EAL/TML)
    
    Returns:
        Sorted list of unique string values (excludes NULL/empty)
    """
    if field not in ALLOWED_DISTINCT_FIELDS:
        return []

    query = f"SELECT DISTINCT {field} FROM saved_repeated_exceptions WHERE {field} IS NOT NULL AND {field} != ''"
    params: List[Any] = []

    if line:
        query += " AND line = ?"
        params.append(line)

    query += f" ORDER BY {field} ASC"

    cursor = conn.execute(query, params)
    return [str(row[0]) for row in cursor.fetchall()]


# =============================================================================
# Phase 12 Bug 4: Line Counts API
# =============================================================================

def get_line_counts(
    conn: sqlite3.Connection,
    filters: Optional[Dict[str, Any]] = None
) -> Dict[str, int]:
    """
    Get record counts grouped by line.
    Used for Tab count indicators in LineTabPanel.
    
    Args:
        conn: Database connection
        filters: Optional filters (action, level, etc.)
    
    Returns:
        Dictionary with line counts, e.g. {'EAL': 26, 'TML': 2}
    """
    query = "SELECT line, COUNT(*) as count FROM saved_repeated_exceptions WHERE 1=1"
    params: List[Any] = []
    
    if filters:
        if filters.get('action'):
            query += " AND action = ?"
            params.append(filters['action'])
        if filters.get('level'):
            query += " AND level = ?"
            params.append(filters['level'])
        if filters.get('track'):
            query += " AND track = ?"
            params.append(filters['track'])
    
    query += " GROUP BY line"
    cursor = conn.execute(query, params)
    
    result: Dict[str, int] = {line: 0 for line in ('AEL', 'TCL', 'DRL', 'KTL', 'ISL', 'TWL', 'TKL')}
    for row in cursor.fetchall():
        line = str(row['line']).strip().upper()
        if line in result:
            result[line] = int(row['count'])
    return result


# =============================================================================
# Phase 12 Issue 9: Import Header Mapping
# =============================================================================

IMPORT_HEADER_MAP: Dict[str, str] = {
    'ID': 'exception_id',
    'Exception Type': 'exception_type',
    'Line': 'line',
    'Track': 'track',
    'Section': 'section',
    'Run Date': 'task_run_date',
    'Task Number': 'task_no',
    'Station Start': 'station_start',
    'Station End': 'station_end',
    'FromM': 'from_m',
    'ToM': 'to_m',
    'Length': 'length',
    'MaxValue': 'max_value',
    'MaxLocation': 'max_location',
    'Level': 'level',
    'Overlap': 'overlap',
    'Track Type': 'track_type',
    'Tension Length': 'tension_length',
    'Landmark': 'landmark',
    'Class': 'class',
    'Previous 1': 'previous_1',
    'Previous 2': 'previous_2',
    'Reoccurrence ID': 'reoccurrence_id',
    'Remarks': 'remarks',
    'ACTION': 'action',
    'CHECK DATE': 'check_date',
    'CHECKED BY': 'checked_by',
    'CHECK RESULT': 'check_result',
    'VERIFY DEADLINE': 'verify_deadline',
    'VERIFY DATE': 'verify_date',
    'VERIFY RESULT': 'verify_result',
    'VERIFIED BY': 'verified_by',
    'ADJUST DEADLINE': 'adjust_deadline',
    'ADJUST DATE': 'adjust_date',
    'ADJUST RESULT': 'adjust_result',
    'ADJUSTED BY': 'adjusted_by',
    'Saved At': 'saved_at',
    'Last Updated': 'last_updated',
}


def _normalize_import_record(rec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a single import record:
    1. Map display headers (e.g. 'ACTION') to snake_case (e.g. 'action')
    2. Convert NaN values to None
    
    Args:
        rec: Raw record dictionary from Excel import
    
    Returns:
        Normalized record with snake_case keys and cleaned values
    """
    import math
    
    normalized: Dict[str, Any] = {}
    for key, value in rec.items():
        snake_key = IMPORT_HEADER_MAP.get(key, key)
        # Clean NaN values (pandas reads empty cells as float NaN)
        if isinstance(value, float) and (math.isnan(value) or pd.isna(value)):
            value = None
        normalized[snake_key] = value
    return normalized


# =============================================================================

def get_database() -> DatabaseManager:
    """
    Get the singleton DatabaseManager instance.
    
    Usage:
        db = get_database()
        with db.get_connection() as conn:
            records = query_exception_records(conn, filters)
    """
    return DatabaseManager()
