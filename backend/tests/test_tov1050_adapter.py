from pathlib import Path

import pandas as pd
import pytest

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
    # TOV1050 Km is normalized to the canonical metre contract at ingestion.
    assert frame["Chainage"].iloc[0] == 48010
    assert frame["source_chainage_km"].iloc[0] == 48.01
    assert frame["height1"].iloc[0] == 4300
    assert loader.last_cleaning_summary["raw_row_count"] == 205
    assert loader.last_cleaning_summary["trimmed_leading_count"] == 100
    assert loader.last_cleaning_summary["trimmed_trailing_count"] == 100
    assert loader.last_cleaning_summary["io_value_count"] > 0


def test_decimal_km_boundary_converts_without_binary_float_underflow(tmp_path):
    path = tmp_path / "20260822_AEL_UT_SHO_AWE.csv"
    _write_csv(path)
    frame = pd.read_csv(path, dtype=str)
    frame.loc[102, "Km"] = "32.431"
    frame.to_csv(path, index=False)

    loaded = TOV1050DataLoader().load_data(path)
    match = loaded.loc[loaded.source_chainage_km == 32.431]

    assert len(match) == 1
    assert match.iloc[0].Chainage == 32431.0


def test_wide_interval_rounds_metres_to_four_decimal_places():
    intervals = TOV1050MetadataManager._wide_intervals(
        pd.DataFrame({
            "FromM": [64522.00000000001, 65000.00016],
            "ToM": [64913.9, 65100],
            "Track": ["Tangent", "Curve"],
        }),
        "test",
        "FromM",
        "ToM",
        "Track",
    )

    assert intervals.index[0].left == 64522.0
    assert intervals.index[0].left <= 64522.0 <= intervals.index[0].right
    assert intervals.index[1].left == 65000.0002


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


def test_metadata_boundaries_fail_closed_for_missing_columns_and_allow_legal_overlap(tmp_path):
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
    boundaries = TOV1050MetadataManager(overlap_path).get_exception_boundaries("AEL", "UT", "Mainline")
    assert len(boundaries) == 2


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


def test_metadata_interval_outputs_use_metres(tmp_path):
    workbook = tmp_path / "units.xlsx"
    with pd.ExcelWriter(workbook) as writer:
        pd.DataFrame(
            {"location type": ["Open"], "startKM": [48.0], "endKM": [49.0]}
        ).to_excel(writer, sheet_name="location type", index=False)
        pd.DataFrame(
            {"track type": ["Tangent"], "startKM": [48.0], "endKM": [49.0]}
        ).to_excel(writer, sheet_name="UT track type", index=False)

    manager = TOV1050MetadataManager(workbook)
    boundaries = manager.get_boundaries_for_plot("AEL", "UT", "Mainline")
    intervals = manager.get_track_type_intervals("AEL", "Mainline", "UT")

    assert boundaries.loc[0, "FromM"] == 48000
    assert boundaries.loc[0, "ToM"] == 49000
    assert intervals.index[0].left == 48000
    assert intervals.index[0].right == 49000


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


def _write_wide_intervals(path, identity="LAR_AEL", defect=None):
    boundaries = pd.DataFrame({
        "Line": [identity], "Class": ["Tunnel"],
        "UP Track FromM": [98150.2], "UP Track ToM": [98200.0],
        "DN Track FromM": [98300.0], "DN Track ToM": [98400.0],
    })
    intervals = pd.DataFrame({
        "Track Type": ["Curve", None],
        "Track Type FromM": [98150.2, None], "Track Type ToM": [98200.0, None],
        "Bracket FromM": [None, 98170.0], "Bracket": [None, "211-1A"],
    })
    if defect == "invalid":
        intervals["Track Type ToM"] = intervals["Track Type ToM"].astype(object)
        intervals.loc[0, "Track Type ToM"] = "bad"
    if defect == "missing":
        intervals = intervals.drop(columns="Track Type ToM")
    with pd.ExcelWriter(path) as writer:
        boundaries.to_excel(writer, sheet_name="Exception Boundarys", index=False)
        intervals.to_excel(writer, sheet_name=f"{identity} UT", index=False)
        if defect == "mixed":
            pd.DataFrame({"location type": ["Open"]}).to_excel(
                writer, sheet_name="location type", index=False,
            )


