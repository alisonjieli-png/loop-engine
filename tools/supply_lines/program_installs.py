"""Line program_installs: one install recipe and typed wrapper per widely used command-line program.

```text
One program (declared in program_sources.json: formula, executable, version arguments, repository, effects)
├── facts
│   ├── the Homebrew formula (formulae.brew.sh/api/formula/<name>.json): version, licence, homepage,
│   │   source archive with its SHA-256, one bottle per platform with its SHA-256
│   ├── the Homebrew install counts of the last 365 days (formulae.brew.sh analytics)
│   ├── homebrew-core's licence text at its head commit (the formula data is homebrew-core's)
│   └── the upstream GitHub repository: its licence (interface and text must agree) and the latest
│       release's assets with the SHA-256 digests GitHub publishes
├── licence gate: the program's licence (the formula's SPDX expression) must be allowlisted, and a
│   repository licence that is known must be allowlisted too
└── one package (kind code_module, form binary_install)
    ├── install.json: program_install_recipe/v1, the pinned version and, per platform, the Homebrew
    │   command with the bottle's published SHA-256; the source archive; the release assets
    ├── <program>_program.py: a wrapper that checks the arguments (a list of strings, no NUL byte,
    │   bounded), the working folder and the time limit before it starts the program, never through
    │   a shell, and raises ProgramError on a failing exit
    ├── test_<program>_program.py: known-wrong arguments that must start nothing, the recipe's pins,
    │   and a smoke test that is skipped cleanly when the program is not installed
    └── README.md, LICENSE (generated code, MIT), UPSTREAM-LICENSE (homebrew-core), ATTRIBUTION.md
```

No binary is downloaded or re-hosted: the recipe points at the upstream
addresses and carries their published checksums.
"""
from __future__ import annotations

import json
import re
import shutil
import urllib.parse
from collections import Counter
from pathlib import Path

from .licences import KNOWN_LICENCE_REFUSALS, decide, repository_licence
from .openapi_operations import literal, run_tests, snake
from .packaging import LICENCE_NAME, UPSTREAM_LICENCE_NAME, PackageFile, SupplyPackage, build
from .reading import github_blob_address, https_address
from .records import (
    BLOCKED_BY_STATIC_CHECK, GENERATED_CODE_LICENCE, GENERATED_TEST_FAILED, LICENCE_TEXT, PROGRAM_INSTALLS,
    SupplyRecordError, fact_source, licence_allowed, provenance, refusal, upstream_key)

GENERATOR_VERSION = "1.0.0"
SOURCES_FILE = Path(__file__).with_name("program_sources.json")
SOURCES_RECORD_TYPE = "library_supply_program_sources/v1"
RECIPE_RECORD_TYPE = "program_install_recipe/v1"
FORMULAE_HOST = "formulae.brew.sh"
HOSTS = (FORMULAE_HOST,)
HOMEBREW_CORE = "Homebrew/homebrew-core"
ANALYTICS_URL = https_address(FORMULAE_HOST, "api/analytics/install-on-request/365d.json")
NATIVE_FORMAT = "program_install_recipe"
EFFECTS = ("network", "writes_fs", "reads_secret")
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")


def read_sources(path: Path = SOURCES_FILE) -> list:
    record = json.loads(Path(path).read_text(encoding="utf-8"))
    if record.get("record_type") != SOURCES_RECORD_TYPE:
        raise ValueError(f"expected {SOURCES_RECORD_TYPE}")
    rows, seen = [], set()
    for formula, program, arguments, repository, effects, category in record["programs"]:
        if formula in seen or not re.fullmatch(r"[a-z0-9][a-z0-9@.+_-]{0,60}", formula) \
                or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,60}", program) \
                or any(effect not in EFFECTS for effect in effects) \
                or not all(isinstance(argument, str) for argument in arguments):
            raise ValueError(f"program_sources.json: the row of {formula} is not a declared program")
        seen.add(formula)
        rows.append({"formula": formula, "program": program, "version_arguments": list(arguments),
                     "repository": repository, "effects": list(effects), "category": category})
    return rows


