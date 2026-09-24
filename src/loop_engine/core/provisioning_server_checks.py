"""Offline public-path checks for tenant disclosure and exact metering acknowledgment.

Exercises host-bound access, source qualification, body integrity, and unknown
commit refusal. Local fixtures do not qualify durable or hosted operation.
"""
from __future__ import annotations

import concurrent.futures
from dataclasses import FrozenInstanceError, replace
from unittest.mock import patch

from . import provisioning_server as serving
from .harness_intelligence import (HarnessIntelligenceCatalogue, HarnessIntelligenceDraft,
                                   item_from_body)
from .intelligence_tagging import TagSet
from .service_api import key_digest


def fixture():
    """Trusted local metadata fixture; no source promotion or external body reader."""
    catalogue = HarnessIntelligenceCatalogue()
    bodies = {identity: f"Reviewed local fixture: {identity}\n" for identity in
              ("skill.reviewed", "skill.private", "skill.candidate", "skill.restricted",
               "tool.files", "skill.other_tenant", "skill.metadata")}
    for identity, body in bodies.items():
        tags = TagSet({})
        if identity == "skill.candidate":
            tags = TagSet({"lifecycle": ["qualified"]})  # tags cannot approve it
        if identity == "skill.restricted":
            tags = TagSet({"lifecycle": ["candidate"], "authentication": ["operator"],
                           "data_sensitivity": ["regulated"]})
        catalogue.register(item_from_body(HarnessIntelligenceDraft(
            identity, "tool" if identity == "tool.files" else "skill", identity,
            "context_intelligence", "context:" + identity, "MIT",
            declared_effects=("reads_fs",) if identity == "tool.files" else (), tags=tags), body))
    tenants = tuple(serving.ProvisioningTenant(name, key_digest(name + "-key"), tier)
                    for name, tier in (("free", "metadata"), ("paid", "bodies"),
                                       ("other", "bodies")))
    decisions = {}
    for item in catalogue.items.values():
        binding = serving.ProvisioningItemBinding.from_item(item)
        refused = item.identity == "skill.candidate"
        decisions[binding.identity] = serving.ProvisioningQualification(
            binding, "refused" if refused else "approved",
            "host_attested", "fixture:review:" + item.identity, "" if refused else serving.VERIFIED_TIER)
    grants = []
    for tenant in ("free", "paid"):
        for identity in ("skill.reviewed", "tool.files", "skill.metadata"):
            grants.append(serving.ProvisioningGrant(
                tenant, decisions[identity].binding, identity != "skill.metadata"))
    grants.extend((serving.ProvisioningGrant("paid", decisions["skill.candidate"].binding, True),
                   serving.ProvisioningGrant("other", decisions["skill.other_tenant"].binding, True)))
    resolver = serving.ProvisioningQualificationResolver(
        "fixture:local-review", lambda binding: decisions.get(binding.identity))
    policy = serving.ProvisioningAccessPolicy(grants, resolver)
    reads = []

    def read(item):
        reads.append(item.identity)
        return bodies[item.identity]

    meter = serving.RecordedMeter()
    server = serving.ProvisioningServer(catalogue, tenants, read, meter, access_policy=policy)
    return server, decisions, reads, meter, bodies


def ask(server, operation, identity="skill.reviewed", key="paid-key", **kwargs):
    return server.handle(serving.ProvisioningRequest(
        operation, key, identity, request_id=kwargs.pop("request_id", "fixture:read"), **kwargs))


def refusal(action, code=None):
    try:
        action()
    except serving.ProvisioningError as error:
        return code is None or error.code == code
    return False


