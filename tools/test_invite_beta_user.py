"""Invitation checks use injected transports only; no provider is contacted.

The scripted provider below stands in for the identity provider's
administration interface. The default transport is exercised through the HTTP
library's in-memory mock transport, so no socket is opened either. A passing
run proves the local contract of the command. It does not prove that the real
provider accepts the requests.
"""
from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import invite_beta_user as tool

ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs" / "guides" / "private-beta-operations.md"
PROJECT = "abcdefghijklmnopqrst"
PROJECT_ORIGIN = "https://" + PROJECT + ".supabase.co"
ORIGIN = "https://app.example.test"
REDIRECT = ORIGIN + "/auth/callback"
EMAIL = "invited.person@example.test"
USER_ID = "00000000-0000-4000-8000-000000000001"
OTHER_ID = "00000000-0000-4000-8000-000000000002"
NOW = datetime(2026, 9, 20, 12, 0, 0, tzinfo=timezone.utc)
# Assembled at run time so the source holds no key-shaped literal.
CREDENTIAL = "sb_secret_" + "fixture-only-" * 2 + "0000"
LINK_TOKEN = "f1" * 28
ONE_TIME_CODE = "482913"
MANIFEST = {"record_type": "operator_credential_references/v1", "api_keys": {
    "identity-admin": {"service": "supabase", "account": PROJECT, "purpose": "secret-api",
                       "environment": "FIXTURE_IDENTITY_ADMIN", "value_pattern": "sb_secret_[A-Za-z0-9_-]{20,128}"},
    "identity-public": {"service": "supabase", "account": PROJECT, "purpose": "publishable-api",
                        "environment": "FIXTURE_IDENTITY_PUBLIC", "value_pattern": "sb_publishable_[A-Za-z0-9_-]{20,128}"},
    "identity-legacy": {"service": "supabase", "account": PROJECT, "purpose": "secret-api",
                        "environment": "FIXTURE_IDENTITY_LEGACY"},
    "payments": {"service": "stripe", "account": "acct_fixture", "purpose": "secret-api",
                 "environment": "FIXTURE_PAYMENTS", "value_pattern": "sk_test_[A-Za-z0-9]{8,64}"}}}
ENVIRONMENT = {"FIXTURE_IDENTITY_ADMIN": CREDENTIAL,
               "FIXTURE_IDENTITY_PUBLIC": "sb_publishable_" + "fixture-only-" * 2 + "0000"}


def link_for(*, host=PROJECT + ".supabase.co", scheme="https", path="/auth/v1/verify", token=LINK_TOKEN,
             kind="recovery", redirect=REDIRECT, extra=""):
    return scheme + "://" + host + path + "?token=" + token + "&type=" + kind + "&redirect_to=" + redirect + extra


LINK = link_for()


def response(status, payload):
    body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
    return tool.AdministrationResponse(status, body)


def user(**changes):
    value = {"id": USER_ID, "aud": "authenticated", "role": "authenticated", "email": EMAIL,
             "email_confirmed_at": "2026-09-20T11:59:58.12345Z", "is_anonymous": False,
             "app_metadata": {"baltor_invitation": tool.INVITATION_MARK_VALUE}, "user_metadata": {}}
    value.update(changes)
    return value


def created(**changes):
    return response(200, user(**changes))


def exists(shape="legacy"):
    if shape == "legacy":
        return response(422, {"code": 422, "error_code": "email_exists", "msg": "fixture refusal"})
    return response(422, {"code": "email_exists", "message": "fixture refusal"})


def linked(link=LINK, **changes):
    value = {**user(), "action_link": link, "email_otp": ONE_TIME_CODE, "hashed_token": LINK_TOKEN,
             "verification_type": "recovery", "redirect_to": REDIRECT}
    value.update(changes)
    return response(200, value)


class Provider:
    """Scripted administration answers. Every request is recorded, none is sent."""

    def __init__(self, *steps):
        self.steps, self.requests = list(steps), []

    def __call__(self, request):
        self.requests.append(request)
        if not self.steps:
            raise AssertionError("an unexpected additional provider request was made")
        step = self.steps.pop(0)
        if isinstance(step, BaseException):
            raise step
        return step

    @property
    def paths(self):
        return [request.url[len(PROJECT_ORIGIN):] for request in self.requests]

    @property
    def bodies(self):
        return [json.loads(request.body) for request in self.requests]


class Run:
    """One command run in a private temporary folder with captured output."""

    def __init__(self, provider, *, arguments=None, remove=(), environment=None, confirm=True, report=None, extra=()):
        self.folder = tempfile.TemporaryDirectory(prefix="baltor-invitation-check-")
        self.report = Path(self.folder.name) / "report.json" if report is None else report
        values = {"--project-ref": PROJECT, "--email": EMAIL, "--service-origin": ORIGIN,
                  "--redirect-to": REDIRECT, "--report": str(self.report), "--credential-ref": "identity-admin"}
        values.update(arguments or {})
        argv = [item for name, value in values.items() if name not in remove for item in (name, value)]
        if confirm:
            argv.append("--acknowledge-identity-account-effects")
        argv.extend(extra)
        self.provider = provider
        stdout, stderr = io.StringIO(), io.StringIO()
        try:
            with redirect_stdout(stdout), redirect_stderr(stderr):
                try:
                    self.code = tool.main(argv, environment=ENVIRONMENT if environment is None else environment,
                                          transport=provider, manifest=MANIFEST, now=lambda: NOW)
                except SystemExit as stop:
                    self.code = stop.code
        except BaseException:
            self.folder.cleanup()
            raise
        self.stdout, self.stderr = stdout.getvalue(), stderr.getvalue()

    @property
    def record(self):
        return json.loads(self.report.read_text("utf-8"))

    def close(self):
        self.folder.cleanup()


