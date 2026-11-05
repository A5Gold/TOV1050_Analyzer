"""P1 fixed-median and P2 cleaned-raw evidence; never writes source workbooks."""
import gc
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import types

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/validation-2026-11-03/stagger-policy"
OUT.mkdir(parents=True, exist_ok=True)
os.environ["DB_PATH"] = str(OUT / "isolated.db")
sys.path.insert(0, str(ROOT / "backend"))
import pandas as pd
from app.core.analyzers import ExceptionDetector
from app.core.chainage_reduction import reduce_chainage, annotate_raw_samples
from app.core.tov1050_metadata import TOV1050MetadataManager
from app.core.metadata import MetadataManager
from app.api.endpoints.analysis import DataLoader, TOV1050DataLoader

legacy = types.ModuleType("legacy_metadata")
exec(subprocess.check_output(["git", "show", "HEAD:backend/app/core/metadata.py"], cwd=ROOT), legacy.__dict__)


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def records(frame):
    return json.loads(frame.to_json(orient="records"))


def canonical(frame):
    cols = [c for c in ["level", "FromM", "ToM", "maxLocation", "maxValue", "exception type",
                       "length", "Class", "Track Type", "Threshold Value", "peak_channel",
                       "peak_source_row", "id"] if c in frame]
    return records(frame[cols])


