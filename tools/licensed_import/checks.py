"""Static checks on every copied package, with no network and no model, and its declared effects.

The checks reuse the library ingestion component's safety-scan slot
(`library_safety_scan`): its engines are selected by that component's own
selection, in its declared order, and the decision is recorded before any
engine runs. One more engine with the same `scan_packages` interface adds
the rules this import needs and the built-in rules lack:

```text
Static checks on one package (every text file)
├── builtin_static_rules (library ingestion): instruction override, system prompt disclosure,
│   concealment, remote script piped to a shell, environment or credential exfiltration,
│   destructive commands, encoded payloads, bidirectional and tag characters, secret-shaped values,
│   hidden comment instructions
├── skillspector_static (library ingestion, when installed): NVIDIA SkillSpector, no model, no network
└── import_static_rules (this module)
    ├── blocking: variation-selector characters used to hide text
    └── caution for the reviewer: network use in code, permission-bypass flags, instructions to act
        without the user's confirmation, destructive git or database commands, a hook that runs on a
        harness event, a server configuration that downloads and runs a package
```

A blocking finding refuses the package by rule name and keeps its bytes in
quarantine only. A caution finding travels with the candidate for the
reviewers. A finding names its rule, severity, file and line and never
copies the text. A clean scan is triage, not proof of safety.

Declared effects are the library ingestion component's rules over each text
file, plus the effects the package's roles imply: any executable file, hook
or command-line server declares that it starts a process.
"""
from __future__ import annotations

import json
import re
from pathlib import PurePosixPath

from loop_engine.core.library_ingestion import engines as ingestion_engines
from loop_engine.core.library_ingestion.effects import declared_effects
from loop_engine.core.library_ingestion.record_rules import LibraryRecordError
from loop_engine.core.library_ingestion.rendering_types import RenderRefused
from loop_engine.core.library_ingestion.scan_builtin import BLOCKING, CAUTION
from loop_engine.core.library_ingestion.selection import select_engines
from loop_engine.core.library_ingestion.skill_rendering import parse_rule, parse_skill
from loop_engine.core.facets import EFFECTS
from loop_engine.core.service_runtime.catalogue_packages import EXECUTABLE_ROLES

from .records import HOOK, PROTOCOL_SERVER, SETTINGS

_CODE_SUFFIXES = frozenset({".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".sh", ".bash", ".zsh", ".rb", ".pl",
                            ".ps1", ".go", ".rs", ".php", ".lua"})
_NETWORK_IN_CODE = re.compile(
    r"(?:\bimport\s+(?:requests|httpx|aiohttp|socket|urllib3)\b|\bfrom\s+(?:requests|httpx|aiohttp|urllib)\b|"
    r"\burllib\.request\b|\bhttp\.client\b|\bfetch\s*\(|\baxios\b|\bXMLHttpRequest\b|\bhttps?\.request\s*\(|"
    r"\bnet\.(?:connect|createConnection)\b|\b(?:curl|wget)\s+\S|\bInvoke-(?:WebRequest|RestMethod)\b)")
_VARIATION_SELECTORS = re.compile("[\U000e0100-\U000e01ef]")
_PERMISSION_BYPASS = re.compile(r"(?:--dangerously-skip-permissions|--yolo\b|\bbypassPermissions\b|"
                                r"--full-auto\b|--dangerously-bypass-approvals-and-sandbox)")
_NO_CONFIRMATION = re.compile(r"\bwithout\s+(?:asking|confirming\s+with|consulting)\s+(?:the\s+)?user\b|"
                              r"\bnever\s+ask\s+(?:the\s+user\s+)?(?:for\s+)?(?:permission|confirmation)\b", re.I)
_DESTRUCTIVE_REPOSITORY = re.compile(r"\bgit\s+(?:push\s+(?:-f\b|--force\b)|reset\s+--hard\b|clean\s+-[a-z]*f)|"
                                     r"\bDROP\s+(?:DATABASE|TABLE|SCHEMA)\b|\bTRUNCATE\s+TABLE\b", re.I)
_DOWNLOAD_AND_RUN = ("npx", "uvx", "bunx", "pnpx")
IMPORT_RULES_ENGINE = "import_static_rules"


