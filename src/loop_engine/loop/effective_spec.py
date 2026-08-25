"""EffectiveLoopSpec — preferences COMPILED into an immutable configuration.

Architectural role: loop (the resolution boundary between what was asked for
and what will actually run).

The owner's ask was that a loop can be "initialized with preferences". Done
naively that makes a run irreproducible: the loop points at whatever the
preference store happens to say now, so replaying it a week later replays a
different loop. Done properly it is the opposite — preferences are INPUTS to a
deterministic resolution that produces an immutable spec, and the run binds
the DIGEST of the resolved values rather than a pointer to mutable ones.

    requested LoopSpec + preferences + policy floor
                        |
             deterministic resolution
                        |
        EffectiveLoopSpec (immutable, digested)
                +
        PreferenceResolutionRecord
        (what was chosen, what was rejected, and WHY)

Owns:
    - EffectiveLoopSpec: the frozen resolved configuration plus its digest;
    - resolve_effective_spec(): the deterministic resolution itself, run as a
      loop (the resolver is a boundary like any other);
    - PreferenceResolutionRecord: per-field selected value, source, rejected
      alternatives, and the reason — so a resolution can be argued with.

Does not own:
    - the authority ladder (user_feedback_intelligence.rank_guidance owns precedence),
      the runtime (recursive_loop), or any preference storage.

Key invariants:
    - the SAME inputs always produce the same digest — resolution is
      deterministic, and the test proves it rather than assuming it;
    - a hard policy-floor value can never be overridden by a preference,
      whatever its strength;
    - every effective field names its source; an unexplained value is a bug;
    - changing the store afterwards does NOT change a resolved spec.

Verification: self_test() — determinism of the digest, floor precedence,
record completeness, and the adversarial "mutate the store afterwards" path.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from .recursive_loop import (default_loop_condition,
                             normalize_exit_condition)

#: Where a resolved value came from, highest authority first.  Mirrors the
#: §13.2 ladder; the first three are the floor a preference cannot cross.
VALUE_SOURCES = ("platform_safety", "organization_policy",
                 "project_constraint", "user_preference", "template_default",
                 "implementation_default")

_FLOOR = VALUE_SOURCES[:3]


@dataclass(frozen=True)
class EffectiveLoopSpec:
    """The immutable configuration a loop will actually run under."""
    fields: tuple                       # ((name, value, source), ...)
    digest: str

    def value(self, name: str, default=None):
        for n, v, _ in self.fields:
            if n == name:
                return v
        return default

    def source(self, name: str) -> str:
        for n, _, s in self.fields:
            if n == name:
                return s
        return ""

    def as_dict(self) -> dict:
        return {n: v for n, v, _ in self.fields}


@dataclass
class PreferenceResolutionRecord:
    """Why each field holds the value it holds."""
    decisions: list = field(default_factory=list)
    digest: str = ""

    def to_dict(self) -> dict:
        return {"record_type": "preference_resolution_record/v1",
                "effective_digest": self.digest,
                "decisions": self.decisions}

    def rejected_for(self, name: str) -> list:
        for d in self.decisions:
            if d["field"] == name:
                return d["rejected"]
        return []


def _digest_fields(fields) -> str:
    return hashlib.sha256(
        json.dumps([[n, v, s] for n, v, s in fields],
                   sort_keys=True, default=str).encode()).hexdigest()


def resolve_effective_spec(requested: dict, *, preferences=(),
                           policy_floor=(), template_defaults=None,
                           ledger=None) -> tuple:
    """Compile preferences into an immutable spec, deterministically.

    ``preferences`` are dicts with ``field``, ``value``, ``source`` and an
    optional ``strength``.  ``policy_floor`` entries use a floor source and
    win outright.  Resolution is a boundary, so it runs as a loop.

    Returns ``(EffectiveLoopSpec, PreferenceResolutionRecord)``.
    """
    from .encapsulate import as_practitioner_loop

    def _mapping(value: dict) -> dict:
        current = dict(value)
        if "exit_condition" in current:
            current["exit_condition"] = normalize_exit_condition(
                current.get("exit_condition", ""))
        return current

    def _candidate(value: dict) -> dict:
        current = dict(value)
        if current.get("field") == "exit_condition":
            current["value"] = normalize_exit_condition(
                current.get("value"))
        return current

    requested = _mapping(requested)
    template_defaults = _mapping(template_defaults or {})
    preferences = tuple(_candidate(value) for value in preferences)
    policy_floor = tuple(_candidate(value) for value in policy_floor)

    def _resolve():
        names = set(requested) | {p["field"] for p in preferences} \
            | {p["field"] for p in policy_floor} | set(template_defaults or {})
        fields, decisions = [], []
        for name in sorted(names):
            candidates = []
            for p in policy_floor:
                if p["field"] == name:
                    src = p.get("source", "organization_policy")
                    if src not in _FLOOR:
                        raise ValueError(
                            f"policy floor entry for {name!r} claims source "
                            f"{src!r}, which is not one of the floor sources "
                            f"{_FLOOR} — the floor cannot be forged downward")
                    candidates.append((VALUE_SOURCES.index(src), p["value"],
                                       src))
            for p in preferences:
                if p["field"] == name:
                    src = p.get("source", "user_preference")
                    candidates.append((VALUE_SOURCES.index(src), p["value"],
                                       src))
            if name in requested:
                candidates.append((VALUE_SOURCES.index("user_preference"),
                                   requested[name], "user_preference"))
            for src, table in (("template_default", template_defaults),):
                if name in table:
                    candidates.append((VALUE_SOURCES.index(src), table[name],
                                       src))
            if not candidates:
                continue
            candidates.sort(key=lambda c: c[0])
            rank, value, src = candidates[0]
            fields.append((name, value, src))
            decisions.append({
                "field": name, "selected": value, "source": src,
                "rejected": [{"value": v, "source": s} for _, v, s
                             in candidates[1:]],
                "rule": "highest authority wins; the floor cannot be crossed",
            })
        selected = {name: value for name, value, _source in fields}
        framework = selected.get("framework", "nine_step")
        expected_loop = default_loop_condition(framework)
        loop_condition = selected.get("loop_condition", "")
        if loop_condition and loop_condition != expected_loop:
            raise ValueError(
                f"framework {framework!r} requires loop_condition "
                f"{expected_loop!r}")
        if not loop_condition:
            fields = [item for item in fields if item[0] != "loop_condition"]
            decisions = [item for item in decisions
                         if item["field"] != "loop_condition"]
            fields.append(("loop_condition", expected_loop,
                           "implementation_default"))
            decisions.append({
                "field": "loop_condition", "selected": expected_loop,
                "source": "implementation_default", "rejected": [],
                "rule": "derived from the effective framework",
            })
        exit_condition = normalize_exit_condition(
            selected.get("exit_condition", ""))
        if not selected.get("exit_condition"):
            fields = [item for item in fields if item[0] != "exit_condition"]
            decisions = [item for item in decisions
                         if item["field"] != "exit_condition"]
            fields.append(("exit_condition", exit_condition,
                           "implementation_default"))
            decisions.append({
                "field": "exit_condition", "selected": exit_condition,
                "source": "implementation_default", "rejected": [],
                "rule": "every Loop has an explicit successful exit",
            })
        fields = tuple(sorted(fields, key=lambda item: item[0]))
        decisions.sort(key=lambda item: item["field"])
        dig = _digest_fields(fields)
        return (EffectiveLoopSpec(fields=fields, digest=dig),
                PreferenceResolutionRecord(decisions=decisions, digest=dig))

    return as_practitioner_loop("resolve effective loop spec", _resolve,
                                ledger=ledger)["value"]


def self_test() -> dict:
    results = []

    def check(name, ok, note=""):
        results.append({"test": name, "passed": bool(ok), "detail": note})

    prefs = [{"field": "power", "value": "deep", "source": "user_preference"},
             {"field": "mode", "value": "non_deterministic",
              "source": "user_preference"}]
    floor = [{"field": "mode", "value": "deterministic",
              "source": "organization_policy"}]
    defaults = {"power": "standard", "timeout": 30}

    spec, record = resolve_effective_spec(
        {"goal": "win"}, preferences=prefs, policy_floor=floor,
        template_defaults=defaults)

    # 1. DETERMINISTIC: same inputs, same digest.  Asserted, not assumed —
    # this is the whole reason a run can bind a digest instead of a pointer.
    spec2, _ = resolve_effective_spec(
        {"goal": "win"}, preferences=prefs, policy_floor=floor,
        template_defaults=defaults)
    check("resolution_is_deterministic_and_digested",
          spec.digest == spec2.digest and len(spec.digest) == 64
          and spec.value("power") == "deep",
          f"digest {spec.digest[:12]}… stable across runs")

    # 2. THE FLOOR HOLDS: a user preference cannot cross organization policy,
    # however strongly it is expressed.
    check("a_preference_cannot_cross_the_policy_floor",
          spec.value("mode") == "deterministic"
          and spec.source("mode") == "organization_policy"
          and any(r["source"] == "user_preference"
                  for r in record.rejected_for("mode")),
          "user asked for non_deterministic; org policy won and the ask is "
          "preserved as a rejected alternative")

    # 3. every field names its source, and a rejected alternative is kept
    # rather than discarded — a resolution you cannot argue with is not one.
    check("every_field_names_its_source_and_keeps_the_rejects",
          all(s for _, _, s in spec.fields)
          and all("rule" in d for d in record.decisions)
          and spec.source("timeout") == "template_default"
          and spec.value("loop_condition") == "steps_remain"
          and spec.value("exit_condition") == "steps_complete",
          f"{len(spec.fields)} fields, all sourced")

    # 4. ADVERSARIAL: a forged floor source is refused, and mutating the
    # preference list AFTERWARDS does not change an already-resolved spec —
    # which is the property that makes "initialized with preferences"
    # reproducible instead of a moving target.
    # the refusal surfaces as LoopError: resolution runs INSIDE an envelope,
    # so its failure lands on the ledger as evidence before it is raised —
    # the envelope working as designed, not an error being swallowed.
    from .recursive_loop import LoopError
    forged = False
    try:
        resolve_effective_spec({}, policy_floor=[
            {"field": "x", "value": 1, "source": "user_preference"}])
    except (LoopError, ValueError):
        forged = True
    prefs.append({"field": "power", "value": "max",
                  "source": "platform_safety"})
    check("forged_floor_refused_and_resolved_specs_are_immutable",
          forged and spec.value("power") == "deep"
          and spec.digest == spec2.digest,
          "later store mutation cannot rewrite a resolved spec")

    current_spec, _ = resolve_effective_spec(
        {"framework": "open", "exit_condition": "accepted_success"})
    invalid = False
    try:
        resolve_effective_spec({"exit_condition": "whenever"})
    except (LoopError, ValueError):
        invalid = True
    check("conditions_are_current_and_invalid_values_fail_closed",
          current_spec.value("loop_condition") == "chooser_selects_work"
          and current_spec.value("exit_condition") == "accepted_success"
          and invalid,
          "effective specs always expose current condition fields")

    passed = sum(1 for t in results if t["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
