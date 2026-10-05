"""An independent checker for derivation traces: each step is re-derived by pattern alone.

```text
check_trace(asserted, steps)
├── for each step, in order
│   ├── the rule is one of the seventeen this checker knows (its own table, written here)
│   ├── the premises unify with the rule's body in its premise order, under one binding
│   ├── the conclusion is one of the rule's heads under that binding, and can be written as RDF
│   └── every premise is asserted or the conclusion of an earlier step
└── the first step that fails is named with its index, its rule and the reason
```

It shares no code with any engine: it imports nothing from this package and
only the standard library, and it does no search, so a fault in an engine's
rule table or join is not a fault here too. The rule table is the contract both
read: W3C RDFS and OWL 2 RL names, premises in the order the Open Ontologies
Lean checker (``lean/OOCert/Rules.lean``, release v2.0.1) also reads, so a trace
written here can be handed to that checker as ``asserted.tsv`` and
``derivations.tsv``, and a certificate it accepts can be read back and checked
here.
"""
from __future__ import annotations

from dataclasses import dataclass

_R = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
_S = "http://www.w3.org/2000/01/rdf-schema#"
_O = "http://www.w3.org/2002/07/owl#"
TYPE, SC, SP = f"<{_R}type>", f"<{_S}subClassOf>", f"<{_S}subPropertyOf>"
DOM, RNG = f"<{_S}domain>", f"<{_S}range>"
TRANS, SYMM, INV, SAME = f"<{_O}TransitiveProperty>", f"<{_O}SymmetricProperty>", f"<{_O}inverseOf>", f"<{_O}sameAs>"
EQC, EQP = f"<{_O}equivalentClass>", f"<{_O}equivalentProperty>"

#: rule: (body in premise order, the heads it may conclude). Variables are single letters after "$".
CHECKER_RULES = {
    "rdfs2": ((("$s", "$p", "$o"), ("$p", DOM, "$c")), (("$s", TYPE, "$c"),)),
    "rdfs3": ((("$s", "$p", "$o"), ("$p", RNG, "$c")), (("$o", TYPE, "$c"),)),
    "rdfs5": ((("$a", SP, "$b"), ("$b", SP, "$c")), (("$a", SP, "$c"),)),
    "rdfs7": ((("$s", "$p", "$o"), ("$p", SP, "$q")), (("$s", "$q", "$o"),)),
    "rdfs9": ((("$x", TYPE, "$a"), ("$a", SC, "$b")), (("$x", TYPE, "$b"),)),
    "rdfs11": ((("$a", SC, "$b"), ("$b", SC, "$c")), (("$a", SC, "$c"),)),
    "prp-trp": ((("$p", TYPE, TRANS), ("$x", "$p", "$y"), ("$y", "$p", "$z")), (("$x", "$p", "$z"),)),
    "prp-symp": ((("$p", TYPE, SYMM), ("$x", "$p", "$y")), (("$y", "$p", "$x"),)),
    "prp-inv1": ((("$p", INV, "$q"), ("$x", "$p", "$y")), (("$y", "$q", "$x"),)),
    "prp-inv2": ((("$p", INV, "$q"), ("$x", "$q", "$y")), (("$y", "$p", "$x"),)),
    "eq-sym": ((("$a", SAME, "$b"),), (("$b", SAME, "$a"),)),
    "scm-eqc1": ((("$a", EQC, "$b"),), (("$a", SC, "$b"), ("$b", SC, "$a"))),
    "scm-eqp1": ((("$a", EQP, "$b"),), (("$a", SP, "$b"), ("$b", SP, "$a"))),
    "scm-dom1": ((("$p", DOM, "$c"), ("$c", SC, "$d")), (("$p", DOM, "$d"),)),
    "scm-dom2": ((("$q", DOM, "$c"), ("$p", SP, "$q")), (("$p", DOM, "$c"),)),
    "scm-rng1": ((("$p", RNG, "$c"), ("$c", SC, "$d")), (("$p", RNG, "$d"),)),
    "scm-rng2": ((("$q", RNG, "$c"), ("$p", SP, "$q")), (("$p", RNG, "$c"),)),
}
#: The W3C OWL 2 RL names of the six RDFS rules, accepted as the same rule.
ALIASES = {"prp-dom": "rdfs2", "prp-rng": "rdfs3", "scm-spo": "rdfs5", "prp-spo1": "rdfs7",
           "cax-sco": "rdfs9", "scm-sco": "rdfs11"}


@dataclass(frozen=True)
class TraceVerdict:
    """The checker's answer: ok, or the first rejected step with its rule and reason."""

    ok: bool
    steps: int
    first_rejected: "int | None" = None
    rule: str = ""
    reason: str = ""

    def to_dict(self) -> dict:
        return {"ok": self.ok, "steps": self.steps, "first_rejected": self.first_rejected, "rule": self.rule,
                "reason": self.reason}


