"""A continuous second look at the items the library serves (roadmap package oracle-review, September 26, 2026).

The daily job publishes an item after the deterministic prechecks and one independent screening call
(``/home/username/baltor-private/tools/daily_library_release.sh``). This tool gives each served item a second
look later, on the machine that runs jobs. The Fly Machine makes no model call and holds no model key; nothing
here changes that. The tool withdraws nothing and publishes nothing: it records what it found, and other paths
decide.

```text
One run
├── reads the active release bundle: the newest daily bundle under ~/baltor-bundles with items.jsonl
├── finds the reviewed folder that holds each served item (the folder the writer wrote from the daily ledger)
│   and the candidate export it was reviewed from, and rebuilds the review request from that export; the
│   rebuilt request must name the reviewed package digest, the exact bytes the first reviewer read, and it
│   is judged under the current criteria (the row records whether they are the first review's)
├── samples up to N items not yet double-checked: oldest first, every harness kind in turn
├── chooses one eligible reviewer for each item, in the preference order given
│   ├── eligible: a family that did not produce the item (an imported item's producer is its upstream author)
│   ├── preferred: a family that has not judged the item yet, so an approval adds a second family
│   └── qualified: the reviewer passed the daily calibration on the batch of twelve within the last 36 hours
├── runs the deterministic prechecks again in this process, with no model call
├── asks the reviewer through the review panel the way the daily job does: the campaign's review command,
│   one reviewer, every other installation excluded, batches of twelve, a call ceiling and a token ceiling
├── writes every verdict, and every attempt without one, to the durable oracle ledger
├── writes each rejection, and each precheck refusal, as a withdrawal candidate record
└── writes an approval by a second family as an upgrade candidate record
```

Current behaviour: imported items whose reviewed folder was written by ``tools/write_reviewed_catalogue.py``
from a licensed import export are double-checked. Items without such a folder or export (the starter items, and
the original items reviewed on September 25, 2026 whose candidate folder is not in the review batches) are
counted in the run report under their reason and are not asked. Reading those is planned work.

Records this tool writes, all under ``/home/username/baltor-library/oracle/``:

- ``review-ledger.jsonl``: one ``oracle_review_ledger_row/v1`` a line: the item identity and served digest,
  the reviewer and its family, the verdict (``approve``, ``reject`` or ``none``), the reasons and findings, and
  the panel ledger call it came from. An item is double-checked when a row holds a verdict at its served digest.
- ``withdrawals/*.json``: one ``oracle_withdrawal_candidate/v1`` for each rejection or precheck refusal. The
  withdrawal path of the feedback-withdrawal package reads these; this tool never withdraws.
- ``upgrades/*.json``: one ``oracle_upgrade_candidate/v1`` when a second family approves an item a first family
  approved, so the full review can make it Verified. This tool changes no tier.
- ``runs/RUN/``: the run report, the identities asked, and the panel ledger and log of each panel call.

    PYTHONPATH=src:tools python tools/oracle_review_served.py --sample 24 --authorize-model-calls
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REPOSITORY = HERE.parent
for entry in (str(HERE), str(REPOSITORY / "src"), str(REPOSITORY)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

from candidate_review import configuration as config  # noqa: E402
from candidate_review import engines, imported, imported_profile  # noqa: E402
from candidate_review.ledger import ReviewLedger  # noqa: E402
from candidate_review.panel import PanelRunRequest, ReviewPanel  # noqa: E402
from candidate_review.prechecks import PrecheckContext, run_prechecks  # noqa: E402
from candidate_review.reviewers import ReviewerContext  # noqa: E402
from write_reviewed_catalogue import verdicts_for  # noqa: E402

LIBRARY = Path("/home/username/baltor-library")
BUNDLES = Path.home() / "baltor-bundles"
CAMPAIGN = REPOSITORY / "artifacts/review-throughput-2026-09-24/community_campaign.py"
PANEL = HERE / "candidate_review/resources/panel.json"
LEDGER_ROW = "oracle_review_ledger_row/v1"
WITHDRAWAL_RECORD = "oracle_withdrawal_candidate/v1"
UPGRADE_RECORD = "oracle_upgrade_candidate/v1"
REPORT_RECORD = "oracle_review_run/v1"
DEFAULT_REVIEWER = "tactical.gemma-4-coding-abliterated"
DEFAULT_SAMPLE = 24
BATCH = 12
NOT_THE_REVIEWER = "not_the_reviewer_of_this_oracle_run"
#: The reviewer named on a ledger row that the deterministic prechecks decided, with no model call.
PRECHECKS, PRECHECK_FAMILY = "deterministic_prechecks", "deterministic"
APPROVE, REJECT, NONE = "approve", "reject", "none"
NOT_ASKED = "not_asked:"
QUALIFIED = "qualified"
COLLECT_REASON = ("Oracle second look (roadmap package oracle-review): one reviewer is asked; its verdict is stored "
                  "in the oracle ledger and waits, through the full review, for a later tier change.")
CONSUMER = ("The withdrawal path of the feedback-withdrawal package reads this record and decides. The oracle "
            "withdraws nothing.")
UPGRADE_NEXT = ("A Verified folder written by tools/write_reviewed_catalogue.py --tier verified, naming both "
                "reviewers and reading both ledgers, is the full review. The oracle changes no tier.")


class OracleError(ValueError):
    """A stable refusal code for a run that cannot proceed as declared."""


def refuse(code: str, message: str = "") -> None:
    raise OracleError(f"{code}: {message}" if message else code)


def _timestamp(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def newest_bundle(root: Path) -> Path:
    """The newest daily bundle folder by name that holds its item lines."""
    found = sorted(path for path in Path(root).glob("daily-*") if path.is_dir() and (path / "items.jsonl").is_file())
    if not found:
        refuse("bundle_not_found", f"no daily bundle with items.jsonl under {root}")
    return found[-1]


def served_items(bundle: Path) -> list:
    """Every item line of the bundle, reduced to what the oracle needs."""
    rows = []
    for line in (Path(bundle) / "items.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        reference, attributes, approval = item["reference"], item.get("attributes", {}), item.get("approval", {})
        rows.append({"identity": reference["identity"], "digest": reference["digest"], "kind": reference["kind"],
                     "tier": str(approval.get("tier") or attributes.get("tier") or ""),
                     "harness_kind": str(attributes.get("harness_kind") or ""),
                     "catalogued_on": str(attributes.get("catalogued_on") or ""),
                     "approval_ref": str(approval.get("approval_ref") or ""), "batch": str(attributes.get("batch") or "")})
    return rows


class ReviewedIndex:
    """Which reviewed folder holds each served item, at which position, with the verdicts on record."""

    def __init__(self, folders) -> None:
        self.entries, self.folders = {}, []
        for order, folder in enumerate(folders):
            folder = Path(folder)
            if not (folder / "reviews.json").is_file() or not (folder / "items.json").is_file():
                continue
            reviews, items = _json(folder / "reviews.json"), _json(folder / "items.json")
            families = {reviewer["reviewer_id"]: reviewer["family"] for reviewer in reviews.get("reviewers", [])}
            by_identity = {item["reference"]["identity"]: item for item in items.get("items", [])}
            self.folders.append(str(folder))
            for position, row in enumerate(reviews.get("rows", [])):
                item = by_identity.get(row["identity"])
                if item is None:
                    continue
                self.entries.setdefault((row["identity"], row["body_digest"]), {
                    "folder": str(folder), "order": order, "position": position, "row": row, "item": item,
                    "families": families, "recorded_at": str(reviews.get("recorded_at") or ""),
                    "written_by_the_panel_writer": (folder / "writer-report.json").is_file()})

    def lookup(self, identity: str, digest: str):
        return self.entries.get((identity, digest))


class CandidateIndex:
    """Which licensed import export holds each identity, and the loaded export when it is asked for."""

    def __init__(self, roots, repository: Path) -> None:
        self.repository, self.folders_of, self._loaded = Path(repository), {}, {}
        for root in roots:
            for folder in sorted(path for path in Path(root).glob("*") if path.is_dir()):
                if not imported.is_imported_catalogue(folder) or not (folder / "items.json").is_file():
                    continue
                try:
                    items = _json(folder / "items.json")["items"]
                except (OSError, ValueError, KeyError, TypeError):
                    continue
                for item in items:
                    self.folders_of.setdefault(item["reference"]["identity"], []).append(str(folder))

    def folders(self, identity: str) -> list:
        return list(self.folders_of.get(identity, ()))

    def catalogue(self, folder: str):
        if folder not in self._loaded:
            self._loaded[folder] = imported.ImportedCatalogue.load(Path(folder), self.repository)
        return self._loaded[folder]


class OracleLedger:
    """The durable, append-only record of every second look. A row with a verdict makes its item double-checked."""

    def __init__(self, path: Path) -> None:
        self.path, self.rows = Path(path), []
        if self.path.is_symlink():
            refuse("oracle_ledger_unsafe", "the oracle ledger path is a link")
        if self.path.exists():
            for number, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), 1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except ValueError:
                    refuse("oracle_ledger_unreadable", f"line {number} of the oracle ledger is not JSON")
                if type(row) is not dict or row.get("record_type") != LEDGER_ROW:
                    refuse("oracle_ledger_row_unknown", f"line {number} of the oracle ledger is not {LEDGER_ROW}")
                self.rows.append(row)

    def _of(self, identity: str, digest: str) -> list:
        return [row for row in self.rows if row["identity"] == identity and row["digest"] == digest]

    def verdict(self, identity: str, digest: str):
        """The newest row that holds a verdict for this served digest, or None."""
        return next((row for row in reversed(self._of(identity, digest)) if row["verdict"] in (APPROVE, REJECT)), None)

    def attempts(self, identity: str, digest: str) -> int:
        """Attempts that reached a reviewer and produced no verdict. A reviewer that was not asked does not count."""
        return sum(1 for row in self._of(identity, digest)
                   if row["verdict"] == NONE and not str(row["attempt_outcome"]).startswith(NOT_ASKED))

    def families(self, identity: str, digest: str) -> set:
        return {row["family"] for row in self._of(identity, digest) if row["verdict"] in (APPROVE, REJECT)
                and row["reviewer"] != PRECHECKS}

    def append(self, row: dict) -> None:
        if row.get("record_type") != LEDGER_ROW:
            refuse("oracle_ledger_row_unknown", "a ledger row is written as " + LEDGER_ROW)
        payload = (json.dumps(row, sort_keys=True) + "\n").encode("utf-8")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(self.path, os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
        try:
            os.write(descriptor, payload)
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        self.rows.append(row)


def sample(candidates, limit: int) -> list:
    """Up to ``limit`` candidates, oldest first, every harness kind in turn.

    Each candidate names its ``sort`` key (older first) and its ``kind``. The kinds take turns in the order of
    their oldest candidate, so no kind waits behind a larger one."""
    queues = {}
    for entry in sorted(candidates, key=lambda candidate: candidate["sort"]):
        queues.setdefault(entry["kind"], []).append(entry)
    order = sorted(queues, key=lambda kind: queues[kind][0]["sort"])
    chosen = []
    while len(chosen) < limit and any(queues.values()):
        for kind in order:
            if queues[kind] and len(chosen) < limit:
                chosen.append(queues[kind].pop(0))
    return chosen


def choose_reviewer(installations, producer_family: str, families_on_record, allow_same_family: bool = True):
    """(reviewer, adds a second family) in preference order, never a reviewer of the producer's family.

    A reviewer whose family has not judged the item yet comes first, so an approval adds a second family. With
    ``allow_same_family`` a family already on record may look again when no new family is available. A mutant
    control that drops the producer test fails ``test_a_reviewer_of_the_producer_family_is_never_chosen``."""
    eligible = [item for item in installations if item.family != producer_family]
    fresh = [item for item in eligible if item.family not in families_on_record]
    if fresh:
        return fresh[0], True
    if allow_same_family and eligible:
        return eligible[0], False
    return None, False


def qualified_recently(reviewer_id: str, calibration_root: Path, hours: float, now: datetime) -> tuple:
    """(qualified, record path): the newest daily calibration within ``hours`` that judged this reviewer on the
    batch of twelve decides. No calibration in the window means not qualified."""
    newest = None
    for path in Path(calibration_root).glob("*/calibration*.json"):
        try:
            record = _json(path)
            status = record["reports"]["mixed_batch_of_12"]["installations"][reviewer_id]["status"]
            written = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
        except (OSError, ValueError, KeyError, TypeError):
            continue
        if (now - written).total_seconds() > hours * 3600:
            continue
        if newest is None or written > newest[0]:
            newest = (written, status, str(path))
    if newest is None:
        return False, ""
    return newest[1] == QUALIFIED, newest[2]


def exclusions_for(panel, reviewer_id: str) -> dict:
    """Every enabled installation but the reviewer, each with the daily job's written reason."""
    return {item.installation_id: NOT_THE_REVIEWER for item in panel.installations
            if item.enabled and item.installation_id != reviewer_id}


