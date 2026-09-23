"""Checks for public sign-up and password recovery email.

The adapter runs with injected transports, so no identity provider and no mail
provider is contacted and no message is ever sent. The two real transport
functions run against loopback listeners that this module starts and stops
itself, so that refusing a redirect, the response ceiling, the request deadline
and the ignored proxy settings are observed rather than asserted. The service
is also driven through its ASGI interface with a chosen client address, the way
the request limit checks drive it. A removed-guard control reruns a scenario
with the guard patched away and requires that scenario's own predicate to fail.

`IdentityProjectStandIn` holds one identity project as the saved probes
observed it, behind the same injected transports. The sign-up checks use it to
play an address registered first by someone else, and the browser checks in
`tools/check_service_workspace.mjs` serve it over a loopback socket with
`serving_identity_project`, so the website's choose-a-password page talks to
the same project the service asked for the link.
"""
from __future__ import annotations

from contextlib import contextmanager, redirect_stderr, redirect_stdout
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import logging
import os
import re
import secrets
import threading
import time
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit
import uuid

from . import account_email as module
from .account_email import (
    CONFIGURATION_RECORD_TYPE, CONFIRM_PAGE, CONFIRMATION_SENT, GENERATE_LINK_PATH, GENERATED_PASSWORD_GROUPS,
    IDENTITY_SECRET_PREFIX, MAIL_SECRET_PREFIX, MAIL_SEND_PATH, MAXIMUM_PASSWORD_BYTES, PROVIDER_PROFILE,
    RECOVERY_ACTION, RECOVERY_RESULT_VERSION, RECOVERY_SENT, SERVICE_REFUSAL_STATUSES, SIGNUP_ACTION,
    SIGNUP_RESULT_VERSION, AccountEmailAdapter, AccountEmailConfiguration, AccountEmailError, AccountMailRequest,
    IdentityLinkRequest, PreparedAccountRequest, ProviderAnswer, counted_email_key, email_address,
    generate_identity_link, generated_signup_password, send_account_mail,
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
#: A password a caller chose. Sign-up refuses a request that carries one, and
#: no request this service makes, answer it gives or record it keeps holds it.
SIGNUP_SECRET_VALUE = "a-long-enough-chosen-phrase"
IDENTITY_KEY_REFERENCE, MAIL_KEY_REFERENCE = "env:FIXTURE_IDENTITY_KEY", "env:FIXTURE_MAIL_KEY"
IDENTITY_KEY_VALUE = IDENTITY_SECRET_PREFIX + "FIXTURE_ONLY_NOT_A_REAL_KEY"
MAIL_KEY_VALUE = MAIL_SECRET_PREFIX + "FIXTURE_ONLY_NOT_A_REAL_KEY"
TOKEN_HASH_VALUE = "pkce_fixture0token0hash0value"
# The link the identity provider generates for itself. This service never
# reads it and never puts it in a message.
PROVIDER_LINK = IDENTITY_ORIGIN + "/auth/v1/verify?token=provider-owned&type=signup"
SIGNUP_REQUEST = {"record_type": "service_account_signup_request/v2", "email": NEW_ADDRESS}
#: The retired version 1 record, which carried a password the caller chose. It
#: is refused, and a host that records request bodies never keeps it.
RETIRED_SIGNUP_REQUEST = {"record_type": "service_account_signup_request/v1", "email": NEW_ADDRESS,
                          "password": SIGNUP_SECRET_VALUE}
RECOVERY_REQUEST = {"record_type": "service_account_recovery_request/v1", "email": NEW_ADDRESS}
#: The password the wire checks put in one identity request, in the shape the
#: adapter generates. Only the transport checks send it.
WIRE_PASSWORD = "generated-fixture-wire-password-Aa1-"
#: What `availability` publishes for a host that opens both operations with the
#: default minimum password length.
BOTH_OPEN = {"signup_available": True, "recovery_available": True, "minimum_password_length": 12}


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
    check("a_generated_password_meets_any_character_rule_and_the_length_ceiling",
          _generated_passwords_are_usable([generated_signup_password() for _each in range(64)]))
    check("the_counted_email_key_keeps_no_address",
          len(counted_email_key(NEW_ADDRESS)) == 64 and NEW_ADDRESS not in counted_email_key(NEW_ADDRESS)
          and counted_email_key(NEW_ADDRESS) != counted_email_key(KNOWN_ADDRESS))


def _generated_passwords_are_usable(passwords):
    """Every password is long, within the byte ceiling, plain, and holds each character group.

    A password the identity project's own policy refused would be answered
    like an ineligible address, so the person would receive the notice
    message instead of a link. Each group is therefore always present.
    """
    return bool(passwords) and all(
        isinstance(value, str) and value.isascii() and value.isprintable() and not any(c.isspace() for c in value)
        and 43 + len(GENERATED_PASSWORD_GROUPS) <= len(value.encode("utf-8")) <= MAXIMUM_PASSWORD_BYTES
        and all(any(character in group for character in value) for group in GENERATED_PASSWORD_GROUPS)
        for value in passwords)


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
          and request.email == NEW_ADDRESS and _generated_passwords_are_usable([request.password])
          and secret == IDENTITY_KEY_VALUE and mail_secret == MAIL_KEY_VALUE
          and mail_request.url == MAIL_ORIGIN + MAIL_SEND_PATH
          and mail_request.sender == DISPLAY_NAME + " <accounts@auth.example.com>"
          and mail_request.recipient == NEW_ADDRESS and request.password not in mail_request.text_body)
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
    open_recovery = _adapter(_Provider(), _settings(allow_network=False, minimum_password_length=16))
    check("a_closed_operation_refuses_with_a_stable_code_and_makes_no_provider_request",
          _refused(lambda: _answer_for(adapter, SIGNUP_REQUEST)) == "account_signup_unavailable"
          and _refused(lambda: _answer_for(open_recovery, RECOVERY_REQUEST, RECOVERY_ACTION))
          == "account_recovery_unavailable"
          and adapter.availability() == {**BOTH_OPEN, "signup_available": False}
          and open_recovery.availability() == {"signup_available": False, "recovery_available": False,
                                               "minimum_password_length": 16}
          and (closed.identity_requests, closed.mail_requests) == ([], []))
    wrong_key, missing_key = _Provider(), _Provider()
    swapped = _adapter(wrong_key, secret_resolver=lambda reference: MAIL_KEY_VALUE)
    absent = _adapter(missing_key, secret_resolver=lambda reference: "")
    check("a_key_of_the_wrong_kind_or_no_key_stops_the_request_before_it_leaves",
          _refused(lambda: _answer_for(swapped, SIGNUP_REQUEST)) == "account_email_secret_unusable"
          and _refused(lambda: _answer_for(absent, SIGNUP_REQUEST)) == "account_email_secret_unusable"
          and (wrong_key.identity_requests, missing_key.identity_requests) == ([], []))


