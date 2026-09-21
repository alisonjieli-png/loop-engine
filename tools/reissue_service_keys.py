"""Reissue a short-lived service key and keep it only in the system keyring.

The diagnostic credentials the hosted checks use expire on purpose. This
command asks the running service for a new one, using the administrator
credential already in the keyring, and stores the answer straight back into
the keyring. The new key is never printed, never written to a file and never
put on a command line. It replaces the saved value for that exact account,
because the previous one has expired or been revoked.
"""
from __future__ import annotations

import argparse
import json
import re
import urllib.error
import urllib.parse
import urllib.request
import uuid

ADMIN_PATH = "/api/v1/admin/access"
REQUEST_VERSION = "service_access_request/v1"
SCOPES = ("provisioning:metadata", "provisioning:read", "usage:read")
IDENTIFIER = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_.:-]{0,100}")


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
            return answer.status, json.loads(answer.read(1_000_000).decode())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read(20000).decode() or "{}")


def reissue(origin, hostname, account, tenant, label, lifetime, saved, scopes=None):
    """Issue one key for a tenant and replace the saved value for that account.

    The scope list is read when the command runs, not when the file is
    imported, so narrowing it in one place really narrows every key.
    """
    scopes = tuple(SCOPES if scopes is None else scopes)
    administrator = stored(saved, hostname, "baltor-admin").get_secret().decode()
    status, answer = call(origin, ADMIN_PATH, administrator, {
        "record_type": REQUEST_VERSION, "operation": "issue", "request_id": "reissue-" + uuid.uuid4().hex,
        "tenant_id": tenant, "label": label, "scopes": list(scopes), "lifetime_seconds": lifetime})
    if status != 200:
        raise ReissueError("issue_refused:" + str((answer.get("error") or {}).get("code", status)))
    value = (answer.get("result") or {}).get("token")
    if not isinstance(value, str) or not value:
        raise ReissueError("no_key_in_answer")
    item = stored(saved, hostname, account)
    item.set_secret(value.encode())
    if item.get_secret().decode() != value:
        raise ReissueError("storage_not_confirmed")
    key = (answer.get("result") or {}).get("key") or {}
    return {"account": account, "tenant": tenant, "stored": True, "secret_printed": False,
            "key_id": key.get("key_id"), "expires_at": key.get("expires_at"), "scopes": sorted(scopes)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--origin", required=True, help="Exact HTTPS origin of the running service.")
    parser.add_argument("--account", action="append", required=True,
                        help="Saved account name, which is also its tenant. Repeat for several.")
    parser.add_argument("--lifetime-seconds", type=int, default=86400)
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
        if not IDENTIFIER.fullmatch(account):
            parser.error("an exact account identity is required")
    if not options.confirm_reissue:
        print(json.dumps({"dry_run": True, "would_reissue": options.account, "origin": options.origin}))
        return 0
    try:
        saved = collection()
        results = [reissue(options.origin.rstrip("/"), origin.hostname, account, account,
                           "hosted verification", options.lifetime_seconds, saved)
                   for account in options.account]
    except ReissueError as error:
        print(json.dumps({"refused": str(error)}))
        return 1
    print(json.dumps({"origin": options.origin, "reissued": results}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
