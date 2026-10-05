"""The Baltor-native engine: RDFS and OWL 2 RL rule closure in the Python standard library.

```text
NativeRuleEngine (engine kind rule_closure_engine, engine baltor_native_rules)
├── the rule table of each profile (contract.RULE_TABLES), as body and head patterns with the premises
│   in the order the trace checker reads
├── semi-naive forward chaining: each round joins only instantiations that use a triple derived in the
│   round before, so every new instantiation is found once per round and nothing is joined twice
├── one derivation per derived triple: of every instantiation a round finds for it, the least by rule
│   order and premises, so the derivation and every trace built from it do not depend on hash order
└── a conclusion no RDF serialiser can write (a literal subject, a non-IRI predicate) is never emitted
    and never used as a premise, which is the rule Open Ontologies follows too
```

It runs in process, reads no file, starts no process and uses no network. The
closure bound of the request is enforced while the closure grows.
"""
from __future__ import annotations

from collections import defaultdict
from types import MappingProxyType

from .contract import RULE_TABLES, EngineDeclaration, EngineFailure, EngineOutcome, PlanningInput
from .rdf_terms import OWL, RDF, RDFS, writable

_TYPE, _SUBCLASS, _SUBPROPERTY = f"<{RDF}type>", f"<{RDFS}subClassOf>", f"<{RDFS}subPropertyOf>"
_DOMAIN, _RANGE = f"<{RDFS}domain>", f"<{RDFS}range>"
_TRANSITIVE, _SYMMETRIC = f"<{OWL}TransitiveProperty>", f"<{OWL}SymmetricProperty>"
_INVERSE, _SAME_AS = f"<{OWL}inverseOf>", f"<{OWL}sameAs>"
_EQUIVALENT_CLASS, _EQUIVALENT_PROPERTY = f"<{OWL}equivalentClass>", f"<{OWL}equivalentProperty>"

#: name: (body patterns in premise order, head patterns). A term starting with "?" is a variable.
_RULE_PATTERNS = MappingProxyType({
    "rdfs2": ((("?s", "?p", "?o"), ("?p", _DOMAIN, "?c")), (("?s", _TYPE, "?c"),)),
    "rdfs3": ((("?s", "?p", "?o"), ("?p", _RANGE, "?c")), (("?o", _TYPE, "?c"),)),
    "rdfs5": ((("?a", _SUBPROPERTY, "?b"), ("?b", _SUBPROPERTY, "?c")), (("?a", _SUBPROPERTY, "?c"),)),
    "rdfs7": ((("?s", "?p", "?o"), ("?p", _SUBPROPERTY, "?q")), (("?s", "?q", "?o"),)),
    "rdfs9": ((("?x", _TYPE, "?a"), ("?a", _SUBCLASS, "?b")), (("?x", _TYPE, "?b"),)),
    "rdfs11": ((("?a", _SUBCLASS, "?b"), ("?b", _SUBCLASS, "?c")), (("?a", _SUBCLASS, "?c"),)),
    "prp-trp": ((("?p", _TYPE, _TRANSITIVE), ("?x", "?p", "?y"), ("?y", "?p", "?z")), (("?x", "?p", "?z"),)),
    "prp-symp": ((("?p", _TYPE, _SYMMETRIC), ("?x", "?p", "?y")), (("?y", "?p", "?x"),)),
    "prp-inv1": ((("?p", _INVERSE, "?q"), ("?x", "?p", "?y")), (("?y", "?q", "?x"),)),
    "prp-inv2": ((("?p", _INVERSE, "?q"), ("?x", "?q", "?y")), (("?y", "?p", "?x"),)),
    "eq-sym": ((("?a", _SAME_AS, "?b"),), (("?b", _SAME_AS, "?a"),)),
    "scm-eqc1": ((("?a", _EQUIVALENT_CLASS, "?b"),), (("?a", _SUBCLASS, "?b"), ("?b", _SUBCLASS, "?a"))),
    "scm-eqp1": ((("?a", _EQUIVALENT_PROPERTY, "?b"),),
                 (("?a", _SUBPROPERTY, "?b"), ("?b", _SUBPROPERTY, "?a"))),
    "scm-dom1": ((("?p", _DOMAIN, "?c1"), ("?c1", _SUBCLASS, "?c2")), (("?p", _DOMAIN, "?c2"),)),
    "scm-dom2": ((("?p2", _DOMAIN, "?c"), ("?p1", _SUBPROPERTY, "?p2")), (("?p1", _DOMAIN, "?c"),)),
    "scm-rng1": ((("?p", _RANGE, "?c1"), ("?c1", _SUBCLASS, "?c2")), (("?p", _RANGE, "?c2"),)),
    "scm-rng2": ((("?p2", _RANGE, "?c"), ("?p1", _SUBPROPERTY, "?p2")), (("?p1", _RANGE, "?c"),)),
})


def _variable(term: str) -> bool:
    return term.startswith("?")


