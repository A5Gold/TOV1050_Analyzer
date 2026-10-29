"""Recover only persisted evidence; never infer missing HTTP durations."""
import csv
from collections import Counter, defaultdict
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "batch-jobs-01"
events = [json.loads(line) for line in (SOURCE / "events.jsonl").read_text(encoding="utf-8").splitlines()]
jobs = defaultdict(list)
for event in events:
    if event["event"] == "poll":
        jobs[event["job_id"]].append(event)
observed_jobs = []
for identity, polls in jobs.items():
    first, last = polls[0], polls[-1]
    observed_jobs.append({"job_id": identity, "kind": first["kind"], "session": first["client_session_id"],
                          "first_poll_wall_time": first["wall_time"], "last_poll_wall_time": last["wall_time"],
                          "last_status": last["status"], "reported_elapsed_seconds": last["elapsed_seconds"],
                          "poll_count": len(polls),
                          "note": "reported elapsed from job state; not HTTP request duration"})
with (SOURCE / "rss-samples.csv").open(encoding="utf-8") as source:
    rss = [int(row["rss_bytes"]) for row in csv.DictReader(source)]
summary = {
    "status": "failed_validation_original_run_preserved",
    "source_events": str(SOURCE / "events.jsonl"), "event_counts": dict(Counter(event["event"] for event in events)),
    "environment": next(event for event in events if event["event"] == "environment"),
    "passed_cases": [event for event in events if event["event"] == "case_passed"],
    "analysis_complete": [event for event in events if event["event"] == "analysis_complete"],
    "verified_reports": [event for event in events if event["event"] == "report_verified"],
    "failure": [event for event in events if event["event"] == "failed"],
    "observed_jobs": observed_jobs,
    "create_latencies": [{"label": event["label"], "seconds": event["create_seconds"]} for event in events if event["event"] == "analysis_complete"],
    "poll_latency": {"available": False, "reason": "Durations existed only in in-memory LATENCIES; failed run never serialized them. Poll timestamps/intervals cannot recover request latency."},
    "sampled_peak_rss_bytes": max(rss), "rss_samples": len(rss),
    "rss_scope": "same process server+client+validation, nominal 250ms; sampled peak may miss transient spikes",
    "full_compact_validation": "Generated and downloaded; ChartData completed before failure at statistics first-row exact empty string vs Excel blank. All statistics/metadata not yet validated in original run. Follow-up batch-02 required.",
    "limitations": "No new performance measurement or XLSX validation performed by this evidence-extraction script; original batch-01 artifacts remain unchanged."}
destination = HERE / "batch01-recovered-summary.json"
with destination.open("x", encoding="utf-8") as output:
    json.dump(summary, output, ensure_ascii=False, indent=2)
print(json.dumps({"path": str(destination), "passed_cases": len(summary["passed_cases"]),
                  "verified_reports": len(summary["verified_reports"]), "jobs": len(observed_jobs),
                  "sampled_peak_rss_bytes": max(rss), "poll_latency_available": False}, indent=2))
