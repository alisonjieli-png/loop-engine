"""Checks for the declared-harness launcher: the plan without a process, and real sandboxed runs.

launch_checks() starts nothing: it reads the sandbox arguments, the launch
folder and the output rules. sandbox_checks() starts the fixture harness, the
custom Loop harness process and, where installed at its pinned version, Pi,
each fresh in Bubblewrap with a loopback endpoint and no model: the fixture
broker answers. Without Bubblewrap every sandbox check is reported as not
tested with its missing dependency, never as a pass. sandbox_checks() is kept
out of the base self-test; tools/register_step_harness.py and its tests run it.
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile

from . import harness_launch as launcher
from .harness_manifest import release_manifest_catalog
from .harness_manifest_checks import step_request
from .records import StepMaterial

SANDBOX_CHECK_NAMES = (
    "a_declared_harness_stays_a_candidate_until_its_qualification_proves_it",
    "a_declared_fixture_harness_qualifies_and_runs_a_step_through_the_slot",
    "a_harness_that_reads_the_folder_above_the_step_is_rejected",
    "a_session_process_never_outlives_its_step_attempt",
    "the_custom_loop_harness_runs_a_step_in_its_own_process")


def _check(name, passed, detail=""):
    return {"name": name, "passed": bool(passed), "detail": str(detail)[:300]}


def _plan(folder, manifest, software, mode="no_model"):
    values = launcher.template_values(folder, software, model_name="probe", prompt="Answer.")
    from .harness_manifest import render_launch
    arguments, environment = render_launch(manifest, values)
    return launcher.LaunchPlan(folder, (software.executable, *arguments), tuple(environment.items()), software,
                               mode, manifest.model_wire, "probe", 30.0, 2, True)


def launch_checks() -> list:
    """The launch plan and the output rules, with their known-wrong cases; no process starts."""
    tests = []
    manifest = release_manifest_catalog().manifest("fixture.step_harness")
    software = launcher.HarnessSoftware("/usr/bin/python3",
                                        (str(Path(__file__).with_name("fixture_harness.py")),))
    with tempfile.TemporaryDirectory(prefix="le-launch-") as root:
        first, second = launcher.LaunchFolder.create(Path(root)), launcher.LaunchFolder.create(Path(root))
        request = step_request(material=(StepMaterial("skill", "review-rules", "Review the rules first."),))
        placed = launcher.place_material(first, manifest, request, model_name="probe")
        plan = _plan(first, manifest, software.pinned())
        arguments = launcher.sandbox_arguments(plan, config_path=Path(root) / "config.json", socket_path=None)
        mounts = [arguments[index + 2] for index, item in enumerate(arguments) if item == "--bind"]
        tests.append(_check(
            "every_attempt_gets_a_new_launch_folder_with_the_material_at_its_native_places",
            first.root != second.root and "step/AGENTS.md" in placed
            and "step/.agents/skills/review-rules/SKILL.md" in placed
            and (first.root / "home").is_dir() and not any((first.root / "home").iterdir())))
        tests.append(_check(
            "the_sandbox_shares_no_network_clears_the_environment_and_writes_only_the_launch_folder",
            "--unshare-all" in arguments and "--clearenv" in arguments and "--share-net" not in arguments
            and mounts == [launcher.LAUNCH] and "--die-with-parent" in arguments))
        home_template = dict(manifest.launch.environment)["HOME"]
        tests.append(_check("the_harness_home_is_the_empty_launch_home",
                            home_template == "{empty_home}"
                            and dict(plan.environment)["HOME"] == launcher.INSIDE["empty_home"]))
    completion = release_manifest_catalog().manifest("pi.print").completion
    events = "\n".join(json.dumps(item) for item in (
        {"type": "turn_end", "message": {"content": [{"type": "text", "text": "first"}]}},
        {"type": "turn_end", "message": {"content": [{"type": "text", "text": "final answer"}]}}))
    tests.append(_check("a_declared_output_rule_reads_the_last_matching_event_and_nothing_else",
                        launcher.read_output(completion, events, "") == ("final answer", "")
                        and launcher.read_output(completion, '{"type":"error"}', "")[0] is None
                        and launcher.read_output(completion, "not json", "")[1] == "invalid_harness_output"))
    return tests


def _fixture_software():
    return launcher.HarnessSoftware("/usr/bin/python3", (str(Path(__file__).with_name("fixture_harness.py")),))


def _loop_software():
    package_root = Path(__file__).resolve().parents[3]
    return launcher.HarnessSoftware("/usr/bin/python3", (str(package_root),))


def _not_tested(reason, dependency) -> list:
    return [{"name": name, "passed": None, "not_tested": True, "outcome": "NOT_APPLICABLE",
             "missing_optional_dependencies": [dependency], "detail": reason} for name in SANDBOX_CHECK_NAMES]


def sandbox_checks(work_root: "Path | None" = None) -> dict:
    """Run the declared harnesses for real, each fresh in the sandbox; no model is called."""
    if not launcher.sandbox_available():
        tests = _not_tested("/usr/bin/bwrap is not installed; no process was started", "bubblewrap")
        return {"tests": tests, "passed": 0, "total": 0, "not_tested": len(tests), "all_passed": False}
    root = Path(work_root) if work_root else Path(tempfile.mkdtemp(prefix="le-sandbox-checks-"))
    try:
        tests = run_sandbox_scenarios(root)
    finally:
        if work_root is None:
            shutil.rmtree(root, ignore_errors=True)
    return {"tests": tests, "passed": sum(item["passed"] is True for item in tests), "total": len(tests),
            "not_tested": 0, "all_passed": all(item["passed"] for item in tests)}


def declared_engine(harness_id: str, software, *, environment_changes=None):
    """A declared harness engine from a packaged manifest, optionally with extra environment."""
    from .declared_harness import DeclaredHarnessStepEngine
    from .harness_manifest import StepHarnessManifest
    manifest = release_manifest_catalog().manifest(harness_id)
    if environment_changes:
        record = manifest.to_dict()
        record["launch"]["environment"].update(environment_changes)
        manifest = StepHarnessManifest.from_dict(record)
    return DeclaredHarnessStepEngine(manifest, software)


def installation_for(engine):
    from ..engines.host_records import EngineInstallation
    from .engines import declared_settings
    return EngineInstallation(engine.manifest.harness_id, engine.manifest.harness_id, engine.manifest.engine_kind,
                              True, declared_settings(engine.manifest, engine.software), None, None)


def step_host(engine, installation, qualification, work_root: Path, *, broker=None):
    from ..configuration_capabilities import digest
    from ..configuration_preferences import MetaPreferencePolicy
    from ..engines.host_records import EngineSlotConfiguration
    from ..engines.selection_records import EngineSelectionPolicy
    from ..engines.slots import load_engine_slot_catalog
    from .envelope import StepExecutionHost
    from .records import StepServices
    slot = next(item for item in load_engine_slot_catalog().slots if item.slot_id == "step_executor")
    name = installation.installation_id
    policy = EngineSelectionPolicy("step_executor", "1.0.0", "default", (name,), (), True, (),
                                   MetaPreferencePolicy(("declared-order",)), None,
                                   {"loop": ("pin", "exclude", "prefer"), "harness": ("prefer",)}, None, (), False)
    configuration = EngineSlotConfiguration("step_executor", "1.0.0", (installation,), {"default": policy},
                                            "declared", digest("sandbox check host"))
    return StepExecutionHost(slot, configuration, {name: engine}, {name: qualification} if qualification else {},
                             StepServices(str(work_root), broker=broker))


def _owner():
    from ...loop.recursive_loop import Loop, LoopConfig
    return Loop("own one step", LoopConfig(framework="custom", custom_steps=("act",),
                                            allowable_modes=("deterministic",), preferred_modes=("deterministic",),
                                            delegated_modes=("deterministic", "hybrid", "non_deterministic")))


def _sleepers() -> set:
    """Process identifiers whose command line is the fixture's lingering sleep."""
    found = set()
    for entry in Path("/proc").iterdir():
        if entry.name.isdigit():
            try:
                if (entry / "cmdline").read_bytes() == b"sleep\x00600\x00":
                    found.add(entry.name)
            except OSError:
                continue
    return found


