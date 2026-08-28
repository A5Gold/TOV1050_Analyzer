"""TOV1050 input, metadata and report naming contracts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


LINE_WORKBOOKS = {
    "AEL": "LAR_AEL metadata.xlsx",
    "TCL": "LAR_TCL metadata.xlsx",
    "DRL": "DRL metadata.xlsx",
    "ISL": "ISL metadata.xlsx",
    "KTL": "KTL metadata.xlsx",
    "TKL": "TKL metadata.xlsx",
    "TWL": "TWL metadata.xlsx",
}

LINE_SESSIONS = {
    "AEL": {"Mainline"},
    "TCL": {"Mainline"},
    "DRL": {"Mainline", "PL"},
    "ISL": {"Mainline"},
    "KTL": {"Mainline"},
    "TKL": {"Mainline", "TKS"},
    "TWL": {"Mainline"},
}

SESSION_ALIASES = {
    "MAINLINE": "Mainline",
    "MAIN LINE": "Mainline",
    "PL": "PL",
    "PASSING LOOP": "PL",
    "TKS": "TKS",
}


@dataclass(frozen=True)
class TOV1050FileContext:
    date_str: str
    line: str
    track: str
    station_start: str
    station_end: str


def normalize_session(session: str) -> str:
    value = str(session or "").strip().upper()
    if value not in SESSION_ALIASES:
        raise ValueError(f"Unsupported TOV1050 session: {session}")
    return SESSION_ALIASES[value]


def parse_input_filename(file_path: str | Path) -> TOV1050FileContext:
    """Parse YYYYMMDD_LINE_TRACK_STATION_START_STATION_END.csv."""
    stem = Path(file_path).stem
    match = re.fullmatch(
        r"(?P<date>\d{8})_(?P<line>[A-Za-z0-9]+)_(?P<track>[A-Za-z0-9]+)_(?P<start>[^_]+)_(?P<end>[^_]+)",
        stem,
    )
    if not match:
        raise ValueError(
            "TOV1050 input filename must be "
            "YYYYMMDD_<LINE>_<TRACK>_<STATION_START>_<STATION_END>.csv"
        )
    return TOV1050FileContext(
        date_str=match.group("date"),
        line=match.group("line").upper(),
        track=match.group("track").upper(),
        station_start=match.group("start").upper(),
        station_end=match.group("end").upper(),
    )


def build_output_filename(
    date_str: str,
    line: str,
    track: str,
    session: str,
    station_start: str,
    station_end: str,
    artifact: str,
    extension: str,
) -> str:
    """Build YYYYMMDD_LINE_TRACK_SESSION_START_END_ARTIFACT.ext."""
    session_name = normalize_session(session)
    ext = extension.lstrip(".")
    fields = [
        str(date_str).strip(),
        str(line).strip().upper(),
        str(track).strip().upper(),
        session_name.upper(),
        str(station_start).strip().upper(),
        str(station_end).strip().upper(),
        str(artifact).strip(),
    ]
    if any(not field for field in fields):
        raise ValueError("All output filename fields are required")
    return "_".join(fields) + f".{ext}"


def metadata_workbook_for(line: str, session: str, config_dir: str | Path) -> Path:
    """Resolve the approved logical line/session to a workbook."""
    logical_line = str(line).strip().upper()
    normalized_session = normalize_session(session)
    if logical_line not in LINE_WORKBOOKS:
        raise ValueError(f"Unsupported TOV1050 line: {line}")
    if normalized_session not in LINE_SESSIONS[logical_line]:
        allowed = ", ".join(sorted(LINE_SESSIONS[logical_line]))
        raise ValueError(f"Session {normalized_session!r} is not supported for {logical_line}; choose {allowed}")
    workbook_name = LINE_WORKBOOKS[logical_line]
    if logical_line == "TKL" and normalized_session == "TKS":
        workbook_name = "TKS metadata.xlsx"
    return Path(config_dir) / workbook_name


def metadata_track_sheet(session: str, track: str) -> str:
    """Return the direction sheet used by TOV1050 metadata."""
    direction = str(track).strip().upper()
    if direction not in {"UT", "DT"}:
        raise ValueError(f"Unsupported TOV1050 direction: {track}")
    return f"{direction} track type"
