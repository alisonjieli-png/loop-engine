"""Create a dated development checkpoint of the entire system.

Captures the repository tree, self-test results, conformance gates,
git state, and a human-readable summary into checkpoints/<date>-<slug>/.
"""
from __future__ import annotations

import datetime
import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _run(command: list[str], *, env: dict | None = None) -> str:
    result = subprocess.run(command, cwd=REPO, capture_output=True,
                            text=True, env=env or os.environ.copy())
    return result.stdout + result.stderr


def _tree() -> str:
    return _run(["git", "ls-files"])


def _git_state() -> str:
    branch = _run(["git", "branch", "--show-current"]).strip()
    commit = _run(["git", "rev-parse", "HEAD"]).strip()
    status = _run(["git", "status", "--short"])
    return f"branch: {branch}\ncommit: {commit}\n\n{status}"


def _self_test() -> dict:
    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.join(REPO, "src")
    output = _run([sys.executable, "-m", "loop_engine", "--self-test"],
                  env=env)
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return {"error": output[-2000:]}


def _conformance() -> dict:
    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.join(REPO, "src")
    output = _run([sys.executable, "-m", "loop_engine", "--conformance"],
                  env=env)
    return {"output": output[-2000:]}


def main() -> int:
    slug = sys.argv[1] if len(sys.argv) > 1 else "checkpoint"
    date = datetime.date.today().isoformat()
    target = os.path.join(REPO, "checkpoints", f"{date}-{slug}")
    os.makedirs(target, exist_ok=True)

    tests = _self_test()
    conformance = _conformance()
    passed = tests.get("passed", "unknown")
    total = tests.get("total", "unknown")
    all_passed = tests.get("all_passed", False)

    state = {
        "date": date,
        "slug": slug,
        "self_test_passed": passed,
        "self_test_total": total,
        "self_test_all_passed": all_passed,
        "conformance": conformance,
    }
    with open(os.path.join(target, "state.json"), "w") as handle:
        json.dump(state, handle, indent=1)
    with open(os.path.join(target, "tree.txt"), "w") as handle:
        handle.write(_tree())
    with open(os.path.join(target, "test-report.json"), "w") as handle:
        json.dump(tests, handle, indent=1)
    with open(os.path.join(target, "git-state.txt"), "w") as handle:
        handle.write(_git_state())
    with open(os.path.join(target, "SNAPSHOT.md"), "w") as handle:
        handle.write(f"""# Checkpoint {date}-{slug}

## System state

- self-test: {passed}/{total} passed, all_passed={all_passed}
- conformance: see conformance.json

## Contents

- state.json: machine-readable state
- tree.txt: full repository tree
- test-report.json: self-test results
- conformance.json: conformance gate output
- git-state.txt: branch, commit, and dirty state
""")
    print(f"checkpoint written to {target}")
    print(f"self-test: {passed}/{total} all_passed={all_passed}")
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
