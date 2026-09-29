"""Acceptance sampling for batches of generated components: the plan, the sample and the written decision.

A generator batch is every qualified component one supply-line run produced. Instead of one review call
for every twelve components, a random sample of the batch goes to one calibrated reviewer from a model
family that did not write the generator, and the whole batch is accepted or withheld by a written rule.

The plan is a lot tolerance percent defective (LTPD) plan in the style of Dodge and Romig:

- the consumer's risk is exact for this batch: a batch of N components holding D1 = ceil(p1 x N) defective
  ones (p1 is the tolerance defect rate) is accepted with probability at most beta. The number of defective
  components in a sample of n drawn without replacement follows the hypergeometric distribution, so the
  probability is computed from it, not approximated;
- the producer's risk uses the generator's observed defect rate p0 (its process average over earlier
  sampled batches): a generator whose components are defective at rate p0 has a batch withheld with
  probability at most alpha. At the process rate each sampled component is defective independently, so
  this probability is binomial;
- the acceptance number c is the smallest that meets both risks, and n is the smallest sample that meets
  the consumer's risk for that c. A generator with too little history gets the zero-acceptance plan
  (c = 0), which is the smallest sample that meets the consumer's risk. A generator whose observed rate
  is at or above the tolerance rate cannot be sampled into acceptance: its batches go to every-component
  review, or wait for a repaired generator.

The decision: accept the batch when the reviewer passed every planted known-wrong control in the same run
and the sample holds at most c defective components; otherwise withhold the whole batch and flag the
generator. A sampled component the reviewer rejected is never published, even in an accepted batch.

Everything here is arithmetic over integers and floats. It reads no file, calls no model and grants no
authority.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
import random

PLAN_RECORD = "generated_batch_sampling_plan/v1"
DECISION_RECORD = "generated_batch_sampling_decision/v1"
POLICY_RECORD = "generated_batch_sampling_policy/v1"
HISTORY_RECORD = "generated_batch_sampling_history/v1"
REVIEW_RECORD = "generated_batch_sampled_review/v2"


def frame_digest(records) -> str:
    """Bind the exact qualified identities, store versions and package bytes.

    Counts alone do not identify a population. Qualification timestamps and
    current checker results may change without changing the reviewed material.
    """
    rows = sorted((row["identity"], row["record_version"], row["package_digest"]) for row in records)
    if len({row[0] for row in rows}) != len(rows):
        raise ValueError("a review frame repeats an identity")
    if any(not all(isinstance(value, str) and value for value in row) for row in rows):
        raise ValueError("a review frame needs identity, store version and package digest")
    return hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode()).hexdigest()

ZERO_ACCEPTANCE = "zero_acceptance_no_history"
OBSERVED_RATE = "acceptance_number_from_observed_rate"
EVERY_COMPONENT = "every_component_reviewed"
GENERATOR_ABOVE_TOLERANCE = "generator_rate_at_or_above_tolerance"

ACCEPTED = "accepted"
WITHHELD = "withheld"
#: The reasons a batch is withheld; each names the rule that applied.
TOO_MANY_DEFECTS = "sample_defects_above_acceptance_number"
CONTROL_APPROVED = "reviewer_approved_a_known_wrong_control"
SAMPLE_INCOMPLETE = "sample_not_fully_decided"
NO_CONTROL = "no_known_wrong_control_in_the_run"
GENERATOR_FLAGGED = "generator_rate_at_or_above_tolerance"

#: Operating characteristic points written with every plan, so a reader sees the plan's behavior.
OC_RATES = (0.0, 0.005, 0.01, 0.02, 0.03, 0.05, 0.08, 0.10, 0.20)


class SamplingError(ValueError):
    """A policy, a history or a sample outside its declared bounds."""


@dataclass(frozen=True)
class SamplingPolicy:
    """The written acceptance rule's numbers. The defaults are the admission defaults of this route."""

    tolerance_defect_rate: float = 0.05
    consumer_risk: float = 0.05
    producer_risk: float = 0.10
    #: Sampled components a generator needs before its observed defect rate chooses the plan.
    minimum_history: int = 50
    maximum_acceptance_number: int = 40

    def __post_init__(self):
        for name in ("tolerance_defect_rate", "consumer_risk", "producer_risk"):
            value = getattr(self, name)
            if type(value) is not float or not 0.0 < value < 0.5:
                raise SamplingError(f"{name} is a rate above 0 and below 0.5")
        for name in ("minimum_history", "maximum_acceptance_number"):
            value = getattr(self, name)
            if type(value) is not int or not 0 <= value <= 100_000:
                raise SamplingError(f"{name} is a whole number from 0 to 100000")

    def to_dict(self) -> dict:
        return {"record_type": POLICY_RECORD, **asdict(self)}

    @property
    def sha256(self) -> str:
        return hashlib.sha256(json.dumps(self.to_dict(), sort_keys=True).encode()).hexdigest()


