"""Build the record behind the staff Systems view from the release, catalogue and edge records in this repository.

Kind: development generator. Roadmap S-6.35.11. The owner asked for an internal reference of live systems with no
internal notes; on October 14, 2026 another harness served invented figures and unmeasured pass labels at
systems.baltor.ai instead. This record holds only facts that a record in this repository states, and the service shows
it to signed-in staff at /admin/systems beside what the running service measures at the moment it is read.

It reads, and reads nothing else:

- the application release records, artifacts/architecture-audit-2026-09-19/pilot-release-*.json
  (pilot_release_record/v1 and deployment_evidence/v1), and the copies in artifacts/release-*/release.json for a
  release that has no record of its own in that folder (pilot_release_record/v2 for releases 45, 46 and 48);
- the check reports a release record points to: the files its after_release.reports list names, its evidence_folder,
  and the release folder whose release.json names the same release;
- the current deployment section of docs/architecture/MVP-CLIENT-SERVER.md, compared field by field with the newest
  release record;
- the catalogue publication records (catalogue_publication_evidence/v1, catalogue_publication_record/v1 and
  catalogue_release_activation_record/v1) and the Community catalogue release records with their check reports;
- the edge measurement records under artifacts/cloudflare-*/.

It writes src/loop_engine/core/service_runtime/systems_view.json, checked against systems_view.schema.json beside it.
loop_engine.core.service_runtime.systems_view reads that record; the service serves it only through the staff route.

The reading rules, each applied the same way to every record:

- A result state is one of passed, failed, pending, skipped and unknown, and the five are never merged.
- A recorded word becomes a state only through WORD_STATES. Any other word is unknown, never passed.
- A count of passed checks becomes a state only beside its own total (or planned, checked or executed count) in the
  same object: equal is passed, smaller is failed. A count without its total, or a null, is unknown, unless the same
  object also records an explicit verdict, which then decides.
- A count whose name begins with first, initial, repeat, final or followup belongs to that attempt and has its own row.
- In the live checks of deployment_evidence/v1 a list of two whole numbers is [passed, total]; release 30 explains its
  [6, 8] as two failed checks. In the early after_release blocks a sentence stating "N of M" is read by those counts.
- A true or false recorded under a name that says passed, confirmed, matches or detected is passed or failed.
- A count of problems, errors or failures is passed at zero and failed above it.
- An object's state is the worst of its readings, in the order failed, pending, skipped, unknown, passed.
- A list of failed attempts gives one failed row for each attempt; no attempt is dropped for a later success.
- The environment of a row is the host it names, or what the record's own field names say (live, local, edge), or
  "not stated in the record". A row whose environment is not stated is never shown as production verification.
- Every number in the output is copied from the record its row cites. Nothing is added, estimated or projected.
- A recorded address keeps its host and path without its scheme, and no email address is kept at all.

Usage:

    PYTHONPATH=src python tools/build_systems_view.py            # write the record
    PYTHONPATH=src python tools/build_systems_view.py --check    # exit 1 when the committed record is stale
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

RECORD_TYPE = "service_systems_view/v1"
GENERATED_BY = "tools/build_systems_view.py"
SERVICE_RUNTIME = Path("src/loop_engine/core/service_runtime")
OUTPUT = ROOT / SERVICE_RUNTIME / "systems_view.json"
SCHEMA = ROOT / SERVICE_RUNTIME / "systems_view.schema.json"
AUDIT = "artifacts/architecture-audit-2026-09-19"
RELEASE_RECORDS = AUDIT + "/pilot-release-*.json"
RELEASE_FOLDERS = "artifacts/release-[0-9]*"
CURRENT_DEPLOYMENT = "docs/architecture/MVP-CLIENT-SERVER.md"
CURRENT_DEPLOYMENT_HEADING = "## Current deployment"
COMMUNITY_RELEASES = "artifacts/community-release-*"
CATALOGUE_PUBLICATION_FOLDERS = (AUDIT, "artifacts/catalogue-publication-*")
EDGE_MEASUREMENTS = "artifacts/cloudflare-*/site-edge*.json"

STATES = ("passed", "failed", "pending", "skipped", "unknown")
#: The worst reading decides an object's state.
SEVERITY = {"passed": 0, "unknown": 1, "skipped": 2, "pending": 3, "failed": 4}
#: The release record versions read. Any other version is refused rather than guessed at.
RELEASE_VERSIONS = ("pilot_release_record/v1", "deployment_evidence/v1", "pilot_release_record/v2")
CATALOGUE_PUBLICATION_VERSIONS = ("catalogue_publication_evidence/v1", "catalogue_publication_record/v1",
                                  "catalogue_release_activation_record/v1")
#: The report of a deployment attempt that failed; it ran against the release's own application.
FAILED_DEPLOYMENT_REPORT = "failed_deployment_attempt/v1"
#: Check reports a release record may point to, and whether each one says where it ran.
REPORT_VERSIONS = {
    "hosted_website_acceptance/v1": "Hosted website acceptance",
    "hosted_catalogue_disclosure_check/v1": "Hosted catalogue disclosure check",
    "hosted_service_transport_qualification/v1": "Hosted service transport qualification",
    "live_account_journeys/v1": "Live account journeys",
    "live_community_retrieval_check/v2": "Live Community retrieval check",
    "live_site_for_people_check/v1": "Live site check for people",
    "service_workspace_browser_checks/v1": "Local browser checks",
    "service_workspace_browser_checks/v2": "Local browser checks",
    "bounded_final_ui_layout_review/v1": "Local layout review",
    FAILED_DEPLOYMENT_REPORT: "Failed deployment attempt",
}
#: Report versions that ran on the engineering machine or in continuous integration, as their record type says.
LOCAL_REPORT_VERSIONS = ("service_workspace_browser_checks/v1", "service_workspace_browser_checks/v2",
                         "bounded_final_ui_layout_review/v1")
EDGE_MEASUREMENT_VERSIONS = ("site_edge_measurement/v1", "site_edge_outage_measurement/v1")

#: Every recorded word this generator turns into a state. A word not listed here is unknown.
WORD_STATES = {
    "success": "passed", "passed": "passed", "passing": "passed", "pass": "passed", "all passed": "passed",
    "complete": "passed", "completed": "passed", "published": "passed", "live_application_confirmed": "passed",
    "deployment_confirmed_by_get_only_reconciliation_exact_asset_readback_passed": "passed",
    "failure": "failed", "failed": "failed", "failed_readiness_gate": "failed",
    "failure_after_image_applied_due_to_grant_exec_deadline": "failed", "failed_before_provider_write": "failed",
    "upload_acknowledged_postcheck_failed_then_get_only_reconciled": "failed",
    "authority_step_refused_before_checkout_or_provider_effects": "failed",
    "completed_with_failures": "failed", "completed_with_retained_metadata_fetch_failures": "failed",
    "complete_coverage_with_unresolved_metadata_fetch_failures": "failed", "usage_limit_reached": "failed",
    "skipped": "skipped", "skipped_separately_gated": "skipped", "not_run_for_this_revision": "skipped",
    "not_run": "skipped", "not_requested": "skipped",
    "pending": "pending", "planned": "pending", "queued": "pending", "in_progress": "pending",
}
#: The fields that hold a recorded word about a result.
STATE_KEYS = ("conclusion", "result", "state", "status", "outcome", "workflow_conclusion")
#: True or false under one of these names is a result; any other true or false is a fact and is not read as one.
FLAG = re.compile(r"^(?:passed|all_passed|complete)$|(?:_passed|_confirmed|_matches|_detected|accounting_complete)$")
#: A count of problems, errors or failures.
PROBLEMS = re.compile(r"(?:^|_)(?:problems|errors|failures|findings)$")
#: A count of things that passed, were detected or were refused as expected, and the part of its name before that.
NUMERATOR = re.compile(r"^(?:(?P<base>.+)_)?(?P<word>passed|detected|refused)$")
NUMERATOR_FIRST = re.compile(r"^passed_(?P<base>.+)$")
#: Names whose prefix says which attempt a count belongs to.
ATTEMPT_PREFIXES = ("first", "initial", "repeat", "final", "followup")
#: Names that hold the reason an attempt failed, kept with its row.
REASON = re.compile(r"(?:^|_)(?:why|reason|cause|failure|error)$")
REASON_CHARACTERS = 320
#: Where an attempt's identity, time and source revision are recorded in an object.
ATTEMPT_FIELDS = ("attempt", "run", "deploy_run", "continuous_integration_run", "workflow_run", "final_attempt")
TIME_FIELDS = ("at", "observed_at", "checked_at", "started_at", "finished_at", "completed_at", "confirmed_at",
               "deployed_at", "recorded_at", "observed_on")
REVISION_FIELDS = ("revision", "source_revision")
#: Lists of attempts: the plain words of their rows, the state a row takes when its own words say nothing, and where
#: the attempts ran: RELEASE_ENVIRONMENT for the release's own application, a constant, or None for the field names.
RELEASE_ENVIRONMENT = "release"
ATTEMPT_LISTS = {
    "workflow_history": ("Guarded workflow run", "unknown", RELEASE_ENVIRONMENT),
    "failed_first_attempts": ("Earlier attempt", "failed", None),
    "failed_first_attempts_preserved": ("Earlier attempt", "failed", None),
    "deployment_attempts": ("Deployment attempt", "unknown", RELEASE_ENVIRONMENT),
    "edge_attempts": ("Edge deployment attempt", "unknown", "Cloudflare edge"),
    "service_check_attempts": ("Hosted service check attempt", "unknown", "production"),
    "retained_failed_attempts": ("Retained failed attempt", "failed", None),
    "retained_failures": ("Retained failed attempt", "failed", None),
    "retained_attempts": ("Retained earlier attempt", "unknown", None),
}
#: A first attempt kept beside the successor that passed: failed whatever its own words say.
PRESERVED_FIRST_ATTEMPT = re.compile(r"first_attempts?_preserved$")
#: Containers whose fields are separate checks side by side; elsewhere one object is one check.
FLAT_CONTAINERS = ("local_checks", "live_checks", "creative_checks", "after_release")
#: Top-level objects that are facts read by their own readers, or narrative, and hold no check of their own.
NOT_CHECKS = ("cloudflare", "catalogue", "catalogue_at_application_deployment", "catalogue_publication",
              "catalogue_release_published", "catalogue_release_after", "continuous_integration", "rollback",
              "host_transition", "allowance_reconciliation", "retention_decision", "advisory", "incident",
              "post_deployment_incident", "deployment_failure", "live_capabilities", "before_release",
              "public_good_policy", "initial_public_good_policy", "billing", "machine", "capacity", "operator")
#: Fields of a check object that only point at evidence; an object with nothing else holds no result.
EVIDENCE_ONLY = ("source_sha256", "evidence_scope", "published_artifact", "published_sha256", "transformation",
                 "private_evidence", "evidence_sha256", "scope", "limit", "record_type")
#: The root fields read by the release identity, workflow and gate readers, never again as checks.
RELEASE_FIELDS = ("ci_run", "ci_conclusion", "continuous_integration_run", "deploy_run", "deployment_workflow_run",
                  "deploy_workflow_conclusion", "deployment_gate_after", "deploy_setting_after",
                  "deployment_switch_after_release", "ci_live_model_job", "ci_successful_jobs", "ci_jobs_passed",
                  "ci_jobs_skipped", "ci_seconds")

# The environment of a row, read from the names of the fields that hold it.
PRODUCTION = "production"
LOCAL = "local or continuous integration"
EDGE = "Cloudflare edge"
NOT_STATED = "not stated in the record"
CONTINUOUS_INTEGRATION = "GitHub Actions continuous integration"
#: Field names that say a check read the deployed service, its hosts or its provider.
PRODUCTION_NAMES = re.compile(r"^(?:live|post_cutover|pulse|final_pulse|provider_readback|application_readback|"
                              r"independent_live|after_release|hosted_browser|agentfeeds_live|machine_readback|"
                              r"billing_readback|visitor|people|service_checks|catalogue_checks|public_route_checks|"
                              r"public_checks|public_hosts|public_addresses|hostnames)|_live(?:_|$)")
#: Field names that say a check ran on the engineering machine, in a container drill or in continuous integration.
LOCAL_NAMES = re.compile(r"^(?:local|offline|self_test|pre_push|planning|conformance|focused|service_smoke|"
                         r"exported_service|documentation|markdown|installed_wheel|clean_installed_wheel|hardcoding|"
                         r"fixture|tooling|scanner|public_runner|owning|container|browser_checks|browser_mutants|"
                         r"rollback_check|readme_offline|agentbriefs_local|source_and_profile|registry_profile|"
                         r"inherited_supply|combined_focused|final_queue|records_index)")
EDGE_NAMES = re.compile(r"^(?:edge|cloudflare)")
#: Field names of the guarded workflow's own steps, which ran against the release's application.
WORKFLOW_NAMES = re.compile(r"^(?:grant_step|billing_step|image_deploy|image_deployment|deployment_steps|"
                            r"failed_attempt|post_deployment|post_deploy)")
#: A host name of the services these records describe, with or without its scheme.
HOSTNAME = re.compile(r"^(?:https?://)?(?:[a-z0-9-]+\.)+(?:ai|si|dev|io|com|net|org|app|co|sh)$")
#: The words a row or entry of this record may never carry: the October 14 portal's projections and investor material.
FORBIDDEN = re.compile(r"\b(?:ARR|MRR|projections?|projected|forecasts?|investors?|revenue|runway|valuation)\b",
                       re.IGNORECASE)
#: An email address. Staff who read service diagnostics read no personal detail, so no row or entry may carry one.
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")

_PAIR_TEXT = re.compile(r"^(\d[\d,]*)\s*/\s*(\d[\d,]*)$")
_PAIR_WORD = re.compile(r"^passed_(\d+)_of_(\d+)$")
_OF = re.compile(r"\b(\d[\d,]*) of (\d[\d,]*)\b")
_HEX64 = re.compile(r"[0-9a-f]{64}")
_SCHEME = re.compile(r"\bhttps?://")


class BuildError(ValueError):
    """A record this generator cannot read without guessing, with the reason."""


#: Retired words of terminology.yaml that a record's field names still carry, and the word a label uses instead.
#: The row's pointer keeps the record's exact field name.
LABEL_WORDS = {"receipt": "record", "receipts": "records"}


def words(name) -> str:
    """A field name as plain words: live_redirect_supplement becomes Live redirect supplement."""
    text = " ".join(LABEL_WORDS.get(part.lower(), part)
                    for part in str(name).replace("_", " ").replace("-", " ").split())
    return text[:1].upper() + text[1:]


def bounded(text, limit=REASON_CHARACTERS) -> str:
    """A recorded sentence, cut at a space so that no number is split, with a mark where it was cut.

    An address in it keeps its host and path without the scheme, so the record names where a check ran and holds
    no endpoint of its own."""
    text = _SCHEME.sub("", " ".join(str(text).split()))
    if len(text) <= limit:
        return text
    cut = text.rfind(" ", 0, limit)
    return text[:cut if cut > 0 else limit] + " …"


def word_state(value) -> str:
    return WORD_STATES.get(str(value).strip().lower(), "unknown")


def worst(states) -> str:
    states = list(states)
    return max(states, key=SEVERITY.get) if states else "unknown"


def _integer(value) -> bool:
    return type(value) is int


def _count(text) -> int:
    return int(str(text).replace(",", ""))


def _pair_state(passed, total) -> str:
    if passed is None or total is None:
        return "unknown"
    if passed == total:
        return "passed"
    return "failed" if passed < total else "unknown"


def environment_of(segments, default=NOT_STATED) -> str:
    """The environment the names of a row's fields state, nearest first, or the default."""
    for segment in reversed([str(item) for item in segments]):
        if HOSTNAME.match(segment):
            return segment.split("://", 1)[-1]
        if PRODUCTION_NAMES.search(segment):
            return PRODUCTION
        if EDGE_NAMES.match(segment):
            return EDGE
        if WORKFLOW_NAMES.match(segment):
            return RELEASE_ENVIRONMENT
        if LOCAL_NAMES.match(segment):
            return LOCAL
    return default


