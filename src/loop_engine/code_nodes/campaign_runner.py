"""Five-problem, multi-mode campaign runner over the shared Loop runtime.

Architectural role: Code Node system for repeatable end-to-end evaluation.

The runner freezes each problem input and evaluator, expands nonredundant mode
and provider arms, records every arm in saved run history, and supports console event
viewing. Deterministic arms never carry a provider label. Model arms require an
explicit authorization flag and a physical-call ceiling.

The built-in cases are local control-plane tests. Kaggle acquisition and
submission remain separate effects and are not performed by this module.
"""
from __future__ import annotations

import json
import os
import re
import tempfile
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from ..core.runtime_settings import RuntimeSettings


CAMPAIGN_MODES = ("deterministic", "hybrid", "non_deterministic")
DEFAULT_PROVIDERS = ("ollama_cloud", "mistral", "openrouter")


def render_campaign_problem_prompt(case, arm, baseline):
    """Render one model prompt through the versioned prompt resource owner."""
    from ..strings.prompt_fragments import campaign_problem_prompt_bundle

    values = {
        "goal": case.goal,
        "inputs": case.inputs,
        "output_contract": case.output_contract,
    }
    provenance = {
        "goal": f"campaign.case.{case.case_id}.goal",
        "inputs": f"campaign.case.{case.case_id}.inputs",
        "output_contract": f"campaign.case.{case.case_id}.output_contract",
    }
    if arm.mode == "hybrid":
        values["baseline"] = baseline
        provenance["baseline"] = (
            f"campaign.case.{case.case_id}.deterministic_baseline")
    return campaign_problem_prompt_bundle().render(
        values, provenance=provenance)


def record_campaign_prompt_resource(rendered, *, ledger, parent) -> str:
    """Record safe prompt identity before returning model-ready text."""
    ledger.record(
        loop_id=parent.loop_id, event="custom",
        custom_kind="prompt_resource_rendered",
        prompt_resource=rendered.to_dict(include_text=False))
    return rendered.text


@dataclass(frozen=True)
class ProblemCase:
    case_id: str
    goal: str
    inputs: dict
    expected: dict
    output_contract: str
    deterministic_solver: object = field(repr=False, compare=False)

    def solve_deterministically(self) -> dict:
        return dict(self.deterministic_solver(dict(self.inputs)))

    def accepts(self, value) -> bool:
        return isinstance(value, dict) and all(
            value.get(key) == expected
            for key, expected in self.expected.items())

    def summary(self) -> dict:
        return {
            "case_id": self.case_id,
            "goal": self.goal,
            "input_keys": sorted(self.inputs),
            "expected_keys": sorted(self.expected),
            "output_contract": self.output_contract,
        }


@dataclass(frozen=True)
class ArmSpec:
    mode: str
    provider: str = ""
    llm_thinking_power: str = "medium"

    def __post_init__(self):
        if self.mode not in CAMPAIGN_MODES:
            raise ValueError(f"mode must be one of {CAMPAIGN_MODES}")
        if self.mode == "deterministic" and self.provider:
            raise ValueError("deterministic arms do not have a provider")
        if self.mode != "deterministic" and not self.provider:
            raise ValueError("model-using arms require a provider")
        if self.mode != "deterministic" and self.llm_thinking_power not in (
                "small", "medium", "high", "max", "specialized"):
            raise ValueError(
                "model-using arms need a valid llm_thinking_power")

    @property
    def arm_id(self) -> str:
        if not self.provider:
            return self.mode
        suffix = ("" if self.llm_thinking_power == "medium"
                  else f".{self.llm_thinking_power}")
        return f"{self.mode}.{self.provider}{suffix}"