def self_test() -> dict:
    tests = []

    def check(name, test):
        try:
            passed = bool(test())
            detail = ""
        except Exception as error:
            passed, detail = False, type(error).__name__ + ": " + str(error)
        tests.append({"test": name, "passed": passed, "detail": detail})

    def metadata():
        server, _, reads, meter, _ = fixture()
        discovery = ask(server, "discover", key="free-key", authority_effects=("reads_fs",))
        listed = ask(server, "list", key="free-key", authority_effects=("reads_fs",))
        manifest = ask(server, "manifest", key="free-key")
        return (discovery["items_held"] == 3 and set(discovery["kinds"]) == {"skill", "tool"}
                and not discovery["bodies_available"] and len(listed["items"]) == 3
                and all("body" not in row for row in listed["items"])
                and manifest["qualification_basis"] == "host_attested"
                and manifest["metered"] is False and not reads and not meter.rows)

    check("metadata_is_scoped_effect_free_and_honest_about_host_attestation", metadata)

    def paid():
        server, _, reads, meter, bodies = fixture()
        result = ask(server, "read")
        ack = result["metering_acknowledgment"]
        return (result["body"] == bodies["skill.reviewed"] and result["metered"] is True
                and result["digest"] == server.catalogue.items["skill.reviewed"].digest
                and ack["committed"] is True and ack["durability"] == "volatile"
                and set(ack) == {"request", "committed", "acknowledgment_ref", "durability", "record_type"}
                and ack["acknowledgment_ref"] == meter.rows[0]["acknowledgment_ref"]
                and ack["request"]["binding"]["identity"] == "skill.reviewed"
                and reads == ["skill.reviewed"] and meter.total("paid") == 1)

    check("approved_paid_read_returns_exact_committed_acknowledgment", paid)

    for identity in ("skill.private", "skill.candidate", "skill.restricted", "skill.other_tenant"):
        def hidden(identity=identity):
            server, _, reads, meter, _ = fixture()
            listed = ask(server, "list", authority_effects=("reads_fs",))
            return (identity not in str(listed)
                    and refusal(lambda: ask(server, "manifest", identity), "item_unavailable")
                    and refusal(lambda: ask(server, "read", identity), "item_unavailable")
                    and not reads and not meter.rows)
        check("unauthorized_item_is_hidden_on_all_surfaces_" + identity, hidden)

    def deny_default():
        server, _, reads, meter, _ = fixture()
        server.replace_access_policy(serving.ProvisioningAccessPolicy())
        return (ask(server, "discover")["items_held"] == 0
                and ask(server, "list")["items"] == []
                and ask(server, "list")["withheld"] == []
                and refusal(lambda: ask(server, "read"), "item_unavailable")
                and not reads and not meter.rows)

    check("missing_host_policy_denies_by_default_and_revokes_previous_grants", deny_default)

    def scope_no_oracle():
        server, _, _, _, _ = fixture()
        errors = []
        for identity in ("skill.private", "absent"):
            try:
                ask(server, "manifest", identity)
            except serving.ProvisioningError as error:
                errors.append((error.code, str(error)))
        return len(errors) == 2 and errors[0] == errors[1]

    check("missing_and_ungranted_items_have_the_same_refusal", scope_no_oracle)

    def body_grants():
        server, _, reads, meter, _ = fixture()
        return (refusal(lambda: ask(server, "read", key="free-key"), "body_forbidden")
                and refusal(lambda: ask(server, "read", "skill.metadata"), "body_forbidden")
                and not reads and not meter.rows)

    check("entitlement_and_exact_body_grant_are_both_required", body_grants)

    def effects():
        server, _, reads, meter, _ = fixture()
        listed = ask(server, "list")
        withheld = {item["identity"]: item["reason"] for item in listed["withheld"]}
        denied = refusal(lambda: ask(server, "read", "tool.files"), "item_withheld")
        loaded = ask(server, "read", "tool.files", authority_effects=("reads_fs",))
        return (denied and "reads_fs" in withheld["tool.files"]
                and loaded["identity"] == "tool.files" and reads == ["tool.files"]
                and meter.total("paid") == 1)

    check("effect_filter_is_consistent_but_never_substitutes_for_a_tenant_grant", effects)

    def missing_resolver():
        server, _, reads, meter, _ = fixture()
        server.replace_access_policy(replace(server.access_policy, qualification_resolver=None))
        return ask(server, "list")["items"] == [] and not reads and not meter.rows

    check("grants_without_qualification_resolver_disclose_nothing", missing_resolver)

    for label, callback in (
            ("unknown", lambda decision: replace(decision, status="unknown", trust_tier="")),
            ("mismatched", lambda decision: replace(decision, binding=replace(
                decision.binding, source_ref="another-source"))),
            ("untyped", lambda decision: {"status": "approved"})):
        def unresolved(callback=callback):
            server, decisions, reads, meter, _ = fixture()
            decisions["skill.reviewed"] = callback(decisions["skill.reviewed"])
            return (refusal(lambda: ask(server, "manifest"), "item_unavailable")
                    and not reads and not meter.rows)
        check("qualification_" + label + "_is_not_disclosure_authority", unresolved)

    def resolver_outage():
        server, _, reads, meter, _ = fixture()
        def failing(_binding):
            raise RuntimeError("private host failure detail")
        server.replace_access_policy(replace(server.access_policy, qualification_resolver=
            serving.ProvisioningQualificationResolver("fixture:failing", failing)))
        return (ask(server, "list")["items"] == []
                and refusal(lambda: ask(server, "read"), "item_unavailable")
                and not reads and not meter.rows)

    check("qualification_failure_does_not_fall_back_to_host_approval", resolver_outage)

    def exact_host_review_not_labels():
        server, decisions, _, _, _ = fixture()
        grant = serving.ProvisioningGrant("paid", decisions["skill.restricted"].binding, True)
        server.replace_access_policy(replace(server.access_policy,
                                             grants=(*server.access_policy.grants, grant)))
        result = ask(server, "read", "skill.restricted")
        return result["identity"] == "skill.restricted" and result["qualification_basis"] == "host_attested"

    check("explicit_review_and_grant_not_classification_labels_authorize_local_items", exact_host_review_not_labels)

    for field_name, value in (("source_ref", "changed-source"), ("purpose", "changed-purpose"),
                              ("license_name", "another-license"), ("digest", "a" * 64)):
        def stale(field_name=field_name, value=value):
            server, _, reads, meter, _ = fixture()
            server.catalogue.items["skill.reviewed"] = replace(
                server.catalogue.items["skill.reviewed"], **{field_name: value})
            return (refusal(lambda: ask(server, "read"), "item_unavailable")
                    and "skill.reviewed" not in str(ask(server, "list"))
                    and not reads and not meter.rows)
        check("changed_" + field_name + "_invalidates_the_exact_grant", stale)

    def body_integrity():
        server, _, reads, meter, bodies = fixture()
        bodies["skill.reviewed"] = "changed"
        return (refusal(lambda: ask(server, "read"), "body_integrity_failed")
                and reads == ["skill.reviewed"] and not meter.rows)

    check("changed_body_is_refused_before_metering", body_integrity)

    def size_integrity():
        server, decisions, _, meter, _ = fixture()
        item = replace(server.catalogue.items["skill.reviewed"], size_bytes=99999)
        server.catalogue.items[item.identity] = item
        binding = serving.ProvisioningItemBinding.from_item(item)
        decisions[item.identity] = replace(decisions[item.identity], binding=binding)
        grants = tuple(replace(grant, binding=binding) if grant.binding.identity == item.identity
                       else grant for grant in server.access_policy.grants)
        server.replace_access_policy(replace(server.access_policy, grants=grants))
        return refusal(lambda: ask(server, "read"), "body_integrity_failed") and not meter.rows

    check("measured_body_size_must_match_the_approved_descriptor", size_integrity)

    def missing_meter():
        server, _, reads, _, _ = fixture()
        server = replace(server, meter=None)
        return (refusal(lambda: ask(server, "read"), "meter_unavailable") and not reads
                and ask(server, "discover")["bodies_available"] is False)

    check("required_missing_meter_refuses_before_body_read", missing_meter)

    def bodiless():
        server, _, reads, _, _ = fixture()
        server = replace(server, body_reader=None)
        return (ask(server, "manifest")["digest"] and ask(server, "discover")["bodies_available"] is False
                and refusal(lambda: ask(server, "read"), "body_reader_unavailable") and not reads)

    check("metadata_only_host_remains_usable_without_a_body_reader", bodiless)

    def explicit_unmetered():
        server, _, reads, meter, _ = fixture()
        grants = tuple(replace(grant, metering="unmetered") for grant in server.access_policy.grants)
        server = replace(server, meter=None, access_policy=replace(server.access_policy, grants=grants))
        result = ask(server, "read", request_id="")
        return (result["metered"] is False and result["metering_acknowledgment"] is None
                and reads == ["skill.reviewed"] and not meter.rows)

    check("explicit_host_unmetered_grant_is_supported_without_false_metering", explicit_unmetered)

    for label, callback in (
            ("none", lambda request: None),
            ("untyped", lambda request: {"committed": True}),
            ("refused", lambda request: serving.ProvisioningMeterAcknowledgment(request, False)),
            ("unknown", lambda request: serving.ProvisioningMeterAcknowledgment(request, None)),
            ("wrong_tenant", lambda request: serving.ProvisioningMeterAcknowledgment(
                replace(request, tenant_id="other"), True, "fixture:acknowledgment")),
            ("wrong_body", lambda request: serving.ProvisioningMeterAcknowledgment(
                replace(request, binding=replace(request.binding, body_digest="b" * 64)),
                True, "fixture:acknowledgment"))):
        def unacknowledged(callback=callback):
            server, _, _, _, _ = fixture()
            return refusal(lambda: ask(replace(server, meter=callback), "read"), "meter_commit_unknown")
        check("meter_" + label + "_does_not_return_a_successful_body", unacknowledged)

    def lost_ack():
        server, _, _, meter, _ = fixture()
        def lost(request):
            meter(request)
            raise RuntimeError("response lost after commit")
        failed = refusal(lambda: ask(replace(server, meter=lost), "read"), "meter_commit_unknown")
        recovered = ask(server, "read")
        return failed and recovered["metered"] is True and meter.total("paid") == 1

    check("unknown_commit_retries_the_same_effect_without_a_second_charge", lost_ack)

    def concurrent_acknowledgment():
        server, _, _, meter, _ = fixture()
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: ask(server, "read"), range(12)))
        acknowledgments = {row["metering_acknowledgment"]["acknowledgment_ref"] for row in results}
        return len(acknowledgments) == 1 and meter.total("paid") == 1 and len(meter.rows) == 1

    check("concurrent_exact_retries_have_one_reference_meter_charge", concurrent_acknowledgment)

    def reused_id():
        server, _, _, meter, _ = fixture()
        ask(server, "read")
        return (refusal(lambda: ask(server, "read", "tool.files", authority_effects=("reads_fs",)),
                        "meter_commit_unknown") and meter.total("paid") == 1)

    check("changed_effect_cannot_reuse_an_existing_charge_identity", reused_id)

    def direct_meter_conflict():
        server, _, _, meter, _ = fixture()
        binding = serving.ProvisioningItemBinding.from_item(server.catalogue.items["skill.reviewed"])
        request = serving.ProvisioningMeterRequest("paid", "fixture:exact", binding)
        meter(request)
        return (refusal(lambda: meter(replace(request, binding=replace(binding, body_digest="c" * 64))),
                        "meter_request_conflict") and meter.total("paid") == 1)

    check("reference_meter_itself_refuses_changed_effect_for_a_committed_identity", direct_meter_conflict)

    def revoked_midread():
        server, _, _, meter, bodies = fixture()
        def read(item):
            server.replace_access_policy(serving.ProvisioningAccessPolicy())
            return bodies[item.identity]
        server = replace(server, body_reader=read)
        return (refusal(lambda: ask(server, "read"), "item_unavailable") and not meter.rows)

    check("revocation_during_body_read_prevents_metering_and_disclosure", revoked_midread)

    def revoked_by_resolver():
        server, decisions, reads, meter, _ = fixture()
        def resolve(binding):
            server.replace_access_policy(serving.ProvisioningAccessPolicy())
            return decisions[binding.identity]
        server.replace_access_policy(replace(server.access_policy, qualification_resolver=
            serving.ProvisioningQualificationResolver("fixture:revocation", resolve)))
        return (ask(server, "list")["items"] == [] and not reads and not meter.rows)

    check("revocation_during_metadata_resolution_cannot_reuse_the_old_policy", revoked_by_resolver)

    def current_versions():
        server, _, reads, meter, _ = fixture()
        return (refusal(lambda: serving.ProvisioningRequest("read", "paid-key", record_type=
                                                        "provisioning_request/v1"), "unsupported_version")
                and refusal(lambda: replace(server.access_policy, record_type="unsupported"),
                            "unsupported_version")
                and refusal(lambda: ask(server, "read", request_id=""))
                and not reads and not meter.rows)

    check("unsupported_versions_and_missing_meter_identity_refuse_before_effects", current_versions)

    def typed_immutable():
        server, _, _, _, _ = fixture()
        frozen = False
        try:
            server.access_policy = serving.ProvisioningAccessPolicy()
        except FrozenInstanceError:
            frozen = True
        grant = server.access_policy.grants[0]
        return (frozen and refusal(lambda: replace(grant, body_allowed="true"))
                and refusal(lambda: replace(server.access_policy.qualification_resolver, read_only="true"))
                and refusal(lambda: replace(server, tenants=(server.tenants[0], server.tenants[0])))
                and "paid-key" not in repr(serving.ProvisioningRequest("list", "paid-key")))

    check("policy_and_tenants_are_unambiguous_immutable_and_secret_safe", typed_immutable)

    def unknown_key():
        server, _, reads, meter, _ = fixture()
        return (refusal(lambda: ask(server, "discover", key="not-a-key"), "unauthorized")
                and not reads and not meter.rows)

    check("wrong_key_refuses_before_catalogue_or_body_effects", unknown_key)
    _tier_checks(check)
    passed = sum(row["passed"] for row in tests)
    return {"record_type": "provisioning_server_test/v2", "tests": tests,
            "passed": passed, "total": len(tests), "all_passed": passed == len(tests)}


