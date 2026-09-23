"""Import-boundary checks for the library ingestion component.

These checks read the exact source tree of src/loop_engine/core/library_ingestion
without importing it. They hold the component to its architecture contract
(its README): it depends only on its own records and three named core
modules; one module owns the network and one owns processes; each optional
library is imported only by the engine module that adopts it; only the
factory table names concrete engine classes; no class name ends in Node; it
keeps no store of its own; every record type is written name/vN; and nothing
in it reaches the serving, approval or release code.
"""
import ast
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "src/loop_engine/core/library_ingestion"
TOOL = ROOT / "tools/ingest_outside_material.py"
#: The core modules outside its own folder that the component may use, and why.
ALLOWED_CORE_MODULES = {"facets": "the effect names the engine defines",
                        "model_call_records": "the repository's own secret patterns",
                        "ollama_client": "the sanctioned model client, used only by the model outline engine"}
#: Standard library modules, plus the base dependencies of this package.
STANDARD = {"__future__", "base64", "collections", "copy", "dataclasses", "datetime", "functools", "hashlib",
            "itertools", "json", "os", "pathlib", "re", "shutil", "subprocess", "tempfile", "time", "urllib"}
#: Optional or base libraries, each allowed only in the modules that adopt it.
LIBRARY_OWNERS = {"datasketch": {"near_duplicate_datasketch.py"}, "skills_ref": {"format_skills_ref.py"},
                  "jsonschema": {"format_json_schema.py"},
                  "tomllib": {"format_connection.py", "format_json_schema.py"},
                  "tomli": {"format_connection.py", "format_json_schema.py"},
                  "yaml": {"skill_rendering.py", "source_github.py", "source_declarations.py"},
                  "urllib": {"https_transport.py"}, "subprocess": {"processes.py"}}
#: Code the component must never reach: serving, approval and release.
FORBIDDEN_NAMES = ("service_runtime", "provisioning", "build_host_catalogue_manifest",
                   "carry_catalogue_approvals", "catalog")


def _sources():
    paths = sorted(COMPONENT.glob("*.py"))
    return [(path, ast.parse(path.read_text(encoding="utf-8"))) for path in paths]


def _imports(tree):
    """Each import as (level, module name) with every imported name for a from-import."""
    for item in ast.walk(tree):
        if isinstance(item, ast.Import):
            for alias in item.names:
                yield 0, alias.name, ()
        elif isinstance(item, ast.ImportFrom):
            yield item.level, item.module or "", tuple(alias.name for alias in item.names)


def _engine_classes():
    """Every class of the component that declares an engine identity."""
    found = {}
    for path, tree in _sources():
        for item in tree.body:
            if isinstance(item, ast.ClassDef) and any(
                    isinstance(statement, ast.Assign)
                    and any(isinstance(target, ast.Name) and target.id == "engine_id"
                            for target in statement.targets) for statement in item.body):
                found[item.name] = path.name
    return found


class LibraryIngestionBoundaryChecks(unittest.TestCase):
    def test_the_component_holds_enough_modules_to_check(self):
        self.assertGreaterEqual(len(_sources()), 30)

    def test_the_component_depends_only_on_its_own_records_and_named_core_modules(self):
        for path, tree in _sources():
            for level, module, _names in _imports(tree):
                top = module.split(".")[0]
                if level == 1:
                    self.assertTrue((COMPONENT / f"{top}.py").is_file(), f"{path.name}: .{module}")
                elif level == 2:
                    self.assertIn(top, ALLOWED_CORE_MODULES, f"{path.name}: ..{module}")
                else:
                    self.assertNotIn("loop_engine", module, f"{path.name}: {module}")
                    self.assertTrue(top in STANDARD or top in LIBRARY_OWNERS, f"{path.name}: {module}")

    def test_each_library_is_imported_only_by_the_modules_that_adopt_it(self):
        for path, tree in _sources():
            for level, module, _names in _imports(tree):
                top = module.split(".")[0]
                if level == 0 and top in LIBRARY_OWNERS:
                    self.assertIn(path.name, LIBRARY_OWNERS[top], f"{path.name} imports {module}")

    def test_only_the_factory_table_names_the_concrete_engine_classes(self):
        engines = _engine_classes()
        self.assertGreaterEqual(len(engines), 12, engines)
        for path, tree in _sources():
            if path.name == "engines.py" or path.name.endswith("_checks.py"):
                continue
            for _level, _module, names in _imports(tree):
                self.assertFalse(set(names) & set(engines), f"{path.name} names {set(names) & set(engines)}")
        tool = ast.parse(TOOL.read_text(encoding="utf-8"))
        for _level, _module, names in _imports(tool):
            self.assertFalse(set(names) & set(engines), f"the tool names {set(names) & set(engines)}")

    def test_no_class_name_ends_in_node_and_the_component_keeps_no_store(self):
        for path, tree in _sources():
            for item in ast.walk(tree):
                if isinstance(item, ast.ClassDef):
                    self.assertFalse(item.name.endswith("Node"), f"{path.name}: {item.name}")
            for _level, module, _names in _imports(tree):
                self.assertNotIn(module.split(".")[0], ("sqlite3", "duckdb", "shelve", "dbm"), path.name)

    def test_every_record_type_is_written_name_and_version(self):
        declared = re.compile(r'^[A-Z_]*RECORD_TYPE\s*=\s*"([^"]+)"', re.M)
        found = []
        for path in sorted(COMPONENT.glob("*.py")):
            found += [(path.name, value) for value in declared.findall(path.read_text(encoding="utf-8"))]
        self.assertGreaterEqual(len(found), 20)
        for name, value in found:
            self.assertRegex(value, r"^[a-z][a-z0-9_]*/v[1-9][0-9]*$", name)

    def test_nothing_in_the_component_reaches_serving_approval_or_release(self):
        for path, tree in _sources():
            for _level, module, _names in _imports(tree):
                self.assertFalse(any(part in FORBIDDEN_NAMES for part in module.split(".")),
                                 f"{path.name} imports {module}")


if __name__ == "__main__":
    unittest.main()
