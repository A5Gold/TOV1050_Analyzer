"""Metadata normalization and coverage rules for wear-cycle aggregation."""

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re
from types import MappingProxyType
from typing import Any

from .wear_cycle_types import (
    EXPECTED_SEGMENTS,
    CanonicalTensionLength,
    LineClass,
    LineGroup,
    MetadataInterval,
    MeasurementResolutionIndex,
    PhysicalInterval,
    ParsedWearSource,
    SegmentCoverage,
)
from .wear_tl_scope import TensionLengthScope, classify_tension_length_scope


class MetadataValidationError(ValueError):
    """Raised when wear-cycle metadata input is structurally invalid."""


class MetadataResolutionError(ValueError):
    """Raised when a tension length cannot be resolved to one continuous range."""


class SegmentDetectionError(ValueError):
    """Raised when a source cannot be mapped to exactly one expected segment."""

    def __init__(self, message_or_filename: Any, *, matches: Iterable[str] | None = None):
        if matches is None:
            self.filename: str | None = None
            self.matches: tuple[str, ...] = ()
            super().__init__(str(message_or_filename))
            return

        self.filename = str(message_or_filename)
        self.matches = tuple(sorted(set(matches)))
        super().__init__(
            f"filename {self.filename!r} has incompatible or ambiguous line tokens: "
            f"{', '.join(self.matches)}"
        )


METADATA_SOURCES: dict[LineGroup, tuple[tuple[str, str, str], ...]] = {
    "EAL": (
        ("UP", "Mainline", "EAL UP"),
        ("DN", "Mainline", "EAL DN"),
        ("UP", "RAC", "RAC UP"),
        ("DN", "RAC", "RAC DN"),
        ("UP", "LOW S1", "LOW S1"),
        ("DN", "LOW S1", "LOW S1"),
        ("UP", "LMC", "LMC UP"),
        ("DN", "LMC", "LMC DN"),
    ),
    "TML": (
        ("UP", "Mainline", "TML UP"),
        ("DN", "Mainline", "TML DN"),
    ),
}


_COMMON_ALIASES = {
    "U1": ("U1", "U1A"),
    "D1": ("D1", "D1A"),
}

_EAL_SPECIAL_ALIASES = {
    "RAC UP": ("UP_RAC", "RAC_UP"),
    "RAC DN": ("DN_RAC", "RAC_DN"),
    "LOW S1": ("S1_LOW", "LOW_S1", "UP_LOW", "LOW S1"),
    "LMC UP": ("UP_LMC", "LMC_UP"),
    "LMC DN": ("DN_LMC", "LMC_DN"),
}

MAX_CANONICAL_TL_LENGTH = 128

_SECTION_ALIASES: dict[LineGroup, dict[str, str]] = {
    "EAL": {
        "MAINLINE": "Mainline",
        "EAL": "Mainline",
        "EAL MAINLINE": "Mainline",
        "RAC": "RAC",
        "LOW": "LOW S1",
        "S1": "LOW S1",
        "LOW S1": "LOW S1",
        "S1 LOW": "LOW S1",
        "LMC": "LMC",
    },
    "TML": {
        "MAINLINE": "Mainline",
        "TML": "Mainline",
        "TML MAINLINE": "Mainline",
    },
}


def normalize_line_group(value: Any) -> LineGroup:
    """Return a supported upper-case line group."""
    if not isinstance(value, str):
        raise MetadataValidationError("line group must be EAL or TML")
    normalized = value.strip().upper()
    if normalized not in EXPECTED_SEGMENTS:
        raise MetadataValidationError("line group must be EAL or TML")
    return normalized  # type: ignore[return-value]


def normalize_line_class(value: Any, line_group: Any | None = None) -> LineClass:
    """Return a supported line class and validate its physical line group."""
    if not isinstance(value, str):
        raise MetadataValidationError("line class must be EAL, LMC, or TML")
    normalized = value.strip().upper()
    if normalized not in {"EAL", "LMC", "TML"}:
        raise MetadataValidationError("line class must be EAL, LMC, or TML")
    if line_group is not None:
        line = normalize_line_group(line_group)
        expected_group = "TML" if normalized == "TML" else "EAL"
        if line != expected_group:
            raise MetadataValidationError(
                f"line class {normalized} is not valid for line group {line}"
            )
    return normalized  # type: ignore[return-value]


