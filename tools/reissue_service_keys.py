"""Reissue a short-lived service key and keep it only in the system keyring.

The diagnostic credentials the hosted checks use expire on purpose. This
command asks the running service for a new one, using the administrator
credential already in the keyring, and stores the answer straight back into
the keyring. The new key is never printed, never written to a file and never
put on a command line. It replaces the saved value for that exact account.
Beside the value, the keyring item gets the key's facts as attributes:
`key_id`, `expires_at` and `issued_at`, which are not secret, so a check can
tell an expired key from a refused one.

With `--renew-within SECONDS` it renews instead of reissuing, which is the form
an unattended timer runs:

- The saved key is checked first. The service's session record names the key
  it accepted, and the administration view gives that key's expiry and scopes.
- Only a key the service refuses, or one that expires within the window, is
  replaced. The new key has the scopes of the key it replaces, never wider
  than `SCOPES`, and the full lifetime.
- The new key must be stored and confirmed, and the service must accept it for
  the same account, before anything else is changed. A new key the service
  does not accept is revoked, and the earlier value is put back when the
  service still accepted it. A key that could not be stored is revoked, so no
  key is left active that nobody holds.
- With `--revoke-replaced` the key a renewal replaced is revoked, and so is
  any other active key of that account that carries this tool's label, so the
  one saved key is the only one of them left active.
- Without `--confirm-reissue` it only reads and reports what it would do.

Exit status: 0 when every account is done, 1 when one was refused, and 3 when
the service refused the administrator credential itself, which no renewal can
repair: that credential is replaced through the operator bootstrap, not here.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

ADMIN_PATH = "/api/v1/admin/access"
SESSION_PATH = "/api/v1/session"
REQUEST_VERSION = "service_access_request/v1"
SESSION_RECORD = "service_session/v1"
SCOPES = ("provisioning:metadata", "provisioning:read", "usage:read")
IDENTIFIER = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_.:-]{0,100}")
#: The label every key this tool issues carries; renewal revokes only keys with this label.
LABEL = "hosted verification"
ADMINISTRATOR_ACCOUNT = "baltor-admin"
#: The failure that no renewal repairs. Its own exit status lets a timer's log say so.
ADMINISTRATOR_REFUSED = "administrator_credential_refused"
EXIT_ADMINISTRATOR_REFUSED = 3


class ReissueError(RuntimeError):
    pass


class RefuseRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args):
        raise ReissueError("redirect_refused")


def collection():
    import secretstorage
    saved = secretstorage.get_default_collection(secretstorage.dbus_init())
    if saved.is_locked():
        raise ReissueError("system_credential_collection_is_locked")
    return saved


def attributes(hostname, account):
    return {"application": "loop-engine", "service": hostname, "account": account, "purpose": "service-access"}


def stored(saved, hostname, account):
    found = list(saved.search_items(attributes(hostname, account)))
    if len(found) != 1:
        raise ReissueError("expected_exactly_one_saved_credential:" + account)
    return found[0]


def call(origin, path, token, body=None, timeout=30):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Authorization": "Bearer " + token, "Accept": "application/json"}
    if data:
        headers["Content-Type"] = "application/json"
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), RefuseRedirect())
    request = urllib.request.Request(origin + path, method="POST" if data else "GET",
                                     headers=headers, data=data)
    try:
        with opener.open(request, timeout=timeout) as answer:
            return answer.status, _json(answer.read(1_000_000))
    except urllib.error.HTTPError as error:
        return error.code, _json(error.read(20000))
    except (urllib.error.URLError, OSError):
        # The outcome of a write is then unknown; nothing here repeats it.
        raise ReissueError("service_unreachable:" + path) from None


def _json(raw):
    try:
        value = json.loads(raw.decode() or "{}")
    except ValueError:
        return {}
    return value if isinstance(value, dict) else {}


def refused(operation, status, answer):
    """The reason one administration request was refused; a refused administrator credential has its own name."""
    if status == 401:
        return ADMINISTRATOR_REFUSED
    return operation + "_refused:" + str((answer.get("error") or {}).get("code", status))


def issue_key(origin, administrator, tenant, label, lifetime, scopes):
    """One new key for a tenant: its value and its facts. The value is only returned, never shown."""
    status, answer = call(origin, ADMIN_PATH, administrator, {
        "record_type": REQUEST_VERSION, "operation": "issue", "request_id": "reissue-" + uuid.uuid4().hex,
        "tenant_id": tenant, "label": label, "scopes": list(scopes), "lifetime_seconds": lifetime})
    if status != 200:
        raise ReissueError(refused("issue", status, answer))
    value = (answer.get("result") or {}).get("token")
    if not isinstance(value, str) or not value:
        raise ReissueError("no_key_in_answer")
    return value, (answer.get("result") or {}).get("key") or {}


def revoke_key(origin, administrator, tenant, key_id):
    """Revoke one key by its identity and confirm the service recorded it revoked."""
    status, answer = call(origin, ADMIN_PATH, administrator, {
        "record_type": REQUEST_VERSION, "operation": "revoke", "request_id": "revoke-" + uuid.uuid4().hex,
        "tenant_id": tenant, "key_id": key_id})
    if status != 200:
        raise ReissueError(refused("revoke", status, answer))
    if ((answer.get("result") or {}).get("key") or {}).get("state") != "revoked":
        raise ReissueError("revoke_not_confirmed:" + key_id)
    return key_id


def managed_keys(origin, administrator, tenant):
    """The administration view's rows for one tenant: identities, labels, scopes, times and states, never values."""
    status, answer = call(origin, ADMIN_PATH, administrator)
    if status != 200:
        raise ReissueError(refused("inspect", status, answer))
    return [row for row in (answer.get("result") or {}).get("tokens") or []
            if isinstance(row, dict) and row.get("tenant_id") == tenant]


