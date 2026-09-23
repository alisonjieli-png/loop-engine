"""Check Codex AGENTS.md discovery in a fresh step root without a model call."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CASES = (
    ("repair-one-failing-test", "Repair one failing test"),
    ("profile-one-csv", "Profile one CSV without changing it"),
)


def prompt_input(work: Path, home: Path, codex_home: Path) -> tuple[int, str, str]:
    env = {
        "PATH": os.environ["PATH"],
        "HOME": str(home),
        "CODEX_HOME": str(codex_home),
        "TERM": "dumb",
        "HTTP_PROXY": "http://127.0.0.1:9",
        "HTTPS_PROXY": "http://127.0.0.1:9",
        "ALL_PROXY": "http://127.0.0.1:9",
        "NO_PROXY": "127.0.0.1,localhost",
    }
    result = subprocess.run(
        [
            "codex", "debug", "prompt-input", "-c",
            "skills.bundled.enabled=false", "native discovery probe",
        ],
        cwd=work,
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    return result.returncode, result.stdout, result.stderr


def main() -> None:
    results = []
    for slug, marker in CASES:
        source = ROOT / slug / "codex/work/AGENTS.md"
        source_digest = hashlib.sha256(source.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory(prefix=".native-probe-", dir=ROOT) as scratch:
            temporary = Path(scratch)
            work = temporary / "work"
            home = temporary / "home"
            codex_home = temporary / "codex-home"
            for folder in (work, home, codex_home):
                folder.mkdir()
            copied = work / "AGENTS.md"
            shutil.copyfile(source, copied)
            if hashlib.sha256(copied.read_bytes()).hexdigest() != source_digest:
                raise SystemExit(f"{slug}: unchanged copy failed")
            subprocess.run(["git", "init", "-q"], cwd=work, check=True, capture_output=True)

            code, visible, stderr = prompt_input(work, home, codex_home)
            found = code == 0 and marker in visible
            copied.unlink()
            negative_code, negative_visible, negative_stderr = prompt_input(work, home, codex_home)
            rejected = negative_code == 0 and marker not in negative_visible
            results.append({
                "candidate_id": slug,
                "source_sha256": source_digest,
                "unchanged_template_visible_without_model": found,
                "removed_file_marker_absent": rejected,
                "positive_exit": code,
                "negative_exit": negative_code,
                "stderr_nonempty": bool(stderr or negative_stderr),
            })
    report = {
        "record_type": "native_context_codex_no_model_discovery_probe/v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "client": "codex-cli 0.155.1",
        "model_calls": 0,
        "method": "codex debug prompt-input on unchanged copy inside an isolated temporary git root, with empty HOME and CODEX_HOME and closed external proxy",
        "scope": "template discovery only; no input rendering, model use, task completion or other-client qualification",
        "observations": results,
    }
    name = "CODEX-NO-MODEL-DISCOVERY-" + datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%S%fZ") + ".json"
    path = ROOT / name
    with path.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    print(path)
    if not all(row["unchanged_template_visible_without_model"] and row["removed_file_marker_absent"] for row in results):
        raise SystemExit("a native discovery control failed; report retained")


if __name__ == "__main__":
    main()
