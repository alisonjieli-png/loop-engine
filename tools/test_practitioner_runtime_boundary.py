"""Protect the extracted Practitioner helpers from recreating their old cycle."""
from __future__ import annotations

import ast
from importlib.util import resolve_name
from pathlib import Path
import unittest

PACKAGE = Path(__file__).resolve().parents[1] / "src/loop_engine/core/practitioner_runtime"
FORBIDDEN = "loop_engine.core.adaptive_practitioner_records"


def facade_imports(source: str) -> list[str]:
    found = []
    for item in ast.walk(ast.parse(source)):
        if isinstance(item, ast.Import):
            found.extend(alias.name for alias in item.names if alias.name == FORBIDDEN)
        elif isinstance(item, ast.ImportFrom):
            name = "." * item.level + (item.module or "")
            resolved = resolve_name(name, "loop_engine.core.practitioner_runtime") if item.level else name
            if resolved == FORBIDDEN:
                found.append(resolved)
    return found


class PractitionerBoundaryTests(unittest.TestCase):
    def test_helpers_do_not_import_the_records_facade(self):
        for path in PACKAGE.glob("*.py"):
            self.assertEqual(facade_imports(path.read_text("utf-8")), [], path.name)

    def test_relative_and_absolute_cycle_canaries_are_detected(self):
        for source in (
            "from ..adaptive_practitioner_records import AdaptiveRunServices",
            "import loop_engine.core.adaptive_practitioner_records",
        ):
            self.assertEqual(facade_imports(source), [FORBIDDEN])

    def test_callers_import_extracted_objects_from_the_owning_module(self):
        moved = {"ADAPTIVE_CAPABILITIES", "AdaptivePractitionerError", "_stage_for"}
        for path in PACKAGE.parents[1].rglob("*.py"):
            for item in ast.walk(ast.parse(path.read_text("utf-8"))):
                if isinstance(item, ast.ImportFrom) and (item.module or "").endswith(
                        "adaptive_practitioner_records"):
                    self.assertFalse(moved.intersection(alias.name for alias in item.names), path)


if __name__ == "__main__":
    unittest.main()
