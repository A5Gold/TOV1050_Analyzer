from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from standardize_tov1050_metadata import standardize_workbook, _wide_thresholds
from validate_tov1050_metadata_candidates import (
    _interval_report,
    _is_landmark,
    _is_bracket_variant,
    _mapping_rows,
    _provenance_check,
    _threshold_check,
    validate_workbook,
)


def _source_frames():
    return {
        "threshold": pd.DataFrame(
            {
                "Location Type": ["Open", "Open"],
                "Track Type": ["Tangent", "Tangent"],
                "Exc Type": ["Low Height L1", "Stagger L2"],
                "min": [None, 300],
                "max": [4500, None],
            }
        ),
        "location type": pd.DataFrame(
            {"location type": ["Open"], "startKM": [48.0], "endKM": [49.0]}
        ),
        "UT track type": pd.DataFrame(
            {"track type": ["Tangent"], "startKM": [48.0], "endKM": [49.0]}
        ),
    }


def _write_source(path: Path) -> None:
    with pd.ExcelWriter(path) as writer:
        for sheet, frame in _source_frames().items():
            frame.to_excel(writer, sheet_name=sheet, index=False)


def _write_mapping(path: Path) -> None:
    with pd.ExcelWriter(path) as writer:
        pd.DataFrame({"Location": [48.1], "Bracket": ["2-045"]}).to_excel(
            writer, sheet_name="AEL UT", index=False
        )


def test_threshold_candidate_matches_canonical_rows():
    source = _source_frames()["threshold"]
    candidate = _wide_thresholds(source)
    report = _threshold_check(source, candidate)

    assert report["schema_match"] is True
    assert report["rows_match"] is True
    assert report["row_diff"]["missing_count"] == 0


def test_lar_mapping_alias_and_invalid_provenance_are_preserved(tmp_path):
    source_path = tmp_path / "LAR_AEL metadata.xlsx"
    mapping_path = tmp_path / "TOV1050 TL-BK No.xlsx"
    candidate_path = tmp_path / "LAR_AEL metadata (wide candidate).xlsx"
    _write_source(source_path)
    _write_mapping(mapping_path)

    standardize_workbook(source_path, mapping_path, candidate_path)
    candidate = pd.read_excel(candidate_path, sheet_name=None)

    # LAR_AEL must resolve the mapping workbook's AEL sheet.
    assert candidate["LAR_AEL UT"]["Bracket"].dropna().tolist() == ["2-045"]
    provenance = candidate["__provenance__"]
    assert ((provenance["source_sheet"] == "AEL UT") & (provenance["status"] == "emitted")).any()

    source_sheets = _source_frames()
    mapping_sheets = {"AEL UT": pd.DataFrame({"Location": [None], "Bracket": ["2-045"]})}
    provenance = pd.DataFrame(
        [
            {"source_sheet": "threshold", "source_row": 2, "status": "emitted", "target_sheet": "threshold"},
            {"source_sheet": "threshold", "source_row": 3, "status": "emitted", "target_sheet": "threshold"},
            {"source_sheet": "location type", "source_row": 2, "status": "emitted", "target_sheet": "Exception Boundarys"},
            {"source_sheet": "UT track type", "source_row": 2, "status": "emitted", "target_sheet": "UT"},
            {"source_sheet": "AEL UT", "source_row": 2, "status": "invalid", "target_sheet": "UT"},
        ]
    )
    report = _provenance_check(
        source_sheets,
        mapping_sheets,
        {"__provenance__": provenance},
        "LAR_AEL",
    )
    assert report["invalid_status_mismatch_count"] == 0
    assert report["target_mismatch_count"] == 0


def test_reversed_interval_is_directional_and_canonicalized_for_parity():
    report = _interval_report(
        pd.DataFrame(
            {"track type": ["Tangent"], "startKM": [49.0], "endKM": [48.0]}
        ),
        "DT track type",
        scale=1000.0,
        group_by_track=True,
    )

    assert report["valid_row_count"] == 1
    assert report["invalid_rows"] == []
    assert report["reversed_row_count"] == 1
    assert report["reversed_rows"][0]["reason"].startswith("directional source ordering")


