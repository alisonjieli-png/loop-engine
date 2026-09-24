"""Offline checks for the engine declaration and host configuration records.

Each check states its known-wrong case and passes only when that case is
refused before any effect; each removed-guard control deletes one guard and
passes only when its named check would then fail. Fixture engines are
records, never adapters: nothing here imports, probes or starts an engine,
calls a model or opens a network connection.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from . import host_records
from . import records
from ..configuration_capabilities import ConfigurationFact, digest
from ..configuration_preferences import MetaPreferencePolicy
from .host_records import (
    BoundEngine, EngineBindingsReport, EngineInstallation, EngineSlotConfiguration, FamilyPolicyInForce,
    FileReference, QualificationSource, ServiceHostEngines, admit_engine_qualification)
from .records import (
    DESCRIPTOR_OBSERVATION_FIELDS, EngineCostBasis, EngineDescriptor, EngineLocality, EngineQualification,
    EngineRecordError, EngineRetirement, EvidenceReference, QualificationScope)
from .selection_records import DECLARED_ORDER_ENGINE_REF, EngineSelectionPolicy

NOW = datetime(2026, 9, 22, 12, tzinfo=timezone.utc)
ISSUED, EXPIRES = "2026-09-22T00:00:00Z", "2026-10-22T00:00:00Z"
SOURCE = "offline-engine-record-fixture@1.0.0"


def fact(state, expires_at=EXPIRES):
    return ConfigurationFact(state, SOURCE, digest("fixture fact:" + state), expires_at)


def descriptor(**changes) -> EngineDescriptor:
    base = EngineDescriptor(
        slot_id="step_executor", engine_id="opencode", engine_version="1.2.3",
        engine_kind="agent_protocol_harness",
        implementation_ref="loop_engine.core.fixture_engines.AgentProtocolFixture",
        implementation_digest=digest("fixture implementation"),
        native_record_type="harness_execution_capabilities/v2", native_record_digest=digest("native"),
        capability_record={"record_type": "executor_profile/v1", "fresh_instance_per_step": "proven"},
        supported_edge_contracts=("step_run_request/v1",), supported_modes=("hybrid", "non_deterministic"),
        effects=("reads_fs", "writes_fs", "spawns_process"), isolation="os_sandbox",
        locality=EngineLocality("core.facets.LOCALITY", "local_machine"), data_recipients=(),
        enforced_limits=("model_calls", "wall_time"), cost_class="metered",
        cost_basis=EngineCostBasis("provider_reported", None, None, None), licence="MIT",
        source_upstream="upstream-fixture", source_revision="0123abcd",
        availability=fact("available"), qualification=fact("qualified"), lifecycle="active",
        implementation_location="main", checks=("adapter_completion_does_not_claim_task_acceptance",))
    return replace(base, **changes)


def installation(**changes) -> EngineInstallation:
    base = EngineInstallation("opencode", "opencode", "agent_protocol_harness", True,
                              {"placement": "fresh_process"}, None, None)
    return replace(base, **changes)


def qualification(for_descriptor=None, for_installation=None, **changes) -> EngineQualification:
    engine, installed = for_descriptor or descriptor(), for_installation or installation()
    base = EngineQualification(
        "step_executor", engine.engine_ref, engine.content_digest, installed.installation_digest,
        QualificationScope("step_run_request/v1", "text_response", ("fixture.answer/v1",)), "local_contract",
        "step_finished", (EvidenceReference("artifacts/fixture/qualification-evidence.json", digest("e")),),
        "independent-reviewer@fixture", "approved", ISSUED, EXPIRES)
    return replace(base, **changes)


def retirement(**changes) -> EngineRetirement:
    base = EngineRetirement("step_executor", "opencode.raw_host", None, "archived",
                            "the raw host adapter is quarantined", "opencode",
                            "docs/architecture/fixture-decision.md", digest("retirement decision"))
    return replace(base, **changes)


def policy(**changes) -> EngineSelectionPolicy:
    base = EngineSelectionPolicy(
        "step_executor", "1.0.0", "default", ("opencode",), ("goose",), False, ("engine_unavailable",),
        MetaPreferencePolicy((DECLARED_ORDER_ENGINE_REF,)), None,
        {"loop": ("pin", "exclude", "prefer"), "harness": ("prefer",)}, None, (), False)
    return replace(base, **changes)


def goose_installation(**changes) -> EngineInstallation:
    return installation(installation_id="goose", engine_id="goose", **changes)


def slot_configuration(**changes) -> EngineSlotConfiguration:
    base = EngineSlotConfiguration("step_executor", "1.0.0", (installation(), goose_installation()),
                                   {"default": policy()}, "declared", digest("host engines block"))
    return replace(base, **changes)


def service_host_engines() -> ServiceHostEngines:
    return ServiceHostEngines({"step_executor": slot_configuration()})


def bindings_report() -> EngineBindingsReport:
    return EngineBindingsReport(
        digest("host configuration"),
        {"record_store": BoundEngine(digest("store decision"), "local.sqlite", "local.sqlite@1.0.0")},
        {"payment_provider": "not_declared"},
        FamilyPolicyInForce("service_host_family_policy/v1", digest("family policy"),
                            "the host file declares no family policy, so the harness family alone is served"))


def refused(action, code=None) -> bool:
    """True when the action is refused by an engine record rule (with the code, if named)."""
    try:
        action()
    except EngineRecordError as exc:
        return code is None or exc.code == code
    except Exception:
        return False
    return False


def accepted(action) -> bool:
    try:
        action()
    except Exception:
        return False
    return True


@contextmanager
def without(module, name, replacement=None):
    """Remove one guard for a removed-guard control, or put its known-wrong shape in its place."""
    with patch.object(module, name, replacement or (lambda *args, **kwargs: None)):
        yield


# The known-wrong shape of each digest or expiry rule, used by its control.

def narrow_descriptor_identity(record):
    """An identity that leaves out every declared field but the engine reference."""
    return {"engine_ref": record["engine_ref"]}


def switch_in_installation_identity(item):
    """An identity that includes the enabled switch, so switching on voids a qualification."""
    return {"installation_id": item.installation_id, "enabled": item.enabled}


def no_expiry(qualification):
    """A fact read from a qualification that never expires."""
    return ""


# Scenarios: each returns True only when its known-wrong case is refused.

def descriptor_digest_moves_with_every_declared_field() -> bool:
    """Known wrong: isolation changed from os_sandbox to none with the digest unchanged."""
    base = descriptor()
    changes = {
        "slot_id": "workspace_backend", "engine_id": "goose", "engine_version": "1.2.4",
        "engine_kind": "native_protocol_harness", "implementation_ref": "loop_engine.core.fixture_engines.Other",
        "implementation_digest": digest("other"), "native_record_type": "harness_execution_capabilities/v3",
        "native_record_digest": digest("other native"), "capability_record": {"record_type": "executor_profile/v1"},
        "supported_edge_contracts": ("step_run_request/v2",), "supported_modes": ("hybrid",),
        "effects": ("reads_fs",), "isolation": "none",
        "locality": EngineLocality("core.facets.LOCALITY", "api_calling"),
        "data_recipients": ("https://models.example.test",), "enforced_limits": ("model_calls",),
        "cost_class": "cheap", "cost_basis": EngineCostBasis(records.UNKNOWN, None, None, None),
        "licence": "Apache-2.0", "source_upstream": "another-upstream", "source_revision": "89abcdef",
        "checks": ()}
    observations = {"availability": fact("unavailable"), "qualification": fact("unqualified"),
                    "lifecycle": "deprecated", "implementation_location": "checkpoint@a3bd0f1"}
    declared = set(records.DESCRIPTOR_FIELDS) - {"engine_ref", "capability_record_digest", "source"} \
        - set(DESCRIPTOR_OBSERVATION_FIELDS)
    covered = set(changes) - {"source_upstream", "source_revision"}
    moved = all(replace(base, **{name: value}).content_digest != base.content_digest
                for name, value in changes.items())
    kept = all(replace(base, **{name: value}).content_digest == base.content_digest
               for name, value in observations.items())
    return moved and kept and covered == declared and set(observations) == set(DESCRIPTOR_OBSERVATION_FIELDS)


def qualification_is_bound_to_its_installation() -> bool:
    """Known wrong: a qualification for one installation accepted for another."""
    engine, first = descriptor(), installation()
    other = installation(settings={"placement": "long_lived_session"})
    issued = qualification(engine, first)
    bound = issued.fact_for(engine, first.installation_digest, source_ref="fixture/qualification.json")
    return (bound.current_state(NOW) == "qualified"
            and refused(lambda: issued.fact_for(engine, other.installation_digest, source_ref="fixture/q.json"),
                        "qualification_scope_mismatch")
            and refused(lambda: issued.fact_for(descriptor(engine_version="1.2.4"), first.installation_digest,
                                                source_ref="fixture/q.json"), "qualification_scope_mismatch"))


def expired_qualification_reads_unknown() -> bool:
    """Known wrong: a fact past its expiry still read as qualified."""
    engine, installed = descriptor(), installation()
    read = qualification(engine, installed).fact_for(engine, installed.installation_digest,
                                                     source_ref="fixture/qualification.json")
    after = datetime(2026, 10, 22, tzinfo=timezone.utc) + timedelta(seconds=1)
    return read.current_state(NOW) == "qualified" and read.current_state(after) == "unknown"


def one_qualification_source_is_kept() -> bool:
    """Known wrong: an engine_qualification/v1 written for an installation that
    already has a harness_project_qualification/v1."""
    project = QualificationSource(records.HARNESS_PROJECT_QUALIFICATION_RECORD_TYPE,
                                  "embodiments/codex/qualification.json", digest("project qualification"))
    with_project = installation(qualification=project)
    renewal = installation(qualification=QualificationSource(
        records.QUALIFICATION_RECORD_TYPE, "artifacts/fixture/engine-qualification.json", digest("earlier")))
    return (refused(lambda: admit_engine_qualification(
                with_project, qualification(for_installation=with_project)), "qualification_source_exists")
            and accepted(lambda: admit_engine_qualification(installation(), qualification()))
            and accepted(lambda: admit_engine_qualification(renewal, qualification(for_installation=renewal))))


#: Settings that carry a credential, each in a spelling a customer's own harness
#: configuration uses: a key name in snake, camel, hyphenated or upper case, a
#: header line, a command option, a bearer value, a key in an address's query,
#: and user information in an address, at the start of the text or after a space.
CREDENTIAL_SETTINGS = (
    {"endpoint": "local", "api_key": "placeholder-value"},
    {"headers": {"authorization": "placeholder-value"}},
    {"endpoints": ["http://user:placeholder@127.0.0.1:11434"]},
    {"baseURL": "http://127.0.0.1:11434/v1", "apiKey": "placeholder-value"},
    {"options": {"APIKey": "placeholder-value"}},
    {"privateKey": "placeholder-value"},
    {"env": {"OLLAMA_API_KEY": "placeholder-value"}},
    {"headers": ["Authorization: Bearer placeholder-value"]},
    {"args": ["--api-key", "placeholder-value"]},
    {"args": ["--token=placeholder-value"]},
    {"authorization_value": "Bearer placeholder-value"},
    {"endpoint": "https://models.example.test/v1?key=placeholder-value"},
    {"endpoint": " http://user:placeholder@127.0.0.1:11434"},
)
#: Settings that only look near a credential: token budgets, a tokenizer, a
#: local address with a port, a header line and an option that name no credential.
PLAIN_SETTINGS = (
    {"endpoint": "http://127.0.0.1:11434", "max_output_tokens": 4096},
    {"baseURL": "http://127.0.0.1:11434/v1", "maxOutputTokens": 4096, "tokenizer": "fixture-tokenizer"},
    {"headers": ["Accept: application/json"], "args": ["--max-tokens=4096", "-y"]},
)


def settings_never_hold_a_credential() -> bool:
    """Known wrong: an installation whose settings carry a provider key, under a
    key name in any of its spellings, in a header line, a command option, a bearer
    value, an address's query or the user information of an address, and a data
    recipient origin that embeds a credential."""
    local = "http://127.0.0.1:11434"
    return (all(refused(lambda s=settings: installation(settings=s), "credential_in_settings")
                for settings in CREDENTIAL_SETTINGS)
            and refused(lambda: descriptor(data_recipients=("https://placeholder@models.example.test",)))
            and all(accepted(lambda s=settings: installation(settings=s)) for settings in PLAIN_SETTINGS)
            and accepted(lambda: descriptor(data_recipients=(local,))))


def installation_digest_binds_settings_not_the_switch() -> bool:
    """Known wrong: switching an engine on voids its qualification, or a
    settings or declaration change keeps the installation digest."""
    base = installation(enabled=False)
    declared = FileReference("/data/embodiments/opencode/harness.json", digest("declaration"), absolute=True)
    return (installation(enabled=True).installation_digest == base.installation_digest
            and installation(qualification=QualificationSource(records.QUALIFICATION_RECORD_TYPE,
                "artifacts/fixture/q.json", digest("q"))).installation_digest == base.installation_digest
            and installation(settings={"placement": "pooled_sessions"}).installation_digest
            != base.installation_digest
            and installation(declaration=declared).installation_digest != base.installation_digest
            and goose_installation().installation_digest != base.installation_digest)


def localities_never_compare_across_vocabularies() -> bool:
    """Known wrong: core.facets local_machine compared with a model route's local."""
    machine = EngineLocality("core.facets.LOCALITY", "local_machine")
    route = EngineLocality("core.model_routes.LOCALITIES", "local")
    return (refused(lambda: machine.same_as(route), "locality_vocabularies_differ")
            and machine.same_as(EngineLocality("core.facets.LOCALITY", "local_machine")))


