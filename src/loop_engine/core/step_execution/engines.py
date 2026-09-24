"""The step executor slot's factory table and the projection of its engines into descriptors.

Owns ENGINE_FACTORIES, the one table that names step executor engine classes
by engine kind with their typed settings (it defines no engine class), the
typed settings records a host installation carries (a declared harness names
its manifest, the manifest digest, the program and the read-only software
mounts; the in-process Loop engine names nothing), build_engine,
project_descriptors (the step_executor slot's descriptor projection: an
engine's own declaration, the executor profile and its one qualification
become an engine_descriptor/v1, with the lifecycle candidate until an
approved, unexpired qualification binds the exact installation) and
StepRequirementScreen, the slot's requirement comparison bound to one step for
the shared selector. Belongs to the step execution component (roadmap S-6.30,
S-6.31).
Does not own: an engine's behavior, selection or dispatch. Settings never hold
authority or a credential, and a projection starts nothing.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
from pathlib import Path

from ..configuration_capabilities import ConfigurationFact, digest
from ..engines.decision_records import EligibilityRefusal
from ..engines.host_records import EngineInstallation
from ..engines.records import (
    EngineCostBasis, EngineDescriptor, EngineLocality, EngineQualification, EngineRecordError)
from ..external_harness_contract import STEP_EDGE, STEP_EXECUTOR_SLOT
from .harness_launch import HarnessSoftware
from .harness_manifest import StepHarnessManifest
from .records import StepRunRequest, unmet_step_requirements

SETTINGS_RECORD_TYPES = ("declared_harness_settings/v1", "loop_runtime_settings/v1")
DECLARED_SETTINGS, LOOP_SETTINGS = SETTINGS_RECORD_TYPES
#: Kind -> (settings record type, constructor path, engine module). The constructor
#: and module are data here; build_engine imports only the classes named below.
ENGINE_FACTORIES = {
    "native_protocol_harness": (DECLARED_SETTINGS, "loop_engine.core.step_execution.declared_harness"
                                                   ".DeclaredHarnessStepEngine",
                                "src/loop_engine/core/step_execution/declared_harness.py"),
    "custom_loop_harness": (DECLARED_SETTINGS, "loop_engine.core.step_execution.declared_harness"
                                               ".DeclaredHarnessStepEngine",
                            "src/loop_engine/core/step_execution/declared_harness.py"),
    "in_process_runner": (LOOP_SETTINGS, "loop_engine.core.step_execution.loop_runtime.LoopRuntimeStepEngine",
                          "src/loop_engine/core/step_execution/loop_runtime.py"),
}
#: The ladder rungs at which a qualification also proves a fresh instance for each step.
FRESH_INSTANCE_RUNGS = ("material_loaded", "step_finished", "independently_accepted")
PROJECTION_SOURCE = "loop_engine.core.step_execution.engines.project_descriptors"
AVAILABILITY_SECONDS = 3600
_DECLARED_KEYS = ("record_type", "manifest", "manifest_digest", "executable", "software_paths")


def declared_settings(manifest: StepHarnessManifest, software: HarnessSoftware) -> dict:
    """The typed settings of one declared harness installation."""
    return {"record_type": DECLARED_SETTINGS, "manifest": manifest.harness_id,
            "manifest_digest": manifest.content_digest, "executable": software.executable,
            "software_paths": list(software.software_paths)}


def loop_settings() -> dict:
    return {"record_type": LOOP_SETTINGS}


def _read_settings(installation: EngineInstallation) -> dict:
    settings = dict(installation.settings)
    factory = ENGINE_FACTORIES.get(installation.engine_kind)
    if factory is None:
        raise EngineRecordError("unsupported_engine_kind", installation.engine_kind)
    if settings.get("record_type") != factory[0]:
        raise EngineRecordError("engine_settings_refused", "the settings record does not match the engine kind")
    expected = _DECLARED_KEYS if factory[0] == DECLARED_SETTINGS else ("record_type",)
    if set(settings) != set(expected):
        raise EngineRecordError("engine_settings_refused", f"settings hold exactly {sorted(expected)}")
    return settings


def build_engine(installation: EngineInstallation, manifests):
    """Construct the engine one installation declares; an unknown kind or wrong settings refuse."""
    settings = _read_settings(installation)
    if settings["record_type"] == LOOP_SETTINGS:
        from .loop_runtime import LoopRuntimeStepEngine
        return LoopRuntimeStepEngine()
    manifest = manifests.manifest(settings["manifest"])
    if manifest.content_digest != settings["manifest_digest"] or manifest.engine_kind != installation.engine_kind:
        raise EngineRecordError("manifest_changed", "the installation binds another manifest or kind")
    if manifest.harness_id != installation.engine_id:
        raise EngineRecordError("engine_settings_refused", "a declared harness is installed under its own identity")
    from .declared_harness import DeclaredHarnessStepEngine
    return DeclaredHarnessStepEngine(manifest, HarnessSoftware(settings["executable"],
                                                               tuple(settings["software_paths"])))


def _module_digest(dotted: str) -> str:
    module_path = ENGINE_FACTORIES[dotted][2]
    path = Path(__file__).resolve().parents[3] / module_path
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else digest(module_path)


def qualification_fact(qualification, descriptor, installation, as_of) -> ConfigurationFact:
    """The one qualification of an installation as a fact; another binding reads unknown."""
    if qualification is None:
        return ConfigurationFact()
    try:
        return qualification.fact_for(descriptor, installation.installation_digest,
                                      source_ref="engine_qualification:" + qualification.content_digest[:16])
    except EngineRecordError:
        return ConfigurationFact()


def proves_fresh_instance(qualification, as_of) -> bool:
    """An approved, unexpired qualification at a rung that shows only the step's material loaded."""
    return (isinstance(qualification, EngineQualification) and qualification.decision == "approved"
            and qualification.ladder_rung in FRESH_INSTANCE_RUNGS
            and datetime.fromisoformat(qualification.expires_at) > as_of)