def test_interval_report_lists_ambiguous_overlap_source_rows():
    report = _interval_report(
        pd.DataFrame({
            "track type": ["Tangent", "Tangent"],
            "startKM": [48.0, 48.5],
            "endKM": [49.0, 49.5],
        }),
        "UT track type",
        scale=1000.0,
        group_by_track=True,
    )

    assert report["ambiguous_overlap_count"] == 1
    assert report["ambiguous_overlap_examples"] == [{
        "label": "Tangent",
        "previous_source_row": 2,
        "current_source_row": 3,
        "previous_start": 48.0,
        "previous_end": 49.0,
        "current_start": 48.5,
        "current_end": 49.5,
        "overlap_m": 500.0,
        "previous_length_m": 1000.0,
        "current_length_m": 1000.0,
    }]
    assert report["overlap_examples_complete"] is True


def test_mapping_marker_and_duplicate_identity_are_review_diagnostics():
    expected, invalid, records, diagnostics = _mapping_rows(
        pd.DataFrame(
            {
                "Location": [48.1, 48.1, 48.2],
                "Bracket": ["2-045", "2-045", "Mid Point"],
            }
        ),
        1000.0,
    )

    assert sum(expected.values()) == 3
    assert invalid == []
    assert len(records) == 3
    assert diagnostics["marker_row_count"] == 1
    assert diagnostics["marker_rows"][0]["bracket"] == "Mid Point"
    assert diagnostics["exact_duplicate_identity_count"] == 1
    assert diagnostics["exact_duplicate_rows"] == [{
        "from_m": 48100.0,
        "bracket": "2-045",
        "source_rows": [2, 3],
    }]


def test_bracket_format_and_landmarks_are_classified_separately():
    assert _is_landmark("123-01") is False
    assert _is_landmark("CR283-15") is False
    assert _is_landmark("SI") is True
    assert _is_landmark("Mid Point") is True
    assert _is_landmark("POA") is True
    assert _is_landmark("POA804-01") is True
    assert _is_landmark("211-1A") is False
    assert _is_landmark("364A-001") is False
    assert _is_landmark("CR185A-01") is False
    assert _is_bracket_variant("211-1A") is True
    assert _is_bracket_variant("364A-001") is True
    assert _is_bracket_variant("CR185A-01") is True
    assert _is_bracket_variant("CR186-10A") is True
    assert _is_bracket_variant("001-002A") is True
    assert _is_bracket_variant("002A-001") is True
    assert _is_bracket_variant("002A-002A") is True
    assert _is_bracket_variant("CR001A-002") is True
    assert _is_bracket_variant("001-002") is False
    assert _is_bracket_variant("POA804-01") is False


def test_letter_variants_are_physical_brackets_for_identity_and_overlap_checks():
    _, _, _, diagnostics = _mapping_rows(
        pd.DataFrame({
            "Location": [48.1, 48.2, 48.1, 48.1],
            "Bracket": ["211-1A", "211-1A", "123-01", "211-1A"],
        }),
        1000.0,
    )

    assert diagnostics["marker_row_count"] == 0
    assert diagnostics["bracket_variant_count"] == 3
    assert diagnostics["exact_duplicate_identity_count"] == 1
    assert diagnostics["exact_duplicate_rows"] == [{
        "from_m": 48100.0,
        "bracket": "211-1A",
        "source_rows": [2, 5],
    }]
    assert diagnostics["bracket_location_conflict_count"] == 1
    assert diagnostics["bracket_location_conflicts"] == [{
        "bracket": "211-1A",
        "from_m_values": [48100.0, 48200.0],
        "source_rows": [2, 3, 5],
    }]
    assert diagnostics["same_location_bracket_overlap_count"] == 1
    assert diagnostics["same_location_bracket_overlaps"] == [{
        "from_m": 48100.0,
        "brackets": ["123-01", "211-1A"],
        "source_rows": [2, 4, 5],
        "rows": [
            {"source_row": 2, "bracket": "211-1A"},
            {"source_row": 4, "bracket": "123-01"},
            {"source_row": 5, "bracket": "211-1A"},
        ],
        "confirmed_variant_overlap": True,
        "variant_brackets": ["211-1A"],
    }]
    assert diagnostics["confirmed_variant_overlap_count"] == 1
    assert diagnostics["unconfirmed_same_location_overlap_count"] == 0