class InvitationChecks(unittest.TestCase):
    def run_command(self, *steps, **options):
        run = Run(Provider(*steps), **options)
        self.addCleanup(run.close)
        return run

    def assert_nothing_happened(self, run):
        self.assertEqual(run.code, tool.EXIT_REFUSED_BEFORE_ANY_REQUEST, run.stderr)
        self.assertEqual(run.provider.requests, [])
        self.assertEqual(run.stdout, "")
        self.assertFalse(run.report.exists())

    def assert_no_secret(self, run, *texts):
        for text in (run.stderr, *texts):
            for secret in (LINK, LINK_TOKEN, ONE_TIME_CODE, CREDENTIAL, EMAIL):
                self.assertNotIn(secret, text)

    # Refusals before any request.

    def test_every_argument_is_required(self):
        for name in ("--project-ref", "--email", "--service-origin", "--redirect-to", "--report"):
            with self.subTest(name=name):
                run = self.run_command(created(), linked(), remove=(name,))
                self.assertEqual((run.code, run.provider.requests, run.stdout), (2, [], ""))

    def test_refusal_is_one_code_without_a_traceback_or_the_address(self):
        run = self.run_command(created(), linked(), arguments={"--service-origin": "http://app.example.test"})
        self.assertIn(run.stderr.strip(), tool.REFUSALS)
        self.assertNotIn(EMAIL, run.stderr)

    def test_non_https_service_origin_is_refused_before_any_request(self):
        for origin in ("http://app.example.test", "ftp://app.example.test", "app.example.test", "//app.example.test"):
            with self.subTest(origin=origin):
                scheme = origin.split("app.example.test")[0]
                run = self.run_command(created(), linked(), arguments={
                    "--service-origin": origin, "--redirect-to": scheme + "app.example.test/auth/callback"})
                self.assert_nothing_happened(run)

    def test_wrong_service_host_shapes_are_refused_before_any_request(self):
        for host in ("localhost", "10.0.0.1", "[::1]", "user@app.example.test", "app.example.test:8443", "app.example.test:port",
                     "APP.example.test", "app_bad.example.test", "-bad.example.test", "app..example.test",
                     "app.example.test.", "xn--bcher-kva.example.test/", "app.example.test/", "app.example.test/path",
                     "app.example.test?next=1", "app.example.test#part", "app.example.test?", " app.example.test", ""):
            with self.subTest(host=host):
                run = self.run_command(created(), linked(), arguments={
                    "--service-origin": "https://" + host, "--redirect-to": "https://" + host + "/auth/callback"})
                self.assert_nothing_happened(run)

    def test_wrong_project_reference_shapes_cannot_build_a_provider_host(self):
        for reference in ("short", PROJECT.upper(), PROJECT[:-1] + "1", PROJECT + "a", "abcdefghij.evil.test/",
                          "abcdefghij.evil.test#", PROJECT + ".evil.test", "", " " + PROJECT[1:], PROJECT[:-1] + "\n"):
            with self.subTest(reference=reference):
                with self.assertRaises(tool.Refusal):
                    tool.InvitationRequest(reference, EMAIL, ORIGIN, REDIRECT)
                self.assert_nothing_happened(self.run_command(created(), linked(), arguments={"--project-ref": reference}))

    def test_redirect_must_stay_inside_the_named_origin(self):
        for redirect in ("https://other.example.test/auth/callback", "http://app.example.test/auth/callback",
                         "https://app.example.test.evil.test/auth/callback", "https://app.example.test@evil.test/auth/callback",
                         "https://app.example.test:8443/auth/callback", ORIGIN, ORIGIN + "/", ORIGIN + "/auth/callback?next=/admin",
                         ORIGIN + "/auth/callback#part", ORIGIN + "/auth/../admin", ORIGIN + "//evil.test/auth",
                         ORIGIN + "/auth/callback/", ORIGIN + "/auth/%2e%2e/admin", ORIGIN + "/auth/call back", "/auth/callback"):
            with self.subTest(redirect=redirect):
                self.assert_nothing_happened(self.run_command(created(), linked(), arguments={"--redirect-to": redirect}))

    def test_invalid_addresses_are_refused_before_any_request(self):
        for address in ("invited.person", "a@b@example.test", "invited person@example.test", "invited@example",
                        ".invited@example.test", "invited..person@example.test", "invited.@example.test",
                        "invited@10.0.0.1", "invit" + chr(0xE9) + "@example.test", "invited@example.test\n", "",
                        "a" * 65 + "@example.test", "invited@" + "a" * 250 + ".test", "invited@-bad.example.test"):
            with self.subTest(address=address):
                self.assert_nothing_happened(self.run_command(created(), linked(), arguments={"--email": address}))

    def test_address_longer_than_the_mailbox_limit_is_refused(self):
        """Every label and the local part are valid here, so only the total length bound can refuse."""
        address = "a" * 64 + "@" + ".".join(["b" * 50] * 4) + ".test"
        self.assertGreater(len(address), 254)
        self.assertIsNotNone(tool._ADDRESS.fullmatch(address))
        self.assert_nothing_happened(self.run_command(created(), linked(), arguments={"--email": address}))
        accepted = "a" * 64 + "@" + ".".join(["b" * 50] * 3) + "." + "c" * 31 + ".test"
        self.assertEqual(len(accepted), 254)
        self.assertEqual(tool._invited_address(accepted), accepted)

    def test_abbreviated_confirmation_flag_is_not_a_confirmation(self):
        for flag in ("--a", "--acknowledge", "--acknowledge-identity-account-effect"):
            with self.subTest(flag=flag):
                run = self.run_command(created(), linked(), confirm=False, extra=(flag,))
                self.assert_nothing_happened(run)
                self.assertIn("unrecognized arguments: " + flag, run.stderr)

    def test_injected_transport_is_used_even_when_it_is_falsy(self):
        class EmptyRecorder(list):
            """A recorder that is still empty is falsy, like any empty list."""

            def __init__(self, *steps):
                super().__init__()
                self.steps = list(steps)

            def __call__(self, request):
                self.append(request.url)
                return self.steps.pop(0)
        network = []

        def default_transport(request, **options):
            network.append(request.url)
            raise tool.TransportFailure("connection_failed")
        recorder = EmptyRecorder(created(), linked())
        self.assertFalse(recorder)
        with patch.object(tool, "send_administration_request", default_transport):
            run = Run(recorder)
        self.addCleanup(run.close)
        self.assertEqual((network, len(recorder), run.code, run.stdout), ([], 2, 0, LINK + "\n"), run.stderr)

    def test_without_confirmation_nothing_is_requested_or_written(self):
        run = self.run_command(created(), linked(), confirm=False)
        self.assert_nothing_happened(run)
        self.assertIn("explicit_confirmation_required", run.stderr)

    def test_missing_or_malformed_credential_is_refused_before_any_request(self):
        for environment in ({}, {"FIXTURE_IDENTITY_ADMIN": ""}, {"FIXTURE_IDENTITY_ADMIN": "sb_secret_****"},
                            {"FIXTURE_IDENTITY_ADMIN": "sb_secret_short"},
                            {"FIXTURE_IDENTITY_ADMIN": ENVIRONMENT["FIXTURE_IDENTITY_PUBLIC"]},
                            {"FIXTURE_IDENTITY_ADMIN": CREDENTIAL + "\nInjected: header"},
                            {"OTHER_NAME": CREDENTIAL}):
            with self.subTest(names=sorted(environment)):
                run = self.run_command(created(), linked(), environment=environment)
                self.assert_nothing_happened(run)
                self.assertNotIn(CREDENTIAL, run.stderr)

    def test_credential_recorded_for_another_project_is_refused(self):
        other = "zyxwvutsrqponmlkjihg"
        run = self.run_command(created(), linked(), arguments={"--project-ref": other})
        self.assert_nothing_happened(run)
        self.assertIn("credential_is_recorded_for_another_project", run.stderr)

    def test_credential_reference_must_be_an_identity_administration_key(self):
        for reference in ("identity-public", "identity-legacy", "payments", "unknown", ""):
            with self.subTest(reference=reference):
                environment = {**ENVIRONMENT, "FIXTURE_IDENTITY_LEGACY": CREDENTIAL, "FIXTURE_PAYMENTS": CREDENTIAL}
                self.assert_nothing_happened(self.run_command(
                    created(), linked(), arguments={"--credential-ref": reference}, environment=environment))

    def test_unsupported_manifest_version_is_refused_before_any_request(self):
        for manifest in ({**MANIFEST, "record_type": "operator_credential_references/v2"},
                         {key: value for key, value in MANIFEST.items() if key != "record_type"}, [], None):
            with self.subTest(manifest=type(manifest).__name__):
                with self.assertRaises(tool.Refusal) as refused:
                    tool.credential_binding("identity-admin", manifest)
                self.assertEqual(refused.exception.code, "credential_manifest_unavailable")
        with patch.object(sys.modules[__name__], "MANIFEST", {**MANIFEST, "record_type": "operator_credential_references/v2"}):
            self.assert_nothing_happened(self.run_command(created(), linked()))

    def test_repository_manifest_names_the_administration_credential(self):
        binding = tool.credential_binding(tool.DEFAULT_CREDENTIAL_REFERENCE, tool.load_manifest())
        self.assertRegex(binding.project_ref, r"\A[a-z]{20}\Z")
        self.assertTrue(binding.environment_name.isupper())
        self.assertIsNone(re.fullmatch(binding.value_pattern, "sb_secret_****"))

    def test_existing_report_is_never_overwritten(self):
        with tempfile.TemporaryDirectory(prefix="baltor-invitation-report-") as folder:
            kept = Path(folder) / "kept.json"
            kept.write_text("earlier evidence", "utf-8")
            dangling = Path(folder) / "dangling.json"
            dangling.symlink_to(Path(folder) / "absent-target.json")
            for report in (kept, dangling, Path(folder) / "absent-folder" / "report.json", Path(folder)):
                with self.subTest(report=report.name):
                    run = self.run_command(created(), linked(), report=report)
                    self.assertEqual(run.code, tool.EXIT_REFUSED_BEFORE_ANY_REQUEST)
                    self.assertEqual((run.provider.requests, run.stdout), ([], ""))
            self.assertEqual(kept.read_text("utf-8"), "earlier evidence")
            self.assertFalse((Path(folder) / "absent-target.json").exists())

    # The two supported journeys.

    def test_new_account_is_created_confirmed_and_the_link_is_shown_once(self):
        run = self.run_command(created(), linked())
        self.assertEqual(run.code, 0, run.stderr)
        self.assertEqual(run.stdout, LINK + "\n")
        self.assertEqual(run.provider.paths, ["/auth/v1/admin/users", "/auth/v1/admin/generate_link"])
        creation, generation = run.provider.bodies
        self.assertEqual(creation, {"email": EMAIL, "email_confirm": True,
                                    "app_metadata": {"baltor_invitation": "beta_invitation_report/v1"}})
        self.assertEqual(generation, {"type": "recovery", "email": EMAIL, "redirect_to": REDIRECT})
        for request in run.provider.requests:
            self.assertEqual(request.credential, CREDENTIAL)
            self.assertNotIn(CREDENTIAL, repr(request))
        text = run.report.read_text("utf-8")
        self.assert_no_secret(run, text)
        record = run.record
        self.assertEqual(record["link_sha256"], hashlib.sha256(LINK.encode()).hexdigest())
        self.assertEqual(record["email_sha256"], hashlib.sha256(EMAIL.encode()).hexdigest())
        self.assertEqual({key: record[key] for key in ("record_type", "outcome", "failure", "user_id", "user_created",
                         "link_generated", "link_kind", "provider_requests", "automatic_retries", "email_requested",
                         "project_url", "identity_issuer", "redirect_to")},
                         {"record_type": "beta_invitation_report/v1", "outcome": "link_issued", "failure": None,
                          "user_id": USER_ID, "user_created": True, "link_generated": True, "link_kind": "recovery",
                          "provider_requests": 2, "automatic_retries": 0, "email_requested": False,
                          "project_url": PROJECT_ORIGIN, "identity_issuer": PROJECT_ORIGIN + "/auth/v1",
                          "redirect_to": REDIRECT})
        self.assertEqual(stat.S_IMODE(run.report.stat().st_mode), 0o600)
        self.assertEqual(json.loads(run.stderr)["outcome"], "link_issued")

    def test_existing_confirmed_account_is_found_and_a_link_is_reissued(self):
        for shape in ("legacy", "dated"):
            with self.subTest(shape=shape):
                run = self.run_command(exists(shape), linked())
                self.assertEqual((run.code, run.stdout), (0, LINK + "\n"), run.stderr)
                self.assertEqual((run.record["user_created"], run.record["user_id"]), (False, USER_ID))
                self.assertEqual(len(run.provider.requests), 2)

    def test_existing_account_without_the_invitation_mark_gets_no_link(self):
        """An account that someone else registered keeps that person's password, sessions and keys."""
        stranger = {"provider": "email", "providers": ["email"]}
        for name, metadata in (("no_mark", stranger), ("no_metadata", None), ("metadata_is_not_an_object", "email"),
                               ("other_value", {**stranger, "baltor_invitation": "beta_invitation_report/v0"}),
                               ("true_is_not_the_mark", {**stranger, "baltor_invitation": True}),
                               ("mark_in_user_metadata_only", stranger)):
            with self.subTest(name=name):
                changes = {"app_metadata": metadata, "created_at": "2026-09-18T08:00:00Z",
                           "last_sign_in_at": "2026-09-19T08:00:00Z",
                           "user_metadata": {"baltor_invitation": tool.INVITATION_MARK_VALUE}}
                run = self.run_command(exists(), linked(**changes))
                self.assertEqual((run.code, run.stdout, len(run.provider.requests)), (1, "", 2), run.stderr)
                record = run.record
                self.assertEqual((record["outcome"], record["failure"], record["user_created"],
                                  record["invitation_mark_present"], record["link_generated"], record["link_sha256"]),
                                 ("refused", "existing_user_was_not_created_by_the_invitation_command", False, False,
                                  True, None))
                self.assertIs(json.loads(run.stderr)["invitation_mark_present"], False)
                self.assert_no_secret(run, run.report.read_text("utf-8"))
        marked = self.run_command(exists(), linked())
        self.assertEqual((marked.code, marked.stdout), (0, LINK + "\n"), marked.stderr)
        self.assertEqual((marked.record["user_created"], marked.record["invitation_mark_present"]), (False, True))
        self.assertIs(json.loads(marked.stderr)["invitation_mark_present"], True)

    def test_report_says_when_the_mark_was_never_read(self):
        run = self.run_command(created(), tool.TransportFailure("timeout"))
        self.assertIsNone(run.record["invitation_mark_present"])

    def test_the_provider_is_never_asked_to_send_email(self):
        run = self.run_command(created(), linked())
        self.assertEqual(run.code, 0)
        for path, body in zip(run.provider.paths, run.provider.bodies, strict=True):
            self.assertIn(path, ("/auth/v1/admin/users", "/auth/v1/admin/generate_link"))
            self.assertNotIn("password", body)
        self.assertIs(run.record["email_requested"], False)

    def test_address_is_lowercased_once_and_used_everywhere(self):
        run = self.run_command(created(), linked(), arguments={"--email": "Invited.Person@Example.TEST"})
        self.assertEqual(run.code, 0, run.stderr)
        self.assertEqual([body["email"] for body in run.provider.bodies], [EMAIL, EMAIL])
        self.assertEqual(run.record["email_sha256"], hashlib.sha256(EMAIL.encode()).hexdigest())

    def test_answer_with_every_published_user_field_is_accepted(self):
        """Field names follow the provider's published user model. Values are fixtures."""
        complete = user(phone="", confirmed_at="2026-09-20T11:59:58.12345Z", recovery_sent_at="2026-09-20T11:59:59Z",
                        last_sign_in_at=None, created_at="2026-09-20T11:59:58.1Z", updated_at="2026-09-20T11:59:59.2Z",
                        banned_until=None, deleted_at=None, invited_at=None, confirmation_sent_at=None,
                        app_metadata={"provider": "email", "providers": ["email"],
                                      "baltor_invitation": tool.INVITATION_MARK_VALUE},
                        user_metadata={"email_verified": True},
                        identities=[{"identity_id": OTHER_ID, "id": USER_ID, "user_id": USER_ID, "provider": "email",
                                     "identity_data": {"email": EMAIL, "sub": USER_ID}, "email": EMAIL}])
        run = self.run_command(response(200, complete), linked(**complete))
        self.assertEqual((run.code, run.stdout, run.record["user_id"]), (0, LINK + "\n", USER_ID), run.stderr)
        self.assert_no_secret(run, run.report.read_text("utf-8"))

    def test_wrapped_creation_answer_is_read_like_the_direct_one(self):
        run = self.run_command(response(201, {"user": user()}), linked())
        self.assertEqual((run.code, run.record["user_created"]), (0, True), run.stderr)

    # Ambiguous outcomes are reported as unknown and nothing is repeated.

    def test_timeout_on_creation_reports_unknown_and_does_not_retry(self):
        for failure in ("timeout", "connection_failed"):
            with self.subTest(failure=failure):
                run = self.run_command(tool.TransportFailure(failure), linked())
                self.assertEqual((run.code, run.stdout), (3, ""))
                self.assertEqual(len(run.provider.requests), 1)
                record = run.record
                self.assertEqual((record["outcome"], record["failure"], record["detail"]),
                                 ("outcome_unknown", "user_creation_outcome_unknown_do_not_repeat", failure))
                self.assertEqual((record["user_created"], record["user_id"], record["link_generated"],
                                  record["link_sha256"], record["automatic_retries"]), (None, None, None, None, 0))

    def test_timeout_on_link_reports_unknown_and_does_not_retry(self):
        run = self.run_command(created(), tool.TransportFailure("timeout"))
        self.assertEqual((run.code, run.stdout), (3, ""))
        self.assertEqual(len(run.provider.requests), 2)
        record = run.record
        self.assertEqual((record["outcome"], record["failure"], record["user_created"], record["user_id"],
                          record["link_generated"]),
                         ("outcome_unknown", "link_outcome_unknown_do_not_repeat", True, USER_ID, None))

    def test_unexpected_transport_error_is_unknown_and_discloses_nothing(self):
        run = self.run_command(RuntimeError("private diagnostic " + CREDENTIAL))
        self.assertEqual((run.code, run.stdout, len(run.provider.requests)), (3, "", 1))
        self.assertEqual(run.record["detail"], "transport_error")
        self.assert_no_secret(run, run.report.read_text("utf-8"))

    def test_provider_redirect_is_refused_and_leaves_the_outcome_unknown(self):
        for status in (301, 302, 303, 307, 308):
            with self.subTest(status=status):
                run = self.run_command(response(status, b""), linked())
                self.assertEqual((run.code, run.stdout, len(run.provider.requests)), (3, "", 1))
                self.assertEqual((run.record["failure"], run.record["provider_status"]),
                                 ("provider_redirect_refused", status))

    def test_server_error_leaves_the_outcome_unknown(self):
        for status in (500, 502, 503, 504, 100, 204, 600):
            with self.subTest(status=status):
                run = self.run_command(response(status, {"msg": "fixture"}), linked())
                self.assertEqual((run.code, run.stdout, len(run.provider.requests)), (3, "", 1))
                self.assertEqual(run.record["outcome"], "outcome_unknown")

    def test_unexpected_status_on_the_link_request_leaves_the_outcome_unknown(self):
        for status in (500, 502, 503, 504, 100, 201, 202, 204, 600):
            with self.subTest(status=status):
                run = self.run_command(created(), response(status, {"msg": "fixture"}))
                self.assertEqual((run.code, run.stdout, len(run.provider.requests)), (3, "", 2))
                record = run.record
                self.assertEqual((record["outcome"], record["failure"], record["detail"], record["user_created"],
                                  record["link_generated"], record["link_sha256"], record["provider_status"]),
                                 ("outcome_unknown", "link_outcome_unknown_do_not_repeat", "unexpected_status", True,
                                  None, None, status))

    def test_provider_redirect_on_the_link_request_is_refused_as_unknown(self):
        for status in (301, 302, 303, 307, 308):
            with self.subTest(status=status):
                run = self.run_command(created(), response(status, b""))
                self.assertEqual((run.code, run.stdout, len(run.provider.requests)), (3, "", 2))
                self.assertEqual((run.record["failure"], run.record["provider_status"], run.record["link_generated"]),
                                 ("provider_redirect_refused", status, None))

    def test_oversized_link_answer_is_refused_by_the_command_itself(self):
        padded = json.dumps({**json.loads(linked().body), "padding": "x" * 70_000}).encode()
        run = self.run_command(created(), response(200, padded))
        self.assertEqual((run.code, run.stdout, len(run.provider.requests)), (3, "", 2))
        self.assertEqual((run.record["failure"], run.record["detail"], run.record["link_sha256"]),
                         ("link_outcome_unknown_do_not_repeat", "response_too_large", None))
        self.assert_no_secret(run, run.report.read_text("utf-8"))

    def test_transport_that_breaks_its_contract_leaves_the_outcome_unknown(self):
        class Answer:
            def __init__(self, status, body):
                self.status, self.body = status, body
        for name, answer in (("nothing", None), ("plain_object", {"status": 200, "body": b"{}"}),
                             ("other_type", Answer(200, created().body)),
                             ("truth_value_status", tool.AdministrationResponse(True, created().body)),
                             ("text_status", tool.AdministrationResponse("200", created().body)),
                             ("text_body", tool.AdministrationResponse(200, created().body.decode()))):
            with self.subTest(name=name):
                run = self.run_command(answer, linked())
                self.assertEqual((run.code, run.stdout, len(run.provider.requests)), (3, "", 1))
                self.assertEqual((run.record["outcome"], run.record["failure"], run.record["detail"]),
                                 ("outcome_unknown", "user_creation_outcome_unknown_do_not_repeat",
                                  "transport_contract_violation"))

    def test_defect_between_the_requests_is_unknown_and_discloses_nothing(self):
        def defect(*arguments, **options):
            raise LookupError("private diagnostic " + CREDENTIAL)
        with patch.object(tool, "_generate_link", defect):
            run = self.run_command(created(), linked())
        self.assertEqual((run.code, run.stdout, len(run.provider.requests)), (3, "", 1))
        record = run.record
        self.assertEqual((record["outcome"], record["failure"], record["detail"], record["user_created"]),
                         ("outcome_unknown", "unexpected_error", "LookupError", True))
        self.assert_no_secret(run, run.report.read_text("utf-8"))
        self.assertNotIn("private diagnostic", run.stderr + run.report.read_text("utf-8"))

    def test_oversized_answer_is_refused_by_the_command_itself(self):
        padded = json.dumps({**user(), "padding": "x" * 70_000}).encode()
        run = self.run_command(response(200, padded), linked())
        self.assertEqual((run.code, run.stdout, len(run.provider.requests)), (3, "", 1))
        self.assertEqual(run.record["detail"], "response_too_large")

    def test_malformed_creation_answers_are_refused_as_unknown(self):
        duplicated = b'{"id": "' + OTHER_ID.encode() + b'", "id": "' + USER_ID.encode() + b'", "email": "' + EMAIL.encode() + b'"}'
        malformed, other_user = "malformed_response", "response_does_not_describe_the_invited_user"
        for name, body, detail in (("not_json", b"<html>fixture</html>", malformed), ("array", b"[]", malformed),
                                   ("text", b'"created"', malformed), ("not_text", b"\xff\xfe", malformed),
                                   ("duplicate_keys", duplicated, malformed), ("empty", b"", malformed),
                                   ("not_finite", b'{"id": NaN}', malformed),
                                   ("no_identity", json.dumps(user(id=None)).encode(), other_user),
                                   ("bad_identity", json.dumps(user(id="1 or 1=1")).encode(), other_user),
                                   ("other_address", json.dumps(user(email="other@example.test")).encode(), other_user)):
            with self.subTest(name=name):
                run = self.run_command(response(200, body), linked())
                self.assertEqual((run.code, run.stdout, len(run.provider.requests)), (3, "", 1))
                self.assertEqual((run.record["failure"], run.record["detail"]),
                                 ("user_creation_outcome_unknown_do_not_repeat", detail))

    def test_malformed_link_answers_are_refused_as_unknown(self):
        duplicated = json.dumps({**user(), "action_link": link_for(host="evil.example.test")})[:-1].encode() \
            + b', "action_link": "' + LINK.encode() + b'"}'
        for name, body in (("not_json", b"fixture"), ("array", b"[1]"), ("duplicate_keys", duplicated), ("empty", b"")):
            with self.subTest(name=name):
                run = self.run_command(created(), response(200, body))
                self.assertEqual((run.code, run.stdout, len(run.provider.requests)), (3, "", 2))
                self.assertEqual(run.record["failure"], "link_outcome_unknown_do_not_repeat")
                self.assert_no_secret(run, run.report.read_text("utf-8"))

    # Known refusals.

    def test_credential_refused_by_the_provider_is_reported_without_a_link(self):
        for status in (401, 403):
            for steps in ((response(status, {"msg": "fixture"}),), (created(), response(status, {"msg": "fixture"}))):
                with self.subTest(status=status, requests=len(steps)):
                    run = self.run_command(*steps)
                    self.assertEqual((run.code, run.stdout), (1, ""))
                    self.assertEqual((run.record["outcome"], run.record["failure"]),
                                     ("refused", "credential_refused_by_provider"))

    def test_other_provider_refusals_stop_without_a_link(self):
        run = self.run_command(response(422, {"code": 422, "error_code": "validation_failed", "msg": "fixture"}))
        self.assertEqual((run.code, run.stdout, run.record["failure"], run.record["user_created"]),
                         (1, "", "user_creation_refused_by_provider", False))
        run = self.run_command(response(422, b"not json"))
        self.assertEqual((run.code, run.record["failure"]), (1, "user_creation_refused_by_provider"))
        run = self.run_command(exists(), response(404, {"code": 404, "error_code": "user_not_found", "msg": "fixture"}))
        self.assertEqual((run.code, run.stdout, run.record["failure"], run.record["link_generated"]),
                         (1, "", "user_not_found_at_the_provider", False))
        run = self.run_command(created(), response(429, {"msg": "fixture"}))
        self.assertEqual((run.code, run.stdout, run.record["failure"]), (1, "", "link_refused_by_provider"))

    def test_unconfirmed_existing_account_gets_no_link(self):
        for stamp in (None, "", "not a time", "2026-09-20T12:30:00Z", "2026-09-20T12:00:00", 5):
            with self.subTest(stamp=stamp):
                run = self.run_command(exists(), linked(email_confirmed_at=stamp))
                self.assertEqual((run.code, run.stdout), (1, ""))
                record = run.record
                self.assertEqual((record["failure"], record["link_generated"], record["link_sha256"]),
                                 ("user_is_not_confirmed", True, None))
                self.assert_no_secret(run, run.report.read_text("utf-8"))

    def test_confirmation_time_accepts_the_provider_formats_and_a_small_clock_difference(self):
        for stamp in ("2026-09-20T11:59:58Z", "2026-09-20T11:59:58.1Z", "2026-09-20T11:59:58.123456789Z",
                      "2026-09-20T13:59:58.5+02:00", "2026-09-20T12:04:00Z"):
            with self.subTest(stamp=stamp):
                self.assertEqual(self.run_command(exists(), linked(email_confirmed_at=stamp)).code, 0)

    def test_disabled_or_unsupported_accounts_get_no_link(self):
        later = (NOW + timedelta(days=30)).isoformat()
        for name, changes in (("banned", {"banned_until": later}), ("unreadable_ban", {"banned_until": "later"}),
                              ("deleted", {"deleted_at": "2026-09-19T00:00:00Z"}), ("anonymous", {"is_anonymous": True}),
                              ("anonymous_unstated", {"is_anonymous": None}), ("other_role", {"role": "service_role"})):
            with self.subTest(name=name):
                run = self.run_command(exists(), linked(**changes))
                self.assertEqual((run.code, run.stdout), (1, ""))
                self.assertEqual(run.record["failure"], "user_cannot_sign_in_at_the_provider")
        self.assertEqual(self.run_command(exists(), linked(banned_until="2026-09-01T00:00:00Z")).code, 0)

    def test_link_for_another_identity_is_withheld(self):
        for name, steps in (("other_identity_after_creation", (created(), linked(id=OTHER_ID))),
                            ("other_address", (exists(), linked(email="other@example.test"))),
                            ("no_identity", (exists(), linked(id=None))),
                            ("bad_identity", (exists(), linked(id="../" + USER_ID[3:])))):
            with self.subTest(name=name):
                run = self.run_command(*steps)
                self.assertEqual((run.code, run.stdout), (1, ""))
                self.assertEqual(run.record["failure"], "user_identity_mismatch")
                self.assert_no_secret(run, run.report.read_text("utf-8"))

    def test_redirect_replaced_by_the_provider_is_refused(self):
        site = "https://site.example.test"
        for name, answer in (("both", linked(link_for(redirect=site), redirect_to=site)),
                             ("link_only", linked(link_for(redirect=site))),
                             ("field_only", linked(redirect_to=site)),
                             ("escaped_other", linked(link_for(redirect="https%3A%2F%2Fsite.example.test")))):
            with self.subTest(name=name):
                run = self.run_command(created(), answer)
                self.assertEqual((run.code, run.stdout), (1, ""))
                self.assertEqual(run.record["failure"], "redirect_replaced_by_the_provider")
        escaped = link_for(redirect="https%3A%2F%2Fapp.example.test%2Fauth%2Fcallback")
        run = self.run_command(created(), linked(escaped))
        self.assertEqual((run.code, run.stdout), (0, escaped + "\n"), run.stderr)

    def test_link_shape_is_checked_before_display(self):
        for name, link in (("other_host", link_for(host="evil.example.test")),
                           ("lookalike_host", link_for(host=PROJECT + ".supabase.co.evil.example.test")),
                           ("user_information", link_for(host="user@" + PROJECT + ".supabase.co")),
                           ("port", link_for(host=PROJECT + ".supabase.co:8443")),
                           ("unreadable_port", link_for(host=PROJECT + ".supabase.co:port")),
                           ("plain_http", link_for(scheme="http")), ("other_path", link_for(path="/auth/v1/other")),
                           ("no_token", link_for(token="")), ("short_token", link_for(token="abc")),
                           ("token_with_separator", link_for(token=LINK_TOKEN + "%26type%3Dinvite")),
                           ("second_token", link_for(extra="&token=" + LINK_TOKEN)),
                           ("additional_parameter", link_for(extra="&next=/admin")),
                           ("fragment", link_for(extra="#access_token=fixture")),
                           ("space", link_for(extra=" ")), ("line_break", link_for(extra="\n")),
                           ("too_long", link_for(token="a" * 4000)), ("not_text", 7), ("absent", None), ("empty", "")):
            with self.subTest(name=name):
                run = self.run_command(created(), linked(link))
                self.assertEqual((run.code, run.stdout), (1, ""), name)
                self.assertEqual(run.record["failure"], "link_shape_refused")
                self.assertIsNone(run.record["link_sha256"])

    def test_other_link_kinds_are_withheld(self):
        for answer in (linked(link_for(kind="magiclink")), linked(verification_type="invite")):
            run = self.run_command(created(), answer)
            self.assertEqual((run.code, run.stdout, run.record["failure"]), (1, "", "link_kind_mismatch"))

    # Output sinks.

    def test_output_guard_refuses_a_report_that_would_hold_a_secret(self):
        with self.assertRaises(tool.Refusal):
            tool.encode_report({"record_type": tool.REPORT_RECORD_TYPE, "note": "see " + LINK}, (LINK,))
        original = tool.build_report

        def leaking(*arguments):
            return {**original(*arguments), "note": arguments[1].link}
        with patch.object(tool, "build_report", leaking):
            run = self.run_command(created(), linked())
        self.assertEqual((run.code, run.stdout), (1, ""))
        self.assertEqual((run.record["outcome"], run.record["failure"]), ("refused", "secret_in_output_refused"))
        self.assert_no_secret(run, run.report.read_text("utf-8"))

    def test_credential_and_one_time_code_reach_the_output_guard(self):
        """End to end: the values come from the run itself, not from a list the check supplies."""
        original = tool.build_report
        for name, secret in (("credential", CREDENTIAL), ("one_time_code", ONE_TIME_CODE)):
            with self.subTest(name=name):
                def leaking(*arguments, secret=secret):
                    return {**original(*arguments), "note": secret}
                with patch.object(tool, "build_report", leaking):
                    run = self.run_command(created(), linked())
                self.assertEqual((run.code, run.stdout), (1, ""), run.stderr)
                self.assertEqual(json.loads(run.stderr)["failure"], "secret_in_output_refused")
                self.assertEqual(run.report.read_text("utf-8"), "")
                self.assert_no_secret(run)

    def test_summary_line_is_guarded_like_the_report(self):
        """A report path that matches a private value costs the path, not the whole line.

        The invitation itself is unaffected: the link is shown and the exit status stays 0.
        """
        for name, secret in (("credential", CREDENTIAL), ("one_time_code", ONE_TIME_CODE)):
            with self.subTest(name=name):
                folder = tempfile.TemporaryDirectory(prefix="baltor-invitation-summary-")
                self.addCleanup(folder.cleanup)
                run = self.run_command(created(), linked(), report=Path(folder.name) / (secret + ".json"))
                self.assertEqual((run.code, run.stdout), (0, LINK + "\n"), run.stderr)
                summary = json.loads(run.stderr)
                self.assertEqual((summary["outcome"], summary["failure"], summary["link_displayed"],
                                  summary["report_written"], summary["report"]),
                                 ("link_issued", None, True, True, tool.WITHHELD_REPORT_PATH))
                self.assertTrue(run.report.exists())
                self.assert_no_secret(run, run.report.read_text("utf-8"))
                self.assertNotIn(str(run.report), run.stderr)

    def test_summary_falls_back_to_the_bare_code_when_a_typed_field_would_hold_a_secret(self):
        """The last resort stays: a reduced line that still matches is replaced entirely."""
        fields = {"outcome": "link_issued", "report": "/private/report.json"}
        self.assertEqual(tool._safe_summary(fields, (LINK,)), json.dumps(fields, sort_keys=True))
        self.assertEqual(json.loads(tool._safe_summary(fields, ("/private/report.json",)))["report"],
                         tool.WITHHELD_REPORT_PATH)
        self.assertEqual(tool._safe_summary(fields, ("link_issued",)), tool.InvitationRefusal.SECRET_IN_OUTPUT.value)

    def test_short_code_is_matched_as_a_whole_value_and_long_secrets_anywhere(self):
        digest = "ab" + ONE_TIME_CODE + "cd" * 28
        honest = {"record_type": tool.REPORT_RECORD_TYPE, "link_sha256": digest}
        self.assertIn(ONE_TIME_CODE, tool.encode_report(honest, (ONE_TIME_CODE, LINK, CREDENTIAL)))
        for leaking in ({"email_otp": ONE_TIME_CODE}, {"note": "code " + ONE_TIME_CODE + "."},
                        {"note": "prefix" + LINK_TOKEN + "suffix"}, {"note": "x" + CREDENTIAL + "x"}):
            with self.subTest(leaking=sorted(leaking)), self.assertRaises(tool.Refusal):
                tool.encode_report({**honest, **leaking}, (ONE_TIME_CODE, LINK_TOKEN, CREDENTIAL))

    def test_report_failure_withholds_the_link(self):
        def full_disk(stream, text):
            raise OSError(28, "fixture: no space left on device")
        with patch.object(tool, "_write_durably", full_disk):
            run = self.run_command(created(), linked())
        self.assertEqual((run.code, run.stdout), (1, ""))
        self.assertEqual(json.loads(run.stderr)["failure"], "report_not_written_link_withheld")
        self.assert_no_secret(run)

    def test_link_that_cannot_be_displayed_is_reported_not_claimed(self):
        class ClosedPipe(io.StringIO):
            def write(self, text):
                raise BrokenPipeError(32, "fixture: the reader went away")
        folder = tempfile.TemporaryDirectory(prefix="baltor-invitation-check-")
        self.addCleanup(folder.cleanup)
        report, stderr = Path(folder.name) / "report.json", io.StringIO()
        with redirect_stdout(ClosedPipe()), redirect_stderr(stderr):
            code = tool.main(["--project-ref", PROJECT, "--email", EMAIL, "--service-origin", ORIGIN, "--redirect-to",
                              REDIRECT, "--report", str(report), "--credential-ref", "identity-admin",
                              "--acknowledge-identity-account-effects"], environment=ENVIRONMENT,
                             transport=Provider(created(), linked()), manifest=MANIFEST, now=lambda: NOW)
        summary = json.loads(stderr.getvalue())
        self.assertEqual((code, summary["outcome"], summary["link_displayed"], summary["report_written"]),
                         (1, "link_issued", False, True))
        self.assertNotIn(LINK, stderr.getvalue())
        self.assertEqual(json.loads(report.read_text("utf-8"))["outcome"], "link_issued")

    def test_defect_after_the_requests_is_unknown_and_prints_no_message(self):
        def defect(*arguments):
            raise RuntimeError("private diagnostic " + LINK + " " + CREDENTIAL)
        with patch.object(tool, "build_report", defect):
            run = self.run_command(created(), linked())
        self.assertEqual((run.code, run.stdout, run.stderr), (3, "", "unexpected_error:RuntimeError\n"))
        self.assertEqual(run.report.read_text("utf-8"), "")

    def test_records_never_print_the_link_or_the_credential(self):
        result = tool.issue_invitation(tool.InvitationRequest(PROJECT, EMAIL, ORIGIN, REDIRECT), CREDENTIAL,
                                       Provider(created(), linked()), now=lambda: NOW)
        self.assertEqual(result.link, LINK)
        for text in (repr(result), str(result), repr(linked()), repr(tool.AdministrationRequest(
                PROJECT_ORIGIN, b"{}", 1.0, 10, CREDENTIAL))):
            for secret in (LINK, LINK_TOKEN, ONE_TIME_CODE, CREDENTIAL):
                self.assertNotIn(secret, text)

    def test_limits_are_typed_and_bounded(self):
        for changes in ({"timeout_seconds": 0}, {"timeout_seconds": 61}, {"timeout_seconds": float("nan")},
                        {"timeout_seconds": True}, {"maximum_response_bytes": 0}, {"maximum_response_bytes": 10 ** 7},
                        {"maximum_link_length": 10}, {"maximum_clock_skew_seconds": -1},
                        {"maximum_clock_skew_seconds": 86400}):
            with self.subTest(changes=changes), self.assertRaises(tool.Refusal):
                tool.AdministrationLimits(**changes)


