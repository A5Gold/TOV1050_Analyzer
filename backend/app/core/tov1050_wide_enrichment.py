"""Read user-maintained wide metadata without losing interval endpoint semantics."""
from __future__ import annotations

from bisect import bisect_right
import hashlib
import math
import re

import numpy as np
import pandas as pd

from .tov1050_capabilities import MetadataCapabilityError


VERSION = "wide-excel-enrichment-2026-11-05-v1"
HEADERS = {"Landmark FromM", "Landmark ToM", "Landmark", "Overlap FromM",
           "Overlap ToM", "Overlap", "Tension Length", "Track Type",
           "Track Type FromM", "Track Type ToM", "Interval Closed"}


def _text(value):
    if value is None or pd.isna(value):
        return ""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(int(value)) if float(value).is_integer() else str(value)
    return str(value).strip()


def _bounds(row, lower, upper, location):
    try:
        if isinstance(row[lower], bool) or isinstance(row[upper], bool):
            raise ValueError("boolean coordinates")
        start = float(_text(row[lower]).replace(",", ""))
        end = float(_text(row[upper]).replace(",", ""))
        if not math.isfinite(start) or not math.isfinite(end) or start > end:
            raise ValueError("invalid bounds")
    except (ValueError, TypeError) as exc:
        raise MetadataCapabilityError(f"{location}: {lower}/{upper} require finite ordered metres") from exc
    return start, end


def _contains(record, position):
    return ((record["from_m"] < position or
             record["closed"] in {"both", "left"} and record["from_m"] == position)
            and (position < record["to_m"] or
                 record["closed"] in {"both", "right"} and record["to_m"] == position))


def _index(records):
    records.sort(key=lambda r: (r["from_m"], r["to_m"]))
    maximum = -math.inf
    ends = []
    for record in records:
        maximum = max(maximum, record["to_m"])
        ends.append(maximum)
    return {"records": records, "starts": [r["from_m"] for r in records], "ends": ends}


def _matches(index, position):
    offset = bisect_right(index["starts"], position) - 1
    found = []
    while offset >= 0 and index["ends"][offset] >= position:
        record = index["records"][offset]
        if _contains(record, position):
            found.append(record)
        offset -= 1
    return found


