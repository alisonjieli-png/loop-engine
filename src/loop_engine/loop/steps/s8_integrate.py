"""STEP 8 — Integrate accepted results, update the plan, commit + distill.

CONTRACT   PractitionerState + PassRecord  ->  committed PractitionerState
REQUIRED   no (optional; the route node commits by default)
WAYS       no-op (route commits) · distill shortcuts · update plan+checkpoint ·
           track dispositions for the no-orphan audit
EXTEND     provide an `integrate_commit` impl to commit domain artifacts; add a
           distillation trigger in self_improve.py.

Learn only from VERIFIED outcomes.  A recurring, verified, model-built decision
distills into a cheaper deterministic shortcut — the smart-over-time flywheel.
Every produced item is TRACKED for the fail-closed closure audit.
"""
from ...loop.kernel import default_integrate_commit
from ...code_nodes.self_improve import (could_this_be_cheaper, learn_from_cycle, Shortcut,
                          ShortcutStore)
from ...code_nodes.closure import (RunLedger, TrackedItem, audit_run, TERMINAL_DISPOSITIONS)

__all__ = ["default_integrate_commit", "could_this_be_cheaper",
           "learn_from_cycle", "Shortcut", "ShortcutStore", "RunLedger",
           "TrackedItem", "audit_run", "TERMINAL_DISPOSITIONS"]
