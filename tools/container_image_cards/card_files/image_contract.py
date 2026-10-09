"""Container image contract card: check inputs against contract.json and render the run command, standard library only.

```text
One card (one tag family of one image repository, pinned to its image index digest)
├── contract.json  container_image_contract/v1: the image and its tags, every platform with its manifest and config
│                  digests, the inputs (environment, ports, volumes, command) and outputs the registry states
├── schema.json    the JSON Schema of contract.json; schema_check.py checks one against the other
├── README.md      the card a harness reads first; every line card_lines() returns is in it, in order
└── this module    problems() and notices() check a caller's inputs; render_run() writes the docker or podman
                   run command for them; card_lines() and disagreements() hold README.md to contract.json
```

Usage (prints the command, or each problem and exit status 2):
    python image_contract.py [--platform linux/arm64/v8] [--env NAME=VALUE] [--env NAME] [--publish 8080:80/tcp]
        [--publish-all] [--volume SOURCE:/target[:ro]] [--name NAME] [--user USER] [--entrypoint PATH]
        [--detach] [--interactive] [--keep] [--engine docker|podman] [-- ARGUMENT ...]
In code: problems(contract, ...), notices(contract, ...), render_run(contract, ...), shell_line(argv).

A value for a variable whose name marks it as a credential (PASSWORD, SECRET, TOKEN, ...) is refused: pass the
name alone (--env NAME), so the engine copies it from the caller's environment and it never appears on a command
line, in a log or in a model's context. The functions read no file but main(), which reads contract.json.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import sys
from pathlib import Path

CONTRACT_RECORD = "container_image_contract/v1"
ENGINES = ("docker", "podman")
DEFAULT_ENGINE = ENGINES[0]
TITLE_PREFIX, SECTION_PREFIX, ROW_PREFIX = "# ", "## ", "| "
#: Every README row that starts this way is checked against contract.json.
CHECKED_ROW_PREFIX = "| `"
ENVIRONMENT_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
CONTAINER_NAME = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}")
PLATFORM = re.compile(r"[a-z0-9]+/[a-z0-9_]+(?:/[a-z0-9]+)?")
PUBLISH = re.compile(r"(?:(?:(\[[0-9a-fA-F:.]+\]|[0-9.]+):)?(\d{1,5})?:)?(\d{1,5})(?:/([a-z]+))?")
PROTOCOLS = ("tcp", "udp", "sctp")
DEFAULT_PROTOCOL = PROTOCOLS[0]
READ_ONLY, READ_WRITE = "ro", "rw"
VOLUME_MODES = (READ_ONLY, READ_WRITE)
#: Parts of a variable name that mark a credential: its value is never rendered.
CREDENTIAL_MARKS = ("PASSWORD", "PASSWD", "SECRET", "TOKEN", "CREDENTIAL", "PRIVATE_KEY", "API_KEY", "ACCESS_KEY",
                    "AUTH_KEY", "SALT")
#: The users a config names when the main process runs as root.
ROOT_USERS = ("root", "0", "0:0", "root:root")
#: The compatibility notes a contract may carry, each written as a sentence in README.md.
NOTES = {
    "runs_as_root": "The main process runs as root: the image sets no user, so files it writes to a mounted volume "
                    "belong to root on the host unless `--user` says otherwise.",
    "runs_as_user": "The main process runs as the user the image sets, so a mounted volume must be writable by "
                    "that user.",
    "declares_volumes": "The image declares volumes: without `-v`, the engine creates an anonymous volume for each "
                        "one, and `--rm` removes them when the container is removed.",
    "no_default_command": "The image sets neither an entrypoint nor a default command: give one after the image.",
    "healthcheck_declared": "The image declares a healthcheck: the engine reports the container healthy or "
                            "unhealthy from it.",
    "on_build_triggers": "The image carries ONBUILD triggers: they run in a build that starts FROM it, not when a "
                         "container starts.",
    "windows_containers": "These are Windows container images: they run on a Windows host whose build matches the "
                          "listed os.version (process isolation), or under Hyper-V isolation.",
    "architectures_declared_not_published": "The library declares architectures whose images the index does not "
                                            "list; they are named under Compatibility.",
}
#: What the outputs section says the registry facts mean.
LOGS = "standard_output_and_standard_error"
EXIT_STATUS = "main_process_exit_status"
HEALTH_DECLARED, HEALTH_NOT_DECLARED = "healthcheck_status", "not_declared"
#: The files the registry evidence binds: every card file but the ones written after the check.
UNBOUND_FILES = ("component.json", "ATTRIBUTION.md")
UNBOUND_FOLDER = "verification/"
#: The fields of a platform's runtime, as contract.json and platform_runtime() name them.
RUNTIME_FIELDS = ("entrypoint", "command", "working_dir", "user", "stop_signal", "shell", "healthcheck", "on_build",
                  "labels")
HEALTHCHECK_FIELD = "healthcheck"
#: How a title names the collection an image belongs to.
COLLECTION_LABELS = {"docker_official_images": "Docker Official Image"}
DEFAULT_COLLECTION_LABEL = "container image"


class InputError(ValueError):
    """The inputs given to render_run() break the contract; .problems lists each problem."""

    def __init__(self, problems: list) -> None:
        super().__init__("; ".join(problems))
        self.problems = list(problems)


# -- reading a contract ---------------------------------------------------------------------------------------------
def platforms(contract: dict) -> list:
    """The platforms the image index lists, as --platform names them."""
    return [row["platform"] for row in contract["platforms"]]


def match_platform(contract: dict, requested: str) -> "str | None":
    """The platform a request names: exactly, or by os/architecture when one listed platform has it."""
    names = platforms(contract)
    if requested in names:
        return requested
    found = [name for name in names if name.split("/")[:2] == str(requested).split("/")[:2]
             and len(str(requested).split("/")) == 2]
    return found[0] if len(found) == 1 else None


def platform_runtime(contract: dict, platform: str) -> dict:
    """The runtime one platform's image has: the common runtime with that platform's own differences applied,
    plus its environment (name -> value, None for a withheld value), ports and volumes."""
    row = next((item for item in contract["platforms"] if item["platform"] == platform), None)
    if row is None:
        raise KeyError(f"the image has no platform {platform}")
    differences = row.get("differences") or {}
    own = differences.get("runtime") or {}
    result = {name: own.get(name, contract["runtime"].get(name)) for name in RUNTIME_FIELDS}
    values = {}
    own_values = differences.get("environment") or {}
    for variable in contract["inputs"]["environment"]:
        if not variable["set_by_image"]:
            continue
        if variable["varies_by_platform"]:
            if variable["name"] in own_values:
                values[variable["name"]] = own_values[variable["name"]]
        else:
            values[variable["name"]] = variable["value"]
    result["environment"] = values
    result["ports"] = differences.get("ports", contract["inputs"]["ports"])
    result["volumes"] = differences.get("volumes", contract["inputs"]["volumes"])
    return result


def is_credential_name(name: str) -> bool:
    upper = str(name).upper()
    return any(mark in upper for mark in CREDENTIAL_MARKS)


def _publish_rows(publish) -> list:
    """(address, host port, container port, protocol, text) of each publish request, or a problem string."""
    rows = []
    for item in publish or ():
        if isinstance(item, dict):
            container, host = item.get("container"), item.get("host")
            protocol, address = item.get("protocol") or DEFAULT_PROTOCOL, item.get("address")
            rows.append((address, host, container, protocol, None))
            continue
        match = PUBLISH.fullmatch(str(item))
        if not match:
            rows.append(f"a port to publish is HOST:CONTAINER[/PROTOCOL]: {str(item)[:60]}")
            continue
        address, host, container, protocol = match.groups()
        rows.append((address, int(host) if host else None, int(container), protocol or DEFAULT_PROTOCOL, str(item)))
    return rows


def _volume_rows(volumes) -> list:
    """(source, target, mode) of each volume request, or a problem string."""
    rows = []
    for item in volumes or ():
        if isinstance(item, dict):
            mode = READ_ONLY if item.get("read_only") else READ_WRITE
            rows.append((item.get("source"), item.get("target"), mode))
            continue
        parts = str(item).split(":")
        if len(parts) == 2:
            rows.append((parts[0], parts[1], READ_WRITE))
        elif len(parts) == 3:
            rows.append((parts[0], parts[1], parts[2]))
        else:
            rows.append(f"a volume is SOURCE:TARGET[:ro]: {str(item)[:60]}")
    return rows


def problems(contract: dict, *, platform=None, environment=None, publish=(), volumes=(), command=None,
             entrypoint=None, user=None, name=None) -> list:
    """Every way the inputs break the contract or the engine's own rules; an empty list means they can run."""
    found = []
    if contract.get("record_type") != CONTRACT_RECORD:
        return [f"not a {CONTRACT_RECORD} contract"]
    if platform is not None and match_platform(contract, platform) is None:
        found.append(f"the image has no platform {platform}; it has {', '.join(platforms(contract))}")
    for key, value in sorted((environment or {}).items()):
        if not ENVIRONMENT_NAME.fullmatch(str(key)):
            found.append(f"not an environment variable name: {str(key)[:60]}")
        elif value is not None and not isinstance(value, str):
            found.append(f"the value of {key} is not a string")
        elif value is not None and ("\0" in value or "\n" in value):
            found.append(f"the value of {key} holds a line break or a NUL")
        elif value is not None and is_credential_name(key):
            found.append(f"{key} names a credential: give the name alone so the engine copies it from your "
                         "environment")
    for row in _publish_rows(publish):
        if isinstance(row, str):
            found.append(row)
            continue
        address, host, container, protocol, text = row
        label = text or f"{host}:{container}/{protocol}"
        if type(container) is not int or not 1 <= container <= 65535:
            found.append(f"the container port of {label} is not a port")
        if host is not None and (type(host) is not int or not 1 <= host <= 65535):
            found.append(f"the host port of {label} is not a port")
        if protocol not in PROTOCOLS:
            found.append(f"the protocol of {label} is not one of {', '.join(PROTOCOLS)}")
        if address is not None and not re.fullmatch(r"\[[0-9a-fA-F:.]+\]|[0-9.]+", str(address)):
            found.append(f"the address of {label} is not an IP address")
    for row in _volume_rows(volumes):
        if isinstance(row, str):
            found.append(row)
            continue
        source, target, mode = row
        if not source or not isinstance(source, str):
            found.append("a volume names no source")
        if not isinstance(target, str) or not (target.startswith("/") or re.match(r"[A-Za-z]:\\", target)):
            found.append(f"a volume's target is not an absolute path in the container: {str(target)[:60]}")
        if mode not in VOLUME_MODES:
            found.append(f"a volume's mode is {READ_ONLY} or {READ_WRITE}, not {str(mode)[:20]}")
    if command is not None and (not isinstance(command, (list, tuple)) or
                                any(not isinstance(part, str) for part in command)):
        found.append("the command is a list of strings")
    if entrypoint is not None and (not isinstance(entrypoint, str) or not entrypoint):
        found.append("the entrypoint is one executable path")
    if user is not None and (not isinstance(user, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+(?::[A-Za-z0-9_.-]+)?",
                                                                              user)):
        found.append("the user is NAME, UID or UID:GID")
    if name is not None and not CONTAINER_NAME.fullmatch(str(name)):
        found.append(f"not a container name: {str(name)[:60]}")
    runtime = contract["runtime"]
    if not command and entrypoint is None and not runtime.get("entrypoint") and not runtime.get("command") \
            and "entrypoint" not in (runtime.get("varies_by_platform") or []) \
            and "command" not in (runtime.get("varies_by_platform") or []):
        found.append("the image sets no entrypoint and no default command: give a command")
    return found


