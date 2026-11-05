"""Real source regressions for review artifacts; no source workbook authoring."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from review_followup_metadata import read_mapping, compare_workbooks, drl_source_differences
from app.core.tov1050_boundary_review import review_contact_boundaries


def test_five_field_examples_and_contact_role_gate():
    points, invalid, inventory = read_mapping(ROOT / "00 Reference Document/TOV1050 TL-BK No.xlsx")
    assert not invalid
    assert len(inventory) == 16
    reviews = {(r["line"], r["branch"], r["direction"], r["tension_length"]): r
               for r in review_contact_boundaries(points)}
    cr = reviews[("ISL", "Mainline", "UT", "CR289")]
    assert cr["point_count"] == 31
    assert (cr["observed_from_m"], cr["observed_to_m"]) == (99731, 99991)
    assert not cr["known_boundaries"] and cr["candidate"] is None
    same_name = reviews[("TKL", "Mainline", "UT", "579")]
    assert [b["chainage_m"] for b in same_name["known_boundaries"]] == [63302, 64561]
    assert len({b["bracket"] for b in same_name["known_boundaries"]}) == 2
    assert all(b["wire_role"] == "contact" for b in same_name["known_boundaries"])
    assert (same_name["candidate"]["from_m"], same_name["candidate"]["to_m"]) == (63302, 64561)
    for tl in ("541",):
        mixed = reviews[("TKL", "Mainline", "UT", tl)]
        assert len(mixed["contact_boundary_positions_m"]) == 1
        assert mixed["candidate"] is None
    mixed = reviews[("TKL", "Mainline", "UT", "581")]
    assert len(mixed["contact_boundary_positions_m"]) == 2
    assert (mixed["candidate"]["from_m"], mixed["candidate"]["to_m"]) == (64501, 65633)
    drl = reviews[("DRL", "Mainline", "unresolved", "487")]
    assert drl["point_count"] == 8
    assert [b["chainage_m"] for b in drl["known_boundaries"]] == [45026]
    assert drl["candidate"] is None
    candidate = reviews[("TKL", "TKS", "DT", "590")]["candidate"]
    assert (candidate["from_m"], candidate["to_m"]) == (65284, 66392)


def test_same_workbook_has_no_semantic_diff_and_drl_threshold_conflict_is_explicit():
    runtime = ROOT / "config/DRL metadata.xlsx"
    assert compare_workbooks(runtime, runtime) == []
    points, _, _ = read_mapping(ROOT / "00 Reference Document/TOV1050 TL-BK No.xlsx")
    differences = drl_source_differences(runtime, ROOT / "00 Reference Document/config/DRL metadata.xlsx", points)
    wear = [r for r in differences if r["kind"] == "threshold_business_difference"
            and r["context"] == "Tunnel/Curve/Wire Wear L1"]
    assert len(wear) == 1
    assert (wear[0]["runtime"], wear[0]["reference"]) == (8.9, 9.1)
    assert any(r.get("bracket") == "487-BWA" and r["kind"] == "mapping_missing_from_reference" for r in differences)
