"""Type-specific verification plans, with targeted reuse and no approval side effect.

Evidence availability comes from the host's existing evidence resolver. A plan
does not validate an evidence issuer, grant effects, or promote a candidate.

A plan describes check and review work. It is not the admission rule. The rule
in force is the approval row of the decision table in AGENTS.md: deterministic
prechecks, pinned provenance and one screening call by a calibrated reviewer
from another family before publication. A plan that needs no reviewer does not
remove that screening call.
"""
from dataclasses import dataclass

KINDS = ('source_reference', 'instruction', 'deterministic_tool', 'integration', 'composition', 'binary_binding')
SCOPES = frozenset({'metadata', 'body', 'contract', 'dependencies', 'effects', 'placement', 'provenance', 'compiler'})
AUTOMATED = ('integrity', 'rights_and_provenance', 'secret_scan', 'format')


@dataclass(frozen=True)
class VerificationNeed:
    component_kind: str
    changed_scopes: tuple = ('body', 'contract', 'dependencies', 'effects', 'placement', 'provenance')
    reusable_checks: tuple = ()
    qualified_reference_pipeline: bool = False
    independent_behavior_oracle: bool = False
    unresolved_findings: tuple = ()
    elevated_effects: bool = False

    def __post_init__(self):
        if type(self.component_kind) is not str or not self.component_kind.strip() or not set(self.changed_scopes) <= SCOPES:
            raise ValueError('unsupported_verification_need')
        if any(type(value) is not bool for value in (self.qualified_reference_pipeline, self.independent_behavior_oracle, self.elevated_effects)):
            raise ValueError('verification_flags_require_booleans')
        if any(not isinstance(value, str) or not value for value in (*self.reusable_checks, *self.unresolved_findings)):
            raise ValueError('verification_evidence_names_invalid')
        for field in ('changed_scopes', 'reusable_checks', 'unresolved_findings'):
            object.__setattr__(self, field, tuple(getattr(self, field)))


def plan_verification(need: VerificationNeed) -> dict:
    """Select the smallest applicable check set, retaining all unresolved findings."""
    checks = list(AUTOMATED)
    reviews, review_scope, shared = 0, [], False
    if need.component_kind == 'source_reference':
        checks += ['source_correspondence', 'reference_closure']
        if not need.qualified_reference_pipeline:
            reviews, shared = 1, True
            review_scope = ['extraction_pipeline_and_guidance_template']
    elif need.component_kind == 'instruction':
        reviews = 1
        review_scope = ['meaning_applicability_and_effects']
    elif need.component_kind == 'deterministic_tool':
        checks += ['contract_cases', 'known_wrong_controls', 'bounded_execution']
        if not need.independent_behavior_oracle:
            reviews, review_scope = 1, ['contract_and_behavior_oracle']
    elif need.component_kind == 'integration':
        checks += ['dependency_binding', 'protocol_cases', 'effect_boundary', 'cancellation_and_retry']
        reviews, review_scope = 1, ['integration_semantics']
    elif need.component_kind == 'composition':
        checks += ['dependency_binding', 'port_compatibility', 'composition_cases', 'effect_boundary']
        reviews, review_scope = 1, ['new_composition_logic_only']
    elif need.component_kind == 'binary_binding':
        checks += ['build_or_publisher_provenance', 'platform_binding', 'binary_interface_cases', 'effect_boundary']
        reviews, review_scope = 1, ['source_or_adapter_contract; not opaque binary text']
    else:
        checks += ['declared_contract', 'declared_effects']
        reviews, review_scope = 1, ['select_applicable_checks_for_new_component_type']
    if need.elevated_effects:
        checks.append('effect_boundary')
        reviews = max(reviews, 2)
        review_scope.append('elevated_effects')
    if need.unresolved_findings:
        reviews = max(reviews, 1)
        review_scope.append('unresolved_findings_only')
    invalidated = {
        'integrity': {'body', 'contract', 'dependencies', 'effects', 'placement', 'provenance', 'compiler', 'metadata'},
        'rights_and_provenance': {'body', 'provenance', 'dependencies'},
        'secret_scan': {'body', 'contract', 'dependencies', 'metadata'},
        'format': {'body', 'contract', 'placement', 'metadata'},
        'source_correspondence': {'body', 'provenance', 'compiler'},
        'reference_closure': {'body', 'dependencies', 'compiler'},
        'contract_cases': {'body', 'contract', 'dependencies', 'compiler'},
        'known_wrong_controls': {'body', 'contract', 'dependencies', 'compiler'},
        'bounded_execution': {'body', 'dependencies', 'effects', 'compiler'},
        'dependency_binding': {'body', 'contract', 'dependencies'},
        'port_compatibility': {'body', 'contract', 'dependencies'},
        'composition_cases': {'body', 'contract', 'dependencies', 'effects'},
        'protocol_cases': {'body', 'contract', 'dependencies', 'effects'},
        'effect_boundary': {'body', 'contract', 'dependencies', 'effects', 'placement'},
        'cancellation_and_retry': {'body', 'contract', 'dependencies', 'effects'},
        'build_or_publisher_provenance': {'body', 'provenance', 'dependencies'},
        'platform_binding': {'body', 'dependencies'},
        'binary_interface_cases': {'body', 'contract', 'dependencies'},
        'declared_contract': {'body', 'contract', 'compiler'},
        'declared_effects': {'body', 'effects', 'dependencies', 'placement'},
    }
    checks = list(dict.fromkeys(checks))
    reusable = [check for check in checks if check in need.reusable_checks
                and not set(need.changed_scopes) & invalidated[check]]
    # A host-confirmed unchanged semantic subject can reuse a previous review.
    if (not set(need.changed_scopes) & {'body', 'contract', 'dependencies', 'effects', 'placement', 'provenance', 'compiler'}
            and 'semantic_review' in need.reusable_checks and not need.unresolved_findings and not need.elevated_effects):
        reviews = 0
        review_scope = []
        reusable.append('semantic_review')
    return {'record_type': 'component_verification_plan/v1', 'component_kind': need.component_kind,
            'run_checks': [check for check in checks if check not in reusable], 'reuse_checks': reusable,
            'independent_reviewers': reviews, 'exclude_producer_family': reviews > 0,
            'review_scope': review_scope, 'review_shared_pipeline_once': shared,
            'unresolved_findings': list(need.unresolved_findings),
            'evidence_reuse_requires_host_resolution': True, 'approves_component': False,
            'grants_execution_authority': False}