def accepted_key(origin, value):
    """The key the service accepts for this value, from its session record, or None when it refuses the value."""
    status, answer = call(origin, SESSION_PATH, value)
    if status == 401:
        return None
    result = answer.get("result") or {}
    principal = result.get("principal") or {}
    if status != 200 or result.get("record_type") != SESSION_RECORD or not principal.get("key_id"):
        raise ReissueError("session_unreadable:" + str(status))
    return {"tenant_id": principal.get("tenant_id"), "key_id": principal["key_id"]}


def facts_of(key):
    """The keyring attributes that describe one issued key, as text."""
    facts = {"key_id": key.get("key_id"), "expires_at": key.get("expires_at"), "issued_at": key.get("created_at")}
    if not isinstance(facts["key_id"], str) or not all(type(facts[name]) is int for name in ("expires_at", "issued_at")):
        raise ReissueError("key_facts_missing_in_answer")
    return {name: str(value) for name, value in facts.items()}


def save(item, value, key):
    """Store one value and its facts in the same keyring item, and confirm both were written."""
    facts = facts_of(key)
    item.set_secret(value.encode())
    if item.get_secret().decode() != value:
        raise ReissueError("storage_not_confirmed")
    item.set_attributes({**item.get_attributes(), **facts})
    held = item.get_attributes()
    if any(held.get(name) != text for name, text in facts.items()):
        raise ReissueError("key_facts_not_confirmed")


def reissue(origin, hostname, account, tenant, label, lifetime, saved, scopes=None):
    """Issue one key for a tenant and replace the saved value for that account.

    The scope list is read when the command runs, not when the file is
    imported, so narrowing it in one place really narrows every key.
    """
    scopes = tuple(SCOPES if scopes is None else scopes)
    administrator = stored(saved, hostname, ADMINISTRATOR_ACCOUNT).get_secret().decode()
    value, key = issue_key(origin, administrator, tenant, label, lifetime, scopes)
    item = stored(saved, hostname, account)
    item.set_secret(value.encode())
    if item.get_secret().decode() != value:
        raise ReissueError("storage_not_confirmed")
    if key.get("key_id") and type(key.get("expires_at")) is int and type(key.get("created_at")) is int:
        item.set_attributes({**item.get_attributes(), **facts_of(key)})
    return {"account": account, "tenant": tenant, "stored": True, "secret_printed": False,
            "key_id": key.get("key_id"), "expires_at": key.get("expires_at"), "scopes": sorted(scopes)}


