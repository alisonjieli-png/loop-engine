"""Intelligence Foundry: generation, multiplication, and composition of
typed intelligence candidates.

Seeds are data. Generation operators are transformations defined as
typed records. Every governed act of generating, composing, evaluating,
selecting, persisting, or promoting runs through ordinary Loops on the
canonical engine. There is no separate generator runtime and no
GeneratorNode class.

Candidates remain candidate-only until an independent review promotes
them. A generator never approves its own output.
"""
from __future__ import annotations

from importlib import import_module as _import_module

_PUBLIC = {
    "CandidateFragment": ("model.fragments", "CandidateFragment"),
    "StringFragment": ("model.fragments", "StringFragment"),
    "PromptBlock": ("model.fragments", "PromptBlock"),
    "ConfigPatch": ("model.fragments", "ConfigPatch"),
    "VariationDimension": ("model.dimensions", "VariationDimension"),
    "GenerationCampaign": ("model.campaign", "GenerationCampaign"),
    "SeedArtifact": ("model.seeds", "SeedArtifact"),
    "expand_variation_space": ("expansion", "expand_variation_space"),
}

__all__ = tuple(_PUBLIC)


def __getattr__(name: str):
    target = _PUBLIC.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module, attribute = target
    return getattr(_import_module(f"{__name__}.{module}"), attribute)


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(_PUBLIC))
