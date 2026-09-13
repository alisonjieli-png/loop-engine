"""Evaluate admitted responses through a separately registered verifier contract.

Owns deterministic response-obligation checks, not overall task acceptance.
Evaluator callbacks are trusted host bindings; model text cannot register one.
This is an existing Loop operation, not another runtime or evidence store.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import inspect
import re
from typing import Callable

from .harness_selection_records import exact_digest, exact_text

# The three verdict statuses an evaluator may issue; every comparison in
# the harness path names these, never retyped text.
PASSED, REJECTED, INCONCLUSIVE = 'passed', 'rejected', 'inconclusive'
EVALUATION_STATUSES = (PASSED, REJECTED, INCONCLUSIVE)


@dataclass(frozen=True)
class ResponseEvaluationContext:
    """The exact occurrence an evaluator is judging, passed to context-aware callbacks.

A callback declared with two parameters receives the admitted text and this
record, so a host oracle can bind its expected answer to the actual input
digest instead of judging text alone. One-parameter callbacks keep working.
"""
    semantic_call_id: str
    input_digest: str
    subject_contract_ref: str
    subject_contract_digest: str


@dataclass(frozen=True)
class ResponseEvaluationVerdict:
    status: str
    finding_codes: tuple[str,...] = ()

    def __post_init__(self):
        if self.status not in EVALUATION_STATUSES:
            raise ValueError('response evaluation status is not recognized')
        if type(self.finding_codes) not in (tuple,list):raise TypeError('finding codes must be a sequence')
        values=tuple(self.finding_codes)
        if (len(values)>16 or len(set(values))!=len(values)
                or any(type(x) is not str or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}',x) for x in values)):
            raise ValueError('evaluation findings must be bounded body-free codes')
        if self.status!=PASSED and not values:raise ValueError('an unsuccessful evaluation needs a finding code')
        object.__setattr__(self,'finding_codes',values)


@dataclass(frozen=True)
class HarnessResponseEvaluator:
    """Exact host registration; its source and qualification are host-attested.

The callback must be trusted, deterministic and effect-free. This binding is
not a sandbox for generated Python and grants no model, tool or file authority.
"""
    contract_ref: str
    implementation_digest: str
    qualification_ref: str
    qualification_digest: str
    subject_contract_ref: str
    subject_contract_digest: str
    evaluate: Callable[...,ResponseEvaluationVerdict] = field(repr=False,compare=False)
    version: str = '1.0.0'

    def __post_init__(self):
        exact_text(self.contract_ref,'response evaluation contract')
        exact_text(self.qualification_ref,'evaluator qualification reference')
        exact_digest(self.implementation_digest,'evaluator implementation digest')
        exact_digest(self.qualification_digest,'evaluator qualification digest')
        exact_text(self.subject_contract_ref,'evaluated subject contract reference')
        exact_digest(self.subject_contract_digest,'evaluated subject contract digest')
        if not re.search(r'(?:/v[1-9][0-9]*|@[0-9]+\.[0-9]+\.[0-9]+)$',self.contract_ref):
            raise ValueError('response evaluator contract must be versioned')
        if not callable(self.evaluate) or self.version!='1.0.0':
            raise TypeError('response evaluation requires an installed supported host binding')

    @property
    def receives_context(self) -> bool:
        """True when the callback declares a second parameter for the occurrence."""
        try:
            parameters=[p for p in inspect.signature(self.evaluate).parameters.values()
                        if p.kind in (p.POSITIONAL_ONLY,p.POSITIONAL_OR_KEYWORD)]
        except (TypeError,ValueError):
            return False
        return len(parameters)>=2


@dataclass(frozen=True)
class HarnessResponseEvaluation:
    contract_ref: str
    implementation_digest: str
    qualification_digest: str
    semantic_call_id: str
    input_digest: str
    response_digest: str
    status: str
    finding_codes: tuple[str,...]
    verifier_loop_id: str
    subject_contract_ref: str = ''
    subject_contract_digest: str = ''
    context_aware: bool = False

    def to_dict(self):
        # Version 2 binds the evaluated subject contract; a record without it
        # keeps the version 1 encoding it was issued with.
        encoding=('harness_response_evaluation/v2' if self.subject_contract_ref
                  else 'harness_response_evaluation/v1')
        body={key:value for key,value in asdict(self).items()
              if self.subject_contract_ref or key not in (
                  'subject_contract_ref','subject_contract_digest','context_aware')}
        return {'record_type':encoding,**body,
                'task_accepted':False,'external_effect_authorized':False}


@dataclass
class HarnessResponseEvaluationState:
    """Invocation-local observations; Run History owns the durable records."""
    evaluations: list[HarnessResponseEvaluation] = field(default_factory=list)
    attempt_start: int = 0

    def begin_attempt(self):self.attempt_start=len(self.evaluations)

    @property
    def latest(self):
        return self.evaluations[-1] if len(self.evaluations)>self.attempt_start else None


def evaluate_response_as_loop(binding,text,*,semantic_call_id,input_digest,parent):
    """A verifier Loop checks one response after its structural admission."""
    from ..loop.loop_contract import LoopContract
    from ..loop.loop_role import LoopRoleIdentity
    from ..loop.recursive_loop import LoopConfig,StepOutcome
    if not isinstance(binding,HarnessResponseEvaluator) or type(text) is not str:
        raise TypeError('response evaluation needs a typed host binding and admitted text')
    exact_digest(input_digest,'evaluated input digest')
    exact_text(semantic_call_id,'evaluated semantic call')
    config=LoopConfig(framework='custom',custom_steps=('evaluate',),
        allowable_modes=('deterministic',),preferred_modes=('deterministic',),
        delegated_modes=('deterministic',),exit_condition='steps_complete')
    owner=parent.spawn('evaluate the admitted response against its registered obligation',config,
        contract=LoopContract('registered response evaluation','code_only',
            input_roles=('admitted_response',),output_roles=('response_evaluation',),role='practitioner'),
        identity=LoopRoleIdentity('practitioner','practitioner.verifier'))
    holder={}
    occurrence=ResponseEvaluationContext(semantic_call_id,input_digest,
        binding.subject_contract_ref,binding.subject_contract_digest)
    context_aware=binding.receives_context
    def handler(active,step,context):
        try:
            verdict=(binding.evaluate(text,occurrence) if context_aware else binding.evaluate(text))
            if not isinstance(verdict,ResponseEvaluationVerdict):
                verdict=ResponseEvaluationVerdict('inconclusive',('evaluator_return_contract_invalid',))
        except Exception as error:
            verdict=ResponseEvaluationVerdict('inconclusive',('evaluator_exception:'+type(error).__name__,))
        holder['verdict']=verdict
        return StepOutcome(output='response_evaluation:'+verdict.status,mode='deterministic',confidence=1.0)
    owner.run(handler=handler,max_steps=1)
    if 'verdict' not in holder:
        raise RuntimeError('the verifier Loop did not run the registered evaluation')
    verdict=holder['verdict']
    result=HarnessResponseEvaluation(binding.contract_ref,binding.implementation_digest,
        binding.qualification_digest,semantic_call_id,input_digest,hashlib.sha256(text.encode()).hexdigest(),
        verdict.status,verdict.finding_codes,owner.loop_id,
        binding.subject_contract_ref,binding.subject_contract_digest,context_aware)
    parent.ledger.record(loop_id=parent.loop_id,event='custom',action='harness_response_evaluated',**result.to_dict())
    return result


def self_test():
    from .harness_selection_checks import run_response_evaluation_checks
    return run_response_evaluation_checks()
