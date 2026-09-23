# Original harness candidate batch: preparation and local search check

Kind: dated candidate-batch verification, September 22, 2026 local time.
The [isolated batch](../../artifacts/first-party-harness-candidates-2026-09-22/README.md)
was prepared against repository revision `0d1f883`. Its current
[manifest](../../artifacts/first-party-harness-candidates-2026-09-22/manifest.json)
has SHA-256
`85eb74823631bb520690e9c486e535c6f1564549761ed4723e759f93fed20bde`.
The starting revision does **not** contain these new candidate bytes; their
individual digests are in the manifest. The
[roadmap](../roadmap/roadmap.yaml) remains the only task authority.

## What exists

| Group | Native `SKILL.md` candidates | Separate review notes |
|---|---:|---:|
| Data and analysis | 8 | 8 |
| Project, product and customer work | 8 | 8 |
| Software and harness work | 8 | 8 |
| Total | 24 | 24 |

Each package is an original, focused text-only Agent Skill candidate.
The [generation guide](../../artifacts/first-party-harness-candidates-2026-09-22/GENERATION-GUIDE.md)
sets method distinctness, source, format, authority and known-wrong rules.
The review notes carry conceptual contracts, applicability, rights basis,
effects, examples, overlap comparisons and search phrasings. No package
contains a script, protocol server configuration or credential. A
cross-review found and repaired substantive draft errors, including an
incorrect offer-cost example, event-replay order, reporting visibility,
cohort-rate windows, budget eligibility for engine selection, cache
first-writer trust, and treatment of untrusted ticket or model text.
Those repairs are **author revisions of candidate bytes**, not an
independent approval.

The batch manifest records `approval_state: none`,
`rights_state: pending_independent_review`,
`effect_qualification: none`, and `benefit_evidence: unmeasured`.
No candidate was imported into the active catalogue, granted to an
account, released, natively loaded in a customer run, or evaluated for
customer benefit. Customer distribution terms have not been assigned.

## Checks run on the exact batch

| Check | Observed result | Limit |
|---|---|---|
| Agent Skills reference validator, `skills-ref==0.1.1` | 24 of 24 native folders valid | Format and naming only. |
| `make_manifest.py --check` | 24 candidate and note pairs match exact recorded bytes | No rights, semantic quality or native-load judgment. |
| `test_make_manifest.py` | 7 tests pass, including changed bytes, missing note, duplicate slug, extra file, symlink refusal and a second batch root | Tests candidate inventory mechanics only. |
| `test_search_candidates.py` | 11 tests pass, including stale bytes, tampered manifest, query injection and no-answer behavior | Local candidate search only. |
| Markdown lint | 51 batch and placement Markdown files, zero issues | Prose structure only. |
| Ruff | Candidate batch Python files pass | Code style and static lint only. |

The local [search command](../../artifacts/first-party-harness-candidates-2026-09-22/search_candidates.py)
validates the manifest and file digests, then builds an in-memory SQLite
full-text index of the package name, description, skill text and
task-relevant review-note lines. It returns bounded metadata cards with
package, note and manifest digests, without body text. Exact name, group
and typed required-effect arguments are available. Any non-`none` required
effect yields no match because this batch has no qualified effect.

An independent reviewer wrote 24 natural task queries, one for each
package, and five unrelated queries. The initial lexical floor found
only 6 of 24 expected packages in the top three. After general ranking
changes and author-supplied discovery phrases, the final pilot found
24 of 24 expected packages at rank one, with no extra returned cards;
all five unrelated queries returned no match. The first 12 task queries
were shared for development. The other 12 were reserved for final review,
although two example failures from that half were disclosed while
diagnosing the initial result. This is a small English-language
regression set, **not** a fully blind customer-query benchmark. A relative
score floor can also hide a useful second item. Two effectful near-negative
queries returned no match when given the typed `file_write` requirement;
plain text alone must not be used to infer effect authority.
The [query set](../../artifacts/first-party-harness-candidates-2026-09-22/search-probes.json)
and [saved development result](../../artifacts/first-party-harness-candidates-2026-09-22/SEARCH-EVALUATION-DEVELOPMENT-2026-09-22.json)
retain the exact cases and search-tool digest. The
[second batch's independent query result](SECOND-ORIGINAL-HARNESS-CANDIDATE-BATCH-QA-2026-09-22.md)
is the more useful generalization check.

## Admission and hosted search handoff

The existing [candidate preparer](../../tools/prepare_harness_candidates.py)
rejects YAML-frontmatter bodies, so it cannot simply ingest these exact
native `SKILL.md` files. Claude Code needs a qualified adapter that keeps
the package name, file layout and approved byte identity intact. The
[host manifest builder](../../tools/build_host_catalogue_manifest.py)
already requires independent exact-byte approvals, a known licence and
matching digest and size; this local candidate manifest is **not** a host
manifest. Save a committed exact-byte source revision before admission.

The [current hosted search](../../src/loop_engine/core/service_runtime/http.py)
uses approved, granted item metadata and does not index these candidates.
The local search result is therefore not proof of customer searchability.
Production work belongs under S-6.32, S-6.40, S-6.44, S-6.45 and S-6.62:
structured task and applicability facets; measured relevance and no-answer
behavior; grants filtered before ranking and rechecked at body read;
versioned catalogue releases; withdrawn-item denial; and a
[client-native placement profile](../research/NATIVE-HARNESS-INTELLIGENCE-PLACEMENT-2026-09-22.md).

Named known-wrong integration checks should refuse an unapproved package
in the host manifest, a changed native byte or wrong destination, a weak
search hit below the relevance floor, a revoked grant during search or
body read, and a withdrawn final item that leaves an old grant active.
An older host must refuse an incompatible new release record. Reuse the
existing catalogue and service test suites for these checks; do not
promote candidates through the local search tool.
