"""Checks for public sign-up and password recovery email.

The adapter runs with injected transports, so no identity provider and no mail
provider is contacted and no message is ever sent. The two real transport
functions run against loopback listeners that this module starts and stops
itself, so that refusing a redirect, the response ceiling, the request deadline
and the ignored proxy settings are observed rather than asserted. The service
is also driven through its ASGI interface with a chosen client address, the way
the request limit checks drive it. A removed-guard control reruns a scenario
with the guard patched away and requires that scenario's own predicate to fail.
"""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import re
import threading
import time
from unittest.mock import patch

from . import account_email as module
from .account_email import (
    CONFIGURATION_RECORD_TYPE, CONFIRMATION_SENT, GENERATE_LINK_PATH, IDENTITY_SECRET_PREFIX,
    MAIL_SECRET_PREFIX, MAIL_SEND_PATH, PROVIDER_PROFILE, RECOVERY_ACTION, RECOVERY_RESULT_VERSION, RECOVERY_SENT,
    SERVICE_REFUSAL_STATUSES, SIGNUP_ACTION, SIGNUP_RESULT_VERSION, AccountEmailAdapter, AccountEmailConfiguration,
    AccountEmailError, AccountMailRequest, IdentityLinkRequest, PreparedAccountRequest, ProviderAnswer,
    counted_email_key, email_address, generate_identity_link, password_for_signup, send_account_mail,
)
from .http import ServiceHttpApplication
from .http_auth import HttpAuthenticationError
from .http_test_fixtures import HttpDomainFixture, running_http
from .records import ServiceRuntimeError
from .request_limits import (
    HEADER_SOURCE, LIMIT_REACHED_CODE, SOCKET_PEER_SOURCE, FailedAttemptLimiter, ServiceRequestLimits,
)

HOST, ORIGIN = "service.test", "https://service.test"
IDENTITY_ORIGIN = "https://project.identity.test"
MAIL_ORIGIN = "https://mail.test"
DISPLAY_NAME = "Baltor"
# Documentation address ranges and reserved names: no check names a real
# machine, a real mailbox or a real credential.
FIRST, SECOND = "198.51.100.10", "198.51.100.20"
NEW_ADDRESS, KNOWN_ADDRESS = "new.person@example.com", "known.person@example.com"
SIGNUP_SECRET_VALUE = "a-long-enough-chosen-phrase"
IDENTITY_KEY_REFERENCE, MAIL_KEY_REFERENCE = "env:FIXTURE_IDENTITY_KEY", "env:FIXTURE_MAIL_KEY"
IDENTITY_KEY_VALUE = IDENTITY_SECRET_PREFIX + "FIXTURE_ONLY_NOT_A_REAL_KEY"
MAIL_KEY_VALUE = MAIL_SECRET_PREFIX + "FIXTURE_ONLY_NOT_A_REAL_KEY"
TOKEN_HASH_VALUE = "pkce_fixture0token0hash0value"
# The link the identity provider generates for itself. This service never
# reads it and never puts it in a message.
PROVIDER_LINK = IDENTITY_ORIGIN + "/auth/v1/verify?token=provider-owned&type=signup"
SIGNUP_REQUEST = {"record_type": "service_account_signup_request/v1", "email": NEW_ADDRESS,
                  "password": SIGNUP_SECRET_VALUE}
RECOVERY_REQUEST = {"record_type": "service_account_recovery_request/v1", "email": NEW_ADDRESS}


def _secrets(reference):
    values = {IDENTITY_KEY_REFERENCE: IDENTITY_KEY_VALUE, MAIL_KEY_REFERENCE: MAIL_KEY_VALUE}
    if reference not in values:
        raise ServiceRuntimeError("configured_secret_unavailable")
    return values[reference]


def _settings(**changes):
    chosen = {"identity_origin": IDENTITY_ORIGIN, "identity_service_key_ref": IDENTITY_KEY_REFERENCE,
              "mail_api_key_ref": MAIL_KEY_REFERENCE, "sender_address": "accounts@auth.example.com",
              "sender_name": DISPLAY_NAME, "mail_origin": MAIL_ORIGIN, "signup_enabled": True,
              "recovery_enabled": True, "allow_network": True}
    chosen.update(changes)
    return AccountEmailConfiguration(**chosen)


def _host_block(**changes):
    return {"record_type": CONFIGURATION_RECORD_TYPE, "identity_origin": IDENTITY_ORIGIN,
            "identity_service_key_ref": IDENTITY_KEY_REFERENCE, "mail_origin": MAIL_ORIGIN,
            "mail_api_key_ref": MAIL_KEY_REFERENCE, "sender_address": "accounts@auth.example.com",
            "signup_enabled": True, "recovery_enabled": True, "allow_network": True, **changes}


def _link_answer(token_hash=TOKEN_HASH_VALUE, action=SIGNUP_ACTION, email=NEW_ADDRESS):
    """The answer the identity provider gives when it generated a link.

    The top-level shape follows the saved probe of the real endpoint,
    `artifacts/architecture-audit-2026-09-19/account-email-path-probe-1.json`.
    """
    return ProviderAnswer(200, {"action_link": PROVIDER_LINK, "email_otp": "123456", "hashed_token": token_hash,
                                "verification_type": action, "redirect_to": IDENTITY_ORIGIN + "/",
                                "id": "00000000-0000-0000-0000-000000000000", "email": email,
                                "confirmation_sent_at": "2026-09-21T10:46:59Z"})


#: Refusal bodies this service must survive without changing what a caller
#: sees. Nothing in this repository records which of these the endpoint really
#: sends, so the source reads no field of a refusal body at all and every one
#: of these takes the same path. The two written codes are the ones the
#: provider's published error-code list names for these two situations.
UNEXPECTED_REFUSAL_BODIES = (
    {"code": 422, "msg": "User already registered"},
    {"code": "email_exists", "msg": "User already registered"},
    {"error_code": "email_exists", "msg": "User already registered"},
    {"code": 404, "msg": "User not found"},
    {"error_code": "user_not_found", "message": "User not found"},
    {},
)


def _ineligible(action):
    """The answer that names the address as not eligible for this action."""
    return ProviderAnswer(422 if action == SIGNUP_ACTION else 404,
                          {"code": 422, "error_code": "fixture_refusal", "msg": "fixture refusal"})


def _sent():
    return ProviderAnswer(200, {"id": "00000000-0000-0000-0000-000000000001"})


def _chosen(answers, standing):
    """The next chosen answer, or the standing one. A chosen failure is raised."""
    answer = answers.pop(0) if answers else standing
    if isinstance(answer, BaseException):
        raise answer
    return answer


class _Provider:
    """Injected transports that record every request and answer from a list."""

    def __init__(self, identity_answers=(), mail_answers=()):
        self.identity_requests, self.mail_requests = [], []
        self.identity_answers, self.mail_answers = list(identity_answers), list(mail_answers)

    def identity(self, request, secret):
        self.identity_requests.append((request, secret))
        # The standing answer names the address and the action that were asked
        # for, as the real endpoint does, so that a check which does not choose
        # an answer still exercises the binding rule rather than avoiding it.
        return _chosen(self.identity_answers, _link_answer(action=request.action, email=request.email))

    def mail(self, request, secret):
        self.mail_requests.append((request, secret))
        return _chosen(self.mail_answers, _sent())

    @property
    def sent_bodies(self):
        return [request.text_body for request, _secret in self.mail_requests]


