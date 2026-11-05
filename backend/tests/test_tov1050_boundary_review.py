import math
import pytest

from app.core.tov1050_boundary_review import review_contact_boundaries, termination_evidence


def point(m, label, classification="termination", **extra):
    return dict(line="TKL", branch="Mainline", direction="UT", tension_length="581",
                chainage_m=m, bracket=label, classification=classification,
                source_sheet="TKL UT", source_excel_row=2, component_index=1, **extra)


def test_contact_pair_retains_provenance_and_stays_review_only():
    source = [point(10, "581-BWA_C"), point(20, "581-Fixed_C"), point(15, "581-001", "normal")]
    result = review_contact_boundaries(source)[0]
    assert result["candidate"]["from_m"] == 10
    assert result["candidate"]["to_m"] == 20
    assert result["candidate"]["required_approval"] == "pairing_continuity_scope_and_coverage"
    assert result["approved_by"] is None
    assert result["point_evidence"][0]["source_excel_row"] == 2
    assert "boundary_confirmed" not in source[0]  # no mutation


def test_same_side_contact_messenger_is_not_a_pair():
    result = review_contact_boundaries([point(12, "581-BWA_C"), point(14, "581-BWA_M"),
                                        point(1, "581-001", "normal")])[0]
    assert result["candidate"] is None
    assert result["contact_boundary_positions_m"] == [12]
    assert "one_contact_boundary_missing_other_end" in result["gaps"]


def test_user_confirmed_untyped_terminals_can_form_review_only_contact_pair():
    result = review_contact_boundaries([point(1, "581-BWA@1m"), point(20, "581-BWA@20m")])[0]
    assert len(result["known_boundaries"]) == 2
    assert result["candidate"]["from_m"] == 1
    assert result["candidate"]["to_m"] == 20
    assert all(b["wire_role_basis"] == "user_confirmed_untyped_contact_2026-10-29" for b in result["known_boundaries"])
    assert result["approved_by"] is None


def test_no_terminal_extrema_remain_observations():
    result = review_contact_boundaries([point(1, "581-001", "normal"), point(20, "581-002", "normal")])[0]
    assert (result["observed_from_m"], result["observed_to_m"]) == (1, 20)
    assert result["candidate"] is None


@pytest.mark.parametrize("points,gap", [
    ([point(1, "581-BWA_C"), point(2, "581-Fixed_C"), point(3, "581-Spring_C")],
     "multiple_contact_boundaries_require_segment_pairing"),
    ([point(1, "581-BWA_C"), point(2, "581-Fixed_C"), point(3, "581-001", "normal")],
     "ordinary_brackets_outside_contact_pair"),
    ([point(1, "581-BWA_C"), point(3, "581-Fixed_C"), point(2, "581-BWA")],
     "multiple_contact_boundaries_require_segment_pairing"),
    ([point(1, "581-001", "normal"), point(2, "581-001", "normal")],
     "normal_bracket_identity_multiple_locations"),
])
def test_ambiguous_evidence_is_not_activated(points, gap):
    result = review_contact_boundaries(points)[0]
    assert result["candidate"] is None
    assert gap in result["gaps"]


def test_contexts_and_nonphysical_points_do_not_mix():
    up = point(1, "581-BWA_C")
    down = {**point(20, "581-Fixed_C"), "direction": "DT"}
    assert len(review_contact_boundaries([up, down, point(2, "SI-581", "landmark")])) == 2


def test_unresolved_direction_cannot_yield_a_contact_pair_candidate():
    points = [{**point(1, "581-BWA_C"), "direction": "unresolved"},
              {**point(20, "581-Fixed_C"), "direction": "unresolved"}]
    result = review_contact_boundaries(points)[0]
    assert result["candidate"] is None
    assert "direction_scope_unresolved" in result["gaps"]


@pytest.mark.parametrize("label,role", [("581-BWA_C", "contact"), ("581-Fixed_M", "messenger"),
                                       ("581-Spring", "contact"), ("581-BWA_UP", "contact"),
                                       ("581-BWA_C_M", "ambiguous")])
def test_roles_are_exact_suffix_tokens(label, role):
    assert termination_evidence(label)["wire_role"] == role
    assert termination_evidence("581-BWA-M") is None


@pytest.mark.parametrize("value", [math.inf, math.nan, True, "10"])
def test_invalid_metres_fail_closed(value):
    with pytest.raises(ValueError, match="finite canonical metres"):
        review_contact_boundaries([point(value, "581-BWA_C")])