def notices(contract: dict, *, environment=None, publish=(), volumes=()) -> list:
    """What the contract does not know about the inputs: a variable the image neither sets nor documents, a port it
    does not expose, a target that is not a declared volume, and a declared volume left unmounted."""
    found = []
    known = {variable["name"] for variable in contract["inputs"]["environment"]}
    for key in sorted(environment or {}):
        if key not in known:
            found.append(f"{key} is neither set by the image nor named by its documentation")
    exposed = {(row["port"], row["protocol"]) for row in contract["inputs"]["ports"]}
    for row in _publish_rows(publish):
        if not isinstance(row, str) and (row[2], row[3]) not in exposed:
            found.append(f"the image does not expose {row[2]}/{row[3]}")
    declared = set(contract["inputs"]["volumes"])
    mounted = {row[1] for row in _volume_rows(volumes) if not isinstance(row, str)}
    for target in sorted(mounted - declared):
        found.append(f"{target} is not a volume the image declares")
    for target in sorted(declared - mounted):
        found.append(f"{target} is a declared volume left unmounted: the engine gives it an anonymous volume")
    return found


def render_run(contract: dict, *, engine: str = DEFAULT_ENGINE, platform=None, environment=None, publish=(),
               publish_all: bool = False, volumes=(), command=None, entrypoint=None, user=None, name=None,
               detach: bool = False, interactive: bool = False, remove: bool = True) -> list:
    """The argument list of `<engine> run` for these inputs, the image pinned by its index digest; raises
    InputError when problems() finds any."""
    found = problems(contract, platform=platform, environment=environment, publish=publish, volumes=volumes,
                     command=command, entrypoint=entrypoint, user=user, name=name)
    if engine not in ENGINES:
        found.append(f"the engine is one of {', '.join(ENGINES)}")
    if found:
        raise InputError(found)
    argv = [engine, "run"]
    if remove:
        argv.append("--rm")
    if detach:
        argv.append("--detach")
    if interactive:
        argv += ["--interactive", "--tty"]
    if name is not None:
        argv += ["--name", name]
    if platform is not None:
        argv += ["--platform", match_platform(contract, platform)]
    for key, value in sorted((environment or {}).items()):
        argv += ["--env", key if value is None else f"{key}={value}"]
    if publish_all:
        argv.append("--publish-all")
    for address, host, container, protocol, _text in _publish_rows(publish):
        spec = f"{'' if host is None else host}:{container}/{protocol}"
        if address is not None:
            spec = f"{address}:{spec}"
        elif host is None:
            spec = f"{container}/{protocol}"
        argv += ["--publish", spec]
    for source, target, mode in _volume_rows(volumes):
        argv += ["--volume", f"{source}:{target}" + (f":{READ_ONLY}" if mode == READ_ONLY else "")]
    if user is not None:
        argv += ["--user", user]
    if entrypoint is not None:
        argv += ["--entrypoint", entrypoint]
    argv.append(contract["image"]["reference"])
    return argv + list(command or [])


