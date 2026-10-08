"""The deterministic qualification checks. Each can only refuse, and each has a known-wrong control.

```text
Qualification of one generated component (every check runs; any refusal refuses the component)
├── source identity checked
│   ├── manifest: record type, authoring, line, kind and form, identity bound to the package digest,
│   │   the record's file list equal to the package, required files present
│   └── licence_provenance: an accepted licence expression (every identifier on the accepted list, no
│       WITH exception), licence texts and attribution present, every file's digest in the attribution,
│       the generator's version and code revision (a commit this repository holds), each fact source
│       pinned by address and SHA-256 with an accepted licence, upstream copies bound to their digest,
│       launcher packages pinned to an exact version, install downloads pinned by SHA-256
├── implementation tested
│   ├── parse: UTF-8 text, Python parses (never executed here), strict JSON without repeated keys or
│   │   non-finite numbers, TOML, CSV
│   ├── schema: JSON Schema documents, harness configuration shapes, connection and install records
│   ├── effects: declared effects in the vocabulary and covering what the code does (Python syntax tree:
│   │   processes, network, file writes and reads, declared credentials) and what the licensed import's
│   │   effect rules find in the text; executable files declare a process
│   ├── sandbox: every module imports and the package's own tests pass in the sandbox, at least one ran
│   └── mutation: with every public function and method replaced by one that raises, the tests must fail
├── compatibility tested: the sandbox's interpreter, or each harness configuration format validated
└── publication safety
    ├── safety: the library ingestion and licensed import scan engines, the review panel's static rules
    │   (hidden and control characters, instruction override, download piped to a shell, decoded text run
    │   by a shell, destructive commands, credential file reads), minified or bundled code, and test code
    │   that tampers with the test report
    ├── secrets: the repository's secret patterns and the panel's extra shapes, in every file and the record
    └── duplicates: exact package or distinctive-content copies, and near copies (population-level)
```

A check reads the component's exact bytes and record; only the sandbox check executes anything, inside
the sandbox. A passed check approves nothing.
"""
from __future__ import annotations

import ast
import csv
from dataclasses import dataclass, field
from fractions import Fraction
import io
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import unicodedata

try:  # Python 3.11 and later; the repository supports 3.10 with tomli, as pyproject.toml declares
    import tomllib
except ImportError:  # pragma: no cover - exercised on 3.10
    import tomli as tomllib

from loop_engine.core.facets import EFFECTS
from loop_engine.core.service_runtime.catalogue_packages import EXECUTABLE_ROLES

from . import sandbox as sandbox_module

VERSION = "1"
PASSED, REFUSED, NOT_APPLICABLE = "passed", "refused", "not_applicable"
SOURCE_IDENTITY, IMPLEMENTATION, COMPATIBILITY, PUBLICATION = (
    "source_identity_checked", "implementation_tested", "compatibility_tested", "publication_safety")
POLICY_PATH = Path(__file__).resolve().parent / "resources" / "qualification-policy.json"
TEXT_MEDIA_PREFIXES = ("text/",)
TEXT_MEDIA = frozenset({"application/json", "application/schema+json", "application/toml", "application/yaml",
                        "application/x-sh", "application/xml", "application/sql", "application/x-python"})
_HEX40 = re.compile(r"[0-9a-f]{40}")
_HEX64 = re.compile(r"[0-9a-f]{64}")
_SEMVER = re.compile(r"\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?")
_IDENTITY = re.compile(r"library\.supply\.([a-z_]+)\.([0-9a-f]{24})\.([0-9a-f]{16})")
_SPDX_TOKEN = re.compile(r"\s*(\(|\)|[A-Za-z0-9.+-]+)")
DETAIL_LIMIT = 300


@dataclass(frozen=True)
class CheckResult:
    check_id: str
    version: str
    kind: str
    dimension: str
    status: str
    findings: tuple = ()
    notes: tuple = ()

    def to_dict(self) -> dict:
        return {"check_id": self.check_id, "version": self.version, "kind": self.kind,
                "dimension": self.dimension, "status": self.status,
                "findings": [{"code": code, "detail": detail[:DETAIL_LIMIT]} for code, detail in self.findings],
                "notes": list(self.notes)}


@dataclass
class QualificationContext:
    """What every check may consult: the policy, the repository, scanners, and population-level results."""

    policy: dict
    repository: Path
    sandbox_settings: "sandbox_module.SandboxSettings | None" = None
    work_root: "Path | None" = None
    duplicates: dict = field(default_factory=dict)
    revisions: dict = field(default_factory=dict)
    _static: object = None
    _patterns: tuple = ()

    @classmethod
    def load(cls, repository: Path, *, sandbox_settings=None, work_root=None, policy_path: Path = POLICY_PATH):
        policy = json.loads(Path(policy_path).read_text(encoding="utf-8"))
        if policy.get("record_type") != "component_qualification_policy/v1":
            raise ValueError("the qualification policy has another record type")
        return cls(policy, Path(repository), sandbox_settings, Path(work_root) if work_root else None)

    @property
    def static_checks(self):
        if self._static is None:
            from tools.licensed_import.checks import StaticChecks
            self._static = StaticChecks()
        return self._static

    @property
    def secret_patterns(self) -> tuple:
        if not self._patterns:
            from tools.candidate_review.prechecks.secrets import secret_patterns
            panel = json.loads((self.repository / "tools/candidate_review/resources/panel.json").read_text())
            self._patterns = secret_patterns(panel["precheck_engines"]["builtin_secret_patterns"])
        return self._patterns

    def revision_exists(self, revision: str) -> bool:
        if revision not in self.revisions:
            done = subprocess.run(["git", "-C", str(self.repository), "cat-file", "-e", f"{revision}^{{commit}}"],
                                  capture_output=True, check=False)
            self.revisions[revision] = done.returncode == 0
        return self.revisions[revision]


def _result(check, findings, notes=()) -> CheckResult:
    return CheckResult(check.check_id, VERSION, check.kind, check.dimension,
                       REFUSED if findings else PASSED, tuple(findings), tuple(notes))


def _not_applicable(check, note: str) -> CheckResult:
    return CheckResult(check.check_id, VERSION, check.kind, check.dimension, NOT_APPLICABLE, (), (note,))


def is_text(entry) -> bool:
    return entry.media_type.startswith(TEXT_MEDIA_PREFIXES) or entry.media_type in TEXT_MEDIA


def is_data_file(path: str, policy: dict) -> bool:
    parts = PurePosixPath(path).parts
    return len(parts) > 1 and parts[0] in policy["data_folders"]


def is_test_file(path: str) -> bool:
    return PurePosixPath(path).name.startswith("test_") and path.endswith(".py")


