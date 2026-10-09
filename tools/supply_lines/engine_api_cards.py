"""Line engine_api_cards: one version-pinned API contract card per class of a pinned engine release.

```text
engine_api_cards (one card format, tools/engine_api_cards; one adapter per engine)
├── godot adapter, pinned to the tag 4.7.2-stable
│   ├── surface: the official build's --doctool dump (classes, Variant types, the global scopes)
│   ├── facts: the tag's commit and tree (GitHub), then LICENSE.txt, COPYRIGHT.txt, the class reference file of
│   │   every class and editor/project_upgrade/renames_map_3_to_4.cpp at that commit, each proven by git blob
│   │   identity and pinned by its raw.githubusercontent.com address and SHA-256; the release asset the build
│   │   comes from, by GitHub's published SHA-256, streamed once to prove the build is its member
│   ├── licence: GitHub's licence interface and LICENSE.txt agree on MIT, and the last COPYRIGHT.txt stanza that
│   │   matches each file read is Expat (MIT); the documentation site (CC BY 3.0) is never read
│   ├── the class reference at the tag must have exactly the dump's structure; it gives the text, the dump the
│   │   surface; the build's version names the commit the tag points at
│   └── native check: one run of the same build over every card (tools/engine_api_cards/godot_verify.gd)
├── one package per class: README.md (and members-N.md for a large class), api.json, component.json,
│   api_card.py, test_api_card.py, verification/native.json, LICENSE (Baltor's MIT), UPSTREAM-LICENSE (the
│   engine's LICENSE.txt, verbatim) and ATTRIBUTION.md; the package's own tests pass before it is kept
├── refused by name: an unreadable fact, a licence off the allowlist, a build that is not the release's, a class
│   with no surface or no class reference, a class reference whose structure differs, missing, stale, invalid or
│   failed native evidence, a failing package test, and the shared packaging refusals
└── job key: component.json job.engine, job.version and job.class, so a second card of one class is one job
```

The line calls no model. A package is a candidate until qualification and the ongoing independent review.
"""
from __future__ import annotations

import fnmatch
import hashlib
import json
import re
import shutil
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, replace
from pathlib import Path

from creative_originals.assemble import Entry, run_package_tests
from engine_api_cards import bbcode, cards, godot_native, godot_renames, jsdoc_reference, node_native
from engine_api_cards import typescript_declarations
from engine_api_cards.godot_reference import ClassKind, ReferenceError, inheritance, read_reference

from .creative_originals import derived_effects
from .licences import LICENCE_UNKNOWN, decide, repository_licence
from .packaging import (LICENCE_NAME, UPSTREAM_LICENCE_NAME, UPSTREAM_NOTICE_NAME, PackageFile, SupplyPackage, build,
                        notice_files)
from .reading import RAW_HOST, github_blob_address, https_address, pinned_files
from .records import (ENGINE_API_CARDS, GENERATED, GENERATED_CODE_LICENCE, GENERATED_TEST_FAILED, LICENCE_TEXT,
                      SupplyRecordError, fact_source, provenance, refusal, upstream_key)

GENERATOR_VERSION = "1.0.0"
NATIVE_FORMAT = "engine_api_card"
#: The Godot release the adapter is pinned to, and where its facts live.
GODOT, GODOT_TITLE = "godot", "Godot"
GODOT_REPOSITORY = "godotengine/godot"
GODOT_TAG = "4.7.2-stable"
GODOT_STATE_SCOPE = "godot_4_7"
LICENCE_PATH, COPYRIGHT_PATH = "LICENSE.txt", "COPYRIGHT.txt"
#: The class reference files of the engine repository: the core classes, then each module's and platform's.
REFERENCE_PATH = re.compile(r"(?:doc/classes|modules/[^/]+/doc_classes|platform/[^/]+/doc_classes)/([^/]+)\.xml")
#: The format of the Godot class reference text, the api type of its editor-only classes and what their cards say.
GODOT_TEXT_FORMAT, GODOT_EDITOR_API = "BBCode", "editor"
GODOT_EDITOR_NOTE = ("**Editor only:** this class exists in the editor, for editor plugins and `@tool` scripts; an "
                     "exported project does not have it.")
#: The type of a file in a git tree listing.
BLOB_TYPE = "blob"
#: The licence COPYRIGHT.txt names for the engine's own MIT files (Debian's short name for MIT).
EXPAT = "Expat"
API_HOST, DOWNLOAD_HOSTS = "api.github.com", ("github.com", "objects.githubusercontent.com",
                                               "release-assets.githubusercontent.com")
DOCS_HOST = "docs.godotengine.org"
HOSTS = (RAW_HOST, API_HOST) + DOWNLOAD_HOSTS
#: The release asset a build is unpacked from is the build's file name with this suffix (the official naming).
ASSET_SUFFIX = ".zip"
DIGEST_PREFIX = "sha256:"
MAXIMUM_ASSET_BYTES = 256 * 1024 * 1024
#: What every Godot card says it does not establish.
LIMITS = GODOT_LIMITS = ("The surface is the official Linux x86_64 editor build's: a class, member or setting that only another "
          "platform, a .NET build or a module this build lacks registers is not listed. The text is the class "
          "reference at the tag, converted from BBCode; references to other classes are names, not links. "
          "Nothing here was loaded by a harness.")
#: The refusal each reason of tools/engine_api_cards/godot_native.read_evidence gives.
EVIDENCE_REFUSALS = {"evidence_unreadable": "native_evidence_invalid", "evidence_invalid": "native_evidence_invalid",
                     "evidence_stale": "native_evidence_stale", "native_check_failed": "native_check_failed"}
#: The package file roles: a card's Python modules are tools a harness may run; everything else is read.
EXECUTABLE_ROLE, OTHER_ROLE, PYTHON_SUFFIX = "executable_tool", "other", ".py"
#: The refusals of a fact the run could not read: a run that gives one is not complete and withdraws nothing.
UNREAD_REASONS = ("source_unreadable",)
#: The refusals the shared packaging gives one package.
PACKAGE_REASONS = ("blocked_by_static_check", "package_above_review_bound", "package_path_invalid")
_RAN = re.compile(r"^Ran (\d+) tests? in ", re.MULTILINE)


class LineStopped(RuntimeError):
    """The whole engine release cannot be carded: every class is refused with this reason."""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason, self.detail = reason, detail


