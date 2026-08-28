# Portable Node System CA Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Codex use the Windows system CA for every npm-family command on this company computer and remove the obsolete TOV640 `CLAUDE.md`.

**Architecture:** Put the same operational rule in the global Codex instructions and the TOV640 project instructions so it applies both generally and locally. Keep the fix process-local with `NODE_USE_SYSTEM_CA=1`; do not weaken or permanently alter TLS configuration.

**Tech Stack:** Codex `AGENTS.md`, PowerShell, portable Node.js 24, npm

## Global Constraints

- Set `NODE_USE_SYSTEM_CA=1` before the initial `npm`, `npx`, or `npm exec` attempt.
- Keep `strict-ssl=true` and the npm registry on HTTPS.
- Never bypass certificate validation or persist environment changes without explicit user approval.
- Preserve all unrelated dirty worktree changes.

---

### Task 1: Persist the portable Node TLS rule and remove CLAUDE.md

**Files:**
- Modify: `C:\Users\chusiukd\.codex\AGENTS.md`
- Modify: `C:\smart maintanence\tov640_analyzer\AGENTS.md`
- Delete: `C:\smart maintanence\tov640_analyzer\CLAUDE.md`

**Interfaces:**
- Consumes: Codex global and project instruction discovery.
- Produces: A process-local npm execution rule available to future Codex tasks.

- [x] **Step 1: Add the exact rule to both AGENTS.md files**

````markdown
## Portable Node.js TLS

This company Windows computer uses portable Node.js. Before the first `npm`,
`npx`, or `npm exec` command, set `NODE_USE_SYSTEM_CA=1` for that process or
shell session. In PowerShell, use:

```powershell
$env:NODE_USE_SYSTEM_CA='1'; npm view npm version
```

Keep `strict-ssl=true` and use an HTTPS registry. Never bypass certificate
validation with `strict-ssl=false`, an HTTP registry, or similar workarounds.
Do not persist Windows or npm environment changes unless the user explicitly
requests it. If `UNABLE_TO_GET_ISSUER_CERT_LOCALLY` remains, inspect CA and
proxy configuration before changing anything.
````

- [x] **Step 2: Delete the obsolete project instruction file**

Delete only `C:\smart maintanence\tov640_analyzer\CLAUDE.md`; preserve the project `AGENTS.md` and all unrelated changes.

- [x] **Step 3: Verify instruction content and file removal**

Run:

```powershell
rg -n "Portable Node.js TLS|NODE_USE_SYSTEM_CA|strict-ssl=false" `
  "C:\Users\chusiukd\.codex\AGENTS.md" `
  "C:\smart maintanence\tov640_analyzer\AGENTS.md"
Test-Path "C:\smart maintanence\tov640_analyzer\CLAUDE.md"
```

Expected: both instruction files contain the rule and `Test-Path` returns `False`.

- [x] **Step 4: Verify npm TLS behavior without permanent configuration**

Run:

```powershell
$env:NODE_USE_SYSTEM_CA='1'; npm view npm version
```

Expected: exit code 0 and a published npm version.

- [x] **Step 5: Verify scope**

Run `git status --short` in `C:\smart maintanence\tov640_analyzer`.

Expected: `AGENTS.md` is modified, `CLAUDE.md` is deleted, the new spec/plan files are present, and all pre-existing unrelated changes remain untouched.

No commit is included because the worktree already contains unrelated user changes and the user did not request a commit.
