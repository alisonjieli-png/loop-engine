"""Serve previously verified portfolio values without reactivating producers."""

from __future__ import annotations

import json
import random
from pathlib import Path

from loop_engine.core.reactive_output_store import SQLiteReactiveOutputStore
from loop_engine.loop.reactive_contracts import PortfolioView
from loop_engine.loop.reactive_outputs import OutputQuery

from .contracts import TaskCase, WorkPacket, digest, identifier
from .runtime import check_candidate
from .storage import confined_root


def view(root: Path, task: TaskCase, options: dict) -> dict:
    root = confined_root(root, create=False)
    database = root / "portfolio.sqlite"
    if not database.is_file() or database.is_symlink():
        raise ValueError("verified portfolio is unavailable")
    mode = options.get("view", "best")
    if mode not in ("best", "all_verified", "random"):
        raise ValueError("unknown serving view")
    seed = options.get("seed", 0)
    if type(seed) is not int:
        raise ValueError("random seed must be an integer")
    store = SQLiteReactiveOutputStore(str(database))
    try:
        result = store.query(
            OutputQuery(
                "lab",
                digest(task.to_dict()),
                PortfolioView.VERIFIED_TOP_K,
                as_of_portfolio_version=options.get("version"),
            )
        )
        entries = result.entries
        if mode == "best":
            entries = entries[:1]
        elif mode == "random" and entries:
            entries = (random.Random(seed).choice(entries),)
        values = []
        for entry in entries:
            identifier(entry.candidate_ref)
            path = root / "attempts" / (entry.candidate_ref + ".json")
            if path.is_symlink():
                raise ValueError("candidate artifact symlink refused")
            attempt = json.loads(path.read_text())
            packet = WorkPacket.from_dict(attempt["packet"])
            if packet.task != task or packet.request_id != entry.candidate_ref:
                raise ValueError("served candidate identity mismatch")
            if not check_candidate(packet, attempt["candidate"])["accepted"]:
                raise ValueError(
                    "served candidate failed integrity or independent verification"
                )
            values.append(
                {
                    "candidate": entry.candidate_ref,
                    "value": attempt["candidate"]["value"],
                }
            )
        return {
            "record_type": "embodiment_serving/v1",
            "view": mode,
            "portfolio_version": result.snapshot.portfolio_version,
            "values": values,
            "seed": seed if mode == "random" else None,
            "producer_reactivated": False,
            "model_calls": 0,
        }
    finally:
        store.close()
