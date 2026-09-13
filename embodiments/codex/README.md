# Codex text adapter experiment

Installed Codex 0.153.4 completed a headless text roundtrip through a scripted
private Responses provider. The actual request contained `tools: []`, and the
CLI returned the exact candidate in a completed turn. No OpenAI or other real
model was called.

The private configuration disables shell, image, collaboration, permission,
plan, user-input, and other native tool features. Its explicit model catalog
sets `shell_type: disabled`, `apply_patch_tool_type: null`, and an empty
`experimental_supported_tools` list. Bundled skills and automatic skill
instructions are disabled. Task text travels through stdin, and `CODEX_HOME`
points inside the private workspace.

The provider uses `wire_api = "responses"`, which is the documented custom
provider protocol. The implementation also uses the documented custom model
catalog and shell feature settings. See the
[official configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference).
Exact additional tool gates were checked against the pinned upstream source.

When the fixture enabled native command tools, the broker refused the request
before a callback. When the fixture sent an undeclared `exec_command` anyway,
Codex reported `unsupported call: exec_command`; no file was created. The
following tool-result request was refused by the text codec.

The installed npm package declares Apache-2.0. The official source tag
`rust-v0.153.4` resolves to
`3d2ee51ca2d5db578f328aa75e20aa22c0197c9a` in
[openai/codex](https://github.com/openai/codex). The local manifest records the
actual installed binary; the qualification record binds its digest.

The [saved probes](../../artifacts/harness-expansion-20260909-DNMQ3Y/responses-recipes/)
include initial catalog and codec failures. These are local transport and
tool-boundary results, not provider integration or task-quality results. Any
future real model call requires the separately authorized Ollama Cloud broker.
That broker must apply the typed output allowance to the translated request.
