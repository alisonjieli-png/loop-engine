"""Seed primitives for the generation package.

A seed is starting material for generation: data, never a Node. The
SeedArtifact type and the closed SEED_SOURCES vocabulary are defined
in model.fragments and re-exported here for a stable import path.
"""
from __future__ import annotations

from .fragments import SeedArtifact, SEED_SOURCES

__all__ = ("SEED_SOURCES", "SeedArtifact")
