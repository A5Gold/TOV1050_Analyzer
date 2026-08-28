# Issue tracker: GitHub

Issues and PRDs for this repository live as GitHub issues. Use the `gh` CLI
for all operations.

## Conventions

- **Create an issue**: `gh issue create --title "..." --body "..."`. Use a
  heredoc or body file for multiline bodies.
- **Read an issue**: `gh issue view <number> --comments`, including labels and
  relevant comments in the result.
- **List issues**: `gh issue list --state open --json number,title,body,labels,comments`
  with appropriate `--label` and `--state` filters.
- **Comment on an issue**: `gh issue comment <number> --body "..."`.
- **Apply or remove labels**: `gh issue edit <number> --add-label "..."` or
  `gh issue edit <number> --remove-label "..."`.
- **Close an issue**: `gh issue close <number> --comment "..."`.

Infer the repository from `git remote -v`; `gh` does this automatically when
run inside the clone.

## Pull requests as a triage surface

**PRs as a request surface: no.** Set this to `yes` if the repository later
treats external pull requests as feature requests.

When enabled, pull requests use the same labels and states as issues through
the corresponding `gh pr` commands. GitHub shares one number space across
issues and pull requests, so resolve an ambiguous `#42` with `gh pr view 42`
and fall back to `gh issue view 42`.

## Skill operations

- When a skill says "publish to the issue tracker", create a GitHub issue.
- When a skill says "fetch the relevant ticket", run
  `gh issue view <number> --comments`.

## Wayfinding operations

The wayfinding map is one issue labelled `wayfinder:map`, with child issues as
tickets.

- **Map**: create an issue labelled `wayfinder:map` containing Notes,
  Decisions-so-far, and Fog sections.
- **Child ticket**: link an issue as a GitHub sub-issue. If sub-issues are not
  enabled, add it to a task list in the map and start the child body with
  `Part of #<map>`. Use a `wayfinder:<type>` label where type is `research`,
  `prototype`, `grilling`, or `task`.
- **Blocking**: use GitHub native issue dependencies. If unavailable, put
  `Blocked by: #<n>, #<n>` at the top of the child body.
- **Frontier query**: select the first open, unassigned child in map order that
  has no open blockers.
- **Claim**: run `gh issue edit <number> --add-assignee @me` as the session's
  first write.
- **Resolve**: comment with the answer, close the child, and add its context
  pointer to the map's Decisions-so-far section.
