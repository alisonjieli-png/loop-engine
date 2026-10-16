"""Private model endpoints: named in the repository by reference, read from operator configuration at run time.

Kind: operator configuration reader. The address of a private model server is
infrastructure the public repository does not carry. The owner's Tactical
server is the one such endpoint today. The repository names its two settings
only by operator references in ``tools/operator_credentials.json``, the same
manifest that names the server's key:

| Setting | Operator reference | Environment variable |
|---|---|---|
| the connect URL, its OpenAI-compatible API base | ``tactical-model-endpoint`` | ``LOOP_ENGINE_TACTICAL_BASE_URL`` |
| the DNS name its certificate proves, when another than the URL host | ``tactical-model-tls-server-name`` | ``LOOP_ENGINE_TACTICAL_TLS_SERVER_NAME`` |

Each setting is read when a caller is about to connect: the environment
variable the reference declares wins, otherwise the system keyring item of
that reference is read through ``tools/operator_credentials.py``. A missing
connect URL refuses with ``private_endpoint_unconfigured`` before any socket
opens, and the message says what to set. A missing certificate name means the
certificate must name the URL host itself; hostname checking stays on either
way. A malformed value refuses with ``private_endpoint_invalid``. No message,
summary or record carries a configured value: a summary holds SHA-256 digests.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

TOOLS = Path(__file__).resolve().parent
MANIFEST = TOOLS / "operator_credentials.json"
SUMMARY_TYPE = "private_endpoint_summary/v1"

#: Each private endpoint and the operator reference of each of its settings.
PRIVATE_ENDPOINTS = {
    "tactical": {"base_url": "tactical-model-endpoint",
                 "tls_server_name": "tactical-model-tls-server-name"},
}
#: The provider settings fields a committed provider binding may take from an operator reference.
REFERENCE_FIELDS = {"endpoint": "base_url", "tls_server_name": "tls_server_name"}
REFERENCE_NAME = re.compile(r"[a-z][a-z0-9-]{0,63}")
#: A lower-case DNS name of letters, digits and inner hyphens, with at least one dot and no wildcard.
DNS_NAME = re.compile(r"(?=.{1,253}\Z)[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+\Z")
API_PATH = re.compile(r"(?:/[A-Za-z0-9._~-]+)*")


class PrivateEndpointError(ValueError):
    """A private endpoint setting is missing or malformed. The message names what to set, never a value."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code


def _sha256(value: str) -> str | None:
    return hashlib.sha256(value.encode("utf-8")).hexdigest() if value else None


@dataclass(frozen=True)
class PrivateEndpoint:
    """The resolved settings of one private endpoint. Never printed or recorded as values."""

    name: str
    base_url: str
    tls_server_name: str = ""
    sources: tuple = ()

    @property
    def host(self) -> str:
        return urlsplit(self.base_url).hostname or ""

    @property
    def port(self) -> int:
        return urlsplit(self.base_url).port or 443

    def __repr__(self) -> str:
        return f"PrivateEndpoint(name={self.name!r}, settings=<private>)"

    def summary(self) -> dict:
        """Digests and sources only, so a record can show which settings ran without holding them."""
        return {"record_type": SUMMARY_TYPE, "private_endpoint": self.name,
                "base_url_sha256": _sha256(self.base_url),
                "tls_server_name_sha256": _sha256(self.tls_server_name),
                "sources": dict(self.sources)}


def references_manifest(path: Path = MANIFEST) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("record_type") != "operator_credential_references/v1":
        raise PrivateEndpointError("private_setting_manifest_invalid",
                                   f"{path.name} is not an operator reference manifest")
    return data


