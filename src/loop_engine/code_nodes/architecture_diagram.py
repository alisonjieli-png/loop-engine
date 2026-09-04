"""The architecture as a typed model, rendered into diagrams.

A diagram drawn by hand starts accurate and drifts, because nothing makes it
wrong when the code moves. The way to stop that is to make the picture a
projection of something the code can contradict: every element here names a
real module, and a self-test fails if any of them stops existing. Rename a
module and the diagram breaks loudly instead of lying quietly.

The typed model is the record. C4 and Mermaid are two renderings of it, and
neither is the source of truth — the distinction matters because a diagram
language can express things the system does not do, and once the picture is
authoritative those inventions become requirements nobody agreed to.

C4's levels map onto this repository as:

    Context     the operator, the providers, and the outside services a run
                actually reaches
    Container   the runtime pieces: the Loop runtime, the Practitioner, the
                model gateway, the stores
    Component   the inside of one container — currently the learning fabric,
                because it is the part that is hard to hold in the head

Owns:
    - Element, Relationship: the typed model.
    - LEARNING_FABRIC, RUNTIME_CONTEXT: the models this repository has.
    - render_mermaid(), render_c4_dsl(): two renderings, neither canonical.

Does not own: the architecture itself (architecture_map, architecture.yaml),
or any claim that the drawing is complete.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

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

    def __post_init__(self):
        if not self.key.strip() or not self.name.strip():
            raise ValueError("a diagram element needs a key and a name")


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
                          "module": item.module} for item in self.elements],
            "relationships": [{"source": item.source, "target": item.target,
                               "label": item.label, "carries": item.carries}
                              for item in self.relationships],
        }


# --------------------------------------------------------------------------
# The models this repository actually has.
# --------------------------------------------------------------------------

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
        Element("kaggle", "Kaggle", EXTERNAL,
                "Competition data in, submissions out and graded."),
    ),
    relationships=(
        Relationship("operator", "engine", "gives a task and authority",
                     carries="task text, permissions, budget"),
        Relationship("engine", "providers", "asks",
                     carries="work packets, typed output contracts"),
        Relationship("engine", "sandbox", "runs generated code in",
                     carries="projects, commands, artifacts"),
        Relationship("engine", "kaggle", "reads and submits",
                     carries="datasets, submission files"),
        Relationship("engine", "operator", "returns",
                     carries="verified result, or a precise blocker"),
    ))


LEARNING_FABRIC = DiagramModel(
    key="learning-fabric", level=COMPONENT,
    title="What a run records, and what later runs read",
    note=("The loop that makes the engine self-observing. Advice flows out "
          "of the store and is recorded rather than obeyed."),
    elements=(
        Element("practitioner", "Adaptive Practitioner", CONTAINER_KIND,
                "Runs the kernel passes and owns every semantic decision.",
                "core.adaptive_practitioner"),
        Element("stage", "Stage fingerprint", COMPONENT_KIND,
                "Names one cognitive situation; its motif crosses domains.",
                "core.stage_fingerprint"),
        Element("decision", "Semantic decision", COMPONENT_KIND,
                "Who decided, from which alternatives, and why.",
                "core.semantic_decision"),
        Element("outcome", "Decision outcome", COMPONENT_KIND,
                "Joins a decision forward to whether it helped.",
                "core.decision_outcome"),
        Element("choice", "Choice contract", COMPONENT_KIND,
                "One typed shape for every decision put to a model.",
                "core.choice"),
        Element("template", "Template negotiation", COMPONENT_KIND,
                "The response shape is offered, and may be refused.",
                "core.template_negotiation"),
        Element("recovery", "Recovery", COMPONENT_KIND,
                "Reasoning chooses what to do after a failure.",
                "core.recovery"),
        Element("ladder", "Model ladder", COMPONENT_KIND,
                "Which route to try first, fitted to what worked.",
                "core.model_demand"),
        Element("convergence", "Convergence measure", COMPONENT_KIND,
                "Splits an arm off so agreement can be told from suggestion.",
                "core.convergence"),
        Element("store", "Stage store", STORE,
                "Append-only; indexed by exact identity, motif, and shape.",
                "core.stage_store"),
        Element("lifecycle", "Run stage lifecycle", COMPONENT_KIND,
                "Loads the store at the start, closes it at every exit.",
                "core.run_stages"),
    ),
    relationships=(
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
        Relationship("stage", "convergence", "assigns an arm from its identity",
                     carries="offered or control, before anything is shown"),
        Relationship("lifecycle", "store", "loads and closes",
                     carries="prior stages in, closed stages out"),
        Relationship("stage", "store", "is recorded in",
                     carries="digest, motif, shape, route"),
        Relationship("store", "ladder", "supplies prior shapes to",
                     carries="routes tried and whether they helped"),
        Relationship("ladder", "practitioner", "advises, and is not obeyed",
                     carries="an order to try, or an honest refusal"),
        Relationship("outcome", "store", "closes stages with the run's result",
                     carries="helped, hurt, or still unknown"),
    ))


DIAGRAMS = (RUNTIME_CONTEXT, LEARNING_FABRIC)

_MERMAID_SHAPES = {
    PERSON: ("([", "])"), SYSTEM: ("[", "]"), EXTERNAL: ("[/", "/]"),
    CONTAINER_KIND: ("[", "]"), STORE: ("[(", ")]"),
    COMPONENT_KIND: ("(", ")"),
}


def render_mermaid(model: DiagramModel) -> str:
    """A Mermaid flowchart. One rendering, not the record."""
    lines = [f"%% {model.title} — {model.level} level",
             "%% Generated from the typed model; do not edit by hand.",
             "flowchart TD"]
    for item in model.elements:
        open_shape, close_shape = _MERMAID_SHAPES.get(
            item.kind, _MERMAID_SHAPES[COMPONENT_KIND])
        label = item.name
        if item.description:
            label += f"<br/><small>{item.description}</small>"
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
        lines.append(f"        {item.key} = {kind.lower()} \"{item.name}\" "
                     f"\"{item.description}\"")
    lines.append("")
    for edge in model.relationships:
        label = edge.label or "uses"
        lines.append(f"        {edge.source} -> {edge.target} \"{label}\"")
    lines += ["    }", "}"]
    return "\n".join(lines)


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

    check("the advice edge records that it is not obeyed",
          any("not obeyed" in edge.label
              for edge in LEARNING_FABRIC.relationships),
          "the drawing should not imply an authority the code does not give")

    round_trip = json.loads(json.dumps(LEARNING_FABRIC.to_dict()))
    check("the model survives serialisation as the record",
          round_trip["record_type"] == DIAGRAM_RECORD_TYPE
          and len(round_trip["elements"]) == len(LEARNING_FABRIC.elements))

    passed = sum(1 for item in tests if item["passed"])
    return {"record_type": "architecture_diagram_test/v1", "tests": tests,
            "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
