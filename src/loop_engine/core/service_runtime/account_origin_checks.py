"""Checks for the one way in: the mark in two places, the replacement and the marking command.

The identity provider is the stand-in project from `account_email_checks.py`,
extended here with the administration operations the one way in uses, so an
address registered through the provider's own public sign-up is played exactly
as the owner feared. Signed browser tokens come from an owned loopback key set.
No provider, mailbox or network outside loopback is used.

Each guard has a known-wrong control. `mutated` rebuilds one function from its
own source with the guard's lines changed, and the check that holds the guard
must then fail. A control whose text no longer matches the source refuses to
run, so a renamed guard cannot pass silently.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import inspect
import json
import secrets
import textwrap
import time
import types
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit
import uuid

from . import account_email as account_email_module
from . import account_origin as origin_module
from .account_email import SIGNUP_ACTION, SIGNUP_REQUEST_VERSION, AccountEmailAdapter, ProviderAnswer
from .account_email_checks import (DISPLAY_NAME, IDENTITY_ORIGIN, ORIGIN, IdentityProjectStandIn, _secrets,
                                   _settings, _stamp)
from .account_origin import (ACCOUNT_MARK, ACCOUNT_MARKER, INVITATION_MARKER, MIGRATION_ORIGIN, REFUSED_ORIGIN,
                             REPLACED, SIGNUP_ORIGIN, USERS_PATH, AccountOrigins,
                             SupabaseIdentityAdministration, address_digest, origin_of, record_origin,
                             require_admitted)
from .account_policy import ServiceAccountPolicy
from .http_auth import HttpAuthenticationError
from .http_test_fixtures import HttpDomainFixture, running_http, running_key_set
from .records import ServiceRuntimeError, SubjectBindingRequest
from .request_limits import SOCKET_PEER_SOURCE, ServiceRequestLimits

ISSUER = IDENTITY_ORIGIN + "/auth/v1"
OWNER = "owner.person@example.com"
FIRST_PASSWORD, OWNER_PASSWORD = "first-registrant-password-1", "owner-chosen-password-22"


@contextmanager
def mutated(owner, name, old, new, *, also=()):
    """Replace one function of `owner` with its own source, `old` changed to `new`, for one block.

    The function is compiled in its own module's namespace, so it behaves as
    the original except for the changed text. `also` names further pairs for a
    guard written on more than one line. A control whose text is not in the
    source raises before it runs.
    """
    original = inspect.getattr_static(owner, name)
    function = original.__func__ if isinstance(original, (staticmethod, classmethod)) else original
    source = textwrap.dedent(inspect.getsource(function))
    for before, after in ((old, new), *also):
        if before not in source:
            raise AssertionError("the control no longer matches the source of " + name)
        source = source.replace(before, after, 1)
    # The changed source is compiled and the function's own code object is
    # taken from it, so nothing but that one definition is ever evaluated.
    compiled = compile(source, inspect.getsourcefile(function), "exec")
    code = next(value for value in compiled.co_consts
                if isinstance(value, types.CodeType) and value.co_name == function.__name__)
    replacement = types.FunctionType(code, function.__globals__, function.__name__, function.__defaults__,
                                     function.__closure__)
    replacement.__kwdefaults__ = function.__kwdefaults__
    if isinstance(original, staticmethod):
        replacement = staticmethod(replacement)
    with patch.object(owner, name, replacement):
        yield


class MarkingIdentityProjectStandIn(IdentityProjectStandIn):
    """The stand-in project with the administration interface and refresh tokens.

    `admin` has the signature of the identity administration transport. A
    created user carries the app_metadata it was created with; a deleted user
    takes its sessions and its refresh tokens with it, as the provider's
    foreign keys from sessions to users and from refresh tokens to sessions do.
    """

    def __init__(self, session_factory=None):
        super().__init__(session_factory)
        self.refresh_tokens, self.admin_requests = {}, []

    def _open(self, user):
        session = super()._open(user)
        user["last_sign_in_at"] = datetime.now(timezone.utc)
        return session

    def refresh_token_for(self, session):
        with self._lock:
            owner = self.sessions.get(session)
            if owner is None:
                return None
            token = "refresh-" + secrets.token_urlsafe(16)
            self.refresh_tokens[token] = owner
            return token

    def refresh(self, token):
        """A new session for a refresh token whose user still exists, or None."""
        with self._lock:
            user = self._user_by_id(self.refresh_tokens.pop(token, None))
            return None if user is None else self._open(user)

    def admin_record(self, user):
        return {"id": user["id"], "aud": "authenticated", "role": "authenticated", "email": user["email"],
                "email_confirmed_at": _stamp(user["confirmed_at"]), "created_at": _stamp(user["created_at"]),
                "last_sign_in_at": _stamp(user.get("last_sign_in_at")), "is_anonymous": False,
                "app_metadata": {"provider": "email", "providers": ["email"], **user.get("app_metadata", {})}}

    def mark_without_the_service(self, address):
        """Write the mark the way anyone holding the administration key could, bypassing this service."""
        self.users[address]["app_metadata"][ACCOUNT_MARKER] = ACCOUNT_MARK

    def admin(self, request, secret):
        with self._lock:
            self._called("admin_" + request.method.lower())
            self.admin_requests.append((request.method, urlsplit(request.url).path))
            parts = urlsplit(request.url)
            query = parse_qs(parts.query)
            if parts.path == USERS_PATH and request.method == "POST":
                body = request.body
                if body["email"] in self.users:
                    return ProviderAnswer(422, {"code": 422, "error_code": "email_exists",
                                                "msg": "A user with this email address has already been registered"})
                user = self._new_user(body["email"], body["password"])
                user["app_metadata"] = dict(body.get("app_metadata") or {})
                if body.get("email_confirm") is True:
                    user["confirmed_at"] = datetime.now(timezone.utc)
                return ProviderAnswer(200, self.admin_record(user))
            if parts.path == USERS_PATH and request.method == "GET":
                page, size = int(query.get("page", ["1"])[0]), int(query.get("per_page", ["50"])[0])
                wanted = query.get("filter", [""])[0]
                rows = sorted((user for user in self.users.values() if wanted in user["email"]),
                              key=lambda user: user["created_at"])
                return ProviderAnswer(200, {"aud": "authenticated", "users": [
                    self.admin_record(user) for user in rows[(page - 1) * size:page * size]]})
            if parts.path.startswith(USERS_PATH + "/"):
                user = self._user_by_id(parts.path.rsplit("/", 1)[-1])
                if user is None:
                    return ProviderAnswer(404, {"code": 404, "error_code": "user_not_found", "msg": "User not found"})
                if request.method == "DELETE":
                    del self.users[user["email"]]
                    for table in (self.sessions, self.refresh_tokens):
                        for key in [key for key, owner in table.items() if owner == user["id"]]:
                            del table[key]
                    return ProviderAnswer(200, {})
                if request.method == "PUT":
                    for key, value in (request.body.get("app_metadata") or {}).items():
                        if value is None:
                            user["app_metadata"].pop(key, None)
                        else:
                            user["app_metadata"][key] = value
                    return ProviderAnswer(200, self.admin_record(user))
            return ProviderAnswer(404, {"code": 404, "msg": "not found"})


def fixture_in(root, name, **changes):
    """A durable service domain in its own new folder."""
    (root / name).mkdir(parents=True, exist_ok=True)
    return HttpDomainFixture(root / name, **changes)


def administration_for(project, *, allow_network=True):
    return SupabaseIdentityAdministration(IDENTITY_ORIGIN, allow_network=allow_network, transport=project.admin)


def signup_adapter(runtime, project):
    """The real sign-up adapter with the one way in, speaking to one stand-in project."""
    origins = AccountOrigins(runtime, ISSUER, administration_for(project))
    return AccountEmailAdapter(_settings(), _secrets, public_base_url=ORIGIN,
        address_limits=ServiceRequestLimits(client_address_source=SOCKET_PEER_SOURCE, failures_allowed=100),
        display_name=DISPLAY_NAME, identity_transport=project.generate_link, mail_transport=project.send_mail,
        account_origins=origins), origins


def sign_up(adapter, address, client="198.51.100.10"):
    """One sign-up through the adapter. The answer, or the refusal code."""
    try:
        return adapter.deliver(adapter.prepare(SIGNUP_ACTION, {"record_type": SIGNUP_REQUEST_VERSION,
                                                              "email": address}, client))
    except (ServiceRuntimeError, ValueError) as error:
        return getattr(error, "code", "failed")


class SignedIdentity:
    """Signed browser tokens from an owned key set, and provider user records the checks control.

    `person` adds a provider user. `marked` says whether its app_metadata
    carries the mark; `recorded` whether the service holds its record.
    """

    def __init__(self, fixture, origin, public_keys):
        import jwt
        from cryptography.hazmat.primitives.asymmetric import rsa
        from .browser_identity import BrowserIdentityConfiguration
        self.fixture, self.origin, self.issuer = fixture, origin, origin + "/auth/v1"
        self._key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public_keys["keys"] = [{**json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(self._key.public_key())),
                                "kid": "origin-test", "alg": "RS256", "use": "sig"}]
        self.people = {}
        self.policy = BrowserIdentityConfiguration(origin, "fixture:publishable", "customers",
            registration_enabled=True, email_signup_enabled=True, allow_network=True, allow_loopback=True)

    def person(self, email, *, marked=True, recorded=True, origin=SIGNUP_ORIGIN, metadata=None):
        subject = str(uuid.uuid4())
        self.people[subject] = {"email": email, "app_metadata": dict(metadata if metadata is not None else (
            {ACCOUNT_MARKER: ACCOUNT_MARK} if marked else {}))}
        if recorded:
            record_origin(self.fixture.runtime, self.issuer, subject, origin)
        return subject

    def token(self, subject, **changes):
        import jwt
        now = int(time.time())
        return jwt.encode({"iss": self.issuer, "aud": "authenticated", "sub": subject, "exp": now + 900,
                           "iat": now, "role": "authenticated", "is_anonymous": False, **changes}, self._key,
                          algorithm="RS256", headers={"kid": "origin-test"})

    def user(self, request):
        import jwt
        subject = jwt.decode(request.access_token, options={"verify_signature": False})["sub"]
        person = self.people[subject]
        return {"id": subject, "role": "authenticated", "is_anonymous": False, "email": person["email"],
                "email_confirmed_at": "2026-01-01T00:00:00Z",
                "app_metadata": {"provider": "email", "providers": ["email"], **person["app_metadata"]}}

    def adapter(self, **keywords):
        from .browser_identity import BrowserIdentityAdapter
        return BrowserIdentityAdapter(self.fixture.runtime, self.policy, lambda _: "sb_publishable_local_fixture",
                                      transport=self.user, **keywords)


@contextmanager
def signed_identity(root, **fixture_changes):
    root.mkdir(parents=True, exist_ok=True)
    with running_key_set() as (origin, public_keys):
        yield SignedIdentity(HttpDomainFixture(root, **fixture_changes), origin, public_keys)


def _admission(identity, subject):
    """True when one person is both activated and signed in, or the refusal code."""
    adapter = identity.adapter()
    try:
        adapter.activate(identity.token(subject))
        adapter.authenticate(identity.token(subject))
        return True
    except (HttpAuthenticationError, ServiceRuntimeError) as error:
        return error.code


def _guard_holds(identity):
    """Every combination of the two marks: only both admit."""
    cases = {"neither": identity.person("neither@example.com", marked=False, recorded=False),
             "provider_mark_alone": identity.person("provider@example.com", marked=True, recorded=False),
             "service_record_alone": identity.person("service@example.com", marked=False, recorded=True),
             "invitation_mark": identity.person("invited@example.com", metadata={INVITATION_MARKER:
                                                                                 "beta_invitation_report/v1"}),
             "other_version": identity.person("other@example.com", metadata={ACCOUNT_MARKER:
                                                                              "service_account_origin/v2"}),
             "both": identity.person("both@example.com")}
    return {name: _admission(identity, subject) for name, subject in cases.items()}


EXPECTED_ADMISSION = {"neither": REFUSED_ORIGIN, "provider_mark_alone": REFUSED_ORIGIN,
                      "service_record_alone": REFUSED_ORIGIN, "invitation_mark": REFUSED_ORIGIN,
                      "other_version": REFUSED_ORIGIN, "both": True}


def _guard_checks(check, root):
    with signed_identity(root / "guard") as identity:
        observed = _guard_holds(identity)
        check("an_unmarked_provider_identity_is_refused_and_only_both_marks_admit", observed == EXPECTED_ADMISSION)
        with mutated(origin_module, "require_admitted", "if not isinstance(subject, str) or not provider_mark_present(user):",
                     "if not isinstance(subject, str):"):
            check("removed_provider_mark_requirement_is_detected", _guard_holds(identity) != EXPECTED_ADMISSION)
        with mutated(origin_module, "require_admitted", "origin = origin_of(runtime, issuer, subject)",
                     "origin = origin_of(runtime, issuer, subject) or {\"issuer\": issuer, \"subject\": subject, "
                     "\"origin\": SIGNUP_ORIGIN}"):
            check("removed_service_record_requirement_is_detected", _guard_holds(identity) != EXPECTED_ADMISSION)
        with patch.object(origin_module, "require_admitted", lambda runtime, issuer, user: {"origin": SIGNUP_ORIGIN}):
            check("removed_one_way_in_guard_is_detected", _guard_holds(identity) != EXPECTED_ADMISSION)
        # Over the real transport, the refusal names its own code, so the page
        # can send the person to Baltor's sign-up instead of a password fault.
        import httpx
        from .http import ServiceHttpApplication
        unmarked = identity.person("over-http@example.com", marked=False, recorded=False)
        with running_http(identity.fixture, application_factory=lambda config: ServiceHttpApplication(
                identity.fixture.runtime, identity.fixture.provisioning, config,
                browser_identity=identity.adapter())) as (base, _service):
            with httpx.Client(base_url=base, trust_env=False, timeout=5) as client:
                headers = {"Authorization": "Bearer " + identity.token(unmarked)}
                activated = client.post("/api/v1/account/activate", headers=headers,
                                        json={"record_type": "service_account_activation_request/v1"})
                session = client.get("/api/v1/session", headers=headers)
        check("an_unmarked_sign_in_is_refused_over_http_with_its_own_code",
              activated.status_code == session.status_code == 401
              and activated.json()["error"]["code"] == session.json()["error"]["code"] == REFUSED_ORIGIN
              and "Get started" in activated.json()["error"]["next_action"])


def _replacement(root, name, *, bound=False):
    """Play the owner's feared case end to end and return every fact a check needs.

    Someone registers the owner's address through the provider's own public
    sign-up with a password they chose. The owner opens the provider's own
    confirmation message, so the account is confirmed, and that someone signs
    in and holds a session and a refresh token. With `bound`, the account also
    predates the guard: the service holds a sign-in bound to it and a personal
    key issued from it. Then the owner signs up through Baltor.
    """
    from .access import ServiceAccessAdministration, ServiceAccessRequest, ServiceAccessSession, ServiceClientAccessPolicy
    from .runtime import SUBJECT
    fixture = fixture_in(root, name)
    project = MarkingIdentityProjectStandIn()
    adapter, origins = signup_adapter(fixture.runtime, project)
    first_id = project.public_signup(OWNER, FIRST_PASSWORD)
    project.verify(project.users[OWNER]["tokens"][SIGNUP_ACTION], SIGNUP_ACTION)
    held_session = project.sign_in(OWNER, FIRST_PASSWORD)
    held_refresh = project.refresh_token_for(held_session)
    try:
        require_admitted(fixture.runtime, ISSUER, project.user_record(held_session))
        refused_before = False
    except HttpAuthenticationError as error:
        refused_before = error.code == REFUSED_ORIGIN
    personal_key = None
    if bound:
        fixture.runtime.bind_subject(SubjectBindingRequest("beta", ISSUER, first_id))
        principal = fixture.runtime.authenticate_subject(ISSUER, first_id)
        manager = ServiceAccessAdministration(fixture.runtime, ServiceClientAccessPolicy(writes_authorized=True))
        with fixture.runtime._catalog.store() as store:
            record_id = fixture.runtime._catalog.read(store, SUBJECT, (ISSUER, first_id))["record_id"]
        personal_key = manager.apply(principal, ServiceAccessRequest.from_customer_dict({
            "record_type": "service_client_access_request/v1", "operation": "issue", "request_id": "legacy-key",
            "label": "Legacy client", "scopes": ["provisioning:metadata"], "lifetime_seconds": 3600}, "beta"),
            session=ServiceAccessSession(record_id, "0" * 64, time.time() + 600,
                                         ("provisioning:metadata",)))["token"]
    answer = sign_up(adapter, OWNER)
    links = project.links_to(OWNER)
    owner_session = project.verify(*links[-1]) if links else None
    chose = bool(owner_session) and project.set_password(owner_session, OWNER_PASSWORD)
    replacement = next((row for row in origins.replacements() if row["provider_user_id"] == first_id), {})
    current = project.users.get(OWNER)
    try:
        admitted = bool(require_admitted(fixture.runtime, ISSUER, project.user_record(owner_session)))
    except (HttpAuthenticationError, TypeError, AttributeError):
        admitted = False
    try:
        key_still_works = personal_key is not None and bool(fixture.runtime.authenticate_key(personal_key))
    except ServiceRuntimeError:
        key_still_works = False
    return {"refused_before": refused_before, "answer": answer, "first_id": first_id,
            "new_id": current["id"] if current else None,
            "held_session_usable": project.user_record(held_session) is not None,
            "held_refresh_usable": project.refresh(held_refresh) is not None,
            "first_password_opens": project.sign_in(OWNER, FIRST_PASSWORD) is not None,
            "owner_chose": chose, "owner_admitted": admitted,
            "owner_password_opens": project.sign_in(OWNER, OWNER_PASSWORD) is not None,
            "replacement": replacement, "key_still_works": key_still_works,
            "fixture": fixture, "project": project, "origins": origins}


def _replaced_cleanly(played):
    record = played["replacement"]
    return (played["refused_before"] and played["answer"] == {"record_type": "service_account_signup_result/v1",
                                                              "status": "confirmation_sent"}
            and played["new_id"] not in (None, played["first_id"])
            and not played["held_session_usable"] and not played["held_refresh_usable"]
            and not played["first_password_opens"] and played["owner_chose"] and played["owner_admitted"]
            and played["owner_password_opens"]
            and record.get("state") == REPLACED and record.get("replacement_provider_user_id") == played["new_id"]
            and record.get("email_confirmed") is True and record.get("address_digest") == address_digest(OWNER)
            and OWNER not in json.dumps(record) and record.get("provider_created_at", "") != "")


def _replacement_checks(check, root):
    root.mkdir(parents=True, exist_ok=True)
    played = _replacement(root, "clean")
    check("the_replacement_flow_leaves_no_old_session_refresh_token_or_password_usable", _replaced_cleanly(played))
    check("the_replaced_account_is_archived_with_its_provider_identity_times_and_confirmation_but_no_address",
          played["replacement"].get("provider_user_id") == played["first_id"]
          and played["replacement"].get("attempts") == 1
          and set(played["replacement"]) >= {"provider_created_at", "email_confirmed_at", "last_sign_in_at",
                                             "provider_mark_present", "service_record_present"})
    with patch.object(AccountOrigins, "honoured", lambda self, user: True):
        check("removed_replacement_keeps_the_first_registrant_in_and_is_detected",
              not _replaced_cleanly(_replacement(root, "kept")))
    with patch.object(SupabaseIdentityAdministration, "delete_user", lambda self, user_id, secret: None):
        check("removed_deletion_at_the_provider_is_detected", not _replaced_cleanly(_replacement(root, "undeleted")))
    with mutated(AccountOrigins, "_archive", "catalog.commit(store, (row,), (", "(("):
        check("removed_archive_before_replacement_is_detected", not _replaced_cleanly(_replacement(root, "unarchived")))
    # An account the service already holds a sign-in for predates the guard.
    # A public sign-up never deletes it: anyone who knows the address could
    # otherwise end a real person's account. It waits for the marking command.
    def bound_account_kept(name):
        played = _replacement(root, name, bound=True)
        return (played["answer"] == {"record_type": "service_account_signup_result/v1", "status": "confirmation_sent"}
                and played["new_id"] == played["first_id"] and played["held_session_usable"]
                and played["key_still_works"] is True and played["replacement"] == {}
                and "already has an account" in played["project"].messages[-1]["text"]
                and not played["project"].links_to(OWNER) and not played["owner_admitted"])
    check("an_account_the_service_already_holds_a_sign_in_for_is_never_deleted_by_a_public_sign_up",
          bound_account_kept("bound"))
    with mutated(AccountOrigins, "prepare_signup", "if self.bound(held.user_id):", "if False:"):
        check("removed_bound_account_rule_is_detected", not bound_account_kept("bound-mutant"))

    def failed_deletion():
        def refuse(self, user_id, secret):
            raise origin_module.IdentityAdministrationError("identity_account_deletion_unknown")
        with patch.object(SupabaseIdentityAdministration, "delete_user", refuse):
            played = _replacement(root, "delete-refused")
        return played
    refused = failed_deletion()
    check("the_archive_is_kept_before_the_provider_deletes_anything",
          refused["answer"] == "identity_account_deletion_unknown"
          and refused["replacement"].get("state") == "archived" and refused["new_id"] == refused["first_id"]
          and not refused["project"].messages)
    # The answer does not say who held the address: a new address, a confirmed
    # account this service created and an account it replaces all read the same.
    fixture = fixture_in(root, "same-answer")
    project = MarkingIdentityProjectStandIn()
    adapter, _origins = signup_adapter(fixture.runtime, project)
    sign_up(adapter, "made.here@example.com")
    project.verify(*project.links_to("made.here@example.com")[-1])
    project.public_signup("held.elsewhere@example.com", FIRST_PASSWORD)
    answers = [sign_up(adapter, address) for address in
               ("fresh@example.com", "made.here@example.com", "held.elsewhere@example.com")]
    check("the_sign_up_answer_is_the_same_for_a_new_a_known_and_a_replaced_address",
          answers == [{"record_type": "service_account_signup_result/v1", "status": "confirmation_sent"}] * 3
          and "already has an account" in project.messages[-2]["text"]
          and project.links_to("held.elsewhere@example.com"))
    # A link must open the account the one way in prepared, never another.
    other = str(uuid.uuid4())

    def elsewhere(request, secret):
        answer = project.generate_link(request, secret)
        return ProviderAnswer(answer.status_code, {**answer.payload, "id": other})
    wrong = AccountEmailAdapter(_settings(), _secrets, public_base_url=ORIGIN,
        address_limits=ServiceRequestLimits(client_address_source=SOCKET_PEER_SOURCE, failures_allowed=100),
        display_name=DISPLAY_NAME, identity_transport=elsewhere, mail_transport=project.send_mail,
        account_origins=AccountOrigins(fixture.runtime, ISSUER, administration_for(project)))
    sent_before = len(project.messages)
    check("a_sign_up_link_for_another_account_is_refused_before_any_message",
          sign_up(wrong, "linked.elsewhere@example.com") == "identity_link_unusable"
          and len(project.messages) == sent_before)
    with mutated(account_email_module.AccountEmailAdapter, "generated_link",
                 "if expected_user and answer.payload.get(\"id\") != expected_user:", "if False:"):
        check("removed_link_to_prepared_account_rule_is_detected",
              sign_up(wrong, "linked.again@example.com") != "identity_link_unusable")


def _marking_setup(root, name):
    """Five provider users: honoured, bound but unmarked, staff by address, staff by identity, and a stranger."""
    fixture = fixture_in(root, name)
    project = MarkingIdentityProjectStandIn()
    origins = AccountOrigins(fixture.runtime, ISSUER, administration_for(project))
    adapter, _ = signup_adapter(fixture.runtime, project)
    sign_up(adapter, "honoured@example.com")
    bound_id = project.public_signup("operator@example.com", FIRST_PASSWORD)
    fixture.runtime.bind_subject(SubjectBindingRequest("alpha", ISSUER, bound_id))
    project.public_signup("staff.by.address@example.com", FIRST_PASSWORD)
    staff_id = project.public_signup("staff.by.identity@example.com", FIRST_PASSWORD)
    project.public_signup("stranger@example.com", FIRST_PASSWORD)
    policy = ServiceAccountPolicy(staff=({"role": "developer", "email": "Staff.By.Address@example.com"},
                                         {"role": "analytics", "provider_user_id": staff_id}))
    return fixture, project, origins, policy


def _state(fixture, project):
    """What the provider and the service hold, to compare before and after a plan."""
    marks = {user["email"]: dict(user["app_metadata"]) for user in project.users.values()}
    with fixture.runtime._catalog.store() as store:
        records = sorted(row["payload"]["subject"] for row in fixture.runtime._catalog.rows_all(store, origin_module.ORIGIN))
    return marks, records


def _marking_is_listed_first_and_idempotent(root, name):
    fixture, project, origins, policy = _marking_setup(root, name)
    before = _state(fixture, project)
    plan = origins.marking_plan("sb_secret_fixture", policy)
    listed_only = _state(fixture, project) == before
    reasons = sorted(item["reason"] for item in plan["changes"])
    stale = "0" * 64
    refusals = []
    for digest_value in (None, stale):
        try:
            origins.apply_marking("sb_secret_fixture", policy, digest_value)
            refusals.append("applied")
        except ServiceRuntimeError as error:
            refusals.append(error.code)
    unchanged_after_refusals = _state(fixture, project) == before
    applied = origins.apply_marking("sb_secret_fixture", policy, plan["plan_digest"])
    again = origins.marking_plan("sb_secret_fixture", policy)
    second = origins.apply_marking("sb_secret_fixture", policy, again["plan_digest"])
    stranger = next(user for user in project.users.values() if user["email"] == "stranger@example.com")
    return (listed_only and plan["changed"] is False and reasons == ["service_account", "staff", "staff"]
            and plan["already_honoured"] == 1 and len(plan["left_unmarked"]) == 1
            and all("@" in item["address_hint"] and "***" in item["address_hint"] for item in plan["changes"])
            and "operator@example.com" not in json.dumps(plan)
            and refusals == ["account_marking_plan_digest_required", "account_marking_plan_changed"]
            and unchanged_after_refusals and len(applied["applied"]) == 3 and applied["changed"] is True
            and again["changes"] == [] and again["already_honoured"] == 4
            and second["applied"] == [] and second["changed"] is False
            and ACCOUNT_MARKER not in stranger["app_metadata"]
            and origin_of(fixture.runtime, ISSUER, stranger["id"]) is None
            and all(origin_of(fixture.runtime, ISSUER, item["provider_user_id"])["origin"] == MIGRATION_ORIGIN
                    for item in plan["changes"]))


def _marking_checks(check, root):
    root.mkdir(parents=True, exist_ok=True)
    check("the_marking_command_lists_before_changing_applies_only_the_listed_plan_and_is_idempotent",
          _marking_is_listed_first_and_idempotent(root, "plan"))
    with mutated(AccountOrigins, "apply_marking", "if plan[\"plan_digest\"] != expected_plan_digest:", "if False:"):
        check("removed_plan_digest_rule_is_detected", not _marking_is_listed_first_and_idempotent(root, "mutant"))
    # After marking, the operator's bound account signs in; before it, it was refused.
    fixture, project, origins, policy = _marking_setup(root, "after")
    operator = project.users["operator@example.com"]
    project.verify(project.users["operator@example.com"]["tokens"][SIGNUP_ACTION] or "", SIGNUP_ACTION)
    operator["confirmed_at"] = datetime.now(timezone.utc)
    session = project.sign_in("operator@example.com", FIRST_PASSWORD)

    def admitted():
        try:
            return bool(require_admitted(fixture.runtime, ISSUER, project.user_record(session)))
        except HttpAuthenticationError:
            return False
    before = admitted()
    origins.apply_marking("sb_secret_fixture", policy, origins.marking_plan("sb_secret_fixture", policy)["plan_digest"])
    check("an_account_that_predates_the_guard_is_refused_until_marked_then_admitted", before is False and admitted())


def _host_file_checks(check, root):
    """The real host loader installs the one way in, the staff administration and the founding count."""
    from .account_email_checks import HOST, _host_block
    from .http_entrypoint import HOST_CONFIGURATION_VERSION, MANIFEST_VERSION, load_host_application
    from .request_limits import HEADER_SOURCE, REQUEST_LIMITS_RECORD_TYPE
    root.mkdir(parents=True, exist_ok=True)
    manifest = root / "manifest.json"
    manifest.write_text(json.dumps({"record_type": MANIFEST_VERSION, "artifact_root": str(root), "items": []}))
    identity = {"project_url": IDENTITY_ORIGIN, "publishable_key_ref": "env:FIXTURE_PUBLISHABLE_KEY",
                "namespace_prefix": "customer", "registration_enabled": True, "email_signup_enabled": True,
                "allow_network": True}

    def load(name, **blocks):
        path = root / (name + ".json")
        path.write_text(json.dumps({"record_type": HOST_CONFIGURATION_VERSION, "manifest_path": str(manifest),
            "runtime": {"database_path": str(root / (name + ".db")), "writes_authorized": True},
            "http": {"public_base_url": ORIGIN, "allowed_hosts": [HOST], "display_name": DISPLAY_NAME,
                     "request_limits": {"record_type": REQUEST_LIMITS_RECORD_TYPE, "client_address_source": HEADER_SOURCE,
                                        "client_address_header": "Fly-Client-IP"}},
            "authentication": {}, **blocks}))
        application = load_host_application(str(path))[0]
        application._workers.shutdown(wait=True)
        return application

    accounts = {"record_type": "service_account_policy/v1", "founding_free_monthly_accounts": 3,
                "staff": [{"role": "superadmin", "email": "owner@example.com"}]}
    loaded = load("full", browser_identity=identity, account_email=_host_block(), accounts=accounts)
    default = load("default", browser_identity=identity, account_email=_host_block())
    check("the_host_loader_installs_the_one_way_in_the_staff_list_and_the_founding_count",
          isinstance(loaded.account_email.account_origins, AccountOrigins)
          and loaded.account_email.account_origins.issuer == ISSUER
          and loaded.account_administration.policy.staff[0].role == "superadmin"
          and loaded.browser_identity.founding_accounts == 3
          and default.browser_identity.founding_accounts == 10
          and default.account_administration.policy.staff == ())

    def refused(block):
        try:
            load("refused-" + uuid.uuid4().hex[:8], browser_identity=identity, accounts=block)
            return None
        except ServiceRuntimeError as error:
            return error.code
    check("a_host_file_cannot_name_a_permission_a_fourth_role_or_a_field_of_its_own",
          refused({**accounts, "staff": [{"role": "superadmin", "email": "a@example.com",
                                          "permissions": ["accounts.list"]}]}) == "invalid_staff_member"
          and refused({**accounts, "staff": [{"role": "owner", "email": "a@example.com"}]}) == "unknown_staff_role"
          and refused({**accounts, "roles": {"support": ["accounts.list"]}}) == "unsupported_account_policy"
          and refused({**accounts, "record_type": "service_account_policy/v2"}) == "unsupported_account_policy")


@contextmanager
def serving_administration(project):
    """Serve the stand-in's administration interface over a loopback socket, for the real transport."""
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from .account_origin import IdentityAdministrationRequest

    class Handler(BaseHTTPRequestHandler):
        def _serve(self, method):
            length = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(length)) if length else None
            answer = project.admin(IdentityAdministrationRequest(method, "http://stand-in" + self.path, body, 5, 262_144),
                                   self.headers.get("apikey"))
            data = json.dumps(answer.payload).encode("utf-8")
            self.send_response(answer.status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            self._serve("GET")

        def do_PUT(self):
            self._serve("PUT")

        def do_POST(self):
            self._serve("POST")

        def do_DELETE(self):
            self._serve("DELETE")

        def log_message(self, *_arguments):
            pass
    import threading
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield "http://127.0.0.1:%d" % server.server_port
    finally:
        server.shutdown()
        server.server_close()
        worker.join(3)


def _command_checks(check, root):
    """The marking command through the service entry point, over the real transport and a loopback socket."""
    import io
    import os
    from contextlib import redirect_stdout
    from .http_entrypoint import HOST_CONFIGURATION_VERSION, MANIFEST_VERSION, main
    from .records import ServiceRuntimeConfig, TenantRegistration
    from .runtime import ServiceRuntime
    root.mkdir(parents=True, exist_ok=True)
    project = MarkingIdentityProjectStandIn()
    bound = project.public_signup("operator@example.com", FIRST_PASSWORD)
    project.public_signup("stranger@example.com", FIRST_PASSWORD)
    with serving_administration(project) as origin:
        runtime = ServiceRuntime(ServiceRuntimeConfig(str(root / "service.db"), writes_authorized=True))
        runtime.register_tenant(TenantRegistration("operator", "operator:private"))
        runtime.bind_subject(SubjectBindingRequest("operator", origin + "/auth/v1", bound))
        (root / "manifest.json").write_text(json.dumps({"record_type": MANIFEST_VERSION, "artifact_root": str(root),
                                                        "items": []}))
        (root / "host.json").write_text(json.dumps({
            "record_type": HOST_CONFIGURATION_VERSION, "manifest_path": str(root / "manifest.json"),
            "runtime": {"database_path": str(root / "service.db"), "writes_authorized": True},
            "http": {"public_base_url": ORIGIN, "allowed_hosts": ["service.test"]}, "authentication": {},
            "browser_identity": {"project_url": origin, "publishable_key_ref": "env:FIXTURE_PUBLISHABLE",
                                 "namespace_prefix": "customer", "allow_network": True, "allow_loopback": True},
            "account_email": {"record_type": "service_account_email_configuration/v1", "identity_origin": origin,
                              "identity_service_key_ref": "env:FIXTURE_MARKING_IDENTITY_KEY", "mail_origin": origin,
                              "mail_api_key_ref": "env:FIXTURE_MAIL_KEY", "sender_address": "accounts@example.com",
                              "allow_network": True, "allow_loopback": True},
            "accounts": {"record_type": "service_account_policy/v1",
                         "staff": [{"role": "superadmin", "email": "stranger@example.com"}]}}))

        def run(*arguments):
            printed = io.StringIO()
            with patch.dict(os.environ, {"FIXTURE_MARKING_IDENTITY_KEY": "sb_secret_fixture_only"}), \
                    redirect_stdout(printed):
                status = main(["mark-accounts", "--config", str(root / "host.json"), *arguments])
            return status, json.loads(printed.getvalue())
        _, plan = run()
        stale = run("--apply", "--expected-plan", "0" * 64)
        applied = run("--apply", "--expected-plan", plan["plan_digest"])
        _, again = run()
        second = run("--apply", "--expected-plan", again["plan_digest"])
    check("the_marking_command_lists_then_applies_through_the_service_entry_point_over_a_real_socket",
          plan["changed"] is False and sorted(item["reason"] for item in plan["changes"]) == ["service_account", "staff"]
          and stale == (1, {"record_type": "service_account_marking_refusal/v1", "code": "account_marking_plan_changed"})
          and applied[0] == 0 and len(applied[1]["applied"]) == 2 and again["changes"] == []
          and again["already_honoured"] == 2 and second[0] == 0 and second[1]["changed"] is False
          and all(ACCOUNT_MARKER in user["app_metadata"] for user in project.users.values()))


def run_checks(check, root):
    _guard_checks(check, root)
    _replacement_checks(check, root / "replacement")
    _marking_checks(check, root / "marking")
    _host_file_checks(check, root / "host")
    _command_checks(check, root / "command")
