"""Reviewer calibration: known-wrong and known-good items asked of every eligible reviewer before real candidates.

Three independent approvals mean something only when each reviewer rejects
what is plainly wrong. The calibration set names items whose correct decision
is known: real catalogue bodies with one planted defect that a written
criterion names, and a body an earlier independent review approved, unchanged.
Every eligible installation is asked about every calibration item. An
installation that approves a known-wrong item, or gives no valid verdict on one,
is not asked about real candidates in the same run, and the record says why.
Rejecting the known-good item is recorded as a false refusal; it does not
exclude the reviewer, because a refusal cannot approve anything.

The calibration measures known defect classes on a small fixed set. It does not
estimate the error rate on real candidates, and the record says so.
"""
from __future__ import annotations

from dataclasses import dataclass

from .records import digest, read_part, read_record, refuse, sha256_hex, text_field
from .verdicts import APPROVE, DECISIONS, REJECT

CALIBRATION_SET_RECORD = "candidate_review_calibration_set/v1"
ITEM_FIELDS = ("identity", "base_identity", "expected_decision", "criterion_id", "defect", "replacements",
               "reference_overrides")
OVERRIDABLE = ("declared_effects", "purpose")
FAILED_CALIBRATION, CALIBRATION_INCOMPLETE = "failed_calibration", "calibration_incomplete"
LIMITS = ("A fixed set of planted defects measures whether a reviewer catches those defect classes. It does not "
          "estimate how often the reviewer errs on real candidates.")


@dataclass(frozen=True)
class CalibrationItem:
    identity: str
    base_identity: str
    expected_decision: str
    criterion_id: str
    defect: str
    replacements: tuple
    reference_overrides: dict

    def to_dict(self) -> dict:
        return {"identity": self.identity, "base_identity": self.base_identity,
                "expected_decision": self.expected_decision, "criterion_id": self.criterion_id,
                "defect": self.defect}


@dataclass(frozen=True)
class CalibrationSet:
    purpose: str
    items: tuple
    sha256: str

    @classmethod
    def from_dict(cls, value, criteria_ids) -> "CalibrationSet":
        record = read_record(value, CALIBRATION_SET_RECORD, ("purpose", "items"))
        rows = record["items"]
        if type(rows) is not list or not rows:
            refuse("invalid_calibration_set", "a calibration set lists items")
        built, names = [], set()
        for raw in rows:
            row = read_part(raw, "calibration item", ITEM_FIELDS)
            if row["identity"] in names or row["identity"] == row["base_identity"]:
                refuse("invalid_calibration_set", "each calibration item has its own identity")
            names.add(row["identity"])
            if row["expected_decision"] not in DECISIONS or row["criterion_id"] not in criteria_ids:
                refuse("invalid_calibration_set", f"{row['identity']} needs a decision and a known criterion")
            if row["expected_decision"] == REJECT and not str(row["defect"]).strip():
                refuse("invalid_calibration_set", f"known-wrong {row['identity']} names its defect")
            replacements = row["replacements"]
            if type(replacements) is not list or any(
                    type(item) is not dict or set(item) != {"find", "replace"} or not str(item["find"]).strip()
                    for item in replacements):
                refuse("invalid_calibration_set", f"{row['identity']} lists find and replace pairs")
            overrides = row["reference_overrides"]
            if type(overrides) is not dict or set(overrides) - set(OVERRIDABLE):
                refuse("invalid_calibration_set", f"{row['identity']} may override only {list(OVERRIDABLE)}")
            if row["expected_decision"] == REJECT and not replacements and not overrides:
                refuse("invalid_calibration_set", f"known-wrong {row['identity']} plants no defect")
            built.append(CalibrationItem(row["identity"], row["base_identity"], row["expected_decision"],
                                         row["criterion_id"], text_field(row["defect"], "defect", limit=1000,
                                                                         empty=True),
                                         tuple((item["find"], item["replace"]) for item in replacements),
                                         dict(overrides)))
        return cls(text_field(record["purpose"], "purpose", limit=2000), tuple(built), digest(value))

    def requests(self, catalogue, producers, criteria, instructions_sha256) -> tuple:
        """One review request per item: the base body with its planted defect, and a matching item record."""
        built = []
        for item in self.items:
            base = catalogue.request(item.base_identity, producers.producer_for(item.base_identity), criteria,
                                     instructions_sha256)
            text = base.body_text
            for find, replace in item.replacements:
                if text.count(find) != 1:
                    refuse("calibration_replacement_not_unique",
                           f"a replacement for {item.identity} does not occur exactly once in its base body")
                text = text.replace(find, replace)
            body = text.encode("utf-8")
            row = base.item
            row["reference"].update(item.reference_overrides)
            row["reference"].update(identity=item.identity, digest=sha256_hex(body), size_bytes=len(body))
            row["body_path"] = f"calibration/{item.identity}.md"
            request = base.replaced(body=body, item=row, identity=item.identity)
            if item.criterion_id not in request.applicable_criteria_ids:
                refuse("calibration_criterion_not_applicable",
                       f"{item.identity} names {item.criterion_id}, which does not apply to its kind of body")
            built.append((item, request))
        return tuple(built)

    def population(self, population) -> dict:
        """The duplicate pre-check's population without the bodies the calibration items are built from."""
        bases = {item.base_identity for item in self.items}
        return {identity: body for identity, body in population.items() if identity not in bases}


def evaluate(calibration: CalibrationSet, result) -> dict:
    """Each installation's decisions against the expected ones, and whether it may review real candidates."""
    expected = {item.identity: item.expected_decision for item in calibration.items}
    # Every installation the run could ask counts, whether or not the run reached it: a reviewer the
    # calibration never measured is not trusted with real candidates.
    asked = {identity: set() for identity, probe in result.availability.items()
             if probe.available and identity not in result.ineligible}
    for call in result.calls:
        asked.setdefault(call["installation_id"], set()).add(call["identity"])
    for item in result.items:
        for verdict in item.verdicts:
            asked.setdefault(verdict["reviewer_id"], set()).add(item.identity)
    decided = {}
    for item in result.items:
        for verdict in item.verdicts:
            decided.setdefault(verdict["reviewer_id"], {})[item.identity] = verdict["decision"]
    installations = {}
    for installation_id in sorted(asked):
        answers = decided.get(installation_id, {})
        wrong = [identity for identity, decision in expected.items() if decision == REJECT]
        good = [identity for identity, decision in expected.items() if decision == APPROVE]
        false_approvals = sorted(identity for identity in wrong if answers.get(identity) == APPROVE)
        unanswered = sorted(identity for identity in wrong if identity not in answers)
        false_refusals = sorted(identity for identity in good if answers.get(identity) == REJECT)
        correct = sum(1 for identity, decision in answers.items() if expected.get(identity) == decision)
        status = FAILED_CALIBRATION if false_approvals else (CALIBRATION_INCOMPLETE if unanswered else "qualified")
        installations[installation_id] = {"decisions": dict(sorted(answers.items())), "correct": correct,
                                          "false_approvals": false_approvals, "false_refusals": false_refusals,
                                          "known_wrong_without_a_verdict": unanswered, "status": status}
    return {"set_sha256": calibration.sha256, "purpose": calibration.purpose,
            "items": [item.to_dict() for item in calibration.items], "run_id": result.run_id,
            "installations": installations,
            "excluded": {installation_id: row["status"] for installation_id, row in installations.items()
                         if row["status"] != "qualified"},
            "limits": LIMITS}