def release_numbers(tag: str) -> tuple:
    """(version, api version) of a tag: 4.7.2-stable is version 4.7.2 and API version 4.7."""
    version = tag.split("-", 1)[0]
    return version, ".".join(version.split(".")[:2])


#: The fields of a Debian machine-readable copyright stanza the licence decision reads, and how a field's value
#: continues on the next line.
FILES_FIELD, LICENSE_FIELD, CONTINUATION = "Files", "License", (" ", "\t")


def copyright_stanzas(text: str) -> list:
    """(file patterns, licence) of every Files stanza of a Debian machine-readable copyright file, in order. A
    field's value continues on the lines indented under it; the licence is the License field's first line, its
    short name or expression ("Expat", "Expat and Zlib")."""
    stanzas = []
    for paragraph in re.split(r"\n\s*\n", text):
        fields, first_lines, current = {}, {}, None
        for line in paragraph.split("\n"):
            if line.startswith(CONTINUATION) and current:
                fields[current] += " " + line.strip()
            elif ":" in line:
                current, _, value = line.partition(":")
                fields[current] = first_lines[current] = value.strip()
        if FILES_FIELD in fields and LICENSE_FIELD in first_lines:
            stanzas.append((fields[FILES_FIELD].split(), first_lines[LICENSE_FIELD]))
    return stanzas


def governing_licence(path: str, stanzas: list) -> "str | None":
    """The licence of the last stanza whose patterns match a path (the Debian format's rule), or None."""
    found = None
    for patterns, licence in stanzas:
        if any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns):
            found = licence
    return found


@dataclass
class EngineSources:
    """Everything one adapter read for one release: the surface, the documentation, the pinned facts."""

    release: cards.EngineRelease
    dump: dict  # class -> (dump path, bytes)
    references: dict  # class -> ClassReference (dump)
    documentation: dict  # class -> ClassReference (repository)
    reference_paths: dict  # class -> repository path
    pinned: dict  # repository path -> pinned file (url, sha256, bytes, retrieved_at, blob)
    licence: dict  # LICENSE.txt pinned, with the decision's evidence
    copyright: dict  # COPYRIGHT.txt pinned
    renames: dict  # class -> rename rows
    renames_map: "dict | None"
    release_asset: "dict | None"
    refusals: list = field(default_factory=list)
    summary: dict = field(default_factory=dict)
    #: The adapter's text interface for one class (a bbcode.Context, a JsDocText); None writes Godot BBCode.
    text_for: object = None
    #: The licence file's path at the commit, the basis its class text facts name, what every card says it does
    #: not establish, and the store state the release keeps.
    licence_path: str = "LICENSE.txt"
    text_basis: str = "copyright_file_stanza_expat"
    limits: str = ""
    state_scope: str = ""
    #: A package registry's record of the release the build came from (role package_metadata), when there is one.
    metadata: "dict | None" = None
    #: The licence of every package (Baltor's generated files and the engine's text), and the engine repository's
    #: notice files a package carries (Apache-2.0 section 4(d)).
    licence_expression: str = GENERATED_CODE_LICENCE
    notices: list = field(default_factory=list)
    #: The text whose copyright lines a card quotes, when it is not the licence (an Apache NOTICE file).
    copyright_text: bytes = b""


#: How the licence of the tag was decided: GitHub's interface at the tag, or (when it names none there) GitHub's
#: interface at the default branch for the same licence blob; LICENSE.txt's own text agrees either way.
LICENCE_AT_THE_TAG, LICENCE_OF_THE_SAME_BLOB = ("github_licence_at_the_tag_and_text_agree",
                                               "github_licence_of_the_same_blob_at_the_default_branch_and_text_agree")


def tag_licence(reader, repository: str, commit: str, pinned_licence: dict) -> tuple:
    """(decision, basis) of a repository's licence at a commit.

    GitHub's licence interface names no licence for godotengine/godot at any commit ref (NOASSERTION, October 9,
    2026), and MIT at its default branch for the very same LICENSE.txt blob. When the commit's answer names none
    and the default branch's answer is for a file with the commit's own blob identity, that answer is the
    interface's signal for these bytes; the text must still match it (licences.decide)."""
    decision = repository_licence(reader, repository, commit)
    if decision.allowed or decision.reason != LICENCE_UNKNOWN or not decision.matched_spdx:
        return decision, LICENCE_AT_THE_TAG
    answer = reader.github(f"repos/{repository}/license")
    if answer.status != 200:
        return decision, LICENCE_AT_THE_TAG
    document = json.loads(answer.body)
    if document.get("sha") != pinned_licence.get("blob") or document.get("path") != decision.path:
        return decision, LICENCE_AT_THE_TAG
    spdx = (document.get("license") or {}).get("spdx_id")
    return decide(repository, commit, (decision.path, decision.text, spdx)), LICENCE_OF_THE_SAME_BLOB


def _fact(pinned: dict, role: str, basis: str, spdx: str = GENERATED_CODE_LICENCE) -> dict:
    return fact_source(pinned["url"], pinned["retrieved_at"], pinned["sha256"],
                       pinned.get("size_bytes", len(pinned.get("bytes", b""))), role, spdx=spdx, basis=basis)


def _release_asset(reader, engine, tag: str) -> dict:
    """The release asset the build comes from, its published SHA-256 checked and the build proven its member."""
    answer = reader.get(https_address(API_HOST, f"repos/{GODOT_REPOSITORY}/releases/tags/{tag}"))
    if answer.status != 200:
        raise LineStopped("source_unreadable", f"the release {tag} did not answer ({answer.status})")
    name = Path(engine.path).name + ASSET_SUFFIX
    asset = next((row for row in json.loads(answer.body).get("assets", []) if row.get("name") == name), None)
    published = str((asset or {}).get("digest") or "")
    if asset is None or not published.startswith(DIGEST_PREFIX):
        raise LineStopped("engine_binary_unverified", f"the release publishes no digest for {name}")
    member = Path(engine.path).name

    def members(path):
        import zipfile
        with zipfile.ZipFile(path) as archive:
            with archive.open(member) as stream:
                digest = hashlib.sha256()
                for block in iter(lambda: stream.read(1 << 20), b""):
                    digest.update(block)
        return {"member": member, "sha256": digest.hexdigest()}

    digested = reader.digest(asset["browser_download_url"], published={"sha256": published[len(DIGEST_PREFIX):]},
                             maximum_bytes=MAXIMUM_ASSET_BYTES, inspect=members)
    if not digested.ok or digested.sha256 != published[len(DIGEST_PREFIX):]:
        raise LineStopped("engine_binary_unverified", f"{name}: the download does not match its published digest")
    if (digested.inspected or {}).get("sha256") != engine.sha256:
        raise LineStopped("engine_binary_unverified", f"{member} is not the build in {name}")
    return {"url": asset["browser_download_url"], "sha256": digested.sha256, "size_bytes": digested.size_bytes,
            "retrieved_at": digested.retrieved_at, "member": member}


