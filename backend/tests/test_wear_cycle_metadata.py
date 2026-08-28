from dataclasses import FrozenInstanceError
from datetime import date, datetime, timezone
from decimal import Decimal, localcontext
import random
from time import perf_counter

import pandas as pd
import pytest

from app.core.calculation import wear_cycle_metadata as metadata_module
from app.core.calculation.wear_cycle_metadata import (
    METADATA_SOURCES,
    MetadataResolutionError,
    MetadataValidationError,
    SegmentDetectionError,
    build_measurement_resolution_index,
    build_segment_coverage,
    detect_segment,
    detect_segments,
    load_line_metadata,
    metadata_sources,
    natural_key,
    normalize_cycle_date,
    normalize_line_group,
    normalize_section,
    normalize_tension_length,
    resolve_measurement_tension_length,
    resolve_canonical_tl,
    section_for_segments,
)
from app.core.calculation.wear_cycle_types import (
    EXPECTED_SEGMENTS,
    AggregatedWearRecord,
    BusinessKey,
    CanonicalTensionLength,
    ConflictPreview,
    CyclePreview,
    MetadataInterval,
    PhysicalInterval,
    ParsedWearSource,
    RawWearMeasurement,
    SegmentCoverage,
)


def _measurement(
    tension_length: str,
    *,
    track: str = "UP",
    line_group: str = "EAL",
    acquisition_date: date = date(2026, 7, 1),
    chainage: str = "50",
) -> RawWearMeasurement:
    return RawWearMeasurement(
        acquisition_date=acquisition_date,
        line_group=line_group,
        track=track,
        task_no="task-1",
        station_start="A",
        station_end="B",
        chainage=Decimal(chainage),
        wear_min=10.5,
        tension_length=tension_length,
    )


def _source(
    segment: str,
    filename: str,
    from_m: str,
    to_m: str,
    *measurements: RawWearMeasurement,
) -> ParsedWearSource:
    return ParsedWearSource(
        filename=filename,
        segment_name=segment,
        from_m=Decimal(from_m),
        to_m=Decimal(to_m),
        measurements=tuple(measurements),
    )


def test_expected_segments_and_domain_records_are_frozen():
    assert EXPECTED_SEGMENTS == {
        "EAL": (
            "U1", "U2", "U3", "D1", "D2", "D3", "LOW S1",
            "RAC UP", "RAC DN", "LMC UP", "LMC DN",
        ),
        "TML": ("U1", "U2", "U3", "U4", "U5", "D1", "D2", "D3", "D4", "D5"),
    }
    key = BusinessKey("EAL", date(2026, 7, 1), "28")
    with pytest.raises(FrozenInstanceError):
        key.tension_length = "29"

    interval = MetadataInterval("28", "UP", Decimal("1"), Decimal("2"), "EAL UP")
    canonical = CanonicalTensionLength("EAL", "28", "UP", Decimal("1"), Decimal("2"))
    segment = SegmentCoverage("U1", True, 100.0, (), ("u1.xlsx",), (date(2026, 7, 1),))
    conflict = ConflictPreview("c1", "m1", (("u1.xlsx", 10.0),), 10.0, True)
    record = AggregatedWearRecord(key, "UP", Decimal("1"), Decimal("2"), 10.0, 20.0, None, False, (), ())
    preview = CyclePreview(
        "EAL", date(2026, 7, 1), (record,), (segment,), (conflict,), (), (), True,
        datetime(2026, 7, 1, tzinfo=timezone.utc),
    )
    assert (interval.track, canonical.track, preview.can_save) == ("UP", "UP", True)


@pytest.mark.parametrize("raw, expected", [(" eal ", "EAL"), ("Tml", "TML")])
def test_normalize_line_group(raw, expected):
    assert normalize_line_group(raw) == expected


@pytest.mark.parametrize("raw", ["", " ", "WRL", None])
def test_normalize_line_group_rejects_invalid_values(raw):
    with pytest.raises(MetadataValidationError):
        normalize_line_group(raw)


@pytest.mark.parametrize(
    "line_group, raw, expected",
    [
        ("EAL", " mainline ", "Mainline"),
        ("EAL", "RAC", "RAC"),
        ("EAL", "S1", "LOW S1"),
        ("EAL", "low_s1", "LOW S1"),
        ("EAL", "LMC", "LMC"),
        ("TML", "TML", "Mainline"),
    ],
)
def test_normalize_section_uses_line_specific_canonical_values(line_group, raw, expected):
    assert normalize_section(line_group, raw) == expected


@pytest.mark.parametrize(
    "line_group, raw",
    [("EAL", "Depot"), ("TML", "RAC"), ("TML", "LMC")],
)
def test_normalize_section_rejects_unknown_and_cross_line_sections(line_group, raw):
    with pytest.raises(MetadataValidationError, match="not valid"):
        normalize_section(line_group, raw)


def test_section_for_segments_maps_mainline_and_siding_segments():
    assert section_for_segments("EAL", ("D3",)) == "Mainline"
    assert section_for_segments("EAL", ("RAC DN",)) == "RAC"
    assert section_for_segments("EAL", ("LOW S1",)) == "LOW S1"
    assert section_for_segments("EAL", ("LMC UP",)) == "LMC"
    assert section_for_segments("TML", ("D3", "D4", "D5")) == "Mainline"


