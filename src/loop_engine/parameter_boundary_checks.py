"""Focused mutation checks for the three-parameter boundary.

The command wrapper runs planted defects and exact exception-registry checks.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import date
import json
from pathlib import Path
import tempfile
from typing import Any

import yaml

from .parameter_boundary import EXEMPTABLE_RULES, ScanRequest, scan_repository


_FIXTURE = '''
from dataclasses import dataclass
from typing import Any
def too_many(a: int, b: int, c: int, d: int) -> None: pass
def vararg_escape(*args: int) -> None: pass
def kwargs_escape(**kwargs: object) -> None: pass
def options_bag(options: dict[str, Any]) -> None: pass
def mutable_default(items: list[int] = []) -> None: pass
def boolean_modes(local: bool = False, cloud: bool = False) -> None: pass
@dataclass(frozen=True)
class WorkItemIR:
    a: int
    b: int
    c: int
    d: int
    e: int
def execute(request: WorkItemIR) -> WorkItemIR: return request
@dataclass(frozen=True)
class AddressArgumentsLoop:
    street: str
    city: str
    state: str
    postal_code: str
'''


def _registry(exception: dict[str, str] | None = None) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "policy": {"max_direct_parameters": 3, "boolean_flag_threshold": 2},
        "exceptions": [exception] if exception else [],
    }


def _exception(kind: str) -> dict[str, str]:
    record = {
        "exception_id": f"PB-{kind.upper()}",
        "file": "src/loop_engine/fixture.py",
        "symbol": "too_many",
        "rule": "parameter_count",
        "external_contract": "fixture callback v1",
        "reason": f"proves {kind} exception handling",
        "owner": "Loop Engine maintainers",
        "test": f"{kind}_exception_check",
        "introduced_version": "0.1.0",
        "removal_version": "0.2.0",
    }
    if kind == "broad":
        record["file"] = "src/loop_engine/*.py"
        record["symbol"] = "*"
    elif kind == "expired":
        record["introduced_version"] = "0.0.1"
        record["removal_version"] = "0.1.0"
    return record


def self_test() -> dict[str, Any]:
    """Exercise every detector against planted negative mutations."""
    tests: list[dict[str, Any]] = []

    def check(name: str, passed: bool, detail: str) -> None:
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        source = root / "src" / "loop_engine" / "fixture.py"
        source.parent.mkdir(parents=True)
        source.write_text(_FIXTURE, encoding="utf-8")
        registry = root / "exceptions.yaml"
        registry.write_text(yaml.safe_dump(_registry()), encoding="utf-8")
        request = ScanRequest(
            root=root, source_paths=("src/loop_engine",),
            exception_registry=registry,
            focus_files=("src/loop_engine/fixture.py",),
            current_version="0.1.0", as_of=date(2026, 8, 27),
            revision="fixture", require_registry=True,
        )
        report = scan_repository(request)
        rules = set(report["unapproved_by_rule"])
        check("negative_mutations_fire_every_source_detector",
              set(EXEMPTABLE_RULES) <= rules, f"detected: {sorted(rules)}")
        symbols = {item["symbol"] for item in report["violations"]}
        check("generated_schema_init_is_not_handwritten",
              "WorkItemIR.__init__" not in symbols and "execute" not in symbols,
              "passive many-field schema and typed request boundary remain clean")

        registry.write_text(yaml.safe_dump(_registry(_exception("exact"))),
                            encoding="utf-8")
        exact_report = scan_repository(request)
        matches = [item for item in exact_report["violations"]
                   if item.get("exception_id") == "PB-EXACT"]
        check("exact_exception_matches_once",
              len(matches) == 1 and matches[0]["approved"],
              f"approved matches: {len(matches)}")

        registry.write_text(yaml.safe_dump(_registry(_exception("broad"))),
                            encoding="utf-8")
        broad = scan_repository(request)
        check("broad_exception_is_rejected",
              broad["unapproved_by_rule"].get("broad_exception") == 1,
              str(broad["unapproved_by_rule"]))

        registry.write_text(yaml.safe_dump(_registry(_exception("expired"))),
                            encoding="utf-8")
        expired = scan_repository(request)
        check("expired_exception_is_rejected",
              expired["unapproved_by_rule"].get("expired_exception") == 1,
              str(expired["unapproved_by_rule"]))

        clean_root = root / "clean"
        for filename in ("parameter_boundary.py", "parameter_boundary_checks.py"):
            target = clean_root / "src" / "loop_engine" / filename
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text((Path(__file__).parent / filename).read_text(
                encoding="utf-8"), encoding="utf-8")
        clean_request = replace(
            request, root=clean_root, exception_registry=None,
            require_registry=False,
            focus_files=("src/loop_engine/parameter_boundary.py",
                         "src/loop_engine/parameter_boundary_checks.py"),
        )
        clean_report = scan_repository(clean_request)
        check("new_checker_modules_have_no_findings",
              clean_report["focused_unapproved_violations"] == 0,
              str(clean_report["focused_by_rule"]))

    passed = sum(1 for item in tests if item["passed"])
    return {"record_type": "parameter_boundary_self_test/v1", "tests": tests,
            "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}


def main() -> int:
    """Run the checker or its focused mutation suite."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--source", action="append", dest="sources")
    parser.add_argument("--registry")
    parser.add_argument("--focus", action="append", dest="focus_files")
    parser.add_argument("--revision", default="UNKNOWN")
    parser.add_argument("--current-version", default="0.0.0")
    parser.add_argument("--self-test", action="store_true")
    arguments = parser.parse_args()
    if arguments.self_test:
        report = self_test()
    else:
        registry = Path(arguments.registry) if arguments.registry else None
        report = scan_repository(ScanRequest(
            root=Path(arguments.root).resolve(),
            source_paths=tuple(arguments.sources or
                               ("src/loop_engine", "devtools/src")),
            exception_registry=registry,
            focus_files=tuple(arguments.focus_files or ()),
            current_version=arguments.current_version,
            revision=arguments.revision,
            require_registry=registry is not None,
        ))
    print(json.dumps(report, indent=2, sort_keys=True))
    passed = report.get("all_passed", report.get("passed", False))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
