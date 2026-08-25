"""The standard LLM-call architecture — four typed objects, one ordered prompt.

Owner spec (2026-08-23): every LLM or hybrid reasoning operation moves through
four typed objects, and the prompt is assembled from thirteen blocks in a
canonical order that experiments may vary — except the authority and task-
contract blocks, which can never be moved below lower-priority content.

    ReasoningRequest      — the semantic intent (what we ask, which problem
                            state / questions / context views / perspectives may
                            be used, output schema, allowed tools/models, budget)
        -> PromptAssemblySpec  — exactly what goes into the prompt and in what
                                 order (the 13 blocks + a named layout policy)
        -> ModelInvocationRequest — the assembled prompt + model params + seeds
                                    + prompt digest
        -> ModelInvocationResult  — the reply + usage + result digest

This standardizes the three things kept separate elsewhere: PROBLEM STATE &
EVIDENCE, REASONING RESOURCES (provisional), and the MODEL-READY PROMPT.  Seeds
are separated by role so wording variation is a named, measurable transformation
and the cache salt changes cache identity WITHOUT injecting nonsense into the
visible prompt.  ``invoke`` is injectable, so the whole pipeline is offline-
testable; production routes through the strict model-call DAG.
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, field, asdict
from typing import Callable, Sequence

# The 13 canonical prompt blocks, highest priority first.
PROMPT_BLOCKS = (
    "authority_and_policy",           # 1
    "model_role_and_capabilities",    # 2
    "objective_and_success",          # 3
    "immediate_question",             # 4
    "hard_constraints_and_tools",     # 5
    "verified_problem_state",         # 6
    "selected_evidence",              # 7
    "prior_attempts_and_failures",    # 8
    "reasoning_perspective",          # 9
    "question_pattern",               # 10
    "candidate_alternatives",         # 11
    "output_contract",                # 12
    "final_directive",                # 13
)

# Blocks that MUST stay in their guard positions — authority pinned to the top,
# the task contract + final directive pinned to the bottom; a layout policy may
# never move a lower-priority block above authority or below the contract.
PINNED_TOP = ("authority_and_policy",)
PINNED_BOTTOM = ("output_contract", "final_directive")
_MIDDLE = tuple(b for b in PROMPT_BLOCKS
                if b not in PINNED_TOP + PINNED_BOTTOM)

PROMPT_LAYOUT_POLICIES = (
    "canonical", "objective_first", "evidence_first", "question_last",
    "minimal_context", "incumbent_hidden", "primary_evidence_only",
    "failure_focused", "hierarchical_context", "randomized_evidence_order",
    "dual_pass_answer_and_critique")


@dataclass
class Seeds:
    """Seeds separated by ROLE — no single ambiguous salt.  ``cache_key_salt``
    changes cache identity only; ``lexical_variant_id`` names a wording
    transformation; the rest steer selection/order/demonstration sampling."""
    campaign_seed: int = 0
    variant_seed: int = 0
    provider_seed: int = 0
    context_selection_seed: int = 0
    context_order_seed: int = 0
    demonstration_seed: int = 0
    lexical_variant_id: int = 0
    cache_key_salt: str = ""


@dataclass
class ReasoningRequest:
    """The semantic intent of one reasoning operation."""
    question: str
    objective: str = ""
    problem_state: dict = field(default_factory=dict)
    allowed_questions: tuple = ()
    allowed_context_views: tuple = ()
    allowed_perspectives: tuple = ()
    output_schema: str = ""
    allowed_tools: tuple = ()
    allowed_models: tuple = ()
    allowed_routes: tuple = ()
    cost_budget: "float | None" = None


@dataclass
class PromptAssemblySpec:
    """What goes into the prompt and in what order."""
    blocks: dict = field(default_factory=dict)   # block name -> content
    layout_policy: str = "canonical"
    seeds: Seeds = field(default_factory=Seeds)

    def __post_init__(self):
        if self.layout_policy not in PROMPT_LAYOUT_POLICIES:
            raise ValueError(f"layout policy must be one of "
                             f"{PROMPT_LAYOUT_POLICIES}")


@dataclass
class ModelInvocationRequest:
    prompt: str
    ordered_blocks: list
    model_chain: tuple
    route_chain: tuple
    temperature: float
    seeds: Seeds
    prompt_digest: str
    cache_key: str


@dataclass
class ModelInvocationResult:
    ok: bool
    text: str = ""
    model_used: str = ""
    provider_used: str = ""
    route_used: str = ""
    prompt_tokens: "int | None" = 0
    eval_tokens: "int | None" = 0
    attempts: list = field(default_factory=list)
    result_digest: str = ""
    error: str = ""

    @property
    def total_tokens(self) -> "int | None":
        if self.prompt_tokens is None or self.eval_tokens is None:
            return None
        return self.prompt_tokens + self.eval_tokens


def _digest(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Layout — order the blocks under a named policy, guards enforced.
# ---------------------------------------------------------------------------


def layout_order(policy: str, present: Sequence[str],
                 seeds: "Seeds | None" = None) -> list:
    """The ordered list of block names for a policy over the present blocks.

    Authority stays first; the task contract + final directive stay last; the
    middle is reordered/filtered per policy.  Deterministic — randomized order
    uses ``context_order_seed``, never a clock."""
    present = [b for b in PROMPT_BLOCKS if b in present]     # canonical baseline
    top = [b for b in PINNED_TOP if b in present]
    bottom = [b for b in PINNED_BOTTOM if b in present]
    mid = [b for b in _MIDDLE if b in present]

    def front(name):
        if name in mid:
            mid.remove(name)
            mid.insert(0, name)

    def to_end(name):
        if name in mid:
            mid.remove(name)
            mid.append(name)

    def drop(*names):
        for n in names:
            if n in mid:
                mid.remove(n)

    if policy == "objective_first":
        front("objective_and_success")
    elif policy == "evidence_first":
        front("selected_evidence")
    elif policy == "question_last":
        to_end("immediate_question")
    elif policy == "minimal_context":
        drop("verified_problem_state", "selected_evidence",
             "candidate_alternatives", "prior_attempts_and_failures")
    elif policy == "incumbent_hidden":
        drop("prior_attempts_and_failures")
    elif policy == "primary_evidence_only":
        drop("reasoning_perspective", "question_pattern",
             "candidate_alternatives")
    elif policy == "failure_focused":
        front("prior_attempts_and_failures")
    elif policy == "randomized_evidence_order":
        rng = random.Random((seeds.context_order_seed if seeds else 0))
        rng.shuffle(mid)
    # canonical / hierarchical_context / dual_pass: middle unchanged
    return top + mid + bottom


def assemble_prompt(spec: PromptAssemblySpec) -> tuple:
    """Return (prompt_text, ordered_block_names).  The cache salt and lexical
    variant id are NOT rendered into the visible prompt — only the block
    contents are, in policy order.  A dual-pass policy appends a critique
    directive after the final directive's content."""
    order = layout_order(spec.layout_policy, list(spec.blocks), spec.seeds)
    parts = []
    for b in order:
        content = str(spec.blocks.get(b, "")).strip()
        if content:
            parts.append(content)
    prompt = "\n\n".join(parts)
    if spec.layout_policy == "dual_pass_answer_and_critique":
        prompt += ("\n\nThen, in a second pass, critique your own answer and "
                   "revise it if the critique holds.")
    return prompt, order


