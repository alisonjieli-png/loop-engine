# Candidate local protocol connection: JSON shape tool

Kind: candidate-only multi-file connection and tool review, September 22,
2026. This package is **not approved, installed for users, or included in
the hosted catalogue**. The current source `server.py` has SHA-256
`38129d0840d56679a4046cfac943418e2b6e71560873cd3cb3c72296d0c27332`.

## Logical package and physical files

One logical candidate contains a local Python protocol server,
`requirements.txt` pinned to `mcp==1.29.0`, tests, a renderer and three
alternative client layouts. Each layout copies the same server and
dependency declaration to `work/tools/json_shape_mcp/` and supplies one
native configuration file:

| Client candidate | File intended for a fresh step root | Qualification state |
|---|---|---|
| Codex 0.155.1 | `work/.codex/config.toml` | Syntax checked. Project trust, relative working directory and native tool listing for these exact files are untested. |
| Claude Code 2.1.280 | `work/.mcp.json` | Syntax checked. The exact candidate has not been natively connected. A headless Claude session can load project protocol servers without an interactive approval prompt, so do not place this file in a real project before admission. |
| OpenCode 1.17.9 | `work/opencode.json` | Native listing tested in an isolated temporary workspace. This is the installed 1.x configuration form; a newer client schema requires a separate profile and test. |
| Pi 0.73.1 | No native protocol file | Unsupported without a separately reviewed extension. |

These are **three renderings of one server**, not three independent
intelligence methods. The `server.py` tool accepts a bounded JSON string
and returns only its top-level type, object field count and up to 100
field names with a truncation flag, or array length. It
refuses malformed input, nonstandard `NaN` and `Infinity`, duplicate
object keys and input above 65,536 bytes. Error text does not echo a
duplicate key. It reads no file and opens no network connection. Running
the server itself starts a local process, which still needs a declared
tool/connection authority. JSON field names can contain sensitive
information; this tool makes no data-classification decision.

## Saved observations and checks

- `tests/test_server.py`: three tests pass. The Python protocol client
  initialized a real local subprocess, listed exactly
  `inspect_json_shape`, called it, and observed refusals for `NaN` and
  duplicate keys without a model call. The negotiated protocol version
  was **2025-11-25**.
- `tests/test_configs.py`: four checks pass, including refusal of
  broadened OpenCode tool permission and unexpected credential fields.
- `render_layouts.py --check`: nine rendered files match the canonical
  server, dependency pin and configuration templates. The renderer
  refuses symlinked parent paths and needs explicit `--replace` before
  overwriting changed candidate files.
- [Unqualified OpenCode probe](OPENCODE-MCP-CONNECTION-UNQUALIFIED-2026-09-22.json):
  OpenCode listed this server but the connection closed under a clean
  home with generic `python3`. The saved listing alone did not show why.
  A separate [same-source dependency failure receipt](OPENCODE-MCP-DEPENDENCY-FAILURE-RECEIPT-2026-09-22.json)
  ran that command under the same clean-home policy and recorded
  `ModuleNotFoundError` for the protocol SDK.
- [Qualified-interpreter OpenCode probe](OPENCODE-MCP-CONNECTION-QUALIFIED-2026-09-22.json):
  the same source server connected when the temporary workspace used an
  ephemeral interpreter with pinned `mcp==1.29.0`. The temporary
  environment was removed after the probe. The
  [reproduced receipt](OPENCODE-MCP-QUALIFIED-INTERPRETER-RECEIPT-2026-09-22.json)
  records the interpreter and SDK versions, rendered config digest and
  config with its temporary path redacted. The canonical config invoking
  `python3` did **not** connect under clean home; the successful trial
  used a modified interpreter command. No model or external server was
  called. A zero exit status from `opencode mcp list` alone did not mean
  the server connected; the reported connection state was checked.

The [Model Context Protocol Python SDK](https://github.com/modelcontextprotocol/python-sdk)
is a separate dependency with its own MIT licence; its exact installed
version and transitive dependencies need a release bill of materials and
qualified environment. Copying `requirements.txt` does **not** install
it. A production placement plan must bind a prepared interpreter to the
configuration before launch, rather than quietly falling back to the
user's Python environment or installing packages during a customer step.

## Admission holds

The current server and test client support the handshake-era protocol
`2025-11-25`; they have not qualified the stateless `2026-07-28`
revision. Codex and Claude Code have not loaded this exact rendered
candidate in a no-model instance, and OpenCode support is limited to
the installed 1.x client. Client trust, startup sources, process identity,
tool permissions, cancellation and credential isolation must be checked
under the actual native adapter. The renderer does not place or enable
anything outside this isolated artifact. Generated `__pycache__` files
must not enter a package manifest or customer release.

The exact source and all nine renderings need independent package review,
rights and dependency approval, native load evidence, and a customer
distribution licence before any active catalogue item is created. A
successful local tool call is not evidence that this package improves a
customer task.
