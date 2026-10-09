# Isolated constraint case files

`build_library_supply.py constraint-cases` creates test data for one declared
constraint at a time. It reads frozen `api_operation_contract_atom/v2`
candidates and leaves them unchanged. The output is ordinary
`library_supply_candidate/v1` material in the existing `json_schemas` line,
with its own `operation_constraint_cases` state scope. Nothing here admits
or publishes a package.

The current run plan is `api_constraint_case_plan/v2`. It binds an optional
case-job exclusion snapshot and the complete source population before selecting
an explicit parent range. An earlier plan keeps its bytes; start a new run
instead of rewriting it to match this version.

A case has a valid baseline, one field/value edit and one expected failure.
The generator requires exactly one matching error from
`jsonschema.Draft202012Validator`: validator name, schema path and instance
path must all agree. The shipped checker must report that same target and
constraint. A rejection for a different reason is not a passing case.

Generator 1.1.0 checks every distinct valid baseline supplied by the parent,
in digest order. A later example can expose an optional field missing from an
earlier example. Invalid examples cannot supply a case. The existing OpenAPI
fixture synthesizer was inspected; optional fields absent from every valid
example and unsupported conditional cases stay findings. Trying several
values or baselines can find one case, but does not create several case jobs. A job is the
parent schema's assertion identity, the exact constraint path and its value
(the missing property for a `required` constraint).

## Case groups and replay

```text
One parent contract's case group
├── exact unchanged contract.schema.json
├── baselines/<digest>.json
├── cases/<job-digest>.json, one minimal edit per constraint job
├── shared schema_check.py and constraint_case_runtime.py
├── shared SKILL.md for selecting and replaying the bound cases
├── constraint-group.json, exact parent and member bindings
└── shared instructions, tests and required licence/attribution files
```

The generator groups cases within their parent contract and caps each group
at 64 files, including support files. This is a grouping policy, not a claim
that the platform has a universal 64-file limit. Larger parent families split
in property/constraint order. Each group includes only the valid baseline
files its cases reference. Reordering or repeating the parent's examples
does not create new case jobs or change the selected case bytes. Identical schema, baseline, runner, guide and
licence bytes retain the same digest; the report counts those bytes once.

The shared skill explains when the cases apply and how to run the bundled
checks. It grants no API access and makes no current endpoint or live execution
claim. Its bytes are identical across groups and count as one distinct file.

Run `python constraint_case_runtime.py .` inside a downloaded group to replay
its cases with the shipped checker. If `jsonschema` is already installed,
add `--independent` to repeat the independent oracle check. The tool never
installs a dependency or follows an external schema reference. Tests exercise
the schema, not the actual API or its permissions.

For a small in-memory example from the repository:

```python
from supply_lines.constraint_case_construction import construct
from supply_lines.constraint_case_runtime import encode, replay

schema = {"type": "object", "properties": {"limit": {"type": "integer", "minimum": 1}},
          "required": ["limit"]}
raw = encode(schema)
cases, baselines, report = construct(raw, [{"limit": 5}])
case = next(row for row in cases if row["expected"]["validator"] == "minimum")
assert case["edit"] == {"op": "replace", "path": ["limit"], "value": 0}
assert replay(case, {"contract.schema.json": raw, **baselines}, independent=True)["isolated_violation"]
```

## Bounded generation

Use a clean committed checkout. Parent run folders must contain their frozen
`run.json` and complete candidate packages. The maximum parent count refuses
an oversized input population; it does not silently sample the first few.

```sh
PYTHONPATH=src:tools python tools/build_library_supply.py constraint-cases \
  --parent-run /home/username/baltor-private/contract-parents \
  --run-folder /home/username/baltor-private/constraint-cases \
  --maximum-contracts 217 --maximum-cases 2000 \
  --maximum-candidate-bytes 67108864 --batch-size 25 --maximum-seconds 60
```

Without `--authorize-output-writes`, this reads the input plan and writes
nothing. With that flag, one existing Starting Practitioner Loop owns a
bounded batch and its local checks. Individual case files are passive data.
Network and model calls remain absent. The calling supervisor must bound the
whole process: input inspection and final reconciliation sit outside the
between-parent time check.

Resume with the same source bytes, generator and whole-run ceilings. The
writer verifies recorded outputs and parent bytes before advancing its
chained cursor. A crash after writing files but before recording their event
can recover only by exact-byte agreement. A partial event, changed parent or
different plan refuses resume. Keep each report and failed attempt.