def a_served_host_selects_only_qualified_engines() -> bool:
    """Known wrong: the service host's engines block with a policy that allows unqualified engines,
    or whose ranking engines may be unqualified."""
    trial = slot_configuration(selection={"default": policy(allow_unqualified=True)})
    ranked = slot_configuration(selection={"default": policy(
        ranking=MetaPreferencePolicy(("evidence-ranker", DECLARED_ORDER_ENGINE_REF), (), (), True))})
    return (refused(lambda: ServiceHostEngines({"step_executor": trial}), "unqualified_on_a_served_path")
            and refused(lambda: ServiceHostEngines({"step_executor": ranked}), "unqualified_on_a_served_path")
            and accepted(lambda: trial) and accepted(lambda: ranked) and accepted(service_host_engines))


def a_qualification_is_independent_evidenced_and_bounded_in_time() -> bool:
    """Known wrong: an engine that qualifies itself; a qualification that expires when
    or before it is issued, is written without a timezone, cites no evidence or one
    piece twice, or names an engine without its version; a qualification admitted
    for an installation it does not bind."""
    other = installation(settings={"placement": "long_lived_session"})
    cited = EvidenceReference("artifacts/fixture/qualification-evidence.json", digest("e"))
    return (refused(lambda: qualification(reviewer="opencode@1.2.3"), "self_qualification")
            and refused(lambda: qualification(reviewer="opencode"), "self_qualification")
            and refused(lambda: qualification(expires_at=ISSUED), "invalid_time")
            and refused(lambda: qualification(issued_at=EXPIRES, expires_at=ISSUED), "invalid_time")
            and refused(lambda: qualification(issued_at="2026-09-22T00:00:00"), "invalid_time")
            and refused(lambda: qualification(evidence=()), "invalid_field")
            and refused(lambda: qualification(evidence=(cited, cited)), "invalid_field")
            and refused(lambda: qualification(engine_ref="opencode"), "invalid_engine_reference")
            and refused(lambda: admit_engine_qualification(other, qualification()), "qualification_scope_mismatch")
            and accepted(qualification))


