"""Select separate written criteria and panel engines for imported licensed packages (roadmap S-6.196)."""
from __future__ import annotations

import json
from pathlib import Path

from .configuration import PanelConfiguration, compile_criteria, load_instructions

RESOURCES = Path(__file__).resolve().parent / "resources"
IMPORTED_ENGINES = {kind: "imported_" + kind + "_rules" for kind in ("licence", "format", "safety", "effects")}
IMPORTED_ENGINES.update(secrets="imported_secret_rules", duplicates="imported_duplicate_rules")


def resources():
    path = RESOURCES / "IMPORTED-PACKAGE-REVIEW.md"
    criteria = compile_criteria(json.loads((RESOURCES / "imported-criteria.json").read_text()), path.read_text())
    return criteria, load_instructions(RESOURCES / "IMPORTED-REVIEWER-INSTRUCTIONS.md")


def configuration(base, *, population_size=0):
    """Change only the content profile; preserve reviewer authority, quorum and budget policy."""
    value = base.to_dict()
    value["policy"]["prechecks"] = {kind: [engine] for kind, engine in IMPORTED_ENGINES.items()}
    value["precheck_engines"].update({engine: {} for engine in IMPORTED_ENGINES.values()})
    value["precheck_engines"]["imported_secret_rules"] = base.engine_settings("builtin_secret_patterns")
    value["precheck_engines"]["imported_duplicate_rules"] = base.engine_settings("exact_shingle_jaccard")
    if population_size > value["precheck_engines"]["imported_duplicate_rules"]["maximum_population"]:
        value["policy"]["prechecks"]["duplicates"] = ["imported_minhash_rules"]
        value["precheck_engines"]["imported_minhash_rules"] = base.engine_settings("datasketch_minhash_lsh")
    return PanelConfiguration.from_dict(value)


def engines(configuration):
    from .engines import build_precheck_engines
    return build_precheck_engines(configuration)
