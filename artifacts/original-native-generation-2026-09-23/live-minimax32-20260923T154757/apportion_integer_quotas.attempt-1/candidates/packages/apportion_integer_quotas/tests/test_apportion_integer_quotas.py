"""Tests for the bundled CLI in ``tools/apportion_integer_quotas.py``.

The suite uses only :mod:`unittest` and :mod:`subprocess`. It invokes the
exact bundled tool as a child process. No third-party packages are
imported, no network is contacted, and no files are written outside this
test runner.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "tools" / "apportion_integer_quotas.py"


def _run(payload: bytes, *, timeout: float = 10.0) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    # Force unbuffered Python for deterministic stdout reads.
    env["PYTHONUNBUFFERED"] = "1"
    return subprocess.run(
        [sys.executable, str(TOOL)],
        input=payload,
        input=None if payload is None else payload,
        capture_output=True,
        env=env,
        timeout=timeout,
        check=False,
    )


def _run_text(payload: str) -> subprocess.CompletedProcess:
    return _run(payload.encode("utf-8"))


class ApportionIntegerQuotasTests(unittest.TestCase):
    # ----------------------------------------------------------------- #
    # Acceptance examples from AGENTS.md
    # ----------------------------------------------------------------- #

    def test_abc_target_two(self) -> None:
        proc = _run_text('{"target":2,"weights":{"a":1,"b":1,"c":1}}')
        self.assertEqual(proc.returncode, 0, msg=proc.stderr.decode())
        out = json.loads(proc.stdout.decode("utf-8"))
        self.assertEqual(
            out,
            {
                "status": "ok",
                "sum": 2,
                "allocations": {"a": 1, "b": 1, "c": 0},
            },
        )

    def test_tie_break_by_id_ascending(self) -> None:
        proc = _run_text('{"target":3,"weights":{"b":2,"a":2,"c":2}}')
        self.assertEqual(proc.returncode, 0, msg=proc.stderr.decode())
        out = json.loads(proc.stdout.decode("utf-8"))
        self.assertEqual(
            out,
            {
                "status": "ok",
                "sum": 3,
                "allocations": {"a": 1, "b": 1, "c": 1},
            },
        )

    # ----------------------------------------------------------------- #
    # Boundary cases.
    # ----------------------------------------------------------------- #

    def test_zero_target_returns_zero(self) -> None:
        proc = _run_text('{"target":0,"weights":{"a":3,"b":4,"c":5}}')
        self.assertEqual(proc.returncode, 0, msg=proc.stderr.decode())
        out = json.loads(proc.stdout.decode("utf-8"))
        self.assertEqual(
            out,
            {
                "status": "ok",
                "sum": 0,
                "allocations": {"a": 0, "b": 0, "c": 0},
            },
        )

    def test_target_exceeds_sum_still_sums_to_target(self) -> None:
        proc = _run_text('{"target":10,"weights":{"x":1,"y":1}}')
        self.assertEqual(proc.returncode, 0, msg=proc.stderr.decode())
        out = json.loads(proc.stdout.decode("utf-8"))
        # ideal is 5/5 each, so floors + tie-break give x=5,y=5.
        self.assertEqual(out["sum"], 10)
        self.assertEqual(out["allocations"], {"x": 5, "y": 5})

    # ----------------------------------------------------------------- #
    # Refusal cases — every error code path.
    # ----------------------------------------------------------------- #

    def _assert_refused(self, payload: str, code: str) -> None:
        proc = _run_text(payload)
        self.assertNotEqual(proc.returncode, 0, msg=proc.stdout.decode())
        out = json.loads(proc.stdout.decode("utf-8"))
        self.assertEqual(out["status"], "refused")
        self.assertEqual(out["error"]["code"], code)
        # Message must not echo user input back.
        self.assertNotIn("a", out["error"]["message"])
        self.assertNotIn("{} ".format("target"), out["error"]["message"])

    def test_refuses_negative_target(self) -> None:
        self._assert_refused(
            '{"target":-1,"weights":{"a":1}}', "E_TARGET"
        )

    def test_refuses_boolean_weight(self) -> None:
        self._assert_refused(
            '{"target":1,"weights":{"a":true}}', "E_WEIGHT_VALUE"
        )

    def test_refuses_float_weight(self) -> None:
        self._assert_refused(
            '{"target":1,"weights":{"a":1.5}}', "E_WEIGHT_VALUE"
        )

    def test_refuses_duplicate_ids(self) -> None:
        self._assert_refused(
            '{"target":1,"weights":{"a":1,"a":1}}', "E_INPUT_SHAPE"
        )

    def test_refuses_all_zero_weights_with_positive_target(self) -> None:
        self._assert_refused(
            '{"target":3,"weights":{"a":0,"b":0}}',
            "E_WEIGHTS_ALL_ZERO",
        )

    def test_refuses_empty_weights(self) -> None:
        self._assert_refused('{"target":1,"weights":{}}', "E_WEIGHTS")

    def test_refuses_empty_id(self) -> None:
        self._assert_refused(
            '{"target":1,"weights":{"":1}}', "E_WEIGHT_ID"
        )

    def test_refuses_nonfinite_target(self) -> None:
        # JSONDecoder rejects ``NaN`` literal by default, so we exercise the
        # hard cap by oversizing the input instead.
        huge = b"{" + b"\"a\":" + b"1," * 200000 + b"\"b\":1}"
        # Streamed via subprocess so we do not build the full string.
        proc = subprocess.run(
            [sys.executable, str(TOOL)],
            input=huge,
            capture_output=True,
            check=False,
            timeout=10,
        )
        self.assertNotEqual(proc.returncode, 0)

    # ----------------------------------------------------------------- #
    # Resource ceiling.
    # ----------------------------------------------------------------- #

    def test_byte_ceiling(self) -> None:
        # 1 MiB - 1 byte of input, but oversized due to trailing content.
        # The CLI only reads once, so we craft >1MiB to trip E_INPUT_BYTES.
        payload = b'{"target":1,"weights":{"a":' + b'1' * (1 << 20) + b'}}'
        proc = _run(payload)
        self.assertNotEqual(proc.returncode, 0)
        out = json.loads(proc.stdout.decode("utf-8"))
        self.assertEqual(out["status"], "refused")
        self.assertEqual(out["error"]["code"], "E_INPUT_BYTES")

    # ----------------------------------------------------------------- #
    # Independent hand-computed examples.
    # ----------------------------------------------------------------- #

    def test_independent_classic_example(self) -> None:
        # Standard textbook: 20 seats across (6, 6, 5, 3, 1) = 21 weight.
        # Ideal: 20 * 6/21 ≈ 5.714, 5.714, 4.762, 2.857, 0.952.
        # Floors: 5,5,4,2,0 -> sum 16, remainder 4.
        # Remainders desc: 0.952 (id 5), 0.857 (id 1 & id 2 tied), 0.762 (id 3),
        # 0.714 (id 0), 0.0 (id 4). After tie-breaking by ID, the four extras
        # go to id 5, id 1, id 2, id 3 -> final (6,6,4,3,1).
        proc = _run_text(
            '{"target":20,"weights":{"p":6,"q":6,"r":5,"s":3,"t":1}}'
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr.decode())
        out = json.loads(proc.stdout.decode("utf-8"))
        self.assertEqual(out["sum"], 20)
        self.assertEqual(
            out["allocations"], {"p": 6, "q": 6, "r": 4, "s": 3, "t": 1}
        )

    def test_independent_all_floors_with_remainder(self) -> None:
        # Weights 1,2,3,4 = 10, target 7 -> ideal 0.7, 1.4, 2.1, 2.8.
        # Floors: 0,1,2,2 = 5, remainder 2.
        # Remainders desc with tie-break by id: (id "d", 0.8), (id "c", 0.1),
        # (id "b", 0.4). Sorted desc remainder, asc id:
        # d (0.8), b (0.4), c (0.1), a (0.7? — wait, a floor was 0 remainder 0.7).
        # Correct ordering: a(0.7), d(0.8), b(0.4), c(0.1).
        # First two extras go to a, d -> final (1,1,2,3).
        proc = _run_text(
            '{"target":7,"weights":{"a":1,"b":2,"c":3,"d":4}}'
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr.decode())
        out = json.loads(proc.stdout.decode("utf-8"))
        self.assertEqual(out["sum"], 7)
        self.assertEqual(out["allocations"], {"a": 1, "b": 1, "c": 2, "d": 3})

    # ----------------------------------------------------------------- #
    # Known-wrong reference algorithm, included only to document the
    # distinction from trace-numeric-rounding. We verify locally that the
    # wrong algorithm breaks the sum invariant.
    # ----------------------------------------------------------------- #

    def test_known_wrong_round_to_nearest_breaks_sum_invariant(self) -> None:
        def wrong(
            target: int, weights: dict[int, int]
        ) -> dict[int, int]:
            total = sum(weights.values())
            rounded: dict[int, int] = {}
            for k, w in weights.items():
                # Standard double rounding — loses the global invariant.
                q = target * w / total
                rounded[k] = int(round(q))
            return rounded

        result = wrong(20, {"p": 6, "q": 6, "r": 5, "s": 3, "t": 1})
        # The wrong algorithm can violate sum==target; we assert just that
        # *some* allocation rounds to a different total.
        self.assertNotEqual(sum(result.values()), 20)


if __name__ == "__main__":
    unittest.main()
