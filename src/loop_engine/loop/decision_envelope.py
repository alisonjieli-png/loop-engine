"""DecisionEnvelope — the structured universal input; a prompt is one rendering.

The most important organizational improvement of the v3 design (§7, §12.1): the
universal input to a decision is not a prompt, it is a typed ``DecisionEnvelope``.
One object carries the task (original / canonical / simplified / fingerprint),
the active goal and success predicates, the current state and its context view,
the decision conditions (deadline, budget, risk, allowed and prohibited moves),
the cognition frame (persona, lenses, shuffle, salts, seeds), the available
capabilities, and the required output contract.

From that one object:

- a **deterministic resolver** reads the fields directly (``read_facts``);
- a **classifier** reads a feature vector (``to_features``);
- an **LLM adapter** renders a prompt (``render_prompt``).

So the same decision works with if-then rules, small models, embeddings, and
frontier models without a separate interface — the prompt is a rendered
artifact, not the universal contract.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any

from ..strings.frame import AskFrame
from ..strings.knowledge import Knowledge


@dataclass
class DecisionEnvelope:
    # -- task --
    original_task: str = ""
    canonical_task: str = ""
    simplified_task: str = ""
    task_fingerprint: dict = field(default_factory=dict)
    # -- goal --
    goal: str = ""
    purpose: str = ""
    horizon: str = "immediate"
    success_predicates: tuple[str, ...] = ()
    # -- state --
    knowledge: "Knowledge | None" = None
    context_view: dict = field(default_factory=dict)   # a ContextView.to_dict()
    decision_need: dict = field(default_factory=dict)  # a DecisionNeed.to_dict()
    # -- conditions --
    deadline: str = ""
    budget: float | None = None
    risk_posture: str = "balanced"
    allowed_move_families: tuple[str, ...] = ()
    prohibited_effects: tuple[str, ...] = ()
    # -- cognition --
    frame: AskFrame = field(default_factory=AskFrame)
    lexical_seed: int = 0
    random_seed: int = 0
    # -- capabilities --
    skills: tuple[str, ...] = ()
    models: tuple[str, ...] = ()
    # -- output contract --
    output_schema: str = "next_move_proposal_list"
    require_assumptions: bool = True
    require_confidence_basis: bool = True
    require_expected_cost: bool = True

    # --- three readings of the one object -------------------------------

    def read_facts(self) -> dict:
        """The fields a deterministic resolver reads directly — the knowledge
        facts plus the envelope's own conditions."""
        facts = dict(self.knowledge.facts) if self.knowledge else {}
        facts.update({"_goal": self.goal, "_horizon": self.horizon,
                      "_risk_posture": self.risk_posture,
                      "_deadline": self.deadline})
        return facts

    def to_features(self) -> dict:
        """A numeric/categorical feature view for a classifier or router — no
        free text, so a small model can consume it."""
        need_mode = self.decision_need.get("mode", "unknown")
        return {"horizon": self.horizon, "risk_posture": self.risk_posture,
                "need_mode": need_mode,
                "n_success_predicates": len(self.success_predicates),
                "n_allowed_families": len(self.allowed_move_families),
                "n_prohibited_effects": len(self.prohibited_effects),
                "has_budget": self.budget is not None,
                "n_skills": len(self.skills), "n_models": len(self.models),
                "n_facts": len(self.knowledge.facts) if self.knowledge else 0,
                "context_policy": self.context_view.get("policy", "none"),
                "task_family": self.task_fingerprint.get("task_family", ""),
                "modality": self.task_fingerprint.get("modality", "")}

    def render_prompt(self) -> str:
        """Render the envelope into a model prompt — one rendering of the object,
        assembled from the cognition frame, the task, the goal, the need, and the
        output contract."""
        parts = [self.frame.render_prompt_preamble()]
        task = self.simplified_task or self.canonical_task or self.original_task
        if task:
            parts.append(f"Task: {task}")
        if self.goal:
            parts.append(f"Goal: {self.goal}"
                         + (f" (purpose: {self.purpose})" if self.purpose else ""))
        if self.decision_need:
            parts.append(f"Open decision ({self.decision_need.get('mode', '?')}): "
                         + self.decision_need.get("question", ""))
        if self.allowed_move_families:
            parts.append("Allowed move families: "
                         + ", ".join(self.allowed_move_families))
        if self.prohibited_effects:
            parts.append("Prohibited effects: "
                         + ", ".join(self.prohibited_effects))
        req = []
        if self.require_assumptions:
            req.append("state your assumptions")
        if self.require_confidence_basis:
            req.append("give the basis of your confidence")
        if self.require_expected_cost:
            req.append("estimate the expected cost")
        parts.append(f"Respond as {self.output_schema}"
                     + ("; " + ", ".join(req) if req else "") + ".")
        return "\n".join(p for p in parts if p)

    def to_dict(self) -> dict:
        d = {k: v for k, v in asdict(self).items() if k != "knowledge"}
        d["frame"] = self.frame.as_dict()
        d["knowledge_goal"] = self.knowledge.goal if self.knowledge else None
        d["record_type"] = "decision_envelope/v1"
        d["the_rule"] = ("one typed object; a rule reads its fields, a classifier "
                         "reads its features, an LLM adapter renders its prompt — "
                         "the prompt is a rendering, not the interface")
        return d


