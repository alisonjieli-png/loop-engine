"""Authored expected answers, independent of the candidate implementations."""
CASES = {
    "schedule_dag_earliest_times": [
        ({"tasks": [{"id": "a", "duration": 3, "depends_on": []}, {"id": "b", "duration": 5, "depends_on": []}, {"id": "c", "duration": 2, "depends_on": ["a", "b"]}]},
         {"duration": 7, "schedule": [{"id": "a", "start": 0, "finish": 3}, {"id": "b", "start": 0, "finish": 5}, {"id": "c", "start": 5, "finish": 7}]}),
        ({"tasks": [{"id": "z", "duration": 0, "depends_on": []}]}, {"duration": 0, "schedule": [{"id": "z", "start": 0, "finish": 0}]}),
        ({"tasks": [{"id": "a", "duration": 1, "depends_on": ["a"]}]}, None),
        ({"tasks": [{"id": "a", "duration": True, "depends_on": []}]}, None),
    ],
    "cover_pairwise_configuration_values": [
        ({"factors": {"a": ["0", "1"], "b": ["0", "1"], "c": ["0", "1"]}},
         {"cases": [{"a": "0", "b": "0", "c": "0"}, {"a": "0", "b": "1", "c": "1"}, {"a": "1", "b": "0", "c": "1"}, {"a": "1", "b": "1", "c": "0"}], "total_pairs": 12, "covered_pairs": 12}),
        ({"factors": {"a": ["x", "y"], "b": ["z"]}}, {"cases": [{"a": "x", "b": "z"}, {"a": "y", "b": "z"}], "total_pairs": 2, "covered_pairs": 2}),
        ({"factors": {"a": ["x", "x"], "b": ["z"]}}, None),
        ({"factors": {"a": ["x"]}}, None),
    ],
    "compare_primitive_object_contracts": [
        ({"old": {"fields": {"age": "integer"}, "required": ["age"], "allow_extra": False}, "new": {"fields": {"age": "number"}, "required": ["age"], "allow_extra": False}}, {"compatible": True, "breaking_changes": []}),
        ({"old": {"fields": {"age": "number"}, "required": [], "allow_extra": False}, "new": {"fields": {"age": "integer", "name": "string"}, "required": ["name"], "allow_extra": False}}, {"compatible": False, "breaking_changes": [{"code": "changed_type", "field": "age"}, {"code": "new_required_field", "field": "name"}]}),
        ({"old": {"fields": {}, "required": [], "allow_extra": True}, "new": {"fields": {"x": "string"}, "required": [], "allow_extra": True}}, {"compatible": False, "breaking_changes": [{"code": "extra_field_constrained", "field": "x"}]}),
        ({"old": {"fields": {}, "required": ["missing"], "allow_extra": False}, "new": {"fields": {}, "required": [], "allow_extra": False}}, None),
    ],
    "pack_first_fit_decreasing_batches": [
        ({"capacity": 8, "items": [{"id": "a", "size": 6}, {"id": "b", "size": 4}, {"id": "c", "size": 4}, {"id": "d", "size": 2}]}, {"bins": [{"item_ids": ["a", "d"], "used": 8}, {"item_ids": ["b", "c"], "used": 8}]}),
        ({"capacity": 1, "items": []}, {"bins": []}),
        ({"capacity": 3, "items": [{"id": "a", "size": 4}]}, None),
        ({"capacity": 0, "items": []}, None),
    ],
    "audit_functional_dependency_rows": [
        ({"determinants": ["a"], "dependents": ["b"], "rows": [{"a": 1, "b": "x"}, {"a": 1, "b": "y"}, {"a": 2, "b": "z"}]}, {"violations": [{"determinant": [1], "dependent_variants": [["x"], ["y"]], "row_indices": [0, 1]}]}),
        ({"determinants": ["a"], "dependents": ["b"], "rows": [{"a": True, "b": "x"}, {"a": 1, "b": "y"}]}, {"violations": []}),
        ({"determinants": ["a"], "dependents": ["b"], "rows": [{"a": 1}]}, None),
        ({"determinants": ["a"], "dependents": ["a"], "rows": []}, None),
    ],
    "find_strongly_connected_components": [
        ({"vertices": ["a", "b", "c"], "edges": [["a", "b"], ["b", "a"], ["b", "c"]]}, {"components": [["a", "b"], ["c"]], "cyclic_components": [["a", "b"]]}),
        ({"vertices": ["x"], "edges": [["x", "x"]]}, {"components": [["x"]], "cyclic_components": [["x"]]}),
        ({"vertices": ["a"], "edges": [["a", "b"]]}, None),
        ({"vertices": ["a", "a"], "edges": []}, None),
    ],
    "simulate_exact_token_bucket": [
        ({"capacity": 3, "initial_tokens": 1, "refill_per_second": 1, "requests": [{"id": "a", "at_ms": 0, "tokens": 2}, {"id": "b", "at_ms": 1000, "tokens": 2}, {"id": "c", "at_ms": 1500, "tokens": 1}, {"id": "d", "at_ms": 2000, "tokens": 1}]}, {"decisions": [{"id": "a", "allowed": False, "tokens_after": {"numerator": 1, "denominator": 1}}, {"id": "b", "allowed": True, "tokens_after": {"numerator": 0, "denominator": 1}}, {"id": "c", "allowed": False, "tokens_after": {"numerator": 1, "denominator": 2}}, {"id": "d", "allowed": True, "tokens_after": {"numerator": 0, "denominator": 1}}]}),
        ({"capacity": 2, "initial_tokens": 0, "refill_per_second": 100, "requests": [{"id": "a", "at_ms": 1000, "tokens": 2}]}, {"decisions": [{"id": "a", "allowed": True, "tokens_after": {"numerator": 0, "denominator": 1}}]}),
        ({"capacity": 2, "initial_tokens": 3, "refill_per_second": 1, "requests": []}, None),
        ({"capacity": 2, "initial_tokens": 2, "refill_per_second": 1, "requests": [{"id": "a", "at_ms": 2, "tokens": 1}, {"id": "b", "at_ms": 1, "tokens": 1}]}, None),
    ],
    "audit_boolean_rule_coverage": [
        ({"variables": ["x"], "rules": [{"id": "a", "when": {"x": False}, "decision": "blue"}, {"id": "b", "when": {"x": True}, "decision": "red"}]}, {"unambiguous_count": 2, "uncovered": [], "conflicts": []}),
        ({"variables": ["x"], "rules": [{"id": "a", "when": {"x": True}, "decision": "blue"}, {"id": "b", "when": {"x": True}, "decision": "red"}]}, {"unambiguous_count": 0, "uncovered": [{"x": False}], "conflicts": [{"assignment": {"x": True}, "rule_ids": ["a", "b"]}]}),
        ({"variables": ["x"], "rules": [{"id": "a", "when": {"unknown": True}, "decision": "red"}]}, None),
        ({"variables": ["x"], "rules": [{"id": "a", "when": {"x": 1}, "decision": "red"}]}, None),
    ],
    "decode_u16_length_prefixed_frames": [
        ({"hex": "00036162630000"}, {"frames_hex": ["616263", ""], "count": 2}),
        ({"hex": ""}, {"frames_hex": [], "count": 0}),
        ({"hex": "00"}, None),
        ({"hex": "000261"}, None),
    ],
    "evaluate_bounded_rational_expression": [
        ({"expression": "1/3 + 1/6"}, {"numerator": 1, "denominator": 2}),
        ({"expression": "-(5 - 8) * 2 / 3"}, {"numerator": 2, "denominator": 1}),
        ({"expression": "__import__('os')"}, None),
        ({"expression": "2**99"}, None),
        ({"expression": "1 / 0"}, None),
    ],
    "resolve_literal_named_template": [
        ({"template": "Hello ${who}", "variables": {"who": "${later}"}}, {"text": "Hello ${later}"}),
        ({"template": "${x}/${x}", "variables": {"x": "a"}}, {"text": "a/a"}),
        ({"template": "Hello ${who}", "variables": {}}, None),
        ({"template": "Hello", "variables": {"unused": "x"}}, None),
        ({"template": "${broken", "variables": {}}, None),
    ],
    "project_json_pointer_values": [
        ({"document": {"a/b": [10, 20], "~1": "literal", "": False}, "pointers": ["/a~1b/1", "/~01", "/"]}, {"values": [20, "literal", False]}),
        ({"document": [1, "x"], "pointers": [""]}, {"values": [[1, "x"]]}),
        ({"document": [1], "pointers": ["/01"]}, None),
        ({"document": {}, "pointers": ["/absent"]}, None),
        ({"document": {}, "pointers": ["#/"]}, None),
    ],
}

