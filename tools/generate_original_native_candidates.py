"""Generate original complete native candidates through ModelGateway, never approve them.

The frozen plan owns method identity, effects, dependencies, paths and roles.
The model supplies UTF-8 file text only. The existing native factory owns
package identity and materialization. A private run journal records dispatch
before the provider call; an interrupted dispatch is never repeated silently.

The provider is Ollama Cloud with a reviewed panel installation, or one
committed provider binding (``original_native_generation_provider_binding/v1``)
that selects a custom endpoint through the existing settings, endpoint and
gateway contracts, with its own family evidence, measured capacity record,
TLS trust and operator credential reference.
"""
from __future__ import annotations

import argparse
import base64
import fcntl
import hashlib
import inspect
import json
import os
import re
import stat
import sys
import time
from dataclasses import dataclass, replace
from pathlib import Path

if __name__ == "__main__" and __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from loop_engine.core import runtime_settings, settings_loader
from loop_engine.core.custom_endpoint import EndpointError
from loop_engine.core.model_call_records import default_secret_patterns
from loop_engine.core.model_capabilities import (
    ModelOutputAllocation,
    ModelOutputCapability,
)
from loop_engine.core.model_gateway import (
    ModelGateway,
    ModelGatewayConfig,
    ModelGatewayRequest,
    builtin_provider_specs,
    provider_spec_from_endpoint,
)
from loop_engine.core.model_response_admission import (
    ModelResponseAdmissionPolicy,
    ModelResponseAdmissionRequest,
    ModelResponseContract,
    admit_model_response_as_loop,
)
from loop_engine.core.model_routes import ModelRoute, screen_route
from loop_engine.core.model_token_preflight import ProviderTokenBound
from loop_engine.core.service_runtime.catalogue_packages import (
    CataloguePackage,
    placement_path,
)
from loop_engine.core.workspace_local import _atomic_write
from loop_engine.strings.prompt_fragments import (
    PromptResourceBundle,
    PromptResourceComponent,
)
from tools import native_harness_candidates as native
from tools import prepare_harness_candidates as factory

PLAN_TYPE = "original_native_generation_plan/v1"
DRAFT_TYPE = "original_native_file_draft/v1"
RUN_TYPE = "original_native_generation_run/v7"
EVENT_TYPE = "original_native_generation_event/v3"
BINDING_TYPE = "original_native_generation_provider_binding/v1"
CAPACITY_TYPE = "endpoint_output_capacity/v1"
FAMILY_EVIDENCE_TYPE = "generation_producer_family_evidence/v1"
BINDING_FIELDS = {"record_type", "binding_id", "provider", "trust_anchor_sha256", "producer_family",
                  "family_evidence", "capacity", "credential_reference"}
PANEL_PATH = "tools/candidate_review/resources/panel.json"
STOP_ERROR_CODES = ("rate_limited", "provider_unavailable", "authentication_failed", "timeout",
                    "model_identity_mismatch", "model_not_found", "missing_credential", "tls_trust_refused",
                    "usage_limit_reached", "payment_required")
PLAN_FIELDS = {"record_type", "source_revision", "license", "sources", "methods"}
METHOD_FIELDS = (native.NATIVE_FIELDS - {"files", "producer"}) | {"brief", "acceptance", "files", "opportunity"}
FILE_FIELDS = {"path", "role", "media_type", "purpose"}
MAX_PLAN_BYTES = 16 * 1024 * 1024
MAX_DRAFT_BYTES = 2 * 1024 * 1024
MAX_JOURNAL_BYTES = 64 * 1024 * 1024
PROMPT_RESOURCE_TYPE = "original_native_generation_prompt/v1"
PROMPT_RESOURCE_PATH = Path(__file__).resolve().parent / "resources/original-native-generation-prompt-v1.json"
MAX_PROMPT_RESOURCE_BYTES = 32 * 1024
#: The draft's own shape, checked by the existing response admission Loop
#: before the exact draft parser. Admission may remove only one exact
#: enclosing Markdown JSON fence, and records it; every other deviation stays
#: a refusal.
DRAFT_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["record_type", "method_id", "files"],
                "properties": {"record_type": {"const": DRAFT_TYPE}, "method_id": {"type": "string"},
                               "files": {"type": "array", "items": {
                                   "type": "object", "additionalProperties": False, "required": ["path", "content"],
                                   "properties": {"path": {"type": "string"}, "content": {"type": "string"}}}}}}
DRAFT_ADMISSION = ModelResponseContract(
    DRAFT_TYPE, json.dumps(DRAFT_SCHEMA),
    ModelResponseAdmissionPolicy(allowed_strategies=("strict_json", "json_markdown_fence_removed")))
#: The delimited-block draft format: each planned file travels in its own
#: block with its path and no escaping, after a two-line header. The run
#: chooses the format; run.json names it.
BLOCKS_TYPE = "original_native_file_blocks/v1"
BLOCKS_PROMPT_RESOURCE_PATH = Path(__file__).resolve().parent / "resources/original-native-generation-blocks-prompt-v1.json"
BLOCKS2_TYPE = "original_native_file_blocks/v2"
BLOCKS2_PROMPT_RESOURCE_PATH = (Path(__file__).resolve().parent
                                / "resources/original-native-generation-blocks-prompt-v2.json")
DRAFT_FORMATS = {
    "json": {"record_type": DRAFT_TYPE, "prompt": PROMPT_RESOURCE_PATH, "bundle_id": "original_native_generation",
             "version": "1.0.0"},
    "blocks": {"record_type": BLOCKS_TYPE, "prompt": BLOCKS_PROMPT_RESOURCE_PATH,
               "bundle_id": "original_native_generation_blocks", "version": "1.0.0"},
    "blocks2": {"record_type": BLOCKS2_TYPE, "prompt": BLOCKS2_PROMPT_RESOURCE_PATH,
                "bundle_id": "original_native_generation_blocks", "version": "2.0.0"},
}
BLOCKS_ADMISSION = {"record_type": BLOCKS_TYPE, "parser": "strict_line_blocks/v1",
                    "repair": "one exact enclosing Markdown fence may be removed, and is recorded",
                    "outside_blocks": "blank lines only"}
BLOCKS2_ADMISSION = {"record_type": BLOCKS2_TYPE, "parser": "strict_line_blocks/v2",
                     "file_lines": ["<<<path>>>", "<<<FILE path>>>"],
                     "end_lines": ["<<<END path>>>", "<<<END FILE path>>>",
                                   "omitted before the next planned file or END DRAFT, and recorded"],
                     "repair": "one exact enclosing Markdown fence may be removed, and is recorded",
                     "outside_blocks": "blank lines only", "inside_blocks": "no marker-shaped line"}
DRAFT_BEGIN, DRAFT_END = "<<<DRAFT>>>", "<<<END DRAFT>>>"
MARKER_LINE = re.compile(r"<<<[^<>\n]+>>>")
FILE_BEGIN = re.compile(r"<<<FILE (?P<path>[^<>\n]+)>>>")
HEADER_KEYS = ("record_type", "method_id")
BLOCKS_FENCE = re.compile(r"\s*```(?P<info>[A-Za-z0-9_+-]*)[ \t]*\n(?P<body>.*)\n```[ \t]*\s*", re.DOTALL)


