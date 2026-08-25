"""steps/ — the nine kernel steps, one module each, in execution order.

This subpackage is the human- and LLM-facing READING SURFACE of the architecture.
Open ``steps/`` and you see the whole solver as nine files, each one kernel step,
in order.  Each ``sN_*`` module carries, at the top, that step's CONTRACT (input
-> output), its WAYS TO ANSWER (cheapest-first), and its EXTENSION POINT (where a
new capability goes) — then curates and re-exports the logic that serves it from
the implementation modules.

The implementation lives in the flat modules (kernel.py, biases.py, review_mode.py,
…) and is battle-tested there; these facades organize it without moving it, so the
structure teaches the architecture while the tests stay green.  The live, tested
map is ``step_registry`` (``--map``); these are its files.

    Step 1  s1_orient           reconstruct state + assemble context
    Step 2  s2_reconcile        reconcile goal / checkpoint / blueprint  (optional)
    Step 3  s3_assess           assess sufficiency + prepare resources    (optional)
    Step 4  s4_decide           generate, challenge, select the next action
    Step 5  s5_how              find / adapt / compose / design the method
    Step 6  s6_act              execute / build / delegate
    Step 7  s7_verify           interrogate + test the result
    Step 8  s8_integrate        integrate + commit + distill              (optional)
    Step 9  s9_route            continue / branch / reset / close / finish
"""
from . import (s1_orient, s2_reconcile, s3_assess, s4_decide, s5_how, s6_act,
               s7_verify, s8_integrate, s9_route)

__all__ = ["s1_orient", "s2_reconcile", "s3_assess", "s4_decide", "s5_how",
           "s6_act", "s7_verify", "s8_integrate", "s9_route"]
