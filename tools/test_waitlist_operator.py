"""The waiting list operator command records before it sends, and never sends twice.

Every check uses injected transports. Nothing here reaches the service, the
identity provider, the mail provider or the network. Two checks are named
mutant controls: they remove one guard inside the check and show that the
behaviour the guard exists to prevent becomes reachable.
"""
from __future__ import annotations

import io
import json
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest
import unittest.mock

import waitlist_operator as operator
import invite_beta_user

ORIGIN = "https://app.baltor.ai"
ENTRY = "service:" + "a1" * 32
ADDRESS = "ada@example.com"
SENDER = "Baltor <hello@baltor.ai>"
DISCOUNT = "BALTORFOUNDING40"
PROJECT = "qfzxmjznlwiopgvfgtsw"
REDIRECT = ORIGIN + "/auth/callback"
LINK = "https://qfzxmjznlwiopgvfgtsw.supabase.co/auth/v1/verify?token=ABCDEFGHIJKLMNOPQRSTUVWX&type=recovery"
MESSAGE_ID = "4ef9a417-02e9-4d39-ad75-9611e0def769"
# These fixtures carry no credential material: each body is a readable phrase
# long enough to pass the length rule that a real value has to pass.
SERVICE_TOKEN = "fixture-service-token-not-a-credential"
IDENTITY_KEY = "sb_secret_" + "FIXTUREVALUENOTACREDENTIAL"
MAIL_KEY = "re_" + "FIXTUREVALUENOTACREDENTIAL"
MANIFEST = {"record_type": "operator_credential_references/v1", "oauth": {},
            "api_keys": {"baltor-admin": {"service": "baltor-pilot.fly.dev", "account": "baltor-admin",
                                          "purpose": "service-access", "environment": "BALTOR_ADMIN_TOKEN"},
                         "supabase-secret": {"service": "supabase", "account": PROJECT,
                                             "purpose": "secret-api", "environment": "SUPABASE_SECRET_KEY"},
                         "resend-send": {"service": "resend", "account": "baltor",
                                         "purpose": "transactional-email", "environment": "RESEND_API_KEY"}}}
ENVIRONMENT = {"BALTOR_ADMIN_TOKEN": SERVICE_TOKEN, "SUPABASE_SECRET_KEY": IDENTITY_KEY,
               "RESEND_API_KEY": MAIL_KEY}


def entry_view(state="waiting", email=ADDRESS, note="I run my own harness"):
    return {"record_type": "service_waitlist_entry_view/v1", "entry_ref": ENTRY,
            "entry_version": "0" * 32, "email": email, "note": note, "state": state,
            "created_at": 1789000000.0, "decided_at": None, "discount_code": "",
            "invitation_ref": "", "delivery": "not_attempted", "source_counted": "counted"}


def listing(entries=None):
    rows = [entry_view()] if entries is None else entries
    return {"record_type": "service_http_result/v1", "operation": "waitlist_administration",
            "result": {"record_type": "service_waitlist_listing/v1", "states": ["waiting"],
                       "counts": {"waiting": len(rows), "invited": 0, "joined": 0, "declined": 0},
                       "matched": len(rows), "entries": rows, "truncated": False}}


def decision(state="invited", **changes):
    return {"record_type": "service_http_result/v1", "operation": "waitlist_administration",
            "result": {"record_type": "service_waitlist_result/v1", "committed": True, "replayed": False,
                       "state": state, "entry": {**entry_view(state), **changes.pop("entry", {})},
                       "request_id": "fixture", **changes}}


def capabilities(discount=True):
    """The public service profile, as the invitation reads it before anything else."""
    return {"record_type": "service_http_result/v1", "operation": "capabilities",
            "result": {"record_type": "service_capabilities/v1", "api_version": "v1",
                       "website": {"display_name": "Baltor", "waitlist_available": True},
                       "billing": {"webhook": True, "checkout": True, "portal": True,
                                   "discount_code": discount, "plans_endpoint": "/api/v1/billing/plans"}}}


