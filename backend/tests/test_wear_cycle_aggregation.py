from dataclasses import replace
from datetime import date, datetime, timezone
from decimal import Decimal
import math
from time import perf_counter

import pytest

from app.core.calculation import wear_cycle_aggregation as aggregation_module
from app.core.calculation.wear_calculator import calculate_wear_percentage
from app.core.calculation.wear_cycle_aggregation import build_cycle_preview, preview_digest
from app.core.calculation.wear_cycle_types import (
    EXPECTED_SEGMENTS,
    MetadataInterval,
    ParsedWearSource,
    RawWearMeasurement,
)


def measurement(
    tension_length: str,
    chainage: float,
    wear_min: float,
    *,
    acquisition_date: date = date(2026, 5, 28),
    line_group: str = "EAL",
    track: str = "UP",
    task_no: str = "9",
    station_start: str = "A",
    station_end: str = "B",
    stable_measurement_id: str | None = None,
) -> RawWearMeasurement:
    return RawWearMeasurement(
        acquisition_date=acquisition_date,
        line_group=line_group,
        track=track,
        task_no=task_no,
        station_start=station_start,
        station_end=station_end,
        chainage=Decimal(str(chainage)),
        wear_min=wear_min,
        tension_length=tension_length,
        stable_measurement_id=stable_measurement_id,
    )


def source(
    segment_name: str,
    from_m: float,
    to_m: float,
    *measurements: RawWearMeasurement,
    filename: str | None = None,
) -> ParsedWearSource:
    return ParsedWearSource(
        filename=filename or f"{segment_name}.xlsx",
        segment_name=segment_name,
        from_m=Decimal(str(from_m)),
        to_m=Decimal(str(to_m)),
        measurements=tuple(measurements),
    )


def metadata_for_tl28() -> tuple[MetadataInterval, ...]:
    return (
        MetadataInterval("28", "UP", Decimal("111361"), Decimal("111633"), "U2"),
        MetadataInterval("28", "DN", Decimal("111409"), Decimal("112486.5"), "D1"),
    )


def complete_sources(
    line_group: str,
    *provided: ParsedWearSource,
    filler_tension_length: str = "1",
) -> tuple[ParsedWearSource, ...]:
    present = {item.segment_name for item in provided}
    matching_wear = [
        item.wear_min
        for source_item in provided
        for item in source_item.measurements
        if item.tension_length == filler_tension_length and math.isfinite(item.wear_min)
    ]
    filler_wear = min(matching_wear, default=11.0)
    fillers = tuple(
        source(
            segment,
            0,
            200000,
            measurement(
                filler_tension_length,
                50,
                filler_wear,
                line_group=line_group,
                track=compatible_track(segment),
                task_no=f"filler-{segment}",
            ),
            filename=f"{segment}-filler.xlsx",
        )
        for segment in EXPECTED_SEGMENTS[line_group]
        if segment not in present
    )
    return tuple(provided) + fillers


def compatible_track(segment_name: str) -> str:
    return "DN" if segment_name.startswith("D") or segment_name.endswith(" DN") else "UP"


def metadata_for_a() -> tuple[MetadataInterval, ...]:
    return (
        MetadataInterval("1", "UP", Decimal("0"), Decimal("100"), "UP"),
        MetadataInterval("1", "DN", Decimal("0"), Decimal("100"), "DN"),
    )


def tml_mainline_tension_lengths() -> tuple[str, ...]:
    return (
        tuple(str(index) for index in range(1, 75))
        + tuple(f"M{index}" for index in range(1, 34))
        + tuple(f"D{index}" for index in range(1, 61))
        + tuple(f"U{index}" for index in range(1, 56))
        + tuple(f"K{index}" for index in range(1, 17))
        + tuple(
            f"U{base}/{suffix}"
            for base in (7, 8, 31, 36)
            for suffix in (1, 2)
        )
    )


def sources_for_every_segment(
    line_group: str,
    measurement_factory,
) -> tuple[ParsedWearSource, ...]:
    return tuple(
        source(
            segment_name,
            0,
            100,
            *measurement_factory(segment_name),
            filename=f"{segment_name}.xlsx",
        )
        for segment_name in EXPECTED_SEGMENTS[line_group]
    )


