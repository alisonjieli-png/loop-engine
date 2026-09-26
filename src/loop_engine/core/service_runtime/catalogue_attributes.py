"""The served attributes every reviewed catalogue declares, in one place, and the harness kind of an item.

An attribute is descriptive only (catalogue_schema): it grants nothing and no
code that decides access reads it. The three declared here travel from the
reviewed catalogue writer through the combined snapshot into the release
bundle, and the library pages and search filters read them from the served
view:

```text
Well-known served attributes
├── tier            Verified or Community, from the approval itself (decision table, "Library tiers")
├── harness_kind    which kind of file a harness picks up: skill, instruction_file, rules, subagent,
│                   command, hook, plugin_manifest, marketplace, protocol_server_configuration,
│                   harness_settings, contract_schema or code_module (the licensed import's vocabulary)
└── step_functions  the kinds of step the item supports, from the closed vocabulary of the
                    library_step_function_tagging engine slot (roadmap S-6.206)
```

The owner, September 26, 2026: the library page must show "ALL types of
harness working directory component files not just SKILLS". The served item
kinds (skill, instruction_file, tool, reusable_code) fold twelve harness
kinds into four, so the pages count and filter by harness_kind instead.
"""
from __future__ import annotations

from ..library_ingestion.step_functions import STEP_FUNCTIONS, STEP_FUNCTIONS_ATTRIBUTE

TIERS = ("verified", "community")
TIER_ATTRIBUTE = {"name": "tier", "type": "choice", "choices": list(TIERS), "searchable": False,
                  "filterable": True, "shown": True,
                  "description": "Verified: approved by independent reviewers of at least two model families. "
                                 "Community: automated checks and one independent review."}
#: Every kind of file a harness picks up, in the order the pages list them.
HARNESS_KINDS = ("skill", "instruction_file", "rules", "subagent", "command", "hook", "plugin_manifest",
                 "marketplace", "protocol_server_configuration", "harness_settings", "contract_schema", "code_module")
HARNESS_KIND_LABELS = {"skill": "Skill", "instruction_file": "Instruction file", "rules": "Rules",
                       "subagent": "Subagent", "command": "Command", "hook": "Hook",
                       "plugin_manifest": "Plugin manifest", "marketplace": "Plugin marketplace",
                       "protocol_server_configuration": "Protocol server configuration",
                       "harness_settings": "Harness settings", "contract_schema": "Contract schema",
                       "code_module": "Code module"}
HARNESS_KIND_ATTRIBUTE = {"name": "harness_kind", "type": "choice", "choices": list(HARNESS_KINDS),
                          "searchable": True, "filterable": True, "shown": True,
                          "description": "The kind of file a harness picks up: a skill, an instruction file, rules, a "
                                         "subagent, a command, a hook, a plugin manifest, a plugin marketplace, a "
                                         "protocol server configuration, harness settings, a contract schema or a "
                                         "code module."}
WELL_KNOWN_ATTRIBUTES = (TIER_ATTRIBUTE, HARNESS_KIND_ATTRIBUTE, STEP_FUNCTIONS_ATTRIBUTE)
#: The served names, written out here so the serving side names what it serves and the documentation check
#: can hold a page to them; a declaration that drifts from this list is refused at import.
WELL_KNOWN_ATTRIBUTE_NAMES = ("tier", "harness_kind", "step_functions")
if tuple(attribute["name"] for attribute in WELL_KNOWN_ATTRIBUTES) != WELL_KNOWN_ATTRIBUTE_NAMES:
    raise ImportError("the well-known attribute declarations and their names disagree")
#: The harness kind a package file role names, for an item whose provenance does not name one.
_ROLE_KINDS = {"skill_definition": "skill", "instruction_file": "instruction_file",
               "subagent_definition": "subagent", "command": "command", "hook": "hook",
               "plugin_manifest": "plugin_manifest", "protocol_server_configuration": "protocol_server_configuration",
               "executable_tool": "code_module", "configuration": "harness_settings"}
_ROLE_ORDER = ("skill_definition", "instruction_file", "subagent_definition", "command", "hook", "plugin_manifest",
               "protocol_server_configuration", "executable_tool", "configuration")
#: The harness kind of a one-file item of each served kind, when neither provenance nor a file role says more.
_ITEM_KINDS = {"skill": "skill", "instruction_file": "instruction_file", "tool": "code_module",
               "reusable_code": "code_module"}


def harness_kind_of(item_kind: str, styles=(), file_roles=(), declared: str = "") -> str:
    """The harness kind of one item: what its provenance declares, else its first style when that names a harness
    kind (the licensed import writes the package kind and its native format there), else its file roles, else
    the served kind's own. Always one of HARNESS_KINDS."""
    if declared in HARNESS_KINDS:
        return declared
    for style in styles or ():
        if style in HARNESS_KINDS:
            return style
    roles = set(file_roles or ())
    for role in _ROLE_ORDER:
        if role in roles:
            return _ROLE_KINDS[role]
    return _ITEM_KINDS.get(item_kind, "code_module")


def harness_kind_label(kind: str) -> str:
    return HARNESS_KIND_LABELS.get(kind, kind.replace("_", " ").capitalize())


def declare(schema: dict, *attributes: dict) -> dict:
    """The schema with each well-known attribute declared once, replacing an earlier declaration of the same name."""
    wanted = list(attributes) or list(WELL_KNOWN_ATTRIBUTES)
    names = {attribute["name"] for attribute in wanted}
    kept = [attribute for attribute in schema.get("attributes", []) if attribute["name"] not in names]
    return {**schema, "attributes": kept + [dict(attribute) for attribute in wanted]}


__all__ = ["TIERS", "TIER_ATTRIBUTE", "HARNESS_KINDS", "HARNESS_KIND_LABELS", "HARNESS_KIND_ATTRIBUTE",
           "STEP_FUNCTIONS", "STEP_FUNCTIONS_ATTRIBUTE", "WELL_KNOWN_ATTRIBUTES", "harness_kind_of",
           "harness_kind_label", "declare"]
