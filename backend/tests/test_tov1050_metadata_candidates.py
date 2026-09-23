from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from standardize_tov1050_metadata import standardize_workbook, _wide_thresholds
from validate_tov1050_metadata_candidates import (
    _interval_report,
    _is_landmark,
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
        "overlap_m": 500.0,
        "previous_length_m": 1000.0,
        "current_length_m": 1000.0,
    }]


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


def test_landmarks_do_not_create_same_location_bracket_conflicts():
    _, _, _, diagnostics = _mapping_rows(
        pd.DataFrame({
            "Location": [48.1, 48.1, 48.2, 48.2, 48.2],
            "Bracket": ["123-01", "SI", "123-02", "CR283-15", "Mid Point"],
        }),
        1000.0,
    )

    assert diagnostics["marker_row_count"] == 2
    assert diagnostics["location_conflict_count"] == 1
    assert diagnostics["location_conflicts"] == [{
        "from_m": 48200.0,
        "brackets": ["123-02", "CR283-15"],
        "source_rows": [4, 5],
    }]


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
