"""Which layer a run reached, so a terminal code cannot name one it did not.

A live run on 2026-09-02 was reported `VERIFICATION_FAILED` while its own
record said verification's method was "not completed". Its provider had never
answered: every failure was transport. The two states are different work for
whoever reads the code next, and the difference is between one configuration
fix and a search through the wrong subsystem.

The rule is general and holds for any task, any data, any provider: a
terminal code may only name a layer the run has evidence of having reached.
Where an explicit failure code exists it is authoritative; this is the
fallback that decides what to say when nothing else did.

Owns:
    - deepest_layer_reached(): the layer, from the run's own evidence.

Does not own: the terminal-code vocabulary or the mapping from failure codes
to it (code_nodes.solve_runtime).
"""
from __future__ import annotations

#: Layers a run passes through, shallowest first, with the evidence that it
#: reached each one.
LAYER_EVIDENCE = (("semantic", ("orientations", "action_decisions")),
                  ("execution", ("project_attempts",)))

#: The runtime's own words for "verification never ran".
NOT_VERIFIED = ("", "not completed", "none")

#: Typed fields on a recorded model transaction meaning the provider answered.
#: A provider that answered proves transport succeeded, even when nothing the
#: model said was admitted. Without this a run whose two orientations were
#: both rejected looks identical to one the provider never reached, and the
#: two need entirely different repairs.
RESPONDED_FIELDS = ("provider_responded", "ok")


def deepest_layer_reached(result) -> str:
    """Return the deepest layer this run has evidence of having reached."""
    if not isinstance(result, dict):
        return "transport"
    reached = "transport"
    if any(isinstance(item, dict) and any(item.get(field)
                                          for field in RESPONDED_FIELDS)
           for item in result.get("model_usage") or ()):
        reached = "semantic"
    for layer, fields in LAYER_EVIDENCE:
        if any(result.get(field) for field in fields):
            reached = layer
    check = result.get("verification")
    if isinstance(check, dict) and (
            str(check.get("method") or "").strip().lower() not in NOT_VERIFIED
            or check.get("verdict") or check.get("criteria")):
        reached = "verification"
    return reached


def self_test() -> dict:
    """Prove each layer is recognized only on its own evidence."""
    tests = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    none = {"verification": {"passed": False, "method": "not completed"}}
    some = {"orientations": [{"a": 1}], **none}
    ran = {"orientations": [{"a": 1}], "project_attempts": [{"a": 1}],
           "verification": {"verdict": "repair", "method": "inspection"}}
    check("a_run_whose_provider_never_answered_reached_only_transport",
          deepest_layer_reached(none) == "transport",
          "verification method 'not completed' is not verification")
    # A live run made two calls, the provider answered both, and both
    # orientations were rejected. Nothing was admitted, so no orientation was
    # recorded, and the run looked exactly like one the provider never
    # reached. A recorded provider response says otherwise.
    check("a_provider_that_answered_proves_the_semantic_layer_was_reached",
          deepest_layer_reached(
              {"model_usage": [{"ok": True, "provider_responded": True}],
               "verification": {"method": "not completed"}}) == "semantic"
          and deepest_layer_reached(
              {"model_usage": [{"ok": False}]}) == "transport",
          "an admitted answer is not required; a delivered one is enough")
    check("orientation_alone_is_semantic_work_not_verification",
          deepest_layer_reached(some) == "semantic")
    check("a_verdict_or_a_method_means_verification_ran",
          deepest_layer_reached(ran) == "verification"
          and deepest_layer_reached(
              {"verification": {"verdict": "accept"}}) == "verification")
    check("execution_evidence_is_deeper_than_orientation",
          deepest_layer_reached(
              {"orientations": [{"a": 1}],
               "project_attempts": [{"a": 1}]}) == "execution")
    check("an_absent_or_malformed_record_claims_nothing",
          deepest_layer_reached({}) == "transport"
          and deepest_layer_reached(None) == "transport"
          and deepest_layer_reached({"verification": "not a mapping"})
          == "transport")

    passed = sum(1 for item in tests if item["passed"])
    return {"record_type": "terminal_layer_test/v1", "tests": tests,
            "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
