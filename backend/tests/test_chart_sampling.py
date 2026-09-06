import pandas as pd

from app.core.chart_sampling import build_chart_payload


def test_envelope_keeps_isolated_extrema_and_requested_chainage():
    frame = pd.DataFrame(
        {
            "Chainage": list(range(10)),
            "height1": [1, 1, 1, 1, 99, 1, 1, 1, 1, 1],
            "stagger1": [0, 0, -40, 0, 0, 0, 0, 0, 0, 0],
            "wear1": [3] * 10,
        }
    )
    payload, resolution = build_chart_payload(
        frame,
        frame.columns,
        max_points=3,
        preserve_chainage=[8],
    )

    assert resolution["source_points"] == 10
    assert resolution["strategy"] == "min_max_envelope"
    assert 99 in payload["height1"]
    assert -40 in payload["stagger1"]
    assert 8 in payload["Chainage"]


def test_small_frames_remain_raw_for_zoom_detail():
    frame = pd.DataFrame({"Chainage": [100, 101], "height1": [5, 6]})
    payload, resolution = build_chart_payload(frame, frame.columns, max_points=6000, from_m=101, to_m=101)

    assert payload == {"Chainage": [101], "height1": [6]}
    assert resolution["strategy"] == "raw"
