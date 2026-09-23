"""Assemble what one reviewer is sent: the shared instructions, then the exact candidate and its evidence.

The system part is the instruction resource's shared section, the reviewer's
lens section and the answer section. The request part names the candidate, its
body digest, its producer, the kind of body it declares (in the review sheet's
own words), the written criteria that apply to that kind with their
identifiers, the item record, every cited source file and the exact body text.
Each block of material is fenced by markers built from its digest, so the
material cannot close its own block. The prompt digest names both parts, and
the panel reuses a verdict only for the exact prompt it answered.
"""
from __future__ import annotations

import json

from loop_engine.core.context_budget import estimate_tokens

from .records import digest
from .reviewers import ReviewPrompt

MARKER_DIGITS = 16
#: The sheet refers to its kinds of body as "the first kind" and "the second kind".
ORDINALS = {1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth"}


def _block(label: str, sha256: str, text: str) -> str:
    tag = f"{label} {sha256[:MARKER_DIGITS]}"
    return f"<<<{tag} BEGIN>>>\n{text}\n<<<{tag} END>>>"


def _kind(request) -> str:
    """The kind of body the item declares, described by the review sheet's own quote for that kind."""
    grounding, criteria = request.grounding, request.criteria
    meaning = criteria.groundings.get(grounding)
    if meaning is None:
        return (f"Kind of body: the item record declares the grounding {grounding or 'nothing'!r}, which the review "
                "sheet does not name. Judge it by the criteria below only.")
    place = criteria.ordinal(grounding)
    return (f"Kind of body: the item record declares the grounding {grounding}, which is kind number {place} "
            f"(the {ORDINALS.get(place, str(place))} kind) of the {len(criteria.groundings)} kinds the review sheet "
            f"names. The sheet says of this kind: \"{meaning}\"")


def build_prompt(request, installation, instructions) -> ReviewPrompt:
    from .native import NativePackageReviewRequest
    if isinstance(request, NativePackageReviewRequest):
        return build_native_prompt(request, installation, instructions)
    system = "\n\n".join((instructions.every_reviewer(), "Your lens: " + instructions.lens(installation.lens),
                          instructions.answer()))
    criteria = "\n".join(f"- {criterion.criterion_id}: {criterion.quote}" for criterion in request.applicable_criteria)
    parts = [
        "Review request for one candidate item.",
        f"Candidate identity: {request.identity}",
        f"Body digest (SHA-256 of the exact bytes shown below): {request.body_sha256}",
        f"Body size: {request.body_size_bytes} bytes",
        f"Producer of the item: {request.producer.producer_identity}, model family {request.producer.family}.",
        _kind(request),
        f"Written criteria for this kind of body, quoted from {request.criteria.source_path}. These are the only "
        f"criteria for this item. Cite them by identifier:\n{criteria}",
        "Item record from items.json, as JSON:\n" + json.dumps(request.item, indent=2, sort_keys=True,
                                                               ensure_ascii=False),
    ]
    for source in request.cited_sources:
        parts.append(f"Cited source file {source.path} at revision {source.revision} (SHA-256 {source.sha256}):\n"
                     + _block("SOURCE", source.sha256, source.text))
    parts.append("Candidate body, exactly the text between the markers:\n"
                 + _block("BODY", request.body_sha256, request.body_text))
    parts.append("Answer now with the one JSON object your instructions describe. Copy this body digest "
                 f"exactly into body_sha256: {request.body_sha256}")
    user = "\n\n".join(parts)
    return ReviewPrompt(system=system, user=user, sha256=digest({"system": system, "user": user}),
                        estimated_input_tokens=estimate_tokens(user, system), identity=request.identity,
                        body_sha256=request.body_sha256)


def build_native_prompt(request, installation, instructions) -> ReviewPrompt:
    """Keep every exact payload separate; the verdict digest identifies the canonical package document."""
    system = "\n\n".join((instructions.every_reviewer(), "Your lens: " + instructions.lens(installation.lens),
                           instructions.answer()))
    criteria = "\n".join(f"- {item.criterion_id}: {item.quote}" for item in request.applicable_criteria)
    tree = "\n".join(f"- {file.entry.path} | {file.entry.role} | {file.entry.media_type} | "
                     f"{file.entry.size_bytes} bytes | {file.entry.digest}" for file in request.files)
    parts = ["Review subject: complete original native harness package.",
             f"Subject record type: {request.to_record()['record_type']}",
             f"Package identity: {request.identity}; canonical package digest: {request.body_sha256}",
             f"Producer: {request.producer.producer_identity}; family: {request.producer.family}",
             "Exact complete file tree:\n" + tree, "Written native package criteria:\n" + criteria,
             "Item declaration:\n" + json.dumps(request.item, sort_keys=True, ensure_ascii=False),
             "Canonical package document:\n" + request.body_text]
    for source in request.cited_sources:
        parts.append(f"Cited source {source.path} at {source.revision}:\n" + _block("SOURCE", source.sha256, source.text))
    for file in request.files:
        if file.text is None:
            parts.append(f"BINARY FILE NOT TEXT-REVIEWED: {file.entry.path}; digest {file.entry.digest}. "
                         "Do not approve without separate declared binary verification.")
        else:
            parts.append(f"Exact file {file.entry.path}:\n" + _block("FILE", file.entry.digest, file.text))
    parts.append("Return one JSON verdict with body_sha256 equal to the canonical package digest: " + request.body_sha256)
    user = "\n\n".join(parts)
    return ReviewPrompt(system, user, digest({"system": system, "user": user}), estimate_tokens(user, system),
                        request.identity, request.body_sha256)
