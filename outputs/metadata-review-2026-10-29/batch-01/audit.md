# Metadata後續審閱

Review-only，未啟用runtime；TL-BK未必完整。

```json
{
  "status": "review-only; NOT runtime approved",
  "review_version": "contact-boundary-review-2026-10-29-v1",
  "source_count": 25,
  "release_workbooks": 7,
  "release_cell_differences": 64,
  "release_digest_mismatch": 7,
  "source_digest_drift": 0,
  "mapping_points": 14437,
  "mapping_invalid": 0,
  "tl_groups": 382,
  "contact_candidates": 1,
  "gap_counts": {
    "no_contact_boundaries": 370,
    "termination_contact_role_unresolved": 46,
    "single_point_tl": 2,
    "one_contact_boundary_missing_other_end": 11
  },
  "runtime_files_unchanged": true,
  "blockers": [
    "TL-BK incomplete; missing Contact endpoints/roles/pairing",
    "DRL Mainline DT and PL direction semantics unresolved",
    "DRL reference/runtime Wire Wear 9.1/8.9 conflict; candidate preserves runtime",
    "No approved interval promotion"
  ]
}
```

七份release逐格比較涵蓋值、公式及sheet增減；byte SHA差異另外列出，不將格式／封裝差異當數值錯誤。
所有ordinary extrema只作observed；未分型終端不自動視為Contact。空白批准欄不會啟用候選。
DRL候選保留runtime threshold整表，未複製UT作DT；reference混單位Bracket欄不使用。
