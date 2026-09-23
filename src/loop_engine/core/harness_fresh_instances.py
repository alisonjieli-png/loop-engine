"""Fresh instance recipes: one harness started for one step with only its material.

Owns: the typed ``harness_fresh_instance_recipe/v1`` records of the release
recipe catalogue, the configuration files each recipe writes, the rendering of
a recipe's environment and command for one step layout, the decoy files an
offline loading check plants, and the assessment of one loading observation
(roadmap S-6.42: the September 22 isolation test, made repeatable). A recipe
starts the customer's own harness with an empty home folder and the harness's
own configuration folder, so the harness reads only the step's instruction
file, skills and protocol servers.
Does not own: starting processes, the capture endpoint or the network sandbox
(``tools/check_harness_fresh_instances.py`` does that), model authority, or
qualification. An observation proves loading at one installed version; it
never proves use by a model, and on its own it never makes a harness
supported for one harness per step.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import PurePosixPath
import re

FRESH_INSTANCE_RECORD_TYPE = "harness_fresh_instance_recipe/v1"
FRESH_INSTANCE_RESULT_RECORD_TYPE = "harness_fresh_instance_result/v1"
#: One run of the offline loading check over every recipe.
FRESH_INSTANCE_RUN_RECORD_TYPE = "harness_fresh_instance_run/v1"

#: A clean environment, an empty home folder, the harness's own configuration
#: folder and the step folder as its own git root: the customer-side launch.
LAUNCH_MODES = ("customer_process",)
MATERIAL_KINDS = ("instruction_file", "skills", "protocol_servers")
MATERIAL_STATES = ("loaded", "not_supported", "not_proven")
SUPPORT_CLAIMS = ("none", "material_loading")
#: What a recipe writes for one step; a closed list, each a function below.
CONFIGURATION_WRITERS = ("codex_configuration_toml", "opencode_configuration",
                         "claude_code_bare_configuration", "claude_code_configuration_folder",
                         "pi_models_json", "none")
INSTRUCTION_BODIES = ("step_instructions", "import_standard_file")
#: The only names a recipe template may contain, written as ``{name}``.
TEMPLATE_FIELDS = ("empty_home", "configuration_folder", "step_folder", "step_parent",
                   "step_skill", "model_origin", "model_base_url", "model_name",
                   "model_credential", "probe_prompt")
#: The ladder rungs an offline loading check can reach (roadmap S-6.31). The
#: last two need a model and are never reached here.
LOADING_RUNGS = ("none", "connected", "material_listed", "material_loaded")
#: The variable a recipe's configuration names for the step's model credential.
#: The credential reaches a harness only as a variable of its own process: no
#: writer puts it in a file and no command line carries it (roadmap S-6.61).
MODEL_CREDENTIAL_VARIABLE = "BALTOR_STEP_MODEL_CREDENTIAL"
#: The skill folder name the step material uses.
STEP_SKILL_NAME = "baltor-step-skill"
#: Decoy files by name; a global location must be one of these kinds.
DECOY_KINDS = ("AGENTS.md", "CLAUDE.md", "SKILL.md", "config.toml", "opencode.json", ".claude.json")
#: A recipe's upstream is a public repository address.
UPSTREAM_PREFIX = "https://github.com/"
#: A step's model endpoint is always a loopback origin.
LOOPBACK_ORIGIN_PREFIX = "http://127.0.0.1:"

_IDENTIFIER = re.compile(r"[a-z][a-z0-9_.-]{0,95}")
_VARIABLE = re.compile(r"[A-Z][A-Z0-9_]{0,63}")
_VERSION = re.compile(r"[A-Za-z0-9][A-Za-z0-9.+_-]{0,95}")
_REVISION = re.compile(r"[0-9a-f]{40}")
_PLACEHOLDER = re.compile(r"\{([a-z_]+)\}")
_RELATIVE = re.compile(r"[A-Za-z0-9._-][A-Za-z0-9._/-]{0,159}")


class FreshInstanceRecipeError(ValueError):
    """A fresh instance recipe, layout or observation that this release refuses."""


def _exact_keys(value, keys, name):
    if type(value) is not dict or set(value) != set(keys):
        raise FreshInstanceRecipeError(f"{name} must hold exactly the fields {sorted(keys)}")


def _text(value, pattern, name, *, optional=False):
    if value is None and optional:
        return None
    if type(value) is not str or not pattern.fullmatch(value):
        raise FreshInstanceRecipeError(f"{name} is not a valid value")
    return value


def _template(value, name):
    if type(value) is not str or "\x00" in value or len(value) > 512:
        raise FreshInstanceRecipeError(f"{name} must be bounded text")
    unknown = [field for field in _PLACEHOLDER.findall(value) if field not in TEMPLATE_FIELDS]
    if unknown or "{" in _PLACEHOLDER.sub("", value) or "}" in _PLACEHOLDER.sub("", value):
        raise FreshInstanceRecipeError(f"{name} names a template field outside {TEMPLATE_FIELDS}")
    return value


def _relative(value, name):
    path = PurePosixPath(_text(value, _RELATIVE, name))
    if path.is_absolute() or ".." in path.parts:
        raise FreshInstanceRecipeError(f"{name} must stay inside its folder")
    return value


def _string_list(value, name, check):
    if type(value) is not list:
        raise FreshInstanceRecipeError(f"{name} must be a list")
    items = tuple(check(item, name) for item in value)
    if len(set(items)) != len(items):
        raise FreshInstanceRecipeError(f"{name} repeats an entry")
    return items


def _template_list(value, name):
    """A command line: an ordered list of templates, where a flag may repeat."""
    if type(value) is not list:
        raise FreshInstanceRecipeError(f"{name} must be a list")
    return tuple(_template(item, name) for item in value)


def _credential_rule(command_templates):
    """A credential never reaches a command line, where every process can read it."""
    if any("{model_credential}" in item for item in command_templates):
        raise FreshInstanceRecipeError("the model credential reaches a harness only through its environment")


def _empty_home_rule(environment):
    """The September 22 finding as a rule: the configuration variable alone
    leaked the home folder's skills for Codex, OpenCode and Pi."""
    if environment.get("HOME") != "{empty_home}":
        raise FreshInstanceRecipeError("a fresh instance starts with HOME set to the empty home folder")


