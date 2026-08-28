# Wear Mainline Resolution and Visual Guides Design

**Date:** 2026-07-16
**Status:** Approved for implementation planning
**Branch:** `main`
**Baseline:** `c466577`

## 1. Purpose

This design delivers five related changes through three independently testable implementation phases:

1. Restrict Wear Calculator calculations to approved mainline tension lengths and resolve EAL section-transition measurements without weakening validation.
2. Make staged Wire Wear Records changes unambiguous and replace the Wear algorithm dialog with an operational explanation available from every feature tab.
3. Replace the iframe-based About visual guide with maintainable React content for operators and developers.

The implementation must preserve the existing Section-aware resolution, composite source signatures, canonical split geometry, preview-level resolution indexes, deterministic preview/save contracts, and tab-scoped Wear state.

## 2. Verified Evidence

### 2.1 Repository and risk

- The canonical checkout is `C:\Smart Maintanence\TOV640_Analyzer` on `main` at `c466577`.
- Existing deleted test fixtures, modified screenshots, metadata analysis outputs, and untracked artifacts are user work and must not be restored, cleaned, or removed.
- Codebase-memory classifies the direct dependencies of `build_cycle_preview`, `build_segment_coverage`, `resolve_canonical_tl`, `parse_chart_data_sheet`, `upload_wear`, `WearCalculatorView`, and `WearRecordsPanel` as CRITICAL, with many second-hop dependencies classified HIGH.
- Every production symbol must receive a fresh inbound impact trace before it is edited.

### 2.2 TML export

`docs/Wear Calculator_Database/2026-05-12_TML_Wear_Cycle.xlsx` contains:

- 164 Wear Records, all with canonical Track `UP` or `DN`.
- Cycle Coverage gaps made entirely from siding identities such as `MX`, `MD`, `CT`, `KX`, `X`, `27A`, and `101-103`.
- Examples include D1 at 75% with `MX7-MX11` gaps, U2 at 80% with `27A`, `CT2`, `EM1`, `MP24`, `MX4`, `MX5`, and `PT1`, and U3-U5 at 57.14% with only siding identities in Diagnostic Gaps.

This proves that siding metadata currently pollutes the coverage denominator and diagnostics even when result records happen to be mainline-only.

### 2.3 EAL report and metadata coordinates

Real-file API reproduction at the approved baseline gives:

| Report | Current result |
| --- | --- |
| EAL Mainline UP | HTTP 200, no unresolved measurement |
| EAL LOW S1 UP | HTTP 200, no unresolved measurement |
| EAL LMC UP | HTTP 200, no unresolved measurement |
| EAL RAC UP | HTTP 422 at chainage `111301.0`, raw TL `23, 25` |

The RAC report has 216 rows from `111301.0` through `111354.75`, all with raw composite TL `23, 25`. RAC metadata starts at `111355.0`, while EAL Mainline UP contains the exact source signature `23, 25` over `111264.0-111401.9`. At `111355.0`, normal RAC resolution resumes.

The Exception Report `ChartData` cells are numeric with General formatting. The retained raw `.datac` files form chainage from `KM + LOCATION`; their `Sequence` values are direction values `U` or `D`. The observed ranges do not support a fixed coordinate offset. A coordinate transformation would make currently valid later rows incorrect.

### 2.4 Live workbook identities

The live metadata workbooks contain formatting variants that the classifier must recognize without rewriting stored identifiers:

- TML includes `MX04`, `MX09`, `MX4`, and `MX9` forms.
- EAL includes unpadded `D1`, padded `H01`, alphanumeric `69B` and `70A`, and special mainline X values.
- EAL source rows may combine mainline and siding identities, for example `25, X21`.
- `Neutral Section` is an explicit siding identity and must be ignored.

The EAL and TML metadata workbooks are read-only inputs for this work and must not be modified.

## 3. Goals and Non-goals

### 3.1 Goals

