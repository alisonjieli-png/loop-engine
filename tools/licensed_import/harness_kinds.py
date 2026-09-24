"""Which files of a repository a harness picks up, grouped into packages.

A harness file is any file a coding harness reads from a working directory
or its step configuration. This module reads one repository tree (paths,
modes and object identities, never bytes) and returns one package plan per
unit a harness picks up whole:

```text
Package kinds, each found by its native path
├── skill: a folder holding SKILL.md, with its scripts, references and assets
├── instruction_file: AGENTS.md, CLAUDE.md, GEMINI.md, .goosehints, .github/copilot-instructions.md
├── rules: Cursor .mdc rules, .cursorrules, .windsurfrules, .clinerules, *.instructions.md,
│   .claude/rules, .kiro/steering, .roo/rules
├── subagent: .claude/agents, *.agent.md, *.chatmode.md, .opencode/agent, a plugin's agents/
├── command: .claude/commands, *.prompt.md, .opencode/command, .gemini/commands, a plugin's commands/
├── hook: a plugin's hooks/hooks.json or hooks.json with the scripts beside it, .cursor/hooks.json
├── plugin_manifest: .claude-plugin/plugin.json, .codex-plugin/plugin.json, gemini-extension.json
├── marketplace: .claude-plugin/marketplace.json, .agents/plugins/marketplace.json
├── protocol_server_configuration: .mcp.json, .vscode/mcp.json, .cursor/mcp.json
├── contract_schema: JSON schemas, only where a source declares them
└── code_module: a module with its tests, only where a source declares them
```

A plugin is imported as its parts: its manifest is one package and each
skill, subagent, command and hook inside it is its own package that names
the plugin it belongs to. No file is copied into two packages, so no count
holds the same bytes twice, and the Harness Working Directory Compiler can
assemble a plugin from its approved parts later.

Every package records where each harness would place it. The paths come
from the verified layouts in docs/research/HARNESS-FILE-STANDARDS-FLEXIBILITY-2026-09-23.md
and the layout profiles in tools/install_selected_material.py. They are
documented targets, not a claim that a harness loaded the package here.
"""
from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field
from pathlib import PurePosixPath

from loop_engine.core.library_ingestion.licences import is_licence_file, is_notice_file
from loop_engine.core.service_runtime.catalogue_packages import MAXIMUM_PACKAGE_FILES

from .records import (
    CODE_MODULE, COMMAND, CONTRACT_SCHEMA, HOOK, INSTRUCTION_FILE, MARKETPLACE, PACKAGE_KINDS,
    PLUGIN_MANIFEST, PROTOCOL_SERVER, RULES, SKILL, SUBAGENT)

#: Git tree modes and object types that are never a file with bytes to copy.
BLOB_TYPE, TREE_TYPE, COMMIT_TYPE = "blob", "tree", "commit"
SYMLINK_MODE, SUBMODULE_MODE = "120000", "160000"
#: Folders whose files are generated, vendored or test fixtures, never harness material.
EXCLUDED_SEGMENTS = frozenset({"node_modules", "vendor", ".venv", "venv", "site-packages", "__pycache__",
                               "dist", "build", ".git", "fixtures", "__fixtures__", "testdata", "test-data",
                               ".next", "target", ".tox", ".cache"})
#: Kinds imported unless a source narrows them; schemas and code modules only where declared.
DEFAULT_KINDS = (SKILL, INSTRUCTION_FILE, RULES, SUBAGENT, COMMAND, HOOK, PLUGIN_MANIFEST, MARKETPLACE,
                 PROTOCOL_SERVER, CODE_MODULE)
#: The subfolders of a skill that sits at a repository root; the rest of the root is the repository's.
ROOT_SKILL_FOLDERS = ("scripts", "references", "assets", "templates", "examples", "resources", "reference")

_INSTRUCTION_NAMES = {"agents.md", "agents.override.md", "claude.md", "gemini.md", ".goosehints"}
_RULE_FILES = {".cursorrules", ".windsurfrules", ".clinerules"}
_RULE_FOLDERS = ((".claude", "rules"), (".windsurf", "rules"), (".kiro", "steering"), (".roo", "rules"),
                 (".clinerules",), (".augment", "rules"), (".trae", "rules"))
