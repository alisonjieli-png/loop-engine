"""Line container_image_cards: one contract card per repository and tag family of the Docker Official Images.

```text
container_image_cards (one card format, tools/container_image_cards; one registry engine per registry)
├── tag families: every library/<name> file of docker-library/official-images at its head commit (Apache-2.0,
│   read for facts: tags, architectures, build context), each proven by git blob identity; one entry is one family
├── documentation: the image's folder of docker-library/docs at its head commit (MIT): the one-line summary (the
│   only text a card quotes), Docker Hub's categories, environment variable names from headings and example
│   commands, the software licence addresses and the source repository
├── registry (Docker Hub by default): the family's first own tag resolved by HEAD; its image index, every platform
│   manifest and every config read by digest through the blob endpoint and checked against the digest; no layer is
│   read and no pull of the anonymous allowance is counted
├── one package per family: README.md, contract.json, schema.json, image_contract.py, schema_check.py,
│   test_image_contract.py, component.json, verification/registry.json (verification/smoke.json for the few a run
│   names), LICENSE (Baltor's MIT), UPSTREAM-LICENSE (docker-library/docs' MIT, for the quoted summary) and
│   ATTRIBUTION.md; the package's own tests pass on its exact files before it is kept
├── native check: a second pass over the registry (tools/container_image_cards/verify.py) confirms every digest by
│   HEAD and parses each config again; missing, stale or failed evidence refuses the card by name
├── an environment value under a credential's name, or shaped like a credential, is withheld (its name stays);
│   a credential-shaped value anywhere else refuses the family
└── job key: component.json job.registry, job.repository and job.family, never a digest, a tag that moves or a
    commit, so a family rebuilt or moved to its next version is the same job
```

The line calls no model. A package is a candidate until qualification and the ongoing independent review.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from container_image_cards import cards, docs, oci
from container_image_cards import verify as native
from container_image_cards.library import LibraryError, read_library
from container_image_cards.registry import INDEX_TYPES, MANIFEST_TYPES, RegistryError, RequestCeilingReached
from creative_originals.assemble import Entry, run_package_tests

from .creative_originals import derived_effects
from .licences import repository_licence
from .packaging import LICENCE_NAME, UPSTREAM_LICENCE_NAME, PackageFile, SupplyPackage, build
from .reading import RAW_HOST, github_blob_address, pinned_files
from .records import (CONTAINER_IMAGE_CARDS, GENERATED, GENERATED_CODE_LICENCE, GENERATED_TEST_FAILED, LICENCE_TEXT,
                      SupplyRecordError, fact_source, provenance, refusal, upstream_key)

GENERATOR_VERSION = "1.0.1"
NATIVE_FORMAT = "container_image_card"
STATE_SCOPE = "docker_official_images"
LIBRARY_REPOSITORY, DOCS_REPOSITORY = cards.LIBRARY_REPOSITORY, cards.DOCS_REPOSITORY
DEFAULT_BRANCH = "master"
LIBRARY_FOLDER, LICENCE_PATH = "library/", "LICENSE"
API_HOST = "api.github.com"
GITHUB_HOSTS = (RAW_HOST, API_HOST)
#: The type of a file in a git tree listing.
BLOB_TYPE = "blob"
EXECUTABLE_ROLE, OTHER_ROLE, PYTHON_SUFFIX = "executable_tool", "other", ".py"
#: The bases of the facts a package names.
LIBRARY_BASIS = "library_definition_read_for_facts_no_text_copied"
DOCS_BASIS = "documentation_folder_at_the_commit"
LICENCE_BASIS = "github_licence_and_text_agree_at_the_commit"
REGISTRY_BASIS = "image_document_read_by_digest_for_facts_no_bytes_copied"
REGISTRY_ROLE, METADATA_LICENCE = "registry_entry", "NOASSERTION"
#: The refusals of a fact or registry answer the run could not read: a run that gives one is not complete and
#: withdraws nothing.
UNREAD_REASONS = ("source_unreadable", "registry_unreadable", "registry_unauthorized", "registry_rate_limited",
                  "registry_redirect_undeclared", "document_not_found", "request_ceiling_reached")
#: The refusals the shared packaging gives one package.
PACKAGE_REASONS = ("blocked_by_static_check", "package_above_review_bound", "package_path_invalid")
#: The refusal each reason of verify.read_evidence gives.
EVIDENCE_REFUSALS = {native.EVIDENCE_UNREADABLE: "native_evidence_invalid",
                     native.EVIDENCE_INVALID: "native_evidence_invalid",
                     native.EVIDENCE_STALE: "native_evidence_stale", native.CHECK_FAILED: "native_check_failed"}
REQUEST_CEILING = "request_ceiling_reached"
#: An address that carries a user and a password ("scheme://user:secret@host"): a credential whatever the patterns
#: of the secret check say about the rest of the value.
ADDRESS_WITH_PASSWORD = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*://[^/@\s:]+:[^/@\s]+@")
PLATFORM_MISMATCH, CREDENTIAL_IN_IMAGE = "platform_mismatch", "credential_shaped_value_in_image"
SMOKE_FAILED = "smoke_check_failed"
#: A family whose card the writer could not write (an error it did not foresee), refused by name with the error.
CARD_NOT_WRITTEN = "card_not_written"
_RAN = re.compile(r"^Ran (\d+) tests? in ", re.MULTILINE)
_SLUG = re.compile(r"[^A-Za-z0-9._-]+")
PASSED = native.PASSED


class LineStopped(RuntimeError):
    """The collection as a whole cannot be carded (an unreadable source, a licence the line cannot use)."""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason, self.detail = reason, detail


@dataclass
class CollectionSources:
    """What the line read of the two documentation repositories, before any registry read."""

    library_commit: str
    docs_commit: str
    library_files: dict  # name -> pinned library file
    docs_files: dict  # name -> {file name: pinned file}
    library_licence: dict  # pinned LICENSE with the decision's evidence
    docs_licence: dict
    refusals: list = field(default_factory=list)


def _head_commit(reader, repository: str) -> tuple:
    head = reader.github(f"repos/{repository}/commits/{DEFAULT_BRANCH}")
    if head.status != 200:
        raise LineStopped("source_unreadable", f"{repository}: no head commit")
    commit = json.loads(head.body)["sha"]
    tree = reader.github(f"repos/{repository}/git/trees/{commit}?recursive=1")
    if tree.status != 200:
        raise LineStopped("source_unreadable", f"{repository}: no tree at {commit[:12]}")
    document = json.loads(tree.body)
    if document.get("truncated"):
        raise LineStopped("source_unreadable", f"{repository}: the tree listing is truncated")
    return commit, [row["path"] for row in document.get("tree", []) if row.get("type") == BLOB_TYPE]


def _licence(reader, repository: str, commit: str) -> dict:
    """The repository's licence file at the commit, decided by GitHub's interface and its text agreeing."""
    decision = repository_licence(reader, repository, commit)
    if not decision.allowed:
        raise LineStopped(decision.reason, f"{repository} at {commit[:12]}: {decision.evidence()}")
    pinned, missing = pinned_files(reader, repository, commit, [decision.path])
    if missing or pinned[decision.path]["sha256"] != decision.sha256:
        raise LineStopped("licence_signals_disagree", f"{repository}: the licence file is not {decision.path}")
    return dict(pinned[decision.path], spdx=decision.spdx, evidence=decision.evidence())


def read_collection(reader, *, only=()) -> CollectionSources:
    """The library files and documentation folders of every repository (only those named, when some are), with both
    repositories' licences; raises LineStopped."""
    library_commit, library_paths = _head_commit(reader, LIBRARY_REPOSITORY)
    docs_commit, docs_paths = _head_commit(reader, DOCS_REPOSITORY)
    library_licence = _licence(reader, LIBRARY_REPOSITORY, library_commit)
    docs_licence = _licence(reader, DOCS_REPOSITORY, docs_commit)
    names = sorted(path[len(LIBRARY_FOLDER):] for path in library_paths
                   if path.startswith(LIBRARY_FOLDER) and "/" not in path[len(LIBRARY_FOLDER):])
    if only:
        names = [name for name in names if name in only]
    pinned, missing = pinned_files(reader, LIBRARY_REPOSITORY, library_commit,
                                   [LIBRARY_FOLDER + name for name in names])
    refusals = [refusal(CONTAINER_IMAGE_CARDS, "source_unreadable", path, LIBRARY_REPOSITORY) for path in missing]
    present = set(docs_paths)
    wanted = [f"{name}/{file}" for name in names for file in docs.FILES if f"{name}/{file}" in present]
    docs_pinned, docs_missing = pinned_files(reader, DOCS_REPOSITORY, docs_commit, wanted)
    refusals += [refusal(CONTAINER_IMAGE_CARDS, "source_unreadable", path, DOCS_REPOSITORY) for path in docs_missing]
    folders = {}
    for path, row in docs_pinned.items():
        name, _, file = path.partition("/")
        folders.setdefault(name, {})[file] = row
    library_files = {path[len(LIBRARY_FOLDER):]: row for path, row in pinned.items()}
    return CollectionSources(library_commit, docs_commit, library_files, folders, library_licence, docs_licence,
                             refusals)


