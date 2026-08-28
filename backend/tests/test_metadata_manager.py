import os
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.metadata import MetadataManager


def test_get_tension_length_lookup_cleans_thousand_separator_values(tmp_path: Path):
    metadata_path = tmp_path / 'TML metadata.xlsx'
    df = pd.DataFrame([
        {
            'Overlap FromM': '107,330.90',
            'Overlap ToM': '107,430.90',
            'Tension Length': 'K12',
            'Track Type': 'Tangent',
            'Overlap': '',
        }
    ])

    with pd.ExcelWriter(metadata_path, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='TML DN', index=False)

    mgr = MetadataManager(config_path=metadata_path)
    lookup = mgr.get_tension_length_lookup('TML', 'DN', 'Mainline')

    assert len(lookup) == 1
    assert lookup.iloc[0]['tension_length'] == 'K12'
    assert lookup.iloc[0]['from_m'] == 107330.90
    assert lookup.iloc[0]['to_m'] == 107430.90


def test_get_tension_length_source_rows_preserves_composite_row_and_full_interval(
    tmp_path: Path,
):
    metadata_path = tmp_path / 'EAL metadata.xlsx'
    frame = pd.DataFrame([
        {
            'Overlap FromM': 130126.0,
            'Overlap ToM': 130178.9,
            'Tension Length': '70, X32, L02',
            'Track Type': 'Tangent',
            'Overlap': 'Y',
        }
    ])

    with pd.ExcelWriter(metadata_path, engine='openpyxl') as writer:
        frame.to_excel(writer, sheet_name='EAL DN', index=False)

    manager = MetadataManager(config_path=metadata_path)

    source_rows = manager.get_tension_length_source_rows('EAL', 'DN', 'Mainline')
    lookup = manager.get_tension_length_lookup('EAL', 'DN', 'Mainline')

    assert source_rows.to_dict('records') == [
        {
            'from_m': 130126,
            'to_m': 130178.9,
            'tension_length': '70, X32, L02',
        }
    ]
    assert len(lookup) == 3
    assert set(lookup['tension_length']) == {'70', 'X32', 'L02'}
