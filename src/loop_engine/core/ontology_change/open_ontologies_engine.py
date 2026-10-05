"""Engine adapter for Open Ontologies v2.0.1, pinned by its release asset digest and run in a sandbox.

```text
OpenOntologiesEngine (engine kind sandboxed_binary_adapter, engine open_ontologies_cli)
├── upstream: github.com/fabio-rovai/open-ontologies, release v2.0.1, commit d1187190, MIT
├── artifact: open-ontologies-x86_64-unknown-linux-gnu, SHA-256 7a54594a... as GitHub publishes it;
│   checked before every run, never downloaded or re-hosted here (the host names the file)
├── one run: write both graphs as canonical N-Triples into a disposable folder, then one `batch` of
│   load, reason --profile P --certificate, save --format ntriples, for the base and the proposal
├── sandbox: bubblewrap with every namespace unshared (no network), the system read-only, the binary
│   bound read-only, the disposable folder the only writable path and its --data-dir, a cleared
│   environment, --no-connect, an address-space limit, a time limit and an output ceiling
└── answer: both closures read back through the N-Triples reader, and the derivation of every
    inferred triple read from the run's derivations.tsv
```

Its own apply, rollback, lock and monitor are never called: apply belongs to
the store of this component. Blank nodes are refused at eligibility, because
the binary relabels them and a set difference over relabelled blank nodes is
meaningless. ``run_lean_checker`` runs the release's ``oo-cert`` the same way,
for the conformance kit's cross-check of any engine's traces.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import resource
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from .contract import RULE_TABLES, EngineDeclaration, EngineFailure, EngineOutcome, PlanningInput
from .rdf_terms import RdfSyntaxError, canonical_ntriples, parse_ntriples, parse_term

RELEASE = "v2.0.1"
COMMIT = "d118719043905132d314611dcee9f0cac5f87868"
REPOSITORY = "fabio-rovai/open-ontologies"
ASSET = "open-ontologies-x86_64-unknown-linux-gnu"
BINARY_SHA256 = "7a54594aad74c572c993fb09f1d0ea3c661f2348592dde542bb8f2fdfeba3572"
CHECKER_ASSET = "oo-cert-x86_64-unknown-linux-gnu"
CHECKER_SHA256 = "68223b4db193783a52bd2810a66ce2ad3a3780f963a5ef84753564c051e3e532"
BWRAP = "/usr/bin/bwrap"
DEFAULT_TIMEOUT_SECONDS = 120.0
#: Address-space limits (RLIMIT_AS), not resident memory. Measured on October 5, 2026 on a 16-core machine: the
#: release's oo-cert aborts at 2 GiB ("failed to create thread") and runs from 4 GiB; the engine binary ran the
#: whole kit at 2 GiB.
DEFAULT_MEMORY_BYTES = 4 * 1024 ** 3
CHECKER_MEMORY_BYTES = 8 * 1024 ** 3
MAXIMUM_OUTPUT_BYTES = 64 * 1024 * 1024
_SANDBOX_BINARY = "/opt/oo/program"
_DIGESTS: dict = {}


def file_sha256(path: str) -> str:
    """The SHA-256 of a file, remembered by path, size and modification time."""
    status = os.stat(path)
    key = (path, status.st_size, status.st_mtime_ns)
    if key not in _DIGESTS:
        digest = hashlib.sha256()
        with open(path, "rb") as handle:
            for block in iter(lambda: handle.read(1 << 20), b""):
                digest.update(block)
        _DIGESTS[key] = digest.hexdigest()
    return _DIGESTS[key]


def pinned_file_problem(path, expected_sha256: str) -> str:
    """Why a configured binary cannot be used, or the empty text when it can."""
    if platform.system() != "Linux" or platform.machine() not in ("x86_64", "AMD64"):
        return f"the pinned asset is for Linux x86_64, not {platform.system()} {platform.machine()}"
    if not os.path.isfile(BWRAP):
        return f"{BWRAP} is not installed, and the binary never runs without its sandbox"
    if not path or type(path) is not str or not os.path.isabs(path):
        return "no absolute binary path is configured (installation setting binary_path)"
    if not os.path.isfile(path):
        return f"no file at {path}"
    found = file_sha256(path)
    if found != expected_sha256:
        return f"the file's SHA-256 is {found}, not the pinned {expected_sha256}"
    return ""


def _limit_memory(limit: int):
    def apply():
        resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
    return apply


def sandboxed_run(binary: str, arguments, work: str, *, timeout: float, memory: int) -> tuple:
    """(exit code, stdout bytes, stderr tail) of the binary inside bubblewrap; the work folder is /work."""
    argv = [BWRAP, "--ro-bind", "/usr", "/usr", "--ro-bind-try", "/lib", "/lib", "--ro-bind-try", "/lib64",
            "/lib64", "--ro-bind-try", "/etc/ld.so.cache", "/etc/ld.so.cache", "--ro-bind", binary,
            _SANDBOX_BINARY, "--dev", "/dev", "--proc", "/proc", "--tmpfs", "/tmp", "--bind", work, "/work",
            "--unshare-all", "--die-with-parent", "--new-session", "--clearenv", "--setenv", "HOME", "/work/home",
            "--setenv", "PATH", "/usr/bin:/bin", "--setenv", "LANG", "C.UTF-8", "--setenv", "MALLOC_ARENA_MAX",
            "2", "--chdir", "/work", "--",
            _SANDBOX_BINARY, *arguments]
    try:
        finished = subprocess.run(argv, capture_output=True, timeout=timeout, check=False,
                                  env={"PATH": "/usr/bin:/bin"}, stdin=subprocess.DEVNULL,
                                  preexec_fn=_limit_memory(memory))
    except subprocess.TimeoutExpired:
        raise EngineFailure("engine_reported_failure", f"the run passed its {timeout} second limit") from None
    except OSError as error:
        raise EngineFailure("engine_unavailable", f"the sandbox could not start: {type(error).__name__}") from None
    if len(finished.stdout) > MAXIMUM_OUTPUT_BYTES:
        raise EngineFailure("engine_reported_failure", "the run printed more than the output ceiling")
    return finished.returncode, finished.stdout, finished.stderr.decode("utf-8", "replace")[-400:]


def _json_values(text: str) -> list:
    decoder, index, values = json.JSONDecoder(), 0, []
    while index < len(text):
        while index < len(text) and text[index].isspace():
            index += 1
        if index >= len(text):
            break
        value, index = decoder.raw_decode(text, index)
        values.append(value)
    return values


def _batch(profile: str) -> str:
    lines = []
    for graph in ("base", "proposed"):
        lines += [f"load /work/{graph}.nt", f"reason --profile {profile} --certificate /work/cert-{graph}",
                  f"save /work/{graph}-closure.nt --format ntriples", "clear"]
    return "\n".join(lines[:-1]) + "\n"


def _canonical(fields) -> tuple:
    return tuple(parse_term(term, position) for term, position in zip(fields, ("subject", "predicate", "object")))


def _derivations(path: Path, allowed: tuple) -> dict:
    """Conclusion -> (rule, premises) from one derivations.tsv, every term made canonical."""
    derivations = {}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        fields = line.split("\t")
        if not line:
            continue
        if len(fields) < 7 or (len(fields) - 4) % 3 or fields[0] not in allowed:
            raise EngineFailure("engine_reported_failure", f"{path.name} line {number} is not a known step")
        premises = tuple(_canonical(fields[index:index + 3]) for index in range(4, len(fields), 3))
        derivations[_canonical(fields[1:4])] = (fields[0], premises)
    return derivations


class OpenOntologiesEngine:
    """The engine adapter of the ontology_change_planning slot for the pinned Open Ontologies binary."""

    def __init__(self, declaration: EngineDeclaration, settings=None):
        self.declaration = declaration
        self.settings = dict(settings or {})

    def availability(self) -> tuple:
        problem = pinned_file_problem(self.settings.get("binary_path"), BINARY_SHA256)
        return (not problem), (problem or f"pinned {ASSET} {RELEASE} found and its SHA-256 matches")

    def plan(self, planning_input: PlanningInput) -> EngineOutcome:
        available, reason = self.availability()
        if not available:
            raise EngineFailure("engine_unavailable", reason)
        if planning_input.has_blank_nodes:
            raise EngineFailure("capability_requirement_unsatisfied",
                                "blank nodes: the binary relabels them, so closures cannot be compared")
        if planning_input.profile not in self.declaration.profiles:
            raise EngineFailure("capability_requirement_unsatisfied", f"profile {planning_input.profile}")
        work = tempfile.mkdtemp(prefix="ontology-change-oo-", dir=self.settings.get("work_root"))
        started = time.monotonic()
        try:
            folder = Path(work)
            (folder / "home").mkdir()
            (folder / "base.nt").write_text(canonical_ntriples(planning_input.base), encoding="utf-8")
            (folder / "proposed.nt").write_text(canonical_ntriples(planning_input.proposed), encoding="utf-8")
            (folder / "plan.batch").write_text(_batch(planning_input.profile), encoding="utf-8")
            code, stdout, stderr = sandboxed_run(
                self.settings["binary_path"], ("--data-dir", "/work/data", "--no-connect", "batch", "--bail",
                                               "/work/plan.batch"), work,
                timeout=float(self.settings.get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS)),
                memory=int(self.settings.get("memory_bytes", DEFAULT_MEMORY_BYTES)))
            reports = self._reports(code, stdout, stderr, planning_input.profile)
            closures = []
            for graph in ("base", "proposed"):
                try:
                    closure = parse_ntriples((folder / f"{graph}-closure.nt").read_text(encoding="utf-8"),
                                             maximum_triples=planning_input.maximum_closure)
                except RdfSyntaxError as error:
                    if "more than" in str(error):
                        raise EngineFailure("limit_exceeded", f"the {graph} closure passes the bound") from None
                    raise EngineFailure("engine_reported_failure", f"{graph} closure: {error}") from None
                closures.append(closure)
            table = RULE_TABLES[planning_input.profile]
            derivations = [_derivations(folder / f"cert-{graph}" / "derivations.tsv", table)
                           for graph in ("base", "proposed")]
        except OSError as error:
            raise EngineFailure("engine_reported_failure", f"the work folder: {type(error).__name__}") from None
        finally:
            if not self.settings.get("keep_work"):
                shutil.rmtree(work, ignore_errors=True)
        return EngineOutcome(self.declaration.engine_ref, table, closures[0], closures[1], derivations[0],
                             derivations[1], {"elapsed_seconds": round(time.monotonic() - started, 3),
                                              "binary_sha256": BINARY_SHA256, "reason_runs": reports})

    @staticmethod
    def _reports(code: int, stdout: bytes, stderr: str, profile: str) -> list:
        """The two reason reports, after every batch step answered without an error."""
        try:
            values = _json_values(stdout.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            raise EngineFailure("engine_reported_failure", f"unreadable output, exit {code}: {stderr}") from None
        expected = ["load", "reason", "save", "clear", "load", "reason", "save"]
        commands = [value.get("command") for value in values if isinstance(value, dict)]
        if code != 0 or commands != expected:
            raise EngineFailure("engine_reported_failure", f"exit {code}, steps {commands}: {stderr}")
        reports = []
        for value in values:
            result = value.get("result")
            if not isinstance(result, dict) or "error" in result:
                raise EngineFailure("engine_reported_failure", f"{value.get('command')}: {str(result)[:300]}")
            if value["command"] == "reason":
                if result.get("fixpoint_reached") is not True or result.get("profile_used") != profile:
                    raise EngineFailure("engine_reported_failure", "a reason step did not reach its fixpoint")
                reports.append({"inferred": result.get("inferred_count"), "iterations": result.get("iterations")})
        return reports


def run_lean_checker(checker_path: str, asserted_text: str, derivations_text: str, *, work_root=None) -> dict:
    """Run the release's oo-cert on a two-file certificate in the same sandbox; its verdict and exit."""
    problem = pinned_file_problem(checker_path, CHECKER_SHA256)
    if problem:
        return {"ran": False, "reason": problem}
    work = tempfile.mkdtemp(prefix="ontology-change-cert-", dir=work_root)
    try:
        Path(work, "asserted.tsv").write_text(asserted_text, encoding="utf-8")
        Path(work, "derivations.tsv").write_text(derivations_text, encoding="utf-8")
        Path(work, "home").mkdir()
        code, stdout, _stderr = sandboxed_run(checker_path, ("/work/asserted.tsv", "/work/derivations.tsv"), work,
                                              timeout=60.0, memory=CHECKER_MEMORY_BYTES)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    try:
        verdict = json.loads(stdout.decode("utf-8").strip().splitlines()[-1])
    except (ValueError, IndexError, UnicodeDecodeError):
        verdict = {}
    return {"ran": True, "exit": code, "ok": verdict.get("ok") is True and code == 0,
            "theorem": verdict.get("theorem"), "first_rejected": verdict.get("first_rejected"),
            "checker_sha256": CHECKER_SHA256}