@dataclass
class FamilyFacts:
    """One family's registry reads: the family itself, and every document (registry.Document) it was written from."""

    family: cards.ImageFamily
    documents: list


def read_family(entry, registry, documentation: dict, collection: CollectionSources, secret_patterns) -> FamilyFacts:
    """Resolve one family's tag and read its index, manifests and configs by digest; raises RegistryError or
    oci.DocumentError (a refusal by its reason)."""
    name = entry.repository
    tag = registry.read_tag(name, entry.resolved_tag)
    index_document = registry.read_document(name, tag.digest, manifest=True)
    value = index_document.json()
    media_type = value.get(oci.MEDIA_TYPE) or tag.media_type
    documents = [index_document]
    if media_type in INDEX_TYPES:
        entries = oci.read_index(value, media_type)
    elif media_type in MANIFEST_TYPES:
        entries = None
    else:
        raise oci.DocumentError(oci.MANIFEST_UNSUPPORTED, f"{name}:{entry.resolved_tag} is {str(media_type)[:80]}")
    images = []
    for platform_entry in entries or [None]:
        manifest_document = index_document if platform_entry is None else registry.read_document(
            name, platform_entry.manifest["digest"], manifest=True)
        manifest = oci.read_manifest(manifest_document.json(), media_type if platform_entry is None else
                                     platform_entry.manifest["media_type"])
        config_document = registry.read_document(name, manifest["config"]["digest"], manifest=False)
        config = config_document.json()
        stated = oci.config_platform(config)
        if platform_entry is None:
            platform_entry = oci.PlatformEntry(stated["os"], stated["architecture"], stated["variant"],
                                               stated["os_version"], (), {"digest": tag.digest,
                                                                          "media_type": media_type,
                                                                          "size": index_document.size}, {})
        elif (stated["os"], stated["architecture"]) != (platform_entry.os, platform_entry.architecture):
            raise oci.DocumentError(PLATFORM_MISMATCH, f"{platform_entry.platform} has a config for "
                                                       f"{stated['os']}/{stated['architecture']}")
        if manifest_document is not index_document:
            documents.append(manifest_document)
        documents.append(config_document)
        images.append(cards.PlatformImage(platform_entry, manifest, oci.runtime(config), stated))
    images.sort(key=lambda image: (image.platform, image.entry.os_version or ""))
    withheld = set()
    shapes = tuple(secret_patterns) + (ADDRESS_WITH_PASSWORD,)
    for image in images:
        runtime = image.runtime
        for row in runtime["environment"]:
            if row["value"] and any(pattern.search(row["value"]) for pattern in shapes):
                withheld.add(row["name"])
        rest = json.dumps({key: item for key, item in runtime.items() if key != "environment"})
        if any(pattern.search(rest) for pattern in shapes):
            raise oci.DocumentError(CREDENTIAL_IN_IMAGE, f"{name}:{entry.resolved_tag} {image.platform}")
    family = cards.ImageFamily(
        entry=entry, tag=tag, index={"digest": tag.digest, "media_type": media_type, "size": index_document.size},
        platforms=tuple(images), documentation=documentation,
        library_location={"repository": LIBRARY_REPOSITORY, "path": LIBRARY_FOLDER + name,
                          "commit": collection.library_commit},
        docs_location={"repository": DOCS_REPOSITORY, "path": name, "commit": collection.docs_commit},
        withheld_values=frozenset(withheld))
    return FamilyFacts(family, documents)