class ImportStaticRules:
    """The rules this import adds, behind the same scan_packages interface as the slot's engines."""

    engine_id = IMPORT_RULES_ENGINE
    engine_version = "1.0.0"
    engine_kind = "static_scanner"
    effects = ("pure",)

    def _finding(self, rule, severity, path, line):
        return {"rule": rule, "severity": severity, "line": line, "engine_id": self.engine_id, "path": path}

    def scan_text(self, path: str, text: str) -> list:
        findings = []
        code = PurePosixPath(path).suffix.lower() in _CODE_SUFFIXES
        for number, line in enumerate(text.splitlines(), start=1):
            if _VARIATION_SELECTORS.search(line):
                findings.append(self._finding("variation_selector_characters", BLOCKING, path, number))
            if code and _NETWORK_IN_CODE.search(line):
                findings.append(self._finding("network_use_in_code", CAUTION, path, number))
            if _PERMISSION_BYPASS.search(line):
                findings.append(self._finding("permission_bypass_flag", CAUTION, path, number))
            if _NO_CONFIRMATION.search(line):
                findings.append(self._finding("acts_without_user_confirmation", CAUTION, path, number))
            if _DESTRUCTIVE_REPOSITORY.search(line):
                findings.append(self._finding("destructive_repository_or_database_command", CAUTION, path, number))
        unique, seen = [], set()
        for finding in findings:
            key = (finding["rule"], finding["path"], finding["line"])
            if key not in seen:
                seen.add(key)
                unique.append(finding)
        return unique

    def scan_packages(self, packages: dict) -> dict:
        results = {}
        for key, files in packages.items():
            findings = []
            for path, data in files:
                try:
                    findings += self.scan_text(path, data.decode("utf-8"))
                except UnicodeDecodeError:
                    continue
            results[key] = findings
        return results


def package_cautions(kind: str, files: dict) -> list:
    """Cautions that follow from what the package is: an event hook, a download-and-run server."""
    found = []
    if kind == HOOK:
        found.append({"rule": "runs_on_harness_event", "severity": CAUTION, "line": 0,
                      "engine_id": IMPORT_RULES_ENGINE, "path": ""})
    if kind == SETTINGS:
        found.append({"rule": "changes_harness_settings", "severity": CAUTION, "line": 0,
                      "engine_id": IMPORT_RULES_ENGINE, "path": ""})
    if kind == PROTOCOL_SERVER:
        for path, data in files.items():
            for server in _servers(data):
                if str(server.get("command", "")).rsplit("/", 1)[-1] in _DOWNLOAD_AND_RUN:
                    found.append({"rule": "downloads_and_runs_a_package", "severity": CAUTION, "line": 0,
                                  "engine_id": IMPORT_RULES_ENGINE, "path": path})
                    break
    return found


def _servers(data: bytes) -> list:
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return []
    if not isinstance(value, dict):
        return []
    table = value.get("mcpServers") or value.get("servers") or {}
    return [server for server in table.values() if isinstance(server, dict)] if isinstance(table, dict) else []


class StaticChecks:
    """The selected scan engines, run over many packages at once, with their decision recorded."""

    def __init__(self, settings: "dict | None" = None, *, extra_engines=None, switched_off=()) -> None:
        settings = dict(settings or {})
        slot = ingestion_engines.SAFETY_SLOT
        try:
            self.decision, chosen = select_engines(slot, ingestion_engines.FACTORIES[slot.slot_id], settings,
                                                   switched_off=tuple(switched_off))
        except LibraryRecordError as error:
            # Every engine of the slot is switched off or unavailable here; the extra engines
            # still run, and the decision records why the slot chose none.
            self.decision, chosen = {"slot_id": slot.slot_id, "chosen": [], "reason": error.code}, ()
        self.engines = [factory.from_settings(settings, {}) for factory in chosen]
        self.engines += list(extra_engines if extra_engines is not None else [ImportStaticRules()])

    def describe(self) -> dict:
        return {"slot_decision": self.decision,
                "engines": [getattr(engine, "engine_id", type(engine).__name__) for engine in self.engines]}

    def scan(self, packages: dict) -> dict:
        """Package key to every finding of every engine; a failing engine refuses by caution, never silently."""
        results = {key: [] for key in packages}
        for engine in self.engines:
            try:
                found = engine.scan_packages(packages)
            except Exception as error:  # an engine failure is recorded, never read as a clean scan
                found = {key: [{"rule": "scan_engine_failed", "severity": BLOCKING, "line": 0,
                                "engine_id": getattr(engine, "engine_id", "unknown"),
                                "path": type(error).__name__}] for key in packages}
            for key, findings in found.items():
                results.setdefault(key, []).extend(findings)
        return results


