"""Executable pre-checks for wave 5 harness candidate packages. Candidate evidence only.

Effects: reads package folders, the read-only repository checkouts and the Agent Skills
validator environments; starts local processes (git, the validators, package tests,
hook samples and protocol servers) inside a Bubblewrap sandbox with no network; writes
only package.json (the fill command), new report files under a package's review/
folder or the wave's reports/ folder, and new proposal documents that do not exist
yet. It makes no network call and no model call, reads no secret and approves nothing.

Usage (Python 3.11 or later for the checker itself):

    python3 check_package.py fill PACKAGE_DIR
    python3 check_package.py check PACKAGE_DIR [--skip-runs]
    python3 check_package.py check-all [--skip-runs]
    python3 check_package.py emit-proposals --output NEW_FILE

A pass means the listed deterministic checks found nothing to refuse. It is not an
approval, a rights decision, a native loading result or a usefulness claim.
"""
from __future__ import annotations

import argparse
import ast
import base64
import datetime as _dt
import hashlib
import json
import os
import re
import select
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unicodedata
from pathlib import Path, PurePosixPath

WAVE = Path(__file__).resolve().parent
PACKAGES = WAVE / "packages"
REPORTS = WAVE / "reports"
REPO = Path("/home/username/loop-engine")
MAIN_CHECKOUT = Path("/home/username/loop-engine-main")
PINNED_REVISION = "a1fc74321912cb9e7d0af7dc5d0ecee24c7081f4"
LICENSE_SHA256 = "663e093e45c8440e61d1dd5e5db8181eb1f305402aad1e91ce3765408b7a46ea"
VALIDATORS = (
    ("agentskills_pypi_0_1_1", Path("/home/username/.le-ci-tmp/research/compilers/validator/.venv-pypi/bin/agentskills")),
    ("skills_ref_official_git", Path("/home/username/.le-ci-tmp/research/compilers/validator/.venv-official/bin/skills-ref")),
)
PYTHONS = (
    ("python3.14", Path("/usr/bin/python3")),
    ("python3.10", Path("/home/username/.local/share/uv/python/cpython-3.10.20-linux-x86_64-gnu/bin/python3.10")),
)
BWRAP = shutil.which("bwrap")
RECORD_TYPE = "wave5_candidate_package/v1"
REPORT_TYPE = "wave5_precheck_report/v1"
ALL_REPORT_TYPE = "wave5_precheck_all_report/v1"
PROPOSALS_TYPE = "harness_candidate_batch_proposals/v2"

# Contracts of the repository, imported from the read-only main checkout when it is
# importable. The literal fallbacks equal origin/main at PINNED_REVISION.
sys.path.insert(0, str(MAIN_CHECKOUT / "src"))
try:  # noqa: SIM105
    from loop_engine.core.facets import EFFECTS  # type: ignore
    from loop_engine.core.intelligence_tagging import TAG_DIMENSIONS  # type: ignore
    from loop_engine.core.model_call_records import default_secret_patterns  # type: ignore
    from loop_engine.core.service_runtime.catalogue_packages import (  # type: ignore
        FILE_ROLES, CataloguePackage, CataloguePackageFile)
    CONTRACT_SOURCE = "imported from /home/username/loop-engine-main/src"
except Exception:  # pragma: no cover - fallback keeps the checker usable
    EFFECTS = ("pure", "reads_fs", "writes_fs", "reads_secret", "network", "spawns_process")
    TAG_DIMENSIONS = ("role", "domain", "geography", "language", "data_sensitivity", "authentication", "lifecycle")
    FILE_ROLES = ("instruction_file", "skill_definition", "skill_script", "skill_reference", "skill_asset",
                  "subagent_definition", "command", "hook", "protocol_server_configuration", "plugin_manifest",
                  "executable_tool", "configuration", "other")
    CataloguePackage = CataloguePackageFile = None

    def default_secret_patterns():
        return (r"sk-[A-Za-z0-9]{20,}", r"AKIA[0-9A-Z]{16}", r"ghp_[A-Za-z0-9]{20,}", r"xox[bap]-[A-Za-z0-9-]{10,}",
                r"api_key\s*=\s*[\"'][A-Za-z0-9_\-]{16,}[\"']", r"password\s*=\s*[\"'][^\"']{8,}[\"']",
                r"Bearer [A-Za-z0-9_\-\.]{20,}")
    CONTRACT_SOURCE = "literal fallback of origin/main contracts"

