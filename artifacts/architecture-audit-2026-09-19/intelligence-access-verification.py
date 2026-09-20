"""Offline checks and in-memory mutants for intelligence access repairs.

All executable probe payloads are supplied pure callables. Existing retrieval
checks may use installed local embedding weights; this runner makes no provider
or cloud request. Set HF_HUB_OFFLINE=1 when running it.
"""
from __future__ import annotations

import hashlib
from contextlib import ExitStack
import importlib
import inspect
import json
import textwrap
from pathlib import Path
from unittest.mock import patch


MODULES = (
    "loop_engine.core.code_intelligence_assets",
    "loop_engine.loop.loop_capsule",
    "loop_engine.core.intelligence_layers",
    "loop_engine.core.retrieval",
    "loop_engine.core.store_serve",
    "loop_engine.core.intelligence_portfolio",
    "loop_engine.core.reusable_capability_checks",
    "loop_engine.loop.capability_loops",
    "loop_engine.loop.intelligence_loops",
    "loop_engine.core.adaptive_practitioner_orientation_capabilities",
)


def run_checks(module):
    try:
        checks = module.self_test()["tests"]
        return {"module": module.__name__, "checks": len(checks),
                "failed": [row.get("name", row.get("test", "unnamed"))
                           for row in checks if row.get("passed") is not True],
                "not_tested": [row for row in checks if row.get("not_tested")]}
    except Exception as exc:
        return {"module": module.__name__, "checks": None,
                "failed": [type(exc).__name__ + ": " + str(exc)], "not_tested": []}


def rewrite(original, old, new):
    function = original.fget if isinstance(original, property) else original
    source = textwrap.dedent(inspect.getsource(function))
    if source.count(old) != 1:
        raise RuntimeError("mutant target is not unique: " + old)
    namespace = {}
    exec(compile(source.replace(old, new), "<intelligence-contract-mutant>", "exec"),
         function.__globals__, namespace)
    return namespace[function.__name__]


def public_candidate_refused(assets, references):
    calls = []
    spec = assets.spec_from_template(
        "pure_function", asset_id="probe.candidate", name="Candidate",
        description="Unadmitted candidate", source_kind="local_path",
        body_ref=references.ExternalPayloadRef("memory://candidate", "a" * 64),
        entrypoints=("run",), license="MIT")

    def resolve(_):
        calls.append("materialized")
        return references.MaterializedPayload({"run": lambda value: value + 1}, "a" * 64)

    try:
        assets.execute_code_ref(assets.CodeRefExecutionRequest(
            assets.code_asset_capsule(spec).to_ref(), resolve, entrypoint="run", inputs=1))
    except assets.CodeAssetAdmissionError:
        return not calls
    return False


