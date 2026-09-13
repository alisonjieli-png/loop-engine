# Current Rust OpenInterpreter adapter experiment

OpenInterpreter 0.0.42 completed a headless text roundtrip through a scripted
private Responses provider. The actual request contained `tools: []`, and its
Codex-compatible event stream returned the exact candidate. No real model was
called. This is the current Rust project, not the historical Python 0.4.3
package, and both versions count as one OpenInterpreter project.

The [official repository](https://github.com/openinterpreter/openinterpreter)
identifies this project as a Codex fork. Release `rust-v0.0.42`, published on
2026-09-08, resolves to source revision
`67299aeb7c1089be425cb7809169747af1e61af5`. The downloaded Linux musl archive
matches the release's published SHA-256 sum. The source license is Apache-2.0.

The recipe uses the actual `interpreter exec` binary, a private provider,
an explicit model catalog, and disabled native tool and skill features. This
version uses `INTERPRETER_HOME` and deliberately ignores `CODEX_HOME`; its home
is set inside the private workspace. It supports a separate Chat Completions
option, but this experiment qualifies its Responses path only.

Enabling native command tools caused refusal before the scripted callback.
An injected undeclared `exec_command` produced an unsupported-call error and
created no file. The text codec refused the following tool-result request.

The [saved probes](../../artifacts/harness-expansion-20260909-DNMQ3Y/responses-recipes/)
preserve both successful and failed attempts. They prove this bounded local
transport configuration, not task quality or a full-system benchmark. Any real
model integration must use the separately authorized Ollama Cloud broker,
which enforces the supplied output allowance after protocol translation.
