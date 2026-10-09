"""Mode godot_demo_projects of the creative_assets line: one editable Godot project per demo project.

```text
godotengine/godot-demo-projects at the head commit of master (one tree read, one archive download of that
│   commit from codeload.github.com, every file then proven by its git blob identity)
├── licence: GitHub's licence interface and LICENSE.md agree on MIT at that commit (decide())
├── notices, project by project: its licence files (LICENSE*, *.LICENSE.md, license.txt, credits, ...)
│   and the licence lines of its READMEs, each read with a pattern table
│   ├── a licence off the allowlist (CC BY 3.0, BY-SA, NC, OFL, GPL, ...) refuses the project by name
│   ├── a licence file that names none, or an unversioned CC BY, refuses it as unclear
│   └── allowlisted licences (CC0 1.0, CC BY 4.0, Apache-2.0) join MIT in the expression, each with its
│       legal text from its publisher; the notice files travel verbatim as notices
├── files: every file of the project at the commit, its bytes proven by git blob identity
│   ├── copied byte for byte into project/: UTF-8 text a package path can hold, up to the review bound
│   │   (scenes, scripts, resources, shaders, import settings, the project's README and notices)
│   └── pinned in creative.json: images, sounds, fonts, models, SVG and larger text, by their raw address
│       at the commit, size and SHA-256 (computed from the archive's bytes once their blob identity holds)
├── checks before the package is kept: godot_project_check.py finds every res:// reference present or
│   pinned and the main scene declared; with Godot 4 installed (or --godot), a headless --import of the
│   whole project, else recorded as skipped
└── package (form template): project/, creative.json, creative_fetch.py, godot_project_check.py,
    test_creative_fetch.py, test_godot_project.py, README.md naming the main scene and scripts, LICENSE,
    UPSTREAM-LICENSE and one LICENSE-<id>.txt per further licence, ATTRIBUTION.md
```
"""
from __future__ import annotations

import hashlib
import html
import importlib.util
import json
import re
import shutil
import subprocess
import tarfile
from collections import Counter
from pathlib import Path, PurePosixPath
import urllib.parse

from loop_engine.core.library_ingestion.record_rules import git_blob_identity

from . import creative_assets as creative
from .licences import repository_licence
from .packaging import LICENCE_NAME, MAXIMUM_REVIEW_FILE_BYTES, UPSTREAM_LICENCE_NAME, PackageFile, SupplyPackage, build
from .reading import GITHUB_WEB_HOST, RAW_HOST, github_blob_address, https_address
from .records import (
    CREATIVE_ASSETS, GENERATED_CODE_LICENCE, GENERATED_TEST_FAILED, LICENCE_TEXT, REFUSAL_REASONS, UPSTREAM_VERBATIM,
    SupplyRecordError, fact_source, provenance, refusal, upstream_key)

GENERATOR_VERSION = "1.0.0"
REPOSITORY = "godotengine/godot-demo-projects"
BRANCH = "master"
ARCHIVE_HOST = "codeload.github.com"
HOSTS = (RAW_HOST, ARCHIVE_HOST) + creative.LICENCE_HOSTS
#: The commit archive is read once per run, streamed to disk and unpacked under the run folder.
MAXIMUM_ARCHIVE_BYTES = 2 * 1024 * 1024 * 1024
ARCHIVE_COMPLETE = ".archive-complete.json"
PROJECT_FOLDER = "project"
PROJECT_VARIANT = "project-media"
CHECKER, PROJECT_TESTS = "godot_project_check.py", "test_godot_project.py"
#: Text a project copies byte for byte, with the media type each suffix is served as (None: the shared table's).
TEXT_MEDIA = {".gd": creative.GDSCRIPT_MEDIA, ".tscn": "text/x-godot-scene", ".tres": "text/x-godot-resource",
              ".godot": "text/x-godot-project", ".import": "text/x-godot-import", ".uid": "text/plain",
              ".gdshader": "text/x-godot-shader", ".gdshaderinc": "text/x-godot-shader",
              ".escn": "text/x-godot-scene", ".cs": "text/x-csharp", ".csproj": "application/xml",
              ".sln": "text/plain", ".glsl": "text/x-glsl", ".po": "text/x-gettext-translation",
              ".pot": "text/x-gettext-translation", ".gdextension": "text/plain", ".cfg": None, ".md": None,
              ".txt": None, ".json": None, ".yml": None, ".yaml": None, ".csv": None, ".html": None, ".js": None,
              ".sh": None, ".xml": None, ".toml": None, ".ini": None, "": None}
