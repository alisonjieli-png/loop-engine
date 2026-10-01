"""Host-only Public Good policy planning and guarded application; no admission or remote database access.

Run as a module on the host owning the existing catalogue store. The default
prints a plan and changes nothing. Apply binds the exact file, held policy
version and catalogue release; it neither expands a tenant's paid entitlement
nor approves a producer's content.

Maintenance verifies the complete active release header/schema/membership and
only the selected versions' records/files. It never installs a partial serving
view, rebuilds search or claims full-catalogue body qualification.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat

from .public_good import PublicGoodAccess, PublicGoodGrant, PublicGoodLimits, _matches
from .public_good_selection import MAXIMUM_SELECTION, PublicGoodPolicySelection, assert_current, host_selection
from .records import ServiceRuntimeError, digest

REQUEST_VERSION = "service_public_good_policy_request/v1"
MAXIMUM_POLICY_BYTES = 2_000_000


def _unique(pairs):
    values = {}
    for key, value in pairs:
        if key in values:
            raise ServiceRuntimeError("public_good_duplicate_field")
        values[key] = value
    return values


def read_request(raw):
    """Parse the existing versioned policy before opening a host or reading bodies."""
    if not isinstance(raw, bytes) or len(raw) > MAXIMUM_POLICY_BYTES:
        raise ServiceRuntimeError("public_good_policy_file_invalid")
    try:
        request = json.loads(raw, object_pairs_hook=_unique)
        if (not isinstance(request, dict) or set(request) != {
                "record_type", "expected_release", "expected_version", "grants", "limits"}
                or request["record_type"] != REQUEST_VERSION or not isinstance(request["grants"], list)
                or not isinstance(request["expected_release"], str) or not request["expected_release"]
                or request["expected_version"] is not None and not isinstance(request["expected_version"], str)):
            raise ValueError()
        limits = PublicGoodLimits.from_dict(request["limits"])
    except (ValueError, TypeError, KeyError):
        raise ServiceRuntimeError("public_good_policy_file_invalid") from None
    if len(request["grants"]) > MAXIMUM_SELECTION:
        raise ServiceRuntimeError("public_good_selection_limit")
    try:
        grants = tuple(PublicGoodGrant.from_dict(value) for value in request["grants"])
    except (ValueError, TypeError, KeyError):
        raise ServiceRuntimeError("public_good_policy_file_invalid") from None
    if len({grant.binding.identity for grant in grants}) != len(grants):
        raise ServiceRuntimeError("public_good_grant_not_current")
    return request, grants, limits


def _current(runtime, view):
    if isinstance(view, PublicGoodPolicySelection):
        assert_current(runtime._catalog, view)
    else:
        # A caller already holding a full view retains the same API, but an
        # empty prior policy must not make its stale state acceptable.
        from .catalogue_grants import require_served_state
        from .catalogue_releases import read_state
        with runtime._catalog.store() as store:
            _row, state = read_state(runtime._catalog, store)
            require_served_state(state, view)


def apply_policy(runtime, view, raw, *, apply=False, expected_digest=None):
    if type(apply) is not bool:
        raise ServiceRuntimeError("public_good_policy_file_invalid")
    request, grants, limits = read_request(raw)
    file_digest = hashlib.sha256(raw).hexdigest()
    _current(runtime, view)
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
    else:
        _current(runtime, view)
    if isinstance(view, PublicGoodPolicySelection):
        result["selection"] = view.summary()
    return result


def read_policy_file(path):
    """Bound the actual read, reject links/non-regular files and never echo bytes."""
    if not path.is_absolute():
        raise ServiceRuntimeError("public_good_policy_file_invalid")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAXIMUM_POLICY_BYTES:
            raise ServiceRuntimeError("public_good_policy_file_invalid")
        raw = stream.read(MAXIMUM_POLICY_BYTES + 1)
    if len(raw) > MAXIMUM_POLICY_BYTES:
        raise ServiceRuntimeError("public_good_policy_file_invalid")
    return raw


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--expected-digest")
    arguments = parser.parse_args(argv)
    try:
        raw = read_policy_file(Path(arguments.policy))
        request, grants, _limits = read_request(raw)
        runtime, view = host_selection(arguments.config, grants, expected_release=request["expected_release"])
        result = apply_policy(runtime, view, raw, apply=arguments.apply, expected_digest=arguments.expected_digest)
    except (OSError, ServiceRuntimeError) as error:
        print(json.dumps({"record_type":"service_public_good_policy_refusal/v1", "code":getattr(error,"code","public_good_policy_file_invalid")}))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
