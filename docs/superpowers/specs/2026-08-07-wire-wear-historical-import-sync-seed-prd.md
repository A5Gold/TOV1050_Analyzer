# Wire Wear Historical Import, Batch Entry, Sync, and Portable Seed

## Problem Statement

Maintenance engineers already have approximately one hundred historical
average wire wear minimum cycles for EAL, TML, and LMC in a workbook. The
workbook is a monthly matrix: each row identifies a Track and Tension Length,
and each remaining column identifies a measurement month. Entering those
measurements one by one is too slow and makes transcription errors likely.

The current Wire Wear Records workbench supports staged record changes, history,
latest summary, dashboard, projection, and SQLite persistence, but it has no
user-facing historical workbook importer and its Add Record interaction accepts
only one Tension Length at a time. Existing Wire Wear data-package APIs and
frontend store actions are not wired into a complete preview and conflict
resolution workflow.

Development and portable builds also use separate SQLite databases. Data loaded
while running the development application is therefore not automatically
included as the approved initial dataset in a later portable build. Copying the
complete development database would risk publishing unrelated or test data and
could overwrite another user's local records.

The normalized staged workbench currently persists only EAL or TML line groups
and identifies a record by line group, cycle date, and Tension Length. This is
insufficient for the approved first-phase requirement that EAL, TML, and LMC
remain independently selectable and durable. LMC belongs to the EAL line group
but requires its own persisted line class.

## Solution

Users will be able to upload the historical workbook, select the supported EAL,
TML, and LMC sheets, inspect a cell-level preview, and see every candidate
classified as New, Update, No Change, or Error. Valid additions and updates will
enter the existing staged-change workflow only after confirmation. The normal
Save Changes action remains the commit boundary, and the full batch is written
atomically after a SQLite backup is created.

Add Records will become a batch-entry workflow with one shared line/class and
cycle date plus a grid of Tension Length and average wear minimum rows. Users
can type rows, add or remove rows, or paste two columns from Excel. The same
normalization, validation, database comparison, and staging rules will be used
for workbook import and manual batch entry.

The normalized Wire Wear domain will persist line class. EAL records use line
group EAL and line class EAL; LMC records use line group EAL and line class LMC;
TML records use line group TML and line class TML. The business key, change
operations, tombstones, workbench queries, sync package, seed package, API
contracts, and frontend state will all retain this identity.

Wire Wear data sharing will use one versioned data-package contract with a
preview/apply lifecycle. Users will see New, Update, Keep Local, No Change,
Conflict, and Delete actions before import. Conflicts require an explicit
choice. Confirmed import creates a backup and applies atomically.

A developer-only seed command will export committed Wire Wear data into the
existing packaged configuration resource chain. A portable application will
load that seed only when its normalized Wire Wear dataset is empty. Each
portable directory then owns an independent SQLite database that is never
overwritten by later seed initialization.

LRL remains visible as a reserved future workbook adapter but is not imported,
stored, displayed, graphed, or used in formulas during this phase.

## User Stories