class DefaultTransportChecks(unittest.TestCase):
    """The production transport against the HTTP library's in-memory mock."""

    def setUp(self):
        import httpx
        self.httpx = httpx
        self.request = tool.AdministrationRequest(PROJECT_ORIGIN + "/auth/v1/admin/users", b'{"email":"fixture"}',
                                                  5.0, 1_000, CREDENTIAL)

    def send(self, handler, request=None):
        return tool.send_administration_request(request or self.request, http_transport=self.httpx.MockTransport(handler))

    def test_default_transport_sends_one_bounded_post_with_the_credential_headers(self):
        seen = []

        def handler(request):
            seen.append(request)
            return self.httpx.Response(200, json={"id": USER_ID})
        answer = self.send(handler)
        self.assertEqual((answer.status, json.loads(answer.body)), (200, {"id": USER_ID}))
        self.assertEqual(len(seen), 1)
        sent = seen[0]
        self.assertEqual((sent.method, str(sent.url), sent.content), ("POST", self.request.url, self.request.body))
        self.assertEqual((sent.headers["apikey"], sent.headers["authorization"], sent.headers["content-type"]),
                         (CREDENTIAL, "Bearer " + CREDENTIAL, "application/json"))
        self.assertEqual(sent.headers.get_list("accept-encoding"), ["identity"])

    def test_default_transport_refuses_a_compressed_answer_before_reading_it(self):
        import gzip
        import zlib
        pulled = []

        def body(packed):
            pulled.append(len(packed))
            yield packed
        for name, packed in (("gzip", gzip.compress(b"x" * 4_000_000)), ("deflate", zlib.compress(b"x" * 4_000_000))):
            with self.subTest(name=name):
                self.assertLess(len(packed), self.request.maximum_response_bytes * 8)

                def handler(request, name=name, packed=packed):
                    return self.httpx.Response(200, headers={"Content-Encoding": name}, content=body(packed))
                with self.assertRaises(tool.TransportFailure) as raised:
                    self.send(handler)
                self.assertEqual(raised.exception.code, "response_encoding_refused")
        self.assertEqual(pulled, [])
        answer = self.send(lambda request: self.httpx.Response(200, headers={"Content-Encoding": "identity"}, content=b"{}"))
        self.assertEqual(answer.body, b"{}")

    def test_default_transport_stops_at_one_overall_deadline(self):
        """Each piece arrives quickly, so only the overall deadline can stop a slow answer."""
        pulled = []

        def body():
            for index in range(40):
                pulled.append(index)
                time.sleep(0.02)
                yield b"x"

        def handler(request):
            return self.httpx.Response(200, content=body())
        slow = tool.AdministrationRequest(self.request.url, self.request.body, 0.1, 1_000, CREDENTIAL)
        with self.assertRaises(tool.TransportFailure) as raised:
            self.send(handler, slow)
        self.assertEqual(raised.exception.code, "timeout")
        self.assertLess(len(pulled), 20)

    def test_default_transport_never_follows_a_redirect_or_forwards_the_credential(self):
        contacted = []

        def handler(request):
            contacted.append(request.url.host)
            if request.url.host == "collector.example.test":
                return self.httpx.Response(200, json={"received": request.headers.get("apikey")})
            return self.httpx.Response(307, headers={"Location": "https://collector.example.test/auth/v1/admin/users"})
        answer = self.send(handler)
        self.assertEqual(answer.status, 307)
        self.assertEqual(contacted, [PROJECT + ".supabase.co"])

    def test_default_transport_stops_reading_an_oversized_body(self):
        pulled = []

        def body():
            for index in range(100):
                pulled.append(index)
                yield b"x" * 100

        def handler(request):
            return self.httpx.Response(200, content=body())
        with self.assertRaises(tool.TransportFailure) as raised:
            self.send(handler)
        self.assertEqual(raised.exception.code, "response_too_large")
        self.assertLess(len(pulled), 20)

    def test_default_transport_maps_lost_answers_to_typed_failures(self):
        for error, code in ((self.httpx.ReadTimeout("fixture"), "timeout"), (self.httpx.ConnectTimeout("fixture"), "timeout"),
                            (self.httpx.ConnectError("fixture"), "connection_failed"),
                            (self.httpx.RemoteProtocolError("fixture"), "connection_failed")):
            with self.subTest(error=type(error).__name__):
                def handler(request, error=error):
                    raise error
                with self.assertRaises(tool.TransportFailure) as raised:
                    self.send(handler)
                self.assertEqual(raised.exception.code, code)
                self.assertNotIn("fixture", str(raised.exception))

    def test_client_options_disable_redirects_and_environment_proxies(self):
        with patch.dict(os.environ, {"HTTPS_PROXY": "http://proxy.example.test:3128"}):
            options = tool._client_options(self.request, None)
        self.assertEqual((options["follow_redirects"], options["trust_env"], options["timeout"]), (False, False, 5.0))


