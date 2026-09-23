"""Bounded native package checks; unsupported components are held, never silently skipped."""
from __future__ import annotations

import ast
import re
import sys
from dataclasses import dataclass
from pathlib import PurePosixPath

import jsonschema
import yaml

from .native import NATIVE_PROFILE, NativePackageReviewRequest, json_document
from .prechecks import result_of
from .prechecks.duplicates import ExactShingleJaccard
from .prechecks.effects import EffectRules
from .prechecks.minhash import DatasketchMinHash
from .prechecks.safety_rules import StaticSafetyRules
from .prechecks.secrets import SecretPatterns
from .records import CandidateReviewError, refuse

VERSION = "1"
PYTHON_MEDIA = frozenset({"text/x-python", "application/x-python"})
EXECUTABLE = frozenset({"skill_script", "executable_tool", "hook"})
SUPPORTED_ROLES = frozenset({"instruction_file", "skill_definition", "skill_script", "skill_reference",
                             "skill_asset", "executable_tool", "configuration", "other"})
SUPPORTED_STYLES = frozenset({"codex", "claude", "claude_code", "opencode", "pi", "gemini"})
INSTRUCTION_ENTRYPOINTS = {"codex": {"AGENTS.md"}, "claude": {"CLAUDE.md"}, "claude_code": {"CLAUDE.md"},
                         "opencode": {"AGENTS.md"}, "pi": {"AGENTS.md"}, "gemini": {"GEMINI.md"}}
PASSIVE_ROOTS = frozenset({"examples", "verification", "references", "assets", "contracts"})
ACTIVATION_DIRECTORIES = frozenset({".claude", ".claude-plugin", ".cursor", ".cursor-plugin", ".codex",
                                    ".agents", ".opencode", ".pi", ".gemini", ".github", ".cline",
                                    ".clinerules", "hooks", "plugins", "agents", "commands"})
ACTIVATION_NAMES = frozenset({"opencode.json", "opencode.jsonc", "plugin.json", "marketplace.json", ".mcp.json",
                              "mcp.json", "mcp-config.json", "settings.json", "settings.local.json", "hooks.json",
                              "gemini-extension.json", "agents.md", "agents.override.md", "claude.md",
                              "claude.local.md", "gemini.md", "skill.md"})
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+[^)]*)?\)")
IMPORT = re.compile(r"(?m)^\s*@([^\s]+)\s*$")
PYTHON_DEPENDENCY = re.compile(r"^python(?:3)?(?:[>=~!].*)?$", re.IGNORECASE)
STANDARD_MODULES = getattr(sys, "stdlib_module_names", frozenset({"json", "sys", "math", "re", "csv", "collections"}))


@dataclass(frozen=True)
class MaterialView:
    body: bytes
    item: dict
    identity: str
    cited_sources: tuple = ()

    @property
    def body_text_lenient(self):
        return self.body.decode("utf-8", "replace")


class NativeCheck:
    kind = ""
    engine_id = ""
    version = VERSION

    def __init__(self, settings, policy):
        if settings:
            refuse("invalid_precheck_settings", "this native check takes no configurable exceptions")
        self.policy = policy

    def availability(self):
        return True, "", self.version

    def check(self, request, context):
        if not isinstance(request, NativePackageReviewRequest) or request.review_profile != NATIVE_PROFILE:
            findings = [("native_review_profile_mismatch", "a native check requires the versioned native request")]
        else:
            findings = self.findings(request, context)
        return result_of(self.kind, self.engine_id, self.version, findings)