def declarations_keep_each_field_in_its_own_vocabulary() -> bool:
    """Known wrong: the pure effect beside another effect; a provider-reported cost basis
    that names a price record; a model route locality under the facet vocabulary; an
    implementation location that is neither main nor a checkpoint revision; an engine
    retired in favour of itself."""
    priced = ("pricing/fixture-prices.json", digest("prices"), "2026-09-20")
    return (refused(lambda: descriptor(effects=("pure", "network")), "invalid_field")
            and refused(lambda: EngineCostBasis("provider_reported", *priced), "invalid_cost_basis")
            and refused(lambda: EngineLocality("core.facets.LOCALITY", "cloud"), "invalid_vocabulary")
            and refused(lambda: descriptor(implementation_location="feature-branch"), "invalid_field")
            and refused(lambda: retirement(engine_id="opencode", replacement="opencode@2.0.0"), "invalid_field")
            and refused(lambda: retirement(engine_id="opencode", engine_version="1.0.0",
                                           replacement="opencode@1.0.0"), "invalid_field")
            and accepted(lambda: retirement(engine_id="opencode", engine_version="1.0.0",
                                            replacement="opencode@2.0.0"))
            and accepted(lambda: descriptor(effects=("pure",), cost_basis=EngineCostBasis("price_record", *priced))))