def save(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


manifest = []
for path in sorted((ROOT / "config").glob("*.xlsx")):
    before_sha = sha(path)
    old = legacy.MetadataManager(path).get_all_thresholds()
    new = TOV1050MetadataManager(path).get_all_thresholds()
    old_s = old[old["Exc Type"].isin(["Stagger Left", "Stagger Right"])]
    new_s = new[new["Exc Type"].isin(["Stagger Left", "Stagger Right"])]
    cols = ["Class", "Track Type", "Exc Type"] + [c for c in ["Stagger L1", "Stagger L2", "Stagger L3"] if c in new]
    manifest.append(dict(path=str(path), sha256=before_sha, source_unchanged=sha(path) == before_sha,
                         before=records(old_s.reindex(columns=cols)), after=records(new_s.reindex(columns=cols))))
save("threshold-semantic-diff.json", manifest)

cases = [
    ("TWL/20260907_TWL_UT.csv", "TWL", "UT", "20260907", "CEN", "TSW"),
    ("TWL/20260630_TWL_UT.csv", "TWL", "UT", "20260630", "CEN", "TSW"),
    ("TML/TML_D1_260410.datac", "TML", "DN", "20260410", "", ""),
]
summary_path = OUT / "summary.json"
summary = json.loads(summary_path.read_text(encoding="utf-8")) if "--tml-only" in sys.argv else []
if "--tml-only" in sys.argv:
    summary = [entry for entry in summary if Path(entry["file"]).parent.name != "TML"]
for name, line, track, date, start, end in cases:
    if "--tml-only" in sys.argv and line != "TML":
        continue
    started = time.perf_counter()
    path = ROOT / "00 Reference Document/Raw data" / name
    source_sha = sha(path)
    print(f"START {name}", flush=True)
    loader = DataLoader() if path.suffix == ".datac" else TOV1050DataLoader()
    raw = loader.load_data(str(path))
    loaded_rows = len(raw)
    for column, selected, source in [("Line", line, "source_line"), ("Track", track, "source_track")]:
        if column in raw:
            raw[source] = raw[column].copy()
        raw[column] = selected
        raw[column.lower()] = selected
    manager_type = MetadataManager if line == "TML" else TOV1050MetadataManager
    mgr = manager_type(ROOT / "config" / f"{line} metadata.xlsx")
    detector = ExceptionDetector(mgr)
    raw = detector._map_class_info(raw, line, track, "Mainline")
    mgr.defer_approved_enrichment = True
    raw = detector._map_track_info(raw, line, "Mainline", track)
    raw = annotate_raw_samples(raw)
    median, aggregation = reduce_chainage(raw)
    if line != "TML":
        median = mgr.map_approved_enrichment(median, line, "Mainline", track)
    kwargs = dict(line=line, section="Mainline", track=track, date_str=date,
                  task_no="", station_start=start, station_end=end, metadata_mapped=True)
    get_new = mgr.get_all_thresholds
    old_thresholds = legacy.MetadataManager(mgr.config_path).get_all_thresholds()
    modes = {}
    mode_times = {}
    for mode, frame, old_policy in [("median_before", median, True), ("median_after", median, False),
                                     ("cleaned_raw_after", raw, False)]:
        tick = time.perf_counter()
        mgr.get_all_thresholds = (lambda: old_thresholds.copy()) if old_policy else get_new
        result, _ = detector.analyze(frame.copy(), **kwargs)
        modes[mode] = {kind: canonical(value) for kind, value in result.items()}
        mode_times[mode] = time.perf_counter() - tick
        save(f"{date}-{line}-{mode}.json", {kind: records(value) for kind, value in result.items()})
        print(mode, {kind: len(value) for kind, value in result.items()}, flush=True)
        del result
        gc.collect()
    diffs = {}
    for mode_a, mode_b in [("median_before", "median_after"), ("median_after", "cleaned_raw_after")]:
        key = f"{mode_a}_to_{mode_b}"
        diffs[key] = {}
        for kind in modes[mode_a]:
            left, right = modes[mode_a][kind], modes[mode_b][kind]
            aset = {json.dumps(v, sort_keys=True) for v in left}
            bset = {json.dumps(v, sort_keys=True) for v in right}
            diffs[key][kind] = dict(before_count=len(left), after_count=len(right), identical=left == right,
                removed=[json.loads(v) for v in sorted(aset-bset)], added=[json.loads(v) for v in sorted(bset-aset)])
    save(f"{date}-{line}-semantic-diff.json", diffs)
    entry = dict(file=str(path), source_sha256=source_sha, source_unchanged=sha(path) == source_sha,
                 loaded_cleaned_rows=loaded_rows, mapped_raw_rows=len(raw), median_rows=len(median),
                 aggregation=aggregation, counts={mode: {k: len(v) for k,v in result.items()} for mode,result in modes.items()},
                 mode_seconds=mode_times, elapsed_seconds=time.perf_counter()-started,
                 unchanged={key: {kind: value["identical"] for kind,value in diff.items()} for key,diff in diffs.items()})
    assert entry["source_unchanged"]
    summary.append(entry)
    save("summary.json", summary)
    print(f"END {name} {entry['elapsed_seconds']:.1f}s", flush=True)
    del raw, median, modes
    gc.collect()
assert all(sha(Path(entry["path"])) == entry["sha256"] for entry in manifest)
print("ALL SOURCES UNCHANGED", flush=True)

# Rebuild every semantic diff from saved full results, including resumed cases.
for entry in summary:
    path = Path(entry["file"])
    line = path.parent.name
    date = "20260410" if line == "TML" else path.name[:8]
    all_modes = {mode: json.loads((OUT / f"{date}-{line}-{mode}.json").read_text(encoding="utf-8"))
                 for mode in ["median_before", "median_after", "cleaned_raw_after"]}
    diffs = {}
    for mode_a, mode_b in [("median_before", "median_after"), ("median_after", "cleaned_raw_after")]:
        key = f"{mode_a}_to_{mode_b}"
        diffs[key] = {}
        for kind in all_modes[mode_a]:
            left = canonical(pd.DataFrame(all_modes[mode_a][kind]))
            right = canonical(pd.DataFrame(all_modes[mode_b][kind]))
            aset = {json.dumps(v, sort_keys=True) for v in left}
            bset = {json.dumps(v, sort_keys=True) for v in right}
            diffs[key][kind] = dict(before_count=len(left), after_count=len(right), identical=left == right,
                removed=[json.loads(v) for v in sorted(aset-bset)], added=[json.loads(v) for v in sorted(bset-aset)])
    save(f"{date}-{line}-semantic-diff.json", diffs)
    entry["level_peak_summary"] = {}
    for mode, values in all_modes.items():
        entry["level_peak_summary"][mode] = {}
        for kind, rows in values.items():
            frame = pd.DataFrame(rows)
            entry["level_peak_summary"][mode][kind] = dict(
                levels=frame["level"].value_counts().to_dict() if len(frame) else {},
                peak_min=float(frame["maxValue"].min()) if len(frame) else None,
                peak_max=float(frame["maxValue"].max()) if len(frame) else None)
    entry["unchanged"] = {key: {kind: value["identical"] for kind,value in diff.items()} for key,diff in diffs.items()}
save("summary.json", summary)
