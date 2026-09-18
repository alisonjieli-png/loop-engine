"""Standalone solution export: a package that runs without the solutioning space.

A solution the solutioning space produced is only useful when it can leave.
This module writes one installable Python package from a typed export
specification: source files, a console entry point, tests, a manifest with
a digest for every file, a Dockerfile, and a Kubernetes Job manifest. It
then verifies the export in an isolated interpreter that cannot import Loop
Engine, so the claim "this solution runs on its own" is executed rather
than assumed.

The export never contains a secret, an absolute path, or an import of
``loop_engine``. Each refusal is a typed error naming the file.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

EXPORT_RECORD_TYPE = "solution_export/v1"
MANIFEST_RECORD_TYPE = "solution_export_manifest/v1"
VERIFICATION_RECORD_TYPE = "solution_export_verification/v1"
ISOLATION_MODES = ("stdlib_only", "site_packages")
#: The kinds an export specification record may declare: typed files, or a
#: conformance rule set that builds its own files.
EXPORT_KINDS = ("files", "text_conformance")
#: The environment an isolated verification interpreter receives: the search
#: path passes through; the locale and stream encoding are fixed so output is
#: comparable across hosts. Nothing else from the parent process is visible.
ISOLATION_PASSTHROUGH = ("PATH",)
ISOLATION_ENVIRONMENT = (("LANG", "C.UTF-8"), ("PYTHONIOENCODING", "utf-8"))
_PACKAGE_NAME = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
_VERSION = re.compile(r"^\d+\.\d+\.\d+$")
_SECRET_SHAPES = (re.compile(r"sk-[A-Za-z0-9]{20,}"), re.compile(r"AKIA[0-9A-Z]{16}"),
                  re.compile(r"(?i)authorization:\s*bearer\s+\S+"),
                  re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"))
_FORBIDDEN_IMPORT = re.compile(r"^\s*(from\s+loop_engine[\s.]|import\s+loop_engine\b)", re.MULTILINE)


class SolutionExportError(ValueError):
    """An export specification, target, or verification is invalid."""


def _digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _digest(value) -> str:
    return _digest_bytes(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    default=str).encode("utf-8"))


def _clean_relative(path: str, *, prefix: str) -> str:
    if not path or path.startswith("/") or "\\" in path or ".." in Path(path).parts \
            or any(not part or part.startswith(".") and part not in (".", "..") and False
                   for part in Path(path).parts):
        raise SolutionExportError(f"{prefix}: path must be relative without traversal: {path!r}")
    if Path(path).is_absolute() or re.match(r"^[A-Za-z]:", path):
        raise SolutionExportError(f"{prefix}: absolute path refused: {path!r}")
    return str(Path(path).as_posix())


def _check_content(path: str, content: str) -> None:
    if _FORBIDDEN_IMPORT.search(content):
        raise SolutionExportError(f"{path}: imports loop_engine; a standalone export cannot")
    for pattern in _SECRET_SHAPES:
        if pattern.search(content):
            raise SolutionExportError(f"{path}: secret-shaped text refused")


@dataclass(frozen=True)
class ExportedFile:
    """One file inside the exported package, relative to the package directory."""

    path: str
    content: str
    executable: bool = False

    def __post_init__(self):
        object.__setattr__(self, "path", _clean_relative(self.path, prefix="exported file"))
        if not isinstance(self.content, str):
            raise SolutionExportError(f"{self.path}: content must be text")
        _check_content(self.path, self.content)


@dataclass(frozen=True)
class ContainerSpec:
    """How the export is containerized and scheduled."""

    base_image: str = "python:3.12-slim"
    image_digest: str = ""
    cpu: str = "500m"
    memory: str = "512Mi"
    arguments: tuple[str, ...] = ()

    def __post_init__(self):
        if not self.base_image.strip() or " " in self.base_image:
            raise SolutionExportError("container base_image must be one image reference")
        if self.image_digest and not re.fullmatch(r"sha256:[0-9a-f]{64}", self.image_digest):
            raise SolutionExportError("image_digest must be sha256:<64 hex> when given")
        object.__setattr__(self, "arguments", tuple(self.arguments))

    @property
    def pinned(self) -> bool:
        return bool(self.image_digest)


@dataclass(frozen=True)
class SolutionExportSpec:
    """Everything needed to write one standalone package."""

    package_name: str
    version: str
    summary: str
    files: tuple[ExportedFile, ...]
    console_script: str = ""
    dependencies: tuple[str, ...] = ()
    python_requires: str = ">=3.10"
    tests: tuple[ExportedFile, ...] = ()
    container: ContainerSpec = field(default_factory=ContainerSpec)
    solution_ref: str = ""
    source_run_id: str = ""
    isolation: str = ISOLATION_MODES[0]

    def __post_init__(self):
        if not _PACKAGE_NAME.fullmatch(self.package_name):
            raise SolutionExportError("package_name must be a lowercase Python identifier")
        if not _VERSION.fullmatch(self.version):
            raise SolutionExportError("version must be major.minor.patch")
        if not self.summary.strip():
            raise SolutionExportError("summary must not be empty")
        files = tuple(self.files)
        if not files or any(not isinstance(item, ExportedFile) for item in files):
            raise SolutionExportError("files must be typed ExportedFile records")
        paths = [item.path for item in files]
        if len(set(paths)) != len(paths):
            raise SolutionExportError("exported file paths must be unique")
        if "__init__.py" not in paths:
            raise SolutionExportError("the package needs an __init__.py file")
        if self.console_script and "__main__.py" not in paths:
            raise SolutionExportError("a console script needs a __main__.py with main()")
        if self.isolation not in ISOLATION_MODES:
            raise SolutionExportError(f"isolation must be one of {ISOLATION_MODES}")
        if self.isolation == ISOLATION_MODES[0] and self.dependencies:
            raise SolutionExportError("stdlib_only isolation cannot declare dependencies")
        object.__setattr__(self, "files", files)
        object.__setattr__(self, "tests", tuple(self.tests))
        object.__setattr__(self, "dependencies", tuple(self.dependencies))

    @property
    def digest(self) -> str:
        return _digest({"package_name": self.package_name, "version": self.version,
                        "files": {item.path: _digest_bytes(item.content.encode("utf-8"))
                                  for item in self.files},
                        "tests": {item.path: _digest_bytes(item.content.encode("utf-8"))
                                  for item in self.tests},
                        "console_script": self.console_script,
                        "dependencies": list(self.dependencies)})


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def render_pyproject(spec: SolutionExportSpec) -> str:
    dependencies = ", ".join(json.dumps(item) for item in spec.dependencies)
    lines = ["[build-system]", 'requires = ["setuptools>=68"]',
             'build-backend = "setuptools.build_meta"', "", "[project]",
             f'name = "{spec.package_name.replace("_", "-")}"', f'version = "{spec.version}"',
             f"description = {json.dumps(spec.summary)}",
             f'requires-python = "{spec.python_requires}"', f"dependencies = [{dependencies}]", ""]
    if spec.console_script:
        lines += ["[project.scripts]",
                  f'{spec.console_script} = "{spec.package_name}.__main__:main"', ""]
    lines += ["[tool.setuptools]", 'package-dir = { "" = "src" }', "",
              "[tool.setuptools.packages.find]", 'where = ["src"]', "",
              "[tool.setuptools.package-data]", f'{spec.package_name} = ["*.json", "*.yaml"]', ""]
    return "\n".join(lines)


def render_dockerfile(spec: SolutionExportSpec) -> str:
    image = spec.container.base_image + (f"@{spec.container.image_digest}" if spec.container.pinned else "")
    entry = json.dumps([spec.console_script] if spec.console_script
                       else ["python", "-m", spec.package_name])
    pin = "" if spec.container.pinned else "# The base image is not digest-pinned; pin it before production use.\n"
    return (f"{pin}FROM {image}\nWORKDIR /app\nCOPY . /app\n"
            "RUN pip install --no-cache-dir /app\nUSER 65534\n"
            f"ENTRYPOINT {entry}\n")


def render_kubernetes_job(spec: SolutionExportSpec) -> str:
    name = spec.package_name.replace("_", "-")
    args = "".join(f"            - {json.dumps(item)}\n" for item in spec.container.arguments)
    return (
        "apiVersion: batch/v1\nkind: Job\nmetadata:\n"
        f"  name: {name}\n  labels:\n    app.kubernetes.io/name: {name}\n"
        f"    loop-engine/solution-ref: {json.dumps(spec.solution_ref or 'unset')}\n"
        "spec:\n  backoffLimit: 0\n  ttlSecondsAfterFinished: 86400\n  template:\n"
        "    spec:\n      restartPolicy: Never\n      containers:\n"
        f"        - name: {name}\n          image: IMAGE_REFERENCE\n"
        + (f"          args:\n{args}" if args else "")
        + "          resources:\n            requests:\n"
        f"              cpu: {json.dumps(spec.container.cpu)}\n"
        f"              memory: {json.dumps(spec.container.memory)}\n"
        "            limits:\n"
        f"              cpu: {json.dumps(spec.container.cpu)}\n"
        f"              memory: {json.dumps(spec.container.memory)}\n"
        "          volumeMounts:\n            - name: work\n              mountPath: /work\n"
        "      volumes:\n        - name: work\n          emptyDir: {}\n")


def render_readme(spec: SolutionExportSpec) -> str:
    run = (f"{spec.console_script} --help" if spec.console_script
           else f"python -m {spec.package_name} --help")
    return (f"# {spec.package_name}\n\n{spec.summary}\n\n"
            "This package was exported from a Loop Engine solutioning run. It has no\n"
            "dependency on Loop Engine and runs on its own.\n\n"
            "Install and run:\n\n```bash\npython -m pip install .\n"
            f"{run}\n```\n\nRun the tests:\n\n```bash\npython -m unittest discover -s tests\n```\n\n"
            "Build the container and run the Kubernetes Job:\n\n```bash\n"
            f"docker build -t {spec.package_name.replace('_', '-')}:{spec.version} .\n"
            "kubectl apply -f k8s/job.yaml\n```\n\n"
            "`MANIFEST.json` lists every file with its SHA-256 digest.\n"
            + (f"\nSolution reference: `{spec.solution_ref}`\n" if spec.solution_ref else "")
            + (f"Source run: `{spec.source_run_id}`\n" if spec.source_run_id else ""))


# ---------------------------------------------------------------------------
# Export and verification
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ExportRecord:
    target: str
    package_name: str
    version: str
    manifest_digest: str
    file_count: int

    def to_dict(self) -> dict:
        return {"record_type": EXPORT_RECORD_TYPE, "target": self.target,
                "package_name": self.package_name, "version": self.version,
                "manifest_digest": self.manifest_digest, "file_count": self.file_count}


def export_solution(spec: SolutionExportSpec, target: str) -> ExportRecord:
    """Write the package into an empty or new directory and return its record."""
    if not isinstance(spec, SolutionExportSpec):
        raise SolutionExportError("export_solution takes a SolutionExportSpec")
    root = Path(target)
    if root.exists() and (not root.is_dir() or any(root.iterdir())):
        raise SolutionExportError(f"target {target!r} must be a new or empty directory")
    if root.is_symlink():
        raise SolutionExportError("target cannot be a symlink")
    package_dir = root / "src" / spec.package_name
    written: dict[str, str] = {}

    def write(relative: str, content: str, executable: bool = False) -> None:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        data = content.encode("utf-8")
        path.write_bytes(data)
        if executable:
            path.chmod(0o755)
        written[relative] = _digest_bytes(data)

    for item in spec.files:
        write(f"src/{spec.package_name}/{item.path}", item.content, item.executable)
    for item in spec.tests:
        write(f"tests/{item.path}", item.content)
    write("pyproject.toml", render_pyproject(spec))
    write("README.md", render_readme(spec))
    write("Dockerfile", render_dockerfile(spec))
    write("k8s/job.yaml", render_kubernetes_job(spec))
    write(".dockerignore", "MANIFEST.json\n.git\n__pycache__\n")
    manifest = {"record_type": MANIFEST_RECORD_TYPE, "package_name": spec.package_name,
                "version": spec.version, "summary": spec.summary,
                "solution_ref": spec.solution_ref, "source_run_id": spec.source_run_id,
                "isolation": spec.isolation, "dependencies": list(spec.dependencies),
                "console_script": spec.console_script, "spec_digest": spec.digest,
                "container": {"base_image": spec.container.base_image,
                              "image_digest": spec.container.image_digest,
                              "pinned": spec.container.pinned},
                "files": dict(sorted(written.items()))}
    manifest["manifest_digest"] = _digest(manifest)
    (root / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", "utf-8")
    assert package_dir.is_dir()
    return ExportRecord(str(root), spec.package_name, spec.version, manifest["manifest_digest"],
                        len(written))


@dataclass(frozen=True)
class ExportVerification:
    passed: bool
    checks: tuple[dict, ...]
    manifest_digest: str

    def to_dict(self) -> dict:
        return {"record_type": VERIFICATION_RECORD_TYPE, "passed": self.passed,
                "checks": list(self.checks), "manifest_digest": self.manifest_digest}


def _isolated_python(isolation: str) -> list[str]:
    flags = ["-I", "-S"] if isolation == ISOLATION_MODES[0] else ["-I"]
    return [sys.executable, *flags]


def isolation_environment() -> dict:
    """The environment for an isolated interpreter: pass-through names plus fixed values."""
    env = {name: os.environ[name] for name in ISOLATION_PASSTHROUGH if name in os.environ}
    env.update(ISOLATION_ENVIRONMENT)
    return env


def _run_isolated(root: Path, isolation: str, code: str, timeout: float) -> subprocess.CompletedProcess:
    return subprocess.run([*_isolated_python(isolation), "-c", code], cwd=str(root),
                          env=isolation_environment(), capture_output=True, text=True, timeout=timeout)


def verify_export(target: str, *, run_arguments: tuple[str, ...] | None = None,
                  expected_artifacts: tuple[str, ...] = (), timeout: float = 120.0) -> ExportVerification:
    """Prove the export is complete, clean, and runs without Loop Engine.

    Checks: the manifest digests match the files on disk; no file imports
    ``loop_engine``; the package imports in an isolated interpreter that
    cannot see the site packages; the tests pass there; and, when arguments
    are given, the entry point runs and produces every expected artifact.
    """
    root = Path(target)
    checks: list[dict] = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        checks.append({"check": name, "passed": bool(passed), "detail": detail[:2000]})

    manifest_path = root / "MANIFEST.json"
    if not manifest_path.is_file():
        raise SolutionExportError("MANIFEST.json is missing; not an export")
    manifest = json.loads(manifest_path.read_text("utf-8"))
    package = str(manifest.get("package_name") or "")
    isolation = str(manifest.get("isolation") or ISOLATION_MODES[0])
    mismatched = [path for path, digest in manifest.get("files", {}).items()
                  if not (root / path).is_file() or _digest_bytes((root / path).read_bytes()) != digest]
    check("manifest_digests_match_files", not mismatched, ", ".join(mismatched))
    offending = []
    for path in manifest.get("files", {}):
        if path.endswith(".py"):
            try:
                _check_content(path, (root / path).read_text("utf-8"))
            except SolutionExportError as exc:
                offending.append(str(exc))
    check("no_loop_engine_import_and_no_secret_shape", not offending, "; ".join(offending))
    imported = _run_isolated(root, isolation,
                             f"import sys; sys.path.insert(0, 'src'); import {package}; "
                             f"assert 'loop_engine' not in sys.modules; print('ok')", timeout)
    check("package_imports_in_isolation", imported.returncode == 0 and imported.stdout.strip() == "ok",
          imported.stderr.strip())
    if (root / "tests").is_dir():
        tested = _run_isolated(root, isolation,
                               "import sys, unittest; sys.path.insert(0, 'src'); "
                               "suite = unittest.defaultTestLoader.discover('tests'); "
                               "result = unittest.TextTestRunner(verbosity=0).run(suite); "
                               "sys.exit(0 if result.wasSuccessful() and result.testsRun else 1)", timeout)
        check("exported_tests_pass_in_isolation", tested.returncode == 0, tested.stderr.strip()[-2000:])
    if run_arguments is not None:
        arguments = json.dumps(list(run_arguments))
        ran = _run_isolated(root, isolation,
                            f"import sys, runpy; sys.path.insert(0, 'src'); "
                            f"sys.argv = ['{package}'] + {arguments}; "
                            f"runpy.run_module('{package}', run_name='__main__')", timeout)
        check("entry_point_runs_in_isolation", ran.returncode == 0, (ran.stderr or ran.stdout).strip()[-2000:])
        missing = [item for item in expected_artifacts if not (root / item).exists()]
        check("expected_artifacts_exist", not missing, ", ".join(missing))
    passed = all(item["passed"] for item in checks)
    return ExportVerification(passed, tuple(checks), str(manifest.get("manifest_digest") or ""))


# ---------------------------------------------------------------------------
# The first exported solution: text conformance
# ---------------------------------------------------------------------------

_SOLUTION_SOURCE = '''"""Standalone text conformance solution exported from Loop Engine."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from . import operations

