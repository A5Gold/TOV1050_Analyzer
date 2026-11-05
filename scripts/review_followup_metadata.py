"""Build review-only metadata evidence. Reads sources; never writes runtime config.

Run with --output pointing to a new dated batch, then run the bundled Node
builder against workbook-layouts.json. Canonical positions are metres.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import sys

import openpyxl
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))
from app.core.tov1050_boundary_review import BOUNDARY_REVIEW_VERSION, review_contact_boundaries
from tov1050_mapping_rules import expand_mapping


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def json_write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def csv_write(path, rows, columns=None):
    columns = columns or list(dict.fromkeys(k for row in rows for k in row))
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v
                             for k, v in row.items()})


def nonempty_matrix(sheet):
    """Remove only trailing formatting empties; preserve interior blank cells."""
    rows = [list(row) for row in sheet.values]
    while rows and all(v is None for v in rows[-1]):
        rows.pop()
    width = max((i + 1 for row in rows for i, v in enumerate(row) if v is not None), default=1)
    return [row[:width] + [None] * max(0, width - len(row)) for row in rows]


def compare_workbooks(current, baseline):
    """Cell values/formulas and sheet structure, separate from byte/style drift."""
    differences = []
    a = openpyxl.load_workbook(current, read_only=True, data_only=False)
    b = openpyxl.load_workbook(baseline, read_only=True, data_only=False)
    for sheet_name in sorted(set(a.sheetnames) | set(b.sheetnames)):
        if sheet_name not in a.sheetnames or sheet_name not in b.sheetnames:
            differences.append(dict(sheet=sheet_name, cell="", kind="sheet_added" if sheet_name in a.sheetnames else "sheet_removed",
                                    baseline=None, current=None))
            # Retain each nonempty cell even on added/removed sheets.
        am = nonempty_matrix(a[sheet_name]) if sheet_name in a.sheetnames else []
        bm = nonempty_matrix(b[sheet_name]) if sheet_name in b.sheetnames else []
        for ri in range(max(len(am), len(bm))):
            ar, br = am[ri] if ri < len(am) else [], bm[ri] if ri < len(bm) else []
            for ci in range(max(len(ar), len(br))):
                av, bv = ar[ci] if ci < len(ar) else None, br[ci] if ci < len(br) else None
                if av != bv or (type(av) is not type(bv) and not isinstance(av, (int, float))):
                    kind = "value_or_formula"
                    if isinstance(av, (int, float)) and isinstance(bv, (int, float)) and abs(av - bv) <= 1e-9:
                        kind = "numeric_representation_only"
                    differences.append(dict(sheet=sheet_name, cell=f"{get_column_letter(ci+1)}{ri+1}", kind=kind,
                                            baseline=bv, current=av))
    a.close()
    b.close()
    return differences


def read_mapping(path):
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    mapping_sha = sha(path)
    points, invalid, inventory = [], [], []
    for sheet in workbook:
        records = []
        for row_number, row in enumerate(sheet.values, 1):
            if row_number == 1 or all(v is None for v in row[:2]):
                continue
            location, label = row[:2]
            try:
                position = Decimal(str(location)) * 1000
                if not position.is_finite() or not str(label or "").strip():
                    raise ValueError("missing/nonfinite Location or Bracket")
            except (InvalidOperation, ValueError, TypeError) as exc:
                invalid.append(dict(source_sheet=sheet.title, source_excel_row=row_number,
                                    location_km=location, bracket=label, error=str(exc)))
                continue
            records.append(dict(source_row=row_number, from_m=float(position.quantize(Decimal("0.000001"))),
                                bracket=str(label).strip(), original_location_km=location))
        expanded = expand_mapping(records)
        source_line, source_track = sheet.title.rsplit(" ", 1)
        line = "TKL" if source_line == "TKS" else source_line
        branch = "TKS" if source_line == "TKS" else "PL" if source_line == "DRL" and source_track == "PL" else "Mainline"
        direction = "unresolved" if source_line == "DRL" else source_track
        for item in expanded:
            physical = item["classification"] in {"normal", "termination"}
            points.append(dict(line=line, branch=branch, direction=direction,
                               tension_length=item["bracket"].split("-", 1)[0] if physical else "",
                               chainage_m=item["from_m"], bracket=item["candidate_bracket"],
                               classification=item["classification"], source_workbook=str(path),
                               source_sha256=mapping_sha, source_sheet=sheet.title,
                               source_excel_row=item["source_row"], component_index=item["component_index"],
                               source_bracket=item["source_bracket"], original_component=item["bracket"],
                               original_location_km=item["original_location_km"],
                               unit_policy="source Location km * 1000 once -> canonical m"))
        inventory.append(dict(source_sheet=sheet.title, source_rows=len(records), component_points=len(expanded),
                              classifications=dict(Counter(p["classification"] for p in expanded)),
                              canonical_line=line, canonical_branch=branch, canonical_direction=direction))
    workbook.close()
    return points, invalid, inventory


def flat_review(record):
    return {k: v for k, v in record.items() if k not in {"point_evidence", "known_boundaries"}} | {
        "source_excel_rows": [p["source_excel_row"] for p in record["point_evidence"]],
        "known_boundaries": record["known_boundaries"],
        "candidate_from_m": record["candidate"]["from_m"] if record["candidate"] else None,
        "candidate_to_m": record["candidate"]["to_m"] if record["candidate"] else None,
        "required_action": "Confirm missing Contact endpoint/segment pairing and continuity; TL-BK completeness is not guaranteed",
    }


def make_drl_layout(runtime, reference, points, reviews, source_snapshot):
    raw = openpyxl.load_workbook(runtime, read_only=True, data_only=True)
    ref = openpyxl.load_workbook(reference, read_only=True, data_only=True)
    sheets = []
    capabilities = [
        ["Status", "review-only; not runtime-ready; no promotion"],
        ["Threshold", "runtime long threshold retained exactly; reference 8.9/9.1 conflict requires decision"],
        ["Mainline UT", "10 track intervals 41000–45500 m; mapping branch UT, direction unresolved"],
        ["Mainline DT", "unavailable: no source DT track sheet; not copied from UT"],
        ["PL directions", "7 intervals 42000–44000 m; direction sharing unconfirmed"],
        ["TL / Overlap", "no approved Contact interval; blank is unknown, not non-overlap"],
        ["Landmark", "points retained separately; no approved interval"],
        ["Units", "track/boundary candidate m; mapping Location km converted once; mixed reference Bracket FromM not reused"],
    ]
    sheets.append(dict(name="Capabilities", matrix=[["Item", "State / required decision"], *capabilities]))
    sheets.append(dict(name="threshold", matrix=nonempty_matrix(raw["threshold"])))
    boundary_rows = []
    for row_number, row in enumerate(raw["location type"].values, 1):
        if row_number > 1 and any(v is not None for v in row[:3]):
            label, start, end = row[:3]
            boundary_rows.append(["DRL", label, "OCS", start * 1000, end * 1000, None, None])
    sheets.append(dict(name="Exception Boundarys", matrix=[
        ["Line", "Class", "C/R", "UP Track FromM", "UP Track ToM", "DN Track FromM", "DN Track ToM"], *boundary_rows]))
    track_columns = ["Landmark FromM", "Landmark ToM", "Landmark", "Overlap FromM", "Overlap ToM", "Overlap", "Tension Length",
                     "Track Type", "Track Type FromM", "Track Type ToM"]
    for source_sheet, target in (("UT track type", "DRL UT"), ("PL track type", "DRL PL")):
        records = []
        for ri, row in enumerate(raw[source_sheet].values, 1):
            if ri == 1 or all(v is None for v in row[:3]):
                continue
            label, start, end = row[:3]
            records.append([None] * 7 + [label, float(Decimal(str(start)) * 1000), float(Decimal(str(end)) * 1000)])
        sheets.append(dict(name=target, matrix=[track_columns, *records]))
    pcols = ["Bracket FromM", "Tension Length", "Bracket", "classification", "direction", "source_sheet", "source_excel_row",
             "component_index", "source_bracket", "original_location_km", "unit_policy", "source_sha256"]
    for branch, label in (("Mainline", "DRL UT Brackets"), ("PL", "DRL PL Brackets")):
        selected = [p for p in points if p["line"] == "DRL" and p["branch"] == branch]
        rows = [[p["chainage_m"], p["tension_length"], p["bracket"], *[p.get(c) for c in pcols[3:]]] for p in selected]
        sheets.append(dict(name=label, matrix=[pcols, *rows]))
    rcols = ["branch", "direction", "tension_length", "point_count", "observed_from_m", "observed_to_m", "contact_boundary_positions_m",
             "candidate_from_m", "candidate_to_m", "status", "gaps", "approved_from_m", "approved_to_m", "approved_by"]
    selected = [flat_review(r) for r in reviews if r["line"] == "DRL"]
    sheets.append(dict(name="Boundary Review", matrix=[rcols, *[[r.get(c) for c in rcols] for r in selected]]))
    sheets.append(dict(name="Source provenance", matrix=[["path", "sha256"], *[[s["path"], s["sha256"]] for s in source_snapshot]]))
    # Preserve the exact reference values as diagnostic evidence; not in the interval sheets.
    diagnostics = [
        ["reference", "DRL UT!E2", ref["DRL UT"]["E2"].value, "Bracket FromM contains km; rebuilt from mapping, never scale by magnitude"],
        ["reference", "Exception Boundarys!F2:G2", json.dumps([ref["Exception Boundarys"]["F2"].value, ref["Exception Boundarys"]["G2"].value]),
         "reverse DN source; direction semantics unresolved; no DT candidate generated"],
        ["runtime", "UT track type", raw["UT track type"].max_row, "10 nonempty rows; formatting tail excluded in candidate"],
    ]
    runtime_wear = {(row[0], row[1]): row[4] for row in list(raw["threshold"].values)[1:]
                    if row[2] == "Wire Wear L1"}
    for row_number, row in enumerate(ref["threshold"].values, 1):
        if row_number > 1 and row[2] == "Wire Wear":
            old = runtime_wear.get((row[0], row[1]))
            if old != row[6]:
                diagnostics.append(["threshold", f"{row[0]}/{row[1]}/Wire Wear L1", f"runtime={old}; reference={row[6]}",
                                    "retain runtime; business approval required before changing threshold"])
    sheets.append(dict(name="Decisions", matrix=[["Source", "Location", "Original value", "Decision / handling"], *diagnostics]))
    raw.close()
    ref.close()
    return dict(filename="DRL metadata (review candidate).xlsx", sheets=sheets)


def drl_source_differences(runtime, reference, points):
    """Compare units using known source schemas, never magnitude heuristics."""
    raw = openpyxl.load_workbook(runtime, read_only=True, data_only=True)
    ref = openpyxl.load_workbook(reference, read_only=True, data_only=True)
    differences = []
    runtime_wear = {(r[0], r[1]): r[4] for r in list(raw["threshold"].values)[1:] if r[2] == "Wire Wear L1"}
    for ri, row in enumerate(ref["threshold"].values, 1):
        if ri > 1 and row[2] == "Wire Wear" and runtime_wear.get((row[0], row[1])) != row[6]:
            differences.append(dict(kind="threshold_business_difference", context=f"{row[0]}/{row[1]}/Wire Wear L1",
                                    source_cell=f"threshold!G{ri}", runtime=runtime_wear.get((row[0], row[1])), reference=row[6],
                                    policy="preserve_runtime; requires business decision"))
    for branch, sheet in (("Mainline", "DRL UT"), ("PL", "DRL PL")):
        current = Counter((p["chainage_m"], p["original_component"]) for p in points if p["line"] == "DRL" and p["branch"] == branch)
        old = Counter()
        for ri, row in enumerate(ref[sheet].values, 1):
            if ri == 1 or len(row) < 7 or (row[4] is None and row[6] is None):
                continue
            # This named source's E column has explicitly verified km units.
            m = float((Decimal(str(row[4])) * 1000).quantize(Decimal("0.000001")))
            for label in str(row[6]).split("/"):
                old[(m, label.strip())] += 1
        for label, count in (current - old).items():
            differences.append(dict(kind="mapping_missing_from_reference", context=sheet, source_cell="mapping", chainage_m=label[0],
                                    bracket=label[1], count=count, policy="candidate_uses_current_mapping"))
        for label, count in (old - current).items():
            differences.append(dict(kind="reference_point_not_in_current_mapping", context=sheet, source_cell="reference E:G", chainage_m=label[0],
                                    bracket=label[1], count=count, policy="preserve_in_audit; do_not_invent_mapping"))
    raw.close()
    ref.close()
    return differences


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    runtime, reference, mapping = (ROOT / p for p in (
        "config/DRL metadata.xlsx", "00 Reference Document/config/DRL metadata.xlsx", "00 Reference Document/TOV1050 TL-BK No.xlsx"))
    release_path = ROOT / "config/tov1050-metadata-release.json"
    release = json.loads(release_path.read_text(encoding="utf-8"))
    source_paths = {runtime, reference, mapping, release_path}
    release_diff, digest_rows, source_drift = [], [], []
    for entry in release["files"]:
        current, baseline = Path(entry["destination"]), Path(entry["source"])
        source_paths.update((current, baseline))
        differences = compare_workbooks(current, baseline)
        release_diff.extend(dict(identity=entry["identity"], **row) for row in differences)
        digest_rows.append(dict(identity=entry["identity"], current_path=str(current), baseline_path=str(baseline),
                                approved_sha256=entry["approved_sha256"], current_sha256=sha(current), baseline_sha256=sha(baseline),
                                current_matches_approved=sha(current) == entry["approved_sha256"],
                                cell_diff_count=len(differences), semantic_values_equal=not differences))
        wb = openpyxl.load_workbook(current, read_only=True, data_only=True)
        if "__standardization__" in wb.sheetnames:
            records = list(wb["__standardization__"].values)
            record = dict(zip(records[0], records[1]))
            for key in ("source", "mapping"):
                path = ROOT / record[f"{key}_workbook"]
                source_paths.add(path)
                source_drift.append(dict(identity=entry["identity"], kind=key, path=str(path),
                                         recorded_sha256=record[f"{key}_sha256"], current_sha256=sha(path),
                                         unchanged=sha(path) == record[f"{key}_sha256"]))
        wb.close()
    snapshots = [dict(path=str(path), sha256=sha(path), bytes=path.stat().st_size) for path in sorted(source_paths)]
    points, invalid, inventory = read_mapping(mapping)
    reviews = review_contact_boundaries(points)
    flat = [flat_review(r) for r in reviews]
    drl_diff = drl_source_differences(runtime, reference, points)
    json_write(args.output / "source-snapshot.json", snapshots)
    json_write(args.output / "release-cell-diff.json", release_diff)
    csv_write(args.output / "release-cell-diff.csv", release_diff, ["identity", "sheet", "cell", "kind", "baseline", "current"])
    csv_write(args.output / "release-digest-review.csv", digest_rows)
    csv_write(args.output / "source-digest-review.csv", source_drift)
    json_write(args.output / "mapping-points.json", points)
    json_write(args.output / "mapping-invalid.json", invalid)
    json_write(args.output / "mapping-inventory.json", inventory)
    json_write(args.output / "drl-three-source-diff.json", drl_diff)
    csv_write(args.output / "drl-three-source-diff.csv", drl_diff)
    csv_write(args.output / "drl-context-capabilities.csv", [
        dict(line="DRL", branch=branch, direction=direction, track_intervals=count,
             track_status="available_source_rows" if count else "unavailable",
             bracket_direction_status="unresolved: mapping sheet denotes branch, not confirmed running direction",
             contact_intervals="unavailable: no approved pairing", overlap="unknown", landmark_intervals="unavailable",
             required_action=action)
        for branch, direction, count, action in (
            ("Mainline", "UT", 10, "Confirm direction of DRL UT mapping; review Contact endpoints"),
            ("Mainline", "DT", 0, "Provide DT track intervals; never copy UT"),
            ("PL", "UT", 7, "Confirm whether PL track/mapping source applies to UT direction"),
            ("PL", "DT", 7, "Confirm whether PL track/mapping source applies to DT direction"))])
    json_write(args.output / "contact-boundary-review.json", reviews)
    csv_write(args.output / "contact-boundary-review.csv", flat)
    layout = make_drl_layout(runtime, reference, points, reviews, snapshots)
    rcols = ["line", "branch", "direction", "tension_length", "point_count", "observed_from_m", "observed_to_m", "contact_boundary_positions_m",
             "candidate_from_m", "candidate_to_m", "status", "gaps", "approved_from_m", "approved_to_m", "approved_by", "source_excel_rows"]
    review_layout = dict(filename="Contact TL boundary review.xlsx", sheets=[
        dict(name="Review Guide", matrix=[["項目", "說明"],
            ["狀態", f"只供審閱，未啟用。382組中有{sum(r['candidate'] is not None for r in reviews)}組Contact雙端候選。"],
            ["已確認規則", "C=Contact、M=Messenger；無C/M分型的BWA/Fixed/Spring全部按Contact邊界處理。"],
            ["觀察與候選", "observed只記錄Bracket首末觀察點；candidate是明確Contact雙端且沒有範圍矛盾的配對建議，仍須審閱連通及適用範圍。"],
            ["批准欄", "黃色approved欄維持空白，不因候選或本次設計批准自動啟用。完整性另須核准；已知一個TL不能自動填Overlap=N。"],
            ["現行metadata", "使用者確認64格runtime門檻/端點改動是有意調整，本次保留現值；release逐格差異另列audit。"],
            ["來源", "Known Boundaries保留位置、Contact/Messenger及角色規則依據；JSON保留完整點位lineage；source_excel_rows對應原TL-BK。"]]),
        dict(name="Boundary Review", matrix=[rcols, *[[r.get(c) for c in rcols] for r in flat]]),
        dict(name="Known Boundaries", matrix=[["line", "branch", "direction", "tension_length", "chainage_m", "bracket", "wire_role", "wire_role_basis", "source_sheet", "source_excel_row"],
             *[[r["line"], r["branch"], r["direction"], r["tension_length"], b["chainage_m"], b["bracket"], b["wire_role"], b["wire_role_basis"], b["source_sheet"], b["source_excel_row"]]
               for r in reviews for b in r["known_boundaries"]]]),
    ])
    json_write(args.output / "workbook-layouts.json", [layout, review_layout])
    summary = dict(status="review-only; NOT runtime approved", review_version=BOUNDARY_REVIEW_VERSION,
                   source_count=len(snapshots), release_workbooks=len(digest_rows), release_cell_differences=len(release_diff),
                   release_digest_mismatch=sum(not r["current_matches_approved"] for r in digest_rows),
                   source_digest_drift=sum(not r["unchanged"] for r in source_drift),
                   mapping_points=len(points), mapping_invalid=len(invalid), tl_groups=len(reviews),
                   contact_candidates=sum(r["candidate"] is not None for r in reviews),
                   gap_counts=dict(Counter(gap for r in reviews for gap in r["gaps"])),
                   runtime_files_unchanged=all(sha(s["path"]) == s["sha256"] for s in snapshots),
                   blockers=["TL-BK incomplete; missing Contact endpoints/pairing", "DRL Mainline DT and PL direction semantics unresolved",
                             "DRL reference/runtime Wire Wear 9.1/8.9 conflict; candidate preserves runtime", "No approved interval promotion"])
    if not summary["runtime_files_unchanged"]:
        raise RuntimeError("A source changed during review; rerun a fresh batch")
    json_write(args.output / "audit-summary.json", summary)
    lines = ["# Metadata後續審閱", "", "Review-only，未啟用runtime；TL-BK未必完整。", "", "```json", json.dumps(summary,ensure_ascii=False,indent=2), "```", "",
             "七份release逐格比較涵蓋值、公式及sheet增減；byte SHA差異另外列出，不將格式／封裝差異當數值錯誤。",
             "所有ordinary extrema只作observed；依2026-10-29使用者確認，無C/M分型的BWA/Fixed/Spring均為Contact；M仍排除。空白批准欄不會啟用候選。",
             "DRL候選保留runtime threshold整表，未複製UT作DT；reference混單位Bracket欄不使用。"]
    (args.output / "audit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
