"""Runtime contracts — executable truth at every boundary, kept distinct from
intelligence.

Owner correction (2026-08-23): a runtime contract is NOT ordinary intelligence.
Intelligence is learned and may be uncertain; a runtime contract must be exact
enough to admit, reject, execute, and verify a graph.  The clean separation:

  * CONTRACT DEFINITION — defines what must be true (columns, allowed values,
    types, nullability, ranges, cardinality).  Immutable, versioned, own registry.
  * VALIDATOR — a deterministic node that checks whether it is true.
  * ADAPTER — an explicit node that converts a known incompatible form into the
    required one.  The graph never silently coerces.
  * CONTRACT CANDIDATE — a proposed contract inferred by intelligence; it becomes
    a registered definition only after review (evidence-gated promotion).

The governing rule: a contract defines the boundary, a validator enforces it, an
adapter explicitly bridges it, and intelligence may propose or improve a boundary
but cannot silently redefine one during execution.

This corrects a conflation: [[decision_schemas.py]] is INTELLIGENCE (it biases the
model to PRODUCE fields — a prompt-side nudge); a ContractDefinition here is TRUTH
(it decides whether the produced result is VALID — deterministic admission).  They
may describe the same fields, but their authority is different.  Contracts live in
their OWN registry (distinct from [[intelligence_registry.py]]) while sharing the
one search DAG.  The four constraint CLASSES stay distinct and are never conflated.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, asdict
from typing import Sequence

# The four constraint classes — kept DISTINCT (the owner's rule).  Only
# hard_contract is executable truth enforced here; the others live elsewhere.
CONSTRAINT_CLASSES = ("hard_contract", "soft_constraint", "policy_constraint",
                      "learned_preference")
CONSTRAINT_OWNER = {
    "hard_contract": "runtime_contracts (executable truth; admit/reject)",
    "soft_constraint": "review_mode / measurement (quality; weaker not invalid)",
    "policy_constraint": "config / operating_profile (authority, not data shape)",
    "learned_preference": "biases / follow_up (a demotable historical prior)",
}
OUTPUT_TYPES = ("table", "object", "enum", "scalar")
# "any" = presence/nullability/uniqueness are still checked, the value TYPE is not
# (for a required-but-free-form field, e.g. a reasoning field bridged from an
# intelligence decision schema).
DATA_TYPES = ("string", "int", "float", "bool", "array", "object", "any")
_SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def _digest(obj: dict) -> str:
    import json
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:16]


@dataclass(frozen=True)
class FieldSpec:
    """One column (table) or property (object)."""
    name: str
    data_type: str = "string"
    nullable: bool = True
    unique: bool = False
    allowed_values: tuple = ()          # closed enumeration, if any
    minimum: "float | None" = None
    maximum: "float | None" = None
    min_length: "int | None" = None

    def __post_init__(self):
        if self.data_type not in DATA_TYPES:
            raise ValueError(f"data_type must be one of {DATA_TYPES}")


def _type_ok(v, dt: str) -> bool:
    if dt == "string":
        return isinstance(v, str)
    if dt == "int":
        return isinstance(v, int) and not isinstance(v, bool)
    if dt == "float":
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    if dt == "bool":
        return isinstance(v, bool)
    if dt == "array":
        return isinstance(v, (list, tuple))
    if dt == "object":
        return isinstance(v, dict)
    if dt == "any":
        return True
    return False


@dataclass
class Violation:
    kind: str                           # missing_field | unexpected_field | ...
    where: str
    detail: str


@dataclass
class ContractValidationResult:
    valid: bool
    violations: tuple = ()
    checked: str = ""

    def summary(self) -> str:
        if self.valid:
            return f"valid against {self.checked}"
        return (f"INVALID against {self.checked}: "
                + "; ".join(f"{v.kind}@{v.where}" for v in self.violations))


@dataclass
class ContractDefinition:
    """The immutable, versioned boundary spec."""
    contract_id: str
    output_type: str
    version: str = "1.0.0"
    role: str = "output"                # input | output
    fields: tuple = ()                  # for table/object
    additional_fields_allowed: bool = False
    allowed_values: tuple = ()          # for enum
    minimum: "float | None" = None      # for scalar
    maximum: "float | None" = None
    row_count_min: int = 0
    digest: str = ""

    def __post_init__(self):
        if self.output_type not in OUTPUT_TYPES:
            raise ValueError(f"output_type must be one of {OUTPUT_TYPES}")
        if not _SEMVER.match(self.version):
            raise ValueError("version must be semver x.y.z")
        self.digest = _digest({"id": self.contract_id, "v": self.version,
                               "t": self.output_type,
                               "f": [asdict(f) for f in self.fields],
                               "e": list(self.allowed_values),
                               "add": self.additional_fields_allowed})

    # --- the validator node (deterministic) --------------------------------

    def validate(self, value) -> ContractValidationResult:
        v: list = []
        if self.output_type == "enum":
            if value not in self.allowed_values:
                v.append(Violation("invalid_enum_value", self.contract_id,
                                   f"{value!r} not in {list(self.allowed_values)}"))
        elif self.output_type == "scalar":
            v += self._check_scalar(value, self.contract_id)
        elif self.output_type == "object":
            v += self._check_record(value, "object")
        elif self.output_type == "table":
            rows = value if isinstance(value, list) else None
            if rows is None:
                v.append(Violation("type_mismatch", self.contract_id,
                                   "table contract expects a list of rows"))
            else:
                if len(rows) < self.row_count_min:
                    v.append(Violation("cardinality", self.contract_id,
                                       f"{len(rows)} rows < min {self.row_count_min}"))
                for i, row in enumerate(rows):
                    v += self._check_record(row, f"row{i}")
                v += self._check_unique(rows)
        return ContractValidationResult(not v, tuple(v),
                                        f"{self.contract_id}@{self.version}")

    def _check_scalar(self, value, where) -> list:
        out = []
        if self.minimum is not None and (not isinstance(value, (int, float))
                                         or value < self.minimum):
            out.append(Violation("constraint", where, f"{value} < {self.minimum}"))
        if self.maximum is not None and (not isinstance(value, (int, float))
                                         or value > self.maximum):
            out.append(Violation("constraint", where, f"{value} > {self.maximum}"))
        return out

    def _check_record(self, rec, where) -> list:
        out = []
        if not isinstance(rec, dict):
            return [Violation("type_mismatch", where, "expected an object/dict")]
        names = {f.name for f in self.fields}
        for f in self.fields:
            if f.name not in rec:
                out.append(Violation("missing_field", where, f.name))
                continue
            val = rec[f.name]
            if val is None:
                if not f.nullable:
                    out.append(Violation("null_violation", f"{where}.{f.name}", ""))
                continue
            if not _type_ok(val, f.data_type):
                out.append(Violation("type_mismatch", f"{where}.{f.name}",
                                     f"expected {f.data_type}"))
                continue
            if f.allowed_values and val not in f.allowed_values:
                out.append(Violation("invalid_enum_value", f"{where}.{f.name}",
                                     f"{val!r} not in {list(f.allowed_values)}"))
            if f.minimum is not None and val < f.minimum:
                out.append(Violation("constraint", f"{where}.{f.name}",
                                     f"{val} < {f.minimum}"))
            if f.maximum is not None and val > f.maximum:
                out.append(Violation("constraint", f"{where}.{f.name}",
                                     f"{val} > {f.maximum}"))
            if f.min_length is not None and len(str(val)) < f.min_length:
                out.append(Violation("constraint", f"{where}.{f.name}",
                                     "shorter than min_length"))
        if not self.additional_fields_allowed:
            for k in rec:
                if k not in names:
                    out.append(Violation("unexpected_field", where, k))
        return out

    def _check_unique(self, rows) -> list:
        out = []
        for f in self.fields:
            if not f.unique:
                continue
            seen, dup = set(), False
            for r in rows:
                if isinstance(r, dict) and f.name in r:
                    if r[f.name] in seen:
                        dup = True
                    seen.add(r[f.name])
            if dup:
                out.append(Violation("uniqueness", f.name, "duplicate values"))
        return out

    def resource(self):
        """Emit the canonical Resource — a contract is a code node that validates
        (a published definition is registered / database tier)."""
        from ..core.asset_lifecycle import Resource
        return Resource(asset_id=f"{self.contract_id}.{self.version}",
                        asset_class="code", role="contract",
                        content=self.as_model_instruction(), lifecycle="registered",
                        version=self.version, provenance="runtime_contracts")

    def as_model_instruction(self) -> str:
        """A contract may ALSO steer the prompt toward compliance — but it remains
        the enforcement authority, not a mere suggestion."""
        if self.output_type == "enum":
            return (f"Return exactly one of {list(self.allowed_values)} "
                    f"(contract {self.contract_id}).")
        if self.output_type in ("table", "object"):
            cols = ", ".join(
                f"{f.name}:{f.data_type}"
                + (f"∈{list(f.allowed_values)}" if f.allowed_values else "")
                for f in self.fields)
            kind = "each row" if self.output_type == "table" else "the object"
            extra = "" if self.additional_fields_allowed else "; no extra fields"
            return f"{kind} must have exactly [{cols}]{extra} (contract {self.contract_id})."
        return f"Return a scalar within [{self.minimum},{self.maximum}]."


# ---------------------------------------------------------------------------
# The adapter node — explicit, recorded, never silent.
# ---------------------------------------------------------------------------

_ADAPTER_OPS = ("rename", "cast", "map_values", "reorder", "fill_missing")


@dataclass
class ContractAdapter:
    """An explicit, authorized transformation from a known form to the required
    one.  Applying it RECORDS what it did — the graph never silently coerces."""
    adapter_id: str
    ops: tuple                          # tuple of (op, params) — declarative
    authorized: bool = True

    def apply(self, rows) -> dict:
        if not self.authorized:
            raise PermissionError(f"adapter {self.adapter_id} is not authorized")
        data = [dict(r) for r in rows] if isinstance(rows, list) else dict(rows)
        changes: list = []
        for op, params in self.ops:
            if op not in _ADAPTER_OPS:
                raise ValueError(f"unknown adapter op {op!r}; valid {_ADAPTER_OPS}")
            recs = data if isinstance(data, list) else [data]
            for r in recs:
                if op == "rename":
                    for old, new in params.items():
                        if old in r:
                            r[new] = r.pop(old)
                            changes.append(f"rename {old}->{new}")
                elif op == "cast":
                    for col, dt in params.items():
                        if col in r and r[col] is not None:
                            r[col] = {"float": float, "int": int,
                                      "string": str}.get(dt, lambda x: x)(r[col])
                            changes.append(f"cast {col}->{dt}")
                elif op == "map_values":
                    for col, mapping in params.items():
                        if col in r and r[col] in mapping:
                            changes.append(f"map {col}:{r[col]}->{mapping[r[col]]}")
                            r[col] = mapping[r[col]]
                elif op == "fill_missing":
                    for col, default in params.items():
                        if col not in r or r[col] is None:
                            r[col] = default
                            changes.append(f"fill {col}={default}")
                elif op == "reorder":
                    order = params
                    for idx in range(len(recs)):
                        recs[idx] = {k: recs[idx][k] for k in order
                                     if k in recs[idx]}
                    data = recs if isinstance(data, list) else recs[0]
        return {"record_type": "adapter_result/v1", "adapter": self.adapter_id,
                "value": data, "changes": changes}


# ---------------------------------------------------------------------------
# Contract candidate — intelligence PROPOSES; promotion REGISTERS.
# ---------------------------------------------------------------------------


@dataclass
class ContractCandidate:
    """A contract inferred by intelligence — not yet executable truth."""
    proposed: ContractDefinition
    rationale: str = ""
    originating_run: str = ""
    examples: tuple = ()
    counterexamples: tuple = ()
    confidence: float = 0.5
    promotion_status: str = "proposed"

    def promote(self, *, evidence: Sequence) -> ContractDefinition:
        """Register the candidate as executable truth — evidence-gated."""
        if not evidence:
            raise PromotionRefused(
                f"contract {self.proposed.contract_id!r} cannot become executable "
                "truth without evidence (validated examples/counterexamples)")
        self.promotion_status = "registered"
        return self.proposed


class PromotionRefused(RuntimeError):
    """Raised when a proposed contract is registered without evidence."""


class ContractRegistry:
    """The contract registry — distinct authority from the intelligence registry,
    shares the one search surface.  Contracts are immutable after publication;
    a change is a new version."""

    def __init__(self):
        self._by_key: dict = {}         # (id, version) -> definition

    def register(self, c: ContractDefinition) -> ContractDefinition:
        key = (c.contract_id, c.version)
        if key in self._by_key and self._by_key[key].digest != c.digest:
            raise ValueError(f"{key} already published with a different digest — "
                             "publish a new version instead of mutating one")
        self._by_key[key] = c
        return c

    def get(self, contract_id: str, version: str = "") -> ContractDefinition:
        if version:
            return self._by_key[(contract_id, version)]
        vers = [k for k in self._by_key if k[0] == contract_id]
        if not vers:
            raise KeyError(f"no contract {contract_id!r}")
        return self._by_key[max(vers, key=lambda k: k[1])]

    def all(self) -> list:
        return list(self._by_key.values())

    def records(self) -> list:
        from ..core.store_serve import StoreRecord
        recs = []
        for c in self._by_key.values():
            recs.append(StoreRecord(
                record_id=f"contract.{c.contract_id}.{c.version}", kind="strategy",
                title=f"Contract: {c.contract_id} ({c.output_type})",
                body={"version": c.version, "digest": c.digest,
                      "output_type": c.output_type, "role": c.role,
                      "instruction": c.as_model_instruction()},
                tags=("runtime_contract", "executable_truth", c.output_type,
                      c.contract_id), tier="core"))
        return recs


# ---------------------------------------------------------------------------
# Self-test — deterministic, no network.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    # A table contract: customer_id (str, unique), prediction (enum), confidence (0..1)
    tc = ContractDefinition(
        "prediction-output", "table", role="output",
        fields=(FieldSpec("customer_id", "string", nullable=False, unique=True),
                FieldSpec("prediction", "string", nullable=False,
                          allowed_values=("approve", "review", "reject")),
                FieldSpec("confidence", "float", nullable=False,
                          minimum=0.0, maximum=1.0)),
        additional_fields_allowed=False, row_count_min=1)

    # 1. a valid table passes.
    good = tc.validate([{"customer_id": "c1", "prediction": "approve",
                         "confidence": 0.9}])
    check("valid_table_passes", good.valid, good.summary())

    # 2. every violation kind the owner named is caught deterministically.
    bad = tc.validate([
        {"customer_id": "c1", "prediction": "MAYBE", "confidence": 1.4,
         "extra": 1},                                   # enum + range + unexpected
        {"prediction": "approve", "confidence": None},  # missing id + null conf
        {"customer_id": "c1", "prediction": "reject", "confidence": 0.2}])  # dup id
    kinds = {v.kind for v in bad.violations}
    check("validator_catches_every_violation_kind",
          not bad.valid
          and {"invalid_enum_value", "constraint", "unexpected_field",
               "missing_field", "null_violation", "uniqueness"} <= kinds,
          f"caught: {sorted(kinds)}")

    # 3. a closed enumeration contract (only 4 permitted values).
    ec = ContractDefinition("decision-enum", "enum",
                            allowed_values=("accept", "reject", "defer", "abstain"))
    check("closed_enum_admits_and_rejects",
          ec.validate("defer").valid and not ec.validate("maybe").valid,
          "only the four permitted values are valid")

    # 4. the ADAPTER bridges a known form EXPLICITLY and records what it did.
    ad = ContractAdapter("normalize-review", ops=(
        ("map_values", {"prediction": {"needs_review": "review"}}),
        ("cast", {"confidence": "float"})))
    out = ad.apply([{"customer_id": "c9", "prediction": "needs_review",
                     "confidence": "0.7"}])
    after = tc.validate(out["value"])
    check("adapter_bridges_explicitly_and_is_recorded",
          after.valid and any("map prediction" in c for c in out["changes"]),
          f"changes: {out['changes']}")

    # 5. silent coercion never happens: without the adapter, the bad form is
    # REJECTED, not quietly fixed.
    raw = tc.validate([{"customer_id": "c9", "prediction": "needs_review",
                        "confidence": "0.7"}])
    check("no_silent_coercion_bad_form_is_rejected",
          not raw.valid,
          "the un-adapted value fails validation rather than being coerced")

    # 6. intelligence PROPOSES a contract; promotion is evidence-gated.
    cand = ContractCandidate(
        ContractDefinition("inferred-decision", "enum",
                           allowed_values=("accept", "reject", "defer")),
        rationale="the model kept emitting one of three labels")
    refused = False
    try:
        cand.promote(evidence=())
    except PromotionRefused:
        refused = True
    reg_def = cand.promote(evidence=["20 validated rows", "0 counterexamples"])
    check("intelligence_proposes_promotion_registers_with_evidence",
          refused and cand.promotion_status == "registered"
          and reg_def.output_type == "enum",
          "a proposed contract becomes executable truth only on evidence")

    # 7. contracts are versioned + immutable; a changed digest needs a new version.
    reg = ContractRegistry()
    reg.register(tc)
    clash = False
    try:
        reg.register(ContractDefinition("prediction-output", "enum",
                                        version="1.0.0",
                                        allowed_values=("a", "b")))
    except ValueError:
        clash = True
    check("contracts_are_immutable_after_publication", clash,
          "re-publishing the same id+version with a different digest is refused")

    # 8. the four constraint CLASSES stay distinct (never conflated).
    check("constraint_classes_are_distinct",
          len(CONSTRAINT_CLASSES) == 4
          and "authority" in CONSTRAINT_OWNER["policy_constraint"]
          and CONSTRAINT_OWNER["hard_contract"].startswith("runtime_contracts"),
          "hard contract / soft constraint / policy / preference each own a lane")

    # 9. contracts are searchable through the ONE search DAG (own registry).
    from ..core.store_serve import SolverStore
    store = SolverStore(core_records=reg.records())
    hit = store.search("required output columns prediction confidence",
                       kind="strategy")
    check("contracts_are_searchable_through_the_one_dag",
          hit["hits"] and any("contract." in h["record_id"]
                              for h in hit["hits"]),
          "the contract registry shares the one search surface")

    flexible = ContractDefinition(
        "flexible-fields", "object", fields=(
            FieldSpec("items", "array", nullable=False),
            FieldSpec("metadata", "object", nullable=False),
            FieldSpec("value", "any", nullable=False)))
    good_flexible = flexible.validate(
        {"items": [], "metadata": {"source": "test"}, "value": 7})
    bad_flexible = flexible.validate(
        {"items": "none", "metadata": [], "value": 7})
    check("array_object_and_any_field_types_validate_correctly",
          good_flexible.valid and not bad_flexible.valid
          and sum(v.kind == "type_mismatch"
                  for v in bad_flexible.violations) == 2)

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "runtime_contracts_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