def read_godot(reader, engine, workspace: Path, *, tag: str = GODOT_TAG, bind_release: bool = True,
               only=()) -> EngineSources:
    """Read the pinned Godot release: the build's dump, the tag's facts and the licence (the class reference of
    only the classes named, when some are); raises LineStopped."""
    version, api_version = release_numbers(tag)
    dump = godot_native.dump(engine, Path(workspace) / "dump")
    references, refusals, located = {}, [], {}
    for path, data in sorted(dump.items()):
        try:
            reference = read_reference(data)
        except ReferenceError as error:
            refusals.append(refusal(ENGINE_API_CARDS, "reference_unreadable", path, str(error)))
            continue
        if reference.name in references:
            refusals.append(refusal(ENGINE_API_CARDS, "duplicate_class", reference.name, path))
            continue
        references[reference.name], located[reference.name] = reference, (path, data)
    head = reader.github(f"repos/{GODOT_REPOSITORY}/commits/{tag}")
    if head.status != 200:
        raise LineStopped("source_unreadable", f"the tag {tag} has no readable commit")
    commit = json.loads(head.body)["sha"]
    build_hash = engine.version.rsplit(".", 1)[-1]
    if not build_hash or not commit.startswith(build_hash):
        raise LineStopped("engine_binary_unverified", f"the build {engine.version} is not the commit {commit[:12]}")
    tree = reader.github(f"repos/{GODOT_REPOSITORY}/git/trees/{commit}?recursive=1")
    if tree.status != 200:
        raise LineStopped("source_unreadable", f"no tree at {commit[:12]}")
    paths = {}
    for entry in json.loads(tree.body).get("tree", []):
        match = REFERENCE_PATH.fullmatch(str(entry.get("path", "")))
        if match and entry.get("type") == BLOB_TYPE:
            paths.setdefault(match.group(1), []).append(entry["path"])
    wanted = [LICENCE_PATH, COPYRIGHT_PATH, godot_renames.MAP_PATH]
    reference_paths = {}
    for name in sorted(references):
        if only and name not in only:
            continue
        found = paths.get(name, [])
        if len(found) == 1:
            reference_paths[name] = found[0]
            wanted.append(found[0])
        else:
            reason = "documentation_missing" if not found else "duplicate_class"
            refusals.append(refusal(ENGINE_API_CARDS, reason, name, ", ".join(found)[:200]))
    pinned, missing = pinned_files(reader, GODOT_REPOSITORY, commit, wanted)
    for required in (LICENCE_PATH, COPYRIGHT_PATH):
        if required in missing:
            raise LineStopped("source_unreadable", required)
    decision, licence_basis = tag_licence(reader, GODOT_REPOSITORY, commit, pinned[LICENCE_PATH])
    if not decision.allowed:
        raise LineStopped(decision.reason, f"{GODOT_REPOSITORY} at {commit[:12]}: {decision.evidence()}")
    if decision.path != LICENCE_PATH or decision.sha256 != pinned[LICENCE_PATH]["sha256"]:
        raise LineStopped("licence_signals_disagree", f"GitHub names {decision.path}, not {LICENCE_PATH}")
    stanzas = copyright_stanzas(pinned[COPYRIGHT_PATH]["bytes"].decode("utf-8"))
    documentation = {}
    for name, path in sorted(reference_paths.items()):
        if path in missing:
            refusals.append(refusal(ENGINE_API_CARDS, "source_unreadable", name, path))
            continue
        governing = governing_licence(path, stanzas)
        if governing != EXPAT:
            refusals.append(refusal(ENGINE_API_CARDS, "licence_not_on_allowlist", name, f"{path}: {governing}"))
            continue
        try:
            documentation[name] = read_reference(pinned[path]["bytes"])
        except ReferenceError as error:
            refusals.append(refusal(ENGINE_API_CARDS, "reference_unreadable", name, str(error)))
    renames_map, renames, outcomes = pinned.get(godot_renames.MAP_PATH), {}, {}
    if renames_map is not None and governing_licence(godot_renames.MAP_PATH, stanzas) == EXPAT:
        chains, _children = inheritance(references)
        entries = godot_renames.read_map(renames_map["bytes"].decode("utf-8"), set(references))
        renames, outcomes = godot_renames.attach(entries, references, chains)
    else:
        renames_map = None
    asset = _release_asset(reader, engine, tag) if bind_release else None
    binary = Path(engine.path).name
    release = cards.EngineRelease(
        name=GODOT, title=GODOT_TITLE, release=tag, version=version, api_version=api_version,
        repository=GODOT_REPOSITORY, commit=commit, binary_name=binary, binary_sha256=engine.sha256,
        binary_version=engine.version, docs_address=https_address(DOCS_HOST, f"en/{api_version}"),
        syntax=cards.card_module().GODOT_SYNTAX, renames_from_version=godot_renames.FROM_VERSION,
        surface_source=(f"dumped with `--doctool` from the official {GODOT_TITLE} {tag} build `{binary}` "
                        f"(SHA-256 `{engine.sha256}`)"),
        surface_phrase="the surface the engine binary itself reports", text_format=GODOT_TEXT_FORMAT,
        licence=GENERATED_CODE_LICENCE, editor_api_types=(GODOT_EDITOR_API,), editor_note=GODOT_EDITOR_NOTE)
    licence = dict(pinned[LICENCE_PATH], evidence=decision.evidence(), basis=licence_basis)
    summary = {"dump_classes": len(dump), "dump_sha256": godot_native.dump_digest(dump),
               "reference_files": len(reference_paths), "renames": outcomes,
               "release_asset": asset["url"] if asset else None}
    return EngineSources(release, located, references, documentation, reference_paths, pinned, licence,
                         pinned[COPYRIGHT_PATH], renames, renames_map, asset, refusals, summary,
                         licence_path=LICENCE_PATH, limits=GODOT_LIMITS, state_scope=GODOT_STATE_SCOPE)


