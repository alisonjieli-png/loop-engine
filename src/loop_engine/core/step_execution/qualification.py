"""Qualify one step executor engine on a fixture step: fresh start, material loading, output reading.

Owns the qualification fixture (a step whose instructions, skill and expected
answer carry markers made for one run), the decoys planted where a harness
must not look (the folder above the step and the global locations the
manifest names in the real home folder), the qualification run record
step_harness_qualification_run/v1, and qualify_engine, which writes one
engine_qualification/v1 at proof level local_contract. A registered harness
stays a candidate engine until this record proves, on the fixture step, that
a fresh instance started with only the step's material (no decoy marker
reached a request), that the step's material loaded (its markers reached the
harness's model requests), and that the declared output was read (a
deterministic fixture broker's answer came back through the manifest's output
rule). Loading counts only from a marker inside a request the harness sent; an
exit, a session identifier or a documented bridge never counts. No model is
called: the only broker is the fixture. Belongs to the step execution
component (roadmap S-6.31, S-6.42).
"""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import pwd
import secrets

from ..configuration_capabilities import digest
from ..engines.records import EngineQualification, EvidenceReference, QualificationScope
from ..external_harness_contract import STEP_EDGE, STEP_EXECUTOR_SLOT
from .engines import project_descriptor
from .records import (
    COMPLETED, StepBudget, StepInput, StepMaterial, StepOutputPort, StepRequirements, StepRunRequest,
    StepServices)

RUN_RECORD_TYPE = "step_harness_qualification_run/v1"
REVIEWER = "loop_engine.core.step_execution.qualification@1.0.0"
FIXTURE_CONTRACT = "step_qualification_fixture/v1"
VALIDITY_DAYS = 30
#: The owning profiles of the fixture step: model-led work and deterministic work.
PROFILE_REF, DETERMINISTIC_PROFILE_REF = "practitioner.solver@1.0.0", "practitioner.code_execution@1.0.0"
RUNGS = ("none", "connected", "material_listed", "material_loaded", "step_finished")


def markers(token: str) -> dict:
    return {"instruction": f"BALTOR-QUALIFY-INSTRUCTION-{token}", "skill": f"BALTOR-QUALIFY-SKILL-{token}",
            "answer": f"BALTOR-QUALIFY-ANSWER-{token}", "decoy": f"BALTOR-QUALIFY-DECOY-{token}"}


def fixture_request(engine, token: str) -> StepRunRequest:
    """The fixture step: a model-led text step for a harness, a template step for the Loop runtime."""
    marks = markers(token)
    profile = engine.executor_profile()
    deterministic = profile.supported_modes == ("deterministic",)
    skill_supported = any(item.component_type == "skill" and item.support in ("native", "translated", "embedded")
                          for item in profile.compatibility)
    material = (StepMaterial("skill", "qualification-skill", f"{marks['skill']} Answer with the fixture answer."),) \
        if skill_supported else ()
    common = dict(
        request_id="qualification-" + token, owning_loop_ref="qualification", owning_profile_ref=PROFILE_REF,
        definition_ref="step_qualification_fixture", definition_digest=digest({"fixture": FIXTURE_CONTRACT}),
        step_name="qualification_fixture", attempt=1, idempotency_key="qualification-" + token,
        goal=f"Answer the qualification fixture. {marks['instruction']}",
        instructions=f"Reply with the fixture answer only. {marks['instruction']}",
        output_ports=(StepOutputPort("answer", "text/plain", True),), output_contract_ref=FIXTURE_CONTRACT,
        evaluation_contract_ref="exact_text/v1", publication="final_only", material=material,
        budget=StepBudget(120.0, 2, None, 0))
    if deterministic:
        common["owning_profile_ref"] = DETERMINISTIC_PROFILE_REF
        return StepRunRequest(**common, inputs=(StepInput("marker", "text/plain", marks["answer"]),),
                              mode="deterministic", procedure_ref="text.render_template@1",
                              procedure_parameters={"template": "$marker"}, granted_effects=(),
                              authorize_model_calls=False, model_routes=(),
                              requirements=StepRequirements(delegation_required=False, fresh_instance_required=False))
    return StepRunRequest(**common, inputs=(), mode="non_deterministic", procedure_ref="", procedure_parameters={},
                          granted_effects=(), authorize_model_calls=True, model_routes=(),
                          requirements=StepRequirements(delegation_required=True, fresh_instance_required=False))


