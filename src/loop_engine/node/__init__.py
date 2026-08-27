"""The Node ontology namespace.

# HARD ARCHITECTURE INVARIANT - DO NOT REMOVE OR WEAKEN:
#
# Every executable graph vertex runs as the canonical Loop runtime.
#
# Never add:
# - a generic concrete Node class;
# - another concrete Node subtype;
# - PractitionerNode, IntelligenceNode, or SolutionNode classes;
# - RootNode, ChildNode, CodeNode, ToolNode, ModelNode, or CapabilityNode classes;
# - deterministic, hybrid, or non-deterministic Node subclasses;
# - a plugin-defined Node kind;
# - a second node executor or node runtime.
#
# Objects that do not execute are records, definitions, canvases, contracts,
# rules, policies, standardizations, profiles, references, resources, artifacts,
# results, evidence, evaluations, governance events, or materializations.
# They are not Nodes.
#
# Common behaviors are represented by versioned passive Loop profiles.
"""
from __future__ import annotations

__all__: tuple[str, ...] = ()