@pytest.mark.parametrize(
    "raw, expected",
    [("2026-07-01", date(2026, 7, 1)), (date(2026, 7, 2), date(2026, 7, 2))],
)
def test_normalize_cycle_date(raw, expected):
    assert normalize_cycle_date(raw) == expected


@pytest.mark.parametrize("raw", ["", "2026/07/01", "2026-02-30", None])
def test_normalize_cycle_date_rejects_invalid_values(raw):
    with pytest.raises(MetadataValidationError):
        normalize_cycle_date(raw)


@pytest.mark.parametrize(
    "raw, expected",
    [(" 28.0 ", "28"), (Decimal("28.50"), "28.5"), ("A-28b", "A-28b")],
)
def test_normalize_tension_length(raw, expected):
    assert normalize_tension_length(raw) == expected


@pytest.mark.parametrize("raw", ["", " ", None, float("nan"), float("inf")])
def test_normalize_tension_length_rejects_invalid_values(raw):
    with pytest.raises(MetadataValidationError):
        normalize_tension_length(raw)


def test_natural_key_sorts_numeric_and_alphanumeric_values_deterministically():
    values = ["X10", "101", "10", "X2", "2", "1"]
    assert sorted(values, key=natural_key) == ["1", "2", "10", "101", "X2", "X10"]


@pytest.mark.parametrize(
    "line_group, token, expected",
    [
        ("EAL", "U1", "U1"), ("EAL", "U1A", "U1"),
        ("EAL", "U2", "U2"), ("EAL", "U3", "U3"),
        ("EAL", "D1", "D1"), ("EAL", "D1A", "D1"),
        ("EAL", "D2", "D2"), ("EAL", "D3", "D3"),
        ("TML", "U4", "U4"), ("TML", "U5", "U5"),
        ("TML", "D4", "D4"), ("TML", "D5", "D5"),
        ("EAL", "UP_RAC", "RAC UP"), ("EAL", "RAC_UP", "RAC UP"),
        ("EAL", "DN_RAC", "RAC DN"), ("EAL", "RAC_DN", "RAC DN"),
        ("EAL", "S1_LOW", "LOW S1"), ("EAL", "LOW_S1", "LOW S1"),
        ("EAL", "UP_LOW", "LOW S1"),
        ("EAL", "UP_LMC", "LMC UP"), ("EAL", "LMC_UP", "LMC UP"),
        ("EAL", "DN_LMC", "LMC DN"), ("EAL", "LMC_DN", "LMC DN"),
    ],
)
def test_detect_segment_supports_every_alias(line_group, token, expected):
    assert detect_segment(line_group, f"survey-{token}-wear.xlsx", {}) == expected


def test_detect_segment_uses_filename_before_source_fields():
    assert detect_segment("EAL", "survey_U1.xlsx", {"section": "D1"}) == "U1"


def test_detect_segment_falls_back_to_source_field_values():
    assert detect_segment("EAL", "survey.xlsx", {"section": "DN_RAC"}) == "RAC DN"


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("20260511_TML_D5-D3_TUM-HUH_Exception_Report.xlsx", ("D3", "D4", "D5")),
        ("20260512_TML_U3-U5_HUH-TUM_Exception_Report.xlsx", ("U3", "U4", "U5")),
        ("20260418_TML_D2_HUH-TAW_Exception_Report.xlsx", ("D2",)),
    ],
)
def test_detect_segments_expands_contiguous_report_ranges(filename, expected):
    assert detect_segments("TML", filename, ()) == expected


@pytest.mark.parametrize(
    "line_group, filename, expected_matches",
    [
        ("EAL", "2026_TML_U1_x.xlsx", ("TML",)),
        ("TML", "2026_EAL_D1_x.xlsx", ("EAL",)),
        ("EAL", "2026_EAL_TML_U1_x.xlsx", ("EAL", "TML")),
    ],
)
def test_detect_segment_rejects_wrong_or_ambiguous_filename_line_tokens(
    line_group, filename, expected_matches
):
    with pytest.raises(SegmentDetectionError) as exc_info:
        detect_segment(line_group, filename, {})

    assert exc_info.value.filename == filename
    assert exc_info.value.matches == expected_matches


@pytest.mark.parametrize(
    "line_group, filename, expected",
    [
        ("EAL", "STEALTH_EALISH_U1.xlsx", "U1"),
        ("TML", "TMLONG_D1.xlsx", "D1"),
    ],
)
def test_detect_segment_does_not_treat_line_substrings_as_line_tokens(
    line_group, filename, expected
):
    assert detect_segment(line_group, filename, {}) == expected


@pytest.mark.parametrize(
    "line_group, filename, fields",
    [
        ("EAL", "U1_D1.xlsx", {}),
        ("EAL", "survey.xlsx", {}),
        ("EAL", "U4.xlsx", {}),
        ("EAL", "U10.xlsx", {}),
        ("EAL", "survey.xlsx", {"one": "U1", "two": "D1"}),
    ],
)
def test_detect_segment_rejects_ambiguous_unknown_and_wrong_line_values(line_group, filename, fields):
    with pytest.raises(SegmentDetectionError):
        detect_segment(line_group, filename, fields)


