"""Seeded generation by role or domain: questions, facts, and code seeds from occupations.

An occupation record (a code, a title, a description, its task statements,
its domain, and the source it came from) becomes a batch of candidate
seeds: the questions a careful worker asks about each task, fact triples
that say what the occupation does, and code seed specifications for tasks
whose verbs name a detection or correction operation. Public occupation
tables such as O*NET and ESCO are read through a declared column mapping,
never through code that knows one file layout, and the packaged first
seeds are hand-authored. Every seed is a candidate with provenance and a
digest, and staging writes seeds through a store contract, never into a
file. This module grants nothing and qualifies nothing: promotion belongs
to the reusable capability flywheel and the governance ladder.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from dataclasses import dataclass, field
from importlib.resources import files
from pathlib import Path

from .context_ontology import LIFECYCLE_STATES, QUESTION_FAMILIES, SOURCE_TYPES
from .store_serve import STORE_KINDS, TIERS, StoreRecord

VERSION = "1.0.0"
OCCUPATION_RECORD_TYPE = "occupation_record/v1"
SEED_RECORD_TYPE = "seed_record/v1"
SEED_BATCH_RECORD_TYPE = "seed_batch/v1"
STAGING_REPORT_RECORD_TYPE = "seed_staging_report/v1"
OCCUPATION_TABLE_RECORD_TYPE = "occupation_table/v1"

#: The three seed kinds one occupation yields.
SEED_KINDS = ("question", "fact", "code_seed")
#: The only lifecycle a seed can carry; qualification happens elsewhere.
CANDIDATE = LIFECYCLE_STATES[1]
#: The category every seed carries, matching the packaged candidate records.
SEED_CATEGORY = "job_position"
#: Declared source identities for occupation tables.
SOURCE_KINDS = ("hand_authored", "onet", "esco")
#: The fact predicates a seed batch emits.
PREDICATES = ("has_task", "in_domain", "titled")
#: A code seed is a specification; it never carries an implementation.
NO_IMPLEMENTATION = "none"
#: The store contracts staging can write through.
STORE_CONTRACTS = ("catalog", "solver")
#: The catalog collection and layer generated seeds are filed under.
SEED_SOURCE_COLLECTION = "learned"
SEED_INTELLIGENCE_LAYER = "context"
SEED_ARTIFACT_KIND = "intelligence_record"
#: The intelligence pillar the search and serve plane files seeds under.
SEED_PILLAR = "context_intelligence"
#: The packaged first seeds.
PACKAGED_SEEDS_FILE = "occupation_seeds.yaml"
#: The general questions asked about every task: name, template, question family.
#: Each family is checked against the context ontology when the module loads.
QUESTION_TEMPLATES = (
    ("inputs_needed", "For the task '{task}' performed by a {title}: which inputs are needed before it starts?",
     "prerequisites"),
    ("outputs_produced", "For the task '{task}' performed by a {title}: which outputs does it produce?",
     "direct"),
    ("completion_check", "For the task '{task}' performed by a {title}: which check proves it is done?",
     "evidence_needed"),
    ("failure_watch", "For the task '{task}' performed by a {title}: which failure does a careful worker watch for?",
     "premortem"),
    ("record_kept", "For the task '{task}' performed by a {title}: which record is kept afterwards?",
     "direct"),
    ("approver", "For the task '{task}' performed by a {title}: who approves the result?",
     "direct"),
)
_UNKNOWN_FAMILIES = [family for _name, _template, family in QUESTION_TEMPLATES
                     if family not in QUESTION_FAMILIES]
if _UNKNOWN_FAMILIES:
    raise ImportError(f"question templates name unknown question families {_UNKNOWN_FAMILIES}")
#: Task verbs that name a detection or correction operation, with the operation kind.
VERB_OPERATIONS = (
    ("verify", "validation"), ("validate", "validation"), ("reconcile", "reconciliation"),
    ("classify", "classification"), ("enter", "entry_check"), ("review", "review"),
    ("calculate", "calculation"), ("match", "matching"), ("detect", "detection"),
    ("correct", "correction"), ("deduplicate", "deduplication"), ("format", "formatting"),
    ("export", "export"), ("standardize", "standardization"), ("monitor", "monitoring"),
)


class SeededGenerationError(ValueError):
    """An occupation, mapping, seed, or staging request is invalid."""


def _digest_of(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _text(value, name: str) -> str:
    if not isinstance(value, str):
        raise SeededGenerationError(f"{name} must be text")
    return value.strip()


def _slug(text: str) -> str:
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", text.lower())).strip("_")


@dataclass(frozen=True)
class OccupationRecord:
    """One occupation: what it is called, what it does, and where it came from."""

    code: str
    title: str
    description: str
    tasks: tuple[str, ...]
    domain: str = ""
    source: str = SOURCE_KINDS[0]
    license: str = ""
    version: str = ""
    task_ids: tuple[str, ...] = ()

    def __post_init__(self):
        for name in ("code", "title"):
            if not _text(getattr(self, name), name):
                raise SeededGenerationError(f"an occupation needs a nonempty {name}")
        for name in ("description", "domain", "source", "license", "version"):
            _text(getattr(self, name), name)
        if not self.source.strip():
            raise SeededGenerationError("an occupation names its source")
        tasks = tuple(_text(item, "task") for item in self.tasks)
        if not tasks or any(not item for item in tasks):
            raise SeededGenerationError("an occupation needs at least one nonempty task statement")
        task_ids = tuple(_text(item, "task_id") for item in self.task_ids)
        if task_ids and len(task_ids) != len(tasks):
            raise SeededGenerationError("task identities, when given, match the tasks one to one")
        object.__setattr__(self, "tasks", tasks)
        object.__setattr__(self, "task_ids", task_ids)

    @property
    def job_position(self) -> str:
        return _slug(self.title)

    def to_dict(self) -> dict:
        return {"record_type": OCCUPATION_RECORD_TYPE, "code": self.code, "title": self.title,
                "description": self.description, "tasks": list(self.tasks),
                "task_ids": list(self.task_ids), "domain": self.domain, "source": self.source,
                "license": self.license, "version": self.version,
                "job_position": self.job_position}

    @property
    def digest(self) -> str:
        return _digest_of(self.to_dict())

    @classmethod
    def from_dict(cls, value) -> "OccupationRecord":
        if not isinstance(value, dict) or value.get("record_type") != OCCUPATION_RECORD_TYPE:
            raise SeededGenerationError(f"an occupation record needs record_type {OCCUPATION_RECORD_TYPE}")
        return cls(str(value.get("code", "")), str(value.get("title", "")),
                   str(value.get("description", "")), tuple(value.get("tasks") or ()),
                   domain=str(value.get("domain", "")), source=str(value.get("source", "")),
                   license=str(value.get("license", "")), version=str(value.get("version", "")),
                   task_ids=tuple(value.get("task_ids") or ()))


@dataclass(frozen=True)
class SourceIdentity:
    """Who published an occupation table, under which license, at which version."""

    source: str = SOURCE_KINDS[0]
    license: str = ""
    version: str = ""

    def __post_init__(self):
        for name in ("source", "license", "version"):
            _text(getattr(self, name), name)
        if not self.source.strip():
            raise SeededGenerationError("a source identity names its source")


@dataclass(frozen=True)
class ColumnMapping:
    """Which columns of an occupation table hold which field; names are data."""

    code: str
    title: str
    description: str
    task: str
    task_code: str = ""
    task_id: str = ""
    domain: str = ""
    identity: SourceIdentity = field(default_factory=SourceIdentity)

    def __post_init__(self):
        for name in ("code", "title", "description", "task"):
            if not _text(getattr(self, name), name):
                raise SeededGenerationError(f"a column mapping names the {name} column")
        for name in ("task_code", "task_id", "domain"):
            _text(getattr(self, name), name)
        if not isinstance(self.identity, SourceIdentity):
            raise SeededGenerationError("identity must be a SourceIdentity")

    def with_version(self, version: str) -> "ColumnMapping":
        """The same mapping bound to one published version of the table."""
        return ColumnMapping(self.code, self.title, self.description, self.task, self.task_code,
                             self.task_id, self.domain,
                             SourceIdentity(self.identity.source, self.identity.license, version))

    @property
    def occupation_columns(self) -> tuple[str, ...]:
        return tuple(item for item in (self.code, self.title, self.description, self.domain) if item)

    @property
    def task_columns(self) -> tuple[str, ...]:
        return tuple(item for item in (self.task_code or self.code, self.task, self.task_id) if item)


#: The public O*NET layout: an occupation file and a task statements file joined on the code.
ONET_MAPPING = ColumnMapping("O*NET-SOC Code", "Title", "Description", "Task", task_id="Task ID",
                             identity=SourceIdentity(SOURCE_KINDS[1], "CC BY 4.0"))
#: The ESCO occupations file has no task file in the same shape, so the
#: description column serves as the single task source; a caller with ESCO
#: task data supplies its own mapping.
ESCO_MAPPING = ColumnMapping("conceptUri", "preferredLabel", "description", "description",
                             identity=SourceIdentity(SOURCE_KINDS[2],
                                                     "European Commission reuse policy, Decision 2011/833/EU"))


@dataclass(frozen=True)
class OccupationTable:
    """The occupations read from a table and the codes skipped for having no task."""

    occupations: tuple[OccupationRecord, ...]
    skipped: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {"record_type": OCCUPATION_TABLE_RECORD_TYPE,
                "occupations": [item.to_dict() for item in self.occupations],
                "skipped": list(self.skipped)}


def _require_columns(row, columns: tuple[str, ...], label: str) -> None:
    missing = [name for name in columns if name not in row]
    if missing:
        raise SeededGenerationError(f"the {label} rows lack the declared columns {missing}")


def read_occupation_table(occupation_rows, task_rows, mapping: ColumnMapping) -> OccupationTable:
    """Join occupation rows with task rows on the code column under one mapping.

    ``task_rows`` may be ``None``: the occupation rows then serve as the task
    rows and ``mapping.task`` names the column that holds the single task,
    which is how the ESCO layout is read.
    """
    if not isinstance(mapping, ColumnMapping):
        raise SeededGenerationError("a typed ColumnMapping is required")
    occupations = [dict(row) for row in occupation_rows]
    tasks = occupations if task_rows is None else [dict(row) for row in task_rows]
    if not occupations:
        return OccupationTable(())
    _require_columns(occupations[0], mapping.occupation_columns, "occupation")
    if tasks:
        _require_columns(tasks[0], mapping.task_columns, "task")
    task_code = mapping.task_code or mapping.code
    by_code: dict = {}
    for row in tasks:
        code = str(row.get(task_code, "")).strip()
        text = str(row.get(mapping.task, "")).strip()
        if code and text:
            by_code.setdefault(code, []).append((str(row.get(mapping.task_id, "")).strip(), text))
    records, skipped = [], []
    for row in occupations:
        code = str(row.get(mapping.code, "")).strip()
        statements = by_code.get(code, [])
        if not code or not statements:
            skipped.append(code or "(no code)")
            continue
        ids = tuple(item[0] for item in statements)
        records.append(OccupationRecord(
            code, str(row.get(mapping.title, "")), str(row.get(mapping.description, "")),
            tuple(item[1] for item in statements),
            domain=str(row.get(mapping.domain, "")) if mapping.domain else "",
            source=mapping.identity.source, license=mapping.identity.license,
            version=mapping.identity.version, task_ids=ids if all(ids) else ()))
    return OccupationTable(tuple(records), tuple(skipped))


def read_occupation_rows(occupation_rows, task_rows, mapping: ColumnMapping) -> tuple[OccupationRecord, ...]:
    """The occupations of ``read_occupation_table``; skipped codes are in the table."""
    return read_occupation_table(occupation_rows, task_rows, mapping).occupations


@dataclass(frozen=True)
class DelimitedSources:
    """The occupation file and the optional task file of one delimited table."""

    occupations_path: str
    tasks_path: str = ""
    delimiter: str = "\t"
    encoding: str = "utf-8"

    def __post_init__(self):
        if not _text(self.occupations_path, "occupations_path"):
            raise SeededGenerationError("delimited sources name the occupation file")
        _text(self.tasks_path, "tasks_path")
        if not isinstance(self.delimiter, str) or len(self.delimiter) != 1:
            raise SeededGenerationError("the delimiter is one character")


def read_delimited(sources: DelimitedSources, mapping: ColumnMapping) -> OccupationTable:
    """Read a delimited occupation table, and its task file when one is named."""
    if not isinstance(sources, DelimitedSources):
        raise SeededGenerationError("typed DelimitedSources are required")
    with Path(sources.occupations_path).open("r", encoding=sources.encoding, newline="") as handle:
        occupations = list(csv.DictReader(handle, delimiter=sources.delimiter))
    tasks = None
    if sources.tasks_path:
        with Path(sources.tasks_path).open("r", encoding=sources.encoding, newline="") as handle:
            tasks = list(csv.DictReader(handle, delimiter=sources.delimiter))
    return read_occupation_table(occupations, tasks, mapping)


@dataclass(frozen=True)
class SeedRecord:
    """One candidate seed: a question, a fact, or a code seed specification."""

    kind: str
    text: str
    subcategory: str
    job_position: str
    domain: str
    body: dict
    provenance: str

    def __post_init__(self):
        if self.kind not in SEED_KINDS:
            raise SeededGenerationError(f"seed kind must be one of {SEED_KINDS}")
        for name in ("text", "subcategory", "job_position", "provenance"):
            if not _text(getattr(self, name), name):
                raise SeededGenerationError(f"a seed needs a nonempty {name}")
        _text(self.domain, "domain")
        if not isinstance(self.body, dict):
            raise SeededGenerationError("a seed body is a mapping")

    @property
    def category(self) -> str:
        return SEED_CATEGORY

    @property
    def maturity(self) -> str:
        return CANDIDATE

    @property
    def digest(self) -> str:
        return _digest_of({"kind": self.kind, "text": self.text, "body": self.body,
                           "job_position": self.job_position})

    @property
    def record_id(self) -> str:
        return f"seed.{self.kind}.{self.digest[:16]}"

    def to_dict(self) -> dict:
        return {"record_type": SEED_RECORD_TYPE, "kind": self.kind, "text": self.text,
                "category": self.category, "subcategory": self.subcategory,
                "job_position": self.job_position, "domain": self.domain,
                "digest": self.digest, "maturity": self.maturity,
                "provenance": self.provenance, "body": json.loads(json.dumps(self.body))}


@dataclass(frozen=True)
class SeedBatch:
    """Every seed generated from one occupation at one generator version."""

    occupation_code: str
    occupation_digest: str
    job_position: str
    domain: str
    version: str
    seeds: tuple[SeedRecord, ...]

    def __post_init__(self):
        if any(not isinstance(item, SeedRecord) for item in self.seeds):
            raise SeededGenerationError("a seed batch holds SeedRecords")
        object.__setattr__(self, "seeds", tuple(self.seeds))

    @property
    def counts(self) -> dict:
        return {kind: sum(1 for item in self.seeds if item.kind == kind) for kind in SEED_KINDS}

    def of_kind(self, kind: str) -> tuple[SeedRecord, ...]:
        if kind not in SEED_KINDS:
            raise SeededGenerationError(f"seed kind must be one of {SEED_KINDS}")
        return tuple(item for item in self.seeds if item.kind == kind)

    @property
    def digest(self) -> str:
        return _digest_of([item.digest for item in self.seeds])

    def to_dict(self) -> dict:
        return {"record_type": SEED_BATCH_RECORD_TYPE, "occupation_code": self.occupation_code,
                "occupation_digest": self.occupation_digest, "job_position": self.job_position,
                "domain": self.domain, "version": self.version, "counts": self.counts,
                "digest": self.digest, "seeds": [item.to_dict() for item in self.seeds]}


def _provenance(occupation: OccupationRecord, version: str) -> str:
    return f"seeded_generation/{version}:{occupation.source}:{occupation.code}"


def _verb_in(verb: str, text: str) -> bool:
    """Whole-word, case-insensitive match of the exact verb; no substring, no inflection."""
    return re.search(r"\b" + re.escape(verb) + r"\b", text, re.IGNORECASE) is not None


def operations_named_by(task: str) -> tuple[tuple[str, str], ...]:
    """The (verb, operation kind) pairs a task statement names, in table order."""
    return tuple((verb, kind) for verb, kind in VERB_OPERATIONS if _verb_in(verb, task))


def _question_seeds(occupation: OccupationRecord, provenance: str) -> list:
    seeds = []
    for index, task in enumerate(occupation.tasks):
        task_id = occupation.task_ids[index] if occupation.task_ids else str(index + 1)
        for form_name, template, family in QUESTION_TEMPLATES:
            text = template.format(task=task, title=occupation.title)
            seeds.append(SeedRecord(SEED_KINDS[0], text, form_name, occupation.job_position,
                                    occupation.domain,
                                    {"form": form_name, "question_family": family,
                                     "slots": {"task": task, "title": occupation.title},
                                     "task_id": task_id}, provenance))
    return seeds


def _fact_seeds(occupation: OccupationRecord, provenance: str) -> list:
    triples = [(occupation.code, PREDICATES[2], occupation.title)]
    if occupation.domain:
        triples.append((occupation.code, PREDICATES[1], occupation.domain))
    triples.extend((occupation.code, PREDICATES[0], task) for task in occupation.tasks)
    seeds = []
    for subject, predicate, obj in triples:
        seeds.append(SeedRecord(SEED_KINDS[1], f"{occupation.title} ({subject}) {predicate}: {obj}",
                                predicate, occupation.job_position, occupation.domain,
                                {"subject": subject, "predicate": predicate, "object": obj,
                                 "source": occupation.source, "source_version": occupation.version},
                                provenance))
    return seeds


def _code_seeds(occupation: OccupationRecord, provenance: str) -> list:
    seeds = []
    for index, task in enumerate(occupation.tasks):
        for verb, operation_kind in operations_named_by(task):
            tests = (f"a_known_good_input_passes_{operation_kind}",
                     f"a_known_bad_input_is_flagged_by_{operation_kind}",
                     "an_ambiguous_input_is_held_with_a_confidence_below_the_apply_threshold")
            seeds.append(SeedRecord(
                SEED_KINDS[2], f"{operation_kind} operation for a {occupation.title}: {task}",
                operation_kind, occupation.job_position, occupation.domain,
                {"operation_kind": operation_kind, "verb": verb, "purpose": task,
                 "task_index": index + 1,
                 "input_sketch": "the rows or records the task acts on, with the field the verb applies to",
                 "output_sketch": f"one {operation_kind} result per input with a confidence and the "
                                  "signal that decided it",
                 "implementation": NO_IMPLEMENTATION, "tests_to_write": list(tests)},
                provenance))
    return seeds


def generate_seeds(occupation: OccupationRecord, *, version: str = VERSION) -> SeedBatch:
    """Every question, fact, and code seed one occupation yields, all candidates."""
    if not isinstance(occupation, OccupationRecord):
        raise SeededGenerationError("a typed OccupationRecord is required")
    if not _text(version, "version"):
        raise SeededGenerationError("a generator version is required")
    provenance = _provenance(occupation, version)
    seeds = (_question_seeds(occupation, provenance) + _fact_seeds(occupation, provenance)
             + _code_seeds(occupation, provenance))
    return SeedBatch(occupation.code, occupation.digest, occupation.job_position, occupation.domain,
                     version, tuple(seeds))


def batches_in_domain(batches, domain: str) -> tuple[SeedBatch, ...]:
    """The batches whose occupation belongs to one domain."""
    wanted = _text(domain, "domain")
    return tuple(item for item in batches if isinstance(item, SeedBatch) and item.domain == wanted)


def batch_for_job_position(batches, job_position: str) -> "SeedBatch | None":
    """The batch for one job position slug, or None."""
    wanted = _text(job_position, "job_position")
    for item in batches:
        if isinstance(item, SeedBatch) and item.job_position == wanted:
            return item
    return None


@dataclass(frozen=True)
class StagingReport:
    """What staging wrote: the contract used, the counts per kind, and the identities."""

    namespace: str
    store_contract: str
    counts: dict
    record_ids: tuple[str, ...]

    @property
    def total(self) -> int:
        return len(self.record_ids)

    def to_dict(self) -> dict:
        return {"record_type": STAGING_REPORT_RECORD_TYPE, "namespace": self.namespace,
                "store_contract": self.store_contract, "counts": dict(self.counts),
                "total": self.total, "record_ids": list(self.record_ids)}


def _facets(seed: SeedRecord, occupation_source: str) -> dict:
    from .facets import context_facets
    source_type = SOURCE_TYPES[0] if occupation_source == SOURCE_KINDS[0] else SOURCE_TYPES[2]
    body = seed.body
    return context_facets(
        category=seed.category, subcategory=seed.subcategory, context_type=_context_type(seed),
        job_position=seed.job_position, domain=seed.domain,
        question_family=str(body.get("question_family", "")) if seed.kind == SEED_KINDS[0] else "",
        lifecycle=seed.maturity, provenance=seed.provenance, source_type=source_type,
        scope="package", digest=seed.digest)


def _context_type(seed: SeedRecord) -> str:
    # question -> question, fact -> fact, code seed -> template (a specification to fill).
    return {SEED_KINDS[0]: "question", SEED_KINDS[1]: "fact", SEED_KINDS[2]: "template"}[seed.kind]


def catalog_record(seed: SeedRecord, *, namespace: str, version: str, occupation_source: str) -> dict:
    """The seed as a unified catalog record for a store with ``put``."""
    return {"record_id": seed.record_id, "record_version": version, "record_type": SEED_RECORD_TYPE,
            "intelligence_layer": SEED_INTELLIGENCE_LAYER, "source_collection": SEED_SOURCE_COLLECTION,
            "artifact_kind": SEED_ARTIFACT_KIND, "lifecycle": seed.maturity, "namespace": namespace,
            "attributes": {**seed.to_dict(), "facets": _facets(seed, occupation_source)}}


def store_record(seed: SeedRecord, *, occupation_source: str) -> StoreRecord:
    """The seed as the search and serve plane's record for a store with ``add``."""
    kind = STORE_KINDS[1] if seed.kind == SEED_KINDS[0] else STORE_KINDS[3]
    body = {**seed.to_dict(), "facets": _facets(seed, occupation_source)}
    return StoreRecord(seed.record_id, kind, seed.text[:80], body=body,
                       tags=(SEED_CATEGORY, seed.kind, seed.job_position, seed.maturity),
                       tier=TIERS[1])