def normalize_line_identity(
    line_group: Any,
    line_class: Any | None = None,
) -> tuple[LineGroup, LineClass]:
    """Normalize the only supported Phase 1 line group/class combinations."""
    line = normalize_line_group(line_group)
    class_value = line if line_class is None or not str(line_class).strip() else line_class
    return line, normalize_line_class(class_value, line)


def normalize_section(line_group: Any, value: Any) -> str:
    """Return a canonical metadata section for one supported line group."""
    line = normalize_line_group(line_group)
    if value is None or not str(value).strip():
        raise MetadataValidationError("measurement section cannot be empty")
    normalized = re.sub(r"[^A-Z0-9]+", " ", str(value).strip().upper()).strip()
    section = _SECTION_ALIASES[line].get(normalized)
    if section is None:
        allowed = ", ".join(dict.fromkeys(_SECTION_ALIASES[line].values()))
        raise MetadataValidationError(
            f"measurement section {str(value).strip()!r} is not valid for {line}; expected {allowed}"
        )
    return section


def section_for_segments(line_group: Any, segments: Iterable[str]) -> str:
    """Map detected source segments to exactly one metadata section."""
    line = normalize_line_group(line_group)
    segment_values = tuple(str(segment).strip().upper() for segment in segments)
    if not segment_values:
        raise MetadataValidationError("source segment cannot be empty")
    if line == "TML":
        sections = {"Mainline"}
    else:
        sections = {
            "RAC"
            if segment.startswith("RAC ")
            else "LMC"
            if segment.startswith("LMC ")
            else "LOW S1"
            if segment == "LOW S1"
            else "Mainline"
            for segment in segment_values
        }
    if len(sections) != 1:
        raise MetadataValidationError(
            f"source segments {list(segment_values)} span multiple metadata sections: {sorted(sections)}"
        )
    return next(iter(sections))


def normalize_cycle_date(value: Any) -> date:
    """Return a date from a date instance or strict ISO YYYY-MM-DD string."""
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        return value
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value.strip()):
        raise MetadataValidationError("cycle date must use ISO YYYY-MM-DD")
    try:
        return date.fromisoformat(value.strip())
    except ValueError as exc:
        raise MetadataValidationError("cycle date must be a valid ISO date") from exc


def normalize_tension_length(value: Any) -> str:
    """Return a trimmed TL identifier with canonical decimal formatting."""
    if value is None:
        raise MetadataValidationError("tension length cannot be empty")
    raw = str(value).strip()
    if not raw:
        raise MetadataValidationError("tension length cannot be empty")
    try:
        numeric = Decimal(raw)
    except InvalidOperation:
        if len(raw) > MAX_CANONICAL_TL_LENGTH:
            raise MetadataValidationError(
                f"tension length cannot exceed {MAX_CANONICAL_TL_LENGTH} characters"
            )
        return raw
    if not numeric.is_finite():
        raise MetadataValidationError("tension length must be finite")
    if numeric.is_zero():
        return "0"

    decimal_tuple = numeric.as_tuple()
    digits = list(decimal_tuple.digits)
    exponent = int(decimal_tuple.exponent)
    while len(digits) > 1 and digits[-1] == 0:
        digits.pop()
        exponent += 1

    sign_length = int(bool(decimal_tuple.sign))
    if exponent >= 0:
        output_length = sign_length + len(digits) + exponent
    else:
        point_position = len(digits) + exponent
        output_length = (
            sign_length + len(digits) + 1
            if point_position > 0
            else sign_length + 2 + (-point_position) + len(digits)
        )
    if output_length > MAX_CANONICAL_TL_LENGTH:
        raise MetadataValidationError(
            f"tension length cannot exceed {MAX_CANONICAL_TL_LENGTH} characters"
        )

    digit_text = "".join(str(digit) for digit in digits)
    sign = "-" if decimal_tuple.sign else ""
    if exponent >= 0:
        return sign + digit_text + ("0" * exponent)
    point_position = len(digit_text) + exponent
    if point_position > 0:
        return sign + digit_text[:point_position] + "." + digit_text[point_position:]
    return sign + "0." + ("0" * (-point_position)) + digit_text


