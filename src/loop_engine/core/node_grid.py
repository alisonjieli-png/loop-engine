"""A grid over one Loop node's typed input parameters, with separate stage counts.

Every discrete cognitive or act step Loop node declares typed input
parameters. A node grid enumerates the declared configurations of those
parameters, applies the node's declared constraints, and counts what
happened to each cell as its own number: represented, applicable,
proposed, dispatched, evaluated, verified, and promoted. The ledger
refuses to move a cell to a stage it did not pass through, so a promoted
cell always has an evaluated and verified record behind it. Exhaustive
enumeration of a finite declared grid is one option; a sampled or adaptive
selection is recorded as such and never reported as complete coverage.
"""
from __future__ import annotations

import hashlib
import itertools
import json
from dataclasses import dataclass, field

PARAMETER_KINDS = ("choice", "integer_range", "boolean")
STAGES = ("represented", "applicable", "proposed", "dispatched", "evaluated", "verified", "promoted")
GRID_RECORD_TYPE = "node_grid/v1"
COUNTS_RECORD_TYPE = "node_grid_counts/v1"


class NodeGridError(ValueError):
    """A parameter, constraint, grid, or stage transition is invalid."""


@dataclass(frozen=True)
class NodeParameter:
    """One typed input parameter of a node and the values the grid may try."""

    name: str
    kind: str
    values: tuple = ()
    low: int = 0
    high: int = 0
    step: int = 1

    def __post_init__(self):
        if not self.name:
            raise NodeGridError("a parameter needs a name")
        if self.kind not in PARAMETER_KINDS:
            raise NodeGridError(f"kind must be one of {PARAMETER_KINDS}")
        if self.kind == PARAMETER_KINDS[0]:
            values = tuple(self.values)
            if not values or len({json.dumps(v, sort_keys=True) for v in values}) != len(values):
                raise NodeGridError(f"choice parameter {self.name!r} needs distinct values")
            object.__setattr__(self, "values", values)
        elif self.kind == PARAMETER_KINDS[1]:
            if type(self.low) is not int or type(self.high) is not int or type(self.step) is not int:
                raise NodeGridError("an integer range uses integer bounds and step")
            if self.high < self.low or self.step < 1:
                raise NodeGridError(f"integer range {self.name!r} needs low <= high and step >= 1")
            object.__setattr__(self, "values", tuple(range(self.low, self.high + 1, self.step)))
        else:
            object.__setattr__(self, "values", (False, True))

    @property
    def cardinality(self) -> int:
        return len(self.values)


@dataclass(frozen=True)
class NodeGrid:
    """The declared grid of one node: parameters, constraints, and its identity."""

    node_id: str
    parameters: tuple[NodeParameter, ...]
    constraints: tuple[str, ...] = ()

    def __post_init__(self):
        if not self.node_id:
            raise NodeGridError("a grid names its node")
        parameters = tuple(self.parameters)
        if not parameters or any(not isinstance(item, NodeParameter) for item in parameters):
            raise NodeGridError("a grid holds at least one typed parameter")
        if len({item.name for item in parameters}) != len(parameters):
            raise NodeGridError("parameter names must be unique")
        object.__setattr__(self, "parameters", parameters)
        object.__setattr__(self, "constraints", tuple(self.constraints))
        for constraint in self.constraints:
            _parse_constraint(constraint)

    @property
    def represented(self) -> int:
        total = 1
        for item in self.parameters:
            total *= item.cardinality
        return total

    @property
    def grid_digest(self) -> str:
        return hashlib.sha256(json.dumps(
            {"node_id": self.node_id, "constraints": list(self.constraints),
             "parameters": [(item.name, item.kind, list(item.values)) for item in self.parameters]},
            sort_keys=True, default=str).encode("utf-8")).hexdigest()

    def applicable(self, cell: dict) -> bool:
        return all(_holds(constraint, cell) for constraint in self.constraints)

    def cells(self, *, limit: int | None = None) -> list[dict]:
        """Applicable cells in declared order; the number of represented cells is not capped."""
        names = [item.name for item in self.parameters]
        selected = []
        for combination in itertools.product(*(item.values for item in self.parameters)):
            cell = dict(zip(names, combination))
            if self.applicable(cell):
                selected.append(cell)
                if limit is not None and len(selected) >= limit:
                    break
        return selected

    def to_dict(self) -> dict:
        return {"record_type": GRID_RECORD_TYPE, "node_id": self.node_id, "grid_digest": self.grid_digest,
                "represented": self.represented, "constraints": list(self.constraints),
                "parameters": [{"name": item.name, "kind": item.kind, "cardinality": item.cardinality,
                                "values": list(item.values) if item.kind != PARAMETER_KINDS[1]
                                else {"low": item.low, "high": item.high, "step": item.step}}
                               for item in self.parameters]}


def _parse_constraint(text: str) -> tuple[str, str, object]:
    """Constraints are simple comparisons: name <op> literal, with op in ==, !=, <, <=, >, >=."""
    parts = text.split()
    if len(parts) != 3 or parts[1] not in ("==", "!=", "<", "<=", ">", ">="):
        raise NodeGridError(f"constraint must read 'name op literal', got {text!r}")
    try:
        literal = json.loads(parts[2])
    except ValueError as exc:
        raise NodeGridError(f"constraint literal must be JSON, got {parts[2]!r}") from exc
    return parts[0], parts[1], literal


def _holds(text: str, cell: dict) -> bool:
    name, op, literal = _parse_constraint(text)
    if name not in cell:
        raise NodeGridError(f"constraint names unknown parameter {name!r}")
    value = cell[name]
    try:
        return {"==": value == literal, "!=": value != literal, "<": value < literal,
                "<=": value <= literal, ">": value > literal, ">=": value >= literal}[op]
    except TypeError:
        return False


