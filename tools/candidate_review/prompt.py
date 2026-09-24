"""Assemble what one reviewer is sent: the shared instructions, then the exact candidate and its evidence.

The system part is the instruction resource's shared section, the reviewer's
lens section and the answer section. The request part names the candidate, its
body digest, its producer, the kind of body it declares (in the review sheet's
own words), the written criteria that apply to that kind with their
identifiers, the item record, every cited source file and the exact body text.
Each block of material is fenced by markers built from its digest, so the
material cannot close its own block. The prompt digest names both parts, and
the panel reuses a verdict only for the exact prompt it answered.

A batch prompt asks one reviewer about several candidates at once. Its system
part adds the batch answer contract from ``resources/BATCH-ANSWER.md`` to the
same instructions, and its request part holds each candidate's own material,
exactly as a single prompt would hold it, inside a block fenced by markers
built from that candidate's digest. Each candidate's verdict is keyed by a
member digest that names the batch system part and that candidate's own
material only, so the same candidate judged under the same contract keeps its
key whichever other candidates share the request; the calibration measures
whether sharing a request changes verdicts at all.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import json
from pathlib import Path

from loop_engine.core.context_budget import estimate_tokens

from .records import digest, refuse, sha256_hex
from .reviewers import ReviewPrompt

BATCH_ANSWER_PATH = Path(__file__).resolve().parent / "resources" / "BATCH-ANSWER.md"
BATCH_ANSWER_SECTION = "Batch answer"
BATCH_PROMPT_RECORD = "candidate_review_batch_prompt/v1"
BATCH_MEMBER_RECORD = "candidate_review_batch_member_prompt/v1"
#: The largest number of candidates one request may hold.
MAXIMUM_BATCH = 12

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


def _system(installation, instructions) -> str:
    return "\n\n".join((instructions.every_reviewer(), "Your lens: " + instructions.lens(installation.lens),
                        instructions.answer()))


def _is_native(request) -> bool:
    from .native import NativePackageReviewRequest
    return isinstance(request, NativePackageReviewRequest)


def build_prompt(request, installation, instructions) -> ReviewPrompt:
    if _is_native(request):
        return build_native_prompt(request, installation, instructions)
    system = _system(installation, instructions)
    parts = _starter_parts(request) + [_starter_answer_line(request)]
    user = "\n\n".join(parts)
    return ReviewPrompt(system=system, user=user, sha256=digest({"system": system, "user": user}),
                        estimated_input_tokens=estimate_tokens(user, system), identity=request.identity,
                        body_sha256=request.body_sha256)


def _starter_answer_line(request) -> str:
    return ("Answer now with the one JSON object your instructions describe. Copy this body digest "
            f"exactly into body_sha256: {request.body_sha256}")


def _starter_parts(request) -> list:
    """Everything a single starter prompt holds about its candidate, without the closing answer line."""
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
    return parts


def build_native_prompt(request, installation, instructions) -> ReviewPrompt:
    """Keep every exact payload separate; the verdict digest identifies the canonical package document."""
    system = _system(installation, instructions)
    user = "\n\n".join(_native_parts(request) + [_native_answer_line(request)])
    return ReviewPrompt(system, user, digest({"system": system, "user": user}), estimate_tokens(user, system),
                        request.identity, request.body_sha256)


def _native_answer_line(request) -> str:
    return "Return one JSON verdict with body_sha256 equal to the canonical package digest: " + request.body_sha256


def _native_parts(request) -> list:
    """Everything a single native prompt holds about its package, without the closing answer line."""
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
    return parts


@lru_cache(maxsize=4)
def _batch_contract(path: str) -> tuple:
    """The batch answer section and the digest of the whole resource it comes from."""
    raw = Path(path).read_bytes()
    text = raw.decode("utf-8")
    heading = "## " + BATCH_ANSWER_SECTION
    if heading not in text.splitlines():
        refuse("instructions_section_missing", f"the batch answer contract needs the section {heading!r}")
    section = text.split(heading + "\n", 1)[1].split("\n## ", 1)[0].strip()
    if not section:
        refuse("instructions_section_missing", "the batch answer section is empty")
    return section, sha256_hex(raw)


def batch_system(installation, instructions, contract_path: Path = BATCH_ANSWER_PATH) -> str:
    section, _sha = _batch_contract(str(contract_path))
    return _system(installation, instructions) + "\n\n" + section


def member_parts(request) -> str:
    """One candidate's own material, exactly as its single prompt holds it, without the answer line."""
    return "\n\n".join(_native_parts(request) if _is_native(request) else _starter_parts(request))


def member_prompt_sha256(request, installation, instructions, contract_path: Path = BATCH_ANSWER_PATH) -> str:
    """The key digest of one candidate inside any batch: the batch system part and its own material only."""
    return digest({"record_type": BATCH_MEMBER_RECORD, "system": batch_system(installation, instructions,
                                                                              contract_path),
                   "material": member_parts(request)})


@dataclass(frozen=True)
class BatchMember:
    """One candidate inside a batch prompt, with the digest its verdict is keyed by."""

    request: object
    member_prompt_sha256: str

    @property
    def identity(self) -> str:
        return self.request.identity

    @property
    def body_sha256(self) -> str:
        return self.request.body_sha256


@dataclass(frozen=True)
class BatchPrompt:
    """What one reviewer is sent about several candidates, and each candidate's own key digest."""

    system: str
    user: str
    sha256: str
    estimated_input_tokens: int
    members: tuple

    def as_prompt(self) -> ReviewPrompt:
        return ReviewPrompt(self.system, self.user, self.sha256, self.estimated_input_tokens)


def build_batch_prompt(requests, installation, instructions, contract_path: Path = BATCH_ANSWER_PATH) -> BatchPrompt:
    """One request about several candidates of one content profile, each fenced by its own digest markers."""
    requests = tuple(requests)
    if not 1 <= len(requests) <= MAXIMUM_BATCH:
        refuse("batch_size_invalid", f"a batch holds from 1 to {MAXIMUM_BATCH} candidates")
    if len({request.identity for request in requests}) != len(requests):
        refuse("batch_repeats_a_candidate", "a batch names each candidate once")
    if len({_is_native(request) for request in requests}) != 1:
        refuse("batch_mixes_profiles", "a batch holds candidates of one content profile")
    system = batch_system(installation, instructions, contract_path)
    total = len(requests)
    blocks, order = [], []
    for position, request in enumerate(requests, 1):
        blocks.append(_block(f"CANDIDATE {position} OF {total}", request.body_sha256, member_parts(request)))
        order.append(f"{position}. identity {request.identity}, body_sha256 {request.body_sha256}")
    user = "\n\n".join([f"Review request for {total} candidates. Judge each one on its own, by the criteria "
                         "listed inside its own block."] + blocks +
                        ["Answer now with one JSON object whose verdicts list holds exactly "
                         f"{total} verdicts, one for each candidate in this order, each copying its identity "
                         "and body digest exactly:\n" + "\n".join(order)])
    members = tuple(BatchMember(request, member_prompt_sha256(request, installation, instructions, contract_path))
                    for request in requests)
    return BatchPrompt(system, user, digest({"record_type": BATCH_PROMPT_RECORD, "system": system, "user": user}),
                       estimate_tokens(user, system), members)