def stage_seeds(batch: SeedBatch, store, *, namespace: str = "seeds",
                occupation_source: str = SOURCE_KINDS[0]) -> StagingReport:
    """Write every seed of a batch through the store's contract and report what landed.

    A store with ``put`` receives unified catalog records; a store with
    ``add`` and ``records`` (the search and serve plane that the intelligence
    layers and the capability directory read) receives StoreRecords in the
    experimental tier, which the plane keeps out of search and serve until a
    caller enables that tier. The report counts only writes the store
    acknowledged or lists back.
    """
    if not isinstance(batch, SeedBatch):
        raise SeededGenerationError("a typed SeedBatch is required")
    if not _text(namespace, "namespace"):
        raise SeededGenerationError("a namespace is required")
    if hasattr(store, "put"):
        contract = STORE_CONTRACTS[0]
    elif hasattr(store, "add") and hasattr(store, "records"):
        contract = STORE_CONTRACTS[1]
    else:
        raise SeededGenerationError("the store offers neither put nor add and records")
    landed = []
    if contract == STORE_CONTRACTS[0]:
        for seed in batch.seeds:
            acknowledged = store.put(catalog_record(seed, namespace=namespace, version=batch.version,
                                                    occupation_source=occupation_source))
            if isinstance(acknowledged, dict) and acknowledged.get("stored") is True:
                landed.append(seed)
    else:
        from ..loop.intelligence_loops import records_as_loop
        for seed in batch.seeds:
            store.add(store_record(seed, occupation_source=occupation_source))
        # The search and serve plane gates candidate tiers on serve, so the
        # acknowledgement reads the record cards through the loop envelope
        # that owns the store; the cards list every tier.
        cards = records_as_loop(store, pillar=SEED_PILLAR)["value"]
        present = {item.record_id for item in cards}
        landed = [seed for seed in batch.seeds if seed.record_id in present]
    counts = {kind: sum(1 for item in landed if item.kind == kind) for kind in SEED_KINDS}
    return StagingReport(namespace, contract, counts, tuple(item.record_id for item in landed))


