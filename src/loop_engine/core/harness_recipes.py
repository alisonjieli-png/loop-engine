"""The release catalogue of process harness recipes, read from package data.

Owns: the typed reader of ``src/loop_engine/data/harness_recipes.yaml``
(``harness_recipe_catalog/v1``): one ``harness_recipe/v1`` for each
command-line harness style, one ``harness_wire_codec/v1`` for each model wire
the relay translates, and the ``harness_fresh_instance_recipe/v1`` launch
recipes that ``harness_fresh_instances`` reads. A style, its module, its
functions, its wire and the codec module of that wire are data here, so adding
a command-line harness is one recipe module and one record, and the process
runner and its relay name no style (plan package X1, engine design 13.7).
Does not own: execution, isolation, model authority or qualification. The
catalogue is package data, never host data: a host file names a style that the
release ships and digests; it cannot name a module or another catalogue.
Every record refuses unknown keys and other versions before any effect, and a
module is loaded only after its bytes match the digest the catalogue records.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
from functools import lru_cache
import hashlib
import importlib.util
from importlib.resources import files
import json
from pathlib import Path
import re
import sys

import yaml

RECIPE_CATALOG_RECORD_TYPE = "harness_recipe_catalog/v1"
RECIPE_RECORD_TYPE = "harness_recipe/v1"
WIRE_CODEC_RECORD_TYPE = "harness_wire_codec/v1"
CATALOG_FILE = "harness_recipes.yaml"

#: What a recipe runs: brokered text only, native tools in the work folder,
#: or the Agent Client Protocol. The text relay runner serves the first only.
RECIPE_VARIANTS = ("text_response", "workspace_tools", "agent_protocol")
TEXT_RESPONSE_VARIANT = RECIPE_VARIANTS[0]
#: How the release obtains the harness program (the Agent Client Protocol
#: registry's distribution kinds, plus a local source checkout).
DISTRIBUTION_KINDS = ("binary", "npx", "uvx", "local")
PATH_MATCHES = ("exact", "prefix")
#: How the relay writes one answer back on a wire. Framing is transport, so
#: the relay knows these four and never a style.
STREAM_FRAMINGS = ("openai_chat_chunks", "responses_events", "single_data_event", "none")
#: The only framing of the wire the relay serves itself, with no codec module.
RELAY_NATIVE_FRAMING = STREAM_FRAMINGS[0]
#: Request values a recipe may copy into its sandbox environment.
ENVIRONMENT_VALUE_SOURCES = ("maximum_output_bytes", "maximum_request_bytes",
                             "output_capacity", "output_allowance", "context_capacity")
#: The instruction style of a harness that reads only the standard file.
STANDARD_INSTRUCTION_STYLE = "standard"

_STYLE = re.compile(r"[a-z][a-z0-9_.-]{0,95}")
_NAME = re.compile(r"[a-z][a-z0-9_]{0,63}")
_VARIABLE = re.compile(r"[A-Z][A-Z0-9_]{0,63}")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_VERSION = re.compile(r"[A-Za-z0-9][A-Za-z0-9.+_-]{0,95}")
_REQUEST_PATH = re.compile(r"/[A-Za-z0-9._/-]{0,127}")


class HarnessRecipeError(ValueError):
    """A recipe record, wire codec or catalogue that this release refuses."""


def _exact_keys(value, keys, name):
    if type(value) is not dict or set(value) != set(keys):
        raise HarnessRecipeError(f"{name} must hold exactly the fields {sorted(keys)}")


def _record_type(value, expected, name):
    if type(value) is not dict or value.get("record_type") != expected:
        raise HarnessRecipeError(f"{name} must be {expected}; other versions are refused")


def _text(value, pattern, name, *, optional=False):
    if value is None and optional:
        return None
    if type(value) is not str or not pattern.fullmatch(value):
        raise HarnessRecipeError(f"{name} is not a valid value")
    return value


def _canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False)


def _digest(value) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def module_file_sha256(path) -> str:
    """The SHA-256 of one module file's exact bytes."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _defined_functions(data: bytes) -> frozenset:
    """Top-level function names of module source, read without importing it."""
    tree = ast.parse(data.decode("utf-8"))
    return frozenset(node.name for node in tree.body if isinstance(node, ast.FunctionDef))


