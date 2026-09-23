# Twelve original mixed native method packages

Status: **12 new logical candidates, 96 payload paths, 85 distinct payload byte
digests, zero approvals and zero hosted items.** There are no `SKILL.md` files.
The eleven repeated digests come from carrying the same repository licence in
every package. Canonical package documents, authoring copies and older attempts
do not increase the count. See the [count record](counts-final.json).

Use [prepared-final/items.json](prepared-final/items.json) for independent
review. `prepared/` is the earlier version retained beside its successor. This
artifact adds useful supply while the generation worker is being built; it does
not generate job-title variants or claim 10,000 items exist.

## Contents and intended use

Each package has eight files:

```text
One original candidate package
├── AGENTS.md                      native usage instructions and first actions
├── tools/<method>.py              bounded standard-library computation
├── contracts/input.schema.json    structural input contract
├── contracts/output.schema.json   successful output contract
├── examples/input.json            original synthetic input
├── examples/output.json           expected result
├── verification/cases.json        success and refusal cases
└── LICENSE                        repository MIT notice
```

These are reusable method packages. Their `AGENTS.md` files must be composed
with the current assignment by the existing instruction composer; do not
overwrite a step's objective with a generic usage guide. Initial native styles
are Codex, OpenCode and Pi. A Claude Code binding needs the existing explicit
`CLAUDE.md` import mechanism where direct `AGENTS.md` loading is unavailable.
No native harness was launched in this supply lane, so these are candidate
compatibility declarations, not native loading qualifications.

## Distinct work methods and prior-library comparison

The [prior inventory](prior-inventory.json) records all 80 earlier advisory
skills and nine mixed candidates. No new identity collides with it. The
following comparison is the author's assessment of scope, not independent
semantic-duplicate approval.

| New method | Concrete result | Relationship to prior material |
| --- | --- | --- |
| `schedule_dag_earliest_times` | Earliest start/finish times and total duration with unlimited parallel resources | The prior prerequisite-order guide inspects written task instructions. This tool computes an explicit duration graph; it does not replace that review. |
| `cover_pairwise_configuration_values` | Deterministic test rows covering every pair of factor values | Prior model/context comparison guidance does not construct covering rows for a factor grid. |
| `compare_primitive_object_contracts` | Breaking changes in a deliberately small primitive-field contract language | Prior source-to-target mapping guidance traces data meaning. This tool checks set inclusion of accepted primitive object shapes. |
| `pack_first_fit_decreasing_batches` | Capacity-respecting batches from integer item sizes | No prior executable bin-packing method was found. This heuristic makes no optimality claim. |
| `audit_functional_dependency_rows` | Concrete row groups contradicting a declared functional dependency | Prior aggregate-grain and join checks address related data risks. This tool distinguishes typed determinant/dependent tuples, including Boolean versus integer values. |
| `find_strongly_connected_components` | Mutually reachable components and self-loop cycles | This is structural directed-graph analysis, distinct from scheduling durations or interpreting prerequisite prose. |
| `simulate_exact_token_bucket` | Offline admit/deny sequence with fractional balances | Prior resource-capacity interval guidance is not a token-bucket simulation. These results grant no quota or authority. |
| `audit_boolean_rule_coverage` | Exhaustive missing and conflicting assignments for a small Boolean rule table | Prior protocol-effect adjudication guidance does not enumerate the truth table or compute coverage. |
| `decode_u16_length_prefixed_frames` | Strictly framed hexadecimal records | The prior JSON shape server and text-encoding tool do not parse length-prefixed byte frames. |
| `evaluate_bounded_rational_expression` | Exact reduced rational result for a restricted arithmetic grammar | Prior rounding and denominator guides discuss interpretation. This tool parses and computes a bounded expression without `eval`. |
| `resolve_literal_named_template` | One-pass literal substitution with missing/unused variable refusal | No prior executable literal-template method was found. It does not escape a target language or execute its output. |
| `project_json_pointer_values` | Values at exact JSON Pointer string paths | The prior JSON shape server reports structure. This tool selects values, including escaped member names and strict array indexes. |

## Authorship, sources and rights

The source and examples were authored in this session by Codex, OpenAI family,
using `codex_original_mixed_native_authoring/v1`. They implement known algorithms
and interfaces; they are not claims of novel algorithm research. No third-party
source code or prose was copied into the packages.

