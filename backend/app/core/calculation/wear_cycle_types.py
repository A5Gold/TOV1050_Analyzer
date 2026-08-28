"""Immutable domain records used by wear-cycle aggregation."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Mapping, Optional


LineGroup = Literal["EAL", "TML"]
LineClass = Literal["EAL", "LMC", "TML"]
MetadataTrack = Literal["UP", "DN"]
CanonicalTrack = Literal["UP", "DN", "Siding"]


EXPECTED_SEGMENTS: dict[LineGroup, tuple[str, ...]] = {
    "EAL": (
        "U1",
        "U2",
        "U3",
        "D1",
        "D2",
        "D3",
        "LOW S1",
        "RAC UP",
        "RAC DN",
        "LMC UP",
        "LMC DN",
    ),
    "TML": ("U1", "U2", "U3", "U4", "U5", "D1", "D2", "D3", "D4", "D5"),
}


@dataclass(frozen=True)
class BusinessKey:
    line_group: LineGroup
    cycle_date: date
    tension_length: str
    line_class: LineClass | None = None


@dataclass(frozen=True)
class PhysicalInterval:
    track: CanonicalTrack
    from_m: Decimal
    to_m: Decimal


@dataclass(frozen=True)
class CanonicalTensionLength:
    line_group: LineGroup
    tension_length: str
    track: CanonicalTrack
    from_m: Decimal
    to_m: Decimal
    intervals: tuple[PhysicalInterval, ...] = ()
    line_class: LineClass | None = None


@dataclass(frozen=True)
class MetadataInterval:
    tension_length: str
    track: MetadataTrack
    from_m: Decimal
    to_m: Decimal
    sheet_name: str
    section: str = "Mainline"
    source_priority: int = 0
    source_tension_lengths: tuple[str, ...] = ()
    source_from_m: Optional[Decimal] = None
    source_to_m: Optional[Decimal] = None
    source_row: Optional[int] = None


@dataclass(frozen=True)
class MeasurementResolutionIndex:
    line_group: LineGroup
    intervals_by_tl: Mapping[str, tuple[MetadataInterval, ...]]


@dataclass(frozen=True)
class RawWearMeasurement:
    acquisition_date: date
    line_group: LineGroup
    track: MetadataTrack
    task_no: str
    station_start: str
    station_end: str
    chainage: Decimal
    wear_min: float
    tension_length: str
    stable_measurement_id: Optional[str] = None


@dataclass(frozen=True)
class ParsedWearSource:
    filename: str
    segment_name: str
    from_m: Decimal
    to_m: Decimal
    measurements: tuple[RawWearMeasurement, ...]


@dataclass(frozen=True)
class SegmentCoverage:
    segment_name: str
    is_present: bool
    coverage_percentage: float
    diagnostic_gaps: tuple[str, ...]
    source_file_names: tuple[str, ...]
    acquisition_dates: tuple[date, ...]


@dataclass(frozen=True)
class ConflictPreview:
    conflict_id: str
    measurement_identity: str
    source_values: tuple[tuple[str, float], ...]
    selected_wear_min: float
    is_accepted: bool


@dataclass(frozen=True)
class AggregatedWearRecord:
    key: BusinessKey
    track: CanonicalTrack
    from_m: Decimal
    to_m: Decimal
    avg_wear_min: float
    wear_percentage: float
    measurement_sd: Optional[float]
    has_data_conflict: bool
    conflict_ids: tuple[str, ...]
    source_lineage: tuple[str, ...]
    intervals: tuple[PhysicalInterval, ...] = ()


@dataclass(frozen=True)
class CyclePreview:
    line_group: LineGroup
    cycle_date: date
    records: tuple[AggregatedWearRecord, ...]
    segments: tuple[SegmentCoverage, ...]
    conflicts: tuple[ConflictPreview, ...]
    unresolved: tuple[str, ...]
    blocking_reasons: tuple[str, ...]
    can_save: bool
    generated_at: datetime
    line_class: LineClass | None = None