def test_metadata_sources_cover_every_supported_sheet_in_order():
    assert metadata_sources("EAL") == (
        ("UP", "Mainline", "EAL UP"),
        ("DN", "Mainline", "EAL DN"),
        ("UP", "RAC", "RAC UP"),
        ("DN", "RAC", "RAC DN"),
        ("UP", "LOW S1", "LOW S1"),
        ("DN", "LOW S1", "LOW S1"),
        ("UP", "LMC", "LMC UP"),
        ("DN", "LMC", "LMC DN"),
    )
    assert metadata_sources("TML") == (
        ("UP", "Mainline", "TML UP"),
        ("DN", "Mainline", "TML DN"),
    )
    assert METADATA_SOURCES["EAL"] == metadata_sources("EAL")


class _FakeMetadataManager:
    def __init__(self, frames):
        self.frames = frames
        self.calls = []

    def get_tension_length_source_rows(self, line, track, section):
        self.calls.append((line, track, section))
        return self.frames.get((track, section), pd.DataFrame())


def test_load_line_metadata_calls_all_sources_expands_commas_and_sorts_deterministically():
    frames = {
        ("UP", "Mainline"): pd.DataFrame([
            {"from_m": "2,000", "to_m": "2,100", "tension_length": "X10, X2"},
            {"from_m": 1000, "to_m": 1100, "tension_length": 28.0},
        ]),
        ("DN", "Mainline"): pd.DataFrame([
            {"from_m": 500, "to_m": 600, "tension_length": "10, 2"},
        ]),
    }
    manager = _FakeMetadataManager(frames)

    result = load_line_metadata(manager, "EAL")

    assert manager.calls == [(line, track, section) for track, section, _ in metadata_sources("EAL") for line in ["EAL"]]
    assert [item.tension_length for item in result] == ["2", "10", "28", "X2", "X10"]
    assert result[0] == MetadataInterval(
        "2",
        "DN",
        Decimal("550"),
        Decimal("600"),
        "EAL DN",
        "Mainline",
        1,
        ("10", "2"),
        Decimal("500"),
        Decimal("600"),
        1,
    )
    assert result[1].source_priority == 0
    assert result[-1].section == "Mainline"
    assert result[-1].sheet_name == "EAL UP"


def test_load_line_metadata_normalizes_directional_lookup_bounds():
    manager = _FakeMetadataManager({
        ("UP", "Mainline"): pd.DataFrame([
            {
                "from_m": 135653,
                "to_m": 134897.9,
                "tension_length": "67",
            },
        ]),
    })

    result = load_line_metadata(manager, "TML")

    assert result == (
        MetadataInterval(
            "67",
            "UP",
            Decimal("134897.9"),
            Decimal("135653"),
            "TML UP",
            "Mainline",
            0,
            ("67",),
            Decimal("134897.9"),
            Decimal("135653"),
            1,
        ),
    )


def test_load_line_metadata_preserves_split_geometry_and_full_source_bounds():
    manager = _FakeMetadataManager({
        ("DN", "Mainline"): pd.DataFrame([
            {
                "from_m": 100,
                "to_m": 120,
                "tension_length": "40,44",
            },
        ]),
    })

    result = load_line_metadata(manager, "TML")
    by_tl = {item.tension_length: item for item in result}

    assert (by_tl["40"].from_m, by_tl["40"].to_m) == (
        Decimal("100"),
        Decimal("110"),
    )
    assert (by_tl["44"].from_m, by_tl["44"].to_m) == (
        Decimal("110"),
        Decimal("120"),
    )
    assert (by_tl["40"].source_from_m, by_tl["40"].source_to_m) == (
        Decimal("100"),
        Decimal("120"),
    )
    assert resolve_canonical_tl("TML", "40", result).to_m == Decimal("110")


def test_load_line_metadata_preserves_descending_composite_token_order():
    manager = _FakeMetadataManager({
        ("DN", "Mainline"): pd.DataFrame([
            {
                "from_m": 120,
                "to_m": 100,
                "tension_length": "40,44",
            },
        ]),
    })

    result = load_line_metadata(manager, "TML")
    by_tl = {item.tension_length: item for item in result}
    index = build_measurement_resolution_index("TML", result)

    assert (by_tl["40"].from_m, by_tl["40"].to_m) == (
        Decimal("110"),
        Decimal("120"),
    )
    assert (by_tl["44"].from_m, by_tl["44"].to_m) == (
        Decimal("100"),
        Decimal("110"),
    )
    assert resolve_measurement_tension_length(
        "TML", "DN", Decimal("105"), index, "40,44", section="Mainline"
    ) == "40"


def test_measurement_resolution_index_is_immutable():
    index = build_measurement_resolution_index(
        "EAL",
        (MetadataInterval("A", "UP", Decimal("100"), Decimal("120"), "EAL UP"),),
    )

    with pytest.raises(TypeError):
        index.intervals_by_tl["A"] = ()
    with pytest.raises(FrozenInstanceError):
        index.line_group = "TML"


def test_measurement_resolution_index_rejects_physical_range_outside_source_range():
    interval = MetadataInterval(
        "A",
        "UP",
        Decimal("90"),
        Decimal("110"),
        "EAL UP",
        source_from_m=Decimal("100"),
        source_to_m=Decimal("120"),
    )

    with pytest.raises(MetadataValidationError, match="physical range.*source range"):
        build_measurement_resolution_index("EAL", (interval,))