def platform_bottles(files: dict) -> dict:
    """The bottle Homebrew installs on each platform family, by the tags of its formula."""
    tags = list(files or {})
    chosen = {}
    if "all" in tags:
        chosen = {name: "all" for name in ("macos-arm64", "macos-x86_64", "linux-x86_64", "linux-arm64")}
    mac_arm = [tag for tag in tags if tag.startswith("arm64_") and tag != "arm64_linux"]
    mac_intel = [tag for tag in tags if not tag.startswith("arm64_") and not tag.endswith("_linux") and tag != "all"]
    if mac_arm:
        chosen["macos-arm64"] = mac_arm[0]
    if mac_intel:
        chosen["macos-x86_64"] = mac_intel[0]
    if "x86_64_linux" in tags:
        chosen["linux-x86_64"] = "x86_64_linux"
    if "arm64_linux" in tags:
        chosen["linux-arm64"] = "arm64_linux"
    return chosen


def recipe(row: dict, formula: dict, release: "dict | None") -> dict:
    """program_install_recipe/v1: the pinned version, per platform the command and the bottle's checksum."""
    version = formula["versions"]["stable"]
    files = ((formula.get("bottle") or {}).get("stable") or {}).get("files") or {}
    platforms = {}
    for platform, tag in platform_bottles(files).items():
        bottle = files[tag]
        if not _DIGEST.match(str(bottle.get("sha256", ""))):
            continue
        platforms[platform] = {"method": "homebrew", "command": ["brew", "install", formula["name"]],
                               "bottle": {"tag": tag, "url": bottle.get("url"), "sha256": bottle["sha256"]}}
    stable = (formula.get("urls") or {}).get("stable") or {}
    source = {"url": stable.get("url"), "sha256": stable.get("checksum")} \
        if _DIGEST.match(str(stable.get("checksum") or "")) else None
    assets = []
    if release and version in str(release.get("tagName") or ""):
        for asset in (release.get("releaseAssets") or {}).get("nodes") or ():
            digest = str(asset.get("digest") or "")
            if digest.startswith("sha256:") and _DIGEST.match(digest[7:]):
                assets.append({"name": asset["name"], "url": asset["downloadUrl"], "sha256": digest[7:],
                               "size_bytes": asset.get("size")})
    return {"record_type": RECIPE_RECORD_TYPE, "program": row["program"], "formula": formula["name"],
            "version": version, "licence": formula.get("license"), "homepage": formula.get("homepage"),
            "platforms": platforms, "source": source,
            "release": ({"repository": row["repository"], "tag": release["tagName"], "assets": assets}
                        if assets else None),
            "executables": list(row.get("executables") or [row["program"]]),
            "verify": {"arguments": [row["program"], *row["version_arguments"]],
                       "basis": "declared_version_arguments" if row.get("declared", True) else
                       "default_version_flag_the_program_may_not_support"},
            "checksums": "published by Homebrew (bottles and source archive) and by GitHub (release asset digests); "
                         "Baltor re-hosts no binary"}


