"""Tests for tools/check_component_guides.py.

Two kinds of test live here.

The fixture tests build a small repository whose source is known, then write a
guide that says something the source does not support, and require a finding.
Each one is a known-wrong case: it states the exact drift the check exists to
refuse, and it fails if the check stops refusing it. Beside every known-wrong
case is the corrected guide, which must produce no finding, so the check cannot
pass the test by rejecting everything.

The last test runs the check against the real repository. A component guide
that starts naming source that is not there, a boundary added without a guide,
or a guide added without a map entry fails here, in continuous integration,
rather than being discovered by a reader months later.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import check_component_guides as tool  # noqa: E402

REPOSITORY = Path(__file__).resolve().parents[1]

#: One registered boundary whose envelope resolves into the fixture's "core"
#: directory, so the fixture exercises the coverage rule without the real
#: register.
FIXTURE_BOUNDARIES = (
    {"boundary": "fixture operation", "envelope": "core.widget.run_widget"},
)

#: A source file the fixture guides may cite correctly.
FIXTURE_SOURCE = '''
"""A fixture component."""

WIDGET_REFUSED = "widget_refused"


class WidgetRequest:
    """A fixture request."""

    record_type = "widget_request/v1"


def run_widget(request):
    return {"record_type": "widget_result/v1", "status": "ok"}


ROUTES = ("/api/v1/widget",)
'''

#: The fixture component's own checks. A check spells wrong values and builds
#: stand-ins on purpose, to show that the component refuses them.
FIXTURE_CHECKS = '''
"""Checks for the fixture component."""
from .widget import run_widget


def self_test():
    class RetiredWidgetHook:
        """A stand-in the component must refuse."""

    refused = run_widget({"record_type": "widget_request/v9"})
    return {"all_passed": refused["status"] == "ok", "hook": RetiredWidgetHook}
'''

#: A help table with exactly one public command word.
FIXTURE_HELP = '''
COMMAND_HELP = {
    "widget": "run one fixture widget",
}
'''

#: A root parser with exactly one long option.
FIXTURE_MAIN = '''
import argparse


def build():
    parser = argparse.ArgumentParser()
    parser.add_argument("--conformance", action="store_true")
    return parser
'''

#: The fixture's own boundary register, read the way the real one is read.
FIXTURE_REGISTER = '''
BOUNDARIES = (
    {"boundary": "fixture operation",
     "crosses": "a fixture request runs",
     "binding": "native_loop",
     "envelope": "core.widget.run_widget",
     "test": "widget.self_test"},
)
'''

#: A guide that only says things the fixture source supports.
CORRECT_GUIDE = """# Widget

Kind: component explanation for `src/loop_engine/core/widget.py`.

The registered operational boundary is `fixture operation`. Its envelope is
`core.widget.run_widget`, and its request is `WidgetRequest`.

Reading a widget request produces `widget_result/v1`. A refused request carries
`WIDGET_REFUSED`.

