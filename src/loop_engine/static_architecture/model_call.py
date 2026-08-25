"""The LLM-call plane — a STRICT, hand-owned DAG for every model call.

Owner rule (2026-08-22): calling a model is core infrastructure.  The
practitioner may build DAGs for novel problems, but it never rebuilds THIS one —
every model call in the system goes through the same strict four-stage DAG:

    prepare_context  ->  render  ->  call (+ model fallbacks)  ->  validate

The input is one standardized **question-in object** (``AskSpec``) carrying every
dimension of the ask: the question itself, the knowledge/context and WHICH VIEW of
it to show (the existing context policies: everything, task_only, blind,
goal_only, masked, ...), the persona, the output contract, the language, extra
details, the temperature, and a preference-ordered MODEL CHAIN.  Because the
dimensions are explicit fields, the same question can be asked many ways — full
context, no context, masked context, different persona — by changing one field,
which is exactly how the ask-strategy layer varies its asks.

Fallbacks are built in: if a model is down, errors, or returns output the
validator rejects, the call falls to the next model in the chain — the ask never
dies with one provider.  Every stage is recorded, so an AskResult says which view
was shown, which models were tried, which answered, and what it cost.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from ..strings.knowledge import Knowledge
from ..strings.context import CONTEXT_POLICIES, build_view
from ..static_architecture.ollama_client import ChatResult

# The default preference-ordered model chain (strong roster; edit per call).
DEFAULT_MODEL_CHAIN = ("deepseek-v4-pro", "glm-5.2", "kimi-k2.7-code")

CALL_STAGES = ("prepare_context", "render", "call", "validate")

# THE STANDARD PROMPT ASSEMBLY ORDER — every prompt integrates its elements in
# exactly this sequence (render() enforces it; seed salts arrive appended to the
# question by the question engine).  Standardized order means two asks differ
# ONLY by the dimensions that changed, never by accidental arrangement.
PROMPT_ASSEMBLY_ORDER = ("persona", "context_view", "details", "question",
                         "seed_salt", "output_contract", "language")


@dataclass
class AskSpec:
    """The standardized question-in object — every dimension of one ask."""
    question: str
    knowledge: "Knowledge | None" = None
    context_policy: str = "fully_informed"      # a key of CONTEXT_POLICIES
    persona: str = ""
    output_contract: str = ""                   # e.g. 'JSON array of moves'
    language: str = "en"
    details: dict = field(default_factory=dict)
    temperature: float = 0.7
    models: tuple = DEFAULT_MODEL_CHAIN         # preference-ordered fallbacks

    def __post_init__(self):
        if self.context_policy not in CONTEXT_POLICIES:
            raise ValueError(
                f"unknown context policy {self.context_policy!r}; valid: "
                f"{tuple(CONTEXT_POLICIES)}")
        if not self.models:
            raise ValueError("an AskSpec needs at least one model in its chain")


@dataclass
class AskResult:
    ok: bool
    text: str = ""
    model_used: str = ""
    models_tried: list = field(default_factory=list)
    fallbacks_used: int = 0
    total_tokens: int = 0
    context_policy: str = ""
    stages: list = field(default_factory=list)   # the strict DAG's trace
    error: str = ""

    def receipt(self) -> dict:
        return {"record_type": "model_call/v1", "ok": self.ok,
                "model_used": self.model_used,
                "models_tried": self.models_tried,
                "fallbacks_used": self.fallbacks_used,
                "total_tokens": self.total_tokens,
                "context_policy": self.context_policy, "stages": self.stages}


# -- stage 1: prepare_context ------------------------------------------------


def prepare_context(spec: AskSpec) -> str:
    """Shape WHICH VIEW of the knowledge the model sees, via the existing
    context policies — everything, task only, blind, goal only, masked, ...
    No knowledge means no context (the 'ask it cold' lane)."""
    if spec.knowledge is None:
        return ""
    view = build_view(spec.knowledge, spec.context_policy)
    lines = [f"{k}: {v}" for k, v in view.included.items()]
    if view.note:
        lines.append(f"(context view: {view.note})")
    return "\n".join(lines)


# -- stage 2: render ---------------------------------------------------------


def render(spec: AskSpec, context_text: str) -> str:
    """Deterministically assemble the dimensions into one prompt."""
    parts: list[str] = []
    if spec.persona:
        parts.append(f"You are {spec.persona}.")
    if context_text:
        parts.append(context_text)
    for k, v in spec.details.items():
        parts.append(f"{k}: {v}")
    parts.append(spec.question)
    if spec.output_contract:
        parts.append(f"Respond ONLY as: {spec.output_contract}.")
    if spec.language and spec.language != "en":
        parts.append(f"Respond in language: {spec.language}.")
    return "\n\n".join(p for p in parts if p)


# -- stages 3+4: call with fallbacks, validate -------------------------------


def execute_ask(spec: AskSpec, *,
                validate: Callable[[str], bool] | None = None,
                _call: "Callable[..., ChatResult] | None" = None) -> AskResult:
    """Run the strict DAG.  A model that errors, answers empty, or fails the
    validator falls through to the next model in the chain.  ``_call`` is
    injectable so the DAG is testable offline; production uses chat_maxout
    (full output ceiling, 10%-backoff-on-failure per model)."""
    if _call is None:
        from .provider_pinned import ProviderPinnedRequest, invoke_provider_model

        def _call(prompt, *, model, temperature):
            return invoke_provider_model(ProviderPinnedRequest(
                prompt=prompt, provider="ollama_cloud", model=model,
                temperature=temperature))

    stages: list = []
    ctx = prepare_context(spec)
    stages.append({"stage": "prepare_context",
                   "policy": spec.context_policy,
                   "chars": len(ctx)})
    prompt = render(spec, ctx)
    stages.append({"stage": "render", "chars": len(prompt)})

    tried: list = []
    tokens = 0
    last_err = ""
    for i, model in enumerate(spec.models):
        tried.append(model)
        try:
            res = _call(prompt, model=model, temperature=spec.temperature)
        except Exception as exc:                                # noqa: BLE001
            last_err = repr(exc)
            stages.append({"stage": "call", "model": model, "ok": False,
                           "error": last_err[:120]})
            continue
        tokens += getattr(res, "total_tokens", 0) or 0
        if not getattr(res, "ok", False) or not (res.text or "").strip():
            last_err = getattr(res, "error", "") or "empty reply"
            stages.append({"stage": "call", "model": model, "ok": False,
                           "error": last_err[:120]})
            continue
        stages.append({"stage": "call", "model": model, "ok": True,
                       "tokens": getattr(res, "total_tokens", 0) or 0})
        if validate is not None and not validate(res.text):
            last_err = "output failed validation"
            stages.append({"stage": "validate", "model": model, "ok": False})
            continue
        stages.append({"stage": "validate", "model": model, "ok": True})
        return AskResult(ok=True, text=res.text, model_used=model,
                         models_tried=tried, fallbacks_used=i,
                         total_tokens=tokens,
                         context_policy=spec.context_policy, stages=stages)
    return AskResult(ok=False, models_tried=tried,
                     fallbacks_used=max(0, len(tried) - 1),
                     total_tokens=tokens, context_policy=spec.context_policy,
                     stages=stages, error=last_err or "all models failed")


# ---------------------------------------------------------------------------
# Self-test — offline: an injected stub call, no network.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    k = Knowledge(goal="predict churn", graph_summary="3 nodes",
                  facts={"modality": "tabular"})

    # 1. the ask spec carries every dimension; unknown policy refused.
    spec = AskSpec(question="What is next?", knowledge=k,
                   context_policy="task_only", persona="a careful statistician",
                   output_contract="JSON array of moves",
                   details={"budget": "2 model calls"})
    bad = False
    try:
        AskSpec(question="x", context_policy="vibes")
    except ValueError:
        bad = True
    check("the_question_in_object_carries_all_dimensions_and_rejects_bad_policy",
          spec.persona and spec.output_contract and bad,
          "one standardized object: question/context-view/persona/contract/"
          "details/models; an unknown context policy is refused")

    # 2. the same question renders DIFFERENTLY under different context policies.
    p_full = render(spec, prepare_context(AskSpec(
        question="What is next?", knowledge=k, context_policy="fully_informed")))
    p_blind = render(spec, prepare_context(AskSpec(
        question="What is next?", knowledge=k, context_policy="goal_only")))
    check("context_policies_change_what_the_model_sees",
          len(p_full) > len(p_blind) and "What is next?" in p_blind,
          "fully_informed vs goal_only: same question, different visible context")

    # 3. persona, details, and output contract land in the prompt.
    prompt = render(spec, "CTX")
    check("persona_details_and_contract_land_in_the_rendered_prompt",
          "careful statistician" in prompt and "budget: 2 model calls" in prompt
          and "Respond ONLY as: JSON array of moves." in prompt,
          "the render stage assembles every populated dimension")

    # 4. FALLBACK: model 1 down -> model 2 answers; the trace shows it.
    def stub(prompt, *, model, temperature):
        if model == "m1":
            return ChatResult("", model, ok=False, error="503 down")
        return ChatResult("the answer", model, prompt_tokens=10, eval_tokens=5)
    r = execute_ask(AskSpec(question="q", models=("m1", "m2")), _call=stub)
    check("a_down_model_falls_back_to_the_next_in_the_chain",
          r.ok and r.model_used == "m2" and r.fallbacks_used == 1
          and r.models_tried == ["m1", "m2"],
          "m1 down -> m2 answered; the ask never dies with one provider")

    # 5. a reply that fails VALIDATION also falls through.
    def stub2(prompt, *, model, temperature):
        return ChatResult("not json" if model == "m1" else '["ok"]', model,
                          eval_tokens=3)
    r2 = execute_ask(AskSpec(question="q", models=("m1", "m2")),
                     validate=lambda t: t.strip().startswith("["), _call=stub2)
    check("invalid_output_falls_through_to_the_next_model",
          r2.ok and r2.model_used == "m2" and r2.fallbacks_used == 1,
          "validation is part of the strict DAG, not an afterthought")

    # 6. all models failing returns ok=False with the full trace, never raises.
    r3 = execute_ask(AskSpec(question="q", models=("m1", "m2")),
                     _call=lambda p, *, model, temperature: ChatResult(
                         "", model, ok=False, error="down"))
    check("total_failure_reports_honestly_instead_of_raising",
          not r3.ok and len(r3.models_tried) == 2 and r3.error,
          "the caller gets the failure and every stage tried")

    # 7. the receipt records the strict DAG's stages in order.
    stages = [s["stage"] for s in r.stages]
    check("the_receipt_traces_the_strict_dag_stages",
          stages[:2] == ["prepare_context", "render"]
          and "call" in stages and "validate" in stages,
          f"trace: {stages}")

    passed = sum(1 for r_ in results if r_["passed"])
    return {"record_type": "model_call_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