#: The three.js release the adapter is pinned to: the tag, the npm package built from it and its entry.
THREEJS, THREEJS_TITLE = "threejs", "three.js"
THREEJS_REPOSITORY, THREEJS_TAG = "mrdoob/three.js", "r186"
THREEJS_PACKAGE, THREEJS_VERSION = "three", "0.186.1"
THREEJS_STATE_SCOPE = "threejs_r186"
THREEJS_LICENCE_PATH, THREEJS_ENTRY, THREEJS_MODULE = "LICENSE", "src/Three.js", "build/three.module.js"
REGISTRY_HOST, THREEJS_DOCS_HOST = "registry.npmjs.org", "threejs.org"
THREEJS_HOSTS = (RAW_HOST, REGISTRY_HOST)
#: An npm package's files sit under this folder of its tarball; integrity is SHA-512, base64, after this prefix; a
#: member path may not climb out of the folder it is unpacked into.
PACKAGE_FOLDER, INTEGRITY_PREFIX, PARENT_SEGMENT = "package", "sha512-", ".."
MAXIMUM_PACKAGE_BYTES = 64 * 1024 * 1024
THREEJS_LIMITS = ("The surface is what the JSDoc of the library's own source declares for the classes its main "
                  "entry exports, each confirmed by importing the published module in Node: a member its JSDoc "
                  "marks private, or does not document, is not listed, and the types are the JSDoc's own claims, "
                  "which a running module cannot confirm. The text is that JSDoc; references to other classes are "
                  "names, not links. Nothing here was loaded by a harness.")


def _package_files(path: Path, folder: Path) -> dict:
    """Unpack an npm tarball's regular files under folder (nothing outside it, no link) and describe it."""
    import base64
    import tarfile
    digest = hashlib.sha512()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True)
    count = 0
    with tarfile.open(path, "r:gz") as archive:
        for member in archive.getmembers():
            parts = Path(member.name).parts
            if not member.isfile() or not parts or parts[0] != PACKAGE_FOLDER or PARENT_SEGMENT in parts \
                    or Path(member.name).is_absolute():
                continue
            target = folder.joinpath(*parts[1:])
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.extractfile(member).read())
            count += 1
    return {"integrity": INTEGRITY_PREFIX + base64.b64encode(digest.digest()).decode("ascii"), "files": count}


def read_threejs(reader, workspace: Path, *, only=()) -> EngineSources:
    """Read the pinned three.js release: the npm package built from the tag (its integrity checked), the classes its
    main entry exports with their JSDoc, and the licence; raises LineStopped."""
    record = reader.get(https_address(REGISTRY_HOST, f"{THREEJS_PACKAGE}/{THREEJS_VERSION}"))
    if record.status != 200:
        raise LineStopped("source_unreadable", f"{THREEJS_PACKAGE}@{THREEJS_VERSION}: the registry did not answer")
    document = json.loads(record.body)
    distribution = document.get("dist") or {}
    head = reader.github(f"repos/{THREEJS_REPOSITORY}/commits/{THREEJS_TAG}")
    if head.status != 200:
        raise LineStopped("source_unreadable", f"the tag {THREEJS_TAG} has no readable commit")
    commit = json.loads(head.body)["sha"]
    if document.get("gitHead") != commit:
        raise LineStopped("engine_binary_unverified", f"{THREEJS_PACKAGE}@{THREEJS_VERSION} was built from "
                                                      f"{document.get('gitHead')}, not the tag's {commit[:12]}")
    folder = Path(workspace) / PACKAGE_FOLDER
    tarball = distribution.get("tarball", "")
    digested = reader.digest(tarball, published={"integrity": distribution.get("integrity")},
                             maximum_bytes=MAXIMUM_PACKAGE_BYTES,
                             inspect=lambda path: _package_files(path, folder),
                             use_cache=(folder / THREEJS_MODULE).is_file())
    if not digested.ok or (digested.inspected or {}).get("integrity") != distribution.get("integrity"):
        raise LineStopped("engine_binary_unverified", f"{tarball}: the download does not match its integrity")

    def published_bytes(path):
        target = folder / path
        return target.read_bytes() if target.is_file() else None

    def published(path):
        data = published_bytes(path)
        return None if data is None else data.decode("utf-8")

    exports = jsdoc_reference.module_exports(THREEJS_ENTRY, published)
    references, reference_paths, refusals = {}, {}, []
    for name, (path, original) in sorted(exports.items()):
        if only and name not in only:
            continue
        text = published(path)
        declared = {row[0]: row for row in jsdoc_reference.read_classes(text or "")}
        if original not in declared:
            continue  # a function or a value, not a class
        _name, parent, reference = declared[original]
        references[name] = reference if name == original else replace(reference, name=name)
        reference_paths[name] = path
    wanted = [THREEJS_LICENCE_PATH] + sorted(set(reference_paths.values()))
    pinned, missing = pinned_files(reader, THREEJS_REPOSITORY, commit, wanted)
    if THREEJS_LICENCE_PATH in missing:
        raise LineStopped("source_unreadable", THREEJS_LICENCE_PATH)
    decision, licence_basis = tag_licence(reader, THREEJS_REPOSITORY, commit, pinned[THREEJS_LICENCE_PATH])
    if not decision.allowed:
        raise LineStopped(decision.reason, f"{THREEJS_REPOSITORY} at {commit[:12]}: {decision.evidence()}")
    package_licence = json.loads(published("package.json") or "{}").get("license")
    if package_licence != decision.spdx or published_bytes(THREEJS_LICENCE_PATH) != pinned[THREEJS_LICENCE_PATH]["bytes"]:
        raise LineStopped("licence_signals_disagree", f"the package names {package_licence}; its LICENSE must be "
                                                      "the tag's")
    for name, path in sorted(reference_paths.items()):
        if path in missing or published_bytes(path) != pinned[path]["bytes"]:
            refusals.append(refusal(ENGINE_API_CARDS, "published_source_differs", name, path))
            del references[name]
    module_bytes = (folder / THREEJS_MODULE).read_bytes()
    code = cards.card_module().code
    release = cards.EngineRelease(
        name=THREEJS, title=THREEJS_TITLE, release=THREEJS_TAG, version=THREEJS_VERSION,
        api_version=THREEJS_TAG, repository=THREEJS_REPOSITORY, commit=commit,
        binary_name=Path(tarball).name, binary_sha256=digested.sha256, binary_version=THREEJS_VERSION,
        docs_address=https_address(THREEJS_DOCS_HOST, "docs/"), syntax=cards.card_module().JAVASCRIPT_SYNTAX,
        surface_source=(f"read from the JSDoc of `{THREEJS_PACKAGE}@{THREEJS_VERSION}` (`{Path(tarball).name}`, "
                        f"SHA-256 `{digested.sha256}`) for the classes its main entry exports, each confirmed by "
                        f"importing its `{THREEJS_MODULE}` in Node"),
        surface_phrase="the surface the library's own JSDoc declares and its published module confirms",
        text_format="JSDoc", licence=decision.spdx)
    licence = dict(pinned[THREEJS_LICENCE_PATH], evidence=decision.evidence(), basis=licence_basis)
    metadata = {"url": https_address(REGISTRY_HOST, f"{THREEJS_PACKAGE}/{THREEJS_VERSION}"), "bytes": record.body,
                "sha256": record.sha256, "retrieved_at": record.retrieved_at}
    summary = {"exports": len(exports), "classes": len(references), "module_sha256": hashlib.sha256(
        module_bytes).hexdigest(), "package": f"{THREEJS_PACKAGE}@{THREEJS_VERSION}"}
    asset = {"url": tarball, "sha256": digested.sha256, "size_bytes": digested.size_bytes,
             "retrieved_at": digested.retrieved_at, "member": THREEJS_MODULE}
    dump = {name: (THREEJS_MODULE, module_bytes) for name in references}
    return EngineSources(release, dump, references, dict(references), reference_paths, pinned, licence, None, {},
                         None, asset, refusals, summary, text_for=lambda name: jsdoc_reference.JsDocText(code),
                         licence_path=THREEJS_LICENCE_PATH, text_basis=LICENCE_AT_THE_TAG, limits=THREEJS_LIMITS,
                         state_scope=THREEJS_STATE_SCOPE, metadata=metadata)