def _malformed_checks(check):
    provider = _Provider()
    adapter = _adapter(provider)
    malformed = ({}, {"record_type": "service_account_signup_request/v1", "email": NEW_ADDRESS},
                 {**SIGNUP_REQUEST, "extra": 1}, {**SIGNUP_REQUEST, "record_type": "service_account_signup_request/v3"},
                 {**SIGNUP_REQUEST, "email": "not an address"}, {"record_type": SIGNUP_REQUEST["record_type"]},
                 [SIGNUP_REQUEST], None, {"record_type": "service_account_recovery_request/v1", "email": NEW_ADDRESS})
    codes = [_refused(lambda row=row: adapter.prepare(SIGNUP_ACTION, row, FIRST)) for row in malformed]
    check("a_request_this_release_does_not_understand_is_refused_before_any_provider_request",
          all(code for code in codes) and codes[4] == "invalid_email_address"
          and codes[0] == codes[1] == codes[2] == codes[3] == codes[5] == "invalid_account_signup"
          and (provider.identity_requests, provider.mail_requests) == ([], []))
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
    prepared = PreparedAccountRequest(SIGNUP_ACTION, NEW_ADDRESS)
    printed = " ".join((repr(identity_request), repr(mail_request), repr(prepared), repr(adapter.configuration),
                        str(identity_request), str(mail_request)))
    hidden = (identity_request.password, NEW_ADDRESS, TOKEN_HASH_VALUE, IDENTITY_KEY_VALUE, MAIL_KEY_VALUE,
              IDENTITY_KEY_REFERENCE, MAIL_KEY_REFERENCE)
    check("no_address_password_token_or_key_appears_in_the_printed_form_of_a_record",
          not any(value in printed for value in hidden))
    talkative = ProviderAnswer(500, {"msg": SIGNUP_SECRET_VALUE + " " + TOKEN_HASH_VALUE + " " + PROVIDER_LINK})
    code, message = "", ""
    try:
        _answer_for(_adapter(_Provider(identity_answers=[talkative])), SIGNUP_REQUEST)
    except AccountEmailError as error:
        code = error.code
        message = " ".join((str(error), repr(error), json.dumps(error.details), json.dumps(error.headers)))
    check("a_refusal_carries_a_code_and_never_the_provider_message_or_a_secret",
          code == "identity_link_unavailable" and message
          and not any(value in message for value in (*hidden, SIGNUP_SECRET_VALUE, PROVIDER_LINK)))


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
        email_signup_enabled = True

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
            generated = [request.password for request, _secret in provider.identity_requests]
            check("the_answer_carries_no_address_password_token_or_link",
                  len(generated) == 3 and all(generated)
                  and not any(value in new.text + existing.text + unread.text
                              for value in (*generated, NEW_ADDRESS, TOKEN_HASH_VALUE, PROVIDER_LINK,
                                            IDENTITY_KEY_VALUE, MAIL_KEY_VALUE)))
            identity = client.get("/api/v1/account/identity").json()["result"]
            check("the_identity_route_reports_whether_sign_up_and_recovery_are_available",
                  identity["signup_available"] is True and identity["recovery_available"] is True
                  and identity["minimum_password_length"] == 12
                  and identity["redirect_url"] == base + "/auth/callback")
            retired = client.post("/api/v1/account/signup", json=RETIRED_SIGNUP_REQUEST)
            chosen = client.post("/api/v1/account/signup", json={**SIGNUP_REQUEST, "password": SIGNUP_SECRET_VALUE})
            check("the_real_route_refuses_a_sign_up_that_carries_a_password_and_asks_no_provider",
                  retired.status_code == chosen.status_code == 400
                  and retired.json()["error"]["code"] == chosen.json()["error"]["code"] == "invalid_account_signup"
                  and SIGNUP_SECRET_VALUE not in retired.text + chosen.text and len(provider.identity_requests) == 3)
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
          and "minimum_password_length" not in identity
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
    return IdentityLinkRequest(origin + GENERATE_LINK_PATH, SIGNUP_ACTION, NEW_ADDRESS, WIRE_PASSWORD,
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
                                                                  "password": WIRE_PASSWORD}
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
                                                   WIRE_PASSWORD, 3.0, 65_536))
              and _refuses(lambda: IdentityLinkRequest(listener.origin + GENERATE_LINK_PATH + "?a=b", SIGNUP_ACTION,
                                                       NEW_ADDRESS, WIRE_PASSWORD, 3.0, 65_536))
              and _refuses(lambda: IdentityLinkRequest(listener.origin + GENERATE_LINK_PATH, "invite", NEW_ADDRESS,
                                                       WIRE_PASSWORD, 3.0, 65_536))
              and _refuses(lambda: IdentityLinkRequest(listener.origin + GENERATE_LINK_PATH, RECOVERY_ACTION,
                                                       NEW_ADDRESS, WIRE_PASSWORD, 3.0, 65_536))
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
          and application.account_email.availability() == BOTH_OPEN
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
          == {**BOTH_OPEN, "signup_available": False})
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


