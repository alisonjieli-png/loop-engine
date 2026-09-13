"""A provisioning step between cognitive steps: decide what the NEXT one gets.

TWO ARCHITECTURES, ONE SEAM
The static architecture selects a step's skills from trigger words in the
task text (``dynamic_step_layer``) and follows a fixed step order. It is
cheap and predictable and remains the default.

This module is the alternative. Between every two cognitive steps runs a
PROVISIONER: its own composed instance, read-only, whose only job is to
look at the run's structured state and say what the next step needs --
which step it should even be, which skills, which files as context. The
step that follows is composed from those grants. Both architectures use
the same layers, the same catalogue, the same admission code and the same
session seam; a caller picks one with a flag.

WHY THE PROVISIONER NEVER GRANTS ANYTHING
It returns a REQUEST. The engine admits it against the registered catalogue
and library, reads any context file itself, and refuses whatever is not
registered -- naming what is. A provisioner that could compose the next
step directly could hand it the edit tool; this one can only ask. That is
the same trust direction every other step in this system has, and the
reason this design is safe to run unattended.

WHAT IT COSTS
One extra model call per cognitive step, at the per-instance overhead this
system has measured (~7.8k input tokens). Overnight that is affordable; the
budget is hours. It also makes the run's shape visible: every provisioning
decision is recorded with its reason, so "why did the run go to verify
instead of implement" has an answer in the morning.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .opencode_step_composition import (
    OpenCodeCompositionError, SkillLibrary, StepLayer, StepLayerCatalogue,
    admit_requests, read_only_tools)

#: A context file larger than this is summarised by its head rather than
#: carried whole. Every byte of context costs on every later call, and a
#: provisioner that asks for a 40 KB file has usually asked for a filename.
MAX_CONTEXT_FILE_BYTES = 6000

#: Files the provisioner may never pull into context, whatever it says.
#: Secrets travel by the environment allowlist or not at all.
FORBIDDEN_CONTEXT_NAMES = (".env", ".env.", "id_rsa", "id_ed25519", ".pem",
                           "credentials", "secrets", "auth.json", ".netrc")


class ProvisionError(OpenCodeCompositionError):
    """A provisioning request or its admission failed closed."""


@dataclass(frozen=True)
class ProvisionOutcome:
    """What the engine actually granted the next step, and why."""

    next_step: str
    granted_skills: dict
    context_files: dict
    refused_steps: tuple = ()
    refused_skills: tuple = ()
    refused_files: tuple = ()
    reason: str = ""

    def to_dict(self) -> dict:
        return {"next_step": self.next_step,
                "skills": sorted(self.granted_skills),
                "context_files": sorted(self.context_files),
                "refused_steps": list(self.refused_steps),
                "refused_skills": list(self.refused_skills),
                "refused_files": list(self.refused_files),
                "reason": self.reason[:300]}

    def refusal_message(self) -> str:
        parts = []
        if self.refused_steps:
            parts.append(f"unknown step(s) {', '.join(self.refused_steps)}")
        if self.refused_skills:
            parts.append(f"unregistered skill(s) {', '.join(self.refused_skills)}")
        if self.refused_files:
            parts.append(f"unavailable file(s) {', '.join(self.refused_files)}")
        return "; ".join(parts)


def provision_step_layer(planned_next: str, catalogue: StepLayerCatalogue,
                         library: SkillLibrary) -> StepLayer:
    """The read-only step that decides what the next step needs."""
    steps = ", ".join(catalogue.registered()) or "(none)"
    skills = ", ".join(library.available()) or "(none)"
    return StepLayer(
        step_id="provision",
        description="Decide which step runs next and what it must be given.",
        system_prompt=(
            "You are the provisioning step. Nothing you say changes the code. "
            "Your job is to decide what the NEXT step needs, from what the "
            "run knows so far.\n\n"
            f"The plan expects the next step to be: {planned_next}\n"
            f"Steps you may choose instead: {steps}\n"
            f"Skills you may request: {skills}\n\n"
            "Decide, in this order:\n"
            "1. Does the next step still make sense given the current state? "
            "If the failure is not yet reproduced, choose reproduce. If the "
            "cause is known, choose implement. If code changed and the gate "
            "has not been rerun, choose verify. If the state says blocked_on, "
            "choose summarise-for-human. Otherwise keep the plan.\n"
            "2. Which skills, from the list above, would change what that step "
            "does? Name each with one sentence on how it would be used. Do not "
            "request a skill you cannot say a use for.\n"
            "3. Which files, if any, must the step have read before it acts? "
            "Give exact paths that exist in the workspace, each with why. A "
            "step that must edit a function needs to see the function; a step "
            "that must run a gate needs to see the gate's config.\n\n"
            "You may read and search the workspace to answer these. You cannot "
            "edit, write, or run anything; that is deliberate.\n\n"
            "Return only what you can justify from the state or from a file "
            "you read. An empty list is a valid and often correct answer."),
        tools=read_only_tools(),
        permission={"edit": "deny", "bash": "deny"},
    )


PROVISION_SCHEMA = ('{"next_step": string, "why_this_step": string, '
                    '"skills": {"skill-name": "how it would be used"}, '
                    '"context_files": {"relative/path": "why the step needs it"}}')


def _parse_request(text: str) -> dict:
    try:
        value = json.loads(text)
    except ValueError as exc:
        raise ProvisionError(
            f"the provisioner did not return a JSON object: {str(exc)[:80]}") from exc
    if not isinstance(value, dict):
        raise ProvisionError("the provisioner must return an object")
    return value


def _safe_relative(raw: str, root: Path) -> "Path | None":
    """Resolve a requested path inside root, or None if it escapes or is forbidden."""
    candidate = (root / str(raw)).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    lowered = str(candidate).lower()
    if any(marker in lowered for marker in FORBIDDEN_CONTEXT_NAMES):
        return None
    # The instance directory is the step's own configuration; a step already
    # has its skills and agent file, so carrying them again as context costs
    # budget and adds nothing. Seen live: the provisioner asked for
    # .opencode/skill/response-contract/SKILL.md alongside the real sources.
    if "/.opencode/" in f"/{candidate.relative_to(root.resolve())}":
        return None
    return candidate if candidate.is_file() else None


def admit_provision(text: str, *, planned_next: str,
                    catalogue: StepLayerCatalogue, library: SkillLibrary,
                    workspace) -> ProvisionOutcome:
    """Turn the provisioner's request into grants. The engine decides everything.

    Steps outside the catalogue and skills outside the library are refused
    by name. Context files are read HERE, by the engine, under a size cap,
    never written by the model and never from outside the workspace.
    """
    request = _parse_request(text)
    root = Path(workspace)

    wanted = str(request.get("next_step") or planned_next).strip()
    refused_steps = ()
    if not catalogue.has(wanted):
        refused_steps = (wanted,)
        wanted = planned_next
        if not catalogue.has(wanted):
            raise ProvisionError(
                f"neither the requested step nor the planned step "
                f"{planned_next!r} is registered; registered steps are "
                f"{', '.join(catalogue.registered())}")

    skills = request.get("skills") or {}
    if not isinstance(skills, dict):
        skills = {str(item): "" for item in (skills or ())}
    admitted = admit_requests(skills, library)

    files_in = request.get("context_files") or {}
    if not isinstance(files_in, dict):
        files_in = {str(item): "" for item in (files_in or ())}
    context, refused_files = {}, []
    for raw, why in files_in.items():
        resolved = _safe_relative(str(raw), root)
        if resolved is None:
            refused_files.append(str(raw))
            continue
        try:
            data = resolved.read_bytes()
        except OSError:
            refused_files.append(str(raw))
            continue
        body = data[:MAX_CONTEXT_FILE_BYTES].decode("utf-8", errors="replace")
        if len(data) > MAX_CONTEXT_FILE_BYTES:
            body += (f"\n... [{len(data) - MAX_CONTEXT_FILE_BYTES:,} more bytes "
                     "not carried; read the file for the rest]")
        context[str(resolved.relative_to(root.resolve()))] = (
            f"# {raw} -- {str(why)[:120]}\n{body}")

    return ProvisionOutcome(
        next_step=wanted, granted_skills=admitted.granted,
        context_files=context, refused_steps=refused_steps,
        refused_skills=admitted.refused + admitted.dropped_without_use,
        refused_files=tuple(refused_files),
        reason=str(request.get("why_this_step") or "")[:300])


def apply_provision(base: StepLayer, outcome: ProvisionOutcome) -> StepLayer:
    """Compose the next step from its base layer plus what was granted.

    Context files are delivered as files in the workspace under a fixed
    name, not spliced into the prompt: the prompt stays bounded and the
    step reads them with the read tool it already has.
    """
    skills = dict(base.skills)
    for name, body in outcome.granted_skills.items():
        skills.setdefault(name, body)
    context_files = dict(base.context_files)
    if outcome.context_files:
        digest = "\n\n".join(outcome.context_files.values())
        context_files[".step-context.md"] = (
            "# Context the provisioning step selected for you\n\n" + digest)
    return StepLayer(
        step_id=base.step_id, description=base.description,
        system_prompt=base.system_prompt + (
            "\n\nA provisioning step selected context for you in "
            ".step-context.md; read it before acting."
            if outcome.context_files else ""),
        tools=dict(base.tools), permission=dict(base.permission),
        skills=skills, context_files=context_files, model=base.model,
        unattended=base.unattended)


def self_test() -> dict:
    """Prove requests are admitted, never obeyed."""
    import tempfile
    from .opencode_step_layers import default_catalogue, default_skill_library

    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed),
                      "detail": str(detail)[:170]})

    catalogue, library = default_catalogue(), default_skill_library()
    layer = provision_step_layer("implement", catalogue, library)
    check("the_provisioner_is_fully_read_only",
          not any(layer.tools.get(t) for t in ("bash", "edit", "write", "patch", "task")))
    check("the_provisioner_is_told_its_closed_vocabularies",
          "implement" in layer.system_prompt
          and "reproduce-before-fix" in layer.system_prompt)

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "src").mkdir()
        (root / "src" / "calc.py").write_text("def f(): return 1\n")
        (root / ".env").write_text("OLLAMA_API_KEY=secret\n")
        (root / "big.txt").write_text("x" * 20000)
        (root / ".opencode" / "skill" / "x").mkdir(parents=True)
        (root / ".opencode" / "skill" / "x" / "SKILL.md").write_text("skill")

        good = json.dumps({
            "next_step": "verify", "why_this_step": "code changed, gate not rerun",
            "skills": {"reproduce-before-fix": "run the failing case first",
                       "time-travel": "undo", "dataset-discipline": ""},
            "context_files": {"src/calc.py": "the function under change",
                              "../../etc/passwd": "curious",
                              ".env": "need the key",
                              "big.txt": "everything",
                              ".opencode/skill/x/SKILL.md": "my own skill",
                              "missing.py": "hmm"}})
        out = admit_provision(good, planned_next="implement",
                              catalogue=catalogue, library=library, workspace=root)
        check("a_registered_next_step_is_granted", out.next_step == "verify")
        check("only_registered_skills_with_a_use_are_granted",
              sorted(out.granted_skills) == ["reproduce-before-fix"]
              and set(out.refused_skills) == {"time-travel", "dataset-discipline"},
              f"refused={out.refused_skills}")
        check("a_real_workspace_file_becomes_context",
              "src/calc.py" in out.context_files
              and "def f()" in out.context_files["src/calc.py"])
        check("path_escape_secret_instance_and_missing_files_are_refused",
              set(out.refused_files) == {"../../etc/passwd", ".env", "missing.py",
                                         ".opencode/skill/x/SKILL.md"},
              str(out.refused_files))
        check("an_oversized_file_is_capped_not_carried_whole",
              "big.txt" in out.context_files
              and len(out.context_files["big.txt"]) < MAX_CONTEXT_FILE_BYTES + 300
              and "not carried" in out.context_files["big.txt"])

        unknown = json.dumps({"next_step": "teleport", "skills": {}, "context_files": {}})
        out2 = admit_provision(unknown, planned_next="implement",
                               catalogue=catalogue, library=library, workspace=root)
        check("an_unknown_step_falls_back_to_the_plan_and_is_named",
              out2.next_step == "implement" and out2.refused_steps == ("teleport",)
              and "teleport" in out2.refusal_message())

        composed = apply_provision(catalogue.select("verify"), out)
        check("grants_reach_the_next_step_as_skills_and_a_context_file",
              "reproduce-before-fix" in composed.skills
              and ".step-context.md" in composed.context_files
              and "def f()" in composed.context_files[".step-context.md"]
              and "read it before acting" in composed.system_prompt)
        check("the_next_steps_own_permissions_are_untouched",
              composed.permission == catalogue.select("verify").permission
              and composed.tools == catalogue.select("verify").tools,
              "a provisioner that could widen permissions would be a hole")

    for bad, frag in (("not json", "JSON object"), ("[1,2]", "must return an object")):
        try:
            admit_provision(bad, planned_next="implement", catalogue=catalogue,
                            library=library, workspace=".")
            check(f"refuses_{frag[:12].replace(' ', '_')}", False)
        except ProvisionError as exc:
            check(f"refuses_{frag[:12].replace(' ', '_')}", frag in str(exc))

    return {"module": "core.opencode_step_provision", "tests": tests,
            "passed": all(item["passed"] for item in tests)}