def shell_line(argv) -> str:
    """The argument list as one POSIX shell command line."""
    return " ".join(shlex.quote(str(part)) for part in argv)


def default_run(contract: dict) -> list:
    """The command README.md shows: the default platform, every exposed port published to a free host port."""
    return render_run(contract, publish_all=bool(contract["inputs"]["ports"]))


# -- the README lines a card checks ----------------------------------------------------------------------------------
def code(text) -> str:
    """Text as a Markdown code span: longer backtick fences than any run inside, and characters a renderer would
    hide or break a line on written visibly."""
    text = "".join(character if character.isprintable() or character == " " else
                   "\\u{:04x}".format(ord(character)) for character in str(text))
    runs = [len(run) for run in re.findall(r"`+", text)]
    fence = "`" * (max(runs, default=0) + 1)
    pad = " " if runs or text.startswith("`") or text.endswith("`") else ""
    return f"{fence}{pad}{text}{pad}{fence}"


def cell(text) -> str:
    """A code span inside a table row: the cell separator escaped, as GitHub's tables read it."""
    return code(text).replace("|", "\\|")


def compact(value) -> str:
    """A list or an object written as compact JSON, the way a config states it."""
    return json.dumps(value, ensure_ascii=False, separators=(", ", ": "))


def title_line(contract: dict) -> str:
    image = contract["image"]
    label = COLLECTION_LABELS.get(image.get("collection"), DEFAULT_COLLECTION_LABEL)
    return f"{TITLE_PREFIX}{image['name']}:{image['resolved_tag']} ({label})"


