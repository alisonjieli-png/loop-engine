# Design guidance

Status: current interface guidance.

Use these tokens after choosing the correct architecture view from
[Architecture visual guidance](ARCHITECTURE-VISUAL-GUIDANCE.md).

## Palette

Mode is the first color axis.

| Token | Light | Dark | Meaning |
|---|---|---|---|
| Background | `#FAFBF9` | `#12161B` | Page and diagram ground. |
| Text | `#1A2129` | `#E8EDF2` | Main text. |
| Deterministic | `#155E54` | `#4EC0AE` | Code and rules with no language model call. |
| Hybrid | `#1B6E8F` | `#4FB0D6` | Code first with bounded model assistance. |
| Non-deterministic | `#B4690E` | `#E8A33D` | Model-led work under loop controls. |
| Success | `#2E7D32` | `#66BB6A` | Passed states only. |
| Failure | `#C23B3B` | `#E06C6C` | Failures and refusals only. |
| Disabled | `#8A939C` | `#6B7580` | Disabled controls. |

Amber can also mark candidate work. Always repeat a mode, state, or maturity in
text. Do not rely on color alone.

## Type and spacing

- Use Bricolage Grotesque for display text.
- Use IBM Plex Sans for body text.
- Use IBM Plex Mono with tabular numbers for code and measurements.
- Use a 4, 8, 12, 16, 24, 32, 48, 64, and 96 pixel spacing scale.
- Keep main content at or below 1,280 pixels when practical.

## Alignment

- Give cards in one sequence the same width.
- Keep labels away from borders and connectors.
- Do not let a connector end in empty space.
- Do not use radial text.
- Keep labels horizontal on narrow screens.
- Use left-to-right graphs for Solution Canvases.
- Use horizontal timelines with the newest event on the right.

## Progressive disclosure

A default card shows the name, status, mode, purpose, and one useful
measurement. A detail view can add the contract, configuration, history,
inputs, outputs, cost, and related intelligence.

## Accessibility

Every interactive view needs keyboard navigation, visible focus, sufficient
contrast, reduced-motion support, and a text alternative for color. Tables and
diagrams must remain understandable with a screen reader.
