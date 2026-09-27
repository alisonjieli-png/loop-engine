# Failure laboratory for served packages

A library file can pass every review and still fail in the harness that loads
it: a skill links a script it does not carry, two commands install the same
file, a hook runs nothing. This example holds one small package for each such
fault and runs the activation check that places a package into each
documented harness layout and verifies what the harness reads first. Each
fixture must be refused with exactly the codes it names, and each control
must activate.

## Why use a loop

A direct function is enough here, and the example uses one. The check is
deterministic: it parses files, places them in a temporary folder and compares
digests. It calls no model and starts no harness. The laboratory is the
reusable part: the same fixtures can test the review prechecks, a native
harness loader or a sandboxed trial later.

## Run settings

| Setting | Value |
|---|---|
| Loop role | None; a deterministic check run from a script |
| Run mode | Deterministic |
| Step profile | Not applicable |
| Intelligence layers | None searched |
| Runtime Memory | Not used |
| Run History | Not saved |

## Install

```bash
python -m pip install "https://github.com/alisonjieli-png/loop-engine/archive/refs/heads/main.zip"
```

This example reads `tools/check_package_activation.py`, so it needs a
repository checkout.

## Run it

```bash
python examples/31_failure_laboratory/run.py
```

No keys, network, ports or credentials are needed. The check writes only into
a temporary folder, which it removes.

## Expected result

One line per fixture, then a summary:

```text
pass  ambiguous-data              expected: frontmatter_ambiguous
pass  control-instructions        expected: activates
...
{"fixtures": 12, "passed": 12, "failed": []}
```

Model calls: none. External effects: none.

## The fixtures

| Fixture | What it breaks | Expected refusal codes |
|---|---|---|
| [control-skill](packages/control-skill/) | nothing | activates |
| [control-plugin](packages/control-plugin/) | nothing | activates |
| [control-instructions](packages/control-instructions/) | nothing | activates |
| [missing-dependency](packages/missing-dependency/) | the manifest names a subagent and a hook script the package lacks | `manifest_part_missing`, `hook_script_missing` |
| [same-path](packages/same-path/) | two packages install the same command file | `target_path_collision` |
| [incorrect-output-claim](packages/incorrect-output-claim/) | the record claims a size and a media type the bytes do not have | `file_claim_false`, `media_type_claim_false` |
| [hook-does-nothing](packages/hook-does-nothing/) | the only hook handler has an empty command | `hook_does_nothing` |
| [permissions-drift](packages/permissions-drift/) | the skill pre-approves tools beyond its declared effects | `authority_exceeds_declared_effects` |
| [source-injection](packages/source-injection/) | imports reach outside the project | `referenced_path_escapes` |
| [ambiguous-data](packages/ambiguous-data/) | the frontmatter names the skill twice | `frontmatter_ambiguous` |
| [interrupted-installation](packages/interrupted-installation/) | a script is missing and a partial copy is left | `file_missing`, `partial_file_present` |
| [loads-but-useless](packages/loads-but-useless/) | the body holds no instruction | `body_has_no_instructions` |

An instruction file is stored under another name, such as `agents-file.md`,
and its manifest gives the package path. A file named AGENTS.md or CLAUDE.md
in this folder would be read by a coding session that works in this
repository, so the check refuses a laboratory that holds one.

To check a release bundle instead of the laboratory:

```bash
PYTHONPATH=src:tools python tools/check_package_activation.py \
    --bundle PATH/TO/BUNDLE --output activation-report.json --compact
```

Add `--observe-listing` when OpenCode is installed. The check then runs
OpenCode's own skill listing, which starts no model turn, once in an empty
project and once in a project that holds only the placed skill folders, and
records for each skill package whether the loader reported it. The empty
project is the baseline: it explains the built-in skills and your own global
skills, so they are never counted as part of a package.

## Watch it live

This example has no live view; it finishes in a few seconds.

## Play it back

This example saves no Run History. The bundle form writes a
`package_activation_report/v1` record bound to the bundle digest.

## What this example does not prove

Activation facts show that a harness can find and read a package. They do not
show that the package helps: whether a model follows the instructions, or a
script produces the output it promises, needs a sandboxed task trial with a
baseline run that has no extra package. A frontmatter that only a forgiving
reader accepts stays unknown until each harness's own loader is observed. The
listing option observes one loader, OpenCode, for skills only; a listing
shows that the loader found a skill, not that a model used it.
