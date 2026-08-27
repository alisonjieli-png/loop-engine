"""Focused command implementations for the public Loop Engine CLI.

Argument parsing remains in ``__main__``. These functions own typed doctor,
model-routing, solve, and learning workflows so the CLI stays a thin adapter.
"""
from __future__ import annotations

import json


def task_intake_from_args(args):
    from .templates.intake import TaskIntakeRequest, intake_task

    if args.dataset:
        request = TaskIntakeRequest(dataset=args.dataset, goal=args.text)
    elif args.repository:
        request = TaskIntakeRequest(repository=args.repository, goal=args.text)
    elif args.url:
        request = TaskIntakeRequest(url=args.url, goal=args.text)
    elif args.task_pack:
        request = TaskIntakeRequest(task_pack=args.task_pack)
    elif args.file:
        request = TaskIntakeRequest(file=args.file)
    else:
        request = TaskIntakeRequest(text=args.text)
    return intake_task(request)


def completed_learning_producer(goal: str):
    from .loop.loop_role import LoopRelationship, LoopRole, LoopRoleIdentity
    from .loop.recursive_loop import Loop, LoopConfig, StepOutcome

    loop = Loop(
        goal,
        LoopConfig(
            framework="custom", custom_steps=("act",), power="light",
            allowable_modes=("deterministic",),
            preferred_modes=("deterministic",),
            exit_condition="accepted_success"),
        identity=LoopRoleIdentity(
            LoopRole.PRACTITIONER, "practitioner.self_improvement"),
        relationship=LoopRelationship.starting())
    loop.run(handler=lambda active, step, context: StepOutcome(
        output="candidate:prepared", mode="deterministic", confidence=0.95),
        max_steps=2)
    return loop


def run_doctor(args) -> int:
    import platform
    from importlib.metadata import PackageNotFoundError, version

    from .architecture_contract import run_architecture_contract_checks
    from .core.settings_loader import load_runtime_settings

    try:
        distribution_version = version("loop-engine")
    except PackageNotFoundError:
        distribution_version = "source-tree"
    architecture = run_architecture_contract_checks()
    loaded = load_runtime_settings(args.settings_file or None)
    gateway = loaded.settings.build_gateway()
    report = {
        "record_type": "loop_engine_doctor/v1", "ok": architecture["passed"],
        "distribution_version": distribution_version,
        "python": platform.python_version(),
        "canonical_runtime": "loop_engine.loop.recursive_loop.Loop",
        "architecture_contract": architecture,
        "settings": loaded.safe_summary(),
        "providers_configured": [provider.describe()
                                 for provider in gateway.providers.values()],
        "provider_calls_made": 0,
        "deterministic_no_key_lane": "available",
    }
    print(json.dumps(report, indent=1))
    return 0 if report["ok"] else 1


