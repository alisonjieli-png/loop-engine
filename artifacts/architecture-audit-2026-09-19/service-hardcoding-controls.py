"""Qualify exact public-protocol and loopback-fixture audit allowances.

All modified sources exist only in memory. No request, provider, credential
lookup, source mutation, or detector modification is performed by a canary.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

from loop_engine_devtools.assurance.hardcoding import _PythonLiteralVisitor, _load_allowlist, _text_findings

ROOT = Path(__file__).resolve().parents[2]
PREFIX = "src/loop_engine/core/service_runtime/"
EXPECTED = {
    "hardcoding.ebc6c07b26c61720ddfc19ed", "hardcoding.839518dfbbe7804c3e423907",
    "hardcoding.883306ba058d99596dd8ac98", "hardcoding.efc735fee76000b94b68ca6f",
    "hardcoding.24ca9147889627b85cfe5c45",
}


def inspect(relative, source):
    tree = ast.parse(source)
    visitor = _PythonLiteralVisitor(ROOT, ROOT / relative, tree, "memory-control", False, {})
    visitor.visit(tree)
    findings = {row.finding_id: row for row in visitor.findings}
    allowed, problems = _load_allowlist(ROOT / "devtools/hardcoding-allowlist.yaml", findings,
                                      require_present=False)
    blocking = {row.finding_id for row in findings.values() if row.severity in ("high", "critical")}
    return {"suppressed": blocking & set(allowed), "blocking": blocking - set(allowed),
            "problems": problems}


def main():
    names = ("http.py", "http_test_fixtures.py", "stripe_provider.py")
    sources = {name: (ROOT / (PREFIX + name)).read_text("utf-8") for name in names}
    initial = {name: inspect(PREFIX + name, source) for name, source in sources.items()}
    checks = []
    def check(name, result): checks.append({"test": name, "passed": bool(result)})

    admitted = set().union(*(row["suppressed"] for row in initial.values()))
    check("only_the_five_reviewed_exact_public_literals_are_admitted", admitted == EXPECTED)
    check("exact_allowances_have_no_loader_errors", all(not row["problems"] for row in initial.values()))
    for name, source in sources.items():
        moved = inspect(PREFIX + "unreviewed_" + name, source)
        check("moving_" + name + "_does_not_transfer_the_allowance",
              not moved["suppressed"] and bool(moved["blocking"]))
    source = sources["http.py"]
    changed = source.replace("Bearer resource_metadata", "Bearer unrelated_metadata")
    result = inspect(PREFIX + "http.py", changed)
    check("a_changed_authentication_challenge_remains_blocking",
          changed != source and bool(result["blocking"] - initial["http.py"]["blocking"])
          and "hardcoding.ebc6c07b26c61720ddfc19ed" not in result["suppressed"])
    planted = source + "\nUNREVIEWED_CREDENTIAL = " + repr("sk-" + "X" * 24) + "\n"
    result = inspect(PREFIX + "http.py", planted)
    check("a_secret_shaped_literal_in_the_same_file_remains_blocking",
          bool(result["blocking"] - initial["http.py"]["blocking"]))
    source = sources["http_test_fixtures.py"]
    changed = source.replace("http://127.0.0.1:", "https://unexpected.invalid:")
    result = inspect(PREFIX + "http_test_fixtures.py", changed)
    check("external_origins_cannot_inherit_loopback_fixture_allowances",
          changed != source and not result["suppressed"] and bool(result["blocking"]))
    source = sources["stripe_provider.py"]
    changed = source.replace("https://api.stripe.com", "https://unexpected.invalid")
    result = inspect(PREFIX + "stripe_provider.py", changed)
    check("a_changed_payment_origin_is_not_silently_approved",
          changed != source and not result["suppressed"] and bool(result["blocking"]))
    from unittest.mock import patch
    relative = "tools/architecture_report/app.js"
    javascript = (ROOT / relative).read_text("utf-8")
    read_text = Path.read_text
    def inspect_script(source):
        def read(path, *args, **kwargs):
            return source if path == ROOT / relative else read_text(path, *args, **kwargs)
        with patch.object(Path, "read_text", read):
            findings, _count, _state = _text_findings(ROOT, ROOT / relative, "memory-control", False, False)
        by_id = {row.finding_id: row for row in findings}
        allowed, problems = _load_allowlist(ROOT / "devtools/hardcoding-allowlist.yaml", by_id, require_present=False)
        high = {row.finding_id for row in findings if row.severity in ("high", "critical")}
        return {"suppressed": high & set(allowed), "blocking": high - set(allowed), "problems": problems}
    original = inspect_script(javascript)
    changed = inspect_script(javascript.replace("http://www.w3.org/2000/svg", "https://unexpected.invalid/svg"))
    injected = inspect_script(javascript + '\nconst unauthorizedOrigin = "https://unexpected.invalid";\n')
    check("the_exact_XML_namespace_is_allowed_without_exempting_the_script",
          original["suppressed"] == {"hardcoding.1e8eaa28b82cba8bf4ed8d8a"} and not original["problems"])
    check("a_changed_XML_namespace_does_not_inherit_the_allowance", not changed["suppressed"] and bool(changed["blocking"]))
    check("an_added_endpoint_in_the_same_script_remains_blocking", bool(injected["blocking"] - original["blocking"]))
    report = {"record_type": "service_audit_allowance_controls/v1", "tests": checks,
        "passed": sum(row["passed"] for row in checks), "total": len(checks),
        "all_passed": all(row["passed"] for row in checks),
        "source_sha256": {PREFIX + name: hashlib.sha256(source.encode()).hexdigest()
                           for name, source in sources.items()},
        "detector_sha256": hashlib.sha256((ROOT / "devtools/src/loop_engine_devtools/assurance/hardcoding.py").read_bytes()).hexdigest(),
        "baseline_sha256": hashlib.sha256((ROOT / "devtools/hardcoding-ci-baseline.json").read_bytes()).hexdigest()}
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