def pointer(segments) -> str:
    return "".join("/" + str(item).replace("~", "~0").replace("/", "~1") for item in segments)


class Readings:
    """The results one object states, read by the rules above, kept in the order they were read.

    A reading that only says a value was not recorded is weak: it decides the state (unknown) when the object states
    nothing else, and it never outweighs a total, a verdict or a recorded word of the same object."""

    def __init__(self):
        self.strong, self.weak, self.observed = [], [], []

    def add(self, state, text, *, weak=False):
        (self.weak if weak else self.strong).append(state)
        self.observed.append(text)

    def extend(self, other):
        self.strong += other.strong
        self.weak += other.weak
        self.observed += other.observed

    @property
    def states(self):
        return self.strong or self.weak

    def __bool__(self):
        return bool(self.states)


def _group_of(key, flat):
    """The row a reading belongs to: its own name in a flat container, else the attempt its prefix names."""
    if flat:
        match = NUMERATOR.match(key) or NUMERATOR_FIRST.match(key)
        if match and match.group("base"):
            return match.group("base")
        for suffix in ("_total", "_planned", "_checked", "_executed", "_denominator"):
            if key.endswith(suffix):
                return key[:-len(suffix)]
        return key
    head = key.split("_", 1)[0]
    return head if head in ATTEMPT_PREFIXES and "_" in key else ""


