from dataclasses import dataclass, field
from typing import Literal


TrackType = Literal["up", "down"]
ExceptionType = Literal["Stagger Left", "Stagger Right"]
OverallResult = Literal["pass", "fail", "n/a"]


@dataclass(slots=True)
class SelectedSummaryRecord:
    id: str
    exception_type: ExceptionType
    run_date: str | None = None
    line: str = ""
    track: TrackType = "up"
    section: str | None = None
    task_no: str | None = None
    station_start: str | None = None
    station_end: str | None = None
    from_m: float | None = None
    to_m: float | None = None
    length: float | None = None
    tension_length: str | None = None
    overlap: str | None = None
    track_type: str | None = None
    level: str | None = None
    landmark: str | None = None
    asset_class: str | None = None
    threshold_value: float | None = None
    max_value: float | None = None
    max_location: float = 0.0
    chi_source: str = "exception_report"


@dataclass(slots=True)
class ResolvedReference:
    chi: float
    spt_a: float | None
    spt_i: float | None
    spt_b: float | None
    span_ai: float | None
    span_ib: float | None


@dataclass(slots=True)
class ResolvedMeasurements:
    hgt_a: float | None = None
    hgt_i: float | None = None
    hgt_b: float | None = None
    stg_a: float | None = None
    stg_i: float | None = None
    stg_b: float | None = None


@dataclass(slots=True)
class StaggerSummaryResult:
    id: str
    exception_type: ExceptionType
    run_date: str | None = None
    line: str = ""
    track: TrackType = "up"
    section: str | None = None
    task_no: str | None = None
    station_start: str | None = None
    station_end: str | None = None
    from_m: float | None = None
    to_m: float | None = None
    length: float | None = None
    tension_length: str | None = None
    overlap: str | None = None
    track_type: str | None = None
    level: str | None = None
    landmark: str | None = None
    asset_class: str | None = None
    threshold_value: float | None = None
    max_value: float | None = None
    max_location: float = 0.0
    chi: float = 0.0
    spt_a: float | None = None
    spt_i: float | None = None
    spt_b: float | None = None
    span_ai: float | None = None
    span_ib: float | None = None
    k_eq: float | None = None
    overall_result: OverallResult = "n/a"
    trace_available: bool = False
    trace_status: str = "partial"
    chi_source: str = "exception_report"
    remark: list[str] = field(default_factory=list)
