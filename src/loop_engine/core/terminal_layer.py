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


def deepest_layer_reached(result) -> str:
    """Return the deepest layer this run has evidence of having reached."""
    if not isinstance(result, dict):
        return "transport"
    reached = "transport"
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
