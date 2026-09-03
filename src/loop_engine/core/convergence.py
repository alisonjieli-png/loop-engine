"""Whether response shapes are converging, or only being told to.

There is an obvious way to be fooled here. The system offers a template. Calls
use it, because it was offered. The record fills with agreement. Concentration
rises, entropy falls, and it looks as though a shape has been discovered when
what has happened is that one was suggested and adopted. A shortcut fitted to
that record would encode the suggestion, not the finding, and would keep
encoding it as the evidence base grew.

The only defence that works is one built before the data exists: a share of
stages must be answered with no template offered at all. Those are the control
arm. If shapes converge there too, the convergence is in the work. If they
converge only where a template was shown, the convergence is in the showing.
Adding a control arm later cannot rescue a record already collected without
one, which is why this is here now rather than when there is enough data to
analyse.

Assignment is deterministic from the stage identity, so the same situation
always lands in the same arm — a run cannot drift into the offered arm by
retrying, and the split is reproducible from the record alone.

Nothing here decides that a shape is good. It reports how much agreement
exists, how much of it survives without prompting, and how often something
genuinely new appeared.

Owns:
    - control_arm(): which arm a stage belongs to, decided before the offer.
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


def control_arm(stage_digest: str, share: float = CONTROL_ARM_SHARE) -> str:
    """Which arm this stage belongs to, decided from its identity alone.

    Deterministic so the same situation always lands the same way. A run that
    retries a stage cannot walk it into the offered arm, and anyone holding
    the record can recompute the split without trusting that it was done
    honestly at the time.
    """
    if not 0.0 <= share <= 1.0:
        raise ValueError("the control share must be between 0 and 1")
    if share == 0.0:
        return OFFERED
    digest = hashlib.sha256(str(stage_digest).encode("utf-8")).hexdigest()
    # The low 16 bits, scaled. Enough resolution for any share worth setting.
    position = int(digest[-4:], 16) / 0xFFFF
    return CONTROL if position < share else OFFERED


@dataclass
class ConvergenceMeasure:
    """How much response shapes agree, and how much of that was prompted."""

    #: shape identity -> count, per arm.
    shapes: dict = field(default_factory=lambda: {OFFERED: {}, CONTROL: {}})
    novel_fields: dict = field(default_factory=lambda: {OFFERED: 0,
                                                        CONTROL: 0})
    departures: dict = field(default_factory=lambda: {OFFERED: 0, CONTROL: 0})

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
            "thin": total < _THIN_ARM,
        }

    def to_dict(self) -> dict:
        offered, control = self._arm(OFFERED), self._arm(CONTROL)
        return {
            "record_type": CONVERGENCE_RECORD_TYPE,
            "offered": offered, "control": control,
            "control_arm_share": CONTROL_ARM_SHARE,
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

    check("the same stage always lands in the same arm",
          control_arm("stage:sha256:abc") == control_arm("stage:sha256:abc"),
          "a retry must not be able to change arms")

    digests = [f"stage:sha256:{index:08x}" for index in range(4000)]
    controls = sum(1 for item in digests if control_arm(item) == CONTROL)
    observed = controls / len(digests)
    check("the split lands near the declared share",
          abs(observed - CONTROL_ARM_SHARE) < 0.03,
          f"{observed:.3f} against {CONTROL_ARM_SHARE}")

    check("a zero share puts everything in the offered arm",
          all(control_arm(item, share=0.0) == OFFERED
              for item in digests[:50]))
    check("a full share puts everything in the control arm",
          all(control_arm(item, share=1.0) == CONTROL
              for item in digests[:50]))

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