1. As a maintenance engineer, I want to upload the historical wear workbook, so that I do not have to enter approximately one hundred cycles manually.
2. As a maintenance engineer, I want the importer to recognize EAL, TML, and LMC sheets, so that all approved first-phase datasets can be loaded together.
3. As a maintenance engineer, I want supported sheets selected by default, so that the common import path requires minimal setup.
4. As a maintenance engineer, I want to deselect an individual supported sheet, so that I can import only the dataset I intend to change.
5. As a maintenance engineer, I want LRL shown as reserved and disabled, so that I understand the workbook was recognized without assuming it was imported.
6. As a maintenance engineer, I want unknown workbook sheets shown as ignored, so that unrelated sheets do not block valid data.
7. As a maintenance engineer, I want month columns parsed by their YYYYMM headings, so that an unsorted TML column sequence is still imported correctly.
8. As a maintenance engineer, I want YYYYMM stored consistently as the first day of that month, so that monthly history has a stable database date.
9. As a maintenance engineer, I want blank cells treated as missing measurements, so that sparse historical matrices import normally.
10. As a maintenance engineer, I want a cell containing only a period treated as a missing measurement, so that the existing workbook convention does not create false errors.
11. As a maintenance engineer, I want other non-numeric values reported as errors, so that invalid wear data cannot enter the database silently.
12. As a maintenance engineer, I want Track values normalized consistently, so that UP and DOWN variations do not create accidental categories.
13. As a maintenance engineer, I want Tension Length identifiers preserved as text, so that leading zeroes, letters, and suffixes remain meaningful.
14. As a maintenance engineer, I want every invalid value tied to its sheet and cell address, so that I can repair the source workbook quickly.
15. As a maintenance engineer, I want a downloadable error report, so that I can work through a large set of workbook corrections outside the application.
16. As a maintenance engineer, I want the preview to distinguish New, Update, No Change, and Error records, so that I understand the exact effect before staging.
17. As a maintenance engineer, I want existing and imported values shown for updates, so that overwrites are auditable.
18. As a maintenance engineer, I want unresolved errors to block confirmation, so that the application cannot create an unnoticed partial import.
19. As a maintenance engineer, I want to explicitly exclude an error row when appropriate, so that a known bad source row does not prevent an otherwise valid import.
20. As a maintenance engineer, I want confirmed workbook data staged rather than immediately saved, so that it participates in the existing review and discard workflow.
21. As a maintenance engineer, I want No Change records excluded from staged changes, so that a repeat import remains clean and understandable.
22. As a maintenance engineer, I want all staged workbook changes saved in one transaction, so that a failure cannot leave a partly imported cycle.
23. As a maintenance engineer, I want a database backup before a workbook batch is saved, so that a large overwrite can be recovered.
24. As a maintenance engineer, I want to add multiple Tension Length measurements under one line/class and cycle date, so that routine manual entry is fast.
25. As a maintenance engineer, I want to paste Tension Length and average wear minimum columns from Excel, so that I can reuse prepared measurements directly.
26. As a maintenance engineer, I want cell-level validation in the batch-entry grid, so that I can correct mistakes before staging.
27. As a maintenance engineer, I want one Stage All action for a valid batch, so that I do not repeat the same confirmation for every Tension Length.
28. As a maintenance engineer, I want EAL, LMC, and TML to remain distinct in the workbench, so that their histories and summaries cannot be mixed accidentally.
29. As a maintenance engineer, I want imported records to appear in History and Latest Summary, so that the workbook becomes immediately useful for engineering review.
30. As a maintenance engineer, I want imported records to feed the existing supported Dashboard and Projection calculations, so that I do not maintain a separate historical-data workflow.
31. As a user sharing data, I want to export only Wire Wear data, so that unrelated analysis records are not included.
32. As a user receiving data, I want to preview an imported package, so that another computer cannot change my database without review.
33. As a user receiving data, I want newer incoming records identified as updates, so that recent work can be applied efficiently.
34. As a user receiving data, I want newer local records kept by default, so that an older package cannot silently replace my work.
35. As a user receiving data, I want identical records reported as No Change, so that repeated package imports are idempotent.
36. As a user receiving data, I want equal-time conflicting values presented side by side, so that I can choose the authoritative value.
37. As a user receiving data, I want deletions represented explicitly, so that records deleted on another computer are not silently recreated.
38. As a user receiving data, I want every conflict resolved before import, so that the system never guesses how to merge ambiguous records.
39. As a user receiving data, I want the application to back up SQLite before applying a package, so that I can recover from an incorrect decision.
40. As a user receiving data, I want package import to roll back completely on failure, so that the database remains internally consistent.
41. As a release developer, I want an explicit seed-generation command, so that only an intentionally approved snapshot enters a portable build.
42. As a release developer, I want seed generation to ignore unsaved frontend changes, so that the portable dataset contains committed records only.
43. As a release developer, I want the build to package the seed through the existing configuration resource mechanism, so that backend resource resolution remains consistent.
44. As a new portable user, I want EAL, LMC, and TML records available on first launch, so that the application does not begin with an empty historical database.
45. As an existing portable user, I want startup to skip the seed when records already exist, so that an update never overwrites my local work.
46. As a portable user, I want my database independent from the development database and other portable copies, so that edits remain local to my installation.
47. As a maintenance engineer, I want the import and batch dialogs to remain usable with large datasets, so that table growth does not move or overlap the primary actions.
48. As a keyboard user, I want predictable grid navigation and accessible controls, so that batch entry does not require repeated mouse interaction.
49. As an existing user, I want current edit, delete, export, chart, summary, dashboard, and projection workflows to keep working, so that the new feature does not regress established tasks.
50. As a developer testing a release, I want an explicit reminder to generate the approved seed before packaging, so that a portable build is not accidentally shipped empty.
51. As the lead developer, I want development split into bounded subagent assignments after shared contracts are fixed, so that parallel work reduces elapsed time without creating overlapping edits.