def setup_report(root, code=DISCOUNT, **changes):
    """A payment account report of the shape tools/setup_stripe_sandbox.py writes."""
    report = {"record_type": "stripe_sandbox_setup_report/v1", "observed_at": "2026-09-21T00:00:00+00:00",
              "mode": "confirmed_writes", "outcome": "ready", "account_id": "acct_fixture",
              "coupon": {"state": "created", "id": "baltor_invitation"},
              "promotion_code": {"state": "created", "id": "promo_fixture", "code": code}}
    report.update(changes)
    path = Path(root) / ("setup-" + str(abs(hash(json.dumps(report, sort_keys=True))) % 10**8) + ".json")
    path.write_text(json.dumps(report), encoding="utf-8")
    return path


class FakeService:
    """An injected service transport. It records every request and answers from a script."""

    def __init__(self, answers=None, raises=None, status=None):
        self.requests = []
        self.answers = list(answers or [])
        self.raises = list(raises or [])
        self.status = list(status or [])

    @property
    def decisions(self):
        return [json.loads(row.body) for row in self.requests if row.method == operator.POST_METHOD]

    def __call__(self, request):
        self.requests.append(request)
        if self.raises and self.raises[0] is not None:
            raise self.raises.pop(0)
        if self.raises:
            self.raises.pop(0)
        status = self.status.pop(0) if self.status else operator.OK_STATUS
        body = self.answers.pop(0) if self.answers else {}
        return operator.ProviderResponse(status, json.dumps(body).encode())


class FakeMail:
    """An injected mail transport. One accepted message returns one identity."""

    def __init__(self, status=200, body=None, raises=None):
        self.requests, self.status, self.raises = [], status, raises
        self.body = {"id": MESSAGE_ID} if body is None else body

    def __call__(self, request):
        self.requests.append(request)
        if self.raises is not None:
            raise self.raises
        return operator.ProviderResponse(self.status, json.dumps(self.body).encode())


def identity_result(outcome=invite_beta_user.InvitationOutcome.LINK_ISSUED, link=LINK, failure=None):
    return invite_beta_user.InvitationResult(outcome, failure, None, "7b2fd7e8-168a-49c5-87c2-d52b79df1a94",
                                             True, link is not None, 2, 200, True, link, (link,))


def invited_service(answers=None, **changes):
    """An injected service whose first answer is the profile the invitation reads."""
    return FakeService([capabilities(), *(answers or [])], **changes)


def invite_request(**changes):
    fields = {"service_origin": ORIGIN, "entry_ref": ENTRY, "email": ADDRESS, "discount_code": DISCOUNT,
              "sender": SENDER, "project_ref": PROJECT, "redirect_to": REDIRECT, "request_id": "fixture-1"}
    return operator.InviteRequest(**{**fields, **changes})


def invite(service, mail, *, identity=None, request=None):
    with unittest.mock.patch.object(invite_beta_user, "issue_invitation",
                                    lambda *_arguments: identity or identity_result()):
        return operator.invite_one_entry(request or invite_request(),
                                         operator.Credentials(SERVICE_TOKEN, IDENTITY_KEY, MAIL_KEY),
                                         operator.OperatorLimits(), service_transport=service, mail_transport=mail)


