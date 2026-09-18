# Text conformance and standalone solution export

This guide explains two capabilities that landed together on 2026-09-18:
deterministic text conformance with a confidence per correction, and the
export of a solution as a package that runs without Loop Engine.

The worked example is a company file with names, phones, emails, and
websites in poor shape: all-capital names, names with lowercase particles,
abbreviations, legal suffixes written six ways, extra spaces, and non-ASCII
letters. The same machinery applies to any text column.

## The two spaces

```text
Solutioning space (reasons, proposes, escalates)
├── profile every column: case, whitespace, encoding, shape, and suffix shares
├── propose typed conformance rules from that evidence
├── run the rules with a confidence and named reasons per correction
├── learn casings the column itself proves
└── stage low-confidence cells as typed escalation requests

Solutions space (executes, no reasoning)
├── the chosen rules, the merged catalogs, and the operations module
├── an installable package with a console entry point and tests
├── a manifest with a SHA-256 digest for every file
├── a Dockerfile and a Kubernetes Job manifest
└── verification in an interpreter that cannot import loop_engine
```

The solutioning side lives in `loop_engine.code_nodes.text_conformance`.
The operations live in `loop_engine.code_nodes.text_conformance_operations`,
which imports only the standard library so the export can ship it verbatim.
The export lives in `loop_engine.code_nodes.solution_export`.

## Operations

| Operation | What it does | Typical confidence |
|---|---|---|
| `whitespace_normalize` | Trims, replaces nonstandard spaces, collapses runs. | 0.99, lossless |
| `unicode_normalize` | NFC composition, zero-width removal, quote straightening; folding to ASCII only when asked. | 0.95 to 0.99; folding 0.5 when held, 0.9 when chosen |
| `case_normalize` | Title case with catalog and evidence exceptions; keeps deliberate capitals in mixed-case input. | 0.92 for all-capital input, lower per ambiguity |
| `suffix_canonicalize` | Canonical legal suffixes (Inc, Corp, LLC, GmbH) and the comma before them. | 0.97; ambiguous suffixes carry their catalog confidence |
| `phone_normalize` | Digits to an international form when the digit count is explainable. | 0.93 to 0.95; unexplained counts 0.35 |
| `email_normalize` | Strips wrappers, lowercases, checks the shape. | 0.97; invalid shapes 0.3 |
| `website_normalize` | Scheme, host case, optional www and trailing slash. | 0.9 to 0.95; invalid hosts 0.3 |

Every correction carries the reasons that produced its confidence, for
example `case_information_absent`, `surname_exception:LaPointe`,
`short_token_kept_upper_unverified`, or `ambiguous_suffix:spa`. The
confidence is the weakest named signal, with a small penalty per additional
ambiguous token. It is not a guess and it is not learned yet.

## Outcomes and thresholds

A policy declares two thresholds. A changed value at or above
`apply_at_or_above` is applied. A value below `escalate_below` is escalated.
Anything between is held: the candidate is recorded, the input is kept, and a
reviewer or a cheaper judgment can batch-approve it. `escalate_held` sends
held corrections to escalation as well.

An escalation request carries the candidates with their confidences, the
reasons, the ordered targets (model judgment, browser research, human
review), the `disambiguate_value` question form, and the registered response
contract `text_conformance.escalation_response`, whose suggested output is a
ranked list of at most three candidates with a unit-interval confidence and
an allowed abstention. The request performs no call. A hybrid Loop dispatches
it under its own authority, and only the low-confidence rows reach a model.
Each escalation also carries an implementation decision record: the
deterministic resolver reached a confidence below the threshold, so a
service model is the next implementation, with both candidates and the
reason recorded for later learning.

## Where an exception can live

```text
Exception catalog layers, lowest precedence first
├── packaged: loop_engine/data/text_conformance_catalogs.yaml
├── task_folder: a YAML or JSON catalog supplied with the task
├── column_evidence: casings the column proves through its mixed-case values
├── inline: parameters on one rule
└── escalation_answers: recorded answers from a model, research, or a person
```