def _stamp(moment):
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ") if moment else None


class IdentityProjectStandIn:
    """One identity project, as the saved probes observed it, behind the adapter's two transports.

    `generate_link` and `send_mail` have the signature of the adapter's two
    injected transports. `public_signup` is the provider's own public sign-up,
    which stays open until the owner closes it; a check calls it the way
    someone who registers an address first could. `verify`, `set_password` and
    `sign_in` are what the website's identity library asks the project for.

    What each rule rests on:

    - The answer to a generated link follows the probe of September 21, 2026,
      `artifacts/architecture-audit-2026-09-19/account-email-path-probe-1.json`.
    - A second sign-up link for an address that is not confirmed keeps the
      first password, and the earlier link stops working; a used link cannot
      be used again. Observed on September 23, 2026,
      `identity-unconfirmed-signup-probe-1.json` in the same folder.
    - A confirmed address refuses a new sign-up link, which the service
      answers like any ineligible address, and a recovery link for an address
      with no account is refused. Both follow the provider's published error
      codes and were not probed here.
    - A recovery link confirms an address that was never confirmed, and a new
      password ends the account's other sessions. Both are read from the
      provider's published source and were not probed here.

    Passwords are compared and never printed; the printed form holds counts.
    """

    def __init__(self, session_factory=None):
        self.users, self.sessions, self.messages, self.link_requests = {}, {}, [], []
        self.calls, self.issuer = {}, ""
        self._session_factory = session_factory or (lambda project, user: "session-" + secrets.token_urlsafe(24))
        self._lock = threading.RLock()

    def __repr__(self):
        return "IdentityProjectStandIn(users=%d, messages=%d)" % (len(self.users), len(self.messages))

    def _called(self, name):
        self.calls[name] = self.calls.get(name, 0) + 1

    def _new_user(self, address, password):
        now = datetime.now(timezone.utc)
        user = {"id": str(uuid.uuid4()), "email": address, "password": password, "confirmed_at": None,
                "created_at": now, "tokens": {SIGNUP_ACTION: None, RECOVERY_ACTION: None}}
        self.users[address] = user
        return user

    def generate_link(self, request, secret):
        """The administration interface the service calls: record the request and answer it."""
        with self._lock:
            self._called("generate_link")
            self.link_requests.append((request, secret))
            user = self.users.get(request.email)
            if request.action == SIGNUP_ACTION:
                if user is not None and user["confirmed_at"]:
                    return ProviderAnswer(422, {"code": 422, "error_code": "email_exists",
                                                "msg": "A user with this email address has already been registered"})
                # An address that is not confirmed keeps its first password.
                user = user or self._new_user(request.email, request.password)
            elif user is None:
                return ProviderAnswer(404, {"code": 404, "error_code": "user_not_found", "msg": "User not found"})
            token = user["tokens"][request.action] = secrets.token_hex(28)
            return ProviderAnswer(200, {"action_link": "stand-in-provider-link", "email_otp": "000000",
                                        "hashed_token": token, "verification_type": request.action,
                                        "redirect_to": "", "id": user["id"], "email": user["email"],
                                        "confirmation_sent_at": _stamp(datetime.now(timezone.utc))})

    def send_mail(self, request, secret):
        """The mail provider's send interface: keep the message for the address it names."""
        with self._lock:
            self._called("send_mail")
            self.messages.append({"to": request.recipient, "subject": request.subject, "text": request.text_body})
            return ProviderAnswer(200, {"id": str(uuid.uuid4())})

    def public_signup(self, address, password):
        """The provider's own public sign-up, which anyone holding the public key can call while it is open."""
        with self._lock:
            self._called("public_signup")
            user = self.users.get(address) or self._new_user(address, password)
            if not user["confirmed_at"]:
                user["tokens"][SIGNUP_ACTION] = secrets.token_hex(28)
            return user["id"]

    def verify(self, token_hash, action):
        """Exchange one link for a session, or None for a used, replaced or unknown link."""
        with self._lock:
            self._called("verify")
            if action not in (SIGNUP_ACTION, RECOVERY_ACTION) or not isinstance(token_hash, str) or not token_hash:
                return None
            for user in self.users.values():
                if user["tokens"][action] and secrets.compare_digest(user["tokens"][action], token_hash):
                    user["tokens"][action] = None
                    user["confirmed_at"] = user["confirmed_at"] or datetime.now(timezone.utc) - timedelta(seconds=1)
                    return self._open(user)
            return None

    def _open(self, user):
        session = self._session_factory(self, user)
        self.sessions[session] = user["email"]
        return session

    def set_password(self, session, password):
        """Replace the password of the account a session belongs to, and end its other sessions."""
        with self._lock:
            self._called("set_password")
            address = self.sessions.get(session)
            if (address is None or not isinstance(password, str)
                    or not 6 <= len(password.encode("utf-8")) <= MAXIMUM_PASSWORD_BYTES):
                return False
            self.users[address]["password"] = password
            for other in [key for key, owner in self.sessions.items() if owner == address and key != session]:
                del self.sessions[other]
            return True

    def sign_in(self, address, password):
        """A session for a confirmed address and its current password, or None."""
        with self._lock:
            self._called("sign_in")
            user = self.users.get(address)
            if (user is None or not user["confirmed_at"] or not isinstance(password, str)
                    or not secrets.compare_digest(user["password"].encode("utf-8"), password.encode("utf-8"))):
                return None
            return self._open(user)

    def user_record(self, session):
        """The user as the provider's user address answers it for one session, or None."""
        with self._lock:
            user = self.users.get(self.sessions.get(session, ""))
            if user is None:
                return None
            return {"id": user["id"], "aud": "authenticated", "role": "authenticated", "email": user["email"],
                    "email_confirmed_at": _stamp(user["confirmed_at"]), "confirmed_at": _stamp(user["confirmed_at"]),
                    "is_anonymous": False, "app_metadata": {"provider": "email", "providers": ["email"]},
                    "user_metadata": {}, "identities": [], "created_at": _stamp(user["created_at"]),
                    "updated_at": _stamp(datetime.now(timezone.utc))}

    def links_to(self, address):
        """Every link to this service's page sent to one address, oldest first, as (token hash, type)."""
        found = []
        for message in self.messages:
            if message["to"] != address:
                continue
            for word in message["text"].split():
                parts = urlsplit(word)
                if parts.path == CONFIRM_PAGE:
                    query = parse_qs(parts.query)
                    found.append((query.get("token_hash", [""])[0], query.get("type", [""])[0]))
        return found