_AGENT_FOLDERS = ((".claude", "agents"), (".opencode", "agent"), (".opencode", "agents"))
_COMMAND_FOLDERS = ((".claude", "commands"), (".opencode", "command"), (".opencode", "commands"))
_PLUGIN_MANIFESTS = ((".claude-plugin", "plugin.json"), (".codex-plugin", "plugin.json"))
_MARKETPLACES = ((".claude-plugin", "marketplace.json"), (".agents", "plugins", "marketplace.json"))
_PROTOCOL_FILES = ((".vscode", "mcp.json"), (".cursor", "mcp.json"))
_TOOL_FOLDERS = ((".opencode", "tool"), (".opencode", "tools"))
_PLUGIN_CODE_FOLDERS = ((".opencode", "plugin"), (".opencode", "plugins"))
_SCRIPT_SUFFIXES = (".sh", ".py", ".js", ".mjs", ".ts")
_EXECUTABLE_SUFFIXES = frozenset({".py", ".sh", ".bash", ".zsh", ".js", ".mjs", ".cjs", ".ts", ".rb", ".pl",
                                  ".ps1", ".php", ".lua", ".go", ".rs"})
_TEXT_REFERENCE_SUFFIXES = frozenset({".md", ".txt", ".rst", ".markdown"})
_CODE_SUFFIXES = frozenset({".py", ".js", ".mjs", ".ts", ".go", ".rs", ".rb", ".sh"})
_MEDIA_TYPES = {".md": "text/markdown", ".mdc": "text/markdown", ".markdown": "text/markdown",
                ".txt": "text/plain", ".rst": "text/x-rst", ".json": "application/json",
                ".toml": "application/toml", ".yaml": "application/yaml", ".yml": "application/yaml",
                ".py": "text/x-python", ".sh": "application/x-sh", ".bash": "application/x-sh",
                ".zsh": "application/x-sh", ".js": "text/javascript", ".mjs": "text/javascript",
                ".cjs": "text/javascript", ".ts": "text/x-typescript", ".tsx": "text/x-typescript",
                ".jsx": "text/javascript", ".rb": "text/x-ruby", ".pl": "text/x-perl", ".ps1": "text/x-powershell",
                ".go": "text/x-go", ".rs": "text/x-rust", ".php": "text/x-php", ".lua": "text/x-lua",
                ".html": "text/html", ".css": "text/css", ".csv": "text/csv", ".xml": "application/xml",
                ".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                ".gif": "image/gif", ".webp": "image/webp", ".pdf": "application/pdf",
                ".ipynb": "application/x-ipynb+json", ".sql": "application/sql", ".ini": "text/plain",
                ".cfg": "text/plain", ".env": "text/plain", ".tmpl": "text/plain", ".j2": "text/plain"}
_STEM_SUFFIXES = (".instructions.md", ".agent.md", ".chatmode.md", ".prompt.md", ".schema.json", ".md", ".mdc",
                  ".toml", ".json")


@dataclass(frozen=True)
class TreeEntry:
    """One entry of a git tree: its path, mode, object type and object identity."""

    path: str
    mode: str
    object_type: str
    oid: str


@dataclass(frozen=True)
class PackagePlan:
    """One unit a harness picks up: its kind, root, primary file and every member path."""

    kind: str
    root: str
    primary: str
    members: tuple
    name: str
    native_format: str
    plugin: "dict | None" = None
    problems: tuple = ()
    roles: dict = field(default_factory=dict)


@dataclass(frozen=True)
class SourceScope:
    """What one source asks for: the kinds, and optional include and exclude patterns."""

    kinds: tuple = DEFAULT_KINDS
    include: tuple = ()
    exclude: tuple = ()

    def __post_init__(self) -> None:
        if not self.kinds or any(kind not in PACKAGE_KINDS for kind in self.kinds):
            raise ValueError(f"a source scope names kinds from {PACKAGE_KINDS}")

    def admits(self, path: str) -> bool:
        if self.include and not any(fnmatch.fnmatchcase(path, pattern) for pattern in self.include):
            return False
        return not any(fnmatch.fnmatchcase(path, pattern) for pattern in self.exclude)


