"""Host-only Public Good policy planning and guarded application; no admission or remote database access.

Run as a module on the host owning the existing catalogue store. The default
prints a plan and changes nothing. Apply binds the exact file, held policy
version and catalogue release; it neither expands a tenant's paid entitlement
nor approves a producer's content.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from .public_good import PublicGoodAccess, PublicGoodGrant, PublicGoodLimits, _matches
from .records import ServiceRuntimeError, digest

REQUEST_VERSION = "service_public_good_policy_request/v1"


def _unique(pairs):
    values = {}
    for key, value in pairs:
        if key in values:
            raise ServiceRuntimeError("public_good_duplicate_field")
        values[key] = value
    return values


def apply_policy(runtime, view, raw, *, apply=False, expected_digest=None):
    if not isinstance(raw, bytes) or len(raw) > 2_000_000:
        raise ServiceRuntimeError("public_good_policy_file_invalid")
    file_digest = hashlib.sha256(raw).hexdigest()
    try:
        request = json.loads(raw, object_pairs_hook=_unique)
        if (not isinstance(request, dict) or set(request) != {
                "record_type", "expected_release", "expected_version", "grants", "limits"}
                or request["record_type"] != REQUEST_VERSION or not isinstance(request["grants"], list)
                or request["expected_version"] is not None and not isinstance(request["expected_version"], str)):
            raise ValueError()
        limits = PublicGoodLimits.from_dict(request["limits"])
        grants = tuple(PublicGoodGrant.from_dict(value) for value in request["grants"])
    except (ValueError, TypeError, KeyError):
        raise ServiceRuntimeError("public_good_policy_file_invalid") from None
    access = PublicGoodAccess(runtime)
    current = access.snapshot(view)
    if request["expected_release"] != view.release_id or not view.release_id:
        raise ServiceRuntimeError("public_good_release_changed")
    if request["expected_version"] != (current.version or None):
        raise ServiceRuntimeError("public_good_policy_changed")
    if len({grant.binding.identity for grant in grants}) != len(grants) or any(
            not _matches(grant, view) or grant.expires_at <= runtime._now() for grant in grants):
        raise ServiceRuntimeError("public_good_grant_not_current")
    result = {"record_type":"service_public_good_policy_plan/v1", "file_digest":file_digest,
        "catalogue_release":view.release_id, "previous_version":current.version or None,
        "grants":len(grants), "payload_digest":digest(request), "applied":False}
    if apply:
        if expected_digest != file_digest:
            raise ServiceRuntimeError("public_good_policy_digest_mismatch")
        committed = access.configure(view, grants, limits=limits, expected_version=request["expected_version"])
        result.update(applied=True, policy_version=committed["version"])
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--expected-digest")
    arguments = parser.parse_args(argv)
    try:
        path = Path(arguments.policy)
        if not path.is_absolute() or path.is_symlink() or not path.is_file() or path.stat().st_size > 2_000_000:
            raise ServiceRuntimeError("public_good_policy_file_invalid")
        from .catalogue_commands import served_view
        runtime, view = served_view(arguments.config)
        result = apply_policy(runtime, view, path.read_bytes(), apply=arguments.apply, expected_digest=arguments.expected_digest)
    except (OSError, ServiceRuntimeError) as error:
        print(json.dumps({"record_type":"service_public_good_policy_refusal/v1", "code":getattr(error,"code","public_good_policy_file_invalid")}))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
