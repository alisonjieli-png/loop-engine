# Records, versions and compatibility

Kind: engineering standard. The governing decision is the
[pre-launch version policy](../architecture/ADR-PRELAUNCH-VERSIONED-CONTRACTS.md).
The [record compatibility guide](../components/loop-object/RECORD-COMPATIBILITY.md)
lists current contracts and the older readers that remain. This standard shows
how the code applies those rules today.

## The rules in short

```text
Record rules
├── 1. A record is a typed immutable object
├── 2. Every record names its type and version
├── 3. Validate in the constructor and refuse before any effect
├── 4. Refuse an unknown version, an unknown field and a duplicate field
├── 5. A record that an older release must not honor gets a new version
├── 6. Do not keep a reader only for an unpublished pre-launch shape
└── 7. Separately deployed components negotiate; they do not guess
```

## 1. A record is a typed immutable object

Configuration, requests and results are frozen data classes, not loose
dictionaries and not long argument lists. Examples in
[records.py](../../src/loop_engine/core/service_runtime/records.py):
`ServiceRuntimeConfig`, `TenantRegistration`, `TenantKeyIssue`,
`SubjectTenantRegistration` and `ServicePrincipal`, each declared with
`@dataclass(frozen=True)`.

- A sequence field is stored as a tuple. `SubjectTenantRegistration`
  normalizes `scopes` and `starter_bindings` in `__post_init__`.
- A secret field is kept out of the printed form. `IssuedServiceKey.key` and
  the private fields of `ServicePrincipal` use `field(repr=False)`.
- A principal is issued in process and is never rebuilt from request data.
  `ServiceRuntime._revalidate` refuses a principal that the same runtime did
  not issue (`unissued_principal`).

## 2. Every record names its type and version

The field is `record_type` and its value looks like `service_key/v2`. The
naming rule is in [Names and nomenclature](NAMES-AND-NOMENCLATURE.md#record-types-and-versions).
Stored rows, wire requests, wire results, configuration files and saved
reports all carry it. `ServiceRuntime` writes `record_type` into every payload
that it stores, and the HTTP adapter wraps every answer in
`service_http_result/v1` or `service_http_error/v1`
([http.py](../../src/loop_engine/core/service_runtime/http.py)).

## 3. Validate in the constructor and refuse before any effect

A record that exists is valid. Each `__post_init__` checks its fields and
raises `ServiceRuntimeError` with a stable code. No database is opened and no
request is sent before that.

- `ServiceRuntimeConfig` refuses a relative path, a symbolic link and a
  write flag that is not a Boolean. Its default is `writes_authorized=False`.
- `ServiceHttpConfiguration` refuses a wildcard host, an origin with a path
  and a limit that is not a positive whole number.
- `ServiceRuntime.issue_key` checks the request type, the expiry, the tenant
  state and scope escalation before it commits the key row.

## 4. Refuse what you do not understand

| Input | Behavior today | Where |
|---|---|---|
| Unknown `record_type` on a configuration record | `unsupported_version` | `ServiceRuntimeConfig.__post_init__` |
| Unknown `record_type` on a wire request | `unsupported_version` | `_validate_search` and `_validate_provisioning` in `http.py` |
| Unknown `record_type` on a stored row | `unsupported_or_corrupt_record` | `ServiceRuntime._payload` in [runtime.py](../../src/loop_engine/core/service_runtime/runtime.py) |
| A field that the contract does not list | `unknown_request_field` | `_validate_search` in `http.py` |
| The same JSON field twice, or a value that is not finite | `invalid_json` | `_parse_json` in `http.py` |

A reader never falls back to an older meaning, never fills a missing field
with a guess and never compares a version by prefix.

## 5. A record that an older release must not honor gets a new version

This is the rule that a rollback depends on. When a new rule makes some
records invalid under conditions that an older release cannot evaluate, the
older release must refuse those records completely. The only way to make it
refuse is a record version that it does not list.

The real example is the personal client key.

- The rule: a key that a customer issued is valid only while the owner's
  sign-in stays enabled.
- The defect: the release candidate stored these keys as `service_key/v1`.
  After a rollback, the older release would read that version, would not know
  the owner rule, and would keep honoring a key whose owner was disabled.
- The repair in `runtime.py`: `OWNER_BOUND_KEY_SCHEMA = KEY + "/v2"`.
  `KEY_SCHEMAS` lists both versions for the current reader. `_payload` in the
  older release lists only `service_key/v1`, so it answers
  `unsupported_or_corrupt_record`.
- The second guard in `ServiceRuntime._principal`: the record version and the
  customer profile must agree. A customer key under the older version, or the
  newer version without the customer profile, is refused by the current
  release as well.
- The writer: `access.py` stores `record_type=OWNER_BOUND_KEY_SCHEMA` when the
  customer profile issues a key. Keys that the operator issues stay
  `service_key/v1`, and the older release still accepts them.

The proof has two levels.

| Level | Check | What it shows |
|---|---|---|
| Source | `version_checks` in `access_checks.py`, for example `customer_key_uses_the_owner_bound_record_version` and the mutant control `removed_key_version_change_is_detected` | The version is written, a mismatch is refused, and a removed version change is noticed. |
| Release | [check_rollback_key_version.py](../../tools/check_rollback_key_version.py) | State written by the current source is read by the real installed code of an older image, in a container without a network. |

The saved drill is
[rollback-key-version-1.json](../../artifacts/architecture-audit-2026-09-19/rollback-key-version-1.json).
It records three cases, including the unfixed candidate whose key the older
image accepted. It used local fixture state, not the deployed volume.

Run the drill before a release that changes stored records:

```bash
.venv/bin/python tools/check_rollback_key_version.py \
  --older-image IMAGE_OF_THE_RUNNING_RELEASE --output NEW_REPORT_PATH
```

Ask this question for every change to a stored record: if the previous
release reads this row after a rollback, is its answer still safe? If not,
the row needs a new version.

## 6. No reader for an unpublished shape

Loop Engine has not launched. Do not add or keep a reader, alias or
constructor only for a record shape that was never published. Update the
callers and the checks together. Keep historical evidence files as bytes; do
not make them runtime input.

Supporting two versions is correct when both are current, as with
`KEY_SCHEMAS`. It is not correct as a way to keep an abandoned shape alive.

## 7. Separately deployed components negotiate

A component that is deployed on its own schedule states what it supports, and
the other side selects an exact shared value or refuses.

- The HTTP adapter accepts one Model Context Protocol version,
  `PROTOCOL_VERSION`, and answers `unsupported_protocol_version` to any other
  (`http.py`). The capabilities record at `/api/v1/capabilities` lists the
  supported versions and limits.
- Storage declares the optional capability `catalog_atomic_write_batch/v1`.
  Domain code asks for the capability and does not branch on a backend class
  ([service runtime README](../../src/loop_engine/core/service_runtime/README.md#persistence-and-concurrency-contract)).

Refuse a downgrade that loses a required meaning, an integrity check or an
authority check. Continuous integration tests the negotiation. It does not
replace the negotiation at run time.