# The panel's extra secret shapes (tools/candidate_review/resources/panel.json at origin/main).
EXTRA_SECRET_PATTERNS = (r"sk_(?:live|test)_[A-Za-z0-9]{16,}", r"github_pat_[A-Za-z0-9_]{20,}",
                         r"AIza[0-9A-Za-z_\-]{35}",
                         r"eyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}",
                         r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
SECRET_PATTERNS = tuple(re.compile(pattern) for pattern in (*default_secret_patterns(), *EXTRA_SECRET_PATTERNS))

# Safety rules restated from tools/candidate_review/prechecks/safety_rules.py (builtin_static_rules v1).
SAFETY_SOURCE = "tools/candidate_review/prechecks/safety_rules.py"
INVISIBLE_RANGES = ((0x200B, 0x200F), (0x202A, 0x202E), (0x2060, 0x2064), (0x2066, 0x2069), (0xFEFF, 0xFEFF),
                    (0xE0000, 0xE007F))
SAFETY_RULES = (
    ("hidden_comment", re.compile(r"<!--")),
    ("instruction_override", re.compile(
        r"(?i)\b(?:ignore|disregard|forget|override)\b[^.\n]{0,40}\b(?:previous|prior|above|earlier|all|any)\b"
        r"[^.\n]{0,20}\b(?:instructions?|prompts?|rules?|guidelines?)\b")),
    ("instruction_override", re.compile(
        r"(?i)\b(?:approve this (?:item|skill|file)|mark (?:it|this) (?:as )?approved|you are now in)\b")),
    ("pipe_to_shell", re.compile(r"(?i)\b(?:curl|wget|fetch|iwr|invoke-webrequest)\b[^\n|]*\|\s*(?:sudo\s+)?"
                                 r"(?:ba|z|k|c|da|fi)?sh\b")),
    ("encoded_execution", re.compile(r"(?i)(?:base64\s+(?:-d|--decode)[^\n]*\|\s*(?:sudo\s+)?(?:ba|z)?sh\b"
                                     r"|\beval\s+[\"']?\$\((?:curl|wget)\b)")),
    ("destructive_command", re.compile(r"(?i)(?:\brm\s+-[a-z]*r[a-z]*\s+(?:/|~|\$HOME)(?:\s|$|\*)"
                                       r"|\bmkfs(?:\.[a-z0-9]+)?\s+/dev/|\bdd\s+if=[^\n]*\bof=/dev/(?:sd|nvme|hd))")),
    ("credential_access", re.compile(r"(?i)(?:~/\.ssh/|\bid_(?:rsa|ed25519|ecdsa)\b|\.aws/credentials\b"
                                     r"|\.netrc\b|/etc/shadow\b|\.docker/config\.json\b|\.kube/config\b)")),
)
# Internal runtime vocabulary refused in customer material (builtin_format_rules forbidden_patterns).
FORBIDDEN_VOCABULARY = tuple(re.compile(pattern, re.IGNORECASE) for pattern in (
    r"(?<![a-z0-9])loops?(?![a-z0-9])", r"(?<![a-z0-9])practitioners?(?![a-z0-9])", r"role[\s_-]+profiles?",
    r"runtime[\s_-]+classification", r"solution[\s_-]+canvas", r"code[\s_-]+nodes?",
    r"(?<![a-z0-9])spawn(?:s|ed|ing)?(?![a-z0-9])", r"starting[\s_-]+(?:solution|intelligence)(?![a-z0-9])",
    r"run[\s_-]+history", r"runtime[\s_-]+(?:memory|history)", r"(?:context|code|solution|feedback)[\s_-]+intelligence",
    r"intelligence[\s_-]+(?:items?|quer(?:y|ies)|layers?)", r"(?<![a-z0-9])(?:grand)?child(?:ren)?(?![a-z0-9])",
    r"[—–―−]", r"stop[\s_-]+conditions?", r"(?<![a-z0-9])receipts?(?![a-z0-9])",
    r"(?<![a-z0-9])chronicles?(?![a-z0-9])", r"what[\s_-]*is[\s_-]*next|what[\s_-]+next|whats[\s_-]*next"))

IDENTITY = re.compile(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*\Z")
NATIVE_NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
SEGMENT = re.compile(r"[A-Za-z0-9._@+-]{1,100}\Z")
MEDIA_TYPE = re.compile(r"[a-z0-9][a-z0-9!#$&^_.+-]{0,62}/[a-z0-9][a-z0-9!#$&^_.+-]{0,126}\Z")
DIGEST = re.compile(r"[0-9a-f]{64}\Z")
REVISION = re.compile(r"[0-9a-f]{40}\Z")
SPEC_FAMILY = re.compile(r"[a-z][a-z0-9_]*\Z")
METHOD_IDENTITY = re.compile(r"[a-z][a-z0-9_.-]*(?:/[a-z0-9_.-]+)*/v[1-9][0-9]*\Z")
SEMVER = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\Z")
PLACEHOLDER = re.compile(r"\{\{([A-Z][A-Z0-9_]*)\}\}")
PYTHON_DEPENDENCY = re.compile(r"^python(?:3)?(?:[>=~!].*)?$", re.IGNORECASE)
WORD = re.compile(r"[A-Za-z0-9]")
SHELL_FENCE = re.compile(r"^```[ \t]*(?:bash|sh|shell|console|zsh|fish|powershell|pwsh|cmd|bat)\b",
                         re.IGNORECASE | re.MULTILINE)

LAYERS = ("context", "code", "runtime_history_solution", "user_feedback")
KINDS = ("skill", "tool", "instruction_file")
PROPOSAL_FIELDS = {"id", "title", "purpose", "sources", "layer", "family", "search_tags", "tags", "symbols",
                   "declared_effects", "kind", "styles", "dependencies", "producer", "files"}
FILE_FIELDS = {"path", "digest", "size_bytes", "media_type", "role"}
WAVE5_FIELDS = {"assignment_id", "file_class", "use_cases", "harness_targets", "unverified_targets", "not_placed",
                "native_name", "version", "entrypoints", "placements", "file_extensions", "render_placeholders",
                "tests", "hooks", "servers", "first_action", "done_when", "stop_and_report_when",
                "source_revision", "source_digests", "package_digest", "review_note", "state", "approval_state"}
FILE_CLASSES = ("skill_with_scripts_and_tests", "verifier_package", "hook_with_script", "subagent_definition",
                "command_file", "protocol_server_config_local", "rules_file", "task_packet", "plugin_bundle",
                "settings_fragment", "root_instruction_fragment")
USE_CASES = ("overnight_tickets_on_a_local_model", "data_cleanup_without_an_expensive_model",
             "competition_solve_task_to_submission", "any_focused_step")
HARNESSES = ("claude_code", "codex", "opencode", "pi", "gemini_cli", "cursor", "copilot", "goose", "kimi_cli",
             "cline")
REVIEW_STYLE = {"claude_code": "claude_code", "codex": "codex", "opencode": "opencode", "pi": "pi",
                "gemini_cli": "gemini"}
OPERATIONS = ("copy_exact_bytes", "merge_json_object", "merge_toml_table", "compose_instruction_section",
              "plugin_directory_binding")
PICKUPS = ("native_discovery", "composed_instruction", "explicit_invocation", "registered_event",
           "launch_binding", "referenced_resource", "licence_notice")
EXECUTABLE_ROLES = ("skill_script", "hook", "executable_tool")
GROUNDING_SOURCE = "src/loop_engine/core/service_runtime/catalogue_packages.py"
PLACEHOLDER_CLASSES = ("task_packet", "root_instruction_fragment")
#: file class -> (proposal kind, proposal layer, proposal family)
CLASS_RULES = {
    "skill_with_scripts_and_tests": ("skill", "code", "native_skill_with_scripts"),
    "verifier_package": ("skill", "code", "native_verifier"),
    "hook_with_script": ("tool", "code", "native_hook"),
    "subagent_definition": ("instruction_file", "context", "native_subagent"),
    "command_file": ("instruction_file", "context", "native_command"),
    "protocol_server_config_local": ("tool", "code", "native_protocol_server"),
    "rules_file": ("instruction_file", "context", "native_rules_file"),
    "task_packet": ("instruction_file", "context", "native_task_packet"),
    "plugin_bundle": ("tool", "code", "native_plugin"),
    "settings_fragment": ("tool", "context", "native_settings_fragment"),
    "root_instruction_fragment": ("instruction_file", "context", "native_instruction_fragment"),
}
MEDIA_BY_SUFFIX = {".py": ("text/x-python",), ".md": ("text/markdown",), ".mdc": ("text/markdown",),
                   ".json": ("application/json", "application/schema+json"), ".toml": ("application/toml",),
                   ".yaml": ("application/yaml",), ".yml": ("application/yaml",), ".txt": ("text/plain",),
                   ".csv": ("text/csv",), ".tsv": ("text/tab-separated-values",)}
FORBIDDEN_NAMES = {"__pycache__", ".pytest_cache", ".venv", "venv", "node_modules", ".git", ".mypy_cache",
                   ".ruff_cache", ".DS_Store"}
FORBIDDEN_SUFFIXES = (".pyc", ".pyo", ".log", ".key", ".pem", ".p12", ".pfx", ".sqlite", ".db")
MAX_FILES, HARD_MAX_FILES = 32, 64
MAX_FILE_BYTES, HARD_MAX_FILE_BYTES = 64 * 1024, 256 * 1024
MAX_PACKAGE_BYTES, HARD_MAX_PACKAGE_BYTES = 512 * 1024, 2 * 1024 * 1024
SKILL_KEYS = {"name", "description", "license", "compatibility", "metadata"}
CANDIDATE_SENTENCE = "Candidate only. Not approved, staged, served or published."
REVIEW_HEADINGS = ("## Method", "## Authoring basis and sources", "## Inputs and outputs", "## Effects",
                   "## Closest existing items", "## Positive example", "## Known-wrong example",
                   "## Harness placement and verification state", "## Customer requests", "## Limits")
ENTRY_SHAPES = {
    "skill": (("## When to use it", "## First action", "## Steps", "## Checks", "## Done when",
               "## Stop and report when", "## Known-wrong example"), 120, 450),
    "packet_entry": (("## Assignment", "## First action", "## Steps", "## Done when", "## Stop and report when",
                      "## Files", "## Authority"), 150, 450),
    "node_context": (("## Objective", "## Relevant context", "## Current state", "## Contracts and input",
                      "## Acceptance"), 80, 450),
    "checklist": (("## Before work", "## Before handoff"), 30, 250),
    "fragment": (("## Applies when", "## Rules", "## If a rule blocks the work"), 80, 350),
    "companion": (("## What is active", "## If something is refused"), 40, 180),
    "subagent": (("## Job", "## Inputs", "## Steps", "## Return format", "## Refuse when"), 80, 350),
    "command": (("## Purpose", "## First action", "## Steps", "## Output", "## Stop and report when"), 60, 350),
    "rule": (("## Rule", "## Applies to", "## Instead", "## Stop and report when"), 40, 250),
}
NETWORK_MODULES = {"socket", "ssl", "http", "urllib", "urllib3", "requests", "httpx", "aiohttp", "websockets",
                   "websocket", "ftplib", "smtplib", "poplib", "imaplib", "telnetlib", "xmlrpc", "socketserver",
                   "paramiko", "pycurl"}
SHELL_NETWORK = re.compile(r"(?i)(?:^|[\s;&|(`])(?:curl|wget|nc|ncat|ssh|scp|rsync|ftp|telnet)\s|"
                           r"\b(?:pip|pip3|uv|npm|pnpm|yarn|bun|cargo|go|gem|brew|apt|apt-get)\s+(?:install|add|get)\b|"
                           r"\bgit\s+(?:clone|fetch|pull|push|remote\s+add)\b|\bnpx\s|\bhttps?://")
READ_CALLS = {"read_text", "read_bytes", "listdir", "scandir", "glob", "iglob", "rglob", "iterdir"}
READ_CALLS_ON_MODULE = {"walk": ("os",)}
WRITE_CALLS = {"write_text", "write_bytes", "unlink", "mkdir", "makedirs", "rmdir", "rmtree", "copy2", "copyfile",
               "copytree", "touch", "mkstemp", "mkdtemp", "NamedTemporaryFile", "TemporaryDirectory",
               "TemporaryFile", "SpooledTemporaryFile", "symlink_to", "hardlink_to"}
#: Names that are also ordinary methods (str.replace, list.remove, dict.copy) count only on these modules.
WRITE_CALLS_ON_MODULE = {"copy": ("shutil",), "move": ("shutil",), "replace": ("os",), "rename": ("os",),
                         "remove": ("os",), "chmod": ("os",), "truncate": ("os",)}
PROCESS_CALLS = {"run", "Popen", "call", "check_call", "check_output", "system", "popen", "execv", "execve",
                 "execvp", "execl", "spawnv", "spawnl", "startfile"}
SECRET_ENV = re.compile(r"(?i)(key|token|secret|password|passwd|credential)")


def now_stamp() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def word_count(text: str) -> int:
    return sum(1 for token in text.split() if WORD.search(token))


class Report:
    def __init__(self) -> None:
        self.results: list[dict] = []

    def add(self, check: str, status: str, findings=()) -> None:
        self.results.append({"check": check, "status": status,
                             "findings": [str(finding)[:600] for finding in findings][:60]})

    def outcome(self, check: str, refusals, warnings=()) -> None:
        refusals, warnings = list(refusals), list(warnings)
        if refusals:
            self.add(check, "refused", refusals + [f"warning: {item}" for item in warnings])
        elif warnings:
            self.add(check, "warning", warnings)
        else:
            self.add(check, "passed")

    @property
    def refused(self) -> bool:
        return any(result["status"] == "refused" for result in self.results)


def strict_json(data: bytes):
    def pairs(items):
        seen = {}
        for key, value in items:
            if key in seen:
                raise ValueError(f"duplicate key {key!r}")
            seen[key] = value
        return seen

    def constant(name):
        raise ValueError(f"nonstandard constant {name}")

    return json.loads(data.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant)


def split_front_matter(text: str):
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError("front matter is not closed by a line of three dashes")
    return text[4:end + 1], text[end + 5:]


def yaml_mapping(text: str) -> dict:
    import yaml  # PyYAML is installed for the system interpreter

    class UniqueKeyLoader(yaml.SafeLoader):
        pass

    def construct(loader, node, deep=False):
        keys = [loader.construct_object(key, deep=deep) for key, _ in node.value]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate key in YAML mapping")
        return loader.construct_mapping(node, deep=deep)

    UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct)
    value = yaml.load(text, Loader=UniqueKeyLoader)
    if not isinstance(value, dict):
        raise ValueError("front matter is not one mapping")
    return value


def cursor_front_matter(text: str) -> dict:
    """Cursor .mdc front matter is key: value lines; glob values are not YAML."""
    values = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        key, separator, value = line.partition(":")
        if not separator or key.strip() in values:
            raise ValueError("each .mdc front matter line is one distinct key: value pair")
        values[key.strip()] = value.strip()
    if set(values) - {"description", "globs", "alwaysApply"}:
        raise ValueError(f"unexpected .mdc keys {sorted(set(values) - {'description', 'globs', 'alwaysApply'})}")
    if values.get("alwaysApply", "false") not in ("true", "false"):
        raise ValueError("alwaysApply is true or false")
    return values


def git_bytes(revision: str, path: str) -> bytes | None:
    result = subprocess.run(["git", "-C", str(REPO), "show", f"{revision}:{path}"], capture_output=True, timeout=60)
    return result.stdout if result.returncode == 0 else None


def placement_problem(value: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 200 or value.startswith(("/", "~")) or value.endswith("/"):
        return "a path is relative, nonempty, at most 200 characters and names a file"
    parts = value.split("/")
    if len(parts) > 8:
        return "a path has at most 8 segments"
    for part in parts:
        if not SEGMENT.fullmatch(part) or part in (".", "..") or part.casefold() == ".git":
            return f"unsafe path segment {part!r}"
    return ""


def load_package(folder: Path):
    manifest = strict_json((folder / "package.json").read_bytes())
    return manifest, manifest.get("proposal", {}), manifest.get("wave5", {})


def payload_files(folder: Path) -> dict[str, Path]:
    root = folder / "payload"
    files = {}
    for current, directories, names in os.walk(root, followlinks=False):
        for name in directories + names:
            path = Path(current) / name
            if path.is_symlink():
                raise ValueError(f"symbolic link refused: {path.relative_to(folder)}")
        for name in names:
            path = Path(current) / name
            files[path.relative_to(root).as_posix()] = path
    return files


def existing_identities() -> set[str]:
    path = WAVE / "existing-identities.txt"
    return {line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}


def canonical_package_digest(entries: list[dict]) -> str:
    if CataloguePackage is not None:
        package = CataloguePackage(tuple(CataloguePackageFile.from_dict(entry) for entry in entries), "package")
        return package.package_digest
    ordered = sorted(entries, key=lambda entry: entry["path"])
    document = json.dumps({"record_type": "catalogue_package/v1", "files": ordered}, sort_keys=True,
                          separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return sha256(document)


# ---------------------------------------------------------------------------
# fill
# ---------------------------------------------------------------------------

def command_fill(folder: Path) -> int:
    folder = folder.resolve()
    manifest, proposal, wave5 = load_package(folder)
    files = payload_files(folder)
    declared = {entry.get("path") for entry in proposal.get("files", [])}
    if declared != set(files):
        print(json.dumps({"fill": "refused", "undeclared_payload_files": sorted(set(files) - declared),
                          "declared_but_missing": sorted(declared - set(files))}, indent=1))
        return 1
    for entry in proposal["files"]:
        data = files[entry["path"]].read_bytes()
        entry["digest"], entry["size_bytes"] = sha256(data), len(data)
    proposal["files"] = sorted(proposal["files"], key=lambda entry: entry["path"])
    wave5["package_digest"] = canonical_package_digest([dict(entry) for entry in proposal["files"]])
    temporary = folder / "package.json.tmp"
    temporary.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(folder / "package.json")
    print(json.dumps({"fill": "done", "files": len(files), "package_digest": wave5["package_digest"]}))
    return 0


# ---------------------------------------------------------------------------
# check
# ---------------------------------------------------------------------------

def check_layout(folder: Path, report: Report) -> None:
    refusals = []
    for required in ("package.json", "payload", "review/REVIEW-NOTE.md"):
        if not (folder / required).exists():
            refusals.append(f"missing {required}")
    for current, directories, names in os.walk(folder, followlinks=False):
        relative_dir = Path(current).relative_to(folder)
        for name in directories + names:
            path = Path(current) / name
            relative = (relative_dir / name).as_posix()
            if path.is_symlink():
                refusals.append(f"symbolic link {relative}")
            elif name in FORBIDDEN_NAMES or name.endswith(FORBIDDEN_SUFFIXES):
                refusals.append(f"generated, cache or secret-like name {relative}")
        for name in names:
            path = Path(current) / name
            relative = (relative_dir / name).as_posix()
            if not path.is_symlink() and not path.is_file():
                refusals.append(f"not a regular file {relative}")
            elif path.is_file() and path.stat().st_size == 0:
                refusals.append(f"empty file {relative}")
    top = {child.name for child in folder.iterdir()}
    extra = top - {"package.json", "payload", "review"}
    if extra:
        refusals.append(f"unexpected top-level entries {sorted(extra)}")
    report.outcome("layout", refusals)


def check_manifest(folder: Path, manifest: dict, proposal: dict, wave5: dict, report: Report) -> None:
    refusals, warnings = [], []
    if manifest.get("record_type") != RECORD_TYPE or set(manifest) != {"record_type", "proposal", "wave5"}:
        refusals.append(f"package.json must be {RECORD_TYPE} with exactly record_type, proposal and wave5")
    if set(proposal) != PROPOSAL_FIELDS:
        refusals.append(f"proposal fields differ: missing {sorted(PROPOSAL_FIELDS - set(proposal))}, "
                        f"extra {sorted(set(proposal) - PROPOSAL_FIELDS)}")
    if set(wave5) != WAVE5_FIELDS:
        refusals.append(f"wave5 fields differ: missing {sorted(WAVE5_FIELDS - set(wave5))}, "
                        f"extra {sorted(set(wave5) - WAVE5_FIELDS)}")
    if refusals:
        report.outcome("manifest_schema", refusals)
        return

    def one_line(value, name, limit):
        if not isinstance(value, str) or not value.strip() or len(value) > limit or "\n" in value \
                or any(ord(character) < 32 for character in value):
            refusals.append(f"{name} is one nonempty line of at most {limit} characters")

    one_line(proposal["title"], "title", 160)
    one_line(proposal["purpose"], "purpose", 1024)
    if isinstance(proposal["purpose"], str) and len(proposal["purpose"]) > 300:
        warnings.append("purpose is longer than 300 characters; search cards read short purposes best")
    if proposal["layer"] not in LAYERS:
        refusals.append(f"layer is one of {LAYERS}")
    if not isinstance(proposal["family"], str) or not SPEC_FAMILY.fullmatch(proposal["family"]):
        refusals.append("family is lower-case letters, digits and underscores")

    def string_list(value, name, maximum, may_be_empty=True):
        if not isinstance(value, list) or len(value) > maximum or (not value and not may_be_empty) \
                or any(not isinstance(item, str) or not item.strip() or len(item) > 160 for item in value) \
                or len(set(value)) != len(value):
            refusals.append(f"{name} is a list of at most {maximum} distinct nonempty strings")
            return []
        return value

    string_list(proposal["search_tags"], "search_tags", 20, may_be_empty=False)
    string_list(proposal["symbols"], "symbols", 30)
    string_list(proposal["dependencies"], "dependencies", 64)
    sources = string_list(proposal["sources"], "sources", 20, may_be_empty=False)
    effects = string_list(proposal["declared_effects"], "declared_effects", 20)
    if any(effect not in EFFECTS for effect in effects) or ("pure" in effects and len(effects) > 1):
        refusals.append(f"declared_effects are drawn from {EFFECTS}; pure stands alone")
    if "network" in effects:
        refusals.append("wave 5 packages make no network use; network may not be declared")
    tags = proposal["tags"]
    if not isinstance(tags, dict) or "lifecycle" in tags or set(tags) - set(TAG_DIMENSIONS) \
            or any(not isinstance(values, list) or not values or any(not isinstance(value, str) or not value.strip()
                                                                     for value in values) for values in tags.values()):
        refusals.append(f"tags use only {TAG_DIMENSIONS} without lifecycle, each a nonempty list of strings")
    elif tags.get("language") != ["en"]:
        refusals.append("tags.language is [\"en\"]")
    if proposal["kind"] not in KINDS:
        refusals.append(f"kind is one of {KINDS}")
    styles = string_list(proposal["styles"], "styles", 20, may_be_empty=False)
    producer = proposal["producer"]
    if not isinstance(producer, dict) or set(producer) != {"producer_identity", "family", "method_identity"} \
            or any(not isinstance(value, str) or not value.strip() for value in producer.values()):
        refusals.append("producer names producer_identity, family and method_identity")
    elif not METHOD_IDENTITY.fullmatch(producer["method_identity"]) or producer["family"] != "anthropic":
        refusals.append("producer.method_identity is versioned like name/v1 and producer.family is anthropic")
    for entry in proposal["files"] if isinstance(proposal["files"], list) else []:
        if not isinstance(entry, dict) or set(entry) != FILE_FIELDS:
            refusals.append(f"every file entry names exactly {sorted(FILE_FIELDS)}")
            break
    # wave5 block
    if wave5["assignment_id"] != folder.parent.name:
        refusals.append("wave5.assignment_id equals the assignment folder name")
    if wave5["file_class"] not in FILE_CLASSES:
        refusals.append(f"wave5.file_class is one of {FILE_CLASSES}")
    use_cases = wave5["use_cases"]
    if not isinstance(use_cases, list) or not use_cases or any(value not in USE_CASES for value in use_cases):
        refusals.append(f"wave5.use_cases is a nonempty list drawn from {USE_CASES}")
    targets = wave5["harness_targets"]
    if not isinstance(targets, list) or len(targets) < 2 or any(value not in HARNESSES for value in targets) \
            or len(set(targets)) != len(targets):
        refusals.append(f"wave5.harness_targets names at least two distinct harnesses from {HARNESSES}")
        targets = []
    expected_styles = sorted({REVIEW_STYLE[target] for target in targets if target in REVIEW_STYLE})
    if expected_styles and sorted(styles) != expected_styles:
        refusals.append(f"proposal.styles must be {expected_styles}, the review-profile names of the targets")
    if not expected_styles and styles:
        warnings.append("no target is in the first native review profile; styles cannot be checked there")
    for name in ("unverified_targets", "not_placed", "render_placeholders", "file_extensions", "placements",
                 "entrypoints", "source_digests"):
        if not isinstance(wave5[name], dict):
            refusals.append(f"wave5.{name} is an object")
    if not isinstance(wave5["native_name"], str) or wave5["native_name"] != str(proposal["id"]).replace("_", "-"):
        refusals.append("wave5.native_name is the identity with underscores replaced by hyphens")
    if not isinstance(wave5["version"], str) or not SEMVER.fullmatch(wave5["version"]):
        refusals.append("wave5.version is a semantic version such as 0.1.0")
    one_line(wave5["first_action"], "wave5.first_action", 300)
    for name in ("done_when", "stop_and_report_when"):
        value = wave5[name]
        if not isinstance(value, list) or not value or any(not isinstance(item, str) or not item.strip() for item in value):
            refusals.append(f"wave5.{name} is a nonempty list of short sentences")
    if not isinstance(wave5["tests"], (dict, type(None))):
        refusals.append("wave5.tests is an object or null")
    for name in ("hooks", "servers"):
        if not isinstance(wave5[name], list):
            refusals.append(f"wave5.{name} is a list")
    if wave5["state"] != "candidate_only" or wave5["approval_state"] != "none":
        refusals.append("wave5.state is candidate_only and wave5.approval_state is none")
    if wave5["review_note"] != "review/REVIEW-NOTE.md":
        refusals.append("wave5.review_note is review/REVIEW-NOTE.md")
    # sources pinned at the revision
    revision = wave5["source_revision"]
    if not isinstance(revision, str) or not REVISION.fullmatch(revision):
        refusals.append("wave5.source_revision is a full 40-character revision")
    else:
        if revision != PINNED_REVISION:
            warnings.append(f"source revision differs from the wave's pinned {PINNED_REVISION}")
        if isinstance(wave5["source_digests"], dict) and set(wave5["source_digests"]) != set(sources):
            refusals.append("wave5.source_digests names exactly the proposal sources")
        for path in sources:
            if path == "LICENSE":
                refusals.append("LICENSE is not an item source")
                continue
            data = git_bytes(revision, path)
            if data is None:
                refusals.append(f"source {path} does not exist at {revision}")
            elif isinstance(wave5["source_digests"], dict) and wave5["source_digests"].get(path) != sha256(data):
                refusals.append(f"source digest of {path} differs from its bytes at the revision")
    file_class = wave5["file_class"]
    if file_class in CLASS_RULES:
        kind, layer, family = CLASS_RULES[file_class]
        if proposal["kind"] != kind or proposal["layer"] != layer or proposal["family"] != family:
            refusals.append(f"{file_class} packages use kind {kind}, layer {layer} and family {family}")
    if not sources or sources[0] != GROUNDING_SOURCE:
        refusals.append(f"the first source is {GROUNDING_SOURCE}, the package format this package follows")
    report.outcome("manifest_schema", refusals, warnings)


def check_identity(folder: Path, proposal: dict, report: Report) -> None:
    refusals = []
    identity = proposal.get("id")
    if not isinstance(identity, str) or len(identity) > 64 or not IDENTITY.fullmatch(identity):
        refusals.append("identity uses lower-case letters, digits and single underscores, at most 64 characters")
    elif folder.name != identity:
        refusals.append("package folder name equals the identity")
    elif identity in existing_identities():
        refusals.append(f"identity {identity} already exists in existing-identities.txt")
    native = str(identity).replace("_", "-")
    if len(native) > 64 or not NATIVE_NAME.fullmatch(native):
        refusals.append("native name is lower-case kebab case of at most 64 characters")
    report.outcome("identity", refusals)


def check_inventory(folder: Path, proposal: dict, wave5: dict, files: dict, report: Report) -> None:
    refusals, warnings = [], []
    entries = proposal.get("files") if isinstance(proposal.get("files"), list) else []
    declared = {entry.get("path"): entry for entry in entries if isinstance(entry, dict)}
    if set(declared) != set(files):
        refusals.append(f"declared files differ from payload: undeclared {sorted(set(files) - set(declared))}, "
                        f"missing {sorted(set(declared) - set(files))}")
    total = 0
    folded: dict[str, str] = {}
    for path, entry in declared.items():
        problem = placement_problem(path)
        if problem:
            refusals.append(f"{path}: {problem}")
        if path.casefold() in folded:
            refusals.append(f"{path} and {folded[path.casefold()]} differ only in letter case")
        folded[path.casefold()] = path
        if entry.get("role") not in FILE_ROLES:
            refusals.append(f"{path}: role is one of {FILE_ROLES}")
        media = entry.get("media_type")
        if not isinstance(media, str) or not MEDIA_TYPE.fullmatch(media):
            refusals.append(f"{path}: media type is a lower-case type/subtype")
        suffix = PurePosixPath(path).suffix
        expected = MEDIA_BY_SUFFIX.get(suffix)
        if PurePosixPath(path).name == "LICENSE":
            expected = ("text/plain",)
        if expected and media not in expected:
            refusals.append(f"{path}: media type for {suffix or 'LICENSE'} is one of {expected}")
        if media in ("text/csv", "text/tab-separated-values"):
            warnings.append(f"{path}: the first native review profile holds CSV or TSV bytes; prefer JSON or inline data")
        if suffix == ".py" and entry.get("role") not in EXECUTABLE_ROLES:
            refusals.append(f"{path}: Python files use an executable role {EXECUTABLE_ROLES}")
        if path not in files:
            continue
        data = files[path].read_bytes()
        total += len(data)
        if entry.get("digest") != sha256(data) or entry.get("size_bytes") != len(data):
            refusals.append(f"{path}: digest or size differs from the bytes; run the fill command")
        if len(data) > HARD_MAX_FILE_BYTES:
            refusals.append(f"{path}: {len(data)} bytes is above the hard limit {HARD_MAX_FILE_BYTES}")
        elif len(data) > MAX_FILE_BYTES:
            warnings.append(f"{path}: {len(data)} bytes is above the wave target {MAX_FILE_BYTES}")
        mode = files[path].stat().st_mode & 0o777
        declared_mode = wave5.get("file_extensions", {}).get(path, {}).get("mode") \
            if isinstance(wave5.get("file_extensions"), dict) else None
        if mode != 0o644 or declared_mode != "0644":
            refusals.append(f"{path}: payload files are mode 0644 on disk and declared as \"0644\"")
    paths = set(declared)
    for path in paths:
        parts = path.split("/")
        for index in range(1, len(parts)):
            if "/".join(parts[:index]) in paths:
                refusals.append(f"{path} lies below a file path {'/'.join(parts[:index])}")
    if len(files) > HARD_MAX_FILES:
        refusals.append(f"{len(files)} files is above the hard limit {HARD_MAX_FILES}")
    elif len(files) > MAX_FILES:
        warnings.append(f"{len(files)} files is above the wave target {MAX_FILES}")
    if total > HARD_MAX_PACKAGE_BYTES:
        refusals.append(f"package is {total} bytes, above the hard limit {HARD_MAX_PACKAGE_BYTES}")
    elif total > MAX_PACKAGE_BYTES:
        warnings.append(f"package is {total} bytes, above the wave target {MAX_PACKAGE_BYTES}")
    if "LICENSE" not in files:
        refusals.append("payload/LICENSE holds the repository MIT licence")
    elif sha256(files["LICENSE"].read_bytes()) != LICENSE_SHA256:
        refusals.append("payload/LICENSE must equal the repository LICENSE bytes at the pinned revision")
    effects = proposal.get("declared_effects", [])
    if any(entry.get("role") in EXECUTABLE_ROLES for entry in entries if isinstance(entry, dict)) \
            and "spawns_process" not in effects:
        refusals.append("a package with an executable role declares spawns_process")
    extensions = wave5.get("file_extensions") if isinstance(wave5.get("file_extensions"), dict) else {}
    if set(extensions) != set(files):
        refusals.append("wave5.file_extensions has one entry for every payload file")
    for path, extension in extensions.items():
        if not isinstance(extension, dict) or set(extension) != {"mode", "license", "pickup", "tested_by"}:
            refusals.append(f"{path}: file_extensions entry names mode, license, pickup and tested_by")
            continue
        if extension["license"] != "MIT" or extension["pickup"] not in PICKUPS \
                or not isinstance(extension["tested_by"], list):
            refusals.append(f"{path}: license is MIT, pickup is one of {PICKUPS}, tested_by is a list")
        for test in extension.get("tested_by", []):
            if test not in files:
                refusals.append(f"{path}: tested_by names a missing payload file {test}")
    digest = wave5.get("package_digest")
    try:
        computed = canonical_package_digest([dict(entry) for entry in entries])
        if digest != computed:
            refusals.append("wave5.package_digest differs from the canonical package document; run fill")
    except Exception as error:  # noqa: BLE001
        refusals.append(f"the catalogue package contract refused the file list: {error}")
    report.outcome("inventory", refusals, warnings)


def text_of(path: Path) -> str | None:
    try:
        return path.read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        return None


def check_text(files: dict, folder: Path, report: Report) -> None:
    refusals, vocabulary, safety = [], [], []
    for path, file in sorted(files.items()):
        data = file.read_bytes()
        text = text_of(file)
        if text is None:
            refusals.append(f"{path}: not UTF-8")
            continue
        if data.startswith(b"\xef\xbb\xbf"):
            refusals.append(f"{path}: byte order mark")
        if b"\r" in data:
            refusals.append(f"{path}: carriage return; use LF line endings")
        if not data.endswith(b"\n"):
            refusals.append(f"{path}: no final newline")
        controls = sorted({f"U+{ord(ch):04X}" for ch in text
                           if unicodedata.category(ch) == "Cc" and ch not in "\n\t"})
        if controls:
            refusals.append(f"{path}: control characters {controls[:6]}")
        hidden = sorted({f"U+{ord(ch):04X}" for ch in text
                         if any(low <= ord(ch) <= high for low, high in INVISIBLE_RANGES)
                         or (unicodedata.category(ch) == "Cf" and ch not in "\n\t")})
        if hidden:
            refusals.append(f"{path}: invisible characters {hidden[:6]}")
        if path == "LICENSE":
            continue
        for pattern in FORBIDDEN_VOCABULARY:
            match = pattern.search(text)
            if match:
                line = text.count("\n", 0, match.start()) + 1
                vocabulary.append(f"{path}:{line}: internal or banned wording {match.group(0)!r}")
        for code, pattern in SAFETY_RULES:
            match = pattern.search(text)
            if match:
                line = text.count("\n", 0, match.start()) + 1
                safety.append(f"{path}:{line}: {code}")
    report.outcome("text_hygiene", refusals)
    report.outcome("vocabulary", vocabulary)
    report.outcome("safety_static", safety)


def check_secrets(folder: Path, report: Report) -> None:
    refusals = []
    for current, _directories, names in os.walk(folder, followlinks=False):
        for name in names:
            path = Path(current) / name
            text = path.read_bytes().decode("utf-8", "replace")
            for number, pattern in enumerate(SECRET_PATTERNS):
                if pattern.search(text):
                    refusals.append(f"{path.relative_to(folder)}: value shaped like secret pattern {number}")
    report.outcome("secrets", refusals)


def check_parse(files: dict, declared: dict, report: Report) -> dict:
    refusals, parsed = [], {}
    try:
        import jsonschema  # noqa: F401
        from jsonschema import Draft202012Validator
    except Exception:  # pragma: no cover
        Draft202012Validator = None
    for path, file in sorted(files.items()):
        text = text_of(file)
        if text is None:
            continue
        suffix = PurePosixPath(path).suffix
        media = declared.get(path, {}).get("media_type")
        try:
            if suffix == ".json":
                value = strict_json(file.read_bytes())
                parsed[path] = value
                if media == "application/schema+json" or path.endswith(".schema.json"):
                    if not isinstance(value, dict) or value.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
                        raise ValueError("a schema declares $schema https://json-schema.org/draft/2020-12/schema")
                    if Draft202012Validator is None:
                        raise ValueError("jsonschema is not installed for the checker")
                    Draft202012Validator.check_schema(value)
                    pending = [value]
                    while pending:
                        item = pending.pop()
                        if isinstance(item, dict):
                            for key in ("$ref", "$dynamicRef"):
                                if key in item and not str(item[key]).startswith("#"):
                                    raise ValueError("schemas use local references only")
                            pending.extend(item.values())
                        elif isinstance(item, list):
                            pending.extend(item)
            elif suffix == ".toml":
                parsed[path] = tomllib.loads(text)
            elif suffix in (".yaml", ".yml"):
                parsed[path] = yaml_mapping(text)
            elif suffix == ".py":
                ast.parse(text, filename=path)
            elif suffix == ".mdc":
                front, _body = split_front_matter(text)
                if front is None:
                    raise ValueError("a Cursor rule starts with front matter")
                parsed[path] = cursor_front_matter(front)
            elif suffix == ".md":
                front, _body = split_front_matter(text)
                if front is not None:
                    parsed[path] = yaml_mapping(front)
        except Exception as error:  # noqa: BLE001
            refusals.append(f"{path}: {type(error).__name__}: {error}")
    report.outcome("parse", refusals)
    return parsed


def section_findings(label: str, path: str, text: str, shape: str) -> list[str]:
    headings, low, high = ENTRY_SHAPES[shape]
    lines = text.splitlines()
    missing = [heading for heading in headings if heading not in lines]
    findings = []
    if missing:
        findings.append(f"{path}: missing {label} sections {missing}")
    count = word_count(text)
    if not low <= count <= high:
        findings.append(f"{path}: {count} words; {label} entries hold {low} to {high} words")
    return findings


def check_entries(files: dict, declared: dict, proposal: dict, wave5: dict, parsed: dict, report: Report) -> None:
    refusals, warnings = [], []
    file_class = wave5.get("file_class")
    native = wave5.get("native_name", "")
    targets = wave5.get("harness_targets", []) if isinstance(wave5.get("harness_targets"), list) else []

    def text(path):
        return text_of(files[path]) if path in files else None

    def body(path):
        front, rest = split_front_matter(text(path))
        return rest

    if file_class in ("skill_with_scripts_and_tests", "verifier_package"):
        if "SKILL.md" not in files or declared.get("SKILL.md", {}).get("role") != "skill_definition":
            refusals.append("payload/SKILL.md with role skill_definition is the entry")
        else:
            front = parsed.get("SKILL.md") or {}
            if set(front) - SKILL_KEYS:
                refusals.append(f"SKILL.md front matter keys are drawn from {sorted(SKILL_KEYS)}")
            if front.get("name") != native or front.get("description") != proposal.get("purpose") \
                    or front.get("license") != "MIT":
                refusals.append("SKILL.md front matter: name is the native name, description is the purpose, license MIT")
            metadata = front.get("metadata")
            if not isinstance(metadata, dict) or metadata.get("version") != wave5.get("version"):
                refusals.append("SKILL.md front matter metadata.version equals wave5.version")
            refusals += section_findings("skill", "SKILL.md", body("SKILL.md"), "skill")
        if not any(path.startswith("scripts/") and path.endswith(".py") for path in files):
            refusals.append("a skill or verifier package holds at least one scripts/*.py")
        if file_class == "verifier_package" and "references/checklist.md" not in files:
            refusals.append("a verifier package holds references/checklist.md for the checks code cannot do")
    if file_class in ("task_packet", "root_instruction_fragment", "hook_with_script",
                      "protocol_server_config_local", "settings_fragment"):
        if "AGENTS.md" not in files or declared["AGENTS.md"].get("role") != "instruction_file":
            refusals.append("payload/AGENTS.md with role instruction_file is the entry")
        else:
            shape = {"task_packet": "packet_entry", "root_instruction_fragment": "fragment"}.get(file_class, "companion")
            refusals += section_findings(shape.replace("_", " "), "AGENTS.md", text("AGENTS.md"), shape)
        if "claude_code" in targets and file_class in ("task_packet", "root_instruction_fragment"):
            if text("CLAUDE.md") != "@AGENTS.md\n":
                refusals.append("CLAUDE.md holds exactly the import line @AGENTS.md")
        if "gemini_cli" in targets and file_class in ("task_packet", "root_instruction_fragment"):
            if "GEMINI.md" not in files or files["GEMINI.md"].read_bytes() != files.get("AGENTS.md", Path("/dev/null")).read_bytes():
                refusals.append("GEMINI.md is a byte copy of AGENTS.md when gemini_cli is a target")
    if file_class == "task_packet":
        for path, shape in (("references/node_context.md", "node_context"), ("references/checklist.md", "checklist")):
            if path not in files:
                refusals.append(f"a task packet holds {path}")
            else:
                refusals += section_findings(shape.replace("_", " "), path, text(path), shape)
        for path in ("contracts/task.json", "contracts/input.schema.json", "contracts/output.schema.json",
                     "examples/input.json", "examples/output.json"):
            if path not in files:
                refusals.append(f"a task packet holds {path}")
        task = parsed.get("contracts/task.json")
        if isinstance(task, dict):
            expected = {"record_type", "node_id", "kind", "objective", "output_contract_refs", "dependency_ids",
                        "required_capabilities", "effects", "harness_style", "model_calls_authorized", "mode"}
            if set(task) != expected or task.get("record_type") != "node_assignment/v3" \
                    or task.get("kind") not in ("reason", "build") \
                    or task.get("mode") not in ("deterministic", "hybrid", "non_deterministic") \
                    or type(task.get("model_calls_authorized")) is not bool:
                refusals.append("contracts/task.json has exactly the node_assignment/v3 fields and values")
    if file_class == "subagent_definition":
        agents = [path for path, entry in declared.items() if entry.get("role") == "subagent_definition"]
        if not agents:
            refusals.append("a subagent package holds at least one subagent_definition file")
        for path in agents:
            refusals += section_findings("subagent", path, body(path), "subagent")
    if file_class == "command_file":
        commands = [path for path, entry in declared.items() if entry.get("role") == "command"]
        if not commands:
            refusals.append("a command package holds at least one command file")
        for path in commands:
            if path.endswith(".toml"):
                prompt = (parsed.get(path) or {}).get("prompt", "")
                if not isinstance(prompt, str) or not isinstance((parsed.get(path) or {}).get("description"), str):
                    refusals.append(f"{path}: a TOML command has description and prompt strings")
                else:
                    refusals += section_findings("command", path, prompt, "command")
            else:
                refusals += section_findings("command", path, body(path), "command")
    if file_class == "rules_file":
        rules = [path for path, entry in declared.items()
                 if entry.get("role") == "instruction_file" and path.startswith("variants/")]
        if not rules:
            refusals.append("a rules package holds rule files under variants/<harness>/")
        for path in rules:
            refusals += section_findings("rule", path, body(path), "rule")
    if file_class == "plugin_bundle":
        if not any(entry.get("role") == "plugin_manifest" for entry in declared.values()):
            refusals.append("a plugin package holds at least one plugin_manifest file")
        roles = {entry.get("role") for entry in declared.values()}
        component_roles = roles & {"skill_definition", "command", "subagent_definition", "hook",
                                   "protocol_server_configuration", "executable_tool", "skill_script"}
        if len(component_roles) < 2:
            refusals.append("a plugin bundles at least two component classes besides its manifest")
    # placeholders
    declared_placeholders = set(wave5.get("render_placeholders", {}) or {})
    used = set()
    for path in files:
        content = text(path) or ""
        found = set(PLACEHOLDER.findall(content))
        if found and path.startswith("examples/"):
            refusals.append(f"{path}: examples are filled and hold no placeholders")
        used |= found
    if file_class not in PLACEHOLDER_CLASSES and (used or declared_placeholders):
        refusals.append(f"only {PLACEHOLDER_CLASSES} use {{{{PLACEHOLDER}}}} markers and render_placeholders")
    if file_class in PLACEHOLDER_CLASSES and used != declared_placeholders:
        refusals.append(f"render_placeholders {sorted(declared_placeholders)} differ from markers used {sorted(used)}")
    for name, description in (wave5.get("render_placeholders") or {}).items():
        if not isinstance(description, str) or len(description.strip()) < 10:
            refusals.append(f"render placeholder {name} has a description of what the host fills in")
    # entrypoints name payload files
    entrypoints = wave5.get("entrypoints", {}) if isinstance(wave5.get("entrypoints"), dict) else {}
    for harness in targets:
        if harness not in entrypoints and harness not in (wave5.get("not_placed") or {}):
            refusals.append(f"wave5.entrypoints names the first file {harness} loads, or not_placed says why")
    for harness, path in entrypoints.items():
        if path not in files:
            refusals.append(f"entrypoint for {harness} names a missing payload file {path}")
    report.outcome("entry_shape", refusals, warnings)


def check_placements(files: dict, wave5: dict, report: Report) -> None:
    refusals = []
    targets = wave5.get("harness_targets", []) if isinstance(wave5.get("harness_targets"), list) else []
    placements = wave5.get("placements", {}) if isinstance(wave5.get("placements"), dict) else {}
    not_placed = wave5.get("not_placed", {}) if isinstance(wave5.get("not_placed"), dict) else {}
    unverified = wave5.get("unverified_targets", {}) if isinstance(wave5.get("unverified_targets"), dict) else {}
    for harness, reason in {**not_placed, **unverified}.items():
        if harness not in HARNESSES or not isinstance(reason, str) or len(reason.strip()) < 20:
            refusals.append(f"{harness}: a not_placed or unverified_targets entry names a known harness and a reason")
    for harness in targets:
        if harness in not_placed:
            if harness in placements:
                refusals.append(f"{harness} is both placed and not placed")
            continue
        mapping = placements.get(harness)
        if not isinstance(mapping, dict) or not mapping:
            refusals.append(f"{harness}: placements map payload files to destinations, or not_placed says why")
            continue
        destinations = {}
        entry = (wave5.get("entrypoints") or {}).get(harness)
        if entry is not None and mapping.get(entry) is None:
            refusals.append(f"{harness}: the entrypoint {entry} must be placed")
        for path, placement in mapping.items():
            if path not in files:
                refusals.append(f"{harness}: placement names a missing payload file {path}")
                continue
            if placement is None:
                continue  # explicitly not placed for this harness, for example CLAUDE.md for codex
            if not isinstance(placement, dict) or set(placement) != {"destination", "operation"} \
                    or placement.get("operation") not in OPERATIONS:
                refusals.append(f"{harness}: {path} placement names destination and an operation from {OPERATIONS}")
                continue
            destination = placement["destination"]
            problem = placement_problem(destination)
            if problem:
                refusals.append(f"{harness}: {path} -> {destination}: {problem}")
            if placement["operation"] == "copy_exact_bytes" and destination in destinations:
                refusals.append(f"{harness}: {path} and {destinations[destination]} copy to one destination {destination}")
            destinations.setdefault(destination, path)
            other = path.split("/")
            if other[0] == "variants" and len(other) > 2 and other[1] != harness:
                refusals.append(f"{harness}: {path} is a variant of another harness")
        for path in files:
            parts = path.split("/")
            is_other_variant = parts[0] == "variants" and len(parts) > 2 and parts[1] != harness
            if path not in mapping and not is_other_variant:
                refusals.append(f"{harness}: payload file {path} has no placement")
    for harness in placements:
        if harness not in targets:
            refusals.append(f"placements name {harness}, which is not a harness target")
    if len([harness for harness in targets if harness not in not_placed]) < 2:
        refusals.append("at least two harness targets are placed")
    report.outcome("placements", refusals)


def python_effects(path: str, text: str) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return found

    def note(effect, node, what):
        found.setdefault(effect, []).append(f"{path}:{getattr(node, 'lineno', 0)} {what}")

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in NETWORK_MODULES and alias.name not in ("http.server",):
                    note("network", node, f"import {alias.name}")
                if alias.name.split(".")[0] in ("subprocess", "pty", "multiprocessing"):
                    note("spawns_process", node, f"import {alias.name}")
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module.split(".")[0] in NETWORK_MODULES:
                note("network", node, f"from {node.module} import")
            if node.module.split(".")[0] in ("subprocess", "pty", "multiprocessing"):
                note("spawns_process", node, f"from {node.module} import")
        elif isinstance(node, ast.Call):
            target = node.func
            name = target.attr if isinstance(target, ast.Attribute) else target.id if isinstance(target, ast.Name) else ""
            if name in ("eval", "exec", "__import__", "import_module") or (name == "compile" and isinstance(target, ast.Name)):
                note("dynamic_execution", node, name)
            if name == "open":
                mode = None
                if len(node.args) > 1 and isinstance(node.args[1], ast.Constant):
                    mode = node.args[1].value
                for keyword in node.keywords:
                    if keyword.arg == "mode" and isinstance(keyword.value, ast.Constant):
                        mode = keyword.value.value
                if isinstance(mode, str) and any(flag in mode for flag in "wax+"):
                    note("writes_fs", node, f"open mode {mode!r}")
                else:
                    note("reads_fs", node, "open")
            elif name in READ_CALLS:
                note("reads_fs", node, name)
            receiver = target.value.id if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) else ""
            if name in READ_CALLS_ON_MODULE and receiver in READ_CALLS_ON_MODULE[name]:
                note("reads_fs", node, f"{receiver}.{name}")
            if name in WRITE_CALLS or (name in WRITE_CALLS_ON_MODULE and receiver in WRITE_CALLS_ON_MODULE[name]):
                note("writes_fs", node, name)
            if name in PROCESS_CALLS and isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) \
                    and target.value.id in ("subprocess", "os"):
                note("spawns_process", node, f"{target.value.id}.{name}")
            if name in ("getenv",) or (isinstance(target, ast.Attribute) and name == "get"
                                         and isinstance(target.value, ast.Attribute) and target.value.attr == "environ"):
                key = node.args[0].value if node.args and isinstance(node.args[0], ast.Constant) else ""
                if isinstance(key, str) and SECRET_ENV.search(key):
                    note("reads_secret", node, f"environment {key}")
        elif isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute) and node.value.attr == "environ":
            key = node.slice.value if isinstance(node.slice, ast.Constant) else ""
            if isinstance(key, str) and SECRET_ENV.search(key):
                note("reads_secret", node, f"environment {key}")
    return found


