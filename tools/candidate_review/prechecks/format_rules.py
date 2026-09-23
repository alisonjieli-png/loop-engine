"""Format pre-check engine ``builtin_format_rules``.

Checks the body against the catalogue's written format (the same contract the
catalogue's own checks enforce, compared in a named check so the two cannot
drift apart) and checks the rendered skill file a client would install:

- the text is UTF-8 and starts with one title line;
- the word count is inside the declared range;
- every required part is present as its own heading line;
- the trailing line carries the grounding sentence of the item's declared
  grounding, anchored to the revision of its cited source;
- the practice sentence appears exactly when the body is general practice;
- no internal runtime vocabulary appears once cited paths are removed;
- the rendered front matter has a valid native name and a description that
  fits without truncation.
"""
from __future__ import annotations

import re

import yaml

from ..records import CandidateReviewError, read_part, refuse, text_field
from . import result_of
from .rendering import rendered_skill

VERSION = "1"
FIELDS = ("minimum_words", "maximum_words", "required_parts", "grounding_sentences", "general_practice_grounding",
          "general_practice_sentence", "maximum_description_characters", "forbidden_patterns")
SHORT_REVISION = 7
WORD = re.compile(r"[A-Za-z0-9]")
FRONT_MATTER_FIELDS = ("name", "description")


def word_count(text: str) -> int:
    """The catalogue's word count: every whitespace token that holds a letter or a digit."""
    return sum(1 for token in text.split() if WORD.search(token))


def vocabulary_patterns(settings: dict) -> tuple:
    return tuple(re.compile(pattern, re.IGNORECASE) for pattern in settings["forbidden_patterns"])


class FormatRules:
    kind = "format"
    engine_id = "builtin_format_rules"

    def __init__(self, settings: dict, policy) -> None:
        part = read_part(settings, self.engine_id, FIELDS)
        minimum, maximum = part["minimum_words"], part["maximum_words"]
        if type(minimum) is not int or type(maximum) is not int or not 0 < minimum <= maximum:
            refuse("invalid_precheck_settings", "the word range is two positive whole numbers in order")
        parts = part["required_parts"]
        if type(parts) is not list or not parts or any(type(item) is not str or not item.strip() for item in parts):
            refuse("invalid_precheck_settings", "required_parts is a non-empty list of heading lines")
        sentences = part["grounding_sentences"]
        if type(sentences) is not dict or not sentences or any(
                type(value) is not str or value.count("{revision}") != 1 for value in sentences.values()):
            refuse("invalid_precheck_settings", "each grounding sentence names {revision} once")
        if part["general_practice_grounding"] not in sentences:
            refuse("invalid_precheck_settings", "the general practice grounding is one of the grounding sentences")
        limit = part["maximum_description_characters"]
        if type(limit) is not int or limit < 1:
            refuse("invalid_precheck_settings", "maximum_description_characters is a positive whole number")
        patterns = part["forbidden_patterns"]
        if type(patterns) is not list or any(type(item) is not str or not item for item in patterns):
            refuse("invalid_precheck_settings", "forbidden_patterns is a list of patterns")
        self.minimum, self.maximum, self.parts = minimum, maximum, tuple(parts)
        self.sentences = dict(sentences)
        self.practice_grounding = part["general_practice_grounding"]
        self.practice_sentence = text_field(part["general_practice_sentence"], "general_practice_sentence", limit=400)
        self.description_limit = limit
        try:
            self.vocabulary = vocabulary_patterns(part)
        except re.error:
            refuse("invalid_precheck_settings", "a forbidden pattern is not a valid pattern")
        self.anchors = {grounding: re.compile(re.escape(sentence).replace(re.escape("{revision}"),
                                                                          f"([0-9a-f]{{{SHORT_REVISION}}})"))
                        for grounding, sentence in self.sentences.items()}

    def availability(self):
        return True, "", VERSION

    def check(self, request, context):
        try:
            text = request.body_text
        except CandidateReviewError as error:
            return result_of(self.kind, self.engine_id, VERSION, [(error.code, "the body is not UTF-8 text")])
        findings = []
        lines = text.split("\n")
        if not lines[0].startswith("# ") or not lines[0][2:].strip():
            findings.append(("title_line_missing", "the first line is not one title line"))
        count = word_count(text)
        if not self.minimum <= count <= self.maximum:
            findings.append(("word_count_out_of_range", f"{count} words is outside {self.minimum} to {self.maximum}"))
        missing = [heading for heading in self.parts if heading not in lines]
        if missing:
            findings.append(("required_part_missing", f"missing parts {missing}"))
        findings += self._grounding(request, text)
        findings += self._vocabulary(request, text)
        findings += self._rendered(request)
        return result_of(self.kind, self.engine_id, VERSION, findings)

    def _grounding(self, request, text: str) -> list:
        grounding = request.item.get("provenance", {}).get("grounding")
        if grounding not in self.sentences:
            return [("grounding_unknown", f"the grounding {grounding!r} is not declared")]
        findings = []
        trailing = next((line for line in reversed(text.split("\n")) if line.strip()), "")
        named = {name: pattern.findall(text) for name, pattern in self.anchors.items()}
        own = self.anchors[grounding].findall(trailing)
        if len(own) != 1 or sum(len(found) for found in named.values()) != 1:
            findings.append(("grounding_sentence_mismatch",
                             f"the trailing line must carry exactly one sentence of the grounding {grounding}"))
        elif request.cited_sources and own[0] != request.cited_sources[0].revision[:SHORT_REVISION]:
            findings.append(("anchor_revision_mismatch", "the anchor names another revision than the cited source"))
        if (self.practice_sentence in text) != (grounding == self.practice_grounding):
            findings.append(("practice_sentence_mismatch",
                             "the practice sentence belongs to a body of general practice and to no other"))
        return findings

    def _vocabulary(self, request, text: str) -> list:
        for source in sorted((source.path for source in request.cited_sources), key=len, reverse=True):
            text = text.replace(source, "")
        purpose = str(request.item.get("reference", {}).get("purpose", ""))
        for pattern in self.vocabulary:
            for place, value in (("body", text), ("purpose", purpose), ("identity", request.identity)):
                match = pattern.search(value)
                if match:
                    return [("internal_vocabulary", f"the {place} uses the wording {match.group(0)!r}")]
        return []

    def _rendered(self, request) -> list:
        try:
            name, payload, truncated = rendered_skill(request)
        except CandidateReviewError as error:
            return [(error.code, str(error))]
        if truncated:
            return [("description_too_long",
                     f"the purpose is longer than the {self.description_limit} characters a description holds")]
        header = payload[:len(payload) - len(request.body)].decode("utf-8")
        try:
            front = yaml.safe_load(header.strip().strip("-"))
        except yaml.YAMLError:
            return [("rendered_front_matter_invalid", "the generated front matter does not parse")]
        if type(front) is not dict or tuple(sorted(front)) != tuple(sorted(FRONT_MATTER_FIELDS)) \
                or front.get("name") != name or not str(front.get("description", "")).strip():
            return [("rendered_front_matter_invalid", "the generated front matter is not one name and one description")]
        if len(front["description"]) > self.description_limit:
            return [("description_too_long", "the description is longer than a client accepts")]
        return []