def test_landmarks_do_not_create_same_location_bracket_conflicts():
    _, _, _, diagnostics = _mapping_rows(
        pd.DataFrame({
            "Location": [48.1, 48.1, 48.2, 48.2, 48.2],
            "Bracket": ["123-01", "SI", "123-02", "CR283-15", "Mid Point"],
        }),
        1000.0,
    )

    assert diagnostics["marker_row_count"] == 2
    assert diagnostics["same_location_bracket_overlap_count"] == 1
    assert diagnostics["same_location_bracket_overlaps"] == [{
        "from_m": 48200.0,
        "brackets": ["123-02", "CR283-15"],
        "source_rows": [4, 5],
        "rows": [
            {"source_row": 4, "bracket": "123-02"},
            {"source_row": 5, "bracket": "CR283-15"},
        ],
        "confirmed_variant_overlap": False,
        "variant_brackets": [],
    }]
    assert diagnostics["confirmed_variant_overlap_count"] == 0
    assert diagnostics["unconfirmed_same_location_overlap_count"] == 0
    assert diagnostics["accepted_same_location_overlap_count"] == 1


def test_landmarks_are_excluded_from_bracket_location_uniqueness():
    _, _, _, diagnostics = _mapping_rows(
        pd.DataFrame({
            "Location": [48.1, 48.2, 48.3, 48.4],
            "Bracket": ["Mid Point", "Mid Point", "AFW", "AFW"],
        }),
        1000.0,
    )
    assert diagnostics["marker_row_count"] == 4
    assert diagnostics["bracket_location_conflict_count"] == 0


def test_landmark_duplicates_are_not_physical_identity_duplicates():
    _, _, _, diagnostics = _mapping_rows(
        pd.DataFrame({"Location": [48.1, 48.1], "Bracket": ["Mid Point", "Mid Point"]}),
        1000.0,
    )
    assert diagnostics["marker_row_count"] == 2
    assert diagnostics["exact_duplicate_identity_count"] == 0


def test_unknown_labels_remain_reviewable_and_slash_conflicts_are_not_hidden():
    frame = pd.DataFrame({
        "Location": [48.1, 48.2, 48.3, 48.4, 48.4],
        "Bracket": ["579-XYZ", "579-XYZ", "251-000 / 245-038", "245-038", "245-038"],
    })
    _, invalid, records, diagnostics = _mapping_rows(frame, 1000.0)
    assert invalid == []
    assert len(records) == 6
    assert diagnostics["unclassified_row_count"] == 2
    assert diagnostics["unclassified_location_conflicts"][0]["source_rows"] == [2, 3]
    assert diagnostics["bracket_location_conflicts"] == [{
        "bracket": "245-038", "from_m_values": [48300.0, 48400.0], "source_rows": [4, 5, 6],
    }]
    assert diagnostics["exact_duplicate_identity_count"] == 1


def test_confirmed_mapping_rules_and_unconfirmed_formats():
    from tov1050_mapping_rules import classify
    for label in ["123-001", "211-1", "123A-001A", "481-A01", "481A-A02",
                  "CR272-001", "CR186-022", "CR001A-002", "211-3B", "549-007(T)"]:
        assert classify(label) == "normal"
    for label in ["487-BWA", "148-BWA_UP", "581-BWA_M", "547-Fixed_C", "549-Spring"]:
        assert classify(label) == "termination"
    for label in ["HAH885", "TIS901", "QUB807", "SI-NOP801", "SI-CR186", "SI-211", "POA804-01"]:
        assert classify(label) == "landmark"
    for label in ["595-BMA_C", "545-BWA-M", "155-XXX", "582", "549-007(Z)"]:
        assert classify(label) == "unclassified"