class CampaignReviewCall:
    """The daily job's review command, ``community_campaign.py review``, run as a separate process."""

    def __init__(self, repository: Path = REPOSITORY, python: str = sys.executable, campaign: Path = CAMPAIGN,
                 authorized: bool = False, timeout_seconds: float = 3600.0) -> None:
        self.repository, self.python, self.campaign = Path(repository), python, Path(campaign)
        self.authorized, self.timeout_seconds = authorized, timeout_seconds

    def command(self, catalogue, identities_file, reviewer_id, exclusions, ledger, output, call_ceiling,
                token_ceiling, calls_left) -> list:
        command = [self.python, str(self.campaign), "review", "--catalogue", str(catalogue), "--output", str(output),
                   "--ledger", str(ledger), "--reviewer", reviewer_id, "--calls-left", str(calls_left),
                   "--batch-size", str(BATCH), "--identities-file", str(identities_file),
                   "--call-ceiling", str(call_ceiling), "--token-ceiling", str(token_ceiling)]
        if self.authorized:
            command.append("--authorize-model-calls")
        for installation_id, reason in sorted(exclusions.items()):
            command += ["--exclude-installation", f"{installation_id}={reason}"]
        return command

    def review(self, *, catalogue, identities_file, reviewer_id, exclusions, ledger, output, call_ceiling,
               token_ceiling, calls_left, log) -> dict:
        command = self.command(catalogue, identities_file, reviewer_id, exclusions, ledger, output, call_ceiling,
                               token_ceiling, calls_left)
        environment = {**os.environ, "PYTHONPATH": "src:tools"}
        try:
            finished = subprocess.run(command, cwd=str(self.repository), env=environment, capture_output=True,
                                      text=True, timeout=self.timeout_seconds, check=False)
        except subprocess.TimeoutExpired as error:
            Path(log).write_text(f"timeout after {self.timeout_seconds} seconds\n{error.stdout or ''}\n"
                                 f"{error.stderr or ''}", encoding="utf-8")
            return {"failed": True, "reason": "timeout"}
        Path(log).write_text(finished.stdout + "\n" + finished.stderr, encoding="utf-8")
        if finished.returncode != 0:
            return {"failed": True, "reason": f"exit {finished.returncode}", "tail": finished.stderr[-400:]}
        try:
            return _json(Path(output))
        except (OSError, ValueError):
            return {"failed": True, "reason": "no summary written"}


