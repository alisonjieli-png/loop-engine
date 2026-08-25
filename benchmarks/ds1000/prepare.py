"""Pinned source acquisition and verification for the DS-1000 smoke run."""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path


BENCHMARK_DIR = Path(__file__).resolve().parent
POPULATION_PATH = BENCHMARK_DIR / "population-v1.json"
CACHE_DIR = BENCHMARK_DIR / ".cache"
SOURCE_DIR = CACHE_DIR / "upstream"


class SourceGateError(RuntimeError):
    """The pinned source does not match the frozen population contract."""


def population() -> dict:
    return json.loads(POPULATION_PATH.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git_output(source_root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(source_root), *args],
        check=True, text=True, capture_output=True)
    return completed.stdout.strip()


def iter_rows(source_root: Path):
    data_path = source_root / "data" / "ds1000.jsonl.gz"
    with gzip.open(data_path, "rt", encoding="utf-8") as stream:
        for line in stream:
            yield json.loads(line)


def row_by_id(source_root: Path, problem_id: int) -> dict:
    for row in iter_rows(source_root):
        if int(row["metadata"]["problem_id"]) == int(problem_id):
            return row
    raise SourceGateError(f"pinned source has no problem {problem_id}")


def verify_source(source_root: Path = SOURCE_DIR) -> dict:
    frozen = population()
    if not source_root.is_dir():
        raise SourceGateError(f"pinned source is missing at {source_root}")
    commit = _git_output(source_root, "rev-parse", "HEAD")
    expected_commit = frozen["source"]["commit"]
    if commit != expected_commit:
        raise SourceGateError(
            f"source commit {commit} does not equal {expected_commit}")

    artifacts = []
    for expected in frozen["source"]["artifacts"]:
        path = source_root / expected["path"]
        if not path.is_file():
            raise SourceGateError(f"missing pinned artifact {expected['path']}")
        observed = {
            "path": expected["path"],
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        if observed["bytes"] != expected["bytes"]:
            raise SourceGateError(
                f"size mismatch for {expected['path']}: {observed['bytes']}")
        if observed["sha256"] != expected["sha256"]:
            raise SourceGateError(
                f"digest mismatch for {expected['path']}: "
                f"{observed['sha256']}")
        artifacts.append(observed)

    selected = []
    for task in frozen["tasks"]:
        row = row_by_id(source_root, int(task["problem_id"]))
        library = str(row["metadata"]["library"])
        if library != task["library"]:
            raise SourceGateError(
                f"problem {task['problem_id']} is {library!r}, expected "
                f"{task['library']!r}; no substitution is allowed")
        prompt = str(row.get("prompt", ""))
        reference_code = str(row.get("reference_code", ""))
        code_context = str(row.get("code_context", ""))
        if not prompt.strip() or not reference_code.strip() \
                or "def test_execution" not in code_context:
            raise SourceGateError(
                f"problem {task['problem_id']} is missing a required field")
        if reference_code in prompt or code_context in prompt:
            raise SourceGateError(
                f"problem {task['problem_id']} prompt is not separated from "
                "reference or evaluator content")
        selected.append({
            "problem_id": int(task["problem_id"]),
            "library": library,
            "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
            "prompt_chars": len(prompt),
            "reference_separated": True,
            "test_case_count": int(row["metadata"]["test_case_cnt"]),
        })

    return {
        "record_type": "ds1000_source_verification/v1",
        "ok": True,
        "repository": frozen["source"]["repository"],
        "commit": commit,
        "artifacts": artifacts,
        "selected_tasks": selected,
    }


def prepare_source(source_root: Path = SOURCE_DIR) -> dict:
    """Acquire exactly the frozen commit, then verify every admitted byte."""
    if source_root.exists():
        return verify_source(source_root)

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    partial = CACHE_DIR / f"upstream.partial.{os.getpid()}"
    if partial.exists():
        shutil.rmtree(partial)
    try:
        subprocess.run(["git", "init", "-q", str(partial)], check=True)
        subprocess.run([
            "git", "-C", str(partial), "remote", "add", "origin",
            population()["source"]["repository"],
        ], check=True)
        subprocess.run([
            "git", "-C", str(partial), "fetch", "-q", "--depth=1",
            "origin", population()["source"]["commit"],
        ], check=True)
        subprocess.run([
            "git", "-C", str(partial), "checkout", "-q", "--detach",
            "FETCH_HEAD",
        ], check=True)
        verify_source(partial)
        os.replace(partial, source_root)
    except BaseException:
        if partial.exists():
            shutil.rmtree(partial)
        raise
    return verify_source(source_root)


def main() -> int:
    print(json.dumps(prepare_source(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