class WideExcelEnrichmentProvider:
    """The workbook is authoritative; no separately edited sidecar is needed.

    A:C, D:G and H:J are independent lists. K controls only D:E. FromM=ToM
    landmarks are buffered in memory; explicit ranges never receive a buffer.
    """

    version = VERSION
    source_kind = "wide_excel"

    def __init__(self, manager, sheets):
        self.manager = manager
        self.workbook = manager.config_path.resolve()
        self.path = self.workbook
        self.digest = hashlib.sha256(self.workbook.read_bytes()).hexdigest()
        self.sources = [(self.workbook, self.digest)]
        self.sheets = sheets
        self.contexts = {}

    @classmethod
    def detect(cls, manager):
        sheets = set()
        with pd.ExcelFile(manager.config_path) as book:
            for sheet in book.sheet_names:
                if not re.fullmatch(r"(?:LAR_AEL|LAR_TCL|ISL|KTL|TKL|TKS|TWL|DRL) (?:UT|DT|PL)", sheet):
                    continue
                headers = set(pd.read_excel(book, sheet_name=sheet, nrows=0).columns)
                marker = {"Overlap FromM", "Overlap ToM", "Landmark FromM", "Landmark ToM", "Interval Closed"}
                if not headers.intersection(marker):
                    continue  # The legacy seven-column point layout still uses its sidecar.
                missing = HEADERS - headers
                if missing:
                    raise MetadataCapabilityError(f"{sheet}: incomplete wide enrichment columns: {', '.join(sorted(missing))}")
                sheets.add(sheet)
        return cls(manager, sheets) if sheets else None

    def verify_sources(self):
        try:
            if hashlib.sha256(self.workbook.read_bytes()).hexdigest() != self.digest:
                raise MetadataCapabilityError("Wide metadata source changed during analysis; import again")
        except OSError as exc:
            raise MetadataCapabilityError("Wide metadata source unavailable during analysis; import again") from exc

    def context(self, line, session, direction):
        identity, route = self.manager._wide_context(line, session, direction)
        sheet = f"{identity} {route}"
        if sheet not in self.sheets:
            raise MetadataCapabilityError(f"{self.workbook.name}: missing wide enrichment sheet {sheet}")
        if sheet in self.contexts:
            return self.contexts[sheet]
        frame = self.manager._load_sheet(sheet)
        atoms, landmarks = [], []
        for index, row in frame.iterrows():
            location = f"{self.workbook.name}/{sheet}/Excel row {index + 2}"
            if any(_text(row[c]) for c in ("Overlap FromM", "Overlap ToM", "Overlap", "Tension Length")):
                start, end = _bounds(row, "Overlap FromM", "Overlap ToM", location)
                closed = _text(row["Interval Closed"]).lower()
                if closed not in {"both", "neither", "left", "right"} or start == end and closed != "both":
                    raise MetadataCapabilityError(f"{location}: invalid Interval Closed for TL interval")
                tls = tuple(sorted(set(x.strip() for x in re.split(r"[,/]", _text(row["Tension Length"])) if x.strip())))
                overlap = _text(row["Overlap"]).upper()
                expected = "Y" if len(tls) > 1 else "N" if tls else ""
                if overlap and overlap != expected:
                    raise MetadataCapabilityError(f"{location}: Overlap disagrees with listed Tension Length set")
                atoms.append(dict(from_m=start, to_m=end, closed=closed,
                                  active_tension_lengths=tls, excel_row=int(index + 2)))
            if any(_text(row[c]) for c in ("Landmark FromM", "Landmark ToM", "Landmark")):
                start, end = _bounds(row, "Landmark FromM", "Landmark ToM", location)
                label = _text(row["Landmark"])
                if not label:
                    raise MetadataCapabilityError(f"{location}: Landmark name is required")
                buffered = start == end
                original = (start, end)
                if buffered:
                    start, end = start - 100.0, end + 100.0
                landmarks.append(dict(from_m=start, to_m=end, closed="both", landmark=label,
                                      source_from_m=original[0], source_to_m=original[1],
                                      point_buffer_m=100 if buffered else 0, excel_row=int(index + 2)))
        context = dict(atoms=atoms, tension_lengths=atoms, landmarks=landmarks,
                       tl_index=_index(atoms), landmark_index=_index(landmarks), source_sheet=sheet)
        self.contexts[sheet] = context
        return context

    def lookup(self, position, line, session, direction):
        context = self.context(line, session, direction)
        result = {"Tension Length": None, "Overlap": None, "Landmark": None,
                  "tl_status": "outside_coverage", "overlap_status": "outside_coverage",
                  "landmark_status": "no_landmark_match", "source_kind": self.source_kind,
                  "source_sheet": context["source_sheet"], "enrichment_version": self.version}
        if not math.isfinite(position):
            return result
        matches = _matches(context["tl_index"], position)
        active = sorted({tl for record in matches for tl in record["active_tension_lengths"]})
        if active:
            result.update({"Tension Length": " / ".join(active), "Overlap": "Y" if len(active) > 1 else "N",
                           "tl_status": "matched", "overlap_status": "matched"})
        elif matches:
            result.update(tl_status="no_tl_interval", overlap_status="unknown")
        found = _matches(context["landmark_index"], position)
        names = sorted({record["landmark"] for record in found})
        if len(names) == 1:
            result.update(Landmark=names[0], landmark_status="matched")
        elif len(names) > 1:
            result.update(Landmark=" / ".join(names), landmark_status="matched", landmark_candidates=names)
        if found:
            result["landmark_source_rows"] = sorted({record["excel_row"] for record in found})
        return result

    def map_frame(self, frame, line, session, direction):
        positions = pd.to_numeric(frame["Chainage"], errors="coerce").to_numpy(dtype=float)
        unique, inverse = np.unique(positions, return_inverse=True)
        values = [self.lookup(x, line, session, direction) for x in unique]
        for field in ("Tension Length", "Overlap", "Landmark"):
            frame[field] = np.array([r[field] for r in values], dtype=object)[inverse]
        return frame

    def intervals_frame(self, line, session, direction, *, landmarks=False):
        context = self.context(line, session, direction)
        records = context["landmarks"] if landmarks else context["atoms"]
        values, intervals = [], []
        for record in records:
            intervals.append(pd.Interval(record["from_m"], record["to_m"], closed=record["closed"]))
            if landmarks:
                values.append({"Landmark": record["landmark"]})
            else:
                tls = record["active_tension_lengths"]
                values.append({"Overlap": "Y" if len(tls) > 1 else "N" if tls else None,
                               "Tension Length": " / ".join(tls) or None})
        # Object index preserves mixed closure; never coerce into closed-both.
        columns = ["Landmark"] if landmarks else ["Overlap", "Tension Length"]
        return pd.DataFrame(values, columns=columns, index=pd.Index(intervals, dtype=object))
