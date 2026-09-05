"""Whether response shapes are converging, or only being told to.

There is an obvious way to be fooled here. The system offers a template. Calls
use it, because it was offered. The record fills with agreement. Concentration
rises, entropy falls, and it looks as though a shape has been discovered when
what has happened is that one was suggested and adopted. A shortcut fitted to
that record would encode the suggestion, not the finding, and would keep
encoding it as the evidence base grew.

The only defence that works is one built before the data exists: a share of
independent occurrences must be answered with no template offered at all.
Those are the control arm. If response shapes converge there too, the
convergence is in the work. If they converge only where a template was shown,
the convergence is in the showing. Adding a control arm later cannot rescue a
record already collected without one.

Assignment is deterministic from the experiment, semantic signature, exact
occurrence, and campaign seed. Retries of one occurrence stay in one arm,
while later occurrences of the same semantic situation may enter either arm.

This module only assigns an arm and summarizes labels supplied by its caller.
It does not alter a work packet. A caller has not created a control merely by
recording this assignment, and a response-shape analysis is invalid when the
caller supplies an input-stage shape instead of the observed response shape.

Nothing here decides that a shape is good. When a caller applies the assigned
exposure and supplies observed response shapes, this module can summarize
agreement, control-arm agreement, and novelty. Without those caller actions,
its output is assignment bookkeeping rather than convergence evidence.

Owns:
    - experiment_arm(): which arm one occurrence belongs to, decided
      before anything is offered to it.
    - ConvergenceMeasure: concentration, entropy, novelty, per arm.

Does not own: templates, the offer, or the choice made from it.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field

CONVERGENCE_RECORD_TYPE = "response_shape_convergence/v1"

#: The arms. `offered` sees candidate templates; `control` sees none and must
#: describe its own shape.
OFFERED, CONTROL = "offered", "control"

#: Share of stages answered with no template offered. Large enough that the
#: control arm can be read on its own, small enough that most work still gets
#: the benefit of prior shapes. This is a design choice, not a measurement,
#: and it is stated here rather than buried so it can be argued with.
CONTROL_ARM_SHARE = 0.15

#: Below this the arm has too few observations to compare. Reported rather
#: than used to suppress: a reader should see that a number is thin, not be
#: shown nothing.
_THIN_ARM = 20


#: Experiments this assignment can serve. Named because a stage may be in
#: the control arm of one and the treated arm of another, and an assignment
#: that cannot say which experiment it belongs to silently entangles them.
TEMPLATE_OFFER, CACHE_ASSIST, MODEL_ROUTE = (
    "template_offer", "cache_assist", "model_route")


def experiment_arm(experiment: str, signature: str, occurrence: str,
                   *, seed: str = "", share: float = CONTROL_ARM_SHARE) -> str:
    """Which arm this occurrence belongs to, decided before anything is shown.

    The occurrence is what makes the comparison possible. An earlier version
    assigned from the stage signature alone, which meant a stage region
    landed in the same arm forever: the treated and control arms could never
    contain the same kind of work, so the one question worth asking — what
    happens to *this* region with help and without — was unanswerable by
    construction. It looked like a control arm and could not control for
    anything.

    Including the occurrence lets independent activations of one region fall
    on both sides, while every retry of a single activation stays put, so a
    run cannot walk itself into the other arm by failing. The signature stays
    in the hash so assignment is stable per region-and-occurrence rather than
    purely random, and the seed lets a campaign re-randomise without changing
    any code.
    """
    if not 0.0 <= share <= 1.0:
        raise ValueError("the control share must be between 0 and 1")
    if share == 0.0:
        return OFFERED
    if share == 1.0:
        return CONTROL
    material = "\u0000".join(
        (str(experiment), str(signature), str(occurrence), str(seed)))
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()
    position = int(digest[-8:], 16) / 0xFFFFFFFF
    return CONTROL if position < share else OFFERED


@dataclass
class ConvergenceMeasure:
    """How much response shapes agree, and how much of that was prompted."""

    control_arm_share: float = CONTROL_ARM_SHARE
    thin_arm_observations: int = _THIN_ARM
    #: shape identity -> count, per arm.
    shapes: dict = field(default_factory=lambda: {OFFERED: {}, CONTROL: {}})
    novel_fields: dict = field(default_factory=lambda: {OFFERED: 0,
                                                        CONTROL: 0})
    departures: dict = field(default_factory=lambda: {OFFERED: 0, CONTROL: 0})

    def __post_init__(self) -> None:
        if not 0.0 <= float(self.control_arm_share) <= 1.0:
            raise ValueError("the control share must be between 0 and 1")
        if (isinstance(self.thin_arm_observations, bool)
                or not isinstance(self.thin_arm_observations, int)
                or self.thin_arm_observations < 1):
            raise ValueError("the thin-arm threshold must be a positive integer")

    def note(self, arm: str, shape: str, *, novel_fields: int = 0,
             departed: bool = False) -> None:
        """Record one answered stage."""
        if arm not in (OFFERED, CONTROL):
            raise ValueError(f"unknown arm {arm!r}")
        bucket = self.shapes[arm]
        bucket[shape] = bucket.get(shape, 0) + 1
        self.novel_fields[arm] += max(0, int(novel_fields))
        if departed:
            self.departures[arm] += 1

    def _arm(self, arm: str) -> dict:
        counts = self.shapes[arm]
        total = sum(counts.values())
        if not total:
            return {"observations": 0, "distinct_shapes": 0,
                    "concentration": None, "entropy": None,
                    "novel_fields": 0, "departure_rate": None, "thin": True}
        largest = max(counts.values())
        entropy = -sum((n / total) * math.log2(n / total)
                       for n in counts.values() if n)
        return {
            "observations": total,
            "distinct_shapes": len(counts),
            # Share taken by the single most common shape. Rising
            # concentration is the thing that looks like discovery.
            "concentration": round(largest / total, 4),
            "entropy_bits": round(entropy, 4),
            "novel_fields": self.novel_fields[arm],
            "departure_rate": round(self.departures[arm] / total, 4),
            "thin": total < self.thin_arm_observations,
        }

    def to_dict(self) -> dict:
        offered, control = self._arm(OFFERED), self._arm(CONTROL)
        return {
            "record_type": CONVERGENCE_RECORD_TYPE,
            "offered": offered, "control": control,
            "control_arm_share": self.control_arm_share,
            "thin_arm_observations": self.thin_arm_observations,
            "reading": _reading(offered, control),
        }


def _reading(offered: dict, control: dict) -> str:
    """What these two arms do and do not support, in one sentence."""
    if not control["observations"]:
        return ("no stage was answered without a template offered, so nothing "
                "here can separate convergence from suggestion")
    if control["thin"] or offered["thin"]:
        return (f"the arms hold {offered['observations']} offered and "
                f"{control['observations']} control observations, too few to "
                "compare; the split exists and the comparison does not yet")
    gap = offered["concentration"] - control["concentration"]
    # Strong agreement in the control arm is reported first because it is
    # the finding: it exists without anything having suggested it. A gap on
    # top of that is amplification, not the whole story, and an earlier
    # version of this reported only the gap and so described genuine
    # convergence as though it were induced.
    if control["concentration"] > 0.5:
        amplified = (f", amplified to {offered['concentration']} where one "
                     "was") if gap > 0.1 else ""
        return (f"shapes concentrate at {control['concentration']} with no "
                f"template offered{amplified}, which is agreement the "
                "suggestion cannot explain")
    if gap > 0.2:
        return (f"shapes concentrate at {offered['concentration']} where a "
                f"template was offered and {control['concentration']} where "
                "none was; the agreement follows the offer rather than the "
                "work")
    return (f"concentration is {offered['concentration']} offered against "
            f"{control['concentration']} control; neither arm shows strong "
            "agreement yet")


def self_test() -> dict:
    """Offline checks. No provider is contacted."""
    tests = []

    def check(name, ok, detail=""):
        tests.append({"test": name, "passed": bool(ok), "detail": detail})

    check("a retry of one occurrence cannot change arms",
          experiment_arm(TEMPLATE_OFFER, "sig", "run7.orient.2")
          == experiment_arm(TEMPLATE_OFFER, "sig", "run7.orient.2"),
          "a failing run must not be able to walk itself into the other arm")

    # The property the earlier design could not have: one region, both arms.
    region = "stage:sha256:one-region"
    arms = [experiment_arm(TEMPLATE_OFFER, region, f"run{n}.orient.0")
            for n in range(400)]
    controls = arms.count(CONTROL)
    check("one stage region reaches both arms across occurrences",
          0 < controls < 400,
          f"{controls} control of 400; assigning from the signature alone "
          "pinned a region to one arm forever and controlled for nothing")
    check("the split lands near the declared share",
          abs(controls / 400 - CONTROL_ARM_SHARE) < 0.06,
          f"{controls / 400:.3f} against {CONTROL_ARM_SHARE}")

    disagree = sum(
        1 for n in range(200)
        if len({experiment_arm(name, "sig", f"occ{n}")
                for name in (TEMPLATE_OFFER, CACHE_ASSIST, MODEL_ROUTE)}) > 1)
    check("separate experiments assign independently of one another",
          disagree > 20,
          f"{disagree}/200 occurrences where the experiments differ; a stage "
          "may be treated in one experiment and control in another")

    check("a zero share puts everything in the offered arm",
          all(experiment_arm(TEMPLATE_OFFER, "s", f"o{n}", share=0.0)
              == OFFERED for n in range(50)))
    check("a full share puts everything in the control arm",
          all(experiment_arm(TEMPLATE_OFFER, "s", f"o{n}", share=1.0)
              == CONTROL for n in range(50)))
    check("a campaign seed re-randomises without a code change",
          any(experiment_arm(TEMPLATE_OFFER, region, f"occ{n}", seed="a")
              != experiment_arm(TEMPLATE_OFFER, region, f"occ{n}", seed="b")
              for n in range(100)),
          "campaigns need a reproducible way to draw a different split")

    bad_share = False
    try:
        experiment_arm(TEMPLATE_OFFER, "s", "o", share=1.5)
    except ValueError:
        bad_share = True
    check("an impossible share is refused", bad_share)

    configured = ConvergenceMeasure(
        control_arm_share=0.4, thin_arm_observations=3)
    configured.note(OFFERED, "a")
    configured.note(CONTROL, "a")
    check("the recorded share and evidence floor are configurable",
          configured.to_dict()["control_arm_share"] == 0.4
          and configured.to_dict()["thin_arm_observations"] == 3
          and configured.to_dict()["control"]["thin"])
    bad_configs = 0
    for values in ({"control_arm_share": -0.1},
                   {"thin_arm_observations": 0}):
        try:
            ConvergenceMeasure(**values)
        except ValueError:
            bad_configs += 1
    check("invalid convergence settings are refused", bad_configs == 2)

    empty = ConvergenceMeasure()
    check("with no control observations nothing can be concluded",
          "nothing here can separate convergence from suggestion"
          in empty.to_dict()["reading"])

    # Agreement that exists only where a template was shown.
    induced = ConvergenceMeasure()
    for _ in range(60):
        induced.note(OFFERED, "experiment_spec")
    for index in range(40):
        induced.note(CONTROL, f"shape_{index % 8}")
    value = induced.to_dict()
    check("agreement that follows the offer is named as such",
          value["offered"]["concentration"] == 1.0
          and value["control"]["concentration"] < 0.2
          and "follows the offer" in value["reading"])

    # Agreement that survives without prompting.
    genuine = ConvergenceMeasure()
    for _ in range(60):
        genuine.note(OFFERED, "experiment_spec")
    for index in range(40):
        genuine.note(CONTROL, "experiment_spec" if index % 4 else "other")
    real = genuine.to_dict()
    check("agreement the suggestion cannot explain is named as such",
          real["control"]["concentration"] >= 0.7
          and "the suggestion cannot explain" in real["reading"]
          and "amplified" in real["reading"],
          "genuine agreement plus amplification, not one or the other")

    thin = ConvergenceMeasure()
    thin.note(OFFERED, "a")
    thin.note(CONTROL, "a")
    check("a thin comparison says it is thin rather than concluding",
          thin.to_dict()["control"]["thin"]
          and "too few to compare" in thin.to_dict()["reading"])

    entropy = ConvergenceMeasure()
    for index in range(4):
        entropy.note(CONTROL, f"s{index}")
    check("entropy rises with genuine variety",
          entropy.to_dict()["control"]["entropy_bits"] == 2.0)

    novel = ConvergenceMeasure()
    novel.note(CONTROL, "s", novel_fields=3, departed=True)
    counted = novel.to_dict()["control"]
    check("novelty and departure are counted per arm",
          counted["novel_fields"] == 3 and counted["departure_rate"] == 1.0)

    bad = False
    try:
        ConvergenceMeasure().note("whichever", "s")
    except ValueError:
        bad = True
    check("an unknown arm is refused", bad)

    passed = sum(1 for item in tests if item["passed"])
    return {"record_type": "convergence_test/v1", "tests": tests,
            "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}


if __name__ == "__main__":
    print(json.dumps(self_test(), indent=1))