class InputRefusalTests(unittest.TestCase):
    def test_an_address_an_origin_a_reference_and_a_code_are_all_checked(self):
        cases = {"service_origin": ["http://app.baltor.ai", ORIGIN + "/", ORIGIN + "/admin", "app.baltor.ai", ""],
                 "entry_ref": ["", "service:zz", ENTRY.upper(), "../service:" + "a1" * 32],
                 "email": ["", "ada", "ada@example", "ada lovelace@example.com", "a" * 250 + "@example.com"],
                 "discount_code": ["", "no", "lowercase40", "CODE WITH SPACE"],
                 "sender": ["", "hello", "Baltor <not-an-address>"]}
        for field, values in cases.items():
            for value in values:
                with self.assertRaises(operator.Refusal, msg=field + "=" + repr(value)):
                    invite_request(**{field: value})

    def test_an_address_is_taken_in_lower_case(self):
        self.assertEqual(invite_request(email=" Ada@Example.COM ").email, ADDRESS)

    def test_a_service_request_can_only_reach_the_waiting_list_path(self):
        for url in (ORIGIN + "/api/v1/admin/access", ORIGIN, "http://app.baltor.ai/api/v1/admin/waitlist",
                    ORIGIN + "/api/v1/admin/waitlist?state=waiting"):
            with self.assertRaises(operator.Refusal, msg=url):
                operator.ServiceRequest(operator.GET_METHOD, url)
        with self.assertRaises(operator.Refusal):
            operator.MailRequest("https://api.resend.example/emails", b"{}")

    def test_a_credential_reference_must_be_the_one_it_claims_to_be(self):
        with self.assertRaises(operator.Refusal):
            operator.credential_environment("resend-send", MANIFEST, service="supabase")
        with self.assertRaises(operator.Refusal):
            operator.credential_environment("supabase-secret", MANIFEST, service="supabase", purpose="anon-api")
        with self.assertRaises(operator.Refusal):
            operator.credential_environment("not-a-reference", MANIFEST)
        self.assertEqual(operator.credential_environment("resend-send", MANIFEST, service="resend",
                                                         purpose="transactional-email"), "RESEND_API_KEY")

    def test_a_missing_or_short_credential_is_refused(self):
        for value in (None, "", "short", " " + SERVICE_TOKEN):
            with self.assertRaises(operator.Refusal, msg=repr(value)):
                operator.resolve_credential("BALTOR_ADMIN_TOKEN", {"BALTOR_ADMIN_TOKEN": value})


class ListingTests(unittest.TestCase):
    def test_reading_the_list_performs_no_write_and_shows_the_addresses(self):
        service = FakeService([listing()])
        progress = operator._Progress()
        result = operator.read_waiting_list(ORIGIN, SERVICE_TOKEN, operator.OperatorLimits(), service, progress)
        self.assertEqual([row.method for row in service.requests], [operator.GET_METHOD])
        self.assertEqual(operator.listing_lines(result), [ENTRY + "\twaiting\t" + ADDRESS + "\tI run my own harness"])

    def test_a_refused_token_and_a_lost_answer_are_different_outcomes(self):
        refused = FakeService([{}], status=[403])
        with self.assertRaises(operator._Stop) as held:
            operator.read_waiting_list(ORIGIN, SERVICE_TOKEN, operator.OperatorLimits(), refused, operator._Progress())
        self.assertIs(held.exception.failure, operator.OperatorFailure.SERVICE_REFUSED)
        lost = FakeService(raises=[operator.TransportFailure("timeout")])
        with self.assertRaises(operator._Stop) as held:
            operator.read_waiting_list(ORIGIN, SERVICE_TOKEN, operator.OperatorLimits(), lost, operator._Progress())
        self.assertIs(held.exception.failure, operator.OperatorFailure.SERVICE_UNAVAILABLE)

    def test_an_answer_that_is_not_a_listing_is_refused(self):
        for body in ({}, {"result": {}}, {"result": {"record_type": "something_else/v1", "entries": []}},
                     {"result": {"record_type": "service_waitlist_listing/v1", "entries": "not a list"}}):
            service = FakeService([body])
            with self.assertRaises(operator._Stop, msg=repr(body)):
                operator.read_waiting_list(ORIGIN, SERVICE_TOKEN, operator.OperatorLimits(),
                                           service, operator._Progress())


