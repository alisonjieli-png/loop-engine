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
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

#: Tool names OpenCode understands in an agent's ``tools`` mapping. Naming
#: an unknown tool is refused at composition rather than discovered as a
#: silently ignored line in a generated agent file.
KNOWN_TOOLS = (
    "bash", "edit", "write", "read", "grep", "glob", "list",
    "patch", "todowrite", "todoread", "webfetch", "task", "skill")

#: Permission verbs OpenCode accepts. "ask" is refused for unattended steps
#: by ``StepLayer.__post_init__`` -- a prompt nobody is awake to answer is a
#: hang, not a safeguard.
PERMISSION_VERBS = ("allow", "deny", "ask")


class OpenCodeCompositionError(ValueError):
    """A layer, catalogue entry, or composed instance violated its contract."""


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
        for name in self.tools:
            if name not in KNOWN_TOOLS:
                raise OpenCodeCompositionError(
                    f"step {self.step_id!r} names unknown tool {name!r}; "
                    f"known tools are {', '.join(KNOWN_TOOLS)}")
        for klass, verb in self.permission.items():
            if verb not in PERMISSION_VERBS:
                raise OpenCodeCompositionError(
                    f"step {self.step_id!r} permission {klass!r} is {verb!r}; "
                    f"must be one of {', '.join(PERMISSION_VERBS)}")
            if verb == "ask" and self.unattended:
                raise OpenCodeCompositionError(
                    f"step {self.step_id!r} sets {klass!r} to 'ask' while "
                    "unattended; nobody is awake to answer, so this hangs "
                    "the run -- use 'allow' or 'deny'")

    def agent_markdown(self) -> str:
        """Render the agent file OpenCode reads for this step."""
        lines = ["---", f"description: {self.description}", "mode: primary"]
        if self.model:
            lines.append(f"model: {self.model}")
        if self.tools:
            lines.append("tools:")
            for name in sorted(self.tools):
                lines.append(f"  {name}: {str(bool(self.tools[name])).lower()}")
        if self.permission:
            lines.append("permission:")
            for klass in sorted(self.permission):
                lines.append(f"  {klass}: {self.permission[klass]}")
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
        if limit < 0:
            raise OpenCodeCompositionError("limit cannot be negative")
        chosen = {}
        for name in sorted(self._candidates):
            candidate = self._candidates[name]
            matched = candidate.matched_term(step_id, task)
            if matched is None:
                continue
            chosen[name] = (candidate.body, matched)
            if len(chosen) >= limit:
                break
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


#: Skills a practitioner run can pick up from the task text. Deliberately
#: few: a library that admits something for every task teaches the step
#: nothing, because a signal present everywhere is not a signal.
DEFAULT_SKILL_LIBRARY = (
    SkillCandidate(
        name="reproduce-before-fix",
        triggers=("bug", "broken", "fails", "failing", "error", "crash",
                  "regression", "traceback"),
        steps=("orient", "plan", "implement"),
        body=("---\nname: reproduce-before-fix\ndescription: Use when the "
              "task reports something broken.\n---\n\n"
              "# Reproduce before fixing\n\n"
              "Do not change code until you have run the failing case and "
              "seen it fail. A fix written against a described symptom "
              "rather than an observed one repairs the description.\n\n"
              "State the exact command you ran and what it printed. If you "
              "could not reproduce it, say so and stop: a report that the "
              "bug does not reproduce is a real result and is more useful "
              "than a speculative change.\n")),
    SkillCandidate(
        name="dataset-discipline",
        triggers=("dataset", "csv", "train", "test set", "accuracy", "f1",
                  "model", "features", "drift"),
        steps=("orient", "plan", "implement", "verify"),
        body=("---\nname: dataset-discipline\ndescription: Use for tasks "
              "involving data files or model metrics.\n---\n\n"
              "# Dataset discipline\n\n"
              "Read the supplied files before describing them. Row counts, "
              "column names and dtypes are facts to be looked up, never "
              "inferred from a filename.\n\n"
              "Never fit on the evaluation split. When a metric is "
              "reported, state which split produced it and how many rows it "
              "had; a number without its denominator is not a result.\n")),
    SkillCandidate(
        name="schedule-arithmetic",
        triggers=("schedule", "gantt", "dependency", "dependencies",
                  "critical path", "milestone", "timeline"),
        steps=("plan", "implement", "verify"),
        body=("---\nname: schedule-arithmetic\ndescription: Use for "
              "scheduling, dependency and timeline tasks.\n---\n\n"
              "# Schedule arithmetic\n\n"
              "A task starts when its last dependency ends, not when its "
              "first does. Compute finish times by walking dependencies, "
              "and detect cycles explicitly rather than recursing until the "
              "stack ends.\n\n"
              "Unknown dependency ids, duplicate ids and cycles are three "
              "distinct errors. Report which one occurred.\n")),
)