def a_slot_configuration_keeps_one_slot_and_names_each_installation_once() -> bool:
    """Known wrong: a policy for another slot or another major version, or filed under
    another scope key; two installations with one identifier; an engine installed once
    under another name, or under two kinds; an engines block that files a slot under
    another name; a file reference that climbs out of its folder; a host declaration
    named by a relative path."""
    twice = (installation(installation_id="opencode.a"), installation(installation_id="opencode.b"))
    two_kinds = (twice[0], installation(installation_id="opencode.b", engine_kind="native_protocol_harness"))

    def only(first):
        return {"default": policy(initial=(first,), fallbacks=(), no_fallback=True, fallback_on=())}
    return (refused(lambda: slot_configuration(selection={"default": policy(slot_version="2.0.0")}),
                    "slot_version_mismatch")
            and refused(lambda: slot_configuration(selection={"default": policy(slot_id="workspace_backend")}),
                        "slot_version_mismatch")
            and refused(lambda: slot_configuration(selection={"offline": policy()}), "invalid_field")
            and refused(lambda: slot_configuration(installed=(installation(), installation(), goose_installation())),
                        "repeated_value")
            and refused(lambda: slot_configuration(installed=(installation(installation_id="opencode.main"),),
                                                   selection=only("opencode.main")), "invalid_installation_id")
            and refused(lambda: slot_configuration(installed=two_kinds, selection=only("opencode.a")), "invalid_field")
            and refused(lambda: ServiceHostEngines({"workspace_backend": slot_configuration()}), "invalid_field")
            and refused(lambda: FileReference("artifacts/../../outside.json", digest("q")), "invalid_path")
            and refused(lambda: FileReference("embodiments/opencode/harness.json", digest("d"), absolute=True),
                        "invalid_path")
            and accepted(lambda: slot_configuration(installed=twice, selection=only("opencode.a")))
            and accepted(lambda: slot_configuration(selection={"default": policy(slot_version="1.4.0")})))