def _adapter(provider, settings=None, *, address_limits=None, secret_resolver=None):
    return AccountEmailAdapter(settings or _settings(), secret_resolver or _secrets, public_base_url=ORIGIN,
        address_limits=address_limits or ServiceRequestLimits(client_address_source=SOCKET_PEER_SOURCE),
        display_name=DISPLAY_NAME, identity_transport=provider.identity, mail_transport=provider.mail)


def _answer_for(adapter, fields, action=SIGNUP_ACTION, address=FIRST):
    return adapter.deliver(adapter.prepare(action, fields, address))


def _refusal(function):
    """Return the refusal code and status of one operation, or empty text and 200."""
    try:
        function()
    except AccountEmailError as error:
        return error.code, error.status
    except ServiceRuntimeError as error:
        return error.code, 0
    return "", 200


def _refused(function):
    """Return the refusal code of one operation, or empty text when it was accepted."""
    return _refusal(function)[0]


def _refuses(function):
    try:
        function()
    except (AttributeError, TypeError, ValueError):
        return True
    return False


def _configuration_checks(check):
    settings = _settings()
    check("account_email_settings_are_an_immutable_versioned_record",
          settings.record_type == CONFIGURATION_RECORD_TYPE and settings.provider_profile == PROVIDER_PROFILE
          and _refuses(lambda: setattr(settings, "signup_enabled", False))
          and _refuses(lambda: _settings(record_type="service_account_email_configuration/v2"))
          and _refuses(lambda: _settings(provider_profile="another_provider_pair/v1")))
    closed = AccountEmailConfiguration(IDENTITY_ORIGIN, IDENTITY_KEY_REFERENCE, MAIL_ORIGIN,
                                       MAIL_KEY_REFERENCE, "accounts@auth.example.com")
    check("sign_up_recovery_and_network_are_closed_until_the_host_opens_them",
          (closed.signup_enabled, closed.recovery_enabled, closed.allow_network) == (False, False, False)
          and _refuses(lambda: AccountEmailConfiguration(IDENTITY_ORIGIN, IDENTITY_KEY_REFERENCE,
                                                         MAIL_KEY_REFERENCE, "accounts@auth.example.com")))
    unsafe = [{"signup_enabled": "yes"}, {"recovery_enabled": 1}, {"allow_network": None}, {"allow_loopback": "no"}]
    unsafe += [{"identity_origin": value} for value in (
        "http://project.identity.test", IDENTITY_ORIGIN + "/auth/v1", "not-a-url", "", IDENTITY_ORIGIN + "?a=b")]
    unsafe += [{"mail_origin": value} for value in ("http://mail.test", MAIL_ORIGIN + "/emails", "ftp://mail.test")]
    unsafe += [{"identity_service_key_ref": value} for value in ("", "FIXTURE_IDENTITY_KEY", "secret:NAME", "env:", 5)]
    unsafe += [{"mail_api_key_ref": value} for value in ("", "keyring:NAME", None)]
    unsafe += [{"sender_address": value} for value in ("", "accounts", "accounts@", "a b@example.com", 7)]
    unsafe += [{"sender_name": value} for value in ("a@b", "Name, Other", 'Say "hello"', " Baltor", "N" * 65)]
    unsafe += [{"minimum_password_length": value} for value in (7, 73, 12.0, True, "12")]
    unsafe += [{"timeout_seconds": value} for value in (0, -1, 31, float("inf"), float("nan"), "5")]
    unsafe += [{"maximum_response_bytes": value} for value in (0, 262_145, 1.0, True)]
    unsafe += [{"attempts_for_each_email": value} for value in (0, 1001, 3.0)]
    unsafe += [{"attempt_window_seconds": value} for value in (0.5, 86_401, float("nan"))]
    unsafe += [{"tracked_emails": value} for value in (0, 65_537)]
    check("account_email_settings_refuse_unsafe_values",
          all(_refuses(lambda row=row: _settings(**row)) for row in unsafe))
    check("a_loopback_identity_origin_needs_explicit_loopback_authority",
          _refuses(lambda: _settings(identity_origin="http://127.0.0.1:9999"))
          and _settings(identity_origin="http://127.0.0.1:9999", mail_origin="http://127.0.0.1:9998",
                        allow_loopback=True).identity_origin == "http://127.0.0.1:9999")
    inexact = ({**_host_block(), "email_signup": True}, {**_host_block(), "record_type": "service_account_email/v1"},
               {key: value for key, value in _host_block().items() if key != "record_type"},
               _host_block(provider_profile="another_provider_pair/v1"), [_host_block()], "account_email")
    check("a_host_block_with_unknown_keys_or_another_version_is_refused",
          AccountEmailConfiguration.from_host(_host_block()).signup_enabled is True
          and all(_refused(lambda row=row: AccountEmailConfiguration.from_host(row))
                  in ("unsupported_account_email_configuration",) for row in inexact))
    check("the_address_table_follows_the_stated_source_and_the_email_table_is_always_active",
          settings.address_attempt_limits(ServiceRequestLimits()).active is False
          and settings.address_attempt_limits(ServiceRequestLimits(
              client_address_source=HEADER_SOURCE, client_address_header="Fly-Client-IP")).client_address_header
          == "Fly-Client-IP"
          and settings.email_attempt_limits().active is True
          and settings.email_attempt_limits().failures_allowed == settings.attempts_for_each_email)


def _address_and_password_checks(check):
    check("one_address_is_read_in_one_form",
          email_address("  User.Name+tag@Example.COM ") == "user.name+tag@example.com"
          and email_address("a@b.co") == "a@b.co")
    unusable = ("", "a@b", "a@@b.co", "a b@c.de", "a@-b.co", "a@b-.co", "a@b..co", ".a@b.co", "a.@b.co",
                "a..b@c.de", "a@b.co ndelivery", "аccounts@example.com", "a@exa mple.co", "a@b.c_d",
                "a@" + "b" * 250 + ".co", "x" * 65 + "@b.co", 7, None, "a@b.co\n")
    check("an_address_this_service_cannot_read_is_refused_before_any_provider_request",
          all(_refused(lambda row=row: email_address(row)) == "invalid_email_address" for row in unusable))
    check("a_password_is_refused_when_it_is_short_over_the_block_limit_or_the_address_itself",
          password_for_signup(SIGNUP_SECRET_VALUE, NEW_ADDRESS, 12) == SIGNUP_SECRET_VALUE
          and _refused(lambda: password_for_signup("short", NEW_ADDRESS, 12)) == "invalid_password"
          and _refused(lambda: password_for_signup("x" * 73, NEW_ADDRESS, 12)) == "invalid_password"
          and _refused(lambda: password_for_signup("long enough\tvalue", NEW_ADDRESS, 12)) == "invalid_password"
          and _refused(lambda: password_for_signup(NEW_ADDRESS, NEW_ADDRESS, 12))
          == "password_matches_the_email_address"
          and _refused(lambda: password_for_signup(" NEW.Person@EXAMPLE.com ", NEW_ADDRESS, 12))
          == "password_matches_the_email_address")
    check("the_counted_email_key_keeps_no_address",
          len(counted_email_key(NEW_ADDRESS)) == 64 and NEW_ADDRESS not in counted_email_key(NEW_ADDRESS)
          and counted_email_key(NEW_ADDRESS) != counted_email_key(KNOWN_ADDRESS))