#: The Babylon.js release the adapter is pinned to: the npm package @babylonjs/core built from the tag 9.30.0.
BABYLONJS, BABYLONJS_TITLE = "babylonjs", "Babylon.js"
BABYLONJS_REPOSITORY, BABYLONJS_TAG = "BabylonJS/Babylon.js", "9.30.0"
BABYLONJS_PACKAGE, BABYLONJS_VERSION = "@babylonjs/core", "9.30.0"
BABYLONJS_STATE_SCOPE = "babylonjs_9_30"
BABYLONJS_LICENCE_PATH, BABYLONJS_ENTRY, BABYLONJS_MODULE = "license.md", "index.js", "index.js"
#: The package's own notice file (Apache-2.0 section 4(d)), in the package and in the repository at the tag.
BABYLONJS_NOTICE, BABYLONJS_PACKAGE_FOLDER = "NOTICE.md", "packages/public/@babylonjs/core"
BABYLONJS_DOCS_HOST = "doc.babylonjs.com"
BABYLONJS_HOSTS = (RAW_HOST, REGISTRY_HOST)
#: A module's declarations sit beside its compiled file, the same path with this suffix.
SCRIPT_SUFFIX, DECLARATION_SUFFIX = ".js", ".d.ts"
BABYLONJS_LIMITS = ("The surface is what the package's own declaration files give for the classes its root index "
                    "exports, each confirmed by importing the published module in Node. A member marked abstract (a "
                    "subclass implements it) is listed and not asked of the running module. A property marked "
                    "declare is one the running module was observed not to hold: not on the class, its prototypes "
                    "or a new instance, and not named in the source of the class or a class it extends; it exists "
                    "once a caller assigns it. Members other modules add to a class by module augmentation, and the "
                    "package's functions, constants and enumerations, are not listed. The text is the "
                    "declarations' TSDoc. Nothing here was loaded by a harness.")
#: The folder under the workspace where Node is asked which properties a module holds, before the cards exist.
OBSERVE_FOLDER = "observe"


def node_observer(module: str, workspace: Path):
    """The observe hook of a JavaScript adapter: once the package is unpacked, Node imports its module and reports
    which listed properties the module does not hold ({class: [names]})."""
    def observe(apis: list) -> dict:
        module_file = Path(workspace) / PACKAGE_FOLDER / module
        engine = node_native.locate(module, hashlib.sha256(module_file.read_bytes()).hexdigest())
        return node_native.observe(engine, module_file, apis, Path(workspace) / OBSERVE_FOLDER)
    return observe


