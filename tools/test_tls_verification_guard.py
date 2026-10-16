"""No current file switches TLS certificate verification off, except the declared exceptions below.

Roadmap step S-6.189 asks that no generation lane run with certificate verification switched off, with a
check and a removed-guard control. This check reads every tracked file that runs code or sets a process
environment: Python through its syntax tree; JavaScript and TypeScript, shell scripts, workflow and action
files, container files and YAML settings through line patterns. It skips ``artifacts/`` and dated records,
whose bytes are history. A file that switches verification off on purpose is named in ``ALLOWED`` with the
rule and the reason. An exception that no longer matches anything fails as well, so the list stays exact.

```text
TLS verification guard
├── Python: check_hostname off, CERT_NONE, verify=False, ssl=False, an unverified context,
│   tls_verification skip, NODE_TLS_REJECT_UNAUTHORIZED set to 0 or false
├── JavaScript and TypeScript: rejectUnauthorized false, NODE_TLS_REJECT_UNAUTHORIZED 0,
│   an empty checkServerIdentity, strictSSL false
├── shell, workflows, container files: NODE_TLS_REJECT_UNAUTHORIZED=0, curl -k or --insecure,
│   wget --no-check-certificate, PYTHONHTTPSVERIFY=0, GIT_SSL_NO_VERIFY, http.sslVerify false
├── YAML settings: tls_verification skip, NODE_TLS_REJECT_UNAUTHORIZED 0
└── known-wrong controls: each rule flags its bad form, leaves the safe forms alone, and a tree holding
    the old lane line and the old notebook probe fails the guard
```
"""
from __future__ import annotations

import ast
import functools
import os
import re
import subprocess
import sys
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from build_records_index import classify  # noqa: E402  the repository's one definition of a dated name

NODE_TLS = "NODE_TLS_REJECT_UNAUTHORIZED"

#: (path, rule) -> why this file switches verification off on purpose. Keep each reason specific.
ALLOWED = {
    ("src/loop_engine/core/custom_endpoint.py", "python.check_hostname_off"):
        "The typed tls_verification: skip setting of one custom endpoint: an explicit per-endpoint operator "
        "choice that describe() and every run record show, never a default and never applied to another "
        "provider.",
    ("src/loop_engine/core/custom_endpoint.py", "python.cert_none"):
        "The same typed tls_verification: skip setting; the context it builds serves that one declared "
        "endpoint only.",
    ("tools/task_campaign.py", "python.check_hostname_off"):
        "The opt-in --insecure-health-probe flag of the September task campaign: off by default, it prints a "
        "warning, and the default probe verifies with the system store.",
    ("tools/task_campaign.py", "python.cert_none"):
        "The same opt-in --insecure-health-probe flag; the default health probe keeps CERT_REQUIRED.",
    ("tools/test_custom_endpoint_tls_trust.py", "python.tls_verification_skip"):
        "Known-wrong declarations the TLS trust contract must refuse: skip beside a pin or a server name.",
    ("tools/test_generate_original_native_provider_binding.py", "python.tls_verification_skip"):
        "Known-wrong bindings the generator must refuse before any credential is read: an unverified "
        "provider is never bound.",
    ("tools/test_opencode_generation_lanes.py", "python.node_tls_off"):
        "A known-wrong parent environment: the check proves the Tactical lane never passes the variable on "
        "to its OpenCode process.",
    ("tools/test_regenerate_all.py", "python.verify_false"):
        "verify= is the regeneration registry runner's own output check, not a TLS setting.",
}

PYTHON_TRIGGER = re.compile(r"CERT_NONE|check_hostname|verify\s*=\s*False|\.verify\s*=|ssl\s*=\s*False|"
                            r"_create_unverified_context|_create_default_https_context|" + NODE_TLS
                            + r"|tls_verification")
