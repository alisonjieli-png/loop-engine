"""Rotate the service administrator key before it expires, keeping the key only in the system keyring.

The bootstrap of tools/service_admin_operator.py issues the administrator key once and refuses to run again
while an administrator exists, and the key has a bounded lifetime: the September 20, 2026 key expires on
October 20, 2026 at 02:51:28 UTC. tools/reissue_service_keys.py signs every diagnostic key renewal with it and
exits 3 once the service refuses it. This command replaces it without a gap:

1. The saved key must be the only keyring item for the administrator and the service must accept it, as an
   access-management key of that tenant (/api/v1/session).
2. The host step (tools/service_admin_rotation_host.py) is uploaded, owned by the service user, and run as the
   service user; it lists the tenant's keys and, with --confirm-rotation, issues one new key of 1 to 90 days.
3. The new key replaces the saved value in the same keyring item, with key_id, expires_at and issued_at as
   attributes, and is read back. The service must accept it for the same tenant before anything else changes.
   If it does not, the earlier value is put back and the new key is revoked.
4. Only then is the replaced key revoked, and the service must refuse it.

Without --confirm-rotation it only reads and reports. A key is never printed, written to a file or put on a
command line. Run with system Python (secretstorage). Exit status: 0 done, 1 refused before any change,
2 outcome unknown (reconcile with the listing; do not repeat), 3 the service refuses the saved key (recovery
needs the operator bootstrap path, not this command).
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parent
HOST_STEP = ROOT / "service_admin_rotation_host.py"
REMOTE_STEP = "/data/incoming/service-admin-rotation-host.py"
SESSION_PATH = "/api/v1/session"
ACCESS_MANAGE_SCOPE = "access:manage"
EXIT_REFUSED, EXIT_UNKNOWN, EXIT_SAVED_KEY_REFUSED = 1, 2, 3


class RotationError(RuntimeError):
    def __init__(self, code, status=EXIT_REFUSED):
        super().__init__(code)
        self.code, self.status = code, status


def keyring_item(origin_host, administrator, collection=None):
    if collection is None:
        import secretstorage
        collection = secretstorage.get_default_collection(secretstorage.dbus_init())
        if collection.is_locked():
            raise RotationError("credential_store_locked")
    items = list(collection.search_items({"application": "loop-engine", "service": origin_host,
                                          "account": administrator, "purpose": "service-access"}))
    if len(items) != 1:
        raise RotationError("saved_administrator_not_unique")
    return items[0]


def session(origin, value, opener=urllib.request.urlopen):
    """(status, principal) for one credential; the value goes only into the request header."""
    request = urllib.request.Request(origin + SESSION_PATH, headers={"Authorization": "Bearer " + value})
    try:
        with opener(request, timeout=30) as response:
            body = json.loads(response.read(262_144))
            status = response.status
    except urllib.error.HTTPError as error:
        return error.code, None
    result = body.get("result") or {}
    return status, result.get("principal") if result.get("record_type") == "service_session/v1" else None


def accepted(origin, value, administrator, opener=urllib.request.urlopen):
    status, principal = session(origin, value, opener)
    if status == 401:
        return None
    if status != 200 or not principal or principal.get("tenant_id") != administrator or not principal.get("key_id"):
        raise RotationError("session_unreadable")
    if ACCESS_MANAGE_SCOPE not in (principal.get("scopes") or []):
        raise RotationError("saved_key_lacks_access_management")
    return principal["key_id"]


class FlyHost:
    """The exact Machine through the existing operator credential path; commands run as the service user."""

    def __init__(self):
        sys.path.insert(0, str(ROOT))
        import publish_catalogue_delta as operator
        self.operator = operator

    def upload_step(self):
        digest = hashlib.sha256(HOST_STEP.read_bytes()).hexdigest()
        existing = self.operator.machine_exec("test ! -e " + REMOTE_STEP + " || sha256sum " + REMOTE_STEP).split()
        if existing and existing[0] != digest:
            self.operator.machine_exec("rm -f " + REMOTE_STEP)
            existing = []
        if not existing:
            self.operator.fly("ssh", "sftp", "put", str(HOST_STEP), REMOTE_STEP,
                              "--machine", self.operator.MACHINE, "--app", self.operator.APP)
        self.operator.machine_exec("chown 65534:65534 " + REMOTE_STEP + " && chmod 0400 " + REMOTE_STEP)
        if self.operator.machine_exec("sha256sum " + REMOTE_STEP).split()[0] != digest:
            raise RotationError("host_step_digest_mismatch")

    def run(self, *arguments):
        command = self.operator.AS_SERVICE + " /usr/local/bin/python3 " + REMOTE_STEP + " " + " ".join(arguments)
        return json.loads(self.operator.machine_exec(command, as_service=True, timeout=300))


def rotate(*, origin, administrator, days, confirm, item, host, opener=urllib.request.urlopen, clock=time.time):
    report = {"record_type": "service_admin_rotation/v1", "origin": origin, "administrator": administrator,
              "checked_at": int(clock()), "dry_run": not confirm, "secret_printed": False}
    previous = item.get_secret().decode()
    previous_attributes = dict(item.get_attributes())
    old_key = accepted(origin, previous, administrator, opener)
    if old_key is None:
        raise RotationError("saved_key_refused", EXIT_SAVED_KEY_REFUSED)
    report["replaced_key_id"] = old_key
    host.upload_step()
    listing = host.run("list", administrator)
    rows = [row for row in listing.get("keys", []) if row.get("key_id") == old_key]
    if len(rows) != 1 or not rows[0].get("enabled"):
        raise RotationError("saved_key_not_listed")
    report["replaced_key_expires_at"] = rows[0].get("expires_at")
    report["active_administrator_keys_before"] = sum(1 for row in listing["keys"] if row.get("enabled"))
    if not confirm:
        report["would_issue_days"] = days
        return report
    try:
        issued = host.run("issue", administrator, str(int(days)), old_key)
    except Exception:  # noqa: BLE001 - the host may have issued a key; only a listing can tell
        raise RotationError("issue_outcome_unknown", EXIT_UNKNOWN) from None
    new_value, new_key = issued.pop("key", None), issued.get("key_id")
    if issued.get("record_type") != "service_admin_rotation_issue/v1" or not new_value or not new_key:
        raise RotationError("issue_outcome_unknown", EXIT_UNKNOWN)
    facts = {"key_id": new_key, "expires_at": str(issued["expires_at"]), "issued_at": str(issued["issued_at"])}
    try:
        item.set_secret(new_value.encode())
        item.set_attributes({**previous_attributes, **facts})
        stored = item.get_secret().decode() == new_value and all(
            item.get_attributes().get(name) == value for name, value in facts.items())
    except Exception:  # noqa: BLE001
        stored = False
    if not stored or accepted(origin, new_value, administrator, opener) != new_key:
        # Revoke the new key only once the keyring holds the earlier, still accepted value again; otherwise the
        # revocation could leave no working key saved.
        if _saved(item) != previous:
            try:
                _put_back(item, previous, previous_attributes)
            except Exception:  # noqa: BLE001
                pass
        if _saved(item) != previous:
            raise RotationError("keyring_state_unknown", EXIT_UNKNOWN)
        host.run("revoke", administrator, new_key)
        raise RotationError("new_key_not_confirmed")
    report.update(key_id=new_key, expires_at=issued["expires_at"], issued_at=issued["issued_at"])
    revoked = host.run("revoke", administrator, old_key)
    if revoked.get("revoked") is not True or accepted(origin, previous, administrator, opener) is not None:
        report["replaced_key_revoked"] = False
        raise RotationError("replaced_key_still_accepted", EXIT_UNKNOWN)
    report["replaced_key_revoked"] = True
    after = host.run("list", administrator)
    report["active_administrator_keys_after"] = sum(1 for row in after.get("keys", []) if row.get("enabled"))
    return report


def _put_back(item, value, attributes):
    item.set_secret(value.encode())
    item.set_attributes(attributes)


def _saved(item):
    try:
        return item.get_secret().decode()
    except Exception:  # noqa: BLE001
        return None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--origin", required=True,
                        help="Exact HTTPS origin of the service Machine the host step runs on, as saved in the "
                             "keyring, for example the Fly application origin.")
    parser.add_argument("--administrator", default="baltor-admin")
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--confirm-rotation", action="store_true")
    options = parser.parse_args(argv)
    origin = urllib.parse.urlsplit(options.origin)
    if (origin.scheme != "https" or not origin.hostname or origin.path not in ("", "/")
            or origin.query or origin.fragment or origin.port):
        parser.error("an exact HTTPS origin is required")
    if not 1 <= options.days <= 90:
        parser.error("the administrator lifetime is 1 to 90 days")
    try:
        report = rotate(origin=options.origin.rstrip("/"), administrator=options.administrator, days=options.days,
                        confirm=options.confirm_rotation, item=keyring_item(origin.hostname, options.administrator),
                        host=FlyHost())
    except RotationError as error:
        print(json.dumps({"record_type": "service_admin_rotation_refusal/v1", "code": error.code,
                          "secret_printed": False}))
        return error.status
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
