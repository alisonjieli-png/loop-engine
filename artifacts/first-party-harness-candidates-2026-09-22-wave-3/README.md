# Occupation-linked original harness candidates

Kind: third isolated candidate-only batch, started September 22, 2026
against Loop Engine revision `0d1f883`. The proposals come from the
[20 original method briefs](../occupation-grid-research-2026-09-22/next-method-briefs.md)
and their exact task identifiers in the pinned
[O*NET® 31.0 Database inventory](../occupation-grid-research-2026-09-22/README.md).
O*NET® 31.0 Database information is from the U.S. Department of Labor,
Employment and Training Administration under
[Creative Commons Attribution 4.0](https://www.onetcenter.org/license_db.html).
This batch adds original method instructions. The agency has not approved,
endorsed or tested them.

The [generation guide](../first-party-harness-candidates-2026-09-22/GENERATION-GUIDE.md)
governs the candidate shape. Every package has a native `SKILL.md` and a
separate note with its source task ID, conceptual contract, known-wrong
case and overlap comparison. Different job titles, employers, models and
client layouts are applicability facets, not duplicate package counts.
None of these files is approved, licensed for customer distribution,
granted, hosted or measured to help a customer task.

After all packages and notes are present, use the shared candidate-only
tools. Their manifest binds local bytes, not an active catalogue release:

```bash
python3 artifacts/first-party-harness-candidates-2026-09-22/make_manifest.py \
  --write --root artifacts/first-party-harness-candidates-2026-09-22-wave-3 \
  --base-revision 0d1f883bf470533543c9a4d8f52452ac84089548
python3 artifacts/first-party-harness-candidates-2026-09-22/make_manifest.py \
  --check --root artifacts/first-party-harness-candidates-2026-09-22-wave-3
python3 artifacts/first-party-harness-candidates-2026-09-22/search_candidates.py \
  --root artifacts/first-party-harness-candidates-2026-09-22-wave-3 \
  'customer task description'
python3 artifacts/first-party-harness-candidates-2026-09-22-wave-3/check_source_refs.py
python3 artifacts/first-party-harness-candidates-2026-09-22-wave-3/test_check_source_refs.py
```

The base revision does not contain these new exact bytes. Claude Code
must assign a committed revision and run the independent catalogue review
before any copy into a host release. The local search command is only for
reviewer discovery and cannot grant a body read or execution authority.
The source-reference check verifies 20 notes with 21 pinned occupation
task IDs and refuses a complete source task statement copied into a
native skill. It cannot establish independent originality or usefulness.
The [frozen independent query set](search-probes.json) and
[initial local search result](SEARCH-EVALUATION-INITIAL-2026-09-22.json)
record 13 of 20 expected candidates at rank one, 13 in the first three,
and five of five unrelated queries returning no match. Seven relevant
queries failed to find their intended candidate. Preserve those failures
when comparing a later search engine; these candidates are not fully
searchable by natural task language yet.
The [successor evaluation](SEARCH-EVALUATION-AFTER-CONTENT-REPAIR-2026-09-22.json)
binds the current manifest after a content correction and records the
same search counts. The initial report stays beside it so its earlier
exact bytes and result are not silently overwritten.
