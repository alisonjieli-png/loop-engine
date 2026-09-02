"""Checks for deterministic extensions, empty paths, and drift policy.

Owns ordering, compatibility, zero-work, and scoped fingerprint proof.
It does not invoke extension work.
"""
from __future__ import annotations

from dataclasses import replace

from ..loop.loop_definition import LoopDefinitionRef
from .development_planning import ResolutionDisposition
from .lifecycle_extensions import (
    DriftDisposition, ExecutionContextFingerprint, ExtensionResolutionRequest,
    LifecycleExtensionDefinition, ProcedureLifecycleDefinition,
    compare_fingerprints, resolve_extensions)


class _Registry:
    def resolve(self, ref):
        return ref


def self_test():
    tests=[]
    def check(name,ok,detail=""):
        tests.append({"test":name,"passed":bool(ok),"detail":detail})
    ref=LoopDefinitionRef("practitioner.fixture","1.0.0","a"*64)
    procedure=ProcedureLifecycleDefinition("procedure.software","1.0.0",
                                           ("before_execution","after_execution"))
    first=LifecycleExtensionDefinition(
        "extension-b","1.0.0","before_execution",20,"single",ref,
        "plan/v1","finding/v1",(),"fail_closed","silent","project")
    second=LifecycleExtensionDefinition(
        "extension-a","1.0.0","before_execution",10,"single",ref,
        "plan/v1","finding/v1",(),"fail_closed","silent","project")
    registry=_Registry()
    resolved=resolve_extensions(ExtensionResolutionRequest(
        procedure,"before_execution",(first,second),registry))
    check("extensions_sort_by_order_then_name",
          [x.extension_id for x in resolved.extensions]
          ==["extension-a","extension-b"])
    empty=resolve_extensions(ExtensionResolutionRequest(
        procedure,"after_execution",(first,second),registry))
    check("empty_event_is_distinct_and_has_no_extensions",
          empty.disposition is ResolutionDisposition.RESOLVED_EMPTY
          and not empty.extensions)
    base=ExecutionContextFingerprint(*("b"*64 for _ in range(8)))
    same=compare_fingerprints(base,base)
    check("unchanged_context_is_exact",same.disposition is DriftDisposition.UNCHANGED)
    changed=replace(base,extension_digest="c"*64)
    drift=compare_fingerprints(base,changed)
    check("extension_drift_requires_replan",
          drift.disposition is DriftDisposition.REQUIRES_REPLAN
          and drift.changed_dimensions==("extension_digest",))
    verification=replace(base,verification_digest="d"*64)
    check("verification_drift_requires_revalidation",
          compare_fingerprints(base,verification).disposition
          is DriftDisposition.REQUIRES_REVALIDATION)
    passed=sum(x["passed"] for x in tests)
    return {"record_type":"lifecycle_extensions_self_test/v1","tests":tests,
            "passed":passed,"total":len(tests),"all_passed":passed==len(tests)}
