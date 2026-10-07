"""The AgentSignals dimension-generation program: curated bases and the derivation rules.

This is a six-dimension demonstration toward the requested larger grid,
not a claim of 1,000 generated dimensions. It declares small curated bases (engine kinds,
demand channels, roles, task stems, time expressions, change types, …) and the
template/cross rules that expand them into a large, reviewable library.
Every generated dimension keeps a deterministic id, a Baltor-owned MIT source,
and carries through the multiplier's screens.

Run the generator offline; the merged library is what the planner validates. The
generated program's size is printed at run time; the point is that the count is
composition, not hand-writing.
"""
from __future__ import annotations

#: Curated bases: small, reviewable vocabularies. Everything larger is derived.
FAMILIES = {
    "search_engine_kind": {"kind": "source_type", "title": "Search engine or interface kind", "values": [
        ("api", "documented API"), ("feed", "published feed"), ("registry", "package registry"),
        ("scrape", "page scrape"), ("browser", "browser-rendered page"), ("webhook", "event webhook"),
        ("graphql", "GraphQL endpoint"), ("sparql", "SPARQL endpoint")]},
    "demand_channel": {"kind": "source_type", "title": "Demand evidence channel", "values": [
        ("stack_exchange", "Stack Exchange"), ("devto", "dev.to"), ("hn", "Hacker News"),
        ("lobsters", "Lobsters"), ("product_hunt", "Product Hunt"), ("reddit", "Reddit"),
        ("osv", "OSV"), ("forge_alt", "non-GitHub forges")]},
    "role": {"kind": "topic", "title": "Occupation shorthand", "values": [
        ("backend", "backend engineer"), ("frontend", "frontend engineer"), ("mlops", "MLOps engineer"),
        ("data_eng", "data engineer"), ("devrel", "developer advocate"), ("researcher", "researcher"),
        ("designer", "product designer"), ("security", "security engineer"), ("embedded", "embedded engineer"),
        ("legal", "legal engineer"), ("sre", "site reliability engineer"), ("student", "student developer")]},
    "task_stem": {"kind": "topic", "title": "Task stems", "values": [
        ("monitor", "monitor changes to"), ("migrate", "migrate away from"), ("compare", "compare"),
        ("optimize", "optimize"), ("secure", "secure"), ("test", "test"), ("integrate", "integrate"),
        ("debug", "debug")]},
    "time_expr": {"kind": "time_window", "title": "Recency expressions", "values": [
        ("this_week", "this week"), ("this_month", "this month"), ("q2026", "2026 quarter"),
        ("y2026", "2026"), ("oct2026", "October 2026"), ("since_release", "since last release")]},
    "output_unit": {"kind": "format", "title": "Output unit kinds", "values": [
        ("feed_item", "feed item"), ("component_file", "component file"), ("newsletter", "newsletter section"),
        ("short_post", "short social post"), ("video_60_90", "60-90 second video"), ("carousel", "carousel card")]},
    "evidence_tier": {"kind": "qualifier", "title": "Evidence tier", "values": [
        ("lead", "early lead"), ("auto_checked", "automated checks passed"), ("reviewed", "sampled independent review passed"),
        ("executed", "execution evidence"), ("licence_clean", "licence verified permissive")]},
    "object_kind": {"kind": "topic", "title": "Object under observation", "values": [
        ("model", "AI model"), ("library", "software library"), ("framework", "framework"),
        ("saas_api", "SaaS API"), ("cli_tool", "CLI tool"), ("spec", "specification"),
        ("dataset", "dataset"), ("protocol", "protocol"), ("extension", "editor extension"),
        ("vector_db", "vector database"), ("newsletter_tool", "newsletter service"), ("host", "hosting platform")]},
}

#: Derivation rules. Each name becomes a dimension; templates/crosses multiply.
DERIVE = [
    {"op": "cross", "name": "role_x_object", "title": "Role x object under observation", "a": "role", "b": "object_kind", "cap": 144},
    {"op": "cross", "name": "task_x_object", "title": "Task stem x object", "a": "task_stem", "b": "object_kind", "cap": 96},
    {"op": "cross", "name": "engine_x_channel", "title": "Search mechanism x demand channel", "a": "search_engine_kind", "b": "demand_channel", "cap": 64},
    {"op": "template", "name": "object_recency_search", "title": "Per-object recency search phrasings", "family": "object_kind", "kind": "qualifier",
     "bindings": {"time": "time_expr"},
     "patterns": ("top {v}", "best {v}", "{v} {time}", "new {v}", "{v} changelog", "{v} release notes")},
    {"op": "template", "name": "role_object_recommendation", "title": "Per-role recommendation phrasings", "family": "object_kind", "kind": "qualifier",
     "bindings": {"role": "role"},
     "patterns": ("{v} for a {role}", "best {v} for {role}", "should I switch {v} for {role}")},
    {"op": "cross", "name": "object_x_evidence", "title": "Object x evidence tier", "a": "object_kind", "b": "evidence_tier", "cap": 72},
]