WRAPPER = '''"""{title}

A typed wrapper for the command-line program {program} {version} ({description}). It checks the arguments before it
starts the program and never uses a shell. Install the program first; install.json holds the pinned recipe with the
published checksums. Baltor generated this file from the Homebrew formula {formula}.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

PROGRAM = {program!r}
FORMULA = {formula!r}
VERSION = {version!r}
VERSION_ARGUMENTS = {version_arguments}
INSTALL_HINT = {hint!r}
MAXIMUM_ARGUMENTS = 512
MAXIMUM_ARGUMENT_CHARACTERS = 32768
MAXIMUM_SECONDS = 86400


class ProgramError(RuntimeError):
    """The program ended with a failing exit status; its output is kept."""

    def __init__(self, returncode, stdout, stderr):
        super().__init__(f"{{PROGRAM}} exited with status {{returncode}}: {{(stderr or stdout or '').strip()[:300]}}")
        self.returncode, self.stdout, self.stderr = returncode, stdout, stderr


def locate():
    """The program's path on this machine, or None when it is not installed."""
    return shutil.which(PROGRAM)


def check_arguments(arguments):
    """The arguments as a list of strings, or refuse one string, a non-string, a NUL byte or an unbounded list."""
    if isinstance(arguments, (str, bytes)):
        raise TypeError("pass the arguments as a list of strings, not as one string")
    values = list(arguments)
    if len(values) > MAXIMUM_ARGUMENTS:
        raise ValueError(f"at most {{MAXIMUM_ARGUMENTS}} arguments")
    for index, value in enumerate(values):
        if not isinstance(value, str):
            raise TypeError(f"argument {{index}} must be a string, not {{type(value).__name__}}")
        if "\\x00" in value:
            raise ValueError(f"argument {{index}} holds a NUL byte")
        if len(value) > MAXIMUM_ARGUMENT_CHARACTERS:
            raise ValueError(f"argument {{index}} is longer than {{MAXIMUM_ARGUMENT_CHARACTERS}} characters")
    return values


def run(arguments, *, cwd=None, timeout=60.0, input_text=None, check=True, runner=subprocess.run):
    """Run {program} with the checked arguments and return the completed process (text output captured).

    Raises TypeError or ValueError for an argument, a time limit or an input that breaks the checks,
    NotADirectoryError for a working folder that does not exist and FileNotFoundError when the program is not
    installed, all before anything starts; ProgramError when check is true and the exit status is not zero.
    """
    values = check_arguments(arguments)
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 0 < timeout <= MAXIMUM_SECONDS:
        raise ValueError(f"the time limit is a number of seconds above 0 and at most {{MAXIMUM_SECONDS}}")
    if input_text is not None and not isinstance(input_text, str):
        raise TypeError("input_text is a string")
    if cwd is not None and not Path(cwd).is_dir():
        raise NotADirectoryError(str(cwd))
    executable = locate()
    if executable is None:
        raise FileNotFoundError(f"{{PROGRAM}} is not installed: {{INSTALL_HINT}}")
    completed = runner([executable, *values], cwd=cwd, timeout=timeout, input=input_text, capture_output=True,
                       text=True, check=False, shell=False)
    if check and completed.returncode != 0:
        raise ProgramError(completed.returncode, completed.stdout, completed.stderr)
    return completed


def version(*, runner=subprocess.run):
    """The first line the program prints for its version arguments."""
    completed = run(list(VERSION_ARGUMENTS), timeout=60, runner=runner)
    text = (completed.stdout or completed.stderr or "").strip()
    return text.splitlines()[0] if text else ""
'''

TESTS = '''"""Offline tests of the {program} wrapper.

Known-wrong arguments must start nothing, the recipe must pin the version and checksums, and the smoke test runs
only when {program} is installed.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import {module} as wrapper  # noqa: E402

RECIPE = json.loads(Path(__file__).with_name("install.json").read_text(encoding="utf-8"))


class _Recorder:
    """Stands in for subprocess.run: it records the command and starts nothing."""

    def __init__(self):
        self.calls = []

    def __call__(self, command, **options):
        self.calls.append((command, options))

        class Completed:
            returncode, stdout, stderr = 0, "ok", ""
        return Completed()


class {class_name}(unittest.TestCase):
    def setUp(self):
        self.recorder = _Recorder()
        self.located = wrapper.locate
        wrapper.locate = lambda: "/usr/bin/{program}"

    def tearDown(self):
        wrapper.locate = self.located

    def test_the_checked_arguments_reach_the_program_without_a_shell(self):
        wrapper.run(["--help", "a file.txt"], runner=self.recorder)
        [(command, options)] = self.recorder.calls
        self.assertEqual(command, ["/usr/bin/{program}", "--help", "a file.txt"])
        self.assertIs(options["shell"], False)

    def test_known_wrong_arguments_start_nothing(self):
        for arguments, error in (("--help", TypeError), ([1], TypeError), (["a\\x00b"], ValueError),
                                 (["x"] * (wrapper.MAXIMUM_ARGUMENTS + 1), ValueError),
                                 (["x" * (wrapper.MAXIMUM_ARGUMENT_CHARACTERS + 1)], ValueError)):
            with self.assertRaises(error):
                wrapper.run(arguments, runner=self.recorder)
        for timeout in (0, -1, True, "60", wrapper.MAXIMUM_SECONDS + 1):
            with self.assertRaises(ValueError):
                wrapper.run([], timeout=timeout, runner=self.recorder)
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(NotADirectoryError):
                wrapper.run([], cwd=os.path.join(folder, "missing"), runner=self.recorder)
        self.assertEqual(self.recorder.calls, [])

    def test_known_wrong_a_missing_program_starts_nothing_and_names_the_install(self):
        wrapper.locate = lambda: None
        with self.assertRaises(FileNotFoundError) as caught:
            wrapper.run([], runner=self.recorder)
        self.assertIn(wrapper.FORMULA, str(caught.exception))
        self.assertEqual(self.recorder.calls, [])

    def test_the_recipe_pins_the_version_and_the_published_checksums(self):
        self.assertEqual((RECIPE["record_type"], RECIPE["program"], RECIPE["version"]),
                         ("program_install_recipe/v1", wrapper.PROGRAM, wrapper.VERSION))
        self.assertTrue(RECIPE["platforms"])
        for platform, step in RECIPE["platforms"].items():
            self.assertEqual(step["command"], ["brew", "install", wrapper.FORMULA], platform)
            self.assertRegex(step["bottle"]["sha256"], "^[0-9a-f]{{64}}$")
        for asset in (RECIPE.get("release") or {{}}).get("assets", []):
            self.assertRegex(asset["sha256"], "^[0-9a-f]{{64}}$")

{smoke}

if __name__ == "__main__":
    unittest.main()
'''