def documentation_of(collection: CollectionSources, name: str) -> dict:
    files = collection.docs_files.get(name, {})
    return docs.facts({file: (files[file]["bytes"] if file in files else None) for file in docs.FILES})


def read_families(collection: CollectionSources, registry, secret_patterns, *, maximum_families: int = 0,
                  workers: int = 1, progress=None) -> tuple:
    """([FamilyFacts], refusals) for every family of every library file read, in file order; ``workers`` families
    are read at once through the one reader, whose pause still holds between any two requests. A request ceiling
    reached refuses every family not yet read, by name."""
    tasks, refusals = [], []
    for name in sorted(collection.library_files):
        pinned = collection.library_files[name]
        try:
            entries = read_library(name, pinned["bytes"].decode("utf-8"))
        except (LibraryError, UnicodeDecodeError) as error:
            refusals.append(refusal(CONTAINER_IMAGE_CARDS, "library_entry_invalid", name, str(error)))
            continue
        documentation = documentation_of(collection, name)
        tasks += [(entry, documentation) for entry in entries]
    if maximum_families:
        tasks = tasks[:maximum_families]
    lock, counts = threading.Lock(), {"read": 0, "refused": 0}

    def read(task):
        entry, documentation = task
        subject = f"{entry.repository}:{entry.resolved_tag}"
        try:
            outcome = read_family(entry, registry, documentation, collection, secret_patterns)
        except RequestCeilingReached as error:
            outcome = refusal(CONTAINER_IMAGE_CARDS, REQUEST_CEILING, subject, str(error))
        except RegistryError as error:
            outcome = refusal(CONTAINER_IMAGE_CARDS, error.reason, subject, error.detail)
        except oci.DocumentError as error:
            outcome = refusal(CONTAINER_IMAGE_CARDS, error.reason, subject, error.detail)
        except ValueError as error:  # a document that is not JSON
            outcome = refusal(CONTAINER_IMAGE_CARDS, oci.CONFIG_UNREADABLE, subject, str(error))
        with lock:
            counts["read" if isinstance(outcome, FamilyFacts) else "refused"] += 1
            if progress is not None:
                progress(counts["read"], counts["refused"], subject)
        return outcome

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        outcomes = list(pool.map(read, tasks))
    families = [outcome for outcome in outcomes if isinstance(outcome, FamilyFacts)]
    refusals += [outcome for outcome in outcomes if not isinstance(outcome, FamilyFacts)]
    return families, refusals


