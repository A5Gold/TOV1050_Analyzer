"""Pure recurrence decision engine for History Compare Check 1 Year."""
from __future__ import annotations

from datetime import datetime, timedelta
import re
from typing import Any, Dict, Iterable, List, Optional
import hashlib
import json

ACTION_VERIFIED = "No action required (Verified within 1 year)"
ACTION_KEEP_MONITORING = "Keep monitoring"
NO_ACTIONS = {
    ACTION_VERIFIED.casefold(),
    "No action required (Overshoot)".casefold(),
    "No action required (Overlapping area)".casefold(),
}


def _text(value: Any) -> str:
    return re.sub(r"[\s_-]+", " ", str(value or "").strip()).casefold()


def normalize_alarm_identity(value: Any) -> str:
    normalized = _text(value)
    if normalized in {"stagger left", "stagger right", "stagger"}:
        return "stagger"
    if normalized in {"low height", "lowheight"}:
        return "low_height"
    if normalized in {"high height", "highheight"}:
        return "high_height"
    if normalized in {"wire wear", "wirewear"}:
        return "wire_wear"
    return normalized.replace(" ", "_")


def normalize_level(value: Any) -> str:
    match = re.search(r"L\s*([123])", str(value or "").upper())
    return f"L{match.group(1)}" if match else ""


def parse_date(value: Any) -> Optional[datetime]:
    if not value:
        return None
    raw = str(value).strip()[:10]
    for fmt in ("%Y%m%d", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            pass
    return None


def _field(row: Dict[str, Any], *names: str) -> Any:
    for name in names:
        if name in row and row[name] not in (None, ""):
            return row[name]
    return None


def _allowed_levels(identity: str, current_level: str) -> set[str]:
    if identity == "stagger" and current_level == "L3":
        return {"L1", "L2", "L3"}
    if identity in {"stagger", "low_height", "high_height", "wire_wear"} and current_level in {"L1", "L2"}:
        return {"L1", "L2"}
    return set()


def _candidate_sort_key(row: Dict[str, Any]) -> tuple:
    date = parse_date(_field(row, "task_run_date", "date_str")) or datetime.min
    try:
        record_id = int(_field(row, "record_id") or 0)
    except (TypeError, ValueError):
        record_id = 0
    return date, record_id


def target_version(row: Dict[str, Any]) -> str:
    """Return the optimistic-concurrency version exposed in review proposals.

    New rows use the database timestamp. Legacy rows may have no timestamp, so
    derive a stable digest from persisted identity/workflow fields instead of
    treating every missing timestamp as the same version.
    """
    timestamp = _field(row, "last_updated")
    if timestamp not in (None, ""):
        return str(timestamp)
    payload = {
        key: _field(row, key)
        for key in (
            "record_id", "exception_id", "line", "track", "section",
            "action", "reoccurrence_id", "from_m", "to_m",
        )
    }
    return "legacy:" + hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


def evaluate_recurrence(
    exception: Dict[str, Any],
    candidates: Iterable[Dict[str, Any]],
    *,
    line: str,
    track: str,
    current_date: Optional[str] = None,
    section_filter: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> Dict[str, Any]:
    original_action = str(_field(exception, "action", "current_action") or "Pending").strip()
    if original_action and original_action.casefold() != "pending":
        return {"status": "skipped", "reason": "current_action_not_pending", "exception": dict(exception)}
    exception_date = parse_date(_field(exception, "task_run_date", "date_str") or current_date)
    location = _field(exception, "maxLocation", "max_location")
    try:
        location = float(location)
    except (TypeError, ValueError):
        location = None
    identity = normalize_alarm_identity(_field(exception, "exception_type", "exception type"))
    level = normalize_level(_field(exception, "level"))
    section = str(_field(exception, "section", "Section") or "").strip()
    if exception_date is None or location is None or not identity:
        return {"status": "skipped", "reason": "unparseable_identity_date_or_location", "exception": dict(exception)}
    lower = exception_date - timedelta(days=365)
    eligible: List[Dict[str, Any]] = []
    for candidate in candidates:
        if str(_field(candidate, "line") or line) != line or str(_field(candidate, "track") or track) != track:
            continue
        if str(_field(candidate, "exception_id", "id") or "") == str(_field(exception, "exception_id", "id") or ""):
            continue
        candidate_section = str(_field(candidate, "section", "Section") or "").strip()
        if section_filter and candidate_section != section_filter.strip():
            continue
        if candidate_section != section:
            continue
        candidate_identity = normalize_alarm_identity(_field(candidate, "exception_type", "exception type"))
        if candidate_identity != identity:
            continue
        allowed = _allowed_levels(identity, level)
        candidate_level = normalize_level(_field(candidate, "level"))
        if allowed and candidate_level not in allowed:
            continue
        candidate_date = parse_date(_field(candidate, "task_run_date", "date_str"))
        if candidate_date is None or not (lower <= candidate_date <= exception_date):
            continue
        if date_from and candidate_date < (parse_date(date_from) or datetime.min):
            continue
        if date_to and candidate_date > (parse_date(date_to) or datetime.max):
            continue
        try:
            from_m = float(_field(candidate, "from_m", "FromM") or 0)
            to_m = float(_field(candidate, "to_m", "ToM") or 0)
        except (TypeError, ValueError):
            continue
        if from_m <= location <= to_m:
            eligible.append(candidate)
    if not eligible:
        status = "keep_monitoring" if identity == "stagger" and level == "L3" else "unmatched"
        proposed = ACTION_KEEP_MONITORING if status == "keep_monitoring" else None
        updated = dict(exception)
        if proposed:
            updated["action"] = proposed
        return {"status": status, "reason": None, "exception": updated}
    target = sorted(eligible, key=_candidate_sort_key, reverse=True)[0]
    target_action = str(_field(target, "action") or "").strip()
    if identity == "stagger" and level == "L3":
        action = ACTION_VERIFIED
        status = "auto_verified"
    elif target_action.casefold() in NO_ACTIONS:
        action = ACTION_VERIFIED
        status = "auto_verified"
    else:
        action = ACTION_VERIFIED
        status = "review_required"
    updated = dict(exception)
    if status == "auto_verified":
        updated["action"] = action
        updated["reoccurrence_id"] = str(_field(target, "exception_id", "id") or "")
    return {
        "status": status,
        "reason": None,
        "exception": updated,
        "target_record_id": _field(target, "record_id"),
        "target_exception_id": _field(target, "exception_id", "id"),
        "target_version": target_version(target),
        "observed_action": target_action,
        "proposed_action": action,
        "proposed_reoccurrence_id": str(_field(target, "exception_id", "id") or ""),
    }


def append_recurrence_ids(existing: Any, ids: Iterable[Any]) -> str:
    values: List[str] = []
    for value in str(existing or "").split(","):
        clean = value.strip()
        if clean and clean not in values:
            values.append(clean)
    for value in ids:
        clean = str(value or "").strip()
        if clean and clean not in values:
            values.append(clean)
    return ", ".join(values)
