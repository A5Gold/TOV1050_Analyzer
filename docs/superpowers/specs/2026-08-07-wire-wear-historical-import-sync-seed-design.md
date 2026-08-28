# Wire Wear Historical Import, Sync, and Seed Design

Date: 2026-08-07
Project: TOV640 Analyzer
Module: Wear Calculator

## Purpose

This design extends the existing `Wire Wear Records` workbench so users can
load the historical average wear minimum workbook in bulk, enter multiple
Tension Length measurements in one action, exchange Wire Wear data between
computers, and ship a non-empty initial dataset in the Windows portable build.

The design builds on the existing SQLite-backed workbench, staged-change flow,
Wire Wear sync backend, and portable directory packaging. It does not introduce
a second application database or replace existing chart, projection, edit, or
delete behaviour.

Reference inputs:

- `docs/Wear Calculator_Database/EAL TML LRL LMC Historical Avg Wear Min Database .xlsx`
- `docs/Wear Calculator_Database/Wire Wear Records UI.png`
- `docs/Wear Calculator_Database/Add Wire Wear Records UI.png`

## Scope

Phase 1 supports these workbook sheets:

- `EAL`
- `TML`
- `LMC`

The workbook also contains `LRL`. Phase 1 displays it as reserved for future
support but does not import it, expose it in record-entry controls, or use it in
charts, summaries, projections, or formulas.

The former `EAL Projection_obsolete` and `LMC (2)` sheets have been removed
from the source workbook and are not part of the import contract.

## Approved Decisions

1. Excel import must preview changes before staging them.
2. Preview statuses are `New`, `Update`, `No Change`, and `Error`.
3. Confirmed `Update` records replace the matching stored wear value.
4. A `YYYYMM` workbook heading is stored as the first day of the month, for
   example `202401` becomes `2024-01-01`.
5. Blank cells and `.` mean no measurement. They are skipped and counted, not
   treated as errors.
6. Other non-numeric wear values are errors.
7. Unresolved errors block `Confirm & Stage`.
8. Manual Add Records supports multiple Tension Length rows under a shared line
   and cycle date, including two-column paste from Excel.
9. Shared data uses a versioned Wire Wear data package, not a raw copy of the
   complete `analysis.db`.
10. Shared package import previews conflicts and backs up SQLite before writing.
11. A developer-only `npm run wear:seed` command creates the initial Wire Wear
    dataset used by subsequent portable builds.
12. A portable installation loads the seed only when Wire Wear Records is empty
    and never overwrites an existing user's records.

## Architecture

All input paths use one normalization and validation pipeline:

```text
Excel workbook / Batch Add Records / Shared data package
                         |
                         v
                 Wear source adapter
                         |
                         v
              WearRecordCandidate records
                         |
                         v
             Validation and classification
                         |
                         v
             Preview and staged changes
                         |
                         v
              Existing Wire Wear API
                         |
                         v
              SQLite transaction boundary
```

### Source adapters

The backend import layer exposes a small adapter interface that converts a
source into canonical `WearRecordCandidate` values. It registers:

- `EALAdapter` for the EAL monthly matrix.
- `TMLAdapter` for the TML monthly matrix. It must parse month headings rather
  than relying on their physical column order.
- `LMCAdapter` for the LMC monthly matrix. It preserves the existing domain
  mapping where LMC belongs to `line_group = EAL` and `line_class = LMC`.
- A disabled LRL registry entry or adapter seam. The current LRL annual layout
  is structurally different and must not be forced through the monthly adapter.

The adapters own source-specific parsing only. Shared validation, comparison,
staging, persistence, and error reporting remain outside them so later LRL
support does not duplicate the rest of the workflow.

### Canonical candidate

Each candidate carries the fields required by the existing Wire Wear record
contract plus import diagnostics:

- Normalized line identity.
- Track.
- Tension Length.
- Cycle date.
- Average wear minimum.
- Source type.
- Source sheet.
- Source row and cell address when available.
- Original value for error reporting.

The implementation must reuse the existing database business key and domain
validation. It must not add a second uniqueness definition for imported data.

### Existing staged changes

Excel import and Batch Add Records return normalized candidates to the
frontend. `New` and `Update` candidates enter the existing pending-change flow.
`No Change` candidates are informational and are not staged. The existing Save
and Cancel controls remain the single user-facing commit boundary.

Shared package import is a database-level synchronization operation. It may not
start while unsaved staged changes exist; the user must save or cancel them
first.

## Historical Workbook Import

### Workbook discovery

After the user chooses an `.xlsx` file, the backend returns all workbook sheet
names and their support status:

- `EAL`, `TML`, and `LMC` are selected by default and may be deselected.
- `LRL` is visible but disabled with `Reserved for future support`.
- Unknown sheets are shown as ignored and do not block supported sheets.

