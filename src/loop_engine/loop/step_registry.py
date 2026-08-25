"""The step registry — the live, tested map of the nine-step kernel.

Owner directive (2026-08-23): make the whole architecture maximally flexible,
understandable, separated, and well organized — for humans AND for LLMs.

This module is that organization made FIRST-CLASS.  For each of the nine kernel
steps it records, in one place:

  * the canonical full-sentence name and the question it answers;
  * whether the step is REQUIRED or OPTIONAL (and its kernel default);
  * its typed input -> output contract;
  * the ways it may be answered (deterministic / retrieved / model / hybrid …);
  * the MODULES and functions that provide its logic (its "shelf");
  * the extension point — where to add a new way to answer it.

It is both **human-readable** (``render_map`` / ``render_step`` print a clean
outline) and **machine-readable** (an LLM or tool queries ``step`` /
``steps_for_module`` to know exactly where a capability belongs).  Crucially it is
**tested against reality**: the self-test verifies every referenced default
exists, every referenced module imports, and the step keys / required-optional
split match the kernel exactly — so the map can never silently drift from the code.

Cross-cutting SERVICES (not steps) are listed separately: the strict model-call
DAG, the search/serve DAG, memory/commit, and the operating profile.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Sequence

from ..loop.kernel import (KERNEL_NODES, KERNEL_REQUIRED_NODES, KERNEL_OPTIONAL_NODES,
                     KERNEL_NODE_NAMES, KERNEL_NODE_QUESTIONS)

@dataclass
class KernelStep:
    number: int
    key: str                          # canonical node key (matches KERNEL_NODES)
    input_contract: str
    output_contract: str
    ways_to_answer: tuple             # resolution kinds, cheapest first
    modules: tuple                    # "module: what it provides here"
    kernel_default: str               # the default fn in kernel.py (or "" if req)
    extension_point: str              # how to add a new way to answer this step

    @property
    def name(self) -> str:
        return KERNEL_NODE_NAMES[self.key]

    @property
    def question(self) -> str:
        return KERNEL_NODE_QUESTIONS[self.key]

    @property
    def required(self) -> bool:
        return self.key in KERNEL_REQUIRED_NODES

    def to_dict(self) -> dict:
        return {"number": self.number, "key": self.key, "name": self.name,
                "question": self.question, "required": self.required,
                "input": self.input_contract, "output": self.output_contract,
                "ways_to_answer": list(self.ways_to_answer),
                "modules": list(self.modules),
                "kernel_default": self.kernel_default,
                "extension_point": self.extension_point}


# The authoritative map.  Ordered exactly like KERNEL_NODES.
KERNEL_STEP_REGISTRY: tuple = (
    KernelStep(
        1, "orient", "PractitionerState", "Situation",
        ("cached state", "retrieval", "deterministic reconstruction"),
        ("kernel: default_orient (state reconstruction)",
         "store_serve: search relevant resources",
         "context: Context Views over memory",
         "kernel_model_impls: orient (search-backed situation)"),
        "default_orient",
        "provide an `orient` impl returning a Situation; register context "
        "sources as searchable resources"),
    KernelStep(
        2, "reconcile_horizon", "PractitionerState + Situation",
        "LongHorizonAnchorPacket",
        ("no-op minimal anchor", "goal-stack + blueprint reconciliation",
         "typed Goal Graph / Plan Frontier"),
        ("blueprint: GoalStack, WorkingBlueprint, LongHorizonAnchorPacket, "
         "build_anchor, WorkPacket, ELABORATION_LEVELS",
         "planning: GoalGraph, BlueprintItem, CheckpointContract, PlanFrontier, "
         "validate_blueprint",
         "task_blueprint: opening-move sequence that biases step 4",
         "kernel: default_reconcile_horizon"),
        "default_reconcile_horizon",
        "provide a `reconcile_horizon` impl returning a LongHorizonAnchorPacket; "
        "add plan schemas in planning.py"),
    KernelStep(
        3, "assess_prepare", "PractitionerState + Situation",
        "DecisionSupportPortfolio",
        ("sufficient_no_expansion", "retrieve reusable resources",
         "generate provisional resources", "spawn a research child"),
        ("enrichment: coverage_probe, generate_enrichment (personas/questions)",
         "question_engine + question_bank: question forms and tiers",
         "capture: required opening scaffolding (research, outline, watch-outs, "
         "common/uncommon mistakes, best practices, success measures)",
         "sub_practitioner: spawn a research child practitioner",
         "kernel: default_assess_prepare"),
        "default_assess_prepare",
        "provide an `assess_prepare` impl; register question/persona generators "
        "and research recipes"),
    KernelStep(
        4, "decide_next", "PractitionerState + Situation", "CandidateAction[]",
        ("deterministic rule", "muscle-memory shortcut", "heuristic",
         "one model call", "council / debate", "biased by opening sequence"),
        ("biases: apply_biases (standing instincts, evidence-demotable)",
         "bias_checklist: semi-persistent preferred-steps checklist carried in "
         "every prompt (research-first; before AND after; skips tracked with "
         "why/when/where/how; freedom to choose once all steps resolved)",
         "task_blueprint: bias_next_from_blueprint (opening moves)",
         "solution_shaping: should_decompose (decompose / monolithic / escalate) "
         "+ shaping strings (outside-the-box, stacking/bagging/ensemble)",
         "decision_schemas: prompt-side reasoning shapes that bias what the model "
         "CONSIDERS (INTELLIGENCE; check_engagement is a soft signal — admission "
         "is runtime_contracts, bridged via to_contract)",
         "output_templates: the response-form ladder (string->list->if/then->"
         "measurement->evaluation->code) biasing reusable forms",
         "follow_up: reactive scheduler obligations (justify/review/structure/"
         "reframe) that lead the candidate list",
         "failure_response: on an error, bias toward diagnose_and_repair / "
         "research / try_other_method (don't hit the same wall; escalate/abstain "
         "when exhausted)",
         "intelligence_strings: compose reasoning strings into the prompt",
         "ask_strategies + question_engine: ways of asking",
         "ollama_resolvers: debate / council",
         "kernel: default_decide_next; kernel_model_impls: decide_next"),
        "default_decide_next",
        "register a bias in biases.py or a question form/strategy; provide a "
        "`decide_next` impl to change candidate generation"),
    KernelStep(
        5, "how", "PractitionerState + Situation + CandidateAction",
        "ExecutionPlan",
        ("exact reuse", "learned shortcut", "deterministic wrapper",
         "compose / configure", "template mutate", "generate"),
        ("methodical: EXECUTION_LADDER + reuse_first_guard (cheapest-first)",
         "self_improve: shortcut probe (learned zero-model routes)",
         "store_serve: capability search (find_executor / nodes)",
         "solution_shaping: sub-model / sub-process / ensemble moves",
         "config: permit_plan (authority gates)",
         "kernel: default_how"),
        "default_how",
        "register a node/executor as a searchable resource; provide a `how` impl "
        "to change method selection"),
    KernelStep(
        6, "act", "PractitionerState + ExecutionPlan", "ResultPacket[]",
        ("run a deterministic node", "run a task graph", "one model call",
         "author via OpenCode worker", "spawn child practitioners",
         "matrix waterfall"),
        ("competition_solver: tabular/image executors (searchable nodes)",
         "rl_vocabulary: policies + novelty/action search",
         "opencode_client: headless coding workers",
         "sub_practitioner + kernel.run_practitioner: child practitioners",
         "canvas: matrix-of-solutions execution",
         "kaggle_executor: real tabular submissions",
         "kernel: default_act"),
        "default_act",
        "register an executor node behind execute(spec)->outcome and add it to "
        "the resource store; add a policy kind in rl_vocabulary"),
    KernelStep(
        7, "verify", "PractitionerState + ExecutionPlan + ResultPacket[]",
        "EvaluationPacket",
        ("deterministic checks", "degeneracy detectors", "contract check",
         "model interrogation", "adversarial review"),
        ("review_mode: degeneracy detectors + the interrogatory battery "
         "(a constant / chance-level / empty result is DEGENERATE, rejected)",
         "measurement: select_measures + read_generalization_gap (train-CV gap) "
         "+ measurement strings (metrics, industry conventions, success framing)",
         "interrogation: the expert questions that separate naive from expert "
         "solutions (residual patterns, latent structure, errors-of-errors, "
         "is-this-the-best-way); each says if a code node or an LLM answers it",
         "kernel: default_verify"),
        "default_verify",
        "add a detector or interrogatory in review_mode.py; provide a `verify` "
        "impl for domain evaluators"),
    KernelStep(
        8, "integrate_commit", "PractitionerState + PassRecord",
        "committed PractitionerState",
        ("no-op (route commits)", "distill shortcuts",
         "update plan + checkpoint", "track dispositions"),
        ("self_improve: could_this_be_cheaper -> distill a Shortcut",
         "capture: encapsulate open-ended results into standardized reusable "
         "units + the fail-closed gate before composing the next step",
         "learning_bundle: every pass gets a LearningBundle + disposition; "
         "requires_additional_structuring blocks integration (3 storage stages)",
         "planning: complete_item / satisfy (evidence-gated)",
         "closure: track item dispositions for the no-orphan audit",
         "kernel: default_integrate_commit"),
        "default_integrate_commit",
        "provide an `integrate_commit` impl to commit domain artifacts; add a "
        "distillation trigger in self_improve.py"),
    KernelStep(
        9, "route", "PractitionerState + PassRecord",
        "RouteDecision + new PractitionerState",
        ("continue", "repair", "reset ladder (soft->cold)", "branch", "distill",
         "escalate", "close checkpoint", "finish"),
        ("kernel: default_route (repair->soft_reset->cold_restart escalation)",
         "closure: audit_run (fail-closed no-orphan check before close)",
         "kernel: plan_skip_next_pass (per-pass optional-node skip)",
         "practitioner_loop: logjam detection + documented reset (reference)"),
        "default_route",
        "provide a `route` impl to emit richer routes (branch/distill/escalate); "
        "call closure.audit_run before finishing"),
)

# Cross-cutting services — hand-owned, used by many steps, never step-specific.
SERVICE_MAP: tuple = (
    ("model-call DAG", "model_call + reasoning_call + model_routes",
     "every model call: ReasoningRequest -> PromptAssemblySpec (13 blocks) -> "
     "ModelInvocationRequest -> ModelInvocationResult; provider-neutral routes "
     "(cloud-only policy, local wired-but-gated); fallbacks + seeds"),
    ("two primitives (String | Code node)", "asset_class",
     "THE classification of everything: literally every resource, asset, node, "
     "and text is a STRING (an LLM reads it) or a CODE NODE (the machine runs "
     "it; may READ strings). 'Contract / logic / capability' are ROLES a code "
     "node plays (validate / decide / execute / adapt / detect), not separate "
     "primitives. Same need, either primitive; the arrow STRING -> CODE NODE is "
     "the distillation flywheel"),
    ("logic (safe AST)", "logic_ast",
     "the Logic category: a closed-operator expression AST (never eval) that "
     "COMPUTES/DECIDES deterministically; the executor for a captured "
     "logic_candidate; emits findings/actions, abstains outside scope, never "
     "mutates state"),
    ("capability directory (handshakes + endpoints)", "capability_directory",
     "how the practitioner KNOWS what strings / code nodes / static components are "
     "available and HOW to call them: a CapabilityHandshake per surface (kind, "
     "operations, query fields, ranking, health — read before use, never "
     "assumed), and a standardized directory (discover / negotiate / call / serve) "
     "with declared fallbacks. serve() is the two-rail bias: use a code node if "
     "one serves the op, else fall back to the LLM-call pipeline"),
        ("real loop handlers", "loop_handlers",
     "the Loop on the REAL infrastructure: directory_handler pulls the mandatory "
     "string intelligence per step (the power lever), probes the code rail with a "
     "real search through the capability directory, resolves deterministic steps "
     "to real code nodes, escalates an empty code rail to the LLM surface "
     "(hybrid), and records every infra call on the ledger; run_loop_via_kernel "
     "delegates a nine_step loop to the wired kernel"),
    ("the Loop (everything is a loop)", "recursive_loop",
     "the fundamental object: a Loop is an initializable, parameterized CLASS — "
     "pass in framework (nine_step | five_step | custom | open), allowable + "
     "preferred MODES (deterministic | hybrid | non_deterministic, a waterfall "
     "with fallback), and a POWER lever (small..max sets string-intelligence pull "
     "+ model-call budget). One loop can SPAWN another (recursive initialization; "
     "loops of loops), all tracked on one shared ledger. nine_step is the default; "
     "the kernel is its executor. The wedge is reusable code nodes + string "
     "intelligence flowing through it"),
    ("decision engine (per-node sub-layer)", "decision_engine",
     "the immediate sub-node under EVERY one of the nine kernel nodes: resolve_path "
     "asks 'deterministic, deterministic + LLM repair, or non-deterministic?' and "
     "branches into three, deciding from heuristics / memory / policy (settings "
     "like model + internet access gate the paths) — the two-rail choice refined "
     "into three, one engine per node"),
    ("continuous improvement (housekeeping)", "housekeeping",
     "a SEPARATE-PURPOSE run of the SAME practitioner loop (self-improvement "
     "objective + instructions): on a trigger/cron it mines our runtimes/logs and "
     "customer legacy code (GitHub URLs) and proposes new code nodes, strings, "
     "logic, and biases — classified string vs code, all runtime CANDIDATES "
     "(promotion is the evidence-gated boundary, never done here)"),
    ("live wiring", "wiring",
     "the composed entry point run_wired: enriches the deterministic kernel "
     "defaults so the LIVE loop exercises guidance, shaping, measurement, "
     "contracts, capture, and learning end-to-end"),
    ("runtime contracts", "runtime_contracts",
     "executable TRUTH at every boundary: ContractDefinition (immutable, "
     "versioned) + deterministic validator + explicit adapter. Distinct "
     "authority from intelligence — a contract ADMITS/REJECTS a result; "
     "intelligence only PROPOSES a contract (to_contract / ContractCandidate)"),
    ("search / serve DAG", "store_serve",
     "one strict search over ALL resources (nodes, packs, rules, prior runs); "
     "tier gates; capability requests"),
    ("resources", "question_engine + question_bank + domain_pack + intelligence_strings + intelligence_registry + packs",
     "question forms/tiers, personas, context/layout policies, Domain Support "
     "Packs, and intelligence-as-strings; intelligence_registry standardizes the Database vs Runtime tiers (serve/version/track/promote)"),
    ("operating profile + config", "operating_profile + config",
     "five enum modes resolved Platform->Org->Project->Run->Child; enforced at "
     "the how/act/model boundaries"),
    ("model transport", "ollama_client + opencode_client",
     "Ollama Cloud (token-counted) + OpenCode headless workers (cloud-only)"),
)


def step(key_or_number) -> KernelStep:
    """Look up a step by its canonical key (e.g. 'decide_next') or number (4)."""
    for s in KERNEL_STEP_REGISTRY:
        if s.key == key_or_number or s.number == key_or_number:
            return s
    raise KeyError(f"no kernel step {key_or_number!r}; keys are {KERNEL_NODES}")


def steps_for_module(module_basename: str) -> list:
    """Which kernel steps a module serves — 'where does this file belong?'."""
    hits = []
    for s in KERNEL_STEP_REGISTRY:
        if any(m.split(":")[0].strip() == module_basename
               or module_basename in m.split(":")[0]
               for m in s.modules):
            hits.append(s.key)
    return hits


def render_step(s: KernelStep) -> str:
    tag = "REQUIRED" if s.required else "OPTIONAL"
    lines = [f"STEP {s.number} — {s.key}  [{tag}]",
             f"  {s.name}",
             f"  Q: {s.question}",
             f"  {s.input_contract}  ->  {s.output_contract}",
             f"  ways: {', '.join(s.ways_to_answer)}",
             "  modules:"]
    lines += [f"    - {m}" for m in s.modules]
    if s.kernel_default:
        lines.append(f"  default: kernel.{s.kernel_default}")
    lines.append(f"  extend: {s.extension_point}")
    return "\n".join(lines)


def render_map() -> str:
    """The whole architecture as one clean outline — for a human or an LLM."""
    out = ["THE NINE-STEP PRACTITIONER KERNEL — where every capability lives", ""]
    for s in KERNEL_STEP_REGISTRY:
        out.append(render_step(s))
        out.append("")
    out.append("CROSS-CUTTING SERVICES (used by many steps, never step-specific):")
    for name, mods, desc in SERVICE_MAP:
        out.append(f"  - {name}  [{mods}]")
        out.append(f"      {desc}")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Self-test — the map is verified AGAINST the code so it cannot silently drift.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    keys = tuple(s.key for s in KERNEL_STEP_REGISTRY)

    # 1. the registry covers exactly the nine kernel nodes, in order.
    check("the_registry_matches_the_kernel_nodes_exactly",
          keys == tuple(KERNEL_NODES) and len(KERNEL_STEP_REGISTRY) == 9,
          f"registry keys == KERNEL_NODES ({len(keys)} steps)")

    # 2. required / optional match the kernel's handshake split.
    reg_req = tuple(s.key for s in KERNEL_STEP_REGISTRY if s.required)
    reg_opt = tuple(s.key for s in KERNEL_STEP_REGISTRY if not s.required)
    check("required_and_optional_match_the_kernel_handshake",
          set(reg_req) == set(KERNEL_REQUIRED_NODES)
          and set(reg_opt) == set(KERNEL_OPTIONAL_NODES),
          "the map's required/optional split is the kernel's, not a guess")

    # 3. every referenced kernel default actually EXISTS (map can't lie).
    from ..architecture_map import module_path
    kernel_mod = importlib.import_module(module_path("kernel"))
    missing = [s.kernel_default for s in KERNEL_STEP_REGISTRY
               if s.kernel_default and not hasattr(kernel_mod, s.kernel_default)]
    check("every_referenced_kernel_default_exists",
          not missing, f"missing defaults: {missing}")

    # 4. every module named in the map IMPORTS (no dangling references).
    named = set()
    for s in KERNEL_STEP_REGISTRY:
        for m in s.modules:
            # a module cell may name several modules ("a + b: what they do")
            for part in m.split(":")[0].split(" + "):
                named.add(part.strip().split(".")[0])   # 'kernel.run_...' -> 'kernel'
    for _n, mods, _d in SERVICE_MAP:
        for m in mods.split(" + "):
            named.add(m.strip().split(".")[0])
    unimportable = []
    for m in named:
        if m in ("kernel", ""):
            continue
        try:
            importlib.import_module(module_path(m))
        except ModuleNotFoundError as exc:
            unimportable.append(f"{m} (missing {exc.name})")
        except Exception:                                       # noqa: BLE001
            unimportable.append(m)
    check("every_module_named_in_the_map_imports",
          not unimportable,
          f"unimportable: {unimportable}")

    # 5. lookup by key and by number both work; unknown raises.
    bad = False
    try:
        step("nope")
    except KeyError:
        bad = True
    check("step_lookup_by_key_and_number_works",
          step("decide_next").number == 4 and step(6).key == "act" and bad,
          "step('decide_next') and step(6) resolve; unknown raises")

    # 6. reverse lookup answers 'where does this module belong?'.
    where = steps_for_module("review_mode")
    where2 = steps_for_module("biases")
    check("reverse_lookup_places_a_module_under_its_steps",
          "verify" in where and "decide_next" in where2,
          "review_mode -> step 7 (verify); biases -> step 4 (decide)")

    # 7. the rendered map is complete and human-readable.
    txt = render_map()
    check("the_rendered_map_lists_all_nine_steps_and_services",
          all(f"STEP {i}" in txt for i in range(1, 10))
          and "CROSS-CUTTING SERVICES" in txt
          and "model-call DAG" in txt,
          "render_map prints all nine steps + the services outline")

    # 8. each step declares an extension point (where to add logic).
    check("every_step_declares_where_to_extend_it",
          all(len(s.extension_point) > 20 and s.ways_to_answer
              for s in KERNEL_STEP_REGISTRY),
          "an LLM or human can read where a new capability belongs for any step")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "step_registry_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
