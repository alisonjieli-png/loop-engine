"""Explicit experiment implementation bindings; metadata never grants execution."""

from __future__ import annotations

from dataclasses import dataclass

from .embodiments import (
    durable_reactive,
    fresh_process,
    long_lived_session,
    native,
    parallel_portfolio,
    pooled_sessions,
)


@dataclass(frozen=True)
class Embodiment:
    name: str
    runner: object
    folder: str
    placement: str
    hypothesis: str


IMPLEMENTED = (
    Embodiment(
        "native",
        native.run,
        "native",
        "in_process",
        "Measure the cost of native canonical Loop execution.",
    ),
    Embodiment(
        "fresh_process",
        fresh_process.run,
        "process_per_step",
        "one_process_per_packet",
        "Measure fresh-process separation and startup cost.",
    ),
    Embodiment(
        "long_lived_session",
        long_lived_session.run,
        "long_lived_session",
        "one_persistent_process",
        "Amortize startup while resetting explicit state per packet.",
    ),
    Embodiment(
        "pooled_sessions",
        pooled_sessions.run,
        "session_pool",
        "bounded_process_pool",
        "Measure process reuse and bounded parallel independent sessions.",
    ),
    Embodiment(
        "parallel_portfolio",
        parallel_portfolio.run,
        "parallel_portfolio",
        "independent_candidate_processes",
        "Publish independently verified alternatives as they complete.",
    ),
    Embodiment(
        "durable_reactive",
        durable_reactive.run,
        "durable_reactive",
        "canonical_durable_scheduler",
        "Preserve activation and history identity across process lifetimes.",
    ),
)


def select(name: str) -> Embodiment:
    for item in IMPLEMENTED:
        if item.name == name:
            return item
    raise ValueError(
        "embodiment unavailable; implemented: " + ", ".join(i.name for i in IMPLEMENTED)
    )


def inventory() -> list[dict]:
    return [
        {
            "name": i.name,
            "folder": i.folder,
            "placement": i.placement,
            "hypothesis": i.hypothesis,
            "runtime_type": "Loop",
            "backend": "trusted_deterministic_workload",
            "model_quality_proven": False,
        }
        for i in IMPLEMENTED
    ]