def test_slash_termination_endpoints_and_provenance_tampering(tmp_path):
    import json
    from standardize_tov1050_metadata import _bracket_rows
    frame = pd.DataFrame({
        "Location": [48.1, 48.2, 48.1],
        "Bracket": ["148-BWA_UP / 152-011 / 154-004", "148-BWA_UP", "549-007(T)"],
    })
    source_path = tmp_path / "LAR_AEL metadata.xlsx"
    mapping_path = tmp_path / "mapping.xlsx"
    candidate_path = tmp_path / "candidate.xlsx"
    _write_source(source_path)
    with pd.ExcelWriter(mapping_path) as writer:
        frame.to_excel(writer, sheet_name="AEL UT", index=False)
    standardize_workbook(source_path, mapping_path, candidate_path)
    sheets = pd.read_excel(candidate_path, sheet_name=None)
    assert sheets["LAR_AEL UT"]["Bracket"].dropna().tolist() == [
        "148-BWA_UP@48100m", "152-011", "154-004", "148-BWA_UP@48200m", "549-007(T)",
    ]
    report = validate_workbook(source_path, candidate_path, mapping_path, "LAR_AEL")
    assert not [x for x in report["findings"] if x["severity"] == "error"]
    assert report["provenance"]["component_mismatch_count"] == 0
    assert report["tracks"]["LAR_AEL UT"]["mapping_diagnostics"]["bracket_location_conflict_count"] == 0
    # Stable endpoint suffixes when source rows are reordered.
    rows, _ = _bracket_rows(frame.iloc[::-1].reset_index(drop=True), "AEL UT", "UT", 1000)
    assert {x["Bracket"] for x in rows} == set(sheets["LAR_AEL UT"]["Bracket"].dropna())
    provenance = sheets["__provenance__"]
    idx = provenance.index[provenance["source_sheet"] == "AEL UT"][0]
    components = json.loads(provenance.loc[idx, "components_json"])
    assert len(components) == 3
    components.pop()
    provenance.loc[idx, "components_json"] = json.dumps(components)
    # Missing/altered component metadata is an error even if candidate parity is intact.
    with pd.ExcelWriter(candidate_path) as writer:
        for name, data in sheets.items():
            data.to_excel(writer, sheet_name=name, index=False)
    report = validate_workbook(source_path, candidate_path, mapping_path, "LAR_AEL")
    assert report["status"] == "fail"
    assert report["provenance"]["component_mismatch_count"] == 1
    # Removing a split candidate component is independently caught by parity.
    sheets["LAR_AEL UT"] = sheets["LAR_AEL UT"].query("Bracket != '152-011'")
    with pd.ExcelWriter(candidate_path) as writer:
        for name, data in sheets.items():
            data.to_excel(writer, sheet_name=name, index=False)
    report = validate_workbook(source_path, candidate_path, mapping_path, "LAR_AEL")
    assert report["tracks"]["LAR_AEL UT"]["bracket_diff"]["missing_count"] == 1


def test_empty_and_duplicate_slash_components_are_not_discarded():
    from standardize_tov1050_metadata import _bracket_rows
    frame = pd.DataFrame({"Location": [48.1, 48.2], "Bracket": ["123-01 / / 124-01", "125-01 / 125-01"]})
    rows, provenance = _bracket_rows(frame, "AEL UT", "UT", 1000)
    assert len(rows) == 2
    assert provenance[0]["status"] == "invalid"
    _, invalid, _, diagnostics = _mapping_rows(frame, 1000)
    assert len(invalid) == 1
    assert diagnostics["exact_duplicate_identity_count"] == 1


def test_termination_suffix_collision_fails_closed():
    import pytest
    from standardize_tov1050_metadata import _bracket_rows
    frame = pd.DataFrame({"Location": [48.1, 48.2, 48.3],
                          "Bracket": ["579-BWA", "579-BWA", "579-BWA@48100m"]})
    with pytest.raises(ValueError, match="collides"):
        _bracket_rows(frame, "AEL UT", "UT", 1000)


def test_provenance_target_mismatch_is_reported():
    source_sheets = _source_frames()
    mapping_sheets = {"AEL UT": pd.DataFrame({"Location": [48.1], "Bracket": ["2-045"]})}
    provenance = pd.DataFrame(
        [
            {"source_sheet": "threshold", "source_row": 2, "status": "emitted", "target_sheet": "threshold"},
            {"source_sheet": "threshold", "source_row": 3, "status": "emitted", "target_sheet": "threshold"},
            {"source_sheet": "location type", "source_row": 2, "status": "emitted", "target_sheet": "Exception Boundarys"},
            {"source_sheet": "UT track type", "source_row": 2, "status": "emitted", "target_sheet": "UT"},
            {"source_sheet": "AEL UT", "source_row": 2, "status": "emitted", "target_sheet": "WRONG"},
        ]
    )

    report = _provenance_check(source_sheets, mapping_sheets, {"__provenance__": provenance}, "LAR_AEL")

    assert report["target_mismatch_count"] == 1
    assert report["target_mismatch"] == [{
        "source_sheet": "AEL UT",
        "source_row": 2,
        "expected": "UT",
    }]


