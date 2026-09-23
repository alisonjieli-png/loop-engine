# Occupation-linked candidate batch and combined local search check

Kind: dated candidate-only verification, September 22, 2026 local time.
The [third batch](../../artifacts/first-party-harness-candidates-2026-09-22-wave-3/README.md)
turns all [20 original method briefs](../../artifacts/occupation-grid-research-2026-09-22/next-method-briefs.md)
into 20 native `SKILL.md` candidates and 20 separate review notes.
The current [exact-byte manifest](../../artifacts/first-party-harness-candidates-2026-09-22-wave-3/manifest.json)
has SHA-256
`b06f1a5a15127dbed6c3e3f0d6580e1dcad31953bc430a9d9bb6db7656cc3c7f`.
It names a research base revision that predates these new files, not a
commit containing their bytes. The [roadmap](../roadmap/roadmap.yaml)
remains the task authority.

## Candidate and source checks

The batch has seven data methods, seven project methods and six software
and documentation methods. Its notes cite 21 exact task identifiers
from ten occupations in the pinned
[O*NET® 31.0 Database subset](../research/OCCUPATION-TASK-OPPORTUNITIES-2026-09-22.md).
The [source check](../../artifacts/first-party-harness-candidates-2026-09-22-wave-3/check_source_refs.py)
confirmed all 20 notes and 21 references, and screened against copying
a complete source task statement into a native skill. Four negative
controls passed, including a fabricated task ID and a planted complete
source statement. A separate lexical review found no contiguous
five-word span shared with the 179 pinned source task statements and at
most one generic seven-word span shared with an earlier catalogue item.
These are screens, not proof of legal originality.

Authors and independent readers found two material draft issues and
repaired them before the current manifest was written. The obsolete-stock
method now caps supported stock by uniquely assigned compatible demand;
one supported use cannot cover an entire older-revision inventory. The
prebuilt-application method now separates a documented interface claim
from an independently observed interaction and holds a qualified fit
claim when mandatory failure or permission semantics are untested.
Independent review found no remaining concrete blocker to **retaining
these bytes as candidates**. It did not grant an approval.

| Check | Observed result | Limit |
|---|---|---|
| Agent Skills reference validator `skills-ref==0.1.1` | 20 of 20 native folders valid | Format and naming only. |
| Candidate manifest `--check --root wave-3` | 20 exact package/note pairs match | Local byte identity, not admission. |
| Source reference check and its tests | 20 notes, 21 pinned task IDs; 4 tests pass | No semantic task or rights judgment. |
| Markdown lint | 41 batch Markdown files, zero issues | Prose structure only. |
| Independent content read | Corrected two issues; no further concrete candidate blocker found | No native task run or domain expert approval. |

## Preserve search failures

An independent reviewer wrote [20 task phrasings and five unrelated controls](../../artifacts/first-party-harness-candidates-2026-09-22-wave-3/search-probes.json)
before searching. The
[initial result](../../artifacts/first-party-harness-candidates-2026-09-22-wave-3/SEARCH-EVALUATION-INITIAL-2026-09-22.json)
on predecessor manifest `3ff47efe...` found the expected package first
for **13 of 20** queries and in the top three for the same 13. Seven
relevant queries returned no match. Five of five unrelated controls
abstained. A content repair changed one skill's bytes, so a
[successor result](../../artifacts/first-party-harness-candidates-2026-09-22-wave-3/SEARCH-EVALUATION-AFTER-CONTENT-REPAIR-2026-09-22.json)
was saved under a new name against the current manifest; the counts
remained 13 of 20 and five of five. Neither result is a customer or
hosted-search benchmark.

The [multi-batch reviewer tool](../../artifacts/first-party-harness-candidates-2026-09-22/search_all_candidates.py)
validated all three manifests together and refused duplicate package
names or exact native body digests. It counted **68 candidate packages**:
24 in batch one, 24 in batch two and 20 here. Five focused tests passed,
including stale-byte and duplicate-name refusals. Its
[saved combined evaluation](../../artifacts/first-party-harness-candidates-2026-09-22/CROSS-BATCH-SEARCH-EVALUATION-INITIAL-2026-09-22.json)
put the expected file first for **47 of 68** task phrasings, in the top
three for **51 of 68**, and returned no match for **15 of 15** unrelated
controls. The first 24 queries were used during search development; the
next two batches supplied fresher probes. Each query has one expected
item, so an alternate useful result was not independently adjudicated.
The tool rebuilds local indexes and is neither scalable hosted retrieval
nor an access-control boundary.

## What Claude Code can pick up

The [generation guide](../../artifacts/first-party-harness-candidates-2026-09-22/GENERATION-GUIDE.md)
and [native placement research](../research/NATIVE-HARNESS-INTELLIGENCE-PLACEMENT-2026-09-22.md)
define the next gates. Review and license each exact candidate package;
record a committed source revision; preserve `SKILL.md` frontmatter and
relative resources through a qualified adapter; place only selected
approved items in a fresh client's native directories; and prove listed,
loaded, used and verified separately. Improve production search using a
new frozen query population and a no-answer floor rather than tuning on
these saved probes. The candidate count is not an approved, hosted or
beneficial-item count.
