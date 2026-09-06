"""Validate reviewable TOV1050 metadata candidates without changing workbooks.

The validator compares each candidate with its source workbook and the
TOV1050 TL-BK mapping workbook. It reports schema drift, interval overlap,
invalid rows, unit conversion, and source-row provenance. A candidate is
never promoted to a runtime workbook by this script.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from standardize_tov1050_metadata import (
    LINES,
    MAPPING_LINE_ALIASES,
    TRACK_COLUMNS,
    THRESHOLD_COLUMNS,
    _number,
    _wide_thresholds,
)


CHAINAGE_SCALE_M_PER_KM = 1000.0
TRACK_DIRECTIONS = ("UT", "DT", "PL")
_BRACKET_ID_RE = re.compile(r"^(?:\d+|[A-Z]{1,5}\d+)-\d+$", re.IGNORECASE)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _present(value: Any) -> bool:
    if value is None:
        return False
    try:
        return not bool(pd.isna(value)) and str(value).strip() != ""
    except (TypeError, ValueError):
        return str(value).strip() != ""


def _text(value: Any) -> str:
    return "" if not _present(value) else str(value).strip()


def _is_landmark(value: Any) -> bool:
    """TL/BK marker tokens may recur; physical bracket identities may not."""
    text = _text(value)
    return bool(text) and _BRACKET_ID_RE.fullmatch(text) is None


def _token(value: Any) -> tuple[str, Any]:
    if not _present(value):
        return ("blank", "")
    number = _number(value)
    if number is not None:
        return ("number", round(number, 6))
    return ("text", _text(value))


def _row_signature(row: Iterable[Any]) -> tuple[tuple[str, Any], ...]:
    return tuple(_token(value) for value in row)


def _non_empty_rows(frame: pd.DataFrame):
    for index, row in frame.iterrows():
        if any(_present(value) for value in row.tolist()):
            yield int(index) + 2, row


def _headers(frame: pd.DataFrame) -> list[str | None]:
    result: list[str | None] = []
    for value in frame.columns:
        text = _text(value)
        result.append(None if not text or text.lower().startswith("unnamed") else text)
    return result


def _column(frame: pd.DataFrame, *names: str) -> str | None:
    aliases = {str(value).strip().casefold(): value for value in frame.columns}
    for name in names:
        if name.casefold() in aliases:
            return aliases[name.casefold()]
    return None


def _load(path: Path) -> dict[str, pd.DataFrame]:
    return pd.read_excel(path, sheet_name=None, dtype=object)


def _counter_diff(expected: Counter, actual: Counter, limit: int = 20) -> dict[str, Any]:
    missing = list((expected - actual).elements())
    extra = list((actual - expected).elements())
    return {
        "missing_count": len(missing),
        "extra_count": len(extra),
        "missing_examples": [list(item) if isinstance(item, tuple) else item for item in missing[:limit]],
        "extra_examples": [list(item) if isinstance(item, tuple) else item for item in extra[:limit]],
    }


def _interval_report(
    frame: pd.DataFrame,
    source_sheet: str,
    *,
    scale: float,
    group_by_track: bool,
) -> dict[str, Any]:
    type_col = _column(frame, "track type", "track_type", "location type", "class")
    start_col = _column(frame, "startKM", "start_m", "fromm", "track type fromm")
    end_col = _column(frame, "endKM", "end_m", "tom", "track type tom")
    result: dict[str, Any] = {
        "source_sheet": source_sheet,
        "headers": _headers(frame),
        "unit": "km" if _column(frame, "startKM", "endKM") else "m",
        "valid_row_count": 0,
        "invalid_rows": [],
        "overlap_count": 0,
        "touching_count": 0,
        "ambiguous_overlap_count": 0,
        "reversed_row_count": 0,
        "reversed_rows": [],
        "overlap_examples": [],
    }
    if not type_col or not start_col or not end_col:
        result["missing_required_columns"] = [
            name for name, value in (("track type/location type", type_col), ("startKM/fromM", start_col), ("endKM/toM", end_col)) if not value
        ]
        return result

    rows: list[dict[str, Any]] = []
    for source_row, row in _non_empty_rows(frame):
        start = _number(row.get(start_col))
        end = _number(row.get(end_col))
        label = _text(row.get(type_col))
        if start is None or end is None:
            result["invalid_rows"].append({
                "source_row": source_row,
                "label": label,
                "start": row.get(start_col),
                "end": row.get(end_col),
                "reason": "interval endpoint is not numeric",
            })
            continue
        if end < start:
            result["reversed_row_count"] += 1
            if len(result["reversed_rows"]) < 100:
                result["reversed_rows"].append({
                    "source_row": source_row,
                    "label": label,
                    "start": row.get(start_col),
                    "end": row.get(end_col),
                    "reason": "directional source ordering; canonical interval uses min/max",
                })
        from_m = min(start, end) * scale if result["unit"] == "km" else min(start, end)
        to_m = max(start, end) * scale if result["unit"] == "km" else max(start, end)
        result["valid_row_count"] += 1
        rows.append({"source_row": source_row, "label": label, "from_m": from_m, "to_m": to_m})

    for index, current in enumerate(rows):
        for previous in rows[:index]:
            if group_by_track and previous["label"] != current["label"]:
                continue
            overlap_m = min(previous["to_m"], current["to_m"]) - max(previous["from_m"], current["from_m"])
            if overlap_m > 0:
                result["overlap_count"] += 1
                previous_length = previous["to_m"] - previous["from_m"]
                current_length = current["to_m"] - current["from_m"]
                if math.isclose(previous_length, current_length, rel_tol=0, abs_tol=1e-6):
                    result["ambiguous_overlap_count"] += 1
                if len(result["overlap_examples"]) < 20:
                    result["overlap_examples"].append({
                        "label": current["label"],
                        "previous_source_row": previous["source_row"],
                        "current_source_row": current["source_row"],
                        "overlap_m": round(overlap_m, 6),
                        "previous_length_m": round(previous_length, 6),
                        "current_length_m": round(current_length, 6),
                    })
            elif math.isclose(overlap_m, 0, rel_tol=0, abs_tol=1e-6):
                result["touching_count"] += 1
    return result


def _threshold_check(source: pd.DataFrame, candidate: pd.DataFrame) -> dict[str, Any]:
    expected = _wide_thresholds(source)
    expected_headers = list(THRESHOLD_COLUMNS)
    actual_headers = [str(value).strip() for value in candidate.columns]
    report: dict[str, Any] = {
        "expected_headers": expected_headers,
        "actual_headers": actual_headers,
        "schema_match": actual_headers == expected_headers,
        "expected_rows": len(expected),
        "actual_rows": len(candidate),
    }
    if report["schema_match"]:
        expected_counter = Counter(_row_signature(row) for _, row in expected[expected_headers].iterrows())
        actual_counter = Counter(_row_signature(row) for _, row in candidate[expected_headers].iterrows())
        report["row_diff"] = _counter_diff(expected_counter, actual_counter)
        report["rows_match"] = expected_counter == actual_counter
    else:
        report["row_diff"] = {"missing_count": 0, "extra_count": 0, "missing_examples": [], "extra_examples": []}
        report["rows_match"] = False
    return report


def _location_check(source: pd.DataFrame, candidate: pd.DataFrame, line: str) -> dict[str, Any]:
    source_class = _column(source, "location type", "class")
    source_start = _column(source, "startKM")
    source_end = _column(source, "endKM")
    expected = Counter()
    for _, row in _non_empty_rows(source):
        start, end = _number(row.get(source_start)) if source_start else None, _number(row.get(source_end)) if source_end else None
        if start is not None and end is not None:
            expected[(_text(row.get(source_class)), round(min(start, end) * CHAINAGE_SCALE_M_PER_KM, 6), round(max(start, end) * CHAINAGE_SCALE_M_PER_KM, 6))] += 1
    expected_headers = ["Line", "Class", "C/R", "UP Track FromM", "UP Track ToM", "DN Track FromM", "DN Track ToM"]
    result = {
        "expected_headers": expected_headers,
        "actual_headers": _headers(candidate),
        "schema_match": _headers(candidate) == expected_headers,
        "expected_rows": sum(expected.values()),
        "actual_rows": 0,
        "rows_match": False,
    }
    candidate_line = _column(candidate, "line")
    candidate_class = _column(candidate, "class")
    candidate_start = _column(candidate, "up track fromm")
    candidate_end = _column(candidate, "up track tom")
    candidate_dn_start = _column(candidate, "dn track fromm")
    candidate_dn_end = _column(candidate, "dn track tom")
    if candidate_line and candidate_class and candidate_start and candidate_end and candidate_dn_start and candidate_dn_end:
        actual = Counter()
        for _, row in _non_empty_rows(candidate):
            start, end = _number(row.get(candidate_start)), _number(row.get(candidate_end))
            dn_start, dn_end = _number(row.get(candidate_dn_start)), _number(row.get(candidate_dn_end))
            if start is not None and end is not None and dn_start is not None and dn_end is not None:
                result["actual_rows"] += 1
                actual[(
                    _text(row.get(candidate_line)),
                    _text(row.get(candidate_class)),
                    round(start, 6),
                    round(end, 6),
                    round(dn_start, 6),
                    round(dn_end, 6),
                )] += 1
        expected_with_line: Counter = Counter()
        for (cls, start, end), count in expected.items():
            expected_with_line[(line, cls, start, end, start, end)] += count
        result["row_diff"] = _counter_diff(expected_with_line, actual)
        result["rows_match"] = expected_with_line == actual
    else:
        result["missing_required_columns"] = [
            name for name, value in (
                ("Line", candidate_line), ("Class", candidate_class),
                ("UP Track FromM", candidate_start), ("UP Track ToM", candidate_end),
                ("DN Track FromM", candidate_dn_start), ("DN Track ToM", candidate_dn_end),
            ) if not value
        ]
        result["row_diff"] = _counter_diff(expected, Counter())
    return result


def _mapping_rows(frame: pd.DataFrame, scale: float) -> tuple[Counter, list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    empty_diagnostics = {
        "marker_row_count": 0,
        "marker_rows": [],
        "exact_duplicate_identity_count": 0,
        "exact_duplicate_rows": [],
        "location_conflict_count": 0,
        "location_conflicts": [],
        "bracket_location_conflict_count": 0,
        "bracket_location_conflicts": [],
    }
    location_col = _column(frame, "location")
    bracket_col = _column(frame, "bracket")
    expected: Counter = Counter()
    invalid: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    if not location_col or not bracket_col:
        return expected, invalid, records, empty_diagnostics
    for source_row, row in _non_empty_rows(frame):
        location = _number(row.get(location_col))
        bracket = _text(row.get(bracket_col))
        if location is None or not bracket:
            invalid.append({
                "source_row": source_row,
                "location": row.get(location_col),
                "bracket": row.get(bracket_col),
                "reason": "Location must be numeric and Bracket must be non-empty",
            })
            continue
        tension_length = bracket.split("-", 1)[0]
        item = (round(location * scale, 6), tension_length, bracket)
        expected[item] += 1
        records.append({"source_row": source_row, "from_m": item[0], "tension_length": tension_length, "bracket": bracket})
    by_identity: dict[tuple[float, str], list[int]] = {}
    by_location: dict[float, list[dict[str, Any]]] = {}
    by_bracket: dict[str, list[dict[str, Any]]] = {}
    marker_rows = []
    for record in records:
        by_identity.setdefault((record["from_m"], record["bracket"]), []).append(record["source_row"])
        by_location.setdefault(record["from_m"], []).append(record)
        if _is_landmark(record["bracket"]):
            marker_rows.append(record)
        else:
            by_bracket.setdefault(record["bracket"], []).append(record)
    exact_duplicates = [
        {"from_m": location, "bracket": bracket, "source_rows": rows}
        for (location, bracket), rows in by_identity.items()
        if len(rows) > 1 and not _is_landmark(bracket)
    ]
    location_conflicts = [
        {"from_m": location, "brackets": sorted({item["bracket"] for item in items}), "source_rows": [item["source_row"] for item in items]}
        for location, items in by_location.items() if len({item["bracket"] for item in items}) > 1
    ]
    bracket_location_conflicts = [
        {"bracket": bracket, "from_m_values": sorted({item["from_m"] for item in items}), "source_rows": [item["source_row"] for item in items]}
        for bracket, items in by_bracket.items() if len({item["from_m"] for item in items}) > 1
    ]
    diagnostics = {
        "marker_row_count": len(marker_rows),
        "marker_rows": marker_rows[:100],
        "exact_duplicate_identity_count": len(exact_duplicates),
        "exact_duplicate_rows": exact_duplicates[:100],
        "location_conflict_count": len(location_conflicts),
        "location_conflicts": location_conflicts[:100],
        "bracket_location_conflict_count": len(bracket_location_conflicts),
        "bracket_location_conflicts": bracket_location_conflicts[:100],
    }
    return expected, invalid, records, diagnostics


def _candidate_mapping_rows(frame: pd.DataFrame) -> Counter:
    from_col = _column(frame, "bracket fromm")
    tension_col = _column(frame, "tension length")
    bracket_col = _column(frame, "bracket")
    result: Counter = Counter()
    if not from_col or not tension_col or not bracket_col:
        return result
    for _, row in _non_empty_rows(frame):
        from_m = _number(row.get(from_col))
        bracket = _text(row.get(bracket_col))
        tension = _text(row.get(tension_col))
        if from_m is not None and bracket:
            result[(round(from_m, 6), tension, bracket)] += 1
    return result


def _track_check(
    source: pd.DataFrame,
    candidate: pd.DataFrame,
    mapping: pd.DataFrame | None,
    *,
    source_sheet: str,
    mapping_sheet: str | None,
) -> dict[str, Any]:
    source_type = _column(source, "track type", "track_type")
    source_start = _column(source, "startKM", "start_m")
    source_end = _column(source, "endKM", "end_m")
    expected_intervals: Counter = Counter()
    invalid_rows: list[dict[str, Any]] = []
    for source_row, row in _non_empty_rows(source):
        start = _number(row.get(source_start)) if source_start else None
        end = _number(row.get(source_end)) if source_end else None
        if start is None or end is None:
            invalid_rows.append({
                "source_row": source_row,
                "start": row.get(source_start) if source_start else None,
                "end": row.get(source_end) if source_end else None,
                "reason": "startKM/endKM is not numeric",
            })
            continue
        expected_intervals[(_text(row.get(source_type)), round(min(start, end) * CHAINAGE_SCALE_M_PER_KM, 6), round(max(start, end) * CHAINAGE_SCALE_M_PER_KM, 6))] += 1

    candidate_type = _column(candidate, "track type")
    candidate_start = _column(candidate, "track type fromm")
    candidate_end = _column(candidate, "track type tom")
    actual_intervals: Counter = Counter()
    if candidate_type and candidate_start and candidate_end:
        for _, row in _non_empty_rows(candidate):
            start, end = _number(row.get(candidate_start)), _number(row.get(candidate_end))
            if start is not None and end is not None and _text(row.get(candidate_type)):
                actual_intervals[(_text(row.get(candidate_type)), round(min(start, end), 6), round(max(start, end), 6))] += 1

    expected_brackets: Counter = Counter()
    mapping_invalid: list[dict[str, Any]] = []
    mapping_diagnostics: dict[str, Any] = {}
    if mapping is not None:
        expected_brackets, mapping_invalid, _, mapping_diagnostics = _mapping_rows(mapping, CHAINAGE_SCALE_M_PER_KM)
    actual_brackets = _candidate_mapping_rows(candidate)
    return {
        "source_sheet": source_sheet,
        "mapping_sheet": mapping_sheet,
        "source_interval_rows": sum(expected_intervals.values()),
        "candidate_interval_rows": sum(actual_intervals.values()),
        "interval_diff": _counter_diff(expected_intervals, actual_intervals),
        "intervals_match": expected_intervals == actual_intervals,
        "source_invalid_rows": invalid_rows,
        "mapping_invalid_rows": mapping_invalid,
        "mapping_diagnostics": mapping_diagnostics,
        "expected_headers": _headers(pd.DataFrame(columns=TRACK_COLUMNS)),
        "actual_headers": _headers(candidate),
        "schema_match": _headers(candidate) == _headers(pd.DataFrame(columns=TRACK_COLUMNS)),
        "source_bracket_rows": sum(expected_brackets.values()),
        "candidate_bracket_rows": sum(actual_brackets.values()),
        "bracket_diff": _counter_diff(expected_brackets, actual_brackets),
        "brackets_match": expected_brackets == actual_brackets,
    }


def _provenance_check(source_sheets: dict[str, pd.DataFrame], mapping_sheets: dict[str, pd.DataFrame], candidate_sheets: dict[str, pd.DataFrame], line: str) -> dict[str, Any]:
    provenance = candidate_sheets.get("__provenance__")
    expected: dict[tuple[str, int], tuple[str, str]] = {}

    def add_source(sheet_name: str, frame: pd.DataFrame, target_sheet: str, status_resolver):
        for source_row, row in _non_empty_rows(frame):
            key = (sheet_name, source_row)
            expected[key] = (status_resolver(row), target_sheet)

    threshold = source_sheets.get("threshold")
    if threshold is not None:
        exc_col = _column(threshold, "exc type", "exception type", "exception_type")
        min_col = _column(threshold, "min", "minimum")
        max_col = _column(threshold, "max", "maximum")

        def threshold_status(row):
            exc = _text(row.get(exc_col)) if exc_col else ""
            if not exc or exc.casefold() == "normal":
                return "skipped"
            supported = any(token in exc.casefold() for token in ("stagger", "wire wear", "high height", "low height"))
            value = _number(row.get(min_col if any(token in exc.casefold() for token in ("stagger", "high height")) else max_col)) if (min_col or max_col) else None
            return "invalid" if not supported or value is None else "emitted"

        add_source("threshold", threshold, "threshold", threshold_status)

    location = source_sheets.get("location type")
    if location is not None:
        start_col, end_col = _column(location, "startKM"), _column(location, "endKM")
        add_source(
            "location type", location, "Exception Boundarys",
            lambda row: "invalid" if _number(row.get(start_col)) is None or _number(row.get(end_col)) is None else "emitted",
        )

    for direction in TRACK_DIRECTIONS:
        source_name = f"{direction} track type"
        frame = source_sheets.get(source_name)
        if frame is not None:
            start_col, end_col = _column(frame, "startKM"), _column(frame, "endKM")
            add_source(
                # The candidate sheet is line-prefixed, but the normalizer
                # deliberately records the logical target name (UT/DT/PL).
                source_name, frame, direction,
                lambda row, s=start_col, e=end_col: "invalid" if _number(row.get(s)) is None or _number(row.get(e)) is None else "emitted",
            )
        mapping_name = f"{MAPPING_LINE_ALIASES.get(line, line)} {direction}"
        mapping_frame = mapping_sheets.get(mapping_name)
        if mapping_frame is not None:
            location_col, bracket_col = _column(mapping_frame, "location"), _column(mapping_frame, "bracket")
            add_source(
                mapping_name, mapping_frame, direction,
                lambda row, l=location_col, b=bracket_col: "invalid" if _number(row.get(l)) is None or not _text(row.get(b)) else "emitted",
            )

    actual: dict[tuple[str, int], list[tuple[str, str]]] = {}
    required_columns_missing: list[str] = []
    if provenance is not None:
        source_col, row_col = _column(provenance, "source_sheet"), _column(provenance, "source_row")
        status_col, target_col = _column(provenance, "status"), _column(provenance, "target_sheet")
        required_columns_missing = [name for name, value in (("source_sheet", source_col), ("source_row", row_col), ("status", status_col), ("target_sheet", target_col)) if not value]
        if not required_columns_missing:
            for _, row in _non_empty_rows(provenance):
                try:
                    source_row = int(float(row.get(row_col)))
                except (TypeError, ValueError):
                    continue
                actual.setdefault((_text(row.get(source_col)), source_row), []).append((_text(row.get(status_col)), _text(row.get(target_col))))

    missing = sorted(set(expected).difference(actual))
    unexpected = sorted(set(actual).difference(expected))
    duplicates = sorted(key for key, values in actual.items() if len(values) != 1)
    status_mismatch = sorted(
        key for key, (expected_status, _) in expected.items()
        if key in actual and not any(status.casefold() == expected_status for status, _ in actual[key])
    )
    target_mismatch = sorted(
        key for key, (_, expected_target) in expected.items()
        if key in actual and not any(target == expected_target for _, target in actual[key])
    )
    return {
        "sheet_present": provenance is not None,
        "required_columns_missing": required_columns_missing,
        "expected_source_rows": len(expected),
        "provenance_rows": len(actual),
        "missing_source_rows": [{"source_sheet": sheet, "source_row": row} for sheet, row in missing[:100]],
        "missing_source_row_count": len(missing),
        "unexpected_source_rows": [{"source_sheet": sheet, "source_row": row} for sheet, row in unexpected[:100]],
        "unexpected_source_row_count": len(unexpected),
        "duplicate_source_rows": [{"source_sheet": sheet, "source_row": row} for sheet, row in duplicates[:100]],
        "duplicate_source_row_count": len(duplicates),
        "status_mismatch": [{"source_sheet": sheet, "source_row": row, "expected": expected[(sheet, row)][0]} for sheet, row in status_mismatch[:100]],
        "status_mismatch_count": len(status_mismatch),
        "target_mismatch": [{"source_sheet": sheet, "source_row": row, "expected": expected[(sheet, row)][1]} for sheet, row in target_mismatch[:100]],
        "target_mismatch_count": len(target_mismatch),
        "invalid_status_mismatch": [{"source_sheet": sheet, "source_row": row} for sheet, row in status_mismatch[:100] if expected[(sheet, row)][0] == "invalid"],
        "invalid_status_mismatch_count": sum(expected[key][0] == "invalid" for key in status_mismatch),
    }


def validate_workbook(source_path: Path, candidate_path: Path, mapping_path: Path, line: str) -> dict[str, Any]:
    source_sheets = _load(source_path)
    candidate_sheets = _load(candidate_path)
    mapping_sheets = _load(mapping_path)
    findings: list[dict[str, Any]] = []

    def finding(code: str, severity: str, detail: Any):
        findings.append({"code": code, "severity": severity, "detail": detail})

    threshold = _threshold_check(source_sheets["threshold"], candidate_sheets.get("threshold", pd.DataFrame()))
    if not threshold.get("schema_match") or not threshold.get("rows_match"):
        finding("threshold_schema_or_rows", "error", threshold)

    location_source = source_sheets.get("location type", pd.DataFrame())
    location_candidate = candidate_sheets.get("Exception Boundarys", pd.DataFrame())
    location = _location_check(location_source, location_candidate, line)
    if not location.get("rows_match"):
        finding("location_boundary_parity", "error", location)

    interval_reports = {
        name: _interval_report(frame, name, scale=CHAINAGE_SCALE_M_PER_KM, group_by_track=("track type" in name.lower()))
        for name, frame in source_sheets.items()
        if name.lower().endswith("track type") or name.casefold() == "location type"
    }
    for name, report in interval_reports.items():
        if report.get("missing_required_columns"):
            finding("source_interval_schema", "error", {"sheet": name, "report": report})
        if report.get("invalid_rows") or report.get("overlap_count"):
            finding("source_interval_review", "review", {"sheet": name, "report": report})
        if report.get("ambiguous_overlap_count"):
            # Overlap is valid at a wire/tension changeover. Keep it visible
            # for review, but do not reject the candidate automatically.
            finding("ambiguous_interval_overlap", "review", {"sheet": name, "report": report})

    track_reports: dict[str, Any] = {}
    for direction in TRACK_DIRECTIONS:
        source_name = f"{direction} track type"
        source_frame = source_sheets.get(source_name)
        if source_frame is None:
            continue
        candidate_name = f"{line} {direction}"
        candidate_frame = candidate_sheets.get(candidate_name)
        if candidate_frame is None:
            finding("candidate_track_sheet_missing", "error", candidate_name)
            continue
        mapping_name = f"{MAPPING_LINE_ALIASES.get(line, line)} {direction}"
        track_reports[candidate_name] = _track_check(
            source_frame,
            candidate_frame,
            mapping_sheets.get(mapping_name),
            source_sheet=source_name,
            mapping_sheet=mapping_name if mapping_name in mapping_sheets else None,
        )
        report = track_reports[candidate_name]
        if not report["intervals_match"] or not report["brackets_match"]:
            finding("candidate_track_parity", "error", {"sheet": candidate_name, "report": report})
        if report["source_invalid_rows"] or report["mapping_invalid_rows"]:
            finding("track_or_mapping_invalid_rows", "review", {"sheet": candidate_name, "report": report})
        diagnostics = report.get("mapping_diagnostics") or {}
        if any(diagnostics.get(key, 0) for key in (
            "marker_row_count",
            "exact_duplicate_identity_count",
            "location_conflict_count",
            "bracket_location_conflict_count",
        )):
            finding("mapping_identity_review", "review", {"sheet": candidate_name, "report": report})
        if diagnostics.get("bracket_location_conflict_count"):
            finding("bracket_identity_multiple_locations", "error", {"sheet": candidate_name, "report": report})

    provenance = _provenance_check(source_sheets, mapping_sheets, candidate_sheets, line)
    if (
        not provenance["sheet_present"]
        or provenance["required_columns_missing"]
        or provenance["missing_source_row_count"]
        or provenance["unexpected_source_row_count"]
        or provenance["duplicate_source_row_count"]
        or provenance["status_mismatch_count"]
        or provenance["target_mismatch_count"]
        or provenance["invalid_status_mismatch_count"]
    ):
        finding("provenance_incomplete", "error", provenance)

    standardization = candidate_sheets.get("__standardization__", pd.DataFrame())
    metadata = standardization.iloc[0].to_dict() if not standardization.empty else {}
    metadata_check = {
        "sheet_present": not standardization.empty,
        "chainage_unit": metadata.get("chainage_unit"),
        "chainage_scale": _number(metadata.get("chainage_scale")),
        "source_sha256": metadata.get("source_sha256"),
        "mapping_sha256": metadata.get("mapping_sha256"),
        "source_sha256_match": metadata.get("source_sha256") == _sha256(source_path),
        "mapping_sha256_match": metadata.get("mapping_sha256") == _sha256(mapping_path),
    }
    if (
        metadata_check["chainage_unit"] != "m"
        or metadata_check["chainage_scale"] != CHAINAGE_SCALE_M_PER_KM
        or not metadata_check["source_sha256_match"]
        or not metadata_check["mapping_sha256_match"]
    ):
        finding("candidate_metadata_provenance", "error", metadata_check)

    status = "fail" if any(item["severity"] == "error" for item in findings) else (
        "review_required" if findings else "pass"
    )
    return {
        "line": line,
        "source": str(source_path),
        "candidate": str(candidate_path),
        "mapping": str(mapping_path),
        "source_sha256": _sha256(source_path),
        "candidate_sha256": _sha256(candidate_path),
        "mapping_sha256": _sha256(mapping_path),
        "chainage_unit": "m",
        "chainage_scale": CHAINAGE_SCALE_M_PER_KM,
        "status": status,
        "threshold": threshold,
        "location": location,
        "intervals": interval_reports,
        "tracks": track_reports,
        "provenance": provenance,
        "candidate_metadata": metadata_check,
        "findings": findings,
    }


def _markdown(report: dict[str, Any]) -> str:
    lines = [
        "# TOV1050 Metadata Candidate Validation",
        "",
        f"- Generated: {report['generated_at']}",
        "- Candidate and source workbooks were read-only; no runtime workbook was modified.",
        "- Canonical Chainage policy: source Km/startKM/endKM/Location values are converted to metres at the adapter boundary.",
        "",
        "## Summary",
        "",
        "| Line | Status | Findings | Same-track overlaps | Invalid source rows | Provenance missing |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for item in report["workbooks"]:
        overlap = sum(value.get("overlap_count", 0) for value in item.get("intervals", {}).values())
        invalid = sum(len(value.get("invalid_rows", [])) for value in item.get("intervals", {}).values())
        invalid += sum(len(value.get("source_invalid_rows", [])) + len(value.get("mapping_invalid_rows", [])) for value in item.get("tracks", {}).values())
        lines.append(f"| {item['line']} | {item['status']} | {len(item['findings'])} | {overlap} | {invalid} | {item['provenance']['missing_source_row_count']} |")
    lines.extend(["", "## Findings", ""])
    for item in report["workbooks"]:
        lines.append(f"### {item['line']} ({item['status']})")
        if not item["findings"]:
            lines.append("- none")
            continue
        for issue in item["findings"]:
            detail = issue["detail"]
            if isinstance(detail, dict) and "report" in detail:
                detail = {key: detail[key] for key in ("sheet", "report") if key in detail}
            lines.append(f"- `{issue['severity']}` `{issue['code']}`: `{json.dumps(detail, ensure_ascii=False, default=str)}`")
    lines.extend([
        "",
        "## Promotion Gate",
        "",
        "Candidates with `fail` or `review_required` status remain review-only. Promote or write back a runtime workbook only after overlap, invalid-row, TL-BK mapping, and provenance findings are explicitly approved.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=Path("00 Reference Document/config"))
    parser.add_argument("--candidate-dir", type=Path, default=Path("docs/audits/standardized-metadata-candidates"))
    parser.add_argument("--mapping", type=Path, default=Path("00 Reference Document/TOV1050 TL-BK No.xlsx"))
    parser.add_argument("--output-dir", type=Path, default=Path("docs/audits"))
    parser.add_argument("--lines", nargs="*", default=list(LINES), choices=LINES)
    args = parser.parse_args()
    reports = []
    for line in args.lines:
        source = args.source_root / f"{line} metadata.xlsx"
        candidate = args.candidate_dir / f"{line} metadata (wide candidate).xlsx"
        if not source.exists() or not candidate.exists() or not args.mapping.exists():
            reports.append({"line": line, "status": "fail", "findings": [{"code": "input_missing", "severity": "error", "detail": {"source": str(source), "candidate": str(candidate), "mapping": str(args.mapping)}}], "intervals": {}, "tracks": {}, "provenance": {"missing_source_row_count": 0}})
            continue
        reports.append(validate_workbook(source, candidate, args.mapping, line))

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    report = {"generated_at": date.today().isoformat(), "workbooks": reports}
    json_path = output_dir / "2026-09-02-tov1050-metadata-candidate-validation.json"
    md_path = output_dir / "2026-09-02-tov1050-metadata-candidate-validation.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    md_path.write_text(_markdown(report), encoding="utf-8")
    print(json.dumps({"json": str(json_path), "markdown": str(md_path), "statuses": {item["line"]: item["status"] for item in reports}}, ensure_ascii=False))
    return 1 if any(item["status"] == "fail" for item in reports) else 0


if __name__ == "__main__":
    raise SystemExit(main())
