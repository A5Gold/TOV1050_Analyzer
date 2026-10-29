"""Adjacent-chainage representatives made exclusively from measured samples.

This is a data reduction algorithm, not a noise classifier. Each channel has
its own source identity: a representative row is not a simultaneous raw row.
"""
from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd

from .chainage_aggregation import CHANNELS, SAMPLE_COUNTER_COLUMNS, _IDENTITY_NAMES


ALGORITHM_VERSION = "same_chainage_median_sample_v1"
EVEN_MEDIAN_RULE = "earliest acquired sample matching either central order-statistic value"


def _number(values):
    return pd.to_numeric(values, errors="coerce").to_numpy(dtype=float, na_value=np.nan, copy=True)


class _Reducer:
    def __init__(self, progress=None):
        self.progress = progress
        self.pending = None
        self.previous = None
        self.last_counter = np.nan
        self.pass_id = 0
        self.segment_id = -1
        self.groups = 0
        self.raw_points = 0
        self.context_columns = []
        self.counter_column = None
        self.columns = None

    def _boundaries(self, frame):
        size = len(frame)
        chainage = _number(frame["Chainage"])
        context_change = np.zeros(size, dtype=bool)
        for column in self.context_columns:
            values = frame[column].reset_index(drop=True)
            previous = values.shift()
            same = values.eq(previous) | (values.isna() & previous.isna())
            context_change |= ~same.fillna(False).to_numpy(dtype=bool)
        if self.previous is not None:
            context_change[0] = not all(
                ((pd.isna(frame[c].iloc[0]) and pd.isna(self.previous[c]))
                 or (not pd.isna(frame[c].iloc[0]) and not pd.isna(self.previous[c])
                     and frame[c].iloc[0] == self.previous[c]))
                for c in self.context_columns
            )
        source = _number(frame["source_row_number"])
        source_gap = np.ones(size, dtype=bool)
        source_gap[1:] = (~np.isfinite(source[1:]) | ~np.isfinite(source[:-1])
                          | (source[1:] != source[:-1] + 1))
        if self.previous is not None:
            old_source = self.previous["source_row_number"]
            source_gap[0] = (not np.isfinite(old_source) or not np.isfinite(source[0])
                             or source[0] != old_source + 1)
        counts = (_number(frame[self.counter_column]) if self.counter_column
                  else np.full(size, np.nan))
        counts[~np.isfinite(counts)] = np.nan
        filled = pd.Series(np.r_[self.last_counter, counts]).ffill().to_numpy()
        reset = np.diff(filled) < 0
        invalid = ~np.isfinite(chainage)
        invalid_boundary = invalid.copy()
        invalid_boundary[1:] |= invalid[:-1]
        if self.previous is not None:
            invalid_boundary[0] |= not np.isfinite(self.previous["Chainage"])
        segment_start = source_gap | context_change | reset | invalid_boundary
        if self.previous is None:
            segment_start[0] = True
        pass_ids = self.pass_id + np.cumsum(reset, dtype=np.int64)
        segment_ids = self.segment_id + np.cumsum(segment_start, dtype=np.int64)
        same_chainage = np.zeros(size, dtype=bool)
        same_chainage[1:] = chainage[1:] == chainage[:-1]
        if self.previous is not None:
            same_chainage[0] = chainage[0] == self.previous["Chainage"]
        starts = np.flatnonzero(segment_start | ~same_chainage)
        # A carried pending run always starts the unprocessed portion.
        if not len(starts) or starts[0] != 0:
            starts = np.r_[0, starts]
        return starts, pass_ids, segment_ids, filled[1:]

    def feed(self, chunk, *, final=False):
        if "Chainage" not in chunk:
            raise ValueError("Chainage is required for median sample reduction")
        chunk = chunk.copy(deep=False)
        if "source_row_number" not in chunk:
            chunk = chunk.copy()
            chunk["source_row_number"] = np.arange(self.raw_points + 1, self.raw_points + len(chunk) + 1)
        self.raw_points += len(chunk)
        if self.columns is None:
            self.columns = tuple(chunk.columns)
            self.context_columns = [c for c in chunk if c.lower() in _IDENTITY_NAMES]
            self.counter_column = next((c for c in SAMPLE_COUNTER_COLUMNS if c in chunk), None)
        elif tuple(chunk.columns) != self.columns:
            raise ValueError("Median sample chunks must have the same columns and order")
        frame = (pd.concat([self.pending, chunk], ignore_index=True)
                 if self.pending is not None else chunk.reset_index(drop=True))
        if frame.empty:
            return self._reduce(frame, np.array([], dtype=int), np.array([], dtype=int),
                                np.array([], dtype=int), np.array([], dtype=int))
        starts, passes, segments, filled_counters = self._boundaries(frame)
        stop = len(frame) if final else int(starts[-1])
        process_starts = starts if final else starts[:-1]
        ends = np.r_[process_starts[1:], stop].astype(int) if len(process_starts) else np.array([], dtype=int)
        result = self._reduce(frame, process_starts, ends, passes, segments)
        if stop:
            self.previous = frame.iloc[stop - 1].to_dict()
            self.previous["Chainage"] = _number(frame["Chainage"].iloc[stop - 1:stop])[0]
            self.previous["source_row_number"] = _number(frame["source_row_number"].iloc[stop - 1:stop])[0]
            self.last_counter = filled_counters[stop - 1]
            self.pass_id = int(passes[stop - 1])
            self.segment_id = int(segments[stop - 1])
        self.pending = frame.iloc[stop:].copy() if stop < len(frame) else None
        return result

    def _reduce(self, frame, starts, ends, passes, segments):
        derived = frame.iloc[starts].copy().reset_index(drop=True)
        # These two generic identities would falsely imply all channels came
        # from the first raw row. Use group bounds and per-channel identities.
        derived = derived.drop(columns=["source_row_number", *SAMPLE_COUNTER_COLUMNS], errors="ignore")
        derived["group_id"] = np.arange(self.groups, self.groups + len(starts), dtype=np.int64)
        self.groups += len(starts)
        derived["pass_id"] = passes[starts] if len(starts) else np.array([], dtype=np.int64)
        derived["segment_id"] = segments[starts] if len(starts) else np.array([], dtype=np.int64)
        lengths = ends - starts
        derived["sample_count"] = lengths
        source = _number(frame["source_row_number"])
        derived["source_row_first"] = source[starts]
        derived["source_row_last"] = source[ends - 1]
        counters = (_number(frame[self.counter_column]) if self.counter_column else np.full(len(frame), np.nan))
        counters[~np.isfinite(counters)] = np.nan
        derived["SampleCount_first"] = counters[starts]
        derived["SampleCount_last"] = counters[ends - 1]
        channels = [c for c in CHANNELS if c in frame]
        if self.progress:
            self.progress("reducing_chainage", 0, len(channels), "channels")
        for channel_index, column in enumerate(channels, 1):
            values = _number(frame[column])
            representative = np.full(len(starts), np.nan)
            chosen = np.full(len(starts), -1, dtype=np.int64)
            counts = np.zeros(len(starts), dtype=np.int64)
            for length in np.unique(lengths):
                groups = np.flatnonzero(lengths == length)
                # Limit temporary matrices even for unusually large groups.
                batch_size = max(1, 250_000 // int(length))
                for begin in range(0, len(groups), batch_size):
                    selected_groups = groups[begin:begin + batch_size]
                    positions = starts[selected_groups, None] + np.arange(length)[None, :]
                    original = values[positions]
                    finite = np.isfinite(original)
                    ordered = np.sort(np.where(finite, original, np.inf), axis=1)
                    valid_count = finite.sum(axis=1)
                    counts[selected_groups] = valid_count
                    rows = np.arange(len(selected_groups))
                    lower = ordered[rows, np.maximum(valid_count - 1, 0) // 2]
                    upper = ordered[rows, valid_count // 2]
                    candidates = finite & ((original == lower[:, None]) | (original == upper[:, None]))
                    offset = candidates.argmax(axis=1)
                    populated = valid_count > 0
                    good_groups = selected_groups[populated]
                    chosen[good_groups] = positions[rows[populated], offset[populated]]
                    representative[good_groups] = values[chosen[good_groups]]
            populated = chosen >= 0
            representative_sources = np.full(len(starts), np.nan)
            representative_counters = np.full(len(starts), np.nan)
            representative_sources[populated] = source[chosen[populated]]
            representative_counters[populated] = counters[chosen[populated]]
            derived[column] = representative
            derived[f"{column}_source_row"] = representative_sources
            derived[f"{column}_sample_counter"] = representative_counters
            derived[f"{column}_valid_count"] = counts
            if self.progress:
                self.progress("reducing_chainage", channel_index, len(channels), "channels")
        for kind, prefix in (("height", "height"), ("wear", "wear"), ("stagger", "stg")):
            selected = [c for c in channels if c.startswith(kind)]
            if selected:
                derived[f"{prefix}_min"] = derived[selected].min(axis=1)
                derived[f"{prefix}_max"] = derived[selected].max(axis=1)
        return derived

    def metadata(self):
        return {
            "aggregation": "chainage_median", "algorithm": ALGORITHM_VERSION,
            "aggregation_version": ALGORITHM_VERSION, "raw_points": self.raw_points,
            "grouped_points": self.groups, "grouping_columns": ["Chainage", *self.context_columns],
            "median_even_rule": EVEN_MEDIAN_RULE, "sample_counter_column": self.counter_column,
            "pass_rule": "finite sample counter decrease", "adjacent_runs_only": True,
            "source_row_unit": "source row number or one-based retained row",
            "representative_semantics": "per-channel measured sample; channels may come from different raw rows",
            "noise_filter": None,
        }


def reduce_chainage(frame: pd.DataFrame, *, progress=None):
    """Return adjacent same-chainage per-channel median samples and provenance."""
    reducer = _Reducer(progress)
    result = reducer.feed(frame, final=True)
    return result, reducer.metadata()


def reduce_chainage_chunks(chunks: Iterable[pd.DataFrame], *, progress=None):
    """Reduce chunks while retaining only the last unfinished raw run.

    Context/metadata columns must already be mapped. Chunk boundaries have no
    semantic effect, and the result equals reducing their ordered concatenation.
    """
    reducer = _Reducer(progress)
    parts = []
    last_empty = None
    for chunk in chunks:
        last_empty = chunk.iloc[:0]
        part = reducer.feed(chunk)
        if not part.empty:
            parts.append(part)
    if last_empty is None:
        last_empty = pd.DataFrame({"Chainage": pd.Series(dtype=float)})
    part = reducer.feed(last_empty, final=True)
    if not part.empty:
        parts.append(part)
    result = pd.concat(parts, ignore_index=True) if parts else part
    return result, reducer.metadata()