def read_babylon(reader, workspace: Path, *, only=(), observe=None) -> EngineSources:
    """Read the pinned Babylon.js release: the npm package built from the tag (its integrity checked), the classes
    its root index exports with their declarations and TSDoc, and the licence; raises LineStopped. ``observe``
    (node_observer) marks declare on each property the published module does not hold; without it no property is
    marked, and the native check refuses a card whose property the module lacks."""
    version, api_version = release_numbers(BABYLONJS_TAG)
    address = https_address(REGISTRY_HOST, f"{BABYLONJS_PACKAGE}/{BABYLONJS_VERSION}")
    record = reader.get(address)
    if record.status != 200:
        raise LineStopped("source_unreadable", f"{BABYLONJS_PACKAGE}@{BABYLONJS_VERSION}: the registry did not answer")
    document = json.loads(record.body)
    distribution = document.get("dist") or {}
    head = reader.github(f"repos/{BABYLONJS_REPOSITORY}/commits/{BABYLONJS_TAG}")
    if head.status != 200:
        raise LineStopped("source_unreadable", f"the tag {BABYLONJS_TAG} has no readable commit")
    commit = json.loads(head.body)["sha"]
    if document.get("gitHead") != commit:
        raise LineStopped("engine_binary_unverified", f"{BABYLONJS_PACKAGE}@{BABYLONJS_VERSION} was built from "
                                                      f"{document.get('gitHead')}, not the tag's {commit[:12]}")
    folder = Path(workspace) / PACKAGE_FOLDER
    tarball = distribution.get("tarball", "")
    digested = reader.digest(tarball, published={"integrity": distribution.get("integrity")},
                             maximum_bytes=MAXIMUM_PACKAGE_BYTES,
                             inspect=lambda path: _package_files(path, folder),
                             use_cache=(folder / BABYLONJS_MODULE).is_file())
    if not digested.ok or (digested.inspected or {}).get("integrity") != distribution.get("integrity"):
        raise LineStopped("engine_binary_unverified", f"{tarball}: the download does not match its integrity")

    def published(path):
        target = folder / path
        return target.read_text(encoding="utf-8") if target.is_file() else None

    def declarations(path):
        return published(path[:-len(SCRIPT_SUFFIX)] + DECLARATION_SUFFIX if path.endswith(SCRIPT_SUFFIX) else path)

    exports = jsdoc_reference.module_exports(BABYLONJS_ENTRY, declarations)
    references, reference_paths, dump, read = {}, {}, {}, {}
    for name, (path, original) in sorted(exports.items()):
        if only and name not in only:
            continue
        if path not in read:
            read[path] = {row[0]: row for row in typescript_declarations.read_declarations(declarations(path) or "")}
        if original not in read[path]:
            continue  # a function, a constant or an enumeration, not a class
        _name, _parent, reference = read[path][original]
        references[name] = reference if name == original else replace(reference, name=name)
        reference_paths[name] = path[:-len(SCRIPT_SUFFIX)] + DECLARATION_SUFFIX
        dump[name] = (path, (folder / path).read_bytes())
    declared = typescript_declarations.mark_declared(references, observe(
        [{"class": name, "sections": reference.sections} for name, reference in references.items()])) \
        if observe is not None and references else 0
    try:
        licence_file = reader.pinned_file(BABYLONJS_REPOSITORY, commit, BABYLONJS_LICENCE_PATH)
    except LookupError as error:
        raise LineStopped("source_unreadable", str(error)[:200]) from None
    decision, licence_basis = tag_licence(reader, BABYLONJS_REPOSITORY, commit, licence_file)
    if not decision.allowed:
        raise LineStopped(decision.reason, f"{BABYLONJS_REPOSITORY} at {commit[:12]}: {decision.evidence()}")
    package_licence = json.loads(published("package.json") or "{}").get("license")
    if package_licence != decision.spdx or (folder / BABYLONJS_LICENCE_PATH).read_bytes() != licence_file["bytes"]:
        raise LineStopped("licence_signals_disagree", f"the package names {package_licence}; its licence file must "
                                                      "be the tag's")
    notice = None
    if (folder / BABYLONJS_NOTICE).is_file():
        try:
            notice_file = reader.pinned_file(BABYLONJS_REPOSITORY, commit, f"{BABYLONJS_PACKAGE_FOLDER}/{BABYLONJS_NOTICE}")
        except LookupError as error:
            raise LineStopped("source_unreadable", str(error)[:200]) from None
        if notice_file["bytes"] != (folder / BABYLONJS_NOTICE).read_bytes():
            raise LineStopped("published_source_differs", f"{BABYLONJS_NOTICE} is not the tag's")
        notice = {"repository": BABYLONJS_REPOSITORY, "commit": commit, "path": notice_file["path"],
                  "bytes": notice_file["bytes"], "sha256": notice_file["sha256"],
                  "retrieved_at": notice_file["retrieved_at"], "spdx": decision.spdx,
                  "url": github_blob_address(BABYLONJS_REPOSITORY, commit, notice_file["path"])}
    package_fact = {"url": tarball, "sha256": digested.sha256, "size_bytes": digested.size_bytes,
                    "retrieved_at": digested.retrieved_at}
    pinned = {path: package_fact for path in reference_paths.values()}
    release = cards.EngineRelease(
        name=BABYLONJS, title=BABYLONJS_TITLE, release=BABYLONJS_TAG, version=version, api_version=api_version,
        repository=BABYLONJS_REPOSITORY, commit=commit, binary_name=Path(tarball).name,
        binary_sha256=digested.sha256, binary_version=BABYLONJS_VERSION,
        docs_address=https_address(BABYLONJS_DOCS_HOST, ""), syntax=cards.card_module().JAVASCRIPT_SYNTAX,
        surface_source=(f"read from the declarations of `{BABYLONJS_PACKAGE}@{BABYLONJS_VERSION}` "
                        f"(`{Path(tarball).name}`, SHA-256 `{digested.sha256}`) for the classes its root index "
                        f"exports, each confirmed by importing its `{BABYLONJS_MODULE}` in Node"),
        surface_phrase="the surface the package's own declarations give and its published module confirms",
        text_format="TSDoc", licence=decision.spdx, notice_file=UPSTREAM_NOTICE_NAME if notice else "",
        text_origin=f"the npm package `{BABYLONJS_PACKAGE}@{BABYLONJS_VERSION}`, built from {BABYLONJS_REPOSITORY}")
    licence = dict(licence_file, evidence=decision.evidence(), basis=licence_basis)
    metadata = {"url": address, "bytes": record.body, "sha256": record.sha256, "retrieved_at": record.retrieved_at}
    summary = {"exports": len(exports), "classes": len(references), "package": f"{BABYLONJS_PACKAGE}@{BABYLONJS_VERSION}",
               "notice": bool(notice), "declared_properties": declared}
    code = cards.card_module().code
    return EngineSources(release, dump, references, dict(references), reference_paths, pinned, licence, None, {},
                         None, None, [], summary, text_for=lambda name: jsdoc_reference.JsDocText(code),
                         licence_path=BABYLONJS_LICENCE_PATH, text_basis="package_licence_file_at_the_tag",
                         limits=BABYLONJS_LIMITS, state_scope=BABYLONJS_STATE_SCOPE, metadata=metadata,
                         licence_expression=f"{GENERATED_CODE_LICENCE} AND {decision.spdx}",
                         notices=[notice] if notice else [], copyright_text=_own_notice(notice))


def _own_notice(notice: "dict | None") -> bytes:
    """The work's own copyright line of a notice file: its first one. The lines after it name the bundled
    components' holders, which the notice file itself carries to every package."""
    if not notice:
        return b""
    lines = [line for line in notice["bytes"].decode("utf-8").splitlines() if line.startswith("Copyright")]
    return lines[0].encode("utf-8") if lines else b""


