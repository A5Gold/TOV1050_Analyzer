# TOV1050 Metadata Candidate Validation

- Generated: 2026-10-23
- Candidate and source workbooks were read-only; no runtime workbook was modified.
- Canonical Chainage policy: source Km/startKM/endKM/Location values are converted to metres at the adapter boundary.

## Summary

- Raw source overlaps include superseded non-support intervals; candidate track overlaps describe the regenerated output.

| Line | Status | Findings | Raw source overlaps | Candidate track overlaps | Invalid source rows | Provenance missing |
|---|---|---:|---:|---:|---:|---:|
| ISL | pass | 0 | 12 | 0 | 0 | 0 |
| KTL | pass | 0 | 132 | 0 | 0 | 0 |
| LAR_AEL | pass | 0 | 0 | 0 | 0 | 0 |
| LAR_TCL | pass | 0 | 0 | 0 | 0 | 0 |
| TKL | pass | 0 | 0 | 0 | 0 | 0 |
| TKS | pass | 0 | 0 | 0 | 0 | 0 |
| TWL | pass | 0 | 0 | 0 | 0 | 0 |

## Findings

### ISL (pass)
- none
### KTL (pass)
- none
### LAR_AEL (pass)
- none
### LAR_TCL (pass)
- none
### TKL (pass)
- none
### TKS (pass)
- none
### TWL (pass)
- none

## Promotion Gate

Candidates with `fail` or `review_required` status remain review-only. Promote or write back a runtime workbook only after overlap, invalid-row, TL-BK mapping, and provenance findings are explicitly approved.
