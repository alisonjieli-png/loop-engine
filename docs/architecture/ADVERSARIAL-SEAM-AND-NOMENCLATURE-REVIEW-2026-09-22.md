# Adversarial review of nomenclature, seams, and the harness-first streamline

Kind: adversarial architecture review. Date: September 22, 2026. Read-only
evidence gathered after the harness-first commits (`6781c89`, `88714c2`,
`ea59df0`, the public-voice merge `ae7362f`, and the catalogue reclassify
`b4fc484`). Each finding names its current state, its intended future state
under owner direction, and the smallest honest change to get there (the
evolution vector). Nothing in this file is a pass claim; it is a map of what
is true, what is claimed, and where they differ.

## The one sentence that matters

The direction is sound and the seams are mostly real, but the streamline is
**suite retirement, not removal**: the in-process execution modules are parked
from the tests yet still importable and still reachable from the command line,
and the delegation seam the future depends on is a duck-typed protocol, not the
typed executor profile the decision record names.

## Current state, honestly separated

```text
Main line (ae7362f..b4fc484)
├── Live and wrapped (swap-safe via typed contracts)
│   ├── Serve surface: HTTP + protocol entrypoint, versioned host config
│   ├── Policies: licence (MIT default) and family (harness-only default),
│   │   both typed/versioned with named refusal checks
│   ├── Catalogue: staged candidate -> approved -> pinned digest; search
│   │   returns references, download re-checks and digest-matches
│   ├── Accounts, billing, protocol: behind adapters, versioned records
│   └── Harness recipes: 18 process styles + 4 SDK adapters, behind
│       HarnessProcessSpec / ExternalHarnessAdapter
├── Retired from tests but still present and reachable
│   ├── In-process solve engine, campaign runner, Kaggle executor
│   │   (277 suites moved to suite_collection_exceptions; still on disk,
│   │   still imported by live CLI paths)
│   └── The four persistent intelligence layers as served content
└── Frozen full-capability tree
    └── checkpoint/full-capability-2026-09-21 @ a3bd0f1 (6229 checks)
```

## Future state under the recorded direction

```text
├── Every executable step delegates to a harness or a future custom engine,
│   all behind one typed, versioned Executor Profile (phase 2)
├── The in-process execution modules are removed from main (phase 3), and
│   each parked folder carries its PARKED.md marker
├── Adding intelligence is a host configuration record, never a code change
├── Adding a harness or an engine is a declared tested profile, never an
│   import edit or a fork of the runtime
└── The edges between functional units are declared interaction records with
    typed request/result contracts, so a unit's engine changes without any
    neighbour noticing
```

## The adversarial findings, with evolution vectors

### Seam 1 — the executor interface is not yet the seam phase 2 needs

Current: `ExternalHarnessAdapter` (core/external_harness.py:530) is a
structural protocol; registration checks only that `info()` and `run()` exist.
A host does not choose an executor by declared profile; code constructs an
adapter object. The SDK adapters (pydantic-ai, deep-agents, openai-agents,
microsoft-agent-framework) report `isolation: none` and run **in this
process**, registered under the same surface as genuinely isolated process
harnesses, so the contract cannot distinguish delegation from in-process
execution. And `HarnessRunRequest` is shaped like one model call, not one step
of work.

Future: one typed seam that every executor (process harness, SDK harness,
future custom engine) implements, chosen by a declared profile record, with the
delegation guarantee explicit.

Evolution vector (smallest honest change, in `core/external_harness.py`, which is
already the rights-shaped home and not parked):

1. Add `executor_profile/v1`: identity, kind (harness process, harness kit,
   custom engine), declared isolation, capabilities, and a digest. A host
   profile record selects by this, not by constructing an adapter.
2. Move the `run_external_harness` pre-execution refusals into registration via
   an `adapter_contract_version` on the info record, so an incompatible version
   refuses at registration, never silently downgrades mid-run.
3. Version `HarnessRunRequest` to a step contract (or leave it and add
   `StepRunRequest`) so a step's typed input/output, authority and spawn rights
   travel with the work instead of being squeezed into a prompt envelope.

### Seam 2 — the harness style list is a closed triple copy

Current: `HarnessProcessSpec.style` is validated against an 18-name tuple
(harness_process.py), and the same names reappear in two if-chains: recipe
preparation (harness_process_relay.py) and output extraction (harness_process.py).
Adding a harness means editing three places. Claude Code is present only as an
instruction-file convention, not as a process harness, so the record phrase
"(OpenCode, Codex, Claude Code, and others)" overstates the executor set.