@dataclass(frozen=True)
class RecipeSource:
    """Where the harness comes from: its upstream, pinned revision and licence."""

    upstream: str
    revision: str | None
    licence: str

    def __post_init__(self):
        if type(self.upstream) is not str or not self.upstream.startswith(UPSTREAM_PREFIX):
            raise FreshInstanceRecipeError("the upstream must be a public repository address")
        _text(self.revision, _REVISION, "source revision", optional=True)
        _text(self.licence, re.compile(r"[A-Za-z0-9][A-Za-z0-9.+-]{0,63}"), "licence")

    def to_dict(self):
        return {"upstream": self.upstream, "revision": self.revision, "licence": self.licence}


@dataclass(frozen=True)
class FreshInstanceRecipe:
    """How one harness program starts fresh for one step, and what is proven.

    ``environment`` and ``arguments`` are templates over ``TEMPLATE_FIELDS``.
    A recipe that is not a candidate sets ``HOME`` to the empty home folder
    and its ``configuration_variable`` to the step's configuration folder:
    the September 22 test found that the documented configuration variable
    alone still let three of four harnesses read skills from the home folder."""

    recipe_id: str
    harness: str
    launch_mode: str
    order: int
    candidate: bool
    source: RecipeSource
    executable: str
    version_arguments: tuple
    version_pattern: str | None
    pinned_version: str | None
    configuration_variable: str | None
    environment: tuple
    arguments: tuple
    instruction_files: tuple
    skills_directory: str | None
    configuration_writer: str
    global_locations: tuple
    bundled_items: tuple
    material: tuple
    support_claim: str
    evidence: tuple

    FIELDS = ("record_type", "recipe_id", "harness", "launch_mode", "order", "candidate",
              "source", "executable", "version_arguments", "version_pattern", "pinned_version",
              "configuration_variable", "environment", "arguments", "instruction_files",
              "skills_directory", "configuration_writer", "global_locations", "bundled_items",
              "material", "support_claim", "evidence")

    def __post_init__(self):
        _text(self.recipe_id, _IDENTIFIER, "recipe_id")
        _text(self.harness, _IDENTIFIER, "harness")
        if not self.recipe_id.startswith(self.harness + "."):
            raise FreshInstanceRecipeError("a recipe identifier starts with its harness name")
        if self.launch_mode not in LAUNCH_MODES:
            raise FreshInstanceRecipeError(f"launch_mode must be one of {LAUNCH_MODES}")
        if type(self.order) is not int or not 1 <= self.order <= 9:
            raise FreshInstanceRecipeError("order is a preference from 1 to 9")
        if type(self.candidate) is not bool or not isinstance(self.source, RecipeSource):
            raise FreshInstanceRecipeError("candidate is a Boolean and source a typed record")
        _text(self.executable, re.compile(r"[a-z][a-z0-9_.-]{0,63}"), "executable")
        if self.version_pattern is not None or not self.candidate:
            try:
                pattern = re.compile(self.version_pattern)
            except (re.error, TypeError) as exc:
                raise FreshInstanceRecipeError("version_pattern must be a regular expression") from exc
            if pattern.groups != 1:
                raise FreshInstanceRecipeError("version_pattern captures exactly one version")
        _text(self.pinned_version, _VERSION, "pinned_version", optional=True)
        _text(self.configuration_variable, _VARIABLE, "configuration_variable", optional=True)
        if self.configuration_writer not in CONFIGURATION_WRITERS:
            raise FreshInstanceRecipeError(f"configuration_writer must be one of {CONFIGURATION_WRITERS}")
        if dict(self.material).keys() != set(MATERIAL_KINDS) or any(
                state not in MATERIAL_STATES for _, state in self.material):
            raise FreshInstanceRecipeError("material names every kind with a known state")
        if self.support_claim not in SUPPORT_CLAIMS:
            raise FreshInstanceRecipeError(f"support_claim must be one of {SUPPORT_CLAIMS}")
        states = dict(self.material)
        if self.candidate:
            if self.support_claim != "none" or set(states.values()) != {"not_proven"}:
                raise FreshInstanceRecipeError("a candidate recipe makes no support claim")
        else:
            self._check_launch_rules()
        if (self.support_claim == "none") == ("loaded" in states.values()):
            raise FreshInstanceRecipeError("loaded material and a material loading claim come together")
        if self.support_claim != "none" and not self.evidence:
            raise FreshInstanceRecipeError("a support claim names its evidence")
        if self.skills_directory is None and states["skills"] == "loaded":
            raise FreshInstanceRecipeError("skills load only from a declared skills folder")
        for location in self.global_locations:
            if PurePosixPath(location).name not in DECOY_KINDS:
                raise FreshInstanceRecipeError(f"{location} has no decoy kind; use one of {DECOY_KINDS}")
        if len({name for name, _ in self.instruction_files}) != len(self.instruction_files):
            raise FreshInstanceRecipeError("an instruction file is named twice")
        templates = [value for _, value in self.environment] + list(self.arguments)
        if self.skills_directory is None and any("{step_skill}" in value for value in templates):
            raise FreshInstanceRecipeError("a recipe that names the step skill declares a skills folder")
        _credential_rule(self.arguments + self.version_arguments)

    def _check_launch_rules(self):
        environment = dict(self.environment)
        _empty_home_rule(environment)
        if (self.configuration_variable is None
                or not environment.get(self.configuration_variable, "").startswith("{configuration_folder}")):
            raise FreshInstanceRecipeError("a fresh instance sets its own configuration folder variable")
        if self.pinned_version is None or not self.arguments or not self.version_arguments:
            raise FreshInstanceRecipeError("a recipe that is not a candidate pins a version and a command")
        if not self.instruction_files or self.instruction_files[0] != ("AGENTS.md", "step_instructions"):
            raise FreshInstanceRecipeError("the step's AGENTS.md is the first instruction file")

    def to_dict(self) -> dict:
        return {"record_type": FRESH_INSTANCE_RECORD_TYPE, "recipe_id": self.recipe_id,
                "harness": self.harness, "launch_mode": self.launch_mode, "order": self.order,
                "candidate": self.candidate, "source": self.source.to_dict(),
                "executable": self.executable, "version_arguments": list(self.version_arguments),
                "version_pattern": self.version_pattern, "pinned_version": self.pinned_version,
                "configuration_variable": self.configuration_variable,
                "environment": dict(self.environment), "arguments": list(self.arguments),
                "instruction_files": [{"name": name, "body": body}
                                      for name, body in self.instruction_files],
                "skills_directory": self.skills_directory,
                "configuration_writer": self.configuration_writer,
                "global_locations": list(self.global_locations),
                "bundled_items": list(self.bundled_items), "material": dict(self.material),
                "support_claim": self.support_claim, "evidence": list(self.evidence)}

    @property
    def digest(self) -> str:
        serialized = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"),
                                ensure_ascii=False, allow_nan=False)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @classmethod
    def from_dict(cls, value) -> "FreshInstanceRecipe":
        if type(value) is not dict or value.get("record_type") != FRESH_INSTANCE_RECORD_TYPE:
            raise FreshInstanceRecipeError(f"a fresh instance recipe must be {FRESH_INSTANCE_RECORD_TYPE}")
        _exact_keys(value, cls.FIELDS, "a fresh instance recipe")
        _exact_keys(value["source"], ("upstream", "revision", "licence"), "source")
        if type(value["environment"]) is not dict or type(value["material"]) is not dict:
            raise FreshInstanceRecipeError("environment and material must be mappings")
        environment = tuple((_text(name, _VARIABLE, "variable name"),
                             _template(item, "variable value"))
                            for name, item in value["environment"].items())
        files = []
        for item in value["instruction_files"] if type(value["instruction_files"]) is list else [None]:
            _exact_keys(item, ("name", "body"), "instruction file")
            if item["body"] not in INSTRUCTION_BODIES:
                raise FreshInstanceRecipeError(f"an instruction body is one of {INSTRUCTION_BODIES}")
            files.append((_relative(item["name"], "instruction file name"), item["body"]))
        return cls(
            value["recipe_id"], value["harness"], value["launch_mode"], value["order"],
            value["candidate"], RecipeSource(**value["source"]), value["executable"],
            _template_list(value["version_arguments"], "version_arguments"),
            value["version_pattern"], value["pinned_version"], value["configuration_variable"],
            environment, _template_list(value["arguments"], "arguments"), tuple(files),
            None if value["skills_directory"] is None else _relative(
                value["skills_directory"], "skills_directory"),
            value["configuration_writer"],
            _string_list(value["global_locations"], "global_locations", _relative),
            _string_list(value["bundled_items"], "bundled_items",
                         lambda item, name: _text(item, re.compile(r"[a-z][a-z0-9_.-]{0,63}"), name)),
            tuple(sorted(value["material"].items())), value["support_claim"],
            _string_list(value["evidence"], "evidence", _relative))