def qualified_placement(file):
    """Reject role/path contradictions before interpreting content; placement never grants an effect."""
    parts = PurePosixPath(file.entry.path).parts
    folded = tuple(part.casefold() for part in parts)
    role = file.entry.role
    if role == "instruction_file" and file.entry.path in {"AGENTS.md", "CLAUDE.md", "GEMINI.md"}:
        return []
    if role == "skill_definition" and file.entry.path == "SKILL.md":
        return []
    if any(part in ACTIVATION_DIRECTORIES for part in folded[:-1]) or folded[-1] in ACTIVATION_NAMES:
        return [("native_activation_path_unqualified", "a reserved native activation path lacks a qualified component binding")]
    if (role in {"other", "skill_reference", "skill_asset", "configuration"} and file.entry.path != "LICENSE"
            and (len(parts) < 2 or parts[0] not in PASSIVE_ROOTS)):
        return [("native_passive_location_unqualified", "supporting resources must stay within profile-owned passive locations")]
    return []


class NativeLicenceRules(NativeCheck):
    kind, engine_id = "licence", "native_licence_rules"

    def findings(self, request, context):
        licence = request.item["reference"]["license"]
        if licence not in self.policy.accepted_licences or licence != "MIT":
            return [("native_licence_unsettled", "the original package licence is not accepted")]
        sources = {source.path: source.text for source in request.cited_sources}
        if not sources.get("LICENSE", "").startswith("MIT License\n"):
            return [("native_licence_unsettled", "the original package lacks the pinned MIT licence source")]
        return []


def _local_resources(file, request):
    paths = {entry.path for entry in request.package.files}
    findings = []
    for target in LINK.findall(file.text or "") + IMPORT.findall(file.text or ""):
        if target.startswith(("https://", "http://", "#", "mailto:")):
            continue
        pure = PurePosixPath(target.split("#", 1)[0])
        combined = (PurePosixPath(file.entry.path).parent / pure).as_posix()
        if pure.is_absolute() or ".." in pure.parts or combined not in paths:
            findings.append(("native_resource_missing", "a declared local resource is missing or escapes the package"))
    return findings


def _skill(file):
    text = file.text or ""
    parts = text.split("---", 2)
    if len(parts) != 3 or parts[0].strip() or not parts[2].strip():
        return [("native_skill_frontmatter_invalid", "a native skill needs bounded YAML metadata and a body")]
    try:
        tree = yaml.compose(parts[1])
        keys = [key.value for key, _value in tree.value] if isinstance(tree, yaml.MappingNode) else []
        header = yaml.safe_load(parts[1])
        if len(set(keys)) != len(keys) or type(header) is not dict:
            raise ValueError("invalid mapping")
    except (ValueError, yaml.YAMLError, RecursionError):
        return [("native_skill_frontmatter_invalid", "skill metadata must be a unique mapping")]
    name, description = header.get("name"), header.get("description")
    if (type(name) is not str or re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name) is None or len(name) > 64
            or type(description) is not str or not description.strip() or len(description) > 1024
            or set(header) - {"name", "description", "license", "compatibility", "metadata"}):
        return [("native_skill_frontmatter_invalid", "skill metadata is missing, malformed or outside this native profile")]
    if PurePosixPath(file.entry.path).name != "SKILL.md":
        return [("native_skill_frontmatter_invalid", "a skill definition must use its native entry filename")]
    return []


def _schema(file):
    try:
        value = json_document(file.payload)
        if type(value) is not dict or value.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            return [("native_required_component_unqualified", "configuration is not a supported JSON Schema contract")]
        jsonschema.Draft202012Validator.check_schema(value)
        pending = [value]
        while pending:
            item = pending.pop()
            if isinstance(item, dict):
                for reference_keyword in ("$ref", "$dynamicRef"):
                    if reference_keyword in item and (
                            not isinstance(item[reference_keyword], str)
                            or not item[reference_keyword].startswith("#")):
                        return [("native_external_schema_refused", "this profile accepts self-contained schema references only")]
                pending.extend(item.values())
            elif isinstance(item, list):
                pending.extend(item)
    except (CandidateReviewError, jsonschema.SchemaError, RecursionError):
        return [("native_schema_invalid", "the declared JSON Schema contract is invalid")]
    return []


