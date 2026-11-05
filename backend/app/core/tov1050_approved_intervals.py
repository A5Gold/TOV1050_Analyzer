"""Explicitly approved Contact geometry, isolated from review-only observations.

The optional <workbook>.approved-intervals.json sidecar is a release artifact.
Every referenced source digest and approval is checked before any value is used.
All coordinates are metres; v1 input intervals are closed on both ends.
"""
from __future__ import annotations

from bisect import bisect_right
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from .tov1050_capabilities import MetadataCapabilityError, TensionLengthInterval, sweep_approved_intervals

VERSION = "approved-contact-intervals-v1"


def _bounds(record):
    start, end = record.get("from_m"), record.get("to_m")
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
           for v in (start, end)) or start > end or record.get("closed") != "both":
        raise MetadataCapabilityError("Approved intervals require finite ordered metres and closed=both")
    return float(start), float(end)


class ApprovedIntervalProvider:
    def __init__(self, workbook):
        self.workbook = Path(workbook).resolve()
        self.path = self.workbook.with_suffix(".approved-intervals.json")
        self.digest = None
        self.contexts = {}
        if not self.path.is_file():
            return
        try:
            raw = self.path.read_bytes()
            self.digest = hashlib.sha256(raw).hexdigest()
            document = json.loads(raw)
            if not isinstance(document, dict):
                raise ValueError("Approved interval document must be an object")
            if document.get("schema_version") != VERSION or document.get("chainage_unit") != "m":
                raise ValueError("Unsupported approved interval schema/unit")
            approvals = document["approvals"]
            if not isinstance(approvals, dict):
                raise ValueError("approvals must be an object")
            for approval in approvals.values():
                if not isinstance(approval, dict):
                    raise ValueError("Each approval must be an object")
                if not all(isinstance(approval.get(k), str) and approval[k].strip()
                           for k in ("approved_by", "approved_at", "scope")):
                    raise ValueError("Approval requires approved_by, approved_at and scope")
            sources = document["sources"]
            if not isinstance(sources, dict):
                raise ValueError("sources must be an object")
            self.sources = []
            for identity, source in sources.items():
                if not isinstance(source, dict):
                    raise ValueError("Each source must be an object")
                path = (self.path.parent / source["path"]).resolve()
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                if digest != source["sha256"]:
                    raise ValueError(f"Approved interval source digest changed: {identity}")
                self.sources.append((path, digest))
            if self.workbook not in [path for path, _ in self.sources]:
                raise ValueError("Approved intervals must bind the runtime metadata workbook digest")
            if not isinstance(document["contexts"], list):
                raise ValueError("contexts must be an array")
            for context in document["contexts"]:
                if not isinstance(context, dict):
                    raise ValueError("Each context must be an object")
                key = tuple(context[k] for k in ("line", "session", "direction"))
                if not all(isinstance(v, str) and v.strip() == v and v for v in key) or key in self.contexts:
                    raise ValueError("Approved intervals require unique explicit context")
                for collection in ("tension_lengths", "landmarks", "coverage"):
                    if not isinstance(context.get(collection, []), list):
                        raise ValueError(f"{collection} must be an array")
                    for record in context.get(collection, []):
                        if not isinstance(record, dict):
                            raise ValueError("Each interval/coverage must be an object")
                        _bounds(record)
                        if (not isinstance(record.get("source_ids"), list)
                                or record.get("approval_id") not in approvals or not record.get("source_ids")):
                            raise ValueError("Every interval/coverage requires approval and source lineage")
                        if any(source not in sources for source in record["source_ids"]):
                            raise ValueError("Unknown approved interval source")
                        if collection == "tension_lengths" and record.get("wire_role") != "contact":
                            raise ValueError("Exception reports require approved Contact intervals")
                        if collection in {"tension_lengths", "landmarks"}:
                            name = record.get("tension_length" if collection == "tension_lengths" else "landmark")
                            if not isinstance(name, str) or not name.strip():
                                raise ValueError("Approved interval identity is required")
                        if collection == "coverage" and type(record.get("complete_tl_set")) is not bool:
                            raise ValueError("Coverage must explicitly declare complete_tl_set")
                intervals = [TensionLengthInterval(r["from_m"], r["to_m"], r["tension_length"],
                             r["approval_id"], ",".join(r["source_ids"]))
                             for r in context.get("tension_lengths", [])]
                atoms = sweep_approved_intervals(intervals)
                context = dict(context, atoms=atoms, starts=[a.from_m for a in atoms])
                self.contexts[key] = context
        except (KeyError, TypeError, ValueError, OSError, AttributeError) as exc:
            raise MetadataCapabilityError(f"Invalid approved interval release {self.path.name}: {exc}") from exc

    def verify_sources(self):
        if not self.digest:
            if self.path.exists():
                raise MetadataCapabilityError("Approved interval release appeared during analysis; import again")
            return
        try:
            if hashlib.sha256(self.path.read_bytes()).hexdigest() != self.digest:
                raise MetadataCapabilityError("Approved interval release changed during analysis; import again")
            for path, digest in self.sources:
                if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                    raise MetadataCapabilityError("Approved interval source changed during analysis; import again")
        except OSError as exc:
            raise MetadataCapabilityError("Approved interval release/source unavailable during analysis; import again") from exc

    def context(self, line, session, direction):
        return self.contexts.get((line, session, direction), {})

    def lookup(self, position, line, session, direction):
        context = self.context(line, session, direction)
        result = {"Tension Length": None, "Overlap": None, "Landmark": None,
                  "tl_status": "no_approved_interval", "overlap_status": "unresolved_pairing",
                  "landmark_status": "no_approved_interval"}
        if not context:
            return result
        coverage = [r for r in context.get("coverage", []) if r["from_m"] <= position <= r["to_m"]]
        complete = any(r["complete_tl_set"] for r in coverage)
        atoms = context["atoms"]
        index = bisect_right(context["starts"], position) - 1
        # Spans and endpoint atoms share starts; an exact endpoint must select
        # the closed point atom, not the following open span.
        if index >= 0 and atoms[index].closed == "neither" and position == atoms[index].from_m:
            index -= 1
        atom = atoms[index] if index >= 0 else None
        active = atom.active_tension_lengths if atom and (
            atom.from_m == position == atom.to_m or atom.from_m < position < atom.to_m) else ()
        if active:
            result.update({"Tension Length": " / ".join(active), "tl_status": "matched"})
        elif coverage:
            result["tl_status"] = "no_approved_interval" if complete else "unresolved_pairing"
        else:
            result["tl_status"] = "outside_coverage"
        if len(active) > 1:
            result.update(Overlap="Y", overlap_status="matched")
        elif len(active) == 1 and complete:
            result.update(Overlap="N", overlap_status="matched")
        else:
            result["overlap_status"] = "unresolved_pairing" if coverage else "outside_coverage"
        landmarks = sorted({r["landmark"] for r in context.get("landmarks", [])
                            if r["from_m"] <= position <= r["to_m"]})
        if len(landmarks) == 1:
            result.update(Landmark=landmarks[0], landmark_status="matched")
        elif len(landmarks) > 1:
            result["landmark_status"] = "ambiguous"
        elif not coverage:
            result["landmark_status"] = "outside_coverage"
        return result

    def map_frame(self, frame, line, session, direction):
        positions = pd.to_numeric(frame["Chainage"], errors="coerce").to_numpy(dtype=float)
        unique, inverse = np.unique(positions, return_inverse=True)
        values = [self.lookup(x, line, session, direction) for x in unique]
        for field in ("Tension Length", "Overlap", "Landmark"):
            frame[field] = np.array([r[field] for r in values], dtype=object)[inverse]
        return frame
