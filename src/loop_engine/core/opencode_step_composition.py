"""Compose one OpenCode instance per cognitive step from two layers.

A step's OpenCode instance is built from a CORE layer that is identical on
every step of every run, and a STEP layer chosen when the instance is
created. The split is the point: the core carries what must never vary --
the response contract, the refusal rules, the safety posture -- and the step
layer carries what should vary, because an orient step and a verify step
want different tools, different skills and different permissions.

WHY COMPOSE A DIRECTORY RATHER THAN PASS FLAGS
OpenCode discovers agents, skills, commands and plugins from a ``.opencode``
tree next to the working directory. Composing that tree gives per-step
control over the whole surface -- including tool permissions, which have no
command-line form -- and leaves an artifact a human can read after the run
to see exactly what the step was given. A flag-only instance would be
unauditable and could not carry skills at all.

WHAT MAKES THE CORE ACTUALLY CORE
``CoreLayer.digest`` is computed over every core file's path and bytes. The
composer records it into the manifest of every instance it builds, and
``verify_core_unchanged`` recomputes it. A core that drifts between steps is
therefore detectable rather than merely promised, which matters because the
core is where the invariants live: if it can be edited per step without
anyone noticing, it is not an invariant, it is a default.

TRUST DIRECTION
Step layers are selected by the engine from a registered catalogue keyed by
step id. A model never names a file to write into the instance, because a
model that could compose its own instance could grant itself tools and lift
its own permissions. Selection is engine authority; the model's influence is
the task text that selection reads.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from collections.abc import Mapping
from types import MappingProxyType

#: Tool names OpenCode understands in an agent's ``tools`` mapping. Naming
#: an unknown tool is refused at composition rather than discovered as a
#: silently ignored line in a generated agent file.
KNOWN_TOOLS = (
    "bash", "edit", "write", "read", "grep", "glob", "list",
    "patch", "todowrite", "todoread", "webfetch", "task", "skill")

#: Every tool that can reach the filesystem, directly or by delegation.
#: A read-only step must switch off ALL of these, not the obvious ones.
#: Measured twice on live runs: with edit/write off but bash on, the model
#: ran `sed -i` and the file changed; with bash also off but `task` left
#: on, it reported "used a general agent task to execute sed -i" and the
#: file changed again -- a subagent inherits the DEFAULT agent, not the
#: composed layer, so `task` hands back every tool this layer removed.
WRITE_CAPABLE_TOOLS = ("bash", "edit", "write", "patch", "task")

#: The complete read-only tool map. Named once so a step cannot be
#: read-only in three of five respects, which is what shipped before.
READ_ONLY_TOOLS = {
    "read": True, "grep": True, "glob": True, "list": True,
    "bash": False, "edit": False, "write": False, "patch": False,
    "task": False,
}


def read_only_tools(**allow) -> dict:
    """Read-only tools, optionally re-enabling named write-capable ones.

    Re-enabling is explicit and visible at the call site, so a step that
    needs a shell says so where a reviewer will see it rather than by
    omitting a key.
    """
    tools = dict(READ_ONLY_TOOLS)
    for name, value in allow.items():
        if name not in KNOWN_TOOLS:
            raise OpenCodeCompositionError(
                f"unknown tool {name!r}; known tools are "
                f"{', '.join(KNOWN_TOOLS)}")
        if not isinstance(value, bool):
            raise OpenCodeCompositionError(
                f"tool {name!r} must be True or False, not {value!r}; the "
                "string 'false' is true in a truth test and would enable it")
        tools[name] = value
    return tools


#: Paths an implement step may not edit unless a caller says otherwise.
#: Found live, twice: given a test it could not make pass by changing the
#: code, the model changed the test -- once by correcting an expectation
#: that was genuinely wrong, once by mocking `urlopen` so an integration
#: test no longer tested the integration. The gate went green both times.
#: Denying edits to test paths turns the second case into the honest
#: answer: the step cannot make the gate pass and must say what it is
#: blocked on. Correcting a wrong expectation becomes a decision a human
#: makes in the morning, with the evidence in front of them.
TEST_PATH_GLOBS = ("**/test_*", "**/*_test.*", "**/tests/**", "**/test/**",
                   "**/*.test.*", "**/*.spec.*", "**/spec/**",
                   "**/__tests__/**", "**/conftest.py")


def source_only_edit_permission() -> dict:
    """An edit rule that allows source and denies tests."""
    # OpenCode evaluates the last matching rule. Preserve that order all
    # the way into the native configuration, including custom patterns.
    return {"*": "allow", **{glob: "deny" for glob in TEST_PATH_GLOBS}}


#: Permission verbs OpenCode accepts. "ask" is refused for unattended steps
#: by ``StepLayer.__post_init__`` -- a prompt nobody is awake to answer is a
#: hang, not a safeguard.
PERMISSION_VERBS = ("allow", "deny", "ask")


class OpenCodeCompositionError(ValueError):
    """A layer, catalogue entry, or composed instance violated its contract."""


class ForeignOpenCodeTreeError(OpenCodeCompositionError):
    """A ``.opencode`` tree this composer did not build is in the way."""


#: The manifest record type that marks a ``.opencode`` tree as one of ours,
#: and therefore disposable. Anything else under that name is somebody's
#: own configuration.
INSTANCE_RECORD_TYPE = "opencode_step_instance/v1"


def _composed_by_this_engine(config_root: Path) -> bool:
    """True only for a tree carrying this composer's own manifest."""
    manifest = config_root / "instance-manifest.json"
    if not manifest.is_file():
        return False
    try:
        record = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return (isinstance(record, dict)
            and record.get("record_type") == INSTANCE_RECORD_TYPE)


