"""Checks for staff sign-up links: a superadmin starts Baltor's own sign-up for a few addresses.

The identity provider is the stand-in project with its administration
interface, from `account_origin_checks.py`, and its outbox is the mail
provider. Staff sign in with signed browser tokens from an owned loopback key
set. No provider, mailbox or network outside loopback is used. Every guard has
a removed-guard control that must fail its named check.
"""
from __future__ import annotations

import hashlib
import json
from unittest.mock import patch

from . import staff_sign_up_links as links_module
from .account_administration import AUDIT, AccountAdministration
from .account_email import AccountEmailAdapter, AccountEmailError
from .account_email_checks import DISPLAY_NAME, ORIGIN, _secrets, _settings
from .account_origin import ORIGIN as ORIGIN_KIND, AccountOrigins, SupabaseIdentityAdministration
from .account_origin_checks import MarkingIdentityProjectStandIn, mutated, signed_identity
from .account_policy import ANALYTICS, DEVELOPER, PERMISSIONS, SUPERADMIN, ServiceAccountPolicy
from .free_monthly import ACCESS_HELD, plan_state
from .records import ServiceRuntimeError
from .request_limits import SOCKET_PEER_SOURCE, ServiceRequestLimits
from .runtime import BILLING_POLICY, ENTITLEMENT
from .staff_sign_up_links import (ACTIVATED, HAS_ACCOUNT, LINK, PENDING, SENT, SENT_RECENTLY, StaffSignUpLinkRequest,
                                  send_sign_up_links)

SENDER_NAME = "Sam at Baltor"
#: The password the person chooses on the confirmation page in these checks.
PERSON_PASSWORD = "person-chosen-password-7"
#: One address more than a batch may hold, fixed when this module loads, so a
#: control that raises the limit still sends this many.
TOO_MANY = links_module.MOST_ADDRESSES + 1


class _World:
    """One service with the one way in, a stand-in identity project, three staff members and a customer."""

    def __init__(self, identity, *, founding=None, attempts=3):
        from .browser_identity import BrowserIdentityAdapter
        self.identity, self.runtime = identity, identity.fixture.runtime
        self.project = MarkingIdentityProjectStandIn()
        self.origins = AccountOrigins(self.runtime, identity.issuer, SupabaseIdentityAdministration(
            identity.origin, allow_network=True, transport=self.project.admin))
        self.email = AccountEmailAdapter(_settings(attempts_for_each_email=attempts), _secrets, public_base_url=ORIGIN,
            address_limits=ServiceRequestLimits(client_address_source=SOCKET_PEER_SOURCE, failures_allowed=100),
            display_name=DISPLAY_NAME, identity_transport=self.project.generate_link,
            mail_transport=self.project.send_mail, account_origins=self.origins)
        self.superadmin = identity.person("owner@example.com")
        self.developer = identity.person("developer@example.com")
        self.analytics = identity.person("numbers@example.com")
        self.customer = identity.person("customer@example.com")
        self.policy = ServiceAccountPolicy(founding_free_monthly_accounts=10 if founding is None else founding, staff=(
            {"role": SUPERADMIN, "email": "owner@example.com", "name": SENDER_NAME},
            {"role": DEVELOPER, "provider_user_id": self.developer},
            {"role": ANALYTICS, "email": "numbers@example.com"}))
        self.adapter = BrowserIdentityAdapter(self.runtime, identity.policy, lambda _: "sb_publishable_local_fixture",
                                              transport=self.user, founding_accounts=founding)
        for subject in (self.superadmin, self.developer, self.analytics, self.customer):
            self.adapter.activate(identity.token(subject))
        self.administration = AccountAdministration(self.runtime, self.policy, identity.issuer, origins=self.origins,
                                                    identity_secret=lambda: "sb_secret_fixture")

    def user(self, request):
        """The provider's current user: a staff member of the key set, or a person of the stand-in project."""
        import jwt
        subject = jwt.decode(request.access_token, options={"verify_signature": False})["sub"]
        if subject in self.identity.people:
            return self.identity.user(request)
        held = self.project._user_by_id(subject)
        return self.project.admin_record(held) if held is not None else {}

    def staff(self, subject):
        token = self.identity.token(subject)
        return self.administration.staff_session(self.adapter.authenticate(token),
                                                 hashlib.sha256(token.encode()).hexdigest())

    def send(self, subject, addresses, request_id, free_monthly=False):
        return send_sign_up_links(self.administration, self.email, self.staff(subject),
                                  StaffSignUpLinkRequest(request_id, tuple(addresses), free_monthly))

    def open_link(self, address, chosen=PERSON_PASSWORD):
        """The person opens the newest link, chooses a password, and the page activates the account."""
        token_hash, kind = self.project.links_to(address)[-1]
        session = self.project.verify(token_hash, kind)
        self.project.set_password(session, chosen)
        return self.adapter.activate(self.identity.token(self.project.users[address]["id"]))

    def plan(self, tenant_id):
        catalog = self.runtime._catalog
        with catalog.store() as store:
            _row, tenant = self.runtime._tenant(store, tenant_id)
            return plan_state(self.runtime, tenant, catalog.read(store, ENTITLEMENT, tenant_id),
                              catalog.read(store, BILLING_POLICY, "stripe"))

    def records(self, kind):
        with self.runtime._catalog.store() as store:
            return [row["payload"] for row in self.runtime._catalog.rows_all(store, kind)]

    def stored_text(self):
        """Every byte the service keeps, as text, to search for an address."""
        return "\n".join(path.read_bytes().decode("latin-1") for path in sorted(self.identity.fixture.root.rglob("*"))
                         if path.is_file())


