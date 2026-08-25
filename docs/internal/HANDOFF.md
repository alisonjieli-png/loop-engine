# Loop Engine maintainer handoff

## Canonical source

This repository is the source of truth:

`https://github.com/alisonjieli-png/loop-engine`

There is no projection or synchronization script. Edit and test this tree
directly.

## Public names

| Surface | Name |
|---|---|
| Product | Loop Engine |
| Repository | `loop-engine` |
| Python distribution | `loop-engine` |
| Python import | `loop_engine` |
| Command-line program | `loop-engine` |

The old package and repository names have no compatibility aliases.

## Install and verify

From any directory:

```bash
python -m pip install "git+https://github.com/alisonjieli-png/loop-engine.git"
python -m loop_engine --self-test
python -m loop_engine --conformance
python -m loop_engine --map
```

The install command includes the runtime and every supported adapter. Do not
add task-specific installation variants.

## Repository rules

- Keep one recursive loop runtime.
- A loop can run deterministic, hybrid, or non-deterministic steps.
- Child loops cannot exceed the permissions of their parent.
- Missing dependencies, providers, measurements, and saved runs remain visible.
- Run the full test and conformance commands before release.
- Keep package metadata, documentation, examples, and CI on the same names.

## Historical material

The retired repository history and its integrity-bearing evidence were saved
before this repository was created. Do not reconstruct old records under the
new name. New evidence must describe work that actually ran as Loop Engine.
