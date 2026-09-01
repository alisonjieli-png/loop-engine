"""Run-local route health learning for the adaptive Practitioner.

A proxy timeout, an output-ceiling rejection, or a string of transport
failures teach the run something about one route. This module records those
observations as typed run-local facts and derives advisory adjustments:
a safer output ceiling for routes whose long generations hit proxy walls,
and a failover preference for routes that keep failing.

Scope and rules:

- Run-local only (Runtime Memory): nothing here is persisted, promoted, or
  becomes configuration. A new run starts from the declared settings again.
- Advisory only: the learner proposes ceilings and route preferences; the
  governed model-step boundary applies them inside its existing authority,
  and every adjustment is published as a typed progress event and recorded
  in the run evidence.
- Fail closed: an unknown or missing observation never fabricates a limit.
  A learned ceiling is derived only from an observed completed generation
  or a repeated timeout wall, and it is always smaller than what failed.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

ROUTE_HEALTH_SCHEMA_VERSION = "route_health/v1"

# Fraction of the last failed ceiling to try next on a gateway timeout.
# Deliberately conservative: one halving must land under the proxy wall.
_GATEWAY_TIMEOUT_CEILING_FACTOR = 0.5
# A timeout wall must be observed at least twice before a route is
# considered persistently blocked at its ceiling for this run.
_REPEATED_WALL_OBSERVATIONS = 2


class RouteHealthError(ValueError):
    """A route health observation or adjustment is invalid."""


@dataclass(frozen=True)
class GenerationOutcome:
    """One observed model-step outcome on one route."""

    route_name: str
    provider: str
    model: str
    error_code: str = ""
    output_tokens: "int | None" = None
    elapsed_seconds: "float | None" = None
    requested_output_ceiling: "int | None" = None

    def __post_init__(self) -> None:
        if not self.route_name.strip() or not self.provider.strip():
            raise RouteHealthError(
                "a generation outcome needs a route and a provider")
        if not self.model.strip():
            raise RouteHealthError("a generation outcome needs a model")


@dataclass
class RouteHealthEntry:
    """Learned facts for one route within one run."""

    route_name: str
    provider: str
    model: str
    completed_generations: int = 0
    completed_output_tokens: list[int] = field(default_factory=list)
    gateway_timeout_walls: int = 0
    last_failed_ceiling: "int | None" = None
    last_completed_ceiling: "int | None" = None
    transport_failures: int = 0
    learned_ceiling: "int | None" = None
    learned_ceiling_reason: str = ""
    adjustment_count: int = 0

    def record(self, outcome: GenerationOutcome) -> None:
        """Fold one outcome into this route's learned facts."""
        if outcome.route_name != self.route_name:
            raise RouteHealthError(
                "outcome route does not match this health entry")
        if outcome.error_code == "gateway_timeout":
            self.gateway_timeout_walls += 1
            if (outcome.requested_output_ceiling is not None
                    and (self.last_failed_ceiling is None
                         or outcome.requested_output_ceiling
                         < self.last_failed_ceiling)):
                self.last_failed_ceiling = outcome.requested_output_ceiling
            return
        if outcome.error_code in ("provider_unavailable", "timeout",
                                  "network_unreachable"):
            self.transport_failures += 1
            return
        if not outcome.error_code:
            self.completed_generations += 1
            if outcome.output_tokens is not None:
                self.completed_output_tokens.append(outcome.output_tokens)
            if (outcome.requested_output_ceiling is not None
                    and outcome.output_tokens is not None
                    and outcome.output_tokens
                    < outcome.requested_output_ceiling):
                # The model finished under the ceiling: the ceiling is
                # proven reachable on this route.
                self.last_completed_ceiling = outcome.requested_output_ceiling

    def advise_ceiling(self, requested: "int | None") -> "int | None":
        """Return a learned working ceiling for the next call, or None.

        Only derived from observed evidence: after a gateway timeout wall
        the next request tries half the failed ceiling; after a repeated
        wall the route is considered blocked at that scale for the rest of
        the run and keeps halving. A route with completed generations at the
        requested ceiling is left untouched.
        """
        if self.gateway_timeout_walls == 0:
            return None
        if requested is not None and self.last_completed_ceiling is not None \
                and requested <= self.last_completed_ceiling:
            return None
        base = self.last_failed_ceiling
        if base is None:
            return None
        walls = max(1, self.gateway_timeout_walls
                    if self.gateway_timeout_walls < _REPEATED_WALL_OBSERVATIONS
                    else _REPEATED_WALL_OBSERVATIONS)
        learned = max(1024, int(base * (_GATEWAY_TIMEOUT_CEILING_FACTOR
                                        ** walls)))
        if requested is not None and requested <= learned:
            return None
        self.learned_ceiling = learned
        self.learned_ceiling_reason = (
            f"gateway timeout wall observed {self.gateway_timeout_walls}x "
            f"at ceiling {base}; halving to a working ceiling")
        self.adjustment_count += 1
        return learned

    def advise_route_preference(self) -> dict:
        """Advisory failover preference derived from observed health."""
        blocked = (self.gateway_timeout_walls >= _REPEATED_WALL_OBSERVATIONS)
        flaky = self.transport_failures >= 3
        return {
            "record_type": "route_health_preference/v1",
            "route_name": self.route_name,
            "provider": self.provider,
            "model": self.model,
            "prefer_failover": bool(blocked or flaky),
            "reason": (
                "repeated gateway timeout walls at the requested ceiling"
                if blocked else
                "repeated transport failures" if flaky else
                "route healthy within observed evidence"),
            "completed_generations": self.completed_generations,
            "gateway_timeout_walls": self.gateway_timeout_walls,
            "transport_failures": self.transport_failures,
            "prior_not_proof": True,
        }

    def to_dict(self) -> dict:
        return {
            "schema_version": ROUTE_HEALTH_SCHEMA_VERSION,
            "route_name": self.route_name,
            "provider": self.provider,
            "model": self.model,
            "completed_generations": self.completed_generations,
            "gateway_timeout_walls": self.gateway_timeout_walls,
            "transport_failures": self.transport_failures,
            "last_failed_ceiling": self.last_failed_ceiling,
            "last_completed_ceiling": self.last_completed_ceiling,
            "learned_ceiling": self.learned_ceiling,
            "learned_ceiling_reason": self.learned_ceiling_reason,
            "adjustment_count": self.adjustment_count,
        }


