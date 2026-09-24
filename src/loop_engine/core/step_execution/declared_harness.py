"""The engine that runs any manifest-declared harness for one step: DeclaredHarnessStepEngine.

Owns the one engine class behind every step_harness_manifest/v1: a
native_protocol_harness such as Pi in print mode, a harness a customer
declares, or the custom_loop_harness that starts Baltor's own Loop runtime as
a separate process. For each attempt it compiles a fresh launch folder, places
the step's material where the manifest's layout says, starts the harness in
the sandbox through core.step_execution.harness_launch, reads completion and
output the way the manifest declares, and returns one step_run_result/v1 with
the material evidence it observed, the broker's accounting and the process and
sandbox identities. It reports; the envelope decides whether the attempt counts
as delegation. Belongs to the step execution component (roadmap S-6.31, S-6.42).
Does not own: selection, qualification, a model call (the owning Loop's broker
makes every one) or acceptance.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ..engines.records import EngineRecordError
from ..external_harness import HarnessAdapterInfo
from ..external_harness_contract import ADAPTER_CONTRACT_VERSION, STEP_EDGE
from ..harness_execution_contracts import HarnessExecutionCapabilities
from . import harness_launch as launcher
from .harness_manifest import STEP_RESULT_JSON, StepHarnessManifest, render_launch
from .records import (
    BUDGET_EXHAUSTED, COMPLETED, FAILED, REFUSED, UNAVAILABLE, MaterialObservation, StepAccounting, StepOutput,
    StepRunResult, text_digest)

#: A request-file harness may write at most this many changed files into the record.
MAXIMUM_RECORDED_CHANGES = 64


def _snippet(text: str) -> str:
    """The distinctive line of a placed file that shows it entered a model request."""
    lines = [line.strip() for line in text.splitlines() if len(line.strip()) >= 12
             and not line.strip().startswith(("#", "---", "name:"))]
    return lines[0][:120] if lines else text.strip()[:120]


class DeclaredHarnessStepEngine:
    """One manifest-declared harness as a step executor engine."""

    def __init__(self, manifest: StepHarnessManifest, software: launcher.HarnessSoftware, *,
                 model_name: str = "step-model"):
        if not isinstance(manifest, StepHarnessManifest) or not isinstance(software, launcher.HarnessSoftware):
            raise EngineRecordError("invalid_field", "a declared harness is a manifest and its pinned software")
        self.manifest, self.software, self.model_name = manifest, software.pinned(), model_name

    def info(self) -> HarnessAdapterInfo:
        manifest, available = self.manifest, self.software.present() and launcher.sandbox_available()
        return HarnessAdapterInfo(
            manifest.harness_id, manifest.harness_version, manifest.launch.executable,
            manifest.launch.pinned_version or "", manifest.supported_features or ("typed_request",),
            ("started fresh in a sandbox for each step",), available,
            "" if available else "the pinned software or the sandbox is missing",
            HarnessExecutionCapabilities(manifest.supported_features, ("model_calls", "wall_time"),
                                         manifest.isolation, (), manifest.native_controls),
            ADAPTER_CONTRACT_VERSION, manifest.engine_kind, (STEP_EDGE,))

    def executor_profile(self):
        return self.manifest.executor_profile()

    def run_step(self, request, services) -> StepRunResult:
        try:
            return self._run(request, services)
        except EngineRecordError as exc:
            status = REFUSED if exc.code in ("material_has_no_place",
                                             "configuration_writer_not_supported_for_steps") else FAILED
            kind = "capability_requirement_unsatisfied" if status == REFUSED else "engine_reported_failure"
            return _failed(request, status, kind, exc.code)

    def _run(self, request, services) -> StepRunResult:
        if self.software.pinned().identities != self.software.identities:
            return _failed(request, UNAVAILABLE, "engine_unavailable", "software_changed")
        manifest = self.manifest
        folder = launcher.LaunchFolder.create(Path(services.work_root))
        try:
            placed = launcher.place_material(folder, manifest, request, model_name=self.model_name)
            (folder.root / "io" / "request.json").write_text(json.dumps(request.to_dict(), sort_keys=True),
                                                            encoding="utf-8")
            values = launcher.template_values(folder, self.software, model_name=self.model_name,
                                              prompt=request.goal.strip().splitlines()[0][:400])
            arguments, environment = render_launch(manifest, values)
            broker = services.broker if request.authorize_model_calls else None
            mode = "none" if manifest.network == "none" else ("broker" if broker is not None else "no_model")
            plan = launcher.LaunchPlan(
                folder, (self.software.executable, *arguments), tuple(environment.items()), self.software, mode,
                manifest.model_wire, self.model_name, request.budget.wall_time_seconds, request.budget.model_calls,
                manifest.native_tools == "none",
                launcher.INSIDE["step_request_file"] if manifest.launch.standard_input == "step_request_json" else "",
                tuple(services.decoy_binds))
            outcome = launcher.launch(plan, manifest_digest=manifest.content_digest, broker=broker)
            result_path = folder.root / "io" / "result.json"
            result_text = result_path.read_text("utf-8", errors="replace") if result_path.is_file() else ""
            return self._result(request, outcome, placed, folder, result_text)
        finally:
            if not services.keep_launch_folders:
                launcher.remove_folder(folder)

    def _result(self, request, outcome, placed, folder, result_text) -> StepRunResult:
        manifest = self.manifest
        identities = {"process_identity": outcome.process_identity,
                      "sandbox_profile_digest": outcome.sandbox_profile_digest,
                      "exit_code": outcome.exit_code, "captured_requests": len(outcome.captured_requests),
                      "broker_refusals": list(outcome.refusals)[:16]}
        # No model call spends nothing; a brokered call's price is not known here.
        accounting = StepAccounting(outcome.model_calls, outcome.input_tokens, outcome.output_tokens,
                                    0.0 if outcome.model_calls == 0 else None)
        material = _observations(request, placed, folder, outcome.captured_requests)
        changes = _changes(folder, placed)
        base = dict(material=material, identities=identities, accounting=accounting, changes=changes,
                    seconds=outcome.elapsed_seconds)
        if outcome.timed_out:
            return _assemble(request, BUDGET_EXHAUSTED, "authority_exhausted", "time_budget_exhausted", (), **base)
        text, reason = launcher.read_output(manifest.completion, outcome.stdout, result_text)
        if manifest.completion.output_format == STEP_RESULT_JSON and text is not None:
            try:
                inner = StepRunResult.from_dict(json.loads(text))
            except (ValueError, EngineRecordError):
                return _assemble(request, FAILED, "output_validation_failed", "invalid_step_result", (), **base)
            if inner.request_id != request.request_id or inner.request_digest != request.digest:
                return _assemble(request, FAILED, "output_validation_failed", "step_result_for_another_request",
                                 (), **base)
            base["identities"].update({key: value for key, value in dict(inner.native_identities).items()
                                       if key in ("loop_id", "terminal_code", "steps_run", "step_profile",
                                                  "procedure")})
            return _assemble(request, inner.status, inner.failure_kind, inner.error_code, inner.outputs, **base)
        if outcome.exit_code not in manifest.completion.completed_exit_codes or text is None:
            return _assemble(request, FAILED, "engine_reported_failure", reason or "harness_exit_code", (), **base)
        port = next((item for item in request.output_ports if item.required), request.output_ports[0])
        return _assemble(request, COMPLETED, "", "", (StepOutput(port.name, port.media_type, text),), **base)


def _failed(request, status, kind, code) -> StepRunResult:
    return StepRunResult(request.request_id, request.digest, status, kind, code, (), (), (), "none",
                         StepAccounting(0, 0, 0, None), (), {}, None, (), None, None)


def _assemble(request, status, kind, code, outputs, *, material, identities, accounting, changes, seconds):
    return StepRunResult(request.request_id, request.digest, status, kind, code, tuple(outputs), (), changes,
                         "none", accounting, material, identities, None, (), seconds, None)


def _observations(request, placed, folder, captured) -> tuple:
    """Materialized with its digest, and loaded only when its text reached a model request."""
    observations = []
    joined = "\n".join(captured)
    for relative, placed_digest in sorted(placed.items()):
        if not relative.startswith("step/"):
            continue
        path = folder.root / relative
        body = path.read_text("utf-8")
        kind = "skill" if relative.endswith("/SKILL.md") else "instruction_file"
        name = path.parent.name if kind == "skill" else "step-instructions"
        loaded = bool(joined) and json.dumps(_snippet(body))[1:-1] in joined
        observations.append(MaterialObservation(
            kind, name if kind == "skill" else name, placed_digest, "loaded" if loaded else "materialized",
            "a model request carried its text" if loaded else "placed with its digest"))
    return tuple(observations)


def _changes(folder, placed) -> tuple:
    """Files the harness wrote in its step folder, beyond the placed material."""
    step, changes = folder.root / "step", []
    for path in sorted(step.rglob("*")):
        relative = path.relative_to(folder.root).as_posix()
        if path.is_file() and not path.is_symlink() and relative not in placed and ".git/" not in relative:
            changes.append((path.relative_to(step).as_posix(), hashlib.sha256(path.read_bytes()).hexdigest()))
    return tuple(changes[:MAXIMUM_RECORDED_CHANGES])


def self_test():
    """Run the step execution checks, which cover the declared harness engine."""
    from .engines_checks import self_test as run_engine_checks
    return run_engine_checks()
