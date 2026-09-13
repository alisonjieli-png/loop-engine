"""Immutable contracts for selecting a harness for one governed assignment.

Belongs to the existing external-harness boundary. These are passive records,
not graph vertices, an intelligence store, or execution authority. Reviewed
measurements remain distinct from eligibility, ranking, and task acceptance.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
import re

from .harness_execution_contracts import HarnessExecutionRequirements, valid_harness_id


def content_digest(value) -> str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),
        ensure_ascii=False,allow_nan=False).encode('utf-8')).hexdigest()


def exact_text(value, name):
    if (type(value) is not str or not value or value!=value.strip()
            or len(value)>512 or any(ord(c)<32 for c in value)):
        raise ValueError(name+' must be bounded exact text')


def exact_digest(value, name):
    if type(value) is not str or not re.fullmatch('[0-9a-f]{64}',value):
        raise ValueError(name+' must be a SHA-256 digest')


def count(value, name, *, positive=False):
    if type(value) is not int or value < (1 if positive else 0):
        raise ValueError(name+' must be a nonnegative integer')


def response_contract_digest(expectation, policy) -> str:
    """Bind the schema and normalization, excluding per-occurrence identities."""
    return content_digest({'contract_ref':expectation.output_contract_ref,
        'schema':json.loads(expectation.schema_json),
        'normalization':asdict(policy) if policy is not None else None})


@dataclass(frozen=True)
class HarnessSelectionScope:
    """Exact assignment contract, owning profile, and configured resource policy."""
    operation_contract_ref: str
    response_contract_digest: str
    profile_ref: str
    resource_profile_digest: str
    execution_settings_digest: str
    owning_definition_digest: str
    evaluation_contract_ref: str = 'response_admission/v1'
    requirements: HarnessExecutionRequirements = HarnessExecutionRequirements()
    version: str = '1.0.0'

    def __post_init__(self):
        for name in ('operation_contract_ref','profile_ref','evaluation_contract_ref'):
            exact_text(getattr(self,name),name)
        for name in ('response_contract_digest','resource_profile_digest','execution_settings_digest','owning_definition_digest'):
            exact_digest(getattr(self,name),name)
        if not re.search(r'(?:/v[1-9][0-9]*|@[0-9]+\.[0-9]+\.[0-9]+)$',self.operation_contract_ref):
            raise ValueError('operation contract must carry an explicit version')
        if not re.fullmatch(r'(?:practitioner|intelligence|solution)\.[A-Za-z0-9_.-]+@[0-9]+\.[0-9]+\.[0-9]+',self.profile_ref):
            raise ValueError('selection scope needs an exact owning Loop profile')
        if not isinstance(self.requirements,HarnessExecutionRequirements) or self.version!='1.0.0':
            raise ValueError('selection scope requires typed requirements and a supported version')

    @property
    def digest(self):return content_digest(asdict(self))

    def to_dict(self):return {'record_type':'harness_selection_scope/v1',**asdict(self)}


@dataclass(frozen=True)
class HarnessTrialEvidence:
    """One frozen measured trial. Missing measurements remain unknown."""
    trial_id: str
    harness_id: str
    adapter_version: str
    provider_id: str
    model_id: str
    scope_digest: str
    population_digest: str
    evaluator_ref: str
    evaluator_digest: str
    subject_digest: str
    history_ref: str
    history_digest: str
    successes: int
    observations: int
    physical_model_calls: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    elapsed_seconds: float | None = None
    cost: float | None = None
    version: str = '1.0.0'

    def __post_init__(self):
        if not valid_harness_id(self.harness_id):raise ValueError('invalid measured harness identity')
        for name in ('trial_id','adapter_version','provider_id','model_id','evaluator_ref','history_ref'):
            exact_text(getattr(self,name),name)
        for name in ('scope_digest','population_digest','evaluator_digest','subject_digest','history_digest'):
            exact_digest(getattr(self,name),name)
        count(self.successes,'successes');count(self.observations,'observations',positive=True)
        if self.successes>self.observations or self.version!='1.0.0':
            raise ValueError('invalid measured denominator or evidence version')
        for name in ('physical_model_calls','input_tokens','output_tokens'):
            value=getattr(self,name)
            if value is not None:count(value,name)
        for name in ('elapsed_seconds','cost'):
            value=getattr(self,name)
            if value is not None and (type(value) not in (int,float) or not math.isfinite(value) or value<0):
                raise ValueError(name+' must be finite, nonnegative, or unknown')

    @property
    def digest(self):return content_digest(asdict(self))

    def to_dict(self):return {'record_type':'harness_trial_evidence/v1',**asdict(self)}


@dataclass(frozen=True)
class HarnessEvidenceReview:
    """Host-issued independent review bound to the exact measured record.

