# TOV1050 Metadata Candidate Validation

- Generated: 2026-10-23
- Candidate and source workbooks were read-only; no runtime workbook was modified.
- Canonical Chainage policy: source Km/startKM/endKM/Location values are converted to metres at the adapter boundary.

## Summary

- Raw source overlaps include superseded non-support intervals; candidate track overlaps describe the regenerated output.

| Line | Status | Findings | Raw source overlaps | Candidate track overlaps | Invalid source rows | Provenance missing |
|---|---|---:|---:|---:|---:|---:|
| ISL | review_required | 3 | 12 | 0 | 0 | 0 |
| KTL | review_required | 2 | 132 | 0 | 0 | 0 |
| LAR_AEL | review_required | 1 | 1 | 0 | 0 | 0 |
| LAR_TCL | review_required | 1 | 1 | 0 | 0 | 0 |
| TKL | pass | 0 | 0 | 0 | 0 | 0 |
| TKS | pass | 0 | 0 | 0 | 0 | 0 |
| TWL | pass | 0 | 0 | 0 | 0 | 0 |

## Findings

### ISL (review_required)
- `review` `outer_non_support_review`: `{"sheet": "UT track type", "rows": [{"source_row": 2, "label": "non-support", "start": 97.0, "end": 97.2619}]}`
- `review` `support_anchor_review`: `{"sheet": "DT track type", "issues": [{"code": "invalid_support_anchor", "source_row": 298, "label": "Support", "start": 99126.0, "end": 99126.0, "reason": "Support is outside the source location envelope (including ORCR); check units/value"}]}`
- `review` `outer_non_support_review`: `{"sheet": "DT track type", "rows": [{"source_row": 2, "label": "non-support", "start": 97.0, "end": 97.7809}]}`
### KTL (review_required)
- `review` `outer_non_support_review`: `{"sheet": "UT track type", "rows": [{"source_row": 2, "label": "non-support", "start": 97.0, "end": 98.0519}, {"source_row": 432, "label": "non-support", "start": 99.8771, "end": 99.942}]}`
- `review` `outer_non_support_review`: `{"sheet": "DT track type", "rows": [{"source_row": 2, "label": "non-support", "start": 97.0, "end": 97.4099}]}`
### LAR_AEL (review_required)
- `review` `source_interval_review`: `{"sheet": "location type", "report": {"source_sheet": "location type", "headers": ["location type", "startKM", "endKM"], "unit": "km", "valid_row_count": 6, "invalid_rows": [], "overlap_count": 1, "touching_count": 0, "ambiguous_overlap_count": 0, "ambiguous_overlap_examples": [], "reversed_row_count": 0, "reversed_rows": [], "overlap_examples": [{"label": "Open", "previous_source_row": 2, "current_source_row": 3, "previous_start": 24.0, "previous_end": 28.3099, "current_start": 28.301, "current_end": 33.198899999999995, "overlap_m": 8.9, "previous_length_m": 4309.9, "current_length_m": 4897.9}], "overlap_examples_complete": true}}`
### LAR_TCL (review_required)
- `review` `source_interval_review`: `{"sheet": "location type", "report": {"source_sheet": "location type", "headers": ["location type", "startKM", "endKM"], "unit": "km", "valid_row_count": 6, "invalid_rows": [], "overlap_count": 1, "touching_count": 0, "ambiguous_overlap_count": 0, "ambiguous_overlap_examples": [], "reversed_row_count": 0, "reversed_rows": [], "overlap_examples": [{"label": "Open", "previous_source_row": 2, "current_source_row": 3, "previous_start": 24.0, "previous_end": 28.3099, "current_start": 28.301, "current_end": 33.198899999999995, "overlap_m": 8.9, "previous_length_m": 4309.9, "current_length_m": 4897.9}], "overlap_examples_complete": true}}`
### TKL (pass)
- none
### TKS (pass)
- none
### TWL (pass)
- none

## Promotion Gate

Candidates with `fail` or `review_required` status remain review-only. Promote or write back a runtime workbook only after overlap, invalid-row, TL-BK mapping, and provenance findings are explicitly approved.
