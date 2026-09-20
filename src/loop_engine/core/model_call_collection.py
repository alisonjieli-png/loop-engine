"""Keep what a model call can teach, and nothing that must not be kept.

A run already publishes an event when a model step starts, completes, fails
its transport, has its response rejected, or deviates from the shape the call
asked for. Those events are forwarded to whatever progress listener the caller
installed and then dropped. The join that turns them into one learnable record
per call exists, and nothing was feeding it.

This is the collector that does. It sits in front of the caller's own progress
listener, passes every event through unchanged, and retains only the five
kinds the join reads.

WHAT IS NEVER RETAINED
A started event carries the prompt itself when the run is not quiet. The
collector drops that field before retaining anything, so the retained events
cannot carry a prompt, a response body, or anything else a learning export
must not see. Digests and byte counts are kept, which is what the record shape
asks for anyway.

WHY A CEILING
A long run publishes a great many events. The collector holds a declared
ceiling and, on reaching it, stops retaining and says so in its report rather
than growing without limit or quietly discarding the newest. A truncated
collection that says it is truncated can be used; one that does not cannot.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import re

from .model_call_records import (COMPLETED, DEVIATION, INVALID_METADATA, REJECTED, STARTED,
                                 TRANSPORT_FAILED, learning_records)

RECORD_TYPE = "model_call_collection/v2"
#: The event kinds the join reads. Anything else is passed on and not retained.
RETAINED_KINDS = (STARTED, COMPLETED, TRANSPORT_FAILED, REJECTED, DEVIATION)
#: Fields that may carry a prompt or a response body. Dropped before retention.
WITHHELD_FIELDS = ("prompt_text", "response_text", "output_text", "system_text")
# This positive field set excludes response previews, task text, arbitrary
# nested payloads, and future text-bearing event fields by default.
RETAINED_FIELDS = frozenset((
    "event_type", "run_id", "context_loop_id", "progress_sequence", "pass_number",
    "model_call_number", "model_calls_completed", "step", "format_attempt",
    "transport_attempt", "model_call_occurrence_id", "output_contract_id",
    "prompt_digest", "prompt_bytes", "output_schema_digest", "output_digest",
    "output_bytes", "admitted_strategy", "error_code", "failure_code",
    "response_digest", "suggested_output_digest"))
DIGEST_FIELDS = frozenset(("prompt_digest", "output_schema_digest", "output_digest",
                           "response_digest", "suggested_output_digest"))
#: How many events one run may retain before the collection is truncated.
DEFAULT_CEILING = 20_000


class ModelCallCollectionError(ValueError):
    """The collector was given something it cannot retain or forward."""


@dataclass
class LearningEventCollector:
    """Forwards every progress event and retains the ones a record needs."""

    forward_to: object = None
    ceiling: int = DEFAULT_CEILING
    events: list = field(default_factory=list, init=False, repr=False)
    seen: int = 0
    truncated: bool = False
    withheld: int = 0
    invalid_metadata_events: int = 0

    def __post_init__(self) -> None:
        if self.forward_to is not None and not callable(self.forward_to):
            raise ModelCallCollectionError(
                "a progress listener must be callable; the collector forwards to it")
        if type(self.ceiling) is not int or self.ceiling < 1:
            raise ModelCallCollectionError("a retention ceiling is a positive count")

    def __call__(self, event) -> None:
        """Retain approved scalar metadata, then forward the untouched event."""
        if not isinstance(event, dict):
            if self.forward_to is not None:
                self.forward_to(event)
            return
        self.seen += 1
        if event.get("event_type") not in RETAINED_KINDS:
            if self.forward_to is not None:
                self.forward_to(event)
            return
        if len(self.events) >= self.ceiling:
            self.truncated = True
            if self.forward_to is not None:
                self.forward_to(event)
            return
        cleaned = {key: value for key, value in event.items()
                   if key in RETAINED_FIELDS and type(value) in (str, int, float, bool, type(None))}
        invalid = [key for key in DIGEST_FIELDS if key in cleaned and cleaned[key] not in (None, "")
                   and (not isinstance(cleaned[key], str)
                        or re.fullmatch(r"[0-9a-f]{64}", cleaned[key]) is None)]
        if invalid:
            self.invalid_metadata_events += 1
            cleaned["markers"] = (INVALID_METADATA,)
            for key in invalid:
                cleaned.pop(key)
        if event.get("event_type") == DEVIATION:
            problems = event.get("problems")
            cleaned["deviation_count"] = max(1, len(problems) if isinstance(problems, (list, tuple)) else 1)
        if len(cleaned) != len(event):
            self.withheld += 1
        self.events.append(cleaned)
        if self.forward_to is not None:
            self.forward_to(event)

    def records(self, result: "dict | None" = None) -> list:
        """One learnable record per started model call, from what was retained."""
        return learning_records(self.events, result)

    def report(self, result: "dict | None" = None) -> dict:
        """What was collected, and whether it is complete enough to learn from."""
        produced = self.records(result)
        return {"record_type": RECORD_TYPE, "events_seen": self.seen,
                "events_retained": len(self.events), "records": len(produced),
                "prompt_fields_withheld": self.withheld,
                "truncated": self.truncated, "ceiling": self.ceiling,
                "complete": not self.truncated and self.invalid_metadata_events == 0,
                "invalid_metadata_events": self.invalid_metadata_events,
                "bodies_retained": False,
                "counting_unit": "model_step_invocation",
                "items": [item.to_dict() for item in produced],
                "persistence": "included_in_product_outcome_when_run_history_is_saved"}


def collector_for(progress, *, ceiling: int = DEFAULT_CEILING) -> LearningEventCollector:
    """Wrap a caller's progress listener so nothing it received is lost."""
    return LearningEventCollector(forward_to=progress, ceiling=ceiling)


