"""Placement 3: every step runs in a container with no network and no writes.

The step body is mounted read-only, the network is off, every capability is
dropped and the container is removed when the step ends. A step cannot reach
the host filesystem outside the mount, cannot call out, and cannot leave
anything behind.

The cost is a container start per step, which is one to three orders of
magnitude more than a function call. That is the trade this arm exists to
price, and the harness records it rather than asserting it.

When no container runtime is present the arm reports that it is unavailable
and the family harness records a skip. It never silently falls back to a
weaker placement, because a placement that quietly downgrades is worse than
one that refuses.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

SHARED = Path(__file__).resolve().parents[2] / "shared"
sys.path.insert(0, str(SHARED))

#: Pinned by tag here because this folder is a comparison, not a deployment.
#: A deployment pins the digest; see the sandbox image note in the engine docs.
IMAGE = "python:3.12-slim"

BODY = (
    "import sys; sys.path.insert(0, '/shared')\n"
    "from port import fixture_reply\n"
    "sys.stdout.write(fixture_reply(sys.stdin.read()))\n"
)


class ContainerStepFailed(RuntimeError):
    """A step container did not return a reply."""


def _docker() -> str:
    return shutil.which("docker") or ""


def make_evaluator(timeout: float = 120.0, image: str = IMAGE):
    binary = _docker()

    def evaluate(prompt: str) -> str:
        done = subprocess.run(
            [binary, "run", "--rm", "-i",
             "--network", "none", "--read-only", "--cap-drop", "ALL",
             "--memory", "512m", "--pids-limit", "128",
             "-v", f"{SHARED}:/shared:ro",
             image, "python", "-c", BODY],
            input=prompt, capture_output=True, text=True, timeout=timeout)
        if done.returncode != 0:
            raise ContainerStepFailed(
                f"exit {done.returncode}: {done.stderr.strip()[:200]}")
        return done.stdout

    return evaluate


def available() -> tuple:
    """Say plainly whether this placement can run, and why not when it cannot."""
    binary = _docker()
    if not binary:
        return False, "no docker binary on PATH"
    try:
        done = subprocess.run(
            [binary, "version", "--format", "{{.Server.Version}}"],
            capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"docker version failed: {type(exc).__name__}"
    if done.returncode != 0:
        return False, f"docker daemon unreachable: {done.stderr.strip()[:120]}"
    return True, done.stdout.strip()


ARM = {
    "name": "container_per_step",
    "placement": "a container per step",
    "isolation": "no network, read-only mount, all capabilities dropped, "
                 "memory and process limits",
    "make_evaluator": make_evaluator,
    "available": available,
}


def self_check() -> None:
    ok, detail = available()
    if not ok:
        print(f"container_per_step self-check: skipped ({detail})")
        return
    reply = make_evaluator()("REMAINING = []\nshard s000\naccount,side,amount\n"
                             "cash,DR,5\n")
    assert '"net": 5' in reply, reply
    print(f"container_per_step self-check: ok (docker {detail})")


if __name__ == "__main__":
    self_check()