def _code(function):
    try:
        function()
        return None
    except (ServiceRuntimeError, ValueError) as error:
        return getattr(error, "code", type(error).__name__)


def _sends_with_both_marks(root, name):
    """Two new addresses: each gets both marks, one message naming the sender, and a pending record."""
    with signed_identity(root / name, operator_access=False) as identity:
        world = _World(identity)
        addresses = ("first.friend@example.com", "second.friend@example.com")
        result = world.send(world.superadmin, addresses, "two-links")
        users = [world.project.users.get(address) for address in addresses]
        origins = {row["subject"]: row for row in world.records(ORIGIN_KIND)}
        messages = [row for row in world.project.messages if row["to"] in addresses]
        pending = {row["provider_user_id"]: row for row in world.records(LINK)}
        audit = [row for row in world.records(AUDIT) if row.get("operation") == links_module.OPERATION]
        stored = world.stored_text()
        return (result["sent"] == 2 and [row["outcome"] for row in result["links"]] == [SENT, SENT]
                and [row["address"] for row in result["links"]] == list(addresses)
                and all(user is not None and user["app_metadata"].get("baltor_account") for user in users)
                and all(origins.get(user["id"], {}).get("origin") == "signup" for user in users)
                and len(messages) == 2 and all(SENDER_NAME in row["subject"] and SENDER_NAME in row["text"]
                                               and "/auth/confirm?token_hash=" in row["text"]
                                               and "&type=signup" in row["text"] for row in messages)
                and all(world.project.links_to(address)[-1][1] == "signup" for address in addresses)
                and all(pending.get(user["id"], {}).get("state") == PENDING for user in users)
                and len(audit) == 1 and audit[0]["state"] == "completed" and len(audit[0]["address_digests"]) == 2
                and not any(address in stored for address in addresses))


def _limited_roles_send_nothing(root, name):
    with signed_identity(root / name, operator_access=False) as identity:
        world = _World(identity)
        codes = [_code(lambda subject=subject: world.send(subject, ("someone@example.com",), "role-" + str(index)))
                 for index, subject in enumerate((world.developer, world.analytics, world.customer))]
        return (codes == ["account_administration_forbidden", "account_administration_forbidden",
                          "staff_role_required"]
                and not world.project.admin_requests and not world.project.messages and not world.records(LINK))


def _existing_account_gets_no_second_message(root, name):
    with signed_identity(root / name, operator_access=False) as identity:
        world = _World(identity)
        world.send(world.superadmin, ("member@example.com",), "first")
        world.open_link("member@example.com")
        before, links_before = len(world.project.messages), world.project.calls.get("generate_link", 0)
        again = world.send(world.superadmin, ("member@example.com", "newcomer@example.com"), "again")
        # The account is recognised before anything is asked of the provider or
        # counted: only the newcomer's link is generated.
        return ([row["outcome"] for row in again["links"]] == [HAS_ACCOUNT, SENT]
                and len(world.project.messages) == before + 1 and world.project.messages[-1]["to"] == "newcomer@example.com"
                and world.project.calls.get("generate_link", 0) == links_before + 1)


def _batch_over_the_limit_is_refused(root, name):
    with signed_identity(root / name, operator_access=False) as identity:
        world = _World(identity)
        addresses = tuple("person%02d@example.com" % index for index in range(TOO_MANY))
        code = _code(lambda: world.send(world.superadmin, addresses, "too-many"))
        return (code == "sign_up_link_batch_too_large" and not world.project.admin_requests
                and not world.project.messages and not world.records(AUDIT))