# ---------------------------------------------------------------------------
# Self-test — deterministic, no model.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    env = DecisionEnvelope(
        original_task="Predict which accounts churn in 30 days.",
        simplified_task="binary tabular classification with time+entity",
        task_fingerprint={"task_family": "classification", "modality": "tabular"},
        goal="maximize private AUC under a runtime limit",
        purpose="win", horizon="tactical",
        success_predicates=("valid submission", "beat baseline"),
        knowledge=Knowledge(goal="churn", facts={"has_model": True,
                                                 "imbalanced": True}),
        context_view={"policy": "memory_informed"},
        decision_need={"mode": "route", "question": "which model branch next?"},
        allowed_move_families=("constructive", "search"),
        prohibited_effects=("deploy",),
        frame=AskFrame(persona="data_scientist", salts=("Could this leak?",)),
        skills=("train_model",), models=("kimi-k2",))

    facts = env.read_facts()
    check("a_rule_reads_the_envelope_fields_directly",
          facts["has_model"] is True and facts["_goal"].startswith("maximize")
          and facts["_horizon"] == "tactical",
          "a deterministic resolver reads the knowledge facts and the envelope's "
          "own conditions straight off the object — no prompt needed")

    feats = env.to_features()
    check("a_classifier_reads_a_feature_view",
          feats["need_mode"] == "route" and feats["task_family"] == "classification"
          and feats["has_budget"] is False and feats["context_policy"]
          == "memory_informed" and "original_task" not in feats,
          "the feature view is numeric/categorical only (need mode, task family, "
          "context policy, counts) — a small model or router can consume it, no "
          "free text")

    prompt = env.render_prompt()
    check("an_llm_adapter_renders_a_prompt_from_the_same_object",
          "binary tabular classification" in prompt
          and "which model branch next?" in prompt
          and "data_scientist" in prompt
          and "Allowed move families: constructive, search" in prompt
          and "Prohibited effects: deploy" in prompt
          and "state your assumptions" in prompt,
          "the rendered prompt carries the task, the open decision, the persona, "
          "the allowed/prohibited moves, and the output-contract requirements — "
          "one object, rendered for a model")

    # The three readings come from ONE object; changing the object changes all.
    env2 = DecisionEnvelope(original_task="x", horizon="campaign",
                            decision_need={"mode": "investigate"})
    check("all_three_readings_derive_from_the_one_envelope",
          env2.read_facts()["_horizon"] == "campaign"
          and env2.to_features()["need_mode"] == "investigate"
          and env2.to_dict()["record_type"] == "decision_envelope/v1",
          "a rule reading, a feature reading, and a dict all derive from the "
          "single envelope — the prompt is not the universal interface, the "
          "object is")

    # Determinism.
    check("envelope_readings_are_deterministic",
          env.render_prompt() == DecisionEnvelope(
              original_task="Predict which accounts churn in 30 days.",
              simplified_task="binary tabular classification with time+entity",
              task_fingerprint={"task_family": "classification",
                                "modality": "tabular"},
              goal="maximize private AUC under a runtime limit", purpose="win",
              horizon="tactical",
              success_predicates=("valid submission", "beat baseline"),
              knowledge=Knowledge(goal="churn",
                                  facts={"has_model": True, "imbalanced": True}),
              context_view={"policy": "memory_informed"},
              decision_need={"mode": "route",
                             "question": "which model branch next?"},
              allowed_move_families=("constructive", "search"),
              prohibited_effects=("deploy",),
              frame=AskFrame(persona="data_scientist",
                             salts=("Could this leak?",)),
              skills=("train_model",), models=("kimi-k2",)).render_prompt(),
          "the same envelope always renders the identical prompt")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "decision_envelope_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
