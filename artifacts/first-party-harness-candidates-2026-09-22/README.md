# Original harness intelligence candidate batch

Kind: isolated, first-party research batch for independent review. Created
September 22, 2026 against Loop Engine revision `0d1f883`. These files are
**candidates**. None is approved, released, granted, indexed by the hosted
service, or measured to improve a customer task. The authoritative work
state remains [roadmap S-6.40 and S-6.53](../../docs/roadmap/roadmap.yaml).

The owner asked Codex to start generating original harness intelligence
packages while Claude Code builds the production candidate factory. This
batch supplies native Agent Skills packages for Claude to inspect and copy
only after the repository's independent admission process qualifies the
exact bytes. It does not alter the active starter catalogue or host release.
The [generation guide](GENERATION-GUIDE.md) gives repeatable authoring rules,
known-wrong checks and the boundary between local candidate search and
hosted approved search.

```text
Original candidate batch
├── packages/
│   ├── data/         original data and analysis methods
│   ├── project/      original project and customer-work methods
│   └── software/     original software and harness methods
├── review-notes/     one task brief and known-wrong case per package
├── manifest.json     generated list of package paths and byte digests
├── make_manifest.py  exact-byte inventory and change detection
├── search_candidates.py  local candidate-only search for reviewers
└── README.md         this handoff and admission boundary
```

Each `SKILL.md` uses the
[Agent Skills specification](https://agentskills.io/specification): a
directory name matching frontmatter `name`, a task-specific description,
and instructions loaded only when selected. All packages in this first
batch are text-only methods. They include no executable script, bundled
dependency, server connection, credential, or claim to grant an effect.
The separate review note records intended inputs, output, effect class,
applicability facets, provenance, a positive example and a known-wrong
example. That note is not part of the native package to install.

The wording is original work by the Codex agent team. The agent team used
the owner's task and the repository's existing starter catalogue to choose
and distinguish methods. Individual notes identify any additional factual
source used. Generation call counts and costs are not captured by this
offline batch; do not infer zero. A customer distribution licence has not
been assigned. Missing rights, provenance, or exact-call evidence should
be recorded as a review finding, not silently filled in.

## Review and copy boundary

1. Check every name, description and native layout with the official
   reference package, currently invoked as
   `uvx --from skills-ref==0.1.1 agentskills validate PACKAGE_DIRECTORY` on this
   workstation. Its result proves format only.
2. Compare each task method with the active catalogue and other batch
   members. A new role, company, model or language label does not make a
   duplicate into a new logical method.
3. Independently review the exact bytes for accuracy, rights, hidden
   effects, secret handling, safety and a discriminating known-wrong case.
   A writer does not approve its own package.
4. Test the selected package in a supported native harness on held-out
   tasks, recording offered, fetched, loaded, used and verified separately.
   A native-load result or model confidence is not a benefit claim.
5. Assign a distribution licence and release identity only through the
   existing catalogue and review contracts. Recheck a package if its bytes
   change. Do not copy this entire batch into a customer's fresh harness;
   materialize only selected approved material.

The [first-party factory research](../../docs/research/FIRST-PARTY-TEN-THOUSAND-HARNESS-PACKAGES-2026-09-22.md)
explains how a measured campaign could scale this pattern. The current
batch demonstrates authored supply and gives the independent reviewer
concrete bytes; it does not validate the 10,000-item throughput target.

## Local reviewer search

The search tool checks the exact manifest and file digests, builds an
in-memory index, and returns bounded metadata cards. It reads review notes
for local discovery but does not return their text or the native body.
The cards include exact package, note and manifest digests. This is not
the hosted customer search path or a permission decision.

```bash
python3 artifacts/first-party-harness-candidates-2026-09-22/make_manifest.py --check
python3 artifacts/first-party-harness-candidates-2026-09-22/test_make_manifest.py
python3 artifacts/first-party-harness-candidates-2026-09-22/test_search_candidates.py
python3 artifacts/first-party-harness-candidates-2026-09-22/search_candidates.py \
  'convert kilograms and grams before adding' --group data
python3 artifacts/first-party-harness-candidates-2026-09-22/search_candidates.py \
  --name audit-measurement-units
python3 artifacts/first-party-harness-candidates-2026-09-22/search_all_candidates.py \
  --root artifacts/first-party-harness-candidates-2026-09-22 \
  --root artifacts/first-party-harness-candidates-2026-09-22-wave-2 \
  --root artifacts/first-party-harness-candidates-2026-09-22-wave-3 \
  'find the right skill for a customer task'
```

These commands run from the repository root. A typed `--required-effect`
other than `none` yields no match because this batch has no qualified
effects. The lexical ranking and relevance floor are useful for review;
they require separate production benchmarking and current account-grant
filters before customer use.
The [saved query set](search-probes.json) and
[development search result](SEARCH-EVALUATION-DEVELOPMENT-2026-09-22.json)
preserve the 24 of 24 rank-one result and five unrelated no-match cases.
Some queries were shared while the ranking was developed, so this is a
regression set, not a blind benchmark. The
[second batch](../first-party-harness-candidates-2026-09-22-wave-2/README.md)
exposed lower recall on fresh queries and retains that failed result.

For reviewer discovery across all three candidate batches, repeat
`--root` with [the multi-batch search tool](search_all_candidates.py).
`--check-only` verifies that the 68 current package names and exact body
digests are distinct across the three manifests. The
[saved combined evaluation](CROSS-BATCH-SEARCH-EVALUATION-INITIAL-2026-09-22.json)
found the expected item first for 47 of 68 task phrasings and within the
first three for 51 of 68; all 15 unrelated controls returned no match.
That result is a local reviewer-search diagnostic with one expected item
per query, not a claim that all relevant results were adjudicated or that
customer search is qualified.
