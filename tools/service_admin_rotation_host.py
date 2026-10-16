"""Host step of the administrator key rotation; tools/rotate_service_administrator.py uploads and runs it.

Run on the service host as the service user, never as root, so the store's files keep their owner:
  python3 service_admin_rotation_host.py list ADMINISTRATOR
  python3 service_admin_rotation_host.py issue ADMINISTRATOR DAYS REPLACED_KEY_ID
  python3 service_admin_rotation_host.py revoke ADMINISTRATOR KEY_ID

It uses the deployed package's own runtime methods (issue_key, revoke_key) and prints one JSON line. Only
`issue` prints a secret, once, as its last action after every check passed, so a failure never echoes one.
`issue` refuses unless the replaced key is an enabled access-management key of the same tenant, and bounds the
new lifetime to 1 to 90 days. Written October 16, 2026: the September 20 bootstrap key expires October 20 and
the bootstrap operation refuses to run again while an administrator exists.
"""
import json
import sys
import time

from loop_engine.core.service_runtime.catalogue_commands import _host
from loop_engine.core.service_runtime.records import ACCESS_MANAGE_SCOPE, ServiceRuntimeError, TenantKeyIssue
from loop_engine.core.service_runtime.runtime import KEY, ServiceRuntime

LABEL = "Owner administrator"


def keys(runtime, tenant_id):
    with runtime._catalog.store() as store:
        runtime._tenant(store, tenant_id)
        rows = [runtime._payload(row, KEY) for row in runtime._catalog.rows(store, KEY, tenant_id)]
    return [{"key_id": row.get("key_id"), "label": row.get("label"), "enabled": row.get("enabled") is True,
             "expires_at": row.get("expires_at"), "scopes": list(row.get("scopes") or [])} for row in rows]


def main(argv):
    if len(argv) < 2 or argv[0] not in ("list", "issue", "revoke"):
        raise SystemExit(2)
    operation, tenant_id = argv[0], argv[1]
    _configuration, _settings, config = _host("/data/host.json", needs_bodies=False)
    runtime = ServiceRuntime(config)
    now = int(time.time())
    if operation == "list" and len(argv) == 2:
        print(json.dumps({"record_type": "service_admin_rotation_keys/v1", "tenant_id": tenant_id, "now": now,
                          "keys": keys(runtime, tenant_id)}))
        return 0
    if operation == "revoke" and len(argv) == 3:
        result = runtime.revoke_key(tenant_id, argv[2])
        print(json.dumps({"record_type": "service_admin_rotation_revoke/v1", "tenant_id": tenant_id,
                          "key_id": result["key_id"], "revoked": result["revoked"] is True}))
        return 0
    if operation == "issue" and len(argv) == 4:
        days, replaced = int(argv[2]), argv[3]
        if not 1 <= days <= 90:
            raise ServiceRuntimeError("invalid_request", "administrator lifetime is 1 to 90 days")
        current = [row for row in keys(runtime, tenant_id) if row["key_id"] == replaced]
        if (len(current) != 1 or not current[0]["enabled"] or ACCESS_MANAGE_SCOPE not in current[0]["scopes"]
                or (current[0]["expires_at"] is not None and current[0]["expires_at"] <= now)):
            raise ServiceRuntimeError("replaced_key_not_current")
        issued = runtime.issue_key(TenantKeyIssue(tenant_id, LABEL, now + days * 86400, (ACCESS_MANAGE_SCOPE,)))
        print(json.dumps({"record_type": "service_admin_rotation_issue/v1", "tenant_id": issued.tenant_id,
                          "key_id": issued.key_id, "expires_at": issued.expires_at, "issued_at": now,
                          "replaces": replaced, "key": issued.key}))
        return 0
    raise SystemExit(2)


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except ServiceRuntimeError as error:
        print(json.dumps({"record_type": "service_admin_rotation_refusal/v1", "code": error.code}))
        raise SystemExit(1)
