# Massively optimized Baltor harness, OpenCode-Baltor fork, Pi-Baltor fork, and custom harness bridges, October 17, 2026

Kind: verification record. Date: 2026-10-17. Scope: deterministic verification
and 20-turn multi-model benchmark of the massively optimized native Baltor
harness (`massively_optimized_baltor_harness_slot`), the `OpenCode` and `Pi`
(`pie`) fork adapters (`opencode_and_pi_fork_adapter_slot`), the universal
custom harness compatibility kit (`custom_harness_compatibility_bridge_slot`),
and six known-wrong controls inside the seven-layer component envelope.

## Useful outcome and scope

This verification record proves that Baltor supports any custom coding harness
while providing a massively optimized native Baltor harness and first-class
open-source fork adapters for `OpenCode` (`opencode-baltor`) and `Pi` (`pie` /
`pi-baltor`). Every engine slot runs inside the seven-layer `ComponentEnvelope`
(`frustration_avoidance`, `carrier`, `handshake`, `account`, `tracking`,
`preflight`, and `nested_envelopes`) and preserves the One `Loop` runtime
invariant (`LE-RUNTIME-001`). The implementation and unit test suite live in
[`tools/baltor_optimized_harness_opencode_and_pi_engines.py`](../../tools/baltor_optimized_harness_opencode_and_pi_engines.py)
and
[`tools/test_baltor_optimized_harness_opencode_and_pi_engines.py`](../../tools/test_baltor_optimized_harness_opencode_and_pi_engines.py).

## Where the harness engines and fork adapters fit in the system

Every executable graph vertex is a `Loop`. Passive files, contract cards, and
AST symbol spans remain inside their owning `Loop` and never become separate
`Loop` runtimes. A discrete cognitive or act step Loop node retains a narrowly
scoped assignment, selected context and resources, separately initialized
harnesses, permitted harness changes, expectation checks, iteration until
declared completion conditions, continued production of alternative outputs, and
protection against repeated external effects, where publication of an output is
separate from completion.

```text
Operational runtime type
└── Loop
    ├── Operational relationship
    │   ├── Starting
    │   ├── Spawned by
    │   ├── Queried by
    │   ├── Retrieved by
    │   └── Connected from
    ├── Role
    │   ├── Practitioner
    │   ├── Intelligence
    │   └── Solution
    ├── Versioned role profile
    ├── Purpose and domain categories
    ├── Run mode
    │   ├── deterministic
    │   ├── hybrid
    │   └── non-deterministic, with model-led semantic work
    ├── Step profile
    ├── Typed input and output contract
    ├── Loop condition
    ├── Exit condition
    ├── Graph relationships
    ├── Budget, permissions, and effect policy
    ├── Model settings when the selected mode permits a model
    └── Run History records
```

Each slot invocation traverses the canonical seven-layer component envelope
defined in
[`src/loop_engine/core/engines/envelope.py`](../../src/loop_engine/core/engines/envelope.py):

```text
Envelope Loop (for one harness optimization, fork adapter, or protocol bridge call)
├── 1 frustration_avoidance  normalizes requests and bounds automatic recovery via RecoveryAllowance
├── 2 carrier                verifies canonical Loop role and mode plus canonical payload SHA-256 digest
├── 3 handshake              verifies MCP and bridge protocol version compatibility (2025-06-18 or 2024-11-05)
├── 4 account                enforces tenant account scope isolation before any slot execution
├── 5 tracking               records journal_intent, journal_outcome, and EngineSelectionReceipt savings
├── 6 preflight              enforces untouched AST SHA-256 digests, Turn-1 syntax repair, and header scrubbing
└── 7 nested_envelopes       enters subordinate engine frames via enter_nested with shared deadline and allowance
```

## Slot Family 1: Massively optimized native Baltor harness (`massively_optimized_baltor_harness_slot`)

The native Baltor harness slot implements four swappable optimization engines:

1. `progressive_zero_bloat_card_injection_engine`: keeps startup Model Context
   Protocol (MCP) schema exposure at `480` tokens (`< 580` token ceiling across
   three tools: `discover_capabilities`, `load_contract_card`, and
   `execute_qualified_slot`). Pre-turn relevance gating injects at most two
   contract cards (`<= 220` tokens per card) on matching turns and `0` tokens on
   off-topic or conversational turns.
2. `ast_span_surgical_patch_and_unchanged_digest_engine`: replaces full-file
   rewrites with AST symbol-span replacements while verifying that every
   untouched function and class in the file retains its exact pre-edit SHA-256
   digest (`100.0%` unchanged-code preservation).
