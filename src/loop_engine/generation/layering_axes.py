"""Harness layering as axes of an indexed configuration space.

Wrapper composition and native-control ownership are enumerable and
indexable in ``core.harness_layering_space``. This module lets every
proposal adapter (exact enumeration, seeded exploration, Bayesian, genetic,
covariance, warm start) address them alongside the other dimensions of a
search: the two layering spaces become two ``integer_range`` axes whose
values are exact indices, a fixed context field binds each configuration
to the digest of the layering space it was addressed in, and every address
decodes back to the validated ``LayeredHarnessBinding`` it names.

Admissibility under the run's outer fallback policy is not a value-equality
rule, so ``ConfigurationSpace.exclusions`` cannot express it. It is reported
per address by ``layering_exclusions`` in the same form, and a proposal
batch can be filtered by ``refuse_inadmissible_proposals`` without changing
the proposal record the search wrote. Nothing here executes a wrapper or a
native control: index 0 on both axes is the direct adapter with the owning
Loop, the path every current recipe runs.
"""
from __future__ import annotations

from ..core.harness_layering import HarnessLayeringError, LayeredHarnessBinding
from ..core.harness_layering_space import LayeringSpace
from .model.fragments import GenerationError
from .space import ConfigurationAxis, ConfigurationSpace, canonical

POLICY_DIMENSION = "harness_layering.control_policy_index"
COMPOSITION_DIMENSION = "harness_layering.composition_index"
SPACE_DIGEST_FIELD = "harness_layering.space_digest"
INADMISSIBLE_RULE = "harness_layering.outer_policy_refuses"
FILTER_RECORD_TYPE = "configuration_search_layering_filter/v1"


def _typed_space(space) -> LayeringSpace:
    if not isinstance(space, LayeringSpace):
        raise GenerationError("layering axes need a typed LayeringSpace")
    return space


def _exact_index(value, name) -> int:
    if type(value) is not int or isinstance(value, bool):
        raise GenerationError(f"{name} must be an exact integer address")
    return value


def layering_axes(space: LayeringSpace) -> tuple[ConfigurationAxis, ConfigurationAxis]:
    """The control-policy axis first and the composition axis last, so a
    configuration space holding only these two axes gives every address the
    same integer ``LayeringSpace.decode`` gives it: the composition is the
    least significant digit in both."""
    space = _typed_space(space)
    return (ConfigurationAxis(POLICY_DIMENSION, "integer_range",
                              minimum=0, maximum=space.policies.size - 1),
            ConfigurationAxis(COMPOSITION_DIMENSION, "integer_range",
                              minimum=0, maximum=space.compositions.size - 1))


def layering_context(space: LayeringSpace) -> dict:
    """The fixed context field that binds a configuration to its layering
    space. A configuration carrying another digest is refused on decode."""
    return {SPACE_DIGEST_FIELD: _typed_space(space).content_digest}


def layering_configuration_space(space: LayeringSpace, space_id: str, *,
                                 extra_axes: tuple = (), context: dict | None = None,
                                 rules: tuple = ()) -> ConfigurationSpace:
    """A configuration space whose first two axes are the layering axes and
    whose remaining axes are the caller's. The caller's fixed context and
    conditional rules pass through unchanged; the layering digest field is
    added to the context and cannot be overridden."""
    space = _typed_space(space)
    fixed = dict(context or {})
    if not isinstance(fixed, dict) or SPACE_DIGEST_FIELD in fixed:
        raise GenerationError("the layering digest field is owned by the layering space")
    fixed.update(layering_context(space))
    return ConfigurationSpace(space_id, "1.0.0", layering_axes(space) + tuple(extra_axes),
                              canonical(fixed), canonical(list(rules)))


