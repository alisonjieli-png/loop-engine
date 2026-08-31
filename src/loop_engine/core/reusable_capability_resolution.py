"""Rebuild, resolve, and invoke promoted reusable capabilities.

Search reads a disposable catalog projection. Execution rechecks the current
authority record, exact artifact digest, admission, contracts, and effects.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, replace
from typing import Callable

from ..catalog.query import IntelligenceQuery
from ..loop.loop_role import LoopRole
from .code_intelligence_assets import (
    CodeRefExecutionContext, CodeRefExecutionRequest, code_asset_capsule,
    execute_code_ref)
from .reusable_capability_flywheel import (
    CapabilityAuthority, ReusableCapabilityError, _run_operation)
from .reusable_capability_records import (
    CapabilityCandidateMatch, CapabilityInvocationRecord, CapabilityNeed,
    CapabilityResolutionPlan, HybridAssistanceProfile,
    HybridAssistanceStage, ResolutionDisposition, content_digest)


def _tokens(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", value.casefold()))


@dataclass(frozen=True)
class ProjectionRebuildResult:
    projection_version: str
    record_count: int
    projection_digest: str
    record_refs: tuple[str, ...]
    manifest_ref: str
    loop_id: str = ""
    model_calls: int = 0


def rebuild_capability_projection_as_loop(
        authority: CapabilityAuthority,
        projection_store,
        projection_version: str,
        *, ledger=None, parent=None) -> ProjectionRebuildResult:
    """Rebuild the active search read model from current authority records."""
    if not isinstance(authority, CapabilityAuthority):
        raise ReusableCapabilityError(
            "projection rebuild requires CapabilityAuthority")

    def rebuild() -> ProjectionRebuildResult:
        states = authority.store.query(IntelligenceQuery(
            layers=("code",), artifact_kinds=("code_asset_state",),
            lifecycle=("registered",)))
        records = []
        for state in states:
            attributes = state["attributes"]
            spec = authority.active_spec(
                attributes["asset_id"], attributes["asset_version"])
            terms = tuple(spec.metadata.get("search_terms") or ())
            record_identity = content_digest({
                "projection_version": projection_version,
                "asset_id": spec.asset_id,
                "asset_version": spec.version,
                "qualification_digest": spec.qualification_digest,
            })[:24]
            record = {
                "record_id": f"capability_projection.{record_identity}",
                "record_version": projection_version,
                "intelligence_layer": "code",
                "source_collection": "projection",
                "artifact_kind": "capability_search_projection",
                "lifecycle": "registered",
                "namespace": str(
                    spec.metadata.get("namespace") or "org:local"),
                "attributes": {
                    "authority_record_ref": attributes["exact_record_id"],
                    "asset_id": spec.asset_id,
                    "asset_version": spec.version,
                    "operation_family": str(
                        spec.metadata.get("operation_family") or ""),
                    "semantic_summary": spec.description,
                    "input_contract_ref": spec.input_contract,
                    "input_contract_digest": content_digest(
                        spec.input_contract),
                    "output_contract_ref": spec.output_contract,
                    "output_contract_digest": content_digest(
                        spec.output_contract),
                    "effects": list(spec.effects),
                    "capabilities": list(
                        spec.metadata.get("capabilities") or ()),
                    "dependencies": list(spec.dependencies),
                    "environment": dict(
                        spec.metadata.get("environment") or {}),
                    "privacy_scope": str(
                        spec.metadata.get("privacy_scope") or "run_private"),
                    "tenant_scope": str(
                        spec.metadata.get("tenant_scope") or ""),
                    "license": spec.license,
                    "search_terms": list(terms),
                    "artifact_digest": spec.body_ref.digest,
                    "qualification_digest": spec.qualification_digest,
                    "admission_ref": spec.admission_ref,
                    "projection_version": projection_version,
                },
            }
            existing = projection_store.get(record["record_id"])
            if existing is not None and existing != record:
                raise ReusableCapabilityError(
                    "projection version already names different content")
            if existing is None:
                projection_store.put(record)
            records.append(record)
        refs = tuple(sorted(item["record_id"] for item in records))
        digest = content_digest(tuple(
            (item["record_id"], item["attributes"]["qualification_digest"])
            for item in sorted(records, key=lambda row: row["record_id"])))
        version_manifest = {
            "record_id": (
                "capability_projection_manifest."
                + content_digest(projection_version)[:24]),
            "record_version": projection_version,
            "intelligence_layer": "code",
            "source_collection": "projection",
            "artifact_kind": "capability_projection_manifest",
            "lifecycle": "registered",
            "namespace": "org:local",
            "attributes": {
                "projection_version": projection_version,
                "projection_digest": digest,
                "record_refs": list(refs),
            },
        }
        existing_manifest = projection_store.get(
            version_manifest["record_id"])
        if (existing_manifest is not None
                and existing_manifest != version_manifest):
            raise ReusableCapabilityError(
                "projection version already names different content")
        if existing_manifest is None:
            projection_store.put(version_manifest)
        active_manifest = {
            "record_id": "capability_projection_manifest.active",
            "record_version": projection_version,
            "intelligence_layer": "code",
            "source_collection": "projection",
            "artifact_kind": "capability_projection_active",
            "lifecycle": "registered",
            "namespace": "org:local",
            "attributes": {
                "manifest_ref": version_manifest["record_id"],
                "projection_version": projection_version,
                "projection_digest": digest,
            },
        }
        projection_store.put(active_manifest)
        return ProjectionRebuildResult(
            projection_version, len(records), digest, refs,
            version_manifest["record_id"])

    run = _run_operation(
        "rebuild reusable capability search projection", rebuild,
        LoopRole.INTELLIGENCE, "intelligence.code.resolve", "queried_by",
        ledger=ledger, parent=parent)
    return replace(
        run["value"], loop_id=run["loop_id"],
        model_calls=run["model_calls"])


def _active_projection_rows(projection_store) -> tuple[tuple[dict, ...], dict]:
    active = projection_store.get("capability_projection_manifest.active")
    if active is None:
        return (), {}
    if active.get("artifact_kind") != "capability_projection_active":
        raise ReusableCapabilityError(
            "active capability projection pointer is malformed")
    attributes = dict(active.get("attributes") or {})
    manifest_ref = str(attributes.get("manifest_ref") or "")
    manifest = projection_store.get(manifest_ref)
    if (manifest is None or manifest.get("artifact_kind")
            != "capability_projection_manifest"):
        raise ReusableCapabilityError(
            "active capability projection manifest is unavailable")
    manifest_attributes = dict(manifest.get("attributes") or {})
    if (attributes.get("projection_version")
            != manifest_attributes.get("projection_version")
            or attributes.get("projection_digest")
            != manifest_attributes.get("projection_digest")):
        raise ReusableCapabilityError(
            "active capability projection pointer changed")
    refs = tuple(manifest_attributes.get("record_refs") or ())
    if (len(refs) != len(set(refs))
            or any(not isinstance(item, str) or not item for item in refs)):
        raise ReusableCapabilityError(
            "capability projection manifest references are invalid")
    rows = []
    for ref in refs:
        row = projection_store.get(ref)
        if row is None:
            raise ReusableCapabilityError(
                "capability projection manifest references missing content")
        rows.append(row)
    observed = content_digest(tuple(
        (row["record_id"],
         row.get("attributes", {}).get("qualification_digest"))
        for row in sorted(rows, key=lambda item: item["record_id"])))
    if observed != manifest_attributes.get("projection_digest"):
        raise ReusableCapabilityError(
            "capability projection manifest digest does not match its records")
    return tuple(rows), {
        "manifest_ref": manifest_ref,
        "projection_version": str(
            manifest_attributes.get("projection_version") or ""),
        "projection_digest": str(
            manifest_attributes.get("projection_digest") or ""),
    }


def _authoritative_match(
        authority: CapabilityAuthority, row: dict, need: CapabilityNeed,
        assistance_profile: HybridAssistanceProfile | None
        ) -> CapabilityCandidateMatch:
    """Treat projection text as a hint and authority records as truth."""
    attributes = dict(row.get("attributes") or {})
    reasons: list[str] = []
    spec = None
    state = None
    try:
        asset_id = str(attributes.get("asset_id") or "")
        asset_version = str(attributes.get("asset_version") or "")
        state = authority.state(asset_id, asset_version)
        spec = authority.active_spec(asset_id, asset_version)
    except Exception as exc:  # noqa: BLE001 - an ineligible row stays visible
        reasons.append(f"active authority unavailable: {type(exc).__name__}")

    if spec is None or state is None:
        artifact_digest = content_digest(row)
        return CapabilityCandidateMatch(
            str(row.get("record_id") or "unavailable.projection"),
            artifact_digest, False, tuple(reasons), False, False, False,
            (("lexical_overlap", 0.0), ("projection_integrity", 0.0)))

    expected_projection = {
        "authority_record_ref": state["attributes"]["exact_record_id"],
        "asset_id": spec.asset_id,
        "asset_version": spec.version,
        "operation_family": str(
            spec.metadata.get("operation_family") or ""),
        "input_contract_ref": spec.input_contract,
        "input_contract_digest": content_digest(spec.input_contract),
        "output_contract_ref": spec.output_contract,
        "output_contract_digest": content_digest(spec.output_contract),
        "effects": list(spec.effects),
        "capabilities": list(spec.metadata.get("capabilities") or ()),
        "dependencies": list(spec.dependencies),
        "environment": dict(spec.metadata.get("environment") or {}),
        "privacy_scope": str(
            spec.metadata.get("privacy_scope") or "run_private"),
        "tenant_scope": str(spec.metadata.get("tenant_scope") or ""),
        "license": spec.license,
        "artifact_digest": spec.body_ref.digest,
        "qualification_digest": spec.qualification_digest,
        "admission_ref": spec.admission_ref,
    }
    if any(attributes.get(key) != value
           for key, value in expected_projection.items()):
        reasons.append("search projection differs from current authority")

    input_exact = (
        content_digest(spec.input_contract) == need.input_contract_digest)
    output_exact = (
        content_digest(spec.output_contract) == need.output_contract_digest)
    exact_contract = input_exact and output_exact
    stages = set(assistance_profile.stages) if assistance_profile else set()
    adapter_allowed = bool({
        HybridAssistanceStage.INPUT_ADAPTER_SYNTHESIS,
        HybridAssistanceStage.OUTPUT_ADAPTER_SYNTHESIS,
    } & stages)
    if not exact_contract and not adapter_allowed:
        reasons.append("typed input or output contract is incompatible")
    if not set(spec.effects) <= set(need.allowed_effects):
        reasons.append("effect declaration exceeds current authority")
    capabilities = set(spec.metadata.get("capabilities") or ())
    if not set(need.required_capabilities) <= capabilities:
        reasons.append("required capability is absent")
    if set(need.prohibited_capabilities) & capabilities:
        reasons.append("prohibited capability is present")
    if spec.license == "unknown":
        reasons.append("license state is unknown")
    environment = dict(spec.metadata.get("environment") or {})
    if any(environment.get(key) != value
           for key, value in need.environment_constraints):
        reasons.append("environment constraint is incompatible")
    dependencies = set(spec.dependencies)
    if any(value not in dependencies
           for _key, value in need.dependency_constraints):
        reasons.append("dependency constraint is incompatible")
    tenant = str(spec.metadata.get("tenant_scope") or "")
    if tenant and tenant != need.tenant_scope:
        reasons.append("tenant scope is incompatible")
    privacy = str(spec.metadata.get("privacy_scope") or "run_private")
    if privacy not in ("public", need.privacy_scope):
        reasons.append("privacy scope is incompatible")

    operation_match = (
        str(spec.metadata.get("operation_family") or "")
        == need.operation_family)
    query_terms = _tokens(" ".join(
        (need.semantic_summary, *need.search_terms)))
    candidate_terms = _tokens(" ".join((
        spec.description,
        *tuple(spec.metadata.get("search_terms") or ()))))
    lexical = (len(query_terms & candidate_terms)
               / len(query_terms) if query_terms else 0.0)
    return CapabilityCandidateMatch(
        str(row.get("record_id") or "unavailable.projection"),
        spec.body_ref.digest, not reasons, tuple(dict.fromkeys(reasons)),
        exact_contract, operation_match, not exact_contract,
        (("contract_match", 1.0 if exact_contract else 0.0),
         ("lexical_overlap", lexical),
         ("operation_family_match", 1.0 if operation_match else 0.0),
         ("projection_integrity", 0.0 if reasons and
          "search projection differs from current authority" in reasons
          else 1.0)))


@dataclass(frozen=True)
class CapabilityResolutionRequest:
    need: CapabilityNeed
    assistance_profile: HybridAssistanceProfile | None = None
    selected_capability_ref: str = ""


@dataclass(frozen=True)
class CapabilityResolutionResult:
    matches: tuple[CapabilityCandidateMatch, ...]
    plan: CapabilityResolutionPlan
    loop_id: str = ""
    model_calls: int = 0


class CapabilityResolver:
    """Search rebuildable projections, then enforce authority again."""

    def __init__(self, authority: CapabilityAuthority, projection_store) -> None:
        self.authority = authority
        self.projection_store = projection_store

    def resolve_as_loop(
            self, request: CapabilityResolutionRequest, *,
            ledger=None, parent=None) -> CapabilityResolutionResult:
        if not isinstance(request, CapabilityResolutionRequest):
            raise ReusableCapabilityError(
                "capability resolution requires its typed request")

        def resolve() -> CapabilityResolutionResult:
            need = request.need
            rows, projection = _active_projection_rows(
                self.projection_store)
            matches = [
                _authoritative_match(
                    self.authority, row, need, request.assistance_profile)
                for row in rows]

            def lexical(item: CapabilityCandidateMatch) -> float:
                return dict(item.feature_evidence).get(
                    "lexical_overlap", 0.0)

            matches.sort(key=lambda item: (
                not item.eligible, not item.exact_contract_match,
                not item.operation_family_match, -lexical(item),
                item.capability_ref))
            eligible = tuple(item for item in matches if item.eligible)
            selected = None
            if request.selected_capability_ref:
                selected = next((item for item in eligible
                                 if item.capability_ref
                                 == request.selected_capability_ref), None)
                if selected is None:
                    raise ReusableCapabilityError(
                        "semantic selection is not a hard-eligible candidate")
            exact = tuple(item for item in eligible
                          if item.exact_contract_match
                          and item.operation_family_match)
            if selected is not None and selected.exact_contract_match:
                disposition = ResolutionDisposition.EXECUTE_EXACT
            elif selected is not None:
                disposition = ResolutionDisposition.REQUEST_HYBRID_ASSISTANCE
            elif len(exact) == 1:
                selected = exact[0]
                disposition = ResolutionDisposition.EXECUTE_EXACT
            elif eligible and request.assistance_profile is not None:
                disposition = ResolutionDisposition.REQUEST_HYBRID_ASSISTANCE
            elif eligible:
                disposition = ResolutionDisposition.REQUIRE_SELECTION
            else:
                disposition = ResolutionDisposition.ESCALATE_TO_NOVEL_BUILD
            mode = ("deterministic"
                    if disposition is ResolutionDisposition.EXECUTE_EXACT
                    else "hybrid" if disposition is
                    ResolutionDisposition.REQUEST_HYBRID_ASSISTANCE
                    else "non_deterministic")
            plan_id = "resolution." + content_digest({
                "need": need.normalized_digest,
                "disposition": disposition.value,
                "selected": selected.capability_ref if selected else "",
                "projection_digest": projection.get(
                    "projection_digest", ""),
            })[:24]
            plan = CapabilityResolutionPlan(
                plan_id, need.need_id, disposition, mode,
                selected.capability_ref if selected else "",
                selected.artifact_digest if selected else "",
                (request.assistance_profile.profile_id
                 if request.assistance_profile else ""),
                (request.assistance_profile.maximum_model_calls
                 if request.assistance_profile else 0),
                tuple(filter(None, (
                    projection.get("manifest_ref", ""),
                    *tuple(item.capability_ref for item in eligible)))))
            return CapabilityResolutionResult(tuple(matches), plan)

        run = _run_operation(
            f"resolve reusable capability for {request.need.need_id}",
            resolve, LoopRole.INTELLIGENCE,
            "intelligence.code.resolve", "queried_by", ledger=ledger,
            parent=parent)
        return replace(
            run["value"], loop_id=run["loop_id"],
            model_calls=run["model_calls"])


@dataclass(frozen=True)
class CapabilityInvocationRequest:
    run_id: str
    need: CapabilityNeed
    plan: CapabilityResolutionPlan
    inputs: object
    materializer: Callable[[str], object]
    verifier: Callable[[object], bool]
    verifier_id: str
    entrypoint: str = ""
    binder: Callable[[object, str], Callable] | None = None

    def __post_init__(self) -> None:
        if (not callable(self.materializer) or not callable(self.verifier)
                or not isinstance(self.verifier_id, str)
                or not self.verifier_id.strip()):
            raise ReusableCapabilityError(
                "capability invocation requires materializer and verifier authority")


@dataclass(frozen=True)
class CapabilityInvocationResult:
    value: object
    record: CapabilityInvocationRecord
    loop_id: str


@dataclass(frozen=True)
class ReusableCapabilityTaskResolver:
    """Configured adapter for the Practitioner's exact resolver protocol.

    Task parsing remains an injected deterministic contract. This adapter does
    not infer a CapabilityNeed from arbitrary prose and never calls a model.
    """

    resolver_id: str
    resolver: CapabilityResolver
    need_builder: Callable[[str], CapabilityNeed | None]
    input_builder: Callable[[str], object]
    materializer: Callable[[str], object]
    verifier: Callable[[str, object], bool]
    verifier_id: str
    entrypoint: str = ""
    binder: Callable[[object, str], Callable] | None = None

    def __post_init__(self) -> None:
        if (not isinstance(self.resolver_id, str)
                or not self.resolver_id.strip()
                or not isinstance(self.resolver, CapabilityResolver)
                or not isinstance(self.verifier_id, str)
                or not self.verifier_id.strip()
                or any(not callable(value) for value in (
                    self.need_builder, self.input_builder,
                    self.materializer, self.verifier))
                or self.binder is not None and not callable(self.binder)):
            raise ReusableCapabilityError(
                "reusable task resolver configuration is invalid")

    def _resolution(self, task: str) -> CapabilityResolutionResult | None:
        need = self.need_builder(task)
        if need is None:
            return None
        if not isinstance(need, CapabilityNeed):
            raise ReusableCapabilityError(
                "deterministic need builder returned an invalid contract")
        return self.resolver.resolve_as_loop(CapabilityResolutionRequest(need))

    def supports(self, task: str) -> bool:
        result = self._resolution(task)
        return bool(result and result.plan.disposition
                    is ResolutionDisposition.EXECUTE_EXACT)

    def execute(self, task: str) -> dict:
        resolution = self._resolution(task)
        if (resolution is None or resolution.plan.disposition
                is not ResolutionDisposition.EXECUTE_EXACT):
            return {
                "verified": False,
                "failure_class": "NO_EXACT_REUSABLE_CAPABILITY",
                "model_calls": 0,
            }
        need = self.need_builder(task)
        invocation = invoke_capability_as_loop(
            self.resolver.authority, self.resolver.projection_store,
            CapabilityInvocationRequest(
                "adaptive-reuse." + content_digest(task)[:24],
                need, resolution.plan, self.input_builder(task),
                self.materializer,
                lambda value: self.verifier(task, value),
                self.verifier_id, entrypoint=self.entrypoint,
                binder=self.binder))
        return {
            "verified": invocation.record.accepted,
            "value": invocation.value,
            "resolution_plan": resolution.plan.plan_id,
            "invocation": invocation.record.to_dict(),
            "model_calls": invocation.record.model_call_count,
        }


def invoke_capability_as_loop(
        authority: CapabilityAuthority,
        projection_store,
        request: CapabilityInvocationRequest,
        *, ledger=None, parent=None) -> CapabilityInvocationResult:
    """Execute and verify one exact promoted capability with no model call."""
    if request.plan.disposition is not ResolutionDisposition.EXECUTE_EXACT:
        raise ReusableCapabilityError(
            "capability invocation requires an exact execution plan")

    def invoke() -> tuple[object, CapabilityInvocationRecord]:
        active_rows, _projection = _active_projection_rows(projection_store)
        if request.plan.selected_capability_ref not in {
                row["record_id"] for row in active_rows}:
            raise ReusableCapabilityError(
                "selected capability is absent from the active projection")
        projection = projection_store.get(
            request.plan.selected_capability_ref)
        if projection is None:
            raise ReusableCapabilityError(
                "selected search projection is unavailable")
        match = _authoritative_match(
            authority, projection, request.need, None)
        if not match.eligible or not match.exact_contract_match:
            raise ReusableCapabilityError(
                "selected capability no longer satisfies hard eligibility")
        attributes = projection["attributes"]
        spec = authority.active_spec(
            attributes["asset_id"], attributes["asset_version"])
        if spec.body_ref.digest != request.plan.selected_artifact_digest:
            raise ReusableCapabilityError(
                "selected artifact digest changed after resolution")
        if request.verifier_id.casefold() == authority.producer_id(
                spec.asset_id, spec.version).casefold():
            raise ReusableCapabilityError(
                "capability producer cannot be the sole result verifier")
        value = None
        model_calls = 0
        execution_status = "failed"
        verification_status = "not_run"
        failure_class = ""
        try:
            ref = code_asset_capsule(spec).to_ref(
                source="capability_search_projection")
            executed = execute_code_ref(
                CodeRefExecutionRequest(
                    ref, request.materializer, request.entrypoint,
                    request.binder, request.inputs),
                CodeRefExecutionContext(ledger, parent))
            value = executed["value"]
            model_calls = int(
                executed["execution"].get("model_calls", 0))
            execution_status = "completed"
            try:
                verified = bool(request.verifier(value))
                verification_status = "verified" if verified else "rejected"
                failure_class = "" if verified else "POSTCONDITION_FAILED"
            except Exception as exc:  # noqa: BLE001
                verified = False
                verification_status = "failed"
                failure_class = type(exc).__name__
        except Exception as exc:  # noqa: BLE001
            verified = False
            failure_class = type(exc).__name__
        record = CapabilityInvocationRecord(
            "invocation." + content_digest({
                "run_id": request.run_id,
                "need": request.need.need_id,
                "plan": request.plan.plan_id,
                "input": content_digest(request.inputs),
            })[:24],
            request.run_id, request.need.need_id, request.plan.plan_id,
            request.plan.selected_capability_ref, spec.body_ref.digest,
            spec.dependency_digest, request.verifier_id,
            "deterministic", "", model_calls,
            content_digest(request.inputs),
            content_digest(value) if verified else "",
            execution_status, verification_status, verified, failure_class)
        return value, record

    run = _run_operation(
        f"invoke promoted capability for {request.need.need_id}", invoke,
        LoopRole.INTELLIGENCE, "intelligence.code.invoke", "retrieved_by",
        ledger=ledger, parent=parent)
    value, record = run["value"]
    if record.model_call_count != 0 or run["model_calls"] != 0:
        raise ReusableCapabilityError(
            "deterministic reusable capability path made a model call")
    return CapabilityInvocationResult(value, record, run["loop_id"])


__all__ = (
    "CapabilityInvocationRequest", "CapabilityInvocationResult",
    "CapabilityResolutionRequest", "CapabilityResolutionResult",
    "CapabilityResolver", "ProjectionRebuildResult",
    "ReusableCapabilityTaskResolver",
    "invoke_capability_as_loop", "rebuild_capability_projection_as_loop",
)