@dataclass(frozen=True)
class FreshInstanceLayout:
    """The folders and model endpoint of one step's fresh instance.

    Every folder is absolute; the step folder sits directly in its parent.
    The model endpoint is a loopback address: a customer launcher supplies the
    customer's own model there, and the offline check supplies an endpoint
    that records the request and answers no model. The two capacities bound
    what a harness declares for its model; the check's endpoint answers none."""

    empty_home: str
    configuration_folder: str
    step_folder: str
    step_parent: str
    model_origin: str
    model_name: str
    model_credential: str
    probe_prompt: str
    protocol_server_name: str
    protocol_server_command: tuple
    model_context_capacity: int
    model_output_capacity: int

    def __post_init__(self):
        for name in ("empty_home", "configuration_folder", "step_folder", "step_parent"):
            path = PurePosixPath(getattr(self, name))
            if not path.is_absolute() or ".." in path.parts:
                raise FreshInstanceRecipeError(f"{name} must be an absolute folder")
        if PurePosixPath(self.step_folder).parent != PurePosixPath(self.step_parent):
            raise FreshInstanceRecipeError("the step folder sits directly in its parent")
        origin = self.model_origin
        if (type(origin) is not str or not origin.startswith(LOOPBACK_ORIGIN_PREFIX)
                or not origin[len(LOOPBACK_ORIGIN_PREFIX):].isdigit()):
            raise FreshInstanceRecipeError("the model endpoint must be a loopback origin")
        for name in ("model_name", "model_credential", "probe_prompt"):
            value = getattr(self, name)
            if type(value) is not str or not value or any(ch in value for ch in "\x00\r\n{}"):
                raise FreshInstanceRecipeError(f"{name} must be one line of text")
        _text(self.protocol_server_name, re.compile(r"[a-z][a-z0-9_]{0,63}"), "protocol server name")
        command = self.protocol_server_command
        if (type(command) is not tuple or not command
                or any(type(part) is not str or not part or "\x00" in part for part in command)
                or not PurePosixPath(command[0]).is_absolute()):
            raise FreshInstanceRecipeError("the protocol server command is an absolute program and its arguments")
        for name in ("model_context_capacity", "model_output_capacity"):
            if type(getattr(self, name)) is not int or getattr(self, name) < 1:
                raise FreshInstanceRecipeError(f"{name} must be a positive integer")


