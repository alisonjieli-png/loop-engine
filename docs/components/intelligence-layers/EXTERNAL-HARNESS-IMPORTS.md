# Import files and history from another harness

Many agent harnesses call a folder of Markdown files, skills, summaries, and
chat history "memory." That word describes where the harness looks. It does
not describe what the item means or whether Loop Engine should trust it.

Loop Engine classifies each imported item before it can enter the Intelligence
Library.

| Source item | Intelligence layer | Example |
|---|---|---|
| Markdown, skill, prompt, method, or rubric | Context Intelligence | A review checklist in `SKILL.md` |
| Tool, script, package, repository, or executable artifact | Code Intelligence | A pinned Python package |
| Run history, checkpoint, failure, measurement, or solution | Runtime History and Solution Intelligence | A saved agent run |
| Instruction, correction, approval, priority, or veto from a person | User Feedback Intelligence | "Do not write to production" |

The source format does not choose the layer. A Markdown file can describe a
tool, a past run, or a user instruction. The importer needs an explicit item
type and source reference so that it can make the correct classification.

## Import rules

An imported item starts as a candidate. Normal retrieval does not serve it as
active intelligence until a separate review accepts it.

The import record contains a bounded preview, a content digest, provenance,
tags, and a reference to the raw item. Large bodies stay outside the search
record. Executable files do not gain permission to run because they were
found or classified.

The import itself runs through a deterministic loop:

```text
external file or history item
  -> classification loop
  -> one intelligence layer
  -> candidate record
  -> independent review
  -> active intelligence or rejection
```

This keeps four decisions separate:

1. What is the item?
2. Where did it come from?
3. May search return it?
4. May a loop load or execute it?

A positive answer to one question does not answer the others.

## Python example

```python
from loop_engine.core.harness_intelligence_bridge import (
    HarnessMemoryItem,
    import_harness_memory_as_loop,
)

items = (
    HarnessMemoryItem(
        item_id="review-skill",
        kind="skill",
        title="Repository review procedure",
        source_harness="external_agent",
        raw_ref="repo:docs/review/SKILL.md",
    ),
    HarnessMemoryItem(
        item_id="prior-run",
        kind="run_trace",
        title="Saved repository review",
        source_harness="external_agent",
        raw_ref="run:2026-08-25/review-17",
    ),
)

result = import_harness_memory_as_loop(items)

for candidate in result.candidates:
    print(candidate.public_layer, candidate.lifecycle)
```

The result contains references and classification. It does not contain new
authority, an approval, or a claim that the source is correct.

Run the repository example for a classification of real Loop Engine files:

```bash
python examples/17_classify_harness_files/run.py
```