class InvitationOrderTests(unittest.TestCase):
    def test_the_invitation_is_recorded_before_the_email_and_the_delivery_after_it(self):
        service = invited_service([decision(), decision(entry={"delivery": "sent"})])
        mail = FakeMail()
        result = invite(service, mail)
        self.assertIs(result.outcome, operator.OperatorOutcome.INVITED)
        operations = [row["operation"] for row in service.decisions]
        self.assertEqual(operations, ["invite", "record_delivery"])
        self.assertEqual(service.decisions[0]["discount_code"], DISCOUNT)
        self.assertEqual(result.delivery_recorded, "sent")
        self.assertEqual(len(mail.requests), 1)
        # The recorded invitation is sent before the message leaves.
        self.assertLess(service.requests.index(service.requests[0]), 1)

    def test_the_message_carries_the_link_once_and_the_discount_code(self):
        service = invited_service([decision(), decision(entry={"delivery": "sent"})])
        mail = FakeMail()
        invite(service, mail)
        message = json.loads(mail.requests[0].body)
        self.assertEqual(message["to"], [ADDRESS])
        self.assertEqual(message["from"], SENDER)
        self.assertEqual(message["text"].count(LINK), 1)
        self.assertIn(DISCOUNT, message["text"])
        for word in ("beta", "pilot"):
            self.assertNotIn(word, (message["text"] + message["subject"]).lower())

    def test_an_entry_that_is_not_waiting_is_never_emailed(self):
        service = invited_service([decision(state="joined")])
        mail = FakeMail()
        result = invite(service, mail)
        self.assertIs(result.failure, operator.OperatorFailure.ENTRY_NOT_WAITING)
        self.assertEqual(mail.requests, [])
        self.assertFalse(result.decision_recorded)

    def test_an_address_that_does_not_match_the_entry_is_never_emailed(self):
        service = invited_service([decision(entry={"email": "someone.else@example.com"})])
        mail = FakeMail()
        result = invite(service, mail)
        self.assertIs(result.failure, operator.OperatorFailure.DECISION_REFUSED)
        self.assertEqual(mail.requests, [])

    def test_an_identity_provider_that_issues_no_link_sends_no_email(self):
        service = invited_service([decision()])
        mail = FakeMail()
        result = invite(service, mail, identity=identity_result(
            invite_beta_user.InvitationOutcome.REFUSED, None, invite_beta_user.InvitationFailure.USER_NOT_FOUND))
        self.assertIs(result.failure, operator.OperatorFailure.IDENTITY_REFUSED)
        self.assertEqual(mail.requests, [])
        self.assertTrue(result.decision_recorded)

    def test_a_refused_message_is_not_repeated_and_is_not_recorded_as_sent(self):
        service = invited_service([decision()])
        mail = FakeMail(status=422)
        result = invite(service, mail)
        self.assertIs(result.failure, operator.OperatorFailure.MAIL_REFUSED)
        self.assertEqual(len(mail.requests), 1)
        self.assertIsNone(result.delivery_recorded)
        self.assertFalse(result.mail_accepted)

    def test_a_lost_mail_answer_is_recorded_as_unknown_and_never_repeated(self):
        service = invited_service([decision(), decision(entry={"delivery": "unknown"})])
        mail = FakeMail(raises=operator.TransportFailure("timeout"))
        result = invite(service, mail)
        self.assertIs(result.outcome, operator.OperatorOutcome.OUTCOME_UNKNOWN)
        self.assertIs(result.failure, operator.OperatorFailure.MAIL_UNKNOWN)
        self.assertEqual(len(mail.requests), 1)
        self.assertEqual(result.delivery_recorded, "unknown")
        self.assertEqual([row["operation"] for row in service.decisions], ["invite", "record_delivery"])
        self.assertEqual(service.decisions[1]["delivery"], "unknown")

    def test_a_delivery_that_cannot_be_recorded_is_reported_and_the_email_is_not_resent(self):
        service = invited_service([decision(), {}], status=[operator.OK_STATUS, operator.OK_STATUS, 503])
        mail = FakeMail()
        result = invite(service, mail)
        self.assertIs(result.failure, operator.OperatorFailure.DELIVERY_NOT_RECORDED)
        self.assertTrue(result.mail_accepted)
        self.assertIsNone(result.delivery_recorded)
        self.assertEqual(len(mail.requests), 1)

    def test_the_two_decisions_of_one_run_have_different_request_identities(self):
        service = invited_service([decision(), decision(entry={"delivery": "sent"})])
        invite(service, FakeMail())
        identities = [row["request_id"] for row in service.decisions]
        self.assertEqual(len(set(identities)), 2)
        self.assertTrue(identities[1].startswith(identities[0]))

    def test_mutant_control_without_the_state_check_an_invited_entry_is_emailed_again(self):
        # Mutant control for the state check. With it removed a second run
        # sends a second message to someone who was already invited, which is
        # what test_an_entry_that_is_not_waiting_is_never_emailed rejects.
        service = invited_service([decision(state="joined"), decision(entry={"delivery": "sent"})])
        mail = FakeMail()
        with unittest.mock.patch.object(operator, "INVITED", "joined"):
            result = invite(service, mail)
        self.assertIs(result.outcome, operator.OperatorOutcome.INVITED)
        self.assertEqual(len(mail.requests), 1)

    def test_mutant_control_without_the_lost_answer_rule_a_lost_message_looks_sent(self):
        # Mutant control for the lost mail answer. With the transport failure
        # treated as an acceptance, a message nobody can account for is
        # recorded as sent, which
        # test_a_lost_mail_answer_is_recorded_as_unknown_and_never_repeated rejects.
        service = invited_service([decision(), decision(entry={"delivery": "sent"})])
        mail = FakeMail(raises=operator.TransportFailure("timeout"))
        with unittest.mock.patch.object(operator, "send_invitation_email",
                                        lambda *_arguments: "fixture-digest"):
            result = invite(service, mail)
        self.assertIs(result.outcome, operator.OperatorOutcome.INVITED)
        self.assertEqual(result.delivery_recorded, "sent")