def natural_key(value: Any) -> tuple[tuple[tuple[Any, ...], ...], str]:
    """Return a deterministic natural-sort key for TL and file identifiers."""
    text = str(value)
    parts = re.split(r"(\d+)", text)
    token_key = tuple(
        (0, int(part), len(part), part)
        if part.isdigit()
        else (1, part.casefold(), part)
        for part in parts if part
    )
    return token_key, text


def metadata_sources(
    line_group: Any,
    line_class: Any | None = None,
) -> tuple[tuple[str, str, str], ...]:
    """Return the metadata manager calls and sheet names for a line group."""
    line = normalize_line_group(line_group)
    sources = METADATA_SOURCES[line]
    if line_class is None:
        return sources
    _, normalized_class = normalize_line_identity(line, line_class)
    if normalized_class == "LMC":
        return tuple(source for source in sources if source[1] == "LMC")
    if normalized_class == "EAL":
        return tuple(source for source in sources if source[1] != "LMC")
    return sources


def _segment_aliases(line_group: LineGroup) -> dict[str, tuple[str, ...]]:
    aliases: dict[str, tuple[str, ...]] = {}
    for segment in EXPECTED_SEGMENTS[line_group]:
        if re.fullmatch(r"[UD]\d", segment):
            aliases[segment] = _COMMON_ALIASES.get(segment, (segment,))
    if line_group == "EAL":
        aliases.update(_EAL_SPECIAL_ALIASES)
    return aliases


def _alias_pattern(alias: str) -> re.Pattern[str]:
    pieces = [re.escape(piece) for piece in re.split(r"[^A-Z0-9]+", alias.upper()) if piece]
    body = r"[^A-Z0-9]+".join(pieces)
    return re.compile(rf"(?<![A-Z0-9]){body}(?![A-Z0-9])", re.IGNORECASE)


def _segments_in_text(line_group: LineGroup, value: Any) -> set[str]:
    text = str(value)
    return {
        segment
        for segment, aliases in _segment_aliases(line_group).items()
        if any(_alias_pattern(alias).search(text) for alias in aliases)
    }


def _line_tokens_in_text(value: Any) -> set[str]:
    return set(re.findall(r"(?<![A-Z0-9])(?:EAL|TML)(?![A-Z0-9])", str(value).upper()))


def _contiguous_segment_range(line_group: LineGroup, value: Any) -> tuple[str, ...] | None:
    matches = tuple(
        re.finditer(
            r"(?<![A-Z0-9])([UD]\d)\s*-\s*([UD]\d)(?![A-Z0-9])",
            str(value).upper(),
        )
    )
    if len(matches) != 1:
        return None
    start, end = matches[0].groups()
    expected = EXPECTED_SEGMENTS[line_group]
    if start[0] != end[0] or start not in expected or end not in expected:
        return None
    start_index, end_index = expected.index(start), expected.index(end)
    lower, upper = sorted((start_index, end_index))
    expanded = expected[lower : upper + 1]
    if any(segment[0] != start[0] for segment in expanded):
        return None
    if _segments_in_text(line_group, value) != {start, end}:
        return None
    return expanded


def detect_segment(line_group: Any, filename: Any, source_fields: Mapping[str, Any] | Iterable[Any]) -> str:
    """Detect exactly one segment, preferring filename tokens over source fields."""
    normalized_line = normalize_line_group(line_group)
    filename_text = Path(str(filename)).name
    filename_line_matches = _line_tokens_in_text(filename_text)
    if filename_line_matches and (
        len(filename_line_matches) > 1 or normalized_line not in filename_line_matches
    ):
        raise SegmentDetectionError(str(filename), matches=filename_line_matches)

    filename_matches = _segments_in_text(normalized_line, filename_text)
    if len(filename_matches) == 1:
        return next(iter(filename_matches))
    if len(filename_matches) > 1:
        raise SegmentDetectionError(f"ambiguous segment tokens in filename: {sorted(filename_matches)}")

    values = tuple(source_fields.values() if isinstance(source_fields, Mapping) else source_fields)
    field_line_matches: set[str] = set()
    for value in values:
        field_line_matches.update(_line_tokens_in_text(value))
    if field_line_matches and (
        len(field_line_matches) > 1 or normalized_line not in field_line_matches
    ):
        raise SegmentDetectionError(str(filename), matches=field_line_matches)

    field_matches: set[str] = set()
    for value in values:
        field_matches.update(_segments_in_text(normalized_line, value))
    if len(field_matches) == 1:
        return next(iter(field_matches))
    if len(field_matches) > 1:
        raise SegmentDetectionError(f"ambiguous segment tokens in source fields: {sorted(field_matches)}")
    raise SegmentDetectionError(f"no segment token found for line {normalized_line}")


