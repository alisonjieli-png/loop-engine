#!/usr/bin/env python3
"""Known-wrong controls for the no-model listing probe (September 25, 2026).

The probe must be able to fail. Two controls, each a fresh git project:
- empty-project: no skill anywhere;
- wrong-root: the same SKILL.md under .skills/<name>/, a folder neither
  harness reads.
Both must report listed = false for Codex and for Claude Code.
"""
import importlib.util
import json
import os
import shutil
import socketserver
import subprocess
import threading

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("listing_probe", os.path.join(SCRIPTS, "listing_probe.py"))
lp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lp)
NAME = "find-duplicate-records-with-blocking-keys"


def main():
    server = socketserver.TCPServer(("127.0.0.1", 0), lp.Stub)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = lp.RESULT["runs"]["native/P1-single-file"]["A"]["base"]
    results = {}
    for label, place in (("empty-project", None), ("wrong-root", f".skills/{NAME}")):
        work = f"{lp.HERE}/probe/control/{label}"
        shutil.rmtree(work, ignore_errors=True)
        os.makedirs(work)
        project = f"{work}/project"
        os.makedirs(project)
        subprocess.run(["git", "init", "-q", project], check=True, env=lp.base_env(work))
        if place:
            os.makedirs(f"{project}/{place}")
            shutil.copy(f"{base}/src/skills/{NAME}/SKILL.md", f"{project}/{place}/SKILL.md")
        results[label] = {"codex": lp.probe_codex(project, work, NAME),
                          "claude_code": lp.probe_claude(project, work, NAME, port)}
        print(label, "codex listed:", results[label]["codex"]["listed"],
              "| claude listed:", results[label]["claude_code"]["listed"])
    server.shutdown()
    json.dump(results, open(f"{lp.HERE}/e01-listing-probe-controls-2026-09-25.json", "w"), indent=1, sort_keys=True)
    failed = [label for label, r in results.items() if r["codex"]["listed"] or r["claude_code"]["listed"]]
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