A later layer overrides a mapping entry and extends a list. The packaged
file holds general conventions: null sentinels, preserved abbreviations,
minor words, lowercase particles, internal-capital prefixes with their
confidence (Mc 0.97, Fitz 0.9, Mac 0.8), apostrophe prefixes, surname
exceptions, legal suffixes with their canonical forms, ambiguous suffixes
with their confidence, long forms, and an ASCII folding map. The confidence
parameters for all-capital input, particles, and short tokens are values in
that file, so a task folder can raise or lower them for a dataset whose
conventions are known.

Column evidence is learned in a first pass: only values that carry case
information vote, and a token whose dominant form reaches eighty percent of
at least two votes becomes evidence. An all-capital row then inherits the
casing its neighbors show. The learned layer is recorded with its digest so
the provenance of every correction stays traceable.

Escalation answers are the fifth layer by design. When a model, a research
step, or a person answers an escalation, the answer is evidence with
provenance and can be staged as a candidate catalog entry for review. That
staging is not automated yet; the layer exists so nothing is written into
the packaged file by a run.

## Rule proposal

`propose_rules` reads the column profiles and returns rules with the evidence
that proposed each one: whitespace and Unicode first, then email, website,
or phone rules for columns whose values look like those kinds, then case and
suffix rules for columns with all-capital values or with lowercase values
next to mixed-case ones. Proposals are candidates for the solutioning space
to keep, change, or drop. The `validate` endpoint of the `text_conformance`
capability surface returns the profiles, the proposals, and the equivalent
DuckDB query for each column without changing any data. The surface is a
typed `SurfaceRegistration` that the conformance module owns; pass
`text_conformance_surface()` to `default_directory(surfaces=...)` to register
it. The registration lives on the code intelligence side so that core never
imports the package that owns the surface, which keeps the dependency
direction ratchet honest.

## The resolver

`TextConformanceResolver` is a `DeterministicTaskResolver`. It supports only
a task whose text is a `text_conformance_task/v1` record; it never infers
support from prose. It reads rows inline or a CSV file inside the workspace
root, refuses a path that escapes the root, and refuses a file above
`max_rows` with a message that names the standalone export for large files.
Its result is verified only when the report is complete: nothing held,
nothing escalated, and a second pass that changes nothing. Otherwise the
typed escalations are the next action for a hybrid Loop.

## The export

An export specification names the package, version, summary, files, console
script, dependencies, tests, container settings, and isolation mode. The
export writes `pyproject.toml`, `README.md`, `MANIFEST.json`, `Dockerfile`,
`k8s/job.yaml`, the sources under `src/<package>/`, and the tests. It refuses
a non-empty target, a path with traversal, an absolute path, a file that
imports `loop_engine`, and secret-shaped text.

Verification runs in an isolated interpreter (`python -I -S` for
standard-library exports) with only the export's `src` on the path. It checks
that the manifest digests match the files, that no file imports
`loop_engine`, that the package imports with `loop_engine` absent from the
loaded modules, that the exported tests pass, and, when arguments are given,
that the entry point runs and produces every expected artifact.

```bash
loop-engine export solution spec.json --out DIR
loop-engine export verify DIR --run-arguments '["--input","input.csv","--output-dir","out"]'
```

A specification with `"kind": "text_conformance"` builds the conformance
solution from rules, a policy, and catalog files. The exported entry point
streams a CSV file and writes `conformed.csv`, `corrections.jsonl`,
`escalations.jsonl`, and `report.json`. The Dockerfile says when its base
image is not digest-pinned. The Job manifest carries the solution reference
as a label, resource requests and limits, no retries, and an empty work
volume; replace `IMAGE_REFERENCE` with the built image.

## Large files

The in-process resolver refuses files above its declared row limit. For a
file with millions of rows, export the solution and run it where the data
is: the exported entry point streams rows and keeps only the column evidence
in memory. The DuckDB queries from the `validate` endpoint profile such a
file before rules are chosen; DuckDB is an optional dependency and the pure
Python profiler remains available.

## Current limits

- Confidence values are declared signals, not learned calibrations. A
  calibration from reviewed corrections is future work and needs enough
  recorded outcomes first.
- Escalation answers are not yet staged automatically as catalog candidates.
- Phone normalization uses a declared default country code and national
  length; it is not a full numbering-plan library.
- ASCII folding is lossy and stays off unless a rule asks for it.

## Duplicate detection