def _same_answer(provider_answer, fields=None, action=SIGNUP_ACTION):
    """Run one request with the chosen identity answer, and return what a caller sees.

    A refusal is returned as its code and its status rather than raised, so
    that a control which removes a guard turns a named check false instead of
    ending the run before the remaining checks report.
    """
    provider = _Provider(identity_answers=[provider_answer])
    adapter = _adapter(provider)
    try:
        seen = _answer_for(adapter, fields if fields is not None else SIGNUP_REQUEST, action)
    except AccountEmailError as error:
        seen = (error.code, error.status)
    return seen, provider


def _caller_answer(provider_answer):
    """What a caller sees, the messages sent, and the one message body."""
    seen, provider = _same_answer(provider_answer)
    return seen, len(provider.mail_requests), "".join(provider.sent_bodies)


def _delivery_checks(check):
    known, existing = _same_answer(_link_answer()), _same_answer(_ineligible(SIGNUP_ACTION))
    new_result, new_provider = known
    existing_result, existing_provider = existing
    link = ORIGIN + "/auth/confirm?token_hash=" + TOKEN_HASH_VALUE + "&type=signup"
    check("sign_up_answers_the_same_record_for_a_new_and_an_existing_address",
          new_result == existing_result == {"record_type": SIGNUP_RESULT_VERSION, "status": CONFIRMATION_SENT}
          and len(new_provider.mail_requests) == len(existing_provider.mail_requests) == 1
          and len(new_provider.identity_requests) == len(existing_provider.identity_requests) == 1)
    sent_new, sent_existing = "".join(new_provider.sent_bodies), "".join(existing_provider.sent_bodies)
    check("the_message_carries_this_service_link_and_never_the_provider_link",
          link in sent_new and PROVIDER_LINK not in sent_new and IDENTITY_ORIGIN not in sent_new
          and TOKEN_HASH_VALUE not in sent_existing and "/auth/confirm" not in sent_existing
          and ORIGIN + "/login" in sent_existing)
    request, secret = new_provider.identity_requests[0]
    mail_request, mail_secret = new_provider.mail_requests[0]
    check("each_provider_request_is_bound_to_its_own_fixed_origin_key_and_fields",
          request.url == IDENTITY_ORIGIN + GENERATE_LINK_PATH and request.action == SIGNUP_ACTION
          and request.email == NEW_ADDRESS and request.password == SIGNUP_SECRET_VALUE
          and secret == IDENTITY_KEY_VALUE and mail_secret == MAIL_KEY_VALUE
          and mail_request.url == MAIL_ORIGIN + MAIL_SEND_PATH
          and mail_request.sender == DISPLAY_NAME + " <accounts@auth.example.com>"
          and mail_request.recipient == NEW_ADDRESS and SIGNUP_SECRET_VALUE not in mail_request.text_body)
    recovery, recovery_provider = _same_answer(_link_answer(action=RECOVERY_ACTION),
                                               RECOVERY_REQUEST, RECOVERY_ACTION)
    missing, missing_provider = _same_answer(_ineligible(RECOVERY_ACTION), RECOVERY_REQUEST, RECOVERY_ACTION)
    check("recovery_answers_the_same_record_for_a_known_and_an_unknown_address",
          recovery == missing == {"record_type": RECOVERY_RESULT_VERSION, "status": RECOVERY_SENT}
          and "&type=recovery" in "".join(recovery_provider.sent_bodies)
          and recovery_provider.identity_requests[0][0].password == ""
          and TOKEN_HASH_VALUE not in "".join(missing_provider.sent_bodies)
          and ORIGIN + "/signup" in "".join(missing_provider.sent_bodies))
    check("the_answer_is_the_same_length_of_work_for_both_addresses",
          len(recovery_provider.mail_requests) == len(missing_provider.mail_requests) == 1)
    unexpected = [_caller_answer(ProviderAnswer(status, body)) for status in (400, 404, 409, 422)
                  for body in UNEXPECTED_REFUSAL_BODIES]
    check("a_refusal_body_this_release_does_not_read_gives_the_same_answer_as_an_eligible_address",
          all(seen == new_result and sent == 1 and TOKEN_HASH_VALUE not in body
              for seen, sent, body in unexpected))
    check("a_refusal_of_this_service_itself_is_reported_and_no_message_is_sent",
          all(_caller_answer(ProviderAnswer(status, body))[:2] == (("identity_link_refused", 503), 0)
              for status in SERVICE_REFUSAL_STATUSES for body in UNEXPECTED_REFUSAL_BODIES))
    bound = ({"hashed_token": TOKEN_HASH_VALUE, "email": "victim@example.com", "verification_type": SIGNUP_ACTION},
             {"hashed_token": TOKEN_HASH_VALUE, "email": NEW_ADDRESS, "verification_type": RECOVERY_ACTION},
             {"hashed_token": TOKEN_HASH_VALUE, "verification_type": SIGNUP_ACTION},
             {"hashed_token": TOKEN_HASH_VALUE, "email": NEW_ADDRESS},
             {"hashed_token": TOKEN_HASH_VALUE, "email": 7, "verification_type": SIGNUP_ACTION})
    check("a_link_that_names_another_address_or_another_action_is_never_put_in_a_message",
          all(_caller_answer(ProviderAnswer(200, row))[:2] == (("identity_link_unusable", 503), 0)
              for row in bound)
          and _caller_answer(ProviderAnswer(200, {"hashed_token": TOKEN_HASH_VALUE, "email": NEW_ADDRESS.upper(),
                                                  "verification_type": SIGNUP_ACTION}))[0] == new_result)


def _unknown_outcome_checks(check):
    outcomes = {}
    for name, identity_answers, mail_answers in (
            ("provider_outage", [ProviderAnswer(500, {"msg": "fixture outage"})], []),
            # A refused server key is about this service, not about the
            # address, so the caller may see it. A 400 is not in that group any
            # more; `_delivery_checks` proves that it keeps the 202 instead.
            ("another_refusal", [ProviderAnswer(401, {"error_code": "bad_jwt"})], []),
            ("unusable_token", [_link_answer(token_hash="not a usable token")], []),
            ("missing_token", [ProviderAnswer(200, {"action_link": PROVIDER_LINK})], []),
            ("broken_connection", [OSError("fixture connection failure")], []),
            ("mail_refusal", [_link_answer()], [ProviderAnswer(422, {"message": "fixture refusal"})]),
            ("mail_outage", [_link_answer()], [ProviderAnswer(503, {})]),
            ("mail_deadline", [_link_answer()], [TimeoutError("fixture deadline")])):
        provider = _Provider(identity_answers=identity_answers, mail_answers=mail_answers)
        adapter = _adapter(provider)
        code, status = _refusal(lambda: _answer_for(adapter, SIGNUP_REQUEST))
        outcomes[name] = (code, len(provider.identity_requests), len(provider.mail_requests), status)
    check("an_outage_a_refusal_and_an_unusable_link_are_reported_without_a_second_request",
          outcomes["provider_outage"][:3] == ("identity_link_unavailable", 1, 0)
          and outcomes["another_refusal"][:3] == ("identity_link_refused", 1, 0)
          and outcomes["unusable_token"][:3] == ("identity_link_unusable", 1, 0)
          and outcomes["missing_token"][:3] == ("identity_link_unusable", 1, 0)
          and outcomes["broken_connection"][:3] == ("identity_link_unavailable", 1, 0))
    check("a_mail_refusal_and_a_mail_deadline_are_separate_and_neither_sends_twice",
          outcomes["mail_refusal"][:3] == ("account_mail_refused", 1, 1)
          and outcomes["mail_outage"][:3] == ("account_mail_unavailable", 1, 1)
          and outcomes["mail_deadline"][:3] == ("account_mail_unavailable", 1, 1))
    check("every_unknown_outcome_answers_503_so_the_caller_is_never_told_it_was_sent",
          all(row[3] == 503 for row in outcomes.values()))
    closed = _Provider()
    adapter = _adapter(closed, _settings(signup_enabled=False))
    open_recovery = _adapter(_Provider(), _settings(allow_network=False))
    check("a_closed_operation_refuses_with_a_stable_code_and_makes_no_provider_request",
          _refused(lambda: _answer_for(adapter, SIGNUP_REQUEST)) == "account_signup_unavailable"
          and _refused(lambda: _answer_for(open_recovery, RECOVERY_REQUEST, RECOVERY_ACTION))
          == "account_recovery_unavailable"
          and adapter.availability() == {"signup_available": False, "recovery_available": True}
          and open_recovery.availability() == {"signup_available": False, "recovery_available": False}
          and (closed.identity_requests, closed.mail_requests) == ([], []))
    wrong_key, missing_key = _Provider(), _Provider()
    swapped = _adapter(wrong_key, secret_resolver=lambda reference: MAIL_KEY_VALUE)
    absent = _adapter(missing_key, secret_resolver=lambda reference: "")
    check("a_key_of_the_wrong_kind_or_no_key_stops_the_request_before_it_leaves",
          _refused(lambda: _answer_for(swapped, SIGNUP_REQUEST)) == "account_email_secret_unusable"
          and _refused(lambda: _answer_for(absent, SIGNUP_REQUEST)) == "account_email_secret_unusable"
          and (wrong_key.identity_requests, missing_key.identity_requests) == ([], []))


