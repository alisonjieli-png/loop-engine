"""Loopback checks for serving catalogue releases: hot swap, schema search, package files and commands.

A real service answers on a loopback socket over a real temporary store and
body folder. A release is published while it runs and reaches search and
download without a restart. A request that started before a swap finishes on
the view it started with. No provider or external network is used.

The runbook's first catalogue release, and the live repair of September 23,
2026, are replayed through the service entry point with a host file: an
account the packaged manifest does not grant must hold no grant to any item,
including an item published afterwards.
"""
from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
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
    followed = command("follow-catalogue-release", "--tenant", "alpha")
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


#: The first-time follow step of the runbook section "Publish and roll back a
#: catalogue release", as the service entry point receives it after
#: `--config`. `tools/test_catalogue_release_runbook.py` requires the runbook
#: to document exactly this step, so the procedure replayed here is the one an
#: operator reads.
FIRST_RELEASE_FOLLOW_STEP = ("follow-catalogue-release", "--tenant", "pilot-owner")
#: The same step as the runbook documented it for release 17, which moved
#: every account on the live Machine on September 23, 2026.
RELEASE_17_FOLLOW_STEP = ("follow-catalogue-release", "--all-tenants")
OWNER, ISOLATED, BILLING = "pilot-owner", "pilot-boundary", "billing-check"
FIRST_ITEMS = {"clean_supplier_names": b"# Clean supplier names\n", "profile_one_column": b"# Profile one column\n"}
LATER_ITEM = ("rank_new_candidates", b"# Rank new candidates\n")


class RunbookHost:
    """A host as a deployed image leaves it before the runbook's first catalogue release.

    The packaged manifest grants its items to the owner account alone, the way
    the pilot manifest is built with `--grant pilot-owner:bodies:required`.
    `configure` registered the owner, the isolation account and a billing check
    account, and `apply-grants` gave the owner the manifest's items. Every
    later step goes through the service entry point with the host file, as an
    operator runs it on the Machine.
    """

    def __init__(self, root):
        from .catalogue_bundle import write_bundle
        self.root, self.count, self.write_bundle = Path(root).resolve(), 0, write_bundle
        image = self.root / "image"
        (image / "bodies").mkdir(parents=True)
        (self.root / "bodies").mkdir()
        items = []
        for identity, body in FIRST_ITEMS.items():
            (image / "bodies" / (identity + ".md")).write_bytes(body)
            items.append({"reference": self.line(identity, body)["reference"], "body_path": f"bodies/{identity}.md",
                          "approval_ref": "review:" + identity,
                          "grants": [{"tenant_id": OWNER, "body_allowed": True, "metering": "required"}]})
        (image / "manifest.json").write_text(json.dumps({
            "record_type": "host_attested_intelligence_manifest/v1", "artifact_root": str(image), "items": items}))
        until = int(time.time()) + 3600
        entitled = {"valid_until": until, "evidence_ref": "local-check-not-payment"}
        self.host = self.root / "host.json"
        self.configuration = {
            "record_type": "service_http_host_configuration/v1",
            "runtime": {"database_path": str(self.root / "service.db"), "writes_authorized": True},
            "http": {"public_base_url": "http://127.0.0.1:8080", "allowed_hosts": ["127.0.0.1:8080"],
                     "allow_loopback_http": True},
            "authentication": {}, "manifest_path": str(image / "manifest.json"),
            "tenants": [{"tenant_id": OWNER, "namespace": "tenant:" + OWNER, "operator_entitlement": entitled},
                        {"tenant_id": ISOLATED, "namespace": "tenant:" + ISOLATED, "operator_entitlement": entitled},
                        {"tenant_id": BILLING, "namespace": "tenant:" + BILLING}]}
        self.save()
        self.run("configure")
        self.run("apply-grants")
        from .records import ServiceRuntimeConfig, TenantKeyIssue
        from .runtime import ServiceRuntime
        self.runtime = ServiceRuntime(ServiceRuntimeConfig(**self.configuration["runtime"]))
        self.keys = {tenant: self.runtime.issue_key(TenantKeyIssue(tenant, "runbook check")).key
                     for tenant in (OWNER, ISOLATED, BILLING)}

    @staticmethod
    def line(identity, body):
        return bundle_line(identity, [("SKILL.md", body, "text/markdown", "skill_definition")])

    def save(self):
        self.host.write_text(json.dumps(self.configuration))

    def run(self, *arguments):
        """One operator command through the service entry point: its exit status and record, or its refusal."""
        from .http_entrypoint import main
        printed = io.StringIO()
        try:
            with redirect_stdout(printed):
                status = main([*arguments, "--config", str(self.host)])
            return status, json.loads(printed.getvalue())
        except (SystemExit, Exception) as error:  # noqa: BLE001 - a refusal is an answer here
            return None, getattr(error, "code", str(error))

    def catalogue_source(self, source):
        """Once-before step 2 names the image source; first-release step 6 moves it to the store."""
        self.configuration["catalogue"] = {"record_type": "service_catalogue_source/v1", "source": source,
                                           "body_store_root": str(self.root / "bodies"), "refresh_seconds": 60,
                                           "new_accounts_follow_release": False}
        self.save()

    def publish(self, items):
        from .catalogue_schema import CatalogueAttributeSchema
        self.count += 1
        folder = self.root / f"incoming-{self.count}"
        digest = self.write_bundle(folder, schema=CatalogueAttributeSchema.from_dict(SCHEMA),
                                   lines=[self.line(identity, body) for identity, body in items.items()],
                                   payloads=list(items.values()))
        return self.run("publish-catalogue", "--bundle", str(folder), "--expected-bundle-digest", digest)

    def first_release(self, follow_step):
        """The runbook's first-time procedure: section, first publish, store source, the follow step."""
        self.catalogue_source("image")
        self.publish(FIRST_ITEMS)
        self.catalogue_source("store")
        return self.run(*follow_step)

    def served(self):
        """What each account is offered by the application the host file starts, and one refused read."""
        from .http_entrypoint import load_host_application
        from .runtime import GRANTS
        application, _configuration = load_host_application(str(self.host))
        offered = {tenant: sorted(row["identity"] for row in application.provisioning.invoke(key, "list")["items"])
                   for tenant, key in self.keys.items()}
        records = {}
        with self.runtime._catalog.store() as store:
            for tenant in self.keys:
                row = self.runtime._catalog.read(store, GRANTS, tenant)
                records[tenant] = row["payload"] if row is not None else None
        read = refused(lambda: application.provisioning.invoke(self.keys[ISOLATED], "read", identity=LATER_ITEM[0],
                                                               request_id="isolation-read"))
        return {"offered": offered, "records": records, "isolated_read_refused": read}


