"""Shared normalization and classification for staged Wire Wear candidates."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal, Sequence
import math
import sqlite3

from app.core.calculation.wear_cycle_metadata import (
    MetadataResolutionError,
    MetadataValidationError,
    normalize_cycle_date,
    normalize_line_identity,
    normalize_tension_length,
    resolve_canonical_tl,
)
from app.core.calculation.wear_cycle_repository import (
    current_data_version,
    list_committed_records,
)
from app.core.calculation.wear_cycle_types import MetadataInterval


CandidateStatus = Literal["new", "update", "no_change", "duplicate", "error"]


@dataclass(frozen=True)
class WearRecordCandidate:
    line_group: Any
    line_class: Any
    cycle_date: Any
    tension_length: Any
    avg_wear_min: Any
    track: Any = None
    source_type: str = "manual"
    source_sheet: str | None = None
    source_row: int | None = None
    tension_length_cell: str | None = None
    avg_wear_min_cell: str | None = None
    track_cell: str | None = None
    original_value: Any = None
    excluded: bool = False
    row_id: str | None = None


@dataclass(frozen=True)
class CandidateIssue:
    code: str
    message: str
    field: str
    cell: str | None = None


@dataclass(frozen=True)
class ClassifiedWearRecordCandidate:
    status: CandidateStatus
    key: dict[str, str] | None
    avg_wear_min: float | None
    track: str | None
    existing_avg_wear_min: float | None
    expected_updated_at: str | None
    source_type: str
    source_sheet: str | None
    source_row: int | None
    source_cell: str | None
    original_value: Any
    excluded: bool
    row_id: str | None
    issues: tuple[CandidateIssue, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["issues"] = [asdict(issue) for issue in self.issues]
        return value


@dataclass(frozen=True)
class CandidatePreview:
    line_group: str
    line_class: str
    cycle_date: str
    data_version: int
    candidates: tuple[ClassifiedWearRecordCandidate, ...]

    def to_dict(self) -> dict[str, Any]:
        counts = {status: 0 for status in ("new", "update", "no_change", "duplicate", "error")}
        for candidate in self.candidates:
            counts[candidate.status] += 1
        return {
            "line_group": self.line_group,
            "line_class": self.line_class,
            "cycle_date": self.cycle_date,
            "wire_wear_data_version": self.data_version,
            "counts": counts,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
        }


def _error(candidate: WearRecordCandidate, issue: CandidateIssue) -> ClassifiedWearRecordCandidate:
    return ClassifiedWearRecordCandidate(
        status="error",
        key=None,
        avg_wear_min=None,
        track=None,
        existing_avg_wear_min=None,
        expected_updated_at=None,
        source_type=candidate.source_type,
        source_sheet=candidate.source_sheet,
        source_row=candidate.source_row,
        source_cell=issue.cell,
        original_value=candidate.original_value,
        excluded=candidate.excluded,
        row_id=candidate.row_id,
        issues=(issue,),
    )


def classify_wear_record_candidates(
    conn: sqlite3.Connection,
    candidates: Sequence[WearRecordCandidate],
    metadata: Sequence[MetadataInterval],
) -> CandidatePreview:
    """Normalize and compare candidates without mutating committed records."""
    if not candidates:
        raise MetadataValidationError("at least one candidate row is required")

    line, line_class = normalize_line_identity(
        candidates[0].line_group, candidates[0].line_class
    )
    cycle_date = normalize_cycle_date(candidates[0].cycle_date).isoformat()
    existing = {
        (
            str(record["line_group"]),
            str(record["line_class"]),
            str(record["cycle_date"]),
            str(record["tension_length"]),
        ): record
        for record in list_committed_records(
            conn, line_group=line, line_class=line_class,
            date_from=cycle_date, date_to=cycle_date,
        )
    }
    seen: dict[tuple[str, str, str, str], float] = {}
    classified: list[ClassifiedWearRecordCandidate] = []

    for candidate in candidates:
        try:
            candidate_line, candidate_class = normalize_line_identity(
                candidate.line_group, candidate.line_class
            )
            candidate_date = normalize_cycle_date(candidate.cycle_date).isoformat()
            if (candidate_line, candidate_class, candidate_date) != (
                line, line_class, cycle_date
            ):
                raise MetadataValidationError(
                    "all candidate rows must share one line identity and cycle date"
                )
            tension_length = normalize_tension_length(candidate.tension_length)
            canonical = resolve_canonical_tl(
                line, tension_length, metadata, line_class=line_class
            )
        except (MetadataValidationError, MetadataResolutionError, ValueError, TypeError) as exc:
            classified.append(_error(candidate, CandidateIssue(
                "invalid_tension_length",
                str(exc),
                "tension_length",
                candidate.tension_length_cell,
            )))
            continue

        try:
            average = float(candidate.avg_wear_min)
            if not math.isfinite(average):
                raise ValueError("average wear must be finite")
        except (ValueError, TypeError) as exc:
            classified.append(_error(candidate, CandidateIssue(
                "invalid_avg_wear_min",
                str(exc),
                "avg_wear_min",
                candidate.avg_wear_min_cell,
            )))
            continue

        key_parts = (line, line_class, cycle_date, tension_length)
        source_track = str(candidate.track or "").strip().upper()
        if source_track:
            normalized_track = {"UP": "UP", "DN": "DOWN", "DOWN": "DOWN"}.get(source_track)
            if normalized_track is None:
                classified.append(_error(candidate, CandidateIssue(
                    "invalid_track",
                    "Track must normalize to UP or DOWN",
                    "track",
                    candidate.track_cell,
                )))
                continue
        else:
            normalized_track = "DOWN" if canonical.track == "DN" else canonical.track
        key = {
            "line_group": line,
            "line_class": line_class,
            "cycle_date": cycle_date,
            "tension_length": tension_length,
        }
        if key_parts in seen:
            equal = seen[key_parts] == average
            issue = CandidateIssue(
                "duplicate_equal" if equal else "duplicate_conflict",
                "duplicate candidate matches an earlier row"
                if equal else "duplicate candidate has a conflicting average wear value",
                "tension_length",
                candidate.tension_length_cell,
            )
            classified.append(ClassifiedWearRecordCandidate(
                status="duplicate" if equal else "error",
                key=key,
                avg_wear_min=average,
                track=normalized_track,
                existing_avg_wear_min=None,
                expected_updated_at=None,
                source_type=candidate.source_type,
                source_sheet=candidate.source_sheet,
                source_row=candidate.source_row,
                source_cell=issue.cell,
                original_value=candidate.original_value,
                excluded=candidate.excluded,
                row_id=candidate.row_id,
                issues=(issue,),
            ))
            continue
        seen[key_parts] = average

        stored = existing.get(key_parts)
        if stored is None:
            status: CandidateStatus = "new"
            existing_average = None
            expected_updated_at = None
        else:
            existing_average = float(stored["avg_wear_min"])
            expected_updated_at = str(stored["updated_at"])
            status = "no_change" if existing_average == average else "update"
        classified.append(ClassifiedWearRecordCandidate(
            status=status,
            key=key,
            avg_wear_min=average,
            track=normalized_track,
            existing_avg_wear_min=existing_average,
            expected_updated_at=expected_updated_at,
            source_type=candidate.source_type,
            source_sheet=candidate.source_sheet,
            source_row=candidate.source_row,
            source_cell=candidate.avg_wear_min_cell,
            original_value=candidate.original_value,
            excluded=candidate.excluded,
            row_id=candidate.row_id,
        ))

    return CandidatePreview(
        line, line_class, cycle_date, current_data_version(conn), tuple(classified)
    )
