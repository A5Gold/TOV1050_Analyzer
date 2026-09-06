# TOV1050 Metadata Audit

- Generated: 2026-09-02
- Source workbooks were read-only; no workbook was modified.
- Canonical Chainage policy: source `Km`/`startKM`/`endKM`/`Location` values are converted to metres at the adapter boundary.

## Runtime Workbooks

| Line | Threshold schema | Sheets | Interval overlaps | Invalid rows | Flags |
|---|---|---:|---:|---:|---|
| DRL | long | 4 | 0 | 0 | threshold not wide |
| ISL | long | 4 | 19 | 6 | threshold not wide, interval overlap, invalid rows |
| KTL | long | 4 | 41 | 10 | threshold not wide, interval overlap, invalid rows |
| LAR_AEL | long | 4 | 0 | 0 | threshold not wide |
| LAR_TCL | long | 4 | 0 | 0 | threshold not wide |
| TKL | long | 4 | 0 | 0 | threshold not wide |
| TKS | long | 4 | 0 | 0 | threshold not wide |
| TWL | long | 4 | 0 | 0 | threshold not wide |

## TL-BK Mapping

| Sheet | Rows | Invalid rows | Source unit |
|---|---:|---:|---|
| AEL UT | 1422 | 0 | km (source) -> m (canonical adapter) |
| AEL DT | 1491 | 0 | km (source) -> m (canonical adapter) |
| TCL UT | 1242 | 0 | km (source) -> m (canonical adapter) |
| TCL DT | 1247 | 0 | km (source) -> m (canonical adapter) |
| DRL UT | 223 | 5 | km (source) -> m (canonical adapter) |
| DRL PL | 86 | 0 | km (source) -> m (canonical adapter) |
| TWL UT | 1176 | 0 | km (source) -> m (canonical adapter) |
| TWL DT | 1192 | 1 | km (source) -> m (canonical adapter) |
| KTL UT | 1583 | 0 | km (source) -> m (canonical adapter) |
| KTL DT | 1652 | 0 | km (source) -> m (canonical adapter) |
| ISL UT | 676 | 4 | km (source) -> m (canonical adapter) |
| ISL DT | 824 | 4 | km (source) -> m (canonical adapter) |
| TKL UT | 639 | 0 | km (source) -> m (canonical adapter) |
| TKL DT | 659 | 0 | km (source) -> m (canonical adapter) |
| TKS UT | 170 | 0 | km (source) -> m (canonical adapter) |
| TKS DT | 183 | 0 | km (source) -> m (canonical adapter) |

## Next Actions

1. Review every `interval overlap` and `invalid rows` entry against the source workbook before editing.
2. Convert each runtime workbook threshold sheet to the approved TOV640-style wide schema while preserving source-row provenance.
3. Generate mapping sheets using `FromM`/`ToM`/`Bracket` names and retain source km values in the audit metadata.
