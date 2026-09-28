# Three original offline method contracts

These candidates use Python standard-library helpers and the existing strict
JSON framing. They introduce no runtime/store/authority component. The existing
CataloguePackage factory retains preparation and admission ownership. Producers
are Codex/OpenAI, method `codex_original_competition_components/v1`.

The current seventeen original components and earlier skill/native populations
were inspected by identity and focused text search. The closest prior methods
are selected dependency closure, context-block selection, SCC analysis and DAG
scheduling. None supplies Python AST candidate facts, a direction/type/hop/budget
graph neighborhood, or explicit test-mapping coverage prioritization. Reuse the
first-party bounded exact-integer JSON parser and sandbox verifier; do not copy
an external implementation or install a graph/parser/server dependency.

Primary references: [Python 3.10 AST](https://docs.python.org/3.10/library/ast.html),
[NetworkX BFS layers](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.traversal.breadth_first_search.bfs_layers.html),
[Agent Skills format](https://agentskills.io/specification). The BFS interface
informed layering; the implementation is original and uses no NetworkX runtime.
Python's AST reports one-based lines and zero-based UTF-8 byte columns. Parsing
does not execute source and does not perform every compilation/scope check.

All requests use closed JSON records, valid Unicode, duplicate-key/nonfinite
refusal, 64 KiB input and 128 KiB output including LF. Numerical fields accept
mathematically integral JSON spellings exactly, exclude booleans, and have stated
bounds. Invalid wire/shape errors return `{ "error": "invalid_input" }`, exit 2.
Successful reports exit 0. The scripts never read task files, import supplied
modules, run tests, spawn commands or use network/credentials. The harness needs
permission to launch Python and read the packaged script; metadata declares
`spawns_process` and `reads_fs` for that host-side launch.

## inspect_python_symbol_dependencies

Input: `files[{path,module,source}]`, one to sixteen unique relative `.py` paths
and unique explicitly supplied ASCII dotted module names. Each source is at
most 16,384 codepoints. Syntax profile is `python_ast_feature_3_10/v1`, requesting
the host parser's best-effort Python 3.10 grammar. Runtime/parser equivalence is
not claimed. The caller supplies bytes; the method does not walk a repository.

Output: file source digests and parsed/syntax-error/analysis-limit statuses;
module, function, async-function and class symbols; import facts; and call-site
candidates. Module IDs hash the exact supplied module name. Definition IDs hash
module, lexical name, kind and source start position; file digests remain the
revision binding. Locations are explicit AST UTF-8 byte columns, never Unicode
character indexes. Limit each tree to 4,096 AST objects, depth 128, and all output
fact arrays to 2,048 combined entries; excess analysis returns a typed refusal
or per-file analysis-limit result, never silently truncated facts.

Decorator, default-argument, base and annotation expressions are visited with
the enclosing owner and `definition_time` context. Function bodies get their
definition owner and `function_body`; class bodies get `class_body`. Anonymous
lambda/comprehension scopes are not fully resolved. Source names/positions do
not establish that a module imports or executes successfully.

Bare-name calls can name same-module top-level definition candidates. They are
never certain dispatch. Function parameter/local-binding shadowing, duplicate
top-level definitions and explicit module rebinding stay unresolved. Attribute
calls stay unresolved; computed callees are dynamic. Imports can identify an
exact supplied absolute module candidate; relative/external imports remain
unresolved and imported attributes are not proven present. Every call has
`certain: false`; `complete_runtime_dependency_graph` is always false.

Decisive controls: source containing `os.system` is parsed as inert text;
defaults/decorators belong to the enclosing definition-time context; a shadowing
parameter does not become a certain callee; repeated definitions do not collapse;
Unicode columns use bytes; one syntax error does not discard another valid file;
unknown relative imports remain unresolved.

## select_graph_context_neighborhood

Input: explicit unique node IDs (at most 512), unique directed edge triples
`{source,target,kind}` (at most 2,048), unique nonempty seeds (at most 32),
direction `outgoing|incoming|both`, allowed edge types (at most 32), node budget
1–256 and hop limit 0–32. All edge endpoints and seeds must exist. A budget
smaller than the seed count refuses with `seed_budget_exceeded`.

Select all seeds in lexical order at distance zero, then complete BFS layers in
lexical order until hop or node budget is reached. At a partially fitting layer,
keep the lexical prefix and stop. Return selected IDs/distances and original
allowed edge triples whose endpoints are both selected. Report every unselected
eligible immediate neighbor of a selected node, using its minimum such distance,
as omitted for node budget or hop limit. Other unselected nodes are not claimed
unreachable. Directions affect traversal, not the orientation of returned edges.

Decisive controls: incoming/outgoing differ, seeds survive ties, hop zero returns
only seeds, unknown endpoints refuse even if unreachable, edge-type filtering
applies to traversal and returned edges, ordering does not depend on input order,
and budget/hop omissions remain distinct from a complete closure claim.

## plan_targeted_test_selection

Input: unique changed symbol IDs (at most 128), unique test records (at most 256)
with ID, distinct explicit dependency IDs (at most 256), integer priority 0–100
and integer estimated milliseconds 0–3,600,000. Selection limits are max_tests
0–128 and max_estimated_ms 0–1,000,000,000. No test code is accepted or run.

An impacted test intersects the changed symbols. Repeatedly choose a remaining
test fitting the residual estimated-time budget by descending newly covered
symbol count, descending total matched count, descending priority, ascending
estimated time, then lexical ID. Stop at max_tests or when no test fits. This
is an explicit greedy rule, not an optimal/minimum suite guarantee.

Return selected tests with matched/newly-covered symbols; omitted impacted tests
with count-budget or time-budget reasons; changed symbols absent from every
mapping; mapped-but-uncovered changed symbols; and total estimated milliseconds.
When both limits prevent another test, count budget is the reported reason.
Mappings can be stale/incomplete; estimates are not actual runtime. Output
`complete_test_safety: false` and `coverage_basis: supplied_mapping_only` always.

Decisive controls: overlapping coverage changes the next choice, equal cases use
stable lexical ties, too-expensive tests do not block fitting alternatives,
zero-time tests fit a zero-time allowance, and unmapped symbols remain different
from known coverage omitted by the budget. No result authorizes skipping gates.

## Packaging boundary

Each logical package has a matching lowercase-hyphen skill folder under
`skills/`, containing SKILL.md, a script, two schemas, examples, acceptance cases,
an invocation prompt resource and method limits. Package README and repository
MIT notice explain portability/provenance. No competition `agent.yaml`, ADK
adapter, hook or plugin configuration is guessed. Those require the exact
competition harness README and a separately qualified binding.
