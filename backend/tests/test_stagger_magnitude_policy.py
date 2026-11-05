import pandas as pd
import pytest

from app.core.analyzers import ExceptionDetector
from app.core.chart_thresholds import build_threshold_segments
from app.core.metadata import normalize_stagger_thresholds
from app.core.tov1050_metadata import TOV1050MetadataManager


def _one_sided_thresholds():
    return pd.DataFrame([
        {"Class": "Open", "Track Type": "Tangent", "Exc Type": "Stagger Right",
         "Stagger L1": 300, "Stagger L2": 200, "Stagger L3": 100},
    ])


def test_one_sided_wide_thresholds_expand_to_equal_magnitudes_without_mutating_source():
    source = _one_sided_thresholds()
    normalized = normalize_stagger_thresholds(source, source="TWL metadata.xlsx")

    assert source["Exc Type"].tolist() == ["Stagger Right"]
    assert normalized["Exc Type"].tolist() == ["Stagger Left", "Stagger Right"]
    assert normalized["Stagger L1"].tolist() == [300, 300]
    assert normalized["Stagger L2"].tolist() == [200, 200]
    assert normalized["Stagger L3"].tolist() == [100, 100]


def test_signed_legacy_values_share_absolute_magnitude_and_blank_level_stays_blank():
    source = pd.DataFrame([
        {"Class": "Open", "Track Type": "Tangent", "Exc Type": "Stagger Left",
         "Stagger L1": 300, "Stagger L2": None, "Stagger L3": 100},
        {"Class": "Open", "Track Type": "Tangent", "Exc Type": "Stagger Right",
         "Stagger L1": -300, "Stagger L2": None, "Stagger L3": -100},
    ])
    normalized = normalize_stagger_thresholds(source)
    assert normalized["Stagger L1"].tolist() == [300, 300]
    assert normalized["Stagger L3"].tolist() == [100, 100]
    assert normalized["Stagger L2"].isna().all()


@pytest.mark.parametrize("left,right", [(299, 300), (300, 299)])
def test_conflicting_sides_fail_with_context_and_rows(left, right):
    source = pd.DataFrame([
        {"Class": "Open", "Track Type": "Tangent", "Exc Type": "Stagger Left", "Stagger L1": left},
        {"Class": "Open", "Track Type": "Tangent", "Exc Type": "Stagger Right", "Stagger L1": right},
    ])
    with pytest.raises(ValueError, match=r"rows 2 and 3.*Class=Open.*Track Type=Tangent.*Stagger L1"):
        normalize_stagger_thresholds(source, source="fixture.xlsx")


@pytest.mark.parametrize("bad", ["not a number", float("inf")])
def test_invalid_stagger_value_fails_instead_of_becoming_no_detection(bad):
    source = _one_sided_thresholds().astype({"Stagger L1": object})
    source.loc[0, "Stagger L1"] = bad
    with pytest.raises(ValueError, match=r"row 2.*Stagger Right Stagger L1"):
        normalize_stagger_thresholds(source, source="fixture.xlsx")


def test_both_sides_missing_fails_but_partial_level_remains_legal():
    source = _one_sided_thresholds()
    source.loc[0, ["Stagger L1", "Stagger L2", "Stagger L3"]] = None
    with pytest.raises(ValueError, match="no configured levels"):
        normalize_stagger_thresholds(source)


def test_positive_and_negative_channels_are_detected_independently_and_chart_is_signed():
    thresholds = normalize_stagger_thresholds(_one_sided_thresholds())
    frame = pd.DataFrame([
        {"Chainage": 1000.0, "Class": "Open", "Track Type": "Tangent",
         "stagger1": 100.0, "stagger2": -100.0, "source_row_number": 2},
        {"Chainage": 1001.0, "Class": "Open", "Track Type": "Tangent",
         "stagger1": 99.0, "stagger2": -99.0, "source_row_number": 3},
        {"Chainage": 1002.0, "Class": "Open", "Track Type": "Tangent",
         "stagger1": 300.0, "stagger2": -300.0, "source_row_number": 4},
    ])
    left, right = ExceptionDetector(None)._detect_stagger(
        frame.copy(), thresholds, "20261103", "UT", "TWL", "Mainline"
    )
    assert left["maxValue"].tolist() == [100.0, 300.0]
    assert right["maxValue"].tolist() == [-100.0, -300.0]
    assert left["level"].tolist() == ["L3", "L1"]
    assert right["level"].tolist() == ["L3", "L1"]
    assert all("_SL" in value for value in left["id"])
    assert all("_SR" in value for value in right["id"])

    segments = build_threshold_segments(frame, thresholds)
    assert {item["value"] for item in segments if item["metric"] == "stagger"} == {
        -300.0, -200.0, -100.0, 100.0, 200.0, 300.0,
    }


def test_tov1050_wide_loader_expands_legacy_single_side_without_editing_workbook(tmp_path):
    path = tmp_path / "TWL metadata.xlsx"
    with pd.ExcelWriter(path) as writer:
        _one_sided_thresholds().to_excel(writer, sheet_name="threshold", index=False)
    before = path.read_bytes()
    normalized = TOV1050MetadataManager(path).get_all_thresholds()
    assert normalized["Exc Type"].tolist() == ["Stagger Left", "Stagger Right"]
    assert path.read_bytes() == before


def test_long_generic_stagger_levels_still_apply_to_both_sides(tmp_path):
    path = tmp_path / "DRL metadata.xlsx"
    with pd.ExcelWriter(path) as writer:
        pd.DataFrame([
            {"Class": "Open", "Track Type": "Tangent", "Exc Type": "Stagger L1", "min": 300},
            {"Class": "Open", "Track Type": "Tangent", "Exc Type": "Stagger L3", "min": 100},
        ]).to_excel(writer, sheet_name="threshold", index=False)
    normalized = TOV1050MetadataManager(path).get_all_thresholds()
    assert normalized["Exc Type"].tolist() == ["Stagger Left", "Stagger Right"]
    assert normalized["Stagger L1"].tolist() == [300, 300]
    assert normalized["Stagger L3"].tolist() == [100, 100]
    assert "Stagger L2" not in normalized or normalized["Stagger L2"].isna().all()


@pytest.mark.parametrize("bad", ["not a number", float("inf")])
def test_long_generic_stagger_rejects_invalid_min_before_numeric_coercion(tmp_path, bad):
    path = tmp_path / "DRL metadata.xlsx"
    with pd.ExcelWriter(path) as writer:
        pd.DataFrame([
            {"Class": "Open", "Track Type": "Tangent", "Exc Type": "Stagger L1", "min": bad},
            {"Class": "Open", "Track Type": "Tangent", "Exc Type": "Stagger L3", "min": 100},
        ]).to_excel(writer, sheet_name="threshold", index=False)
    with pytest.raises(ValueError, match=r"row 2.*Stagger L1 min.*Class=Open.*Track Type=Tangent"):
        TOV1050MetadataManager(path).get_all_thresholds()


def test_conflicting_duplicate_long_levels_cannot_be_overwritten_by_pivot(tmp_path):
    from app.core.metadata import MetadataManager
    path = tmp_path / "DRL metadata.xlsx"
    path.touch()
    manager = MetadataManager(path)
    source = pd.DataFrame([
        {"Class": "Open", "Track Type": "Tangent", "Exc Type": "Stagger L1", "min": 300},
        {"Class": "Open", "Track Type": "Tangent", "Exc Type": "Stagger L1", "min": 301},
    ])
    with pytest.raises(ValueError, match=r"conflicting Stagger magnitude.*Class=Open.*Stagger L1"):
        manager._normalize_thresholds(source)
