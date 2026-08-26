"""The central folder ontology: one typed spec per semantic folder.

The repository rule is that the folder structure mirrors the persistent
architecture. This table is the machine-readable form of that mirror.
README front matter, manifests, catalog discovery, and structural checks
all read their expectations from here, so the folder tree cannot drift
from the architecture by silent local edits.
"""
from __future__ import annotations

from dataclasses import dataclass

from .artifacts import (
    ARTIFACT_KINDS,
    CORE_LAYER_IDS,
    LAYER_FOLDER_SEGMENTS,
    ONTOLOGY_VERSION,
)


@dataclass(frozen=True)
class FolderSpec:
    """Contract for one semantic folder."""

    folder_id: str
    parent: str
    purpose: str
    artifact_kinds: tuple[str, ...] = ()
    requires_manifest: bool = False
    python_free: bool = True


def _layer_folders() -> dict[str, FolderSpec]:
    specs: dict[str, FolderSpec] = {}
    for layer_id, segment in LAYER_FOLDER_SEGMENTS.items():
        fid = f"intelligence.{segment}"
        specs[fid] = FolderSpec(
            folder_id=fid,
            parent="intelligence",
            purpose=(f"Persistent {layer_id} collection grouped by"
                     " provenance."),
            artifact_kinds=("intelligence_record",))
        for source in ("core", "learned", "plugin"):
            sfid = f"{fid}.{source}"
            specs[sfid] = FolderSpec(
                folder_id=sfid,
                parent=fid,
                purpose=f"{source}-provenance records for {layer_id}.",
                artifact_kinds=("intelligence_record",),
                requires_manifest=(
                    source == "core" and layer_id in CORE_LAYER_IDS))
    return specs


def _root_table() -> dict[str, FolderSpec]:
    specs = {
        "ontology": FolderSpec(
            folder_id="ontology",
            parent="",
            purpose=("The closed foundational object classes and the"
                     " catalog that combines physical roots."),
            artifact_kinds=tuple(ARTIFACT_KINDS),
            python_free=False),
        "intelligence": FolderSpec(
            folder_id="intelligence",
            parent="",
            purpose=("The four persistent intelligence layers at rest,"
                     " each split into core, learned, and plugin"
                     " provenance."),
            artifact_kinds=("intelligence_record",)),
        "kernel": FolderSpec(
            folder_id="kernel",
            parent="",
            purpose=("Kernel concerns documented at rest: loading,"
                     " resolution, execution, and enforcement. Each"
                     " member names the existing owning modules; it does"
                     " not add another executor."),
            python_free=True),
        "runtime": FolderSpec(
            folder_id="runtime",
            parent="",
            purpose=("Per-run state at rest: saved runs, Runtime Memory"
                     " scope rules, and offloaded artifacts. Nothing here"
                     " is persistent intelligence."),
            python_free=True),
        "governance": FolderSpec(
            folder_id="governance",
            parent="",
            purpose=("Candidate staging through independent review,"
                     " approval, and explicit promotion. Promotion is"
                     " never inferred from retrieval or a good score."),
            artifact_kinds=("intelligence_record", "policy")),
    }
    for name, purpose in (
            ("loader", "Binds records and payloads from the three"
                       " physical roots; owned today by"
                       " core.knowledge_loader and"
                       " ontology.catalog."),
            ("resolver", "Turns references into registered profiles and"
                         " definitions; owned today by"
                         " loop.loop_profile_ontology."),
            ("executor", "Runs one Loop; owned solely by"
                         " loop.recursive_loop. There is no second"
                         " executor."),
            ("enforcement", "Approvals, boundaries, and workspaces;"
                            " owned today by loop.effect_approval and"
                            " core boundary services.")):
        specs[f"kernel.{name}"] = FolderSpec(
            folder_id=f"kernel.{name}", parent="kernel", purpose=purpose)
    for name, purpose in (
            ("runs", "Saved Run History trees written by the Loop"
                     " runtime; runtime output, not catalog artifacts."),
            ("runtime_memory", "Temporary single-run state; never"
                               " promoted into a persistent layer"
                               " automatically."),
            ("artifacts", "Digest-addressed offloaded context payloads;"
                          " runtime output, not catalog artifacts.")):
        specs[f"runtime.{name}"] = FolderSpec(
            folder_id=f"runtime.{name}", parent="runtime", purpose=purpose)
    gov_purposes = {
        "candidates": "Unreviewed staged output; candidate-only by"
                      " definition and excluded from search unless a"
                      " query explicitly includes candidates.",
        "review": "Independent verification records produced by a"
                  " process that did not author the candidate.",
        "approval": "Durable, exact-effect-bound decisions consumed"
                    " once; owned today by loop.effect_approval.",
        "promotion": "Explicit promotion records only; retrieval, a"
                     " good score, or model confidence never promotes"
                     " anything.",
    }
    for name, purpose in gov_purposes.items():
        specs[f"governance.{name}"] = FolderSpec(
            folder_id=f"governance.{name}", parent="governance",
            purpose=purpose, artifact_kinds=("intelligence_record",))
    specs.update(_layer_folders())
    return specs


#: The authoritative folder table, keyed by dotted folder id.
FOLDER_ONTOLOGY: dict[str, FolderSpec] = _root_table()

SEMANTIC_FOLDER_IDS: tuple[str, ...] = tuple(sorted(FOLDER_ONTOLOGY))


def folder_path(folder_id: str) -> str:
    """On-disk path relative to the package root for one folder id."""
    spec = FOLDER_ONTOLOGY.get(folder_id)
    if spec is None:
        raise KeyError(f"unknown folder_id {folder_id!r}")
    return folder_id.replace(".", "/")


def folder_id_for_relpath(relpath: str) -> str:
    """Reverse of folder_path; empty when the path is not semantic."""
    posix = relpath.replace("\\", "/").strip("/")
    if not posix:
        return ""
    candidate = ".".join(posix.split("/"))
    return candidate if candidate in FOLDER_ONTOLOGY else ""


def expected_front_matter(folder_id: str) -> dict[str, str]:
    """Front-matter keys every README in this folder must declare."""
    spec = FOLDER_ONTOLOGY.get(folder_id)
    if spec is None:
        raise KeyError(f"unknown folder_id {folder_id!r}")
    return {
        "folder_id": folder_id,
        "parent": spec.parent,
        "ontology_version": ONTOLOGY_VERSION,
    }


def self_test() -> dict:
    """Prove the folder table stays total, acyclic, and path-reversible."""
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    missing_parent = [fid for fid, spec in FOLDER_ONTOLOGY.items()
                      if spec.parent and spec.parent not in FOLDER_ONTOLOGY]
    check("every_folder_has_registered_parent", not missing_parent,
          str(missing_parent))
    bad_kinds = [fid for fid, spec in FOLDER_ONTOLOGY.items()
                 if any(k not in ARTIFACT_KINDS for k in spec.artifact_kinds)]
    check("artifact_kinds_stay_closed", not bad_kinds, str(bad_kinds))
    reversible = [fid for fid in SEMANTIC_FOLDER_IDS
                  if folder_id_for_relpath(folder_path(fid)) != fid]
    check("folder_ids_round_trip_through_paths", not reversible,
          str(reversible))
    check("ontology_folder_is_the_only_python_root",
          all(FOLDER_ONTOLOGY[fid].python_free
              for fid in SEMANTIC_FOLDER_IDS if fid != "ontology"))
    return {"tests": results}