The second detection and correction family finds fuzzy duplicates over
names, addresses, emails, and phones. It keys each field with the same
catalogs text conformance uses (legal suffixes, email shape) and a declared
table of address abbreviations, compares rows only inside blocks formed by
declared blocking keys, and gives every compared pair named signals per
field and a confidence that is the weakest named signal.

```python
from loop_engine.code_nodes.duplicate_detection import (
    DuplicateFieldSpec, DuplicatePolicy, dedupe, find_duplicates, summarize)
from loop_engine.code_nodes.text_conformance import load_packaged_catalogs, merge_layers

catalogs = merge_layers((load_packaged_catalogs(),))
fields = DuplicateFieldSpec(name="company", address="address", email="email", phone="phone", identity="id")
report = find_duplicates(rows, fields, DuplicatePolicy(), catalogs=catalogs)
print(summarize(report))
proposal = dedupe(rows, report, strategy="keep_first")
```

What the report guarantees:

- A pair is a duplicate only when every compared field agrees strongly; a
  shared email with a different name is a possible pair for review, never
  a merge, because the confidence is the weakest named signal.
- Clusters follow duplicate decisions only, and a dedupe is a proposal that
  names the survivor and the merged identities; no row is deleted.
- A block above the declared size ceiling is recorded as skipped, so a
  report never claims to have compared what it did not.
- Possible pairs can be sent to a judge behind the model call boundary as
  typed decisions (`decide_possible_pairs`), with the answers recorded as
  decisions and call records, not applied as merges.

## Email recovery and malformed field detection

Two more members of the family live in `code_nodes/field_recovery.py`.

```python
from loop_engine.code_nodes.field_recovery import detect_malformed, recover_column, recover_email

recover_email("John.Smith at Example dot com")   # john.smith@example.com, applied
recover_email("maria@gmail.co")                  # gmail.com suggested, held for review
recover_email("ana@example.com; bo@example.com") # unchanged, escalated
report = recover_column(column_values)           # exact counts per outcome
flags = detect_malformed(["2026-09-18", "2026-09-19", "18/09/2026"])
```

Email recovery repairs spelled-out separators, punctuation slips around the
separator and the dots, and typed domains from declared tables that a
caller can replace with `RecoveryTables`. Every correction names its
reasons and carries the weakest named confidence, so the same apply, hold,
and escalate bands as text conformance decide what happens: a plausible
typo that is also a real domain is held, and an ambiguous or unrecoverable
address is escalated and left unchanged. Malformed field detection induces
the character pattern of every value, finds the column's dominant pattern,
and flags the values that differ with a confidence equal to the share
margin; when no pattern reaches the declared dominant share it flags
nothing and says so.

## Database copy with corrections and a dedupe proposal

```python
from loop_engine.code_nodes.database_copy import ColumnCorrection, TableLocation, copy_table
from loop_engine.code_nodes.field_recovery import recover_email

manifest = copy_table(
    TableLocation("contacts.csv"), TableLocation("clean.sqlite", "contacts_clean"),
    corrections=(ColumnCorrection("email", recover_email),),
    proposal=proposal, identity_column="id")
```

The copy writes a new delimited file or a new SQLite table and refuses a
target that exists or that is the source. Only a correction in the applied
band changes a value; held and escalated values are copied unchanged and
counted per column so a reviewer sees what was left alone. A dedupe
proposal drops the merged identities and keeps the survivors. The manifest
carries the source digest before and after the copy (they must match), the
target digest, and the rows in, out, and dropped.

## Address component extraction

```python
from loop_engine.code_nodes.address_components import extract_components

parts = extract_components("12 N Main St Apt 4B, Springfield, IL 62704, USA")
parts.components   # house_number, street, unit, city, region, postal_code, country
parts.reasons      # what was recognized and what could not be placed
parts.confidence   # the weakest named signal
parts.key()        # a comparison key for duplicate detection
```

The standard library parser works from declared data: unit keywords and
postal code patterns for the United States, Canada, and Britain. It finds
the postal code before it judges the city, so a city ahead of a code is
never called ambiguous, and it names every component it could not place.
The optional `usaddress` and `libpostal` parsers enter through
`extract_components(text, parser="usaddress")` or `parser="libpostal"` as
adapters whose label maps are data; when the package is not installed the
result says so (`available` is false) instead of guessing.
