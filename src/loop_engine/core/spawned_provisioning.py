"""Provision the folder a spawned node works in, before it starts working.

A run already breaks a task into spawned subproblems, orders them by their
dependencies, and gives each one its own workspace folder. What it did not do
is put anything in that folder: the node received a task string and whatever
the machine it runs on happened to carry.

This is the connector. Before a spawned node runs, its folder receives the
instruction file in the name its harness reads, its assignment as typed
fields, and the record of what it was offered, what was withheld, and what was
exposed. The guardrails that apply are evaluated first, and a blocking rule
refuses the node before a file is written.

THE KIND IS DERIVED FROM AUTHORITY, NOT GUESSED
A node either reasons or builds, and that decides the authority it holds. The
derivation runs the other way here, which is the only honest direction
available: a node the run has already authorized to write its workspace is a
build node, and one that was not is a reason node. That reads a declared field
rather than inferring intent from an objective sentence.

NOTHING HAPPENS WITHOUT A CATALOGUE
A run whose dependencies carry no harness catalogue is unchanged. The result
says so by name rather than silently doing nothing, because a folder that was
never provisioned and a folder that was provisioned with nothing look the same
on disk.
"""
from __future__ import annotations

from pathlib import Path

from .intelligence_tagging import EMPTY_TAGS, TagSet
from .node_provisioning import (NODE_KINDS, NodeAssignment, NodeProvisioningError,
                                provision)

RECORD_TYPE = "spawned_provisioning/v1"
#: Why a node was not provisioned. Each one is a fact about the run, not a failure.
NOT_PROVISIONED = ("no_catalogue_installed", "no_workspace")
#: The effect every node holds: it may read the folder it was given.
BASE_EFFECT = "reads_fs"
#: The effect a node holds only when the run authorized workspace writes.
WRITE_EFFECT = "writes_fs"


def kind_for(request) -> str:
    """Reason or build, from the authority the run already granted.

    A node authorized to write its workspace builds; one that was not reasons.
    This reads a declared field instead of reading intent out of an objective.
    """
    return NODE_KINDS[1] if getattr(request, "allow_workspace_writes", False) else NODE_KINDS[0]


def effects_for(request) -> tuple[str, ...]:
    """What the node may do, taken from what the run already permits."""
    if getattr(request, "allow_workspace_writes", False):
        return (BASE_EFFECT, WRITE_EFFECT)
    return (BASE_EFFECT,)


def tags_for(request) -> TagSet:
    """The dimensions this node's work is filed under, when the run declares them."""
    declared = getattr(request, "intelligence_tags", None)
    if declared is None:
        return EMPTY_TAGS
    if isinstance(declared, TagSet):
        return declared
    if isinstance(declared, dict):
        return TagSet(declared)
    raise NodeProvisioningError(
        "declared intelligence tags must be a typed tag set or a mapping")


def provision_spawned(services, *, node_id: str, objective: str,
                      output_contract_refs=(), dependency_ids=()) -> dict:
    """Write one spawned node's folder and return what was placed in it.

    ``services`` is the forked run services for that node: its request carries
    the authority, and its workspace is the folder the node starts in. A
    blocking guardrail raises rather than returning, because a node that must
    not run is not a node with an empty folder.
    """
    dependencies = getattr(services, "dependencies", None)
    catalogue = getattr(dependencies, "harness_catalogue", None)
    if catalogue is None:
        return {"record_type": RECORD_TYPE, "node_id": node_id, "provisioned": False,
                "reason": NOT_PROVISIONED[0], "files_written": []}
    workspace = getattr(services, "workspace_base", None)
    if workspace is None:
        return {"record_type": RECORD_TYPE, "node_id": node_id, "provisioned": False,
                "reason": NOT_PROVISIONED[1], "files_written": []}
    folder = Path(workspace)
    folder.mkdir(parents=True, exist_ok=True)
    request = getattr(services, "request", None)
    assignment = NodeAssignment(
        node_id, kind_for(request), objective, tuple(output_contract_refs),
        tuple(dependency_ids), (), effects_for(request),
        str(getattr(request, "harness_style", "") or ""),
        bool(getattr(request, "authorize_model_calls", True)))
    placed = provision(assignment, catalogue=catalogue, root=folder,
                       guardrails=getattr(dependencies, "guardrails", None),
                       tags=tags_for(request))
    record = placed.to_dict()
    record["record_type"] = RECORD_TYPE
    record["provisioned"] = True
    record["reason"] = ""
    return record


