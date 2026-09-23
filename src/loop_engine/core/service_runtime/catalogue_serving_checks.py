"""Loopback checks for serving catalogue releases: hot swap, schema search, package files and commands.

A real service answers on a loopback socket over a real temporary store and
body folder. A release is published while it runs and reaches search and
download without a restart. A request that started before a swap finishes on
the view it started with. No provider or external network is used.
"""
from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import time
from unittest.mock import patch

from .catalogue_release_checks import SCHEMA, Fixture, bundle_line, refused
from .catalogue_packages import sha256_hex
from .catalogue_serving import CatalogueRefresher, next_view, state_token
from .http import RETRIEVAL_REQUEST_VERSION
from .http_checks import provisioning_request
from .http_test_fixtures import running_http
from .provisioning import DurableProvisioningBinding

PICTURE = b"\x89PNG\r\n\x1a\n\x00binary asset"
SCRIPT = b"#!/bin/sh\necho ready\n"


def _package_line():
    return bundle_line("layout_with_assets", [
        ("SKILL.md", b"# Layout with assets\n", "text/markdown", "skill_definition"),
        ("assets/logo.png", PICTURE, "image/png", "skill_asset")],
        attributes={"domain": ["design"], "origin_layer": "context_intelligence", "batch": "internal batch"})


class _Served:
    """What `running_http` reads from a fixture: one runtime and one provisioning binding."""

    def __init__(self, case):
        self.case, self.runtime = case, case.runtime
        self.provisioning = case.binding()


def _application(served, refresh_seconds):
    from .http import ServiceHttpApplication
    from .http_auth import ServiceHttpAuthentication
    case = served.case

    def factory(configuration):
        service = ServiceHttpApplication(served.runtime, served.provisioning, configuration,
                                         ServiceHttpAuthentication())
        service.catalogue_refresher = CatalogueRefresher(
            served.provisioning, build=lambda current, token: next_view(
                current, token, case.config, case.settings, license_policy=case.license_policy,
                family_policy=case.family_policy),
            probe=lambda: state_token(case.config), journal=service.failure_journal,
            interval_seconds=refresh_seconds)
        return service
    return factory


