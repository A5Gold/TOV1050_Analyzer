from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from app.core.config import get_config_dir


DEFAULT_STAGGER_WORKBOOKS = {
    "EAL": "EAL Enhanced stagger calculation (Formula).xlsx",
    "TML": "TML Enhanced stagger calculation (Formula).xlsx",
}


@dataclass(slots=True)
class SupportPoint:
    line: str
    track: str
    chainage: float
    section: str | None = None
    support_id: str | None = None


@dataclass(slots=True)
class RangeValue:
    start: float
    end: float
    value: float


def build_support_index(points: list[SupportPoint]) -> dict[str, dict[str, list[SupportPoint]]]:
    index: dict[str, dict[str, list[SupportPoint]]] = {}
    for point in points:
        line_bucket = index.setdefault(point.line.upper(), {})
        track_bucket = line_bucket.setdefault(point.track.lower(), [])
        track_bucket.append(point)

    for line_bucket in index.values():
        for track, items in line_bucket.items():
            line_bucket[track] = sorted(items, key=lambda item: item.chainage)

    return index


def build_tml_threshold_strategy(
    boundary: float,
    above: float,
    below_or_equal: float,
) -> dict[str, float | str]:
    return {
        "strategy": "threshold",
        "boundary": boundary,
        "above": above,
        "below_or_equal": below_or_equal,
    }


def resolve_stagger_workbook_path(
    line: str,
    workbook_path: Path | None = None,
    config_dir: Path | None = None,
) -> Path:
    project_root = get_config_dir().parent

    if workbook_path is not None:
        candidate = Path(workbook_path)
        if not candidate.is_absolute():
            candidate = project_root / candidate
        return candidate.resolve()

    line_key = line.upper()
    filename = DEFAULT_STAGGER_WORKBOOKS.get(line_key)
    if filename is None:
        raise ValueError(f"Unsupported stagger line: {line}")

    candidate_dirs: list[Path] = []
    if config_dir is not None:
        candidate_dirs.append(Path(config_dir))
    candidate_dirs.extend(
        [
            project_root / "docs" / "stagger",
            project_root / "config" / "stagger",
            get_config_dir() / "stagger",
        ]
    )

    for base_dir in candidate_dirs:
        candidate = base_dir / filename
        if candidate.exists():
            return candidate.resolve()

    raise FileNotFoundError(f"Stagger workbook not found for line {line_key}: {filename}")


def load_stagger_metadata(
    line: str,
    workbook_path: Path | None = None,
    config_dir: Path | None = None,
) -> dict:
    line_key = line.upper()
    resolved_path = resolve_stagger_workbook_path(
        line=line_key,
        workbook_path=workbook_path,
        config_dir=config_dir,
    )

    if line_key == "EAL":
        supports = _load_eal_supports(resolved_path, line_key)
        wind_factor = {"EAL": _load_eal_wind_factor(resolved_path)}
    elif line_key == "TML":
        supports = _load_tml_supports(resolved_path, line_key)
        wind_factor = {
            "TML": build_tml_threshold_strategy(
                boundary=121207.0,
                above=1.5,
                below_or_equal=1.0,
            )
        }
    else:
        raise ValueError(f"Unsupported stagger line: {line}")

    return {
        "source_path": resolved_path,
        "supports": {line_key: build_support_index(supports)[line_key]},
        "wind_factor": wind_factor,
        "constants": {"tension": 13.8},
    }


def _load_eal_supports(workbook_path: Path, line: str) -> list[SupportPoint]:
    df = pd.read_excel(workbook_path, sheet_name="EAL Support database")
    up_points = _parse_support_columns(
        df,
        line=line,
        track_col="Track",
        chainage_col="Chainage",
        tension_col="Tension Length",
    )
    down_points = _parse_support_columns(
        df,
        line=line,
        track_col="Track.1",
        chainage_col="Chainage.1",
        tension_col="Tension Length.1",
    )
    supports = up_points + down_points
    if not supports:
        raise ValueError("No support points found in EAL stagger workbook")
    return supports


def _load_tml_supports(workbook_path: Path, line: str) -> list[SupportPoint]:
    df = pd.read_excel(workbook_path, sheet_name="TML Support database")
    up_points = _parse_support_columns(
        df,
        line=line,
        track_col="Tk",
        chainage_col="Chg",
        tension_col="TL",
    )
    down_points = _parse_support_columns(
        df,
        line=line,
        track_col="Tk.1",
        chainage_col="Chg.1",
        tension_col="TL.1",
    )
    supports = up_points + down_points
    if not supports:
        raise ValueError("No support points found in TML stagger workbook")
    return supports


def _parse_support_columns(
    df: pd.DataFrame,
    line: str,
    track_col: str,
    chainage_col: str,
    tension_col: str,
) -> list[SupportPoint]:
    points: list[SupportPoint] = []
    if track_col not in df.columns or chainage_col not in df.columns:
        return points

    for _, row in df.iterrows():
        chainage = _to_float(row.get(chainage_col))
        if chainage is None:
            continue
        track = _normalize_track(row.get(track_col))
        if track is None:
            continue
        support_id = _to_support_id(row.get(tension_col))
        points.append(
            SupportPoint(
                line=line,
                track=track,
                chainage=chainage,
                support_id=support_id,
            )
        )
    return points


def _load_eal_wind_factor(workbook_path: Path) -> dict[str, dict[str, list[RangeValue]]]:
    df = pd.read_excel(workbook_path, sheet_name="EAL Wind Speed Factor")
    return {
        "kr": {
            "up": _parse_range_block(df, 0, 2),
            "down": _parse_range_block(df, 5, 7),
        },
        "ke": {
            "up": _parse_range_block(df, 10, 12),
            "down": _parse_range_block(df, 15, 17),
        },
        "kh": {
            "up": _parse_range_block(df, 20, 22),
            "down": _parse_range_block(df, 25, 27),
        },
    }


def _parse_range_block(df: pd.DataFrame, start_idx: int, value_idx: int) -> list[RangeValue]:
    ranges: list[RangeValue] = []
    start_col = df.columns[start_idx]
    end_col = df.columns[start_idx + 1]
    value_col = df.columns[value_idx]

    for _, row in df.iloc[1:].iterrows():
        start = _to_float(row.get(start_col))
        end = _to_float(row.get(end_col))
        value = _to_float(row.get(value_col))
        if start is None or end is None or value is None:
            continue
        ranges.append(RangeValue(start=start, end=end, value=value))

    if not ranges:
        raise ValueError(f"No stagger range values found in columns {start_col}/{end_col}/{value_col}")
    return ranges


def _normalize_track(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    raw = str(value).strip().lower()
    if raw == "up":
        return "up"
    if raw in {"dn", "down"}:
        return "down"
    return None


def _to_float(value: object) -> float | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = str(value).strip().replace(",", "")
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _to_support_id(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    return text or None