@dataclass(frozen=True)
class CampaignSpec:
    campaign_id: str
    cases: tuple
    arms: tuple
    authorize_model_calls: bool = False
    max_model_calls: "int | None" = None
    max_total_tokens: "int | None" = None

    def __post_init__(self):
        if not self.campaign_id or not self.cases or not self.arms:
            raise ValueError("a campaign needs an id, cases, and arms")
        model_arms = sum(1 for case in self.cases for arm in self.arms
                         if arm.mode != "deterministic")
        if model_arms and not self.authorize_model_calls:
            raise ValueError(
                "model arms require authorize_model_calls=True")
        if (model_arms and self.max_model_calls is not None
                and self.max_model_calls < model_arms):
            raise ValueError(
                f"campaign needs at least {model_arms} model calls but the "
                f"declared ceiling is {self.max_model_calls}")

    @property
    def run_count(self) -> int:
        return len(self.cases) * len(self.arms)

    @property
    def model_arm_count(self) -> int:
        return sum(1 for case in self.cases for arm in self.arms
                   if arm.mode != "deterministic")

    def summary(self) -> dict:
        return {
            "record_type": "campaign_spec/v1",
            "campaign_id": self.campaign_id,
            "cases": [case.summary() for case in self.cases],
            "arms": [arm.arm_id for arm in self.arms],
            "runs": self.run_count,
            "model_arms": self.model_arm_count,
            "authorize_model_calls": self.authorize_model_calls,
            "max_model_calls": self.max_model_calls,
            "max_total_tokens": self.max_total_tokens,
        }


@dataclass
class ArmResult:
    case_id: str
    arm_id: str
    run_id: str
    accepted: bool
    value: object
    provider: str = ""
    model: str = ""
    physical_model_calls: int = 0
    input_tokens: "int | None" = 0
    output_tokens: "int | None" = 0
    accounting_complete: bool = True
    gateway_attempts: list = field(default_factory=list)
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "arm_id": self.arm_id,
            "run_id": self.run_id,
            "accepted": self.accepted,
            "value": self.value,
            "provider": self.provider,
            "model": self.model,
            "physical_model_calls": self.physical_model_calls,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "accounting_complete": self.accounting_complete,
            "gateway_attempts": list(self.gateway_attempts),
            "error": self.error,
        }


@dataclass
class CampaignResult:
    campaign_id: str
    arms: list
    runs_dir: str

    @property
    def accepted(self) -> int:
        return sum(1 for arm in self.arms if arm.accepted)

    @property
    def accounting_complete(self) -> bool:
        return all(arm.accounting_complete for arm in self.arms)

    def to_dict(self) -> dict:
        return {
            "record_type": "campaign_result/v1",
            "campaign_id": self.campaign_id,
            "runs": len(self.arms),
            "accepted": self.accepted,
            "failed": len(self.arms) - self.accepted,
            "physical_model_calls": sum(
                arm.physical_model_calls for arm in self.arms),
            "input_tokens": sum(
                arm.input_tokens or 0 for arm in self.arms),
            "output_tokens": sum(
                arm.output_tokens or 0 for arm in self.arms),
            "accounting_complete": self.accounting_complete,
            "runs_dir": self.runs_dir,
            "arms": [arm.to_dict() for arm in self.arms],
        }


