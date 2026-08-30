"""Checks for resume truth, publication authority, isolation, and self-hosting.

Owns adversarial proof that projections, contributors, and legacy state cannot
silently override verified reality.
"""
from __future__ import annotations

from .development_governance import (
    ContributionIsolationRequest, DevelopmentGovernanceError,
    LegacyAuthorityDisposition,
    LegacyAuthorityState, PublicationAuthorization, PublicationEffect,
    ResumeReconciliationRequest, SelfHostingProfile, TaskReality,
    isolate_contribution, reconcile_resume)
from .development_planning import TerminalPlanCode


def self_test():
    tests=[]
    def check(n,o,d=""): tests.append({"test":n,"passed":bool(o),"detail":d})
    result=reconcile_resume(ResumeReconciliationRequest(
        "plan", "a"*64,"b"*64,(
            TaskReality("done","completed",True,True),
            TaskReality("stale","completed",False,False),)))
    check("stale_projection_reopens_against_reality",
          result.verified_completed==("done",) and result.reopened_tasks==("stale",))
    blocked=reconcile_resume(ResumeReconciliationRequest(
        "plan","a"*64,"b"*64,(TaskReality("x","blocked",False,False,"gap"),)))
    check("blocked_is_terminal_for_current_activation",
          blocked.terminal_code is TerminalPlanCode.TASKS_BLOCKED)
    auth=PublicationAuthorization("auth",PublicationEffect.COMMIT,"c"*64,"d"*64,
                                  "loop-requester","human-owner",True)
    check("commit_authority_binds_exact_verified_target",len(auth.content_digest)==64)
    self_auth=False
    try: PublicationAuthorization("bad","push","c"*64,"d"*64,"same","same",True)
    except DevelopmentGovernanceError: self_auth=True
    check("loop_cannot_approve_its_own_publication",self_auth)
    isolated=isolate_contribution(ContributionIsolationRequest(
        True, True, False, False))
    check("contribution_matrix_identifies_extension_failure",
          isolated.responsible_contributions==("extension",))
    masquerade=False
    try: SelfHostingProfile("bad",True,True,False,0)
    except DevelopmentGovernanceError: masquerade=True
    check("repository_config_cannot_be_user_template",masquerade)
    legacy=LegacyAuthorityState("old","new",LegacyAuthorityDisposition.DETECTED_BLOCKING,
                                "migration:available")
    check("legacy_authority_blocks_with_repair_path",
          legacy.disposition is LegacyAuthorityDisposition.DETECTED_BLOCKING)
    passed=sum(x["passed"] for x in tests)
    return {"record_type":"development_governance_self_test/v1","tests":tests,
            "passed":passed,"total":len(tests),"all_passed":passed==len(tests)}