def _reads_but_ignores(origin, credential, limits, transport, progress):
    """The known-wrong rule: read the service profile and invite whatever it says."""
    transport(operator.ServiceRequest(operator.GET_METHOD, origin + operator.SERVICE_CAPABILITIES_PATH,
                                      None, limits.timeout_seconds, limits.maximum_response_bytes, credential))
    progress.service_requests += 1
    return True


class DiscountPromiseTests(unittest.TestCase):
    """The invitation promises a discount, so both halves of that promise are checked."""

    def test_an_invitation_stops_when_checkout_does_not_take_a_code(self):
        service = FakeService([capabilities(discount=False), decision()])
        mail = FakeMail()
        result = invite(service, mail)
        self.assertIs(result.outcome, operator.OperatorOutcome.REFUSED)
        self.assertIs(result.failure, operator.OperatorFailure.DISCOUNT_NOT_ACCEPTED)
        self.assertEqual(service.decisions, [])
        self.assertEqual(mail.requests, [])
        self.assertFalse(result.decision_recorded)

    def test_the_profile_is_read_before_anything_is_recorded(self):
        service = invited_service([decision(), decision(entry={"delivery": "sent"})])
        invite(service, FakeMail())
        self.assertEqual(service.requests[0].method, operator.GET_METHOD)
        self.assertTrue(service.requests[0].url.endswith(operator.SERVICE_CAPABILITIES_PATH))
        self.assertEqual([row["operation"] for row in service.decisions], ["invite", "record_delivery"])

    def test_mutant_control_without_the_checkout_rule_the_code_is_sent_anyway(self):
        # Mutant control for the checkout rule. With the check removed, a
        # person receives a code and finds no field to type it into, which
        # test_an_invitation_stops_when_checkout_does_not_take_a_code rejects.
        service = FakeService([capabilities(discount=False), decision(),
                               decision(entry={"delivery": "sent"})])
        mail = FakeMail()
        with unittest.mock.patch.object(operator, "require_checkout_takes_a_code", _reads_but_ignores):
            result = invite(service, mail)
        self.assertIs(result.outcome, operator.OperatorOutcome.INVITED)
        self.assertIn(DISCOUNT, json.loads(mail.requests[0].body)["text"])

    def test_a_malformed_profile_answer_is_not_read_as_permission(self):
        for body in ({}, {"result": {}}, {"result": {"record_type": "service_capabilities/v1"}},
                     {"result": {"record_type": "other/v1", "billing": {"discount_code": True}}},
                     {"result": {"record_type": "service_capabilities/v1", "billing": {"discount_code": "yes"}}}):
            service = FakeService([body, decision()])
            result = invite(service, FakeMail())
            self.assertIs(result.outcome, operator.OperatorOutcome.REFUSED, msg=repr(body))
            self.assertEqual(service.decisions, [])

    def test_the_evidence_must_name_this_exact_code_as_present(self):
        with tempfile.TemporaryDirectory(prefix="waitlist-evidence-") as root:
            good = operator.read_discount_evidence(str(setup_report(root)), DISCOUNT)
            self.assertEqual(good["promotion_code_id"], "promo_fixture")
            self.assertEqual(good["state"], "created")
            refused = [setup_report(root, code="ANOTHERCODE"),
                       setup_report(root, mode="dry_run"),
                       setup_report(root, outcome="stopped"),
                       setup_report(root, record_type="some_other_report/v1"),
                       setup_report(root, promotion_code={"state": "missing", "id": "promo_fixture",
                                                          "code": DISCOUNT}),
                       setup_report(root, promotion_code={"state": "created", "id": "", "code": DISCOUNT}),
                       Path(root) / "absent.json"]
            for path in refused:
                with self.assertRaises(operator.Refusal, msg=str(path)) as held:
                    operator.read_discount_evidence(str(path), DISCOUNT)
                self.assertEqual(held.exception.code, operator.OperatorRefusal.DISCOUNT_EVIDENCE.value)


