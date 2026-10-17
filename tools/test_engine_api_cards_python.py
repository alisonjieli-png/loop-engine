"""The Python adapter of the engine API cards: the signature syntax, the wheel and repository proofs, the sandboxed
introspection and its check, and the line end to end on a fixture library served by a fake registry and repository.

Known-wrong controls: a package whose PyPI metadata names another licence than its repository's, a wheel whose files
are not the tag's blobs, and a library whose import opens a network connection are each refused by name; a wheel
member that differs from the wheel's RECORD, leaves its folder or is a link is refused; a text most of whose lines
the tag's files do not hold is refused; a card whose api.json changed a default or lost a member fails the native
check; a card's own test detects a changed Python default; a second card of one object and version is the same job.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "tools", ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from engine_api_cards import (cards, jsdoc_members, node_members, node_native, python_native,  # noqa: E402
                              python_reference, python_wheels)
from engine_api_cards.godot_native import NativeError, read_evidence  # noqa: E402
from loop_engine.core.library_ingestion.record_rules import git_blob_identity  # noqa: E402
from supply_lines import engine_api_cards as line  # noqa: E402
from supply_lines import engine_api_cards_jsdoc as jsdoc_line  # noqa: E402
from supply_lines import engine_api_cards_python as python_line  # noqa: E402
from supply_lines.function_extracts import foreign_licences  # noqa: E402
from supply_lines.reading import Digested, Fetched  # noqa: E402
from supply_lines.records import (ENGINE_API_CARDS, JAVASCRIPT_CARD_SCOPES, PYTHON_CARD_SCOPES,  # noqa: E402
                                  REFUSAL_REASONS, STATE_SCOPES)
from tools.component_qualification import checks, components  # noqa: E402
from tools.component_qualification.sandbox import SandboxSettings  # noqa: E402

INTERPRETER = "/usr/bin/python3.14"
REVISION = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
HAS_INTERPRETER = Path(INTERPRETER).is_file()
HAS_BWRAP = shutil.which("bwrap") is not None and SandboxSettings().works()
HAS_NODE = shutil.which("node") is not None
COMMIT = "c" * 40
REPOSITORY, TAG, DISTRIBUTION, VERSION = "baltor-fixtures/thing", "v1.2.3", "baltorfixture", "1.2.3"
WHEEL_NAME = f"{DISTRIBUTION}-{VERSION}-py3-none-any.whl"
WHEEL_URL = f"https://files.pythonhosted.org/packages/00/{WHEEL_NAME}"

INIT = '''"""A fixture library for the engine API card tests."""
from ._core import Thing, make
from .colours import Colour

__all__ = ["Colour", "Thing", "make"]
'''
NETWORK_INIT = INIT + '''
import socket

try:
    socket.create_connection(("192.0.2.1", 9), timeout=0.05)
except OSError:
    pass
'''
CORE = '''_MISSING = object()


class _Hidden:
    def shared(self, value: int = 1) -> int:
        """Return the value it was given, unchanged by the fixture."""
        return value


class Thing(_Hidden):
    """A thing the fixture library makes for its tests.

    It has a name and a size, and its label is its name in capitals.
    """

    size: int = 3

    def __init__(self, name: str, *, size: int = 3) -> None:
        self.name, self.size = name, size

    @property
    def label(self) -> str:
        """The thing's name written in capital letters."""
        return self.name.upper()

    @classmethod
    def build(cls, name: str) -> "Thing":
        """Build a thing of the default size from its name."""
        return cls(name)

    @staticmethod
    def describe(value, /, *rest, flag=_MISSING, **options):
        """Describe a value and the options given with it."""
        return repr(value)

    async def fetch(self) -> None:
        """Fetch nothing at all, without blocking the caller."""

    def quiet(self):
        return None


def make(name, size=2, *, marker=_MISSING):
    """Make a thing of the given name and size.

    The marker is ignored by the fixture and only shows a sentinel default.
    """
    return Thing(name, size=size)
'''
COLOURS = '''import enum


class Colour(enum.Enum):
    """The colours a thing of the fixture library can have."""

    RED = 1
    BLUE = 2
