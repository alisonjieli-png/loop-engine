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
#: A fence of three or more backticks or tildes, closed by at least as many of the same mark or by the end.
FENCED_CODE = re.compile(r"^[ \t]*(?P<fence>(?P<mark>[`~])(?P=mark){2,})[^\n]*\n(?P<code>.*?)"
                         r"(?:^[ \t]*(?P=fence)(?P=mark)*[ \t]*$|\Z)", re.MULTILINE | re.DOTALL)
#: Lines indented four columns after a blank line; an indented line cannot continue a paragraph as code.
INDENTED_CODE = re.compile(r"(?:\A|^(?:[ \t]*\n)+)(?P<code>(?:(?: {4}| {0,3}\t)[^\n]*(?:\n|\Z))+)", re.MULTILINE)


def section(text):
    """The catalogue release section of the runbook, up to the next heading of its level or above."""
    start = text.index(SECTION)
    following = re.search(r"^#{2,3} ", text[start + len(SECTION):], flags=re.MULTILINE)
    return text[start:start + len(SECTION) + following.start()] if following else text[start:]


def service_commands(text):
    """Every documented `loop-engine service` command, as the entry point receives it without `--config`."""
    commands = []
    spans = [block["code"] for block in FENCED_CODE.finditer(text)]
    prose = FENCED_CODE.sub("", text)
    spans += [block["code"] for block in INDENTED_CODE.finditer(prose)]
    spans += re.findall(r"`([^`]+)`", INDENTED_CODE.sub("\n\n", prose))
    for span in spans:
        for found in (entry for line in span.replace("\\\n", " ").splitlines() for entry in COMMAND.findall(line)):
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

    def test_fenced_examples_do_not_hide_later_inline_recovery_commands(self):
        text = ('An example:\n\n   ```bash\n   python tools/example.py --dry-run\n   ```\n\n'
                '`loop-engine service stop-following-catalogue-release --config /data/host.json --tenant fixture`')
        self.assertEqual(service_commands(text), [('stop-following-catalogue-release', '--tenant', 'fixture')])
        self.assertEqual(service_commands('```bash\nloop-engine service catalogue-status --config /data/host.json\n```'),
                         [('catalogue-status',)])
        self.assertEqual(service_commands('```bash\nloop-engine service catalogue-status\nloop-engine service unknown-command\n```'),
                         [('catalogue-status',), ('unknown-command',)])
        stop = '`loop-engine service stop-following-catalogue-release --tenant fixture`'
        for example in ('~~~bash\npython tools/example.py --dry-run\n~~~\n\n', '    python tools/example.py --dry-run\n\n'):
            with self.subTest(example=example):
                self.assertEqual(service_commands(example + stop), [('stop-following-catalogue-release', '--tenant', 'fixture')])

    def test_the_release_17_step_is_refused_in_every_markdown_code_form(self):
        # Known wrong until October 5, 2026: only ``` fences and inline code were read, so the same step in any of these
        # forms was not checked at all.
        step = "loop-engine service follow-catalogue-release --config /data/host.json --all-tenants"
        for form, block in (("tilde fence", f"~~~bash\n{step}\n~~~\n"),
                            ("tilde fence holding a backtick line", f"~~~\n```\n{step}\n~~~\n"),
                            ("longer fence holding a shorter one", f"````markdown\n```\n{step}\n````\n"),
                            ("unterminated fence", f"```bash\n{step}\n"),
                            ("indented block", f"    {step}\n"),
                            ("tab-indented block", f"\t{step}\n")):
            with self.subTest(form=form):
                changed = self.text.rstrip("\n") + "\n\n" + block
                self.assertIn(RELEASE_17_FOLLOW_STEP, service_commands(changed))
                self.assertIn("a follow step moves every account: follow-catalogue-release --all-tenants",
                              follow_step_findings(changed))
        # An indented line that continues a paragraph is prose, as Markdown renders it.
        self.assertEqual(service_commands(f"Run this:\n    {step}\n"), [])

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
