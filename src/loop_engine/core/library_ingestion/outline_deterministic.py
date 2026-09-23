"""Engine deterministic_outline of the library_outline engine slot.

For a source whose licence permits no copy, an outline keeps what a later
original rewrite needs and nothing of the author's expression: the source
identity (provenance), the item's name as an identifier, and topic words
from the closed list. The abstract purpose is a sentence of this engine's
own template. Before an outline is returned, it is compared with the source
text, and an outline that repeats any run of five words from the source is
refused with outline_would_copy_source_text. A source whose licence forbids
derivative works never reaches this engine.
"""
from __future__ import annotations

from .candidates import OUTLINE_RECORD_TYPE, read_outline
from .duplicates import normalized
from .record_rules import canonical_digest
from .rendering_types import RenderRefused
from .topics import topic_words

OVERLAP_WORDS = 5
_KIND_WORDS = {"skill": "skill", "instruction_file": "instruction file", "tool": "connection file"}


def copies_source(outline_text: str, source_text: str, size: int = OVERLAP_WORDS) -> bool:
    """True when the outline repeats any run of `size` words from the source."""
    source = normalized(source_text).split()
    runs = {" ".join(source[index:index + size]) for index in range(len(source) - size + 1)}
    words = normalized(outline_text).split()
    return any(" ".join(words[index:index + size]) in runs for index in range(len(words) - size + 1))


class DeterministicOutline:
    """A template outline: the identity, the name as an identifier and closed-list topics."""

    engine_id = "deterministic_outline"
    engine_version = "1.0.0"
    engine_kind = "outline_writer"
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
                "overlap_words": OVERLAP_WORDS}

    def outline(self, candidate: dict, source_text: str) -> dict:
        provenance = candidate["provenance"]
        name = candidate["name"]
        topics = topic_words(name, source_text[:4000])
        kind = _KIND_WORDS[candidate["kind"]]
        about = ", ".join(topics) if topics else "the task its name describes"
        purpose = (f"Write an original {kind} about {about}, with the same general aim as the {kind} "
                   f"named {name} in {provenance['repository']}. Use no sentence, list or example "
                   "from the source.")
        if copies_source(purpose, source_text):
            raise RenderRefused("outline_would_copy_source_text", "the template repeats five source words")
        record = {"record_type": OUTLINE_RECORD_TYPE,
                  "outline_key": canonical_digest({"candidate": candidate["candidate_key"],
                                                   "engine": self.engine_id, "version": self.engine_version}),
                  "kind": candidate["kind"], "native_format": candidate["native_format"],
                  "source_name": name[:128], "topic_words": topics, "abstract_purpose": purpose[:600],
                  "provenance": provenance,
                  "generator": {"engine_id": self.engine_id, "engine_version": self.engine_version},
                  "text_included": False, "model_calls": []}
        return read_outline(record)
