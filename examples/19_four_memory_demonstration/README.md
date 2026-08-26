# Four-memory demonstration

Two-run migration scenario exercising all four memory types through
the canonical Loop runtime.

Run:

```bash
python3 examples/19_four_memory_demonstration/run.py
```

First run: a Practitioner fails a migration, the failure is captured
as an episodic candidate, reviewed, and consolidated into a semantic
claim and a procedural candidate, both independently promoted.

Second run: a related task starts with empty working memory, recalls
the failure episode, the compatibility fact, and the verified
procedure, then succeeds.

No network, no external service, no model calls.
