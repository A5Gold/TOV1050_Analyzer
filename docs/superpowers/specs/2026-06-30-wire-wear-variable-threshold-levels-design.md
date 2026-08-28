# Wire Wear Variable Threshold Levels Design

## Goal

Allow the Metadata Editor and exception detection algorithm to respect the threshold levels actually configured for Wire Wear. This supports the department simulation where Wire Wear may use only L1, without removing L2 support permanently from the program.

## Context

`docs/architecture.md` section 4.2 identifies the metadata mapping path:

- `MetadataManager`
- `ExceptionDetector._map_class_info`
- `ExceptionDetector._map_track_info`
- `ExceptionDetector._apply_mapping`

The relevant threshold path is:

- `MetadataService.get_metadata()` loads the workbook for the Metadata Editor.
- `MetadataManager.get_all_thresholds()` loads the `threshold` sheet and calls `_normalize_thresholds()`.
- `ExceptionDetector.analyze()` consumes normalized thresholds.
- `ExceptionDetector._detect_scalar()` currently assumes scalar exception types use L1 and L2.

The current behavior is incorrect for the simulation: after the user deletes Wire Wear L2 values in the Metadata Editor, switching away and back can show the old L2 values again. The new behavior must preserve the user's configured level set.

## Chosen Approach

Use metadata-driven threshold levels for Wire Wear rather than hard-coding Wire Wear to one level.

If the workbook has Wire Wear L1 and L2, detection keeps the existing two-level behavior. If the workbook has Wire Wear L1 only, the editor reloads with L2 blank and detection only produces L1 Wire Wear exceptions. This keeps the simulation reversible: restoring L2 in metadata restores L2 behavior without a code change.

## Data Semantics

For Wire Wear rows:

- `Wire Wear L1` with a numeric value means L1 is enabled.
- `Wire Wear L2` with a numeric value means L2 is enabled.
- Missing, blank, `None`, or `NaN` `Wire Wear L2` means L2 is disabled for that row.

This applies per class/track threshold row. A `both` row may have L2 disabled while another class row may also have L2 disabled. Existing class fallback behavior must remain intact: undefined classes can fall back to `both`, but a defined class with a blank threshold must stay blank.

## Backend Design

`MetadataManager._normalize_thresholds()` must preserve missing levels when converting long threshold format to wide detector format. It must not synthesize Wire Wear L2 if no source value exists.

`MetadataService.save_configuration()` already replaces the sheet after validation. It should continue allowing blank L2 values because `validate_row()` treats blank values as absent. Tests should verify that saving and reloading a threshold sheet with Wire Wear L2 blank does not restore old L2 values.

`ExceptionDetector._detect_scalar()` should compute active threshold levels from non-null threshold columns. For min-mode scalar types such as Wire Wear and Low Height, the gatekeeper is the maximum available threshold value. For max-mode scalar types such as High Height, the gatekeeper is the minimum available threshold value. Classification still checks severe levels first, L1 before L2.

The implementation should keep the behavior focused on scalar detection and avoid changing stagger detection.

## Frontend Design

`MetadataEditorView` should allow Wire Wear L2 cells to remain blank after editing, saving, switching tabs, and reloading.

`transformToGrid()` should represent missing level values as `null`, not as old numeric values. `transformToBackend()` should preserve the user's intent when a level is blank. The implementation may either send explicit `null` for blank level columns or ensure the backend treats missing level fields as blank during save and reload. Tests must lock the selected behavior.

The UI can keep the Level 2 column visible. This avoids a larger design change and lets users re-enter L2 later if the department keeps two-level Wire Wear thresholds.

## Risk And Impact

Impact analysis showed the relevant symbols are high-risk:

- `_normalize_thresholds()` affects `get_all_thresholds()`, Metadata Editor reload, and `ExceptionDetector.analyze()`.
- `_detect_scalar()` affects `ExceptionDetector.analyze()` and the analysis API.
- `save_configuration()` and `update_metadata()` affect workbook persistence and backup.

Development must be test-first and narrowly scoped.

## Testing

Required backend coverage:

- Normalizing long-format Wire Wear L1-only thresholds returns no numeric L2.
- Saving then reloading Wire Wear L1-only metadata preserves blank L2.
- Wire Wear L1-only detection produces L1 only and never L2.
- Existing two-level Wire Wear detection still produces L1/L2 as before.
- Low Height, High Height, and Stagger regression tests continue passing.

Required frontend coverage:

- Clearing Wire Wear L2 produces a backend payload that preserves blank L2 semantics.
- Reloading grid data with blank Wire Wear L2 displays an empty L2 cell.
- Metadata Editor cache does not reintroduce stale L2 values after save.

## Out Of Scope

- Removing the Level 2 column from the UI.
- Changing Low Height, High Height, or Stagger threshold policy.
- Changing workbook filenames or metadata sheet names.
- Changing exception ID formats.