@dataclass(frozen=True)
class RecipeDistribution:
    """How the release obtains a harness and the pin it was written against.

    ``sha256`` is the digest a qualification bound, or None where no
    qualification pinned one; it is never guessed."""

    kind: str
    version: str
    sha256: str | None

    def __post_init__(self):
        if self.kind not in DISTRIBUTION_KINDS:
            raise HarnessRecipeError(f"distribution kind must be one of {DISTRIBUTION_KINDS}")
        _text(self.version, _VERSION, "distribution version")
        _text(self.sha256, _SHA256, "distribution sha256", optional=True)

    def to_dict(self) -> dict:
        return {"kind": self.kind, "version": self.version, "sha256": self.sha256}

    @classmethod
    def from_dict(cls, value) -> "RecipeDistribution":
        _exact_keys(value, ("kind", "version", "sha256"), "distribution")
        return cls(value["kind"], value["version"], value["sha256"])


@dataclass(frozen=True)
class RecipeModule:
    """One module file the sandbox mounts, with the digest it must match."""

    module: str
    path: str
    sha256: str


def _native_control_policy(value):
    from .harness_layering import (ControlOwnership, HarnessLayeringError, NativeControl,
                                   NativeControlPolicy)
    _exact_keys(value, ("ownership", "reasons"), "native_controls")
    if type(value["ownership"]) is not dict or type(value["reasons"]) is not dict:
        raise HarnessRecipeError("native control ownership and reasons must be mappings")
    try:
        return NativeControlPolicy(
            {NativeControl(control): ControlOwnership(owner)
             for control, owner in value["ownership"].items()},
            {NativeControl(control): reason for control, reason in value["reasons"].items()})
    except (ValueError, HarnessLayeringError) as exc:
        raise HarnessRecipeError(f"native controls are not a complete ownership policy: {exc}") from exc


def _native_control_dict(policy) -> dict:
    return {"ownership": {control.value: owner.value for control, owner in policy.ownership.items()},
            "reasons": {control.value: reason for control, reason in policy.reasons.items()}}


def _sandbox_environment(value) -> tuple:
    from .harness_confinement import default_confined_environment
    if type(value) is not list:
        raise HarnessRecipeError("sandbox_environment must be a list of variables")
    confined = default_confined_environment().variables()
    entries = []
    for item in value:
        _exact_keys(item, ("variable", "value_from"), "sandbox environment entry")
        variable = _text(item["variable"], _VARIABLE, "sandbox environment variable")
        if variable in confined:
            raise HarnessRecipeError(f"{variable} is set by the confined environment; a recipe cannot change it")
        if item["value_from"] not in ENVIRONMENT_VALUE_SOURCES:
            raise HarnessRecipeError(f"a sandbox variable may copy only {ENVIRONMENT_VALUE_SOURCES}")
        entries.append((variable, item["value_from"]))
    if len({name for name, _ in entries}) != len(entries):
        raise HarnessRecipeError("a sandbox variable is declared twice")
    return tuple(entries)