def default_skill_library() -> SkillLibrary:
    return SkillLibrary(DEFAULT_SKILL_LIBRARY)


def compose_instance(core: CoreLayer, step: StepLayer, workspace) -> ComposedInstance:
    """Materialize ``.opencode`` for one step and return its manifest.

    The core is written first and the step second, and a step file that
    would overwrite a core file is refused rather than silently winning.
    Layering that lets the variable half quietly replace the fixed half
    gives an invariant that holds only until something needs it not to.
    """
    if not core.verify_core_unchanged():
        raise OpenCodeCompositionError(
            "core layer bytes no longer match the digest recorded for them")
    root = Path(workspace)
    root.mkdir(parents=True, exist_ok=True)
    config_root = root / ".opencode"
    if config_root.exists():
        shutil.rmtree(config_root)
    written = {}

    for relative, payload in core.files.items():
        target = config_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        written[relative] = "core"

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
    for relative, payload in step_files.items():
        target = config_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        written[relative] = "step"

    for relative, text in step.context_files.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            text if isinstance(text, str) else text.decode("utf-8"),
            encoding="utf-8")

    manifest = {
        "record_type": "opencode_step_instance/v1",
        "step_id": step.step_id,
        "agent_name": agent_name,
        "core_digest": core.digest,
        "core_file_count": len(core.files),
        "step_file_count": len(step_files),
        "composed_digest": _digest_tree({**core.files, **step_files}),
        "tools": dict(sorted(step.tools.items())),
        "permission": dict(sorted(step.permission.items())),
        "skills": sorted(step.skills),
        "skill_count": len(step.skills),
        "context_files": sorted(step.context_files),
        "provenance": dict(sorted(written.items())),
    }
    (config_root / "instance-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return ComposedInstance(
        workspace=root, agent_name=agent_name, manifest=manifest)


#: A minimal core: the contract and refusal rules every step shares. Callers
#: with their own core pass ``CoreLayer.from_directory``; this exists so a
#: composed instance is available without a repository of layer files.
DEFAULT_CORE_FILES = {
    "skill/response-contract/SKILL.md": (
        "---\n"
        "name: response-contract\n"
        "description: Use on every step. States how this runtime reads a "
        "reply and what it does with one that does not fit.\n"
        "---\n\n"
        "# Response contract\n\n"
        "Your final message must be exactly one JSON object matching the "
        "contract stated in the request. No prose before or after it.\n\n"
        "If the request cannot be satisfied, still return the object, and "
        "put the reason in the field the contract provides for it. A refusal "
        "written as prose is read as a malformed reply and costs the step.\n\n"
        "Never invent a file path, a command, or a result you did not "
        "observe. A field you cannot fill from evidence is left empty, and "
        "an empty field is a usable answer.\n"),
}


def default_core() -> CoreLayer:
    return CoreLayer.from_mapping(DEFAULT_CORE_FILES)


