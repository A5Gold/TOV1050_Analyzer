import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.calculation.stagger_measurements import resolve_measurements


def test_resolve_measurements_uses_nearest_rows_and_channel_maxima():
    chart_rows = [
        {
            "chainage": 120900.0,
            "heights": [5300.0, 5310.0, 5320.0, 5330.0],
            "staggers": [90.0, 91.0, 92.0, 93.0],
        },
        {
            "chainage": 121000.0,
            "heights": [5400.0, 5390.0, 5380.0, 5410.0],
            "staggers": [120.0, 118.0, 122.0, 121.0],
        },
        {
            "chainage": 121120.0,
            "heights": [5500.0, 5490.0, 5480.0, 5470.0],
            "staggers": [80.0, 81.0, 82.0, 83.0],
        },
    ]

    resolved = resolve_measurements(
        chart_rows=chart_rows,
        chi=121005.0,
        spt_a=120901.0,
        spt_b=121100.0,
    )

    assert resolved.hgt_a == 5330.0
    assert resolved.hgt_i == 5410.0
    assert resolved.hgt_b == 5500.0
    assert resolved.stg_a == 93.0
    assert resolved.stg_i == 122.0
    assert resolved.stg_b == 83.0