- Include only approved mainline TL identities in Wear aggregation, result records, coverage, diagnostics, graphs, and exports.
- Keep valid mainline TLs even when their canonical Track is `Siding` because their physical intervals span both directions.
- Resolve the RAC approach-zone rows through an exact, auditable Section transition rule.
- Fail closed when a new or malformed TL identity is neither approved mainline nor approved siding.
- Make every staged mutation identifiable by color, icon, and Traditional Chinese text.
- Explain the current algorithm accurately to operators and developers.
- Preserve light/dark themes, keyboard use, mobile layouts, and existing business workflows.

### 3.2 Non-goals

- Do not widen metadata intervals.
- Do not select the nearest interval.
- Do not apply an inferred chainage offset.
- Do not add a general fallback to Mainline.
- Do not weaken true gap or ambiguity validation.
- Do not change canonical interval splitting or stored Track values.
- Do not modify EAL or TML metadata workbooks.
- Do not redesign unrelated application surfaces.
- Do not restore deleted test fixtures or remove analysis artifacts.

## 4. Phase A: Mainline TL Scope and Section Transition

### 4.1 Central classifier

Add a central domain classifier with this logical contract:

```text
classify_tension_length(line_group, tension_length)
  -> MAINLINE | SIDING | UNKNOWN
```

Matching normalization is private to the classifier:

- Trim surrounding whitespace and compare case-insensitively.
- Accept padded and unpadded numeric components for prefixed series, such as `MX09` and `MX9`.
- Preserve the existing canonical and displayed TL string. Classification must not rename database keys, export values, source signatures, or canonical geometry.
- Use fully anchored rules so that `D` cannot accidentally match `MD`, and `X` cannot accidentally match `HX` or `KX`.

Special cases are evaluated before general series rules.

### 4.2 Approved TML identities

#### TML mainline

| Family | Approved identities |
| --- | --- |
| M | M01-M33 |
| D | D01-D60 |
| U | U01-U55 |
| U slash variants | U07/1, U07/2, U08/1, U08/2, U31/1, U31/2, U36/1, U36/2 |
| K | K01-K16 |
| Numeric | 01-74 |

#### TML siding

| Family | Approved identities |
| --- | --- |
| MX | MX1-MX11, including zero-padded workbook forms |
| MD | MD1-MD22 |
| MP | MP24 |
| EM | EM1 |
| PT | PT1-PT2 |
| CT | CT1-CT3 |
| KX | KX1-KX7 |
| X | X01-X29 |
| W | W1-1 |
| Special numeric | 27A, 101, 102, 103 |
| Special text | Neutral Section |

### 4.3 Approved EAL identities

#### EAL mainline

| Family | Approved identities |
| --- | --- |
| H | H01-H52 |
| H suffix exceptions | H23D, H26D |
| D | D01-D31 |
| U | U01-U55 |
| U slash variants | U07/1, U07/2, U08/1, U08/2, U31/1, U31/2, U36/1, U36/2 |
| K | K01-K16 |
| Numeric | 1-76 |
| Verified numeric suffix exceptions | 69B, 70A |
| L | L01-L20 |
| T | T2, T3 |
| Special X | X36, X37, X50, X53, X54 |

#### EAL siding

| Family | Approved identities |
| --- | --- |
| HX | HX02 |
| X | X01-X39 except X36 and X37 |
| LX | LX followed by a positive integer |
| D exceptions | D32, D33 |
| EM | EM1 |
| Special text | Neutral Section |

The special mainline X set is evaluated before the general siding X rule. `X50`, `X53`, and `X54` are outside the general siding range and remain explicit mainline values.

### 4.4 Unknown identities

Any non-empty identity that matches neither the approved mainline table nor the approved siding table is `UNKNOWN`.

An unknown value blocks preview and save with a diagnostic containing:

- Line group.
- Metadata sheet and source row when available.
- Raw source signature.
- Unknown TL identity.

This is intentional fail-closed behavior. It exposes workbook drift instead of silently treating new infrastructure as siding.

### 4.5 Measurement resolution order

The resolver follows this order:

1. Normalize Line, Track, Section, Chainage, and raw composite TL tokens.
2. Run the existing strict Section-aware match using Track, Chainage, source bounds, source signature, and source priority.
3. If strict matching succeeds, keep the existing unique-primary selection behavior.
4. If strict matching has no match, attempt the constrained Section transition rule in section 4.6.
5. Classify the uniquely selected TL.
6. Continue only for `MAINLINE`.
7. Drop `SIDING` measurements before conflict generation, aggregation, accepted-source coverage, result records, and export.
8. Reject `UNKNOWN` with a diagnostic.

A mixed composite row is not discarded as a whole. The existing source-signature priority selects the physical TL first. For example, `25, X21` may select mainline `25`; a row whose primary selected TL is `X21` is siding and is ignored.

### 4.6 Constrained Section transition

Section transition is attempted only after a true strict-Section gap. It is not a general fallback.

Candidate rows must match all of these values exactly:

- Same line group.
- Same Track.
- Same original numeric Chainage.
- Full normalized composite source signature in the same order.
- Source bounds containing the original Chainage.

The transition succeeds only when those conditions identify one unique source row and one unique primary TL. The selected primary TL then passes through the scope classifier.

For the verified RAC example, the exact Mainline source row `23,25` at `111301.0` uniquely selects primary TL `23`. No coordinate change is made.

No match, multiple matching source rows, multiple primary TLs, or an unknown selected TL remains HTTP 422. Diagnostics retain filename, raw TL, report Section, Track, Chainage, and the transition failure reason.

### 4.7 Aggregation, coverage, and diagnostics

Mainline scope is applied consistently to:

- Candidate measurements.
- Conflict groups.
- Aggregated records.
- Accepted measurements used by segment coverage.
- Coverage denominator metadata.
- Coverage numerator identities.
- Expected TL lists.
- Diagnostic Gaps.
- Saved records and exported workbook rows.

The coverage formula remains:

```text
coverage_percent = round(100 * present_mainline_tls / expected_mainline_tls, 2)
```

Existing rules for missing segments, empty denominators, source range intersection, and advisory coverage remain unchanged.

### 4.8 Canonical Track and Analysis filters

TL scope and canonical Track are separate concepts.

- A mainline identity can retain canonical Track `Siding` when its canonical physical intervals contain both UP and DN geometry.
- Such a record remains a valid calculated result.
- Backend enums, persisted Track, canonical intervals, preview digest, and exports retain their existing contract.

The Analysis chart removes the `Siding` checkbox. UP and DN filtering uses the record's physical intervals:

- UP includes records with at least one UP physical interval.
- DN includes records with at least one DN physical interval.
- A mixed-direction mainline record appears when either applicable direction is selected.

This removes siding as a dataset concept without hiding valid mixed-direction mainline records.

## 5. Phase B: Staged Records and Algorithm Dialog

### 5.1 Design register

This is a repeated operational workflow for railway maintenance staff. Impeccable's product register is primary. The visual settings are:

- Wear UI: DESIGN_VARIANCE 3, MOTION_INTENSITY 2, VISUAL_DENSITY 7.
- Familiar MUI controls and the existing Railway Blue theme are preserved.
- Motion communicates state only. No decorative animation is added.

### 5.2 Staged-state visual contract

The Zustand staged-change model remains authoritative. Presentation maps each existing kind to a semantic visual state:

| Change kind | Traditional Chinese label | Icon role | Visual treatment |
| --- | --- | --- | --- |
| `add` | 待新增 | Add | Orange-tinted background, orange border, strong orange text |
| `edit` | 待修改 | Edit | Orange-tinted background, orange border, strong orange text |
| `delete_cell` | 待刪除 | Delete | Orange treatment plus retained value and strikethrough |
| `delete_row` | 整列待刪除 | Delete row | Continuous orange row treatment; label in Cycle Date cell |

Rules:

- Use the active MUI theme's `warning` tokens and `alpha()` rather than hard-coded `warning.50`.
- Calibrate background, border, text, hover, and focus separately for light and dark themes.
- Never encode staged meaning by color alone.
- Use the existing MUI icon family.
- Preserve focus visibility for the cell and its delete action.
- Preserve Enter and Space activation, double-click edit, hover/focus delete visibility, touch overflow actions, Save Changes, Discard Changes, and failed-save retention.
- When an add creates a new cycle-date row, mark the Cycle Date cell and the added record cell as pending add.

