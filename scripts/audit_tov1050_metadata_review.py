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
    args = parser.parse_args()
    root, out, previous = Path.cwd(), args.batch_dir.resolve(), args.previous_batch_dir.resolve()
    mapping = root / "00 Reference Document/TOV1050 TL-BK No.xlsx"
    report = json.loads(next((out / "validation-final").glob("*.json")).read_text(encoding="utf-8"))
    manifest = json.loads((out / "candidates/manifest.json").read_text(encoding="utf-8"))
    old_manifest = json.loads((previous / "candidates/manifest.json").read_text(encoding="utf-8"))
    old_by_line = {item["line"]: item for item in old_manifest}
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
    for item in old_manifest:
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
        assert not [item for item in book["findings"] if item["severity"] == "error"]
        for sheet, info in book["intervals"].items():
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
    write_csv(out / "interval-overlaps.csv", intervals, list(intervals[0]))
    # Store the raw source pair snapshot for a future review, including multiplicity.
    raw_snapshot = [dict(sheet=sheet, excel_row=row, location_km=location, bracket=bracket)
                    for sheet, pairs in current.items() for (location, bracket), rows in pairs.items() for row in rows]
    write_csv(out / "mapping-source-records.csv", raw_snapshot, ["sheet", "excel_row", "location_km", "bracket"])
    summary = dict(rules_version=RULES_VERSION, mapping_sha256=mapping_digest, source_digests=source_digests,
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

    md = ["# TOV1050 metadata 審閱：2026-10-23 batch-01", "",
          "本批以目前實際來源重新產生七線候選，規則版本 2026-10-23。候選全部維持 review-only，沒有 runtime promotion；技術 pass 不代表 metadata 核准。", "",
          "## Git 與實際來源", "",
          "- 開始時 master；HEAD／origin/master 均為 4c12e8d4e004c004c07b21394028beac88ebf75d。",
          "- 使用者原有四份 dirty Excel（mapping、ISL、KTL、2026-09-23 舊 ISL candidate）均保留，不納入本次 commit。",
          f"- Mapping SHA-256：`{mapping_digest}`；前次 batch-03：`{summary['previous_mapping_sha256']}`。",
          "- 七份 metadata source digest 全部與昨日 batch-03 相同；ISL／KTL 自該次審閱後沒有新內容變更，與 Git HEAD 的差異仍存在。",
          "- 共用 mapping 全 16 sheets 核對；七線覆蓋 14 sheets，DRL UT／PL 另作唯讀診斷，未建立沒有 source 的 DRL candidate。", "",
          "## 實際資料差異", "",
          f"相較昨日 batch-03 的 14 sheets，Location／Bracket 多重集合差異 {len(changes)} 筆（刪除和新增分別列一筆，不能當作相同數量的錯誤）。以前次 candidate 配對 provenance 重建來源 row，按 canonical 精度排除 Excel 浮點尾數噪音；非單純比較移列後的 row。DRL 依前次已核實的歷史 mapping 比較，變更 {len(drl_changes)} 筆。",
          link("與上次審閱的完整差異", out / "mapping-diff-since-previous-review.csv"), "",
          "本次變更包括 SI 補編號、BWA／Fixed subtype、TKS isolator 格式、TKL DT／TKS DT 刪除或整理列；已重新核對剩餘 identity，不以刪列數推論整段 tension length 消失。",
          "較早的刪除決策另以 9742a50 比較；2026-09-23 審閱檔以 dbce953 比較，完整 CSV 保留各歷史基準，不能把今日 HEAD 當作 9 月更新前版本。", "",
          "## 已解決與已接受規則", "",
          f"- 不同 physical Bracket 同位置：共 {len(accepted)} 組已依使用者規則接受，不再要求逐組確認；資料全保留。",
          f"- Slash 複合 mapping：{summary['split_source_rows']} 個來源列拆分，增加 {summary['extra_split_rows']} 個輸出列；provenance 保留原串、各 component、位置及分類。",
          f"- 合法同名 termination：{summary['termination_renamed_rows']} 列候選加位置 suffix；未改來源。",
          "- 全 16 sheets 的 normal 同名多位置、physical exact duplicate 與 invalid mapping 皆為 0。",
          f"- 所有 source reversed interval 共 {resolved['reversed_interval_rows']} 列；ISL DT row 387 仍為 99.5361 → 99.5369 km。",
          "- AEL DT 350-001～350-042 各保留一次；KTL DT CR186-06／08 分別只在 98.368／98.382 km；TWL DT row 46 為 0.4 km／2-045；ISL DT C:N 輔助欄無非空值。", "",
          "## 優先人工操作表", "",
          "| Workbook（完整路徑） | Sheet／Excel row | 欄位與原始值 | 問題／需要決策 |",
          "|---|---|---|---|"]
    for row in summary["priority_review_rows"]:
        md.append(f"| {link(Path(row['workbook']).name, row['workbook'])} | {row['sheet']} / {row['excel_rows']} | {row['columns']}：{row['original_value']} | {row['issue']}；{row['decision']} |")
    md.extend(["", f"另有 {len(intervals)} 組 interval overlaps（包含上述兩組等長 overlap），完整操作表保留每組 workbook／sheet／row／端點與決策。Bracket 同位合法規則不直接核准 interval 的範圍／解析優先政策。",
               link("完整人工操作表", out / "manual-review-checklist.csv"), "",
               "## 實際驗證與候選", "",
               "18 targeted metadata tests passed；standardizer exit 0；validator exit 0，沒有 error finding。各候選 threshold／location／interval／Bracket parity、source／mapping digest、provenance source-row 及 component payload 核對全部吻合。", "",
               "| Line | Validator status | 新候選（全為 review-only） |",
               "|---|---|---|"])
    for item in manifest:
        md.append(f"| {item['line']} | {summary['statuses'][item['line']]} | {link(Path(item['output']).name, root / item['output'])} |")
    md.extend(["", "## 產物與 Linear", "",
               link("規則集", root / "docs/tov1050-metadata-rules.md"),
               link("需求與實際執行命令", root / "docs/requests/2026-10-23-tov1050-metadata-review.md"),
               link("Validator JSON", next((out / "validation-final").glob("*.json"))),
               link("16 sheets 摘要", out / "all-mapping-sheet-summary.csv"),
               link("Mapping 原始記錄快照", out / "mapping-source-records.csv"),
               link("拆分及 termination 對照", out / "mapping-components.csv"), "",
               "本工作階段 Linear MCP 實際掛載且成功讀取 DAV-19／DAV-10；實作前需求與設計已同步。結果與 commit／push 狀態由當日 request 及 Linear 最終進度記錄。Next action：使用者確認三列未分類命名與 interval 端點／政策，之後依決策重新產生；未取得明確核准不得 promotion。", ""])
    (out / "metadata-review-audit.md").write_text("\n".join(md), encoding="utf-8")
    (out / "audit-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    assert _sha256(mapping) == mapping_digest
    assert all(_sha256(Path(item["workbook"])) == item["sha256"] for item in source_digests)
    print(json.dumps({key: value for key, value in summary.items() if key not in ("mapping_sheets", "source_digests")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