def run_models_action(args) -> int:
    from hashlib import sha256

    from .core.model_routing_intelligence import (
        MODEL_ROUTING_PORTFOLIO_ID, ModelRouteBootstrapSelector,
        ModelRoutingEvidence, ModelSelectionRequest, ModelSelectorConfig,
        select_model_as_loop)
    from .core.settings_loader import load_runtime_settings
    from .templates.compiler import TaskCompileRequest, compile_task_value

    loaded = load_runtime_settings(args.settings_file or None)
    settings = loaded.settings
    gateway = settings.build_gateway()
    routes = gateway.registry.all()
    if args.models_action in ("inventory", "routes"):
        print(json.dumps({
            "record_type": "model_inventory/v1",
            "providers": [provider.describe()
                          for provider in gateway.providers.values()],
            "routes": [{
                "route_id": route.name, "provider_id": route.provider,
                "exact_model_id": route.model, "locality": route.locality,
                "purposes": list(route.purposes),
            } for route in routes],
            "provider_calls_made": 0,
        }, indent=1))
        return 0
    if args.models_action == "benchmark":
        from .core.model_routing_intelligence_checks import run_frozen_benchmark
        result = run_frozen_benchmark()
        print(json.dumps(result, indent=1))
        return 0 if result["all_passed"] else 1
    if not args.text:
        print(json.dumps({"record_type": "model_explain_failure/v1",
                          "error": "models explain requires --text"}, indent=1))
        return 2
    compiled = compile_task_value(TaskCompileRequest(args.text))
    coordinates = compiled["work_item"]["coordinates"]
    operator = args.operator or coordinates["operator"]
    topology = args.response_topology or coordinates["response_topology"]
    selector = ModelRouteBootstrapSelector.from_gateway(
        gateway, ModelRoutingEvidence(), ModelSelectorConfig(settings))
    request = ModelSelectionRequest(
        request_id="explain:" + sha256(args.text.encode()).hexdigest()[:16],
        run_id="explain:not-executed", loop_id="explain:selection",
        role="practitioner", profile="practitioner.solver",
        run_mode=("deterministic" if args.deterministic_sufficient else "hybrid"),
        compiled_task_ref=compiled["compiled_task_id"],
        task_fingerprint=sha256(json.dumps(
            compiled["work_item"], sort_keys=True).encode()).hexdigest(),
        operator=operator, response_topology=topology,
        output_contract="compiled-task output contract",
        model_purpose=args.model_purpose,
        structured_output_required=topology not in ("text", "artifact"),
        input_context_estimate=max(1, len(args.text) // 4),
        expected_output_estimate=1024,
        verification_plan="typed output plus independent verification",
        allowed_localities=(("local",) if args.local_only
                            else ("local", "organization", "cloud")),
        deterministic_sufficient=args.deterministic_sufficient,
        deterministic_evidence_refs=(
            ("user-declared:verified-deterministic-procedure",)
            if args.deterministic_sufficient else ()),
        require_suitability_evidence=True)
    selected = select_model_as_loop(selector, request)
    print(json.dumps({
        "record_type": "model_selection_explanation/v1",
        "compiled_task": compiled, "portfolio_id": MODEL_ROUTING_PORTFOLIO_ID,
        "selection_loop_id": selected["loop_id"],
        "decision": selected["decision_record"], "provider_calls_made": 0,
        "note": ("unprobed routes remain rejected; run models probe with "
                 "explicit provider-call authority before live use"),
    }, indent=1))
    return 0 if selected["decision"].status != "abstained" else 1


def run_task_compile(args) -> int:
    from .templates.compiler import TaskCompileRequest, compile_task
    from .templates.intake import TaskIntakeError
    try:
        intake = task_intake_from_args(args)
        result = compile_task(TaskCompileRequest(
            text=intake.original_input, source_kind=intake.kind,
            source_refs=intake.source_refs))
        print(json.dumps({"intake": intake.to_dict(), **result}, indent=1))
        return 0
    except (TaskIntakeError, ValueError) as exc:
        print(json.dumps({"record_type": "task_compile_failure/v1",
                          "error": str(exc)}, indent=1))
        return 2


def run_solve(args) -> int:
    from .code_nodes.solve_runtime import SolveRequest, solve_task
    from .code_nodes.solution_model_port import ModelExecution
    from .core.runtime_settings import ModelPolicyRequest, ModelTask
    from .core.settings_loader import load_runtime_settings
    try:
        intake = task_intake_from_args(args)
        loaded = load_runtime_settings(args.settings_file or None)
        settings = loaded.settings
        model_execution = None
        if args.authorize_model_calls:
            if args.max_model_calls < 1 or not args.max_total_tokens:
                raise ValueError(
                    "authorized solve requires --max-model-calls >= 1 and "
                    "--max-total-tokens")
            policy = ModelPolicyRequest(
                thinking_power=(args.thinking_power
                                or settings.models.default_thinking_power),
                max_total_tokens=args.max_total_tokens,
                max_route_attempts=args.max_model_calls)
            request = settings.model_request(ModelTask(
                prompt="solve authorization preflight", policy=policy))
            model_execution = ModelExecution(
                settings.build_gateway(), request.config,
                max_model_calls=args.max_model_calls,
                llm_thinking_power=policy.thinking_power)
        outcome = solve_task(SolveRequest(
            intake=intake, model_execution=model_execution,
            runs_dir=(args.runs_dir or settings.history.resolved_runs_dir()),
            save_run_history=settings.history.save_run_history))
        print(json.dumps(outcome.to_dict(), indent=1))
        return 0 if outcome.solved else 1
    except (OSError, ValueError) as exc:
        print(json.dumps({
            "record_type": "solve_failure/v2", "solved": False,
            "failure_code": ("PERMISSION_DENIED" if isinstance(
                exc, PermissionError) else "OUTPUT_CONTRACT_VIOLATION"),
            "error": str(exc)}, indent=1))
        return 2


def run_learn(args) -> int:
    import hashlib
    import os

    from .core.run_history import default_runs_dir, verify_saved_run
    from .memory.model.memory_type import (MemoryIdentity, MemoryLifecycle,
                                           MemoryScope, MemoryType)
    from .memory.semantic.record import SemanticMemoryRecord
    from .memory.storage.repository import CandidateJournal, LearningPolicy

    if not args.lesson.strip():
        print(json.dumps({"record_type": "learning_candidate_failure/v1",
                          "error": "learn requires --lesson; Loop Engine does "
                                   "not invent a reusable claim"}, indent=1))
        return 2
    runs_dir = default_runs_dir(args.runs_dir or "")
    saved = sorted(
        (name for name in os.listdir(runs_dir)
         if os.path.isdir(os.path.join(runs_dir, name))),
        key=lambda name: os.path.getmtime(os.path.join(runs_dir, name))) \
        if os.path.isdir(runs_dir) else []
    if not saved:
        print(json.dumps({"record_type": "learning_candidate_failure/v1",
                          "error": "no saved Run History exists"}, indent=1))
        return 1
    source_run = verify_saved_run(runs_dir, saved[-1])
    lesson_digest = hashlib.sha256(args.lesson.encode()).hexdigest()
    journal = CandidateJournal()
    producer = completed_learning_producer(
        f"derive candidate from verified run {source_run['run_id']}")
    transition = journal.stage(SemanticMemoryRecord(
        identity=MemoryIdentity(
            f"candidate.learn.{lesson_digest[:16]}", "1.0.0",
            lesson_digest, MemoryType.SEMANTIC),
        subject=f"run:{source_run['run_id']}", predicate="suggests",
        object_value=args.lesson, claim_type="derived", scope=MemoryScope.PROJECT,
        lifecycle=MemoryLifecycle.CANDIDATE), producer_loop=producer,
        policy=LearningPolicy(), evidence_refs=(
            f"run_history:{source_run['run_id']}:{source_run['head_digest']}",
            *tuple(args.evidence)))
    print(json.dumps({"record_type": "learning_candidates/v1",
                      "staged": [transition.to_dict()],
                      "storage": str(journal.journal),
                      "note": "candidate staged; independent review required"},
                     indent=1))
    return 0


def run_candidate_action(args) -> int:
    from .memory.model.memory_type import MemoryType
    from .memory.storage.repository import (
        CandidateJournal, LearningDecision, LearningPolicy,
        LearningRecordRef, LearningTransitionResult)
    if not all((args.candidate_id, args.candidate_version,
                args.candidate_digest, args.decision_reason, args.evidence)):
        print(json.dumps({
            "record_type": "learning_governance_failure/v1",
            "error": ("candidate governance requires exact identity, reason, "
                      "and at least one evidence reference")}, indent=1))
        return 2
    journal = CandidateJournal()
    policy = LearningPolicy()
    ref = LearningRecordRef(args.candidate_id, args.candidate_version,
                            args.candidate_digest, MemoryType.SEMANTIC)
    evidence = tuple(args.evidence)
    try:
        if args.candidate_action == "review":
            transition = journal.review(
                ref, policy=policy,
                evaluator=lambda record: LearningDecision(
                    args.decision == "accept", args.decision_reason, evidence))
        elif args.candidate_action == "promote":
            reviewed = LearningTransitionResult(
                journal.get_exact(ref),
                journal.governance_history(ref.record_id)[-1])
            transition = journal.promote(
                reviewed, policy=policy,
                authorizer=lambda record, review: LearningDecision(
                    args.decision == "accept", args.decision_reason, evidence))
        else:
            transition = journal.rollback(
                ref, policy=policy,
                authorizer=lambda record: LearningDecision(
                    args.decision == "accept", args.decision_reason, evidence))
        print(json.dumps({
            "record_type": "learning_governance_transition/v1",
            "action": args.candidate_action,
            "transition": transition.to_dict(),
            "journal_validation": journal.validate_journal()}, indent=1))
        return 0
    except (OSError, TypeError, ValueError, PermissionError) as exc:
        print(json.dumps({"record_type": "learning_governance_failure/v1",
                          "action": args.candidate_action,
                          "error": str(exc)}, indent=1))
        return 1


def run_five_step_demo(args) -> int:
    """Run a real no-key compile, solve, verify, history, and candidate stage."""
    import hashlib
    import tempfile
    from pathlib import Path

    from .code_nodes.solve_runtime import SolveRequest, solve_task
    from .core.settings_loader import load_runtime_settings
    from .memory.model.memory_type import (MemoryIdentity, MemoryLifecycle,
                                           MemoryScope, MemoryType)
    from .memory.semantic.record import SemanticMemoryRecord
    from .memory.storage.repository import CandidateJournal, LearningPolicy
    from .templates.intake import TaskIntakeRequest, intake_task

    settings = load_runtime_settings(args.settings_file or None).settings
    goal = args.text or "Validate and normalize a structured customer record."
    with tempfile.TemporaryDirectory(prefix="loop-engine-five-step-") as root:
        source = Path(root) / "customer.json"
        source.write_text(json.dumps({
            " customer_id ": " C-100 ", " status ": " active ",
        }), encoding="utf-8")
        outcome = solve_task(SolveRequest(
            intake=intake_task(TaskIntakeRequest(
                dataset=str(source), goal=goal)),
            runs_dir=(args.runs_dir or settings.history.resolved_runs_dir()),
            save_run_history=True))
    if not outcome.solved:
        print(json.dumps({"record_type": "five_step_demo/v2",
                          "solved": False,
                          "failure": outcome.to_dict()}, indent=1))
        return 1
    lesson = "Normalize surrounding whitespace without changing typed values."
    digest = hashlib.sha256(lesson.encode()).hexdigest()
    transition = CandidateJournal().stage(SemanticMemoryRecord(
        identity=MemoryIdentity(
            f"candidate.demo.{outcome.run_id[-16:]}", "1.0.0", digest,
            MemoryType.SEMANTIC),
        subject="structured_normalization", predicate="suggests",
        object_value=lesson, claim_type="derived", scope=MemoryScope.PROJECT,
        lifecycle=MemoryLifecycle.CANDIDATE),
        producer_loop=completed_learning_producer(
            f"stage candidate from {outcome.run_id}"),
        policy=LearningPolicy(), evidence_refs=(
            f"run_history:{outcome.run_id}:"
            f"{outcome.run_history['head_digest']}",))
    print(json.dumps({
        "record_type": "five_step_demo/v2", "solved": True,
        "steps": {
            "1_install_and_verify": "loop-engine --self-test",
            "2_configure": "deterministic no-key settings",
            "3_compile": outcome.compiled_task["compiled_task_id"],
            "4_solve_and_verify": {
                "run_id": outcome.run_id,
                "mode": outcome.selected_mode,
                "verified": outcome.verification["passed"],
                "run_history": outcome.run_history,
            },
            "5_stage_learning_candidate": {
                "candidate": transition.to_dict(),
                "state": "candidate_only",
                "next": "independent candidates review then promote",
            },
        },
        "provider_calls": 0,
    }, indent=1))
    return 0