def _parts(path: str) -> tuple:
    return tuple(PurePosixPath(path).parts)


def excluded(path: str) -> bool:
    """True for a path inside a generated, vendored or fixture folder."""
    return any(part.lower() in EXCLUDED_SEGMENTS for part in _parts(path)[:-1])


def _under(path: str, folder: tuple) -> bool:
    """True when the path lies inside a folder sequence such as (.claude, agents), at any depth."""
    parts = tuple(part.lower() for part in _parts(path)[:-1])
    width = len(folder)
    return any(parts[index:index + width] == folder for index in range(len(parts) - width + 1))


def _ends_with(path: str, tail: tuple) -> bool:
    parts = tuple(part.lower() for part in _parts(path))
    return len(parts) >= len(tail) and parts[-len(tail):] == tail


def media_type(path: str) -> str:
    name = PurePosixPath(path).name.lower()
    suffix = PurePosixPath(name).suffix
    if not suffix or name.startswith(".") and name.count(".") == 1:
        return "text/plain"
    return _MEDIA_TYPES.get(suffix, "application/octet-stream")


def item_stem(path: str) -> str:
    """The name of a single-file item: its file name without the harness suffix."""
    name = PurePosixPath(path).name
    for suffix in _STEM_SUFFIXES:
        if name.lower().endswith(suffix) and len(name) > len(suffix):
            return name[: -len(suffix)].lstrip(".") or name
    return name.lstrip(".") or name


def plugin_roots(paths) -> dict:
    """Every plugin or extension root in a tree, with the manifest that declares it."""
    roots = {}
    for path in paths:
        for tail in _PLUGIN_MANIFESTS:
            if _ends_with(path, tail):
                parts = _parts(path)
                roots[str(PurePosixPath(*parts[:-2])) if len(parts) > 2 else ""] = path
        if PurePosixPath(path).name == "gemini-extension.json":
            parent = str(PurePosixPath(path).parent)
            roots["" if parent == "." else parent] = path
    return roots


def _plugin_of(path: str, roots: dict) -> "tuple | None":
    """The nearest plugin root above a path, and the path relative to it."""
    folder = PurePosixPath(path).parent
    while True:
        key = "" if str(folder) == "." else str(folder)
        if key in roots:
            relative = path[len(key) + 1:] if key else path
            return key, relative
        if key == "":
            return None
        folder = folder.parent


