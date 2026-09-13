"""Keep the coverage inventory tied to the authoritative dimension baseline.

These are documentation completeness checks, not functional qualification
of every dimension or path. Missing behavior remains explicit in the report.
"""
from pathlib import Path
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "docs/verification/RUN-PATH-AND-DIMENSION-COVERAGE-2026-09-13.md"
LABELS = {
    "harness_implementation_and_process_initialization": "Harness implementation and process initialization",
    "role_profile": "Role profile", "step_profile": "Step profile", "model": "Model",
    "provider_and_route": "Provider and route", "tools": "Tools", "skills": "Skills",
    "context_markdown_files": "Context Markdown files",
    "harness_native_instruction_markdown_files": "Harness-native instruction Markdown files",
    "prompt_injected_markdown_and_prompt_construction": "Prompt-injected Markdown and prompt construction",
    "plugins": "Plugins", "hooks": "Hooks", "input_contract": "Input contract",
    "output_contract": "Output contract", "supervisors_and_independent_verifiers": "Supervisors and independent verifiers",
    "thinking_power": "Thinking power", "model_call_strategy": "Model-call strategy",
    "model_generation_settings": "Model generation settings", "model_output_allocation": "Model output allocation",
    "loop_usage_and_orchestration": "Loop usage and orchestration", "run_mode": "Run mode",
    "intelligence_and_runtime_memory": "Intelligence and Runtime Memory",
    "workspace_and_execution_environment": "Workspace and execution environment",
    "budgets_permissions_and_effect_policy": "Budgets, permissions, and effect policy",
    "loop_exit_and_output_publication_conditions": "Loop condition, exit condition, and output publication",
}


class RunPathCoverageChecks(unittest.TestCase):
    def test_every_authoritative_baseline_has_one_coverage_row(self):
        design = yaml.safe_load((ROOT / "architecture.yaml").read_text())["loop_dimensions"]["configuration_design"]
        self.assertEqual(set(design["dimensions"]), set(LABELS))
        body = REPORT.read_text().split("## Baseline dimension checklist", 1)[1].split("## Additional dimensions", 1)[0]
        rows = [line.split("|")[1].strip() for line in body.splitlines()
                if line.startswith("| ") and not line.startswith("| Required dimension")]
        self.assertEqual(sorted(rows), sorted(LABELS.values()))

    def test_every_configured_harness_is_visible_without_claiming_qualification(self):
        body = REPORT.read_text().split("## Configured harness paths", 1)[1].split("## Process, output", 1)[0]
        for manifest in (ROOT / "embodiments").glob("*/harness.json"):
            self.assertIn("`" + manifest.parent.name + "`", body)
        self.assertIn("not 19 currently qualified task solvers", body)

    def test_coverage_distinguishes_proposals_controls_and_full_trials(self):
        body = REPORT.read_text()
        for required in ("not claim that all dimensions", "every permitted fallback trigger",
                         "Pairwise", "higher-order", "independent-evaluation", "has not yet been completed"):
            self.assertIn(required.casefold(), body.casefold())


if __name__ == "__main__":
    unittest.main()