def licence_identifiers(expression: str) -> "list | None":
    """The identifiers of an SPDX expression of AND, OR and parentheses; None when it is not one."""
    if type(expression) is not str or not expression.strip():
        return None
    tokens, position = [], 0
    while position < len(expression):
        match = _SPDX_TOKEN.match(expression, position)
        if not match:
            if expression[position:].strip():
                return None
            break
        tokens.append(match.group(1))
        position = match.end()
    depth, expect_operand, identifiers = 0, True, []
    for token in tokens:
        if token == "(":
            if not expect_operand:
                return None
            depth += 1
        elif token == ")":
            if expect_operand or depth == 0:
                return None
            depth -= 1
        elif token in ("AND", "OR"):
            if expect_operand:
                return None
            expect_operand = True
        elif token == "WITH":
            return None
        else:
            if not expect_operand:
                return None
            identifiers.append(token)
            expect_operand = False
    return identifiers if identifiers and depth == 0 and not expect_operand else None


class ManifestCheck:
    check_id, kind, dimension = "manifest", "format", SOURCE_IDENTITY

    def run(self, component, context) -> CheckResult:
        policy, record, findings = context.policy, component.candidate, []
        if record.get("record_type") != policy["record_types"]["candidate"]:
            findings.append(("record_type_unsupported", str(record.get("record_type"))))
        if record.get("authoring") != policy["authoring"]:
            findings.append(("authoring_not_generated", str(record.get("authoring"))))
        line = policy["lines"].get(component.line)
        if line is None:
            findings.append(("line_unknown", component.line))
            return _result(self, findings)
        if component.kind not in line["kinds"]:
            findings.append(("kind_not_of_line", component.kind))
        form = record.get("component_form")
        if (not isinstance(form, dict) or form.get("record_type") != policy["record_types"]["component_form"]
                or form.get("form") not in line["forms"]):
            findings.append(("form_not_of_line", json.dumps(form)[:120]))
        match = _IDENTITY.fullmatch(component.identity)
        if (not match or match.group(1) != component.line
                or not component.package.package_digest.startswith(match.group(3))):
            findings.append(("identity_not_bound_to_package", component.identity))
        declared = sorted((row.get("path"), row.get("digest"), row.get("size_bytes"), row.get("media_type"),
                           row.get("role")) for row in record.get("files", []) if isinstance(row, dict))
        package = sorted((entry.path, entry.digest, entry.size_bytes, entry.media_type, entry.role)
                         for entry in component.package.files)
        if declared != package:
            findings.append(("file_list_differs_from_package", f"{len(declared)} declared, {len(package)} packaged"))
        paths = {entry.path for entry in component.package.files}
        for required in line["required_files"]:
            if required not in paths:
                findings.append(("required_file_missing", required))
        if line["shape"] == "code":
            modules, tests = sandbox_module.python_modules(component)
            if not modules:
                findings.append(("no_python_module", "a code component holds at least one root-level module"))
            if not tests:
                findings.append(("no_test_module", "a code component holds at least one root-level test_*.py"))
        try:
            constraint_group(component, policy, replay=True)
        except Exception as error:
            findings.append(("constraint_group_invalid", type(error).__name__))
        return _result(self, findings)


class LicenceProvenanceCheck:
    check_id, kind, dimension = "licence_provenance", "licence", SOURCE_IDENTITY

    def run(self, component, context) -> CheckResult:
        policy, record, findings = context.policy, component.candidate, []
        accepted = set(policy["accepted_licences"])
        licence = record.get("licence") if isinstance(record.get("licence"), dict) else {}
        identifiers = licence_identifiers(licence.get("spdx_expression", ""))
        if identifiers is None:
            findings.append(("licence_expression_invalid", str(licence.get("spdx_expression"))))
        else:
            outside = sorted(set(identifiers) - accepted)
            if outside:
                findings.append(("licence_not_accepted", ",".join(outside)))
        texts = licence.get("texts") if isinstance(licence.get("texts"), list) else []
        if not texts:
            findings.append(("licence_text_missing", "the record names no licence text"))
        granted = set()
        for path in texts:
            text = component.text(path) if isinstance(path, str) else None
            if not text or not text.strip():
                findings.append(("licence_text_missing", str(path)))
                continue
            recognized = recognized_licences(text, policy)
            if not recognized:
                findings.append(("licence_text_unrecognized", str(path)))
            granted |= recognized
        if identifiers is not None and texts and set(identifiers) - granted:
            findings.append(("licence_text_does_not_grant_declared",
                             ",".join(sorted(set(identifiers) - granted))))
        attribution_path = licence.get("attribution")
        attribution = component.text(attribution_path) if isinstance(attribution_path, str) else None
        if not attribution:
            findings.append(("attribution_missing", str(attribution_path)))
        else:
            for entry in component.package.files:
                if entry.path != attribution_path and entry.digest not in attribution:
                    findings.append(("attribution_lacks_file_digest", entry.path))
        provenance = record.get("provenance") if isinstance(record.get("provenance"), dict) else {}
        generator = provenance.get("generator") if isinstance(provenance.get("generator"), dict) else {}
        revision = str(generator.get("code_revision", ""))
        if not generator.get("identity") or not _SEMVER.fullmatch(str(generator.get("version", ""))):
            findings.append(("generator_unnamed", json.dumps(generator)[:120]))
        if not _HEX40.fullmatch(revision):
            findings.append(("generator_revision_not_pinned", revision[:60]))
        elif not context.revision_exists(revision):
            findings.append(("generator_revision_unknown", revision))
        facts = provenance.get("facts") if isinstance(provenance.get("facts"), list) else []
        if not facts:
            findings.append(("fact_sources_missing", "the record names no fact source"))
        file_digests = {entry.digest for entry in component.package.files}
        governed = False
        for fact in facts:
            fact = fact if isinstance(fact, dict) else {}
            fact_licence = fact.get("licence") if isinstance(fact.get("licence"), dict) else {}
            fact_ids = licence_identifiers(fact_licence.get("spdx_expression", ""))
            if (fact.get("record_type") != policy["record_types"]["fact_source"]
                    or not _pinned_address(fact.get("url"), policy)
                    or not _HEX64.fullmatch(str(fact.get("sha256", ""))) or not fact.get("retrieved_at")):
                findings.append(("fact_source_not_pinned", str(fact.get("url", ""))[:160]))
            accepted_fact = fact_ids is not None and not set(fact_ids) - accepted
            metadata_only = (fact.get("role") in policy["metadata_fact_roles"]
                             and fact.get("sha256") not in file_digests)
            if accepted_fact and fact.get("role") not in policy["metadata_fact_roles"]:
                governed = True
            if not accepted_fact and not (metadata_only and fact_licence.get("spdx_expression") == "NOASSERTION"):
                findings.append(("fact_licence_not_accepted", str(fact_licence.get("spdx_expression"))))
        if facts and not governed:
            findings.append(("no_governing_licence_fact", "no licence text, specification or data fact carries "
                                                          "an accepted licence"))
        for row in record.get("files", []):
            if isinstance(row, dict) and row.get("origin") == "upstream_verbatim":
                upstream = row.get("upstream") if isinstance(row.get("upstream"), dict) else {}
                if upstream.get("sha256") != row.get("digest") or not _pinned_address(upstream.get("url"), policy):
                    findings.append(("upstream_copy_not_bound", str(row.get("path"))))
        # An upstream notice file (Apache-2.0 section 4(d)) is carried verbatim; one the record names that is not a
        # verbatim upstream copy is refused, so the list cannot hide generated files from the duplicate check.
        notices = licence.get("notices", [])
        origins = {row.get("path"): row.get("origin") for row in record.get("files", []) if isinstance(row, dict)}
        if not isinstance(notices, list) or any(origins.get(path) != "upstream_verbatim" for path in notices
                                                if isinstance(path, str)) or not all(
                isinstance(path, str) for path in notices):
            findings.append(("notice_not_an_upstream_copy", json.dumps(notices)[:160]))
        findings += _pinned_launchers(component, policy)
        findings += _pinned_downloads(component, policy)
        return _result(self, findings)


