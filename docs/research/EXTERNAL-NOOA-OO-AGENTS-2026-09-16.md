# External research note: NVIDIA-labs Object Oriented Agents (NOOA)

Reviewed on September 16, 2026, from the public repository
(<https://github.com/NVIDIA-NeMo/labs-OO-Agents>, Apache 2.0, about 2.1k
stars, 559 commits at review time). This is an external evidence note under
the reference-sources rule: ideas are recorded with their source, mapped
against existing Loop Engine boundaries, and nothing is adopted without a
verified gap and the smallest typed extension. NOOA is external research
software; nothing here endorses its safety claims, and its own README
states its in-process validators are defense in depth, not a containment
boundary.

## What NOOA is

A model-agnostic Python framework where an agent is one Python class:
fields are typed state, ordinary methods are deterministic capabilities,
docstrings are prompts, and type annotations are contracts. A method whose
body is `...` becomes an language model-driven generation method; a real body stays
deterministic Python. The model acts by writing Python in a Jupyter-style
REPL with access to `self`. Every language model call, code execution, and method
invocation is traced with parent and descendant spans. Sub-packages add a CLI with
a trace viewer, an ACP coding-agent host, a long-term `MemoryManager`, and
a Harbor-based benchmark runner.

## The honest mapping to Loop Engine boundaries

| NOOA concept | Loop Engine equivalent today | Assessment |
|---|---|---|
| Agent as one Python class | `Loop` with `LoopDefinition` + role profile | Different packaging of the same idea: NOOA binds behavior by class shape; Loop Engine binds by versioned definition with digest. Loop Engine's record survives across processes; NOOA's class is the process. |
| `...` body = language model-driven method | Semantic Loop contract with a model-led realization | Loop Engine already separates the implementation-independent specification from realizations; NOOA's `...` is a concise authoring syntax for the same split. |
| Real method body = deterministic | `deterministic` run mode | Equivalent; both keep deterministic work out of model spend. |
| Docstrings as prompts | Prompt resource bundle with typed slots | Loop Engine's slots add trust classes, provenance, size policy, and render digests; a docstring carries none of those. |
| Type annotations as contracts | `LoopContract` typed input/output roles | NOOA checks signatures at the Python boundary; Loop Engine's contract is versioned and digest-bound. The contracts index already records full value schemas at every edge as a known limit, which NOOA inherits from Python typing too. |
| Code-as-action REPL with `self` | Generated-project execution in a confined Docker workspace | Loop Engine's is stronger: network-disabled, non-root, read-only, pinned image. NOOA's README itself concedes in-process validation is not containment. |
| Parent and descendant trace spans | Run History with hash-chained events | Equivalent intent; Loop Engine's chain is tamper-evident and survives the process. |
| `MemoryManager` sub-package | Four intelligence layers + lifecycle governance | Loop Engine's admission and promotion rules are stricter; NOOA's memory is a store without an independent-qualification gate. |
| ACP host package | Harness adapters and ACP boundary already documented | Converging industry direction, already recorded in the layered-harness design. |
| Harbor benchmark runner | Benchmark evidence rules | Loop Engine requires frozen populations and exact denominators; adopting NOOA's runner would add none of those. |

## Ideas worth recording, none adopted yet

1. **The `...`-body syntax is the cheapest useful idea.** A one-token
   marker that says "this exact contract is model-led, everything else on
   this object is deterministic" is a good authoring surface for the
   semantic runtime. Existing boundary: `SemanticLoopContract` and
   `select_semantic_realization`. A port would be a compact authoring
   wrapper over the existing bind call, not a runtime change.

2. **Their safety framing corroborates ours.** NOOA's README states a
   static checker over Python cannot be a containment boundary and names
   OS-level isolation as the real boundary. This is independent external
   evidence for Loop Engine's existing rule that generated code runs in a
   declared sandbox and that in-process validation is admission control,
   not containment.

3. **Trace-viewer ergonomics.** NOOA traces every span by default with a
   browser viewer. Loop Engine's Studio and reports exist; the delta is
   default-on tracing with parent and descendant span export, which OpenTelemetry
   export already supports. A gap in convenience, not authority.

4. **Benchmark runner reuse is not justified.** Their Harbor runner lacks
   the frozen-population, exact-denominator, and independent-review rules
   the constitution requires. Published results from it are external
   evidence only, citable with exact population, model, harness version,
   evaluator, source, and limitations.

## What we explicitly do not adopt

NOOA's central inversion, binding the agent's identity to a live Python
class instance, conflicts with three Loop Engine invariants: immutable
digest-bound definitions (LE-VERSION-001), the one-runtime rule
(LE-NODE-001) with roles as fields, and Run History surviving the process.
An object graph is not a runtime; NOOA itself is a harness-shaped substrate
that a Loop could bind for bounded work, exactly like OpenCode or Pi, if it
were ever installed for comparison. Nothing is installed.

## Verdict

NOOA is an object-oriented harness with an honest safety note. Its useful
contribution to this repository is confirmation, not novelty: the
specification-versus-realization split, typed contracts, deterministic
versus model-led separation, OS-level containment, and default tracing all
exist here as governed boundaries. The single candidate port is the
`...`-body authoring syntax, which fills no functional gap but could
reduce authoring friction for semantic Loop contracts. Recorded for
review, not scheduled.
