# Design Guidance — tokens and interaction rules

Status: CURRENT (registered in `conformance_report.CURRENT_DOCS`).
Source: the correction directive (2026-08-24 §16-§17). Supersedes the
earlier mode palette (the violet model-backed and amber hybrid are
RETIRED).

## Palette (light / dark)

| Token | Light | Dark | Meaning |
|---|---|---|---|
| bone (ground) | #FAFBF9 | #12161B | background |
| ink | #1A2129 | #E8EDF2 | text |
| deep teal (primary + Deterministic) | #155E54 | #4EC0AE | accepted code, registered assets |
| blue-teal (Hybrid) | #1B6E8F | #4FB0D6 | code-first with model fallback |
| amber (Model-backed + candidate/honesty) | #B4690E | #E8A33D | model-guided; also candidate maturity and honesty callouts — never decoration |
| green (success) | #2E7D32 | #66BB6A | pass states only |
| red (failure) | #C23B3B | #E06C6C | failures/refusals only |
| neutral gray | #8A939C | #6B7580 | disabled |

Amber is reserved. Mode order everywhere: Deterministic → Hybrid →
Model-backed.

## Type, grid, spacing

Bricolage Grotesque display · IBM Plex Sans body · IBM Plex Mono data
(tabular numerals). 12/8/4-column grid, content max 1280-1440px.
Spacing scale 4/8/12/16/24/32/48/64/96.

## Alignment laws

No manually nudged labels; no connector ending in empty space; no
mismatched card widths in a sequence; no text touching borders; no
orphaned arrows; **no radial text** (the two-row loop rail is the
default loop form — see ARCHITECTURE-VISUAL-GUIDANCE.md).

## Progressive disclosure

Card default: name, status, mode, one-line purpose, one metric. Hover:
definition, why it matters, typical behavior. Click: full config,
history, inputs/outputs, evidence, costs, related intelligence.

## Accessibility (required)

Keyboard navigation, visible focus, contrast compliance, reduced
motion, no color-only information, responsive layouts, screen-reader
compatible tables and diagrams.
