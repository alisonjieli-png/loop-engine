"""Checks for catalogue releases, the body store, the attribute schema and release-following grants.

Every check runs against a real temporary service store and a real body
folder. No network, model or provider is used. Each guard is shown twice: the
known-wrong case is refused, and a removed-guard control reruns the same case
with the guard patched away and requires the check's own predicate to fail.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import replace
import json
import os
from pathlib import Path
import tempfile
import time
from unittest.mock import patch

from ..harness_intelligence import HarnessIntelligenceDraft, item_from_body
from . import catalogue_bundle, catalogue_packages, catalogue_releases, catalogue_schema
from .catalogue_bundle import BUNDLE_ITEM_RECORD_TYPE, read_bundle, write_bundle
from .catalogue_grants import follow_active_release
from .catalogue_packages import CataloguePackage, CataloguePackageFile, VolumeBodyStore, sha256_hex
from .catalogue_releases import CatalogueOperatorContext, publish, rollback, status, withdraw
from .catalogue_schema import CatalogueAttributeSchema
from .catalogue_serving import CatalogueRefresher, CatalogueSourceSettings, next_view, state_token, store_view
from .provisioning import DurableProvisioningBinding
from .records import ServiceRuntimeConfig, ServiceRuntimeError, TenantKeyIssue, TenantRegistration
from .runtime import ServiceRuntime
from .storage import ServiceCatalogBinding

SCHEMA = {"record_type": "catalogue_attribute_schema/v1", "attributes": [
    {"name": "domain", "type": "keyword_list", "searchable": True, "filterable": True, "shown": True},
    {"name": "origin_layer", "type": "choice", "choices": ["context_intelligence", "code_intelligence"],
     "filterable": True, "shown": True},
    {"name": "batch", "type": "keyword", "visibility": "internal"}]}


def refused(action, code=None):
    from ..provisioning_server import ProvisioningError
    try:
        action()
    except (ServiceRuntimeError, ProvisioningError) as error:
        return code is None or error.code == code
    except Exception:  # noqa: BLE001 - a crash is not a typed refusal
        return False
    return False


def _policies():
    from .http_entrypoint import DEFAULT_LICENSE_POLICY, HostFamilyPolicy
    return DEFAULT_LICENSE_POLICY, HostFamilyPolicy(accepted_families=("harness",))


def bundle_line(identity, files, *, effects=(), attributes=None, approved_digest=None, approval_ref=None,
                body_form=None, purpose=None):
    """One bundle item for a package of `(path, bytes, media_type, role)` files."""
    entries = tuple(CataloguePackageFile(path, sha256_hex(data), len(data), media, role)
                    for path, data, media, role in files)
    form = body_form or ("file" if len(entries) == 1 and files[0][2].startswith("text/") else "package")
    package = CataloguePackage(entries, form)
    draft = HarnessIntelligenceDraft(identity, "skill", purpose or ("Purpose of " + identity.replace("_", " ")),
                                     "harness_local", "fixture:" + identity, "MIT", tuple(effects))
    item = replace(item_from_body(draft, "placeholder"), digest=package.served_digest, size_bytes=package.served_size)
    return {"record_type": BUNDLE_ITEM_RECORD_TYPE, "reference": item.reference(), "package": package.to_dict(),
            "approval": {"approval_ref": "review:" + identity if approval_ref is None else approval_ref,
                         "approved_digest": package.served_digest if approved_digest is None else approved_digest},
            "attributes": attributes or {}}


def skill(identity, text, **fields):
    return bundle_line(identity, [("SKILL.md", text.encode(), "text/markdown", "skill_definition")], **fields)


class Fixture:
    """A service store with one entitled account, a body folder and a bundle folder counter."""

    def __init__(self, root):
        self.root = Path(root).resolve()
        (self.root / "bodies").mkdir(parents=True)
        self.config = ServiceRuntimeConfig(str(self.root / "service.db"), writes_authorized=True)
        self.runtime = ServiceRuntime(self.config)
        self.runtime.register_tenant(TenantRegistration("alpha", "tenant:alpha"))
        self.key = self.runtime.issue_key(TenantKeyIssue("alpha", "catalogue checks"))
        self.runtime.set_operator_entitlement("alpha", valid_until=int(time.time()) + 3600,
                                              evidence_ref="local-check-not-payment")
        self.context = CatalogueOperatorContext(ServiceCatalogBinding(self.config), str(self.root / "bodies"))
        self.settings = CatalogueSourceSettings("store", str(self.root / "bodies"))
        self.license_policy, self.family_policy = _policies()
        self.count = 0
        # The account follows the active release, so each check reads what the
        # release serves rather than a list copied by hand.
        follow_active_release(self.runtime, ["alpha"])

    def bundle(self, lines, *, schema=SCHEMA, withdrawals=(), notes="", payloads=None):
        self.count += 1
        folder = self.root / f"bundle-{self.count}"
        if payloads is None:
            payloads = self.payloads
        write_bundle(folder, schema=CatalogueAttributeSchema.from_dict(schema), lines=lines, payloads=payloads,
                     notes=notes, withdrawals=list(withdrawals))
        return read_bundle(folder, license_policy=self.license_policy, family_policy=self.family_policy)

    payloads = ()

    def publish(self, lines, **fields):
        self.payloads = [data for line in lines for data in self._bytes.get(line["reference"]["identity"], ())]
        return publish(self.context, self.bundle(lines, **{k: v for k, v in fields.items() if k != "expected"}),
                       expected_release=fields.get("expected"))

    _bytes = {}

    def line(self, identity, text, **fields):
        self._bytes = {**self._bytes, identity: (text.encode(),)}
        return skill(identity, text, **fields)

    def view(self):
        return store_view(self.config, self.settings, license_policy=self.license_policy,
                          family_policy=self.family_policy)

    def binding(self, view=None):
        view = view or self.view()
        return DurableProvisioningBinding(self.runtime, view.catalogue, view.qualification_resolver,
                                          view.body_reader, view=view)

    def listed(self, binding):
        return sorted(row["identity"] for row in binding.invoke(self.key.key, "list")["items"])


@contextmanager
def fixture():
    with tempfile.TemporaryDirectory(prefix="catalogue-release-checks-") as directory:
        yield Fixture(directory)


def _body_store_checks(check, root):
    folder = Path(root).resolve() / "store"
    folder.mkdir()
    writer = VolumeBodyStore(str(folder), writes_authorized=True)
    stored = writer.put(b"one body")
    again = writer.put(b"one body")
    check("a_blob_is_stored_once_under_its_digest_and_read_back_verified",
          stored["written"] is True and again["written"] is False
          and VolumeBodyStore(str(folder)).read(stored["digest"], 8) == b"one body"
          and (folder / VolumeBodyStore.object_key(stored["digest"])).is_file()
          and refused(lambda: VolumeBodyStore(str(folder)).put(b"x"), "body_store_writes_not_authorized")
          and refused(lambda: writer.put(b"x", expected_digest="0" * 64), "body_digest_mismatch"))
    outside = Path(root).resolve() / "outside"
    outside.mkdir()
    linked = Path(root).resolve() / "linked"
    linked.mkdir()
    os.symlink(outside, linked / "sha256")

    def escape():
        refusal = refused(lambda: VolumeBodyStore(str(linked), writes_authorized=True).put(b"escape"),
                          "body_path_unsafe")
        return refusal and not any(outside.rglob("*"))
    check("a_blob_is_never_written_through_a_linked_folder_outside_the_store", escape())
    with patch.object(catalogue_packages, "real_folder", lambda info: True):
        check("removed_real_folder_rule_is_detected", not escape())
    digest = sha256_hex(b"honest bytes")
    planted = folder / "sha256" / digest[:2]
    planted.mkdir(parents=True, exist_ok=True)

    def conflict():
        target = planted / digest
        if target.exists():
            os.chmod(target, 0o644)
            target.unlink()
        target.write_bytes(b"planted bytes!")
        refusal = refused(lambda: writer.put(b"honest bytes"))
        return refusal and target.read_bytes() == b"planted bytes!"
    check("an_existing_object_with_other_bytes_is_never_overwritten", conflict())
    with patch.object(VolumeBodyStore, "_present", lambda self, digest, size: False), \
            patch.object(catalogue_packages, "_link_once", os.replace):
        check("removed_no_overwrite_rule_is_detected", not conflict())
    reader = VolumeBodyStore(str(folder))
    tampered = folder / VolumeBodyStore.object_key(stored["digest"])
    os.chmod(tampered, 0o644)
    tampered.write_bytes(b"two body")
    link_digest = sha256_hex(b"linked object")
    (folder / "sha256" / link_digest[:2]).mkdir(parents=True, exist_ok=True)
    (outside / "target").write_bytes(b"linked object")
    os.symlink(outside / "target", folder / "sha256" / link_digest[:2] / link_digest)
    check("a_changed_linked_or_invented_object_is_refused_at_read",
          refused(lambda: reader.read(stored["digest"], 8), "body_digest_mismatch")
          and refused(lambda: reader.read(link_digest, 13), "body_path_unsafe")
          and refused(lambda: reader.read("../../../etc/passwd", 1), "body_digest_invalid")
          and refused(lambda: reader.read("a" * 64, 1), "body_missing"))


def _package_and_schema_checks(check):
    def package(*files, form="package"):
        return CataloguePackage(tuple(CataloguePackageFile(path, "a" * 64, 1, media, role)
                                      for path, media, role in files), form)
    check("a_package_refuses_unsafe_paths_duplicate_placements_and_unknown_types",
          all(refused(lambda path=path: package((path, "text/plain", "other")), "package_path_invalid")
              for path in ("../escape", ".git/hooks/pre-commit", "/absolute", "a/./b", "a//b", "a\\b", ""))
          and refused(lambda: package(("A.md", "text/plain", "other"), ("a.md", "text/plain", "other")),
                      "package_path_duplicate")
          and refused(lambda: package(("x", "Text/Plain", "other")), "package_media_type_invalid")
          and refused(lambda: package(("x", "text/plain", "daemon")), "package_file_role_invalid")
          and refused(lambda: package(("a", "text/plain", "other"), ("b", "text/plain", "other"), form="file"),
                      "package_body_form_invalid"))
    mixed = CataloguePackage((
        CataloguePackageFile("AGENTS.md", sha256_hex(b"# Agents\n"), 9, "text/markdown", "instruction_file"),
        CataloguePackageFile("scripts/run.py", sha256_hex(b"print(1)\n"), 9, "text/x-python", "skill_script"),
        CataloguePackageFile("assets/logo.png", sha256_hex(b"\x89PNG\x00"), 5, "image/png", "skill_asset"),
        CataloguePackageFile(".mcp.json", sha256_hex(b"{}"), 2, "application/json", "protocol_server_configuration")))
    check("a_package_holds_any_harness_file_type_with_its_own_digest_type_and_role",
          mixed.served_digest == sha256_hex(mixed.document()) and mixed.executable
          and [entry.path for entry in mixed.files] == [".mcp.json", "AGENTS.md", "assets/logo.png", "scripts/run.py"]
          and catalogue_packages.parse_package_document(mixed.document().decode()) == mixed)
    reserved = ("declared_effects", "licence", "license_state", "permissions", "network_effects", "review_passed",
                "grant_level", "approved_by", "body_allowed")

    def reserved_refused():
        return all(refused(lambda name=name: CatalogueAttributeSchema.from_dict(
            {"record_type": "catalogue_attribute_schema/v1", "attributes": [{"name": name, "type": "keyword"}]}),
            "attribute_name_reserved") for name in reserved)
    check("an_attribute_named_for_an_effect_licence_or_permission_is_refused", reserved_refused())
    with patch.object(catalogue_schema, "attribute_name_refusal", lambda name: ""):
        check("removed_reserved_attribute_rule_is_detected", not reserved_refused())
    schema = CatalogueAttributeSchema.from_dict(SCHEMA)
    check("attribute_values_that_are_undeclared_mistyped_or_unlisted_are_refused",
          refused(lambda: schema.validate_values({"declared_effects": ["network"]}), "attribute_not_declared")
          and refused(lambda: schema.validate_values({"domain": "not a list"}), "attribute_value_invalid")
          and refused(lambda: schema.validate_values({"origin_layer": "somewhere_else"}), "attribute_value_invalid")
          and schema.validate_values({"origin_layer": "code_intelligence"}) == {"origin_layer": "code_intelligence"})
    check("an_internal_attribute_is_never_searched_filtered_sorted_or_shown",
          all(refused(lambda flag=flag: catalogue_schema.CatalogueAttribute("batch", "keyword", visibility="internal",
                                                                            **{flag: True}), "attribute_schema_invalid")
              for flag in ("searchable", "filterable", "sortable", "shown"))
          and schema.shown_values({"domain": ["x"], "batch": "secret batch"}) == {"domain": ["x"]}
          and "secret" not in schema.search_text({"domain": ["x"], "batch": "secret batch"}))

    def internal_filter_refused():
        return (refused(lambda: schema.filter_request({"batch": {"equals": "one"}}), "search_filter_not_allowed")
                and refused(lambda: schema.filter_request({"undeclared": {"equals": "x"}}), "search_filter_not_allowed"))
    check("a_filter_on_an_internal_or_undeclared_attribute_is_refused", internal_filter_refused())
    with patch.object(catalogue_schema, "filter_permitted", lambda declared: declared is not None):
        check("removed_public_filter_rule_is_detected", not internal_filter_refused())


def _bundle_checks(check, root):
    license_policy, family_policy = _policies()
    schema = CatalogueAttributeSchema.from_dict(SCHEMA)
    body = b"# Skill\n"

    def accepted(line, payloads=(body,)):
        folder = Path(tempfile.mkdtemp(dir=root)) / "bundle"
        write_bundle(folder, schema=schema, lines=[line], payloads=list(payloads))
        try:
            read_bundle(folder, license_policy=license_policy, family_policy=family_policy)
            return True
        except ServiceRuntimeError as error:
            return error.code
    unapproved = skill("unapproved_item", body.decode(), approval_ref="")
    other_bytes = skill("approval_elsewhere", body.decode(), approved_digest=sha256_hex(b"other bytes"))
    check("an_unapproved_item_is_never_published", accepted(unapproved) == "explicit_host_review_required")
    check("an_approval_of_other_bytes_is_never_published", accepted(other_bytes) == "approval_not_bound_to_bytes")
    with patch.object(catalogue_bundle, "approval_refusal", lambda approval, package: ""):
        check("removed_approval_rule_is_detected", accepted(unapproved) is True)
    with patch.object(catalogue_bundle, "approval_refusal",
                      lambda approval, package: "" if approval["approval_ref"] else "explicit_host_review_required"):
        check("removed_exact_bytes_rule_is_detected", accepted(other_bytes) is True)
    script = b"#!/bin/sh\necho run\n"
    runnable = bundle_line("runs_a_script", [("SKILL.md", body, "text/markdown", "skill_definition"),
                                             ("scripts/run.sh", script, "text/x-shellscript", "skill_script")])
    declared = bundle_line("declares_its_process", [("SKILL.md", body, "text/markdown", "skill_definition"),
                                                     ("scripts/run.sh", script, "text/x-shellscript", "skill_script")],
                           effects=("spawns_process",))
    check("a_package_with_a_runnable_file_declares_the_process_effect",
          accepted(runnable, (body, script)) == "package_executable_effect_undeclared"
          and accepted(declared, (body, script)) is True)
    with patch.object(catalogue_bundle, "effect_refusal", lambda item, package: ""):
        check("removed_process_effect_rule_is_detected", accepted(runnable, (body, script)) is True)
    loop_native = skill("loop_native_item", body.decode())
    loop_native["reference"] = {**loop_native["reference"], "source_layer": "context_intelligence",
                                "family": "loop_native"}
    unknown_licence = skill("unknown_licence", body.decode())
    unknown_licence["reference"] = {**unknown_licence["reference"], "license": "NOASSERTION"}
    check("a_bundle_applies_the_host_family_and_licence_policies_like_the_manifest_loader",
          accepted(loop_native) == "item_family_not_accepted" and accepted(unknown_licence) == "item_license_unknown")
    folder = Path(tempfile.mkdtemp(dir=root)) / "bundle"
    write_bundle(folder, schema=schema, lines=[skill("bounded_line", body.decode())], payloads=[body])
    items = folder / "items.jsonl"
    original = items.read_bytes()

    def after(change):
        change()
        try:
            read_bundle(folder, license_policy=license_policy, family_policy=family_policy)
            outcome = True
        except ServiceRuntimeError as error:
            outcome = error.code
        items.write_bytes(original)
        header = json.loads((folder / "bundle.json").read_text())
        header.update(items=1, items_bytes=len(original), items_digest=sha256_hex(original))
        (folder / "bundle.json").write_text(json.dumps(header))
        return outcome

    def rewrite(payload, count=1, digest=True):
        items.write_bytes(payload)
        header = json.loads((folder / "bundle.json").read_text())
        header.update(items=count, items_bytes=len(payload),
                      items_digest=sha256_hex(payload) if digest else sha256_hex(original))
        (folder / "bundle.json").write_text(json.dumps(header))

    def bounds():
        return (after(lambda: rewrite(b"{not json\n")) == "bundle_item_invalid"
                and after(lambda: rewrite(original, count=2)) == "bundle_items_changed"
                and after(lambda: rewrite(original.replace(b"bounded", b"Bounded"), digest=False))
                == "bundle_items_changed"
                and after(lambda: rewrite(original[:-1])) == "bundle_item_line_invalid"
                and after(lambda: rewrite(b"[" * 70_000 + b"\n")) in (
                    "bundle_item_line_invalid", "bundle_item_invalid", "bundle_header_invalid"))
    check("an_oversized_malformed_truncated_or_changed_bundle_is_refused", bounds())
    with patch.object(catalogue_bundle, "MAXIMUM_ITEM_LINE_BYTES", 10_000_000):
        check("a_larger_line_limit_alone_still_refuses_malformed_or_changed_bundles", bounds())
    check("a_bundle_folder_of_the_wrong_shape_is_refused",
          refused(lambda: read_bundle("relative/folder", license_policy=license_policy, family_policy=family_policy),
                  "bundle_folder_invalid"))


def _release_checks(check):
    with fixture() as case:
        first = case.publish([case.line("clean_names", "# Clean names\none\n", attributes={"domain": ["data"]}),
                              case.line("profile_column", "# Profile\none\n")], notes="first")
        again = case.publish([case.line("clean_names", "# Clean names\none\n", attributes={"domain": ["data"]}),
                              case.line("profile_column", "# Profile\none\n")])
        second = case.publish([case.line("clean_names", "# Clean names\ntwo\n", attributes={"domain": ["data"]}),
                               case.line("profile_column", "# Profile\none\n"), case.line("new_item", "# New\n")])
        record = status(case.context)
        stored = [row for row in record["releases"] if row["release_id"] == second["release_id"]][0]
        check("a_publish_is_idempotent_by_content_and_records_what_changed",
              first["state"] == "published" and again["state"] == "unchanged"
              and again["release_id"] == first["release_id"]
              and (second["added"], second["changed"], second["withdrawn"]) == (1, 1, 0)
              and stored["changes"] == {"added": 1, "changed": 1, "withdrawn": 0}
              and record["active_release_id"] == second["release_id"] and record["catalogue_state_version"] == 1)
        check("the_pointer_moves_only_under_its_expected_version",
              refused(lambda: case.publish([case.line("late", "# Late\n")], expected=first["release_id"]),
                      "catalogue_pointer_moved")
              and refused(lambda: rollback(case.context, to_release=first["release_id"],
                                           expected_release=first["release_id"]), "catalogue_pointer_moved")
              and status(case.context)["active_release_id"] == second["release_id"])
        lines = [case.line("clean_names", "# Clean names\ntwo\n", attributes={"domain": ["data"]}),
                 case.line("half_written", "# Half\n")]

        def partial():
            real = catalogue_releases._write_immutable
            with patch.object(catalogue_releases, "_write_immutable", lambda binding, rows: real(binding, rows[:1])):
                outcome = refused(lambda: case.publish(lines), "catalogue_release_incomplete")
            return outcome and status(case.context)["active_release_id"] == second["release_id"]
        check("a_partial_publish_never_becomes_active", partial())
        with patch.object(catalogue_releases, "require_complete_release", lambda *arguments: None):
            check("removed_complete_release_rule_is_detected", not partial())
    _withdrawal_checks(check)


def _withdrawal_checks(check):
    with fixture() as case:
        first = case.publish([case.line("keeper", "# Keeper\n"), case.line("harmful", "# Harmful\n")])
        second = case.publish([case.line("keeper", "# Keeper\n")],
                              withdrawals=[{"identity": "harmful", "note": "unsafe instruction"}])
        back = rollback(case.context, to_release=first["release_id"], expected_release=second["release_id"])

        def withheld():
            binding = case.binding()
            listed = case.listed(binding)
            read = refused(lambda: binding.invoke(case.key.key, "read", identity="harmful", request_id="after"))
            return listed == ["keeper"] and read
        check("a_withdrawn_item_is_not_served_after_a_rollback",
              back["withdrawn_items_kept_withheld"] == ["harmful"] and second["durable_withdrawals"] == 1 and withheld())
        with patch.object(catalogue_releases, "withdrawal_keys", lambda binding, store: frozenset()), \
                patch.object(catalogue_releases, "is_withdrawn", lambda *arguments: False):
            check("removed_withdrawal_rule_is_detected", not withheld())
        check("a_release_that_lists_a_withdrawn_item_version_is_refused",
              refused(lambda: case.publish([case.line("keeper", "# Keeper\n"), case.line("harmful", "# Harmful\n")]),
                      "catalogue_release_lists_withdrawn_item"))
        binding = case.binding()
        withdraw(case.context, identity="keeper", note_text="withdrawn while the view was served")

        def refused_on_the_old_view():
            return refused(lambda: binding.invoke(case.key.key, "read", identity="keeper", request_id="late"),
                           "item_withdrawn")
        check("a_withdrawal_recorded_after_the_view_was_built_is_refused_at_read", refused_on_the_old_view())
        with patch.object(catalogue_releases, "is_withdrawn", lambda *arguments: False):
            check("removed_read_time_withdrawal_rule_is_detected", not refused_on_the_old_view())
    with fixture() as case:
        first = case.publish([case.line("stable", "# Stable\n")])
        second = case.publish([case.line("stable", "# Stable\nnew\n")])
        target = case.root / "bodies" / VolumeBodyStore.object_key(sha256_hex(b"# Stable\n"))
        os.chmod(target, 0o644)
        target.write_bytes(b"# Stabl3\n")
        check("a_rollback_target_with_a_changed_body_is_refused_before_the_pointer_moves",
              refused(lambda: rollback(case.context, to_release=first["release_id"],
                                       expected_release=second["release_id"]), "body_digest_mismatch")
              and status(case.context)["active_release_id"] == second["release_id"])


def _refresh_and_grant_checks(check):
    from .observability import ServiceFailureJournal
    with fixture() as case:
        case.publish([case.line("first_item", "# First\n")])
        binding = case.binding()
        follow_active_release(case.runtime, ["alpha"], denials=("denied_item",))
        journal = ServiceFailureJournal(case.config, ("/api/v1/health",))
        refresher = CatalogueRefresher(
            binding, build=lambda current, token: next_view(current, token, case.config, case.settings,
                                                            license_policy=case.license_policy,
                                                            family_policy=case.family_policy),
            probe=lambda: state_token(case.config), journal=journal, interval_seconds=5)
        before = case.listed(binding)
        second = case.publish([case.line("first_item", "# First\n"), case.line("second_item", "# Second\n"),
                               case.line("denied_item", "# Denied\n"),
                               case.line("needs_network", "# Network\n", effects=("network",))])
        swapped = refresher.check_once()
        after = case.listed(binding)
        check("a_new_item_reaches_a_following_account_without_apply_grants",
              before == ["first_item"] and swapped["changed"] is True and after == ["first_item", "second_item"]
              and binding.current_view().release_id == second["release_id"])

        def denied():
            return "denied_item" not in case.listed(binding)
        check("a_denied_item_never_reaches_a_following_account", denied())
        from .catalogue_grants import ReleaseFollowingGrants
        materialize = ReleaseFollowingGrants.materialize
        with patch.object(ReleaseFollowingGrants, "materialize", lambda self, view, candidates=None: materialize(
                replace(self, denials=frozenset()), view, candidates)):
            check("removed_denial_rule_is_detected", not denied())
        effects = binding.invoke(case.key.key, "list", authority_effects=("network",))["items"]
        check("an_item_that_declares_effects_stays_withheld_until_the_client_declares_them",
              "needs_network" not in after and "needs_network" in [row["identity"] for row in effects])
        third = case.publish([case.line("first_item", "# First\n"), case.line("third_item", "# Third\n")])
        target = case.root / "bodies" / VolumeBodyStore.object_key(sha256_hex(b"# Third\n"))
        os.chmod(target, 0o644)
        target.write_bytes(b"# Thirt\n")

        def keeps_previous():
            outcome = refresher.check_once()
            return (outcome.get("failure") == "body_digest_mismatch"
                    and binding.current_view().release_id == second["release_id"]
                    and journal.recent(limit=5)["failures"][0]["refusal_code"] == "catalogue_refresh:body_digest_mismatch")
        check("a_release_with_a_changed_body_is_never_swapped_in_and_the_failure_is_recorded", keeps_previous())
        with patch.object(catalogue_releases, "verify_release_bodies", lambda *arguments, **fields: None):
            check("removed_body_verification_before_swap_is_detected",
                  not keeps_previous() and binding.current_view().release_id == third["release_id"])


def _new_account_checks(check):
    from ..provisioning_server import ProvisioningItemBinding
    from .records import SubjectTenantRegistration
    with fixture() as case:
        case.publish([case.line("welcome", "# Welcome\n")])
        created = case.runtime.ensure_subject_tenant(SubjectTenantRegistration(
            "https://issuer.example", "subject-one", "account", follows_active_release=True))
        principal = case.runtime.authenticate_subject("https://issuer.example", "subject-one")
        listed = case.binding().invoke_for_principal(principal, "list")["items"]
        starter = ProvisioningItemBinding.from_item(case.view().catalogue.items["welcome"])
        check("a_new_account_can_follow_the_active_release_from_its_first_request",
              created["created"] is True and [row["identity"] for row in listed] == ["welcome"]
              and refused(lambda: SubjectTenantRegistration("https://issuer.example", "subject-two", "account",
                                                            starter_bindings=(starter,), follows_active_release=True),
                          "invalid_starter_bindings"))


def _gate_checks(check, root):
    from .catalogue_serving import catalogue_state_gate
    with fixture() as case:
        case.publish([case.line("gated", "# Gated\n")])
        binding = case.context.binding
        with binding.store(write=True) as store:
            state_row, state = catalogue_releases.read_state(binding, store)
            future = binding.record(catalogue_releases.STATE_KIND, catalogue_releases.STATE_LOGICAL,
                                    {**state, "state_version": 2, "revision": state["revision"] + 1})
            # A later release withdraws the item through a record kind this
            # release has never heard of, and raises the state version with it.
            blocked = binding.record("service_catalogue_block", "gated",
                                     {"record_type": "catalogue_block/v1", "identity": "gated"})
            binding.commit(store, (future, blocked), (binding.guard(state_row),
                                                      binding.guard(None, blocked["record_id"])))

        def start_refused():
            return refused(lambda: case.view(), "catalogue_state_version_unsupported") and refused(
                lambda: catalogue_state_gate(case.config, case.settings), "catalogue_state_version_unsupported")
        check("an_image_refuses_to_start_on_catalogue_state_it_does_not_understand", start_refused())

        def ignoring_image_serves_withdrawn():
            # A later state version can carry a withdrawal kind this image never
            # reads. An image that ignored the marker would serve the item.
            with patch.object(catalogue_releases, "SUPPORTED_CATALOGUE_STATE_VERSIONS", (1, 2)):
                return "gated" in case.listed(case.binding())
        check("an_image_that_ignores_the_marker_serves_a_withdrawn_item", ignoring_image_serves_withdrawn())
        with patch.object(catalogue_releases, "SUPPORTED_CATALOGUE_STATE_VERSIONS", (1, 2)):
            check("removed_state_version_gate_is_detected", not start_refused())
    with fixture() as case:
        case.publish([case.line("gated", "# Gated\n")])
        check("a_host_file_without_the_catalogue_section_is_refused_when_the_store_holds_catalogue_state",
              refused(lambda: catalogue_state_gate(case.config, None), "catalogue_section_required")
              and catalogue_state_gate(case.config, case.settings)["state_version"] == 1)
        from .catalogue_commands import operator_context
        host = case.root / "host.json"
        host.write_text(json.dumps({"record_type": "service_http_host_configuration/v1",
                                    "runtime": {"database_path": str(case.config.database_path),
                                                "writes_authorized": True}}))
        check("every_catalogue_command_refuses_a_host_file_without_the_catalogue_section",
              refused(lambda: operator_context(str(host)), "catalogue_section_required"))
        from .http_entrypoint import load_host_application
        host.write_text(json.dumps({"record_type": "service_http_host_configuration/v1", "runtime": {},
                                    "http": {}, "authentication": {}, "manifest_path": "/absent",
                                    "catalogue_state_after_this_release": {}}))
        check("a_host_reader_refuses_a_host_key_it_does_not_know",
              refused(lambda: load_host_application(str(host)), "unsupported_host_configuration"))


def run_checks(check=None):
    tests = []
    if check is None:
        def check(name, passed):
            tests.append({"test": name, "passed": bool(passed),
                          "detail": "real temporary service store and body folder; no provider"})
    with tempfile.TemporaryDirectory(prefix="catalogue-body-store-") as directory:
        _body_store_checks(check, directory)
    _package_and_schema_checks(check)
    with tempfile.TemporaryDirectory(prefix="catalogue-bundles-") as directory:
        _bundle_checks(check, directory)
    _release_checks(check)
    _refresh_and_grant_checks(check)
    _new_account_checks(check)
    with tempfile.TemporaryDirectory(prefix="catalogue-gates-") as directory:
        _gate_checks(check, directory)
    return {"record_type": "catalogue_release_checks/v1", "tests": tests,
            "passed": sum(row["passed"] for row in tests), "total": len(tests),
            "all_passed": all(row["passed"] for row in tests)}


def self_test():
    return run_checks()
