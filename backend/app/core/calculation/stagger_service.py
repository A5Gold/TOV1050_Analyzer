from __future__ import annotations

from app.core.calculation.stagger_formula import (
    calculate_allowable_value,
    calculate_b_value,
    calculate_e_value,
    calculate_p_value,
    calculate_s_value,
    is_short_circuit_pass,
)
from app.core.calculation.stagger_keq import calculate_eal_keq, calculate_tml_keq
from app.core.calculation.stagger_measurements import resolve_measurements
from app.core.calculation.stagger_reference import resolve_reference_points
from app.core.calculation.stagger_types import (
    ResolvedMeasurements,
    ResolvedReference,
    SelectedSummaryRecord,
    StaggerSummaryResult,
)


NEAREST_ROW_ASSUMPTION = "ChartData A/I/B uses nearest-row assumption"
HEIGHT_CORRECTION_NOTE = "HeightCorrection defaulted to 0.0"
INCOMPLETE_TRACE_NOTE = "Incomplete support references for stagger span computation"


def compute_stagger_result_for_record(
    record: SelectedSummaryRecord,
    chart_rows: list[dict[str, object]],
    metadata: dict,
    case_type: str,
    height_correction: float = 0.0,
) -> tuple[StaggerSummaryResult, dict[str, object]]:
    supports = metadata["supports"][record.line][record.track]
    reference = resolve_reference_points(record, supports)

    if reference.spt_a is None or reference.spt_i is None or reference.spt_b is None:
        summary = StaggerSummaryResult(
            id=record.id,
            run_date=record.run_date,
            line=record.line,
            track=record.track,
            section=record.section,
            task_no=record.task_no,
            station_start=record.station_start,
            station_end=record.station_end,
            from_m=record.from_m,
            to_m=record.to_m,
            length=record.length,
            tension_length=record.tension_length,
            overlap=record.overlap,
            track_type=record.track_type,
            level=record.level,
            landmark=record.landmark,
            asset_class=record.asset_class,
            threshold_value=record.threshold_value,
            exception_type=record.exception_type,
            max_value=record.max_value,
            max_location=record.max_location,
            chi=reference.chi,
            spt_a=reference.spt_a,
            spt_i=reference.spt_i,
            spt_b=reference.spt_b,
            span_ai=reference.span_ai,
            span_ib=reference.span_ib,
            k_eq=None,
            overall_result="n/a",
            trace_available=False,
            trace_status="partial",
            chi_source=record.chi_source,
            remark=[f"Case {case_type}", INCOMPLETE_TRACE_NOTE],
        )
        return summary, _build_partial_trace(
            case_type=case_type,
            record=record,
            reference=reference,
            height_correction=height_correction,
        )

    measurements = resolve_measurements(
        chart_rows=chart_rows,
        chi=reference.chi,
        spt_a=reference.spt_a,
        spt_b=reference.spt_b,
    )
    keq_parts = _calculate_keq(record=record, reference=reference, metadata=metadata)
    k_eq = float(keq_parts["k_eq"])
    tension = float(metadata["constants"]["tension"])

    span_results = _build_span_results(
        reference=reference,
        measurements=measurements,
        k_eq=k_eq,
        tension=tension,
        height_correction=height_correction,
    )
    overall_result = _determine_overall_result(span_results)

    summary = StaggerSummaryResult(
        id=record.id,
        run_date=record.run_date,
        line=record.line,
        track=record.track,
        section=record.section,
        task_no=record.task_no,
        station_start=record.station_start,
        station_end=record.station_end,
        from_m=record.from_m,
        to_m=record.to_m,
        length=record.length,
        tension_length=record.tension_length,
        overlap=record.overlap,
        track_type=record.track_type,
        level=record.level,
        landmark=record.landmark,
        asset_class=record.asset_class,
        threshold_value=record.threshold_value,
        exception_type=record.exception_type,
        max_value=record.max_value,
        max_location=record.max_location,
        chi=reference.chi,
        spt_a=reference.spt_a,
        spt_i=reference.spt_i,
        spt_b=reference.spt_b,
        span_ai=reference.span_ai,
        span_ib=reference.span_ib,
        k_eq=k_eq,
        overall_result=overall_result,
        trace_available=True,
        trace_status="complete",
        chi_source=record.chi_source,
        remark=[f"Case {case_type}", NEAREST_ROW_ASSUMPTION, HEIGHT_CORRECTION_NOTE],
    )
    trace = {
        "trace_status": "complete",
        "case_type": case_type,
        "chi_source": record.chi_source,
        "assumptions": {
            "chartdata_mapping": "nearest-row",
            "height_correction": "defaulted_to_zero" if height_correction == 0.0 else "provided",
        },
        "reference": {
            "chi": reference.chi,
            "spt_a": reference.spt_a,
            "spt_i": reference.spt_i,
            "spt_b": reference.spt_b,
        },
        "measurements": {
            "hgt_a": measurements.hgt_a,
            "hgt_i": measurements.hgt_i,
            "hgt_b": measurements.hgt_b,
            "stg_a": measurements.stg_a,
            "stg_i": measurements.stg_i,
            "stg_b": measurements.stg_b,
        },
        "spans": span_results,
        "k_eq": k_eq,
        "keq_components": keq_parts,
    }
    return summary, trace