def renew(origin, hostname, account, lifetime, within, saved, *, write, revoke_replaced, now=None):
    """Check one account's saved key and renew it only when it is refused or expires within `within` seconds."""
    now = int(time.time() if now is None else now)
    item = stored(saved, hostname, account)
    administrator = stored(saved, hostname, ADMINISTRATOR_ACCOUNT).get_secret().decode()
    previous, previous_attributes = item.get_secret().decode(), dict(item.get_attributes())
    previous_facts = {name: previous_attributes.get(name) for name in ("key_id", "expires_at", "issued_at")}
    accepted = accepted_key(origin, previous)
    if accepted is not None and accepted["tenant_id"] != account:
        raise ReissueError("saved_key_belongs_to_another_account:" + account)
    rows = managed_keys(origin, administrator, account)
    # The saved key's row: the key the service accepted, or the one the keyring facts name when it refused it.
    known = accepted["key_id"] if accepted else previous_facts.get("key_id")
    current = next((row for row in rows if known and row.get("key_id") == known), None)
    if accepted is not None and current is None:
        raise ReissueError("saved_key_not_in_the_administration_view:" + account)
    expires_at = current.get("expires_at") if current else None
    due = accepted is None or type(expires_at) is not int or expires_at - now <= within
    others = [row["key_id"] for row in rows if row.get("state") == "active" and row.get("label") == LABEL
              and row.get("key_id") != (accepted or {}).get("key_id")]
    result = {"account": account, "secret_printed": False, "saved_key_accepted": accepted is not None,
              "saved_key_id": known, "saved_key_expires_at": expires_at, "renewal_due": due}
    replaced = [accepted["key_id"]] if accepted and due else []
    if not write:
        return {**result, "dry_run": True, "would_renew": due,
                "would_revoke": (replaced + others) if revoke_replaced else []}
    if not due:
        if current and previous_facts.get("key_id") != accepted["key_id"]:
            # A key saved before facts were written, or by hand: describe the key the service accepted.
            item.set_attributes({**item.get_attributes(), **facts_of(current)})
        revoked = [revoke_key(origin, administrator, account, key_id) for key_id in others] if revoke_replaced else []
        return {**result, "action": "kept", "key_id": accepted["key_id"], "expires_at": expires_at, "revoked": revoked}
    held_scopes = (current or {}).get("scopes")
    scopes = [scope for scope in SCOPES if not isinstance(held_scopes, list) or scope in held_scopes]
    if not scopes:
        raise ReissueError("replaced_key_holds_no_renewable_scope:" + account)
    value, key = issue_key(origin, administrator, account, LABEL, lifetime, scopes)
    try:
        save(item, value, key)
        confirmed = accepted_key(origin, value)
        if confirmed != {"tenant_id": account, "key_id": key.get("key_id")}:
            raise ReissueError("new_key_not_accepted:" + account)
    except Exception as error:  # noqa: BLE001 - any failure here leaves the earlier value saved and the new key revoked
        failure = error if isinstance(error, ReissueError) else ReissueError("storage_failed:" + type(error).__name__)
        try:
            _put_back(item, previous, previous_attributes)
        except Exception as restore_error:  # noqa: BLE001 - the keyring may still hold the new key, so it stays active
            raise ReissueError("{}; the earlier value was not restored ({}), so the new key {} stays active".format(
                failure, type(restore_error).__name__, key.get("key_id"))) from None
        try:
            revoke_key(origin, administrator, account, key.get("key_id"))
        except ReissueError as revoke_failure:
            failure = ReissueError("{}; the new key {} was not revoked: {}".format(failure, key.get("key_id"), revoke_failure))
        raise failure from None
    revoked = [revoke_key(origin, administrator, account, key_id) for key_id in replaced + others] if revoke_replaced else []
    return {**result, "action": "renewed", "key_id": key.get("key_id"), "expires_at": key.get("expires_at"),
            "scopes": scopes, "revoked": revoked}