def _confined_path(root: Path, relative, *, purpose: str) -> Path:
    """Resolve a materialization target strictly inside ``root``.

    Absolute paths, ``..`` components, empty names and any path that
    resolves (through an existing symlink) outside the root are refused
    before a byte is written. A context file that could land outside the
    workspace, or inside the instance directory, would let a layer rewrite
    what the manifest claims about it.
    """
    text = str(relative)
    parts = Path(text).parts
    if (not text.strip() or not parts or Path(text).is_absolute()
            or ".." in parts):
        raise OpenCodeCompositionError(
            f"{purpose} path {text!r} must be a relative path with no '..'")
    resolved_root = root.resolve()
    target = root / text
    for component in (target, *target.parents):
        if component == root:
            break
        if component.is_symlink():
            raise OpenCodeCompositionError(
                f"{purpose} path {text!r} contains a symlink")
    target = target.resolve()
    try:
        target.relative_to(resolved_root)
    except ValueError:
        raise OpenCodeCompositionError(
            f"{purpose} path {text!r} resolves to {target}, outside "
            f"{resolved_root}") from None
    return target


def _write_bytes(target: Path, payload: bytes) -> None:
    """Write through a real path only; a symlink at the name is an error."""
    target.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0)
    with os.fdopen(os.open(str(target), flags, 0o644), "wb") as stream:
        stream.write(payload)


def _digest_tree(files: dict) -> str:
    """Digest a path -> bytes mapping, path-ordered so it is reproducible."""
    hasher = hashlib.sha256()
    for relative in sorted(files):
        hasher.update(relative.encode("utf-8"))
        hasher.update(b"\0")
        hasher.update(files[relative])
        hasher.update(b"\0")
    return hasher.hexdigest()


def _relative_files(root: Path) -> dict:
    """Read a directory into a path -> bytes mapping, symlinks refused."""
    files = {}
    if not root.is_dir():
        raise OpenCodeCompositionError(f"layer directory {root} does not exist")
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise OpenCodeCompositionError(
                f"layer file {path} is a symlink; a composed instance must "
                "carry its own bytes so its digest describes what ran")
        if path.is_file():
            files[str(path.relative_to(root))] = path.read_bytes()
    return files