### 5.3 Pending legend and summary

Add a compact legend adjacent to the Historical Avg Wear Min heading with icons and labels for 待新增, 待修改, and 待刪除.

Keep the bottom pending action bar, but:

- Translate the pending summary to Traditional Chinese.
- Give it `role="status"` and an appropriate live region.
- Keep the existing save and discard commands.
- Preserve pending state after a failed save.

### 5.4 Shared algorithm entry point

Move the algorithm action out of the Analysis-only calculation tab bar and into the feature-level toolbar shared by:

- Analysis.
- 線耗紀錄.
- Dashboard.
- Projection.

Use an information icon plus the visible label `線耗計算邏輯`. The action opens the same dialog from every feature tab and does not modify the active analysis tab or staged-record navigation guard.

### 5.5 Algorithm dialog information architecture

The dialog is an operational explanation with three sections:

1. 輸入與分類.
2. 解析與計算.
3. 覆蓋率與保存.

It must explain the real order of operations:

- File and segment detection.
- Section and Track validation.
- Strict resolution and constrained Section transition.
- MAINLINE continuation, SIDING ignore, and UNKNOWN block.
- Identity de-duplication, lower-value conflict selection, conflict acceptance, and aggregation.
- Mainline-only coverage.
- Save gates and atomic persistence.
- Staged record changes.

Presentation uses unframed flow bands, a decision table, status examples, threshold tables, and small diagrams. It must not become a grid of nested cards.

All user-facing prose is Traditional Chinese. Technical identifiers such as `Section`, `Track`, `Chainage`, `source signature`, `preview_digest`, and `data_version` may remain English.

Desktop uses a wide scrolling dialog with a sticky title bar. Mobile uses a full-screen dialog. The close action has an accessible name. MUI supplies focus trapping and Escape behavior.

## 6. Phase C: React About Visual Guide

### 6.1 Runtime architecture

`AboutView` becomes a native React surface. It no longer loads guide HTML through an Electron IPC bridge or renders it in an iframe.

The existing `docs/tov640-analyzer-visual-guide.html` file is retained as a legacy artifact so user work is not deleted, but it is no longer the runtime or maintenance source of truth. New guide content lives in focused React components and structured content modules.

The implementation may remove obsolete runtime IPC and packaging references only after impact analysis confirms no remaining caller. That cleanup must be a separate commit from the React guide.

### 6.2 Design register

The About guide is a preserved product redesign, not a landing page:

- DESIGN_VARIANCE 5.
- MOTION_INTENSITY 3.
- VISUAL_DENSITY 6.
- Existing MUI theme, Railway Blue accent, six-pixel radius, and semantic status colors remain.
- No marketing hero, decorative card wall, gradient text, glass effects, or ornamental animation.

### 6.3 Primary tabs

The page has two primary tabs:

#### 操作指南

This is the default and follows the operator workflow:

1. Import raw measurements and Exception Reports.
2. Align metadata, Section, Track, and Chainage.
3. Run Threshold, Repeat, 1 Year, Wear, Trend, and Stagger decisions.
4. Preview conflicts and coverage.
5. Save, export, or diagnose a rejected result.

Meaningful visuals include:

- Threshold range chart with real threshold values.
- Repeat-chain timeline.
- One-year comparison window.
- Wear resolution decision flow.
- Mainline-only coverage numerator and denominator example.
- Staged-change status example.
- Stagger span scenario.

Any invented values are explicitly labelled `示例`. Every chart has a textual or tabular equivalent.

#### 開發者參考

This tab includes:

- Electron, React/Zustand, API client, FastAPI routes, core services, SQLite, and config workbook architecture.
- API and state-ownership matrix.
- End-to-end data flows for analysis, comparison, Wear, Trend, and Stagger.
- Section-aware resolution, composite source signatures, canonical split geometry, and preview-level indexes.
- Deterministic preview digest, data version, conflict audit, atomic save, tab-scoped state, and staged change set.
- Error taxonomy and required diagnostics.
- Test-layer and real-fixture regression matrix.
- Active Database Path and packaging diagnostics.