#: The smoke test of a program whose version arguments a person declared: it prints its version.
SMOKE_DECLARED = '''    @unittest.skipUnless(shutil.which("{program}"), "{program} is not installed on this machine")
    def test_smoke_the_installed_program_prints_its_version(self):
        wrapper.locate = self.located
        self.assertTrue(wrapper.version())
'''
#: The smoke test of a program taken from the whole catalogue, whose version flag nobody declared: it starts and
#: ends within the time limit, whatever its exit status.
SMOKE_CATALOGUE = '''    @unittest.skipUnless(shutil.which("{program}"), "{program} is not installed on this machine")
    def test_smoke_the_installed_program_starts_and_ends(self):
        wrapper.locate = self.located
        completed = wrapper.run(list(wrapper.VERSION_ARGUMENTS), timeout=60, check=False)
        self.assertIsInstance(completed.returncode, int)
'''


def source_line(plan: dict) -> str:
    source = plan.get("source")
    if not source:
        return "Homebrew publishes no source archive checksum for this formula (it builds from a pinned revision)."
    return f"Source archive: `{source['url']}`, SHA-256 `{source['sha256']}`."


def readme(row: dict, formula: dict, plan: dict, installs: "int | None", program_licence: str,
           repository_licence_text: str) -> str:
    rows = [f"| {platform} | `brew install {formula['name']}` | `{step['bottle']['tag']}` | `{step['bottle']['sha256']}` |"
            for platform, step in plan["platforms"].items()]
    release = plan.get("release")
    assets = ""
    if release:
        assets = "\n".join([f"\nThe GitHub release `{release['tag']}` of `{release['repository']}` publishes these "
                            "assets with their SHA-256 digests:\n", "| Asset | SHA-256 |", "|---|---|",
                            *[f"| `{asset['name']}` | `{asset['sha256']}` |" for asset in release["assets"][:40]]])
    words = {"network": "uses the network", "writes_fs": "writes files", "reads_secret": "reads credentials"}
    effects = ", ".join(["starts a process", *(words[effect] for effect in row["effects"])])
    if not row.get("declared", True):
        effects += (". The formula does not say what the program does, so this package declares the network and "
                    "file writes to be safe")
    executables = row.get("executables") or [row["program"]]
    others = [name for name in executables if name != row["program"]]
    module = f"{snake(row['program'])}_program"
    return f"""# {row['program']} {plan['version']}: install recipe and typed wrapper

{formula.get('desc') or ''}. Homepage: {formula.get('homepage') or 'not given'}.
The program is licensed {program_licence} (Homebrew formula `{formula['name']}`{repository_licence_text}).
{f'Homebrew counted {installs:,} installs on request in the last 365 days.' if installs else ''}

## Install

| Platform | Command | Bottle | Bottle SHA-256 |
|---|---|---|---|
{chr(10).join(rows)}

{source_line(plan)}
{assets}

Baltor re-hosts no binary. `install.json` holds the same recipe as data
(`program_install_recipe/v1`).

## Use

```python
import {module}

completed = {module}.run(["--help"])
print(completed.stdout)
```

{('The formula also installs ' + ', '.join(f'`{name}`' for name in others[:20]) + '; the wrapper runs `' + row['program'] + '`.' + chr(10)) if others else ''}
`run` checks that the arguments are a list of strings without NUL bytes,
that the working folder exists and that the time limit is sane before it
starts `{row['program']}`, and it never uses a shell. It raises
`FileNotFoundError` with the install command when the program is missing and
`ProgramError` when the program exits with a failing status.

What running it does: {effects}.

## Tests

```bash
python -m unittest test_{module}
```

The smoke test is skipped when `{row['program']}` is not installed.
"""