def _varies(contract: dict, field: str) -> bool:
    return field in (contract["runtime"].get("varies_by_platform") or [])


def _runtime_value(contract: dict, field: str, absent: str) -> str:
    if _varies(contract, field):
        return "varies by platform (see Platform differences)"
    value = contract["runtime"].get(field)
    if value is None or value == [] or value == {}:
        return absent
    return code(compact(value) if isinstance(value, (list, dict)) else value)


def healthcheck_text(value, span=None) -> str:
    """A healthcheck as a line says it: its test as a code span, then its timings and retries."""
    if not value:
        return "none declared"
    parts = [(span or code)(compact(value["test"]))]
    for key in ("interval_ns", "timeout_ns", "start_period_ns", "start_interval_ns"):
        if value.get(key):
            parts.append(f"{key[:-3].replace('_', ' ')} {value[key] / 1e9:g} s")
    if value.get("retries"):
        parts.append(f"retries {value['retries']}")
    return ", ".join(parts)


def runtime_lines(contract: dict) -> list:
    runtime = contract["runtime"]
    lines = [f"Entrypoint: {_runtime_value(contract, 'entrypoint', 'none')}",
             f"Default command: {_runtime_value(contract, 'command', 'none')}",
             f"Working directory: {_runtime_value(contract, 'working_dir', 'not set (/)')}",
             f"User: {_runtime_value(contract, 'user', 'not set (root)')}",
             f"Stop signal: {_runtime_value(contract, 'stop_signal', 'not set (SIGTERM)')}"]
    if _varies(contract, HEALTHCHECK_FIELD):
        lines.append("Healthcheck: varies by platform (see Platform differences)")
    else:
        lines.append(f"Healthcheck: {healthcheck_text(runtime.get('healthcheck'))}")
    return lines


