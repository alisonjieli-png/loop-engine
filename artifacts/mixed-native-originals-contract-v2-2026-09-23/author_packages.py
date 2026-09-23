"""Twelve explicitly authored methods, not a cross product of titles or templates."""
from __future__ import annotations

import base64
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from acceptance_cases import CASES

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
COMMON = '''import json
import math
import re
import sys
from decimal import Decimal, DecimalException


def need(value):
    if not value:
        raise ValueError("invalid input")


def obj(value, keys):
    need(type(value) is dict and set(value) == set(keys))


def integer(value, low=0, high=10**9):
    need(type(value) is int and low <= value <= high)


def names(values, minimum=0, maximum=60):
    need(type(values) is list and minimum <= len(values) <= maximum)
    need(all(type(v) is str and re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]{0,31}", v) for v in values))
    need(len(values) == len(set(values)))


def unique(pairs):
    result = {}
    for key, value in pairs:
        need(key not in result)
        result[key] = value
    return result


def json_number(token):
    # JSON Schema integers include finite numbers such as 1.0 and 1e0.
    # Decimal classifies the literal before binary rounding can hide a fraction.
    need(len(token) <= 1024)
    number = float(token)
    need(math.isfinite(number))
    try:
        exact = Decimal(token)
        need(-4096 <= exact.as_tuple().exponent <= 4096)
        need(number != 0 or exact.is_zero())
        if exact == exact.to_integral_value():
            need(exact.is_zero() or exact.adjusted() <= 308)
            return int(exact)
    except DecimalException:
        raise ValueError("invalid numeric literal") from None
    return number


def bounded(value, depth=0):
    need(depth <= 16)
    if type(value) is float:
        need(math.isfinite(value))
    elif type(value) is dict:
        for item in value.values():
            bounded(item, depth + 1)
    elif type(value) is list:
        for item in value:
            bounded(item, depth + 1)


'''
MAIN = '''

def main():
    try:
        raw = sys.stdin.buffer.read(32769)
        need(len(raw) <= 32768)
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique, parse_float=json_number,
                           parse_constant=lambda _: need(False))
        bounded(value)
        result = solve(value)
        text = json.dumps(result, sort_keys=True, ensure_ascii=True, allow_nan=False)
        need(len(text.encode("utf-8")) <= 65536)
        print(text)
        return 0
    except (ValueError, TypeError, KeyError, IndexError, SyntaxError,
            RecursionError, ZeroDivisionError, OverflowError, UnicodeError):
        print('{"error":"invalid_input"}')
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
'''