An encrypted, corrupt, or non-XLSX input stops before any preview is created.

### Sheet structure

Each supported sheet must have `Track` and `Tension Length` as its first two
logical columns. Remaining importable columns must use valid `YYYYMM` headings.

Month headings are parsed independently and normalized to `YYYY-MM-01`. The
importer must accept an unsorted month sequence and must reject duplicate or
invalid month headings with exact column diagnostics.

For each row and month column:

- A numeric cell becomes one candidate record.
- A blank cell is skipped.
- A cell containing only `.` is skipped.
- Any other non-numeric value is an error.

`Track` values are trimmed and normalized to `UP` or `DOWN`. Any other non-empty
track value is an error. Tension Length remains a string and is trimmed without
changing meaningful identifiers such as leading zeroes, letters, or suffixes.

### Duplicate source records

When the workbook produces the same existing business key more than once:

- Equal values collapse to one candidate and produce a duplicate notice.
- Different values produce an error because the importer cannot safely choose
  which source value is authoritative.

### Database comparison

The backend compares valid candidates with current committed records and
returns:

- `New`: no matching record exists.
- `Update`: a matching record exists with a different wear value.
- `No Change`: the stored and imported values are equivalent.
- `Error`: the candidate cannot be safely normalized or validated.

Each preview row includes the source location and enough existing/imported
value context for the user to audit the decision. All remaining errors must be
fixed in the workbook or explicitly excluded before `Confirm & Stage` is
enabled.

### Commit behaviour

Confirmation stages only `New` and `Update` candidates. Saving applies the
entire pending set in one SQLite transaction. A failure rolls back the complete
save rather than leaving a partially imported cycle.

Before an Excel-originated large batch is committed, the backend creates an
automatic SQLite backup. Failure to create that backup stops the write.

## Batch Add Records

The existing one-record dialog becomes a wide operational dialog with shared
context controls and a stable input grid.

Shared controls:

- `Line`: EAL, TML, or LMC.
- `Cycle Date`: the existing date control and validation semantics.

Grid columns:

```text
# | Tension Length | Avg Wear Min | Status | Delete
```

The user can add and remove rows, navigate by keyboard, and paste two columns
from Excel. Pasted and typed rows use the same validator and database
classifier as workbook import. Inline errors remain attached to the exact cell.

The dialog footer shows valid, update, duplicate, and error counts. `Stage All`
is disabled until every non-empty row is valid. One action adds all valid rows
to the existing pending-change list.

## User Interface

The UI retains the current Material UI workbench language and data density. It
does not introduce a landing page, decorative dashboard cards, or a separate
administration area for domain-specific actions.

The Wire Wear Records toolbar contains:

```text
[Add Records] [Import Excel]              [Database menu] [Save Changes]
```

The Database menu contains:

- `Export Data Package`
- `Import Data Package`

### Excel import dialog

The dialog has three stages:

1. Select the file and supported worksheets.
2. Validate and inspect the preview.
3. Confirm and stage changes.

The preview header shows per-sheet and total counts. The table supports `All`,
`New`, `Update`, `No Change`, and `Error` filters. Error rows show the sheet,
cell address, original value, and reason, and the user may download an error
report for workbook correction.

### Shared package import dialog

The package preview uses the same visual structure with these statuses:

- `New`: add the imported record.
- `Update`: the imported record is newer and is selected by default.
- `Keep Local`: the local record is newer and is selected by default.
- `No Change`: both sides are equivalent.
- `Conflict`: timestamps are equal but content differs; the user must select
  local or imported data.

All conflicts must be resolved before import. The dialog clearly shows local
and imported values side by side.

Desktop uses a wide dialog with stable table dimensions. Narrow layouts use a
full-screen dialog with fixed primary actions so data growth does not move or
overlap the commit controls.

## Versioned Data Packages

Export creates a versioned Wire Wear package containing only the Wire Wear
records and sync metadata required by the existing import logic. It does not
contain unrelated analysis tables or a raw SQLite file.

The package includes at least:

- Schema/package version.
- Export timestamp.
- Application version when available.
- Source identifier when available.
- Wire Wear records with row-level `updated_at` values.

Package import validates the complete envelope before comparing records. An
unsupported package version stops the import; the system does not attempt a
partial best-effort conversion.

Immediately before confirmed package import, SQLite backup succeeds or the
import does not start. The import then runs in one transaction. Automatic
backups live under `<data>/backups/` and retain the latest 10 files. Manual data
package exports are user-owned and are never included in automatic retention.

## Seed and Portable Packaging

Development and portable databases stay independent:

```text
npm run dev
    -> editable development analysis.db

npm run wear:seed
    -> versioned Wire Wear seed generated from committed development records

npm run package or npm run package:win
    -> seed copied into packaged resources/config

first portable launch with no Wire Wear records
    -> seed imported into the portable data/analysis.db
```