def default_catalogue() -> StepLayerCatalogue:
    """Layers for the practitioner's own steps.

    Read-only steps have edit and bash denied outright. That is not caution
    for its own sake: an orient step that can write has a way to appear to
    make progress without producing the orientation it was asked for.
    """
    return StepLayerCatalogue((
        StepLayer(
            step_id="orient",
            description="Read the task and supplied sources; produce an orientation.",
            system_prompt=(
                "You are the orientation step. Read the task and any "
                "supplied sources, then state what is known, what is "
                "unknown, and what should happen next.\n\n"
                "You may read. You may not write, edit, or run commands: "
                "orientation is a reading act, and a step that edits has "
                "left its job."),
            tools={"read": True, "grep": True, "glob": True, "list": True,
                   "edit": False, "write": False, "bash": False},
            permission={"edit": "deny", "bash": "deny"},
        ),
        StepLayer(
            step_id="plan",
            description="Turn an orientation into ordered, checkable steps.",
            system_prompt=(
                "You are the planning step. Turn the orientation into an "
                "ordered list of steps, each one a thing that can be done "
                "and then checked.\n\n"
                "A step whose completion cannot be checked is not a step; "
                "split it until each piece has an observable result. You "
                "may read but not modify anything."),
            tools={"read": True, "grep": True, "glob": True, "list": True,
                   "edit": False, "write": False, "bash": False},
            permission={"edit": "deny", "bash": "deny"},
        ),
        StepLayer(
            step_id="implement",
            description="Make the change the plan calls for.",
            system_prompt=(
                "You are the implementation step. Make the change the plan "
                "calls for, in files, using the tools you have.\n\n"
                "Prefer the smallest change that satisfies the step. When "
                "you finish, report exactly the paths you wrote."),
            tools={"read": True, "write": True, "edit": True, "bash": True,
                   "grep": True, "glob": True, "list": True},
            permission={"edit": "allow", "bash": "allow"},
        ),
        StepLayer(
            step_id="verify",
            description="Run the checks and report what actually happened.",
            system_prompt=(
                "You are the verification step. Run the project's own "
                "checks and report their real output.\n\n"
                "Report what the commands printed, including failures. A "
                "verification step that reports success it did not observe "
                "is worse than one that reports nothing, because the run "
                "above it will believe you. You may run commands and read "
                "files; you may not edit them, because a verifier that can "
                "edit can make a failing check pass."),
            tools={"read": True, "bash": True, "grep": True, "glob": True,
                   "list": True, "edit": False, "write": False},
            permission={"edit": "deny", "bash": "allow"},
        ),
    ))


def inventory_step_layer(library: "SkillLibrary", catalogue: "StepLayerCatalogue"
                        ) -> StepLayer:
    """A step that establishes what this run actually has before using it.

    A run that never asks what it has tends to use the first capability it
    thinks of. Measured in this codebase: across a day of runs the model
    used 2 of 9 available capabilities, and rewording the prompt to advertise
    the others changed nothing. Naming the inventory as its own step, with
    its own output contract, is the structural version of that fix.

    It is read-only on purpose. An inventory step that could also act would
    stop being an inventory step at the first opportunity to make progress.
    """
    available_skills = ", ".join(library.available()) or "(none registered)"
    available_steps = ", ".join(catalogue.registered()) or "(none registered)"
    return StepLayer(
        step_id="inventory",
        description="Establish what tools, files and skills this run has.",
        system_prompt=(
            "You are the inventory step. Establish what is actually here "
            "before anything is decided.\n\n"
            "Look at the workspace: list the files, find the project's own "
            "test, lint and build commands by reading its config (package"
            ".json scripts, pyproject, Makefile, CI workflow). Report the "
            "commands you FOUND, quoted from the file you found them in. Do "
            "not report a command you assume is conventional.\n\n"
            f"Skills this runtime can admit: {available_skills}\n"
            f"Steps this runtime can compose: {available_steps}\n"
            "Your own tools this step: read, grep, glob, list.\n\n"
            "You may not edit, write, or run commands. Report only what you "
            "observed. A capability you could not confirm is reported as "
            "absent, not assumed present: a run that believes it has a test "
            "command it does not have will report a pass it never ran."),
        tools={"read": True, "grep": True, "glob": True, "list": True,
               "edit": False, "write": False, "bash": False},
        permission={"edit": "deny", "bash": "deny"},
    )