def template_values(recipe: FreshInstanceRecipe, layout: FreshInstanceLayout) -> dict:
    skill = ""
    if recipe.skills_directory is not None:
        skill = str(PurePosixPath(layout.step_folder) / recipe.skills_directory / STEP_SKILL_NAME)
    return {"empty_home": layout.empty_home, "configuration_folder": layout.configuration_folder,
            "step_folder": layout.step_folder, "step_parent": layout.step_parent,
            "step_skill": skill, "model_origin": layout.model_origin,
            "model_base_url": layout.model_origin + "/v1", "model_name": layout.model_name,
            "model_credential": layout.model_credential, "probe_prompt": layout.probe_prompt}


def render(template: str, values: dict) -> str:
    """Replace every ``{field}`` of a checked template; nothing else changes."""
    return _PLACEHOLDER.sub(lambda match: values[match.group(1)], _template(template, "template"))


def render_launch(recipe: FreshInstanceRecipe, layout: FreshInstanceLayout):
    """The rendered command arguments (after the executable) and environment."""
    if recipe.candidate:
        raise FreshInstanceRecipeError("a candidate recipe is listed for study and never launched")
    values = template_values(recipe, layout)
    return (tuple(render(item, values) for item in recipe.arguments),
            {name: render(item, values) for name, item in recipe.environment})


