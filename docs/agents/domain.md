# Domain Docs

This repository uses a single-context domain documentation layout.

## Before exploring

Read the following documentation when it exists and is relevant to the area
being changed:

- `CONTEXT.md` at the repository root.
- ADRs under `docs/adr/`.

If either path does not exist, proceed silently. Domain-modeling work creates
these files when terminology or architectural decisions are resolved.

## File structure

```text
/
|-- CONTEXT.md
|-- docs/
|   `-- adr/
`-- backend, frontend, electron, and other source directories
```

`CONTEXT.md` contains the shared domain glossary, core concepts, boundaries,
and business rules. `docs/adr/` contains repository-wide architecture decision
records.

## Use the glossary vocabulary

When output names a domain concept in an issue title, proposal, hypothesis,
test, or implementation, use the term defined in `CONTEXT.md`. Do not drift to
synonyms that the glossary explicitly avoids.

If a required concept is absent, first reconsider whether the proposed term
matches the product language. If the gap is real, record it for domain-modeling
work.

## Flag ADR conflicts

If proposed work contradicts an existing ADR, identify the conflict explicitly
instead of silently overriding the decision. Cite the ADR and explain why the
decision may need to be revisited.