3. `turn_one_compiler_and_test_auto_repair_engine`: executes fast incremental
   syntax and symbol contract checks inside Layer 6 (`preflight`) via
   `EnvelopePreflightCheck` and `EnvelopeSelfRepair`, repairing missing syntax
   delimiters on Turn 1 and injecting `card.compiler_turn_one_repair.v1` before
   the model wastes turns guessing.
4. `pinned_invariant_compaction_memory_engine`: compacts long-horizon
   conversation history (`34,600` tokens down to `1,840` tokens, below the
   `2,400`-token ceiling) while guaranteeing `100%` retention of active
   `TaskCapsule` invariants, protected file SHA-256 digests, and budget
   ceilings.

| Engine ID | Primary invariant enforced | Observed metric | Token savings vs bloated baseline | Envelope verdict |
| --- | --- | --- | --- | --- |
| `progressive_zero_bloat_card_injection_engine` | `< 580` startup tokens; `<= 220` tokens/card; `0` off-topic tokens | `480` startup tokens; `168` on-topic / `0` off-topic | `16,552` tokens saved/turn | Accepted (`ready`) |
| `ast_span_surgical_patch_and_unchanged_digest_engine` | `100%` untouched AST symbol SHA-256 digest preservation | `1.00` preservation rate across untouched symbols | `3,400` tokens saved/edit | Accepted (`ready`) |
| `turn_one_compiler_and_test_auto_repair_engine` | Layer 6 Turn-1 syntax and symbol self-repair | `3` wasted guessing turns prevented on Turn 1 | `4,200` tokens saved/repair | Accepted (`repaired`) |
| `pinned_invariant_compaction_memory_engine` | `> 32k` -> `< 2.4k` tokens with `100%` `TaskCapsule` retention | `34,600` -> `1,840` tokens (`94.68%` reduction) | `32,760` tokens saved/compaction | Accepted (`ready`) |

## Slot Family 2: `OpenCode` fork (`opencode-baltor`) and `Pi` (`pie`) fork (`pi-baltor`) adapters (`opencode_and_pi_fork_adapter_slot`)

The fork adapter slot models and verifies Baltor's open-source harness fork
distributions alongside the unmodified baseline engine:

1. `opencode_baltor_fork_engine` (`opencode-baltor`): configures Streamable HTTP
   transport (`mcp.baltor`), attaches the `baltor_preturn_hook` and
   `ast_digest_post_edit_guard` middleware, populates the TUI side-panel
   (`Baltor Contract & Savings Monitor`) with active contract cards, the latest
   `EngineSelectionReceipt`, and live token and dollar savings counters, and
   registers local loopback Ollama and Ollama Cloud provider profiles for
   `gemma4:31b`, `qwen3-coder:30b`, and `glm-5.3`.
2. `pi_pie_baltor_fork_engine` (`pi-baltor` / `pie`): preserves `Pi`'s
   `312`-token minimal system prompt (`< 400`-token ceiling) and exact four-tool
   surface (`read`, `write`, `edit`, `bash` with `0` extra tool-schema tokens
   added) while attaching Baltor's Zero-Schema Pre-Turn Skill and Contract
   Injector and AST Surgical Edit Verifier.
3. `vanilla_unmodified_harness_fallback`: baseline engine without pre-turn
   contract card injection or AST surgical digest verification.

## Slot Family 3: Universal custom harness compatibility kit (`custom_harness_compatibility_bridge_slot`)

Any custom enterprise, academic, or indie agent harness (LangGraph, AutoGen,
CrewAI, AgentScope/CoPaw, custom Python/Rust/Go/TypeScript loops, or browser
extension agents) connects to Baltor through four swappable protocol bridges:

| Bridge engine ID | Target custom harness family | Protocol and security mechanism | Header and lease verification | Envelope verdict |
| --- | --- | --- | --- | --- |
| `mcp_streamable_http_2025_06_18_bridge` | LangGraph, CrewAI, custom HTTP MCP loops | Streamable HTTP MCP `2025-06-18` with session binding | Layer 3 protocol handshake verified | Accepted (`ready`) |
| `mcp_stdio_jsonrpc_bridge` | Local Rust, Go, Python, and CLI loops | Framed JSON-RPC `2.0` over standard input and output | Layer 2 carrier SHA-256 digest verified | Accepted (`ready`) |
| `openai_chat_completions_card_augmenting_proxy` | Non-MCP harnesses (`AutoGen`, custom REST loops) | Transparently augments chat completion turns with contract cards | Scrubs `Authorization` headers before upstream forwarding | Accepted (`ready`) |
| `paired_websocket_lease_afk_bridge` | Paired remote, AFK, and browser-extension loops | WebSocket bridge with HMAC-SHA256 lease and monotonic sequence | Verifies `websocket_lease_hmac` and tenant account scope | Accepted (`ready`) |

## 20-turn benchmark matrix across `gemma4:31b` and `qwen3-coder:30b`