@pytest.mark.parametrize(
    "priority, signature, tension_length",
    [
        (2, ("A", "B"), "A"),
        (0, ("A", "B"), "B"),
    ],
)
def test_measurement_resolution_index_rejects_invalid_signature_priority(
    priority, signature, tension_length
):
    interval = MetadataInterval(
        tension_length,
        "UP",
        Decimal("100"),
        Decimal("110"),
        "EAL UP",
        source_priority=priority,
        source_tension_lengths=signature,
        source_from_m=Decimal("100"),
        source_to_m=Decimal("120"),
    )

    with pytest.raises(MetadataValidationError, match="source signature"):
        build_measurement_resolution_index("EAL", (interval,))


@pytest.mark.parametrize(
    "row",
    [
        {"from_m": "NaN", "to_m": 1, "tension_length": "A"},
        {"from_m": 1, "to_m": 2, "tension_length": " "},
        {"from_m": "bad", "to_m": 2, "tension_length": "A"},
    ],
)
def test_load_line_metadata_rejects_the_entire_load_when_any_row_is_invalid(row):
    manager = _FakeMetadataManager({("UP", "Mainline"): pd.DataFrame([row])})
    with pytest.raises(MetadataValidationError, match="row"):
        load_line_metadata(manager, "EAL")


def test_load_line_metadata_rejects_unknown_identity_with_actionable_source_context():
    manager = _FakeMetadataManager({
        ("UP", "Mainline"): pd.DataFrame([
            {"from_m": 100, "to_m": 120, "tension_length": "1, NEW-TL"},
        ]),
    })

    with pytest.raises(MetadataValidationError) as exc_info:
        load_line_metadata(manager, "EAL")

    detail = str(exc_info.value)
    assert "EAL" in detail
    assert "EAL UP row 1" in detail
    assert "1, NEW-TL" in detail
    assert "NEW-TL" in detail


def test_resolve_canonical_tl_merges_overlap_touch_and_tolerance_into_full_union():
    intervals = (
        MetadataInterval("28.0", "DN", Decimal("111409"), Decimal("112486.5"), "EAL DN"),
        MetadataInterval("28", "UP", Decimal("112486.5"), Decimal("112700"), "EAL UP"),
        MetadataInterval("28", "DN", Decimal("111361"), Decimal("111633"), "EAL DN"),
    )
    assert resolve_canonical_tl("EAL", "28.00", intervals) == CanonicalTensionLength(
        "EAL", "28", "Siding", Decimal("111361"), Decimal("112700"),
        (PhysicalInterval("Siding", Decimal("111361"), Decimal("112700")),),
    )

    tolerance_intervals = (
        MetadataInterval("A", "UP", Decimal("1"), Decimal("2"), "one"),
        MetadataInterval("A", "UP", Decimal("2.01"), Decimal("3"), "two"),
    )
    assert resolve_canonical_tl("EAL", "A", tolerance_intervals).to_m == Decimal("3")


def test_resolve_canonical_tl_preserves_single_direction_track():
    intervals = (MetadataInterval("A", "DN", Decimal("1"), Decimal("2"), "EAL DN"),)
    assert resolve_canonical_tl("EAL", "A", intervals).track == "DN"


def test_resolve_canonical_tl_preserves_disjoint_physical_intervals_with_bounding_summary():
    intervals = (
        MetadataInterval("A", "UP", Decimal("1"), Decimal("2"), "one"),
        MetadataInterval("A", "UP", Decimal("2.02"), Decimal("3"), "two"),
    )
    canonical = resolve_canonical_tl("EAL", "A", intervals)
    assert (canonical.from_m, canonical.to_m) == (Decimal("1"), Decimal("3"))
    assert canonical.intervals == (
        PhysicalInterval("UP", Decimal("1"), Decimal("2")),
        PhysicalInterval("UP", Decimal("2.02"), Decimal("3")),
    )


def test_measurement_tl_resolution_uses_track_and_chainage_and_rejects_gaps_or_ambiguity():
    intervals = (
        MetadataInterval("M05", "DN", Decimal("100"), Decimal("120"), "TML DN"),
        MetadataInterval("M05", "DN", Decimal("140"), Decimal("160"), "TML DN"),
        MetadataInterval("M07", "DN", Decimal("160"), Decimal("180"), "TML DN"),
    )
    assert resolve_measurement_tension_length("TML", "DN", Decimal("150"), intervals) == "M05"
    with pytest.raises(MetadataResolutionError, match="gap.*130"):
        resolve_measurement_tension_length("TML", "DN", Decimal("130"), intervals)
    with pytest.raises(MetadataResolutionError, match="ambiguous.*160"):
        resolve_measurement_tension_length("TML", "DN", Decimal("160"), intervals)


def test_measurement_tl_resolution_uses_section_and_metadata_token_priority():
    intervals = (
        MetadataInterval(
            "70", "DN", Decimal("130100"), Decimal("130200"), "EAL DN", "Mainline", 0
        ),
        MetadataInterval(
            "X32", "DN", Decimal("130100"), Decimal("130200"), "EAL DN", "Mainline", 1
        ),
        MetadataInterval(
            "L02", "DN", Decimal("130100"), Decimal("130200"), "EAL DN", "Mainline", 2
        ),
        MetadataInterval(
            "L02", "DN", Decimal("130100"), Decimal("130200"), "LMC DN", "LMC", 0
        ),
        MetadataInterval(
            "70", "DN", Decimal("130100"), Decimal("130200"), "LMC DN", "LMC", 1
        ),
        MetadataInterval(
            "X38", "DN", Decimal("130100"), Decimal("130200"), "LMC DN", "LMC", 2
        ),
    )

    assert resolve_measurement_tension_length(
        "EAL",
        "DN",
        Decimal("130170.25"),
        intervals,
        "70, X32, L02",
        section="Mainline",
    ) == "70"
    assert resolve_measurement_tension_length(
        "EAL",
        "DN",
        Decimal("130170.25"),
        intervals,
        "L02, 70, X38",
        section="LMC",
    ) == "L02"


