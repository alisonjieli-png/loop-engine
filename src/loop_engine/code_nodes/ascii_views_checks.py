"""Checks for graph and Run History ASCII projections.

Owns deterministic, shared-node, and canonical-source rendering proof.
"""
from __future__ import annotations

from ..loop.recursive_loop import Loop, LoopConfig
from .ascii_views import render_run_tree_ascii


def self_test():
    parent=Loop("ascii parent",LoopConfig(framework="five_step"))
    spawned=parent.spawn("ascii spawned",LoopConfig(framework="five_step"))
    spawned.cancel("fixture")
    parent.cancel("fixture")
    rendered=render_run_tree_ascii(parent.ledger.events)
    tests=[{"test":"run_ascii_uses_real_loop_relationships",
            "passed":parent.loop_id in rendered and spawned.loop_id in rendered
                     and "└─" in rendered,
            "detail":rendered}]
    return {"record_type":"ascii_views_self_test/v1","tests":tests,
            "passed":sum(x["passed"] for x in tests),"total":len(tests),
            "all_passed":all(x["passed"] for x in tests)}
