"""The architecture as a typed model, rendered into diagrams.

A diagram drawn by hand starts accurate and drifts, because nothing makes it
wrong when the code moves. The way to stop that is to make the picture a
projection of something the code can contradict: every element here names a
real module, and a self-test fails if any of them stops existing. Rename a
module and the diagram breaks loudly instead of lying quietly.

The typed model is the record. C4 and Mermaid are two renderings of it, and
neither is the source of truth. The distinction matters because a diagram
language can express things the system does not do, and once the picture is
authoritative those inventions become requirements nobody agreed to.

Owns:
    - Element, Relationship: the typed model and explicit evidence state.
    - Context, container, component, dynamic, and identity-lattice views.
    - render_mermaid(), render_c4_dsl(): two renderings, neither canonical.

The architecture authority remains architecture_map and architecture.yaml.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass

from .architecture_diagram_text import (
    DIAGRAM_PREAMBLE,
    LOOP_CLASSIFICATION_TREE,
    ROLE_PROFILE_TREE,
)

DIAGRAM_RECORD_TYPE = "architecture_diagram/v1"

#: C4's levels, and the one extra this repository needs. A run's dynamic
#: shape is a sequence rather than a structure, and forcing it into a
#: component diagram loses the ordering that is the whole point of it.
CONTEXT, CONTAINER, COMPONENT, DYNAMIC = (
    "context", "container", "component", "dynamic")
DIAGRAM_LEVELS = (CONTEXT, CONTAINER, COMPONENT, DYNAMIC)

#: What an element is. Kept small: a vocabulary large enough to describe
#: anything describes nothing, and these are the kinds this system has.
PERSON, SYSTEM, EXTERNAL, CONTAINER_KIND, STORE, COMPONENT_KIND = (
    "person", "system", "external", "container", "store", "component")

#: What the code and saved evidence currently support. A diagram without this
#: field turns a target into an implementation claim merely by drawing it.
IMPLEMENTED, PARTIAL, SHADOW, TARGET = (
    "implemented", "partial", "shadow", "target")
EVIDENCE_STATES = (IMPLEMENTED, PARTIAL, SHADOW, TARGET)


@dataclass(frozen=True)
class Element:
    """One box, and the module that makes it real."""

    key: str
    name: str
    kind: str = COMPONENT_KIND
    description: str = ""
    #: The module this element stands for. An element that names one must
    #: name one that exists; that is what keeps the picture honest.
    module: str = ""
    evidence_state: str = IMPLEMENTED

    def __post_init__(self):
        if not self.key.strip() or not self.name.strip():
            raise ValueError("a diagram element needs a key and a name")
        if self.evidence_state not in EVIDENCE_STATES:
            raise ValueError(
                f"unknown diagram evidence state {self.evidence_state!r}")


@dataclass(frozen=True)
class Relationship:
    """One arrow, and what actually travels along it."""

    source: str
    target: str
    label: str = ""
    #: What crosses this edge. An unlabelled arrow means "these are somehow
    #: related", which is the least useful thing a diagram can say.
    carries: str = ""


@dataclass(frozen=True)
class DiagramModel:
    """A typed picture of one level."""

    key: str
    title: str
    level: str
    elements: tuple[Element, ...] = ()
    relationships: tuple[Relationship, ...] = ()
    note: str = ""

    def __post_init__(self):
        if self.level not in DIAGRAM_LEVELS:
            raise ValueError(f"unknown diagram level {self.level!r}")
        keys = [item.key for item in self.elements]
        if len(set(keys)) != len(keys):
            raise ValueError("diagram elements repeat a key")
        known = set(keys)
        for edge in self.relationships:
            missing = {edge.source, edge.target} - known
            if missing:
                raise ValueError(
                    f"relationship names elements not in the diagram: "
                    f"{sorted(missing)}")

    @property
    def modules(self) -> tuple[str, ...]:
        return tuple(item.module for item in self.elements if item.module)

    def to_dict(self) -> dict:
        return {
            "record_type": DIAGRAM_RECORD_TYPE, "key": self.key,
            "title": self.title, "level": self.level, "note": self.note,
            "elements": [{"key": item.key, "name": item.name,
                          "kind": item.kind, "description": item.description,
                          "module": item.module,
                          "evidence_state": item.evidence_state}
                         for item in self.elements],
            "relationships": [{"source": item.source, "target": item.target,
                               "label": item.label, "carries": item.carries}
                              for item in self.relationships],
        }


RUNTIME_CONTEXT = DiagramModel(
    key="context", level=CONTEXT,
    title="Loop Engine in its setting",
    note="What a run reaches outside itself.",
    elements=(
        Element("operator", "Operator", PERSON,
                "Sets the task, the authority, and the budget."),
        Element("engine", "Loop Engine", SYSTEM,
                "Interprets the task and performs the work through Loops."),
        Element("providers", "Model providers", EXTERNAL,
                "Ollama, Mistral, OpenRouter and other configured routes."),
        Element("sandbox", "Execution sandbox", EXTERNAL,
                "Docker or a confined host process."),
        Element("sources", "Task and data sources", EXTERNAL,
                "Files, repositories, datasets, task systems, and benchmarks.",
                evidence_state=PARTIAL),
        Element("tools", "External tools and services", EXTERNAL,
                "Typed capabilities selected under explicit effect authority.",
                evidence_state=PARTIAL),
    ),
    relationships=(
        Relationship("operator", "engine", "gives a task and authority",
                     carries="task text, permissions, budget"),
        Relationship("engine", "providers", "asks",
                     carries="work packets, typed output contracts"),
        Relationship("engine", "sandbox", "runs generated code in",
                     carries="projects, commands, artifacts"),
        Relationship("engine", "sources", "reads from or writes to",
                     carries="authorized source refs and verified artifacts"),
        Relationship("engine", "tools", "invokes",
                     carries="typed requests, observations, effect records"),
        Relationship("engine", "operator", "returns",
                     carries="verified result, or a precise blocker"),
    ))

LEARNING_FABRIC = DiagramModel(
    key="learning-fabric", level=COMPONENT,
    title="What a run records, and what later runs read",
    note=("Default ladder advice stays shadow. An explicit offline binding "
          "can expose prior material, with mechanism-only evidence."),
    elements=(
        Element("practitioner", "Adaptive Practitioner", CONTAINER_KIND,
                "Runs the kernel passes and owns every semantic decision.",
                "core.adaptive_practitioner"),
        Element("stage", "Stage fingerprint", COMPONENT_KIND,
                "Names a semantic situation, motif, and shape. It does not "
                "persist exact occurrence identity.",
                "core.stage_fingerprint", evidence_state=PARTIAL),
        Element("decision", "Semantic decision", COMPONENT_KIND,
                "Who decided, from which alternatives, and why.",
                "core.semantic_decision"),
        Element("outcome", "Decision outcome", COMPONENT_KIND,
                "Provides an initial forward join. Complete stage "
                "contribution is not wired.",
                "core.decision_outcome", evidence_state=PARTIAL),
        Element("choice", "Choice contract", COMPONENT_KIND,
                "One typed shape for every decision put to a model.",
                "core.choice"),
        Element("template", "Template negotiation", COMPONENT_KIND,
                "Defines negotiable response shapes. Product calls still "
                "use fixed step schemas.",
                "core.template_negotiation", evidence_state=PARTIAL),
        Element("recovery", "Recovery", COMPONENT_KIND,
                "Reasoning chooses what to do after a failure.",
                "core.recovery"),
        Element("ladder", "Model ladder", COMPONENT_KIND,
                "Computes a shadow route order from coarse prior outcomes. "
                "It does not select a route.",
                "core.model_demand", evidence_state=SHADOW),
        Element("convergence", "Convergence measure", COMPONENT_KIND,
                "Default arms stay shadow; explicit bindings control offline "
                "packet exposure with injected-provider evidence only.",
                "core.convergence", evidence_state=SHADOW),
        Element("credit", "Outcome vector", COMPONENT_KIND,
                "Separates several signals from run outcome. Production "
                "stage attribution remains partial.",
                "core.outcome_vector", evidence_state=PARTIAL),
        Element("store", "Stage JSONL store", STORE,
                "Local sidecar index; selected exposure, decision, and action "
                "facts also enter Run History, but canonical rows are pending.",
                "core.stage_store", evidence_state=PARTIAL),
        Element("lifecycle", "Run stage lifecycle", COMPONENT_KIND,
                "Loads the sidecar and closes it at run exits. Durable "
                "campaign storage is not implemented.",
                "core.run_stages", evidence_state=PARTIAL),
        Element("history", "Run History", STORE,
                "Canonical append-only runtime evidence and event chain.",
                "core.run_history"),
    ),
    relationships=(
        Relationship("credit", "store", "is stored beside each stage",
                     carries="known signals, unknown signals, granularity"),
        Relationship("store", "ladder", "projects coarse evidence into",
                     carries="route, attempts, Boolean helped projection"),
        Relationship("practitioner", "stage", "names each step",
                     carries="responsibility, horizons, what is open"),
        Relationship("practitioner", "decision", "records every choice",
                     carries="owner, alternatives, reason"),
        Relationship("decision", "outcome", "is followed forward",
                     carries="admitted, executed, observed, verified"),
        Relationship("practitioner", "choice", "asks through",
                     carries="options, enforced bounds, novel proposals"),
        Relationship("choice", "template", "may negotiate the shape with",
                     carries="disposition, replacement, extensions"),
        Relationship("choice", "recovery", "carries the failure decision for",
                     carries="eligible routes, mechanical facts"),
        Relationship("stage", "convergence", "requests an occurrence assignment",
                     carries="experiment, signature, ephemeral occurrence, seed"),
        Relationship("lifecycle", "store", "loads and closes",
                     carries="prior stages in, closed stages out"),
        Relationship("stage", "store", "is recorded in",
                     carries="digest, motif, shape, route"),
        Relationship("ladder", "practitioner", "is recorded but not applied",
                     carries="shadow route order, or an honest refusal"),
        Relationship("outcome", "store", "adds the run-level result to",
                     carries="task outcome beside any local signals"),
        Relationship("practitioner", "history", "records governed work in",
                     carries="Loop events, decisions, effects, verification"),
    ))

SOLVER_CONTAINERS = DiagramModel(
    key="containers", level=CONTAINER,
    title="What a task passes through",
    note=("The middle level between the setting and the components. The "
          "state label distinguishes working paths from partial and shadow "
          "contracts."),
    elements=(
        Element("frontier", "Task and frontier", CONTAINER_KIND,
                "The task plus a post-run projection of what stayed open. "
                "A living frontier is not implemented.",
                "core.task_frontier", evidence_state=PARTIAL),
        Element("practitioner", "Practitioner runtime", CONTAINER_KIND,
                "Runs the task as Loops and owns what happens next.",
                "core.adaptive_practitioner"),
        Element("orientation", "Orientation", CONTAINER_KIND,
                "Reads the situation before committing to an approach.",
                "core.adaptive_practitioner_orientation"),
        Element("planning", "Planning", CONTAINER_KIND,
                "Turns an approach into bounded steps.",
                "core.adaptive_practitioner_planning"),
        Element("context", "Context compiler", CONTAINER_KIND,
                "Fits the chosen evidence into the window that exists.",
                "core.context_budget"),
        Element("interface", "Semantic interface", CONTAINER_KIND,
                "Defines negotiable response contracts but is not yet wired "
                "into product calls.",
                "core.template_negotiation", evidence_state=PARTIAL),
        Element("calls", "Model calls and recording", CONTAINER_KIND,
                "Asks providers, and writes down what was decided.",
                "core.adaptive_practitioner_records"),
        Element("allocation", "Model allocation", CONTAINER_KIND,
                "Computes a shadow ladder. Product solve keeps one "
                "run-scoped model configuration.",
                "core.model_demand", evidence_state=SHADOW),
        Element("capabilities", "Capability fabric", CONTAINER_KIND,
                "Tools and skills the run may reach for.",
                "core.capability_directory"),
        Element("harness", "External harnesses", CONTAINER_KIND,
                "Other coding agents driven as subordinate workers.",
                "core.external_harness"),
        Element("verification", "Verification", CONTAINER_KIND,
                "Decides whether the work actually satisfies the task.",
                "core.adaptive_practitioner_verification"),
        Element("recovery", "Recovery", CONTAINER_KIND,
                "Chooses what to do after a failure, by reasoning.",
                "core.adaptive_practitioner_recovery"),
        Element("stage_evidence", "Stage evidence sidecar", STORE,
                "Local observations beside selected facts in Run History.",
                "core.stage_store", evidence_state=PARTIAL),
        Element("history", "Run History", STORE,
                "Canonical ordered evidence for governed Loop work.",
                "core.run_history"),
    ),
    relationships=(
        Relationship("frontier", "practitioner", "hands the open work to",
                     carries="task, authority, what is unresolved"),
        Relationship("practitioner", "orientation", "starts by",
                     carries="the task as given, and the situation"),
        Relationship("orientation", "planning", "settles enough to",
                     carries="approach, knowns, what is still unknown"),
        Relationship("planning", "calls", "issues steps through",
                     carries="one bounded responsibility at a time"),
        Relationship("context", "calls", "supplies the evidence to",
                     carries="selected evidence, within the window"),
        Relationship("interface", "calls", "shapes the answer for",
                     carries="offered contract, and room to refuse it"),
        Relationship("allocation", "calls", "orders the routes for",
                     carries="a ladder, or a refusal to advise"),
        Relationship("calls", "capabilities", "may reach for",
                     carries="a tool, with its contract and effects"),
        Relationship("calls", "harness", "may delegate to",
                     carries="bounded work, returned as events"),
        Relationship("calls", "verification", "submits the result to",
                     carries="artifacts, claims, evidence"),
        Relationship("verification", "recovery", "escalates a failure to",
                     carries="what failed, and what survived it"),
        Relationship("recovery", "practitioner", "returns a plan to",
                     carries="the smallest change worth trying"),
        Relationship("calls", "stage_evidence", "records stage observations in",
                     carries="semantic signature, motif, shape, route"),
        Relationship("stage_evidence", "allocation", "supplies observations to",
                     carries="prior outcomes, or too few to advise on"),
        Relationship("practitioner", "history", "records governed work in",
                     carries="Loop events, effects, decisions, verification"),
        Relationship("verification", "frontier", "closes or reopens",
                     carries="what is now settled, what is still open"),
    ))

ATOMIC_LOOP_SEQUENCE = DiagramModel(
    key="atomic-loop-sequence", level=DYNAMIC,
    title="One governed semantic responsibility",
    note=("Current product sequence. Response negotiation and stage model "
          "allocation have contracts but do not yet control this path."),
    elements=(
        Element("request", "Typed responsibility", COMPONENT_KIND,
                "Goal, inputs, authority, budget, and completion condition.",
                "core.task_frontier", evidence_state=PARTIAL),
        Element("loop", "Owning Loop", CONTAINER_KIND,
                "The only executable graph vertex.",
                "loop.recursive_loop"),
        Element("context", "Context selection", COMPONENT_KIND,
                "Selects bounded task and intelligence material.",
                "core.practitioner_context"),
        Element("interface", "Response program", COMPONENT_KIND,
                "Negotiable contract exists but is not on the product path.",
                "core.template_negotiation", evidence_state=PARTIAL),
        Element("allocation", "Model allocation", COMPONENT_KIND,
                "A shadow ladder is recorded; the run route stays fixed.",
                "core.model_demand", evidence_state=SHADOW),
        Element("call", "Semantic model call", COMPONENT_KIND,
                "Provider-neutral call through the ModelGateway.",
                "core.model_gateway"),
        Element("candidate", "Candidate admission", COMPONENT_KIND,
                "Parses and validates an untrusted response.",
                "core.model_response_admission"),
        Element("action", "Authorized action", COMPONENT_KIND,
                "Executes a selected registered capability.",
                "core.adaptive_practitioner_capabilities"),
        Element("verify", "Verification", COMPONENT_KIND,
                "Checks task evidence and produces a verdict.",
                "core.adaptive_practitioner_verification"),
        Element("state", "Trusted state transition", COMPONENT_KIND,
                "Implemented for the semantic runtime, not yet for every "
                "adaptive Practitioner update.",
                "core.semantic_state", evidence_state=PARTIAL),
        Element("outcome", "Stage outcome", COMPONENT_KIND,
                "One selected-action stage has a local result signal; complete "
                "stage contribution is unavailable.",
                "core.outcome_vector", evidence_state=PARTIAL),
        Element("history", "Run History", STORE,
                "Preserves the governed event sequence.",
                "core.run_history"),
    ),
    relationships=(
        Relationship("request", "loop", "starts", carries="typed work"),
        Relationship("loop", "context", "requests", carries="context need"),
        Relationship("context", "interface", "supplies",
                     carries="selected references and task state"),
        Relationship("interface", "allocation", "describes",
                     carries="response and model demand"),
        Relationship("allocation", "call", "would select",
                     carries="eligible model portfolio; currently shadow"),
        Relationship("call", "candidate", "returns",
                     carries="untrusted model response"),
        Relationship("candidate", "action", "proposes",
                     carries="validated action request"),
        Relationship("action", "verify", "produces",
                     carries="observation, artifacts, execution records"),
        Relationship("verify", "state", "authorizes or refuses",
                     carries="verified proposed state change"),
        Relationship("state", "outcome", "reports",
                     carries="local and downstream outcome signals"),
        Relationship("outcome", "history", "records",
                     carries="identity, evidence, unknowns, cost"),
    ))

FINGERPRINT_LATTICE = DiagramModel(
    key="fingerprint-lattice", level=COMPONENT,
    title="Identity scales and their current linkage",
    note=("Several records exist, but one linked multi-scale fingerprint "
          "lattice is not implemented. Partial labels prevent the drawing "
          "from claiming otherwise."),
    elements=(
        Element("f8", "F8 Campaign", COMPONENT_KIND,
                "A bounded task population and evaluation run.",
                "code_nodes.campaign_runner", evidence_state=PARTIAL),
        Element("f7", "F7 Task", COMPONENT_KIND,
                "Structured task identity and compatibility facts.",
                "core.task_fingerprint"),
        Element("f6", "F6 Solution branch", COMPONENT_KIND,
                "Independent branch identity and outcome linkage are target "
                "behavior.", evidence_state=TARGET),
        Element("f5", "F5 Structural subgraph", COMPONENT_KIND,
                "Solution graphs exist; cross-run subgraph fingerprints do not.",
                "code_nodes.solution_graph", evidence_state=PARTIAL),
        Element("f4", "F4 Cognitive episode", COMPONENT_KIND,
                "Reviewed episode records exist outside the production stage "
                "lattice.", "memory.episodic.record", evidence_state=PARTIAL),
        Element("f3", "F3 State transition", COMPONENT_KIND,
                "Versioned semantic transitions exist on a narrower runtime "
                "path.", "core.semantic_state", evidence_state=PARTIAL),
        Element("f2", "F2 Loop activation occurrence", COMPONENT_KIND,
                "Product events link activation, semantic call, and attempts; "
                "canonical projection records are pending.",
                "loop.recursive_loop", evidence_state=PARTIAL),
        Element("f1", "F1 Logical semantic call", COMPONENT_KIND,
                "One coherent semantic invocation identity.",
                "core.semantic_runtime_records", evidence_state=PARTIAL),
        Element("f0", "F0 Physical provider attempt", COMPONENT_KIND,
                "Exact provider attempt and usage evidence.",
                "core.model_gateway"),
        Element("f9", "F9 Cross-run motif", COMPONENT_KIND,
                "Derived stage motif with no campaign outcome linkage.",
                "core.stage_fingerprint", evidence_state=PARTIAL),
    ),
    relationships=(
        Relationship("f8", "f7", "contains", carries="task references"),
        Relationship("f7", "f6", "may compare",
                     carries="branch identity and task objective"),
        Relationship("f6", "f5", "contains",
                     carries="subgraph identity and topology"),
        Relationship("f5", "f4", "contains",
                     carries="episode references"),
        Relationship("f4", "f3", "summarizes",
                     carries="ordered transition references"),
        Relationship("f3", "f2", "is produced by",
                     carries="exact Loop activation reference"),
        Relationship("f2", "f1", "owns",
                     carries="logical semantic call references"),
        Relationship("f1", "f0", "may require",
                     carries="one or more physical attempt references"),
        Relationship("f4", "f9", "may project to",
                     carries="cross-run motif candidate"),
    ))

STAGE_ASSISTANCE_TRIAL = DiagramModel(
    key="stage-assistance-trial", level=DYNAMIC,
    title="Candidate paired stage assistance path",
    note=("The evidence contracts and rebuildable projection are implemented "
          "as a partial foundation. The public offline solve path executes "
          "both arms with injected responses and hydrated advisory material. "
          "Its control manifest says mechanism-only; live benefit is unproven."),
    elements=(
        Element("history", "Canonical Run History", STORE,
                "Immutable source events for experiment records.",
                "core.run_history"),
        Element("projection", "Stage evidence projection", STORE,
                "Rebuilds canonical source rows, not current product histories.",
                "core.stage_evidence_projection", evidence_state=PARTIAL),
        Element("trial", "Control manifest and trial", COMPONENT_KIND,
                "The fixture shares one manifest with six blocking unknowns.",
                "core.stage_assistance_experiment", evidence_state=PARTIAL),
        Element("retrieval", "Prior candidate snapshot", COMPONENT_KIND,
                "Offline fixture injects typed candidates and digest-bound "
                "hydrated material; canonical Run History query is pending.",
                "core.stage_evidence_records", evidence_state=PARTIAL),
        Element("advisory", "Advisory assignment", COMPONENT_KIND,
                "Exposure manifest may name retrieved prior references.",
                "core.stage_assistance_experiment", evidence_state=PARTIAL),
        Element("fresh", "Fresh assignment", COMPONENT_KIND,
                "Exposure manifest requires zero prior references.",
                "core.stage_assistance_experiment", evidence_state=PARTIAL),
        Element("assisted_call", "Assisted model call", COMPONENT_KIND,
                "Public offline solve sends hydrated prior material through "
                "the prompt-sensitive injected provider adapter.",
                "core.model_gateway", evidence_state=PARTIAL),
        Element("fresh_call", "Fresh model call", COMPONENT_KIND,
                "Public offline solve sends no candidate or hydrated prior "
                "material through the same injected provider path.",
                "core.model_gateway", evidence_state=PARTIAL),
        Element("verify", "Action result verification", COMPONENT_KIND,
                "Exact occurrence refs link one selected action, execution, "
                "and same-Practitioner verifier; independence is pending.",
                "core.stage_action_lineage", evidence_state=PARTIAL),
        Element("outcome", "Linked trial outcomes", COMPONENT_KIND,
                "The contract can hold outcomes; the fixture emits none.",
                "core.stage_evidence_records", evidence_state=PARTIAL),
    ),
    relationships=(
        Relationship("history", "projection", "rebuilds",
                     carries="digest-bound stage experiment records"),
        Relationship("projection", "trial", "is intended to supply",
                     carries="scoped prior occurrence references"),
        Relationship("trial", "retrieval", "freezes",
                     carries="source-state digest and control unknowns"),
        Relationship("retrieval", "advisory", "may expose",
                     carries="exact prior candidate references"),
        Relationship("trial", "fresh", "also creates",
                     carries="an occurrence with zero prior references"),
        Relationship("advisory", "assisted_call", "feeds offline",
                     carries="hydrated material and explicit use contract"),
        Relationship("fresh", "fresh_call", "feeds offline",
                     carries="fresh packet from the same declared source state"),
        Relationship("assisted_call", "verify", "submits offline",
                     carries="assisted output and call records"),
        Relationship("fresh_call", "verify", "submits offline",
                     carries="fresh output and call records"),
        Relationship("verify", "outcome", "would produce canonical",
                     carries="metric, run validity, cost, latency, usage"),
        Relationship("outcome", "history", "must be recorded in",
                     carries="linked immutable outcome evidence"),
    ))

DEPLOYMENT_VIEW = DiagramModel(
    key="deployment", level=CONTAINER,
    title="Learning evidence deployment boundary",
    note=("Current runs and Run History are local. The SQLite stage evidence "
          "projection is a rebuildable index, not a shared authority. A "
          "multi-tenant learning service remains a target."),
    elements=(
        Element("solve", "Local product solve", CONTAINER_KIND,
                "One adaptive Practitioner run.",
                "core.adaptive_practitioner"),
        Element("history", "Local Run History", STORE,
                "Canonical event and artifact references.",
                "core.run_history"),
        Element("sidecar", "Stage JSONL sidecar", STORE,
                "Optional shared path with no campaign transaction contract.",
                "core.stage_store", evidence_state=PARTIAL),
        Element("projection", "SQLite stage projection", STORE,
                "File-backed WAL index rebuilt from Run History events.",
                "core.stage_evidence_projection", evidence_state=PARTIAL),
        Element("scheduler", "Reactive scheduler", CONTAINER_KIND,
                "Local durable activation scheduling and fencing.",
                "core.reactive_scheduler"),
        Element("providers", "Model gateway", CONTAINER_KIND,
                "Configured provider routes and exact physical attempts.",
                "core.model_gateway"),
        Element("tools", "Capability directory", CONTAINER_KIND,
                "Effect-free discovery before authorized invocation.",
                "core.capability_directory"),
        Element("shared", "Shared learning service", EXTERNAL,
                "Transactional multi-tenant ingestion, retention, and query.",
                evidence_state=TARGET),
    ),
    relationships=(
        Relationship("solve", "history", "writes",
                     carries="canonical Loop events and artifact refs"),
        Relationship("solve", "sidecar", "may write",
                     carries="shadow stage observations"),
        Relationship("history", "projection", "rebuilds",
                     carries="committed intact stage evidence events"),
        Relationship("scheduler", "solve", "may activate",
                     carries="leased finite Loop work"),
        Relationship("solve", "providers", "calls through",
                     carries="authorized semantic requests"),
        Relationship("solve", "tools", "discovers and invokes through",
                     carries="typed capability requests and effect records"),
        Relationship("history", "shared", "could publish to",
                     carries="privacy-scoped immutable evidence"),
        Relationship("shared", "projection", "could replace",
                     carries="shared query projection, never runtime authority"),
    ))

DIAGRAMS = (
    RUNTIME_CONTEXT, SOLVER_CONTAINERS, LEARNING_FABRIC,
    ATOMIC_LOOP_SEQUENCE, FINGERPRINT_LATTICE,
    STAGE_ASSISTANCE_TRIAL, DEPLOYMENT_VIEW)

_MERMAID_SHAPES = {
    PERSON: ("([", "])"), SYSTEM: ("[", "]"), EXTERNAL: ("[/", "/]"),
    CONTAINER_KIND: ("[", "]"), STORE: ("[(", ")]"),
    COMPONENT_KIND: ("(", ")"),
}


def render_mermaid(model: DiagramModel) -> str:
    """A Mermaid flowchart. One rendering, not the record."""
    lines = [f"%% {model.title}: {model.level} level",
             "%% Generated from the typed model; do not edit by hand.",
             "flowchart TD"]
    for item in model.elements:
        open_shape, close_shape = _MERMAID_SHAPES.get(
            item.kind, _MERMAID_SHAPES[COMPONENT_KIND])
        label = item.name
        if item.description:
            label += f"<br/><small>{item.description}</small>"
        label += f"<br/><small>State: {item.evidence_state}.</small>"
        lines.append(f"    {item.key}{open_shape}\"{label}\"{close_shape}")
    lines.append("")
    for edge in model.relationships:
        text = edge.label
        if edge.carries:
            text = f"{text}<br/><i>{edge.carries}</i>" if text else edge.carries
        lines.append(f"    {edge.source} -->|\"{text}\"| {edge.target}")
    if model.note:
        lines += ["", f"%% {model.note}"]
    return "\n".join(lines)


_C4_KINDS = {PERSON: "Person", SYSTEM: "System", EXTERNAL: "System_Ext",
             CONTAINER_KIND: "Container", STORE: "ContainerDb",
             COMPONENT_KIND: "Component"}


def render_c4_dsl(model: DiagramModel) -> str:
    """A Structurizr-flavoured DSL rendering. Also not the record."""
    lines = [f"# {model.title}", f"# level: {model.level}",
             "# Generated from the typed model; do not edit by hand.",
             "workspace {", "    model {"]
    for item in model.elements:
        kind = _C4_KINDS.get(item.kind, "Component")
        description = (f"[{item.evidence_state}] {item.description}"
                       if item.description else f"[{item.evidence_state}]")
        lines.append(f"        {item.key} = {kind.lower()} \"{item.name}\" "
                     f"\"{description}\"")
    lines.append("")
    for edge in model.relationships:
        label = edge.label or "uses"
        lines.append(f"        {edge.source} -> {edge.target} \"{label}\"")
    lines += ["    }", "}"]
    return "\n".join(lines)


#: Where the rendered document lives, relative to the repository root. The
#: file is a projection; this module is the record.
DOCUMENT_PATH = "docs/ARCHITECTURE-DIAGRAMS.md"

def render_document(models=DIAGRAMS) -> str:
    """The whole page, so the committed file cannot drift from the model.

    Written out rather than maintained: a diagram kept by hand beside a
    typed model is a second copy of the same list, and the copy is wrong
    from the first edit that forgets it.
    """
    lines = ["# Architecture diagrams", "", DIAGRAM_PREAMBLE, "",
             "## Loop classification", "", "```text",
             LOOP_CLASSIFICATION_TREE, "```", "",
             "## Loop role profiles", "", "```text",
             ROLE_PROFILE_TREE, "```", ""]
    for model in models:
        lines += [f"## {model.title}", "",
                  f"*{model.level} level.* {model.note}", "",
                  "```mermaid", render_mermaid(model), "```", ""]
    lines += ["## The same models as C4 DSL", "",
              "Rendered for a Structurizr-style tool.", ""]
    for model in models:
        lines += [f"### {model.title} (DSL)", "",
                  "```text", render_c4_dsl(model), "```", ""]
    return "\n".join(lines).rstrip("\n") + "\n"


def self_test() -> dict:
    """Offline checks. No provider is contacted."""
    from ..architecture_map import MODULE_MAP

    tests = []

    def check(name, ok, detail=""):
        tests.append({"test": name, "passed": bool(ok), "detail": detail})

    known = set()
    for package, modules in MODULE_MAP.items():
        for module in modules:
            known.add(f"{package}.{module}" if package else module)
            known.add(module)

    missing = []
    for model in DIAGRAMS:
        for module in model.modules:
            leaf = module.split(".")[-1]
            if module not in known and leaf not in known:
                missing.append(module)
    check("every element names a module that exists",
          not missing,
          f"named but absent: {missing}" if missing else
          "a renamed module breaks the diagram instead of it lying quietly")
    orphan = False
    try:
        DiagramModel(key="k", title="t", level=COMPONENT,
                     elements=(Element("a", "A"),),
                     relationships=(Relationship("a", "ghost"),))
    except ValueError:
        orphan = True
    check("an arrow to nothing is refused", orphan)
    repeated = False
    try:
        DiagramModel(key="k", title="t", level=COMPONENT,
                     elements=(Element("a", "A"), Element("a", "B")))
    except ValueError:
        repeated = True
    check("a repeated element key is refused", repeated)
    bad_level = False
    try:
        DiagramModel(key="k", title="t", level="birds-eye")
    except ValueError:
        bad_level = True
    check("an unknown level is refused", bad_level)

    bad_state = False
    try:
        Element("a", "A", evidence_state="claimed")
    except ValueError:
        bad_state = True
    check("an unknown evidence state is refused", bad_state)

    mermaid = render_mermaid(LEARNING_FABRIC)
    check("the mermaid rendering carries every element and edge",
          all(item.key in mermaid for item in LEARNING_FABRIC.elements)
          and mermaid.count("-->") == len(LEARNING_FABRIC.relationships)
          and mermaid.startswith("%%"))
    check("the store renders as a store, not as one more box",
          'store[("' in mermaid)

    dsl = render_c4_dsl(RUNTIME_CONTEXT)
    check("the C4 rendering distinguishes external systems",
          "system_ext" in dsl and "person" in dsl)

    check("edges say what travels along them, not merely that they exist",
          all(edge.carries for edge in LEARNING_FABRIC.relationships),
          "an unlabelled arrow says these are somehow related")

    check("the advice edge records that it is not applied",
          any("not applied" in edge.label
              for edge in LEARNING_FABRIC.relationships),
          "the drawing should not imply an authority the code does not give")

    round_trip = json.loads(json.dumps(LEARNING_FABRIC.to_dict()))
    check("the model survives serialisation as the record",
          round_trip["record_type"] == DIAGRAM_RECORD_TYPE
          and len(round_trip["elements"]) == len(LEARNING_FABRIC.elements)
          and {item["evidence_state"] for item in round_trip["elements"]}
          >= {IMPLEMENTED, PARTIAL, SHADOW})

    check("the container level exists between context and component",
          {model.level for model in DIAGRAMS}
          >= {CONTEXT, CONTAINER, COMPONENT},
          "skipping the middle level hides what a task passes through")

    check("dynamic sequence and paired experiment views are explicit",
          {model.key for model in DIAGRAMS}
          >= {"atomic-loop-sequence", "stage-assistance-trial"}
          and any(model.level == DYNAMIC for model in DIAGRAMS))
    check("target behavior is labelled rather than drawn as current",
          any(item.evidence_state == TARGET
              for model in DIAGRAMS for item in model.elements))
    check("stage evidence is not called exact identity or Run History",
          "exact identity" not in next(
              item.description for item in LEARNING_FABRIC.elements
              if item.key == "store")
          and next(item.module for item in SOLVER_CONTAINERS.elements
                   if item.key == "history") == "core.run_history")
    check("the paired fresh branch declares zero prior references",
          any(item.key == "fresh" and "zero prior" in item.description
              for item in STAGE_ASSISTANCE_TRIAL.elements))

    page = render_document()
    check("complete Loop trees precede specialized views",
          page.index("## Loop classification")
          < page.index(f"## {DIAGRAMS[0].title}")
          and all(value in LOOP_CLASSIFICATION_TREE for value in (
              "Starting", "Spawned by", "Queried by", "Retrieved by",
              "Connected from", "Practitioner", "Intelligence", "Solution")))
    check("the rendered page carries every model",
          all(model.title in page for model in DIAGRAMS))

    root = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__)))))
    committed = os.path.join(root, DOCUMENT_PATH)
    if os.path.isfile(committed):
        with open(committed, encoding="utf-8") as handle:
            check("the committed page matches the typed model",
                  handle.read() == page,
                  "regenerate with render_document(); a hand-kept copy "
                  "drifts from the model the first time one is forgotten")

    passed = sum(1 for item in tests if item["passed"])
    return {"record_type": "architecture_diagram_test/v1", "tests": tests,
            "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