'''


def library_files(init: str = INIT) -> dict:
    return {f"{DISTRIBUTION}/__init__.py": init.encode(), f"{DISTRIBUTION}/_core.py": CORE.encode(),
            f"{DISTRIBUTION}/colours.py": COLOURS.encode()}


def _record_digest(data: bytes) -> str:
    return "sha256=" + base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip("=")


def wheel_bytes(files: dict, *, tamper: str = "", extra=()) -> bytes:
    """A wheel of the given files with a RECORD of their digests; ``tamper`` names a member whose bytes then differ
    from RECORD, ``extra`` adds raw (name, bytes, external attributes) members RECORD does not list."""
    dist = f"{DISTRIBUTION}-{VERSION}.dist-info"
    members = dict(files)
    members[f"{dist}/METADATA"] = f"Metadata-Version: 2.4\nName: {DISTRIBUTION}\nVersion: {VERSION}\n".encode()
    members[f"{dist}/WHEEL"] = b"Wheel-Version: 1.0\nGenerator: fixture\nRoot-Is-Purelib: true\nTag: py3-none-any\n"
    record = "".join(f"{name},{_record_digest(data)},{len(data)}\n" for name, data in members.items())
    record += f"{dist}/RECORD,,\n"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, data in members.items():
            archive.writestr(name, data + (b"# changed\n" if name == tamper else b""))
        archive.writestr(f"{dist}/RECORD", record)
        for name, data, attributes in extra:
            info = zipfile.ZipInfo(name)
            info.external_attr = attributes
            archive.writestr(info, data)
    return buffer.getvalue()


INTERPRETER_FACTS = {"path": INTERPRETER, "version": "", "python_tag": "cp314", "machine": "x86_64", "glibc": [2, 43]}


def interpreter_facts() -> dict:
    version = subprocess.run([INTERPRETER, "-I", "-S", "-c", "import sys; print(sys.version.split()[0])"],
                             capture_output=True, text=True).stdout.strip()
    return dict(INTERPRETER_FACTS, version=version)


class FakeReader:
    """A registry and a repository that answer like PyPI and GitHub for one fixture release."""

    def __init__(self, root: Path, *, init: str = INIT, repository_files=None, pypi_licence: str = "MIT",
                 github_licence: str = "MIT", licence_text: bytes = b"") -> None:
        self.root = Path(root)
        self.wheel = self.root / WHEEL_NAME
        self.wheel.write_bytes(wheel_bytes(library_files(init)))
        self.licence = licence_text or (ROOT / "LICENSE").read_bytes()
        files = repository_files if repository_files is not None else {
            f"src/{name}": data for name, data in library_files(init).items()}
        self.files = {"LICENSE": self.licence, **files}
        self.pypi_licence, self.github_licence = pypi_licence, github_licence

    @staticmethod
    def _answer(url, body, status=200):
        return Fetched(url, status, body, hashlib.sha256(body).hexdigest(), "2026-10-16T00:00:00Z", False)

    def get(self, url, **_options):
        if url == python_wheels.pypi_address(DISTRIBUTION, VERSION):
            document = {"info": {"name": DISTRIBUTION, "version": VERSION, "license_expression": self.pypi_licence,
                                 "classifiers": []},
                        "urls": [{"filename": WHEEL_NAME, "url": WHEEL_URL, "packagetype": "bdist_wheel",
                                  "digests": {"sha256": hashlib.sha256(self.wheel.read_bytes()).hexdigest()},
                                  "size": self.wheel.stat().st_size}]}
            return self._answer(url, json.dumps(document).encode())
        prefix = f"https://raw.githubusercontent.com/{REPOSITORY}/{COMMIT}/"
        if url.startswith(prefix) and url[len(prefix):] in self.files:
            return self._answer(url, self.files[url[len(prefix):]])
        return self._answer(url, b"", 404)

    def github(self, path):
        if path == f"repos/{REPOSITORY}/commits/{TAG}" or path == f"repos/{REPOSITORY}/commits/{COMMIT}":
            return self._answer(path, json.dumps({"sha": COMMIT}).encode())
        if path == f"repos/{REPOSITORY}/git/trees/{COMMIT}?recursive=1":
            tree = [{"path": name, "type": "blob", "sha": git_blob_identity(data)} for name, data in self.files.items()]
            return self._answer(path, json.dumps({"tree": tree, "truncated": False}).encode())
        if path.startswith(f"repos/{REPOSITORY}/license"):
            return self._answer(path, json.dumps({"path": "LICENSE", "sha": git_blob_identity(self.licence),
                                                  "license": {"spdx_id": self.github_licence}}).encode())
        return self._answer(path, b"{}", 404)

    def licence_text(self, repository, commit):
        return "LICENSE", self.licence, self.github_licence

    def digest(self, url, *, published=None, maximum_bytes=0, inspect=None, use_cache=True):
        data = self.wheel.read_bytes()
        inspected = inspect(self.wheel) if inspect is not None else None
        return Digested(url, url, 200, hashlib.sha256(data).hexdigest(), hashlib.md5(data).hexdigest(), len(data),
                        "2026-10-16T00:00:00Z", False, inspected)


def fixture_record(interpreter: dict) -> dict:
    row = {"identity": "baltorfixture-1.2", "distribution": DISTRIBUTION, "version": VERSION, "title": "Fixture",
           "repository": REPOSITORY, "tag": TAG, "state_scope": PYTHON_CARD_SCOPES[0],
           "modules": [DISTRIBUTION], "recurse": False, "exclude": [], "dependencies": []}
    return {"record_type": python_line.SOURCES_RECORD, "interpreter": interpreter, "libraries": [row], "rejected": []}


class SyntaxTests(unittest.TestCase):
    def test_parameters_are_written_the_way_inspect_writes_them(self):
        module = cards.card_module()
        parameters = [{"name": "value", "kind": "positional_only"}, {"name": "rest", "kind": "var_positional"},
                      {"name": "flag", "kind": "keyword_only", "default": "<object object>"},
                      {"name": "options", "kind": "var_keyword"}]
        self.assertEqual(module.python_parameters(parameters), "value, /, *rest, flag=<object object>, **options")
        typed = [{"name": "a", "kind": "positional_or_keyword", "type": "int"},
                 {"name": "b", "kind": "keyword_only", "type": "str", "default": "'x'"}]
        self.assertEqual(module.python_parameters(typed), "a: int, *, b: str = 'x'")
        self.assertEqual(module.python_parameters(None), "...")
        item = {"name": "fetch", "params": [], "returns": {"type": "None"}, "qualifiers": ["async"]}
        self.assertEqual(module.python_signature(module.METHODS, item), "async fetch() -> None")
        self.assertEqual(module.python_signature(module.CONSTRUCTORS, {"name": "Thing", "params": None}),
                         "Thing(...)")
        self.assertEqual(module.python_signature(module.MEMBERS, {"name": "label", "type": "str",
                                                                  "qualifiers": ["readonly"]}), "readonly label: str")

    def test_the_card_checker_reports_a_changed_python_default(self):
        module = cards.card_module()
        api = {"record_type": module.SURFACE_RECORD, "syntax": module.PYTHON_SYNTAX, "class": "pkg.make",
               "engine": {"title": "Pkg", "api_version": "1.2"}, "inherits": [], "inherited_by": [],
               "sections": {"functions": [{"name": "make", "params": [
                   {"name": "size", "kind": "positional_or_keyword", "default": "2"}], "returns": None}]}}
        text = "# pkg.make (Pkg 1.2)\n\n## Functions\n\n### `make(size=2)`\n\ntext\n"
        self.assertEqual(module.disagreements(api, [text]), [])
        changed = json.loads(json.dumps(api))
        changed["sections"]["functions"][0]["params"][0]["default"] = "3"
        self.assertTrue(module.disagreements(changed, [text]))


class WheelTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_the_wheel_the_interpreter_installs_is_chosen(self):
        facts = dict(INTERPRETER_FACTS, version="3.14.4")
        rank = lambda name: python_wheels.wheel_rank(name, facts)  # noqa: E731
        self.assertIsNotNone(rank("x-1-cp314-cp314-manylinux_2_28_x86_64.whl"))
        self.assertIsNotNone(rank("x-1-cp39-abi3-manylinux2014_x86_64.whl"))
        self.assertIsNotNone(rank("x-1-py3-none-any.whl"))
        # Known wrong: another interpreter's ABI, a newer glibc than the machine's, another machine.
        self.assertIsNone(rank("x-1-cp313-cp313-manylinux_2_28_x86_64.whl"))
        self.assertIsNone(rank("x-1-cp314-cp314-manylinux_2_99_x86_64.whl"))
        self.assertIsNone(rank("x-1-cp314-cp314-manylinux_2_28_aarch64.whl"))
        names = ["x-1-py3-none-any.whl", "x-1-cp39-abi3-manylinux2014_x86_64.whl",
                 "x-1-cp314-cp314-manylinux_2_17_x86_64.manylinux2014_x86_64.whl",
                 "x-1-cp314-cp314-manylinux_2_28_x86_64.whl"]
        document = {"info": {"name": "x", "version": "1"}, "urls": [
            {"filename": name, "packagetype": "bdist_wheel", "digests": {"sha256": "0" * 64}} for name in names]}
        self.assertEqual(python_wheels.choose_wheel(document, facts)["filename"],
                         "x-1-cp314-cp314-manylinux_2_28_x86_64.whl")

    def test_a_wheel_unpacks_only_members_its_record_vouches_for(self):
        path = self.root / WHEEL_NAME
        path.write_bytes(wheel_bytes(library_files()))
        summary = python_wheels.unpack_wheel(path, self.root / "out")
        self.assertIn(f"{DISTRIBUTION}/_core.py", summary["members"])
        self.assertEqual((self.root / "out" / DISTRIBUTION / "_core.py").read_text(), CORE)
        # Known wrong: a member whose bytes differ from RECORD, one that climbs out, and a link.
        for tamper, extra in ((f"{DISTRIBUTION}/_core.py", ()), ("", (("../escape.py", b"x", 0),)),
                              ("", ((f"{DISTRIBUTION}/link.py", b"_core.py", (0o120777 << 16)),))):
            path.write_bytes(wheel_bytes(library_files(), tamper=tamper, extra=extra))
            with self.assertRaises(python_wheels.WheelError) as raised:
                python_wheels.unpack_wheel(path, self.root / "bad")
            self.assertEqual(raised.exception.reason, "engine_binary_unverified")

    def test_wheel_files_are_proven_by_blob_identity_at_the_tag(self):
        path = self.root / WHEEL_NAME
        path.write_bytes(wheel_bytes(library_files()))
        summary = python_wheels.unpack_wheel(path, self.root / "out")
        wheel = python_wheels.InstalledWheel(DISTRIBUTION, VERSION, WHEEL_NAME, WHEEL_URL, "0" * 64, 1, "", self.root
                                             / "out", summary["members"])
        blobs = {f"src/{name}": git_blob_identity(data) for name, data in library_files().items()}
        proofs = python_wheels.prove(blobs, wheel)
        self.assertEqual(proofs.proven[f"{DISTRIBUTION}/_core.py"], f"src/{DISTRIBUTION}/_core.py")
        self.assertEqual(proofs.prefixes, {DISTRIBUTION: "src/"})
        # Known wrong: the tag holds other bytes for one file, and none for another.
        blobs[f"src/{DISTRIBUTION}/_core.py"] = "f" * 40
        del blobs[f"src/{DISTRIBUTION}/colours.py"]
        proofs = python_wheels.prove(blobs, wheel)
        self.assertEqual((proofs.differs, proofs.absent), ([f"{DISTRIBUTION}/_core.py"], [f"{DISTRIBUTION}/colours.py"]))

    def test_a_text_is_traced_to_the_sources_and_an_untraced_one_is_not(self):
        corpus = python_wheels.Corpus()
        corpus.add(f"src/{DISTRIBUTION}/_core.py", CORE)
        share, counted, holder = corpus.trace("Make a thing of the given name and size.\n\nA second line no "
                                              "source file of the fixture holds.")
        self.assertEqual((share, counted, holder), (0.5, 2, f"src/{DISTRIBUTION}/_core.py"))
        share, _counted, _holder = corpus.trace("Make a thing of the given name and size.")
        self.assertEqual(share, 1.0)
        # Escapes are read as the running module holds them: a docstring's \\* is \* at run time.
        corpus.add("src/escaped.py", 'def f():\n    """:param \\\\*\\\\*kwargs: the options."""\n')
        self.assertEqual(corpus.trace(":param \\*\\*kwargs: the options.")[0], 1.0)
        # Known wrong: words no source file holds.
        self.assertEqual(corpus.trace("A sentence the release never wrote anywhere.")[0], 0.0)

    def test_a_source_file_under_another_licence_is_excluded(self):
        mit = (ROOT / "LICENSE").read_bytes()
        apache = b"Apache License\nVersion 2.0, January 2004\nhttp://www.apache.org/licenses/\n"
        files = ["LICENSE", "vendored/LICENSE"]
        self.assertIsNone(python_wheels.licence_problem("pkg/a.py", "x = 1\n", "MIT", files, "LICENSE", {},
                                                        foreign_licences))
        self.assertEqual(python_wheels.licence_problem("vendored/b.py", "x = 1\n", "MIT", files, "LICENSE",
                                                       {"vendored/LICENSE": apache}, foreign_licences),
                         "nested_licence_differs")
        self.assertIsNone(python_wheels.licence_problem("vendored/b.py", "x = 1\n", "MIT", files, "LICENSE",
                                                        {"vendored/LICENSE": mit}, foreign_licences))
        stated = '"""Copied from elsewhere. Licensed under the GNU General Public License, version 3."""\nx = 1\n'
        self.assertEqual(python_wheels.licence_problem("pkg/c.py", stated, "MIT", files, "LICENSE", {},
                                                       foreign_licences), "module_licence_differs")


@unittest.skipUnless(HAS_INTERPRETER, f"{INTERPRETER} is the pinned interpreter")
class IntrospectionTests(unittest.TestCase):
    """The sandbox-side script run directly (and in bubblewrap when it works) on the fixture package."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.env = self.root / "env"
        for name, data in library_files().items():
            (self.env / name).parent.mkdir(parents=True, exist_ok=True)
            (self.env / name).write_bytes(data)

    def tearDown(self):
        shutil.rmtree(self.root)

    def read(self, spec: dict, mode: str = "read") -> dict:
        out = self.root / "out"
        out.mkdir(exist_ok=True)
        (out / "spec.json").write_text(json.dumps(dict(spec, record_type=python_native.SPEC_RECORD,
                                                       roots=[str(self.env)], target=0)))
        subprocess.run([INTERPRETER, "-I", "-S", "-B", str(python_native.SCRIPT), mode, str(out / "spec.json"),
                        str(out / "result.json")], check=True, env={"PATH": "/usr/bin", "PYTHONHASHSEED": "0"},
                       timeout=120)
        return json.loads((out / "result.json").read_text())

    def test_the_surface_of_a_function_and_a_class(self):
        result = self.read({"modules": [DISTRIBUTION]})
        objects = {row["path"]: row for row in result["objects"]}
        self.assertEqual(sorted(objects), [f"{DISTRIBUTION}.Colour", f"{DISTRIBUTION}.Thing", f"{DISTRIBUTION}.make"])
        make = objects[f"{DISTRIBUTION}.make"]
        self.assertEqual(make["signature"]["params"][2], {"name": "marker", "kind": "keyword_only",
                                                          "default": "<object object>"})
        thing = objects[f"{DISTRIBUTION}.Thing"]
        members = {row["name"]: row for row in thing["members"]}
        self.assertEqual(members["build"]["qualifiers"], ["classmethod"])
        self.assertEqual(members["build"]["signature"]["params"], [{"name": "name", "kind": "positional_or_keyword",
                                                                    "type": "str"}])
        self.assertEqual(members["describe"]["qualifiers"], ["staticmethod"])
        self.assertEqual(members["fetch"]["qualifiers"], ["async"])
        self.assertEqual((members["label"]["kind"], members["label"]["qualifiers"]), ("property", ["readonly"]))
        self.assertEqual((members["size"]["kind"], members["size"]["type"]), ("field", "int"))
        self.assertEqual(members["shared"]["owner"], f"{DISTRIBUTION}._core._Hidden")
        self.assertEqual([row["key"] for row in thing["mro"]], [f"{DISTRIBUTION}._core._Hidden"])
        colours = {row["name"]: row for row in objects[f"{DISTRIBUTION}.Colour"]["members"]}
        self.assertEqual(colours["RED"], dict(colours["RED"], kind="constant", value="<Colour.RED: 1>"))
        self.assertEqual([event for event in result["events"] if event["kind"] != "local"], [])

    def test_the_check_reports_a_changed_default_and_a_lost_member(self):
        expected = {"signature": {"params": [{"name": "name", "kind": "positional_or_keyword"},
                                             {"name": "size", "kind": "positional_or_keyword", "default": "2"},
                                             {"name": "marker", "kind": "keyword_only",
                                              "default": "<object object>"}], "returns": None}, "qualifiers": []}
        cards_asked = [{"card": "make", "kind": "function", "module": DISTRIBUTION, "qualname": "make",
                        "functions": [expected]},
                       {"card": "wrong", "kind": "function", "module": DISTRIBUTION, "qualname": "make",
                        "functions": [json.loads(json.dumps(expected).replace('"2"', '"3"'))]},
                       {"card": "gone", "kind": "method", "module": DISTRIBUTION, "qualname": "Thing",
                        "member": "vanished", "expected": {"kind": "method"}}]
        answers = self.read({"cards": cards_asked}, mode="verify")["cards"]
        self.assertEqual((answers["make"]["differs"], answers["wrong"]["differs"], answers["gone"]["missing"]),
                         ([], ["make"], ["vanished"]))

    @unittest.skipUnless(HAS_BWRAP, "bubblewrap is needed for the sandboxed run (the network test runs only there)")
    def test_the_sandboxed_import_that_opens_a_connection_or_writes_a_file_is_recorded(self):
        written = f"/tmp/baltor-card-test-{hashlib.sha256(str(self.root).encode()).hexdigest()[:12]}"
        (self.env / DISTRIBUTION / "__init__.py").write_text(NETWORK_INIT + f'\nopen("{written}", "w").close()\n')
        engine = python_native.locate(INTERPRETER, interpreter_facts()["version"])
        result = python_native.run(engine, [self.env], {"modules": [DISTRIBUTION]}, self.root / "work",
                                   python_native.READ, timeout=300)
        kinds = {(event["kind"], event["module"]) for event in result["events"]}
        self.assertTrue({("network", DISTRIBUTION), ("write", DISTRIBUTION)} <= kinds, kinds)
        # The sandbox's /tmp is its own: nothing reached the host's.
        self.assertFalse(Path(written).exists())


@unittest.skipUnless(HAS_INTERPRETER and HAS_BWRAP, "the pinned interpreter and bubblewrap run the adapter")
class LineTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.record = fixture_record(interpreter_facts())

    def tearDown(self):
        shutil.rmtree(self.root)

    def read(self, **reader):
        fake = FakeReader(self.root, **reader)
        return python_line.read_python(fake, self.root / "workspace", "baltorfixture-1.2",
                                       cache_root=self.root / "wheels", record=self.record, timeout=300)

    def generate(self, sources, verifier=None):
        verifier = verifier or (lambda prepared: python_line.python_evidence(sources, prepared, self.root / "verify",
                                                                             timeout=300))
        return line.generate(sources, verifier=verifier, code_revision=REVISION,
                             licence_text=(ROOT / "LICENSE").read_bytes(), generated_on="2026-10-16",
                             staging=self.root / "staging", workers=2)

    def component(self, built):
        payload, bodies = built
        folder = self.root / "package" / payload["record_id"]
        for entry in payload["package"]["files"]:
            target = folder / entry["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(bodies[entry["digest"]])
        (folder / "candidate.json").write_text(json.dumps(payload), encoding="utf-8")
        return components.from_folder(folder)

    def test_known_wrong_a_licence_the_package_metadata_does_not_name_is_refused(self):
        with self.assertRaises(line.LineStopped) as raised:
            self.read(pypi_licence="Apache-2.0")
        self.assertEqual(raised.exception.reason, "licence_signals_disagree")

    def test_known_wrong_a_wheel_that_is_not_the_tag_is_refused(self):
        other = {f"src/{name}": data + b"\n# another commit\n" for name, data in library_files().items()}
        with self.assertRaises(line.LineStopped) as raised:
            self.read(repository_files=other)
        self.assertEqual(raised.exception.reason, "published_source_differs")

    def test_known_wrong_an_import_that_touches_the_network_is_refused(self):
        with self.assertRaises(line.LineStopped) as raised:
            self.read(init=NETWORK_INIT)
        self.assertEqual(raised.exception.reason, "import_touches_network")

    def test_every_card_is_packaged_checked_natively_and_passes_every_static_check(self):
        sources = self.read()
        built, refusals, facts, summary = self.generate(sources)
        names = sorted(payload["repository"]["class"] for payload, _bodies in built)
        self.assertEqual(names, [f"{DISTRIBUTION}.Colour", f"{DISTRIBUTION}.Thing", f"{DISTRIBUTION}.Thing.build",
                                 f"{DISTRIBUTION}.Thing.describe", f"{DISTRIBUTION}.Thing.fetch",
                                 f"{DISTRIBUTION}.Thing.label", f"{DISTRIBUTION}.Thing.shared",
                                 f"{DISTRIBUTION}.make"])
        self.assertEqual(refusals, [])
        self.assertTrue(set(row["reason"] for row in refusals) <= set(REFUSAL_REASONS[ENGINE_API_CARDS]))
        self.assertEqual(summary["packaged_by_kind"], {"class": 2, "method": 4, "property": 1, "function": 1})
        payload = next(payload for payload, _bodies in built if payload["repository"]["class"].endswith(".make"))
        self.assertEqual([fact["role"] for fact in payload["provenance"]["facts"]],
                         ["licence_text", "data_source", "package_metadata", "release"])
        self.assertIn(hashlib.sha256(CORE.encode()).hexdigest(), facts)
        population = [self.component(row) for row in built]
        context = checks.QualificationContext.load(ROOT)
        context.duplicates = checks.duplicate_findings(population, context.policy)
        for component in population:
            for check in checks.CHECKS:
                if check.check_id in ("sandbox", "mutation"):
                    continue
                result = check.run(component, context)
                self.assertEqual(result.status, checks.PASSED, (component.identity, check.check_id, result.findings))
        self.assertEqual(checks.job_key(population[0], context.policy).split("|")[:3],
                         [ENGINE_API_CARDS, DISTRIBUTION, "1.2"])
        # Known wrong: a second card of one object and version is the same job, whatever its bytes.
        twin = population[0].replaced(identity=population[0].identity[:-16] + "0" * 16,
                                      payloads={**population[0].payloads, "README.md": b"# other bytes\n"})
        duplicates = checks.duplicate_findings(population + [twin], context.policy)
        self.assertTrue(any(code == "same_job_as" for row in duplicates.values() for code, _detail in row))
        context = checks.QualificationContext.load(ROOT, sandbox_settings=SandboxSettings(), work_root=self.root / "q")
        by_id = {check.check_id: check for check in checks.CHECKS}
        self.assertEqual(by_id["sandbox"].run(population[0], context).status, checks.PASSED)
        self.assertEqual(by_id["mutation"].run(population[0], context).status, checks.PASSED)

    def test_known_wrong_a_card_the_running_module_contradicts_fails_its_native_check(self):
        sources = self.read()
        prepared, _refused = line.prepare(sources, (ROOT / "LICENSE").read_bytes())
        card_ = prepared[f"{DISTRIBUTION}.make"]
        wrong = json.loads(json.dumps(card_.api))
        wrong["sections"]["functions"][0]["params"][1]["default"] = "3"
        thing = json.loads(json.dumps(prepared[f"{DISTRIBUTION}.Thing"].api))
        thing["sections"]["methods"].append({"name": "vanished", "params": [], "returns": None})
        engine, roots = sources.native
        answers = python_native.verify(engine, roots, [wrong, thing], sources.locations, self.root / "check",
                                       timeout=300)
        for api in (wrong, thing):
            record = python_native.evidence(engine, api, answers[api["class"]], "d" * 64)
            with self.assertRaises(NativeError) as raised:
                read_evidence(json.dumps(record).encode(), api, "d" * 64)
            self.assertEqual(raised.exception.reason, "native_check_failed")


    def test_wheel_ast_reads_the_surface_without_importing_and_native_verify_checks_defaults(self):
        sources = python_line.read_python(FakeReader(self.root), self.root / "workspace", "baltorfixture-1.2",
                                          cache_root=self.root / "wheels", record=self.record, timeout=300,
                                          surface_engine=python_line.WHEEL_AST_ENGINE)
        self.assertEqual(sources.summary["surface_engine"], python_line.WHEEL_AST_ENGINE)
        built, refusals, _facts, summary = self.generate(sources)
        names = sorted(payload["repository"]["class"] for payload, _bodies in built)
        # Thing, its 5 documented members, and make pass both wheel_ast and python_native.verify; Colour (an
        # enum.Enum whose metaclass synthesizes a runtime constructor and enum instances) is refused by native_check_failed.
        self.assertEqual(names, [f"{DISTRIBUTION}.Thing", f"{DISTRIBUTION}.Thing.build",
                                 f"{DISTRIBUTION}.Thing.describe", f"{DISTRIBUTION}.Thing.fetch",
                                 f"{DISTRIBUTION}.Thing.label", f"{DISTRIBUTION}.Thing.shared",
                                 f"{DISTRIBUTION}.make"])
        self.assertEqual(sorted((row["reason"], row["subject"]) for row in refusals),
                         [("native_check_failed", f"{DISTRIBUTION}.Colour")])
        self.assertEqual(summary["packaged"], 7)


class SourcesTests(unittest.TestCase):
    def test_every_library_row_names_a_known_state_scope_and_pins_its_environment(self):
        record = python_line.read_sources()
        scopes = [row["state_scope"] for row in record["libraries"]]
        self.assertEqual(sorted(scopes), sorted(PYTHON_CARD_SCOPES))
        self.assertTrue(set(scopes) <= set(STATE_SCOPES))
        for row in record["libraries"]:
            self.assertTrue(row["modules"] and row["chosen"])
            for pin in row["dependencies"]:
                python_wheels.requirement(pin)
        self.assertTrue(all(row["reason"] for row in record["rejected"]))
        js_record = jsdoc_line.read_sources()
        js_scopes = [row["state_scope"] for row in js_record["packages"]]
        self.assertEqual(sorted(js_scopes), sorted(JAVASCRIPT_CARD_SCOPES))
        self.assertTrue(set(js_scopes) <= set(STATE_SCOPES))
        self.assertTrue(all(row["reason"] for row in js_record["rejected"]))

    def test_package_licences_read_an_expression_a_field_and_classifiers(self):
        self.assertEqual(python_line.package_licences({"license_expression": "BSD-3-Clause AND MIT"}),
                         {"BSD-3-Clause", "MIT"})
        self.assertEqual(python_line.package_licences({"license": "MIT"}), {"MIT"})
        self.assertEqual(python_line.package_licences({"classifiers": ["License :: OSI Approved :: BSD License"]}),
                         {"BSD-2-Clause", "BSD-3-Clause"})
        self.assertEqual(python_line.package_licences({}), set())

    def test_hidden_characters_and_comment_openers_are_written_visibly(self):
        text = python_reference.fenced("a​b <!-- c --> ```inner```\x1b")
        self.assertNotIn("​", text)
        self.assertNotIn("<!--", text)
        self.assertIn("\\u200b", text)
        self.assertIn("\\x1b", text)
        self.assertTrue(text.startswith("````text\n"))
        self.assertEqual(python_reference.sentence("# A heading\nwith more"), "\\# A heading with more")
        self.assertNotIn("<!--", python_reference.sentence("x <!-- y"))


JS_APP = """/**
 * Application prototype.
 *
 * @public
 */
var app = exports = module.exports = {};

/**
 * Use the given middleware function, with a zero-width\u200b space and <!-- comment -->.
 *
 * @param {String|Function} path The mount path or middleware.
 * @param {Function} [fn] The middleware function.
 * @return {app} for chaining
 * @public
 * @example
 * app.use('/users',<!-- hidden --> fn)
 */
app.use = function use(path, fn) {
  return this;
};

/**
 * Old delete alias.
 *
 * @deprecated Use app.delete instead.
 * @public
 */
app.del = function del(path) {
  return this;
};

/**
 * Mount path property.
 *
 * @return {String}
 * @public
 */
defineGetter(app, 'mountpath', function mountpath() {
  throw new Error('getter must not be invoked on the prototype');
});

/**
 * Internal helper.
 *
 * @private
 */
app.secret = function secret() {};

app._hidden = function _hidden() {};

function defineGetter(obj, name, getter) {
  Object.defineProperty(obj, name, { configurable: true, enumerable: true, get: getter });
}
"""
JS_ENTRY = """var app = require('./lib/application');

/**
 * Create an express application.
 *
 * @return {Function}
 * @api public
 */
function createApplication() {
  return function () {};
}

exports = module.exports = createApplication;
exports.application = app;
"""
JS_RULES = [{"files": r"lib/application\.js", "marker": "public", "owners": {"app": "application"}},
            {"files": r"index\.js", "marker": "public", "exports": {"createApplication": ""},
             "export_name": "miniexpress"}]


def _tgz_bytes(files: dict) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for name, data in sorted(files.items()):
            info = tarfile.TarInfo(f"package/{name}")
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


class FakeJsReader:
    def __init__(self, root: Path, *, git_head: str = COMMIT, package_licence: str = "MIT",
                 repository_files: "dict | None" = None) -> None:
        self.root = Path(root)
        self.licence = (ROOT / "LICENSE").read_bytes()
        pkg_files = {"index.js": JS_ENTRY.encode(), "lib/application.js": JS_APP.encode(), "LICENSE": self.licence,
                     "package.json": json.dumps({"name": "miniexpress", "version": "1.0.0",
                                                 "license": package_licence}).encode()}
        self.tgz = _tgz_bytes(pkg_files)
        self.integrity = "sha512-" + base64.b64encode(hashlib.sha512(self.tgz).digest()).decode()
        self.git_head = git_head
        self.files = dict(repository_files or {"index.js": JS_ENTRY.encode(), "lib/application.js": JS_APP.encode()},
                          LICENSE=self.licence)

    @staticmethod
    def _answer(url, body, status=200):
        return Fetched(url, status, body, hashlib.sha256(body).hexdigest(), "2026-10-16T00:00:00Z", False)

    def get(self, url, **_options):
        if url == "https://registry.npmjs.org/miniexpress/1.0.0":
            doc = {"name": "miniexpress", "version": "1.0.0", "gitHead": self.git_head,
                   "dist": {"tarball": "https://registry.npmjs.org/miniexpress/-/miniexpress-1.0.0.tgz",
                            "integrity": self.integrity}}
            return self._answer(url, json.dumps(doc).encode())
        prefix = f"https://raw.githubusercontent.com/{REPOSITORY}/{COMMIT}/"
        if url.startswith(prefix) and url[len(prefix):] in self.files:
            return self._answer(url, self.files[url[len(prefix):]])
        return self._answer(url, b"", 404)

    def github(self, path):
        if path in (f"repos/{REPOSITORY}/commits/{TAG}", f"repos/{REPOSITORY}/commits/{COMMIT}"):
            return self._answer(path, json.dumps({"sha": COMMIT}).encode())
        if path == f"repos/{REPOSITORY}/git/trees/{COMMIT}?recursive=1":
            tree = [{"path": name, "type": "blob", "sha": git_blob_identity(data)} for name, data in self.files.items()]
            return self._answer(path, json.dumps({"tree": tree, "truncated": False}).encode())
        if path.startswith(f"repos/{REPOSITORY}/license"):
            return self._answer(path, json.dumps({"path": "LICENSE", "sha": git_blob_identity(self.licence),
                                                  "license": {"spdx_id": "MIT"}}).encode())
        return self._answer(path, b"{}", 404)

    def licence_text(self, repository, commit):
        return "LICENSE", self.licence, "MIT"

    def digest(self, url, *, published=None, maximum_bytes=0, inspect=None, use_cache=True):
        archive = self.root / "miniexpress.tgz"
        archive.write_bytes(self.tgz)
        inspected = inspect(archive) if inspect is not None else None
        return Digested(url, url, 200, hashlib.sha256(self.tgz).hexdigest(), "", len(self.tgz),
                        "2026-10-16T00:00:00Z", False, inspected)


class JsDocMembersTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.record = {"record_type": jsdoc_line.SOURCES_RECORD, "packages": [{
            "identity": "miniexpress-1.0", "package": "miniexpress", "version": "1.0.0", "title": "MiniExpress",
            "repository": REPOSITORY, "tag": TAG, "module": "index.js", "prefix": "",
            "state_scope": JAVASCRIPT_CARD_SCOPES[0], "rules": JS_RULES, "dependencies": []}], "rejected": []}

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_jsdoc_members_extract_functions_objects_methods_and_getters_and_hide_private_ones(self):
        found, problems = jsdoc_members.units({"index.js": JS_ENTRY, "lib/application.js": JS_APP}, JS_RULES, prefix="")
        self.assertEqual(problems, [])
        self.assertEqual(sorted(found), ["app", "app.del", "app.mountpath", "app.use", "miniexpress"])
        self.assertEqual(found["miniexpress"].reference.kind, cards.ClassKind.FUNCTION)
        self.assertEqual(found["app"].reference.kind, cards.ClassKind.OBJECT)
        self.assertEqual(found["app.use"].reference.kind, cards.ClassKind.METHOD)
        self.assertEqual(found["app.mountpath"].reference.kind, cards.ClassKind.PROPERTY)
        # Parameter fallback from the declaration line when @param is absent (app.del(path)).
        self.assertEqual(found["app.del"].reference.sections["methods"][0]["params"], [{"name": "path"}])
        # Invisible characters and HTML comment openers are escaped in prose and examples.
        desc = found["app.use"].reference.documentation["items"]["methods"][0]["description"]
        self.assertNotIn("\u200b", desc)
        self.assertNotIn("<!--", desc)
        self.assertIn("\\x3c!--", desc)

    @unittest.skipUnless(HAS_NODE, "node is required for the JavaScript member verifier")
    def test_jsdoc_line_end_to_end_and_known_wrong_controls(self):
        sources = jsdoc_line.read_package(FakeJsReader(self.root), self.root / "ws", "miniexpress-1.0",
                                          record=self.record)
        built, refusals, _facts, summary = line.generate(
            sources, verifier=lambda prepared: jsdoc_line.package_evidence(sources, prepared, self.root / "verify"),
            code_revision=REVISION, licence_text=(ROOT / "LICENSE").read_bytes(), generated_on="2026-10-16",
            staging=self.root / "staging", workers=2)
        self.assertEqual(refusals, [])
        self.assertEqual(summary["packaged_by_kind"], {"function": 1, "object": 1, "method": 2, "property": 1})
        # Known wrong: a missing method on an object or a member card fails the Node native check.
        prepared, _ = line.prepare(sources, (ROOT / "LICENSE").read_bytes())
        wrong = json.loads(json.dumps(prepared["app"].api))
        wrong["sections"]["methods"].append({"name": "vanished", "params": [], "returns": None})
        engine, module_file = sources.native
        answers = node_members.verify(engine, module_file, [wrong], sources.locations, self.root / "bad")
        ev = node_members.evidence(engine, wrong, answers["app"], "f" * 64)
        with self.assertRaises(NativeError) as raised:
            read_evidence(json.dumps(ev).encode(), wrong, "f" * 64)
        self.assertEqual(raised.exception.reason, "native_check_failed")
        # Known wrong: gitHead mismatch, package.json licence mismatch, and differing source file at the tag.
        with self.assertRaises(line.LineStopped) as bad_head:
            jsdoc_line.read_package(FakeJsReader(self.root, git_head="0" * 40), self.root / "ws2",
                                    "miniexpress-1.0", record=self.record)
        self.assertEqual(bad_head.exception.reason, "engine_binary_unverified")
        with self.assertRaises(line.LineStopped) as bad_lic:
            jsdoc_line.read_package(FakeJsReader(self.root, package_licence="Apache-2.0"), self.root / "ws3",
                                    "miniexpress-1.0", record=self.record)
        self.assertEqual(bad_lic.exception.reason, "licence_signals_disagree")
        diff_sources = jsdoc_line.read_package(
            FakeJsReader(self.root, repository_files={"index.js": JS_ENTRY.encode(),
                                                      "lib/application.js": b"// changed\n"}),
            self.root / "ws4", "miniexpress-1.0", record=self.record)
        self.assertEqual([(r["reason"], r["subject"]) for r in diff_sources.refusals],
                         [("published_source_differs", "lib/application.js")])


if __name__ == "__main__":
    unittest.main()