@dataclass(frozen=True)
class CoreLayer:
    """Files every step instance receives, and the digest that pins them."""

    files: dict = field(default_factory=dict)
    digest: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "files", MappingProxyType(dict(self.files)))

    @classmethod
    def from_directory(cls, root) -> "CoreLayer":
        files = _relative_files(Path(root))
        return cls(files=files, digest=_digest_tree(files))

    @classmethod
    def from_mapping(cls, files: dict) -> "CoreLayer":
        encoded = {
            str(key): (value if isinstance(value, bytes)
                       else str(value).encode("utf-8"))
            for key, value in files.items()}
        return cls(files=encoded, digest=_digest_tree(encoded))

    def verify_core_unchanged(self) -> bool:
        return self.digest == _digest_tree(self.files)


@dataclass(frozen=True)
class StepLayer:
    """One cognitive step's own agent, skills, tools and permissions."""

    step_id: str
    description: str
    system_prompt: str
    #: Tool name -> bool. Absent tools are left to OpenCode's default; the
    #: point of naming them is to switch a tool OFF for a step that has no
    #: business using it, which is how an orient step is kept read-only.
    tools: dict = field(default_factory=dict)
    #: Permission verb per class, e.g. {"edit": "deny", "bash": "deny"}.
    permission: dict = field(default_factory=dict)
    #: Skill directories carried only by this step: name -> SKILL.md text.
    skills: dict = field(default_factory=dict)
    #: Extra context files written under the workspace, e.g. AGENTS.md.
    context_files: dict = field(default_factory=dict)
    model: str = ""
    unattended: bool = True

    def __post_init__(self) -> None:
        if not self.step_id.strip():
            raise OpenCodeCompositionError("a step layer must name its step")
        if not self.system_prompt.strip():
            raise OpenCodeCompositionError(
                f"step {self.step_id!r} must carry a system prompt; an agent "
                "file with an empty body silently inherits the default agent")
        for name, value in self.tools.items():
            if name not in KNOWN_TOOLS:
                raise OpenCodeCompositionError(
                    f"step {self.step_id!r} names unknown tool {name!r}; "
                    f"known tools are {', '.join(KNOWN_TOOLS)}")
            # Real Booleans only. Observed: the string "false" enabled a
            # tool, because a truth test on text reads it as true.
            if not isinstance(value, bool):
                raise OpenCodeCompositionError(
                    f"step {self.step_id!r} sets tool {name!r} to {value!r}; "
                    "a tool flag must be True or False, since text, numbers "
                    "and None are read as truth values and 'false' would "
                    "enable the tool")
        if not isinstance(self.unattended, bool):
            raise OpenCodeCompositionError(
                f"step {self.step_id!r} unattended must be True or False, "
                f"not {self.unattended!r}")
        for klass, rule in self.permission.items():
            # A rule is one verb, or a {glob: verb} object. The object form
            # is what lets a step edit source but not tests: OpenCode
            # resolves patterns per path, so "tests/**": "deny" holds at
            # the tool layer, which is the layer observed to hold.
            verbs = (rule.values() if isinstance(rule, Mapping) else (rule,))
            if isinstance(rule, Mapping) and not rule:
                raise OpenCodeCompositionError(
                    f"step {self.step_id!r} permission {klass!r} is an empty "
                    "object; name at least one pattern")
            for verb in verbs:
                if verb not in PERMISSION_VERBS:
                    raise OpenCodeCompositionError(
                        f"step {self.step_id!r} permission {klass!r} is "
                        f"{verb!r}; must be one of {', '.join(PERMISSION_VERBS)}")
                if verb == "ask" and self.unattended:
                    raise OpenCodeCompositionError(
                        f"step {self.step_id!r} sets {klass!r} to 'ask' while "
                        "unattended; nobody is awake to answer, so this hangs "
                        "the run -- use 'allow' or 'deny'")
        for name in ("tools", "skills", "context_files"):
            object.__setattr__(self, name, MappingProxyType(dict(getattr(self, name))))
        object.__setattr__(self, "permission", MappingProxyType({
            key: MappingProxyType(dict(rule)) if isinstance(rule, Mapping) else rule
            for key, rule in self.permission.items()}))

    def agent_markdown(self) -> str:
        """Render the agent file OpenCode reads for this step."""
        # JSON strings are valid YAML scalars. Quoting prevents descriptive
        # text or a permission pattern from injecting another native field.
        quote = json.dumps
        lines = ["---", f"description: {quote(self.description)}", "mode: primary"]
        if self.model:
            lines.append(f"model: {quote(self.model)}")
        if self.tools:
            lines.append("tools:")
            for name in sorted(self.tools):
                lines.append(f"  {name}: {str(self.tools[name]).lower()}")
        if self.permission:
            lines.append("permission:")
            for klass in self.permission:
                rule = self.permission[klass]
                if isinstance(rule, Mapping):
                    lines.append(f"  {quote(klass)}:")
                    for pattern in rule:
                        lines.append(f"    {quote(pattern)}: {rule[pattern]}")
                else:
                    lines.append(f"  {quote(klass)}: {rule}")
        lines += ["---", "", self.system_prompt.strip(), ""]
        return "\n".join(lines)