def packaged_occupations() -> tuple[OccupationRecord, ...]:
    """The hand-authored occupations shipped inside the package."""
    import yaml
    text = files("loop_engine.data").joinpath(PACKAGED_SEEDS_FILE).read_text("utf-8")
    data = yaml.safe_load(text)
    if not isinstance(data, dict) or not isinstance(data.get("occupations"), list):
        raise SeededGenerationError("the packaged seeds file holds a mapping with an occupations list")
    source = str(data.get("source", SOURCE_KINDS[0]))
    license_text = str(data.get("license", ""))
    version = str(data.get("version", ""))
    return tuple(OccupationRecord(str(item.get("code", "")), str(item.get("title", "")),
                                  str(item.get("description", "")), tuple(item.get("tasks") or ()),
                                  domain=str(item.get("domain", "")), source=source,
                                  license=license_text, version=version)
                 for item in data["occupations"])


def packaged_seed_batches(*, version: str = VERSION) -> tuple[SeedBatch, ...]:
    """One seed batch per packaged occupation."""
    return tuple(generate_seeds(item, version=version) for item in packaged_occupations())


def self_test() -> dict:
    """Reading, generation, candidate state, whole-word verbs, staging, and the packaged seeds."""
    import tempfile
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    def refuses(action):
        try:
            action()
        except SeededGenerationError:
            return True
        return False

    onet_occupations = [
        {"O*NET-SOC Code": "43-9021.00", "Title": "Data Entry Keyers",
         "Description": "Operate data entry devices."},
        {"O*NET-SOC Code": "43-3031.00", "Title": "Bookkeeping Clerks",
         "Description": "Compute and record numerical data."},
        {"O*NET-SOC Code": "99-0000.00", "Title": "No Tasks Listed", "Description": "Placeholder."},
    ]
    onet_tasks = [
        {"O*NET-SOC Code": "43-9021.00", "Task ID": "1", "Task": "Enter records into the database."},
        {"O*NET-SOC Code": "43-9021.00", "Task ID": "2", "Task": "Verify entered data against source documents."},
        {"O*NET-SOC Code": "43-3031.00", "Task ID": "3", "Task": "Reconcile bank statements with the ledger."},
        {"O*NET-SOC Code": "43-3031.00", "Task ID": "4", "Task": "Prepare an overview of monthly totals."},
    ]
    table = read_occupation_table(onet_occupations, onet_tasks, ONET_MAPPING.with_version("30.1"))
    keyers = table.occupations[0]
    check("onet_shaped_rows_read_into_occupations_with_tasks_joined_by_code",
          len(table.occupations) == 2 and keyers.code == "43-9021.00" and len(keyers.tasks) == 2
          and keyers.task_ids == ("1", "2") and keyers.source == SOURCE_KINDS[1]
          and keyers.version == "30.1" and keyers.job_position == "data_entry_keyers"
          and table.skipped == ("99-0000.00",))
    check("a_mapping_whose_column_is_absent_is_refused",
          refuses(lambda: read_occupation_table([{"Code": "1", "Title": "x", "Description": "y"}],
                                                onet_tasks, ONET_MAPPING))
          and refuses(lambda: read_occupation_table(onet_occupations, [{"Task": "x"}], ONET_MAPPING))
          and refuses(lambda: read_occupation_table(onet_occupations, onet_tasks, {"code": "x"})))
    esco = read_occupation_table(
        [{"conceptUri": "http://data.europa.eu/esco/occupation/1", "preferredLabel": "records clerk",
          "description": "Classify and file records."}], None, ESCO_MAPPING)
    check("esco_shaped_rows_take_the_description_as_the_single_task",
          len(esco.occupations) == 1 and esco.occupations[0].tasks == ("Classify and file records.",)
          and esco.occupations[0].source == SOURCE_KINDS[2] and esco.occupations[0].task_ids == ())
    batch = generate_seeds(keyers)
    check("every_generated_seed_is_a_candidate_with_provenance_and_a_digest",
          batch.seeds and all(item.maturity == LIFECYCLE_STATES[1] for item in batch.seeds)
          and all(item.to_dict()["maturity"] == LIFECYCLE_STATES[1] for item in batch.seeds)
          and all(item.provenance == f"seeded_generation/{VERSION}:onet:43-9021.00" for item in batch.seeds)
          and all(len(item.digest) == 64 for item in batch.seeds)
          and all(item.category == "job_position" for item in batch.seeds)
          and batch.counts == {"question": 12, "fact": 3, "code_seed": 2})
    again = generate_seeds(keyers)
    check("generation_is_deterministic_for_the_same_occupation_and_version",
          again.digest == batch.digest
          and [item.digest for item in again.seeds] == [item.digest for item in batch.seeds]
          and generate_seeds(keyers, version="2.0.0").digest == batch.digest
          and generate_seeds(keyers, version="2.0.0").seeds[0].provenance != batch.seeds[0].provenance)
    clerks = table.occupations[1]
    clerk_batch = generate_seeds(clerks)
    code_seeds = clerk_batch.of_kind(SEED_KINDS[2])
    verify_only = generate_seeds(OccupationRecord("t", "Tester", "", ("Correctness reports are filed.",)))
    check("a_code_seed_appears_only_for_a_whole_word_verb_match",
          len(code_seeds) == 1 and code_seeds[0].body["operation_kind"] == "reconciliation"
          and code_seeds[0].body["implementation"] == NO_IMPLEMENTATION
          and len(code_seeds[0].body["tests_to_write"]) == 3
          and verify_only.counts["code_seed"] == 0
          and operations_named_by("Match invoices and REVIEW them weekly.") == (("review", "review"),
                                                                                 ("match", "matching"))
          and operations_named_by("Matches are reviewed; formatted output.") == ())
    from ..catalog.stores.in_memory import EphemeralRecordStore
    from ..catalog.query import IntelligenceQuery
    from .store_serve import SolverStore
    catalog = EphemeralRecordStore()
    report = stage_seeds(batch, catalog, namespace="fixture", occupation_source=keyers.source)
    stored = catalog.query(IntelligenceQuery(namespaces=("fixture",), lifecycle=(LIFECYCLE_STATES[1],)))
    solver = SolverStore()
    solver_report = stage_seeds(batch, solver, occupation_source=keyers.source)
    gated = solver.serve(batch.seeds[0].record_id)
    solver.enable_tier(TIERS[1])
    served = solver.serve(batch.seeds[0].record_id)
    check("staging_writes_one_candidate_record_per_seed_through_the_store_contract",
          report.store_contract == STORE_CONTRACTS[0] and report.counts == batch.counts
          and report.total == len(batch.seeds) == len(stored)
          and all(item["attributes"]["maturity"] == LIFECYCLE_STATES[1] for item in stored)
          and all(item["attributes"]["facets"]["lifecycle"] == LIFECYCLE_STATES[1] for item in stored)
          and solver_report.store_contract == STORE_CONTRACTS[1] and solver_report.counts == batch.counts
          and gated is None and served is not None and served.tier == TIERS[1]
          and served.body["facets"]["job_position"] == "data_entry_keyers"
          and served.body["facets"]["lifecycle"] == LIFECYCLE_STATES[1]
          and refuses(lambda: stage_seeds(batch, object())))
    packaged = packaged_occupations()
    batches = packaged_seed_batches()
    totals = {kind: sum(item.counts[kind] for item in batches) for kind in SEED_KINDS}
    check("the_packaged_occupations_load_and_generate_all_three_seed_kinds",
          len(packaged) == 6 and all(item.source == SOURCE_KINDS[0] for item in packaged)
          and all(5 <= len(item.tasks) <= 8 for item in packaged)
          and len({item.code for item in packaged}) == 6
          and all(totals[kind] > 0 for kind in SEED_KINDS)
          and all(item.counts["code_seed"] > 0 for item in batches))
    check("an_occupation_without_tasks_is_refused",
          refuses(lambda: OccupationRecord("c", "Title", "d", ()))
          and refuses(lambda: OccupationRecord("c", "Title", "d", ("",)))
          and refuses(lambda: OccupationRecord("", "Title", "d", ("task",)))
          and refuses(lambda: OccupationRecord("c", "Title", "d", ("task",), task_ids=("1", "2"))))
    check("batches_can_be_found_by_domain_and_job_position",
          batch_for_job_position(batches, "data_engineer") is not None
          and batch_for_job_position(batches, "astronaut") is None
          and len(batches_in_domain(batches, packaged[0].domain)) >= 1
          and all(item.domain == packaged[0].domain for item in batches_in_domain(batches, packaged[0].domain)))
    names = [name for name in globals() if callable(globals()[name])]
    check("the_module_exposes_no_promote_or_qualify_function",
          not any("promote" in name.lower() or "qualif" in name.lower() for name in names))
    with tempfile.TemporaryDirectory(prefix="seeds-") as folder:
        occupations_path = Path(folder) / "Occupation Data.txt"
        tasks_path = Path(folder) / "Task Statements.txt"
        with occupations_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["O*NET-SOC Code", "Title", "Description"], delimiter="\t")
            writer.writeheader()
            writer.writerows(onet_occupations)
        with tasks_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["O*NET-SOC Code", "Task ID", "Task"], delimiter="\t")
            writer.writeheader()
            writer.writerows(onet_tasks)
        from_files = read_delimited(DelimitedSources(str(occupations_path), str(tasks_path)), ONET_MAPPING)
    check("read_delimited_reads_tab_separated_files_with_the_onet_mapping",
          [item.digest for item in from_files.occupations]
          == [item.digest for item in read_occupation_table(onet_occupations, onet_tasks, ONET_MAPPING).occupations]
          and from_files.skipped == ("99-0000.00",)
          and refuses(lambda: DelimitedSources("", ""))
          and refuses(lambda: read_delimited("x", ONET_MAPPING)))
    check("records_round_trip_through_their_dicts",
          OccupationRecord.from_dict(keyers.to_dict()) == keyers
          and refuses(lambda: OccupationRecord.from_dict({"code": "x"}))
          and batch.to_dict()["counts"] == batch.counts
          and report.to_dict()["total"] == report.total
          and "seeded_generation" in json.dumps(batch.to_dict()))
    passed = sum(item["passed"] for item in tests)
    return {"record_type": "seeded_generation_test/v1", "tests": tests, "passed": passed,
            "total": len(tests), "all_passed": passed == len(tests)}
