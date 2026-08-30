"""Global solver configuration — five core settings, clearly bucketed, ENFORCED.

Owner rule (2026-08-23): a small set of very clear, very high-level parameters —
not a wall of knobs.  The five core settings:

  1. **internet_access** — may the practitioner reach the internet at all
     (search, downloads, live research)?  Default ALLOWED — full power.
  2. **allowed_models** — which model families may be called?  ``None`` means
     the sanctioned roster; an explicit tuple restricts to those; ``()`` means
     NO model calls at all (the pure-deterministic profile).
  3. **code_authoring** — may it write/generate code (OpenCode workers,
     generated nodes)?  Off forces reuse/configure/compose only.
  4. **budgets** — ceilings for passes, tokens, seconds.  Defaults are
     UNCAPPED (a budget is an explicit owner choice, never a silent default —
     the no-arbitrary-limits rule).
  5. **optimize_for** — what the run should prioritise: accuracy, runtime,
     cost, or reliability.  It travels into every prompt's details so decisions
     actually weigh it.

Advanced settings exist but stay out of the way (deterministic_first,
reuse_sources).  Enforcement is structural: guard functions raise
``ConfigViolation`` with a plain-English reason, and the kernel implementations
consult them at the how/act/ask boundaries — a setting the code cannot violate,
not a comment.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Sequence

from ..core.ollama_client import FORBIDDEN_MODELS

OPTIMIZE_FOR = ("accuracy", "runtime", "cost", "reliability")

# Where reusable nodes may come from.
REUSE_SOURCES = ("internal", "github", "pypi")

# Plan handles/modes that require the internet.
_NEEDS_INTERNET = ("research", "web", "download", "scrape", "search_online")


class ConfigViolation(RuntimeError):
    """An action the active configuration forbids — refused with the reason."""


@dataclass
class Budgets:
    """Ceilings.  ``None`` = uncapped — a budget is an explicit choice."""
    max_passes: "int | None" = None
    max_tokens: "int | None" = None
    max_seconds: "float | None" = None


@dataclass
class SolverConfig:
    # --- the five core settings (defaults = FULL POWER; the config exists
    # to RESTRICT when the owner chooses, never to hobble by default) -------
    internet_access: bool = True
    allowed_models: "tuple | None" = None      # None=sanctioned; ()=no models
    code_authoring: bool = True
    budgets: Budgets = field(default_factory=Budgets)
    optimize_for: str = "accuracy"
    # --- advanced (defaulted, out of the way) -----------------------------
    deterministic_first: bool = False
    reuse_sources: tuple = ("internal", "github", "pypi")

    def __post_init__(self):
        if self.optimize_for not in OPTIMIZE_FOR:
            raise ValueError(f"optimize_for must be one of {OPTIMIZE_FOR}")
        for src in self.reuse_sources:
            if src not in REUSE_SOURCES:
                raise ValueError(f"unknown reuse source {src!r}; valid: "
                                 f"{REUSE_SOURCES}")
        if self.allowed_models is not None:
            bad = [m for m in self.allowed_models
                   if any(f in m for f in FORBIDDEN_MODELS)]
            if bad:
                raise ValueError(f"models {bad} are forbidden by policy and "
                                 f"cannot be allowed by configuration")

    def summary(self) -> dict:
        """The plain-English record of what this run may and may not do."""
        models = ("no model calls (pure deterministic)"
                  if self.allowed_models == ()
                  else "the sanctioned roster" if self.allowed_models is None
                  else ", ".join(self.allowed_models))
        return {
            "record_type": "solver_config/v1",
            "internet access": ("allowed" if self.internet_access
                                else "NOT allowed"),
            "models allowed": models,
            "code authoring": ("allowed" if self.code_authoring
                               else "NOT allowed — reuse only"),
            "budgets": {k: (v if v is not None else "uncapped")
                        for k, v in asdict(self.budgets).items()},
            "optimizing for": self.optimize_for,
            "deterministic first": self.deterministic_first,
            "reuse sources": list(self.reuse_sources),
        }


# ---------------------------------------------------------------------------
# Enforcement guards — consulted at the how/act/ask boundaries.
# ---------------------------------------------------------------------------


def screen_models(config: SolverConfig,
                  requested: "Sequence[str] | None") -> tuple:
    """The model chain a call may actually use.

    Filters the requested chain to the allowed set; raises when a model call is
    being attempted under a no-models configuration or when nothing survives
    the filter — silence would look like a provider outage."""
    if config.allowed_models == ():
        raise ConfigViolation("this configuration allows NO model calls "
                              "(pure deterministic profile)")
    if config.allowed_models is None:
        return tuple(requested or ())
    req = list(requested) if requested else list(config.allowed_models)
    kept = tuple(m for m in req
                 if any(m.startswith(a) or a in m
                        for a in config.allowed_models))
    if not kept:
        raise ConfigViolation(
            f"none of the requested models {req} are in the allowed set "
            f"{list(config.allowed_models)}")
    return kept


def permit_plan(config: SolverConfig, *, how_mode: str, handle: str = "",
                act_mode: str = "") -> None:
    """Refuse an execution plan the configuration forbids, with the reason."""
    text = f"{how_mode} {act_mode} {handle}".lower()
    if not config.internet_access and any(w in text for w in _NEEDS_INTERNET):
        raise ConfigViolation(
            "internet access is NOT allowed by this configuration; the plan "
            f"({how_mode}: {handle or act_mode}) needs it")
    if not config.code_authoring and how_mode in ("generate", "mutate"):
        raise ConfigViolation(
            "code authoring is NOT allowed by this configuration; only "
            "use/configure/compose of existing nodes is permitted")


class TokenMeter:
    """Tracks provider-reported tokens against the configured ceiling.

    Uncapped by default; when a ceiling is set, a call past it raises rather
    than silently continuing — spend is an explicit, visible boundary."""

    def __init__(self, config: SolverConfig):
        self.ceiling = config.budgets.max_tokens
        self.spent = 0

    def charge(self, tokens: int) -> None:
        self.spent += max(0, int(tokens))
        if self.ceiling is not None and self.spent > self.ceiling:
            raise ConfigViolation(
                f"token budget exhausted: {self.spent} spent of "
                f"{self.ceiling} allowed")

    def check(self) -> None:
        if self.ceiling is not None and self.spent >= self.ceiling:
            raise ConfigViolation(
                f"token budget exhausted: {self.spent} of {self.ceiling}")


def config_details(config: SolverConfig) -> dict:
    """The settings every prompt should carry so decisions weigh them."""
    return {"optimize_for": config.optimize_for,
            "internet_access": ("allowed" if config.internet_access
                                else "not allowed"),
            "code_authoring": ("allowed" if config.code_authoring
                               else "not allowed")}


# ---------------------------------------------------------------------------
# Self-test — deterministic, no network.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    # 1. defaults are FULL POWER: internet on, sanctioned models, authoring
    # on, budgets UNCAPPED, all reuse sources — restriction is an explicit
    # owner choice, never a silent default.
    c = SolverConfig()
    s = c.summary()
    check("defaults_are_full_power",
          s["internet access"] == "allowed"
          and s["models allowed"] == "the sanctioned roster"
          and s["code authoring"] == "allowed"
          and s["budgets"]["max_tokens"] == "uncapped"
          and s["reuse sources"] == ["internal", "github", "pypi"]
          and s["optimizing for"] == "accuracy",
          "full power by default; the config exists to RESTRICT on demand")

    # 2. internet off refuses an internet-needing plan with the reason.
    denied = ""
    try:
        permit_plan(SolverConfig(internet_access=False), how_mode="research",
                    handle="search_online::pubmed")
    except ConfigViolation as e:
        denied = str(e)
    check("internet_off_refuses_online_research_with_the_reason",
          "internet access is NOT allowed" in denied,
          denied[:80])
    permit_plan(SolverConfig(internet_access=True), how_mode="research",
                handle="search_online::pubmed")     # allowed -> no raise

    # 3. the model allow-list restricts the chain; empty = no model calls.
    c2 = SolverConfig(allowed_models=("glm-5.2",))
    kept = screen_models(c2, ("deepseek-v4-pro", "glm-5.2", "kimi-k2.7-code"))
    no_models_denied = False
    try:
        screen_models(SolverConfig(allowed_models=()), ("glm-5.2",))
    except ConfigViolation:
        no_models_denied = True
    check("the_model_allow_list_restricts_and_empty_means_no_calls",
          kept == ("glm-5.2",) and no_models_denied,
          "chain filtered to the allowed set; () raises before any call")

    # 4. a forbidden model can never be allowed by configuration.
    bad = False
    try:
        SolverConfig(allowed_models=("kimi-k3",))
    except ValueError:
        bad = True
    check("a_policy_forbidden_model_cannot_be_configured_in", bad,
          "kimi-k3 stays forbidden no matter the config")

    # 5. code authoring off forces reuse-only.
    denied2 = False
    try:
        permit_plan(SolverConfig(code_authoring=False), how_mode="generate",
                    handle="build::new_node")
    except ConfigViolation:
        denied2 = True
    permit_plan(SolverConfig(code_authoring=False), how_mode="use",
                handle="node_v1")                    # reuse still fine
    check("code_authoring_off_forces_reuse_only", denied2,
          "generate/mutate refused; use/configure/compose permitted")

    # 6. the token meter bites at the ceiling, loudly.
    m = TokenMeter(SolverConfig(budgets=Budgets(max_tokens=100)))
    m.charge(60)
    hit = False
    try:
        m.charge(60)
    except ConfigViolation as e:
        hit = "120" in str(e)
    m2 = TokenMeter(SolverConfig())                  # uncapped: never raises
    m2.charge(10_000_000)
    check("the_token_ceiling_bites_loudly_and_uncapped_never_does",
          hit and m2.spent == 10_000_000,
          "a set budget refuses past the ceiling; the default caps nothing")

    # 7. optimize_for is validated and travels into prompt details.
    bad2 = False
    try:
        SolverConfig(optimize_for="vibes")
    except ValueError:
        bad2 = True
    d = config_details(SolverConfig(optimize_for="runtime"))
    check("optimize_for_is_validated_and_reaches_every_prompt",
          bad2 and d["optimize_for"] == "runtime",
          "the priority metric is a closed set and rides the ask details")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "config_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
