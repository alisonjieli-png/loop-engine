"""Reviewer engine ``fixture``: a scripted reviewer for offline checks.

A fixture reviewer answers from a script given by a check and records every
prompt it was sent. It never calls a model. The panel refuses a fixture
reviewer unless the run is declared a fixture run, and the review record reader
refuses a record that a fixture reviewer decided unless it was told to read a
fixture record, so a scripted answer can never approve a real item.
"""
from __future__ import annotations

from ..records import refuse
from ..verdicts import JSON_ONLY
from . import Availability, ReviewerAttempt

FIXTURE_VERSION = "fixture"


class FixtureReviewer:
    def __init__(self, installation, script=None) -> None:
        self.installation = installation
        self.script = script
        self.calls = []
        self.answer_format, self.output_allocation_tokens = JSON_ONLY, None

    def availability(self) -> Availability:
        return Availability(True, "", FIXTURE_VERSION, {"model": self.installation.model})

    def review(self, prompt, allowance) -> ReviewerAttempt:
        self.calls.append(prompt)
        if self.script is None:
            refuse("fixture_without_script", f"the fixture reviewer {self.installation.installation_id} has no script")
        attempt = self.script(prompt, len(self.calls))
        if not isinstance(attempt, ReviewerAttempt):
            refuse("fixture_script_invalid", "a fixture script returns one ReviewerAttempt")
        return attempt
