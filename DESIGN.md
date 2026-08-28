---
name: TOV1050 Analyzer
description: 高密度鐵路接觸網維運資料分析工作台
colors:
  primary: "#2b63c9"
  primary-dark: "#1f4fa6"
  primary-light: "#eaf1ff"
  secondary: "#256f62"
  success: "#2f8a67"
  warning: "#b8791b"
  error: "#c74444"
  canvas: "#f6f8fb"
  surface: "#ffffff"
  text-primary: "#263348"
  text-secondary: "#687589"
  divider: "#e2e7ef"
typography:
  display:
    fontFamily: 'Inter, "Noto Sans", "Segoe UI", sans-serif'
    fontSize: "1.72rem"
    fontWeight: 750
    lineHeight: 1.22
    letterSpacing: "0"
  title:
    fontFamily: 'Inter, "Noto Sans", "Segoe UI", sans-serif'
    fontSize: "1.28rem"
    fontWeight: 750
    lineHeight: 1.3
    letterSpacing: "0"
  body:
    fontFamily: 'Inter, "Noto Sans", "Segoe UI", sans-serif'
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "0"
  label:
    fontFamily: 'Inter, "Noto Sans", "Segoe UI", sans-serif'
    fontSize: "0.875rem"
    fontWeight: 700
    lineHeight: 1.4
    letterSpacing: "0"
rounded:
  sm: "6px"
  md: "8px"
spacing:
  sm: "8px"
  md: "16px"
  lg: "24px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "#ffffff"
    rounded: "{rounded.sm}"
    height: "40px"
  surface-outlined:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text-primary}"
    rounded: "{rounded.md}"
    padding: "16px"
---

# Design System: TOV1050 Analyzer

## 1. Overview

**Creative North Star: "The Maintenance Control Room"**

TOV1050 Analyzer is a Windows desktop control room for railway maintenance analysts. The interface serves repeated inspection work: importing CSV files, validating physical metadata, reviewing exceptions, and exporting evidence. Visual design therefore prioritizes stable geometry, scanable density, explicit state, and trustworthy numbers over novelty.

The system uses the existing MUI language rather than introducing a second design system. Surfaces are flat and lightly outlined, with restrained Railway Blue actions and semantic safety colors. It explicitly rejects marketing heroes, decorative card grids, excessive rounding, low-contrast text, and visual effects that obscure source context.

**Key Characteristics:**

- Operational density with predictable spacing.
- Clear separation between input, preview, review, commit, and export states.
- Data tables and Plotly charts are primary work surfaces, not decoration.
- Traditional Chinese explanatory content may coexist with stable technical identifiers and API terms.

## 2. Colors

The palette is a cool, restrained blue system with green confirmation, amber review, red error, and blue safety-level semantics.

### Primary

