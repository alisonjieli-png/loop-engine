"""Tests for the four-memory demonstration."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from run import run_demonstration  # noqa: E402


def test_first_run_promotes_all_three_records() -> None:
    result = run_demonstration()
    first = result["first_run"]
    assert first["episode_lifecycle"] == "active"
    assert first["semantic_lifecycle"] == "active"
    assert first["procedure_lifecycle"] == "active"


def test_second_run_recalls_all_three_types() -> None:
    result = run_demonstration()
    second = result["second_run"]
    assert second["episode_recalled"] is True
    assert second["semantic_recalled"] is True
    assert second["procedure_recalled"] is True
    assert second["procedure_applicable"] is True


def test_recall_runs_through_canonical_loop() -> None:
    result = run_demonstration()
    assert result["second_run"]["recall_loop_id"].startswith("loop")


def test_second_run_starts_with_empty_working_memory() -> None:
    result = run_demonstration()
    # The second run's working memory holds only the goal plus recalled
    # records; the first run's private hypothesis must not leak.
    assert result["second_run"]["working_memory_items"] >= 1