def cache_key(spec: PromptAssemblySpec, prompt: str) -> str:
    """Cache identity = prompt digest + the cache salt (salt changes identity
    WITHOUT appearing in the prompt)."""
    return _digest(prompt + "::" + spec.seeds.cache_key_salt)


# ---------------------------------------------------------------------------
# The pipeline: request -> assembly -> invocation request -> result.
# ---------------------------------------------------------------------------


def to_invocation(request: ReasoningRequest, spec: PromptAssemblySpec, *,
                  temperature: float = 0.7) -> ModelInvocationRequest:
    prompt, order = assemble_prompt(spec)
    return ModelInvocationRequest(
        prompt=prompt, ordered_blocks=order,
        model_chain=tuple(request.allowed_models),
        route_chain=tuple(request.allowed_routes),
        temperature=temperature, seeds=spec.seeds,
        prompt_digest=_digest(prompt),
        cache_key=cache_key(spec, prompt))


def invoke(inv: ModelInvocationRequest, *,
           ask: "Callable | None" = None, ledger=None,
           parent=None, gateway=None) -> ModelInvocationResult:
    """Run an invocation through the strict model-call DAG, AS A LOOP.

    Owner law (2026-08-24): every model call is a loop.  The four-stage DAG
    and the cloud-only gate are unchanged — this adds the envelope, so a
    provider call is never a silent side effect of a helper.  Pass ``ledger``
    to put the request and its outcome on the run's own timeline.
    ``ask`` stays injectable so the DAG remains testable offline."""
    if ask is not None:
        from ..static_architecture.model_call import AskSpec
        from ..loop.encapsulate import as_model_loop
        spec = AskSpec(question=inv.prompt, temperature=inv.temperature)
        if inv.model_chain:
            spec.models = inv.model_chain
        res = as_model_loop(inv.prompt[:60], lambda: ask(spec),
                            ledger=ledger, parent=parent)["value"]
        text = getattr(res, "text", "") or ""
        return ModelInvocationResult(
            ok=bool(getattr(res, "ok", False)), text=text,
            model_used=getattr(res, "model_used", ""),
            provider_used=getattr(res, "provider", ""),
            prompt_tokens=getattr(res, "total_tokens", 0), eval_tokens=0,
            result_digest=_digest(text),
            error="" if getattr(res, "ok", False)
            else getattr(res, "error", ""))

    from .model_gateway import (ModelGateway, ModelGatewayConfig,
                                ModelGatewayRequest)
    gateway = gateway or ModelGateway()
    response = gateway.invoke(
        ModelGatewayRequest(
            inv.prompt,
            ModelGatewayConfig(
                route_names=inv.route_chain,
                allowed_models=inv.model_chain,
                max_route_attempts=max(1, len(inv.route_chain) or 3)),
            temperature=inv.temperature),
        ledger=ledger, parent=parent)
    return ModelInvocationResult(
        ok=response.ok, text=response.text, model_used=response.model,
        provider_used=response.provider, route_used=response.route,
        prompt_tokens=response.input_tokens,
        eval_tokens=response.output_tokens,
        attempts=[attempt.to_dict() for attempt in response.attempts],
        result_digest=_digest(response.text), error=response.error)


