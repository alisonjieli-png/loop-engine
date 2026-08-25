"""Research-to-capability — a model naming a package is not an executable node.

When the swarm hits a capability it cannot satisfy from the registry, it may
research: ask which packages, methods, papers, or algorithms solve this, and get
back a ranked list (which ``list_intelligence`` archives).  The v2 specification
(A11, A12) is emphatic about what that list is and is not: a package name a model
returned is a *nomination*, not an executable node.  It becomes usable only after
a verification ladder confirms it exists, its licence permits the use, its API
was inspected, and a capability contract was derived from it — and only then does
it enter the forge (for a wrapper) or become a reference record (for a public
package).  This module is that ladder, with the states kept strictly separate so
one can never be mistaken for another (SN-A028):

    nominated → existence_verified → license_verified → api_inspected
              → contract_derived → (forge a wrapper | record a reference)

Reuse comes before research here too: if a registered node already satisfies the
capability, no research runs.  The actual checks (does the package exist on the
index, what licence, what API surface) need network and package access, so this
module does not perform them — it *sequences and gates* them, taking each gate's
verdict from the caller (or a verifier plugged in behind a typed interface).
What it guarantees is that no finding is marked executable until every gate has
passed, and that a finding blocked at any gate becomes a named capability gap
recording exactly where it stopped — never a silent "the model said it works."

Run: ``python -m loop_engine.loop.research_to_capability --self-test``.
Architectural role: Practitioner Loop.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

# The verification ladder, in order.  Each gate must pass before the next runs.
VERIFICATION_LADDER = ("existence", "license", "api_surface", "contract")

# What a finding can be — kept distinct so a paper is never treated as a package.
FINDING_KINDS = ("package", "method", "paper", "algorithm", "standard")


@dataclass(frozen=True)
class ResearchFinding:
    """One nominated item a model returned for a capability need."""
    kind: str                       # one of FINDING_KINDS
    name: str
    capability: str                 # the capability need it claims to satisfy
    source: str = ""                # where the nomination came from
    claim: str = ""                 # what it is claimed to do
    ecosystem: str = ""             # e.g. "pypi", "npm" (for packages)


@dataclass(frozen=True)
class GateOutcome:
    """A caller-supplied verdict for one verification gate."""
    gate: str
    passed: bool
    detail: str = ""
    # Payload a gate may return (a derived contract from the contract gate, the
    # inspected api surface, the resolved licence id).
    payload: Any = None


# A verifier answers one gate for one finding.  Real verifiers do network/pip
# work; the self-test supplies pure ones.
Verifier = Callable[[ResearchFinding, str, Mapping[str, Any]], GateOutcome]


@dataclass
class ResearchOutcome:
    resolution: str                 # reuse | verified | named_gap
    capability: str
    finding_name: str = ""
    finding_kind: str = ""
    reused_node: str = ""
    gates: list[GateOutcome] = field(default_factory=list)
    blocked_at: str = ""
    derived_contract: Any = None
    # A verified finding is a CANDIDATE for the forge or a reference — never
    # trusted here.
    next_step: str = ""             # "forge_wrapper" | "record_reference" | ""
    executable: bool = False        # always False until forge/foundry gates pass

    def to_dict(self) -> dict:
        out = {"record_type": "research_to_capability_outcome/v1",
               "resolution": self.resolution, "capability": self.capability,
               "gates": [{"gate": g.gate, "passed": g.passed,
                          "detail": g.detail} for g in self.gates],
               "executable": self.executable,
               "the_rule": ("a nominated package/method/paper is verified "
                            "through existence→license→api→contract before it is "
                            "usable, and is a CANDIDATE for the forge or a "
                            "reference even then — never executable by a model's "
                            "say-so")}
        if self.reused_node:
            out["reused_node"] = self.reused_node
        if self.finding_name:
            out["finding"] = {"name": self.finding_name,
                              "kind": self.finding_kind}
        if self.blocked_at:
            out["blocked_at"] = self.blocked_at
        if self.next_step:
            out["next_step"] = self.next_step
        return out


def resolve_capability(finding: ResearchFinding, *,
                       registry: Mapping[str, Sequence[str]] | None = None,
                       verifiers: Mapping[str, Verifier] | None = None,
                       context: Mapping[str, Any] | None = None
                       ) -> ResearchOutcome:
    """Reuse if possible, else walk the verification ladder for one finding.

    ``verifiers`` maps a gate name to a verifier that returns its GateOutcome.
    A missing verifier for a required gate blocks the finding at that gate (fail
    closed — an unverifiable claim is not a verified one).
    """
    registry = registry or {}
    verifiers = verifiers or {}
    ctx = dict(context or {})

    # Reuse before research.
    existing = registry.get(finding.capability)
    if existing:
        return ResearchOutcome(
            resolution="reuse", capability=finding.capability,
            reused_node=existing[0],
            gates=[GateOutcome("reuse_ladder", True,
                               f"existing node {existing[0]!r} satisfies the "
                               f"capability; no research run")])

    gates: list[GateOutcome] = []
    derived_contract = None
    for gate in VERIFICATION_LADDER:
        verifier = verifiers.get(gate)
        if verifier is None:
            gates.append(GateOutcome(gate, False,
                                     f"no verifier for {gate!r}; cannot confirm "
                                     f"— fail closed"))
            return ResearchOutcome(
                resolution="named_gap", capability=finding.capability,
                finding_name=finding.name, finding_kind=finding.kind,
                gates=gates, blocked_at=gate)
        outcome = verifier(finding, gate, ctx)
        gates.append(outcome)
        if not outcome.passed:
            return ResearchOutcome(
                resolution="named_gap", capability=finding.capability,
                finding_name=finding.name, finding_kind=finding.kind,
                gates=gates, blocked_at=gate)
        if gate == "contract":
            derived_contract = outcome.payload

    # Every gate passed → a verified capability, routed to the forge (for a
    # package/algorithm that needs a wrapper) or a reference record (for a
    # public package used by contract).  Still not executable here.
    next_step = ("record_reference" if finding.kind in ("paper", "standard")
                 else "forge_wrapper")
    return ResearchOutcome(
        resolution="verified", capability=finding.capability,
        finding_name=finding.name, finding_kind=finding.kind, gates=gates,
        derived_contract=derived_contract, next_step=next_step,
        executable=False)


def resolve_ranked(findings: Sequence[ResearchFinding], **kwargs
                   ) -> dict:
    """Run a whole ranked research list (as ``list_intelligence`` would archive)
    through the ladder, returning the outcomes and a compact tally so the caller
    sees how many nominations actually became verified capabilities vs named
    gaps — the honest yield of a research list."""
    outcomes = [resolve_capability(f, **kwargs) for f in findings]
    tally = {"reuse": 0, "verified": 0, "named_gap": 0}
    for o in outcomes:
        tally[o.resolution] = tally.get(o.resolution, 0) + 1
    return {"record_type": "research_list_resolution/v1",
            "nominated": len(findings), "tally": tally,
            "outcomes": [o.to_dict() for o in outcomes],
            "note": ("of N model-nominated findings, only the 'verified' ones "
                     "cleared every gate; the rest are named gaps recording "
                     "where they stopped — a research list's honest yield")}


# ---------------------------------------------------------------------------
# Self-test — deterministic, no model, no network.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    finding = ResearchFinding(
        kind="package", name="imbalanced-learn",
        capability="transform.resample_imbalanced", ecosystem="pypi",
        source="swarm research list", claim="fold-safe resampling")

    # Verifiers that all pass, with the contract gate returning a derived
    # contract.
    def ok_verifier(f, gate, ctx):
        payload = ({"inputs": "X,y", "outputs": "X',y'"}
                   if gate == "contract" else None)
        return GateOutcome(gate, True, f"{gate} ok", payload=payload)

    all_ok = {g: ok_verifier for g in VERIFICATION_LADDER}

    # Reuse before research.
    reused = resolve_capability(finding, registry={
        "transform.resample_imbalanced": ["registered_resampler"]},
        verifiers=all_ok)
    check("reuse_before_research_short_circuits_the_ladder",
          reused.resolution == "reuse"
          and reused.reused_node == "registered_resampler"
          and all(g.gate == "reuse_ladder" for g in reused.gates),
          "when a registered node already satisfies the capability the ladder "
          "is skipped entirely — reuse beats research")

    # Full verification yields a verified (but not executable) capability.
    verified = resolve_capability(finding, registry={}, verifiers=all_ok)
    check("full_verification_yields_verified_but_not_executable",
          verified.resolution == "verified" and verified.executable is False
          and verified.next_step == "forge_wrapper"
          and verified.derived_contract == {"inputs": "X,y",
                                            "outputs": "X',y'"}
          and [g.gate for g in verified.gates] == list(VERIFICATION_LADDER),
          "a package that clears existence→license→api→contract becomes a "
          "VERIFIED capability with a derived contract, routed to the forge — "
          "but executable stays False; the forge/foundry gates decide that")

    # A finding blocked at the licence gate becomes a named gap AT licence.
    def license_blocks(f, gate, ctx):
        if gate == "license":
            return GateOutcome(gate, False, "GPL incompatible with policy")
        return GateOutcome(gate, True, f"{gate} ok")
    blocked = resolve_capability(
        finding, registry={},
        verifiers={g: license_blocks for g in VERIFICATION_LADDER})
    check("a_finding_blocked_at_a_gate_becomes_a_named_gap_at_that_gate",
          blocked.resolution == "named_gap" and blocked.blocked_at == "license"
          and not blocked.executable
          and [g.gate for g in blocked.gates] == ["existence", "license"],
          "a package that exists but fails the licence gate stops there and "
          "becomes a named gap recording licence as the blocker — it never "
          "proceeds to api/contract, and is never marked usable")

    # A missing verifier fails closed (an unverifiable claim is not verified).
    fail_closed = resolve_capability(finding, registry={},
                                     verifiers={"existence": ok_verifier})
    check("a_missing_verifier_fails_closed",
          fail_closed.resolution == "named_gap"
          and fail_closed.blocked_at == "license",
          "with no licence verifier available the finding fails closed at the "
          "licence gate — an unverifiable claim is a named gap, not a verified "
          "capability")

    # A ranked list's honest yield: mixed nominations tally correctly.
    good = finding
    bad = ResearchFinding("package", "abandonware", "transform.x", "pypi")
    def existence_blocks(f, gate, ctx):
        if f.name == "abandonware" and gate == "existence":
            return GateOutcome(gate, False, "not found on index")
        payload = ({"c": 1} if gate == "contract" else None)
        return GateOutcome(gate, True, "ok", payload=payload)
    listed = resolve_ranked([good, bad], registry={},
                            verifiers={g: existence_blocks
                                       for g in VERIFICATION_LADDER})
    check("a_research_lists_honest_yield_is_tallied",
          listed["nominated"] == 2 and listed["tally"]["verified"] == 1
          and listed["tally"]["named_gap"] == 1,
          "of two model-nominated packages, one clears every gate (verified) "
          "and one fails existence (named gap); the tally reports the list's "
          "real yield rather than treating all nominations as capabilities")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "research_to_capability_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        report = self_test()
        print(json.dumps(report, indent=1))
        return 0 if report["all_passed"] else 1
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