@dataclass(frozen=True)
class PreparedCard:
    """One family's card files before the registry check, the contract they hold and the digest the check binds."""

    identity: str
    facts: FamilyFacts
    contract: dict
    files: dict
    digest: str


def copyright_line(licence_bytes: bytes) -> str:
    """The licence text's first copyright notice, as a sentence."""
    for line in licence_bytes.decode("utf-8").splitlines():
        if line.startswith("Copyright") and re.search(r"\d{4}", line):
            line = line.strip()
            return line if line.endswith(".") else line + "."
    return ""


def family_identity(family: cards.ImageFamily) -> str:
    return f"{family.entry.repository}/{family.entry.family}"


def file_stem(identity: str) -> str:
    """A short file name for a card's run records: its repository and the start of its identity's digest (an
    identity that names every architecture's directory is longer than a file name may be)."""
    repository = identity.split("/", 1)[0]
    return f"{_SLUG.sub('_', repository)}-{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:16]}"


def prepare(families: list, collection: CollectionSources, licence_text: bytes, refusals: "list | None" = None
            ) -> dict:
    """{identity: PreparedCard} of every family read. A family the writer fails on is refused by name
    (card_not_written, with the error), so one unexpected document never stops the run; ``refusals`` collects
    them."""
    prepared = {}
    notice = copyright_line(collection.docs_licence["bytes"])
    for facts in families:
        subject = f"{facts.family.entry.repository}:{facts.family.entry.resolved_tag}"
        try:
            record = cards.contract(facts.family)
            files = cards.card_files(record, licence_text=licence_text,
                                     upstream_licence=collection.docs_licence["bytes"], copyright_line=notice)
        except Exception as error:  # noqa: BLE001 - a writer defect is reported by name, never a stopped run
            if refusals is None:
                raise
            refusals.append(refusal(CONTAINER_IMAGE_CARDS, CARD_NOT_WRITTEN, subject,
                                    f"{type(error).__name__}: {error}"))
            continue
        identity = family_identity(facts.family)
        prepared[identity] = PreparedCard(identity, facts, record, files, cards.card_digest(files))
    return prepared


