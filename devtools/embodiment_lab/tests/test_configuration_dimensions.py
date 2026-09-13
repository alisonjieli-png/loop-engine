"""Protect the owner's design inventory without claiming runtime qualification."""
from pathlib import Path
import unittest

import yaml


REPOSITORY = Path(__file__).resolve().parents[3]
DOCUMENT = 'docs/architecture/DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-DIMENSIONS.md'
HANDOFF = 'docs/context/DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-HANDOFF-2026-09-12.md'
REQUIRED_BASELINE_DIMENSIONS = (
    'harness_implementation_and_process_initialization', 'role_profile', 'step_profile',
    'model', 'provider_and_route', 'tools', 'skills', 'context_markdown_files',
    'harness_native_instruction_markdown_files', 'prompt_injected_markdown_and_prompt_construction',
    'plugins', 'hooks', 'input_contract', 'output_contract', 'supervisors_and_independent_verifiers',
    'thinking_power', 'model_call_strategy', 'model_generation_settings', 'model_output_allocation',
    'loop_usage_and_orchestration', 'run_mode', 'intelligence_and_runtime_memory',
    'workspace_and_execution_environment', 'budgets_permissions_and_effect_policy',
    'loop_exit_and_output_publication_conditions',
)


class ConfigurationDimensionDocumentationChecks(unittest.TestCase):
    def setUp(self):
        self.architecture = yaml.safe_load((REPOSITORY / 'architecture.yaml').read_text())
        self.design = self.architecture['loop_dimensions']['configuration_design']

    def test_required_baseline_is_preserved_without_an_exact_count_ceiling(self):
        inventory = self.design['dimensions']
        self.assertLessEqual(set(REQUIRED_BASELINE_DIMENSIONS), set(inventory))
        self.assertEqual(len(set(inventory)), len(inventory))

    def test_inventory_requires_ongoing_discovery_without_runtime_permission(self):
        self.assertEqual(self.design['inventory_policy'], 'non_exhaustive')
        self.assertTrue(self.design['discovery_required'])
        self.assertEqual(self.design['baseline_preservation'],
                         'required_entries_are_a_minimum_not_a_ceiling')
        self.assertFalse(self.design['executable_configuration'])

    def test_proposals_remain_distinct_and_inherit_all_choice_requirements(self):
        self.assertEqual(self.design['proposal_status'], 'proposed_for_review')
        self.assertEqual(self.design['proposal_choice_requirements'], 'required_per_dimension')
        proposals = self.design['proposed_dimensions']
        self.assertTrue(proposals)
        self.assertFalse(set(proposals).intersection(self.design['dimensions']))
        document = (REPOSITORY / DOCUMENT).read_text()
        for identity, proposal in proposals.items():
            with self.subTest(dimension=identity):
                self.assertIn(proposal['relation_to_baseline'], ('refinement', 'cross_cutting'))
                self.assertTrue(proposal['related_baseline_dimensions'])
                self.assertLessEqual(set(proposal['related_baseline_dimensions']),
                                     set(self.design['dimensions']))
                self.assertTrue((REPOSITORY / proposal['boundary_to_inspect']).is_file())
                self.assertIn(proposal['label'], document)

    def test_discovery_addendum_is_linked_without_replacing_the_frozen_review(self):
        addendum = self.design['review_addendum']
        self.assertTrue((REPOSITORY / addendum).is_file())
        for name in (DOCUMENT, 'docs/context/CODEX-START-HERE.md',
                     'docs/context/CLAUDE-FABLE-5.1-REVIEW-HANDOFF-2026-09-13.md'):
            self.assertIn(Path(addendum).name, (REPOSITORY / name).read_text())

    def test_every_dimension_requires_initial_choice_and_ordered_fallback(self):
        required = self.design['required_per_dimension']
        self.assertIn('explicit_initial_choice_and_immutable_identity', required)
        self.assertIn('ordered_fallback_priorities_or_explicit_no_fallback', required)
        self.assertIn('eligibility_and_cross_dimension_compatibility', required)
        self.assertIn('exact_authority_and_remaining_resources', required)

    def test_design_is_explicitly_not_runtime_permission_or_qualification(self):
        self.assertFalse(self.design['executable_configuration'])
        self.assertEqual(self.design['status'], 'accepted_requirement_partially_implemented')
        self.assertEqual(self.design['operational_runtime_type'], 'Loop')

    def test_packaged_architecture_matches_authoritative_inventory(self):
        packaged = yaml.safe_load((REPOSITORY / 'src/loop_engine/data/architecture.yaml').read_text())
        self.assertEqual(packaged, self.architecture)

    def test_packaged_contract_files_preserve_exact_authoritative_bytes(self):
        for name in ('architecture.yaml', 'terminology.yaml'):
            self.assertEqual((REPOSITORY / name).read_bytes(),
                             (REPOSITORY / 'src/loop_engine/data' / name).read_bytes(), name)

    def test_complete_behavioral_explanation_is_preserved_verbatim(self):
        original = (REPOSITORY / HANDOFF).read_text().split('## Complete explanation\n\n', 1)[1]
        original = original.split('\n## Meaning of the existing runtime', 1)[0].strip()
        for name in (DOCUMENT, 'docs/context/CLAUDE-FABLE-5.1-REVIEW-HANDOFF-2026-09-13.md'):
            self.assertIn(original, (REPOSITORY / name).read_text(), name)

    def test_agent_entry_points_link_the_same_dimension_requirement(self):
        self.assertEqual(self.design['document'], DOCUMENT)
        self.assertEqual(self.design['behavioral_explanation'], HANDOFF)
        for name in ('AGENTS.md', 'docs/context/CODEX-START-HERE.md', HANDOFF):
            self.assertIn(Path(DOCUMENT).name, (REPOSITORY / name).read_text(), name)


if __name__ == '__main__':
    unittest.main()