def _json_answer(handler, status, value, origin):
    body = b"" if value is None else json.dumps(value).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Access-Control-Allow-Origin", origin or "*")
    handler.send_header("Vary", "Origin")
    if value is not None:
        handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _session_answer(project, session):
    return {"access_token": session, "token_type": "bearer", "expires_in": 3600,
            "expires_at": int(time.time()) + 3600, "refresh_token": "stand-in-" + secrets.token_urlsafe(12),
            "user": project.user_record(session)}


@contextmanager
def serving_identity_project(project, public_keys):
    """Serve one stand-in project over a loopback socket, as the website's identity library calls it.

    It answers the addresses that library uses, `/auth/v1/verify`,
    `/auth/v1/user`, `/auth/v1/token`, `/auth/v1/signup` and `/auth/v1/logout`,
    the key set the service reads at `/auth/v1/.well-known/jwks.json`, and one
    address for the checks alone, `/stand-in/outbox`, which returns the
    messages sent to one address. Every answer names the calling page's origin
    as allowed, as the provider does for a browser. It yields the origin.
    """
    class Handler(BaseHTTPRequestHandler):
        def _origin(self):
            return self.headers.get("Origin", "")

        def _read(self):
            length = int(self.headers.get("Content-Length") or 0)
            try:
                value = json.loads(self.rfile.read(length) or b"{}")
            except ValueError:
                value = {}
            return value if isinstance(value, dict) else {}

        def _session(self):
            header = self.headers.get("Authorization", "")
            return header[7:] if header.startswith("Bearer ") else ""

        def do_OPTIONS(self):
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", self._origin() or "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", self.headers.get("Access-Control-Request-Headers", "*"))
            self.send_header("Access-Control-Max-Age", "600")
            self.send_header("Content-Length", "0")
            self.end_headers()

        def do_GET(self):
            parts = urlsplit(self.path)
            if parts.path == "/auth/v1/.well-known/jwks.json":
                return _json_answer(self, 200, {"keys": public_keys}, self._origin())
            if parts.path == "/auth/v1/user":
                user = project.user_record(self._session())
                return _json_answer(self, 200 if user else 401, user or {"code": 401, "error_code": "bad_jwt",
                                                                         "msg": "invalid JWT"}, self._origin())
            if parts.path == "/stand-in/outbox":
                address = parse_qs(parts.query).get("to", [""])[0]
                return _json_answer(self, 200, {"messages": [row for row in project.messages if row["to"] == address],
                                                "calls": dict(project.calls)}, self._origin())
            return _json_answer(self, 404, {"code": 404, "msg": "not found"}, self._origin())

        def do_POST(self):
            parts, fields = urlsplit(self.path), self._read()
            if parts.path == "/auth/v1/verify":
                session = project.verify(fields.get("token_hash"), fields.get("type"))
                return _json_answer(self, 200 if session else 403, _session_answer(project, session) if session else
                                    {"code": 403, "error_code": "otp_expired",
                                     "msg": "Email link is invalid or has expired"}, self._origin())
            if parts.path == "/auth/v1/token" and parse_qs(parts.query).get("grant_type") == ["password"]:
                session = project.sign_in(fields.get("email"), fields.get("password"))
                return _json_answer(self, 200 if session else 400, _session_answer(project, session) if session else
                                    {"code": 400, "error_code": "invalid_credentials",
                                     "msg": "Invalid login credentials"}, self._origin())
            if parts.path == "/auth/v1/signup":
                project.public_signup(fields.get("email"), fields.get("password"))
                return _json_answer(self, 200, {"id": project.users[fields.get("email")]["id"]}, self._origin())
            if parts.path == "/auth/v1/logout":
                return _json_answer(self, 204, None, self._origin())
            return _json_answer(self, 404, {"code": 404, "msg": "not found"}, self._origin())

        def do_PUT(self):
            if urlsplit(self.path).path != "/auth/v1/user":
                return _json_answer(self, 404, {"code": 404, "msg": "not found"}, self._origin())
            session, fields = self._session(), self._read()
            if project.set_password(session, fields.get("password")):
                return _json_answer(self, 200, project.user_record(session), self._origin())
            return _json_answer(self, 422, {"code": 422, "error_code": "weak_password",
                                            "msg": "Password should be at least 6 characters."}, self._origin())

        def log_message(self, *_arguments):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    origin = "http://127.0.0.1:%d" % server.server_port
    project.issuer = origin + "/auth/v1"
    try:
        yield origin
    finally:
        server.shutdown()
        server.server_close()
        worker.join(3)


