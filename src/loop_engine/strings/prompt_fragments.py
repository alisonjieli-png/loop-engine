"""Prompt fragments — composable, versioned pieces, not millions of full prompts.

Storing thousands of fully-materialized prompts creates duplication, drift, and
an unmanageable Cartesian product (v3 §12.2, AP-05).  Instead, prompts are
composed from small, typed, versioned **fragments** — a system/authority
boundary, an output-schema instruction, an anti-hallucination clause, a
failure-first framing, a persona line — assembled by a **recipe**.  Only the
selected combination is materialized, and each materialized instance is recorded
by digest, so prompt experimentation is reproducible and the source of every
variation is inspectable.

A fragment declares which envelope fields it requires, so composing a recipe
whose fragments need a field the caller did not supply fails loudly rather than
rendering a broken prompt.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

# Fragment purposes (namespaces) — a small stable set.
FRAGMENT_PURPOSES = ("system", "authority", "purpose", "role", "method",
                     "context", "uncertainty", "critique", "evidence",
                     "output", "safety", "domain")


@dataclass(frozen=True)
class PromptFragment:
    id: str
    purpose: str
    template: str                              # may contain {field} placeholders
    version: str = "1.0.0"
    required_fields: tuple[str, ...] = ()
    optional_fields: tuple[str, ...] = ()
    incompatible_with: tuple[str, ...] = ()    # fragment ids that conflict
    effect_tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.purpose not in FRAGMENT_PURPOSES:
            raise ValueError(f"unknown fragment purpose {self.purpose!r}; "
                             f"expected {FRAGMENT_PURPOSES}")

    def render(self, values: Mapping[str, Any]) -> str:
        missing = [f for f in self.required_fields if f not in values]
        if missing:
            raise KeyError(f"fragment {self.id!r} requires fields {missing}")
        safe = {**{f: "" for f in self.optional_fields}, **values}
        try:
            return self.template.format(**safe)
        except KeyError as exc:
            raise KeyError(f"fragment {self.id!r} template references "
                           f"undeclared field {exc}") from exc


@dataclass(frozen=True)
class PromptRecipe:
    id: str
    fragment_ids: tuple[str, ...]
    version: str = "1.0.0"


@dataclass
class FragmentRegistry:
    _frags: dict = field(default_factory=dict)      # id -> PromptFragment

    def register(self, fragment: PromptFragment, *, replace: bool = False
                 ) -> PromptFragment:
        if fragment.id in self._frags and not replace:
            raise ValueError(f"fragment {fragment.id!r} already registered")
        self._frags[fragment.id] = fragment
        return fragment

    def get(self, fragment_id: str) -> "PromptFragment | None":
        return self._frags.get(fragment_id)

    def compose(self, recipe: PromptRecipe, values: Mapping[str, Any]) -> dict:
        """Render a recipe into a prompt instance, checking that every fragment
        exists, no two are incompatible, and every required field is supplied.
        Returns the text and a digest identifying this exact instance."""
        frags = []
        for fid in recipe.fragment_ids:
            frag = self._frags.get(fid)
            if frag is None:
                raise KeyError(f"recipe {recipe.id!r} references unknown "
                               f"fragment {fid!r}")
            frags.append(frag)
        # Incompatibility check.
        ids = set(recipe.fragment_ids)
        for frag in frags:
            clash = ids & set(frag.incompatible_with)
            if clash:
                raise ValueError(f"fragment {frag.id!r} is incompatible with "
                                 f"{sorted(clash)} in recipe {recipe.id!r}")
        rendered = [f.render(values) for f in frags]
        text = "\n".join(r for r in rendered if r)
        digest = hashlib.sha256(
            ("|".join(f"{f.id}@{f.version}" for f in frags) + "||" + text)
            .encode()).hexdigest()[:16]
        return {"record_type": "prompt_instance/v1", "recipe": recipe.id,
                "fragment_ids": list(recipe.fragment_ids),
                "fragment_versions": [f.version for f in frags],
                "text": text, "prompt_digest": digest,
                "effect_tags": sorted({t for f in frags for t in f.effect_tags})}


def seed_registry() -> FragmentRegistry:
    """A few reusable fragments used by each next-action prompt
    tends to share."""
    reg = FragmentRegistry()
    reg.register(PromptFragment(
        "frag.system.authority", "system",
        "You are a decision assistant. You propose; you do not authorize, "
        "compile, or claim success. The fold oracle decides outcomes.",
        effect_tags=("authority.boundary",)))
    reg.register(PromptFragment(
        "frag.role.persona", "role", "Adopt the lens of: {persona}.",
        required_fields=("persona",), effect_tags=("diversify.role",)))
    reg.register(PromptFragment(
        "frag.method.failure_first", "method",
        "Before proposing, ask what would make this fail and how to detect it.",
        effect_tags=("reduce.confirmation_bias",),
        incompatible_with=("frag.method.optimistic",)))
    reg.register(PromptFragment(
        "frag.uncertainty.declare", "uncertainty",
        "State your assumptions and what you do NOT know.",
        effect_tags=("increase.calibration",)))
    reg.register(PromptFragment(
        "frag.output.next_move_json", "output",
        "Return a JSON list of next-move proposals, each with move, reason, "
        "confidence, and a falsification test.",
        effect_tags=("format.structured",)))
    return reg


# ---------------------------------------------------------------------------
# Self-test — deterministic, no model.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    reg = seed_registry()
    recipe = PromptRecipe("recipe.next_action.review",
                          ("frag.system.authority", "frag.role.persona",
                           "frag.method.failure_first",
                           "frag.uncertainty.declare",
                           "frag.output.next_move_json"))

    inst = reg.compose(recipe, {"persona": "skeptical statistician"})
    check("a_recipe_composes_fragments_into_a_prompt_instance",
          "skeptical statistician" in inst["text"]
          and "propose; you do not authorize" in inst["text"]
          and "JSON list" in inst["text"] and inst["prompt_digest"]
          and "authority.boundary" in inst["effect_tags"],
          "the recipe assembles the authority boundary, persona, failure-first "
          "method, uncertainty, and output fragments into one prompt with a "
          "digest and effect tags")

    # A missing required field fails loudly.
    missing = False
    try:
        reg.compose(recipe, {})   # no persona
    except KeyError:
        missing = True
    check("a_missing_required_field_fails_loudly",
          missing, "composing a recipe whose persona fragment needs a persona, "
          "with no persona supplied, raises rather than rendering a broken "
          "prompt")

    # An incompatible pair is refused.
    reg.register(PromptFragment("frag.method.optimistic", "method",
                                "Assume this will work.",
                                incompatible_with=("frag.method.failure_first",)))
    clash_recipe = PromptRecipe("r.clash", ("frag.method.failure_first",
                                            "frag.method.optimistic"))
    clashed = False
    try:
        reg.compose(clash_recipe, {})
    except ValueError:
        clashed = True
    check("incompatible_fragments_are_refused",
          clashed, "a recipe pairing failure-first with its declared-incompatible "
          "optimistic fragment is refused")

    # Determinism: same recipe + values -> same digest.
    inst2 = reg.compose(recipe, {"persona": "skeptical statistician"})
    check("prompt_instances_are_deterministic_and_digested",
          inst2["prompt_digest"] == inst["prompt_digest"],
          "the same recipe and values always produce the identical prompt "
          "digest — prompt experimentation is reproducible and inspectable")

    # Unknown fragment purpose refused.
    bad = False
    try:
        PromptFragment("x", "vibes", "...")
    except ValueError:
        bad = True
    check("an_unknown_fragment_purpose_is_refused",
          bad, "a fragment of an unknown purpose is refused")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "prompt_fragments_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
