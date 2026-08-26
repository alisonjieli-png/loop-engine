"""Registered DS-1000 benchmark Code Intelligence.

Only implemented and admission-tested operations are registered here. Model
outputs remain run artifacts and never become active Code Intelligence.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from loop_engine.code_nodes.solution_canvas import (
    SolutionLoopSpec,
    SolutionSpec,
    run_solution,
)
from loop_engine.code_nodes.solution_compiler import compile_solution, render_canvas
from loop_engine.core.store_serve import StoreRecord

from prepare import SOURCE_DIR, row_by_id, verify_source
from runtime import RuntimeImage, sandbox_command


PACK_VERSION = "1.0.0"
MODULE_NAME = "benchmarks.ds1000.code_intelligence"


class BenchmarkContractError(RuntimeError):
    """A typed benchmark operation received incompatible input."""


@dataclass(frozen=True)
class SolverTask:
    """The only upstream task view permitted to enter a model prompt."""

    problem_id: int
    library: str
    prompt: str
    prompt_sha256: str
    test_case_count: int

    def as_dict(self) -> dict:
        return {
            "record_type": "ds1000_solver_task/v1",
            "problem_id": self.problem_id,
            "library": self.library,
            "prompt": self.prompt,
            "prompt_sha256": self.prompt_sha256,
            "test_case_count": self.test_case_count,
        }


@dataclass(frozen=True)
class EvaluatorContext:
    """Evaluator-only task data that must never enter a model prompt."""

    problem_id: int
    library: str
    code_context: str
    code_context_sha256: str


@dataclass(frozen=True)
class CodeCandidate:
    problem_id: int
    library: str
    call_role: str
    raw_response: str
    code: str
    code_sha256: str
    extraction_strategy: str

    def as_dict(self) -> dict:
        return {
            "record_type": "ds1000_code_candidate/v1",
            "problem_id": self.problem_id,
            "library": self.library,
            "call_role": self.call_role,
            "raw_response": self.raw_response,
            "code": self.code,
            "code_sha256": self.code_sha256,
            "extraction_strategy": self.extraction_strategy,
        }


@dataclass(frozen=True)
class IsolatedEvaluation:
    problem_id: int
    library: str
    candidate_sha256: str
    passed: bool
    status: str
    upstream_result: str
    container_returncode: int | None
    container_stdout: str
    container_stderr: str
    image_id: str

    def as_dict(self) -> dict:
        return {
            "record_type": "ds1000_isolated_evaluation/v1",
            "problem_id": self.problem_id,
            "library": self.library,
            "candidate_sha256": self.candidate_sha256,
            "passed": self.passed,
            "status": self.status,
            "upstream_result": self.upstream_result,
            "container_returncode": self.container_returncode,
            "container_stdout": self.container_stdout,
            "container_stderr": self.container_stderr,
            "image_id": self.image_id,
        }


@dataclass(frozen=True)
class CanvasExecution:
    plan_digest: str
    plan: dict
    canvas: dict
    trace: tuple[dict, ...]
    evaluation: IsolatedEvaluation

    def as_dict(self) -> dict:
        return {
            "record_type": "ds1000_canvas_execution/v1",
            "plan_digest": self.plan_digest,
            "plan": self.plan,
            "canvas": self.canvas,
            "trace": list(self.trace),
            "evaluation": self.evaluation.as_dict(),
        }


def verify_pinned_source(source_root: Path = SOURCE_DIR) -> dict:
    """Verify commit, bytes, digests, IDs, labels, and prompt separation."""
    return verify_source(Path(source_root))


def load_solver_task(source_root: Path, problem_id: int) -> SolverTask:
    """Load the public prompt view and discard evaluator and reference fields."""
    verification = verify_source(Path(source_root))
    admitted = {
        int(row["problem_id"]): row["library"]
        for row in verification["selected_tasks"]
    }
    if int(problem_id) not in admitted:
        raise BenchmarkContractError(
            f"problem {problem_id} is outside population-v1")
    row = row_by_id(Path(source_root), int(problem_id))
    prompt = str(row["prompt"])
    return SolverTask(
        problem_id=int(problem_id),
        library=str(row["metadata"]["library"]),
        prompt=prompt,
        prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest(),
        test_case_count=int(row["metadata"]["test_case_cnt"]),
    )


def load_evaluator_context(source_root: Path,
                           problem_id: int) -> EvaluatorContext:
    """Load evaluator-only context through a separate typed boundary."""
    task = load_solver_task(source_root, problem_id)
    row = row_by_id(Path(source_root), int(problem_id))
    context = str(row["code_context"])
    return EvaluatorContext(
        problem_id=task.problem_id,
        library=task.library,
        code_context=context,
        code_context_sha256=hashlib.sha256(context.encode()).hexdigest(),
    )


def load_reference_for_admission(source_root: Path,
                                 problem_id: int) -> CodeCandidate:
    """Load a reference only for pre-model evaluator admission testing."""
    task = load_solver_task(source_root, problem_id)
    row = row_by_id(Path(source_root), int(problem_id))
    code = str(row["reference_code"])
    return CodeCandidate(
        task.problem_id,
        task.library,
        "admission_reference_not_solver_visible",
        "",
        code,
        hashlib.sha256(code.encode()).hexdigest(),
        "pinned_reference_admission_only",
    )


def safe_extract_code(task: SolverTask, raw_response: str,
                      call_role: str) -> CodeCandidate:
    """Extract code without executing it or consulting hidden evaluator data."""
    if not isinstance(task, SolverTask):
        raise BenchmarkContractError("safe_extract_code needs SolverTask")
    raw = str(raw_response)
    code = raw
    strategy = "plain_text"
    if "<code>" in code:
        code = code.split("<code>", 1)[1]
        code = code.split("</code>", 1)[0]
        strategy = "code_tag"
    elif "```python" in code:
        code = code.split("```python", 1)[1].split("```", 1)[0]
        strategy = "python_fence"
    elif "```" in code:
        code = code.split("```", 1)[1].split("```", 1)[0]
        strategy = "generic_fence"
    code = code.split("\nEND SOLUTION", 1)[0]
    if not code.strip():
        raise BenchmarkContractError("model response contained no candidate code")
    return CodeCandidate(
        problem_id=task.problem_id,
        library=task.library,
        call_role=str(call_role),
        raw_response=raw,
        code=code,
        code_sha256=hashlib.sha256(code.encode()).hexdigest(),
        extraction_strategy=strategy,
    )


def run_isolated_evaluator(candidate: CodeCandidate,
                           evaluator: EvaluatorContext,
                           runtime: RuntimeImage) -> IsolatedEvaluation:
    """Run one candidate through upstream checks inside the locked sandbox."""
    if not isinstance(candidate, CodeCandidate):
        raise BenchmarkContractError(
            "run_isolated_evaluator needs CodeCandidate")
    if not isinstance(evaluator, EvaluatorContext):
        raise BenchmarkContractError(
            "run_isolated_evaluator needs EvaluatorContext")
    if candidate.problem_id != evaluator.problem_id \
            or candidate.library != evaluator.library:
        raise BenchmarkContractError(
            "candidate and evaluator task identities do not match")
    payload = json.dumps({
        "problem_id": candidate.problem_id,
        "library": candidate.library,
        "code_context": evaluator.code_context,
        "candidate": candidate.code,
    })
    try:
        completed = subprocess.run(
            sandbox_command(runtime, interactive=True),
            input=payload, text=True, capture_output=True, timeout=150)
    except subprocess.TimeoutExpired as exc:
        return IsolatedEvaluation(
            candidate.problem_id,
            candidate.library,
            candidate.code_sha256,
            False,
            "container_timeout",
            "upstream evaluator did not return before the host timeout",
            None,
            str(exc.stdout or ""),
            str(exc.stderr or ""),
            runtime.image_id,
        )
    stdout = completed.stdout
    stderr = completed.stderr
    if completed.returncode != 0:
        return IsolatedEvaluation(
            candidate.problem_id,
            candidate.library,
            candidate.code_sha256,
            False,
            "container_failed",
            stderr or stdout or "container returned no diagnostic",
            completed.returncode,
            stdout,
            stderr,
            runtime.image_id,
        )
    try:
        row = json.loads(stdout)
    except json.JSONDecodeError:
        return IsolatedEvaluation(
            candidate.problem_id,
            candidate.library,
            candidate.code_sha256,
            False,
            "invalid_evaluator_output",
            "evaluator stdout was not one JSON object",
            completed.returncode,
            stdout,
            stderr,
            runtime.image_id,
        )
    return IsolatedEvaluation(
        candidate.problem_id,
        candidate.library,
        candidate.code_sha256,
        bool(row.get("passed")),
        "completed",
        str(row.get("result", "")),
        completed.returncode,
        stdout,
        stderr,
        runtime.image_id,
    )


def upstream_passed(evaluation: IsolatedEvaluation) -> bool:
    """Apply the upstream boolean pass rule without model judgment."""
    if not isinstance(evaluation, IsolatedEvaluation):
        raise BenchmarkContractError("upstream_passed needs IsolatedEvaluation")
    return evaluation.status == "completed" and evaluation.passed is True


def compile_and_run_canvas(candidate: CodeCandidate,
                           evaluator: EvaluatorContext,
                           runtime: RuntimeImage, *, parent=None,
                           ledger=None) -> CanvasExecution:
    """Compile and execute the typed code Canvas in the isolated runtime."""
    registry = {
        "ds1000_isolated_evaluator": lambda value, params: (
            run_isolated_evaluator(value, evaluator, runtime)),
    }
    spec = SolutionSpec(
        solution_id=(
            f"ds1000.{candidate.problem_id}.{candidate.call_role}."
            f"{candidate.code_sha256[:12]}"),
        allowed_modes=("deterministic",),
        loops=(SolutionLoopSpec(
            "execute_candidate_in_isolated_upstream_evaluator",
            "ds1000_isolated_evaluator",
            mode="deterministic",
            params={
                "input_contract": "ds1000_code_candidate/v1",
                "output_contract": "ds1000_isolated_evaluation/v1",
                "runtime_image_id": runtime.image_id,
            }),),
    )
    compiled = compile_solution(spec, registry)
    if compiled["plan"] is None:
        raise BenchmarkContractError(
            "Canvas did not compile: " + "; ".join(compiled["violations"]))
    trace: list[dict] = []
    evaluation = run_solution(
        spec, registry, candidate, trace=trace, ledger=ledger, parent=parent)
    if not isinstance(evaluation, IsolatedEvaluation):
        raise BenchmarkContractError(
            "Canvas returned a value outside its output contract")
    if parent is not None:
        parent.ledger.record(
            loop_id=parent.loop_id,
            event="custom",
            action="upstream_evaluation_completed",
            problem_id=candidate.problem_id,
            candidate_sha256=candidate.code_sha256,
            evaluator="DS-1000 pinned upstream execution",
            evaluator_passed=upstream_passed(evaluation),
            runtime_image_id=runtime.image_id,
            canvas_plan_digest=compiled["digest"],
        )
    return CanvasExecution(
        plan_digest=compiled["digest"],
        plan=compiled["plan"],
        canvas=render_canvas(compiled["plan"]),
        trace=tuple(trace),
        evaluation=evaluation,
    )


def _record(record_id: str, title: str, function_name: str,
            inputs: dict, outputs: dict, effects: tuple[str, ...],
            admission_test_ref: str, keywords: tuple[str, ...]) -> StoreRecord:
    return StoreRecord(
        record_id,
        "node",
        title,
        body={
            "role": "benchmark_code_intelligence",
            "maturity": "registered",
            "version": PACK_VERSION,
            "handle": {"module": MODULE_NAME, "callable": function_name},
            "typed_contract": {"inputs": inputs, "outputs": outputs},
            "effects": list(effects),
            "admission_test_ref": admission_test_ref,
            "facets": {
                "category": "benchmark_operation",
                "subcategory": function_name,
                "scope": "ds1000_population_v1",
                "lifecycle": "registered",
                "effects": list(effects),
            },
        },
        tags=("ds1000", "registered", *keywords),
        tier="core",
        source="benchmarks/ds1000/code_intelligence.py",
    )


def code_intelligence_records() -> tuple[StoreRecord, ...]:
    """Return the six tested operations, and no generated solution records."""
    return (
        _record(
            "ds1000.code.verify_pinned_source",
            "Verify the pinned DS-1000 source commit, hashes, IDs, and labels",
            "verify_pinned_source",
            {"source_root": "Path"},
            {"verification": "ds1000_source_verification/v1"},
            ("read_files", "read_git_metadata"),
            "benchmarks/ds1000/self_test.py::source_verifier_passes",
            ("source", "hash", "verify"),
        ),
        _record(
            "ds1000.code.load_solver_task",
            "Load a typed solver task without evaluator or reference content",
            "load_solver_task",
            {"source_root": "Path", "problem_id": "int"},
            {"task": "ds1000_solver_task/v1"},
            ("read_files",),
            "benchmarks/ds1000/self_test.py::task_loader_hides_evaluator",
            ("task", "loader", "prompt"),
        ),
        _record(
            "ds1000.code.safe_extract_code",
            "Extract typed Python code from a model response without execution",
            "safe_extract_code",
            {"task": "ds1000_solver_task/v1", "raw_response": "str"},
            {"candidate": "ds1000_code_candidate/v1"},
            ("pure",),
            "benchmarks/ds1000/self_test.py::safe_extractor_is_non_executing",
            ("extract", "code", "safe"),
        ),
        _record(
            "ds1000.code.run_isolated_evaluator",
            "Run one code candidate in the network-disabled DS-1000 sandbox",
            "run_isolated_evaluator",
            {"candidate": "ds1000_code_candidate/v1",
             "evaluator": "EvaluatorContext", "runtime": "RuntimeImage"},
            {"evaluation": "ds1000_isolated_evaluation/v1"},
            ("container_execution", "untrusted_code_execution"),
            "benchmarks/ds1000/self_test.py::reference_tasks_pass_in_sandbox",
            ("isolated", "sandbox", "execute"),
        ),
        _record(
            "ds1000.code.upstream_passed",
            "Apply the pinned upstream DS-1000 pass or fail rule",
            "upstream_passed",
            {"evaluation": "ds1000_isolated_evaluation/v1"},
            {"passed": "bool"},
            ("pure",),
            "benchmarks/ds1000/self_test.py::negative_candidate_is_rejected",
            ("upstream", "evaluate", "verify"),
        ),
        _record(
            "ds1000.code.compile_and_run_canvas",
            "Compile and run the typed code Solution Canvas in the sandbox",
            "compile_and_run_canvas",
            {"candidate": "ds1000_code_candidate/v1",
             "evaluator": "EvaluatorContext", "runtime": "RuntimeImage"},
            {"canvas": "ds1000_canvas_execution/v1"},
            ("container_execution", "run_history_events"),
            "benchmarks/ds1000/self_test.py::canvas_compiles_and_runs",
            ("canvas", "compile", "run"),
        ),
    )


def resolve_registered_callable(record: StoreRecord):
    handle = dict((record.body or {}).get("handle") or {})
    if handle.get("module") != MODULE_NAME:
        raise BenchmarkContractError(
            f"record {record.record_id} points outside the benchmark pack")
    name = str(handle.get("callable", ""))
    value = getattr(sys.modules[__name__], name, None)
    if not callable(value):
        raise BenchmarkContractError(
            f"record {record.record_id} has no callable entrypoint {name!r}")
    return value


def validate_code_intelligence_pack() -> dict:
    records = code_intelligence_records()
    resolved = []
    for record in records:
        function = resolve_registered_callable(record)
        body = dict(record.body or {})
        if body.get("maturity") != "registered" \
                or not body.get("typed_contract") \
                or not body.get("effects") \
                or not body.get("version") \
                or not body.get("admission_test_ref"):
            raise BenchmarkContractError(
                f"record {record.record_id} is missing an admission field")
        resolved.append({
            "record_id": record.record_id,
            "callable": function.__name__,
            "version": body["version"],
            "admission_test_ref": body["admission_test_ref"],
        })
    if len(records) != 6:
        raise BenchmarkContractError(
            "the DS-1000 pack must contain exactly the six admitted operations")
    return {
        "record_type": "ds1000_code_intelligence_admission/v1",
        "ok": True,
        "records": resolved,
    }


def benchmark_code_pack():
    """Project the six admitted callables into the canonical Code pack."""
    from loop_engine.loop.loop_capsule import ExternalPayloadRef
    from loop_engine.core.code_intelligence_assets import (
        CodeAssetSpec,
    )
    from loop_engine.core.intelligence_portfolio import (
        BenchmarkCodePack,
        BenchmarkCodeRegistration,
        LensFamily,
    )

    family_map = {
        "verify_pinned_source": (LensFamily.VERIFICATION_EVALUATION,),
        "load_solver_task": (LensFamily.OUTPUT_CONTRACT_FORMAT,),
        "safe_extract_code": (LensFamily.OUTPUT_CONTRACT_FORMAT,),
        "run_isolated_evaluator": (LensFamily.VERIFICATION_EVALUATION,),
        "upstream_passed": (LensFamily.VERIFICATION_EVALUATION,),
        "compile_and_run_canvas": (LensFamily.COST_RESOURCE,),
    }
    effects = {
        "verify_pinned_source": ("reads_fs", "spawns_process"),
        "load_solver_task": ("reads_fs", "spawns_process"),
        "safe_extract_code": ("pure",),
        "run_isolated_evaluator": ("spawns_process",),
        "upstream_passed": ("pure",),
        "compile_and_run_canvas": ("spawns_process",),
    }
    registrations = []
    for record in code_intelligence_records():
        function = resolve_registered_callable(record)
        body = dict(record.body or {})
        handle = dict(body["handle"])
        source = inspect.getsource(function).encode()
        digest = hashlib.sha256(source).hexdigest()
        payload = ExternalPayloadRef(
            uri=(f"python://benchmarks/ds1000/code_intelligence/"
                 f"{function.__name__}"),
            digest=digest,
            size_bytes=len(source),
            media_type="text/x-python",
        )
        contract = dict(body["typed_contract"])
        spec = CodeAssetSpec(
            asset_id=record.record_id,
            name=record.title,
            description=record.title,
            asset_kind="function",
            source_kind="local_path",
            body_ref=payload,
            entrypoints=(function.__name__,),
            modes=("deterministic",),
            input_contract=json.dumps(
                contract["inputs"], sort_keys=True),
            output_contract=json.dumps(
                contract["outputs"], sort_keys=True),
            effects=effects[function.__name__],
            dependencies=("loop-engine",),
            file_count=1,
            line_count=len(source.splitlines()),
            load_strategy="import",
            template_id="pure_function",
            version=body["version"],
            license="MIT",
            lifecycle="registered",
            admission_ref=body["admission_test_ref"],
            metadata={
                "implementation_module": handle["module"],
                "implementation_callable": handle["callable"],
            },
        )
        registrations.append(BenchmarkCodeRegistration(
            spec=spec,
            benchmark_ids=("ds1000-pandas-sklearn-4-v1",),
            lens_families=family_map[function.__name__],
            entrypoints=((function.__name__, function),),
        ))
    return BenchmarkCodePack(
        "ds1000-pandas-sklearn-4-v1-code-pack",
        tuple(registrations),
    )
