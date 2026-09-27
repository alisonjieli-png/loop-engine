"""Contract tests only: fake trusted-reader results never qualify live material."""
import hashlib
import unittest
from dataclasses import replace
from unittest.mock import patch

from loop_engine.core.service_runtime.catalogue_packages import (
    CataloguePackage,
    CataloguePackageFile,
)
from tools.candidate_review.records import canonical_bytes
from tools.candidate_review.shared_profiles import (
    CHECKS,
    ReferenceCheckReceipt,
    ReferenceOutputSubject,
    SharedReferenceProfile,
    compiler_inputs_digest,
    resolve_shared_review,
)


def checksum(value):
    return hashlib.sha256(value.encode()).hexdigest()


def scope_bytes(profile):
    value = profile.to_dict()
    del value['package_digest']
    value['record_type'] = 'shared_reference_profile_scope/v1'
    return canonical_bytes(value)


def fixture():
    profile = SharedReferenceProfile('reference_pipeline', '0' * 64, 'openai', checksum('criteria'),
        checksum('instructions'), 'openapi_reference/v2', checksum('compiler'), 'api_operation_reference',
        tuple((name, checksum(name)) for name in CHECKS))
    raw = scope_bytes(profile)
    package = CataloguePackage((CataloguePackageFile('contracts/shared-profile.json',
        hashlib.sha256(raw).hexdigest(), len(raw), 'application/json', 'other'),))
    profile = replace(profile, package_digest=package.package_digest)
    output = ReferenceOutputSubject('reference_one', checksum('output'), profile.component_type,
        profile.compiler_method, profile.compiler_digest, ('reads_fs',))
    receipts = [ReferenceCheckReceipt(name, output.package_digest, profile.compiler_digest,
        checksum(name), checksum('evidence:' + name), 'passed') for name in CHECKS]
    review = {'calibration': {}, 'reviewers': [{'reviewer_id': 'reviewer', 'family': 'google'}],
              'rows': [{'identity': profile.identity, 'body_sha256': profile.package_digest,
                        'prechecks': {'refused': False},
                        'subject': {'criteria_sha256': profile.criteria_digest,
                                    'instructions_sha256': profile.instructions_digest,
                                    'producer': {'family': profile.producer_family},
                                    'package': package.to_dict()},
                        'decisions': [{'reviewer_id': 'reviewer', 'call_ref': 'fixture-shaped-call#1',
                                       'decision': 'approve'}]}]}
    return profile, output, receipts, review


