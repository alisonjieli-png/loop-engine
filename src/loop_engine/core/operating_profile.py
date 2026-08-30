"""Operating profile — five enum modes, resolved Platform -> ... -> spawned.

Owner spec (2026-08-23): reduce the operating configuration to five clear,
bucketed, high-level controls (not a wall of knobs), each an ENUM with an
authority ordering, plus a small limits block.  Profiles resolve through a chain
— Platform -> Organization -> Project -> Run -> Spawned practitioner — where a
spawned may receive LESS authority than its parent but NEVER more.

The five modes:

  * access_mode                 — how far out the practitioner may reach
  * reasoning_and_model_mode    — what kinds of reasoning/model calls are allowed
  * construction_and_execution_mode — what it may build/run
  * effort_mode                 — how hard to work (a preference, not authority)
  * optimization_mode           — what to optimise for (a preference)

This is the owner-facing surface; ``to_solver_config()`` derives the already-
enforced ``SolverConfig`` (internet/models/authoring/budgets/optimize_for) from
it, so the guards in the kernel implementations bite exactly as before.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict

# Each authority mode, ORDERED from least to most authority (index = authority).
ACCESS_MODES = ("offline", "internal_only", "approved_external_read",
                "broad_external_read", "approved_external_write")
REASONING_MODES = ("deterministic_only", "local_only",
                   "deterministic_first_local_first", "approved_remote",
                   "best_available")
CONSTRUCTION_MODES = ("inspect_only", "reuse_only", "compose_configure",
                      "sandbox_generate", "promotion_authorized")
# Preferences have no authority ordering. A spawned Loop may pick any.
EFFORT_MODES = ("minimal", "standard", "deep", "exhaustive")
OPTIMIZATION_MODES = ("balanced", "quality_first", "reliability_first",
                      "cost_first", "latency_first", "exploration_first")

_AUTHORITY = {"access_mode": ACCESS_MODES,
              "reasoning_and_model_mode": REASONING_MODES,
              "construction_and_execution_mode": CONSTRUCTION_MODES}


@dataclass
class Limits:
    """Resource ceilings.  None = unset (inherits / uncapped)."""
    wall_time_seconds: "float | None" = None
    model_cost: "float | None" = None
    maximum_parallel_practitioners: "int | None" = None
    maximum_recursion_depth: "int | None" = None
    memory_gib: "float | None" = None


@dataclass
class OperatingProfile:
    access_mode: str = "approved_external_read"
    reasoning_and_model_mode: str = "best_available"
    construction_and_execution_mode: str = "sandbox_generate"
    effort_mode: str = "standard"
    optimization_mode: str = "quality_first"
    limits: Limits = field(default_factory=Limits)

    def __post_init__(self):
        for fld, valid in (("access_mode", ACCESS_MODES),
                           ("reasoning_and_model_mode", REASONING_MODES),
                           ("construction_and_execution_mode",
                            CONSTRUCTION_MODES),
                           ("effort_mode", EFFORT_MODES),
                           ("optimization_mode", OPTIMIZATION_MODES)):
            if getattr(self, fld) not in valid:
                raise ValueError(f"{fld} must be one of {valid}")

    def authority_at_most(self, other: "OperatingProfile") -> bool:
        """True if THIS profile never exceeds ``other``'s authority (all three
        authority modes ordinally <=, and no limit larger)."""
        for fld, order in _AUTHORITY.items():
            if order.index(getattr(self, fld)) > order.index(getattr(other,
                                                                     fld)):
                return False
        for lf in ("wall_time_seconds", "model_cost",
                   "maximum_parallel_practitioners", "maximum_recursion_depth",
                   "memory_gib"):
            mine = getattr(self.limits, lf)
            theirs = getattr(other.limits, lf)
            if mine is not None and theirs is not None and mine > theirs:
                return False
        return True

    def summary(self) -> dict:
        d = asdict(self)
        d["record_type"] = "operating_profile/v1"
        return d


def resolve_chain(*profiles: OperatingProfile) -> OperatingProfile:
    """Resolve a precedence chain (Platform -> Org -> Project -> Run -> Spawned).

    Each later profile may REQUEST settings, but is clamped to never exceed the
    authority granted so far: authority modes take the MINIMUM ordinal seen, and
    limits take the minimum value. A spawned Loop can only narrow. Preferences
    (effort/optimization) take the LAST profile's choice (the most specific)."""
    if not profiles:
        return OperatingProfile()
    acc = profiles[0]
    for nxt in profiles[1:]:
        new = OperatingProfile(
            access_mode=_min_mode("access_mode", acc, nxt),
            reasoning_and_model_mode=_min_mode("reasoning_and_model_mode",
                                               acc, nxt),
            construction_and_execution_mode=_min_mode(
                "construction_and_execution_mode", acc, nxt),
            effort_mode=nxt.effort_mode,          # preference: most specific wins
            optimization_mode=nxt.optimization_mode,
            limits=_min_limits(acc.limits, nxt.limits))
        acc = new
    return acc


def _min_mode(fld: str, a: OperatingProfile, b: OperatingProfile) -> str:
    order = _AUTHORITY[fld]
    return order[min(order.index(getattr(a, fld)),
                     order.index(getattr(b, fld)))]


