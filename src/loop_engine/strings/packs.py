"""Domain packs — swappable question / persona / context / research / checklist
knowledge, layered from general to very specific.

The loop should be as sharp as the best expert in whatever field the problem is
in.  An expert's edge is partly a large, mostly-tacit list of things they check,
measure, and consider — and that list is different for general AI/ML, for data
engineering, and again for something as specific as image processing, well
drilling, or disease detection.  So the knowledge that drives deliberation —
what questions to ask, which personas to adopt, which context lenses to use,
which research to run, which checklist to satisfy — must be **swappable data**,
not hard-coded, and it must **layer**: a general ML question pack applies to
every ML task, a domain pack adds to it, and a very specific pack adds to that.

A ``Pack`` is that data: a versioned, namespaced list of items with an
applicability declaration.  A ``PackRegistry`` resolves the applicable packs for
a task signature and composes their items **general-first, specific-last**, so a
domain pack augments (never silently replaces) the general one.  Adding a new
pack — a 10,000-question AI/ML pack mined from textbooks and competitions, or a
narrow disease-detection pack — is one ``register`` call or one loaded file; no
code changes.  Packs are the mechanism by which the system continuously becomes
smarter about a field.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Mapping, Sequence

PACK_KINDS = ("question", "persona", "context", "research", "checklist", "lens")


@dataclass(frozen=True)
class PackItem:
    """One item in a pack — a question, a persona name, a research query, a
    checklist point.  ``facet`` groups it (validation, leakage, modeling…) and
    ``measures`` says what an expert is checking with it."""
    id: str
    text: str
    facet: str = ""
    measures: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {k: (list(v) if isinstance(v, tuple) else v)
                for k, v in asdict(self).items()}


@dataclass(frozen=True)
class Pack:
    """A versioned, applicability-scoped bundle of items of one kind."""
    id: str
    kind: str
    domain: str                              # "general" | "ml" | "image" | …
    version: str = "1.0.0"
    items: tuple[PackItem, ...] = ()
    # Applicability: the task shapes this pack applies to.  A "general" pack (or
    # empty applicability) applies to everything within its domain family.
    task_families: tuple[str, ...] = ()
    modalities: tuple[str, ...] = ()
    keywords: tuple[str, ...] = ()
    # Scoping dimensions (AND-filters): a pack scoped to an expert level,
    # geography, or industry applies only to a matching signature — "per job
    # description, expert level, geography, industry".
    expert_level: str = ""              # e.g. "senior", "specialist"
    geography: str = ""                 # e.g. "eu", "us"
    industry: str = ""                  # e.g. "healthcare", "oil_and_gas"
    # Layering: how specific this pack is (0 = general, higher = more specific).
    specificity: int = 0
    provenance: str = ""

    def __post_init__(self) -> None:
        if self.kind not in PACK_KINDS:
            raise ValueError(f"unknown pack kind {self.kind!r}; expected "
                             f"{PACK_KINDS}")

    def applies_to(self, signature: Mapping[str, Any]) -> bool:
        """True if this pack applies to a task signature.  Scoping dimensions
        (expert_level / geography / industry) are AND-filters — a scoped pack
        applies only to a matching signature.  Then a general pack (no
        family/modality/keyword constraints) applies to everything, otherwise it
        applies when any declared family, modality, or keyword matches."""
        for dim in ("expert_level", "geography", "industry"):
            declared = getattr(self, dim)
            if declared and str(signature.get(dim, "")).lower() != declared.lower():
                return False
        if not (self.task_families or self.modalities or self.keywords):
            return True
        fam = str(signature.get("task_family", "")).lower()
        mod = str(signature.get("modality", "")).lower()
        kws = {str(k).lower() for k in signature.get("keywords", ())}
        kws.add(str(signature.get("domain", "")).lower())
        return (fam in {f.lower() for f in self.task_families}
                or mod in {m.lower() for m in self.modalities}
                or bool(kws & {k.lower() for k in self.keywords}))

    def to_dict(self) -> dict:
        d = {k: (list(v) if isinstance(v, tuple) else v)
             for k, v in asdict(self).items()}
        d["items"] = [i.to_dict() for i in self.items]
        d["item_count"] = len(self.items)
        return d


def pack_from_dict(data: Mapping[str, Any]) -> Pack:
    """Build a Pack from plain data (as loaded from a JSONL/JSON store), so packs
    live in a store and are swapped in without code."""
    items = tuple(PackItem(id=str(i["id"]), text=str(i["text"]),
                           facet=str(i.get("facet", "")),
                           measures=tuple(i.get("measures", ())))
                  for i in data.get("items", ()))
    return Pack(
        id=str(data["id"]), kind=str(data["kind"]),
        domain=str(data.get("domain", "general")),
        version=str(data.get("version", "1.0.0")), items=items,
        task_families=tuple(data.get("task_families", ())),
        modalities=tuple(data.get("modalities", ())),
        keywords=tuple(data.get("keywords", ())),
        expert_level=str(data.get("expert_level", "")),
        geography=str(data.get("geography", "")),
        industry=str(data.get("industry", "")),
        specificity=int(data.get("specificity", 0)),
        provenance=str(data.get("provenance", "")))


@dataclass
class PackRegistry:
    _packs: dict = field(default_factory=dict)   # id -> Pack

    def register(self, pack: Pack, *, replace: bool = False) -> Pack:
        if pack.id in self._packs and not replace:
            raise ValueError(f"pack {pack.id!r} already registered; "
                             f"pass replace=True")
        self._packs[pack.id] = pack
        return pack

    def unregister(self, pack_id: str) -> None:
        self._packs.pop(pack_id, None)

    def get(self, pack_id: str) -> "Pack | None":
        return self._packs.get(pack_id)

    def packs_for(self, kind: str, signature: Mapping[str, Any]) -> list[Pack]:
        """Applicable packs of a kind, ordered general-first (ascending
        specificity) so a specific pack layers on top of the general one."""
        out = [p for p in self._packs.values()
               if p.kind == kind and p.applies_to(signature)]
        out.sort(key=lambda p: (p.specificity, p.domain, p.id))
        return out

    def items_for(self, kind: str, signature: Mapping[str, Any], *,
                  dedup: bool = True) -> list[PackItem]:
        """The composed items from every applicable pack, general-first,
        deduplicated by text so a specific pack augments the general one without
        repeating shared items."""
        seen: set[str] = set()
        out: list[PackItem] = []
        for pack in self.packs_for(kind, signature):
            for item in pack.items:
                key = item.text.strip().lower()
                if dedup and key in seen:
                    continue
                seen.add(key)
                out.append(item)
        return out

    def coverage(self, signature: Mapping[str, Any]) -> dict:
        """What packs and how many items apply to a signature, by kind — so an
        operator can see the system is drawing on the right domain expertise."""
        by_kind: dict[str, dict] = {}
        for kind in PACK_KINDS:
            packs = self.packs_for(kind, signature)
            if packs:
                by_kind[kind] = {"packs": [p.id for p in packs],
                                 "item_count": len(self.items_for(kind,
                                                                  signature))}
        return {"record_type": "pack_coverage/v1", "signature": dict(signature),
                "by_kind": by_kind}


# A few seed packs (fixtures / examples).  Real packs live in a store and can be
# thousands of items; these show the layering.
def seed_registry() -> PackRegistry:
    reg = PackRegistry()
    reg.register(Pack(
        id="pack.question.ml.general", kind="question", domain="ml",
        specificity=0,
        items=(PackItem("q.ml.leakage", "Could this result be caused by leakage?",
                        "validation", ("leakage",)),
               PackItem("q.ml.split", "Does the validation unit match the test "
                        "distribution?", "validation", ("split",)),
               PackItem("q.ml.baseline", "What is the simplest competitive "
                        "baseline?", "modeling", ("baseline",)),
               PackItem("q.ml.metric", "What is the metric actually rewarding?",
                        "metric", ("metric",)))))
    reg.register(Pack(
        id="pack.question.image.processing", kind="question", domain="image",
        specificity=2, modalities=("image",), keywords=("image", "vision"),
        items=(PackItem("q.img.resolution", "Is the input resolution and "
                        "aspect ratio consistent across samples?", "preprocess",
                        ("resolution",)),
               PackItem("q.img.augment", "Which augmentations preserve the "
                        "label, and which corrupt it?", "augmentation",
                        ("augmentation",)),
               PackItem("q.img.noise", "Is there sensor noise or artifacts that "
                        "need principled handling?", "preprocess", ("noise",)))))
    reg.register(Pack(
        id="pack.checklist.ml.validation", kind="checklist", domain="ml",
        specificity=0,
        items=(PackItem("c.ml.split_frozen", "Split contract is frozen and "
                        "leakage-audited.", "validation"),
               PackItem("c.ml.oof", "Out-of-fold predictions exist before any "
                        "ensembling.", "validation"))))
    return reg


# ---------------------------------------------------------------------------
# Self-test — deterministic.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    reg = seed_registry()
    tabular = {"task_family": "classification", "modality": "tabular"}
    image = {"task_family": "segmentation", "modality": "image",
             "domain": "disease_detection"}

    # A general ML pack applies to any ML task; the image pack does not apply to
    # a tabular task.
    tab_q = reg.items_for("question", tabular)
    check("a_general_pack_applies_and_a_domain_pack_does_not_leak",
          any(i.id == "q.ml.leakage" for i in tab_q)
          and not any(i.id.startswith("q.img") for i in tab_q),
          "a tabular task draws the general ML questions and none of the "
          "image-specific ones — a domain pack does not leak into an unrelated "
          "task")

    # An image task LAYERS the general ML questions AND the image-specific ones,
    # general first.
    img_q = reg.items_for("question", image)
    ids = [i.id for i in img_q]
    check("a_specific_task_layers_general_plus_domain_packs",
          "q.ml.leakage" in ids and "q.img.noise" in ids
          and ids.index("q.ml.leakage") < ids.index("q.img.noise"),
          "an image task gets the general ML questions AND the image-processing "
          "questions, general-first — the specific pack augments the general "
          "one, it does not replace it")

    # Swapping in a NEW domain pack is one call and it immediately applies.
    reg.register(Pack(
        id="pack.question.disease.detection", kind="question",
        domain="disease_detection", specificity=3,
        keywords=("disease_detection", "disease"),
        items=(PackItem("q.dis.class_prior", "Is the disease prevalence in "
                        "training representative of deployment?", "epidemiology",
                        ("prevalence",)),)))
    img_q2 = reg.items_for("question", image)
    check("a_new_pack_swaps_in_with_one_call_and_applies_immediately",
          any(i.id == "q.dis.class_prior" for i in img_q2)
          and len(img_q2) == len(img_q) + 1,
          "registering a disease-detection question pack makes its questions "
          "immediately apply to a matching task — the system gets smarter about "
          "a field by adding a pack, no code change")

    # Packs load from plain data (a store), and coverage reports what applies.
    loaded = pack_from_dict({
        "id": "pack.persona.image.experts", "kind": "persona", "domain": "image",
        "modalities": ["image"], "specificity": 2,
        "items": [{"id": "p.img.radiologist", "text": "radiologist",
                   "facet": "domain"}]})
    reg.register(loaded)
    cov = reg.coverage(image)
    check("packs_load_from_data_and_coverage_reports_applied_expertise",
          "persona" in cov["by_kind"]
          and "pack.persona.image.experts" in cov["by_kind"]["persona"]["packs"]
          and "question" in cov["by_kind"],
          "a persona pack built from plain data registers and applies; coverage "
          "shows which packs and how many items drive a task, so an operator "
          "sees the domain expertise in play")

    # Determinism + unknown kind refused.
    reg2 = seed_registry()
    bad = False
    try:
        Pack("x", "gossip", "ml")
    except ValueError:
        bad = True
    check("composition_is_deterministic_and_unknown_kind_refused",
          [i.id for i in reg2.items_for("question", image)]
          == [i.id for i in seed_registry().items_for("question", image)]
          and bad,
          "the same registry and signature always compose the identical item "
          "list, and a pack of an unknown kind is refused")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "packs_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