The record does not perform the review or turn model confidence into approval.
The host supplies the independently verified outcome and immutable source refs.
"""
    trial_digest: str
    reviewer_ref: str
    review_evidence_ref: str
    review_evidence_digest: str
    decision: str = 'approved'
    version: str = '1.0.0'

    def __post_init__(self):
        exact_digest(self.trial_digest,'reviewed trial digest')
        exact_digest(self.review_evidence_digest,'review evidence digest')
        exact_text(self.reviewer_ref,'reviewer reference')
        exact_text(self.review_evidence_ref,'review evidence reference')
        if self.decision not in ('approved','rejected') or self.version!='1.0.0':
            raise ValueError('invalid independent review decision')


@dataclass(frozen=True)
class ReviewedHarnessEvidence:
    trial: HarnessTrialEvidence
    review: HarnessEvidenceReview

    def __post_init__(self):
        if not isinstance(self.trial,HarnessTrialEvidence) or not isinstance(self.review,HarnessEvidenceReview):
            raise TypeError('harness evidence and review must use their typed records')
        if self.review.trial_digest!=self.trial.digest:
            raise ValueError('review does not bind the exact measured trial')
        if self.review.reviewer_ref in (self.trial.trial_id,self.trial.harness_id):
            raise ValueError('a producer cannot approve its own trial')


@dataclass(frozen=True)
class HarnessSelectionPolicy:
    """Explicit opt-in ranking policy over already authorized adapter choices."""
    resource_profile_digest: str
    evidence: tuple[ReviewedHarnessEvidence,...]
    minimum_records: int
    objective: str = 'verified_outcome_then_tokens'
    evaluation_contract_ref: str = 'response_admission/v1'
    version: str = '1.0.0'

    def __post_init__(self):
        exact_digest(self.resource_profile_digest,'resource profile digest')
        if type(self.evidence) not in (tuple,list) or any(not isinstance(x,ReviewedHarnessEvidence) for x in self.evidence):
            raise TypeError('selection evidence must contain reviewed typed records')
        values=tuple(self.evidence)
        if len({x.trial.trial_id for x in values})!=len(values):
            raise ValueError('duplicate trial identities cannot inflate evidence')
        # One Run History reference is one trial. Repeated trials of the same
        # subject remain welcome; each has its own history.
        if len({x.trial.history_ref for x in values})!=len(values):
            raise ValueError('one Run History reference cannot count as several trials')
        object.__setattr__(self,'evidence',values)
        count(self.minimum_records,'minimum_records',positive=True)
        exact_text(self.evaluation_contract_ref,'evaluation contract reference')
        if self.objective not in ('verified_outcome_then_tokens','verified_outcome_then_latency') or self.version!='1.0.0':
            raise ValueError('unsupported selection objective or policy version')

    @property
    def digest(self):return content_digest(asdict(self))

    def to_dict(self):
        return {'record_type':'harness_selection_policy/v1',**asdict(self),'content_digest':self.digest}

    @classmethod
    def from_dict(cls,value):
        if type(value) is not dict or set(value)!={*cls.__dataclass_fields__,'record_type','content_digest'}:
            raise ValueError('harness selection policy has an invalid serialized shape')
        if value['record_type']!='harness_selection_policy/v1':
            raise ValueError('unsupported harness selection policy encoding')
        fields={name:value[name] for name in cls.__dataclass_fields__}
        if type(fields['evidence']) not in (list,tuple):raise TypeError('serialized evidence must be a sequence')
        evidence=[]
        for item in fields['evidence']:
            if type(item) is not dict or set(item)!={'trial','review'}:
                raise ValueError('reviewed evidence has an invalid serialized shape')
            if (type(item['trial']) is not dict or set(item['trial'])!=set(HarnessTrialEvidence.__dataclass_fields__)
                    or type(item['review']) is not dict or set(item['review'])!=set(HarnessEvidenceReview.__dataclass_fields__)):
                raise ValueError('trial or review fields do not match the versioned contract')
            evidence.append(ReviewedHarnessEvidence(HarnessTrialEvidence(**item['trial']),HarnessEvidenceReview(**item['review'])))
        fields['evidence']=tuple(evidence)
        result=cls(**fields)
        if value['content_digest']!=result.digest:raise ValueError('harness selection policy digest mismatch')
        return result


@dataclass(frozen=True)
class HarnessSelectionDecision:
    ordered_harness_ids: tuple[str,...]
    reason: str
    scope_digest: str
    policy_digest: str
    assessments_json: str
    rejected_json: str
    evidence_refs: tuple[str,...] = ()
    selection_loop_id: str = ''

    def to_dict(self):
        return {'record_type':'harness_selection_decision/v1',
            'ordered_harness_ids':list(self.ordered_harness_ids),'reason':self.reason,
            'scope_digest':self.scope_digest,'policy_digest':self.policy_digest,
            'assessments':json.loads(self.assessments_json),'rejected':json.loads(self.rejected_json),
            'evidence_refs':list(self.evidence_refs),'selection_loop_id':self.selection_loop_id,
            'provider_or_model_changed':False,'task_accepted':False}
