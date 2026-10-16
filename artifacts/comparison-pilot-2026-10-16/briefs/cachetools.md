# AgentBriefs demonstration brief: cachetools 7.2.2

Kind: demonstration brief for the AgentBriefs proposal, written by engineering
on October 16, 2026 from dated public sources. It is not output of a qualified
AgentBriefs service. Every benefit below is a hypothesis to test. No experiment
has run, so this brief reports no realized benefit. The machine-readable form is
[cachetools.json](cachetools.json).

## Project as observed

[cachetools](https://github.com/tkem/cachetools) is a pure-Python library of
memoizing caches. It is MIT-licensed, has 2,787 GitHub stars and is listed under
Caching in [awesome-python](https://github.com/vinta/awesome-python). Version
7.2.2 was uploaded to [PyPI](https://pypi.org/project/cachetools/7.2.2/) on
October 15, 2026, with no runtime dependencies.

- The continuous integration matrix at v7.2.2 already runs Python 3.10 to
  3.15, the free-threaded builds 3.13t, 3.14t and 3.15t, and PyPy 3.10 and
  3.11 (`.github/workflows/ci.yml`).
- Several recent releases fixed cache bookkeeping in edge cases. 7.1.5 (July
  23) fixed "TLRUCache silently keeping stale values on expired overwrites".
  7.1.7 (August 1) improved `Cache.__setitem__` when an item is replaced by a
  larger value. 7.2.2 (October 15) improved `TTLCache` robustness when
  calculating an expiration time fails (`CHANGELOG.rst`).
- In pilot task a, OpenCode with `gemma4:31b` recreated `TLRUCache` from the
  documentation four times, twice in each arm. Each run passed 31 of the 34
  held-out TLRUCache tests and failed the same three: `test_ttu`,
  `test_ttu_expired` and `test_ttu_reverse_insert`
  ([pilot report](../../../docs/verification/COMPARISON-PILOT-2026-10-16.md)).
- The repository keeps an AI-assisted review record,
  `.github/copilot-review.md`, dated October 15, 2026, and Copilot
  instructions in `.github/copilot-instructions.md`.

## Opportunities worth one bounded experiment

### CT-1. Stateful property tests for the timed caches

- **Evidence.** The three bookkeeping fixes above came between July and
  October 2026. [Hypothesis](https://pypi.org/project/hypothesis/) 6.170.0
  (MPL-2.0, uploaded October 15, 2026) provides rule-based stateful testing
  against a reference model.
- **Estimated benefit, a hypothesis.** A model-based test of `TTLCache` and
  `TLRUCache` driven by a fake timer would have found the 7.1.5 stale-value
  bug, and it may find similar faults before a release. The cost is test time
  and one test-only dependency.
- **Experiment.** Write one `RuleBasedStateMachine` that applies random sets,
  gets, deletions, timer advances and `expire()` calls to a cache and to a
  dictionary-plus-expiry reference. Run 2,000 examples against v7.1.4, the
  known positive, and against v7.2.2. Accept if it reports the stale-value
  failure on v7.1.4 within the run and nothing on v7.2.2, and the run takes
  under 60 seconds. Keep every failing example.

### CT-2. State that time-to-use values can expire out of insertion order

- **Evidence.** All four pilot runs built `TLRUCache` on `TTLCache`'s
  insertion-ordered linked list. That list assumes items expire in the order
  they were inserted, which holds for one fixed time-to-live but not for a
  time-to-use function. The upstream class keeps a heap ordered by expiration
  time instead. The three tests every run failed insert items whose
  expiration times run against insertion order, or that are already expired
  when inserted. The documentation of `TLRUCache` in `docs/index.rst` begins
  "Similar to TTLCache, this class also associates an expiration time with
  each item" and does not state either case. The task prompt
  also pointed at `TTLCache`, so the prompt may have encouraged the same
  reading.
- **Estimated benefit, a hypothesis.** One documented sentence and one
  doctest, saying that expiration times may come in any order and that an
  item already expired at insertion is never stored, would stop the same
  misreading by people and by coding agents. The cost is a few lines of
  documentation.
- **Experiment.** Repeat pilot task a with the same model, harness and budget
  six times with the current documentation and six times with the added
  sentence, removing the pointer to `TTLCache` from the prompt in both.
  Accept if the three tests pass in at least four of six runs with the
  sentence and in at most one of six without it. Report every run.

## Considered and not recommended

- **Withheld: an agent-memory server as a smarter cache.** A directory search
  for memoization returned
  [Memoize, persistent agent memory](https://github.com/harrisonford/memoize)
  (updated August 29, 2026). GitHub Trending's monthly Python view also showed
  agent-memory projects, such as vectorize-io/hindsight with 26,652 stars that
  month. These store an agent's cross-session memory. They do not memoize
  function results, so a matching word and a popularity count are not
  evidence that they fit cachetools. The brief raises no alert for them.
- **Already in place: AI-assisted code review.** The repository's
  `.github/copilot-review.md` (October 15, 2026) records findings from an
  AI-assisted review of 7.2.2. Recommending another reviewer, such as the
  CodeRabbit service whose free open-source tier its
  [October 8 post](https://coderabbit.ai/blog/one-million-open-source-reviews-september-2026)
  describes, would duplicate it without evidence that it finds more.
- **Already in place: free-threaded and Python 3.15 testing.** Python 3.15.0
  was released on October 9, 2026
  ([endoflife.date](https://endoflife.date/python)), and the CI matrix already
  covers 3.15 and 3.15t. Recommending it would repeat existing work.
- **Advisories: none listed.** [OSV](https://osv.dev) returned no advisory
  for cachetools 7.2.2 on October 16, 2026. An empty answer is not a security
  certificate, so the brief raises nothing.
- **Maintenance note, no experiment needed.** Python 3.10 reached end of life
  on October 1, 2026 (endoflife.date), and 7.2.2 still declares
  `requires-python >=3.10`. When to drop 3.10 is the maintainer's choice.
  This brief lists the date and makes no recommendation.

## Sources read on October 16, 2026

| Source | What it supplied |
| --- | --- |
| PyPI JSON for cachetools and hypothesis | Versions, upload dates, licences, classifiers |
| cachetools v7.2.2 tree (commit `be0b2eba`) | CI matrix, changelog entries, documentation |
| endoflife.date Python product | 3.15.0 release date, 3.10 end of life |
| OSV query for cachetools 7.2.2 | No advisory listed |
| CodeRabbit blog, October 8, 2026 | Open-source review counts and free tier |
| This pilot's trial records | TLRUCache runs and the three failed tests |
| Baltor MCP directory data | Memoization search results |
| GitHub Trending, monthly Python | Agent-memory projects and their monthly stars |
| Baltor model directory | No row bears on this library |
| Baltor research watch | No watched source bears on this library |
