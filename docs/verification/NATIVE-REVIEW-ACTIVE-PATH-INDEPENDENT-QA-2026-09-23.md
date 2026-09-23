# Independent native review profile check

Date: September 23, 2026. Reviewed read-only in
`/home/username/.le-codex-build/review-integrity`, native package review patch
SHA-256 `15c34134b7486756cfd12559cfe87ca625d5514c1ed82f7bbbb69c2e6f5249f2`.
No model call, installation, package execution or approval occurred.

## Confirmed gap

The native format precheck permits strict JSON data with the `other` role, while
refusing some known active paths. Two active native configuration paths were
missing from that classification:

| Fixture | Declared metadata | Observed result |
| --- | --- | --- |
| `opencode.json` containing a configured npm plugin | `application/json`, `other`, no effects, OpenCode style, plus a normal `AGENTS.md` | All deterministic prechecks passed. |
| `.pi/settings.json` containing a configured package | `application/json`, `other`, no effects, Pi style, plus a normal `AGENTS.md` | All deterministic prechecks passed. |

These paths can influence native startup and dependency loading. They therefore
need a qualified active-component profile or a typed refusal. Declaring them
inert cannot establish that they remain inert in the selected harness.
The [counterexample record](../../artifacts/generator-independent-qa-2026-09-23/native-active-path-controls.json)
records the exact cases. The payloads were parsed by the review code only.

The finding does not mean the review panel approved either item. It shows a gap
in the promised deterministic refusal of unknown required components. The three
independent model reviewers remain another gate. The twelve current original
method packages use ordinary example and verification JSON, so their data paths
should remain accepted after this repair.

## Inspected controls

The native reader compares the full filesystem inventory to the canonical
package, refuses symlinks and special files, checks exact size and SHA-256,
compares item and specification metadata, and binds provenance to committed
source bytes. Binary payloads remain held for a separate asset verification
profile. These source findings are not a claim of a complete adversarial audit.

The author has the counterexamples and will refine passive JSON placement
without weakening whole-package review or allowing unqualified native settings.
Successor evidence should be saved separately from this initial finding.