Version-2 event rows bind the exact version-1 retained record, its parent at
that plan position, case members, group package and candidate-record hashes,
and recomputed byte accounting. The last event has the same checks as every
other event; an unchanged retained hash cannot authorize changing its counts
or dropping its groups. Version-1 event journals are refused, not migrated.

Each retained parent record has a separate 4 MiB read/write bound, because it
can hold hundreds of diagnostic rows. Served schemas and individual case files
keep their existing smaller bounds. Retained bytes still count toward the
whole-run byte ceiling; the restart reader checks the file size before reading
and repeats strict JSON and structure validation. A changed generator binding
requires a fresh run, not a rewrite of an earlier campaign's journal.

Before writing, the runner checks the whole output tree for aliases and
special files, including staging and packages not named by the journal.
Complete package writes from an interrupted next event can be reconciled
only against the next parent. Unknown partial package contents require
explicit reconciliation. These checks assume exclusive filesystem ownership;
they are not a sandbox against a concurrent privileged writer changing paths.

Reports distinguish source contracts, attempted constraint jobs, probe
attempts, retained findings, case files, groups, placements and distinct
payload digests. Run records and diagnostics are not component files.

## Qualification and duplicate ownership

The existing qualification policy recognizes only the strict case-group
manifest. Its job key binds the exact parent contract and sorted case-job
set. A different group name or member order creates no new job. The population
pass also checks member-level overlap, even when two groups have different
membership. All other package identity rules remain unchanged.

For comparison with prior groups in another run, pass each exact candidate
folder using `qualify_generated_components.py qualify
--known-constraint-groups FOLDER`. The reader verifies and replays those
groups before their case jobs enter the duplicate comparison. This is a
caller-declared comparison corpus, not an automatic claim to have scanned
every served package. Global publication still needs the parent's complete
served/admitted comparison scope and exact digest reconciliation.

## Larger campaigns

`case-exclusions` verifies existing candidate bytes and replays their case
groups with the independent schema checker. It writes a frozen list of known
case jobs. This is a comparison artifact, not approval or proof of worldwide
originality. Keep its bytes unchanged while a campaign uses it.

```sh
PYTHONPATH=src:tools python tools/build_library_supply.py case-exclusions \
  --group-root /home/username/baltor-private/prior-cases/packages \
  --maximum-groups 5000 \
  --output /home/username/baltor-private/next-case-exclusions.json \
  --authorize-output-writes
```

`constraint-campaign` partitions each source population into sorted parent
ranges. Each batch runs through the existing Starting Practitioner Loop. The
campaign excludes known jobs before grouping and carries completed ranges into
the next exclusion snapshot. Shared runtime and licence files still count once
by digest. It does not add cohort file counts and call the sum unique files.

```sh
PYTHONPATH=src:tools python tools/build_library_supply.py constraint-campaign \
  --parent-run /home/username/baltor-private/contract-parents-a \
  --parent-run /home/username/baltor-private/contract-parents-b \
  --exclude-case-jobs /home/username/baltor-private/next-case-exclusions.json \
  --run-folder /home/username/baltor-private/case-campaign \
  --maximum-contracts 100000 --maximum-cases 1000000 \
  --maximum-candidate-bytes 6442450944 --maximum-invocations 2000 \
  --maximum-campaign-seconds 7200 --shard-size 500 \
  --batch-size 100 --maximum-seconds 30 --max-batches 1
```

This command previews the frozen source plan. Add `--authorize-output-writes`
to produce candidates from a clean committed checkout. `--max-batches` limits
one invocation; the case, byte, time and invocation ceilings cover the entire
campaign and cannot be raised on resume. A million is a ceiling here, not a
forecast. The source population determines the available jobs.

Repeat the same command after a clean partial batch. Changed sources, changed
exclusions, altered receipts and changed limits refuse continuation. An
unanswered dispatch requires inspection of its native child journal before
any retry. A failed child holds the campaign. Preserve its evidence and repair
the cause in a new run; do not remove the failed event.

The campaign checks its deadline and free-space floor between native batches.
Each native batch also has a POSIX wall timer, including its source and resume
checks, controlled by `--maximum-batch-wall-seconds`. An existing process timer
is never replaced. Initial campaign enumeration and final snapshot work remain
outside that batch timer. An operator requiring a hard deadline for the whole
process must provide an outer supervisor. Network,
model calls, source writes, admission and publication remain outside this
driver. Global payload accounting and qualification are separate final stages.

These generators were authored with OpenAI. The native review and admission
commands must use `--producer-family openai`; the case-group declaration
refuses an unrelated default family. No review or admission command runs as
part of generation. Independent review, sandbox evidence, rights and actual
customer benefit remain separate from a generated case passing its checks.