def run_reasoning(request: ReasoningRequest, blocks: dict, *,
                  layout_policy: str = "canonical",
                  seeds: "Seeds | None" = None, temperature: float = 0.7,
                  ask: "Callable | None" = None, gateway=None,
                  ledger=None, parent=None) -> dict:
    """The whole standardized pipeline in one call, returning every typed
    object for the receipt."""
    spec = PromptAssemblySpec(blocks=blocks, layout_policy=layout_policy,
                              seeds=seeds or Seeds())
    inv = to_invocation(request, spec, temperature=temperature)
    result = invoke(inv, ask=ask, gateway=gateway,
                    ledger=ledger, parent=parent)
    return {"record_type": "reasoning_call/v1",
            "request": {"question": request.question,
                        "objective": request.objective},
            "assembly": {"layout_policy": spec.layout_policy,
                         "ordered_blocks": inv.ordered_blocks},
            "invocation": {"prompt_digest": inv.prompt_digest,
                           "cache_key": inv.cache_key},
            "result": asdict(result)}


# ---------------------------------------------------------------------------
# Self-test — offline: injected stub invoke, no network.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    all_blocks = {b: f"[{b}] content" for b in PROMPT_BLOCKS}

    # 1. canonical layout is the 13 blocks in order.
    order = layout_order("canonical", list(all_blocks))
    check("canonical_layout_is_the_thirteen_blocks_in_order",
          order == list(PROMPT_BLOCKS) and len(order) == 13,
          "the canonical baseline matches the spec's ordering")

    # 2. AUTHORITY stays first and the task contract stays last under EVERY
    # layout policy — the guard invariant.
    ok_pins = True
    for pol in PROMPT_LAYOUT_POLICIES:
        o = layout_order(pol, list(all_blocks))
        if o and o[0] != "authority_and_policy":
            ok_pins = False
        # output_contract and final_directive, when present, remain the last two
        tail = [b for b in o if b in PINNED_BOTTOM]
        if tail != [b for b in ("output_contract", "final_directive")
                    if b in o]:
            ok_pins = False
    check("authority_and_task_contract_blocks_cannot_be_moved",
          ok_pins,
          "no layout policy moves authority off the top or the contract off the "
          "bottom")

    # 3. a layout policy reorders the MIDDLE (evidence_first, question_last).
    ef = layout_order("evidence_first", list(all_blocks))
    ql = layout_order("question_last", list(all_blocks))
    check("layout_policies_reorder_the_middle_blocks",
          ef.index("selected_evidence") < ef.index("objective_and_success")
          and ql.index("immediate_question")
          == max(i for i, b in enumerate(ql) if b in _MIDDLE),
          "evidence_first fronts evidence; question_last sends the question to "
          "the end of the middle")

    # 4. minimal_context drops the heavy state/evidence blocks.
    mc = layout_order("minimal_context", list(all_blocks))
    check("minimal_context_drops_state_and_evidence",
          "verified_problem_state" not in mc and "selected_evidence" not in mc
          and "authority_and_policy" in mc and "output_contract" in mc,
          "minimal keeps authority + contract, drops the bulky context")

    # 5. the cache salt changes the cache key but NOT the visible prompt.
    s1 = PromptAssemblySpec(blocks=all_blocks, seeds=Seeds(cache_key_salt="a"))
    s2 = PromptAssemblySpec(blocks=all_blocks, seeds=Seeds(cache_key_salt="b"))
    p1, _ = assemble_prompt(s1)
    p2, _ = assemble_prompt(s2)
    check("the_cache_salt_changes_cache_identity_not_the_prompt",
          p1 == p2 and cache_key(s1, p1) != cache_key(s2, p2)
          and "cache_key_salt" not in p1 and "a" not in p1.split()[-3:],
          "salt alters cache identity without injecting into the prompt")

    # 6. seeds are separated by role (eight named fields, not one salt).
    check("seeds_are_separated_by_role",
          set(asdict(Seeds())) == {"campaign_seed", "variant_seed",
                                   "provider_seed", "context_selection_seed",
                                   "context_order_seed", "demonstration_seed",
                                   "lexical_variant_id", "cache_key_salt"},
          "no single ambiguous salt field")

    # 7. the four typed objects flow end to end with an injected invoker.
    class _A:
        ok = True; text = "the answer"; model_used = "stub"; total_tokens = 12
        error = ""
    req = ReasoningRequest(question="what is next?",
                           objective="win the task",
                           allowed_models=("glm-5.2",),
                           output_schema="JSON moves")
    out = run_reasoning(req, all_blocks, layout_policy="evidence_first",
                        seeds=Seeds(variant_seed=3),
                        ask=lambda spec: _A())
    check("the_four_typed_objects_flow_request_to_result",
          out["result"]["ok"] and out["result"]["text"] == "the answer"
          and out["assembly"]["layout_policy"] == "evidence_first"
          and out["invocation"]["prompt_digest"]
          and out["result"]["result_digest"],
          "ReasoningRequest -> PromptAssemblySpec -> ModelInvocationRequest -> "
          "ModelInvocationResult, all digested")

    from .model_gateway import GatewayAttempt, ModelGatewayResult

    class _Gateway:
        def invoke(self, request, **kwargs):
            return ModelGatewayResult(
                ok=True, text="gateway answer", provider="mistral",
                model="mistral-small", route="test.mistral",
                input_tokens=8, output_tokens=5,
                attempts=[GatewayAttempt(
                    "mistral", "mistral-small", "test.mistral", "loop2",
                    True, 8, 5, True, provider_ok=True)])

    gateway_out = run_reasoning(
        ReasoningRequest(question="use gateway", allowed_routes=(
            "test.mistral",)),
        all_blocks, gateway=_Gateway())
    check("production_reasoning_uses_the_provider_neutral_gateway",
          gateway_out["result"]["provider_used"] == "mistral"
          and gateway_out["result"]["route_used"] == "test.mistral"
          and gateway_out["result"]["prompt_tokens"] == 8
          and gateway_out["result"]["eval_tokens"] == 5
          and len(gateway_out["result"]["attempts"]) == 1,
          "provider, route, split usage, and attempts survive the typed path")

    # 8. assembly is deterministic — same inputs, same digest.
    a = to_invocation(req, PromptAssemblySpec(blocks=all_blocks,
                      seeds=Seeds(variant_seed=3)))
    b = to_invocation(req, PromptAssemblySpec(blocks=all_blocks,
                      seeds=Seeds(variant_seed=3)))
    check("assembly_is_deterministic_and_digested",
          a.prompt_digest == b.prompt_digest and a.cache_key == b.cache_key,
          "identical request+spec -> identical prompt digest + cache key")

    # 9. randomized_evidence_order is deterministic under a fixed seed and
    # still respects the pins.
    r1 = layout_order("randomized_evidence_order", list(all_blocks),
                      Seeds(context_order_seed=5))
    r2 = layout_order("randomized_evidence_order", list(all_blocks),
                      Seeds(context_order_seed=5))
    check("randomized_order_is_seeded_and_pin_respecting",
          r1 == r2 and r1[0] == "authority_and_policy"
          and r1[-1] == "final_directive",
          "the shuffle is reproducible by context_order_seed and never moves "
          "the pinned blocks")

    # 10. an unknown layout policy is refused.
    bad = False
    try:
        PromptAssemblySpec(blocks={}, layout_policy="freeform")
    except ValueError:
        bad = True
    check("an_unknown_layout_policy_is_refused", bad,
          "the layout-policy vocabulary is closed")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "reasoning_call_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
