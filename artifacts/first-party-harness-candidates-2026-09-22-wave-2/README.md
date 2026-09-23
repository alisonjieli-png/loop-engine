# Original harness intelligence candidate batch two

Kind: isolated, candidate-only research batch, started September 22, 2026
against Loop Engine revision `0d1f883`. The owner asked Codex to keep
generating and reviewing material while Claude Code is unavailable. This
batch extends the [first 24-package pilot](../first-party-harness-candidates-2026-09-22/README.md)
with new task methods chosen across data, project and software work.

The [generation guide](../first-party-harness-candidates-2026-09-22/GENERATION-GUIDE.md)
applies here. Authors search both the 123 starter items and the first
batch before writing, then record the closest method and a known-wrong
case in a separate review note. A job title, company type, project phase
or model label alone is not a new method. These files are not approved,
licensed for customer distribution, hosted, or tested to improve tasks.

Use the first batch's exact-byte and local-search tools against this
batch root after all package and review-note files are present:

```bash
python3 artifacts/first-party-harness-candidates-2026-09-22/make_manifest.py \
  --write --root artifacts/first-party-harness-candidates-2026-09-22-wave-2 \
  --base-revision 0d1f883bf470533543c9a4d8f52452ac84089548
python3 artifacts/first-party-harness-candidates-2026-09-22/make_manifest.py \
  --check --root artifacts/first-party-harness-candidates-2026-09-22-wave-2
python3 artifacts/first-party-harness-candidates-2026-09-22/search_candidates.py \
  --root artifacts/first-party-harness-candidates-2026-09-22-wave-2 \
  'customer task description'
```

The manifest is candidate integrity evidence only. Claude Code must use
the repository's independent exact-byte review and active catalogue
contracts before copying any item into the service. The source revision
above predates these uncommitted bytes; it is a research baseline, not a
commit containing this batch.

The [independent query population](search-probes.json) and
[initial saved search result](SEARCH-EVALUATION-INITIAL-2026-09-22.json)
preserve the local search's weaker second-batch performance: 14 of 24
expected files at rank one, 16 in the first three, and five of five
unrelated queries returning no match. Reproduce the result with
`evaluate_search.py` from the first batch and a **new** output filename;
it refuses to overwrite an earlier report. This is local reviewer search,
not a customer relevance or benefit claim.
