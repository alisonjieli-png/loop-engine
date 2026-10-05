"""The research_query_planner slot: a declared product of dimensions as a lazy, fair, resumable stream of queries.

```text
research_query_plan/v1 (plans/*.json)
└── products                one executor, a weight, the dimensions it multiplies, their null shares and filters
    └── research_query/v1   one query: product, k, assignment (value id or null per dimension), the executor's
                            rendered request, query_id = SHA-256 of executor + rendered request
```

Engines of the slot (selected by the plan's `engine` field; one slot, swappable without changing the runner):
- `factorized_multiplier` (Baltor-native, this module): the product as mixed residues. Each dimension becomes a
  virtual list (each value repeated by its weight, the null value repeated to its declared share, padded so the
  list lengths are pairwise coprime). Query k takes, in every dimension d, entry (a_d * k + b_d) mod n_d. By the
  Chinese remainder theorem k -> (k mod n_1, ..., k mod n_D) is a bijection of [0, n_1 * ... * n_D), and an affine
  map with a_d coprime to n_d keeps it one, so no combination repeats before the whole product is spent, and
  every value of every dimension comes round once in each n_d queries: every slice of the product is covered
  early, and no dimension exhausts the budget before the others move. The cursor is k.
- `matrix_pages` (adapter): the October 1 query matrix (`knowledge_radar.query_matrix.page`), whose coprime
  traversal and plan binding this engine generalises; kept selectable behind the same edge.
- `queue_import` (adapter, importers.py): finite queues of planned searches imported from earlier research,
  rotated round-robin over their declared keys (SDG x country) instead of file order.

Compatibility is decided twice. A value the executor cannot express (a licence it cannot filter by, a format with
no rendering for that source) never enters the product, and the count is reported. A combination that breaks a
library rule, or renders to an empty request, is examined and skipped with its reason. Null values stay: a null
geography is the global baseline query.

A query is planned, then executed only by the runner, and counts as executed only once its raw response is stored
(evidence.py). The planner never repeats a query the ledger holds as executed inside its refresh period.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType

from knowledge_radar.query_matrix import digest, plain

from .dimensions import Dimension, DimensionError, Library

PLAN = "research_query_plan/v1"
QUERY = "research_query/v1"
CURSOR = "research_query_cursor/v1"
ENGINES = ("factorized_multiplier", "matrix_pages", "queue_import")
PAD = object()
GOLDEN = (math.sqrt(5) - 1) / 2
MAXIMUM_PRODUCTS = 200
MAXIMUM_AXES = 8
#: Gates every planned query carries: a query is a probe, never a package, a licence decision or a publication.
GATES = MappingProxyType({"executed": "not_yet", "licence_decision": "not_made_by_the_planner",
                          "package_identity": "never_a_query_permutation", "publication": "not_authorized"})
IMPLEMENTATION_FILES = ("planner.py", "dimensions.py", "executors.py")


class PlanError(ValueError):
    """The plan broke a rule before any query was produced."""


def implementation_digest() -> str:
    folder = Path(__file__).resolve().parent
    return digest({name: hashlib.sha256((folder / name).read_bytes()).hexdigest() for name in IMPLEMENTATION_FILES})


@dataclass(frozen=True)
class Axis:
    dimension: Dimension
    entries: tuple  # Value, None (the null value) or PAD
    size: int
    stride: int
    phase: int
    values_used: int
    values_not_expressible: int
    null_entries: int

    def entry(self, k: int):
        return self.entries[(self.stride * k + self.phase) % self.size]


@dataclass(frozen=True)
class Product:
    id: str
    executor_id: str
    weight: int
    axes: tuple
    params: MappingProxyType
    refresh_days: int
    follow_pages: int
    digest: str
    declaration: MappingProxyType = field(repr=False)

    @property
    def total(self) -> int:
        return math.prod(axis.size for axis in self.axes)

    def assignment(self, k: int):
        out = {}
        for axis in self.axes:
            entry = axis.entry(k)
            if entry is PAD:
                return None
            out[axis.dimension.id] = entry
        return out


@dataclass(frozen=True)
class PlannedQuery:
    product_id: str
    executor_id: str
    k: int
    assignment: dict
    request: dict
    query_id: str
    page: int = 1
    parent_query_id: str = ""
    origin: str = "product"

    def record(self) -> dict:
        return {"record_type": QUERY, "product_id": self.product_id, "executor_id": self.executor_id, "k": self.k,
                "assignment": {name: (value.id if value is not None else None) for name, value in self.assignment.items()},
                "request": self.request, "query_id": self.query_id, "page": self.page,
                "parent_query_id": self.parent_query_id, "origin": self.origin, "gates": dict(GATES)}


def _coprime_with_all(n: int, sizes: list) -> bool:
    return all(math.gcd(n, other) == 1 for other in sizes)


def _stride(n: int) -> int:
    stride = max(1, round(n * GOLDEN))
    while math.gcd(stride, n) != 1:
        stride += 1
    return stride % n or 1


def build_axis(dimension: Dimension, *, null_share: int, accepts, where, earlier_sizes: list, salt: str) -> Axis:
    """One dimension's virtual list: weighted values the executor can express, nulls to their share, coprime size."""
    values, not_expressible = [], 0
    for value in dimension.values:
        if where and not where(value):
            continue
        if not accepts(dimension, value):
            not_expressible += 1
            continue
        values.append(value)
    if not values and null_share == 0:
        raise PlanError("dimension_has_no_expressible_value:" + dimension.id)
    entries = [value for value in values for _ in range(value.weight)]
    base = len(entries)
    nulls = 0
    if null_share:
        nulls = max(1, math.ceil(null_share * base / (100 - null_share))) if base else 1
    entries = entries + [None] * nulls
    # Spread the nulls through the list instead of leaving them as one run at the end.
    if nulls and base:
        spread, step = [], (base + nulls) / nulls
        positions = {int(index * step) for index in range(nulls)}
        values_iter = iter(entries[:base])
        for index in range(base + nulls):
            spread.append(None if index in positions else next(values_iter, None))
        entries = spread
    size = len(entries)
    while not _coprime_with_all(size, earlier_sizes):
        entries.append(None if null_share else PAD)
        if null_share:
            nulls += 1
        size += 1
    phase = int(hashlib.sha256((salt + dimension.id).encode()).hexdigest(), 16) % size
    return Axis(dimension, tuple(entries), size, _stride(size), phase, len(values), not_expressible, nulls)