SOLVERS = {
"schedule_dag_earliest_times": '''from graphlib import TopologicalSorter


def solve(value):
    obj(value, ["tasks"])
    tasks = value["tasks"]
    need(type(tasks) is list and 1 <= len(tasks) <= 60)
    for task in tasks:
        obj(task, ["id", "duration", "depends_on"])
        integer(task["duration"])
        names(task["depends_on"])
    names([task["id"] for task in tasks], 1)
    by_id = {task["id"]: task for task in tasks}
    need(all(set(task["depends_on"]) <= set(by_id) for task in tasks))
    graph = {key: set(by_id[key]["depends_on"]) for key in sorted(by_id)}
    finishes, rows = {}, []
    for key in TopologicalSorter(graph).static_order():
        start = max((finishes[parent] for parent in graph[key]), default=0)
        finish = start + by_id[key]["duration"]
        finishes[key] = finish
        rows.append({"id": key, "start": start, "finish": finish})
    return {"duration": max(finishes.values()), "schedule": sorted(rows, key=lambda row: row["id"])}
''',
"cover_pairwise_configuration_values": '''from itertools import combinations, product


def solve(value):
    obj(value, ["factors"])
    factors = value["factors"]
    need(type(factors) is dict)
    keys = sorted(factors)
    names(keys, 2, 6)
    for values in factors.values():
        need(type(values) is list and 1 <= len(values) <= 3)
        need(all(type(v) is str and 1 <= len(v) <= 32 for v in values))
        need(len(values) == len(set(values)))
    pairs = list(combinations(range(len(keys)), 2))
    candidates = list(product(*(sorted(factors[key]) for key in keys)))
    coverage = [set((a, row[a], b, row[b]) for a, b in pairs) for row in candidates]
    uncovered = set().union(*coverage)
    total = len(uncovered)
    selected = []
    while uncovered:
        best = max(range(len(candidates)), key=lambda i: len(coverage[i] & uncovered))
        need(bool(coverage[best] & uncovered))
        selected.append(dict(zip(keys, candidates[best])))
        uncovered -= coverage[best]
    return {"cases": selected, "total_pairs": total, "covered_pairs": total - len(uncovered)}
''',
"compare_primitive_object_contracts": '''def contract(value):
    obj(value, ["fields", "required", "allow_extra"])
    need(type(value["fields"]) is dict and len(value["fields"]) <= 40)
    names(list(value["fields"]))
    need(all(t in ("string", "integer", "number", "boolean", "null") for t in value["fields"].values()))
    names(value["required"])
    need(set(value["required"]) <= set(value["fields"]))
    need(type(value["allow_extra"]) is bool)


def solve(value):
    obj(value, ["old", "new"])
    old, new = value["old"], value["new"]
    contract(old)
    contract(new)
    changes = []
    def add(code, field=""):
        changes.append({"code": code, "field": field})
    for field, old_type in old["fields"].items():
        if field not in new["fields"]:
            if not new["allow_extra"]:
                add("removed_field", field)
        elif new["fields"][field] != old_type and (old_type, new["fields"][field]) != ("integer", "number"):
            add("changed_type", field)
    for field in set(new["required"]) - set(old["required"]):
        add("new_required_field", field)
    if old["allow_extra"] and not new["allow_extra"]:
        add("extra_fields_rejected")
    if old["allow_extra"]:
        for field in set(new["fields"]) - set(old["fields"]):
            add("extra_field_constrained", field)
    return {"compatible": not changes, "breaking_changes": sorted(changes, key=lambda row: (row["code"], row["field"]))}
''',
"pack_first_fit_decreasing_batches": '''def solve(value):
    obj(value, ["capacity", "items"])
    integer(value["capacity"], 1)
    need(type(value["items"]) is list and len(value["items"]) <= 100)
    for item in value["items"]:
        obj(item, ["id", "size"])
        integer(item["size"], 1, value["capacity"])
    names([item["id"] for item in value["items"]], maximum=100)
    bins = []
    for item in sorted(value["items"], key=lambda item: (-item["size"], item["id"])):
        target = next((bucket for bucket in bins if bucket["used"] + item["size"] <= value["capacity"]), None)
        if target is None:
            target = {"item_ids": [], "used": 0}
            bins.append(target)
        target["item_ids"].append(item["id"])
        target["used"] += item["size"]
    return {"bins": bins}
''',
"audit_functional_dependency_rows": '''def solve(value):
    obj(value, ["determinants", "dependents", "rows"])
    names(value["determinants"], 1, 5)
    names(value["dependents"], 1, 5)
    need(not set(value["determinants"]) & set(value["dependents"]))
    need(type(value["rows"]) is list and len(value["rows"]) <= 100)
    columns = value["determinants"] + value["dependents"]
    groups = {}
    for index, row in enumerate(value["rows"]):
        need(type(row) is dict and set(columns) <= set(row))
        need(all(type(row[key]) in (str, int, bool, type(None)) for key in columns))
        need(all(type(row[key]) is not str or len(row[key]) <= 64 for key in columns))
        determinant = [row[key] for key in value["determinants"]]
        dependent = [row[key] for key in value["dependents"]]
        key = json.dumps(determinant, sort_keys=True)
        group = groups.setdefault(key, {"determinant": determinant, "dependent_variants": {}, "row_indices": []})
        group["dependent_variants"][json.dumps(dependent, sort_keys=True)] = dependent
        group["row_indices"].append(index)
    violations = [{**group, "dependent_variants": list(group["dependent_variants"].values())}
                  for group in groups.values() if len(group["dependent_variants"]) > 1]
    return {"violations": violations}
''',
"find_strongly_connected_components": '''def solve(value):
    obj(value, ["vertices", "edges"])
    names(value["vertices"], 1, 60)
    need(type(value["edges"]) is list and len(value["edges"]) <= 300)
    graph = {key: [] for key in sorted(value["vertices"])}
    reverse = {key: [] for key in graph}
    edge_set = set()
    for edge in value["edges"]:
        need(type(edge) is list and len(edge) == 2 and all(type(v) is str and v in graph for v in edge))
        pair = tuple(edge)
        need(pair not in edge_set)
        edge_set.add(pair)
        graph[edge[0]].append(edge[1])
        reverse[edge[1]].append(edge[0])
    visited, order = set(), []
    def visit(vertex):
        if vertex in visited:
            return
        visited.add(vertex)
        for neighbor in sorted(graph[vertex]):
            visit(neighbor)
        order.append(vertex)
    for vertex in graph:
        visit(vertex)
    visited.clear()
    groups = []
    for vertex in reversed(order):
        if vertex in visited:
            continue
        stack, group = [vertex], []
        visited.add(vertex)
        while stack:
            current = stack.pop()
            group.append(current)
            for neighbor in reverse[current]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    stack.append(neighbor)
        groups.append(sorted(group))
    groups.sort()
    cyclic = [group for group in groups if len(group) > 1 or (group[0], group[0]) in edge_set]
    return {"components": groups, "cyclic_components": cyclic}
''',
"simulate_exact_token_bucket": '''from fractions import Fraction


def solve(value):
    obj(value, ["capacity", "initial_tokens", "refill_per_second", "requests"])
    integer(value["capacity"], 1, 1000)
    integer(value["initial_tokens"], 0, value["capacity"])
    integer(value["refill_per_second"], 0, 1000)
    need(type(value["requests"]) is list and len(value["requests"]) <= 100)
    for row in value["requests"]:
        obj(row, ["id", "at_ms", "tokens"])
        integer(row["at_ms"])
        integer(row["tokens"], 1)
    names([row["id"] for row in value["requests"]], maximum=100)
    tokens, previous, decisions = Fraction(value["initial_tokens"]), 0, []
    for row in value["requests"]:
        need(row["at_ms"] >= previous)
        tokens = min(Fraction(value["capacity"]), tokens + Fraction((row["at_ms"] - previous) * value["refill_per_second"], 1000))
        allowed = tokens >= row["tokens"]
        if allowed:
            tokens -= row["tokens"]
        previous = row["at_ms"]
        decisions.append({"id": row["id"], "allowed": allowed,
                          "tokens_after": {"numerator": tokens.numerator, "denominator": tokens.denominator}})
    return {"decisions": decisions}
''',
"audit_boolean_rule_coverage": '''from itertools import product


def solve(value):
    obj(value, ["variables", "rules"])
    names(value["variables"], 1, 6)
    need(type(value["rules"]) is list and len(value["rules"]) <= 50)
    for rule in value["rules"]:
        obj(rule, ["id", "when", "decision"])
        names([rule["decision"]], 1, 1)
        need(type(rule["when"]) is dict and set(rule["when"]) <= set(value["variables"]))
        need(all(type(v) is bool for v in rule["when"].values()))
    names([rule["id"] for rule in value["rules"]], maximum=50)
    uncovered, conflicts, count = [], [], 0
    keys = sorted(value["variables"])
    for combination in product((False, True), repeat=len(keys)):
        assignment = dict(zip(keys, combination))
        matches = [rule for rule in value["rules"] if all(assignment[key] is expected for key, expected in rule["when"].items())]
        decisions = set(rule["decision"] for rule in matches)
        if not matches:
            uncovered.append(assignment)
        elif len(decisions) > 1:
            conflicts.append({"assignment": assignment, "rule_ids": sorted(rule["id"] for rule in matches)})
        else:
            count += 1
    return {"unambiguous_count": count, "uncovered": uncovered, "conflicts": conflicts}
''',
"decode_u16_length_prefixed_frames": '''def solve(value):
    obj(value, ["hex"])
    need(type(value["hex"]) is str and len(value["hex"]) <= 16384)
    need(re.fullmatch(r"(?:[0-9A-Fa-f]{2})*", value["hex"]) is not None)
    data = bytes.fromhex(value["hex"])
    offset, frames = 0, []
    while offset < len(data):
        need(offset + 2 <= len(data))
        size = int.from_bytes(data[offset:offset + 2], "big")
        offset += 2
        need(size <= 1024 and offset + size <= len(data))
        frames.append(data[offset:offset + size].hex())
        offset += size
        need(len(frames) <= 256)
    return {"frames_hex": frames, "count": len(frames)}
''',
"evaluate_bounded_rational_expression": '''import ast
from fractions import Fraction


def solve(value):
    obj(value, ["expression"])
    need(type(value["expression"]) is str and 1 <= len(value["expression"]) <= 256)
    tree = ast.parse(value["expression"].strip(), mode="eval")
    need(sum(1 for _ in ast.walk(tree)) <= 64)
    def evaluate(node):
        if isinstance(node, ast.Constant):
            integer(node.value, -(10**9), 10**9)
            result = Fraction(node.value)
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
            result = evaluate(node.operand)
            if isinstance(node.op, ast.USub):
                result = -result
        elif isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
            left, right = evaluate(node.left), evaluate(node.right)
            if isinstance(node.op, ast.Add):
                result = left + right
            elif isinstance(node.op, ast.Sub):
                result = left - right
            elif isinstance(node.op, ast.Mult):
                result = left * right
            else:
                result = left / right
        else:
            raise ValueError("unsupported expression")
        need(result.numerator.bit_length() <= 512 and result.denominator.bit_length() <= 512)
        return result
    result = evaluate(tree.body)
    return {"numerator": result.numerator, "denominator": result.denominator}
''',
"resolve_literal_named_template": '''def solve(value):
    obj(value, ["template", "variables"])
    need(type(value["template"]) is str and len(value["template"]) <= 8192)
    need(type(value["variables"]) is dict and len(value["variables"]) <= 30)
    pattern = re.compile(r"\\$\\{([A-Za-z_][A-Za-z0-9_]*)\\}")
    names_used = set(pattern.findall(value["template"]))
    need("${" not in pattern.sub("", value["template"]))
    need(names_used == set(value["variables"]))
    need(all(type(v) is str and len(v) <= 2048 for v in value["variables"].values()))
    text = pattern.sub(lambda match: value["variables"][match.group(1)], value["template"])
    return {"text": text}
''',
"project_json_pointer_values": '''def solve(value):
    obj(value, ["document", "pointers"])
    need(type(value["pointers"]) is list and 1 <= len(value["pointers"]) <= 16)
    results = []
    for pointer in value["pointers"]:
        need(type(pointer) is str and len(pointer) <= 512 and (pointer == "" or pointer.startswith("/")))
        current = value["document"]
        for encoded in ([] if pointer == "" else pointer[1:].split("/")):
            need(re.search(r"~(?![01])", encoded) is None)
            token = encoded.replace("~1", "/").replace("~0", "~")
            if type(current) is dict:
                need(token in current)
                current = current[token]
            elif type(current) is list:
                need(re.fullmatch(r"0|[1-9][0-9]*", token) is not None)
                index = int(token)
                need(index < len(current))
                current = current[index]
            else:
                raise ValueError("pointer cannot continue")
        results.append(current)
    return {"values": results}
''',
}