def python_findings(file, request):
    try:
        tree = ast.parse(file.text or "", filename=file.entry.path)
    except (SyntaxError, ValueError, RecursionError):
        return [("native_python_syntax_invalid", "a declared Python tool does not parse")]
    findings = []
    dependencies = request.dependencies
    if not any(PYTHON_DEPENDENCY.fullmatch(value) for value in dependencies):
        findings.append(("native_dependency_unresolved", "Python execution needs a declared Python dependency"))
    local = {PurePosixPath(entry.path).stem for entry in request.package.files if entry.media_type in PYTHON_MEDIA}
    declared = {re.split(r"[<>=!~\[]", value, 1)[0].replace("-", "_") for value in dependencies}
    for part in ast.walk(tree):
        if isinstance(part, (ast.Import, ast.ImportFrom)):
            names = [name.name.split(".")[0] for name in part.names] if isinstance(part, ast.Import) else [part.module or ""]
            for name in names:
                root = name.split(".")[0]
                if root not in STANDARD_MODULES and root not in local and root not in declared:
                    findings.append(("native_dependency_unresolved", "an imported module has no declared dependency or bundled source"))
        if isinstance(part, ast.Call):
            name = part.func.id if isinstance(part.func, ast.Name) else part.func.attr if isinstance(part.func, ast.Attribute) else ""
            if name in {"eval", "exec", "__import__", "import_module"} or (name == "compile" and isinstance(part.func, ast.Name)):
                findings.append(("native_dynamic_execution_refused", "dynamic code evaluation is outside this static profile"))
    return findings


class NativeFormatRules(NativeCheck):
    kind, engine_id = "format", "native_format_rules"
    version = "2"

    def findings(self, request, context):
        findings, entrypoints = [], 0
        styles = request.item["reference"]["styles"]
        if not styles or any(style not in SUPPORTED_STYLES for style in styles):
            findings.append(("native_required_component_unqualified", "the package needs supported explicit client styles"))
        for file in request.files:
            role, media, text = file.entry.role, file.entry.media_type, file.text
            findings.extend(qualified_placement(file))
            if role not in SUPPORTED_ROLES:
                findings.append(("native_required_component_unqualified", "a required component has no validator in this profile"))
            if text is None:
                findings.append(("native_binary_verification_missing", "binary material needs an independent asset verification profile"))
                continue
            if media in PYTHON_MEDIA and role not in EXECUTABLE:
                findings.append(("native_executable_role_mismatch", "declared Python code must use an executable file role"))
            if role in EXECUTABLE:
                if media not in PYTHON_MEDIA:
                    findings.append(("native_required_component_unqualified", "only declared Python tools have a static executable profile"))
                else:
                    findings.extend(python_findings(file, request))
            if role == "instruction_file":
                if file.entry.path not in {"AGENTS.md", "CLAUDE.md", "GEMINI.md"} or not text.strip():
                    findings.append(("native_instruction_invalid", "instructions need a qualified native root entrypoint"))
                entrypoints += 1
            if role == "skill_definition":
                findings.extend(_skill(file))
                entrypoints += 1
            if role == "configuration":
                findings.extend(_schema(file) if media in {"application/json", "application/schema+json"} else [(
                    "native_required_component_unqualified", "this configuration format is not qualified")])
            if role == "other" and file.entry.path != "LICENSE":
                if media != "application/json":
                    findings.append(("native_required_component_unqualified", "an unclassified required component cannot be ignored"))
                else:
                    try:
                        json_document(file.payload)
                    except CandidateReviewError:
                        findings.append(("native_data_json_invalid", "a supporting data file must be strict JSON"))
            if media in {"text/markdown", "text/plain"}:
                findings.extend(_local_resources(file, request))
        if not entrypoints:
            findings.append(("native_entrypoint_missing", "the package has no qualified native instruction or skill entrypoint"))
        if not any(file.entry.role == "skill_definition" for file in request.files):
            supplied = {file.entry.path for file in request.files if file.entry.role == "instruction_file"}
            for style in styles:
                if style in INSTRUCTION_ENTRYPOINTS and not (supplied & INSTRUCTION_ENTRYPOINTS[style]):
                    findings.append(("native_required_component_unqualified", "a declared client has no matching instruction entrypoint"))
        return findings


