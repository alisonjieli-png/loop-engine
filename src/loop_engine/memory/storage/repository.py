"""Compatibility facade for the governed learning repository.

Typed passive records live in learning_records.py. Durable lifecycle behavior
lives in learning_cycle.py. The executable offline proof lives in
learning_cycle_checks.py so every module remains below the architecture cap.
"""
from __future__ import annotations

from .learning_cycle import CandidateJournal, default_memory_root
from .learning_records import (
    LearningDecision,
    LearningGovernanceEntry,
    LearningPolicy,
    LearningRecallResult,
    LearningRecordRef,
    LearningTransitionResult,
    LearningUseResult,
    LoopExecutionEvidence,
    candidate_from_dict,
)

__all__ = (
    "CandidateJournal",
    "LearningDecision",
    "LearningGovernanceEntry",
    "LearningPolicy",
    "LearningRecallResult",
    "LearningRecordRef",
    "LearningTransitionResult",
    "LearningUseResult",
    "LoopExecutionEvidence",
    "candidate_from_dict",
    "default_memory_root",
    "self_test",
)


def self_test() -> dict:
    """Run the focused offline governed-learning proof."""
    from .learning_cycle_checks import self_test as run_checks

    return run_checks()
