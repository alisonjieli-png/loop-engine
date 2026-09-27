import unittest

from tools.component_verification_plan import VerificationNeed, plan_verification


class VerificationPlanChecks(unittest.TestCase):
    def test_source_facts_do_not_need_per_item_models_after_pipeline_qualification(self):
        plan = plan_verification(VerificationNeed('source_reference', qualified_reference_pipeline=True))
        self.assertEqual(plan['independent_reviewers'], 0)
        self.assertIn('source_correspondence', plan['run_checks'])

    def test_unqualified_pipeline_has_one_shared_review(self):
        plan = plan_verification(VerificationNeed('source_reference'))
        self.assertEqual(plan['independent_reviewers'], 1)
        self.assertTrue(plan['review_shared_pipeline_once'])

    def test_instructions_default_to_one_independent_reviewer(self):
        plan = plan_verification(VerificationNeed('instruction'))
        self.assertEqual(plan['independent_reviewers'], 1)
        self.assertTrue(plan['exclude_producer_family'])

    def test_independent_oracle_can_qualify_deterministic_behavior_without_llm_vote(self):
        plan = plan_verification(VerificationNeed('deterministic_tool', independent_behavior_oracle=True))
        self.assertEqual(plan['independent_reviewers'], 0)
        self.assertIn('known_wrong_controls', plan['run_checks'])

    def test_producer_tests_alone_do_not_claim_independent_oracle(self):
        self.assertEqual(plan_verification(VerificationNeed('deterministic_tool'))['independent_reviewers'], 1)

    def test_metadata_update_reuses_behavior_and_semantic_evidence(self):
        plan = plan_verification(VerificationNeed('deterministic_tool', changed_scopes=('metadata',),
            reusable_checks=('contract_cases', 'known_wrong_controls', 'bounded_execution', 'semantic_review')))
        self.assertEqual(plan['independent_reviewers'], 0)
        self.assertIn('contract_cases', plan['reuse_checks'])
        self.assertIn('secret_scan', plan['run_checks'])

    def test_contract_change_invalidates_old_behavior_checks(self):
        plan = plan_verification(VerificationNeed('deterministic_tool', changed_scopes=('contract',), reusable_checks=('contract_cases',)))
        self.assertIn('contract_cases', plan['run_checks'])

    def test_elevated_effects_get_targeted_additional_review(self):
        plan = plan_verification(VerificationNeed('integration', elevated_effects=True))
        self.assertEqual(plan['independent_reviewers'], 2)
        self.assertIn('effect_boundary', plan['run_checks'])
        self.assertFalse(plan['grants_execution_authority'])

    def test_findings_remain_visible_and_prevent_silent_reuse(self):
        plan = plan_verification(VerificationNeed('instruction', changed_scopes=('metadata',),
            reusable_checks=('semantic_review',), unresolved_findings=('missing_dependency',)))
        self.assertEqual(plan['independent_reviewers'], 1)
        self.assertEqual(plan['unresolved_findings'], ['missing_dependency'])

    def test_binary_checks_are_about_interfaces_and_provenance(self):
        plan = plan_verification(VerificationNeed('binary_binding'))
        self.assertIn('binary_interface_cases', plan['run_checks'])
        self.assertFalse(plan['approves_component'])

    def test_new_kind_gets_an_explicit_review_route_instead_of_blocking_intake(self):
        plan = plan_verification(VerificationNeed('new_notebook_component'))
        self.assertEqual(plan['independent_reviewers'], 1)
        self.assertIn('declared_contract', plan['run_checks'])
        self.assertFalse(plan['approves_component'])

    def test_malformed_kind_and_nonboolean_claim_refuse(self):
        with self.assertRaises(ValueError): VerificationNeed('')
        with self.assertRaises(ValueError): VerificationNeed('source_reference', qualified_reference_pipeline='yes')


if __name__ == '__main__':
    unittest.main()