def recognized_licences(text: str, policy: dict) -> set:
    """The accepted licences whose fingerprint phrases a licence text holds, case and spacing ignored."""
    folded = " ".join(text.lower().split())
    found = set()
    for identifier, rule in policy["licence_fingerprints"].items():
        if all(phrase in folded for phrase in rule.get("all", [])) and not any(
                phrase in folded for phrase in rule.get("none", [])):
            found.add(identifier)
    return found


def _pinned_address(url, policy) -> bool:
    """Whether a fact or upstream address uses one of the policy's address schemes."""
    return isinstance(url, str) and url.split("://", 1)[0] in policy["address_schemes"] and "://" in url


def _server_tables(component, policy) -> list:
    """(path, name, command list) for every server of every harness configuration file."""
    rows = []
    for path, shape in policy["harness_configurations"].items():
        text = component.text(path)
        if text is None:
            continue
        try:
            value = tomllib.loads(text) if shape["format"] == "toml" else json.loads(text)
        except (ValueError, tomllib.TOMLDecodeError):
            continue
        table = value.get(shape["table"]) if isinstance(value, dict) else None
        for name, server in (table.items() if isinstance(table, dict) else ()):
            if not isinstance(server, dict):
                rows.append((path, name, None))
            elif "command_list" in shape:
                rows.append((path, name, server.get(shape["command_list"])))
            else:
                command, arguments = server.get(shape["command"]), server.get(shape["arguments"], [])
                rows.append((path, name, [command] + list(arguments) if isinstance(arguments, list) else None))
    return rows


def _pinned_launchers(component, policy) -> list:
    findings = []
    for path, name, command in _server_tables(component, policy):
        if not isinstance(command, list) or not command or any(type(part) is not str for part in command):
            findings.append(("server_command_invalid", f"{path}:{name}"))
            continue
        launcher = PurePosixPath(command[0]).name
        registry = policy["package_launchers"].get(launcher)
        if registry is None:
            continue
        packages = [part for part in command[1:] if not part.startswith("-")]
        if not packages:
            findings.append(("launcher_package_missing", f"{path}:{name}"))
            continue
        spec = packages[0]
        # npm pins name@version (a scoped name starts with @); uvx pins name==version or name@version.
        if registry == "pypi" and "==" in spec:
            version = spec.split("==", 1)[1]
        else:
            version = spec.rsplit("@", 1)[1] if "@" in spec.lstrip("@") else ""
        if not _SEMVER.fullmatch(version):
            findings.append(("launcher_package_not_pinned", f"{path}:{name}:{spec[:80]}"))
    return findings


def _pinned_downloads(component, policy) -> list:
    text = component.text("install.json")
    if text is None:
        return []
    try:
        recipe = json.loads(text)
    except ValueError:
        return [("install_recipe_invalid", "install.json is not JSON")]
    findings = []

    def walk(value, where):
        if isinstance(value, dict):
            url = value.get("url")
            if isinstance(url, str):
                scheme = url.split("://", 1)[0] if "://" in url else ""
                if scheme not in policy["download_schemes"] or not _HEX64.fullmatch(str(value.get("sha256", ""))):
                    findings.append(("download_not_pinned", f"{where}:{url[:120]}"))
            for key, item in value.items():
                walk(item, f"{where}.{key}")
        elif isinstance(value, list):
            for index, item in enumerate(value):
                walk(item, f"{where}[{index}]")

    walk(recipe, "install")
    return findings


def _strict_json(text: str):
    def pairs(items):
        keys = [key for key, _value in items]
        if len(set(keys)) != len(keys):
            raise ValueError("repeated key")
        return dict(items)

    def constant(name):
        raise ValueError(f"non-finite number {name}")

    return json.loads(text, object_pairs_hook=pairs, parse_constant=constant)


class ParseCheck:
    check_id, kind, dimension = "parse", "format", IMPLEMENTATION

    def run(self, component, context) -> CheckResult:
        findings = []
        for entry in component.package.files:
            if not is_text(entry):
                findings.append(("binary_file_unverified", entry.path))
                continue
            text = component.text(entry.path)
            if text is None:
                findings.append(("text_not_utf8", entry.path))
                continue
            suffix = PurePosixPath(entry.path).suffix.lower()
            try:
                if suffix == ".py":
                    ast.parse(text, filename=entry.path)
                elif suffix == ".json":
                    _strict_json(text)
                elif suffix == ".toml":
                    tomllib.loads(text)
                elif suffix == ".csv":
                    list(csv.reader(io.StringIO(text)))
            except SyntaxError as error:
                findings.append(("python_syntax_error", f"{entry.path}:{error.lineno}"))
            except (ValueError, tomllib.TOMLDecodeError, csv.Error, RecursionError) as error:
                findings.append(("document_does_not_parse", f"{entry.path}: {type(error).__name__}"))
        return _result(self, findings)


