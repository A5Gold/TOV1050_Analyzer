import os
import sys

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.calculation.stagger_selector import select_stagger_candidates


def test_select_stagger_candidates_without_repeated_uses_exception_summary():
    summary = pd.DataFrame(
        [
            {
                "ID": "A1",
                "Run Date": "2026-05-05",
                "Line": "EAL",
                "Track": "UP",
                "Section": "UNI-TAP",
                "Tension Length": "H01",
                "Level": "L1",
                "Exception Type": "Stagger Left",
                "MaxValue": 132.4,
                "MaxLocation": 121000.0,
            },
            {
                "ID": "A2",
                "Run Date": "2026-05-05",
                "Line": "EAL",
                "Track": "DOWN",
                "Section": "UNI-TAP",
                "Tension Length": "H02",
                "Level": "L3",
                "Exception Type": "Stagger Left",
                "MaxValue": 140.0,
                "MaxLocation": 121010.0,
            },
            {
                "ID": "A3",
                "Run Date": "2026-05-05",
                "Line": "EAL",
                "Track": "Down",
                "Section": "UNI-TAP",
                "Tension Length": "H03",
                "Level": "L2",
                "Exception Type": "Stagger Right",
                "MaxValue": 145.0,
                "MaxLocation": 121020.0,
            },
        ]
    )

    selected = select_stagger_candidates(summary_df=summary, repeated_summary_df=None)

    assert [item.id for item in selected] == ["A1", "A3"]
    assert selected[0].run_date == "2026-05-05"
    assert selected[0].line == "EAL"
    assert selected[0].track == "up"
    assert selected[0].section == "UNI-TAP"
    assert selected[0].tension_length == "H01"
    assert selected[0].level == "L1"
    assert selected[0].exception_type == "Stagger Left"
    assert selected[0].max_value == 132.4
    assert selected[0].max_location == 121000.0
    assert selected[1].track == "down"


def test_select_stagger_candidates_with_repeated_filters_by_id_and_uses_repeated_max_location():
    summary = pd.DataFrame(
        [
            {
                "ID": "1001",
                "Run Date": "2026-05-05",
                "Line": "TML",
                "Track": "DN",
                "Section": "KSL-HUH",
                "Tension Length": "T01",
                "Level": "L2",
                "Exception Type": "Stagger Right",
                "MaxValue": 150.0,
                "MaxLocation": 220000.0,
            },
            {
                "ID": "1002",
                "Run Date": "2026-05-05",
                "Line": "TML",
                "Track": "UP",
                "Section": "KSL-HUH",
                "Tension Length": "T02",
                "Level": "L1",
                "Exception Type": "Stagger Left",
                "MaxValue": 151.0,
                "MaxLocation": 220050.0,
            },
            {
                "ID": "1003",
                "Run Date": "2026-05-05",
                "Line": "TML",
                "Track": "UP",
                "Section": "KSL-HUH",
                "Tension Length": "T03",
                "Level": "L2",
                "Exception Type": "Wire Wear",
                "MaxValue": 152.0,
                "MaxLocation": 220100.0,
            },
        ]
    )
    repeated = pd.DataFrame(
        [
            {"ID": 1001.0, "RUN DATE": "2026-05-06", "MaxLocation": 221207.0},
            {"ID": "1003", "RUN DATE": "2026-05-06", "MaxLocation": 221300.0},
        ]
    )

    selected = select_stagger_candidates(summary_df=summary, repeated_summary_df=repeated)

    assert [item.id for item in selected] == ["1001"]
    assert selected[0].run_date == "2026-05-05"
    assert selected[0].track == "down"
    assert selected[0].max_location == 221207.0
    assert selected[0].max_value == 150.0


def test_select_stagger_candidates_with_repeated_only_keeps_repeated_stagger_ids_without_fallback():
    summary = pd.DataFrame(
        [
            {
                "ID": "2001",
                "Run Date": "2026-05-05",
                "Line": "EAL",
                "Track": "UP",
                "Section": "FOT-TAP",
                "Level": "L1",
                "Exception Type": "Stagger Left",
                "MaxValue": 132.0,
                "MaxLocation": 113498.5,
            },
            {
                "ID": "2002",
                "Run Date": "2026-05-05",
                "Line": "EAL",
                "Track": "UP",
                "Section": "FOT-TAP",
                "Level": "L2",
                "Exception Type": "Stagger Right",
                "MaxValue": 145.0,
                "MaxLocation": 113520.0,
            },
        ]
    )
    repeated = pd.DataFrame(
        [
            {
                "ID": "9999",
                "Run Date": "2026-05-06",
                "Level": "L2",
                "Exception Type": "Stagger Left",
                "MaxLocation": 113499.0,
            },
            {
                "ID": "8888",
                "Run Date": "2026-05-06",
                "Level": "L1",
                "Exception Type": "Wire Wear",
                "MaxLocation": 113530.0,
            },
        ]
    )

    selected = select_stagger_candidates(summary_df=summary, repeated_summary_df=repeated)

    assert selected == []