def run_checks() -> dict:
    tests = []

    def check(name, passed):
        tests.append({"name": name, "passed": bool(passed)})

    scenarios = (
        ("descriptor_digest_moves_when_any_field_moves", descriptor_digest_moves_with_every_declared_field,
         "removed_descriptor_identity_rule_is_detected", records, "_descriptor_identity",
         narrow_descriptor_identity),
        ("qualification_binds_the_installation_digest", qualification_is_bound_to_its_installation,
         "removed_qualification_binding_is_detected", records, "_refuse_unbound_qualification", None),
        ("expired_qualification_becomes_unknown_and_ineligible", expired_qualification_reads_unknown,
         "removed_qualification_expiry_is_detected", records, "_fact_expiry", no_expiry),
        ("one_qualification_source_per_installation", one_qualification_source_is_kept,
         "removed_single_qualification_source_rule_is_detected", host_records,
         "_refuse_second_qualification_source", None),
        ("installation_settings_never_hold_a_credential", settings_never_hold_a_credential,
         "removed_credential_settings_rule_is_detected", host_records, "_refuse_credential_settings", None),
        ("installation_digest_binds_the_settings_but_not_the_enabled_switch",
         installation_digest_binds_settings_not_the_switch,
         "removed_installation_identity_rule_is_detected", host_records, "_installation_identity",
         switch_in_installation_identity),
        ("localities_from_two_vocabularies_are_never_compared", localities_never_compare_across_vocabularies,
         "removed_locality_vocabulary_rule_is_detected", records, "_refuse_cross_vocabulary", None),
        ("a_served_host_never_allows_an_unqualified_engine", a_served_host_selects_only_qualified_engines,
         "removed_served_path_qualification_rule_is_detected", host_records,
         "_refuse_unqualified_on_a_served_path", None),
    )
    for name, scenario, control, module, guard, replacement in scenarios:
        check(name, _observe(scenario))
        with without(module, guard, replacement):
            check(control, _observe(scenario) is False)
    check("the_engines_block_is_a_declaration_and_a_slot_is_bound_or_unbound_once", _host_block_rules_hold())
    # Known wrong: a lifecycle stage selection reads that the component ontology does not define.
    check("every_lifecycle_stage_selection_reads_is_in_the_component_vocabulary",
          set(records.SELECTION_LIFECYCLES) <= set(records.lifecycles())
          and len(set(records.SELECTION_LIFECYCLES)) == len(records.SELECTION_LIFECYCLES))
    # Rules written inline in the records: each has no guard function to remove
    # inside the test, so source mutants confirm that removing it fails the check.
    for name, scenario in (
            ("a_qualification_is_independent_evidenced_and_bounded_in_time",
             a_qualification_is_independent_evidenced_and_bounded_in_time),
            ("declarations_keep_each_field_in_its_own_vocabulary", declarations_keep_each_field_in_its_own_vocabulary),
            ("a_slot_configuration_keeps_one_slot_and_names_each_installation_once",
             a_slot_configuration_keeps_one_slot_and_names_each_installation_once)):
        check(name, _observe(scenario))
    return {"tests": tests, "passed": sum(t["passed"] for t in tests), "total": len(tests),
            "all_passed": all(t["passed"] for t in tests)}


def _observe(scenario) -> bool:
    try:
        return bool(scenario())
    except Exception:
        return False


def _host_block_rules_hold() -> bool:
    """Known wrong: a projected configuration inside the host file's engines block;
    one slot reported both bound and unbound."""
    projected = replace(slot_configuration(), source="projected:models.tiers")
    both = {"record_store": BoundEngine(digest("d"), "local.sqlite", "local.sqlite@1.0.0")}
    return (refused(lambda: ServiceHostEngines({"step_executor": projected}))
            and refused(lambda: EngineBindingsReport(digest("c"), both, {"record_store": "no_eligible_engine"},
                                                     bindings_report().family_policy))
            and accepted(service_host_engines) and accepted(bindings_report))


def self_test() -> dict:
    return run_checks()