class SchemaCheck:
    check_id, kind, dimension = "schema", "format", IMPLEMENTATION

    def run(self, component, context) -> CheckResult:
        policy, findings, notes = context.policy, [], []
        for entry in component.package.files:
            if PurePosixPath(entry.path).name == "schema.json":
                findings += _schema_findings(entry.path, component.text(entry.path))
        shapes = policy["harness_configurations"]
        present = [path for path in shapes if path in component.payloads]
        if present:
            servers = _server_tables(component, policy)
            names = {path: sorted(name for where, name, _command in servers if where == path) for path in present}
            for path in present:
                if not names[path]:
                    findings.append(("harness_configuration_has_no_server", path))
            if len({tuple(value) for value in names.values()}) > 1:
                findings.append(("harness_configurations_disagree", json.dumps(names)[:200]))
            commands = {json.dumps(command) for _path, _name, command in servers}
            if len(commands) > 1:
                findings.append(("harness_commands_disagree", f"{len(commands)} different commands"))
            notes.append("harness formats validated: " + ", ".join(present))
        documented = policy["lines"].get(component.line, {}).get("documented_fields")
        if documented:
            operation = python_assignment(component, policy["lines"][component.line]["job_key"]["python_assignment"])
            readme = component.text("README.md") or ""
            if not isinstance(operation, dict):
                findings.append(("operation_undeclared", "the module declares no operation record"))
            elif " ".join(str(operation.get(field)) for field in documented) not in readme:
                findings.append(("documentation_contradicts_operation",
                                 " ".join(str(operation.get(field)) for field in documented)[:160]))
        connection = component.text("baltor-connection.json")
        if connection is not None:
            try:
                value = json.loads(connection)
                if value.get("record_type") != policy["record_types"]["connection"]:
                    findings.append(("connection_record_type", str(value.get("record_type"))))
            except ValueError:
                findings.append(("connection_record_invalid", "baltor-connection.json"))
        recipe = component.text("install.json")
        if recipe is not None:
            try:
                value = json.loads(recipe)
                if (value.get("record_type") != policy["record_types"]["install_recipe"]
                        or not str(value.get("program", "")).strip() or not str(value.get("version", "")).strip()):
                    findings.append(("install_recipe_incomplete", "install.json"))
            except ValueError:
                findings.append(("install_recipe_invalid", "install.json"))
        return _result(self, findings, notes)


def _schema_findings(path: str, text: "str | None") -> list:
    if text is None:
        return [("schema_not_text", path)]
    try:
        schema = json.loads(text)
    except ValueError:
        return [("schema_not_json", path)]
    if not isinstance(schema, dict):
        return [("schema_not_object", path)]
    try:
        import jsonschema
        validator = jsonschema.validators.validator_for(schema, default=jsonschema.Draft202012Validator)
        validator.check_schema(schema)
    except ImportError:
        allowed = {"object", "array", "string", "number", "integer", "boolean", "null"}
        kinds = schema.get("type")
        kinds = [kinds] if isinstance(kinds, str) else kinds
        if kinds is not None and (not isinstance(kinds, list) or set(kinds) - allowed):
            return [("schema_invalid", path)]
    except Exception as error:  # jsonschema.SchemaError and its relatives
        return [("schema_invalid", f"{path}: {type(error).__name__}")]
    return []


PROCESS_MODULES = frozenset({"subprocess", "pty", "multiprocessing"})
NETWORK_MODULES = frozenset({"socket", "ssl", "urllib.request", "http.client", "ftplib", "smtplib", "poplib",
                             "imaplib", "telnetlib", "xmlrpc.client", "requests", "httpx", "aiohttp", "urllib3",
                             "websocket", "websockets"})
WRITE_CALLS = frozenset({"os.remove", "os.unlink", "os.rename", "os.replace", "os.makedirs", "os.mkdir",
                         "os.rmdir", "os.removedirs", "os.chmod", "os.chown", "os.symlink", "os.link",
                         "os.truncate", "shutil.copy", "shutil.copy2", "shutil.copyfile", "shutil.copytree",
                         "shutil.move", "shutil.rmtree", "shutil.make_archive", "shutil.unpack_archive",
                         "tempfile.mkstemp", "tempfile.mkdtemp", "tempfile.NamedTemporaryFile",
                         "tempfile.TemporaryDirectory", "tempfile.TemporaryFile"})
WRITE_METHODS = frozenset({"write_text", "write_bytes", "touch", "unlink", "rmdir", "mkdir", "symlink_to",
                           "hardlink_to"})
READ_METHODS = frozenset({"read_text", "read_bytes", "iterdir", "glob", "rglob"})
READ_CALLS = frozenset({"os.listdir", "os.scandir", "os.walk"})
PROCESS_CALL_PREFIXES = ("os.system", "os.popen", "os.fork", "os.exec", "os.spawn", "os.posix_spawn")
#: The keyword argument of open() that names its mode (Python's own vocabulary).
OPEN_MODE_KEYWORD = "mode"


def _dotted(node) -> str:
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return ".".join(reversed(parts))
    return ""


def _opener_request(node, aliases) -> bool:
    """True for urllib.request.build_opener(...).open(...) written in one expression: the opener's open sends a
    request (the network, which the module's import of urllib.request already shows) and reads no file. An
    opener kept in a variable first is not followed, so its open still counts as a file read."""
    receiver = node.func.value if isinstance(node.func, ast.Attribute) else None
    if not isinstance(receiver, ast.Call):
        return False
    head, _, rest = _dotted(receiver.func).partition(".")
    return (f"{aliases.get(head, head)}.{rest}" if rest else aliases.get(head, head)) == "urllib.request.build_opener"