def test_wide_direction_units_and_sparse_bracket_rows(tmp_path):
    workbook = tmp_path / "wide.xlsx"
    _write_wide_intervals(workbook)
    manager = TOV1050MetadataManager(workbook)
    up = manager.get_exception_boundaries("AEL", "UT", "Mainline")
    down = manager.get_boundaries_for_plot("AEL", "DT", "Mainline")
    tracks = manager.get_track_type_intervals("AEL", "Mainline", "UT")
    assert up.index[0] == pd.Interval(98150.2, 98200, closed="both")
    assert down.loc[0, "FromM"] == 98300
    assert down.loc[0, "ToM"] == 98400
    assert len(tracks) == 1  # Bracket points are not Track Type intervals.
    assert tracks.index[0].left == 98150.2
    assert tracks.iloc[0]["Track Type"] == "Curve"
    with pytest.raises(ValueError, match="no rows for KTL"):
        manager.get_exception_boundaries("KTL", "UT", "Mainline")
    with pytest.raises(ValueError, match="not found"):
        manager.get_track_type_intervals("AEL", "Mainline", "DT")
    with pytest.raises(ValueError, match="direction"):
        manager.get_exception_boundaries("AEL", "UP", "Mainline")


@pytest.mark.parametrize("defect", ["invalid", "missing", "mixed"])
def test_wide_intervals_reject_malformed_or_ambiguous_schema(tmp_path, defect):
    workbook = tmp_path / "invalid.xlsx"
    _write_wide_intervals(workbook, defect=defect)
    with pytest.raises(ValueError):
        TOV1050MetadataManager(workbook).get_track_type_intervals("AEL", "Mainline", "UT")


def test_long_drl_passing_loop_still_uses_kilometres(tmp_path):
    workbook = tmp_path / "DRL metadata.xlsx"
    with pd.ExcelWriter(workbook) as writer:
        pd.DataFrame({"track type": ["Curve"], "startKM": [1.2], "endKM": [1.3]}).to_excel(
            writer, sheet_name="PL track type", index=False,
        )
    intervals = TOV1050MetadataManager(workbook).get_track_type_intervals("DRL", "PL", "UT")
    assert intervals.index[0] == pd.Interval(1200, 1300, closed="both")


@pytest.mark.parametrize(("line", "session", "identity"), [
    ("AEL", "Mainline", "LAR_AEL"), ("TCL", "Mainline", "LAR_TCL"),
    ("ISL", "Mainline", "ISL"), ("KTL", "Mainline", "KTL"),
    ("TKL", "Mainline", "TKL"), ("TKL", "TKS", "TKS"), ("TWL", "Mainline", "TWL"),
])
@pytest.mark.parametrize("track", ["UT", "DT"])
def test_shipped_wide_workbooks_match_runtime_contract(line, session, identity, track):
    config = Path(__file__).resolve().parents[2] / "config"
    workbook = metadata_workbook_for(line, session, config)
    manager = TOV1050MetadataManager(workbook)
    assert manager._uses_wide_intervals()
    boundary = manager.get_exception_boundaries(line, track, session)
    tracks = manager.get_track_type_intervals(line, session, track)
    plot = manager.get_boundaries_for_plot(line, track, session)
    thresholds = manager.get_all_thresholds()
    expected = manager._load_sheet(f"{identity} {track}")["Track Type FromM"].dropna()
    assert not boundary.empty and not tracks.empty and not thresholds.empty
    assert tracks.index.left.min() == pytest.approx(expected.min())
    assert tracks.index.right.max() < 200000  # Never scale metres again.
    assert plot["FromM"].tolist() == boundary.index.left.tolist()
    assert plot["ToM"].tolist() == boundary.index.right.tolist()


def test_four_decimal_rounding_does_not_hide_reversed_endpoints():
    with pytest.raises(ValueError, match="invalid interval"):
        TOV1050MetadataManager._wide_intervals(
            pd.DataFrame({"FromM": [1.00002], "ToM": [1.00001], "Track": ["Curve"]}),
            "test", "FromM", "ToM", "Track",
        )
