"""Typed text conformance: catalogs, rules, corrections, escalation, and the resolver.

This is the Loop Engine layer over ``text_conformance_operations``. It adds
the typed records the runtime stores and compares, the layered exception
catalogs, rule proposal from column evidence, the escalation request for a
low-confidence cell, the conformance report, and a
``DeterministicTaskResolver`` so a typed conformance task can complete
before any model call.

Where an exception can live, lowest precedence first:

```text
Exception catalog layers
├── packaged: loop_engine/data/text_conformance_catalogs.yaml
├── task_folder: a catalog file supplied with the task
├── column_evidence: casings the column itself proves
├── inline: parameters on one rule
└── escalation_answers: recorded answers from a model, research, or a person
```

A later layer overrides a mapping entry and extends a list. Every correction
names the entry or signal that decided it.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from importlib.resources import files
from pathlib import Path

from . import text_conformance_operations as operations
from .text_conformance_operations import (ASCII_FOLD_MODES, CATALOG_KINDS, OPERATIONS,
                                          OUTCOMES, SUFFIX_STYLES)

CATALOG_SOURCES = ("packaged", "task_folder", "column_evidence", "inline", "escalation_answers")
ESCALATION_TARGETS = ("model_judgment", "browser_research", "human_review")
TASK_RECORD_TYPE = "text_conformance_task/v1"
RULE_RECORD_TYPE = "conformance_rule/v1"
POLICY_RECORD_TYPE = "conformance_policy/v1"
CORRECTION_RECORD_TYPE = "correction_record/v1"
ESCALATION_RECORD_TYPE = "escalation_request/v1"
REPORT_RECORD_TYPE = "conformance_report/v1"
CATALOG_LAYER_RECORD_TYPE = "exception_catalog_layer/v1"
ESCALATION_CONTRACT_ID = "text_conformance.escalation_response"
RESOLVER_ID = "code_nodes.text_conformance/v1"
DEFAULT_MAX_RESOLVER_ROWS = 100_000
_LIST_KINDS = ("null_sentinels", "preserved_tokens", "minor_words", "lowercase_particles",
               "apostrophe_prefixes")


class TextConformanceError(ValueError):
    """A conformance record, catalog, rule, or task is invalid."""


def _digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     default=str).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Catalog layers
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ExceptionCatalogLayer:
    """One source of exceptions with its provenance and digest."""

    layer_id: str
    source: str
    catalogs: dict
    version: str = "1.0.0"

    def __post_init__(self):
        if self.source not in CATALOG_SOURCES:
            raise TextConformanceError(f"catalog source must be one of {CATALOG_SOURCES}")
        if not self.layer_id.strip():
            raise TextConformanceError("a catalog layer needs an identifier")
        if not isinstance(self.catalogs, dict):
            raise TextConformanceError("catalogs must be a mapping of kinds")
        unknown = [key for key in self.catalogs
                   if key not in CATALOG_KINDS and not key.endswith("_confidence")
                   and key not in ("catalog_id", "version")]
        if unknown:
            raise TextConformanceError(f"unknown catalog kinds {unknown}; valid {CATALOG_KINDS}")
        for kind in _LIST_KINDS:
            if kind in self.catalogs and not isinstance(self.catalogs[kind], (list, tuple)):
                raise TextConformanceError(f"catalog {kind} must be a list")
        for kind in CATALOG_KINDS:
            if kind in self.catalogs and kind not in _LIST_KINDS \
                    and not isinstance(self.catalogs[kind], dict):
                raise TextConformanceError(f"catalog {kind} must be a mapping")

    @property
    def digest(self) -> str:
        return _digest(self.catalogs)

    def to_dict(self) -> dict:
        return {"record_type": CATALOG_LAYER_RECORD_TYPE, "layer_id": self.layer_id,
                "source": self.source, "version": self.version, "digest": self.digest,
                "kinds": sorted(self.catalogs)}


def load_packaged_catalogs() -> ExceptionCatalogLayer:
    """The catalogs shipped inside the package."""
    import yaml
    text = files("loop_engine.data").joinpath("text_conformance_catalogs.yaml").read_text("utf-8")
    data = yaml.safe_load(text)
    return ExceptionCatalogLayer(str(data.get("catalog_id") or "packaged"), CATALOG_SOURCES[0],
                                 {key: value for key, value in data.items()
                                  if key not in ("catalog_id", "version")},
                                 str(data.get("version") or "1.0.0"))


def catalog_layer_from_file(path: str, root: str, *, source: str = CATALOG_SOURCES[1],
                            layer_id: str = "") -> ExceptionCatalogLayer:
    """A catalog file inside ``root``; a path outside the root is refused."""
    root_path = Path(root).resolve()
    file_path = (root_path / path).resolve()
    if root_path not in file_path.parents and file_path != root_path:
        raise TextConformanceError("catalog path escapes the task folder")
    text = file_path.read_text("utf-8")
    if file_path.suffix.lower() in (".yaml", ".yml"):
        import yaml
        data = yaml.safe_load(text)
    else:
        data = json.loads(text)
    if not isinstance(data, dict):
        raise TextConformanceError("a catalog file holds one mapping")
    return ExceptionCatalogLayer(layer_id or file_path.name, source,
                                 {key: value for key, value in data.items()
                                  if key not in ("catalog_id", "version")},
                                 str(data.get("version") or "1.0.0"))


def evidence_layer(column_evidence: dict, layer_id: str = "column_evidence") -> ExceptionCatalogLayer:
    """Column evidence as a catalog layer so its provenance is recorded."""
    exceptions = {}
    for learned in column_evidence.values():
        for key, item in learned.items():
            exceptions[key] = item["form"]
    return ExceptionCatalogLayer(layer_id, CATALOG_SOURCES[2], {"surname_exceptions": exceptions})


def merge_layers(layers) -> dict:
    """Merge layers in order: mappings update, lists union, later wins."""
    merged: dict = {}
    for layer in layers:
        if not isinstance(layer, ExceptionCatalogLayer):
            raise TextConformanceError("merge_layers takes ExceptionCatalogLayer records")
        for kind, value in layer.catalogs.items():
            if isinstance(value, (list, tuple)):
                existing = list(merged.get(kind) or ())
                merged[kind] = existing + [item for item in value if item not in existing]
            elif isinstance(value, dict):
                merged[kind] = {**(merged.get(kind) or {}), **value}
            else:
                merged[kind] = value
    return merged


# ---------------------------------------------------------------------------
# Rules and policy
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ConformanceRule:
    """One operation over named columns with optional thresholds."""

    rule_id: str
    operation: str
    columns: tuple[str, ...]
    parameters: dict = field(default_factory=dict)
    apply_at_or_above: float | None = None
    escalate_below: float | None = None

    def __post_init__(self):
        if not self.rule_id.strip():
            raise TextConformanceError("a rule needs an identifier")
        if self.operation not in OPERATIONS:
            raise TextConformanceError(f"operation must be one of {OPERATIONS}")
        columns = tuple(self.columns)
        if not columns or any(not isinstance(item, str) or not item.strip() for item in columns):
            raise TextConformanceError("a rule names at least one column")
        object.__setattr__(self, "columns", columns)
        try:
            json.dumps(self.parameters, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise TextConformanceError("rule parameters must be strict JSON") from exc
        for name in ("apply_at_or_above", "escalate_below"):
            value = getattr(self, name)
            if value is not None and not (isinstance(value, (int, float)) and 0.0 <= value <= 1.0):
                raise TextConformanceError(f"{name} must lie in [0, 1]")
        if (self.apply_at_or_above is not None and self.escalate_below is not None
                and self.escalate_below > self.apply_at_or_above):
            raise TextConformanceError("escalate_below cannot exceed apply_at_or_above")
        style = self.parameters.get("style")
        if self.operation == OPERATIONS[3] and style is not None and style not in SUFFIX_STYLES:
            raise TextConformanceError(f"suffix style must be one of {SUFFIX_STYLES}")
        fold = self.parameters.get("ascii_fold")
        if self.operation == OPERATIONS[1] and fold is not None and fold not in ASCII_FOLD_MODES:
            raise TextConformanceError(f"ascii_fold must be one of {ASCII_FOLD_MODES}")

    def to_dict(self) -> dict:
        return {"record_type": RULE_RECORD_TYPE, "rule_id": self.rule_id,
                "operation": self.operation, "columns": list(self.columns),
                "parameters": dict(self.parameters),
                "apply_at_or_above": self.apply_at_or_above,
                "escalate_below": self.escalate_below}

    @classmethod
    def from_dict(cls, value) -> "ConformanceRule":
        if not isinstance(value, dict) or value.get("record_type", RULE_RECORD_TYPE) != RULE_RECORD_TYPE:
            raise TextConformanceError(f"a rule record needs record_type {RULE_RECORD_TYPE}")
        return cls(str(value.get("rule_id", "")), str(value.get("operation", "")),
                   tuple(value.get("columns") or ()), dict(value.get("parameters") or {}),
                   value.get("apply_at_or_above"), value.get("escalate_below"))


@dataclass(frozen=True)
class ConformancePolicy:
    """Thresholds and escalation order for a whole conformance run."""

    apply_at_or_above: float = operations.DEFAULT_APPLY_AT_OR_ABOVE
    escalate_below: float = operations.DEFAULT_ESCALATE_BELOW
    escalate_held: bool = False
    escalation_targets: tuple[str, ...] = ESCALATION_TARGETS

    def __post_init__(self):
        for name in ("apply_at_or_above", "escalate_below"):
            value = getattr(self, name)
            if not (isinstance(value, (int, float)) and 0.0 <= value <= 1.0):
                raise TextConformanceError(f"{name} must lie in [0, 1]")
        if self.escalate_below > self.apply_at_or_above:
            raise TextConformanceError("escalate_below cannot exceed apply_at_or_above")
        if type(self.escalate_held) is not bool:
            raise TextConformanceError("escalate_held must be an explicit Boolean")
        targets = tuple(self.escalation_targets)
        if not targets or any(item not in ESCALATION_TARGETS for item in targets):
            raise TextConformanceError(f"escalation targets must be drawn from {ESCALATION_TARGETS}")
        object.__setattr__(self, "escalation_targets", targets)

    def to_dict(self) -> dict:
        return {"record_type": POLICY_RECORD_TYPE, "apply_at_or_above": self.apply_at_or_above,
                "escalate_below": self.escalate_below, "escalate_held": self.escalate_held,
                "escalation_targets": list(self.escalation_targets)}

    @classmethod
    def from_dict(cls, value) -> "ConformancePolicy":
        if not isinstance(value, dict):
            raise TextConformanceError("a policy record is a mapping")
        return cls(value.get("apply_at_or_above", operations.DEFAULT_APPLY_AT_OR_ABOVE),
                   value.get("escalate_below", operations.DEFAULT_ESCALATE_BELOW),
                   value.get("escalate_held", False),
                   tuple(value.get("escalation_targets") or ESCALATION_TARGETS))


# ---------------------------------------------------------------------------
# Corrections, escalation, and the report
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CorrectionRecord:
    """One proposed or applied change to one cell, with its confidence and reasons."""

    row_ref: str
    column: str
    rule_id: str
    operation: str
    input_value: str
    output_value: str
    confidence: float
    reasons: tuple[str, ...]
    outcome: str

    def __post_init__(self):
        if self.outcome not in OUTCOMES:
            raise TextConformanceError(f"outcome must be one of {OUTCOMES}")
        if not (0.0 <= self.confidence <= 1.0):
            raise TextConformanceError("confidence must lie in [0, 1]")
        object.__setattr__(self, "reasons", tuple(self.reasons))

    def to_dict(self) -> dict:
        return {"record_type": CORRECTION_RECORD_TYPE, "row_ref": self.row_ref,
                "column": self.column, "rule_id": self.rule_id, "operation": self.operation,
                "input_value": self.input_value, "output_value": self.output_value,
                "confidence": self.confidence, "reasons": list(self.reasons),
                "outcome": self.outcome}

    @classmethod
    def from_operation(cls, row_ref: str, item: dict) -> "CorrectionRecord":
        return cls(row_ref, item["column"], item["rule_id"], item["operation"], item["input"],
                   item["output"], float(item["confidence"]), tuple(item["reasons"]),
                   item["outcome"])


@dataclass(frozen=True)
class EscalationRequest:
    """A low-confidence cell handed to a model, research, or a person.

    The request carries the candidates the deterministic pass produced, the
    question form to ask, the registered response contract, and the ordered
    targets. It performs no call; a hybrid Loop dispatches it under its own
    authority.
    """

    row_ref: str
    column: str
    input_value: str
    candidates: tuple[tuple[str, float], ...]
    reasons: tuple[str, ...]
    targets: tuple[str, ...]
    task: str = "conform this column"
    contract_id: str = ESCALATION_CONTRACT_ID

    def __post_init__(self):
        if not self.candidates:
            raise TextConformanceError("an escalation carries at least one candidate")
        object.__setattr__(self, "candidates", tuple((str(v), float(c)) for v, c in self.candidates))
        object.__setattr__(self, "reasons", tuple(self.reasons))
        targets = tuple(self.targets)
        if not targets or any(item not in ESCALATION_TARGETS for item in targets):
            raise TextConformanceError(f"escalation targets must be drawn from {ESCALATION_TARGETS}")
        object.__setattr__(self, "targets", targets)

    def question(self) -> str:
        from ..strings.question_engine import core_forms
        options = "; ".join(f"{value} (confidence {confidence:.2f})"
                            for value, confidence in self.candidates)
        return core_forms()["disambiguate_value"].render(
            column=self.column, task=self.task, value=self.input_value, options=options)

    def suggested_output(self):
        from ..core.response_contracts import registered_contract
        return registered_contract(self.contract_id).suggested_output

    def to_dict(self) -> dict:
        return {"record_type": ESCALATION_RECORD_TYPE, "row_ref": self.row_ref,
                "column": self.column, "input_value": self.input_value,
                "candidates": [{"candidate": value, "confidence": confidence}
                               for value, confidence in self.candidates],
                "reasons": list(self.reasons), "targets": list(self.targets),
                "task": self.task, "contract_id": self.contract_id,
                "question": self.question()}


@dataclass(frozen=True)
class ConformanceReport:
    """Counts and digests for one conformance run."""

    rows: int
    per_rule: dict
    overall: dict
    confidence_histogram: tuple[int, ...]
    reason_counts: dict
    rules_digest: str
    catalog_digest: str
    idempotent: bool | None = None

    def to_dict(self) -> dict:
        body = {"record_type": REPORT_RECORD_TYPE, "rows": self.rows, "per_rule": self.per_rule,
                "overall": self.overall, "confidence_histogram": list(self.confidence_histogram),
                "reason_counts": self.reason_counts, "rules_digest": self.rules_digest,
                "catalog_digest": self.catalog_digest, "idempotent": self.idempotent}
        return {**body, "content_digest": _digest(body)}

    @property
    def complete(self) -> bool:
        """True when nothing was held or escalated and the pass was idempotent."""
        return (self.overall.get(OUTCOMES[1], 0) == 0 and self.overall.get(OUTCOMES[2], 0) == 0
                and self.idempotent is True)


@dataclass(frozen=True)
class ConformanceRun:
    report: ConformanceReport
    output_rows: tuple[dict, ...]
    corrections: tuple[CorrectionRecord, ...]
    escalations: tuple[EscalationRequest, ...]
    evidence_layer: ExceptionCatalogLayer | None


def _escalation_for(record: CorrectionRecord, policy: ConformancePolicy, task: str) -> EscalationRequest:
    candidates = [(record.output_value, record.confidence)]
    if record.output_value != record.input_value:
        candidates.append((record.input_value, round(1.0 - record.confidence, 3)))
    return EscalationRequest(record.row_ref, record.column, record.input_value, tuple(candidates),
                             record.reasons, policy.escalation_targets, task=task)


def run_conformance(rows, rules, policy: ConformancePolicy | None = None, catalogs: dict | None = None,
                    *, learn_evidence: bool = True, task: str = "conform this column") -> ConformanceRun:
    """Apply typed rules to rows in memory and return the typed run.

    The first pass learns column evidence when asked; the second applies the
    rules; a third re-applies them to the output to prove idempotence.
    """
    policy = policy or ConformancePolicy()
    rules = tuple(rules)
    if any(not isinstance(item, ConformanceRule) for item in rules) or not rules:
        raise TextConformanceError("run_conformance takes at least one ConformanceRule")
    rows = [dict(row) for row in rows]
    catalogs = dict(catalogs if catalogs is not None else merge_layers([load_packaged_catalogs()]))
    columns = sorted({column for rule in rules for column in rule.columns})
    evidence = operations.learn_column_evidence(rows, columns) if learn_evidence else {}
    layer = evidence_layer(evidence) if evidence else None
    rule_dicts = [rule.to_dict() for rule in rules]
    policy_dict = policy.to_dict()
    outputs, corrections, escalations = [], [], []
    for index, row in enumerate(rows):
        row_ref = str(row.get("row_ref") or index)
        output, items = operations.apply_rules_to_row(row, rule_dicts, catalogs, policy_dict, evidence)
        outputs.append(output)
        for item in items:
            record = CorrectionRecord.from_operation(row_ref, item)
            corrections.append(record)
            if record.outcome == OUTCOMES[2] or (policy.escalate_held and record.outcome == OUTCOMES[1]):
                escalations.append(_escalation_for(record, policy, task))
    again = second_pass_changes(outputs, rule_dicts, catalogs, policy_dict, evidence)
    summary = operations.summarize([item.to_dict() | {"input": item.input_value} for item in corrections],
                                   rule_dicts)
    report = ConformanceReport(len(rows), summary["per_rule"], summary["overall"],
                               tuple(summary["confidence_histogram"]), summary["reason_counts"],
                               _digest(rule_dicts), _digest(catalogs), idempotent=again == 0)
    return ConformanceRun(report, tuple(outputs), tuple(corrections), tuple(escalations), layer)


def second_pass_changes(rows, rule_dicts, catalogs: dict, policy_dict: dict, evidence: dict) -> int:
    """How many corrections a second pass over ``rows`` would still apply.

    Zero over a run's outputs proves the pass is idempotent; a positive count
    over the inputs proves the second pass really runs the rules.
    """
    again = 0
    for row in rows:
        _, items = operations.apply_rules_to_row(row, rule_dicts, catalogs, policy_dict, evidence)
        again += sum(1 for item in items if item["outcome"] == OUTCOMES[0])
    return again


# ---------------------------------------------------------------------------
# Rule proposal from evidence
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RuleProposal:
    rule: ConformanceRule
    reasons: tuple[str, ...]

    def to_dict(self) -> dict:
        return {"record_type": "conformance_rule_proposal/v1", "rule": self.rule.to_dict(),
                "reasons": list(self.reasons)}


def propose_rules(profiles: dict, *, minimum_share: float = 0.05) -> tuple[RuleProposal, ...]:
    """Rules the column profiles justify, each with the evidence that proposed it.

    A proposal is a candidate for the solutioning space to keep, change, or
    drop. Whitespace and Unicode rules come first because later operations
    read cleaned text.
    """
    proposals: list[RuleProposal] = []
    ordered = sorted(profiles)
    whitespace = [c for c in ordered if profiles[c]["shares"].get("whitespace_issue", 0) > 0
                  or profiles[c]["shares"].get("nonstandard_space_or_zero_width", 0) > 0]
    if whitespace:
        proposals.append(RuleProposal(ConformanceRule("whitespace", OPERATIONS[0], tuple(whitespace)),
                                      tuple(f"{c}: whitespace issues in {profiles[c]['shares'].get('whitespace_issue', 0):.0%} of values" for c in whitespace)))
    unicode_columns = [c for c in ordered if profiles[c]["shares"].get("non_ascii", 0) > 0]
    if unicode_columns:
        proposals.append(RuleProposal(ConformanceRule("unicode", OPERATIONS[1], tuple(unicode_columns)),
                                      tuple(f"{c}: non-ASCII in {profiles[c]['shares'].get('non_ascii', 0):.0%} of values" for c in unicode_columns)))
    for column in ordered:
        shares = profiles[column]["shares"]
        if shares.get("email_like", 0) >= 0.5:
            proposals.append(RuleProposal(ConformanceRule(f"email.{column}", OPERATIONS[5], (column,)),
                                          (f"{column}: {shares['email_like']:.0%} email-like values",)))
            continue
        if shares.get("url_like", 0) >= 0.5:
            proposals.append(RuleProposal(ConformanceRule(f"website.{column}", OPERATIONS[6], (column,)),
                                          (f"{column}: {shares['url_like']:.0%} URL-like values",)))
            continue
        if shares.get("phone_like", 0) >= 0.5:
            proposals.append(RuleProposal(ConformanceRule(f"phone.{column}", OPERATIONS[4], (column,)),
                                          (f"{column}: {shares['phone_like']:.0%} phone-like values",)))
            continue
        case_share = shares.get("all_upper", 0) + shares.get("all_lower", 0)
        mixed = shares.get("mixed_case", 0) > 0
        if shares.get("all_upper", 0) >= minimum_share or (shares.get("all_lower", 0) >= minimum_share and mixed):
            proposals.append(RuleProposal(ConformanceRule(f"case.{column}", OPERATIONS[2], (column,)),
                                          (f"{column}: {case_share:.0%} of values carry no case information"
                                           + ("; other values are mixed case" if mixed else ""),)))
        if shares.get("legal_suffix_like", 0) >= minimum_share:
            proposals.append(RuleProposal(ConformanceRule(f"suffix.{column}", OPERATIONS[3], (column,)),
                                          (f"{column}: {shares['legal_suffix_like']:.0%} of values end in a legal suffix",)))
    return tuple(proposals)


# ---------------------------------------------------------------------------
# Resolver and capability surface
# ---------------------------------------------------------------------------

def _rows_from_task(task: dict, root: Path) -> list[dict]:
    if "rows" in task:
        rows = task["rows"]
        if not isinstance(rows, list) or any(not isinstance(item, dict) for item in rows):
            raise TextConformanceError("task rows must be a list of mappings")
        return rows
    path = str(task.get("input_path") or "")
    if not path:
        raise TextConformanceError("a conformance task supplies rows or an input_path")
    file_path = (root / path).resolve()
    if root not in file_path.parents:
        raise TextConformanceError("input_path escapes the workspace root")
    import csv
    limit = int(task.get("max_rows") or DEFAULT_MAX_RESOLVER_ROWS)
    with file_path.open("r", encoding="utf-8", newline="") as handle:
        rows = []
        for row in csv.DictReader(handle):
            rows.append(row)
            if len(rows) > limit:
                raise TextConformanceError(
                    f"input exceeds max_rows {limit}; export the standalone solution for large files")
    return rows


class TextConformanceResolver:
    """Exact resolver for a typed ``text_conformance_task/v1`` record.

    ``supports`` reads only the record type, never prose. ``execute`` returns
    ``verified`` True only when the report is complete: nothing held, nothing
    escalated, and the pass idempotent. Otherwise the typed escalations are
    the next action for a hybrid Loop.
    """

    resolver_id = RESOLVER_ID

    def __init__(self, workspace_root: str = "."):
        self.workspace_root = str(workspace_root)

    def _parse(self, task: str) -> dict | None:
        try:
            value = json.loads(task)
        except (TypeError, ValueError):
            return None
        return value if isinstance(value, dict) and value.get("record_type") == TASK_RECORD_TYPE else None

    def supports(self, task: str) -> bool:
        return self._parse(task) is not None

    def execute(self, task: str) -> dict:
        record = self._parse(task)
        if record is None:
            raise TextConformanceError("not a text conformance task")
        root = Path(self.workspace_root).resolve()
        rules = tuple(ConformanceRule.from_dict(item) for item in record.get("rules") or ())
        policy = ConformancePolicy.from_dict(record.get("policy") or {})
        layers = [load_packaged_catalogs()]
        for item in record.get("catalog_files") or ():
            layers.append(catalog_layer_from_file(str(item), str(root)))
        if isinstance(record.get("inline_catalogs"), dict):
            layers.append(ExceptionCatalogLayer("inline", CATALOG_SOURCES[3], record["inline_catalogs"]))
        run = run_conformance(_rows_from_task(record, root), rules, policy, merge_layers(layers),
                              task=str(record.get("task") or "conform this column"))
        return {"verified": run.report.complete, "report": run.report.to_dict(),
                "output_rows": list(run.output_rows),
                "corrections": [item.to_dict() for item in run.corrections],
                "escalations": [item.to_dict() for item in run.escalations],
                "catalog_layers": [layer.to_dict() for layer in layers]
                + ([run.evidence_layer.to_dict()] if run.evidence_layer else [])}


def text_conformance_run_endpoint(**kw) -> dict:
    """The capability directory ``run`` endpoint over in-memory rows."""
    rules = tuple(ConformanceRule.from_dict(item) if isinstance(item, dict) else item
                  for item in kw.get("rules") or ())
    policy = kw.get("policy")
    if isinstance(policy, dict):
        policy = ConformancePolicy.from_dict(policy)
    run = run_conformance(kw.get("rows") or (), rules, policy, kw.get("catalogs"))
    return {"report": run.report.to_dict(), "output_rows": list(run.output_rows),
            "corrections": [item.to_dict() for item in run.corrections],
            "escalations": [item.to_dict() for item in run.escalations]}


def text_conformance_surface():
    """The typed surface registration a capability directory accepts.

    Pass it as ``default_directory(surfaces=(text_conformance_surface(),))``.
    The registration lives here so core never imports this package.
    """
    from ..core.capability_directory import CapabilityHandshake, Endpoint, SurfaceRegistration
    return SurfaceRegistration(CapabilityHandshake(
        "text_conformance", "code_node_registry",
        "typed text conformance: profile columns, propose rules, normalize case, "
        "legal suffixes, whitespace, Unicode, phones, emails, and websites with a "
        "confidence and named reasons per correction; stages low-confidence cells "
        "for escalation without calling a model",
        operations=("run", "validate"), accepts=("code",), returns=("code",),
        input_schema=TASK_RECORD_TYPE, output_schema=REPORT_RECORD_TYPE),
        (Endpoint("run", text_conformance_run_endpoint),
         Endpoint("validate", text_conformance_validate_endpoint)))


def text_conformance_validate_endpoint(**kw) -> dict:
    """The ``validate`` endpoint: profile columns and propose rules without changing data."""
    rows = list(kw.get("rows") or ())
    catalogs = kw.get("catalogs") or merge_layers([load_packaged_catalogs()])
    columns = list(kw.get("columns") or (sorted(rows[0]) if rows else ()))
    profiles = {column: operations.profile_column([row.get(column) for row in rows], catalogs)
                for column in columns}
    return {"profiles": profiles,
            "proposals": [item.to_dict() for item in propose_rules(profiles)],
            "duckdb_sql": {column: operations.duckdb_profile_sql("rows", column) for column in columns}}


def self_test() -> dict:
    from .text_conformance_checks import run_checks
    return run_checks()
