# Checks and evidence

Kind: engineering standard. The working cycle that this standard follows is
recorded in the
[takeover checkpoint](../context/TAKEOVER-CHECKPOINT-2026-09-20.md#working-cycle).
A passing count is not a working customer journey. Offered, fetched, loaded,
used and verified are separate facts.

## The order of work

```text
Proving one change
├── 1. Write the check for the known-wrong case first
├── 2. See it fail, then make the repair
├── 3. Prove with a mutant that a named check fails without the guard
├── 4. Run the smallest owning check, then the owning suite, then the gates
├── 5. Save each report under a new name and keep failed attempts
└── 6. State observed, inferred, missing and disputed facts separately
```

## Known-wrong first

Start from the input or state that must be refused, and write the check that
expects the refusal. Give it a name that is a sentence
([naming rule](NAMES-AND-NOMENCLATURE.md#check-names-written-as-sentences)).

A check in this repository is a function call with a name and a Boolean:
`check("name_written_as_a_sentence", condition)`. A suite collects the rows
and returns `tests`, `passed`, `total` and `all_passed`. See `run_all_checks`
in [access_checks.py](../../src/loop_engine/core/service_runtime/access_checks.py).
A checks module sits beside its subject and the package self-test runs it.

Compare the stable error code, never the message text. The helper `refused`
in `access_checks.py` does this.

## Mutant proof

A check that cannot fail proves nothing. For each new guard, remove the guard
inside the check run and assert that a named check notices.

The model is `version_checks` in `access_checks.py`. It patches
`OWNER_BOUND_KEY_SCHEMA` back to the first key version, issues a key, and the
check `removed_key_version_change_is_detected` asserts that the mutant key is
not stored under the owner-bound version and is refused. The patch lives only
inside the `with patch(...)` block. The source is never edited.

Rules:

- The mutant control has its own sentence name and is reported like any check.
- Never weaken or delete an existing check to make a change pass. First
  decide whether the work, the check or the environment is wrong, and record
  why. A revised check must still refuse a known-wrong answer.
- The checkpoint records two controls that had silently stopped failing.
  Rerun the mutant when you move a guard.

## Reports under new names, failed attempts kept

- A report file ends in a rising number: `rollback-key-version-1.json`,
  `account-website-browser-1.json` and `account-website-browser-2.json` in
  `artifacts/architecture-audit-2026-09-19/`.
- A tool refuses to overwrite. `check_rollback_key_version.py` opens its
  output with mode `x`. `check_service_workspace.mjs` stops with "Refusing to
  overwrite an existing browser evidence artifact".
- Keep a failed attempt beside its successor, for example
  `conformance-attempt-1.json`. Do not edit a saved report, a baseline or a
  historical record to make a gate pass.
- A report states its own limits. The rollback drill records
  `"container_network": "none"`, `"provider_requests": 0` and a `limitations`
  list.
- No report, log or check output may contain a credential value.

## What each gate covers

Run from the repository root with the project interpreter. In a worktree,
first confirm that `loop_engine.__file__` resolves inside that worktree.

| Gate | Command | Covers | Does not cover |
|---|---|---|---|
| Service smoke | `PYTHONPATH=src .venv/bin/python -m loop_engine service smoke` | The hosted service domain and HTTP adapter against local fixtures. | A deployed host or a real provider. |
| Conformance | `PYTHONPATH=src .venv/bin/python -m loop_engine --conformance` | Thirty zero-tolerance gates: file classification, a README with a kind in every `docs/` folder, network and subprocess imports outside registered modules, secret-shaped literals, module size, the one Loop runtime type, map freshness. The list is `zero_tolerance_gates` in `src/loop_engine/architecture_conformance.json`. | Behavior. It scans structure. |
| Self-test | `PYTHONPATH=src .venv/bin/python -m loop_engine --self-test` | Every packaged checks module. | Live model quality. |
| Tool tests | `PYTHONPATH=src:tools .venv/bin/python -m unittest discover -s tools -p 'test_*.py'` | Development commands and generated reports. | `tools/test_overnight.py` can wait on an external binary. Run your own test modules directly if it hangs. |
| Embodiment suite | `PYTHONPATH=src:devtools .venv/bin/python -m unittest discover -s devtools/embodiment_lab/tests` | Experimental embodiments, and links that the route documents must keep. | |
| Hardcoding audit | `PYTHONPATH=devtools/src .venv/bin/python -m loop_engine_devtools.cli --hardcoding-audit --allowlist devtools/hardcoding-allowlist.yaml --baseline devtools/hardcoding-ci-baseline.json --fail-on-new high` | Literals in source that were not reviewed, compared with a baseline. It fails on a new finding of high severity. Add `--triage PATH.yaml` for a worklist ([devtools README](../../devtools/README.md#self-orientation-and-abstraction-audit)). | Findings already in the baseline. |
| Roadmap status | `PYTHONPATH=src:tools .venv/bin/python tools/build_continuation_status.py --check` | The generated status matches `roadmap.yaml`. | |
| Rollback drill | `.venv/bin/python tools/check_rollback_key_version.py --older-image IMAGE --output NEW_REPORT_PATH` | An older image refuses records it must not honor. | The deployed volume. |
| Browser checks | `node tools/check_service_workspace.mjs NEW_REPORT_PATH` | The website in a real browser against a local service. | Live hostnames. `tools/check_hosted_website.mjs` reads those. |

For documents, the `docs` job of
[ci.yml](../../.github/workflows/ci.yml) runs four gates over prose. Each one
lints a fixed set of paths, not the paths you touched. A local run over your
own files does not predict the gate, so run the declared set before you
commit. The set is `AGENTS.md README.md CHANGELOG.md CONTRIBUTING.md
SECURITY.md humanizer-context.md showcase/README.md 'docs/**/*.md'
'case-studies/*.md' 'examples/**/*.md'`.

| Gate | Command or action | Scope |
|---|---|---|
| Markdown structure | `npx --yes markdownlint-cli2@0.23.2 DECLARED_SET` | The declared set above. |
| Public language | vale 3.18.0 with `.vale.ini`, run by `vale-cli/vale-action@v3` with `sync: false` | `AGENTS.md`, `README.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`, `humanizer-context.md`, `showcase/README.md`, and the `docs`, `case-studies` and `examples` folders. |
| Refuse retired public language | Two `rg` searches, case insensitive | `README.md`, `CHANGELOG.md`, `humanizer-context.md`, `docs`, `examples`, `case-studies`, `showcase`, and `benchmarks` for the first search. |
| Local links and section anchors | `lycheeverse/lychee-action@v2` with `--offline --include-fragments --root-dir` | The declared set above. A renamed heading breaks every link to it. |

The third gate is worth reading before you write. Its first search refuses the
two retired evidence words that this repository replaced with Run History,
event log, record, report and evidence, in the singular and the plural. Its
second search refuses the two retired topology words, the one for a Spawned
Loop and the one for a Starting Loop, and a family of four retired decision
phrases built from the words for "what" and "next", which the repository
replaced with "select next action". That decision family is refused here and
nowhere else: the three rules in `.vale/styles/LoopEngine` do not carry it, so
a developer who reads only the vale folder will be blocked by a gate they
never saw. Both searches ignore case and exempt `docs/prompts`,
`docs/evidence` and `docs/verification`, because those are dated evidence and
a report whose finding is that a retired term was used has to quote it.

Read the two regular expressions in the `Refuse retired public language` step
of `ci.yml`. No document under `docs/` can quote the refused words, because
the gate would then refuse that document.

The same job also validates the benchmark registry and renders the Mermaid
diagrams. Those cover data files and diagrams rather than prose. After you add
a document under `docs/`, run
`PYTHONPATH=src:tools .venv/bin/python tools/build_records_index.py` and commit
`docs/RECORDS-INDEX.md`.

## Continuous integration traps

These are recorded in the takeover checkpoint and in the history of the
repairs that followed it.

| Trap | What to do |
|---|---|
| The conformance and self-test commands rewrite `src/loop_engine/architecture_conformance.json` and one context manifest. | Commit the rewritten files with the change that caused them. The rewrite is identical when nothing changed. |
| A new file with unregistered literals fails the hardcoding gate. The checkpoint records 120 such findings. | Run the audit before you commit. Repair the literal in source where you can. An allowlist entry is exact and carries a truthful reason. |
| A checks file that imports `urllib`, `http`, `httpx`, `requests`, `socket` or `aiohttp` fails conformance unless that exact file is listed in `network_allowed_modules` of `src/loop_engine/forbidden_paths.json`. | Use the existing fixtures. Register a file only when it truly owns a network boundary. A registration that grants nothing is removed. |
| A check passed on the workstation and failed on a clean machine. The first continuous integration run after the takeover failed in a different step on each Python version. | Do not rely on a package that arrives only as a dependency of another package. Install it by exact version. Continuous integration runs Python 3.10, 3.11 and 3.12. |
| A check that waits a fixed number of milliseconds fails on a slow machine. | Retry the same request identity while the answer is busy, as the interface documents. Keep the assertions unchanged. |
| Two self-test checks need name resolution for `example.com`. | This is an open finding. Expect it without a network. |
| Releases one to seven were built from an uncommitted working tree. | Release only from a committed revision whose continuous integration run passed. The workflow `fly-pilot.yml` requires a successful run for the exact revision and deploys by image digest. |

## Evidence language

- A stub or an injected transport tests a local contract. It does not prove
  provider integration or model quality.
- Missing usage and cost stay unknown. They are never zero.
- Report the exact denominator. Show failures with the same prominence as
  successes.
- A check that you did not run is not passed. Say so.