SHELL_BLOCK = re.compile(r"^```[ \t]*(?:bash|sh|shell|console|zsh|fish|powershell|pwsh|cmd|bat)\b[^\n]*\n(.*?)^```",
                         re.IGNORECASE | re.MULTILINE | re.DOTALL)
COMMAND_KEYS = {"command", "args", "cmd", "bash", "powershell", "exec"}
TRANSPORT_KEYS = {"url", "httpUrl", "serverUrl", "endpoint", "uri", "type", "transport"}


def shell_blocks(text: str) -> list[str]:
    return [match.group(1) for match in SHELL_BLOCK.finditer(text)]


def parsed_value(file: Path, path: str):
    try:
        if path.endswith(".json"):
            return strict_json(file.read_bytes())
        return tomllib.loads(file.read_bytes().decode("utf-8"))
    except Exception:  # noqa: BLE001 - the parse check reports it
        return None


def walk_pairs(value, where=""):
    if isinstance(value, dict):
        for key, item in value.items():
            yield from walk_pairs(item, f"{where}.{key}" if where else str(key))
            if isinstance(item, (str, list)):
                yield key, f"{where}.{key}" if where else str(key), item
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from walk_pairs(item, f"{where}[{index}]")


def command_values(value):
    for key, where, item in walk_pairs(value):
        if key in COMMAND_KEYS:
            text = " ".join(item) if isinstance(item, list) else item
            if isinstance(text, str):
                yield where, text