@dataclass(frozen=True)
class ComposedInstance:
    """A materialized instance plus the manifest describing what it is."""

    workspace: Path
    agent_name: str
    manifest: dict

    @property
    def config_root(self) -> Path:
        return self.workspace / ".opencode"


class StepLayerCatalogue:
    """Engine-owned mapping from step id to that step's layer.

    Registration is explicit and duplicate ids are refused, so two
    definitions of "verify" cannot silently shadow each other and leave the
    run using whichever was imported last.
    """

    def __init__(self, layers=()):
        self._layers = {}
        for layer in layers:
            self.register(layer)

    def register(self, layer: StepLayer) -> None:
        if not isinstance(layer, StepLayer):
            raise OpenCodeCompositionError("catalogue holds StepLayer values")
        if layer.step_id in self._layers:
            raise OpenCodeCompositionError(
                f"step {layer.step_id!r} is already registered")
        self._layers[layer.step_id] = layer

    def has(self, step_id: str) -> bool:
        return step_id in self._layers

    def select(self, step_id: str) -> StepLayer:
        if step_id not in self._layers:
            raise OpenCodeCompositionError(
                f"no step layer for {step_id!r}; registered steps are "
                f"{', '.join(sorted(self._layers)) or '(none)'}")
        return self._layers[step_id]

    def registered(self) -> tuple:
        return tuple(sorted(self._layers))


@dataclass(frozen=True)
class SkillCandidate:
    """One optional skill and the evidence that would justify carrying it."""

    name: str
    body: str
    #: Lowercase terms whose presence in the task text admits this skill.
    #: Terms are matched against the task, never against model output: a
    #: model that could trigger its own skills could grant itself tools.
    triggers: tuple = ()
    #: Steps this skill is eligible for at all. Empty means any step.
    steps: tuple = ()

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise OpenCodeCompositionError("a skill candidate must be named")
        if "/" in self.name or self.name.strip() != self.name:
            raise OpenCodeCompositionError(
                f"skill name {self.name!r} must be one path segment with no "
                "slashes; it becomes a directory under skill/")
        if not self.body.strip():
            raise OpenCodeCompositionError(
                f"skill {self.name!r} has an empty body; an empty SKILL.md "
                "is carried, indexed, and says nothing")
        if not self.triggers:
            raise OpenCodeCompositionError(
                f"skill {self.name!r} declares no triggers, so it would "
                "either always load or never load; say which")

    def admits(self, step_id: str, task: str) -> bool:
        if self.steps and step_id not in self.steps:
            return False
        return self.matched_term(step_id, task) is not None

    def matched_term(self, step_id: str, task: str) -> "str | None":
        """The trigger this task matched, or None.

        Matching is on WORD BOUNDARIES, not substrings. Observed on a real
        run: the trigger "error" matched inside "ValueError" and pulled a
        debugging skill into a task that was creating a function from
        scratch. A substring trigger fires on the spelling of unrelated
        words, and every wrongly-carried skill costs prompt budget on every
        call the instance makes.
        """
        if self.steps and step_id not in self.steps:
            return None
        for term in self.triggers:
            pattern = r"\b" + re.escape(term).replace(r"\ ", r"\s+") + r"\b"
            if re.search(pattern, task, re.IGNORECASE):
                return term
        return None