def node_evidence(engine, module_file: Path, prepared: dict, workspace: Path, folder: "Path | None" = None) -> dict:
    """{class: evidence bytes} from one Node run over every prepared card of a JavaScript library."""
    answers = node_native.verify(engine, module_file, [card.api for card in prepared.values()],
                                 Path(workspace) / "verify")
    records = {}
    for name, card in prepared.items():
        data = godot_native.evidence_bytes(node_native.evidence(engine, card.api, answers.get(name), card.digest))
        records[name] = data
        if folder is not None:
            target = Path(folder) / card.api["engine"]["name"] / f"{name}.json"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    return records


@dataclass(frozen=True)
class PreparedCard:
    """One class's card files before the native check, the surface they hold and the digest the check binds."""

    name: str
    api: dict
    files: dict
    digest: str
    sources: cards.CardSources
    context: bbcode.Context


def _copyright_lines(licence_bytes: bytes) -> list:
    """The copyright notices of a licence text, each ending as a sentence; a licence's own template line (Apache's
    "Copyright [yyyy] [name of copyright owner]") names no year and is not a notice."""
    lines = [line.strip() for line in licence_bytes.decode("utf-8").splitlines()
             if line.startswith("Copyright") and re.search(r"\d{4}", line)]
    return [line if line.endswith(".") else line + "." for line in lines]


def prepare(sources: EngineSources, licence_text: bytes, only=()) -> tuple:
    """({class: PreparedCard}, refusals) for every class with a surface and its class reference (only the classes
    named, when some are)."""
    chains, children = inheritance(sources.references)
    known = frozenset(sources.references)
    module = cards.card_module()
    prepared, refused = {}, []
    for name, reference in sorted(sources.references.items()):
        if name not in sources.documentation or (only and name not in only):
            continue
        if reference.is_empty:
            refused.append(refusal(ENGINE_API_CARDS, "no_api_surface", name, "no section holds an item and the "
                                                                            "class inherits nothing"))
            continue
        documentation = sources.documentation[name]
        if documentation.structure() != reference.structure():
            refused.append(refusal(ENGINE_API_CARDS, "documentation_structure_differs", name,
                                   sources.reference_paths[name]))
            continue
        dump_path, dump_bytes = sources.dump[name]
        pinned = sources.pinned[sources.reference_paths[name]]
        renames = sources.renames.get(name, [])
        card_sources = cards.CardSources(
            dump_path=dump_path, dump_sha256=hashlib.sha256(dump_bytes).hexdigest(),
            reference_path=sources.reference_paths[name], reference_sha256=pinned["sha256"],
            renames_path=godot_renames.MAP_PATH if renames else "",
            renames_sha256=sources.renames_map["sha256"] if renames else "")
        api = cards.surface_record(sources.release, reference, chains[name], children[name], renames, card_sources)
        context = sources.text_for(name) if sources.text_for else bbcode.Context(
            known, name, sources.release.docs_address, module.code)
        texts = cards.documents(api, sources.release, documentation, context, card_sources,
                                _copyright_lines(sources.copyright_text or sources.licence["bytes"]))
        files = {path: text.encode("utf-8") for path, text in texts.items()}
        files[cards.API_NAME] = cards.json_bytes(api)
        files.update(cards.shared_files())
        files[LICENCE_NAME] = licence_text
        files[UPSTREAM_LICENCE_NAME] = sources.licence["bytes"]
        prepared[name] = PreparedCard(name, api, files, cards.card_digest(files), card_sources, context)
    return prepared, refused


def native_evidence(engine, prepared: dict, workspace: Path, folder: "Path | None" = None) -> dict:
    """{class: evidence bytes} from one run of the build over every prepared card; written under folder too."""
    answers = godot_native.verify(engine, [card.api for card in prepared.values()], Path(workspace) / "verify")
    records = {}
    for name, card in prepared.items():
        data = godot_native.evidence_bytes(godot_native.evidence(engine, card.api, answers.get(name), card.digest))
        records[name] = data
        if folder is not None:
            target = Path(folder) / GODOT / f"{name}.json"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    return records


def _test(folder: Path, files: dict) -> tuple:
    """(passed, tests run, output tail) of a card's own tests on its exact files, the way the sandbox runs them."""
    if folder.exists():
        shutil.rmtree(folder)
    for path, data in files.items():
        target = folder / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    result = run_package_tests(folder)
    shutil.rmtree(folder, ignore_errors=True)
    ran = _RAN.findall(result.get("output_tail", ""))
    return result["state"] == godot_native.PASSED, int(ran[-1]) if ran else 0, result.get("output_tail", "")[-300:]


def final_files(card: PreparedCard, evidence: bytes, sources: EngineSources, code_revision: str) -> dict:
    """Every file of a card's package but ATTRIBUTION.md: the card files, component.json and the evidence."""
    release = sources.release
    component = cards.component_card(
        card.api, release, sources.documentation[card.name], card.context, card.files, json.loads(evidence),
        limits=sources.limits or LIMITS,
        generator={"line": ENGINE_API_CARDS, "version": GENERATOR_VERSION, "adapter": release.name,
                   "code_revision": code_revision})
    return {**card.files, cards.COMPONENT_NAME: cards.json_bytes(component), godot_native.EVIDENCE_PATH: evidence}