def code_effects(text: str, credentials) -> dict:
    """Effects a Python module's syntax tree shows, each with the first line that shows it."""
    tree = ast.parse(text)
    aliases, found = {}, {}

    def note(effect, node):
        found.setdefault(effect, getattr(node, "lineno", 0))

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                aliases[alias.asname or alias.name.split(".")[0]] = alias.name if alias.asname else alias.name.split(".")[0]
                if alias.name in PROCESS_MODULES or alias.name.split(".")[0] in PROCESS_MODULES:
                    note("spawns_process", node)
                if alias.name in NETWORK_MODULES or alias.name.split(".")[0] in {"requests", "httpx", "aiohttp",
                                                                                   "urllib3", "socket", "ssl"}:
                    note("network", node)
        elif isinstance(node, ast.ImportFrom) and node.module:
            base = node.module
            for alias in node.names:
                aliases[alias.asname or alias.name] = f"{base}.{alias.name}"
                full = f"{base}.{alias.name}"
                if base.split(".")[0] in PROCESS_MODULES:
                    note("spawns_process", node)
                if base in NETWORK_MODULES or full in NETWORK_MODULES or base.split(".")[0] in {
                        "requests", "httpx", "aiohttp", "urllib3", "socket", "ssl"}:
                    note("network", node)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _dotted(node.func)
        head, _, rest = name.partition(".")
        resolved = f"{aliases.get(head, head)}.{rest}" if rest else aliases.get(head, head)
        if resolved.startswith(PROCESS_CALL_PREFIXES):
            note("spawns_process", node)
        if resolved in WRITE_CALLS:
            note("writes_fs", node)
        if resolved in READ_CALLS:
            note("reads_fs", node)
        if isinstance(node.func, ast.Attribute):
            if node.func.attr in WRITE_METHODS:
                note("writes_fs", node)
            elif node.func.attr in READ_METHODS:
                note("reads_fs", node)
        if resolved in ("open", "io.open", "builtins.open") or (isinstance(node.func, ast.Attribute)
                                                                and node.func.attr == "open" and resolved != "os.open"
                                                                and head not in ("webbrowser",)
                                                                and not _opener_request(node, aliases)):
            mode = node.args[1] if len(node.args) > 1 else next((keyword.value for keyword in node.keywords
                                                                 if keyword.arg == OPEN_MODE_KEYWORD), None)
            mode_text = mode.value if isinstance(mode, ast.Constant) and isinstance(mode.value, str) else "r"
            note("writes_fs" if set(mode_text) & set("wax+") else "reads_fs", node)
        if resolved in ("os.getenv", "os.environ.get") and node.args:
            argument = node.args[0]
            if isinstance(argument, ast.Constant) and argument.value in credentials:
                note("reads_secret", node)
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and _dotted(node.value) == "os.environ":
            key = node.slice
            if isinstance(key, ast.Constant) and key.value in credentials:
                note("reads_secret", node)
    return found


class EffectsCheck:
    check_id, kind, dimension = "effects", "effects", IMPLEMENTATION

    def run(self, component, context) -> CheckResult:
        record, findings, notes = component.candidate, [], []
        declared = record.get("declared_effects")
        if type(declared) is not list or any(type(effect) is not str for effect in declared):
            return _result(self, [("effects_not_a_list", "declared_effects is a list of effect names")])
        unknown = sorted(set(declared) - set(EFFECTS))
        if unknown:
            findings.append(("effect_unknown", ",".join(unknown)))
        if len(set(declared)) != len(declared):
            findings.append(("effect_repeated", "an effect is declared twice"))
        if "pure" in declared and len(set(declared)) > 1:
            findings.append(("pure_combined", "pure excludes every other effect"))
        evidence = {row.get("effect") for row in record.get("effect_evidence", []) if isinstance(row, dict)}
        for effect in set(declared) - {"pure"} - evidence:
            findings.append(("effect_without_evidence_rule", effect))
        credentials = {name for name in record.get("credentials", []) if isinstance(name, str)}
        derived = {}
        for entry in component.package.files:
            if entry.path.endswith(".py") and not is_test_file(entry.path):
                text = component.text(entry.path)
                try:
                    for effect, line in code_effects(text or "", credentials).items():
                        derived.setdefault(effect, f"{entry.path}:{line}")
                except SyntaxError:
                    findings.append(("effects_unreadable", entry.path))
        if any(entry.role in EXECUTABLE_ROLES for entry in component.package.files):
            derived.setdefault("spawns_process", "an executable file role")
        from tools.licensed_import.checks import package_effects
        text_roles = set(context.policy["effect_text_roles"])
        _effects, evidence_rows = package_effects(
            component.kind, {entry.path: component.payloads[entry.path] for entry in component.package.files
                             if entry.role in text_roles and not is_data_file(entry.path, context.policy)},
            {entry.path: entry.role for entry in component.package.files})
        for row in evidence_rows:
            if row["effect"] != "pure":
                derived.setdefault(row["effect"], f"the licensed import's rule {row['rule']}")
        for effect in sorted(set(derived) - set(declared)):
            findings.append(("undeclared_effect", f"{effect} shown by {derived[effect]}"))
        notes.append("derived: " + ",".join(sorted(derived)) if derived else "derived: none")
        return _result(self, findings, notes)


LITERAL_NODES = (ast.Dict, ast.List, ast.Tuple, ast.Set, ast.Constant, ast.Name, ast.Attribute, ast.Load,
                 ast.UnaryOp, ast.USub, ast.UAdd, ast.Starred, ast.JoinedStr, ast.FormattedValue)