CATALOGUE_URL = https_address(FORMULAE_HOST, "api/formula.json")
DEFAULT_VERSION_ARGUMENTS = ("--version",)
#: What a program from the whole catalogue is declared to do: its formula does not say, so the package declares the
#: network and file writes, which a step must authorize before it is offered the package.
UNDECLARED_EFFECTS = ("network", "writes_fs")
_GITHUB_PROJECT = re.compile(r"https://github\.com/([A-Za-z0-9][A-Za-z0-9-]{0,38})/([A-Za-z0-9._-]{1,100}?)(?:\.git)?(?:/|$)")


def github_project(formula: dict) -> "str | None":
    """The formula's GitHub repository, from its homepage or its stable source address."""
    for address in (formula.get("homepage"), ((formula.get("urls") or {}).get("stable") or {}).get("url")):
        match = _GITHUB_PROJECT.match(str(address or ""))
        if match:
            return f"{match.group(1)}/{match.group(2)}"
    return None


def catalogue_rows(formulae, curated) -> tuple:
    """(rows, skipped) for every formula of the catalogue the curated declaration does not describe."""
    rows, skipped = [], Counter()
    for formula in formulae:
        name = formula.get("name")
        if not name or name in curated:
            skipped["curated_or_unnamed"] += 1
            continue
        executables = sorted({value for value in formula.get("executables") or () if isinstance(value, str) and
                              re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,60}", value)})
        if not executables:
            skipped["no_executables"] += 1
            continue
        program = name if name in executables else executables[0]
        rows.append({"formula": name, "program": program, "version_arguments": list(DEFAULT_VERSION_ARGUMENTS),
                     "repository": github_project(formula), "effects": list(UNDECLARED_EFFECTS), "category": "catalogue",
                     "executables": executables, "declared": False, "formula_document": formula})
    return rows, dict(skipped)


def generate(reader, rows, *, code_revision: str, licence_text: bytes, generated_on: str, staging: Path,
             repository_facts: dict, catalogue=None) -> tuple:
    """(built, refusals, facts, summary) of every declared program, and of the catalogue's rows when given.

    A catalogue row carries its formula from the one catalogue read (formula.json); its licence is the formula's
    license field, and its repository gives only the release assets, so no licence read is made per program."""
    built, refused, facts, summary = [], [], {}, Counter()
    generator = {"identity": "tools/supply_lines/program_installs.py", "version": GENERATOR_VERSION,
                 "code_revision": code_revision}
    core = repository_facts.get(HOMEBREW_CORE.lower()) or {}
    core_commit = (((core.get("defaultBranchRef") or {}).get("target")) or {}).get("oid")
    core_licence = repository_licence(reader, HOMEBREW_CORE, core_commit) if core_commit else None
    if core_licence is None or not core_licence.allowed:
        raise SupplyRecordError("licence_signals_disagree", "homebrew-core's licence could not be decided")
    analytics = reader.get(ANALYTICS_URL)
    counts = {}
    if analytics.status == 200:
        facts[analytics.sha256] = analytics.body
        for item in json.loads(analytics.body).get("items") or ():
            try:
                counts[item.get("formula")] = int(str(item.get("count", "0")).replace(",", ""))
            except ValueError:
                continue
    seen = set()
    if catalogue is not None:
        facts[catalogue.sha256] = catalogue.body
    for row in rows:
        name = row["formula"]
        if row.get("formula_document") is not None:
            answer, formula = catalogue, row["formula_document"]
        else:
            answer = reader.get(https_address(FORMULAE_HOST, f"api/formula/{urllib.parse.quote(name)}.json"))
            if answer.status != 200:
                refused.append(refusal(PROGRAM_INSTALLS, "not_a_command_line_program", name,
                                       f"formula answered {answer.status}"))
                continue
            facts[answer.sha256] = answer.body
            formula = json.loads(answer.body)
        if formula.get("deprecated") or formula.get("disabled"):
            refused.append(refusal(PROGRAM_INSTALLS, "formula_deprecated_or_disabled", name))
            continue
        program_licence = formula.get("license") or ""
        if not licence_allowed(program_licence):
            refused.append(refusal(PROGRAM_INSTALLS, "formula_licence_not_on_allowlist", name, str(program_licence)))
            continue
        release, repository_decision, repository_text = None, None, ""
        if row["repository"] and not row.get("declared", True):
            release = (repository_facts.get(row["repository"].lower()) or {}).get("latestRelease")
        elif row["repository"]:
            facts_row = repository_facts.get(row["repository"].lower())
            commit = (((facts_row or {}).get("defaultBranchRef") or {}).get("target") or {}).get("oid")
            if not facts_row or not commit:
                refused.append(refusal(PROGRAM_INSTALLS, "upstream_repository_unreadable", name, row["repository"]))
                continue
            repository_decision = decide(row["repository"], commit, reader.licence_text(row["repository"], commit))
            if repository_decision.reason in KNOWN_LICENCE_REFUSALS:
                refused.append(refusal(PROGRAM_INSTALLS, "licence_signals_disagree", name,
                                       f"{row['repository']}: {repository_decision.reason} "
                                       f"{repository_decision.github_spdx}"))
                continue
            release = facts_row.get("latestRelease")
            if repository_decision.allowed:
                repository_text = f"; its repository `{row['repository']}` is licensed {repository_decision.spdx}"
        plan = recipe(row, formula, release)
        if not plan["platforms"] and not plan["source"]:
            refused.append(refusal(PROGRAM_INSTALLS, "no_published_checksum", name))
            continue
        if row["program"] in seen:
            refused.append(refusal(PROGRAM_INSTALLS, "duplicate_program", name))
            continue
        try:
            built.append(_package(row, formula, plan, counts.get(name), program_licence, repository_text,
                                  repository_decision, core_licence, core_commit, answer, analytics, generator,
                                  licence_text, generated_on, staging, repository_facts))
        except SupplyRecordError as error:
            reason = error.code if error.code == BLOCKED_BY_STATIC_CHECK else GENERATED_TEST_FAILED
            refused.append(refusal(PROGRAM_INSTALLS, reason, name, str(error)[:280]))
            continue
        seen.add(row["program"])
        summary["smoke_ran" if shutil.which(row["program"]) else "smoke_skipped"] += 1
    return built, refused, facts, dict(summary)


def _package(row, formula, plan, installs, program_licence, repository_text, repository_decision, core_licence,
             core_commit, answer, analytics, generator, licence_text, generated_on, staging, repository_facts):
    module = f"{snake(row['program'])}_program"
    title = f"{row['program']} {plan['version']}: a typed wrapper and its install recipe"
    hint = (f"brew install {formula['name']} (Homebrew); install.json holds the recipe for each platform with "
            "the published checksums")
    wrapper = WRAPPER.format(title=title, program=row["program"], version=plan["version"], formula=formula["name"],
                             description=str(formula.get("desc") or "")[:120].replace("\\", "/").replace('"', "'"),
                             version_arguments=literal(tuple(row["version_arguments"])), hint=hint)
    class_name = "".join(part.capitalize() for part in module.split("_") if part)[:60] + "Test"
    smoke = (SMOKE_DECLARED if row.get("declared", True) else SMOKE_CATALOGUE).format(program=row["program"])
    tests = TESTS.format(program=row["program"], module=module, class_name=class_name, smoke=smoke)
    recipe_text = json.dumps(plan, indent=1, ensure_ascii=False) + "\n"
    folder = staging / module
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{module}.py").write_text(wrapper, encoding="utf-8")
    (folder / f"test_{module}.py").write_text(tests, encoding="utf-8")
    (folder / "install.json").write_text(recipe_text, encoding="utf-8")
    passed, count, output = run_tests(folder, module)
    shutil.rmtree(folder, ignore_errors=True)  # the package keeps the files; the staging copy is not needed
    if not passed:
        raise SupplyRecordError("generated_test_failed", output[-280:])
    text = readme(row, formula, plan, installs, program_licence, repository_text)
    files = [PackageFile(f"{module}.py", wrapper.encode(), "executable_tool"),
             PackageFile(f"test_{module}.py", tests.encode(), "executable_tool"),
             PackageFile("install.json", recipe_text.encode(), "configuration"),
             PackageFile("README.md", text.encode(), "other"),
             PackageFile(LICENCE_NAME, licence_text, "other", LICENCE_TEXT),
             PackageFile(UPSTREAM_LICENCE_NAME, core_licence.text, "other", LICENCE_TEXT,
                         {"url": github_blob_address(HOMEBREW_CORE, core_commit, core_licence.path),
                          "sha256": core_licence.sha256})]
    facts = [fact_source(answer.url, answer.retrieved_at, answer.sha256, len(answer.body), "formula",
                         spdx=core_licence.spdx, basis="homebrew_core_licence_at_its_head_commit",
                         evidence_sha256=core_licence.sha256),
             fact_source(github_blob_address(HOMEBREW_CORE, core_commit, core_licence.path),
                         answer.retrieved_at, core_licence.sha256, len(core_licence.text), "licence_text",
                         spdx=core_licence.spdx, basis="github_licence_interface_and_text_agree")]
    if analytics.status == 200:
        facts.append(fact_source(analytics.url, analytics.retrieved_at, analytics.sha256, len(analytics.body),
                                 "analytics", spdx=core_licence.spdx, basis="homebrew_public_analytics"))
    if repository_decision is not None and repository_decision.text:
        facts.append(fact_source(github_blob_address(row["repository"], repository_decision.commit,
                                                     repository_decision.path), answer.retrieved_at, repository_decision.sha256,
                                 len(repository_decision.text), "repository_facts",
                                 spdx=repository_decision.spdx or "NOASSERTION", basis=repository_decision.reason))
    effects = [("spawns_process", f"the wrapper starts {row['program']}")]
    rules = {"network": "the program uses the network", "writes_fs": "the program writes files",
             "reads_secret": "the program reads credentials"}
    basis = "declared in program_sources.json" if row.get("declared", True) else \
        "the formula does not say what the program does, so it is declared conservatively"
    effects += [(effect, f"{rules[effect]} ({basis})") for effect in row["effects"]]
    name = f"{snake(row['program']).replace('_', '-')}-program"
    stars = ((repository_facts.get((row["repository"] or "").lower()) or {}).get("stargazerCount")) or 0
    supply = SupplyPackage(
        line=PROGRAM_INSTALLS, identity=f"homebrew:{formula['name']}",
        key=upstream_key(PROGRAM_INSTALLS, f"homebrew:{formula['name']}"), kind="code_module",
        native_format=NATIVE_FORMAT, form="binary_install", name=name,
        description=(f"{row['program']} {plan['version']} ({formula.get('desc') or row['category']}): the install "
                     "recipe with published checksums for each platform and a typed wrapper that checks arguments "
                     "before running it."),
        files=files, licence_expression=f"{GENERATED_CODE_LICENCE} AND {core_licence.spdx}",
        provenance=provenance("homebrew_formulae", row["repository"] or HOMEBREW_CORE,
                              f"api/formula/{formula['name']}.json", f"version:{plan['version']}", facts, generator),
        placements=[{"harness": "reference", "path": f"tools/{name}/", "basis": "documented_layout",
                     "scope": "project", "support": "unverified"}],
        effects=effects, credentials=[],
        tests={"files": [f"test_{module}.py"], "command": f"python -m unittest test_{module}", "result": "passed",
               "tests_run": count, "network": False,
               "smoke": "ran" if shutil.which(row["program"]) else "skipped: not installed on the generating machine"},
        repository={"name": row["repository"] or HOMEBREW_CORE, "stars": stars, "formula": formula["name"],
                    "program_licence": program_licence, "installs_365_days": installs, "category": row["category"]},
        generated_on=generated_on, comparison_text=f"homebrew:{formula['name']}")
    return build(supply)
