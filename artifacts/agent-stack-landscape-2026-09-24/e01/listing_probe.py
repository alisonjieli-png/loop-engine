#!/usr/bin/env python3
"""No-model listing probe for the E01 pilot projects (September 25, 2026).

For a copy of each engine's run A project, ask each harness what it would send
to a model, without any model behind the endpoint:
- Codex 0.155.1: `codex debug prompt-input` renders the model-visible input.
- Claude Code: `claude -p` against a local capture stub on 127.0.0.1 that saves
  the request body and answers HTTP 400; the key is the literal string
  `not-a-real-key`; every other outbound connection goes to a closed proxy.

A skill counts as listed when its native name appears in the captured input.
Listed is not loaded into use, and loaded is not useful: those are E02's rungs.
"""
import http.server
import json
import os
import shutil
import socketserver
import subprocess
import sys
import threading

# E01_WORK is the same folder the pilot wrote; the probe copies projects from it.
HERE = os.environ["E01_WORK"]
RESULT = json.load(open(f"{HERE}/e01-pilot-result-2026-09-25.json"))
DEAD = "http://127.0.0.1:9"
BASE_PATH = "/usr/local/bin:/usr/bin:/bin:" + os.path.dirname(shutil.which("node")) + ":" + os.path.dirname(shutil.which("codex")) + ":" + os.path.dirname(shutil.which("claude"))
CAPTURED = []


class Stub(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        n = int(self.headers.get("content-length", 0))
        CAPTURED.append(self.rfile.read(n).decode("utf-8", "replace"))
        body = b'{"type":"error","error":{"type":"invalid_request_error","message":"capture stub: no model behind this endpoint"}}'
        self.send_response(400)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self.send_response(404)
        self.end_headers()

    def log_message(self, *args):
        pass


def base_env(home):
    env = {"HOME": home, "PATH": BASE_PATH, "LANG": "C.UTF-8", "TERM": "dumb", "NO_COLOR": "1"}
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        env[k] = DEAD
    env["NO_PROXY"] = env["no_proxy"] = "127.0.0.1,localhost"
    return env


def probe_codex(project, work, name):
    home, iso = f"{work}/codex-home", f"{work}/codex-iso"
    os.makedirs(home), os.makedirs(iso)
    env = base_env(home) | {"CODEX_HOME": iso}
    p = subprocess.run(["codex", "debug", "prompt-input", "probe"], cwd=project, env=env,
                       capture_output=True, text=True, timeout=120)
    open(f"{work}/codex-prompt-input.json", "w").write(p.stdout)
    open(f"{work}/codex-stderr.txt", "w").write(p.stderr)
    return {"rc": p.returncode, "listed": name in p.stdout, "stdout_bytes": len(p.stdout),
            "stderr_tail": p.stderr[-300:]}


def probe_claude(project, work, name, port):
    home, iso = f"{work}/claude-home", f"{work}/claude-iso"
    os.makedirs(home), os.makedirs(iso)
    env = base_env(home) | {"CLAUDE_CONFIG_DIR": iso, "ANTHROPIC_BASE_URL": f"http://127.0.0.1:{port}",
                            "ANTHROPIC_API_KEY": "not-a-real-key", "DISABLE_TELEMETRY": "1",
                            "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1", "DISABLE_AUTOUPDATER": "1"}
    before = len(CAPTURED)
    p = subprocess.run(["claude", "-p", "probe", "--no-session-persistence", "--max-turns", "1",
                        "--debug-file", f"{work}/claude-debug.txt"], cwd=project, env=env,
                       capture_output=True, text=True, timeout=180)
    bodies = CAPTURED[before:]
    open(f"{work}/claude-requests.json", "w").write(json.dumps(bodies))
    debug = open(f"{work}/claude-debug.txt").read() if os.path.exists(f"{work}/claude-debug.txt") else ""
    loaded = [line.strip()[-160:] for line in debug.splitlines() if "Loaded" in line and "skills" in line][:3]
    return {"rc": p.returncode, "requests_captured": len(bodies), "listed": any(name in b for b in bodies),
            "debug_skill_lines": loaded, "stdout_tail": (p.stdout + p.stderr)[-200:]}


def main():
    server = socketserver.TCPServer(("127.0.0.1", 0), Stub)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    out = {"record_type": "e01_listing_probe/v1", "codex": "0.155.1", "claude_code": None, "probes": {}}
    out["claude_code"] = subprocess.run(["claude", "--version"], capture_output=True, text=True,
                                        env=base_env(f"{HERE}/vhome")).stdout.strip()
    for key, runs in sorted(RESULT["runs"].items()):
        engine, pkg = key.split("/")
        name = RESULT["packages"][pkg]["name"]
        src_project = f"{runs['A']['base']}/project"
        work = f"{HERE}/probe/{engine}/{pkg}"
        shutil.rmtree(work, ignore_errors=True)
        os.makedirs(work)
        project = f"{work}/project"
        shutil.copytree(src_project, project, symlinks=True)
        out["probes"][key] = {"codex": probe_codex(project, work, name),
                              "claude_code": probe_claude(project, work, name, port)}
        c, k = out["probes"][key]["codex"], out["probes"][key]["claude_code"]
        print(f"{key}: codex listed={c['listed']} rc={c['rc']} | claude listed={k['listed']} rc={k['rc']} "
              f"requests={k['requests_captured']} debug={k['debug_skill_lines'][:1]}")
    server.shutdown()
    json.dump(out, open(f"{HERE}/e01-listing-probe-2026-09-25.json", "w"), indent=1, sort_keys=True)


if __name__ == "__main__":
    main()