def classify(path: str, roots: dict) -> "tuple | None":
    """(kind, native format) of one blob path, or None when no harness reads it as a unit."""
    lower = PurePosixPath(path).name.lower()
    if lower == "skill.md":
        return SKILL, "agent_skill"
    if lower in _INSTRUCTION_NAMES:
        return INSTRUCTION_FILE, lower.replace(".", "_").strip("_")
    if _ends_with(path, (".github", "copilot-instructions.md")):
        return INSTRUCTION_FILE, "copilot_instructions"
    if lower.endswith(".mdc"):
        return RULES, "cursor_rule"
    if lower in _RULE_FILES:
        return RULES, lower.strip(".")
    if lower.endswith(".instructions.md"):
        return RULES, "copilot_path_instructions"
    if lower.endswith(".md") and any(_under(path, folder) for folder in _RULE_FOLDERS):
        return RULES, "folder_rule"
    if lower.endswith(".agent.md"):
        return SUBAGENT, "copilot_agent"
    if lower.endswith(".chatmode.md"):
        return SUBAGENT, "copilot_chat_mode"
    if lower.endswith(".prompt.md"):
        return COMMAND, "copilot_prompt"
    if lower.endswith(".md") and any(_under(path, folder) for folder in _AGENT_FOLDERS):
        return SUBAGENT, "agent_definition"
    if lower.endswith(".md") and any(_under(path, folder) for folder in _COMMAND_FOLDERS):
        return COMMAND, "command_definition"
    if lower.endswith(".toml") and _under(path, (".gemini", "commands")):
        return COMMAND, "gemini_command"
    if any(_ends_with(path, tail) for tail in _PLUGIN_MANIFESTS) or lower == "gemini-extension.json":
        return PLUGIN_MANIFEST, "plugin_manifest"
    if any(_ends_with(path, tail) for tail in _MARKETPLACES):
        return MARKETPLACE, "plugin_marketplace"
    if lower == ".mcp.json" or any(_ends_with(path, tail) for tail in _PROTOCOL_FILES):
        return PROTOCOL_SERVER, "protocol_server_configuration"
    if _ends_with(path, (".cursor", "hooks.json")):
        return HOOK, "cursor_hooks"
    if lower.endswith(_SCRIPT_SUFFIXES) and _under(path, (".claude", "hooks")):
        return HOOK, "claude_hook_script"
    if lower.endswith((".ts", ".js", ".mjs")) and any(_under(path, folder) for folder in _TOOL_FOLDERS):
        return CODE_MODULE, "opencode_tool"
    if lower.endswith((".ts", ".js", ".mjs")) and any(_under(path, folder) for folder in _PLUGIN_CODE_FOLDERS):
        return CODE_MODULE, "opencode_plugin"
    inside = _plugin_of(path, roots)
    if inside is not None:
        _root, relative = inside
        relative_parts = tuple(part.lower() for part in _parts(relative))
        if relative_parts in (("hooks", "hooks.json"), ("hooks.json",)):
            return HOOK, "plugin_hooks"
        if len(relative_parts) >= 2 and relative_parts[0] == "agents" and lower.endswith(".md"):
            return SUBAGENT, "plugin_agent"
        if len(relative_parts) >= 2 and relative_parts[0] == "commands" and lower.endswith((".md", ".toml")):
            return COMMAND, "plugin_command"
    return None


_TEST_NAME = re.compile(r"(?:^test_.+|.+_test|.+\.test|.+\.spec)\Z")


def declared_kind(path: str, scope: SourceScope) -> "tuple | None":
    """A schema or a code module, found only where the source declares those kinds and paths.

    Neither has a native file name a harness looks for, so they are never
    guessed from a whole repository: the source must name the kind and the
    include patterns. A test file is a member of its module, not a module.
    """
    if not scope.include or not scope.admits(path):
        return None
    location = PurePosixPath(path)
    if CONTRACT_SCHEMA in scope.kinds and location.suffix.lower() == ".json":
        return CONTRACT_SCHEMA, "json_schema"
    if (CODE_MODULE in scope.kinds and location.suffix.lower() in _CODE_SUFFIXES
            and not _TEST_NAME.match(location.stem) and location.parent.name not in ("tests", "test", "__tests__")):
        return CODE_MODULE, "code_module"
    return None


def _skill_members(root: str, primary: str, blobs: dict, skill_roots: set) -> list:
    """Every blob in a skill folder, without nested skills; a root skill keeps its standard folders."""
    if root == "":
        members = [primary]
        for path in blobs:
            first = _parts(path)[0]
            if path != primary and (first in ROOT_SKILL_FOLDERS or (len(_parts(path)) == 1 and
                                                                     (is_licence_file(path) or is_notice_file(path)))):
                members.append(path)
    else:
        prefix = root + "/"
        members = [path for path in blobs if path.startswith(prefix)]
    nested = [other for other in skill_roots if other != root and (root == "" or other.startswith(root + "/"))]
    return sorted(path for path in members
                  if not any(path.startswith(other + "/") for other in nested) and not excluded(path))


_PLUGIN_ROOT_REFERENCE = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}/([A-Za-z0-9._/@+-]{1,200})")