def test_preview_merges_tl_across_overlapping_files_and_uses_canonical_range():
    preview = build_cycle_preview(
        line_group="EAL",
        requested_cycle_date="2026-05-28",
        sources=[
            source(
                "U2",
                99999.0,
                111999.0,
                measurement("28", 111361.0, 11.8, track="UP"),
                filename="EAL_U2.xlsx",
            ),
            source(
                "D1",
                111000.0,
                139999.0,
                measurement("28", 112486.5, 11.4, track="DN"),
                filename="EAL_D1.xlsx",
            ),
        ],
        metadata=metadata_for_tl28(),
        accepted_conflict_ids=set(),
    )

    assert len(preview.records) == 1
    record = preview.records[0]
    assert record.track == "Siding"
    assert (record.from_m, record.to_m) == (Decimal("111361"), Decimal("112486.5"))
    assert record.avg_wear_min == pytest.approx(11.6)
    assert record.measurement_sd == pytest.approx(0.28)
    assert record.wear_percentage == calculate_wear_percentage(11.6)


def test_exact_duplicates_count_once_and_merge_source_lineage():
    duplicate = measurement("28.0", 111500, 11.7, task_no=" 9 ")
    preview = build_cycle_preview(
        line_group=" eal ",
        requested_cycle_date=None,
        sources=[
            source("U2", 111000, 112000, duplicate, filename="z/EAL_U2.xlsx"),
            source(
                "U2",
                111000,
                112000,
                replace(duplicate, task_no="9"),
                filename="a/EAL_U2.xlsx",
            ),
        ],
        metadata=metadata_for_tl28(),
        accepted_conflict_ids=set(),
    )

    assert preview.records[0].avg_wear_min == 11.7
    assert preview.records[0].measurement_sd is None
    assert preview.records[0].source_lineage == ("a/EAL_U2.xlsx", "z/EAL_U2.xlsx")
    assert preview.conflicts == ()


def test_combined_segment_source_aggregates_each_measurement_once():
    combined = source(
        "D3,D4,D5",
        0,
        100,
        measurement("1", 25, 12.0, line_group="TML", track="DN", task_no="D5-D3"),
        measurement("1", 75, 10.0, line_group="TML", track="DN", task_no="D5-D3"),
        filename="TML_D5-D3.xlsx",
    )

    preview = build_cycle_preview(
        line_group="TML",
        requested_cycle_date="2026-05-11",
        sources=(combined,),
        metadata=(MetadataInterval("1", "DN", Decimal("0"), Decimal("100"), "TML DN"),),
        accepted_conflict_ids=set(),
    )

    assert preview.records[0].avg_wear_min == 11.0
    assert preview.records[0].measurement_sd == pytest.approx(1.41)
    assert preview.records[0].source_lineage == ("TML_D5-D3.xlsx",)


def test_conflicting_identity_previews_lower_value_and_blocks_until_accepted():
    first = source(
        "U2", 111000, 112000,
        measurement("28", 111500, 12.1, task_no="9"),
        filename="a/EAL_U2.xlsx",
    )
    second = source(
        "U2", 111000, 112000,
        measurement("28", 111500, 11.7, task_no="9"),
        filename="b/EAL_U2.xlsx",
    )
    sources = complete_sources("EAL", first, second, filler_tension_length="28")
    blocked = build_cycle_preview(
        line_group="EAL",
        requested_cycle_date=None,
        sources=sources,
        metadata=metadata_for_tl28(),
        accepted_conflict_ids=set(),
    )

    assert blocked.records[0].avg_wear_min == 11.7
    assert len(blocked.conflicts) == 1
    conflict = blocked.conflicts[0]
    assert conflict.source_values == (
        ("a/EAL_U2.xlsx", 12.1),
        ("b/EAL_U2.xlsx", 11.7),
    )
    assert conflict.measurement_identity == (
        'fallback:["EAL","U2","UP","2026-05-28","9","a","b","111500"]'
    )
    assert conflict.conflict_id == blocked.records[0].conflict_ids[0]
    assert "EAL_U2.xlsx" not in conflict.measurement_identity
    assert conflict.is_accepted is False
    assert blocked.records[0].has_data_conflict is True
    assert blocked.can_save is False
    assert "conflict_not_accepted" in blocked.blocking_reasons

    accepted = build_cycle_preview(
        line_group="EAL",
        requested_cycle_date=None,
        sources=sources,
        metadata=metadata_for_tl28(),
        accepted_conflict_ids={conflict.conflict_id},
    )
    assert accepted.can_save is True
    assert accepted.conflicts[0].is_accepted is True
    assert accepted.records[0].has_data_conflict is True
    assert accepted.records[0].conflict_ids == (conflict.conflict_id,)