def registry_evidence(prepared: dict, registry, folder: "Path | None" = None, *, workers: int = 1,
                      progress=None) -> dict:
    """{identity: evidence bytes} from one registry check of every prepared card; written under folder too. A card
    the run's request ceiling left unchecked has no evidence and is refused as missing it."""
    module = cards.card_module()
    lock, done = threading.Lock(), [0]

    def check(identity):
        card = prepared[identity]
        try:
            data = native.evidence_bytes(native.verify(card.contract, card.digest, registry, module))
        except RequestCeilingReached:
            return identity, None
        except Exception:  # noqa: BLE001 - a check that cannot finish leaves no evidence: the card is refused
            return identity, None
        if folder is not None:
            target = Path(folder) / "registry" / f"{file_stem(identity)}.json"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        with lock:
            done[0] += 1
            if progress is not None:
                progress(done[0], 0, identity)
        return identity, data

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        answers = list(pool.map(check, sorted(prepared)))
    return {identity: data for identity, data in answers if data is not None}


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
    return result["state"] == PASSED, int(ran[-1]) if ran else 0, result.get("output_tail", "")[-300:]


def final_files(card: PreparedCard, evidence: bytes, smoke: "bytes | None", code_revision: str) -> dict:
    """Every file of a card's package but ATTRIBUTION.md: the card files, the evidence and component.json."""
    files = dict(card.files)
    files[cards.EVIDENCE_PATH] = evidence
    if smoke is not None:
        files[cards.SMOKE_PATH] = smoke
    component = cards.component_card(card.contract, files, json.loads(evidence),
                                     smoke=json.loads(smoke) if smoke else None,
                                     generator={"line": CONTAINER_IMAGE_CARDS, "version": GENERATOR_VERSION,
                                                "code_revision": code_revision})
    files[cards.COMPONENT_NAME] = cards.json_bytes(component)
    return files


def _facts(card: PreparedCard, collection: CollectionSources) -> list:
    family = card.facts.family
    name = family.entry.repository
    library_file = collection.library_files[name]
    rows = [fact_source(collection.docs_licence["url"], collection.docs_licence["retrieved_at"],
                        collection.docs_licence["sha256"], len(collection.docs_licence["bytes"]), "licence_text",
                        spdx=collection.docs_licence["spdx"], basis=LICENCE_BASIS),
            fact_source(collection.library_licence["url"], collection.library_licence["retrieved_at"],
                        collection.library_licence["sha256"], len(collection.library_licence["bytes"]),
                        "licence_evidence", spdx=collection.library_licence["spdx"], basis=LICENCE_BASIS),
            fact_source(library_file["url"], library_file["retrieved_at"], library_file["sha256"],
                        len(library_file["bytes"]), "data_source", spdx=collection.library_licence["spdx"],
                        basis=LIBRARY_BASIS)]
    for file, pinned in sorted(collection.docs_files.get(name, {}).items()):
        rows.append(fact_source(pinned["url"], pinned["retrieved_at"], pinned["sha256"], len(pinned["bytes"]),
                                "data_source", spdx=collection.docs_licence["spdx"], basis=DOCS_BASIS))
    for document in card.facts.documents:
        rows.append(fact_source(document.url, document.retrieved_at, document.digest.split(":", 1)[1], document.size,
                                REGISTRY_ROLE, spdx=METADATA_LICENCE, basis=REGISTRY_BASIS))
    return rows