`npm run wear:seed` is explicit so packaging cannot accidentally publish test
or partially edited development data. It exports committed records only and
does not include frontend staged changes.

The seed asset lives under `resources/config` and is declared in
`package.json` `build.extraResources`. The packaged backend resolves it through
the established config resource path.

At startup:

1. Run normal schema migrations.
2. Determine whether committed Wire Wear Records are empty.
3. If empty and a valid seed exists, import it transactionally.
4. If records already exist, do nothing.
5. If seed import fails, roll back the seed import, keep the database usable,
   and report/log the error without affecting other modules.

Reopening or updating the application must never reapply the seed over existing
records. Each portable directory owns its own `<portable root>/data/analysis.db`
after first launch and cannot affect the development database or another
portable copy.

## Error Handling and Recovery

All preview errors use structured codes internally and actionable messages in
the UI. Relevant errors include:

- Invalid workbook or package.
- Missing required column.
- Invalid or duplicate month heading.
- Invalid track.
- Empty Tension Length on a populated row.
- Non-numeric or domain-invalid wear value.
- Conflicting duplicate source key.
- Unsupported package version.
- Backup failure.
- Transaction failure.

Parsing and preview never modify SQLite. Write operations use one transaction.
Backup failure blocks import, and write failure rolls back the complete change.
The original database and any successfully created backup remain available for
recovery.

## Testing Strategy

### Backend tests

- Parse EAL, TML, and LMC monthly matrices.
- Parse unsorted TML month headings correctly.
- Convert `YYYYMM` to `YYYY-MM-01`.
- Skip blanks and `.` while reporting skipped counts.
- Normalize Track values and reject invalid values.
- Preserve Tension Length identifiers.
- Classify new, updated, unchanged, and invalid candidates.
- Collapse equal duplicate source records and reject conflicting duplicates.
- Keep LRL disabled and outside the Phase 1 data model.
- Roll back a failed batch save.
- Validate package versions and all sync conflict states.
- Create a backup before Excel batch and package imports.
- Create a seed from committed records only.
- Apply the seed only to an empty Wire Wear dataset.

Automated parser tests should use small deterministic workbook fixtures. The
full reference workbook is used for integration and acceptance verification so
the unit suite does not depend on a large mutable binary fixture.

### Frontend tests

- Open Batch Add Records and manage multiple rows.
- Paste two-column values and retain stable grid dimensions.
- Disable `Stage All` while errors exist.
- Select supported Excel sheets and keep LRL disabled.
- Filter each preview status.
- Display exact source locations for import errors.
- Stage new and updated records through the existing pending-change flow.
- Block package import while pending changes exist.
- Resolve package conflicts and confirm import.
- Cover loading, empty, error, and large-result states.

### Integration and regression tests

- Import the updated reference workbook and verify EAL, TML, and LMC counts.
- Verify imported records appear in History, Latest Summary, Dashboard, and
  currently supported Projection flows.
- Verify existing edit, delete, export, and staged-save behaviour still works.
- Export a package from one database and import it into another with new,
  updated, local-newer, unchanged, and conflict cases.
- Verify the pre-import backup can be opened and contains the previous data.

### Portable acceptance test

Before the packaging test, explicitly remind the developer to complete this
sequence:

```text
Import and save the approved data under npm run dev
-> run npm run wear:seed
-> run the supported root package command
-> verify the seed under dist/**/resources/config/
-> start from a clean portable directory
-> verify EAL, TML, and LMC records are present on first launch
-> edit the portable records
-> verify the development database is unchanged
```

Every npm command on the company Windows environment sets
`NODE_USE_SYSTEM_CA=1` for that process while preserving HTTPS and
`strict-ssl=true`.

## Acceptance Criteria

1. The updated workbook can import EAL, TML, and LMC in one action after a
   complete preview.
2. LRL is visible as future support but cannot enter Phase 1 storage or
   calculations.
3. Users can stage multiple manual Tension Length measurements in one action.
4. Invalid input cannot silently produce a partial import.
5. Existing records are clearly classified before an Excel update.
6. Wire Wear data can be exported and imported between computers without
   copying the complete SQLite database.
7. Conflicts require an explicit decision and package import creates a backup.
8. A newly built portable directory starts with the approved seed dataset.
9. Portable edits, development edits, and other portable copies remain
   independent.
10. Existing Wire Wear charts, summaries, projections, editing, deletion, and
    export workflows remain functional.

## Deferred Work

- LRL workbook import and data-model mapping.
- LRL graphs, formulas, summaries, and projections.
- Real-time or automatic multi-computer synchronization.
- Hosted database deployment.
- User authentication or role-based permissions.
- Replacing SQLite with a server database.