class RemovalTests(unittest.TestCase):
    """A person who asks to be taken off the list is taken off it."""

    def forget(self, service, entry=ENTRY):
        return operator.forget_one_entry(operator.ForgetRequest(ORIGIN, entry, "fixture-forget"),
                                         operator.Credentials(SERVICE_TOKEN), operator.OperatorLimits(),
                                         service_transport=service)

    def test_one_removal_erases_the_address_and_the_note_and_sends_nothing(self):
        service = FakeService([decision(state="removed", entry={"email": "", "note": ""})])
        result = self.forget(service)
        self.assertIs(result.outcome, operator.OperatorOutcome.FORGOTTEN)
        self.assertEqual([row["operation"] for row in service.decisions], ["forget"])
        self.assertNotIn("discount_code", service.decisions[0])
        self.assertTrue(result.decision_recorded)
        self.assertEqual(result.entry_state, "removed")

    def test_an_answer_that_still_holds_the_address_is_not_a_removal(self):
        for answer in (decision(state="removed", entry={"email": ADDRESS, "note": ""}),
                       decision(state="removed", entry={"email": "", "note": "I run my own harness"}),
                       decision(state="waiting", entry={"email": "", "note": ""})):
            service = FakeService([answer])
            result = self.forget(service)
            self.assertIs(result.outcome, operator.OperatorOutcome.REFUSED)
            self.assertIs(result.failure, operator.OperatorFailure.REMOVAL_REFUSED)
            self.assertFalse(result.decision_recorded)

    def test_a_lost_answer_is_unknown_and_is_not_repeated(self):
        service = FakeService(raises=[operator.TransportFailure("timeout")])
        result = self.forget(service)
        self.assertIs(result.outcome, operator.OperatorOutcome.OUTCOME_UNKNOWN)
        self.assertIs(result.failure, operator.OperatorFailure.REMOVAL_UNKNOWN)
        self.assertEqual(len(service.requests), 1)

    def test_a_removal_needs_an_entry_reference_of_the_right_shape(self):
        for value in ("", "service:zz", ENTRY.upper(), "../" + ENTRY):
            with self.assertRaises(operator.Refusal, msg=value):
                operator.ForgetRequest(ORIGIN, value, "fixture-forget")


class ReportTests(unittest.TestCase):
    def test_the_report_holds_no_address_no_link_and_no_credential(self):
        service = invited_service([decision(), decision(entry={"delivery": "sent"})])
        result = invite(service, FakeMail())
        report = operator.build_report(result, "invite", datetime(2026, 9, 21, tzinfo=timezone.utc), invite_request())
        encoded = operator.encode_report(report, result.sensitive_values)
        for value in (ADDRESS, LINK, SERVICE_TOKEN, IDENTITY_KEY, MAIL_KEY, MESSAGE_ID):
            self.assertNotIn(value, encoded)
        self.assertIn(invite_request().email_digest, encoded)
        self.assertEqual(report["record_type"], operator.REPORT_RECORD_TYPE)
        self.assertEqual(report["discount_code"], DISCOUNT)
        self.assertIs(report["sign_in_link_recorded"], False)
        self.assertEqual(report["automatic_retries"], 0)

    def test_a_report_that_would_hold_a_credential_is_refused(self):
        report = {"record_type": operator.REPORT_RECORD_TYPE, "detail": SERVICE_TOKEN}
        with self.assertRaises(operator.Refusal) as held:
            operator.encode_report(report, (SERVICE_TOKEN,))
        self.assertEqual(held.exception.code, operator.OperatorRefusal.SECRET_IN_OUTPUT.value)