- **Railway Blue** (#2b63c9): primary actions, selected navigation, links, focus-adjacent emphasis.
- **Railway Blue Deep** (#1f4fa6): contained-button hover and pressed emphasis.
- **Railway Blue Wash** (#eaf1ff): selected/active background and upload affordance emphasis.

### Secondary

- **Maintenance Teal** (#256f62): secondary actions and supporting analytical emphasis.

### Tertiary

- **Success Green** (#2f8a67): saved/validated completion states.
- **Review Amber** (#b8791b): pending changes, conflicts, and caution.
- **Exception Red** (#c74444): blocking errors and L1 severity.

### Neutral

- **Canvas** (#f6f8fb): application background.
- **Surface** (#ffffff): Paper, dialogs, tables, and input surfaces.
- **Ink** (#263348): primary text and numeric content.
- **Muted Ink** (#687589): supporting labels and secondary explanation.
- **Divider** (#e2e7ef): table rules, outlines, and section boundaries.

### Named Rules

**The Semantic State Rule.** Use warning/error/success and L1/L2/L3 colors with labels or icons; never communicate a maintenance decision by color alone.

### Version Difference Cycle Palette

Version Difference uses one ordered cycle descriptor for upload slots, multipart
fields, response keys, chart traces, and difference headings:

- **Latest**: Exception Red `#c74444`
- **Previous 1**: Railway Blue `#2b63c9`
- **Previous 2**: Success Green `#2f8a67`
- **Previous 3**: Review Amber `#b8791b`
- **Previous 4**: Supporting Violet `#9467bd`

The cycle color is an accent for the outlined upload surface, swatch, and
Plotly trace. Every colored element retains its explicit role label, so color
is never the only way to identify a report or comparison.

## 3. Typography

**Display Font:** Inter (with Noto Sans and Segoe UI fallbacks)

**Body Font:** Inter (with Noto Sans and Segoe UI fallbacks)

**Character:** Compact, neutral, and legible at table density. Traditional Chinese copy must remain readable beside technical English identifiers, file names, chainage, and TL values.

### Hierarchy

- **Display** (750, 1.72rem, 1.22): page titles and primary workbench headings.
- **Title** (750, 1.28rem, 1.3): major panels and result sections.
- **Body** (400, 1rem, 1.5): descriptions, explanations, and empty/error guidance.
- **Label** (700, 0.875rem, 1.4): controls, table headers, tabs, and status labels.

**The Stable Type Rule.** Keep letter spacing at zero and use weight/size hierarchy instead of tracked uppercase labels or decorative display type.

## 4. Elevation

The system is flat by default. MUI Paper uses `elevation: 0`; depth comes from white surfaces against the cool canvas, 1px dividers, and bounded dialogs rather than broad shadows. Outlined surfaces may use the shared 6-8px radius. Focus rings and state borders are functional, not decorative.

### Named Rules

**The Evidence Surface Rule.** A surface may frame a dataset, chart, dialog, or staged workbench state; do not nest decorative cards or add shadows merely to make a section look important.

## 5. Components

### Buttons

- **Shape:** 6px radius, minimum height 40px, no elevation, sentence-case labels.
- **Primary:** Railway Blue background with white text; Deep Blue on hover.
- **Secondary:** outlined or neutral action with the same height and visible disabled state.
- **Focus:** preserve a clear `:focus-visible` outline and keyboard activation.

### Cards / Containers

- **Shape:** MUI Paper with 8px maximum radius and no default shadow.
- **Surface:** white on Canvas, with Divider outlines when a boundary is needed.
- **Use:** frame a repeated dataset, result group, chart, or dialog; page sections remain unframed layouts where possible.

### Inputs / Fields

- **Shape:** outlined MUI inputs with 6px radius and white background.
- **Focus:** primary-color border/focus treatment with keyboard-visible outline.
- **Error:** Alert/error color plus actionable source context; do not silently coerce invalid data.

### Navigation

- **Style:** responsive MUI drawer/navigation with tabs for workbench sub-features.
- **State:** selected navigation uses primary color and a tonal wash; tab changes respect staged-record navigation guards.

### Data Tables and Charts

- **Data tables:** dense but stable columns, sortable/filterable where supported, explicit row/cell states, and preserved technical identifiers.
- **Plotly:** charts explain trend, wear, projection, or exception location; axes and hover context must retain units, dates, line/track, TL, and chainage.
- **Staged records:** add/edit/delete states use warning tokens plus icon/text/strikethrough, not color alone.

## 6. Do's and Don'ts

### Do:

- **Do** preserve the MUI/Plotly vocabulary and existing business workflow.
- **Do** make loading, empty, error, conflict, pending, saved, and export states explicit.
- **Do** keep source filename, chainage, TL, section, and lineage context near validation failures.
- **Do** preserve light/dark themes, keyboard access, responsive layouts, and reduced-motion behavior.
- **Do** use backend preview/digest/version contracts as the source of truth for commit UI.

### Don't:

- **Don't** turn this operational tool into a marketing landing page.
- **Don't** use decorative card grids, excessive rounding, broad ornamental shadows, or low-contrast text.
- **Don't** rely on color alone for L1/L2/L3, pending, conflict, success, or error states.
- **Don't** widen metadata intervals, choose nearest intervals, invent chainage offsets, or add silent fallbacks in the UI.
- **Don't** hide validation failures or replace an actionable diagnostic with a generic error.