def _denominator(value, base, word):
    """The total a count of passed checks is read against, from the same object, or None."""
    names = ([f"{base}_total", f"{base}_planned", f"{base}_checked", f"{base}_executed", base] if base
             else ["total", "executed", "planned", "planned_checks"])
    for name in names:
        if name in value and (value[name] is None or _integer(value[name])):
            return name
    return None


def read_object(value, *, flat=False, prose=False):
    """Every result one object states, grouped into rows: {group: Readings}, in the order the fields appear.

    With `prose`, a sentence that states counts as "N of M" is read by those counts, as the early release records
    state their checks after a release."""
    groups, paired, unpaired = {}, set(), []

    def reading(key):
        return groups.setdefault(_group_of(key, flat), Readings())

    for key, item in value.items():
        match = NUMERATOR.match(key)
        first = NUMERATOR_FIRST.match(key)
        if (match or first) and (item is None or _integer(item)):
            base = match.group("base") if match else None
            denominator = (_denominator(value, base or "", match.group("word")) if match
                           else (f"total_{first.group('base')}" if _integer(value.get(f"total_{first.group('base')}"))
                                 else None))
            if denominator is None:
                if item is None:
                    reading(key).add("unknown", f"{words(key)}: not recorded", weak=True)
                    paired.add(key)
                else:
                    unpaired.append(key)
                continue
            total = value[denominator]
            label = words(base or first.group("base")) if (base or first) else "Checks"
            if base in ATTEMPT_PREFIXES:
                label = "Checks"
            elif base and base.split("_", 1)[0] in ATTEMPT_PREFIXES:
                label = words(base.split("_", 1)[1])
            reading(key).add(_pair_state(item, total),
                             f"{label}: {'not recorded' if item is None else item} of "
                             f"{'not recorded' if total is None else total}", weak=item is None or total is None)
            paired.update((key, denominator))
    # A count named X beside X_total is read the same way, as release 62 keeps website_assertions.
    for key, item in value.items():
        if (key not in paired and _integer(item) and _integer(value.get(key + "_total"))
                and not NUMERATOR.match(key) and not PROBLEMS.search(key)):
            reading(key).add(_pair_state(item, value[key + "_total"]), f"{words(key)}: {item} of {value[key + '_total']}")
            paired.update((key, key + "_total"))
    # One count of passed checks without a total of its own is read against a plain total, when that is the only
    # reading the total can belong to.
    if len(unpaired) == 1 and _integer(value.get("total")) and "total" not in paired and "passed" not in value:
        key = unpaired.pop()
        base = (NUMERATOR.match(key) or NUMERATOR_FIRST.match(key)).group("base") or ""
        reading(key).add(_pair_state(value[key], value["total"]), f"{words(base)}: {value[key]} of {value['total']}")
        paired.update((key, "total"))
    for key in unpaired:
        reading(key).observed.append(f"{words(key)}: {value[key]}, no total recorded")
    for key, item in value.items():
        if key in paired:
            continue
        if isinstance(item, bool) and FLAG.search(key):
            reading(key).add("passed" if item else "failed", f"{words(key)}: {'true' if item else 'false'}")
        elif item is None and FLAG.search(key):
            reading(key).add("unknown", f"{words(key)}: not recorded", weak=True)
        elif _integer(item) and PROBLEMS.search(key):
            reading(key).add("passed" if item == 0 else "failed", f"{words(key)}: {item}")
        elif isinstance(item, str) and (key in STATE_KEYS or key.endswith("_conclusion")) and key not in RELEASE_FIELDS:
            reading(key).add(word_state(item), f"{words(key)}: {bounded(item, 160)}")
        elif key == "error" and isinstance(item, str) and item.strip():
            reading(key).add("failed", f"Error: {bounded(item, 160)}")
        elif isinstance(item, str) and (_PAIR_TEXT.match(item.strip()) or _PAIR_WORD.match(item.strip())):
            found = _PAIR_TEXT.match(item.strip()) or _PAIR_WORD.match(item.strip())
            reading(key).add(_pair_state(_count(found.group(1)), _count(found.group(2))),
                             f"{words(key)}: {found.group(1)} of {found.group(2)}")
        elif (flat and isinstance(item, list) and len(item) == 2 and all(_integer(part) for part in item)
              and 0 <= item[0] <= item[1]):
            # The live checks of deployment_evidence/v1 keep a result as [passed, total]; release 30's record
            # explains its [6, 8] as two failed checks. Elsewhere two numbers are not read as a result.
            reading(key).add(_pair_state(item[0], item[1]), f"{words(key)}: {item[0]} of {item[1]}")
        elif (isinstance(item, list) and len(item) > 2 and all(_integer(part) for part in item)
              and _integer(value.get(key + "_denominator"))):
            each = value[key + "_denominator"]
            reading(key).add(worst(_pair_state(part, each) for part in item),
                             f"{words(key)}: {', '.join(str(part) for part in item)}, each of {each}")
            paired.add(key + "_denominator")
        elif prose and isinstance(item, str) and _OF.search(item):
            counts = [(_count(passed), _count(total)) for passed, total in _OF.findall(item)]
            if all(passed <= total for passed, total in counts):
                reading(key).add(worst(_pair_state(passed, total) for passed, total in counts),
                                 f"{words(key)}: {bounded(item)}")
        elif isinstance(item, str) and REASON.search(key) and item.strip() and key != "error":
            reading(key).observed.append(f"{words(key)}: {bounded(item)}")
    return {group: found for group, found in groups.items() if found or found.observed}


