# Resolve an exact selected dependency closure

Candidate harness intelligence. Native loading and usefulness are not qualified.

## Task

Find the transitive closure of selected exact package IDs and report cycles; refuse a missing reachable dependency without choosing versions or downloading material.

## First steps

1. Read `contracts/input.schema.json` and the semantic rules below.
2. Construct one bounded JSON request from supplied data.
3. With host permission to start the interpreter, run `python3 tools/resolve_selected_dependency_closure.py` and supply the request on standard input.
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

Package IDs are unique, exact case-sensitive Unicode strings. Roots and each requires list contain no duplicate ID. At most 256 packages, 256 roots and 16 direct requirements per package. Only the selected closure must resolve: an unselected package may refer to an absent ID. A missing root or reached dependency returns missing_dependency. The selected list is sorted; cyclic_components are strongly connected groups of size greater than one or self-loop singletons, each sorted and then lexicographically ordered. This is a selection report, not a topological install order, semantic-version solver, provider selector or compiler.

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
