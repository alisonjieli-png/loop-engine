# Seeded intelligence from occupations

Loop Engine can turn an occupation, a job title with its responsibilities,
into candidate intelligence: questions a careful worker asks about each
task, facts about the occupation, and specifications for code that could
check or correct the work. Everything it produces is a candidate. Nothing
becomes active until the admission ladder qualifies it in a separate
process.

```text
Seeded generation
├── Source
│   ├── the packaged occupation seeds (six hand-authored occupations)
│   ├── an O*NET occupation table and task table, read through the packaged mapping
│   └── an ESCO occupation table, read through the packaged mapping
├── Occupation record
│   └── code, title, description, task statements, domain, source, license, version
├── Seed batch
│   ├── question seeds: six general forms applied to every task
│   ├── fact seeds: has_task, in_domain, titled
│   └── code seeds: a specification with no implementation, only for a whole-word verb match
└── Staging
    └── through a store contract, as candidates, never a file
```

## Generate seeds from the packaged occupations

```python
from loop_engine.core.seeded_generation import packaged_seed_batches

for batch in packaged_seed_batches():
    print(batch.job_position, batch.counts)
```

Each batch names its occupation code and digest, its job position, its
domain, the generator version, and its seeds. The same occupation and the
same version give the same digests every time.

## Read a public occupation table

The O*NET database publishes an occupation file and a task statements file
as tab-separated text. The column names are packaged as a mapping, so the
files are read without any code that knows O*NET:

```python
from loop_engine.core.seeded_generation import (
    DelimitedSources, ONET_MAPPING, generate_seeds, read_delimited)

mapping = ONET_MAPPING.with_version("31.0")
table = read_delimited(DelimitedSources("Occupation Data.txt", "Task Statements.txt"), mapping)
batches = [generate_seeds(occupation) for occupation in table.occupations]
```

A mapping whose column is absent from the file is refused with the column
named. ESCO has no task file in the same shape, so its packaged mapping
reads the description column as the single task; the ESCO reuse terms
should be confirmed before any ESCO-derived seed is redistributed.

## Stage the seeds

```python
from loop_engine.core.seeded_generation import stage_seeds

report = stage_seeds(batch, store, namespace="seeds")
print(report.counts, report.total)
```

The store is a catalog store (any adapter behind the catalog contract) or
the search and serve store the intelligence layers read. Staging writes one
record per seed with the lifecycle candidate and returns a report that
counts only the writes the store acknowledged. On the search and serve
store the records enter the experimental tier, so they stay out of search
until a caller enables that tier. No file is written by this step; the
conformance gate `direct_writes_to_intelligence_files_outside_adapters`
refuses any module that tries.

## What a candidate can and cannot do

- A seed can be searched when a caller includes candidates, reviewed, and
  proposed to the admission ladder in `core/reusable_capability_flywheel`.
- A seed cannot run, cannot be served as a registered form, and cannot be
  promoted by this module; the module has no promote or qualify function,
  and its checks fail when any seed leaves the candidate state.
- A code seed is a specification: an operation kind from the declared
  verb table, a purpose, an input and output sketch, and the tests to
  write. Implementing it is a Practitioner task under the usual authority.

## Limits on 2026-09-18

The six packaged occupations are authored from general knowledge of the
roles, not from O*NET text. The question forms are six general forms; a
model-authored form enters through the question engine with its own
provenance. No live run has consumed a seed yet, so nothing here is a
claim about how useful the seeds are; that is measured when a seed is
cited by a verified outcome and reuse evidence records it.