### 6.4 Components and maintainability

Create a focused About guide component boundary rather than one large view. Expected responsibilities are:

- Page shell and primary tabs.
- Operator workflow navigation.
- Reusable flow and decision visuals.
- Algorithm-specific content sections.
- Developer architecture and contract sections.
- Diagnostics status panel.
- Structured algorithm content and source references.

The exact filenames are decided in the implementation plan, but no component should duplicate backend business logic. The guide documents verified contracts; backend code and tests remain authoritative.

### 6.5 Responsive and accessible behavior

- Desktop uses a compact section navigator and a wide content column.
- Below the existing mobile breakpoint, layouts become one column and tabs remain horizontally scrollable.
- Loading diagnostics uses a skeleton matching the final panel.
- Diagnostics failure does not hide the guide; the error stays inside the developer diagnostics section.
- Headings remain semantic and sequential.
- Tabs expose their selected state and keyboard behavior.
- Charts expose summaries and tables.
- Light and dark themes preserve hierarchy and WCAG AA contrast.

## 7. Error Handling

### 7.1 Blocking backend errors

The following remain blocking:

- Unknown TL identity.
- Invalid Line, Section, Track, Chainage, source bounds, or source signature.
- True measurement gap after constrained transition.
- Multiple exact transition rows.
- Multiple primary TLs.
- Unaccepted data conflict.
- Invalid cycle date.
- Missing required segment.

Errors identify the source filename and the smallest actionable context. No exception is converted into a silent fallback.

### 7.2 Non-blocking exclusions

Approved siding measurements and metadata are expected exclusions, not errors. They do not appear in results, coverage, Expected TLs, Diagnostic Gaps, graphs, saves, or exports.

### 7.3 Frontend errors

- Failed staged saves retain pending styles and actions.
- Failed diagnostics leave About content available.
- Loading and empty states preserve stable layout dimensions.
- Error copy is Traditional Chinese except raw backend technical details.

## 8. Testing and Acceptance

### 8.1 Backend focused tests

Add table-driven classifier tests for:

- Every approved family boundary.
- Padded and unpadded forms.
- TML `27` versus `27A`.
- EAL `D31` versus `D32` and `D33`.
- EAL special X mainline values versus general siding X values.
- TML `D` versus `MD`.
- TML `X` versus `MX` and `KX`.
- Cross-line identities such as numeric suffix values.
- `Neutral Section` as siding.
- Unknown values as blocking.
- Valid mainline identities with canonical Track `Siding`.

Add resolver and API tests for:

- Strict Section success.
- Exact Section transition success.
- Transition with no exact signature.
- Transition collision.
- True gap.
- True ambiguity.
- Siding primary exclusion.
- Unknown primary rejection.

### 8.2 Real-file backend matrix

Use present repository files where available:

- EAL Mainline.
- EAL RAC UP with `111301.0 / 23,25`.
- EAL LOW S1.
- EAL LMC.
- TML complete cycle and the supplied exported workbook as an output reference.

Deleted historical fixtures remain deleted. The final report lists any acceptance case that cannot run because its fixture is unavailable. Representative synthetic tests cover the same contract without restoring files.

### 8.3 Frontend tests

Vitest interaction tests cover:

- Staged cell edit.
- Add into an existing row.
- Add creating a new row.
- Cell delete.
- Row delete.
- Legend and pending summary.
- Light and dark semantic tokens.
- Keyboard edit and delete access.
- Failed-save retention.
- Shared algorithm entry from all four feature tabs.
- Dialog sections and Traditional Chinese content.
- About operator/developer tabs.
- Diagnostics loading, success, and failure.
- Responsive component behavior where unit-testable.

Run the full frontend suite in shards because an unsharded Windows run can exceed ten minutes.

### 8.4 Browser verification

Start the canonical root development server with `NODE_USE_SYSTEM_CA=1` set for the process. Do not bypass the root scripts.

Playwright verifies:

- Real EAL Mainline, RAC, LOW S1, and LMC browser workflows.
- Real TML complete-cycle workflow.
- Mainline-only coverage and absence of siding gaps.
- Analysis charts without a Siding filter.
- Mixed-direction mainline chart visibility.
- Staged add, edit, cell delete, and row delete.
- Algorithm dialog from all four feature tabs.
- About operator and developer tabs.
- Desktop and mobile screenshots.
- Light and dark theme screenshots.
- No overlap, clipped text, blank charts, or inaccessible focus states.

### 8.5 Full verification

- Backend focused pytest.
- Full backend pytest.
- Full frontend Vitest in shards.
- ESLint.
- TypeScript and production build.
- Playwright real-file workflows and screenshots.
- `git diff --check` and final status review.
- Codebase-memory re-index after committed production changes.
- Final affected-scope verification through graph queries and inbound traces.

Every `npm`, `npx`, or `npm exec` command sets `NODE_USE_SYSTEM_CA=1` for that process. TLS verification remains enabled.

## 9. Development Phases, Subagent, and Commits

### 9.1 Required subagent

Phase A requires at least one subagent. The subagent owns a new, isolated backend test file for classifier collisions and real-file regression coverage, plus an independent review of the production classifier contract. The primary agent owns production code and integration tests. They do not edit the same file concurrently.

Additional subagent work may be used for a bounded About accessibility review, but Phase A already satisfies the required development delegation.

### 9.2 Narrow commit sequence

Planned commit boundaries are:

1. Design specification.
2. Central TL scope classifier and table-driven tests.
3. Mainline-only aggregation and coverage integration.
4. Exact Section transition resolver and real-file regressions.
5. Analysis direction filters and removal of the Siding filter.
6. Staged Wire Wear Records semantics and tests.
7. Shared algorithm entry and redesigned dialog.
8. React About guide.
9. Obsolete iframe IPC/package cleanup, only if verified unused.

Each commit stages only its own files. Existing user changes and artifacts remain unstaged unless they are explicitly part of the approved change.

### 9.3 Phase completion gates

Phase A completes only when backend focused tests, real-file regressions, Analysis frontend tests, and the affected browser workflows pass.

Phase B completes only when staged operation tests, dialog access tests, light/dark checks, keyboard checks, and desktop/mobile screenshots pass.

Phase C completes only when About tests, diagnostics states, responsive screenshots, full frontend verification, and the production build pass.

The final response reports exact commit hashes, test results, unavailable fixtures, codebase-memory affected scope, and residual risks.

## 10. Risks and Mitigations

| Risk | Mitigation |
| --- | --- |
| A regex misclassifies a colliding family | Anchored, table-driven family rules and explicit collision tests |
| Workbook formatting changes create a silent exclusion | `UNKNOWN` fail-closed diagnostics |
| Section transition becomes a Mainline fallback | Require strict gap, exact full signature, original coordinate, and one unique source row |
| Siding filtering removes mixed-direction mainline records | Classify by line-specific TL identity, never canonical Track |
| Coverage and result filtering diverge | Apply one classifier at shared backend boundaries and test every consumer |
| Dialog or About content drifts from code | Structured content modules, source references, and contract tests for key wording |
| React About migration breaks packaged Electron | Separate runtime migration from IPC cleanup and run production build/package-path tests |
| User artifacts are accidentally staged | Explicit file lists, status checks before every commit, and no cleanup commands |

## 11. Approved Decisions

- Use one umbrella specification with three independent implementation phases.
- Use the contract-first React approach.
- Treat `Neutral Section` as siding.
- Treat all other unrecognized TL identities as blocking unknown values.
- Use constrained exact Section transition for the RAC approach zone.
- Do not transform chainage coordinates.
- Preserve canonical Track `Siding` for valid mixed-direction mainline TLs.
- Use Impeccable product patterns for operational UI and Taste guidance only for hierarchy, spacing, typography, rhythm, and the About guide.
- Require at least one subagent during Phase A development.
- Preserve all current user changes, deleted fixtures, screenshots, workbooks, and analysis artifacts.