def _calculate_keq(
    record: SelectedSummaryRecord,
    reference: ResolvedReference,
    metadata: dict,
) -> dict[str, float | None]:
    line_key = record.line.upper()
    if line_key == "EAL":
        wind = metadata["wind_factor"]["EAL"]
        return calculate_eal_keq(
            track=record.track,
            spt_a=reference.spt_a,
            spt_i=reference.spt_i,
            spt_b=reference.spt_b,
            kr_by_track=wind["kr"],
            ke_by_track=wind["ke"],
            kh_by_track=wind["kh"],
        )

    strategy = metadata["wind_factor"]["TML"]
    k_eq = calculate_tml_keq(
        chi=reference.chi,
        boundary=float(strategy["boundary"]),
        above=float(strategy["above"]),
        below_or_equal=float(strategy["below_or_equal"]),
    )
    return {
        "k_a": None,
        "k_i": None,
        "k_b": None,
        "k_ai_max": None,
        "k_ib_max": None,
        "k_eq": k_eq,
    }


def _build_span_results(
    reference: ResolvedReference,
    measurements: ResolvedMeasurements,
    k_eq: float,
    tension: float,
    height_correction: float,
) -> dict[str, dict[str, float | str | bool | None]]:
    spans: dict[str, dict[str, float | str | bool | None]] = {}

    spans["ai"] = _evaluate_span(
        span=reference.span_ai,
        stg_x=measurements.stg_a,
        stg_i=measurements.stg_i,
        height_correction=height_correction,
        k_eq=k_eq,
        tension=tension,
    )
    spans["ib"] = _evaluate_span(
        span=reference.span_ib,
        stg_x=measurements.stg_b,
        stg_i=measurements.stg_i,
        height_correction=height_correction,
        k_eq=k_eq,
        tension=tension,
    )

    return spans


def _evaluate_span(
    span: float | None,
    stg_x: float | None,
    stg_i: float | None,
    height_correction: float,
    k_eq: float,
    tension: float,
) -> dict[str, float | str | bool | None]:
    if span is None or stg_x is None or stg_i is None:
        return {
            "span": span,
            "b": None,
            "p": None,
            "s": None,
            "e": None,
            "allowable": None,
            "short_circuit": None,
            "result": "n/a",
        }

    b_value = calculate_b_value(span=span, k_eq=k_eq, tension=tension)
    p_value = calculate_p_value(stg_x=stg_x, stg_i=stg_i)
    s_value = calculate_s_value(stg_x=stg_x, stg_i=stg_i)
    e_value = calculate_e_value(s_value=s_value, b_value=b_value)
    allowable = calculate_allowable_value(
        b_value=b_value,
        e_value=e_value,
        height_correction=height_correction,
    )
    short_circuit = is_short_circuit_pass(s_value=s_value, b_value=b_value)

    if short_circuit:
        result = "pass_short_circuit"
    elif p_value <= allowable:
        result = "pass"
    else:
        result = "fail"

    return {
        "span": span,
        "b": b_value,
        "p": p_value,
        "s": s_value,
        "e": e_value,
        "allowable": allowable,
        "short_circuit": short_circuit,
        "result": result,
    }


def _determine_overall_result(
    span_results: dict[str, dict[str, float | str | bool | None]]
) -> str:
    results = [str(span_result["result"]) for span_result in span_results.values()]
    if any(result == "fail" for result in results):
        return "fail"
    if any(result in {"pass", "pass_short_circuit"} for result in results):
        return "pass"
    return "n/a"


def _build_partial_trace(
    case_type: str,
    record: SelectedSummaryRecord,
    reference: ResolvedReference,
    height_correction: float,
) -> dict[str, object]:
    return {
        "trace_status": "partial",
        "case_type": case_type,
        "chi_source": "exception_report" if case_type == "A" else "n_repeated",
        "assumptions": {
            "chartdata_mapping": "nearest-row",
            "height_correction": "defaulted_to_zero" if height_correction == 0.0 else "provided",
        },
        "record": {
            "id": record.id,
            "line": record.line,
            "track": record.track,
            "exception_type": record.exception_type,
            "max_location": record.max_location,
            "from_m": record.from_m,
            "to_m": record.to_m,
        },
        "reference": {
            "chi": reference.chi,
            "spt_a": reference.spt_a,
            "spt_i": reference.spt_i,
            "spt_b": reference.spt_b,
        },
        "spans": {},
        "notes": [INCOMPLETE_TRACE_NOTE],
    }