DESCRIPTIONS = {
    "schedule_dag_earliest_times": ("Schedule earliest times in a dependency graph", "Compute earliest starts and finishes for a bounded acyclic task graph with nonnegative integer durations.", "Assumes unlimited parallel resources and zero transfer delays. It does not assign staff or optimize a calendar. Cycles and undeclared dependencies are refused."),
    "cover_pairwise_configuration_values": ("Cover pairs of configuration values", "Construct deterministic test rows that cover every pair of values across two to six independent configuration factors.", "Uses greedy uncovered-pair selection. The result is not claimed to use the minimum number of rows. Constraints between factors are unsupported and must be resolved before calling."),
    "compare_primitive_object_contracts": ("Compare primitive object input contracts", "Find when a proposed primitive-field object contract would reject a value admitted by the prior contract.", "This is a closed subset with primitive field types, required fields and an extra-field switch. It is not a general JSON Schema compatibility solver. Integer to number is widening; number to integer is narrowing."),
    "pack_first_fit_decreasing_batches": ("Pack items with first fit decreasing", "Group positive integer item sizes into capacity-bounded batches using deterministic first fit decreasing.", "This is a heuristic, not an optimal bin-packing solver. Input item identities are unique; equal sizes sort by identity. Oversized items are refused instead of silently split."),
    "audit_functional_dependency_rows": ("Audit a declared functional dependency", "Report determinant groups that map to more than one distinct dependent value tuple in supplied rows.", "Only selected determinant and dependent columns are compared; they must be strings of at most 64 characters, integers, Booleans or null. Other columns may contain bounded JSON and are ignored. True and integer 1 are different; 1 and 1.0 are the same mathematical integer. Missing or nonscalar selected columns are refused. This finds counterexamples in the supplied sample, not proof that the dependency holds in a population."),
    "find_strongly_connected_components": ("Find mutually reachable graph components", "Partition a bounded directed graph into strongly connected components and identify cyclic components including self-loops.", "Edges are directed and every endpoint must be declared. A singleton with no self-loop is not cyclic. Components are structural findings, not a recommendation to delete dependencies."),
    "simulate_exact_token_bucket": ("Simulate an exact token bucket", "Replay ordered timestamped token requests against one bounded bucket using exact fractional refill arithmetic.", "Time is integer milliseconds from zero, with input-order handling of equal timestamps. Denied requests consume no tokens. This is an offline simulator; it grants no quota or access authority."),
    "audit_boolean_rule_coverage": ("Audit Boolean rule coverage and conflicts", "Enumerate every assignment of up to six Boolean variables and report missing or conflicting routing decisions.", "A match uses conjunction; an empty condition is a catch-all. Same-decision overlaps are unambiguous. Results describe a supplied table and never authorize actions or apply policy to users."),
    "decode_u16_length_prefixed_frames": ("Decode two-byte length-prefixed records", "Split a bounded hexadecimal byte stream into complete records prefixed by unsigned two-byte big-endian lengths.", "Zero-length records are valid. Incomplete headers, incomplete payloads, more than 256 frames and payloads over 1024 bytes are refused. Bytes remain hexadecimal and are never executed or deserialized further."),
    "evaluate_bounded_rational_expression": ("Evaluate a bounded rational expression", "Evaluate integer arithmetic with parentheses, unary signs, addition, subtraction, multiplication and true division as an exact fraction.", "Names, calls, attributes, floating literals, powers and other syntax are refused. The expression is parsed into an abstract syntax tree, never evaluated with Python eval. It has length, tree-size and intermediate-bit limits."),
    "resolve_literal_named_template": ("Resolve a literal named template", "Replace declared ${name} placeholders exactly once with supplied literal strings and refuse missing or unused variables.", "Replacement text is not rescanned. This does not escape shell, HTML, SQL or another target syntax. Treat the result as text; a separate context-aware encoder is required before any such use."),
    "project_json_pointer_values": ("Project values using JSON Pointer", "Select values from a supplied JSON document using JSON Pointer string-form paths, with strict escape and array-index checks.", "Implements string-form reference tokens; URI fragment form and the nonexistent array append index are refused. No Unicode normalization is applied. Document depth is bounded and oversized projected output is refused."),
}


