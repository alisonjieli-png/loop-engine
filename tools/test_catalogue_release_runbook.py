"""Hold the catalogue release runbook to the procedure the service checks replay.

On September 23, 2026 the runbook section "Publish and roll back a catalogue
release" was followed on the live Machine exactly as written. Its first-time
step `follow-catalogue-release --all-tenants` gave every account every item,
including `pilot-boundary`, the account that exists to prove isolation.

`catalogue_serving_checks` replays the first-time procedure through the
service entry point and requires that an account the manifest does not grant
holds nothing, including an item published afterwards. This test makes that
replay the documented one: it reads the section, takes every
`loop-engine service` command out of it, and requires the first-time follow
step to be exactly the step the check replays, every command to be one the
entry point accepts, and the recovery step to stop one named account. The
known-wrong case is the step as the runbook wrote it for release 17.
"""
from __future__ import annotations

from pathlib import Path
import re
import shlex
import sys
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))

from loop_engine.core.service_runtime.catalogue_serving_checks import (  # noqa: E402
    FIRST_RELEASE_FOLLOW_STEP, RELEASE_17_FOLLOW_STEP,
)
from loop_engine.core.service_runtime.http_entrypoint import SERVICE_COMMANDS  # noqa: E402

RUNBOOK = HERE.parent / "docs/guides/launch-setup-runbook.md"
SECTION = "### Publish and roll back a catalogue release"
#: The first-time step as the runbook wrote it for release 17.
RELEASE_17_STEP = """7. The first time only, move accounts to grants that follow the release:
   `flyctl machine exec MACHINE "AS_SERVICE loop-engine service follow-catalogue-release --config /data/host.json --all-tenants" --app baltor-pilot --json`.
"""
COMMAND = re.compile(r"loop-engine service ([^\"`]+)")


def section(text):
    """The catalogue release section of the runbook, up to the next heading of its level or above."""
    start = text.index(SECTION)
    following = re.search(r"^#{2,3} ", text[start + len(SECTION):], flags=re.MULTILINE)
    return text[start:start + len(SECTION) + following.start()] if following else text[start:]


def service_commands(text):
    """Every documented `loop-engine service` command, as the entry point receives it without `--config`."""
    commands = []
    for span in re.findall(r"`([^`]+)`", text):
        for found in COMMAND.findall(span):
            words = shlex.split(found)
            if "--config" in words:
                at = words.index("--config")
                del words[at:at + 2]
            commands.append(tuple(words))
    return commands


def follow_step_findings(text):
    """What is wrong with the documented follow steps; empty when each names the account the check replays."""
    follows = [words for words in service_commands(text) if words[:1] == ("follow-catalogue-release",)]
    findings = []
    if not follows:
        findings.append("the section documents no follow-catalogue-release step")
    for words in follows:
        if "--all-tenants" in words:
            findings.append("a follow step moves every account: " + " ".join(words))
        elif words != FIRST_RELEASE_FOLLOW_STEP:
            findings.append("a follow step is not the step the service checks replay: " + " ".join(words))
    return findings


class CatalogueReleaseRunbook(unittest.TestCase):
    def setUp(self):
        self.text = section(RUNBOOK.read_text(encoding="utf-8"))

    def test_the_first_time_follow_step_is_the_step_the_service_checks_replay(self):
        self.assertEqual(follow_step_findings(self.text), [])
        self.assertIn(FIRST_RELEASE_FOLLOW_STEP, service_commands(self.text))

    def test_the_first_time_step_as_written_for_release_17_is_refused(self):
        self.assertEqual(service_commands(RELEASE_17_STEP), [RELEASE_17_FOLLOW_STEP])
        findings = follow_step_findings(RELEASE_17_STEP)
        self.assertEqual(len(findings), 1)
        self.assertIn("--all-tenants", findings[0])

    def test_a_follow_step_for_another_account_is_refused(self):
        changed = self.text.replace("--tenant pilot-owner", "--tenant pilot-boundary")
        self.assertNotEqual(changed, self.text)
        self.assertTrue(follow_step_findings(changed))

    def test_every_service_command_the_section_documents_is_one_the_entry_point_accepts(self):
        commands = service_commands(self.text)
        self.assertGreaterEqual(len(commands), 6)
        self.assertEqual([words for words in commands if words[0] not in SERVICE_COMMANDS], [])

    def test_the_recovery_step_stops_one_named_account_and_is_followed_by_the_isolation_check(self):
        stops = [words for words in service_commands(self.text) if words[:1] == ("stop-following-catalogue-release",)]
        self.assertTrue(stops)
        for words in stops:
            self.assertEqual(words[1], "--tenant")
            self.assertEqual(len(words), 3)
        self.assertIn("tools/check_hosted_service.py", self.text)
        self.assertIn("--isolated-account pilot-boundary", self.text)


FOLLOW_SECTION = "### Let new accounts follow the catalogue release"
DIAGNOSTIC_ACCOUNTS = ("pilot-boundary", "billing-check", "billing-check-2", "billing-check-3", "baltor-admin")


def follow_section(text):
    start = text.index(FOLLOW_SECTION)
    following = re.search(r"^#{2,3} ", text[start + len(FOLLOW_SECTION):], flags=re.MULTILINE)
    return text[start:start + len(FOLLOW_SECTION) + following.start()] if following else text[start:]


def follow_findings(text):
    """What is wrong with the follow section; empty when it runs exactly the replayed steps in order."""
    from loop_engine.core.service_runtime.catalogue_follow_checks import FOLLOW_CUSTOMERS_STEP, FOLLOW_PREVIEW_STEP
    findings = []
    commands = service_commands(text)
    if commands != [FOLLOW_PREVIEW_STEP, FOLLOW_CUSTOMERS_STEP]:
        findings.append("the section runs other commands than the replay: " + repr(commands))
    for needed in ('"new_accounts_follow_release": true', '"starter_identities": []', "invalid_starter_identities",
                   "not_granted_every_item", "already_following", *DIAGNOSTIC_ACCOUNTS):
        if needed not in text:
            findings.append("the section does not name " + needed)
    return findings


class FollowReleaseRunbook(unittest.TestCase):
    def setUp(self):
        self.text = follow_section(RUNBOOK.read_text(encoding="utf-8"))

    def test_the_section_runs_exactly_the_replayed_steps(self):
        self.assertEqual(follow_findings(self.text), [])

    def test_a_step_that_names_a_diagnostic_account_is_refused(self):
        changed = self.text.replace("--all-tenants\"", "--tenant pilot-boundary\"")
        self.assertNotEqual(changed, self.text)
        self.assertTrue(follow_findings(changed))

    def test_a_section_without_the_preview_is_refused(self):
        changed = self.text.replace("loop-engine service catalogue-status --config /data/host.json", "true")
        self.assertNotEqual(changed, self.text)
        self.assertTrue(follow_findings(changed))

    def test_the_first_release_section_still_ends_before_this_one(self):
        self.assertNotIn(FOLLOW_SECTION, section(RUNBOOK.read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()