Run it with `loop-engine widget`, or check the tree with
`python -m loop_engine --conformance`. It answers on `/api/v1/widget`.
"""

MAP_HEADER = """record_type: component_guide_map/v1
version: 1.0.0
"""


class FixtureRepository:
    """A throwaway repository with one component, one guide and one map."""

    def __init__(self):
        self._directory = tempfile.TemporaryDirectory()
        self.root = Path(self._directory.name)
        package = self.root / "src" / "loop_engine"
        (package / "core").mkdir(parents=True)
        (package / "__init__.py").write_text("", "utf-8")
        (package / "core" / "__init__.py").write_text("", "utf-8")
        (package / "core" / "widget.py").write_text(FIXTURE_SOURCE, "utf-8")
        (package / "core" / "widget_checks.py").write_text(
            FIXTURE_CHECKS, "utf-8")
        (package / "core" / "boundary_registry.py").write_text(
            FIXTURE_REGISTER, "utf-8")
        (package / "cli_help.py").write_text(FIXTURE_HELP, "utf-8")
        (package / "__main__.py").write_text(FIXTURE_MAIN, "utf-8")
        (self.root / "docs" / "components" / "widget").mkdir(parents=True)
        self.guide = self.root / "docs" / "components" / "widget" / "README.md"
        self.write_guide(CORRECT_GUIDE)
        self.write_map()

    def close(self):
        self._directory.cleanup()

    def write_guide(self, text: str) -> None:
        self.guide.write_text(text, "utf-8")

    def write_map(self, *, components=None, guides=None, external=None,
                  examples=None, reader_supplied=None,
                  repository_files=None) -> None:
        """Write the map, defaulting every section to the correct fixture."""
        if components is None:
            components = {"core": "docs/components/widget/README.md"}
        if guides is None:
            guides = ["docs/components/widget/README.md"]
        lines = [MAP_HEADER, "components:"]
        for directory, guide in components.items():
            lines.append("  %r:" % directory)
            lines.append("    guide: %s" % guide)
            lines.append("    covers: the fixture component")
        lines.append("guides:")
        for guide in guides:
            lines.append("  %s: the fixture guide" % guide)
        lines.append("external_names:")
        for name in (external or []):
            lines.append("  %s: belongs to another project" % name)
        lines.append("example_record_types:")
        for name in (examples or []):
            lines.append("  %s: an invented example contract" % name)
        lines.append("reader_supplied_names:")
        for name in (reader_supplied or []):
            lines.append("  %s: a value the reader supplies" % name)
        lines.append("repository_file_names:")
        for name, file in (repository_files or {}).items():
            lines.append("  %s:" % name)
            lines.append("    file: %s" % file)
            lines.append("    meaning: a value of the fixture's example data")
        path = self.root / tool.MAP_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n", "utf-8")

    def audit(self):
        return tool.audit(self.root, boundaries=FIXTURE_BOUNDARIES)

    def kinds(self):
        return sorted({finding.kind for finding in self.audit()})


class GuideClaimTests(unittest.TestCase):
    """Known-wrong cases: a guide names source the fixture does not define."""

    def setUp(self):
        self.repository = FixtureRepository()
        self.addCleanup(self.repository.close)

    def test_the_correct_guide_produces_no_finding(self):
        # The negative control. Without it, a check that refused everything
        # would pass every test below.
        self.assertEqual(self.repository.audit(), [])

    def test_a_command_the_help_table_does_not_register_is_refused(self):
        self.repository.write_guide(
            CORRECT_GUIDE.replace("`loop-engine widget`",
                                  "`loop-engine sprocket`"))
        findings = self.repository.audit()
        self.assertEqual([finding.kind for finding in findings],
                         ["unknown command"])
        self.assertEqual(findings[0].claim, "sprocket")

    def test_a_root_option_the_parser_does_not_register_is_refused(self):
        self.repository.write_guide(
            CORRECT_GUIDE.replace("--conformance", "--inspect-everything"))
        findings = self.repository.audit()
        self.assertEqual([finding.kind for finding in findings],
                         ["unknown command option"])
        self.assertEqual(findings[0].claim, "--inspect-everything")

    def test_a_record_type_the_package_does_not_define_is_refused(self):
        self.repository.write_guide(
            CORRECT_GUIDE.replace("widget_result/v1", "widget_outcome/v3"))
        findings = self.repository.audit()
        self.assertEqual([finding.kind for finding in findings],
                         ["unknown record type"])
        self.assertEqual(findings[0].claim, "widget_outcome/v3")

    def test_a_refusal_code_the_package_does_not_define_is_refused(self):
        self.repository.write_guide(
            CORRECT_GUIDE.replace("WIDGET_REFUSED", "WIDGET_DENIED"))
        findings = self.repository.audit()
        self.assertEqual([finding.kind for finding in findings],
                         ["unknown refusal or status code"])
        self.assertEqual(findings[0].claim, "WIDGET_DENIED")

    def test_a_lower_case_refusal_code_is_refused_too(self):
        # This repository writes almost every refusal code, status value and
        # field name in lower case with underscores. A rule that only read
        # upper case constants would pass nearly every real refusal code,
        # right or wrong.
        self.repository.write_guide(
            CORRECT_GUIDE.replace("`WIDGET_REFUSED`", "`widget_declined`"))
        findings = self.repository.audit()
        self.assertEqual([finding.kind for finding in findings],
                         ["unknown refusal or status code"])
        self.assertEqual(findings[0].claim, "widget_declined")

    def test_a_lower_case_code_the_package_defines_is_accepted(self):
        # The negative control for the same rule. "widget_refused" is the
        # string the fixture source really raises.
        self.repository.write_guide(
            CORRECT_GUIDE.replace("`WIDGET_REFUSED`", "`widget_refused`"))
        self.assertEqual(self.repository.audit(), [])

    def test_a_single_lower_case_word_is_not_decided(self):
        # A word with no underscore, such as "status", is too common to decide
        # from a name alone. The rule stays silent rather than guessing.
        self.repository.write_guide(
            CORRECT_GUIDE + "\nThe field is `elsewhere`.\n")
        self.assertEqual(self.repository.audit(), [])

    def test_a_service_address_the_package_does_not_serve_is_refused(self):
        # A reader pastes an address straight into a request, so a renamed
        # route has to fail here rather than at the reader's terminal.
        self.repository.write_guide(
            CORRECT_GUIDE.replace("/api/v1/widget", "/api/v1/widgets"))
        findings = self.repository.audit()
        self.assertEqual([finding.kind for finding in findings],
                         ["unknown service address"])
        self.assertEqual(findings[0].claim, "/api/v1/widgets")

    def test_a_declared_reader_supplied_name_is_accepted(self):
        # An example that asks the reader to supply a value names something
        # the package will never define. It is declared once, with its reason.
        self.repository.write_guide(
            CORRECT_GUIDE + "\nSupply `your_configured_tracer`.\n")
        self.assertEqual(self.repository.kinds(),
                         ["unknown refusal or status code"])
        self.repository.write_map(reader_supplied=["your_configured_tracer"])
        self.assertEqual(self.repository.audit(), [])

    def test_a_class_the_package_does_not_define_is_refused(self):
        self.repository.write_guide(
            CORRECT_GUIDE.replace("`WidgetRequest`", "`WidgetEnvelope`"))
        findings = self.repository.audit()
        self.assertEqual([finding.kind for finding in findings],
                         ["unknown name"])
        self.assertEqual(findings[0].claim, "WidgetEnvelope")

    def test_a_dotted_path_the_package_does_not_define_is_refused(self):
        self.repository.write_guide(
            CORRECT_GUIDE.replace("`core.widget.run_widget`",
                                  "`core.gadget.run_gadget`"))
        findings = self.repository.audit()
        self.assertEqual([finding.kind for finding in findings],
                         ["unknown name"])

    def test_a_member_of_a_class_the_package_does_not_define_is_refused(self):
        # The shape that let `ServiceHttp._search` through: a function of that
        # member name exists elsewhere in the package, but no class of that
        # class name does, so reading the last name alone accepted it.
        self.repository.write_guide(
            CORRECT_GUIDE + "\nIt is built by `WidgetEnvelope.run_widget`.\n")
        findings = self.repository.audit()
        self.assertEqual([finding.kind for finding in findings],
                         ["unknown name"])
        self.assertEqual(findings[0].claim, "WidgetEnvelope.run_widget")

    def test_a_name_its_module_does_not_define_is_refused(self):
        # The module is real, so reading the leading part alone accepted any
        # name after it.
        self.repository.write_guide(
            CORRECT_GUIDE.replace("`core.widget.run_widget`",
                                  "`core.widget.run_gadget`"))
        findings = self.repository.audit()
        self.assertEqual([finding.kind for finding in findings],
                         ["unknown name"])
        self.assertEqual(findings[0].claim, "core.widget.run_gadget")

    def test_a_member_its_class_defines_is_accepted(self):
        self.repository.write_guide(
            CORRECT_GUIDE + "\nIts version is `WidgetRequest.record_type`, "
            "also written `core.widget.WidgetRequest.record_type`.\n")
        self.assertEqual(self.repository.audit(), [])

    def test_a_package_file_name_resolves_to_its_module(self):
        self.repository.write_guide(
            CORRECT_GUIDE + "\nThe source is `widget.py`.\n")
        self.assertEqual(self.repository.audit(), [])
        self.repository.write_guide(
            CORRECT_GUIDE + "\nThe source is `gadget.py`.\n")
        self.assertEqual(self.repository.kinds(), ["unknown name"])

    def test_part_of_a_longer_code_is_not_that_code(self):
        # A truncated code appears inside the real one, so a search for the
        # text anywhere in the package accepted it.
        self.repository.write_guide(
            CORRECT_GUIDE.replace("`WIDGET_REFUSED`", "`WIDGET_REFUSE`"))
        findings = self.repository.audit()
        self.assertEqual([finding.kind for finding in findings],
                         ["unknown refusal or status code"])
        self.assertEqual(findings[0].claim, "WIDGET_REFUSE")

    def test_a_record_type_only_a_check_spells_is_refused(self):
        # The shape that let `service_request_limits/v2` through: a check
        # sends that version to show it is refused, and a search of the whole
        # package then found it and accepted the guide.
        self.repository.write_guide(
            CORRECT_GUIDE + "\nA request is `widget_request/v9`.\n")
        findings = self.repository.audit()
        self.assertEqual([finding.kind for finding in findings],
                         ["unknown record type"])
        self.assertEqual(findings[0].claim, "widget_request/v9")

    def test_a_stand_in_only_a_check_builds_is_refused(self):
        self.repository.write_guide(
            CORRECT_GUIDE + "\nA host installs `RetiredWidgetHook`.\n")
        findings = self.repository.audit()
        self.assertEqual([finding.kind for finding in findings],
                         ["unknown name"])

    def test_a_check_module_and_its_entry_point_are_accepted(self):
        self.repository.write_guide(
            CORRECT_GUIDE + "\nRun `core.widget_checks.self_test` to check "
            "it, from `widget_checks.py`.\n")
        self.assertEqual(self.repository.audit(), [])

    def test_the_finding_names_the_guide_and_the_line(self):
        # A finding a reader cannot act on is not much use. Give the file and
        # the line the claim sits on.
        self.repository.write_guide(
            CORRECT_GUIDE.replace("WIDGET_REFUSED", "WIDGET_DENIED"))
        finding = self.repository.audit()[0]
        self.assertTrue(finding.location.endswith("widget/README.md"),
                        finding.location)
        expected = CORRECT_GUIDE.replace(
            "WIDGET_REFUSED", "WIDGET_DENIED").splitlines().index(
                "`WIDGET_DENIED`.") + 1
        self.assertEqual(finding.line, expected)
        self.assertIn("WIDGET_DENIED", finding.render())

    def test_a_declared_external_name_is_accepted(self):
        # The escape hatch has to work, and it has to be written down. A name
        # from another project is declared once, with its reason.
        self.repository.write_guide(
            CORRECT_GUIDE + "\nA host supplies `FastMCP`.\n")
        self.assertEqual(self.repository.kinds(), ["unknown name"])
        self.repository.write_map(external=["FastMCP"])
        self.assertEqual(self.repository.audit(), [])

    def test_a_declared_example_record_type_is_accepted(self):
        self.repository.write_guide(
            CORRECT_GUIDE + "\nAn example carries `invoice/v1`.\n")
        self.assertEqual(self.repository.kinds(), ["unknown record type"])
        self.repository.write_map(examples=["invoice/v1"])
        self.assertEqual(self.repository.audit(), [])


class RepositoryFileNameTests(unittest.TestCase):
    """A name a guide cites from repository data outside the package.

    The declaration is not an exemption: it names the file that holds the name,
    and the check reads that file. Each known-wrong case is a declaration the
    file no longer supports.
    """

    GUIDE = (CORRECT_GUIDE + "\nThe measurement reads the `held_back` requests "
             "of `widget_queries/v1`.\n")
    DATA = "examples/widget/queries.json"
    DECLARED = {"held_back": DATA, "widget_queries/v1": DATA}

    def setUp(self):
        self.repository = FixtureRepository()
        self.addCleanup(self.repository.close)
        self.data = self.repository.root / self.DATA
        self.data.parent.mkdir(parents=True)
        self.write_data({"record_type": "widget_queries/v1",
                         "rows": [{"split": "held_back"}]})
        self.repository.write_guide(self.GUIDE)

    def write_data(self, document):
        self.data.write_text(json.dumps(document), "utf-8")

    def test_an_undeclared_name_from_repository_data_is_refused(self):
        self.assertEqual(self.repository.kinds(),
                         ["unknown record type", "unknown refusal or status code"])

    def test_a_name_declared_with_the_file_that_holds_it_is_accepted(self):
        self.repository.write_map(repository_files=self.DECLARED)
        self.assertEqual(self.repository.audit(), [])

    def test_a_name_its_declared_file_no_longer_holds_is_refused(self):
        # The data renamed the value. The declaration fails, and so does
        # every guide line that cites the old name.
        self.write_data({"record_type": "widget_queries/v1",
                         "rows": [{"split": "holdout"}]})
        self.repository.write_map(repository_files=self.DECLARED)
        findings = self.repository.audit()
        self.assertEqual(sorted((finding.kind, finding.claim) for finding in findings),
                         [("declared name not in its file", "held_back"),
                          ("unknown refusal or status code", "held_back")])

    def test_part_of_a_longer_value_is_not_that_value(self):
        self.write_data({"record_type": "widget_queries/v1",
                         "rows": [{"held_back_when": "never"}]})
        self.repository.write_map(repository_files=self.DECLARED)
        self.assertIn("declared name not in its file", self.repository.kinds())

    def test_a_declared_file_outside_the_repository_is_refused(self):
        outside = tempfile.TemporaryDirectory()
        self.addCleanup(outside.cleanup)
        stray = Path(outside.name) / "queries.json"
        stray.write_text(self.data.read_text("utf-8"), "utf-8")
        relative = os.path.relpath(stray, self.repository.root)
        for file in (relative, str(stray)):
            with self.subTest(file=file):
                self.repository.write_map(repository_files={
                    "held_back": file, "widget_queries/v1": self.DATA})
                self.assertEqual(self.repository.kinds(),
                                 ["declared name without its file",
                                  "unknown refusal or status code"])

    def test_a_declared_file_that_is_missing_is_refused(self):
        self.repository.write_map(repository_files={
            "held_back": "examples/widget/missing.json",
            "widget_queries/v1": self.DATA})
        self.assertEqual(self.repository.kinds(),
                         ["declared name without its file",
                          "unknown refusal or status code"])


class MapShapeTests(unittest.TestCase):
    """Known-wrong cases: a map whose loaded meaning is not what it says."""

    def setUp(self):
        self.repository = FixtureRepository()
        self.addCleanup(self.repository.close)

    def test_a_map_key_written_twice_is_refused(self):
        # YAML keeps only the last of two equal keys, silently, so a merge
        # that adds the same guide twice would hide one of its descriptions.
        path = self.repository.root / tool.MAP_PATH
        text = path.read_text("utf-8").replace(
            "guides:\n", "guides:\n  docs/components/widget/README.md: a second, "
            "different description\n", 1)
        path.write_text(text, "utf-8")
        findings = self.repository.audit()
        self.assertEqual([finding.kind for finding in findings],
                         ["duplicate map key"])
        self.assertEqual(findings[0].claim, "docs/components/widget/README.md")

    def test_a_name_declared_in_two_lists_is_refused(self):
        # One name, two claims about what it is: another project's name and a
        # value that a repository file holds cannot both be true.
        data = self.repository.root / "examples" / "widget" / "queries.json"
        data.parent.mkdir(parents=True)
        data.write_text(json.dumps({"split": "held_back"}), "utf-8")
        self.repository.write_guide(
            CORRECT_GUIDE + "\nIt reads the `held_back` requests.\n")
        self.repository.write_map(
            external=["held_back"],
            repository_files={"held_back": "examples/widget/queries.json"})
        findings = self.repository.audit()
        self.assertEqual([(finding.kind, finding.claim) for finding in findings],
                         [("name declared more than once", "held_back")])


class CoverageTests(unittest.TestCase):
    """Known-wrong cases: a component or a guide is missing from the map."""

    def setUp(self):
        self.repository = FixtureRepository()
        self.addCleanup(self.repository.close)

    def test_a_registered_boundary_with_no_guide_is_refused(self):
        # This is the drift that a claim check alone never catches: the
        # runtime gains a boundary and no guide mentions it.
        self.repository.write_map(components={})
        findings = self.repository.audit()
        self.assertEqual([finding.kind for finding in findings],
                         ["undocumented component"])
        self.assertEqual(findings[0].claim, "fixture operation")
        self.assertIn("core", findings[0].detail)

    def test_a_map_entry_pointing_at_a_missing_file_is_refused(self):
        self.repository.write_map(
            components={"core": "docs/components/widget/GONE.md"},
            guides=["docs/components/widget/README.md",
                    "docs/components/widget/GONE.md"])
        self.assertEqual(self.repository.kinds(),
                         ["guide for nothing", "missing guide"])

    def test_a_guide_absent_from_the_map_is_refused(self):
        extra = self.repository.root / "docs" / "components" / "EXTRA.md"
        extra.write_text("# Extra\n\nNothing.\n", "utf-8")
        findings = self.repository.audit()
        self.assertEqual([finding.kind for finding in findings],
                         ["unregistered guide"])

    def test_a_missing_map_is_refused(self):
        (self.repository.root / tool.MAP_PATH).unlink()
        findings = self.repository.audit()
        self.assertEqual([finding.kind for finding in findings], ["missing map"])


class RegisterReadingTests(unittest.TestCase):
    """The rows come from the audited tree, and an unreadable register stops."""

    def setUp(self):
        self.repository = FixtureRepository()
        self.addCleanup(self.repository.close)

    def test_the_rows_come_from_the_audited_repository(self):
        # Known-wrong case for the opposite mistake: reading whichever copy of
        # the package is importable would return this repository's eighty-odd
        # boundaries while auditing a fixture that registers one.
        rows = tool._registered_boundaries(self.repository.root)
        self.assertEqual(rows, ({"boundary": "fixture operation",
                                 "envelope": "core.widget.run_widget"},))

    def test_an_unreadable_register_stops_instead_of_passing(self):
        # A coverage rule that quietly checks nothing is worse than no rule.
        (self.repository.root / tool.REGISTER_MODULE).unlink()
        with self.assertRaises(SystemExit):
            tool.audit(self.repository.root)

    def test_the_parsed_rows_match_the_imported_register(self):
        from loop_engine.core.boundary_registry import BOUNDARIES

        parsed = tool._registered_boundaries(REPOSITORY)
        self.assertEqual(
            parsed,
            tuple({"boundary": row["boundary"],
                   "envelope": row.get("envelope", "")} for row in BOUNDARIES))


class OwningDirectoryTests(unittest.TestCase):
    """The envelope-to-directory rule the coverage check depends on."""

    def setUp(self):
        self.repository = FixtureRepository()
        self.addCleanup(self.repository.close)
        self.package = self.repository.root / "src" / "loop_engine"

    def test_a_module_envelope_resolves_to_its_directory(self):
        self.assertEqual(
            tool.owning_directory("core.widget.run_widget", self.package),
            "core")

    def test_a_template_selector_is_ignored(self):
        self.assertEqual(
            tool.owning_directory("core.widget:some_case", self.package),
            "core")

    def test_a_package_root_module_resolves_to_the_root(self):
        (self.package / "widget_cli.py").write_text("x = 1\n", "utf-8")
        self.assertEqual(
            tool.owning_directory("widget_cli.widget_command", self.package),
            ".")

    def test_an_envelope_that_resolves_to_nothing_is_reported_not_guessed(self):
        # An unresolvable envelope must not silently land in some directory
        # that happens to have a guide.
        self.assertEqual(
            tool.owning_directory("nowhere.at.all", self.package), "")


class DocumentedCheckTests(unittest.TestCase):
    """Known-wrong cases for the commands a guide tells a reader to run.

    A command can name a module that is gone, or ask a report for a field the
    source only builds at run time. Neither is visible by reading the source,
    so these run the command the way a reader would.
    """

    #: A real package module whose self test is small, fast and reports
    #: ``all_passed``. It is used as a stand-in for any documented check.
    MODULE = "loop_engine.core.boundary_registry"

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.guides = self.root / "docs" / "components"
        self.guides.mkdir(parents=True)
        self.guide = self.guides / "README.md"

    def write(self, module: str, expression: str) -> None:
        self.guide.write_text(
            "# Guide\n\n## How to check it\n\n```bash\n"
            "PYTHONPATH=src python -c \\\n"
            f"  'from {module} import self_test; print({expression})'\n"
            "```\n", "utf-8")

    def run_checks(self):
        return tool.run_documented_checks(self.guides, REPOSITORY)

    def test_a_working_command_produces_no_finding(self):
        # The negative control for this rule.
        self.write(self.MODULE, 'self_test()["all_passed"]')
        self.assertEqual(self.run_checks(), [])

    def test_a_report_field_the_source_does_not_build_is_refused(self):
        # This is the defect the rule was added for. The field exists only in
        # the returned dictionary, so no amount of reading the source
        # decides it, and the reader meets a KeyError.
        self.write(self.MODULE, 'self_test()["no_such_summary_field"]')
        findings = self.run_checks()
        self.assertEqual([finding.kind for finding in findings],
                         ["documented check fails"])
        self.assertIn("KeyError", findings[0].detail)

    def test_a_module_that_is_gone_is_refused(self):
        self.write("loop_engine.core.no_such_module", "self_test()")
        findings = self.run_checks()
        self.assertEqual([finding.kind for finding in findings],
                         ["documented check fails"])
        self.assertIn("ModuleNotFoundError", findings[0].detail)

    def test_both_quote_styles_are_found(self):
        # The guides write the command with single and with double quotes.
        # A rule that only saw one style would silently skip the other.
        self.guide.write_text(
            "```bash\n"
            f"python -c \"from {self.MODULE} import self_test; "
            "print(self_test())\"\n"
            f"python -c 'from {self.MODULE} import self_test; "
            "print(self_test())'\n```\n", "utf-8")
        found = list(tool.documented_checks(self.guides, self.root))
        self.assertEqual([row[2] for row in found], [self.MODULE] * 2)

    def test_the_default_audit_does_not_run_anything(self):
        # Rules one to three must stay fast and effect-free. A guide with a
        # command that would fail is not run by audit().
        self.write(self.MODULE, 'self_test()["no_such_summary_field"]')
        kinds = {finding.kind for finding
                 in tool.audit(REPOSITORY, boundaries=())}
        self.assertNotIn("documented check fails", kinds)


class RealRepositoryTests(unittest.TestCase):
    """The gate. The committed guides must match the committed source."""

    def test_every_component_guide_matches_the_source(self):
        findings = tool.audit(REPOSITORY)
        self.assertEqual(
            [finding.render() for finding in findings], [],
            "component guide drift; repair the guide or declare the name in "
            + tool.MAP_PATH)

    def test_every_registered_boundary_directory_has_a_guide(self):
        # Stated separately from the claim check so the reason a build went
        # red is legible without reading the whole finding list.
        self.assertTrue(tool._registered_boundaries(REPOSITORY),
                        "the boundary register is empty")
        uncovered = [finding.render() for finding in tool.audit(REPOSITORY)
                     if finding.kind in ("undocumented component",
                                         "missing guide")]
        self.assertEqual(uncovered, [])

    def test_the_command_exits_non_zero_when_a_guide_drifts(self):
        # The gate is the exit status, not the printed text.
        repository = FixtureRepository()
        self.addCleanup(repository.close)
        repository.write_guide(
            CORRECT_GUIDE.replace("WIDGET_REFUSED", "WIDGET_DENIED"))
        self.assertEqual(
            tool.main(["--repository", str(repository.root),
                       "--format", "json"]), 1)
        repository.write_guide(CORRECT_GUIDE)
        self.assertEqual(tool.main(["--repository", str(repository.root)]), 0)


if __name__ == "__main__":
    unittest.main()
