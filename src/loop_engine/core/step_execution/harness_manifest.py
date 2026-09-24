"""The declaration a harness author writes: step_harness_manifest/v1.

Owns the typed manifest that turns any harness program into a candidate step
executor engine without code: the launch command and environment as
templates over a closed list of fields, the working-folder layout (a
native_client_layout_profile/v1 client kind, the instruction files and the
skill folder), the native controls, capabilities and compatibility entries
with fresh-instance support, the sandbox and network needs, and how
completion and outputs are read. It is validated before any use, rendered for
one attempt's launch folder, and read from the release catalogue
``data/step_harness_manifests.yaml`` or from a host file. Belongs to the step
execution component (roadmap S-6.31, S-6.42).
Does not own: starting a process (core.step_execution.harness_launch), the
qualification that makes a registered harness eligible
(core.step_execution.qualification) or any authority. A manifest names what a
harness needs; it can never widen what a step's owning Loop grants: nothing in
it opens the network, adds a writable path, adds a credential or raises a
budget, and a need the step does not grant makes the engine ineligible.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import PurePosixPath
import re

from ..configuration_capabilities import digest
from ..engines.records import (
    EngineRecordError, identifier, member, pattern, read_part, read_record, sequence, text)
from ..harness_fresh_instances import CONFIGURATION_WRITERS, INSTRUCTION_BODIES
from ..harness_layering import NativeControl
from .records import (
    ACTIVATION_MODES, COMPONENT_SCOPES, FRESH_PROCESS, MATERIAL_KINDS, NATIVE_TOOLS, NETWORK_NEEDS, SUPPORT_STATES,
    CompatibilityEntry, ExecutorProfile)

MANIFEST_RECORD_TYPE = "step_harness_manifest/v1"
MANIFEST_CATALOG_RECORD_TYPE = "step_harness_manifest_catalog/v1"
MANIFEST_CATALOG_FILE = "step_harness_manifests.yaml"
#: The engine kinds a manifest may declare: a harness driven through its own
#: documented command line, or the Loop runtime started as a separate process.
MANIFEST_ENGINE_KINDS = ("native_protocol_harness", "custom_loop_harness")
NATIVE_KIND, CUSTOM_LOOP_KIND = MANIFEST_ENGINE_KINDS
#: The only isolations a process harness may declare; none is never enough.
PROCESS_ISOLATIONS = ("os_sandbox", "container")
STANDARD_INPUTS = ("none", "step_request_json")
OUTPUT_SOURCES = ("stdout", "result_file")
OUTPUT_FORMATS = ("text", "json_lines", "json_document", "step_run_result_json")
TEXT, JSON_LINES, JSON_DOCUMENT, STEP_RESULT_JSON = OUTPUT_FORMATS
OCCURRENCES = ("first", "last")
FRESH_INSTANCE_DECLARATIONS = ("supported", "unsupported")
#: The model wires a relay can serve, named by the release's wire codec records.
MODEL_WIRES = ("openai_chat_completions", "openai_responses", "google_generate_content", "anthropic_messages",
               "none")
#: The only names a template may contain, written as ``{name}``.
TEMPLATE_FIELDS = ("empty_home", "configuration_folder", "step_folder", "model_base_url", "model_name",
                   "model_credential", "step_prompt", "step_request_file", "step_result_file", "software_root")
#: A layout profile names a client kind of native_client_layout_profile/v1, or none.
NO_LAYOUT_PROFILE = "none"
MANIFEST_FIELDS = ("harness_id", "harness_version", "engine_kind", "title", "source", "launch", "layout",
                   "capabilities", "sandbox", "completion", "evidence")
LAUNCH_FIELDS = ("executable", "version_arguments", "version_pattern", "pinned_version", "arguments",
                 "environment", "configuration_variable", "configuration_writer", "standard_input")
LAYOUT_FIELDS = ("layout_profile", "instruction_files", "skills_directory", "global_locations")
CAPABILITY_FIELDS = ("supported_modes", "supported_features", "native_controls", "fresh_instance",
                     "compatibility")
SANDBOX_FIELDS = ("isolation", "network", "model_wire", "native_tools", "placement")
COMPLETION_FIELDS = ("completed_exit_codes", "output_source", "output_format", "event_field", "event_value",
                     "occurrence", "text_pointer")

_PLACEHOLDER = re.compile(r"\{([a-z_]+)\}")
_VARIABLE = re.compile(r"[A-Z][A-Z0-9_]{0,63}")
_PROGRAM = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.+-]{0,63}")
_VERSION = re.compile(r"[0-9A-Za-z][0-9A-Za-z.+_-]{0,63}")
_RELATIVE = re.compile(r"[A-Za-z0-9._-][A-Za-z0-9._/-]{0,159}")
_POINTER = re.compile(r"(?:/(?:[^/~]|~[01])*)*")
_UPSTREAM = re.compile(r"https://[a-z0-9.-]+/[A-Za-z0-9._/-]+")
_REVISION = re.compile(r"[0-9a-f]{7,40}")
_LICENCE = re.compile(r"[A-Za-z0-9][A-Za-z0-9.+-]{0,63}")
_CREDENTIAL_WORDS = ("key", "token", "secret", "password", "credential", "authorization")


def _refuse(code, detail):
    raise EngineRecordError(code, detail)


def _template(value, name):
    if type(value) is not str or "\x00" in value or len(value) > 512:
        _refuse("invalid_template", f"{name} is bounded text")
    fields = _PLACEHOLDER.findall(value)
    unknown = [field for field in fields if field not in TEMPLATE_FIELDS]
    rest = _PLACEHOLDER.sub("", value)
    if unknown or "{" in rest or "}" in rest:
        _refuse("invalid_template", f"{name} names a field outside {TEMPLATE_FIELDS}")
    return value


def _relative(value, name):
    pattern(value, name, _RELATIVE, "a relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts:
        _refuse("invalid_path", f"{name} stays inside its folder")
    return value


def _strings(value, name, rule):
    if type(value) not in (list, tuple):
        _refuse("invalid_field", f"{name} must be a list")
    return tuple(rule(item, name) for item in value)


def _registered_layout_profiles() -> tuple:
    """The client kinds of the packaged client registry, the ones the installer's
    native_client_layout_profile/v1 profiles are keyed by."""
    from importlib.resources import files
    registry = json.loads(files("loop_engine").joinpath(
        "core", "service_runtime", "web_assets", "client-recipes.json").read_text(encoding="utf-8"))
    return tuple(row["id"] for row in registry["recipes"])


@dataclass(frozen=True)
class ManifestLaunch:
    """How the harness starts for one step: a program, arguments and environment as templates."""

    executable: str
    version_arguments: tuple
    version_pattern: "str | None"
    pinned_version: "str | None"
    arguments: tuple
    environment: tuple
    configuration_variable: "str | None"
    configuration_writer: str
    standard_input: str

    def __post_init__(self):
        pattern(self.executable, "executable", _PROGRAM, "a program name")
        object.__setattr__(self, "version_arguments", _strings(self.version_arguments, "version_arguments",
                                                               _template))
        if self.version_pattern is not None:
            try:
                compiled = re.compile(self.version_pattern)
            except (re.error, TypeError) as exc:
                raise EngineRecordError("invalid_field", "version_pattern is a regular expression") from exc
            if compiled.groups != 1:
                _refuse("invalid_field", "version_pattern captures exactly one version")
        if self.pinned_version is not None:
            pattern(self.pinned_version, "pinned_version", _VERSION, "a version")
        object.__setattr__(self, "arguments", _strings(self.arguments, "arguments", _template))
        environment = tuple(self.environment)
        names = [name for name, _ in environment]
        if len(set(names)) != len(names):
            _refuse("repeated_value", "an environment variable is named once")
        for name, value in environment:
            pattern(name, "environment variable", _VARIABLE, "an upper case variable name")
            _template(value, "environment value")
        object.__setattr__(self, "environment", environment)
        if self.configuration_variable is not None:
            pattern(self.configuration_variable, "configuration_variable", _VARIABLE, "a variable name")
        member(self.configuration_writer, "configuration_writer", CONFIGURATION_WRITERS)
        member(self.standard_input, "standard_input", STANDARD_INPUTS)
        _require_fresh_launch(self)

    def to_dict(self):
        return {"executable": self.executable, "version_arguments": list(self.version_arguments),
                "version_pattern": self.version_pattern, "pinned_version": self.pinned_version,
                "arguments": list(self.arguments), "environment": dict(self.environment),
                "configuration_variable": self.configuration_variable,
                "configuration_writer": self.configuration_writer, "standard_input": self.standard_input}


def _require_fresh_launch(launch):
    """The September 22 finding as a rule: a fresh instance starts with HOME set to the
    empty home folder and its own configuration folder; a credential reaches a harness
    only through its own environment, never a command line every process can read."""
    environment = dict(launch.environment)
    if environment.get("HOME") != "{empty_home}":
        _refuse("fresh_instance_rule", "a fresh instance starts with HOME set to {empty_home}")
    if launch.configuration_variable is not None and not environment.get(
            launch.configuration_variable, "").startswith("{configuration_folder}"):
        _refuse("fresh_instance_rule", "the configuration variable names {configuration_folder}")
    if any("{model_credential}" in item for item in launch.arguments + launch.version_arguments):
        _refuse("credential_on_command_line", "the model credential reaches a harness only through its environment")
    for name, value in launch.environment:
        words = name.lower().split("_")
        if any(word in _CREDENTIAL_WORDS for word in words) and value != "{model_credential}":
            _refuse("credential_in_manifest", f"{name} carries a credential that is not the step's own")


@dataclass(frozen=True)
class ManifestLayout:
    """Where the step's material goes in the harness's working folder."""

    layout_profile: str
    instruction_files: tuple
    skills_directory: "str | None"
    global_locations: tuple

    def __post_init__(self):
        if self.layout_profile != NO_LAYOUT_PROFILE and self.layout_profile not in _registered_layout_profiles():
            _refuse("unknown_layout_profile", f"{self.layout_profile} is not a registered client layout profile")
        files = tuple(self.instruction_files)
        for name, body in files:
            _relative(name, "instruction file")
            member(body, "instruction body", INSTRUCTION_BODIES)
        if len({name for name, _ in files}) != len(files):
            _refuse("repeated_value", "an instruction file is named once")
        object.__setattr__(self, "instruction_files", files)
        if self.skills_directory is not None:
            _relative(self.skills_directory, "skills_directory")
        object.__setattr__(self, "global_locations", _strings(self.global_locations, "global_locations",
                                                              _relative))

    def to_dict(self):
        return {"layout_profile": self.layout_profile,
                "instruction_files": [{"name": name, "body": body} for name, body in self.instruction_files],
                "skills_directory": self.skills_directory, "global_locations": list(self.global_locations)}


@dataclass(frozen=True)
class ManifestCompletion:
    """How completion is decided and the output read: an exit code and a declared place and shape."""

    completed_exit_codes: tuple
    output_source: str
    output_format: str
    event_field: str
    event_value: str
    occurrence: str
    text_pointer: str

    def __post_init__(self):
        codes = tuple(self.completed_exit_codes)
        if not codes or any(type(code) is not int or not 0 <= code <= 255 for code in codes):
            _refuse("invalid_field", "completed_exit_codes are process exit codes")
        object.__setattr__(self, "completed_exit_codes", codes)
        member(self.output_source, "output_source", OUTPUT_SOURCES)
        member(self.output_format, "output_format", OUTPUT_FORMATS)
        member(self.occurrence, "occurrence", OCCURRENCES)
        pattern(self.text_pointer, "text_pointer", _POINTER, "a JSON pointer")
        structured = self.output_format in (JSON_LINES, JSON_DOCUMENT)
        if (self.output_format == STEP_RESULT_JSON) != (self.output_source == "result_file"):
            _refuse("invalid_field", "a step result is read from the result file, and only a step result is")
        if structured != bool(self.text_pointer):
            _refuse("invalid_field", "a JSON output names the pointer to its text, and only a JSON output does")
        if (self.output_format == JSON_LINES) != bool(self.event_field):
            _refuse("invalid_field", "JSON lines name the event field that selects the answer, and only they do")
        if self.event_field:
            identifier(self.event_field, "event_field")
            text(self.event_value, "event_value", 64)
        elif self.event_value:
            _refuse("invalid_field", "an event value belongs to an event field")

    def to_dict(self):
        return {"completed_exit_codes": list(self.completed_exit_codes), "output_source": self.output_source,
                "output_format": self.output_format, "event_field": self.event_field,
                "event_value": self.event_value, "occurrence": self.occurrence, "text_pointer": self.text_pointer}


@dataclass(frozen=True)
class StepHarnessManifest:
    """One harness declared for the step edge; a declaration, never a grant."""

    harness_id: str
    harness_version: str
    engine_kind: str
    title: str
    source: tuple
    launch: ManifestLaunch
    layout: ManifestLayout
    supported_modes: tuple
    supported_features: tuple
    native_controls: tuple
    fresh_instance: str
    compatibility: tuple
    isolation: str
    network: str
    model_wire: str
    native_tools: str
    placement: str
    completion: ManifestCompletion
    evidence: tuple

    def __post_init__(self):
        identifier(self.harness_id, "harness_id")
        pattern(self.harness_version, "harness_version", _VERSION, "a version")
        member(self.engine_kind, "engine_kind", MANIFEST_ENGINE_KINDS)
        text(self.title, "title", 160)
        upstream, revision, licence = self.source
        pattern(upstream, "source upstream", _UPSTREAM, "an https repository address")
        if revision is not None:
            pattern(revision, "source revision", _REVISION, "a commit")
        pattern(licence, "licence", _LICENCE, "an SPDX identifier or unknown")
        for name, kind in (("launch", ManifestLaunch), ("layout", ManifestLayout),
                           ("completion", ManifestCompletion)):
            if not isinstance(getattr(self, name), kind):
                _refuse("invalid_field", f"{name} must be a {kind.__name__}")
        from ..engines.records import engine_modes
        object.__setattr__(self, "supported_modes", sequence(
            self.supported_modes, "supported_modes", lambda v, n: member(v, n, engine_modes()), nonempty=True))
        object.__setattr__(self, "supported_features", sequence(self.supported_features, "supported_features",
                                                                identifier))
        object.__setattr__(self, "native_controls", sequence(
            self.native_controls, "native_controls",
            lambda v, n: member(v, n, tuple(item.value for item in NativeControl))))
        member(self.fresh_instance, "fresh_instance", FRESH_INSTANCE_DECLARATIONS)
        entries = tuple(self.compatibility)
        if any(not isinstance(item, CompatibilityEntry) for item in entries):
            _refuse("invalid_field", "compatibility holds CompatibilityEntry values")
        object.__setattr__(self, "compatibility", entries)
        member(self.isolation, "isolation", PROCESS_ISOLATIONS)
        member(self.network, "network", NETWORK_NEEDS)
        member(self.model_wire, "model_wire", MODEL_WIRES)
        member(self.native_tools, "native_tools", NATIVE_TOOLS)
        if self.placement != FRESH_PROCESS:
            _refuse("placement_not_qualified", "only a fresh process for each step is qualified for a manifest")
        object.__setattr__(self, "evidence", _strings(self.evidence, "evidence", _relative))
        _require_consistent_needs(self)

    def to_dict(self) -> dict:
        upstream, revision, licence = self.source
        return {"record_type": MANIFEST_RECORD_TYPE, "harness_id": self.harness_id,
                "harness_version": self.harness_version, "engine_kind": self.engine_kind, "title": self.title,
                "source": {"upstream": upstream, "revision": revision, "licence": licence},
                "launch": self.launch.to_dict(), "layout": self.layout.to_dict(),
                "capabilities": {"supported_modes": list(self.supported_modes),
                                 "supported_features": list(self.supported_features),
                                 "native_controls": list(self.native_controls),
                                 "fresh_instance": self.fresh_instance,
                                 "compatibility": [item.to_dict() for item in self.compatibility]},
                "sandbox": {"isolation": self.isolation, "network": self.network, "model_wire": self.model_wire,
                            "native_tools": self.native_tools, "placement": self.placement},
                "completion": self.completion.to_dict(), "evidence": list(self.evidence)}

    @property
    def engine_ref(self) -> str:
        return f"{self.harness_id}@{self.harness_version}"

    @property
    def content_digest(self) -> str:
        return digest(self.to_dict())

    def executor_profile(self) -> ExecutorProfile:
        """The capability record this manifest declares; a fresh instance is proven only by qualification."""
        return ExecutorProfile(
            self.engine_kind, self.isolation, self.placement, self.fresh_instance, self.supported_modes,
            self.supported_features, ("model_calls", "wall_time"), self.native_controls, self.network,
            self.model_wire, self.native_tools, ("spawns_process",), self.compatibility)

    @classmethod
    def from_dict(cls, record) -> "StepHarnessManifest":
        """Read a manifest; an unknown key, another version or a missing part refuses before any use."""
        record = read_record(record, MANIFEST_RECORD_TYPE, MANIFEST_FIELDS)
        source = read_part(record["source"], "source", ("upstream", "revision", "licence"))
        launch = read_part(record["launch"], "launch", LAUNCH_FIELDS)
        if type(launch["environment"]) is not dict:
            _refuse("invalid_field", "environment must be a mapping")
        layout = read_part(record["layout"], "layout", LAYOUT_FIELDS)
        files = []
        for item in layout["instruction_files"] if type(layout["instruction_files"]) is list else [None]:
            item = read_part(item, "instruction file", ("name", "body"))
            files.append((item["name"], item["body"]))
        capabilities = read_part(record["capabilities"], "capabilities", CAPABILITY_FIELDS)
        entries = []
        for item in capabilities["compatibility"] if type(capabilities["compatibility"]) is list else [None]:
            entries.append(CompatibilityEntry(**read_part(item, "compatibility entry", tuple(
                CompatibilityEntry.__dataclass_fields__))))
        sandbox = read_part(record["sandbox"], "sandbox", SANDBOX_FIELDS)
        completion = read_part(record["completion"], "completion", COMPLETION_FIELDS)
        return cls(
            record["harness_id"], record["harness_version"], record["engine_kind"], record["title"],
            (source["upstream"], source["revision"], source["licence"]),
            ManifestLaunch(launch["executable"], launch["version_arguments"], launch["version_pattern"],
                           launch["pinned_version"], launch["arguments"],
                           tuple(launch["environment"].items()), launch["configuration_variable"],
                           launch["configuration_writer"], launch["standard_input"]),
            ManifestLayout(layout["layout_profile"], tuple(files), layout["skills_directory"],
                           layout["global_locations"]),
            capabilities["supported_modes"], capabilities["supported_features"], capabilities["native_controls"],
            capabilities["fresh_instance"], tuple(entries), sandbox["isolation"], sandbox["network"],
            sandbox["model_wire"], sandbox["native_tools"], sandbox["placement"],
            ManifestCompletion(**completion), record["evidence"])


def _require_consistent_needs(manifest):
    """What a harness reads must match how it is started: the Loop harness speaks the
    step edge and needs no network; a model-led harness names the wire it speaks; a
    skill the manifest supports has a folder; the request file is given when the
    harness reads it."""
    arguments = " ".join(manifest.launch.arguments)
    if manifest.engine_kind == CUSTOM_LOOP_KIND and (
            manifest.completion.output_format != STEP_RESULT_JSON or manifest.network != "none"):
        _refuse("inconsistent_manifest", "a custom Loop harness returns a step result and needs no network")
    if manifest.network == "loopback_model_endpoint" and manifest.model_wire == "none":
        _refuse("inconsistent_manifest", "a model endpoint is served in a declared wire")
    if manifest.network == "none" and manifest.model_wire != "none":
        _refuse("inconsistent_manifest", "a model wire needs the loopback model endpoint")
    if manifest.completion.output_format == STEP_RESULT_JSON and "{step_result_file}" not in arguments:
        _refuse("inconsistent_manifest", "a harness that writes a step result is told where")
    if manifest.launch.standard_input == "none" and "{step_request_file}" not in arguments and \
            manifest.engine_kind == CUSTOM_LOOP_KIND:
        _refuse("inconsistent_manifest", "a custom Loop harness reads the step request")
    skills = [item for item in manifest.compatibility if item.component_type == "skill"
              and item.support in SUPPORT_STATES[:3]]
    if skills and manifest.layout.skills_directory is None:
        _refuse("inconsistent_manifest", "a harness that loads skills names its skill folder")
    for item in manifest.compatibility:
        member(item.scope, "compatibility scope", COMPONENT_SCOPES)
        member(item.activation, "compatibility activation", ACTIVATION_MODES)
        member(item.component_type, "compatibility component", MATERIAL_KINDS)


def render(template: str, values: dict) -> str:
    """Replace every ``{field}`` of a checked template; nothing else changes."""
    return _PLACEHOLDER.sub(lambda match: values[match.group(1)], _template(template, "template"))


def render_launch(manifest: StepHarnessManifest, values: dict) -> tuple:
    """The rendered arguments (after the program) and the rendered environment."""
    missing = sorted(set(TEMPLATE_FIELDS) - set(values))
    if missing:
        _refuse("template_values_missing", str(missing))
    return (tuple(render(item, values) for item in manifest.launch.arguments),
            {name: render(item, values) for name, item in manifest.launch.environment})


@dataclass(frozen=True)
class StepHarnessManifestCatalog:
    """The manifests the release ships, each named once."""

    version: str
    manifests: tuple

    def __post_init__(self):
        pattern(self.version, "catalog version", re.compile(r"[0-9]+\.[0-9]+\.[0-9]+"), "a semantic version")
        manifests = tuple(self.manifests)
        if any(not isinstance(item, StepHarnessManifest) for item in manifests):
            _refuse("invalid_field", "a catalogue holds manifests")
        names = [item.harness_id for item in manifests]
        if len(set(names)) != len(names):
            _refuse("repeated_value", "a harness is declared once in a catalogue")
        object.__setattr__(self, "manifests", manifests)

    def manifest(self, harness_id: str) -> StepHarnessManifest:
        for item in self.manifests:
            if item.harness_id == harness_id:
                return item
        _refuse("manifest_not_found", harness_id)

    @property
    def content_digest(self) -> str:
        return digest({"version": self.version, "manifests": [item.to_dict() for item in self.manifests]})

    @classmethod
    def from_dict(cls, record) -> "StepHarnessManifestCatalog":
        record = read_record(record, MANIFEST_CATALOG_RECORD_TYPE, ("version", "manifests"))
        if type(record["manifests"]) is not list:
            _refuse("invalid_field", "manifests must be a list")
        return cls(record["version"], tuple(StepHarnessManifest.from_dict(item) for item in record["manifests"]))


def release_manifest_catalog() -> StepHarnessManifestCatalog:
    """The manifests this release ships, read through the one component resource loader."""
    from ..component_contracts import load_component_resource
    return StepHarnessManifestCatalog.from_dict(
        load_component_resource(MANIFEST_CATALOG_FILE, MANIFEST_CATALOG_RECORD_TYPE))


def self_test():
    """Run the manifest checks."""
    from .harness_manifest_checks import self_test as run_manifest_checks
    return run_manifest_checks()
