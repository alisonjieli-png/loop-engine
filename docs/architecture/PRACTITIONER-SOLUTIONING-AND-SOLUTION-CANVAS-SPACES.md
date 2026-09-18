# The two spaces: the solutioning space and the solutions space

Status: recorded on September 16, 2026. This document makes the separation
between the reasoning that discovers a solution and the solution that gets
reused explicit, standardized, and easy to follow. It changes no runtime,
grants no authority, and adds no invariant. Where a rule here becomes
normative, it enters the Architecture Constitution with an enforcement test
first.

## The one-paragraph version

Loop Engine works in two spaces. The **solutioning space** is
where Loops reason, investigate, build, verify, and repair: the discovery
process that produces a solution. The **solutions space** is where a
finished, verified solution lives as a reusable artifact: a compiled
`LoopGraphDefinition` with its inputs, authority, and verification bound,
ready to run again for a new input without repeating the discovery. The
Practitioner graph records how the system arrived at a solution. The Canvas
records what must run next time. Reusing a Canvas must not repeat the
solutioning that produced it.

## Why the separation matters

Without it, three failure modes recur:

1. **Discovery cost is paid twice.** A consumer re-runs the whole
   investigation for each new input, because no durable artifact separates
   the discovered method from the reasoning that found it.
2. **The process is confused with the product.** A passing run's event
   history gets treated as if it were the executable solution, when it is
   evidence about how the solution was found.
3. **Verification drift.** The deliverable is re-derived, so the guarantee
   that was verified is not the artifact that is later executed.

## Standardized nomenclature

These are the terms, each with one meaning. Existing code identifiers are
unchanged; this standardizes the prose that explains them.

| Term | Meaning | Existing authority |
|---|---|---|
| solutioning space | Where classified Loops orient, investigate, build, verify, repair, and record the discovery process. The resident of this space is the running Loop and its Run History. | `practitioner` role profiles; Run History |
| Solutioning | The activity of the solutioning space: producing and verifying a candidate deliverable. Not a runtime, not a component. | Practitioner workflows |
| Solution Canvas | The candidate, comparison, and projection object that resolves to a `LoopGraphDefinition`. Passive, versioned, digest-bound. | `SolutionSpec` in `code_nodes/solution_canvas.py`; terminology `core.term.solution_canvas` |
| solutions space | The space where finished, verified solutions live as reusable artifacts, compiled and bound to their inputs, authority, and verification. | The Canvas and its compiled graph |
| Deliverable | The artifact the task asked for, produced inside the solutions space by executing the compiled graph under declared authority. | Product outcome records |
| Compiled solution | A `LoopGraphDefinition` with every vertex resolved to an exact Loop definition reference, ready to execute. | `LoopGraphDefinition` |
| Handoff | The moment solutioning produces a Canvas the independent verification accepts. The solutioning space's Run History records it; the Canvas carries the result forward. | Independent verification acceptance |
| Re-execution | Running a compiled solution for a new input under its declared authority, without solutioning. | `execute_development_plan`; solution executor |

The two spaces are not runtimes, roles, or modes. They are architectural
places with different residents, different lifetimes, and different
evidence:

```text
solutioning space                 solutions space
──────────────────────────────                 ─────────────────────
Residents: Loops in a solve run                Resident: the compiled LoopGraphDefinition
Evidence: Run History event chains             Evidence: definition digests, verification bindings
Lifetime: the solve, then archived             Lifetime: versioned, reused, superseded
Question answered: how was this solved?         Question answered: what runs next time?
Model spend: authorized per step               Model spend: declared in Loop definitions only
Changes: recovery, repair, re-orientation       Changes: new version, requalification
```

## The handoff contract

The bridge between the spaces is the point where the architecture already
concentrates its guarantees, stated here as one place:

```text
Solutioning (Practitioner Loops, any modes)
    │
    │  produces a candidate Canvas with complete Loop definitions
    ▼
Independent verification (verifier Loop, own contract)
    │
    │  accepts the exact artifact against the registered criteria
    ▼
Handoff: the Canvas enters the solutions space
    │
    │  compiled to LoopGraphDefinition, digest-bound, inputs and
    │  authority declared
    ▼
Re-execution for new inputs (no solutioning repeated)
```

What the handoff does and does not carry:

- It carries the method, not the process. The Canvas contains the compiled
  graph and its contracts. The Run History of the solutioning run remains
  in the solutioning space as evidence.
- It carries verification of the exact artifact. A later edit to any
  definition changes the digest and therefore requires requalification.
- It never carries authority. Executing a compiled solution for a new
  input still requires that run's own typed permissions and budget. A
  Canvas is permission-shaped, never permission-granting.
- It may carry model-led Loops where the contract requires semantic work.
  Reusable does not mean zero model calls; a deterministic realization
  becomes possible when a verified implementation satisfies the contract
  in a defined input region.

## What exists and what is missing

Verified in source today: the Canvas and its compiler
(`SolutionSpec` projects selected candidates into one authoritative
`LoopGraphDefinition`); independent verification with frozen subjects;
the development plan compiler and wave executor that already run compiled
graphs; Run History that preserves the solutioning evidence; the reusable
capability flywheel that admits qualified implementations for reuse; and
the embodiment catalogs that compare realization alternatives.

The genuine gaps, each mapped to its owning boundary:

1. **No explicit handoff record.** Acceptance today updates the solve
   outcome; nothing names "this Canvas is now the deliverable for this
   task family" as a first-class record. Smallest extension: a typed
   handoff record in the product outcome store binding the accepted Canvas
   digest, the verification record, and the input region. Test: a handoff
   record whose Canvas digest no longer matches its compiled graph is
   refused.

2. **No re-execution path from an accepted Canvas.** The wave executor
   exists and is tested, but no solve path says "an accepted Canvas for
   this task family exists; execute it instead of solutioning." This is
   the fast-path allowance's natural extension: from resolvers to compiled
   Canvases. Smallest extension: the fast-path lookup consults accepted
   Canvas handoff records before starting solutioning. Test: a task with
   an accepted Canvas executes with zero solutioning model calls.

3. **Canvas-to-intelligence promotion is designed but not wired.** Runtime
   History and Solution Intelligence is the recorded home for accepted
   solutions; the handoff record feeds it. Smallest extension: the handoff
   record is indexed as Runtime History and Solution Intelligence with its
   applicability region, so future solutioning retrieves it as a
   candidate.

4. **The deliverable-space lane for incomplete sources exists; the
   Canvas-space equivalent for unverifiable deliverables does not.** A
   best-available resolution stays in the solutioning space with its
   findings. Smallest extension: none needed; a Canvas without accepted
   verification never crosses the handoff. This is correct behavior,
   recorded so it is not mistaken for a gap.

## Documentation rule

Prose in this repository uses the standardized terms: the solutioning
space reasons and builds; the solutions space holds compiled, verified,
reusable solutions; the handoff records acceptance; re-execution runs the
compiled solution for new inputs. Avoid the adjectives "agent space" and
"tool space" for these concepts; both are misleading because the resident
of each space is a Loop, not an agent or a tool. The session-era terms
"practitioner space" and "solutions space" from the stub experiment
readmes are synonyms for the solutioning space and the solutions space
respectively and are updated where they appear in new documents.

## Current implementation, September 18

Both spaces are now registered terms. `SolutioningSpace` binds to
`run_adaptive_practitioner`, the operation that realizes it. `SolutionsSpace`
binds to `SolutionsSpaceRecord` in
[`code_nodes/solutions_space.py`](../../src/loop_engine/code_nodes/solutions_space.py).

```text
Solutions space for one task
├── task_digest
└── members, one per published Solution Canvas
    ├── candidate_id and graph_digest (the member identity)
    ├── status: candidate, verified, superseded, or retired
    ├── verification_report_digest (required for a verified member)
    ├── applicability, cost, and evidence_refs
    └── superseded_by (required for a superseded member)
```

What the record enforces: adding a member never removes another; a member
with the same graph digest is the same member; a verified member cites the
passed independent report; supersession names a successor inside the same
space. `solutions_space_from_adaptive` projects a finished run's candidate
canvases into a space and verifies only the accepted canvas when the run is
solved and holds a passed independent report.

What is missing: the run does not write the space yet, there is no store
that keeps a task's space across runs, and selection among members by
applicability and cost is not implemented. Those are the next steps, and
none of them changes the rule that the solutions space stays plural.
