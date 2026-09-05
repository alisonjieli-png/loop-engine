"""Passive records, identity checks, and paths for Kaggle qualification."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

PREFLIGHT_REPORT_TYPE = "kaggle_access_preflight/v1"
PREFLIGHT_POPULATION_TYPE = "kaggle_access_population/v1"
QUALIFICATION_RECORD_TYPE = "source_qualification/v1"
QUALIFICATION_CAMPAIGN_TYPE = "kaggle_source_qualification_campaign/v1"
EVALUATOR_CANDIDATE_TYPE = "independent_evaluator_contract_candidate/v1"
DOWNLOAD_PLAN_TYPE = "kaggle_download_plan/v1"

QUALIFICATION_STATES = frozenset({"QUALIFIED", "DEFERRED", "UNSUPPORTED", "BLOCKED"})
SUCCESSFUL_PREFLIGHT_STATUSES = frozenset({"files_accessible", "files_listing_empty"})
SAFE_PAGE_KINDS = frozenset(
    {"description", "rules", "evaluation", "data-description", "prizes"}
)
_HEX = frozenset("0123456789abcdef")


class SourceQualificationError(ValueError):
    """The qualification request or its evidence failed closed."""


def canonical(value: object) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def digest(value: object) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def bytes_digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(char in _HEX for char in value)


def require_sha256(value: str, name: str) -> None:
    if not _is_sha256(value):
        raise SourceQualificationError(f"{name} must be a lowercase SHA-256")


def safe_slug(value: object) -> str:
    slug = str(value or "").strip()
    if (
        not slug
        or len(slug) > 160
        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", slug)
        or ".." in slug
    ):
        raise SourceQualificationError("competition slug is not safe")
    return slug


def utc_datetime(value: str, name: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise SourceQualificationError(f"{name} must be an ISO-8601 time") from exc
    if parsed.tzinfo is None:
        raise SourceQualificationError(f"{name} must include a time zone")
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class QualificationPrivacyPolicy:
    """Private handling rules for untrusted competition source pages."""

    classification: str = "account_scoped_private_source"
    store_full_page_bodies: bool = True
    publish_page_content: bool = False
    retain_raw_cli_response: bool = False

    def __post_init__(self) -> None:
        if self.classification != "account_scoped_private_source":
            raise SourceQualificationError(
                "qualification pages require account_scoped_private_source"
            )
        if self.store_full_page_bodies is not True:
            raise SourceQualificationError(
                "full page bodies must be retained privately"
            )
        if self.publish_page_content is not False:
            raise SourceQualificationError(
                "competition page content cannot be published"
            )
        if self.retain_raw_cli_response is not False:
            raise SourceQualificationError(
                "the raw CLI envelope is not an approved retained artifact"
            )


@dataclass(frozen=True)
class QualificationByteBudget:
    """Hard byte and count bounds applied before private persistence."""

    maximum_preflight_bytes: int = 24 * 1024 * 1024
    maximum_response_bytes: int = 8 * 1024 * 1024
    maximum_page_body_bytes: int = 4 * 1024 * 1024
    maximum_total_private_bytes: int = 32 * 1024 * 1024
    maximum_pages_per_competition: int = 16

    def __post_init__(self) -> None:
        for name in (
            "maximum_preflight_bytes",
            "maximum_response_bytes",
            "maximum_page_body_bytes",
            "maximum_total_private_bytes",
            "maximum_pages_per_competition",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise SourceQualificationError(f"{name} must be a positive integer")
        if self.maximum_page_body_bytes > self.maximum_total_private_bytes:
            raise SourceQualificationError(
                "maximum_page_body_bytes cannot exceed the private byte budget"
            )


@dataclass(frozen=True)
class QualificationPathBudget:
    """Exact paths confined below one private workspace."""

    workspace_root: str
    preflight_report_path: str
    private_artifact_root: str
    run_history_root: str
    output_record_path: str
    maximum_path_characters: int = 512

    def __post_init__(self) -> None:
        for name in (
            "workspace_root",
            "preflight_report_path",
            "private_artifact_root",
            "run_history_root",
            "output_record_path",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise SourceQualificationError(f"{name} must be a non-empty path")
        if (
            isinstance(self.maximum_path_characters, bool)
            or not isinstance(self.maximum_path_characters, int)
            or self.maximum_path_characters < 80
        ):
            raise SourceQualificationError(
                "maximum_path_characters must be an integer of at least 80"
            )


@dataclass(frozen=True)
class SourceQualificationAuthority:
    """Exact read and private-write authority for this layer only."""

    authorized_by: str
    preflight_read_path: str
    page_read_slugs: tuple[str, ...]
    private_artifact_write_root: str
    run_history_write_root: str
    output_record_write_path: str
    allow_preflight_read: bool = False
    allow_network_page_reads: bool = False
    allow_kaggle_cli_command_execution: bool = False
    allow_kaggle_credential_access: bool = False
    allow_private_artifact_writes: bool = False
    allow_run_history_write: bool = False
    allow_output_record_write: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.authorized_by, str) or not self.authorized_by.strip():
            raise SourceQualificationError("authority needs authorized_by")
        if self.authorized_by == "mechanical_extractor":
            raise SourceQualificationError(
                "a mechanical extractor cannot issue effect authority"
            )
        if not isinstance(self.page_read_slugs, tuple):
            raise SourceQualificationError("page_read_slugs must be a tuple")
        slugs = tuple(safe_slug(item) for item in self.page_read_slugs)
        if len(slugs) != len(set(slugs)):
            raise SourceQualificationError("page_read_slugs must be unique")
        object.__setattr__(self, "page_read_slugs", slugs)
        for name in (
            "preflight_read_path",
            "private_artifact_write_root",
            "run_history_write_root",
            "output_record_write_path",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise SourceQualificationError(f"authority {name} must be a path")
        for name in (
            "allow_preflight_read",
            "allow_network_page_reads",
            "allow_kaggle_cli_command_execution",
            "allow_kaggle_credential_access",
            "allow_private_artifact_writes",
            "allow_run_history_write",
            "allow_output_record_write",
        ):
            if not isinstance(getattr(self, name), bool):
                raise SourceQualificationError(f"{name} must be an exact Boolean")


@dataclass(frozen=True)
class HumanLegalReview:
    """Independent legal decision bound to one exact source bundle."""

    competition_slug: str
    source_bundle_digest: str
    decision_id: str
    reviewer_id: str
    data_use_decision: str
    external_model_decision: str
    expires_at: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "competition_slug", safe_slug(self.competition_slug))
        require_sha256(self.source_bundle_digest, "source_bundle_digest")
        if not all(
            isinstance(value, str) and value.strip()
            for value in (self.decision_id, self.reviewer_id)
        ):
            raise SourceQualificationError(
                "legal review needs decision_id and reviewer_id"
            )
        if self.reviewer_id == "mechanical_extractor":
            raise SourceQualificationError(
                "mechanical extraction cannot grant legal authority"
            )
        if self.data_use_decision not in {"ALLOW", "DENY"}:
            raise SourceQualificationError("data_use_decision must be ALLOW or DENY")
        if self.external_model_decision not in {"ALLOW", "DENY", "UNKNOWN"}:
            raise SourceQualificationError(
                "external_model_decision must be ALLOW, DENY, or UNKNOWN"
            )
        if self.expires_at:
            utc_datetime(self.expires_at, "legal review expires_at")


@dataclass(frozen=True)
class IndependentEvaluatorReview:
    """Independent admission of one exact evaluator contract candidate."""

    competition_slug: str
    candidate_digest: str
    review_id: str
    reviewer_id: str
    implementation_producer_id: str
    implementation_ref: str
    implementation_digest: str
    verification_evidence_refs: tuple[str, ...]
    verified: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "competition_slug", safe_slug(self.competition_slug))
        require_sha256(self.candidate_digest, "candidate_digest")
        require_sha256(self.implementation_digest, "implementation_digest")
        if not all(
            isinstance(value, str) and value.strip()
            for value in (
                self.review_id,
                self.reviewer_id,
                self.implementation_producer_id,
                self.implementation_ref,
            )
        ):
            raise SourceQualificationError(
                "evaluator review needs review, reviewer, and implementation refs"
            )
        if self.reviewer_id == "mechanical_extractor":
            raise SourceQualificationError(
                "mechanical extraction cannot admit an evaluator"
            )
        if self.reviewer_id == self.implementation_producer_id:
            raise SourceQualificationError(
                "the evaluator implementation needs an independent reviewer"
            )
        if not isinstance(self.verification_evidence_refs, tuple) or (
            not self.verification_evidence_refs
            or any(
                not isinstance(item, str) or not item.strip()
                for item in self.verification_evidence_refs
            )
        ):
            raise SourceQualificationError(
                "evaluator review needs non-empty verification evidence refs"
            )
        if not isinstance(self.verified, bool):
            raise SourceQualificationError("verified must be an exact Boolean")


@dataclass(frozen=True)
class KaggleDownloadAuthority:
    """Separate future authority not consumed by source qualification."""

    competition_slug: str
    qualification_record_digest: str
    destination_root: str
    maximum_download_bytes: int
    authorized_by: str
    authorize_download: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "competition_slug", safe_slug(self.competition_slug))
        require_sha256(self.qualification_record_digest, "qualification_record_digest")
        if not all(
            isinstance(value, str) and value.strip()
            for value in (self.destination_root, self.authorized_by)
        ):
            raise SourceQualificationError(
                "download authority needs destination_root and authorized_by"
            )
        if (
            isinstance(self.maximum_download_bytes, bool)
            or not isinstance(self.maximum_download_bytes, int)
            or self.maximum_download_bytes < 1
        ):
            raise SourceQualificationError(
                "maximum_download_bytes must be a positive integer"
            )
        if not isinstance(self.authorize_download, bool):
            raise SourceQualificationError("authorize_download must be Boolean")


@dataclass(frozen=True)
class SourceQualificationRequest:
    """One exact qualification campaign over selected preflight members."""

    run_id: str
    expected_preflight_report_digest: str
    expected_population_digest: str
    competition_slugs: tuple[str, ...]
    as_of: str
    paths: QualificationPathBudget
    bytes: QualificationByteBudget
    privacy: QualificationPrivacyPolicy
    authority: SourceQualificationAuthority
    legal_reviews: tuple[HumanLegalReview, ...] = ()
    evaluator_reviews: tuple[IndependentEvaluatorReview, ...] = ()
    timeout_seconds: int = 60
    require_external_model_permission: bool = True

    def __post_init__(self) -> None:
        from loop_engine.core.run_history_paths import (
            RunHistoryIntegrityError,
            validated_run_id,
        )

        try:
            validated_run_id(self.run_id)
        except RunHistoryIntegrityError as exc:
            raise SourceQualificationError(str(exc)) from exc
        require_sha256(
            self.expected_preflight_report_digest,
            "expected_preflight_report_digest",
        )
        require_sha256(self.expected_population_digest, "expected_population_digest")
        for name, expected_type in (
            ("paths", QualificationPathBudget),
            ("bytes", QualificationByteBudget),
            ("privacy", QualificationPrivacyPolicy),
            ("authority", SourceQualificationAuthority),
        ):
            if not isinstance(getattr(self, name), expected_type):
                raise SourceQualificationError(
                    f"{name} must be {expected_type.__name__}"
                )
        if not isinstance(self.competition_slugs, tuple):
            raise SourceQualificationError("competition_slugs must be a tuple")
        slugs = tuple(safe_slug(item) for item in self.competition_slugs)
        if not slugs or len(slugs) != len(set(slugs)):
            raise SourceQualificationError(
                "competition_slugs must be a non-empty unique tuple"
            )
        object.__setattr__(self, "competition_slugs", slugs)
        utc_datetime(self.as_of, "as_of")
        if (
            isinstance(self.timeout_seconds, bool)
            or not isinstance(self.timeout_seconds, int)
            or self.timeout_seconds < 1
        ):
            raise SourceQualificationError("timeout_seconds must be positive")
        if not isinstance(self.require_external_model_permission, bool):
            raise SourceQualificationError(
                "require_external_model_permission must be Boolean"
            )
        for name, values in (
            ("legal_reviews", self.legal_reviews),
            ("evaluator_reviews", self.evaluator_reviews),
        ):
            if not isinstance(values, tuple):
                raise SourceQualificationError(f"{name} must be a tuple")
            expected_type = (
                HumanLegalReview
                if name == "legal_reviews"
                else IndependentEvaluatorReview
            )
            if any(not isinstance(item, expected_type) for item in values):
                raise SourceQualificationError(
                    f"{name} must contain only {expected_type.__name__}"
                )
            review_slugs = [item.competition_slug for item in values]
            if len(review_slugs) != len(set(review_slugs)):
                raise SourceQualificationError(f"{name} has duplicate slugs")


@dataclass(frozen=True)
class PageCommandResult:
    """One physical response from the read-only Kaggle pages command."""

    argv: tuple[str, ...]
    returncode: int
    stdout: bytes = b""
    stderr: bytes = b""

    def __post_init__(self) -> None:
        if not isinstance(self.argv, tuple) or any(
            not isinstance(item, str) for item in self.argv
        ):
            raise SourceQualificationError("page command argv must be a text tuple")
        if isinstance(self.returncode, bool) or not isinstance(self.returncode, int):
            raise SourceQualificationError("page command returncode must be an integer")
        if not isinstance(self.stdout, bytes) or not isinstance(self.stderr, bytes):
            raise SourceQualificationError("page command streams must be bytes")


@dataclass(frozen=True)
class QualificationRunResult:
    """Saved campaign record plus its independent Run History report."""

    record: dict
    run_history_path: str
    run_history_head_digest: str
    run_history_chain: dict
    run_history_events: int


@dataclass(frozen=True)
class ResolvedQualificationPaths:
    workspace_root: Path
    preflight_report: Path
    artifact_root: Path
    run_history_root: Path
    output_record: Path


def _reject_symlink_chain(workspace: Path, candidate: Path, label: str) -> None:
    current = candidate
    while current != workspace:
        if current.exists() and current.is_symlink():
            raise SourceQualificationError(f"{label} cannot use a symlink")
        if current.parent == current:
            break
        current = current.parent


def _confined_path(
    workspace: Path, raw_value: str, label: str, maximum_characters: int
) -> Path:
    if len(raw_value) > maximum_characters:
        raise SourceQualificationError(f"{label} exceeds the path budget")
    unresolved = Path(raw_value).expanduser()
    if unresolved.exists() and unresolved.is_symlink():
        raise SourceQualificationError(f"{label} cannot be a symlink")
    resolved = unresolved.resolve()
    if resolved == workspace or workspace not in resolved.parents:
        raise SourceQualificationError(f"{label} must remain below workspace_root")
    _reject_symlink_chain(workspace, unresolved.absolute(), label)
    return resolved


def resolve_paths(request: SourceQualificationRequest) -> ResolvedQualificationPaths:
    path_budget = request.paths
    root_source = Path(path_budget.workspace_root).expanduser()
    if len(path_budget.workspace_root) > path_budget.maximum_path_characters:
        raise SourceQualificationError("workspace_root exceeds the path budget")
    if root_source.exists() and root_source.is_symlink():
        raise SourceQualificationError("workspace_root cannot be a symlink")
    workspace = root_source.resolve()
    resolved = ResolvedQualificationPaths(
        workspace_root=workspace,
        preflight_report=_confined_path(
            workspace,
            path_budget.preflight_report_path,
            "preflight_report_path",
            path_budget.maximum_path_characters,
        ),
        artifact_root=_confined_path(
            workspace,
            path_budget.private_artifact_root,
            "private_artifact_root",
            path_budget.maximum_path_characters,
        ),
        run_history_root=_confined_path(
            workspace,
            path_budget.run_history_root,
            "run_history_root",
            path_budget.maximum_path_characters,
        ),
        output_record=_confined_path(
            workspace,
            path_budget.output_record_path,
            "output_record_path",
            path_budget.maximum_path_characters,
        ),
    )
    concrete = (
        resolved.preflight_report,
        resolved.artifact_root,
        resolved.run_history_root,
        resolved.output_record,
    )
    for left_index, left in enumerate(concrete):
        for right in concrete[left_index + 1 :]:
            if left == right or left in right.parents or right in left.parents:
                raise SourceQualificationError(
                    "qualification evidence paths must be disjoint"
                )
    authority = request.authority
    exact_pairs = (
        (authority.preflight_read_path, resolved.preflight_report, "preflight read"),
        (
            authority.private_artifact_write_root,
            resolved.artifact_root,
            "artifact write",
        ),
        (authority.run_history_write_root, resolved.run_history_root, "history write"),
        (
            authority.output_record_write_path,
            resolved.output_record,
            "record write",
        ),
    )
    for raw, actual, label in exact_pairs:
        if Path(raw).expanduser().resolve() != actual:
            raise PermissionError(f"{label} path is not exactly authorized")
    if tuple(authority.page_read_slugs) != tuple(request.competition_slugs):
        raise PermissionError("page read authority does not match selected slugs")
    for name in (
        "allow_preflight_read",
        "allow_network_page_reads",
        "allow_kaggle_cli_command_execution",
        "allow_kaggle_credential_access",
        "allow_private_artifact_writes",
        "allow_run_history_write",
        "allow_output_record_write",
    ):
        if getattr(authority, name) is not True:
            raise PermissionError(f"qualification requires {name}=True")
    expected_history = resolved.run_history_root / request.run_id
    if expected_history.exists() or expected_history.is_symlink():
        raise FileExistsError(
            f"Run History destination already exists: {expected_history}"
        )
    if resolved.output_record.exists() or resolved.output_record.is_symlink():
        raise FileExistsError(
            f"qualification record already exists: {resolved.output_record}"
        )
    return resolved


def page_command(slug: str) -> tuple[str, ...]:
    return (
        "kaggle",
        "competitions",
        "pages",
        safe_slug(slug),
        "--content",
        "--format",
        "json",
    )


def validate_page_command(argv: tuple[str, ...], slug: str) -> None:
    if argv != page_command(slug):
        raise SourceQualificationError("page runner received an unexpected command")
    forbidden = {"download", "submit", "submissions", "leaderboard"}
    if forbidden.intersection(argv):
        raise SourceQualificationError(
            "qualification cannot execute a write or download"
        )


def verified_preflight(
    content: bytes, request: SourceQualificationRequest
) -> tuple[dict, dict[str, dict], dict[str, dict]]:
    try:
        report = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SourceQualificationError("preflight report is unreadable JSON") from exc
    if (
        not isinstance(report, dict)
        or report.get("record_type") != PREFLIGHT_REPORT_TYPE
    ):
        raise SourceQualificationError("preflight report has the wrong record type")
    stored_report_digest = str(report.get("report_digest") or "")
    report_body = dict(report)
    report_body.pop("report_digest", None)
    calculated_report_digest = digest(report_body)
    if stored_report_digest != calculated_report_digest:
        raise SourceQualificationError("preflight report digest does not match")
    if stored_report_digest != request.expected_preflight_report_digest:
        raise SourceQualificationError("preflight report is not the expected report")
    population = report.get("population")
    if (
        not isinstance(population, dict)
        or population.get("record_type") != PREFLIGHT_POPULATION_TYPE
    ):
        raise SourceQualificationError("preflight population is missing")
    population_body = {
        key: population.get(key)
        for key in (
            "record_type",
            "group",
            "sort_by",
            "page_size",
            "target_competitions",
            "selected",
            "list_failures",
        )
    }
    # Older v1 populations did not have a search field. Preserve that exact
    # digest shape; new populations bind the filter even when it is empty.
    if "search" in population:
        search = population["search"]
        if (type(search) is not str or search != search.strip()
                or any(ord(character) < 32 or ord(character) == 127
                       for character in search)):
            raise SourceQualificationError("preflight search filter is invalid")
        population_body["search"] = search
    calculated_population_digest = digest(population_body)
    if population.get("population_digest") != calculated_population_digest:
        raise SourceQualificationError("preflight population digest does not match")
    if calculated_population_digest != request.expected_population_digest:
        raise SourceQualificationError(
            "preflight population is not the expected population"
        )
    selected_rows = population.get("selected")
    if not isinstance(selected_rows, list):
        raise SourceQualificationError("preflight selected population is not a list")
    selected: dict[str, dict] = {}
    for row in selected_rows:
        if not isinstance(row, dict):
            raise SourceQualificationError("preflight population row is not an object")
        slug = safe_slug(row.get("slug"))
        if slug in selected:
            raise SourceQualificationError("preflight population has duplicate slugs")
        selected[slug] = row
    if any(slug not in selected for slug in request.competition_slugs):
        raise SourceQualificationError(
            "requested competition is outside the exact preflight population"
        )
    probes: dict[str, dict] = {}
    for probe in report.get("probes", ()):
        if not isinstance(probe, dict):
            raise SourceQualificationError("preflight probe is not an object")
        slug = safe_slug(probe.get("slug"))
        if slug in probes:
            raise SourceQualificationError("preflight has duplicate probe slugs")
        probes[slug] = probe
    if any(slug not in probes for slug in request.competition_slugs):
        raise SourceQualificationError("preflight is missing a selected probe")
    return report, selected, probes


__all__ = [
    "DOWNLOAD_PLAN_TYPE",
    "EVALUATOR_CANDIDATE_TYPE",
    "PREFLIGHT_POPULATION_TYPE",
    "PREFLIGHT_REPORT_TYPE",
    "QUALIFICATION_CAMPAIGN_TYPE",
    "QUALIFICATION_RECORD_TYPE",
    "QUALIFICATION_STATES",
    "SAFE_PAGE_KINDS",
    "SUCCESSFUL_PREFLIGHT_STATUSES",
    "HumanLegalReview",
    "IndependentEvaluatorReview",
    "KaggleDownloadAuthority",
    "PageCommandResult",
    "QualificationByteBudget",
    "QualificationPathBudget",
    "QualificationPrivacyPolicy",
    "QualificationRunResult",
    "ResolvedQualificationPaths",
    "SourceQualificationAuthority",
    "SourceQualificationError",
    "SourceQualificationRequest",
    "bytes_digest",
    "canonical",
    "digest",
    "page_command",
    "resolve_paths",
    "safe_slug",
    "utc_datetime",
    "validate_page_command",
    "verified_preflight",
]