def read_plan(value: dict, library: Library, executors: dict) -> list:
    """Validate a research_query_plan/v1 and build its products against the library and the executors."""
    if type(value) is not dict or value.get("record_type") != PLAN:
        raise PlanError("plan_version")
    if value.get("engine") not in ENGINES:
        raise PlanError("plan_engine")
    products = value.get("products")
    if type(products) is not list or not 1 <= len(products) <= MAXIMUM_PRODUCTS:
        raise PlanError("plan_products_bound")
    built, names = [], set()
    implementation = implementation_digest()
    for raw in products:
        if type(raw) is not dict or not {"id", "executor", "weight", "dimensions"} <= set(raw) or not set(raw) <= {
                "id", "executor", "weight", "dimensions", "params", "refresh_days", "follow_pages", "note"}:
            raise PlanError("product_fields")
        if raw["id"] in names or type(raw["id"]) is not str:
            raise PlanError("product_identity")
        names.add(raw["id"])
        executor = executors.get(raw["executor"])
        if executor is None:
            raise PlanError("product_executor_unknown:" + str(raw["executor"]))
        if type(raw["weight"]) is not int or not 1 <= raw["weight"] <= 100:
            raise PlanError("product_weight")
        dimensions = raw["dimensions"]
        if type(dimensions) is not list or not 1 <= len(dimensions) <= MAXIMUM_AXES:
            raise PlanError("product_dimensions_bound")
        specs = []
        for spec in dimensions:
            if type(spec) is not dict or "dimension" not in spec or not set(spec) <= {"dimension", "null_share", "where"}:
                raise PlanError("product_dimension_fields")
            dimension = library.dimension(spec["dimension"])
            if not executor.supports_dimension(dimension):
                raise PlanError(f"executor_cannot_express_dimension:{executor.executor_id}:{dimension.id}")
            null_share = spec.get("null_share", dimension.null_share)
            if type(null_share) is not int or not 0 <= null_share <= 90:
                raise PlanError("product_null_share")
            specs.append((dimension, null_share, _where(spec.get("where"))))
        if len({dimension.id for dimension, _, _ in specs}) != len(specs):
            raise PlanError("product_dimension_repeated")
        # Smaller dimensions first: making the lengths pairwise coprime then pads least.
        specs.sort(key=lambda item: (sum(value.weight for value in item[0].values), item[0].id))
        axes, sizes = [], []
        for dimension, null_share, where in specs:
            axis = build_axis(dimension, null_share=null_share, accepts=executor.accepts, where=where,
                              earlier_sizes=sizes, salt=raw["id"])
            axes.append(axis)
            sizes.append(axis.size)
        params = raw.get("params") or {}
        executor.check_params(params)
        refresh_days = raw.get("refresh_days", executor.refresh_days)
        follow_pages = raw.get("follow_pages", executor.follow_pages)
        if type(refresh_days) is not int or not 1 <= refresh_days <= 3650 or type(follow_pages) is not int or not 0 <= follow_pages <= 10:
            raise PlanError("product_refresh_or_pages")
        identity = digest({"product": raw, "dimensions": {axis.dimension.id: axis.dimension.digest() for axis in axes},
                           "library_rules": [rule.id for rule in library.rules], "executor": executor.identity(),
                           "implementation": implementation})
        built.append(Product(raw["id"], executor.executor_id, raw["weight"], tuple(axes), MappingProxyType(dict(params)),
                             refresh_days, follow_pages, identity, MappingProxyType(dict(raw))))
    return built


