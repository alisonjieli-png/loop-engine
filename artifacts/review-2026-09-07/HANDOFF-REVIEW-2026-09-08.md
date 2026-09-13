# Review of the latest handoffs and catalog results

Reviewed: `docs/context/EVERYTHING-LEARNED-2026-09-08.md`, all 445 lines, at Loop Engine revision `acfd826eeee3ea2c05b638031ff235b709a69eb2`; the 30-axis catalog and its implementations; the current overnight catalog; the uncommitted Python catalog inside speculative_prompting; and the supplied live-run summaries. Other agents' implementations and handoff files were left unchanged.

The useful central conclusion survives: state representation, batching, verification, isolation and failure handling need separate experiments. The handoffs contain valuable negative results. They also overstate some wiring, persistence, selection and economic conclusions. These corrections matter before turning a chooser into runtime policy.

## Checks performed in this review

| Check | Observed result | Meaning |
|---|---|---|
| Axis catalog `registry.py check` | 30 embodiments, 7 families, check passed | Imports and component checks, including an actual container smoke. No model call was made |
| Latest frozen overnight catalog | 71 pytest tests passed in 22.68 seconds | Exact snapshot `8a6c4214c1cfaea4ab6b7f22468843d419310df2`, read-only source, writable disposable work area, network denied, clean virtual environment |
| Canonical lab | 19 tests passed in 5.277 seconds in the clean environment | Contracts, payload effects, process lifetime, cancellation, independent oracle, history, serving, reference preparation |
| Static memory inventory | 32 path-name matches: 14 reached, 18 unreached | Includes packages, facades, test modules and an unrelated catalog storage module |
| Actual import check | `loop_engine.memory` and `loop_engine.memory.semantic` were imported even though the static scan marked their `__init__` modules unreached | The scanner omits Python's implicit parent-package import behavior |
| Speculative_prompting catalog inventory | 33 non-hidden catalog folders; 15 contain nonempty Python implementation files | 18 remaining folders contain a README and empty initializer, not implemented solver code |
| Selector normalization probe | Programs returning `'allow'` and `'deny'` produced the same normalized vote key | String-literal normalization erases meaningful program differences |
| Global pandas probe | `qty=900`, threshold 50: expected false, observed true | The external startup hook alters evaluator behavior |

The separate source self-test attempted during this work timed out in the unchanged optional MCP SDK mismatch/cleanup test. Its seven checks passed alone. Claude's later full-suite pass, 3,412 checks in 1,392 seconds, is recorded in its handoff; it is not relabeled as a full-suite execution by this review. The source and clean-wheel conformance checks passed. The installed wheel also ran all six canonical mechanism arrangements successfully on three tasks each.

## 1. Correct the dark-memory recommendation

The scan does not establish that the whole memory subsystem is unused. Its reached set includes:

```text
memory.episodic.record
memory.semantic.record
memory.procedural.record
memory.working.state
memory.lifecycle.lifecycle
memory.query.query
memory.storage.learning_cycle
memory.storage.learning_records
memory.storage.repository
memory.storage.store
```

Some of these are reached only through imports inside checks. That is a limitation in the other direction: static reachability does not prove runtime use. Meanwhile, the unreached set contains package initializers that Python executes implicitly, compatibility facades, test modules, and `catalog.stores.in_memory`. It is not a list of eighteen missing end-to-end features.

The semantic learned-memory projection has a real solve-path caller. Its actual problems reproduced in the earlier review are weak relevance filtering and a filesystem exception outside its intended refusal boundary. Episodic/procedural serving and durable curation may still need meaningful integration, but their requirements should be stated as behaviors, not imports.

Reactive scheduling and output serving have different entry points from an ordinary solve. Our canonical lab now exercises them through their own APIs. Adding their imports to `solve_task` solely to increase its closure would be a misleading completion criterion.

Replace “wire all eighteen modules” with an entry-point inventory: which request needs which behavior, which typed configuration selects it, which actual operation executes, and which independent observation proves the promised effect. Keep L1 import, L2 invocation and L3 effect checks distinct. L3 must observe the trusted execution boundary; a logger repeating intended metadata is not enough.

## 2. Keep the axis experiments' evidence class precise

The context/batching findings are useful mechanism evidence. They demonstrate how a particular accumulator schema and world reader behave. They do not establish that a real model can reason equally well with the smaller packet or with sixty-four units grouped into one call. Batching also changes feedback latency and the size of a failed or retried unit.

