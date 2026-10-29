"""Revision-local chart indexes and bounded temporary storage.

Raw chart arrays live in temporary mmap files, never a retained raw DataFrame.
Only requested windows are decoded. Acquisition order is preserved after an
indexed chainage lookup, including repeated passes through the same position.
"""
from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
from tempfile import TemporaryDirectory
import threading
import time

import numpy as np
import pandas as pd


class ChartSource:
    def __init__(self, frame, columns, *, numeric_columns=(), disk=False, ttl=120, lifecycle_lock=None):
        self.lock = threading.RLock()
        self.lifecycle_lock = lifecycle_lock or threading.RLock()
        self.columns = tuple(dict.fromkeys(c for c in columns if c in frame))
        self.arrays = {}
        self.categories = {}
        self.directory = TemporaryDirectory(prefix="tov-chart-") if disk else None
        self.ttl = ttl
        self.last_access = time.monotonic()
        self.timer = None
        self.closed = False
        for offset, column in enumerate(self.columns):
            values = frame[column]
            if column == "Chainage" or column in numeric_columns:
                array = pd.to_numeric(values, errors="coerce").to_numpy(dtype=float, na_value=np.nan)
            elif pd.api.types.is_numeric_dtype(values.dtype):
                array = values.to_numpy(dtype=float, na_value=np.nan)
            elif disk:
                encoded, categories = pd.factorize(values, sort=False)
                array = encoded.astype(np.int32)
                self.categories[column] = categories.to_numpy()
            else:
                array = values.to_numpy(copy=False)
            self.arrays[column] = self._store(str(offset), array)
        chainage = self.arrays.get("Chainage", np.array([], dtype=float))
        finite = np.flatnonzero(np.isfinite(chainage))
        order = np.argsort(chainage[finite], kind="stable")
        self.positions = self._store("positions", finite[order])
        self.sorted_chainage = self._store("chainage_index", chainage[self.positions])
        self.domain = ({"from_m": float(self.sorted_chainage[0]), "to_m": float(self.sorted_chainage[-1])}
                       if len(self.positions) else None)
        if disk:
            self._schedule_expiry()

    def _store(self, name, values):
        if self.directory is None:
            return values
        path = Path(self.directory.name) / f"{name}.npy"
        np.save(path, values, allow_pickle=False)
        return np.load(path, mmap_mode="r", allow_pickle=False)

    def _schedule_expiry(self):
        if self.timer:
            self.timer.cancel()
        self.timer = threading.Timer(self.ttl, self._expire)
        self.timer.daemon = True
        self.timer.start()

    def _expire(self):
        with self.lifecycle_lock, self.lock:
            remaining = self.ttl - (time.monotonic() - self.last_access)
            if remaining > 0 and not self.closed:
                self.timer = threading.Timer(remaining, self._expire)
                self.timer.daemon = True
                self.timer.start()
            else:
                self.close()

    def window(self, from_m=None, to_m=None):
        with self.lock:
            if self.closed:
                raise RuntimeError("Chart source expired")
            self.last_access = time.monotonic()
            lo = 0 if from_m is None else np.searchsorted(self.sorted_chainage, from_m, side="left")
            hi = len(self.positions) if to_m is None else np.searchsorted(self.sorted_chainage, to_m, side="right")
            positions = np.sort(self.positions[lo:hi])
            data = {}
            for column, values in self.arrays.items():
                selected = values[positions]
                if column in self.categories:
                    categories = self.categories[column]
                    decoded = np.empty(len(selected), dtype=object)
                    decoded[:] = None
                    valid = selected >= 0
                    decoded[valid] = categories[selected[valid]]
                    selected = decoded
                data[column] = selected
            return pd.DataFrame(data)

    def close(self):
        with self.lock:
            if self.closed:
                return
            self.closed = True
            if self.timer:
                self.timer.cancel()
            for array in [*self.arrays.values(), self.positions, self.sorted_chainage]:
                mmap = getattr(array, "_mmap", None)
                if mmap is not None:
                    mmap.close()
            self.arrays.clear()
            self.categories.clear()
            if self.directory:
                self.directory.cleanup()


class WindowCache:
    """Small response cache; scope is one immutable snapshot/mode."""
    def __init__(self, max_entries=8, max_bytes=8 * 1024 * 1024):
        self.items = OrderedDict()
        self.bytes = 0
        self.max_entries, self.max_bytes = max_entries, max_bytes

    def get(self, key):
        found = self.items.get(key)
        if found:
            self.items.move_to_end(key)
            return found[0]

    def put(self, key, value):
        payload = value[0]
        # Include Python list slots and scalar object overhead, not only the
        # equivalent packed-double size. Unicode strings may use two bytes.
        size = sum(64 * len(values) + 2 * sum(len(v) for v in values if isinstance(v, str))
                   for values in payload.values())
        if size > self.max_bytes:
            return
        previous = self.items.pop(key, None)
        if previous:
            self.bytes -= previous[1]
        self.items[key] = (value, size)
        self.bytes += size
        while len(self.items) > self.max_entries or self.bytes > self.max_bytes:
            _, (_, removed) = self.items.popitem(last=False)
            self.bytes -= removed
