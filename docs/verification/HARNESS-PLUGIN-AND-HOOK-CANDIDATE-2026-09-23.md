# Native plugin and hook candidate, September 23, 2026

Kind: original candidate artifact and bounded qualification record. The
owner clarified that harness intelligence includes tools, plugins,
contracts, hooks, agent definitions and other native files. This work
produces **one Claude Code plugin candidate with 13 package files and no
`SKILL.md`**. It contributes zero independently approved or hosted packages.
The existing roadmap S-6.40 and S-6.44 own admission and native delivery.

## Package and purpose

The [candidate folder](../../artifacts/harness-plugin-context-2026-09-23/README.md)
contains a focused-step briefing plugin. Its SessionStart hook adds fixed
briefing guidance. Its deterministic standard-input tool checks a supplied
brief's structure and verifies that each declared output has a named
acceptance check. A custom command describes safe invocation; an advisory
agent reviews gaps in a supplied brief only when model review is authorized.
The package does not run the declared task or open paths named in a brief.

```text
Native Claude Code plugin candidate
├── Identity: .claude-plugin/plugin.json
├── Hook registration: hooks/hooks.json
├── Native command: commands/check-brief.md
├── Advisory agent: agents/brief-reviewer.md
├── Executable resources
│   ├── scripts/session_start.py
│   ├── scripts/check_brief.py
│   └── scripts/protocol.py
├── Typed resource contracts
│   ├── contracts/brief-input.schema.json
│   ├── contracts/brief-output.schema.json
│   ├── contracts/hook-input.schema.json
│   ├── contracts/hook-output.schema.json
│   └── contracts/example-brief.json
└── Licence: LICENSE
```

[The inventory](../../artifacts/harness-plugin-context-2026-09-23/candidate-manifest.json)
binds every path, role, byte count, pickup mechanism and SHA-256. Its digest
at this report is
`fdfd23ea7ea160a66d5d3be7805261050595ea07597497b35c021da8a4ee68ff`.
The package's original source follows the repository MIT licence; its
licence notice is included. Test, evidence and inventory files outside the
native package are review material, not additional usable packages.

## Existing work and official sources inspected first

