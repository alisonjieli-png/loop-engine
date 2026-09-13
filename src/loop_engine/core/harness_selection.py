"""Select an eligible harness using exact, independently reviewed measurements.

Owns eligibility and deterministic ranking inside the existing harness boundary.
Uses the canonical Loop for selection and the existing Run History vocabulary.
Does not own execution authority, provider selection, task acceptance, or stores.
"""
from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import json

from .harness_execution_contracts import HarnessExecutionCapabilities
from .harness_selection_records import (
    HarnessSelectionDecision,HarnessSelectionPolicy,HarnessSelectionScope)


def _json(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)


def select_harness(policy, scope, registrations, *, provider_id, model_id):
    """Compare only matched populations; missing evidence preserves eligible order."""
    if not isinstance(policy,HarnessSelectionPolicy) or not isinstance(scope,HarnessSelectionScope):
        raise TypeError('harness selection needs typed policy and assignment scope')
    if type(registrations) not in (tuple,list) or not registrations:
        raise ValueError('selection needs an existing authorized registration sequence')
    from .external_harness import HarnessAdapterInfo
    if any(not isinstance(info,HarnessAdapterInfo) for info in registrations):
        raise TypeError('harness selection needs typed registered adapter facts')
    if len({x.harness_id for x in registrations})!=len(registrations):
        raise ValueError('authorized harness registrations must be unique')
    eligible=[];rejected=[];assessments=[]
    for info in registrations:
        capabilities=info.execution_capabilities or HarnessExecutionCapabilities()
        reasons=[]
        if not info.available:reasons.append('adapter_unavailable')
        requirements=scope.requirements
        reasons.extend('feature:'+x for x in requirements.required_features
                       if x not in capabilities.supported_features)
        reasons.extend('limit:'+x for x in requirements.required_limits
                       if x not in capabilities.enforced_limits)
        if requirements.allowed_isolations and capabilities.isolation not in requirements.allowed_isolations:
            reasons.append('isolation:'+capabilities.isolation)
        if reasons:rejected.append({'harness_id':info.harness_id,'reasons':reasons})
        else:eligible.append(info)
    def decision(order,reason,refs=()):
        return HarnessSelectionDecision(tuple(order),reason,scope.digest,policy.digest,
            _json(assessments),_json(rejected),tuple(refs))
    if not eligible:return decision((),'no_eligible_harness')
    if scope.evaluation_contract_ref!=policy.evaluation_contract_ref:
        return decision([x.harness_id for x in eligible],'evaluation_scope_mismatch')
    records={info.harness_id:[] for info in eligible}
    for info in eligible:
        for item in policy.evidence:
            trial=item.trial
            if (item.review.decision=='approved' and trial.harness_id==info.harness_id
                    and trial.adapter_version==info.adapter_version
                    and trial.provider_id==provider_id and trial.model_id==model_id
                    and trial.scope_digest==scope.digest):
                records[info.harness_id].append(trial)
    # One population and one evaluator identity are a comparison unit. No
    # unmatched task populations, evaluator revisions, or missing arms are pooled.
    populations=[{(t.population_digest,t.evaluator_ref,t.evaluator_digest)
                  for t in records[info.harness_id]} for info in eligible]
    common=set.intersection(*populations)
    matched={key:[t for t in values if (t.population_digest,t.evaluator_ref,t.evaluator_digest) in common]
             for key,values in records.items()}
    # Distinct Run History references are what count toward the minimum.
    if any(len({t.history_ref for t in matched[x.harness_id]})<policy.minimum_records for x in eligible):
        for info in eligible:
            assessments.append({'harness_id':info.harness_id,'matching_reviewed_records':len(matched[info.harness_id]),
                'verified_quality':None,'input_tokens':None,'output_tokens':None})
        return decision([x.harness_id for x in eligible],'insufficient_matched_reviewed_evidence')
    ranks=[];refs=[]
    for index,info in enumerate(eligible):
        trials=matched[info.harness_id]
        successes=sum(t.successes for t in trials);denominator=sum(t.observations for t in trials)
        quality=Fraction(successes,denominator)
        tokens=(sum(t.input_tokens+t.output_tokens for t in trials)/len(trials)
                if all(t.input_tokens is not None and t.output_tokens is not None for t in trials) else None)
        latency=(sum(t.elapsed_seconds for t in trials)/len(trials)
                 if all(t.elapsed_seconds is not None for t in trials) else None)
        metric=tokens if policy.objective=='verified_outcome_then_tokens' else latency
        ranks.append((-quality,metric is None,metric if metric is not None else 0,index,info.harness_id))
        assessments.append({'harness_id':info.harness_id,'matching_reviewed_records':len(trials),
            'successes':successes,'observations':denominator,'verified_quality':float(quality),
            'mean_tokens_per_trial':tokens,'mean_elapsed_seconds':latency,
            'generalization_confidence':'not_established'})
        refs.extend(t.history_ref for t in trials)
    return decision([item[-1] for item in sorted(ranks)],'ranked_matched_reviewed_evidence',refs)


def select_harness_as_loop(policy,scope,registrations,*,provider_id,model_id,parent):
    """Run one effect-free selection inside its owning canonical Practitioner."""
    from ..loop.loop_role import LoopRoleIdentity
    from ..loop.recursive_loop import LoopConfig,StepOutcome
    config=LoopConfig(framework='custom',custom_steps=('select',),
        allowable_modes=('deterministic',),preferred_modes=('deterministic',),
        delegated_modes=('deterministic',),exit_condition='steps_complete')
    owner=parent.spawn('select an eligible harness for the bound assignment',config,
        identity=LoopRoleIdentity('practitioner','practitioner.code_execution'))
    holder={}
    def handler(active,step,context):
        holder['decision']=select_harness(policy,scope,registrations,provider_id=provider_id,model_id=model_id)
        return StepOutcome(output=holder['decision'].reason,mode='deterministic',confidence=1.0)
    owner.run(handler=handler,max_steps=1)
    value=replace(holder['decision'],selection_loop_id=owner.loop_id)
    parent.ledger.record(loop_id=parent.loop_id,event='custom',action='harness_selection_assessed',
        **value.to_dict())
    return value


def self_test():
    from .harness_selection_checks import run_self_test_checks
    return run_self_test_checks()