def transport_values(value):
    for key, where, item in walk_pairs(value):
        if key in TRANSPORT_KEYS and isinstance(item, str):
            lowered = item.lower()
            if lowered.startswith(("http://", "https://", "ws://", "wss://")) or lowered in (
                    "http", "sse", "streamable_http", "streamable-http", "remote", "websocket"):
                yield where, item


def check_effects_and_network(files: dict, declared: dict, proposal: dict, report: Report) -> None:
    refusals, warnings, network = [], [], []
    effects = set(proposal.get("declared_effects", []))
    detected: dict[str, list[str]] = {}
    for path, file in sorted(files.items()):
        text = text_of(file) or ""
        if path.endswith(".py"):
            for effect, where in python_effects(path, text).items():
                detected.setdefault(effect, []).extend(where)
            local_modules = {PurePosixPath(other).stem for other in files if other.endswith(".py")}
            try:
                nodes = list(ast.walk(ast.parse(text)))
            except SyntaxError:
                nodes = []
            for node in nodes:
                names = []
                if isinstance(node, ast.Import):
                    names = [alias.name.split(".")[0] for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                    names = [node.module.split(".")[0]]
                for name in names:
                    if name not in sys.stdlib_module_names and name not in local_modules:
                        refusals.append(f"{path}: import {name} is outside the standard library and the package")
        if path.endswith((".md", ".mdc", ".toml")):
            if SHELL_FENCE.search(text):
                detected.setdefault("spawns_process", []).append(f"{path}: shell code block")
            for block in shell_blocks(text):
                for match in SHELL_NETWORK.finditer(block):
                    network.append(f"{path}: shell block uses the network: {match.group(0).strip()!r}")
        if path.endswith((".json", ".toml")):
            for where, value in command_values(parsed_value(files[path], path)):
                for match in SHELL_NETWORK.finditer(value):
                    network.append(f"{path}: {where} uses the network: {match.group(0).strip()!r}")
            for where, value in transport_values(parsed_value(files[path], path)):
                network.append(f"{path}: {where} declares a remote transport {value!r}; wave 5 is local stdio only")
        if path.endswith(".py"):
            for match in re.finditer(r"https?://[^\s\"')]+", text):
                if "json-schema.org/draft/2020-12/schema" in match.group(0):
                    continue
                warnings.append(f"{path}:{text.count(chr(10), 0, match.start()) + 1}: URL {match.group(0)!r} in code")
    if "network" in detected:
        network += detected.pop("network")
    if "dynamic_execution" in detected:
        refusals += [f"dynamic code evaluation {where}" for where in detected.pop("dynamic_execution")]
    for effect, where in sorted(detected.items()):
        if effect not in effects:
            refusals.append(f"undeclared {effect}: {where[:3]}")
    for effect in sorted(effects - set(detected) - {"pure"}):
        warnings.append(f"{effect} is declared but no step or code was detected using it; the reviewer judges")
    report.outcome("effects", refusals, warnings)
    report.outcome("network_static", network)


def sandbox_argv(workdir: Path, interpreter: Path, argv: list[str], *, writable: bool, env: dict) -> list[str]:
    command = [BWRAP, "--ro-bind", "/usr", "/usr", "--symlink", "usr/lib", "/lib", "--symlink", "usr/lib64", "/lib64",
               "--symlink", "usr/bin", "/bin", "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp"]
    if not str(interpreter).startswith("/usr/"):
        root = interpreter.parent.parent
        command += ["--ro-bind", str(root), str(root)]
    command += ["--bind" if writable else "--ro-bind", str(workdir), "/work", "--chdir", "/work",
                "--unshare-net", "--unshare-pid", "--unshare-ipc", "--unshare-uts", "--die-with-parent",
                "--clearenv", "--setenv", "PATH", "/usr/bin:/bin", "--setenv", "HOME", "/tmp",
                "--setenv", "LANG", "C.UTF-8", "--setenv", "PYTHONDONTWRITEBYTECODE", "1"]
    for key, value in env.items():
        command += ["--setenv", key, value]
    return command + [str(interpreter)] + argv


def copy_payload(folder: Path, destination: Path) -> None:
    shutil.copytree(folder / "payload", destination, symlinks=False)
    for path in destination.rglob("*"):
        path.chmod(0o755 if path.is_dir() else 0o644)


def run_tests(folder: Path, files: dict, proposal: dict, wave5: dict, report: Report) -> None:
    refusals, warnings, runs = [], [], []
    scripts = [path for path in files if path.endswith(".py") and not path.startswith("tests/")]
    tests = [path for path in files if path.startswith("tests/") and PurePosixPath(path).name.startswith("test_")
             and path.endswith(".py")]
    if scripts and not tests:
        refusals.append("every package with Python code holds tests/test_*.py")
    test_text = "\n".join(text_of(files[path]) or "" for path in tests)
    for script in scripts:
        if PurePosixPath(script).name not in test_text:
            refusals.append(f"{script} is not named by any test file")
    if tests:
        spec = wave5.get("tests")
        expected = ["python3", "-I", "-B", "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"]
        if not isinstance(spec, dict) or spec.get("command") != expected or spec.get("minimum_python") != "3.10":
            refusals.append(f"wave5.tests is {{\"command\": {expected}, \"minimum_python\": \"3.10\"}}")
        if BWRAP is None:
            refusals.append("Bubblewrap is not installed; tests are never run outside the sandbox")
        else:
            writable = "writes_fs" in proposal.get("declared_effects", [])
            for label, interpreter in PYTHONS:
                if not interpreter.exists():
                    warnings.append(f"{label} is not installed; not run")
                    continue
                with tempfile.TemporaryDirectory(prefix="wave5-tests-") as directory:
                    work = Path(directory) / "work"
                    copy_payload(folder, work)
                    argv = sandbox_argv(work, interpreter, ["-I", "-B", "-m", "unittest", "discover", "-s", "tests",
                                                            "-p", "test_*.py", "-v"], writable=writable, env={})
                    try:
                        finished = subprocess.run(argv, capture_output=True, text=True, timeout=300)
                        tail = (finished.stderr.strip().splitlines() or [""])[-1]
                        counted = re.search(r"Ran (\d+) tests?", finished.stderr)
                        runs.append({"python": label, "exit": finished.returncode, "summary": tail,
                                     "tests_ran": int(counted.group(1)) if counted else 0})
                        if finished.returncode != 0:
                            refusals.append(f"{label}: tests failed: {finished.stderr[-800:]}")
                        elif not counted or int(counted.group(1)) == 0:
                            refusals.append(f"{label}: no test ran")
                    except subprocess.TimeoutExpired:
                        refusals.append(f"{label}: tests did not finish in 300 seconds")
    report.add("tests_run", "refused" if refusals else ("warning" if warnings else "passed"),
               refusals + warnings + [json.dumps(run) for run in runs])


def run_hooks(folder: Path, files: dict, proposal: dict, wave5: dict, report: Report) -> None:
    refusals, observations = [], []
    hooks = wave5.get("hooks") or []
    if wave5.get("file_class") == "hook_with_script" and not hooks:
        refusals.append("a hook package declares wave5.hooks with samples")
    for hook in hooks:
        if not isinstance(hook, dict) or set(hook) != {"harness", "event", "script", "arguments", "environment",
                                                         "samples"}:
            refusals.append("each hook names harness, event, script, arguments, environment and samples")
            continue
        if hook["script"] not in files or not isinstance(hook["arguments"], list) \
                or not isinstance(hook["environment"], dict) or not hook["samples"]:
            refusals.append(f"hook {hook.get('script')}: script exists, arguments list, environment object, samples")
            continue
        for sample in hook["samples"]:
            if not isinstance(sample, dict) or set(sample) != {"input", "expect_exit", "expect_stdout_json",
                                                               "expect_stdout_contains"}:
                refusals.append("each hook sample names input, expect_exit, expect_stdout_json, expect_stdout_contains")
                continue
            if sample["input"] not in files:
                refusals.append(f"hook sample {sample['input']} is not a payload file")
                continue
            if BWRAP is None:
                refusals.append("Bubblewrap is not installed; hooks are never run outside the sandbox")
                break
            with tempfile.TemporaryDirectory(prefix="wave5-hook-") as directory:
                work = Path(directory) / "work"
                copy_payload(folder, work)
                environment = {key: str(value).replace("{WORKSPACE}", "/work") for key, value in hook["environment"].items()}
                argv = sandbox_argv(work, PYTHONS[0][1], ["-I", "-B", hook["script"], *hook["arguments"]],
                                    writable=True, env=environment)
                try:
                    finished = subprocess.run(argv, input=(work / sample["input"]).read_bytes(), capture_output=True,
                                              timeout=20)
                except subprocess.TimeoutExpired:
                    refusals.append(f"{hook['script']} with {sample['input']}: no answer in 20 seconds")
                    continue
                stdout = finished.stdout.decode("utf-8", "replace")
                observations.append(f"{hook['harness']} {hook['event']} {sample['input']}: exit {finished.returncode}")
                if finished.returncode != sample["expect_exit"]:
                    refusals.append(f"{sample['input']}: exit {finished.returncode}, expected {sample['expect_exit']}; "
                                    f"stderr {finished.stderr.decode('utf-8', 'replace')[-300:]!r}")
                if sample["expect_stdout_json"]:
                    try:
                        strict_json(finished.stdout.strip() or b"null")
                    except Exception:  # noqa: BLE001
                        refusals.append(f"{sample['input']}: standard output is not one JSON value")
                for expected in sample["expect_stdout_contains"]:
                    if expected not in stdout:
                        refusals.append(f"{sample['input']}: standard output lacks {expected!r}")
    report.add("hooks_run", "refused" if refusals else "passed", refusals + observations)


def rpc(process, message, timeout=10.0):
    process.stdin.write((json.dumps(message) + "\n").encode("utf-8"))
    process.stdin.flush()
    if "id" not in message:
        return None
    ready, _w, _x = select.select([process.stdout], [], [], timeout)
    if not ready:
        raise TimeoutError(f"no answer to {message.get('method')}")
    line = process.stdout.readline()
    return json.loads(line.decode("utf-8"))


def run_servers(folder: Path, files: dict, wave5: dict, report: Report) -> None:
    refusals, observations = [], []
    servers = wave5.get("servers") or []
    if wave5.get("file_class") == "protocol_server_config_local" and not servers:
        refusals.append("a protocol server package declares wave5.servers")
    for server in servers:
        if not isinstance(server, dict) or set(server) != {"name", "script", "arguments", "tools", "sample_call",
                                                           "protocol_versions"}:
            refusals.append("each server names name, script, arguments, tools, sample_call and protocol_versions")
            continue
        if server["script"] not in files or BWRAP is None:
            refusals.append(f"server script {server['script']} exists and Bubblewrap is installed")
            continue
        with tempfile.TemporaryDirectory(prefix="wave5-server-") as directory:
            work = Path(directory) / "work"
            copy_payload(folder, work)
            argv = sandbox_argv(work, PYTHONS[0][1], ["-I", "-B", server["script"], *server["arguments"]],
                                writable=False, env={})
            process = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                answer = rpc(process, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
                    "protocolVersion": server["protocol_versions"][0], "capabilities": {},
                    "clientInfo": {"name": "wave5-check", "version": "0.1.0"}}})
                result = answer.get("result", {})
                if result.get("protocolVersion") not in server["protocol_versions"] or "tools" not in result.get("capabilities", {}):
                    refusals.append(f"{server['name']}: initialize answered {json.dumps(result)[:300]}")
                rpc(process, {"jsonrpc": "2.0", "method": "notifications/initialized"})
                listed = rpc(process, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
                names = sorted(tool.get("name") for tool in listed.get("result", {}).get("tools", []))
                if names != sorted(server["tools"]):
                    refusals.append(f"{server['name']}: tools/list gave {names}, expected {sorted(server['tools'])}")
                call = server["sample_call"]
                called = rpc(process, {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                                       "params": {"name": call["tool"], "arguments": call["arguments"]}})
                content = called.get("result", {})
                if not isinstance(content.get("content"), list) or bool(content.get("isError")) != call["expect_is_error"]:
                    refusals.append(f"{server['name']}: tools/call answered {json.dumps(called)[:400]}")
                bad = rpc(process, {"jsonrpc": "2.0", "id": 4, "method": "no/such/method", "params": {}})
                if "error" not in bad:
                    refusals.append(f"{server['name']}: an unknown method must return a JSON-RPC error")
                observations.append(f"{server['name']}: initialize, tools/list, tools/call and error answered")
            except Exception as error:  # noqa: BLE001
                refusals.append(f"{server['name']}: {type(error).__name__}: {error}; "
                                f"stderr {process.stderr.read1(400) if process.poll() is not None else b''!r}")
            finally:
                try:
                    process.stdin.close()
                    process.wait(timeout=5)
                except Exception:  # noqa: BLE001
                    process.kill()
                    process.wait()
                    refusals.append(f"{server['name']}: did not exit within 5 seconds after its input closed")
                finally:
                    process.stdout.close()
                    process.stderr.close()
    report.add("servers_run", "refused" if refusals else "passed", refusals + observations)


def run_skill_validators(folder: Path, files: dict, wave5: dict, report: Report) -> None:
    findings, observations = [], []
    skill_dirs = sorted({str(PurePosixPath(path).parent) for path in files if PurePosixPath(path).name == "SKILL.md"})
    if not skill_dirs:
        report.add("agent_skills_validator", "skipped", ["no SKILL.md in the payload"])
        return
    for relative in skill_dirs:
        source = folder / "payload" / relative if relative != "." else folder / "payload"
        text = text_of(source / "SKILL.md") or ""
        front, _ = split_front_matter(text)
        name = (yaml_mapping(front) if front else {}).get("name", wave5.get("native_name"))
        with tempfile.TemporaryDirectory(prefix="wave5-skill-") as directory:
            target = Path(directory) / str(name)
            shutil.copytree(source, target)
            for label, program in VALIDATORS:
                if not program.exists():
                    observations.append(f"{label}: not installed")
                    continue
                finished = subprocess.run([str(program), "validate", str(target)], capture_output=True, text=True,
                                          timeout=60)
                output = " ".join((finished.stdout + " " + finished.stderr).split()).replace(directory, "TMP")
                observations.append(f"{label} {relative}: exit {finished.returncode} {output[:200]}")
                if finished.returncode != 0:
                    findings.append(f"{label} refused {relative}: {output[:400]}")
    report.add("agent_skills_validator", "refused" if findings else "passed", findings + observations)


def shingles(text: str, size: int = 5) -> frozenset:
    tokens = tuple(re.findall(r"[a-z0-9]+", text.casefold()))
    if len(tokens) < size:
        return frozenset({tokens}) if tokens else frozenset()
    return frozenset(tokens[index:index + size] for index in range(len(tokens) - size + 1))


def model_facing_text(files: dict) -> str:
    parts = []
    for path in sorted(files):
        if path == "LICENSE" or path.startswith(("tests/", "examples/")) or path.endswith((".py", ".json")):
            continue
        parts.append(text_of(files[path]) or "")
    return "\n".join(parts)


def check_duplicates(folder: Path, files: dict, report: Report, others: dict | None = None) -> None:
    refusals, warnings = [], []
    own = shingles(model_facing_text(files))
    corpus = json.loads((WAVE / "scout" / "inputs" / "corpus.json").read_text(encoding="utf-8"))["bodies"]
    comparisons = dict(corpus)
    for package in PACKAGES.glob("*/*/"):
        if package.resolve() != folder.resolve() and (package / "payload").is_dir():
            try:
                comparisons[f"wave5:{package.name}"] = model_facing_text(payload_files(package))
            except Exception:  # noqa: BLE001
                continue
    for name, text in comparisons.items():
        other = shingles(text)
        if not own or not other:
            continue
        similarity = len(own & other) / len(own | other)
        if similarity >= 0.8:
            refusals.append(f"near duplicate of {name}: five-word shingle similarity {similarity:.3f}")
        elif similarity >= 0.5:
            warnings.append(f"similar to {name}: {similarity:.3f}")
    report.outcome("duplicates", refusals, warnings)


def check_review_note(folder: Path, report: Report) -> None:
    refusals = []
    path = folder / "review" / "REVIEW-NOTE.md"
    text = text_of(path) if path.exists() else ""
    if not text:
        report.outcome("review_note", ["review/REVIEW-NOTE.md is missing or not UTF-8"])
        return
    lines = text.splitlines()
    if CANDIDATE_SENTENCE not in text:
        refusals.append(f"the note states: {CANDIDATE_SENTENCE}")
    missing = [heading for heading in REVIEW_HEADINGS if heading not in lines]
    if missing:
        refusals.append(f"missing sections {missing}")
    if re.search(r"(?i)\b(is|was|been) (approved|qualified|admitted)\b", text):
        refusals.append("a producer note never claims approval, qualification or admission")
    for pattern in FORBIDDEN_VOCABULARY[13:14]:
        if pattern.search(text):
            refusals.append("the note uses an em or en dash")
    if word_count(text) < 250:
        refusals.append("the note holds at least 250 words")
    report.outcome("review_note", refusals)


def check_package(folder: Path, *, skip_runs: bool = False, write: bool = True) -> dict:
    folder = folder.resolve()
    report = Report()
    started = _dt.datetime.now(_dt.timezone.utc).isoformat()
    check_layout(folder, report)
    try:
        manifest, proposal, wave5 = load_package(folder)
    except Exception as error:  # noqa: BLE001
        report.add("manifest_schema", "refused", [f"package.json unreadable: {error}"])
        return finish(folder, report, started, write)
    try:
        files = payload_files(folder)
    except Exception as error:  # noqa: BLE001
        report.add("inventory", "refused", [str(error)])
        return finish(folder, report, started, write)
    declared = {entry.get("path"): entry for entry in proposal.get("files", []) if isinstance(entry, dict)}
    check_manifest(folder, manifest, proposal, wave5, report)
    check_identity(folder, proposal, report)
    check_inventory(folder, proposal, wave5, files, report)
    check_text(files, folder, report)
    check_secrets(folder, report)
    parsed = check_parse(files, declared, report)
    check_entries(files, declared, proposal, wave5, parsed, report)
    check_placements(files, wave5, report)
    check_effects_and_network(files, declared, proposal, report)
    run_skill_validators(folder, files, wave5, report)
    check_duplicates(folder, files, report)
    check_review_note(folder, report)
    if skip_runs:
        report.add("tests_run", "skipped", ["--skip-runs was given; this report cannot pass the wave gate"])
    else:
        run_tests(folder, files, proposal, wave5, report)
        run_hooks(folder, files, proposal, wave5, report)
        run_servers(folder, files, wave5, report)
    return finish(folder, report, started, write, wave5.get("package_digest"), skip_runs)


def finish(folder: Path, report: Report, started: str, write: bool, digest=None, skip_runs=False) -> dict:
    checker = sha256(Path(__file__).read_bytes())
    record = {"record_type": REPORT_TYPE, "package": str(folder.relative_to(WAVE)) if folder.is_relative_to(WAVE) else str(folder),
              "identity": folder.name, "package_digest": digest, "checked_at": started,
              "checker_sha256": checker, "contracts": CONTRACT_SOURCE, "runs_skipped": skip_runs,
              "refused": report.refused, "passed_for_wave_gate": not report.refused and not skip_runs,
              "results": report.results,
              "limits": "Deterministic pre-checks only. Not an approval, rights decision, native loading result or usefulness claim."}
    if write and (folder / "review").is_dir():
        target = folder / "review" / f"precheck-{now_stamp()}.json"
        with target.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(record, indent=1) + "\n")
        record["written_to"] = str(target.relative_to(folder))
    return record