#: A package path (catalogue_packages.placement_path): safe segments, at most eight deep and 200 characters.
_SEGMENT = re.compile(r"[A-Za-z0-9._@+-]{1,100}\Z")
MAXIMUM_PROJECT_PINNED_BYTES = 256 * 1024 * 1024
#: The command search path a headless Godot import runs with: the system's own folders, never the caller's PATH,
#: so the import starts only the Godot executable it is given and the tools of a standard system.
GODOT_IMPORT_PATH = "/usr/bin:/bin"
#: File names that are a licence or attribution notice: each must name a licence the line can read.
NOTICE_NAME = re.compile(r"(licen[cs]e|copying|notice|credits?|attribution|authors)", re.I)
README_NAME = re.compile(r"readme(\.[a-z]+)?\Z", re.I)
#: The licences a notice names, by pattern over its folded text, in the order they are tried.
LICENCE_PATTERNS = (
    ("CC-BY-SA", r"\bcc[- ]?by[- ]?sa\b|licenses/by-sa|share[- ]?alike"),
    ("CC-BY-NC", r"\bcc[- ]?by[- ]?nc|licenses/by-nc|non-?commercial"),
    ("CC-BY-ND", r"\bcc[- ]?by[- ]?nd\b|licenses/by-nd|no ?derivatives"),
    ("CC-BY-4.0", r"\bcc[- ]?by[- ]?4\.0|licenses/by/4\.0|attribution 4\.0"),
    ("CC-BY-3.0", r"\bcc[- ]?by[- ]?3\.0|licenses/by/3\.0|attribution 3\.0"),
    ("CC-BY-2.x", r"\bcc[- ]?by[- ]?2\.\d|licenses/by/2\.\d|attribution 2\.\d"),
    ("CC-BY-unversioned", r"\bcc[- ]?by\b(?![- ]?(?:sa|nc|nd|\d))"),
    ("CC0-1.0", r"\bcc0\b|creative commons zero|publicdomain/zero|\bcc-zero\b"),
    ("OFL-1.1", r"open font licen[cs]e|scripts\.sil\.org/ofl|\bofl\b"),
    ("Apache-2.0", r"apache licen[cs]e,? version 2\.0|\bapache-2\.0\b|licenses/license-2\.0"),
    ("MIT", r"\bmit licen[cs]e\b|permission is hereby granted, free of charge|licensed under (?:the )?mit\b"),
    ("GPL", r"\b(?:a|l)?gpl(?:v?\d)?\b|gnu (?:affero |lesser )?general public licen[cs]e"),
    ("Unlicense", r"\bunlicense\b"),
    ("BSD", r"\bbsd\b|redistribution and use in source and binary forms"),
    ("public-domain", r"public domain"),
    ("reserved", r"all rights reserved|used with permission|by permission of|not for redistribution"))
NOTICE_ALLOWED = ("CC0-1.0", "CC-BY-4.0", "Apache-2.0", "MIT", "Unlicense")
NOTICE_UNCLEAR = ("CC-BY-unversioned", "BSD", "public-domain")
_LICENCE_HEADING = re.compile(r"^#{1,6}\s*(licen[cs]es?|credits|attributions?)\b", re.I | re.M)


def folded(text: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(text)).strip().lower()


def named_licences(text: str) -> set:
    """The licence names a notice's text holds, by the pattern table."""
    body = folded(text)
    found = {name for name, pattern in LICENCE_PATTERNS if re.search(pattern, body)}
    if "CC0-1.0" in found:
        found.discard("public-domain")
    return found