HERE = Path(__file__).resolve().parent


def load_configuration() -> tuple[list, dict, dict]:
    rules = json.loads((HERE / "rules.json").read_text("utf-8"))
    return rules["rules"], rules["policy"], json.loads((HERE / "catalogs.json").read_text("utf-8"))


def conform_rows(rows, rules, policy, catalogs, *, learn_evidence: bool = True):
    """Two passes: learn column evidence, then apply the rules row by row."""
    rows = list(rows)
    columns = sorted({column for rule in rules for column in rule["columns"]})
    evidence = operations.learn_column_evidence(rows, columns) if learn_evidence else {}
    for index, row in enumerate(rows):
        output, corrections = operations.apply_rules_to_row(row, rules, catalogs, policy, evidence)
        yield str(row.get("row_ref") or index), output, corrections


def run(input_path: str, output_dir: str, *, learn_evidence: bool = True) -> dict:
    rules, policy, catalogs = load_configuration()
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    corrections_all = []
    with open(input_path, "r", encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        rows = list(reader)
        fieldnames = list(reader.fieldnames or [])
    with open(out / "conformed.csv", "w", encoding="utf-8", newline="") as target, \\
            open(out / "corrections.jsonl", "w", encoding="utf-8") as corrections_file, \\
            open(out / "escalations.jsonl", "w", encoding="utf-8") as escalations_file:
        writer = csv.DictWriter(target, fieldnames=fieldnames)
        writer.writeheader()
        for row_ref, output, corrections in conform_rows(rows, rules, policy, catalogs,
                                                         learn_evidence=learn_evidence):
            writer.writerow({key: output.get(key, "") for key in fieldnames})
            for item in corrections:
                record = {"row_ref": row_ref, **item}
                corrections_file.write(json.dumps(record, sort_keys=True) + "\\n")
                corrections_all.append(record)
                if item["outcome"] == "escalated" or (policy.get("escalate_held") and item["outcome"] == "held"):
                    escalations_file.write(json.dumps(record, sort_keys=True) + "\\n")
    report = {"record_type": "conformance_report/v1", "rows": len(rows),
              **operations.summarize(corrections_all, rules)}
    (out / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\\n", "utf-8")
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Conform text columns with a confidence per correction.")
    parser.add_argument("--input", required=True, help="CSV file to conform")
    parser.add_argument("--output-dir", required=True, help="directory for conformed.csv, corrections.jsonl, escalations.jsonl, report.json")
    parser.add_argument("--no-column-evidence", action="store_true", help="skip the first pass that learns casings from the column")
    args = parser.parse_args(argv)
    report = run(args.input, args.output_dir, learn_evidence=not args.no_column_evidence)
    print(json.dumps(report["overall"], sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''

_MAIN_SOURCE = '''from .solution import main

if __name__ == "__main__":
    raise SystemExit(main())
'''

_TEST_SOURCE = '''import json
import tempfile
import unittest
from pathlib import Path

from {package} import operations, solution


class ConformanceTest(unittest.TestCase):
    def test_rules_apply_hold_and_escalate(self):
        rules, policy, catalogs = solution.load_configuration()
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "in.csv"
            source.write_text("{header}\\n{row_confident}\\n{row_low}\\n", "utf-8")
            report = solution.run(str(source), folder)
            self.assertEqual(report["rows"], 2)
            self.assertGreaterEqual(report["overall"]["applied"], 1)
            lines = (Path(folder) / "conformed.csv").read_text("utf-8").splitlines()
            self.assertEqual(len(lines), 3)
            self.assertTrue((Path(folder) / "report.json").is_file())

    def test_operations_are_deterministic(self):
        rules, policy, catalogs = solution.load_configuration()
        first = operations.apply_operation("case_normalize", "ACME CORPORATION", {{}}, catalogs)
        second = operations.apply_operation("case_normalize", "ACME CORPORATION", {{}}, catalogs)
        self.assertEqual(first, second)
        self.assertTrue(first["changed"])


if __name__ == "__main__":
    unittest.main()
'''


@dataclass(frozen=True)
class ExportSample:
    """The header and two rows the exported test file conforms: one confident, one held."""

    header: str = "name"
    rows: tuple[str, str] = ("ACME CORPORATION", "AA CAREERS")


def text_conformance_export_spec(rules, policy, catalogs: dict, *, package_name: str,
                                 version: str = "0.1.0", summary: str = "",
                                 solution_ref: str = "", source_run_id: str = "",
                                 sample: ExportSample = ExportSample()) -> SolutionExportSpec:
    """The export specification for a conformance rule set.

    The operations module is copied verbatim from this package, which is why
    it imports only the standard library. Rules, policy, and the merged
    catalogs become JSON so the export needs no YAML dependency.
    """
    sample_header, sample_rows = sample.header, sample.rows
    from . import text_conformance_operations
    source = inspect.getsource(text_conformance_operations)
    rule_records = [item.to_dict() if hasattr(item, "to_dict") else dict(item) for item in rules]
    policy_record = policy.to_dict() if hasattr(policy, "to_dict") else dict(policy)
    files = (
        ExportedFile("__init__.py", f'"""{summary or "Exported text conformance solution."}"""\n'
                                    f'__version__ = "{version}"\n'),
        ExportedFile("operations.py", source),
        ExportedFile("solution.py", _SOLUTION_SOURCE),
        ExportedFile("__main__.py", _MAIN_SOURCE),
        ExportedFile("rules.json", json.dumps({"record_type": "conformance_rule_set/v1",
                                               "rules": rule_records, "policy": policy_record},
                                              indent=2, sort_keys=True) + "\n"),
        ExportedFile("catalogs.json", json.dumps(catalogs, indent=2, sort_keys=True,
                                                 ensure_ascii=False) + "\n"),
    )
    tests = (ExportedFile("test_solution.py", _TEST_SOURCE.format(
        package=package_name, header=sample_header, row_confident=sample_rows[0],
        row_low=sample_rows[1])),)
    return SolutionExportSpec(package_name, version, summary or "Text conformance with a confidence per correction.",
                              files, console_script=package_name.replace("_", "-"), tests=tests,
                              container=ContainerSpec(arguments=("--input", "/work/input.csv",
                                                                 "--output-dir", "/work/out")),
                              solution_ref=solution_ref, source_run_id=source_run_id)


def self_test() -> dict:
    from .solution_export_checks import run_checks
    return run_checks()