def detect_segments(
    line_group: Any,
    filename: Any,
    source_fields: Mapping[str, Any] | Iterable[Any],
) -> tuple[str, ...]:
    """Detect one segment or a strictly declared contiguous segment range."""
    normalized_line = normalize_line_group(line_group)
    filename_text = Path(str(filename)).name
    filename_line_matches = _line_tokens_in_text(filename_text)
    if filename_line_matches and (
        len(filename_line_matches) > 1 or normalized_line not in filename_line_matches
    ):
        raise SegmentDetectionError(str(filename), matches=filename_line_matches)
    filename_range = _contiguous_segment_range(normalized_line, filename_text)
    if filename_range is not None:
        return filename_range
    return (detect_segment(normalized_line, filename, source_fields),)


def declared_segments(value: Any) -> tuple[str, ...]:
    """Return the canonical segment memberships stored on a parsed source."""
    return tuple(dict.fromkeys(part.strip().upper() for part in str(value).split(",") if part.strip()))


def _decimal_coordinate(value: Any, *, context: str) -> Decimal:
    if value is None:
        raise MetadataValidationError(f"{context} must be numeric")
    try:
        result = Decimal(str(value).strip().replace(",", ""))
    except (InvalidOperation, ValueError) as exc:
        raise MetadataValidationError(f"{context} must be numeric") from exc
    if not result.is_finite():
        raise MetadataValidationError(f"{context} must be finite")
    return result


def _records(frame: Any) -> list[Mapping[str, Any]]:
    error_message = "metadata lookup must return tabular rows"
    if frame is None:
        return []
    if hasattr(frame, "to_dict"):
        try:
            rows = list(frame.to_dict("records"))
        except (AttributeError, TypeError, ValueError) as exc:
            raise MetadataValidationError(error_message) from exc
    elif isinstance(frame, Sequence) and not isinstance(frame, (str, bytes, bytearray)):
        rows = list(frame)
    else:
        raise MetadataValidationError(error_message)
    if any(not isinstance(row, Mapping) for row in rows):
        raise MetadataValidationError(error_message)
    return rows


def load_line_metadata(
    manager: Any,
    line_group: Any,
    line_class: Any | None = None,
) -> tuple[MetadataInterval, ...]:
    """Load, validate, expand, and deterministically sort all metadata for a line."""
    line = normalize_line_group(line_group)
    intervals: list[MetadataInterval] = []
    for track, section, sheet_name in metadata_sources(line, line_class):
        frame = manager.get_tension_length_source_rows(line, track, section)
        for row_index, row in enumerate(_records(frame)):
            context = f"{sheet_name} row {row_index + 1}"
            try:
                raw_from_m = _decimal_coordinate(
                    row.get("from_m"), context=f"{context} from_m"
                )
                raw_to_m = _decimal_coordinate(
                    row.get("to_m"), context=f"{context} to_m"
                )
                source_from_m = min(raw_from_m, raw_to_m)
                source_to_m = max(raw_from_m, raw_to_m)
                raw_tl = row.get("tension_length")
                tl_values = str(raw_tl).split(",") if raw_tl is not None else [raw_tl]
                source_tension_lengths = tuple(
                    normalize_tension_length(tl_value) for tl_value in tl_values
                )
                unknown_tension_lengths = tuple(
                    tension_length
                    for tension_length in source_tension_lengths
                    if classify_tension_length_scope(line, tension_length)
                    is TensionLengthScope.UNKNOWN
                )
                if unknown_tension_lengths:
                    raise MetadataValidationError(
                        f"{line} {context} source signature {str(raw_tl)!r} has "
                        f"unknown tension length {unknown_tension_lengths[0]!r}"
                    )
                segment_length = (raw_to_m - raw_from_m) / len(source_tension_lengths)
                for source_priority, tension_length in enumerate(source_tension_lengths):
                    physical_from_m = raw_from_m + source_priority * segment_length
                    physical_to_m = physical_from_m + segment_length
                    intervals.append(
                        MetadataInterval(
                            tension_length=tension_length,
                            track=track,  # type: ignore[arg-type]
                            from_m=min(physical_from_m, physical_to_m),
                            to_m=max(physical_from_m, physical_to_m),
                            sheet_name=sheet_name,
                            section=normalize_section(line, section),
                            source_priority=source_priority,
                            source_tension_lengths=source_tension_lengths,
                            source_from_m=source_from_m,
                            source_to_m=source_to_m,
                            source_row=row_index + 1,
                        )
                    )
            except MetadataValidationError as exc:
                if "row" in str(exc):
                    raise
                raise MetadataValidationError(f"invalid metadata {context}: {exc}") from exc
    return tuple(
        sorted(
            intervals,
            key=lambda item: (
                natural_key(item.tension_length),
                item.track,
                item.from_m,
                item.to_m,
                item.sheet_name,
                item.section,
                item.source_priority,
                item.source_tension_lengths,
                item.source_row or 0,
            ),
        )
    )