def test_stable_id_takes_priority_over_fallback_fields():
    sources = [
        source(
            "U2", 111000, 112000,
            measurement("28", 111500, 11.7, task_no="one", stable_measurement_id=" id-7 "),
            filename="one.xlsx",
        ),
        source(
            "U2", 111000, 112000,
            measurement(
                "28", 111600, 11.6,
                acquisition_date=date(2026, 5, 29),
                task_no="two",
                station_start="X",
                station_end="Y",
                stable_measurement_id="id-7",
            ),
            filename="two.xlsx",
        ),
    ]

    preview = build_cycle_preview(
        line_group="EAL",
        requested_cycle_date=None,
        sources=sources,
        metadata=metadata_for_tl28(),
        accepted_conflict_ids=set(),
    )

    assert preview.records[0].measurement_sd is None
    assert preview.records[0].source_lineage == ("one.xlsx", "two.xlsx")
    assert preview.conflicts[0].measurement_identity == "stable:id-7"


def test_stable_ids_are_trimmed_but_remain_case_sensitive():
    preview = build_cycle_preview(
        line_group="EAL",
        requested_cycle_date=None,
        sources=[
            source(
                "U2", 111000, 112000,
                measurement("28", 111500, 11.8, stable_measurement_id=" ID-7 "),
                filename="upper.xlsx",
            ),
            source(
                "U2", 111000, 112000,
                measurement("28", 111500, 11.4, stable_measurement_id="id-7"),
                filename="lower.xlsx",
            ),
        ],
        metadata=metadata_for_tl28(),
        accepted_conflict_ids=set(),
    )

    assert preview.records[0].avg_wear_min == 11.6
    assert preview.records[0].measurement_sd == pytest.approx(0.28)
    assert preview.conflicts == ()


def test_stable_id_does_not_bypass_measurement_track_validation():
    invalid = source(
        "U2", 111000, 112000,
        measurement("28", 111500, 11.7, track="SIDE", stable_measurement_id="id-7"),
        filename="invalid-track.xlsx",
    )
    preview = build_cycle_preview(
        line_group="EAL",
        requested_cycle_date=None,
        sources=complete_sources("EAL", invalid, filler_tension_length="28"),
        metadata=metadata_for_tl28(),
        accepted_conflict_ids=set(),
    )

    assert len(preview.records) == 1
    assert "invalid-track.xlsx" not in preview.records[0].source_lineage
    assert "measurement track must be UP or DN" in preview.unresolved[0]
    assert preview.blocking_reasons == (
        "segment_missing",
        "unresolved_tension_length",
    )


def test_fallback_identity_keeps_different_acquisition_sessions():
    first = measurement("28", 111500, 11.8, acquisition_date=date(2026, 5, 27))
    second = replace(first, acquisition_date=date(2026, 5, 28), wear_min=11.4)
    preview = build_cycle_preview(
        line_group="EAL",
        requested_cycle_date=None,
        sources=[source("U2", 111000, 112000, first, second)],
        metadata=metadata_for_tl28(),
        accepted_conflict_ids=set(),
    )

    assert preview.cycle_date == date(2026, 5, 28)
    assert preview.records[0].avg_wear_min == 11.6
    assert preview.records[0].measurement_sd == pytest.approx(0.28)


def test_requested_cycle_date_overrides_latest_acquisition_date():
    preview = build_cycle_preview(
        line_group="EAL",
        requested_cycle_date="2026-06-01",
        sources=[source("U2", 111000, 112000, measurement("28", 111500, 11.7))],
        metadata=metadata_for_tl28(),
        accepted_conflict_ids=set(),
    )
    assert preview.cycle_date == date(2026, 6, 1)
    assert preview.records[0].key.cycle_date == date(2026, 6, 1)