OWNER_ADDRESS = "owner.person@example.com"
#: The password the person who registers the owner's address first chooses,
#: and the one the owner chooses on the page the newest link opens.
FIRST_REGISTRANT_PASSWORD, OWNER_PASSWORD = "first-registrant-password-1", "owner-chosen-password-22"


def _signup_request(address, **extra):
    return {"record_type": SIGNUP_REQUEST["record_type"], "email": address, **extra}


def _registered_first_by_someone_else(first_route):
    """Who can open an address that someone else registered first, at each moment of the owner's journey.

    `first_route` is how the other person registers the owner's address: this
    service's sign-up route, or the identity provider's own public sign-up
    while it is open. The other person then knows every password it sent,
    everything the service answered, and whatever the same code yields when it
    runs it: three fresh generated passwords. The owner asks this service for
    sign-up, opens the newest link, and chooses a password, which this plays
    with the project's `verify` and `set_password` as the website does.
    """
    project = IdentityProjectStandIn()
    adapter = AccountEmailAdapter(_settings(), _secrets, public_base_url=ORIGIN,
        address_limits=ServiceRequestLimits(client_address_source=SOCKET_PEER_SOURCE), display_name=DISPLAY_NAME,
        identity_transport=project.generate_link, mail_transport=project.send_mail)
    known, refusals = {FIRST_REGISTRANT_PASSWORD}, []
    if first_route == "service":
        for fields in (dict(RETIRED_SIGNUP_REQUEST, email=OWNER_ADDRESS, password=FIRST_REGISTRANT_PASSWORD),
                       _signup_request(OWNER_ADDRESS, password=FIRST_REGISTRANT_PASSWORD)):
            refusals.append(_refused(lambda fields=fields: adapter.prepare(SIGNUP_ACTION, fields, FIRST)))
        known.add(json.dumps(_answer_for(adapter, _signup_request(OWNER_ADDRESS))))
    else:
        project.public_signup(OWNER_ADDRESS, FIRST_REGISTRANT_PASSWORD)
    known.update(module.generated_signup_password() for _each in range(3))
    _answer_for(adapter, _signup_request(OWNER_ADDRESS), address=SECOND)

    def opened():
        return any(project.sign_in(OWNER_ADDRESS, value) for value in known)
    moments = {"before_confirmation": opened()}
    links = project.links_to(OWNER_ADDRESS)
    earlier_refused = all(project.verify(*link) is None for link in links[:-1])
    session = project.verify(*links[-1]) if links else None
    moments["after_confirmation"] = opened()
    chosen = project.set_password(session, OWNER_PASSWORD)
    moments["after_the_owner_chose_a_password"] = opened()
    return {"moments": moments, "refusals": refusals, "earlier_links_refused": earlier_refused,
            "confirmed": session is not None and chosen, "owner_signs_in": project.sign_in(OWNER_ADDRESS, OWNER_PASSWORD)
            is not None, "links": links, "project": project, "adapter": adapter}