def _serving_checks(check, root):
    import httpx
    case = Fixture(root)
    case._bytes = {"layout_with_assets": (b"# Layout with assets\n", PICTURE)}
    first = case.publish([case.line("clean_supplier_names", "# Clean supplier names\nalpha one\n",
                                    attributes={"domain": ["data"], "batch": "internal batch"}),
                          _package_line()])
    served = _Served(case)
    headers = {"Authorization": "Bearer " + case.key.key}
    with running_http(served, application_factory=_application(served, 0.05)) as (base, service):
        with httpx.Client(base_url=base, headers=headers, trust_env=False, timeout=5) as client:
            def search(query, **fields):
                return client.post("/api/v1/retrieval", json={"record_type": RETRIEVAL_REQUEST_VERSION,
                                                               "query": query, **fields})
            before = search("supplier names").json()["result"]
            second = case.publish([case.line("clean_supplier_names", "# Clean supplier names\nalpha one\n",
                                             attributes={"domain": ["data"], "batch": "internal batch"}),
                                   _package_line(), case.line("rank_new_candidates", "# Rank new candidates\n",
                                                              attributes={"domain": ["ranking"]})])
            deadline = time.monotonic() + 5
            while served.provisioning.current_view().release_id != second["release_id"] and time.monotonic() < deadline:
                time.sleep(0.02)
            found = search("rank new candidates").json()["result"]
            fetched = client.post("/api/v1/download", json=provisioning_request(
                "read", identity="rank_new_candidates", request_id="first-download"))
            health = client.get("/api/v1/health").json()["result"]
            check("a_published_item_is_searched_and_downloaded_over_http_without_a_redeploy",
                  before["catalogue_release"] == first["release_id"]
                  and found["catalogue_release"] == second["release_id"]
                  and found["hits"][0]["reference"]["identity"] == "rank_new_candidates"
                  and fetched.status_code == 200 and fetched.content == b"# Rank new candidates\n"
                  and health["catalogue_release"]["release_id"] == second["release_id"]
                  and health["catalogue_release"]["refresher"]["swaps"] >= 1
                  and any(row["name"] == "catalogue_view_current" and row["passed"] and not row["required"]
                          for row in health["checks"]))
            internal = search("supplier", filters={"batch": {"equals": "internal batch"}})
            undeclared = search("supplier", filters={"licence": {"equals": "MIT"}})
            filtered = search("supplier names design ranking", filters={"domain": {"equals": "data"}}).json()["result"]
            check("search_filters_only_on_public_filterable_attributes_and_shows_only_public_shown_ones",
                  internal.status_code == undeclared.status_code == 400
                  and internal.json()["error"]["code"] == undeclared.json()["error"]["code"] == "search_filter_not_allowed"
                  and [hit["reference"]["identity"] for hit in filtered["hits"]] == ["clean_supplier_names"]
                  and filtered["hits"][0]["attributes"] == {"domain": ["data"]}
                  and "internal batch" not in json.dumps(filtered))
            document = client.post("/api/v1/download", json=provisioning_request(
                "read", identity="layout_with_assets", request_id="package-read"))
            picture = client.post("/api/v1/download", json=provisioning_request(
                "read", identity="layout_with_assets", request_id="package-read", path="assets/logo.png"))
            missing = client.post("/api/v1/download", json=provisioning_request(
                "read", identity="layout_with_assets", request_id="package-read", path="assets/absent.png"))
            inline = client.post("/api/v1/provisioning", json=provisioning_request(
                "read", identity="layout_with_assets", request_id="package-read", path="assets/logo.png"))
            usage = case.runtime.usage_for(case.runtime.authenticate_key(case.key.key))
            listed = json.loads(document.content)
            check("a_package_file_of_any_type_is_downloaded_by_path_with_its_own_digest_and_one_charge",
                  document.status_code == picture.status_code == 200
                  and document.headers["x-content-sha256"] == sha256_hex(document.content)
                  and [row["path"] for row in listed["files"]] == ["SKILL.md", "assets/logo.png"]
                  and picture.content == PICTURE and picture.headers["x-content-sha256"] == sha256_hex(PICTURE)
                  and missing.status_code == 404 and missing.json()["error"]["code"] == "package_file_not_found"
                  and inline.status_code == 400
                  and inline.json()["error"]["code"] == "package_file_requires_download"
                  and usage["records"] == 2)
            _mid_flight_checks(check, case, served, client)


def _mid_flight_checks(check, case, served, client):
    """A request that started before a swap is answered wholly from the view it started with."""
    third = case.publish([case.line("clean_supplier_names", "# Clean supplier names\nalpha three\n",
                                    attributes={"domain": ["data"]})])
    old_view = served.provisioning.current_view()
    new_view = case.view()
    original = DurableProvisioningBinding.invoke_for_principal

    def download_across_a_swap(counter):
        served.provisioning.install_view(old_view)

        def swapping(self, principal, operation, **fields):
            result = original(self, principal, operation, **fields)
            if operation == "manifest":
                self.install_view(new_view)
            return result
        with patch.object(DurableProvisioningBinding, "invoke_for_principal", swapping):
            answer = client.post("/api/v1/download", json=provisioning_request(
                "read", identity="clean_supplier_names", request_id=f"across-swap-{counter}"))
        return answer.status_code == 200 and answer.content == b"# Clean supplier names\nalpha one\n"
    check("a_request_in_flight_finishes_on_the_view_it_started_with",
          new_view.release_id == third["release_id"] and download_across_a_swap(1))
    ignoring = original

    def current_view_only(self, principal, operation, *, view=None, **fields):
        return ignoring(self, principal, operation, **fields)
    with patch.object(DurableProvisioningBinding, "invoke_for_principal", current_view_only):
        original = current_view_only
        check("removed_one_view_for_each_request_rule_is_detected", not download_across_a_swap(2))