def test_tov640_wide_threshold_schema_is_a_valid_canonical_candidate():
    wide = pd.DataFrame(
        [{
            "Class": "Open",
            "Track Type": "Tangent",
            "Exc Type": "Stagger Left",
            "Stagger L1": 300.0,
        }]
    ).reindex(columns=_wide_thresholds(_source_frames()["threshold"]).columns)

    report = _threshold_check(wide, wide)

    assert report["schema_match"] is True
    assert report["rows_match"] is True


def test_candidate_digest_mismatch_is_reported(tmp_path):
    source_path = tmp_path / "LAR_AEL metadata.xlsx"
    mapping_path = tmp_path / "TOV1050 TL-BK No.xlsx"
    candidate_path = tmp_path / "LAR_AEL metadata (wide candidate).xlsx"
    _write_source(source_path)
    _write_mapping(mapping_path)
    standardize_workbook(source_path, mapping_path, candidate_path)

    # Rewriting the source simulates a changed reference workbook after
    # candidate generation; promotion must fail closed on the digest.
    changed = _source_frames()
    changed["threshold"].loc[0, "max"] = 4499
    with pd.ExcelWriter(source_path) as writer:
        for sheet, frame in changed.items():
            frame.to_excel(writer, sheet_name=sheet, index=False)

    report = validate_workbook(source_path, candidate_path, mapping_path, "LAR_AEL")
    assert report["candidate_metadata"]["source_sha256_match"] is False
    assert any(item["code"] == "candidate_metadata_provenance" for item in report["findings"])


def test_support_policy_uses_sorted_anchors_not_untrusted_non_support():
    from tov1050_support_intervals import reconstruct
    frame = pd.DataFrame({
        "track type": ["Support", "non-support", "Support", "Support", "Support"],
        "startKM": [98.671, 98.668, 98.643, 98.661, 98.651],
        "endKM": [98.671, 98.644, 98.643, 98.661, 98.651],
    })
    result = reconstruct(frame, "DT track type")
    assert [(r["from_km"], r["to_km"]) for r in result["derived"]] == [
        ("98.6431", "98.6509"), ("98.6511", "98.6609"), ("98.6611", "98.6709"),
    ]
    assert result["sources"][1]["status"] == "superseded"
    assert result["derived"][0]["anchors"] == [
        {"source_row": 4, "start": 98.643, "end": 98.643},
        {"source_row": 6, "start": 98.651, "end": 98.651},
    ]


def test_support_policy_handles_extended_supports_and_retains_outer_bounds():
    from tov1050_support_intervals import reconstruct
    frame = pd.DataFrame({
        "track type": ["non-support", "Support", "Support", "non-support"],
        "startKM": [98.0, 98.643, 98.651, 98.6531],
        "endKM": [98.6429, 98.645, 98.653, 99.0],
    })
    result = reconstruct(frame, "UT track type")
    assert [(r["from_km"], r["to_km"]) for r in result["derived"]] == [("98.6451", "98.6509")]
    assert [r["source_row"] for r in result["retained_edges"]] == [2, 5]
    assert len(result["intervals"]) == 5


def test_support_policy_reports_bad_anchors_and_does_not_derive_huge_gap():
    from tov1050_support_intervals import reconstruct
    frame = pd.DataFrame({
        "track type": ["Support", "Support", "Support", "Tangent"],
        "startKM": [99.12, 99126, 99.13, 97],
        "endKM": [99.12, 99126, 99.13, 113.5],
    })
    result = reconstruct(frame, "DT track type", bounds=(97, 113.5))
    assert result["issues"][0]["source_row"] == 3
    assert result["issues"][0]["code"] == "invalid_support_anchor"
    assert [(r["from_km"], r["to_km"]) for r in result["derived"]] == [("99.1201", "99.1299")]
    # Source anomaly stays visible; it is never divided by 1000 silently.
    assert result["sources"][1]["output"]["from_m"] == 99126000