def fixture_broker(answer: str):
    """A deterministic broker that answers every request with the fixture answer; no model is called."""
    def broker(request: dict) -> dict:
        return {"id": "qualification-fixture", "object": "chat.completion", "created": 0,
                "model": request.get("model", ""), "choices": [{"index": 0, "finish_reason": "stop", "message": {
                    "role": "assistant", "content": answer}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}}
    return broker


def decoy_files(folder: Path, manifest, token: str) -> tuple:
    """Decoys beside the step and at each global location the manifest names; (host file, sandbox path)."""
    marks, binds = markers(token), []
    folder.mkdir(parents=True, exist_ok=True)
    for name in ("AGENTS.md", "CLAUDE.md"):
        path = folder / ("parent-" + name)
        path.write_text(f"# Instructions above the step\n\n{marks['decoy']}\n", encoding="utf-8")
        binds.append((str(path), "/launch/" + name))
    home = pwd.getpwuid(os.getuid()).pw_dir
    for number, location in enumerate(manifest.layout.global_locations if manifest is not None else ()):
        path = folder / f"global-{number}.md"
        header = f"---\nname: decoy-global-skill\ndescription: {marks['decoy']}\n---\n\n" \
            if location.endswith("SKILL.md") else "# Global instructions\n\n"
        path.write_text(header + marks["decoy"] + "\n", encoding="utf-8")
        binds.append((str(path), f"{home}/{location}"))
    return tuple(binds)


def _captures(work_root: Path) -> list:
    return [path.read_text("utf-8", errors="replace") for path in sorted(work_root.glob("launch-*/capture/*.json"))]


def _phase(engine, request, work_root: Path, *, broker, decoys) -> dict:
    services = StepServices(str(work_root), broker=broker, keep_launch_folders=True, decoy_binds=decoys)
    result = engine.run_step(request, services)
    captured = _captures(work_root)
    return {"result": result, "captured": captured}


def qualify_engine(engine, installation, *, work_root: Path, as_of: "datetime | None" = None,
                   token: "str | None" = None) -> tuple:
    """Run the fixture step and return (engine_qualification/v1, the run record)."""
    moment, token = as_of or datetime.now(timezone.utc), token or secrets.token_hex(6)
    marks = markers(token)
    request = fixture_request(engine, token)
    manifest = getattr(engine, "manifest", None)
    decoys = decoy_files(work_root / "decoys", manifest, token) if manifest is not None else ()
    phases = {}
    if request.mode == "deterministic":
        phases["fixture"] = _phase(engine, request, work_root / "fixture", broker=None, decoys=decoys)
        loaded_texts = [item.text for item in phases["fixture"]["result"].outputs]
    else:
        phases["no_model"] = _phase(engine, request, work_root / "no-model", broker=None, decoys=decoys)
        phases["fixture"] = _phase(engine, request, work_root / "fixture", broker=fixture_broker(marks["answer"]),
                                   decoys=decoys)
        loaded_texts = phases["no_model"]["captured"] + phases["fixture"]["captured"]
    joined = "\n".join(loaded_texts)
    fixture = phases["fixture"]["result"]
    wanted = [marks["answer"]] if request.mode == "deterministic" else [marks["instruction"]] + (
        [marks["skill"]] if request.material else [])
    found = {marker: marker in joined for marker in wanted}
    decoys_found = marks["decoy"] in joined or any(marks["decoy"] in item.text for item in fixture.outputs)
    answered = fixture.status == COMPLETED and [item.text.strip() for item in fixture.outputs] == [marks["answer"]]
    connected = bool(loaded_texts) or fixture.status == COMPLETED
    rung = ("step_finished" if connected and all(found.values()) and not decoys_found and answered
            else "material_loaded" if connected and all(found.values()) and not decoys_found
            else "connected" if connected else "none")
    record = {"record_type": RUN_RECORD_TYPE, "engine_ref": f"{engine.info().harness_id}@{engine.info().adapter_version}",
              "installation_digest": installation.installation_digest, "token_digest": digest(token),
              "fresh_instance": not decoys_found, "markers_found": {key[:24]: value for key, value in found.items()},
              "output_read": answered, "rung": rung, "model_calls_to_a_real_model": 0,
              "phases": {name: {"status": phase["result"].status, "failure_kind": phase["result"].failure_kind,
                                "error_code": phase["result"].error_code,
                                "captured_requests": len(phase["captured"]),
                                "material": [item.to_dict() for item in phase["result"].material],
                                "native_identities": dict(phase["result"].native_identities)}
                         for name, phase in phases.items()},
              "decoys": [target for _, target in decoys], "issued_at": moment.isoformat()}
    path = work_root / "qualification-run.json"
    text = json.dumps(record, indent=1, sort_keys=True, default=str)
    path.write_text(text, encoding="utf-8")
    descriptor = project_descriptor(engine, installation, as_of=moment)
    qualification = EngineQualification(
        STEP_EXECUTOR_SLOT, descriptor.engine_ref, descriptor.content_digest, installation.installation_digest,
        QualificationScope(STEP_EDGE, None, (FIXTURE_CONTRACT,)), "local_contract", None if rung == "none" else rung,
        (EvidenceReference(str(path), hashlib.sha256(text.encode("utf-8")).hexdigest()),), REVIEWER,
        "approved" if rung == "step_finished" else "rejected", moment.isoformat(),
        (moment + timedelta(days=VALIDITY_DAYS)).isoformat())
    return qualification, record


def self_test():
    """Run the step execution checks, which cover the qualification."""
    from .engines_checks import self_test as run_engine_checks
    return run_engine_checks()