class GenerationError(ValueError):
    """A stable safe error code, never private model output."""


def refuse(code):
    raise GenerationError(code)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def strict_json(raw):
    def pairs(values):
        result = {}
        for key, value in values:
            if key in result:
                refuse("duplicate_json_key")
            result[key] = value
        return result
    try:
        return json.loads(raw, object_pairs_hook=pairs,
                          parse_constant=lambda _value: refuse("nonfinite_json"))
    except (ValueError, TypeError, UnicodeError, RecursionError) as error:
        if isinstance(error, GenerationError):
            raise
        refuse("invalid_json")


def exact(value, fields, code):
    if type(value) is not dict or set(value) != fields:
        refuse(code)


def text(value, maximum=12000):
    if type(value) is not str or not value.strip() or len(value) > maximum or "\x00" in value:
        refuse("invalid_text")
    try:
        value.encode("utf-8")
    except UnicodeError:
        refuse("invalid_utf8")
    return value


def secret_present(value):
    return any(re.search(pattern, value) for pattern in default_secret_patterns())


def redacted(value):
    for pattern in default_secret_patterns():
        value = re.sub(pattern, "[redacted secret-shaped text]", value)
    return value


def plain_path(path):
    path = Path(path).absolute()
    if path.resolve() != path or any(p.is_symlink() for p in [path, *path.parents]):
        refuse("path_not_plain")
    return path


