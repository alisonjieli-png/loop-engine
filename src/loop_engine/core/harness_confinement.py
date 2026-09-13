"""The environment a confined harness process sees.

The sandbox clears the host environment and sets exactly the variables
declared here. None of them is a deployment setting: each names a location
inside the sandbox's own filesystem layout (the read-only ``/usr`` bind, the
writable ``/work`` tree), a deterministic text mode for captured output, or
a consent switch that keeps a harness from writing caches, colouring
output, or reporting home. A typed record makes each one an owned,
documented, digest-bound fact: a recipe extends it with its own switches,
an attempt can cite the digest of what it ran under, and the profile can
be declared and varied like any other configuration instead of living as
an anonymous dictionary inside the sandbox argument builder.
"""
from __future__ import annotations

from dataclasses import dataclass, field, fields
import hashlib
import json
from types import MappingProxyType

CONFINED_ENVIRONMENT_RECORD_TYPE = "confined_environment/v1"


class ConfinedEnvironmentError(ValueError):
    """The environment declaration is not a well-formed set of variables."""


def _variable_name(name: str) -> None:
    if (type(name) is not str or not name or name != name.strip()
            or not all(ch.isalnum() or ch == "_" for ch in name) or name[0].isdigit()):
        raise ConfinedEnvironmentError(f"{name!r} is not an environment variable name")


def _variable_value(name: str, value: str) -> None:
    if type(value) is not str or "\0" in value:
        raise ConfinedEnvironmentError(f"{name} needs a text value without NUL")


@dataclass(frozen=True)
class ConfinedEnvironment:
    """Every variable the sandbox sets after clearing the host environment.

    The fixed fields are the sandbox's own layout and modes; ``switches``
    carries the consent variables a particular harness reads, each named by
    the harness's own documented variable. Variable names are unique across
    fields and switches, so a switch cannot silently override a layout
    variable."""

    path: str = "/usr/bin:/bin"
    home: str = "/work/home"
    config_home: str = "/work/home/.config"
    cache_home: str = "/work/home/.cache"
    language: str = "C.UTF-8"
    terminal: str = "dumb"
    no_color: str = "1"
    python_dont_write_bytecode: str = "1"
    do_not_track: str = "1"
    ci: str = "1"
    switches: object = field(default_factory=dict)

    _NAMES = MappingProxyType({
        "path": "PATH", "home": "HOME", "config_home": "XDG_CONFIG_HOME",
        "cache_home": "XDG_CACHE_HOME", "language": "LANG", "terminal": "TERM",
        "no_color": "NO_COLOR", "python_dont_write_bytecode": "PYTHONDONTWRITEBYTECODE",
        "do_not_track": "DO_NOT_TRACK", "ci": "CI"})

    def __post_init__(self):
        for item in fields(self):
            if item.name == "switches":
                continue
            _variable_value(self._NAMES[item.name], getattr(self, item.name))
        if not isinstance(self.switches, dict) and not isinstance(self.switches, MappingProxyType):
            raise ConfinedEnvironmentError("switches must be a mapping of variable names to text")
        switches = {}
        for name, value in dict(self.switches).items():
            _variable_name(name)
            _variable_value(name, value)
            if name in self._NAMES.values():
                raise ConfinedEnvironmentError(f"{name} is a layout variable, not a switch")
            switches[name] = value
        object.__setattr__(self, "switches", MappingProxyType(dict(sorted(switches.items()))))

    def with_switches(self, **switches: str) -> "ConfinedEnvironment":
        """The same layout with more consent switches; a name already set
        must carry the same value, since two owners of one variable would
        make the record ambiguous."""
        merged = dict(self.switches)
        for name, value in switches.items():
            if name in merged and merged[name] != value:
                raise ConfinedEnvironmentError(f"{name} is already set to {merged[name]!r}")
            merged[name] = value
        return ConfinedEnvironment(**{item.name: getattr(self, item.name) for item in fields(self)
                                      if item.name != "switches"}, switches=merged)

    def variables(self) -> dict[str, str]:
        """The complete variable set, layout first, switches after, in a
        stable order."""
        result = {self._NAMES[item.name]: getattr(self, item.name)
                  for item in fields(self) if item.name != "switches"}
        result.update(self.switches)
        return result

    def setenv_arguments(self) -> list[str]:
        """The ``--setenv NAME VALUE`` triples for a sandbox launcher."""
        arguments: list[str] = []
        for name, value in self.variables().items():
            arguments += ["--setenv", name, value]
        return arguments

    def to_dict(self) -> dict:
        return {"record_type": CONFINED_ENVIRONMENT_RECORD_TYPE, "variables": self.variables()}

    @property
    def content_digest(self) -> str:
        serialized = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"),
                                allow_nan=False)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def default_confined_environment() -> ConfinedEnvironment:
    """The environment every brokered text-response harness runs under
    today: the sandbox layout plus the Continue command line's two
    telemetry switches, which the shared sandbox has always set."""
    return ConfinedEnvironment().with_switches(CONTINUE_METRICS_ENABLED="0",
                                               CONTINUE_CLI_ENABLE_TELEMETRY="0")