class RemovedGuardControls(unittest.TestCase):
    """Each guard is removed in memory, and its named check must then fail.

    Source files are never changed. A control first shows that the named check
    passes with the guard in place, so a failure is caused by the removal.
    """

    @staticmethod
    def failed(case, name):
        outcome = unittest.TestResult()
        unittest.TestSuite([case(name)]).run(outcome)
        return bool(outcome.failures or outcome.errors)

    def assert_detected(self, guard, replacement, case, name):
        self.assertFalse(self.failed(case, name), name + " must pass before the guard is removed")
        with patch.object(tool, guard, replacement):
            self.assertTrue(self.failed(case, name), "removing " + guard + " was not detected by " + name)

    CONTROLS = (
        ("_require_secure_scheme", "test_non_https_service_origin_is_refused_before_any_request"),
        ("_require_public_host_shape", "test_wrong_service_host_shapes_are_refused_before_any_request"),
        ("_require_project_reference", "test_wrong_project_reference_shapes_cannot_build_a_provider_host"),
        ("_require_same_origin", "test_redirect_must_stay_inside_the_named_origin"),
        ("_require_confirmation", "test_without_confirmation_nothing_is_requested_or_written"),
        ("_require_credential_shape", "test_missing_or_malformed_credential_is_refused_before_any_request"),
        ("_require_credential_for_project", "test_credential_recorded_for_another_project_is_refused"),
        ("_require_administration_reference", "test_credential_reference_must_be_an_identity_administration_key"),
        ("_require_supported_manifest", "test_unsupported_manifest_version_is_refused_before_any_request"),
        ("_refuse_provider_redirect", "test_provider_redirect_is_refused_and_leaves_the_outcome_unknown"),
        ("_require_bounded_body", "test_oversized_answer_is_refused_by_the_command_itself"),
        ("_require_confirmed_user", "test_unconfirmed_existing_account_gets_no_link"),
        ("_require_sign_in_allowed", "test_disabled_or_unsupported_accounts_get_no_link"),
        ("_require_same_identity", "test_link_for_another_identity_is_withheld"),
        ("_require_redirect_kept", "test_redirect_replaced_by_the_provider_is_refused"),
        ("_require_link_at_project", "test_link_shape_is_checked_before_display"),
        ("_require_link_kind", "test_other_link_kinds_are_withheld"),
        ("_require_no_secret", "test_output_guard_refuses_a_report_that_would_hold_a_secret"),
        ("_require_invited_user", "test_existing_account_without_the_invitation_mark_gets_no_link"),
        ("_require_transport_contract", "test_transport_that_breaks_its_contract_leaves_the_outcome_unknown"),
        ("_require_definite_status", "test_unexpected_status_on_the_link_request_leaves_the_outcome_unknown"),
    )
    # Each of these guards is removed for the link request only, so the creation checks cannot catch it.
    LINK_REQUEST_CONTROLS = (
        ("_require_definite_status", "test_unexpected_status_on_the_link_request_leaves_the_outcome_unknown"),
        ("_refuse_provider_redirect", "test_provider_redirect_on_the_link_request_is_refused_as_unknown"),
        ("_require_bounded_body", "test_oversized_link_answer_is_refused_by_the_command_itself"),
    )
    TRANSPORT_CONTROLS = (
        ("_deadline_passed", lambda deadline: False, "test_default_transport_stops_at_one_overall_deadline"),
        ("_require_unencoded_body", lambda encoding: None,
         "test_default_transport_refuses_a_compressed_answer_before_reading_it"),
    )
    COMMAND_CONTROLS = (
        ("_outcome_after_defect", lambda progress: tool.InvitationOutcome.REFUSED,
         "test_defect_between_the_requests_is_unknown_and_discloses_nothing"),
        ("_safe_summary", lambda fields, sensitive: json.dumps(fields, sort_keys=True),
         "test_summary_line_is_guarded_like_the_report"),
        ("_sensitive_values", lambda credential, result: tuple(result.sensitive_values),
         "test_credential_and_one_time_code_reach_the_output_guard"),
        ("_SENSITIVE_FIELDS", ("action_link", "hashed_token"), "test_credential_and_one_time_code_reach_the_output_guard"),
        ("MAXIMUM_INVITED_ADDRESS_LENGTH", 10 ** 6, "test_address_longer_than_the_mailbox_limit_is_refused"),
        ("_invitation_mark_present", lambda payload: True,
         "test_existing_account_without_the_invitation_mark_gets_no_link"),
        ("_select_transport", lambda transport: transport or tool.send_administration_request,
         "test_injected_transport_is_used_even_when_it_is_falsy"),
    )

    def test_each_guard_removed_for_the_link_request_only_fails_its_named_check(self):
        original = tool._generate_link
        for guard, name in self.LINK_REQUEST_CONTROLS:
            def generate(*arguments, guard=guard):
                with patch.object(tool, guard, lambda *values, **options: None):
                    return original(*arguments)
            with self.subTest(guard=guard):
                self.assert_detected("_generate_link", generate, InvitationChecks, name)

    def test_each_removed_transport_guard_fails_its_named_check(self):
        for guard, replacement, name in self.TRANSPORT_CONTROLS:
            with self.subTest(guard=guard):
                self.assert_detected(guard, replacement, DefaultTransportChecks, name)

    def test_each_weakened_command_guard_fails_its_named_check(self):
        for guard, replacement, name in self.COMMAND_CONTROLS:
            with self.subTest(guard=guard, name=name):
                self.assert_detected(guard, replacement, InvitationChecks, name)

    def test_accepting_an_abbreviated_confirmation_is_detected(self):
        import argparse
        original = argparse.ArgumentParser

        def abbreviating(*arguments, **options):
            return original(*arguments, **{**options, "allow_abbrev": True})
        self.assertFalse(self.failed(InvitationChecks, "test_abbreviated_confirmation_flag_is_not_a_confirmation"))
        with patch.object(tool.argparse, "ArgumentParser", abbreviating):
            self.assertTrue(self.failed(InvitationChecks, "test_abbreviated_confirmation_flag_is_not_a_confirmation"))

    def test_the_number_of_controls_matches_the_guide(self):
        """The guide states how many removals are proven, so the statement cannot exceed this list."""
        single = [name for name in dir(self) if name.startswith("test_") and name.endswith("_is_detected")]
        count = (len(self.CONTROLS) + len(self.LINK_REQUEST_CONTROLS) + len(self.TRANSPORT_CONTROLS)
                 + len(self.COMMAND_CONTROLS) + len(single))
        self.assertIn("The " + str(count) + " removals listed in `RemovedGuardControls`", GUIDE.read_text("utf-8"))

    def test_each_removed_guard_fails_its_named_check(self):
        for guard, name in self.CONTROLS:
            with self.subTest(guard=guard):
                self.assert_detected(guard, lambda *arguments, **options: None, InvitationChecks, name)

    def test_accepting_repeated_keys_is_detected(self):
        self.assert_detected("_unique_pairs", dict, InvitationChecks, "test_malformed_link_answers_are_refused_as_unknown")

    def test_lenient_reading_of_a_malformed_answer_is_detected(self):
        def lenient(body):
            try:
                value = json.loads(body)
            except ValueError:
                return {}
            return value if isinstance(value, dict) else {}
        self.assert_detected("_json_object", lenient, InvitationChecks,
                             "test_malformed_creation_answers_are_refused_as_unknown")

    def test_an_automatic_retry_is_detected(self):
        original = tool._exchange

        def retrying(*arguments, **options):
            try:
                return original(*arguments, **options)
            except tool._Stop:
                return original(*arguments, **options)
        self.assert_detected("_exchange", retrying, InvitationChecks,
                             "test_timeout_on_creation_reports_unknown_and_does_not_retry")

    def test_overwriting_a_report_is_detected(self):
        self.assert_detected("_REPORT_OPEN_FLAGS", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, InvitationChecks,
                             "test_existing_report_is_never_overwritten")

    def test_showing_a_link_without_a_report_is_detected(self):
        self.assert_detected("_report_is_durable", lambda written: True, InvitationChecks,
                             "test_report_failure_withholds_the_link")

    def test_following_redirects_is_detected(self):
        def following(request, http_transport):
            return {"follow_redirects": True, "trust_env": False, "timeout": request.timeout_seconds,
                    "transport": http_transport}
        self.assert_detected("_client_options", following, DefaultTransportChecks,
                             "test_default_transport_never_follows_a_redirect_or_forwards_the_credential")

    def test_reading_without_a_bound_is_detected(self):
        self.assert_detected("_within_limit", lambda size, request: True, DefaultTransportChecks,
                             "test_default_transport_stops_reading_an_oversized_body")

    def test_asking_the_provider_to_send_email_is_detected(self):
        self.assert_detected("LINK_PATH", "/auth/v1/recover", InvitationChecks,
                             "test_the_provider_is_never_asked_to_send_email")