def test_support_policy_gap_precision_and_overlap_edges():
    from tov1050_support_intervals import reconstruct
    frame = pd.DataFrame({"track type": ["Support"] * 5,
                          "startKM": [1.0000, 1.0001, 1.0003, 1.0003, 1.00031],
                          "endKM": [1.0000, 1.0001, 1.0003, 1.0003, 1.00031]})
    result = reconstruct(frame, "UT track type")
    assert [(r["from_km"], r["to_km"]) for r in result["derived"]] == [("1.0002", "1.0002")]
    assert {r["code"] for r in result["issues"]} == {"overlapping_support_anchors", "invalid_support_anchor"}
    no_support = reconstruct(pd.DataFrame({"track type": ["non-support"], "startKM": [1.0], "endKM": [2.0]}), "UT track type")
    assert no_support["derived"] == []
    assert no_support["sources"][0]["status"] == "emitted"
    assert no_support["issues"][0]["code"] == "no_valid_support_anchors"


def test_orcr_supports_before_mainline_curve_range_remain_valid():
    from tov1050_support_intervals import reconstruct, location_envelope
    locations = pd.DataFrame({"location type": ["ORCR", "Tunnel"],
                              "startKM": [97, 100.242], "endKM": [100.241, 113.5]})
    frame = pd.DataFrame({"track type": ["Support", "Support", "Curve"],
                          "startKM": [97.781, 97.785, 100.2411], "endKM": [97.781, 97.785, 113.5]})
    result = reconstruct(frame, "DT track type", location_envelope({"location type": locations}))
    assert result["issues"] == []
    assert [(r["from_km"], r["to_km"]) for r in result["derived"]] == [("97.7811", "97.7849")]


def test_support_derivation_candidate_and_anchor_provenance_are_verified(tmp_path):
    source_path, mapping_path, candidate_path = (tmp_path / name for name in ("LAR_AEL metadata.xlsx", "mapping.xlsx", "candidate.xlsx"))
    frames = _source_frames()
    frames["UT track type"] = pd.DataFrame({
        "track type": ["Support", "non-support", "Support"],
        "startKM": [48.1, 48.13, 48.2], "endKM": [48.1, 48.12, 48.2],
    })
    with pd.ExcelWriter(source_path) as writer:
        for name, frame in frames.items():
            frame.to_excel(writer, sheet_name=name, index=False)
    _write_mapping(mapping_path)
    standardize_workbook(source_path, mapping_path, candidate_path)
    report = validate_workbook(source_path, candidate_path, mapping_path, "LAR_AEL")
    assert report["tracks"]["LAR_AEL UT"]["intervals_match"]
    assert report["interval_derivations"]["rows_match"]
    assert not [r for r in report["findings"] if r["severity"] == "error"]
    original = pd.read_excel(candidate_path, sheet_name=None)
    assert original["LAR_AEL UT"].loc[original["LAR_AEL UT"]["Track Type"] == "non-support", "Track Type FromM"].tolist() == [48100.1]
    # An incorrect anchor source row cannot be accepted even with valid output.
    corrupted = {name: frame.copy() for name, frame in original.items()}
    corrupted["__interval_derivation__"].loc[0, "anchors_json"] = '[]'
    with pd.ExcelWriter(candidate_path) as writer:
        for name, frame in corrupted.items():
            frame.to_excel(writer, sheet_name=name, index=False)
    report = validate_workbook(source_path, candidate_path, mapping_path, "LAR_AEL")
    assert not report["interval_derivations"]["rows_match"]
    assert report["status"] == "fail"

    # Original non-support disposition and payload must remain traceable.
    corrupted = {name: frame.copy() for name, frame in original.items()}
    provenance = corrupted["__provenance__"]
    idx = provenance.index[(provenance["source_sheet"] == "UT track type") & (provenance["status"] == "superseded")][0]
    provenance.loc[idx, "interval_payload_json"] = '{}'
    with pd.ExcelWriter(candidate_path) as writer:
        for name, frame in corrupted.items():
            frame.to_excel(writer, sheet_name=name, index=False)
    report = validate_workbook(source_path, candidate_path, mapping_path, "LAR_AEL")
    assert report["provenance"]["interval_mismatch_count"] == 1
    assert report["status"] == "fail"
    # Reversing the derived endpoints must fail, even though min/max is equal.
    corrupted = {name: frame.copy() for name, frame in original.items()}
    track = corrupted["LAR_AEL UT"]
    idx = track.index[track["Track Type"] == "non-support"][0]
    track.loc[idx, ["Track Type FromM", "Track Type ToM"]] = [48199.9, 48100.1]
    with pd.ExcelWriter(candidate_path) as writer:
        for name, frame in corrupted.items():
            frame.to_excel(writer, sheet_name=name, index=False)
    report = validate_workbook(source_path, candidate_path, mapping_path, "LAR_AEL")
    assert not report["tracks"]["LAR_AEL UT"]["intervals_match"]
    assert report["status"] == "fail"


