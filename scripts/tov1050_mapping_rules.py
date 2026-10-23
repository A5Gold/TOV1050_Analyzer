"""Review-only mapping policy; see docs/tov1050-metadata-rules.md."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

RULES_VERSION = "2026-10-23"
RULES_DOCUMENT = "docs/tov1050-metadata-rules.md"
_PART = r"(?=[A-Z0-9]*\d)[A-Z0-9]+"
_NORMAL = re.compile(rf"^{_PART}-{_PART}(?:\(T\))?$", re.I)
_TERMINATION = re.compile(rf"^{_PART}-(?:BWA|Fixed|Spring)(?:_[A-Z0-9]+)*$", re.I)
_MARKER = re.compile(r"^(?:SI|MID\s+POINT|POA)(?![A-Z])", re.I)
_ISOLATOR = re.compile(r"^[A-Z]{3}\d{3}$", re.I)


def classify(label: str) -> str:
    label = label.strip()
    if not label or "/" in label:
        return "unclassified"
    if _MARKER.match(label) or _ISOLATOR.fullmatch(label):
        return "landmark"
    if _TERMINATION.fullmatch(label):
        return "termination"
    if _NORMAL.fullmatch(label):
        return "normal"
    if not re.search(r"\d", label):
        return "landmark"
    return "unclassified"


def component_labels(label: str) -> list[str]:
    """Preserve order/multiplicity: duplicates must remain detectable."""
    return [part.strip() for part in label.split("/")]


def expand_mapping(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Input has source_row/from_m/bracket; output retains each source label."""
    expanded = []
    for record in records:
        for index, label in enumerate(component_labels(record["bracket"]), 1):
            expanded.append({**record, "source_bracket": record["bracket"],
                             "component_index": index, "bracket": label,
                             "classification": classify(label)})
    locations: dict[str, set[float]] = defaultdict(set)
    source_labels = {item["bracket"] for item in expanded}
    for item in expanded:
        if item["classification"] == "termination":
            locations[item["bracket"]].add(item["from_m"])
    for item in expanded:
        label = item["bracket"]
        if item["classification"] == "termination" and len(locations[label]) > 1:
            position = f"{item['from_m']:.6f}".rstrip("0").rstrip(".")
            label += f"@{position}m"
            if label in source_labels:
                raise ValueError(f"Generated termination identity collides with source: {label}")
        item["candidate_bracket"] = label
    return expanded


def provenance_components(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{key: item[key] for key in (
        "component_index", "bracket", "candidate_bracket", "classification", "from_m",
    )} for item in records]
