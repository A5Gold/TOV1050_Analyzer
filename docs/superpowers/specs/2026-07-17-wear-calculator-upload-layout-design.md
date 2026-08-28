# Wear Calculator Upload and Records Layout Design

## Scope

This change addresses three existing workflows without changing route names,
form field names, or the underlying record-editing interactions:

1. Save a partial wire-wear cycle when expected segments are missing.
2. Restore the Wear Calculator label and requested sidebar order, and move the
   Wear Calculator feature toolbar and Method Guide action above its result
   content.
3. Let Database Record use the desktop viewport so the table has a useful
   scrolling region instead of collapsing to a single visible row.

## Behaviour and Data Flow

The preview remains the source of truth. A preview with `segment_missing` is
saveable when it contains at least one valid record and has no unresolved
conflict. The persisted cycle is marked `incomplete`, and every expected segment
is still stored with its presence, coverage, diagnostics, and source files.

The following conditions continue to block saving:

- no records;
- an unaccepted data conflict;
- duplicate business keys;
- a stale data version or changed preview digest;
- invalid line or cycle date values.

The API and repository validation share this rule. The frontend button mirrors
the rule so the user can act on a partial preview without bypassing any data
integrity check. Missing segments remain visible as a warning/informational
state rather than being presented as a save error.

## Navigation and Wear Calculator Layout

The sidebar order becomes: About, Generate, History, Records, Wear Calculator,
Stagger, Trends, Settings. The desktop and compact labels both use
`Wear Calculator` for the wear route.

Wear Calculator renders its feature toolbar directly below the upload heading
and above analysis results. The toolbar continues to control Analysis, Wire
Wear Records, Dashboard, and Projection, and its Method Guide action remains
available at the same top-level position. Existing tab guards and record-save
flows remain unchanged.

## Database Record Layout

Database Record keeps its header, filters, line tabs, and section tabs, but its
root becomes a desktop flex viewport region. The table wrapper and DataGrid are
allowed to grow into the remaining height; the virtual scroller owns table
scrolling. On compact screens the view returns to natural document flow so the
page itself can scroll.

## Verification

Add focused tests for partial-cycle persistence and retained blocking rules,
sidebar order and Wear Calculator label, toolbar placement, and the database
viewport layout contract. Run the existing frontend and backend test suites,
then verify desktop and compact layouts in a real browser session.
