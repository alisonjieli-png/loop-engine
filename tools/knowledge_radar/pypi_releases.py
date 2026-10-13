"""Offline PyPI Simple JSON projection with separate version and file identity.

This parser makes no network calls. New versions require a caller-supplied
baseline and do not establish changed capabilities or installation compatibility.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import hashlib
import json
import re
from urllib.parse import urlsplit

REQUEST_RECORD_TYPE = "pypi_index_read_request/v1"
OBSERVATION_RECORD_TYPE = "pypi_project_release_observation/v1"
FILE_RECORD_TYPE = "pypi_distribution_file/v1"
ALLOWED_HOST = "pypi.org"
SIMPLE_ACCEPT = "application/vnd.pypi.simple.v1+json"
MAXIMUM_RESPONSE_BYTES = 1048576
MAXIMUM_FILES_INSPECTED = 1000
MAXIMUM_RELEASES_RETAINED = 60
_PEP503_NAME = re.compile(r"[a-z0-9](?:[a-z0-9._-]{0,126}[a-z0-9])?\Z")
_VERSION = re.compile(r"[A-Za-z0-9][A-Za-z0-9._!+-]{0,63}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_WHEEL_RE = re.compile(
    r"^(?P<dist>[A-Za-z0-9_]+)-(?P<ver>[A-Za-z0-9._!+-]+)"
    r"(?:-(?P<build>[0-9][A-Za-z0-9._]*))?-(?P<py>[A-Za-z0-9._]+)"
    r"-(?P<abi>[A-Za-z0-9._]+)-(?P<plat>[A-Za-z0-9._]+)\.whl$"
)
_SDIST_RE = re.compile(r"^(?P<dist>[A-Za-z0-9_.-]+)-(?P<ver>[0-9][A-Za-z0-9._!+-]*)\.(?:tar\.gz|zip)$")
_STEERING = re.compile(
    r"(?i)\b(?:ignore|disregard|override)\b.{0,40}\b(?:previous|prior|all)\b.{0,20}\b(?:instructions?|rules?)\b"
    r"|\b(?:grant|authorize)\b.{0,30}\b(?:permissions?|network|execution)\b"
)


class PyPIReadError(ValueError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def normalize_project_name(name: str) -> str:
    if not isinstance(name, str):
        raise PyPIReadError("pypi_project_name_invalid")
    lowered = name.strip().lower()
    if not _PEP503_NAME.fullmatch(lowered):
        raise PyPIReadError("pypi_project_name_invalid")
    return re.sub(r"[-_.]+", "-", lowered)


def _require(condition: bool, code: str = "pypi_response_invalid") -> None:
    if not condition:
        raise PyPIReadError(code)


def _safe_url(value: object) -> str:
    _require(isinstance(value, str) and 0 < len(value) <= 512)
    parsed = urlsplit(value)
    _require(
        parsed.scheme == "https"
        and parsed.hostname in ("files.pythonhosted.org", "pypi.org")
        and parsed.username is None
        and parsed.password is None
        and parsed.port is None
        and not parsed.query
        and not parsed.fragment
    )
    return value


@dataclass(frozen=True)
class PyPIRequest:
    project: str
    pinned_version: str | None = None
    target_platform: str = "manylinux"
    max_releases: int = 20

    def __post_init__(self) -> None:
        normalized = normalize_project_name(self.project)
        object.__setattr__(self, "project", normalized)
        if self.pinned_version is not None:
            _require(
                isinstance(self.pinned_version, str) and bool(_VERSION.fullmatch(self.pinned_version)),
                "pypi_version_invalid",
            )
        _require(
            isinstance(self.target_platform, str) and bool(re.fullmatch(r"[a-z0-9_.-]{2,32}", self.target_platform)),
            "pypi_platform_invalid",
        )
        _require(
            type(self.max_releases) is int and 1 <= self.max_releases <= MAXIMUM_RELEASES_RETAINED,
            "pypi_limit_invalid",
        )

    @property
    def endpoint_url(self) -> str:
        return f"https://{ALLOWED_HOST}/simple/{self.project}/"

    def plan(self) -> dict[str, object]:
        return {
            "record_type": REQUEST_RECORD_TYPE,
            "project": self.project,
            "pinned_version": self.pinned_version,
            "target_platform": self.target_platform,
            "max_releases": self.max_releases,
            "endpoint_url": self.endpoint_url,
            "accept_header": SIMPLE_ACCEPT,
            "network_requests_dispatched": 0,
            "effects_granted": [],
        }


@dataclass(frozen=True)
class DistributionFile:
    filename: str
    version: str
    package_kind: str
    python_tag: str
    abi_tag: str
    platform_tag: str
    sha256: str
    url: str
    requires_python: str | None
    yanked: bool

    def record(self) -> dict[str, object]:
        return {
            "record_type": FILE_RECORD_TYPE,
            "filename": self.filename,
            "version": self.version,
            "package_kind": self.package_kind,
            "python_tag": self.python_tag,
            "abi_tag": self.abi_tag,
            "platform_tag": self.platform_tag,
            "sha256": self.sha256,
            "url": self.url,
            "requires_python": self.requires_python,
            "yanked": self.yanked,
        }


def _parse_filename(filename: str, project: str) -> tuple[str, str, str, str, str]:
    wheel = _WHEEL_RE.fullmatch(filename)
    if wheel:
        _require(normalize_project_name(wheel.group("dist")) == project, "pypi_filename_project_mismatch")
        return (
            wheel.group("ver"),
            "bdist_wheel",
            wheel.group("py"),
            wheel.group("abi"),
            wheel.group("plat"),
        )
    sdist = _SDIST_RE.fullmatch(filename)
    if sdist:
        _require(normalize_project_name(sdist.group("dist")) == project, "pypi_filename_project_mismatch")
        return (sdist.group("ver"), "sdist", "source", "none", "any")
    raise PyPIReadError("pypi_filename_unrecognized")


def parse_simple_index(
    body: bytes,
    request: PyPIRequest,
    *,
    observed_on: str,
    known_files_by_version: dict[str, list[str]] | None = None,
) -> dict[str, object]:
    """Parse a PyPI Simple Index v1 JSON response and separate new releases from platform wheels."""
    _require(type(body) is bytes and 0 < len(body) <= MAXIMUM_RESPONSE_BYTES, "pypi_response_byte_limit")
    _require(
        isinstance(observed_on, str) and bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", observed_on)),
        "pypi_observed_date_invalid",
    )
    try:
        date.fromisoformat(observed_on)
    except ValueError:
        raise PyPIReadError("pypi_observed_date_invalid") from None
    try:
        data = json.loads(body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise PyPIReadError("pypi_json_invalid") from None

    _require(type(data) is dict, "pypi_json_invalid")
    meta = data.get("meta")
    _require(type(meta) is dict and isinstance(meta.get("api-version"), str)
             and bool(re.fullmatch(r"1\.\d+", meta["api-version"])), "pypi_api_version_unsupported")
    serial = meta.get("_last-serial")
    if serial is not None:
        _require(type(serial) is int and serial >= 0, "pypi_serial_invalid")

    project_name = normalize_project_name(str(data.get("name", "")))
    _require(project_name == request.project, "pypi_project_mismatch")

    files_raw = data.get("files")
    _require(type(files_raw) is list and len(files_raw) <= MAXIMUM_FILES_INSPECTED, "pypi_files_limit_exceeded")

    parsed_files: list[DistributionFile] = []
    by_version: dict[str, list[DistributionFile]] = {}
    excluded_yanked = 0

    for row in files_raw:
        _require(type(row) is dict, "pypi_file_row_invalid")
        filename = row.get("filename")
        _require(isinstance(filename, str) and 1 <= len(filename) <= 255 and not _STEERING.search(filename))
        hashes = row.get("hashes")
        _require(type(hashes) is dict and isinstance(hashes.get("sha256"), str) and bool(_SHA256.fullmatch(hashes["sha256"].lower())))
        sha256_hex = hashes["sha256"].lower()
        url = _safe_url(row.get("url"))
        requires_python = row.get("requires-python")
        if requires_python is not None:
            _require(isinstance(requires_python, str) and len(requires_python) <= 128 and not _STEERING.search(requires_python))
        yanked_raw = row.get("yanked", False)
        _require(type(yanked_raw) in (bool, str), "pypi_yanked_invalid")
        yanked = bool(yanked_raw)
        if yanked:
            excluded_yanked += 1
            continue
        version, pkg_kind, py_tag, abi_tag, plat_tag = _parse_filename(filename, request.project)
        _require(filename not in {item.filename for item in parsed_files}, "pypi_duplicate_filename")
        dist_file = DistributionFile(
            filename=filename,
            version=version,
            package_kind=pkg_kind,
            python_tag=py_tag,
            abi_tag=abi_tag,
            platform_tag=plat_tag,
            sha256=sha256_hex,
            url=url,
            requires_python=requires_python,
            yanked=yanked,
        )
        parsed_files.append(dist_file)
        by_version.setdefault(version, []).append(dist_file)

    # Simple API arrays are unordered. Lexical selection is deterministic, not
    # a newest-release or semantic-version claim; legacy versions may exist.
    all_versions = sorted(by_version)
    retained_versions = all_versions[:request.max_releases]
    known = {} if known_files_by_version is None else known_files_by_version
    _require(type(known) is dict, "pypi_baseline_invalid")
    for version, names in known.items():
        _require(isinstance(version, str) and type(names) is list
                 and all(isinstance(name, str) for name in names), "pypi_baseline_invalid")

    newly_observed_versions: list[str] = []
    distribution_updates: list[dict[str, object]] = []
    target_platform_tag_candidates: list[str] = []

    for ver in retained_versions:
        v_files = by_version[ver]
        has_compatible = any(
            f.package_kind == "bdist_wheel" and (f.platform_tag == "any"
            or request.target_platform in f.platform_tag
            )
            for f in v_files
        )
        if has_compatible:
            target_platform_tag_candidates.append(ver)

        if ver not in known and known_files_by_version is not None:
            newly_observed_versions.append(ver)
        elif ver in known:
            previous_names = set(known[ver])
            added_files = [f for f in v_files if f.filename not in previous_names]
            if added_files:
                # Another file for a known version does not prove a capability change.
                distribution_updates.append(
                    {
                        "version": ver,
                        "classification": "additional_distribution_for_known_version",
                        "added_filenames": [f.filename for f in added_files],
                        "matches_target_platform": any(
                            f.platform_tag == "any" or request.target_platform in f.platform_tag
                            for f in added_files
                        ),
                    }
                )

    return {
        "record_type": OBSERVATION_RECORD_TYPE,
        "project": request.project,
        "pinned_version": request.pinned_version,
        "target_platform": request.target_platform,
        "observed_on": observed_on,
        "serial_marker": serial,
        "response_sha256": hashlib.sha256(body).hexdigest(),
        "response_bytes": len(body),
        "total_non_yanked_versions": len(all_versions),
        "excluded_yanked_files": excluded_yanked,
        "retained_versions": retained_versions,
        "selection_order": "lexical_not_release_chronology",
        "selection_complete": len(retained_versions) == len(all_versions),
        "baseline_supplied": known_files_by_version is not None,
        "newly_observed_versions": newly_observed_versions,
        "distribution_updates": distribution_updates,
        "target_platform_tag_candidates": target_platform_tag_candidates,
        "installation_compatibility_checked": False,
        "capability_change_checked": False,
        "distribution_files": [
            f.record() for ver in retained_versions for f in by_version[ver]
        ],
        "effects_granted": [],
        "automatic_install_authorized": False,
    }
