"""What a layering space can execute today, address by address.

An enumerable space is not an executable one. For one adapter, every
address of a ``LayeringSpace`` falls into exactly one state, decided by the
same rule ``HarnessSemanticBinding`` applies at construction: the run's
outer policy refuses it, no executor runs a layered composition, the
adapter does not declare a natively owned control, the adapter declares it
but no executor hands it over yet, or it executes now (the direct adapter
with every control owned by the Loop). A search reads the projection before
proposing, so an unavailable setting stays visible with its reason instead
of being proposed as if it could run, and a summary is counted without
enumerating the compositions, since every rule here depends on the policy
and on whether the composition has layers.
"""
from __future__ import annotations

from .harness_layering import HarnessLayeringError, LayeredHarnessBinding, NativeControl
from .harness_layering_space import LayeringSpace

EXECUTABLE_NOW = "executable_now"
OUTER_POLICY_REFUSES = "outer_policy_refuses"
COMPOSITION_WITHOUT_EXECUTOR = "composition_without_executor"
ADAPTER_DOES_NOT_DECLARE = "adapter_does_not_declare"
DECLARED_WITHOUT_EXECUTOR = "declared_without_executor"
STATES = (EXECUTABLE_NOW, OUTER_POLICY_REFUSES, COMPOSITION_WITHOUT_EXECUTOR,
          ADAPTER_DOES_NOT_DECLARE, DECLARED_WITHOUT_EXECUTOR)
AVAILABILITY_RECORD_TYPE = "harness_layering_availability/v1"


def _controls(adapter_native_controls) -> tuple[str, ...]:
    if adapter_native_controls is None:
        return ()
    if isinstance(adapter_native_controls, str) or not all(
            isinstance(item, str) for item in adapter_native_controls):
        raise HarnessLayeringError("adapter native controls are a sequence of control names")
    names = {item.value for item in NativeControl}
    unknown = sorted(set(adapter_native_controls) - names)
    if unknown:
        raise HarnessLayeringError(f"unknown native controls {unknown}")
    return tuple(dict.fromkeys(adapter_native_controls))


def executor_refusal(binding: LayeredHarnessBinding, harness_id: str,
                     adapter_native_controls=()) -> tuple[str, str]:
    """The state one validated binding is in for the adapter named, with the
    exact reason the semantic binding would raise. ``executable_now`` has
    an empty reason. A declaration is not an implementation: wrappers and
    native controls that no registered executor implements are refused."""
    if not isinstance(binding, LayeredHarnessBinding):
        raise HarnessLayeringError("executor refusal needs a typed LayeredHarnessBinding")
    declared = set(_controls(adapter_native_controls))
    if binding.initial.layers:
        return (COMPOSITION_WITHOUT_EXECUTOR,
                'no executor is registered for a layered composition; only the '
                'direct adapter (an empty composition) can run today')
    natively = binding.control_policy.natively_owned()
    if not natively:
        return EXECUTABLE_NOW, ""
    unsupported = [item.value for item in natively if item.value not in declared]
    if unsupported:
        return (ADAPTER_DOES_NOT_DECLARE,
                f'adapter {harness_id!r} does not support native ownership '
                f'of {unsupported}; its declared native controls are {sorted(declared)}')
    return (DECLARED_WITHOUT_EXECUTOR,
            'the direct adapter implements owning-Loop control for every native '
            f'control; {[item.value for item in natively]} is declared by the '
            'adapter but no executor hands it to the harness yet')


def classify_address(space: LayeringSpace, index: int, adapter_native_controls=()) -> dict:
    """One address's state and reason. The outer policy is consulted first,
    since a refused address never becomes a binding at all."""
    if not isinstance(space, LayeringSpace):
        raise HarnessLayeringError("classification needs a typed LayeringSpace")
    declared = _controls(adapter_native_controls)
    try:
        binding = space.candidate_at(index)
    except HarnessLayeringError as exc:
        if type(index) is not int or isinstance(index, bool) or not 0 <= index < space.size:
            raise
        return {"index": index, "state": OUTER_POLICY_REFUSES, "reason": str(exc)}
    state, reason = executor_refusal(binding, space.compositions.harness_id, declared)
    return {"index": index, "state": state, "reason": reason}


def availability_summary(space: LayeringSpace, adapter_native_controls=()) -> dict:
    """Counts per state over the whole space, computed from the policies and
    the composition count alone. Every rule depends on the policy and on
    whether the composition has layers, and only index 0 of the composition
    space has none, so the compositions are never walked. The executable
    addresses are listed exactly: the direct adapter under every policy with
    no natively owned control (owning-Loop or disabled for each control), at
    most 2 ** 8 of them."""
    if not isinstance(space, LayeringSpace):
        raise HarnessLayeringError("an availability summary needs a typed LayeringSpace")
    declared = _controls(adapter_native_controls)
    compositions = space.compositions.size
    counts = {state: 0 for state in STATES}
    executable = []
    for policy_index in range(space.policies.size):
        direct = space.encode(0, policy_index)
        row = classify_address(space, direct, declared)
        if row["state"] == OUTER_POLICY_REFUSES:
            counts[OUTER_POLICY_REFUSES] += compositions
            continue
        counts[row["state"]] += 1
        counts[COMPOSITION_WITHOUT_EXECUTOR] += compositions - 1
        if row["state"] == EXECUTABLE_NOW:
            executable.append(direct)
    if sum(counts.values()) != space.size:
        raise HarnessLayeringError("availability counts do not cover the space")
    outer = space.fallback_policy
    return {"record_type": AVAILABILITY_RECORD_TYPE,
            "layering_space_digest": space.content_digest, "size": space.size,
            "harness_id": space.compositions.harness_id,
            "adapter_native_controls": list(declared),
            "outer_policy_allows_native_retry": bool(outer is not None and outer.allow_native_retry),
            "executors_registered": {"direct_adapter": True, "wrapper_layers": False,
                                     "native_controls": []},
            "counts": counts, "executable_now_indices": executable}


def self_test() -> dict:
    from .harness_layering_availability_checks import run_checks
    return run_checks()