def _package(card: PreparedCard, files: dict, collection: CollectionSources, *, code_revision: str,
             generated_on: str, tests: tuple, smoked: bool) -> tuple:
    passed, count, tail = tests
    if not passed:
        raise SupplyRecordError(GENERATED_TEST_FAILED, tail)
    family, record = card.facts.family, card.contract
    rows = []
    for path, data in sorted(files.items()):
        if path == LICENCE_NAME:
            rows.append(PackageFile(path, data, OTHER_ROLE, LICENCE_TEXT))
        elif path == UPSTREAM_LICENCE_NAME:
            rows.append(PackageFile(path, data, OTHER_ROLE, LICENCE_TEXT, {
                "url": github_blob_address(DOCS_REPOSITORY, collection.docs_commit, collection.docs_licence["path"]),
                "sha256": collection.docs_licence["sha256"]}))
        else:
            rows.append(PackageFile(path, data, EXECUTABLE_ROLE if path.endswith(PYTHON_SUFFIX) else OTHER_ROLE,
                                    GENERATED))
    image = record["image"]
    identity = card.identity
    slug = _SLUG.sub("-", image["resolved_tag"])
    supply = SupplyPackage(
        line=CONTAINER_IMAGE_CARDS, identity=identity, key=upstream_key(CONTAINER_IMAGE_CARDS, identity),
        kind=cards.KIND, native_format=NATIVE_FORMAT, form=cards.FORM,
        name=f"{image['name']}:{image['resolved_tag']} (Docker Official Image)", description=cards.purpose(record),
        files=rows, licence_expression=GENERATED_CODE_LICENCE,
        provenance=provenance("docker_hub_registry", f"{image['registry']}/{image['repository']}",
                              image["resolved_tag"], image["index"]["digest"], _facts(card, collection),
                              {"identity": CONTAINER_IMAGE_CARDS, "version": GENERATOR_VERSION,
                               "code_revision": code_revision}),
        placements=[{"harness": "reference", "path": f"baltor/container-images/{image['name']}/{slug}/",
                     "basis": "documented_layout", "scope": "project", "support": "unverified"}],
        effects=derived_effects(cards.KIND, [Entry(row.path, row.data, row.role, "") for row in rows]),
        credentials=[],
        tests={"files": [cards.TEST_NAME], "command": "python -m unittest test_image_contract", "network": False,
               "result": PASSED, "tests_run": count, "native": PASSED, "native_record": cards.EVIDENCE_PATH,
               "smoke": PASSED if smoked else "not_run"},
        repository={"registry": image["registry"], "repository": image["repository"], "name": image["name"],
                    "family": family.entry.family, "resolved_tag": image["resolved_tag"], "tags": image["tags"],
                    "index_digest": image["index"]["digest"], "platforms": cards.card_module().platforms(record),
                    "library_commit": collection.library_commit, "docs_commit": collection.docs_commit,
                    "collection": STATE_SCOPE, "documents": [cards.README_NAME]},
        generated_on=generated_on, comparison_text=identity)
    return build(supply)


def package(prepared: dict, evidence: dict, smoke: dict, collection: CollectionSources, *, code_revision: str,
            generated_on: str, staging: Path, workers: int = 8) -> tuple:
    """(built, refusals): every prepared card whose evidence holds and whose own tests pass on its exact files."""
    built, refused, ready = [], [], {}
    for identity, card in sorted(prepared.items()):
        subject = f"{card.contract['image']['name']}:{card.contract['image']['resolved_tag']}"
        data = evidence.get(identity)
        if data is None:
            refused.append(refusal(CONTAINER_IMAGE_CARDS, "native_evidence_missing", subject))
            continue
        try:
            native.read_evidence(data, card.digest, card.contract["image"]["index"]["digest"])
        except native.NativeError as error:
            refused.append(refusal(CONTAINER_IMAGE_CARDS, EVIDENCE_REFUSALS.get(error.reason,
                                                                                 "native_evidence_invalid"),
                                   subject, str(error)[:300]))
            continue
        smoked = smoke.get(identity)
        if smoked is not None and json.loads(smoked).get("state") != PASSED:
            refused.append(refusal(CONTAINER_IMAGE_CARDS, SMOKE_FAILED, subject, smoked.decode("utf-8")[:300]))
            continue
        ready[identity] = final_files(card, data, smoked, code_revision)
    staging = Path(staging)

    def test(identity):
        return identity, _test(staging / file_stem(identity), ready[identity])

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        results = dict(pool.map(test, sorted(ready)))
    for identity in sorted(ready):
        card = prepared[identity]
        subject = f"{card.contract['image']['name']}:{card.contract['image']['resolved_tag']}"
        try:
            built.append(_package(card, ready[identity], collection, code_revision=code_revision,
                                  generated_on=generated_on, tests=results[identity],
                                  smoked=identity in smoke))
        except SupplyRecordError as error:
            reason = error.code if error.code in PACKAGE_REASONS + (GENERATED_TEST_FAILED,) else "package_path_invalid"
            refused.append(refusal(CONTAINER_IMAGE_CARDS, reason, subject, str(error)[:300]))
    return built, refused


