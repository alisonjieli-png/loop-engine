#!/usr/bin/env python3
"""Inventory a mounted volume of the owner's own projects as seed material for harness files, reading only.

The owner, September 26, 2026: an attached drive holds "thousands of python
projects and other projects" that the owner wrote, to be scanned "as source
material for harness component files", for ideation and for generating new
files, "without license concerns, because everything on the drive was created
and written by me as the original author". This command is the first step: it
walks the volume once, writes an inventory outside the repository, and
classifies each project root by the provenance signals it finds. It copies
nothing, hashes nothing, and generates nothing.

```text
Inventory of one volume (outside the repository: it names private paths)
├── files-NNN.jsonl       one row per file: path, size, extension, modified time, and its
│                         harness kind (harness_kind/v1) when the path names one
├── projects.jsonl        one row per project root: markers, languages, size, git remotes,
│                         licence holders, copyright lines, and its provenance class
├── excluded.jsonl        what was left out and why, by folder and class, never a file's contents
├── summary.json          counts by extension, language, harness kind, provenance class and top folder
└── progress.json         rewritten every few thousand files while the walk runs
```

The owner's authorship declaration is recorded as the basis of provenance,
never assumed per file: a project whose git remote names another account,
whose licence file names another holder, or whose files carry another
copyright line is classed as third-party material and stays inspiration only,
as the licence rule requires. Vendored dependencies, virtual environments,
caches and system folders are skipped by name.

The owner asked on October 5, 2026 to "look at all of the files on this PC,
and look for harness components", which takes the walk into home folders and
old system disks. Three rules keep that walk private. Secret stores (SSH and
GnuPG folders, key rings, password stores, browser and mail profiles) are
never entered. A file whose name says it holds or may hold a credential, or a
private message, is never opened or listed by name: excluded.jsonl counts it
by folder and class. A folder the operator names with --exclude-path (personal
identity, legal or business-operations material) is not walked, and its reason
is recorded. A harness kind is nominated from the path alone; content decides
later, in the step that reads and hashes the nominated files.

    PYTHONPATH=src python tools/scan_local_volume.py --volume /run/media/username/Expansion \\
        --output ~/baltor-library/volumes/expansion/inventory-1 --owner-account alisonjieli-png
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

RECORD_TYPE = "local_volume_inventory/v1"
FILE_RECORD_TYPE = "local_volume_file/v1"
PROJECT_RECORD_TYPE = "local_volume_project/v1"
EXCLUDED_RECORD_TYPE = "local_volume_exclusion/v1"
HARNESS_KIND_VOCABULARY = "harness_kind/v1"
#: Folders never walked: vendored dependencies, environments, caches, system and recycle folders, and
#: the git object store (its config is read for remotes, nothing else).
SKIPPED_FOLDERS = frozenset({
    "node_modules", "vendor", ".venv", "venv", "env", ".env", "site-packages", "dist-packages", "__pycache__",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", ".tox", ".nox", ".cache", "dist", "build", ".next", "target",
    ".gradle", ".idea", ".vscode-server", "$RECYCLE.BIN", "$Recycle.Bin", ".Trash-1000", "System Volume Information",
    "FOUND.000", "$WinREAgent", "Windows", "Program Files", "Program Files (x86)", "ProgramData", "AppData",
    ".conda", "conda", "anaconda3", "miniconda3", ".npm", ".yarn", ".pnpm-store", "bower_components",
    "Library", ".Spotlight-V100", ".fseventsd", "lost+found", ".git"})
#: Secret stores and private profiles, never entered: key material, password and key rings, and the browser and
#: mail profiles that hold cookies, saved logins and messages. Each one skipped is counted in excluded.jsonl.
SECRET_FOLDERS = frozenset({
    ".ssh", ".gnupg", ".password-store", "keyrings", ".pki", ".mozilla", ".thunderbird", ".waterfox", ".floorp",
    ".moonchild productions", "google-chrome", "chromium", "BraveSoftware", "vivaldi", "opera", "Thunderbird",
    "Mozilla", ".aws", ".azure", ".kube", ".docker", "gcloud", ".gcloud", ".putty", ".vnc", ".anydesk"})
SKIPPED_SUFFIXES = (".tar", ".tar.gz", ".tgz", ".zip", ".7z", ".rar", ".iso", ".img", ".vhd", ".vhdx", ".vmdk",
                    ".dmg", ".pkg", ".exe", ".msi", ".dll", ".so", ".dylib", ".bin", ".safetensors", ".ckpt",
                    ".pt", ".pth", ".onnx", ".gguf", ".npz", ".npy", ".parquet", ".sqlite", ".db")
#: A folder holding one of these is a project root. Archives (tar files) are inventoried as files, not opened.
PROJECT_MARKERS = ("pyproject.toml", "setup.py", "setup.cfg", "requirements.txt", "package.json", "Cargo.toml",
                   "go.mod", "pom.xml", "build.gradle", "Makefile", "Dockerfile", "docker-compose.yml",
                   "environment.yml", "AGENTS.md", "CLAUDE.md", "README.md", "readme.md", "README", "main.py",
                   "app.py", "manage.py", "index.html", "package-lock.json", "pubspec.yaml", "CMakeLists.txt")
GIT_MARKER = ".git"
LANGUAGES = {".py": "python", ".ipynb": "notebook", ".js": "javascript", ".mjs": "javascript", ".ts": "typescript",
             ".tsx": "typescript", ".jsx": "javascript", ".html": "html", ".css": "css", ".sh": "shell",
             ".bash": "shell", ".ps1": "powershell", ".go": "go", ".rs": "rust", ".java": "java", ".kt": "kotlin",
             ".c": "c", ".h": "c", ".cpp": "cpp", ".hpp": "cpp", ".cs": "csharp", ".rb": "ruby", ".php": "php",
             ".lua": "lua", ".dart": "dart", ".swift": "swift", ".r": "r", ".jl": "julia", ".sql": "sql",
             ".md": "markdown", ".rst": "text", ".txt": "text", ".json": "data", ".yaml": "data", ".yml": "data",
             ".toml": "data", ".csv": "data", ".xml": "data", ".glsl": "shader", ".blend": "blender",
             ".obj": "3d", ".fbx": "3d", ".gltf": "3d", ".glb": "3d", ".stl": "3d", ".svg": "image",
             ".png": "image", ".jpg": "image", ".jpeg": "image", ".gif": "image", ".webp": "image", ".psd": "image",
             ".mp4": "video", ".mov": "video", ".mkv": "video", ".webm": "video", ".mp3": "audio", ".wav": "audio",
             ".flac": "audio", ".pdf": "document", ".docx": "document", ".pptx": "document", ".xlsx": "document"}
#: Code files: the languages a harness could run or read as a program, never prose, data or media.
SOURCE_SUFFIXES = frozenset(suffix for suffix, language in LANGUAGES.items()
                            if language not in ("image", "video", "audio", "document", "3d", "blender", "data",
                                                "markdown", "text"))
LICENCE_NAMES = ("LICENSE", "LICENSE.md", "LICENSE.txt", "LICENCE", "LICENCE.md", "LICENCE.txt", "COPYING",
                 "COPYING.md", "NOTICE", "NOTICE.md")
COPYRIGHT = re.compile(r"copyright\s*(?:\(c\)|©)?\s*(?:\d{4}(?:\s*[-,]\s*\d{4})?)?\s*(?:by\s+)?([^\n]{2,80})",
                       re.IGNORECASE)
REMOTE_URL = re.compile(r"^\s*url\s*=\s*(\S+)", re.MULTILINE)
GITHUB_OWNER = re.compile(r"github\.com[:/]([^/\s]+)/")
#: Provenance classes, from the strongest third-party signal down.
THIRD_PARTY_REMOTE = "third_party_git_remote"
THIRD_PARTY_LICENCE = "third_party_licence_holder"
THIRD_PARTY_COPYRIGHT = "third_party_copyright_line"
OWNER_REMOTE = "owner_git_remote"
OWNER_DECLARED = "owner_declared_no_contrary_signal"
PROVENANCE_UNRESOLVED = "provenance_unresolved"
PROGRESS_EVERY = 5000
SAMPLE_SOURCE_FILES = 40
HEAD_BYTES = 4096

#: File names that hold or may hold a credential. Such a file is never opened, hashed or listed by name.
_CREDENTIAL_NAMES = frozenset({
    "credentials", "credentials.json", "credentials.yml", "credentials.yaml", ".git-credentials", ".netrc",
    "_netrc", ".pgpass", ".pypirc", ".npmrc", ".yarnrc", ".dockercfg", "kubeconfig", "rclone.conf", ".s3cfg", ".boto",
    "kaggle.json", "token.json", "tokens.json", "token.pickle", ".credentials.json", "auth.json", "client_secret.json",
    "client_secrets.json", "service_account.json", "service-account.json", "hosts.yml", ".htpasswd", "wp-config.php",
    ".claude.json", "settings.local.json", "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519", "known_hosts",
    "authorized_keys", "cookies", "cookies.sqlite", "cookies.txt", "login data", "web data", "key4.db", "key3.db",
    "logins.json", "cert9.db", "signons.sqlite", ".bash_history", ".zsh_history", ".python_history", ".psql_history",
    ".mysql_history", ".lesshst", ".viminfo", ".xauthority", ".iceauthority", "history.jsonl"})
#: Model-harness configuration that routinely carries API keys or tokens in its environment blocks.
_HARNESS_SECRET_CONFIGS = frozenset({
    ".mcp.json", "mcp.json", "mcp_config.json", "mcp_servers.json", "claude_desktop_config.json"})
_KEY_SUFFIXES = (".pem", ".key", ".p12", ".pfx", ".jks", ".keystore", ".ppk", ".kdbx", ".kdb", ".keychain",
                 ".keyring", ".gpg", ".pgp", ".asc", ".ovpn", ".token", ".secret", ".cookies")
_PRIVATE_MESSAGE_SUFFIXES = (".eml", ".mbox", ".msf", ".pst", ".ost", ".msg", ".vcf")
_SECRET_WORDS = re.compile(r"(?:credential|secret|passw(?:or)?d|apikey|api[_-]key|access[_-]?token|"
                           r"refresh[_-]?token|auth[_-]?token|private[_-]?key)")


def excluded_class(relative: str) -> tuple:
    """(class, reason) for a file never opened or listed by name, or ("", "") for an ordinary file.

    The name decides, never the contents, so a file is left out before a single byte of it is read."""
    parts = relative.replace("\\", "/").split("/")
    name = parts[-1].lower()
    lowered = [part.lower() for part in parts[:-1]]
    suffix = os.path.splitext(name)[1]
    if name == ".env" or name.startswith(".env.") or name.endswith(".env") or name.startswith(".envrc"):
        return "dotenv", "an environment file holds or may hold credentials"
    if name in _HARNESS_SECRET_CONFIGS or ((".codex" in lowered or ".claude" in lowered or ".copilot" in lowered)
                                           and name in ("config.toml", "settings.json", "auth.json")):
        return "harness_settings", "a harness or protocol-server configuration may carry keys in its environment"
    if name in _CREDENTIAL_NAMES or name.startswith(("id_rsa", "id_dsa", "id_ecdsa", "id_ed25519")):
        return "credential_file", "the file name is a known credential, history or browser-store name"
    if suffix in _KEY_SUFFIXES:
        return "key_material", "the extension is key, certificate, token or password-store material"
    if suffix in _PRIVATE_MESSAGE_SUFFIXES:
        return "private_message", "mail, message or contact files are the owner's private correspondence"
    if _SECRET_WORDS.search(name):
        return "credential_file", "the file name says it holds a credential"
    return "", ""


_TEXT_SUFFIXES = frozenset({".md", ".txt", ".yaml", ".yml", ".json", ".j2", ".jinja", ".jinja2", ".tmpl", ".toml",
                            ".prompt", ".prompty", ".mdc", ""})
_CREATIVE_KINDS = (
    ((".blend",), "blender"), ((".tscn", ".tres", ".gd", ".gdshader", ".godot"), "godot"),
    ((".glsl", ".frag", ".vert", ".wgsl", ".hlsl", ".shader", ".comp", ".fsh", ".vsh"), "shader"),
    ((".gltf", ".glb", ".obj", ".fbx", ".stl", ".usd", ".usda", ".usdz", ".ply", ".dae", ".3mf"), "three_d_model"),
    ((".svg",), "svg"), ((".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aif", ".aiff", ".opus"), "audio"),
    ((".mid", ".midi"), "midi"), ((".prproj", ".aep", ".drp", ".kdenlive", ".mlt", ".otio", ".veg"), "video_project"),
    ((".psd", ".kra", ".xcf", ".ora"), "image_project"), ((".cube", ".3dl"), "colour_lut"),
    ((".pde",), "processing_sketch"), ((".ipynb",), "notebook"),
    ((".csv", ".tsv", ".jsonl", ".ndjson", ".parquet", ".arrow", ".feather"), "data_table"))


def harness_kind(relative: str) -> str:
    """The harness kind a file's path nominates (vocabulary harness_kind/v1), or "" when it names none.

    A coding or agent harness picks these files up as they are: skills, agent and command definitions, hooks,
    instruction and rule files, plugin manifests, prompt templates, workflows, tool definitions, schemas, API
    descriptions, fixtures, notebooks, data tables and creative assets. Code files are counted by project, not here."""
    parts = relative.replace("\\", "/").split("/")
    name = parts[-1].lower()
    folders = [part.lower() for part in parts[:-1]]
    parent = folders[-1] if folders else ""
    suffix = os.path.splitext(name)[1]
    if ".ipynb_checkpoints" in folders:
        return ""
    if name == "skill.md":
        return "skill"
    if name in ("plugin.json", "marketplace.json") and parent in (".claude-plugin", ".codex-plugin"):
        return "plugin" if name == "plugin.json" else "marketplace"
    if name in ("gemini-extension.json", "opencode.json", "opencode.jsonc"):
        return "plugin"
    if name in ("agents.md", "claude.md", "gemini.md", "copilot-instructions.md", "agent.md") \
            or name.endswith(".instructions.md"):
        return "instructions"
    if name in (".cursorrules", ".windsurfrules", ".clinerules", ".roorules") or suffix == ".mdc" \
            or any(part in (".clinerules", ".roo", ".windsurf") for part in folders) \
            or (parent == "rules" and (".cursor" in folders or ".kiro" in folders)) or parent == "steering":
        return "rules"
    if name.endswith((".agent.md", ".chatmode.md")) or (parent in ("agents", "agent") and suffix in (".md", ".toml")
                                                        and any(part.startswith(".") for part in folders)):
        return "agent"
    if name.endswith(".prompt.md") or (parent in ("commands", "command", "prompts")
                                       and suffix in (".md", ".toml")
                                       and any(part in (".claude", ".opencode", ".cursor", ".gemini", ".codex",
                                                        ".github", ".qwen") for part in folders)):
        return "command"
    if name == "hooks.json" or (parent == "hooks" and ".claude" in folders):
        return "hook"
    if parent == "workflows" and len(folders) > 1 and folders[-2] == ".github" and suffix in (".yml", ".yaml"):
        return "ci_workflow"
    if name in ("action.yml", "action.yaml"):
        return "ci_workflow"
    if name.endswith((".workflow.json", "_workflow.json", "-workflow.json")) or (
            "workflow" in name and suffix == ".json") or (parent == "workflows" and suffix == ".json"):
        return "workflow"
    stem = os.path.splitext(name)[0]
    if suffix in (".json", ".yaml", ".yml") and (stem in ("openapi", "swagger") or stem.startswith(("openapi",
                                                                                                    "swagger"))):
        return "openapi"
    if name.endswith(".schema.json") or (suffix == ".json" and (stem == "schema" or parent in ("schemas", "schema"))):
        return "json_schema"
    if name in ("tools.json", "tool.json", "functions.json", "tool-definitions.jsonl", "tool_definitions.json",
                "tool-definitions.json") or name.endswith(".tool.json"):
        return "tool_definition"
    if suffix in (".prompt", ".prompty") or (suffix in _TEXT_SUFFIXES and (
            "prompt" in stem or any(part in ("prompts", "prompt_templates", "prompt-templates") for part in folders))):
        return "prompt_template"
    if any(part in ("fixtures", "__fixtures__", "testdata", "test_data", "golden", "goldens") for part in folders):
        return "test_fixture"
    if name == "project.godot":
        return "godot"
    for suffixes, kind in _CREATIVE_KINDS:
        if suffix in suffixes:
            return kind
    return ""


def _read_head(path: str, size: int = HEAD_BYTES, *, redact: bool = True) -> str:
    if os.path.islink(path):
        return ""
    try:
        with open(path, "rb") as stream:
            text = stream.read(size).decode("utf-8", "replace")
            return _redact(text) if redact else text
    except OSError:
        return ""


def _redact(text: str) -> str:
    """Remove common credential forms before any excerpt reaches an inventory."""
    text = re.sub(r"-----BEGIN [^-]*PRIVATE KEY-----.*?(?:-----END [^-]*PRIVATE KEY-----|$)",
                  "[private key omitted]", text, flags=re.DOTALL)
    text = re.sub(r"(?i)\b(?:sk|rk|pk)[_-](?:live|test)[_-][A-Za-z0-9_-]+", "[credential omitted]", text)
    text = re.sub(r"(?i)\b(?:gh[pousr]_[A-Za-z0-9_]{15,}|github_pat_[A-Za-z0-9_]+|sk-[A-Za-z0-9_-]{15,})",
                  "[credential omitted]", text)
    return re.sub(r"(?im)(\b(?:api[_-]?key|access[_-]?token|password|client[_-]?secret)\s*[:=]\s*)[^\s,;]+",
                  r"\1[omitted]", text)


def _remotes(git_folder: str, *, problems=None) -> list:
    if os.path.islink(git_folder):
        return []
    config = os.path.join(git_folder, "config")
    if not os.path.isfile(config):
        return []
    remotes = []
    for value in REMOTE_URL.findall(_read_head(config, 65536, redact=False)):
        if "://" in value:
            try:
                parsed = urlsplit(value)
            except ValueError:
                if problems is not None:
                    problems.append("remote_url_unreadable")
                continue
            value = urlunsplit((parsed.scheme, parsed.hostname or "", parsed.path, "", ""))
        remotes.append(_redact(value))
    return remotes


def _holders(text: str) -> list:
    found = []
    for match in COPYRIGHT.finditer(text):
        holder = match.group(1).strip().strip(".,;:'\"<>()[]")
        if holder and holder.lower() not in ("all rights reserved",):
            found.append(holder[:80])
    return found[:5]


def _classify(project: dict, owner_accounts: set, owner_names: set) -> str:
    if project.get("provenance_issues"):
        return PROVENANCE_UNRESOLVED
    owners = {owner.lower() for owner in project["remote_owners"]}
    if owners - owner_accounts:
        return THIRD_PARTY_REMOTE
    holders = [holder for holder in project["licence_holders"] + project["copyright_holders"]
               if not any(name and name in holder.lower() for name in owner_names)]
    if project["licence_holders"] and holders and any(h in project["licence_holders"] for h in holders):
        return THIRD_PARTY_LICENCE
    if holders and any(h in project["copyright_holders"] for h in holders):
        return THIRD_PARTY_COPYRIGHT
    if owners:
        return OWNER_REMOTE
    return OWNER_DECLARED


class Inventory:
    def __init__(self, volume: Path, output: Path, owner_accounts, owner_names, shard_rows=200_000,
                 excluded_paths=None, skipped_names=()):
        self.volume, self.output = volume, output
        self.owner_accounts = {account.lower() for account in owner_accounts}
        self.owner_names = {name.lower() for name in owner_names if name}
        self.shard_rows = shard_rows
        #: Relative folder -> reason, for the folders the operator excluded (personal or business material).
        self.excluded_paths = dict(excluded_paths or {})
        self.skipped_names = SKIPPED_FOLDERS | frozenset(skipped_names)
        self.files = 0
        self.bytes = 0
        self.shard, self.shard_index, self.shard_count = None, 0, 0
        self.extensions, self.languages, self.top_folders = Counter(), Counter(), Counter()
        self.harness_kinds = Counter()
        self.skipped_folders, self.errors = Counter(), 0
        #: (relative folder, class) -> [reason, files, bytes]; folders left out whole carry files None.
        self.exclusions = {}
        self.projects = []
        self._stats_store = {}
        self.started = time.time()
        self.projects_stream = open(output / "projects.jsonl", "w", encoding="utf-8")

    def exclude(self, folder: str, kind: str, reason: str, size: "int | None" = None):
        """Count one left-out file (or record one left-out folder) without its name or its contents."""
        row = self.exclusions.setdefault((os.path.relpath(folder, self.volume), kind), [reason, 0, 0])
        if size is None:
            row[1] = None
        elif row[1] is not None:
            row[1] += 1
            row[2] += size

    def _open_shard(self):
        if self.shard:
            self.shard.close()
        self.shard_index += 1
        self.shard = open(self.output / f"files-{self.shard_index:03d}.jsonl", "w", encoding="utf-8")
        self.shard_count = 0

    def file_row(self, path: str, entry_stat, top: str):
        if self.shard is None or self.shard_count >= self.shard_rows:
            self._open_shard()
        suffix = os.path.splitext(path)[1].lower()
        relative = os.path.relpath(path, self.volume)
        row = {"record_type": FILE_RECORD_TYPE, "path": relative, "size_bytes": entry_stat.st_size,
               "extension": suffix, "language": LANGUAGES.get(suffix, ""), "modified_at": int(entry_stat.st_mtime)}
        kind = harness_kind(relative)
        if kind:
            row["harness_kind"] = kind
            self.harness_kinds[kind] += 1
        self.shard.write(json.dumps(row, ensure_ascii=False) + "\n")
        self.shard_count += 1
        self.files += 1
        self.bytes += entry_stat.st_size
        self.extensions[suffix or "(none)"] += 1
        if row["language"]:
            self.languages[row["language"]] += 1
        self.top_folders[top] += 1
        if self.files % PROGRESS_EVERY == 0:
            self.progress("walking")

    def progress(self, state: str):
        (self.output / "progress.json").write_text(json.dumps({
            "state": state, "files": self.files, "bytes": self.bytes, "projects": len(self.projects),
            "errors": self.errors, "seconds": round(time.time() - self.started, 1),
            "skipped_folders": dict(self.skipped_folders.most_common(20))}, indent=1))

    def project(self, folder: str, names: list, top: str) -> dict:
        markers = sorted(name for name in names if name in PROJECT_MARKERS or name == GIT_MARKER)
        problems = []
        remotes = _remotes(os.path.join(folder, GIT_MARKER), problems=problems) if GIT_MARKER in names else []
        licence_holders, licence_files = [], []
        for name in names:
            if name in LICENCE_NAMES:
                licence_files.append(name)
                licence_holders.extend(_holders(_read_head(os.path.join(folder, name))))
        row = {"record_type": PROJECT_RECORD_TYPE, "path": os.path.relpath(folder, self.volume), "top_folder": top,
               "name": os.path.basename(folder), "markers": markers, "git_remotes": remotes[:5],
               "provenance_issues": problems,
               "remote_owners": sorted({match.group(1) for url in remotes for match in [GITHUB_OWNER.search(url)] if match}),
               "licence_files": licence_files, "licence_holders": sorted(set(licence_holders)),
               "copyright_holders": [], "source_files": 0, "files": 0, "size_bytes": 0, "languages": {},
               "newest_modified_at": 0, "oldest_modified_at": 0, "readme": "", "provenance_class": ""}
        return row

    def finish_project(self, row: dict, counts: Counter, languages: Counter, size: int, newest: int, oldest: int,
                       copyright_holders: Counter, readme: str):
        row.update({"files": sum(counts.values()), "source_files": sum(counts[s] for s in counts if s in SOURCE_SUFFIXES),
                    "size_bytes": size, "languages": dict(languages.most_common(8)), "newest_modified_at": newest,
                    "oldest_modified_at": oldest, "copyright_holders": [h for h, _n in copyright_holders.most_common(5)],
                    "readme": readme[:600]})
        row["provenance_class"] = _classify(row, self.owner_accounts, self.owner_names)
        self.projects.append({key: row[key] for key in ("path", "provenance_class", "source_files", "size_bytes")})
        self.projects_stream.write(json.dumps(row, ensure_ascii=False) + "\n")

    def walk(self, folder: str, top: str, project: "dict | None", depth: int):
        """Walk one folder; a folder with a marker starts a project (nested projects keep their own row)."""
        try:
            with os.scandir(folder) as entries:
                listed = list(entries)
        except OSError:
            self.errors += 1
            return
        names = [entry.name for entry in listed]
        own = None
        if any(name in PROJECT_MARKERS or name == GIT_MARKER for name in names):
            own = self.project(folder, names, top)
        current = own or project
        for entry in listed:
            name = entry.name
            if name.startswith("._"):
                continue  # AppleDouble sidecars carry no content of their own.
            try:
                if entry.is_symlink():
                    continue
                if entry.is_dir(follow_symlinks=False):
                    if name in SECRET_FOLDERS:
                        self.exclude(entry.path, "secret_store",
                                     "key, password, browser or mail profile folders are never entered")
                        continue
                    reason = self.excluded_paths.get(os.path.relpath(entry.path, self.volume))
                    if reason:
                        self.exclude(entry.path, "operator_excluded", reason)
                        continue
                    if name in self.skipped_names:
                        self.skipped_folders[name] += 1
                        continue
                    self.walk(entry.path, top, current, depth + 1)
                    continue
                entry_stat = entry.stat(follow_symlinks=False)
            except OSError:
                self.errors += 1
                continue
            kind, reason = excluded_class(os.path.relpath(entry.path, self.volume))
            if kind:
                # Left out before any byte is read: no file row, no copyright sample, no name in the inventory.
                self.exclude(folder, kind, reason, entry_stat.st_size)
                continue
            self.file_row(entry.path, entry_stat, top)
            if current is not None:
                suffix = os.path.splitext(name)[1].lower()
                stats_of = self._stats(current)
                stats_of["counts"][suffix] += 1
                if LANGUAGES.get(suffix):
                    stats_of["languages"][LANGUAGES[suffix]] += 1
                stats_of["size"] += entry_stat.st_size
                modified = int(entry_stat.st_mtime)
                stats_of["newest"] = max(stats_of["newest"], modified)
                stats_of["oldest"] = modified if not stats_of["oldest"] else min(stats_of["oldest"], modified)
                if suffix in SOURCE_SUFFIXES and stats_of["sampled"] < SAMPLE_SOURCE_FILES:
                    stats_of["sampled"] += 1
                    for holder in _holders(_read_head(entry.path)):
                        stats_of["holders"][holder] += 1
        if own is not None:
            stats = self._stats(own)
            self.finish_project(own, stats["counts"], stats["languages"], stats["size"], stats["newest"],
                                stats["oldest"], stats["holders"], stats["readme"])
            self._stats_store.pop(id(own), None)

    def _stats(self, project: dict) -> dict:
        store = self._stats_store
        if id(project) not in store:
            store[id(project)] = {"counts": Counter(), "languages": Counter(), "size": 0, "newest": 0, "oldest": 0,
                                  "holders": Counter(), "readme": "", "sampled": 0}
            for name in ("README.md", "readme.md", "README"):
                candidate = os.path.join(self.volume, project["path"], name)
                if os.path.isfile(candidate):
                    store[id(project)]["readme"] = _read_head(candidate, 2000)
                    break
        return store[id(project)]

    def run(self, roots) -> dict:
        for root in roots:
            top = os.path.basename(root.rstrip("/"))
            self.walk(root, top, None, 0)
        if self.shard:
            self.shard.close()
        self.projects_stream.close()
        excluded_by_class = Counter()
        with open(self.output / "excluded.jsonl", "w", encoding="utf-8") as stream:
            for (folder, kind), (reason, files, size) in sorted(self.exclusions.items()):
                excluded_by_class[kind] += 1 if files is None else files
                stream.write(json.dumps({"record_type": EXCLUDED_RECORD_TYPE, "folder": folder, "class": kind,
                                         "reason": reason, "files": files, "bytes": None if files is None else size},
                                        ensure_ascii=False) + "\n")
        classes = Counter(row["provenance_class"] for row in self.projects)
        summary = {"record_type": RECORD_TYPE, "volume": str(self.volume), "output": str(self.output),
                   "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self.started)),
                   "seconds": round(time.time() - self.started, 1), "files": self.files, "bytes": self.bytes,
                   "errors": self.errors, "projects": len(self.projects),
                   "projects_by_provenance_class": dict(classes.most_common()),
                   "source_files_by_provenance_class": {
                       name: sum(row["source_files"] for row in self.projects if row["provenance_class"] == name)
                       for name in classes},
                   "extensions": dict(self.extensions.most_common(60)), "languages": dict(self.languages.most_common()),
                   "harness_kind_vocabulary": HARNESS_KIND_VOCABULARY,
                   "harness_kinds": dict(self.harness_kinds.most_common()),
                   "excluded_by_class": dict(excluded_by_class.most_common()),
                   "top_folders": dict(self.top_folders.most_common()),
                   "skipped_folders": dict(self.skipped_folders.most_common(40)),
                   "provenance_basis": ("The owner declared on September 26, 2026 that everything on the volume was "
                                        "written by the owner; a project keeps that basis only while no git remote, "
                                        "licence file or copyright line names someone else."),
                   "what_this_is_not": "No file was copied, hashed, opened beyond its first bytes, or generated from."}
        (self.output / "summary.json").write_text(json.dumps(summary, indent=1))
        self.progress("finished")
        return summary


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--volume", required=True)
    parser.add_argument("--output", required=True, help="a new folder outside the repository")
    parser.add_argument("--root", action="append", help="a top-level folder to walk (default: every one not skipped)")
    parser.add_argument("--owner-account", action="append", default=[], help="a git host account the owner holds")
    parser.add_argument("--owner-name", action="append", default=[], help="a name the owner's copyright lines use")
    parser.add_argument("--exclude-path", action="append", default=[], metavar="FOLDER=REASON",
                        help="a folder, relative to the volume, that is not walked, with the reason recorded")
    parser.add_argument("--skip-folder", action="append", default=[], metavar="NAME",
                        help="a folder name skipped wherever it appears, like the built-in vendored names")
    args = parser.parse_args(argv)
    volume, output = Path(args.volume).resolve(), Path(args.output).resolve()
    repository = Path(__file__).resolve().parents[1]
    if output == repository or repository in output.parents:
        print("the inventory names private paths; write it outside the repository", file=sys.stderr)
        return 2
    if not volume.is_dir():
        print(f"not a folder: {volume}", file=sys.stderr)
        return 2
    if args.root and any(Path(root).is_absolute() or ".." in Path(root).parts
                         or not (volume / root).resolve().is_relative_to(volume) for root in args.root):
        print("a selected root must stay within the named volume", file=sys.stderr)
        return 2
    # The inventory must never be walked into itself. Without selected roots every top-level folder is walked, so the
    # output must lie outside the volume; with selected roots (a home folder walked by named roots, October 5, 2026)
    # it may lie inside the volume when no selected root holds it.
    walked = [(volume / root).resolve() for root in args.root] if args.root else [volume]
    if any(output == folder or folder in output.parents for folder in walked):
        print("write the inventory outside the scanned volume and every selected root", file=sys.stderr)
        return 2
    excluded_paths = {}
    for value in args.exclude_path:
        folder, _sep, reason = value.partition("=")
        relative = Path(folder.strip().rstrip("/"))
        if not reason.strip() or not folder.strip() or relative.is_absolute() or ".." in relative.parts:
            print("--exclude-path takes FOLDER=REASON, with FOLDER relative to the volume", file=sys.stderr)
            return 2
        excluded_paths[relative.as_posix()] = reason.strip()
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    skipped = SKIPPED_FOLDERS | frozenset(args.skip_folder)
    roots = [str(volume / root) for root in args.root] if args.root else [
        entry.path for entry in os.scandir(volume) if entry.is_dir(follow_symlinks=False)
        and entry.name not in skipped and entry.name not in SECRET_FOLDERS and not entry.name.startswith(".")]
    inventory = Inventory(volume, output, args.owner_account, args.owner_name, excluded_paths=excluded_paths,
                          skipped_names=args.skip_folder)
    for root in list(roots):
        reason = excluded_paths.get(os.path.relpath(root, volume))
        if os.path.basename(root.rstrip("/")) in SECRET_FOLDERS:
            # A secret store named as a root is still never entered.
            inventory.exclude(root, "secret_store", "key, password, browser or mail profile folders are never entered")
            roots.remove(root)
        elif reason:
            inventory.exclude(root, "operator_excluded", reason)
            roots.remove(root)
    summary = inventory.run(roots)
    print(json.dumps({key: summary[key] for key in ("files", "bytes", "projects", "projects_by_provenance_class",
                                                     "harness_kinds", "excluded_by_class", "seconds", "errors")},
                     indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