def _json_text(value) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"


def _toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _server_entry(layout):
    return layout.protocol_server_command[0], list(layout.protocol_server_command[1:])


def _codex_files(layout):
    command, arguments = _server_entry(layout)
    lines = [
        f"model = {_toml_string(layout.model_name)}", 'model_provider = "step_model"',
        'approval_policy = "never"', 'sandbox_mode = "read-only"',
        "check_for_update_on_startup = false",
        "[model_providers.step_model]", 'name = "Step model endpoint"',
        f"base_url = {_toml_string(layout.model_origin + '/v1')}", 'wire_api = "responses"',
        f'env_key = "{MODEL_CREDENTIAL_VARIABLE}"',
        "request_max_retries = 0", "stream_max_retries = 0",
        f"[mcp_servers.{layout.protocol_server_name}]", f"command = {_toml_string(command)}",
        "args = [" + ", ".join(_toml_string(item) for item in arguments) + "]",
        "[skills.bundled]", "enabled = false", "[analytics]", "enabled = false"]
    return ((f"{layout.configuration_folder}/config.toml", "\n".join(lines) + "\n"),)


def _opencode_files(layout):
    command, arguments = _server_entry(layout)
    model = {"autoupdate": False, "share": "disabled", "model": "step_model/" + layout.model_name,
             "provider": {"step_model": {
                 "npm": "@ai-sdk/openai-compatible", "name": "Step model endpoint",
                 "options": {"baseURL": layout.model_origin + "/v1",
                             "apiKey": "{env:" + MODEL_CREDENTIAL_VARIABLE + "}"},
                 "models": {layout.model_name: {"name": layout.model_name, "limit": {
                     "context": layout.model_context_capacity,
                     "output": layout.model_output_capacity}}}}}}
    project = {"mcp": {layout.protocol_server_name: {
        "type": "local", "command": [command, *arguments], "enabled": True}}}
    return ((f"{layout.configuration_folder}/model.json", _json_text(model)),
            (f"{layout.step_folder}/opencode.json", _json_text(project)))