def layering_index(space: LayeringSpace, configuration: dict) -> int:
    """The ``LayeringSpace`` index one configuration addresses. A
    configuration addressed in a different layering space, or one missing
    either axis, is refused rather than decoded against the wrong table."""
    space = _typed_space(space)
    if not isinstance(configuration, dict):
        raise GenerationError("a configuration is a mapping of dimension values")
    if configuration.get(SPACE_DIGEST_FIELD) != space.content_digest:
        raise GenerationError("configuration was addressed in a different layering space")
    if POLICY_DIMENSION not in configuration or COMPOSITION_DIMENSION not in configuration:
        raise GenerationError("configuration lacks a layering axis")
    policy = _exact_index(configuration[POLICY_DIMENSION], "control policy index")
    composition = _exact_index(configuration[COMPOSITION_DIMENSION], "composition index")
    try:
        return space.encode(composition, policy)
    except HarnessLayeringError as exc:
        raise GenerationError(str(exc)) from exc


def layering_binding(space: LayeringSpace, configuration: dict) -> LayeredHarnessBinding:
    """The validated binding a configuration names. An address the outer
    fallback policy refuses raises here, exactly as a hand-written binding
    would; use ``layering_exclusions`` to report it instead of raising."""
    index = layering_index(space, configuration)
    try:
        return space.candidate_at(index)
    except HarnessLayeringError as exc:
        raise GenerationError(str(exc)) from exc


def layering_fields(space: LayeringSpace, binding: LayeredHarnessBinding) -> dict:
    """The configuration fields that address one binding in this space, or a
    refusal when the space cannot produce that binding (a composition
    outside the catalogue or depth, an ownership the adapter did not
    declare)."""
    space = _typed_space(space)
    if not isinstance(binding, LayeredHarnessBinding):
        raise GenerationError("layering fields need a typed LayeredHarnessBinding")
    try:
        return {**layering_context(space),
                POLICY_DIMENSION: space.policies.index_of(binding.control_policy),
                COMPOSITION_DIMENSION: space.compositions.index_of(binding.initial)}
    except HarnessLayeringError as exc:
        raise GenerationError(str(exc)) from exc


def layering_exclusions(space: LayeringSpace, configuration: dict) -> tuple[str, ...]:
    """Rule identities excluding one address, in the form
    ``ConfigurationSpace.exclusions`` uses. Only admissibility under the
    outer fallback policy lives here; a configuration that does not address
    this space at all is an error, not an exclusion."""
    index = layering_index(space, configuration)
    return () if space.admissible(index) else (INADMISSIBLE_RULE,)


def iter_admissible(space: LayeringSpace, configuration_space: ConfigurationSpace, *,
                    start: int = 0, stride: int = 1):
    """Walk one declared shard lazily, yielding only addresses that both the
    space's conditional rules and the outer fallback policy admit, with
    their exact address identity retained."""
    if not isinstance(configuration_space, ConfigurationSpace):
        raise GenerationError("iter_admissible walks a typed ConfigurationSpace")
    for index, configuration in configuration_space.iter_configurations(start=start, stride=stride):
        if not layering_exclusions(space, configuration):
            yield index, configuration


def refuse_inadmissible_proposals(space: LayeringSpace, batch: dict) -> dict:
    """Split one proposal batch's proposals by the outer fallback policy.
    The search's own record is not altered: this returns a separate record
    naming the batch, the layering space, the proposals that remain
    admissible, and the ones refused with the rule that refused them. It
    performs no execution and no promotion."""
    space = _typed_space(space)
    if not isinstance(batch, dict) or not isinstance(batch.get("proposals"), list):
        raise GenerationError("a proposal batch record with a proposals list is required")
    admissible, refused = [], []
    for proposal in batch["proposals"]:
        if not isinstance(proposal, dict) or not isinstance(proposal.get("configuration"), dict):
            raise GenerationError("each proposal carries its configuration")
        reasons = layering_exclusions(space, proposal["configuration"])
        (refused if reasons else admissible).append(
            {**proposal, "layering_reasons": list(reasons)} if reasons else proposal)
    return {"record_type": FILTER_RECORD_TYPE,
            "request_digest": batch.get("request_digest"),
            "space_digest": batch.get("space_digest"),
            "layering_space_digest": space.content_digest,
            "proposals": admissible, "refused_proposals": refused,
            "admissible_count": len(admissible), "refused_count": len(refused),
            "task_execution_performed": False, "promotion_performed": False}


def self_test() -> dict:
    from .layering_axes_checks import run_checks
    return run_checks()
