# 隔離設計研究（2026-10-26）

現行範圍：只做同Km每channel中位實測樣本，不做噪訊處理。

- `median-study.json`、`*-median-audit.csv`、`*-median-exceptions.csv`、`*-median-vs-raw.csv`：已完成median研究，來源及metadata hash相同，全群來源oracle通過。
- `median_study.py`：研究腳本，包含已取消的noise敏感度分支，不由應用程式引用。
- noise候選／hypothetical輸出：已取消，不是噪訊真值或正式參數。
- `study.py`／`study.json`／candidate-summary及p1–p4產物：先前共識研究，需求改變時中止，沒有完整full驗收。
- `profile.py`／`profile.json`：群大小與值域探索。

現行設計：`docs/requests/2026-10-26-exception-median-sample-proposal.md`。
本目錄不產生正式Excel、不寫DB、不覆寫原始資料或metadata。