def test_measurement_tl_resolution_selects_tml_primary_token_48():
    intervals = (
        MetadataInterval(
            "48", "DN", Decimal("126300"), Decimal("126400"), "TML DN", "Mainline", 0
        ),
        MetadataInterval(
            "50", "DN", Decimal("126300"), Decimal("126400"), "TML DN", "Mainline", 1
        ),
    )

    assert resolve_measurement_tension_length(
        "TML",
        "DN",
        Decimal("126335.25"),
        intervals,
        "48,50",
        section="Mainline",
    ) == "48"


def test_measurement_tl_resolution_keeps_true_primary_tie_ambiguous():
    intervals = (
        MetadataInterval("A", "DN", Decimal("100"), Decimal("120"), "row one"),
        MetadataInterval("B", "DN", Decimal("100"), Decimal("120"), "row two"),
    )

    with pytest.raises(MetadataResolutionError) as exc_info:
        resolve_measurement_tension_length(
            "TML",
            "DN",
            Decimal("110"),
            intervals,
            "A,B",
            section="Mainline",
        )

    detail = str(exc_info.value)
    assert "ambiguous" in detail
    assert "row one" in detail and "row two" in detail
    assert "[100, 120]" in detail


def test_measurement_tl_resolution_prefers_exact_composite_source_signature():
    intervals = (
        MetadataInterval(
            "40",
            "DN",
            Decimal("123406"),
            Decimal("123498.9"),
            "TML DN",
            "Mainline",
            0,
            ("40", "44"),
        ),
        MetadataInterval(
            "44",
            "DN",
            Decimal("123406"),
            Decimal("123498.9"),
            "TML DN",
            "Mainline",
            1,
            ("40", "44"),
        ),
        MetadataInterval(
            "44",
            "DN",
            Decimal("123015"),
            Decimal("124115.9"),
            "TML DN",
            "Mainline",
            0,
            ("44",),
        ),
    )

    assert resolve_measurement_tension_length(
        "TML",
        "DN",
        Decimal("123498.75"),
        intervals,
        "40,44",
        section="Mainline",
    ) == "40"


def test_measurement_tl_resolution_uses_exact_transition_after_strict_section_gap():
    intervals = (
        MetadataInterval(
            "23",
            "UP",
            Decimal("111301"),
            Decimal("111327.875"),
            "EAL UP",
            "Mainline",
            0,
            ("23", "25"),
            Decimal("111301"),
            Decimal("111354.75"),
        ),
        MetadataInterval(
            "25",
            "UP",
            Decimal("111327.875"),
            Decimal("111354.75"),
            "EAL UP",
            "Mainline",
            1,
            ("23", "25"),
            Decimal("111301"),
            Decimal("111354.75"),
        ),
    )

    assert resolve_measurement_tension_length(
        "EAL",
        "UP",
        Decimal("111301.0"),
        intervals,
        "23,25",
        section="RAC",
    ) == "23"


def test_measurement_tl_resolution_rejects_exact_transition_source_row_collision():
    intervals = tuple(
        MetadataInterval(
            tension_length,
            "UP",
            Decimal("111301"),
            Decimal("111354.75"),
            sheet_name,
            "Mainline",
            priority,
            ("23", "25"),
            Decimal("111301"),
            Decimal("111354.75"),
        )
        for sheet_name in ("EAL UP row one", "EAL UP row two")
        for priority, tension_length in enumerate(("23", "25"))
    )

    with pytest.raises(MetadataResolutionError, match="transition.*multiple source rows"):
        resolve_measurement_tension_length(
            "EAL",
            "UP",
            Decimal("111301.0"),
            intervals,
            "23,25",
            section="RAC",
        )


def test_measurement_tl_resolution_does_not_expand_one_track_through_siding_bounds():
    intervals = (
        MetadataInterval("A", "UP", Decimal("0"), Decimal("10"), "EAL UP"),
        MetadataInterval("A", "DN", Decimal("5"), Decimal("15"), "EAL DN"),
    )

    with pytest.raises(MetadataResolutionError, match="gap.*12"):
        resolve_measurement_tension_length(
            "EAL", "UP", Decimal("12"), intervals, raw_tension_length="A"
        )

    assert resolve_measurement_tension_length(
        "EAL", "DN", Decimal("12"), intervals, raw_tension_length="A"
    ) == "A"


def test_resolve_canonical_tl_rejects_unknown_reversed_and_nonfinite_ranges():
    with pytest.raises(MetadataResolutionError, match="unknown"):
        resolve_canonical_tl("EAL", "missing", ())
    with pytest.raises(MetadataValidationError, match="reversed"):
        resolve_canonical_tl(
            "EAL", "A", (MetadataInterval("A", "UP", Decimal("2"), Decimal("1"), "bad"),)
        )
    with pytest.raises(MetadataValidationError, match="finite"):
        resolve_canonical_tl(
            "EAL", "A", (MetadataInterval("A", "UP", Decimal("NaN"), Decimal("1"), "bad"),)
        )