def _claude_server_file(layout):
    command, arguments = _server_entry(layout)
    return (f"{layout.configuration_folder}/mcp.json", _json_text({"mcpServers": {
        layout.protocol_server_name: {"type": "stdio", "command": command, "args": arguments}}}))


def _claude_bare_files(layout):
    return (_claude_server_file(layout),)


#: Instruction files Claude Code reads from each folder above the start folder.
CLAUDE_CODE_ANCESTOR_FILES = ("CLAUDE.md", "CLAUDE.local.md", ".claude/CLAUDE.md", "AGENTS.md")


def _claude_configuration_folder_files(layout):
    """Exclude the instruction files of every folder above the step.

    The offline check of September 22 found that excluding only the parent's
    files still let the home folder's ``.claude/CLAUDE.md`` in whenever the
    step folder sits below the home folder, because Claude Code reads that
    file as a project file of an ancestor folder."""
    excluded = []
    folder = PurePosixPath(layout.step_parent)
    while True:
        excluded += [str(folder / name) for name in CLAUDE_CODE_ANCESTOR_FILES]
        if folder == folder.parent:
            break
        folder = folder.parent
    return (_claude_server_file(layout),
            (f"{layout.configuration_folder}/step-settings.json",
             _json_text({"claudeMdExcludes": excluded})))


def _pi_files(layout):
    models = {"providers": {"step_model": {
        "baseUrl": layout.model_origin + "/v1", "api": "openai-completions",
        "apiKey": MODEL_CREDENTIAL_VARIABLE,
        "models": [{"id": layout.model_name, "name": layout.model_name, "reasoning": False,
                    "input": ["text"], "contextWindow": layout.model_context_capacity,
                    "maxTokens": layout.model_output_capacity}]}}}
    return ((f"{layout.configuration_folder}/models.json", _json_text(models)),)


#: The one table that names each writer; a recipe chooses a writer by name.
_WRITERS = {
    "codex_configuration_toml": _codex_files, "opencode_configuration": _opencode_files,
    "claude_code_bare_configuration": _claude_bare_files,
    "claude_code_configuration_folder": _claude_configuration_folder_files,
    "pi_models_json": _pi_files, "none": lambda layout: (),
}


def configuration_files(recipe: FreshInstanceRecipe, layout: FreshInstanceLayout) -> tuple:
    """(absolute path, text) for each configuration file the recipe writes."""
    return _WRITERS[recipe.configuration_writer](layout)


def step_material_files(recipe, layout, *, instructions: str, skill_description: str) -> tuple:
    """(absolute path, text) for the step's instruction files and skill."""
    files = []
    for name, body in recipe.instruction_files:
        text = instructions if body == "step_instructions" else "@AGENTS.md\n"
        files.append((f"{layout.step_folder}/{name}", text))
    if recipe.skills_directory is not None:
        files.append((f"{layout.step_folder}/{recipe.skills_directory}/{STEP_SKILL_NAME}/SKILL.md",
                      f"---\nname: {STEP_SKILL_NAME}\ndescription: {skill_description}\n---\n\n"
                      f"{skill_description}\n"))
    return tuple(files)


def decoy_files(recipe, home: str, marker: str, server_command: tuple) -> tuple:
    """A decoy at every global location the recipe's harness documents reading.

    A decoy marker in a captured request, or a started decoy server, means the
    instance read material that was not the step's."""
    return tuple((str(PurePosixPath(home) / location),
                  _DECOY_WRITERS[PurePosixPath(location).name](PurePosixPath(location), marker, server_command))
                 for location in recipe.global_locations)


def _instruction_decoy(path, marker, server_command):
    return f"# Global instructions\n\n{marker}\n"


def _skill_decoy(path, marker, server_command):
    return f"---\nname: {path.parent.name}\ndescription: {marker}\n---\n\n{marker}\n"


def _codex_server_decoy(path, marker, server_command):
    return ("[mcp_servers.decoy_global]\n" f"command = {_toml_string(server_command[0])}\n"
            "args = [" + ", ".join(_toml_string(item) for item in server_command[1:]) + "]\n")


def _opencode_server_decoy(path, marker, server_command):
    return _json_text({"mcp": {"decoy_global": {"type": "local", "enabled": True,
                                                "command": list(server_command)}}})