@dataclass(frozen=True)
class GeneratorHistory:
    """What earlier sampled batches of one generator found: components sampled and defective among them."""

    generator: str
    batches: int = 0
    sampled: int = 0
    defective: int = 0

    def __post_init__(self):
        if type(self.generator) is not str or not self.generator:
            raise SamplingError("a history names its generator")
        for name in ("batches", "sampled", "defective"):
            if type(getattr(self, name)) is not int or getattr(self, name) < 0:
                raise SamplingError(f"{name} is a whole number of zero or more")
        if self.defective > self.sampled:
            raise SamplingError("a history cannot hold more defective components than it sampled")

    def observed_rate(self, policy: SamplingPolicy) -> "float | None":
        """The process average, or None while the history is shorter than the policy's minimum."""
        if self.sampled < max(1, policy.minimum_history):
            return None
        return self.defective / self.sampled

    @classmethod
    def from_decisions(cls, generator: str, decisions) -> "GeneratorHistory":
        """Sum the decided batches of one generator; batches whose sample was not fully decided count nothing."""
        batches = sampled = defective = 0
        for row in decisions:
            if row.get("generator") != generator or row.get("sample_complete") is not True:
                continue
            batches += 1
            sampled += int(row["sampled"])
            defective += int(row["defective"])
        return cls(generator, batches, sampled, defective)


def _log_comb(n: int, k: int) -> float:
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)


def hypergeometric_cdf(c: int, population: int, defective: int, sample: int) -> float:
    """P(X <= c) for the defective count X in a sample drawn without replacement."""
    if not 0 <= defective <= population or not 0 <= sample <= population:
        raise SamplingError("a hypergeometric draw stays within its population")
    low, high = max(0, sample - (population - defective)), min(defective, sample)
    if c < low:
        return 0.0
    if c >= high:
        return 1.0
    denominator = _log_comb(population, sample)
    total = 0.0
    for x in range(low, c + 1):
        total += math.exp(_log_comb(defective, x) + _log_comb(population - defective, sample - x) - denominator)
    return min(1.0, total)


def binomial_cdf(c: int, n: int, p: float) -> float:
    """P(X <= c) for X binomial with n trials at rate p."""
    if c < 0:
        return 0.0
    if c >= n or p <= 0.0:
        return 1.0
    if p >= 1.0:
        return 0.0
    total, log_p, log_q = 0.0, math.log(p), math.log1p(-p)
    for x in range(0, c + 1):
        total += math.exp(_log_comb(n, x) + x * log_p + (n - x) * log_q)
    return min(1.0, total)


def smallest_sample(c: int, population: int, defective: int, consumer_risk: float) -> int:
    """The smallest n with P(X <= c) <= consumer_risk, or the whole population when none is smaller."""
    low, high = c + 1, population
    if high < low or hypergeometric_cdf(c, population, defective, high) > consumer_risk:
        return population
    while low < high:
        middle = (low + high) // 2
        if hypergeometric_cdf(c, population, defective, middle) <= consumer_risk:
            high = middle
        else:
            low = middle + 1
    return low


def clopper_pearson_upper(defective: int, sampled: int, confidence: float = 0.95) -> float:
    """The one-sided upper confidence bound of a defect rate from a sample (exact binomial, by bisection)."""
    if sampled <= 0:
        return 1.0
    if defective >= sampled:
        return 1.0
    target, low, high = 1.0 - confidence, defective / sampled, 1.0
    for _ in range(80):
        middle = (low + high) / 2
        if binomial_cdf(defective, sampled, middle) > target:
            low = middle
        else:
            high = middle
    return high


@dataclass(frozen=True)
class SamplingPlan:
    batch: str
    generator: str
    batch_size: int
    sample_size: int
    acceptance_number: int
    mode: str
    tolerance_defectives: int
    observed_rate: "float | None"
    consumer_risk_achieved: float
    producer_risk_at_observed_rate: "float | None"
    policy: SamplingPolicy
    history: GeneratorHistory

    @property
    def reviews_every_component(self) -> bool:
        return self.sample_size >= self.batch_size

    def acceptance_probability(self, rate: float) -> float:
        """The operating characteristic at a process defect rate (binomial, the generator's view)."""
        if self.mode == GENERATOR_ABOVE_TOLERANCE:
            return 0.0
        return binomial_cdf(self.acceptance_number, self.sample_size, rate)

    def to_dict(self) -> dict:
        return {"record_type": PLAN_RECORD, "batch": self.batch, "generator": self.generator,
                "batch_size": self.batch_size, "sample_size": self.sample_size,
                "acceptance_number": self.acceptance_number, "mode": self.mode,
                "tolerance_defectives": self.tolerance_defectives, "observed_rate": self.observed_rate,
                "consumer_risk_achieved": round(self.consumer_risk_achieved, 6),
                "producer_risk_at_observed_rate": (None if self.producer_risk_at_observed_rate is None
                                                   else round(self.producer_risk_at_observed_rate, 6)),
                "operating_characteristic": {f"{rate:.3f}": round(self.acceptance_probability(rate), 6)
                                             for rate in OC_RATES},
                "policy": self.policy.to_dict(), "policy_sha256": self.policy.sha256,
                "history": asdict(self.history),
                "rule": ("Accept the batch when the reviewer approved no planted known-wrong control in this run "
                         f"and at most {self.acceptance_number} of the {self.sample_size} sampled components are "
                         "defective (rejected under the written criteria, or left without a valid verdict); "
                         "otherwise withhold the whole batch and flag the generator. A rejected sampled component "
                         "is never published.")}