def _package(card: PreparedCard, files: dict, sources: EngineSources, *, code_revision: str, generated_on: str,
             tests: tuple) -> tuple:
    release, name = sources.release, card.name
    passed, count, tail = tests
    if not passed:
        raise SupplyRecordError(GENERATED_TEST_FAILED, tail)
    component = json.loads(files[cards.COMPONENT_NAME])
    rows = []
    for path, data in sorted(files.items()):
        if path == LICENCE_NAME:
            rows.append(PackageFile(path, data, "other", LICENCE_TEXT))
        elif path == UPSTREAM_LICENCE_NAME:
            rows.append(PackageFile(path, data, "other", LICENCE_TEXT,
                                    {"url": github_blob_address(release.repository, release.commit,
                                                                sources.licence_path),
                                     "sha256": sources.licence["sha256"]}))
        else:
            rows.append(PackageFile(path, data, EXECUTABLE_ROLE if path.endswith(PYTHON_SUFFIX) else OTHER_ROLE,
                                    GENERATED))
    text_licence = sources.release.licence
    facts = [_fact(sources.licence, "licence_text", sources.licence["basis"], text_licence)]
    if sources.copyright is not None:
        facts.append(_fact(sources.copyright, "licence_evidence", "copyright_file_files_star_expat_at_the_tag"))
    facts.append(_fact(sources.pinned[card.sources.reference_path], "data_source", sources.text_basis, text_licence))
    if card.sources.renames_path:
        facts.append(_fact(sources.renames_map, "data_source", sources.text_basis))
    if sources.metadata is not None:
        facts.append(fact_source(sources.metadata["url"], sources.metadata["retrieved_at"], sources.metadata["sha256"],
                                 len(sources.metadata["bytes"]), "package_metadata", spdx="NOASSERTION",
                                 basis="registry_record_read_for_the_package_digest_and_its_git_head"))
    if sources.release_asset:
        asset = sources.release_asset
        facts.append(fact_source(asset["url"], asset["retrieved_at"], asset["sha256"], asset["size_bytes"] or 0,
                                 "release", spdx=GENERATED_CODE_LICENCE,
                                 basis="official_build_of_the_tag_surface_read_never_copied"))
    notice_rows, notice_facts = notice_files(sources.notices)
    rows += notice_rows
    facts += notice_facts
    identity = f"{release.name}/{release.api_version}/{name}"
    reference = sources.references[name]
    supply = SupplyPackage(
        line=ENGINE_API_CARDS, identity=identity, key=upstream_key(ENGINE_API_CARDS, identity), kind=cards.KIND,
        native_format=NATIVE_FORMAT, form=cards.FORM, name=f"{name} ({release.title} {release.api_version})",
        description=component["purpose"], files=rows, licence_expression=sources.licence_expression,
        provenance=provenance("github_repository", release.repository, card.sources.reference_path, release.commit,
                              facts, {"identity": "engine_api_cards", "version": GENERATOR_VERSION,
                                      "code_revision": code_revision}),
        placements=[{"harness": "reference", "path": f"baltor/engine-api/{release.name}/{release.api_version}/{name}/",
                     "basis": "documented_layout", "scope": "project", "support": "unverified"}],
        effects=derived_effects(cards.KIND, [Entry(row.path, row.data, row.role, "") for row in rows]),
        credentials=[],
        tests={"files": [cards.TEST_NAME], "command": "python -m unittest test_api_card", "network": False,
               "result": godot_native.PASSED, "tests_run": count, "native": godot_native.PASSED,
               "native_record": godot_native.EVIDENCE_PATH},
        repository={"name": release.repository, "tag": release.release, "commit": release.commit,
                    "engine": release.name, "api_version": release.api_version, "class": name,
                    "kind": reference.kind.value, "binary_sha256": release.binary_sha256,
                    "renames": len(card.api.get("renames", {}).get("entries", [])),
                    "documents": component["documents"]},
        generated_on=generated_on, comparison_text=identity)
    return build(supply)


def package(prepared: dict, evidence: dict, sources: EngineSources, *, code_revision: str, generated_on: str,
            staging: Path, workers: int = 8) -> tuple:
    """(built, refusals): every prepared card whose evidence holds and whose own tests pass on its exact files."""
    built, refused, ready = [], [], {}
    for name, card in sorted(prepared.items()):
        data = evidence.get(name)
        if data is None:
            refused.append(refusal(ENGINE_API_CARDS, "native_evidence_missing", name))
            continue
        try:
            godot_native.read_evidence(data, card.api, card.digest)
        except godot_native.NativeError as error:
            refused.append(refusal(ENGINE_API_CARDS, EVIDENCE_REFUSALS.get(error.reason, "native_evidence_invalid"),
                                   name, str(error)[:300]))
            continue
        ready[name] = final_files(card, data, sources, code_revision)
    staging = Path(staging)

    def test(name):
        return name, _test(staging / re.sub(r"[^A-Za-z0-9_.-]", "_", name), ready[name])

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        results = dict(pool.map(test, sorted(ready)))
    for name in sorted(ready):
        try:
            built.append(_package(prepared[name], ready[name], sources, code_revision=code_revision,
                                  generated_on=generated_on, tests=results[name]))
        except SupplyRecordError as error:
            reason = error.code if error.code in PACKAGE_REASONS + (GENERATED_TEST_FAILED,) else "package_path_invalid"
            refused.append(refusal(ENGINE_API_CARDS, reason, name, str(error)[:300]))
    return built, refused


def facts_of(sources: EngineSources) -> dict:
    """{SHA-256: bytes} of every pinned fact the packages name and the run kept, for the store's quarantine."""
    return {row["sha256"]: row["bytes"] for row in sources.pinned.values() if row.get("bytes")}


def generate(sources: EngineSources, *, verifier, code_revision: str, licence_text: bytes, generated_on: str,
             staging: Path, workers: int = 8, only=()) -> tuple:
    """(built, refusals, facts, summary): prepare every card, check them all natively with ``verifier``
    (prepared -> {class: evidence bytes}), then package the cards whose evidence holds."""
    prepared, refused = prepare(sources, licence_text, only)
    evidence = verifier(prepared) if prepared else {}
    built, package_refusals = package(prepared, evidence, sources, code_revision=code_revision,
                                      generated_on=generated_on, staging=staging, workers=workers)
    refusals = list(sources.refusals) + refused + package_refusals
    kinds = {}
    for payload, _bodies in built:
        kind = payload["repository"]["kind"]
        kinds[kind] = kinds.get(kind, 0) + 1
    summary = dict(sources.summary, prepared=len(prepared), packaged=len(built), refused=len(refusals),
                   packaged_by_kind=kinds, release=sources.release.identity())
    return built, refusals, facts_of(sources), summary


__all__ = ["GENERATOR_VERSION", "NATIVE_FORMAT", "GODOT_TAG", "GODOT_STATE_SCOPE", "HOSTS", "EngineSources",
           "PreparedCard", "LineStopped", "read_godot", "read_threejs", "prepare", "native_evidence", "node_evidence",
           "package", "generate", "THREEJS_HOSTS", "THREEJS_STATE_SCOPE", "read_babylon", "BABYLONJS_HOSTS",
           "BABYLONJS_STATE_SCOPE", "node_observer",
           "copyright_stanzas", "governing_licence", "release_numbers"]
