# 本批次實作與驗證

- 正式review批次為batch-02；batch-01保留為前次生成證據。
- 所有workbook為review-only，沒有runtime promotion或核准interval。
- 七份runtime相對release candidate有64格實質差異：threshold46格、Exception Boundarys18格。
- threshold差異：32格8.9→9.1、14格7.24→7.44；區間18格端點亦有變動。
- 不能把這批差異當byte/格式噪音；本次保留runtime現值，不自動還原、不沿用舊digest宣稱核准。
- 來源source/mapping相對__standardization__記錄的digest皆無漂移，runtime七份則皆與release digest不同。
- 全mapping拆分後14437點、382個physical TL/context組；1組明確Contact雙端候選：TKL/TKS/DT/590，65284–66392m。仍待連通、scope及coverage審閱，未啟用。
- DRL9組方向scope unresolved；沒有使用無分型終端補C，也未把普通首末Bracket升格邊界。

## 命令

```powershell
venv/Scripts/python.exe scripts/review_followup_metadata.py --output outputs/metadata-review-2026-10-29/batch-02
# workbook builder使用bundled Node及batch-02/node_modules→bundled node_modules junction
node scripts/build_followup_metadata_workbooks.mjs outputs/metadata-review-2026-10-29/batch-02
venv/Scripts/python.exe scripts/validate_followup_metadata_workbooks.py --output outputs/metadata-review-2026-10-29/batch-02
venv/Scripts/python.exe -m pytest -q backend/tests/test_tov1050_boundary_review.py backend/tests/test_followup_metadata_review.py
```

workbook-validation.json保存逐格完整輸出parity；所有sheet有PNG檢視，工作簿未由原生Excel人工驗收。
