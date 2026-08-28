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


def test_metadata_adapter_matches_real_workbook():
    workbook = metadata_workbook_for("AEL", "Mainline", REFERENCE_ROOT / "config")
    manager = TOV1050MetadataManager(workbook)
    boundaries = manager.get_exception_boundaries("AEL", "UT", "Mainline")
    track_types = manager.get_track_type_intervals("AEL", "Mainline", "UT")
    thresholds = manager.get_all_thresholds()
    assert not boundaries.empty
    assert not track_types.empty
    assert {"Class", "Track Type", "Exc Type"}.issubset(thresholds.columns)