def _validated_interval(interval: MetadataInterval) -> tuple[Decimal, Decimal]:
    from_m = _decimal_coordinate(interval.from_m, context=f"{interval.sheet_name} from_m")
    to_m = _decimal_coordinate(interval.to_m, context=f"{interval.sheet_name} to_m")
    if from_m > to_m:
        raise MetadataValidationError(f"{interval.sheet_name} has reversed range")
    if interval.track not in ("UP", "DN"):
        raise MetadataValidationError(f"{interval.sheet_name} has invalid track")
    return from_m, to_m


def _group_intervals_by_tl(
    intervals: Iterable[MetadataInterval],
) -> dict[str, tuple[MetadataInterval, ...]]:
    grouped: dict[str, list[MetadataInterval]] = {}
    for interval in intervals:
        normalized_tl = normalize_tension_length(interval.tension_length)
        grouped.setdefault(normalized_tl, []).append(interval)
    return {tl: tuple(items) for tl, items in grouped.items()}


def build_measurement_resolution_index(
    line_group: Any,
    intervals: Iterable[MetadataInterval],
) -> MeasurementResolutionIndex:
    """Validate and group immutable measurement metadata once per preview."""
    line = normalize_line_group(line_group)
    normalized_intervals: list[MetadataInterval] = []
    for interval in intervals:
        tension_length = normalize_tension_length(interval.tension_length)
        section = normalize_section(line, interval.section)
        if not isinstance(interval.source_priority, int) or isinstance(
            interval.source_priority, bool
        ) or interval.source_priority < 0:
            raise MetadataValidationError(
                f"{interval.sheet_name} has invalid source priority"
            )
        if interval.source_row is not None and (
            not isinstance(interval.source_row, int)
            or isinstance(interval.source_row, bool)
            or interval.source_row < 1
        ):
            raise MetadataValidationError(f"{interval.sheet_name} has invalid source row")
        from_m, to_m = _validated_interval(interval)
        if (interval.source_from_m is None) != (interval.source_to_m is None):
            raise MetadataValidationError(
                f"{interval.sheet_name} has incomplete source range"
            )
        source_from_m = _decimal_coordinate(
            interval.source_from_m if interval.source_from_m is not None else from_m,
            context=f"{interval.sheet_name} source_from_m",
        )
        source_to_m = _decimal_coordinate(
            interval.source_to_m if interval.source_to_m is not None else to_m,
            context=f"{interval.sheet_name} source_to_m",
        )
        if source_from_m > source_to_m:
            raise MetadataValidationError(
                f"{interval.sheet_name} has reversed source range"
            )
        if not source_from_m <= from_m <= to_m <= source_to_m:
            raise MetadataValidationError(
                f"{interval.sheet_name} physical range "
                f"[{format(from_m, 'f')}, {format(to_m, 'f')}] is outside source range "
                f"[{format(source_from_m, 'f')}, {format(source_to_m, 'f')}]"
            )
        source_tension_lengths = tuple(
            normalize_tension_length(value)
            for value in interval.source_tension_lengths
        )
        if source_tension_lengths and (
            interval.source_priority >= len(source_tension_lengths)
            or source_tension_lengths[interval.source_priority] != tension_length
        ):
            raise MetadataValidationError(
                f"{interval.sheet_name} source signature does not match "
                f"priority {interval.source_priority} for tension length {tension_length}"
            )
        normalized_intervals.append(
            replace(
                interval,
                tension_length=tension_length,
                section=section,
                from_m=from_m,
                to_m=to_m,
                source_tension_lengths=source_tension_lengths,
                source_from_m=source_from_m,
                source_to_m=source_to_m,
            )
        )
    grouped = _group_intervals_by_tl(normalized_intervals)
    return MeasurementResolutionIndex(line, MappingProxyType(grouped))


