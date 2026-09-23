"""No-model check of Codex's optional CODEX.md fallback configuration.

The default configuration should ignore CODEX.md; a clean, isolated
CODEX_HOME with an explicit fallback should load it. This creates only
temporary files and writes one new, nonsecret observation record.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

MARKER = "BALTOR-CODEX-FALLBACK-PROBE-82f1"
DOCUMENT = f"# Candidate fallback\n{MARKER}\n"
CONFIGS = {
    "default": "project_doc_fallback_filenames = []\n[skills.bundled]\nenabled = false\n",
    "configured": "project_doc_fallback_filenames = [\"CODEX.md\"]\n[skills.bundled]\nenabled = false\n",
}


def probe() -> dict:
    version = subprocess.run(["codex", "--version"], capture_output=True,
                             text=True, timeout=10, check=True).stdout.strip()
    observations = []
    with tempfile.TemporaryDirectory(prefix="baltor-codex-fallback-") as scratch:
        root = Path(scratch)
        work = root / "work"
        work.mkdir()
        (work / ".git").mkdir()
        (work / "CODEX.md").write_text(DOCUMENT, encoding="utf-8")
        home = root / "home"
        home.mkdir()
        config = root / "codex-home"
        config.mkdir()
        environment = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": str(home),
            "CODEX_HOME": str(config),
            "TERM": "dumb",
            "HTTP_PROXY": "http://127.0.0.1:9",
            "HTTPS_PROXY": "http://127.0.0.1:9",
            "ALL_PROXY": "http://127.0.0.1:9",
        }
        for label, content in CONFIGS.items():
            (config / "config.toml").write_text(content, encoding="utf-8")
            result = subprocess.run(["codex", "debug", "prompt-input", "probe"],
                                    cwd=work, env=environment, capture_output=True,
                                    text=True, timeout=25, check=False)
            combined = result.stdout + result.stderr
            observations.append({
                "case": label,
                "config_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
                "exit_code": result.returncode,
                "marker_in_prompt_input": MARKER in combined,
                "captured_bytes": len(combined.encode("utf-8")),
            })
    return {
        "record_type": "codex_optional_instruction_fallback_probe/v1",
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "codex_version": version,
        "candidate_document_sha256": hashlib.sha256(DOCUMENT.encode("utf-8")).hexdigest(),
        "workspace": "fresh temporary git root with empty HOME and CODEX_HOME",
        "provider_calls": 0,
        "observations": observations,
        "limits": "Prompt-input observation only; no model use, customer task, or permission decision tested.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = probe()
        rows = {row["case"]: row for row in result["observations"]}
        if (rows["default"]["exit_code"] != 0
                or rows["configured"]["exit_code"] != 0
                or rows["default"]["marker_in_prompt_input"]
                or not rows["configured"]["marker_in_prompt_input"]):
            raise ValueError("Codex fallback behavior differs from expected control")
        if args.output.is_symlink():
            raise ValueError("output symlink refused")
        with args.output.open("x", encoding="utf-8") as target:
            json.dump(result, target, indent=2, sort_keys=True)
            target.write("\n")
        print("default ignored CODEX.md; configured fallback loaded CODEX.md")
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        parser.exit(1, f"Codex fallback probe refused: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
