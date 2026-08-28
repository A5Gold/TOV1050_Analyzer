# Wear Seed and Startup Reliability Design

Date: 2026-08-26
Project: TOV640 Analyzer

## Problem

Development uses `%APPDATA%\\TOV640_Analyzer\\data\\analysis.db`, which currently
contains the historical EAL, LMC, and TML Wire Wear records. A packaged
portable build creates a separate database under its own `data/` directory,
but no Wire Wear seed is packaged or applied, so its historical average wear
table is empty. The packaged Electron shell also waits for backend health
before creating the window and gives up after 30 seconds; first-run PyInstaller
startup can exceed that window and produce a misleading offline state.

## Approved approach

1. Export only committed normalized Wire Wear records into a versioned JSON
   seed with the existing `wear_cycle_seed` serialization and validation.
2. Include the seed in `resources/config` during packaging. On backend startup,
   apply it transactionally only when the normalized Wire Wear dataset is
   empty. Existing user data is never overwritten.
3. Start the Electron window without blocking on backend readiness. Continue
   health polling for a longer bounded period, keep the UI in `Connecting`
   while startup is in progress, and report a failure only after the backend
   process exits or the extended wait expires.

## Data flow

```text
development analysis.db
        -> npm run wear:seed
        -> config/wire-wear-seed.json
        -> package extraResources/resources/config
        -> first portable backend startup
        -> empty normalized tables only
        -> transactionally imported historical records
```

The seed contains no SQLite files, WAL files, staged frontend state, or
repeated-exception records. Each portable installation continues to own its
`data/analysis.db`.

## Error handling

Seed absence or validation failure is logged and leaves the database usable;
it must not prevent other modules from starting. A non-empty normalized
dataset skips seed application. Electron treats a slow but alive backend as
`Connecting`; a dead process or extended timeout produces a non-blocking error
state and keeps the window available for retry/diagnostics.

## Verification

- Unit tests cover seed application, idempotent reopen, and missing/invalid
  seed behavior.
- Electron/frontend checks cover slow backend readiness without an early
  blocking dialog.
- The supported package command verifies the seed exists under
  `dist/**/resources/config/`.