def _keyring_value(reference: str) -> str:
    """The keyring item of one reference, through the existing operator credential helper."""
    module = sys.modules.get("tools.operator_credentials") or sys.modules.get("operator_credentials")
    if module is None:
        spec = importlib.util.spec_from_file_location("operator_credentials", TOOLS / "operator_credentials.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    return module.resolve(reference)


def _well_formed(value: str, spec: dict) -> bool:
    """The reference's own declared shape: required prefixes and the exact value pattern."""
    if not value.isascii() or any(ord(character) < 33 or ord(character) == 127 for character in value):
        return False
    prefixes = spec.get("required_prefixes") or ()
    if prefixes and not any(value.startswith(prefix) for prefix in prefixes):
        return False
    pattern = spec.get("value_pattern")
    return not pattern or re.fullmatch(pattern, value) is not None


def setting(reference: str, *, environ=None, keyring=None, manifest: dict | None = None) -> tuple[str, str]:
    """(value, source) of one operator reference: its environment variable, else its keyring item.

    The source is ``environment``, ``keyring`` or ``absent``. A keyring that is locked, missing or
    unreachable counts as absent; a value of the wrong shape refuses.
    """
    if type(reference) is not str or not REFERENCE_NAME.fullmatch(reference):
        raise PrivateEndpointError("private_setting_reference_invalid", "a reference is a lower-case name")
    data = manifest if manifest is not None else references_manifest()
    spec = data.get("api_keys", {}).get(reference)
    if spec is None or not spec.get("environment"):
        raise PrivateEndpointError("private_setting_reference_unknown",
                                   f"{reference} is not declared in tools/operator_credentials.json")
    variable = spec["environment"]
    value = str((os.environ if environ is None else environ).get(variable, "")).strip()
    source = "environment"
    if not value:
        try:
            value = str((keyring or _keyring_value)(reference) or "").strip()
        except Exception:  # noqa: BLE001 - an unreachable keyring is an absent setting, never a printed error
            value = ""
        source = "keyring"
    if not value:
        return "", "absent"
    if not _well_formed(value, spec):
        raise PrivateEndpointError("private_endpoint_invalid",
                                   f"the value of {variable} (or the keyring item {reference}) has the wrong shape")
    return value, source


def validated_base_url(value: str, label: str) -> str:
    """An https:// API base with a host, no credentials, query or fragment, and no trailing slash."""
    parts = urlsplit(value)
    try:
        port = parts.port
    except ValueError:
        port = -1
    if (parts.scheme != "https" or not parts.hostname or parts.username is not None or parts.password is not None
            or parts.query or parts.fragment or port == -1 or not API_PATH.fullmatch(parts.path.rstrip("/"))
            or parts.hostname != parts.hostname.lower()):
        raise PrivateEndpointError("private_endpoint_invalid",
                                   f"{label} must be an https:// API base such as https://host:port/v1")
    return value.rstrip("/")


def _guidance(reference: str, variable: str) -> str:
    return (f"set {variable}, or store it once with "
            f"`python3 tools/operator_credentials.py store --ref {reference}`")


def resolve(name: str, *, environ=None, keyring=None, manifest: dict | None = None) -> PrivateEndpoint:
    """The settings of one declared private endpoint, read now; refuses when the connect URL is absent."""
    references = PRIVATE_ENDPOINTS.get(name)
    if references is None:
        raise PrivateEndpointError("private_endpoint_undeclared", f"{name!r} is not a declared private endpoint")
    data = manifest if manifest is not None else references_manifest()
    url_reference, name_reference = references["base_url"], references["tls_server_name"]
    url_variable = data["api_keys"][url_reference]["environment"]
    base_url, url_source = setting(url_reference, environ=environ, keyring=keyring, manifest=data)
    if not base_url:
        raise PrivateEndpointError("private_endpoint_unconfigured",
                                   f"the {name} endpoint's connect URL is not configured: "
                                   + _guidance(url_reference, url_variable))
    base_url = validated_base_url(base_url, url_variable)
    server_name, name_source = setting(name_reference, environ=environ, keyring=keyring, manifest=data)
    if server_name and not DNS_NAME.fullmatch(server_name):
        raise PrivateEndpointError("private_endpoint_invalid",
                                   f"{data['api_keys'][name_reference]['environment']} must be a lower-case DNS name")
    return PrivateEndpoint(name, base_url, server_name,
                           (("base_url", url_source), ("tls_server_name", name_source)))


def resolve_references(references: dict, *, environ=None, keyring=None, manifest: dict | None = None) -> dict:
    """Provider settings fields read from the operator references a committed provider binding names.

    ``references`` maps ``endpoint`` (required) and ``tls_server_name`` (optional) to reference names.
    Returns the fields to merge into the binding's provider block; an unset certificate name is left out,
    so the certificate must then name the URL host.
    """
    if (type(references) is not dict or "endpoint" not in references
            or not set(references) <= set(REFERENCE_FIELDS)):
        raise PrivateEndpointError("private_setting_references_invalid",
                                   "a binding names endpoint and optionally tls_server_name by reference")
    data = manifest if manifest is not None else references_manifest()
    resolved = {}
    for field, reference in sorted(references.items()):
        value, _source = setting(reference, environ=environ, keyring=keyring, manifest=data)
        variable = data["api_keys"][reference]["environment"]
        if field == "endpoint":
            if not value:
                raise PrivateEndpointError("private_endpoint_unconfigured",
                                           "the binding's endpoint is not configured: "
                                           + _guidance(reference, variable))
            resolved[field] = validated_base_url(value, variable)
        elif value:
            if not DNS_NAME.fullmatch(value):
                raise PrivateEndpointError("private_endpoint_invalid", f"{variable} must be a lower-case DNS name")
            resolved[field] = value
    return resolved
