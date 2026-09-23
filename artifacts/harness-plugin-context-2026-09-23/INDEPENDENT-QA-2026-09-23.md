# Independent review of the focused-step plugin candidate

Date: September 23, 2026, United States Eastern time. The reviewer did not
author or edit the 13-file `plugin/` payload. This note is **not an approval,
admission or release decision**. It records deterministic and no-model native
observations for one candidate package at
[manifest SHA-256](candidate-manifest.json)
`fdfd23ea7ea160a66d5d3be7805261050595ea07597497b35c021da8a4ee68ff`.
The [package guide](README.md) states the intended behavior and limits.

```text
One candidate package
├── Native declarations: plugin identity, SessionStart hook, command, agent
├── Executable files: hook entrypoint, explicit checker, JSON helper
└── Resources: four contracts, an example and the MIT licence notice
```

## Saved wrong cases and successor replay

The initial candidate manifest had SHA-256
`7b9d52d01e0da5ac219d528850d86ca4024a6c35058e16790c0c49a789471321`.
It bound 13 regular files but its builder ignored a nonregular extra path. In
a disposable copy, `os.mkfifo(plugin/extra.pipe)` left
`build_manifest.py --check` at exit 0 with the same reported manifest digest.
The author retained the failed control and repaired the builder, which is
outside the payload. The independent replay against the successor made the
same FIFO fail at exit 1 with `candidate nonregular path refused`. Changed
payload bytes also fail the manifest check. The current manifest has one
logical package and 13 physical package files; tests and review notes are
outside those 13 files.

The initial registered hook used `python3` from inherited `PATH`. In a
disposable shell with a fake executable named `python3` first in `PATH`, the
exact hook command printed `path-hijacked` and did not run the reviewed hook
script. The successor [hook declaration](plugin/hooks/hooks.json) binds
`/usr/bin/python3` and declares a Linux host with a trusted immutable Python
3.10 or newer interpreter. The independent replay with the same poisoned
`PATH` returned the expected `SessionStart` JSON and did not execute the fake
file. This is a Linux deployment binding; it does not protect a compromised
host or an installation whose `CLAUDE_PLUGIN_ROOT` is untrusted. Other
platforms need their own reviewed interpreter binding.

## Current deterministic and native observations

- The independent run of `build_manifest.py --check` passed for the exact
  candidate payload. The independent run of the 25 then-current command tests
  passed. Those tests include malformed JSON, duplicate fields, nonstandard
  numbers, UTF-8 errors, nesting and byte ceilings, missing output checks,
  symlink and FIFO manifest controls, and poisoned `PATH`.
- An additional disposable input probe gave the checker a 65,016-byte extreme
  exponent, a 65,014-byte integer, an escaped-bracket string and a 17-level
  array. Each returned exit 1 with bounded JSON, no traceback, and no supplied
  text in standard error. The first returned `invalid_json`; the array
  returned `nesting_too_deep`.
- A schema comparison over 18 text boundary cases each for `objective`,
  `authority_reference`, `constraints`, `out_of_scope` and
  `unresolved_questions` found no acceptance disagreement between the Python
  checker and its JSON input schema. This is a bounded probe, not a proof of
  schema equivalence.
- In a disposable working folder, home and Claude configuration directory,
  `claude --plugin-dir <plugin> plugin details
  baltor-focused-brief-candidate@inline` on Claude Code 2.1.280 exited 0 and
  listed one command, one agent and one SessionStart hook. No credentials or
  model prompt were supplied.
- In another disposable folder, the documented no-model
  `claude --plugin-dir <plugin> --debug-file <temporary-log> --init-only`
  exited 0. The debug log recorded `Hook SessionStart:startup ... success` and
  said the exact `/usr/bin/python3 -I -B
  "${CLAUDE_PLUGIN_ROOT}/scripts/session_start.py"` command provided
  `additionalContext (603 chars)`. This independently establishes startup
  hook execution and host acceptance of its context for this client and host.
  It does not establish that a model used the context or that a task improved.

The [official hook reference](https://code.claude.com/docs/en/hooks) says a
SessionStart command hook can supply `hookSpecificOutput.additionalContext`,
and `--init-only` runs startup hooks without opening a conversation. The
[plugin reference](https://code.claude.com/docs/en/plugins-reference) describes
native command and agent discovery. These sources support the observed native
path, but the exact client result above remains scoped to Claude Code 2.1.280.

## Outstanding admission evidence

The SessionStart hook accepts startup, resume, clear and compact sources.
Forked sessions are outside this candidate profile. The command has been
discovered, but its model-mediated instructions have not been invoked through
Claude Code on a supplied brief. The agent has been discovered, but its
`tools: []` restriction, two-turn limit, model budget and semantic review have
not been exercised. The checker still needs the host to close standard input
and impose a process timeout. The selected package must be mounted immutably
and invoked with the declared Linux interpreter and scoped environment.

The checker reports structure and named output-check coverage. It does not
verify the task goal, the quality of an assertion, a claimed authority
reference, the safety of requested effects or a completed task. A model review
of a brief needs separate authority, privacy handling and an independent
evaluator. No hosted customer fetched, loaded or used this candidate, and no
customer outcome or benefit is measured. The producer cannot approve its own
exact bytes; a separate admission decision remains necessary.