def _service_registration_opens_nothing_for_the_first_registrant():
    played = _registered_first_by_someone_else("service")
    return (played["refusals"] == ["invalid_account_signup"] * 2 and not any(played["moments"].values())
            and played["earlier_links_refused"] and len(played["links"]) == 2 and played["confirmed"]
            and played["owner_signs_in"])


def _recovery_opens_the_same_page_and_the_same_step():
    """A recovery link leads to the page a sign-up link leads to, and ends at a password the owner chooses."""
    played = _registered_first_by_someone_else("service")
    project, adapter = played["project"], played["adapter"]
    _answer_for(adapter, {**RECOVERY_REQUEST, "email": OWNER_ADDRESS}, RECOVERY_ACTION, address=SECOND)
    message = project.messages[-1]["text"]
    link = next((word for word in message.split() if urlsplit(word).path == CONFIRM_PAGE), "")
    token_hash, kind = project.links_to(OWNER_ADDRESS)[-1]
    session = project.verify(token_hash, kind)
    replaced = project.set_password(session, OWNER_PASSWORD + "-new")
    return (link.startswith(ORIGIN + CONFIRM_PAGE + "?token_hash=") and link.endswith("&type=recovery")
            and kind == RECOVERY_ACTION and replaced
            and project.sign_in(OWNER_ADDRESS, OWNER_PASSWORD + "-new") is not None
            and project.sign_in(OWNER_ADDRESS, OWNER_PASSWORD) is None
            and project.verify(token_hash, kind) is None)


