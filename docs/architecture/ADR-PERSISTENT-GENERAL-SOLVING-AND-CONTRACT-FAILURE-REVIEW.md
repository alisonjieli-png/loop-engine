# Persistent general solving and contract failure review

Status: proposed and partly implemented. Owner requirement recorded on
September 14, 2026. A declared supervision policy on solve requests,
recoverable format repair stalls, persistent orientation, the action vector
guard on recovery panel routes, and verifier format repair are implemented
and pass offline checks. No proposed invariant is qualified yet.

## Owner direction

On September 14, 2026, the owner gave these directions for Loop Engine:

1. Move toward generalized solving in which every applicable approach is
   tried, the work is highly persistent, and the system does not give up.
2. Do not build one-off solutions. Build a general cognitive and action
   Practitioner Loop that thinks, acts, and writes tools as needed.
3. When any check fails, start a waterfall of reviews that asks whether the
   test is the problem, whether the test is too arbitrary, or whether other
   edits are needed, across every aspect of the work.
4. Make every contract deterministic, hybrid, or model-reasoned, so that a
   failed contract can be asked whether it was supposed to fail or failed
   unreasonably.
5. Keep these rules and this guidance in the Constitution and the governing
   Markdown files.

This record places those directions in the existing architecture, lists where
the current solve path departs from them, and names the tests that will show
whether an implementation works. The proposed invariants are in the
[Constitution](CONSTITUTION.md#proposed-invariants-from-owner-direction).

## Ownership

```text
Operational runtime type
└── Loop
    ├── Operational relationship: Starting, Spawned by, Queried by, Retrieved by, Connected from
    ├── Role: Practitioner, Intelligence, Solution
    ├── Versioned role profile
    ├── Purpose and domain categories
    ├── Run mode: deterministic, hybrid, non-deterministic
    ├── Step profile
    ├── Typed input and output contract
    ├── Loop condition
    ├── Exit condition
    ├── Graph relationships
    ├── Budget, permissions, and effect policy
    ├── Model settings when the selected mode permits a model
    └── Run History records
```

Nothing here adds a runtime type, role, or run mode. Persistence, review, and
tool writing are work owned by existing Loops:

```text
Starting Practitioner Loop
├── Recovery and supervision decisions after each failed step
├── Spawned Practitioner Loops for subproblems
├── Spawned verifier Loops for independent checks and failure review
│   ├── classify the failure
│   ├── confirm a proposed check change
│   └── test that a revised check still discriminates
└── Tool candidates written into the declared sandbox
    └── qualified by a process other than the builder
```

## Decision

### Persist within declared authority

A run continues while a safe authorized next action and declared authority
remain. A run may end only for one of these recorded reasons:

- an accepted result that passed the required verification,
- exhausted authority that the owner or the request declared, such as model
  calls, passes, time, or spending,
- a question or authority request that only the owner can answer,
- an operator cancellation,
- a provider outage, recorded so the run can resume.

Each failure becomes a typed next action chosen from options that the
existing recovery and supervision decisions own: repair, reframe, another
method from the work function catalog, a Spawned subproblem Loop, a permitted
fallback harness or model, a request for material, or resumption after an
interruption.

Persistence never grants authority. It does not repeat an external effect,
invent a budget, raise a declared budget, or replace a failed model call with
canned output. Exhausted declared authority ends the run with its own terminal
code, not with a verification failure.

### Build general mechanisms

Task knowledge enters through typed context, capabilities, skills, contracts,
and generated artifacts. The runtime has no control flow, prompt, or check
written for one task, dataset, or benchmark. The same Practitioner Loop
orients, decides, acts, verifies, and writes tools when a task needs one.

A tool written during a run is a candidate. It runs only in the declared
sandbox. It is reused within the run only after checks written by a process
other than its builder pass. It is reused across tasks only after Code
Intelligence admission, which already refuses a producer as the only verifier
(`core/code_intelligence_assets.py`).

### Declare how every contract check is evaluated

Every contract check declares its evaluation mode:

- **deterministic**: code decides, for example a schema, an exit code, or an
  exact comparison,
- **hybrid**: code applies a policy that a model chose and an independent
  review approved, for example a declared comparison policy with a numeric
  tolerance,
- **model-reasoned**: a model judges against stated criteria, and the judgment
  is recorded as a model observation, not as a fact.

An evaluation mode describes how an outcome is decided. It is not a Loop run
mode and it grants no authority.

### Review every failed check

When a check fails, the owning Loop records the failure and starts a review
before it repairs the work or changes the check:

1. **Record.** Run History keeps the failed check, its evaluation mode and
   version, the expected and observed values, and the environment. Nothing is
   deleted or rewritten.
2. **Classify.** A Spawned verifier Loop with a fresh context and no access to
   the producer's plan classifies the failure as one of: correct failure,
   wrong expectation, check stricter than the task requires, environment or
   harness defect, ambiguous requirement, or unknown.
3. **Confirm.** A classification that would change or relax the check needs a
   second independent review, with a different model route when the policy
   permits one. Agreement between attempts that share one context does not
   count as confirmation.
4. **Discriminate.** A revised check must still reject at least one
   known-wrong answer, such as a mutated subject or a recorded failing
   candidate.
5. **Act.** A correct failure routes to repair and names the part of the work
   that needs edits: implementation, interface, inputs, output format,
   dependencies, configuration, or plan. A confirmed check defect creates a new
   check version that keeps the old version and its failure. An environment or
   harness defect routes to that adapter or sandbox. An ambiguous requirement
   becomes a recorded assumption with a delegated default, or a question when
   only the owner can decide.
6. **Account.** Every review step spends shared model authority and appears in
   Run History with its evidence.

The same review applies to development checks in this repository. Before a
failing test or the code changes, establish which one is wrong. On September
14, eleven failed self-test checks first looked like a runtime regression; the
review showed that a scripted fixture was stale and the stricter contract was
correct, so only the fixture changed.

### Never waive an authority contract

Permission, secret, network, spending, sandbox, and external effect contracts
are authority contracts. A review may explain why one failed and may propose
a policy change for the owner. It cannot waive the contract, relax it, or
approve its own proposal. This follows LE-DOC-001, LE-TRUST-001, LE-INTEL-003,
and LE-GOV-001.

## Current state

A read-only map of the solve path and the saved live campaign records at
commit `89553f2` found these departures. Line references are at that commit.
The live cell counts come from the saved records, not from new runs.

| Departure | Evidence |
|---|---|
| Four inadmissible outputs for one step, or one byte-identical repeat, raise `ModelResponseRepairStalled`, and several steps do not catch it. In the saved records it ended two of the eight executed live cells. Later on September 14 orientation, verification, project generation, routing, and the recovery panel began treating the stall as a recoverable failure. | `core/adaptive_practitioner_records.py:376`, `:2555-2569`, `:2857-2871` |
| After a stall, the recovery panel's route, including `stop_unprofitable`, is adopted without running the action vector route guard again. The saved records of the two live cells that delivered artifacts end with this route. Later on September 14 the panel's route began passing the same guard and final acceptance binding as the model's route. | `core/adaptive_practitioner_routing.py:130-138` |
| An independent verifier response that is not admitted raises at once, with no format repair, and the report becomes `unavailable`. Later on September 14 the verifier began repairing the response format within declared call authority. | `core/independent_verification.py:243-256` |
| A failed independent check forces repair, and the retained probe is reused on later passes. Nothing asks whether the probe is wrong. | `core/independent_verification.py:285`, `:355` |
| Two rejected orientation proposals raised an error, which ended any run without an earlier accepted orientation. In a live Ollama Cloud rerun on September 14 this ended five of the first nine trials after two model calls: the prompt showed the step objective as the task's immediate goal, and the model copied it into its proposal. Later that day orientation began repairing the whole record, then the named fields, and then carrying an orientation forward with its findings. | `core/adaptive_practitioner.py:195`, `:282-284`, and `core/adaptive_practitioner_records.py:2415-2417`, at commit `41cb7ae` |
| `SolveRequest` had no supervision policy field, so every solve run used the default policy. Later on September 14 the request gained a typed policy that reaches the Starting and Spawned Practitioner Loops. | `code_nodes/solve_request_adaptation.py`, `code_nodes/solve_runtime.py` |
| A transport failure is retried only when the recovery reasoning call selects a retry, and that call uses the same model session. When the provider is unavailable, the reasoning call cannot answer, and the step raises after one attempt. In the September 14 rerun a flash trial with a 150-call ceiling ended `PROVIDER_UNAVAILABLE` after two model calls this way. The run records the outage for a later resumption, but nothing inside the run waits for the provider to recover. | `core/adaptive_practitioner_records.py` (`_reasoned_recovery` and the transport loop in `_model_step`) |
| A model-authored method assessment that could not be admitted raised while the best-available resolution was built, so a run that had finished lost its whole outcome at the campaign trial boundary. The model-facing contract showed the list of method identifiers where one identifier belonged, and in the September 14 rerun on `793f27e` the first two trials ended this way after 60 model calls each. Later that day inadmissible assessments began falling back to dispositions derived from the preserved material, with the refusal recorded. | `code_nodes/solve_terminal.py` (`resolution_input_contract` and `_assess_resolution_methods`) at commit `793f27e` |
| A campaign cell that reached the provider wait ceiling or a route stop is scored failed on restart without running. | `devtools/embodiment_lab/task_database_campaign.py:530`, `:910-933` |
| In the September 14 rerun on `d3bda30`, two runs produced work that passed its own checks but was never accepted, because the independent verifier could not produce an admitted check program. In AE-001 the evaluator found every acceptance criterion met by the first attempt, and the verifier was unavailable three times: a planned file response gave only its content, and two oracle reviews read recomputed expected values as hardcoded observations. In DA-001 it was unavailable six times: four plans wrote `timeout_seconds` as text and were refused with a diagnostic that named no case or field, so each repair repeated the value, and two calls reached the 65536 token output limit. In FIN-001 five oracle reviews were refused, and every one returned only the example criterion reference that its contract showed, so no review could cover the task's several criteria. Later on September 14 a file response without a path began receiving its declared path, a refused case began naming the field to repair, the review contract began showing every registered criterion reference, and the review prompt began separating a recomputed expectation from a hardcoded observation. An unavailable verifier still yields the verdict `repair`, which led AE-001 to rewrite and break its passing work, and nothing retries a verifier call that reaches the output limit. | `core/independent_verification.py` (`_materialize_probe_files` and the review call in `_probe`), `core/independent_probe_planning.py`, and `core/adaptive_practitioner_verification.py` (the independent check handling) at commit `d3bda30` |
| The task database campaign sent a small text attachment only as prompt text when a cell used `bounded_inline` delivery, so no attachment file reached the run's folder, its project inputs, or the verifier's probe. Later on September 14 new configuration spaces began declaring `attachment_files` as `supplied`, which also gives every admitted attachment to the run as a source file. A saved configuration without the setting keeps its recorded `inline_only` behavior. | `devtools/embodiment_lab/task_database_campaign.py` (`task_intake`) at commit `d3bda30` |
| An unverified run presented its latest attempt as the best available result, even when that attempt failed its checks after an earlier attempt passed them. Later on September 14 an unverified run began presenting its latest execution whose checks passed. | `code_nodes/solve_runtime.py` (`_product_result`) at commit `d3bda30` |

## Planned tests

| Proposed invariant | Discriminating test |
|---|---|
| LE-SOLVE-001 | A fixture whose first format repairs fail but whose reframed request succeeds reaches the accepted result instead of ending with `ModelResponseRepairStalled`. A fixture with an exhausted declared call budget ends with `BUDGET_EXHAUSTED` and makes no extra model call. |
| LE-SOLVE-002 | The hardcoding delta gate finds no new task-specific literal, and the same solve path completes two unrelated task fixtures with no code change. |
| LE-SOLVE-003 | A tool that passes its builder's checks but fails held-out checks from another process is not reused. Removing the requirement lets the same tool through, which shows the check is what refuses it. |
| LE-CONTRACT-001 | Every registered contract check exposes a declared evaluation mode, and a check without one fails conformance. |
| LE-CONTRACT-002 | A probe with a wrong expected value against a correct subject is classified as a wrong expectation, confirmed, revised, and then passes, while the original failure stays in Run History. A correct probe against a wrong subject stays failed and routes to repair. |
| LE-CONTRACT-003 | A review proposing to relax a network or secret contract is refused. A revised check that accepts a known-wrong mutated subject is refused. |

## Consequences

- Runs may use more of their declared authority before ending, so reports
  must show the reason each run ended and the authority it consumed.
- Review steps add model calls, charged to the same accounting as other work.
- Check versions become part of the evidence, so an evaluation report must
  name the check version that accepted a result.
- Persistence can hide a broken mechanism behind retries. Reports keep the
  counts of repairs, reviews, and check revisions for each run so that this
  stays visible.

## Related records

- [Proposed invariants in the Constitution](CONSTITUTION.md#proposed-invariants-from-owner-direction)
- [Independent executable feedback for task repair](ADR-INDEPENDENT-TASK-FEEDBACK.md)
- [September 14 review](../verification/CLAUDE-OPUS-5-REVIEW-2026-09-14.md)
- [Self-resolving intake, sandboxes, and sharing research](../research/SELF-RESOLVING-INTAKE-SANDBOXES-AND-SHARING-2026-09-14.md)
- [Configuration dimensions for the discrete cognitive or act step Loop node](DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-DIMENSIONS.md)
