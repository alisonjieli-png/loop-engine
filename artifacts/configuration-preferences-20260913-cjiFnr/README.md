# Configuration preference verification artifacts

These are offline controls for configuration setters, preference engines,
meta-selection, and composition with existing search adapters. They contain
no live provider or real task-solving results.

Read the [verification report](../../docs/verification/CONFIGURATION-PREFERENCES-AND-META-SELECTION-2026-09-13.md)
for the source identity, denominators, failed control, and limits.

| File | Contents |
|---|---|
| `summary.json` | Verification totals, dependency limits, source scope, and wheel digest. |
| `component-checks.json` | Individual component checks and outcomes. |
| `verification-commands.json` | Exact final verification commands, exit codes, output, and elapsed times. |
| `optimizer-composition-first.json` | First composition control, including the vector fixture failure. |
| `optimizer-composition.json` | Corrected six-method composition control and actual optional optimizer checks. |
| `source-manifest.json` | Digests of the frozen package and build inputs. |

The existing DuckDB projection writer generated the JSON files. They are
derived verification artifacts, not a new Run History or managed-record store.