def _resolve_canonical_group(
    line: LineGroup,
    normalized_tl: str,
    intervals: Sequence[MetadataInterval],
    tolerance: Decimal,
) -> CanonicalTensionLength:
    if not intervals:
        raise MetadataResolutionError(f"unknown tension length {normalized_tl} for {line}")

    candidates: list[tuple[Decimal, Decimal, str]] = []
    for interval in intervals:
        from_m, to_m = _validated_interval(interval)
        candidates.append((from_m, to_m, interval.track))

    candidates.sort(key=lambda item: (item[0], item[1], item[2]))
    tracks: set[str] = set()
    merged: list[PhysicalInterval] = []
    interval_from, interval_to, first_track = candidates[0]
    interval_tracks = {first_track}
    for from_m, to_m, track in candidates:
        tracks.add(track)
        if from_m > interval_to + tolerance:
            merged_track = next(iter(interval_tracks)) if len(interval_tracks) == 1 else "Siding"
            merged.append(PhysicalInterval(merged_track, interval_from, interval_to))  # type: ignore[arg-type]
            interval_from, interval_to, interval_tracks = from_m, to_m, {track}
            continue
        interval_to = max(interval_to, to_m)
        interval_tracks.add(track)
    merged_track = next(iter(interval_tracks)) if len(interval_tracks) == 1 else "Siding"
    merged.append(PhysicalInterval(merged_track, interval_from, interval_to))  # type: ignore[arg-type]

    canonical_track = next(iter(tracks)) if len(tracks) == 1 else "Siding"
    return CanonicalTensionLength(
        line_group=line,
        tension_length=normalized_tl,
        track=canonical_track,  # type: ignore[arg-type]
        from_m=merged[0].from_m,
        to_m=merged[-1].to_m,
        intervals=tuple(merged),
    )


def resolve_canonical_tl(
    line_group: Any,
    tension_length: Any,
    intervals: Iterable[MetadataInterval],
    tolerance: Any = Decimal("0.01"),
    line_class: Any | None = None,
) -> CanonicalTensionLength:
    """Resolve one normalized TL within a line-class metadata boundary."""
    line = normalize_line_group(line_group)
    normalized_tl = normalize_tension_length(tension_length)
    tolerance_decimal = _decimal_coordinate(tolerance, context="tolerance")
    if tolerance_decimal < 0:
        raise MetadataValidationError("tolerance cannot be negative")
    normalized_class = None
    filtered_intervals = intervals
    if line_class is not None:
        _, normalized_class = normalize_line_identity(line, line_class)
        allowed_sheets = {
            sheet_name for _, _, sheet_name in metadata_sources(line, normalized_class)
        }
        filtered_intervals = (
            interval for interval in intervals if interval.sheet_name in allowed_sheets
        )
    grouped = _group_intervals_by_tl(filtered_intervals)
    canonical = _resolve_canonical_group(
        line,
        normalized_tl,
        grouped.get(normalized_tl, ()),
        tolerance_decimal,
    )
    return canonical if normalized_class is None else replace(canonical, line_class=normalized_class)