def _review_correction():
    return dict(id="reviewed-ISL-DT", line="ISL", sheet="DT track type", source_row=3,
                label="Support", expected=dict(start=99126, end=99126),
                replacement=dict(start=99.126, end=99.126), authorization="User confirmed 99.126 km")


def test_review_correction_is_scoped_and_rejects_stale_source():
    import pytest
    from copy import deepcopy
    from tov1050_review_corrections import bind_corrections
    from tov1050_support_intervals import reconstruct
    frame = pd.DataFrame({"track type": ["Support"] * 3,
                          "startKM": [99.12, 99126, 99.13], "endKM": [99.12, 99126, 99.13]})
    frames = {"UT track type": frame.copy(), "DT track type": frame.copy()}
    correction = _review_correction()
    assert bind_corrections(frames, "KTL", [correction]) == []
    assert reconstruct(frames["DT track type"], "DT track type")["sources"][1]["output"]["from_m"] == 99126000
    applied = bind_corrections(frames, "ISL", [correction])
    assert applied[0]["application_status"] == "applied"
    assert reconstruct(frames["UT track type"], "UT track type")["sources"][1]["output"]["from_m"] == 99126000
    result = reconstruct(frames["DT track type"], "DT track type", (97, 113.5))
    assert result["sources"][1]["start"] == 99126
    assert result["sources"][1]["output"]["from_m"] == 99126
    assert [(r["from_km"], r["to_km"]) for r in result["derived"]] == [
        ("99.1201", "99.1259"), ("99.1261", "99.1299")]
    assert result["derived"][0]["anchors"][1]["correction"]["original"]["start"] == 99126
    assert frame.loc[1, "startKM"] == 99126  # Raw cells remain untouched.
    for mutation in (dict(source_row=40), dict(sheet="PL track type"), dict(label="non-support")):
        with pytest.raises(ValueError):
            bind_corrections(frames, "ISL", [{**correction, **mutation}])
    frames["DT track type"].loc[1, "startKM"] = 99.127
    with pytest.raises(ValueError, match="Stale"):
        bind_corrections(frames, "ISL", [correction])
    frames["DT track type"].loc[1, ["startKM", "endKM"]] = [99.126, 99.126]
    assert bind_corrections(frames, "ISL", [correction])[0]["application_status"] == "already_applied"
    duplicate = deepcopy(correction)
    duplicate["id"] = "second-id"
    with pytest.raises(ValueError, match="Duplicate"):
        bind_corrections(frames, "ISL", [correction, duplicate])