def test_build_segment_coverage_always_returns_expected_order_and_missing_diagnostics():
    result = build_segment_coverage("EAL", (), ())
    assert tuple(item.segment_name for item in result) == EXPECTED_SEGMENTS["EAL"]
    assert all(item == SegmentCoverage(item.segment_name, False, 0.0, ("segment_missing",), (), ()) for item in result)


def test_build_segment_coverage_reports_present_percentage_and_natural_missing_tls():
    intervals = (
        MetadataInterval("10", "UP", Decimal("100"), Decimal("200"), "EAL UP"),
        MetadataInterval("2", "UP", Decimal("0"), Decimal("100"), "EAL UP"),
        MetadataInterval("X10", "UP", Decimal("200"), Decimal("300"), "EAL UP"),
        MetadataInterval("D1", "DN", Decimal("0"), Decimal("100"), "EAL DN"),
    )
    source = _source("U1", "u1.xlsx", "0", "300", _measurement("10"))
    coverage = build_segment_coverage("EAL", (source,), intervals)[0]
    assert coverage.is_present is True
    assert coverage.coverage_percentage == 50.0
    assert coverage.diagnostic_gaps == ("2",)


def test_build_segment_coverage_uses_mainline_only_denominator_and_gaps():
    intervals = (
        MetadataInterval("1", "UP", Decimal("0"), Decimal("100"), "EAL UP"),
        MetadataInterval("X1", "UP", Decimal("0"), Decimal("100"), "EAL UP"),
    )
    source = _source("U1", "u1.xlsx", "0", "100", _measurement("1"))

    coverage = build_segment_coverage("EAL", (source,), intervals)[0]

    assert coverage.coverage_percentage == 100.0
    assert coverage.diagnostic_gaps == ()


def test_build_segment_coverage_keeps_mainline_with_canonical_siding_track():
    intervals = (
        MetadataInterval("1", "UP", Decimal("0"), Decimal("100"), "EAL UP"),
        MetadataInterval("1", "DN", Decimal("0"), Decimal("100"), "EAL DN"),
    )
    source = _source("U1", "u1.xlsx", "0", "100", _measurement("1", track="UP"))

    coverage = build_segment_coverage("EAL", (source,), intervals)[0]

    assert coverage.coverage_percentage == 100.0
    assert coverage.diagnostic_gaps == ()


def test_build_segment_coverage_counts_one_combined_source_for_each_declared_segment():
    intervals = (
        MetadataInterval("1", "DN", Decimal("100"), Decimal("200"), "TML DN"),
    )
    source = _source(
        "D3,D4,D5",
        "TML_D5-D3.xlsx",
        "100",
        "200",
        _measurement("1", line_group="TML", track="DN", chainage="150"),
    )

    coverage = build_segment_coverage("TML", (source,), intervals)

    for segment in ("D3", "D4", "D5"):
        item = coverage[EXPECTED_SEGMENTS["TML"].index(segment)]
        assert item.is_present is True
        assert item.source_file_names == ("TML_D5-D3.xlsx",)


def test_build_segment_coverage_counts_disjoint_metadata_as_one_tl_with_a_gap_detail():
    intervals = (
        MetadataInterval("10", "UP", Decimal("100"), Decimal("200"), "EAL UP"),
        MetadataInterval("3", "UP", Decimal("0"), Decimal("50"), "EAL UP"),
        MetadataInterval("3", "UP", Decimal("50.1"), Decimal("90"), "EAL UP"),
    )
    source = _source("U1", "u1.xlsx", "0", "200", _measurement("10"))

    coverage = build_segment_coverage("EAL", (source,), intervals)[0]

    assert coverage.is_present is True
    assert coverage.coverage_percentage == 50.0
    assert coverage.diagnostic_gaps == ("3",)


def test_build_segment_coverage_reports_empty_metadata_denominator():
    source = _source("U1", "u1.xlsx", "1000", "1100", _measurement("A", chainage="1050"))
    coverage = build_segment_coverage("EAL", (source,), ()) [0]
    assert coverage == SegmentCoverage(
        "U1", False, 0.0, ("metadata_denominator_empty",), ("u1.xlsx",), (date(2026, 7, 1),)
    )


def test_build_segment_coverage_deduplicates_overlapping_ranges_files_dates_and_tls():
    intervals = (
        MetadataInterval("1", "UP", Decimal("100000"), Decimal("111500"), "EAL UP"),
        MetadataInterval("2", "UP", Decimal("120000"), Decimal("130000"), "EAL UP"),
    )
    first = _source(
        "U1", "z.xlsx", "99999", "111999",
        _measurement("1"), _measurement("1"),
    )
    second = _source(
        "U1", "a.xlsx", "111000", "139999",
        _measurement("2"), _measurement("2", acquisition_date=date(2026, 7, 2)),
    )
    coverage = build_segment_coverage("EAL", (first, second), intervals)[0]
    assert coverage.coverage_percentage == 100.0
    assert coverage.diagnostic_gaps == ()
    assert coverage.source_file_names == ("a.xlsx", "z.xlsx")
    assert coverage.acquisition_dates == (date(2026, 7, 1), date(2026, 7, 2))