def licence_sections(readme: str) -> list:
    """The text of each README section headed License(s), Credits or Attribution(s)."""
    sections = []
    for match in _LICENCE_HEADING.finditer(readme):
        level = len(readme[match.start():].split(" ", 1)[0])
        rest = readme[match.end():]
        end = re.search(r"^#{1,%d}\s" % level, rest, re.M)
        sections.append(rest[:end.start()] if end else rest)
    return sections


def notice_decision(path: str, text: str) -> tuple:
    """(allowed licence ids, refusal reason or None, detail) of one notice file or README."""
    name = PurePosixPath(path).name
    found = named_licences(text)
    if README_NAME.match(name) and not NOTICE_NAME.search(name):
        # A README counts by the licences its lines name; a licence section that names none is unclear.
        if any(not named_licences(section) for section in licence_sections(text)):
            return (), "asset_licence_unclear", f"{path}: a licence section names no licence"
    elif not found:
        return (), "asset_licence_unclear", f"{path} names no licence this line can read"
    outside = sorted(found - set(NOTICE_ALLOWED) - set(NOTICE_UNCLEAR))
    if outside:
        return (), "asset_licence_not_on_allowlist", f"{path} names {', '.join(outside)}"
    unclear = sorted(found & set(NOTICE_UNCLEAR))
    if unclear:
        return (), "asset_licence_unclear", f"{path} names {', '.join(unclear)}"
    return tuple(sorted(found & set(NOTICE_ALLOWED))), None, ""


def is_notice(path: str) -> bool:
    name = PurePosixPath(path).name
    return bool(NOTICE_NAME.search(name)) or bool(README_NAME.match(name))


def package_path(relative: str) -> "str | None":
    """The package path of a project file, or None when a catalogue package cannot hold that path."""
    path = f"{PROJECT_FOLDER}/{relative}"
    parts = path.split("/")
    if len(path) > 200 or len(parts) > 8 or any(not _SEGMENT.match(part) or part in (".", "..") or
                                                 part.casefold() == ".git" for part in parts):
        return None
    return path


def copyable(relative: str, data: bytes) -> bool:
    """Whether a project file travels byte for byte: known text, UTF-8 without NUL, a package path, in bound."""
    suffix = PurePosixPath(relative).suffix.lower()
    if suffix not in TEXT_MEDIA or len(data) > MAXIMUM_REVIEW_FILE_BYTES or b"\x00" in data \
            or package_path(relative) is None:
        return False
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


def projects_of(tree: list) -> dict:
    """{project folder: [tree entries]} for every folder holding a project.godot, nested projects kept apart."""
    roots = sorted({str(PurePosixPath(entry["path"]).parent) for entry in tree
                    if entry.get("type") == "blob" and PurePosixPath(entry["path"]).name == "project.godot"})
    found = {root: [] for root in roots}
    for entry in tree:
        if entry.get("type") != "blob":
            continue
        owners = [root for root in roots if entry["path"].startswith(root + "/")]
        if owners:
            found[max(owners, key=len)].append(entry)
    return found


def _check_module():
    """godot_project_check.py, loaded from the files every project package carries."""
    specification = importlib.util.spec_from_file_location("_godot_project_check", creative.SHIPPED / CHECKER)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def godot_import(godot: str, folder: Path, timeout: float = 300.0) -> str:
    """'passed' when Godot imports the whole project headless with exit status 0 and no parse error; the reason
    otherwise. A script or resource that does not parse fails the import. Other error lines are counted in the
    note, because a headless editor reports what its environment lacks (no display, no RenderingDevice for an
    editor tool script that runs a compute shader) while the project itself is sound. A C# project is skipped
    unless the executable is a Godot .NET build, which alone can read C# scripts."""
    if any(folder.rglob("*.cs")) and not any(mark in Path(godot).name.lower() for mark in ("mono", "dotnet")):
        return "skipped: a C# project needs the Godot .NET build"
    home = folder.parent / "godot-home"
    home.mkdir(exist_ok=True)
    try:
        done = subprocess.run([godot, "--headless", "--path", str(folder), "--import"], capture_output=True, text=True,
                              timeout=timeout, check=False, env={"HOME": str(home), "PATH": GODOT_IMPORT_PATH})
    except subprocess.TimeoutExpired:
        return f"failed: no answer within {timeout:.0f} s"
    lines = [_ANSI.sub("", line).strip() for line in (done.stdout + done.stderr).splitlines()]
    unparsed = [line for line in lines if "Parse Error" in line]
    if done.returncode != 0 or unparsed:
        return f"failed: exit {done.returncode}; {unparsed[0] if unparsed else ' '.join(lines[-3:])}"[:300]
    errors = [line for line in lines if line.startswith(("ERROR:", "SCRIPT ERROR:"))]
    return ("passed" + (f": {len(errors)} error lines from the headless editor, the first {errors[0][:160]!r}"
                        if errors else ""))[:300]


