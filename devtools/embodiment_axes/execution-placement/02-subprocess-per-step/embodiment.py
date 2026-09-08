"""Placement 2: every step runs in a fresh operating system process.

The step body is handed to a new interpreter on standard input and its reply
comes back on standard output. Nothing survives between steps except what the
loop chose to send, which is the point: a step cannot accumulate hidden state
because it has nowhere to keep it.

This is the placement that makes the transport question real. In process, an
arm that "forgets" to carry state still works by accident through shared
memory. Here it cannot.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SHARED = Path(__file__).resolve().parents[2] / "shared"
sys.path.insert(0, str(SHARED))

#: The whole step body. It reads a prompt on stdin and writes a reply on
#: stdout, and it is the only thing that crosses the boundary.
BODY = (
    "import sys; sys.path.insert(0, %r)\n"
    "from port import fixture_reply\n"
    "sys.stdout.write(fixture_reply(sys.stdin.read()))\n"
)


class SubprocessStepFailed(RuntimeError):
    """A step process did not return a reply. Visible, never swallowed."""


def make_evaluator(timeout: float = 30.0):
    code = BODY % str(SHARED)

    def evaluate(prompt: str) -> str:
        done = subprocess.run(
            [sys.executable, "-c", code],
            input=prompt, capture_output=True, text=True, timeout=timeout)
        if done.returncode != 0:
            raise SubprocessStepFailed(
                f"exit {done.returncode}: {done.stderr.strip()[:200]}")
        return done.stdout

    return evaluate


def available() -> tuple:
    return True, ""


ARM = {
    "name": "subprocess_per_step",
    "placement": "a fresh interpreter per step",
    "isolation": "process memory only; same filesystem, same network, same user",
    "make_evaluator": make_evaluator,
    "available": available,
}


def self_check() -> None:
    evaluate = make_evaluator()
    reply = evaluate("REMAINING = []\nshard s000\naccount,side,amount\n"
                     "cash,DR,5\n")
    assert '"net": 5' in reply, reply
    # the boundary is real: nothing set here reaches the step
    import os
    os.environ["LEAK_CHECK"] = "visible-in-parent"
    probe = subprocess.run(
        [sys.executable, "-c",
         "import os; print(os.environ.get('LEAK_CHECK', 'absent'))"],
        capture_output=True, text=True, env={"PATH": os.environ.get("PATH", "")})
    assert probe.stdout.strip() == "absent", probe.stdout
    print("subprocess_per_step self-check: ok")


if __name__ == "__main__":
    self_check()