## Implementation Decisions

### Normalized Wire Wear identity

- Line group remains the physical route grouping and continues to allow EAL or
  TML.
- A required line class is added to the normalized cycle domain and allows EAL,
  LMC, or TML.
- The supported combinations are EAL/EAL, EAL/LMC, and TML/TML.
- The normalized business key becomes line group, line class, cycle date, and
  Tension Length.
- Cycle ownership, records, tombstones, preview actions, staged operations,
  optimistic concurrency, workbench queries, summaries, sync packages, and
  seed packages must preserve the complete business key.
- Existing normalized EAL records migrate to line class EAL. Existing normalized
  TML records migrate to line class TML.
- The migration must preserve record timestamps, parent-cycle status, lineage,
  tombstones, and data-version semantics.
- The workbench's user-facing EAL selection queries EAL/EAL, LMC queries
  EAL/LMC, and TML queries TML/TML.
- Canonical Tension Length metadata resolution receives line-class context so
  LMC records cannot resolve against the wrong EAL class while still reusing
  the established EAL physical-route grouping.

This is a CRITICAL-impact domain change. It must be completed and regression
tested before importer, sync, and seed integration rely on the expanded key.

### Historical workbook preview

- One historical-workbook preview service is the primary backend seam.
- It accepts workbook bytes, selected sheets, current metadata, and the current
  committed data version.
- It returns a deterministic preview containing normalized candidates, skipped
  counts, per-sheet totals, source locations, existing/imported values,
  expected record timestamps, and status/reason codes.
- EAL, TML, and LMC use source adapters that handle only source-specific matrix
  parsing. Shared validation and comparison remain outside the adapters.
- TML headings are parsed by value rather than physical order.
- LRL has a registered but disabled capability entry and cannot produce
  candidates in this phase.
- A numeric matrix cell creates a candidate. Blank cells and period-only cells
  increment skipped counts. Other non-numeric cells create errors.
- Equal duplicate source keys collapse with a notice. Different values under
  the same source key create an error.
- Track is trimmed and normalized to UP or DOWN. Tension Length is trimmed but
  otherwise remains text.
- Domain-invalid or non-finite wear values create errors using the existing
  Wear Calculator validation rules.
- New and Update candidates contain the complete staged operation inputs.
  Update candidates include the expected stored timestamp for optimistic
  concurrency.
- The preview includes the committed data version. Saving after the database
  has changed must fail as stale rather than applying an outdated preview.

### Batch staging and atomic save

- The frontend store gains one batch-staging operation that merges all selected
  candidates in one state transition.
- Batch staging reuses the existing staged-change coalescing and optimistic
  matrix derivation rather than maintaining a second pending-change model.
- Workbook candidates retain provenance at batch level so Save Changes can
  request the required pre-write backup.
- The backend wraps the existing atomic change-set operation with a backup-aware
  application service. The existing change-set transaction remains the record
  mutation boundary.