def project_readme(manifest: dict, notices, attribution) -> str:
    asset, project = manifest["asset"], manifest["asset"]["project"]
    variant = manifest["variants"][0] if manifest["variants"] else None
    scripts = ", ".join(f"`{path}`" for path in project["scripts"][:24]) or "none"
    if len(project["scripts"]) > 24:
        scripts += f" and {len(project['scripts']) - 24} more"
    media = (f"Its {len(variant['files'])} media files ({variant['total_bytes']:,} bytes: images, sounds, fonts, "
             "models and other files a package does not carry) are pinned in `creative.json` by their exact address "
             "at that commit, their size and their SHA-256; `creative_fetch.py` downloads them into `project/` and "
             "keeps only the recorded bytes." if variant else "Every file of the project is in `project/`.")
    notice_lines = ("The project's own licence notices, read file by file, name these licences; each is allowed "
                    "and travels as `LICENSE-<id>.txt` beside the notice itself:\n\n"
                    + "\n".join(f"- `{path}`: {', '.join(ids)}" for path, ids in notices)
                    if notices else "The project carries no licence notice of its own, so every file is under the "
                                    "repository's MIT licence.")
    credit = ("\n\nCC BY 4.0 asks that the authors be credited wherever the work is shared; the notices above name "
              "them: " + ", ".join(f"`{path}`" for path in attribution) + "." if attribution else "")
    fetch = (f"python creative_fetch.py fetch {PROJECT_VARIANT} .\n" if variant else "")
    main = "none declared"
    if project["main_scene"]:
        main = f"`{project['main_scene']}`" + (f" (`{project['main_scene_path']}`)"
                                               if project.get("main_scene_path") else "")
    return f"""# {asset['name']}: an editable Godot project ({project['path']})

The demo project `{project['path']}` of godotengine/godot-demo-projects at commit `{asset['commit']}`
({asset['source_page']}), made for Godot {', '.join(project['godot_features']) or '4'}. Its
{project['copied_files']} text files (scenes, scripts, resources, shaders and import settings) are copied byte
for byte into `project/`. {media}

Main scene: {main}. Scripts: {scripts}.

## Licence

The demo projects are licensed MIT by the Godot Engine contributors (the repository's LICENSE.md, carried as
`UPSTREAM-LICENSE`); the generated files are MIT (`LICENSE`). {notice_lines}

Package licence: {manifest['licence']['spdx']}.{credit}

## Open it

```bash
{fetch}python godot_project_check.py
godot --editor --path project
```

`godot_project_check.py` reads `project.godot`, the main scene and every quoted `res://` path of the project's
scenes, resources, scripts, shaders and import settings, and reports each one that is neither in `project/` nor
pinned. It runs nothing.

## Tests

```bash
python -m unittest test_creative_fetch test_godot_project
```

Offline: the fetcher against a loopback server with known-wrong bytes, sizes, paths and addresses, and the
project check against copies of the project with a reference removed or invented. With Godot 4 installed and
the media fetched, Godot imports the project headless.
"""