class _Graph:
    """The growing closure with the indexes the joins read."""

    def __init__(self, triples):
        self.triples = set()
        self.by_p = defaultdict(set)
        self.by_ps = defaultdict(set)
        self.by_po = defaultdict(set)
        self.by_s = defaultdict(set)
        self.by_o = defaultdict(set)
        for triple in triples:
            self.add(triple)

    def add(self, triple) -> None:
        if triple in self.triples:
            return
        subject, predicate, obj = triple
        self.triples.add(triple)
        self.by_p[predicate].add(triple)
        self.by_ps[(predicate, subject)].add(triple)
        self.by_po[(predicate, obj)].add(triple)
        self.by_s[subject].add(triple)
        self.by_o[obj].add(triple)

    def candidates(self, pattern, binding):
        """The triples that can match a pattern under a binding, from the narrowest index."""
        subject, predicate, obj = (binding.get(term, term) if _variable(term) else term for term in pattern)
        bound_s, bound_p, bound_o = (not _variable(term) for term in (subject, predicate, obj))
        if bound_p and bound_s:
            return self.by_ps.get((predicate, subject), ())
        if bound_p and bound_o:
            return self.by_po.get((predicate, obj), ())
        if bound_p:
            return self.by_p.get(predicate, ())
        if bound_s:
            return self.by_s.get(subject, ())
        if bound_o:
            return self.by_o.get(obj, ())
        return self.triples


def _unify(pattern, triple, binding):
    """The binding extended so the pattern equals the triple, or None."""
    extended = dict(binding)
    for term, value in zip(pattern, triple):
        if _variable(term):
            if extended.setdefault(term, value) != value:
                return None
        elif term != value:
            return None
    return extended


def _instantiate(pattern, binding) -> tuple:
    return tuple(binding[term] if _variable(term) else term for term in pattern)


def _joins(body, position, seed, binding, graph):
    """Every (binding, premises) whose premise at ``position`` is ``seed``, the rest from the graph."""
    premises = [None] * len(body)
    premises[position] = seed
    order = [index for index in range(len(body)) if index != position]

    def extend(step, current):
        if step == len(order):
            yield current, tuple(premises)
            return
        index = order[step]
        for triple in list(graph.candidates(body[index], current)):
            matched = _unify(body[index], triple, current)
            if matched is not None:
                premises[index] = triple
                yield from extend(step + 1, matched)
        premises[index] = None

    yield from extend(0, binding)


def closure(asserted, profile: str, maximum: int):
    """(closure, derivations) of ``asserted`` under the profile's table, or EngineFailure past ``maximum``."""
    if profile not in RULE_TABLES:
        raise EngineFailure("capability_requirement_unsatisfied", f"profile {profile!r} has no rule table here")
    rules = [(rank, name, *_RULE_PATTERNS[name]) for rank, name in enumerate(RULE_TABLES[profile])]
    graph = _Graph(asserted)
    if len(graph.triples) > maximum:
        raise EngineFailure("limit_exceeded", f"the asserted graph already holds more than {maximum} triples")
    derivations, delta = {}, sorted(graph.triples)
    while delta:
        found = {}
        for rank, name, body, heads in rules:
            for position, pattern in enumerate(body):
                for seed in delta:
                    start = _unify(pattern, seed, {})
                    if start is None:
                        continue
                    for binding, premises in _joins(body, position, seed, start, graph):
                        for head in heads:
                            conclusion = _instantiate(head, binding)
                            if conclusion in graph.triples or not writable(conclusion):
                                continue
                            candidate = (rank, premises, name)
                            if conclusion not in found or candidate < found[conclusion]:
                                found[conclusion] = candidate
        if len(graph.triples) + len(found) > maximum:
            raise EngineFailure("limit_exceeded", f"the closure grows past {maximum} triples")
        for conclusion, (_rank, premises, name) in found.items():
            graph.add(conclusion)
            derivations[conclusion] = (name, premises)
        delta = sorted(found)
    return frozenset(graph.triples), derivations


class NativeRuleEngine:
    """The Baltor-native engine of the ontology_change_planning slot."""

    def __init__(self, declaration: EngineDeclaration, settings=None):
        self.declaration = declaration
        self.settings = dict(settings or {})

    def availability(self) -> tuple:
        return True, "the Python standard library; nothing to install"

    def plan(self, planning_input: PlanningInput) -> EngineOutcome:
        base_closure, base_derivations = closure(planning_input.base, planning_input.profile,
                                                 planning_input.maximum_closure)
        proposed_closure, proposed_derivations = closure(planning_input.proposed, planning_input.profile,
                                                         planning_input.maximum_closure)
        return EngineOutcome(self.declaration.engine_ref, RULE_TABLES[planning_input.profile], base_closure,
                             proposed_closure, base_derivations, proposed_derivations,
                             {"strategy": "semi_naive_forward_chaining"})