def hook_members(root: str, primary: str, blobs: dict, text: "str | None" = None) -> list:
    """A hook configuration, every file in its hooks folder, and the plugin files it names."""
    folder = str(PurePosixPath(primary).parent)
    folder = "" if folder == "." else folder
    members = {primary}
    if PurePosixPath(folder).name.lower() in ("hooks",) and folder:
        members.update(path for path in blobs if path.startswith(folder + "/"))
    if text:
        for match in _PLUGIN_ROOT_REFERENCE.finditer(text):
            candidate = f"{root}/{match.group(1)}" if root else match.group(1)
            if candidate in blobs:
                members.add(candidate)
    return sorted(path for path in members if not excluded(path))


def code_module_members(primary: str, blobs: dict) -> list:
    """A module and the test files that name it by the usual conventions."""
    location = PurePosixPath(primary)
    stem, suffix, folder = location.stem, location.suffix, location.parent
    names = {f"test_{stem}{suffix}", f"{stem}_test{suffix}", f"{stem}.test{suffix}", f"{stem}.spec{suffix}"}
    members = {primary}
    for path in blobs:
        candidate = PurePosixPath(path)
        if candidate.name in names and (candidate.parent == folder or candidate.parent.name in
                                        ("tests", "test", "__tests__") or str(candidate.parent).startswith("tests")):
            members.add(path)
    return sorted(members)


def plan_packages(entries, scope: SourceScope = SourceScope(), repository: str = "") -> tuple:
    """(plans, skipped) for one tree: each unit a harness picks up, and paths left out with why.

    A symbolic link or a submodule inside a package makes that package a
    problem, never a silent omission. Licence and notice files are not
    packages; the licence stage reads them.
    """
    entries = tuple(entries)
    blobs = {entry.path: entry for entry in entries if entry.object_type == BLOB_TYPE}
    special = {entry.path: entry for entry in entries
               if entry.mode in (SYMLINK_MODE, SUBMODULE_MODE) or entry.object_type == COMMIT_TYPE}
    roots = plugin_roots(path for path in blobs if not excluded(path))
    skill_roots = {("" if str(PurePosixPath(path).parent) == "." else str(PurePosixPath(path).parent))
                   for path in blobs if PurePosixPath(path).name.lower() == "skill.md" and not excluded(path)}
    plans, skipped = [], []
    for path in sorted(blobs):
        if excluded(path):
            continue
        found = classify(path, roots) or declared_kind(path, scope)
        if found is None:
            continue
        kind, native = found
        if kind not in scope.kinds or not scope.admits(path):
            skipped.append((path, "outside_source_scope"))
            continue
        if kind == SKILL:
            root = "" if str(PurePosixPath(path).parent) == "." else str(PurePosixPath(path).parent)
            members = _skill_members(root, path, blobs, skill_roots)
            name = PurePosixPath(root).name if root else (repository.rsplit("/", 1)[-1] or "skill")
        elif kind == HOOK and native == "claude_hook_script":
            root, members, name = path, [path], PurePosixPath(path).name
        elif kind == HOOK:
            inside = _plugin_of(path, roots)
            root = inside[0] if inside else str(PurePosixPath(path).parent)
            members = hook_members(root, path, blobs)
            name = (PurePosixPath(root).name if root else repository.rsplit("/", 1)[-1]) + "-hooks"
        elif kind == CODE_MODULE:
            root = path
            members = code_module_members(path, blobs)
            name = PurePosixPath(path).name
        else:
            root = path
            members = [path]
            stem = item_stem(path)
            if kind == INSTRUCTION_FILE or kind == PLUGIN_MANIFEST or kind == MARKETPLACE or kind == PROTOCOL_SERVER:
                parent = PurePosixPath(path).parent
                while parent.name.startswith(".") and str(parent) != ".":
                    parent = parent.parent
                owner = parent.name if str(parent) != "." else repository.rsplit("/", 1)[-1]
                stem = f"{owner}-{stem}" if owner else stem
            name = stem
        problems = []
        if len(members) > MAXIMUM_PACKAGE_FILES:
            problems.append("package_too_many_files")
        folder_prefix = (root + "/") if kind in (SKILL, HOOK) and root else None
        if folder_prefix is not None and any(other.startswith(folder_prefix) for other in special):
            reasons = {special[other].mode for other in special if other.startswith(folder_prefix)}
            problems.append("symbolic_link_in_package" if SYMLINK_MODE in reasons else "submodule_in_package")
        inside = _plugin_of(path, roots)
        plugin = None
        if inside is not None and kind not in (PLUGIN_MANIFEST, MARKETPLACE):
            plugin = {"root": inside[0], "manifest": roots[inside[0]]}
        plans.append(PackagePlan(kind, root, path, tuple(members), name, native, plugin, tuple(problems)))
    return plans, skipped


