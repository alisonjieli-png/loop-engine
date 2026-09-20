"""From one atomic node of the solutioning space to one provisioned folder.

The engine breaks a task into atomic nodes and gives each one its own harness
instance. This module is the step between those two facts: it takes one node,
decides what that node may be given, writes the folder the instance starts in,
and returns a record of exactly what was placed there.

PURPOSE IS SEPARATE FROM AUTHORITY
Reasoning and building describe the assignment's primary deliverable. A
reasoning assignment may need an authorized experiment; a building assignment
may only prepare a proposal. Neither purpose grants or forbids an effect.
The caller supplies exact effects after checking the owning Loop's authority.

WHAT GOES IN THE FOLDER
The instruction file in the name that harness reads, the assignment as typed
fields, and the provisioning record naming every item the node may obtain with
its digest and where to ask for it. Bodies do not go in by default. An
instance starts small and asks for what it needs, and the record says what was
offered, what was withheld and why, and how many bytes were actually exposed.

WHAT THIS DOES NOT DO
It opens no process and calls no model. Provisioning a node and running it are
separate, so a plan can be provisioned, inspected, and compared before
anything executes, and so the whole path is checkable offline.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from ..loop.loop_control import DETERMINISTIC, MODES

from .harness_intelligence import HarnessIntelligenceCatalogue, offer
from .facets import EFFECTS
from .instance_instructions import (AssignmentBriefing, InstanceInstructionError,
                                    compose, sections_for_assignment, write)

RECORD_TYPE = "provisioned_node/v2"
ASSIGNMENT_FILE = "task.json"
PROVISIONING_FILE = "provisioning.json"
#: Primary deliverable categories, not runtime types or permission grants.
NODE_KINDS = ("reason", "build")
REASON, BUILD = NODE_KINDS
#: Resource eligibility follows exact selection and effects, not purpose.
ASSIGNMENT_ITEM_KINDS = ("instruction_file", "skill", "tool", "reusable_code")
#: Folders every instance gets, empty, so it never has to invent a location.
FOLDERS = ("contracts", "artifacts")


class NodeProvisioningError(ValueError):
    """An assignment has an invalid purpose, effect declaration or confined path."""


@dataclass(frozen=True)
class NodeAssignment:
    """One atomic node of the solutioning space, as typed fields."""

    node_id: str
    kind: str
    objective: str
    output_contract_refs: tuple[str, ...] = ()
    dependency_ids: tuple[str, ...] = ()
    required_capabilities: tuple[str, ...] = ()
    effects: tuple[str, ...] = ()
    harness_style: str = ""
    model_calls_authorized: bool = False
    mode: str = DETERMINISTIC

    def __post_init__(self) -> None:
        if any(not isinstance(getattr(self, name), str) for name in ("node_id", "kind", "objective", "harness_style")):
            raise NodeProvisioningError("assignment identifiers, kind, objective, and harness style must be text")
        if type(self.model_calls_authorized) is not bool:
            raise NodeProvisioningError("model call authority must be an explicit boolean")
        if self.mode not in MODES:
            raise NodeProvisioningError("assignment mode must be a current Loop run mode")
        for name in ("output_contract_refs", "dependency_ids", "required_capabilities", "effects"):
            value = getattr(self, name)
            if not isinstance(value, (list, tuple)) or any(not isinstance(item, str) for item in value):
                raise NodeProvisioningError(f"{name} must be a sequence of text values")
            object.__setattr__(self, name, tuple(value))
        if not self.node_id.strip() or not self.objective.strip():
            raise NodeProvisioningError("a node needs an identifier and an objective")
        if (self.node_id in (".", "..") or "/" in self.node_id
                or "\\" in self.node_id or ":" in self.node_id
                or any(ord(character) < 32 for character in self.node_id)):
            raise NodeProvisioningError("a node identifier must be one plain path component")
        if self.kind not in NODE_KINDS:
            raise NodeProvisioningError(f"kind must be one of {NODE_KINDS}")
        if (any(effect not in EFFECTS for effect in self.effects)
                or len(set(self.effects)) != len(self.effects)
                or ("pure" in self.effects and len(self.effects) != 1)):
            raise NodeProvisioningError(
                "assignment effects must be distinct declared effects; pure excludes other effects")

    def to_dict(self) -> dict:
        return {"record_type": "node_assignment/v3", "node_id": self.node_id,
                "kind": self.kind, "objective": self.objective,
                "output_contract_refs": list(self.output_contract_refs),
                "dependency_ids": list(self.dependency_ids),
                "required_capabilities": list(self.required_capabilities),
                "effects": list(self.effects),
                "harness_style": self.harness_style,
                "model_calls_authorized": self.model_calls_authorized, "mode": self.mode}


@dataclass(frozen=True)
class ProvisionedInstance:
    """What one node was actually given, and what it was not."""

    node_id: str
    kind: str
    folder: str
    instruction_digest: str
    files_written: tuple[str, ...]
    offered: tuple[dict, ...] = ()
    withheld: tuple[dict, ...] = ()
    offered_bytes: int = 0
    exposed_bytes: int = 0
    guardrails: dict = field(default_factory=dict)
    mode: str = "deterministic"

    def to_dict(self) -> dict:
        return {"record_type": RECORD_TYPE, "node_id": self.node_id, "kind": self.kind, "mode": self.mode,
                "folder": self.folder, "instruction_digest": self.instruction_digest,
                "files_written": list(self.files_written),
                "offered": [dict(row) for row in self.offered],
                "withheld": [dict(row) for row in self.withheld],
                "offered_bytes": self.offered_bytes,
                "exposed_bytes": self.exposed_bytes,
                "guardrails": dict(self.guardrails),
                "bodies_included": False}


def _reporting_for(assignment: NodeAssignment) -> str:
    """What the instance is told about reporting, by kind."""
    if assignment.kind == NODE_KINDS[0]:
        return ("Return the answer your output contract names. Finishing a response is "
                "not acceptance: the owning Loop checks the work.")
    return ("Write your result inside this folder and name the files you wrote. "
            "Finishing is not acceptance: the owning Loop checks the work.")


def provision(assignment: NodeAssignment, *, catalogue: HarnessIntelligenceCatalogue,
              root, reporting: str = "", guardrails=None, tags=None) -> ProvisionedInstance:
    """Write one node's folder and return the record of what was placed in it.

    Nothing is executed. The folder holds the instruction file in the name the
    harness reads, the assignment as typed fields, and the provisioning record
    naming every item with its digest, so the instance can ask for a body
    rather than being handed everything.
    """
    if not isinstance(assignment, NodeAssignment):
        raise NodeProvisioningError("a typed node assignment is required")
    folder = Path(root)
    if folder.is_symlink() or not folder.is_dir():
        raise NodeProvisioningError(
            f"the node folder {folder} must be an existing directory, not a symbolic link")
    folder = folder.resolve()
    # Reserve metadata names against unsafe overwrite before any instruction
    # file is written. Exclusive creation below also rejects a later collision.
    for name in (ASSIGNMENT_FILE, PROVISIONING_FILE):
        target = folder / name
        if target.exists() or target.is_symlink():
            raise NodeProvisioningError(f"{name} already exists; provisioning does not overwrite it")
    for name in FOLDERS:
        target = folder / name
        if target.is_symlink() or (target.exists() and not target.is_dir()):
            raise NodeProvisioningError(f"{name} must be a confined directory")
    from .guardrail_intelligence import (GuardrailSet, POINTS, evaluate, refusal_lines)
    from .intelligence_tagging import EMPTY_TAGS
    request = tags if tags is not None else EMPTY_TAGS
    refusals, guardrail_record = (), {}
    if guardrails is not None:
        if not isinstance(guardrails, GuardrailSet):
            raise NodeProvisioningError("guardrails must be a typed guardrail set")
        applicable = guardrails.applicable(request, POINTS[0])
        guardrail_record = evaluate(
            applicable,
            {"node_id": assignment.node_id, "kind": assignment.kind,
             "effects": list(assignment.effects),
             "output_contract_refs": list(assignment.output_contract_refs),
             "objective_present": bool(assignment.objective)},
            tags=request, point=POINTS[0])
        unresolved = guardrail_record["blocked_by"] + guardrail_record["escalated_by"]
        if unresolved:
            raise NodeProvisioningError(
                f"node {assignment.node_id!r} is blocked before provisioning by "
                f"{unresolved}; a completed decision is required before anything is written")
        refusals = refusal_lines(guardrails.applicable(request, POINTS[2]))
    available = offer(catalogue, style=assignment.harness_style,
                      authority_effects=assignment.effects,
                      kinds=ASSIGNMENT_ITEM_KINDS, tags=request)
    surfaces = tuple(row["identity"] for row in available["offered"])
    try:
        composed = compose(
            sections_for_assignment(AssignmentBriefing(
                goal=assignment.objective, mode=assignment.mode,
                contract_id=", ".join(assignment.output_contract_refs),
                effects=tuple(assignment.effects), surfaces=surfaces,
                tools=tuple(assignment.required_capabilities),
                working_folder=str(folder),
                reporting=reporting or _reporting_for(assignment),
                model_calls_authorized=assignment.model_calls_authorized), refusals),
            authority_effects=assignment.effects,
            style=assignment.harness_style)
    except InstanceInstructionError as exc:
        raise NodeProvisioningError(str(exc)) from None
    written = write(composed, folder)
    for name in FOLDERS:
        (folder / name).mkdir(exist_ok=True)
    try:
        with (folder / ASSIGNMENT_FILE).open("x", encoding="utf-8") as stream:
            json.dump(assignment.to_dict(), stream, indent=1, sort_keys=True)
    except OSError as exc:
        raise NodeProvisioningError("the assignment write was not committed; existing work is preserved") from exc
    record = ProvisionedInstance(
        assignment.node_id, assignment.kind, str(folder), composed.digest,
        tuple(written["written"]), tuple(available["offered"]),
        tuple(available["withheld"]), available["offered_bytes"],
        available["exposed_bytes"], guardrail_record, mode=assignment.mode)
    try:
        with (folder / PROVISIONING_FILE).open("x", encoding="utf-8") as stream:
            json.dump(record.to_dict(), stream, indent=1, sort_keys=True)
    except OSError as exc:
        raise NodeProvisioningError("the provisioning record was not committed; inspect partial work before retry") from exc
    return record


def provision_plan(assignments, *, catalogue: HarnessIntelligenceCatalogue,
                   root) -> dict:
    """Provision every node of a plan under one folder, one directory per node.

    Every node is provisioned or none is: a plan half provisioned is worse
    than a plan not provisioned, because the half that exists looks ready.
    """
    base = Path(root)
    if base.is_symlink() or not base.is_dir():
        raise NodeProvisioningError(f"{base} does not exist")
    base = base.resolve()
    prepared = tuple(assignments)
    if any(not isinstance(item, NodeAssignment) for item in prepared):
        raise NodeProvisioningError("a plan contains only typed node assignments")
    identities = [item.node_id for item in prepared]
    if len(set(identities)) != len(identities):
        raise NodeProvisioningError("node identifiers must be unique within one plan")
    made, records = [], []
    try:
        for assignment in prepared:
            node_folder = base / assignment.node_id
            node_folder.mkdir(exist_ok=False)
            made.append(node_folder)
            records.append(provision(assignment, catalogue=catalogue, root=node_folder))
    except Exception:
        import shutil
        for path in made:
            shutil.rmtree(path, ignore_errors=True)
        raise
    return {"record_type": "provisioned_plan/v1", "folder": str(base),
            "nodes": [record.to_dict() for record in records],
            "node_count": len(records),
            "reason_nodes": sum(1 for item in prepared if item.kind == NODE_KINDS[0]),
            "build_nodes": sum(1 for item in prepared if item.kind == NODE_KINDS[1]),
            "offered_bytes": sum(record.offered_bytes for record in records),
            "exposed_bytes": sum(record.exposed_bytes for record in records)}


def assignments_from_plan(plan, *, kinds, effects=(), harness_style: str = "") -> tuple:
    """Turn the task slices of a compiled plan into node assignments.

    ``kinds`` names the primary deliverable of each slice. ``effects`` is the
    caller's explicit shared grant; purpose never creates that grant.
    """
    slices = tuple(getattr(plan, "task_slices", ()) or ())
    if not slices:
        raise NodeProvisioningError("a plan needs at least one task slice")
    missing = [item.task_id for item in slices if item.task_id not in kinds]
    if missing:
        raise NodeProvisioningError(
            f"these slices declare no kind: {missing}; a step that reasons and a step "
            "that builds have different deliverables, so the kind is declared, never guessed")
    out = []
    for item in slices:
        kind = kinds[item.task_id]
        allowed = tuple(effects)
        out.append(NodeAssignment(
            item.task_id, kind, item.objective,
            tuple(item.output_contract_refs), tuple(item.dependency_ids),
            tuple(item.required_capabilities), allowed, harness_style))
    return tuple(out)


def self_test() -> dict:
    """Purpose, explicit authority, confinement, and exact resource offers."""
    import tempfile
    from .harness_intelligence import HarnessIntelligenceDraft, item_from_body
    from .instance_instructions import STANDARD_FILE
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    def refuses(action):
        try:
            action()
        except NodeProvisioningError:
            return True
        except Exception:  # noqa: BLE001 - a crash is not a typed refusal
            return False
        return False

    catalogue = HarnessIntelligenceCatalogue()
    catalogue.register(item_from_body(HarnessIntelligenceDraft(
        "skill.read_the_source", "skill", "How to read a supplied source file",
        "context_intelligence", "ctx.skill.read_the_source", "MIT"),
        "# Read the source\n\nOpen what the assignment names.\n"))
    catalogue.register(item_from_body(HarnessIntelligenceDraft(
        "capability.clean_names", "reusable_code", "Clean a supplier column",
        "code_intelligence", "code.capability.clean_names", "MIT"),
        "def clean(value): return value.strip()\n"))
    catalogue.register(item_from_body(HarnessIntelligenceDraft(
        "tool.write_report", "tool", "Write a report file",
        "code_intelligence", "code.capability.write_report",
        declared_effects=("reads_fs", "writes_fs")),
        "{}"))

    check("purpose_does_not_grant_authority_and_explicit_effects_are_validated",
          NodeAssignment("n1", "reason", "Run an authorized experiment", effects=("writes_fs",)).effects == ("writes_fs",)
          and NodeAssignment("n1", "build", "Propose an artifact").effects == ()
          and refuses(lambda: NodeAssignment("n1", "reason", "Decide", effects=("invented",)))
          and refuses(lambda: NodeAssignment("n1", "reason", "Decide", effects=("pure", "writes_fs")))
          and refuses(lambda: NodeAssignment("n1", "think", "Decide"))
          and refuses(lambda: NodeAssignment("", "reason", "Decide"))
          and NodeAssignment("n1", "reason", "Decide", effects=("reads_fs",)).kind == "reason")
    check("an_assignment_identifier_cannot_escape_its_plan_folder",
          all(refuses(lambda identity=identity: NodeAssignment(identity, "reason", "Decide"))
              for identity in ("../escaped", "/absolute", "a/b", "a\\b", "..", "C:outside")))
    mutable_effects = ["reads_fs"]
    frozen_assignment = NodeAssignment("immutable", "reason", "Decide", effects=mutable_effects)
    mutable_effects.append("writes_fs")
    check("assignment_authority_is_detached_from_mutable_caller_values",
          frozen_assignment.effects == ("reads_fs",)
          and frozen_assignment.model_calls_authorized is False
          and refuses(lambda: NodeAssignment("invalid", "reason", "Decide", model_calls_authorized="false")))
    with tempfile.TemporaryDirectory() as folder:
        outside = Path(folder) / "outside.txt"
        outside.write_text("unchanged", "utf-8")
        instance = Path(folder) / "instance"
        instance.mkdir()
        (instance / ASSIGNMENT_FILE).symlink_to(outside)
        refused = refuses(lambda: provision(NodeAssignment("n1", "reason", "Decide"),
                                            catalogue=catalogue, root=instance))
        check("metadata_symlinks_refuse_before_any_instruction_write",
              refused and outside.read_text("utf-8") == "unchanged"
              and not (instance / STANDARD_FILE).exists())
        (instance / ASSIGNMENT_FILE).unlink()
        (instance / "contracts").symlink_to(Path(folder), target_is_directory=True)
        check("a_resource_directory_cannot_be_a_symbolic_link",
              refuses(lambda: provision(NodeAssignment("n1", "reason", "Decide"),
                                         catalogue=catalogue, root=instance))
              and not (instance / STANDARD_FILE).exists())

    with tempfile.TemporaryDirectory() as folder:
        reason_node = NodeAssignment(
            "n1", "reason", "Decide which columns carry the supplier name",
            ("decision/v1",), (), ("read",), ("reads_fs",), "claude_code")
        placed = provision(reason_node, catalogue=catalogue, root=folder)
        body = (Path(folder) / STANDARD_FILE).read_text("utf-8")
        assignment_written = json.loads((Path(folder) / ASSIGNMENT_FILE).read_text("utf-8"))
        record_written = json.loads((Path(folder) / PROVISIONING_FILE).read_text("utf-8"))
        offered_ids = [row["identity"] for row in placed.offered]
        check("a_reason_node_is_given_the_instruction_file_the_assignment_and_the_record",
              placed.files_written == (STANDARD_FILE, "CLAUDE.md")
              and reason_node.objective in body
              and assignment_written["kind"] == "reason"
              and assignment_written["output_contract_refs"] == ["decision/v1"]
              and record_written["instruction_digest"] == placed.instruction_digest
              and record_written["bodies_included"] is False
              and (Path(folder) / "contracts").is_dir()
              and (Path(folder) / "artifacts").is_dir(),
              str(placed.files_written))
        check("a_reason_assignment_can_use_code_but_ungranted_writes_are_withheld",
              offered_ids == ["capability.clean_names", "skill.read_the_source"]
              and [row["identity"] for row in placed.withheld] == ["tool.write_report"]
              and "capability.clean_names" in body
              and placed.exposed_bytes == 0 and placed.offered_bytes > 0,
              str(offered_ids))

    with tempfile.TemporaryDirectory() as folder:
        build_node = NodeAssignment(
            "n2", "build", "Write the cleaned file", ("artifact/v1",), ("n1",),
            ("write",), ("reads_fs", "writes_fs"), "codex")
        built = provision(build_node, catalogue=catalogue, root=folder)
        built_ids = sorted(row["identity"] for row in built.offered)
        body = (Path(folder) / STANDARD_FILE).read_text("utf-8")
        check("a_build_node_is_offered_code_and_tools_as_well_and_only_the_standard_file_is_written",
              built_ids == ["capability.clean_names", "skill.read_the_source",
                            "tool.write_report"]
              and built.files_written == (STANDARD_FILE,)
              and "reads_fs, writes_fs" in body
              and "tool.write_report" in body,
              str(built_ids))

    with tempfile.TemporaryDirectory() as folder:
        plan_result = provision_plan(
            (NodeAssignment("n1", "reason", "Decide", ("decision/v1",), (), (),
                            ("reads_fs",)),
             NodeAssignment("n2", "build", "Write", ("artifact/v1",), ("n1",), (),
                            ("reads_fs", "writes_fs"))),
            catalogue=catalogue, root=folder)
        check("a_plan_is_provisioned_one_folder_per_node_with_the_counts_kept_apart",
              plan_result["node_count"] == 2 and plan_result["reason_nodes"] == 1
              and plan_result["build_nodes"] == 1
              and (Path(folder) / "n1" / ASSIGNMENT_FILE).is_file()
              and (Path(folder) / "n2" / ASSIGNMENT_FILE).is_file()
              and plan_result["exposed_bytes"] == 0,
              str(plan_result["node_count"]))

    with tempfile.TemporaryDirectory() as folder:
        broken = (NodeAssignment("n1", "reason", "Decide", ("decision/v1",), (), (),
                                 ("reads_fs",)),
                  NodeAssignment("n1", "build", "Write", ("artifact/v1",), (), (),
                                 ("reads_fs", "writes_fs")))
        # The second node fails inside provisioning, after the first folder exists,
        # so this is the case that shows a half provisioned plan is rolled back.
        mid_plan = (NodeAssignment("n1", "reason", "Decide", ("decision/v1",), (), (),
                                   ("reads_fs",)),
                    NodeAssignment("n2", "reason", "x" * 20_000, ("decision/v1",), (), (),
                                   ("reads_fs",), "windsurf"))
        rolled_back = refuses(lambda: provision_plan(
            mid_plan, catalogue=catalogue, root=folder))
        check("a_plan_with_a_repeated_node_or_a_missing_folder_provisions_nothing_at_all",
              rolled_back and not list(Path(folder).iterdir())
              and refuses(lambda: provision_plan(broken, catalogue=catalogue, root=folder))
              and not list(Path(folder).iterdir())
              and refuses(lambda: provision_plan((), catalogue=catalogue,
                                                 root=Path(folder) / "absent"))
              and refuses(lambda: provision(
                  NodeAssignment("n3", "reason", "Decide", effects=("reads_fs",)),
                  catalogue=catalogue, root=Path(folder) / "absent"))
              and refuses(lambda: provision("not a node", catalogue=catalogue, root=folder)))

    from .guardrail_intelligence import Guardrail, GuardrailSet
    from .intelligence_tagging import TagSet
    rules = GuardrailSet()
    pending_rules = GuardrailSet()
    pending_rules.register(Guardrail(
        "guard.pending_permission", "Confirm permission", "permission", "block",
        "before_provisioning", "the permission decision must be established",
        judge="model_judged", on_unavailable="escalate"))
    with tempfile.TemporaryDirectory() as folder:
        check("an_unresolved_escalation_cannot_allow_provisioning",
              refuses(lambda: provision(NodeAssignment("n1", "reason", "Decide"),
                                         catalogue=catalogue, root=folder,
                                         guardrails=pending_rules))
              and not list(Path(folder).iterdir()))
    rules.register(Guardrail(
        "guard.regulated_needs_a_contract", "Regulated work states its output contract",
        "data_handling", "block", "before_provisioning",
        "provision regulated work without an output contract",
        applies_to=TagSet({"data_sensitivity": ("regulated",)}),
        evidence_required=("output_contract_refs",)))
    rules.register(Guardrail(
        "guard.no_secret_in_output", "Keep credentials out of anything written",
        "secret", "block", "before_effect",
        "write a credential value into an output or a record"))
    regulated = TagSet({"data_sensitivity": ("regulated",)})
    with tempfile.TemporaryDirectory() as folder:
        guarded = provision(
            NodeAssignment("n4", "build", "Correct the patient list", ("artifact/v1",),
                           (), (), ("reads_fs", "writes_fs")),
            catalogue=catalogue, root=folder, guardrails=rules, tags=regulated)
        body = (Path(folder) / STANDARD_FILE).read_text("utf-8")
        record_written = json.loads((Path(folder) / PROVISIONING_FILE).read_text("utf-8"))
        check("an_instance_is_told_to_refuse_in_the_words_of_the_rules_that_apply_to_it",
              "You must not: write a credential value into an output or a record" in body
              and "Do not widen your own authority" not in body
              and record_written["guardrails"]["evaluated"] == 1
              and record_written["guardrails"]["blocked"] is False,
              str(record_written["guardrails"]["evaluated"]))
    with tempfile.TemporaryDirectory() as folder:
        blocked = refuses(lambda: provision(
            NodeAssignment("n5", "build", "Correct the patient list", (), (), (),
                           ("reads_fs", "writes_fs")),
            catalogue=catalogue, root=folder, guardrails=rules, tags=regulated))
        check("a_blocking_rule_refuses_the_node_before_a_single_file_is_written",
              blocked and not list(Path(folder).iterdir())
              and refuses(lambda: provision(
                  NodeAssignment("n6", "reason", "Decide", ("decision/v1",), (), (),
                                 ("reads_fs",)),
                  catalogue=catalogue, root=folder, guardrails="not a set")))

    class _Slice:
        def __init__(self, task_id, objective):
            self.task_id, self.objective = task_id, objective
            self.output_contract_refs = ("result/v1",)
            self.dependency_ids = ()
            self.required_capabilities = ()

    class _Plan:
        task_slices = (_Slice("task_1", "Read the input"), _Slice("task_2", "Write it back"))

    from_plan = assignments_from_plan(
        _Plan(), kinds={"task_1": "reason", "task_2": "build"},
        effects=("reads_fs", "writes_fs"))
    check("slices_become_nodes_only_when_each_one_declares_whether_it_reasons_or_builds",
          [item.kind for item in from_plan] == ["reason", "build"]
          and from_plan[0].effects == ("reads_fs", "writes_fs")
          and from_plan[1].effects == ("reads_fs", "writes_fs")
          and refuses(lambda: assignments_from_plan(_Plan(), kinds={"task_1": "reason"}))
          and refuses(lambda: assignments_from_plan(
              type("_Empty", (), {"task_slices": ()})(), kinds={})),
          str([item.effects for item in from_plan]))
    passed = sum(item["passed"] for item in tests)
    return {"record_type": "node_provisioning_test/v1", "tests": tests,
            "passed": passed, "total": len(tests), "all_passed": passed == len(tests)}