def unpack_archive(path: Path, folder: Path) -> dict:
    """Unpack a commit archive's regular files under ``folder`` (its top folder removed), refusing a member that
    would land outside it; a summary of what was written."""
    written = skipped = 0
    folder.mkdir(parents=True, exist_ok=True)
    base = folder.resolve()
    with tarfile.open(path, "r|*") as archive:
        for member in archive:
            parts = PurePosixPath(member.name).parts[1:]
            if not member.isfile() or not parts:
                skipped += 1
                continue
            if any(part in ("", ".", "..") for part in parts) or member.name.startswith("/"):
                return {"unsafe": member.name[:200]}
            target = base.joinpath(*parts)
            if base not in target.resolve().parents:
                return {"unsafe": member.name[:200]}
            target.parent.mkdir(parents=True, exist_ok=True)
            source = archive.extractfile(member)
            with open(target, "wb") as stream:
                shutil.copyfileobj(source, stream, 1024 * 1024)
            written += 1
    return {"files": written, "skipped": skipped}


def commit_files(reader, commit: str, folder: Path) -> dict:
    """The archive of the commit, unpacked under ``folder`` once per run folder; its download summary."""
    marker = folder / ARCHIVE_COMPLETE
    if marker.is_file():
        return json.loads(marker.read_text(encoding="utf-8"))
    shutil.rmtree(folder, ignore_errors=True)
    address = https_address(ARCHIVE_HOST, f"{REPOSITORY}/tar.gz/{commit}")
    answer = reader.digest(address, maximum_bytes=MAXIMUM_ARCHIVE_BYTES, inspect=lambda path: unpack_archive(
        path, folder), use_cache=False)
    if not answer.ok or not (answer.inspected or {}).get("files"):
        raise creative.AssetRefused("source_unreadable", f"the archive of {commit[:12]}: {answer.status} "
                                                         f"{answer.error} {answer.inspected}"[:280])
    summary = {"url": address, "sha256": answer.sha256, "size_bytes": answer.size_bytes,
               "retrieved_at": answer.retrieved_at, **answer.inspected}
    marker.write_text(json.dumps(summary, sort_keys=True), encoding="utf-8")
    return summary


def generate(reader, *, code_revision: str, licence_text: bytes, generated_on: str, staging: Path,
             archive_folder: Path, only=(), maximum_projects: int = 0, godot: "str | None" = None) -> tuple:
    """(built, refusals, facts, summary) of the demo projects: every project, or the chosen ones."""
    built, refused, facts, counts = [], [], {}, Counter()
    generator = {"identity": "tools/supply_lines/godot_demos.py", "version": GENERATOR_VERSION,
                 "code_revision": code_revision}
    vocabulary = REFUSAL_REASONS[CREATIVE_ASSETS]
    head = reader.github(f"repos/{REPOSITORY}/commits/{BRANCH}")
    if head.status != 200:
        return [], [refusal(CREATIVE_ASSETS, "source_unreadable", REPOSITORY, f"head answered {head.status}")], {}, {}
    commit = json.loads(head.body)["sha"]
    tree_answer = reader.github(f"repos/{REPOSITORY}/git/trees/{commit}?recursive=1")
    if tree_answer.status != 200:
        return [], [refusal(CREATIVE_ASSETS, "source_unreadable", REPOSITORY, "no tree")], {}, {}
    tree_document = json.loads(tree_answer.body)
    if tree_document.get("truncated"):
        return [], [refusal(CREATIVE_ASSETS, "source_unreadable", REPOSITORY, "the tree answer is truncated")], {}, {}
    licence = repository_licence(reader, REPOSITORY, commit)
    if not licence.allowed:
        return [], [refusal(CREATIVE_ASSETS, licence.refusal_reason(vocabulary), REPOSITORY,
                            f"{licence.reason} {licence.github_spdx}")], {}, {}
    facts[licence.sha256] = licence.text
    projects = projects_of(tree_document["tree"])
    chosen = [path for path in sorted(projects) if not only or path in only]
    if maximum_projects:
        chosen = chosen[:maximum_projects]
    summary = {"commit": commit, "projects_in_repository": len(projects), "chosen": len(chosen)}
    try:
        archive = commit_files(reader, commit, archive_folder / commit)
    except creative.AssetRefused as error:
        return [], [refusal(CREATIVE_ASSETS, error.reason, REPOSITORY, error.detail)], facts, summary
    summary["archive"] = {key: archive.get(key) for key in ("url", "sha256", "size_bytes", "files")}
    texts = creative.LicenceTexts(reader)
    checker = _check_module()
    licence_address = github_blob_address(REPOSITORY, commit, licence.path)
    tree_fact = fact_source(https_address("api.github.com", f"repos/{REPOSITORY}/git/trees/{commit}"),
                            tree_answer.retrieved_at, tree_answer.sha256, len(tree_answer.body), "repository_facts",
                            spdx="NOASSERTION", basis="github_tree_read_for_paths_sizes_and_blob_identities")
    context = {"commit": commit, "licence": licence, "licence_address": licence_address, "tree_fact": tree_fact,
               "texts": texts, "checker": checker, "generator": generator, "licence_text": licence_text,
               "generated_on": generated_on, "staging": staging, "godot": godot, "counts": counts,
               "files": archive_folder / commit, "retrieved_at": archive["retrieved_at"]}
    for root in chosen:
        try:
            built.append(_project(root, projects[root], context))
        except creative.AssetRefused as error:
            refused.append(refusal(CREATIVE_ASSETS, error.reason, root, error.detail))
        except SupplyRecordError as error:
            refused.append(refusal(CREATIVE_ASSETS, creative.refusal_for(error), root, str(error)[:280]))
    summary.update({"counts": dict(counts), "godot": godot or "not installed: import check skipped"})
    return built, refused, facts, summary


