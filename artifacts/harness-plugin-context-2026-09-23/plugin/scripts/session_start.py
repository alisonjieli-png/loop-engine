"""Candidate SessionStart hook. Reads stdin metadata only; never opens its paths."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

# Isolated Python ignores cwd and PYTHONPATH. Load our exact adjacent helper.
_spec = importlib.util.spec_from_file_location("brief_protocol", Path(__file__).with_name("protocol.py"))
_protocol = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_protocol)

GUIDANCE = (
    "Baltor focused-brief candidate is available. For a focused step, use only "
    "the brief and materials explicitly supplied for that step. Name its objective, "
    "inputs, outputs, constraints, out-of-scope work and acceptance checks. "
    "If essential information is missing, report the unanswered question. "
    "The /baltor-focused-brief-candidate:check-brief command can check the structure "
    "of a supplied brief. Structure validity does not establish truth, adequacy, "
    "permission or task success. This hook has not read any task file, transcript, "
    "credential or external source. Existing host permissions remain controlling."
)


def main():
    try:
        value, _digest = _protocol.parse_input(sys.stdin.buffer)
        if (not isinstance(value, dict)
                or value.get("hook_event_name") != "SessionStart"
                or value.get("source") not in ("startup", "resume", "clear", "compact")):
            raise _protocol.InvalidInput("unsupported_hook_input")
    except _protocol.InvalidInput:
        # SessionStart is context-only, not a task admission or denial boundary.
        _protocol.write_json({}, sys.stdout)
        sys.stderr.write("focused_brief_hook_input_refused\n")
        return 1
    _protocol.write_json({"hookSpecificOutput": {
        "hookEventName": "SessionStart", "additionalContext": GUIDANCE}}, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
