# Independent review of twelve mixed native methods

Reviewed population: the factory's frozen `prepared-final` cohort, twelve
logical candidates with 96 delivered payload paths. This review did not edit
those files or approve a package. The reviewing process and the producer both
belong to the OpenAI family, so this is **not** one of three independent model
families for admission.

## Results

[302 sandbox executions](independent-behavior-report.json), representing 301
distinct script/input pairs, passed their independent expected behavior checks:
197 expected successes and 105 expected refusals. Every successful output
matched its output schema. No run timed out or exceeded the output collector's
limit. All source hashes were unchanged. The [summary](summary.json) records
the exact denominator and measured durations.

The independent checks use a fixed seed, `20260923`, and cover every method:

| Method | Independent comparison |
| --- | --- |
| Earliest graph times | Repeated readiness/longest-path relaxation, plus a 60-task maximum-duration chain |
| Strong components | Transitive-closure matrix, plus a 60-vertex cycle |
| Pairwise configurations | Membership and complete pair-coverage properties, including the full six-factor/three-value domain |
| Primitive contract compatibility | Exhaustive representative-value set inclusion on small contracts |
| First fit decreasing | Capacity, exactly-once membership and reconstructed first-fit obligations |
| Functional dependencies | Pairwise typed-tuple comparison, including Boolean/integer separation |
| Token bucket | Integer thousandths of tokens, independent of the delivered Fraction implementation |
| Boolean rules | Bitmask truth-table enumeration |
| Length-prefixed frames | Independently constructed byte frames and malformed/truncated/excessive streams |
| Rational expressions | Generated operator trees with separately computed exact Fraction results; calls, attributes, powers and other unsupported syntax |
| Literal template | Literal one-pass substitution, unexpanded replacement syntax and bounded output expansion |
| JSON Pointer | Escaped member names, distinct Unicode spellings, exact array indexes and invalid paths |

Every method also received duplicate-key JSON, NaN, overflowing numeric JSON,
invalid UTF-8, oversized input, excessive nesting and truncated JSON. Candidate
code ran only through the existing Bubblewrap runner with no network, no
mounted host home and a cleared environment. The resource runner applied
two CPU seconds, 256 MiB address space and a four-second wall timeout. The
largest observed run was about 49 milliseconds, including sandbox launch;
this is a local component measurement, not a full-system or customer latency
claim. Peak resident memory was not measured.

[Additional boundary probes](resource-boundary-probes.json) accepted exactly
256 empty frames and refused an oversized repeated JSON projection. The first
Unicode template probe exceeded the input ceiling, so it did not establish
the output check. A [corrected Unicode probe](unicode-output-boundary-confirmed.json)
used 20,520 input bytes within the schema and field limits and still returned
the documented refusal for the expanded output. Those probes are separate
from the 302-case denominator above.

## Contract findings requiring resolution

### Integral JSON numbers

[Separate interface probes](integral-number-interface-probes.json) changed
integer-valued example inputs to equivalent integral floating representations.
The shipped JSON Schemas accept them, while four runtimes refuse them:

- `schedule_dag_earliest_times`
- `pack_first_fit_decreasing_batches`
- `audit_functional_dependency_rows`
- `simulate_exact_token_bucket`

For example, `{"tasks":[{"id":"a","duration":1.0,"depends_on":[]}]}`
passes the scheduling input schema but exits 2. The shared helper requires
Python's exact integer type. JSON Pointer accepted the corresponding number
representation change as a positive control. Resolve this by aligning parsing
with the intended JSON number domain or explicitly documenting and validating
the narrower lexical input contract. Do not imply schema validity guarantees
successful processing. Graph cycles and other documented semantic refusals
are separate from this representation issue.

### Unselected row values

The functional-dependency schema restricts every row property to a short
scalar. The runtime validates selected columns only. This input is rejected
by the shipped schema but accepted by the runtime with no violations:

```json
{"determinants":["a"],"dependents":["b"],"rows":[{"a":"x","b":1,"unused":{"nested":true}}]}
```

Decide whether unselected columns may hold arbitrary bounded JSON. Then make
the schema and runtime describe the same input domain. The selected-column
calculation itself was correct in this probe.

