"""TOV1050 metadata semantics v1. Observations never authorize geometry."""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
import hashlib
import json
import math

import pandas as pd


class MetadataCapabilityError(ValueError):
    """A consumer requires metadata that has no approved physical geometry."""


@dataclass(frozen=True)
class TensionLengthInterval:
    from_m: float
    to_m: float
    tension_length: str
    approval: str
    source: str

    def __post_init__(self):
        if (not all(math.isfinite(v) for v in (self.from_m, self.to_m))
                or self.from_m > self.to_m or not self.tension_length.strip()
                or not self.approval.strip() or not self.source.strip()):
            raise ValueError("TL interval requires finite ordered metres, identity, approval and source")


@dataclass(frozen=True)
class OverlapInterval:
    from_m: float
    to_m: float
    closed: str
    active_tension_lengths: tuple[str, ...]
    state: str
    sources: tuple[str, ...]


def sweep_approved_intervals(intervals: list[TensionLengthInterval]) -> list[OverlapInterval]:
    """Closed input intervals -> exact endpoint atoms + open spans, no grid guess.

    Endpoint contact remains a point, never an artificial nonzero overlap.
    Empty active sets inside the observation domain remain unknown.
    These atoms must not be flattened to the legacy closed-both mapper.
    """
    events = defaultdict(lambda: {"start": [], "end": []})
    for index, interval in enumerate(intervals):
        events[interval.from_m]["start"].append(index)
        events[interval.to_m]["end"].append(index)
    positions = sorted(events)
    active = set()
    result = []

    def atom(start, end, closed, indices):
        tls = tuple(sorted({intervals[i].tension_length for i in indices}))
        state = "overlap" if len(tls) > 1 else "known_non_overlap" if tls else "unknown"
        result.append(OverlapInterval(start, end, closed, tls, state,
                                     tuple(sorted({intervals[i].source for i in indices}))))

    for offset, position in enumerate(positions):
        active.update(events[position]["start"])
        atom(position, position, "both", active)
        active.difference_update(events[position]["end"])
        if offset + 1 < len(positions):
            atom(position, positions[offset + 1], "neither", active)
    return result


POINT_COLUMNS = ["chainage_m", "tension_length", "bracket", "classification",
                 "workbook", "sheet", "excel_row", "source_workbook", "source_sheet",
                 "source_excel_row", "source_bracket", "component_index"]


