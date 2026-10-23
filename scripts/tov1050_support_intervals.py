"""Review-only Support-based non-support derivation. Never edits sources."""

from __future__ import annotations

import math
from decimal import Decimal, ROUND_HALF_UP

import pandas as pd

POLICY_VERSION = "support-2026-10-23-v1"
TICK = Decimal("0.0001")
DERIVATION_COLUMNS = ["source_sheet", "target_sheet", "policy_version", "derived_key",
                      "track_type", "from_km", "to_km", "from_m", "to_m", "anchors_json"]


def numeric(value):
    try:
        value = float(str(value).replace(",", ""))
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None


def text(value):
    return "" if value is None or pd.isna(value) else str(value).strip()


def tick(value):
    return Decimal(str(value)).quantize(TICK, rounding=ROUND_HALF_UP)


def location_envelope(source_sheets: dict) -> tuple[float, float] | None:
    frame = source_sheets.get("location type")
    if frame is None:
        return None
    columns = {str(c).strip().casefold(): c for c in frame.columns}
    start, end = columns.get("startkm"), columns.get("endkm")
    if start is None or end is None:
        return None
    pairs = [(numeric(row[start]), numeric(row[end])) for _, row in frame.iterrows()]
    values = [value for pair in pairs if None not in pair for value in pair]
    return (min(values), max(values)) if values else None


def reconstruct(frame: pd.DataFrame, sheet: str, bounds: tuple[float, float] | None = None) -> dict:
    """Return expected intervals, source disposition and anchor derivations.

    Only bounded interior non-support is replaced. Original outer intervals
    remain visible with a review finding. Invalid anchors never create a gap.
    """
    columns = {str(c).strip().casefold(): c for c in frame.columns}
    type_col = columns.get("track type", columns.get("track_type"))
    start_col, end_col = columns.get("startkm"), columns.get("endkm")
    result = dict(active=False, intervals=[], sources=[], derived=[], issues=[], retained_edges=[])
    if type_col is None or start_col is None or end_col is None:
        return result
    source = []
    for index, row in frame.iterrows():
        if not any(text(v) for v in row):
            continue
        source.append(dict(source_row=int(index) + 2, label=text(row.get(type_col)),
                           start=numeric(row.get(start_col)), end=numeric(row.get(end_col))))
    result["active"] = any(item["label"].casefold() in ("support", "non-support") for item in source)
    if not result["active"]:
        return result
    anchors = []
    for item in source:
        if item["label"].casefold() != "support":
            continue
        start, end = item["start"], item["end"]
        reason = None
        if start is None or end is None:
            reason = "Support endpoint is not finite/numeric"
        elif end < start:
            reason = "Support endpoints are reversed"
        elif abs(Decimal(str(start)) - tick(start)) > Decimal("0.000000001") or abs(Decimal(str(end)) - tick(end)) > Decimal("0.000000001"):
            reason = "Support endpoint is outside the four-decimal km grid"
        elif bounds and (start < bounds[0] - 1e-9 or end > bounds[1] + 1e-9):
            reason = "Support is outside the source location envelope (including ORCR); check units/value"
        if reason:
            result["issues"].append(dict(code="invalid_support_anchor", **item, reason=reason))
        else:
            anchors.append({**item, "a": tick(start), "b": tick(end)})
    anchors.sort(key=lambda x: (x["a"], x["b"], x["source_row"]))
    if not anchors:
        result["issues"].append(dict(code="no_valid_support_anchors", reason="Cannot rebuild non-support without a valid Support"))
    for item in source:
        entry = {**item, "status": "emitted", "output": None}
        start, end = item["start"], item["end"]
        is_non_support = item["label"].casefold() == "non-support"
        if is_non_support and anchors:
            outside = start is not None and end is not None and (
                min(start, end) < float(anchors[0]["a"]) or max(start, end) > float(anchors[-1]["b"]))
            if outside:
                result["retained_edges"].append(item)
            else:
                entry["status"] = "superseded"
        if entry["status"] == "emitted":
            if start is None or end is None:
                entry["status"] = "invalid"
            else:
                entry["output"] = dict(label=item["label"], from_m=round(min(start, end) * 1000, 6),
                                       to_m=round(max(start, end) * 1000, 6))
                result["intervals"].append(entry["output"])
        result["sources"].append(entry)
    for left, right in zip(anchors, anchors[1:]):
        if right["a"] <= left["b"]:
            result["issues"].append(dict(code="overlapping_support_anchors", source_rows=[left["source_row"], right["source_row"]],
                                         reason="Duplicate or overlapping Support anchors; no gap emitted"))
            continue
        start, end = left["b"] + TICK, right["a"] - TICK
        if start > end:
            continue  # Adjacent grid positions have no representable inner point.
        anchors_payload = [{key: anchor[key] for key in ("source_row", "start", "end")} for anchor in (left, right)]
        record = dict(source_sheet=sheet, target_sheet=sheet.replace(" track type", ""),
                      policy_version=POLICY_VERSION, derived_key=f"{sheet}|{left['b']:.4f}|{right['a']:.4f}",
                      track_type="non-support", from_km=f"{start:.4f}", to_km=f"{end:.4f}",
                      from_m=float(start * 1000), to_m=float(end * 1000), anchors=anchors_payload)
        result["derived"].append(record)
        result["intervals"].append(dict(label="non-support", from_m=record["from_m"], to_m=record["to_m"]))
    result["intervals"].sort(key=lambda x: (x["from_m"], x["to_m"], x["label"]))
    return result