def licence_paths(entries) -> dict:
    """Every licence and notice file of a tree, by path, with its object identity."""
    return {entry.path: entry.oid for entry in entries
            if entry.object_type == BLOB_TYPE and (is_licence_file(entry.path) or is_notice_file(entry.path))
            and not excluded(entry.path)}


def ancestors_licence_paths(member_paths, licence_index: dict) -> list:
    """The licence and notice files in any folder from each member up to the root."""
    wanted = set()
    folders = set()
    for path in member_paths:
        folder = PurePosixPath(path).parent
        while True:
            folders.add("" if str(folder) == "." else str(folder))
            if str(folder) in (".", ""):
                break
            folder = folder.parent
    for path in licence_index:
        parent = str(PurePosixPath(path).parent)
        if ("" if parent == "." else parent) in folders:
            wanted.add(path)
    return sorted(wanted)


def file_role(kind: str, package_root: str, path: str) -> str:
    """The catalogue_package/v1 role of one member, from its kind and its place in the package."""
    name = PurePosixPath(path).name.lower()
    suffix = PurePosixPath(name).suffix
    if is_licence_file(path) or is_notice_file(path):
        return "other"
    if kind == SKILL:
        relative = path[len(package_root) + 1:] if package_root else path
        first = _parts(relative)[0].lower() if len(_parts(relative)) > 1 else ""
        if name == "skill.md" and len(_parts(relative)) == 1:
            return "skill_definition"
        if first == "scripts" or suffix in _EXECUTABLE_SUFFIXES:
            return "skill_script"
        if first in ("references", "reference", "docs") or suffix in _TEXT_REFERENCE_SUFFIXES:
            return "skill_reference"
        return "skill_asset"
    if kind in (INSTRUCTION_FILE, RULES):
        return "instruction_file"
    if kind == SUBAGENT:
        return "subagent_definition"
    if kind == COMMAND:
        return "command"
    if kind == HOOK:
        return "hook"
    if kind in (PLUGIN_MANIFEST, MARKETPLACE):
        return "plugin_manifest"
    if kind == PROTOCOL_SERVER:
        return "protocol_server_configuration"
    if kind == CODE_MODULE:
        return "executable_tool" if suffix in _CODE_SUFFIXES else "other"
    return "other"


def package_path(kind: str, package_root: str, path: str) -> str:
    """Where one upstream member sits inside the package folder."""
    if kind in (SKILL, HOOK) and package_root:
        return path[len(package_root) + 1:] if path.startswith(package_root + "/") else PurePosixPath(path).name
    if kind == SKILL:
        return path
    return PurePosixPath(path).name


