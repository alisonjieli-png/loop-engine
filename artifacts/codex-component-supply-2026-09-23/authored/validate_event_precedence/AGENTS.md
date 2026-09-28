# Validate declared event precedence

Candidate harness intelligence. Native loading and usefulness are not qualified.

## Task

Check strictly-before constraints against one supplied event-ID sequence, reporting missing IDs and order violations without inferring causality or using timestamps.

## First steps

1. Read `contracts/input.schema.json` and the semantic rules below.
2. Construct one bounded JSON request from supplied data.
3. With host permission to start the interpreter, run `python3 tools/validate_event_precedence.py` and supply the request on standard input.
4. Check the exit code and `contracts/output.schema.json`; compare the result with the task's acceptance conditions.

The command returns one JSON line: exit 0 for a result, exit 2 for a refusal.
The input is at most 65536 UTF-8 bytes and 16 container levels. JSON duplicate
keys, nonfinite numbers, invalid Unicode scalars and unknown fields refuse.
Numeric literals are at most 128 characters; integral forms such as 1.0 and
1e0 are accepted without binary-float rounding. Booleans are not integers.
The output limit is 131072 UTF-8 bytes including its trailing newline; an
oversized result returns `output_limit_exceeded`. Schemas describe shape and
field bounds; wire limits and cross-field conditions are additional rules.

## Method and limits

Event IDs are unique and exact; repeated IDs refuse rather than selecting an occurrence. Constraints are unique ordered pairs. At most 1024 events and 2048 constraints. Indices are zero-based. before_index must be strictly less than after_index; a self-constraint is unsatisfied. Missing endpoints produce missing_event with null indices. Violations retain input constraint order. Empty constraints are satisfied. This checks only declared sequence obligations, not actual event occurrence, time or causal order.

## Authority and dependencies

Python 3.10 or newer, standard library only. The method reads supplied standard
input and writes standard output. It performs no task-file access, network
request, subprocess launch, environment lookup or dynamic import. The host's
interpreter launch is a separate `spawns_process` effect. Paths and labels are
data; no result grants execution, installation, publication or access authority.
No current workspace, package catalogue or live filesystem state is inferred.

## Verification

Use the synthetic example and `verification/cases.json`. Structural success
is separate from semantic usefulness and independent review. This candidate
is original Codex/OpenAI-family material under the repository MIT notice;
no third-party content is claimed licensed by that notice.