class RouteHealthLedger:
    """Run-local ledger of observed route outcomes and learned adjustments."""

    def __init__(self) -> None:
        self._entries: dict[str, RouteHealthEntry] = {}

    def record_outcome(self, outcome: GenerationOutcome) -> None:
        key = f"{outcome.route_name}|{outcome.model}"
        entry = self._entries.get(key)
        if entry is None:
            entry = RouteHealthEntry(
                route_name=outcome.route_name,
                provider=outcome.provider,
                model=outcome.model)
            self._entries[key] = entry
        entry.record(outcome)

    def advise_ceiling(
            self, route_name: str, model: str,
            requested: "int | None") -> "int | None":
        entry = self._entries.get(f"{route_name}|{model}")
        if entry is None:
            return None
        return entry.advise_ceiling(requested)

    def advise_route_preferences(self) -> list[dict]:
        return [entry.advise_route_preference()
                for entry in self._entries.values()]

    def to_dict(self) -> dict:
        return {
            "record_type": "route_health_ledger/v1",
            "schema_version": ROUTE_HEALTH_SCHEMA_VERSION,
            "entries": [entry.to_dict() for entry in self._entries.values()],
        }

    def digest(self) -> str:
        encoded = json.dumps(
            self.to_dict(), sort_keys=True, separators=(",", ":"),
            ensure_ascii=True).encode("utf-8")
        return "sha256:" + hashlib.sha256(encoded).hexdigest()


def self_test() -> dict:
    tests: list[dict] = []
    ledger = RouteHealthLedger()
    route = "custom.tacticalengineering"
    provider = "tacticalengineering"
    model = "gemma-4-coding-abliterated"

    def check(name: str, passed: bool, detail: str = "") -> None:
        tests.append({"test": name, "passed": bool(passed),
                      "detail": detail})

    # 1. a healthy generation at the requested ceiling learns nothing forced
    ledger.record_outcome(GenerationOutcome(
        route, provider, model, output_tokens=8192,
        requested_output_ceiling=16384))
    check("completed_generation_records_reachable_ceiling",
          ledger.advise_ceiling(route, model, 16384) is None)

    # 2. one gateway timeout at 32768 advises half
    ledger.record_outcome(GenerationOutcome(
        route, provider, model, error_code="gateway_timeout",
        requested_output_ceiling=32768))
    advised = ledger.advise_ceiling(route, model, 32768)
    check("one_timeout_wall_halves_the_ceiling",
          advised == 16384,
          f"advised {advised} after one wall at 32768")

    # 3. a repeated wall keeps halving and marks the route blocked
    ledger.record_outcome(GenerationOutcome(
        route, provider, model, error_code="gateway_timeout",
        requested_output_ceiling=32768))
    advised2 = ledger.advise_ceiling(route, model, 32768)
    preferences = ledger.advise_route_preferences()
    blocked = next((p for p in preferences
                    if p["route_name"] == route), {})
    check("repeated_wall_prefer_failover_and_lower_ceiling",
          advised2 is not None and advised2 < advised
          and blocked.get("prefer_failover") is True,
          f"second advice {advised2}; prefer_failover="
          f"{blocked.get('prefer_failover')}")

    # 4. transport failures accumulate into a flaky preference
    flaky_ledger = RouteHealthLedger()
    for _ in range(3):
        flaky_ledger.record_outcome(GenerationOutcome(
            "cloud.default", "ollama_cloud", "deepseek-v4-flash:0731",
            error_code="provider_unavailable"))
    flaky = flaky_ledger.advise_route_preferences()[0]
    check("repeated_transport_failures_prefer_failover",
          flaky["prefer_failover"] is True)

    # 5. a route with no observations advises nothing
    empty = RouteHealthLedger()
    check("no_observations_advise_nothing",
          empty.advise_ceiling("unknown.route", "m", 100) is None
          and empty.advise_route_preferences() == [])

    # 6. learned ceilings never exceed the failed ceiling
    ledger3 = RouteHealthLedger()
    ledger3.record_outcome(GenerationOutcome(
        route, provider, model, error_code="gateway_timeout",
        requested_output_ceiling=65536))
    small = ledger3.advise_ceiling(route, model, 65536)
    check("learned_ceiling_stays_below_the_failed_ceiling",
          small is not None and small < 65536 and small >= 1024)

    return {"record_type": "route_health_test/v1", "tests": tests,
            "passed": sum(t["passed"] for t in tests),
            "total": len(tests),
            "all_passed": all(t["passed"] for t in tests)}


__all__ = (
    "GenerationOutcome", "RouteHealthEntry", "RouteHealthError",
    "RouteHealthLedger", "ROUTE_HEALTH_SCHEMA_VERSION")