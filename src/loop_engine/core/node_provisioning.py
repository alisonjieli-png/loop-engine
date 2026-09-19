"""From one atomic node of the solutioning space to one provisioned folder.

The engine breaks a task into atomic nodes and gives each one its own harness
instance. This module is the step between those two facts: it takes one node,
decides what that node may be given, writes the folder the instance starts in,
and returns a record of exactly what was placed there.

TWO KINDS, AND THE DIFFERENCE HAS TEETH
A node either reasons or builds. The difference is not a label on a prompt: a
reason node reads and returns an answer, so it holds no authority to write,
and a build node writes inside its own folder and nowhere else. A node that
asks for more than its kind allows is refused by name before a folder exists,
because a folder that grants more than the kind is how a reasoning step
quietly becomes a writing one.

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

from .harness_intelligence import HarnessIntelligenceCatalogue, offer
from .instance_instructions import (AssignmentBriefing, InstanceInstructionError,
                                    compose, sections_for_assignment, write)

RECORD_TYPE = "provisioned_node/v1"
ASSIGNMENT_FILE = "task.json"
PROVISIONING_FILE = "provisioning.json"
#: A node reasons or builds. Nothing else.
NODE_KINDS = ("reason", "build")
#: What each kind may be given, as declared data rather than a branch.
KIND_ITEM_KINDS = {
    "reason": ("instruction_file", "skill"),
    "build": ("instruction_file", "skill", "tool", "reusable_code"),
}
#: The most authority each kind may hold. A reason node does not write.
KIND_CEILING = {"reason": ("reads_fs",), "build": ("reads_fs", "writes_fs")}
#: Folders every instance gets, empty, so it never has to invent a location.
FOLDERS = ("contracts", "artifacts")


class NodeProvisioningError(ValueError):
    """The node names an unknown kind, or asks for more authority than its kind holds."""


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
    model_calls_authorized: bool = True

    def __post_init__(self) -> None:
        if not self.node_id.strip() or not self.objective.strip():
            raise NodeProvisioningError("a node needs an identifier and an objective")
        if self.kind not in NODE_KINDS:
            raise NodeProvisioningError(f"kind must be one of {NODE_KINDS}")
        ceiling = KIND_CEILING[self.kind]
        beyond = [effect for effect in self.effects if effect not in ceiling]
        if beyond:
            raise NodeProvisioningError(
                f"node {self.node_id!r} is a {self.kind} node, which holds {list(ceiling)}; "
                f"it cannot also hold {beyond}. Make it a build node, or narrow the work")

    def to_dict(self) -> dict:
        return {"record_type": "node_assignment/v1", "node_id": self.node_id,
                "kind": self.kind, "objective": self.objective,
                "output_contract_refs": list(self.output_contract_refs),
                "dependency_ids": list(self.dependency_ids),
                "required_capabilities": list(self.required_capabilities),
                "effects": list(self.effects),
                "harness_style": self.harness_style,
                "model_calls_authorized": self.model_calls_authorized}


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

    def to_dict(self) -> dict:
        return {"record_type": RECORD_TYPE, "node_id": self.node_id, "kind": self.kind,
                "folder": self.folder, "instruction_digest": self.instruction_digest,
                "files_written": list(self.files_written),
                "offered": [dict(row) for row in self.offered],
                "withheld": [dict(row) for row in self.withheld],
                "offered_bytes": self.offered_bytes,
                "exposed_bytes": self.exposed_bytes,
                "bodies_included": False}


def _reporting_for(assignment: NodeAssignment) -> str:
    """What the instance is told about reporting, by kind."""
    if assignment.kind == NODE_KINDS[0]:
        return ("Return the answer your output contract names. Finishing a response is "
                "not acceptance: the owning Loop checks the work.")
    return ("Write your result inside this folder and name the files you wrote. "
            "Finishing is not acceptance: the owning Loop checks the work.")


def provision(assignment: NodeAssignment, *, catalogue: HarnessIntelligenceCatalogue,
              root, reporting: str = "") -> ProvisionedInstance:
    """Write one node's folder and return the record of what was placed in it.

    Nothing is executed. The folder holds the instruction file in the name the
    harness reads, the assignment as typed fields, and the provisioning record
    naming every item with its digest, so the instance can ask for a body
    rather than being handed everything.
    """
    if not isinstance(assignment, NodeAssignment):
        raise NodeProvisioningError("a typed node assignment is required")
    folder = Path(root)
    if not folder.is_dir():
        raise NodeProvisioningError(
            f"the node folder {folder} does not exist, so nothing is provisioned")
    available = offer(catalogue, style=assignment.harness_style,
                      authority_effects=assignment.effects,
                      kinds=KIND_ITEM_KINDS[assignment.kind])
    surfaces = tuple(row["identity"] for row in available["offered"])
    try:
        composed = compose(
            sections_for_assignment(AssignmentBriefing(
                goal=assignment.objective, mode="non_deterministic",
                contract_id=", ".join(assignment.output_contract_refs),
                effects=tuple(assignment.effects), surfaces=surfaces,
                tools=tuple(assignment.required_capabilities),
                working_folder=str(folder),
                reporting=reporting or _reporting_for(assignment),
                model_calls_authorized=assignment.model_calls_authorized)),
            authority_effects=assignment.effects,
            style=assignment.harness_style)
    except InstanceInstructionError as exc:
        raise NodeProvisioningError(str(exc)) from None
    written = write(composed, folder)
    for name in FOLDERS:
        (folder / name).mkdir(exist_ok=True)
    (folder / ASSIGNMENT_FILE).write_text(
        json.dumps(assignment.to_dict(), indent=1, sort_keys=True), "utf-8")
    record = ProvisionedInstance(
        assignment.node_id, assignment.kind, str(folder), composed.digest,
        tuple(written["written"]), tuple(available["offered"]),
        tuple(available["withheld"]), available["offered_bytes"],
        available["exposed_bytes"])
    (folder / PROVISIONING_FILE).write_text(
        json.dumps(record.to_dict(), indent=1, sort_keys=True), "utf-8")
    return record


def provision_plan(assignments, *, catalogue: HarnessIntelligenceCatalogue,
                   root) -> dict:
    """Provision every node of a plan under one folder, one directory per node.

    Every node is provisioned or none is: a plan half provisioned is worse
    than a plan not provisioned, because the half that exists looks ready.
    """
    base = Path(root)
    if not base.is_dir():
        raise NodeProvisioningError(f"{base} does not exist")
    prepared = tuple(assignments)
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

    ``kinds`` names the kind of every slice by its identifier. A slice without
    a declared kind is refused rather than guessed, because whether a step
    reasons or builds decides the authority it is given.
    """
    slices = tuple(getattr(plan, "task_slices", ()) or ())
    if not slices:
        raise NodeProvisioningError("a plan needs at least one task slice")
    missing = [item.task_id for item in slices if item.task_id not in kinds]
    if missing:
        raise NodeProvisioningError(
            f"these slices declare no kind: {missing}; a step that reasons and a step "
            "that builds hold different authority, so the kind is declared, never guessed")
    out = []
    for item in slices:
        kind = kinds[item.task_id]
        allowed = tuple(effect for effect in effects if effect in KIND_CEILING.get(kind, ()))
        out.append(NodeAssignment(
            item.task_id, kind, item.objective,
            tuple(item.output_contract_refs), tuple(item.dependency_ids),
            tuple(item.required_capabilities), allowed, harness_style))
    return tuple(out)


