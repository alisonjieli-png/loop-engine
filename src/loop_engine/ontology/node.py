"""Compatibility imports for the former passive ``ontology.node`` module.

New code imports passive objects from ``ontology.records``. ``NodeError`` is
kept as an exact pre-1.0 alias and does not name a runtime or record category.
"""
from __future__ import annotations

from .records import CatalogRecord, ObjectIdentity, OntologyRecordError

NodeError = OntologyRecordError

__all__ = (
    "CatalogRecord", "NodeError", "ObjectIdentity", "OntologyRecordError",
)