def _ungranted_accounts_hold_nothing(outcome):
    """The isolation account and the billing check account hold no grant, and the owner still follows."""
    if not isinstance(outcome, dict):
        return False
    empty = all(outcome["records"][tenant] is None
                or (outcome["records"][tenant]["record_type"] == "service_grants/v1"
                    and outcome["records"][tenant]["grants"] == [])
                for tenant in (ISOLATED, BILLING))
    return (empty and outcome["offered"][ISOLATED] == [] and outcome["offered"][BILLING] == []
            and outcome["isolated_read_refused"]
            and outcome["offered"][OWNER] == sorted([*FIRST_ITEMS, LATER_ITEM[0]]))


def _release_17_rules():
    """Release 17's `--all-tenants`, which moved every registered account whatever it held."""
    from . import catalogue_grants
    return patch.object(catalogue_grants, "left_out_reason", lambda *arguments: "")


#: What an operator runs on the live Machine after the release that carries
#: the repair: the workflow's `apply-grants`, then one stop for each account
#: that follows the release and must not.
LIVE_REPAIR = (("apply-grants",),
               *(("stop-following-catalogue-release", "--tenant", tenant) for tenant in (ISOLATED, BILLING)))


def _procedure(root, follow_step, *, incident=False, after=()):
    """Replay the first-time procedure, then `after`, a later deploy and a later release.

    With `incident`, the follow step runs under release 17's rules and every
    account that must not follow is then given the denials the live accounts
    were given on September 23, 2026: every item published so far.
    """
    try:
        host = RunbookHost(tempfile.mkdtemp(dir=root))
        if incident:
            with _release_17_rules():
                host.first_release(follow_step)
            denied = [argument for identity in sorted(FIRST_ITEMS) for argument in ("--deny", identity)]
            for tenant in (ISOLATED, BILLING):
                host.run("follow-catalogue-release", "--tenant", tenant, *denied)
        else:
            host.first_release(follow_step)
        for step in after:
            host.run(*step)
        # The release workflow applies the manifest grants after every deploy.
        host.run("apply-grants")
        host.publish({**FIRST_ITEMS, LATER_ITEM[0]: LATER_ITEM[1]})
        return host.served()
    except Exception:  # noqa: BLE001 - a procedure that stops part way is a failed check
        return None


