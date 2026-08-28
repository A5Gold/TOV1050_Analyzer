# Portable Node System CA Design

## Goal

Prevent npm and npx commands on this company Windows computer from failing with
`UNABLE_TO_GET_ISSUER_CERT_LOCALLY` when using the portable Node.js runtime.

## Design

- Add the same rule to the global Codex `AGENTS.md` and the TOV640 Analyzer
  `AGENTS.md`.
- Before running `npm`, `npx`, or `npm exec`, set `NODE_USE_SYSTEM_CA=1` for that
  process or shell session.
- Keep TLS verification enabled. Never use `strict-ssl=false`, an HTTP registry,
  or another certificate-validation bypass.
- Do not persist Windows or npm environment changes unless the user explicitly
  requests them.
- Remove the TOV640 Analyzer root `CLAUDE.md`; keep its `AGENTS.md` as the sole
  project instruction file.

## Verification

- Confirm both `AGENTS.md` files contain the rule.
- Confirm `CLAUDE.md` no longer exists.
- Run an npm registry query with `NODE_USE_SYSTEM_CA=1` and require exit code 0.
- Inspect Git status to verify the intended project scope.