def plan_for(batch: str, batch_size: int, history: GeneratorHistory,
             policy: SamplingPolicy = SamplingPolicy()) -> SamplingPlan:
    """The sample size and acceptance number for one batch, from its size and the generator's observed rate."""
    if type(batch_size) is not int or batch_size < 1:
        raise SamplingError("a batch holds at least one component")
    tolerance = max(1, math.ceil(policy.tolerance_defect_rate * batch_size))
    observed = history.observed_rate(policy)

    def build(n, c, mode, producer):
        achieved = hypergeometric_cdf(c, batch_size, tolerance, n) if n < batch_size else 0.0
        return SamplingPlan(batch, history.generator, batch_size, n, c, mode, tolerance, observed, achieved,
                            producer, policy, history)

    if observed is not None and observed >= policy.tolerance_defect_rate:
        return build(batch_size, 0, GENERATOR_ABOVE_TOLERANCE, 1.0)
    if observed is None:
        n = smallest_sample(0, batch_size, tolerance, policy.consumer_risk)
        return build(n, 0, EVERY_COMPONENT if n >= batch_size else ZERO_ACCEPTANCE, None)
    for c in range(0, policy.maximum_acceptance_number + 1):
        n = smallest_sample(c, batch_size, tolerance, policy.consumer_risk)
        if n >= batch_size:
            return build(batch_size, c, EVERY_COMPONENT, 1.0 - binomial_cdf(c, batch_size, observed))
        producer = 1.0 - binomial_cdf(c, n, observed)
        if producer <= policy.producer_risk:
            return build(n, c, OBSERVED_RATE, producer)
    return build(batch_size, policy.maximum_acceptance_number, EVERY_COMPONENT, None)


def draw_sample(identities, sample_size: int, seed: str) -> list:
    """A simple random sample, reproducible from the recorded seed, in the population's sorted order."""
    population = sorted(set(identities))
    if not 0 <= sample_size <= len(population):
        raise SamplingError("a sample stays within its population")
    if type(seed) is not str or len(seed) < 16:
        raise SamplingError("a sample seed is recorded text of at least 16 characters")
    chosen = set(random.Random(seed).sample(population, sample_size))
    return [identity for identity in population if identity in chosen]


def decide(plan: SamplingPlan, *, defective: int, decided: int, controls_planted: int,
           controls_approved: int) -> dict:
    """The written rule applied to one reviewed sample."""
    if not 0 <= defective <= decided <= plan.sample_size:
        raise SamplingError("defective and decided counts stay within the sample")
    if not 0 <= controls_approved <= controls_planted:
        raise SamplingError("approved controls stay within the planted ones")
    undecided = plan.sample_size - decided
    # A sampled component without a valid verdict counts as defective: the rule never assumes a good outcome.
    counted = defective + undecided
    reasons = []
    if plan.mode == GENERATOR_ABOVE_TOLERANCE:
        reasons.append(GENERATOR_FLAGGED)
    if controls_planted == 0 or controls_approved:
        reasons.append(CONTROL_APPROVED if controls_approved else NO_CONTROL)
    if counted > plan.acceptance_number:
        reasons.append(TOO_MANY_DEFECTS)
    if undecided:
        reasons.append(SAMPLE_INCOMPLETE)
    outcome = WITHHELD if reasons else ACCEPTED
    return {"record_type": DECISION_RECORD, "batch": plan.batch, "generator": plan.generator,
            "outcome": outcome, "reasons": reasons, "sampled": plan.sample_size, "decided": decided,
            "defective": defective, "counted_defective": counted, "acceptance_number": plan.acceptance_number,
            "sample_complete": undecided == 0, "controls_planted": controls_planted,
            "controls_approved": controls_approved,
            "defect_rate_upper_95": round(clopper_pearson_upper(counted, plan.sample_size), 6),
            "flag_generator": (TOO_MANY_DEFECTS in reasons) or (GENERATOR_FLAGGED in reasons)}