class SkillLibrary:
    """Optional skills, selected per instantiation from task evidence.

    Selection is deterministic and engine-owned. The same task and step
    always produce the same skill set, which is what makes a composed
    instance reproducible from its manifest -- and the manifest records the
    matched trigger for each skill, so "why was this skill here" has an
    answer after the run rather than a guess.
    """

    def __init__(self, candidates=()):
        self._candidates = {}
        for candidate in candidates:
            self.register(candidate)

    def register(self, candidate: SkillCandidate) -> None:
        if not isinstance(candidate, SkillCandidate):
            raise OpenCodeCompositionError("library holds SkillCandidate values")
        if candidate.name in self._candidates:
            raise OpenCodeCompositionError(
                f"skill {candidate.name!r} is already registered")
        self._candidates[candidate.name] = candidate

    def available(self) -> tuple:
        return tuple(sorted(self._candidates))

    def select(self, step_id: str, task: str, *, limit: int = 4) -> dict:
        """Return name -> (body, matched trigger) for admitted skills.

        Ordered by name, then truncated, so a task that admits more skills
        than the limit drops a stable set rather than a different one each
        run. ``limit`` exists because every carried skill costs prompt
        budget on every call the instance makes.
        """
        # An integer, honored exactly: zero means none. Observed: a limit
        # of zero selected one skill, because the cut was checked after
        # the first admission rather than before it.
        if isinstance(limit, bool) or not isinstance(limit, int):
            raise OpenCodeCompositionError(
                f"limit must be an integer, not {limit!r}")
        if limit < 0:
            raise OpenCodeCompositionError("limit cannot be negative")
        chosen = {}
        for name in sorted(self._candidates):
            if len(chosen) >= limit:
                break
            candidate = self._candidates[name]
            matched = candidate.matched_term(step_id, task)
            if matched is None:
                continue
            chosen[name] = (candidate.body, matched)
        return chosen


def dynamic_step_layer(base: StepLayer, task: str, library: SkillLibrary,
                       *, limit: int = 4) -> tuple:
    """Specialize one step layer for one task; return (layer, selection).

    The base layer's own skills are kept and always win: a step's fixed
    skills are part of what that step IS, and a task-triggered skill that
    could displace one would make the step's identity depend on wording.
    """
    selected = library.select(base.step_id, task, limit=limit)
    merged = dict(base.skills)
    provenance = {}
    for name, (body, matched) in selected.items():
        if name in merged:
            provenance[name] = f"step (task term {matched!r} also matched)"
            continue
        merged[name] = body
        provenance[name] = f"task term {matched!r}"
    layer = StepLayer(
        step_id=base.step_id, description=base.description,
        system_prompt=base.system_prompt, tools=dict(base.tools),
        permission=dict(base.permission), skills=merged,
        context_files=dict(base.context_files), model=base.model,
        unattended=base.unattended)
    return layer, provenance