def facts_of(collection: CollectionSources, families: list) -> dict:
    """{SHA-256: bytes} of every fact the packages name whose bytes the run holds, for the store's quarantine: the
    library files, the documentation files, both licence files and every registry document."""
    rows = [collection.library_licence, collection.docs_licence, *collection.library_files.values()]
    rows += [row for folder in collection.docs_files.values() for row in folder.values()]
    found = {row["sha256"]: row["bytes"] for row in rows if row.get("bytes")}
    for facts in families:
        for document in facts.documents:
            found[document.digest.split(":", 1)[1]] = document.data
    return found


#: The review panel's settings, whose extra secret patterns qualification adds to the repository's own.
PANEL_SETTINGS = Path(__file__).resolve().parents[1] / "candidate_review" / "resources" / "panel.json"
SECRET_ENGINE, EXTRA_PATTERNS = "builtin_secret_patterns", "extra_patterns"


def secret_patterns(panel: Path = PANEL_SETTINGS) -> tuple:
    """The patterns qualification's secret check refuses a value by: the repository's own and the panel's extras."""
    from loop_engine.core.model_call_records import default_secret_patterns
    settings = json.loads(Path(panel).read_text(encoding="utf-8"))["precheck_engines"][SECRET_ENGINE]
    return tuple(re.compile(pattern) for pattern in (*default_secret_patterns(), *settings[EXTRA_PATTERNS]))


def subject_of(card: PreparedCard) -> str:
    """name:tag of a card's resolved tag, the way a run names the cards to smoke."""
    return f"{card.contract['image']['name']}:{card.contract['image']['resolved_tag']}"


def generate(collection: CollectionSources, registry, *, code_revision: str, licence_text: bytes, generated_on: str,
             staging: Path, secret: tuple, workers: int = 8, registry_workers: int = 1, maximum_families: int = 0,
             smoke_runner=None, smoke_subjects=(), evidence_folder: "Path | None" = None, progress=None) -> tuple:
    """(built, refusals, facts, summary): read every family, prepare its card, check them all on the registry, smoke
    the named ones (name:tag of a family's first tag) whose check passed, then package the cards whose evidence
    holds."""
    families, refusals = read_families(collection, registry, secret, maximum_families=maximum_families,
                                       workers=registry_workers, progress=progress)
    prepared = prepare(families, collection, licence_text, refusals)
    evidence = registry_evidence(prepared, registry, evidence_folder, workers=registry_workers,
                                 progress=progress) if prepared else {}
    smoke = {}
    for identity, card in sorted(prepared.items()):
        if smoke_runner is None or subject_of(card) not in smoke_subjects or identity not in evidence:
            continue
        if json.loads(evidence[identity]).get("state") != PASSED:
            continue
        try:
            smoke[identity] = smoke_runner(card)
        except Exception as error:  # noqa: BLE001 - a smoke run that breaks is a failed smoke run, by name
            smoke[identity] = json.dumps({"state": native.FAILED, "error": type(error).__name__}).encode()
        if evidence_folder is not None:
            target = Path(evidence_folder) / "smoke" / f"{file_stem(identity)}.json"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(smoke[identity])
    built, package_refusals = package(prepared, evidence, smoke, collection, code_revision=code_revision,
                                      generated_on=generated_on, staging=staging, workers=workers)
    refusals = list(collection.refusals) + refusals + package_refusals
    platforms = sum(len(payload["repository"]["platforms"]) for payload, _bodies in built)
    summary = {"library_commit": collection.library_commit, "docs_commit": collection.docs_commit,
               "repositories": len(collection.library_files), "families_read": len(families),
               "prepared": len(prepared), "checked": len(evidence), "smoked": len(smoke), "packaged": len(built),
               "refused": len(refusals), "platform_images": platforms, "registry": registry.summary()}
    return built, refusals, facts_of(collection, families), summary


__all__ = ["GENERATOR_VERSION", "NATIVE_FORMAT", "STATE_SCOPE", "GITHUB_HOSTS", "LineStopped", "CollectionSources",
           "FamilyFacts", "PreparedCard", "read_collection", "read_family", "read_families", "prepare",
           "registry_evidence", "package", "generate", "facts_of", "secret_patterns", "copyright_line",
           "UNREAD_REASONS", "family_identity", "subject_of"]