def literal_statement_lines(text: str) -> set:
    """Lines held by exactly one statement that only displays literal data (no call, no operator but a sign)."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return set()
    starts, literal = {}, set()
    for node in ast.walk(tree):
        if isinstance(node, ast.stmt):
            for line in range(node.lineno, (node.end_lineno or node.lineno) + 1):
                starts[line] = starts.get(line, 0) + 1 if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                                                                                 ast.ClassDef, ast.If, ast.For,
                                                                                 ast.While, ast.With, ast.Try)) else \
                    starts.get(line, 0)
            value = getattr(node, "value", None)
            if isinstance(node, (ast.Assign, ast.AnnAssign, ast.Expr, ast.Return)) and value is not None and all(
                    isinstance(child, LITERAL_NODES) for child in ast.walk(value)):
                literal.update(range(node.lineno, (node.end_lineno or node.lineno) + 1))
    return {line for line in literal if starts.get(line, 0) == 1}


JAVASCRIPT_CONSTANT = re.compile(r"(?:export\s+)?const\s+[A-Za-z_$][\w$]*\s*=\s*(.+);")


def javascript_literal_lines(text: str) -> set:
    """Lines held by exactly one constant declaration whose whole value is JSON, such as a generated client's
    parameter table: JSON is literal data in JavaScript, and a second statement on the line makes the value
    fail to parse as JSON, so minified code is never exempt."""
    exempt = set()
    for number, line in enumerate(text.splitlines(), 1):
        match = JAVASCRIPT_CONSTANT.fullmatch(line.strip())
        if match is None:
            continue
        try:
            json.loads(match.group(1))
        except ValueError:
            continue
        exempt.add(number)
    return exempt


TEST_TAMPERING = re.compile(r"\bos\._exit\s*\(|\bsys\.(?:stdout|stderr|__stdout__|__stderr__)\s*=|"
                            r"\bTextTestRunner\b|\bTestResult\b|\bunittest\.main\s*\(\s*exit\s*=\s*False")


class SafetyCheck:
    check_id, kind, dimension = "safety", "safety", PUBLICATION

    def run(self, component, context) -> CheckResult:
        from tools.candidate_review.prechecks.safety_rules import ALLOWED_CONTROLS, RULES, _invisible
        from tools.licensed_import.checks import blocking_rules
        policy, findings, notes = context.policy, [], []
        texts = {entry.path: component.text(entry.path) for entry in component.package.files if is_text(entry)}
        scanned = context.static_checks.scan({component.identity: [
            (path, text.encode("utf-8")) for path, text in texts.items() if text is not None
            and not is_data_file(path, policy)]})[component.identity]
        for rule in blocking_rules(scanned):
            findings.append(("static_scan_blocking", rule))
        cautions = sorted({finding["rule"] for finding in scanned if finding["severity"] != "blocking"})
        if cautions:
            notes.append("cautions: " + ",".join(cautions))
        limits = policy["minified_code"]
        for path, text in texts.items():
            if text is None:
                continue
            data_file = is_data_file(path, policy)
            if not data_file:
                hidden = sorted({f"U+{ord(character):04X}" for character in text if _invisible(character)})
                if hidden:
                    findings.append(("hidden_character", f"{path}: {hidden[:6]}"))
                controls = sorted({f"U+{ord(character):04X}" for character in text
                                   if unicodedata.category(character) == "Cc" and character not in ALLOWED_CONTROLS
                                   and character != "\r"})
                if controls:
                    findings.append(("control_character", f"{path}: {controls[:6]}"))
            for code, pattern in RULES:
                if code == "hidden_comment" and data_file:
                    continue
                match = pattern.search(text)
                if match:
                    findings.append((code, f"{path}:{text.count(chr(10), 0, match.start()) + 1}"))
            if PurePosixPath(path).suffix.lower() in policy["code_suffixes"] and not data_file:
                lines = text.splitlines() or [""]
                exempt = (literal_statement_lines(text) if path.endswith(".py") else
                          javascript_literal_lines(text) if path.endswith((".js", ".mjs")) else set())
                long_lines = [(number, len(line)) for number, line in enumerate(lines, 1)
                              if len(line) > limits["longest_line"] and number not in exempt]
                mean = len(text) / len(lines)
                if long_lines or (len(text) > limits["large_file_bytes"] and mean > limits["large_file_mean_line"]):
                    longest = max((length for _number, length in long_lines), default=max(len(line) for line in lines))
                    findings.append(("minified_or_bundled_code", f"{path}: longest line {longest}"))
            if is_test_file(path) and TEST_TAMPERING.search(text):
                findings.append(("test_report_tampering", path))
        return _result(self, findings, notes)


class SecretsCheck:
    check_id, kind, dimension = "secrets", "secrets", PUBLICATION

    def run(self, component, context) -> CheckResult:
        findings = []
        places = [(entry.path, component.text(entry.path)) for entry in component.package.files]
        places.append(("candidate record", json.dumps(dict(component.candidate), sort_keys=True)))
        for place, text in places:
            if text is None:
                continue
            for number, pattern in enumerate(context.secret_patterns):
                if pattern.search(text):
                    findings.append(("secret_shaped_value", f"{place} matches secret pattern {number}"))
        return _result(self, findings)


def licence_paths(record) -> set:
    """The licence texts, upstream notice files and attribution of a candidate record: paths every package of
    one source carries alike, which say nothing about the job the package does."""
    licence = record.get("licence") or {}
    notices = licence.get("notices") if isinstance(licence.get("notices"), list) else []
    return (set(licence.get("texts") or []) | {path for path in notices if isinstance(path, str)}) | {
        licence.get("attribution")}


def distinctive_text(component, policy) -> str:
    """What makes a component itself: its code, schema, README and connection record, not the licence texts,
    the upstream notice files, the attribution or the tests, which every member of a line shares by construction."""
    try:
        group = constraint_group(component, policy)
    except (ValueError, KeyError, TypeError):
        group = None
    if group is not None:
        # The contract, runner and licences are shared dependencies. Only
        # declared case work distinguishes two groups of that contract.
        return "\n".join(component.text(row["path"]) or "" for row in sorted(group["cases"], key=lambda row: row["job_id"]))
    skip = licence_paths(component.candidate)
    parts = []
    for entry in component.package.files:
        if entry.path in skip or is_test_file(entry.path) or not is_text(entry):
            continue
        parts.append(entry.path + "\n" + (component.text(entry.path) or ""))
    return "\n".join(parts)


def main_module(component) -> "str | None":
    modules = sorted(path for path in component.payloads if path.endswith(".py") and "/" not in path
                     and not path.startswith("test_"))
    return modules[0] if modules else None


def python_assignment(component, name: str):
    """The literal value a module-level assignment of the main module gives ``name``, or None."""
    module = main_module(component)
    if module is None:
        return None
    try:
        for node in ast.parse(component.text(module) or "").body:
            if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == name
                                                    for target in node.targets):
                return ast.literal_eval(node.value)
    except (ValueError, SyntaxError):
        return None
    return None


def job_key(component, policy) -> "str | None":
    """The one job a component does, by its line's declared rule; None when the line declares none.

    The rule is data (the policy's job_key per line): fields of a JSON file (named, or the one top-level file
    with a suffix), fields of a Python module-level dictionary, or the digests of the upstream files other than
    licence texts and notices, optionally with the address of a fact of a named role (without its commit, so
    two revisions of one specification name one job). A rule whose own parts find nothing names no job, or
    uses its ``otherwise`` rule: a generated API component schema copies no upstream file, so its job is its
    specification and the schema's title."""
    try:
        group = constraint_group(component, policy)
        if group is not None:
            from supply_lines.constraint_case_runtime import group_key
            return component.line + "|constraint_group|" + group_key(group)
    except (ValueError, KeyError, TypeError):
        return None  # ManifestCheck refuses the invalid group, never a fallback identity.
    rule = policy["lines"].get(component.line, {}).get("job_key")
    if not rule:
        return None
    try:
        parts = _job_parts(component, rule)
    except (ValueError, SyntaxError, IndexError, TypeError):
        return None
    return None if parts is None else "|".join([component.line] + parts)


def constraint_group(component, policy, *, replay=False):
    rule = policy["lines"].get(component.line, {}).get("constraint_groups")
    if rule is None:
        return None
    present = rule["manifest"] in component.payloads
    expected = component.generator.get("identity") == rule["generator_identity"]
    if not present:
        if expected:
            raise ValueError("constraint_group_manifest_missing")
        return None
    if not expected:
        try:
            marker = json.loads(component.text(rule["manifest"]) or "null")
        except ValueError:
            return None
        if not isinstance(marker, dict) or marker.get("record_type") != rule["record_type"]:
            return None
    from supply_lines.constraint_case_runtime import read_group
    group = read_group(component.payloads, independent=replay, replay_cases=replay)
    if group["record_type"] != rule["record_type"]:
        raise ValueError("constraint_group_version")
    return group


def constraint_jobs(component, policy):
    try:
        group = constraint_group(component, policy)
    except (ValueError, KeyError, TypeError):
        return ()
    return tuple(sorted(row["job_id"] for row in group["cases"])) if group else ()


