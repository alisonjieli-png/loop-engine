"""Store adapter implementations for the unified intelligence catalog.

Each adapter implements the CatalogStore protocol for one backend kind
and declares its real capabilities. No adapter is the ontology; the
logical record identity never depends on the backend.
"""
from __future__ import annotations