def read_file(path, maximum):
    path = plain_path(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > maximum:
            refuse("file_not_bounded_regular")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            raw = stream.read(maximum + 1)
        if len(raw) > maximum:
            refuse("file_too_large")
        return raw
    finally:
        os.close(fd)


def load_prompt_resource(draft_format="json"):
    """Read exact operator-owned semantics through the existing prompt bundle owner."""
    form = DRAFT_FORMATS[draft_format]
    raw = read_file(form["prompt"], MAX_PROMPT_RESOURCE_BYTES)
    value = strict_json(raw)
    exact(value, {"record_type", "bundle_id", "version", "system"}, "prompt_resource_fields_invalid")
    if value["record_type"] != PROMPT_RESOURCE_TYPE:
        refuse("prompt_resource_version_unsupported")
    if value["bundle_id"] != form["bundle_id"] or value["version"] != form["version"]:
        refuse("prompt_resource_identity_unsupported")
    system = text(value["system"], MAX_PROMPT_RESOURCE_BYTES)
    if secret_present(system):
        refuse("prompt_resource_contains_secret")
    try:
        bundle = PromptResourceBundle(
            bundle_id=value["bundle_id"], version=value["version"],
            components=(PromptResourceComponent("system", system, ()),), slots=(),
            output_schema_ref=form["record_type"], interpreter_profile_ref="original_native_generation/v1",
            policy_ref=PLAN_TYPE)
        rendered = bundle.render({}, provenance={})
    except (ValueError, KeyError, TypeError):
        refuse("prompt_resource_invalid")
    return rendered.text, {"record_type": PROMPT_RESOURCE_TYPE,
        "path": form["prompt"].relative_to(Path(__file__).resolve().parents[1]).as_posix(),
        "sha256": digest(raw), "render": rendered.to_dict()}


def require_provider_credential(spec):
    """Ollama-only presence check; the selected adapter owns credential discovery.

    load_api_key is the Ollama adapter's existing local-only resolver. Do not
    use verify/live_models here: they can perform provider requests outside the
    generation call ledger. Presence does not establish credential validity.
    """
    if spec.provider_id != "ollama_cloud":
        refuse("provider_not_supported_for_generation")
    resolver = getattr(spec.adapter, "load_api_key", None)
    if not callable(resolver):
        refuse("provider_credential_unavailable")
    try:
        present = bool(resolver())
    except (OSError, ValueError, TypeError):
        refuse("provider_credential_unavailable")
    if not present:
        refuse("provider_credential_unavailable")


@dataclass(frozen=True)
class ProviderBinding:
    """One committed provider binding, validated before any provider exists.

    It holds the parsed ProviderSettings (repository-relative trust anchor),
    the capacity from its measured record, the producer family from its
    evidence, and the name of an operator credential reference. It never
    holds a credential.
    """

    binding_id: str
    path: str
    sha256: str
    settings: runtime_settings.ProviderSettings
    capability: ModelOutputCapability
    producer_family: str
    trust_anchor_sha256: str | None
    family_evidence_sha256: str
    capacity_sha256: str
    panel_sha256: str
    credential_reference: str

    def summary(self):
        return {"record_type": BINDING_TYPE, "binding_id": self.binding_id, "path": self.path,
                "sha256": self.sha256, "settings_sha256": digest(canonical(self.settings.safe_summary())),
                "endpoint": self.settings.endpoint, "tls_verification": self.settings.tls_verification,
                "tls_server_name": self.settings.tls_server_name,
                "tls_pinned_sha256": self.settings.tls_pinned_sha256,
                "trust_anchor_sha256": self.trust_anchor_sha256,
                "family_evidence_sha256": self.family_evidence_sha256,
                "capacity_sha256": self.capacity_sha256, "panel_vocabulary_sha256": self.panel_sha256,
                "credential_reference": "operator:" + self.credential_reference}


def committed_bytes(repository, revision, relative, expected, code):
    """Bytes of one repository file that are committed unchanged at the plan revision."""
    if type(relative) is not str or type(expected) is not str:
        refuse(code)
    try:
        factory._checked_source(repository, revision, relative, expected)
    except factory.PreparationError:
        refuse(code)
    raw = read_file(repository / relative, MAX_PLAN_BYTES)
    if digest(raw) != expected:
        refuse(code)
    return raw


def committed_record(repository, revision, reference, record_type, code):
    """A small JSON record named by {path, sha256}, committed at the plan revision."""
    exact(reference, {"path", "sha256"}, code)
    raw = committed_bytes(repository, revision, reference["path"], reference["sha256"], code)
    if secret_present(raw.decode("utf-8")):
        refuse(code)
    value = strict_json(raw)
    if type(value) is not dict or value.get("record_type") != record_type:
        refuse(code)
    return value


def load_provider_binding(repository, revision, path, expected_digest, model, family):
    """Validate one provider binding and everything it names, before any credential is read."""
    raw = committed_bytes(repository, revision, path, expected_digest, "provider_binding_not_committed")
    if secret_present(raw.decode("utf-8")):
        refuse("provider_binding_contains_secret")
    value = strict_json(raw)
    exact(value, BINDING_FIELDS, "provider_binding_fields_invalid")
    if value["record_type"] != BINDING_TYPE:
        refuse("provider_binding_version_unsupported")
    if type(value["binding_id"]) is not str or not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", value["binding_id"]):
        refuse("provider_binding_identity_invalid")
    provider = value["provider"]
    if type(provider) is not dict or any(key in provider for key in (
            "credential_env", "maximum_output_tokens", "maximum_output_source")):
        # One credential path (the operator reference) and one capacity source (the record).
        refuse("provider_binding_settings_invalid")
    # The settings loader is a cited source of the starter catalogue, so its
    # key list gains the two TLS identity fields only with the next catalogue
    # re-anchor. Until then they are applied through ProviderSettings' own
    # validation, and every other key through the loader's.
    identity_fields = {key: provider[key] for key in ("tls_server_name", "tls_pinned_sha256") if key in provider}
    try:
        parsed = settings_loader.runtime_settings_from_mapping({"version": 1, "models": {"providers": [
            {key: item for key, item in provider.items() if key not in identity_fields}]}})
        if any(type(item) is not str for item in identity_fields.values()):
            refuse("provider_binding_settings_invalid")
        settings = replace(parsed.models.providers[0], **identity_fields)
    except (runtime_settings.SettingsError, EndpointError, ValueError, TypeError):
        refuse("provider_binding_settings_invalid")
    if (settings.kind != "custom" or not settings.enabled or "generation" not in settings.purposes
            or not settings.endpoint.startswith("https://") or settings.tls_verification == "skip"):
        refuse("provider_binding_requires_verified_https")
    if settings.model != model:
        refuse("provider_binding_model_mismatch")
    if value["producer_family"] != family:
        refuse("provider_binding_family_mismatch")
    anchor = value["trust_anchor_sha256"]
    if settings.tls_verification == "ca_file":
        committed_bytes(repository, revision, settings.tls_ca_file, anchor, "provider_binding_trust_anchor_invalid")
    elif anchor is not None:
        refuse("provider_binding_trust_anchor_invalid")
    reference = value["credential_reference"]
    if type(reference) is not str or not re.fullmatch(r"[a-z][a-z0-9-]{0,63}", reference):
        refuse("provider_binding_credential_reference_invalid")
    panel_digest = digest(read_file(repository / PANEL_PATH, MAX_PLAN_BYTES))
    panel_raw = committed_bytes(repository, revision, PANEL_PATH, panel_digest, "review_panel_not_committed")
    if family not in strict_json(panel_raw)["families"]:
        # The review panel refuses an unknown producer family, so generation does too.
        refuse("producer_family_outside_review_vocabulary")
    identity = {"provider_id": settings.provider_id, "endpoint": settings.endpoint, "model": settings.model}
    evidence = committed_record(repository, revision, value["family_evidence"], FAMILY_EVIDENCE_TYPE,
                                "family_evidence_invalid")
    if {key: evidence.get(key) for key in identity} != identity or evidence.get("family") != family:
        refuse("family_evidence_not_for_this_binding")
    capacity = committed_record(repository, revision, value["capacity"], CAPACITY_TYPE, "capacity_record_invalid")
    if {key: capacity.get(key) for key in identity} != identity:
        refuse("capacity_record_not_for_this_binding")
    try:
        capability = ModelOutputCapability(
            capacity["maximum_output_tokens"],
            f"{CAPACITY_TYPE} {value['capacity']['path']} sha256:{value['capacity']['sha256'][:16]}",
            endpoint=settings.endpoint, observed_at=capacity["observed_at"])
    except (KeyError, ValueError, TypeError):
        refuse("capacity_record_invalid")
    if capability.declared_maximum is None:
        # Refused here, before any credential is read or provider built.
        refuse("output_capacity_unknown")
    return ProviderBinding(value["binding_id"], path, expected_digest, settings, capability, family, anchor,
                           value["family_evidence"]["sha256"], value["capacity"]["sha256"], panel_digest, reference)


def operator_credential(reference):
    """Resolve an operator credential reference in this process only; never printed or stored."""
    from tools import operator_credentials
    return operator_credentials.resolve(reference)


def binding_provider_spec(repository, binding, credential_resolver):
    """Build the isolated ProviderSpec for a binding with the credential resolved just now."""
    try:
        key = credential_resolver(binding.credential_reference)
    except Exception:  # noqa: BLE001 - keyring and helper failures are reported by a stable code only
        refuse("provider_credential_unavailable")
    if type(key) is not str or not key:
        refuse("provider_credential_unavailable")
    settings = binding.settings
    if settings.tls_ca_file:
        settings = replace(settings, tls_ca_file=str(plain_path(repository / settings.tls_ca_file)))
    try:
        endpoint = replace(settings.custom_endpoint(key), output_capability=binding.capability)
    except (EndpointError, runtime_settings.SettingsError, ValueError):
        refuse("provider_binding_settings_invalid")
    return replace(provider_spec_from_endpoint(endpoint), credential_ref="operator:" + binding.credential_reference)


def admit_draft(text):
    """Admit one model answer through the existing deterministic admission Loop.

    Returns the typed admission result and its secret-free record. Strict JSON
    is tried first; the only permitted repair removes one exact enclosing
    Markdown JSON fence, and the record names it with its transformation.
    """
    result = admit_model_response_as_loop(ModelResponseAdmissionRequest(
        text, DRAFT_ADMISSION.contract_ref, DRAFT_ADMISSION.content_digest, DRAFT_SCHEMA, DRAFT_ADMISSION.policy))
    return result, {"admitted": result.admitted, "strategy": result.strategy, "failure_code": result.failure_code,
                    "transformation_trace": list(result.transformation_trace),
                    "normalized_sha256": result.normalized_digest,
                    "schema_errors": list(result.schema_errors)}


def parse_blocks(body, method):
    """Read one original_native_file_blocks/v1 answer strictly.

    Returns the canonical draft value that the exact draft parser reads. Only
    blank lines may stand outside the header and the FILE blocks. Inside a
    block every line is content, verbatim, until that block's own END line.
    """
    planned = {row["path"] for row in method["files"]}
    lines = body.split("\n")
    index, header, files, found = 0, {}, [], set()
    while index < len(lines) and not lines[index].strip():
        index += 1
    if index == len(lines) or lines[index] != DRAFT_BEGIN:
        refuse("draft_blocks_header_invalid")
    index += 1
    ended = False
    while index < len(lines):
        line = lines[index]
        index += 1
        if not line.strip():
            continue
        if line == DRAFT_END:
            ended = True
            break
        opening = FILE_BEGIN.fullmatch(line)
        if opening is None:
            key, separator, value = line.partition(": ")
            if not files and separator and key in HEADER_KEYS and key not in header:
                header[key] = value
                continue
            refuse("draft_content_outside_blocks")
        path = opening.group("path")
        try:
            placement_path(path)
        except ValueError:
            refuse("draft_path_unsafe")
        if path in found:
            refuse("draft_path_duplicate")
        if path not in planned:
            refuse("draft_path_not_planned")
        closing, content = f"<<<END FILE {path}>>>", []
        while True:
            if index == len(lines):
                refuse("draft_block_unterminated")
            line = lines[index]
            index += 1
            if line == closing:
                break
            content.append(line)
        if not "".join(content).strip():
            refuse("draft_file_empty")
        found.add(path)
        files.append({"path": path, "content": "\n".join(content) + "\n"})
    if not ended:
        refuse("draft_blocks_end_missing")
    if any(line.strip() for line in lines[index:]):
        refuse("draft_content_after_end")
    if header != {"record_type": BLOCKS_TYPE, "method_id": method["id"]}:
        refuse("draft_blocks_header_invalid")
    if found != planned:
        refuse("draft_missing_planned_files")
    return {"record_type": DRAFT_TYPE, "method_id": method["id"], "files": files}


def parse_blocks_v2(body, method):
    """Read one original_native_file_blocks/v2 answer strictly.

    A block opens with ``<<<path>>>`` or ``<<<FILE path>>>`` for a planned
    path and closes with ``<<<END path>>>`` or ``<<<END FILE path>>>``, or
    right before the next planned file or the END DRAFT line; each omitted
    end is returned as a note. Inside a block any other marker-shaped line is
    refused, so a file cannot silently absorb another. Outside blocks only
    blank lines and the two header lines may appear.
    """
    planned = {row["path"] for row in method["files"]}
    lines = body.split("\n")
    index, header, files, found, notes = 0, {}, [], set(), []
    while index < len(lines) and not lines[index].strip():
        index += 1
    if index == len(lines) or lines[index] != DRAFT_BEGIN:
        refuse("draft_blocks_header_invalid")
    index += 1

    def opened(line):
        """The path a FILE line names, or None when the line is not one."""
        if not MARKER_LINE.fullmatch(line) or line == DRAFT_BEGIN or line.startswith("<<<END "):
            return None
        return line[3:-3].removeprefix("FILE ")

    open_path, content, ended = None, [], False
    while index < len(lines):
        line = lines[index]
        index += 1
        if open_path is not None:
            follows = opened(line)
            if line in (f"<<<END {open_path}>>>", f"<<<END FILE {open_path}>>>"):
                closing = "explicit"
            elif line == DRAFT_END or (follows in planned and follows not in found and follows != open_path):
                closing = "omitted"
            elif MARKER_LINE.fullmatch(line):
                refuse("draft_path_duplicate" if follows in found or follows == open_path
                       else "draft_marker_misplaced")
            else:
                content.append(line)
                continue
            if not "".join(content).strip():
                refuse("draft_file_empty")
            files.append({"path": open_path, "content": "\n".join(content) + "\n"})
            found.add(open_path)
            if closing == "omitted":
                notes.append("block_end_omitted:" + open_path)
            open_path, content = None, []
            if line == DRAFT_END:
                ended = True
                break
            if closing == "explicit":
                continue
        if not line.strip():
            continue
        if line == DRAFT_END:
            ended = True
            break
        path = opened(line)
        if path is None:
            key, separator, value = line.partition(": ")
            if not files and open_path is None and separator and key in HEADER_KEYS and key not in header:
                header[key] = value
                continue
            refuse("draft_marker_misplaced" if MARKER_LINE.fullmatch(line) else "draft_content_outside_blocks")
        try:
            placement_path(path)
        except ValueError:
            refuse("draft_path_unsafe")
        if path in found:
            refuse("draft_path_duplicate")
        if path not in planned:
            refuse("draft_path_not_planned")
        open_path, content = path, []
    if open_path is not None:
        refuse("draft_block_unterminated")
    if not ended:
        refuse("draft_blocks_end_missing")
    if any(line.strip() for line in lines[index:]):
        refuse("draft_content_after_end")
    if header != {"record_type": BLOCKS2_TYPE, "method_id": method["id"]}:
        refuse("draft_blocks_header_invalid")
    if found != planned:
        refuse("draft_missing_planned_files")
    return {"record_type": DRAFT_TYPE, "method_id": method["id"], "files": files}, notes


def draft_admission_binding(draft_format):
    """The admission contract a run binds for its draft format, with its digest."""
    if draft_format == "json":
        return {"contract": DRAFT_ADMISSION.to_dict(), "sha256": DRAFT_ADMISSION.content_digest}
    contract = BLOCKS2_ADMISSION if draft_format == "blocks2" else BLOCKS_ADMISSION
    return {"contract": contract, "sha256": digest(canonical(contract))}


@dataclass(frozen=True)
class BlocksAdmission:
    admitted: bool
    value: dict | None = None


def admit_blocks(text_value, method, grammar="blocks"):
    """Admit one block-format answer: strict first, then one recorded fence removal."""
    strategy, trace, body = "strict_blocks", [], text_value
    fenced = BLOCKS_FENCE.fullmatch(text_value)
    if fenced is not None:
        strategy, body = "blocks_markdown_fence_removed", fenced.group("body")
        trace = ["removed_exact_markdown_fence" + (":" + fenced.group("info") if fenced.group("info") else "")]
    try:
        if len(text_value.encode("utf-8")) > MAX_DRAFT_BYTES or secret_present(text_value):
            refuse("draft_too_large_or_secret_shaped")
        if grammar == "blocks2":
            value, notes = parse_blocks_v2(body, method)
            trace = trace + notes
        else:
            value = parse_blocks(body, method)
    except GenerationError as refusal:
        return BlocksAdmission(False), {"admitted": False, "strategy": strategy, "failure_code": str(refusal),
                                        "transformation_trace": trace, "normalized_sha256": "", "schema_errors": []}
    return BlocksAdmission(True, value), {"admitted": True, "strategy": strategy, "failure_code": "",
                                          "transformation_trace": trace,
                                          "normalized_sha256": digest(canonical(value)), "schema_errors": []}


def write_new(path, raw):
    path = plain_path(path)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def load_plan(repository, path, expected_digest):
    raw = read_file(path, MAX_PLAN_BYTES)
    if digest(raw) != expected_digest:
        refuse("plan_digest_mismatch")
    if secret_present(raw.decode("utf-8")):
        refuse("plan_contains_secret")
    plan = strict_json(raw)
    exact(plan, PLAN_FIELDS, "plan_fields_invalid")
    if plan["record_type"] != PLAN_TYPE:
        refuse("plan_version_unsupported")
    factory._validated_sources(repository, plan)
    if type(plan["methods"]) is not list or not 1 <= len(plan["methods"]) <= 5000:
        refuse("method_population_invalid")
    seen = set()
    for method in plan["methods"]:
        exact(method, METHOD_FIELDS, "method_fields_invalid")
        identity = method["id"]
        if type(identity) is not str or not factory.IDENTITY.fullmatch(identity) or len(identity) > 64 or identity in seen:
            refuse("method_identity_invalid_or_duplicate")
        seen.add(identity)
        text(method["brief"])
        text(method["opportunity"], 2000)
        if type(method["acceptance"]) is not list or not 1 <= len(method["acceptance"]) <= 20:
            refuse("acceptance_required")
        for criterion in method["acceptance"]:
            text(criterion, 2000)
        if type(method["files"]) is not list or not 2 <= len(method["files"]) <= 32:
            refuse("complete_file_plan_required")
        paths = set()
        for file in method["files"]:
            exact(file, FILE_FIELDS, "file_plan_invalid")
            text(file["role"], 64)
            text(file["media_type"], 128)
            placement_path(file["path"])
            if file["path"].casefold() in paths:
                refuse("duplicate_planned_path")
            paths.add(file["path"].casefold())
            text(file["purpose"], 2000)
        if not any(f["role"] in ("instruction_file", "skill_definition") for f in method["files"]):
            refuse("native_entrypoint_required")
        if any(not (f["media_type"].startswith("text/") or f["media_type"] in
                    ("application/json", "application/schema+json", "application/x-python")) for f in method["files"]):
            refuse("generation_supports_text_files_only")
        native._package({"body_form": "package", "files": [{"path": f["path"], "role": f["role"],
            "media_type": f["media_type"], "size_bytes": 1, "digest": "0" * 64} for f in method["files"]]},
            method["declared_effects"])
        # Reuse factory metadata validation before any paid call.
        row = {k: method[k] for k in native.NATIVE_FIELDS - {"producer", "files"}}
        row["producer"] = {"producer_identity": "validation", "family": "fixture", "method_identity": "original_native_generation/v1"}
        row["files"] = []
        normalized = native._proposal_metadata({"proposals": [row]})
        selected = {k: plan["sources"][k] for k in method["sources"] if k in plan["sources"]}
        factory._compile({"proposals": normalized["proposals"], "sources": selected},
                         plan["source_revision"], {**selected, "LICENSE": plan["license"]["sha256"]}, "MIT")
    return plan


@dataclass(frozen=True)
class GenerationRequest:
    repository: Path
    plan: Path
    plan_sha256: str
    output: Path
    model: str
    producer_family: str
    call_ceiling: int
    output_tokens: int | None = None
    token_ceiling: int | None = None
    allow_unbounded_total: bool = False
    calls_authorized: bool = False
    writes_authorized: bool = False
    retry_failed: bool = False
    timeout_seconds: float = 180.0
    #: Repository-relative path and digest of a committed provider binding;
    #: both absent selects the reviewed Ollama Cloud path.
    provider_binding: str | None = None
    provider_binding_sha256: str | None = None
    #: The draft format the model answers in: "json" or "blocks".
    draft_format: str = "json"


class ExactRequestBounds:
    """Read-only host-qualified bounds using the existing token-bound contract."""

    def __init__(self, path, expected_digest):
        raw = read_file(path, MAX_PLAN_BYTES)
        if digest(raw) != expected_digest or secret_present(raw.decode()):
            refuse("token_bound_source_invalid")
        self.source_sha256 = expected_digest
        value = strict_json(raw)
        exact(value, {"record_type", "bounds"}, "token_bound_source_invalid")
        if value["record_type"] != "original_native_generation_token_bounds/v1" or type(value["bounds"]) is not list:
            refuse("token_bound_source_invalid")
        self.bounds = {}
        for row in value["bounds"]:
            bound = ProviderTokenBound(**row)
            if bound.provider_request_digest in self.bounds:
                refuse("token_bound_duplicate")
            self.bounds[bound.provider_request_digest] = bound

    def resolve(self, request):
        return self.bounds.get(request.provider_request_digest)


def read_journal(path, method_ids):
    raw = read_file(path, MAX_JOURNAL_BYTES) if path.exists() else b""
    if raw and not raw.endswith(b"\n"):
        refuse("journal_incomplete_line")
    rows, pending, complete = [], {}, {}
    previous = ""
    for line in raw.splitlines():
        row = strict_json(line)
        exact(row, {"record_type", "sequence", "kind", "method_id", "attempt", "previous_sha256", "data"}, "journal_fields_invalid")
        if (row["record_type"] != EVENT_TYPE or row["sequence"] != len(rows) + 1
                or type(row["sequence"]) is not int or row["previous_sha256"] != previous
                or row["method_id"] not in method_ids or type(row["attempt"]) is not int or row["attempt"] < 1):
            refuse("journal_binding_invalid")
        key = (row["method_id"], row["attempt"])
        if row["kind"] == "dispatch":
            exact(row["data"], {"request_sha256", "reservation_tokens"}, "dispatch_invalid")
            reserve = row["data"]["reservation_tokens"]
            if reserve is not None and (type(reserve) is not int or reserve < 1):
                refuse("dispatch_reservation_invalid")
            if key in pending or key in complete:
                refuse("duplicate_dispatch")
            pending[key] = row
        elif row["kind"] == "complete":
            exact(row["data"], {"status", "error_code", "physical_model_calls", "input_tokens", "output_tokens",
                  "charged_tokens", "charge_basis", "gateway_model", "response_sha256", "response_saved_sha256",
                  "response_path", "proposal_path", "proposal_sha256", "prepared_path", "package_digest", "elapsed_seconds",
                  "prepared_tree_sha256", "reported_model", "attempt_provider", "provider_request_digest",
                  "response_admission"}, "completion_invalid")
            if key not in pending:
                refuse("completion_without_dispatch")
            data = row["data"]
            if data["status"] not in ("failed", "candidate_prepared", "outcome_unknown"):
                refuse("completion_status_invalid")
            admission = data["response_admission"]
            if admission is not None:
                exact(admission, {"admitted", "strategy", "failure_code", "transformation_trace", "normalized_sha256",
                                  "schema_errors"}, "completion_admission_invalid")
                if (type(admission["admitted"]) is not bool
                        or admission["strategy"] not in ("strict_json", "json_markdown_fence_removed", "strict_blocks",
                                                         "blocks_markdown_fence_removed", "unparsed")
                        or type(admission["failure_code"]) is not str
                        or type(admission["transformation_trace"]) is not list
                        or type(admission["schema_errors"]) is not list):
                    refuse("completion_admission_invalid")
            if data["status"] == "candidate_prepared" and (admission is None or admission["admitted"] is not True):
                refuse("completion_admission_invalid")
            if data["charge_basis"] not in ("reported", "reserved_remaining", "unknown"):
                refuse("completion_usage_invalid")
            for name in ("physical_model_calls", "input_tokens", "output_tokens", "charged_tokens"):
                if data[name] is not None and (type(data[name]) is not int or data[name] < 0):
                    refuse("completion_usage_invalid")
            if data["charge_basis"] == "reported" and (data["input_tokens"] is None or data["output_tokens"] is None
                    or data["charged_tokens"] != data["input_tokens"] + data["output_tokens"]):
                refuse("completion_usage_invalid")
            reserved = pending[key]["data"]["reservation_tokens"]
            if ((data["charge_basis"] == "reserved_remaining" and (reserved is None or data["charged_tokens"] != reserved))
                    or (data["charge_basis"] == "unknown" and (reserved is not None or data["charged_tokens"] is not None))):
                refuse("completion_reservation_invalid")
            for name in ("response_path", "proposal_path", "prepared_path"):
                if data[name]:
                    placement_path(data[name])
            pending.pop(key)
            complete[key] = row
        else:
            refuse("journal_event_unknown")
        rows.append(row)
        previous = digest(canonical(row))
    return rows, pending, complete


def append_event(path, rows, kind, method_id, attempt, data):
    row = {"record_type": EVENT_TYPE, "sequence": len(rows) + 1, "kind": kind, "method_id": method_id,
           "attempt": attempt, "previous_sha256": digest(canonical(rows[-1])) if rows else "", "data": data}
    raw = canonical(row) + b"\n"
    fd = os.open(plain_path(path), os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    rows.append(row)


def parse_draft(raw, method, plan, producer):
    if len(raw) > MAX_DRAFT_BYTES or secret_present(raw.decode("utf-8")):
        refuse("draft_too_large_or_secret_shaped")
    value = strict_json(raw)
    exact(value, {"record_type", "method_id", "files"}, "draft_fields_invalid")
    if value["record_type"] != DRAFT_TYPE or value["method_id"] != method["id"] or type(value["files"]) is not list:
        refuse("draft_identity_invalid")
    planned = {row["path"]: row for row in method["files"]}
    files, found = [], set()
    for row in value["files"]:
        exact(row, {"path", "content"}, "draft_file_fields_invalid")
        path = row["path"]
        if type(path) is not str or path not in planned or path in found:
            refuse("draft_path_not_planned")
        found.add(path)
        content = text(row["content"], MAX_DRAFT_BYTES).encode()
        file = planned[path]
        files.append({"path": path, "role": file["role"], "media_type": file["media_type"],
                      "digest": digest(content), "size_bytes": len(content), "content_base64": base64.b64encode(content).decode()})
    if found != set(planned):
        refuse("draft_missing_planned_files")
    proposal = {k: method[k] for k in native.NATIVE_FIELDS - {"files", "producer"}}
    proposal.update(files=files, producer=producer)
    native._files(files, proposal["declared_effects"])
    return {"record_type": factory.NATIVE_INPUT_TYPE, "source_revision": plan["source_revision"],
            "license": plan["license"], "sources": {k: plan["sources"][k] for k in proposal["sources"]},
            "proposals": [proposal]}


def prepared_tree_digest(root):
    """Bind all factory outputs, including metadata, specifications and reports."""
    root = plain_path(root)
    inventory, directories, total, entries = {}, [root], 0, 0
    while directories:
        with os.scandir(directories.pop()) as stream:
            for entry in stream:
                entries += 1
                if entries > 1024:
                    refuse("prepared_tree_too_large")
                path = plain_path(Path(entry.path))
                relative = path.relative_to(root).as_posix()
                if entry.is_dir(follow_symlinks=False):
                    inventory[relative] = {"kind": "directory"}
                    directories.append(path)
                else:
                    raw = read_file(path, MAX_PLAN_BYTES)
                    total += len(raw)
                    if total > MAX_JOURNAL_BYTES:
                        refuse("prepared_tree_too_large")
                    inventory[relative] = {"sha256": digest(raw), "size_bytes": len(raw)}
    return digest(canonical(inventory))


def verify_success(output, row):
    data = row["data"]
    if digest(read_file(output / data["proposal_path"], MAX_PLAN_BYTES)) != data["proposal_sha256"]:
        refuse("saved_proposal_changed")
    prepared = plain_path(output / data["prepared_path"])
    if prepared_tree_digest(prepared) != data["prepared_tree_sha256"]:
        refuse("saved_prepared_tree_changed")
    items = strict_json(read_file(prepared / "items.json", MAX_PLAN_BYTES))
    if items["record_type"] != native.NATIVE_ITEMS or len(items["items"]) != 1:
        refuse("saved_candidates_changed")
    for item in items["items"]:
        package = CataloguePackage.from_dict(item["package"])
        if (package.package_digest != data["package_digest"] or item["reference"]["digest"] != data["package_digest"]
                or item["reference"]["identity"] != row["method_id"]):
            refuse("saved_package_binding_changed")
        native._verify_tree(prepared, item, package)


def implementation_digests(spec, extra=()):
    adapter = spec.adapter if inspect.ismodule(spec.adapter) or inspect.isclass(spec.adapter) else type(spec.adapter)
    try:
        paths = (Path(__file__), Path(native.__file__), Path(factory.__file__),
                 Path(inspect.getfile(PromptResourceBundle)),
                 Path(inspect.getfile(ModelGateway)), Path(inspect.getfile(adapter)),
                 Path(inspect.getfile(admit_model_response_as_loop)), *extra)
    except (TypeError, OSError):
        refuse("implementation_source_unavailable")
    result = {}
    for path in paths:
        if path.name in result:
            refuse("implementation_identity_collision")
        result[path.name] = digest(read_file(path, MAX_PLAN_BYTES))
    return result


def generate(request, *, gateway=None, provider_spec=None, token_bound_resolver=None, fixture_run=False,
             credential_resolver=None):
    if request.calls_authorized is not True or request.writes_authorized is not True:
        refuse("generation_authority_required")
    if type(request.call_ceiling) is not int or request.call_ceiling < 1:
        refuse("call_ceiling_invalid")
    if request.token_ceiling is None:
        if request.allow_unbounded_total is not True:
            refuse("explicit_total_budget_mode_required")
    elif type(request.token_ceiling) is not int or request.token_ceiling < 1 or request.allow_unbounded_total:
        refuse("token_ceiling_invalid")
    if gateway is not None and fixture_run is not True:
        refuse("injected_gateway_requires_fixture_marker")
    bound = request.provider_binding is not None or request.provider_binding_sha256 is not None
    if bound and provider_spec is not None:
        refuse("provider_binding_excludes_injected_provider")
    if fixture_run and (gateway is None or (provider_spec is None and not bound)):
        refuse("fixture_requires_injected_gateway_and_provider")
    if request.draft_format not in DRAFT_FORMATS:
        refuse("draft_format_unsupported")
    form = DRAFT_FORMATS[request.draft_format]
    text(request.model, 128)
    if secret_present(request.model):
        refuse("model_identity_contains_secret")
    if type(request.producer_family) is not str or not re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", request.producer_family):
        refuse("producer_family_invalid")
    repository = plain_path(request.repository)
    plan = load_plan(repository, request.plan, request.plan_sha256)
    binding = None
    family_source_digest = "fixture"
    if bound:
        # A custom producer is bound by its own committed evidence, never by
        # adding an unqualified reviewer installation to the review panel.
        binding = load_provider_binding(repository, plan["source_revision"], request.provider_binding,
                                        request.provider_binding_sha256, request.model, request.producer_family)
        family_source_digest = binding.family_evidence_sha256
    elif not fixture_run:
        family_path = PANEL_PATH
        family_raw = read_file(repository / family_path, MAX_PLAN_BYTES)
        family_source_digest = digest(family_raw)
        factory._checked_source(repository, plan["source_revision"], family_path, family_source_digest)
        installations = strict_json(family_raw)["installations"]
        families = {row["family"] for row in installations if row["model"] == request.model
                    and row["engine_kind"] == "model_gateway" and row["settings"].get("provider_id") == "ollama_cloud"}
        if families != {request.producer_family}:
            refuse("producer_family_not_bound_to_registered_model")
    if binding is None:
        spec = provider_spec or next(p for p in builtin_provider_specs() if p.provider_id == "ollama_cloud")
        if not fixture_run:
            require_provider_credential(spec)
    system, prompt_binding = load_prompt_resource(request.draft_format)
    if binding is not None:
        # The credential is resolved in this process immediately before the
        # provider is built, and only after every committed input was checked.
        spec = binding_provider_spec(repository, binding, credential_resolver or operator_credential)
    capability = spec.output_capability_for(request.model)
    maximum = capability.declared_maximum
    if maximum is None:
        refuse("output_capacity_unknown")
    allocation = None
    if request.output_tokens is not None:
        allocation = ModelOutputAllocation(capability, spec.provider_id, request.model, "original_native_generation",
                                          request.output_tokens, "original_native_generation_plan/v1#run",
                                          "The operator explicitly allocated this output allowance for complete candidate files.")
        maximum = allocation.requested_tokens
    route = screen_route(ModelRoute("original_native_generation", spec.provider_id, request.model,
                                   spec.locality, purposes=("generation",)), purpose="generation")
    if request.token_ceiling is not None and token_bound_resolver is None:
        refuse("token_bound_resolver_required")
    active_gateway = gateway or ModelGateway(providers=(spec,), routes=(route,), token_bound_resolver=token_bound_resolver)
    output = plain_path(request.output)
    if not output.exists():
        output.mkdir(mode=0o700)
    if not output.is_dir():
        refuse("output_not_directory")
    lock_fd = os.open(output / ".lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            refuse("generation_already_running")
        config = {"record_type": RUN_TYPE, "journal_record_type": EVENT_TYPE, "plan_sha256": request.plan_sha256,
                  "source_revision": plan["source_revision"], "model": request.model,
                  "provider": spec.provider_id, "producer_family": request.producer_family,
                  "family_source_sha256": family_source_digest,
                  "call_ceiling": request.call_ceiling, "token_ceiling": request.token_ceiling,
                  "timeout_seconds": request.timeout_seconds,
                  "output_tokens": maximum, "capacity": capability.summary(), "fixture_run": fixture_run,
                  "token_bounds_source": getattr(token_bound_resolver, "source_sha256", "host-injected")
                      if token_bound_resolver is not None else None,
                  "provider_binding": binding.summary() if binding is not None else None,
                  "draft_format": {"name": request.draft_format, "record_type": form["record_type"]},
                  "draft_admission": draft_admission_binding(request.draft_format),
                  "implementations": implementation_digests(spec, (
                      Path(runtime_settings.__file__), Path(settings_loader.__file__)) if binding is not None else ()),
                  "prompt_resource": prompt_binding}
        meta = output / "run.json"
        if meta.exists():
            if strict_json(read_file(meta, MAX_PLAN_BYTES)) != config:
                refuse("resume_binding_changed")
        else:
            if {p.name for p in output.iterdir()} != {".lock"}:
                refuse("new_run_directory_not_empty")
            write_new(meta, canonical(config) + b"\n")
        journal = output / "journal.jsonl"
        rows, pending, completed = read_journal(journal, {m["id"] for m in plan["methods"]})
        for row in completed.values():
            data = row["data"]
            if digest(read_file(output / data["response_path"], MAX_DRAFT_BYTES)) != data["response_saved_sha256"]:
                refuse("saved_response_changed")
        successful = {key[0]: row for key, row in completed.items() if row["data"]["status"] == "candidate_prepared"}
        for row in successful.values():
            verify_success(output, row)
        unresolved = pending or any(r["data"]["status"] == "outcome_unknown" for r in completed.values())
        stop = "interrupted_dispatch_needs_reconciliation" if unresolved else "completed"
        producer = {"producer_identity": ("fixture:" if fixture_run else "") + f"{spec.provider_id}:{request.model}",
                    "family": request.producer_family,
                    "method_identity": "original_native_generation_fixture/v1" if fixture_run else "original_native_generation/v1"}
        for method in ([] if unresolved else plan["methods"]):
            identity = method["id"]
            previous = [row for key, row in completed.items() if key[0] == identity]
            if identity in successful or (previous and not request.retry_failed):
                continue
            used_calls = sum(max(1, row["data"]["physical_model_calls"] or 1) for row in completed.values())
            used_tokens = sum(row["data"]["charged_tokens"] or 0 for row in rows if row["kind"] == "complete")
            if used_calls >= request.call_ceiling:
                stop = "call_ceiling_reached"
                break
            remaining = request.token_ceiling - used_tokens if request.token_ceiling is not None else None
            if remaining is not None and remaining <= 0:
                stop = "token_ceiling_reached"
                break
            # Check frozen source material again before each provider call.
            load_plan(repository, request.plan, request.plan_sha256)
            attempt = 1 + max([key[1] for key in completed if key[0] == identity], default=0)
            prompt = canonical({"method": method, "source_revision": plan["source_revision"],
                                "draft_record_type": form["record_type"]}).decode()
            call = ModelGatewayRequest(prompt, ModelGatewayConfig(
                purpose="generation", route_names=(route.name,), allowed_models=(request.model,),
                allow_failover=False, max_route_attempts=1, output_allocation=allocation,
                max_total_tokens=remaining, timeout_seconds=request.timeout_seconds),
                system=system, temperature=0.0, output_contract=form["record_type"])
            attempt_folder = output / f"{identity}.attempt-{attempt}"
            attempt_folder.mkdir(mode=0o700)
            append_event(journal, rows, "dispatch", identity, attempt,
                         {"request_sha256": call.request_digest, "reservation_tokens": remaining})
            result = None
            error_code = ""
            started = time.monotonic()
            try:
                result = active_gateway.invoke(call)
            except Exception:  # noqa: BLE001 - unknown provider outcomes are recorded without private exception text
                error_code = "gateway_outcome_unknown"
            elapsed_seconds = round(time.monotonic() - started, 6)
            wire_text_valid = True
            try:
                raw = (result.text if result else "").encode("utf-8")
            except UnicodeError:
                raw = result.text.encode("utf-8", errors="replace")
                wire_text_valid = False
            safe_raw = redacted(raw[:MAX_DRAFT_BYTES].decode("utf-8", errors="replace")).encode()
            response_path = attempt_folder / "response.txt"
            write_new(response_path, safe_raw)
            physical = result.physical_model_calls if result else None
            attempts = result.physical_provider_attempts if result else ()
            last_attempt = attempts[-1] if attempts else None
            reported_model = last_attempt.model if last_attempt and type(last_attempt.model) is str else ""
            input_tokens = result.input_tokens if result else None
            output_tokens = result.output_tokens if result else None
            input_tokens = input_tokens if type(input_tokens) is int and input_tokens >= 0 else None
            output_tokens = output_tokens if type(output_tokens) is int and output_tokens >= 0 else None
            complete_usage = type(input_tokens) is int and type(output_tokens) is int and input_tokens >= 0 and output_tokens >= 0
            charge = input_tokens + output_tokens if complete_usage else remaining
            proposal_path, prepared_path = "", ""
            admission_record = None
            proposal_digest, package_digest, prepared_digest = "", "", ""
            status = "failed" if result is not None else "outcome_unknown"
            if result is not None:
                error_code = result.error_code or ""
                if error_code and (type(error_code) is not str or not re.fullmatch(r"[a-z][a-z0-9_]{0,127}", error_code)):
                    error_code = "unrecognized_gateway_error"
                if result.ok and (result.model != request.model or result.provider != spec.provider_id or reported_model != request.model):
                    error_code = "model_identity_mismatch"
                elif not wire_text_valid:
                    error_code = "model_output_invalid_utf8"
                elif result.ok and physical != 1:
                    error_code = "physical_call_contract_mismatch"
                elif remaining is not None and charge is not None and charge > remaining:
                    error_code = "token_bound_exceeded"
                elif result.ok:
                    if request.draft_format in ("blocks", "blocks2"):
                        admitted, admission_record = admit_blocks(raw.decode("utf-8"), method, request.draft_format)
                    else:
                        admitted, admission_record = admit_draft(raw.decode("utf-8"))
                    try:
                        if not admitted.admitted:
                            refuse("draft_json_not_admitted" if request.draft_format == "json"
                                   else "draft_blocks_not_admitted")
                        proposal = parse_draft(canonical(admitted.value), method, plan, producer)
                        package, _bodies = native._files(proposal["proposals"][0]["files"], method["declared_effects"])
                        package_digest = package.package_digest
                        if any(row["data"]["package_digest"] == package_digest for row in successful.values()):
                            refuse("duplicate_generated_package")
                        proposal_file = attempt_folder / "proposals.json"
                        proposal_raw = canonical(proposal) + b"\n"
                        write_new(proposal_file, proposal_raw)
                        prepared = attempt_folder / "candidates"
                        factory.prepare(factory.PreparationRequest(repository, proposal_file, prepared, True))
                        prepared_digest = prepared_tree_digest(prepared)
                        proposal_path, prepared_path = proposal_file.relative_to(output).as_posix(), prepared.relative_to(output).as_posix()
                        proposal_digest = digest(proposal_raw)
                        status = "candidate_prepared"
                    except (GenerationError, factory.PreparationError, ValueError, KeyError, TypeError, UnicodeError) as refusal:
                        error_code = (str(refusal) if str(refusal) in ("draft_json_not_admitted", "draft_blocks_not_admitted")
                                      else "candidate_draft_or_factory_refused")
            data = {"status": status, "error_code": "" if status == "candidate_prepared" else error_code or "provider_failed", "physical_model_calls": physical,
                    "input_tokens": input_tokens, "output_tokens": output_tokens, "charged_tokens": charge,
                    "charge_basis": "reported" if complete_usage else ("reserved_remaining" if remaining is not None else "unknown"),
                    "gateway_model": redacted(result.model) if result and type(result.model) is str else "", "response_sha256": digest(raw),
                    "response_saved_sha256": digest(safe_raw), "response_path": response_path.relative_to(output).as_posix(),
                    "proposal_path": proposal_path, "proposal_sha256": proposal_digest, "prepared_path": prepared_path,
                    "package_digest": package_digest, "elapsed_seconds": elapsed_seconds,
                    "prepared_tree_sha256": prepared_digest, "reported_model": redacted(reported_model),
                    "attempt_provider": last_attempt.provider if last_attempt else "",
                    "provider_request_digest": last_attempt.provider_request_digest if last_attempt else "",
                    "response_admission": admission_record}
            append_event(journal, rows, "complete", identity, attempt, data)
            completed[(identity, attempt)] = rows[-1]
            if status == "candidate_prepared":
                successful[identity] = rows[-1]
            if (result is None or physical is None or physical > 1 or
                    (remaining is not None and (not complete_usage or charge > remaining))):
                stop = "unknown_or_exceeded_accounting"
                break
            if error_code in STOP_ERROR_CODES:
                stop = error_code
                break
        cursor = {"record_type": "original_native_generation_cursor/v1", "plan_sha256": request.plan_sha256,
                  "last_event_sha256": digest(canonical(rows[-1])) if rows else "", "stop_reason": stop,
                  "distinct_methods_prepared": sorted(successful), "candidate_count": len(successful),
                  "dispatches": sum(r["kind"] == "dispatch" for r in rows), "approval_count": 0,
                  "fixture_run": fixture_run, "strict_total_token_ceiling": request.token_ceiling,
                  "usage_complete": not pending and all(r["data"]["charge_basis"] == "reported" for r in rows if r["kind"] == "complete"),
                  "physical_model_calls_reported": None if pending or any(r["data"]["physical_model_calls"] is None for r in completed.values())
                      else sum(r["data"]["physical_model_calls"] for r in completed.values()),
                  "cost_state": "unknown", "interrupted_dispatches": len(pending)}
        _atomic_write(plain_path(output / "cursor.json"), canonical(cursor) + b"\n")
        return cursor
    finally:
        os.close(lock_fd)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--plan-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--family", required=True)
    parser.add_argument("--max-calls", type=int, required=True)
    parser.add_argument("--output-tokens", type=int)
    parser.add_argument("--token-ceiling", type=int)
    parser.add_argument("--allow-unbounded-total", action="store_true")
    parser.add_argument("--token-bounds", type=Path)
    parser.add_argument("--token-bounds-sha256")
    parser.add_argument("--authorize-model-calls", action="store_true")
    parser.add_argument("--authorize-writes", action="store_true")
    parser.add_argument("--retry-failed", action="store_true")
    parser.add_argument("--provider-binding",
                        help="repository-relative path of a committed provider binding")
    parser.add_argument("--provider-binding-sha256")
    parser.add_argument("--draft-format", choices=sorted(DRAFT_FORMATS), default="json",
                        help="the answer format: json drafts, or delimited file blocks (blocks is version 1, "
                             "blocks2 is version 2)")
    parser.add_argument("--timeout-seconds", type=float, default=180.0,
                        help="per-request timeout; bound in run.json")
    args = parser.parse_args(argv)
    try:
        resolver = ExactRequestBounds(args.token_bounds, args.token_bounds_sha256) if args.token_bounds else None
        request = GenerationRequest(args.repository, args.plan, args.plan_sha256, args.output, args.model,
                                    args.family, args.max_calls, args.output_tokens, args.token_ceiling,
                                    args.allow_unbounded_total, args.authorize_model_calls, args.authorize_writes,
                                    args.retry_failed, timeout_seconds=args.timeout_seconds,
                                    provider_binding=args.provider_binding,
                                    provider_binding_sha256=args.provider_binding_sha256,
                                    draft_format=args.draft_format)
        print(json.dumps(generate(request, token_bound_resolver=resolver), indent=2))
        return 0
    except (GenerationError, factory.PreparationError, ValueError, OSError) as error:
        print(json.dumps({"record_type": "original_native_generation_refusal/v1", "error_type": type(error).__name__,
                          "code": str(error) if isinstance(error, GenerationError) else "preflight_or_io_refused"}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