def self_test() -> dict:
    """The kind follows the authority, a blocking rule refuses, and no catalogue changes nothing."""
    import json
    import tempfile
    from types import SimpleNamespace
    from .guardrail_intelligence import Guardrail, GuardrailSet
    from .harness_intelligence import (HarnessIntelligenceCatalogue,
                                       HarnessIntelligenceDraft, item_from_body)
    from .instance_instructions import STANDARD_FILE
    from .node_provisioning import ASSIGNMENT_FILE, PROVISIONING_FILE
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    def refuses(action, kind=NodeProvisioningError):
        try:
            action()
        except kind:
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
        "tool.write_report", "tool", "Write a report file",
        "code_intelligence", "code.capability.write_report",
        declared_effects=("reads_fs", "writes_fs")), "{}"))
    catalogue.register(item_from_body(HarnessIntelligenceDraft(
        "skill.nurse_intake", "skill", "Intake questions for a nurse",
        "context_intelligence", "ctx.skill.nurse_intake", "MIT",
        tags=TagSet({"role": ("nurse",)})), "# Intake\n\nAsk plainly.\n"))

    def services_for(folder, *, writes: bool, catalogue_installed=True, rules=None,
                     tags=None):
        return SimpleNamespace(
            request=SimpleNamespace(allow_workspace_writes=writes, harness_style="claude_code",
                                    authorize_model_calls=True, intelligence_tags=tags),
            dependencies=SimpleNamespace(
                harness_catalogue=catalogue if catalogue_installed else None,
                guardrails=rules),
            workspace_base=Path(folder) / "spawned" / "1")

    check("the_kind_and_the_effects_follow_the_authority_the_run_already_granted",
          kind_for(SimpleNamespace(allow_workspace_writes=True)) == "build"
          and kind_for(SimpleNamespace(allow_workspace_writes=False)) == "reason"
          and kind_for(SimpleNamespace()) == "reason"
          and effects_for(SimpleNamespace(allow_workspace_writes=True))
          == ("reads_fs", "writes_fs")
          and effects_for(SimpleNamespace(allow_workspace_writes=False)) == ("reads_fs",))

    with tempfile.TemporaryDirectory() as folder:
        services = services_for(folder, writes=True)
        placed = provision_spawned(
            services, node_id="task_1", objective="Write the cleaned supplier file",
            output_contract_refs=("artifact/v1",), dependency_ids=("task_0",))
        node_folder = services.workspace_base
        body = (node_folder / STANDARD_FILE).read_text("utf-8")
        assignment = json.loads((node_folder / ASSIGNMENT_FILE).read_text("utf-8"))
        check("a_spawned_node_that_may_write_is_provisioned_as_a_build_node",
              placed["provisioned"] is True and placed["kind"] == "build"
              and "Write the cleaned supplier file" in body
              and "reads_fs, writes_fs" in body
              and assignment["dependency_ids"] == ["task_0"]
              and assignment["output_contract_refs"] == ["artifact/v1"]
              and (node_folder / PROVISIONING_FILE).is_file()
              and "tool.write_report" in body,
              str(placed["kind"]))

    with tempfile.TemporaryDirectory() as folder:
        services = services_for(folder, writes=False)
        placed = provision_spawned(services, node_id="task_2", objective="Decide the columns")
        body = (services.workspace_base / STANDARD_FILE).read_text("utf-8")
        check("a_spawned_node_that_may_not_write_is_a_reason_node_and_is_offered_no_writing_tool",
              placed["kind"] == "reason"
              and "tool.write_report" not in body and "skill.read_the_source" in body
              and "reads_fs" in body and "writes_fs" not in body
              and placed["exposed_bytes"] == 0,
              str(placed["kind"]))

    with tempfile.TemporaryDirectory() as folder:
        rules = GuardrailSet()
        rules.register(Guardrail(
            "guard.contract_before_writing", "A writing node states its output contract",
            "process", "block", "before_provisioning",
            "provision a writing node without an output contract",
            evidence_required=("output_contract_refs",)))
        services = services_for(folder, writes=True, rules=rules)
        blocked = refuses(lambda: provision_spawned(
            services, node_id="task_3", objective="Write something"))
        check("a_blocking_rule_refuses_the_spawned_node_before_its_folder_is_filled",
              blocked
              and not (services.workspace_base / STANDARD_FILE).exists()
              and provision_spawned(
                  services_for(folder, writes=True, rules=rules), node_id="task_4",
                  objective="Write something", output_contract_refs=("artifact/v1",)
              )["provisioned"] is True)

    with tempfile.TemporaryDirectory() as folder:
        services = services_for(folder, writes=True, catalogue_installed=False)
        untouched = provision_spawned(services, node_id="task_5", objective="Decide")
        check("a_run_with_no_catalogue_is_unchanged_and_says_so_rather_than_writing_nothing",
              untouched["provisioned"] is False
              and untouched["reason"] == "no_catalogue_installed"
              and not services.workspace_base.exists()
              and provision_spawned(
                  SimpleNamespace(request=SimpleNamespace(allow_workspace_writes=True),
                                  dependencies=SimpleNamespace(harness_catalogue=catalogue,
                                                               guardrails=None),
                                  workspace_base=None),
                  node_id="task_6", objective="Decide")["reason"] == "no_workspace",
              untouched["reason"])

    with tempfile.TemporaryDirectory() as folder:
        for_nurse = provision_spawned(
            services_for(folder, writes=False, tags={"role": ("nurse",)}),
            node_id="task_7", objective="Ask the intake questions")
        for_analyst = provision_spawned(
            services_for(folder + "/other", writes=False, tags={"role": ("data analyst",)}),
            node_id="task_8", objective="Ask the intake questions")
        offered_to_nurse = [row["identity"] for row in for_nurse["offered"]]
        withheld_from_analyst = {row["identity"]: row["reason"]
                                 for row in for_analyst["withheld"]}
        check("declared_tags_reach_the_offer_and_a_wrong_shape_is_refused",
              # The tagged skill reaches the node whose request declares that role,
              # and is withheld from the one that does not, which is the wiring
              # rather than the helper.
              "skill.nurse_intake" in offered_to_nurse
              and withheld_from_analyst.get("skill.nurse_intake") == "filed under other tags"
              and tags_for(SimpleNamespace()) == EMPTY_TAGS
              and tags_for(SimpleNamespace(intelligence_tags={"role": ("nurse",)})).on("role")
              == ("nurse",)
              and tags_for(SimpleNamespace(
                  intelligence_tags=TagSet({"language": ("de",)}))).on("language") == ("de",)
              and refuses(lambda: tags_for(SimpleNamespace(intelligence_tags="nurse"))),
              str(offered_to_nurse))
    passed = sum(item["passed"] for item in tests)
    return {"record_type": "spawned_provisioning_test/v1", "tests": tests,
            "passed": passed, "total": len(tests), "all_passed": passed == len(tests)}
