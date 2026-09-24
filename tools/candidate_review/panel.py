"""The review panel: the envelope that decides one candidate at a time behind the fixed reviewer edge.

For each candidate the panel:

1. runs the six deterministic pre-checks; a refusal ends the item before any
   reviewer is asked;
2. needs explicit model call authority before any call;
3. takes the enabled, available installations in declared order and removes
   every one whose family produced the item;
4. spends no call when the remaining families cannot reach the quorum;
5. reuses every verdict the ledger already holds for the same review key (the
   same installation, the same exact request and the same exact prompt), and
   never repeats a call that was dispatched and not completed;
6. asks reviewers one at a time, a new family first, until the declared number
   of reviewers answered, within the call and token ceilings; a rate limit
   pauses for a bounded, recorded time and retries; a spent allowance stops
   every installation that shares it for the rest of the run; a refused login,
   an unknown model, a route policy refusal or a missing engine stops that
   installation for the rest of the run, so a known failure is not repeated for
   every item;
7. counts an answer only when it is one valid verdict bound to the exact bytes
   it was asked about; any other answer or failed call is replaced by the next
   reviewer;
8. applies the rule: any rejection keeps the item a candidate with its
   reasons; approval needs the declared number of approvals from the declared
   number of distinct families, none of them the producer's. An approval from
   the producer's family never counts, even if a defect let that family be
   asked.

Items run one after another, or several at a time when the run request allows
it; one item's reviewers are always asked in sequence, so a spent allowance or
a stop is seen before the next call. Every call is written to the ledger with
its model, route or command, version, usage exactly as reported (unknown stays
unknown), charge, pause and outcome. Every text written is scanned with the
secret patterns first and a secret-shaped value is replaced.

A run request may also declare, each with its own recorded effect:

- a batch size per installation: that reviewer is asked about several items in
  one call, each item still chosen by the same reviewer order, each verdict
  bound to its own item's digest, and one bad verdict costing only its own
  item (the calibration decides whether a reviewer is asked this way);
- a call ceiling per quota group: a group that reaches it is asked no more in
  the run, as if its allowance were spent, while other groups continue;
- a limit on repeated identical failures: an installation that fails the same
  way that many calls in a row is asked no more in the run;
- a written reason to collect verdicts below the quorum: while a family is out
  of reach, the families that remain are each asked once, the approval rule is
  unchanged, and the stored verdicts wait in the ledger for the missing
  families, which a later run asks without asking the others again.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
import threading
import time

from .configuration import FIXTURE_ENGINE_KIND, thawed
from .ledger import ReviewLedger
from .prechecks import PrecheckContext, run_prechecks
from .prechecks.secrets import secret_patterns
from .prompt import MAXIMUM_BATCH, build_batch_prompt, build_prompt, member_prompt_sha256
from .records import (
    BATCH_CALL_RECORD, BATCH_DISPATCH_RECORD, CALL_RECORD, DISPATCH_RECORD, RUN_END_RECORD, RUN_RECORD,
    VERDICT_RECORD, CandidateReviewError, digest, refuse,
)
from .reviewers import (
    ANSWERED, AUTHENTICATION_UNAVAILABLE, ENGINE_UNAVAILABLE, MODEL_IDENTITY_MISMATCH, MODEL_NOT_FOUND, PROVIDER_FAILED, RATE_LIMITED,
    REFUSED_BY_ROUTE_POLICY, USAGE_LIMIT_REACHED, CallAllowance, failed,
)
from .verdicts import APPROVE, JSON_ONLY, REJECT, parse_batch_verdicts, parse_verdict

APPROVED, REJECTED, REFUSED_BEFORE_REVIEW = "approved", "rejected", "refused_before_review"
PANEL_INCOMPLETE, NOT_STARTED = "panel_incomplete", "not_started"
ITEM_OUTCOMES = (APPROVED, REJECTED, REFUSED_BEFORE_REVIEW, PANEL_INCOMPLETE, NOT_STARTED)
FAMILY_QUORUM_RULE = "family_quorum_approval"
REJECTION_RULE = "one_written_objection_withholds_approval"
PRECHECK_RULE = "refused_by_deterministic_prechecks"
INCOMPLETE_RULE = "no_standing_verdict_yet"
NOT_STARTED_RULE = "the_run_stopped_before_this_item"
#: Call outcomes beyond the engine's own: an answer that is not a valid verdict, and a verdict.
VERDICT_OUTCOME, INVALID_RESPONSE, INTERRUPTED = "verdict", "invalid_response", "interrupted"
#: A batch call the reviewer answered, whose member rows name each item's own outcome, and a member whose
#: call failed before any answer.
BATCH_ANSWERED, NOT_ANSWERED = "batch_answered", "not_answered"
#: Why an installation was not asked.
PRODUCER_FAMILY, DISABLED, FIXTURE_OUTSIDE_FIXTURE_RUN = "producer_family", "disabled", "fixture_outside_fixture_run"
ENGINE_NOT_BUILT = "engine_not_built"
#: Failures that do not change within one run. The installation that reports one is asked no more in that run,
#: and the record names it with this prefix and the failure. A mutant control empties this set.
LASTING_FAILURES = frozenset({AUTHENTICATION_UNAVAILABLE, MODEL_NOT_FOUND, REFUSED_BY_ROUTE_POLICY,
                              ENGINE_UNAVAILABLE})
UNUSABLE_DURING_RUN = "unusable_during_run:"
#: The reason an installation that failed the same way too many calls in a row is asked no more in the run.
REPEATED_FAILURE = "repeated_failure:"
#: Outcomes that never count toward a repeated failure: a rate limit is paused and retried, and a spent
#: allowance or a lasting failure already stops the installation.
NOT_A_REPEATABLE_FAILURE = frozenset({RATE_LIMITED, USAGE_LIMIT_REACHED})
#: Why an item has no standing verdict.
NOT_ENOUGH_FAMILIES, APPROVALS_BELOW_QUORUM = "not_enough_families", "approvals_below_quorum"
#: Why a run stopped.
COMPLETED, CALL_CEILING_REACHED, TOKEN_CEILING_REACHED = "completed", "call_ceiling_reached", "token_ceiling_reached"
MODEL_CALLS_NOT_AUTHORIZED = "model_calls_not_authorized"
CHARGED_AS_REPORTED, CHARGED_AT_RESERVATION = "reported", "reservation"
REDACTED = "[redacted: a secret-shaped value]"
OVERHEAD_SETTING = "reserved_overhead_tokens"
#: How much of an answer that is not a valid verdict the call row keeps, redacted, as evidence of the failure.
EXCERPT_CHARACTERS = 400
DEFAULT_TIMEOUT_SECONDS = 600.0


def review_key(installation, request, prompt) -> str:
    """One installation, one exact request and the exact prompt it was sent: the unit never reviewed twice.

    The prompt is part of the key because a verdict answers the words its
    reviewer read. A changed prompt is a new review, and the ledger keeps both."""
    return review_key_for(installation, request, prompt.sha256)


def review_key_for(installation, request, prompt_sha256: str) -> str:
    """The review key for a prompt digest: a single prompt's, or a batch member's own digest."""
    return digest({"installation_sha256": installation.sha256, "request_sha256": request.request_sha256,
                   "prompt_sha256": prompt_sha256, "record_type": VERDICT_RECORD,
                   "request_record_type": request.to_record()["record_type"]})


def distinct_families(members, family_of) -> int:
    return len({family_of[member] for member in members})


def producer_family_excluded(installation, producer) -> bool:
    return installation.family == producer.family


def counts_toward_approval(family: str, producer_family: str) -> bool:
    """An approval counts only from a family that did not produce the item. A mutant control replaces this."""
    return family != producer_family


def answering_model_matches(installation, attempt) -> bool:
    """Every engine must report the exact configured reviewer identity before its answer can count."""
    return type(attempt.reported_model) is str and attempt.reported_model == installation.model


def _timestamp(seconds: float) -> str:
    return datetime.fromtimestamp(seconds, timezone.utc).isoformat().replace("+00:00", "Z")


class Budget:
    """The declared ceilings of one run. A call is reserved before it is dispatched, and settled after."""

    def __init__(self, call_ceiling: int, token_ceiling: int) -> None:
        self.call_ceiling, self.token_ceiling = call_ceiling, token_ceiling
        self.calls, self.charged, self.reserved = 0, 0, 0
        self.stop_reason = ""
        self._lock = threading.Lock()

    def reserve(self, tokens: int) -> bool:
        with self._lock:
            if self.calls + 1 > self.call_ceiling:
                self.stop_reason = CALL_CEILING_REACHED
                return False
            if self.charged + self.reserved + tokens > self.token_ceiling:
                self.stop_reason = TOKEN_CEILING_REACHED
                return False
            self.calls += 1
            self.reserved += tokens
            return True

    def settle(self, reserved: int, charged: int) -> None:
        with self._lock:
            self.reserved -= reserved
            self.charged += charged

    def to_dict(self) -> dict:
        return {"call_ceiling": self.call_ceiling, "token_ceiling": self.token_ceiling, "calls_reserved": self.calls,
                "tokens_charged": self.charged}


@dataclass(frozen=True)
class PanelRunRequest:
    run_id: str
    requests: tuple
    population: object
    call_ceiling: int
    token_ceiling: int
    model_calls_authorized: bool
    fixture_run: bool = False
    item_concurrency: int = 1
    #: Calibration asks every eligible reviewer about every item instead of stopping at the quorum.
    ask_every_eligible_reviewer: bool = False
    #: Installations this run must not ask, each with its written reason (for example a failed calibration).
    excluded_installations: dict = field(default_factory=dict)
    #: How many items one call asks each installation about; an installation not named is asked one at a time.
    batch_sizes: dict = field(default_factory=dict)
    #: When not empty, why verdicts are collected although the reachable families cannot reach the quorum.
    collect_below_quorum_reason: str = ""
    #: The most calls each named quota group may take in this run; a group not named has no own ceiling.
    quota_group_call_ceilings: dict = field(default_factory=dict)
    #: After this many identical failures in a row an installation is asked no more in the run; zero is off.
    repeated_failure_limit: int = 0

    def __post_init__(self):
        if type(self.run_id) is not str or not self.run_id.strip():
            refuse("invalid_run_request", "a run has an identity")
        for name in ("call_ceiling", "token_ceiling"):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                refuse("invalid_run_request", f"{name} is a declared whole number of zero or more")
        if type(self.model_calls_authorized) is not bool or type(self.fixture_run) is not bool:
            refuse("invalid_run_request", "model call authority and the fixture flag are true or false")
        if type(self.item_concurrency) is not int or not 1 <= self.item_concurrency <= 8:
            refuse("invalid_run_request", "item_concurrency is a whole number from 1 to 8")
        if type(self.ask_every_eligible_reviewer) is not bool or type(self.excluded_installations) is not dict \
                or any(type(reason) is not str or not reason.strip()
                       for reason in self.excluded_installations.values()):
            refuse("invalid_run_request", "an excluded installation carries a written reason")
        identities = [request.identity for request in self.requests]
        if not identities or len(set(identities)) != len(identities):
            refuse("invalid_run_request", "a run reviews at least one item and each item once")
        if type(self.batch_sizes) is not dict or any(
                type(name) is not str or type(size) is not int or not 1 <= size <= MAXIMUM_BATCH
                for name, size in self.batch_sizes.items()):
            refuse("invalid_run_request", f"a batch size names an installation and is a whole number from 1 to "
                                          f"{MAXIMUM_BATCH}")
        if type(self.collect_below_quorum_reason) is not str or len(self.collect_below_quorum_reason) > 2000:
            refuse("invalid_run_request", "the reason to collect verdicts below the quorum is text")
        if type(self.quota_group_call_ceilings) is not dict or any(
                type(name) is not str or type(ceiling) is not int or ceiling < 0
                for name, ceiling in self.quota_group_call_ceilings.items()):
            refuse("invalid_run_request", "a quota group ceiling is a whole number of zero or more")
        if type(self.repeated_failure_limit) is not int or self.repeated_failure_limit < 0:
            refuse("invalid_run_request", "the repeated failure limit is a whole number of zero or more")

    @property
    def batched(self) -> bool:
        return any(size > 1 for size in self.batch_sizes.values())

    @property
    def below_quorum(self) -> bool:
        return bool(self.collect_below_quorum_reason.strip())


@dataclass
class ItemResult:
    identity: str
    request: object
    prechecks: object
    verdicts: list
    outcome: str
    rule_applied: str
    reasons: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"identity": self.identity, "body_sha256": self.request.body_sha256,
                "request_sha256": self.request.request_sha256, "prechecks": self.prechecks.to_dict(),
                "verdicts": list(self.verdicts), "outcome": self.outcome, "rule_applied": self.rule_applied,
                "reasons": list(self.reasons)}


@dataclass
class PanelRunResult:
    run_id: str
    items: list
    calls: list
    stop_reason: str
    ineligible: dict
    spent_quota_groups: set
    interrupted: set
    availability: dict
    started_at: str
    finished_at: str
    elapsed_seconds: float
    budget: dict
    pause_seconds: float
    #: Quota groups that reached their own call ceiling in this run.
    capped_quota_groups: set = field(default_factory=set)

    def totals(self) -> dict:
        outcomes = [item.outcome for item in self.items]
        disagreements = sum(1 for item in self.items
                            if {verdict["decision"] for verdict in item.verdicts} == {APPROVE, REJECT})
        by_outcome = {}
        for call in self.calls:
            by_outcome[call["outcome"]] = by_outcome.get(call["outcome"], 0) + 1
        known = [call["physical_model_calls"] for call in self.calls if call["physical_model_calls"] is not None]
        reported = [call["usage"] for call in self.calls if call["usage"]["input_tokens"] is not None
                    and call["usage"]["output_tokens"] is not None]
        return {"items": len(self.items), **{outcome: outcomes.count(outcome) for outcome in ITEM_OUTCOMES},
                "disagreements": disagreements, "calls": len(self.calls), "calls_by_outcome": by_outcome,
                "physical_model_calls_known": sum(known),
                "calls_with_unknown_physical_count": len(self.calls) - len(known),
                "calls_with_unknown_usage": len(self.calls) - len(reported),
                "input_tokens_reported": sum(usage["input_tokens"] for usage in reported),
                "output_tokens_reported": sum(usage["output_tokens"] for usage in reported),
                "charged_tokens": sum(call["charged_tokens"] for call in self.calls),
                "pause_seconds": self.pause_seconds, "elapsed_seconds": self.elapsed_seconds}

    def to_dict(self) -> dict:
        return {"run_id": self.run_id, "stop_reason": self.stop_reason, "started_at": self.started_at,
                "finished_at": self.finished_at, "items": [item.to_dict() for item in self.items],
                "calls": list(self.calls), "ineligible": dict(self.ineligible),
                "spent_quota_groups": sorted(self.spent_quota_groups),
                "capped_quota_groups": sorted(self.capped_quota_groups), "interrupted": sorted(self.interrupted),
                "budget": dict(self.budget), "totals": self.totals()}


class _RunState:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.stop_reason = ""
        self.spent = set()
        self.pause_total = 0.0
        self.sequence = 0
        self.calls = []
        self.interrupted = set()
        self.ineligible = {}
        self.unusable = set()
        self.capped = set()
        self.group_calls = {}
        self.streaks = {}


class ReviewPanel:
    """One configured panel: its policy, criteria, instructions, engines and ledger."""

    def __init__(self, configuration, criteria, instructions, reviewers, prechecks, ledger: ReviewLedger, *,
                 sleeper=time.sleep, clock=time.time) -> None:
        self.configuration, self.policy = configuration, configuration.policy
        self.criteria, self.instructions = criteria, instructions
        self.reviewers, self.prechecks, self.ledger = dict(reviewers), dict(prechecks), ledger
        self.sleeper, self.clock = sleeper, clock
        self.patterns = secret_patterns(configuration.engine_settings("builtin_secret_patterns"))
        self.family_of = {item.installation_id: item.family for item in configuration.installations}

    def _redacted(self, value):
        if isinstance(value, str):
            for pattern in self.patterns:
                value = pattern.sub(REDACTED, value)
            return value
        if isinstance(value, dict):
            return {key: self._redacted(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._redacted(item) for item in value]
        return value

    def run(self, run_request: PanelRunRequest) -> PanelRunResult:
        started = self.clock()
        state = _RunState()
        availability, eligible = {}, []
        for installation in self.configuration.installations:
            reason = self._ineligible(installation, run_request)
            if reason:
                state.ineligible[installation.installation_id] = reason
                continue
            probe = self.reviewers[installation.installation_id].availability()
            availability[installation.installation_id] = probe
            if not probe.available:
                state.ineligible[installation.installation_id] = probe.reason_code or ENGINE_UNAVAILABLE
                continue
            eligible.append(installation)
        self.ledger.start_run({
            "record_type": RUN_RECORD, "run_id": run_request.run_id, "started_at": _timestamp(started),
            "policy_sha256": self.policy.sha256, "call_ceiling": run_request.call_ceiling,
            "token_ceiling": run_request.token_ceiling, "fixture_run": run_request.fixture_run,
            "requests": [request.request_sha256 for request in run_request.requests]})
        budget = Budget(run_request.call_ceiling, run_request.token_ceiling)
        if not run_request.model_calls_authorized:
            state.stop_reason = MODEL_CALLS_NOT_AUTHORIZED

        def one(request):
            return self._item(request, run_request, eligible, availability, budget, state)

        if run_request.batched:
            items = self._items_batched(run_request, eligible, availability, budget, state)
        elif run_request.item_concurrency == 1:
            items = [one(request) for request in run_request.requests]
        else:
            with ThreadPoolExecutor(max_workers=run_request.item_concurrency) as pool:
                items = list(pool.map(one, run_request.requests))
        finished = self.clock()
        self.ledger.end_run({
            "record_type": RUN_END_RECORD, "run_id": run_request.run_id, "finished_at": _timestamp(finished),
            "stop_reason": state.stop_reason or COMPLETED, "elapsed_seconds": round(finished - started, 3),
            "calls": len(state.calls), "items": len(items), "pause_seconds": round(state.pause_total, 3)})
        return PanelRunResult(run_request.run_id, items, list(state.calls), state.stop_reason or COMPLETED,
                              dict(state.ineligible), set(state.spent), set(state.interrupted), availability,
                              _timestamp(started), _timestamp(finished), round(finished - started, 3),
                              budget.to_dict(), round(state.pause_total, 3), set(state.capped))

    def _ineligible(self, installation, run_request) -> str:
        if installation.installation_id in run_request.excluded_installations:
            return run_request.excluded_installations[installation.installation_id]
        if not installation.enabled:
            return DISABLED
        if installation.engine_kind == FIXTURE_ENGINE_KIND and not run_request.fixture_run:
            return FIXTURE_OUTSIDE_FIXTURE_RUN
        if installation.installation_id not in self.reviewers:
            return ENGINE_NOT_BUILT
        return ""

    def _item(self, request, run_request, eligible, availability, budget, state) -> ItemResult:
        prechecks = run_prechecks(request, self.prechecks, PrecheckContext(self.policy, run_request.population))
        if prechecks.refused:
            return ItemResult(request.identity, request, prechecks, [], REFUSED_BEFORE_REVIEW, PRECHECK_RULE,
                              list(prechecks.reasons))
        candidates = []
        for installation in eligible:
            if producer_family_excluded(installation, request.producer):
                with state.lock:
                    state.ineligible.setdefault(installation.installation_id, PRODUCER_FAMILY)
                continue
            candidates.append(installation)
        verdicts, tried = {}, set()
        prompts = {installation.installation_id: build_prompt(request, installation, self.instructions)
                   for installation in candidates}
        for installation in candidates:
            key = review_key(installation, request, prompts[installation.installation_id])
            stored = self.ledger.verdict(key)
            if stored is not None:
                verdicts[installation.installation_id] = stored
                tried.add(installation.installation_id)
            elif self.ledger.interrupted(key):
                tried.add(installation.installation_id)
                with state.lock:
                    state.interrupted.add(key)
        with state.lock:
            stopped = state.stop_reason
        if stopped and not verdicts:
            return ItemResult(request.identity, request, prechecks, [], NOT_STARTED, NOT_STARTED_RULE, [stopped])
        every = run_request.ask_every_eligible_reviewer
        if not every and not run_request.below_quorum and \
                distinct_families([item.installation_id for item in candidates], self.family_of) \
                < self.policy.minimum_distinct_families:
            return self._decided(request, prechecks, verdicts, extra=[NOT_ENOUGH_FAMILIES])
        target = len(candidates) if every else self.policy.reviewers_per_item
        while len(verdicts) < target:
            if self.policy.stop_asking_after_first_rejection and any(
                    row["decision"] == REJECT for row in verdicts.values()):
                break
            with state.lock:
                if state.stop_reason:
                    break
            installation = (self._next_in_order(candidates, tried, state) if every
                            else self._next(candidates, tried, verdicts, state, run_request.below_quorum))
            if installation is None:
                break
            tried.add(installation.installation_id)
            verdict = self._ask(installation, request, prompts[installation.installation_id], availability, budget,
                                state, run_request)
            if verdict is not None:
                verdicts[installation.installation_id] = verdict
        if not verdicts:
            with state.lock:
                stopped = bool(state.stop_reason)
            if stopped:
                return ItemResult(request.identity, request, prechecks, [], NOT_STARTED, NOT_STARTED_RULE,
                                  [state.stop_reason])
        return self._decided(request, prechecks, verdicts)

    @staticmethod
    def _next_in_order(candidates, tried, state):
        with state.lock:
            spent, unusable = set(state.spent) | set(state.capped), set(state.unusable)
        return next((item for item in candidates if item.installation_id not in tried
                     and item.installation_id not in unusable and item.quota_group not in spent), None)

    def _next(self, candidates, tried, verdicts, state, below_quorum: bool = False):
        """The next reviewer to ask: a new family first; a family already heard only once the quorum's
        families are reached; nobody when the families still reachable cannot make the quorum, unless the
        run collects verdicts below the quorum, when each reachable family is still asked once."""
        with state.lock:
            spent, unusable = set(state.spent) | set(state.capped), set(state.unusable)
        remaining = [item for item in candidates if item.installation_id not in tried
                     and item.installation_id not in unusable and item.quota_group not in spent]
        heard = list(verdicts)
        needed = self.policy.minimum_distinct_families
        if not below_quorum and \
                distinct_families(heard + [item.installation_id for item in remaining], self.family_of) < needed:
            return None
        current = distinct_families(heard, self.family_of)
        for item in remaining:
            if distinct_families(heard + [item.installation_id], self.family_of) > current:
                return item
        return remaining[0] if remaining and current >= needed else None

    def _ask(self, installation, request, prompt, availability, budget, state, run_request):
        engine = self.reviewers[installation.installation_id]
        settings = thawed(installation.settings)
        allowance = CallAllowance(getattr(engine, "output_allocation_tokens", None)
                                  or self.policy.output_allocation_tokens,
                                  float(settings.get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS)),
                                  self.policy.temperature)
        answer_format = getattr(engine, "answer_format", JSON_ONLY)
        overhead = settings.get(OVERHEAD_SETTING, 0)
        reservation = prompt.estimated_input_tokens + allowance.max_output_tokens + \
            (overhead if type(overhead) is int and overhead > 0 else 0)
        key = review_key(installation, request, prompt)
        probe = availability.get(installation.installation_id)
        retries = 0
        while True:
            with state.lock:
                if state.stop_reason or installation.quota_group in state.spent \
                        or installation.installation_id in state.unusable:
                    return None
            if not self._claim_group_call(installation, run_request, state):
                return None
            if not budget.reserve(reservation):
                with state.lock:
                    state.stop_reason = state.stop_reason or budget.stop_reason
                return None
            with state.lock:
                state.sequence += 1
                sequence = state.sequence
            started = self.clock()
            self.ledger.dispatch({
                "record_type": DISPATCH_RECORD, "run_id": run_request.run_id, "sequence": sequence,
                "review_key": key, "installation_id": installation.installation_id, "identity": request.identity,
                "body_sha256": request.body_sha256, "request_sha256": request.request_sha256,
                "request_record_type": request.to_record()["record_type"],
                "dispatched_at": _timestamp(started)})
            try:
                attempt = engine.review(prompt, allowance)
            except CandidateReviewError as error:
                attempt = failed(ENGINE_UNAVAILABLE, installation.installation_id, error.code,
                                 physical_model_calls=None)
            except Exception as error:  # noqa: BLE001 - an engine defect is recorded, never read as a verdict
                attempt = failed(PROVIDER_FAILED, installation.installation_id, type(error).__name__,
                                 physical_model_calls=None)
            if attempt.outcome == ANSWERED and not answering_model_matches(installation, attempt):
                attempt = replace(attempt, outcome=MODEL_IDENTITY_MISMATCH, text="",
                                  error_detail="reviewer_answering_model_mismatch")
            content, error_code = None, ""
            if attempt.outcome == ANSWERED:
                content, error_code = parse_verdict(attempt.text, body_sha256=request.body_sha256,
                                                    criteria_ids=request.applicable_criteria_ids,
                                                    answer_format=answer_format)
            else:
                error_code = attempt.error_detail[:120] or attempt.outcome
            outcome = VERDICT_OUTCOME if content else (INVALID_RESPONSE if attempt.outcome == ANSWERED
                                                       else attempt.outcome)
            usage = attempt.usage
            charged, basis = ((usage.total, CHARGED_AS_REPORTED) if usage.complete
                              else (reservation, CHARGED_AT_RESERVATION))
            budget.settle(reservation, charged)
            pause = 0.0
            if attempt.outcome == RATE_LIMITED and retries < self.policy.rate_limit.maximum_retries_per_call:
                pause = self._pause(attempt.retry_after_seconds, retries, state)
            call = self._redacted({
                "record_type": CALL_RECORD, "run_id": run_request.run_id, "sequence": sequence, "review_key": key,
                "installation_id": installation.installation_id, "installation_sha256": installation.sha256,
                "engine_kind": installation.engine_kind, "family": installation.family, "model": installation.model,
                "reported_model": attempt.reported_model,
                "request_record_type": request.to_record()["record_type"],
                "model_version": dict(probe.model_version) if probe else {},
                "engine_version": probe.engine_version if probe else "",
                "route_or_command": attempt.route_or_command, "identity": request.identity,
                "body_sha256": request.body_sha256, "request_sha256": request.request_sha256,
                "prompt_sha256": prompt.sha256, "started_at": _timestamp(started),
                "elapsed_seconds": attempt.elapsed_seconds, "outcome": outcome, "error_code": error_code,
                "decision": content.decision if content else "",
                "invalid_answer_excerpt": attempt.text[:EXCERPT_CHARACTERS] if outcome == INVALID_RESPONSE else "",
                "physical_model_calls": attempt.physical_model_calls,
                "physical_calls_basis": attempt.physical_calls_basis, "usage": usage.to_dict(),
                "reserved_tokens": reservation, "charged_tokens": charged, "charge_basis": basis,
                "retry_after_seconds": attempt.retry_after_seconds, "pause_seconds_after": pause})
            verdict = None
            if content is not None:
                verdict = self._redacted({
                    "record_type": VERDICT_RECORD, "run_id": run_request.run_id, "sequence": sequence,
                    "review_key": key, "installation_id": installation.installation_id,
                    "family": installation.family, "identity": request.identity,
                    "body_sha256": request.body_sha256, "request_sha256": request.request_sha256,
                    "reported_model": attempt.reported_model,
                    "request_record_type": request.to_record()["record_type"],
                    **content.to_dict()})
            self.ledger.complete(call, verdict)
            with state.lock:
                state.calls.append(call)
            self._note_failure(installation, None if verdict is not None else (outcome, error_code),
                               run_request, state)
            if verdict is not None:
                return verdict
            if attempt.outcome == USAGE_LIMIT_REACHED:
                with state.lock:
                    state.spent.add(installation.quota_group)
                return None
            if attempt.outcome in LASTING_FAILURES:
                with state.lock:
                    state.unusable.add(installation.installation_id)
                    state.ineligible[installation.installation_id] = UNUSABLE_DURING_RUN + attempt.outcome
                return None
            if pause > 0:
                self.sleeper(pause)
                retries += 1
                continue
            return None

    def _items_batched(self, run_request, eligible, availability, budget, state) -> list:
        """Every item through the same reviewer order as one at a time, with calls grouped per reviewer.

        Each round finds, for every item still short of verdicts, the reviewer the item-at-a-time order would
        ask next, and asks each chosen reviewer about its items together, in calls of at most its batch size.
        Items fail, retry and move to the next reviewer on their own. Rounds for different reviewers run side by
        side up to the run's item concurrency; one reviewer's calls run in sequence."""
        decided, pending = {}, []
        every, below = run_request.ask_every_eligible_reviewer, run_request.below_quorum
        for request in run_request.requests:
            prechecks = run_prechecks(request, self.prechecks, PrecheckContext(self.policy, run_request.population))
            if prechecks.refused:
                decided[request.identity] = ItemResult(request.identity, request, prechecks, [],
                                                       REFUSED_BEFORE_REVIEW, PRECHECK_RULE, list(prechecks.reasons))
                continue
            candidates = []
            for installation in eligible:
                if producer_family_excluded(installation, request.producer):
                    with state.lock:
                        state.ineligible.setdefault(installation.installation_id, PRODUCER_FAMILY)
                    continue
                candidates.append(installation)
            verdicts, tried = {}, set()
            for installation in candidates:
                key = self._key(installation, request, run_request)
                stored = self.ledger.verdict(key)
                if stored is not None:
                    verdicts[installation.installation_id] = stored
                    tried.add(installation.installation_id)
                elif self.ledger.interrupted(key):
                    tried.add(installation.installation_id)
                    with state.lock:
                        state.interrupted.add(key)
            with state.lock:
                stopped = state.stop_reason
            if stopped and not verdicts:
                decided[request.identity] = ItemResult(request.identity, request, prechecks, [], NOT_STARTED,
                                                       NOT_STARTED_RULE, [stopped])
                continue
            if not every and not below and distinct_families([item.installation_id for item in candidates],
                                                             self.family_of) < self.policy.minimum_distinct_families:
                decided[request.identity] = self._decided(request, prechecks, verdicts, extra=[NOT_ENOUGH_FAMILIES])
                continue
            pending.append({"request": request, "prechecks": prechecks, "candidates": candidates,
                            "verdicts": verdicts, "tried": tried})
        order = {installation.installation_id: position for position, installation in enumerate(eligible)}
        while True:
            groups = {}
            for row in pending:
                target = len(row["candidates"]) if every else self.policy.reviewers_per_item
                if len(row["verdicts"]) >= target:
                    continue
                if self.policy.stop_asking_after_first_rejection and any(
                        verdict["decision"] == REJECT for verdict in row["verdicts"].values()):
                    continue
                with state.lock:
                    if state.stop_reason:
                        break
                installation = (self._next_in_order(row["candidates"], row["tried"], state) if every
                                else self._next(row["candidates"], row["tried"], row["verdicts"], state, below))
                if installation is not None:
                    groups.setdefault(installation.installation_id, (installation, []))[1].append(row)
            if not groups:
                break

            def ask_group(entry):
                installation, rows = entry
                size = run_request.batch_sizes.get(installation.installation_id, 1)
                for start in range(0, len(rows), size):
                    chunk = rows[start:start + size]
                    for row in chunk:
                        row["tried"].add(installation.installation_id)
                    if size == 1:
                        request = chunk[0]["request"]
                        verdict = self._ask(installation, request,
                                            build_prompt(request, installation, self.instructions), availability,
                                            budget, state, run_request)
                        answers = {request.identity: verdict} if verdict is not None else {}
                    else:
                        answers = self._ask_batch(installation, [row["request"] for row in chunk], availability,
                                                  budget, state, run_request)
                    for row in chunk:
                        if row["request"].identity in answers:
                            row["verdicts"][installation.installation_id] = answers[row["request"].identity]

            entries = [groups[name] for name in sorted(groups, key=lambda name: order.get(name, len(order)))]
            workers = min(len(entries), run_request.item_concurrency)
            if workers == 1:
                for entry in entries:
                    ask_group(entry)
            else:
                with ThreadPoolExecutor(max_workers=workers) as pool:
                    list(pool.map(ask_group, entries))
        for row in pending:
            request, verdicts = row["request"], row["verdicts"]
            if not verdicts:
                with state.lock:
                    stopped = state.stop_reason
                if stopped:
                    decided[request.identity] = ItemResult(request.identity, request, row["prechecks"], [],
                                                           NOT_STARTED, NOT_STARTED_RULE, [stopped])
                    continue
            decided[request.identity] = self._decided(request, row["prechecks"], verdicts)
        return [decided[request.identity] for request in run_request.requests]

    def _key(self, installation, request, run_request) -> str:
        """The key an installation's verdict on this item is stored under in this run's mode of asking."""
        if run_request.batch_sizes.get(installation.installation_id, 1) > 1:
            return review_key_for(installation, request, member_prompt_sha256(request, installation,
                                                                              self.instructions))
        return review_key(installation, request, build_prompt(request, installation, self.instructions))

    def _ask_batch(self, installation, requests, availability, budget, state, run_request) -> dict:
        """One call about several items; returns each item's verdict row by identity, for the items that got one."""
        engine = self.reviewers[installation.installation_id]
        settings = thawed(installation.settings)
        allowance = CallAllowance(getattr(engine, "output_allocation_tokens", None)
                                  or self.policy.output_allocation_tokens,
                                  float(settings.get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS)),
                                  self.policy.temperature)
        answer_format = getattr(engine, "answer_format", JSON_ONLY)
        overhead = settings.get(OVERHEAD_SETTING, 0)
        batch = build_batch_prompt(requests, installation, self.instructions)
        reservation = batch.estimated_input_tokens + allowance.max_output_tokens + \
            (overhead if type(overhead) is int and overhead > 0 else 0)
        members = [(member, review_key_for(installation, member.request, member.member_prompt_sha256))
                   for member in batch.members]
        batch_key = digest({"record_type": BATCH_CALL_RECORD, "installation_sha256": installation.sha256,
                            "prompt_sha256": batch.sha256})
        probe = availability.get(installation.installation_id)
        retries = 0
        while True:
            with state.lock:
                if state.stop_reason or installation.quota_group in state.spent \
                        or installation.installation_id in state.unusable:
                    return {}
            if not self._claim_group_call(installation, run_request, state):
                return {}
            if not budget.reserve(reservation):
                with state.lock:
                    state.stop_reason = state.stop_reason or budget.stop_reason
                return {}
            with state.lock:
                state.sequence += 1
                sequence = state.sequence
            started = self.clock()
            self.ledger.dispatch({
                "record_type": BATCH_DISPATCH_RECORD, "run_id": run_request.run_id, "sequence": sequence,
                "batch_key": batch_key, "installation_id": installation.installation_id,
                "members": [self._member(position, member, key) for position, (member, key) in enumerate(members)],
                "dispatched_at": _timestamp(started)})
            try:
                attempt = engine.review(batch.as_prompt(), allowance)
            except CandidateReviewError as error:
                attempt = failed(ENGINE_UNAVAILABLE, installation.installation_id, error.code,
                                 physical_model_calls=None)
            except Exception as error:  # noqa: BLE001 - an engine defect is recorded, never read as a verdict
                attempt = failed(PROVIDER_FAILED, installation.installation_id, type(error).__name__,
                                 physical_model_calls=None)
            if attempt.outcome == ANSWERED and not answering_model_matches(installation, attempt):
                attempt = replace(attempt, outcome=MODEL_IDENTITY_MISMATCH, text="",
                                  error_detail="reviewer_answering_model_mismatch")
            results, error_code = None, ""
            if attempt.outcome == ANSWERED:
                results, error_code = parse_batch_verdicts(
                    attempt.text, members=[(member.identity, member.body_sha256,
                                            member.request.applicable_criteria_ids) for member, _key in members],
                    answer_format=answer_format)
            else:
                error_code = attempt.error_detail[:120] or attempt.outcome
            usage = attempt.usage
            charged, basis = ((usage.total, CHARGED_AS_REPORTED) if usage.complete
                              else (reservation, CHARGED_AT_RESERVATION))
            budget.settle(reservation, charged)
            pause = 0.0
            if attempt.outcome == RATE_LIMITED and retries < self.policy.rate_limit.maximum_retries_per_call:
                pause = self._pause(attempt.retry_after_seconds, retries, state)
            member_rows, verdict_rows, found = [], [], {}
            for position, (member, key) in enumerate(members):
                content, code = results[position] if results is not None else (None, error_code)
                outcome = VERDICT_OUTCOME if content else (INVALID_RESPONSE if attempt.outcome == ANSWERED
                                                           else NOT_ANSWERED)
                member_rows.append({**self._member(position, member, key), "outcome": outcome,
                                    "error_code": "" if content else code[:120],
                                    "decision": content.decision if content else ""})
                if content is not None:
                    verdict = self._redacted({
                        "record_type": VERDICT_RECORD, "run_id": run_request.run_id, "sequence": sequence,
                        "review_key": key, "installation_id": installation.installation_id,
                        "family": installation.family, "identity": member.identity,
                        "body_sha256": member.body_sha256, "request_sha256": member.request.request_sha256,
                        "reported_model": attempt.reported_model,
                        "request_record_type": member.request.to_record()["record_type"], **content.to_dict()})
                    verdict_rows.append(verdict)
                    found[member.identity] = verdict
            call_outcome = BATCH_ANSWERED if attempt.outcome == ANSWERED else attempt.outcome
            call = self._redacted({
                "record_type": BATCH_CALL_RECORD, "run_id": run_request.run_id, "sequence": sequence,
                "batch_key": batch_key, "installation_id": installation.installation_id,
                "installation_sha256": installation.sha256, "engine_kind": installation.engine_kind,
                "family": installation.family, "model": installation.model,
                "reported_model": attempt.reported_model,
                "model_version": dict(probe.model_version) if probe else {},
                "engine_version": probe.engine_version if probe else "",
                "route_or_command": attempt.route_or_command, "prompt_sha256": batch.sha256,
                "started_at": _timestamp(started), "elapsed_seconds": attempt.elapsed_seconds,
                "outcome": call_outcome, "error_code": error_code if results is None else "",
                "invalid_answer_excerpt": (attempt.text[:EXCERPT_CHARACTERS]
                                           if attempt.outcome == ANSWERED and len(found) < len(members) else ""),
                "physical_model_calls": attempt.physical_model_calls,
                "physical_calls_basis": attempt.physical_calls_basis, "usage": usage.to_dict(),
                "reserved_tokens": reservation, "charged_tokens": charged, "charge_basis": basis,
                "retry_after_seconds": attempt.retry_after_seconds, "pause_seconds_after": pause,
                "members": member_rows})
            self.ledger.complete_batch(call, verdict_rows)
            with state.lock:
                state.calls.append(call)
            if found:
                self._note_failure(installation, None, run_request, state)
                return found
            self._note_failure(installation, (call_outcome if results is None else INVALID_RESPONSE,
                                              error_code or next((row["error_code"] for row in member_rows), "")),
                               run_request, state)
            if attempt.outcome == USAGE_LIMIT_REACHED:
                with state.lock:
                    state.spent.add(installation.quota_group)
                return {}
            if attempt.outcome in LASTING_FAILURES:
                with state.lock:
                    state.unusable.add(installation.installation_id)
                    state.ineligible[installation.installation_id] = UNUSABLE_DURING_RUN + attempt.outcome
                return {}
            if pause > 0:
                self.sleeper(pause)
                retries += 1
                continue
            return {}

    @staticmethod
    def _member(position, member, key) -> dict:
        return {"position": position, "review_key": key, "identity": member.identity,
                "body_sha256": member.body_sha256, "request_sha256": member.request.request_sha256,
                "request_record_type": member.request.to_record()["record_type"],
                "member_prompt_sha256": member.member_prompt_sha256}

    @staticmethod
    def _claim_group_call(installation, run_request, state) -> bool:
        """Count one call against the installation's quota group, or refuse it at the group's own ceiling."""
        ceiling = run_request.quota_group_call_ceilings.get(installation.quota_group)
        with state.lock:
            used = state.group_calls.get(installation.quota_group, 0)
            if ceiling is not None and used >= ceiling:
                state.capped.add(installation.quota_group)
                return False
            state.group_calls[installation.quota_group] = used + 1
        return True

    @staticmethod
    def _note_failure(installation, signature, run_request, state) -> None:
        """Track identical failures in a row; at the run's limit the installation is asked no more."""
        limit = run_request.repeated_failure_limit
        with state.lock:
            if signature is None or signature[0] in NOT_A_REPEATABLE_FAILURE:
                if signature is None:
                    state.streaks.pop(installation.installation_id, None)
                return
            previous, count = state.streaks.get(installation.installation_id, (None, 0))
            count = count + 1 if previous == signature else 1
            state.streaks[installation.installation_id] = (signature, count)
            if limit and count >= limit:
                state.unusable.add(installation.installation_id)
                state.ineligible[installation.installation_id] = (
                    UNUSABLE_DURING_RUN + REPEATED_FAILURE + ":".join(str(part) for part in signature if part))

    def _pause(self, requested, retries: int, state) -> float:
        rate = self.policy.rate_limit
        wanted = requested if isinstance(requested, (int, float)) and requested > 0 \
            else rate.initial_seconds * (2 ** retries)
        with state.lock:
            pause = min(float(wanted), rate.maximum_seconds, rate.maximum_total_seconds - state.pause_total)
            if pause <= 0:
                return 0.0
            state.pause_total += pause
        return round(pause, 3)

    def _decided(self, request, prechecks, verdicts, extra=()) -> ItemResult:
        rows = [{"reviewer_id": identity, "family": row["family"], "decision": row["decision"],
                 "findings": row["findings"], "reasons": row["reasons"], "body_sha256": row["body_sha256"],
                 "request_sha256": row["request_sha256"], "review_key": row["review_key"],
                 "run_id": row["run_id"], "sequence": row["sequence"]}
                for identity, row in verdicts.items()]
        outcome, rule, reasons = decide_outcome(rows, self.policy, self.family_of, request.producer.family)
        return ItemResult(request.identity, request, prechecks, rows, outcome, rule, list(extra) + reasons)


def decide_outcome(rows, policy, family_of, producer_family: str) -> tuple:
    """The rule: any rejection withholds approval; approval needs the family quorum without the producer."""
    rejections = [row for row in rows if row["decision"] == REJECT]
    if rejections:
        return REJECTED, REJECTION_RULE, [row["reasons"] for row in rejections]
    approvers = [row["reviewer_id"] for row in rows if row["decision"] == APPROVE
                 and counts_toward_approval(family_of[row["reviewer_id"]], producer_family)]
    if len(approvers) >= policy.minimum_approvals \
            and distinct_families(approvers, family_of) >= policy.minimum_distinct_families:
        return APPROVED, FAMILY_QUORUM_RULE, []
    return PANEL_INCOMPLETE, INCOMPLETE_RULE, [APPROVALS_BELOW_QUORUM]