class PanelReviewCall:
    """The same run request as the campaign's review command, run in this process over a given panel file.

    A check hands it a fixture panel and scripted reviewers, so no model is called; the ledger it writes has
    the shape the campaign writes."""

    def __init__(self, panel_path: Path, repository: Path = REPOSITORY, fixture_scripts=None,
                 authorized: bool = False) -> None:
        self.panel_path, self.repository = Path(panel_path), Path(repository)
        self.fixture_scripts, self.authorized = fixture_scripts, authorized

    def review(self, *, catalogue, identities_file, reviewer_id, exclusions, ledger, output, call_ceiling,
               token_ceiling, calls_left, log) -> dict:
        identities = [line.strip() for line in Path(identities_file).read_text().splitlines() if line.strip()]
        base = config.PanelConfiguration.from_dict(_json(self.panel_path))
        loaded = imported.ImportedCatalogue.load(Path(catalogue), self.repository)
        configuration = imported_profile.configuration(base, population_size=len(loaded.identities()))
        criteria, instructions = imported_profile.resources()
        context = ReviewerContext(repository=self.repository, fixture_scripts=self.fixture_scripts)
        reviewers = {item.installation_id: engines.build_reviewer(item, configuration.policy, context)
                     for item in configuration.installations}
        panel = ReviewPanel(configuration, criteria, instructions, reviewers,
                            engines.build_precheck_engines(configuration), ReviewLedger(Path(ledger)))
        requests = tuple(loaded.request(identity, loaded.producer_for(identity), criteria, instructions.sha256)
                         for identity in identities)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        result = panel.run(PanelRunRequest(
            run_id=f"oracle-review-{stamp}", requests=requests, population=loaded.population_bodies(),
            call_ceiling=call_ceiling, token_ceiling=token_ceiling, model_calls_authorized=self.authorized,
            fixture_run=self.fixture_scripts is not None, batch_sizes={reviewer_id: BATCH},
            excluded_installations=dict(exclusions),
            quota_group_call_ceilings={configuration.installation(reviewer_id).quota_group: calls_left},
            repeated_failure_limit=3, collect_below_quorum_reason=COLLECT_REASON))
        summary = {"run_id": result.run_id, "stop_reason": result.stop_reason, "totals": result.totals(),
                   "ineligible": result.ineligible, "capped_quota_groups": sorted(result.capped_quota_groups),
                   "spent_quota_groups": sorted(result.spent_quota_groups)}
        _write_json(Path(output), summary)
        Path(log).write_text(json.dumps(summary, sort_keys=True) + "\n", encoding="utf-8")
        return summary


