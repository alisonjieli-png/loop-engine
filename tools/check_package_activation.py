"""Install a served package into each harness layout and verify the facts a harness needs to activate it.

The review panel's deterministic checks refuse format, licence, safety, effect,
secret and duplicate faults before a reviewer reads a candidate, and the daily
release check downloads one item and compares its digest. Neither of them
places a package where a harness reads it. This tool closes that gap without
starting a harness or a model: for every package it writes the files into a
scratch project in each documented layout and checks the activation facts,
which are the facts a harness reads before it can use the package at all.

```text
Activation facts, one row per package, bound to exact digests
├── bytes         every file reads back under its recorded digest and size and is its media type
├── entry         one entry file of the role the harness reads first
├── placed        the entry file exists at every documented native path with those bytes
├── skill         the frontmatter parses once, names the skill and describes it
├── instruction   the file holds instructions and no import climbs out of the package
├── subagent      the frontmatter parses once and describes the subagent
├── command       the body holds instructions; a TOML command carries a prompt
├── manifest      the manifest parses and every part it names exists inside it
├── protocol      every server names a command or an address
├── hook          every event runs a handler of a documented type whose script exists
└── authority     the files ask for no effect the item leaves undeclared
```

Each fact is pass, fail or unknown, and unknown is never a pass. The verdicts:

- activates: every fact passed and the files were placed in every documented layout;
- refused: at least one fact failed;
- unresolved: no fact failed and at least one is unknown, for example a
  native format without a documented layout, or an import that only the
  customer's own project can satisfy;
- no_native_activation: no file of a role a harness reads first, as for a
  contract schema or a code module a harness never loads on its own.

Two packages of one run that write different bytes to one named slot are a
set-level finding, kept beside the results and never a refusal of either
package. A file a harness reads at one fixed path, such as AGENTS.md, is
placed in a project of its own, because one project holds one of them by
design. When the entry sits in a single-file slot, such as a command, only
the entry goes into the slot and the other files of the package wait in a
side folder that no documented harness scans, because a licence notice
copied beside a command would become a second command.

A frontmatter that a strict YAML parser refuses but a line-by-line reader
recovers is unknown, not failed and not passed: the Claude Code
documentation itself shows `argument-hint: [pr-number] [priority]`, which
strict YAML refuses, and whether each harness recovers such a line is a
fact of its own loader. The laboratory under
`examples/31_failure_laboratory/packages/` holds one fixture for each way a
package can fail these facts; each names the refusal codes it expects, and
its controls must activate.

    PYTHONPATH=src:tools python tools/check_package_activation.py \\
        --bundle ~/baltor-bundles/daily-2026-09-26-10 --output REPORT.json --compact
    PYTHONPATH=src:tools python tools/check_package_activation.py \\
        --laboratory examples/31_failure_laboratory/packages --output REPORT.json

The tool writes only under its scratch folder and the report path. It reads
no network, calls no model and grants no effect. With `--observe-listing` it
also starts one client process twice: OpenCode's own skill listing, which
starts no model turn, first in an empty project (the no-extra-component
baseline) and then in a project that holds only the placed skill folders.
Loaded, as that listing reports it, stays a separate fact beside the
activation facts and never changes a verdict. What a harness does after the
load, such as following the instructions or running a script, is outside
these facts; the decision record of September 26, 2026 under docs/research/
compares the verification approaches that would cover it.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
import tempfile

try:
    import tomllib as _toml
except ImportError:  # Python 3.10 reads TOML through the tomli package the environment ships
    import tomli as _toml
import yaml

HERE = Path(__file__).resolve().parent
for _folder in (HERE, HERE.parent / "src"):
    if str(_folder) not in sys.path:
        sys.path.insert(0, str(_folder))

from install_selected_material import (  # noqa: E402
    CLIENT_LAYOUT_PROFILES, OPENCODE_PROFILE, InstallRefusal, TransferLimits, native_name, observe_client_listing,
    render_skill_header,
)
from licensed_import.harness_kinds import PackagePlan, item_stem, placements  # noqa: E402
from licensed_import.records import ALLOWED_LICENCES, PACKAGE_KINDS  # noqa: E402
from loop_engine.core.facets import EFFECTS  # noqa: E402
from loop_engine.core.harness_intelligence import KINDS  # noqa: E402
from loop_engine.core.service_runtime.catalogue_bundle import read_bundle  # noqa: E402
from loop_engine.core.service_runtime.catalogue_packages import (  # noqa: E402
    EXECUTABLE_ROLES, FILE_ROLES, PACKAGE_RECORD_TYPE, placement_path, sha256_hex,
)
from loop_engine.core.service_runtime.http_entrypoint import DEFAULT_FAMILY_POLICY, HostLicensePolicy  # noqa: E402
from loop_engine.core.service_runtime.records import ServiceRuntimeError  # noqa: E402

REPORT_RECORD_TYPE = "package_activation_report/v1"
RESULT_RECORD_TYPE = "package_activation_result/v1"
LABORATORY_PACKAGE_RECORD_TYPE = "laboratory_package/v1"
LABORATORY_SET_RECORD_TYPE = "laboratory_package_set/v1"
LABORATORY_MANIFEST, LABORATORY_SET_MANIFEST = "package.json", "set.json"
REQUIRED_MANIFEST_FIELDS = frozenset({"record_type", "identity", "kind", "styles", "purpose", "license",
                                      "declared_effects", "breaks", "expected_refusals", "files"})
OPTIONAL_MANIFEST_FIELDS = frozenset({"body_form"})
FILE_ROW_FIELDS = frozenset({"path", "role", "media_type", "digest", "size_bytes", "stored_as"})
#: File names a harness loads as instructions from the folder a session works in.
LIVE_INSTRUCTION_NAMES = frozenset({"agents.md", "agents.override.md", "claude.md", "claude.local.md", "gemini.md",
                                    ".goosehints", ".cursorrules", ".windsurfrules", ".clinerules"})
PASS, FAIL, UNKNOWN = "pass", "fail", "unknown"
ACTIVATES, REFUSED, UNRESOLVED, NO_NATIVE_ACTIVATION = "activates", "refused", "unresolved", "no_native_activation"
VERDICTS = (ACTIVATES, REFUSED, UNRESOLVED, NO_NATIVE_ACTIVATION)
#: The role a harness reads first, by package kind, and the fallback order for a package without one.
ENTRY_ROLE_BY_KIND = {"skill": "skill_definition", "instruction_file": "instruction_file",
                      "rules": "instruction_file", "subagent": "subagent_definition", "command": "command",
                      "hook": "hook", "plugin_manifest": "plugin_manifest", "marketplace": "plugin_manifest",
                      "protocol_server_configuration": "protocol_server_configuration",
                      "harness_settings": "configuration"}
ENTRY_ROLES = ("skill_definition", "instruction_file", "subagent_definition", "command", "plugin_manifest",
               "protocol_server_configuration", "hook", "configuration")
FRONTMATTER_ROLES = ("skill_definition", "instruction_file", "subagent_definition", "command")
NATIVE_NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+[^)]*)?\)")
#: An import token as Claude Code reads it: an @ that starts a word, then a path-like token.
IMPORT = re.compile(r"(?:^|(?<=\s))@((?:~/|/|(?:\.{1,2}/)+)?[A-Za-z0-9_.][A-Za-z0-9._/~-]*)")
FENCED_CODE = re.compile(r"(?ms)^[ \t]*(`{3,}|~{3,})[^\n]*\n.*?^[ \t]*\1[ \t]*$")
INLINE_CODE = re.compile(r"`[^`\n]*`")
PLUGIN_ROOT = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}/([A-Za-z0-9._/@+-]{1,200})")
PROJECT_DIR = re.compile(r"\$\{CLAUDE_PROJECT_DIR\}/([A-Za-z0-9._/@+-]{1,200})")
HEADING_OR_RULE = re.compile(r"(?m)^\s*(?:#{1,6}\s.*|-{3,}|\*{3,}|_{3,})\s*$")
HTML_COMMENT = re.compile(r"(?s)<!--.*?-->")
LENIENT_LINE = re.compile(r"([A-Za-z0-9_][A-Za-z0-9_.-]*)[ \t]*:(?:[ \t]+(.*))?")
#: A token ends a sentence more often than a path does; these characters are cut from its end.
TRAILING_PUNCTUATION = ".,;:!?)]}'\""
#: The roles whose harness expands an @ import: Claude Code reads imports in memory files and
#: file references in commands. A skill or subagent body is read as text, so an @ there is prose.
IMPORTING_ROLES = ("instruction_file", "command")
#: Where the check places the files of a package whose entry sits in a single-file slot: a folder
#: no documented harness scans, so a licence notice never becomes a second command or rule.
SIDE_FOLDER = ".baltor/packages"
#: Manifest fields whose relative paths are parts of the plugin, as the manifest reference documents them.
MANIFEST_PART_FIELDS = ("agents", "commands", "skills", "hooks", "mcpServers", "lspServers", "outputStyles",
                        "workflows")
REMOTE_PART_PREFIXES = ("https://", "http://", "git@", "github:", "npm:")
#: Claude Code tools whose pre-approval asks for an effect the item must declare.
TOOL_EFFECTS = {"bash": "spawns_process", "write": "writes_fs", "edit": "writes_fs", "multiedit": "writes_fs",
                "notebookedit": "writes_fs", "webfetch": "network", "websearch": "network",
                "read": "reads_fs", "grep": "reads_fs", "glob": "reads_fs", "ls": "reads_fs"}
#: The hook handler types Claude Code documents, each with the field that makes it act and its effect.
HOOK_HANDLERS = {"command": ("command", "spawns_process"), "http": ("url", "network"),
                 "mcp_tool": ("tool", ""), "prompt": ("prompt", ""), "agent": ("prompt", "")}
PARTIAL_SUFFIX = ".partial"
MAXIMUM_TEXT_BYTES = 8 * 1024 * 1024
JSON_ERRORS = (ValueError, RecursionError)
SCRATCH_PREFIX = "package-activation-"
SENTINEL_NAME = "zz-named-slot-probe"
SHARED_PROJECT, OWN_PROJECT = "shared", "own"
LISTING_RECORD_TYPE = "package_activation_listing/v1"
#: The one client whose own skill listing starts no model turn (recorded in install_selected_material.py).
LISTING_HARNESS, LISTING_ROOT = "opencode", ".opencode/skills"
#: The installer removes this variable from a client's environment; this check holds no service key at all.
LISTING_KEY_VARIABLE = "BALTOR_SERVICE_KEY"
LISTING_LIMITS = TransferLimits(listing_timeout_seconds=600.0, maximum_listing_bytes=512 * 1024 * 1024,
                                maximum_watched_paths=1_000_000)
WRITTEN, HELD_BY_ANOTHER, NOT_PLACED = "written", "held_by_another_package", "not_placed"


class ActivationCheckError(Exception):
    """A request this tool refuses before any file is written."""


@dataclass(frozen=True)
class Finding:
    code: str
    state: str
    path: str = ""
    detail: str = ""

    def to_dict(self):
        return {"code": self.code, "state": self.state, "path": self.path, "detail": self.detail}


@dataclass(frozen=True)
class FileUnderTest:
    path: str
    role: str
    media_type: str
    size_bytes: int
    digest: str
    payload: "bytes | None"
    claim: str = ""

    @property
    def text(self):
        if self.payload is None:
            return None
        try:
            return self.payload.decode("utf-8")
        except UnicodeDecodeError:
            return None


@dataclass(frozen=True)
class PackageUnderTest:
    identity: str
    kind: str
    styles: tuple
    purpose: str
    license: str
    declared_effects: tuple
    body_form: str
    served_digest: str
    files: tuple
    source: str
    expected_refusals: tuple = ()
    problems: tuple = ()

    @property
    def paths(self):
        return {entry.path for entry in self.files}


# ---------------------------------------------------------------------------
# Reading packages: a release bundle, or laboratory fixture folders
# ---------------------------------------------------------------------------

def verify_claim(payload, digest, size_bytes):
    """Empty text when the bytes are what the record claims, otherwise the code of the false claim."""
    if payload is None:
        return "body_missing"
    if sha256_hex(payload) != digest:
        return "body_digest_mismatch"
    if len(payload) != size_bytes:
        return "body_size_mismatch"
    return ""


def bundle_packages(folder, limit=None):
    """Every package of a release bundle with its verified bytes, in identity order."""
    policy = HostLicensePolicy(accepted_licenses=tuple(ALLOWED_LICENCES))
    bundle = read_bundle(Path(folder).resolve(), license_policy=policy, family_policy=DEFAULT_FAMILY_POLICY,
                         verify_blobs=False)
    blobs = bundle.blobs()
    packages = []
    for entry in bundle.items[:limit] if limit else bundle.items:
        files = []
        for file in entry.package.files:
            payload = None
            try:
                payload = blobs.read(file.digest, file.size_bytes)
                claim = verify_claim(payload, file.digest, file.size_bytes)
            except ServiceRuntimeError as error:
                claim = error.code
            files.append(FileUnderTest(file.path, file.role, file.media_type, file.size_bytes, file.digest,
                                       payload, claim))
        item = entry.item
        packages.append(PackageUnderTest(item.identity, item.kind, tuple(item.styles), item.purpose,
                                         item.license_name, tuple(item.declared_effects), entry.package.body_form,
                                         entry.package.served_digest, tuple(files), "bundle:" + bundle.digest))
    return bundle.digest, packages


def _strict_json(payload, where):
    """Strict JSON with one value per key; a repeated key is ambiguous data, never a silent override."""
    def pairs(items):
        keys = [key for key, _value in items]
        if len(set(keys)) != len(keys):
            raise ValueError(f"{where}: a key appears twice")
        return dict(items)
    return json.loads(payload, object_pairs_hook=pairs)


def _laboratory_manifest(folder, name):
    path = Path(folder) / name
    if not path.is_file():
        raise ActivationCheckError(f"{folder}: laboratory fixture has no {name}")
    try:
        return _strict_json(path.read_bytes(), str(path))
    except JSON_ERRORS as error:
        raise ActivationCheckError(f"{path}: {error}") from None


def stray_partials(folder):
    """Every leftover of an interrupted installation inside a fixture folder."""
    return [stray.relative_to(folder).as_posix() for stray in sorted(Path(folder).rglob("*" + PARTIAL_SUFFIX))]


def laboratory_package(folder):
    """One laboratory fixture folder: its manifest names the files, and the folder holds the bytes.

    A manifest may pin a digest or size for a file. The pin is a claim about the
    bytes, checked like the bundle's own claims, so a fixture can state a false
    claim on purpose. A named file that is absent stays absent, as an
    interrupted installation leaves it.
    """
    folder = Path(folder)
    manifest = _laboratory_manifest(folder, LABORATORY_MANIFEST)
    if (not isinstance(manifest, dict) or not REQUIRED_MANIFEST_FIELDS <= set(manifest)
            or not set(manifest) <= REQUIRED_MANIFEST_FIELDS | OPTIONAL_MANIFEST_FIELDS
            or manifest["record_type"] != LABORATORY_PACKAGE_RECORD_TYPE):
        raise ActivationCheckError(f"{folder}: a laboratory manifest is {LABORATORY_PACKAGE_RECORD_TYPE} "
                                   f"with {sorted(REQUIRED_MANIFEST_FIELDS)} and at most "
                                   f"{sorted(OPTIONAL_MANIFEST_FIELDS)}")
    if manifest["kind"] not in KINDS:
        raise ActivationCheckError(f"{folder}: an item kind is one of {KINDS}")
    if any(effect not in EFFECTS for effect in manifest["declared_effects"]):
        raise ActivationCheckError(f"{folder}: declared effects come from {EFFECTS}")
    if manifest["styles"] and manifest["styles"][0] not in PACKAGE_KINDS:
        raise ActivationCheckError(f"{folder}: the first style is a package kind from {PACKAGE_KINDS}")
    files = []
    for row in manifest["files"]:
        if (not isinstance(row, dict) or not {"path", "role", "media_type"} <= set(row)
                or not set(row) <= FILE_ROW_FIELDS or row["role"] not in FILE_ROLES):
            raise ActivationCheckError(f"{folder}: each file names path, role from {FILE_ROLES} and media_type, "
                                       f"and at most {sorted(FILE_ROW_FIELDS)}")
        placement_path(row["path"])
        source = folder / placement_path(row.get("stored_as", row["path"]))
        payload = source.read_bytes() if source.is_file() and not source.is_symlink() else None
        digest = row.get("digest") or (sha256_hex(payload) if payload is not None else "0" * 64)
        size = row.get("size_bytes", len(payload) if payload is not None else 0)
        files.append(FileUnderTest(row["path"], row["role"], row["media_type"], size, digest, payload,
                                   verify_claim(payload, digest, size)))
    problems = tuple(("partial_file_present", path) for path in stray_partials(folder))
    files.sort(key=lambda entry: entry.path)
    body_form = manifest.get("body_form", "package")
    if body_form == "file" and len(files) == 1:
        served = files[0].digest
    else:
        served = sha256_hex(json.dumps(
            {"record_type": PACKAGE_RECORD_TYPE,
             "files": [{"path": f.path, "digest": f.digest, "size_bytes": f.size_bytes,
                        "media_type": f.media_type, "role": f.role} for f in files]},
            sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    return PackageUnderTest(manifest["identity"], manifest["kind"], tuple(manifest["styles"]), manifest["purpose"],
                            manifest["license"], tuple(manifest["declared_effects"]), body_form, served,
                            tuple(files), "laboratory:" + folder.name, tuple(manifest["expected_refusals"]),
                            problems)


def live_instruction_files(folder):
    """Every file in a laboratory folder that a harness would load as instructions where it lies.

    Codex reads AGENTS.md and Claude Code reads CLAUDE.md in the folders a
    session works in, so a fixture stored under such a name would act on the
    people who develop this repository. A fixture stores that body under
    another name and gives the package path in its manifest (`stored_as`).
    """
    return [path.relative_to(folder).as_posix() for path in sorted(Path(folder).rglob("*"))
            if path.name.lower() in LIVE_INSTRUCTION_NAMES]


def laboratory_fixtures(folder):
    """(fixture name, packages, expected refusals) for every fixture folder of a laboratory."""
    live = live_instruction_files(folder)
    if live:
        raise ActivationCheckError(f"{folder}: a laboratory holds no live instruction file; found {live}")
    fixtures = []
    for fixture_folder in sorted(Path(folder).iterdir()):
        if not fixture_folder.is_dir():
            continue
        if (fixture_folder / LABORATORY_SET_MANIFEST).is_file():
            manifest = _laboratory_manifest(fixture_folder, LABORATORY_SET_MANIFEST)
            if (not isinstance(manifest, dict) or manifest.get("record_type") != LABORATORY_SET_RECORD_TYPE
                    or not isinstance(manifest.get("packages"), list) or not manifest["packages"]):
                raise ActivationCheckError(f"{fixture_folder}: a set manifest is {LABORATORY_SET_RECORD_TYPE}")
            packages = tuple(laboratory_package(fixture_folder / name) for name in manifest["packages"])
            fixtures.append((fixture_folder.name, packages, tuple(manifest.get("expected_refusals", ()))))
        elif (fixture_folder / LABORATORY_MANIFEST).is_file():
            package = laboratory_package(fixture_folder)
            fixtures.append((fixture_folder.name, (package,), package.expected_refusals))
    if not fixtures:
        raise ActivationCheckError(f"{folder}: no laboratory fixture found")
    return fixtures


# ---------------------------------------------------------------------------
# Activation facts
# ---------------------------------------------------------------------------

def split_frontmatter(text):
    """(header text or None, body, error code or empty). A file may carry no frontmatter at all."""
    if not text.startswith("---"):
        return None, text, ""
    first = text.split("\n", 1)
    if first[0].strip() != "---" or len(first) < 2:
        return None, text, "frontmatter_unterminated"
    rest = first[1]
    match = re.search(r"(?m)^---[ \t]*$", rest)
    if match is None:
        return None, text, "frontmatter_unterminated"
    return rest[:match.start()], rest[match.end():], ""


def parse_frontmatter(header):
    """(mapping, error code). A repeated key is ambiguous data and refused."""
    try:
        tree = yaml.compose(header)
        if tree is None:
            return {}, ""
        if not isinstance(tree, yaml.MappingNode):
            return None, "frontmatter_not_a_mapping"
        keys = [key.value for key, _value in tree.value]
        if len(set(keys)) != len(keys):
            return None, "frontmatter_ambiguous"
        value = yaml.safe_load(header)
    except (yaml.YAMLError, RecursionError, ValueError):
        return None, "frontmatter_invalid"
    return (value if isinstance(value, dict) else None), ("" if isinstance(value, dict) else "frontmatter_not_a_mapping")


def lenient_frontmatter(header):
    """(mapping or None, error code): one `key: value` per line, as a forgiving frontmatter reader takes it.

    A strict YAML parser refuses a line such as `argument-hint: [file] [mode]`,
    which the Claude Code documentation itself shows. Whether a harness
    recovers such a file is not known here, so a header that only this reader
    accepts yields an unknown fact, never a pass. A repeated key stays
    ambiguous, and a header with no key line stays invalid.
    """
    mapping = {}
    for line in header.splitlines():
        if not line.strip() or line.lstrip().startswith("#") or line[:1] in (" ", "\t", "-"):
            continue
        match = LENIENT_LINE.fullmatch(line.rstrip())
        if match is None:
            return None, "frontmatter_invalid"
        key, value = match.group(1), (match.group(2) or "").strip()
        if key in mapping:
            return None, "frontmatter_ambiguous"
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        mapping[key] = value
    return (mapping, "") if mapping else (None, "frontmatter_invalid")


def body_has_instructions(body):
    """Whether anything but headings, rules and comments is left for a model to follow."""
    return bool(HEADING_OR_RULE.sub("", HTML_COMMENT.sub("", body)).strip())


def scannable_text(text):
    """The text a harness parses for references; fenced code blocks and code spans are left out."""
    return INLINE_CODE.sub(" ", FENCED_CODE.sub("\n", text))


def path_like(target):
    """A token that names a file: it has a folder separator or a suffix, and no character a path never holds."""
    if any(character in target for character in "<>{}$ \t\"'|"):
        return False
    return "/" in target or "." in PurePosixPath(target).name


def _relative_inside(base, target, paths):
    """(normalized path or None when it escapes, exists in the package)."""
    pure = PurePosixPath(target.split("#", 1)[0].split("?", 1)[0])
    if pure.is_absolute() or ".." in pure.parts or target.startswith("~"):
        return None, False
    combined = (PurePosixPath(base).parent / pure).as_posix() if base else pure.as_posix()
    combined = combined[2:] if combined.startswith("./") else combined
    if combined in paths:
        return combined, True
    prefix = combined.rstrip("/") + "/"
    return combined, any(path.startswith(prefix) for path in paths)


def import_like(target):
    """An @ token that names a file: an explicit relative or home prefix, or a file name with a suffix.

    `@tanstack/react-query` names a package and `@alice` names a person; neither is an import.
    """
    if not path_like(target):
        return False
    return target.startswith(("./", "../", "~/", "/")) or "." in PurePosixPath(target).name.strip(".")


def reference_findings(role, path, text, paths):
    """Links and imports of an entry file, graded by what the harness would find after installation.

    A skill, command or subagent ships what its links name: a relative target
    that the package lacks is a missing dependency, and one that climbs out of
    the package, names an absolute path or the home folder escapes it. An
    instruction file's links are prose. An @ import is expanded only in an
    instruction file (relative to the file) and in a command (relative to the
    customer's project), so an import the package lacks is unknown, because
    the customer's project may hold it, while an import that climbs out of
    the project or names the home folder is an outside import a served file
    must not make. Code blocks and code spans are left out, as Claude Code
    documents for imports.
    """
    findings = []
    scanned = scannable_text(text)
    targets = []
    if role in IMPORTING_ROLES:
        targets += [("import", value.rstrip(TRAILING_PUNCTUATION)) for value in IMPORT.findall(scanned)]
    if role != "instruction_file":
        targets += [("link", value) for value in LINK.findall(scanned)]
    seen = set()
    for form, target in targets:
        if (target in seen or target.startswith(("https://", "http://", "#", "mailto:"))
                or not (import_like(target) if form == "import" else path_like(target))):
            continue
        seen.add(target)
        base = path if not (form == "import" and role == "command") else ""
        inside, exists = _relative_inside(base, target, paths)
        if inside is None:
            findings.append(Finding("referenced_path_escapes", FAIL, path, f"{target} leaves the package"))
        elif exists:
            continue
        elif form == "import":
            findings.append(Finding("import_outside_package", UNKNOWN, path,
                                    f"{target} is imported but not in the package; the customer's project may hold it"))
        else:
            findings.append(Finding("referenced_file_missing", FAIL, path,
                                    f"{target} is named by a {form} but not in the package"))
    return findings


def tool_effects_of(tools):
    """The effects that a tools or allowed-tools value pre-approves."""
    needed = set()
    values = [tools] if isinstance(tools, str) else tools if isinstance(tools, list) else []
    for value in values:
        if not isinstance(value, str):
            continue
        for token in re.split(r"[\s,]+", value):
            effect = TOOL_EFFECTS.get(token.split("(", 1)[0].strip().lower())
            if effect:
                needed.add(effect)
    return needed


def hook_handlers(entries):
    """(type, handler) for every handler of one event that does something, by the documented handler types."""
    handlers = []
    for entry in entries if isinstance(entries, list) else []:
        if not isinstance(entry, dict):
            continue
        inner = entry.get("hooks") if isinstance(entry.get("hooks"), list) else [entry]
        for hook in inner:
            if not isinstance(hook, dict):
                continue
            kind = hook.get("type", "command" if "command" in hook else "")
            field = HOOK_HANDLERS.get(kind, ("", ""))[0]
            if field and isinstance(hook.get(field), str) and hook[field].strip():
                handlers.append((kind, hook))
    return handlers


def hook_effects(document, path, paths, findings):
    """The effects a hook configuration asks for; a silent event and a missing script are failures."""
    needed = set()
    hooks = document.get("hooks") if isinstance(document, dict) else None
    if not isinstance(hooks, dict) or not hooks:
        findings.append(Finding("hook_does_nothing", FAIL, path, "the configuration registers no event"))
        return needed
    for event, entries in hooks.items():
        handlers = hook_handlers(entries)
        if not handlers:
            findings.append(Finding("hook_does_nothing", FAIL, path, f"event {event} runs no handler"))
            continue
        for kind, handler in handlers:
            effect = HOOK_HANDLERS[kind][1]
            if effect:
                needed.add(effect)
            if kind != "command":
                continue
            command = handler["command"]
            for script in PROJECT_DIR.findall(command):
                findings.append(Finding("hook_script_outside_package", UNKNOWN, path,
                                        f"event {event} runs {script} from the customer's project"))
            scripts = PLUGIN_ROOT.findall(command) + [token[2:] for token in command.split() if token.startswith("./")]
            for script in scripts:
                inside, exists = _relative_inside("", script, paths)
                if inside is None:
                    findings.append(Finding("part_path_escapes", FAIL, path, f"{script} leaves the package"))
                elif not exists:
                    findings.append(Finding("hook_script_missing", FAIL, path,
                                            f"{script} is run by event {event} but not in the package"))
    return needed


def server_effects(servers, path, findings):
    needed = set()
    for name, server in servers.items():
        if not isinstance(server, dict):
            findings.append(Finding("protocol_server_invalid", FAIL, path, f"server {name} is not an object"))
            continue
        if isinstance(server.get("command"), str) and server["command"].strip():
            needed.add("spawns_process")
        elif isinstance(server.get("url"), str) and server["url"].strip():
            needed.add("network")
        else:
            findings.append(Finding("protocol_server_invalid", FAIL, path,
                                    f"server {name} names neither a command nor an address"))
    return needed


def _manifest_part_paths(value):
    """Every relative path string a manifest field names as a part; inline objects are handled by the caller."""
    if isinstance(value, str):
        return [] if value.startswith(REMOTE_PART_PREFIXES) or value in (".", "./") else [value]
    if isinstance(value, list):
        return [part for row in value for part in _manifest_part_paths(row)]
    if isinstance(value, dict):
        parts = []
        for row in value.values():
            if isinstance(row, dict) and isinstance(row.get("source"), str):
                parts.extend(_manifest_part_paths(row["source"]))
        return parts
    return []


def plugin_manifest_facts(document, path, paths, findings):
    """The facts of a plugin.json: a name, and every part it names present inside the package."""
    needed = set()
    name = document.get("name")
    if not isinstance(name, str) or not name.strip() or re.search(r"[\s@:/\\]", name):
        findings.append(Finding("manifest_name_missing", FAIL, path,
                                "the manifest names no plugin, or the name holds a space, @, : or a path separator"))
    for key in MANIFEST_PART_FIELDS:
        value = document.get(key)
        if key == "hooks" and isinstance(value, dict):
            needed.update(hook_effects(value if "hooks" in value else {"hooks": value}, path, paths, findings))
            continue
        if key == "mcpServers" and isinstance(value, dict):
            needed.update(server_effects(value, path, findings))
            continue
        for part in _manifest_part_paths(value):
            if not part.startswith("./"):
                findings.append(Finding("manifest_part_not_relative", FAIL, path,
                                        f"{key} names {part}, and a component path starts with ./"))
                continue
            inside, exists = _relative_inside("", part, paths)
            if inside is None:
                findings.append(Finding("part_path_escapes", FAIL, path, f"{part} leaves the package"))
            elif not exists:
                findings.append(Finding("manifest_part_missing", FAIL, path, f"{part} is named but not in the package"))
    return needed


def marketplace_facts(document, path, paths, findings):
    """The facts of a marketplace.json: a name and plugin entries whose local sources exist inside the package."""
    if not isinstance(document.get("name"), str) or not document["name"].strip():
        findings.append(Finding("manifest_name_missing", FAIL, path, "the marketplace names nothing"))
    plugins = document.get("plugins")
    if not isinstance(plugins, list) or not plugins:
        findings.append(Finding("marketplace_lists_no_plugin", FAIL, path, "the marketplace lists no plugin"))
        return
    for row in plugins:
        if not isinstance(row, dict) or not isinstance(row.get("name"), str) or not row["name"].strip():
            findings.append(Finding("marketplace_entry_invalid", FAIL, path, "a plugin entry names no plugin"))
            continue
        source = row.get("source")
        if isinstance(source, str) and not source.startswith(REMOTE_PART_PREFIXES):
            inside, exists = _relative_inside("", source, paths)
            if inside is None:
                findings.append(Finding("part_path_escapes", FAIL, path, f"{source} leaves the package"))
            elif not exists:
                findings.append(Finding("manifest_part_missing", FAIL, path,
                                        f"{source} is the source of {row['name']} but not in the package"))
        elif not isinstance(source, (str, dict)):
            findings.append(Finding("marketplace_entry_invalid", FAIL, path, f"{row['name']} names no source"))


def entry_facts(package, entry, kind, native):
    """The facts of the one entry file, by its role and the native format the package kind names."""
    findings, needed = [], set()
    text = entry.text
    if text is None:
        return [Finding("entry_not_text", FAIL, entry.path, "the entry file is not UTF-8 text")], needed
    role = entry.role
    if role in FRONTMATTER_ROLES and not (role == "command" and entry.media_type == "application/toml"):
        header, body, error = split_frontmatter(text)
        if error:
            return [Finding(error, FAIL, entry.path, "the frontmatter never closes")], needed
        mapping, error = ({}, "") if header is None else parse_frontmatter(header)
        if error == "frontmatter_invalid":
            mapping, error = lenient_frontmatter(header)
            if not error:
                findings.append(Finding("frontmatter_not_strict_yaml", UNKNOWN, entry.path,
                                        "a strict YAML parser refuses the frontmatter and a line-by-line reader "
                                        "recovers it; whether each harness recovers it needs its own loader"))
        if error:
            detail = {"frontmatter_ambiguous": "a key appears twice, and parsers disagree on which value wins",
                      }.get(error, "the frontmatter does not parse as one mapping of keys to values")
            return [Finding(error, FAIL, entry.path, detail)], needed
        if role == "skill_definition":
            if header is None and package.body_form == "package":
                findings.append(Finding("skill_frontmatter_missing", FAIL, entry.path,
                                        "a packaged skill carries its own name and description"))
            elif header is not None:
                name, description = mapping.get("name"), mapping.get("description")
                if not isinstance(name, str) or not name.strip():
                    findings.append(Finding("skill_name_missing", FAIL, entry.path,
                                            "the frontmatter names no skill; Codex, Pi and the Agent Skills "
                                            "specification require the name"))
                elif NATIVE_NAME.fullmatch(name) is None or len(name) > 64:
                    findings.append(Finding("skill_name_not_native", FAIL, entry.path,
                                            "a skill name is lowercase letters, digits and hyphens, at most 64 characters"))
                if not isinstance(description, str) or not description.strip():
                    findings.append(Finding("skill_description_missing", FAIL, entry.path,
                                            "the frontmatter describes nothing"))
        if role == "subagent_definition":
            if header is None:
                findings.append(Finding("subagent_frontmatter_missing", FAIL, entry.path,
                                        "a subagent definition opens with frontmatter"))
            else:
                description = mapping.get("description")
                if not isinstance(description, str) or not description.strip():
                    findings.append(Finding("subagent_description_missing", FAIL, entry.path,
                                            "the frontmatter describes nothing"))
                name = mapping.get("name")
                if native in ("agent_definition", "plugin_agent") and (not isinstance(name, str) or not name.strip()):
                    findings.append(Finding("subagent_name_missing", FAIL, entry.path,
                                            "a Claude Code subagent names itself"))
        if role == "command" and native == "gemini_command":
            findings.append(Finding("command_format_mismatch", FAIL, entry.path, "a Gemini command is TOML"))
        if mapping:
            needed.update(tool_effects_of(mapping.get("allowed-tools", mapping.get("tools"))))
            if isinstance(mapping.get("hooks"), dict):
                needed.update(hook_effects({"hooks": mapping["hooks"]}, entry.path, package.paths, findings))
        if not body_has_instructions(body):
            findings.append(Finding("body_has_no_instructions", FAIL, entry.path,
                                    "the entry file loads but holds no instruction a model could follow"))
        findings.extend(reference_findings(role, entry.path, body, package.paths))
        return findings, needed
    if role == "command":
        try:
            document = _toml.loads(text)
        except (_toml.TOMLDecodeError, RecursionError):
            return [Finding("command_toml_invalid", FAIL, entry.path, "the command does not parse as TOML")], needed
        prompt = document.get("prompt") if isinstance(document, dict) else None
        if not isinstance(prompt, str) or not prompt.strip():
            findings.append(Finding("command_prompt_missing", FAIL, entry.path,
                                    "a TOML command carries a top-level prompt; Gemini CLI requires it, and no "
                                    "documented layout reads a TOML command without one"))
        if native != "gemini_command":
            findings.append(Finding("command_format_mismatch", FAIL, entry.path,
                                    "a TOML command placed where the harness reads Markdown commands"))
        return findings, needed
    try:
        document = _strict_json(entry.payload, entry.path)
    except JSON_ERRORS as error:
        code = "manifest_ambiguous" if "appears twice" in str(error) else "manifest_json_invalid"
        return [Finding(code, FAIL, entry.path, "the file is not strict JSON with one value per key")], needed
    if not isinstance(document, dict):
        return [Finding("manifest_not_an_object", FAIL, entry.path, "the file is not a JSON object")], needed
    if role == "plugin_manifest":
        if PurePosixPath(entry.path).name == "marketplace.json":
            marketplace_facts(document, entry.path, package.paths, findings)
        else:
            needed.update(plugin_manifest_facts(document, entry.path, package.paths, findings))
    elif role == "protocol_server_configuration":
        servers = document.get("mcpServers")
        if not isinstance(servers, dict) or not servers:
            findings.append(Finding("protocol_servers_missing", FAIL, entry.path, "no mcpServers object"))
        else:
            needed.update(server_effects(servers, entry.path, findings))
    elif role == "hook":
        needed.update(hook_effects(document, entry.path, package.paths, findings))
    elif role == "configuration":
        permissions = document.get("permissions")
        if isinstance(permissions, dict):
            needed.update(tool_effects_of(permissions.get("allow")))
            if permissions.get("defaultMode") in ("bypassPermissions", "acceptEdits"):
                needed.add("writes_fs")
        if isinstance(document.get("hooks"), dict):
            needed.update(hook_effects({"hooks": document["hooks"]}, entry.path, package.paths, findings))
    return findings, needed


def media_claim_holds(file):
    """Whether the bytes are what the recorded media type says: JSON parses, and text is UTF-8."""
    if file.media_type == "application/json":
        try:
            _strict_json(file.payload, file.path)
        except JSON_ERRORS:
            return False
        return True
    return not (file.media_type.startswith("text/") and file.text is None)


def configuration_facts(package, entry, findings):
    """The facts of every hook or protocol server configuration the package holds besides its entry.

    A plugin reads `hooks/hooks.json` and `.mcp.json` from its own root, so a
    silent event, a missing script or a server with nothing to start fails
    there exactly as it would in an entry file.
    """
    needed = set()
    for file in package.files:
        if (file is entry or file.payload is None or file.claim or not file.path.endswith(".json")
                or file.role not in ("hook", "protocol_server_configuration")):
            continue
        try:
            document = _strict_json(file.payload, file.path)
        except JSON_ERRORS:
            findings.append(Finding("manifest_json_invalid", FAIL, file.path, "the file is not strict JSON"))
            continue
        if not isinstance(document, dict):
            findings.append(Finding("manifest_not_an_object", FAIL, file.path, "the file is not a JSON object"))
        elif file.role == "hook":
            needed.update(hook_effects(document, file.path, package.paths, findings))
        elif isinstance(document.get("mcpServers"), dict):
            needed.update(server_effects(document["mcpServers"], file.path, findings))
        else:
            findings.append(Finding("protocol_servers_missing", FAIL, file.path, "no mcpServers object"))
    return needed


def package_kind(package):
    """(package kind, native format) from the styles, or from the item kind of a single-file item."""
    if package.styles and package.styles[0] in PACKAGE_KINDS:
        return package.styles[0], (package.styles[1] if len(package.styles) > 1 else "")
    if package.kind == "skill":
        return "skill", "agent_skill"
    return "instruction_file", "agents_md"


def select_entry(package, kind):
    """(entry file or None, ambiguity finding or None): the file of the role the harness reads first."""
    role = ENTRY_ROLE_BY_KIND.get(kind)
    candidates = [file for file in package.files if file.role == role] if role else []
    if not candidates:
        for fallback in ENTRY_ROLES:
            candidates = [file for file in package.files if file.role == fallback]
            if candidates:
                role = fallback
                break
    if not candidates:
        return None, None
    if role == "hook":
        # A hook package gives its scripts the hook role too; the harness reads the configuration first.
        candidates = [file for file in candidates if file.path.endswith(".json")] or candidates
    if len(candidates) > 1 and role != "instruction_file":
        return None, Finding("entry_ambiguous", FAIL, ", ".join(file.path for file in candidates),
                             "more than one file of the role the harness reads first")
    return candidates[0], None


def package_facts(package):
    """Every activation fact of one package before any layout is written: (findings, entry, kind, native)."""
    findings = []
    kind, native = package_kind(package)
    for code, path in package.problems:
        findings.append(Finding(code, FAIL, path, "a leftover of an interrupted installation"))
    for file in package.files:
        if file.claim == "body_missing":
            findings.append(Finding("file_missing", FAIL, file.path, "the package names a file it does not hold"))
        elif file.claim:
            findings.append(Finding("file_claim_false", FAIL, file.path,
                                    f"the recorded digest or size is not what the bytes are ({file.claim})"))
        elif not media_claim_holds(file):
            findings.append(Finding("media_type_claim_false", FAIL, file.path,
                                    f"the file claims {file.media_type} but its bytes are not that"))
    entry, ambiguity = select_entry(package, kind)
    if ambiguity is not None:
        findings.append(ambiguity)
        return findings, None, kind, native
    if entry is None:
        findings.append(Finding("entry_file_present", UNKNOWN, "", "no file of a role a harness reads natively"))
        return findings, None, kind, native
    if entry.payload is None:
        return findings, entry, kind, native
    if entry.size_bytes > MAXIMUM_TEXT_BYTES:
        findings.append(Finding("entry_too_large_to_read", UNKNOWN, entry.path, "the entry file is over the read bound"))
        return findings, entry, kind, native
    if package.body_form == "file" and package.kind == "skill":
        try:
            render_skill_header(native_name(package.identity), package.purpose)
        except InstallRefusal as refusal:
            findings.append(Finding("skill_name_not_native", FAIL, entry.path, refusal.code.value))
    entry_findings, needed = entry_facts(package, entry, kind, native)
    findings.extend(entry_findings)
    needed.update(configuration_facts(package, entry, findings))
    if any(file.role in EXECUTABLE_ROLES for file in package.files):
        needed.add("spawns_process")
    missing = sorted(needed - set(package.declared_effects))
    if missing:
        findings.append(Finding("authority_exceeds_declared_effects", FAIL, entry.path,
                                "the files ask for " + ", ".join(missing) + " which the item leaves undeclared"))
    return findings, entry, kind, native


# ---------------------------------------------------------------------------
# Layouts and placement
# ---------------------------------------------------------------------------

def identity_slug(identity):
    return re.sub(r"[^a-z0-9]+", "-", identity.lower()).strip("-")[:64] or "package"


def slot_name(package, entry, kind):
    """The name of the slot a harness reads the package from: its own native name, else the identity's."""
    if package.body_form == "file":
        return native_name(package.identity)
    if entry.text is None:
        return identity_slug(package.identity)
    if kind == "skill":
        header, _body, error = split_frontmatter(entry.text)
        mapping = parse_frontmatter(header)[0] if header and not error else None
        name = mapping.get("name") if mapping else None
        if isinstance(name, str) and NATIVE_NAME.fullmatch(name) and len(name) <= 64:
            return name
        return identity_slug(package.identity)
    if kind in ("plugin_manifest", "marketplace"):
        try:
            name = _strict_json(entry.payload, entry.path).get("name")
        except (JSON_ERRORS, AttributeError):
            name = None
        return identity_slug(name) if isinstance(name, str) and name.strip() else identity_slug(package.identity)
    return item_stem(entry.path) or identity_slug(package.identity)


def layout_targets(package, entry, kind, native):
    """Every (harness, scope, named slot, files placed) the documented layouts give this package."""
    if entry is None:
        return []
    try:
        name = slot_name(package, entry, kind)
    except InstallRefusal:
        name = identity_slug(package.identity)
    if package.body_form == "file":
        if package.kind != "skill":
            return []
        return [(profile.client_kind, "project", True,
                 [("/".join(profile.location_for("skill").relative_parts(name)), entry)])
                for profile in CLIENT_LAYOUT_PROFILES.values() if profile.locations]
    members = tuple(file.path for file in package.files)
    rows = placements(PackagePlan(kind, "", entry.path, members, name, native))
    probes = placements(PackagePlan(kind, "", entry.path, members, SENTINEL_NAME, native))
    side = SIDE_FOLDER + "/" + identity_slug(package.identity) + "/"
    targets = []
    for row, probe in zip(rows, probes):
        if row["harness"] in ("upstream", "reference"):
            continue
        template = row["path"]
        if template.endswith("/"):
            # A folder slot, such as a skill folder: the whole package goes inside it.
            placed = [(template + file.path, file) for file in package.files]
        elif "/" in entry.path and (template == entry.path or template.endswith("/" + entry.path)):
            # The package mirrors a folder the harness reads, such as a plugin root: keep its shape.
            root = template[:-len(entry.path)]
            placed = [(root + file.path, file) for file in package.files]
        else:
            # A single-file slot, such as a command or AGENTS.md: only the entry goes there. Every
            # other file waits in a side folder, because a notice placed beside a command becomes
            # a second command and a LICENSE at a project root replaces the customer's own.
            placed = [(template, entry)] + [(side + file.path, file) for file in package.files if file is not entry]
        targets.append((row["harness"], row["scope"], row["path"] != probe["path"], placed))
    return targets


def _safe_parts(relative):
    parts = tuple(relative.split("/"))
    if any(part in ("", ".", "..") or "\\" in part or "\x00" in part for part in parts):
        raise ActivationCheckError(f"{relative}: a target path never escapes the project")
    return parts


def write_placed(root, relative, payload):
    """Write one file under the project root, creating real folders only and never replacing a file."""
    parts = _safe_parts(relative)
    folder = root
    for part in parts[:-1]:
        folder = folder / part
        if folder.is_symlink():
            raise ActivationCheckError(f"{folder}: a symbolic link inside the scratch project")
        folder.mkdir(exist_ok=True)
    target = folder / parts[-1]
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(target, flags, 0o644)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(payload)
    return target


def same_bytes(holder, digest):
    """Whether the package that already holds a slot wrote the same bytes."""
    return holder[1] == digest


def install(package, entry, kind, native, scratch, occupied):
    """Place the package in every layout; return the layout rows and the set-level collisions found."""
    layouts, collisions = [], []
    for harness, scope, named, placed in layout_targets(package, entry, kind, native):
        project = Path(scratch) / harness / (SHARED_PROJECT if named else OWN_PROJECT + "/" + identity_slug(package.identity))
        project.mkdir(parents=True, exist_ok=True)
        written = []
        for relative, file in placed:
            if file.payload is None:
                written.append({"path": relative, "state": UNKNOWN, "digest": file.digest})
                continue
            payload = file.payload
            if package.body_form == "file" and package.kind == "skill":
                payload = render_skill_header(native_name(package.identity), package.purpose)[0] + payload
            digest = sha256_hex(payload)
            holder = occupied.get((harness, relative)) if named else None
            if holder is not None:
                if not same_bytes(holder, digest):
                    collisions.append({"harness": harness, "path": relative, "packages": [holder[0], package.identity],
                                       "digests": [holder[1], digest]})
                    written.append({"path": relative, "state": FAIL, "digest": digest, "code": "target_path_collision"})
                else:
                    written.append({"path": relative, "state": PASS, "digest": digest, "shared": True})
                continue
            try:
                target = write_placed(project, relative, payload)
            except (ActivationCheckError, OSError) as error:
                written.append({"path": relative, "state": FAIL, "digest": digest,
                                "code": "placement_refused", "detail": str(error)[:200]})
                continue
            read_back = sha256_hex(target.read_bytes())
            if named:
                occupied[(harness, relative)] = (package.identity, digest)
            row = {"path": relative, "state": PASS if read_back == digest else FAIL, "digest": read_back}
            if relative.startswith(SIDE_FOLDER + "/"):
                row["side"] = True
            written.append(row)
        layouts.append({"harness": harness, "scope": scope, "project": SHARED_PROJECT if named else OWN_PROJECT,
                        "files": written})
    return layouts, collisions


def check_package(package, scratch, occupied):
    """One result record: the facts, the layouts written and the verdict, bound to exact digests."""
    findings, entry, kind, native = package_facts(package)
    layouts, collisions = install(package, entry, kind, native, scratch, occupied) if entry is not None else ([], [])
    if entry is not None and not layouts:
        findings.append(Finding("layout_known", UNKNOWN, entry.path, "no documented layout for this native format"))
    for layout in layouts:
        for row in layout["files"]:
            if row["state"] == FAIL and row.get("code") != "target_path_collision":
                findings.append(Finding(row.get("code", "placement_failed"), FAIL, row["path"], row.get("detail", "")))
    failed = sorted({finding.code for finding in findings if finding.state == FAIL})
    unknown = sorted({finding.code for finding in findings if finding.state == UNKNOWN})
    if failed:
        verdict = REFUSED
    elif entry is None:
        verdict = NO_NATIVE_ACTIVATION
    elif unknown:
        verdict = UNRESOLVED
    else:
        verdict = ACTIVATES
    return {"record_type": RESULT_RECORD_TYPE, "identity": package.identity, "kind": package.kind,
            "package_kind": kind, "native_format": native, "styles": list(package.styles),
            "body_form": package.body_form, "served_digest": package.served_digest, "source": package.source,
            "entry": entry.path if entry else "",
            "files": [{"path": file.path, "role": file.role, "digest": file.digest, "size_bytes": file.size_bytes}
                      for file in package.files],
            "facts": [finding.to_dict() for finding in findings], "failed_codes": failed, "unknown_codes": unknown,
            "layouts": layouts, "verdict": verdict}, collisions


def run(packages, scratch):
    """Check every package of one run; named slots share one scratch project per harness."""
    occupied, results, collisions = {}, [], []
    for package in packages:
        result, found = check_package(package, scratch, occupied)
        results.append(result)
        collisions.extend(found)
    return results, collisions


def summarize(results, collisions):
    verdicts = {verdict: 0 for verdict in VERDICTS}
    codes, unknown, kinds = {}, {}, {}
    side = 0
    for result in results:
        verdicts[result["verdict"]] += 1
        row = kinds.setdefault(result["package_kind"], {verdict: 0 for verdict in VERDICTS})
        row[result["verdict"]] += 1
        for code in result["failed_codes"]:
            codes[code] = codes.get(code, 0) + 1
        for code in result["unknown_codes"]:
            unknown[code] = unknown.get(code, 0) + 1
        side += any(placed.get("side") for layout in result["layouts"] for placed in layout["files"])
    pairs = {tuple(sorted(row["packages"])) for row in collisions}
    return {"packages": len(results), "verdicts": verdicts, "failed_codes": dict(sorted(codes.items())),
            "unknown_codes": dict(sorted(unknown.items())), "collisions": len(collisions),
            "collision_pairs": len(pairs), "packages_in_collisions": len({name for pair in pairs for name in pair}),
            "collision_slots": len({(row["harness"], slot_of(row["path"])) for row in collisions}),
            "verdicts_by_package_kind": dict(sorted(kinds.items())), "packages_with_side_files": side}


def slot_of(path):
    """The named slot a placed path belongs to: a skill folder, or the file of a single-file slot."""
    parts = path.split("/")
    return "/".join(parts[:3]) if len(parts) > 3 else path


# ---------------------------------------------------------------------------
# A real loader's listing against the no-extra-component baseline
# ---------------------------------------------------------------------------

def opencode_listing(project):
    """(state, client version, entries or None) from OpenCode's own skill listing, which starts no model turn."""
    observation, entries = observe_client_listing(OPENCODE_PROFILE, None, Path(project), LISTING_KEY_VARIABLE,
                                                  LISTING_LIMITS)
    state = observation["state"]
    return getattr(state, "value", state), observation["client_version"], entries


def listed_entry_path(result):
    """(path of a skill package's entry in the OpenCode layout, whether this package wrote it)."""
    for layout in result["layouts"]:
        if layout["harness"] != LISTING_HARNESS:
            continue
        for row in layout["files"]:
            parts = row["path"].split("/")
            if parts[:2] != LISTING_ROOT.split("/") or len(parts) < 4:
                continue
            if "/".join(parts[3:]) == result["entry"] or (result["body_form"] == "file" and parts[3:] == ["SKILL.md"]):
                return row["path"], WRITTEN if row["state"] == PASS and not row.get("shared") else HELD_BY_ANOTHER
    return None, NOT_PLACED


def split_listing(entries, installed):
    """(entries inside the listing project by relative path, names of the entries outside it).

    An entry outside the project comes from the loader itself or from the
    person's own folders, and the baseline explains it by name, not by
    location: OpenCode 1.18.32 keeps one of two same-named global skills and
    chose a different one of them between two runs on September 26, 2026.
    """
    root = os.path.realpath(installed)
    inside, outside = {}, set()
    for row in entries:
        location = row.get("location") if isinstance(row, dict) else None
        real = os.path.realpath(location) if isinstance(location, str) and os.path.isabs(location) else ""
        if real.startswith(root + os.sep):
            inside[os.path.relpath(real, root).replace(os.sep, "/")] = row
        else:
            outside.add(row.get("name") if isinstance(row, dict) else None)
    return inside, outside


def observe_listing(results, scratch, work, lister=opencode_listing):
    """Compare a real loader's listing of the placed skills with its listing of an empty project.

    The empty project is the no-extra-component baseline: whatever the loader
    lists there, its own skills and the person's global ones, explains every
    listed entry outside the project. The listing project holds the skill
    folders of the shared OpenCode project and nothing else, so no plugin or
    tool file is ever loaded as code. For each skill package that wrote its
    own slot, the loader reports the entry at its exact path or it does not;
    any other entry it reports from inside that folder is an extra component.
    A listing that could not be observed leaves every package unknown, never
    not reported. The static verdicts stay as they are: loaded is a separate
    fact from the activation facts.
    """
    work = Path(work)
    baseline, installed = work / "baseline", work / "installed"
    baseline.mkdir(parents=True)
    installed.mkdir(parents=True)
    source = Path(scratch) / LISTING_HARNESS / SHARED_PROJECT / LISTING_ROOT
    if source.is_dir():
        shutil.copytree(source, installed / LISTING_ROOT, symlinks=True)
    started = datetime.now(timezone.utc)
    baseline_state, _baseline_version, baseline_entries = lister(baseline)
    state, version, entries = lister(installed)
    record = {"record_type": LISTING_RECORD_TYPE, "harness": LISTING_HARNESS, "client_version": version,
              "baseline_state": baseline_state, "state": state, "started_at": started.isoformat(),
              "elapsed_seconds": round((datetime.now(timezone.utc) - started).total_seconds(), 3), "summary": None}
    if baseline_entries is None or entries is None:
        return record
    baseline_names = sorted({str(row.get("name")) for row in baseline_entries if isinstance(row, dict)})
    inside, outside = split_listing(entries, installed)
    claimed, by_verdict, by_code, placements_seen = set(), {}, {}, {}
    for result in results:
        if result["package_kind"] != "skill":
            continue
        path, placement = listed_entry_path(result)
        placements_seen[placement] = placements_seen.get(placement, 0) + 1
        listing = {"harness": LISTING_HARNESS, "placement": placement}
        if placement == WRITTEN:
            folder = "/".join(path.split("/")[:3]) + "/"
            extra = sorted(relative for relative in inside if relative.startswith(folder) and relative != path)
            reported = path in inside
            claimed.update([path, *extra])
            listing.update({"reported": reported, "reported_name": inside[path].get("name") if reported else None,
                            "extra_components": extra})
            key = "reported" if reported else "not_reported"
            by_verdict.setdefault(result["verdict"], {"reported": 0, "not_reported": 0})[key] += 1
            for code in result["failed_codes"]:
                by_code.setdefault(code, {"reported": 0, "not_reported": 0})[key] += 1
        result["listing"] = listing
    record["summary"] = {
        "baseline_entries": len(baseline_entries),
        "baseline_names_digest": sha256_hex(json.dumps(baseline_names).encode("utf-8")),
        "listed_entries": len(entries), "entries_inside_project": len(inside),
        "outside_names_not_in_baseline": sorted(str(name) for name in outside if str(name) not in baseline_names),
        "skill_packages_by_placement": dict(sorted(placements_seen.items())),
        "written_by_verdict": dict(sorted(by_verdict.items())), "written_by_failed_code": dict(sorted(by_code.items())),
        "packages_with_extra_components": sum(bool(result.get("listing", {}).get("extra_components"))
                                              for result in results),
        "unattributed_entries": sorted(set(inside) - claimed)}
    return record


def laboratory_outcome(fixtures, scratch):
    """Each fixture must be refused with exactly the codes it names; a fixture that names none must activate.

    Exact, not a superset: a refusal code the fixture does not name means the
    check changed what it sees in that fixture, which is a regression to read,
    and a control that stops activating means the check refuses correct work.
    """
    rows = []
    for name, packages, expected in fixtures:
        results, collisions = run(packages, Path(scratch) / name)
        observed = sorted({code for result in results for code in result["failed_codes"]}
                          | ({"target_path_collision"} if collisions else set()))
        missing = sorted(set(expected) - set(observed))
        unexpected = sorted(set(observed) - set(expected))
        if expected:
            outcome = PASS if not missing and not unexpected else FAIL
        else:
            outcome = PASS if all(result["verdict"] == ACTIVATES for result in results) and not collisions else FAIL
        rows.append({"fixture": name, "expected_refusals": list(expected), "observed_refusals": observed,
                     "missing": missing, "unexpected": unexpected, "outcome": outcome, "results": results,
                     "collisions": collisions})
    return rows


def compact_results(results):
    """The results a reader acts on: everything that did not activate, and every listing that disagrees."""
    def disagrees(result):
        listing = result.get("listing") or {}
        return listing.get("reported") is False or bool(listing.get("extra_components"))
    return [result for result in results if result["verdict"] != ACTIVATES or disagrees(result)]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--bundle", help="a catalogue release bundle folder")
    source.add_argument("--laboratory", help="a folder of laboratory fixture packages")
    parser.add_argument("--output", required=True, help="the report path, which must not exist yet")
    parser.add_argument("--scratch", help="the scratch folder for the layouts; new or empty (default: a new temporary folder)")
    parser.add_argument("--limit", type=int, help="check only the first N packages of the bundle")
    parser.add_argument("--compact", action="store_true",
                        help="keep only the results that did not activate; the bundle digest binds the rest")
    parser.add_argument("--keep-scratch", action="store_true",
                        help="keep the temporary scratch folder this run creates (a --scratch folder is always kept)")
    parser.add_argument("--observe-listing", action="store_true",
                        help="with --bundle: also run OpenCode's own skill listing, which starts no model turn, in "
                             "an empty baseline project and in a project that holds the placed skill folders only")
    options = parser.parse_args(argv)
    output = Path(options.output)
    if output.exists():
        raise SystemExit("report_path_not_new")
    if options.observe_listing and not options.bundle:
        raise SystemExit("listing_needs_a_bundle")
    if options.scratch:
        scratch = Path(options.scratch)
        if scratch.exists() and any(scratch.iterdir()):
            raise SystemExit("scratch_not_empty")
        scratch.mkdir(parents=True, exist_ok=True)
    else:
        scratch = Path(tempfile.mkdtemp(prefix=SCRATCH_PREFIX))
    try:
        return _checked(options, output, scratch)
    finally:
        # Only the folder this run created itself is removed; a folder the caller named is theirs.
        if not options.scratch and not options.keep_scratch:
            shutil.rmtree(scratch, ignore_errors=True)


def _checked(options, output, scratch):
    report = {"record_type": REPORT_RECORD_TYPE, "checked_at": datetime.now(timezone.utc).isoformat(),
              "scratch": str(scratch), "verdicts": list(VERDICTS), "compact": bool(options.compact)}
    if options.bundle:
        digest, packages = bundle_packages(options.bundle, options.limit)
        results, collisions = run(packages, scratch)
        if options.observe_listing:
            report["listing"] = observe_listing(results, scratch, Path(scratch) / "loader-listing")
        header = _strict_json((Path(options.bundle) / "bundle.json").read_bytes(), "bundle.json")
        report.update({"bundle": str(Path(options.bundle).resolve()), "bundle_digest": digest,
                       "items_digest": header["items_digest"], "items": header["items"],
                       "summary": summarize(results, collisions), "collisions": collisions,
                       "results": compact_results(results) if options.compact else results})
        failed = report["summary"]["verdicts"][REFUSED]
    else:
        rows = laboratory_outcome(laboratory_fixtures(options.laboratory), scratch)
        report.update({"laboratory": str(Path(options.laboratory).resolve()), "fixtures": rows,
                       "summary": {"fixtures": len(rows), "passed": sum(row["outcome"] == PASS for row in rows),
                                   "failed": [row["fixture"] for row in rows if row["outcome"] == FAIL]}})
        failed = len(report["summary"]["failed"])
    output.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], sort_keys=True))
    if report.get("listing"):
        print(json.dumps({key: report["listing"][key] for key in ("client_version", "state", "summary")},
                         sort_keys=True))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
