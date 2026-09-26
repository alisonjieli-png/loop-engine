"""The factory table of the library ingestion component: every slot and every engine class.

This is the only module that names concrete engine classes, and it defines
none. Each slot names its edge protocol, its closed engine kinds, whether
one engine is chosen or every eligible engine runs, and the declared order
(the initial choice first, then the fallbacks). Adding an engine is one
module, one row here and its checks; no neighbour changes. Selection itself
is in selection.py and grants no authority.
"""
from __future__ import annotations

from .format_builtin import AgentSkillsBuiltinRules
from .format_connection import ConnectionFileRules
from .format_json_schema import ConnectionSchemaValidator
from .format_skills_ref import AgentSkillsReferenceValidator
from .near_duplicate_builtin import BuiltinMinHashLsh
from .near_duplicate_datasketch import DatasketchMinHashLsh
from .outline_deterministic import DeterministicOutline
from .outline_model import ModelOutline
from .scan_builtin import BuiltinStaticRules
from .scan_skillspector import SkillSpectorStatic
from .selection import ONE_OF, SET_OF, EngineSlot
from .source_github import GitHubPinnedRepositoriesSource
from .source_mcp_registry import McpOfficialRegistrySource
from .step_functions import RulesStepFunctionTagger

SOURCE_SLOT = EngineSlot(
    "library_ingestion_source", "1.0.0", "read_candidates(declaration, library_candidate_request/v1) -> "
    "library_candidate_batch/v1", ("pinned_repository_reader", "registry_link_reader"), SET_OF,
    ("github_pinned_repositories", "mcp_official_registry"))
FORMAT_SLOT = EngineSlot(
    "library_format_validation", "1.0.0", "validate_skill(folder, text) or validate_package(document) -> "
    "problems", ("format_rules",), SET_OF,
    ("agent_skills_builtin_rules", "agent_skills_reference_validator", "connection_builtin_rules",
     "connection_schema_validator"))
SAFETY_SLOT = EngineSlot(
    "library_safety_scan", "1.0.0", "scan_packages(packages) -> findings by package", ("static_scanner",),
    SET_OF, ("builtin_static_rules", "skillspector_static"))
NEAR_DUPLICATE_SLOT = EngineSlot(
    "library_near_duplicate", "1.0.0", "pairs(shingle sets, threshold) -> similar pairs",
    ("near_duplicate_detector",), ONE_OF, ("datasketch_minhash_lsh", "builtin_minhash_lsh"))
OUTLINE_SLOT = EngineSlot(
    "library_outline", "1.0.0", "outline(candidate, source text) -> library_candidate_outline/v1",
    ("outline_writer",), ONE_OF, ("model_outline", "deterministic_outline"))
STEP_FUNCTION_SLOT = EngineSlot(
    "library_step_function_tagging", "1.0.0", "tag(step_function_material/v1) -> step_function_tags/v1",
    ("function_tagger",), ONE_OF, ("step_function_rules",))

SLOTS = (SOURCE_SLOT, FORMAT_SLOT, SAFETY_SLOT, NEAR_DUPLICATE_SLOT, OUTLINE_SLOT, STEP_FUNCTION_SLOT)
FACTORIES = {
    SOURCE_SLOT.slot_id: {"github_pinned_repositories": GitHubPinnedRepositoriesSource,
                          "mcp_official_registry": McpOfficialRegistrySource},
    FORMAT_SLOT.slot_id: {"agent_skills_builtin_rules": AgentSkillsBuiltinRules,
                          "agent_skills_reference_validator": AgentSkillsReferenceValidator,
                          "connection_builtin_rules": ConnectionFileRules,
                          "connection_schema_validator": ConnectionSchemaValidator},
    SAFETY_SLOT.slot_id: {"builtin_static_rules": BuiltinStaticRules,
                          "skillspector_static": SkillSpectorStatic},
    NEAR_DUPLICATE_SLOT.slot_id: {"datasketch_minhash_lsh": DatasketchMinHashLsh,
                                  "builtin_minhash_lsh": BuiltinMinHashLsh},
    OUTLINE_SLOT.slot_id: {"model_outline": ModelOutline, "deterministic_outline": DeterministicOutline},
    STEP_FUNCTION_SLOT.slot_id: {"step_function_rules": RulesStepFunctionTagger},
}
