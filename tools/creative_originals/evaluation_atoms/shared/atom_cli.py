"""The JSON command line every evaluation atom shares: one JSON request on standard input, one JSON reply on output.

    echo '{"call": "FUNCTION", "arguments": {...}}' | python3 ITEM.py
    python3 ITEM.py --list

A reply is {"call": ..., "result": ...} with exit status 0, or {"call": ..., "error": {"type", "message"}} with
exit status 2 when the request or its arguments are invalid. Results are strict JSON: a NaN or an infinity is an
error, never an output. Nothing is read or written apart from the two standard streams.
"""
from __future__ import annotations

import inspect
import json
import sys


def describe(functions):
    """The entry points: name, parameters and the first line of each docstring."""
    rows = []
    for name in sorted(functions):
        function = functions[name]
        doc = (inspect.getdoc(function) or "").strip().splitlines()
        rows.append({"name": name, "parameters": list(inspect.signature(function).parameters),
                     "summary": doc[0] if doc else ""})
    return rows


def handle(functions, request):
    """Run one request dict against the entry points; (reply dict, exit status)."""
    if not isinstance(request, dict) or set(request) - {"call", "arguments"} or "call" not in request:
        return {"error": {"type": "ValueError", "message": "a request is {\"call\": name, \"arguments\": {...}}"}}, 2
    call, arguments = request["call"], request.get("arguments", {})
    if call not in functions:
        return {"call": call, "error": {"type": "ValueError",
                                        "message": f"unknown call; one of {sorted(functions)}"}}, 2
    if not isinstance(arguments, dict):
        return {"call": call, "error": {"type": "ValueError", "message": "arguments must be an object"}}, 2
    try:
        result = functions[call](**arguments)
        text = json.dumps(result, allow_nan=False, sort_keys=True)
    except (ValueError, TypeError) as error:
        return {"call": call, "error": {"type": type(error).__name__, "message": str(error)}}, 2
    return {"call": call, "result": json.loads(text)}, 0


def run(functions, argv=None, stdin=None, stdout=None):
    """The command line: ``--list`` describes the entry points; otherwise one request is read from ``stdin``."""
    argv = sys.argv[1:] if argv is None else list(argv)
    stdin = sys.stdin if stdin is None else stdin
    stdout = sys.stdout if stdout is None else stdout
    if argv == ["--list"]:
        stdout.write(json.dumps(describe(functions), indent=1, sort_keys=True) + "\n")
        return 0
    if argv:
        stdout.write(json.dumps({"error": {"type": "ValueError", "message": "the only option is --list"}}) + "\n")
        return 2
    try:
        request = json.loads(stdin.read())
    except ValueError as error:
        reply, status = {"error": {"type": "ValueError", "message": f"request is not JSON: {error}"}}, 2
    else:
        reply, status = handle(functions, request)
    stdout.write(json.dumps(reply, allow_nan=False, sort_keys=True) + "\n")
    return status


__all__ = ["describe", "handle", "run"]