@dataclass(frozen=True)
class HarnessRecipe:
    """How one command-line harness style is launched and read.

    ``module`` is mounted into the sandbox with the codec module of each wire
    in ``wire_protocols``; ``prepare_function(style, config, base)`` returns
    the command, environment overrides and prompt, and
    ``extract_function(style, stdout, expected)`` admits the answer."""

    style: str
    variant: str
    module: str | None
    prepare_function: str | None
    extract_function: str | None
    module_sha256: str | None
    wire_protocols: tuple
    instruction_style: str
    requires_context_capacity: bool
    sandbox_environment: tuple
    native_controls: object
    distribution: RecipeDistribution

    FIELDS = ("record_type", "style", "variant", "module", "prepare_function",
              "extract_function", "module_sha256", "wire_protocols", "instruction_style",
              "requires_context_capacity", "sandbox_environment", "native_controls",
              "distribution")

    def __post_init__(self):
        from .harness_layering import NativeControlPolicy
        from .instance_instructions import STYLE_FILES
        _text(self.style, _STYLE, "recipe style")
        if self.variant not in RECIPE_VARIANTS:
            raise HarnessRecipeError(f"recipe variant must be one of {RECIPE_VARIANTS}")
        named = (self.module, self.module_sha256, self.prepare_function, self.extract_function)
        if self.variant == TEXT_RESPONSE_VARIANT and any(item is None for item in named):
            raise HarnessRecipeError("a text response recipe names its module, digest and functions")
        if self.module is None and any(item is not None for item in named):
            raise HarnessRecipeError("functions and a digest need the module that holds them")
        _text(self.module, _NAME, "recipe module", optional=True)
        _text(self.module_sha256, _SHA256, "recipe module digest", optional=True)
        _text(self.prepare_function, _NAME, "prepare function", optional=True)
        _text(self.extract_function, _NAME, "extract function", optional=True)
        if (type(self.wire_protocols) is not tuple
                or len(set(self.wire_protocols)) != len(self.wire_protocols)
                or (self.variant == TEXT_RESPONSE_VARIANT and not self.wire_protocols)):
            raise HarnessRecipeError("wire protocols must be a unique tuple, and a text recipe needs one")
        for wire in self.wire_protocols:
            _text(wire, _NAME, "wire protocol")
        if self.instruction_style != STANDARD_INSTRUCTION_STYLE and self.instruction_style not in {
                entry.style for entry in STYLE_FILES}:
            raise HarnessRecipeError("instruction_style must name an instruction file row or the standard file")
        if type(self.requires_context_capacity) is not bool:
            raise HarnessRecipeError("requires_context_capacity must be a Boolean")
        if type(self.sandbox_environment) is not tuple:
            raise HarnessRecipeError("sandbox_environment must be a tuple")
        if not isinstance(self.native_controls, NativeControlPolicy):
            raise HarnessRecipeError("native_controls must be a native control ownership policy")
        if not isinstance(self.distribution, RecipeDistribution):
            raise HarnessRecipeError("distribution must be a typed distribution record")

    def to_dict(self) -> dict:
        return {"record_type": RECIPE_RECORD_TYPE, "style": self.style, "variant": self.variant,
                "module": self.module, "prepare_function": self.prepare_function,
                "extract_function": self.extract_function, "module_sha256": self.module_sha256,
                "wire_protocols": list(self.wire_protocols),
                "instruction_style": self.instruction_style,
                "requires_context_capacity": self.requires_context_capacity,
                "sandbox_environment": [{"variable": name, "value_from": source}
                                        for name, source in self.sandbox_environment],
                "native_controls": _native_control_dict(self.native_controls),
                "distribution": self.distribution.to_dict()}

    @property
    def digest(self) -> str:
        return _digest(self.to_dict())

    @classmethod
    def from_dict(cls, value) -> "HarnessRecipe":
        _record_type(value, RECIPE_RECORD_TYPE, "a harness recipe")
        _exact_keys(value, cls.FIELDS, "a harness recipe")
        if type(value["wire_protocols"]) is not list:
            raise HarnessRecipeError("wire_protocols must be a list")
        return cls(value["style"], value["variant"], value["module"], value["prepare_function"],
                   value["extract_function"], value["module_sha256"],
                   tuple(value["wire_protocols"]), value["instruction_style"],
                   value["requires_context_capacity"],
                   _sandbox_environment(value["sandbox_environment"]),
                   _native_control_policy(value["native_controls"]),
                   RecipeDistribution.from_dict(value["distribution"]))