@pytest.mark.parametrize(
    "invalid_measurement",
    [
        measurement(
            "MISSING",
            60,
            10.5,
            acquisition_date=date(2026, 5, 29),
            line_group="TML",
            task_no="unknown-tl",
        ),
        measurement(
            "1",
            60,
            10.5,
            acquisition_date=date(2026, 5, 29),
            line_group="TML",
            track="SIDE",
            task_no="invalid-track",
        ),
        replace(
            measurement(
                "1",
                60,
                10.5,
                acquisition_date=date(2026, 5, 29),
                line_group="TML",
                task_no="invalid-chainage",
            ),
            chainage=Decimal("NaN"),
        ),
        measurement(
            "1",
            60,
            float("nan"),
            acquisition_date=date(2026, 5, 29),
            line_group="TML",
            task_no="invalid-wear",
        ),
    ],
    ids=("unknown-tl", "invalid-track", "invalid-chainage", "invalid-wear"),
)
def test_default_cycle_date_uses_latest_accepted_measurement(invalid_measurement):
    accepted = measurement(
        "1",
        50,
        11.0,
        acquisition_date=date(2026, 5, 28),
        line_group="TML",
        task_no="accepted",
    )
    measured = source("U1", 0, 100, accepted, invalid_measurement, filename="u1.xlsx")

    preview = build_cycle_preview(
        line_group="TML",
        requested_cycle_date=None,
        sources=complete_sources("TML", measured),
        metadata=metadata_for_a(),
        accepted_conflict_ids=set(),
    )

    assert len(preview.records) == 1
    assert preview.records[0].key.tension_length == "1"
    assert preview.cycle_date == date(2026, 5, 28)
    assert preview.records[0].key.cycle_date == date(2026, 5, 28)


def test_default_cycle_date_uses_selected_conflict_observation_date():
    selected = measurement(
        "1",
        50,
        11.0,
        acquisition_date=date(2026, 5, 28),
        line_group="TML",
        stable_measurement_id="stable-a",
    )
    rejected = replace(
        selected,
        acquisition_date=date(2026, 5, 29),
        wear_min=12.0,
    )
    measured = source("U1", 0, 100, selected, rejected, filename="u1.xlsx")

    preview = build_cycle_preview(
        line_group="TML",
        requested_cycle_date=None,
        sources=complete_sources("TML", measured),
        metadata=metadata_for_a(),
        accepted_conflict_ids=set(),
    )

    assert preview.conflicts[0].selected_wear_min == 11.0
    assert preview.cycle_date == date(2026, 5, 28)
    assert preview.records[0].key.cycle_date == date(2026, 5, 28)


@pytest.mark.parametrize("requested", [None, "2026-02-30", "not-a-date"])
def test_missing_or_invalid_cycle_date_blocks_save(requested):
    preview = build_cycle_preview(
        line_group="TML",
        requested_cycle_date=requested,
        sources=sources_for_every_segment("TML", lambda _segment: ()),
        metadata=(),
        accepted_conflict_ids=set(),
    )
    assert preview.cycle_date == date.min
    assert preview.can_save is False
    assert "cycle_date_invalid" in preview.blocking_reasons


def test_missing_segments_unknown_segments_and_unresolved_tls_block_save():
    preview = build_cycle_preview(
        line_group="EAL",
        requested_cycle_date="2026-05-28",
        sources=[
            source("UNKNOWN", 0, 100, filename="unknown.xlsx"),
            source("U1", 0, 100, measurement("missing", 50, 11.0), filename="u1.xlsx"),
        ],
        metadata=(),
        accepted_conflict_ids=set(),
    )
    assert preview.records == ()
    assert any("missing" in item for item in preview.unresolved)
    assert set(preview.blocking_reasons) >= {
        "segment_missing",
        "unknown_segment",
        "unresolved_tension_length",
    }
    assert preview.can_save is False


def test_missing_expected_segment_is_diagnostic_but_allows_partial_save():
    sources = complete_sources("TML")[:-1]
    preview = build_cycle_preview(
        line_group="TML",
        requested_cycle_date="2026-05-28",
        sources=sources,
        metadata=metadata_for_a(),
        accepted_conflict_ids=set(),
    )
    assert preview.blocking_reasons == ("segment_missing",)
    assert preview.records
    assert preview.can_save is True