# Successor contract cases, written before changing the candidate implementation.
REPAIR_CASES = {
    "schedule_dag_earliest_times": [
        ({"tasks": [{"id": "a", "duration": 1.0, "depends_on": []}]}, {"duration": 1, "schedule": [{"id": "a", "start": 0, "finish": 1}]}),
        ({"tasks": [{"id": "a", "duration": 1.5, "depends_on": []}]}, None),
    ],
    "audit_functional_dependency_rows": [
        ({"determinants": ["a"], "dependents": ["b"], "rows": [{"a": "x", "b": 1, "unused": {"nested": True}}]}, {"violations": []}),
        ({"determinants": ["a"], "dependents": ["b"], "rows": [{"a": "x", "b": {"nested": True}}]}, None),
        ({"determinants": ["a"], "dependents": ["b"], "rows": [{"a": 1.0, "b": "x"}, {"a": 1, "b": "y"}]}, {"violations": [{"determinant": [1], "dependent_variants": [["x"], ["y"]], "row_indices": [0, 1]}]}),
    ],
    "pack_first_fit_decreasing_batches": [
        ({"capacity": 8.0, "items": [{"id": "a", "size": 6.0}, {"id": "b", "size": 2.0}]}, {"bins": [{"item_ids": ["a", "b"], "used": 8}]}),
    ],
    "simulate_exact_token_bucket": [
        ({"capacity": 2.0, "initial_tokens": 1.0, "refill_per_second": 1.0, "requests": [{"id": "a", "at_ms": 1000.0, "tokens": 2.0}]}, {"decisions": [{"id": "a", "allowed": True, "tokens_after": {"numerator": 0, "denominator": 1}}]}),
    ],
}
for method, additions in REPAIR_CASES.items():
    CASES[method].extend(additions)
