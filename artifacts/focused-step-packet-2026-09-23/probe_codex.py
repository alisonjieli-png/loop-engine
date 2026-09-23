"""Observe candidate AGENTS.md pickup with Codex's no-model debug command."""
import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import render_packet as packet

ROOT = Path(__file__).resolve().parent


def strings(value):
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return "\n".join(strings(item) for item in value.values())
    if isinstance(value, list):
        return "\n".join(strings(item) for item in value)
    return ""


def main():
    codex = shutil.which("codex")
    if not codex:
        raise SystemExit("Codex unavailable; native pickup remains untested")
    version = subprocess.run([codex, "--version"], capture_output=True,
                             text=True, timeout=10, check=True).stdout.strip()
    observations = []
    for row in json.loads((ROOT / "fixture-bindings.json").read_text())["fixtures"]:
        brief = packet.load_brief(json.loads((ROOT / row["fixture"]).read_text()))
        slug = Path(row["fixture"]).stem
        source = ROOT / "packets" / slug
        packet.verify(source, row["expected_binding"])
        with tempfile.TemporaryDirectory(prefix="baltor-focused-packet-") as tmp:
            root = Path(tmp)
            for ancestor in root.parents:
                if any((ancestor / name).exists() for name in ("AGENTS.md", "AGENTS.override.md")):
                    raise SystemExit("ancestor instruction would contaminate native probe")
            work = root / "work"
            shutil.copytree(source, work)
            (work / ".git").mkdir()
            home = root / "home"
            config = root / "codex-home"
            home.mkdir()
            config.mkdir()
            (config / "config.toml").write_text(
                'web_search = "disabled"\n[skills.bundled]\nenabled = false\n')
            environment = {
                "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                "HOME": str(home), "CODEX_HOME": str(config), "TERM": "dumb",
                "HTTP_PROXY": "http://127.0.0.1:9", "HTTPS_PROXY": "http://127.0.0.1:9",
                "ALL_PROXY": "http://127.0.0.1:9",
            }
            markers = [brief.assignment.objective, brief.data["first_actions"][0],
                       brief.state.state_id, brief.assignment.output_contract_refs[0]]
            cases = []
            for case in ("entrypoint_present", "entrypoint_removed_auxiliary_files_retained"):
                if case != "entrypoint_present":
                    (work / "AGENTS.md").unlink()
                result = subprocess.run(
                    [codex, "debug", "prompt-input", "Inspect the prepared focused assignment."],
                    cwd=work, env=environment, capture_output=True, text=True, timeout=35,
                    check=False)
                try:
                    visible = strings(json.loads(result.stdout))
                except ValueError:
                    visible = ""
                cases.append({"case": case, "exit_code": result.returncode,
                              "markers_visible": [marker in visible for marker in markers],
                              "stderr_present": bool(result.stderr),
                              "prompt_output_sha256": packet.digest(result.stdout.encode())})
            observations.append({"fixture": slug, "source_style": brief.assignment.harness_style,
                                 "tested_style": "codex", "expected_binding": row["expected_binding"],
                                 "cases": cases,
                                 "passed": cases[0]["exit_code"] == 0
                                 and all(cases[0]["markers_visible"])
                                 and cases[1]["exit_code"] == 0
                                 and not any(cases[1]["markers_visible"])})
    record = {"record_type": "focused_step_native_debug_probe/v1", "client": version,
              "created_at": datetime.now(timezone.utc).isoformat(),
              "command": "codex debug prompt-input", "model_calls": 0,
              "observations": observations, "passed": all(r["passed"] for r in observations),
              "limits": ["Debug prompt composition only; no model use or accepted task work.",
                         "Both shared AGENTS.md files tested through Codex only; Claude import remains untested.",
                         "Closed proxy configuration is not an operating-system network sandbox.",
                         "Auxiliary filenames alone did not load the task markers in this Codex configuration."]}
    path = ROOT / ("CODEX-PICKUP-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + ".json")
    with path.open("x") as stream:
        json.dump(record, stream, indent=2)
        stream.write("\n")
    print(path)
    if not record["passed"]:
        raise SystemExit("Native pickup failed; saved record retained")


if __name__ == "__main__":
    main()