def test_unknown_segment_independently_blocks_save():
    unknown = source("UNKNOWN", 0, 100, filename="unknown.xlsx")
    preview = build_cycle_preview(
        line_group="TML",
        requested_cycle_date="2026-05-28",
        sources=complete_sources("TML") + (unknown,),
        metadata=metadata_for_a(),
        accepted_conflict_ids=set(),
    )
    assert preview.blocking_reasons == ("unknown_segment",)


def test_unresolved_tension_length_independently_blocks_save():
    unresolved_source = source(
        "U1", 0, 100,
        measurement("missing", 50, 11.0, line_group="TML"),
        filename="u1.xlsx",
    )
    valid_u1 = source(
        "U1", 0, 100,
        measurement("1", 50, 11.0, line_group="TML", task_no="valid-u1"),
        filename="u1-valid.xlsx",
    )
    preview = build_cycle_preview(
        line_group="TML",
        requested_cycle_date="2026-05-28",
        sources=complete_sources("TML", unresolved_source, valid_u1),
        metadata=metadata_for_a(),
        accepted_conflict_ids=set(),
    )
    assert preview.blocking_reasons == ("unresolved_tension_length",)
    assert "missing" in preview.unresolved[0]


def test_coverage_below_100_percent_is_advisory_when_all_segments_are_present():
    measured = source(
        "U1", 0, 100,
        measurement("1", 50, 11.0, line_group="TML"),
        filename="u1.xlsx",
    )
    preview = build_cycle_preview(
        line_group="TML",
        requested_cycle_date="2026-05-28",
        sources=complete_sources("TML", measured),
        metadata=metadata_for_a() + (
            MetadataInterval("2", "UP", Decimal("0"), Decimal("100"), "UP"),
            MetadataInterval("2", "DN", Decimal("0"), Decimal("100"), "DN"),
        ),
        accepted_conflict_ids=set(),
    )
    assert tuple(item.segment_name for item in preview.segments) == EXPECTED_SEGMENTS["TML"]
    assert any(item.coverage_percentage < 100 for item in preview.segments)
    assert preview.can_save is True


def test_empty_sources_for_all_expected_segments_do_not_satisfy_completeness():
    sources = sources_for_every_segment("TML", lambda _segment: ())

    preview = build_cycle_preview(
        line_group="TML",
        requested_cycle_date="2026-05-28",
        sources=sources,
        metadata=metadata_for_a(),
        accepted_conflict_ids=set(),
    )

    assert preview.records == ()
    assert all(not item.is_present for item in preview.segments)
    assert "segment_missing" in preview.blocking_reasons
    assert preview.can_save is False


def test_all_invalid_measurements_do_not_satisfy_segment_completeness():
    def invalid_measurement(segment_name):
        return (
            measurement(
                "1",
                50,
                float("nan"),
                line_group="TML",
                track=compatible_track(segment_name),
                task_no=segment_name,
            ),
        )

    preview = build_cycle_preview(
        line_group="TML",
        requested_cycle_date="2026-05-28",
        sources=sources_for_every_segment("TML", invalid_measurement),
        metadata=metadata_for_a(),
        accepted_conflict_ids=set(),
    )

    assert preview.records == ()
    assert all(not item.is_present for item in preview.segments)
    assert "segment_missing" in preview.blocking_reasons
    assert preview.can_save is False


def test_wrong_track_measurements_do_not_satisfy_segment_completeness():
    def wrong_track_measurement(segment_name):
        required = compatible_track(segment_name)
        wrong = "UP" if required == "DN" else "DN"
        return (
            measurement(
                "1",
                50,
                11.0,
                line_group="TML",
                track=wrong,
                task_no=segment_name,
            ),
        )

    preview = build_cycle_preview(
        line_group="TML",
        requested_cycle_date="2026-05-28",
        sources=sources_for_every_segment("TML", wrong_track_measurement),
        metadata=metadata_for_a(),
        accepted_conflict_ids=set(),
    )

    assert any(not item.is_present for item in preview.segments)
    assert "segment_missing" in preview.blocking_reasons
    assert preview.can_save is False