class SharedProfileChecks(unittest.TestCase):
    def resolve(self, profile=None, output=None, receipts=None, review=None):
        p, o, c, r = fixture()
        with patch('tools.candidate_review.shared_profiles.read_panel_review_record', return_value=review or r) as reader:
            result = resolve_shared_review(profile or p, output or o, receipts if receipts is not None else c,
                                           [{'trusted_reader_fixture': True}])
            reader.assert_called_once_with({'trusted_reader_fixture': True}, allow_fixture=False,
                                           calibration_inputs=None)
            return result

    def test_one_independent_bound_review_can_supply_shared_semantics(self):
        result = self.resolve()
        self.assertEqual(result['status'], 'eligible')
        self.assertFalse(result['approves_catalogue_component'])
        self.assertFalse(result['publishes_component'])
        self.assertFalse(result['grants_execution_authority'])

    def test_changed_profile_cannot_borrow_old_package_review(self):
        p, o, c, r = fixture()
        p = replace(p, compiler_digest=checksum('changed compiler'))
        o = replace(o, compiler_digest=p.compiler_digest)
        c = [replace(value, compiler_digest=p.compiler_digest) for value in c]
        self.assertNotEqual(self.resolve(p, o, c, r)['status'], 'eligible')

    def test_missing_independent_review_remains_pending(self):
        p, o, c, _r = fixture()
        self.assertEqual(resolve_shared_review(p, o, c, [])['status'], 'pending')

    def test_missing_check_remains_pending(self):
        _p, _o, c, _r = fixture()
        self.assertIn('check_missing:semantic_duplicates', self.resolve(receipts=c[:-1])['reasons'])

    def test_other_output_receipt_cannot_be_reused(self):
        _p, _o, c, _r = fixture()
        c[0] = replace(c[0], package_digest=checksum('other output'))
        self.assertNotEqual(self.resolve(receipts=c)['status'], 'eligible')

    def test_changed_checker_requires_qualification(self):
        _p, _o, c, _r = fixture()
        c[0] = replace(c[0], checker_digest=checksum('other checker'))
        self.assertNotEqual(self.resolve(receipts=c)['status'], 'eligible')

    def test_pending_failed_and_findings_cannot_coast(self):
        _p, _o, c, _r = fixture()
        for value in [replace(c[0], status='pending'), replace(c[0], status='failed'),
                      replace(c[0], findings=('unresolved example',))]:
            self.assertNotEqual(self.resolve(receipts=[value, *c[1:]])['status'], 'eligible')

    def test_producer_family_cannot_supply_independence(self):
        _p, _o, _c, r = fixture()
        r['reviewers'][0]['family'] = 'openai'
        self.assertIn('producer_review_cannot_qualify', self.resolve(review=r)['reasons'])

    def test_unqualified_reviewer_cannot_supply_independence(self):
        _p, _o, _c, r = fixture()
        r['calibration'] = None
        self.assertIn('shared_reviewer_calibration_missing', self.resolve(review=r)['reasons'])

    def test_rejection_is_retained(self):
        _p, _o, _c, r = fixture()
        r['rows'][0]['decisions'][0]['decision'] = 'reject'
        self.assertEqual(self.resolve(review=r)['status'], 'rejected')

    def test_wrong_criteria_does_not_qualify_same_bytes(self):
        _p, _o, _c, r = fixture()
        r['rows'][0]['subject']['criteria_sha256'] = checksum('other criteria')
        self.assertNotEqual(self.resolve(review=r)['status'], 'eligible')

    def test_output_effects_cannot_expand_profile(self):
        _p, o, _c, _r = fixture()
        o = replace(o, consumption_effects=('reads_fs', 'network'))
        self.assertNotEqual(self.resolve(output=o)['status'], 'eligible')

    def test_duplicate_check_is_refused(self):
        _p, _o, c, _r = fixture()
        with self.assertRaisesRegex(ValueError, 'duplicate_reference_check'):
            self.resolve(receipts=[*c, c[0]])

    def test_real_reader_does_not_accept_a_bare_approval_flag(self):
        p, o, c, _r = fixture()
        with self.assertRaises(ValueError):
            resolve_shared_review(p, o, c, [{'approved': True}])

    def test_profile_check_omission_and_write_effect_are_refused(self):
        p, _o, _c, _r = fixture()
        with self.assertRaises(ValueError):
            replace(p, checker_digests=p.checker_digests[:-1])
        with self.assertRaises(ValueError):
            replace(p, consumption_effects=('writes_fs',))

    def test_profile_roundtrip_and_unknown_version(self):
        p, _o, _c, _r = fixture()
        self.assertEqual(SharedReferenceProfile.from_dict(p.to_dict()), p)
        changed = p.to_dict()
        changed['record_type'] = 'shared_reference_profile/v2'
        with self.assertRaises(ValueError):
            SharedReferenceProfile.from_dict(changed)

    def test_unknown_approval_field_is_not_accepted(self):
        p, _o, _c, _r = fixture()
        changed = {**p.to_dict(), 'approved': True}
        with self.assertRaises(ValueError):
            SharedReferenceProfile.from_dict(changed)


#: The inputs of the reviewed compiler: its code, its guidance template and its check code.
REVIEWED_INPUTS = {'reference_compiler.py': checksum('compiler code, reviewed'),
                   'templates/operation-guidance.md': checksum('guidance template, reviewed'),
                   'verify_reference_fidelity.py': checksum('fidelity check code, reviewed')}


