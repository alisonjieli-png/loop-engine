# Folder depth and the flat core, measured on 2026-09-18

Kind: architecture record. It states what the tree looks like today, measured
rather than remembered, and proposes a migration in tranches. Nothing here is
implemented yet.

## What the tree looks like today

Measured on the working tree at commit `dfdab58`.

| Directory | Python files directly inside |
|---|---:|
| `src/loop_engine/core` | 354 |
| `src/loop_engine/code_nodes` | 60 |
| `src/loop_engine/loop` | 43 |
| `src/loop_engine` | 30 |
| `src/loop_engine/strings` | 15 |
| `src/loop_engine/generation` | 12 |
| `src/loop_engine/ontology` | 9 |
| `src/loop_engine/catalog` | 9 |

Depth of every Python file under `src`, counted as path segments: 30 files at
two segments, 510 at three, 39 at four. So the tree is two levels deep almost
everywhere, and more than half of the package sits in one directory.

The consequence is not stylistic. A reader looking for the code that spawns a
harness instance sees 354 names in one list. A change to one family cannot be
reviewed as a change to one folder. Ownership, import boundaries, and size
caps all have to be stated per file because the folder cannot state them.

## The grouping is already there in the names

The 354 files in `core` carry strong name families. The twelve largest:

| Family | Files |
|---|---:|
| `harness_` | 42 |
| `adaptive_` | 28 |
| `model_` | 22 |
| `stage_` | 14 |
| `independent_` | 11 |
| `opencode_` | 10 |
| `run_` | 9 |
| `workspace_` | 8 |
| `semantic_` | 8 |
| `task_` | 7 |
| `information_` | 7 |
| `external_` | 7 |

Those families are what a folder would be named. The classification exists
already, written into every file name, and the filesystem does not use it.

## Why this is not one change

Two things point at a module by name, and both have to move together.

1. Import statements. One family, `harness_`, is named by 128 import
   statements across 106 files.
2. Strings. The architecture map, the folded self-test list, the boundary
   registry, and several records name modules as text rather than as imports.
   The same family appears in 113 string references.

A missed string does not fail quietly: the conformance gate refuses a file it
cannot classify, and the self-test folds its modules by name. That is the
reason this can be done at all, and the reason it must be done a family at a
time with the whole gate chain between tranches.

## The proposal

Move one family per batch, largest first, into a subpackage of the folder it
already lives in. For the first tranche that means `core/harness_*.py` becomes
`core/harness/*.py`, with the family prefix dropped from the file name because
the folder now carries it.

Each tranche is one commit and runs the standing chain: the conformance gates
on an exported tree, the hardcoding delta, the documentation lint, the tools
tests, the full self-test, and the example battery, plus mutants for any
behavior that changed. A tranche that cannot pass is reverted whole rather
than patched forward.

Three rules hold across every tranche.

- The public import path does not change. Names exported from the package
  stay where callers find them today.
- No behavior changes in a move. A tranche that also fixes something is two
  changes wearing one commit message.
- The architecture map, the folded self-test list, and every string that names
  a module move in the same commit as the files, because a map that describes
  a tree that no longer exists is worse than a flat tree.

## What this does not change

Folder path, classification tree, and record file remain three different
things, as
[the repository layout record](REPOSITORY-LAYOUT-AND-RECORD-KINDS-2026-09-18.md)
states. Making the folder path mirror the classification tree inside `core`
removes a mismatch; it does not merge the two ideas. A record file still says
what it is in its own front matter, and a folder still says only where
something lives.