def resolve_measurement_tension_length(
    line_group: Any,
    track: Any,
    chainage: Any,
    intervals: Iterable[MetadataInterval] | MeasurementResolutionIndex,
    raw_tension_length: Any | None = None,
    section: Any | None = None,
) -> str:
    line = normalize_line_group(line_group)
    normalized_track = str(track).strip().upper()
    if normalized_track not in ("UP", "DN"):
        raise MetadataValidationError("measurement track must be UP or DN")
    normalized_section = normalize_section(line, section) if section is not None else None
    coordinate = _decimal_coordinate(chainage, context="measurement chainage")
    resolution_index = (
        intervals
        if isinstance(intervals, MeasurementResolutionIndex)
        else build_measurement_resolution_index(line, intervals)
    )
    if resolution_index.line_group != line:
        raise MetadataValidationError(
            f"measurement metadata index is for {resolution_index.line_group}, not {line}"
        )
    grouped = resolution_index.intervals_by_tl
    if raw_tension_length is None:
        candidates = tuple(grouped)
    else:
        candidates = tuple(
            normalize_tension_length(value)
            for value in str(raw_tension_length).split(",")
            if value.strip()
        )
    matches: list[
        tuple[int, str, tuple[str, ...], str, Decimal, Decimal, str, int | None]
    ] = []
    for tension_length in dict.fromkeys(candidates):
        for interval in grouped.get(tension_length, ()):
            source_from_m = interval.source_from_m
            source_to_m = interval.source_to_m
            if source_from_m is None or source_to_m is None:
                raise MetadataValidationError(
                    f"{interval.sheet_name} has incomplete resolution index"
                )
            if (
                interval.track == normalized_track
                and (normalized_section is None or interval.section == normalized_section)
                and source_from_m <= coordinate <= source_to_m
            ):
                matches.append(
                    (
                        interval.source_priority,
                        tension_length,
                        interval.source_tension_lengths,
                        interval.sheet_name,
                        source_from_m,
                        source_to_m,
                        interval.section,
                        interval.source_row,
                    )
                )
    used_transition = False
    if not matches:
        transition_matches = []
        if normalized_section is not None and raw_tension_length is not None:
            for tension_length in dict.fromkeys(candidates):
                for interval in grouped.get(tension_length, ()):
                    source_from_m = interval.source_from_m
                    source_to_m = interval.source_to_m
                    if source_from_m is None or source_to_m is None:
                        raise MetadataValidationError(
                            f"{interval.sheet_name} has incomplete resolution index"
                        )
                    if (
                        interval.track == normalized_track
                        and interval.source_tension_lengths == candidates
                        and source_from_m <= coordinate <= source_to_m
                    ):
                        transition_matches.append(
                            (
                                interval.source_priority,
                                tension_length,
                                interval.source_tension_lengths,
                                interval.sheet_name,
                                source_from_m,
                                source_to_m,
                                interval.section,
                                interval.source_row,
                            )
                        )
        if transition_matches:
            source_rows = {
                (
                    match[3],
                    match[6],
                    match[7],
                    match[4],
                    match[5],
                    match[2],
                )
                for match in transition_matches
            }
            if len(source_rows) != 1:
                raise MetadataResolutionError(
                    "section transition failed at chainage "
                    f"{format(coordinate, 'f')}: multiple source rows match exact "
                    f"signature {list(candidates)}"
                )
            matches = transition_matches
            used_transition = True
        else:
            section_detail = f" section {normalized_section}" if normalized_section else ""
            transition_detail = (
                f"; section transition found no exact source signature {list(candidates)}"
                if normalized_section is not None and raw_tension_length is not None
                else ""
            )
            raise MetadataResolutionError(
                f"measurement gap at chainage {format(coordinate, 'f')} for "
                f"{line}{section_detail} {normalized_track}{transition_detail}"
            )
    if len(candidates) > 1:
        exact_source_matches = [
            match for match in matches if match[2] == candidates
        ]
        if exact_source_matches:
            matches = exact_source_matches
    primary_priority = min(match[0] for match in matches)
    primary_matches = tuple(
        dict.fromkeys(
            match[1]
            for match in matches
            if match[0] == primary_priority
        )
    )
    if len(primary_matches) != 1:
        section_detail = f" in section {normalized_section}" if normalized_section else ""
        source_details = "; ".join(
            f"{tension_length} from {sheet_name} "
            f"[{format(source_from_m, 'f')}, {format(source_to_m, 'f')}]"
            for tension_length, sheet_name, source_from_m, source_to_m in sorted(
                {
                    (match[1], match[3], match[4], match[5])
                    for match in matches
                    if match[0] == primary_priority
                },
                key=lambda item: (natural_key(item[0]), item[1], item[2], item[3]),
            )
        )
        failure_prefix = "section transition failed: " if used_transition else ""
        raise MetadataResolutionError(
            f"{failure_prefix}ambiguous metadata at chainage "
            f"{format(coordinate, 'f')}{section_detail}: "
            f"{sorted(primary_matches)}; sources: {source_details}"
        )
    return primary_matches[0]


def _required_track(segment_name: str) -> str | None:
    if segment_name == "LOW S1":
        return None
    if segment_name.startswith("U") or segment_name.endswith(" UP"):
        return "UP"
    if segment_name.startswith("D") or segment_name.endswith(" DN"):
        return "DN"
    return None


