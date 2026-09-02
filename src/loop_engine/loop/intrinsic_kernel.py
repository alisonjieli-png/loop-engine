"""Finite native substrate for registered deterministic atomic primitives.

Native Python string, JSON, mapping, and sequence operations are allowed here
because a Loop must eventually reach a finite execution substrate. This module
contains no task, domain, provider, storage, permission, policy, routing, or
example logic. Callers use ``atomic_primitives.run_atomic_primitive`` so every
semantic operation still has a logical Loop identity and Run History.
"""
from __future__ import annotations

import hashlib
import json


INTRINSIC_PRIMITIVES = (
    "core.primitive.text.constant",
    "core.primitive.text.combine",
    "core.primitive.text.normalize",
    "core.primitive.text.utf8_size",
    "core.primitive.number.ceil_divide",
    "core.primitive.component.read",
    "core.primitive.json.serialize",
    "core.primitive.json.deserialize",
    "core.primitive.record.project",
    "core.primitive.record.select",
    "core.primitive.record.merge",
    "core.primitive.sequence.order",
)


class IntrinsicKernelError(ValueError):
    """An intrinsic request used an unregistered operation or invalid input."""


def intrinsic_content_digest(value: object) -> str:
    """Return the canonical digest used by atomic LoopValue results."""
    body = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        default=str)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _mapping(parameters: tuple[tuple[str, object], ...]) -> dict:
    return dict(parameters)


def execute_intrinsic(
        primitive_id: str, values: tuple[object, ...],
        parameters: tuple[tuple[str, object], ...]) -> object:
    """Execute one exact native primitive without policy or hidden effects."""
    if primitive_id not in INTRINSIC_PRIMITIVES:
        raise IntrinsicKernelError("intrinsic primitive is not registered")
    params = _mapping(parameters)
    if primitive_id == "core.primitive.text.constant":
        value = params.get("value")
        if not isinstance(value, str):
            raise IntrinsicKernelError("text.constant needs one string value")
        return value
    if primitive_id == "core.primitive.component.read":
        if "value" not in params:
            raise IntrinsicKernelError("component.read needs a value binding")
        return params["value"]
    if primitive_id == "core.primitive.text.combine":
        parts = (values[0] if len(values) == 1
                 and isinstance(values[0], tuple) else values)
        if any(not isinstance(value, str) for value in parts):
            raise IntrinsicKernelError("text.combine inputs must be strings")
        separator = params.get("separator", "")
        prefix = params.get("prefix", "")
        suffix = params.get("suffix", "")
        if any(not isinstance(item, str)
               for item in (separator, prefix, suffix)):
            raise IntrinsicKernelError("text.combine parameters must be strings")
        return prefix + separator.join(parts) + suffix
    if primitive_id == "core.primitive.text.normalize":
        if len(values) != 1 or not isinstance(values[0], str):
            raise IntrinsicKernelError("text.normalize needs one string")
        policy = params.get("whitespace_policy", "strip")
        if policy == "strip":
            return values[0].strip()
        if policy == "preserve":
            return values[0]
        raise IntrinsicKernelError("text.normalize policy is not registered")
    if primitive_id == "core.primitive.text.utf8_size":
        if len(values) != 1 or not isinstance(values[0], str):
            raise IntrinsicKernelError("text.utf8_size needs one string")
        return len(values[0].encode("utf-8"))
    if primitive_id == "core.primitive.number.ceil_divide":
        if (len(values) != 1 or not isinstance(values[0], int)
                or isinstance(values[0], bool)):
            raise IntrinsicKernelError("number.ceil_divide needs one integer")
        divisor = params.get("divisor")
        if not isinstance(divisor, int) or isinstance(divisor, bool) or divisor < 1:
            raise IntrinsicKernelError(
                "number.ceil_divide needs a positive divisor")
        return (values[0] + divisor - 1) // divisor
    if primitive_id == "core.primitive.json.serialize":
        if len(values) != 1:
            raise IntrinsicKernelError("json.serialize needs one value")
        return json.dumps(
            values[0], sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, default=str)
    if primitive_id == "core.primitive.json.deserialize":
        if len(values) != 1 or not isinstance(values[0], str):
            raise IntrinsicKernelError("json.deserialize needs one string")
        return json.loads(values[0])
    if primitive_id == "core.primitive.record.project":
        if len(values) != 1:
            raise IntrinsicKernelError("record.project needs one record")
        field_name = params.get("field")
        if not isinstance(field_name, str) or not field_name:
            raise IntrinsicKernelError("record.project needs a field")
        source = values[0]
        if isinstance(source, dict):
            if field_name not in source:
                raise IntrinsicKernelError("record.project field is absent")
            return source[field_name]
        if not hasattr(source, field_name):
            raise IntrinsicKernelError("record.project attribute is absent")
        return getattr(source, field_name)
    if primitive_id == "core.primitive.record.select":
        if len(values) != 1 or not isinstance(values[0], dict):
            raise IntrinsicKernelError("record.select needs one record")
        names = params.get("fields")
        if not isinstance(names, (list, tuple)) or not names:
            raise IntrinsicKernelError("record.select needs fields")
        present = {name: values[0][name]
                   for name in names if name in values[0]}
        absent = [name for name in names if name not in values[0]]
        # An absent field is reported in the result rather than dropped, so a
        # reader can tell "the record holds nothing here" from "this field was
        # never asked for". Selecting is not a place to fail a run.
        return {**present, "absent_from_packet": absent} if absent else present
    if primitive_id == "core.primitive.record.merge":
        if any(not isinstance(value, dict) for value in values):
            raise IntrinsicKernelError("record.merge inputs must be mappings")
        merged = {}
        for value in values:
            overlap = set(merged) & set(value)
            if overlap:
                raise IntrinsicKernelError(
                    "record.merge refuses competing keys")
            merged.update(value)
        return merged
    if primitive_id == "core.primitive.sequence.order":
        indices = params.get("indices")
        if (not isinstance(indices, tuple)
                or sorted(indices) != list(range(len(values)))):
            raise IntrinsicKernelError("sequence.order indices are invalid")
        return tuple(values[index] for index in indices)
    raise IntrinsicKernelError("intrinsic primitive has no implementation")


def self_test() -> dict:
    """Prove the kernel stays finite, pure, and task agnostic."""
    combined = execute_intrinsic(
        "core.primitive.text.combine", ("a", "b"),
        (("separator", "|"),))
    serialized = execute_intrinsic(
        "core.primitive.json.serialize", ({"b": 2, "a": 1},), ())
    refused = False
    try:
        execute_intrinsic("core.primitive.task.solve", (), ())
    except IntrinsicKernelError:
        refused = True
    tests = [{
        "test": "intrinsic_text_combine_is_exact",
        "passed": combined == "a|b", "detail": combined,
    }, {
        "test": "intrinsic_json_serialization_is_canonical",
        "passed": serialized == '{"a":1,"b":2}', "detail": serialized,
    }, {
        "test": "intrinsic_kernel_refuses_domain_operations",
        "passed": refused, "detail": "task.solve is not a primitive",
    }]
    passed = sum(item["passed"] for item in tests)
    return {"record_type": "intrinsic_kernel_test/v1", "tests": tests,
            "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