def run_sandbox_scenarios(root: Path) -> list:
    """The real-process scenarios; each returns one named check."""
    from .envelope import execute_step
    from .qualification import fixture_broker, qualify_engine
    tests = []
    engine = declared_engine("fixture.step_harness", _fixture_software())
    installation = installation_for(engine)
    request = step_request()
    before = execute_step(request, step_host(engine, installation, None, root / "candidate"), parent=_owner())
    codes = {item.code for entry in before.decisions[0].eligibility for item in entry.refusals}
    tests.append(_check(SANDBOX_CHECK_NAMES[0], before.result.status == "unavailable"
                        and {"engine_not_active", "engine_unqualified"} <= codes, sorted(codes)))
    qualification, record = qualify_engine(engine, installation, work_root=root / "fixture-qualification")
    answer = "The fixture answered through the slot."
    ran = execute_step(request, step_host(engine, installation, qualification, root / "fixture-run",
                                          broker=fixture_broker(answer)), parent=_owner())
    result = ran.result
    tests.append(_check(SANDBOX_CHECK_NAMES[1], qualification.decision == "approved"
                        and qualification.ladder_rung == "step_finished" and result.status == "completed"
                        and [item.text for item in result.outputs] == [answer] and result.executor.delegated
                        and any(item.state == "loaded" for item in result.material),
                        {"rung": qualification.ladder_rung, "status": result.status, "error": result.error_code}))
    snooping = declared_engine("fixture.step_harness", _fixture_software(),
                               environment_changes={"FIXTURE_HARNESS_MISBEHAVE": "read_parent"})
    rejected, _ = qualify_engine(snooping, installation_for(snooping), work_root=root / "snooping-qualification")
    tests.append(_check(SANDBOX_CHECK_NAMES[2], rejected.decision == "rejected"
                        and rejected.ladder_rung != "step_finished", rejected.ladder_rung))
    lingering = declared_engine("fixture.step_harness", _fixture_software(),
                                environment_changes={"FIXTURE_HARNESS_MISBEHAVE": "leave_process"})
    sleepers = _sleepers()
    from .records import StepServices
    lingering.run_step(request, StepServices(str(root / "lingering"), broker=fixture_broker(answer)))
    tests.append(_check(SANDBOX_CHECK_NAMES[3], _sleepers() <= sleepers, sorted(_sleepers() - sleepers)))
    loop_engine = declared_engine("baltor_loop.process", _loop_software())
    loop_installation = installation_for(loop_engine)
    loop_qualification, _ = qualify_engine(loop_engine, loop_installation, work_root=root / "loop-qualification")
    from .engines_checks import deterministic_request
    from .records import StepRequirements
    delegated_request = deterministic_request(requirements=StepRequirements(delegation_required=True))
    loop_run = execute_step(delegated_request, step_host(loop_engine, loop_installation, loop_qualification,
                                                         root / "loop-run"), parent=_owner()).result
    tests.append(_check(SANDBOX_CHECK_NAMES[4], loop_qualification.decision == "approved"
                        and loop_run.status == "completed" and loop_run.executor.delegated
                        and json.loads(loop_run.outputs[0].text)["matched"] is True,
                        {"rung": loop_qualification.ladder_rung, "status": loop_run.status,
                         "error": loop_run.error_code}))
    return tests