def _password_carrying_sign_up_is_refused():
    """The retired record and the current record with a password are both refused before anything is counted."""
    provider = _Provider()
    adapter = _adapter(provider)
    codes = [_refused(lambda row=row: adapter.prepare(SIGNUP_ACTION, row, FIRST))
             for row in (RETIRED_SIGNUP_REQUEST, {**SIGNUP_REQUEST, "password": SIGNUP_SECRET_VALUE},
                         {**SIGNUP_REQUEST, "new_password": SIGNUP_SECRET_VALUE})]
    return (codes == ["invalid_account_signup"] * 3 and not provider.identity_requests
            and counted_email_key(NEW_ADDRESS) not in adapter.email_attempts._failures)


def _each_sign_up_gets_its_own_password():
    """Three sign-ups, two for one address, carry three different usable passwords that no caller sent."""
    provider = _Provider()
    adapter = _adapter(provider)
    for address in (NEW_ADDRESS, NEW_ADDRESS, KNOWN_ADDRESS):
        _answer_for(adapter, _signup_request(address))
    sent = [request.password for request, _secret in provider.identity_requests]
    return (len(sent) == len(set(sent)) == 3 and _generated_passwords_are_usable(sent)
            and SIGNUP_SECRET_VALUE not in sent)


def _registration_report(root, name):
    """What three services report as account creation: sign-up open, sign-up closed, no account email."""
    fixture = _fixture(root, name)
    reports = []
    for account_email in (_adapter(_Provider()), _adapter(_Provider(), _settings(signup_enabled=False)), None):
        application = _shut(ServiceHttpApplication(fixture.runtime, fixture.provisioning, _loopback_configuration(),
                            browser_identity=_IdentityStandIn(fixture.runtime), account_email=account_email))
        reports.append(application.capabilities()["website"]["registration_available"])
    return tuple(reports)


def _files_text(root):
    """Every byte under one folder, as text an operator could read."""
    return "\n".join(path.read_bytes().decode("latin-1") for path in sorted(root.rglob("*")) if path.is_file())


def _generated_password_places(root, name):
    """Run sign-ups through the real route and name every place a generated password was seen.

    The places a caller or an operator can read are searched: the answers and
    their headers, every record any logger made at any level, anything written
    to standard output or error, every file the service keeps with request
    bodies recorded, the printed form of the adapter and its two tables, and
    the messages sent. Only the request to the identity provider may hold it.
    """
    import httpx
    from .observability import ServiceObservabilityPolicy
    fixture = _fixture(root, name)
    provider, logged, printed = _Provider(), [], io.StringIO()

    def keep(_logger, record):
        try:
            logged.append(" ".join((str(record.msg), repr(record.args), record.getMessage(),
                                    str(record.exc_text or ""), repr(record.exc_info or ""))))
        except Exception as error:
            logged.append("unreadable log record " + type(error).__name__)

    def build(configuration):
        adapter = AccountEmailAdapter(_settings(allow_loopback=True), _secrets,
            public_base_url=configuration.public_base_url, address_limits=configuration.request_limits,
            display_name=configuration.display_name, identity_transport=provider.identity,
            mail_transport=provider.mail)
        return ServiceHttpApplication(fixture.runtime, fixture.provisioning, configuration,
            browser_identity=_IdentityStandIn(fixture.runtime), account_email=adapter,
            observability=ServiceObservabilityPolicy(payload_capture="metadata_and_request_body"))
    limits = ServiceRequestLimits(client_address_source=SOCKET_PEER_SOURCE, failures_allowed=50, window_seconds=600)
    with patch.object(logging.Logger, "isEnabledFor", lambda self, level: True), \
            patch.object(logging.Logger, "callHandlers", keep), redirect_stdout(printed), redirect_stderr(printed):
        with running_http(fixture, application_factory=build, request_limits=limits) as (base, service):
            with httpx.Client(base_url=base, trust_env=False, timeout=5) as client:
                answers = [client.post(module.SIGNUP_PATH, json=_signup_request(address))
                           for address in (NEW_ADDRESS, KNOWN_ADDRESS)]
                answers.append(client.post(module.SIGNUP_PATH, json={**SIGNUP_REQUEST, "unexpected": True}))
            adapter = service.account_email
            state = " ".join(repr(value) for value in (vars(adapter), vars(adapter.address_attempts),
                                                       vars(adapter.email_attempts), adapter))
    generated = [request.password for request, _secret in provider.identity_requests]
    places = {"answers": " ".join(answer.text + json.dumps(dict(answer.headers)) for answer in answers),
              "logs": "\n".join(logged), "printed": printed.getvalue(), "files": _files_text(root / name),
              "adapter": state, "messages": "".join(provider.sent_bodies)}
    seen = sorted(place for place, text in places.items() if any(value in text for value in generated))
    return {"generated": len(generated), "accepted": [answer.status_code for answer in answers], "seen": seen,
            "logged_records": len(logged)}


