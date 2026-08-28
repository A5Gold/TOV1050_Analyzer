"""Metadata adapter for TOV1050 workbooks."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .metadata import MetadataManager
from .tov1050_contract import metadata_track_sheet


class TOV1050MetadataManager(MetadataManager):
    """Expose TOV1050 metadata through the TOV640 detector contract."""

    def _get_direction_sheet(self, section: str, track: str) -> str:
        # DRL Passing Loop uses its dedicated PL sheet; other sessions use UT/DT.
        if str(section).strip().upper() in {"PL", "PASSING LOOP"}:
            return "PL track type"
        return metadata_track_sheet(section, track)

    def get_exception_boundaries(self, line: str, track: str, selected_section: str) -> pd.DataFrame:
        frame = self._load_sheet("location type")
        required = {"location type", "startKM", "endKM"}
        if not required.issubset(frame.columns):
            return pd.DataFrame()
        frame = frame.loc[:, ["location type", "startKM", "endKM"]].copy()
        frame["startKM"] = pd.to_numeric(frame["startKM"], errors="coerce")
        frame["endKM"] = pd.to_numeric(frame["endKM"], errors="coerce")
        frame = frame.dropna(subset=["startKM", "endKM"])
        if frame.empty:
            return pd.DataFrame()
        frame["Class"] = frame["location type"].astype(str).str.strip()
        frame.index = pd.IntervalIndex.from_arrays(
            np.minimum(frame["startKM"], frame["endKM"]),
            np.maximum(frame["startKM"], frame["endKM"]),
            closed="both",
        )
        return frame[["Class"]]

    def get_boundaries_for_plot(self, line: str, track: str, selected_section: str) -> pd.DataFrame:
        frame = self._load_sheet("location type")
        required = {"location type", "startKM", "endKM"}
        if not required.issubset(frame.columns):
            return pd.DataFrame(columns=["Class", "FromM", "ToM"])
        frame = frame.loc[:, ["location type", "startKM", "endKM"]].copy()
        frame["startKM"] = pd.to_numeric(frame["startKM"], errors="coerce")
        frame["endKM"] = pd.to_numeric(frame["endKM"], errors="coerce")
        frame = frame.dropna(subset=["startKM", "endKM"])
        if frame.empty:
            return pd.DataFrame(columns=["Class", "FromM", "ToM"])
        return pd.DataFrame(
            {
                "Class": frame["location type"].astype(str).str.strip(),
                "FromM": np.minimum(frame["startKM"], frame["endKM"]),
                "ToM": np.maximum(frame["startKM"], frame["endKM"]),
            }
        )

    def get_track_type_intervals(self, line: str, section: str, track: str) -> pd.DataFrame:
        sheet = self._get_direction_sheet(section, track)
        result = self._extract_interval_data(sheet, "startKM", "endKM", ["track type"])
        return result.rename(columns={"track type": "Track Type"})

    def get_overlap_intervals(self, line: str, section: str, track: str) -> pd.DataFrame:
        return pd.DataFrame(columns=["Overlap", "Tension Length"])

    def get_landmark_intervals(self, line: str, section: str, track: str) -> pd.DataFrame:
        return pd.DataFrame(columns=["Landmark"])

    def get_all_thresholds(self) -> pd.DataFrame:
        frame = self._load_sheet("threshold").copy()
        frame = frame.rename(columns={"Location Type": "Class", "Track Type": "Track Type"})
        frame["Class"] = frame["Class"].astype(str).str.strip()
        frame["Track Type"] = frame["Track Type"].astype(str).str.strip()
        for column in ["min", "max"]:
            if column in frame:
                frame[column] = pd.to_numeric(frame[column], errors="coerce")
        # MetadataEditor writes the detector's normalized wide representation
        # back to the workbook. Preserve it on the next read instead of trying
        # to pivot it as if it were the original long-form TOV1050 sheet.
        if any(column in frame.columns for column in (
            "Stagger L1", "Low Height L1", "High Height L1", "Wire Wear L1",
        )):
            return frame
        return self._normalize_thresholds(frame)
