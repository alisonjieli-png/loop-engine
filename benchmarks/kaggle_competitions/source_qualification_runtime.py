"""Loop-owned effects and persistence for Kaggle source qualification."""

from __future__ import annotations

import hashlib
import json
import os
import selectors
import subprocess
import time
from collections.abc import Callable
from pathlib import Path

from source_qualification_evidence import (
    artifact_path,
    deadline_assessment,
    download_plan,
    evaluator_candidate,
    matching_evaluator_review,
    matching_legal_review,
    mechanical_facts,
    parse_pages,
    qualification_state,
    source_completeness,
)
from source_qualification_records import (
    PREFLIGHT_REPORT_TYPE,
    QUALIFICATION_CAMPAIGN_TYPE,
    QUALIFICATION_RECORD_TYPE,
    QUALIFICATION_STATES,
    PageCommandResult,
    QualificationRunResult,
    ResolvedQualificationPaths,
    SourceQualificationError,
    SourceQualificationRequest,
    bytes_digest,
    digest,
    page_command,
    resolve_paths,
    safe_slug,
    validate_page_command,
    verified_preflight,
)

PageRunner = Callable[[tuple[str, ...], int, int], PageCommandResult]


def run_pages_cli(
    argv: tuple[str, ...], timeout_seconds: int, maximum_bytes: int
) -> PageCommandResult:
    """Execute only the exact pages command with bounded output memory."""
    validate_page_command(argv, argv[3] if len(argv) > 3 else "")
    try:
        process = subprocess.Popen(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError as exc:
        message = type(exc).__name__.encode("ascii", errors="replace")
        return PageCommandResult(argv, 124, b"", message)
    selector = selectors.DefaultSelector()
    assert process.stdout is not None
    assert process.stderr is not None
    selector.register(process.stdout, selectors.EVENT_READ, "stdout")
    selector.register(process.stderr, selectors.EVENT_READ, "stderr")
    stdout = bytearray()
    stderr = bytearray()
    deadline = time.monotonic() + timeout_seconds
    size_exceeded = False
    timed_out = False
    try:
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                timed_out = True
                process.kill()
                break
            events = selector.select(min(remaining, 0.25))
            if not events and process.poll() is not None:
                continue
            for key, _mask in events:
                try:
                    chunk = os.read(key.fileobj.fileno(), 64 * 1024)
                except OSError:
                    chunk = b""
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                if key.data == "stdout":
                    allowance = maximum_bytes + 1 - len(stdout)
                    if allowance > 0:
                        stdout.extend(chunk[:allowance])
                    if len(stdout) > maximum_bytes or len(chunk) > allowance:
                        size_exceeded = True
                        process.kill()
                        break
                elif len(stderr) < 4096:
                    stderr.extend(chunk[: 4096 - len(stderr)])
            if size_exceeded:
                break
    finally:
        selector.close()
        process.stdout.close()
        process.stderr.close()
        if process.poll() is None:
            process.kill()
        try:
            returncode = process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            returncode = 124
    if timed_out:
        return PageCommandResult(argv, 124, bytes(stdout), b"timeout")
    if size_exceeded:
        return PageCommandResult(
            argv, returncode or 126, bytes(stdout), b"response_size_exceeded"
        )
    return PageCommandResult(argv, int(returncode), bytes(stdout), bytes(stderr))


def _failure_class(result: PageCommandResult) -> str:
    text = bytes(result.stderr[:4096]).lower()
    if result.returncode == 124:
        return "TIMEOUT_OR_CLI_UNAVAILABLE"
    if b"429" in text or b"too many requests" in text:
        return "RATE_LIMITED"
    if any(marker in text for marker in (b"403", b"forbidden", b"permission")):
        return "ACCESS_REFUSED"
    if b"404" in text or b"not found" in text:
        return "NOT_FOUND"
    return "PAGE_READ_FAILED"


def _effect_approval(parent, effect, request: SourceQualificationRequest, reason: str):
    from loop_engine.core.runtime_observer import RuntimeObservationServices
    from loop_engine.loop.effect_approval import (
        ApprovalDecision,
        ApprovalRequest,
        EffectApprovalService,
    )

    service = EffectApprovalService(
        runtime=RuntimeObservationServices(parent=parent, ledger=parent.ledger)
    )
    approval = ApprovalRequest.create(
        parent.loop_id,
        effect,
        reason,
        requested_by="kaggle_source_qualification",
    )
    checkpoint = service.create(approval)
    service.resume(
        checkpoint.pending,
        checkpoint.resume_token,
        ApprovalDecision.approve(
            approval.request_id,
            request.authority.authorized_by,
            reason="Exact typed qualification authority was supplied.",
        ),
    )
    service.consume(approval.request_id, approval.effect)
    return approval


def _effect_loop(
    parent,
    *,
    name: str,
    contract_name: str,
    effect: str | tuple[str, ...],
    profile: str,
    relationship: str,
):
    from loop_engine.loop.loop_contract import contract_for_code_loop
    from loop_engine.loop.loop_role import LoopRelationship, LoopRole, LoopRoleIdentity
    from loop_engine.loop.recursive_loop import LoopConfig

    effects = (effect,) if isinstance(effect, str) else effect
    contract = contract_for_code_loop(
        contract_name,
        input_roles=(f"{contract_name}_request/v1",),
        output_roles=(f"{contract_name}_observation/v1",),
        effects=effects,
        locality="api_calling" if "network" in effects else "local_machine",
        role="intelligence",
    )
    config = LoopConfig(
        framework="custom",
        custom_steps=(
            "materialize" if profile == "intelligence.materialize" else "retrieve",
        ),
        logical_kind="execution",
        replay_guarantee="evidence_equivalent",
        allowable_modes=("deterministic",),
        preferred_modes=("deterministic",),
        delegated_modes=("deterministic",),
        power="light",
        exit_condition="accepted_success",
    )
    relation = (
        LoopRelationship.retrieved_by(parent.loop_id)
        if relationship == "retrieved_by"
        else LoopRelationship.queried_by(parent.loop_id)
    )
    return parent.spawn(
        name,
        config,
        contract=contract,
        identity=LoopRoleIdentity(LoopRole.INTELLIGENCE, profile),
        relationship=relation,
    )


def _read_preflight_as_loop(
    parent,
    request: SourceQualificationRequest,
    paths: ResolvedQualificationPaths,
) -> bytes:
    from loop_engine.loop.effect_approval import EffectClass, EffectSpec
    from loop_engine.loop.recursive_loop import StepOutcome

    effect = EffectSpec(
        EffectClass.LOCAL_READ,
        "read_exact_kaggle_preflight",
        str(paths.preflight_report),
        (("maximum_bytes", str(request.bytes.maximum_preflight_bytes)),),
    )
    approval = _effect_approval(
        parent, effect, request, "Read the exact approved Kaggle preflight report."
    )
    loop = _effect_loop(
        parent,
        name="materialize exact Kaggle preflight evidence",
        contract_name="kaggle_preflight_materialization",
        effect="reads_fs",
        profile="intelligence.materialize",
        relationship="retrieved_by",
    )
    holder: dict[str, object] = {}

    def handler(active, _step: str, _context: dict):
        with open(paths.preflight_report, "rb") as handle:
            content = handle.read(request.bytes.maximum_preflight_bytes + 1)
        if len(content) > request.bytes.maximum_preflight_bytes:
            active.ledger.record(
                loop_id=active.loop_id,
                event="failure.detected",
                failure_class="PREFLIGHT_SIZE_EXCEEDED",
                approval_request_id=approval.request_id,
            )
            return StepOutcome(
                output="preflight:size_exceeded",
                mode="deterministic",
                confidence=0.0,
                failed=True,
            )
        holder["content"] = content
        active.ledger.record(
            loop_id=active.loop_id,
            event="information.materialized",
            kind="kaggle_preflight_report",
            content_digest=bytes_digest(content),
            content_bytes=len(content),
            approval_request_id=approval.request_id,
            content_recorded=False,
        )
        return StepOutcome(
            output="preflight:materialized", mode="deterministic", confidence=1.0
        )

    loop.run(handler=handler, max_steps=1)
    content = holder.get("content")
    if not isinstance(content, bytes):
        raise SourceQualificationError("preflight report could not be materialized")
    return content


def _retrieve_pages_as_loop(
    parent,
    request: SourceQualificationRequest,
    slug: str,
    runner: PageRunner,
) -> tuple[PageCommandResult, str]:
    from loop_engine.loop.effect_approval import EffectClass, EffectSpec
    from loop_engine.loop.recursive_loop import StepOutcome

    argv = page_command(slug)
    validate_page_command(argv, slug)
    command_digest = hashlib.sha256("\0".join(argv).encode("utf-8")).hexdigest()
    network_effect = EffectSpec(
        EffectClass.NETWORK_READ,
        "kaggle_competition_pages_read",
        f"kaggle://competitions/{slug}/pages",
        (
            ("command_sha256", command_digest),
            ("maximum_response_bytes", str(request.bytes.maximum_response_bytes)),
        ),
    )
    network_approval = _effect_approval(
        parent,
        network_effect,
        request,
        f"Read the approved Kaggle competition pages for {slug}.",
    )
    command_effect = EffectSpec(
        EffectClass.COMMAND_EXECUTION,
        "execute_kaggle_pages_cli",
        "executable://kaggle",
        (("command_sha256", command_digest), ("shell", "false")),
    )
    command_approval = _effect_approval(
        parent,
        command_effect,
        request,
        f"Execute the exact read-only Kaggle pages command for {slug}.",
    )
    credential_effect = EffectSpec(
        EffectClass.SECRET_ACCESS,
        "read_kaggle_cli_credentials",
        "secret://kaggle/current-account",
        (("purpose", "competition_pages_read"),),
    )
    credential_approval = _effect_approval(
        parent,
        credential_effect,
        request,
        "Permit the Kaggle CLI to authenticate this exact page read.",
    )
    loop = _effect_loop(
        parent,
        name=f"retrieve Kaggle page set {command_digest[:20]}",
        contract_name="kaggle_competition_pages_read",
        effect=("network", "spawns_process", "reads_secret"),
        profile="intelligence.search",
        relationship="queried_by",
    )
    holder: dict[str, object] = {}

    def handler(active, _step: str, _context: dict):
        approval_fields = {
            "approval_request_id": network_approval.request_id,
            "command_approval_request_id": command_approval.request_id,
            "credential_approval_request_id": credential_approval.request_id,
        }
        active.ledger.record(
            loop_id=active.loop_id,
            event="tool_invocation_started",
            tool="kaggle_cli",
            operation="competition_pages_read",
            command_sha256=command_digest,
            declared_effects=("network_read", "command_execution", "secret_access"),
            **approval_fields,
        )
        try:
            result = runner(
                argv, request.timeout_seconds, request.bytes.maximum_response_bytes
            )
        except (
            OSError,
            subprocess.SubprocessError,
            TimeoutError,
            TypeError,
            ValueError,
        ) as exc:
            result = PageCommandResult(
                argv, 125, b"", type(exc).__name__.encode("ascii", errors="replace")
            )
        if not isinstance(result, PageCommandResult) or result.argv != argv:
            result = PageCommandResult(argv, 125, b"", b"runner_contract_failure")
        holder["result"] = result
        response_bytes = len(result.stdout)
        response_digest = bytes_digest(result.stdout) if result.stdout else ""
        status = "READ" if result.returncode == 0 else _failure_class(result)
        if response_bytes > request.bytes.maximum_response_bytes:
            status = "CONTENT_SIZE_EXCEEDED"
        ok = status == "READ"
        active.ledger.record(
            loop_id=active.loop_id,
            event=("tool_invocation_completed" if ok else "tool_invocation_failed"),
            tool="kaggle_cli",
            operation="competition_pages_read",
            command_sha256=command_digest,
            declared_effects=("network_read", "command_execution", "secret_access"),
            response_status=status,
            response_bytes=response_bytes,
            response_sha256=response_digest,
            response_content_recorded=False,
            **approval_fields,
        )
        if ok:
            active.ledger.record(
                loop_id=active.loop_id,
                event="intelligence.context.retrieved",
                kind="kaggle_competition_pages",
                name=command_digest[:20],
                pulled=True,
                response_sha256=response_digest,
                response_bytes=response_bytes,
                response_content_recorded=False,
            )
        else:
            active.ledger.record(
                loop_id=active.loop_id,
                event="failure.detected",
                failure_class=status,
                command_sha256=command_digest,
            )
        return StepOutcome(
            output=f"competition_pages:{status}",
            mode="deterministic",
            confidence=1.0 if ok else 0.0,
            failed=not ok,
        )

    loop.run(handler=handler, max_steps=1)
    result = holder.get("result")
    if not isinstance(result, PageCommandResult):
        raise SourceQualificationError("page Intelligence Loop produced no result")
    status = "READ" if result.returncode == 0 else _failure_class(result)
    if len(result.stdout) > request.bytes.maximum_response_bytes:
        status = "CONTENT_SIZE_EXCEEDED"
    return result, status


def _write_private_bytes(path: Path, body: bytes, private_root: Path) -> None:
    private_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    if private_root.is_symlink():
        raise SourceQualificationError("private storage root cannot be a symlink")
    os.chmod(private_root, 0o700)
    if path != private_root and private_root not in path.parents:
        raise SourceQualificationError("private write escaped its exact root")
    relative_parent = path.parent.relative_to(private_root)
    current = private_root
    for part in relative_parent.parts:
        current = current / part
        if current.exists() and current.is_symlink():
            raise SourceQualificationError("private path cannot use a symlink")
        current.mkdir(exist_ok=True, mode=0o700)
        os.chmod(current, 0o700)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(body)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        try:
            os.unlink(path)
        except OSError:
            pass
        raise


def _store_page_as_loop(
    parent,
    request: SourceQualificationRequest,
    paths: ResolvedQualificationPaths,
    page_kind: str,
    name_digest: str,
    body: bytes,
) -> dict:
    from loop_engine.loop.effect_approval import EffectClass, EffectSpec
    from loop_engine.loop.recursive_loop import StepOutcome

    body_digest = bytes_digest(body)
    destination = artifact_path(paths.artifact_root, body_digest)
    if paths.artifact_root not in destination.parents:
        raise SourceQualificationError("content-addressed artifact escaped its root")
    if len(str(destination)) > request.paths.maximum_path_characters:
        raise SourceQualificationError(
            "content-addressed artifact exceeds the path budget"
        )
    effect = EffectSpec(
        EffectClass.LOCAL_WRITE,
        "store_private_competition_page",
        str(destination),
        (
            ("body_sha256", body_digest),
            ("body_bytes", str(len(body))),
            ("privacy_class", request.privacy.classification),
        ),
    )
    approval = _effect_approval(
        parent, effect, request, "Store one exact competition page privately."
    )
    loop = _effect_loop(
        parent,
        name=f"materialize private page {body_digest[:20]}",
        contract_name="private_kaggle_page_materialization",
        effect="writes_fs",
        profile="intelligence.materialize",
        relationship="retrieved_by",
    )

    def handler(active, _step: str, _context: dict):
        try:
            _write_private_bytes(destination, body, paths.artifact_root)
        except OSError:
            active.ledger.record(
                loop_id=active.loop_id,
                event="failure.detected",
                failure_class="PRIVATE_ARTIFACT_WRITE_FAILED",
                content_digest=body_digest,
                approval_request_id=approval.request_id,
            )
            return StepOutcome(
                output="page_artifact:write_failed",
                mode="deterministic",
                confidence=0.0,
                failed=True,
            )
        active.ledger.record(
            loop_id=active.loop_id,
            event="information.materialized",
            kind="private_kaggle_page",
            page_kind=page_kind,
            source_name_sha256=name_digest,
            content_digest=body_digest,
            content_bytes=len(body),
            privacy_class=request.privacy.classification,
            approval_request_id=approval.request_id,
            content_recorded=False,
        )
        return StepOutcome(
            output="page_artifact:stored", mode="deterministic", confidence=1.0
        )

    loop.run(handler=handler, max_steps=1)
    if not destination.is_file():
        raise SourceQualificationError("private page artifact was not written")
    relative = destination.relative_to(paths.artifact_root).as_posix()
    return {
        "record_type": "private_source_artifact/v1",
        "page_kind": page_kind,
        "source_name_sha256": name_digest,
        "content_sha256": body_digest,
        "content_bytes": len(body),
        "content_type": "text/plain; charset=utf-8",
        "artifact_ref": f"sha256:{body_digest}",
        "private_relative_path": relative,
        "privacy_classification": request.privacy.classification,
        "publication_allowed": False,
    }


def _qualify_one(
    parent,
    request: SourceQualificationRequest,
    paths: ResolvedQualificationPaths,
    selected_row: dict,
    probe: dict,
    runner: PageRunner,
    artifact_cache: dict[str, dict],
    private_byte_state: dict[str, int],
) -> dict:
    slug = safe_slug(selected_row.get("slug"))
    result, transport_status = _retrieve_pages_as_loop(parent, request, slug, runner)
    parsed_pages: list[tuple[str, str, bytes]] = []
    parse_status = transport_status
    if transport_status == "READ":
        parsed_pages, parse_status = parse_pages(result, request)
    artifact_records: list[dict] = []
    page_bodies: dict[str, list[bytes]] = {}
    stored_by_digest: dict[str, dict] = {}
    if parse_status == "PARSED":
        new_bodies = {
            bytes_digest(body): body
            for _page_kind, _name_digest, body in parsed_pages
            if bytes_digest(body) not in artifact_cache
        }
        new_bytes = sum(len(body) for body in new_bodies.values())
        if (
            private_byte_state["stored"] + new_bytes
            > request.bytes.maximum_total_private_bytes
        ):
            parsed_pages = []
            parse_status = "PRIVATE_BYTE_BUDGET_EXCEEDED"
    if parse_status == "PARSED":
        for page_kind, name_digest, body in parsed_pages:
            body_digest = bytes_digest(body)
            artifact = artifact_cache.get(body_digest)
            if artifact is None:
                artifact = _store_page_as_loop(
                    parent, request, paths, page_kind, name_digest, body
                )
                artifact_cache[body_digest] = artifact
                private_byte_state["stored"] += len(body)
            else:
                artifact = {
                    **artifact,
                    "page_kind": page_kind,
                    "source_name_sha256": name_digest,
                }
            stored_by_digest[body_digest] = artifact
            artifact_records.append(artifact)
            page_bodies.setdefault(page_kind, []).append(body)
    facts = mechanical_facts(page_bodies)
    completeness = source_completeness(probe, artifact_records)
    deadline = deadline_assessment(selected_row.get("deadline"), request.as_of)
    source_bundle_material = {
        "competition_slug": slug,
        "preflight_report_digest": request.expected_preflight_report_digest,
        "population_digest": request.expected_population_digest,
        "preflight_probe_digest": digest(probe),
        "page_transport_status": transport_status,
        "page_parse_status": parse_status,
        "page_artifacts": artifact_records,
    }
    source_bundle_digest = digest(source_bundle_material)
    evaluator = evaluator_candidate(slug, source_bundle_digest, facts)
    legal_review, legal_state = matching_legal_review(
        request, slug, source_bundle_digest
    )
    evaluator_review, evaluator_state = matching_evaluator_review(
        request, slug, evaluator["candidate_digest"]
    )
    status, reasons = qualification_state(
        retrieval_status=parse_status,
        completeness=completeness,
        deadline=deadline,
        evaluator=evaluator,
        legal_review=legal_review,
        legal_state=legal_state,
        evaluator_review=evaluator_review,
        evaluator_state=evaluator_state,
        require_external_model_permission=request.require_external_model_permission,
    )
    record = {
        "record_type": QUALIFICATION_RECORD_TYPE,
        "competition_slug": slug,
        "state": status,
        "reasons": reasons,
        "source_identity": {
            "preflight_report_digest": request.expected_preflight_report_digest,
            "population_digest": request.expected_population_digest,
            "preflight_probe_digest": digest(probe),
            "source_bundle_digest": source_bundle_digest,
        },
        "page_retrieval": {
            "transport_status": transport_status,
            "parse_status": parse_status,
            "physical_page_reads": 1,
            "raw_response_retained": False,
            "private_page_artifact_count": len(stored_by_digest),
            "page_occurrence_count": len(artifact_records),
            "private_page_bytes": sum(
                item["content_bytes"] for item in stored_by_digest.values()
            ),
            "page_artifacts": artifact_records,
        },
        "rules": {
            "page_present": any(
                item["page_kind"] == "rules" for item in artifact_records
            ),
            "page_artifact_refs": [
                item["artifact_ref"]
                for item in artifact_records
                if item["page_kind"] == "rules"
            ],
            "mechanical_extraction_only": True,
        },
        "license_and_data_use": {
            "mechanical_candidates": facts["license_or_data_use_candidates"],
            "authoritative_decision": (
                legal_review.data_use_decision if legal_review else "UNRESOLVED"
            ),
            "mechanical_extraction_grants_authority": False,
        },
        "deadline": deadline,
        "external_model_permission": {
            "mechanical_candidate": facts["external_model_permission_candidate"],
            "authoritative_decision": (
                legal_review.external_model_decision if legal_review else "UNRESOLVED"
            ),
            "required_for_this_campaign": request.require_external_model_permission,
            "mechanical_extraction_grants_authority": False,
        },
        "evaluation": {
            "metric_candidate": facts["metric_candidate"],
            "metric_candidates": facts["metric_candidates"],
            "direction_candidate": facts["direction_candidate"],
            "candidate": evaluator,
            "review_record_type": "independent_evaluator_review/v1",
            "review_state": evaluator_state,
            "review_ref": evaluator_review.review_id if evaluator_review else "",
            "reviewer_id": evaluator_review.reviewer_id if evaluator_review else "",
            "implementation_producer_id": (
                evaluator_review.implementation_producer_id if evaluator_review else ""
            ),
            "implementation_ref": (
                evaluator_review.implementation_ref if evaluator_review else ""
            ),
            "implementation_digest": (
                evaluator_review.implementation_digest if evaluator_review else ""
            ),
            "verification_evidence_refs": (
                list(evaluator_review.verification_evidence_refs)
                if evaluator_review
                else []
            ),
        },
        "source_completeness": completeness,
        "human_or_legal_review": {
            "record_type": "human_legal_review/v1",
            "state": legal_state,
            "decision_ref": legal_review.decision_id if legal_review else "",
            "reviewer_id": legal_review.reviewer_id if legal_review else "",
            "reviewed_source_bundle_digest": (
                legal_review.source_bundle_digest if legal_review else ""
            ),
            "expires_at": legal_review.expires_at if legal_review else "",
            "review_required": True,
        },
        "untrusted_content": {
            "instruction_markers_detected": facts[
                "untrusted_instruction_markers_detected"
            ],
            "treated_as_authority": False,
            "content_in_run_history": False,
        },
        "download_plan": download_plan(
            slug, source_bundle_digest, completeness, status
        ),
        "model_calls": 0,
        "downloads": 0,
        "submissions": 0,
    }
    record["record_digest"] = digest(record)
    return record


def _write_record_as_loop(
    parent,
    request: SourceQualificationRequest,
    paths: ResolvedQualificationPaths,
    record: dict,
) -> None:
    from loop_engine.loop.effect_approval import EffectClass, EffectSpec
    from loop_engine.loop.recursive_loop import StepOutcome

    body = (json.dumps(record, indent=2, sort_keys=True) + "\n").encode("utf-8")
    body_digest = bytes_digest(body)
    effect = EffectSpec(
        EffectClass.LOCAL_WRITE,
        "write_kaggle_source_qualification_record",
        str(paths.output_record),
        (("content_sha256", body_digest), ("content_bytes", str(len(body)))),
    )
    approval = _effect_approval(
        parent, effect, request, "Write the exact private qualification record."
    )
    loop = _effect_loop(
        parent,
        name=f"materialize qualification record {body_digest[:20]}",
        contract_name="kaggle_qualification_record_materialization",
        effect="writes_fs",
        profile="intelligence.materialize",
        relationship="retrieved_by",
    )

    def handler(active, _step: str, _context: dict):
        try:
            _write_private_bytes(paths.output_record, body, paths.output_record.parent)
        except OSError:
            active.ledger.record(
                loop_id=active.loop_id,
                event="failure.detected",
                failure_class="QUALIFICATION_RECORD_WRITE_FAILED",
                approval_request_id=approval.request_id,
            )
            return StepOutcome(
                output="qualification_record:write_failed",
                mode="deterministic",
                confidence=0.0,
                failed=True,
            )
        active.ledger.record(
            loop_id=active.loop_id,
            event="information.materialized",
            kind="kaggle_source_qualification_record",
            content_digest=record["record_digest"],
            serialized_sha256=body_digest,
            content_bytes=len(body),
            approval_request_id=approval.request_id,
            content_recorded=False,
        )
        return StepOutcome(
            output="qualification_record:stored",
            mode="deterministic",
            confidence=1.0,
        )

    loop.run(handler=handler, max_steps=1)
    if not paths.output_record.is_file():
        raise SourceQualificationError("qualification record was not written")


def run_source_qualification_as_loop(
    request: SourceQualificationRequest,
    runner: PageRunner = run_pages_cli,
) -> QualificationRunResult:
    """Run the exact read-only qualification path through canonical Loops."""
    paths = resolve_paths(request)
    from loop_engine.core.run_history import RunHistory
    from loop_engine.loop.effect_approval import EffectClass, EffectSpec
    from loop_engine.loop.loop_role import LoopRelationship, LoopRole, LoopRoleIdentity
    from loop_engine.loop.recursive_loop import (
        Loop,
        LoopConfig,
        LoopLedger,
        StepOutcome,
    )

    ledger = LoopLedger()
    owner = Loop(
        f"Kaggle source qualification {request.run_id}",
        LoopConfig(
            framework="five_step",
            power="small",
            allowable_modes=("deterministic",),
            preferred_modes=("deterministic",),
        ),
        ledger=ledger,
        identity=LoopRoleIdentity(LoopRole.PRACTITIONER, "practitioner.research"),
        relationship=LoopRelationship.starting(),
    )
    holder: dict[str, object] = {}

    def handler(active, step: str, _context: dict):
        if step == "act":
            content = _read_preflight_as_loop(active, request, paths)
            _report, selected, probes = verified_preflight(content, request)
            artifact_cache: dict[str, dict] = {}
            private_byte_state = {"stored": 0}
            records = [
                _qualify_one(
                    active,
                    request,
                    paths,
                    selected[slug],
                    probes[slug],
                    runner,
                    artifact_cache,
                    private_byte_state,
                )
                for slug in request.competition_slugs
            ]
            campaign = {
                "record_type": QUALIFICATION_CAMPAIGN_TYPE,
                "run_id": request.run_id,
                "created_as_of": request.as_of,
                "source_preflight": {
                    "record_type": PREFLIGHT_REPORT_TYPE,
                    "report_digest": request.expected_preflight_report_digest,
                    "population_digest": request.expected_population_digest,
                    "selected_competitions": list(request.competition_slugs),
                },
                "privacy": {
                    "classification": request.privacy.classification,
                    "page_content_publication_allowed": False,
                    "publication_review_required": True,
                    "raw_cli_responses_retained": False,
                },
                "qualifications": records,
                "summary": {
                    "selected_denominator": len(records),
                    "state_counts": {
                        state: sum(item["state"] == state for item in records)
                        for state in sorted(QUALIFICATION_STATES)
                    },
                    "physical_page_reads": len(records),
                    "private_page_artifacts": len(artifact_cache),
                    "private_page_bytes": private_byte_state["stored"],
                    "model_calls": 0,
                    "downloads": 0,
                    "submissions": 0,
                },
                "authority_boundary": {
                    "network_reads": "exact selected competition page sets",
                    "command_execution": "exact digest-bound Kaggle pages commands",
                    "secret_access": "Kaggle credentials for exact approved reads",
                    "local_reads": "exact preflight report",
                    "local_writes": "private page artifacts, record, and Run History",
                    "download_authority_present": False,
                    "submission_authority_present": False,
                    "mechanical_extraction_can_grant_legal_authority": False,
                },
                "limitations": [
                    "Mechanical page extraction proposes facts and grants no "
                    "legal authority.",
                    "An evaluator candidate is not admitted until independent review.",
                    "The download plan is passive and no competition data was "
                    "downloaded.",
                    "A locally admitted evaluator would not itself be a Kaggle "
                    "leaderboard score.",
                ],
            }
            campaign["record_digest"] = digest(campaign)
            holder["record"] = campaign
            return StepOutcome(
                output="source qualification candidates created",
                mode="deterministic",
                confidence=1.0,
            )
        if step == "check":
            record = holder.get("record")
            complete = isinstance(record, dict) and len(
                record.get("qualifications", ())
            ) == len(request.competition_slugs)
            return StepOutcome(
                output=(
                    "qualification accounting:complete"
                    if complete
                    else "qualification accounting:failed"
                ),
                mode="deterministic",
                confidence=1.0 if complete else 0.0,
                failed=not complete,
            )
        return StepOutcome(
            output=f"{step}:recorded", mode="deterministic", confidence=1.0
        )

    result = owner.run(handler=handler, max_steps=len(owner.steps()) + 1)
    record = holder.get("record")
    if not isinstance(record, dict):
        raise SourceQualificationError("qualification owner produced no record")
    _write_record_as_loop(owner, request, paths, record)
    ledger.record(
        loop_id=result.loop_id,
        event="information.binding.published",
        binding_kind="kaggle_source_qualification",
        record_type=QUALIFICATION_CAMPAIGN_TYPE,
        content_digest=record["record_digest"],
        content_recorded=False,
    )
    history_effect = EffectSpec(
        EffectClass.LOCAL_WRITE,
        "save_kaggle_qualification_run_history",
        str(paths.run_history_root / request.run_id),
        (("record_digest", record["record_digest"]),),
    )
    _effect_approval(
        owner,
        history_effect,
        request,
        "Save the qualification Run History at its exact destination.",
    )
    paths.run_history_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    if paths.run_history_root.is_symlink():
        raise SourceQualificationError("Run History root cannot be a symlink")
    os.chmod(paths.run_history_root, 0o700)
    history = RunHistory.from_ledger(ledger.events, run_id=request.run_id)
    head = history.commit()
    history_path = history.save(str(paths.run_history_root))
    os.chmod(paths.run_history_root, 0o700)
    os.chmod(history_path, 0o700)
    for saved in Path(history_path).iterdir():
        if saved.is_file() and not saved.is_symlink():
            os.chmod(saved, 0o600)
    return QualificationRunResult(
        record=record,
        run_history_path=history_path,
        run_history_head_digest=head,
        run_history_chain=history.verify_chain(),
        run_history_events=len(history.event_log),
    )


__all__ = ["PageRunner", "run_pages_cli", "run_source_qualification_as_loop"]