def test_empty_metadata_denominator_does_not_satisfy_segment_completeness():
    def valid_measurement(segment_name):
        return (
            measurement(
                "1",
                50,
                11.0,
                line_group="TML",
                track=compatible_track(segment_name),
                task_no=segment_name,
            ),
        )

    preview = build_cycle_preview(
        line_group="TML",
        requested_cycle_date="2026-05-28",
        sources=sources_for_every_segment("TML", valid_measurement),
        metadata=(),
        accepted_conflict_ids=set(),
    )

    assert all(not item.is_present for item in preview.segments)
    assert "segment_missing" in preview.blocking_reasons
    assert preview.can_save is False


def test_records_use_one_normalized_tl_row_and_canonical_natural_order():
    metadata = (
        MetadataInterval("10", "UP", Decimal("0"), Decimal("100"), "UP"),
        MetadataInterval("2", "UP", Decimal("0"), Decimal("100"), "UP"),
        MetadataInterval("3", "UP", Decimal("200"), Decimal("300"), "UP"),
    )
    preview = build_cycle_preview(
        line_group="TML",
        requested_cycle_date="2026-05-28",
        sources=[
            source(
                "U1", 0, 300,
                measurement("10.0", 10, 10.0, line_group="TML"),
                measurement("2", 20, 11.0, line_group="TML"),
                measurement("3", 250, 12.0, line_group="TML"),
                measurement("10", 30, 12.0, line_group="TML", task_no="other"),
            )
        ],
        metadata=metadata,
        accepted_conflict_ids=set(),
    )
    assert [item.key.tension_length for item in preview.records] == ["2", "10", "3"]
    assert preview.records[1].avg_wear_min == 11.0


def test_preview_digest_is_deterministic_and_excludes_generated_at():
    kwargs = dict(
        line_group="EAL",
        requested_cycle_date="2026-05-28",
        sources=[source("U2", 111000, 112000, measurement("28", 111500, 11.7))],
        metadata=metadata_for_tl28(),
        accepted_conflict_ids=set(),
    )
    first = build_cycle_preview(**kwargs)
    second = replace(first, generated_at=datetime(2030, 1, 1, tzinfo=timezone.utc))
    changed = replace(second, records=(replace(second.records[0], avg_wear_min=11.6),))
    assert preview_digest(first) == preview_digest(second)
    assert preview_digest(first) != preview_digest(changed)


def test_preview_digest_rejects_nonfinite_record_values():
    preview = build_cycle_preview(
        line_group="EAL",
        requested_cycle_date="2026-05-28",
        sources=[source("U2", 111000, 112000, measurement("28", 111500, 11.7))],
        metadata=metadata_for_tl28(),
        accepted_conflict_ids=set(),
    )
    nonfinite = replace(
        preview,
        records=(replace(preview.records[0], avg_wear_min=float("inf")),),
    )

    with pytest.raises(ValueError, match="JSON compliant"):
        preview_digest(nonfinite)


def test_duplicate_heavy_input_does_not_multiply_samples_and_completes_within_wide_limit():
    repeated = tuple(
        measurement("1", index, 11.0, line_group="TML", stable_measurement_id=f"id-{index}")
        for index in range(5000)
    )
    original = source("U1", 0, 5000, *repeated, filename="original.xlsx")
    duplicate = source("U1", 0, 5000, *repeated, filename="duplicate.xlsx")

    started = perf_counter()
    preview = build_cycle_preview(
        line_group="TML",
        requested_cycle_date="2026-05-28",
        sources=[original, duplicate],
        metadata=(MetadataInterval("1", "UP", Decimal("0"), Decimal("5000"), "UP"),),
        accepted_conflict_ids=set(),
    )
    elapsed = perf_counter() - started

    assert preview.records[0].avg_wear_min == 11.0
    assert preview.records[0].measurement_sd == 0.0
    assert preview.records[0].source_lineage == ("duplicate.xlsx", "original.xlsx")
    assert elapsed < 10.0