#: The documented native placement of each kind, per harness. {name} is the package name.
_PLACEMENTS = {
    SKILL: (("claude-code", ".claude/skills/{name}/"), ("codex", ".agents/skills/{name}/"),
            ("opencode", ".opencode/skills/{name}/"), ("pi", ".pi/skills/{name}/"),
            ("gemini-cli", ".gemini/skills/{name}/")),
    SUBAGENT: (("claude-code", ".claude/agents/{name}.md"), ("opencode", ".opencode/agent/{name}.md")),
    COMMAND: (("claude-code", ".claude/commands/{name}.md"), ("opencode", ".opencode/command/{name}.md")),
    HOOK: (("claude-code-plugin", "hooks/hooks.json"),),
    MARKETPLACE: (("claude-code", ".claude-plugin/marketplace.json"), ("codex", ".agents/plugins/marketplace.json")),
    PROTOCOL_SERVER: (("claude-code", ".mcp.json"), ("cursor", ".cursor/mcp.json"),
                      ("vscode-copilot", ".vscode/mcp.json")),
    CONTRACT_SCHEMA: (("reference", "schemas/{name}"),),
    CODE_MODULE: (("reference", "tools/{name}/"),),
}
_NATIVE_PLACEMENTS = {
    "agents_md": (("codex", "AGENTS.md"), ("opencode", "AGENTS.md"), ("goose", "AGENTS.md")),
    "agents_override_md": (("codex", "AGENTS.override.md"),),
    "claude_md": (("claude-code", "CLAUDE.md"),),
    "gemini_md": (("gemini-cli", "GEMINI.md"),),
    "goosehints": (("goose", ".goosehints"),),
    "copilot_instructions": (("copilot", ".github/copilot-instructions.md"),),
    "cursor_rule": (("cursor", ".cursor/rules/{name}.mdc"),),
    "cursorrules": (("cursor", ".cursorrules"),),
    "windsurfrules": (("windsurf", ".windsurfrules"),),
    "clinerules": (("cline", ".clinerules"),),
    "copilot_path_instructions": (("copilot", ".github/instructions/{name}.instructions.md"),),
    "folder_rule": (("claude-code", ".claude/rules/{name}.md"),),
    "copilot_agent": (("copilot", ".github/agents/{name}.agent.md"),),
    "copilot_chat_mode": (("copilot", ".github/chatmodes/{name}.chatmode.md"),),
    "copilot_prompt": (("copilot", ".github/prompts/{name}.prompt.md"),),
    "gemini_command": (("gemini-cli", ".gemini/commands/{name}.toml"),),
    "cursor_hooks": (("cursor", ".cursor/hooks.json"),),
    "claude_hook_script": (("claude-code", ".claude/hooks/{name}"),),
    "opencode_tool": (("opencode", ".opencode/tool/{name}"),),
    "opencode_plugin": (("opencode", ".opencode/plugin/{name}"),),
}
#: A plugin manifest's harness follows from the folder that holds it.
_MANIFEST_PLACEMENTS = {".claude-plugin": ("claude-code", "{name}/.claude-plugin/plugin.json"),
                        ".codex-plugin": ("codex", "{name}/.codex-plugin/plugin.json")}
_EXTENSION_PLACEMENT = ("gemini-cli", "{name}/gemini-extension.json")


#: How far a placement is known to work. Import establishes none of these beyond the
#: documented layout; native, translated, simulated and unsupported come from a harness
#: profile's own evidence (roadmap S-6.44), never from a file name.
SUPPORT_UNVERIFIED = "unverified"
PROJECT_SCOPE, PLUGIN_SCOPE, UPSTREAM_SCOPE = "project", "plugin", "upstream"


def placements(plan: PackagePlan) -> list:
    """Documented native targets for a package, with the upstream path the harness was found at.

    Each row carries the parts of the compatibility key that import can state:
    the harness, the path, the installation scope and the support state, which
    is always unverified here. The package format, component kind and native
    format are on the candidate record; the adapter, harness interface
    version, activation and permission mode belong to the placement evidence
    of the Harness Working Directory Compiler.
    """
    rows = [{"harness": "upstream", "path": plan.primary, "basis": "observed_upstream_path",
             "scope": UPSTREAM_SCOPE, "support": SUPPORT_UNVERIFIED}]
    options = _NATIVE_PLACEMENTS.get(plan.native_format) or _PLACEMENTS.get(plan.kind, ())
    if plan.kind == PLUGIN_MANIFEST:
        holder = PurePosixPath(plan.primary).parent.name.lower()
        options = ((_MANIFEST_PLACEMENTS[holder],) if holder in _MANIFEST_PLACEMENTS
                   else (_EXTENSION_PLACEMENT,))
    for harness, template in options:
        scope = PLUGIN_SCOPE if harness.endswith("-plugin") or plan.kind == PLUGIN_MANIFEST else PROJECT_SCOPE
        rows.append({"harness": harness, "path": template.format(name=plan.name), "basis": "documented_layout",
                     "scope": scope, "support": SUPPORT_UNVERIFIED})
    return rows
