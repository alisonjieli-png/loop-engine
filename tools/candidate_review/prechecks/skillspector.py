"""Safety pre-check engine ``skillspector_static``: NVIDIA SkillSpector in static mode.

Adapted, not copied: the engine runs SkillSpector's own command (Apache-2.0,
Python 3.12 or later) with ``--no-llm`` on the rendered skill file and reads
its JSON report. It refuses on a reported issue at or above the declared
severity (HIGH), on an issue whose severity it does not know, on a scan that did
not run, and on a partial scan unless every reason for the partial result is
declared tolerable. An issue below the threshold is recorded as a triage note
beside the pass: on this catalogue the MEDIUM rule for skill enumeration fires
on a body's own provenance citation of the skill file it restates. The declared
tolerable reason for a partial scan is ``reference_missing``: every catalogue
body names its cited repository path, which is provenance and not a file the
skill bundles. A SkillSpector pass approves nothing; it is triage.

Static mode sends no text to a model. SkillSpector's dependency lookups query
an advisory service only for dependency manifests; a rendered single-file
skill has none. Where the program is not installed the engine is unavailable
and the built-in static rules still decide the kind.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile

from ..records import refuse
from . import PASSED, PrecheckFinding, PrecheckResult, result_of
from .command import DeclaredProgram
from .rendering import write_rendered_skill

SKILL_FOLDER, REPORT_PATH = "{skill_folder}", "{report_path}"
REPORT_FILE = "skillspector-report.json"
#: SkillSpector's severity words, lowest first. An issue at or above the declared threshold refuses;
#: an issue below it is recorded as a triage note; a severity outside this list refuses.
SEVERITY_ORDER = {"INFO": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}


class SkillSpectorStatic:
    kind = "safety"
    engine_id = "skillspector_static"

    def __init__(self, settings: dict, policy) -> None:
        self.program = DeclaredProgram(settings, self.engine_id, (SKILL_FOLDER, REPORT_PATH),
                                       ("tolerated_partial_reasons", "refuse_at_or_above"))
        if settings["refuse_at_or_above"] not in SEVERITY_ORDER:
            refuse("invalid_precheck_settings", f"refuse_at_or_above is one of {list(SEVERITY_ORDER)}")
        self.threshold = settings["refuse_at_or_above"]
        tolerated = settings["tolerated_partial_reasons"]
        if type(tolerated) is not list or any(type(item) is not str for item in tolerated):
            refuse("invalid_precheck_settings", "tolerated_partial_reasons is a list of reason codes")
        self.tolerated = frozenset(tolerated)
        self._version = None

    def availability(self):
        if self._version is None:
            self._version = self.program.version()
        return self._version

    def check(self, request, context):
        version = self.availability()[2]
        with tempfile.TemporaryDirectory(prefix="skill-scan-") as directory:
            folder = write_rendered_skill(request, Path(directory))
            report_path = Path(directory) / REPORT_FILE
            try:
                finished = self.program.run({SKILL_FOLDER: str(folder), REPORT_PATH: str(report_path)},
                                            Path(directory))
            except subprocess.TimeoutExpired:
                return result_of(self.kind, self.engine_id, version,
                                 [("skillspector_incomplete", "the scan did not finish in time")])
            try:
                report = json.loads(report_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                return result_of(self.kind, self.engine_id, version,
                                 [("skillspector_incomplete", f"no readable report (exit {finished.returncode})")])
        refusals, notes = self._findings(report, finished.returncode)
        if refusals:
            return result_of(self.kind, self.engine_id, version, refusals)
        return PrecheckResult(self.kind, self.engine_id, version, PASSED,
                              tuple(PrecheckFinding(code, detail) for code, detail in notes))

    def _findings(self, report, exit_code: int) -> tuple:
        """(refusals, notes): refusals end the item; notes are triage recorded beside a pass."""
        if type(report) is not dict:
            return [("skillspector_incomplete", "the report is not one JSON object")], []
        issues = report.get("issues")
        if type(issues) is not list or any(type(issue) is not dict for issue in issues):
            return [("skillspector_incomplete", "the report lists no readable issues")], []
        limit = SEVERITY_ORDER[self.threshold]
        severe = [issue for issue in issues if SEVERITY_ORDER.get(str(issue.get("severity")), limit) >= limit]
        mild = [issue for issue in issues if issue not in severe]
        if severe:
            return [("skillspector_issue", f"{len(severe)} issues at or above {self.threshold}: "
                                           f"{_named(severe)}")], []
        notes = [("skillspector_note", f"{len(mild)} issues below {self.threshold}: {_named(mild)}")] if mild else []
        if report.get("execution_successful") is not True:
            return [("skillspector_incomplete", "the scan reports that it did not run successfully")], []
        completeness = report.get("analysis_completeness")
        if type(completeness) is not dict:
            return [("skillspector_incomplete", "the report has no completeness record")], []
        if completeness.get("is_complete") is not True:
            reasons = {str(entry.get("reason_code")) for entry in completeness.get("ledger_exceptions") or ()
                       if type(entry) is dict}
            if not reasons or reasons - self.tolerated:
                return [("skillspector_incomplete",
                         f"the scan is partial for the reasons {sorted(reasons - self.tolerated) or ['unstated']}")
                        ], []
        if exit_code != 0 and not mild:
            return [("skillspector_incomplete", f"the scan exited with {exit_code} and reported no issue")], []
        return [], notes


def _named(issues) -> list:
    return sorted({f"{issue.get('rule_id') or issue.get('id') or 'unnamed'}:{issue.get('severity', '')}"
                   for issue in issues})[:12]
