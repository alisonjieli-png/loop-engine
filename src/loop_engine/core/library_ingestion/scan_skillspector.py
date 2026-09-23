"""Engine skillspector_static of the library_safety_scan engine slot.

The adopted scanner: NVIDIA SkillSpector 2.11.2 (Apache-2.0) at commit
844ac30f47ca4cc6ff0d1481ac88945eb0eff039, run in static mode (--no-llm)
over a folder of rendered skill packages at a time (--recursive), inside a
bubblewrap sandbox with no network, so its dependency lookup cannot leave
the machine and it can write only its report. A skill it recommends not to
install (score above its threshold of 50) is blocked; each of its findings
and an incomplete analysis are marked for the reviewer. A failed run marks
every package it covered, so a missing scan is never read as a clean one.
It is configured with the executable path; without one it is not_configured.
"""
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from .processes import executable, launcher_environment, run_command, sandbox_argv

BLOCKING, CAUTION = "blocking", "caution"
RISK_THRESHOLD = 50
CHUNK = 50


def findings_from_report(data: dict, folders: dict, engine_id: str) -> dict:
    """Package key to findings, from one SkillSpector JSON report over a folder of packages."""
    def finding(rule, severity, line=0):
        return {"rule": rule, "severity": severity, "line": line, "engine_id": engine_id}

    results = {key: [] for key in folders.values()}
    skills = data.get("skills") if isinstance(data.get("skills"), list) else [data]
    seen = set()
    for skill in skills:
        key = folders.get(Path(str(skill.get("path") or skill.get("name") or "")).name)
        if key is None:
            continue
        seen.add(key)
        assessment = skill.get("risk_assessment") or {}
        score = skill.get("risk_score", assessment.get("score", 0)) or 0
        if assessment.get("recommendation") == "DO_NOT_INSTALL" or score > RISK_THRESHOLD:
            results[key].append(finding("skillspector_do_not_install", BLOCKING))
        for issue in skill.get("issues") or ():
            line = (issue.get("location") or {}).get("start_line") or 0
            results[key].append(finding(f"skillspector_{issue.get('id', 'finding')}", CAUTION,
                                        int(line) if str(line).isdigit() else 0))
        completeness = skill.get("analysis_completeness") or data.get("analysis_completeness") or {}
        if completeness and completeness.get("is_complete") is False:
            results[key].append(finding("skillspector_scan_incomplete", CAUTION))
    for key in set(results) - seen:
        results[key].append(finding("skillspector_package_not_reported", CAUTION))
    return results


class SkillSpectorStatic:
    """SkillSpector's static scan, many skills per run, without network."""

    engine_id = "skillspector_static"
    engine_version = "1.0.0"
    engine_kind = "static_scanner"
    effects = ("spawns_process", "reads_fs", "writes_fs")
    third_party = "NVIDIA SkillSpector 2.11.2 (Apache-2.0) at 844ac30, --no-llm, sandboxed without network"

    def __init__(self, program: str, work_folder: str, *, timeout_seconds: float = 900.0) -> None:
        self.program, self.work_folder, self.timeout_seconds = program, Path(work_folder), timeout_seconds
        self.runs: list = []

    @classmethod
    def availability(cls, settings: dict):
        program = settings.get("skillspector_program")
        if not program or not Path(program).is_file() or not settings.get("work_folder"):
            return False, "not_configured"
        if executable("bwrap") is None:
            return False, "dependency_missing"
        return True, "available"

    @classmethod
    def from_settings(cls, settings: dict, resources: dict):
        """Construct from declared settings and the run's resources; nothing starts here."""
        return cls(settings["skillspector_program"], settings["work_folder"])

    def describe(self) -> dict:
        return {"engine_id": self.engine_id, "engine_version": self.engine_version,
                "third_party": self.third_party, "runs": len(self.runs)}

    def _finding(self, rule: str, severity: str, line: int = 0) -> dict:
        return {"rule": rule, "severity": severity, "line": line, "engine_id": self.engine_id}

    def scan_packages(self, packages: dict) -> dict:
        results = {}
        keys = sorted(key for key, files in packages.items() if any(path.endswith("SKILL.md") for path, _ in files))
        for start in range(0, len(keys), CHUNK):
            results.update(self._scan_chunk({key: packages[key] for key in keys[start:start + CHUNK]}))
        for key in packages:
            results.setdefault(key, [])
        return results

    def _scan_chunk(self, chunk: dict) -> dict:
        self.work_folder.mkdir(parents=True, exist_ok=True)
        root = Path(tempfile.mkdtemp(prefix="skillspector-", dir=self.work_folder))
        inputs, outputs = root / "in", root / "out"
        inputs.mkdir()
        outputs.mkdir()
        folders = {}
        for index, (key, files) in enumerate(sorted(chunk.items())):
            folder = f"item-{index:03d}"
            folders[folder] = key
            for path, data in files:
                target = inputs / folder / Path(path).name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
        report = outputs / "report.json"
        argv = sandbox_argv((self.program, "scan", str(inputs), "--recursive", "--no-llm", "--format", "json",
                             "--output", str(report)), read_only_paths=(inputs,), writable_paths=(outputs,))
        result = run_command(argv, timeout_seconds=self.timeout_seconds, maximum_output_bytes=4 * 1024 * 1024,
                             environment=launcher_environment())
        self.runs.append({"packages": len(chunk), "exit_code": result.exit_code,
                          "elapsed_ms": round(result.elapsed_ms, 1), "timed_out": result.timed_out})
        try:
            data = json.loads(report.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = None
        shutil.rmtree(root, ignore_errors=True)
        if not isinstance(data, dict):
            return {key: [self._finding("skillspector_run_failed", CAUTION)] for key in chunk}
        return findings_from_report(data, folders, self.engine_id)