def _repeat_within_the_allowance_is_refused(root, name):
    """The allowance for one address that public sign-up keeps, two in the window here, covers links too."""
    with signed_identity(root / name, operator_access=False) as identity:
        world = _World(identity, attempts=2)
        outcomes = [world.send(world.superadmin, ("waiting@example.com",), "repeat-%d" % index)["links"][0]["outcome"]
                    for index in range(3)]
        sent = [row for row in world.project.messages if row["to"] == "waiting@example.com"]
        try:
            world.email.prepare("signup", {"record_type": "service_account_signup_request/v2",
                                           "email": "waiting@example.com"}, "198.51.100.10")
            public = "accepted"
        except AccountEmailError as error:
            public = error.code
        return outcomes == [SENT, SENT, SENT_RECENTLY] and len(sent) == 2 and public == "failed_attempt_limit_reached"


def _replay_and_audit_in_one_write(root, name):
    with signed_identity(root / name, operator_access=False) as identity:
        world = _World(identity)
        first = world.send(world.superadmin, ("replayed@example.com",), "same-request")
        count = len(world.project.messages)
        again = world.send(world.superadmin, ("replayed@example.com",), "same-request")
        changed = _code(lambda: world.send(world.superadmin, ("other@example.com",), "same-request"))
        audit = [row for row in world.records(AUDIT) if row.get("operation") == links_module.OPERATION]
        return (first["replayed"] is False and again["replayed"] is True and again["links"] == first["links"]
                and len(world.project.messages) == count
                and changed == "account_administration_request_identity_conflict"
                and len(audit) == 1 and audit[0]["result"]["links"][0].get("address_digest")
                and "replayed@example.com" not in json.dumps(audit))


def _interrupted_batch_is_not_sent_twice(root, name):
    with signed_identity(root / name, operator_access=False) as identity:
        world = _World(identity)

        def lost(*_arguments):
            raise ServiceRuntimeError("store_unavailable")
        with patch.object(links_module, "_complete", lost):
            first = _code(lambda: world.send(world.superadmin, ("interrupted@example.com",), "lost-write"))
        count = len(world.project.messages)
        retried = _code(lambda: world.send(world.superadmin, ("interrupted@example.com",), "lost-write"))
        return first == "store_unavailable" and retried == "sign_up_links_in_progress" and len(world.project.messages) == count == 1


def _free_monthly_when_the_account_opens(root, name):
    with signed_identity(root / name, operator_access=False) as identity:
        world = _World(identity, founding=10)
        world.send(world.superadmin, ("gifted@example.com",), "gifted", free_monthly=True)
        world.send(world.superadmin, ("plain@example.com",), "plain")
        listing = world.administration.accounts(world.staff(world.superadmin))
        before = {row["email"]: (row.get("sign_up_link") or {}).get("state") for row in listing["accounts"]}
        gifted, plain = world.open_link("gifted@example.com"), world.open_link("plain@example.com")
        after = {row["email"]: (row.get("sign_up_link") or {}).get("state")
                 for row in world.administration.accounts(world.staff(world.superadmin))["accounts"]}
        return (before.get("gifted@example.com") == PENDING and before.get("plain@example.com") == PENDING
                and gifted.get("sign_up_link") == ACTIVATED and world.plan(gifted["tenant_id"]) == "free_monthly"
                and gifted.get("founding_offer") == ACCESS_HELD
                and plain.get("sign_up_link") == ACTIVATED and plain.get("founding_offer") == "granted"
                and world.plan(plain["tenant_id"]) == "founding_free_monthly"
                and after.get("gifted@example.com") == ACTIVATED)