@dataclass(frozen=True)
class HarnessWireCodec:
    """One model wire the relay translates, and where its codec lives.

    A wire with no module is served by the relay itself on the OpenAI chat
    wire. A codec module is mounted beside the recipe that declares the wire,
    whichever module the recipe itself lives in."""

    wire_protocol: str
    module: str | None
    module_sha256: str | None
    decode_function: str | None
    encode_function: str | None
    request_paths: tuple
    path_match: str
    stream_framing: str

    FIELDS = ("record_type", "wire_protocol", "module", "module_sha256", "decode_function",
              "encode_function", "request_paths", "path_match", "stream_framing")

    def __post_init__(self):
        _text(self.wire_protocol, _NAME, "wire protocol")
        named = (self.module, self.module_sha256, self.decode_function, self.encode_function)
        if any(item is None for item in named) and any(item is not None for item in named):
            raise HarnessRecipeError("a codec names its module, digest, decoder and encoder together")
        _text(self.module, _NAME, "codec module", optional=True)
        _text(self.module_sha256, _SHA256, "codec module digest", optional=True)
        _text(self.decode_function, _NAME, "decode function", optional=True)
        _text(self.encode_function, _NAME, "encode function", optional=True)
        if (type(self.request_paths) is not tuple or not self.request_paths
                or len(set(self.request_paths)) != len(self.request_paths)):
            raise HarnessRecipeError("a wire needs a unique tuple of request paths")
        for path in self.request_paths:
            _text(path, _REQUEST_PATH, "wire request path")
        if self.path_match not in PATH_MATCHES:
            raise HarnessRecipeError(f"path_match must be one of {PATH_MATCHES}")
        if self.stream_framing not in STREAM_FRAMINGS:
            raise HarnessRecipeError(f"stream_framing must be one of {STREAM_FRAMINGS}")
        if (self.module is None) != (self.stream_framing == RELAY_NATIVE_FRAMING):
            raise HarnessRecipeError("only the relay's own chat wire has no codec module")

    def matches(self, path: str) -> bool:
        if self.path_match == "exact":
            return path in self.request_paths
        return any(path.startswith(prefix) for prefix in self.request_paths)

    def to_dict(self) -> dict:
        return {"record_type": WIRE_CODEC_RECORD_TYPE, "wire_protocol": self.wire_protocol,
                "module": self.module, "module_sha256": self.module_sha256,
                "decode_function": self.decode_function, "encode_function": self.encode_function,
                "request_paths": list(self.request_paths), "path_match": self.path_match,
                "stream_framing": self.stream_framing}

    @property
    def digest(self) -> str:
        return _digest(self.to_dict())

    @classmethod
    def from_dict(cls, value) -> "HarnessWireCodec":
        _record_type(value, WIRE_CODEC_RECORD_TYPE, "a wire codec")
        _exact_keys(value, cls.FIELDS, "a wire codec")
        if type(value["request_paths"]) is not list:
            raise HarnessRecipeError("request_paths must be a list")
        return cls(value["wire_protocol"], value["module"], value["module_sha256"],
                   value["decode_function"], value["encode_function"],
                   tuple(value["request_paths"]), value["path_match"], value["stream_framing"])


def _paths_overlap(first: HarnessWireCodec, second: HarnessWireCodec) -> bool:
    return (any(second.matches(path) for path in first.request_paths)
            or any(first.matches(path) for path in second.request_paths))


