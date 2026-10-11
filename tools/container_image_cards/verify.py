"""The native check of a container image card: the registry still serves every digest the card names, and each
platform's config, parsed again here, says what the card says.

```text
verify(card, reader) -> container_image_registry_check/v1 (verification/registry.json)
├── tag_points_at_index: a HEAD of the resolved tag names the card's index digest; a tag rebuilt since fails it
├── index_resolves: a HEAD of the index by digest answers with that digest and the card's size
├── manifest_resolves, per platform: a HEAD of its manifest by digest, the digest and size the card names
├── config_resolves, per platform: a HEAD of its config blob by digest, the size the card names
└── config_matches_card, per platform: the config's exact bytes (by digest: the reader's checked cache or the
    registry) parsed here, independently of oci.py, against image_contract.platform_runtime() of the card
```

A HEAD costs no pull of the registry's anonymous allowance. The record binds the card digest (every card file but
component.json, the attribution and the verification records), names the registry and carries no time stamp, so
the same registry answers give the same bytes. Read back with read_evidence before a card is packaged.
"""
from __future__ import annotations

import json
import re

from .registry import DIGEST_HEADER, RegistryError

EVIDENCE_RECORD = "container_image_registry_check/v1"
PASSED, FAILED = "passed", "failed"
TAG_CHECK, INDEX_CHECK, MANIFEST_CHECK, CONFIG_CHECK, MATCH_CHECK = CHECK_NAMES = (
    "tag_points_at_index", "index_resolves", "manifest_resolves", "config_resolves", "config_matches_card")
#: The reasons read_evidence gives, each a refusal of the line.
EVIDENCE_UNREADABLE, EVIDENCE_INVALID, EVIDENCE_STALE, CHECK_FAILED = (
    "evidence_unreadable", "evidence_invalid", "evidence_stale", "native_check_failed")
OK = 200
_PORT = re.compile(r"(\d+)(?:-(\d+))?(?:/([a-z]+))?")


class NativeError(ValueError):
    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason, self.detail = reason, detail


def observed_runtime(document: dict) -> dict:
    """The runtime a config states, read on its own: the image configuration specification's field names mapped
    straight to the card's, with no shared code."""
    config = document.get("config") or {}
    health = config.get("Healthcheck")
    ports = set()
    for key in config.get("ExposedPorts") or {}:
        match = _PORT.fullmatch(key)
        if match:
            for number in range(int(match.group(1)), int(match.group(2) or match.group(1)) + 1):
                ports.add((number, match.group(3) or "tcp"))
    variables = {}
    for row in config.get("Env") or []:
        name, separator, value = row.partition("=")
        variables[name] = value if separator else None
    return {"entrypoint": config.get("Entrypoint"), "command": config.get("Cmd"),
            "working_dir": config.get("WorkingDir") or None, "user": config.get("User") or None,
            "stop_signal": config.get("StopSignal") or None, "shell": config.get("Shell"),
            "healthcheck": None if health is None else {
                "test": health.get("Test") or [], "interval_ns": health.get("Interval"),
                "timeout_ns": health.get("Timeout"), "start_period_ns": health.get("StartPeriod"),
                "start_interval_ns": health.get("StartInterval"), "retries": health.get("Retries")},
            "on_build": config.get("OnBuild") or [], "labels": dict(sorted((config.get("Labels") or {}).items())),
            "environment": variables,
            "ports": [{"port": number, "protocol": protocol} for number, protocol in sorted(ports)],
            "volumes": sorted(config.get("Volumes") or {})}


def runtime_differences(card_runtime: dict, observed: dict, withheld: set) -> list:
    """Each field where the card's runtime of a platform and the config's own differ; a withheld value is
    compared by its name only."""
    found = []
    for field in sorted(set(card_runtime) | set(observed)):
        if field == "environment":
            card_names, seen_names = set(card_runtime[field]), set(observed[field])
            if card_names != seen_names:
                found.append(f"environment names differ: {sorted(card_names ^ seen_names)[:6]}")
            for name in sorted(card_names & seen_names):
                if name not in withheld and card_runtime[field][name] != observed[field][name]:
                    found.append(f"environment {name} differs")
        elif card_runtime.get(field) != observed.get(field):
            found.append(f"{field} differs")
    return found


