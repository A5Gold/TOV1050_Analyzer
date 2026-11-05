"""Pure, review-only Contact TL boundary evidence; never runtime approval.

Input points use canonical metres and an explicit line/branch/direction. Every
source field is retained. Ordinary bracket extrema describe observations only.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
import math
import re
from typing import Any, Iterable, Mapping

BOUNDARY_REVIEW_VERSION = "contact-boundary-review-2026-10-29-v2"
_TERMINAL = re.compile(
    r"^(?P<tl>(?=[A-Z0-9]*\d)[A-Z0-9]+)-(?P<kind>BWA|Fixed|Spring)"
    r"(?P<suffix>(?:_[A-Z0-9]+)*)(?:@-?\d+(?:\.\d+)?m)?$", re.I,
)


def termination_evidence(bracket: str) -> dict[str, str] | None:
    """Recognize confirmed termination syntax and the user's Contact rule.

    A generated @position suffix is identity provenance, not a wire subtype.
    C/M are exact suffix tokens. On 2026-10-29 the user confirmed all terminals
    without C/M are Contact boundaries; retain that decision as role provenance.
    """
    match = _TERMINAL.fullmatch(str(bracket).strip())
    if not match:
        return None
    tokens = set(match["suffix"].upper().strip("_").split("_")) - {""}
    role = "ambiguous" if {"C", "M"} <= tokens else (
        "contact" if "C" in tokens else "messenger" if "M" in tokens else "contact"
    )
    return {"tension_length": match["tl"], "kind": match["kind"].lower(),
            "wire_role": role, "subtype": match["suffix"].lstrip("_"),
            "wire_role_basis": "explicit_suffix" if tokens & {"C", "M"} else "user_confirmed_untyped_contact_2026-10-29"}


def review_contact_boundaries(points: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Group evidence by exact line/branch/direction/TL; return review records.

    Required: line, branch, direction, tension_length, chainage_m, bracket,
    classification. Accepted physical classes: normal, termination. Landmark
    and unclassified points remain with the caller and never authorize a TL.
    Optional source_workbook/source_sheet/source_excel_row/component_index,
    workbook/sheet/excel_row and any other fields survive in point_evidence.
    A candidate still needs pairing/continuity/scope approval before runtime.
    """
    groups: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for original in points:
        point = deepcopy(dict(original))
        if point.get("classification") not in {"normal", "termination"}:
            continue
        key = tuple(str(point.get(field, "")).strip() for field in
                    ("line", "branch", "direction", "tension_length"))
        if not all(key):
            raise ValueError("Boundary review requires explicit line/branch/direction/TL scope")
        position = point.get("chainage_m")
        if isinstance(position, bool) or not isinstance(position, (int, float)) or not math.isfinite(position):
            raise ValueError(f"Boundary review requires finite canonical metres: {key}")
        if not str(point.get("bracket", "")).strip():
            raise ValueError(f"Boundary review requires bracket identity: {key}")
        point["chainage_m"] = float(position)
        groups[key].append(point)

    results = []
    for key, group in sorted(groups.items()):
        group.sort(key=lambda p: (p["chainage_m"], str(p["bracket"]), str(p.get("source_excel_row", ""))))
        boundaries, gaps = [], []
        if key[2].upper() not in {"UT", "DT", "UP", "DN"}:
            gaps.append("direction_scope_unresolved")
        locations: dict[str, set[float]] = defaultdict(set)
        for point in group:
            if point["classification"] == "normal":
                locations[str(point["bracket"])].add(point["chainage_m"])
                continue
            evidence = termination_evidence(point["bracket"])
            if evidence is None or evidence["tension_length"].upper() != key[3].upper():
                gaps.append("unrecognized_or_mismatched_termination")
                continue
            boundaries.append({**point, **evidence, "boundary_confirmed": True})
        if any(len(positions) > 1 for positions in locations.values()):
            gaps.append("normal_bracket_identity_multiple_locations")
        contact = sorted({p["chainage_m"] for p in boundaries if p["wire_role"] == "contact"})
        unspecified = [p for p in boundaries if p["wire_role"] in {"unspecified", "ambiguous"}]
        if unspecified:
            gaps.append("termination_contact_role_unresolved")
        if len(contact) == 0:
            gaps.append("no_contact_boundaries")
        elif len(contact) == 1:
            gaps.append("one_contact_boundary_missing_other_end")
        elif len(contact) > 2:
            gaps.append("multiple_contact_boundaries_require_segment_pairing")
        if len(group) == 1:
            gaps.append("single_point_tl")
        candidate = None
        if len(contact) == 2:
            if any(not contact[0] <= p["chainage_m"] <= contact[1] for p in group
                   if p["classification"] == "normal"):
                gaps.append("ordinary_brackets_outside_contact_pair")
            if not gaps:
                candidate = {"from_m": contact[0], "to_m": contact[1], "wire_role": "contact",
                             "closed": "both", "status": "termination_bounded_candidate",
                             "required_approval": "pairing_continuity_scope_and_coverage"}
        results.append({
            **dict(zip(("line", "branch", "direction", "tension_length"), key)),
            "review_version": BOUNDARY_REVIEW_VERSION, "chainage_unit": "m",
            "observed_from_m": group[0]["chainage_m"], "observed_to_m": group[-1]["chainage_m"],
            "point_count": len(group), "known_boundaries": boundaries,
            "contact_boundary_positions_m": contact, "candidate": candidate,
            "status": "candidate_requires_approval" if candidate else "unresolved_pairing",
            "gaps": sorted(set(gaps)), "point_evidence": group,
            "mapping_completeness": "not_guaranteed", "approved_from_m": None,
            "approved_to_m": None, "approved_by": None,
        })
    return results