def _where(spec):
    if spec is None:
        return None
    if type(spec) is not dict or not set(spec) <= {"attribute", "in", "ids"}:
        raise PlanError("product_where")
    if "ids" in spec:
        allowed = frozenset(spec["ids"])
        return lambda value: value.id in allowed
    attribute, members = spec["attribute"], frozenset(spec["in"])

    def accepted(value):
        held = value.attributes.get(attribute)
        held = held if isinstance(held, (list, tuple)) else (held,)
        return any(item in members for item in held)
    return accepted


def load_plan(path: Path, library: Library, executors: dict) -> list:
    return read_plan(json.loads(Path(path).read_bytes()), library, executors)


def plan_dimensions(path: Path) -> set:
    """The dimension ids a plan names, so the library loads only the tables the plan needs."""
    value = json.loads(Path(path).read_bytes())
    return {spec["dimension"] for product in value.get("products", []) for spec in product.get("dimensions", [])}


def query_at(product: Product, k: int, library: Library, executor, *, page: int = 1):
    """The query at position k of one product, or (None, reason) when the combination is skipped."""
    assignment = product.assignment(k)
    if assignment is None:
        return None, "padding"
    broken = library.violations(assignment)
    if broken:
        return None, "rule:" + broken[0]
    request = executor.render(assignment, dict(product.params), page=page)
    if isinstance(request, str):
        return None, "render:" + request
    query_id = query_identity(executor.executor_id, request)
    return PlannedQuery(product.id, executor.executor_id, k, assignment, request, query_id, page), ""


def query_identity(executor_id: str, request: dict) -> str:
    """Stable identity of one probe: the executor and its exact rendered request (method, host, path, parameters).

    Labels, plan revision and enumeration order are not part of it, so the same request reached from two
    products, two plans or an imported queue is one query.
    """
    return digest({"executor": executor_id, "request": request})


def coverage(product: Product, ks) -> dict:
    """How many distinct values of each dimension a set of positions touched (null counted as its own value)."""
    seen = {axis.dimension.id: set() for axis in product.axes}
    for k in ks:
        for axis in product.axes:
            entry = axis.entry(k)
            if entry is not PAD:
                seen[axis.dimension.id].add(None if entry is None else entry.id)
    return {name: len(values) for name, values in seen.items()}


def describe(products: list) -> dict:
    """Sizes of every product: values per dimension, nulls, padding and the full virtual product."""
    out = {}
    for product in products:
        out[product.id] = {
            "executor": product.executor_id, "weight": product.weight, "digest": product.digest[:16],
            "dimensions": {axis.dimension.id: {"values": axis.values_used, "not_expressible": axis.values_not_expressible,
                                                "null_entries": axis.null_entries, "virtual_size": axis.size}
                           for axis in product.axes},
            "virtual_product": product.total}
    return out


def plain_assignment(assignment: dict) -> dict:
    return plain({name: (value.id if value is not None else None) for name, value in assignment.items()})


__all__ = ["PLAN", "QUERY", "CURSOR", "ENGINES", "GATES", "PlanError", "Product", "PlannedQuery", "read_plan",
           "load_plan", "plan_dimensions", "query_at", "query_identity", "coverage", "describe", "DimensionError"]