def tier_fixture():
    """Two verified and two community items granted to one paid tenant; one community item runs a script."""
    catalogue = HarnessIntelligenceCatalogue()
    tiers = {"skill.verified": serving.VERIFIED_TIER, "tool.verified_runs": serving.VERIFIED_TIER,
             "skill.community": serving.COMMUNITY_TIER, "tool.community_runs": serving.COMMUNITY_TIER}
    bodies = {identity: f"Tier fixture: {identity}\n" for identity in tiers}
    for identity in tiers:
        runs = identity.endswith("_runs")
        catalogue.register(item_from_body(HarnessIntelligenceDraft(
            identity, "tool" if runs else "skill", "Tier fixture " + identity, "context_intelligence",
            "context:" + identity, "MIT", declared_effects=("spawns_process",) if runs else ()),
            bodies[identity]))
    decisions = {}
    for item in catalogue.items.values():
        binding = serving.ProvisioningItemBinding.from_item(item)
        decisions[item.identity] = serving.ProvisioningQualification(
            binding, "approved", "host_attested", "fixture:admission:" + item.identity, tiers[item.identity])
    policy = serving.ProvisioningAccessPolicy(
        tuple(serving.ProvisioningGrant("paid", decision.binding, True) for decision in decisions.values()),
        serving.ProvisioningQualificationResolver("fixture:tiers", lambda binding: decisions.get(binding.identity)))
    reads = []
    server = serving.ProvisioningServer(
        catalogue, (serving.ProvisioningTenant("paid", key_digest("paid-key"), "bodies"),),
        lambda item: reads.append(item.identity) or bodies[item.identity], serving.RecordedMeter(),
        access_policy=policy)
    return server, reads


