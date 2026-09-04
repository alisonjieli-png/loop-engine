"""The stage record's lifecycle across one run: load it, then close it.

Two small operations that have to happen at the edges of a run and nowhere
else. They live here because both are easy to wire into one exit and forget
about the others, which is exactly what happened: persistence was attached to
the success path while three failure exits returned before it, and the runs
that fail are the ones whose stages are worth the most.

Neither can fail a run. A stage record that raises is worse than a stage
record that is missing, and observation must not change the thing observed.
That cuts both ways — a defensive boundary hides your own mistakes as
effectively as the ones it was built for — so both report through the store
rather than swallowing silently where a caller could have noticed.

Owns:
    - load_prior_stages(): what earlier runs recorded, read once.
    - close_stages(): this run's stages, closed with their outcome.

Does not own: naming a stage (core.stage_fingerprint), storing one
(core.stage_store), or deciding anything from it.
"""
from __future__ import annotations

from pathlib import Path

#: The file a run's stages are written to, beside its history.
STAGE_FILE_NAME = "stages.jsonl"


def _stage_path(runs_dir) -> str:
    return str(Path(runs_dir) / STAGE_FILE_NAME) if runs_dir else ""


def load_prior_stages(services, runs_dir) -> int:
    """Read what earlier runs recorded. Returns rows loaded.

    Without this the store is write-only and every run begins as though
    nothing had ever been done before it.
    """
    try:
        services.prior_stages.path = _stage_path(runs_dir)
        return services.prior_stages.load()
    except Exception:                                   # noqa: BLE001
        return 0


def close_stages(services, runs_dir, *, helped) -> int:
    """Persist this run's stages with the outcome they actually had.

    Called from every exit, including the failing ones. A cancelled run
    passes ``helped=None``: cancellation says nothing about whether the work
    was going well, and recording it as failure would poison the evidence
    with the operator's timing.
    """
    try:
        return services.stage_store.close_run(
            helped=helped, path=_stage_path(runs_dir))
    except Exception:                                   # noqa: BLE001
        return 0


def self_test() -> dict:
    """Offline checks. No provider is contacted."""
    import tempfile
    from types import SimpleNamespace

    from .stage_fingerprint import SemanticStageFingerprint
    from .stage_store import StageStore

    tests = []

    def check(name, ok, detail=""):
        tests.append({"test": name, "passed": bool(ok), "detail": detail})

    stage = SemanticStageFingerprint(
        semantic_responsibility="inspect the supplied files",
        cognitive_phase="orient", knowns=("a manifest",))

    with tempfile.TemporaryDirectory() as root:
        first = SimpleNamespace(stage_store=StageStore(),
                                prior_stages=StageStore())
        first.stage_store.add(stage, run_id="r1")
        wrote = close_stages(first, root, helped=True)
        check("a run's stages are written where a later run will look",
              wrote == 1)

        second = SimpleNamespace(stage_store=StageStore(),
                                 prior_stages=StageStore())
        loaded = load_prior_stages(second, root)
        check("a later run loads what the earlier one recorded", loaded == 1)
        check("and can find it by shape",
              any(item.found_by == "shape"
                  for item in second.prior_stages.lookup(stage)))

        cancelled = SimpleNamespace(stage_store=StageStore(),
                                    prior_stages=StageStore())
        cancelled.stage_store.add(stage, run_id="r2")
        close_stages(cancelled, root, helped=None)
        check("a cancelled run leaves its stages unknown, not failed",
              cancelled.stage_store.observations[0].helped is None,
              "the operator's timing is not evidence about the work")

    broken = SimpleNamespace(stage_store=None, prior_stages=None)
    check("neither operation can raise into the run",
          close_stages(broken, "/nowhere", helped=True) == 0
          and load_prior_stages(broken, "/nowhere") == 0)

    check("no runs directory means no file and no error",
          close_stages(SimpleNamespace(stage_store=StageStore(),
                                       prior_stages=StageStore()),
                       "", helped=True) == 0)

    passed = sum(1 for item in tests if item["passed"])
    return {"record_type": "run_stages_test/v1", "tests": tests,
            "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