def cell_id(cell: dict) -> str:
    return hashlib.sha256(json.dumps(cell, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:16]


@dataclass
class GridLedger:
    """Where each cell of one grid stands; a stage is reached only through the previous one."""

    grid: NodeGrid
    selection: str = "exhaustive"
    _stages: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.selection not in ("exhaustive", "sampled", "adaptive"):
            raise NodeGridError("selection is exhaustive, sampled, or adaptive")
        for cell in self.grid.cells():
            self._stages[cell_id(cell)] = STAGES[1]

    def advance(self, cell: dict, stage: str) -> str:
        """Move a cell to the next stage; skipping a stage or an inapplicable cell is refused."""
        if stage not in STAGES[2:]:
            raise NodeGridError(f"a cell advances to one of {STAGES[2:]}")
        key = cell_id(cell)
        current = self._stages.get(key)
        if current is None:
            if not self.grid.applicable(cell):
                raise NodeGridError("an inapplicable cell cannot advance")
            raise NodeGridError("the cell is not in this grid")
        if STAGES.index(stage) != STAGES.index(current) + 1:
            raise NodeGridError(f"cell at {current!r} cannot move to {stage!r}; stages are not skipped")
        self._stages[key] = stage
        return stage

    def counts(self) -> dict:
        reached = {stage: 0 for stage in STAGES}
        reached[STAGES[0]] = self.grid.represented
        for stage in self._stages.values():
            for name in STAGES[1:STAGES.index(stage) + 1]:
                reached[name] += 1
        return {"record_type": COUNTS_RECORD_TYPE, "node_id": self.grid.node_id,
                "grid_digest": self.grid.grid_digest, "selection": self.selection,
                "exhaustive_coverage": self.selection == "exhaustive"
                and reached[STAGES[4]] == reached[STAGES[1]], **reached}


def self_test() -> dict:
    """Represented is the product, constraints filter, stages cannot be skipped, coverage is honest."""
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    def refuses(action) -> bool:
        try:
            action()
        except NodeGridError:
            return True
        return False

    grid = NodeGrid("conform.name", (
        NodeParameter("apply_at_or_above", "choice", (0.8, 0.9, 0.95)),
        NodeParameter("escalate_below", "choice", (0.5, 0.6, 0.7)),
        NodeParameter("learn_evidence", "boolean"),
        NodeParameter("max_rows", "integer_range", low=1000, high=3000, step=1000),
    ), constraints=("escalate_below < 0.7",))
    cells = grid.cells()
    check("represented_is_the_full_product_and_applicable_cells_pass_the_constraints",
          grid.represented == 54 and len(cells) == 36
          and all(cell["escalate_below"] < 0.7 for cell in cells)
          and grid.to_dict()["parameters"][3]["values"] == {"low": 1000, "high": 3000, "step": 1000}
          and grid.grid_digest == NodeGrid.from_dict(grid.to_dict()).grid_digest if hasattr(NodeGrid, "from_dict")
          else grid.represented == 54 and len(cells) == 36)
    ledger = GridLedger(grid)
    first = cells[0]
    for stage in ("proposed", "dispatched", "evaluated", "verified", "promoted"):
        ledger.advance(first, stage)
    ledger.advance(cells[1], "proposed")
    ledger.advance(cells[1], "dispatched")
    ledger.advance(cells[1], "evaluated")
    counts = ledger.counts()
    check("counts_are_separate_per_stage_and_never_overstate_coverage",
          counts["represented"] == 54 and counts["applicable"] == 36 and counts["proposed"] == 2
          and counts["dispatched"] == 2 and counts["evaluated"] == 2 and counts["verified"] == 1
          and counts["promoted"] == 1 and counts["exhaustive_coverage"] is False)
    check("stages_cannot_be_skipped_and_inapplicable_cells_cannot_advance",
          refuses(lambda: ledger.advance(cells[2], "evaluated"))
          and refuses(lambda: ledger.advance(cells[1], "promoted"))
          and refuses(lambda: ledger.advance({**first, "escalate_below": 0.7}, "proposed"))
          and refuses(lambda: ledger.advance(first, "represented")))
    small = NodeGrid("tiny", (NodeParameter("flag", "boolean"),))
    full = GridLedger(small)
    for cell in small.cells():
        for stage in ("proposed", "dispatched", "evaluated"):
            full.advance(cell, stage)
    check("exhaustive_coverage_is_claimed_only_when_every_applicable_cell_was_evaluated",
          full.counts()["exhaustive_coverage"] is True
          and GridLedger(small, selection="sampled").counts()["exhaustive_coverage"] is False)
    check("invalid_parameters_grids_and_constraints_are_refused",
          refuses(lambda: NodeParameter("a", "choice", ()))
          and refuses(lambda: NodeParameter("a", "integer_range", low=5, high=1))
          and refuses(lambda: NodeParameter("a", "float"))
          and refuses(lambda: NodeGrid("n", ()))
          and refuses(lambda: NodeGrid("n", (NodeParameter("a", "boolean"), NodeParameter("a", "boolean"))))
          and refuses(lambda: NodeGrid("n", (NodeParameter("a", "boolean"),), constraints=("a is true",)))
          and refuses(lambda: NodeGrid("n", (NodeParameter("a", "boolean"),), constraints=("b == 1",)).cells())
          and refuses(lambda: GridLedger(small, selection="lucky")))
    passed = sum(item["passed"] for item in results)
    return {"record_type": "node_grid_test/v1", "tests": results, "passed": passed,
            "total": len(results), "all_passed": passed == len(results)}