def _min_limits(a: Limits, b: Limits) -> Limits:
    def m(x, y):
        if x is None:
            return y
        if y is None:
            return x
        return min(x, y)
    return Limits(m(a.wall_time_seconds, b.wall_time_seconds),
                  m(a.model_cost, b.model_cost),
                  m(a.maximum_parallel_practitioners,
                    b.maximum_parallel_practitioners),
                  m(a.maximum_recursion_depth, b.maximum_recursion_depth),
                  m(a.memory_gib, b.memory_gib))


def to_solver_config(profile: OperatingProfile):
    """Derive the enforced SolverConfig from the owner-facing profile, so the
    kernel guards bite unchanged."""
    from ..core.config import SolverConfig, Budgets
    internet = profile.access_mode in ("approved_external_read",
                                       "broad_external_read",
                                       "approved_external_write")
    # deterministic_only forbids model calls; everything else uses the roster.
    models = () if profile.reasoning_and_model_mode == "deterministic_only" \
        else None
    authoring = profile.construction_and_execution_mode in (
        "sandbox_generate", "promotion_authorized")
    optimize = {"quality_first": "accuracy", "latency_first": "runtime",
                "cost_first": "cost", "reliability_first": "reliability",
                "balanced": "accuracy", "exploration_first": "accuracy"}[
        profile.optimization_mode]
    return SolverConfig(
        internet_access=internet, allowed_models=models,
        code_authoring=authoring,
        budgets=Budgets(max_seconds=profile.limits.wall_time_seconds),
        optimize_for=optimize)


# ---------------------------------------------------------------------------
# Self-test — deterministic, no network.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    # 1. exactly five modes, each a closed enum; defaults are the owner example.
    p = OperatingProfile()
    check("five_enum_modes_with_closed_vocabularies",
          len(_AUTHORITY) == 3
          and p.access_mode == "approved_external_read"
          and p.optimization_mode == "quality_first",
          "access/reasoning/construction are authority modes; effort/"
          "optimization are preferences")
    bad = 0
    for kw in ({"access_mode": "x"}, {"effort_mode": "y"},
               {"optimization_mode": "z"}):
        try:
            OperatingProfile(**kw)
        except ValueError:
            bad += 1
    check("unknown_mode_values_are_refused", bad == 3, "closed vocabularies")

    # 2. Resolution clamps a spawned Loop to the spawning authority.
    platform = OperatingProfile(access_mode="broad_external_read",
                                construction_and_execution_mode="sandbox_generate")
    spawned_req = OperatingProfile(access_mode="approved_external_write",
                                 construction_and_execution_mode="promotion_authorized")
    resolved = resolve_chain(platform, spawned_req)
    check("a_spawned_cannot_exceed_parent_authority",
          resolved.access_mode == "broad_external_read"
          and resolved.construction_and_execution_mode == "sandbox_generate"
          and resolved.authority_at_most(platform),
          "the spawned asked for MORE access/construction and was clamped down")

    # 3. A spawned Loop can narrow authority.
    narrowing = OperatingProfile(access_mode="offline",
                                 reasoning_and_model_mode="deterministic_only")
    r2 = resolve_chain(platform, narrowing)
    check("a_spawned_can_narrow_authority",
          r2.access_mode == "offline"
          and r2.reasoning_and_model_mode == "deterministic_only",
          "narrowing is always allowed; broadening never is")

    # 4. limits take the minimum along the chain.
    a = OperatingProfile(limits=Limits(wall_time_seconds=3600, model_cost=5.0))
    b = OperatingProfile(limits=Limits(wall_time_seconds=600, model_cost=20.0))
    r3 = resolve_chain(a, b)
    check("limits_resolve_to_the_minimum_along_the_chain",
          r3.limits.wall_time_seconds == 600 and r3.limits.model_cost == 5.0,
          "a run inherits the tightest ceiling seen, never a looser one")

    # 5. preferences take the most-specific (last) profile.
    pa = OperatingProfile(optimization_mode="balanced", effort_mode="minimal")
    pb = OperatingProfile(optimization_mode="cost_first", effort_mode="deep")
    r4 = resolve_chain(pa, pb)
    check("preferences_take_the_most_specific_profile",
          r4.optimization_mode == "cost_first" and r4.effort_mode == "deep",
          "effort/optimization are preferences — the spawned's choice wins")

    # 6. to_solver_config derives the ENFORCED config faithfully.
    off = to_solver_config(OperatingProfile(
        access_mode="offline", reasoning_and_model_mode="deterministic_only",
        construction_and_execution_mode="reuse_only",
        optimization_mode="latency_first"))
    check("offline_deterministic_reuse_derives_a_locked_down_config",
          off.internet_access is False and off.allowed_models == ()
          and off.code_authoring is False and off.optimize_for == "runtime",
          "the five modes derive the already-enforced SolverConfig")

    full = to_solver_config(OperatingProfile())
    check("the_default_profile_derives_a_capable_config",
          full.internet_access is True and full.allowed_models is None
          and full.code_authoring is True and full.optimize_for == "accuracy",
          "the owner-default profile is full-power, matching the config default")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "operating_profile_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
