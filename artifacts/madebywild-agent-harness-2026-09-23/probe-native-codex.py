"""Offline prompt construction from exact renderer output and matched controls."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
render_bytes = (ROOT / "adapter-observations.json").read_bytes()
render = json.loads(render_bytes)
codex = next(row for row in render["providers"] if row["provider"] == "codex")
executable = shutil.which("codex")
version = subprocess.check_output([executable, "--version"], text=True).strip()
cases = ("empty", "upstream_codex_skill", "shared_agents_skill", "upstream_inline_subagent", "native_config_file_subagent")
results = []
for case in cases:
    with tempfile.TemporaryDirectory(prefix="baltor-madebywild-") as raw:
        base = Path(raw)
        work, home, config = (base / item for item in ("work", "home", "configuration"))
        for directory in (work, home, config):
            directory.mkdir()
        for ancestor in work.parents:
            if any((ancestor / filename).exists() for filename in ("AGENTS.md", "AGENTS.override.md")):
                raise RuntimeError("Uncontrolled instruction ancestor")
        (work / ".git").mkdir()
        (config / "config.toml").write_text('web_search="disabled"\n[skills.bundled]\nenabled=false\n[projects.' + json.dumps(str(work)) + ']\ntrust_level="trusted"\n')
        if case in ("upstream_codex_skill", "shared_agents_skill"):
            for artifact in codex["skill"]:
                relative = artifact["path"]
                if case == "shared_agents_skill":
                    relative = relative.replace(".codex/skills/", ".agents/skills/")
                target = work / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(artifact["content"])
        if case == "upstream_inline_subagent":
            for artifact in codex["subagent"]:
                target = work / artifact["path"]
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(artifact["content"])
        if case == "native_config_file_subagent":
            (work / ".codex").mkdir()
            (work / ".codex/config.toml").write_text('[agents.reviewer]\ndescription="Synthetic reviewer"\nconfig_file="reviewer.toml"\n')
            (work / ".codex/reviewer.toml").write_text('developer_instructions="REVIEWER_BODY"\n')
        before = {str(p.relative_to(work)): hashlib.sha256(p.read_bytes()).hexdigest() for p in work.rglob("*") if p.is_file()}
        environment = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME":str(home), "CODEX_HOME":str(config), "TERM":"dumb", "HTTP_PROXY":"http://127.0.0.1:9", "HTTPS_PROXY":"http://127.0.0.1:9", "ALL_PROXY":"http://127.0.0.1:9"}
        result = subprocess.run([executable, "debug", "prompt-input", "Inspect synthetic configuration only; do not execute work."], cwd=work, env=environment, text=True, capture_output=True, timeout=40)
        try:
            parsed = json.loads(result.stdout)
            valid_json = True
        except ValueError:
            parsed = None
            valid_json = False
        after = {str(p.relative_to(work)): hashlib.sha256(p.read_bytes()).hexdigest() for p in work.rglob("*") if p.is_file()}
        results.append({"case":case,"exit_code":result.returncode,"valid_json":valid_json,
                        "description_visible":"SAMPLE_SKILL_DESCRIPTION" in result.stdout,
                        "body_visible":"SAMPLE_SKILL_BODY" in result.stdout,
                        "reviewer_visible":"Synthetic reviewer" in result.stdout,
                        "reviewer_body_visible":"REVIEWER_BODY" in result.stdout,
                        "stderr":result.stderr.replace(raw,"<temporary>"),
                        "stdout_sha256":hashlib.sha256(result.stdout.encode()).hexdigest(),
                        "workspace_unchanged":before==after,"inputs":before})
report = {"schema":"baltor.research-native-observations/v1","created_at":datetime.now(timezone.utc).isoformat(),"runtime":version,"model_calls":0,"renderer_report_sha256":hashlib.sha256(render_bytes).hexdigest(),"observations":results,"limitations":["Prompt construction, not model task execution or subagent spawning.","No native MCP servers or hooks were started.","Closed proxy settings are not an operating-system sandbox."]}
(ROOT / "native-codex-observations.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps([{key:row[key] for key in ('case','exit_code','valid_json','description_visible','reviewer_visible','workspace_unchanged','stderr')} for row in results],indent=2))
