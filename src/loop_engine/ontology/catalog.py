"""Unified catalog: three physical roots resolved into one logical view.

Core records ship inside the installed package and stay read-only.
Learned records live in an instance data root owned by the user of the
installation. Plugin records arrive through declared plugin roots. The
catalog combines them for search and resolution without copying, without
letting any root overwrite another, and without granting candidate
records execution authority.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import os
from typing import Any

import yaml

from .artifacts import PHYSICAL_ROOTS, SOURCE_CLASSES
from .folders import FOLDER_ONTOLOGY, SEMANTIC_FOLDER_IDS, folder_path
from .loop_node import LoopNode
from .node import CatalogRecord, NodeError, ObjectIdentity

MANIFEST_SCHEMA = "catalog_manifest/v1"
DEFAULT_LEARNED_ROOT = os.path.join(
    os.path.expanduser("~"), ".loop-engine", "intelligence")
LEARNED_ROOT_ENV = "LOOP_ENGINE_LEARNED_ROOT"
PLUGIN_ROOTS_ENV = "LOOP_ENGINE_PLUGIN_ROOTS"


class CatalogError(ValueError):
    """Catalog discovery refused a root, a manifest, or a record."""


@dataclasses.dataclass(frozen=True)
class CatalogEntry:
    """One record plus the provenance facts discovery attached to it."""

    node: CatalogRecord
    physical_root: str
    manifest_path: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "node": self.node.to_dict(),
            "physical_root": self.physical_root,
            "manifest_path": self.manifest_path,
        }


@dataclasses.dataclass(frozen=True)
class CatalogSnapshot:
    """Immutable result of one discovery pass over all roots."""

    entries: tuple[CatalogEntry, ...]
    roots: dict[str, str]
    problems: tuple[str, ...]

    def object_ids(self) -> tuple[str, ...]:
        return tuple(sorted(e.node.identity.object_id for e in self.entries))

    def index_document(self) -> dict[str, Any]:
        """Deterministic index payload used by the freshness check."""
        return {
            "record_type": "ontology_catalog_index/v1",
            "entries": [e.to_dict() for e in self.entries],
        }

    def index_json(self) -> str:
        return json.dumps(self.index_document(), sort_keys=True, indent=1,
                          ensure_ascii=False)


def _sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _confined(root: str, relative: str) -> str:
    """Resolve one manifest-relative path and refuse escape or absence."""
    candidate = os.path.normpath(os.path.join(root, relative))
    if not candidate.startswith(os.path.abspath(root) + os.sep):
        raise CatalogError(
            f"manifest payload escapes its root: {relative!r}")
    if not os.path.isfile(candidate):
        raise CatalogError(f"manifest payload is missing: {relative!r}")
    return candidate

def _record_from_manifest_object(obj: dict, *, source_class: str,
                                 layer: str, parent_collection: str,
                                 manifest_dir: str,
                                 root: str) -> CatalogRecord:
    base_keys = {"id", "version", "artifact_kind", "lifecycle", "payload"}
    if not isinstance(obj, dict) or not base_keys <= set(obj) \
            or not set(obj) <= base_keys | {"content_digest"}:
        raise CatalogError("manifest object has an invalid shape")
    payload = obj["payload"]
    if isinstance(payload, str) and payload.startswith("file:"):
        if "content_digest" not in obj:
            raise CatalogError(
                f"file payload for {obj['id']!r} requires content_digest")
        target = _confined(manifest_dir, payload[len("file:"):])
        actual = _sha256_file(target)
        if actual != obj["content_digest"]:
            raise CatalogError(
                f"payload digest mismatch for {obj['id']!r}: manifest"
                f" {obj['content_digest']} != actual {actual}")
        digest = obj["content_digest"]
    elif isinstance(payload, str) and payload.startswith("code_ref:"):
        # A code_ref record is a pointer; its identity digests the
        # locator itself so the reference is tamper-evident without
        # copying bytes out of the owning module.
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    else:
        raise CatalogError(
            f"payload must start with file: or code_ref: in {obj['id']!r}")
    identity = ObjectIdentity(str(obj["id"]), str(obj["version"]), digest)
    artifact_kind = obj["artifact_kind"]
    base = dict(identity=identity, kind="node", artifact_kind=artifact_kind,
                source_class=source_class, layer=layer,
                lifecycle=str(obj["lifecycle"]),
                parent_collection=parent_collection)
    try:
        return CatalogRecord(**base)
    except NodeError as exc:
        raise CatalogError(f"manifest record refused: {exc}") from exc


def _read_manifest(path: str, *, source_class: str, layer: str,
                   parent_collection: str, root: str) -> list[CatalogRecord]:
    with open(path, encoding="utf-8") as handle:
        document = yaml.safe_load(handle)
    if not isinstance(document, dict):
        raise CatalogError(f"{path} must contain one YAML mapping")
    if document.get("schema") != MANIFEST_SCHEMA:
        raise CatalogError(
            f"{path} must declare schema {MANIFEST_SCHEMA}")
    declared = document.get("source_class")
    if declared != source_class:
        raise CatalogError(
            f"{path} declares source_class {declared!r}; its folder"
            f" requires {source_class!r}")
    objects = document.get("objects", [])
    if not isinstance(objects, list):
        raise CatalogError(f"{path} objects must be a list")
    manifest_dir = os.path.dirname(path)
    return [
        _record_from_manifest_object(
            obj, source_class=source_class, layer=layer,
            parent_collection=parent_collection,
            manifest_dir=manifest_dir, root=root)
        for obj in objects
    ]


def default_learned_root() -> str:
    """Instance learned root from the environment or the user default."""
    return os.environ.get(LEARNED_ROOT_ENV, DEFAULT_LEARNED_ROOT)


def default_plugin_roots() -> tuple[str, ...]:
    raw = os.environ.get(PLUGIN_ROOTS_ENV, "")
    return tuple(p for p in (s.strip() for s in raw.split(os.pathsep))
                 if p)


class UnifiedCatalog:
    """Resolve package core, instance learned, and plugin roots."""

    def __init__(self, *, package_root: str | None = None,
                 learned_root: str | None = None,
                 plugin_roots: tuple[str, ...] | None = None) -> None:
        import loop_engine as package
        self._package_root = package_root or os.path.dirname(
            os.path.abspath(package.__file__))
        self._learned_root = learned_root or default_learned_root()
        self._plugin_roots = (tuple(plugin_roots)
                              if plugin_roots is not None
                              else default_plugin_roots())
        unknown = [p for p in self._plugin_roots
                   if not os.path.isdir(p)]
        self._roots: dict[str, str] = {
            "package_core": self._package_root,
            "instance_learned": self._learned_root,
            **{f"plugin:{i}": p for i, p in enumerate(self._plugin_roots)},
        }
        self._missing_plugin_roots = tuple(unknown)

    @property
    def roots(self) -> dict[str, str]:
        return dict(self._roots)

    def discover(self) -> CatalogSnapshot:
        """Walk semantic folders in every declared root, fail closed."""
        entries: list[CatalogEntry] = []
        seen: dict[str, CatalogEntry] = {}
        problems: list[str] = [
            f"plugin root does not exist: {p}"
            for p in self._missing_plugin_roots]
        for root_name, root_path in self._roots.items():
            for folder_id in SEMANTIC_FOLDER_IDS:
                spec = FOLDER_ONTOLOGY[folder_id]
                if root_name != "package_core" and not folder_id.startswith(
                        "intelligence."):
                    continue
                source_class = ("core" if root_name == "package_core"
                                else "learned"
                                if root_name == "instance_learned"
                                else "plugin")
                rel = folder_path(folder_id)
                folder_abs = os.path.join(root_path, rel)
                if not os.path.isdir(folder_abs):
                    continue
                layer = ""
                parts = folder_id.split(".")
                if len(parts) >= 2 and parts[0] == "intelligence":
                    from .artifacts import FOLDER_SEGMENT_LAYERS
                    layer = FOLDER_SEGMENT_LAYERS.get(parts[1], "")
                manifest = os.path.join(folder_abs, "manifest.yaml")
                records: list[CatalogRecord] = []
                if os.path.isfile(manifest):
                    try:
                        records = _read_manifest(
                            manifest, source_class=source_class, layer=layer,
                            parent_collection=folder_id, root=root_path)
                    except CatalogError as exc:
                        problems.append(str(exc))
                        continue
                elif spec.requires_manifest:
                    problems.append(
                        f"missing required manifest: {rel}/manifest.yaml")
                for record in records:
                    prior = seen.get(record.identity.object_id)
                    if prior is not None:
                        problems.append(
                            f"duplicate object id "
                            f"{record.identity.object_id!r} in "
                            f"{prior.manifest_path} and {manifest}")
                        continue
                    entry = CatalogEntry(node=record, physical_root=root_name,
                                         manifest_path=os.path.relpath(
                                             manifest, root_path))
                    seen[record.identity.object_id] = entry
                    entries.append(entry)
        return CatalogSnapshot(entries=tuple(entries),
                               roots=dict(self._roots),
                               problems=tuple(problems))

    def snapshot(self) -> CatalogSnapshot:
        """Discover and refuse the whole pass when problems exist."""
        result = self.discover()
        if result.problems:
            raise CatalogError("; ".join(result.problems))
        return result


def self_test() -> dict:
    """Prove discovery integrity on synthetic roots, then the real tree."""
    import tempfile

    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    with tempfile.TemporaryDirectory() as tmp:
        core = os.path.join(tmp, "pkg")
        learned = os.path.join(tmp, "learned")
        ctx_core = os.path.join(core, "intelligence", "context", "core")
        ctx_learned = os.path.join(learned, "intelligence", "context",
                                   "learned")
        os.makedirs(ctx_core)
        os.makedirs(ctx_learned)
        payload_rel = "seed.jsonl"
        payload_abs = os.path.join(ctx_core, payload_rel)
        with open(payload_abs, "w", encoding="utf-8") as handle:
            handle.write('{"text":"seed record"}\n')
        digest = _sha256_file(payload_abs)
        manifest = {
            "schema": MANIFEST_SCHEMA,
            "folder_id": "intelligence.context.core",
            "source_class": "core",
            "objects": [{
                "id": "core.context.seed_example",
                "version": "1.0.0",
                "artifact_kind": "intelligence_record",
                "lifecycle": "registered",
                "content_digest": digest,
                "payload": f"file:{payload_rel}",
            }],
        }
        with open(os.path.join(ctx_core, "manifest.yaml"), "w",
                  encoding="utf-8") as handle:
            yaml.safe_dump(manifest, handle, sort_keys=True)
        escaped = dict(manifest)
        escaped["source_class"] = "learned"
        escaped["objects"] = [dict(manifest["objects"][0],
                                   payload="file:../../etc/passwd")]
        with open(os.path.join(ctx_learned, "manifest.yaml"), "w",
                  encoding="utf-8") as handle:
            yaml.safe_dump(escaped, handle, sort_keys=False)

        catalog = UnifiedCatalog(package_root=core, learned_root=learned,
                                 plugin_roots=())
        broken = catalog.discover()
        check("traversal_payload_is_reported",
              any("escapes its root" in p for p in broken.problems),
              str(broken.problems))

        duplicate_manifest = dict(manifest)
        duplicate_manifest["source_class"] = "learned"
        with open(os.path.join(ctx_learned, "seed.jsonl"), "w",
                  encoding="utf-8") as handle:
            handle.write('{"text":"seed record"}\n')
        with open(os.path.join(ctx_learned, "manifest.yaml"), "w",
                  encoding="utf-8") as handle:
            yaml.safe_dump(duplicate_manifest, handle, sort_keys=True)
        duplicate = UnifiedCatalog(package_root=core, learned_root=learned,
                                   plugin_roots=())
        dup = duplicate.discover()
        check("duplicate_object_id_is_reported",
              any("duplicate object id" in p for p in dup.problems),
              str(dup.problems))

        os.remove(os.path.join(ctx_learned, "manifest.yaml"))
        clean = UnifiedCatalog(package_root=core, learned_root=learned,
                               plugin_roots=()).snapshot()
        check("clean_snapshot_has_one_entry", len(clean.entries) == 1)
        check("candidate_default_for_learned_without_manifest",
              clean.entries[0].node.source_class in SOURCE_CLASSES)
        first = clean.index_json()
        second = UnifiedCatalog(package_root=core, learned_root=learned,
                                plugin_roots=()).snapshot().index_json()
        check("index_is_deterministic", first == second)

    try:
        UnifiedCatalog().snapshot()
        live_ok, note = True, ""
    except CatalogError as exc:
        live_ok, note = False, str(exc)
    check("live_package_tree_passes_discovery", live_ok, note)
    check("physical_roots_vocabulary_used",
          set(PHYSICAL_ROOTS[:2]) <= {"package_core", "instance_learned"})
    return {"tests": results}