@dataclass(frozen=True)
class HarnessRecipeCatalog:
    """Every recipe, wire codec and fresh instance recipe of one catalogue.

    ``module_directory`` holds every module a record names; for the release
    catalogue it is this package folder. Record data is validated when the
    catalogue is built; module files are verified when a recipe is bound or a
    function is loaded, so one stale module refuses its own recipe only."""

    version: str
    wire_codecs: tuple
    recipes: tuple
    fresh_instance_recipes: tuple
    module_directory: str

    FIELDS = ("record_type", "version", "wire_codecs", "recipes", "fresh_instance_recipes")

    def __post_init__(self):
        _text(self.version, _VERSION, "catalogue version")
        if (any(not isinstance(item, HarnessWireCodec) for item in self.wire_codecs)
                or any(not isinstance(item, HarnessRecipe) for item in self.recipes)):
            raise HarnessRecipeError("a catalogue holds typed recipes and wire codecs")
        wires = {item.wire_protocol: item for item in self.wire_codecs}
        if len(wires) != len(self.wire_codecs):
            raise HarnessRecipeError("a wire protocol is declared twice")
        if len({item.style for item in self.recipes}) != len(self.recipes):
            raise HarnessRecipeError("a recipe style is declared twice")
        for recipe in self.recipes:
            unknown = [wire for wire in recipe.wire_protocols if wire not in wires]
            if unknown:
                raise HarnessRecipeError(f"{recipe.style} declares wires the catalogue lacks: {unknown}")
            declared = [wires[wire] for wire in recipe.wire_protocols]
            if any(_paths_overlap(first, second) for index, first in enumerate(declared)
                   for second in declared[index + 1:]):
                raise HarnessRecipeError(f"{recipe.style} declares wires whose request paths overlap")
        digests = {}
        for module, sha256 in self._named_modules():
            if digests.setdefault(module, sha256) != sha256:
                raise HarnessRecipeError(f"{module} is named with two different digests")
        directory = Path(self.module_directory)
        if not directory.is_absolute() or not directory.is_dir():
            raise HarnessRecipeError("the module directory must be an existing absolute folder")
        seen = set()
        for item in self.fresh_instance_recipes:
            if getattr(item, "recipe_id", None) in seen:
                raise HarnessRecipeError("a fresh instance recipe is declared twice")
            seen.add(item.recipe_id)

    def _named_modules(self):
        for item in self.recipes:
            if item.module is not None:
                yield item.module, item.module_sha256
        for item in self.wire_codecs:
            if item.module is not None:
                yield item.module, item.module_sha256

    def recipe(self, style: str):
        """The recipe of one style, or None when this catalogue has none."""
        return next((item for item in self.recipes if item.style == style), None)

    def wires_for(self, recipe: HarnessRecipe) -> tuple:
        wires = {item.wire_protocol: item for item in self.wire_codecs}
        return tuple(wires[name] for name in recipe.wire_protocols)

    def module_digest(self, module: str) -> str:
        for name, sha256 in self._named_modules():
            if name == module:
                return sha256
        raise HarnessRecipeError(f"{module} is not a module this catalogue names")

    def _verified(self, module: str, functions) -> RecipeModule:
        path = Path(self.module_directory) / (module + ".py")
        if not path.is_file() or path.is_symlink():
            raise HarnessRecipeError(f"{module} is missing from the module folder")
        data = path.read_bytes()
        sha256 = self.module_digest(module)
        if hashlib.sha256(data).hexdigest() != sha256:
            raise HarnessRecipeError(f"{module} differs from the digest the catalogue records")
        missing = sorted(set(functions) - _defined_functions(data))
        if missing:
            raise HarnessRecipeError(f"{module} does not define {missing}")
        return RecipeModule(module, str(path), sha256)

    def mounted_modules(self, recipe: HarnessRecipe) -> tuple:
        """The recipe's own module and each declared wire's codec module,
        verified against their digests; nothing else is mounted."""
        if recipe.module is None:
            raise HarnessRecipeError(f"{recipe.style} names no module to mount")
        needed = {recipe.module: {recipe.prepare_function, recipe.extract_function}}
        for wire in self.wires_for(recipe):
            if wire.module is not None:
                needed.setdefault(wire.module, set()).update(
                    {wire.decode_function, wire.encode_function})
        return tuple(self._verified(module, needed[module]) for module in sorted(needed))

    def to_dict(self) -> dict:
        return {"record_type": RECIPE_CATALOG_RECORD_TYPE, "version": self.version,
                "wire_codecs": [item.to_dict() for item in self.wire_codecs],
                "recipes": [item.to_dict() for item in self.recipes],
                "fresh_instance_recipes": [item.to_dict() for item in self.fresh_instance_recipes]}

    @property
    def digest(self) -> str:
        return _digest(self.to_dict())

    @classmethod
    def from_dict(cls, value, *, module_directory: str) -> "HarnessRecipeCatalog":
        from .harness_fresh_instances import FreshInstanceRecipe
        _record_type(value, RECIPE_CATALOG_RECORD_TYPE, "a harness recipe catalogue")
        _exact_keys(value, cls.FIELDS, "a harness recipe catalogue")
        for name in ("wire_codecs", "recipes", "fresh_instance_recipes"):
            if type(value[name]) is not list:
                raise HarnessRecipeError(f"{name} must be a list")
        try:
            fresh = tuple(FreshInstanceRecipe.from_dict(item) for item in value["fresh_instance_recipes"])
        except ValueError as exc:
            raise HarnessRecipeError(f"a fresh instance recipe is refused: {exc}") from exc
        return cls(value["version"],
                   tuple(HarnessWireCodec.from_dict(item) for item in value["wire_codecs"]),
                   tuple(HarnessRecipe.from_dict(item) for item in value["recipes"]),
                   fresh, str(module_directory))


