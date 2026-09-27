"""Bind reusable compiler review evidence to exact passive reference outputs.

The host supplies its trusted review records and verified check receipts. This
module reuses the panel's strict reader; it neither accepts a producer's approval
flag nor writes a new store. Resolution is eligibility evidence under a distinct
versioned policy. It grants no execution or publication authority and does not
reinterpret the older catalogue's Verified tier.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass

from loop_engine.core.service_runtime.catalogue_packages import CataloguePackage

from .records import canonical_bytes, digest, read_record
from .review_record import read_panel_review_record

POLICY = 'passive_reference_shared_review/v1'
CHECKS = ('integrity', 'rights_and_provenance', 'format', 'secret_scan',
          'source_correspondence', 'reference_closure', 'safety_scan', 'semantic_duplicates')
PROFILE_FIELDS = ('identity', 'package_digest', 'producer_family', 'criteria_digest', 'instructions_digest',
                  'compiler_method', 'compiler_digest', 'component_type', 'checker_digests', 'consumption_effects')
SHA = re.compile(r'[0-9a-f]{64}\Z')
METHOD = re.compile(r'[a-z][a-z0-9_.-]*(?:/[a-z0-9_.-]+)*/v[1-9][0-9]*\Z')


def _digest(value):
    if type(value) is not str or SHA.fullmatch(value) is None:
        raise ValueError('shared_profile_digest_invalid')
    return value


def compiler_inputs_digest(inputs):
    """The compiler identity: one digest over every input file that shapes an output.

    `inputs` maps each input path to its SHA-256: the compiler code, its guidance
    templates, its parameters and its check code. A changed template is a changed
    input, so it is a different compiler identity and cannot reuse a review of the
    old one. The encoding is the one the reference compiler's build identity uses.
    """
    if type(inputs) is not dict or not inputs:
        raise ValueError('compiler_inputs_required')
    for path, checksum in inputs.items():
        if type(path) is not str or not path.strip() or len(path) > 512:
            raise ValueError('compiler_input_path_invalid')
        _digest(checksum)
    encoded = (json.dumps(inputs, indent=2, sort_keys=True) + '\n').encode()
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class SharedReferenceProfile:
    """Host-selected profile identity, reviewed subject and applicable output scope."""

    identity: str
    package_digest: str
    producer_family: str
    criteria_digest: str
    instructions_digest: str
    compiler_method: str
    compiler_digest: str
    component_type: str
    checker_digests: tuple
    consumption_effects: tuple = ('reads_fs',)

    def __post_init__(self):
        for value in (self.package_digest, self.criteria_digest, self.instructions_digest, self.compiler_digest):
            _digest(value)
        for value in (self.identity, self.producer_family, self.component_type):
            if type(value) is not str or not value.strip() or len(value) > 160:
                raise ValueError('shared_profile_text_invalid')
        if type(self.compiler_method) is not str or METHOD.fullmatch(self.compiler_method) is None:
            raise ValueError('shared_profile_method_invalid')
        pairs = tuple(tuple(pair) for pair in self.checker_digests)
        if (any(len(pair) != 2 for pair in pairs) or len(pairs) != len(CHECKS)
                or {pair[0] for pair in pairs} != set(CHECKS)):
            raise ValueError('shared_profile_checks_incomplete')
        for _name, checksum in pairs:
            _digest(checksum)
        if tuple(self.consumption_effects) != ('reads_fs',):
            raise ValueError('shared_profile_effects_out_of_scope')
        object.__setattr__(self, 'checker_digests', tuple(sorted(pairs)))
        object.__setattr__(self, 'consumption_effects', ('reads_fs',))

    def to_dict(self):
        return {'record_type': 'shared_reference_profile/v1', **self.__dict__,
                'checker_digests': dict(self.checker_digests),
                'consumption_effects': list(self.consumption_effects)}

    @property
    def sha256(self):
        return digest(self.to_dict())

    def scope_document(self):
        """Scope bytes included in the reviewed package, without a digest cycle."""
        scope = self.to_dict()
        del scope['package_digest']
        scope['record_type'] = 'shared_reference_profile_scope/v1'
        return canonical_bytes(scope)

    @classmethod
    def from_dict(cls, value):
        part = read_record(value, 'shared_reference_profile/v1', PROFILE_FIELDS)
        if type(part['checker_digests']) is not dict:
            raise ValueError('shared_profile_checks_incomplete')
        fields = {name: part[name] for name in PROFILE_FIELDS}
        fields['checker_digests'] = tuple(fields['checker_digests'].items())
        return cls(**fields)


@dataclass(frozen=True)
class ReferenceCheckReceipt:
    """A host-resolved check result; issuer authenticity remains a host responsibility."""

    name: str
    package_digest: str
    compiler_digest: str
    checker_digest: str
    evidence_digest: str
    status: str
    findings: tuple = ()

    def __post_init__(self):
        if self.name not in CHECKS or self.status not in ('passed', 'failed', 'pending'):
            raise ValueError('reference_check_invalid')
        for value in (self.package_digest, self.compiler_digest, self.checker_digest, self.evidence_digest):
            _digest(value)
        if any(type(value) is not str or not value.strip() for value in self.findings):
            raise ValueError('reference_check_findings_invalid')
        object.__setattr__(self, 'findings', tuple(self.findings))


@dataclass(frozen=True)
class ReferenceOutputSubject:
    identity: str
    package_digest: str
    component_type: str
    compiler_method: str
    compiler_digest: str
    consumption_effects: tuple

    def __post_init__(self):
        _digest(self.package_digest)
        _digest(self.compiler_digest)
        if any(type(value) is not str or not value.strip() for value in
               (self.identity, self.component_type, self.compiler_method)):
            raise ValueError('reference_output_invalid')
        object.__setattr__(self, 'consumption_effects', tuple(self.consumption_effects))


def resolve_shared_review(profile, output, checks, review_records, *, calibration_inputs=None):
    """Resolve a supplied output against reviewed code, scope and exact check receipts.

    Review records come from the operator's existing trusted evidence location.
    An individual calibrated verdict may support this one-review profile even
    when the record's historical two-review item quorum was not reached. That
    record keeps its original outcome; this resolution uses a new named policy.
    """
    if not isinstance(profile, SharedReferenceProfile) or not isinstance(output, ReferenceOutputSubject):
        raise TypeError('typed_shared_profile_subjects_required')
    reasons, receipts, decision_refs, approving_families = [], {}, [], set()
    if (output.component_type != profile.component_type
            or output.compiler_method != profile.compiler_method
            or output.compiler_digest != profile.compiler_digest
            or output.consumption_effects != profile.consumption_effects):
        reasons.append('output_outside_reviewed_profile')
    expected_checkers = dict(profile.checker_digests)
    for receipt in checks:
        if not isinstance(receipt, ReferenceCheckReceipt):
            raise TypeError('typed_reference_receipt_required')
        if receipt.name in receipts:
            raise ValueError('duplicate_reference_check')
        receipts[receipt.name] = receipt
        if (receipt.package_digest != output.package_digest
                or receipt.compiler_digest != output.compiler_digest
                or receipt.checker_digest != expected_checkers[receipt.name]):
            reasons.append('check_binding_mismatch:' + receipt.name)
        if receipt.status != 'passed':
            reasons.append('check_not_passed:' + receipt.name)
        reasons.extend('unresolved_finding:' + receipt.name + ':' + value for value in receipt.findings)
    reasons.extend('check_missing:' + name for name in CHECKS if name not in receipts)

    rejected = False
    for supplied in review_records:
        # Retain the established model identity, calibration, call/decision,
        # package, precheck and fixture checks. The caller cannot replace them
        # with a boolean claiming that a pipeline is qualified.
        record = read_panel_review_record(supplied, allow_fixture=False,
                                          calibration_inputs=calibration_inputs)
        reviewers = {row['reviewer_id']: row for row in record['reviewers']}
        for row in record['rows']:
            if row['identity'] != profile.identity or row['body_sha256'] != profile.package_digest:
                continue
            subject = row['subject']
            package = CataloguePackage.from_dict(subject['package'])
            scope = profile.scope_document()
            scope_files = [entry for entry in package.files if entry.path == 'contracts/shared-profile.json']
            if (package.package_digest != profile.package_digest or len(scope_files) != 1
                    or scope_files[0].digest != hashlib.sha256(scope).hexdigest()
                    or scope_files[0].size_bytes != len(scope)):
                reasons.append('shared_profile_scope_not_bound')
                continue
            if (subject['criteria_sha256'] != profile.criteria_digest
                    or subject['instructions_sha256'] != profile.instructions_digest
                    or subject['producer']['family'] != profile.producer_family):
                reasons.append('shared_review_subject_mismatch')
                continue
            if row['prechecks']['refused']:
                reasons.append('shared_subject_prechecks_refused')
            if record['calibration'] is None:
                reasons.append('shared_reviewer_calibration_missing')
                continue
            for decision in row['decisions']:
                reviewer = reviewers[decision['reviewer_id']]
                if reviewer['family'] == profile.producer_family:
                    reasons.append('producer_review_cannot_qualify')
                    continue
                decision_refs.append({'record_sha256': digest(record), 'reviewer_id': reviewer['reviewer_id'],
                                      'call_ref': decision['call_ref'], 'decision': decision['decision']})
                if decision['decision'] == 'reject':
                    rejected = True
                    reasons.append('shared_profile_rejected')
                elif decision['decision'] == 'approve':
                    approving_families.add(reviewer['family'])
    if not approving_families:
        reasons.append('independent_shared_review_missing')
    reasons = sorted(set(reasons))
    status = 'rejected' if rejected else 'eligible' if not reasons else 'pending'
    return {'record_type': 'shared_reference_review_resolution/v1', 'policy': POLICY,
            'profile_sha256': profile.sha256, 'output_identity': output.identity,
            'package_digest': output.package_digest, 'status': status, 'reasons': reasons,
            'semantic_review_families': sorted(approving_families), 'shared_review_evidence': decision_refs,
            'check_evidence': {name: receipt.evidence_digest for name, receipt in sorted(receipts.items())},
            'may_reuse_shared_semantic_review': status == 'eligible',
            'approves_catalogue_component': False, 'grants_execution_authority': False,
            'publishes_component': False}