def old_approval():
    """One approval of the shared profile that the reviewed compiler inputs define."""
    profile = SharedReferenceProfile('reference_pipeline', '0' * 64, 'openai', checksum('criteria'),
        checksum('instructions'), 'openapi_reference/v2', compiler_inputs_digest(REVIEWED_INPUTS),
        'api_operation_reference', tuple((name, checksum(name)) for name in CHECKS))
    raw = profile.scope_document()
    package = CataloguePackage((CataloguePackageFile('contracts/shared-profile.json',
        hashlib.sha256(raw).hexdigest(), len(raw), 'application/json', 'other'),))
    profile = replace(profile, package_digest=package.package_digest)
    review = {'calibration': {}, 'reviewers': [{'reviewer_id': 'reviewer', 'family': 'google'}],
              'rows': [{'identity': profile.identity, 'body_sha256': profile.package_digest,
                        'prechecks': {'refused': False},
                        'subject': {'criteria_sha256': profile.criteria_digest,
                                    'instructions_sha256': profile.instructions_digest,
                                    'producer': {'family': profile.producer_family},
                                    'package': package.to_dict()},
                        'decisions': [{'reviewer_id': 'reviewer', 'call_ref': 'old-approval#1',
                                       'decision': 'approve'}]}]}
    return profile, review


def output_of(profile, compiler_digest):
    """An output that names the compiler it came from, with every check bound to that output and compiler."""
    output = ReferenceOutputSubject('reference_one', checksum('output of ' + compiler_digest),
        profile.component_type, profile.compiler_method, compiler_digest, ('reads_fs',))
    checkers = dict(profile.checker_digests)
    receipts = [ReferenceCheckReceipt(name, output.package_digest, compiler_digest, checkers[name],
                                      checksum('evidence:' + name), 'passed') for name in CHECKS]
    return output, receipts


def rebound(profile, **changes):
    """The known-wrong profile: fields changed, while it still names the old reviewed package."""
    return replace(profile, **changes)


