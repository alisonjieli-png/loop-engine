# Reports

A live run emits an event log. A saved Chronicle adds an immutable hash chain.
Reports turn either form into something a person can act on.

## From the command line

```bash
RUNS_DIR="$HOME/.loop-engine/runs"
loop-engine --runs --runs-dir "$RUNS_DIR"
loop-engine --report --runs-dir "$RUNS_DIR"
loop-engine --report <run_id> --runs-dir "$RUNS_DIR"
loop-engine --report <run_id> --format html --out report.html \
  --runs-dir "$RUNS_DIR"
```

For interactive playback:

```bash
loop-engine --studio --runs-dir "$RUNS_DIR" --port 8765
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

```text
LOOP REPORT: quarterly-plan
  5 loops, 34 events, max depth 2
  0 model calls, 0 tokens
  chain verified: yes

loop1: prepare a quarterly plan
    loop2: gather last quarter's numbers
        [deterministic] 0.4s, 6 events, 0 model calls
        steps: act
    loop3: review the draft
        loop4: check one assumption
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
| `html` | sending to someone: self-contained, no assets, no network, dark-mode aware |
| `json` | a dashboard or a downstream check |

All four project the **same** underlying report, so they cannot disagree.

## What makes a report trustworthy

**It projects; it never re-derives.** Every figure comes from the ledger the
run emitted. Nothing is recomputed from another source: a report that quietly
recalculates becomes a second source of truth, and the two drift.

**Unknown is not zero.** A ledger with no timestamps yields `seconds = None`,
not `0.0`. Reporting zero would claim an instantaneous loop, which is a
different statement from "this run did not record time".

**An empty run reports an empty run**: no invented structure to make the
output look populated.

**When a provider returns token counts, the report preserves them.** Missing
provider identity remains unknown.

**The chain is verified.** `chain_intact` reports whether every event digest
still matches, so tampering or corruption shows up rather than passing quietly.

Runnable walkthrough: [play back a saved run](../../examples/08_play_back_a_saved_run/).
