"""Map extracted owner phrases onto query-multiplier dimension ids.

This is the bridge from "what the owner asked for" to "what the discovery grid
should search." The mapping is keyword-based and deliberately transparent: a
reviewer can see exactly why a phrase landed on a dimension. It never invents
a dimension; it only assigns ids that exist in the discovery library.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

#: Keyword triggers -> dimension id. A phrase containing any trigger maps to
#: that dimension. Ordered; a phrase may land on several dimensions.
TRIGGERS = {
    "sdg_goal": ("sdg", "sustainable development", "public good", "united nations goal"),
    "sdg_target": ("sdg target", "indicator"),
    "onet_occupation": ("for a ", "job", "role", "engineer", "designer", "developer", "analyst"),
    "onet_task": ("task", "workflow for", "how to "),
    "industry": ("industry", "sector", "vertical", "fintech", "health", "legal", "agriculture", "construction"),
    "harness_kind": ("harness", "claude code", "codex", "opencode", "mcp", "agent"),
    "step_function": ("function", "recipe", "callable", "operation"),
    "creative_domain": ("video", "social media", "design", "render", "blender", "animation", "image", "creative"),
    "algorithm": ("algorithm", "search", "rank", "sort", "cluster", "embedding"),
    "file_format": ("json", "markdown", "yaml", "csv", "protobuf", "avro", "json-ld", "schema", "shader"),
    "programming_language": ("python", "typescript", "rust", "go ", "javascript"),
    "natural_language": ("spanish", "portuguese", "french", "translate", "multilingual"),
    "geography": ("country", "region", "europe", "africa", "asia", "global"),
    "time_window": ("2026", "weekly", "daily", "monthly", "quarterly", "recent", "latest"),
    "licence": ("licence", "license", "mit", "apache", "permissive", "copyright"),
    "source_type": ("github", "registry", "dataset", "repository", "api"),
    "github_stars": ("top ", "best ", "popular", "stars", "trending"),
    "ranking": ("top ", "best ", "trending", "popular"),
    "authority": ("official", "verified", "trusted", "claimed"),
    "change_type": ("breaking", "deprecat", "security advisory", "withdrawn", "new release", " changelog"),
    "failure_lens": ("cve", "vulnerability", "fails", "broken", "incident", "outage", "advisory"),
    "feed_topic": ("newsletter", "feed", "rss", "digest", "updates", "news", "briefing"),
    "interrogation_template": ("what if", "scenario", "question", "why does", "how does"),
    "demand_channel": ("reddit", "hn", "hacker news", "stack overflow", "dev.to", "product hunt", "lobsters"),
}


def map_phrases(phrases) -> tuple:
    """Return the sorted set of dimension ids these phrases touch."""
    hits = set()
    for phrase in phrases:
        low = phrase.lower()
        for dimension, triggers in TRIGGERS.items():
            if any(trigger in low for trigger in triggers):
                hits.add(dimension)
    return tuple(sorted(hits))