- Backup creation must succeed before an Excel-originated change set begins.
- Manual batch entry uses the same candidate validator and classifier, but it
  is not treated as a workbook-originated backup requirement unless product
  policy is expanded later.
- No Change rows are never converted to staged operations.
- Excluded error rows remain in the preview audit but are not staged.

### Batch Add Records user experience

- Add Record becomes Add Records and opens a wide operational dialog.
- One line/class selector and one cycle-date input apply to all grid rows.
- The line/class choices are EAL, LMC, and TML, mapped to the supported line
  group and line class combinations.
- Each row contains Tension Length, average wear minimum, status, and a delete
  action.
- The grid supports row insertion, row deletion, keyboard navigation, and
  two-column paste.
- Inline messages identify the exact invalid cell.
- The footer reports valid, update, duplicate, and error counts.
- Stage All is disabled while any non-excluded error remains.
- Responsive layout keeps primary actions fixed and converts to a full-screen
  dialog on narrow viewports.

### Excel import user experience

- The Wire Wear Records toolbar exposes Add Records and Import Excel as primary
  actions.
- Import Excel uses Select, Preview, and Confirm & Stage phases.
- Supported sheets are selected by default and may be deselected.
- LRL is visible, disabled, and labelled as future support.
- Unknown sheets are visible as ignored.
- Preview filters are All, New, Update, No Change, and Error.
- Errors show sheet, cell address, original value, and actionable reason.
- The user can download an error report.
- Confirm & Stage is disabled until all errors are corrected or explicitly
  excluded.
- Completing Stage returns to the existing workbench and Save Changes flow.

### Versioned Wire Wear data packages

- The product uses one normalized `wear-cycle-v1` package family for export,
  preview, apply, and portable seed data.
- The legacy direct-import path that writes without a user preview is no longer
  used by the frontend and must not be extended for this feature.
- Export includes normalized cycles, records, conflict decisions, tombstones,
  package version, export timestamp, application version when available,
  source identity when available, metadata fingerprint, and row timestamps.
- Preview validates the complete package before returning actions.
- Preview actions are New, Update, Keep Local, No Change, Conflict, Error, and
  Delete. Delete represents an accepted incoming tombstone.
- Imported-newer records default to Update. Local-newer records default to Keep
  Local. Equivalent records become No Change.
- Equal-time content differences become Conflict and require an explicit local
  or incoming resolution.
- Apply accepts the preview digest, expected data version, and explicit conflict
  decisions. A changed digest or stale version stops the operation.
- Backup creation is added before sync apply. Failure to create the backup stops
  the import.
- Sync apply remains one transaction and includes deletion/tombstone behavior.
- Automatic SQLite backups retain the latest ten files. User-exported packages
  are not subject to automatic backup retention.
- Package import is blocked while unsaved workbench changes exist.

### Seed generation and portable initialization

- A developer-only `npm run wear:seed` command exports committed normalized
  Wire Wear data as a versioned `wear-cycle-v1` seed.
- Seed generation reads the development SQLite database but includes only Wire
  Wear domain data and required metadata fingerprints, not unrelated analysis
  tables.
- Seed generation excludes frontend staged changes because they are not
  committed database state.
- The seed is written into the repository's existing configuration-resource
  source and is packaged through the existing extra-resources rule. A second
  resource root is not introduced.
- Startup runs schema migrations before seed initialization.
- Seed initialization checks the normalized Wire Wear dataset, not the legacy
  table.
- An empty normalized dataset imports the seed transactionally. A non-empty
  normalized dataset skips initialization.
- Seed import failure rolls back, leaves the database usable, and reports the
  problem without preventing unrelated application modules from starting.
- Reopening or upgrading the application never reapplies the seed over existing
  data.
- Each portable directory continues to use its own writable data database.

### API and frontend contracts

- Public API models add line class wherever a normalized business key or
  record identity is exchanged.
- Historical preview accepts a multipart workbook and selected sheet list and
  returns a deterministic preview contract.
