"""Shared immutable configuration for the five public text scenarios."""
from __future__ import annotations

from loop_engine.templates.model import InteractionMode


LIVE_INTERACTION_MODE = InteractionMode.AUTONOMOUS
LIVE_EXPECTED_STATUS = "ready"


TASK_SCENARIOS: tuple[
        tuple[str, str, InteractionMode, str], ...] = (
    ("01_model_portfolio.txt", "model-portfolio",
     InteractionMode.AUTONOMOUS, "ready"),
    ("02_repository_audit.txt", "repository-audit",
     InteractionMode.AUTONOMOUS, "abstain_required"),
    ("03_data_standardization.txt", "data-standardization",
     InteractionMode.AUTONOMOUS, "ready"),
    ("04_source_digestion.txt", "source-digestion",
     InteractionMode.ASK_WHEN_MATERIAL, "needs_clarification"),
    ("05_customer_prediction.txt", "customer-prediction",
     InteractionMode.AUTONOMOUS, "ready"),
)