Reuse was considered before building. Python's standard-library
[graphlib](https://docs.python.org/3/library/graphlib.html) supplies topological
ordering and cycle refusal. [fractions](https://docs.python.org/3/library/fractions.html)
supplies exact rational arithmetic for expressions and token refill. JSON Pointer
behavior was checked against [RFC 6901](https://www.rfc-editor.org/rfc/rfc6901):
decode `~1` before `~0`, preserve exact member names, refuse leading-zero array
indexes, and treat a missing value as an error. The custom examples are separate
from the standard's examples.

The proposal provenance pins the existing `CataloguePackage` implementation and
repository licence at revision
`9c57c9a4c813578bffa504108ef9d785b308bb86`. That source grounds package layout,
roles, bounds and digest handling. It is **not** evidence that the repository
already contained these algorithms or that their mathematics is correct. The
saved tests provide the bounded behavioral evidence. Root MIT metadata does not
license third-party task inputs or clear imported source rights.

## Verification on the exact final package bytes

[The final verification report](verification-after-format-and-schema-fix.json)
binds each canonical package digest and every payload digest. It records:

- 51 authored success/refusal cases passing across the twelve methods.
- Twelve wrong-algorithm mutations detected, each using the same acceptance
  cases. Examples change latest-predecessor scheduling to earliest-predecessor
  scheduling, stop pair coverage after one row, omit singleton cycles and reverse
  JSON Pointer escape decoding.
- Valid input schemas for success fixtures and valid output schemas for their
  results. Semantic refusal cases are checked separately; structural schemas
  alone cannot detect a graph cycle or a missing referenced field.
- Python 3.14.4 at `/usr/bin/python3`, run with `-I -S -B`. The package dependency
  declaration is Python 3.10 or later, but other interpreter versions were not
  executed in this lane.

Candidate code ran only inside a minimal Bubblewrap namespace with no network,
no mounted home directory and a cleared environment. The process could see the
read-only interpreter tree, one read-only candidate script, synthetic input and
the trusted test runner. It had a two-second CPU limit, 256 MiB address-space
limit and four-second wall timeout. The existing bounded `run_command` function
collected output. No credential or model provider was used.

[The sandbox control](sandbox-control.json) confirms that host homes were absent,
an external connection was refused and the candidate script mount could not be
written. This is evidence for those tested boundaries, not a general sandbox
escape audit. Nothing was installed into a user's native harness configuration.

## Search and staging

[The final staging report](staging-report-final.json) records twelve acknowledged
candidate writes through the existing authoritative catalogue contract. Normal
search returns zero candidates. Review search found each candidate within its
first three results for its title-derived probe. That is a search smoke check,
not a held-out relevance benchmark. The [export](staging-export-final.json)
contains the staged records; the SQLite database is an isolated local artifact.

## Reproduction and retained failures

`acceptance_cases.py` was written before the implementations. The
[initial record](before-authoring.json) records twelve missing implementations
against 51 cases. `author_packages.py` contains twelve explicitly authored method
implementations and their schemas. It refuses existing output paths; it does not
construct packages from a Cartesian product of titles, roles or occupations.

The first functional verification passed, but Markdown checks then found twelve
broken ordered-list continuations. A separate schema check found that the regular
expression end marker accepted an invalid trailing newline in an identifier.
Both failures and their original payload trees remain saved:

- [Markdown before](markdown-before-fix.txt) and [after](markdown-after-fix.txt).
- [Schema before](schema-before-fix.json) and [after](schema-after-fix.json).
- Earlier `authored/`, `prepared/` and `proposals.json`; current
  `authored-final/`, `prepared-final/` and [proposals-final.json](proposals-final.json).

The fixes preserve list nesting and use a strict end-of-string assertion in
JSON Schema patterns. All final-byte behavioral and mutation checks passed again.

To repeat the final verification with the repository Python environment, use a
new report path:

```bash
PYTHONPATH=src python3 artifacts/mixed-native-originals-2026-09-23/verify_packages.py \
  --packages artifacts/mixed-native-originals-2026-09-23/prepared-final/packages \
  --report /a/new/report.json --mutants
```

The generator and candidate factory do not approve their own outputs. Independent
review must still assess meaning, limitations, rights, effects, native loading,
relevance and task acceptance before any package is served.
