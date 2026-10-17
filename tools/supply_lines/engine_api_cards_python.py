"""The Python adapter of the engine_api_cards line: one release of a library of python_libraries.json a run.

```text
read_python(reader, workspace, identity)
├── the interpreter: the pinned CPython (path and version in the sources), its binary's SHA-256
├── facts: the release's PyPI record; the library's wheel and every pinned dependency's, by PyPI's SHA-256, each
│   member by the wheel's RECORD (tools/engine_api_cards/python_wheels.py); the tag's commit and tree on GitHub
├── licence: GitHub's licence interface and the licence file's text agree on an allowlisted licence at the tag (or
│   at the default branch for the same blob, tag_licence), and the package's own PyPI metadata names it
├── source identity: at least half of the wheel's Python files must be the tag's blobs, else the release is not
│   the tag's; a file that differs refuses the objects defined in it by name
├── surface: one sandboxed import of the wheels (python_native.py), no network; a top module whose import touches
│   the network, starts a process or writes a file stops the release
├── units: python_reference.Builder (class, function, method and property cards; texts traced to the tag)
└── native check: a second sandboxed run of the same interpreter over every card (python_evidence)
```

The line calls no model. A package is a candidate until qualification and the ongoing independent review.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from engine_api_cards import cards, python_native, python_reference, python_wheels
from engine_api_cards.godot_native import NativeError, evidence_bytes

from .engine_api_cards import EngineSources, LineStopped, tag_licence
from .function_extracts import foreign_licences
from .reading import RAW_HOST, github_blob_address, https_address, pinned_files, repository_notice
from .records import ENGINE_API_CARDS, GENERATED_CODE_LICENCE, refusal

SOURCES_FILE = Path(__file__).resolve().parents[1] / "engine_api_cards" / "python_libraries.json"
SOURCES_RECORD = "python_api_card_sources/v1"
HOSTS = (RAW_HOST, python_wheels.PYPI_HOST, python_wheels.FILES_HOST)
#: Below this share of the wheel's Python files proven to be the tag's blobs, the wheel is not the tag's release.
MINIMUM_PROVEN_SHARE = 0.5
TEXT_FORMAT = "Python docstrings"
TEXT_BASIS = "docstring_traced_to_the_source_files_at_the_tag"
RELEASE_BASIS = "published_wheel_of_the_tag_imported_in_a_sandbox_never_copied"
#: The classifiers of a package's metadata and the licences each names (a BSD classifier names either clause count).
CLASSIFIER_LICENCES = {"MIT License": ("MIT",), "Apache Software License": ("Apache-2.0",),
                       "BSD License": ("BSD-2-Clause", "BSD-3-Clause"), "ISC License (ISCL)": ("ISC",),
                       "The Unlicense (Unlicense)": ("Unlicense",)}
CLASSIFIER_PREFIX = "License :: OSI Approved :: "
_EXPRESSION_WORDS = frozenset(("AND", "OR", "WITH"))
LIMITS = ("The surface is what the published wheel reports when the pinned CPython imports it in a sandbox with no "
          "network: the classes and functions that the library's public modules export and the library itself "
          "defines, and each class's public methods, properties, fields and constants (special methods, and the "
          "members of a listed ancestor, are on that ancestor's card or not listed). Signatures and types are the "
          "release's own annotations as written, which no import can confirm. The text is each object's own "
          "docstring, quoted verbatim; at least nine in ten of its lines occur in the release's source files at the "
          "tag. Objects that are instances (a scipy.stats distribution), module constants and members other modules "
          "add at run time are not carded. Nothing here was loaded by a harness.")


def read_sources(path: Path = SOURCES_FILE) -> dict:
    record = json.loads(Path(path).read_text(encoding="utf-8"))
    if record.get("record_type") != SOURCES_RECORD:
        raise ValueError(f"expected {SOURCES_RECORD}")
    identities = [row["identity"] for row in record["libraries"]]
    if len(identities) != len(set(identities)):
        raise ValueError("every library row has its own identity")
    return record


def library(record: dict, identity: str) -> dict:
    for row in record["libraries"]:
        if row["identity"] == identity:
            return row
    raise LookupError(f"no library row {identity!r} in {SOURCES_FILE.name}")


def package_licences(info: dict) -> set:
    """The licences a package's own PyPI metadata names: its licence expression (PEP 639), else its licence field (a
    short name or a licence text), and its licence classifiers."""
    from loop_engine.core.library_ingestion.licences import match_licence, notice_identifier
    expression = info.get("license_expression")
    if expression:
        return {word for word in re.findall(r"[A-Za-z0-9.+-]+", expression) if word not in _EXPRESSION_WORDS}
    named = set()
    text = (info.get("license") or "").strip()
    if text:
        found = notice_identifier(text) if len(text) <= 80 else None
        found = found or match_licence(text).spdx
        if found:
            named.add(found)
    for classifier in info.get("classifiers") or ():
        if classifier.startswith(CLASSIFIER_PREFIX):
            named.update(CLASSIFIER_LICENCES.get(classifier[len(CLASSIFIER_PREFIX):], ()))
    return named


SANDBOX_IMPORT_ENGINE, WHEEL_AST_ENGINE = "sandbox_import", "wheel_ast"
SURFACE_ENGINES = (SANDBOX_IMPORT_ENGINE, WHEEL_AST_ENGINE)


def major_minor(version: str) -> str:
    return ".".join(version.split(".")[:2])


def read_python(reader, workspace: Path, identity: str, *, cache_root: Path, record: "dict | None" = None,
                only=(), timeout: float = 3600.0, surface_engine: str = SANDBOX_IMPORT_ENGINE) -> EngineSources:
    """Read one pinned Python library release and its surface; raises LineStopped when the release as a whole cannot
    be carded."""
    if surface_engine not in SURFACE_ENGINES:
        raise ValueError(f"unknown surface_engine {surface_engine!r}; expected one of {SURFACE_ENGINES}")
    record = record or read_sources()
    row = library(record, identity)
    interpreter = record["interpreter"]
    workspace = Path(workspace)
    try:
        engine = python_native.locate(interpreter["path"], interpreter["version"])
        wheel, document, answer = python_wheels.install(reader, row["distribution"], row["version"], interpreter,
                                                        cache_root)
        dependencies = [python_wheels.install(reader, *python_wheels.requirement(pin), interpreter, cache_root)[0]
                        for pin in row.get("dependencies", ())]
    except python_wheels.WheelError as error:
        raise LineStopped(error.reason, error.detail) from None
    except NativeError as error:
        raise LineStopped("engine_binary_unverified", str(error)) from None
    repository, tag = row["repository"], row["tag"]
    head = reader.github(f"repos/{repository}/commits/{tag}")
    if head.status != 200:
        raise LineStopped("source_unreadable", f"the tag {tag} has no readable commit")
    commit = json.loads(head.body)["sha"]
    tree = reader.github(f"repos/{repository}/git/trees/{commit}?recursive=1")
    if tree.status != 200 or json.loads(tree.body).get("truncated"):
        raise LineStopped("source_unreadable", f"no complete tree at {commit[:12]}")
    blobs = {entry["path"]: entry["sha"] for entry in json.loads(tree.body).get("tree", []) if entry.get("type") == "blob"}
    found = reader.licence_text(repository, commit)
    if found is None:
        raise LineStopped("licence_unknown", f"{repository} at {commit[:12]}: no licence file")
    licence_path = found[0]
    pinned_licence, missing = pinned_files(reader, repository, commit, [licence_path])
    if missing:
        raise LineStopped("source_unreadable", licence_path)
    decision, licence_basis = tag_licence(reader, repository, commit, pinned_licence[licence_path])
    if not decision.allowed:
        raise LineStopped(decision.reason, f"{repository} at {commit[:12]}: {decision.evidence()}")
    if decision.path != licence_path or decision.sha256 != pinned_licence[licence_path]["sha256"]:
        raise LineStopped("licence_signals_disagree", f"GitHub names {decision.path}, not {licence_path}")
    declared = package_licences(document.get("info") or {})
    if decision.spdx not in declared:
        raise LineStopped("licence_signals_disagree", f"{row['distribution']} {row['version']} declares "
                                                      f"{sorted(declared) or 'no licence'} on PyPI, not {decision.spdx}")
    proofs = python_wheels.prove(blobs, wheel)
    python_files = len(proofs.proven) + len(proofs.differs) + len(proofs.absent)
    if not python_files or len(proofs.proven) < MINIMUM_PROVEN_SHARE * python_files:
        raise LineStopped("published_source_differs", f"{len(proofs.proven)} of {python_files} Python files of "
                                                      f"{wheel.filename} are the blobs of {tag}")
    extras = python_wheels.extra_sources(proofs)
    pinned_extras, _missing_extras = pinned_files(reader, repository, commit, extras) if extras else ({}, [])
    corpus_texts = {proofs.proven[path]: (wheel.folder / path).read_bytes() for path in proofs.proven}
    corpus_texts.update({path: pinned["bytes"] for path, pinned in pinned_extras.items()})
    nested = python_wheels.nested_licence_paths(corpus_texts, blobs, licence_path)
    nested_texts = {path: pinned["bytes"] for path, pinned in pinned_files(reader, repository, commit, nested)[0].items()} \
        if nested else {}
    licence_files = [path for path in blobs if path in nested or path == licence_path]
    corpus, excluded = python_wheels.Corpus(), {}
    for path, data in sorted(corpus_texts.items()):
        text = data.decode("utf-8", "replace")
        problem = python_wheels.licence_problem(path, text, decision.spdx, licence_files, licence_path, nested_texts,
                                                foreign_licences)
        if problem:
            excluded[path] = problem
            continue
        corpus.add(path, text)
    roots = [wheel.folder] + [dependency.folder for dependency in dependencies]
    environment = tuple((item.filename, item.sha256) for item in [wheel] + dependencies)
    engine = python_native.PythonEngine(engine.path, engine.version, engine.sha256, row["distribution"],
                                        wheel.filename, wheel.sha256, environment)
    spec = {"modules": row["modules"], "recurse": row.get("recurse", True), "exclude": row.get("exclude", []),
            "target": 0}
    if surface_engine == WHEEL_AST_ENGINE:
        result = python_wheels.read_wheel_ast(wheel.folder, spec, engine.version)
    else:
        try:
            result = python_native.run(engine, roots, spec, workspace / "read", python_native.READ, timeout=timeout)
        except NativeError as error:
            raise LineStopped("import_failed", str(error)[:300]) from None
    top = row["modules"][0]
    first = next((module for module in result["modules"] if module["name"] == top), None)
    if first is None or not first.get("ok"):
        raise LineStopped("import_failed", f"{top}: {(first or {}).get('error', 'not imported')}")
    for event in result.get("events", ()):
        if event.get("module") == top and event.get("kind") in python_reference.EVENT_REFUSALS:
            raise LineStopped(python_reference.EVENT_REFUSALS[event["kind"]], json.dumps(event)[:300])
    builder = python_reference.Builder(result, proven=proofs.proven, members=wheel.members, corpus=corpus,
                                       excluded=excluded, refusal=lambda reason, subject, detail="": refusal(
                                           ENGINE_API_CARDS, reason, subject, detail))
    units, chains, children = builder.units(top)
    if only:
        units = {name: unit for name, unit in units.items() if name in only}
    pinned, reference_paths, dump = {}, {}, {}
    for name, unit in sorted(units.items()):
        text_path = unit.text_file or proofs.proven.get(unit.surface_file)
        if text_path is None:
            builder.refusals.append(refusal(ENGINE_API_CARDS, "text_not_traced_to_the_tag", name,
                                            "no source file holds its text"))
            continue
        if text_path not in pinned:
            data = corpus_texts[text_path]
            pinned[text_path] = {"url": https_address(RAW_HOST, f"{repository}/{commit}/{text_path}"), "bytes": data,
                                 "sha256": hashlib.sha256(data).hexdigest(), "blob": blobs[text_path],
                                 "retrieved_at": (pinned_extras.get(text_path) or {}).get("retrieved_at",
                                                                                          wheel.retrieved_at)}
        reference_paths[name] = text_path
        dump[name] = (unit.surface_file, wheel.members[unit.surface_file])
    units = {name: unit for name, unit in units.items() if name in reference_paths}
    version, api_version = row["version"], major_minor(row["version"])
    notice = repository_notice(reader, repository, commit, decision.spdx) if decision.spdx == "Apache-2.0" else None
    release = cards.EngineRelease(
        name=row["distribution"], title=row["title"], release=tag, version=version, api_version=api_version,
        repository=repository, commit=commit, binary_name=wheel.filename, binary_sha256=wheel.sha256,
        binary_version=version, docs_address="", syntax=cards.card_module().PYTHON_SYNTAX,
        surface_source=(f"introspected from the wheel `{wheel.filename}` (SHA-256 `{wheel.sha256}`) as CPython "
                        f"{engine.version} imports it in a sandbox with no network"),
        surface_phrase="the surface the published wheel itself reports when it is imported",
        text_format=TEXT_FORMAT, licence=decision.spdx, notice_file="UPSTREAM-NOTICE" if notice else "",
        text_phrase="the library's own docstring", text_conversion="the object's own docstring, quoted verbatim")
    licence = dict(pinned_licence[licence_path], evidence=decision.evidence(), basis=licence_basis)
    metadata = {"url": python_wheels.pypi_address(row["distribution"], version), "bytes": answer.body,
                "sha256": answer.sha256, "retrieved_at": answer.retrieved_at}
    asset = {"url": wheel.url, "sha256": wheel.sha256, "size_bytes": wheel.size_bytes,
             "retrieved_at": wheel.retrieved_at, "member": wheel.filename}
    references = {name: unit.reference for name, unit in units.items()}
    locations = {name: unit.location for name, unit in units.items()}
    summary = {"distribution": row["distribution"], "version": version, "wheel": wheel.filename,
               "surface_engine": surface_engine, "environment": [list(item) for item in environment],
               "python_files": python_files,
               "proven_files": len(proofs.proven), "differing_files": sorted(proofs.differs)[:50],
               "files_not_in_the_tag": sorted(proofs.absent)[:50], "extra_text_files": len(pinned_extras),
               "excluded_text_files": excluded, "modules": len(result["modules"]),
               "modules_failed": sorted(module["name"] for module in result["modules"] if not module.get("ok")),
               "local_events": sum(1 for event in result.get("events", ()) if event.get("kind") == "local"),
               "units": {kind: sum(1 for unit in units.values() if unit.reference.kind.value == kind)
                         for kind in ("class", "function", "method", "property")}, **builder.counts}
    sources = EngineSources(
        release, dump, references, dict(references), reference_paths, pinned, licence, None, {}, None, asset,
        list(builder.refusals), summary, text_for=lambda name: python_reference.PyDocText(), licence_path=licence_path,
        text_basis=TEXT_BASIS, limits=LIMITS, state_scope=row["state_scope"], metadata=metadata,
        licence_expression=f"{GENERATED_CODE_LICENCE} AND {decision.spdx}" if decision.spdx != GENERATED_CODE_LICENCE
        else GENERATED_CODE_LICENCE, notices=[notice] if notice else [],
        copyright_text=_own_notice(notice), chains={name: chains[name] for name in units},
        children={name: [child for child in children.get(name, []) if child in units] for name in units},
        locations=locations, release_basis=RELEASE_BASIS, native=(engine, roots))
    return sources


def _own_notice(notice: "dict | None") -> bytes:
    if not notice:
        return b""
    lines = [line for line in notice["bytes"].decode("utf-8", "replace").splitlines() if line.startswith("Copyright")]
    return lines[0].encode("utf-8") if lines else b""


def python_evidence(sources: EngineSources, prepared: dict, workspace: Path, folder: "Path | None" = None,
                    *, timeout: float = 3600.0) -> dict:
    """{card: evidence bytes} from one sandboxed run over every prepared card; a run that cannot happen gives no
    evidence, so every card is refused by name (native_evidence_missing)."""
    engine, roots = sources.native
    apis = [card.api for card in prepared.values()]
    try:
        answers = python_native.verify(engine, roots, apis, sources.locations, Path(workspace) / "verify",
                                       timeout=timeout)
    except NativeError as error:
        sources.summary["native_check_error"] = str(error)[:300]
        return {}
    records = {}
    for name, card in prepared.items():
        data = evidence_bytes(python_native.evidence(engine, card.api, answers.get(name), card.digest))
        records[name] = data
        if folder is not None:
            target = Path(folder) / card.api["engine"]["name"] / f"{re.sub(r'[^A-Za-z0-9_.-]', '_', name)}.json"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    return records


__all__ = ["read_sources", "library", "package_licences", "read_python", "python_evidence", "HOSTS", "LIMITS",
           "SOURCES_FILE", "SANDBOX_IMPORT_ENGINE", "WHEEL_AST_ENGINE", "SURFACE_ENGINES"]