def _first(value, names):
    for name in names:
        if name in value and value[name] not in (None, ""):
            return value[name]
    return None


class Builder:
    """Collects entries and rows from the records of one checkout."""

    def __init__(self, root: Path):
        self.root = root
        self.entries, self.rows, self.sources = [], [], {}

    # Files.

    def relative(self, path: Path) -> str:
        return path.resolve().relative_to(self.root.resolve()).as_posix()

    def read_json(self, path: Path, role: str):
        try:
            value = json.loads(path.read_text("utf-8"))
        except (OSError, ValueError) as error:
            raise BuildError(f"{self.relative(path)} is not readable JSON: {error}") from None
        self.source(path, role, value.get("record_type") if isinstance(value, dict) else None)
        return value

    def source(self, path: Path, role: str, record_type=None):
        name = self.relative(path)
        if name not in self.sources:
            self.sources[name] = {"path": name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "role": role,
                                  "record_type": record_type}

    def glob(self, pattern):
        return sorted(Path(item) for item in glob.glob(str(self.root / pattern)))

    # Rows.

    def row(self, entry, check, state, observed, *, where, segments=(), evidence, revision=None,
            revision_basis="release_record", attempt=None, at=None):
        if state not in STATES:
            raise BuildError(f"{evidence}{pointer(segments)}: the state {state!r} is not one of {STATES}")
        if where == RELEASE_ENVIRONMENT:
            where = entry["environment_or_host"]
        self.rows.append({"entry": entry["id"], "check": check, "state": state,
                          "observed": "; ".join(observed) if isinstance(observed, (list, tuple)) else observed,
                          "source_revision": revision if revision is not None else entry.get("source_revision"),
                          "revision_basis": revision_basis if revision is not None else "release_record",
                          "environment_or_host": where, "attempt": None if attempt is None else str(attempt),
                          "at": at, "evidence": evidence, "pointer": pointer(segments)})

    def object_rows(self, entry, label, value, segments, evidence, *, flat=False, where=None,
                    holds_one_check=False, prose=False):
        """The rows of one object, then of the objects and attempt lists inside it."""
        if not isinstance(value, dict):
            return
        place = where or environment_of(segments)
        groups = read_object(value, flat=flat, prose=prose)
        revision = _first(value, REVISION_FIELDS)
        attempt, at = _first(value, ATTEMPT_FIELDS), _first(value, TIME_FIELDS)
        evidence_only = set(value) <= set(EVIDENCE_ONLY)
        holds_objects = any(isinstance(item, (dict, list)) for item in value.values())
        if (holds_one_check and not any(found.states for found in groups.values()) and not evidence_only
                and not holds_objects):
            groups = {"": Readings()}
            groups[""].add("unknown", "No result field this reader can read; see the evidence record")
        for group, found in groups.items():
            if not found.states:
                found.add("unknown", "No total or verdict recorded", weak=True)
            title = label if not group or group in ATTEMPT_PREFIXES else f"{label} · {words(group).lower()}"
            this_place = place if not flat else where or environment_of([*segments, group])
            this_attempt = (f"{group} attempt" if group in ATTEMPT_PREFIXES else attempt)
            self.row(entry, title, worst(found.states), found.observed, where=this_place,
                     segments=segments, evidence=evidence, revision=revision,
                     revision_basis="row", attempt=this_attempt, at=at)
        for key, item in value.items():
            here = [*segments, key]
            if PRESERVED_FIRST_ATTEMPT.search(key) and isinstance(item, (str, dict)):
                text = item if isinstance(item, str) else " ".join(
                    f"{words(name)}: {part}" for name, part in item.items() if isinstance(part, str))
                self.row(entry, f"{label} · earlier attempt" if label else "Earlier attempt", "failed",
                         [bounded(text)], where=where or environment_of(here), segments=here,
                         evidence=evidence)
            elif isinstance(item, dict):
                if all(HOSTNAME.match(name) for name in item) and item:
                    for host, result in item.items():
                        self.host_rows(entry, f"{label} · {words(key).lower()}", host, result, [*here, host], evidence)
                else:
                    nested_flat = flat and (key in FLAT_CONTAINERS or any(
                        isinstance(part, list) and len(part) == 2 and all(_integer(each) for each in part)
                        for part in item.values()))
                    self.object_rows(entry, f"{label} · {words(key).lower()}" if label else words(key), item, here,
                                     evidence, flat=nested_flat, where=where)
            elif isinstance(item, list):
                self.list_rows(entry, label, key, item, here, evidence, where=where)

    def host_rows(self, entry, label, host, result, segments, evidence):
        """One row for one host's result. A value that states no result, such as an identifier, gives no row."""
        name = host.split("://", 1)[-1]
        if isinstance(result, dict):
            self.object_rows(entry, label, result, segments, evidence, where=name, holds_one_check=True)
            return
        found = Readings()
        if isinstance(result, str) and (_PAIR_TEXT.match(result.strip()) or _PAIR_WORD.match(result.strip())):
            readings = read_object({"checks": result})
        elif isinstance(result, list):
            readings = read_object({"checks": result}, flat=True)
        elif isinstance(result, str) and word_state(result) != "unknown":
            readings = read_object({"result": result})
        else:
            return
        for each in readings.values():
            found.extend(each)
        if not found.states:
            return
        self.row(entry, label, worst(found.states), found.observed, where=name, segments=segments,
                 evidence=evidence)

    def list_rows(self, entry, label, key, items, segments, evidence, *, where=None):
        known = ATTEMPT_LISTS.get(key)
        preserved = PRESERVED_FIRST_ATTEMPT.search(key)
        if not known and not preserved:
            return
        title, default, listed = known or ("Earlier attempt", "failed", None)
        title = f"{label} · {title.lower()}" if label else title
        for index, item in enumerate(items):
            here = [*segments, index]
            place = (entry["environment_or_host"] if listed == RELEASE_ENVIRONMENT else listed) or where \
                or environment_of(segments)
            if isinstance(item, str):
                self.row(entry, title, default, [bounded(item)], where=place, segments=here, evidence=evidence)
            elif isinstance(item, dict):
                found = Readings()
                for readings in read_object(item).values():
                    found.extend(readings)
                state = worst(found.states) if found.states else default
                if default == "failed":
                    state = "failed"
                observed = found.observed or [f"{words(name)}: {bounded(item[name])}" for name in item
                                              if isinstance(item[name], str) and REASON.search(name)]
                step = item.get("operation") or item.get("stage")
                self.row(entry, f"{title}: {words(step).lower()}" if isinstance(step, str) else title, state,
                         observed or ["No reason recorded"], where=place, segments=here, evidence=evidence,
                         revision=_first(item, REVISION_FIELDS), revision_basis="row",
                         attempt=_first(item, ATTEMPT_FIELDS), at=_first(item, TIME_FIELDS))

    # Application releases.

    def release_records(self):
        """Every application release record, with the copies kept in release folders, by Fly release number."""
        records = {}
        for path in self.glob(RELEASE_RECORDS):
            value = self.read_json(path, "application_release_record")
            if not isinstance(value, dict) or value.get("record_type") not in RELEASE_VERSIONS[:2]:
                raise BuildError(f"{self.relative(path)}: this generator reads {RELEASE_VERSIONS[:2]} in the audit folder")
            number = release_number(value)
            if not _integer(number):
                raise BuildError(f"{self.relative(path)} names no Fly release number")
            if number in records:
                raise BuildError(f"two release records name Fly release {number}")
            records[number] = {"path": path, "value": value, "copies": []}
        for folder in self.glob(RELEASE_FOLDERS):
            path = folder / "release.json"
            if not path.is_file():
                continue
            value = json.loads(path.read_text("utf-8"))
            if not isinstance(value, dict) or value.get("record_type") not in RELEASE_VERSIONS:
                raise BuildError(f"{self.relative(path)}: this generator reads {RELEASE_VERSIONS}")
            number = release_number(value)
            if number in records:
                self.source(path, "application_release_record_copy", value["record_type"])
                records[number]["copies"].append(path)
            else:
                self.source(path, "application_release_record", value["record_type"])
                records[number] = {"path": path, "value": value, "copies": []}
        return records

    def application_release(self, number, held):
        path, value = held["path"], held["value"]
        evidence = self.relative(path)
        app = _first(value, ("app", "application"))
        region = value.get("region")
        rollback = value.get("rollback") if isinstance(value.get("rollback"), dict) else {}
        rollback = {"release": _first(value, ("rollback_release", "rollback_fly_release")) or rollback.get("previous_release"),
                    "image": _first(value, ("rollback_image", "rollback_image_digest")) or rollback.get("previous_image")}
        entry = {"id": f"fly-release-{number}", "kind": "application_release", "title": f"Fly release {number}",
                 "number": number, "at": _first(value, ("deployed_at", "observed_at", "recorded_at")),
                 "source_revision": value.get("source_revision"), "source_tree": value.get("source_tree"),
                 "environment_or_host": (f"Fly application {app}" + (f" ({region})" if region else "")) if app
                 else "Fly application, name not recorded",
                 "image": _first(value, ("image", "image_digest")),
                 "rollback": rollback if any(item is not None for item in rollback.values()) else None,
                 "edge": edge_facts(value.get("cloudflare")),
                 "catalogue": catalogue_facts(value),
                 "evidence": evidence, "record_type": value["record_type"],
                 "also_recorded_in": [self.relative(copy) for copy in held["copies"]]}
        self.entries.append(entry)
        place = entry["environment_or_host"]
        integration = value.get("continuous_integration") if isinstance(value.get("continuous_integration"), dict) else {}
        run = _first(value, ("ci_run", "continuous_integration_run")) or integration.get("run")
        conclusion = value.get("ci_conclusion") or integration.get("conclusion")
        jobs = [f"{words(name)}: {value[name]}" for name in ("ci_successful_jobs", "ci_jobs_passed", "ci_jobs_skipped")
                if _integer(value.get(name))]
        self.row(entry, "Continuous integration of the release revision",
                 word_state(conclusion) if conclusion else "unknown",
                 [f"Conclusion: {conclusion}" if conclusion else "Conclusion not recorded", *jobs]
                 + ([] if run else ["Run not recorded"]),
                 where=CONTINUOUS_INTEGRATION,
                 segments=[name for name in ("ci_conclusion", "continuous_integration", "ci_run",
                                             "continuous_integration_run") if name in value][:1],
                 evidence=evidence, attempt=run)
        if isinstance(value.get("ci_live_model_job"), str):
            self.row(entry, "Continuous integration live model job", word_state(value["ci_live_model_job"]),
                     [f"Recorded as {value['ci_live_model_job']}"], where=CONTINUOUS_INTEGRATION,
                     segments=["ci_live_model_job"], evidence=evidence, attempt=run)
        deploy_run = _first(value, ("deploy_run", "deployment_workflow_run"))
        deployed = value.get("deploy_workflow_conclusion")
        # A record that lists each workflow run with its conclusion is read by that list instead.
        if deployed or deploy_run or not any(isinstance(value.get(name), list)
                                             for name in ("workflow_history", "deployment_attempts")):
            self.row(entry, "Guarded deployment workflow", word_state(deployed) if deployed else "unknown",
                     [f"Conclusion: {deployed}" if deployed else "Conclusion not recorded"]
                     + ([] if deploy_run else ["Run not recorded"]),
                     where=place,
                     segments=[name for name in ("deploy_workflow_conclusion", "deploy_run", "deployment_workflow_run")
                               if name in value][:1],
                     evidence=evidence, attempt=deploy_run, at=entry["at"])
        gate = gate_reading(value)
        if gate is not None:
            self.row(entry, "Deployment switch off after the release", gate[0], [gate[1]], where=place,
                     segments=[gate[2]], evidence=evidence, attempt=deploy_run)
        for key, item in value.items():
            if key in NOT_CHECKS or key in RELEASE_FIELDS:
                continue
            if isinstance(item, dict):
                flat = key in FLAT_CONTAINERS
                if key == "checks":
                    for name, check in item.items():
                        if isinstance(check, dict):
                            self.object_rows(entry, words(name), check, [key, name], evidence, holds_one_check=True)
                        elif isinstance(check, list):
                            self.list_rows(entry, "", name, check, [key, name], evidence)
                        else:
                            self.scalar_check(entry, name, check, [key, name], evidence)
                else:
                    self.object_rows(entry, words(key), item, [key], evidence, flat=flat,
                                     where=environment_of([key], None) if flat else None,
                                     prose=key == "after_release")
            elif isinstance(item, list):
                self.list_rows(entry, "", key, item, [key], evidence)
        self.root_checks(entry, value, evidence)
        self.edge_rows(entry, value, evidence)
        self.pointed_reports(entry, held, value)

    def scalar_check(self, entry, name, value, segments, evidence):
        """A check recorded as one word or number: its own word decides, else it is unknown."""
        if isinstance(value, bool) or value is None:
            return
        state = word_state(value) if isinstance(value, str) else "unknown"
        text = f"Recorded as {bounded(value, 200)}" if isinstance(value, str) else f"Recorded as {value}, no total"
        self.row(entry, words(name), state, [text], where=environment_of(segments), segments=segments,
                 evidence=evidence)

    def root_checks(self, entry, value, evidence):
        """The checks a release record keeps as plain fields beside its identity, one row for each name."""
        plain = {key: item for key, item in value.items() if key not in RELEASE_FIELDS
                 and not isinstance(item, (dict, list)) and key not in ("record_type",)}
        for group, found in read_object(plain, flat=True).items():
            if not found.states:
                found.add("unknown", "No total or verdict recorded")
            self.row(entry, words(group), worst(found.states), found.observed, where=environment_of([group]),
                     segments=[group if group in value else next((key for key in value if key.startswith(group)),
                                                                 group)],
                     evidence=evidence)

    def edge_rows(self, entry, value, evidence):
        block = value.get("cloudflare")
        if not isinstance(block, dict):
            return
        found = Readings()
        for readings in read_object(block).values():
            found.extend(readings)
        if not found.states:
            found.add("unknown", "No readback result recorded in this release record")
        worker = block.get("worker")
        self.row(entry, "Edge Worker deployment readback", worst(found.states), found.observed,
                 where=f"Cloudflare Worker {worker}" if worker else EDGE, segments=["cloudflare"],
                 evidence=evidence, revision=block.get("source_revision"), revision_basis="row",
                 attempt=block.get("worker_deployment"), at=_first(block, ("deployed_at", "provider_created_at")))

    def pointed_reports(self, entry, held, value):
        """The check reports this release record points to, each one an attempt with its own host and time."""
        folder = held["path"].parent
        paths = []
        after = value.get("after_release")
        if isinstance(after, dict) and isinstance(after.get("reports"), list):
            paths += [folder / name for name in after["reports"] if isinstance(name, str)]
        if isinstance(value.get("evidence_folder"), str):
            paths += sorted((self.root / value["evidence_folder"]).rglob("*.json"))
        for copy in held["copies"] + ([held["path"]] if held["path"].name == "release.json" else []):
            paths += sorted(path for path in copy.parent.rglob("*.json") if path != copy)
        seen = set()
        for path in paths:
            if path in seen or not path.is_file():
                continue
            seen.add(path)
            report = json.loads(path.read_text("utf-8"))
            if isinstance(report, dict) and report.get("record_type") in REPORT_VERSIONS:
                self.source(path, "check_report", report["record_type"])
                self.report_row(entry, path, report)

    def report_row(self, entry, path, report):
        record_type = report["record_type"]
        found = Readings()
        for readings in read_object({key: item for key, item in report.items() if not isinstance(item, (dict, list))}
                                    ).values():
            found.extend(readings)
        if record_type == FAILED_DEPLOYMENT_REPORT:
            found.add("failed", f"Failed step: {bounded(report.get('failed_step') or 'not recorded', 160)}")
        if not found.states:
            found.add("unknown", "No total or verdict recorded")
        origin = report.get("origin")
        place = (origin.split("://", 1)[-1] if isinstance(origin, str) and origin else
                 LOCAL if record_type in LOCAL_REPORT_VERSIONS else
                 RELEASE_ENVIRONMENT if record_type == FAILED_DEPLOYMENT_REPORT else NOT_STATED)
        self.row(entry, REPORT_VERSIONS[record_type], worst(found.states), found.observed, where=place,
                 evidence=self.relative(path), revision=_first(report, REVISION_FIELDS), revision_basis="row",
                 attempt=_first(report, ("deployment_workflow_run",)) or path.name,
                 at=_first(report, TIME_FIELDS))

    # Catalogue publications.

    def catalogue_publications(self):
        for pattern in CATALOGUE_PUBLICATION_FOLDERS:
            for folder in self.glob(pattern):
                for path in sorted(folder.glob("*.json")):
                    if path.name.startswith("pilot-release-"):
                        continue
                    try:
                        value = json.loads(path.read_text("utf-8"))
                    except ValueError:
                        continue
                    if isinstance(value, dict) and value.get("record_type") in CATALOGUE_PUBLICATION_VERSIONS:
                        self.source(path, "catalogue_publication_record", value["record_type"])
                        self.catalogue_publication(path, value)

    def catalogue_publication(self, path, value):
        evidence = self.relative(path)
        running = value.get("running_release") if isinstance(value.get("running_release"), dict) else {}
        receipt = value.get("publication_receipt") if isinstance(value.get("publication_receipt"), dict) else {}
        population = value.get("live_file_population") if isinstance(value.get("live_file_population"), dict) else {}
        status = value.get("catalogue_status_after") if isinstance(value.get("catalogue_status_after"), dict) else {}
        entry = {"id": f"publication-{path.stem}", "kind": "catalogue_publication",
                 "title": f"Catalogue publication {path.stem}",
                 "number": None,
                 "at": _first(value, ("confirmed_at", "observed_at", "recorded_on")),
                 "source_revision": _first(value, ("publisher_revision", "publisher_source_revision",
                                                   "operator_source_revision")) or running.get("source_revision"),
                 "source_tree": None,
                 "environment_or_host": "Catalogue served by the Fly application",
                 "image": running.get("image"),
                 "rollback": None, "edge": None,
                 "catalogue": {"release_id": _first(value, ("release_id", "active_release")) or receipt.get("release_id")
                               or status.get("active_release_id"),
                               "previous_release_id": _first(value, ("previous_release_id", "base_release")),
                               "packages": _first(value, ("items_after", "total_packages")) or population.get("packages"),
                               "distinct_files": _first(value, ("distinct_files_after", "total_distinct_files"))
                               or population.get("distinct_files"),
                               "application_release": _first(value, ("application_release", "app_release"))
                               or running.get("fly_release_version")},
                 "evidence": evidence, "record_type": value["record_type"], "also_recorded_in": []}
        self.entries.append(entry)
        if value.get("publisher_ci_run") or value.get("publisher_ci_conclusion"):
            conclusion = value.get("publisher_ci_conclusion")
            self.row(entry, "Continuous integration of the publisher revision",
                     word_state(conclusion) if conclusion else "unknown",
                     [f"Conclusion: {conclusion}" if conclusion else "Conclusion not recorded"],
                     where=CONTINUOUS_INTEGRATION, segments=["publisher_ci_conclusion"], evidence=evidence,
                     attempt=value.get("publisher_ci_run"))
        for key, item in value.items():
            if isinstance(item, dict) and key not in ("running_release", "live_file_population", "previous_population",
                                                      "source_bundle"):
                self.object_rows(entry, words(key), item, [key], evidence)
            elif isinstance(item, list):
                self.list_rows(entry, "", key, item, [key], evidence)

    def community_releases(self):
        sys.path.insert(0, str(self.root / "tools"))
        from build_public_status_pages import library_release
        for folder in self.glob(COMMUNITY_RELEASES):
            readme = folder / "README.md"
            if not readme.is_file():
                continue
            self.source(readme, "catalogue_release_record")
            text = readme.read_text("utf-8")
            release = library_release(readme)
            identity = next(iter(_HEX64.findall(_identity_text(text))), None)
            served = _served_count(text)
            entry = {"id": f"publication-{folder.name}", "kind": "catalogue_publication",
                     "title": f"Community catalogue release {release['number']}", "number": release["number"],
                     "at": release["at"], "source_revision": None, "source_tree": None,
                     "environment_or_host": "Catalogue served by the Fly application", "image": None, "rollback": None,
                     "edge": None, "catalogue": {"release_id": identity, "previous_release_id": None,
                                                 "packages": served, "distinct_files": None,
                                                 "application_release": None},
                     "evidence": self.relative(readme), "record_type": "community_catalogue_release_record",
                     "also_recorded_in": []}
            self.entries.append(entry)
            reports = 0
            for path in sorted(folder.glob("*.json")):
                report = json.loads(path.read_text("utf-8"))
                if isinstance(report, dict) and report.get("record_type") in REPORT_VERSIONS:
                    self.source(path, "check_report", report["record_type"])
                    self.report_row(entry, path, report)
                    reports += 1
            # A release whose folder keeps no check report is read by the counts its own record states, once.
            stated = _table_cell(text, ("Live check", "Live retrieval check"))
            if not reports and stated and _OF.search(stated):
                counts = [(_count(passed), _count(total)) for passed, total in _OF.findall(stated)]
                self.row(entry, "Live check stated in the release record",
                         worst(_pair_state(passed, total) for passed, total in counts), [bounded(stated)],
                         where=PRODUCTION, segments=[], evidence=self.relative(readme))

    # Edge measurements.

    def edge_measurements(self):
        for path in self.glob(EDGE_MEASUREMENTS):
            value = self.read_json(path, "edge_measurement")
            if not isinstance(value, dict) or value.get("record_type") not in EDGE_MEASUREMENT_VERSIONS:
                continue
            evidence = self.relative(path)
            worker = value.get("worker")
            entry = {"id": f"edge-{path.parent.name}-{path.stem}", "kind": "edge_measurement",
                     "title": f"Edge measurement {path.stem}", "number": None,
                     "at": value.get("measured_at"), "source_revision": None, "source_tree": None,
                     "environment_or_host": f"Cloudflare Worker {worker.split('://', 1)[-1]}" if isinstance(worker, str) else EDGE,
                     "image": None, "rollback": None,
                     "edge": {"export_id": value.get("export_id"), "worker": _host(worker), "origin": _host(value.get("origin"))},
                     "catalogue": None, "evidence": evidence, "record_type": value["record_type"],
                     "also_recorded_in": []}
            self.entries.append(entry)
            if value["record_type"] == "site_edge_measurement/v1":
                for name, label in (("edge_bodies_differing_from_the_export", "Edge bodies differ from the export"),
                                    ("origin_failures", "Origin failures during the measurement")):
                    if isinstance(value.get(name), list):
                        self.row(entry, label, "passed" if not value[name] else "failed",
                                 ["None recorded"] if not value[name]
                                 else ["Recorded: " + bounded(json.dumps(value[name]), 200)],
                                 where=entry["environment_or_host"], segments=[name], evidence=evidence,
                                 attempt=value.get("export_id"), at=value.get("measured_at"))
            else:
                pages, exact = value.get("pages"), value.get("pages_served_exactly")
                self.row(entry, "Pages served exactly while the origin was unavailable", _pair_state(exact, pages),
                         [f"Pages: {exact} of {pages}"], where=entry["environment_or_host"],
                         segments=["pages_served_exactly"], evidence=evidence)

    # Current deployment.

    def current_deployment(self):
        path = self.root / CURRENT_DEPLOYMENT
        self.source(path, "current_deployment_statement")
        text = self.statement_text(path)
        start = text.find(CURRENT_DEPLOYMENT_HEADING + "\n")
        if start < 0:
            raise BuildError(f"{CURRENT_DEPLOYMENT} has no '{CURRENT_DEPLOYMENT_HEADING}' section")
        end = text.find("\n### ", start)
        section = " ".join(text[start:end if end > 0 else len(text)].split())
        stated = {}
        for name, pattern, kind in CURRENT_DEPLOYMENT_FACTS:
            found = re.search(pattern, section)
            stated[name] = (int(found.group(1)) if kind is int else found.group(1)) if found else None
        if stated["release"] is None or stated["source_revision"] is None:
            raise BuildError(f"the current deployment section of {CURRENT_DEPLOYMENT} names no Fly release and revision")
        applications = [entry for entry in self.entries if entry["kind"] == "application_release"]
        newest = max(applications, key=lambda entry: entry["number"])
        held = json.loads((self.root / newest["evidence"]).read_text("utf-8"))
        edge = held.get("cloudflare") if isinstance(held.get("cloudflare"), dict) else {}
        recorded = {"release": newest["number"], "source_revision": newest["source_revision"],
                    "source_tree": newest["source_tree"],
                    "image": (_HEX64.search(newest["image"] or "") or [None])[0],
                    "ci_run": _first(held, ("ci_run", "continuous_integration_run")),
                    "deploy_run": _first(held, ("deploy_run", "deployment_workflow_run")),
                    "edge_deployment": edge.get("worker_deployment"), "edge_version": edge.get("worker_version"),
                    "edge_export": edge.get("export_id")}
        if stated["image"]:
            stated["image"] = stated["image"].split(":", 1)[-1]
        comparison = {}
        for name in stated:
            if stated[name] is None:
                comparison[name] = "not_stated"
            elif recorded[name] is None:
                comparison[name] = "not_recorded"
            else:
                comparison[name] = "agrees" if str(stated[name]) == str(recorded[name]) else "differs"
        return {"statement": CURRENT_DEPLOYMENT, "section": CURRENT_DEPLOYMENT_HEADING[3:], "stated": stated,
                "newest_release_entry": newest["id"], "newest_release_evidence": newest["evidence"],
                "comparison": comparison}

    def statement_text(self, path: Path) -> str:
        """The current deployment statement as written; a check substitutes a changed copy here."""
        return path.read_text("utf-8")

    def build(self):
        for number, held in sorted(self.release_records().items()):
            self.application_release(number, held)
        current = self.current_deployment()
        self.catalogue_publications()
        self.community_releases()
        self.edge_measurements()
        order = {entry["id"]: index for index, entry in enumerate(sorted(
            self.entries, key=lambda entry: (_moment(entry["at"]), entry["id"]), reverse=True))}
        self.entries.sort(key=lambda entry: order[entry["id"]])
        self.rows.sort(key=lambda row: order[row["entry"]])
        ids = [entry["id"] for entry in self.entries]
        if len(set(ids)) != len(ids):
            raise BuildError(f"two records give the same entry identity: {sorted(ids)}")
        for item in [*self.entries, *self.rows]:
            text = json.dumps(item, ensure_ascii=False)
            found = FORBIDDEN.search(text)
            if found:
                raise BuildError(f"{item.get('evidence')}: the Systems view refuses the word {found.group(0)!r}; "
                                 "it carries recorded facts only")
            if EMAIL.search(text):
                raise BuildError(f"{item.get('evidence')}: the Systems view carries no email address")
        return {"record_type": RECORD_TYPE, "generated_by": GENERATED_BY, "states": list(STATES),
                "reading_rules": "tools/build_systems_view.py",
                "current_deployment": current, "entries": self.entries, "rows": self.rows,
                "sources": [self.sources[name] for name in sorted(self.sources)]}


