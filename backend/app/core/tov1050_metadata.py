"""Metadata adapter for TOV1050 workbooks."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .metadata import MetadataManager
from .tov1050_contract import metadata_track_sheet


CHAINAGE_SCALE_M_PER_KM = 1000.0


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
            missing = sorted(required.difference(frame.columns))
            raise ValueError(f"TOV1050 location type sheet missing columns: {', '.join(missing)}")
        frame = frame.loc[:, ["location type", "startKM", "endKM"]].copy()
        frame["startKM"] = pd.to_numeric(frame["startKM"], errors="coerce")
        frame["endKM"] = pd.to_numeric(frame["endKM"], errors="coerce")
        frame = frame.dropna(subset=["startKM", "endKM"])
        if frame.empty:
            raise ValueError("TOV1050 location type sheet has no valid intervals")
        starts = np.minimum(frame["startKM"], frame["endKM"]) * CHAINAGE_SCALE_M_PER_KM
        ends = np.maximum(frame["startKM"], frame["endKM"]) * CHAINAGE_SCALE_M_PER_KM
        # Overlap is valid at tension/section changeovers.  The detector's
        # interval mapper resolves overlapping matches by shortest interval;
        # validation keeps the source overlap visible for human review.
        frame["Class"] = frame["location type"].astype(str).str.strip()
        frame.index = pd.IntervalIndex.from_arrays(
            starts,
            ends,
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
                "FromM": np.minimum(frame["startKM"], frame["endKM"]) * CHAINAGE_SCALE_M_PER_KM,
                "ToM": np.maximum(frame["startKM"], frame["endKM"]) * CHAINAGE_SCALE_M_PER_KM,
            }
        )

    def get_track_type_intervals(self, line: str, section: str, track: str) -> pd.DataFrame:
        sheet = self._get_direction_sheet(section, track)
        result = self._extract_interval_data(sheet, "startKM", "endKM", ["track type"])
        if not result.empty:
            starts = result.index.left.to_numpy(dtype=float) * CHAINAGE_SCALE_M_PER_KM
            ends = result.index.right.to_numpy(dtype=float) * CHAINAGE_SCALE_M_PER_KM
            result.index = pd.IntervalIndex.from_arrays(starts, ends, closed="both")
        return result.rename(columns={"track type": "Track Type"})

    def get_overlap_intervals(self, line: str, section: str, track: str) -> pd.DataFrame:
        return pd.DataFrame(columns=["Overlap", "Tension Length"])

    def get_landmark_intervals(self, line: str, section: str, track: str) -> pd.DataFrame:
        return pd.DataFrame(columns=["Landmark"])

    def get_all_thresholds(self) -> pd.DataFrame:
        frame = self._load_sheet("threshold").copy()
        aliases = {
            str(column).strip().lower(): column
            for column in frame.columns
        }
        rename = {}
        for canonical, candidates in {
            "Class": ("class", "location type", "location_type"),
            "Track Type": ("track type", "track_type"),
            "Exc Type": ("exc type", "exception type", "exception_type"),
            "min": ("min", "minimum"),
            "max": ("max", "maximum"),
        }.items():
            for candidate in candidates:
                source = aliases.get(candidate)
                if source is not None:
                    rename[source] = canonical
                    break
        frame = frame.rename(columns=rename)
        required = {"Class", "Track Type", "Exc Type"}
        missing = sorted(required.difference(frame.columns))
        if missing:
            raise ValueError(
                "TOV1050 threshold sheet missing canonical columns: "
                + ", ".join(missing)
            )
        frame["Class"] = frame["Class"].astype(str).str.strip()
        frame["Track Type"] = frame["Track Type"].astype(str).str.strip()
        for column in ["min", "max"]:
            if column in frame:
                frame[column] = pd.to_numeric(frame[column], errors="coerce")
        # MetadataEditor writes the detector's normalized wide representation
        # back to the workbook. Preserve it on the next read instead of trying
        # to pivot it as if it were the original long-form TOV1050 sheet.
        wide_columns = {
            column for column in frame.columns
            if any(column.startswith(prefix) for prefix in (
                "Stagger ", "Low Height ", "High Height ", "Wire Wear ",
            )) and column.rsplit(" ", 1)[-1] in {"L1", "L2", "L3"}
            and frame[column].notna().any()
        }
        long_columns = {"min", "max"}.intersection(frame.columns)
        if wide_columns and long_columns:
            raise ValueError(
                "TOV1050 threshold sheet mixes long min/max and canonical wide columns; "
                "standardize the workbook before analysis"
            )
        if wide_columns:
            expected = {
                f"{prefix} L{level}"
                for prefix in ("Stagger", "Low Height", "High Height", "Wire Wear")
                for level in (1, 2, 3)
            }
            frame = frame.copy()
            for column in expected.intersection(frame.columns):
                frame[column] = pd.to_numeric(
                    frame[column].astype(str).str.replace(",", "", regex=False).str.strip(),
                    errors="coerce",
                )
            return frame
        return self._normalize_thresholds(frame)
