"""Generate the packaged Wire Wear seed from a committed development database."""

from __future__ import annotations

import argparse
from pathlib import Path
import sqlite3
import sys


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.calculation.wear_cycle_seed import (  # noqa: E402
    SEED_FILENAME,
    metadata_fingerprints,
    write_seed_package,
)
from app.core.config import get_config_dir, get_default_db_path  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export committed normalized Wire Wear records as wear-cycle-v1 seed JSON.",
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=None,
        help="Development SQLite database. Defaults to the configured development DB path.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=f"Seed output path. Defaults to CONFIG_PATH/{SEED_FILENAME}.",
    )
    parser.add_argument(
        "--config-dir",
        type=Path,
        default=None,
        help="Metadata directory used for EAL/TML fingerprints.",
    )
    parser.add_argument(
        "--source-workstation",
        default="TOV640 Analyzer development seed",
        help="Source identity recorded in the seed envelope.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    database_path = Path(args.database or get_default_db_path()).resolve()
    config_dir = Path(args.config_dir or get_config_dir()).resolve()
    output_path = Path(args.output or (config_dir / SEED_FILENAME)).resolve()

    if not database_path.is_file():
        raise SystemExit(f"development database not found: {database_path}")

    uri = f"{database_path.as_uri()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as conn:
        conn.row_factory = sqlite3.Row
        destination = write_seed_package(
            conn,
            output_path,
            metadata_fingerprint=metadata_fingerprints(config_dir),
            source_workstation=args.source_workstation,
        )

    print(f"Wire Wear seed written to {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
