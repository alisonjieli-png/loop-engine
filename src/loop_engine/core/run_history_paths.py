"""Portable path and identity rules for saved Run History bundles.

Run History owns the record semantics. This small deterministic boundary owns
only where those records may live and which directory names are valid. Keeping
path validation separate prevents CLI, Studio, report, and playback callers
from inventing their own resolution rules.
"""
from __future__ import annotations

import os
import re


RUNS_DIR_ENV = "LOOP_ENGINE_RUNS_DIR"
_RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")


class RunHistoryIntegrityError(ValueError):
    """Saved run history is incomplete, inconsistent, or has been changed."""


def validated_run_id(value: str) -> str:
    """Return one portable path-segment run ID or fail before path use."""
    if (not isinstance(value, str) or not _RUN_ID.fullmatch(value)
            or value in (".", "..")):
        raise RunHistoryIntegrityError(
            "run_id must be one portable path segment using letters, "
            "numbers, dot, underscore, or hyphen")
    return value


def default_runs_dir(path: str = "") -> str:
    """Resolve one shared directory for runs, reports, playback, and Studio."""
    selected = path or os.environ.get(RUNS_DIR_ENV, "")
    if selected:
        return os.path.abspath(os.path.expanduser(selected))
    return os.path.join(os.path.expanduser("~"), ".loop-engine", "runs")


def saved_run_ids(root: str) -> list[str]:
    """List only safe directories with a complete saved-run file shape."""
    if not os.path.isdir(root):
        return []
    required = ("manifest.json", "events.jsonl")
    return sorted(
        name for name in os.listdir(root)
        if _RUN_ID.fullmatch(name) and name not in (".", "..")
        and os.path.isdir(os.path.join(root, name))
        and all(os.path.isfile(os.path.join(root, name, filename))
                for filename in required))


__all__ = (
    "RUNS_DIR_ENV", "RunHistoryIntegrityError", "default_runs_dir",
    "saved_run_ids", "validated_run_id")