def _check(name: str, subject: str, passed: bool, detail: str = "") -> dict:
    return {"name": name, "subject": subject, "passed": bool(passed), "detail": detail[:300]}


def verify(contract: dict, card_digest: str, reader, module) -> dict:
    """The registry check of one card (``module`` is the shipped image_contract module)."""
    image = contract["image"]
    name = image["name"]
    checks = []

    def head(digest, manifest):
        try:
            return reader.head_document(name, digest, manifest=manifest)
        except RegistryError as error:
            return {"status": None, "digest": None, "size": None, "error": error.reason}

    try:
        tag = reader.read_tag(name, image["resolved_tag"])
        checks.append(_check(TAG_CHECK, image["resolved_tag"], tag.digest == image["index"]["digest"],
                             "" if tag.digest == image["index"]["digest"] else f"now {tag.digest}"))
    except RegistryError as error:
        checks.append(_check(TAG_CHECK, image["resolved_tag"], False, error.reason))
    answer = head(image["index"]["digest"], True)
    checks.append(_check(INDEX_CHECK, image["index"]["digest"], answer["status"] == OK and answer["digest"] ==
                         image["index"]["digest"] and answer["size"] in (None, image["index"]["size"]),
                         str(answer.get("error") or answer["status"])))
    withheld = {row["name"] for row in contract["inputs"]["environment"] if row["withheld"]}
    for row in contract["platforms"]:
        platform = row["platform"] + (f" {row['os_version']}" if row.get("os_version") else "")
        answer = head(row["manifest"]["digest"], True)
        checks.append(_check(MANIFEST_CHECK, platform, answer["status"] == OK and answer["digest"] ==
                             row["manifest"]["digest"] and answer["size"] in (None, row["manifest"]["size"]),
                             str(answer.get("error") or answer["status"])))
        answer = head(row["config"]["digest"], False)
        checks.append(_check(CONFIG_CHECK, platform, answer["status"] == OK and answer["size"] in (
            None, row["config"]["size"]), str(answer.get("error") or answer["status"])))
        try:
            document = reader.read_document(name, row["config"]["digest"], manifest=False).json()
            differences = runtime_differences(module.platform_runtime(contract, row["platform"]),
                                              observed_runtime(document), withheld)
            checks.append(_check(MATCH_CHECK, platform, not differences, "; ".join(differences)))
        except (RegistryError, ValueError) as error:
            checks.append(_check(MATCH_CHECK, platform, False, str(error)))
    return {"record_type": EVIDENCE_RECORD, "state": PASSED if all(check["passed"] for check in checks) else FAILED,
            "card_digest": card_digest, "index_digest": image["index"]["digest"], "engine": reader.profile.name,
            "registry": reader.profile.host, "checks": checks}


def evidence_bytes(record: dict) -> bytes:
    return (json.dumps(record, indent=1, sort_keys=True) + "\n").encode("utf-8")


def read_evidence(data: bytes, card_digest: str, index_digest: str) -> dict:
    """The evidence record when it is a passed check of exactly this card; raises NativeError otherwise."""
    try:
        record = json.loads(data)
    except ValueError:
        raise NativeError(EVIDENCE_UNREADABLE, "not JSON") from None
    if not isinstance(record, dict) or record.get("record_type") != EVIDENCE_RECORD or \
            not isinstance(record.get("checks"), list) or not record["checks"]:
        raise NativeError(EVIDENCE_INVALID, "not a registry check record")
    if record.get("card_digest") != card_digest or record.get("index_digest") != index_digest:
        raise NativeError(EVIDENCE_STALE, "the record checked other bytes")
    failed = [check for check in record["checks"] if not check.get("passed")]
    if record.get("state") != PASSED or failed:
        raise NativeError(CHECK_FAILED, "; ".join(f"{check['name']} {check['subject']}: {check['detail']}"
                                                  for check in failed)[:300])
    return record


__all__ = ["verify", "read_evidence", "evidence_bytes", "observed_runtime", "runtime_differences", "NativeError",
           "EVIDENCE_RECORD", "PASSED", "FAILED", "CHECK_NAMES", "DIGEST_HEADER"]
