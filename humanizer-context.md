# Loop Engine writing context

Use this context when editing public Markdown with a prose-review or humanizer
skill.

## Reader

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

## Product names

- Product and repository: Loop Engine
- README title: Building with Loops
- Python distribution and command: `loop-engine`
- Python import: `loop_engine`

Do not construct a title by combining the import name, distribution name, or
runtime class name.

## Preferred architecture terms

- Loop object
- Loop Practitioner
- Practitioner Loop graph
- Solution Canvas
- Solution Loop
- self-improvement Practitioner task
- Core Architecture
- Intelligence Search and Retrieval
- Web Research
- Custom Plugins
- Retrieval Engine
- built-in adapter
- extension point
- potential external plugin
- Context Intelligence
- Code Intelligence
- Runtime History and Solution Intelligence
- User Feedback Intelligence
- Runtime Memory
- Run History
- report, event log, contract, evidence, or run record according to meaning

## Terms that need a qualifier

- Step profile means the number, order, and repetition of steps.
- Effort setting means bounded work limits.
- Operating settings mean permissions, access, and preferences.
- Candidate means under review and not available to run.
- Potential plugin means planned packaging around an existing extension point.

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