def test_unique_tl_resolution_passes_only_matching_metadata_bucket(monkeypatch):
    identities = tml_mainline_tension_lengths()[:200]
    unique_count = len(identities)
    metadata = tuple(
        MetadataInterval(identity, "UP", Decimal("0"), Decimal("200"), "TML UP")
        for identity in identities
    )
    measurements = tuple(
        measurement(
            identity,
            index,
            11.0,
            line_group="TML",
            task_no=f"task-{index}",
        )
        for index, identity in enumerate(identities)
    )
    measured = source("U1", 0, 200, *measurements, filename="unique-tls.xlsx")
    calls = []
    original_resolver = aggregation_module.resolve_canonical_tl

    def recording_resolver(line_group, tension_length, intervals):
        calls.append((tension_length, tuple(interval.tension_length for interval in intervals)))
        return original_resolver(line_group, tension_length, intervals)

    monkeypatch.setattr(aggregation_module, "resolve_canonical_tl", recording_resolver)

    preview = build_cycle_preview(
        line_group="TML",
        requested_cycle_date="2026-05-28",
        sources=[measured],
        metadata=metadata,
        accepted_conflict_ids=set(),
    )

    assert len(preview.records) == unique_count
    assert len(calls) == unique_count
    assert all(interval_tls == (tension_length,) for tension_length, interval_tls in calls)


def test_one_thousand_measurements_across_mainline_tls_complete_within_wide_limit():
    measurement_count = 1000
    identities = tml_mainline_tension_lengths()
    metadata = tuple(
        MetadataInterval(identity, "UP", Decimal("0"), Decimal("1000"), "TML UP")
        for identity in identities
    )
    measurements = tuple(
        measurement(
            identities[index % len(identities)],
            index,
            11.0,
            line_group="TML",
            task_no=f"task-{index}",
        )
        for index in range(measurement_count)
    )
    measured = source("U1", 0, 1000, *measurements, filename="unique-tls.xlsx")

    started = perf_counter()
    preview = build_cycle_preview(
        line_group="TML",
        requested_cycle_date="2026-05-28",
        sources=[measured],
        metadata=metadata,
        accepted_conflict_ids=set(),
    )
    elapsed = perf_counter() - started

    assert len(preview.records) == len(identities)
    assert elapsed < 10.0


def test_complete_cycle_large_finite_values_produce_finite_aggregate_and_digest():
    def large_measurement(segment_name):
        return (
            measurement(
                "1",
                50,
                1e308,
                line_group="TML",
                track=compatible_track(segment_name),
                task_no=segment_name,
            ),
        )

    preview = build_cycle_preview(
        line_group="TML",
        requested_cycle_date="2026-05-28",
        sources=sources_for_every_segment("TML", large_measurement),
        metadata=metadata_for_a(),
        accepted_conflict_ids=set(),
    )

    assert preview.can_save is True
    assert len(preview.records) == 1
    assert math.isfinite(preview.records[0].avg_wear_min)
    assert math.isfinite(preview.records[0].measurement_sd)
    assert len(preview_digest(preview)) == 64


def test_unrepresentable_tl_aggregate_is_unresolved_and_excluded_from_digest():
    def valid_measurement(segment_name):
        return (
            measurement(
                "1",
                50,
                11.0,
                line_group="TML",
                track=compatible_track(segment_name),
                task_no=segment_name,
            ),
        )

    overflow_source = source(
        "U1",
        0,
        100,
        measurement("2", 51, 1.7e308, line_group="TML", task_no="x-positive"),
        measurement("2", 52, -1.7e308, line_group="TML", task_no="x-negative"),
        filename="overflow.xlsx",
    )
    metadata = metadata_for_a() + (
        MetadataInterval("2", "UP", Decimal("0"), Decimal("100"), "UP"),
    )

    preview = build_cycle_preview(
        line_group="TML",
        requested_cycle_date="2026-05-28",
        sources=sources_for_every_segment("TML", valid_measurement) + (overflow_source,),
        metadata=metadata,
        accepted_conflict_ids=set(),
    )

    assert {record.key.tension_length for record in preview.records} == {"1"}
    assert any("aggregate" in item and "2" in item for item in preview.unresolved)
    assert "unresolved_tension_length" in preview.blocking_reasons
    assert all(
        math.isfinite(value)
        for record in preview.records
        for value in (record.avg_wear_min, record.measurement_sd or 0.0, record.wear_percentage)
    )
    assert len(preview_digest(preview)) == 64