def _tier_checks(check):
    """Known-wrong cases of the trust tier, each with a control that removes its guard."""
    runs = ("spawns_process",)

    def listed(server, choice, effects=runs):
        return [(row["identity"], row["trust_tier"]) for row in
                ask(server, "list", authority_effects=effects, community_items=choice)["items"]]

    def silent_by_default():
        server, reads = tier_fixture()
        rows = listed(server, serving.COMMUNITY_EXCLUDED)
        return (rows == [("skill.verified", "baltor_verified"), ("tool.verified_runs", "baltor_verified")]
                and ask(server, "list", authority_effects=runs)["items"] == ask(
                    server, "list", authority_effects=runs, community_items=serving.COMMUNITY_EXCLUDED)["items"]
                and refusal(lambda: ask(server, "manifest", "skill.community"), "item_outside_library_setting")
                and refusal(lambda: ask(server, "read", "skill.community"), "item_outside_library_setting")
                and not reads)

    check("a_request_that_says_nothing_is_offered_no_community_item", silent_by_default)
    with patch.object(serving, "in_library", lambda item, decision, choice: True):
        check("removed_community_default_rule_is_detected", lambda: not silent_by_default())

    def runnable_needs_inclusion():
        server, reads = tier_fixture()
        middle = listed(server, serving.COMMUNITY_WITHOUT_RUNNABLE)
        every = listed(server, serving.COMMUNITY_INCLUDED)
        loaded = ask(server, "read", "tool.community_runs", authority_effects=runs,
                     community_items=serving.COMMUNITY_INCLUDED)
        return (middle == [("skill.verified", "baltor_verified"), ("tool.verified_runs", "baltor_verified"),
                           ("skill.community", "community")]
                and every == middle + [("tool.community_runs", "community")]
                and refusal(lambda: ask(server, "read", "tool.community_runs", authority_effects=runs,
                                        community_items=serving.COMMUNITY_WITHOUT_RUNNABLE),
                            "item_outside_library_setting")
                and loaded["trust_tier"] == "community" and reads == ["tool.community_runs"])

    check("a_community_item_that_runs_a_file_is_offered_only_when_the_account_includes_it", runnable_needs_inclusion)
    with patch.object(serving, "RUNNABLE_EFFECT", "not_an_effect"):
        check("removed_runnable_community_rule_is_detected", lambda: not runnable_needs_inclusion())

    def every_answer_names_the_tier():
        server, _ = tier_fixture()
        choice = serving.COMMUNITY_INCLUDED
        rows = ask(server, "list", authority_effects=runs, community_items=choice)["items"]
        manifest = ask(server, "manifest", "skill.community", community_items=choice)
        body = ask(server, "read", "skill.verified", community_items=choice)
        held = ask(server, "discover", authority_effects=runs, community_items=choice)
        order = [serving.TIER_ORDER[row["trust_tier"]] for row in rows]
        return (all(row["trust_tier"] in serving.TRUST_TIERS for row in rows) and order == sorted(order)
                and manifest["trust_tier"] == "community"
                and manifest["record_type"] == serving.TIERED_MANIFEST_RECORD_TYPE
                and body["trust_tier"] == "baltor_verified" and body["record_type"] == serving.TIERED_BODY_RECORD_TYPE
                and held["items_by_trust_tier"] == {"baltor_verified": 2, "community": 2})

    check("every_list_row_manifest_and_body_names_its_trust_tier_and_verified_rows_come_first",
          every_answer_names_the_tier)

    def approval_states_its_tier():
        server, _ = tier_fixture()
        binding = serving.ProvisioningItemBinding.from_item(server.catalogue.items["skill.verified"])
        return (serving.ProvisioningQualification(binding, "approved", "host_attested", "ref").trust_tier
                == serving.VERIFIED_TIER
                and refusal(lambda: serving.ProvisioningQualification(binding, "approved", "host_attested", "ref",
                                                                      "reviewed_by_someone"), "trust_tier_invalid")
                and refusal(lambda: serving.ProvisioningQualification(binding, "unknown", "host_attested", "",
                                                                      "community"), "trust_tier_invalid")
                and refusal(lambda: serving.ProvisioningRequest("list", "paid-key", community_items="all")))

    check("an_approval_names_a_known_tier_panel_approvals_are_verified_and_nothing_else_carries_one",
          approval_states_its_tier)

    def unknown_tier_is_never_offered():
        server, reads = tier_fixture()
        decision = server.access_policy.qualification_resolver.resolve(
            serving.ProvisioningItemBinding.from_item(server.catalogue.items["skill.community"]))
        forged = object.__new__(serving.ProvisioningQualification)
        for name in ("binding", "status", "basis", "approval_ref", "record_type"):
            object.__setattr__(forged, name, getattr(decision, name))
        object.__setattr__(forged, "trust_tier", "reviewed_elsewhere")
        return (not serving.in_library(server.catalogue.items["skill.community"], forged, serving.COMMUNITY_INCLUDED)
                and not reads)

    check("a_decision_with_an_unknown_tier_belongs_to_no_library", unknown_tier_is_never_offered)
