"""Shared parent-line, branch and direction identity; no engineering fallback.

The JSON catalog is also bundled by the frontend. Source-specific readers must
opt in to the historical LMC/TKS line aliases and retain their source values.
"""
from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.config import get_config_dir


def _load_catalog() -> dict[str, Any]:
    path = get_config_dir() / "line_catalog.json"
    if not path.is_file():
        path = Path(__file__).resolve().parents[3] / "config" / "line_catalog.json"
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


_CATALOG = _load_catalog()
LINE_CATALOG = {item["line"]: item for item in _CATALOG["lines"]}
PARENT_LINES = tuple(LINE_CATALOG)
LEGACY_LINE_ALIASES = {"LMC": ("EAL", "LMC"), "TKS": ("TKL", "TKS")}


def normalize_line(line: Any) -> str:
    value = str(line or "").strip().upper()
    if value not in LINE_CATALOG:
        raise ValueError(f"Unsupported parent line: {value or '(missing)'}")
    return value


def normalize_direction(direction: Any) -> str:
    value = str(direction or "").strip().upper()
    if not value:
        return ""
    if value in {"UP", "UT", "U"}:
        return "UP"
    if value in {"DOWN", "DN", "DT", "D"}:
        return "DOWN"
    raise ValueError(f"Unsupported direction: {direction}")


def normalize_branch(line: Any, branch: Any) -> str:
    parent = normalize_line(line)
    value = str(branch or "").strip().upper()
    if not value:
        return ""
    if value in {"MAIN LINE", "MAINLINE"}:
        value = "UT" if parent == "DRL" else "MAINLINE"
    if value == "PASSING LOOP":
        value = "PL"
    for item in LINE_CATALOG[parent]["branches"]:
        if item["branch"].upper() == value:
            return item["branch"]
    raise ValueError(f"Branch {branch!r} is not supported for {parent}")


@dataclass(frozen=True)
class LineContext:
    line: str
    branch: str
    direction: str
    legacy_session: str
    source_line: str = ""
    source_direction: str = ""

    @property
    def wire_track(self) -> str:
        if not self.direction:
            return ""
        if LINE_CATALOG[self.line]["source_system"] == "TOV1050":
            return "UT" if self.direction == "UP" else "DT"
        return "UP" if self.direction == "UP" else "DN"


def normalize_context(
    line: Any,
    branch: Any = None,
    direction: Any = None,
    section: Any = None,
    *,
    allow_legacy_aliases: bool = False,
) -> LineContext:
    source_line = str(line or "").strip().upper()
    alias_branch = ""
    if allow_legacy_aliases and source_line in LEGACY_LINE_ALIASES:
        parent, alias_branch = LEGACY_LINE_ALIASES[source_line]
    else:
        parent = normalize_line(source_line)
    selected = normalize_branch(parent, branch)
    section_value = str(section or "").strip()
    section_branch = ""
    if section_value:
        try:
            section_branch = normalize_branch(parent, section_value)
        except ValueError:
            # These existing EAL sections are subdivisions of Mainline.
            if parent == "EAL" and (section_value.upper() == "RAC" or "LOW" in section_value.upper()):
                section_branch = "Mainline"
            # Other section names are geographical context, not branch aliases.
    known = {value for value in (selected, alias_branch, section_branch) if value}
    if len(known) > 1:
        raise ValueError(f"Conflicting branch context for {parent}: {sorted(known)}")
    selected = next(iter(known), "")
    legacy = next((item["legacy_session"] for item in LINE_CATALOG[parent]["branches"]
                   if item["branch"] == selected), "")
    return LineContext(parent, selected, normalize_direction(direction), legacy,
                       source_line, str(direction or "").strip())


def catalog_payload() -> dict[str, Any]:
    """Return catalog plus explicit configuration capability, never coefficients."""
    result = copy.deepcopy(_CATALOG)
    config_dir = get_config_dir()
    for line in result["lines"]:
        for branch in line["branches"]:
            branch["metadata_available"] = (config_dir / branch["metadata_file"]).is_file()
            branch["capabilities"] = {
                "report_context": {"available": True},
                "stagger": {
                    "available": bool(branch["stagger_profile"]),
                    "reason": None if branch["stagger_profile"] else "未有核准的分支 Stagger 計算配置",
                },
                "wear_scope": {
                    "available": line["source_system"] == "TOV640",
                    "reason": None if line["source_system"] == "TOV640" else "需要已核准的 Tension Length 區間及工程配置",
                },
            }
    return result
