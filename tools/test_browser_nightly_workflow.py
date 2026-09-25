"""The nightly browser suite reports and never releases: it runs the suite, keeps the report and touches no deploy.

Roadmap step S-6.180. The workflow is .github/workflows/browser-nightly.yml. Each rule below refuses one way the
workflow could stop being a report: a deploy setting or release command, write access beyond its one issue, a
missing schedule, or a run that no longer drives the browser suite. Each rule has a known-wrong control.
"""
from __future__ import annotations

from pathlib import Path
import re
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "browser-nightly.yml"
#: Words of a release: a deploy setting, the deploy workflow, a machine operation or a pushed revision.
RELEASE_WORDS = re.compile(r"FLY_DEPLOY_ENABLED|fly-pilot|flyctl|fly_operator|gh variable set|gh workflow run|git push")


def workflow_problems(text: str) -> list:
    """What is wrong with the workflow text, or nothing."""
    problems = []
    data = yaml.safe_load(text)
    triggers = data.get(True, data.get("on")) or {}
    if not isinstance(triggers, dict) or "schedule" not in triggers or "workflow_dispatch" not in triggers:
        problems.append("it does not run on a schedule and on demand")
    if data.get("permissions") != {"contents": "read", "issues": "write"}:
        problems.append("its permissions are not exactly contents read and issues write")
    found = RELEASE_WORDS.search(text)
    if found:
        problems.append(f"it names a release action: {found.group(0)}")
    if "node tools/check_service_workspace.mjs" not in text:
        problems.append("it does not run the browser suite")
    return problems


class NightlyBrowserWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.text = WORKFLOW.read_text(encoding="utf-8")

    def test_the_workflow_reports_and_never_releases(self):
        self.assertEqual(workflow_problems(self.text), [])

    def test_known_wrong_a_deploy_setting_is_found(self):
        changed = self.text.replace("set -euo pipefail\n          python -m pip",
                                    "set -euo pipefail\n          gh variable set FLY_DEPLOY_ENABLED --env pilot --body true\n"
                                    "          python -m pip", 1)
        self.assertNotEqual(changed, self.text)
        self.assertTrue(any("release action" in problem for problem in workflow_problems(changed)))

    def test_known_wrong_write_access_to_contents_is_found(self):
        changed = self.text.replace("contents: read", "contents: write", 1)
        self.assertIn("its permissions are not exactly contents read and issues write", workflow_problems(changed))

    def test_known_wrong_a_workflow_without_a_schedule_is_found(self):
        changed = re.sub(r"  schedule:\n    - cron: \"[^\"]+\"\n", "", self.text, count=1)
        self.assertNotEqual(changed, self.text)
        self.assertIn("it does not run on a schedule and on demand", workflow_problems(changed))

    def test_known_wrong_a_run_without_the_suite_is_found(self):
        changed = self.text.replace("node tools/check_service_workspace.mjs", "node --version", 1)
        self.assertIn("it does not run the browser suite", workflow_problems(changed))


if __name__ == "__main__":
    unittest.main()