def command_check(folder: Path, skip_runs: bool) -> int:
    record = check_package(folder, skip_runs=skip_runs)
    summary = {result["check"]: result["status"] for result in record["results"]}
    print(json.dumps({"identity": record["identity"], "refused": record["refused"],
                      "passed_for_wave_gate": record["passed_for_wave_gate"], "checks": summary,
                      "report": record.get("written_to")}, indent=1))
    for result in record["results"]:
        if result["status"] in ("refused", "warning"):
            print(f"\n[{result['status']}] {result['check']}")
            for finding in result["findings"]:
                print(f"  - {finding}")
    return 1 if record["refused"] else 0


def command_check_all(skip_runs: bool, assignment: str | None = None) -> int:
    REPORTS.mkdir(exist_ok=True)
    packages = sorted(path for path in PACKAGES.glob("*/*") if path.is_dir()
                      and (assignment is None or path.parent.name == assignment))
    records = [check_package(path, skip_runs=skip_runs) for path in packages]
    identities, natives, digests, cross = {}, {}, {}, []
    for path, record in zip(packages, records):
        try:
            _manifest, proposal, wave5 = load_package(path)
        except Exception:  # noqa: BLE001
            continue
        for index, key in ((identities, proposal.get("id")), (natives, wave5.get("native_name")),
                           (digests, wave5.get("package_digest"))):
            if key in index:
                cross.append(f"{path.name} repeats {key} of {index[key]}")
            index[key] = path.name
    assignments = json.loads((WAVE / "assignments.json").read_text(encoding="utf-8"))
    planned = {(item["id"], package["identity"]) for item in assignments["assignments"] for package in item["packages"]
               if assignment is None or item["id"] == assignment}
    present = {(path.parent.name, path.name) for path in packages}
    unplanned = sorted(present - planned)
    if unplanned:
        cross.append(f"packages outside assignments.json: {unplanned}")
    if planned - present:
        cross.append(f"planned packages not present yet: {sorted(planned - present)}")
    record = {"record_type": ALL_REPORT_TYPE, "checked_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
              "packages": len(records), "refused": [r["identity"] for r in records if r["refused"]],
              "passed_for_wave_gate": [r["identity"] for r in records if r["passed_for_wave_gate"]],
              "missing_planned": sorted(planned - present), "cross_package_refusals": cross,
              "reports": [r.get("written_to") and f"{r['package']}/{r['written_to']}" for r in records]}
    target = REPORTS / f"precheck-all-{now_stamp()}.json"
    with target.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(record, indent=1) + "\n")
    print(json.dumps({key: record[key] for key in ("packages", "refused", "missing_planned", "cross_package_refusals")},
                     indent=1))
    print(f"report: {target.relative_to(WAVE)}")
    return 1 if record["refused"] or cross else 0


