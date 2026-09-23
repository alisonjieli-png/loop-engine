"""Engine builtin_static_rules of the library_safety_scan engine slot.

A static scan of every text file of a rendered package, with no network and
no model. Blocking rules refuse an item by name: an instruction to ignore
earlier instructions or reveal a system prompt, an instruction to hide an
action from the user, a remote script piped into a shell, a credential file
or the environment sent over the network, a command that destroys a home or
root folder, bidirectional or invisible tag characters, a value with the
shape of a secret, a decoded payload piped into a shell and an instruction
to a model hidden in an HTML comment. Caution rules only mark an item for
the reviewer. A finding names its rule, severity and line and never copies
the text. Scanner output is triage for independent review, never approval.
"""
from __future__ import annotations

import re

from ..model_call_records import default_secret_patterns

BLOCKING, CAUTION = "blocking", "caution"
_I = re.I
_SENDERS = r"\b(?:curl|wget|nc|ncat|netcat|scp|rsync|ftp|invoke-webrequest|iwr|requests\.post|fetch)\b"
_CREDENTIAL_PATHS = re.compile(
    r"(?:\.ssh/(?:id_[a-z0-9]+|identity)\b(?!\.pub)|\.aws/credentials|\.config/gh/hosts\.yml|"
    r"\.docker/config\.json|\.kube/config|\.netrc\b|\.npmrc\b|\.pypirc\b|\.git-credentials|"
    r"\bid_rsa\b(?!\.pub))", _I)