def _support_case() -> ProblemCase:
    tickets = [
        {"id": "SUP-1042", "severity": 3, "blocked": 12, "minutes": 95},
        {"id": "SUP-1043", "severity": 2, "blocked": 1, "minutes": 180},
        {"id": "SUP-1044", "severity": 4, "blocked": 4, "minutes": 20},
    ]

    def solve(data):
        ranked = sorted(data["tickets"], key=lambda row: -(
            row["severity"] * 30 + row["blocked"] * 3
            + min(row["minutes"] // 15, 20)))
        return {"next_ticket": ranked[0]["id"],
                "reason": "highest combined severity and customer impact"}

    return ProblemCase(
        "support_queue", "Choose the next support incident and explain why.",
        {"tickets": tickets}, {"next_ticket": "SUP-1044"},
        '{"next_ticket":"SUP-####","reason":"one sentence"}', solve)


def _customer_import_case() -> ProblemCase:
    rows = [
        {"id": 1, "country": "US", "email": "a@example.com"},
        {"id": 2, "country": "XX", "email": "b@example.com"},
        {"id": 3, "country": "PH", "email": "bad-email"},
        {"id": 4, "country": "GB", "email": "d@example.com"},
    ]

    def solve(data):
        countries = {"US", "PH", "GB"}
        bad = [row["id"] for row in data["rows"]
               if row["country"] not in countries or "@" not in row["email"]]
        return {"valid_rows": len(data["rows"]) - len(bad),
                "quarantined_ids": bad,
                "decision": "import valid rows and quarantine invalid rows"}

    return ProblemCase(
        "customer_import", "Decide how to import customer rows safely.",
        {"rows": rows}, {"valid_rows": 2, "quarantined_ids": [2, 3]},
        '{"valid_rows":2,"quarantined_ids":[2,3],"decision":"..."}', solve)


def _invoice_case() -> ProblemCase:
    def solve(data):
        expected = {row["invoice_id"]: row["amount"]
                    for row in data["purchase_orders"]}
        mismatches = [row["invoice_id"] for row in data["invoices"]
                      if expected.get(row["invoice_id"]) != row["amount"]]
        return {"mismatched_invoices": mismatches,
                "action": "hold mismatches and pay exact matches"}

    return ProblemCase(
        "invoice_reconciliation",
        "Reconcile invoices and choose the safe payment action.",
        {"purchase_orders": [
            {"invoice_id": "INV-1", "amount": 1250},
            {"invoice_id": "INV-2", "amount": 840}],
         "invoices": [
            {"invoice_id": "INV-1", "amount": 1250},
            {"invoice_id": "INV-2", "amount": 940}]},
        {"mismatched_invoices": ["INV-2"]},
        '{"mismatched_invoices":["INV-2"],"action":"..."}', solve)


def _deployment_case() -> ProblemCase:
    def solve(data):
        unsafe = (data["error_rate"] > data["maximum_error_rate"]
                  or data["p95_ms"] > data["maximum_p95_ms"])
        return {"decision": "rollback" if unsafe else "continue",
                "main_reason": "error rate exceeds the release threshold"
                if data["error_rate"] > data["maximum_error_rate"]
                else "latency exceeds the release threshold" if unsafe
                else "all release checks pass"}

    return ProblemCase(
        "deployment_decision",
        "Decide whether to continue or roll back a production deployment.",
        {"error_rate": 0.031, "maximum_error_rate": 0.01,
         "p95_ms": 420, "maximum_p95_ms": 500},
        {"decision": "rollback"},
        '{"decision":"continue|rollback","main_reason":"..."}', solve)


def _delivery_case() -> ProblemCase:
    def solve(data):
        days = data["base_days"] + int(data["after_cutoff"])
        days += 1 if data["weekend_crossing"] else 0
        return {"estimated_days": days,
                "promise": f"delivery in {days} business days"}

    return ProblemCase(
        "delivery_estimate",
        "Estimate delivery time and state a customer-safe promise.",
        {"base_days": 2, "after_cutoff": True, "weekend_crossing": True},
        {"estimated_days": 4},
        '{"estimated_days":4,"promise":"one sentence"}', solve)


def default_problem_cases() -> tuple:
    return (_support_case(), _customer_import_case(), _invoice_case(),
            _deployment_case(), _delivery_case())


def campaign_arms(modes=CAMPAIGN_MODES,
                  providers=DEFAULT_PROVIDERS,
                  llm_thinking_power: str = "medium") -> tuple:
    """Expand arms without repeating deterministic work per provider."""
    out = []
    if "deterministic" in modes:
        out.append(ArmSpec("deterministic"))
    for mode in modes:
        if mode == "deterministic":
            continue
        out.extend(ArmSpec(mode, provider, llm_thinking_power)
                   for provider in providers)
    return tuple(out)


def default_campaign_spec(*, modes=CAMPAIGN_MODES,
                          providers=DEFAULT_PROVIDERS,
                          llm_thinking_power: str = "medium",
                          cases=None,
                          authorize_model_calls: bool = False,
                          max_model_calls: "int | None" = None,
                          max_total_tokens: "int | None" = None,
                          campaign_id: str = "five-utility-problems") -> CampaignSpec:
    return CampaignSpec(
        campaign_id, tuple(cases or default_problem_cases()),
        campaign_arms(modes, providers, llm_thinking_power),
        authorize_model_calls=authorize_model_calls,
        max_model_calls=max_model_calls,
        max_total_tokens=max_total_tokens)


def _extract_json(text: str):
    start, end = str(text).find("{"), str(text).rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        value = json.loads(str(text)[start:end + 1])
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


class WatchingLedger:
    """LoopLedger-compatible console tap for campaign progress."""
    def __init__(self, watch=False):
        from ..loop.recursive_loop import LoopLedger
        self._ledger = LoopLedger()
        self.watch = watch

    def __getattr__(self, name):
        return getattr(self._ledger, name)

    def record(self, **event):
        self._ledger.record(**event)
        if self.watch:
            loop_id = event.get("loop_id", "run") or "run"
            detail = event.get("step") or event.get("provider") or ""
            print(f"[{loop_id}] {event.get('event', 'event')} {detail}".rstrip())


@dataclass(frozen=True)
class CampaignRunOptions:
    """Runtime dependencies for a campaign, passed as one object."""

    runs_dir: str
    watch: bool = False
    runtime_settings: "RuntimeSettings | None" = field(
        default=None, repr=False, compare=False)
    model_call: "Callable | None" = field(
        default=None, repr=False, compare=False)

    def __post_init__(self):
        if not self.runs_dir:
            raise ValueError("CampaignRunOptions needs runs_dir")


class CampaignRunner:
    def __init__(self, spec: CampaignSpec, options: CampaignRunOptions):
        """Create a runner from one campaign and one runtime options object."""
        if not isinstance(options, CampaignRunOptions):
            raise TypeError("CampaignRunner needs CampaignRunOptions")
        self.spec = spec
        self.options = options
        self.runs_dir = options.runs_dir
        self.watch = options.watch
        self.runtime_settings = options.runtime_settings
        self.model_call = options.model_call or self._live_model_call
        self.model_calls_used = 0
        self.tokens_used = 0

    def _live_model_call(self, case, arm, baseline, *, ledger, parent):
        from ..core.provider_pinned import (
            ProviderPinnedRequest, invoke_provider_model)
        from ..core.provider_failover import PROVIDERS
        adapter = PROVIDERS.get(arm.provider)
        model = getattr(adapter, "DEFAULT_MODEL", "") if adapter else ""
        rendered_prompt = render_campaign_problem_prompt(
            case, arm, baseline)
        prompt = record_campaign_prompt_resource(
            rendered_prompt, ledger=ledger, parent=parent)
        if self.runtime_settings is not None:
            from ..core.runtime_settings import (
                ModelPolicyRequest, ModelTask)
            gateway = self.runtime_settings.build_gateway()
            tier = self.runtime_settings.models.tier(
                arm.llm_thinking_power)
            route_names = tuple(
                route_name for route_name in tier.routes
                if gateway.registry.get(route_name).provider == arm.provider)
            if not route_names:
                route_names = tuple(
                    route.name for route in gateway.registry.all()
                    if route.provider == arm.provider
                    and "counted_generation" in route.purposes)[:1]
            task = ModelTask(
                prompt=prompt,
                policy=ModelPolicyRequest(
                    thinking_power=arm.llm_thinking_power,
                    allow_escalation=False,
                    route_names=route_names,
                    max_route_attempts=1,
                    max_total_tokens=self.spec.max_total_tokens),
                output_contract=case.output_contract,
                temperature=0.2,
                trace_id=f"{case.case_id}.{arm.arm_id}")
            return gateway.invoke(
                self.runtime_settings.model_request(task),
                ledger=ledger, parent=parent)
        return invoke_provider_model(ProviderPinnedRequest(
            prompt=prompt, provider=arm.provider, model=model,
            max_output_tokens=None, thinking_power=arm.llm_thinking_power),
            ledger=ledger, parent=parent)

    def _model(self, case, arm, baseline, *, ledger, parent):
        if (self.spec.max_model_calls is not None
                and self.model_calls_used >= self.spec.max_model_calls):
            raise RuntimeError("campaign model-call ceiling reached")
        response = self.model_call(
            case, arm, baseline, ledger=ledger, parent=parent)
        physical = len(getattr(response, "attempts", ()))
        self.model_calls_used += physical
        tokens = getattr(response, "total_tokens", None)
        if tokens is not None:
            self.tokens_used += tokens
        if (self.spec.max_total_tokens is not None
                and self.tokens_used > self.spec.max_total_tokens):
            raise RuntimeError("campaign token ceiling reached")
        return response

    def run_arm(self, case: ProblemCase, arm: ArmSpec) -> ArmResult:
        from ..loop.recursive_loop import Loop, LoopConfig, StepOutcome

        ledger = WatchingLedger(self.watch)
        run_id = re.sub(
            r"[^a-z0-9_.-]+", "-",
            f"{self.spec.campaign_id}.{case.case_id}.{arm.arm_id}."
            f"{time.time_ns()}".lower())
        root = Loop(
            f"{case.goal} [{arm.arm_id}]",
            LoopConfig(
                framework="custom",
                custom_steps=("orient", "solve", "verify", "finish"),
                allowable_modes=("deterministic",),
                preferred_modes=("deterministic",),
                delegated_modes=CAMPAIGN_MODES,
                power="standard", max_depth=4),
            ledger=ledger)
        root.enable_run_history(run_id, root_dir=self.runs_dir)
        state = {"baseline": case.solve_deterministically(),
                 "value": None, "gateway": None, "accepted": False,
                 "error": ""}

        def handler(loop, step, context):
            if step == "orient":
                return StepOutcome(
                    output=f"case={case.case_id}; arm={arm.arm_id}",
                    mode="deterministic", confidence=1.0)
            if step == "solve":
                if arm.mode == "deterministic":
                    state["value"] = state["baseline"]
                    return StepOutcome(
                        output="solve:deterministic", mode="deterministic",
                        confidence=1.0)
                spawned = loop.spawn(
                    f"solve {case.case_id} with {arm.arm_id}",
                    LoopConfig(
                        framework="custom", custom_steps=("solve",),
                        allowable_modes=(arm.mode,),
                        preferred_modes=(arm.mode,),
                        delegated_modes=CAMPAIGN_MODES,
                        power="standard",
                        llm_thinking_power=arm.llm_thinking_power,
                        max_depth=4))

                def spawned_handler(spawned_loop, spawned_step, spawned_context):
                    try:
                        response = self._model(
                            case, arm, state["baseline"], ledger=ledger,
                            parent=spawned_loop)
                        state["gateway"] = response
                        spawned_loop.ledger.record(
                            loop_id=spawned_loop.loop_id, event="custom",
                            model_gateway_result=response.to_dict())
                        candidate = _extract_json(response.text) if response.ok else None
                        if arm.mode == "hybrid":
                            state["value"] = (candidate if case.accepts(candidate)
                                              else state["baseline"])
                            return StepOutcome(
                                output="hybrid:code-first candidate reviewed",
                                mode="hybrid", confidence=0.9)
                        state["value"] = candidate
                        return StepOutcome(
                            output="model-led candidate returned",
                            mode="non_deterministic",
                            confidence=0.9 if case.accepts(candidate) else 0.2,
                            failed=not case.accepts(candidate))
                    except Exception as exc:  # noqa: BLE001
                        state["error"] = f"{type(exc).__name__}: {exc}"[:200]
                        if arm.mode == "hybrid":
                            state["value"] = state["baseline"]
                            return StepOutcome(
                                output="hybrid:model unavailable; code result kept",
                                mode="hybrid", confidence=0.7)
                        return StepOutcome(
                            output="model-led:failed",
                            mode="non_deterministic", confidence=0.0,
                            failed=True)

                spawned.run(handler=spawned_handler, max_steps=2)
                return StepOutcome(
                    output=f"solve:{arm.arm_id}", mode="deterministic",
                    confidence=0.9 if state["value"] is not None else 0.1,
                    failed=state["value"] is None)
            if step == "verify":
                state["accepted"] = case.accepts(state["value"])
                return StepOutcome(
                    output=f"verify:accepted={state['accepted']}",
                    mode="deterministic",
                    confidence=1.0 if state["accepted"] else 0.1,
                    failed=not state["accepted"])
            return StepOutcome(output="finish:recorded", mode="deterministic",
                               confidence=1.0)

        root.run(handler=handler, max_steps=6)
        gateway = state["gateway"]
        attempts = list(getattr(gateway, "attempts", ()))
        last_attempt = attempts[-1] if attempts else None
        return ArmResult(
            case.case_id, arm.arm_id, run_id, state["accepted"], state["value"],
            provider=(getattr(gateway, "provider", "")
                      or getattr(last_attempt, "provider", "")),
            model=(getattr(gateway, "model", "")
                   or getattr(last_attempt, "model", "")),
            physical_model_calls=len(attempts),
            input_tokens=(getattr(gateway, "input_tokens", None)
                          if getattr(gateway, "input_tokens", None) is not None
                          else getattr(last_attempt, "input_tokens", None))
            if gateway is not None else 0,
            output_tokens=(getattr(gateway, "output_tokens", None)
                           if getattr(gateway, "output_tokens", None) is not None
                           else getattr(last_attempt, "output_tokens", None))
            if gateway is not None else 0,
            accounting_complete=(all(
                attempt.input_tokens is not None
                and attempt.output_tokens is not None for attempt in attempts)
                if attempts else gateway is None),
            gateway_attempts=[attempt.to_dict() for attempt in attempts],
            error=(state["error"] or getattr(gateway, "error", "")
                   or getattr(last_attempt, "error", "")))

    def run(self) -> CampaignResult:
        os.makedirs(self.runs_dir, exist_ok=True)
        results = [self.run_arm(case, arm)
                   for case in self.spec.cases for arm in self.spec.arms]
        return CampaignResult(self.spec.campaign_id, results, self.runs_dir)


def run_campaign_arm(runner: CampaignRunner, case: ProblemCase,
                     arm: ArmSpec) -> ArmResult:
    """Top-level operational boundary for one frozen campaign arm."""
    return runner.run_arm(case, arm)


def self_test() -> dict:
    """Offline campaign contracts and real deterministic executions only."""
    results = []

    def check(name, ok, detail=""):
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    arms = campaign_arms()
    check("default_matrix_is_five_deterministic_and_thirty_model_arms",
          len(default_problem_cases()) == 5 and len(arms) == 7
          and sum(arm.mode == "deterministic" for arm in arms) == 1)

    prompt_case = default_problem_cases()[0]
    prompt_arm = ArmSpec("hybrid", "ollama_cloud")
    prompt_render = render_campaign_problem_prompt(
        prompt_case, prompt_arm, prompt_case.solve_deterministically())
    check("campaign_prompt_uses_versioned_typed_resource",
          prompt_render.bundle_ref == "campaign.problem.solve@1.0.0"
          and len(prompt_render.bundle_digest) == 64
          and len(prompt_render.render_digest) == 64
          and "trust=\"untrusted_data\"" in prompt_render.text
          and "trust=\"trusted_contract\"" in prompt_render.text
          and "Code-first candidate" in prompt_render.text)
    prompt_ledger = WatchingLedger()
    prompt_text = record_campaign_prompt_resource(
        prompt_render, ledger=prompt_ledger,
        parent=type("PromptOwner", (), {"loop_id": "loop.prompt.test"})())
    prompt_events = [event for event in prompt_ledger.events
                     if event.get("custom_kind")
                     == "prompt_resource_rendered"]
    check("campaign_run_history_records_safe_prompt_identity",
          prompt_text == prompt_render.text and len(prompt_events) == 1
          and prompt_events[0]["prompt_resource"]["bundle_ref"]
          == prompt_render.bundle_ref
          and "text" not in prompt_events[0]["prompt_resource"])

    no_auth = False
    try:
        default_campaign_spec(max_model_calls=30)
    except ValueError:
        no_auth = True
    check("model_campaign_requires_explicit_authorization_and_call_ceiling",
          no_auth)

    deterministic = default_campaign_spec(
        modes=("deterministic",), providers=(),
        campaign_id="offline-five")
    with tempfile.TemporaryDirectory(prefix="loop-engine-campaign-") as root:
        det_result = CampaignRunner(
            deterministic, CampaignRunOptions(runs_dir=root)).run()
        check("five_deterministic_cases_run_and_save_run_histories",
              det_result.accepted == 5 and len(det_result.arms) == 5
              and det_result.to_dict()["physical_model_calls"] == 0
              and len(os.listdir(root)) == 5)

    one_case = default_problem_cases()[:1]
    model_arms = campaign_arms(
        modes=("hybrid", "non_deterministic"),
        providers=DEFAULT_PROVIDERS)
    model_spec = CampaignSpec(
        "authorized-live-model-matrix", one_case, model_arms,
        authorize_model_calls=True, max_model_calls=6)
    check("model_matrix_can_be_planned_but_is_not_run_by_offline_tests",
          model_spec.model_arm_count == 6
          and model_spec.authorize_model_calls
          and model_spec.max_model_calls == 6,
          "provider integration requires a separately authorized live run")

    passed = sum(1 for test in results if test["passed"])
    return {"record_type": "campaign_runner_contract_test/v2",
            "scope": "offline_contract_and_deterministic_execution",
            "provider_integration_proven": False,
            "tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