def _http_route(root, name):
    import httpx
    from .http import ServiceHttpApplication
    from .http_test_fixtures import running_http
    from .records import ACCESS_MANAGE_SCOPE, TenantKeyIssue, TenantRegistration
    with signed_identity(root / name, operator_access=False) as identity:
        world = _World(identity)
        world.runtime.register_tenant(TenantRegistration("host-administrator", "host:administrator", (ACCESS_MANAGE_SCOPE,)))
        host_key = world.runtime.issue_key(TenantKeyIssue("host-administrator", "host administration")).key

        def create(config):
            return ServiceHttpApplication(world.runtime, identity.fixture.provisioning, config,
                                          browser_identity=world.adapter, account_email=world.email,
                                          account_administration=world.administration)
        request = {"record_type": links_module.REQUEST_VERSION, "request_id": "over-http",
                   "addresses": ["web.friend@example.com"], "free_monthly": False}
        with httpx.Client(trust_env=False, timeout=10) as client, \
                running_http(identity.fixture, application_factory=create) as (base, _service):
            def post(credential, body, query="", **headers):
                return client.post(base + "/api/v1/admin/sign-up-links" + query, json=body,
                                   headers={"Authorization": "Bearer " + credential, **headers})
            answers = {"superadmin": post(identity.token(world.superadmin), request),
                       "analytics": post(identity.token(world.analytics), {**request, "request_id": "numbers"}),
                       "customer": post(identity.token(world.customer), {**request, "request_id": "customer"}),
                       "host_key": post(host_key, {**request, "request_id": "host"}),
                       "too_many": post(identity.token(world.superadmin), {**request, "request_id": "too-many",
                                        "addresses": ["p%02d@example.com" % index for index in range(11)]}),
                       "foreign": post(identity.token(world.superadmin), {**request, "request_id": "foreign"},
                                       Origin="https://foreign.invalid"),
                       "query": post(identity.token(world.superadmin), {**request, "request_id": "query"}, "?batch=1")}
        codes = {key: (answer.status_code, answer.json().get("error", {}).get("code")) for key, answer in answers.items()}
        good = answers["superadmin"].json()
        return (answers["superadmin"].status_code == 200 and good["execution"]["runtime_type"] == "Loop"
                and good["result"]["links"] == [{"address": "web.friend@example.com", "outcome": SENT,
                                                 "provider_user_id": world.project.users["web.friend@example.com"]["id"]}]
                and codes["analytics"] == (403, "account_administration_forbidden")
                and codes["customer"] == (403, "staff_role_required") and codes["host_key"] == (403, "staff_role_required")
                and codes["too_many"] == (400, "sign_up_link_batch_too_large")
                and codes["foreign"] == (403, "invalid_origin") and codes["query"] == (400, "unknown_request_field")
                and len([row for row in world.project.messages if row["to"] == "web.friend@example.com"]) == 1)


def run_checks(check, root):
    check("a_superadmin_starts_baltor_sign_up_for_each_address_with_both_marks_and_one_message_naming_the_sender",
          _sends_with_both_marks(root, "sends"))
    check("developer_analytics_and_customers_cannot_send_sign_up_links", _limited_roles_send_nothing(root, "roles"))
    with patch("loop_engine.core.service_runtime.account_administration.permissions_for",
               lambda role: frozenset(PERMISSIONS)):
        check("removed_sign_up_link_permission_is_detected", not _limited_roles_send_nothing(root, "roles-mutant"))
    check("an_address_that_already_has_an_account_is_refused_without_a_second_message",
          _existing_account_gets_no_second_message(root, "existing"))
    with mutated(links_module, "_sent_once", "if held is not None and (origins.bound(held.user_id)", "if False and (origins.bound(held.user_id)"):
        check("removed_existing_account_rule_is_detected",
              not _existing_account_gets_no_second_message(root, "existing-mutant"))
    check("a_batch_over_the_limit_is_refused_before_any_provider_request",
          _batch_over_the_limit_is_refused(root, "batch"))
    with patch.object(links_module, "MOST_ADDRESSES", 50):
        check("removed_batch_limit_is_detected", not _batch_over_the_limit_is_refused(root, "batch-mutant"))
    check("a_repeat_within_the_allowance_sign_up_keeps_for_one_address_is_refused_without_a_message",
          _repeat_within_the_allowance_is_refused(root, "repeat"))
    with mutated(links_module, "_sent_once", "if adapter.email_attempts.retry_after(key):", "if False:"):
        check("removed_allowance_for_one_address_is_detected",
              not _repeat_within_the_allowance_is_refused(root, "repeat-mutant"))
    check("a_batch_and_its_audit_record_share_one_request_identity_and_hold_no_address",
          _replay_and_audit_in_one_write(root, "replay"))
    check("an_interrupted_batch_is_not_sent_twice_under_its_request_identity",
          _interrupted_batch_is_not_sent_twice(root, "interrupted"))
    check("free_monthly_is_granted_when_the_account_opens_and_the_link_leaves_the_pending_list",
          _free_monthly_when_the_account_opens(root, "opens"))
    with mutated(links_module, "complete_on_activation", 'if value["free_monthly"]:', "if False:"):
        check("removed_free_monthly_on_activation_is_detected",
              not _free_monthly_when_the_account_opens(root, "opens-mutant"))
    check("the_sign_up_link_route_serves_a_superadmin_and_refuses_everyone_else_over_http", _http_route(root, "http"))
