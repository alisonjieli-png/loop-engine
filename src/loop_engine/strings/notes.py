"""Notes — the working knowledge a practitioner GENERATES while solving.

An engineer does not only bring materials (checklists, packs, prior experience);
they *produce* their own — notes on paper, in logs, filled-in sheets, sketches.
Those notes start personal, some become institutional knowledge that is shared
and reviewed, and a few are published.  This module gives that production its own
plane, mirroring how a human actually works:

- a **NoteTemplate** is a sheet template — typed fields so notes are consistent
  and *measurable*;
- a **Note** is one generated artifact, content-addressed, tagged with who or
  what produced it (the practitioner, research, the graph, a council) and with a
  status that only ever advances through review, never by assertion;
- ``measure_note`` extracts deterministic measures even from unstructured notes
  (a model can extract richer ones; images and logs are carried as refs);
- a **council review** aggregates several reviewers' quality / stability /
  fragility scores and recommends **promotion with a weight** — a stable,
  low-fragility, high-quality note is promoted from personal to institutional
  knowledge with more weight, so it surfaces first when recalled;
- **publishing** an institutional note requires authorization.

The discipline matches the rest of the system: a note is an observation, not
truth.  Personal → reviewed → institutional → published is an append-only ladder
gated by evidence and authority; a low-quality or fragile note is not promoted,
and nothing is published by assertion.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, replace
from typing import Any, Mapping, Sequence

NOTE_KINDS = ("observation", "hypothesis", "decision_log", "experiment_sheet",
              "postmortem", "research_digest", "sketch", "checklist_fill")

# The append-only status ladder — each advance is gated, never by assertion.
NOTE_STATUSES = ("personal", "reviewed", "institutional", "published",
                 "retracted")

# Who or what generated the note.
NOTE_AUTHORS = ("practitioner", "research", "graph", "council", "human")


@dataclass(frozen=True)
class NoteTemplate:
    """A sheet template: typed fields so notes are consistent and measurable."""
    id: str
    kind: str
    required_fields: tuple[str, ...] = ()
    optional_fields: tuple[str, ...] = ()
    measures: tuple[str, ...] = ()          # what an evaluator should extract

    def __post_init__(self) -> None:
        if self.kind not in NOTE_KINDS:
            raise ValueError(f"unknown note kind {self.kind!r}; expected "
                             f"{NOTE_KINDS}")


@dataclass(frozen=True)
class Note:
    """One generated note — content-addressed, provenance-tagged."""
    id: str
    template_id: str
    kind: str
    author: str
    fields: dict = field(default_factory=dict)
    free_text: str = ""
    refs: tuple[str, ...] = ()              # image/log/artifact refs
    status: str = "personal"
    weight: float = 0.0                     # institutional recall weight
    review: dict = field(default_factory=dict)
    created_ts: str = ""

    def to_dict(self) -> dict:
        return {k: (list(v) if isinstance(v, tuple) else v)
                for k, v in {**self.__dict__}.items()}


def _note_digest(template_id: str, author: str, kind: str,
                 fields: Mapping[str, Any], free_text: str,
                 refs: Sequence[str]) -> str:
    payload = json.dumps({"t": template_id, "a": author, "k": kind,
                          "f": {k: fields[k] for k in sorted(fields)},
                          "x": free_text, "r": sorted(refs)},
                         sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def fill_note(template: NoteTemplate, author: str, values: Mapping[str, Any], *,
              free_text: str = "", refs: Sequence[str] = (),
              created_ts: str = "") -> Note:
    """Fill a template into a personal Note, validating the required fields.
    Unstructured notes are fine — pass free_text and refs, with no fields."""
    if author not in NOTE_AUTHORS:
        raise ValueError(f"unknown note author {author!r}; expected "
                         f"{NOTE_AUTHORS}")
    missing = [f for f in template.required_fields if not values.get(f)]
    if missing:
        raise ValueError(f"note is missing required fields: {missing}")
    fields = {k: v for k, v in values.items()
              if k in template.required_fields or k in template.optional_fields}
    nid = _note_digest(template.id, author, template.kind, fields, free_text,
                       tuple(refs))
    return Note(id=f"note.{nid}", template_id=template.id, kind=template.kind,
                author=author, fields=fields, free_text=free_text,
                refs=tuple(refs), status="personal", created_ts=created_ts)


# A small facet vocabulary for measuring unstructured note text.
_FACET_TERMS = {
    "validation": ("validation", "cv", "fold", "leakage", "split"),
    "modeling": ("model", "estimator", "train", "fit"),
    "data": ("missing", "categorical", "outlier", "scale", "encode"),
    "risk": ("risk", "fragile", "unstable", "overfit"),
    "result": ("score", "metric", "improved", "regressed")}


def measure_note(note: Note, template: NoteTemplate | None = None) -> dict:
    """Deterministic measures over a note — completeness, size, facets, refs —
    so even an unstructured note can be measured and compared.  A model may add
    richer semantic measures later; these need none."""
    completeness = 1.0
    if template and template.required_fields:
        present = sum(1 for f in template.required_fields if note.fields.get(f))
        completeness = present / len(template.required_fields)
    text = (note.free_text + " " + " ".join(str(v) for v in note.fields.values())
            ).lower()
    facets = sorted(f for f, terms in _FACET_TERMS.items()
                    if any(t in text for t in terms))
    return {"record_type": "note_measures/v1", "note_id": note.id,
            "kind": note.kind, "author": note.author,
            "field_completeness": round(completeness, 3),
            "text_length": len(note.free_text),
            "field_count": len(note.fields), "ref_count": len(note.refs),
            "has_image": any(str(r).lower().endswith((".png", ".jpg", ".jpeg"))
                             or "image" in str(r).lower() for r in note.refs),
            "facets": facets}


def council_review(scores: Sequence[Mapping[str, float]]) -> dict:
    """Aggregate several reviewers' quality/stability/fragility scores (each
    0..1).  Quality and stability are averaged; fragility takes the WORST case
    (a note is as fragile as its most fragile review — conservative).  The
    recall weight rewards stable, low-fragility, high-quality notes."""
    if not scores:
        return {"quality": 0.0, "stability": 0.0, "fragility": 1.0,
                "weight": 0.0, "reviewers": 0}
    q = sum(float(s.get("quality", 0.0)) for s in scores) / len(scores)
    st = sum(float(s.get("stability", 0.0)) for s in scores) / len(scores)
    fr = max(float(s.get("fragility", 0.0)) for s in scores)
    weight = q * st * (1.0 - fr)
    return {"quality": round(q, 3), "stability": round(st, 3),
            "fragility": round(fr, 3), "weight": round(weight, 3),
            "reviewers": len(scores)}


@dataclass
class NoteStore:
    """Two planes: personal notes and promoted institutional knowledge.  Every
    status change appends a new version; the prior is preserved."""
    personal: dict = field(default_factory=dict)       # id -> Note
    institutional: dict = field(default_factory=dict)  # id -> Note
    history: list = field(default_factory=list)        # append-only log

    def add(self, note: Note) -> Note:
        self.personal[note.id] = note
        self.history.append({"event": "add", "note": note.id,
                             "status": note.status})
        return note

    def review(self, note_id: str, reviewer_scores: Sequence[Mapping[str, float]]
               ) -> Note:
        note = self.personal.get(note_id)
        if note is None:
            raise KeyError(f"no personal note {note_id!r}")
        agg = council_review(reviewer_scores)
        reviewed = replace(note, status="reviewed", review=agg,
                           weight=agg["weight"])
        self.personal[note_id] = reviewed
        self.history.append({"event": "review", "note": note_id, "review": agg})
        return reviewed

    def promote(self, note_id: str, *, min_quality: float = 0.6,
                max_fragility: float = 0.4) -> dict:
        """Promote a reviewed note to institutional knowledge ONLY if its council
        review clears the quality and fragility gates.  Returns the outcome."""
        note = self.personal.get(note_id)
        if note is None or note.status != "reviewed":
            return {"promoted": False, "reason": "note is not reviewed"}
        r = note.review
        if r.get("quality", 0.0) < min_quality:
            return {"promoted": False,
                    "reason": f"quality {r.get('quality')} below {min_quality}"}
        if r.get("fragility", 1.0) > max_fragility:
            return {"promoted": False,
                    "reason": f"fragility {r.get('fragility')} above "
                    f"{max_fragility}"}
        inst = replace(note, status="institutional")
        self.institutional[note_id] = inst
        self.history.append({"event": "promote", "note": note_id,
                             "weight": inst.weight})
        return {"promoted": True, "note": note_id, "weight": inst.weight}

    def publish(self, note_id: str, *, authorized: bool) -> dict:
        """Publish an institutional note — requires authorization, never by
        assertion."""
        note = self.institutional.get(note_id)
        if note is None:
            return {"published": False, "reason": "note is not institutional"}
        if not authorized:
            return {"published": False, "reason": "publishing not authorized"}
        published = replace(note, status="published")
        self.institutional[note_id] = published
        self.history.append({"event": "publish", "note": note_id})
        return {"published": True, "note": note_id}

    def recall_institutional(self, *, facet: str | None = None) -> list[Note]:
        """Institutional notes, highest-weight first — so a stable, high-quality
        note surfaces before a marginal one when the loop recalls context."""
        notes = list(self.institutional.values())
        notes.sort(key=lambda n: (-n.weight, n.id))
        return notes


# ---------------------------------------------------------------------------
# Self-test — deterministic, no model.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    tmpl = NoteTemplate(
        "sheet.experiment", "experiment_sheet",
        required_fields=("hypothesis", "result"),
        optional_fields=("next_step",), measures=("field_completeness",))

    # fill_note validates required fields.
    missing = False
    try:
        fill_note(tmpl, "practitioner", {"hypothesis": "leakage suspected"})
    except ValueError:
        missing = True
    note = fill_note(tmpl, "practitioner",
                     {"hypothesis": "leakage suspected", "result": "group CV "
                      "score dropped 0.15", "next_step": "freeze group split"},
                     free_text="Random CV looked too good; validation unit "
                     "matters here.", refs=("log://run-4",))
    check("filling_a_template_validates_required_fields",
          missing and note.status == "personal"
          and note.author == "practitioner" and note.id.startswith("note."),
          "a sheet missing a required field is refused; a complete one becomes a "
          "personal, content-addressed note")

    # measure_note extracts deterministic measures from a (partly unstructured)
    # note.
    m = measure_note(note, tmpl)
    check("a_note_is_measurable_even_when_unstructured",
          m["field_completeness"] == 1.0 and "validation" in m["facets"]
          and m["ref_count"] == 1,
          "the note measures full field completeness, detects the 'validation' "
          "facet from its free text, and counts its log ref — an unstructured "
          "note is still measured")

    store = NoteStore()
    store.add(note)

    # A strong council review promotes the note to institutional knowledge with
    # weight; a weak/fragile one does not.
    store.review(note.id, [{"quality": 0.9, "stability": 0.9, "fragility": 0.1},
                           {"quality": 0.8, "stability": 0.85, "fragility": 0.2}])
    promo = store.promote(note.id)
    check("a_council_reviewed_strong_note_is_promoted_with_weight",
          promo["promoted"] and promo["weight"] > 0.5
          and store.institutional[note.id].status == "institutional",
          "two reviewers score the note high-quality, stable, low-fragility; it "
          "is promoted to institutional knowledge with a recall weight > 0.5")

    fragile_note = fill_note(tmpl, "graph",
                             {"hypothesis": "add deep net", "result": "unstable "
                              "across seeds"})
    store.add(fragile_note)
    store.review(fragile_note.id,
                 [{"quality": 0.7, "stability": 0.3, "fragility": 0.8}])
    frag_promo = store.promote(fragile_note.id)
    check("a_fragile_note_is_not_promoted",
          not frag_promo["promoted"] and "fragility" in frag_promo["reason"],
          "a note the council scored highly fragile (0.8) fails the fragility "
          "gate and is NOT promoted — quality alone does not carry it")

    # Publishing requires authorization.
    unauth = store.publish(note.id, authorized=False)
    auth = store.publish(note.id, authorized=True)
    check("publishing_requires_authorization",
          not unauth["published"] and auth["published"]
          and store.institutional[note.id].status == "published",
          "an institutional note cannot be published without authorization; with "
          "it, the note advances to published — never by assertion")

    # Recall orders institutional notes by weight; append-only history preserved.
    recalled = store.recall_institutional()
    check("recall_orders_by_weight_and_history_is_append_only",
          recalled and recalled[0].id == note.id
          and any(h["event"] == "promote" for h in store.history)
          and len(store.history) >= 5,
          "the strong note leads institutional recall by weight, and every "
          "status change (add/review/promote/publish) is preserved in the "
          "append-only history")

    # Determinism: same content -> same note id.
    note2 = fill_note(tmpl, "practitioner",
                      {"hypothesis": "leakage suspected", "result": "group CV "
                       "score dropped 0.15", "next_step": "freeze group split"},
                      free_text="Random CV looked too good; validation unit "
                      "matters here.", refs=("log://run-4",))
    check("notes_are_content_addressed_and_deterministic",
          note2.id == note.id,
          "an identical note produces the identical content-addressed id — "
          "deduplicated and replayable")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "notes_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
