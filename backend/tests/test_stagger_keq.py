import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

PROJECT_ROOT = Path(__file__).resolve().parents[2]

from app.core.calculation.stagger_keq import calculate_eal_keq, calculate_tml_keq
from app.core.calculation.stagger_metadata import (
    RangeValue,
    SupportPoint,
    build_support_index,
    build_tml_threshold_strategy,
    load_stagger_metadata,
    resolve_stagger_workbook_path,
)


def test_build_support_index_groups_by_line_and_track():
    supports = [
        SupportPoint(line="EAL", track="up", chainage=121050.0),
        SupportPoint(line="eal", track="UP", chainage=121000.0),
        SupportPoint(line="TML", track="down", chainage=221000.0),
    ]

    index = build_support_index(supports)

    assert [item.chainage for item in index["EAL"]["up"]] == [121000.0, 121050.0]
    assert [item.chainage for item in index["TML"]["down"]] == [221000.0]


def test_build_tml_threshold_strategy_keeps_threshold_values():
    strategy = build_tml_threshold_strategy(
        boundary=121207.0,
        above=1.5,
        below_or_equal=1.0,
    )

    assert strategy["strategy"] == "threshold"
    assert strategy["boundary"] == 121207.0
    assert strategy["above"] == 1.5
    assert strategy["below_or_equal"] == 1.0


def test_range_value_keeps_numeric_interval_payload():
    item = RangeValue(start=0.0, end=999999.0, value=1.2)

    assert item.start == 0.0
    assert item.end == 999999.0
    assert item.value == 1.2


def test_resolve_stagger_workbook_path_uses_independent_docs_source_by_default():
    path = resolve_stagger_workbook_path(line="EAL")

    assert path.name == "EAL Enhanced stagger calculation (Formula).xlsx"
    assert path.parent.name == "stagger"
    assert path.exists() is True


def test_load_stagger_metadata_from_eal_workbook_builds_support_and_wind_factor_sections():
    workbook_path = Path("docs/stagger/EAL Enhanced stagger calculation (Formula).xlsx")

    metadata = load_stagger_metadata(line="EAL", workbook_path=workbook_path)

    assert metadata["source_path"] == (PROJECT_ROOT / workbook_path).resolve()
    assert metadata["constants"]["tension"] == 13.8
    assert metadata["supports"]["EAL"]["up"]
    assert metadata["supports"]["EAL"]["down"]
    assert metadata["supports"]["EAL"]["up"][0].line == "EAL"
    assert metadata["supports"]["EAL"]["up"][0].track == "up"
    assert metadata["wind_factor"]["EAL"]["kr"]["up"][0] == RangeValue(
        start=100810.0,
        end=101164.9,
        value=0.9,
    )


def test_load_stagger_metadata_from_tml_workbook_builds_threshold_strategy():
    workbook_path = Path("docs/stagger/TML Enhanced stagger calculation (Formula).xlsx")

    metadata = load_stagger_metadata(line="TML", workbook_path=workbook_path)

    assert metadata["source_path"] == (PROJECT_ROOT / workbook_path).resolve()
    assert metadata["constants"]["tension"] == 13.8
    assert metadata["supports"]["TML"]["up"]
    assert metadata["supports"]["TML"]["down"]
    assert metadata["wind_factor"]["TML"] == {
        "strategy": "threshold",
        "boundary": 121207.0,
        "above": 1.5,
        "below_or_equal": 1.0,
    }


def test_load_stagger_metadata_raises_controlled_error_for_unknown_line():
    with pytest.raises(ValueError, match="Unsupported stagger line"):
        load_stagger_metadata(line="LMC")


def test_calculate_eal_keq_uses_track_specific_range_lookup():
    ranges = [RangeValue(start=0.0, end=999999.0, value=1.0)]

    result = calculate_eal_keq(
        track="up",
        spt_a=120900.0,
        spt_i=121020.0,
        spt_b=121120.0,
        kr_by_track={"up": ranges, "down": ranges},
        ke_by_track={"up": ranges, "down": ranges},
        kh_by_track={"up": ranges, "down": ranges},
    )

    assert result["k_ai_max"] == pytest.approx(1.0)
    assert result["k_ib_max"] == pytest.approx(1.0)
    assert result["k_eq"] == pytest.approx(1.0)


def test_calculate_eal_keq_raises_for_missing_support_range():
    ranges = [RangeValue(start=0.0, end=1000.0, value=1.0)]

    with pytest.raises(ValueError, match="No support factor range"):
        calculate_eal_keq(
            track="up",
            spt_a=120900.0,
            spt_i=121020.0,
            spt_b=121120.0,
            kr_by_track={"up": ranges, "down": ranges},
            ke_by_track={"up": ranges, "down": ranges},
            kh_by_track={"up": ranges, "down": ranges},
        )


def test_calculate_tml_keq_uses_threshold_strategy():
    assert (
        calculate_tml_keq(
            chi=121208.0,
            boundary=121207.0,
            above=1.5,
            below_or_equal=1.0,
        )
        == pytest.approx(1.5)
    )


def test_load_stagger_metadata_returns_public_section_types():
    metadata = load_stagger_metadata(
        line="EAL",
        workbook_path=Path("docs/stagger/EAL Enhanced stagger calculation (Formula).xlsx"),
    )

    assert isinstance(metadata["constants"], dict)
    assert isinstance(metadata["supports"], dict)
    assert isinstance(metadata["wind_factor"], dict)
    assert isinstance(metadata["supports"]["EAL"]["up"][0], SupportPoint)
    assert isinstance(metadata["wind_factor"]["EAL"]["kr"]["up"][0], RangeValue)