def require_declared_producer_family(component, producer_family):
    """A case group's declared authoring family cannot be replaced by a CLI default."""
    from supply_lines.constraint_case_runtime import GROUP_FILE, GROUP_TYPE, read_group
    if GROUP_FILE not in component.payloads:
        return
    marker = json.loads(component.text(GROUP_FILE) or "null")
    if not isinstance(marker, dict) or marker.get("record_type") != GROUP_TYPE:
        return
    group = read_group(component.payloads)
    declared = group["producer_family"]
    if (producer_family != declared
            or component.candidate.get("repository", {}).get("producer_family") != declared):
        raise ValueError("constraint_group_producer_family_mismatch")


CONSTRAINT_CASE_JOB_PREFIX = "constraint_case_job:"


def _json_fields(value, fields) -> list:
    parts = []
    for dotted in fields:
        item = value
        for key in dotted.split("."):
            item = item.get(key) if isinstance(item, dict) else None
        parts.append(str(item))
    return parts


def _job_parts(component, rule) -> "list | None":
    parts = []
    if "json_file" in rule:
        parts += _json_fields(json.loads(component.text(rule["json_file"]) or "null"), rule["fields"])
    elif "json_suffix" in rule:
        paths = sorted(path for path in component.payloads if path.endswith(rule["json_suffix"]) and "/" not in path)
        if len(paths) != 1:
            return None
        parts += _json_fields(json.loads(component.text(paths[0]) or "null"), rule["fields"])
    elif "python_assignment" in rule:
        found = python_assignment(component, rule["python_assignment"])
        if not isinstance(found, dict):
            return None
        parts += [str(found.get(field)) for field in rule["fields"]]
    elif rule.get("public_functions"):
        module = main_module(component)
        names = sorted(node.name for node in ast.parse(component.text(module) or "").body
                       if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                       and not node.name.startswith("_")) if module else []
        if not names:
            return None
        parts += names
    elif rule.get("upstream_digests"):
        skip = licence_paths(component.candidate)
        digests = sorted(str(row.get("digest")) for row in component.candidate.get("files", [])
                         if isinstance(row, dict) and row.get("origin") == "upstream_verbatim"
                         and row.get("path") not in skip)
        if not digests:
            return _job_parts(component, rule["otherwise"]) if rule.get("otherwise") else None
        parts += digests
    if rule.get("fact_role"):
        facts = (component.candidate.get("provenance") or {}).get("facts") or []
        urls = sorted(re.sub(r"/[0-9a-f]{40}/", "/", str(fact.get("url", ""))) for fact in facts
                      if isinstance(fact, dict) and fact.get("role") == rule["fact_role"])
        parts += urls
    return parts


def duplicate_findings(components, policy, *, known_digests=None) -> dict:
    """Population-level duplicates of components; see duplicate_findings_from."""
    return duplicate_findings_hashed(((component.identity, component.package.package_digest,
        *comparison_parts(distinctive_text(component, policy)), job_key(component, policy), constraint_jobs(component, policy))
        for component in components), policy, known_digests=known_digests)


def comparison_parts(text: str) -> tuple:
    """What the duplicate pass needs of one distinctive text: the SHA-256 of its normalized form and its
    five-word shingles as sorted distinct 64-bit hashes (tools/global_component_duplicates.shingle_hashes)."""
    from loop_engine.core.library_ingestion.duplicates import normalized
    from tools.global_component_duplicates import shingle_hashes
    import hashlib
    return hashlib.sha256(normalized(text).encode()).hexdigest(), shingle_hashes(text)


def duplicate_findings_from(subjects, policy, *, known_digests=None) -> dict:
    """Identity to duplicate findings, from (identity, package digest, distinctive text, job key) subjects.

    See duplicate_findings_hashed, which this calls with each text's comparison parts."""
    return duplicate_findings_hashed(((identity, digest, *comparison_parts(text), key)
                                      for identity, digest, text, key in subjects), policy,
                                     known_digests=known_digests)


def duplicate_findings_hashed(subjects, policy, *, known_digests=None, scratch=None) -> dict:
    """Identity to duplicate findings, from (identity, package digest, normalized text digest, shingle hashes,
    job key) subjects, the text's parts as ``comparison_parts`` makes them.

    The first of a group in identity order is kept. Exact: the same package digest, a digest already known
    (the served library, earlier admissions), the same normalized distinctive text, or the same job key.
    Near: five-word shingle Jaccard of the distinctive text at or above the policy threshold, confirmed
    exactly with prefix filtering over the shingles' 64-bit hashes (tools/global_component_duplicates.py,
    prefix_pairs_hashed, which finds the pairs prefix_pairs finds over the strings). Until October 5, 2026 the
    pass held every shingle string: a population of 118,106 generated API clients needed about 52 GB, and the
    out-of-memory killer stopped that qualification run in this pass at 35 GB with no record written."""
    from tools.global_component_duplicates import prefix_pairs_hashed
    known_digests = dict(known_digests or {})
    ordered = sorted(subjects, key=lambda subject: subject[0])
    findings = {subject[0]: [] for subject in ordered}
    by_package, by_text, by_job, by_case, documents = {}, {}, {}, {}, {}
    for subject in ordered:
        identity, digest, text_digest, tokens, key = subject[:5]
        cases = subject[5] if len(subject) == 6 else ()
        overlaps = [(case, known_digests.get(CONSTRAINT_CASE_JOB_PREFIX + case) or by_case.get(case)) for case in cases]
        overlaps = [(case, owner) for case, owner in overlaps if owner is not None]
        if overlaps:
            findings[identity].append(("overlapping_constraint_case_jobs", f"{len(overlaps)} jobs; first {overlaps[0][0]} from {overlaps[0][1]}"))
            continue
        if digest in known_digests:
            findings[identity].append(("exact_copy_of_existing", known_digests[digest]))
            continue
        if digest in by_package:
            findings[identity].append(("exact_package_copy", by_package[digest]))
            continue
        if text_digest in by_text:
            findings[identity].append(("exact_content_copy", by_text[text_digest]))
            continue
        if key is not None and key in by_job:
            findings[identity].append(("same_job_as", by_job[key]))
            continue
        by_package[digest], by_text[text_digest] = identity, identity
        if key is not None:
            by_job[key] = identity
        by_case.update((case, identity) for case in cases)
        documents[identity] = tokens
    numerator, denominator = policy["near_duplicate_threshold"].split("/")
    threshold = Fraction(int(numerator), int(denominator))
    for left, right, intersection, union in prefix_pairs_hashed(
            {key: value for key, value in documents.items() if len(value)}, threshold, scratch=scratch):
        first, second = sorted((left, right))
        if not findings[second]:
            findings[second].append(("near_copy", f"{first} at {intersection / union:.3f}"))
    return findings