def compose_instance(core: CoreLayer, step: StepLayer, workspace, *,
                     replace_existing: bool = False) -> ComposedInstance:
    """Materialize ``.opencode`` for one step and return its manifest.

    The core is written first and the step second, and a step file that
    would overwrite a core file is refused rather than silently winning.
    Layering that lets the variable half quietly replace the fixed half
    gives an invariant that holds only until something needs it not to.

    An existing ``.opencode`` tree is replaced only when it carries this
    composer's own manifest: a per-step instance is disposable, a project's
    own configuration is not. Anything else raises
    ``ForeignOpenCodeTreeError`` unless ``replace_existing`` says the
    caller has decided to lose it.

    Every path is confined to the workspace before anything is written, a
    context file may not touch the instance directory, and the manifest
    records the digest of each file as written, so it describes the tree
    that exists rather than the settings that were requested.
    """
    if not core.verify_core_unchanged():
        raise OpenCodeCompositionError(
            "core layer bytes no longer match the digest recorded for them")
    root = Path(workspace)
    config_root = root / ".opencode"
    if type(replace_existing) is not bool:
        raise OpenCodeCompositionError("replace_existing must be a Boolean")
    # Refuse before resolving any target or reading a foreign manifest.
    # Resolving through this link and unlinking it later leaves a write
    # plan pointing outside the workspace, even with explicit replacement.
    if config_root.is_symlink():
        raise OpenCodeCompositionError(".opencode must not be a symlink")
    if config_root.exists() and not config_root.is_dir():
        raise ForeignOpenCodeTreeError(".opencode exists and is not a directory")

    agent_name = f"step-{step.step_id}"
    step_files = {f"agent/{agent_name}.md": step.agent_markdown().encode("utf-8")}
    for name, text in step.skills.items():
        step_files[f"skill/{name}/SKILL.md"] = (
            text if isinstance(text, bytes) else str(text).encode("utf-8"))

    collisions = sorted(set(step_files) & set(core.files))
    if collisions:
        raise OpenCodeCompositionError(
            f"step {step.step_id!r} would overwrite core files {collisions}; "
            "rename the step's file -- the core layer is not overridable")

    # Every target is confined before the first write, so a refused path
    # leaves no half-built instance behind.
    plan = {}
    reserved = config_root.resolve() / "instance-manifest.json"
    for relative in list(core.files) + list(step_files):
        target = _confined_path(
            config_root, relative, purpose="instance file")
        if target == reserved or target in plan.values():
            raise OpenCodeCompositionError(
                f"instance file {relative!r} aliases another or reserved file")
        plan[f".opencode/{relative}"] = target
    instance_root = config_root.resolve()
    for relative in step.context_files:
        target = _confined_path(root, relative, purpose="context file")
        key = str(Path(str(relative)))
        inside_instance = target == instance_root or instance_root in target.parents
        if key in plan or target in plan.values() or inside_instance:
            raise OpenCodeCompositionError(
                f"context file {relative!r} would land on a file the composer "
                "writes itself, or inside the instance directory; the "
                "composer alone writes .opencode, and a context file there "
                "would change what the manifest claims")
        plan[key] = target

    if config_root.exists() or config_root.is_symlink():
        if not (_composed_by_this_engine(config_root) or replace_existing):
            raise ForeignOpenCodeTreeError(
                f"{config_root} exists and carries no instance-manifest.json "
                f"of record_type {INSTANCE_RECORD_TYPE!r}; it looks like the "
                "project's own configuration. Pass replace_existing=True to "
                "replace it deliberately, or compose into another workspace")
        if config_root.is_symlink():
            config_root.unlink()
        else:
            shutil.rmtree(config_root)
    root.mkdir(parents=True, exist_ok=True)
    written = {}

    for relative, payload in core.files.items():
        _write_bytes(plan[f".opencode/{relative}"], payload)
        written[relative] = "core"
    for relative, payload in step_files.items():
        _write_bytes(plan[f".opencode/{relative}"], payload)
        written[relative] = "step"
    for relative, text in step.context_files.items():
        _write_bytes(plan[str(Path(str(relative)))],
                     text if isinstance(text, bytes) else str(text).encode("utf-8"))
    materialized = {key: hashlib.sha256(path.read_bytes()).hexdigest()
                    for key, path in sorted(plan.items())}

    manifest = {
        "record_type": INSTANCE_RECORD_TYPE,
        "step_id": step.step_id,
        "agent_name": agent_name,
        "core_digest": core.digest,
        "core_file_count": len(core.files),
        "step_file_count": len(step_files),
        "composed_digest": _digest_tree({**core.files, **step_files}),
        "tools": dict(sorted(step.tools.items())),
        "permission": {key: dict(rule) if isinstance(rule, Mapping) else rule
                       for key, rule in step.permission.items()},
        "skills": sorted(step.skills),
        "skill_count": len(step.skills),
        "context_files": sorted(step.context_files),
        "provenance": dict(sorted(written.items())),
        #: What is on disk, path -> sha256 of the bytes as written, read
        #: back after writing. The settings above are what was requested;
        #: this is what exists.
        "materialized": materialized,
    }
    (config_root / "instance-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return ComposedInstance(
        workspace=root, agent_name=agent_name, manifest=manifest)