def closed(properties):
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


def array(items, maximum=100, minimum=0, unique=False):
    value = {"type": "array", "items": items, "minItems": minimum, "maxItems": maximum}
    if unique:
        value["uniqueItems"] = True
    return value


IDENTIFIER = {"type": "string", "pattern": "^[A-Za-z][A-Za-z0-9_.-]{0,31}$"}
INTEGER = {"type": "integer", "minimum": 0, "maximum": 10**9}
POSITIVE = {**INTEGER, "minimum": 1}
BOOLEAN = {"type": "boolean"}
SCALAR = {"type": ["string", "integer", "boolean", "null"], "maxLength": 64}
FRACTION = closed({"numerator": {"type": "integer"}, "denominator": {"type": "integer", "minimum": 1}})
PRIMITIVE_CONTRACT = closed({"fields": {"type": "object", "maxProperties": 40, "propertyNames": IDENTIFIER, "additionalProperties": {"enum": ["string", "integer", "number", "boolean", "null"]}}, "required": array(IDENTIFIER, 60, unique=True), "allow_extra": BOOLEAN})
SCHEMAS = {
    "schedule_dag_earliest_times": (closed({"tasks": array(closed({"id": IDENTIFIER, "duration": INTEGER, "depends_on": array(IDENTIFIER, 60, unique=True)}), 60, 1)}), closed({"duration": {"type": "integer", "minimum": 0}, "schedule": array(closed({"id": IDENTIFIER, "start": {"type": "integer", "minimum": 0}, "finish": {"type": "integer", "minimum": 0}}), 60, 1)})),
    "cover_pairwise_configuration_values": (closed({"factors": {"type": "object", "minProperties": 2, "maxProperties": 6, "propertyNames": IDENTIFIER, "additionalProperties": array({"type": "string", "minLength": 1, "maxLength": 32}, 3, 1, True)}}), closed({"cases": array({"type": "object", "minProperties": 2, "maxProperties": 6, "propertyNames": IDENTIFIER, "additionalProperties": {"type": "string"}}, 135, 1), "total_pairs": POSITIVE, "covered_pairs": POSITIVE})),
    "compare_primitive_object_contracts": (closed({"old": PRIMITIVE_CONTRACT, "new": PRIMITIVE_CONTRACT}), closed({"compatible": BOOLEAN, "breaking_changes": array(closed({"code": {"enum": ["removed_field", "changed_type", "new_required_field", "extra_fields_rejected", "extra_field_constrained"]}, "field": {"type": "string"}}), 200)})),
    "pack_first_fit_decreasing_batches": (closed({"capacity": POSITIVE, "items": array(closed({"id": IDENTIFIER, "size": POSITIVE}), 100)}), closed({"bins": array(closed({"item_ids": array(IDENTIFIER, 100, 1, True), "used": POSITIVE}), 100)})),
    "audit_functional_dependency_rows": (closed({"determinants": array(IDENTIFIER, 5, 1, True), "dependents": array(IDENTIFIER, 5, 1, True), "rows": array({"type": "object", "additionalProperties": {}, "description": "Only columns named in determinants/dependents require the bounded scalar domain; the tool enforces these data-dependent constraints. Other columns are ignored."}, 100)}), closed({"violations": array(closed({"determinant": array(SCALAR, 5, 1), "dependent_variants": array(array(SCALAR, 5, 1), 100, 2), "row_indices": array(INTEGER, 100, 2)}), 100)})),
    "find_strongly_connected_components": (closed({"vertices": array(IDENTIFIER, 60, 1, True), "edges": array(array(IDENTIFIER, 2, 2), 300, unique=True)}), closed({"components": array(array(IDENTIFIER, 60, 1, True), 60, 1), "cyclic_components": array(array(IDENTIFIER, 60, 1, True), 60)})),
    "simulate_exact_token_bucket": (closed({"capacity": {**POSITIVE, "maximum": 1000}, "initial_tokens": {**INTEGER, "maximum": 1000}, "refill_per_second": {**INTEGER, "maximum": 1000}, "requests": array(closed({"id": IDENTIFIER, "at_ms": INTEGER, "tokens": POSITIVE}), 100)}), closed({"decisions": array(closed({"id": IDENTIFIER, "allowed": BOOLEAN, "tokens_after": FRACTION}), 100)})),
    "audit_boolean_rule_coverage": (closed({"variables": array(IDENTIFIER, 6, 1, True), "rules": array(closed({"id": IDENTIFIER, "when": {"type": "object", "propertyNames": IDENTIFIER, "additionalProperties": BOOLEAN}, "decision": IDENTIFIER}), 50)}), closed({"unambiguous_count": INTEGER, "uncovered": array({"type": "object", "additionalProperties": BOOLEAN}, 64), "conflicts": array(closed({"assignment": {"type": "object", "additionalProperties": BOOLEAN}, "rule_ids": array(IDENTIFIER, 50, 2, True)}), 64)})),
    "decode_u16_length_prefixed_frames": (closed({"hex": {"type": "string", "pattern": "^(?:[0-9A-Fa-f]{2})*$", "maxLength": 16384}}), closed({"frames_hex": array({"type": "string", "pattern": "^(?:[0-9a-f]{2})*$", "maxLength": 2048}, 256), "count": INTEGER})),
    "evaluate_bounded_rational_expression": (closed({"expression": {"type": "string", "minLength": 1, "maxLength": 256}}), FRACTION),
    "resolve_literal_named_template": (closed({"template": {"type": "string", "maxLength": 8192}, "variables": {"type": "object", "maxProperties": 30, "propertyNames": {"pattern": "^[A-Za-z_][A-Za-z0-9_]*$"}, "additionalProperties": {"type": "string", "maxLength": 2048}}}), closed({"text": {"type": "string", "maxLength": 65536}})),
    "project_json_pointer_values": (closed({"document": {}, "pointers": array({"type": "string", "maxLength": 512}, 16, 1)}), closed({"values": array({}, 16, 1)})),
}


