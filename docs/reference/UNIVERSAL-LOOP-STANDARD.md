# Universal Loop Standard — Migration Blueprint

Status: CURRENT (registered in `conformance_report.CURRENT_DOCS`).
Date: 2026-08-24. This is the doctrine-to-code bridge for the Universal Loop
Standard; it names what is already executable, what is newly decided, and the
exact migration phases. The current package and conformance tests are the
executable authority for this repository;
this document carries the migration detail so the prompt stays readable.

## 1. What the standard decides (the deltas worth recording)

- **Precise principle:** *every ACTIVE unit of work* runs through the governed
  loop protocol. Contracts, edges, artifacts, frozen plans, policies, evidence,
  and receipts are DATA; capabilities, executions, slot invocations, searches,
  verifications, repairs, and campaigns are WORK and so run in a loop envelope.
- **Acceptance, not invocation, completes work.** A loop that may fall back is
  not "one iteration" — it requires **one ACCEPTED success**, with iteration /
  attempt / accepted-success as separate counters. A failed deterministic
  attempt does not count; a verified hybrid fallback satisfies it.
- **The identity ladder:** LoopDefinition → LoopSpec → EffectiveLoopSpec →
  LoopRun → LoopSegment (continue-as-new) → LoopIteration → LoopAttempt →
  LoopResult. None of these is a synonym for another.
- **Three loop levels, one protocol:** execution loop / task-semantic loop /
  search-improvement loop. The improvement loop stays OUTSIDE the executable
  Solution graph and never self-admits.
- **The controller is replay-deterministic**; nondeterministic work happens in
  declared, recorded attempts. Record the actual replay guarantee (exact /
  event-equivalent / evidence-equivalent / none), never infer it from a seed.
- **Escalation requires a typed trigger**, and de-escalation is first-class.
- **The Intelligence Search Fabric (ISF)** is distinct from the Capability
  Directory: ISF answers "what evidence is relevant?", the Directory answers
  "what can execute this capability?". `OCI` stays reserved for its industry
  meaning (Open Container Initiative).

## 2. What is already executable (verified at 819/819, 15/15)

| Standard concept | Existing, proven code |
|---|---|
| one baseline per loop | `loop/loop_contract.py::LoopContract` — typed goal, input/output roles, mode classification (execution↔runtime map derived, never conflated) |
| the declarative baseline | `loop/loop_doctrine.py::LoopBaseline` — goal + typing + stop + waterfall, closed vocabs, cheapest-first, leapfrog refused |
| code loops / solution loops as loops | `encapsulate.as_practitioner_loop` / `as_component_loop`; every Solution component executes as a PractitionerLoop (`run_solution` cannot reach a callable directly) |
| nine-step as a loop of nine loops | `encapsulate.as_loop_of_stage_loops` — 9 spawns, 9 child returns, one receipt each |
| public vocabulary | `SolutionSpec(loops=...)`, dict key `"loops"`, `kind="loop"` in the store vocab; the SaaS/Studio projections and `saas_routes` serve `"loops"`; a scanner detector guards the renamed surfaces |
| replay/determinism rail | the §12 one-semantic-call-per-iteration boundary; `model_boundary_deferred` defers a semantic fallback visibly to the next iteration |
| the closed Chronicle vocabulary | `chronicle.to_canonical_events` total/lossless; 59 families machine-enforced |

## 3. What remains to build (the migration phases, ranked)

| Phase | Work | Gate |
|---|---|---|
| **A. Acceptance semantics** | Replace "stop condition = first iteration" with `accepted_success_target` + attempt counters in `LoopBaseline`; add the completion-policy vocabulary (`success_once`, `success_quorum`, `until_goal`, …) and wire it into the runtime's iteration engine so a verified fallback satisfies the loop | one loop with a failed deterministic + accepted hybrid iteration proves "accepted-success ≠ attempt"; the suite stays green |
| **B. Identity ladder** | Surface `run_id / segment_id / iteration_id / attempt_id / spec_digest` on every ledger event; add a `continue_as_new` segment link for long runs | a crashed-and-resumed multi-segment run reconstructs identical state |
| **C. The three levels** | Add `loop_level` to `LoopBaseline` (`execution` / `task_semantic` / `search_improvement`); enforce the authority boundary (improvement loops cannot self-admit) | a search-improvement loop attempting to promote fails closed |
| **D. Replay guarantee** | Extend the loop contract with a `replay_guarantee` axis (exact / event-equivalent / evidence-equivalent / none); record it on every attempt | a replay-equivalence check across two identical deterministic runs |
| **E. Wire it as THE constructor** | Make `LoopBaseline`/`LoopContract` the standard spawn/constructor path; SolutionSpec's loops compose through `baseline_for_solution_loop`; emit the baseline on LoopSpec + Chronicle | the suite and a live canary pass with every loop on one baseline |
| **F. ISF as a distinct fabric** | Separate the retrieval provider handshake from the capability handshake; keep RRF the deterministic fusion baseline; two providers per plane swappable under the same conformance tests | a provider swap preserves result schema + receipt completeness |

Phase A and B precede the others; E is the convergence point. Do NOT wire the
baseline into `run_next_iteration` as the spawning authority until A–D land —
that keeps the migration an extension, not a runtime rewrite.

## 4. Research grounding (why this shape)

The standard borrows the durable lessons, not the products: Temporal / Durable
Task (deterministic orchestrator + event-history replay; continue-as-new;
never blindly retry unchanged deterministic logic) · Kubernetes (desired-vs-
observed reconciliation) · AWS Step Functions (typed retry vs catch/fallback) ·
Sagas (compensation, not fake exactly-once) · W3C SCXML (compact normative state
machine) · structured concurrency (child lifetime/cancellation propagate) ·
SPARQL federation + RRF (federated search, deterministic fusion by rank, never
by raw score) · Tree-sitter / SCIP / CodeQL (code intelligence is symbol /
syntax / reference / type / dataflow retrieval, not only embeddings) · and the
agent literature's caution that **unaided self-correction is unreliable** — so
reflection is one proposal arm, with external tools/tests and independent
verifiers gating acceptance and promotion.

## 5. Verification

```bash
PYTHONPATH=. python3 -m loop_engine --self-test    # 819/819 at generation
PYTHONPATH=. python3 -m loop_engine --conformance  # ALL GATES PASS
```