class NativeSafetyRules(NativeCheck):
    kind, engine_id = "safety", "native_safety_rules"

    def findings(self, request, context):
        engine = StaticSafetyRules({}, self.policy)
        findings = []
        for file in request.files:
            result = engine.check(MaterialView(file.payload, request.item, request.identity), context)
            findings.extend((finding.code, f"{file.entry.path}: {finding.detail}") for finding in result.findings)
        return findings


class NativeEffectsRules(NativeCheck):
    kind, engine_id = "effects", "native_effects_rules"

    def findings(self, request, context):
        effects = request.item["reference"]["declared_effects"]
        common = EffectRules({}, self.policy).check(MaterialView(request.duplicate_material, request.item, request.identity), context)
        findings = [(finding.code, finding.detail) for finding in common.findings]
        if any(file.entry.role in EXECUTABLE for file in request.files) and "spawns_process" not in effects:
            findings.append(("native_process_effect_missing", "executable files require the declared process effect"))
        for file in request.files:
            if file.entry.media_type not in PYTHON_MEDIA:
                continue
            try:
                tree = ast.parse(file.text or "")
            except (SyntaxError, ValueError, RecursionError):
                continue  # The format engine records the syntax refusal.
            aliases = {}
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    aliases.update((part.asname or part.name.split(".")[0], part.name) for part in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    aliases.update((part.asname or part.name, node.module + "." + part.name) for part in node.names)
            needed = set()
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                parts, target = [], node.func
                while isinstance(target, ast.Attribute):
                    parts.insert(0, target.attr)
                    target = target.value
                if isinstance(target, ast.Name):
                    parts.insert(0, aliases.get(target.id, target.id))
                qualified = ".".join(parts)
                name = parts[-1] if parts else ""
                if isinstance(target, ast.Name) and target.id in aliases and qualified.startswith(
                        ("requests.", "httpx.", "socket.", "urllib.request.", "http.client.")):
                    needed.add("network")
                if name in {"open", "read_text", "read_bytes", "listdir", "scandir"}:
                    needed.add("reads_fs")
                if name in {"write_text", "write_bytes", "unlink", "mkdir"}:
                    needed.add("writes_fs")
                if name == "open" and len(node.args) > 1 and isinstance(node.args[1], ast.Constant) \
                        and isinstance(node.args[1].value, str) and any(value in node.args[1].value for value in "wax+"):
                    needed.add("writes_fs")
            findings.extend(("native_effect_undeclared", f"a tool operation requires the declared {effect} effect")
                            for effect in sorted(needed - set(effects)))
        return findings


class NativeSecretRules(NativeCheck):
    kind, engine_id = "secrets", "native_secret_rules"

    def __init__(self, settings, policy):
        self.inner, self.policy = SecretPatterns(settings, policy), policy

    def findings(self, request, context):
        findings = []
        for file in request.files:
            result = self.inner.check(MaterialView(file.payload, request.item, request.identity, request.cited_sources), context)
            findings.extend((finding.code, f"{file.entry.path}: {finding.detail}") for finding in result.findings)
        return findings


class NativeDuplicateRules(NativeCheck):
    kind, engine_id = "duplicates", "native_duplicate_rules"

    def __init__(self, settings, policy):
        self.inner, self.policy = ExactShingleJaccard(settings, policy), policy

    def findings(self, request, context):
        result = self.inner.check(MaterialView(request.duplicate_material, request.item, request.identity), context)
        return [(finding.code, finding.detail) for finding in result.findings]


class NativeMinHashRules(NativeDuplicateRules):
    engine_id = "native_minhash_rules"

    def __init__(self, settings, policy):
        self.inner, self.policy = DatasketchMinHash(settings, policy), policy

    def availability(self):
        return self.inner.availability()
