"""Exact identities for a semantic packet preserved inside a harness envelope.

This passive record relates input bytes to the actual provider-facing prompt.
It grants no model, tool, acceptance, or promotion authority.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ModelPromptEnvelopeBinding:
    source_prompt_digest: str
    source_system_digest: str
    source_request_digest: str
    envelope_prompt_digest: str
    envelope_system_digest: str
    envelope_request_digest: str
    semantic_call_id: str
    owner_loop_id: str

    def __post_init__(self):
        for name in ('source_prompt_digest', 'source_system_digest', 'source_request_digest',
                     'envelope_prompt_digest', 'envelope_system_digest', 'envelope_request_digest'):
            value = getattr(self, name)
            if type(value) is not str or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
                raise ValueError('prompt envelope requires exact SHA-256 identities')
        if not self.semantic_call_id or not self.owner_loop_id:
            raise ValueError('prompt envelope requires semantic and owning Loop identities')

    @classmethod
    def bind(cls, source, envelope, owner_loop_id):
        if (source.prompt not in envelope.prompt or source.system != envelope.system
                or source.semantic_call_id != envelope.semantic_call_id):
            raise ValueError('harness envelope changed the original semantic packet')
        return cls(source.prompt_digest, source.system_digest, source.request_digest,
                   envelope.prompt_digest, envelope.system_digest, envelope.request_digest,
                   source.semantic_call_id, owner_loop_id)

    def summary(self):
        return {'record_type': 'model_prompt_envelope/v1', **asdict(self)}

    def matches(self, result, attempt, prompt_digest, semantic_call_id, owner_loop_id):
        return (self.source_prompt_digest == prompt_digest
                and self.source_system_digest == result.system_digest
                and self.source_request_digest == result.request_digest
                and self.envelope_prompt_digest == attempt.prompt_digest
                and self.envelope_system_digest == attempt.system_digest
                and self.envelope_request_digest == attempt.logical_request_digest
                and self.semantic_call_id == semantic_call_id
                and self.owner_loop_id == owner_loop_id)
