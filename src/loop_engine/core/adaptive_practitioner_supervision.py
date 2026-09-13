"""Deterministic progress and breakout laws for the adaptive Practitioner.

The semantic resolver may propose research, repair, or continuation. These
pure controls decide whether the proposal represents executable work and
whether repeated passes have changed the governed task state.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json

from .action_fence import ActionFencePolicy


@dataclass(frozen=True)
class PractitionerSupervisionPolicy:
    """Require real progress without imposing a numerical work ceiling."""

    require_executable_repair_delta: bool = True
    diagnose_identical_state_action_failure: bool = True
    action_fence: ActionFencePolicy = field(default_factory=ActionFencePolicy)


DEFAULT_SUPERVISION_POLICY = PractitionerSupervisionPolicy()


def supervision_context(services, state) -> dict:
    """Return exact progress facts without deciding how much work is enough."""
    latest = _progress_snapshot(services, state)
    repeated = latest in services.progress_snapshots
    return {
        "record_type": "practitioner_supervision_context/v2",
        "project_attempts": len(services.project_attempts),
        "verified_project_attempts": sum(
            bool(item.get("deterministic_checks_passed"))
            for item in services.project_attempts),
        "artifact_refs": sorted(str(key) for key in state.artifacts),
        "identical_state_action_failure_repeated": repeated,
        "progress_fingerprint": _snapshot_digest(latest),
        "recovery_rounds": services.recovery_rounds,
        "active_recovery_directive": (
            services.active_recovery_directive),
    }


def validate_progressing_action(decision, services) -> None:
    """Reject non-executable or explicitly repeated post-diagnosis actions."""
    capabilities = set(decision.required_capabilities)
    from .adaptive_practitioner_planning import action_needs_execution_capability
    if action_needs_execution_capability(decision.action_kind) and not capabilities:
        raise ValueError('This installed planner needs a registered execution capability for '
                         'the selected action. Bind an available capability or choose an '
                         'explicit delegation or terminal control; do not request an impossible method.')
    if (decision.action_kind == "REPAIR" and services.project_attempts
            and not capabilities):
        raise ValueError(
            "A repair after an executable attempt must bind a registered "
            "capability or stop honestly.")
    if services.active_recovery_directive:
        directive = services.active_recovery_directive
        forbidden = set(directive.get("forbidden_action_kinds", ()))
        if decision.action_kind in forbidden:
            raise ValueError(
                "The selected recovery directive forbids repeating this "
                "action kind without new evidence.")


def _progress_snapshot(services, state) -> tuple:
    """Observable progress projection, never an acceptance or result-cache key.

    Occurrence IDs, pass counters, confidence, estimated utility, and rewritten
    explanations do not establish progress. Complete records remain in history.
    A repeat only requests diagnosis by the existing model-led recovery panel.
    """
    unique_web_evidence = tuple(sorted({
        str(item.get("sha256") or "") for item in services.web_results
        if item.get("sha256")}))
    unique_source_evidence = tuple(sorted({
        str(item.get("digest") or "")
        for inspection in services.source_inspections
        for item in inspection.get("selected", ())
        if item.get("digest")}))
    projects = tuple(sorted({
        (str(item.get("manifest_digest") or ""),
         bool(item.get("deterministic_checks_passed")))
        for item in services.project_attempts}))
    host_evidence = tuple(sorted({_snapshot_digest({key:item.get(key) for key in (
        'capability_ref','surface','operation','ok','value','state_after','artifact_refs')})
        for item in getattr(services,'host_results',())
        if isinstance(item,dict) and item.get('record_type')=='host_operation_result/v1'}))
    action = services.action_history[-1] if services.action_history else {}
    action_fingerprint = hashlib.sha256(json.dumps(
        {key:action.get(key) for key in (
            'action_kind', 'inputs', 'required_capabilities', 'permissions')},
        sort_keys=True, separators=(",", ":"), default=str
    ).encode()).hexdigest() if action else ""
    verification = (
        services.verification_records[-1]
        if services.verification_records else {})
    verification_fingerprint = hashlib.sha256(json.dumps(
        {'verdict':verification.get('verdict'),
         'deterministic_checks_passed':verification.get('deterministic_checks_passed'),
         'operational_failures':[
             {key:item.get(key) for key in ('source','status','code','reason_code','error_code')}
             for item in verification.get('operational_failures',()) if isinstance(item,dict)]},
        sort_keys=True, separators=(",", ":"), default=str
    ).encode()).hexdigest() if verification else ""
    return (
        unique_web_evidence,
        unique_source_evidence,
        projects,
        tuple(sorted((str(key), _snapshot_digest(value))
                     for key,value in state.artifacts.items())),
        action_fingerprint,
        verification_fingerprint,
        host_evidence,
    )


def _snapshot_digest(snapshot: object) -> str:
    return hashlib.sha256(json.dumps(
        snapshot, sort_keys=True, separators=(",", ":"), default=str
    ).encode()).hexdigest()


def _material_snapshot(snapshot):
    return (*snapshot[:4],snapshot[6]) if snapshot is not None else None


def detect_stall(services, state) -> dict | None:
    """Return a typed stall signal; never choose a repair or terminal route."""
    snapshot = _progress_snapshot(services, state)
    previous = (
        services.progress_snapshots[-1]
        if services.progress_snapshots else None)
    repeated = snapshot in services.progress_snapshots
    unchanged_evidence = (previous is not None
                          and _material_snapshot(snapshot)==_material_snapshot(previous))
    diagnose_evidence = (getattr(getattr(services,'request',None),'diagnose_unchanged_evidence',False)
                         and unchanged_evidence)
    services.progress_snapshots.append(snapshot)
    if repeated or diagnose_evidence:
        services.unchanged_progress_snapshots += 1
    else:
        services.unchanged_progress_snapshots = 0
        if not unchanged_evidence:
            services.active_recovery_directive = None
    if (not DEFAULT_SUPERVISION_POLICY.
            diagnose_identical_state_action_failure
            or not (repeated or diagnose_evidence)):
        return None
    reasons = ([
        "observable evidence, executable action inputs, and verification "
        "status repeated; new occurrence IDs or explanations alone do not "
        "establish progress"] if repeated else [
        "the action may have changed, but no new source, web, host, project, "
        "or artifact evidence was recorded; determine whether continued "
        "exploration or a changed approach is justified"])
    finding = {
        "record_type": "practitioner_stall_signal/v2",
        "code": "RECOVERY_DIAGNOSIS_REQUIRED",
        "unchanged_snapshots": services.unchanged_progress_snapshots,
        "reasons": reasons,
        "progress_fingerprint": _snapshot_digest(snapshot),
        "trigger": ('repeated_observable_state_action' if repeated else 'unchanged_material_evidence'),
        "action_changed": previous is not None and snapshot[4]!=previous[4],
        "diagnosis_only": True,
        "progress_snapshot": {
            "unique_web_evidence": len(snapshot[0]),
            "unique_source_evidence": len(snapshot[1]),
            "project_attempts": len(snapshot[2]),
            "artifact_refs": len(snapshot[3]),
            "host_observations": len(snapshot[6]),
        },
    }
    services.supervision_findings.append(finding)
    return finding


def self_test():
    """Prove occurrence churn cannot hide stalls or erase real evidence."""
    from copy import deepcopy
    from types import SimpleNamespace
    tests=[]
    def check(name, passed):
        tests.append({'test':name,'passed':bool(passed)})
    def fixture():
        return SimpleNamespace(web_results=[],source_inspections=[],project_attempts=[],
            action_history=[{'action_kind':'REPAIR','inputs':{'path':'a'},
                'required_capabilities':['example.repair'],'permissions':[],
                'state_version':1,'decision_id':'old','reason':'first description'}],
            verification_records=[{'verdict':'repair','deterministic_checks_passed':False,
                'pass_number':1,'verifier_stage_occurrence_id':'old','notes':'first description'}],
            progress_snapshots=[],unchanged_progress_snapshots=0,supervision_findings=[],
            recovery_rounds=0,active_recovery_directive=None)
    state=SimpleNamespace(artifacts={'source':{'digest':'a'}},failures=('old explanation',))
    services=fixture()
    check('first_observation_does_not_claim_a_stall', detect_stall(services,state) is None)
    services.action_history[-1].update(state_version=2,decision_id='new',reason='rewritten',
        source_stage_occurrence_id='new-stage',confidence=0.99,budget={'estimated_cost':0.01})
    services.verification_records[-1].update(pass_number=2,verifier_stage_occurrence_id='new',
        verifier_semantic_call_id='new-call',notes='rewritten',subject={'action_occurrence_ref':'new'})
    state.failures=('different explanation of the same absent progress',)
    signal=detect_stall(services,state)
    check('new_metadata_and_explanations_do_not_hide_stalls', signal is not None)
    check('stall_requests_reasoning_not_a_terminal_route', signal['code']=='RECOVERY_DIAGNOSIS_REQUIRED'
          and 'route' not in signal and services.active_recovery_directive is None)
    for name, mutate in (
            ('new_action_inputs', lambda s,st:s.action_history[-1]['inputs'].update(path='b')),
            ('new_capability', lambda s,st:s.action_history[-1].update(required_capabilities=['example.other'])),
            ('new_permissions', lambda s,st:s.action_history[-1].update(permissions=['approved'])),
            ('artifact_content_under_same_key', lambda s,st:st.artifacts['source'].update(digest='b')),
            ('new_source_evidence', lambda s,st:s.source_inspections.append({'selected':[{'digest':'new'}]})),
            ('new_web_evidence', lambda s,st:s.web_results.append({'sha256':'new'})),
            ('new_project', lambda s,st:s.project_attempts.append({'manifest_digest':'new','deterministic_checks_passed':False})),
            ('verified_outcome', lambda s,st:s.verification_records[-1].update(deterministic_checks_passed=True)),
            ('new_operational_failure', lambda s,st:s.verification_records[-1].update(operational_failures=[{'source':'host','status':'failed'}])),
            ('new_host_state', lambda s,st:setattr(s,'host_results',[{'record_type':'host_operation_result/v1','state_after':'new','ok':True,'value':{}}])),
        ):
        s,st=fixture(),deepcopy(state)
        detect_stall(s,st); mutate(s,st)
        check(name+'_changes_observable_progress',detect_stall(s,st) is None)
    s,st=fixture(),deepcopy(state)
    detect_stall(s,st)
    s.action_history[-1]['inputs']['path']='b';detect_stall(s,st)
    s.action_history[-1]['inputs']['path']='a'
    check('non_adjacent_action_cycles_trigger_diagnosis',detect_stall(s,st) is not None)
    s,st=fixture(),deepcopy(state)
    s.request=SimpleNamespace(diagnose_unchanged_evidence=True)
    detect_stall(s,st);s.action_history[-1]['inputs']['path']='b'
    signal=detect_stall(s,st)
    check('optional_stable_evidence_check_distinguishes_changed_actions',signal is not None
          and signal['trigger']=='unchanged_material_evidence' and signal['action_changed'] is True
          and signal['diagnosis_only'] is True)
    s,st=fixture(),deepcopy(state)
    s.host_results=[{'record_type':'host_operation_result/v1','state_after':'a','ok':True,
                     'value':{'content':'same'},'result_digest':'first'}]
    detect_stall(s,st);s.host_results[0]['result_digest']='new-occurrence'
    check('host_result_occurrence_churn_is_not_new_evidence',detect_stall(s,st) is not None)
    return {'tests':tests,'passed':sum(t['passed'] for t in tests),'total':len(tests),
            'all_passed':all(t['passed'] for t in tests)}