def test_build_segment_coverage_enforces_segment_track_compatibility_and_low_s1_accepts_both():
    intervals = (
        MetadataInterval("1", "UP", Decimal("0"), Decimal("100"), "EAL UP"),
        MetadataInterval("2", "DN", Decimal("0"), Decimal("100"), "EAL DN"),
    )
    up = _source("U1", "u1.xlsx", "0", "100", _measurement("2", track="DN"))
    low = _source(
        "LOW S1", "low.xlsx", "0", "100",
        _measurement("1", track="UP"), _measurement("2", track="DN"),
    )
    result = build_segment_coverage("EAL", (up, low), intervals)
    assert result[0].coverage_percentage == 0.0
    assert result[0].diagnostic_gaps == ("1",)
    low_coverage = result[EXPECTED_SEGMENTS["EAL"].index("LOW S1")]
    assert low_coverage.is_present is True
    assert low_coverage.coverage_percentage == 100.0


@pytest.mark.parametrize(
    "segment_name, compatible_track, wrong_track",
    [
        ("D1", "DN", "UP"),
        ("RAC UP", "UP", "DN"),
        ("RAC DN", "DN", "UP"),
        ("LMC UP", "UP", "DN"),
        ("LMC DN", "DN", "UP"),
    ],
)
def test_build_segment_coverage_directional_track_matrix_excludes_wrong_metadata_and_measurements(
    segment_name, compatible_track, wrong_track
):
    intervals = (
        MetadataInterval("1", compatible_track, Decimal("0"), Decimal("100"), "good"),
        MetadataInterval(
            "2", compatible_track, Decimal("0"), Decimal("100"), "misdirected"
        ),
        MetadataInterval("3", wrong_track, Decimal("0"), Decimal("100"), "wrong"),
    )
    source = _source(
        segment_name,
        "segment.xlsx",
        "0",
        "100",
        _measurement("1", track=compatible_track),
        _measurement("2", track=wrong_track),
        _measurement("3", track=compatible_track),
    )

    coverage = build_segment_coverage("EAL", (source,), intervals)[
        EXPECTED_SEGMENTS["EAL"].index(segment_name)
    ]

    assert coverage.is_present is True
    assert coverage.coverage_percentage == 50.0
    assert coverage.diagnostic_gaps == ("2",)


@pytest.mark.parametrize(
    "segment_name, measurement_track",
    [
        ("U1", "UP"),
        ("D1", "DN"),
        ("RAC UP", "UP"),
        ("RAC DN", "DN"),
        ("LMC UP", "UP"),
        ("LMC DN", "DN"),
    ],
)
def test_build_segment_coverage_counts_canonical_siding_for_directional_segments(
    segment_name, measurement_track
):
    intervals = (
        MetadataInterval("1", "UP", Decimal("0"), Decimal("100"), "up"),
        MetadataInterval("1", "DN", Decimal("0"), Decimal("100"), "dn"),
    )
    source = _source(
        segment_name,
        "segment.xlsx",
        "0",
        "100",
        _measurement("1", track=measurement_track),
    )

    coverage = build_segment_coverage("EAL", (source,), intervals)[
        EXPECTED_SEGMENTS["EAL"].index(segment_name)
    ]

    assert coverage.is_present is True
    assert coverage.coverage_percentage == 100.0
    assert coverage.diagnostic_gaps == ()


def test_build_segment_coverage_low_s1_counts_up_dn_and_canonical_siding():
    intervals = (
        MetadataInterval("1", "UP", Decimal("0"), Decimal("100"), "up"),
        MetadataInterval("2", "DN", Decimal("0"), Decimal("100"), "dn"),
        MetadataInterval("3", "UP", Decimal("0"), Decimal("100"), "siding-up"),
        MetadataInterval("3", "DN", Decimal("0"), Decimal("100"), "siding-dn"),
    )
    source = _source(
        "LOW S1",
        "low.xlsx",
        "0",
        "100",
        _measurement("1", track="UP"),
        _measurement("2", track="DN"),
        _measurement("3", track="UP"),
    )

    coverage = build_segment_coverage("EAL", (source,), intervals)[
        EXPECTED_SEGMENTS["EAL"].index("LOW S1")
    ]

    assert coverage.is_present is True
    assert coverage.coverage_percentage == 100.0
    assert coverage.diagnostic_gaps == ()


@pytest.mark.parametrize(
    "target_line, measurement_line",
    [("EAL", "TML"), ("TML", "EAL"), ("EAL", "WRL")],
)
def test_build_segment_coverage_excludes_cross_line_and_invalid_line_measurements(
    target_line, measurement_line
):
    intervals = (MetadataInterval("1", "UP", Decimal("0"), Decimal("100"), "up"),)
    source = _source(
        "U1",
        "source.xlsx",
        "0",
        "100",
        _measurement("1", line_group=measurement_line),
    )

    coverage = build_segment_coverage(target_line, (source,), intervals)[0]

    assert coverage.is_present is False
    assert coverage.coverage_percentage == 0.0
    assert coverage.diagnostic_gaps == ("1",)


@pytest.mark.parametrize(
    "fields, expected_matches",
    [
        ({"line": "TML", "section": "U1"}, ("TML",)),
        ({"line": "EAL TML", "section": "U1"}, ("EAL", "TML")),
    ],
)
def test_detect_segment_rejects_wrong_or_ambiguous_line_tokens_in_fallback_fields(
    fields, expected_matches
):
    with pytest.raises(SegmentDetectionError) as exc_info:
        detect_segment("EAL", "survey.xlsx", fields)

    assert exc_info.value.filename == "survey.xlsx"
    assert exc_info.value.matches == expected_matches


