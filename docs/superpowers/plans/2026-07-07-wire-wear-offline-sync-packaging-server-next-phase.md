# Wire Wear Offline Sync Packaging Server Next Phase Plan

## Goal

Define the next phase after the Wire Wear Records Workbench: package strategy, offline export/import sync, and optional hosted-server deployment.

## Phase 2A: Packaging Decision

- Keep `dir` folder packaging as the recommended default for portable offline use.
- Document that production Electron currently sets `DB_PATH` to `<packaged app root>/data/analysis.db`.
- Document that single exe packaging must externalize writable data to `%APPDATA%` or another writable folder because embedded executable resources are not a database storage location.
- Add an in-app About or diagnostics view showing the active database path.

## Phase 2B: Offline Sync Package

- Add export sync package action that writes:
  - SQLite data version.
  - Export timestamp.
  - Source machine/user label.
  - Wire wear records.
  - Repeated records if selected.
  - Metadata file hashes.
- Add import sync package action that:
  - Creates a SQLite backup before import.
  - Compares row-level `updated_at`.
  - Updates local rows only when import rows are newer.
  - Reports conflicts and skipped rows.

## Phase 2C: Hosted Server Option

- Evaluate central FastAPI deployment on VPS.
- Prefer PostgreSQL for multi-user writes.
- Add authentication before exposing write APIs.
- Use HTTPS, firewall restrictions, backups, and database migration scripts.
- Treat SharePoint as file exchange/backup storage, not as the live concurrency database.
