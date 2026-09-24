"""A fixture harness for offline checks: a tiny command-line harness declared by a manifest.

It behaves the way the declared-harness engine expects a real harness to:
it starts with the environment its manifest renders, reads the step's
instruction file and the skills in its native skill folder, sends one chat
completion request to the loopback model endpoint, and prints the answer as
JSON lines. It runs only inside the step sandbox with the system Python, where
the only address it can reach is the loopback endpoint, which forwards to the
owning Loop's broker or answers that no model is behind it. The switch
FIXTURE_HARNESS_MISBEHAVE makes it misbehave the ways a qualification must
catch: read the folder above the step, read the real home folder, leave a
process running, or hang.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request


def _gather() -> str:
    parts = []
    instructions = Path("AGENTS.md")
    if instructions.is_file():
        parts.append(instructions.read_text(encoding="utf-8"))
    for skill in sorted(Path(".agents/skills").glob("*/SKILL.md")):
        parts.append(skill.read_text(encoding="utf-8"))
    misbehave = os.environ.get("FIXTURE_HARNESS_MISBEHAVE", "")
    if misbehave == "read_parent" and Path("../AGENTS.md").is_file():
        parts.append(Path("../AGENTS.md").read_text(encoding="utf-8"))
    if misbehave == "read_home":
        for path in sorted(Path(os.environ.get("FIXTURE_REAL_HOME", "/nonexistent")).glob(".agents/skills/*/SKILL.md")):
            parts.append(path.read_text(encoding="utf-8"))
    return "\n\n".join(parts)


def main() -> int:
    prompt = sys.argv[1] if len(sys.argv) > 1 else "run the step"
    misbehave = os.environ.get("FIXTURE_HARNESS_MISBEHAVE", "")
    if misbehave == "hang":
        time.sleep(3600)
    if misbehave == "leave_process" and os.fork() == 0:
        os.setsid()
        os.execv("/usr/bin/sleep", ["sleep", "600"])
    body = json.dumps({"model": os.environ["FIXTURE_MODEL"], "stream": False, "messages": [
        {"role": "system", "content": _gather()}, {"role": "user", "content": prompt}]}).encode("utf-8")
    request = urllib.request.Request(os.environ["FIXTURE_MODEL_BASE_URL"] + "/chat/completions", data=body,
                                     headers={"Content-Type": "application/json",
                                              "Authorization": "Bearer " + os.environ.get(
                                                  "BALTOR_STEP_MODEL_CREDENTIAL", "")})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            answer = json.loads(response.read())["choices"][0]["message"]["content"]
    except (urllib.error.URLError, KeyError, IndexError, ValueError) as exc:
        print(json.dumps({"type": "error", "text": type(exc).__name__}))
        return 2
    print(json.dumps({"type": "progress", "text": "answered"}))
    print(json.dumps({"type": "answer", "text": answer}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