def _malformed_checks(check):
    adapter = _adapter(_Provider())
    malformed = ({}, {"record_type": "service_account_signup_request/v1", "email": NEW_ADDRESS},
                 {**SIGNUP_REQUEST, "extra": 1}, {**SIGNUP_REQUEST, "record_type": "service_account_signup_request/v2"},
                 {**SIGNUP_REQUEST, "email": "not an address"}, {**SIGNUP_REQUEST, "password": "short"},
                 [SIGNUP_REQUEST], None, {"record_type": "service_account_recovery_request/v1", "email": NEW_ADDRESS})
    codes = [_refused(lambda row=row: adapter.prepare(SIGNUP_ACTION, row, FIRST)) for row in malformed]
    check("a_request_this_release_does_not_understand_is_refused_before_any_provider_request",
          all(code for code in codes) and codes[4] == "invalid_email_address"
          and codes[5] == "invalid_password" and codes[0] == codes[1] == codes[2] == "invalid_account_signup")
    extra = {"record_type": "service_account_recovery_request/v1", "email": NEW_ADDRESS, "password": "anything here"}
    check("a_recovery_request_carries_no_password_and_an_unknown_route_is_refused",
          _refused(lambda: adapter.prepare(RECOVERY_ACTION, extra, FIRST)) == "invalid_account_recovery"
          and _refused(lambda: adapter.prepare("invite", RECOVERY_REQUEST, FIRST)) == "route_unavailable"
          and _refused(lambda: adapter.prepare(SIGNUP_ACTION, SIGNUP_REQUEST, "")) == "invalid_request"
          and _refuses(lambda: adapter.deliver({"action": SIGNUP_ACTION})))


def _no_secret_checks(check):
    provider = _Provider(identity_answers=[_link_answer()])
    adapter = _adapter(provider)
    _answer_for(adapter, SIGNUP_REQUEST)
    identity_request = provider.identity_requests[0][0]
    mail_request = provider.mail_requests[0][0]
    prepared = PreparedAccountRequest(SIGNUP_ACTION, NEW_ADDRESS, SIGNUP_SECRET_VALUE)
    printed = " ".join((repr(identity_request), repr(mail_request), repr(prepared), repr(adapter.configuration),
                        str(identity_request), str(mail_request)))
    secrets = (SIGNUP_SECRET_VALUE, NEW_ADDRESS, TOKEN_HASH_VALUE, IDENTITY_KEY_VALUE, MAIL_KEY_VALUE,
               IDENTITY_KEY_REFERENCE, MAIL_KEY_REFERENCE)
    check("no_address_password_token_or_key_appears_in_the_printed_form_of_a_record",
          not any(value in printed for value in secrets))
    talkative = ProviderAnswer(500, {"msg": SIGNUP_SECRET_VALUE + " " + TOKEN_HASH_VALUE + " " + PROVIDER_LINK})
    code, message = "", ""
    try:
        _answer_for(_adapter(_Provider(identity_answers=[talkative])), SIGNUP_REQUEST)
    except AccountEmailError as error:
        code = error.code
        message = " ".join((str(error), repr(error), json.dumps(error.details), json.dumps(error.headers)))
    check("a_refusal_carries_a_code_and_never_the_provider_message_or_a_secret",
          code == "identity_link_unavailable" and message
          and not any(value in message for value in (*secrets, PROVIDER_LINK)))


def _limit_checks(check):
    provider = _Provider()
    adapter = _adapter(provider, _settings(attempts_for_each_address=3, attempts_for_each_email=2))
    accepted = [_refused(lambda index=index: _answer_for(adapter,
                dict(SIGNUP_REQUEST, email="a%d@example.com" % index), address=FIRST)) for index in range(4)]
    check("the_client_address_allowance_refuses_the_fourth_attempt_and_asks_it_to_wait",
          accepted[:3] == ["", "", ""] and accepted[3] == LIMIT_REACHED_CODE and len(provider.mail_requests) == 3)
    waiting = _waiting_refusal(adapter, FIRST)
    check("the_refusal_carries_the_typed_record_and_the_seconds_to_wait",
          waiting[0]["record_type"] == "service_request_limit_refusal/v1"
          and waiting[0]["retry_after_seconds"] >= 1 and waiting[1]["Retry-After"] == str(waiting[0]["retry_after_seconds"]))
    for_each_email = _adapter(_Provider(), _settings(attempts_for_each_address=50, attempts_for_each_email=2))
    from_many = [_refused(lambda index=index: _answer_for(for_each_email, SIGNUP_REQUEST,
                 address="198.51.100.%d" % index)) for index in range(1, 5)]
    check("one_email_address_cannot_be_flooded_from_many_client_addresses",
          from_many == ["", "", LIMIT_REACHED_CODE, LIMIT_REACHED_CODE]
          and _refused(lambda: _answer_for(for_each_email, dict(SIGNUP_REQUEST, email=KNOWN_ADDRESS),
                                           address="198.51.100.9")) == "")
    check("the_table_of_attempts_holds_digests_and_no_address",
          counted_email_key(NEW_ADDRESS) in for_each_email.email_attempts._failures
          and not any(NEW_ADDRESS in key for key in for_each_email.email_attempts._failures))
    check("an_open_operation_with_no_stated_client_address_source_is_refused_before_it_serves",
          _refused(lambda: _adapter(_Provider(), _settings(), address_limits=ServiceRequestLimits()))
          == "account_email_needs_a_stated_client_address_source"
          and _refused(lambda: _adapter(_Provider(), _settings(recovery_enabled=False),
                                        address_limits=ServiceRequestLimits()))
          == "account_email_needs_a_stated_client_address_source"
          and _refused(lambda: _adapter(_Provider(), _settings(signup_enabled=False, recovery_enabled=False),
                                        address_limits=ServiceRequestLimits())) == ""
          and _refused(lambda: _adapter(_Provider(), _settings(), address_limits=ServiceRequestLimits(
              client_address_source=HEADER_SOURCE, client_address_header=PROXY_HEADER))) == "")
    moving = _adapter(_Provider(), _settings(attempts_for_each_address=1, attempts_for_each_email=50,
                                             attempt_window_seconds=60))
    _answer_for(moving, dict(SIGNUP_REQUEST, email="c1@example.com"), address=SECOND)
    blocked = _refused(lambda: _answer_for(moving, dict(SIGNUP_REQUEST, email="c2@example.com"), address=SECOND))
    started = moving.address_attempts.clock
    moving.address_attempts.clock = lambda: started() + 61
    check("the_allowance_returns_when_the_window_has_passed",
          blocked == LIMIT_REACHED_CODE
          and _refused(lambda: _answer_for(moving, dict(SIGNUP_REQUEST, email="c3@example.com"),
                                           address=SECOND)) == "")


