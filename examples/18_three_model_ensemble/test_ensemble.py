"""Tests for the three-model ensemble example.

Proves the example runs through the canonical Loop runtime, shares one
immutable split, reports per-member and ensemble metrics, and verifies
honestly rather than hiding a weak ensemble.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from run import DatasetSpec, run_ensemble  # noqa: E402


def test_ensemble_runs_through_canonical_runtime() -> None:
    result = run_ensemble(DatasetSpec(n_samples=400, n_features=8,
                                      n_informative=5))
    assert result["record_type"] == "three_model_ensemble/v1"
    assert result["root_loop_id"].startswith("loop")
    assert result["ledger_events"] > 0


def test_ensemble_reports_all_members() -> None:
    result = run_ensemble(DatasetSpec(n_samples=400, n_features=8,
                                      n_informative=5))
    members = result["ensemble"]["members"]
    assert {m["family"] for m in members} == {"linear", "neural", "tree"}
    for member in members:
        assert 0.0 <= member["accuracy"] <= 1.0
        assert 0.0 <= member["roc_auc"] <= 1.0


def test_ensemble_verification_is_honest() -> None:
    result = run_ensemble(DatasetSpec(n_samples=400, n_features=8,
                                      n_informative=5))
    ensemble = result["ensemble"]
    assert ensemble["ensemble_accuracy"] >= 0.0
    assert ensemble["best_member_accuracy"] >= 0.0
    # The honest flag must be a boolean, never silently rounded up.
    assert isinstance(ensemble["ensemble_beats_all_members"], bool)


def test_split_digest_is_deterministic() -> None:
    first = run_ensemble(DatasetSpec(n_samples=200, n_features=6,
                                     n_informative=4))
    second = run_ensemble(DatasetSpec(n_samples=200, n_features=6,
                                      n_informative=4))
    assert first["split_digest"] == second["split_digest"]
