"""Credential reuse checks use fake keyring records, never live secrets."""
from __future__ import annotations

from contextlib import redirect_stdout, redirect_stderr
import copy
import io
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import operator_credentials as tool


class Item:
    def __init__(self, value, label="fixture|entry@Codex MCP Credentials"):
        self.value = value; self.label = label; self.writes = 0
    def get_label(self): return self.label
    def get_secret(self): return self.value
    def set_secret(self, value): self.value = value; self.writes += 1


class Saved:
    def __init__(self, items): self.items = items
    def get_all_items(self): return self.items
    def search_items(self, attrs): return self.items
    def create_item(self, label, attrs, value, replace=False):
        if replace:raise AssertionError("overwrite forbidden")
        self.items.append(Item(value,label))


class KeyItem(Item):
    """A saved service key with the attributes the keyring holds beside it."""
    def __init__(self, value, attributes):
        super().__init__(value, "Baltor operator / baltor-pilot-owner"); self.attributes = dict(attributes)
    def get_attributes(self): return dict(self.attributes)


KEY_ATTRIBUTES = {"application": "loop-engine", "service": "baltor-pilot.fly.dev", "account": "pilot-owner",
                  "purpose": "service-access", "xdg:schema": "org.freedesktop.Secret.Generic"}


class CredentialTests(unittest.TestCase):
    def test_secondary_research_references_do_not_alias_primary_credentials(self):
        references = tool.references()["api_keys"]
        for primary, secondary in (("anthropic-model-primary", "anthropic-model-secondary"),
                                   ("rapidapi-reddit34-primary", "rapidapi-owner-secondary"),
                                   ("rapidapi-reddit34-primary", "rapidapi-owner-third"),
                                   ("rapidapi-owner-secondary", "rapidapi-owner-third"),
                                   ("rapidapi-owner-third", "rapidapi-owner-fourth"),
                                   ("rapidapi-owner-secondary", "rapidapi-owner-fourth")):
            first, second = references[primary], references[secondary]
            self.assertNotEqual(tuple(first[name] for name in ("service", "account", "purpose")),
                                tuple(second[name] for name in ("service", "account", "purpose")))
            self.assertEqual(first["environment"], second["environment"])
            self.assertNotIn("value", second)
            self.assertNotIn("token", second)

    def test_research_references_resolve_separate_fake_keyring_items(self):
        names = ("rapidapi-reddit34-primary", "rapidapi-owner-secondary", "rapidapi-owner-third",
                 "rapidapi-owner-fourth")
        data = tool.references()
        rows = [KeyItem(("fixture-research-" + str(index)).encode(), {
            "application": "loop-engine", **{field: data["api_keys"][name][field]
            for field in ("service", "account", "purpose")}}) for index, name in enumerate(names)]
        saved = Saved(rows)
        def matching(attributes):
            return [item for item in rows if item.get_attributes() == attributes]
        with patch.object(saved, "search_items", side_effect=matching), patch.object(
                tool, "collection", side_effect=AssertionError("live keyring not authorized")):
            resolved = [tool.resolve(name, saved, data) for name in names]
        self.assertEqual(resolved, ["fixture-research-" + str(index) for index in range(len(names))])
        self.assertTrue(all(item.writes == 0 for item in rows))

    def test_third_reference_selects_its_own_fake_keyring_record(self):
        data = tool.references()
        items = []
        for name in ("rapidapi-owner-secondary", "rapidapi-owner-third"):
            spec = data["api_keys"][name]
            attributes = {"application": "loop-engine", **{
                key: spec[key] for key in ("service", "account", "purpose")}}
            items.append(KeyItem(("fixture-value-for-" + name).encode(), attributes))

        class ScopedSaved(Saved):
            def search_items(self, attributes):
                return [item for item in self.items if all(
                    item.get_attributes().get(key) == value for key, value in attributes.items())]

        with patch.object(tool, "collection", side_effect=AssertionError("live keyring forbidden")), \
                patch.object(tool, "request_refresh", side_effect=AssertionError("provider forbidden")):
            self.assertEqual(tool.resolve("rapidapi-owner-third", ScopedSaved(items), data),
                             "fixture-value-for-rapidapi-owner-third")

    def test_third_reference_audit_exception_is_exact_and_known_bad_values_still_block(self):
        root = Path(__file__).resolve().parents[1]
        sys.path.insert(0, str(root / "devtools" / "src"))
        from loop_engine_devtools.assurance.hardcoding import (
            AuditRequest, compare_with_baseline, load_audit_finding_ids, new_findings_at_or_above, scan_hardcoding,
        )
        allowlist = root / "devtools/hardcoding-allowlist.yaml"
        baseline = load_audit_finding_ids(root / "devtools/hardcoding-ci-baseline.json")
        spec = tool.references()["api_keys"]["rapidapi-owner-third"]
        with TemporaryDirectory(prefix="credential-reference-audit-") as temporary:
            fixture = Path(temporary)
            (fixture / "pyproject.toml").write_text("[project]\nname='loop-engine'\nversion='0.0.0'\n")
            (fixture / "tools").mkdir()
            manifest = fixture / "tools/operator_credentials.json"

            def audit(value, *, exceptions=allowlist):
                manifest.write_text(json.dumps(value))
                report = scan_hardcoding(AuditRequest(fixture, allowlist_path=exceptions,
                    source_prefixes=("tools/operator_credentials.json",)))
                delta = compare_with_baseline(report, baseline)
                return report, new_findings_at_or_above(delta, report, "high")

            valid = {"record_type": "operator_credential_references/v1", "api_keys": {"rapidapi-owner-third": spec}}
            report, blocking = audit(valid)
            self.assertEqual(blocking, ())
            target = next(row for row in report["findings"]
                          if row["symbol_ref"] == "api_keys.rapidapi-owner-third.environment")
            self.assertEqual(target["classification"], "SECRET_OR_CREDENTIAL_REFERENCE")
            self.assertEqual(target["severity"], "high")
            self.assertTrue(target["suppressed"], "the reviewed finding stays visible")
            self.assertTrue(audit(valid, exceptions=None)[1], "removing the exact exception must expose the finding")
            changed = copy.deepcopy(valid)
            changed["api_keys"]["rapidapi-owner-third"]["environment"] = "UNREVIEWED_API_KEY"
            self.assertTrue(audit(changed)[1], "another environment name cannot inherit this review")
            changed = copy.deepcopy(valid)
            changed["api_keys"]["unreviewed-reference"] = dict(spec)
            self.assertTrue(audit(changed)[1], "another owner cannot inherit this review")
            changed = copy.deepcopy(valid)
            changed["api_keys"]["rapidapi-owner-third"]["environment"] = "Bearer " + "fixture-shaped-value-not-a-secret"
            report, blocking = audit(changed)
            self.assertTrue(blocking)
            secrets = [row for row in report["findings"] if row["finding_id"] in blocking]
            self.assertTrue(any(row["severity"] == "critical" and row["sensitive_value_redacted"]
                                and row["literal_preview"] == "<redacted>" for row in secrets))

    def test_reddit_inventory_alias_reuses_the_native_reader_keyring_identity(self):
        from knowledge_radar.rapidapi_reddit import REFERENCE
        spec = tool.references()["api_keys"]["rapidapi-reddit34-primary"]
        self.assertEqual({"application": "loop-engine", **{
            name: spec[name] for name in ("service", "account", "purpose")}}, REFERENCE)

    def setUp(self):
        self.data = tool.references()
        self.spec = self.data["oauth"]["resend-management"]
        self.held = {"server_name": self.spec["server_name"], "issuer": self.spec["issuer"],
                     "url": self.spec["url"], "client_id": "fixture-public-client",
                     "expires_at": 2000000000000,
                     "token_response": {"access_token": "fixture-access", "refresh_token": "fixture-refresh",
                                        "token_type": "Bearer", "scope": "read write", "expires_in": 1000}}
        self.item = Item(json.dumps(self.held).encode(), self.spec["server_name"]+"|fixture@Codex MCP Credentials")

    def test_configuration_contains_helpers_not_secrets_or_static_headers(self):
        config = tool.claude_configuration()
        self.assertEqual(len(config["mcpServers"]), 6)
        for name, row in config["mcpServers"].items():
            self.assertNotIn("headers", row)
            self.assertNotIn("env", row)
            if row["type"] == "http" and name not in self.data["native_mcp"]:
                self.assertIn("headers " + name, row["headersHelper"])

    def test_key_facts_read_the_recorded_identity_and_expiry_never_the_key(self):
        secret = b"le_fixture_service_key_that_is_never_a_fact_000000"
        item = KeyItem(secret, {**KEY_ATTRIBUTES, "key_id": "a" * 32, "expires_at": "1791848094",
                                "issued_at": "1791243294", "token": secret.decode()})
        facts = tool.key_facts("baltor-pilot-owner", Saved([item]), self.data)
        self.assertEqual(facts, {"key_id": "a" * 32, "expires_at": 1791848094, "issued_at": 1791243294})
        self.assertNotIn(secret.decode(), json.dumps(facts), "an attribute outside the facts is never returned")

    def test_known_wrong_key_facts_leave_out_what_is_not_in_its_exact_form(self):
        # A key saved by hand, or before the renewal wrote its facts, answers no expiry instead of a guess.
        item = KeyItem(b"le_value", {**KEY_ATTRIBUTES, "key_id": "not-a-key-id", "expires_at": "soon"})
        self.assertEqual(tool.key_facts("baltor-pilot-owner", Saved([item]), self.data), {})
        self.assertEqual(tool.key_facts("baltor-pilot-owner", Saved([KeyItem(b"le_value", KEY_ATTRIBUTES)]), self.data), {})
        with self.assertRaisesRegex(tool.CredentialError, "only_service_access"):
            tool.key_facts("stripe-test", Saved([item]), self.data)

    def test_native_authorization_stays_with_client_and_exports_no_token(self):
        config=tool.claude_configuration()["mcpServers"]["baltor-namecheap"]
        self.assertEqual(config,self.data["native_mcp"]["baltor-namecheap"])
        self.assertNotIn("headersHelper",config)
        self.assertEqual(config["oauth"]["authServerMetadataUrl"],
                         "https://www.namecheap.com/.well-known/oauth-authorization-server")

    def test_native_configuration_refuses_secret_fields_and_name_collisions(self):
        for change in ("headers","collision","insecure"):
            data=copy.deepcopy(self.data)
            native=data["native_mcp"]["baltor-namecheap"]
            if change=="headers":native["headers"]={"Authorization":"fixture"}
            elif change=="collision":data["native_mcp"]["baltor-resend"]=native
            else:native["oauth"]["authServerMetadataUrl"]="http://unrelated.invalid"
            with self.assertRaises(tool.CredentialError):tool.claude_configuration(data)

    def test_helper_refuses_wrong_url_before_reading_credentials(self):
        called = []
        with self.assertRaisesRegex(tool.CredentialError, "unbound"):
            tool.headers("baltor-resend", {"CLAUDE_CODE_MCP_SERVER_NAME":"baltor-resend",
                         "CLAUDE_CODE_MCP_SERVER_URL":"https://unrelated.invalid"}, lambda ref:called.append(ref))
        self.assertEqual(called, [])

    def test_helper_refuses_missing_or_wrong_server_name(self):
        for env in ({}, {"CLAUDE_CODE_MCP_SERVER_NAME":"another", "CLAUDE_CODE_MCP_SERVER_URL":self.spec["url"]}):
            with self.assertRaises(tool.CredentialError): tool.headers("baltor-resend", env)

    def test_changed_connection_url_cannot_redirect_a_valid_provider_credential(self):
        data=copy.deepcopy(self.data);data["mcp"]["baltor-resend"]["url"]="https://unrelated.invalid"
        called=[]
        with self.assertRaisesRegex(tool.CredentialError,"destination_mismatch"):
            tool.headers("baltor-resend",{"CLAUDE_CODE_MCP_SERVER_NAME":"baltor-resend",
                         "CLAUDE_CODE_MCP_SERVER_URL":"https://unrelated.invalid"},lambda ref:called.append(ref),data)
        self.assertEqual(called,[])

    def test_test_mode_profile_refuses_non_test_credential(self):
        spec=self.data["api_keys"]["stripe-test"]
        with self.assertRaisesRegex(tool.CredentialError,"mode_or_type"):
            tool.validate_api_token("fixture-not-a-test-credential",spec)
        self.assertEqual(tool.validate_api_token("sk_test_fixture_only",spec),"sk_test_fixture_only")

    def test_bound_helper_resolves_only_selected_reference(self):
        called=[]
        def resolver(ref): called.append(ref); return "fixture-access"
        result=tool.headers("baltor-resend", {"CLAUDE_CODE_MCP_SERVER_NAME":"baltor-resend",
                            "CLAUDE_CODE_MCP_SERVER_URL":self.spec["url"]}, resolver)
        self.assertEqual(result,{"Authorization":"Bearer fixture-access"})
        self.assertEqual(called,["resend-management"])

    def test_missing_and_ambiguous_records_refuse(self):
        for saved in (Saved([]),Saved([self.item,self.item])):
            with self.assertRaises(tool.CredentialError): tool.select_item(saved,"resend-management",self.data)

    def test_saved_grant_binding_must_match_provider_and_project(self):
        for key in ("issuer","url","server_name"):
            bad={**self.held,key:"wrong"}
            with self.assertRaises(tool.CredentialError): tool.validated_oauth(Item(json.dumps(bad).encode()),self.spec)

    def test_header_control_characters_refuse(self):
        for value in ("",None,"fixture\nInjected: header","fixture\x00token","sb_secret_masked\u00b7\u00b7\u00b7"):
            with self.assertRaises(tool.CredentialError): tool.clean_token(value)

    def test_masked_modern_key_cannot_become_a_usable_reference(self):
        spec=self.data["api_keys"]["supabase-secret"]
        for value in ("sb_secret_partial...hidden", "sb_secret_****", "sb_secret_short"):
            with self.assertRaises(tool.CredentialError):tool.validate_api_token(value,spec)

    def test_required_write_scope_cannot_use_a_read_only_grant(self):
        spec={**self.spec,"required_scopes":["write"]}
        self.assertEqual(tool.validated_oauth(self.item,spec),self.held)
        read_only={**self.held,"token_response":{**self.held["token_response"],"scope":"read"}}
        with self.assertRaisesRegex(tool.CredentialError,"scopes_not_granted"):
            tool.validated_oauth(Item(json.dumps(read_only).encode()),spec)

    def test_unexpired_grant_does_not_refresh_or_write(self):
        with patch.object(tool,"request_refresh",side_effect=AssertionError("network not permitted")):
            self.assertEqual(tool.resolve("resend-management",Saved([self.item]),self.data),"fixture-access")
        self.assertEqual(self.item.writes,0)

    def test_refresh_rotates_in_same_item_and_preserves_binding(self):
        result=tool.renew(self.item,self.spec,self.held,1000,
                          lambda *_:{"token_type":"Bearer","access_token":"new-fixture","refresh_token":"rotated-fixture","expires_in":3600,"scope":"read"})
        saved=json.loads(self.item.get_secret())
        self.assertEqual(saved,result);self.assertEqual(saved["expires_at"],4600000)
        self.assertEqual(saved["client_id"],self.held["client_id"]);self.assertEqual(self.item.writes,1)

    def test_absent_rotated_refresh_token_keeps_original(self):
        result=tool.renew(self.item,self.spec,self.held,1000,
                          lambda *_:{"token_type":"Bearer","access_token":"new-fixture","expires_in":3600})
        self.assertEqual(result["token_response"]["refresh_token"],"fixture-refresh")

    def test_refresh_cannot_drop_required_scopes_and_return_a_usable_token(self):
        before=self.item.get_secret()
        spec={**self.spec,"required_scopes":["write"]}
        with self.assertRaisesRegex(tool.CredentialError,"scopes_not_granted"):
            tool.renew(self.item,spec,self.held,1000,
                       lambda *_:{"token_type":"Bearer","access_token":"new-fixture","expires_in":3600,"scope":"read"})
        self.assertEqual(self.item.get_secret(),before)
        self.assertEqual(self.item.writes,0)

    def test_malformed_broader_or_redirected_refresh_never_writes(self):
        base={"token_type":"Bearer","access_token":"new-fixture","expires_in":3600}
        for extra in ({"expires_in":True},{"expires_in":-1},{"token_type":"other"},{"access_token":""},
                      {"scope":"read write administrator"},{"resource":"https://unrelated.invalid"}):
            with self.assertRaises(tool.CredentialError):
                tool.renew(self.item,self.spec,self.held,1000,lambda *_,v={**base,**extra}:v)
        self.assertEqual(self.item.writes,0)

    def test_refresh_failure_does_not_clear_prior_grant(self):
        def fail(*_): raise tool.CredentialError("token_refresh_refused_400")
        before=self.item.get_secret()
        with self.assertRaises(tool.CredentialError):tool.renew(self.item,self.spec,self.held,1000,fail)
        self.assertEqual(self.item.get_secret(),before)

    def test_child_gets_secret_in_environment_not_arguments_and_output_is_redacted(self):
        captured=[]
        def run(command,**kwargs):
            captured.append((command,kwargs));return subprocess.CompletedProcess(command,0,"fixture-secret","fixture-secret")
        stdout,stderr=io.StringIO(),io.StringIO()
        with patch.object(tool,"resolve",return_value="fixture-secret"),patch.object(tool.subprocess,"run",side_effect=run),redirect_stdout(stdout),redirect_stderr(stderr):
            result=tool.run_with_credentials(["stripe-test"],["trusted-command","get"],10)
        self.assertEqual(result,0);self.assertNotIn("fixture-secret",repr(captured[0][0]))
        self.assertEqual(captured[0][1]["env"]["STRIPE_API_KEY"],"fixture-secret")
        self.assertNotIn("fixture-secret",stdout.getvalue()+stderr.getvalue())

    def test_conflicting_environment_targets_do_not_run(self):
        with patch.object(tool,"resolve",return_value="fixture-secret"),patch.object(tool.subprocess,"run") as child:
            with self.assertRaises(tool.CredentialError):
                tool.run_with_credentials(["baltor-pilot-owner","baltor-pilot-boundary"],["command"],10)
            child.assert_not_called()

    def test_timeout_is_unknown_outcome_and_no_automatic_retry(self):
        with patch.object(tool,"resolve",return_value="fixture-secret"),patch.object(tool.subprocess,"run",side_effect=subprocess.TimeoutExpired("command",1)) as child:
            with self.assertRaisesRegex(tool.CredentialError,"outcome_unknown"):
                tool.run_with_credentials(["stripe-test"],["command"],1)
            self.assertEqual(child.call_count,1)

    def test_private_store_creates_and_confirms_one_named_key(self):
        saved=Saved([])
        tool.store_api_reference("cloudflare-dns","fixture-domain-secret",saved,self.data)
        self.assertEqual(len(saved.items),1)
        self.assertEqual(saved.items[0].get_secret(),b"fixture-domain-secret")

    def test_private_store_preserves_existing_keys_and_refuses_oauth_records(self):
        saved=Saved([Item(b"existing-fixture")])
        for reference in ("cloudflare-dns","resend-management"):
            with self.assertRaises(tool.CredentialError):tool.store_api_reference(reference,"new-fixture",saved,self.data)
        self.assertEqual(saved.items[0].get_secret(),b"existing-fixture")


if __name__ == "__main__":
    unittest.main()