def _project_files(root: str, entries, files: Path, commit: str) -> dict:
    """{relative path: (bytes, raw address, SHA-256)} of every file of the project, each proven equal to its git
    blob at the commit; a file that is missing or differs refuses the project."""
    found = {}
    for entry in entries:
        relative = entry["path"][len(root) + 1:]
        path = files.joinpath(*PurePosixPath(entry["path"]).parts)
        data = path.read_bytes() if path.is_file() else None
        if data is None or git_blob_identity(data) != entry["sha"]:
            raise creative.AssetRefused("project_file_unreadable", f"{entry['path']} is missing from the archive or "
                                                                   "differs from its blob")
        address = https_address(RAW_HOST, f"{REPOSITORY}/{commit}/{urllib.parse.quote(entry['path'])}")
        found[relative] = (data, address, hashlib.sha256(data).hexdigest())
    return found


def _project(root: str, entries, context: dict) -> tuple:
    commit, licence, checker, counts = context["commit"], context["licence"], context["checker"], context["counts"]
    project_files = _project_files(root, entries, context["files"], commit)
    # The notices decide first: a project with a licence off the allowlist is refused before it is packaged.
    allowed, notices, attribution = set(), [], []
    for relative, (data, _address, _digest) in sorted(project_files.items()):
        if not is_notice(relative):
            continue
        ids, reason, detail = notice_decision(relative, data.decode("utf-8", "replace"))
        if reason:
            raise creative.AssetRefused(reason, f"{root}/{detail}")
        if ids:
            notices.append((f"{PROJECT_FOLDER}/{relative}", ids))
            allowed |= set(ids)
            if "CC-BY-4.0" in ids:
                attribution.append(f"{PROJECT_FOLDER}/{relative}")
    copied = {relative: held for relative, held in project_files.items() if copyable(relative, held[0])}
    pinned = {relative: held for relative, held in project_files.items() if relative not in copied}
    if any(len(data) > creative.MAXIMUM_PINNED_FILE_BYTES for data, _address, _digest in pinned.values()) or \
            sum(len(data) for data, _address, _digest in pinned.values()) > MAXIMUM_PROJECT_PINNED_BYTES:
        raise creative.AssetRefused("project_above_the_pin_bound", f"{root}: a media file or the media together "
                                                                  "exceed the pin bound")
    blobs = {entry["path"][len(root) + 1:]: entry["sha"] for entry in entries}
    rows = [{"path": f"{PROJECT_FOLDER}/{relative}", "url": address, "size_bytes": len(data), "sha256": digest,
             "role": "media", "git_blob": blobs[relative]}
            for relative, (data, address, digest) in sorted(pinned.items())]
    counts["copied_files"] += len(copied)
    counts["pinned_files"] += len(rows)
    variants = [{"id": PROJECT_VARIANT, "format": "media", "resolution": None, "main": rows[0]["path"],
                 "total_bytes": sum(row["size_bytes"] for row in rows), "files": rows}] if rows else []
    config_text = copied.get("project.godot", (b"",))[0].decode("utf-8", "replace")
    if not config_text:
        raise creative.AssetRefused("project_unreadable", f"{root}/project.godot is not copied text")
    try:
        config = checker.read_config(config_text)
    except ValueError as error:
        raise creative.AssetRefused("project_unreadable", f"{root}/project.godot: {error}") from None
    application = config.get("application", {})
    features = re.findall(r'"([^"]+)"', application.get("config/features", ""))
    scripts = sorted(relative for relative in copied if relative.endswith((".gd", ".cs")))
    scenes = sorted(relative for relative in copied if relative.endswith((".tscn", ".escn")))
    expression = " AND ".join([GENERATED_CODE_LICENCE] + sorted(allowed - {GENERATED_CODE_LICENCE}))
    project_type = creative.AssetType.GODOT_PROJECT.value
    asset = {"name": checker.unquoted(application.get("config/name", "")) or root, "type": project_type,
             "source_page": https_address(GITHUB_WEB_HOST, f"{REPOSITORY}/tree/{commit}/{root}"), "commit": commit,
             "asset_role": creative.ASSET_ROLES[project_type],
             "credit": "the Godot Engine contributors (godotengine/godot-demo-projects)",
             "project": {"path": root, "folder": PROJECT_FOLDER, "main_scene": checker.main_scene(config),
                         "scripts": scripts, "scenes": scenes, "godot_features": features,
                         "copied_files": len(copied), "pinned_files": len(rows)}}
    manifest = creative.manifest_record(
        REPOSITORY, root, asset, {"spdx": expression, "repository_licence": {"url": context["licence_address"],
                                                                            "sha256": licence.sha256},
                                  "notices": [{"path": path, "licences": list(ids)} for path, ids in notices]},
        variants, PROJECT_VARIANT if rows else None, (RAW_HOST,))
    name = f"godot-demo-{creative.slug(root)}"
    folder = context["staging"] / name
    shutil.rmtree(folder, ignore_errors=True)
    (folder / PROJECT_FOLDER).mkdir(parents=True)
    for relative, (data, _address, _digest) in copied.items():
        target = folder / PROJECT_FOLDER / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    scene = asset["project"]["main_scene"] or ""
    if scene.startswith("uid://"):
        owner = checker.uid_owners(folder / PROJECT_FOLDER).get(scene)
        if owner:
            asset["project"]["main_scene_path"] = owner
    elif scene.startswith("res://"):
        asset["project"]["main_scene_path"] = scene[len("res://"):]
    problems = checker.problems(folder / PROJECT_FOLDER, manifest)
    if problems:
        shutil.rmtree(folder, ignore_errors=True)
        reason = "project_unreadable" if problems[0].startswith("project.godot") else "project_reference_missing"
        raise creative.AssetRefused(reason, f"{root}: {problems[0]}"[:240] + (f" (+{len(problems) - 1} more)"
                                                                            if len(problems) > 1 else ""))
    manifest_text = json.dumps(manifest, indent=1, ensure_ascii=False) + "\n"
    shipped_rows = [(creative.FETCHER, "executable_tool"), (CHECKER, "executable_tool"),
                    (creative.FETCH_TESTS, "executable_tool"), (PROJECT_TESTS, "executable_tool")]
    for file_name, _role in shipped_rows:
        (folder / file_name).write_bytes(creative.shipped(file_name))
    (folder / creative.MANIFEST_NAME).write_text(manifest_text, encoding="utf-8")
    godot = context["godot"]
    try:
        passed, count, skipped, output = creative.run_package_tests(folder, ("test_creative_fetch",
                                                                             "test_godot_project"))
        imported = "skipped: godot is not installed on the generating machine"
        if godot and passed:
            for relative, (data, _address, _digest) in pinned.items():
                target = folder / PROJECT_FOLDER / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            imported = godot_import(godot, folder / PROJECT_FOLDER)
    finally:
        shutil.rmtree(folder, ignore_errors=True)
    if not passed:
        raise SupplyRecordError(GENERATED_TEST_FAILED, output[-280:])
    if imported.startswith("failed"):
        raise creative.AssetRefused("project_import_failed", f"{root}: {imported}")
    counts["godot_import_" + imported.split(":")[0]] += 1
    notice_paths = {path for path, _ids in notices}
    files = [PackageFile(f"{PROJECT_FOLDER}/{relative}", data, "other", UPSTREAM_VERBATIM,
                         {"url": address, "sha256": digest}, notice=f"{PROJECT_FOLDER}/{relative}" in notice_paths,
                         media_type=TEXT_MEDIA.get(PurePosixPath(relative).suffix.lower()))
             for relative, (data, address, digest) in sorted(copied.items())]
    files += [PackageFile(file_name, creative.shipped(file_name), role) for file_name, role in shipped_rows]
    files += [PackageFile(creative.MANIFEST_NAME, manifest_text.encode("utf-8"), "other"),
              PackageFile("README.md", project_readme(manifest, notices, attribution).encode("utf-8"), "other"),
              PackageFile(LICENCE_NAME, context["licence_text"], "other", LICENCE_TEXT),
              PackageFile(UPSTREAM_LICENCE_NAME, licence.text, "other", LICENCE_TEXT,
                          {"url": context["licence_address"], "sha256": licence.sha256})]
    package_facts = [fact_source(context["licence_address"], context["tree_fact"]["retrieved_at"], licence.sha256,
                                 len(licence.text), "licence_text", spdx=licence.spdx,
                                 basis="github_licence_interface_and_text_agree"),
                     context["tree_fact"]]
    for spdx in sorted(allowed - {GENERATED_CODE_LICENCE}):
        text = context["texts"].get(spdx)
        files.append(PackageFile(f"LICENSE-{spdx}.txt", text["bytes"], "other", LICENCE_TEXT,
                                 {"url": text["url"], "sha256": text["sha256"]}))
        package_facts.append(context["texts"].fact(spdx))
    for relative, (data, address, digest) in sorted(project_files.items()):
        package_facts.append(fact_source(address, context["retrieved_at"], digest, len(data), "data_source",
                                         spdx=expression, evidence_sha256=licence.sha256,
                                         basis="git_blob_at_the_pinned_commit_read_from_its_archive_under_the_"
                                               "repository_licence_and_the_project_notices"))
    supply = SupplyPackage(
        line=CREATIVE_ASSETS, identity=f"{REPOSITORY}:{root}",
        key=upstream_key(CREATIVE_ASSETS, f"{REPOSITORY}:{root}"),
        kind="template", native_format="godot_project", form="template", name=name,
        description=(f"{asset['name']}: the editable Godot demo project {root} with its scenes and scripts copied "
                     "byte for byte, its media pinned by SHA-256 with a verifying fetcher, and a check that every "
                     "res:// reference resolves."),
        files=files, licence_expression=expression,
        provenance=provenance("github_repository", REPOSITORY, root, commit, package_facts, context["generator"]),
        placements=[{"harness": "reference", "path": f"projects/{name}/", "basis": "documented_layout",
                     "scope": "project", "support": "unverified"}],
        effects=list(creative.EFFECTS), credentials=[],
        tests={"files": [creative.FETCH_TESTS, PROJECT_TESTS],
               "command": "python -m unittest test_creative_fetch test_godot_project", "result": "passed",
               "tests_run": count, "skipped": skipped, "network": "loopback_only", "godot_import": imported,
               "references": "every res:// reference present or pinned"},
        repository={"name": REPOSITORY, "project": root, "asset_type": asset["type"],
                    "asset_role": asset["asset_role"], "commit": commit, "copied_files": len(copied),
                    "pinned_files": len(rows), "pinned_bytes": variants[0]["total_bytes"] if variants else 0,
                    "notices": len(notices), "stars": 0},
        generated_on=context["generated_on"], comparison_text=f"{REPOSITORY}:{root}")
    return build(supply)