def environment_rows(contract: dict) -> list:
    rows = []
    for variable in contract["inputs"]["environment"]:
        if not variable["set_by_image"]:
            value = "not set"
        elif variable["withheld"]:
            value = "withheld (a credential name)"
        elif variable["varies_by_platform"]:
            value = "varies by platform"
        else:
            value = cell(variable["value"]) if variable["value"] else "empty"
        where = ", ".join(label for flag, label in ((variable["set_by_image"], "image"),
                                                    (variable["documented"], "documentation")) if flag)
        rows.append(f"{CHECKED_ROW_PREFIX}{variable['name']}` | {value} | {where} |")
    return rows


def port_rows(contract: dict) -> list:
    return [f"{CHECKED_ROW_PREFIX}{row['port']}/{row['protocol']}` | exposed |" for row in contract["inputs"]["ports"]]


def volume_rows(contract: dict) -> list:
    return [f"{CHECKED_ROW_PREFIX}{path}` | declared volume |" for path in contract["inputs"]["volumes"]]


def size_text(count: int) -> str:
    return f"{count:,} bytes"


def platform_rows(contract: dict) -> list:
    rows = []
    for row in contract["platforms"]:
        version = f" {row['os_version']}" if row.get("os_version") else ""
        rows.append(f"{CHECKED_ROW_PREFIX}{row['platform']}`{version} | `{row['manifest']['digest']}` | "
                    f"`{row['config']['digest']}` | {size_text(row['compressed_bytes'])} | {row['layers']} |")
    return rows


def difference_rows(contract: dict) -> list:
    rows = []
    for row in contract["platforms"]:
        differences = row.get("differences") or {}
        for field, value in sorted((differences.get("runtime") or {}).items()):
            shown = healthcheck_text(value, cell) if field == HEALTHCHECK_FIELD else (
                cell(compact(value)) if isinstance(value, (list, dict)) else cell(value) if value else "not set")
            rows.append(f"{CHECKED_ROW_PREFIX}{row['platform']}` | {field} | {shown} |")
        for key, value in sorted((differences.get("environment") or {}).items()):
            rows.append(f"{CHECKED_ROW_PREFIX}{row['platform']}` | environment {key} | "
                        f"{cell(value) if value else 'withheld or empty'} |")
        for field in ("ports", "volumes"):
            if field in differences:
                shown = ", ".join(f"{item['port']}/{item['protocol']}" if field == "ports" else item
                                  for item in differences[field]) or "none"
                rows.append(f"{CHECKED_ROW_PREFIX}{row['platform']}` | {field} | {cell(shown)} |")
    return rows