NODE_TLS_TEXT = re.compile(NODE_TLS + r"""['"\]]*\s*[=:]\s*['"]?(?:0|false)\b""", re.IGNORECASE)
SCRIPT_RULES = (
    ("script.reject_unauthorized_false", re.compile(r"rejectUnauthorized\s*[:=]\s*false\b")),
    ("script.node_tls_off", NODE_TLS_TEXT),
    ("script.empty_server_identity_check", re.compile(r"checkServerIdentity\s*[:=]\s*(?:\(\s*\)|_)\s*=>")),
    ("script.strict_ssl_false", re.compile(r"strictSSL\s*[:=]\s*false\b")),
)
SHELL_RULES = (
    ("shell.node_tls_off", re.compile(NODE_TLS + r"""=['"]?(?:0|false)\b""", re.IGNORECASE)),
    ("shell.curl_insecure", re.compile(r"\bcurl\b[^\n|;&#]*\s(?:-[A-Za-z]*k[A-Za-z]*|--insecure)(?=\s|$)")),
    ("shell.wget_no_check_certificate", re.compile(r"\bwget\b[^\n|;&#]*--no-check-certificate")),
    ("shell.python_https_verify_off", re.compile(r"""PYTHONHTTPSVERIFY=['"]?0\b""")),
    ("shell.git_ssl_no_verify", re.compile(r"\bGIT_SSL_NO_VERIFY\s*[=:]")),
    ("shell.git_ssl_verify_false", re.compile(r"""http\.sslVerify[= ]+['"]?false""", re.IGNORECASE)),
)
#: YAML settings name the variable or the setting as a mapping key; prose that mentions them is not a setting.
CONFIG_RULES = (
    ("config.node_tls_off", re.compile(r"""^\s*(?:-\s*)?['"]?""" + NODE_TLS + r"""['"]?\s*:\s*['"]?(?:0|false)\b""",
                                       re.IGNORECASE)),
    ("config.tls_verification_skip", re.compile(r"""^\s*(?:-\s*)?['"]?tls_verification['"]?\s*:\s*['"]?skip\b""")),
)
SCRIPT_SUFFIXES = (".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".mts", ".cts")
SHELL_SUFFIXES = (".sh", ".bash", ".zsh")
YAML_SUFFIXES = (".yml", ".yaml")


@dataclass(frozen=True, order=True)
class Finding:
    path: str
    line: int
    rule: str


def _constant(node, *values) -> bool:
    return isinstance(node, ast.Constant) and any(
        type(node.value) is type(value) and node.value == value for value in values)


def _off(node) -> bool:
    """A value that turns NODE_TLS_REJECT_UNAUTHORIZED off: 0, "0", "false" or False."""
    return _constant(node, 0, "0", "false", "False", False)


def _cert_none(node) -> bool:
    return (isinstance(node, ast.Attribute) and node.attr == "CERT_NONE") or (
        isinstance(node, ast.Name) and node.id == "CERT_NONE")


def _callee(node) -> str:
    return node.attr if isinstance(node, ast.Attribute) else node.id if isinstance(node, ast.Name) else ""


def python_findings(source: str, path: str = "<source>") -> list:
    """The rules a Python source breaks, from its syntax tree; strings and comments never count as code."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return [Finding(path, 1, "python.unparsed")] if PYTHON_TRIGGER.search(source) else []
    parents, docstrings, found = {}, set(), []
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                docstrings.add(first.value)

    def flag(node, rule):
        found.append(Finding(path, getattr(node, "lineno", 1), rule))

    def assigned(target, value, node):
        if isinstance(target, ast.Attribute):
            if target.attr == "check_hostname" and _constant(value, False, 0, None):
                flag(node, "python.check_hostname_off")
            if target.attr == "verify_mode" and _constant(value, 0):
                flag(node, "python.cert_none")
            if target.attr == "verify" and _constant(value, False):
                flag(node, "python.verify_false")
            if target.attr == "_create_default_https_context":
                flag(node, "python.unverified_context")
        if isinstance(target, ast.Subscript) and _constant(target.slice, NODE_TLS) and _off(value):
            flag(node, "python.node_tls_off")

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                assigned(target, node.value, node)
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign)) and node.value is not None:
            assigned(node.target, node.value, node)
        elif isinstance(node, ast.Call):
            for keyword in node.keywords:
                if keyword.arg in ("verify", "check_hostname") and _constant(keyword.value, False):
                    flag(node, "python.verify_false" if keyword.arg == "verify" else "python.check_hostname_off")
                elif keyword.arg == "ssl" and _constant(keyword.value, False):
                    flag(node, "python.ssl_false")
                elif keyword.arg == "cert_reqs" and _constant(keyword.value, "CERT_NONE", 0):
                    flag(node, "python.cert_none")
                elif keyword.arg == NODE_TLS and _off(keyword.value):
                    flag(node, "python.node_tls_off")
                elif keyword.arg == "tls_verification" and _constant(keyword.value, "skip"):
                    flag(node, "python.tls_verification_skip")
            name = _callee(node.func)
            if (name in ("setdefault", "putenv", "__setitem__") and len(node.args) >= 2
                    and _constant(node.args[0], NODE_TLS) and _off(node.args[1])):
                flag(node, "python.node_tls_off")
            if (name == "setattr" and len(node.args) == 3 and _constant(node.args[1], "check_hostname")
                    and _constant(node.args[2], False, 0, None)):
                flag(node, "python.check_hostname_off")
        elif isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if _constant(key, NODE_TLS) and _off(value):
                    flag(key, "python.node_tls_off")
                elif _constant(key, "tls_verification") and _constant(value, "skip"):
                    flag(key, "python.tls_verification_skip")
        elif isinstance(node, (ast.Attribute, ast.Name)) and _callee(node) == "_create_unverified_context":
            flag(node, "python.unverified_context")
        elif _cert_none(node):
            # A comparison or an assertion reads the setting; anything else uses it.
            ancestor, reading = parents.get(node), False
            while ancestor is not None and not reading:
                reading = isinstance(ancestor, ast.Compare) or (
                    isinstance(ancestor, ast.Call) and _callee(ancestor.func).startswith("assert"))
                ancestor = parents.get(ancestor)
            if not reading:
                flag(node, "python.cert_none")
        elif (isinstance(node, ast.Constant) and isinstance(node.value, str) and node not in docstrings
              and NODE_TLS_TEXT.search(node.value)):
            flag(node, "python.node_tls_off")
    return found


def line_findings(text: str, rules, comment_prefixes, path: str = "<source>") -> list:
    found = []
    for number, line in enumerate(text.splitlines(), start=1):
        if line.lstrip().startswith(comment_prefixes):
            continue
        found.extend(Finding(path, number, rule) for rule, pattern in rules if pattern.search(line))
    return found


def _shell_script(path: Path, head: str) -> bool:
    return path.suffix in SHELL_SUFFIXES or (not path.suffix and re.match(r"#!.*\b(?:ba|z|da)?sh\b", head) is not None)


def file_findings(root: Path, relative: str) -> list:
    path = root / relative
    if path.is_symlink() or not path.is_file():
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    name = path.name
    if path.suffix == ".py":
        return python_findings(text, relative) if PYTHON_TRIGGER.search(text) else []
    if path.suffix in SCRIPT_SUFFIXES:
        return line_findings(text, SCRIPT_RULES, ("//", "/*", "*"), relative)
    workflow = relative.startswith((".github/workflows/", ".github/actions/"))
    if name.startswith("Dockerfile") or (workflow and path.suffix in YAML_SUFFIXES):
        return line_findings(text, SHELL_RULES + CONFIG_RULES, ("#",), relative)
    if path.suffix in YAML_SUFFIXES:
        return line_findings(text, CONFIG_RULES, ("#",), relative)
    if _shell_script(path, text[:200]):
        return line_findings(text, SHELL_RULES, ("#",), relative)
    return []


def current(relative: str) -> bool:
    """A current file: outside artifacts/ and outside every dated record (a dated file or folder name)."""
    parts = relative.split("/")
    return parts[0] != "artifacts" and not any(classify(part) is not None for part in parts)


def tracked_files(root: Path) -> list:
    """The files git tracks when ``root`` is the top of a work tree, otherwise every file under it."""
    try:
        top = subprocess.run(["git", "-C", str(root), "rev-parse", "--show-toplevel"], capture_output=True,
                             check=True, timeout=60, text=True).stdout.strip()
        if Path(top).resolve() == root.resolve():
            listed = subprocess.run(["git", "-C", str(root), "ls-files", "-z"], capture_output=True, check=True,
                                    timeout=120).stdout.decode("utf-8", "surrogateescape").split("\0")
            return sorted(item for item in listed if item)
    except (OSError, subprocess.SubprocessError):
        pass
    return sorted(str(Path(folder, name).relative_to(root)).replace(os.sep, "/")
                  for folder, directories, names in os.walk(root)
                  if ".git" not in Path(folder).relative_to(root).parts for name in names)


def scan_tree(root: Path) -> list:
    return sorted(finding for relative in tracked_files(root) if current(relative)
                  for finding in file_findings(root, relative))


@functools.lru_cache(maxsize=1)
def repository_findings() -> tuple:
    return tuple(scan_tree(ROOT))


class RepositoryTest(unittest.TestCase):
    def test_no_current_file_switches_verification_off_outside_the_declared_exceptions(self):
        unexpected = [finding for finding in repository_findings() if (finding.path, finding.rule) not in ALLOWED]
        self.assertEqual(unexpected, [], "certificate verification switched off at:\n" + "\n".join(
            f"  {finding.path}:{finding.line} {finding.rule}" for finding in unexpected))

    def test_every_declared_exception_still_matches_and_gives_its_reason(self):
        matched = {(finding.path, finding.rule) for finding in repository_findings()}
        self.assertEqual(sorted(set(ALLOWED) - matched), [], "remove exceptions that match nothing")
        for key, reason in ALLOWED.items():
            self.assertGreater(len(reason), 50, key)

    def test_no_generation_lane_or_tactical_client_is_an_exception(self):
        for path, _rule in ALLOWED:
            self.assertNotIn(path, ("tools/opencode_generation_lanes.py", "tools/overnight_candidate_batch.py",
                                    "tools/showcase_3d/proxy.py", "tools/verified_forwarder.py",
                                    "kaggle/02_tacticalengineering_only.py", "kaggle/03_three_provider_failover.py"))


class KnownWrongControlTest(unittest.TestCase):
    def rules(self, findings) -> set:
        return {finding.rule for finding in findings}

    def test_each_python_rule_flags_its_bad_form(self):
        cases = {
            "context.check_hostname = False": "python.check_hostname_off",
            "setattr(context, 'check_hostname', False)": "python.check_hostname_off",
            "context.verify_mode = ssl.CERT_NONE": "python.cert_none",
            "context.verify_mode = CERT_NONE": "python.cert_none",
            "context.verify_mode = 0": "python.cert_none",
            "ssl.wrap_socket(sock, cert_reqs=ssl.CERT_NONE)": "python.cert_none",
            "urllib3.PoolManager(cert_reqs='CERT_NONE')": "python.cert_none",
            "requests.get(url, verify=False)": "python.verify_false",
            "session.verify = False": "python.verify_false",
            "aiohttp.TCPConnector(ssl=False)": "python.ssl_false",
            "ssl._create_default_https_context = ssl._create_unverified_context": "python.unverified_context",
            "opener = ssl._create_unverified_context()": "python.unverified_context",
            "environment['" + NODE_TLS + "'] = '0'": "python.node_tls_off",
            "os.environ.setdefault('" + NODE_TLS + "', '0')": "python.node_tls_off",
            "env = {'" + NODE_TLS + "': 0}": "python.node_tls_off",
            "env = dict(" + NODE_TLS + "='false')": "python.node_tls_off",
            "subprocess.run('" + NODE_TLS + "=" + "0 opencode run', shell=True)": "python.node_tls_off",
            "endpoint = CustomEndpoint(name='x', tls_verification='skip')": "python.tls_verification_skip",
            "provider = {'tls_verification': 'skip'}": "python.tls_verification_skip",
        }
        for source, rule in cases.items():
            with self.subTest(source=source):
                self.assertIn(rule, self.rules(python_findings(source)))

    def test_the_safe_python_forms_are_not_flagged(self):
        safe = '''
"""A docstring may say that NODE_TLS_REJECT_UNAUTHORIZED''' + '''=0 and check_hostname = False are refused."""
import ssl
context = ssl.create_default_context(cafile="anchor.pem")
context.check_hostname = True
context.verify_mode = ssl.CERT_REQUIRED
# context.check_hostname = False would be refused
assert context.verify_mode != ssl.CERT_NONE
if context.verify_mode == ssl.CERT_NONE:
    raise ValueError("unverified")
self.assertEqual(context.verify_mode, ssl.CERT_NONE)
environment.pop("NODE_TLS_REJECT_UNAUTHORIZED", None)
note = "never send NODE_TLS_REJECT_UNAUTHORIZED to a harness"
requests.get(url, verify="anchor.pem")
provider = {"tls_verification": "ca_file"}
'''
        self.assertEqual(python_findings(safe), [])

    def test_each_script_rule_flags_its_bad_form(self):
        cases = {
            "https.request({host, rejectUnauthorized: false})": "script.reject_unauthorized_false",
            "agent.options.rejectUnauthorized = false;": "script.reject_unauthorized_false",
            "process.env." + NODE_TLS + ' = "0";': "script.node_tls_off",
            "process.env['" + NODE_TLS + "'] = '0';": "script.node_tls_off",
            "tls.connect({checkServerIdentity: () => undefined})": "script.empty_server_identity_check",
            "request({url, strictSSL: false})": "script.strict_ssl_false",
        }
        for source, rule in cases.items():
            with self.subTest(source=source):
                self.assertIn(rule, self.rules(line_findings(source, SCRIPT_RULES, ("//", "/*", "*"))))
        safe = ("// rejectUnauthorized: false is refused here\n * strictSSL: false is refused\n"
                "https.request({host, rejectUnauthorized: true})\n"
                "tls.connect({checkServerIdentity: (host, cert) => verify(host, cert)})\n")
        self.assertEqual(line_findings(safe, SCRIPT_RULES, ("//", "/*", "*")), [])

    def test_each_shell_rule_flags_its_bad_form(self):
        cases = {
            NODE_TLS + "=" + "0 opencode run --pure": "shell.node_tls_off",
            "export " + NODE_TLS + "='0'": "shell.node_tls_off",
            "curl -k https://origin.fixture.invalid/v1/models": "shell.curl_insecure",
            "curl -fsSLk https://origin.fixture.invalid/v1/models": "shell.curl_insecure",
            "curl --insecure https://origin.fixture.invalid/v1/models": "shell.curl_insecure",
            "wget --no-check-certificate https://origin.fixture.invalid/x": "shell.wget_no_check_certificate",
            "PYTHONHTTPSVERIFY=0 python3 tool.py": "shell.python_https_verify_off",
            "export GIT_SSL_NO_VERIFY=1": "shell.git_ssl_no_verify",
            "git -c http.sslVerify=false clone https://origin.fixture.invalid/r": "shell.git_ssl_verify_false",
        }
        for source, rule in cases.items():
            with self.subTest(source=source):
                self.assertIn(rule, self.rules(line_findings(source, SHELL_RULES, ("#",))))
        safe = ("# curl -k is refused here\nsort -k2 data.txt\ncurl -fsS https://origin.fixture.invalid\n"
                "curl -K settings.conf https://origin.fixture.invalid\ncurl --keepalive-time 5 https://x.invalid\n"
                "ssh -k host\n")
        self.assertEqual(line_findings(safe, SHELL_RULES, ("#",)), [])

    def test_each_settings_rule_flags_its_bad_form_and_not_prose(self):
        cases = {
            "env:\n  " + NODE_TLS + ': "0"': "config.node_tls_off",
            "providers:\n  - tls_verification: skip": "config.tls_verification_skip",
            "    tls_verification: 'skip'": "config.tls_verification_skip",
        }
        for source, rule in cases.items():
            with self.subTest(source=source):
                self.assertIn(rule, self.rules(line_findings(source, CONFIG_RULES, ("#",))))
        prose = ('evidence: "one lane sets ' + NODE_TLS + '=' + '0 for its process"\n'
                 "tls_verification: ca_file\n# tls_verification: skip is refused\n")
        self.assertEqual(line_findings(prose, CONFIG_RULES, ("#",)), [])

    def test_a_tree_holding_the_old_lane_line_and_the_old_notebook_probe_fails_the_guard(self):
        old_lane = 'environment = {}\nenvironment["' + NODE_TLS + '"] = "0"\n'
        old_probe = ("import ssl\ncontext = ssl.create_default_context()\ncontext.check_hostname = False\n"
                     "context.verify_mode = ssl.CERT_NONE\n")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for relative, text in (("tools/opencode_generation_lanes.py", old_lane),
                                   ("kaggle/02_tacticalengineering_only.py", old_probe),
                                   ("tools/run.sh", "#!/bin/sh\ncurl -sk https://origin.fixture.invalid/v1\n"),
                                   ("tools/fetch", "#!/usr/bin/env bash\n" + NODE_TLS + "=" + "0 node x.js\n"),
                                   ("artifacts/old-run/lane.py", old_lane),
                                   ("docs/verification/OLD-RECORD-2026-09-23/probe.py", old_probe),
                                   ("docs/context/probe-2026-09-24.py", old_probe)):
                (root / relative).parent.mkdir(parents=True, exist_ok=True)
                (root / relative).write_text(text)
            findings = scan_tree(root)
        self.assertEqual({(finding.path, finding.rule) for finding in findings},
                         {("tools/opencode_generation_lanes.py", "python.node_tls_off"),
                          ("kaggle/02_tacticalengineering_only.py", "python.check_hostname_off"),
                          ("kaggle/02_tacticalengineering_only.py", "python.cert_none"),
                          ("tools/run.sh", "shell.curl_insecure"),
                          ("tools/fetch", "shell.node_tls_off")})
        self.assertTrue(all((finding.path, finding.rule) not in ALLOWED for finding in findings),
                        "none of these is a declared exception, so the repository check would fail on them")


if __name__ == "__main__":
    unittest.main()