def command_emit(output: Path) -> int:
    output = output.resolve()
    if output.exists():
        print("refused: the output exists; choose a new name")
        return 1
    proposals, sources, revision = [], {}, None
    for package in sorted(path for path in PACKAGES.glob("*/*") if path.is_dir()):
        _manifest, proposal, wave5 = load_package(package)
        reports = sorted((package / "review").glob("precheck-*.json"))
        latest = strict_json(reports[-1].read_bytes()) if reports else {}
        if not latest.get("passed_for_wave_gate") or latest.get("package_digest") != wave5.get("package_digest"):
            print(f"refused: {package.name} has no passing precheck for its current package digest")
            return 1
        revision = revision or wave5["source_revision"]
        if wave5["source_revision"] != revision:
            print("refused: packages pin different source revisions")
            return 1
        sources.update(wave5["source_digests"])
        files = payload_files(package)
        row = dict(proposal)
        row["files"] = [{**entry, "content_base64": base64.b64encode(files[entry["path"]].read_bytes()).decode("ascii")}
                        for entry in proposal["files"]]
        proposals.append(row)
    document = {"record_type": PROPOSALS_TYPE, "source_revision": revision,
                "license": {"expression": "MIT", "path": "LICENSE", "sha256": LICENSE_SHA256},
                "sources": dict(sorted(sources.items())), "proposals": proposals}
    with output.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(document, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {len(proposals)} proposals to {output}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    fill = commands.add_parser("fill", help="write digests, sizes and the package digest into package.json")
    fill.add_argument("package", type=Path)
    check = commands.add_parser("check", help="run every pre-check on one package and save a new report")
    check.add_argument("package", type=Path)
    check.add_argument("--skip-runs", action="store_true", help="skip tests, hooks and servers (never passes the gate)")
    check_all = commands.add_parser("check-all", help="check every package and the cross-package rules")
    check_all.add_argument("--skip-runs", action="store_true")
    check_all.add_argument("--assignment", help="check only this assignment's packages and plan")
    emit = commands.add_parser("emit-proposals", help="write harness_candidate_batch_proposals/v2 for integration")
    emit.add_argument("--output", type=Path, required=True)
    options = parser.parse_args(argv)
    if options.command == "fill":
        return command_fill(options.package)
    if options.command == "check":
        return command_check(options.package, options.skip_runs)
    if options.command == "check-all":
        return command_check_all(options.skip_runs, options.assignment)
    return command_emit(options.output)


if __name__ == "__main__":
    raise SystemExit(main())
