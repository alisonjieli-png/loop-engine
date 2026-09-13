"""Part 1 claim 1: whole-plan admission adversarial probes (no model calls)."""
import json, sys, traceback
from copy import deepcopy
from loop_engine.core.adaptive_practitioner_bindings_checks import assignment, input_binding, spec_from
from loop_engine.core.adaptive_practitioner_bindings import compile_assignments, DependencyBindingError
from loop_engine.core.adaptive_practitioner_bindings import SpawnedAssignment, SpawnedOutputContract, SpawnedInputBinding
from loop_engine.core.adaptive_practitioner_planning import _require_fields, EXTENDED_ASSIGNMENT_FIELDS

def attempt(label, values, goal="root"):
    try:
        order, digest = compile_assignments(tuple(spec_from(v) for v in values), goal)
        print(f"[{label}] ADMITTED order={order} digest={digest[:12]}")
        return ("admitted", order)
    except Exception as exc:
        print(f"[{label}] REFUSED {type(exc).__name__}: {str(exc)[:160]} disposition={getattr(exc,'disposition',None)}")
        return ("refused", type(exc).__name__)

producer = assignment("source")
consumer = assignment("consumer", dependencies=("source",), inputs=(input_binding(),), output=None)

# 1a self-dependency (barrier only) and self-dependency with input binding to self
a = assignment("a", dependencies=("a",), output=None)
attempt("self_dependency_barrier", [a])
a2 = assignment("a", dependencies=("a",), inputs=(input_binding("a"),))
attempt("self_dependency_with_self_input", [a2])

# 1b 3-cycle
x = assignment("x", dependencies=("z",), output=None); y = assignment("y", dependencies=("x",), output=None); z = assignment("z", dependencies=("y",), output=None)
attempt("three_cycle", [x, y, z])
# 3-cycle with typed inputs
x2 = assignment("x", dependencies=("z",), inputs=(input_binding("z"),)); y2 = assignment("y", dependencies=("x",), inputs=(input_binding("x"),)); z2 = assignment("z", dependencies=("y",), inputs=(input_binding("y"),))
attempt("three_cycle_typed", [x2, y2, z2])

# 1c diamond: d <- b,c <- a (typed), listed in worst order
da = assignment("a")
db = assignment("b", dependencies=("a",), inputs=(input_binding("a"),))
dc = assignment("c", dependencies=("a",), inputs=(input_binding("a"),))
dd = assignment("d", dependencies=("b", "c"), inputs=(
    {"role": "values/v1", "source_task_id": "b", "source_role": "values/v1", "value_contract_ref": "integer_sequence/v1", "delivery": "value"},
    {"role": "other_values/v1", "source_task_id": "c", "source_role": "values/v1", "value_contract_ref": "integer_sequence/v1", "delivery": "value"},), output=None)
attempt("diamond_listed_reverse", [dd, dc, db, da])
# diamond where the two inputs have the same consumer role (must be refused: role bound twice)
dd_dup = deepcopy(dd); dd_dup["inputs"][1]["role"] = "values/v1"
attempt("diamond_duplicate_consumer_role", [dd_dup, dc, db, da])

# 1d missing producer
m = assignment("m", dependencies=("ghost",), output=None)
attempt("missing_producer", [m])
m2 = assignment("m", dependencies=("source",), inputs=(input_binding("ghost"),), output=None)
attempt("input_from_unlisted_producer", [m2, producer])

# 1e duplicates differing by case / whitespace / unicode
attempt("dup_case", [producer, dict(producer, task_id="Source")])
attempt("dup_trailing_space", [producer, dict(producer, task_id="source ")])
attempt("dup_leading_space", [producer, dict(producer, task_id=" source")])
attempt("dup_nfkc", [producer, dict(producer, task_id="ſource")])  # long s
attempt("consumer_depends_on_case_variant", [dict(consumer, depends_on=["Source"], inputs=[input_binding("Source")]), producer, dict(producer, task_id="Source")])
# task id oddities
for tid in ("", " ", "a b", "a/b", "a\nb", "../x", "x" * 300, "🚀", "task:evil", "slot.00000000"):
    attempt(f"task_id={tid!r}"[:40], [dict(producer, task_id=tid)])

# 1f consumer binds to a producer that has no output contract / wrong port
p_no_out = dict(producer, output_contract=None)
attempt("bind_to_barrier_producer_without_output", [consumer, p_no_out])
c_wrong_port = deepcopy(consumer); c_wrong_port["inputs"][0]["source_role"] = "missing_port/v1"
attempt("bind_to_nonexistent_output_port", [c_wrong_port, producer])

# 1g malformed / hostile schemas
for label, schema in (
        ("items_not_schema", {"type": "array", "items": 5}),
        ("minimum_string", {"type": "integer", "minimum": "x"}),
        ("enum_not_list", {"enum": 5}),
        ("required_dup", {"type": "object", "required": ["a", "a"]}),
        ("type_list_bad", {"type": ["integer", "banana"]}),
        ("bool_true_schema", True),
        ("bool_false_schema", False),
        ("empty_schema", {}),
        ("nan_default", {"type": "number", "default": float("nan")}),
        ("pattern", {"type": "string", "pattern": "^a$"}),
        ("format", {"type": "string", "format": "email"}),
        ("defs", {"$defs": {"x": {}}, "type": "integer"}),
        ("properties_list", {"type": "object", "properties": [1, 2]}),
        ("allOf_not_list", {"allOf": {"type": "integer"}}),
        ("nested_3000", None)):
    if label == "nested_3000":
        schema = {"type": "integer"}
        for _ in range(3000):
            schema = {"type": "array", "items": schema}
    p = deepcopy(producer); p["output_contract"]["schema"] = schema
    attempt("schema_" + label, [consumer, p])

# 1h prerequisites w/o binding (barrier) and binding w/o prerequisite
barrier = assignment("barrier", dependencies=("source",), output=None)
attempt("prereq_without_binding_barrier", [barrier, producer])
nb = deepcopy(consumer); nb["depends_on"] = []
attempt("binding_without_prereq", [nb, producer])

# mixed legacy and named
from loop_engine.loop.kernel import ProblemSpec
legacy = ProblemSpec("legacy", success_criteria=("c",))
try:
    print("mixed:", compile_assignments((legacy, spec_from(producer)), "root"))
except Exception as exc:
    print("mixed REFUSED", type(exc).__name__, str(exc)[:100])

# record_type version drift and surplus fields through the planning field gate
base = deepcopy(producer)
for label, mutate in (("v2", lambda v: v.update(record_type="adaptive_spawned_assignment/v2")),
                      ("v01", lambda v: v.update(record_type="adaptive_spawned_assignment/v01")),
                      ("surplus_field", lambda v: v.update(permissions=["all"])),
                      ("surplus_underscore", lambda v: v.update(_adaptive_spawned_assignment={"x": 1}))):
    v = deepcopy(base); mutate(v)
    try:
        _require_fields(v, EXTENDED_ASSIGNMENT_FIELDS, "plan.spawned_tasks[0]")
        SpawnedAssignment.from_mapping(v)
        print(f"[record_{label}] ADMITTED")
    except Exception as exc:
        print(f"[record_{label}] REFUSED {type(exc).__name__}: {str(exc)[:140]}")