def _waiting_refusal(adapter, address):
    try:
        _answer_for(adapter, SIGNUP_REQUEST, address=address)
    except AccountEmailError as error:
        return error.details, error.headers
    return {}, {}


class _IdentityStandIn:
    """An injected browser identity behind the browser_identity/v1 boundary."""

    protocol_version = "browser_identity/v1"

    class configuration:
        project_url = IDENTITY_ORIGIN

    def __init__(self, runtime):
        self.runtime = runtime

    def public_configuration(self):
        return {"record_type": "browser_identity_public_configuration/v1", "project_url": IDENTITY_ORIGIN,
                "registration_enabled": True, "email_signup_enabled": True}

    def authenticate(self, _credential):
        raise HttpAuthenticationError()


PROXY_HEADER = "Fly-Client-IP"


def _running(fixture, provider, settings=None, *, installed=True):
    """Build the real application for a loopback socket, with or without the adapter."""
    def build(configuration):
        adapter = AccountEmailAdapter(settings or _settings(allow_loopback=True), _secrets,
            public_base_url=configuration.public_base_url, address_limits=configuration.request_limits,
            display_name=configuration.display_name, identity_transport=provider.identity,
            mail_transport=provider.mail) if installed else None
        return ServiceHttpApplication(fixture.runtime, fixture.provisioning, configuration,
            browser_identity=_IdentityStandIn(fixture.runtime), account_email=adapter)
    return build


def _fixture(root, name):
    (root / name).mkdir(parents=True)
    return HttpDomainFixture(root / name)


def _service_checks(check, root):
    """The routes over real sockets, with the client address in the host's stated header."""
    import httpx
    limits = ServiceRequestLimits(client_address_source=HEADER_SOURCE, client_address_header=PROXY_HEADER)
    fixture = _fixture(root, "open")
    provider = _Provider(identity_answers=[_link_answer(), _ineligible(SIGNUP_ACTION),
                                           ProviderAnswer(422, {"code": 422, "msg": "User already registered"})])
    with running_http(fixture, application_factory=_running(fixture, provider), display_name=DISPLAY_NAME,
                      request_limits=limits) as (base, _service):
        with httpx.Client(base_url=base, trust_env=False, timeout=5) as client:
            new = client.post("/api/v1/account/signup", json=SIGNUP_REQUEST)
            existing = client.post("/api/v1/account/signup", json=SIGNUP_REQUEST)
            unread = client.post("/api/v1/account/signup", json=SIGNUP_REQUEST)
            check("the_real_route_answers_202_with_the_same_bytes_for_a_new_and_an_existing_address",
                  new.status_code == existing.status_code == unread.status_code == 202
                  and new.content == existing.content == unread.content
                  and new.json()["result"] == {"record_type": SIGNUP_RESULT_VERSION, "status": CONFIRMATION_SENT}
                  and new.json()["operation"] == "account_signup" and new.headers["cache-control"] == "no-store"
                  and len(provider.mail_requests) == 3)
            check("the_answer_carries_no_address_password_token_or_link",
                  not any(value in new.text for value in (SIGNUP_SECRET_VALUE, NEW_ADDRESS, TOKEN_HASH_VALUE,
                                                          PROVIDER_LINK, IDENTITY_KEY_VALUE, MAIL_KEY_VALUE)))
            identity = client.get("/api/v1/account/identity").json()["result"]
            check("the_identity_route_reports_whether_sign_up_and_recovery_are_available",
                  identity["signup_available"] is True and identity["recovery_available"] is True
                  and identity["redirect_url"] == base + "/auth/callback")
            malformed = client.post("/api/v1/account/signup", json={"record_type": "another/v1"})
            page = client.get("/auth/confirm")
            # Another method on the same path is not this route, so only the exact method reaches a
            # provider. Since September 21, 2026 the router compares the address and the method with
            # its own table before it asks who is calling, so the answer is a missing route and not a
            # credential problem; `an_address_the_service_does_not_serve_answers_missing_not_unauthorized`
            # in http_checks owns that rule and this check follows it.
            other_method = client.get("/api/v1/account/signup")
            check("a_malformed_request_is_400_another_method_reaches_no_provider_and_the_page_is_served",
                  malformed.status_code == 400 and malformed.json()["error"]["code"] == "invalid_account_signup"
                  and malformed.json()["automatic_retry"] is False and len(provider.identity_requests) == 3
                  and other_method.status_code == 404
                  and other_method.json()["error"]["code"] == "route_unavailable"
                  and "www-authenticate" not in other_method.headers and page.status_code == 200
                  and page.headers["content-type"].startswith("text/html"))
    fixture = _fixture(root, "limited")
    many = _Provider()
    settings = _settings(allow_loopback=True, attempts_for_each_address=2, attempts_for_each_email=50)
    with running_http(fixture, application_factory=_running(fixture, many, settings), display_name=DISPLAY_NAME,
                      request_limits=limits) as (base, _service):
        with httpx.Client(base_url=base, trust_env=False, timeout=5) as client:
            def signup(address, value):
                return client.post("/api/v1/account/signup", json=dict(SIGNUP_REQUEST, email=value),
                                   headers={PROXY_HEADER: address})
            statuses = [signup(FIRST, "d%d@example.com" % index).status_code for index in range(3)]
            over = signup(FIRST, "d9@example.com")
            check("the_real_route_refuses_an_address_over_its_allowance_with_429_and_Retry_After",
                  statuses == [202, 202, 429] and over.status_code == 429
                  and over.headers["retry-after"].isdigit()
                  and over.json()["error"]["code"] == LIMIT_REACHED_CODE
                  and signup(SECOND, NEW_ADDRESS).status_code == 202)
    quiet = _Provider()
    fixture = _fixture(root, "closed")
    settings = _settings(allow_loopback=True, signup_enabled=False, recovery_enabled=False)
    with running_http(fixture, application_factory=_running(fixture, quiet, settings)) as (base, _service):
        with httpx.Client(base_url=base, trust_env=False, timeout=5) as client:
            switched_off = client.post("/api/v1/account/signup", json=SIGNUP_REQUEST)
    fixture = _fixture(root, "absent")
    with running_http(fixture, application_factory=_running(fixture, quiet, installed=False)) as (base, _service):
        with httpx.Client(base_url=base, trust_env=False, timeout=5) as client:
            without = client.post("/api/v1/account/recovery", json=RECOVERY_REQUEST)
            identity = client.get("/api/v1/account/identity").json()["result"]
    check("a_closed_or_absent_operation_answers_a_stable_code_and_reaches_no_provider",
          switched_off.status_code == 503
          and switched_off.json()["error"]["code"] == "account_signup_unavailable"
          and without.status_code == 404 and without.json()["error"]["code"] == "account_email_unavailable"
          and identity["signup_available"] is False and identity["recovery_available"] is False
          and (quiet.identity_requests, quiet.mail_requests) == ([], []))
    fixture = _fixture(root, "boundary")
    check("an_adapter_that_speaks_another_account_email_boundary_is_refused_before_the_routes_are_served",
          _another_boundary_is_refused(fixture)
          and _shut(ServiceHttpApplication(fixture.runtime, fixture.provisioning, _loopback_configuration(),
              browser_identity=_IdentityStandIn(fixture.runtime),
              account_email=_adapter(_Provider()))).account_email.protocol_version == "account_email/v1")
    from . import http as http_module
    with patch.object(http_module, "speaks_the_account_email_boundary", lambda adapter: True):
        check("removed_account_email_boundary_rule_is_detected", not _another_boundary_is_refused(fixture))