def _attempt_outcome(ledger: ReviewLedger, identity: str) -> str:
    """What the panel ledger says happened to one identity that has no verdict."""
    outcome = ""
    for call in ledger.calls():
        if call["identity"] == identity:
            outcome = call["outcome"]
    for call in ledger.batch_calls():
        for member in call["members"]:
            if member["identity"] == identity:
                outcome = member["outcome"] if call["outcome"] == "batch_answered" else call["outcome"]
    return outcome


def _record_name(identity: str, digest: str, stamp: str) -> str:
    return f"{identity}--{digest[:12]}--{stamp}.json"


class OracleRun:
    """One run: the sample, the prechecks, the panel calls and every record they lead to."""

    def __init__(self, options, review_call=None, now=None) -> None:
        self.options = options
        self.now = now or datetime.now(timezone.utc)
        self.stamp = self.now.strftime("%Y%m%dT%H%M%SZ")
        self.run_id = options.run_id or f"oracle-{self.stamp}"
        self.review_call = review_call
        self.panel = config.PanelConfiguration.from_dict(_json(Path(options.panel)))
        self.criteria, self.instructions = imported_profile.resources()
        self.folder = Path(options.runs) / self.run_id
        self.report = {"record_type": REPORT_RECORD, "run_id": self.run_id, "started_at": _timestamp(self.now),
                       "skipped": {}, "examples": {}, "groups": [], "calls": 0, "charged_tokens": 0,
                       "verdicts": {APPROVE: 0, REJECT: 0, NONE: 0}, "precheck_refusals": 0,
                       "withdrawal_candidates": [], "upgrade_candidates": [], "stop_reason": ""}
        self._precheck_cache = {}

    def skip(self, reason: str, identity: str) -> None:
        skipped, examples = self.report["skipped"], self.report["examples"]
        skipped[reason] = skipped.get(reason, 0) + 1
        examples.setdefault(reason, [])
        if len(examples[reason]) < 5:
            examples[reason].append(identity)

    def pending(self, served, reviewed: ReviewedIndex, candidates: CandidateIndex, ledger: OracleLedger,
                preferred) -> list:
        """Every served item that can be double-checked now, with its reviewer, sort key and kind."""
        found = []
        for item in served:
            identity, digest = item["identity"], item["digest"]
            if ledger.verdict(identity, digest) is not None:
                self.skip("already_double_checked", identity)
                continue
            if ledger.attempts(identity, digest) >= self.options.set_aside_after:
                self.skip("set_aside_after_failed_attempts", identity)
                continue
            entry = reviewed.lookup(identity, digest)
            if entry is None:
                self.skip("reviewed_folder_not_found", identity)
                continue
            if not entry["written_by_the_panel_writer"]:
                self.skip("reviewed_folder_not_written_by_the_panel_writer", identity)
                continue
            folders = candidates.folders(identity)
            if not folders:
                self.skip("candidate_export_not_found", identity)
                continue
            producer_family = str(entry["row"].get("producer", {}).get("family") or "")
            on_record = {entry["families"].get(decision["reviewer_id"], "")
                         for decision in entry["row"].get("decisions", [])} | ledger.families(identity, digest)
            reviewer, second = choose_reviewer(preferred, producer_family, on_record,
                                               allow_same_family=not self.options.second_family_only)
            if reviewer is None:
                self.skip("no_eligible_reviewer", identity)
                continue
            kind = item["harness_kind"] or str(entry["item"].get("provenance", {}).get("harness_kind") or "") \
                or item["kind"]
            found.append({**item, "kind": kind, "entry": entry, "candidate_folders": folders, "reviewer": reviewer,
                          "second_family": second, "producer_family": producer_family,
                          "sort": (item["catalogued_on"] or entry["recorded_at"], entry["order"], entry["position"])})
        return found

    def bind(self, chosen, candidates: CandidateIndex) -> list:
        """Rebuild each chosen item's review request and keep the ones bound to the reviewed package.

        The reviewed package digest names the exact bytes the first reviewer read, and the rebuilt request must
        name the same bytes. The request digest also covers the criteria and instructions of the day, so it
        changes when those change; the second look reads the item under the current criteria on purpose, and
        the row records whether they are the first review's."""
        bound = []
        for entry in chosen:
            row = entry["entry"]["row"]
            expected = row.get("reviewed_package", {})
            request, folder = None, ""
            for candidate in entry["candidate_folders"]:
                loaded = candidates.catalogue(candidate)
                if entry["identity"] not in loaded.identities():
                    continue
                rebuilt = loaded.request(entry["identity"], loaded.producer_for(entry["identity"]), self.criteria,
                                         self.instructions.sha256)
                if rebuilt.package.package_digest == expected.get("package_digest"):
                    request, folder = rebuilt, candidate
                    break
            if request is None:
                self.skip("reviewed_package_not_rebuilt", entry["identity"])
                continue
            bound.append({**entry, "request": request, "candidate_folder": folder,
                          "first_review_request_sha256": str(expected.get("request_sha256") or ""),
                          "same_criteria_as_first_review": request.request_sha256 == expected.get("request_sha256")})
        return bound

    def prechecks(self, candidate_folder: str, catalogue, request):
        if candidate_folder not in self._precheck_cache:
            configuration = imported_profile.configuration(self.panel, population_size=len(catalogue.identities()))
            self._precheck_cache[candidate_folder] = (engines.build_precheck_engines(configuration),
                                                      PrecheckContext(configuration.policy, catalogue.population_bodies()))
        checks, context = self._precheck_cache[candidate_folder]
        return run_prechecks(request, checks, context)

    def row(self, entry, **fields) -> dict:
        reviewer = entry["reviewer"]
        return {"record_type": LEDGER_ROW, "recorded_at": _timestamp(datetime.now(timezone.utc)), "run_id": self.run_id,
                "bundle": self.report["bundle"], "identity": entry["identity"], "digest": entry["digest"],
                "package_digest": entry["request"].package.package_digest,
                "request_sha256": entry["request"].request_sha256,
                "first_review_request_sha256": entry["first_review_request_sha256"],
                "same_criteria_as_first_review": entry["same_criteria_as_first_review"],
                "tier": entry["tier"], "harness_kind": entry["kind"],
                "reviewed_folder": entry["entry"]["folder"], "candidate_folder": entry["candidate_folder"],
                "producer_family": entry["producer_family"], "reviewer": reviewer.installation_id,
                "family": reviewer.family, "model": reviewer.model, "second_family": entry["second_family"],
                "verdict": NONE, "attempt_outcome": "", "reasons": "", "findings": [], "call_ref": "",
                "panel_ledger": "", "withdrawal_candidate": "", "upgrade_candidate": "", **fields}

    def withdrawal(self, entry, row: dict, decision: str) -> str:
        path = Path(self.options.withdrawals) / _record_name(entry["identity"], entry["digest"], self.stamp)
        reviewed = entry["entry"]["row"]
        _write_json(path, {
            "record_type": WITHDRAWAL_RECORD, "recorded_at": row["recorded_at"], "run_id": self.run_id,
            "bundle": self.report["bundle"], "identity": entry["identity"], "digest": entry["digest"],
            "package_digest": row["package_digest"], "request_sha256": row["request_sha256"],
            "first_review_request_sha256": row["first_review_request_sha256"],
            "same_criteria_as_first_review": row["same_criteria_as_first_review"],
            "tier": entry["tier"], "approval_ref": entry["approval_ref"],
            "reviewed_folder": entry["entry"]["folder"], "candidate_folder": entry["candidate_folder"],
            "producer_family": entry["producer_family"],
            "first_review": [{"reviewer_id": decision_row["reviewer_id"],
                              "family": entry["entry"]["families"].get(decision_row["reviewer_id"], ""),
                              "decision": decision_row["decision"], "call_ref": decision_row.get("call_ref", "")}
                             for decision_row in reviewed.get("decisions", [])],
            "reviewer": {"installation_id": row["reviewer"], "family": row["family"], "model": row["model"]},
            "decision": decision, "reasons": row["reasons"], "findings": row["findings"], "call_ref": row["call_ref"],
            "panel_ledger": row["panel_ledger"], "status": "candidate", "consumer": CONSUMER})
        self.report["withdrawal_candidates"].append(str(path))
        return str(path)

    def upgrade(self, entry, row: dict) -> str:
        path = Path(self.options.upgrades) / _record_name(entry["identity"], entry["digest"], self.stamp)
        reviewed = entry["entry"]["row"]
        reviews = [{"reviewer_id": decision_row["reviewer_id"],
                    "family": entry["entry"]["families"].get(decision_row["reviewer_id"], ""),
                    "decision": decision_row["decision"], "call_ref": decision_row.get("call_ref", ""),
                    "ledger": next((ledger["path"] for ledger in _json(Path(entry["entry"]["folder"]) / "reviews.json")
                                    .get("ledgers", []) if ledger["name"] == decision_row.get("call_ref", "").split("#")[0]),
                                   "")}
                   for decision_row in reviewed.get("decisions", [])]
        reviews.append({"reviewer_id": row["reviewer"], "family": row["family"], "decision": APPROVE,
                        "call_ref": row["call_ref"], "ledger": row["panel_ledger"]})
        _write_json(path, {
            "record_type": UPGRADE_RECORD, "recorded_at": row["recorded_at"], "run_id": self.run_id,
            "bundle": self.report["bundle"], "identity": entry["identity"], "digest": entry["digest"],
            "package_digest": row["package_digest"], "tier": entry["tier"], "approval_ref": entry["approval_ref"],
            "reviewed_folder": entry["entry"]["folder"], "candidate_folder": entry["candidate_folder"],
            "producer_family": entry["producer_family"], "families": sorted({review["family"] for review in reviews}),
            "reviews": reviews, "status": "candidate", "next_step": UPGRADE_NEXT})
        self.report["upgrade_candidates"].append(str(path))
        return str(path)

    def record(self, entry, ledger: OracleLedger, row: dict) -> None:
        ledger.append(row)
        self.report["verdicts"][row["verdict"]] += 1

    def run(self) -> dict:
        options = self.options
        bundle = Path(options.bundle) if options.bundle else newest_bundle(Path(options.bundles_root))
        self.report["bundle"] = bundle.name
        self.report["bundle_path"] = str(bundle)
        served = served_items(bundle)
        self.report["served"] = len(served)
        folders_file = Path(options.reviewed_folders_file)
        folders = ([line.strip() for line in folders_file.read_text().splitlines() if line.strip()]
                   if folders_file.is_file() else []) + list(options.reviewed_folder)
        reviewed = ReviewedIndex(folders)
        candidates = CandidateIndex(options.candidate_root, Path(options.repository))
        ledger = OracleLedger(Path(options.ledger))
        try:
            preferred = [self.panel.installation(name) for name in options.reviewer]
        except KeyError as error:
            refuse("reviewer_unknown", f"the panel names no installation {error}")
        chosen = sample(self.pending(served, reviewed, candidates, ledger, preferred), options.sample)
        self.report["sampled"] = [{"identity": entry["identity"], "kind": entry["kind"],
                                   "reviewer": entry["reviewer"].installation_id, "second_family": entry["second_family"],
                                   "catalogued_on": entry["catalogued_on"]} for entry in chosen]
        self.folder.mkdir(parents=True, exist_ok=True)
        if not options.authorize_model_calls:
            self.report["stop_reason"] = "model_calls_not_authorized"
            return self.finish()
        bound = self.bind(chosen, candidates)
        qualified = {}
        for entry in bound:
            reviewer_id = entry["reviewer"].installation_id
            if reviewer_id not in qualified:
                qualified[reviewer_id] = qualified_recently(reviewer_id, Path(options.calibration_root),
                                                           options.calibration_hours, self.now)
        self.report["qualified"] = {name: {"qualified": value[0], "record": value[1]} for name, value in qualified.items()}
        groups = {}
        for entry in bound:
            groups.setdefault((entry["candidate_folder"], entry["reviewer"].installation_id), []).append(entry)
        remaining_calls, remaining_tokens = options.call_ceiling, options.token_ceiling
        for number, (key, members) in enumerate(sorted(groups.items(), key=lambda pair: pair[1][0]["sort"]), 1):
            candidate_folder, reviewer_id = key
            reviewer = members[0]["reviewer"]
            if not qualified[reviewer_id][0]:
                for entry in members:
                    self.skip("reviewer_not_qualified_recently", entry["identity"])
                continue
            catalogue = candidates.catalogue(candidate_folder)
            to_ask = []
            for entry in members:
                outcome = self.prechecks(candidate_folder, catalogue, entry["request"])
                if outcome.refused:
                    findings = [{"kind": result.kind, "engine": result.engine_id, "status": result.status,
                                 "codes": sorted({finding.code for finding in result.findings})}
                                for result in outcome.results if result.findings or result.status != "passed"]
                    row = self.row(entry, verdict=REJECT, attempt_outcome="precheck_refused",
                                   reasons=", ".join(outcome.reasons), findings=findings, reviewer=PRECHECKS,
                                   family=PRECHECK_FAMILY, model="", second_family=False)
                    row["withdrawal_candidate"] = self.withdrawal(entry, row, "precheck_refused")
                    self.record(entry, ledger, row)
                    self.report["precheck_refusals"] += 1
                    continue
                to_ask.append(entry)
            if not to_ask:
                continue
            needed = math.ceil(len(to_ask) / BATCH) + 1
            if needed > remaining_calls:
                self.report["stop_reason"] = "call_ceiling_reached"
                for entry in to_ask:
                    self.skip("left_for_the_next_run_by_the_call_ceiling", entry["identity"])
                continue
            identities_file = self.folder / f"group-{number}-identities.txt"
            identities_file.write_text("".join(entry["identity"] + "\n" for entry in to_ask), encoding="utf-8")
            panel_ledger = self.folder / f"group-{number}-ledger.jsonl"
            summary = self.review_call.review(
                catalogue=candidate_folder, identities_file=identities_file, reviewer_id=reviewer_id,
                exclusions=exclusions_for(self.panel, reviewer_id), ledger=panel_ledger,
                output=self.folder / f"group-{number}-review.json", call_ceiling=needed,
                token_ceiling=remaining_tokens, calls_left=needed, log=self.folder / f"group-{number}.log")
            totals = summary.get("totals", {})
            calls, charged = int(totals.get("calls", 0)), int(totals.get("charged_tokens", 0))
            remaining_calls, remaining_tokens = remaining_calls - calls, max(0, remaining_tokens - charged)
            self.report["calls"] += calls
            self.report["charged_tokens"] += charged
            self.report["groups"].append({"number": number, "candidate_folder": candidate_folder,
                                          "reviewer": reviewer_id, "items": len(to_ask), "calls": calls,
                                          "charged_tokens": charged, "stop_reason": summary.get("stop_reason", ""),
                                          "failed": bool(summary.get("failed")), "reason": summary.get("reason", ""),
                                          "ineligible": summary.get("ineligible", {})})
            self.settle(to_ask, reviewer, panel_ledger, ledger, summary)
            if remaining_tokens == 0:
                self.report["stop_reason"] = "token_ceiling_reached"
                break
        return self.finish()

    def settle(self, asked, reviewer, panel_ledger: Path, ledger: OracleLedger, summary: dict) -> None:
        """Read the panel ledger and write one oracle row for each item asked."""
        try:
            read = ReviewLedger(panel_ledger) if panel_ledger.exists() else None
        except Exception as error:  # noqa: BLE001 - a ledger that cannot be read is recorded, never read as a verdict
            read = None
            self.report["groups"][-1]["ledger_error"] = str(error)[:200]
        ledgers = ([(panel_ledger.name, read, {(row["run_id"], row["sequence"]): row
                                                 for row in read.calls() + read.batch_calls()})] if read else [])
        for entry in asked:
            found = verdicts_for(ledgers, reviewer, entry["request"], self.instructions) if ledgers else []
            if not found:
                outcome = _attempt_outcome(read, entry["identity"]) if read else ""
                if not outcome:
                    outcome = NOT_ASKED + (summary.get("reason") or summary.get("stop_reason") or "no_call")
                self.record(entry, ledger, self.row(entry, attempt_outcome=outcome, panel_ledger=str(panel_ledger)))
                continue
            name, verdict, call = next(((n, v, c) for n, v, c in found if v["decision"] == REJECT), found[0])
            if verdict["body_sha256"] != entry["request"].body_sha256 or verdict["reported_model"] != reviewer.model:
                self.record(entry, ledger, self.row(entry, attempt_outcome="verdict_binding_invalid",
                                                    panel_ledger=str(panel_ledger)))
                continue
            row = self.row(entry, verdict=verdict["decision"], attempt_outcome="verdict",
                           reasons=verdict["reasons"] if verdict["decision"] == REJECT else "",
                           findings=list(verdict["findings"]),
                           call_ref=f"{name}#{verdict['run_id']}#{verdict['sequence']}", panel_ledger=str(panel_ledger))
            if verdict["decision"] == REJECT:
                row["withdrawal_candidate"] = self.withdrawal(entry, row, REJECT)
            elif entry["second_family"]:
                row["upgrade_candidate"] = self.upgrade(entry, row)
            self.record(entry, ledger, row)

    def finish(self) -> dict:
        self.report["finished_at"] = _timestamp(datetime.now(timezone.utc))
        self.report["stop_reason"] = self.report["stop_reason"] or "completed"
        self.report["ledger"] = str(self.options.ledger)
        _write_json(self.folder / "report.json", self.report)
        return self.report