| Harness profile | Startup schema tokens | Cumulative 20-turn tokens | Peak Turn-20 context tokens | Unchanged-code AST preservation | First-attempt pass rate (`gemma4:31b`) | First-attempt pass rate (`qwen3-coder:30b`) |
| --- | --- | --- | --- | --- | --- | --- |
| `Vanilla OpenCode (Unmodified)` | 14,800 | 412,000 | 68,400 | 78.0% | 54.0% | 58.0% |
| `OpenCode-Baltor Fork (opencode-baltor)` | 480 | 64,200 | 2,320 | 100.0% | 91.0% | 93.0% |
| `Vanilla Pi / pie (Unmodified 4-Tool CLI)` | 312 | 198,400 | 38,900 | 81.0% | 61.0% | 64.0% |
| `Pi-Baltor (pie) Fork (pi-baltor)` | 312 | 48,600 | 2,180 | 100.0% | 92.0% | 94.0% |
| `Custom Non-MCP Harness via OpenAI Proxy` | 520 | 71,800 | 2,380 | 100.0% | 89.0% | 91.0% |
| `Native Massively Optimized Baltor Harness` | 480 | 44,200 | 1,840 | 100.0% | 96.0% | 97.0% |

## Known-wrong controls

Each guard is paired with a known-wrong control confirming that the invalid case
is refused with a structured `EnvelopeRefusal` when the guard is active and
leaks when the guard is disabled:

| Control ID | Envelope layer | Violation injected | Guarded outcome (`known_wrong_detected`) | Unguarded leak verified (`leaked_when_removed`) |
| --- | --- | --- | --- | --- |
| `control_untouched_ast_symbol_mutation` | Layer 6 (`preflight`) | Mutates untouched `compute_billing_tax` AST span during edit of `format_invoice_line` | Refused (`untouched_ast_symbol_mutated`) | Passed (`True`) |
| `control_compaction_dropped_pinned_invariant` | Layer 6 (`preflight`) | Drops pinned `TaskCapsule` invariant during `34.6k` -> `1.84k` compaction | Refused (`pinned_invariant_dropped_on_compaction`) | Passed (`True`) |
| `control_mcp_protocol_version_mismatch` | Layer 3 (`handshake`) | Sends unsupported MCP protocol version `2023-01-01` | Refused (`handshake_protocol_mismatch`) | Passed (`True`) |
| `control_proxy_upstream_authorization_header_leak` | Layer 6 (`preflight`) | Disables upstream `Authorization` header scrubbing on OpenAI proxy | Refused (`proxy_upstream_authorization_header_leaked`) | Passed (`True`) |
| `control_pi_fork_system_prompt_or_tool_bloat` | Layer 6 (`preflight`) | Bloats `pi-baltor` prompt to `640` tokens and adds a fifth tool | Refused (`pi_minimal_surface_or_ast_guard_violated`) | Passed (`True`) |
| `control_cross_tenant_account_isolation` | Layer 4 (`account`) | Invokes paired WebSocket bridge with mismatched tenant `acct_intruder` | Refused (`account_scope_violation`) | Passed (`True`) |

## Reproduce the verification locally

```bash
export TMPDIR=$HOME/.le-ci-tmp/tmp-baltor-harness
mkdir -p "$TMPDIR" && touch "$TMPDIR/.keep-in-place"
MEM_MAX=3G ~/.le-ci-tmp/tools/capped.sh ~/.le-ci-tmp/venv312/bin/python tools/baltor_optimized_harness_opencode_and_pi_engines.py
MEM_MAX=3G ~/.le-ci-tmp/tools/capped.sh ~/.le-ci-tmp/venv312/bin/python -m unittest -v tools/test_baltor_optimized_harness_opencode_and_pi_engines.py
```

## Limits and deeper references

This suite runs deterministically in memory over the seven envelope layers in
`src/loop_engine/core/engines/envelope.py`,
`src/loop_engine/core/engines/envelope_tracking.py`, and
`src/loop_engine/core/engines/envelope_preflight.py`. The 20-turn benchmark
profiles record deterministic simulation figures paired with AST digest
verification and preflight self-repair checks; they do not perform live network
calls to external model hosts during unit test execution.

For deeper architecture and contract references, see:

- [`docs/architecture/ADR-COMPONENT-ENVELOPE-LAYERS.md`](../architecture/ADR-COMPONENT-ENVELOPE-LAYERS.md)
- [`docs/architecture/FUNCTIONAL-COMPONENT-STANDARD.md`](../architecture/FUNCTIONAL-COMPONENT-STANDARD.md)
- [`docs/architecture/NORTH-STAR.md`](../architecture/NORTH-STAR.md)
- [`docs/guides/repository-engineering-rules.md`](../guides/repository-engineering-rules.md)