def main():
    modules = {name: importlib.import_module(name) for name in MODULES}
    baseline = [run_checks(module) for module in modules.values()]
    if any(row["failed"] for row in baseline):
        print(json.dumps({"baseline": baseline, "passed": False}, indent=2))
        return 1
    assets, references, layers, retrieval = (modules[name] for name in MODULES[:4])
    mutants = []

    def exercise(name, module, owner, attribute, replacement):
        original = getattr(owner, attribute)
        with ExitStack() as stack:
            stack.enter_context(patch.object(owner, attribute, replacement))
            # Simulate re-importing the changed definition for its existing
            # direct-import consumers, rather than testing stale aliases.
            for consumer_name in ("loop_engine.core.code_intelligence_asset_checks",
                                  "loop_engine.core.reusable_capability_flywheel"):
                consumer = importlib.import_module(consumer_name)
                if getattr(consumer, attribute, None) is original:
                    stack.enter_context(patch.object(consumer, attribute, replacement))
            result = run_checks(module)
        mutants.append({"name": name, "detected": bool(result["failed"]),
                        "failing_checks": result["failed"]})

    with patch.object(assets, "_admitted_entrypoint", lambda request: request.entrypoint):
        candidate_rejected = public_candidate_refused(assets, references)
    mutants.append({"name": "bypass_authoritative_Code_admission", "detected": not candidate_rejected,
                    "failing_checks": [] if candidate_rejected else ["public_candidate_refused_before_materialization"]})
    exercise("omit_data_references_from_qualification", assets, assets.CodeAssetSpec,
             "qualification_digest", rewrite(
                 assets.CodeAssetSpec.qualification_digest,
                 'body["data_refs"] = [_reference_dict(ref) for ref in self.data_refs]',
                 'pass'))
    exercise("omit_qualification_from_selected_reference_identity", assets,
             references.IntelligenceItemPackage, "digest", rewrite(
                 references.IntelligenceItemPackage.digest,
                 'identity["qualification_digest"] = self.handshake.qualification_digest',
                 'pass'))
    exercise("accept_unsupported_Code_asset_schema", assets, assets.CodeAssetSpec, "from_dict", classmethod(rewrite(
        assets.CodeAssetSpec.from_dict.__func__,
        'if record_type != SPEC_RECORD_TYPE:', 'if False:').__func__))
    exercise("construct_unsupported_qualification_schema", assets, assets.CodeAssetSpec, "__post_init__", rewrite(
        assets.CodeAssetSpec.__post_init__,
        'if self.qualification_version != QUALIFICATION_VERSION:', 'if False:'))
    exercise("accept_unsupported_intelligence_reference_schema", references,
             references.IntelligenceItemRef, "from_dict", classmethod(rewrite(
                 references.IntelligenceItemRef.from_dict.__func__,
                 'if not isinstance(body, dict) or body.get("record_type") != REFERENCE_SCHEMA:',
                 'if False:').__func__))
    exercise("ignore_stored_admission_evidence_integrity", assets,
             assets.CodeAssetAdmissionRecord, "from_dict", classmethod(rewrite(
                 assets.CodeAssetAdmissionRecord.from_dict.__func__,
                 'if expected != record.digest:', 'if False:').__func__))
    exercise("ignore_selected_Code_contract", assets, assets, "_admitted_entrypoint", rewrite(
        assets._admitted_entrypoint,
        'if (ref.item_ref != expected.item_ref or ref.handshake != expected.handshake\n            or ref.payload_ref != expected.payload_ref\n            or ref.payload_digest != expected.payload_digest or ref.digest != expected.digest):',
        'if False:'))
    exercise("permit_unavailable_effectful_callable", assets, assets, "_admitted_entrypoint", rewrite(
        assets._admitted_entrypoint,
        'if "deterministic" not in spec.modes or set(spec.effects) - {"pure"}:',
        'if False:'))
    exercise("ignore_changed_inline_value", references, references, "load_intelligence_ref", rewrite(
        references.load_intelligence_ref,
        'if measured != ref.payload_digest or (',
        'if False and measured != ref.payload_digest or ('))
    exercise("discard_inline_record_version", references, references, "intelligence_package_from_record", rewrite(
        references.intelligence_package_from_record,
        'version=str(body.get("version") or "1.0.0")',
        'version="1.0.0"'))
    exercise("expand_unified_result_limit", layers, layers, "query_intelligence", rewrite(
        layers.query_intelligence,
        'requested = max(1, len(combined)) if request.top_n is None else request.top_n',
        'requested = max(1, len(combined)) if request.top_n is None else request.top_n * 4'))
    exercise("bound_pool_before_required_facets", retrieval, retrieval.Retriever, "search", rewrite(
        retrieval.Retriever.search,
        'pool_limit = max(1, len(self._records)) if not f.is_empty() else requested * 2',
        'pool_limit = requested * 2'))
    exercise("ignore_facet_preference_during_sort", retrieval, retrieval.Retriever, "search", rewrite(
        retrieval.Retriever.search, '0.01 * eligible[t[0]][1]', '0.0'))
    exercise("turn_backend_failure_into_no_matches", retrieval, retrieval.SqliteFtsBackend, "search", rewrite(
        retrieval.SqliteFtsBackend.search,
        'raise RetrievalUnavailableError("SQLite lexical retrieval failed") from exc',
        'return []'))
    paths = {Path(module.__file__) for module in modules.values()}
    for name in ("loop_engine.core.code_intelligence_asset_checks",
                 "loop_engine.core.intelligence_portfolio_checks",
                 "loop_engine.core.reusable_capability_resolution"):
        paths.add(Path(importlib.import_module(name).__file__))
    passed = all(row["detected"] for row in mutants)
    print(json.dumps({"record_type": "intelligence_access_verification/v1",
                      "baseline": baseline,
                      "baseline_candidate_refused": public_candidate_refused(assets, references),
                      "mutants": mutants, "passed": passed,
                      "source_sha256": {str(path.relative_to(Path.cwd())):
                                        hashlib.sha256(path.read_bytes()).hexdigest()
                                        for path in sorted(paths)}}, indent=2, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
