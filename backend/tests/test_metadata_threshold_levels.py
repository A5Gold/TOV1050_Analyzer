import pandas as pd

from app.core.metadata import MetadataManager


def _manager(tmp_path):
    workbook = tmp_path / "metadata.xlsx"
    with pd.ExcelWriter(workbook) as writer:
        pd.DataFrame({"placeholder": [1]}).to_excel(writer, sheet_name="threshold", index=False)
    return MetadataManager(workbook)


def test_normalize_thresholds_leaves_wire_wear_l2_blank_when_long_format_has_only_l1(tmp_path):
    mgr = _manager(tmp_path)
    long_df = pd.DataFrame(
        [
            {"Class": "both", "Track Type": "both", "Exc Type": "Wire Wear L1", "min": None, "max": 7.24},
            {"Class": "SCL", "Track Type": "both", "Exc Type": "Wire Wear L1", "min": None, "max": 5.8},
        ]
    )

    normalized = mgr._normalize_thresholds(long_df)

    wire_wear_rows = normalized[normalized["Exc Type"] == "Wire Wear"]
    assert len(wire_wear_rows) == 2

    by_class = wire_wear_rows.set_index("Class")
    assert by_class.loc["both", "Wire Wear L1"] == 7.24
    assert by_class.loc["SCL", "Wire Wear L1"] == 5.8
    if "Wire Wear L2" in wire_wear_rows.columns:
        assert pd.isna(by_class.loc["both", "Wire Wear L2"])
        assert pd.isna(by_class.loc["SCL", "Wire Wear L2"])


def test_normalize_thresholds_preserves_wire_wear_l2_when_long_format_has_l1_and_l2(tmp_path):
    mgr = _manager(tmp_path)
    long_df = pd.DataFrame(
        [
            {"Class": "both", "Track Type": "both", "Exc Type": "Wire Wear L1", "min": None, "max": 7.24},
            {"Class": "both", "Track Type": "both", "Exc Type": "Wire Wear L2", "min": None, "max": 10.2},
            {"Class": "SCL", "Track Type": "both", "Exc Type": "Wire Wear L1", "min": None, "max": 5.8},
            {"Class": "SCL", "Track Type": "both", "Exc Type": "Wire Wear L2", "min": None, "max": 8.16},
        ]
    )

    normalized = mgr._normalize_thresholds(long_df)

    by_class = normalized.set_index("Class")
    assert by_class.loc["both", "Wire Wear L2"] == 10.2
    assert by_class.loc["SCL", "Wire Wear L2"] == 8.16