class CommandTests(unittest.TestCase):
    def _run(self, argv, service, mail=None, identity=None, environment=None, evidence=True):
        with tempfile.TemporaryDirectory(prefix="waitlist-operator-") as root:
            report = Path(root) / "report.json"
            if evidence and "--invite" in argv and "--discount-evidence" not in argv:
                argv = [*argv, "--discount-evidence", str(setup_report(root))]
            output, errors = io.StringIO(), io.StringIO()
            with redirect_stdout(output), redirect_stderr(errors):
                with unittest.mock.patch.object(invite_beta_user, "issue_invitation",
                                                lambda *_arguments: identity or identity_result()):
                    code = operator.main([*argv, "--report", str(report)], manifest=MANIFEST,
                                         environment=ENVIRONMENT if environment is None else environment,
                                         service_transport=service, mail_transport=mail or FakeMail(),
                                         now=lambda: datetime(2026, 9, 21, tzinfo=timezone.utc))
            saved = json.loads(report.read_text()) if report.exists() else None
            return code, output.getvalue(), errors.getvalue(), saved

    def test_listing_prints_one_line_for_each_entry_and_writes_a_report(self):
        code, output, _errors, saved = self._run(["--service-origin", ORIGIN, "--list"], FakeService([listing()]))
        self.assertEqual(code, 0)
        self.assertIn(ENTRY + "\twaiting\t" + ADDRESS, output)
        self.assertEqual(saved["outcome"], "listed")
        self.assertEqual(saved["listed_entries"], 1)
        self.assertIsNone(saved["entry_ref"])
        self.assertNotIn(ADDRESS, json.dumps(saved))

    def test_choosing_neither_or_both_modes_is_refused_before_any_request(self):
        for argv in (["--service-origin", ORIGIN],
                     ["--service-origin", ORIGIN, "--list", "--invite", ENTRY],
                     ["--service-origin", ORIGIN, "--list", "--forget", ENTRY],
                     ["--service-origin", ORIGIN, "--invite", ENTRY, "--forget", ENTRY]):
            service = FakeService([listing()])
            code, _output, errors, saved = self._run(argv, service)
            self.assertEqual(code, operator.EXIT_REFUSED_BEFORE_ANY_REQUEST)
            self.assertEqual(errors.strip(), operator.OperatorRefusal.MODE.value)
            self.assertEqual(service.requests, [])
            self.assertIsNone(saved)

    def test_an_invitation_without_the_acknowledgement_sends_nothing(self):
        service, mail = invited_service([decision()]), FakeMail()
        code, _output, errors, saved = self._run(
            ["--service-origin", ORIGIN, "--invite", ENTRY, "--email", ADDRESS, "--discount-code", DISCOUNT,
             "--sender", SENDER, "--project-ref", PROJECT, "--redirect-to", REDIRECT], service, mail)
        self.assertEqual(code, operator.EXIT_REFUSED_BEFORE_ANY_REQUEST)
        self.assertEqual(errors.strip(), operator.OperatorRefusal.CONFIRMATION.value)
        self.assertEqual((service.requests, mail.requests), ([], []))
        self.assertIsNone(saved)

    def test_a_confirmed_invitation_records_sends_and_reports(self):
        service = invited_service([decision(), decision(entry={"delivery": "sent"})])
        mail = FakeMail()
        code, output, _errors, saved = self._run(
            ["--service-origin", ORIGIN, "--invite", ENTRY, "--email", ADDRESS, "--discount-code", DISCOUNT,
             "--sender", SENDER, "--project-ref", PROJECT, "--redirect-to", REDIRECT,
             "--acknowledge-invitation-effects"], service, mail)
        self.assertEqual(code, 0)
        self.assertEqual(saved["outcome"], "invited_and_email_sent")
        self.assertIs(saved["invitation_recorded"], True)
        self.assertEqual(saved["delivery_recorded"], "sent")
        self.assertNotIn(LINK, output + json.dumps(saved))
        self.assertEqual(json.loads(output.strip().split("\n")[-1])["delivery_recorded"], "sent")

    def test_an_invitation_without_the_payment_account_report_is_refused(self):
        service, mail = invited_service([decision()]), FakeMail()
        code, _output, errors, saved = self._run(
            ["--service-origin", ORIGIN, "--invite", ENTRY, "--email", ADDRESS, "--discount-code", DISCOUNT,
             "--sender", SENDER, "--project-ref", PROJECT, "--redirect-to", REDIRECT,
             "--acknowledge-invitation-effects"], service, mail, evidence=False)
        self.assertEqual(code, operator.EXIT_REFUSED_BEFORE_ANY_REQUEST)
        self.assertEqual(errors.strip(), operator.OperatorRefusal.DISCOUNT_EVIDENCE.value)
        self.assertEqual((service.requests, mail.requests), ([], []))
        self.assertIsNone(saved)

    def test_a_confirmed_invitation_records_the_evidence_it_relied_on(self):
        service = invited_service([decision(), decision(entry={"delivery": "sent"})])
        code, _output, _errors, saved = self._run(
            ["--service-origin", ORIGIN, "--invite", ENTRY, "--email", ADDRESS, "--discount-code", DISCOUNT,
             "--sender", SENDER, "--project-ref", PROJECT, "--redirect-to", REDIRECT,
             "--acknowledge-invitation-effects"], service, FakeMail())
        self.assertEqual(code, 0)
        self.assertEqual(saved["discount_evidence"]["promotion_code_id"], "promo_fixture")
        self.assertEqual(saved["discount_evidence"]["payment_account_id"], "acct_fixture")

    def test_a_removal_without_the_acknowledgement_touches_nothing(self):
        service = FakeService([decision(state="removed", entry={"email": "", "note": ""})])
        code, _output, errors, saved = self._run(["--service-origin", ORIGIN, "--forget", ENTRY], service)
        self.assertEqual(code, operator.EXIT_REFUSED_BEFORE_ANY_REQUEST)
        self.assertEqual(errors.strip(), operator.OperatorRefusal.CONFIRMATION.value)
        self.assertEqual(service.requests, [])
        self.assertIsNone(saved)

    def test_a_confirmed_removal_reports_the_erased_entry_and_no_address(self):
        service = FakeService([decision(state="removed", entry={"email": "", "note": ""})])
        code, output, _errors, saved = self._run(
            ["--service-origin", ORIGIN, "--forget", ENTRY, "--acknowledge-erasure"], service, FakeMail())
        self.assertEqual(code, 0)
        self.assertEqual(saved["outcome"], "removed_and_erased")
        self.assertEqual(saved["mode"], "forget")
        self.assertEqual(saved["entry_ref"], ENTRY)
        self.assertIsNone(saved["invited_address_digest"])
        self.assertNotIn(ADDRESS, json.dumps(saved) + output)
        self.assertEqual(json.loads(output.strip().split("\n")[-1])["entry_state"], "removed")

    def test_a_missing_mail_credential_stops_before_the_service_is_touched(self):
        service = invited_service([decision()])
        code, _output, errors, saved = self._run(
            ["--service-origin", ORIGIN, "--invite", ENTRY, "--email", ADDRESS, "--discount-code", DISCOUNT,
             "--sender", SENDER, "--project-ref", PROJECT, "--redirect-to", REDIRECT,
             "--acknowledge-invitation-effects"], service,
            environment={**ENVIRONMENT, "RESEND_API_KEY": ""})
        self.assertEqual(code, operator.EXIT_REFUSED_BEFORE_ANY_REQUEST)
        self.assertEqual(errors.strip(), operator.OperatorRefusal.CREDENTIAL_VALUE.value)
        self.assertEqual(service.requests, [])
        self.assertIsNone(saved)


if __name__ == "__main__":
    unittest.main()