#: The facts the current deployment section states, each with the pattern that reads it and its kind.
CURRENT_DEPLOYMENT_FACTS = (
    ("release", r"Fly release (\d+)", int),
    ("source_revision", r"Fly release \d+, from `([0-9a-f]{40})`", str),
    ("source_tree", r"tree `([0-9a-f]{40})`", str),
    ("image", r"image `(sha256:[0-9a-f]{64})`", str),
    ("ci_run", r"CI `(\d+)`", int),
    ("deploy_run", r"[Gg]uarded deployment `(\d+)`", int),
    ("edge_deployment", r"Cloudflare deployment `([0-9a-f-]{32,36})`", str),
    ("edge_version", r"serving version `([0-9a-f-]{32,36})`", str),
    ("edge_export", r"export is `([0-9a-f]{64})`", str),
)


def release_number(record: dict):
    """The Fly release number: `fly_release`, else `fly_release_version`, else `release`, as the status pages read it."""
    return record.get("fly_release") or record.get("fly_release_version") or record.get("release")


def gate_reading(value):
    """(state, observed, field) for the deployment switch after the release, or None when it is not recorded."""
    for name in ("deployment_gate_after", "deploy_setting_after", "deployment_switch_after_release"):
        if name not in value:
            continue
        item = value[name]
        if item is False or item in ("false", "FLY_DEPLOY_ENABLED=false"):
            return "passed", f"{words(name)}: {str(item).lower() if isinstance(item, bool) else item}", name
        if item is True or item in ("true", "FLY_DEPLOY_ENABLED=true"):
            return "failed", f"{words(name)}: {str(item).lower() if isinstance(item, bool) else item}", name
        return "unknown", f"{words(name)}: {bounded(item, 120)}", name
    return None


