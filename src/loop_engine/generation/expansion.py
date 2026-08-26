"""Variation-space expansion engine for generation campaigns.

``expand_variation_space`` materializes a campaign's typed variation
space into candidate configurations, bounded by the campaign budget
and pruned by conditional rules. The expansion is deterministic data
work; the governed execution of generation runs through Loops.
"""
from __future__ import annotations

from .model.campaign import expand_variation_space

__all__ = ("expand_variation_space",)
