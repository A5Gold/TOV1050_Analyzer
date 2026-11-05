# Metadata後續審閱

Review-only，未啟用runtime；TL-BK未必完整。

```json
{
  "status": "review-only; NOT runtime approved",
  "review_version": "contact-boundary-review-2026-10-29-v2",
  "source_count": 25,
  "release_workbooks": 7,
  "release_cell_differences": 64,
  "release_digest_mismatch": 7,
  "source_digest_drift": 0,
  "mapping_points": 14437,
  "mapping_invalid": 0,
  "tl_groups": 382,
  "contact_candidates": 31,
  "gap_counts": {
    "no_contact_boundaries": 332,
    "direction_scope_unresolved": 9,
    "one_contact_boundary_missing_other_end": 15,
    "single_point_tl": 2,
    "ordinary_brackets_outside_contact_pair": 2,
    "multiple_contact_boundaries_require_segment_pairing": 2
  },
  "runtime_files_unchanged": true,
  "blockers": [
    "TL-BK incomplete; missing Contact endpoints/pairing",
    "DRL Mainline DT and PL direction semantics unresolved",
    "DRL reference/runtime Wire Wear 9.1/8.9 conflict; candidate preserves runtime",
    "No approved interval promotion"
  ]
}
```

七份release逐格比較涵蓋值、公式及sheet增減；byte SHA差異另外列出，不將格式／封裝差異當數值錯誤。
所有ordinary extrema只作observed；依2026-10-29使用者確認，無C/M分型的BWA/Fixed/Spring均為Contact；M仍排除。空白批准欄不會啟用候選。
DRL候選保留runtime threshold整表，未複製UT作DT；reference混單位Bracket欄不使用。

## Batch-01 revalidation (2026-11-03)

- Source snapshot rechecked against `outputs/metadata-review-2026-10-29/batch-04/source-snapshot.json`: 25 source SHA-256 values unchanged; no source drift.
- Workbook parity command: `python scripts/validate_followup_metadata_workbooks.py --output outputs/metadata-review-2026-11-03/batch-01`; DRL candidate 4,532 cells pass; Contact boundary candidate 7,152 cells pass.
- Isolated regression command: `python -m pytest backend/tests/test_tov1050_approved_intervals.py backend/tests/test_tov1050_boundary_review.py backend/tests/test_followup_metadata_review.py backend/tests/test_tov1050_adapter.py backend/tests/test_tov1050_capabilities.py -q`; result: 77 passed.
- Visual checks: DRL UT/PL track ranges render in H:J; interval columns remain blank where unresolved. Contact approved_from_m/approved_to_m/approved_by columns remain blank and yellow for review input.
- Formal config/source immutability check: candidate workbooks are under this batch only; no runtime/reference workbook or approved manifest was changed by this review. `git diff --check` reports only existing line-ending warnings and no whitespace errors.
- Status remains `review-only; NOT runtime approved`. Promotion is blocked by unresolved DRL direction/DT semantics, Contact pairing/coverage, Landmark scope, and threshold business decision.
- Final on-disk SHA recheck: 25 sources, zero current SHA mismatches, zero prior-batch mismatches. `git diff --name-only` for formal config/reference config/TL-BK source returned no files.
- Regression run completed: 77 passed in 32.02s.
- Linear MCP verified via whoami; results synced to DAV-27 comment `c4e01aad-f723-4bc7-91f1-f4fb8ae77f3e` and DAV-21 comment `9d89b6e7-9b59-4859-93af-d197cb26d558`. Data-owner next action explicitly recorded.