_LINE_RULES = (
    ("instruction_override", BLOCKING, re.compile(
        r"\b(?:ignore|disregard|forget|override)\b[^.\n]{0,40}?\b(?:all\s+|any\s+|the\s+|your\s+)?"
        r"(?:previous|prior|above|earlier|preceding|system|original)\s+(?:instructions?|prompts?|"
        r"directions|rules|messages?|guidelines)\b", _I)),
    ("instruction_override", BLOCKING, re.compile(
        r"\byou\s+are\s+now\s+(?:in\s+)?(?:developer\s+mode|dan\b|jailbroken|unrestricted)", _I)),
    ("system_prompt_disclosure", BLOCKING, re.compile(
        r"\b(?:reveal|print|output|repeat|show|leak)\b[^.\n]{0,30}\b(?:your|the)\s+(?:system\s+prompt|"
        r"hidden\s+instructions|initial\s+instructions)\b", _I)),
    ("concealment", BLOCKING, re.compile(
        r"\b(?:(?:do\s+not|don't|never)\s+(?:tell|inform|alert|notify)\s+the\s+user|without\s+"
        r"(?:telling|informing|notifying|alerting)\s+the\s+user)\b", _I)),
    ("remote_script_to_shell", BLOCKING, re.compile(
        r"\b(?:curl|wget|iwr|irm)\b[^\n|]{0,300}\|\s*(?:sudo\s+)?(?:(?:ba|z|da|k)?sh|python3?|node|perl|ruby)\b", _I)),
    ("remote_script_to_shell", BLOCKING, re.compile(r"\b(?:ba|z)?sh\s+<\(\s*(?:curl|wget)\b", _I)),
    ("remote_script_to_shell", BLOCKING, re.compile(
        r"\b(?:iex|invoke-expression)\b[^\n]{0,20}?(?:iwr|irm|invoke-webrequest|invoke-restmethod|"
        r"net\.webclient)", _I)),
    ("environment_exfiltration", BLOCKING, re.compile(
        r"\b(?:printenv|env|export\s+-p)\s*\|\s*(?:curl|wget|nc|ncat|netcat)\b", _I)),
    ("destructive_command", BLOCKING, re.compile(
        r"\brm\s+-(?:[a-z]*r[a-z]*f|[a-z]*f[a-z]*r)[a-z]*\s+(?:--no-preserve-root\s+)?"
        r"(?:/|~/?|\$HOME/?|/\*)(?=[\s'\"`]|$)", _I)),
    ("destructive_command", BLOCKING, re.compile(r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:")),
    ("destructive_command", BLOCKING, re.compile(
        r"\bmkfs\.[a-z0-9]+\s+/dev/|\bdd\s+if=[^\n]{0,80}\bof=/dev/(?:sd|nvme|hd|disk)", _I)),
    ("encoded_payload_executed", BLOCKING, re.compile(
        r"\bbase64\s+(?:-d|--decode|-D)\b[^\n]{0,40}\|\s*(?:sudo\s+)?(?:(?:ba|z)?sh|python3?|node|perl)\b", _I)),
    ("long_encoded_blob", CAUTION, re.compile(r"[A-Za-z0-9+/]{240,}={0,2}")),
)
_HIDDEN_CONTROLS = re.compile("[\u202a-\u202e\u2066-\u2069\U000e0000-\U000e007f]")
_INVISIBLE = re.compile("[\u200b-\u200d\u2060]|(?<!^)\ufeff")
_COMMENT = re.compile(r"<!--(.*?)-->", re.S)
_COMMENT_ADDRESSEE = re.compile(r"\b(?:assistant|ai|model|agent|claude|codex|llm|copilot)\b", _I)
_COMMENT_ORDER = re.compile(r"\b(?:run|execute|ignore|send|delete|upload|do\s+not\s+mention|don't\s+mention|"
                            r"never\s+mention)\b", _I)


class BuiltinStaticRules:
    """Blocking and caution rules over text, with line numbers and no copied text."""

    engine_id = "builtin_static_rules"
    engine_version = "1.0.0"
    engine_kind = "static_scanner"
    effects = ("pure",)
    third_party = "rules written here; the secret patterns are the repository's own"

    def __init__(self) -> None:
        self._secrets = tuple(re.compile(pattern) for pattern in default_secret_patterns())

    @classmethod
    def availability(cls, settings: dict):
        return True, "always_available"

    @classmethod
    def from_settings(cls, settings: dict, resources: dict):
        """Construct from declared settings and the run's resources; nothing starts here."""
        return cls()

    def describe(self) -> dict:
        return {"engine_id": self.engine_id, "engine_version": self.engine_version,
                "engine_kind": self.engine_kind, "rules": sorted({rule for rule, _, _ in _LINE_RULES})}

    def _finding(self, rule: str, severity: str, line: int) -> dict:
        return {"rule": rule, "severity": severity, "line": line, "engine_id": self.engine_id}

    def scan_text(self, text: str) -> list:
        findings = []
        for number, line in enumerate(text.splitlines(), start=1):
            for rule, severity, pattern in _LINE_RULES:
                if pattern.search(line):
                    findings.append(self._finding(rule, severity, number))
            if _CREDENTIAL_PATHS.search(line) and re.search(_SENDERS, line, _I):
                findings.append(self._finding("credential_exfiltration", BLOCKING, number))
            if _HIDDEN_CONTROLS.search(line):
                findings.append(self._finding("hidden_text_control", BLOCKING, number))
            if _INVISIBLE.search(line):
                findings.append(self._finding("invisible_characters", CAUTION, number))
            if any(pattern.search(line) for pattern in self._secrets):
                findings.append(self._finding("secret_shaped_value", BLOCKING, number))
        for match in _COMMENT.finditer(text):
            body = match.group(1)
            if _COMMENT_ADDRESSEE.search(body) and _COMMENT_ORDER.search(body):
                findings.append(self._finding("hidden_comment_instruction", BLOCKING,
                                              text[:match.start()].count("\n") + 1))
        unique, seen = [], set()
        for finding in findings:
            key = (finding["rule"], finding["line"])
            if key not in seen:
                seen.add(key)
                unique.append(finding)
        return unique

    def scan_packages(self, packages: dict) -> dict:
        """Package key to findings, over every text file of each package."""
        results = {}
        for key, files in packages.items():
            findings = []
            for path, data in files:
                try:
                    text = data.decode("utf-8")
                except UnicodeDecodeError:
                    findings.append({**self._finding("binary_file", CAUTION, 0), "path": path})
                    continue
                findings += [{**finding, "path": path} for finding in self.scan_text(text)]
            results[key] = findings
        return results