def self_test() -> dict:
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": str(detail)[:160]})

    environment = default_confined_environment()
    variables = environment.variables()
    check("the_default_environment_is_the_sandbox_layout_plus_the_shared_switches",
          variables == {"PATH": "/usr/bin:/bin", "HOME": "/work/home",
                        "XDG_CONFIG_HOME": "/work/home/.config", "XDG_CACHE_HOME": "/work/home/.cache",
                        "LANG": "C.UTF-8", "TERM": "dumb", "NO_COLOR": "1",
                        "PYTHONDONTWRITEBYTECODE": "1", "DO_NOT_TRACK": "1", "CI": "1",
                        "CONTINUE_CLI_ENABLE_TELEMETRY": "0", "CONTINUE_METRICS_ENABLED": "0"})
    arguments = environment.setenv_arguments()
    check("setenv_arguments_are_name_value_triples_in_variable_order",
          arguments[:3] == ["--setenv", "PATH", "/usr/bin:/bin"]
          and len(arguments) == 3 * len(variables)
          and arguments[1::3] == list(variables) and arguments[2::3] == list(variables.values()))
    extended = environment.with_switches(GPTME_TELEMETRY_ENABLED="false")
    check("a_recipe_extends_the_switches_without_touching_the_layout",
          extended.variables()["GPTME_TELEMETRY_ENABLED"] == "false"
          and extended.path == environment.path
          and extended.content_digest != environment.content_digest
          and environment.variables() == variables)
    for name, operation in (
            ("a_switch_cannot_override_a_layout_variable",
             lambda: environment.with_switches(PATH="/tmp")),
            ("a_switch_cannot_change_its_value_silently",
             lambda: extended.with_switches(GPTME_TELEMETRY_ENABLED="true")),
            ("a_variable_name_must_be_a_name",
             lambda: ConfinedEnvironment(switches={"bad name": "1"})),
            ("a_value_must_be_text",
             lambda: ConfinedEnvironment(switches={"X": 1})),
            ("a_layout_value_must_be_text",
             lambda: ConfinedEnvironment(path=None))):
        try:
            operation()
            check(name, False, "accepted")
        except ConfinedEnvironmentError:
            check(name, True)
    check("the_record_is_portable_and_read_only",
          json.loads(json.dumps(environment.to_dict())) == environment.to_dict()
          and isinstance(environment.switches, MappingProxyType)
          and ConfinedEnvironment().with_switches(CONTINUE_METRICS_ENABLED="0",
                                                  CONTINUE_CLI_ENABLE_TELEMETRY="0").content_digest
          == environment.content_digest)
    return {"module": "core.harness_confinement", "tests": tests,
            "passed": sum(1 for item in tests if item["passed"]), "total": len(tests),
            "all_passed": all(item["passed"] for item in tests)}
