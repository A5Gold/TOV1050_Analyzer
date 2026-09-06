"""Audit TOV1050 metadata workbooks without modifying source files.

The report is intentionally conservative: it records differences and possible
data-quality issues, but never rewrites a workbook or guesses a unit.
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import date
from pathlib import Path
from typing import Any

from openpyxl import load_workbook


LINES = ["DRL", "ISL", "KTL", "LAR_AEL", "LAR_TCL", "TKL", "TKS", "TWL"]
REQUIRED_INTERVAL_HEADERS = {"track type", "startkm", "endkm"}
REQUIRED_WIDE_THRESHOLD_HEADERS = {"class", "track type", "exc type"}
REQUIRED_LONG_THRESHOLD_HEADERS = {"location type", "track type", "exc type", "min", "max"}


def _norm(value: Any) -> str:
    return "" if value is None else str(value).strip().lower()


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _sheet_rows(ws):
    rows = ws.iter_rows(values_only=True)
    header = next(rows, ())
    headers = [_norm(value) for value in header]
    return headers, rows


def _interval_audit(ws) -> dict[str, Any]:
    headers, rows = _sheet_rows(ws)
    non_empty_columns = [idx for idx, value in enumerate(headers) if value]
    header_set = set(headers)
    result: dict[str, Any] = {
        "headers": [value for value in headers if value],
        "extra_blank_columns": max(0, ws.max_column - len(non_empty_columns)),
        "missing_required_headers": sorted(REQUIRED_INTERVAL_HEADERS - header_set),
        "unit": "km" if {"startkm", "endkm"}.issubset(header_set) else "unknown",
        "row_count": 0,
        "invalid_rows": [],
        "overlap_count": 0,
        "gap_count": 0,
        "source_rows": [],
    }
    if result["missing_required_headers"]:
        return result

    track_idx = headers.index("track type")
    start_idx = headers.index("startkm")
    end_idx = headers.index("endkm")
    intervals: list[tuple[float, float, int]] = []
    for source_row, values in enumerate(rows, start=2):
        if not any(value not in (None, "") for value in values):
            continue
        result["row_count"] += 1
        track = values[track_idx] if track_idx < len(values) else None
        start = values[start_idx] if start_idx < len(values) else None
        end = values[end_idx] if end_idx < len(values) else None
        if not (_is_number(start) and _is_number(end)) or float(end) < float(start):
            result["invalid_rows"].append({"source_row": source_row, "track_type": track, "start": start, "end": end})
            continue
        intervals.append((float(start), float(end), source_row))
        result["source_rows"].append(source_row)

    intervals.sort(key=lambda item: (item[0], item[1], item[2]))
    for previous, current in zip(intervals, intervals[1:]):
        if current[0] <= previous[1]:
            result["overlap_count"] += 1
        elif current[0] > previous[1] + 0.0002:
            result["gap_count"] += 1
    return result


def _threshold_audit(ws) -> dict[str, Any]:
    headers, rows = _sheet_rows(ws)
    header_set = set(headers)
    if REQUIRED_WIDE_THRESHOLD_HEADERS.issubset(header_set):
        schema = "wide"
        required = REQUIRED_WIDE_THRESHOLD_HEADERS
    elif REQUIRED_LONG_THRESHOLD_HEADERS.issubset(header_set):
        schema = "long"
        required = REQUIRED_LONG_THRESHOLD_HEADERS
    else:
        schema = "unknown"
        required = REQUIRED_WIDE_THRESHOLD_HEADERS
    non_empty_columns = [value for value in headers if value]
    return {
        "schema": schema,
        "headers": non_empty_columns,
        "missing_required_headers": sorted(required - header_set),
        "extra_blank_columns": max(0, ws.max_column - len(non_empty_columns)),
        "row_count": sum(1 for values in rows if any(value not in (None, "") for value in values)),
    }


def _workbook_audit(path: Path) -> dict[str, Any]:
    workbook = load_workbook(path, read_only=True, data_only=False)
    sheets: dict[str, Any] = {}
    for ws in workbook.worksheets:
        if _norm(ws.title) == "threshold":
            sheets[ws.title] = _threshold_audit(ws)
        elif {"track type", "startkm", "endkm"}.issubset({_norm(value) for value in next(ws.iter_rows(min_row=1, max_row=1, values_only=True), ())}):
            sheets[ws.title] = _interval_audit(ws)
        else:
            headers = [_norm(value) for value in next(ws.iter_rows(min_row=1, max_row=1, values_only=True), ())]
            sheets[ws.title] = {
                "schema": "other",
                "headers": [value for value in headers if value],
                "extra_blank_columns": max(0, ws.max_column - sum(bool(value) for value in headers)),
                "row_count": max(0, ws.max_row - 1),
            }
    return {"path": str(path), "sheet_names": workbook.sheetnames, "sheets": sheets}


def _mapping_audit(path: Path) -> dict[str, Any]:
    workbook = load_workbook(path, read_only=True, data_only=False)
    result: dict[str, Any] = {"path": str(path), "sheets": {}}
    for ws in workbook.worksheets:
        headers = [_norm(value) for value in next(ws.iter_rows(min_row=1, max_row=1, values_only=True), ())]
        location_idx = headers.index("location") if "location" in headers else None
        bracket_idx = headers.index("bracket") if "bracket" in headers else None
        rows = 0
        invalid = []
        values: list[float] = []
        if location_idx is not None and bracket_idx is not None:
            for source_row, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                location = row[location_idx] if location_idx < len(row) else None
                bracket = row[bracket_idx] if bracket_idx < len(row) else None
                if location in (None, "") and bracket in (None, ""):
                    continue
                rows += 1
                if not _is_number(location) or bracket in (None, ""):
                    invalid.append({"source_row": source_row, "location": location, "bracket": bracket})
                else:
                    values.append(float(location))
        result["sheets"][ws.title] = {
            "headers": [value for value in headers if value],
            "unit": "km (source) -> m (canonical adapter)",
            "row_count": rows,
            "invalid_rows": invalid,
            "min_location_km": min(values) if values else None,
            "max_location_km": max(values) if values else None,
        }
    return result


def _markdown(report: dict[str, Any]) -> str:
    lines = [
        "# TOV1050 Metadata Audit",
        "",
        f"- Generated: {report['generated_at']}",
        "- Source workbooks were read-only; no workbook was modified.",
        "- Canonical Chainage policy: source `Km`/`startKM`/`endKM`/`Location` values are converted to metres at the adapter boundary.",
        "",
        "## Runtime Workbooks",
        "",
        "| Line | Threshold schema | Sheets | Interval overlaps | Invalid rows | Flags |",
        "|---|---|---:|---:|---:|---|",
    ]
    for line, audit in report["runtime"].items():
        threshold = audit["sheets"].get("threshold", {})
        intervals = [value for value in audit["sheets"].values() if "overlap_count" in value]
        overlap = sum(value.get("overlap_count", 0) for value in intervals)
        invalid = sum(len(value.get("invalid_rows", [])) for value in audit["sheets"].values())
        flags = []
        if threshold.get("schema") != "wide":
            flags.append("threshold not wide")
        if threshold.get("extra_blank_columns"):
            flags.append("threshold blank columns")
        if overlap:
            flags.append("interval overlap")
        if invalid:
            flags.append("invalid rows")
        lines.append(f"| {line} | {threshold.get('schema', 'unknown')} | {len(audit['sheet_names'])} | {overlap} | {invalid} | {', '.join(flags) or 'none'} |")
    lines.extend(["", "## TL-BK Mapping", "", "| Sheet | Rows | Invalid rows | Source unit |", "|---|---:|---:|---|"])
    for sheet, audit in report["mapping"]["sheets"].items():
        lines.append(f"| {sheet} | {audit['row_count']} | {len(audit['invalid_rows'])} | {audit['unit']} |")
    lines.extend([
        "",
        "## Next Actions",
        "",
        "1. Review every `interval overlap` and `invalid rows` entry against the source workbook before editing.",
        "2. Convert each runtime workbook threshold sheet to the approved TOV640-style wide schema while preserving source-row provenance.",
        "3. Generate mapping sheets using `FromM`/`ToM`/`Bracket` names and retain source km values in the audit metadata.",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output-dir", type=Path, default=Path("docs/audits"))
    args = parser.parse_args()
    root = args.root.resolve()
    output_dir = (root / args.output_dir).resolve() if not args.output_dir.is_absolute() else args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    runtime = {}
    for line in LINES:
        path = root / "config" / f"{line} metadata.xlsx"
        runtime[line] = _workbook_audit(path) if path.exists() else {"path": str(path), "missing": True, "sheet_names": [], "sheets": {}}
    mapping_path = root / "00 Reference Document" / "TOV1050 TL-BK No.xlsx"
    report = {
        "generated_at": date.today().isoformat(),
        "runtime": runtime,
        "mapping": _mapping_audit(mapping_path) if mapping_path.exists() else {"path": str(mapping_path), "missing": True, "sheets": {}},
    }
    json_path = output_dir / "2026-09-02-tov1050-metadata-audit.json"
    md_path = output_dir / "2026-09-02-tov1050-metadata-audit.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(_markdown(report), encoding="utf-8")
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
