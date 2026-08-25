"""STEP 7 — Independently interrogate inputs, outputs, and process.

CONTRACT   PractitionerState + ExecutionPlan + ResultPacket[]  ->  EvaluationPacket
REQUIRED   yes (you always verify — a degenerate result must not update state)
WAYS       deterministic checks · degeneracy detectors · contract check ·
           model interrogation · adversarial review
EXTEND     add a detector or interrogatory in review_mode.py; provide a `verify`
           impl for domain evaluators.

A constant / chance-level / empty / too-perfect result is DEGENERATE and
rejected — carrying no information is not success (AUC 0.5 is a coin flip).
"""
from ...loop.kernel import EvaluationPacket, default_verify
from ...code_nodes.review_mode import (review, ReviewReport, detect_constant_output,
                          detect_chance_level, detect_too_perfect,
                          INTERROGATORIES, REVIEW_VERDICTS)

__all__ = ["EvaluationPacket", "default_verify", "review", "ReviewReport",
           "detect_constant_output", "detect_chance_level",
           "detect_too_perfect", "INTERROGATORIES", "REVIEW_VERDICTS"]