Future: adding a harness is adding one recipe record.

Evolution vector: a versioned `harness_recipe/v1` record (style, prepare
reference, extract reference, instruction-file profile, sandbox mounts) that
`HarnessProcessSpec` references by digest; the two if-chains read the registry.
Phase 2 for a custom engine then drops in behind the same executor profile.

### Seam 3 — "parked" is not "unreachable"

Current: the parked folders are suite-retired but still imported by live CLI
and core modules (cli_operations, main, run_history_cli still import
code_nodes.solve_runtime and friends; loop/recursive_loop.py still imports
parked loop/ modules). The serving HTTP surface does not reach them, so the
hosted service genuinely cannot execute — which is correct for the beta. But
the local command line still can, and the README/quickstart still describe the
in-process solve as the customer path.

Future: after phase 3, the modules are gone from main and only their markers
remain; until then, the docs must not present the in-process path as the live
one.

Evolution vector: docs-first now (a phase-state note in README and quickstart);
module deletion lands only in phase 3, after one real delegated step runs
end-to-end. Do not delete before the delegation exists — the seam must carry
the guarantee first.

### Seam 4 — the word "family" is overloaded, once dangerously

Current: the served intelligence family (loop_native / harness /
open_knowledge, the serving axis) and the candidate-specification "family"
(method / checklist / procedure, a catalogue category) are the *same word* in
two unrelated files, and the staging tool literally writes the category into a
field named `family`. An editor can pass the staging gate with `"family":
"procedure"` and then have the serving policy refuse the item with a message
that "names the family" — two different meanings, two same-worded errors.

Future: one meaning per word.

Evolution vector: rename the candidate-specification field to `category` end to
end (stage_intelligence_candidates.py, the specifications-*.json inputs, and
their tests). The specification record is versioned, so bump its version and
update callers together — the pre-launch policy permits exactly this.

## The ten same-word-two-meanings to retire (highest-risk for an editor)

1. `family`: serving axis vs catalogue category (Seam 4).
2. "Intelligence Library": the definition still says it is served by
   `query_intelligence`, which main does not serve; the served path is Harness
   Intelligence provisioning. Add the clause "on the full-capability tree; the
   main line serves the harness family".
3. "Harness Intelligence serves material from the four persistent layers": it
   does not; harness bodies live in `harness_local`. Fix the glossary row to
   say so.
4. "current" solve path in README/quickstart describes in-process solving; the
   in-process suites are retired on main. One banner resolves it.
5. `*Node` classes: the rule says none are permitted, yet two live
   (`NodeAssignment`, `NodeProvisioningError`) and three parked ones exist. The
   conformance gate misses the `NodeFoo` shape; tighten it and rename or
   grandfather the two.
6. `code_nodes` the package name vs the retired `CodeNode` class: same words
   different case; the package holds the live graph authority. Long-term rename
   is already flagged in the ratchet.
7. `checkpoint`: the hibernation Checkpoint record vs the frozen git branch;
   both read as the same word to an editor. Define the branch term once.
8. `PractitionerLoop`: the forbidden retired alias vs the document that quotes
   the owner doctrine with it. Keep the prohibition on the import, keep the
   quote only in parked doctrine.
9. Bare "Intelligence": deliberately not a reserved word, yet a role, a
   library, and three layer names. Context must carry the meaning; documentation
   must never use it bare where a name applies.
10. "parked": means "not tested, not the direction" (true) and is read as "not
    reachable" (false today). The phase-state note in docs makes the reachable
    truth explicit until phase 3.

## Evolution order (respects "never weaken a check")

1. Seam 4 (`family` to `category` rename) — removes the one dangerous
   overload; pure vocabulary, no behaviour change.
2. The two documentation clauses (Intelligence Library, harness-local sourcing)
   — closes the doc-vs-code gap without touching code.
3. Seam 1 (Executor Profile + registration-time refusal) — the phase-2 gate;
   makes delegation provable and the future engine a config choice.
4. Seam 2 (recipe registry) — makes adding a harness a data change.
5. Seam 3 (phase-3 removal) — last, only after Seam 1 proves one delegated step.
6. The Node-name tightening and the `code_nodes` package rename — hygiene,
   scheduled when the seams above are in.

Each step keeps the checkpoint branch frozen and the removed-guard controls
green, and each names its evolution vector so a later harness can pick it up
without re-deriving the reasoning.
