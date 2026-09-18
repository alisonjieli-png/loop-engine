"""The model ontology: what every model route and model-using tool declares.

A reasoning or building step may need a large language model, a small
classifier, an extractor, an embedding model, a vision model, a forecasting
model, a tabular foundation model, a typed-judgment model, or a model this
repository trained on its own records. The engine can only choose among those
as implementations, place them correctly, and record what it used when each
one is declared in the same typed vocabulary. This module owns that vocabulary
and the profile record a route or a tool handshake carries. It grants no
authority and calls no model.

The placement rule the owner set on September 18: a heavy model runs behind a
service boundary, local or remote. A tool may call a model service, and it may
embed only a small in-process model with a declared memory ceiling; it never
loads a large model inside itself. ``validate_tool_model_use`` applies that
rule from the declared size class and placement, not from a guessed threshold.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .facets import DETERMINISM

#: What a model does. One route or tool declares one kind per profile.
MODEL_KINDS = (
    "generative_text", "judgment", "classification", "extraction", "embedding",
    "reranking", "vision", "forecasting", "tabular_foundation", "custom_trained",
)
#: The kinds the existing text gateway can serve without another route.
TEXT_SERVABLE_KINDS = MODEL_KINDS[:4]
#: Where the model's weights run relative to the calling process.
PLACEMENTS = ("in_process", "local_endpoint", "remote_endpoint")
#: How large the model is for placement decisions; a declared class, not a
#: measured byte count.
SIZE_CLASSES = ("in_process_small", "local_service", "remote_service")
#: The size class each placement requires.
PLACEMENT_SIZE_CLASS = dict(zip(PLACEMENTS, SIZE_CLASSES))
#: Where the weights came from.
PROVENANCE_KINDS = ("vendor_foundation", "open_weights", "custom_trained")
#: Input parts a model can accept.
MODALITIES = ("text", "image", "table", "series", "audio", "file")
#: Typed outputs a model can return.
OUTPUT_KINDS = ("text", "structured", "label", "probability", "score", "vector",
                "span", "series")
#: A profile stays a candidate until a different process qualifies it for a
#: purpose; a retired profile is kept for the records that cite it.
QUALIFICATION_STATES = ("candidate", "qualified", "retired")
#: What a tool declares about models: none, a call to a model service, or an
#: embedded small in-process model.
TOOL_MODEL_USES = ("none", "calls_service", "embeds_small")


class ModelOntologyError(ValueError):
    """A profile or a tool declaration violates the ontology."""


@dataclass(frozen=True)
class ModelProfile:
    """The declared classification of one model behind a route or a tool."""

    kind: str
    determinism: str = DETERMINISM[2]
    placement: str = PLACEMENTS[2]
    size_class: str = SIZE_CLASSES[2]
    provenance: str = PROVENANCE_KINDS[0]
    input_modalities: tuple[str, ...] = (MODALITIES[0],)
    output_kinds: tuple[str, ...] = (OUTPUT_KINDS[0],)
    memory_ceiling_mb: int = 0
    hardware: str = ""
    provenance_digest: str = ""
    qualification: str = QUALIFICATION_STATES[0]
    version: str = "1.0.0"

    def __post_init__(self):
        if self.kind not in MODEL_KINDS:
            raise ModelOntologyError(f"model kind must be one of {MODEL_KINDS}")
        if self.determinism not in DETERMINISM:
            raise ModelOntologyError(f"determinism must be one of {DETERMINISM}")
        if self.placement not in PLACEMENTS:
            raise ModelOntologyError(f"placement must be one of {PLACEMENTS}")
        if self.size_class not in SIZE_CLASSES:
            raise ModelOntologyError(f"size class must be one of {SIZE_CLASSES}")
        if PLACEMENT_SIZE_CLASS[self.placement] != self.size_class:
            raise ModelOntologyError(
                f"placement {self.placement!r} requires size class "
                f"{PLACEMENT_SIZE_CLASS[self.placement]!r}")
        if self.provenance not in PROVENANCE_KINDS:
            raise ModelOntologyError(f"provenance must be one of {PROVENANCE_KINDS}")
        modalities = tuple(self.input_modalities)
        outputs = tuple(self.output_kinds)
        if not modalities or any(item not in MODALITIES for item in modalities):
            raise ModelOntologyError(f"input modalities must be drawn from {MODALITIES}")
        if not outputs or any(item not in OUTPUT_KINDS for item in outputs):
            raise ModelOntologyError(f"output kinds must be drawn from {OUTPUT_KINDS}")
        if type(self.memory_ceiling_mb) is not int or self.memory_ceiling_mb < 0:
            raise ModelOntologyError("memory ceiling must be a non-negative integer of megabytes")
        if self.placement == PLACEMENTS[0] and self.memory_ceiling_mb == 0:
            raise ModelOntologyError("an in-process model must declare its memory ceiling")
        if self.qualification not in QUALIFICATION_STATES:
            raise ModelOntologyError(f"qualification must be one of {QUALIFICATION_STATES}")
        if self.provenance == PROVENANCE_KINDS[2] and not self.provenance_digest:
            raise ModelOntologyError("a custom trained model must carry its training record digest")
        for name in ("hardware", "provenance_digest", "version"):
            if not isinstance(getattr(self, name), str):
                raise ModelOntologyError(f"{name} must be text")
        if not self.version.strip():
            raise ModelOntologyError("version must be nonempty text")
        object.__setattr__(self, "input_modalities", modalities)
        object.__setattr__(self, "output_kinds", outputs)

    @property
    def text_servable(self) -> bool:
        """Whether the existing text gateway can serve this kind."""
        return (self.kind in TEXT_SERVABLE_KINDS
                and self.input_modalities == (MODALITIES[0],))

    @property
    def is_service(self) -> bool:
        return self.placement != PLACEMENTS[0]

    def to_dict(self) -> dict:
        return {
            "record_type": "model_profile/v1", "kind": self.kind,
            "determinism": self.determinism, "placement": self.placement,
            "size_class": self.size_class, "provenance": self.provenance,
            "input_modalities": list(self.input_modalities),
            "output_kinds": list(self.output_kinds),
            "memory_ceiling_mb": self.memory_ceiling_mb, "hardware": self.hardware,
            "provenance_digest": self.provenance_digest,
            "qualification": self.qualification, "version": self.version,
        }

    @classmethod
    def from_dict(cls, value) -> "ModelProfile":
        if not isinstance(value, dict) or value.get("record_type") != "model_profile/v1":
            raise ModelOntologyError("a model profile record needs record_type model_profile/v1")
        fields = {key: value[key] for key in (
            "kind", "determinism", "placement", "size_class", "provenance",
            "memory_ceiling_mb", "hardware", "provenance_digest", "qualification",
            "version") if key in value}
        return cls(input_modalities=tuple(value.get("input_modalities") or ()),
                   output_kinds=tuple(value.get("output_kinds") or ()), **fields)


def validate_tool_model_use(model_use: str, profile: "ModelProfile | None") -> str:
    """Apply the placement rule to one tool's declaration and return the use.

    A tool that embeds a model must declare an in-process small profile with a
    memory ceiling. A tool that calls a service must not declare an in-process
    profile. A tool with no model use must not carry a profile.
    """
    if model_use not in TOOL_MODEL_USES:
        raise ModelOntologyError(f"model use must be one of {TOOL_MODEL_USES}")
    if profile is not None and not isinstance(profile, ModelProfile):
        raise ModelOntologyError("a tool's model profile must be a typed ModelProfile")
    if model_use == TOOL_MODEL_USES[0]:
        if profile is not None:
            raise ModelOntologyError("a tool that uses no model must not declare a model profile")
        return model_use
    if model_use == TOOL_MODEL_USES[2]:
        if profile is None or not profile.text_servable and profile.kind == MODEL_KINDS[0]:
            raise ModelOntologyError("an embedded model needs a declared in-process profile")
        if profile.placement != PLACEMENTS[0]:
            raise ModelOntologyError(
                "a tool may embed only an in-process small model; a larger model "
                "runs behind a local or remote service and the tool calls it")
        return model_use
    if profile is not None and profile.placement == PLACEMENTS[0]:
        raise ModelOntologyError(
            "a tool that calls a model service must declare a service placement")
    return model_use


@dataclass(frozen=True)
class ModelProfileMatch:
    """Whether one profile can serve one requested kind and input modalities."""

    profile: ModelProfile
    kind: str
    modalities: tuple[str, ...] = field(default=(MODALITIES[0],))

    @property
    def serves(self) -> bool:
        return (self.profile.kind == self.kind
                and all(item in self.profile.input_modalities for item in self.modalities)
                and self.profile.qualification != QUALIFICATION_STATES[2])


def self_test() -> dict:
    """Vocabulary closure, profile consistency, and the tool placement rule."""
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    def refuses(action):
        try:
            action()
        except ModelOntologyError:
            return True
        return False

    remote = ModelProfile(kind=MODEL_KINDS[0])
    small = ModelProfile(kind=MODEL_KINDS[2], determinism=DETERMINISM[0], placement=PLACEMENTS[0],
                         size_class=SIZE_CLASSES[0], provenance=PROVENANCE_KINDS[2],
                         output_kinds=(OUTPUT_KINDS[2],), memory_ceiling_mb=256,
                         provenance_digest="sha256:fixture")
    vision = ModelProfile(kind=MODEL_KINDS[6], placement=PLACEMENTS[1], size_class=SIZE_CLASSES[1],
                          provenance=PROVENANCE_KINDS[1], input_modalities=(MODALITIES[1],),
                          output_kinds=(OUTPUT_KINDS[2], OUTPUT_KINDS[6]))
    check("a_default_profile_is_a_remote_stochastic_text_model",
          remote.placement == PLACEMENTS[2] and remote.size_class == SIZE_CLASSES[2]
          and remote.text_servable and remote.is_service)
    check("a_vision_profile_is_not_text_servable", not vision.text_servable and vision.is_service)
    check("placement_and_size_class_must_agree",
          refuses(lambda: ModelProfile(kind=MODEL_KINDS[0], placement=PLACEMENTS[0]))
          and refuses(lambda: ModelProfile(kind=MODEL_KINDS[0], placement=PLACEMENTS[2],
                                           size_class=SIZE_CLASSES[0])))
    check("an_in_process_model_declares_its_memory_ceiling",
          refuses(lambda: ModelProfile(kind=MODEL_KINDS[2], placement=PLACEMENTS[0],
                                       size_class=SIZE_CLASSES[0])))
    check("a_custom_trained_model_carries_its_training_digest",
          refuses(lambda: ModelProfile(kind=MODEL_KINDS[9], provenance=PROVENANCE_KINDS[2])))
    check("unknown_vocabulary_values_are_refused",
          all(refuses(action) for action in (
              lambda: ModelProfile(kind="oracle"),
              lambda: ModelProfile(kind=MODEL_KINDS[0], determinism="mostly"),
              lambda: ModelProfile(kind=MODEL_KINDS[0], input_modalities=("thought",)),
              lambda: ModelProfile(kind=MODEL_KINDS[0], output_kinds=()),
              lambda: ModelProfile(kind=MODEL_KINDS[0], qualification="trusted"))))
    check("a_profile_round_trips_through_its_record",
          ModelProfile.from_dict(vision.to_dict()) == vision
          and ModelProfile.from_dict(small.to_dict()) == small
          and refuses(lambda: ModelProfile.from_dict({"kind": MODEL_KINDS[0]})))
    check("a_tool_may_embed_only_a_small_in_process_model",
          validate_tool_model_use(TOOL_MODEL_USES[2], small) == TOOL_MODEL_USES[2]
          and refuses(lambda: validate_tool_model_use(TOOL_MODEL_USES[2], remote))
          and refuses(lambda: validate_tool_model_use(TOOL_MODEL_USES[2], None)))
    check("a_tool_that_calls_a_service_declares_a_service_placement",
          validate_tool_model_use(TOOL_MODEL_USES[1], remote) == TOOL_MODEL_USES[1]
          and validate_tool_model_use(TOOL_MODEL_USES[1], None) == TOOL_MODEL_USES[1]
          and refuses(lambda: validate_tool_model_use(TOOL_MODEL_USES[1], small)))
    check("a_tool_without_a_model_carries_no_profile",
          validate_tool_model_use(TOOL_MODEL_USES[0], None) == TOOL_MODEL_USES[0]
          and refuses(lambda: validate_tool_model_use(TOOL_MODEL_USES[0], remote))
          and refuses(lambda: validate_tool_model_use("sometimes", None)))
    check("a_profile_match_requires_kind_modalities_and_an_unretired_profile",
          ModelProfileMatch(vision, MODEL_KINDS[6], (MODALITIES[1],)).serves
          and not ModelProfileMatch(vision, MODEL_KINDS[6], (MODALITIES[0],)).serves
          and not ModelProfileMatch(remote, MODEL_KINDS[6]).serves
          and not ModelProfileMatch(ModelProfile(kind=MODEL_KINDS[0],
                                                 qualification=QUALIFICATION_STATES[2]),
                                    MODEL_KINDS[0]).serves)
    passed = sum(item["passed"] for item in tests)
    return {"record_type": "model_ontology_test/v1", "tests": tests, "passed": passed,
            "total": len(tests), "all_passed": passed == len(tests)}