def project_descriptor(engine, installation: EngineInstallation, *, as_of: datetime,
                       qualification: "EngineQualification | None" = None) -> EngineDescriptor:
    """One engine's own declaration, projected; the lifecycle stays candidate until qualified.

    The lifecycle, availability and qualification are observations outside the
    descriptor's identity, so the qualification binds the same digest before and after."""
    info, profile = engine.info(), engine.executor_profile()
    manifest = getattr(engine, "manifest", None)
    expires = (as_of + timedelta(seconds=AVAILABILITY_SECONDS)).isoformat()
    identity = {"info": {"harness_id": info.harness_id, "adapter_version": info.adapter_version,
                         "engine_kind": info.engine_kind},
                "module": _module_digest(installation.engine_kind),
                "software": [list(item) for item in getattr(getattr(engine, "software", None), "identities", ())],
                "manifest": manifest.content_digest if manifest is not None else ""}
    availability = ConfigurationFact("available" if info.available else "unavailable", PROJECTION_SOURCE,
                                     digest(identity), expires)
    upstream, revision, licence = (manifest.source if manifest is not None
                                   else ("https://github.com/alisonjieli-png/loop-engine", None, "unknown"))

    def descriptor(qualification_fact, lifecycle):
        return EngineDescriptor(
            STEP_EXECUTOR_SLOT, info.harness_id, info.adapter_version, info.engine_kind,
            ENGINE_FACTORIES[installation.engine_kind][1], digest(identity),
            "step_harness_manifest/v1" if manifest is not None else "harness_adapter_registration/v1",
            manifest.content_digest if manifest is not None else digest(identity["info"]), profile.to_dict(),
            (STEP_EDGE,), profile.supported_modes, profile.required_effects, profile.isolation,
            EngineLocality("core.facets.LOCALITY", "local_machine"), (), profile.enforced_limits,
            "free" if profile.model_wire == "none" else "metered",
            EngineCostBasis("provider_reported", None, None, None), licence, upstream, revision or "unpinned",
            availability, qualification_fact, lifecycle, "main",
            ("a_delegation_claim_cannot_be_met_by_an_in_process_engine",))
    unqualified = descriptor(ConfigurationFact(), "candidate")
    fact = qualification_fact(qualification, unqualified, installation, as_of)
    return unqualified if fact.current_state(as_of) != "qualified" else descriptor(fact, "active")


def project_descriptors(engines, installations, *, as_of: datetime, qualifications=None) -> tuple:
    """Every installed step executor engine's descriptor, keyed by installation."""
    qualifications = qualifications or {}
    return tuple((item.installation_id, project_descriptor(engines[item.installation_id], item, as_of=as_of,
                                                           qualification=qualifications.get(item.installation_id)))
                 for item in installations if item.installation_id in engines)


@dataclass(frozen=True)
class StepRequirementScreen:
    """The step executor slot's requirement comparison, bound to one step for the selector."""

    request: StepRunRequest
    as_of: datetime

    def screen(self, candidate) -> tuple:
        from .records import ExecutorProfile
        profile = ExecutorProfile.from_dict(dict(candidate.descriptor.capability_record))
        refusals = [EligibilityRefusal("capability_requirement_unsatisfied", item)
                    for item in unmet_step_requirements(self.request, profile)]
        if self.request.requirements.fresh_instance_required and (
                profile.fresh_instance_per_step != "supported"
                or not proves_fresh_instance(candidate.qualification, self.as_of)):
            refusals.append(EligibilityRefusal("engine_unqualified", "a fresh instance for each step is not proven"))
        return tuple(refusals)

    def to_dict(self) -> dict:
        return {"record_type": "step_requirement_screen/v1", "request_digest": self.request.digest}


def self_test():
    """Run the step execution checks."""
    from .engines_checks import self_test as run_engine_checks
    return run_engine_checks()