Both findings were sent to the producer and integrating session before any
repair. [The confirmed counterexample record](confirmed-counterexamples.json)
binds their script hashes. The initial exploratory record is retained; it
used a placeholder expected output and its `passed` field is not acceptance
evidence. The confirmed record supplies meaningful expected outputs.

## Comparison with the prior 89 candidates

The [prior material inventory](prior-material-inspection.json) reads the
manifests and actual material of all 89 prior logical candidates: 119 source
or delivery paths and 102 distinct payload byte digests. Source/delivery
copies do not increase the package count. No new payload matched those 102
digests exactly. Nearest procedural and executable comparators were then
inspected for their actual input, transformation and result:

| New method | Nearest older material | Scope distinction |
| --- | --- | --- |
| Earliest graph times | Prerequisite-order guide; capacity-by-interval guide | Computes duration-constrained earliest times under unlimited resources; does not interpret prose or prove staffing feasibility |
| Pairwise configurations | Model/context frozen-case comparison | Constructs covering rows for factor-value pairs; does not design or run a paired model experiment |
| Primitive contracts | Source-to-target mapping; JSON shape server | Decides accepted-value containment for a closed primitive contract language; the old server only describes top-level shape |
| First fit decreasing | Capacity-by-interval and stock allocation guides | Packs scalar sizes into bins without calendars, priority policies or stock ledgers |
| Functional dependencies | JSON Lines identity audit; join-cardinality audit | Groups selected typed column tuples and reports dependent-value variants; old tools compare whole events or two-table key multiplicity |
| Strong components | Prerequisite-order and plan-change propagation guides | Computes mutual reachability in an explicit graph; does not infer dependency meaning or proposed commitment changes |
| Token bucket | Resource-capacity guide; output-allocation fallback guide | Simulates fractional replenishment over time; does not grant model budget, permissions or real quota |
| Boolean coverage | State-transition test derivation; protocol-effect adjudication | Exhaustively evaluates a bounded Boolean condition table, without lifecycle or authority semantics |
| Length-prefixed frames | Text-encoding and ZIP-package audits | Decodes a specific binary framing format; does not inspect UTF-8 or archive structure |
| Rational expression | Numeric-rounding guide | Parses a small exact arithmetic grammar; does not select a rounding stage or reconcile financial meaning |
| Literal template | Native material placement and task-brief templates | Performs strict one-pass text substitution; does not choose files, resolve harness settings or escape target-language code |
| JSON Pointer | JSON shape server | Retrieves requested values with standard string-form token rules; the older server deliberately does not return values |

These are twelve scope-distinct methods relative to the inspected prior
collection. They share common algorithm families and validation boilerplate.
This is not a claim of novel algorithms or a formal semantic duplicate proof
against every public repository. Independent admission can still judge a
method too narrow, insufficiently useful or improperly framed.

## Reproduce and limits

Run `independent_review.py --report /a/new/report.json` in the existing
repository Python environment. The runner refuses an existing report path and
uses the inspected factory sandbox command. It executes no candidate source
directly on the host. Its fixed factory path identifies this frozen review
population; it is an evidence runner, not a general admission command.

No native Codex, OpenCode or Pi session was launched. No customer outcome,
provider behavior, token saving or three-family approval was measured.
Python 3.14.4 supplied the sandbox interpreter; the candidate declaration of
Python 3.10 or later remains wider than this execution evidence. The seeded
cases and explicit boundaries do not establish correctness for every valid
input. The four affected packages need a contract disposition before admission;
the remaining packages still require the normal independent review process.

## Contract successor replay

The original population and all its failed evidence remain unchanged. The author
prepared a separate `mixed-native-originals-contract-v2-2026-09-23/prepared`
cohort. `independent_review_frozen_v1.py` preserves the exact prior runner;
`independent_review.py` adds an explicit `--packages` location without changing
its behavioral oracles. On the repaired cohort, all **302 sandboxed executions**
pass and all **six explicit contract counterexamples/control cases** are accepted
by both input schema and runtime. The replay records bind the successor package
inventory and script digests. No model call or independent-family approval occurred.

- `independent-behavior-contract-v2.json`: full frozen behavior corpus replay.
- `contract-v2-counterexample-replay.json`: the four integral-number methods,
  rational arithmetic control, and unrelated-column functional dependency case.