def _term(value) -> bool:
    return type(value) is str and bool(value) and value[0] in '<_"' and "\t" not in value and "\n" not in value


def _triple(value) -> "tuple | None":
    if isinstance(value, (list, tuple)) and len(value) == 3 and all(_term(item) for item in value):
        return tuple(value)
    return None


def _match(pattern, triple, binding) -> "dict | None":
    for slot, value in zip(pattern, triple):
        if slot.startswith("$"):
            if binding.setdefault(slot, value) != value:
                return None
        elif slot != value:
            return None
    return binding


def check_step(rule: str, conclusion, premises) -> str:
    """The reason a single step does not hold, or the empty text when it does."""
    name = ALIASES.get(rule, rule)
    if name not in CHECKER_RULES:
        return f"rule {rule!r} is not in this checker's table"
    body, heads = CHECKER_RULES[name]
    conclusion = _triple(conclusion)
    if conclusion is None:
        return "the conclusion is not three N-Triples terms"
    if conclusion[0].startswith('"') or not conclusion[1].startswith("<"):
        return "the conclusion cannot be written as RDF (a literal subject or a non-IRI predicate)"
    if not isinstance(premises, (list, tuple)) or len(premises) != len(body):
        return f"rule {name} takes {len(body)} premises"
    binding: dict = {}
    for index, (pattern, premise) in enumerate(zip(body, premises)):
        premise = _triple(premise)
        if premise is None or _match(pattern, premise, binding) is None:
            return f"premise {index} does not have the shape rule {name} requires"
    for head in heads:
        if tuple(binding.get(slot, slot) for slot in head) == conclusion:
            return ""
    return f"rule {name} does not conclude this triple from these premises"


def check_trace(asserted, steps, *, rule_table=None) -> TraceVerdict:
    """Check every step in order against the asserted triples and the earlier conclusions."""
    known = {tuple(item) for item in asserted}
    allowed = None if rule_table is None else {ALIASES.get(name, name) for name in rule_table}
    if not isinstance(steps, (list, tuple)):
        return TraceVerdict(False, 0, 0, "", "steps is a list")
    for index, step in enumerate(steps):
        if not isinstance(step, dict) or set(step) != {"rule", "conclusion", "premises"}:
            return TraceVerdict(False, len(steps), index, "", "a step is exactly rule, conclusion and premises")
        rule = step["rule"]
        if type(rule) is not str:
            return TraceVerdict(False, len(steps), index, "", "a rule is named by text")
        if allowed is not None and ALIASES.get(rule, rule) not in allowed:
            return TraceVerdict(False, len(steps), index, rule, "the rule is outside the declared rule table")
        reason = check_step(rule, step["conclusion"], step["premises"])
        if reason:
            return TraceVerdict(False, len(steps), index, rule, reason)
        for position, premise in enumerate(step["premises"]):
            if tuple(premise) not in known:
                return TraceVerdict(False, len(steps), index, rule,
                                    f"premise {position} is neither asserted nor concluded by an earlier step")
        known.add(tuple(step["conclusion"]))
    return TraceVerdict(True, len(steps))


def write_certificate(asserted, steps) -> tuple:
    """(asserted.tsv, derivations.tsv) in the two-file format the Open Ontologies checkers read."""
    asserted_text = "".join("\t".join(triple) + "\n" for triple in sorted(tuple(item) for item in asserted))
    lines = []
    for step in steps:
        fields = [step["rule"], *step["conclusion"]]
        for premise in step["premises"]:
            fields += list(premise)
        lines.append("\t".join(fields) + "\n")
    return asserted_text, "".join(lines)


def read_certificate(asserted_text: str, derivations_text: str) -> tuple:
    """(asserted triples, steps) read back from the two-file format; a malformed line is refused."""
    asserted = []
    for number, line in enumerate(asserted_text.splitlines(), 1):
        fields = line.split("\t")
        if not line:
            continue
        if len(fields) != 3 or not all(_term(field) for field in fields):
            raise ValueError(f"asserted.tsv line {number} is not three terms")
        asserted.append(tuple(fields))
    steps = []
    for number, line in enumerate(derivations_text.splitlines(), 1):
        if not line:
            continue
        fields = line.split("\t")
        if len(fields) < 7 or (len(fields) - 4) % 3 or not all(_term(field) for field in fields[1:]):
            raise ValueError(f"derivations.tsv line {number} is not a rule, a conclusion and whole premises")
        premises = [list(fields[index:index + 3]) for index in range(4, len(fields), 3)]
        steps.append({"rule": fields[0], "conclusion": list(fields[1:4]), "premises": premises})
    return asserted, steps
