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
├── step_functions  the kinds of step the item supports, from the closed vocabulary of the
│                   library_step_function_tagging engine slot (roadmap S-6.206)
├── component_form  what the component is, from the closed vocabulary component_form/v1: a
│                   function, a library module, a program, an API operation client, a binary
│                   install recipe, a protocol server, a plugin, a data table and the rest below
└── the five facets of the library_facet_tagging engine slot (roadmap S-6.209), each a keyword list
    from the declared vocabulary in data/library_facets.yaml
    ├── job_titles    the pinned occupation grid and the packaged occupation seeds
    ├── industries    a declared list of thirty-four
    ├── levels        student, junior, mid, senior, lead, executive
    ├── languages     english by default, else one of twelve found by script or stopwords
    └── geographies   countries and regions from a declared list
```

The owner, September 26, 2026: the library page must show "ALL types of
harness working directory component files not just SKILLS". The served item
kinds (skill, instruction_file, tool, reusable_code) fold twelve harness
kinds into four, so the pages count and filter by harness_kind instead. The
same day: "tag/label our harness component files by job title, industry,
level, language, geography, etc, and allow people to search in the dashboard
(when they sign up not on the home pages)". The signed-in table and the
search hits show the facets; the public pages read only harness_kind.

The owner, September 27, 2026: "We need to increase our goal to 100K library
components, and a diverse well balanced library, not overweighted with
skills.md, we should have more functions, tools, programs, binaries, plugins,
etc". The harness kind cannot say that: a function, a program and a data
table are all code modules to a harness, and clients depend on the twelve
kinds. The component form is a second, orthogonal choice attribute with its
own versioned vocabulary. Every package has exactly one form, taken from a
typed declaration when a supply line wrote one and otherwise derived from the
harness kind, the file roles and the native format, never from prose:

```text
component_form/v1, grouped by the composition family it counts toward
├── executable code          function, library_module, program, api_operation, binary_install
├── connectors and extensions  mcp_server, plugin, marketplace, hook
├── skills                   skill_with_scripts, skill
├── agents and commands      agent, command
├── instructions and rules   instructions, rules
└── data and contracts       data_table, schema, settings, evaluation_set
```

A declared form must be one the harness kind can carry (a data table is a
code module or a contract schema, never a skill), so a supply line cannot
file a skill under executable code.
"""
from __future__ import annotations

from ..library_ingestion.facet_tags import FACET_ATTRIBUTES, FACETS
from ..library_ingestion.step_functions import STEP_FUNCTIONS, STEP_FUNCTIONS_ATTRIBUTE

TIERS = ("verified", "community")
TIER_ATTRIBUTE = {"name": "tier", "type": "choice", "choices": list(TIERS), "searchable": False,
                  "filterable": True, "shown": True,
                  "description": "Verified: approved by independent reviewers of at least two model families. "
                                 "Community: automated checks and one independent review."}
#: Every kind of file a harness picks up, in the order the pages list them.
HARNESS_KINDS = ("skill", "instruction_file", "rules", "subagent", "command", "hook", "plugin_manifest",
                 "marketplace", "protocol_server_configuration", "harness_settings", "contract_schema", "code_module",
                 # The owner's September 29, 2026 direction: "images could be harness component files, masks could be
                 # harness component masks, 3D models, STL files, 3D files, autocode styles, etc, all of these could
                 # be reference files that a harness could analyze, understand". A harness reads these the way it
                 # reads a skill: it places the file, the harness interprets it, and the file is versioned bytes.
                 "reference_image", "mask", "pose_layout", "three_d_model", "cad_model", "template")
HARNESS_KIND_LABELS = {"skill": "Skill", "instruction_file": "Instruction file", "rules": "Rules",
                       "subagent": "Subagent", "command": "Command", "hook": "Hook",
                       "plugin_manifest": "Plugin manifest", "marketplace": "Plugin marketplace",
                       "protocol_server_configuration": "Protocol server configuration",
                       "harness_settings": "Harness settings", "contract_schema": "Contract schema",
                       "code_module": "Code module", "reference_image": "Reference image", "mask": "Mask",
                       "pose_layout": "Pose layout", "three_d_model": "3D model", "cad_model": "CAD model",
                       "template": "Template"}
#: What a harness is meant to do with a reference artifact. One PNG can be read for guidance, handed to a
#: generator as an input, opened as an editable source, or kept as the evidence a check compares against. Those
#: are four different uses of the same bytes, so the use is a declared field and not a guess from the file name.
ASSET_ROLES = ("reference", "generation_input", "editable_source", "test_evidence")
ASSET_ROLE_LABELS = {"reference": "Reference", "generation_input": "Generation input",
                     "editable_source": "Editable source", "test_evidence": "Test evidence"}
ASSET_ROLE_ATTRIBUTE = {"name": "asset_role", "type": "choice", "choices": list(ASSET_ROLES),
                        "searchable": True, "filterable": True, "shown": True,
                        "description": "What a harness does with this artifact: reads it for guidance, feeds it to a "
                                       "generator, opens it as an editable source, or compares against it as evidence."}
#: How a pose layout is drawn. A keypoint set is meaningless without its layout and its scale, and the common
#: mistake is to read a 25-keypoint body layout as an 18-keypoint face-and-hands layout.
POSE_LAYOUTS = ("coco18", "coco25", "openpose25", "face68", "hands21", "custom")
#: What a mask's painted pixels mean. Inverting this silently inverts every later operation, so it is declared.
MASK_POLARITIES = ("foreground", "background")
POSE_LAYOUT_ATTRIBUTE = {"name": "pose_layout", "type": "choice", "choices": list(POSE_LAYOUTS),
                         "searchable": False, "filterable": True, "shown": True,
                         "description": "The declared keypoint convention. Coordinates and scale require their own source record."}
MASK_POLARITY_ATTRIBUTE = {"name": "mask_polarity", "type": "choice", "choices": list(MASK_POLARITIES),
                           "searchable": False, "filterable": True, "shown": True,
                           "description": "Whether painted mask pixels select the foreground or background."}
#: The forms whose bytes a harness interprets rather than executes, and so carry the fields above.
INTERPRETED_FORMS = ("reference_image", "mask", "pose_layout")
ASSET_ROLE_FORMS = INTERPRETED_FORMS + ("three_d_model", "cad_model", "template", "code_example")
HARNESS_KIND_ATTRIBUTE = {"name": "harness_kind", "type": "choice", "choices": list(HARNESS_KINDS),
                          "searchable": True, "filterable": True, "shown": True,
                          "description": "The kind of file a harness picks up: a skill, an instruction file, rules, a "
                                         "subagent, a command, a hook, a plugin manifest, a plugin marketplace, a "
                                         "protocol server configuration, harness settings, a contract schema or a "
                                         "code module."}
#: The version of the component form vocabulary. A package records its form as a component_form/v1 record; a
#: reader of another version refuses it rather than guessing what an unknown form means.
COMPONENT_FORM_VERSION = "component_form/v1"
#: Every form a component can take, grouped by the composition family it counts toward (the families and their
#: target shares are data: src/loop_engine/data/library_composition.json).
COMPONENT_FORMS = ("function", "library_module", "program", "api_operation", "binary_install",
                   "mcp_server", "plugin", "marketplace", "hook",
                   "skill_with_scripts", "skill",
                   "agent", "command",
                   "instructions", "rules",
                   "data_table", "schema", "settings", "evaluation_set",
                   # A form is a role, not only a file type: the same PNG may be read as a reference, fed to a
                   # generator, or kept as the evidence a check compares against, and the three are different uses.
                   "reference_image", "mask", "pose_layout", "three_d_model", "cad_model", "template",
                   "code_example")
COMPONENT_FORM_LABELS = {"function": "Function", "library_module": "Library module", "program": "Program",
                         "api_operation": "API operation", "binary_install": "Binary install recipe",
                         "mcp_server": "Protocol server", "plugin": "Plugin", "marketplace": "Plugin marketplace",
                         "hook": "Hook", "skill_with_scripts": "Skill with scripts", "skill": "Skill",
                         "agent": "Agent", "command": "Command", "instructions": "Instructions", "rules": "Rules",
                         "data_table": "Data table", "schema": "Schema", "settings": "Settings",
                         "evaluation_set": "Evaluation set", "reference_image": "Reference image",
                         "mask": "Mask", "pose_layout": "Pose layout", "three_d_model": "3D model",
                         "cad_model": "CAD model", "template": "Template", "code_example": "Code example"}
#: The harness kinds each form may be served as. A declaration outside this table is refused.
COMPONENT_FORM_KINDS = {
    "function": ("code_module",), "library_module": ("code_module",), "program": ("code_module",),
    "api_operation": ("code_module",), "binary_install": ("code_module",),
    "mcp_server": ("protocol_server_configuration",), "plugin": ("plugin_manifest", "code_module"),
    "marketplace": ("marketplace",), "hook": ("hook",), "skill_with_scripts": ("skill",), "skill": ("skill",),
    "agent": ("subagent",), "command": ("command",), "instructions": ("instruction_file",), "rules": ("rules",),
    "data_table": ("code_module", "contract_schema"), "schema": ("contract_schema",),
    "settings": ("harness_settings",), "evaluation_set": ("code_module", "contract_schema"),
    "reference_image": ("reference_image",), "mask": ("mask",), "pose_layout": ("pose_layout",),
    "three_d_model": ("three_d_model",), "cad_model": ("cad_model",), "template": ("template",),
    "code_example": ("code_module",)}
#: The form of a package whose supply wrote none, by harness kind; a skill holding a script and a code module of
#: a known native format are refined below.
_KIND_FORMS = {"skill": "skill", "instruction_file": "instructions", "rules": "rules", "subagent": "agent",
               "command": "command", "hook": "hook", "plugin_manifest": "plugin", "marketplace": "marketplace",
               "protocol_server_configuration": "mcp_server", "harness_settings": "settings",
               "contract_schema": "schema", "code_module": "library_module",
               "reference_image": "reference_image", "mask": "mask", "pose_layout": "pose_layout",
               "three_d_model": "three_d_model", "cad_model": "cad_model", "template": "template"}
#: Native formats whose form is known from the format alone, by harness kind: the licensed import's OpenCode tools
#: are functions and its OpenCode plugin modules are plugins.
_FORMAT_FORMS = {"code_module": {"opencode_tool": "function", "opencode_plugin": "plugin"}}
#: The form of a package of this harness kind that holds a file a harness may run.
_SCRIPT_FORMS = {"skill": "skill_with_scripts"}
#: The harness kind of an item whose kind is unknown, as harness_kind_of falls back.
_FALLBACK_KIND = "code_module"
#: Package file roles a harness may run (catalogue_packages.EXECUTABLE_ROLES, restated so this module reads no
#: package code).
_RUNNABLE_ROLES = ("skill_script", "hook", "executable_tool")
#: How a package's form was decided.
FORM_DECLARED, FORM_DERIVED = "declared_by_supply_line", "derived_from_kind_roles_and_format"
FORM_BASES = (FORM_DECLARED, FORM_DERIVED)
COMPONENT_FORM_ATTRIBUTE = {"name": "component_form", "type": "choice", "choices": list(COMPONENT_FORMS),
                            "searchable": True, "filterable": True, "shown": True,
                            "description": "What the component is (vocabulary component_form/v1): a function, a "
                                           "library module, a program, an API operation, a binary install "
                                           "recipe, a protocol server, a plugin, a plugin marketplace, a hook, a "
                                           "skill with or without scripts, an agent, a command, instructions, "
                                           "rules, a data table, a schema, settings or an evaluation set."}
WELL_KNOWN_ATTRIBUTES = (TIER_ATTRIBUTE, HARNESS_KIND_ATTRIBUTE, STEP_FUNCTIONS_ATTRIBUTE, COMPONENT_FORM_ATTRIBUTE,
                         ASSET_ROLE_ATTRIBUTE, POSE_LAYOUT_ATTRIBUTE, MASK_POLARITY_ATTRIBUTE,
                         *FACET_ATTRIBUTES)
#: The served names, written out here so the serving side names what it serves and the documentation check
#: can hold a page to them; a declaration that drifts from this list is refused at import.
WELL_KNOWN_ATTRIBUTE_NAMES = ("tier", "harness_kind", "step_functions", "component_form",
                              "asset_role", "pose_layout", "mask_polarity", "job_titles",
                              "industries", "levels", "languages", "geographies")
if set(COMPONENT_FORMS) != set(COMPONENT_FORM_LABELS) or set(COMPONENT_FORMS) != set(COMPONENT_FORM_KINDS):
    raise ImportError("the component forms, their labels and their harness kinds disagree")
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


class ComponentFormError(ValueError):
    """A component form record or declaration that cannot be true, with a stable code."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code


def check_form(form: str, harness_kind: str) -> str:
    """The form, when it is known and the harness kind may carry it; otherwise refuse by name."""
    if form not in COMPONENT_FORMS:
        raise ComponentFormError("component_form_unknown", f"{form!r} is not one of {COMPONENT_FORM_VERSION}")
    if harness_kind not in HARNESS_KINDS:
        raise ComponentFormError("harness_kind_unknown", f"{harness_kind!r} is not a served harness kind")
    if harness_kind not in COMPONENT_FORM_KINDS[form]:
        raise ComponentFormError("component_form_kind_mismatch",
                                 f"a {form} is served as {' or '.join(COMPONENT_FORM_KINDS[form])}, not {harness_kind}")
    return form


def component_form_of(harness_kind: str, file_roles=(), native_format: str = "", declared: str = "") -> str:
    """The form of one package: its declaration when the harness kind may carry it, else derived by rule.

    A declared form the harness kind cannot carry is refused, never quietly replaced, because the declaration
    came from a supply line that must be corrected. An empty declaration derives the form from the harness kind,
    the file roles (a skill that holds a script) and the native format (an OpenCode tool is a function)."""
    if declared:
        return check_form(declared, harness_kind)
    kind = harness_kind if harness_kind in HARNESS_KINDS else _FALLBACK_KIND
    if kind in _SCRIPT_FORMS and any(role in _RUNNABLE_ROLES for role in file_roles or ()):
        return _SCRIPT_FORMS[kind]
    return _FORMAT_FORMS.get(kind, {}).get(native_format, _KIND_FORMS[kind])


def component_form_record(form: str, harness_kind: str, basis: str) -> dict:
    """The versioned record a package carries: its form and how it was decided."""
    if basis not in FORM_BASES:
        raise ComponentFormError("component_form_basis_unknown", f"a basis is one of {FORM_BASES}")
    return {"record_type": COMPONENT_FORM_VERSION, "form": check_form(form, harness_kind), "basis": basis}


def read_component_form(value, harness_kind: str) -> str:
    """The form a record names, or refuse another version, an unknown or missing field, or a mismatch."""
    if not isinstance(value, dict):
        raise ComponentFormError("component_form_record_invalid", "a component form record is an object")
    if value.get("record_type") != COMPONENT_FORM_VERSION:
        raise ComponentFormError("component_form_version_unsupported",
                                 f"expected {COMPONENT_FORM_VERSION}, found {value.get('record_type')!r}")
    if set(value) != {"record_type", "form", "basis"}:
        raise ComponentFormError("component_form_record_invalid", "the record names record_type, form and basis only")
    if value["basis"] not in FORM_BASES:
        raise ComponentFormError("component_form_basis_unknown", f"a basis is one of {FORM_BASES}")
    return check_form(value["form"], harness_kind)


def component_form_label(form: str) -> str:
    return COMPONENT_FORM_LABELS.get(form, form.replace("_", " ").capitalize())


def declare(schema: dict, *attributes: dict) -> dict:
    """The schema with each well-known attribute declared once, replacing an earlier declaration of the same name."""
    wanted = list(attributes) or list(WELL_KNOWN_ATTRIBUTES)
    names = {attribute["name"] for attribute in wanted}
    kept = [attribute for attribute in schema.get("attributes", []) if attribute["name"] not in names]
    return {**schema, "attributes": kept + [dict(attribute) for attribute in wanted]}


__all__ = ["TIERS", "TIER_ATTRIBUTE", "HARNESS_KINDS", "HARNESS_KIND_LABELS", "HARNESS_KIND_ATTRIBUTE",
           "STEP_FUNCTIONS", "STEP_FUNCTIONS_ATTRIBUTE", "FACETS", "FACET_ATTRIBUTES", "WELL_KNOWN_ATTRIBUTES",
           "WELL_KNOWN_ATTRIBUTE_NAMES", "COMPONENT_FORM_VERSION", "COMPONENT_FORMS", "COMPONENT_FORM_LABELS",
           "COMPONENT_FORM_KINDS", "COMPONENT_FORM_ATTRIBUTE", "FORM_BASES", "FORM_DECLARED", "FORM_DERIVED",
           "ComponentFormError", "check_form", "component_form_of", "component_form_record", "read_component_form",
           "component_form_label", "harness_kind_of", "harness_kind_label", "declare"]


def asset_role_problems(component_form: str, attributes: dict) -> list:
    """What a reference or creative artifact still has to declare before a harness can read it.

    A harness is handed these bytes and interprets them; nothing tells it how. Three mistakes are silent and
    each is refused here rather than corrected by the reader: an artifact with no declared role, a pose layout
    read with no layout named, and a mask whose polarity was never stated. The last is the expensive one, because
    an inverted mask inverts every selection made from it and the result still looks plausible.
    """
    problems: list = []
    declared = (attributes or {}).get("asset_role")
    if component_form in ASSET_ROLE_FORMS:
        if declared is None:
            problems.append("the artifact declares no asset_role")
        elif declared not in ASSET_ROLES:
            problems.append(f"the artifact declares the asset role {declared!r}")
    if component_form == "pose_layout":
        layout = (attributes or {}).get("pose_layout")
        if layout is None:
            problems.append("the pose layout names no layout, so its keypoints cannot be read")
        elif layout not in POSE_LAYOUTS:
            problems.append(f"the pose layout names the layout {layout!r}")
    if component_form == "mask":
        polarity = (attributes or {}).get("mask_polarity")
        if polarity is None:
            problems.append("the mask states no polarity, so its painted pixels are ambiguous")
        elif polarity not in MASK_POLARITIES:
            problems.append(f"the mask states the polarity {polarity!r}")
    return problems
