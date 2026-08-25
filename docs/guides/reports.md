# Reports

A run emits a hash-chained ledger. Complete and checkable — and unreadable as
raw JSON. Reports turn it into something a person can act on.

## From the command line

```bash
loop-engine --runs                                    # what is available
loop-engine --report                                  # most recent, as text
loop-engine --report <run_id>                         # a specific run
loop-engine --report --format markdown                # for an issue or PR
loop-engine --report --format html --out report.html  # self-contained page
loop-engine --report --format json                    # for a dashboard
```

## In code

```python
from loop_engine.code_nodes.loop_report import (
    report_from_ledger, report_from_run, render_text, render_markdown,
    render_html, write_report)

report = report_from_ledger(ledger.events, run_id="my-run")   # a live run
report = report_from_run("path/to/runs", "my-run")            # a saved one

print(render_text(report))
write_report(report, "report.html")        # format chosen by extension
```

## What a report shows

```
LOOP REPORT — quarterly-plan
  5 loops, 34 events, max depth 2
  0 model calls, 0 tokens
  chain verified: yes

loop1 — prepare a quarterly plan
    loop2 — gather last quarter's numbers
        [deterministic] 0.4s, 6 events, 0 model calls
        steps: act
    loop3 — review the draft
        loop4 — check one assumption
            [hybrid] 1.2s, 9 events, 1 model call, 294 tokens (mistral)
```

The nesting is the point. A loop of loops rendered as a flat list hides the one
structure worth seeing, so the tree is built from the parentage the runtime
actually recorded.

```python
report.loops                  # how many
report.deepest()              # nesting depth
report.model_calls
report.total_tokens
report.cost_by_provider()     # {'mistral': 294}
report.summary()              # the structured form
```

## Four renderings, one projection

| Format | For |
|---|---|
| `text` | a terminal |
| `markdown` | an issue, a pull request, a status update |
| `html` | sending to someone — self-contained, no assets, no network, dark-mode aware |
| `json` | a dashboard or a downstream check |

All four project the **same** underlying report, so they cannot disagree.

## What makes a report trustworthy

**It projects; it never re-derives.** Every figure comes from the ledger the
run emitted. Nothing is recomputed from another source — a report that quietly
recalculates becomes a second source of truth, and the two drift.

**Unknown is not zero.** A ledger with no timestamps yields `seconds = None`,
not `0.0`. Reporting zero would claim an instantaneous loop, which is a
different statement from "this run did not record time".

**An empty run reports an empty run** — no invented structure to make the
output look populated.

**Token counts are provider-reported** and carry the provider that produced
them.

**The chain is verified.** `chain_intact` reports whether every event digest
still matches, so tampering or corruption shows up rather than passing quietly.