def self_test() -> dict:
    """Events pass through, prompts do not survive, and a ceiling is reported."""
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    def refuses(action):
        try:
            action()
        except ModelCallCollectionError:
            return True
        except Exception:  # noqa: BLE001 - a crash is not a typed refusal
            return False
        return False

    forwarded = []
    collector = collector_for(forwarded.append)
    started = {"event_type": STARTED, "run_id": "run-1", "step": "route",
               "model_call_number": 1, "pass_number": 1,
               "output_contract_id": "route/v1", "prompt_digest": "a" * 64,
               "prompt_bytes": 1200, "output_schema_digest": "b" * 64,
               "objective": "choose the next action", "format_attempt": 1,
               "transport_attempt": 1,
               "prompt_text": "the whole prompt, which must not be retained"}
    completed = {"event_type": COMPLETED, "run_id": "run-1", "step": "route",
                 "format_attempt": 1, "transport_attempt": 1,
                 "output_digest": "c" * 64, "output_bytes": 400,
                 "admitted_strategy": "first_attempt",
                 "response_text": "the whole response",
                 "output_preview": "a response preview that must not survive",
                 "future_payload": {"text": "an unrecognized response field"}}
    unrelated = {"event_type": "solve.stage.entered", "run_id": "run-1"}
    for event in (started, completed, unrelated, "not an event"):
        collector(event)
    check("every_event_reaches_the_caller_and_only_the_read_kinds_are_retained",
          forwarded == [started, completed, unrelated, "not an event"]
          and len(collector.events) == 2
          and {row["event_type"] for row in collector.events} == {STARTED, COMPLETED}
          and collector.seen == 3,
          str(collector.seen))
    check("a_prompt_or_a_response_body_does_not_survive_retention",
          all("prompt_text" not in row and "response_text" not in row
              for row in collector.events)
          and collector.events[0]["prompt_digest"] == "a" * 64
          and collector.events[0]["prompt_bytes"] == 1200
          and collector.withheld == 2
          and "the whole prompt" not in str(collector.events)
          and "output_preview" not in str(collector.events)
          and "future_payload" not in str(collector.events)
          and "objective" not in collector.events[0],
          str(collector.withheld))
    produced = collector.records({"status": "COMPLETED_VERIFIED"})
    report = collector.report({"status": "COMPLETED_VERIFIED"})
    check("the_retained_events_join_into_one_record_per_started_call",
          len(produced) == 1 and produced[0].run_id == "run-1"
          and produced[0].completed is True
          and produced[0].prompt_digest == "a" * 64
          and produced[0].output_bytes == 400
          and report["records"] == 1 and report["complete"] is True
          and report["bodies_retained"] is False
          and len(report["items"]) == 1
          and report["items"][0]["record_id"] == produced[0].record_id,
          str(report["records"]))
    bounded = LearningEventCollector(ceiling=2)
    for number in range(5):
        bounded({**started, "model_call_number": number + 1,
                 "transport_attempt": number + 1})
    bounded_report = bounded.report()
    check("a_run_past_the_ceiling_is_truncated_and_says_so_rather_than_growing",
          bounded_report["events_retained"] == 2
          and bounded_report["truncated"] is True
          and bounded_report["complete"] is False
          and bounded_report["events_seen"] == 5
          and bounded_report["ceiling"] == 2,
          str(bounded_report["events_retained"]))
    check("a_collector_with_no_listener_still_collects_and_a_bad_one_is_refused",
          LearningEventCollector()(started) is None
          and refuses(lambda: LearningEventCollector(forward_to="not callable"))
          and refuses(lambda: LearningEventCollector(ceiling=0))
          and refuses(lambda: LearningEventCollector(ceiling=True))
          and refuses(lambda: LearningEventCollector(ceiling="many")))
    failing = LearningEventCollector()
    for event in (started,
                  {"event_type": TRANSPORT_FAILED, "run_id": "run-1", "step": "route",
                   "format_attempt": 1, "transport_attempt": 1},
                  {"event_type": REJECTED, "run_id": "run-1", "step": "route",
                   "format_attempt": 1, "transport_attempt": 1}):
        failing(event)
    failed_records = failing.records({"status": "COMPLETED_PARTIAL"})
    check("a_call_that_failed_its_transport_and_was_rejected_is_still_one_record",
          len(failed_records) == 1
          and failed_records[0].transport_failures == 1
          and failed_records[0].rejections == 1
          and failed_records[0].completed is False,
          str(failed_records[0].rejections))
    malformed = LearningEventCollector()
    malformed({**started, "prompt_digest": "private text in a digest field"})
    check("an_invalid_digest_cannot_smuggle_text_into_retained_metadata",
          "private text" not in str(malformed.events)
          and malformed.report()["complete"] is False
          and malformed.report()["invalid_metadata_events"] == 1)
    deviated = LearningEventCollector()
    deviated(started)
    deviated({**completed, "event_type": DEVIATION,
              "problems": ["response-derived private detail", "another private detail"]})
    deviated(completed)
    check("deviation_counts_survive_without_retaining_diagnostic_prose",
          deviated.records()[0].deviation_count == 2
          and deviated.records()[0].deviation_problems == ()
          and "private detail" not in str(deviated.events))
    passed = sum(item["passed"] for item in tests)
    return {"record_type": "model_call_collection_test/v1", "tests": tests,
            "passed": passed, "total": len(tests), "all_passed": passed == len(tests)}
