"""Pure chainage alignment calculations for History Compare.

The helper works on column-oriented ChartData dictionaries and never mutates
the input.  Values are matched on normalized 0.25 m integer ticks; no
interpolation or gap filling is performed.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Mapping, Optional, Tuple

import numpy as np


METRICS: Tuple[str, ...] = ("height", "stagger", "wear")
CHANNELS: Tuple[int, ...] = (1, 2, 3, 4)
STEP_M = 0.25
EPSILON = 1e-12
MIN_VALID_POINTS = 100
MIN_SPAN_M = 25.0
MIN_COVERAGE_RATIO = 0.8
MAX_DENSE_TICKS = 640_000
SPARSE_WORK_BUDGET = 25_000_000
DISPLAY_POINT_CAP = 8_000


def _finite(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _tick(value: Any) -> Optional[int]:
    number = _finite(value)
    if number is None:
        return None
    return int(round(number / STEP_M))


def _column(chart: Mapping[str, Any], name: str) -> List[Any]:
    value = chart.get(name, [])
    return list(value) if isinstance(value, (list, tuple, np.ndarray)) else []


def _normalized_metric(chart: Mapping[str, Any], metric: str) -> Dict[int, np.ndarray]:
    """Return deterministic tick -> channel values, averaging duplicate ticks."""
    chainage = _column(chart, "Chainage")
    sums: Dict[int, np.ndarray] = {}
    counts: Dict[int, np.ndarray] = {}
    channels = [_column(chart, f"{metric}{channel}") for channel in CHANNELS]
    for index, raw_chainage in enumerate(chainage):
        tick = _tick(raw_chainage)
        if tick is None:
            continue
        if tick not in sums:
            sums[tick] = np.zeros(4, dtype=float)
            counts[tick] = np.zeros(4, dtype=float)
        for channel_index, values in enumerate(channels):
            if index >= len(values):
                continue
            value = _finite(values[index])
            if value is not None:
                sums[tick][channel_index] += value
                counts[tick][channel_index] += 1
    result: Dict[int, np.ndarray] = {}
    for tick, total in sums.items():
        values = np.full(4, np.nan, dtype=float)
        np.divide(total, counts[tick], out=values, where=counts[tick] > 0)
        result[tick] = values
    return result


def prepare_chart(chart: Mapping[str, Any]) -> Dict[str, Dict[int, np.ndarray]]:
    """Create the compact normalized representation once for reuse."""
    return {metric: _normalized_metric(chart, metric) for metric in METRICS}


def _metric_scale(*maps: Mapping[int, np.ndarray]) -> float:
    values: List[float] = []
    for mapping in maps:
        for row in mapping.values():
            values.extend(float(value) for value in row if math.isfinite(float(value)))
    if not values:
        return 1.0
    p5, p95 = np.percentile(np.asarray(values, dtype=float), [5, 95])
    return max(float(p95 - p5), EPSILON)


def _dense_maps(
    latest: Mapping[int, np.ndarray], previous: Mapping[int, np.ndarray]
) -> Tuple[np.ndarray, np.ndarray, int]:
    ticks = list(latest.keys()) + list(previous.keys())
    if not ticks:
        return np.empty((4, 0)), np.empty((4, 0)), 0
    start, end = min(ticks), max(ticks)
    length = end - start + 1
    latest_dense = np.full((4, length), np.nan, dtype=float)
    previous_dense = np.full((4, length), np.nan, dtype=float)
    for tick, values in latest.items():
        latest_dense[:, tick - start] = values
    for tick, values in previous.items():
        previous_dense[:, tick - start] = values
    return latest_dense, previous_dense, start


def _candidate(
    latest: np.ndarray,
    previous: np.ndarray,
    shift_ticks: int,
    scale: float,
) -> Dict[str, Any]:
    length = latest.shape[1]
    if abs(shift_ticks) >= length:
        return {"shift_ticks": shift_ticks, "valid_points": 0, "span_m": 0.0}
    if shift_ticks >= 0:
        latest_view = latest[:, shift_ticks:]
        previous_view = previous[:, : length - shift_ticks]
    else:
        latest_view = latest[:, : length + shift_ticks]
        previous_view = previous[:, -shift_ticks:]

    valid = np.isfinite(latest_view) & np.isfinite(previous_view)
    channel_counts = valid.sum(axis=1).astype(int)
    total_points = int(channel_counts.sum())
    positions = np.flatnonzero(valid.any(axis=0))
    span_m = float((positions[-1] - positions[0]) * STEP_M) if positions.size else 0.0
    channel_rmse = np.zeros(4, dtype=float)
    for channel_index in range(4):
        if channel_counts[channel_index]:
            errors = latest_view[channel_index, valid[channel_index]] - previous_view[channel_index, valid[channel_index]]
            channel_rmse[channel_index] = math.sqrt(float(np.mean(errors * errors)))
    weighted_rmse = float(np.dot(channel_rmse, channel_counts) / total_points) if total_points else math.inf
    return {
        "shift_ticks": shift_ticks,
        "valid_points": total_points,
        "channel_counts": channel_counts.tolist(),
        "span_m": span_m,
        "rmse": weighted_rmse,
        "normalized_rmse": weighted_rmse / scale if math.isfinite(weighted_rmse) else math.inf,
    }


def _fft_cross_correlation(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    """Return linear cross-correlation indexed by signed lag modulo its length."""
    linear_length = left.size + right.size - 1
    fft_length = 1 << (linear_length - 1).bit_length()
    correlation = np.fft.irfft(
        np.fft.rfft(left, fft_length) * np.conj(np.fft.rfft(right, fft_length)),
        fft_length,
    )
    return correlation


def _dense_candidates(
    latest: np.ndarray,
    previous: np.ndarray,
    shifts: range,
    scale: float,
) -> List[Dict[str, Any]]:
    """Score all bounded shifts with FFT correlations and direct span checks."""
    length = latest.shape[1]
    channel_counts = np.zeros((4, len(shifts)), dtype=np.int64)
    squared_errors = np.zeros((4, len(shifts)), dtype=float)
    signed_shifts = np.asarray(list(shifts), dtype=int)
    # FFT output is circular; map negative lags to the tail of the spectrum.
    # Out-of-range shifts are skipped below, but clipped here so very short
    # arrays cannot trigger an indexing error before that guard runs.
    correlation_indices = np.where(signed_shifts >= 0, signed_shifts, 0)
    negative_indices = signed_shifts < 0

    for channel_index in range(4):
        left = latest[channel_index]
        right = previous[channel_index]
        left_mask = np.isfinite(left).astype(float)
        right_mask = np.isfinite(right).astype(float)
        left_values = np.nan_to_num(left, nan=0.0, posinf=0.0, neginf=0.0)
        right_values = np.nan_to_num(right, nan=0.0, posinf=0.0, neginf=0.0)

        correlations = (
            _fft_cross_correlation(left_mask, right_mask),
            _fft_cross_correlation(left_values * left_values, right_mask),
            _fft_cross_correlation(left_mask, right_values * right_values),
            _fft_cross_correlation(left_values, right_values),
        )
        correlation_indices[negative_indices] = correlations[0].size + signed_shifts[negative_indices]
        correlation_indices = np.clip(correlation_indices, 0, correlations[0].size - 1)
        counts, left_squares, right_squares, products = (
            values[correlation_indices] for values in correlations
        )
        channel_counts[channel_index] = np.rint(counts).astype(np.int64)
        squared_errors[channel_index] = np.maximum(
            left_squares + right_squares - 2.0 * products,
            0.0,
        )

    candidates: List[Dict[str, Any]] = []
    for shift_index, shift_ticks in enumerate(shifts):
        counts = channel_counts[:, shift_index]
        total_points = int(counts.sum())
        if abs(shift_ticks) >= length:
            candidates.append({"shift_ticks": shift_ticks, "valid_points": 0, "span_m": 0.0})
            continue
        if shift_ticks >= 0:
            valid = np.isfinite(latest[:, shift_ticks:]) & np.isfinite(previous[:, : length - shift_ticks])
        else:
            valid = np.isfinite(latest[:, : length + shift_ticks]) & np.isfinite(previous[:, -shift_ticks:])
        positions = np.flatnonzero(valid.any(axis=0))
        span_m = float((positions[-1] - positions[0]) * STEP_M) if positions.size else 0.0
        channel_rmse = np.sqrt(
            np.divide(
                squared_errors[:, shift_index],
                counts,
                out=np.zeros(4, dtype=float),
                where=counts > 0,
            )
        )
        weighted_rmse = float(np.dot(channel_rmse, counts) / total_points) if total_points else math.inf
        candidates.append({
            "shift_ticks": shift_ticks,
            "valid_points": total_points,
            "channel_counts": counts.tolist(),
            "span_m": span_m,
            "rmse": weighted_rmse,
            "normalized_rmse": weighted_rmse / scale if math.isfinite(weighted_rmse) else math.inf,
        })
    return candidates


def _unavailable(reason: str) -> Dict[str, Any]:
    return {
        "status": "unavailable",
        "reason": reason,
        "shift_m": None,
        "rmse": None,
        "normalized_rmse": None,
        "overlap_from": None,
        "overlap_to": None,
        "overlap_length": None,
        "valid_points": 0,
        "chainage": [],
        "latest": [[], [], [], []],
        "previous": [[], [], [], []],
        "difference": [[], [], [], []],
        "source_points": 0,
        "display_points": 0,
        "downsampled": False,
    }


def _has_finite_values(mapping: Mapping[int, np.ndarray]) -> bool:
    return any(np.isfinite(values).any() for values in mapping.values())


def _raw_unshifted_result(
    latest: Mapping[int, np.ndarray], previous: Mapping[int, np.ndarray], reason: str,
) -> Dict[str, Any]:
    """Preserve raw metric values when a trustworthy shift cannot be selected."""
    result = _unavailable(reason)
    output_ticks = sorted(set(latest) | set(previous))
    result["chainage"] = [tick * STEP_M for tick in output_ticks]
    for index, tick in enumerate(output_ticks):
        latest_row = latest.get(tick)
        previous_row = previous.get(tick)
        for channel_index in range(4):
            if latest_row is not None and math.isfinite(float(latest_row[channel_index])):
                result["latest"][channel_index].append(float(latest_row[channel_index]))
            else:
                result["latest"][channel_index].append(None)
            if previous_row is not None and math.isfinite(float(previous_row[channel_index])):
                result["previous"][channel_index].append(float(previous_row[channel_index]))
            else:
                result["previous"][channel_index].append(None)
            result["difference"][channel_index].append(None)
    _add_display_metadata(result)
    return result


def _downsample_indices(result: Mapping[str, Any], cap: int = DISPLAY_POINT_CAP) -> List[int]:
    chainage = list(result.get("chainage") or [])
    if len(chainage) <= cap:
        return list(range(len(chainage)))

    def evenly_select(indices: List[int], count: int) -> List[int]:
        if count <= 0:
            return []
        if len(indices) <= count:
            return indices
        positions = np.linspace(0, len(indices) - 1, count)
        return [indices[int(round(position))] for position in positions]

    # Anchors have absolute priority. Gap boundaries are selected before any
    # extrema and use deterministic chainage spacing if they exhaust budget.
    selected = {0, len(chainage) - 1}
    latest = result.get("latest") or []
    previous = result.get("previous") or []
    difference = result.get("difference") or []
    finite_series = [list(values) for values in (*latest, *previous, *difference) if values]
    gap_candidates = set()
    for values in finite_series:
        for index in range(1, min(len(values), len(chainage))):
            if (values[index - 1] is None) != (values[index] is None):
                gap_candidates.update((index - 1, index))
    gap_candidates.difference_update(selected)
    remaining = cap - len(selected)
    ordered_gaps = sorted(gap_candidates)
    if len(ordered_gaps) >= remaining:
        selected.update(evenly_select(ordered_gaps, remaining))
        return sorted(selected)
    selected.update(ordered_gaps)

    # Each series nominates its finite min and max in every contiguous bucket.
    # Nominations share a robust-scale score so all returned units compete
    # deterministically without one plot receiving a separate index set.
    normalized_series = []
    for values in finite_series:
        numeric = np.asarray([
            float(value) if value is not None and math.isfinite(float(value)) else np.nan
            for value in values
        ])
        finite = numeric[np.isfinite(numeric)]
        if finite.size:
            scale = max(float(np.percentile(finite, 95) - np.percentile(finite, 5)), EPSILON)
            center = float(np.median(finite))
            normalized_series.append((numeric, np.abs(numeric - center) / scale))

    remaining = cap - len(selected)
    nominations_per_bucket = max(1, 2 * len(normalized_series))
    bucket_count = max(1, math.ceil(remaining / nominations_per_bucket))
    base_quota, extra = divmod(remaining, bucket_count)
    for bucket in range(bucket_count):
        start = int(bucket * len(chainage) / bucket_count)
        end = max(start + 1, int((bucket + 1) * len(chainage) / bucket_count))
        nominations: Dict[int, float] = {}
        for numeric, scores in normalized_series:
            segment = numeric[start:end]
            finite_positions = np.flatnonzero(np.isfinite(segment))
            if not finite_positions.size:
                continue
            finite_values = segment[finite_positions]
            for relative in (
                int(finite_positions[int(np.argmin(finite_values))]),
                int(finite_positions[int(np.argmax(finite_values))]),
            ):
                index = start + relative
                nominations[index] = max(nominations.get(index, -math.inf), float(scores[index]))
        quota = base_quota + (1 if bucket < extra else 0)
        ranked = sorted(nominations, key=lambda index: (-nominations[index], index))
        for index in ranked:
            if index not in selected:
                selected.add(index)
                quota -= 1
                if quota == 0:
                    break

    # Duplicate nominations can leave budget. Fill it with deterministic
    # chainage spacing while preserving every higher-priority selection.
    if len(selected) < cap:
        available = [index for index in range(len(chainage)) if index not in selected]
        selected.update(evenly_select(available, cap - len(selected)))
    return sorted(selected)


def _add_display_metadata(result: Dict[str, Any]) -> Dict[str, Any]:
    source_points = len(result.get("chainage") or [])
    result["source_points"] = source_points
    if source_points <= DISPLAY_POINT_CAP:
        result["display_points"] = source_points
        result["downsampled"] = False
        return result
    indices = _downsample_indices(result)
    for key in ("chainage", "latest", "previous", "difference"):
        values = result.get(key)
        if key == "chainage":
            result[key] = [values[i] for i in indices]
        elif isinstance(values, list):
            result[key] = [[series[i] for i in indices] for series in values]
    result["display_points"] = len(indices)
    result["downsampled"] = True
    return result


def _sparse_candidate(latest: Mapping[int, np.ndarray], previous: Mapping[int, np.ndarray], shift_ticks: int, scale: float) -> Dict[str, Any]:
    paired = []
    channel_counts = np.zeros(4, dtype=int)
    errors: List[List[float]] = [[] for _ in CHANNELS]
    for tick, latest_values in latest.items():
        previous_values = previous.get(tick - shift_ticks)
        if previous_values is None:
            continue
        paired.append(tick)
        for channel_index in range(4):
            left, right = latest_values[channel_index], previous_values[channel_index]
            if math.isfinite(float(left)) and math.isfinite(float(right)):
                channel_counts[channel_index] += 1
                errors[channel_index].append(float(left - right))
    total = int(channel_counts.sum())
    span_m = float((max(paired) - min(paired)) * STEP_M) if paired else 0.0
    rmses = [math.sqrt(float(np.mean(np.square(values)))) if values else 0.0 for values in errors]
    rmse = float(np.dot(rmses, channel_counts) / total) if total else math.inf
    return {"shift_ticks": shift_ticks, "valid_points": total, "channel_counts": channel_counts.tolist(), "span_m": span_m, "rmse": rmse, "normalized_rmse": rmse / scale if math.isfinite(rmse) else math.inf}


def _align_metric(
    latest_chart: Mapping[str, Any], previous_chart: Mapping[str, Any], metric: str,
    *, max_shift_m: float, step_m: float, latest_map_override: Optional[Mapping[int, np.ndarray]] = None,
) -> Dict[str, Any]:
    if step_m != STEP_M:
        return _unavailable("ChartData alignment requires a 0.25 m sample step.")
    latest_map = dict(latest_map_override) if latest_map_override is not None else _normalized_metric(latest_chart, metric)
    previous_map = _normalized_metric(previous_chart, metric)
    if not _has_finite_values(latest_map) or not _has_finite_values(previous_map):
        return _unavailable(f"No usable {metric} ChartData values were found.")
    max_ticks = int(round(max_shift_m / STEP_M))
    if latest_map:
        latest_min, latest_max = min(latest_map), max(latest_map)
        previous_map = {
            tick: values for tick, values in previous_map.items()
            if latest_min - max_ticks <= tick <= latest_max + max_ticks
        }
    if not previous_map:
        return _unavailable(f"No {metric} Previous values fall within Latest +/- {max_shift_m:g} m.")
    scale = _metric_scale(latest_map, previous_map)
    min_tick = min(min(latest_map), min(previous_map))
    max_tick = max(max(latest_map), max(previous_map))
    tick_span = max_tick - min_tick + 1
    if tick_span <= MAX_DENSE_TICKS:
        latest_dense, previous_dense, _ = _dense_maps(latest_map, previous_map)
        candidates = _dense_candidates(
            latest_dense,
            previous_dense,
            range(-max_ticks, max_ticks + 1),
            scale,
        )
    else:
        probes = len(set(latest_map) | set(previous_map)) * (2 * max_ticks + 1)
        if probes > SPARSE_WORK_BUDGET:
            return _unavailable(
                f"Sparse alignment budget exceeded for {metric}: tick span {tick_span}, "
                f"observed ticks {len(set(latest_map) | set(previous_map))}, probes {probes} > {SPARSE_WORK_BUDGET}."
            )
        candidates = [_sparse_candidate(latest_map, previous_map, shift_ticks, scale) for shift_ticks in range(-max_ticks, max_ticks + 1)]
    max_coverage = max((item["valid_points"] for item in candidates), default=0)
    eligible = [
        item for item in candidates
        if item["valid_points"] >= MIN_VALID_POINTS
        and item["span_m"] >= MIN_SPAN_M
        and item["valid_points"] >= max_coverage * MIN_COVERAGE_RATIO
        and math.isfinite(item.get("normalized_rmse", math.inf))
    ]
    if not eligible:
        return _raw_unshifted_result(
            latest_map,
            previous_map,
            f"Insufficient overlap for {metric}: at least 100 paired points, 25 m span, "
            "and 80% of maximum coverage are required. Raw values are shown without a shift.",
        )
    best = min(eligible, key=lambda item: (item["normalized_rmse"], abs(item["shift_ticks"]), -item["valid_points"], item["shift_ticks"]))
    shift_ticks = int(best["shift_ticks"])
    shifted_previous: Dict[int, np.ndarray] = {
        tick + shift_ticks: values for tick, values in previous_map.items()
    }
    output_ticks = sorted(set(latest_map) | set(shifted_previous))
    latest_values = [[None for _ in output_ticks] for _ in CHANNELS]
    previous_values = [[None for _ in output_ticks] for _ in CHANNELS]
    difference = [[None for _ in output_ticks] for _ in CHANNELS]
    for index, tick in enumerate(output_ticks):
        latest_values_at_tick = latest_map.get(tick)
        previous_values_at_tick = shifted_previous.get(tick)
        for channel_index in range(4):
            latest_value = latest_values_at_tick[channel_index] if latest_values_at_tick is not None else np.nan
            previous_value = previous_values_at_tick[channel_index] if previous_values_at_tick is not None else np.nan
            if math.isfinite(float(latest_value)):
                latest_values[channel_index][index] = float(latest_value)
            if math.isfinite(float(previous_value)):
                previous_values[channel_index][index] = float(previous_value)
            if math.isfinite(float(latest_value)) and math.isfinite(float(previous_value)):
                difference[channel_index][index] = float(latest_value - previous_value)
    paired_ticks = [tick for index, tick in enumerate(output_ticks) if any(difference[channel][index] is not None for channel in range(4))]
    overlap_from = paired_ticks[0] * STEP_M if paired_ticks else None
    overlap_to = paired_ticks[-1] * STEP_M if paired_ticks else None
    return _add_display_metadata({
        "status": "ready",
        "reason": None,
        "shift_m": shift_ticks * STEP_M,
        "rmse": float(best["rmse"]),
        "normalized_rmse": float(best["normalized_rmse"]),
        "overlap_from": overlap_from,
        "overlap_to": overlap_to,
        "overlap_length": float(overlap_to - overlap_from) if overlap_from is not None else 0.0,
        "valid_points": int(best["valid_points"]),
        "chainage": [tick * STEP_M for tick in output_ticks],
        "latest": latest_values,
        "previous": previous_values,
        "difference": difference,
    })


def build_aligned_comparison(
    latest_chart: Optional[Mapping[str, Any]],
    previous_chart: Optional[Mapping[str, Any]],
    *, max_shift_m: float = 50.0, step_m: float = STEP_M,
    prepared_latest: Optional[Mapping[str, Mapping[int, np.ndarray]]] = None,
) -> Dict[str, Any]:
    """Build Height/Stagger/Wear alignment for Latest and Prev 1 ChartData."""
    if not isinstance(latest_chart, Mapping) or not isinstance(previous_chart, Mapping):
        reason = "Latest and Prev 1 reports must both contain a ChartData sheet."
        metrics = {metric: _unavailable(reason) for metric in METRICS}
        return {"status": "unavailable", "reason": reason, "step_m": step_m, "max_shift_m": max_shift_m, "metrics": metrics}
    metrics = {
        metric: _align_metric(
            latest_chart,
            previous_chart,
            metric,
            max_shift_m=max_shift_m,
            step_m=step_m,
            latest_map_override=(prepared_latest or {}).get(metric),
        )
        for metric in METRICS
    }
    ready = any(metric["status"] == "ready" for metric in metrics.values())
    reason = None if ready else "No metric has enough valid overlap for alignment."
    return {
        "status": "ready" if ready else "unavailable",
        "reason": reason,
        "step_m": step_m,
        "max_shift_m": max_shift_m,
        "metrics": metrics,
    }
