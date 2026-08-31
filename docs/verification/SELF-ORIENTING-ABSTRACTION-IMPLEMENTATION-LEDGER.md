# Self-orienting abstraction implementation ledger

Repository revision at start: `e197a3e61591bf760426da7d21e0ebab9e89fd50`.
Branch: `main`. Delivery actions were not authorized and were not performed.

The working tree already contained the Reusable Capability Flywheel,
transactional semantic runtime, Context Intelligence fallback, and related
documentation changes. Those changes were preserved.

## Implemented surfaces

| Surface | Main files | Purpose |
|---|---|---|
| Repository orientation | `devtools/src/loop_engine_devtools/assurance/orientation.py` | Discover roots, entry points, symbols, imports, calls, configuration reads, authorities, checks, digests, drift, and exact bindings. |
| Hardcoding audit | `devtools/src/loop_engine_devtools/assurance/hardcoding.py` | Contextual AST and structured-resource findings, redaction, classifications, stable IDs, duplicates, allowlist, JSONL, delta, and CI severity gate. |
| Devtools CLI | `devtools/src/loop_engine_devtools/cli.py` | Orientation, validation, audit, baseline, allowlist, output, self-test, and new-finding controls. |
| Audit policy | `devtools/hardcoding-allowlist.yaml`, `devtools/hardcoding-ci-baseline.json` | One exact local-literal exception and a complete current finding baseline that blocks only new high findings. |
| Parameter governance | `src/loop_engine/core/parameter_resolution.py`, `src/loop_engine/core/runtime_settings.py` | Tagged omission states, typed definition, deterministic precedence, safe resolution records, bounded Intelligence proposal, and compatibility-preserving LoopConfig integration. |
| Prompt governance | `src/loop_engine/strings/prompt_fragments.py` | Typed versioned bundles, components, slots, trust classes, size, provenance, omission, exact digests, and deterministic rendering. |
| Prompt consumers | `src/loop_engine/code_nodes/campaign_runner.py`, `src/loop_engine/core/external_harness_adapters.py`, `src/loop_engine/core/external_harness.py` | Campaign trust boundaries and external harness instruction identity in safe result records. |
| OpenRouter correction | `src/loop_engine/core/openrouter_client.py`, `src/loop_engine/core/task_compile_model.py`, `src/loop_engine/cli_operations.py` | Text-only zero-price selection, explicit capacity filtering, native structured-output preference, and exact maximum retention. |
| Graphify scoping | `.graphifyignore` | Exclude generated evidence and schema-governed JSON from the optional descriptive source graph. |
| Architecture | `architecture.yaml`, `terminology.yaml`, packaged projections, architecture map, public API, contract index | Register one parameter and prompt boundary without adding a runtime or settings authority. |
| Continuous enforcement | `.github/workflows/ci.yml` | Run devtools canaries and block new high-severity hardcoding findings. |
| Research and guidance | Graphify evaluation, ADR, verification report, master prompt, prompt indexes | Preserve upstream facts, observed limits, design decision, evidence, and the paste-ready development mandate. |

## Key commands and results

### Repository and Development Assurance

```text
PYTHONPATH=src:devtools/src python3 -m loop_engine_devtools.cli --self-test
PASS: 19/19 current canaries

PYTHONPATH=src:devtools/src python3 -m loop_engine_devtools.cli --orientation
orientation.sha256_c2856f69b832f1a4147cf990b0353b6f886cb46febba610fac180d32051e257e
18 bindings, 0 unresolved, 0 contradictions

PYTHONPATH=src:devtools/src python3 -m loop_engine_devtools.cli --hardcoding-audit ...
773 files, 179,388 literal candidates, 9,379 material findings
770 high, 8,609 medium, no new high findings
```

### Focused source checks

```text
Parameter resolution                         16/16
Prompt resources                             13/13
Campaign runner                               6/6
External harness adapters                    21/21
OpenRouter client                             6/6
Model-assisted task compile                  14/14
Architecture map                             13/13
Orientation                                   7/7
Hardcoding audit                             12/12
Total                                       108/108
```

### Source suite and conformance

```text
PYTHONPATH=src python3 -m loop_engine --conformance
All zero-tolerance gates pass. Eight guard-enforced rails are active.

PYTHONPATH=src python3 -m loop_engine --self-test
1,646/1,646 passed in 106.600 seconds. Provider calls: 0.
```

