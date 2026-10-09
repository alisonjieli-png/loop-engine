# Provenance-aware evidence counting

Counts the independent observations behind a claim instead of the messages or reports that mention it. A claim relayed from agent A to B to C and back to A is still one observation, and a report that merges two relays of the same observation adds nothing.

## When to use it

- Several agents or tools pass findings to each other, and one of them is about to treat repetition as corroboration.
- You aggregate reports from sources that quote each other.
- You want to find circular reporting: claims whose citations never reach an actual observation.

## Formula

`count_independent_evidence`: each report is a root observation (`observed: true`, no sources) or rests on earlier reports (`sources`). For a claim,

    independent_observations = | union over the claim's reports of roots(report) |
    roots(report) = the root observations reachable from the report through sources

Reports with an empty root set are listed in `unsupported_reports`.

`relay_non_backtracking`: in each round every agent sends each observation id it learned in the previous round to its out-neighbours, except the agents it learned it from. A receiver keeps an id once. The `naive` column counts every received message instead, which is what double counting does.

## Assumptions and what it does not establish

- Provenance links are complete and honest. A report that hides its sources looks like a new observation.
- Root observations are treated as independent. A shared hidden cause (two agents reading the same flawed page) is not detected.
- Non-backtracking removes direct echoes but not all redundant messages: in a triangle an agent can still receive an id twice. The provenance set keeps the count right either way.

## Parameters

| Name | Meaning |
|---|---|
| `reports` | `[{id, agent, claim, observed, sources}]`; ids unique; sources cite reports of the same claim |
| `edges` | directed `[sender, receiver]` pairs between different agents |
| `origins` | `{agent: [observation ids]}` held at the start |
| `rounds` | 1 to 10000; the simulation stops early when nothing new is learned |

## Example

```python
from provenance_evidence_counting import relay_non_backtracking

result = relay_non_backtracking([["a", "b"], ["b", "c"], ["c", "a"]], {"a": ["o1"]}, rounds=3)
result["independent"]["a"], result["naive"]["a"]     # 1, 2: the returning message is not new evidence
```

Command line:

```bash
echo '{"call": "count_independent_evidence", "arguments": {"reports": [{"id": "r1", "agent": "a", "claim": "x", "observed": true}, {"id": "r2", "agent": "b", "claim": "x", "sources": ["r1"]}]}}' | python3 provenance_evidence_counting.py
```

## Limits

- Synchronous rounds without message loss or delay.
- Graphs of thousands of edges are fine. Very large graphs are slow in pure Python.

## Files

- `provenance_evidence_counting.py`: the functions and the JSON command line.
- `numerics.py`, `atom_cli.py`, `schema_lite.py`: shared helpers.
- `test_provenance_evidence_counting.py`, `test_package.py`: run with `python3 -m unittest`.