- Change-set apply accepts the expanded business key, expected timestamps,
  expected data version, and workbook backup provenance when applicable.
- Sync export, preview, and apply use the normalized versioned package contract.
- Sync apply accepts explicit conflict resolutions and returns backup path,
  applied action counts, and the resulting data version.
- Frontend types map wire-format names to application naming at the API client
  boundary.
- The Wire Wear store owns preview state, batch staging, backup provenance,
  pending-change guards, sync preview state, and apply summaries.
- The Records workbench owns toolbar actions and dialog orchestration while
  keeping table and summary components focused on display and row interaction.

### Error handling and recovery

- Parsing and preview are read-only operations.
- Structured error codes are used internally; UI messages remain actionable
  and source-specific.
- Workbook structure errors identify the affected sheet or heading.
- Data errors identify the affected source cell and original value.
- Backup failure prevents any database mutation.
- Change-set, sync, and seed writes use explicit transaction boundaries and
  roll back completely on failure.
- Stale record timestamps, stale data versions, and changed preview digests are
  reported distinctly so users know they must refresh rather than repair the
  workbook.
- Successfully created backups remain available even when the subsequent apply
  fails.

### Subagent development model

- Shared domain and API contracts are fixed by the primary agent before
  parallel implementation begins.
- First-wave Backend Import subagent work is limited to the new historical
  importer core, adapters, fixtures, and focused tests.
- First-wave Persistence and Sync subagent work is limited to shared backup,
  sync resolution, seed core, and focused tests.
- First-wave Frontend UX subagent work is limited to new presentational dialogs,
  grids, and component tests without editing shared store or API contracts.
- The primary agent retains ownership of migration integration, shared API
  models, API client mappings, the central Wire Wear store, workbench shell,
  package configuration, and final regression verification.
- Second-wave wiring begins only after first-wave contracts and tests are
  reviewed. Shared hotspot files are edited sequentially by one owner.
- Each subagent performs codebase impact analysis before editing symbols and
  reports focused commits or a clean diff for primary-agent integration.
- Existing unrelated worktree changes are preserved and never reverted.

## Testing Decisions

Tests assert externally observable behavior at the highest practical seam.
They do not assert private helper calls, component implementation structure, or
incidental database query order. Small pure tests are reserved for matrix edge
cases that would make API scenarios unreadable.

### Primary backend seam

- Historical workbook behavior is primarily tested through the preview service
  and its API using in-memory XLSX fixtures and a temporary migrated SQLite
  database.
- One scenario can therefore cover adapter parsing, normalization, domain
  validation, database comparison, source diagnostics, and the public preview
  response.
- Apply scenarios continue through the public change-set API and assert the
  resulting committed database state, backup creation, data-version change,
  and rollback behavior.
- Prior art is the existing FastAPI TestClient setup, temporary DatabaseManager
  configuration, change-set stale-timestamp tests, workbench contract tests,
  and in-memory Excel fixture builders.

Historical preview coverage includes:

- EAL, TML, and LMC matrices.
- Unsorted TML month headings.
- YYYYMM to first-of-month conversion.
- Blank and period-only skip counts.
- Track normalization.
- Tension Length text preservation.
- Invalid heading, missing column, invalid track, and invalid numeric value.
- Equal and conflicting duplicate source keys.
- New, Update, No Change, and Error classification.
- Exact source sheet and cell diagnostics.
- Expanded line-class business keys.
- Stale database version between preview and save.

### Persistence and migration seam

- Migration tests start from representative pre-line-class normalized schemas
  and assert preserved records, parents, tombstones, timestamps, and versions.
- Change-set tests assert atomic add/edit/delete operations under the expanded
  key and optimistic concurrency.
- Backup-aware apply tests assert that backup happens before mutation, backup
  failure prevents mutation, and operation failure rolls back the complete
  change set.
- Prior art is the existing migration, atomic change-set rollback, tombstone,
  metadata resolution, and data-version test suites.