def _password_stays_hidden(root, name):
    places = _generated_password_places(root, name)
    return places["generated"] == 2 and places["accepted"] == [202, 202, 400] and places["seen"] == []


def _telling_generator(record):
    """A generator that also hands each password to `record`, for the controls below."""
    real = module.generated_signup_password

    def generated():
        value = real()
        record(value)
        return value
    return generated


def _email_first_signup_checks(check, root):
    """Sign-up takes an address alone; each check has a control that removes its guard."""
    check("a_sign_up_request_carrying_a_password_is_refused_before_anything_is_counted",
          _password_carrying_sign_up_is_refused())
    with patch.dict(module.REQUEST_FIELDS, {SIGNUP_ACTION: frozenset({"record_type", "email", "password"})}):
        check("removed_no_password_field_rule_is_detected", not _password_carrying_sign_up_is_refused())
    check("each_sign_up_gets_a_new_password_that_no_caller_sent", _each_sign_up_gets_its_own_password())
    constant = "Constant-password-Aa1-" + "x" * 30
    with patch.object(module, "generated_signup_password", lambda: constant):
        check("removed_random_password_rule_is_detected", not _each_sign_up_gets_its_own_password())
    check("an_address_registered_first_through_this_service_never_opens_with_a_password_the_registrant_knows",
          _service_registration_opens_nothing_for_the_first_registrant())
    # The person who registers first runs the same code. A generator that
    # returns what that person's own run returns lets them in once the owner
    # confirms the address.
    with patch.object(module, "generated_signup_password", lambda: constant):
        check("removed_unguessable_password_rule_lets_the_first_registrant_in",
              not _service_registration_opens_nothing_for_the_first_registrant())
    provider_route = _registered_first_by_someone_else("provider")
    # The provider's own public sign-up takes a password from anyone, so a
    # password chosen first opens the account from the moment the owner
    # confirms the address until the owner chooses theirs. The website asks
    # for the password before it opens the account, and the owner closes that
    # route at the provider; this check keeps the reason for both in view.
    check("with_the_provider_public_sign_up_open_a_password_chosen_first_lasts_until_the_owner_chooses_one",
          provider_route["moments"] == {"before_confirmation": False, "after_confirmation": True,
                                        "after_the_owner_chose_a_password": False}
          and provider_route["confirmed"] and provider_route["owner_signs_in"])
    check("a_recovery_link_opens_the_same_page_and_ends_at_a_password_the_owner_chooses",
          _recovery_opens_the_same_page_and_the_same_step())
    check("the_generated_password_is_never_answered_stored_printed_or_logged",
          _password_stays_hidden(root, "hidden"))
    seen = []
    with patch.object(module, "generated_signup_password",
                      _telling_generator(lambda value: logging.getLogger(module.__name__).debug("made %s", value))):
        check("a_generated_password_written_to_a_log_is_found", not _password_stays_hidden(root, "logged"))
    original = AccountEmailAdapter.deliver

    def telling(self, prepared):
        result = original(self, prepared)
        return {**result, "password": seen[-1]} if seen else result
    with patch.object(module, "generated_signup_password", _telling_generator(seen.append)), \
            patch.object(AccountEmailAdapter, "deliver", telling):
        check("a_generated_password_put_in_the_answer_is_found", not _password_stays_hidden(root, "answered"))
    check("registration_is_reported_open_only_when_this_service_can_send_the_sign_up_link",
          _registration_report(root, "registration-open") == (True, False, False))
    with patch.object(ServiceHttpApplication, "registration_available",
                      lambda self: self.browser_identity is not None
                      and self.browser_identity.configuration.email_signup_enabled):
        check("removed_sign_up_link_rule_for_registration_is_detected",
              _registration_report(root, "registration-mutant") != (True, False, False))


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
    _email_first_signup_checks(check, root / "email-first")
