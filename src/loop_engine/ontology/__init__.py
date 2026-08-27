"""The closed foundational ontology for Loop Engine.

This package defines the two object classes every persistent record
shares, the vocabularies that classify them, the authoritative folder
table that mirrors the architecture onto directories, and the unified
catalog that resolves package core, instance learned, and plugin roots
into one logical view. It adds no runtime: execution starts through
``LoopStartRequest`` into the sole ``Loop`` runtime.
"""
from __future__ import annotations

from importlib import import_module as _import_module

_PUBLIC = {
    # Vocabularies.
    "ONTOLOGY_VERSION": ("artifacts", "ONTOLOGY_VERSION"),
    "ONTOLOGY_OBJECT_KINDS": ("artifacts", "ONTOLOGY_OBJECT_KINDS"),
    "ARTIFACT_KINDS": ("artifacts", "ARTIFACT_KINDS"),
    "SOURCE_CLASSES": ("artifacts", "SOURCE_CLASSES"),
    "PHYSICAL_ROOTS": ("artifacts", "PHYSICAL_ROOTS"),
    "INTELLIGENCE_LAYERS": ("artifacts", "LAYERS"),
    "LAYER_FOLDER_SEGMENTS": ("artifacts", "LAYER_FOLDER_SEGMENTS"),
    # Foundational object classes.
    "OntologyRecordError": ("records", "OntologyRecordError"),
    "ObjectIdentity": ("records", "ObjectIdentity"),
    "CatalogRecord": ("records", "CatalogRecord"),
    "LoopDefinitionRecord": (
        "loop_definition_record", "LoopDefinitionRecord"),
    "LoopDefinitionProjectionRequest": (
        "loop_definition_record", "LoopDefinitionProjectionRequest"),
    # Folder table and structural validation.
    "FolderSpec": ("folders", "FolderSpec"),
    "FOLDER_ONTOLOGY": ("folders", "FOLDER_ONTOLOGY"),
    "SEMANTIC_FOLDER_IDS": ("folders", "SEMANTIC_FOLDER_IDS"),
    "folder_path": ("folders", "folder_path"),
    "folder_id_for_relpath": ("folders", "folder_id_for_relpath"),
    "expected_front_matter": ("folders", "expected_front_matter"),
    "OntologyCheckError": ("ontology_checks", "OntologyCheckError"),
    "run_ontology_checks": ("ontology_checks", "run_checks"),
    # Unified catalog over three physical roots.
    "MANIFEST_SCHEMA": ("catalog", "MANIFEST_SCHEMA"),
    "CatalogError": ("catalog", "CatalogError"),
    "CatalogEntry": ("catalog", "CatalogEntry"),
    "CatalogSnapshot": ("catalog", "CatalogSnapshot"),
    "UnifiedCatalog": ("catalog", "UnifiedCatalog"),
    "default_learned_root": ("catalog", "default_learned_root"),
    "default_plugin_roots": ("catalog", "default_plugin_roots"),
}

__all__ = tuple(_PUBLIC)


def __getattr__(name: str):
    """Load a documented public name only when it is requested."""
    target = _PUBLIC.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module, attribute = target
    return getattr(_import_module(f"{__name__}.{module}"), attribute)


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(_PUBLIC))