def _another_boundary_is_refused(fixture):
    """An adapter with another declared boundary, and one with none, are both refused."""
    return all(_refuses(lambda installed=installed: ServiceHttpApplication(fixture.runtime, fixture.provisioning,
               _loopback_configuration(), browser_identity=_IdentityStandIn(fixture.runtime),
               account_email=installed)) for installed in (_OtherBoundary(), object()))


class _OtherBoundary:
    """An adapter with the whole surface and another declared boundary version."""

    protocol_version = "account_email/v2"

    def availability(self):
        return {"signup_available": True, "recovery_available": True}

    def prepare(self, action, request_fields, address_key):
        raise AccountEmailError("route_unavailable", 404)

    def deliver(self, prepared):
        raise AccountEmailError("route_unavailable", 404)


def _loopback_configuration():
    from .http import ServiceHttpConfiguration
    return ServiceHttpConfiguration("http://127.0.0.1:8123", ("127.0.0.1:8123",), allow_loopback_http=True,
                                    display_name=DISPLAY_NAME,
                                    request_limits=ServiceRequestLimits(client_address_source=SOCKET_PEER_SOURCE))


def _shut(application):
    """Stop the worker pool an application started, and return the application."""
    application._workers.shutdown(wait=True)
    return application


class _Listener:
    """One owned loopback listener that answers what the running check chose."""

    def __init__(self):
        self.requests = []
        self.state = {"status": 200, "payload": {"hashed_token": TOKEN_HASH_VALUE}, "raw": None,
                      "location": "", "delay": 0.0, "drip": 0.0}
        listener = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get("Content-Length") or 0)
                listener.requests.append({"path": self.path, "body": self.rfile.read(length),
                                          "headers": {name.lower(): value for name, value in self.headers.items()}})
                if listener.state["delay"]:
                    time.sleep(listener.state["delay"])
                raw = listener.state["raw"]
                body = raw if raw is not None else json.dumps(listener.state["payload"]).encode()
                self.send_response(listener.state["status"])
                if listener.state["location"]:
                    self.send_header("Location", listener.state["location"])
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                drip = listener.state["drip"]
                if not drip:
                    self.wfile.write(body)
                    return
                # A provider that keeps sending a few bytes: every single read
                # arrives well inside the client's own read deadline, so only a
                # total bound on the body read can end this answer.
                try:
                    for start in range(0, len(body), 8):
                        self.wfile.write(body[start:start + 8])
                        self.wfile.flush()
                        time.sleep(drip)
                except (BrokenPipeError, ConnectionResetError):
                    # The reader stopped at its deadline, which is the point of
                    # the check that chose this answer.
                    self.close_connection = True

            def log_message(self, *_arguments):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.worker = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.worker.start()
        self.origin = "http://127.0.0.1:%d" % self.server.server_port

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.worker.join(3)


def _identity_request(origin, timeout_seconds=3.0, maximum_response_bytes=65_536):
    return IdentityLinkRequest(origin + GENERATE_LINK_PATH, SIGNUP_ACTION, NEW_ADDRESS, SIGNUP_SECRET_VALUE,
                               timeout_seconds, maximum_response_bytes)


def _transport_checks(check):
    listener = _Listener()
    try:
        answer = generate_identity_link(_identity_request(listener.origin), IDENTITY_KEY_VALUE)
        seen = listener.requests[0]
        sent = json.loads(seen["body"])
        check("the_identity_request_carries_the_documented_fields_and_the_server_key",
              answer == ProviderAnswer(200, {"hashed_token": TOKEN_HASH_VALUE})
              and seen["path"] == GENERATE_LINK_PATH and sent == {"type": SIGNUP_ACTION, "email": NEW_ADDRESS,
                                                                  "password": SIGNUP_SECRET_VALUE}
              and "redirect_to" not in sent
              and seen["headers"]["apikey"] == IDENTITY_KEY_VALUE
              and seen["headers"]["authorization"] == "Bearer " + IDENTITY_KEY_VALUE)
        mail = AccountMailRequest(listener.origin + MAIL_SEND_PATH, "Baltor <accounts@auth.example.com>",
                                  NEW_ADDRESS, "Confirm your Baltor account", "Open this link:\n" + ORIGIN, 3.0, 65_536)
        listener.state["payload"] = {"id": "fixture-message"}
        send_account_mail(mail, MAIL_KEY_VALUE)
        sent = json.loads(listener.requests[1]["body"])
        check("the_mail_request_carries_the_documented_fields_and_one_recipient",
              sent == {"from": "Baltor <accounts@auth.example.com>", "to": [NEW_ADDRESS],
                       "subject": "Confirm your Baltor account", "text": "Open this link:\n" + ORIGIN}
              and listener.requests[1]["headers"]["authorization"] == "Bearer " + MAIL_KEY_VALUE)
        check("the_client_is_built_with_no_redirects_and_no_inherited_proxy_settings",
              _client_arguments(listener) == {"follow_redirects": False, "trust_env": False})
        listener.state.update({"status": 200, "location": "", "raw": b"{\"hashed_token\": \"" + b"x" * 4096 + b"\"}"})
        oversized = _refused(lambda: generate_identity_link(_identity_request(listener.origin,
            maximum_response_bytes=256), IDENTITY_KEY_VALUE))
        listener.state["raw"] = b"not json at all"
        unreadable = _refused(lambda: generate_identity_link(_identity_request(listener.origin), IDENTITY_KEY_VALUE))
        listener.state["raw"] = b"{\"hashed_token\": \"a\", \"hashed_token\": \"b\"}"
        ambiguous = _refused(lambda: generate_identity_link(_identity_request(listener.origin), IDENTITY_KEY_VALUE))
        check("an_oversized_an_unreadable_and_an_ambiguous_answer_are_refused",
              oversized == unreadable == ambiguous == "identity_link_unavailable")
        listener.state.update({"raw": None, "delay": 1.5})
        before = len(listener.requests)
        late = _refused(lambda: generate_identity_link(_identity_request(listener.origin, timeout_seconds=0.25),
                                                       IDENTITY_KEY_VALUE))
        check("a_silent_provider_passes_the_read_deadline_and_nothing_is_sent_again",
              late == "identity_link_unavailable" and len(listener.requests) == before + 1)
        listener.state["delay"] = 0.0
        check("a_provider_that_sends_a_few_bytes_at_a_time_cannot_hold_a_worker_past_the_deadline",
              _dripping_answer_is_refused(listener))
        with patch.object(module, "within_the_deadline", lambda deadline: True):
            check("removed_total_body_deadline_is_detected", not _dripping_answer_is_refused(listener))
        check("a_request_ignores_the_proxy_settings_of_its_environment",
              _reaches_through_proxy_settings(listener))
        check("a_wire_record_refuses_another_path_a_query_and_the_wrong_action",
              _refuses(lambda: IdentityLinkRequest(listener.origin + "/auth/v1/token", SIGNUP_ACTION, NEW_ADDRESS,
                                                   SIGNUP_SECRET_VALUE, 3.0, 65_536))
              and _refuses(lambda: IdentityLinkRequest(listener.origin + GENERATE_LINK_PATH + "?a=b", SIGNUP_ACTION,
                                                       NEW_ADDRESS, SIGNUP_SECRET_VALUE, 3.0, 65_536))
              and _refuses(lambda: IdentityLinkRequest(listener.origin + GENERATE_LINK_PATH, "invite", NEW_ADDRESS,
                                                       SIGNUP_SECRET_VALUE, 3.0, 65_536))
              and _refuses(lambda: IdentityLinkRequest(listener.origin + GENERATE_LINK_PATH, RECOVERY_ACTION,
                                                       NEW_ADDRESS, SIGNUP_SECRET_VALUE, 3.0, 65_536))
              and _refuses(lambda: AccountMailRequest(listener.origin + "/send", "a@b.co", NEW_ADDRESS, "s", "b",
                                                      3.0, 65_536))
              and _refuses(lambda: generate_identity_link({"url": listener.origin}, IDENTITY_KEY_VALUE))
              and _refuses(lambda: send_account_mail({"url": listener.origin}, MAIL_KEY_VALUE)))
    finally:
        listener.close()


