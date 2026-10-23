"""Read-only metadata audit and compatibility-layout payload (never promotion)."""
from __future__ import annotations
from collections import Counter
import argparse
import hashlib
import json
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.core.tov1050_contract import LINE_SESSIONS, metadata_workbook_for
from app.core.tov1050_metadata import TOV1050MetadataManager


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def clean(frame):
    return json.loads(frame.to_json(orient="records", double_precision=15))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    release = json.loads((ROOT / "config/tov1050-metadata-release.json").read_text(encoding="utf-8"))
    release_files = {Path(f["destination"]).name:f for f in release["files"]}
    capability_rows, review, drift, layouts, drl_inventory = [], [], [], [], []
    for line, sessions in LINE_SESSIONS.items():
        for session in sorted(sessions):
            path = metadata_workbook_for(line, session, ROOT / "config")
            manager = TOV1050MetadataManager(path)
            actual = sha(path)
            expected = release_files.get(path.name)
            if expected:
                if actual != expected["approved_sha256"] or sha(expected["source"]) != actual:
                    raise ValueError(f"Approved config/candidate digest drift: {path}")
                standard = manager._load_sheet("__standardization__").iloc[0]
                for source_key, digest_key in (("source_workbook","source_sha256"),("mapping_workbook","mapping_sha256")):
                    source = ROOT / standard[source_key]
                    current = sha(source)
                    drift.append(dict(identity=path.stem,kind=source_key,path=str(source),expected=standard[digest_key],actual=current,unchanged=current==standard[digest_key]))
            if line == "DRL" and session == "Mainline":
                for sheet in pd.ExcelFile(path).sheet_names:
                    frame = pd.read_excel(path,sheet_name=sheet)
                    drl_inventory.append(dict(workbook=str(path),sha256=actual,sheet=sheet,rows=len(frame),columns=list(frame.columns),approval="not_in_batch04",scope="direction semantics of PL require business review"))
            candidate_sheets = []
            if expected:
                for sheet in ("threshold", "Exception Boundarys"):
                    frame = manager._load_sheet(sheet)
                    candidate_sheets.append(dict(name=sheet,columns=list(frame.columns),rows=clean(frame)))
            for direction in ("UT", "DT"):
                capabilities = manager.get_capabilities(line, session, direction)
                for name, state in capabilities["capabilities"].items():
                    capability_rows.append(dict(line=line,session=session,direction=direction,capability=name,**state,workbook=str(path),sha256=actual,approval="batch04_activated" if expected else "DRL_not_reviewed"))
                points = manager._point_frame(line,session,direction)
                physical = points[points.classification.isin(["normal","termination"])]
                for tl, group in physical.groupby("tension_length",sort=False):
                    term = group[group.classification.eq("termination")]
                    review.append(dict(line=line,session=session,direction=direction,tension_length=tl,
                                       observed_from_m=group.chainage_m.min(),observed_to_m=group.chainage_m.max(),point_count=len(group),
                                       source_workbook=group.source_workbook.iloc[0],source_sheet=group.source_sheet.iloc[0],
                                       source_excel_rows=json.dumps(group.source_excel_row.tolist()),
                                       runtime_workbook=str(path),runtime_sheet=group.sheet.iloc[0],runtime_excel_rows=json.dumps(group.excel_row.tolist()),
                                       termination_count=len(term),terminations_json=json.dumps(clean(term),ensure_ascii=False),
                                       observed_start_brackets=json.dumps(group[group.chainage_m.eq(group.chainage_m.min())].bracket.tolist(),ensure_ascii=False),
                                       observed_end_brackets=json.dumps(group[group.chainage_m.eq(group.chainage_m.max())].bracket.tolist(),ensure_ascii=False),
                                       boundary_status="observed_envelope_only_not_approved_physical_extent",
                                       approved_from_m=None,approved_to_m=None,approved_by=None,
                                       required_decision="Confirm completeness, continuity, true termination bounds, split segments, single-point policy and closure/resolution"))
                if expected:
                    identity,_ = manager._wide_context(line,session,direction)
                    name=f"{identity} {direction}"
                    original = manager._load_sheet(name)
                    # Independent wide column groups; no inferred alignment between rows.
                    track = original[["Track Type","Track Type FromM","Track Type ToM"]].dropna(how="all").reset_index(drop=True)
                    compatible = pd.DataFrame(columns=["Landmark FromM","Landmark ToM","Landmark","Overlap FromM","Overlap ToM","Overlap","Tension Length"])
                    compatible = pd.concat([compatible,track],axis=1)
                    candidate_sheets.append(dict(name=name,columns=list(compatible.columns),rows=clean(compatible)))
                    brackets = points.rename(columns={"chainage_m":"Bracket FromM","tension_length":"Tension Length","bracket":"Bracket"})
                    candidate_sheets.append(dict(name=f"{name} Brackets",columns=list(brackets.columns),rows=clean(brackets)))
            if expected:
                candidate_sheets.append(dict(name="Capabilities",columns=["Status","TL intervals","Overlap","Landmark intervals","Source SHA256","Enrichment"],rows=[{
                    "Status":"review-only layout; NOT runtime-ready", "TL intervals":"unavailable: physical boundaries not approved",
                    "Overlap":"unknown; blank flags are NOT known non-overlap", "Landmark intervals":"unavailable; points remain points",
                    "Source SHA256":actual,"Enrichment":"tov640-first-nonempty-v1"}]))
                layouts.append(dict(filename=f"{path.stem} (compatibility review).xlsx",sheets=candidate_sheets))
    pd.DataFrame(capability_rows).to_csv(args.output/"metadata-capability-matrix.csv",index=False,encoding="utf-8-sig")
    pd.DataFrame(review).to_csv(args.output/"tl-boundary-review.csv",index=False,encoding="utf-8-sig")
    pd.DataFrame(drift).to_csv(args.output/"source-digest-check.csv",index=False,encoding="utf-8-sig")
    for name,data in (("compatibility-layouts.json",layouts),("drl-pl-inventory.json",drl_inventory)):
        (args.output/name).write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")
    summary=dict(physical_tl_groups=len(review),single_point_groups=sum(r["point_count"]==1 for r in review),
                 capability_contexts=len(capability_rows)//8,source_drift_count=sum(not r["unchanged"] for r in drift),
                 runtime_configs_unchanged=True,overlap_state="unknown",candidate_status="review_only_not_activated",
                 drl_pl_status="not_in_batch04; inventory only",interval_generation="none: no approved physical boundaries")
    (args.output/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False))


if __name__ == "__main__":
    main()
