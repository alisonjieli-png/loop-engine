"""The process entry point of the custom Loop harness: one step, one fresh process.

The manifest ``baltor_loop.process`` (engine kind custom_loop_harness) starts
this file with the system Python inside the step's sandbox, with the package
source mounted read-only and named by PYTHONPATH. It reads one
step_run_request/v1 from the request file, runs the step through the canonical
Loop exactly as the in-process engine does (core.step_execution.loop_runtime),
and writes one step_run_result/v1 to the result file. It has no network and
calls no model; the envelope outside computes whether the attempt counts as
delegation and never reads that claim from this file.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run one step through the Loop runtime.")
    parser.add_argument("--request", required=True)
    parser.add_argument("--result", required=True)
    arguments = parser.parse_args(argv)
    from loop_engine.core.step_execution.loop_runtime import run_step_in_loop
    from loop_engine.core.step_execution.records import StepRunRequest
    request = StepRunRequest.from_dict(json.loads(Path(arguments.request).read_text(encoding="utf-8")))
    result = run_step_in_loop(request)
    with open(arguments.result, "x", encoding="utf-8") as handle:
        handle.write(json.dumps(result.to_dict(), ensure_ascii=False, sort_keys=True))
    return 0 if result.status == "completed" else 3


if __name__ == "__main__":
    sys.exit(main())