class OperatorGuideChecks(unittest.TestCase):
    """The procedure document must match the command and the real host loader.

    The local service comes from the runnable service example. It needs no
    network, no credential and no provider.
    """

    SUBJECT = "00000000-0000-4000-8000-0000000000aa"

    @classmethod
    def setUpClass(cls):
        cls.text = GUIDE.read_text("utf-8")
        cls.blocks = re.findall(r"^```([a-z]*)\n(.*?)^```$", cls.text, re.M | re.S)
        documents = [json.loads(body) for language, body in cls.blocks if language == "json"]
        cls.hosts = [document for document in documents if "browser_identity" in document]

    def local_host(self, *, without=()):
        """A complete local host configuration with the guide's two blocks added."""
        from importlib.util import module_from_spec, spec_from_file_location
        spec = spec_from_file_location("service_example_prepare", ROOT / "examples/29_intelligence_service/prepare.py")
        example = module_from_spec(spec)
        sys.modules[spec.name] = example
        self.addCleanup(sys.modules.pop, spec.name, None)
        spec.loader.exec_module(example)
        folder = tempfile.TemporaryDirectory(prefix="baltor-guide-check-")
        self.addCleanup(folder.cleanup)
        root = Path(folder.name).resolve() / "service"
        example.prepare(example.PreparationRequest(root, allow_write=True))
        path = root / "host.json"
        configuration = json.loads(path.read_text("utf-8"))
        configuration.update({name: block for name, block in self.hosts[0].items() if name not in without})
        path.write_text(json.dumps(configuration), "utf-8")
        return path

    def test_guide_host_blocks_load_through_the_real_host_loader(self):
        from loop_engine.core.service_runtime.http_entrypoint import ENVIRONMENT_REFERENCE_PREFIX, load_host_application
        from loop_engine.core.service_runtime.records import ServiceRuntimeError
        self.assertEqual(len(self.hosts), 1)
        self.assertEqual(sorted(self.hosts[0]), ["browser_identity", "client_access"])
        self.assertNotIn("sb_publishable_", json.dumps(self.hosts[0]))
        application, _ = load_host_application(str(self.local_host()))
        identity = application.browser_identity.configuration
        self.assertEqual((identity.registration_enabled, identity.email_signup_enabled, identity.allow_network),
                         (True, False, True))
        self.assertTrue(identity.publishable_key_ref.startswith(ENVIRONMENT_REFERENCE_PREFIX))
        self.assertIs(application.client_access.policy.writes_authorized, True)
        website = application.capabilities()["website"]
        self.assertEqual((website["browser_identity_available"], website["client_access_available"],
                          website["registration_available"]), (True, True, False))
        name = identity.publishable_key_ref[len(ENVIRONMENT_REFERENCE_PREFIX):]
        with patch.dict(os.environ, {name: ENVIRONMENT["FIXTURE_IDENTITY_PUBLIC"]}):
            public = application.browser_identity.public_configuration()
        self.assertEqual((public["registration_enabled"], public["email_signup_enabled"]), (True, False))
        with patch.dict(os.environ, {name: CREDENTIAL}), self.assertRaises(ServiceRuntimeError):
            application.browser_identity.public_configuration()

    def test_personal_keys_need_the_browser_identity_block(self):
        from loop_engine.core.service_runtime.http_entrypoint import load_host_application
        with self.assertRaises(ValueError):
            load_host_application(str(self.local_host(without=("browser_identity",))))
        application, _ = load_host_application(str(self.local_host(without=("client_access",))))
        self.assertIsNone(application.client_access)

    def test_guide_revocation_snippet_stops_sign_in_and_personal_keys(self):
        from loop_engine.core.service_runtime.access import ServiceAccessRequest, ServiceAccessSession
        from loop_engine.core.service_runtime.http_entrypoint import load_host_application
        from loop_engine.core.service_runtime.records import DEFAULT_SCOPES, ServiceRuntimeError, SubjectTenantRegistration
        snippets = [body for language, body in self.blocks if language == "python" and "revoke_subject" in body]
        self.assertEqual(len(snippets), 1)
        path = self.local_host()
        application, _ = load_host_application(str(path))
        identity = application.browser_identity.configuration
        issuer = identity.project_url + "/auth/v1"
        # A first sign-in, as the browser identity adapter performs it after it verified the person.
        account = SubjectTenantRegistration(issuer, self.SUBJECT, identity.namespace_prefix)
        self.assertIs(application.runtime.ensure_subject_tenant(account)["created"], True)
        principal = application.runtime.authenticate_subject(issuer, self.SUBJECT)
        session = ServiceAccessSession(principal.authentication_record_id, hashlib.sha256(b"fixture").hexdigest(),
                                       application.runtime._now() + 600, DEFAULT_SCOPES)
        issued = application.client_access.apply(principal, ServiceAccessRequest.from_customer_dict({
            "record_type": "service_client_access_request/v1", "operation": "issue", "request_id": "guide-check",
            "label": "Guide check", "scopes": ["provisioning:metadata"], "lifetime_seconds": 600},
            principal.tenant_id), session=session)
        self.assertEqual(application.runtime.authenticate_key(issued["token"]).tenant_id, account.tenant_id)

        def run_snippet(subject):
            """Run the documented snippet as the operator would: in a separate Python process."""
            source = snippets[0].replace('"/data/host.json"', repr(str(path)))
            source = source.replace('"the user_id field of the invitation report"', repr(subject))
            self.assertEqual(source.count(repr(str(path))) + source.count(repr(subject)), 2)
            return subprocess.run([sys.executable, "-c", source], capture_output=True, text=True, timeout=120,
                                  env={"PATH": os.environ.get("PATH", ""), "PYTHONPATH": str(ROOT / "src"),
                                       "PYTHONDONTWRITEBYTECODE": "1"})
        done = run_snippet(self.SUBJECT)
        self.assertEqual((done.returncode, done.stdout.strip()), (0, "{'committed': True, 'revoked': True}"), done.stderr)
        self.assertIn("`{'committed': True, 'revoked': True}`", self.text)
        for refused in (lambda: application.runtime.authenticate_subject(issuer, self.SUBJECT),
                        lambda: application.runtime.authenticate_key(issued["token"]),
                        lambda: application.runtime.ensure_subject_tenant(account)):
            with self.assertRaises(ServiceRuntimeError):
                refused()
        again = run_snippet(self.SUBJECT)
        self.assertEqual((again.returncode, again.stdout.strip()), (0, "{'committed': True, 'revoked': True}"), again.stderr)
        never_signed_in = run_snippet(OTHER_ID)
        self.assertEqual((never_signed_in.returncode, never_signed_in.stdout, never_signed_in.stderr.strip()),
                         (1, "", "refused: not_found"))
        for line in ("`refused: not_found`", "`refused: commit_unknown`"):
            self.assertIn(line, self.text)

    def test_guide_commands_use_only_options_the_command_accepts(self):
        accepted = {option for action in tool.build_parser()._actions for option in action.option_strings}
        commands = [body for language, body in self.blocks if language == "bash" and "tools/invite_beta_user.py" in body]
        self.assertGreaterEqual(len(commands), 2)
        for body in commands:
            used = set(re.findall(r"(?<![\w-])--[a-z][a-z-]+", body.split("tools/invite_beta_user.py", 1)[1]))
            self.assertTrue(used, body)
            self.assertLessEqual(used, accepted)
            self.assertIn("--acknowledge-identity-account-effects", used)
            self.assertIn("operator_credentials.py run --ref " + tool.DEFAULT_CREDENTIAL_REFERENCE, body)

    def test_guide_names_every_outcome_and_failure_the_command_can_report(self):
        self.assertGreaterEqual(len(tool.FAILURES), 10)
        self.assertGreaterEqual(len(tool.REFUSALS), 10)
        for value in (*[outcome.value for outcome in tool.InvitationOutcome], *tool.FAILURES, *tool.REFUSALS,
                      *tool.DETAILS, tool.REPORT_RECORD_TYPE, tool.INVITATION_MARKER):
            self.assertIn("`" + value + "`", self.text, value)

    def test_guide_prose_follows_the_public_language_rules(self):
        """Apply the repository's own rule files, so that no retired term is repeated here."""
        tokens = []
        for style in sorted((ROOT / ".vale" / "styles" / "LoopEngine").glob("*.yml")):
            tokens.extend(re.findall(r"^\s+- '(.+)'$", style.read_text("utf-8"), re.M))
        policy = json.loads((ROOT / "src" / "loop_engine" / "forbidden_paths.json").read_text("utf-8"))
        tokens.extend(r"\b" + re.escape(term) + r"\b" for term in policy["retired_source_nomenclature"]["terms"])
        self.assertGreaterEqual(len(tokens), 25)
        for token in tokens:
            with self.subTest(token=token):
                self.assertIsNone(re.search(token, self.text, re.I))
        self.assertIn("\n## Current behavior\n", self.text)
        self.assertIn("\n## Planned behavior\n", self.text)

    def test_guide_links_point_at_files_and_sections_that_exist(self):
        def anchors(text):
            return {re.sub(r"[^a-z0-9 -]", "", line.lstrip("# ").lower()).replace(" ", "-")
                    for line in text.splitlines() if line.startswith("#")}
        links = re.findall(r"\]\(([^)#\s]*)(?:#([^)\s]+))?\)", self.text)
        self.assertGreaterEqual(len(links), 8)
        for target, section in links:
            with self.subTest(target=target, section=section):
                self.assertFalse(target.startswith(("http:", "https:")), "this guide links to repository files only")
                path = (GUIDE.parent / target).resolve() if target else GUIDE
                self.assertTrue(path.is_file(), target)
                if section:
                    self.assertIn(section, anchors(path.read_text("utf-8")))


if __name__ == "__main__":
    unittest.main()
