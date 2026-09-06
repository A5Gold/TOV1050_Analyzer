"""Streaming CSV adapter for TOV1050 measurements."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, Iterator, Optional

import numpy as np
import pandas as pd


RAW_TO_CANONICAL = {
    "HeightWire1 [mm]": "height1",
    "HeightWire2 [mm]": "height2",
    "HeightWire3 [mm]": "height3",
    "HeightWire4 [mm]": "height4",
    "StaggerWire1 [mm]": "stagger1",
    "StaggerWire2 [mm]": "stagger2",
    "StaggerWire3 [mm]": "stagger3",
    "StaggerWire4 [mm]": "stagger4",
    "WearWire1 [mm]": "wear1",
    "WearWire2 [mm]": "wear2",
    "WearWire3 [mm]": "wear3",
    "WearWire4 [mm]": "wear4",
    "Line": "Line",
    "Km": "Chainage",
}

MEASUREMENT_COLUMNS = [
    "height1", "height2", "height3", "height4",
    "stagger1", "stagger2", "stagger3", "stagger4",
    "wear1", "wear2", "wear3", "wear4",
]
CHAINAGE_SCALE_M_PER_KM = 1000.0


class TOV1050DataLoader:
    """Load a TOV1050 CSV without applying TOV640 coordinate corrections."""

    def __init__(self, chunk_size: int = 50_000):
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        self.chunk_size = chunk_size
        self.last_cleaning_summary: Dict[str, Any] = {}

    @staticmethod
    def _detect_delimiter(path: Path) -> str:
        with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
            sample = handle.read(8192)
        try:
            return csv.Sniffer().sniff(sample, delimiters=",;\t").delimiter
        except csv.Error:
            return ","

    @staticmethod
    def _raw_row_count(path: Path) -> int:
        with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
            return max(sum(1 for _ in handle) - 1, 0)

    @staticmethod
    def _clean_headers(columns: Iterator[Any]) -> list[str]:
        return [str(column).strip() for column in columns]

    def _validate_headers(self, columns: list[str]) -> None:
        required = {"Line", "Km", *RAW_TO_CANONICAL.keys()}
        missing = sorted(required.difference(columns))
        if missing:
            raise ValueError(f"TOV1050 CSV missing required columns: {', '.join(missing)}")

    def load_data(self, file_path: str | Path) -> pd.DataFrame:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Data file not found: {path}")

        delimiter = self._detect_delimiter(path)
        raw_rows = self._raw_row_count(path)
        leading = min(100, raw_rows)
        trailing = min(100, max(raw_rows - leading, 0))
        retained_start = leading
        retained_end = raw_rows - trailing

        header = pd.read_csv(
            path, sep=delimiter, nrows=0, dtype=str, keep_default_na=False,
            encoding="utf-8-sig",
        )
        headers = self._clean_headers(header.columns)
        self._validate_headers(headers)

        parts: list[pd.DataFrame] = []
        io_count = 0
        invalid_chainage_count = 0
        no_valid_measurement_count = 0
        rows_read = 0

        reader = pd.read_csv(
            path,
            sep=delimiter,
            dtype=str,
            keep_default_na=False,
            na_filter=False,
            encoding="utf-8-sig",
            chunksize=self.chunk_size,
        )
        for chunk in reader:
            chunk.columns = headers
            chunk_size = len(chunk)
            source_rows = np.arange(rows_read + 2, rows_read + chunk_size + 2, dtype=np.int64)
            rows_read += chunk_size
            io_count += int((chunk == "1.#IO").to_numpy().sum())
            chunk = chunk.mask(chunk.eq("1.#IO"), np.nan)
            chunk["source_row_number"] = source_rows

            keep_start = max(retained_start - (rows_read - chunk_size), 0)
            keep_end = min(retained_end - (rows_read - chunk_size), chunk_size)
            if keep_start >= keep_end:
                continue
            chunk = chunk.iloc[keep_start:keep_end].copy()
            source_chainage_km = pd.to_numeric(chunk["Km"], errors="coerce")
            chunk = chunk.rename(columns=RAW_TO_CANONICAL)
            chunk["source_chainage_km"] = source_chainage_km.to_numpy()
            for column in ["Chainage", *MEASUREMENT_COLUMNS]:
                chunk[column] = pd.to_numeric(chunk[column], errors="coerce")
            # TOV1050 files expose Km; the detector/export contract is metres.
            chunk["Chainage"] = chunk["Chainage"] * CHAINAGE_SCALE_M_PER_KM
            invalid_chainage_count += int(chunk["Chainage"].isna().sum())
            chunk = chunk.dropna(subset=["Chainage"])
            valid_measurement = chunk[MEASUREMENT_COLUMNS].notna().any(axis=1)
            no_valid_measurement_count += int((~valid_measurement).sum())
            chunk = chunk.loc[valid_measurement]
            if not chunk.empty:
                parts.append(chunk)

        if parts:
            result = pd.concat(parts, ignore_index=True, copy=False)
        else:
            result = pd.DataFrame(columns=["source_row_number", *RAW_TO_CANONICAL.values(), *MEASUREMENT_COLUMNS])

        self.last_cleaning_summary = {
            "raw_row_count": raw_rows,
            "retained_row_count": int(len(result)),
            "trimmed_leading_count": leading,
            "trimmed_trailing_count": trailing,
            "io_value_count": io_count,
            "invalid_chainage_count": invalid_chainage_count,
            "no_valid_measurement_count": no_valid_measurement_count,
            "delimiter": delimiter,
            "chunk_size": self.chunk_size,
            "chainage_unit": "m",
            "chainage_scale": CHAINAGE_SCALE_M_PER_KM,
        }
        if result.empty:
            raise ValueError("TOV1050 CSV has no valid measurement rows after cleaning")
        return result
