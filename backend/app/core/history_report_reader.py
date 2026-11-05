"""Read history report exceptions and bounded chart windows without materializing ChartData."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math
import posixpath
import re
import xml.etree.ElementTree as ET
import zipfile
import struct
from itertools import chain
import numpy as np

import pandas as pd

from .report_context import (ReportContext, ReportContextError, context_values,
                             load_report_preflight, read_report_context, sheet_records)


EXCEPTION_SHEETS = ("Low Height", "High Height", "Wire Wear", "Stagger Left", "Stagger Right")
REQUIRED_COLUMNS = {"id", "exception type", "FromM", "ToM", "maxLocation", "maxValue"}
CHART_COLUMNS = ("Chainage", *(f"{kind}{index}" for kind in ("height", "stagger", "wear")
                              for index in range(1, 5)))
CONTEXT_COLUMNS = {name for aliases in (
    ("line", "parent_line", "logical_line", "source_line"),
    ("branch", "session", "legacy_session", "section"),
    ("track", "direction", "source_track"),
    ("task_no", "task no", "station_start", "st. start", "station_end", "st. end"),
    ("task_run_date", "task run date", "run_date", "run date"),
) for name in aliases}
_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_CELL_RE = re.compile(r"([A-Z]+)")
_RENAMES = {
    "id": "id", "exception type": "exception type", "maxvalue": "maxValue",
    "maxlocation": "maxLocation", "length": "length", "level": "level",
    "startm": "FromM", "endm": "ToM", "fromm": "FromM", "tom": "ToM",
    "run date": "task_run_date", "line": "line", "track": "track",
    "task no": "task_no", "st. start": "station_start", "st. end": "station_end",
}


@dataclass
class HistoryReport:
    filename: str
    path: Path
    context: ReportContext
    exceptions: pd.DataFrame
    chart_rows: int
    chart_domain: tuple[float, float] | None


def _sheet_path(archive: zipfile.ZipFile, sheet_name: str) -> str | None:
    root = ET.fromstring(archive.read("xl/workbook.xml"))
    relations = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    targets = {item.attrib["Id"]: item.attrib.get("Target", "") for item in relations}
    sheets = root.find(f"{{{_MAIN}}}sheets")
    for sheet in sheets if sheets is not None else ():
        if sheet.attrib.get("name") != sheet_name:
            continue
        target = targets.get(sheet.attrib.get(f"{{{_REL}}}id"), "")
        if not target:
            return None
        return posixpath.normpath(target.lstrip("/") if target.startswith("/") else "xl/" + target)
    return None


def _shared_strings(archive: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    with archive.open("xl/sharedStrings.xml") as stream:
        root = ET.parse(stream).getroot()
    return ["".join(node.itertext()) for node in root]


def _column_index(reference: str) -> int:
    match = _CELL_RE.match(reference)
    result = 0
    for letter in match.group(1) if match else "":
        result = result * 26 + ord(letter) - 64
    return result - 1


def _cell_value(cell, shared_strings: list[str]):
    kind = cell.attrib.get("t")
    if kind == "inlineStr":
        inline = cell.find(f"{{{_MAIN}}}is")
        return "".join(inline.itertext()) if inline is not None else None
    value = cell.find(f"{{{_MAIN}}}v")
    if value is None or value.text is None:
        return None
    if kind == "s":
        return shared_strings[int(value.text)]
    if kind in {"str", "e"}:
        return value.text if kind == "str" else None
    if kind == "b":
        return value.text == "1"
    try:
        return float(value.text)
    except ValueError:
        return value.text


def iter_chart_rows(path: Path, wanted: set[str] | None = None):
    """Stream selected ChartData columns from XLSX XML, including dimensionless sheets."""
    with zipfile.ZipFile(path) as archive:
        target = _sheet_path(archive, "ChartData")
        if target is None:
            return
        shared_strings = _shared_strings(archive)
        with archive.open(target) as stream:
            events = ET.iterparse(stream, events=("start", "end"))
            _, root = next(events)
            headers = None
            selected = None
            sheet_data = None
            for event, element in events:
                if event == "start" and element.tag == f"{{{_MAIN}}}sheetData":
                    sheet_data = element
                if event != "end" or element.tag != f"{{{_MAIN}}}row":
                    continue
                values = {}
                for cell in element:
                    if cell.tag != f"{{{_MAIN}}}c":
                        continue
                    index = _column_index(cell.attrib.get("r", ""))
                    if index < 0 or (selected is not None and index not in selected):
                        continue
                    values[index] = _cell_value(cell, shared_strings)
                if headers is None:
                    headers = {index: str(value).strip() for index, value in values.items() if value is not None}
                    selected = {index for index, name in headers.items()
                                if wanted is None or name.casefold() in wanted}
                else:
                    yield {headers[index]: value for index, value in values.items()
                           if index in headers and (wanted is None or index in selected)}
                element.clear()
                if sheet_data is not None:
                    sheet_data.clear()


def _exception_frame(workbook) -> pd.DataFrame:
    individual = [name for name in EXCEPTION_SHEETS if name in workbook.sheetnames]
    sheets = individual or (["Summary"] if "Summary" in workbook.sheetnames else [])
    frames = []
    for name in sheets:
        records = list(sheet_records(workbook[name]))
        if not records:
            continue
        frame = pd.DataFrame.from_records(records)
        for column in tuple(frame.columns):
            canonical = _RENAMES.get(str(column).strip().casefold())
            if canonical and column != canonical:
                if canonical in frame.columns:
                    if not frame[column].equals(frame[canonical]):
                        raise ReportContextError(f"{name}: conflicting {column}/{canonical} columns", "INVALID_REPORT_SCHEMA")
                    frame = frame.drop(columns=[column])
                else:
                    frame = frame.rename(columns={column: canonical})
        if "exception type" not in frame:
            if name == "Summary":
                raise ReportContextError("Summary: missing exception type column", "INVALID_REPORT_SCHEMA")
            frame["exception type"] = name
        if name == "Summary":
            frame = frame[frame["exception type"].notna()]
        missing = REQUIRED_COLUMNS - set(frame.columns)
        if missing:
            raise ReportContextError(f"{name}: missing exception columns: {', '.join(sorted(missing))}",
                                     "INVALID_REPORT_SCHEMA")
        for column in ("FromM", "ToM", "maxLocation", "maxValue"):
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
            if not np.isfinite(frame[column].to_numpy(dtype=float)).all():
                raise ReportContextError(f"{name}: invalid numeric values in {column}", "INVALID_REPORT_SCHEMA")
        frames.append(frame)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def read_history_report(path: Path, filename: str, progress=None, *, cache_chart=False, preflight=False) -> HistoryReport:
    """Validate the complete scope and optionally persist chart signals in a leased numeric cache."""
    workbook = load_report_preflight(path, sheet_names={"Summary", "_Metadata", *EXCEPTION_SHEETS})
    try:
        exceptions = _exception_frame(workbook)
        if preflight:
            context = read_report_context(workbook, filename, chart_rows=exceptions.to_dict(orient="records"))
            return HistoryReport(filename, path, context, exceptions, 0, None)
        chart_contexts = []
        observed = set()
        sections = set()
        minimum, maximum = math.inf, -math.inf
        count = 0
        wanted = CONTEXT_COLUMNS | {name.casefold() for name in (CHART_COLUMNS if cache_chart else ("Chainage",))}
        cache = path.with_suffix(".chart.bin").open("wb") if cache_chart else None
        def observed_rows():
            try:
                for row in iter_chart_rows(path, wanted):
                    if cache is not None:
                        cache.write(struct.pack("<13d", *(float(row[name]) if isinstance(row.get(name), (int, float))
                                                         else math.nan for name in CHART_COLUMNS)))
                    yield row
            finally:
                if cache is not None:
                    cache.close()
        for row in observed_rows():
            count += 1
            value = row.get("Chainage")
            if isinstance(value, (int, float)) and math.isfinite(value):
                minimum, maximum = min(minimum, value), max(maximum, value)
            context = context_values(row)
            context["source_line"] = str(row.get("source_line") or "").strip()
            section = context.get("section", "").upper()
            if section:
                sections.add(section)
                if len(sections) > 1:
                    raise ReportContextError(f"{filename}: multiple Section values; compare each section separately.",
                                             "INCOMPATIBLE_REPORT_SCOPE")
            key = tuple(context.values())
            if key not in observed:
                observed.add(key)
                chart_contexts.append(row)
            if progress and count % 25000 == 0:
                progress(count)
        context = read_report_context(workbook, filename,
            chart_rows=chain(exceptions.to_dict(orient="records"), chart_contexts))
        return HistoryReport(filename, path, context, exceptions, count,
                             (minimum, maximum) if minimum <= maximum else None)
    finally:
        workbook.close()


def read_chart_window(path: Path, from_m: float, to_m: float, *, max_points: int = 5000,
                      preserve: tuple[float, ...] = ()) -> tuple[dict, dict]:
    """Return a bounded min/max envelope for one requested chart viewport."""
    if not (math.isfinite(from_m) and math.isfinite(to_m)):
        raise ValueError("Chart bounds must be finite")
    if from_m > to_m:
        from_m, to_m = to_m, from_m
    wanted = {column.casefold() for column in CHART_COLUMNS}
    buckets = max(1, (max_points // 2 - 16) // (2 + 2 * (len(CHART_COLUMNS) - 1)))
    extrema = [dict() for _ in range(buckets)]
    nearest = {value: (math.inf, -1, None) for value in preserve if math.isfinite(value)}
    raw = []
    over_limit = False
    count = 0
    gap_counts = {column: 0 for column in CHART_COLUMNS[1:]}
    span = max(to_m - from_m, 1e-9)
    def chart_rows():
        binary = path.with_suffix(".chart.bin")
        if not binary.exists() or binary.stat().st_size == 0:
            yield from iter_chart_rows(path, wanted)
            return
        values = np.memmap(binary, dtype="<f8", mode="r").reshape((-1, len(CHART_COLUMNS)))
        try:
            for start in range(0, len(values), 50000):
                block = values[start:start + 50000]
                mask = np.isfinite(block[:, 0]) & (block[:, 0] >= from_m) & (block[:, 0] <= to_m)
                for record in block[mask]:
                    yield dict(zip(CHART_COLUMNS, record))
        finally:
            values._mmap.close()
    for row in chart_rows():
        chainage = row.get("Chainage")
        if not isinstance(chainage, (int, float)) or not math.isfinite(chainage):
            continue
        if chainage < from_m or chainage > to_m:
            continue
        item = {column: row.get(column) for column in CHART_COLUMNS}
        for column in CHART_COLUMNS[1:]:
            value = item[column]
            item[column] = value if isinstance(value, (int, float)) and math.isfinite(value) else None
        for column in CHART_COLUMNS[1:]:
            if item[column] is None:
                gap_counts[column] += 1
        item["_gap_counts"] = gap_counts.copy()
        index = count
        count += 1
        if not over_limit:
            raw.append((index, item))
            if len(raw) > max_points:
                raw.clear()
                over_limit = True
        bucket = min(buckets - 1, int((chainage - from_m) / span * buckets))
        slot = extrema[bucket]
        slot.setdefault("first", (index, item))
        slot["last"] = (index, item)
        for column in CHART_COLUMNS[1:]:
            value = item[column]
            if value is None:
                continue
            low, high = slot.get(column, ((index, item), (index, item)))
            slot[column] = ((index, item) if value < low[1][column] else low,
                            (index, item) if value > high[1][column] else high)
        for peak, (distance, _, _) in tuple(nearest.items()):
            if abs(chainage - peak) < distance:
                nearest[peak] = (abs(chainage - peak), index, item)
    if not over_limit:
        selected = raw
    else:
        candidates = {}
        for slot in extrema:
            for value in slot.values():
                pairs = value if isinstance(value, tuple) and value and isinstance(value[0], tuple) else (value,)
                for index, item in pairs:
                    candidates[index] = item
        for _, index, item in nearest.values():
            if item is not None:
                candidates[index] = item
        selected = sorted(candidates.items())
    if over_limit:
        with_gaps = []
        previous = None
        for index, item in selected:
            if previous is not None:
                missing = [column for column in CHART_COLUMNS[1:]
                           if previous[column] is not None and item[column] is not None
                           and item["_gap_counts"][column] > previous["_gap_counts"][column]]
                if missing:
                    boundary = item.copy()
                    for column in missing:
                        boundary[column] = None
                    with_gaps.append((index, boundary))
            with_gaps.append((index, item))
            previous = item
        selected = with_gaps
    payload = {column: [row[column] for _, row in selected] for column in CHART_COLUMNS}
    return payload, {"source_points": count, "returned_points": len(selected),
                     "strategy": "raw" if not over_limit else "min_max_envelope", "from_m": from_m, "to_m": to_m,
                     "target_points": max_points}
