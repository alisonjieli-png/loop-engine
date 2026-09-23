"""Staging rows for outside candidates, in the existing candidate staging contract.

Each kept item becomes one row of candidate_intelligence_specifications/v2,
the version of the existing specification record that carries outside
provenance instead of paths inside this repository: the rendered text, the
list of provenance records (the kept source first, then every merged
duplicate), how the text was authored, the licence of the text, the
declared effects, the files of its package with their digests and the
reviewer notes of the triage engines. A row carries no lifecycle and no
approval: the staging tool forces the candidate lifecycle, and only an
independent review can approve exact bytes. Rows travel in populations of
at most fifty, the bound the staging tool accepts in one atomic batch.
"""
from __future__ import annotations

import re

from .record_rules import bytes_digest

SPECIFICATIONS_RECORD_TYPE = "candidate_intelligence_specifications/v2"
POPULATION_SIZE = 50
IMPORTED_VERBATIM = "imported_verbatim_under_permissive_licence"
GENERATED_FROM_FACTS = "generated_from_registry_facts"
AUTHORINGS = (IMPORTED_VERBATIM, GENERATED_FROM_FACTS)
FAMILIES = {"skill": "harness_skill", "instruction_file": "harness_instruction", "tool": "harness_connection"}
LAYERS = {"skill": "context", "instruction_file": "context", "tool": "code"}
_PREFIXES = {"skill": "skill", "instruction_file": "instr", "tool": "conn"}


def row_identity(kind: str, name: str, candidate_key: str) -> str:
    """Lower case letters, digits and underscores, at most 80 characters, unique by the key."""
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")[:48] or "item"
    return f"{_PREFIXES[kind]}_{slug}_{candidate_key[:12]}"


def package_files(package, roles: dict) -> list:
    return [{"path": path, "sha256": bytes_digest(data), "size_bytes": len(data),
             "role": roles.get(path, "native_file")} for path, data in package.files]


def specification_row(*, candidate: dict, package, provenance_records, effects, triage, tags,
                      license_expression: str, authoring: str, roles: dict) -> dict:
    kind = candidate["kind"]
    return {"id": row_identity(kind, candidate["name"], candidate["candidate_key"]), "layer": LAYERS[kind],
            "family": FAMILIES[kind], "title": package.title, "tags": list(tags),
            "text": package.main_text, "outside_provenance": list(provenance_records),
            "authoring": authoring, "license_expression": license_expression,
            "declared_effects": list(effects), "kind": kind,
            "package_files": package_files(package, roles), "triage": sorted(set(triage))}


def populations(rows) -> list:
    rows = list(rows)
    count = (len(rows) + POPULATION_SIZE - 1) // POPULATION_SIZE
    return [{"record_type": SPECIFICATIONS_RECORD_TYPE, "population": number, "populations": count,
             "specifications": rows[(number - 1) * POPULATION_SIZE:number * POPULATION_SIZE]}
            for number in range(1, count + 1)]
