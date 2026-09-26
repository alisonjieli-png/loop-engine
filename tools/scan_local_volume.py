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
├── files-NNN.jsonl       one row per file: path, size, extension, modified time
├── projects.jsonl        one row per project root: markers, languages, size, git remotes,
│                         licence holders, copyright lines, and its provenance class
├── summary.json          counts by extension, language, provenance class and top folder
└── progress.json         rewritten every few thousand files while the walk runs
```

The owner's authorship declaration is recorded as the basis of provenance,
never assumed per file: a project whose git remote names another account,
whose licence file names another holder, or whose files carry another
copyright line is classed as third-party material and stays inspiration only,
as the licence rule requires. Vendored dependencies, virtual environments,
caches and system folders are skipped by name.

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

RECORD_TYPE = "local_volume_inventory/v1"
FILE_RECORD_TYPE = "local_volume_file/v1"
PROJECT_RECORD_TYPE = "local_volume_project/v1"
#: Folders never walked: vendored dependencies, environments, caches, system and recycle folders, and
#: the git object store (its config is read for remotes, nothing else).
SKIPPED_FOLDERS = frozenset({
    "node_modules", "vendor", ".venv", "venv", "env", ".env", "site-packages", "dist-packages", "__pycache__",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", ".tox", ".nox", ".cache", "dist", "build", ".next", "target",
    ".gradle", ".idea", ".vscode-server", "$RECYCLE.BIN", "$Recycle.Bin", ".Trash-1000", "System Volume Information",
    "FOUND.000", "$WinREAgent", "Windows", "Program Files", "Program Files (x86)", "ProgramData", "AppData",
    ".conda", "conda", "anaconda3", "miniconda3", ".npm", ".yarn", ".pnpm-store", "bower_components",
    "Library", ".Spotlight-V100", ".fseventsd", "lost+found", ".git"})
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
PROGRESS_EVERY = 5000
SAMPLE_SOURCE_FILES = 40
HEAD_BYTES = 4096


def _read_head(path: str, size: int = HEAD_BYTES) -> str:
    try:
        with open(path, "rb") as stream:
            return stream.read(size).decode("utf-8", "replace")
    except OSError:
        return ""


def _remotes(git_folder: str) -> list:
    config = os.path.join(git_folder, "config")
    if not os.path.isfile(config):
        return []
    return REMOTE_URL.findall(_read_head(config, 65536))


def _holders(text: str) -> list:
    found = []
    for match in COPYRIGHT.finditer(text):
        holder = match.group(1).strip().strip(".,;:'\"<>()[]")
        if holder and holder.lower() not in ("all rights reserved",):
            found.append(holder[:80])
    return found[:5]


def _classify(project: dict, owner_accounts: set, owner_names: set) -> str:
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
    def __init__(self, volume: Path, output: Path, owner_accounts, owner_names, shard_rows=200_000):
        self.volume, self.output = volume, output
        self.owner_accounts = {account.lower() for account in owner_accounts}
        self.owner_names = {name.lower() for name in owner_names if name}
        self.shard_rows = shard_rows
        self.files = 0
        self.bytes = 0
        self.shard, self.shard_index, self.shard_count = None, 0, 0
        self.extensions, self.languages, self.top_folders = Counter(), Counter(), Counter()
        self.skipped_folders, self.errors = Counter(), 0
        self.projects = []
        self._stats_store = {}
        self.started = time.time()
        self.projects_stream = open(output / "projects.jsonl", "w", encoding="utf-8")

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
        row = {"record_type": FILE_RECORD_TYPE, "path": os.path.relpath(path, self.volume), "size_bytes": entry_stat.st_size,
               "extension": suffix, "language": LANGUAGES.get(suffix, ""), "modified_at": int(entry_stat.st_mtime)}
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
        remotes = _remotes(os.path.join(folder, GIT_MARKER)) if GIT_MARKER in names else []
        licence_holders, licence_files = [], []
        for name in names:
            if name in LICENCE_NAMES:
                licence_files.append(name)
                licence_holders.extend(_holders(_read_head(os.path.join(folder, name))))
        row = {"record_type": PROJECT_RECORD_TYPE, "path": os.path.relpath(folder, self.volume), "top_folder": top,
               "name": os.path.basename(folder), "markers": markers, "git_remotes": remotes[:5],
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
        if any(name in PROJECT_MARKERS or name == GIT_MARKER for name in names) and depth > 0:
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
                    if name in SKIPPED_FOLDERS:
                        self.skipped_folders[name] += 1
                        continue
                    self.walk(entry.path, top, current, depth + 1)
                    continue
                entry_stat = entry.stat(follow_symlinks=False)
            except OSError:
                self.errors += 1
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
    args = parser.parse_args(argv)
    volume, output = Path(args.volume).resolve(), Path(args.output).resolve()
    repository = Path(__file__).resolve().parents[1]
    if output == repository or repository in output.parents:
        print("the inventory names private paths; write it outside the repository", file=sys.stderr)
        return 2
    if not volume.is_dir():
        print(f"not a folder: {volume}", file=sys.stderr)
        return 2
    output.mkdir(parents=True, exist_ok=False)
    roots = [str(volume / root) for root in args.root] if args.root else [
        entry.path for entry in os.scandir(volume) if entry.is_dir(follow_symlinks=False)
        and entry.name not in SKIPPED_FOLDERS and not entry.name.startswith(".")]
    inventory = Inventory(volume, output, args.owner_account, args.owner_name)
    summary = inventory.run(roots)
    print(json.dumps({key: summary[key] for key in ("files", "bytes", "projects", "projects_by_provenance_class",
                                                     "seconds", "errors")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
