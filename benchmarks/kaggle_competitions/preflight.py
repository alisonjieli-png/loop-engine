"""Read-only access preflight for a frozen Kaggle competition population.

This benchmark utility lists entered competitions, freezes the selected order,
then probes the files endpoint for every selected competition. It never
downloads competition data, runs a model, trains a solution, or submits an
artifact. The resulting report is acquisition evidence only.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import tempfile
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

REPORT_TYPE = "kaggle_access_preflight/v1"
POPULATION_TYPE = "kaggle_access_population/v1"
DEFAULT_PAGE_SIZE = 20
FILES_PAGE_SIZE = 200
RETRYABLE_PROBE_STATUSES = frozenset({
    "empty_response",
    "probe_failed",
    "rate_limited",
    "response_invalid",
    "timeout_or_cli_unavailable",
})


class KagglePreflightError(ValueError):
    """A preflight request or Kaggle response could not be used safely."""


@dataclass(frozen=True)
class CommandResult:
    """Bounded process result from one read-only Kaggle CLI request."""

    argv: tuple[str, ...]
    returncode: int
    stdout: str = ""
    stderr: str = ""


@dataclass(frozen=True)
class KagglePreflightRequest:
    """Explicit population, network, concurrency, and timeout authority."""

    campaign_id: str
    target_competitions: int = 120
    maximum_pages: int = 8
    page_size: int = DEFAULT_PAGE_SIZE
    concurrency: int = 4
    timeout_seconds: int = 60
    probe_delay_seconds: float = 0.0
    resume_report_path: str = ""
    workspace_root: str = ""
    authorize_network_reads: bool = False
    group: str = "entered"
    sort_by: str = "prize"
    search: str = ""

    def __post_init__(self) -> None:
        if not self.campaign_id.strip():
            raise KagglePreflightError("campaign_id cannot be empty")
        from loop_engine.core.run_history_paths import (
            RunHistoryIntegrityError,
            validated_run_id,
        )
        try:
            validated_run_id(self.campaign_id)
        except RunHistoryIntegrityError as exc:
            raise KagglePreflightError(str(exc)) from exc
        if not isinstance(self.authorize_network_reads, bool):
            raise KagglePreflightError(
                "authorize_network_reads must be an exact Boolean")
        for name in (
            "target_competitions", "maximum_pages", "page_size",
            "concurrency", "timeout_seconds",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise KagglePreflightError(f"{name} must be a positive integer")
        if self.page_size > 200:
            raise KagglePreflightError("Kaggle list page_size cannot exceed 200")
        if (isinstance(self.probe_delay_seconds, bool)
                or not isinstance(self.probe_delay_seconds, (int, float))
                or self.probe_delay_seconds < 0):
            raise KagglePreflightError(
                "probe_delay_seconds must be a non-negative number")
        if self.group not in ("entered", "general", "inClass"):
            raise KagglePreflightError("unsupported Kaggle competition group")
        if not isinstance(self.resume_report_path, str):
            raise KagglePreflightError("resume_report_path must be text")
        if not isinstance(self.workspace_root, str):
            raise KagglePreflightError("workspace_root must be text")
        if self.sort_by not in (
            "grouped", "prize", "earliestDeadline", "latestDeadline",
            "numberOfTeams", "recentlyCreated",
        ):
            raise KagglePreflightError("unsupported Kaggle competition ordering")
        if (type(self.search) is not str or self.search != self.search.strip()
                or any(ord(character) < 32 or ord(character) == 127
                       for character in self.search)):
            raise KagglePreflightError(
                "search must be trimmed text without control characters")
        try:
            self.search.encode("utf-8")
        except UnicodeError:
            raise KagglePreflightError("search must be UTF-8 text") from None


def _confined_path(root: str, value: str, label: str) -> Path:
    """Resolve one path below an explicit non-symlink workspace root."""
    if not str(root or "").strip():
        raise KagglePreflightError(f"{label} requires workspace_root")
    workspace = Path(root).expanduser()
    if workspace.exists() and workspace.is_symlink():
        raise KagglePreflightError("workspace_root cannot be a symlink")
    workspace = workspace.resolve()
    candidate = Path(value).expanduser()
    if candidate.exists() and candidate.is_symlink():
        raise KagglePreflightError(f"{label} cannot be a symlink")
    candidate = candidate.resolve()
    if candidate == workspace or workspace not in candidate.parents:
        raise KagglePreflightError(
            f"{label} must remain below workspace_root")
    return candidate


def _validate_destinations(
    request: KagglePreflightRequest, output_path: str, runs_dir: str,
) -> tuple[Path, Path]:
    """Refuse overlapping evidence destinations before external effects."""
    output = _confined_path(
        request.workspace_root, output_path, "output_path")
    history_root = _confined_path(
        request.workspace_root, runs_dir, "runs_dir")
    expected_history = history_root / request.campaign_id

    def overlaps(left: Path, right: Path) -> bool:
        return left == right or left in right.parents or right in left.parents

    if overlaps(output, history_root) or overlaps(output, expected_history):
        raise KagglePreflightError(
            "output_path and Run History destinations must be disjoint")
    if request.resume_report_path:
        resume = _confined_path(
            request.workspace_root, request.resume_report_path,
            "resume_report_path")
        if output == resume or overlaps(resume, expected_history):
            raise KagglePreflightError(
                "resume, output, and new Run History destinations must be "
                "disjoint")
    return output, history_root


Runner = Callable[[tuple[str, ...], int], CommandResult]


def _canonical(value: object) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    )


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _file_digest(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _local_command(argv: tuple[str, ...]) -> str:
    try:
        result = subprocess.run(
            argv, capture_output=True, text=True, timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return (result.stdout or result.stderr).strip()


def implementation_snapshot() -> dict:
    """Bind evidence to code and local tool identity without storing secrets."""
    source = os.path.abspath(__file__)
    status = _local_command(("git", "status", "--porcelain=v1"))
    try:
        kaggle_version = importlib.metadata.version("kaggle")
    except importlib.metadata.PackageNotFoundError:
        kaggle_version = "unknown"
    if os.environ.get("KAGGLE_API_TOKEN"):
        auth_kind = "environment_access_token"
    elif os.environ.get("KAGGLE_USERNAME") or os.environ.get("KAGGLE_KEY"):
        auth_kind = "legacy_environment_fields"
    elif Path("~/.kaggle/access_token").expanduser().is_file():
        auth_kind = "access_token_file"
    elif Path("~/.kaggle/kaggle.json").expanduser().is_file():
        auth_kind = "legacy_config_file"
    else:
        auth_kind = "unknown_or_unavailable"
    return {
        "script": "benchmarks/kaggle_competitions/preflight.py",
        "script_sha256": _file_digest(source),
        "repository_head": _local_command(("git", "rev-parse", "HEAD")),
        "repository_branch": _local_command(
            ("git", "branch", "--show-current")),
        "worktree_dirty": bool(status),
        "worktree_status_sha256": _digest(status.splitlines()),
        "python_version": platform.python_version(),
        "kaggle_cli_version": kaggle_version,
        "authentication_kind": auth_kind,
        "secret_values_recorded": False,
    }


def _bounded(text: object, maximum: int = 800) -> str:
    value = str(text or "").replace("\x00", "")
    return value[:maximum]


def _run_cli(argv: tuple[str, ...], timeout_seconds: int) -> CommandResult:
    try:
        completed = subprocess.run(
            argv, capture_output=True, text=True, timeout=timeout_seconds,
            check=False,
        )
        return CommandResult(
            argv, int(completed.returncode), completed.stdout,
            _bounded(completed.stderr),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return CommandResult(argv, 124, "", _bounded(
            f"{type(exc).__name__}: {exc}"))


def _read_json(result: CommandResult, purpose: str):
    if result.returncode != 0:
        raise KagglePreflightError(
            f"{purpose} failed with exit {result.returncode}: "
            f"{_failure_status(result)}")
    try:
        return json.loads(result.stdout)
    except (TypeError, json.JSONDecodeError) as exc:
        raise KagglePreflightError(
            f"{purpose} returned unreadable JSON") from exc


def _read_files_json(result: CommandResult, purpose: str) -> tuple[object, bool]:
    """Read file JSON and recognize the Kaggle CLI cursor preamble."""
    if result.returncode != 0:
        raise KagglePreflightError(
            f"{purpose} failed with exit {result.returncode}: "
            f"{_failure_status(result)}")
    body = result.stdout.lstrip()
    next_page_available = False
    if body.startswith("Next Page Token = "):
        header, separator, body = body.partition("\n")
        token = header.removeprefix("Next Page Token = ").strip()
        if not separator or not token:
            raise KagglePreflightError(
                f"{purpose} returned an invalid pagination preamble")
        next_page_available = True
        body = body.lstrip()
    try:
        return json.loads(body), next_page_available
    except (TypeError, json.JSONDecodeError) as exc:
        raise KagglePreflightError(
            f"{purpose} returned unreadable JSON") from exc


def _slug(reference: object) -> str:
    text = str(reference or "").strip().rstrip("/")
    marker = "/competitions/"
    value = text.rsplit(marker, 1)[-1] if marker in text else text
    if not value or "/" in value or "\\" in value:
        raise KagglePreflightError(
            f"competition reference has no safe slug: {_bounded(text, 160)!r}")
    return value


def _list_command(request: KagglePreflightRequest, page: int) -> tuple[str, ...]:
    return (
        "kaggle", "competitions", "list", "--group", request.group,
        "--sort-by", request.sort_by, "--page", str(page), "--page-size",
        str(request.page_size), "--format", "json",
    ) + (("--search", request.search) if request.search else ())


def _files_command(slug: str) -> tuple[str, ...]:
    return (
        "kaggle", "competitions", "files", slug,
        "--page-size", str(FILES_PAGE_SIZE), "--format", "json",
    )


def freeze_population(
    request: KagglePreflightRequest, runner: Runner = _run_cli,
) -> dict:
    """List and freeze the selected competition order before file probes."""
    if request.authorize_network_reads is not True:
        raise PermissionError(
            "Kaggle population discovery requires authorize_network_reads=True")
    if runner is _run_cli:
        raise KagglePreflightError(
            "the real Kaggle runner requires canonical Loop ownership")
    rows: list[dict] = []
    failures: list[dict] = []
    seen: set[str] = set()
    calls = 0
    for page in range(1, request.maximum_pages + 1):
        command = _list_command(request, page)
        calls += 1
        result = runner(command, request.timeout_seconds)
        try:
            payload = _read_json(result, f"competition list page {page}")
            if not isinstance(payload, list):
                raise KagglePreflightError(
                    f"competition list page {page} is not a list")
        except KagglePreflightError as exc:
            failures.append({
                "page": page, "error": _bounded(exc),
                "returncode": result.returncode,
            })
            continue
        if not payload:
            break
        for item in payload:
            if not isinstance(item, dict):
                failures.append({
                    "page": page,
                    "error": "competition row is not an object",
                })
                continue
            try:
                slug = _slug(item.get("ref"))
            except KagglePreflightError as exc:
                failures.append({"page": page, "error": _bounded(exc)})
                continue
            if slug in seen:
                continue
            seen.add(slug)
            rows.append({
                "selection_rank": len(rows) + 1,
                "slug": slug,
                "ref": str(item.get("ref") or ""),
                "deadline": str(item.get("deadline") or ""),
                "category": str(item.get("category") or ""),
                "reward": str(item.get("reward") or ""),
                "team_count": item.get("teamCount"),
                "user_has_entered": bool(item.get("userHasEntered")),
                "source_page": page,
            })
            if len(rows) >= request.target_competitions:
                break
        if len(rows) >= request.target_competitions:
            break
    selected = rows[:request.target_competitions]
    material = {
        "record_type": POPULATION_TYPE,
        "group": request.group,
        "sort_by": request.sort_by,
        "search": request.search,
        "page_size": request.page_size,
        "target_competitions": request.target_competitions,
        "selected": selected,
        "list_failures": failures,
    }
    return {
        **material,
        "population_digest": _digest(material),
        "list_calls": calls,
        "target_met": len(selected) == request.target_competitions,
    }


def _failure_status(result: CommandResult) -> str:
    stdout = result.stdout
    if stdout.lstrip().startswith("Next Page Token = "):
        stdout = ""
    text = f"{result.stderr}\n{stdout}".lower()
    if "429" in text or "too many requests" in text:
        return "rate_limited"
    if any(word in text for word in (
            "403", "forbidden", "permission", "rules", "authenticate")):
        return "access_refused"
    if "404" in text or "not found" in text:
        return "not_found"
    if result.returncode == 124:
        return "timeout_or_cli_unavailable"
    return "probe_failed"


def _load_resume_report(path: str, request: KagglePreflightRequest) -> dict:
    """Load an exact prior report and retain its frozen population."""
    try:
        with open(path, encoding="utf-8") as handle:
            report = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise KagglePreflightError("resume report is unreadable") from exc
    if not isinstance(report, dict) or report.get("record_type") != REPORT_TYPE:
        raise KagglePreflightError("resume report has the wrong record type")
    stored_digest = str(report.get("report_digest") or "")
    body = dict(report)
    body.pop("report_digest", None)
    if stored_digest != _digest(body):
        raise KagglePreflightError("resume report digest does not match")
    population = report.get("population")
    if not isinstance(population, dict) or population.get(
            "record_type") != POPULATION_TYPE:
        raise KagglePreflightError("resume report has no frozen population")
    selected = population.get("selected")
    if not isinstance(selected, list) or len(selected) != \
            request.target_competitions:
        raise KagglePreflightError(
            "resume population does not match target_competitions")
    slugs = [item.get("slug") for item in selected if isinstance(item, dict)]
    if len(slugs) != len(selected) or len(set(slugs)) != len(slugs):
        raise KagglePreflightError("resume population has invalid identities")
    population_body = {
        key: population.get(key) for key in (
            "record_type", "group", "sort_by", "page_size",
            "target_competitions", "selected", "list_failures",
        )
    }
    # Historical v1 populations predate the optional filter. Verify their
    # original bytes/field set; absence means the unfiltered default only.
    if "search" in population:
        population_body["search"] = population["search"]
    if population.get("population_digest") != _digest(population_body):
        raise KagglePreflightError("resume population digest does not match")
    requested_semantics = {
        "group": request.group,
        "sort_by": request.sort_by,
        "search": request.search,
        "page_size": request.page_size,
        "target_competitions": request.target_competitions,
    }
    mismatches = {
        name: {"requested": value, "frozen": population.get(
            name, "" if name == "search" else None)}
        for name, value in requested_semantics.items()
        if population.get(name, "" if name == "search" else None) != value
    }
    if mismatches:
        raise KagglePreflightError(
            "resume population selection semantics do not match: "
            f"{_canonical(mismatches)}")
    migrations = []
    normalized_probes = []
    for probe in report.get("probes", ()):
        normalized = dict(probe) if isinstance(probe, dict) else probe
        if (isinstance(normalized, dict)
                and normalized.get("status") == "files_accessible"
                and normalized.get("file_count_returned") == 0):
            normalized["status"] = "files_listing_empty"
            normalized["access_response_readable"] = True
            migrations.append({
                "slug": normalized.get("slug"),
                "from": "files_accessible",
                "to": "files_listing_empty",
                "reason": "readable v1 response contained no file rows",
            })
        normalized_probes.append(normalized)
    return {
        **report,
        "probes": normalized_probes,
        "_reader_migrations": migrations,
    }


def _prior_probe_is_retryable(probe: object) -> bool:
    """Retry transient results and legacy parse failures, not hard refusals."""
    if not isinstance(probe, dict):
        return True
    status = str(probe.get("status") or "")
    if status in {"files_accessible", "files_listing_empty"}:
        return False
    if status in RETRYABLE_PROBE_STATUSES:
        return True
    if status in {"access_refused", "not_found"}:
        # A zero-exit response was mislabeled by the v1 parser when a cursor
        # happened to contain status-like digits. It remains safe to retry.
        return probe.get("returncode") == 0
    return True


class _ProbeStartLimiter:
    """Space physical request starts without hiding the chosen interval."""

    def __init__(self, delay_seconds: float) -> None:
        self.delay_seconds = float(delay_seconds)
        self._lock = threading.Lock()
        self._last_started = 0.0

    def wait(self) -> None:
        if self.delay_seconds <= 0:
            return
        with self._lock:
            remaining = self.delay_seconds - (time.monotonic()
                                                - self._last_started)
            if remaining > 0:
                time.sleep(remaining)
            self._last_started = time.monotonic()


def probe_competition_files(
    row: dict, request: KagglePreflightRequest, runner: Runner = _run_cli,
) -> dict:
    """Probe one files endpoint without downloading any body."""
    if request.authorize_network_reads is not True:
        raise PermissionError(
            "Kaggle file metadata requires authorize_network_reads=True")
    if runner is _run_cli:
        raise KagglePreflightError(
            "the real Kaggle runner requires canonical Loop ownership")
    slug = _slug(row.get("slug"))
    command = _files_command(slug)
    result = runner(command, request.timeout_seconds)
    base = {
        "selection_rank": row.get("selection_rank"),
        "slug": slug,
        "command_kind": "kaggle competitions files",
        "returncode": result.returncode,
    }
    if result.returncode != 0:
        failure_status = _failure_status(result)
        return {
            **base, "status": failure_status,
            "error": f"files probe failed: {failure_status}",
            "file_count_returned": 0,
            "known_total_bytes": 0,
            "may_be_truncated": False,
            "files": [],
        }
    try:
        payload, next_page_available = _read_files_json(
            result, f"files probe for {slug}")
        if not isinstance(payload, list):
            raise KagglePreflightError("files response is not a list")
        files = []
        for item in payload:
            if not isinstance(item, dict):
                raise KagglePreflightError("files response contains a non-object")
            size = item.get("size")
            size = int(size) if isinstance(size, (int, float)) else None
            files.append({
                "name": _bounded(item.get("name"), 300),
                "size_bytes": size,
                "creation_date": str(item.get("creationDate") or ""),
            })
        known_sizes = [item["size_bytes"] for item in files
                       if isinstance(item["size_bytes"], int)]
        status = "files_accessible" if files else "files_listing_empty"
        return {
            **base, "status": status, "error": "",
            "access_response_readable": True,
            "file_count_returned": len(files),
            "known_total_bytes": sum(known_sizes),
            "largest_known_file_bytes": max(known_sizes, default=0),
            "files_with_unknown_size": len(files) - len(known_sizes),
            "may_be_truncated": (
                next_page_available or len(files) >= FILES_PAGE_SIZE),
            "next_page_available": next_page_available,
            "files": files,
        }
    except (KagglePreflightError, ValueError) as exc:
        status = "empty_response" if not (
            result.stdout.strip() or result.stderr.strip()
        ) else "response_invalid"
        return {
            **base, "status": status,
            "error": _bounded(exc),
            "response_diagnostic": {
                "stdout_nonempty": bool(result.stdout.strip()),
                "stdout_characters": len(result.stdout),
                "pagination_preamble_present": result.stdout.lstrip().startswith(
                    "Next Page Token = "),
            },
            "file_count_returned": 0,
            "known_total_bytes": 0, "may_be_truncated": False,
            "files": [],
        }


def _transport_observation(result: CommandResult) -> dict:
    """Return a bounded, secret-free observation about one CLI response."""
    stdout = result.stdout
    body = stdout.lstrip()
    pagination_preamble = body.startswith("Next Page Token = ")
    if pagination_preamble:
        _header, separator, body = body.partition("\n")
        if not separator:
            body = ""
    payload = None
    if result.returncode == 0:
        try:
            payload = json.loads(body)
        except (TypeError, json.JSONDecodeError):
            pass
    readable_list = isinstance(payload, list)
    status = (
        "readable_list" if readable_list else
        _failure_status(result) if result.returncode != 0 else
        "empty_response" if not (stdout.strip() or result.stderr.strip()) else
        "response_invalid"
    )
    return {
        "status": status,
        "returncode": result.returncode,
        "stdout_bytes": len(stdout.encode("utf-8", errors="replace")),
        "response_body_sha256": (
            hashlib.sha256(
                body.encode("utf-8", errors="replace")).hexdigest()
            if readable_list else ""),
        "stderr_bytes": len(result.stderr.encode("utf-8", errors="replace")),
        "pagination_preamble_present": pagination_preamble,
        "item_count": len(payload) if readable_list else 0,
        "response_content_recorded": False,
    }


def _run_cli_in_loop(
    argv: tuple[str, ...], timeout_seconds: int, parent, runner: Runner,
) -> CommandResult:
    """Execute one approved metadata read in an effect-declared Loop."""
    from loop_engine.core.runtime_observer import RuntimeObservationServices
    from loop_engine.loop.effect_approval import (
        ApprovalDecision,
        ApprovalRequest,
        EffectApprovalService,
        EffectClass,
        EffectSpec,
    )
    from loop_engine.loop.loop_contract import contract_for_code_loop
    from loop_engine.loop.loop_role import (
        LoopRelationship,
        LoopRole,
        LoopRoleIdentity,
    )
    from loop_engine.loop.recursive_loop import LoopConfig, StepOutcome

    command_digest = hashlib.sha256("\0".join(argv).encode()).hexdigest()
    effect = EffectSpec(
        EffectClass.NETWORK_READ,
        "kaggle_cli_metadata_read",
        f"kaggle://competitions/{argv[2]}",
        (("command_sha256", command_digest),),
    )
    approvals = EffectApprovalService(
        runtime=RuntimeObservationServices(parent=parent, ledger=parent.ledger))
    approval = ApprovalRequest.create(
        parent.loop_id, effect,
        "User requested a read-only Kaggle competition preflight.",
        requested_by="kaggle_preflight")
    checkpoint = approvals.create(approval)
    approvals.resume(
        checkpoint.pending, checkpoint.resume_token,
        ApprovalDecision.approve(
            approval.request_id, "user.current_request",
            reason="The current request authorizes read-only Kaggle testing."))
    approvals.consume(approval.request_id, approval.effect)

    contract = contract_for_code_loop(
        "kaggle_metadata_read",
        input_roles=("kaggle_cli_metadata_request/v1",),
        output_roles=("kaggle_cli_metadata_observation/v1",),
        effects=("network",), locality="api_calling", role="intelligence")
    loop = parent.spawn(
        f"read one Kaggle metadata response {command_digest[:20]}",
        LoopConfig(
            framework="custom", custom_steps=("retrieve",),
            logical_kind="execution", replay_guarantee="evidence_equivalent",
            allowable_modes=("deterministic",),
            preferred_modes=("deterministic",),
            delegated_modes=("deterministic",), power="light",
            exit_condition="accepted_success"),
        contract=contract,
        identity=LoopRoleIdentity(LoopRole.INTELLIGENCE, "intelligence.search"),
        relationship=LoopRelationship.queried_by(parent.loop_id))
    holder: dict[str, object] = {}

    def handler(active, _step: str, _context: dict) -> StepOutcome:
        active.ledger.record(
            loop_id=active.loop_id, event="tool_invocation_started",
            tool="kaggle_cli", operation="metadata_read",
            command_sha256=command_digest, declared_effect="network",
            effect_class=EffectClass.NETWORK_READ.value,
            approval_request_id=approval.request_id)
        result = runner(argv, timeout_seconds)
        observation = _transport_observation(result)
        holder["result"] = result
        holder["observation"] = observation
        ok = observation["status"] == "readable_list"
        active.ledger.record(
            loop_id=active.loop_id,
            event=("tool_invocation_completed" if ok
                   else "tool_invocation_failed"),
            tool="kaggle_cli", operation="metadata_read",
            command_sha256=command_digest, declared_effect="network",
            effect_class=EffectClass.NETWORK_READ.value,
            approval_request_id=approval.request_id, **observation)
        if ok:
            active.ledger.record(
                loop_id=active.loop_id,
                event="intelligence.context.retrieved",
                kind="kaggle_metadata", name=command_digest[:20],
                pulled=True,
                response_sha256=observation["response_body_sha256"],
                item_count=observation["item_count"])
        else:
            active.ledger.record(
                loop_id=active.loop_id, event="failure.detected",
                failure_class=observation["status"],
                command_sha256=command_digest)
        return StepOutcome(
            output=f"metadata:{observation['status']}",
            mode="deterministic", confidence=1.0 if ok else 0.0,
            failed=not ok)

    loop.run(handler=handler, max_steps=1)
    result = holder.get("result")
    if not isinstance(result, CommandResult):
        raise KagglePreflightError("metadata Loop produced no command result")
    return result


def run_preflight(
    request: KagglePreflightRequest, runner: Runner = _run_cli,
    parent=None,
) -> dict:
    """Freeze a population, probe every member, and return one report."""
    if request.authorize_network_reads is not True:
        raise PermissionError(
            "Kaggle access preflight requires authorize_network_reads=True")
    if parent is None and runner is _run_cli:
        raise KagglePreflightError(
            "the real Kaggle runner requires canonical Loop ownership")
    started = time.monotonic()
    active_runner = runner
    if parent is not None:
        def loop_owned_runner(
            argv: tuple[str, ...], timeout_seconds: int,
        ) -> CommandResult:
            return _run_cli_in_loop(
                argv, timeout_seconds, parent, runner)

        active_runner = loop_owned_runner
    prior_report = None
    if request.resume_report_path:
        resume_path = _confined_path(
            request.workspace_root, request.resume_report_path,
            "resume_report_path")
        prior_report = _load_resume_report(
            str(resume_path), request)
        population = prior_report["population"]
        list_calls = 0
    else:
        population = freeze_population(request, active_runner)
        list_calls = population["list_calls"]
    selected = tuple(population["selected"])
    prior_by_slug = {
        item.get("slug"): item for item in (
            prior_report.get("probes", ()) if prior_report else ())
        if isinstance(item, dict) and item.get("slug")
    }
    retry_rows = tuple(
        row for row in selected
        if _prior_probe_is_retryable(prior_by_slug.get(row["slug"])))
    limiter = _ProbeStartLimiter(request.probe_delay_seconds)

    def probe(row: dict) -> dict:
        limiter.wait()
        return probe_competition_files(row, request, active_runner)

    with ThreadPoolExecutor(max_workers=request.concurrency) as executor:
        new_probes = list(executor.map(probe, retry_rows))
    new_by_slug = {item["slug"]: item for item in new_probes}
    probes = [
        new_by_slug.get(row["slug"], prior_by_slug.get(row["slug"]))
        for row in selected
    ]
    if any(not isinstance(item, dict) for item in probes):
        raise KagglePreflightError(
            "preflight did not produce one result per selected competition")
    statuses: dict[str, int] = {}
    for item in probes:
        status = item["status"]
        statuses[status] = statuses.get(status, 0) + 1
    report = {
        "record_type": REPORT_TYPE,
        "campaign_id": request.campaign_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "request": {
            "target_competitions": request.target_competitions,
            "maximum_pages": request.maximum_pages,
            "page_size": request.page_size,
            "concurrency": request.concurrency,
            "timeout_seconds": request.timeout_seconds,
            "probe_delay_seconds": request.probe_delay_seconds,
            "resumed": prior_report is not None,
            "network_reads_authorized": request.authorize_network_reads,
            "group": request.group,
            "sort_by": request.sort_by,
            "search": request.search,
        },
        "implementation": implementation_snapshot(),
        "privacy": {
            "classification": "account_scoped_private_metadata",
            "entered_membership_included": population.get("group") == "entered",
            "publication_review_required": True,
            "credentials_or_tokens_included": False,
        },
        "population": population,
        "summary": {
            "selected_denominator": len(selected),
            "target_met": population["target_met"],
            "file_probes_attempted": len(probes),
            "file_probes_attempted_this_run": len(new_probes),
            "prior_probe_results_reused": len(probes) - len(new_probes),
            "status_counts": dict(sorted(statuses.items())),
            "known_total_bytes_across_accessible_metadata": sum(
                item.get("known_total_bytes", 0) for item in probes),
            "list_calls": list_calls,
            "file_probe_calls": len(new_probes),
            "physical_cli_requests": list_calls + len(new_probes),
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "model_calls": 0,
            "downloads": 0,
            "submissions": 0,
        },
        "probes": sorted(probes, key=lambda item: item["selection_rank"]),
        "retry_lineage": ({
            "parent_report_digest": prior_report["report_digest"],
            "parent_population_digest": population["population_digest"],
            "reader_migrations": prior_report.get("_reader_migrations", []),
            "retried_statuses": sorted({
                item.get("status") for item in prior_by_slug.values()
                if _prior_probe_is_retryable(item)}),
        } if prior_report else {}),
        "limitations": [
            ("This is a read-only access and file-metadata campaign, not a "
             "competition solve or score."),
            ("A files response with 200 rows may be truncated by the CLI page "
             "size and is marked as such."),
            ("File names and sizes describe source morphology. They do not "
             "establish the target, metric, evaluator, or solution route."),
            ("No competition data was downloaded and no Kaggle submission "
             "was created or sent."),
        ],
    }
    report["report_digest"] = _digest(report)
    return report


def run_preflight_as_loop(
    request: KagglePreflightRequest, runs_dir: str,
    runner: Runner = _run_cli,
) -> dict:
    """Run discovery and probes through canonical Loops and Run History."""
    if request.concurrency != 1:
        raise KagglePreflightError(
            "the Loop-owned preflight currently requires concurrency=1")
    if not str(runs_dir or "").strip():
        raise KagglePreflightError("the Loop-owned preflight needs runs_dir")
    history_root = _confined_path(
        request.workspace_root, runs_dir, "runs_dir")
    expected_history = history_root / request.campaign_id
    if expected_history.exists() or expected_history.is_symlink():
        raise FileExistsError(
            f"Run History destination already exists: {expected_history}")
    from loop_engine.core.run_history import RunHistory
    from loop_engine.loop.loop_role import (
        LoopRelationship,
        LoopRole,
        LoopRoleIdentity,
    )
    from loop_engine.loop.recursive_loop import (
        Loop,
        LoopConfig,
        LoopLedger,
        StepOutcome,
    )

    ledger = LoopLedger()
    owner = Loop(
        f"Kaggle access preflight {request.campaign_id}",
        LoopConfig(
            framework="five_step", power="small",
            allowable_modes=("deterministic",),
            preferred_modes=("deterministic",),
        ),
        ledger=ledger,
        identity=LoopRoleIdentity(
            LoopRole.PRACTITIONER, "practitioner.research"),
        relationship=LoopRelationship.starting(),
    )
    holder: dict = {}

    def handler(loop, step: str, _context: dict) -> StepOutcome:
        if step == "act":
            holder["report"] = run_preflight(
                request, runner, parent=loop)
            return StepOutcome(
                output="kaggle access population probed",
                mode="deterministic", confidence=1.0)
        if step == "check":
            complete = len(holder.get("report", {}).get("probes", ())) \
                == request.target_competitions
            return StepOutcome(
                output=("preflight accounting:complete" if complete else
                        "preflight accounting:failed"),
                mode="deterministic", confidence=1.0 if complete else 0.0)
        return StepOutcome(
            output=f"{step}:recorded", mode="deterministic", confidence=1.0)

    result = owner.run(handler=handler, max_steps=len(owner.steps()) + 1)
    report = holder.get("report")
    if not isinstance(report, dict):
        raise KagglePreflightError("the owning Practitioner produced no report")
    report_core_digest = report["report_digest"]
    ledger.record(
        loop_id=result.loop_id, event="information.binding.published",
        binding_kind="kaggle_access_preflight_core",
        record_type=REPORT_TYPE, content_digest=report_core_digest)
    history = RunHistory.from_ledger(ledger.events, run_id=request.campaign_id)
    head = history.commit()
    history_path = history.save(str(history_root))
    os.chmod(history_root, 0o700)
    os.chmod(history_path, 0o700)
    for saved_file in Path(history_path).iterdir():
        if saved_file.is_file() and not saved_file.is_symlink():
            os.chmod(saved_file, 0o600)
    report.pop("report_digest", None)
    report["loop_execution"] = {
        "root_loop_id": result.loop_id,
        "root_loop_definition": {
            "id": result.loop_definition_id,
            "version": result.loop_definition_version,
            "digest": result.loop_definition_digest,
        },
        "model_calls": result.model_calls,
        "run_history_id": history.run_id,
        "run_history_path": history_path,
        "run_history_events": len(history.event_log),
        "run_history_head_digest": head,
        "run_history_chain": history.verify_chain(),
        "report_core_digest": report_core_digest,
        "tool_attempt_events": sum(
            event.get("event") == "tool_invocation_started"
            for event in ledger.events),
        "tool_success_events": sum(
            event.get("event") == "tool_invocation_completed"
            for event in ledger.events),
        "tool_failure_events": sum(
            event.get("event") == "tool_invocation_failed"
            for event in ledger.events),
        "retrieval_events": sum(
            event.get("event") == "intelligence.context.retrieved"
            for event in ledger.events),
    }
    report["report_digest"] = _digest(report)
    return report


def write_report(report: dict, output_path: str, workspace_root: str) -> None:
    """Write one report atomically after the campaign has completed."""
    path = str(_confined_path(workspace_root, output_path, "output_path"))
    if os.path.lexists(path):
        raise FileExistsError(f"preflight report already exists: {path}")
    parent = os.path.dirname(path)
    os.makedirs(parent, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=".kaggle-preflight-", suffix=".json", dir=parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Probe 100+ entered Kaggle competitions without download")
    parser.add_argument("--campaign-id", required=True)
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--runs-dir", required=True)
    parser.add_argument("--target", type=int, default=120)
    parser.add_argument("--maximum-pages", type=int, default=8)
    parser.add_argument("--page-size", type=int, default=DEFAULT_PAGE_SIZE)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--timeout-seconds", type=int, default=60)
    parser.add_argument("--probe-delay-seconds", type=float, default=0.0)
    parser.add_argument("--resume-report", default="")
    parser.add_argument("--search", default="",
                        help="optional exact Kaggle competition-list search filter")
    parser.add_argument("--authorize-network-reads", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    request = KagglePreflightRequest(
        campaign_id=args.campaign_id,
        target_competitions=args.target,
        maximum_pages=args.maximum_pages,
        page_size=args.page_size,
        concurrency=args.concurrency,
        timeout_seconds=args.timeout_seconds,
        probe_delay_seconds=args.probe_delay_seconds,
        resume_report_path=args.resume_report,
        search=args.search,
        workspace_root=args.workspace_root,
        authorize_network_reads=args.authorize_network_reads,
    )
    output_path, _history_root = _validate_destinations(
        request, args.output, args.runs_dir)
    if output_path.exists() or output_path.is_symlink():
        raise FileExistsError(
            f"preflight report already exists: {output_path}")
    report = run_preflight_as_loop(request, args.runs_dir)
    write_report(report, args.output, request.workspace_root)
    print(json.dumps({
        "record_type": "kaggle_access_preflight_summary/v1",
        "campaign_id": report["campaign_id"],
        "report_digest": report["report_digest"],
        **report["summary"],
        "output": os.path.abspath(args.output),
    }, indent=2, sort_keys=True))
    return 0 if report["summary"]["target_met"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