def run(options, review_call=None, now=None) -> dict:
    """One oracle run. Without ``--authorize-model-calls`` it reports the sample and asks nobody."""
    if review_call is None:
        review_call = CampaignReviewCall(Path(options.repository), options.python, Path(options.campaign),
                                         authorized=options.authorize_model_calls,
                                         timeout_seconds=options.group_timeout_seconds)
    return OracleRun(options, review_call, now).run()


def parser() -> argparse.ArgumentParser:
    parse = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parse.add_argument("--bundles-root", type=Path, default=BUNDLES)
    parse.add_argument("--bundle", type=Path, help="One bundle folder; the newest daily bundle otherwise.")
    parse.add_argument("--library", type=Path, default=LIBRARY)
    parse.add_argument("--reviewed-folders-file", type=Path,
                       help="Defaults to LIBRARY/release-folders/reviewed-folders.txt.")
    parse.add_argument("--reviewed-folder", action="append", default=[], help="One more reviewed folder.")
    parse.add_argument("--candidate-root", action="append", default=[],
                       help="A folder whose subfolders are licensed import exports; LIBRARY/review-batches otherwise.")
    parse.add_argument("--ledger", type=Path, help="Defaults to LIBRARY/oracle/review-ledger.jsonl.")
    parse.add_argument("--withdrawals", type=Path, help="Defaults to LIBRARY/oracle/withdrawals.")
    parse.add_argument("--upgrades", type=Path, help="Defaults to LIBRARY/oracle/upgrades.")
    parse.add_argument("--runs", type=Path, help="Defaults to LIBRARY/oracle/runs.")
    parse.add_argument("--calibration-root", type=Path, help="Defaults to LIBRARY/daily.")
    parse.add_argument("--calibration-hours", type=float, default=36.0)
    parse.add_argument("--panel", type=Path, default=PANEL)
    parse.add_argument("--reviewer", action="append", default=[],
                       help="Reviewer installations in preference order; the Tactical reviewer otherwise.")
    parse.add_argument("--second-family-only", action="store_true",
                       help="Ask only a family that has not judged the item yet.")
    parse.add_argument("--sample", type=int, default=DEFAULT_SAMPLE)
    parse.add_argument("--set-aside-after", type=int, default=3,
                       help="Attempts without a verdict after which an item is set aside.")
    parse.add_argument("--call-ceiling", type=int, default=8)
    parse.add_argument("--token-ceiling", type=int, default=4_000_000)
    parse.add_argument("--group-timeout-seconds", type=float, default=3600.0)
    parse.add_argument("--authorize-model-calls", action="store_true")
    parse.add_argument("--run-id", default="")
    parse.add_argument("--repository", type=Path, default=REPOSITORY)
    parse.add_argument("--python", default=sys.executable)
    parse.add_argument("--campaign", type=Path, default=CAMPAIGN)
    return parse