class _UniqueKeyLoader(yaml.SafeLoader):
    """A safe YAML reader that refuses a key written twice in one mapping."""


def _unique_mapping(loader, node, deep=False):
    keys = [loader.construct_object(key, deep=deep) for key, _ in node.value]
    if len(keys) != len(set(keys)):
        raise HarnessRecipeError("a catalogue mapping repeats a key")
    return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)


_UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _unique_mapping)


def load_recipe_catalog(path, *, module_directory) -> HarnessRecipeCatalog:
    """Read one catalogue file; reading starts nothing and imports no recipe."""
    source = path if hasattr(path, "read_text") else Path(path)
    text = source.read_text(encoding="utf-8")
    try:
        value = yaml.load(text, Loader=_UniqueKeyLoader)
    except yaml.YAMLError as exc:
        raise HarnessRecipeError(f"the catalogue is not valid YAML: {exc}") from exc
    return HarnessRecipeCatalog.from_dict(value, module_directory=module_directory)


@lru_cache(maxsize=1)
def release_recipe_catalog() -> HarnessRecipeCatalog:
    """The catalogue this release ships, with this package folder's modules."""
    return load_recipe_catalog(files("loop_engine").joinpath("data", CATALOG_FILE),
                               module_directory=str(Path(__file__).resolve().parent))


_LOADED: dict = {}


def resolve_recipe_function(catalog: HarnessRecipeCatalog, module: str, function: str):
    """Load one catalogued module from its verified file and return a function.

    The module name must be one the catalogue records, and its bytes must
    match the recorded digest; loading registers nothing."""
    _text(function, _NAME, "function name")
    verified = catalog._verified(module, {function})
    key = (verified.path, verified.sha256)
    if key not in _LOADED:
        name = f"loop_engine_harness_recipe_{module}_{verified.sha256[:16]}"
        spec = importlib.util.spec_from_file_location(name, verified.path)
        loaded = importlib.util.module_from_spec(spec)
        sys.modules[name] = loaded
        try:
            spec.loader.exec_module(loaded)
        except BaseException:
            sys.modules.pop(name, None)
            raise
        _LOADED[key] = loaded
    return getattr(_LOADED[key], function)


def self_test():
    """The catalogue's checks live beside it."""
    from .harness_recipe_catalog_checks import self_test as run_checks
    return run_checks()
