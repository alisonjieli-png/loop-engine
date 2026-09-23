# Focused-step plugin candidate

One original harness-intelligence package with **no `SKILL.md`**. Its native
Claude Code layout carries a plugin manifest, a SessionStart hook, a command,
an agent, Python tools and JSON contracts. This package is candidate-only.
It has no independent approval, hosted release, production installation or
model-use evidence. The repository's MIT licence is included unchanged.

## Files and native behavior

```text
plugin/
├── .claude-plugin/plugin.json       native plugin identity
├── hooks/hooks.json                native SessionStart registration
├── commands/check-brief.md          native user-invoked command
├── agents/brief-reviewer.md         native advisory agent definition
├── scripts/
│   ├── session_start.py             hook entrypoint
│   ├── check_brief.py               explicit standard-input tool
│   └── protocol.py                  bounded JSON helper
├── contracts/
│   ├── brief-input.schema.json      tool input contract
│   ├── brief-output.schema.json     tool result contract
│   ├── hook-input.schema.json       accepted hook input subset
│   ├── hook-output.schema.json      produced hook output subset
│   └── example-brief.json           original example, no real user data
└── LICENSE                         repository MIT notice
```

The directory under `artifacts/` is not a native installation location.
An authorized caller can explicitly bind its `plugin/` folder using
`claude --plugin-dir <plugin-directory>`. That is a native development binding,
not a persistent install. The hook configuration then registers automatically;
the hook sends fixed guidance at supported SessionStart events. The command
is invoked as `/baltor-focused-brief-candidate:check-brief`, and the agent has
a native scoped name. The JSON contracts and tool source are package resources,
not independently auto-loaded context. The checker runs only when explicitly
invoked with a supplied brief. A source file's presence never establishes use.

[Official plugin layout and command discovery](https://code.claude.com/docs/en/plugins-reference)
and [local plugin binding](https://code.claude.com/docs/en/plugins) informed
this layout. The [hook reference](https://code.claude.com/docs/en/hooks)
defines SessionStart JSON. The
[subagent reference](https://code.claude.com/docs/en/sub-agents) informed the
advisory agent's fields. Claude Code 2.1.280 is the only client version
observed here. No cross-client compatibility is claimed.

## What the checker does

Pass one JSON document through standard input and close the input stream:

```bash
/usr/bin/python3 -I -B plugin/scripts/check_brief.py < plugin/contracts/example-brief.json
```

The checker verifies required fields, bounded text and lists, unique logical
labels and check identifiers, known effect names, and at least one declared
check for every output. It reports unanswered-question count and an exact
input digest without repeating the supplied text. A passing structure may
still contain a wrong goal or an inadequate acceptance criterion. The tool
always reports that semantic review remains required and grants no authority.
Requested effects and an authority reference are declarations only.

The hook accepts startup, resume, clear and compact events. Other events and
sources, including fork, are outside this candidate profile. Both entrypoints
bound input at 65,536 bytes and nesting at 16 levels; reject duplicate object
keys, malformed UTF-8 and nonstandard JSON constants; and emit bounded JSON.
The hook declares a three-second host timeout for a caller that never closes
input; enforcement in a native session remains untested. The checker likewise
requires a host-enforced process timeout. Both use
Python's isolated mode and disable bytecode writes. The bundled helper is
read by exact adjacent path, so the approved package mount must be immutable.

The hook never reads `cwd`, transcript or configuration paths from its input,
never echoes supplied metadata, and never scans the workspace. Invalid input
produces an empty output object, a fixed diagnostic and exit 1. This is a
context hook. It does not stop task execution or enforce access permissions.

## Authority and review

The host must explicitly authorize loading this plugin and running its hook
process with a trusted `/usr/bin/python3` on Linux, version 3.10 or newer. Even a small startup hook is executable
code. Its declared behavior reads its package source and standard input and
writes standard output and error; it makes no network, model or task-file
call. Do not give it unnecessary credentials. Native plugin permission and
sandbox controls still apply, and loading a plugin is not a grant for later
tool effects.

The `brief-reviewer` agent has an empty tool list, inherits the caller's model
and has two maximum turns. A model review requires separate model authority
and budget. The observed native inventory lists that agent, but runtime tool
restriction and actual review behavior have not been exercised. Its output
is advisory and cannot admit this package or accept a task result.

[Inventory and exact file digests](candidate-manifest.json) identify one
logical package and each physical file's role. Tests and evidence are review
materials, not additional packages. The admission process must separately
review the exact final bytes, rights, effects, loading and task outcomes.

## Qualification recorded

[Native manifest validation](evidence/native-validation-initial.json) passed
strictly in Claude Code 2.1.280. The malformed-name control was refused.
The CLI's directory-validation responses reported empty component lists;
individual hook and Markdown paths were interpreted as manifests and failed.
Those failed probes remain in
[initial component evidence](evidence/native-components-initial.json) and
[isolated discovery evidence](evidence/native-components-isolated.json).
They are not treated as successful hook or frontmatter validators.

In an isolated home outside the repository, `claude --plugin-dir ... plugin
details ...` actually listed one command as a skill, one agent and one
SessionStart hook. This establishes native discovery. A separate [independent review](INDEPENDENT-QA-2026-09-23.md) then ran
`--init-only` with this plugin in a disposable working directory, home and
configuration. Claude Code 2.1.280 executed the startup hook successfully
and accepted its 603-character additional context. No model request was
made. This establishes native startup hook execution and context acceptance;
it does not establish model use, command use or task benefit. The CLI's displayed
token counts are estimates; no provider usage was measured.

The [test report](evidence/final-checks-4.json) records deterministic tests and
a guard-removal control. Tests use `jsonschema` 4.26.0 as an independent
contract checker; the delivered tools use Python's standard library only.
Run the tests from this candidate root:

```bash
python3 -B -m unittest discover -s tests -v
```

## Reuse decision

The existing `core.plugin_bundles` boundary uses passive Loop Engine bundle
manifests and admitted skill references. It is not a Claude Code plugin
renderer, so this isolated candidate does not replace it or introduce a
second runtime. A future native layout adapter belongs at the existing
selected-material installation boundary, tracked by S-6.44.

The earlier JSON-shape protocol candidate supplied the duplicate-key and
nonstandard-number rejection design. No source body was copied. Its parser
was insufficient for this task's byte, nesting and output-coverage checks,
so this small standard-library implementation is original. The tests target
malformed inputs and inadequate contracts rather than source-code spelling.

Independent review found that the initial inventory builder omitted unexpected
FIFOs instead of refusing them. The [failed replay](evidence/manifest-fifo-failure.json)
and [old builder](evidence/initial-build-manifest.py.txt) are preserved. The
repaired builder rejects symlinks and special files;
new tests also reject changed tool bytes. The 13-file plugin payload and its
manifest digest did not change during this repair. This review is not admission.

The independent reviewer also demonstrated that a PATH-resolved interpreter
could run different code before reaching the hook. The
[failed PATH control](evidence/hook-path-failure.json) remains saved. The
Linux candidate now binds `/usr/bin/python3`, observed here as Python 3.14.4.
The exact registered hook command passes with a fake `python3` first on PATH.
This is a deployment binding, not universal portability or protection from a
compromised host replacing that interpreter. The host must also control the
launch environment and keep the reviewed package immutable.
