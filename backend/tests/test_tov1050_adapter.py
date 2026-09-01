from pathlib import Path

import pandas as pd

from app.core.tov1050_contract import (
    build_output_filename,
    metadata_workbook_for,
    parse_input_filename,
)
from app.core.tov1050_data_ingestion import TOV1050DataLoader
from app.core.tov1050_metadata import TOV1050MetadataManager


REFERENCE_ROOT = Path(__file__).resolve().parents[2] / "docs" / "TOV1050_Migration"


def _write_csv(path: Path, rows: int = 205) -> None:
    columns = [
        "Line", "Km", "HeightWire1 [mm]", "HeightWire2 [mm]", "HeightWire3 [mm]", "HeightWire4 [mm]",
        "StaggerWire1 [mm]", "StaggerWire2 [mm]", "StaggerWire3 [mm]", "StaggerWire4 [mm]",
        "WearWire1 [mm]", "WearWire2 [mm]", "WearWire3 [mm]", "WearWire4 [mm]",
    ]
    values = []
    for i in range(rows):
        measurement = ["1.#IO"] * 12 if i == 101 else [str(4200 + i), "1.#IO", "1.#IO", "1.#IO", "-10", "1.#IO", "1.#IO", "1.#IO", "10", "1.#IO", "1.#IO", "1.#IO"]
        values.append(["GREY LINE", str(48 + i / 10000), *measurement])
    pd.DataFrame(values, columns=columns).to_csv(path, index=False)


def test_loader_trims_io_and_preserves_source_rows(tmp_path):
    path = tmp_path / "20260822_AEL_UT_SHO_AWE.csv"
    _write_csv(path)

    loader = TOV1050DataLoader(chunk_size=17)
    frame = loader.load_data(path)

    assert frame["source_row_number"].iloc[0] == 102
    assert frame["source_row_number"].iloc[-1] == 106
    assert len(frame) == 4
    assert frame["Chainage"].iloc[0] == 48.01
    assert frame["height1"].iloc[0] == 4300
    assert loader.last_cleaning_summary["raw_row_count"] == 205
    assert loader.last_cleaning_summary["trimmed_leading_count"] == 100
    assert loader.last_cleaning_summary["trimmed_trailing_count"] == 100
    assert loader.last_cleaning_summary["io_value_count"] > 0


def test_reference_sample_has_expected_trimmed_rows():
    path = REFERENCE_ROOT / "Raw data" / "AEL" / "20260822_AEL_UT_SHO_AWE.csv"
    loader = TOV1050DataLoader(chunk_size=100)
    frame = loader.load_data(path)
    assert len(frame) == 276
    assert frame["source_row_number"].iloc[0] == 102
    assert frame["source_row_number"].iloc[-1] == 377
    assert frame["height1"].iloc[0] < 5000


def test_filename_and_metadata_mapping():
    parsed = parse_input_filename("20260822_AEL_UT_SHO_AWE.csv")
    assert parsed.line == "AEL"
    assert parsed.station_start == "SHO"
    assert parsed.station_end == "AWE"
    assert build_output_filename("20260822", "AEL", "UT", "Mainline", "SHO", "AWE", "Exception_Report", "xlsx") == "20260822_AEL_UT_MAINLINE_SHO_AWE_Exception_Report.xlsx"
    assert metadata_workbook_for("TCL", "Mainline", REFERENCE_ROOT / "config").name == "LAR_TCL metadata.xlsx"
    assert metadata_workbook_for("TKL", "TKS", REFERENCE_ROOT / "config").name == "TKS metadata.xlsx"


def test_filename_rejects_non_tov1050_line_or_direction():
    import pytest

    with pytest.raises(ValueError, match="Unsupported TOV1050 line"):
        parse_input_filename("20260822_EAL_UT_SHO_AWE.csv")
    with pytest.raises(ValueError, match="Unsupported TOV1050 direction"):
        parse_input_filename("20260822_AEL_UP_SHO_AWE.csv")


def test_metadata_boundaries_fail_closed_for_missing_columns_or_overlap(tmp_path):
    import pytest

    missing_path = tmp_path / "missing.xlsx"
    with pd.ExcelWriter(missing_path) as writer:
        pd.DataFrame({"location type": ["Open"]}).to_excel(writer, sheet_name="location type", index=False)
    with pytest.raises(ValueError, match="missing columns"):
        TOV1050MetadataManager(missing_path).get_exception_boundaries("AEL", "UT", "Mainline")

    overlap_path = tmp_path / "overlap.xlsx"
    with pd.ExcelWriter(overlap_path) as writer:
        pd.DataFrame(
            {
                "location type": ["Open", "Tunnel"],
                "startKM": [0, 10],
                "endKM": [20, 30],
            }
        ).to_excel(writer, sheet_name="location type", index=False)
    with pytest.raises(ValueError, match="intervals overlap"):
        TOV1050MetadataManager(overlap_path).get_exception_boundaries("AEL", "UT", "Mainline")


def test_metadata_adapter_matches_real_workbook():
    workbook = metadata_workbook_for("AEL", "Mainline", REFERENCE_ROOT / "config")
    manager = TOV1050MetadataManager(workbook)
    boundaries = manager.get_exception_boundaries("AEL", "UT", "Mainline")
    track_types = manager.get_track_type_intervals("AEL", "Mainline", "UT")
    thresholds = manager.get_all_thresholds()
    assert not boundaries.empty
    assert not track_types.empty
    assert {"Class", "Track Type", "Exc Type"}.issubset(thresholds.columns)


def test_output_filename_requires_station_range_and_valid_context():
    import pytest

    with pytest.raises(ValueError, match="required"):
        build_output_filename("20260822", "AEL", "UT", "Mainline", "", "AWE", "Report", "xlsx")
    with pytest.raises(ValueError, match="not supported"):
        build_output_filename("20260822", "DRL", "UT", "TKS", "SHO", "AWE", "Report", "xlsx")


def test_metadata_adapter_rejects_mixed_long_and_wide_threshold_schema(tmp_path):
    import pytest

    workbook = tmp_path / "mixed.xlsx"
    with pd.ExcelWriter(workbook) as writer:
        pd.DataFrame(
            {
                "Location Type": ["Open"],
                "Track Type": ["Tangent"],
                "Exc Type": ["Low Height L1"],
                "min": [4000],
                "max": [4500],
                "Low Height L1": [4500],
            }
        ).to_excel(writer, sheet_name="threshold", index=False)

    with pytest.raises(ValueError, match="mixes long min/max"):
        TOV1050MetadataManager(workbook).get_all_thresholds()


def test_metadata_adapter_normalizes_case_and_numeric_commas(tmp_path):
    workbook = tmp_path / "wide.xlsx"
    with pd.ExcelWriter(workbook) as writer:
        pd.DataFrame(
            {
                " class ": [" Open "],
                "track_type": [" Tangent "],
                "exception type": ["Low Height"],
                "Low Height L1": ["4,500"],
                "Low Height L2": ["4,600"],
            }
        ).to_excel(writer, sheet_name="threshold", index=False)

    frame = TOV1050MetadataManager(workbook).get_all_thresholds()
    assert frame.loc[0, "Class"] == "Open"
    assert frame.loc[0, "Track Type"] == "Tangent"
    assert frame.loc[0, "Low Height L1"] == 4500