def _put_back(item, value, held_attributes):
    """Restore the value and attributes the item held before a renewal that did not complete."""
    item.set_secret(value.encode())
    item.set_attributes(held_attributes)
    if item.get_secret().decode() != value:
        raise ReissueError("earlier_value_not_restored")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--origin", required=True, help="Exact HTTPS origin of the running service.")
    parser.add_argument("--account", action="append", required=True,
                        help="Saved account name, which is also its tenant. Repeat for several.")
    parser.add_argument("--lifetime-seconds", type=int, default=86400)
    parser.add_argument("--renew-within", type=int, metavar="SECONDS",
                        help="Renew only a saved key the service refuses or one that expires within this many "
                             "seconds, after checking it. Without it every named account is reissued.")
    parser.add_argument("--revoke-replaced", action="store_true",
                        help="With --renew-within: revoke the key a renewal replaced and any other active key this "
                             "tool issued for the account.")
    parser.add_argument("--confirm-reissue", action="store_true",
                        help="Required. Reissuing replaces the saved value for that account.")
    options = parser.parse_args(argv)
    origin = urllib.parse.urlsplit(options.origin)
    if (origin.scheme != "https" or not origin.hostname or origin.path not in ("", "/")
            or origin.query or origin.fragment):
        parser.error("an exact HTTPS origin is required")
    if not 60 <= options.lifetime_seconds <= 604800:
        parser.error("a key lives between one minute and seven days")
    for account in options.account:
        if not IDENTIFIER.fullmatch(account) or account == ADMINISTRATOR_ACCOUNT:
            parser.error("an exact account identity is required")
    if options.renew_within is not None and not 0 <= options.renew_within < options.lifetime_seconds:
        parser.error("the renewal window must be shorter than the lifetime a renewal gives")
    if options.revoke_replaced and options.renew_within is None:
        parser.error("--revoke-replaced works with --renew-within")
    if options.renew_within is not None:
        return run_renewal(options, origin.hostname)
    if not options.confirm_reissue:
        print(json.dumps({"dry_run": True, "would_reissue": options.account, "origin": options.origin}))
        return 0
    try:
        saved = collection()
        results = [reissue(options.origin.rstrip("/"), origin.hostname, account, account,
                           LABEL, options.lifetime_seconds, saved)
                   for account in options.account]
    except ReissueError as error:
        print(json.dumps({"refused": str(error)}))
        return EXIT_ADMINISTRATOR_REFUSED if str(error) == ADMINISTRATOR_REFUSED else 1
    print(json.dumps({"origin": options.origin, "reissued": results}))
    return 0


def run_renewal(options, hostname):
    """Renew each named account in turn; one refused account does not stop the next."""
    checked_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    results, failures = [], []
    try:
        saved = collection()
    except ReissueError as error:
        print(json.dumps({"origin": options.origin, "checked_at": checked_at, "renewal_ok": False,
                          "refused": str(error)}))
        return 1
    for account in options.account:
        try:
            results.append(renew(options.origin.rstrip("/"), hostname, account, options.lifetime_seconds,
                                 options.renew_within, saved, write=options.confirm_reissue,
                                 revoke_replaced=options.revoke_replaced))
        except ReissueError as error:
            failures.append(str(error))
            results.append({"account": account, "refused": str(error), "secret_printed": False})
    print(json.dumps({"origin": options.origin, "checked_at": checked_at, "dry_run": not options.confirm_reissue,
                      "renewal_ok": not failures, "renewal": results}))
    if ADMINISTRATOR_REFUSED in failures:
        return EXIT_ADMINISTRATOR_REFUSED
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
