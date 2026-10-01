# Read selected native package files in Baltor Harness

`loop-engine solve` can read a completed first-party client fetch without
copying the component's text into the task instruction. Pass its staging
folder with `--material-package`. Repeat the option for another package.
Keep the solve workspace separate and empty.

The usual model authorization is still required. For example, after the
client has fetched a selected package into `selected-reference`:

```sh
loop-engine solve --file task.md \
  --material-package selected-reference \
  --allow-source-to-model --ollama-api-key --model-route cloud.default \
  --max-model-calls 30 --workspace task-output
```

The download remains a separate authenticated operation. This option performs
no search or network request, creates no install folder and starts no package
script. The existing solver controls model calls and any later execution.

## Exact files, selected when needed

The [intake adapter](../../src/loop_engine/core/task_material_packages.py)
reads the current first-party fetch record, its served body and every declared
payload. It accepts complete package metadata in the current version only.
The existing `CataloguePackage` contract checks native relative paths, sizes,
media types and file roles. Single-file and multi-file packages are supported.
Unknown files beside the declared payload are ignored.

The adapter captures `task_material_package/v1` with the selected digest,
transfer-record digest and complete file bindings. Every later inspection,
profile or project-input read rechecks the selected file's bytes. Linked path
components, traversal, missing files and changed bytes refuse. The adapter
requires POSIX descriptor-relative file operations; there is no weaker path
fallback.

The model first sees package identities, digests and native source paths.
`core.source.inspect` returns a manifest before selected contents. Its paths
look like `components/<selection-digest>/references/table.json`; each result
also retains the original package member path. A selected file reaches a
generated project at `inputs/<source-path>`, unchanged. Binary assets may be
selected as project inputs but are never decoded into model text.

Only explicitly selected component text is sampled by automatic source-role
orientation. Unselected scripts, instruction files and references do not
enter prompts merely because another package file was inspected. A solve may
ignore optional component packages entirely. Ordinary task data keeps its
existing source-selection requirements.

Selections are limited to 32 packages, 512 declared files and 32 MiB of
payload in total. Catalogue file limits also apply. A caller may give the
intake adapter smaller byte and file allowances. These bound the selected
payload, not cumulative I/O, model context or execution budgets. Revalidation
reads a selected file again. The source owner keeps its existing
secret-content and hidden-path exclusions.

## Authority and qualification

`SKILL.md`, `AGENTS.md`, rules, code and references are advisory source files
on this path. Their filenames and declared roles do not register a skill,
override task instructions, widen permissions or approve execution. A local
transfer record is provenance supplied by the caller, not independent proof
of service access or content admission. It cannot create `SkillAdmissionRecord`.

The package layout survives as files; active skill loading and native tool
registration remain separate. Downloaded scripts are not imported or run.
The solver's existing generated-project execution still requires its own
authority, sandbox checks and output verification. This input option is the
first native-file step, not complete harness parity.

[`test_task_material_packages.py`](../../tools/test_task_material_packages.py)
checks the adapter, source inspection, profiling and generated-project input
path. Offline scripted gateway responses drive two public solve runs. The
existing executor runs a small authored Python calculation using selected
native data and produces `49` and `98` for two revisions. Those checks use
explicit host-execution authority with Docker unavailable; the host process
is not an operating-system sandbox. No downloaded code, provider, model
purchase or network request is used. This qualifies the mechanism, not model
selection quality or field benefit.

## Next project-selection boundary

Automatic discovery should consume one explicitly enabled project selection
manifest that names exact package bindings. It should not recursively import
ambient project files. That manifest can feed the same intake adapter and
source owner; it needs no new catalogue or store. Validation must finish
before the selected step receives any file, and changes require a new exact
selection.

Active skills should use the existing `SkillRegistry` and
`SkillAdmissionRecord`, with an exact skill id, version and manifest digest.
The fetch record's catalogue identity is not that skill manifest digest.
Strict front matter, support files and independent admission must agree
before `load_instructions(..., purpose=TASK_USE)` runs. A descriptor match or
Public Good tag cannot substitute for those records. Unsupported instruction
or tool formats stay passive sources until their existing native owner has
a qualified adapter. The no-extra-material baseline remains eligible.

Rollback removes the optional flag and its supplied bindings. This path
changes no catalogue, account, project install or skill registry state.
