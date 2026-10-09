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
from dataclasses import dataclass, field
from pathlib import Path

from creative_originals.assemble import Entry, run_package_tests
from engine_api_cards import bbcode, cards, godot_native, godot_renames
from engine_api_cards.godot_reference import ClassKind, ReferenceError, inheritance, read_reference

from .creative_originals import derived_effects
from .licences import LICENCE_UNKNOWN, decide, repository_licence
from .packaging import LICENCE_NAME, UPSTREAM_LICENCE_NAME, PackageFile, SupplyPackage, build
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
#: What every card says it does not establish.
LIMITS = ("The surface is the official Linux x86_64 editor build's: a class, member or setting that only another "
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


def _fact(pinned: dict, role: str, basis: str) -> dict:
    return fact_source(pinned["url"], pinned["retrieved_at"], pinned["sha256"], len(pinned["bytes"]), role,
                       spdx=GENERATED_CODE_LICENCE, basis=basis)


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
    release = cards.EngineRelease(
        name=GODOT, title=GODOT_TITLE, release=tag, version=version, api_version=api_version,
        repository=GODOT_REPOSITORY, commit=commit, binary_name=Path(engine.path).name, binary_sha256=engine.sha256,
        binary_version=engine.version, docs_address=https_address(DOCS_HOST, f"en/{api_version}"),
        syntax=cards.card_module().GODOT_SYNTAX, renames_from_version=godot_renames.FROM_VERSION)
    licence = dict(pinned[LICENCE_PATH], evidence=decision.evidence(), basis=licence_basis)
    summary = {"dump_classes": len(dump), "dump_sha256": godot_native.dump_digest(dump),
               "reference_files": len(reference_paths), "renames": outcomes,
               "release_asset": asset["url"] if asset else None}
    return EngineSources(release, located, references, documentation, reference_paths, pinned, licence,
                         pinned[COPYRIGHT_PATH], renames, renames_map, asset, refusals, summary)


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
    return [line.strip() for line in licence_bytes.decode("utf-8").splitlines() if line.startswith("Copyright")]


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
        context = bbcode.Context(known, name, sources.release.docs_address, module.code)
        texts = cards.documents(api, sources.release, documentation, context, card_sources,
                                _copyright_lines(sources.licence["bytes"]))
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
        limits=LIMITS,
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
                                    {"url": github_blob_address(release.repository, release.commit, LICENCE_PATH),
                                     "sha256": sources.licence["sha256"]}))
        else:
            rows.append(PackageFile(path, data, EXECUTABLE_ROLE if path.endswith(PYTHON_SUFFIX) else OTHER_ROLE,
                                    GENERATED))
    facts = [_fact(sources.licence, "licence_text", sources.licence["basis"]),
             _fact(sources.copyright, "licence_evidence", "copyright_file_files_star_expat_at_the_tag"),
             _fact(sources.pinned[card.sources.reference_path], "data_source", "copyright_file_stanza_expat")]
    if card.sources.renames_path:
        facts.append(_fact(sources.renames_map, "data_source", "copyright_file_stanza_expat"))
    if sources.release_asset:
        asset = sources.release_asset
        facts.append(fact_source(asset["url"], asset["retrieved_at"], asset["sha256"], asset["size_bytes"] or 0,
                                 "release", spdx=GENERATED_CODE_LICENCE,
                                 basis="official_build_of_the_tag_surface_read_never_copied"))
    identity = f"{release.name}/{release.api_version}/{name}"
    reference = sources.references[name]
    supply = SupplyPackage(
        line=ENGINE_API_CARDS, identity=identity, key=upstream_key(ENGINE_API_CARDS, identity), kind=cards.KIND,
        native_format=NATIVE_FORMAT, form=cards.FORM, name=f"{name} ({release.title} {release.api_version})",
        description=component["purpose"], files=rows, licence_expression=GENERATED_CODE_LICENCE,
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
    """{SHA-256: bytes} of every pinned fact the packages name, for the store's quarantine."""
    return {row["sha256"]: row["bytes"] for row in sources.pinned.values()}


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
           "PreparedCard", "LineStopped", "read_godot", "prepare", "native_evidence", "package", "generate",
           "copyright_stanzas", "governing_licence", "release_numbers"]
