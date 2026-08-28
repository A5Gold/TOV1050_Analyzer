import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.calculation.stagger_formula import (
    calculate_allowable_value,
    calculate_b_value,
    calculate_e_value,
    calculate_p_value,
    calculate_s_value,
    is_short_circuit_pass,
)
from app.core.calculation.stagger_types import (
    ResolvedMeasurements,
    ResolvedReference,
    SelectedSummaryRecord,
    StaggerSummaryResult,
)


def test_selected_summary_record_keeps_summary_first_fields_needed_by_service():
    record = SelectedSummaryRecord(
        id="SG-001",
        run_date="2026-05-05",
        line="EAL",
        track="up",
        section="UNI-TAP",
        tension_length="H01",
        level="L1",
        exception_type="Stagger Left",
        max_value=132.4,
        max_location=121000.0,
    )

    assert record.id == "SG-001"
    assert record.run_date == "2026-05-05"
    assert record.section == "UNI-TAP"
    assert record.tension_length == "H01"
    assert record.level == "L1"
    assert record.max_value == 132.4


def test_stagger_summary_result_supports_spec_summary_fields_with_optional_defaults():
    result = StaggerSummaryResult(
        id="SG-001",
        run_date="2026-05-05",
        line="EAL",
        track="up",
        section="UNI-TAP",
        tension_length="H01",
        level="L1",
        exception_type="Stagger Left",
        max_value=132.4,
        max_location=121000.0,
        chi=121000.0,
        spt_i=121020.0,
        k_eq=1.32,
        overall_result="pass",
        trace_available=True,
    )

    assert result.run_date == "2026-05-05"
    assert result.section == "UNI-TAP"
    assert result.tension_length == "H01"
    assert result.level == "L1"
    assert result.max_value == 132.4
    assert result.remark == []
    assert result.span_ai is None
    assert result.span_ib is None


def test_stagger_summary_result_remark_default_factory_is_not_shared():
    first = StaggerSummaryResult(
        id="SG-001",
        run_date="2026-05-05",
        line="EAL",
        track="up",
        exception_type="Stagger Left",
        max_location=121000.0,
        chi=121000.0,
        spt_i=121020.0,
        k_eq=None,
        overall_result="n/a",
        trace_available=False,
    )
    second = StaggerSummaryResult(
        id="SG-002",
        run_date="2026-05-06",
        line="TML",
        track="down",
        exception_type="Stagger Right",
        max_location=221000.0,
        chi=221000.0,
        spt_i=None,
        k_eq=None,
        overall_result="n/a",
        trace_available=False,
    )

    first.remark.append("Case A")

    assert first.remark == ["Case A"]
    assert second.remark == []


def test_resolved_types_keep_optional_measurement_and_reference_values():
    reference = ResolvedReference(
        chi=121000.0,
        spt_a=None,
        spt_i=121020.0,
        spt_b=None,
        span_ai=None,
        span_ib=None,
    )
    measurements = ResolvedMeasurements()

    assert reference.spt_a is None
    assert reference.spt_b is None
    assert measurements.hgt_a is None
    assert measurements.stg_i is None


def test_calculate_b_value_matches_known_formula_result():
    result = calculate_b_value(span=50.0, k_eq=1.2, tension=13.8)

    assert result == pytest.approx(67.13, abs=0.01)


def test_calculate_p_value_returns_absolute_average_stagger():
    assert calculate_p_value(stg_x=90.0, stg_i=-30.0) == pytest.approx(30.0)


def test_calculate_s_value_returns_absolute_stagger_difference():
    assert calculate_s_value(stg_x=90.0, stg_i=-30.0) == pytest.approx(120.0)


def test_calculate_e_value_returns_zero_when_b_value_is_not_positive():
    assert calculate_e_value(s_value=120.0, b_value=0.0) == pytest.approx(0.0)


def test_calculate_e_value_uses_span_formula():
    assert calculate_e_value(s_value=120.0, b_value=30.0) == pytest.approx(30.0)


def test_calculate_allowable_value_accepts_resolved_height_correction_value():
    assert calculate_allowable_value(
        b_value=67.13,
        e_value=30.0,
        height_correction=12.5,
    ) == pytest.approx(395.37)


def test_is_short_circuit_pass_uses_four_b_rule():
    assert is_short_circuit_pass(s_value=120.0, b_value=25.0) is True
    assert is_short_circuit_pass(s_value=99.99, b_value=25.0) is False