### Graphify

Exact upstream source: Graphify 0.9.53 at
`33362d969292b57eda82f3fbd9eb5f3f5bc9bbc2`.

```text
graphify extract /home/username/loop-engine --code-only --no-cluster --max-workers 4

Unfiltered cold: 575 files, 8,736 explicit entities, 24,973 relationships,
10.89 seconds, 406,296 KB peak memory.

Filtered cold: 401 files, 7,985 explicit entities, 24,164 relationships,
10.42 seconds, 404,012 KB peak memory.

Filtered unchanged: 0 changed files, 1.17 seconds, 78,116 KB peak memory.
```

Filtered graph SHA-256:
`005a36f9a7b3ca2a62a50ed6e51f02cb95111f25412ce71a2a9e61c4f548f413`.

### Real providers

Ollama Cloud exact probe:

```text
Provider: ollama_cloud
Route: cloud.default
Model: deepseek-v4-flash:0731
Physical calls: 1
Tokens: 66 input, 119 output
Status: accepted
```

OpenRouter accepted zero-price call:

```text
Provider binding: openrouter_zero_cost
Model: liquid/lfm-2.5-2.6b:free
Exact output maximum: 8,192
Physical calls: 1
Tokens: 38 input, 63 output
Status: accepted
```

Mistral and OpenCode were not run because their values were not available to
the current process or recoverable from the checked user-authorized local
records. Their key names in documentation are not credentials.

Real bounded parameter inference:

```text
Provider: ollama_cloud
Model: deepseek-v4-flash:0731
Physical calls: 1
Tokens: 234 input, 184 output
Proposal confidence: 0.9
Deterministic result: stable
Resolution source: Intelligence proposal, precedence rank 9
```

### Packaging

The first source-tree wheel was rejected because the repository's pre-existing
`build/` directory leaked retired `universal_solve.py` into the wheel. The
directory was not deleted. A clean wheel was rebuilt from a fresh extraction of
the source distribution.

```text
Clean Loop Engine wheel
f3eef34372828ee59cde655a4e2fb542d6b9f1ad2718cc928627cc4a9071f20d

Source distribution
5c8e17252e0e97dbc27552d4bd1c05c150a93c04845e9806f4a5812f3a47890d

Devtools wheel
095a51862bd34a4c880db4a6d140ef037ca064bf7c58f066536e5723dd7e9d0b
```

Clean Python 3.10 results:

```text
Installed conformance: all gates pass
Installed devtools: all canaries pass
Installed full suite: 1,617/1,617 in 162.258 seconds
Provider calls: 0
```

The clean base installation did not test optional DuckDB, MCP, model2vec,
NumPy, OpenTelemetry SDK, pandas, or scikit-learn adapters.

## Machine evidence

- `artifacts/verification/repository_orientation_snapshot.json`
- `artifacts/verification/hardcoding_audit_baseline.jsonl`
- `artifacts/verification/hardcoding_audit_final.jsonl`
- `artifacts/verification/self_orienting_abstraction_results.json`
- `artifacts/verification/reusable_capability_flywheel_results.json`
- `artifacts/verification/semantic_runtime_results.json`

## Known limits

- CodeGraph MCP was specified in repository instructions but was not available
  in this tool session and `.codegraph/` was absent. Graphify was evaluated
  independently and did not become an authority replacement.
- Graphify free-form queries over-expanded on the two tested questions.
- Graphify raw files carried implicit external endpoints that require adapter
  normalization.
- The hardcoding audit still has 9,379 material triage findings. They are not
  all defects and were not mechanically centralized.
- No independent human-labeled precision sample exists for the audit yet.
- OpenRouter free-tier availability produced later rate-limit failures after
  the accepted call.
- Real provider probes demonstrate integration and contract behavior, not full
  solve quality or economic savings.
- The current working tree remains uncommitted and unpublished.

## Highest-value next increment

Build a versioned optional descriptive Code Intelligence adapter at the
existing MCP and Code Intelligence boundaries. Normalize Graphify implicit
endpoints, bind results to source digests, and evaluate exact symbol, impact,
and context-package questions against a frozen manual truth set. Do not make
free-form graph retrieval or an external graph artifact executable authority.