class CiscoSkillScanner:
    """Engine cisco_skill_scanner_static: Cisco's skill-scanner, static analyzers only, sandboxed.

    It runs `skill-scanner scan-all` with no model option inside a bubblewrap
    sandbox that has no network and can write only its report folder, over
    many skills per call. A CRITICAL finding blocks; HIGH, MEDIUM and LOW are
    cautions; INFO is dropped. Only the rule, severity, file and line are
    kept: the scanner's snippets and descriptions copy text, and a finding
    never does. A run that fails or leaves no report blocks every package of
    its chunk, so a crash is never read as a clean scan.
    """

    engine_id = "cisco_skill_scanner_static"
    engine_version = "1.0.0"
    engine_kind = "static_scanner"
    effects = ("spawns_process", "reads_fs", "writes_fs")
    third_party = "cisco-ai-skill-scanner 2.1.0 (Apache-2.0), static analyzers, no model, sandboxed without network"
    chunk = 150

    def __init__(self, program: str, work_folder: str, *, timeout_seconds: float = 1800.0) -> None:
        self.program, self.work_folder, self.timeout_seconds = program, work_folder, timeout_seconds
        self.runs: list = []

    def scan_packages(self, packages: dict) -> dict:
        import shutil
        import tempfile
        from pathlib import Path

        from loop_engine.core.library_ingestion.processes import launcher_environment, run_command, sandbox_argv

        results = {key: [] for key in packages}
        keys = sorted(key for key, files in packages.items() if any(path == "SKILL.md" for path, _data in files))
        for start in range(0, len(keys), self.chunk):
            chunk = keys[start:start + self.chunk]
            Path(self.work_folder).mkdir(parents=True, exist_ok=True)
            root = Path(tempfile.mkdtemp(prefix="cisco-", dir=self.work_folder))
            inputs, outputs = root / "in", root / "out"
            outputs.mkdir(parents=True)
            folders = {}
            for index, key in enumerate(chunk):
                folder = f"item-{index:04d}"
                folders[folder] = key
                for path, data in packages[key]:
                    target = inputs / folder / path
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(data)
            report = outputs / "report.json"
            argv = sandbox_argv((self.program, "scan-all", str(inputs), "--recursive", "--format", "json",
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
                for key in chunk:
                    results[key].append({"rule": "cisco_scanner_run_failed", "severity": BLOCKING, "line": 0,
                                         "engine_id": self.engine_id, "path": ""})
                continue
            for row in data.get("results") or ():
                key = folders.get(Path(str(row.get("skill_path", ""))).name)
                if key is None:
                    continue
                for finding in row.get("findings") or ():
                    level = str(finding.get("severity", "")).upper()
                    if level == "INFO" or not level:
                        continue
                    results[key].append({"rule": f"cisco_{str(finding.get('rule_id', 'unknown')).lower()}"[:80],
                                         "severity": BLOCKING if level == "CRITICAL" else CAUTION,
                                         "line": int(finding.get("line_number") or 0),
                                         "engine_id": self.engine_id,
                                         "path": str(finding.get("file_path") or "")[:200]})
        return results


def blocking_rules(findings) -> list:
    return sorted({finding["rule"] for finding in findings if finding["severity"] == BLOCKING})


def frontmatter_of(text: str) -> dict:
    if not text.startswith("---"):
        return {}
    for parser in (parse_skill, parse_rule):
        try:
            value = parser(text).frontmatter
            return value if isinstance(value, dict) else {}
        except (RenderRefused, ValueError, TypeError):
            continue
    return {}


def package_effects(kind: str, files: dict, roles: dict) -> tuple:
    """(effects, evidence) of a package: every text file's declared effects plus its roles' effects."""
    found = {}
    for path, data in sorted(files.items()):
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            continue
        result = declared_effects(kind, text, frontmatter_of(text) if path.lower().endswith((".md", ".mdc")) else {})
        for row in result.evidence:
            found.setdefault(row["effect"], f"{row['rule']} in {PurePosixPath(path).name}")
    for path, role in roles.items():
        if role in EXECUTABLE_ROLES:
            found.setdefault("spawns_process", f"holds_an_executable_file {PurePosixPath(path).name}")
    if kind == HOOK:
        found.setdefault("spawns_process", "a_hook_runs_commands_on_harness_events")
    if kind == SETTINGS:
        # Settings can add hooks, protocol servers and permissions, so they declare the widest
        # effects on purpose: a step without those authorities is never offered them.
        found.setdefault("spawns_process", "harness_settings_can_start_hooks_and_servers")
        found.setdefault("network", "harness_settings_can_connect_servers")
    if kind == PROTOCOL_SERVER:
        for data in files.values():
            for server in _servers(data):
                if server.get("command"):
                    found.setdefault("spawns_process", "starts_a_local_server_process")
                if server.get("url") or str(server.get("command", "")).rsplit("/", 1)[-1] in _DOWNLOAD_AND_RUN:
                    found.setdefault("network", "reaches_or_downloads_a_server")
    if not found:
        return ("pure",), ()
    order = {name: index for index, name in enumerate(EFFECTS)}
    effects = tuple(sorted(found, key=order.__getitem__))
    return effects, tuple({"effect": effect, "rule": found[effect]} for effect in effects)
