"""Deterministic harness intelligence idea matrix.

Crosses the pinned occupation grid with declared datatype, operation,
and use-case facets to emit candidate method hypotheses. Every hypothesis
is a typed record with provenance, a known-wrong case, and a method
signature used for deduplication: job title, employer, location, model,
or harness are applicability facets until they change the method, its
effects, or its acceptance check. Nothing here approves, stages, or
serves an item: the output is candidate ideation only, in the same
family as the pinned O*NET method briefs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

if __name__ == "__main__" and __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    sys.path.insert(0, str(Path(__file__).resolve().parent))

MATRIX_RECORD_TYPE = "harness_idea_matrix/v1"
IDEA_RECORD_TYPE = "harness_idea_record/v1"
IDEA_BATCH_RECORD_TYPE = "harness_idea_batch/v1"

#: Digital data kinds a harness method can transform or inspect.
DATATYPES = (
    "text", "string", "string_column", "number", "numeric_column",
    "date_and_time", "identifier", "boolean", "json_object", "json_array",
    "csv_table", "tsv_table", "sql_table", "sql_query_log", "parquet_table",
    "matrix", "vector", "image", "audio", "pdf_document", "html_page",
    "log_lines", "yaml_config", "toml_config", "markdown_document",
    "url", "email_address", "postal_address", "person_name", "geolocation",
    "tree_structure", "graph", "file_path", "binary_blob", "version_range",
)

#: Operation families: what a method does to its input datatype.
OPERATIONS = (
    "standardization", "validation", "deduplication", "matching",
    "reconciliation", "classification", "extraction", "transformation",
    "parsing", "formatting", "sorting", "grouping", "aggregation",
    "join", "splitting", "comparison", "correction", "monitoring",
    "profiling", "sampling", "encoding_conversion", "linking",
    "enrichment", "counting", "measurement", "detection", "routing",
    "planning", "reviewing", "explanation", "estimation", "verification",
    "multiplication", "inversion", "normalization", "reduction",
)

#: Use-case facets: where and by whom the method runs.
USE_CASES = (
    "data_cleaning", "data_engineering", "database_operations",
    "text_processing", "report_generation", "quality_assurance",
    "software_development", "devops", "security_review", "compliance_audit",
    "financial_reconciliation", "customer_support", "project_management",
    "research_analysis", "machine_learning", "benchmarking",
    "agentic_task", "agentic_benchmark", "agent_coordination",
    "documentation", "training_material", "string_operations",
    "matrix_mathematics", "entity_resolution", "record_linkage",
)

#: Job-description dimensions kept as facets, per the S-6.40 rule.
FACET_DIMENSIONS = ("job_title", "seniority", "location", "language",
                    "company_archetype", "project_stage", "harness",
                    "model")

#: The pinned O*NET selection of occupations with task statements.
DEFAULT_OPPORTUNITIES = Path(__file__).resolve().parents[1] / (
    "artifacts/occupation-grid-research-2026-09-22/task-opportunities.json")
DEFAULT_SEEDS = Path(__file__).resolve().parents[1] / "src/loop_engine/data/occupation_seeds.yaml"
MAX_IDEAS = 200000
IDENTITY = re.compile(r"^[a-z0-9][a-z0-9-]{2,63}$")
LIFECYCLE = "candidate"


class MatrixError(ValueError):
    """A matrix, source, or idea request is invalid."""


@dataclass(frozen=True)
class MatrixSource:
    """One pinned source inventory the matrix may draw occupations from."""

    kind: str
    path: Path
    sha256: str = ""

    def __post_init__(self):
        if self.kind not in ("onet_pinned", "hand_authored", "none"):
            raise MatrixError("unknown_source_kind")
        if self.kind != "none":
            if not isinstance(self.path, Path) or not self.path.is_file():
                raise MatrixError("source_missing")
            digest = hashlib.sha256(self.path.read_bytes()).hexdigest()
            if self.sha256 and digest != self.sha256:
                raise MatrixError("source_digest_mismatch")


@dataclass
class Idea:
    """One candidate method hypothesis: typed, dedupable, never approved."""

    datatype: str
    operation: str
    use_case: str
    occupation_code: str
    occupation_title: str
    task_reference: str
    facet: str
    brief: str
    known_wrong: str

    @property
    def signature(self) -> str:
        """Method identity: datatype, operation, and use case, never facets."""
        return f"{self.datatype}|{self.operation}|{self.use_case}"


def _occupation_rows(source: MatrixSource) -> list[dict]:
    """Read occupation pairs from the pinned O*NET selection JSON."""
    if source.kind == "none":
        return []
    raw = json.loads(source.path.read_text(encoding="utf-8"))
    rows = []
    for occupation in raw.get("occupations", []):
        code = occupation.get("occupation_code", "")
        title = occupation.get("occupation_title", "")
        if not code or not title:
            raise MatrixError("occupation_row_incomplete")
        rows.append({"code": code, "title": title})
    return rows


def _task_rows(source: MatrixSource) -> dict[str, list[str]]:
    """Group task statements by occupation code from the pinned selection."""
    if source.kind == "none":
        return {}
    raw = json.loads(source.path.read_text(encoding="utf-8"))
    grouped: dict[str, list[str]] = {}
    for reference in raw.get("task_references", []):
        code = reference.get("occupation_code", "")
        statement = reference.get("source_task_text", "")
        if code and statement and statement not in grouped.setdefault(code, []):
            grouped[code].append(statement)
    return grouped


def operation_fits_datatype(datatype: str, operation: str) -> bool:
    """Reject impossible datatype-operation pairs, like parsing an image."""
    if datatype not in DATATYPES:
        raise MatrixError("unknown_datatype")
    if operation not in OPERATIONS:
        raise MatrixError(f"unknown_operation:{operation}")
    incompatible = {
        "multiplication": {"text", "html_page", "markdown_document", "person_name",
                          "email_address", "postal_address", "url", "boolean",
                          "yaml_config", "toml_config", "file_path"},
        "inversion": {"text", "html_page", "markdown_document", "person_name",
                      "email_address", "postal_address", "url", "boolean",
                      "yaml_config", "toml_config", "file_path", "date_and_time",
                      "log_lines"},
    }
    if operation in incompatible and datatype in incompatible[operation]:
        return False
    if datatype in ("matrix", "vector"):
        return operation in (
            "multiplication", "inversion", "normalization", "reduction",
            "transformation", "validation", "comparison", "aggregation",
            "measurement", "detection", "sampling", "explanation",
        )
    if datatype in ("person_name", "postal_address", "email_address"):
        return operation not in ("multiplication", "inversion", "normalization")
    return True


def _brief_for(datatype: str, operation: str, use_case: str, title: str, task: str) -> str:
    """Render the hypothesis prompt from declared dimensions."""
    return (
        f"Propose one original harness method for a {title} whose task is: {task}. "
        f"The method's input is a {datatype}; the method performs {operation}; "
        f"the use case is {use_case}. The method must name its trigger, typed input, "
        f"typed output, effects, stop condition, and the known-wrong case it must catch."
    )


KNOWN_WRONG_CASES = {
    ("string", "standardization", "data_cleaning"):
        "A record with leading and trailing whitespace is treated as clean already.",
    ("string_column", "deduplication", "data_cleaning"):
        "Two rows that differ only by case are kept as two distinct records.",
    ("text", "standardization", "data_cleaning"):
        "A tab-indented document is normalized as if the tabs were spaces.",
    ("number", "validation", "financial_reconciliation"):
        "A negative amount is accepted as a valid credit without a credit reason.",
    ("date_and_time", "standardization", "data_engineering"):
        "A naive timestamp is treated as UTC without zone evidence.",
    ("matrix", "multiplication", "machine_learning"):
        "Inner dimensions that do not match are silently padded rather than refused.",
    ("identifier", "matching", "entity_resolution"):
        "Two different entities that share a format are declared the same entity.",
    ("csv_table", "validation", "data_engineering"):
        "A row with more fields than the header is truncated and loaded.",
    ("sql_table", "standardization", "database_operations"):
        "A reserved word is accepted as a column name without quoting.",
    ("postal_address", "standardization", "data_cleaning"):
        "A unit number is dropped because the parser treats it as noise.",
    ("log_lines", "detection", "devops"):
        "A rotated log file's first lines are treated as the newest.",
    ("version_range", "comparison", "compliance_audit"):
        "A pre-release version is declared compatible with a stable pin.",
}


def _known_wrong_for(datatype: str, operation: str, use_case: str) -> str:
    """A discriminating failure each generated method must catch."""
    return KNOWN_WRONG_CASES.get(
        (datatype, operation, use_case),
        f"A plausible but wrong {operation} of a {datatype} is accepted as correct.",
    )


def _facet_rows() -> list[str]:
    """The declared job-description facet dimensions."""
    return list(FACET_DIMENSIONS)


def build_ideas(sources: list[MatrixSource] | MatrixSource | None) -> list[Idea]:
    """Cross every declared dimension into deduplicated method hypotheses."""
    if sources is None:
        sources = [MatrixSource("onet_pinned", DEFAULT_OPPORTUNITIES)]
    if isinstance(sources, MatrixSource):
        sources = [sources]
    occupations: list[dict] = []
    tasks: dict[str, list[str]] = {}
    for source in sources:
        occupations.extend(_occupation_rows(source))
        for code, statements in _task_rows(source).items():
            for statement in statements:
                if statement not in tasks.setdefault(code, []):
                    tasks[code].append(statement)
    if not occupations:
        raise MatrixError("no_occupation_source")
    seen_signatures: set[tuple[str, str, str]] = set()
    ideas: list[Idea] = []
    facets = _facet_rows()
    for datatype in DATATYPES:
        for operation in OPERATIONS:
            if not operation_fits_datatype(datatype, operation):
                continue
            for use_case in USE_CASES:
                occupation = occupations[0]
                code = occupation["code"]
                task = tasks.get(code, [""])[0] if tasks.get(code) else ""
                key = (datatype, operation, use_case)
                if key in seen_signatures:
                    continue
                seen_signatures.add(key)
                ideas.append(Idea(
                    datatype=datatype,
                    operation=operation,
                    use_case=use_case,
                    occupation_code=code,
                    occupation_title=occupation["title"],
                    task_reference=task or "the role's core work",
                    facet=facets[0],
                    brief=_brief_for(datatype, operation, use_case,
                                     occupation["title"], task or "the role's core work"),
                    known_wrong=_known_wrong_for(datatype, operation, use_case),
                ))
                if len(ideas) > MAX_IDEAS:
                    raise MatrixError("idea_overflow")
    if not ideas:
        raise MatrixError("matrix_empty")
    return ideas


def _identity_for(datatype: str, operation: str, use_case: str) -> str:
    raw = f"{datatype}-{operation}-{use_case}"
    slug = re.sub(r"[^a-z0-9]+", "-", raw.lower()).strip("-")
    if not IDENTITY.match(slug):
        raise MatrixError("identity_invalid")
    return slug


def render_batch(ideas: list[Idea], sources: list[MatrixSource]) -> dict:
    """Emit the typed batch record with provenance and digests."""
    source_records = []
    for source in sources:
        if source.kind == "none":
            continue
        source_records.append({
            "kind": source.kind,
            "path": source.path.relative_to(Path(__file__).resolve().parents[1]).as_posix(),
            "sha256": hashlib.sha256(source.path.read_bytes()).hexdigest(),
        })
    records = []
    for idea in ideas:
        identity = _identity_for(idea.datatype, idea.operation, idea.use_case)
        records.append({
            "record_type": IDEA_RECORD_TYPE,
            "id": identity,
            "datatype": idea.datatype,
            "operation": idea.operation,
            "use_case": idea.use_case,
            "lifecycle": LIFECYCLE,
            "applicability": {
                "occupation_code": idea.occupation_code,
                "occupation_title": idea.occupation_title,
                "task_reference": idea.task_reference,
                "facet_dimensions": _facet_rows(),
                "facet": idea.facet,
            },
            "method_signature": idea.signature,
            "brief": idea.brief,
            "known_wrong": idea.known_wrong,
        })
    batch_digest = hashlib.sha256(
        json.dumps(records, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "record_type": IDEA_BATCH_RECORD_TYPE,
        "matrix": {
            "record_type": MATRIX_RECORD_TYPE,
            "datatypes": len(DATATYPES),
            "operations": len(OPERATIONS),
            "use_cases": len(USE_CASES),
            "facet_dimensions": list(FACET_DIMENSIONS),
        },
        "sources": source_records,
        "ideas": records,
        "idea_count": len(records),
        "unique_method_signatures": len({r["method_signature"] for r in records}),
        "batch_sha256": batch_digest,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", required=True,
                        help="new JSON file for the typed idea batch")
    parser.add_argument("--source", action="append", default=None,
                        choices=("onet_pinned", "hand_authored", "none"),
                        help="source kind; default is the pinned O*NET selection")
    parser.add_argument("--seed-file", default=None,
                        help="path override for the hand-authored seeds file")
    args = parser.parse_args(argv)

    output = Path(args.output)
    if output.exists() or output.is_symlink():
        raise MatrixError("output_already_exists")
    sources = []
    kinds = args.source or ["onet_pinned"]
    for kind in kinds:
        if kind == "onet_pinned":
            sources.append(MatrixSource("onet_pinned", DEFAULT_OPPORTUNITIES))
        elif kind == "hand_authored":
            path = Path(args.seed_file) if args.seed_file else DEFAULT_SEEDS
            sources.append(MatrixSource("hand_authored", path))
        else:
            sources.append(MatrixSource("none", Path("")))
    ideas = build_ideas(sources)
    batch = render_batch(ideas, sources)
    payload = json.dumps(batch, indent=2, ensure_ascii=False) + "\n"
    output.write_text(payload, encoding="utf-8")
    print(f"wrote {batch['idea_count']} ideas, "
          f"{batch['unique_method_signatures']} unique method signatures, to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())