class DuplicatesCheck:
    check_id, kind, dimension = "duplicates", "duplicates", PUBLICATION

    def run(self, component, context) -> CheckResult:
        if component.identity not in context.duplicates:
            return _result(self, [("duplicates_not_decided", "the population-level duplicate pass did not run")])
        return _result(self, context.duplicates[component.identity])


class SandboxCheck:
    check_id, kind, dimension = "sandbox", "format", IMPLEMENTATION

    def run(self, component, context) -> CheckResult:
        line = context.policy["lines"].get(component.line, {})
        modules, tests = sandbox_module.python_modules(component)
        if line.get("shape") == "configuration" and not modules and not tests:
            return _not_applicable(self, "configuration component: nothing to run; its formats are checked by schema")
        if context.sandbox_settings is None or context.work_root is None:
            return _result(self, [("sandbox_not_configured", "no sandbox settings were supplied")])
        available, reason = context.sandbox_settings.available()
        if not available:
            return _result(self, [("sandbox_unavailable", reason)])
        untested = sorted(entry.path for entry in component.package.files
                          if PurePosixPath(entry.path).suffix.lower() in context.policy["code_suffixes"]
                          and PurePosixPath(entry.path).suffix.lower() not in context.policy["tested_code_suffixes"])
        if untested:
            return _result(self, [("code_language_not_tested", ", ".join(untested)[:240])])
        run = sandbox_module.run_component(component, context.sandbox_settings, context.work_root)
        findings = []
        if not run["ran"]:
            code = "sandbox_timed_out" if run.get("timed_out") else "sandbox_run_failed"
            findings.append((code, run.get("reason", "") + " " + run.get("stderr_tail", "")[-200:]))
            return CheckResult(self.check_id, VERSION, self.kind, self.dimension, REFUSED, tuple(findings),
                               (json.dumps({key: run.get(key) for key in ("wall_seconds", "timed_out", "exit")}),))
        for row in run["imports"]:
            if not row["ok"]:
                findings.append(("entry_point_import_failed", f"{row['module']}: {row['tail'][-160:]}"))
        tests_row = run["tests"]
        if tests_row is None:
            findings.append(("no_tests_ran", "the package declares no test module"))
        else:
            executed = tests_row["ran"] - tests_row["skipped"]
            if tests_row["timed_out"]:
                findings.append(("tests_timed_out", f"the tests ran past {context.sandbox_settings.limits.test_seconds} s"))
            elif not tests_row["passed"]:
                findings.append(("tests_failed", tests_row["tail"][-240:]))
            elif executed < 1:
                findings.append(("no_test_executed", f"{tests_row['ran']} ran, {tests_row['skipped']} skipped"))
        summary = {"interpreter": run.get("interpreter"), "wall_seconds": run["wall_seconds"],
                   "tests": None if tests_row is None else {key: tests_row[key] for key in
                                                            ("ran", "skipped", "failures", "errors", "passed")}}
        return _result(self, findings, (json.dumps(summary, sort_keys=True),))


class _Mutator(ast.NodeTransformer):
    """Replace the body of every public function and of every public method of public classes."""

    def __init__(self, replacement: str) -> None:
        self.replacement = replacement
        self.mutated = 0

    def _replace(self, node):
        node.body = [ast.Expr(node.body[0].value)] if (node.body and isinstance(node.body[0], ast.Expr)
                                                       and isinstance(getattr(node.body[0], "value", None),
                                                                      ast.Constant)) else []
        node.body += ast.parse(self.replacement).body
        self.mutated += 1
        return node

    def visit_Module(self, node):
        for index, item in enumerate(node.body):
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and not item.name.startswith("_"):
                node.body[index] = self._replace(item)
            elif isinstance(item, ast.ClassDef) and not item.name.startswith("_"):
                for position, member in enumerate(item.body):
                    if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)) and not member.name.startswith("_"):
                        item.body[position] = self._replace(member)
        return node


def mutant(component, policy) -> "tuple | None":
    """(mutated component, functions replaced) with every public implementation raising; None without code."""
    modules, tests = sandbox_module.python_modules(component)
    if not modules or not tests:
        return None
    payloads, replaced = dict(component.payloads), 0
    for module in modules:
        path = module + ".py"
        tree = ast.parse(component.text(path) or "")
        mutator = _Mutator(policy["mutation"]["replacement"])
        mutator.visit(tree)
        if mutator.mutated:
            payloads[path] = (ast.unparse(ast.fix_missing_locations(tree)) + "\n").encode()
            replaced += mutator.mutated
    if not replaced:
        return None
    return component.replaced(payloads=payloads), replaced


class MutationCheck:
    """The package's own tests must fail when its implementation is replaced by one that raises."""

    check_id, kind, dimension = "mutation", "format", IMPLEMENTATION

    def run(self, component, context) -> CheckResult:
        line = context.policy["lines"].get(component.line, {})
        if line.get("shape") not in context.policy["mutation"]["shapes"]:
            return _not_applicable(self, "no executable implementation to mutate")
        if context.sandbox_settings is None or context.work_root is None:
            return _result(self, [("sandbox_not_configured", "no sandbox settings were supplied")])
        built = mutant(component, context.policy)
        if built is None:
            return _result(self, [("nothing_to_mutate", "no public function or method in a root module with tests")])
        mutated, replaced = built
        run = sandbox_module.run_component(mutated, context.sandbox_settings, context.work_root)
        tests_row = run.get("tests")
        if run.get("timed_out") or (tests_row is not None and tests_row["timed_out"]):
            return _result(self, [("mutation_timed_out", "the mutant's tests did not finish within the limits")])
        if not run["ran"] or tests_row is None:
            return _result(self, [("mutation_run_failed", run.get("reason", "") + " " + run.get("stderr_tail", "")[-160:])])
        if tests_row["passed"]:
            return _result(self, [("tests_accept_a_broken_implementation",
                                   f"{replaced} public implementations replaced; the tests still pass")])
        return _result(self, [], (json.dumps({"replaced": replaced, "mutant_tests": {
            key: tests_row[key] for key in ("ran", "failures", "errors", "skipped")}}, sort_keys=True),))


CHECKS = (ManifestCheck(), LicenceProvenanceCheck(), ParseCheck(), SchemaCheck(), EffectsCheck(), SafetyCheck(),
          SecretsCheck(), DuplicatesCheck(), SandboxCheck(), MutationCheck())
CHECK_IDS = tuple(check.check_id for check in CHECKS)
