# Documentation style

Write for a developer who is new to Loop Engine and may use English as a
second language.

## Order

1. State the useful outcome.
2. Show where the concept fits in the system.
3. Define the current behavior.
4. Give a realistic example.
5. State the main limit.
6. Link to deeper reference material.

The main README starts with the complete bird's-eye diagram. A component page
does not repeat that full map unless the relationship would otherwise be
unclear.

## Language

- Use one main point per sentence.
- Use active voice when the actor matters.
- Prefer builds, starts, uses, tests, runs, saves, and searches.
- Repeat the exact technical term when a synonym could change the meaning.
- Define a technical term before relying on it.
- Use sentence-case headings.
- Use a period, comma, colon, or parentheses instead of dash punctuation.
- Use report, log, contract, event history, or run record according to the
  actual object.

Do not use slogans, vague praise, or proof-sounding language. Name the input,
behavior, output, limit, or current implementation state instead.

## Product terms

Use the names in [Product nomenclature](reference/PRODUCT-NOMENCLATURE.md).
The short list is:

- Loop
- Loop Practitioner
- Practitioner Loop graph
- Solution Canvas
- Solution Loop
- self-improvement Practitioner task
- Core Architecture
- Retrieval Engine
- Context Intelligence
- Code Intelligence
- Runtime History and Solution Intelligence
- User Feedback Intelligence
- Runtime Memory
- Run History

Use step profile, effort setting, and operating settings as three separate
terms.

## Current and planned behavior

Use direct statements for current behavior. Use "potential" or "planned" for
work that is not implemented. Do not draw a potential external plugin as an
installed feature.

One successful run is one result. It is not a general success rate.

## Examples

Each new example follows the
[example README template](templates/example-readme.md). It must name its mode,
step profile, intelligence layers, model or network use, file writes, and
external effects. Add each safe offline example to CI.

## Checks

The documentation job uses external development tools. They are not Loop
Engine runtime dependencies.

1. [markdownlint-cli2](https://github.com/DavidAnson/markdownlint-cli2) checks
   Markdown structure.
2. [Vale](https://github.com/vale-cli/vale) checks the high-confidence wording
   rules in `.vale/styles/LoopEngine/`.
3. [Lychee](https://github.com/lycheeverse/lychee) checks local links and
   section anchors without using the network.
4. [Mermaid CLI](https://github.com/mermaid-js/mermaid-cli) renders the first
   README diagram.

The repository also contains [humanizer-context.md](../humanizer-context.md)
for a restrained technical editing pass. Treat humanizer scores as editorial
hints, not as proof of writing quality.