def settle_defaults(options) -> argparse.Namespace:
    library = Path(options.library)
    options.reviewed_folders_file = options.reviewed_folders_file or library / "release-folders/reviewed-folders.txt"
    options.candidate_root = options.candidate_root or [library / "review-batches"]
    options.ledger = options.ledger or library / "oracle/review-ledger.jsonl"
    options.withdrawals = options.withdrawals or library / "oracle/withdrawals"
    options.upgrades = options.upgrades or library / "oracle/upgrades"
    options.runs = options.runs or library / "oracle/runs"
    options.calibration_root = options.calibration_root or library / "daily"
    options.reviewer = options.reviewer or [DEFAULT_REVIEWER]
    if options.sample < 1 or options.call_ceiling < 1 or options.token_ceiling < 1:
        refuse("invalid_options", "the sample, the call ceiling and the token ceiling are whole numbers above zero")
    return options


def main(argv=None) -> int:
    options = parser().parse_args(argv)
    try:
        report = run(settle_defaults(options))
    except OracleError as error:
        print(json.dumps({"record_type": REPORT_RECORD, "refused": True, "message": str(error)}))
        return 2
    print(json.dumps({key: report[key] for key in ("run_id", "bundle", "served", "skipped", "calls", "charged_tokens",
                                                    "verdicts", "precheck_refusals", "stop_reason")}
                     | {"sampled": len(report["sampled"]), "withdrawal_candidates": len(report["withdrawal_candidates"]),
                        "upgrade_candidates": len(report["upgrade_candidates"]), "report": str(Path(options.runs)
                                                                                                / report["run_id"] / "report.json")},
                     sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
