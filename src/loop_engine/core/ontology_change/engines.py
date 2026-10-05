"""Factory table of the ontology_change_planning slot: declarations, declared order, factories, descriptors.

```text
engines (the slot's one factory table; it defines no engine class)
├── DECLARED_ENGINES   ontology_change_engine_declaration/v1 of each engine
│   ├── baltor_native_rules   rule_closure_engine, in process, pure, every profile, blank nodes
│   └── open_ontologies_cli   sandboxed_binary_adapter, Open Ontologies v2.0.1 pinned by commit and
│                             asset digest, MIT, OS sandbox, no blank nodes
├── DECLARED_ORDER     the native engine first, the adapter as the declared fallback
├── ENGINE_FACTORIES   engine id -> a function that builds the engine with its installation settings
├── describe_engine    the shared engine_descriptor/v1, projected from a declaration; its identity
│                      binds the source bytes of the engine and of the edge it reads
├── unmet_requirements what a planning input asks that a declaration does not offer
└── default_installations and default_policy   engine_installation/v1 and engine_selection_policy/v1
```

A host switches engines by its installations and policy, never by editing a
caller. Building an engine runs nothing; the adapter checks its binary only
when asked for availability or a plan.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import MappingProxyType

from ..configuration_capabilities import ConfigurationFact, digest
from ..configuration_preferences import MetaPreferencePolicy
from ..engines.host_records import EngineInstallation
from ..engines.records import EngineCostBasis, EngineDescriptor, EngineLocality
from ..engines.selection_records import DECLARED_ORDER_ENGINE_REF, EngineSelectionPolicy
from .contract import (
    DECLARATION_RECORD_TYPE, FALLBACK_FAILURE_KINDS, PLAN_RECORD_TYPE, PROFILES, REQUEST_RECORD_TYPE, SLOT_ID,
    SLOT_VERSION, EngineDeclaration, PlanningInput)
from .open_ontologies_engine import (
    ASSET, BINARY_SHA256, CHECKER_ASSET, CHECKER_SHA256, COMMIT, RELEASE, REPOSITORY)

NATIVE_ENGINE_ID, ADAPTER_ENGINE_ID = "baltor_native_rules", "open_ontologies_cli"
ENGINE_KINDS = ("rule_closure_engine", "sandboxed_binary_adapter")
NATIVE_DECLARATION = EngineDeclaration(
    NATIVE_ENGINE_ID, "1.0.0", ENGINE_KINDS[0], "loop_engine.core.ontology_change.native_engine.NativeRuleEngine",
    PROFILES, True, ("pure",), "none", "MIT", "github.com/alisonjieli-png/loop-engine", "own_code")
ADAPTER_DECLARATION = EngineDeclaration(
    ADAPTER_ENGINE_ID, RELEASE.lstrip("v"), ENGINE_KINDS[1],
    "loop_engine.core.ontology_change.open_ontologies_engine.OpenOntologiesEngine", PROFILES, False,
    ("reads_fs", "writes_fs", "spawns_process"), "os_sandbox", "MIT", f"github.com/{REPOSITORY}", COMMIT,
    MappingProxyType({"release": RELEASE, "asset": ASSET, "sha256": BINARY_SHA256, "checker_asset": CHECKER_ASSET,
                      "checker_sha256": CHECKER_SHA256, "digest_source": "GitHub release asset digest"}))
DECLARED_ENGINES = (NATIVE_DECLARATION, ADAPTER_DECLARATION)
DECLARED_ORDER = (NATIVE_ENGINE_ID, ADAPTER_ENGINE_ID)
_DECLARATIONS = MappingProxyType({item.engine_id: item for item in DECLARED_ENGINES})
#: The source files each engine's behaviour depends on; their bytes are its implementation digest.
_SOURCES = MappingProxyType({
    NATIVE_ENGINE_ID: ("native_engine.py", "contract.py", "rdf_terms.py"),
    ADAPTER_ENGINE_ID: ("open_ontologies_engine.py", "contract.py", "rdf_terms.py"),
})
_CHECKS = ("a_stale_base_digest_is_refused_before_any_engine_runs",
           "every_listed_consequence_carries_a_trace_the_independent_checker_accepts",
           "a_forged_derivation_trace_is_refused")


def _native(settings):
    from .native_engine import NativeRuleEngine
    return NativeRuleEngine(NATIVE_DECLARATION, settings)


def _adapter(settings):
    from .open_ontologies_engine import OpenOntologiesEngine
    return OpenOntologiesEngine(ADAPTER_DECLARATION, settings)


ENGINE_FACTORIES = MappingProxyType({NATIVE_ENGINE_ID: _native, ADAPTER_ENGINE_ID: _adapter})


def declaration(engine_id: str) -> EngineDeclaration:
    if engine_id not in _DECLARATIONS:
        raise KeyError(f"no engine {engine_id!r} in the ontology_change_planning factory table")
    return _DECLARATIONS[engine_id]


def create_engine(engine_id: str, settings=None):
    """Build one engine with its installation settings; nothing runs."""
    declaration(engine_id)
    return ENGINE_FACTORIES[engine_id](dict(settings or {}))


def implementation_digest(engine_id: str) -> str:
    """SHA-256 over the source bytes the engine runs, and for the adapter the pinned artifact digest."""
    folder, hasher = Path(__file__).resolve().parent, hashlib.sha256()
    for name in _SOURCES[engine_id]:
        hasher.update(name.encode() + b"\0" + (folder / name).read_bytes() + b"\0")
    pinned = declaration(engine_id).pinned_artifact
    if pinned:
        hasher.update(pinned["sha256"].encode())
    return hasher.hexdigest()


def _fact(state: str, basis: str, now: datetime) -> ConfigurationFact:
    return ConfigurationFact(state, f"core.ontology_change.engines:{basis}", digest(f"{basis}:{state}"),
                             (now + timedelta(hours=1)).isoformat())


def describe_engine(engine_id: str, settings=None, *, now: "datetime | None" = None) -> EngineDescriptor:
    """The shared engine_descriptor/v1 of one engine, its availability observed now."""
    item, now = declaration(engine_id), now or datetime.now(timezone.utc)
    available, _reason = create_engine(engine_id, settings).availability()
    native_record = item.to_dict()
    return EngineDescriptor(
        slot_id=SLOT_ID, engine_id=item.engine_id, engine_version=item.engine_version, engine_kind=item.engine_kind,
        implementation_ref=item.implementation_ref, implementation_digest=implementation_digest(engine_id),
        native_record_type=DECLARATION_RECORD_TYPE, native_record_digest=digest(native_record),
        capability_record={"record_type": "ontology_change_capabilities/v1", "profiles": list(item.profiles),
                           "blank_nodes": item.blank_nodes},
        supported_edge_contracts=(REQUEST_RECORD_TYPE, PLAN_RECORD_TYPE), supported_modes=("deterministic",),
        effects=item.effects, isolation=item.isolation,
        locality=EngineLocality("core.facets.LOCALITY", "local_machine"),
        data_recipients=(), enforced_limits=("wall_time", "maximum_output") if item.pinned_artifact else (),
        cost_class="free", cost_basis=EngineCostBasis("unknown", None, None, None), licence=item.licence,
        source_upstream=item.source_upstream, source_revision=item.source_revision,
        availability=_fact("available" if available else "unavailable", "availability", now),
        qualification=ConfigurationFact(), lifecycle="candidate", implementation_location="main", checks=_CHECKS)


def unmet_requirements(item: EngineDeclaration, planning_input: PlanningInput) -> tuple:
    """What the planning input needs that the declaration does not offer, each named."""
    unmet = []
    if planning_input.profile not in item.profiles:
        unmet.append(f"profile {planning_input.profile}")
    if planning_input.has_blank_nodes and not item.blank_nodes:
        unmet.append("blank nodes in the base or the proposal")
    return tuple(unmet)


def default_installations(binary_path: "str | None" = None, *, work_root: "str | None" = None) -> tuple:
    """Both engines installed and enabled; the adapter is available only when its binary path is set."""
    adapter_settings = {key: value for key, value in (("binary_path", binary_path), ("work_root", work_root))
                        if value}
    return (EngineInstallation(NATIVE_ENGINE_ID, NATIVE_ENGINE_ID, ENGINE_KINDS[0], True, {}, None, None),
            EngineInstallation(ADAPTER_ENGINE_ID, ADAPTER_ENGINE_ID, ENGINE_KINDS[1], True, adapter_settings,
                               None, None))


def default_policy(initial=(NATIVE_ENGINE_ID,), fallbacks=(ADAPTER_ENGINE_ID,)) -> EngineSelectionPolicy:
    """The declared order as engine_selection_policy/v1; no engine is independently qualified yet."""
    return EngineSelectionPolicy(
        SLOT_ID, SLOT_VERSION, "default", tuple(initial), tuple(fallbacks), not fallbacks,
        FALLBACK_FAILURE_KINDS + ("output_validation_failed",) if fallbacks else (),
        MetaPreferencePolicy((DECLARED_ORDER_ENGINE_REF,)), None,
        {"loop": ("pin", "exclude", "prefer"), "harness": ("prefer",)}, None, (), True)
