"""Targeted checks for the LLM-first public solve path.

This scanner rejects task-literal routing, implicit semantic work ceilings,
and drift in the open-task defaults. It does not treat permissions, typed
contracts, or explicit owner limits as semantic binding.
"""
from __future__ import annotations

import ast
import os


def scan_semantic_freedom(root: str, rules: dict, py_files, source_tree) -> list:
    """Return task preselection and implicit-default findings."""
    root_is_canary = not os.path.isdir(os.path.join(root, "loop"))
    policed = set(rules.get("llm_first_semantic_modules", ()))
    task_names = {
        "task", "task_text", "original_task", "original_input",
        "normalized_interpretation"}
    findings = []
    for rel in py_files(root):
        normalized = rel.replace(os.sep, "/")
        tree = source_tree(os.path.join(root, rel))
        if tree is None:
            continue
        if root_is_canary or normalized in policed:
            for node in ast.walk(tree):
                if not isinstance(node, (ast.If, ast.IfExp, ast.While)):
                    continue
                referenced = {
                    part.id for part in ast.walk(node.test)
                    if isinstance(part, ast.Name)} | {
                    part.attr for part in ast.walk(node.test)
                    if isinstance(part, ast.Attribute)}
                semantic_literals = [
                    part.value for part in ast.walk(node.test)
                    if isinstance(part, ast.Constant)
                    and isinstance(part.value, str)
                    and len(part.value.strip()) > 2]
                if referenced & task_names and semantic_literals:
                    findings.append({
                        "rule": "task_text_controls_solution",
                        "file": normalized, "line": node.lineno,
                        "detail": (
                            "task wording controls a product branch using "
                            f"{semantic_literals[:3]!r}; pass the open task "
                            "to model-led orientation instead"),
                    })
        ceilings = set(rules.get("unset_default_ceiling_fields", ()))
        for node in tree.body:
            if not isinstance(node, ast.ClassDef) or any(
                    marker in node.name.casefold()
                    for marker in ("fixture", "test", "benchmark", "live")):
                continue
            for field_node in node.body:
                if (isinstance(field_node, ast.AnnAssign)
                        and isinstance(field_node.target, ast.Name)
                        and field_node.target.id in ceilings
                        and isinstance(field_node.value, ast.Constant)
                        and isinstance(field_node.value.value, (int, float))
                        and not isinstance(field_node.value.value, bool)):
                    findings.append({
                        "rule": "implicit_semantic_work_ceiling",
                        "file": normalized, "line": field_node.lineno,
                        "detail": (
                            f"{node.name}.{field_node.target.id} defaults to "
                            f"{field_node.value.value!r}; use None and require "
                            "an explicit owner limit"),
                    })
    expected = rules.get("llm_first_defaults", {})
    for identity, fields in expected.items():
        relative, class_name = identity.split(":", 1)
        path = os.path.join(root, relative)
        if not os.path.isfile(path):
            if not root_is_canary:
                findings.append({
                    "rule": "llm_first_default_drift", "file": relative,
                    "line": 1, "detail": f"missing class {class_name}"})
            continue
        tree = source_tree(path)
        target = next((item for item in tree.body
                       if isinstance(item, ast.ClassDef)
                       and item.name == class_name), None)
        if target is None:
            findings.append({
                "rule": "llm_first_default_drift", "file": relative,
                "line": 1, "detail": f"missing class {class_name}"})
            continue
        observed = {}
        lines = {}
        for item in target.body:
            if not (isinstance(item, ast.AnnAssign)
                    and isinstance(item.target, ast.Name)):
                continue
            try:
                value = ast.literal_eval(item.value)
            except (ValueError, TypeError):
                if (isinstance(item.value, ast.Attribute)
                        and isinstance(item.value.value, ast.Name)):
                    value = f"{item.value.value.id}.{item.value.attr}"
                else:
                    continue
            observed[item.target.id] = value
            lines[item.target.id] = item.lineno
        for field_name, expected_value in fields.items():
            if observed.get(field_name, object()) != expected_value:
                findings.append({
                    "rule": "llm_first_default_drift", "file": relative,
                    "line": lines.get(field_name, target.lineno),
                    "detail": (
                        f"{class_name}.{field_name} must default to "
                        f"{expected_value!r}, observed "
                        f"{observed.get(field_name, '<missing>')!r}"),
                })
    return findings