def _dripping_answer_is_refused(listener):
    """One answer sent in small pieces, each well inside the client's read deadline."""
    listener.state.update({"raw": b'{"hashed_token": "' + b"a" * 380 + b'"}', "drip": 0.05})
    started = time.monotonic()
    try:
        code = _refused(lambda: generate_identity_link(_identity_request(listener.origin, timeout_seconds=0.5),
                                                       IDENTITY_KEY_VALUE))
    finally:
        listener.state.update({"raw": None, "drip": 0.0})
    return code == "identity_link_unavailable" and time.monotonic() - started < 2.0


def _client_arguments(listener):
    """The settings the transport gives its client, observed once."""
    import httpx
    seen = {}
    build = httpx.Client

    def recording(*arguments, **keywords):
        seen.update({name: keywords.get(name) for name in ("follow_redirects", "trust_env")})
        return build(*arguments, **keywords)

    with patch.object(httpx, "Client", recording):
        generate_identity_link(_identity_request(listener.origin), IDENTITY_KEY_VALUE)
    return seen


def _reaches_through_proxy_settings(listener):
    """Send one request while the environment names a proxy that does not exist."""
    unreachable = "http://198.51.100.250:9"
    previous = {name: os.environ.get(name) for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY")}
    before = len(listener.requests)
    try:
        for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"):
            os.environ[name] = unreachable
        os.environ.pop("NO_PROXY", None)
        answer = generate_identity_link(_identity_request(listener.origin, timeout_seconds=5.0), IDENTITY_KEY_VALUE)
    finally:
        for name in previous:
            os.environ.pop(name, None)
        os.environ.update({name: value for name, value in previous.items() if value is not None})
    return answer.status_code == 200 and len(listener.requests) == before + 1


def _host_file_checks(check, root):
    """The mapping the operations guide gives, through the real host loader."""
    from .http_entrypoint import HOST_CONFIGURATION_VERSION, MANIFEST_VERSION, load_host_application
    root.mkdir()
    manifest = root / "manifest.json"
    manifest.write_text(json.dumps({"record_type": MANIFEST_VERSION, "artifact_root": str(root), "items": []}))
    identity = {"project_url": IDENTITY_ORIGIN, "publishable_key_ref": "env:FIXTURE_PUBLISHABLE_KEY",
                "namespace_prefix": "customer", "registration_enabled": True, "email_signup_enabled": True,
                "allow_network": True}

    from .request_limits import REQUEST_LIMITS_RECORD_TYPE
    stated = {"record_type": REQUEST_LIMITS_RECORD_TYPE, "client_address_source": HEADER_SOURCE,
              "client_address_header": PROXY_HEADER}

    def load(name, *, request_limits=stated, **blocks):
        path = root / (name + ".json")
        transport = {"public_base_url": ORIGIN, "allowed_hosts": [HOST], "display_name": DISPLAY_NAME}
        if request_limits is not None:
            transport["request_limits"] = request_limits
        path.write_text(json.dumps({"record_type": HOST_CONFIGURATION_VERSION, "manifest_path": str(manifest),
            "runtime": {"database_path": str(root / (name + ".db")), "writes_authorized": True},
            "http": transport, "authentication": {}, **blocks}))
        application = load_host_application(str(path))[0]
        application._workers.shutdown(wait=True)
        return application

    application = load("open", browser_identity=identity, account_email=_host_block())
    check("the_documented_host_block_installs_the_adapter_through_the_real_host_loader",
          application.account_email is not None
          and application.account_email.protocol_version == "account_email/v1"
          and application.account_email.availability() == {"signup_available": True, "recovery_available": True}
          and application.account_email.transport_basis == "provider_https"
          and application.account_email.public_base_url == ORIGIN
          and application.account_email.display_name == DISPLAY_NAME
          and load("none", browser_identity=identity).account_email is None)
    check("account_email_needs_the_browser_identity_of_the_same_project",
          _refused(lambda: load("alone", account_email=_host_block()))
          == "account_email_requires_browser_identity"
          and _refused(lambda: load("other", browser_identity=identity,
                                    account_email=_host_block(identity_origin="https://other.identity.test")))
          == "account_email_identity_origin_mismatch")
    check("a_host_file_with_an_unknown_account_email_key_stops_the_loader_before_it_serves",
          _refused(lambda: load("unknown", browser_identity=identity,
                                account_email={**_host_block(), "send_from": "a@b.co"}))
          == "unsupported_account_email_configuration")
    closed_registration = {**identity, "registration_enabled": False, "email_signup_enabled": False}

    def closed_registration_stops_open_sign_up(name):
        return (_refused(lambda: load(name + "_closed", browser_identity=closed_registration,
                                      account_email=_host_block()))
                == "account_email_signup_needs_open_registration"
                and _refused(lambda: load(name + "_no_email_signup",
                                          browser_identity={**identity, "email_signup_enabled": False},
                                          account_email=_host_block()))
                == "account_email_signup_needs_open_registration")

    check("open_sign_up_against_closed_account_creation_stops_the_loader_before_it_serves",
          closed_registration_stops_open_sign_up("first")
          # Recovery alone stays permitted while account creation is closed,
          # because a person who already has an account may need a new password.
          and load("recovery_only", browser_identity=closed_registration,
                   account_email=_host_block(signup_enabled=False)).account_email.availability()
          == {"signup_available": False, "recovery_available": True})
    from . import http_entrypoint as entrypoint
    with patch.object(entrypoint, "signup_matches_the_browser_identity",
                      lambda settings, browser_identity: True):
        check("removed_open_registration_rule_is_detected",
              not closed_registration_stops_open_sign_up("mutant"))
    check("a_host_file_that_opens_an_operation_without_a_stated_address_source_stops_the_loader",
          _refused(lambda: load("unstated", request_limits=None, browser_identity=identity,
                                account_email=_host_block()))
          == "account_email_needs_a_stated_client_address_source"
          and load("unstated_closed", request_limits=None, browser_identity=identity,
                   account_email=_host_block(signup_enabled=False, recovery_enabled=False)).account_email is not None)


def _unusable_token_is_refused():
    provider = _Provider(identity_answers=[_link_answer(token_hash="a token with spaces")])
    return (_refused(lambda: _answer_for(_adapter(provider), SIGNUP_REQUEST)) == "identity_link_unusable"
            and not provider.mail_requests)


def _same_answer_holds():
    """A refusal this release does not read gives the eligible answer and one message."""
    try:
        eligible, _first = _same_answer(_link_answer())
        for body in UNEXPECTED_REFUSAL_BODIES:
            unread, provider = _same_answer(ProviderAnswer(422, body))
            if unread != eligible or len(provider.mail_requests) != 1:
                return False
        return True
    except (AccountEmailError, ServiceRuntimeError):
        return False


def _link_is_bound_to_the_address_asked_for():
    """A link naming another address or another action is never put in a message."""
    foreign = ProviderAnswer(200, {"hashed_token": TOKEN_HASH_VALUE, "email": "victim@example.com",
                                   "verification_type": SIGNUP_ACTION})
    other_action = ProviderAnswer(200, {"hashed_token": TOKEN_HASH_VALUE, "email": NEW_ADDRESS,
                                        "verification_type": RECOVERY_ACTION})
    return all(_caller_answer(row)[:2] == (("identity_link_unusable", 503), 0)
               for row in (foreign, other_action))


def _one_address_cannot_send_without_limit():
    """One client address sends at most its allowance, whatever the recipient is.

    With the rule in place the adapter is never built, so the unlimited state
    cannot exist. With the rule removed the adapter is built and one address
    sends a message to every recipient it names.
    """
    try:
        adapter = _adapter(_Provider(), _settings(attempts_for_each_address=1, attempts_for_each_email=50),
                           address_limits=ServiceRequestLimits())
    except ServiceRuntimeError:
        return True
    sent = [_refused(lambda index=index: _answer_for(adapter, dict(SIGNUP_REQUEST,
            email="flood%d@example.com" % index), address=FIRST)) for index in range(25)]
    return sent.count("") <= 1


def _an_open_operation_needs_a_stated_address_source():
    return (_refused(lambda: _adapter(_Provider(), _settings(), address_limits=ServiceRequestLimits()))
            == "account_email_needs_a_stated_client_address_source")


def _email_allowance_holds():
    adapter = _adapter(_Provider(identity_answers=[_link_answer() for _each in range(10)]),
                       _settings(attempts_for_each_address=50, attempts_for_each_email=2))
    return [_refused(lambda index=index: _answer_for(adapter, SIGNUP_REQUEST, address="198.51.100.%d" % index))
            for index in range(1, 5)] == ["", "", LIMIT_REACHED_CODE, LIMIT_REACHED_CODE]


def _wrong_kind_of_key_is_refused():
    provider = _Provider()
    swapped = _adapter(provider, secret_resolver=lambda reference: MAIL_KEY_VALUE)
    return (_refused(lambda: _answer_for(swapped, SIGNUP_REQUEST)) == "account_email_secret_unusable"
            and not provider.identity_requests)


def _redirect_is_not_followed(first, second):
    """A redirect answer is refused, and the address it names is never asked."""
    first.state.update({"status": 307, "location": second.origin + GENERATE_LINK_PATH})
    before = len(second.requests)
    code = _refused(lambda: generate_identity_link(_identity_request(first.origin), IDENTITY_KEY_VALUE))
    return code == "identity_link_unavailable" and len(second.requests) == before


def _following_client(build):
    def following(*arguments, **keywords):
        return build(*arguments, **{**keywords, "follow_redirects": True})
    return following


def _mutant_controls(check):
    """Each control removes one guard and requires a named check to fail."""
    check("an_unusable_token_hash_is_refused_before_a_message_is_sent", _unusable_token_is_refused())
    with patch.object(module, "TOKEN_HASH", re.compile(r"[\s\S]*")):
        check("removed_token_hash_rule_is_detected", not _unusable_token_is_refused())
    check("the_same_answer_rule_holds", _same_answer_holds())
    # The removed guard is the one the previous revision had: recognise one
    # refusal code and refuse everything else. It reads a field of the refusal
    # body, so an answer written another way splits the two addresses apart.
    with patch.object(module, "SERVICE_REFUSAL_STATUSES", (401, 403, 404, 409, 422, 429)):
        check("removed_unexpected_refusal_rule_is_detected", not _same_answer_holds())
    check("the_link_is_bound_to_the_address_and_the_action_asked_for",
          _link_is_bound_to_the_address_asked_for())
    with patch.object(module, "TOKEN_HASH", re.compile(r"[\s\S]*")):
        check("the_binding_rule_is_not_the_token_hash_rule", _link_is_bound_to_the_address_asked_for())
    for removed in ("names_the_same_address", "names_the_same_action"):
        with patch.object(module, removed, lambda payload, expected: True):
            check("removed_" + removed + "_is_detected", not _link_is_bound_to_the_address_asked_for())
    check("the_stated_address_source_rule_holds", _an_open_operation_needs_a_stated_address_source())
    check("one_client_address_cannot_send_to_any_number_of_recipients", _one_address_cannot_send_without_limit())
    with patch.object(module, "may_open_without_a_stated_address_source",
                      lambda configuration, stated: True):
        check("removed_stated_address_source_rule_is_detected",
              not _an_open_operation_needs_a_stated_address_source()
              and not _one_address_cannot_send_without_limit())
    check("the_email_allowance_rule_holds", _email_allowance_holds())
    with patch.object(FailedAttemptLimiter, "retry_after", lambda self, key: 0):
        check("removed_attempt_allowance_is_detected", not _email_allowance_holds())
    check("the_key_kind_rule_holds", _wrong_kind_of_key_is_refused())
    with patch.object(AccountEmailAdapter, "_secret", lambda self, reference, prefix: self._secrets(reference)):
        check("removed_key_kind_rule_is_detected", not _wrong_kind_of_key_is_refused())
    import httpx
    first, second = _Listener(), _Listener()
    try:
        check("a_redirect_answer_is_refused_and_the_address_it_names_is_never_asked",
              _redirect_is_not_followed(first, second))
        with patch.object(httpx, "Client", _following_client(httpx.Client)):
            check("removed_redirect_rule_is_detected", not _redirect_is_not_followed(first, second))
    finally:
        first.close()
        second.close()


def run_checks(check, root):
    _configuration_checks(check)
    _address_and_password_checks(check)
    _delivery_checks(check)
    _unknown_outcome_checks(check)
    _malformed_checks(check)
    _no_secret_checks(check)
    _limit_checks(check)
    _service_checks(check, root / "service")
    _transport_checks(check)
    _host_file_checks(check, root / "host-file")
    _mutant_controls(check)