@dataclass(frozen=True)
class AdmissionOutcome:
    """What the engine granted, refused, and why -- for the run record."""

    granted: dict
    refused: tuple
    dropped_without_use: tuple
    available: tuple

    def refusal_message(self) -> str:
        """A refusal that states the legal set rather than only the error.

        The rule this obeys was already written in this codebase and applied
        once: a closed vocabulary refused without stating itself leaves the
        next attempt to guess again. Every refusal built here names what
        WOULD have been accepted.
        """
        if not self.refused and not self.dropped_without_use:
            return ""
        parts = []
        if self.refused:
            parts.append(
                f"not registered: {', '.join(self.refused)}; "
                f"available skills are {', '.join(self.available) or '(none)'}")
        if self.dropped_without_use:
            parts.append(
                "requested without saying what it would be used for, so "
                f"dropped: {', '.join(self.dropped_without_use)}")
        return "; ".join(parts)


def admit_requests(requests, library: "SkillLibrary") -> AdmissionOutcome:
    """Engine-side answer to a requirements step. The model never grants.

    ``requests`` is what the model returned: either a list of names, or a
    mapping of name -> stated use. A name with no stated use is dropped
    rather than granted, because a request for everything costs budget on
    every later call and carries no information about the task.
    """
    if isinstance(requests, dict):
        pairs = [(str(k), str(v or "")) for k, v in requests.items()]
    else:
        pairs = [(str(item), "") for item in (requests or ())]
    available = library.available()
    granted, refused, dropped = {}, [], []
    for name, use in pairs:
        cleaned = name.strip()
        if not cleaned:
            continue
        if cleaned not in available:
            refused.append(cleaned)
            continue
        if not use.strip():
            dropped.append(cleaned)
            continue
        candidate = library._candidates[cleaned]   # noqa: SLF001
        granted[cleaned] = candidate.body
    return AdmissionOutcome(
        granted=granted, refused=tuple(sorted(set(refused))),
        dropped_without_use=tuple(sorted(set(dropped))), available=available)


def provisioned_step_layer(base: StepLayer, outcome: AdmissionOutcome) -> StepLayer:
    """Fold an admission outcome into the next step's layer.

    The base layer's own skills still win a name collision, for the same
    reason a task-triggered skill does not displace them: a step's fixed
    skills are part of what that step is.
    """
    merged = dict(base.skills)
    for name, body in outcome.granted.items():
        merged.setdefault(name, body)
    return StepLayer(
        step_id=base.step_id, description=base.description,
        system_prompt=base.system_prompt, tools=dict(base.tools),
        permission=dict(base.permission), skills=merged,
        context_files=dict(base.context_files), model=base.model,
        unattended=base.unattended)






def self_test() -> dict:
    """Run the separately housed offline composition checks."""
    from .opencode_step_composition_checks import run_checks

    return run_checks()


# The concrete layers, skills and core files live in ``opencode_step_layers``
# and are re-exported here so existing imports keep working. The split is
# machinery vs content, not a change to the public surface.
#
# Resolved LAZILY (PEP 562). An eager import here formed a cycle: layers
# imports this module at its top, so importing layers first ran this
# module to its bottom, which imported layers while layers was still
# half-initialised, and DEFAULT_CORE_FILES did not exist yet. It worked
# only when callers happened to import this module first.
_LAYER_EXPORTS = frozenset({
    "DEFAULT_CORE_FILES", "DEFAULT_SKILL_LIBRARY", "OBSERVATION_SKILL",
    "default_catalogue", "default_core", "default_skill_library",
    "inventory_step_layer", "observation_step_layer",
    "requirements_step_layer"})


def __getattr__(name: str):
    if name in _LAYER_EXPORTS:
        from . import opencode_step_layers as _layers
        return getattr(_layers, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
