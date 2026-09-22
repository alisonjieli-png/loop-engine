# Loop Engine writing context

Use this context when editing public Markdown with a prose-review or humanizer
skill. This file owns the voice, the punctuation and the reference style. It
does not own the vocabulary.

The vocabulary lives in [terminology.yaml](terminology.yaml), the single
structured source. Every term there states its kind, its definition, the
surfaces where it may appear, the surfaces that refuse it and its status.
[The developer language guide](docs/guides/developer-language.md) explains how
to read it. A term list repeated here would drift away from the file that the
conformance gate reads, so the sections below point at it.

## Reader

For Baltor's homepage and How it works, address a person who wants useful
results without learning the internal architecture. Use task, each step,
information, tools, models and checks. Omit Loop, Loop node and Loop Engine
from those pages and their shared footer. Preserve exact implementation names
and complete definitions in technical documentation and GitHub.

Write for a developer who is seeing Loop Engine for the first time. The reader
may use English as a second language. They should not need project history or
internal vocabulary to understand one page.

## Voice

- Use a neutral technical voice.
- Lead with the outcome, then explain the mechanism.
- Use one main point per sentence.
- Prefer short paragraphs and concrete examples.
- Repeat the exact technical term when variation would create ambiguity.
- Keep claims narrow and testable.
- State current behavior separately from planned behavior.

## Full terms without shorthand

Do not use shorthand or introduce abbreviated aliases in explanations,
documentation, prompts, or handoffs. Repeat the full descriptive term even
after defining it. Consistent repetition prevents meaning from drifting
between language-model sessions. Do not replace an established term with a
shorter synonym for style.

Preserve the full phrase "discrete cognitive or act step Loop node" and its
complete behavioral explanation. Do not shorten the phrase, remove "node,"
substitute an acronym, or retain only a label. Read
[the complete explanation and session handoff](docs/context/DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-HANDOFF-2026-09-12.md).
The explanation must retain the narrowly scoped assignment, selected context
and resources, separately initialized harnesses, permitted harness changes,
expectation checks, iteration until declared completion conditions, continued
production of alternative outputs, and protection against repeated external
effects. Publication of an output is separate from completion.

The descriptive phrase does not introduce a runtime class, role, or mode.
Preserve exact existing code identifiers, contract fields, product names, and
historical source quotations. The canonical runtime identifier remains `Loop`.

## Product names

- Product and repository: Loop Engine
- README title: Baltor
- Python distribution and command: `loop-engine`
- Python import: `loop_engine`

Do not construct a title by combining the import name, distribution name, or
runtime class name.

## Architecture terms and where each one may appear

Open [terminology.yaml](terminology.yaml) and read the entry for the term you
are about to write. It gives the kind, the definition, the surfaces that allow
the term, the surfaces that refuse it and the status. The homepage, the How it
works view and the shared footer refuse the exact runtime terms; technical
documentation, the Documentation view, GitHub and source code keep them.

[The developer language guide](docs/guides/developer-language.md) explains the
surfaces, the three settings a developer confuses on the first day, the two
views over the four intelligence layers and the retired words. Choose report,
event log, contract, evidence or run record according to the actual object.

## Punctuation and structure

- Do not use em dashes or en dashes.
- Use a period, comma, colon, or parentheses instead.
- Use sentence case for headings.
- Do not use decorative slogans, fake quotations, or three-part marketing
  claims.
- Do not use a list when two direct sentences are clearer.
- Keep code comments factual and short.

## Reference style

Good:

> Every executable graph vertex is a Loop. Each Loop has a role, run mode,
> typed ports, loop condition, exit condition, budget, and permissions.

Good:

> The Practitioner graph shows how the work was built. The Solution Canvas
> shows what runs for a new input.

Avoid language that sounds impressive but does not name a behavior, input,
output, limit, or current implementation state.

## Tree diagram style

Use a text tree or Mermaid tree when a page explains a hierarchy with three or
more branches. Start at the shared trunk and label each classification axis.
Do not place unrelated dimensions under one branch.

Good:

```text
Loop
├── Relationship: Starting, Spawned by, Queried by, Retrieved by, Connected from
├── Role: Practitioner, Intelligence, or Solution
├── Mode: deterministic, hybrid, or non-deterministic
└── Settings: contract, loop condition, exit condition, budget, and permissions
```

Avoid a diagram that treats every non-starting Loop as Spawned. Practitioner
subproblems may be Spawned. Intelligence Query Loops are Queried, selected
Intelligence Item Loops are Retrieved, and deterministic Solution pipeline
steps are Connected. Role profiles describe purpose. Modes describe execution.
Categories support organization and search. Settings constrain the run.

Passive records, services, ports, slots, and edges are not graph vertices.
Do not call them nodes. Use `Loop` for every executable graph vertex.