def _track_is_compatible(track: str, required_track: str | None) -> bool:
    return required_track is None or track in (required_track, "Siding")


def _ranges_intersect(
    from_m: Decimal,
    to_m: Decimal,
    source_range: tuple[Decimal, Decimal],
) -> bool:
    source_from, source_to = source_range
    return from_m <= source_to and to_m >= source_from


def _canonical_by_tl(
    line: LineGroup, intervals: tuple[MetadataInterval, ...]
) -> dict[str, CanonicalTensionLength]:
    grouped = _group_intervals_by_tl(intervals)
    canonical = {}
    for tl in sorted(grouped, key=natural_key):
        try:
            canonical[tl] = _resolve_canonical_group(
                line, tl, grouped[tl], Decimal("0.01")
            )
        except MetadataResolutionError:
            # Coverage is advisory. Measured TLs with incoherent metadata are
            # reported as unresolved by the aggregation pipeline.
            continue
    return canonical


def build_segment_coverage(
    line_group: Any,
    sources: Iterable[ParsedWearSource],
    intervals: Iterable[MetadataInterval],
) -> tuple[SegmentCoverage, ...]:
    """Build advisory segment coverage in the line's required segment order."""
    line = normalize_line_group(line_group)
    source_items = tuple(sources)
    source_ranges: dict[int, tuple[Decimal, Decimal]] = {}
    for source in source_items:
        context = f"source {source.filename!r}"
        source_from = _decimal_coordinate(source.from_m, context=f"{context} from_m")
        source_to = _decimal_coordinate(source.to_m, context=f"{context} to_m")
        if source_from > source_to:
            raise MetadataValidationError(f"{context} has reversed range")
        source_ranges[id(source)] = (source_from, source_to)

    interval_items = tuple(intervals)
    canonical = {
        tension_length: item
        for tension_length, item in _canonical_by_tl(line, interval_items).items()
        if classify_tension_length_scope(line, tension_length)
        is TensionLengthScope.MAINLINE
    }
    coverage: list[SegmentCoverage] = []

    for segment_name in EXPECTED_SEGMENTS[line]:
        segment_sources = tuple(
            item
            for item in source_items
            if segment_name in declared_segments(item.segment_name)
        )
        if not segment_sources:
            coverage.append(SegmentCoverage(segment_name, False, 0.0, ("segment_missing",), (), ()))
            continue

        required_track = _required_track(segment_name)
        denominator = {
            tl
            for tl, item in canonical.items()
            if _track_is_compatible(item.track, required_track)
            and any(
                _ranges_intersect(item.from_m, item.to_m, source_ranges[id(source)])
                for source in segment_sources
            )
        }
        filenames = tuple(sorted({item.filename for item in segment_sources}, key=natural_key))
        acquisition_dates = tuple(
            sorted(
                {
                    measurement.acquisition_date
                    for source in segment_sources
                    for measurement in source.measurements
                }
            )
        )
        if not denominator:
            coverage.append(
                SegmentCoverage(
                    segment_name,
                    False,
                    0.0,
                    ("metadata_denominator_empty",),
                    filenames,
                    acquisition_dates,
                )
            )
            continue

        numerator: set[str] = set()
        for source in segment_sources:
            for measurement in source.measurements:
                try:
                    measurement_line = normalize_line_group(measurement.line_group)
                except MetadataValidationError:
                    continue
                if measurement_line != line:
                    continue
                if not _track_is_compatible(measurement.track, required_track):
                    continue
                try:
                    tl = normalize_tension_length(measurement.tension_length)
                except MetadataValidationError:
                    continue
                if (
                    classify_tension_length_scope(line, tl)
                    is not TensionLengthScope.MAINLINE
                ):
                    continue
                resolved = canonical.get(tl)
                if resolved is None:
                    continue
                if tl in denominator and _track_is_compatible(resolved.track, required_track):
                    numerator.add(tl)

        missing = tuple(sorted(denominator - numerator, key=natural_key))
        percentage = round(100 * len(numerator) / len(denominator), 2)
        coverage.append(
            SegmentCoverage(
                segment_name,
                bool(numerator),
                percentage,
                missing,
                filenames,
                acquisition_dates,
            )
        )
    return tuple(coverage)