def edge_facts(block):
    if not isinstance(block, dict):
        return None
    names = ("worker", "export_id", "worker_deployment", "worker_version", "deployed_at", "provider_created_at",
             "static_files", "static_bytes", "origin_mode", "production_hostnames", "rollback_export_id",
             "rollback_worker_deployment", "rollback_worker_version")
    return {name: block[name] for name in names if name in block}


def catalogue_facts(value):
    for name in ("catalogue", "catalogue_at_application_deployment", "catalogue_publication",
                 "catalogue_release_published", "catalogue_release_after"):
        block = value.get(name)
        if isinstance(block, dict):
            return {"block": name,
                    "release_id": _first(block, ("release_id", "last_recorded_release_id")),
                    "packages": _first(block, ("packages", "last_recorded_packages", "items", "approved_items")),
                    "distinct_files": _first(block, ("distinct_files", "last_recorded_distinct_files")),
                    "changed_by_this_application_release": block.get("changed_by_this_application_release"),
                    "publication_performed": block.get("publication_performed")}
        if isinstance(block, str) and _HEX64.fullmatch(block):
            return {"block": name, "release_id": block, "packages": None, "distinct_files": None,
                    "changed_by_this_application_release": None, "publication_performed": None}
    return None


def _host(address):
    """A recorded address as its host name alone, so the record keeps where a check ran and no endpoint."""
    return address.split("://", 1)[-1].rstrip("/") if isinstance(address, str) else address