def _claude_server_decoy(path, marker, server_command):
    return _json_text({"mcpServers": {"decoy_global": {
        "type": "stdio", "command": server_command[0], "args": list(server_command[1:])}}})


#: One decoy writer for each decoy kind, in the order of ``DECOY_KINDS``.
_DECOY_WRITERS = dict(zip(DECOY_KINDS, (
    _instruction_decoy, _instruction_decoy, _skill_decoy, _codex_server_decoy,
    _opencode_server_decoy, _claude_server_decoy)))


@dataclass(frozen=True)
class FreshInstanceObservation:
    """What one offline launch showed: the requests the harness sent to the
    loopback endpoint, the protocol server events, the exit and the version.

    ``step_markers`` maps each material kind to the marker placed only in the
    step's material; ``decoy_markers`` are the markers placed everywhere else."""

    recipe_id: str
    installed_version: str | None
    requests: tuple
    protocol_events: tuple
    exit_code: int | None
    timed_out: bool
    step_markers: tuple
    decoy_markers: tuple


def _decoys_found(markers, text, events) -> list:
    """Every decoy marker that reached a request or started a protocol server."""
    return sorted(marker for marker in markers
                  if marker and (marker in text or any(marker in event for event in events)))


def assess_observation(recipe: FreshInstanceRecipe, observation: FreshInstanceObservation) -> dict:
    """Decide what one launch proved, as ``harness_fresh_instance_result/v1``.

    Loading is counted only from a marker inside a request the harness sent.
    A clean exit, a session identifier, a listed tool or a file on disk never
    counts as loaded, and any decoy marker fails the launch."""
    if observation.recipe_id != recipe.recipe_id:
        raise FreshInstanceRecipeError("an observation is assessed against its own recipe")
    markers = dict(observation.step_markers)
    if set(markers) != set(MATERIAL_KINDS):
        raise FreshInstanceRecipeError("every material kind needs its step marker")
    text = "\n".join(observation.requests)
    found = {kind: bool(markers[kind]) and markers[kind] in text for kind in MATERIAL_KINDS}
    decoys = _decoys_found(observation.decoy_markers, text, observation.protocol_events)
    listed = any(event.startswith("request tools/list") for event in observation.protocol_events)
    declared = dict(recipe.material)
    connected = bool(observation.requests)
    reasons = []
    if recipe.candidate:
        reasons.append("candidate recipe: listed for study, not launched, no support claim")
    if observation.installed_version != recipe.pinned_version:
        reasons.append("installed version differs from the pinned version: unqualified until proven again")
    if not connected:
        reasons.append("no request reached the endpoint; an exit is not loading")
    if decoys:
        reasons.append("material from outside the step reached the request")
    for kind in MATERIAL_KINDS:
        if declared[kind] == "loaded" and not found[kind]:
            reasons.append(f"{kind} is claimed loaded but its step marker is not in any request")
        if declared[kind] == "not_supported" and found[kind]:
            reasons.append(f"{kind} is recorded as not supported but its step marker arrived")
    required = [kind for kind in MATERIAL_KINDS if declared[kind] != "not_supported"]
    if connected and not decoys and required and all(found[kind] for kind in required):
        rung = "material_loaded"
    elif connected and (listed or any(found.values())):
        rung = "material_listed"
    else:
        rung = "connected" if connected else "none"
    return {"record_type": FRESH_INSTANCE_RESULT_RECORD_TYPE, "recipe_id": recipe.recipe_id,
            "recipe_digest": recipe.digest, "pinned_version": recipe.pinned_version,
            "installed_version": observation.installed_version,
            "version_matches_pin": observation.installed_version == recipe.pinned_version,
            "connected": connected, "exit_code": observation.exit_code,
            "timed_out": observation.timed_out,
            "material": {kind: {"declared": declared[kind], "found_in_request": found[kind]}
                         for kind in MATERIAL_KINDS},
            "protocol_server_listed": listed, "decoys_found": decoys, "rung": rung,
            "passed": not reasons, "reasons": reasons}


def self_test():
    """The fresh instance checks live beside this module."""
    from .harness_fresh_instance_checks import self_test as run_checks
    return run_checks()