def _runbook_checks(check, root):
    """The runbook's first catalogue release, replayed through the entry point, never widens an account."""
    from . import catalogue_grants
    check("the_documented_first_release_procedure_leaves_ungranted_accounts_with_nothing",
          _ungranted_accounts_hold_nothing(_procedure(root, FIRST_RELEASE_FOLLOW_STEP)))
    check("the_first_release_step_as_written_for_release_17_now_leaves_ungranted_accounts_with_nothing",
          _ungranted_accounts_hold_nothing(_procedure(root, RELEASE_17_FOLLOW_STEP)))
    try:
        with _release_17_rules():
            wrong = _procedure(root, RELEASE_17_FOLLOW_STEP)
    except AttributeError:
        wrong = None
    everything = sorted([*FIRST_ITEMS, LATER_ITEM[0]])
    check("the_release_17_procedure_under_release_17_rules_is_detected",
          isinstance(wrong, dict) and not _ungranted_accounts_hold_nothing(wrong)
          and wrong["offered"][ISOLATED] == everything)
    check("the_live_repair_empties_the_denied_accounts_and_keeps_the_owner_following",
          _ungranted_accounts_hold_nothing(_procedure(root, RELEASE_17_FOLLOW_STEP, incident=True, after=LIVE_REPAIR)))
    # Without the fixed list each account keeps following with the denials it
    # held, as the live accounts did after the mitigation, and the later item
    # reaches it.
    try:
        with patch.object(catalogue_grants, "snapshot_payload", lambda tenant_id, grants:
                          catalogue_grants.release_following_payload(tenant_id, sorted(FIRST_ITEMS))):
            left = _procedure(root, RELEASE_17_FOLLOW_STEP, incident=True, after=LIVE_REPAIR)
    except AttributeError:
        left = None
    check("removed_stop_following_snapshot_is_detected",
          isinstance(left, dict) and LATER_ITEM[0] in left["offered"][ISOLATED])
    try:
        host = RunbookHost(tempfile.mkdtemp(dir=root))
        host.first_release(FIRST_RELEASE_FOLLOW_STEP)
        answers = [host.run("stop-following-catalogue-release", "--all-tenants"),
                   host.run("stop-following-catalogue-release"),
                   host.run("stop-following-catalogue-release", "--tenant", OWNER, "--deny", "x"),
                   host.run("stop-following-catalogue-release", "--tenant", ISOLATED),
                   host.run("stop-following-catalogue-release", "--tenant", OWNER)]
    except Exception:  # noqa: BLE001 - a setup that stops part way is a failed check
        answers = []
    stopped = answers[-1][1] if answers and isinstance(answers[-1][1], dict) else {}
    check("stop_following_names_one_following_account_and_nothing_else",
          [answer[1] for answer in answers[:4]] == ["invalid_request", "invalid_request", "invalid_request",
                                                     "account_not_following_release"]
          and answers[-1][0] == 0 and stopped.get("tenants") == [OWNER] and stopped.get("grants") == len(FIRST_ITEMS))


def run_checks(check, root):
    folder = Path(root)
    (folder / "serving").mkdir()
    (folder / "commands").mkdir()
    (folder / "runbook").mkdir()
    _serving_checks(check, folder / "serving")
    _command_checks(check, folder / "commands")
    try:
        _runbook_checks(check, folder / "runbook")
    except Exception:  # noqa: BLE001 - a group that stops part way is a failure with a name
        check("the_runbook_checks_ran_to_completion", False)
