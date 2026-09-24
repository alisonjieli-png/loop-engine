"""The loopback model endpoint that runs beside one declared harness inside its sandbox.

This file runs standalone in the sandbox with the system Python, so no harness
dependency enters the engine process and no package import is needed. It
serves the one model wire the harness manifest declares on a loopback port of
the sandbox's own network namespace, using the release relay module mounted
beside it (its wire table, handler and broker framing), records every request
the harness sends into the attempt's capture folder, and either forwards each
request to the owning Loop's broker over the mounted socket or, with no model
authority, answers that no model is behind it. It then runs the harness
command with exactly the rendered environment and waits for it. It owns no
authority: the broker outside decides every model call.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

CONFIG = Path("/relay/config.json")
RELAY = Path("/relay/harness_process_relay.py")
NO_MODEL_ANSWER = {"error": {"message": "loopback endpoint: no model is behind it"}}


def _load_relay(expected_sha256: str):
    """The release relay, after its bytes match the digest the launcher recorded."""
    if hashlib.sha256(RELAY.read_bytes()).hexdigest() != expected_sha256:
        raise SystemExit("the mounted relay differs from the launcher's digest")
    spec = importlib.util.spec_from_file_location("step_harness_relay", RELAY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _capturing_exchange(relay, config, forward):
    """Record each request, then forward it or answer that no model is behind the endpoint."""
    capture = Path(config["capture"])
    lock, state = threading.Lock(), {"count": 0}

    def exchange(settings, request):
        with lock:
            state["count"] += 1
            number = state["count"]
        (capture / f"request-{number:03d}.json").write_text(
            json.dumps(request, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        if config["mode"] != "broker":
            return dict(NO_MODEL_ANSWER)
        return forward(settings, request)
    return exchange


def main() -> int:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    relay = _load_relay(config["relay_sha256"])
    server = None
    if config["mode"] != "none":
        wires = relay._wire_table(config, str(RELAY.parent))
        relay._exchange = _capturing_exchange(relay, config, relay._exchange)
        from http.server import ThreadingHTTPServer
        server = ThreadingHTTPServer(("127.0.0.1", config["port"]), relay._handler(config, wires))
        threading.Thread(target=server.serve_forever, daemon=True).start()
    started = time.monotonic()
    stdin = open(config["stdin"], "rb") if config["stdin"] else subprocess.DEVNULL
    try:
        with open(config["stdout"], "wb") as out, open(config["stderr"], "wb") as err:
            process = subprocess.Popen(config["command"], cwd=config["cwd"], env=config["environment"],
                                       stdin=stdin, stdout=out, stderr=err, start_new_session=True)
            try:
                code = process.wait(timeout=config["timeout_seconds"])
                timed_out = False
            except subprocess.TimeoutExpired:
                code, timed_out = None, True
            finally:
                try:
                    os.killpg(process.pid, 9)
                except ProcessLookupError:
                    pass
                process.wait()
    finally:
        if stdin is not subprocess.DEVNULL:
            stdin.close()
        if server is not None:
            server.shutdown()
    Path(config["exit"]).write_text(json.dumps({
        "exit_code": code, "timed_out": timed_out,
        "elapsed_seconds": round(time.monotonic() - started, 6)}), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
