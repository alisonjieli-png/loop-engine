"""The concrete step layers, skills and core files this engine ships.

Split from ``opencode_step_composition`` at the size cap. That module holds
the machinery -- how a layer is validated, digested and materialised. This
one holds the content: which steps exist, what each one is allowed to touch,
and which skills a task can pull in. The two change for different reasons
and at different rates, which is the only good reason to split a module.
"""

from __future__ import annotations

from .opencode_step_composition import (
    OpenCodeCompositionError, SkillCandidate, SkillLibrary, StepLayer,
    StepLayerCatalogue, CoreLayer, read_only_tools,
    source_only_edit_permission)


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
            tools=read_only_tools(),
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
            tools=read_only_tools(),
            permission={"edit": "deny", "bash": "deny"},
        ),
        StepLayer(
            step_id="implement",
            description="Make the change the plan calls for.",
            system_prompt=(
                "You are the implementation step. Make the change the plan "
                "calls for, in files, using the tools you have.\n\n"
                "Prefer the smallest change that satisfies the step. When "
                "you finish, report exactly the paths you wrote.\n\n"
                "You cannot edit test files; that is deliberate. If the gate "
                "can only pass by changing a test -- because the expectation "
                "is wrong, or because the test needs a service that is not "
                "here -- do not work around it. Set blocked_on to say exactly "
                "what a person would have to decide or provide, and stop. "
                "That is a complete answer."),
            tools=read_only_tools(bash=True, write=True, edit=True,
                                  patch=True),
            permission={"edit": source_only_edit_permission(),
                        "bash": "allow"},
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
            tools=read_only_tools(bash=True),
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
        tools=read_only_tools(),
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
        tools=read_only_tools(),
        permission={"edit": "deny", "bash": "deny"},
    )
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
def observation_step_layer(failed_step_id: str, failure_text: str, *,
                           engine_observed: "dict | None" = None) -> StepLayer:
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
    if engine_observed:
        # The engine ran the command, so the step has no reason to hold a
        # shell. bash is removed rather than forbidden in prose: a step
        # that keeps bash keeps a write path (sed, redirect, git checkout)
        # no matter what its prompt asserts, and this step's prompt used to
        # assert it could not edit while holding exactly that path.
        ran = str(engine_observed.get("command", ""))[:300]
        code = engine_observed.get("exit_code")
        body = str(engine_observed.get("output", ""))[:2500]
        exit_line = ("it did not finish and was stopped"
                     if engine_observed.get("timed_out")
                     else f"it exited {code}")
        prompt = (
            f"The {failed_step_id} step failed. The runtime ran the command "
            f"for you; you do not need to run anything.\n\n"
            f"Command: {ran}\nResult: {exit_line}\n\n"
            f"Real output:\n{body}\n\n"
            "Read that output and report what it actually says. Quote the "
            "lines that matter rather than summarising them. Name the "
            "single most specific fact in it -- a file and line, an exact "
            "value, a missing name.\n\n"
            "If the output contradicts the explanation the failed step "
            "gave, say so plainly. That contradiction is the most useful "
            "thing you can return, and the run above you cannot see it "
            "unless you name it.\n\n"
            "Do not propose a fix. A fix proposed in the same breath as an "
            "observation bends the observation toward the fix.\n\n"
            "If the output does not explain the failure, say that. \"The "
            "output does not say why\" is a real answer and is better than "
            "a cause invented to fill the field.")
        return StepLayer(
            step_id=f"observe-{failed_step_id}",
            description=f"Read what actually happened when {failed_step_id} failed.",
            system_prompt=prompt,
            tools=read_only_tools(),
            permission={"edit": "deny", "bash": "deny"},
            skills={"observe-the-failure": OBSERVATION_SKILL},
        )
    return StepLayer(
        step_id=f"observe-{failed_step_id}",
        description=f"Observe what actually happened when {failed_step_id} failed.",
        system_prompt=(
            f"The {failed_step_id} step failed. This is what the runtime "
            f"recorded:\n\n{excerpt}\n\n"
            "Find out what actually happened. Run the failing thing, read "
            "its real output, and report it exactly.\n\n"
            "Use bash to observe, never to change the tree: no redirect "
            "into a file, no `sed -i`, no `git checkout`, `stash` or "
            "`apply`, no installing or upgrading anything. You have no "
            "edit, write or patch tool, which leaves bash as the only way "
            "to modify a file here -- you are the one holding it shut, and "
            "the runtime checks the workspace afterwards and rolls back "
            "anything that moved.\n\n"
            "Return only what you observed. Do not propose a fix."),
        tools=read_only_tools(bash=True),
        permission={"edit": "deny", "bash": "allow"},
        skills={"observe-the-failure": OBSERVATION_SKILL},
    )
