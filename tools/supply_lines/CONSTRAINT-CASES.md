# Isolated constraint case files

`build_library_supply.py constraint-cases` creates test data for one declared
constraint at a time. It reads frozen `api_operation_contract_atom/v2`
candidates and leaves them unchanged. The output is ordinary
`library_supply_candidate/v1` material in the existing `json_schemas` line,
with its own `operation_constraint_cases` state scope. Nothing here admits
or publishes a package.

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

These generators were authored with OpenAI. The native review and admission
commands must use `--producer-family openai`; the case-group declaration
refuses an unrelated default family. No review or admission command runs as
part of generation. Independent review, sandbox evidence, rights and actual
customer benefit remain separate from a generated case passing its checks.
