import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.calculation.stagger_metadata import SupportPoint
from app.core.calculation.stagger_types import SelectedSummaryRecord


def test_resolve_reference_points_finds_nearest_and_adjacent_supports():
    from app.core.calculation.stagger_reference import resolve_reference_points

    record = SelectedSummaryRecord(
        id="A1",
        line="EAL",
        track="up",
        exception_type="Stagger Left",
        max_location=121000.0,
    )
    supports = [
        SupportPoint(line="EAL", track="up", chainage=120900.0),
        SupportPoint(line="EAL", track="up", chainage=121020.0),
        SupportPoint(line="EAL", track="up", chainage=121120.0),
    ]

    resolved = resolve_reference_points(record, supports)

    assert resolved.chi == 121000.0
    assert resolved.spt_i == 121020.0
    assert resolved.spt_a == 120900.0
    assert resolved.spt_b == 121120.0
    assert resolved.span_ai == 120.0
    assert resolved.span_ib == 100.0


def test_resolve_reference_points_returns_none_for_missing_adjacent_supports():
    from app.core.calculation.stagger_reference import resolve_reference_points

    record = SelectedSummaryRecord(
        id="A2",
        line="EAL",
        track="up",
        exception_type="Stagger Left",
        max_location=121010.0,
    )
    supports = [
        SupportPoint(line="EAL", track="up", chainage=121000.0),
        SupportPoint(line="EAL", track="up", chainage=121100.0),
    ]

    resolved = resolve_reference_points(record, supports)

    assert resolved.chi == 121010.0
    assert resolved.spt_i == 121000.0
    assert resolved.spt_a is None
    assert resolved.spt_b == 121100.0
    assert resolved.span_ai is None
    assert resolved.span_ib == 100.0


def test_resolve_reference_points_prefers_non_edge_support_when_nearest_is_first_boundary():
    from app.core.calculation.stagger_reference import resolve_reference_points

    record = SelectedSummaryRecord(
        id="TML-1",
        line="TML",
        track="up",
        exception_type="Stagger Left",
        max_location=1005.0,
    )
    supports = [
        SupportPoint(line="TML", track="up", chainage=1000.0),
        SupportPoint(line="TML", track="up", chainage=1015.0),
        SupportPoint(line="TML", track="up", chainage=1030.0),
    ]

    resolved = resolve_reference_points(record, supports)

    assert resolved.spt_a == 1000.0
    assert resolved.spt_i == 1015.0
    assert resolved.spt_b == 1030.0
    assert resolved.span_ai == 15.0
    assert resolved.span_ib == 15.0