def test_detect_segment_accepts_matching_line_token_and_segment_in_fallback_fields():
    assert detect_segment("EAL", "survey.xlsx", {"line": "EAL", "section": "U1"}) == "U1"


def test_detect_segment_uses_token_boundaries_for_fallback_field_line_values():
    fields = {"line": "STEALTH_EALISH", "section": "U1"}
    assert detect_segment("EAL", "survey.xlsx", fields) == "U1"


def test_natural_key_has_total_order_for_zero_padding_and_case_variants():
    values = ["h01", "file01", "File1", "H01", "file1", "h1", "FILE1", "H1"]
    expected = ["FILE1", "File1", "file1", "file01", "H1", "H01", "h1", "h01"]

    assert sorted(values, key=natural_key) == expected
    assert sorted(set(values), key=natural_key) == expected
    for seed in range(10):
        shuffled = values.copy()
        random.Random(seed).shuffle(shuffled)
        assert sorted(shuffled, key=natural_key) == expected


def test_normalize_tension_length_renders_large_decimals_exactly_independent_of_context():
    first = "1234567890123456789012345678901.5000"
    second = "1234567890123456789012345678902.5000"
    with localcontext() as context:
        context.prec = 5
        normalized = (normalize_tension_length(first), normalize_tension_length(second))

    assert normalized == (
        "1234567890123456789012345678901.5",
        "1234567890123456789012345678902.5",
    )


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("000123.45000", "123.45"),
        ("-000.5000", "-0.5"),
        ("-0.000", "0"),
        ("+001.00", "1"),
        ("-1200.00", "-1200"),
    ],
)
def test_normalize_tension_length_exact_renderer_handles_zero_and_sign(raw, expected):
    assert normalize_tension_length(raw) == expected


@pytest.mark.parametrize("raw", ["1e100000", "9" * 129, "A" * 129])
def test_normalize_tension_length_rejects_canonical_output_over_128_characters(raw):
    assert metadata_module.MAX_CANONICAL_TL_LENGTH == 128
    with pytest.raises(MetadataValidationError, match="128"):
        normalize_tension_length(raw)


@pytest.mark.parametrize(
    "from_m, to_m",
    [
        (Decimal("NaN"), Decimal("100")),
        (Decimal("0"), Decimal("Infinity")),
        (Decimal("101"), Decimal("100")),
        ("not-a-number", Decimal("100")),
    ],
)
def test_build_segment_coverage_rejects_invalid_source_ranges_with_filename(from_m, to_m):
    source = ParsedWearSource("bad-source.xlsx", "U1", from_m, to_m, (_measurement("A"),))
    intervals = (MetadataInterval("A", "UP", Decimal("0"), Decimal("100"), "up"),)

    with pytest.raises(MetadataValidationError, match="bad-source.xlsx"):
        build_segment_coverage("EAL", (source,), intervals)


@pytest.mark.parametrize("invalid_frame", [[1], "not-tabular", [{"from_m": 1}, 2]])
def test_load_line_metadata_rejects_non_mapping_lookup_rows_without_leaking_attribute_errors(
    invalid_frame
):
    manager = _FakeMetadataManager({("UP", "Mainline"): invalid_frame})

    with pytest.raises(
        MetadataValidationError, match="^metadata lookup must return tabular rows$"
    ):
        load_line_metadata(manager, "EAL")


def test_records_accepts_dataframe_and_list_of_mappings():
    rows = [{"from_m": 1, "to_m": 2, "tension_length": "A"}]
    assert metadata_module._records(pd.DataFrame(rows)) == rows
    assert metadata_module._records(rows) == rows


def test_build_segment_coverage_groups_once_and_resolves_each_unique_tl_once(monkeypatch):
    intervals = tuple(
        MetadataInterval(str(index), "UP", Decimal("0"), Decimal("100"), "up")
        for index in range(100)
    )
    measurements = tuple(_measurement(str(index % 100)) for index in range(1000))
    source = _source("U1", "bulk.xlsx", "0", "100", *measurements)
    calls = {"group": 0, "resolve": 0}
    original_group = metadata_module._group_intervals_by_tl
    original_resolve = metadata_module._resolve_canonical_group

    def counted_group(*args, **kwargs):
        calls["group"] += 1
        return original_group(*args, **kwargs)

    def counted_resolve(*args, **kwargs):
        calls["resolve"] += 1
        return original_resolve(*args, **kwargs)

    monkeypatch.setattr(metadata_module, "_group_intervals_by_tl", counted_group)
    monkeypatch.setattr(metadata_module, "_resolve_canonical_group", counted_resolve)

    coverage = build_segment_coverage("EAL", (source,), intervals)[0]

    assert coverage.coverage_percentage == 100.0
    assert calls == {"group": 1, "resolve": 100}


def test_build_segment_coverage_large_input_smoke_completes_within_wide_limit():
    intervals = tuple(
        MetadataInterval(str(index), "UP", Decimal("0"), Decimal("100"), "up")
        for index in range(300)
    )
    measurements = tuple(_measurement(str(index % 300)) for index in range(3000))
    source = _source("U1", "large.xlsx", "0", "100", *measurements)

    started = perf_counter()
    coverage = build_segment_coverage("EAL", (source,), intervals)[0]
    elapsed = perf_counter() - started

    assert coverage.coverage_percentage == 100.0
    assert elapsed < 10.0