def test_reviewed_candidate_requires_external_authorization_and_intact_provenance(tmp_path):
    import hashlib
    source, mapping, candidate = (tmp_path / name for name in ("ISL metadata.xlsx", "mapping.xlsx", "candidate.xlsx"))
    frames = _source_frames()
    frames.pop("UT track type")
    frames["location type"] = pd.DataFrame({"location type": ["ORCR"], "startKM": [97], "endKM": [113.5]})
    frames["DT track type"] = pd.DataFrame({"track type": ["Support"] * 3,
                                           "startKM": [99.12, 99126, 99.13], "endKM": [99.12, 99126, 99.13]})
    with pd.ExcelWriter(source) as writer:
        for name, frame in frames.items():
            frame.to_excel(writer, sheet_name=name, index=False)
    _write_mapping(mapping)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    corrections = [_review_correction()]
    standardize_workbook(source, mapping, candidate, corrections=corrections)
    report = validate_workbook(source, candidate, mapping, "ISL", corrections=corrections)
    assert report["status"] == "pass"
    assert report["interval_derivations"]["expected_count"] == 2
    assert report["review_corrections"]["rows_match"]
    assert validate_workbook(source, candidate, mapping, "ISL")["status"] == "fail"
    original = pd.read_excel(candidate, sheet_name=None)
    # Each independent traceability surface must be verified, even with intact intervals.
    for sheet, column, index in (("__review_corrections__", "correction_json", 0),
                                  ("__provenance__", "interval_payload_json", None),
                                  ("__interval_derivation__", "anchors_json", 0),
                                  ("__standardization__", "review_corrections_sha256", 0)):
        corrupted = {name: frame.copy() for name, frame in original.items()}
        if index is None:
            prov = corrupted[sheet]
            index = prov.index[(prov["source_sheet"] == "DT track type") & (prov["source_row"] == 3)][0]
        corrupted[sheet].loc[index, column] = "{}"
        with pd.ExcelWriter(candidate) as writer:
            for name, frame in corrupted.items():
                frame.to_excel(writer, sheet_name=name, index=False)
        assert validate_workbook(source, candidate, mapping, "ISL", corrections=corrections)["status"] == "fail"
    assert hashlib.sha256(source.read_bytes()).hexdigest() == digest


def test_accepted_outer_ranges_require_matching_source_continuity_and_provenance(tmp_path):
    import pytest
    from tov1050_review_corrections import bind_outer_acceptances
    from tov1050_support_intervals import reconstruct
    source, mapping, candidate = (tmp_path / name for name in ("ISL metadata.xlsx", "mapping.xlsx", "candidate.xlsx"))
    frames = _source_frames()
    frames.pop("UT track type")
    frames["location type"] = pd.DataFrame({"location type": ["ORCR"], "startKM": [97], "endKM": [113.5]})
    frame = pd.DataFrame({"track type": ["non-support", "Support", "Support", "non-support"],
                          "startKM": [97, 99.12, 99.13, 99.1301], "endKM": [99.1199, 99.12, 99.13, 100]})
    frames["DT track type"] = frame
    accepted = [dict(id=f"edge-{row}", line="ISL", sheet="DT track type", source_row=row,
                     label="non-support", expected=dict(start=start, end=end), authorization="User accepted continuity")
                for row, start, end in ((2, 97, 99.1199), (5, 99.1301, 100))]
    bind_outer_acceptances(frames, "ISL", accepted)
    result = reconstruct(frame, "DT track type", (97, 113.5))
    assert not result["retained_edges"]
    assert [item["adjacent_support_row"] for item in result["accepted_edges"]] == [3, 4]
    with pd.ExcelWriter(source) as writer:
        for name, data in frames.items():
            data.to_excel(writer, sheet_name=name, index=False)
    _write_mapping(mapping)
    standardize_workbook(source, mapping, candidate, outer_acceptances=accepted)
    report = validate_workbook(source, candidate, mapping, "ISL", outer_acceptances=accepted)
    assert report["status"] == "pass"
    assert len(report["tracks"]["ISL DT"]["support_policy"]["accepted_edges"]) == 2
    assert validate_workbook(source, candidate, mapping, "ISL")["status"] == "fail"
    sheets = pd.read_excel(candidate, sheet_name=None)
    sheets["__review_acceptances__"].loc[0, "record_json"] = '{}'
    with pd.ExcelWriter(candidate) as writer:
        for name, data in sheets.items():
            data.to_excel(writer, sheet_name=name, index=False)
    report = validate_workbook(source, candidate, mapping, "ISL", outer_acceptances=accepted)
    assert report["status"] == "fail"
    assert not report["outer_acceptances"]["rows_match"]
    frame.loc[0, "endKM"] = 99.1198
    with pytest.raises(ValueError, match="Stale outer"):
        bind_outer_acceptances(frames, "ISL", accepted)
    frame.loc[0, "endKM"] = 99.1199
    bind_outer_acceptances(frames, "ISL", accepted)
    # Acceptance of the range does not authorize changed adjacent Support values.
    frame.loc[1, ["startKM", "endKM"]] = [99.121, 99.121]
    with pytest.raises(ValueError, match="no longer connects"):
        reconstruct(frame, "DT track type", (97, 113.5))
