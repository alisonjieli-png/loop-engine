"""Select separate written criteria and existing panel engines for original native packages."""
from __future__ import annotations

import json
from pathlib import Path

from .configuration import PanelConfiguration, compile_criteria, load_instructions

RESOURCES = Path(__file__).resolve().parent / "resources"
NATIVE_ENGINES = {kind: "native_" + kind + "_rules" for kind in
                  ("licence", "format", "safety", "effects", "secrets", "duplicates")}
NATIVE_ENGINES.update(secrets="native_secret_rules", duplicates="native_duplicate_rules")


def resources():
    path = RESOURCES / "NATIVE-PACKAGE-REVIEW.md"
    criteria = compile_criteria(json.loads((RESOURCES / "native-criteria.json").read_text()), path.read_text())
    return criteria, load_instructions(RESOURCES / "NATIVE-REVIEWER-INSTRUCTIONS.md")


def configuration(base, *, population_size=0):
    """Change only the content profile; preserve reviewer authority, quorum and budget policy."""
    value = base.to_dict()
    value["policy"]["prechecks"] = {kind: [engine] for kind, engine in NATIVE_ENGINES.items()}
    value["precheck_engines"].update({engine: {} for engine in NATIVE_ENGINES.values()})
    value["precheck_engines"]["native_secret_rules"] = base.engine_settings("builtin_secret_patterns")
    value["precheck_engines"]["native_duplicate_rules"] = base.engine_settings("exact_shingle_jaccard")
    if population_size > value["precheck_engines"]["native_duplicate_rules"]["maximum_population"]:
        value["policy"]["prechecks"]["duplicates"] = ["native_minhash_rules"]
        value["precheck_engines"]["native_minhash_rules"] = base.engine_settings("datasketch_minhash_lsh")
    return PanelConfiguration.from_dict(value)


def engines(configuration):
    from .engines import build_precheck_engines
    return build_precheck_engines(configuration)
