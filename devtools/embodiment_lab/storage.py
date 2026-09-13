"""Study artifacts and canonical output portfolios; no replacement event store."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from loop_engine.core.reactive_output_store import SQLiteReactiveOutputStore
from loop_engine.loop.atomic_primitives import LoopValue, LoopValueCreateRequest
from loop_engine.loop.reactive_contracts import (
    CandidateVerdict,
    MetricDirection,
    PortfolioPolicy,
    PortfolioView,
    RankingDimension,
)
from loop_engine.loop.reactive_outputs import (
    CandidateEvaluation,
    CandidateOutput,
    ConfidenceVector,
    OutputQuery,
    PortfolioBuildRequest,
    build_output_portfolio,
)

from .contracts import WorkPacket, canonical, digest
from .runtime import check_candidate, save_history


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def confined_root(path: Path, *, create: bool) -> Path:
    path = path.absolute()
    if path == Path(path.anchor) or ".." in path.parts:
        raise ValueError("a specific confined directory is required")
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("symlink output roots are refused")
    if create:
        path.mkdir(mode=0o700, parents=True, exist_ok=False)
    elif not path.is_dir():
        raise ValueError("study directory is missing")
    return path


def write_new(path: Path, value: object) -> None:
    if path.is_symlink():
        raise ValueError("symlink output refused")
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf8") as stream:
        stream.write(canonical(value) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


class ResultRecorder:
    """Projects independently checked candidates into the existing output store."""

    def __init__(self, root: Path):
        self.root = root
        self.store = SQLiteReactiveOutputStore(str(root / "portfolio.sqlite"))
        self.candidates: dict[str, list] = {}
        self.evaluations: dict[str, list] = {}
        self.policy = PortfolioPolicy(
            "lab.verified",
            "1.0.0",
            PortfolioView.VERIFIED_TOP_K,
            (RankingDimension("evidence_coverage", MetricDirection.MAXIMIZE),),
            16,
        )

    def record(self, packet: WorkPacket, candidate: dict) -> dict:
        verdict = check_candidate(packet, candidate)
        topic = digest(packet.task.to_dict())
        write_new(
            self.root / "attempts" / (packet.request_id + ".json"),
            {
                "packet": packet.to_dict(),
                "candidate": candidate,
                "verification": verdict,
            },
        )
        if isinstance(candidate, dict) and isinstance(candidate.get("ledger"), list):
            save_history(
                candidate["ledger"], packet.request_id, str(self.root / "history")
            )
        save_history(
            verdict.pop("ledger"),
            packet.request_id + ".verify",
            str(self.root / "history"),
        )
        if not verdict["accepted"]:
            return verdict
        value = LoopValue.create(
            candidate["value"],
            LoopValueCreateRequest(
                "embodiment_result/v1",
                "result",
                candidate["loop_id"],
                candidate["definition_ref"]["definition_id"],
            ),
        )
        stamp = now()
        output = CandidateOutput(
            packet.request_id,
            "lab",
            packet.request_id,
            packet.request_id,
            candidate["loop_id"],
            "result",
            topic,
            topic,
            topic,
            topic,
            value.to_ref(),
            (),
            digest({"method": packet.method}),
            candidate["definition_ref"]["content_digest"],
            stamp,
            stamp,
        )
        evaluation = CandidateEvaluation(
            packet.request_id + ".evaluation",
            packet.request_id,
            (verdict["verifier_loop_id"],),
            "lab.oracle",
            "1.0.0",
            CandidateVerdict.VERIFIED,
            stamp,
            ConfidenceVector(evidence_coverage=1.0, independent_verification=1.0),
        )
        self.store.append_candidate(output)
        self.store.append_evaluation(evaluation)
        self.candidates.setdefault(topic, []).append(output)
        self.evaluations.setdefault(topic, []).append(evaluation)
        portfolio = build_output_portfolio(
            PortfolioBuildRequest(
                "lab",
                topic,
                len(self.candidates[topic]),
                topic,
                stamp,
                self.policy,
                tuple(self.candidates[topic]),
                tuple(self.evaluations[topic]),
            )
        )
        self.store.append_portfolio(portfolio)
        verdict["portfolio_version"] = portfolio.portfolio_version
        return verdict

    def current(self, task_digest: str):
        return self.store.query(
            OutputQuery("lab", task_digest, PortfolioView.VERIFIED_TOP_K)
        )

    def close(self):
        self.store.close()
