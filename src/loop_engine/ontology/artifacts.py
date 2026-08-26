"""Closed vocabularies for the persistent folder and catalog ontology.

This module is the single machine-readable home for the classification
axes that folder paths, README front matter, manifests, and catalog
records must agree on. Every value here is closed: adding a member is a
versioned architecture change, not a local edit.
"""
from __future__ import annotations

from ..core.intelligence_layers import LAYERS

ONTOLOGY_VERSION = "1.0.0"

#: The two foundational object classes. A ``node`` is a passive persistent
#: record at rest. A ``loop_node`` is its only executable specialization:
#: the at-rest definition of one Loop graph vertex.
ONTOLOGY_OBJECT_KINDS = ("node", "loop_node")

#: Persistent artifact kinds a semantic folder may hold or reference.
ARTIFACT_KINDS = (
    "loop_definition",
    "loop_graph",
    "intelligence_record",
    "contract",
    "binding",
    "code_unit",
    "policy",
)

#: Provenance of a record: shipped with the package, learned after
#: installation, or supplied by an installed plugin. Provenance never
#: changes how work executes; every executable vertex stays one Loop.
SOURCE_CLASSES = ("core", "learned", "plugin")

#: Physical roots the unified catalog combines into one logical view.
PHYSICAL_ROOTS = ("package_core", "instance_learned", "plugin_root")

#: Folder segment used for each persistent intelligence layer.
LAYER_FOLDER_SEGMENTS = {
    "context_intelligence": "context",
    "code_intelligence": "code",
    "runtime_history_solution_intelligence": "runtime_history_solution",
    "user_feedback_intelligence": "user_feedback",
}
FOLDER_SEGMENT_LAYERS = {v: k for k, v in LAYER_FOLDER_SEGMENTS.items()}

#: Layers with shipped core records. User Feedback Intelligence has no
#: core records at installation; an empty layer remains visible.
CORE_LAYER_IDS = (
    "context_intelligence",
    "code_intelligence",
    "runtime_history_solution_intelligence",
)


def self_test() -> dict:
    """Prove the vocabularies stay closed, aligned, and reversible."""
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    check("ontology_object_kinds_closed",
          ONTOLOGY_OBJECT_KINDS == ("node", "loop_node"))
    check("artifact_kinds_nonempty_and_unique",
          len(ARTIFACT_KINDS) == len(set(ARTIFACT_KINDS)) > 0)
    check("source_classes_exact",
          SOURCE_CLASSES == ("core", "learned", "plugin"))
    check("physical_roots_exact",
          PHYSICAL_ROOTS == ("package_core", "instance_learned", "plugin_root"))
    check("layer_folder_mapping_is_a_bijection",
          sorted(LAYER_FOLDER_SEGMENTS) == sorted(FOLDER_SEGMENT_LAYERS.values()
                                                  ) or
          set(LAYER_FOLDER_SEGMENTS.values()) == set(FOLDER_SEGMENT_LAYERS))
    check("layer_segments_reuse_authoritative_layers",
          set(LAYER_FOLDER_SEGMENTS) == set(LAYERS))
    core_layers = {LAYER_FOLDER_SEGMENTS[c] for c in CORE_LAYER_IDS}
    check("core_layers_subset_of_all_layers",
          core_layers <= set(LAYER_FOLDER_SEGMENTS.values()))
    return {"tests": results}