def card_lines(contract: dict) -> list:
    """Every line README.md holds verbatim, in order: written from contract.json, so a card agrees with its contract
    exactly when disagreements() finds nothing."""
    image = contract["image"]
    lines = [title_line(contract), f"Image: `{image['reference']}`",
             "Tags: " + ", ".join(code(tag) for tag in image["tags"]),
             "Shared tags: " + (", ".join(code(tag) for tag in image["shared_tags"]) or "none"),
             f"Platforms: {len(contract['platforms'])} (" + ", ".join(code(name) for name in platforms(contract)) + ")",
             shell_line(default_run(contract))]
    lines += runtime_lines(contract)
    lines += environment_rows(contract) + port_rows(contract) + volume_rows(contract)
    lines += platform_rows(contract) + difference_rows(contract)
    lines += [f"- {NOTES[note]}" for note in contract["compatibility"]["notes"]]
    return lines


def disagreements(contract: dict, text: str) -> list:
    """Each line card_lines() expects that README.md lacks or holds out of order, and each checked row README.md
    holds that the contract does not."""
    lines = text.split("\n")
    expected = card_lines(contract)
    found, position = [], 0
    for line in expected:
        try:
            position = lines.index(line, position) + 1
        except ValueError:
            found.append(f"missing or out of order: {line[:160]}")
    wanted = set(expected)
    for line in lines:
        if line.startswith(CHECKED_ROW_PREFIX) and line not in wanted:
            found.append(f"not in contract.json: {line[:160]}")
    return found


def card_digest(files: dict) -> str:
    """The digest the registry evidence binds: every card file's path and SHA-256 but component.json, the
    attribution and the verification records, which are written after the check."""
    rows = sorted((path, hashlib.sha256(data).hexdigest()) for path, data in files.items()
                  if path not in UNBOUND_FILES and not path.startswith(UNBOUND_FOLDER))
    return hashlib.sha256(json.dumps(rows).encode("utf-8")).hexdigest()


# -- command line ---------------------------------------------------------------------------------------------------
def _environment(values) -> dict:
    found = {}
    for item in values or ():
        key, separator, value = item.partition("=")
        found[key] = value if separator else None
    return found


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Print the run command of this card's image for these inputs.")
    parser.add_argument("--contract", default=str(Path(__file__).with_name("contract.json")))
    parser.add_argument("--engine", choices=ENGINES, default=DEFAULT_ENGINE)
    parser.add_argument("--platform")
    parser.add_argument("--env", action="append", default=[], help="NAME=VALUE, or NAME to copy it from your "
                                                                     "environment (required for a credential)")
    parser.add_argument("--publish", action="append", default=[], help="HOST:CONTAINER[/PROTOCOL]")
    parser.add_argument("--publish-all", action="store_true")
    parser.add_argument("--volume", action="append", default=[], help="SOURCE:TARGET[:ro]")
    parser.add_argument("--name")
    parser.add_argument("--user")
    parser.add_argument("--entrypoint")
    parser.add_argument("--detach", action="store_true")
    parser.add_argument("--interactive", action="store_true")
    parser.add_argument("--keep", action="store_true", help="keep the container after it exits (no --rm)")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    options = parser.parse_args(argv)
    contract = json.loads(Path(options.contract).read_text(encoding="utf-8"))
    command = options.command[1:] if options.command[:1] == ["--"] else options.command
    environment = _environment(options.env)
    try:
        argv = render_run(contract, engine=options.engine, platform=options.platform, environment=environment,
                          publish=options.publish, publish_all=options.publish_all, volumes=options.volume,
                          command=command or None, entrypoint=options.entrypoint, user=options.user,
                          name=options.name, detach=options.detach, interactive=options.interactive,
                          remove=not options.keep)
    except InputError as error:
        for problem in error.problems:
            print(f"problem: {problem}", file=sys.stderr)
        return 2
    for notice in notices(contract, environment=environment, publish=options.publish, volumes=options.volume):
        print(f"notice: {notice}", file=sys.stderr)
    print(shell_line(argv))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