class OldApprovalReuseChecks(unittest.TestCase):
    """A changed template, compiler or scope never reuses an approval of the old profile.

    Each case starts from an approval that makes the old profile eligible, changes one thing, and
    gives the resolver every chance to reuse the old approval: the old review record, receipts bound
    to the new output, and a profile rewritten to match that output. None of them may be eligible.
    """

    def resolve(self, profile, output, receipts, review):
        with patch('tools.candidate_review.shared_profiles.read_panel_review_record', return_value=review):
            return resolve_shared_review(profile, output, receipts, [{'trusted_reader_fixture': True}])

    def test_the_old_approval_holds_for_its_own_compiler(self):
        profile, review = old_approval()
        output, receipts = output_of(profile, profile.compiler_digest)
        self.assertEqual(self.resolve(profile, output, receipts, review)['status'], 'eligible')

    def test_every_compiler_input_is_part_of_the_compiler_identity(self):
        reviewed = compiler_inputs_digest(REVIEWED_INPUTS)
        self.assertEqual(compiler_inputs_digest(dict(reversed(list(REVIEWED_INPUTS.items())))), reviewed)
        for name in REVIEWED_INPUTS:
            with self.subTest(changed=name):
                self.assertNotEqual(compiler_inputs_digest({**REVIEWED_INPUTS, name: checksum('changed ' + name)}),
                                    reviewed)
        with self.assertRaises(ValueError):
            compiler_inputs_digest({**REVIEWED_INPUTS, 'templates/extra.md': 'not a digest'})

    def test_the_identity_matches_the_reference_compiler_build_record(self):
        """The helper reproduces the compiler digest the reference compiler recorded on September 26, 2026."""
        recorded = {'expand_api_references.py': '42d34a7f6a1ecdcccefd39fe1ae165d738d64157b7379d85f6bb64b8d5c52d38',
                    'reference_compiler.py': 'b46f697b3a62cac0a8fecb8050a8e3136aa9cbaad77020770312dbaa80286e30',
                    'verify_reference_fidelity.py': 'b708b3826e4347bb9df4e47e7bf172eddb438e3e70d770e5e6040a9d12d4d37b'}
        self.assertEqual(compiler_inputs_digest(recorded),
                         '4f5a248fb220e880511758b2bf82f3ab9c82814f7326a0c2771161a67917cbc4')

    def test_a_changed_template_or_compiler_cannot_reuse_the_old_approval(self):
        for name in REVIEWED_INPUTS:
            profile, review = old_approval()
            changed = compiler_inputs_digest({**REVIEWED_INPUTS, name: checksum('changed ' + name)})
            with self.subTest(changed=name, attempt='old profile, new output'):
                output, receipts = output_of(profile, changed)
                result = self.resolve(profile, output, receipts, review)
                self.assertNotEqual(result['status'], 'eligible')
                self.assertIn('output_outside_reviewed_profile', result['reasons'])
            with self.subTest(changed=name, attempt='profile rewritten to the new compiler'):
                moved = rebound(profile, compiler_digest=changed)
                output, receipts = output_of(moved, changed)
                result = self.resolve(moved, output, receipts, review)
                self.assertEqual(result['status'], 'pending')
                self.assertIn('shared_profile_scope_not_bound', result['reasons'])
                self.assertIn('independent_shared_review_missing', result['reasons'])
            with self.subTest(changed=name, attempt='new profile package, old review record'):
                raw = moved.scope_document()
                package = CataloguePackage((CataloguePackageFile('contracts/shared-profile.json',
                    hashlib.sha256(raw).hexdigest(), len(raw), 'application/json', 'other'),))
                repackaged = replace(moved, package_digest=package.package_digest)
                output, receipts = output_of(repackaged, changed)
                result = self.resolve(repackaged, output, receipts, review)
                self.assertEqual(result['status'], 'pending')
                self.assertIn('independent_shared_review_missing', result['reasons'])

    def test_a_changed_scope_cannot_reuse_the_old_approval(self):
        profile, review = old_approval()
        checkers = dict(profile.checker_digests)
        changes = {'component_type': {'component_type': 'service_reference'},
                   'compiler_method': {'compiler_method': 'openapi_reference/v3'},
                   'checker': {'checker_digests': tuple({**checkers,
                                                         'secret_scan': checksum('other scanner')}.items())},
                   'criteria': {'criteria_digest': checksum('other criteria')},
                   'instructions': {'instructions_digest': checksum('other instructions')},
                   'identity': {'identity': 'reference_pipeline_copy'},
                   'producer': {'producer_family': 'anthropic'}}
        for label, change in changes.items():
            with self.subTest(scope=label):
                moved = rebound(profile, **change)
                output, receipts = output_of(moved, moved.compiler_digest)
                result = self.resolve(moved, output, receipts, review)
                self.assertNotEqual(result['status'], 'eligible')
                self.assertIn('independent_shared_review_missing', result['reasons'])
        with self.assertRaises(ValueError):
            rebound(profile, consumption_effects=('reads_fs', 'network'))

    def test_the_scope_binding_is_the_guard_that_refuses_reuse(self):
        """Known-wrong control: without the scope binding, the changed template would reuse the approval."""
        profile, review = old_approval()
        old_scope = profile.scope_document()
        changed = compiler_inputs_digest({**REVIEWED_INPUTS,
                                          'templates/operation-guidance.md': checksum('changed template')})
        moved = rebound(profile, compiler_digest=changed)
        output, receipts = output_of(moved, changed)
        self.assertEqual(self.resolve(moved, output, receipts, review)['status'], 'pending')
        with patch.object(SharedReferenceProfile, 'scope_document', lambda _self: old_scope):
            self.assertEqual(self.resolve(moved, output, receipts, review)['status'], 'eligible',
                             'the control must show that only the scope binding stops this reuse')


if __name__ == '__main__':
    unittest.main()
