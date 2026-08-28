from app.core.check_1_year_rules import evaluate_recurrence, append_recurrence_ids


def candidate(**overrides):
    row = {
        "record_id": 10,
        "exception_id": "old-10",
        "line": "EAL",
        "track": "UP",
        "section": "Mainline",
        "exception_type": "Stagger Left",
        "level": "L2",
        "from_m": 100,
        "to_m": 200,
        "task_run_date": "2025-06-01",
        "action": "No action required (Overshoot)",
        "last_updated": "v1",
    }
    row.update(overrides)
    return row


def exception(**overrides):
    row = {
        "id": "new-1",
        "exception_type": "Stagger Right",
        "level": "L2",
        "max_location": 150,
        "section": "Mainline",
        "task_run_date": "2026-01-01",
        "action": "Pending",
    }
    row.update(overrides)
    return row


def test_stagger_left_right_are_one_family_and_no_action_is_automatic():
    result = evaluate_recurrence(exception(), [candidate()], line="EAL", track="UP")
    assert result["status"] == "auto_verified"
    assert result["exception"]["reoccurrence_id"] == "old-10"


def test_height_families_do_not_cross_match():
    result = evaluate_recurrence(exception(exception_type="Low Height"), [candidate(exception_type="High Height")], line="EAL", track="UP")
    assert result["status"] == "unmatched"


def test_l3_stagger_without_candidate_keeps_monitoring():
    result = evaluate_recurrence(exception(level="L3"), [], line="EAL", track="UP")
    assert result["status"] == "keep_monitoring"
    assert result["exception"]["action"] == "Keep monitoring"


def test_non_pending_is_skipped_and_review_proposal_is_staged():
    skipped = evaluate_recurrence(exception(action="Calculation"), [candidate()], line="EAL", track="UP")
    assert skipped["status"] == "skipped"
    review = evaluate_recurrence(exception(), [candidate(action="Verify on site")], line="EAL", track="UP")
    assert review["status"] == "review_required"
    assert review["proposed_reoccurrence_id"] == "old-10"


def test_recurrence_append_is_idempotent():
    assert append_recurrence_ids("a, b", ["b", "c", "c"]) == "a, b, c"
