"""Select separate written criteria and panel engines for imported licensed packages (roadmap S-6.196)."""
from __future__ import annotations

import json
from pathlib import Path

from .configuration import PanelConfiguration, compile_criteria, load_instructions
from .imported_prechecks import CODE_ROUTES, REVIEWER_READS_CODE, SANDBOX_TESTS

RESOURCES = Path(__file__).resolve().parent / "resources"
IMPORTED_ENGINES = {kind: "imported_" + kind + "_rules" for kind in ("licence", "format", "safety", "effects")}
IMPORTED_ENGINES.update(secrets="imported_secret_rules", duplicates="imported_duplicate_rules")
#: The format engine of each code route (imported_prechecks): the reviewer reads code at Community, the
#: sandbox route is the earlier rule and the route to Verified for code.
FORMAT_ENGINES = {REVIEWER_READS_CODE: "imported_format_rules_code_read", SANDBOX_TESTS: "imported_format_rules"}


def resources():
    path = RESOURCES / "IMPORTED-PACKAGE-REVIEW.md"
    criteria = compile_criteria(json.loads((RESOURCES / "imported-criteria.json").read_text()), path.read_text())
    return criteria, load_instructions(RESOURCES / "IMPORTED-REVIEWER-INSTRUCTIONS.md")


def engine_map(code_route=REVIEWER_READS_CODE) -> dict:
    """The precheck engine of each kind under one code route."""
    if code_route not in CODE_ROUTES:
        raise ValueError(f"the code route is one of {CODE_ROUTES}: {code_route!r}")
    return {**IMPORTED_ENGINES, "format": FORMAT_ENGINES[code_route]}


def configuration(base, *, population_size=0, code_route=REVIEWER_READS_CODE):
    """Change only the content profile; preserve reviewer authority, quorum and budget policy."""
    engines = engine_map(code_route)
    value = base.to_dict()
    value["policy"]["prechecks"] = {kind: [engine] for kind, engine in engines.items()}
    value["precheck_engines"].update({engine: {} for engine in engines.values()})
    value["precheck_engines"]["imported_secret_rules"] = base.engine_settings("builtin_secret_patterns")
    value["precheck_engines"]["imported_duplicate_rules"] = base.engine_settings("exact_shingle_jaccard")
    if population_size > value["precheck_engines"]["imported_duplicate_rules"]["maximum_population"]:
        value["policy"]["prechecks"]["duplicates"] = ["imported_minhash_rules"]
        value["precheck_engines"]["imported_minhash_rules"] = base.engine_settings("datasketch_minhash_lsh")
    return PanelConfiguration.from_dict(value)


def engines(configuration):
    from .engines import build_precheck_engines
    return build_precheck_engines(configuration)