### Sync seam

- Existing normalized sync preview/apply is extended rather than replaced.
- Tests cover exact package schema, package version rejection, metadata
  fingerprint warnings, new/update/keep-local/no-change/conflict/error/delete
  actions, explicit conflict decisions, stale digest, stale data version,
  tombstone recreation rules, backup creation, and atomic rollback.
- The current test that asserts sync apply creates no backup is deliberately
  changed to require a backup.
- Frontend tests that currently exercise legacy direct import are migrated to
  the preview/apply contract.

### Frontend seam

- Component tests render the real Records workbench and dialogs with the real
  store while mocking only the network boundary.
- Batch Add tests cover typing, two-column paste, add/remove row, keyboard flow,
  validation, counts, disabled Stage All, and batch staging.
- Excel Import tests cover sheet selection, disabled LRL, unknown sheets,
  preview status filters, source diagnostics, error exclusion, and Confirm &
  Stage.
- Sync tests cover pending-change blocking, side-by-side conflicts, explicit
  resolution, Delete actions, backup/apply summaries, and refresh after apply.
- Responsive tests assert stable action placement and full-screen narrow
  behavior without coupling to incidental CSS implementation.
- Prior art is the existing staged workbench component tests, store
  coalescing/optimistic-matrix tests, failed-save focus behavior, and feature-tab
  unsaved-change guards.

### Seed and packaging seam

- Seed command tests run against a temporary development database and inspect
  the exported normalized package.
- Initialization tests cover empty, non-empty, malformed-seed, and failed-apply
  databases.
- Packaging verification uses the supported root package command and asserts
  the seed exists in generated packaged configuration resources.
- Portable acceptance starts in a clean directory, confirms EAL, LMC, and TML
  records on first launch, edits the portable database, and confirms the
  development database is unchanged.
- Before this test, the developer is explicitly reminded to import and save the
  approved workbook, run `npm run wear:seed`, then run the supported package
  command.
- Every npm process on the company Windows environment sets
  `NODE_USE_SYSTEM_CA=1` while preserving HTTPS and `strict-ssl=true`.

### Integration and regression

- The updated reference workbook is used for an integration test or controlled
  acceptance run after deterministic small-fixture tests pass.
- Imported EAL, LMC, and TML data is verified in History, Latest Summary,
  Dashboard, and currently supported Projection behavior.
- Existing single-record edit, delete, Excel export, analysis save, workbench
  staging, dashboard, projection, and package export behavior is regression
  tested.
- Browser verification checks desktop and narrow layouts, large previews,
  non-overlapping actions, keyboard navigation, loading, empty, and error
  states.

## Out of Scope

- LRL workbook import.
- LRL database identity, metadata mapping, history, graphs, summaries,
  projections, or formulas.
- Importing the removed `EAL Projection_obsolete` or `LMC (2)` sheets.
- Real-time or automatic multi-computer synchronization.
- Concurrent multi-user editing.
- Hosted database deployment.
- User authentication or role-based authorization.
- SharePoint as a database synchronization layer.
- Replacing SQLite with PostgreSQL or another server database.
- Sharing the complete `analysis.db` file.
- Automatically packaging whatever data happens to be present in the
  development database without an explicit seed-generation step.
- Overwriting an existing portable user's data with a newer seed.

## Further Notes

- This spec is synthesized from the approved 2026-08-07 Wire Wear historical
  import, sync, and seed design conversation and its design document.
- Codebase impact analysis classifies the normalized line-class migration and
  central staged-change integration as CRITICAL. Implementation must proceed in
  dependency order with broad regression coverage.
- The repository currently has no root domain glossary or architecture decision
  records for this area. Existing Wire Wear product terminology and the approved
  design therefore define the vocabulary for this spec.
- The source workbook currently contains exactly EAL, LMC, TML, and LRL sheets.
- The local worktree contains unrelated uncommitted changes. Spec and future
  implementation work must preserve them and avoid broad staging commands.
