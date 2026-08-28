"""Build deterministic complete-cycle wire-wear previews."""

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math

from .wear_calculator import calculate_wear_percentage, calculate_wear_statistics
from .wear_cycle_metadata import (
    MetadataResolutionError,
    MetadataValidationError,
    build_segment_coverage,
    declared_segments,
    natural_key,
    normalize_cycle_date,
    normalize_line_group,
    normalize_tension_length,
    resolve_canonical_tl,
)
from .wear_cycle_types import (
    EXPECTED_SEGMENTS,
    AggregatedWearRecord,
    BusinessKey,
    ConflictPreview,
    CyclePreview,
    MetadataInterval,
    ParsedWearSource,
    RawWearMeasurement,
)
from .wear_tl_scope import TensionLengthScope, classify_tension_length_scope


@dataclass(frozen=True)
class _Candidate:
    tension_length: str
    acquisition_date: date
    wear_min: float
    source_filename: str
    source: ParsedWearSource
    measurement: RawWearMeasurement


def _normalized_text(value: object) -> str:
    return str(value or "").strip().casefold()


def _decimal_identity(value: object) -> str:
    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise MetadataValidationError("measurement chainage must be decimal") from exc
    if not decimal_value.is_finite():
        raise MetadataValidationError("measurement chainage must be finite")
    if decimal_value.is_zero():
        return "0"
    rendered = format(decimal_value, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered


def _measurement_identity(
    line: str,
    segment_name: str,
    measurement: object,
) -> str:
    track = str(getattr(measurement, "track", "")).strip().upper()
    if track not in {"UP", "DN"}:
        raise MetadataValidationError("measurement track must be UP or DN")
    stable_value = getattr(measurement, "stable_measurement_id", None)
    stable_id = str(stable_value).strip() if stable_value is not None else ""
    if stable_id:
        return f"stable:{stable_id}"

    acquisition_date = normalize_cycle_date(getattr(measurement, "acquisition_date", None))
    fallback = (
        line,
        segment_name,
        track,
        acquisition_date.isoformat(),
        _normalized_text(getattr(measurement, "task_no", "")),
        _normalized_text(getattr(measurement, "station_start", "")),
        _normalized_text(getattr(measurement, "station_end", "")),
        _decimal_identity(getattr(measurement, "chainage", None)),
    )
    return "fallback:" + json.dumps(
        fallback,
        ensure_ascii=True,
        separators=(",", ":"),
    )


def _conflict_id(identity: str, source_values: tuple[tuple[str, float], ...]) -> str:
    encoded = json.dumps(
        {"measurement_identity": identity, "source_values": source_values},
        ensure_ascii=True,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _digest_json_default(value: object) -> str:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(f"cannot serialize {type(value).__name__}")


def preview_digest(preview: CyclePreview) -> str:
    """Return a stable content digest, excluding preview generation time."""
    payload = asdict(preview)
    payload.pop("generated_at", None)
    encoded = json.dumps(
        payload,
        default=_digest_json_default,
        ensure_ascii=True,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_cycle_preview(
    *,
    line_group: str,
    requested_cycle_date: str | None,
    sources: Sequence[ParsedWearSource],
    metadata: Sequence[MetadataInterval],
    accepted_conflict_ids: set[str],
) -> CyclePreview:
    """Aggregate parsed source measurements into canonical TL records."""
    line = normalize_line_group(line_group)
    source_items = tuple(sources)
    expected_segments = set(EXPECTED_SEGMENTS[line])
    has_unknown_segment = any(
        not declared_segments(source.segment_name)
        or not set(declared_segments(source.segment_name)).issubset(expected_segments)
        for source in source_items
    )
    metadata_by_tl: dict[str, list[MetadataInterval]] = defaultdict(list)
    for interval in metadata:
        normalized_tl = normalize_tension_length(interval.tension_length)
        metadata_by_tl[normalized_tl].append(interval)
    canonical_by_tl = {}
    candidates_by_identity: dict[str, list[_Candidate]] = defaultdict(list)
    acquisition_dates: set[date] = set()
    unresolved: set[str] = set()

    for source in source_items:
        source_segments = declared_segments(source.segment_name)
        if not source_segments or not set(source_segments).issubset(expected_segments):
            continue
        segment_name = ",".join(source_segments)
        for measurement in source.measurements:
            try:
                measurement_line = normalize_line_group(measurement.line_group)
                measurement_date = normalize_cycle_date(measurement.acquisition_date)
            except MetadataValidationError as exc:
                unresolved.add(f"{source.filename}: {exc}")
                continue
            if measurement_line != line:
                unresolved.add(
                    f"{source.filename}: measurement line {measurement_line} "
                    f"does not match {line}"
                )
                continue
            try:
                tension_length = normalize_tension_length(measurement.tension_length)
                scope = classify_tension_length_scope(line, tension_length)
                if scope is TensionLengthScope.SIDING:
                    continue
                if scope is TensionLengthScope.UNKNOWN:
                    unresolved.add(
                        f"{source.filename}: {line} has unknown tension length "
                        f"{tension_length!r}"
                    )
                    continue
                identity = _measurement_identity(line, segment_name, measurement)
                wear_min = float(measurement.wear_min)
                if not math.isfinite(wear_min):
                    raise MetadataValidationError("wear_min must be finite")
            except (MetadataValidationError, TypeError, ValueError) as exc:
                unresolved.add(f"{source.filename}: {exc}")
                continue
            canonical = canonical_by_tl.get(tension_length)
            if canonical is None:
                try:
                    canonical = resolve_canonical_tl(
                        line,
                        tension_length,
                        metadata_by_tl.get(tension_length, ()),
                    )
                except (MetadataResolutionError, MetadataValidationError) as exc:
                    unresolved.add(f"{source.filename}: {exc}")
                    continue
                canonical_by_tl[tension_length] = canonical
            candidates_by_identity[identity].append(
                _Candidate(
                    tension_length,
                    measurement_date,
                    wear_min,
                    source.filename,
                    source,
                    measurement,
                )
            )

    grouped: dict[str, list[float]] = defaultdict(list)
    lineage: dict[str, set[str]] = defaultdict(set)
    conflicts: list[ConflictPreview] = []
    conflict_ids_by_tl: dict[str, set[str]] = defaultdict(set)
    accepted_measurements_by_source: dict[int, list[RawWearMeasurement]] = defaultdict(list)

    for identity in sorted(candidates_by_identity):
        candidates = candidates_by_identity[identity]
        tension_lengths = {candidate.tension_length for candidate in candidates}
        if len(tension_lengths) != 1:
            unresolved.add(f"{identity}: measurement resolves to multiple tension lengths")
            continue
        tension_length = next(iter(tension_lengths))
        selected_wear_min = min(candidate.wear_min for candidate in candidates)
        source_values = tuple(
            sorted(
                {(candidate.source_filename, candidate.wear_min) for candidate in candidates},
                key=lambda item: (natural_key(item[0]), item[1]),
            )
        )
        distinct_values = {candidate.wear_min for candidate in candidates}
        if len(distinct_values) > 1:
            conflict_id = _conflict_id(identity, source_values)
            is_accepted = conflict_id in accepted_conflict_ids
            conflicts.append(
                ConflictPreview(
                    conflict_id=conflict_id,
                    measurement_identity=identity,
                    source_values=source_values,
                    selected_wear_min=selected_wear_min,
                    is_accepted=is_accepted,
                )
            )
            conflict_ids_by_tl[tension_length].add(conflict_id)
        selected_candidates = tuple(
            candidate for candidate in candidates if candidate.wear_min == selected_wear_min
        )
        grouped[tension_length].append(selected_wear_min)
        lineage[tension_length].update(candidate.source_filename for candidate in candidates)
        for candidate in selected_candidates:
            accepted_measurements_by_source[id(candidate.source)].append(candidate.measurement)
        acquisition_dates.add(
            max(candidate.acquisition_date for candidate in selected_candidates)
        )

    accepted_sources = tuple(
        ParsedWearSource(
            source.filename,
            source.segment_name,
            source.from_m,
            source.to_m,
            tuple(accepted_measurements_by_source[id(source)]),
        )
        for source in source_items
        if id(source) in accepted_measurements_by_source
    )
    segments = build_segment_coverage(line, accepted_sources, metadata)

    cycle_date_invalid = False
    if requested_cycle_date is not None:
        try:
            cycle_date = normalize_cycle_date(requested_cycle_date)
        except MetadataValidationError:
            cycle_date = date.min
            cycle_date_invalid = True
    elif acquisition_dates:
        cycle_date = max(acquisition_dates)
    else:
        cycle_date = date.min
        cycle_date_invalid = True

    records = []
    for tension_length, values in grouped.items():
        canonical = canonical_by_tl[tension_length]
        try:
            mean, sample_sd = calculate_wear_statistics(values)
            wear_percentage = calculate_wear_percentage(mean)
            if not math.isfinite(wear_percentage):
                raise ValueError("wear percentage must be finite")
        except ValueError as exc:
            unresolved.add(f"aggregate {tension_length}: {exc}")
            continue
        records.append(
            AggregatedWearRecord(
                key=BusinessKey(line, cycle_date, tension_length),
                track=canonical.track,
                from_m=canonical.from_m,
                to_m=canonical.to_m,
                avg_wear_min=mean,
                wear_percentage=wear_percentage,
                measurement_sd=sample_sd,
                has_data_conflict=bool(conflict_ids_by_tl[tension_length]),
                conflict_ids=tuple(sorted(conflict_ids_by_tl[tension_length])),
                source_lineage=tuple(sorted(lineage[tension_length], key=natural_key)),
                intervals=canonical.intervals,
            )
        )
    records.sort(
        key=lambda record: (record.from_m, natural_key(record.key.tension_length))
    )

    conflicts.sort(key=lambda conflict: conflict.conflict_id)
    blocking_reasons = []
    if cycle_date_invalid:
        blocking_reasons.append("cycle_date_invalid")
    if any(not segment.is_present for segment in segments):
        blocking_reasons.append("segment_missing")
    if has_unknown_segment:
        blocking_reasons.append("unknown_segment")
    if unresolved:
        blocking_reasons.append("unresolved_tension_length")
    if any(not conflict.is_accepted for conflict in conflicts):
        blocking_reasons.append("conflict_not_accepted")
    hard_blocking_reasons = tuple(
        reason for reason in blocking_reasons if reason != "segment_missing"
    )
    return CyclePreview(
        line_group=line,
        cycle_date=cycle_date,
        records=tuple(records),
        segments=segments,
        conflicts=tuple(conflicts),
        unresolved=tuple(sorted(unresolved, key=natural_key)),
        blocking_reasons=tuple(blocking_reasons),
        can_save=(
            bool(records)
            and any(segment.is_present for segment in segments)
            and not hard_blocking_reasons
        ),
        generated_at=datetime.now(timezone.utc),
    )
