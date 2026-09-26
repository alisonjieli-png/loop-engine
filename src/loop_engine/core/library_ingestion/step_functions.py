"""Step function tags: which kinds of step a library item supports, as one served attribute.

The owner, September 26, 2026: "it would be helpful to tag some of these
skills by whether they support acting, reasoning, building, analysis,
verification, etc". A tag answers that question for one item, so a customer
or a harness can filter the library by the kind of step it is about to run.

```text
library_step_function_tagging (engine slot, one_of)
├── edge: tag(step_function_material/v1) -> step_function_tags/v1
├── step_function_rules: word and file-role rules, no model, no network
└── a text model engine may follow behind the same edge; the tags record
    which engine wrote them, so a rule tag is never mistaken for a judged one
```

The vocabulary is closed, because a filter needs stable words. A tag is
descriptive only: it grants nothing, and no code that decides access reads
it. An item whose text names no function gets no tag, which is the honest
answer, not a guess.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .record_rules import LibraryRecordError

MATERIAL_RECORD_TYPE = "step_function_material/v1"
TAGS_RECORD_TYPE = "step_function_tags/v1"
ATTRIBUTE_NAME = "step_functions"
#: The closed vocabulary, in the order tags of equal weight are listed.
STEP_FUNCTIONS = ("acting", "analysis", "building", "operating", "planning", "reasoning", "research",
                  "reviewing", "verification", "writing")
#: The attribute a release schema declares so the tags are searched, filtered and shown.
STEP_FUNCTIONS_ATTRIBUTE = {
    "name": ATTRIBUTE_NAME, "type": "keyword_list", "searchable": True, "filterable": True, "shown": True,
    "description": ("The kinds of step the item supports: acting, analysis, building, operating, planning, "
                    "reasoning, research, reviewing, verification or writing. Tagged by rules from the item's "
                    "own words and file roles, so a tag says what the item talks about, not that it was judged.")}
#: How much of the entry file the rules read.
TEXT_BOUND = 6000
NAME_BOUND = 256
PURPOSE_BOUND = 2048
#: A function is tagged at this score: one distinct word in the name or purpose, or two distinct
#: words in the body, or a file role that a harness runs.
MINIMUM_SCORE = 2
HEADLINE_WEIGHT = 2
BODY_CAP = 2
MAXIMUM_FUNCTIONS = 4
#: Package file roles a harness runs (catalogue_packages.EXECUTABLE_ROLES, restated here so this
#: module reads nothing from the serving side) and the package kinds that exist to be run.
EXECUTABLE_ROLES = ("skill_script", "hook", "executable_tool")
ROLE_FUNCTIONS = {"skill_script": "acting", "hook": "acting", "executable_tool": "acting"}
HARNESS_KIND_FUNCTIONS = {"hook": "acting", "protocol_server_configuration": "acting"}
_WORDS = {
    "acting": r"run|runs|running|execute|executes|executing|execution|command|commands|invoke|invokes|install|"
              r"installs|installation|apply|applies|automate|automates|automation|trigger|triggers|shell|script|"
              r"scripts|tool|tools|hook|hooks|cli",
    "analysis": r"analy[sz]e|analy[sz]es|analy[sz]ing|analysis|analytics|inspect|inspects|inspection|diagnose|"
                r"diagnoses|diagnosis|diagnostics|debug|debugging|profile|profiling|profiler|investigate|"
                r"investigation|metrics|measure|measures|measurement|compare|comparison|evaluate|evaluation|"
                r"benchmark|benchmarks|benchmarking|trace|tracing|root cause",
    "building": r"build|builds|building|implement|implements|implementation|scaffold|scaffolds|scaffolding|"
                r"generate|generates|generating|generator|create|creates|creating|compile|compiles|refactor|"
                r"refactors|refactoring|migrate|migration|migrations|bootstrap|develop|developing|development|"
                r"prototype|prototyping",
    "operating": r"deploy|deploys|deployment|deployments|monitor|monitoring|ci|cd|pipeline|pipelines|release|"
                 r"releases|releasing|docker|kubernetes|k8s|infrastructure|infra|ops|devops|incident|incidents|"
                 r"logging|observability|alert|alerts|uptime|rollback|terraform|helm|container|containers",
    "planning": r"plan|plans|planning|roadmap|milestone|milestones|breakdown|break down|task list|prioriti[sz]e|"
                r"prioriti[sz]ation|spec|specs|specification|prd|design doc|design document|estimate|estimates|"
                r"estimation|scope|scoping|backlog|sprint|sprints",
    "reasoning": r"reason|reasons|reasoning|think|thinking|decide|decides|decision|decisions|brainstorm|"
                 r"brainstorming|hypothesis|hypotheses|trade-?offs?|strategy|strategies|architecture|"
                 r"architectural|judge|judgement|judgment|weigh|weighs|alternatives|first principles|"
                 r"chain of thought",
    "research": r"research|researching|search|searches|searching|explore|explores|exploring|exploration|"
                r"discover|discovers|discovery|browse|browsing|lookup|look up|literature|survey|surveys|"
                r"find out|gather information|sources",
    "reviewing": r"review|reviews|reviewing|reviewer|critique|critiques|feedback|pull request|pull requests|"
                 r"code review|approve|approval|audit|audits|auditing",
    "verification": r"test|tests|testing|verify|verifies|verification|validate|validates|validation|check|checks|"
                    r"checking|lint|linting|linter|assert|asserts|assertion|qa|regression|coverage|correctness|"
                    r"proof|prove|proves",
    "writing": r"writing|writer|draft|drafts|drafting|document|documents|documenting|documentation|docs|readme|"
               r"blog|article|articles|prose|changelog|commit message|commit messages|summary|summari[sz]e|"
               r"summari[sz]es|translate|translation|rewrite|editing|report|reports|essay|email|emails|newsletter",
}
_PATTERNS = {function: re.compile(r"(?<![a-z0-9])(?:" + words + r")(?![a-z0-9])") for function, words in _WORDS.items()}
_SEPARATORS = re.compile(r"[_\-./]+")


def _text(value, name: str, bound: int) -> str:
    if not isinstance(value, str):
        raise LibraryRecordError("step_function_material_invalid", f"{name} is text")
    return value[:bound]


@dataclass(frozen=True)
class StepFunctionMaterial:
    """What the tagger reads about one item: its kinds, name, purpose, entry text and file roles."""

    kind: str
    harness_kind: str
    name: str
    purpose: str
    text: str
    file_roles: tuple = ()

    def __post_init__(self) -> None:
        for field in ("kind", "harness_kind"):
            value = getattr(self, field)
            if not isinstance(value, str) or len(value) > NAME_BOUND:
                raise LibraryRecordError("step_function_material_invalid", f"{field} is a bounded name")
        object.__setattr__(self, "name", _text(self.name, "name", NAME_BOUND))
        object.__setattr__(self, "purpose", _text(self.purpose, "purpose", PURPOSE_BOUND))
        object.__setattr__(self, "text", _text(self.text, "text", TEXT_BOUND))
        roles = tuple(self.file_roles)
        if any(not isinstance(role, str) for role in roles):
            raise LibraryRecordError("step_function_material_invalid", "file roles are names")
        object.__setattr__(self, "file_roles", roles)

    def to_dict(self) -> dict:
        return {"record_type": MATERIAL_RECORD_TYPE, "kind": self.kind, "harness_kind": self.harness_kind,
                "name": self.name, "purpose": self.purpose, "text": self.text, "file_roles": list(self.file_roles)}


@dataclass(frozen=True)
class StepFunctionTags:
    """The tags of one item, with the engine that wrote them and the words or roles that led to each."""

    functions: tuple
    engine_id: str
    engine_version: str
    evidence: tuple = ()

    def __post_init__(self) -> None:
        functions = tuple(self.functions)
        if (len(functions) > MAXIMUM_FUNCTIONS or len(set(functions)) != len(functions)
                or any(function not in STEP_FUNCTIONS for function in functions)):
            raise LibraryRecordError("step_function_tags_invalid",
                                     f"tags are at most {MAXIMUM_FUNCTIONS} distinct words of the closed vocabulary")
        if not self.engine_id or not self.engine_version:
            raise LibraryRecordError("step_function_tags_invalid", "tags name the engine that wrote them")
        object.__setattr__(self, "functions", functions)
        object.__setattr__(self, "evidence", tuple((str(function), str(basis)) for function, basis in self.evidence))

    def to_dict(self) -> dict:
        return {"record_type": TAGS_RECORD_TYPE, "functions": list(self.functions),
                "engine": {"engine_id": self.engine_id, "engine_version": self.engine_version},
                "evidence": [{"function": function, "basis": basis} for function, basis in self.evidence]}

    def attribute_values(self) -> dict:
        """The attribute values a release line carries; empty when the item has no tag."""
        return {ATTRIBUTE_NAME: list(self.functions)} if self.functions else {}


class StepFunctionTagger:
    """The edge every tagging engine implements: engine_id, engine_version, engine_kind and tag()."""

    engine_id = ""
    engine_version = ""
    engine_kind = "function_tagger"

    def tag(self, material: StepFunctionMaterial) -> StepFunctionTags:
        raise NotImplementedError


def _headline(material: StepFunctionMaterial) -> str:
    return (_SEPARATORS.sub(" ", material.name) + "\n" + material.purpose).lower()


class RulesStepFunctionTagger(StepFunctionTagger):
    """Engine step_function_rules: distinct vocabulary words in the name, purpose and entry text, and file roles.

    A word in the name or purpose weighs two, a distinct word in the body one
    (at most two count), and a file role a harness runs weighs two for
    acting. A function is tagged at a score of two; the four highest are
    kept, in vocabulary order among equals. The evidence names each word or
    role, so a sampled tag can be checked against the item by hand.
    """

    engine_id = "step_function_rules"
    engine_version = "1.0.0"
    engine_kind = "function_tagger"
    effects = ("pure",)
    third_party = "none"

    @classmethod
    def availability(cls, settings: dict):
        return True, "always_available"

    @classmethod
    def from_settings(cls, settings: dict, resources: dict):
        """Construct from declared settings and the run's resources; nothing starts here."""
        return cls()

    def describe(self) -> dict:
        return {"engine_id": self.engine_id, "engine_version": self.engine_version,
                "minimum_score": MINIMUM_SCORE, "maximum_functions": MAXIMUM_FUNCTIONS, "text_bound": TEXT_BOUND}

    def scores(self, material: StepFunctionMaterial) -> dict:
        """The score and the evidence of every function, before the threshold is applied."""
        headline, body = _headline(material), material.text.lower()
        scored = {}
        for function in STEP_FUNCTIONS:
            pattern = _PATTERNS[function]
            head_words = sorted(set(pattern.findall(headline)))
            body_words = sorted(set(pattern.findall(body)) - set(head_words))
            score = HEADLINE_WEIGHT * len(head_words) + min(len(body_words), BODY_CAP)
            evidence = [f"name or purpose: {word}" for word in head_words] + [f"text: {word}" for word in body_words[:BODY_CAP]]
            scored[function] = [score, evidence]
        for role in sorted(set(material.file_roles)):
            function = ROLE_FUNCTIONS.get(role)
            if function:
                scored[function][0] += HEADLINE_WEIGHT
                scored[function][1].append(f"file role: {role}")
        function = HARNESS_KIND_FUNCTIONS.get(material.harness_kind)
        if function:
            scored[function][0] += HEADLINE_WEIGHT
            scored[function][1].append(f"harness kind: {material.harness_kind}")
        return {function: (score, tuple(evidence)) for function, (score, evidence) in scored.items()}

    def tag(self, material: StepFunctionMaterial) -> StepFunctionTags:
        if not isinstance(material, StepFunctionMaterial):
            raise LibraryRecordError("step_function_material_invalid", "the tagger reads step_function_material/v1")
        scored = self.scores(material)
        order = {function: index for index, function in enumerate(STEP_FUNCTIONS)}
        chosen = sorted((function for function, (score, _evidence) in scored.items() if score >= MINIMUM_SCORE),
                        key=lambda function: (-scored[function][0], order[function]))[:MAXIMUM_FUNCTIONS]
        evidence = tuple((function, basis) for function in chosen for basis in scored[function][1])
        return StepFunctionTags(tuple(chosen), self.engine_id, self.engine_version, evidence)


def entry_text(files, *, primary_roles=("skill_definition", "instruction_file", "subagent_definition", "command",
                                         "hook", "protocol_server_configuration", "plugin_manifest",
                                         "configuration")) -> str:
    """The text the rules read from a package: its primary file, else its first Markdown file, else nothing.

    ``files`` is a sequence of (path, role, media type, text or None), in package order."""
    rows = [row for row in files if row[3] is not None]
    for wanted in primary_roles:
        for path, role, _media, text in rows:
            if role == wanted and not path.upper().startswith(("LICENSE", "ATTRIBUTION")):
                return text[:TEXT_BOUND]
    for path, _role, media, text in rows:
        if media == "text/markdown" and not path.upper().startswith(("LICENSE", "ATTRIBUTION")):
            return text[:TEXT_BOUND]
    return ""