def _command_checks(check, root):
    """The operator commands answer through the service entry point, and apply-grants keeps a following account."""
    from . import catalogue_grants
    from .http_entrypoint import apply_host_grants, load_host_application, main
    from .catalogue_bundle import write_bundle
    from .catalogue_schema import CatalogueAttributeSchema
    from .runtime import GRANTS
    case = Fixture(root)
    image = case.root / "image"
    (image / "bodies").mkdir(parents=True)
    body = b"# Packaged item\n"
    (image / "bodies" / "packaged.md").write_bytes(body)
    reference = bundle_line("packaged_item", [("SKILL.md", body, "text/markdown", "skill_definition")])["reference"]
    (image / "manifest.json").write_text(json.dumps({
        "record_type": "host_attested_intelligence_manifest/v1", "artifact_root": str(image),
        "items": [{"reference": reference, "body_path": "bodies/packaged.md", "approval_ref": "review:packaged",
                   "grants": [{"tenant_id": "alpha", "body_allowed": True, "metering": "required"}]}]}))
    host = case.root / "host.json"
    configuration = {"record_type": "service_http_host_configuration/v1",
                     "runtime": {"database_path": case.config.database_path, "writes_authorized": True},
                     "http": {"public_base_url": "http://127.0.0.1:8080", "allowed_hosts": ["127.0.0.1:8080"],
                              "allow_loopback_http": True},
                     "authentication": {}, "manifest_path": str(image / "manifest.json"),
                     "catalogue": {"record_type": "service_catalogue_source/v1", "source": "store",
                                   "body_store_root": str(case.root / "bodies"), "refresh_seconds": 5}}
    host.write_text(json.dumps(configuration))
    bundle = case.root / "command-bundle"
    digest = write_bundle(bundle, schema=CatalogueAttributeSchema.from_dict(SCHEMA),
                          lines=[bundle_line("command_item", [("SKILL.md", b"# Command\n", "text/markdown",
                                                               "skill_definition")])], payloads=[b"# Command\n"])

    def command(*arguments):
        printed = io.StringIO()
        try:
            with redirect_stdout(printed):
                status_code = main([*arguments, "--config", str(host)])
            return status_code, json.loads(printed.getvalue())
        except (SystemExit, ValueError, Exception) as error:  # noqa: BLE001 - a refusal is an answer here
            return None, getattr(error, "code", str(error))
    wrong = command("publish-catalogue", "--bundle", str(bundle), "--expected-bundle-digest", "0" * 64)
    published = command("publish-catalogue", "--bundle", str(bundle), "--expected-bundle-digest", digest)
    reported = command("catalogue-status")
    application, _configuration = load_host_application(str(host))
    check("the_catalogue_commands_answer_through_the_service_entry_point",
          wrong == (None, "bundle_digest_mismatch") and published[0] == 0 and published[1]["state"] == "published"
          and reported[1]["active_release_id"] == published[1]["release_id"]
          and application.provisioning.current_view().release_id == published[1]["release_id"]
          and application.catalogue_refresher is not None
          and application.catalogue_refresher.interval_seconds == 5)
    withdrawn = command("withdraw-catalogue-item", "--identity", "command_item", "--note", "operator check")
    followed = command("follow-catalogue-release", "--all-tenants")
    check("withdraw_and_follow_answer_through_the_service_entry_point",
          withdrawn[1]["state"] == "withdrawn" and followed[1]["tenants"] == ["alpha"])

    def keeps_following():
        answered = apply_host_grants(str(host))
        with case.runtime._catalog.store() as store:
            record = case.runtime._catalog.read(store, GRANTS, "alpha")["payload"]["record_type"]
        return answered["following_release_tenants"] == ["alpha"] and record == "service_grants/v2"
    check("apply_grants_keeps_a_following_account_on_its_engine", keeps_following())
    with patch.object(catalogue_grants, "following_release", lambda runtime, tenant: None):
        check("removed_following_account_rule_is_detected", not keeps_following())
    check("a_rollback_needs_the_release_it_expects",
          command("rollback-catalogue", "--to-release", published[1]["release_id"],
                  "--expected-release", "0" * 64)[1] == "catalogue_pointer_moved")
    check("a_catalogue_command_is_refused_without_the_catalogue_section",
          refused(lambda: _without_section(host, configuration)))


def _without_section(host, configuration):
    from .catalogue_commands import operator_context
    host.write_text(json.dumps({key: value for key, value in configuration.items() if key != "catalogue"}))
    try:
        operator_context(str(host))
    finally:
        host.write_text(json.dumps(configuration))


def run_checks(check, root):
    folder = Path(root)
    (folder / "serving").mkdir()
    (folder / "commands").mkdir()
    _serving_checks(check, folder / "serving")
    _command_checks(check, folder / "commands")
