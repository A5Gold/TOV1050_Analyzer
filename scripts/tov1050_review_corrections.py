"""Explicit human-authorized candidate corrections; never writes source cells."""

import hashlib
import json
import math
from pathlib import Path


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def corrections_digest(corrections):
    return hashlib.sha256(canonical(corrections or []).encode("utf-8")).hexdigest()


def load_corrections(path: Path | None):
    corrections = json.loads(path.read_text(encoding="utf-8")) if path else []
    validate_corrections(corrections)
    return corrections


def validate_corrections(corrections):
    if not isinstance(corrections, list):
        raise ValueError("Review corrections must be a list")
    seen, ids = set(), set()
    for item in corrections:
        required = {"id", "line", "sheet", "source_row", "label", "expected", "replacement", "authorization"}
        if not isinstance(item, dict) or set(item) != required:
            raise ValueError("Review correction schema mismatch")
        if item["line"] not in ("ISL", "KTL", "LAR_AEL", "LAR_TCL", "TKL", "TKS", "TWL") or item["sheet"] not in ("UT track type", "DT track type", "PL track type"):
            raise ValueError("Review correction line/sheet is unsupported")
        if item["label"] != "Support" or type(item["source_row"]) is not int or item["source_row"] < 2:
            raise ValueError("Review corrections require an exact Support source row")
        if not all(isinstance(item[k], str) and item[k].strip() for k in ("id", "authorization")):
            raise ValueError("Review correction requires identity and authorization")
        for key in ("expected", "replacement"):
            pair = item[key]
            if not isinstance(pair, dict) or set(pair) != {"start", "end"} or not all(type(v) in (float, int) and math.isfinite(v) for v in pair.values()):
                raise ValueError("Review correction endpoints must be finite numeric pairs")
        key = (item["line"], item["sheet"], item["source_row"])
        if key in seen or item["id"] in ids:
            raise ValueError("Duplicate review correction")
        seen.add(key)
        ids.add(item["id"])


def bind_corrections(source_sheets, line, corrections=None):
    """Validate against raw source before attaching effective-value annotations."""
    corrections = [] if corrections is None else corrections
    validate_corrections(corrections)
    for frame in source_sheets.values():
        frame.attrs.pop("review_corrections", None)
    applied = []
    for item in corrections:
        if item["line"] != line:
            continue
        frame = source_sheets.get(item["sheet"])
        index = item["source_row"] - 2
        if frame is None or index >= len(frame):
            raise ValueError(f"Stale review correction {item['id']}: source row/sheet missing")
        cols = {str(c).strip().casefold(): c for c in frame.columns}
        if not {"track type", "startkm", "endkm"} <= cols.keys():
            raise ValueError(f"Stale review correction {item['id']}: columns missing")
        row = frame.iloc[index]
        original = {k: float(row[cols[c]]) for k, c in (("start", "startkm"), ("end", "endkm"))}
        if str(row[cols["track type"]]).strip() != item["label"] or original not in (item["expected"], item["replacement"]):
            raise ValueError(f"Stale review correction {item['id']}: label/endpoints changed")
        record = {**item, "original": original,
                  "application_status": "already_applied" if original == item["replacement"] else "applied"}
        frame.attrs.setdefault("review_corrections", {})[item["source_row"]] = record
        applied.append(record)
    return applied


def source_payload(item):
    payload = {key: item[key] for key in ("label", "start", "end", "output")}
    for key in ("correction", "outer_acceptance"):
        if key in item:
            payload[key] = item[key]
    return payload


def load_outer_acceptances(path: Path | None):
    records = json.loads(path.read_text(encoding="utf-8")) if path else []
    validate_outer_acceptances(records)
    return records


def validate_outer_acceptances(records):
    if not isinstance(records, list):
        raise ValueError("Outer acceptances must be a list")
    # Reuse scope, row, numeric, identity and duplicate validation.
    translated = []
    for item in records:
        if not isinstance(item, dict) or set(item) != {"id", "line", "sheet", "source_row", "label", "expected", "authorization"} or item["label"] != "non-support":
            raise ValueError("Outer acceptance schema mismatch")
        translated.append({**item, "label": "Support", "replacement": item["expected"]})
    validate_corrections(translated)


def bind_outer_acceptances(source_sheets, line, records=None):
    records = [] if records is None else records
    validate_outer_acceptances(records)
    for frame in source_sheets.values():
        frame.attrs.pop("outer_acceptances", None)
    selected = []
    for item in records:
        if item["line"] != line:
            continue
        frame = source_sheets.get(item["sheet"])
        index = item["source_row"] - 2
        if frame is None or index >= len(frame):
            raise ValueError(f"Stale outer acceptance {item['id']}: row/sheet missing")
        columns = {str(c).strip().casefold(): c for c in frame.columns}
        if not {"track type", "startkm", "endkm"} <= columns.keys():
            raise ValueError(f"Stale outer acceptance {item['id']}: columns missing")
        row = frame.iloc[index]
        original = {key: float(row[columns[col]]) for key, col in (("start", "startkm"), ("end", "endkm"))}
        if str(row[columns["track type"]]).strip() != item["label"] or original != item["expected"]:
            raise ValueError(f"Stale outer acceptance {item['id']}: label/endpoints changed")
        frame.attrs.setdefault("outer_acceptances", {})[item["source_row"]] = item
        selected.append(item)
    return selected


def review_records_check(frame, expected, records, digest):
    actual = []
    if frame is not None and "record_json" in frame:
        for value in frame["record_json"].dropna():
            try:
                actual.append(canonical(json.loads(value)))
            except (ValueError, TypeError):
                actual.append("invalid JSON")
    return dict(sheet_present=frame is not None,
                rows_match=sorted(canonical(item) for item in expected) == sorted(actual),
                digest_match=digest == corrections_digest(records), applied=expected)
