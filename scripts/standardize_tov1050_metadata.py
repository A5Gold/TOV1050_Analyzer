"""Build reviewable TOV640-style metadata candidates for TOV1050.

The source workbooks are never modified.  Each candidate contains canonical
wide threshold data, metre-based interval columns, bracket mappings, and a
provenance sheet that records every emitted source row.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


LINES = ("ISL", "KTL", "LAR_AEL", "LAR_TCL", "TKL", "TKS", "TWL")
MAPPING_LINE_ALIASES = {"LAR_AEL": "AEL", "LAR_TCL": "TCL"}
THRESHOLD_COLUMNS = [
    "Class", "Track Type", "Exc Type",
    "Stagger L1", "Stagger L2", "Stagger L3",
    "Wire Wear L1", "Wire Wear L2",
    "High Height L1", "High Height L2",
    "Low Height L2", "Low Height L1",
    "Wire Wear L3", "High Height L3", "Low Height L3",
]
TRACK_COLUMNS = [
    "Track Type", "Track Type FromM", "Track Type ToM", None,
    "Bracket FromM", "Tension Length", "Bracket",
]


def _number(value: Any) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _class_column(frame: pd.DataFrame) -> str:
    for name in ("Class", "Location Type", "location type"):
        if name in frame.columns:
            return name
    raise ValueError("threshold sheet has no Class/Location Type column")


def _threshold_provenance(frame: pd.DataFrame) -> list[dict[str, Any]]:
    """Record every non-empty source threshold row and its canonical mapping."""

    names = {str(c).strip().lower(): c for c in frame.columns}
    class_col = next((names[key] for key in ("class", "location type", "location_type") if key in names), None)
    track_col = next((names[key] for key in ("track type", "track_type") if key in names), None)
    exc_col = next((names[key] for key in ("exc type", "exception type", "exception_type") if key in names), None)
    min_col = next((names[key] for key in ("min", "minimum") if key in names), None)
    max_col = next((names[key] for key in ("max", "maximum") if key in names), None)
    records: list[dict[str, Any]] = []
    for source_row, row in frame.iterrows():
        values = row.tolist()
        if not any(value not in (None, "") and not pd.isna(value) for value in values):
            continue
        record: dict[str, Any] = {
            "source_sheet": "threshold",
            "source_row": int(source_row) + 2,
            "target_sheet": "threshold",
            "status": "emitted",
        }
        cls = str(row.get(class_col, "both")).strip() if class_col else "both"
        track = str(row.get(track_col, "both")).strip() if track_col else "both"
        exc = str(row.get(exc_col, "")).strip() if exc_col else ""
        record.update({"source_class": cls, "source_track_type": track, "source_exc_type": exc})
        if not exc or exc.lower() == "normal":
            record.update({"status": "skipped", "reason": "normal or empty exception type"})
            records.append(record)
            continue
        match = re.search(r"(Stagger|Wire Wear|High Height|Low Height)\s*(L[123])?", exc, re.I)
        if not match:
            record.update({"status": "invalid", "reason": "unsupported exception type"})
            records.append(record)
            continue
        base, level = match.group(1), match.group(2) or "L1"
        canonical_base = base.title() if base.lower() != "wire wear" else "Wire Wear"
        targets = ("Stagger Left", "Stagger Right") if canonical_base == "Stagger" else ({
            "Wire Wear": "Wire Wear",
            "High Height": "High Height",
            "Low Height": "Low Height",
        }[canonical_base],)
        value_column = min_col if canonical_base in ("Stagger", "High Height") else max_col
        value = _number(row.get(value_column)) if value_column else None
        if value is None:
            record.update({"status": "invalid", "reason": "threshold value is not numeric"})
        record.update({
            "target_exc_types": ", ".join(targets),
            "target_columns": ", ".join(f"{canonical_base} {level}" for _ in targets),
            "transform": f"{value_column or 'value'} -> canonical {canonical_base} {level}",
        })
        records.append(record)
    return records


def _wide_thresholds(frame: pd.DataFrame) -> pd.DataFrame:
    names = {str(c).strip().lower(): c for c in frame.columns}
    if "class" in names and any(str(c).startswith("Stagger ") for c in frame.columns):
        result = frame.copy()
        result.columns = [str(c).strip() for c in result.columns]
        return result.reindex(columns=THRESHOLD_COLUMNS)

    cls_col = _class_column(frame)
    track_col = next((names[k] for k in ("track type", "track_type") if k in names), None)
    exc_col = next((names[k] for k in ("exc type", "exception type", "exception_type") if k in names), None)
    min_col = next((names[k] for k in ("min", "minimum") if k in names), None)
    max_col = next((names[k] for k in ("max", "maximum") if k in names), None)
    if not all((track_col, exc_col)):
        raise ValueError("threshold sheet is missing Track Type or Exc Type")

    grouped: dict[tuple[str, str, str], dict[str, Any]] = {}
    for _, row in frame.iterrows():
        cls = str(row.get(cls_col, "both")).strip() or "both"
        track = str(row.get(track_col, "both")).strip() or "both"
        exc = str(row.get(exc_col, "")).strip()
        if not exc or exc.lower() == "normal":
            continue
        match = re.search(r"(Stagger|Wire Wear|High Height|Low Height)\s*(L[123])?", exc, re.I)
        if not match:
            continue
        base, level = match.group(1), match.group(2) or "L1"
        base = base.title() if base.lower() != "wire wear" else "Wire Wear"
        out_exc = {"Stagger": "Stagger Left", "Wire Wear": "Wire Wear", "High Height": "High Height", "Low Height": "Low Height"}[base]
        key = (cls, track, out_exc)
        item = grouped.setdefault(key, {"Class": cls, "Track Type": track, "Exc Type": out_exc})
        value = _number(row.get(min_col)) if base in ("Stagger", "High Height") else _number(row.get(max_col))
        if value is not None:
            item[f"{base} {level}"] = value
        # A stagger row often applies to both left and right.  Keep one row per
        # direction to match the detector contract used by the TOV640 workbook.
        if base == "Stagger":
            for direction in ("Stagger Left", "Stagger Right"):
                dkey = (cls, track, direction)
                d_item = grouped.setdefault(dkey, {"Class": cls, "Track Type": track, "Exc Type": direction})
                if value is not None:
                    d_item[f"Stagger {level}"] = value
            grouped.pop(key, None)
    return pd.DataFrame(grouped.values()).reindex(columns=THRESHOLD_COLUMNS)


def _bracket_rows(
    mapping: pd.DataFrame,
    source_sheet: str,
    target_sheet: str,
    scale: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    provenance: list[dict[str, Any]] = []
    location_col = "Location" if "Location" in mapping.columns else mapping.columns[0]
    bracket_col = "Bracket" if "Bracket" in mapping.columns else mapping.columns[1]
    for source_row, row in mapping.iterrows():
        location = _number(row.get(location_col))
        bracket = row.get(bracket_col)
        if location is None and (bracket is None or pd.isna(bracket) or not str(bracket).strip()):
            continue
        base_provenance = {
            "source_sheet": source_sheet,
            "source_row": int(source_row) + 2,
            "target_sheet": target_sheet,
        }
        if location is None:
            provenance.append({**base_provenance, "status": "invalid", "reason": "Location is not numeric"})
            continue
        if bracket is None or pd.isna(bracket) or not str(bracket).strip():
            provenance.append({**base_provenance, "status": "invalid", "reason": "Bracket is blank"})
            continue
        bracket_text = str(bracket).strip()
        tl = bracket_text.split("-", 1)[0] if "-" in bracket_text else bracket_text
        rows.append({"Track Type": None, "Track Type FromM": None, "Track Type ToM": None,
                     None: None, "Bracket FromM": location * scale,
                     "Tension Length": tl, "Bracket": bracket_text})
        provenance.append({**base_provenance, "status": "emitted",
                           "transform": "Location km -> Bracket FromM m; bracket prefix -> Tension Length"})
    return rows, provenance


def _track_rows(
    frame: pd.DataFrame,
    mapping: pd.DataFrame | None,
    source_sheet: str,
    mapping_source_sheet: str | None,
    scale: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    columns = {str(c).strip().lower(): c for c in frame.columns}
    type_col = columns.get("track type") or columns.get("track_type") or columns.get("track type ")
    start_col = columns.get("startkm") or columns.get("start_m")
    end_col = columns.get("endkm") or columns.get("end_m")
    if not (type_col and start_col and end_col):
        raise ValueError(f"{source_sheet} is missing track type/startKM/endKM")
    rows: list[dict[str, Any]] = []
    provenance: list[dict[str, Any]] = []
    for source_row, row in frame.iterrows():
        start, end = _number(row.get(start_col)), _number(row.get(end_col))
        if start is None and end is None and not str(row.get(type_col, "")).strip():
            continue
        if start is None or end is None:
            provenance.append({"source_sheet": source_sheet, "source_row": int(source_row) + 2,
                               "target_sheet": source_sheet.replace(" track type", ""),
                               "status": "invalid", "reason": "startKM/endKM is not numeric"})
            continue
        reversed_interval = end < start
        rows.append({"Track Type": str(row.get(type_col, "")).strip(),
                     "Track Type FromM": min(start, end) * scale,
                     "Track Type ToM": max(start, end) * scale,
                     None: None, "Bracket FromM": None, "Tension Length": None, "Bracket": None})
        provenance.append({"source_sheet": source_sheet, "source_row": int(source_row) + 2,
                           "target_sheet": source_sheet.replace(" track type", ""), "status": "emitted",
                           "transform": "startKM/endKM -> Track Type FromM/ToM m"
                           + ("; canonicalized min/max for directional source ordering" if reversed_interval else "")})
    if mapping is not None:
        bracket, bracket_provenance = _bracket_rows(
            mapping,
            mapping_source_sheet or f"{source_sheet} mapping",
            source_sheet.replace(" track type", ""),
            scale,
        )
        rows.extend(bracket)
        provenance.extend(bracket_provenance)
    return rows, provenance


def standardize_workbook(source: Path, mapping_book: Path, output: Path, scale: float = 1000.0) -> dict[str, Any]:
    source_sheets = pd.read_excel(source, sheet_name=None)
    mapping_sheets = pd.read_excel(mapping_book, sheet_name=None)
    line = source.stem.replace(" metadata", "")
    output.parent.mkdir(parents=True, exist_ok=True)
    provenance: list[dict[str, Any]] = []
    source_digest = hashlib.sha256(source.read_bytes()).hexdigest()
    mapping_digest = hashlib.sha256(mapping_book.read_bytes()).hexdigest()
    summary: dict[str, Any] = {
        "line": line,
        "source": str(source),
        "output": str(output),
        "mapping": str(mapping_book),
        "source_sha256": source_digest,
        "mapping_sha256": mapping_digest,
        "chainage_scale": scale,
        "sheets": {},
    }
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        threshold = _wide_thresholds(source_sheets["threshold"])
        threshold.to_excel(writer, sheet_name="threshold", index=False)
        provenance.extend(_threshold_provenance(source_sheets["threshold"]))
        summary["sheets"]["threshold"] = {"rows": len(threshold), "schema": "wide"}

        location = source_sheets.get("location type")
        if location is not None:
            lc = {str(c).strip().lower(): c for c in location.columns}
            rows = []
            for source_row, row in location.iterrows():
                start, end = _number(row.get(lc.get("startkm"))), _number(row.get(lc.get("endkm")))
                if start is None and end is None and not str(row.get(lc.get("location type"), "")).strip():
                    continue
                if start is None or end is None:
                    provenance.append({"source_sheet": "location type", "source_row": int(source_row) + 2,
                                       "target_sheet": "Exception Boundarys", "status": "invalid",
                                       "reason": "startKM/endKM is not numeric"})
                    continue
                rows.append({"Line": line, "Class": str(row.get(lc.get("location type"), "")).strip(), "C/R": None,
                             "UP Track FromM": min(start, end) * scale, "UP Track ToM": max(start, end) * scale,
                             "DN Track FromM": min(start, end) * scale, "DN Track ToM": max(start, end) * scale})
                reversed_interval = end < start
                provenance.append({"source_sheet": "location type", "source_row": int(source_row) + 2,
                                   "target_sheet": "Exception Boundarys", "status": "emitted",
                                   "transform": "startKM/endKM -> Exception Boundarys FromM/ToM m"
                                   + ("; canonicalized min/max for directional source ordering" if reversed_interval else "")})
            pd.DataFrame(rows).to_excel(writer, sheet_name="Exception Boundarys", index=False)
            summary["sheets"]["Exception Boundarys"] = {"rows": len(rows), "schema": "wide"}

        for direction in ("UT", "DT", "PL"):
            source_name = f"{direction} track type" if f"{direction} track type" in source_sheets else None
            if source_name is None:
                continue
            mapping_line = MAPPING_LINE_ALIASES.get(line, line)
            mapping_sheet = f"{mapping_line} {direction}"
            mapping = mapping_sheets.get(mapping_sheet)
            rows, rows_provenance = _track_rows(
                source_sheets[source_name], mapping, source_name,
                mapping_sheet if mapping is not None else None, scale,
            )
            pd.DataFrame(rows, columns=TRACK_COLUMNS).to_excel(writer, sheet_name=f"{line} {direction}", index=False)
            provenance.extend(rows_provenance)
            summary["sheets"][f"{line} {direction}"] = {"rows": len(rows), "schema": "wide+bracket"}

        pd.DataFrame([{"generated_at": datetime.now(timezone.utc).isoformat(), "source_workbook": str(source),
                       "source_sha256": source_digest, "mapping_workbook": str(mapping_book),
                       "mapping_sha256": mapping_digest, "chainage_unit": "m", "chainage_scale": scale,
                       "candidate_status": "review_required",
                       "note": "Candidate only; review overlaps, invalid rows, and bracket prefix mapping before activation."}]).to_excel(
            writer, sheet_name="__standardization__", index=False
        )
        pd.DataFrame(provenance).to_excel(writer, sheet_name="__provenance__", index=False)
    summary["provenance_rows"] = len(provenance)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("00 Reference Document/config"))
    parser.add_argument("--mapping", type=Path, default=Path("00 Reference Document/TOV1050 TL-BK No.xlsx"))
    parser.add_argument("--output-dir", type=Path, default=Path("docs/audits/standardized-metadata-candidates"))
    parser.add_argument("--lines", nargs="*", default=list(LINES), choices=LINES)
    args = parser.parse_args()
    summaries = []
    for line in args.lines:
        source = args.root / f"{line} metadata.xlsx"
        output = args.output_dir / f"{line} metadata (wide candidate).xlsx"
        summaries.append(standardize_workbook(source, args.mapping, output))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "manifest.json").write_text(json.dumps(summaries, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summaries, indent=2))


if __name__ == "__main__":
    main()