def _identity_text(text: str) -> str:
    """The text that names a Community release's identity: its identity row, else its opening paragraph."""
    for line in text.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if line.lstrip().startswith("|") and len(cells) >= 2 and cells[0] in ("Release identity", "Release"):
            return cells[1]
    return text.split("\n\n", 2)[1] if text.count("\n\n") >= 1 else text


def _table_cell(text: str, names) -> str:
    """The value of the first table row of a Markdown record whose first cell is one of `names`, or empty text."""
    for line in text.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if line.lstrip().startswith("|") and len(cells) >= 2 and cells[0] in names:
            return cells[1]
    return ""


def _served_count(text: str):
    """The package count a Community release record states in its served or items row."""
    found = re.search(r"\d[\d,]*", _table_cell(text, ("Served", "Items served", "Items")))
    return _count(found.group(0)) if found else None


def _moment(value) -> datetime:
    """A recorded time for ordering only; the record keeps the value exactly as written."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return datetime.fromtimestamp(value, timezone.utc)
    if isinstance(value, str) and value:
        text = value.replace("Z", "+00:00")
        try:
            moment = datetime.fromisoformat(text)
        except ValueError:
            try:
                moment = datetime.combine(date.fromisoformat(text[:10]), datetime.min.time())
            except ValueError:
                return datetime.min.replace(tzinfo=timezone.utc)
        return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)
    return datetime.min.replace(tzinfo=timezone.utc)


def validate(value: dict) -> None:
    """Refuse a record that its schema refuses."""
    from jsonschema import Draft202012Validator
    schema = json.loads(SCHEMA.read_text("utf-8"))
    errors = sorted(Draft202012Validator(schema).iter_errors(value), key=lambda error: list(error.path))
    if errors:
        first = errors[0]
        raise BuildError(f"the record does not match {SCHEMA.name} at {pointer(first.path)}: {first.message}")


def build(root: Path = ROOT) -> dict:
    """The whole record, from the records as they stand in the checkout."""
    value = Builder(root).build()
    validate(value)
    return value


def render(value: dict) -> str:
    return json.dumps(value, indent=1, ensure_ascii=False) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="exit 1 when the committed record is stale")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)
    try:
        text = render(build())
    except (BuildError, KeyError, TypeError, ValueError) as error:
        sys.stderr.write(f"The Systems record cannot be built: {error}\n")
        return 2
    if args.check:
        if not args.output.is_file() or args.output.read_text("utf-8") != text:
            sys.stderr.write(f"{args.output} is stale; run python tools/build_systems_view.py\n")
            return 1
        print(f"{args.output} is current")
        return 0
    args.output.write_text(text, "utf-8")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
