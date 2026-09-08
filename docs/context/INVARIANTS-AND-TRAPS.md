# Invariants and traps

Two lists. The first is what the machine refuses, so you can predict a failure
before you cause it. The second is mistakes already made in this repository
that cost real time, so you do not repeat them.

Every item in the trap list says how it was established. Items marked verified
here were reproduced while writing this page. Items marked recorded earlier
come from a previous session's notes and were not re-run.

## What the machine refuses

`--conformance` runs 27 gates and every one of them has a tolerance of zero.
The full list of names is in the command's own output. These are the ones you
are most likely to trip.

| Gate | What it refuses | How to satisfy it |
|---|---|---|
| `unclassified_files` | a module that no group in `architecture_map.py` names | add the module name to its group list |
| `architecture_map_freshness` | `src/loop_engine/ARCHITECTURE-MAP.md` differing from `render_map()` | regenerate the file from its generator, never by hand |
| `modules_whose_self_test_the_suite_never_runs` | a module with a `self_test` the aggregator does not fold in | add it to `_FOLDED_SUBMODULE_TESTS` in `_self_test.py` |
| `subprocess_outside_declared_adapters` | `subprocess` anywhere but a declared adapter | do the work in process, or declare the adapter |
| `eval_or_exec_anywhere` | exactly what it says | there is no exception |
| `direct_model_or_network_calls_outside_gateway` | a provider call that bypasses the model gateway | route it through the gateway |
| `secret_shaped_literals_in_code_or_run_records` | a literal shaped like a credential | reference the variable name through settings |
| `modules_missing_llm_context_docstring` | a module without the docstring shape used across the tree | say what the module owns and does not own |
| `modules_over_size_cap_without_declared_exception` | a module past the size cap | split it, or declare the exception |
| `runtime_event_kinds_outside_the_canonical_vocabulary` | an invented ledger event kind | extend the vocabulary deliberately |
| `operational_graph_vertex_types_outside_canonical_loop` | a second runtime type | there is one Loop; roles and modes are fields |

Adding one module therefore touches three places: the group list in
`architecture_map.py`, the regenerated `ARCHITECTURE-MAP.md`, and the folded
list in `_self_test.py`. Miss any one and conformance fails with a gate name
that tells you which.

## The documentation checks are three different checks

They have different file lists, so a document can pass one and fail another.
All three run in the `public documentation` job.

| Check | Scope | Refuses |
|---|---|---|
| `markdownlint-cli2` | a fixed file list plus `docs/**/*.md`, `case-studies/*.md`, `examples/**/*.md` | structural problems |
| `vale` | `AGENTS.md`, `README.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`, `humanizer-context.md`, `showcase/README.md`, `docs`, `case-studies`, `examples`, minus the paths `.vale.ini` exempts | em and en dashes anywhere; retired terms and retired topology outside `docs/verification` |
| a ripgrep step | `README.md`, `CHANGELOG.md`, `humanizer-context.md`, `docs`, `examples`, `case-studies`, `benchmarks`, `showcase`, excluding `docs/prompts`, `docs/evidence` and `docs/verification` | the retired words on their own |

Practical rules for prose here: no em or en dashes, use a period, comma, colon
or parentheses instead. Do not write the retired words for a stored record, a
spawned Loop, or an exit condition. Say record, report, log, event history or
evidence; say spawned Loop; say exit condition. Dated reports under
`docs/verification` may quote a retired term, because a finding about a
retired term has to name it, and both the ripgrep step and `.vale.ini` exempt
that path for that reason.

## Traps

**The interpreter.** The repository virtual environment is Python 3.10. The
system `python3` is 3.14 and does not have the package installed, so a bare
`python3` fails as though the module were missing. Always use
`.venv/bin/python` with `PYTHONPATH=src`. Verified here.

**A context block the model never sees.** `_render_packet_governed` in
`core/adaptive_practitioner_prompting.py` builds the prompt from
`BLOCK_SOURCES`, a fixed map of packet fields. A context block you declare on
a field that map does not carry is invisible, and nothing raises. Put new
runtime facts inside a field the map already carries, and keep the guard named
`facts_the_runtime_states_reach_the_rendered_prompt`. Verified here.

**Context block positions must be contiguous.** `LLMWorkPacket` refuses unless
the block positions are exactly `0..N` with no gap, and the failure kills the
run rather than degrading it. If you add a block behind a condition, another
conditional block will eventually leave a hole. The safe move is to extend a
mapping a block already carries instead of adding a block. Verified here.

**A self-test that asserts an interpreter property.** A check here assumed a
JSON document nested 1,500 levels deep would exhaust the decoder. That is true
on this machine and false on the build runners, so the check passed locally
and failed on all three Python versions in CI. Probe for the real limit rather
than assuming one. Verified here, on 2026-09-08.

**A broad process kill hits another session.** Another agent runs Loop Engine
self-tests from a different checkout on this machine. A command like
`pkill -f 'loop_engine --self-test'` matches its processes as well as yours
and kills both runs. Run long gates through a wrapper script whose command
line no broad pattern matches. Verified here, after doing exactly this.

**Another agent commits into this checkout.** The working tree moves under
you. Check `git log` and `git status` before and after any long operation,
stage explicit paths, and never use `git add -A`. Verified here: the head
moved twice mid-session.

**`/tmp` is a memory-backed filesystem.** A single campaign wrote about 570 MB
before a bound landed, and stale scratch directories accumulate without limit.
Check `df -h /tmp` before a campaign and prune `loop-engine-*` directories.
Recorded earlier.

**The sandbox image must be named by digest and must carry the stack.** A tag
is refused with a message about immutable digests. The default image is a bare
interpreter with no data science packages, so a modelling task refuses
honestly and spends its passes discovering it cannot work. Set
`LOOP_ENGINE_SANDBOX_IMAGE` to a digest-pinned image that has what the task
needs. Recorded earlier.

**Atomic primitives have no native bypass.** A check named
`strict_atomic_symbols_have_no_native_bypass` in `core/primitive_conformance.py`
scans self-test bodies too, so a native string operation used as a shortcut
inside a check fails the suite. Recorded earlier.

**An allowlist entry must agree with the audit.** The hardcoding allowlist
requires the entry's classification to equal the audit's own classification
for that finding, even when you think the finding is wrong. Renaming or
deleting the offending construct is usually better than arguing with it in an
allowlist entry. Recorded earlier.

**The audit's test-fixture exemption is narrow.** It exempts a literal when
the enclosing symbol is named `self_test`, so a literal inside a nested
function or a helper called from a self-test is not exempt. Twenty of the 260
blocking findings are of this kind. Measured here on 2026-09-08.

## Two claims to check before you make them

**"The gates are green."** Say which gates, on which commit, and cite the
GitHub run. The suite job on `main` has failed one gate since 2026-09-05, so a
report that quotes only local counts hides a red build.

**"The capability works."** A module can have passing checks and no caller.
Ask whether a live path reaches it:

```bash
PYTHONPATH=src .venv/bin/python -c \
  "from loop_engine.reachability_report import reachability_report; \
   print(reachability_report('solve_path'))"
```

If you wire a capability, add it to `REQUIRED_REACHABLE` in
`reachability_report.py` so it cannot go dark again without the check naming
it.