class TOV1050CapabilitiesMixin:
    """Read native points separately; approved TL geometry is not yet supplied."""

    def _point_frame(self, line, section, track):
        if not self._uses_wide_intervals():
            return pd.DataFrame(columns=POINT_COLUMNS)
        identity, direction = self._wide_context(line, section, track)
        sheet = f"{identity} {direction}"
        # The companion layout keeps point rows on a distinct sheet.
        if f"{sheet} Brackets" in self._interval_sheet_names:
            sheet += " Brackets"
        frame = self._load_sheet(sheet)
        required = {"Bracket FromM", "Tension Length", "Bracket"}
        if not required.issubset(frame.columns):
            return pd.DataFrame(columns=POINT_COLUMNS)
        provenance = defaultdict(deque)
        standard = {}
        if "__standardization__" in self._interval_sheet_names:
            rows = self._load_sheet("__standardization__")
            if not rows.empty:
                standard = rows.iloc[0].to_dict()
        if "__provenance__" in self._interval_sheet_names:
            for row in self._load_sheet("__provenance__").to_dict("records"):
                source_identity = identity.removeprefix("LAR_")
                if row.get("source_sheet") not in {f"{identity} {direction}", f"{source_identity} {direction}"}:
                    continue
                payload = row.get("components_json")
                if not isinstance(payload, str):
                    continue
                for component in json.loads(payload):
                    key = (float(component["from_m"]), str(component["candidate_bracket"]))
                    provenance[key].append({**component, **row})
        result = []
        for index, row in frame.iterrows():
            if pd.isna(row["Bracket FromM"]) and pd.isna(row["Bracket"]):
                continue
            try:
                position = float(row["Bracket FromM"])
                if not math.isfinite(position) or pd.isna(row["Bracket"]) or not str(row["Bracket"]).strip():
                    raise ValueError("invalid point")
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{self.config_path.name}/{sheet}/Excel row {index + 2}: invalid BracketPoint") from exc
            bracket = str(row["Bracket"]).strip()
            matches = provenance[(position, bracket)]
            source = matches.popleft() if matches else {}
            classification = source.get("classification", "unclassified")
            value = row["Tension Length"]
            tl = "" if pd.isna(value) else str(int(value)) if isinstance(value, float) and value.is_integer() else str(value).strip()
            result.append(dict(chainage_m=position, tension_length=tl, bracket=bracket,
                               classification=classification, workbook=str(self.config_path),
                               sheet=sheet, excel_row=int(index + 2),
                               source_workbook=standard.get("mapping_workbook", ""),
                               source_sheet=source.get("source_sheet", ""),
                               source_excel_row=source.get("source_row", ""),
                               source_bracket=source.get("source_bracket", bracket),
                               component_index=source.get("component_index", "")))
        return pd.DataFrame(result, columns=POINT_COLUMNS)

    def get_bracket_points(self, line, section, track):
        frame = self._point_frame(line, section, track)
        return frame.loc[frame.classification.isin(["normal", "termination"])].reset_index(drop=True)

    def get_landmark_points(self, line, section, track):
        frame = self._point_frame(line, section, track)
        return frame.loc[frame.classification.eq("landmark")].reset_index(drop=True)

    def get_capabilities(self, line, section, track):
        """available describes usable records, not certified full-line coverage."""
        points = self._point_frame(line, section, track)
        capabilities = {}
        for name, getter in (
            ("thresholds", lambda: self.get_all_thresholds()),
            ("class_intervals", lambda: self.get_exception_boundaries(line, track, section)),
            ("track_intervals", lambda: self.get_track_type_intervals(line, section, track)),
        ):
            data = getter()  # Required errors must escape the detector's fallback.
            capabilities[name] = dict(status="available" if len(data) else "unavailable",
                                      count=len(data), reason="" if len(data) else "No usable records")
        unknown = int(points.classification.eq("unclassified").sum())
        for name, classes in (("bracket_points", ["normal", "termination"]), ("landmark_points", ["landmark"])):
            count = int(points.classification.isin(classes).sum())
            capabilities[name] = dict(status="partial" if unknown else "available" if count else "unavailable",
                                      count=count, reason=f"{unknown} points lack classification provenance" if unknown else "" if count else "No classified point records")
        for name in ("tension_length_intervals", "overlap_intervals", "landmark_intervals"):
            capabilities[name] = dict(status="unavailable", count=0,
                                      reason="No approved physical interval source; observed bracket envelopes and landmark points are not intervals")
        return dict(schema_version="tov1050-metadata-capabilities-v1", workbook=str(self.config_path),
                    workbook_sha256=hashlib.sha256(self.config_path.read_bytes()).hexdigest(),
                    line=line, session=section, direction=track, chainage_unit="m",
                    enrichment_version="tov640-first-nonempty-v1", overlap_state="unknown",
                    capabilities=capabilities)

    def require_tension_length_intervals(self, line, track, section):
        raise MetadataCapabilityError(
            f"{self.config_path.name}/{line}/{section}/{track}: missing approved "
            "TensionLengthInterval FromM/ToM and TL scope policy; bracket observations "
            "cannot authorize wear lookup. Supply reviewed physical boundaries and approval provenance."
        )

    def get_measurement_coverage(self, chainages, line, section, track):
        """Audit actual retained measurements, independently of sheet availability."""
        positions = pd.Series(chainages, dtype=float)
        wide = self._uses_wide_intervals()
        track_sheet = (" ".join(self._wide_context(line, section, track)) if wide
                       else self._get_direction_sheet(section, track))
        audit = {}
        for name, sheet, intervals in (
            ("class_intervals", "Exception Boundarys" if wide else "location type",
             self.get_exception_boundaries(line, track, section)),
            ("track_intervals", track_sheet, self.get_track_type_intervals(line, section, track)),
        ):
            _, missing = intervals.index.get_indexer_non_unique(positions)
            audit[name] = dict(sheet=sheet, total_rows=len(positions), uncovered_rows=len(missing),
                               first_uncovered_chainages_m=positions.iloc[missing[:20]].tolist())
        return audit

    def require_measurement_coverage(self, chainages, line, section, track):
        audit = self.get_measurement_coverage(chainages, line, section, track)
        gaps = [f"{name} sheet={value['sheet']}: {value['uncovered_rows']}/{value['total_rows']} "
                f"uncovered rows; Chainage_m={value['first_uncovered_chainages_m']}"
                for name, value in audit.items() if value['uncovered_rows']]
        if gaps:
            raise MetadataCapabilityError(
                f"{self.config_path.name}/{line}/{section}/{track}: metadata coverage incomplete; "
                + "; ".join(gaps) + ". Supply reviewed intervals; detector fallback is not permitted."
            )
        return audit

    def get_tension_length_lookup(self, line, track, section):
        self.require_tension_length_intervals(line, track, section)

    def get_tension_length_source_rows(self, line, track, section):
        self.require_tension_length_intervals(line, track, section)
