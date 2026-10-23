"""Metadata adapter for TOV1050 workbooks."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .metadata import MetadataManager
from .tov1050_contract import metadata_track_sheet, metadata_workbook_for


CHAINAGE_SCALE_M_PER_KM = 1000.0


class TOV1050MetadataManager(MetadataManager):
    """Expose TOV1050 metadata through the TOV640 detector contract."""

    def _uses_wide_intervals(self) -> bool:
        if not hasattr(self, "_interval_sheet_names"):
            with pd.ExcelFile(self.config_path) as workbook:
                self._interval_sheet_names = set(workbook.sheet_names)
        sheets = self._interval_sheet_names
        if {"Exception Boundarys", "location type"}.issubset(sheets):
            raise ValueError("TOV1050 workbook mixes wide and long boundary sheets")
        return "Exception Boundarys" in sheets

    @staticmethod
    def _wide_context(line: str, section: str, track: str) -> tuple[str, str]:
        # Reuse the public logical line/session contract; workbook labels are
        # different for AEL/TCL and for the TKL TKS session.
        workbook = metadata_workbook_for(line, section, Path("."))
        direction = str(track).strip().upper()
        if direction not in {"UT", "DT"}:
            raise ValueError(f"Unsupported TOV1050 direction: {track}")
        return workbook.name.removesuffix(" metadata.xlsx"), direction

    @staticmethod
    def _wide_intervals(
        frame: pd.DataFrame, sheet: str, start: str, end: str, value: str,
    ) -> pd.DataFrame:
        required = {start, end, value}
        missing = sorted(required.difference(frame.columns))
        if missing:
            raise ValueError(f"TOV1050 {sheet} sheet missing columns: {', '.join(missing)}")
        # A wide direction sheet also contains independent bracket point rows.
        # Ignore those rows, but never silently discard a malformed interval.
        labels = frame[value].astype("string").str.strip()
        active = frame[start].notna() | frame[end].notna() | (
            labels.notna() & ~labels.str.lower().isin(["", "nan", "none"])
        )
        data = frame.loc[active, [start, end, value]].copy()
        for column in (start, end):
            data[column] = pd.to_numeric(
                data[column].astype("string").str.replace(",", "", regex=False).str.strip(),
                errors="coerce",
            )
        data[value] = labels.loc[active]
        invalid = (
            ~np.isfinite(data[start].to_numpy(dtype=float, na_value=np.nan))
            | ~np.isfinite(data[end].to_numpy(dtype=float, na_value=np.nan))
            | (data[start] > data[end]).fillna(True).to_numpy(dtype=bool)
            | data[value].fillna("").str.lower().isin(["", "nan", "none"]).to_numpy()
        )
        if data.empty or invalid.any():
            raise ValueError(f"TOV1050 {sheet} has no valid intervals or contains invalid interval rows")
        data.index = pd.IntervalIndex.from_arrays(
            data[start].to_numpy(dtype=float), data[end].to_numpy(dtype=float), closed="both",
        )
        return data[[value]]

    def _wide_boundaries(self, line: str, track: str, section: str) -> pd.DataFrame:
        identity, direction = self._wide_context(line, section, track)
        frame = self._load_sheet("Exception Boundarys")
        if "Line" not in frame:
            raise ValueError("TOV1050 Exception Boundarys sheet missing columns: Line")
        frame = frame.loc[frame["Line"].astype(str).str.strip().str.upper() == identity.upper()]
        if frame.empty:
            raise ValueError(f"TOV1050 Exception Boundarys has no rows for {identity}")
        prefix = "UP" if direction == "UT" else "DN"
        return self._wide_intervals(
            frame, "Exception Boundarys", f"{prefix} Track FromM", f"{prefix} Track ToM", "Class",
        )

    def _get_direction_sheet(self, section: str, track: str) -> str:
        # DRL Passing Loop uses its dedicated PL sheet; other sessions use UT/DT.
        if str(section).strip().upper() in {"PL", "PASSING LOOP"}:
            return "PL track type"
        return metadata_track_sheet(section, track)

    def get_exception_boundaries(self, line: str, track: str, selected_section: str) -> pd.DataFrame:
        if self._uses_wide_intervals():
            return self._wide_boundaries(line, track, selected_section)
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
        if self._uses_wide_intervals():
            intervals = self._wide_boundaries(line, track, selected_section)
            return pd.DataFrame({
                "Class": intervals["Class"].to_numpy(),
                "FromM": intervals.index.left, "ToM": intervals.index.right,
            })
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
        if self._uses_wide_intervals():
            identity, direction = self._wide_context(line, section, track)
            sheet = f"{identity} {direction}"
            return self._wide_intervals(
                self._load_sheet(sheet), sheet,
                "Track Type FromM", "Track Type ToM", "Track Type",
            )
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