def json_bytes(value):
    return (json.dumps(value, indent=2, ensure_ascii=True) + "\n").encode()


def strict_patterns(value):
    """JSON Schema patterns must reject a trailing newline, as the tools do."""
    if isinstance(value, list):
        return [strict_patterns(item) for item in value]
    if not isinstance(value, dict):
        return value
    return {key: (item[:-1] + r"(?![\s\S])" if key == "pattern" and item.endswith("$")
                  else strict_patterns(item)) for key, item in value.items()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=HERE / "authored")
    parser.add_argument("--proposals", type=Path, default=HERE / "proposals.json")
    options = parser.parse_args()
    target = options.output
    if target.exists() or options.proposals.exists():
        raise ValueError("Authoring refuses an existing output folder")
    target.mkdir()
    source_path = "src/loop_engine/core/service_runtime/catalogue_packages.py"
    revision = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
    licence = (ROOT / "LICENSE").read_bytes()
    proposals = []
    for identity, solver in SOLVERS.items():
        title, purpose, limits = DESCRIPTIONS[identity]
        schema_in, schema_out = SCHEMAS[identity]
        instruction = f'''# {title}

This candidate supplies a reusable tool for one focused task. Preserve the
current task assignment when composing this instruction with a per-step brief.

## First steps

1. Confirm that the task needs this exact method: {purpose}
2. Read `contracts/input.schema.json` and the method limits below. Build an input
   object from the supplied evidence; do not guess missing values.
3. After the host authorizes local execution, run the selected immutable script
   with JSON on standard input. The example demonstrates the interface:

   ```bash
   python3 -I -S -B tools/{identity}.py < examples/input.json
   ```

4. Compare the result with `contracts/output.schema.json` and the task's own
   acceptance rule. The synthetic example output is in `examples/output.json`.
   A successful structure does not make the supplied facts correct.

## Method limits

{limits}

The program accepts at most 32 KiB of UTF-8 JSON and document depth 16. It refuses
duplicate keys, non-finite numbers, extra root fields and method-specific invalid
inputs. Finite mathematically integral numeric literals such as 1.0 are normalized
to integers before method validation; Booleans stay distinct. Nonintegral values
do not become integer fields through rounding. Decimal/scientific numeric tokens
have at most 1024 characters and an exponent between -4096 and 4096. Overflow and
nonzero underflow beyond a finite binary float are refused before conversion;
nonintegral values otherwise use Python's finite float representation.
It emits at most 64 KiB of JSON. Refusal is exit 2 with
`{{"error":"invalid_input"}}`; success is exit 0 with the result object. A host
must bound time and memory and supply only approved input. The script reads no
task files, credentials or environment values and makes no network or subprocess
calls. The interpreter reads the script and standard-library modules. It writes
only standard output. No instruction here grants execution authority.

## Acceptance and provenance

`verification/cases.json` contains original synthetic success and refusal cases.
They test this method, not a customer's real outcome. This package is original
candidate work by Codex (OpenAI family), method
`codex_original_mixed_native_authoring/v2`. No third-party code or prose was
copied. The included repository MIT notice applies to the authored candidate;
it is not a claim of rights over outside task data. Independent exact-byte
review, native loading and task acceptance remain required.
'''
        payloads = {
            "AGENTS.md": (instruction.encode(), "instruction_file", "text/markdown"),
            f"tools/{identity}.py": ((COMMON + solver + MAIN).encode(), "executable_tool", "text/x-python"),
            "contracts/input.schema.json": (json_bytes(strict_patterns({"$schema": "https://json-schema.org/draft/2020-12/schema", **schema_in})), "configuration", "application/schema+json"),
            "contracts/output.schema.json": (json_bytes(strict_patterns({"$schema": "https://json-schema.org/draft/2020-12/schema", **schema_out})), "configuration", "application/schema+json"),
            "examples/input.json": (json_bytes(CASES[identity][0][0]), "other", "application/json"),
            "examples/output.json": (json_bytes(CASES[identity][0][1]), "other", "application/json"),
            "verification/cases.json": (json_bytes([{"input": given, "expected": expected, "expected_exit": 2 if expected is None else 0} for given, expected in CASES[identity]]), "other", "application/json"),
            "LICENSE": (licence, "other", "text/plain"),
        }
        files = []
        for path, (body, role, media_type) in payloads.items():
            dest = target / identity / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(body)
            files.append({"path": path, "digest": hashlib.sha256(body).hexdigest(), "size_bytes": len(body), "media_type": media_type, "role": role, "content_base64": base64.b64encode(body).decode()})
        proposals.append({"id": identity, "title": title, "purpose": purpose,
            "sources": [source_path], "layer": "code", "family": "deterministic_native_method",
            "search_tags": [identity.replace("_", " "), "standard library", "json input", "deterministic tool"],
            "tags": {"language": ["en"], "domain": ["software", "data"]}, "symbols": ["solve"],
            "kind": "tool", "styles": ["codex", "opencode", "pi"],
            "dependencies": ["Python>=3.10 standard library; no third-party packages"],
            "declared_effects": ["reads_fs", "spawns_process"],
            "producer": {"producer_identity": "Codex original mixed native authoring session", "family": "openai", "method_identity": "codex_original_mixed_native_authoring/v2"}, "files": files})
    record = {"record_type": "harness_candidate_batch_proposals/v2", "source_revision": revision,
        "license": {"expression": "MIT", "path": "LICENSE", "sha256": hashlib.sha256(licence).hexdigest()},
        "sources": {source_path: hashlib.sha256((ROOT / source_path).read_bytes()).hexdigest()}, "proposals": proposals}
    options.proposals.write_bytes(json_bytes(record))
    print(json.dumps({"original_candidate_methods": len(proposals), "payload_paths": sum(len(row["files"]) for row in proposals), "approved": 0}))


if __name__ == "__main__":
    main()