def requirements_step_layer(library: "SkillLibrary") -> StepLayer:
    """A step that names what THIS task needs, from a closed vocabulary.

    The model requests; it does not grant. That distinction is the whole
    safety property: a step that could add its own skills could add the one
    that tells it edit permission is fine, so requests are answered by
    ``admit_requests`` on the engine side against a registered catalogue.

    The closed vocabulary is stated in the prompt rather than left to be
    guessed, because a closed vocabulary that does not state itself makes
    the next attempt guess again -- the failure mode this codebase already
    paid for once.
    """
    offered = ", ".join(library.available()) or "(none registered)"
    return StepLayer(
        step_id="requirements",
        description="Name what this specific task needs, and what is missing.",
        system_prompt=(
            "You are the requirements step. Say what this task needs.\n\n"
            "You may request skills only from this exact list:\n"
            f"  {offered}\n"
            "Requesting anything outside it is refused, so name what you "
            "need from the list and describe anything missing in prose "
            "instead of inventing a name for it.\n\n"
            "For each request, say what you would do with it. A request "
            "with no stated use is dropped -- asking for everything "
            "available costs prompt budget on every later call and is the "
            "same as asking for nothing.\n\n"
            "If the task cannot be done with what exists, say so plainly "
            "and name the missing capability. An honest gap is a usable "
            "answer; an attempt that pretends the gap is not there is not."),
        tools={"read": True, "grep": True, "glob": True, "list": True,
               "edit": False, "write": False, "bash": False},
        permission={"edit": "deny", "bash": "deny"},
    )


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


#: The skill an observation step always carries. It is core to that step
#: rather than task-triggered: a step that exists to observe cannot have
#: observing be optional.
OBSERVATION_SKILL = (
    "---\nname: observe-the-failure\ndescription: Always active on an "
    "observation step.\n---\n\n"
    "# Observe before deciding\n\n"
    "A previous step failed. Your only job is to find out what actually "
    "happened. You cannot change anything -- the tools to do so are not "
    "here.\n\n"
    "Run the thing that failed and read its real output. Report the exact "
    "command and the exact text it printed, including the parts you did not "
    "expect. Quote it rather than summarising it.\n\n"
    "If what you observe contradicts the previous step's explanation, say "
    "so plainly. That contradiction is the most useful thing you can "
    "return, and the run above you cannot see it unless you name it.\n\n"
    "Do not propose a fix. A fix proposed in the same breath as an "
    "observation tends to bend the observation toward the fix.\n")


def observation_step_layer(failed_step_id: str, failure_text: str) -> StepLayer:
    """The step a run is forced into after a failure.

    WHY THIS IS A SEPARATE STEP RATHER THAN A RETRY
    Retrying a failed step gives the model the same tools and the same
    framing that produced the failure, plus an error string. Measured in
    this codebase: the same refusal was hit nine times across runs, because
    nothing in the loop's shape changed between attempts -- only the words
    did. A step that repeats is not a step that adapts.

    This layer changes the shape. Edit and write are absent, so the only
    available move is to look. That is the difference between asking a
    model to observe first and making observation the only thing it can do,
    and the distinction matters because framing has already been measured
    ineffective here while composition has not.
    """
    if not failed_step_id.strip():
        raise OpenCodeCompositionError(
            "an observation step must name the step that failed")
    excerpt = " ".join(str(failure_text).split())[:600] or "(no failure text recorded)"
    return StepLayer(
        step_id=f"observe-{failed_step_id}",
        description=f"Observe what actually happened when {failed_step_id} failed.",
        system_prompt=(
            f"The {failed_step_id} step failed. This is what the runtime "
            f"recorded:\n\n{excerpt}\n\n"
            "Find out what actually happened. Run the failing thing, read "
            "its real output, and report it exactly. You cannot edit or "
            "write files; that is deliberate. Return only what you "
            "observed."),
        tools={"read": True, "bash": True, "grep": True, "glob": True,
               "list": True, "edit": False, "write": False},
        permission={"edit": "deny", "bash": "allow"},
        skills={"observe-the-failure": OBSERVATION_SKILL},
    )


def self_test() -> dict:
    """Run the separately housed offline composition checks."""
    from .opencode_step_composition_checks import run_checks

    return run_checks()