def self_test() -> dict:
    """A reason node cannot write, a build node gets more, and the folder says what it got."""
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

    check("a_reason_node_cannot_hold_write_authority_and_an_unknown_kind_is_refused",
          refuses(lambda: NodeAssignment("n1", "reason", "Decide", effects=("writes_fs",)))
          and refuses(lambda: NodeAssignment("n1", "think", "Decide"))
          and refuses(lambda: NodeAssignment("", "reason", "Decide"))
          and NodeAssignment("n1", "reason", "Decide", effects=("reads_fs",)).kind == "reason")

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
        check("a_reason_node_is_offered_reading_material_and_never_the_writing_tool",
              offered_ids == ["skill.read_the_source"]
              and [row["identity"] for row in placed.withheld] == []
              and "capability.clean_names" not in body
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
          and from_plan[0].effects == ("reads_fs",)
          and from_plan[1].effects == ("reads_fs", "writes_fs")
          and refuses(lambda: assignments_from_plan(_Plan(), kinds={"task_1": "reason"}))
          and refuses(lambda: assignments_from_plan(
              type("_Empty", (), {"task_slices": ()})(), kinds={})),
          str([item.effects for item in from_plan]))
    passed = sum(item["passed"] for item in tests)
    return {"record_type": "node_provisioning_test/v1", "tests": tests,
            "passed": passed, "total": len(tests), "all_passed": passed == len(tests)}
