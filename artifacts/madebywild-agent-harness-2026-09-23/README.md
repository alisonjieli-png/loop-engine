# Agent Harness research evidence

Source: `madebywild/agent-harness` at
`2ecf44f97ab6ffd76f5c1a58ac57b930e2ccfa17` (`v2.1.0`).
These are research observations, not package approvals or runtime qualifications.

- [Compatibility and adoption report](../../docs/research/MADEBYWILD-AGENT-HARNESS-COMPATIBILITY-AND-ADOPTION-2026-09-23.md)
- [Architecture and ownership report](../../docs/research/MADEBYWILD-AGENT-HARNESS-ARCHITECTURE-AND-OWNERSHIP-2026-09-23.md)
- [Renderer observations](adapter-observations.json)
- [Native Codex observations](native-codex-observations.json)
- [Sandboxed renderer recheck](adapter-sandboxed-recheck.json)

## Reproduce the renderer observations

Use a disposable checkout of the exact upstream revision and an isolated scratch
folder. Install `@iarna/toml@2.2.5`, `yaml@2.8.2`, `zod@4.4.3` and
`typescript@5.9.3` into the scratch folder with npm's `--ignore-scripts`,
`--no-audit` and `--no-fund` options. Do not initialize Agent Harness in Loop
Engine or an existing customer workspace.

```bash
node probe-adapters.mjs UPSTREAM_CHECKOUT SCRATCH_FOLDER NEW_OUTPUT_JSON
```

The probe transpiles exact provider modules and calls pure render functions with
synthetic inputs. It does not type-check or run the upstream full suite. It
does not run any generated command, connect a protocol server, install a native
plugin, start a model, or invoke the upstream command line tool. Record the
Node and compiler versions, dependency lock, source hashes and resulting file.

The first attempted transpilation used `node:module.stripTypeScriptTypes`.
Node 22.22.1 returned `ERR_NO_TYPESCRIPT`: this local build has no built-in
TypeScript support. No renderer output or model call resulted. The successor
uses TypeScript 5.9.3; this environment failure is retained here separately.

The successful renderer run was independently repeated inside a network
namespace with an empty environment, a read-only host filesystem, bounded
writable analysis directories, a 128 MB JavaScript heap and a 30-second process
timeout. All provider outputs, control results and source hashes matched the
first successful run. This qualifies that scoped experiment, not the upstream
application's general filesystem or native runtime behavior.

## Reproduce native loading

`probe-native-codex.py` reads the adjacent frozen renderer observation and runs
`codex debug prompt-input` in five temporary workspaces with synthetic inputs,
isolated user configuration and no credentials. It records input hashes and
checks that project files did not change. Use a new evidence folder for a new
run rather than replacing the saved observation.

Both skill locations exposed metadata in installed Codex 0.155.1. Full skill
bodies were not initially exposed. Neither subagent case exposed the reviewer
marker, including the comparison control, so this observation is inconclusive
for subagent correctness. A successfully parsed prompt cannot prove that every
configuration field was applied.

There were zero model calls. Closed proxy settings are not an operating-system
network sandbox. Neither this probe nor the renderer probe establishes native
hook behavior, subagent spawning, accepted task results or performance benefits.
