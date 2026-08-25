"""AskFrame — the dimensions always available to a what-is-next ask.

Every time the loop asks "what is next", a bundle of framing dimensions rides
along: the system prompt, the original task, a simplified restatement, the
salient features, a persona, a time period, a purpose, and any salts.  Two
properties matter and are the reason this is its own small type:

- it is **rendered into the prompt** for a model resolver — this is where a
  persona database and a prompt-variation database plug in; and
- it is **available deterministically** even when nothing is sent to a model, so
  a rule-based resolver can read ``frame.persona`` or ``frame.time_period`` and
  branch on it.

A persona / prompt database is therefore just a store of ``AskFrame`` presets,
sampled (e.g. by the hybrid-dimension lattice) and slotted into each ask.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict


@dataclass
class AskFrame:
    system_prompt: str = ""
    original_task: str = ""
    simplified_task: str = ""
    features: tuple[str, ...] = ()
    persona: str = ""
    time_period: str = ""
    purpose: str = ""
    salts: tuple[str, ...] = ()
    # Namespaced extra dimensions a caller wants always-available without
    # changing this contract (survives round trips; never silently dropped).
    extra: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {k: (list(v) if isinstance(v, tuple) else v)
                for k, v in asdict(self).items()}

    def render_prompt_preamble(self) -> str:
        """The frame as a compact prompt preamble for a model resolver.  Empty
        dimensions are omitted, so a blind frame renders to almost nothing."""
        parts = []
        if self.system_prompt:
            parts.append(self.system_prompt)
        if self.persona:
            parts.append(f"Adopt the lens of: {self.persona}.")
        if self.time_period:
            parts.append(f"Reason as of: {self.time_period}.")
        if self.simplified_task:
            parts.append(f"Task (plain): {self.simplified_task}")
        elif self.original_task:
            parts.append(f"Task: {self.original_task}")
        if self.purpose:
            parts.append(f"Purpose: {self.purpose}")
        if self.features:
            parts.append("Salient features: " + ", ".join(self.features))
        for salt in self.salts:
            parts.append(f"Consider: {salt}")
        return "\n".join(parts)