[Anthropic's plugin reference](https://code.claude.com/docs/en/plugins-reference)
documents native manifest, hook, agent and command locations. The
[plugin guide](https://code.claude.com/docs/en/plugins) documents loading a
local package with `--plugin-dir` without a persistent installation. The
[hook reference](https://code.claude.com/docs/en/hooks) defines SessionStart
input and `hookSpecificOutput.additionalContext`. The
[subagent reference](https://code.claude.com/docs/en/sub-agents) describes
agent frontmatter and tool restrictions. These primary sources were read
on September 23 before building. The native command is a flat command file,
which this installed client inventories under skills; no `SKILL.md` wrapper
was added to satisfy that name.

The existing [Loop Engine plugin bundle boundary](../../src/loop_engine/core/plugin_bundles.py)
is a passive composition of admitted skill references with its own manifest.
It is not a native Claude Code package renderer. This candidate is an
artifact for the existing native installation work, not another runtime,
a production registry or a replacement for that boundary. The earlier
[JSON-shape tool candidate](../../artifacts/harness-intelligence-format-pilot-2026-09-22/connections/json-shape-stdio/server.py)
supplied a useful parser-rejection pattern. Its code was not copied; its
bounds and purpose do not cover brief validation, so the small
standard-library tool here is original.

## What was actually observed

Only **Claude Code 2.1.280** was inspected. Its native command-line parser
strictly accepted the manifest and refused a copied manifest whose name
contained spaces. Isolated home and configuration directories were used,
without credentials, a prompt, a model turn or a persistent installation.

`claude --plugin-dir <candidate> plugin details
baltor-focused-brief-candidate` listed **one command, one agent and one
SessionStart hook**. That is native component discovery. A separate
[independent review](../../artifacts/harness-plugin-context-2026-09-23/INDEPENDENT-QA-2026-09-23.md)
then ran `--init-only` in a disposable working directory, home and
configuration with this exact package. Claude Code 2.1.280 reported the
startup hook succeeded and accepted 603 characters of additional context.
This establishes native startup hook execution and host context acceptance.
No model request, command use or agent model execution occurred.
The command-line inventory's token costs are estimates; they do not measure
provider usage or the context later emitted by the hook.

The native validator returned empty component arrays when pointed at the
plugin or component directories. Passing individual Markdown and hook
files instead made it interpret them as manifests and refuse them. These
failed probes are preserved in the
[initial component record](../../artifacts/harness-plugin-context-2026-09-23/evidence/native-components-initial.json)
and [isolated discovery record](../../artifacts/harness-plugin-context-2026-09-23/evidence/native-components-isolated.json).
The passing manifest validator is therefore not counted as complete hook
or agent validation.

| File behavior | Evidence now | Still required |
|---|---|---|
| Manifest and native component inventory | Actual installed command line recognizes the package and its three components | Exact-byte independent admission and installed-session compatibility |
| Hook registration | Native inventory lists SessionStart; independent startup event succeeds | Resume, clear, compact and timeout behavior in the native client |
| Hook output | Direct protocol tests pass; native startup accepts 603 characters of additional context | Whether a model uses that context correctly under a declared task and budget |
| Deterministic checker | Valid and invalid JSON briefs exercise a real local process | Native command invokes the tool safely, and independent task evaluation measures whether the brief helps |
| Command and agent definitions | Native inventory lists both | Actual authorized invocation; effective tool restriction; useful advisory results |
| JSON contracts and example | Independent JSON Schema validation and cross-checks against the tool | Resources selected and referenced by a native task, rather than merely present on disk |

## Tests and preserved failures

The [final check record](../../artifacts/harness-plugin-context-2026-09-23/evidence/final-checks-4.json)
is bound to the manifest above. **Twenty-six tests pass**, along with Ruff,
manifest integrity and native strict manifest validation. The test engine
uses `jsonschema` 4.26.0; delivered scripts use only Python's standard library.
A copied mutant with the output-coverage guard removed fails
`test_output_without_check_refused`. No repository check was weakened.

Tests cover missing and unsupported contract fields, duplicate check
identifiers, unknown outputs, an output without a check, empty assertions,
unknown effects, duplicate effects, wrong scalar types, unanswered-question
counting, exact 65,536-byte input acceptance and larger-input refusal,
16-level nesting, malformed UTF-8, duplicate JSON keys, nonstandard numeric
constants, an extreme exponent, escaped surrogates, quoted brackets,
nonexecution of command-shaped input and no echo of supplied values.

A schema review found that a final newline in an identifier was accepted by
the initial schema's regular-expression end anchor while the tool refused
it. An explicit character exclusion now aligns the schema and tool, and the
agreement test includes that counterexample. The
[predecessor schema](../../artifacts/harness-plugin-context-2026-09-23/evidence/initial-brief-input.schema.json),
[predecessor inventory](../../artifacts/harness-plugin-context-2026-09-23/evidence/initial-candidate-manifest.json),
[previous check record](../../artifacts/harness-plugin-context-2026-09-23/evidence/final-checks.json)
and [correction record](../../artifacts/harness-plugin-context-2026-09-23/evidence/schema-boundary-correction.json)
remain beside the successor. A passing structure check still cannot judge
whether a natural-language acceptance assertion is adequate.

Independent code review by `multifile_wave2_independent_qa` found that the
inventory builder ignored an unexpected FIFO in the plugin tree. The
[failed replay](../../artifacts/harness-plugin-context-2026-09-23/evidence/manifest-fifo-failure.json)
records acceptance of that known-wrong tree before repair; the
[old builder](../../artifacts/harness-plugin-context-2026-09-23/evidence/initial-build-manifest.py.txt)
is retained. The repaired builder refuses nonregular paths and symlinks. Added tests cover
those cases and changed tool bytes. Empty directories are allowed and do
not increase the 13-file inventory. This repair changes the review tooling, not the frozen 13-file
plugin payload. The independent review also passed its then-current 25 tests, probed large
numeric and nested inputs, and compared 90 text boundary cases between the
schema and checker without finding a disagreement. The current author's
26-test run additionally covers an allowed empty directory that cannot
inflate the file count. Independent defect review does not admit the package.

The reviewer also demonstrated that the original hook could run an unrelated
interpreter supplied through PATH. The
[failed control](../../artifacts/harness-plugin-context-2026-09-23/evidence/hook-path-failure.json)
and [previous manifest](../../artifacts/harness-plugin-context-2026-09-23/evidence/second-candidate-manifest.json)
are preserved. The successor binds `/usr/bin/python3` in both the hook and
command definition and declares Linux as its deployment profile. The real
registered hook command now passes with a fake `python3` first on PATH. The
observed interpreter is Python 3.14.4. This binding does not establish
portability to another host or protect against the host replacing the
absolute interpreter. The host must control its launch environment and
qualify any differently rendered interpreter binding.

## Authority, placement and remaining admission work

The package remains under `artifacts/`, outside native autoload locations.
A future authorized binding must supply the plugin root explicitly. The
native hook configuration registers a local Python process, so approval to
load a plugin must cover that executable startup effect. The scripts read
package source and standard input, write standard output and error, and
make no network or model calls. The hook does not read transcript paths or
task files supplied in its input. The package mount must preserve the
reviewed bytes, including its adjacent helper, during execution.

The hook accepts startup, resume, clear and compact sources. The current
official source also describes fork; that source is intentionally outside
this candidate's declared profile. A three-second hook timeout is configured for a caller that never closes
input; native timeout enforcement remains untested. The explicit checker
also needs a host process timeout. Rejecting malformed hook input is a diagnostic, not a
permission or task-admission decision. The hook provides context only.

The agent definition requests an empty tool list, the caller's selected
model and at most two turns. Native discovery does not prove those runtime
restrictions; the next isolated session probe must verify them. The agent's
review is advisory. It cannot approve this package or accept its own work.
Model authority and budget remain with the caller.

Admission still needs independent review of exact bytes, rights and effects;
the remaining native event profiles and command execution record; a
known-wrong native loading case; and a task comparison that can reject a structurally valid but useless
brief. Other harnesses need their own versioned renderings and tests. One
Claude Code plugin is one logical package, even though several different
file types contribute to its behavior.
