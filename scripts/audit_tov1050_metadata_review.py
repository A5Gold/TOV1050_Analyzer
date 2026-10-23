"""Build a read-only, source-row review audit for a new candidate batch."""

from __future__ import annotations

import argparse
import csv
import io
import json
import subprocess
from collections import defaultdict
from pathlib import Path

import pandas as pd

from standardize_tov1050_metadata import MAPPING_LINE_ALIASES
from tov1050_mapping_rules import RULES_VERSION
from tov1050_support_intervals import reconstruct, location_envelope, POLICY_VERSION
from tov1050_review_corrections import bind_outer_acceptances, load_outer_acceptances, bind_corrections, canonical, corrections_digest, load_corrections
from validate_tov1050_metadata_candidates import _mapping_rows, _number, _sha256, _text


def write_csv(path, rows, fields):
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def raw_records(frame):
    result = defaultdict(list)
    for index, row in frame.iterrows():
        location, bracket = _number(row.get("Location")), _text(row.get("Bracket"))
        # Match candidate metre precision; ignore Excel binary float noise.
        location = round(location, 9) if location is not None else None
        if location is not None or bracket:
            result[(location, bracket)].append(int(index) + 2)
    return result


def differences(before, after, baseline):
    changes = []
    for sheet in sorted(set(before) | set(after)):
        a, b = before.get(sheet, {}), after.get(sheet, {})
        for location, bracket in sorted(set(a) | set(b), key=str):
            key = (location, bracket)
            delta = len(b.get(key, [])) - len(a.get(key, []))
            if delta:
                changes.append(dict(baseline=baseline, sheet=sheet, location_km=location,
                                    bracket=bracket, count_change=delta,
                                    old_rows=";".join(map(str, a.get(key, []))),
                                    current_rows=";".join(map(str, b.get(key, [])))))
    return changes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-dir", type=Path, required=True)
    parser.add_argument("--previous-batch-dir", type=Path, required=True)
    parser.add_argument("--review-corrections", type=Path)
    parser.add_argument("--accepted-outer-ranges", type=Path)
    args = parser.parse_args()
    corrections = load_corrections(args.review_corrections)
    outer_acceptances = load_outer_acceptances(args.accepted_outer_ranges)
    root, out, previous = Path.cwd(), args.batch_dir.resolve(), args.previous_batch_dir.resolve()
    mapping = root / "00 Reference Document/TOV1050 TL-BK No.xlsx"
    report = json.loads(next((out / "validation-final").glob("*.json")).read_text(encoding="utf-8"))
    manifest = json.loads((out / "candidates/manifest.json").read_text(encoding="utf-8"))
    old_manifest = json.loads((previous / "candidates/manifest.json").read_text(encoding="utf-8"))
    old_by_line = {item["line"]: item for item in old_manifest}
    assert all(item["review_corrections_sha256"] == corrections_digest(corrections) for item in manifest)
    assert all(item["outer_acceptances_sha256"] == corrections_digest(outer_acceptances) for item in manifest)
    assert all(all(book["review_corrections"][key] for key in ("sheet_present", "rows_match", "digest_match")) for book in report["workbooks"])
    source_digests = []
    for item in manifest:
        path = root / item["source"]
        digest = _sha256(path)
        assert digest == item["source_sha256"]
        source_digests.append(dict(workbook=str(path), line=item["line"], sha256=digest,
                                  previous_sha256=old_by_line[item["line"]]["source_sha256"],
                                  changed_since_previous=digest != old_by_line[item["line"]]["source_sha256"]))
    mapping_digest = _sha256(mapping)
    assert all(item["mapping_sha256"] == mapping_digest for item in manifest)
    frames = pd.read_excel(mapping, sheet_name=None)
    current = {sheet: raw_records(frame) for sheet, frame in frames.items()}

    # The previous generation emitted one candidate row per mapping source row.
    # Recover the exact 14-sheet Location/Bracket baseline from those immutable
    # candidates and their source-row provenance, rather than comparing shifted rows.
    old_mapping = {}
    snapshot = previous / "mapping-source-records.csv"
    if snapshot.exists():
        with snapshot.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                location = _number(row["location_km"])
                location = round(location, 9) if location is not None else None
                old_mapping.setdefault(row["sheet"], defaultdict(list))[(location, row["bracket"])].append(int(row["excel_row"]))
    for item in ([] if snapshot.exists() else old_manifest):
        old = pd.read_excel(previous / "candidates" / Path(item["output"]).name, sheet_name=None)
        provenance = old["__provenance__"]
        for direction in ("UT", "DT", "PL"):
            target = f"{item['line']} {direction}"
            sheet = f"{MAPPING_LINE_ALIASES.get(item['line'], item['line'])} {direction}"
            if target not in old:
                continue
            bracket_rows = old[target].loc[old[target]["Bracket"].notna()]
            source_rows = provenance.loc[(provenance["source_sheet"] == sheet) & (provenance["status"] == "emitted")]
            assert len(bracket_rows) == len(source_rows)
            records = defaultdict(list)
            for (_, row), (_, prov) in zip(bracket_rows.iterrows(), source_rows.iterrows()):
                records[(round(float(row["Bracket FromM"]) / 1000, 9), _text(row["Bracket"]))].append(int(prov["source_row"]))
            old_mapping[sheet] = records
    diff_fields = ["baseline", "sheet", "location_km", "bracket", "count_change", "old_rows", "current_rows"]
    changes = differences(old_mapping, {k: current[k] for k in old_mapping}, str(previous))
    write_csv(out / "mapping-diff-since-previous-review.csv", changes, diff_fields)
    historical_counts = {}
    for ref in ("dbce953", "9742a50"):
        raw = subprocess.check_output(["git", "show", f"{ref}:00 Reference Document/TOV1050 TL-BK No.xlsx"])
        baseline = {sheet: raw_records(frame) for sheet, frame in pd.read_excel(io.BytesIO(raw), sheet_name=None).items()}
        diff = differences(baseline, current, ref)
        historical_counts[ref] = len(diff)
        write_csv(out / f"mapping-diff-{ref}.csv", diff, diff_fields)
        if ref == "dbce953":
            # DRL had no metadata source/candidate in the previous batch; that
            # audit verified its mappings against this exact historical version.
            drl_changes = [item for item in diff if item["sheet"].startswith("DRL ")]

    sheets, components, unknown, accepted, intervals, manual = [], [], [], [], [], []
    support_summary, derivations, dispositions, applied_corrections = [], [], [], []
    accepted_edges, location_changes = [], []
    for sheet, frame in frames.items():
        _, invalid, records, diag = _mapping_rows(frame, 1000)
        sheets.append(dict(sheet=sheet, source_rows=sum(map(len, raw_records(frame).values())), component_rows=len(records),
                           invalid=len(invalid), normal_multiple_locations=diag["bracket_location_conflict_count"],
                           exact_duplicates=diag["exact_duplicate_identity_count"],
                           accepted_overlaps=diag["accepted_same_location_overlap_count"],
                           unclassified=diag["unclassified_row_count"],
                           termination_rows=diag["termination_row_count"],
                           termination_renamed=len(diag["termination_renamed_rows"])))
        for item in records:
            components.append(dict(workbook=str(mapping), sheet=sheet, **item))
        for item in diag["accepted_same_location_overlaps"]:
            accepted.append(dict(sheet=sheet, location_km=item["from_m"] / 1000,
                                 source_rows=";".join(map(str, item["source_rows"])), brackets=";".join(item["brackets"])))
        for item in diag["unclassified_rows"]:
            decision = "確認連字號 subtype -M/-C 是否等同 _M/_C；或提供正確類別／值" if item["bracket"].startswith("545-BWA-") else "確認 BMA_C 是獨立類型或 BWA_C 的輸入錯誤；提供分類或正確值"
            row = dict(workbook=str(mapping), sheet=sheet, excel_rows=str(item["source_row"]),
                       columns="A:Location / B:Bracket", original_value=f"{item['from_m']/1000:g} km / {item['bracket']}",
                       issue="未確認命名格式", decision=decision, priority="優先")
            manual.append(row)
            unknown.append(row)
        for item in invalid:
            manual.append(dict(workbook=str(mapping), sheet=sheet, excel_rows=str(item["source_row"]),
                               columns="Location / Bracket", original_value=json.dumps(item, ensure_ascii=False, default=str),
                               issue="invalid mapping", decision="補正來源值或提供有理由的排除決定", priority="優先"))
    for book in report["workbooks"]:
        source_book = root / book["source"]
        source_frames = pd.read_excel(source_book, sheet_name=None)
        applied = bind_corrections(source_frames, book["line"], corrections)
        assert applied == book["review_corrections"]["applied"]
        applied_corrections.extend(applied)
        accepted_for_book = bind_outer_acceptances(source_frames, book["line"], outer_acceptances)
        assert accepted_for_book == book["outer_acceptances"]["applied"]
        assert all(book["outer_acceptances"][key] for key in ("sheet_present", "rows_match", "digest_match"))
        old_sheets = pd.read_excel(previous / "candidates" / Path(old_by_line[book["line"]]["output"]).name, sheet_name=None)
        old_location = old_sheets.get("Exception Boundarys", pd.DataFrame())
        old_prov = old_sheets["__provenance__"]
        old_location_rows = old_prov.loc[(old_prov["source_sheet"] == "location type") & (old_prov["status"] == "emitted"), "source_row"].tolist()
        for (_, old_row), source_row in zip(old_location.iterrows(), old_location_rows):
            current_frame = source_frames.get("location type", pd.DataFrame())
            if int(source_row) - 2 >= len(current_frame):
                continue
            current_row = current_frame.iloc[int(source_row) - 2]
            for column, candidate_column in (("startKM", "UP Track FromM"), ("endKM", "UP Track ToM")):
                old_value = round(float(old_row[candidate_column]) / 1000, 9)
                new_value = round(float(current_row[column]), 9)
                if old_value != new_value:
                    location_changes.append(dict(workbook=str(source_book), sheet="location type", excel_row=int(source_row),
                                                 column=column, previous_km=old_value, current_km=new_value))
        for sheet, frame in source_frames.items():
            if not sheet.endswith("track type"):
                continue
            policy = reconstruct(frame, sheet, location_envelope(source_frames))
            if not policy["active"]:
                continue
            support_summary.append(dict(line=book["line"], sheet=sheet,
                                        superseded=sum(x["status"] == "superseded" for x in policy["sources"]),
                                        derived=len(policy["derived"]), retained_edges=len(policy["retained_edges"]),
                                        accepted_edges=len(policy["accepted_edges"]),
                                        issues=len(policy["issues"])))
            for item in policy["derived"]:
                derivations.append(dict(workbook=str(source_book), **{k: v for k, v in item.items() if k != "anchors"},
                                        anchors_json=json.dumps(item["anchors"], ensure_ascii=False)))
            for item in policy["sources"]:
                dispositions.append(dict(workbook=str(source_book), sheet=sheet,
                                         **{k: v for k, v in item.items() if k not in ("correction", "outer_acceptance")},
                                         correction_json=canonical(item.get("correction")),
                                         outer_acceptance_json=canonical(item.get("outer_acceptance"))))
            for item in policy["accepted_edges"]:
                accepted_edges.append(dict(workbook=str(source_book), sheet=sheet, source_row=item["source_row"],
                                           start_km=item["start"], end_km=item["end"],
                                           adjacent_support_row=item["adjacent_support_row"],
                                           adjacent_support_start_km=item["adjacent_support_start"],
                                           adjacent_support_end_km=item["adjacent_support_end"],
                                           acceptance_json=canonical(item["outer_acceptance"])))
            for item in policy["issues"]:
                manual.append(dict(workbook=str(source_book), sheet=sheet,
                                   excel_rows=str(item.get("source_row", item.get("source_rows", ""))),
                                   columns="track type / startKM / endKM", original_value=json.dumps(item, ensure_ascii=False),
                                   issue="Support 基準異常", decision="確認 Support 基準值；不能按舊 non-support 端點推斷正確值", priority="優先"))
            for item in policy["retained_edges"]:
                manual.append(dict(workbook=str(source_book), sheet=sheet, excel_rows=str(item["source_row"]),
                                   columns="startKM / endKM", original_value=f"{item['start']} → {item['end']} km",
                                   issue="外側 non-support 依已確認政策保留", decision="核對保留範圍是否符合實際覆蓋；邊界政策已確認，僅另列內容審閱", priority="範圍審閱"))
        for sheet, info in book["intervals"].items():
            if sheet.endswith("track type") and reconstruct(source_frames[sheet], sheet, location_envelope(source_frames))["active"]:
                continue
            assert info["overlap_examples_complete"]
            ambiguous = {(item["previous_source_row"], item["current_source_row"]) for item in info["ambiguous_overlap_examples"]}
            for item in info["overlap_examples"]:
                is_ambiguous = (item["previous_source_row"], item["current_source_row"]) in ambiguous
                row = dict(workbook=str((root / book["source"]).resolve()), sheet=sheet,
                           excel_rows=f"{item['previous_source_row']};{item['current_source_row']}", columns="startKM / endKM",
                           original_value=f"{item['previous_start']} → {item['previous_end']} / {item['current_start']} → {item['current_end']} km",
                           issue=f"interval overlap {item['overlap_m']:.6g} m" + ("（等長，解析優先次序不明）" if is_ambiguous else ""),
                           decision="確認兩列端點是否正確；若保留 overlap，確認 interval 範圍／解析優先政策", priority="優先" if is_ambiguous else "業務政策確認")
                intervals.append({**row, **item})
                manual.append(row)
    write_csv(out / "all-mapping-sheet-summary.csv", sheets, list(sheets[0]))
    write_csv(out / "mapping-components.csv", components, list(components[0]))
    manual_fields = ["workbook", "sheet", "excel_rows", "columns", "original_value", "issue", "decision", "priority"]
    write_csv(out / "manual-review-checklist.csv", manual, manual_fields)
    write_csv(out / "unclassified-mapping-rows.csv", unknown, manual_fields)
    write_csv(out / "accepted-same-location-overlaps.csv", accepted, list(accepted[0]))
    write_csv(out / "interval-overlaps.csv", intervals, list(intervals[0]) if intervals else manual_fields)
    write_csv(out / "support-derived-intervals.csv", derivations, list(derivations[0]) if derivations else ["workbook"])
    write_csv(out / "support-source-disposition.csv", dispositions, list(dispositions[0]) if dispositions else ["workbook"])
    write_csv(out / "accepted-outer-ranges.csv", accepted_edges, list(accepted_edges[0]) if accepted_edges else ["workbook"])
    write_csv(out / "location-diff-since-previous-review.csv", location_changes,
              ["workbook", "sheet", "excel_row", "column", "previous_km", "current_km"])
    # Store the raw source pair snapshot for a future review, including multiplicity.
    raw_snapshot = [dict(sheet=sheet, excel_row=row, location_km=location, bracket=bracket)
                    for sheet, pairs in current.items() for (location, bracket), rows in pairs.items() for row in rows]
    write_csv(out / "mapping-source-records.csv", raw_snapshot, ["sheet", "excel_row", "location_km", "bracket"])
    summary = dict(rules_version=RULES_VERSION, mapping_sha256=mapping_digest, source_digests=source_digests,
                   review_corrections_sha256=corrections_digest(corrections), review_corrections=applied_corrections,
                   interval_policy=POLICY_VERSION, support_summary=support_summary,
                   accepted_outer_ranges=accepted_edges, location_changes=location_changes,
                   outer_acceptances_sha256=corrections_digest(outer_acceptances), manual_review_count=len(manual),
                   previous_mapping_sha256=old_manifest[0]["mapping_sha256"],
                   previous_review_mapping_record_changes=len(changes), drl_record_changes_since_previous=len(drl_changes),
                   historical_record_changes=historical_counts, mapping_sheets=sheets,
                   statuses={book["line"]: book["status"] for book in report["workbooks"]},
                   unclassified_rows=len(unknown), accepted_same_location_groups=len(accepted), interval_overlap_pairs=len(intervals),
                   priority_review_rows=[row for row in manual if row["priority"] == "優先"],
                   split_source_rows=len({(r["sheet"], r["source_row"]) for r in components if "/" in r["source_bracket"]}),
                   extra_split_rows=sum(r["component_index"] > 1 for r in components),
                   termination_renamed_rows=sum(item["termination_renamed"] for item in sheets))
    resolved = {
        "AEL_DT_350_001_to_042_each_retained_once": all(
            sum(len(rows) for (_, bracket), rows in current["AEL DT"].items() if bracket == f"350-{index:03d}") == 1
            for index in range(1, 43)),
        "TWL_DT_row_46": frames["TWL DT"].iloc[44][["Location", "Bracket"]].tolist(),
        "KTL_DT_CR186_06": [(location, rows) for (location, bracket), rows in current["KTL DT"].items() if bracket == "CR186-06"],
        "KTL_DT_CR186_08": [(location, rows) for (location, bracket), rows in current["KTL DT"].items() if bracket == "CR186-08"],
        "ISL_DT_mapping_CN_nonempty": int(frames["ISL DT"].iloc[:, 2:14].notna().sum().sum()),
        "reversed_interval_rows": sum(info["reversed_row_count"] for book in report["workbooks"] for info in book["intervals"].values()),
    }
    summary["resolved_checks"] = resolved
    def link(label, path):
        return f"[{label}](<{Path(path).resolve().as_posix()}>)"

    correction_description = "；".join(
        f"{item['line']} / {item['sheet']} / row{item['source_row']}："
        f"{item['original']} → {item['replacement']} km ({item['application_status']})"
        for item in applied_corrections) or "無個別更正"
    md = [f"# TOV1050 metadata 審閱：2026-10-23 {out.name}", "",
          "本批以目前實際來源重新產生七線候選，規則版本 2026-10-23。候選全部維持 review-only，沒有 runtime promotion；技術 pass 不代表 metadata 核准。", "",
          "## Git 與實際來源", "",
          f"- 產生時 branch：{subprocess.check_output(['git', 'branch', '--show-current'], text=True).strip()}；HEAD：{subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()}。",
          "- 使用者六份 dirty Excel（mapping、ISL、KTL、LAR_AEL、LAR_TCL、2026-09-23 舊 ISL candidate）均保留，不納入本次 commit。",
          f"- Mapping SHA-256：`{mapping_digest}`；前批：`{summary['previous_mapping_sha256']}`。",
          f"- 相較前批，metadata source digest 改變 {sum(x['changed_since_previous'] for x in source_digests)} 份；各檔完整 digest 見 audit-summary.json。",
          "- 共用 mapping 全 16 sheets 核對；七線覆蓋 14 sheets，DRL UT／PL 另作唯讀診斷，未建立沒有 source 的 DRL candidate。", "",
          "## 實際資料差異", "",
          f"相較前批 {previous.name}，Location／Bracket 多重集合差異 {len(changes)} 筆（刪除和新增分別列一筆，不代表相同數量的錯誤）；使用前批原始記錄快照，避免拆分、suffix 或移列影響。",
          link("與上次審閱的 mapping 差異", out / "mapping-diff-since-previous-review.csv"),
          link("location type 端點差異", out / "location-diff-since-previous-review.csv"), "",
          "本次來源差異詳上述 CSV 與 source digests。候選依 Support 政策及外部人工授權更正清單重建；原始 metadata 未被流程寫回。",
          "較早的刪除決策另以 9742a50 比較；2026-09-23 審閱檔以 dbce953 比較，完整 CSV 保留各歷史基準，不能把今日 HEAD 當作 9 月更新前版本。", "",
          "## 已解決與已接受規則", "",
          f"- 不同 physical Bracket 同位置：共 {len(accepted)} 組已依使用者規則接受，不再要求逐組確認；資料全保留。",
          f"- Slash 複合 mapping：{summary['split_source_rows']} 個來源列拆分，增加 {summary['extra_split_rows']} 個輸出列；provenance 保留原串、各 component、位置及分類。",
          f"- 合法同名 termination：{summary['termination_renamed_rows']} 列候選加位置 suffix；未改來源。",
          "- 全 16 sheets 的 normal 同名多位置、physical exact duplicate 與 invalid mapping 皆為 0。",
          f"- 所有 source reversed interval 共 {resolved['reversed_interval_rows']} 列。舊內側 non-support 已 superseded，不再要求逐列確認其端點。",
          "- AEL DT 350-001～350-042 各保留一次；KTL DT CR186-06／08 分別只在 98.368／98.382 km；TWL DT row 46 為 0.4 km／2-045；ISL DT C:N 輔助欄無非空值。", "",
          "## Support 推導政策與結果", "",
          f"政策 `{POLICY_VERSION}`：Support 按位置排序，每對有效 anchor 建立 `[左Support.endKM+0.0001, 右Support.startKM-0.0001]` km，十進位計算並保留四位；canonical仍為m。Support、Curve／Tangent及location type不套用non-support重建。",
          "首末 Support 外的原始 non-support 依使用者已確認政策保留；本批5筆已明確接受並另存銜接證據，無須重複確認。只有明確授權且與來源值匹配的更正可參與推導，其原值與授權保留；其餘異常 Support 不自行更改單位或小數點。", "",
          f"本批人工授權更正 {len(applied_corrections)} 筆，清單 digest `{corrections_digest(corrections)}`。完整原值、有效值、授權與套用狀態見 audit-summary.json／候選 __review_corrections__。{correction_description}。", "",
          "| Line／source sheet | 舊內側 non-support superseded | 新衍生段 | 外側待審 | 外側已接受 | Anchor 問題 |",
          "|---|---:|---:|---:|---:|---:|"]
    for item in support_summary:
        md.append(f"| {item['line']} / {item['sheet']} | {item['superseded']} | {item['derived']} | {item['retained_edges']} | {item['accepted_edges']} | {item['issues']} |")
    md.extend(["", link("每段雙側 Support 原始 row、端點及四位公里值", out / "support-derived-intervals.csv"),
               link("來源列處置與原值", out / "support-source-disposition.csv"),
               link("已接受外側範圍與 Support 銜接證據", out / "accepted-outer-ranges.csv"), "",
          "## 人工操作表", "",
          "| Workbook（完整路徑） | Sheet／Excel row | 欄位與原始值 | 問題／需要決策 |",
          "|---|---|---|---|"])
    if not manual:
        md.append("| 無待確認列 | — | — | 已列問題全部解決或取得使用者接受；候選仍待整體核准 |")
    for row in manual:
        md.append(f"| {link(Path(row['workbook']).name, row['workbook'])} | {row['sheet']} / {row['excel_rows']} | {row['columns']}：{row['original_value']} | {row['issue']}；{row['decision']} |")
    md.extend(["", f"目前人工操作表共 {len(manual)} 筆，非重建範圍的 interval overlap 共 {len(intervals)} 組。原始overlap仍保存在validator原始intervals證據；其中舊non-support端點不再列為修正待辦。候選有效interval另有effective_intervals檢查。",
               link("完整人工操作表", out / "manual-review-checklist.csv"), "",
               "## 實際驗證與候選", "",
               "實際測試命令與數目見當日 request。Standardizer、validator結果與各候選parity／digest／provenance見JSON；source-to-candidate interval比對已納入Support推導政策，另核對anchor payload與衍生段數量。", "",
               "| Line | Validator status | 新候選（全為 review-only） |",
               "|---|---|---|"])
    for item in manifest:
        md.append(f"| {item['line']} | {summary['statuses'][item['line']]} | {link(Path(item['output']).name, root / item['output'])} |")
    md.extend(["", "## 產物與 Linear", "",
               link("規則集", root / "docs/tov1050-metadata-rules.md"),
               link("需求與實際執行命令", root / "docs/requests/2026-10-23-tov1050-support-intervals.md"),
               link("Validator JSON", next((out / "validation-final").glob("*.json"))),
               link("16 sheets 摘要", out / "all-mapping-sheet-summary.csv"),
               link("Mapping 原始記錄快照", out / "mapping-source-records.csv"),
               link("拆分及 termination 對照", out / "mapping-components.csv"), "",
               "本工作階段 Linear MCP 實際掛載且成功讀取 DAV-19／DAV-10；實作前需求與設計已同步。結果與commit／push由當日request及Linear記錄。Next action：使用者審閱本批候選後明確決定是否核准；已接受外側範圍不再重複要求確認。尚未取得整份metadata核准，不promotion。", ""])
    (out / "metadata-review-audit.md").write_text("\n".join(md), encoding="utf-8")
    (out / "audit-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    assert _sha256(mapping) == mapping_digest
    assert all(_sha256(Path(item["workbook"])) == item["sha256"] for item in source_digests)
    print(json.dumps({key: value for key, value in summary.items() if key not in ("mapping_sheets", "source_digests")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