The checkpoint arm stores `state` and `cursor` together, which is the correct invariant for that fixture. Its `Store` currently uses an in-memory dictionary; the `root` parameter is not used for persistence. The governed-journal arm similarly uses in-memory dictionaries/lists and promotes during its reviewer callback. There is no separately enforced authorizer in that implementation. Treat these as checkpoint and review-policy simulations, not disk-restart or production-governance qualification.

The container arm actually starts Docker, but uses the mutable tag `python:3.12-slim`. It does not pin or record a resolved image digest in the inspected evaluator, and its subprocess timeout does not explicitly stop a named container. Qualify image identity and cleanup before using it for untrusted code. The current canonical read-only OpenCode bridge has stronger lifecycle controls to use as design input.

The ratios comparing a sub-millisecond function with process/container startup are specific to a tiny fixture and a warm image. They should not be presented as durable universal multipliers. A model call or a long computation changes their share of total time substantially.

## 3. Incorporate the overnight race's fixes without overclaiming its economics

The newer catalog contains worthwhile protections, and the isolated 71-test run verified its current scripted harness. In particular, retain per-arm library isolation, no write-back for already-green/no-change tasks, original gate hashes through copied workspaces, and rejection of void candidates before selection and promotion.

Three inspected weaknesses remain relevant to further races:

- `engine_fingerprint()` hashes `base.py`, `race.py` and `core/sandbox.py`. It does not cover every shared module, arm implementation, environment or provider/harness setting. The README's claim that any shared-substrate edit changes the fingerprint is too broad for this implementation.
- `normalise_change()` collapses every string literal. Two behaviorally different programs can vote together. Normalize syntax carefully and retain semantic literals; add adversarial selector controls before treating diff consensus as reliable ranking evidence.
- The selector description includes a judge scored in both orders, but the inspected `select()` implementation proceeds from diff voting to shortest-diff tie-breaking without that judge rung. Keep the unimplemented step labeled as a plan.

“Cost per verified task is reliable at any sample size” is not a valid generalization. The observed ratio is calculable when its denominator is nonzero; its estimate of future cost is uncertain, especially with six tasks, already-green work, failures and rate limits. Report already-green checks separately from newly verified repairs. Report tokens as tokens unless source-backed monetary accounting exists.

Do not infer that one architecture wins from the partial live race. HTTP 429, unreadable/truncated inputs, missing model output and reasoning-budget exhaustion are distinct execution conditions. Preserve them, distinguish infrastructure validity from semantic failure, and freeze arm code, shared code, input/evaluator bytes, model route, memory baseline and environment before a matched rerun.

The new_overnight_build table is likewise a reported single-ticket comparison. One agent instance is not one physical model call. Its reported gateway failure is evidence about that model/architecture/budget combination, not a general rejection of direct gateways. No new live race or paid probe was launched here.

## 4. The global environment is contaminated

The inspected file is `/home/username/.local/lib/python3.14/site-packages/usercustomize.py`. Python startup loads it in the affected user environment. It replaces `pandas.read_csv`; frames with `qty` and `stock_status` columns get comparison objects that can report true for false conditions.

A benign controlled probe read a single row, `qty=900, stock_status=low`. `bool((frame['qty'] <= 50).all())` returned true; it must be false. This is not a valid fix for a broken chained-comparison gate. Affected measurements cannot be trusted without re-execution in an uncontaminated environment.

The file was not removed or edited. New qualification used a fresh virtual environment with user-site startup excluded, and the overnight catalog test additionally denied network and mounted its source read-only. Our three JSON-only mechanism workloads do not use pandas, but the clean-environment runs are the stronger evidence to retain.

The supplied handoff also reports an exposed `OLLAMA_API_KEY`. The key was not inspected or printed in this review. It should be rotated through the provider account before further live testing. Long-running OpenCode sessions owned by other work were not terminated.

## 5. How this is incorporated

The [related-catalog index](../../embodiments/RELATED-CATALOGS.md) connects the canonical launch surfaces, the 30-axis lab, whole-architecture races and source mirrors without pretending they are one interchangeable implementation. The newer overnight catalog is preserved beside the earlier mirror with its own provenance. The uncommitted speculative_prompting additions remain explicitly candidate material.

The remix and mutation plans now carry obligations for evaluator identity across restarts, state/cursor alignment, arm-memory isolation, failed-attempt accounting, semantic selector controls, environment integrity and actual route/call observations. Planned designs remain planned; successful imports or fixture tests do not silently promote them.

The next productive experiment is a small independently checked task population with immutable inputs/evaluators and a clean environment, comparing only already-qualified adapters under one exact authorized model contract. It should follow the fixture controls rather than replace them. A universal-solver claim and production overnight readiness remain separate from an executable experiment catalog.
