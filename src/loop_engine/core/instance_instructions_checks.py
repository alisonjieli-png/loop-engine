"""Checks for the instruction file every harness instance is given.

Split from ``external_harness_checks`` at the module size cap. These checks
run inside the gateway binding fixtures, which already own a parent Loop, a
bounded request, and an artifact store, so they are given those rather than
building a second set.
"""
from __future__ import annotations

import tempfile
from dataclasses import replace
from pathlib import Path

from .external_harness import (
    HarnessAdapterInfo, HarnessRunResult, HarnessServices, run_external_harness)
from .harness_execution_contracts import HarnessExecutionCapabilities


def instruction_file_checks(check, request, parent, services) -> None:
    """The instance is given its file before dispatch, and overreach refuses."""
    from .instance_instructions import (
        AssignmentBriefing, STANDARD_FILE, InstanceInstructionWriter, compose,
        sections_for_assignment, verify)

    class InstructionAdapter:
        """Reads the instruction file the engine left for it, and nothing else."""

        def __init__(self):
            self.ran, self.seen = 0, ""

        @staticmethod
        def info():
            return HarnessAdapterInfo("host_gateway", "fixture/v1", "not-imported",
                                      available=True,
                                      execution_capabilities=HarnessExecutionCapabilities(
                                          supported_features=("model_routes",)))

        def run(self, current, active_services):
            self.ran += 1
            folder = Path(active_services.instruction_writer.root)
            self.seen = (folder / STANDARD_FILE).read_text("utf-8")
            return HarnessRunResult(current.request_id, current.harness_id, "completed",
                                    output="fixture answer", adapter_version="fixture/v1")

    with tempfile.TemporaryDirectory(prefix="loop-engine-instructions-") as folder:
        writer = InstanceInstructionWriter(folder, ("reads_fs", "writes_fs"),
                                           ("text_conformance",),
                                           "Report through the packet contract.")
        reader = InstructionAdapter()
        instructed = run_external_harness(
            reader, replace(request, request_id="instructed-run"),
            services=HarnessServices(artifact_store=services.artifact_store,
                                     instruction_writer=writer), parent=parent)
        check("an_instance_is_given_its_instruction_file_before_the_adapter_runs",
              reader.ran == 1 and len(instructed.instruction_file_digest) == 64
              and request.goal in reader.seen and "text_conformance" in reader.seen
              and "reads_fs, writes_fs" in reader.seen
              and instructed.instruction_file_digest in reader.seen,
              instructed.instruction_file_digest[:16])
        composed = compose(sections_for_assignment(AssignmentBriefing(
            goal=request.goal, mode=request.mode, effects=("reads_fs", "writes_fs"),
            surfaces=("text_conformance",), tools=tuple(request.tool_refs),
            skills=tuple(request.skill_refs), working_folder=folder,
            reporting="Report through the packet contract.",
            model_calls_authorized=True)),
            authority_effects=("reads_fs", "writes_fs"), style=request.harness_id)
        check("the_instructions_on_disk_recompute_to_the_digest_the_run_recorded",
              verify(composed, folder)["all_unchanged"] is True
              and composed.digest == instructed.instruction_file_digest,
              composed.digest[:16])

    with tempfile.TemporaryDirectory(prefix="loop-engine-overreach-") as folder:
        overreaching = InstanceInstructionWriter(folder, ("network", "not_an_effect"))
        never_ran = InstructionAdapter()
        refused_instructions = run_external_harness(
            never_ran, replace(request, request_id="overreaching-run"),
            services=HarnessServices(artifact_store=services.artifact_store,
                                     instruction_writer=overreaching), parent=parent)
        check("instructions_that_name_an_effect_outside_the_declared_ones_refuse_the_dispatch",
              refused_instructions.status == "refused"
              and refused_instructions.error_code == "instance_instructions_refused"
              and not (Path(folder) / STANDARD_FILE).exists()
              and never_ran.ran == 0,
              refused_instructions.underlying_error[:80])
