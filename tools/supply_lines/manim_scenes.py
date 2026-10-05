"""Line manim_scenes: one tested animation scene per example scene of Manim Community's documentation.

```text
ManimCommunity/manim at a pinned release tag (MIT)
├── the tag resolved to its commit (one REST read), the commit's tree (one REST read) and the repository
│   archive at that commit (one HTTPS read); the archive's own header names the same commit, and every
│   file used is proven by its git blob identity against the tree
├── licence: LICENSE, where GitHub's licence interface and the text agree, and LICENSE.community, whose
│   text must match the same licence; both carried verbatim, and a NOTICE file at the root when there is one
├── every `.. manim::` directive outside literal blocks, in the library's docstrings (module, class,
│   function and method docstrings of manim/**/*.py) and the documentation pages (docs/source/**/*.rst)
│   ├── the scene's code as the documentation's directive runs it: `from manim import *`, then the
│   │   directive's content verbatim (doctest prompts removed the way the directive removes them)
│   ├── refused by name: a block that does not parse or does not define its scene, a name neither the block
│   │   nor Manim binds, a scene that needs LaTeX while no LaTeX is installed, one that needs a file it does
│   │   not carry or a module Manim does not install, one that fails or runs past its time, the same code twice
│   ├── one location may show two different scenes of one name: each keeps its occurrence number
│   └── test: the scene rendered in a child process with the network closed, every frame computed at low
│       quality and nothing written; then a known-wrong control, the scene's construct raising, must fail it
└── package: scene_<name>.py, test_scene_<name>.py, scene.json (manim_scene/v1), requirements.txt,
    README.md, LICENSE, UPSTREAM-LICENSE, UPSTREAM-LICENSE-COMMUNITY, ATTRIBUTION.md
```

One package is one example scene, a distinct animation recipe, never one per quality setting or output
format: the directive's quality and output options are recorded and the README gives the documented render
command. The scene's lines are the documentation's own, copied whole; the generated lines are a three-line
header naming the source and the `from manim import *` line the directive runs every example with.
"""
from __future__ import annotations

import ast
import builtins
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import tarfile
import textwrap
import time
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from loop_engine.core.library_ingestion.licences import match_licence
from loop_engine.core.library_ingestion.record_rules import git_blob_identity

from .licences import repository_licence
from .packaging import LICENCE_NAME, UPSTREAM_LICENCE_NAME, PackageFile, SupplyPackage, build, notice_files
from .reading import NOTICE_NAMES, github_blob_address, https_address
from .records import (
    BLOCKED_BY_STATIC_CHECK, GENERATED_CODE_LICENCE, LICENCE_TEXT, MANIM_SCENES, PACKAGE_ABOVE_REVIEW_BOUND,
    SupplyRecordError, fact_source, provenance, refusal, upstream_key)

GENERATOR_VERSION = "1.0.0"
NATIVE_FORMAT = "manim_scene"
SCENE_RECORD_TYPE = "manim_scene/v1"
#: The pinned source: Manim Community's repository and the release tag the scenes are read at. A new release is a
#: new tag here; the job key leaves the tag out, so the same scene at two tags is one job.
REPOSITORY = "ManimCommunity/manim"
RELEASE_TAG = "v0.21.0"
ARCHIVE_HOST = "codeload.github.com"
HOSTS = (ARCHIVE_HOST,)
#: The second licence file of the repository: the Manim Community developers' copyright beside 3Blue1Brown's.
COMMUNITY_LICENCE_PATH = "LICENSE.community"
COMMUNITY_LICENCE_NAME = "UPSTREAM-LICENSE-COMMUNITY"
#: Where the directives are read: the library's docstrings and the documentation's pages.
LIBRARY_FOLDER = "manim/"
PAGES_FOLDER = "docs/source/"
#: The role a harness gives a scene (catalogue_attributes ASSET_ROLES): it opens the scene as an editable source
#: of an animation and renders its own version.
ASSET_ROLE = "editable_source"
#: The quality the generated test renders every frame at, and the most seconds one scene's test may run.
TEST_QUALITY = "low_quality"
TEST_SECONDS = 240
#: Headings that name a docstring's section rather than what an example shows.
GENERIC_HEADINGS = frozenset({"examples", "example", "tests", "notes", "parameters", "see also", "returns",
                              "usage", "attributes", "methods", "references", "warnings", "raises", "yields"})
#: The reasons this line leaves a scene out (records.REFUSAL_REASONS[MANIM_SCENES] holds the same names).
(SOURCE_UNREADABLE, LICENCE_NOT_ON_ALLOWLIST, LICENCE_SIGNALS_DISAGREE, LICENCE_UNKNOWN, SCENE_UNREADABLE,
 SCENE_NOT_DEFINED, NAME_UNRESOLVED, NEEDS_LATEX, NEEDS_A_FILE, NEEDS_A_MODULE, SCENE_FAILED, SCENE_TIMED_OUT,
 CONTROL_NOT_FAILED, DUPLICATE_SCENE) = REASONS = (
    "source_unreadable", "licence_not_on_allowlist", "licence_signals_disagree", "licence_unknown",
    "scene_unreadable", "scene_not_defined", "name_unresolved", "needs_latex", "needs_a_file", "needs_a_module",
    "scene_failed", "scene_timed_out", "known_wrong_control_passed", "duplicate_scene")

#: Where a directive is documented: a documentation page, or the docstring of a module, class or function.
PAGE, DOCSTRING = BLOCK_KINDS = ("page", "docstring")
#: The exception names a failed run prints for a file and for a module the scene needs but nobody installed.
FILE_ERRORS = ("FileNotFoundError", "IsADirectoryError")
MODULE_ERRORS = ("ModuleNotFoundError", "ImportError")

_DIRECTIVE = re.compile(r"^(?P<indent>[ \t]*)\.\.[ \t]+manim::[ \t]*(?P<scene>\S*)[ \t]*$")
#: Directives whose content is literal text, never parsed as reStructuredText: a `.. manim::` inside one is an
#: example of the syntax, not a scene.
_LITERAL_DIRECTIVE = re.compile(r"^[ \t]*\.\.[ \t]+(?:code|code-block|sourcecode|literalinclude|raw|math|doctest|"
                                r"testcode|testoutput|highlight|parsed-literal)::")
_ANY_DIRECTIVE = re.compile(r"^[ \t]*\.\.[ \t]+[\w:-]+::")
_OPTION = re.compile(r"^[ \t]*:(?P<name>[\w-]+):(?P<value>.*)$")
_UNDERLINE = re.compile(r"^([=\-~^\"'`#*+<>:._])\1{2,}[ \t]*$")
_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")


class SceneRefused(ValueError):
    def __init__(self, reason: str, detail: str = "") -> None:
        if reason not in REASONS:
            raise ValueError(f"unknown reason {reason}")
        super().__init__(f"{reason}: {detail}")
        self.reason, self.detail = reason, detail


# -- the directives of one text -------------------------------------------------------------------------------------
@dataclass
class Block:
    """One `.. manim::` directive: where it is documented, its options and its content as the directive sees it."""

    path: str  # the repository file
    documented_at: str  # the page's path, or the documented object's dotted name for a docstring
    kind: str  # PAGE or DOCSTRING
    scene: str
    options: dict
    content: list  # the directive's content lines, dedented
    first_line: int  # 1-based lines of the directive in the repository file
    last_line: int
    section: "str | None" = None
    summary: str = ""  # the documented object's first sentence (docstrings)
    ordinal: int = 1  # the how-manyeth directive of this scene name at this location


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" \t"))


def _heading(lines: list, index: int) -> "str | None":
    """The heading text when lines[index] is a section underline below a title line."""
    if index < 1 or not _UNDERLINE.match(lines[index]):
        return None
    title = lines[index - 1].strip()
    if not title or _UNDERLINE.match(lines[index - 1]) or len(lines[index].strip()) < len(title) \
            or _indent(lines[index - 1]) != _indent(lines[index]) or title.startswith(".. "):
        return None
    return title


def _option_value(name: str, raw: str):
    value = raw.strip()
    if name in ("ref_modules", "ref_classes", "ref_functions", "ref_methods"):
        return value.split()
    if name == "quality":
        return value
    return True if not value else value


def directive_blocks(text: str) -> list:
    """(line index, scene, options, content, last index, section) of every `.. manim::` directive of a text,
    skipping those inside a literal block (an expanded `::` paragraph or a code directive)."""
    lines = text.split("\n")
    found, literal_indent, section = [], None, None
    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if literal_indent is not None:
            if stripped and _indent(line) <= literal_indent:
                literal_indent = None
            else:
                index += 1
                continue
        heading = _heading(lines, index)
        if heading is not None:
            section = heading
        match = _DIRECTIVE.match(line)
        if match:
            indent = _indent(line)
            end = index + 1
            while end < len(lines) and (not lines[end].strip() or _indent(lines[end]) > indent):
                end += 1
            body = lines[index + 1:end]
            while body and not body[-1].strip():
                body.pop()
            options, position = {}, 0
            while position < len(body) and body[position].strip():
                option = _OPTION.match(body[position])
                if not option:
                    break
                options[option.group("name")] = _option_value(option.group("name"), option.group("value"))
                position += 1
            content = body[position:]
            while content and not content[0].strip():
                content.pop(0)
            content = textwrap.dedent("\n".join(content)).split("\n") if content else []
            found.append((index, match.group("scene"), options, content, index + len(body), section))
            index = end
            continue
        if _LITERAL_DIRECTIVE.match(line) or (stripped.endswith("::") and not _ANY_DIRECTIVE.match(line)):
            literal_indent = _indent(line)
        index += 1
    return found


def page_blocks(path: str, text: str) -> list:
    """The directives of one documentation page."""
    return [Block(path, path, PAGE, scene, options, content, index + 1, last + 1, section)
            for index, scene, options, content, last, section in directive_blocks(text)]


def _summary(docstring: str) -> str:
    """The first sentence of a docstring's first paragraph, with reStructuredText roles reduced to their text."""
    paragraph = textwrap.dedent("\n".join(docstring.strip().split("\n\n", 1)[0].split("\n"))).replace("\n", " ")
    paragraph = re.sub(r":[\w:]+:`~?\.?([^`<]*?)(?:\s*<[^>]*>)?`", r"\1", paragraph)
    paragraph = re.sub(r"``([^`]*)``", r"\1", paragraph).strip()
    sentence = re.split(r"(?<=[.!?])\s", paragraph, maxsplit=1)[0]
    return sentence[:240]


def _docstring_nodes(tree, module: str):
    """(dotted name, node) of the module and of every class, function and method with a docstring."""
    yield module, tree
    stack = [(module, node) for node in tree.body]
    while stack:
        prefix, node = stack.pop(0)
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            name = f"{prefix}.{node.name}"
            yield name, node
            if isinstance(node, ast.ClassDef):
                stack[0:0] = [(name, child) for child in node.body]


def module_name(path: str) -> str:
    parts = list(PurePosixPath(path).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def docstring_blocks(path: str, source: str) -> list:
    """The directives of every docstring of one library module, each located at its documented object."""
    tree = ast.parse(source)
    blocks = []
    for name, node in _docstring_nodes(tree, module_name(path)):
        docstring = ast.get_docstring(node, clean=False)
        if not docstring or "manim::" not in docstring:
            continue
        constant = node.body[0].value
        found = directive_blocks(docstring)
        source_lines = source.split("\n")
        for index, scene, options, content, last, section in found:
            # The directive's line in the file: the docstring starts at its node's line, and a docstring holding
            # escapes may shift by a line, so the directive line itself is searched from there.
            start = constant.lineno - 1 + index
            directive = docstring.split("\n")[index].strip()
            for offset in range(constant.lineno - 1, min(len(source_lines), constant.end_lineno)):
                if source_lines[offset].strip() == directive and offset >= start - 2:
                    start = offset
                    break
            heading = section if section and section.lower() not in GENERIC_HEADINGS else None
            blocks.append(Block(path, name, DOCSTRING, scene, options, content, start + 1,
                                start + 1 + (last - index), heading, _summary(docstring)))
    return blocks


def number_repeats(blocks: list) -> list:
    """Each block's ordinal among the blocks of the same scene name at the same location."""
    seen: dict = {}
    for block in blocks:
        key = (block.documented_at, block.scene)
        seen[key] = seen.get(key, 0) + 1
        block.ordinal = seen[key]
    return blocks


# -- the scene's code -----------------------------------------------------------------------------------------------
def user_code(content: list) -> list:
    """The lines the directive executes: doctest prompts removed exactly as manim_directive.py removes them."""
    lines = list(content)
    if lines and lines[0].startswith(">>> "):
        lines = [line[4:] for line in lines if line.startswith((">>> ", "... "))]
    return lines


def snake(name: str) -> str:
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", "_", name).lower()
    return re.sub(r"[^a-z0-9_]+", "_", text).strip("_")


def words(name: str) -> str:
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|(?<=[A-Za-z])(?=[0-9])", " ", name)
    return spaced[:1].upper() + spaced[1:].lower() if spaced else name


def module_for(scene: str) -> str:
    """The scene's module name: scene_<name in snake case>, so it never shadows a standard or Manim module."""
    base = snake(scene) or hashlib.sha256(scene.encode()).hexdigest()[:10]
    return f"scene_{base}"[:80]


def scene_source(block: Block, release: dict) -> str:
    """The scene file: a generated three-line header, the directive's own import and the example verbatim."""
    where = f"the docstring of {block.documented_at}" if block.kind == DOCSTRING else block.path
    header = (f"# {block.scene}: example scene of {where}, {release['repository']} {release['tag']}\n"
              f"# (commit {release['commit']}, {block.path} lines {block.first_line} to {block.last_line}).\n"
              "# The lines after the import are the documentation's own; MIT, see the UPSTREAM-LICENSE files.\n")
    code = "\n".join(user_code(block.content)).rstrip("\n")
    return header + "from manim import *\n\n" + code + "\n"


# -- Manim's namespace, read once from the interpreter that renders -------------------------------------------------
#: Run by the rendering interpreter: what `from manim import *` binds, each name's category, the classes that
#: typeset with LaTeX (SingleStringMathTex and every subclass) or Typst, and the versions and programs present.
PROBE = r'''
import importlib, inspect, json, shutil, sys
namespace = {}
exec("from manim import *", namespace)
import manim
from manim.mobject.text.tex_mobject import SingleStringMathTex
try:
    from manim.mobject.text.typst_mobject import Typst
except ImportError:
    Typst = None
try:
    from manim.mobject.opengl.opengl_mobject import OpenGLMobject
except ImportError:
    OpenGLMobject = manim.Mobject
categories, latex, typst = {}, [], []
for name, value in namespace.items():
    if name.startswith("_") or name == "__builtins__":
        continue
    if inspect.isclass(value):
        if issubclass(value, manim.Scene):
            category = "scene"
        elif issubclass(value, manim.Animation):
            category = "animation"
        elif issubclass(value, (manim.Mobject, OpenGLMobject)):
            category = "mobject"
        else:
            category = "class"
        if issubclass(value, SingleStringMathTex):
            latex.append(name)
        if Typst is not None and issubclass(value, Typst):
            typst.append(name)
    elif inspect.ismodule(value):
        category = "module"
    elif callable(value):
        category = "function"
    else:
        category = "constant"
    categories[name] = category
def version(name):
    try:
        return importlib.import_module("importlib.metadata").version(name)
    except Exception:
        return None
print(json.dumps({"manim": manim.__version__, "python": sys.version.split()[0],
                  "prefixes": sorted({sys.prefix, sys.base_prefix, sys.exec_prefix}),
                  "versions": {name: version(name) for name in ("manim", "av", "pycairo", "manimpango", "typst",
                                                                  "numpy", "scipy")},
                  "programs": {name: bool(shutil.which(name)) for name in ("latex", "dvisvgm", "ffmpeg")},
                  "categories": categories, "latex": sorted(latex), "typst": sorted(typst)}, sort_keys=True))
'''


@dataclass(frozen=True)
class Namespace:
    """What the rendering interpreter's Manim provides, read once by PROBE."""

    manim: str
    python: str
    prefixes: tuple
    versions: dict
    programs: dict
    categories: dict  # name -> scene, animation, mobject, class, module, function or constant
    latex: frozenset  # classes that typeset with LaTeX
    typst: frozenset  # classes that typeset with Typst

    @property
    def has_latex(self) -> bool:
        return bool(self.programs.get("latex")) and bool(self.programs.get("dvisvgm"))

    def summary(self) -> dict:
        return {"manim": self.manim, "python": self.python, "versions": self.versions, "programs": self.programs,
                "names": len(self.categories), "latex_classes": len(self.latex), "typst_classes": len(self.typst)}


def read_namespace(python: str, *, timeout: float = 180.0) -> Namespace:
    """The namespace of the Manim that `python` imports; raises RuntimeError when it cannot import Manim."""
    done = subprocess.run([python, "-E", "-s", "-B", "-c", PROBE], capture_output=True, timeout=timeout,
                          stdin=subprocess.DEVNULL, env=_child_environment(None))
    if done.returncode != 0:
        raise RuntimeError(f"the interpreter {python} cannot import Manim: "
                           f"{done.stderr.decode('utf-8', 'replace')[-400:]}")
    value = json.loads(done.stdout.decode("utf-8").strip().splitlines()[-1])
    return Namespace(value["manim"], value["python"], tuple(value["prefixes"]), value["versions"],
                     value["programs"], value["categories"], frozenset(value["latex"]), frozenset(value["typst"]))


# -- what one scene reads -------------------------------------------------------------------------------------------
_BUILTINS = frozenset(dir(builtins)) | {"__name__", "__file__", "__doc__", "__builtins__"}


def names_read_and_bound(tree) -> tuple:
    """(names loaded anywhere, names bound anywhere) of a module: a scope-blind view, enough to find a name that
    nothing binds."""
    loaded, bound = set(), set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            (loaded if isinstance(node.ctx, ast.Load) else bound).add(node.id)
        elif isinstance(node, ast.arg):
            bound.add(node.arg)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bound.add(node.name)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            bound.update((alias.asname or alias.name).split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            bound.add(node.name)
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            bound.update(node.names)
        elif isinstance(node, ast.MatchAs) and node.name:
            bound.add(node.name)
    return loaded, bound


@dataclass
class SceneFacts:
    """What a scene's code is, read without running it."""

    tree: object
    uses: dict  # category -> sorted Manim names the code reads
    latex: list  # LaTeX classes the code names
    typst: list  # Typst classes the code names
    plays: int  # calls of .play(
    waits: int  # calls of .wait(
    base: "str | None"  # the scene's first base class


def read_scene(block: Block, namespace: Namespace) -> SceneFacts:
    """Parse a block's code and check it statically; raise SceneRefused by name."""
    code = "\n".join(user_code(block.content))
    if not _IDENTIFIER.match(block.scene or ""):
        raise SceneRefused(SCENE_UNREADABLE, f"the directive names no scene class ({block.scene!r})")
    try:
        tree = ast.parse(code)
    except SyntaxError as error:
        raise SceneRefused(SCENE_UNREADABLE, f"line {error.lineno}: {error.msg}") from None
    classes = [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == block.scene]
    if not classes:
        raise SceneRefused(SCENE_NOT_DEFINED, f"no top-level class {block.scene}")
    loaded, bound = names_read_and_bound(tree)
    unresolved = sorted(loaded - bound - _BUILTINS - set(namespace.categories))
    if unresolved:
        raise SceneRefused(NAME_UNRESOLVED, ", ".join(unresolved)[:200])
    used = sorted(name for name in loaded - bound if name in namespace.categories)
    uses: dict = {}
    for name in used:
        uses.setdefault(namespace.categories[name], []).append(name)
    calls = [node.func.attr for node in ast.walk(tree) if isinstance(node, ast.Call)
             and isinstance(node.func, ast.Attribute)]
    base = classes[0].bases[0] if classes[0].bases else None
    return SceneFacts(tree, uses, sorted(set(used) & namespace.latex), sorted(set(used) & namespace.typst),
                      calls.count("play"), calls.count("wait"),
                      ast.unparse(base) if base is not None else None)


def code_identity(tree) -> str:
    """The same program whatever its comments and layout: the digest of its syntax tree."""
    return hashlib.sha256(ast.dump(tree, annotate_fields=False).encode("utf-8")).hexdigest()


# -- the generated test and its run ----------------------------------------------------------------------------------
def test_text(module: str, scene: str) -> str:
    """The package's test: the scene rendered once, every frame at low quality, nothing written."""
    return (f'"""Renders the scene {scene} of {module}.py once, offline:\n'
            'every frame computed at low quality, nothing written.\n\n'
            "The test passes only when the scene's construct method runs to its end under Manim Community; a scene\n"
            "whose construct raises fails it. It needs Manim: pip install -r requirements.txt\n"
            '"""\n'
            "import importlib\nimport os\nimport sys\nimport tempfile\nimport unittest\n\n"
            "sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))\n\n"
            f"SCENE_MODULE = {json.dumps(module)}\nSCENE = {json.dumps(scene)}\n"
            f"SETTINGS = {{\"dry_run\": True, \"quality\": {json.dumps(TEST_QUALITY)}, \"disable_caching\": True, "
            "\"progress_bar\": \"none\",\n            \"verbosity\": \"WARNING\"}\n\n\n"
            "class SceneRendersTest(unittest.TestCase):\n"
            "    def test_the_scene_renders_every_frame(self):\n"
            "        import manim\n"
            "        scene_class = getattr(importlib.import_module(SCENE_MODULE), SCENE)\n"
            "        self.assertTrue(issubclass(scene_class, manim.Scene))\n"
            "        with tempfile.TemporaryDirectory() as media:\n"
            "            with manim.tempconfig({**SETTINGS, \"media_dir\": media}):\n"
            "                scene = scene_class()\n"
            "                scene.render()\n"
            "        self.assertTrue(scene.renderer.num_plays > 0 or len(scene.mobjects) > 0,\n"
            "                        \"the scene neither played an animation nor showed a mobject\")\n\n\n"
            'if __name__ == "__main__":\n    unittest.main()\n')


def mutant_text(text: str, scene: str) -> str:
    """The scene with its construct method replaced by one that raises: its test must fail."""
    return text + (f"\n\ndef _known_wrong_construct(self):\n    raise NotImplementedError('known-wrong control')\n\n\n"
                   f"{scene}.construct = _known_wrong_construct\n")


#: Host paths the test run never shows (the component qualification sandbox hides the same ones); the
#: rendering interpreter's own folders and the package folder are mounted back read-only and writable.
HIDDEN_PATHS = ("/home", "/root", "/run", "/mnt", "/media", "/srv")
SYSTEM_PATH = "/usr/bin:/bin"
#: The runner the child interpreter starts with: the network is closed in Python before the test is loaded, and
#: the run passes only when at least one test ran and every test passed.
RUNNER = r'''
import socket, sys, unittest
def closed(*arguments, **options):
    raise OSError("the network is closed while generated tests run")
socket.socket.connect = socket.socket.connect_ex = closed
socket.create_connection = socket.getaddrinfo = closed
sys.path.insert(0, ".")
program = unittest.main(module=sys.argv[1], argv=["unittest", "-v"], exit=False)
result = program.result
sys.exit(0 if result.wasSuccessful() and result.testsRun > 0 and not result.skipped else 1)
'''


@dataclass(frozen=True)
class TestRun:
    passed: bool
    seconds: float
    timed_out: bool
    output: str  # the tail of what the run printed


#: The whole environment of a test run: the system path, a UTF-8 locale and no compiled files written.
CHILD_ENVIRONMENT = {"PATH": SYSTEM_PATH, "LANG": "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1"}


def _child_environment(folder: "Path | None", cache: "Path | None" = None) -> dict:
    environment = dict(CHILD_ENVIRONMENT)
    if folder is not None:
        environment.update({"HOME": str(folder), "TMPDIR": str(folder / ".tmp")})
    if cache is not None:
        environment["XDG_CACHE_HOME"] = str(cache)
    return environment


@dataclass(frozen=True)
class Runtime:
    """The interpreter that renders, the sandbox it runs in, and the per-scene time limit."""

    python: str
    namespace: Namespace
    cache: Path  # a writable folder kept across runs (the font cache)
    bwrap: "str | None" = None
    seconds: float = TEST_SECONDS

    def argv(self, folder: Path, test_module: str) -> list:
        command = [self.python, "-E", "-s", "-B", "-c", RUNNER, test_module]
        if not self.bwrap:
            return command
        argv = [self.bwrap, "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc"]
        for path in HIDDEN_PATHS:
            if os.path.isdir(path) and not os.path.islink(path):
                argv += ["--tmpfs", path]
        for prefix in sorted({*self.namespace.prefixes, str(Path(self.python).resolve().parent.parent)}):
            if any(prefix == hidden or prefix.startswith(hidden + "/") for hidden in HIDDEN_PATHS):
                argv += ["--ro-bind", prefix, prefix]
        argv += ["--bind", str(folder), str(folder), "--bind", str(self.cache), str(self.cache),
                 "--unshare-net", "--unshare-ipc", "--unshare-pid", "--unshare-uts", "--die-with-parent",
                 "--new-session", "--chdir", str(folder), "--clearenv"]
        for name, value in _child_environment(folder, self.cache).items():
            argv += ["--setenv", name, value]
        return argv + ["--"] + command


def run_test(runtime: Runtime, folder: Path, test_module: str) -> TestRun:
    """Run one package's test in a child process with the network closed; never raises for the test's sake."""
    (folder / ".tmp").mkdir(exist_ok=True)
    started = time.monotonic()
    try:
        done = subprocess.run(runtime.argv(folder, test_module), cwd=folder, capture_output=True,
                              timeout=runtime.seconds, stdin=subprocess.DEVNULL,
                              env=_child_environment(folder, runtime.cache))
    except subprocess.TimeoutExpired as expired:
        output = (expired.stderr or b"").decode("utf-8", "replace")
        return TestRun(False, round(time.monotonic() - started, 2), True, output[-1500:])
    finally:
        shutil.rmtree(folder / ".tmp", ignore_errors=True)
    output = (done.stdout + b"\n" + done.stderr).decode("utf-8", "replace")
    return TestRun(done.returncode == 0, round(time.monotonic() - started, 2), False, output[-3000:])


_LAST_ERROR = re.compile(r"^(?P<type>[A-Za-z_][\w.]*(?:Error|Exception|Exit|Interrupt)):\s?(?P<message>.*)$",
                         re.MULTILINE)


def failure_reason(run: TestRun) -> tuple:
    """(reason, detail) of a failed test run, by what the run printed."""
    if run.timed_out:
        return SCENE_TIMED_OUT, f"stopped after {run.seconds} seconds"
    errors = _LAST_ERROR.findall(run.output)
    last = f"{errors[-1][0]}: {errors[-1][1]}"[:200] if errors else run.output.strip()[-200:]
    if "tex_file_writing" in run.output or "No such file or directory: 'latex'" in run.output:
        return NEEDS_LATEX, f"observed: {last}"
    if errors and errors[-1][0] in MODULE_ERRORS:
        return NEEDS_A_MODULE, last
    if any(kind in FILE_ERRORS for kind, _message in errors) or \
            "No such file or directory" in last or "could not find" in last:
        return NEEDS_A_FILE, last
    if errors and errors[-1][0] == "NameError":
        return NAME_UNRESOLVED, f"observed: {last}"
    return SCENE_FAILED, last


# -- the release ----------------------------------------------------------------------------------------------------
@dataclass
class Release:
    """The pinned release: its commit, the archive it was read from, and the files used, proven by blob identity."""

    repository: str
    tag: str
    commit: str
    archive: dict  # url, sha256, size_bytes, retrieved_at
    files: dict = field(default_factory=dict)  # path -> bytes
    unreadable: list = field(default_factory=list)  # paths whose bytes differ from the tree's blob

    def as_header(self) -> dict:
        return {"repository": self.repository, "tag": self.tag, "commit": self.commit}

    def blob_address(self, path: str) -> str:
        return github_blob_address(self.repository, self.commit, path)


def wanted(path: str) -> bool:
    """The files the line reads from the archive: library modules, documentation pages, licence and notice files."""
    return ((path.startswith(LIBRARY_FOLDER) and path.endswith(".py"))
            or (path.startswith(PAGES_FOLDER) and path.endswith(".rst"))
            or path in ("LICENSE", COMMUNITY_LICENCE_PATH, *NOTICE_NAMES))


def read_release(reader, repository: str = REPOSITORY, tag: str = RELEASE_TAG) -> Release:
    """The release at its tag: three reads (the tag's commit, the commit's tree, the archive at the commit);
    raises LookupError when any of them fails or the archive is not the commit's."""
    head = reader.github(f"repos/{repository}/commits/{tag}")
    if head.status != 200:
        raise LookupError(f"{repository}: the tag {tag} names no readable commit")
    commit = json.loads(head.body)["sha"]
    tree = reader.github(f"repos/{repository}/git/trees/{commit}?recursive=1")
    if tree.status != 200:
        raise LookupError(f"{repository}: no tree at {commit[:12]}")
    listing = json.loads(tree.body)
    if listing.get("truncated"):
        raise LookupError(f"{repository}: the tree at {commit[:12]} is truncated")
    blobs = {entry["path"]: entry["sha"] for entry in listing.get("tree", []) if entry.get("type") == "blob"}
    address = https_address(ARCHIVE_HOST, f"{repository}/tar.gz/{commit}")
    archive = reader.get(address)
    if archive.status != 200:
        raise LookupError(f"{repository}: the archive at {commit[:12]} did not answer ({archive.status})")
    release = Release(repository, tag, commit, {"url": address, "sha256": archive.sha256,
                                                "size_bytes": len(archive.body), "retrieved_at": archive.retrieved_at})
    with tarfile.open(fileobj=io.BytesIO(archive.body), mode="r:gz") as bundle:
        if bundle.pax_headers.get("comment") != commit:
            raise LookupError(f"{repository}: the archive names commit {bundle.pax_headers.get('comment')!r}")
        for member in bundle.getmembers():
            parts = member.name.split("/", 1)
            if not member.isfile() or len(parts) != 2 or not wanted(parts[1]):
                continue
            data = bundle.extractfile(member).read()
            if blobs.get(parts[1]) != git_blob_identity(data):
                release.unreadable.append(parts[1])
                continue
            release.files[parts[1]] = data
    return release


def page_title(text: str) -> "str | None":
    lines = text.split("\n")
    for index in range(1, len(lines)):
        heading = _heading(lines, index)
        if heading:
            return heading
    return None


def release_blocks(release: Release) -> tuple:
    """(blocks, refusals, page titles) of every directive of the release, the Cairo renderer's modules first so a
    scene the OpenGL classes repeat keeps its location at the class most readers find it under."""
    blocks, refused, titles = [], [], {}
    order = sorted(release.files, key=lambda path: ("/opengl/" in path, path))
    for path in order:
        if not path.endswith((".py", ".rst")):
            continue
        text = release.files[path].decode("utf-8", "replace")
        if "manim::" not in text:
            continue
        try:
            found = docstring_blocks(path, text) if path.endswith(".py") else page_blocks(path, text)
        except SyntaxError as error:
            refused.append(refusal(MANIM_SCENES, SOURCE_UNREADABLE, path, str(error)[:120]))
            continue
        if path.endswith(".rst"):
            titles[path] = page_title(text)
        blocks += found
    return number_repeats(blocks), refused, titles


# -- one package ----------------------------------------------------------------------------------------------------
OUTPUTS = {"last_frame": ("-s", "its last frame as an image"), "gif": ("--format gif", "a GIF"),
           "video": ("", "a video")}
QUALITY_FLAGS = {"low": "-ql", "medium": "-qm", "high": "-qh", "fourk": "-qk"}


def output_of(options: dict) -> str:
    if options.get("save_last_frame"):
        return "last_frame"
    return "gif" if options.get("save_as_gif") else "video"


def render_commands(module: str, scene: str, options: dict) -> dict:
    """The render commands a README gives: the documented output at low quality, and the test's dry run."""
    flag = OUTPUTS[output_of(options)][0]
    quality = QUALITY_FLAGS.get(str(options.get("quality")), "-ql")
    documented = " ".join(part for part in ("manim render", flag, quality, f"{module}.py", scene) if part)
    return {"documented": documented, "dry_run": f"manim render --dry_run -ql {module}.py {scene}"}


def requirement(facts: SceneFacts, namespace: Namespace) -> str:
    return f"manim[typst]=={namespace.manim}" if facts.typst else f"manim=={namespace.manim}"


def _quoted(names) -> str:
    return ", ".join(f"`{name}`" for name in names)


USE_LABELS = (("mobject", "Mobjects"), ("animation", "Animations"), ("scene", "Scene classes"),
              ("class", "Other classes"), ("function", "Functions"), ("constant", "Constants"),
              ("module", "Modules"))


def references(options: dict) -> list:
    return [name for key in ("ref_modules", "ref_classes", "ref_functions", "ref_methods")
            for name in options.get(key, [])]


def what_it_shows(block: Block, facts: SceneFacts) -> str:
    built = facts.uses.get("mobject", [])
    animations = facts.uses.get("animation", [])
    if block.options.get("save_last_frame"):
        shown = "a still image (the documentation renders its last frame)"
    else:
        counts = [f"{count} `{name}` call{'s' if count != 1 else ''}"
                  for name, count in (("play", facts.plays), ("wait", facts.waits)) if count]
        shown = "an animation" + (f" of {' and '.join(counts)}" if counts else "")
    parts = [shown]
    if built:
        parts.append(f"built from {_quoted(built[:12])}{' and more' if len(built) > 12 else ''}")
    if animations:
        parts.append(f"animated with {_quoted(animations[:12])}{' and more' if len(animations) > 12 else ''}")
    return ", ".join(parts)


def location_text(block: Block, titles: dict) -> str:
    if block.kind == DOCSTRING:
        text = f"the reference documentation of `{block.documented_at}` (`{block.path}`)"
        if block.section:
            text += f", section \"{block.section}\""
        return text
    title = titles.get(block.path)
    named = f'"{title}" ' if title else ""
    text = f"the page {named}(`{block.path}`)"
    if block.section and block.section != title:
        text += f", section \"{block.section}\""
    return text


def readme_text(block: Block, facts: SceneFacts, module: str, release: Release, namespace: Namespace,
                titles: dict, licence_spdx: str) -> str:
    commands = render_commands(module, block.scene, block.options)
    occurrence = f" (the {_ordinal(block.ordinal)} scene of that name there)" if block.ordinal > 1 else ""
    lines = [f"# {words(block.scene)}", "",
             f"`{block.scene}`, an example scene of Manim Community's documentation: "
             f"{location_text(block, titles)}{occurrence}, Manim Community {release.tag}."]
    if block.kind == DOCSTRING and block.summary:
        lines += ["", f"Manim's documentation of `{block.documented_at.rsplit('.', 1)[-1]}`: {block.summary}"]
    lines += ["", f"It shows {what_it_shows(block, facts)}.", "", "## Manim API it uses", ""]
    for category, label in USE_LABELS:
        if facts.uses.get(category):
            lines.append(f"- {label}: {_quoted(facts.uses[category])}")
    named = references(block.options)
    if named:
        lines.append(f"- The documentation points to: {_quoted(named)}")
    lines += ["", "## Render it", "", "```bash", "pip install -r requirements.txt", commands["documented"], "```", "",
              f"This writes {OUTPUTS[output_of(block.options)][1]} under `media/` at 480p"
              f"{' (the documentation uses quality ' + block.options['quality'] + ')' if block.options.get('quality') else ''};"
              " use `-qh` for 1080p at 60 frames a second.",
              f"Requirements: `{requirement(facts, namespace)}` (Manim needs Cairo and Pango;"
              + (" Typst typesets this scene's text, no LaTeX)." if facts.typst else " no LaTeX).")]
    lines += ["", "## Test", "", "```bash", f"python -m unittest test_{module}", "```", "",
              f"The test renders every frame of `{block.scene}` at low quality without writing a file (as "
              f"`{commands['dry_run']}` does) and passes only when its `construct` method runs to the end. It passed "
              f"with Manim Community {namespace.manim} on Python {namespace.python}, offline; the same scene with its "
              "`construct` method raising fails it.", "",
              "## Source and licence", "",
              f"From {release.repository} {release.tag} (commit `{release.commit}`), `{block.path}` lines "
              f"{block.first_line} to {block.last_line}, licensed {licence_spdx}: `UPSTREAM-LICENSE` (Copyright "
              "3Blue1Brown LLC) and `UPSTREAM-LICENSE-COMMUNITY` (Copyright the Manim Community Developers). The "
              f"lines of `{module}.py` after its import are the documentation's own, as its `manim` directive runs "
              "them; the three header lines and `from manim import *` are generated. `scene.json` records the same "
              "facts for a program. Baltor's files are MIT (`LICENSE`); `ATTRIBUTION.md` lists every source and "
              "file digest.", ""]
    return "\n".join(lines)


def _ordinal(number: int) -> str:
    return {1: "first", 2: "second", 3: "third", 4: "fourth"}.get(number, f"{number}th")


def scene_record(block: Block, facts: SceneFacts, module: str, release: Release, namespace: Namespace,
                 titles: dict) -> dict:
    """scene.json (manim_scene/v1): the scene, where it is documented and what it uses, for a program."""
    return {"record_type": SCENE_RECORD_TYPE, "scene": block.scene, "occurrence": block.ordinal,
            "documented_at": block.documented_at,
            "documentation": {"kind": block.kind, "path": block.path, "first_line": block.first_line,
                              "last_line": block.last_line, "section": block.section,
                              "page_title": titles.get(block.path) if block.kind == PAGE else None,
                              "summary": block.summary or None},
            "module": module, "release": {**release.as_header(), "manim": namespace.manim},
            "directive": {"output": output_of(block.options), "quality": block.options.get("quality"),
                          "hide_source": bool(block.options.get("hide_source")), "references": references(block.options)},
            "render": render_commands(module, block.scene, block.options),
            "uses": facts.uses, "plays": facts.plays, "waits": facts.waits, "base": facts.base,
            "requires": [requirement(facts, namespace)], "typesetting": "typst" if facts.typst else None,
            "asset_role": ASSET_ROLE,
            "test": {"module": f"test_{module}", "quality": TEST_QUALITY, "renders": "every frame, nothing written",
                     "known_wrong_control": "the scene's construct raising fails the test"}}


def text_effects(text: str) -> list:
    """The effects the library ingestion rules read in the scene's code."""
    from loop_engine.core.library_ingestion.effects import declared_effects
    found = declared_effects("code_module", text, {})
    return [(row["effect"], row["rule"]) for row in found.evidence]


#: Rendering a scene writes its video or image under media/ (Manim's own output folder).
RENDER_EFFECT = ("writes_fs", "manim_render_writes_media_files")


@dataclass
class Verified:
    """One scene that passed its static checks, with its code and the two test runs."""

    block: Block
    facts: SceneFacts
    module: str
    text: str
    run: "TestRun | None" = None
    control: "TestRun | None" = None


def verify(verified: Verified, runtime: Runtime, staging: Path) -> Verified:
    """Run the scene's test, then the known-wrong control; the folder is removed afterwards."""
    folder = staging / f"{verified.module}-{verified.block.ordinal}-{code_identity(verified.facts.tree)[:8]}"
    folder.mkdir(parents=True, exist_ok=True)
    try:
        (folder / f"{verified.module}.py").write_text(verified.text, encoding="utf-8")
        (folder / f"test_{verified.module}.py").write_text(test_text(verified.module, verified.block.scene),
                                                          encoding="utf-8")
        verified.run = run_test(runtime, folder, f"test_{verified.module}")
        if verified.run.passed:
            (folder / f"{verified.module}.py").write_text(mutant_text(verified.text, verified.block.scene),
                                                          encoding="utf-8")
            verified.control = run_test(runtime, folder, f"test_{verified.module}")
    finally:
        shutil.rmtree(folder, ignore_errors=True)
    return verified


def package_names(kept: list) -> dict:
    """Each kept scene's package name: manim-<scene>, and where two kept scenes would share it, the fewest last
    parts of each one's location that tell them apart (and the occurrence number of a repeated scene)."""

    def name_for(item, parts: int) -> str:
        name = "manim-" + snake(item.block.scene).replace("_", "-")
        if parts:
            tail = re.split(r"[./]", item.block.documented_at.removesuffix(".rst"))[-parts:]
            name += "-" + "-".join(snake(part).replace("_", "-") for part in tail)
        if parts and item.block.ordinal > 1:
            name += f"-{item.block.ordinal}"
        return name[:90]

    names = {}
    groups: dict = {}
    for item in kept:
        groups.setdefault(name_for(item, 0), []).append(item)
    for base, items in groups.items():
        parts = 0
        while len({name_for(item, parts) for item in items}) < len(items) and parts < 8:
            parts += 1
        for item in items:
            names[id(item)] = name_for(item, parts) if len(items) > 1 else base
    return names


def generate(reader, *, runtime: Runtime, code_revision: str, licence_text: bytes, generated_on: str,
             staging: Path, repository_facts: "dict | None" = None, only=None, maximum: int = 0,
             workers: int = 3, repository: str = REPOSITORY, tag: str = RELEASE_TAG) -> tuple:
    """(built, refusals, facts, summary): every example scene of the release that renders, tested."""
    from concurrent.futures import ThreadPoolExecutor
    built, refused, kept_facts = [], [], {}
    generator = {"identity": "tools/supply_lines/manim_scenes.py", "version": GENERATOR_VERSION,
                 "code_revision": code_revision}
    summary = {"repository": repository, "tag": tag, "renderer": runtime.namespace.summary(),
               "sandbox": "bwrap" if runtime.bwrap else "python_socket_closure", "scenes": []}
    try:
        release = read_release(reader, repository, tag)
    except (LookupError, ValueError, tarfile.TarError) as error:
        refused.append(refusal(MANIM_SCENES, SOURCE_UNREADABLE, f"{repository} {tag}", str(error)))
        return built, refused, kept_facts, summary
    summary.update({"commit": release.commit, "archive": release.archive})
    for path in release.unreadable:
        refused.append(refusal(MANIM_SCENES, SOURCE_UNREADABLE, path, "the archive's bytes differ from the blob"))
    licence = repository_licence(reader, repository, release.commit)
    if not licence.allowed:
        refused.append(refusal(MANIM_SCENES, licence.refusal_reason(
            (LICENCE_NOT_ON_ALLOWLIST, LICENCE_SIGNALS_DISAGREE, LICENCE_UNKNOWN)), repository,
            str(licence.github_spdx)))
        return built, refused, kept_facts, summary
    community = release.files.get(COMMUNITY_LICENCE_PATH)
    if community is None or match_licence(community.decode("utf-8", "replace")).spdx != licence.spdx:
        refused.append(refusal(MANIM_SCENES, LICENCE_SIGNALS_DISAGREE, f"{repository} {COMMUNITY_LICENCE_PATH}",
                               f"the text does not match {licence.spdx}"))
        return built, refused, kept_facts, summary
    notice = next(({"repository": repository, "commit": release.commit, "path": name,
                    "bytes": release.files[name], "sha256": hashlib.sha256(release.files[name]).hexdigest(),
                    "retrieved_at": release.archive["retrieved_at"], "spdx": licence.spdx,
                    "url": release.blob_address(name)} for name in NOTICE_NAMES if name in release.files), None)
    summary["licence"] = {**licence.evidence(), "community_licence": COMMUNITY_LICENCE_PATH,
                          "notice": notice["path"] if notice else None}
    blocks, unreadable, titles = release_blocks(release)
    refused += unreadable
    summary["directives"] = len(blocks)
    if only:
        blocks = [block for block in blocks if block.scene in set(only)]
    if maximum:
        blocks = blocks[:maximum]
    pending, identities = [], {}
    for block in blocks:
        label = f"{block.documented_at} {block.scene}" + (f" #{block.ordinal}" if block.ordinal > 1 else "")
        try:
            facts = read_scene(block, runtime.namespace)
        except SceneRefused as error:
            refused.append(refusal(MANIM_SCENES, error.reason, label, error.detail))
            continue
        if facts.latex and not runtime.namespace.has_latex:
            refused.append(refusal(MANIM_SCENES, NEEDS_LATEX, label, f"static: names {', '.join(facts.latex)}"))
            continue
        identity = code_identity(facts.tree)
        if identity in identities:
            refused.append(refusal(MANIM_SCENES, DUPLICATE_SCENE, label, f"the same code as {identities[identity]}"))
            continue
        identities[identity] = label
        module = module_for(block.scene)
        pending.append(Verified(block, facts, module, scene_source(block, release.as_header())))
    staging.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        verified = list(pool.map(lambda item: verify(item, runtime, staging), pending))
    kept = []
    for item in verified:
        block = item.block
        label = f"{block.documented_at} {block.scene}" + (f" #{block.ordinal}" if block.ordinal > 1 else "")
        row = {"scene": block.scene, "documented_at": block.documented_at, "occurrence": block.ordinal,
               "seconds": item.run.seconds, "control_seconds": item.control.seconds if item.control else None}
        if not item.run.passed:
            reason, detail = failure_reason(item.run)
            refused.append(refusal(MANIM_SCENES, reason, label, detail))
            summary["scenes"].append({**row, "result": reason})
            continue
        if item.control is None or item.control.passed:
            refused.append(refusal(MANIM_SCENES, CONTROL_NOT_FAILED, label,
                                   "the scene with its construct raising still passes the test"))
            summary["scenes"].append({**row, "result": CONTROL_NOT_FAILED})
            continue
        summary["scenes"].append({**row, "result": "passed"})
        kept.append(item)
    names = package_names(kept)
    for item in kept:
        block = item.block
        label = f"{block.documented_at} {block.scene}" + (f" #{block.ordinal}" if block.ordinal > 1 else "")
        try:
            payload = build_package(item, names[id(item)], release, licence, notice, titles, generator,
                                    licence_text, generated_on, runtime.namespace, repository_facts or {})
        except SupplyRecordError as error:
            reason = error.code if error.code in (BLOCKED_BY_STATIC_CHECK, PACKAGE_ABOVE_REVIEW_BOUND) else \
                SCENE_UNREADABLE
            refused.append(refusal(MANIM_SCENES, reason, label, str(error)))
            continue
        source = release.files[block.path]
        kept_facts[hashlib.sha256(source).hexdigest()] = source
        built.append(payload)
    summary["kept"] = len(built)
    return built, refused, kept_facts, summary


def build_package(item: Verified, name: str, release: Release, licence, notice, titles: dict, generator: dict,
                  licence_text: bytes, generated_on: str, namespace: Namespace, repository_facts: dict) -> tuple:
    """(payload, bodies) of one verified scene's package; raises SupplyRecordError by name."""
    block, facts, module = item.block, item.facts, item.module
    record = scene_record(block, facts, module, release, namespace, titles)
    readme = readme_text(block, facts, module, release, namespace, titles, licence.spdx)
    community = release.files[COMMUNITY_LICENCE_PATH]
    files = [PackageFile(f"{module}.py", item.text.encode("utf-8"), "executable_tool"),
             PackageFile(f"test_{module}.py", test_text(module, block.scene).encode("utf-8"), "executable_tool"),
             PackageFile("scene.json", (json.dumps(record, indent=1, sort_keys=True) + "\n").encode("utf-8"), "other"),
             PackageFile("requirements.txt", (requirement(facts, namespace) + "\n").encode("utf-8"), "other"),
             PackageFile("README.md", readme.encode("utf-8"), "other"),
             PackageFile(LICENCE_NAME, licence_text, "other", LICENCE_TEXT),
             PackageFile(UPSTREAM_LICENCE_NAME, licence.text, "other", LICENCE_TEXT,
                         {"url": release.blob_address(licence.path), "sha256": licence.sha256}),
             PackageFile(COMMUNITY_LICENCE_NAME, community, "other", LICENCE_TEXT,
                         {"url": release.blob_address(COMMUNITY_LICENCE_PATH),
                          "sha256": hashlib.sha256(community).hexdigest()})]
    source = release.files[block.path]
    archive = release.archive
    retrieved = archive["retrieved_at"]
    facts_rows = [fact_source(archive["url"], retrieved, archive["sha256"], archive["size_bytes"], "data_source",
                              spdx=licence.spdx, basis="github_licence_interface_and_text_agree",
                              evidence_sha256=licence.sha256),
                  fact_source(release.blob_address(block.path), retrieved, hashlib.sha256(source).hexdigest(),
                              len(source), "data_source", spdx=licence.spdx,
                              basis="github_licence_interface_and_text_agree", evidence_sha256=licence.sha256),
                  fact_source(release.blob_address(licence.path), retrieved, licence.sha256, len(licence.text),
                              "licence_text", spdx=licence.spdx, basis="licence_file_at_the_pinned_commit"),
                  fact_source(release.blob_address(COMMUNITY_LICENCE_PATH), retrieved,
                              hashlib.sha256(community).hexdigest(), len(community), "licence_text",
                              spdx=licence.spdx, basis="licence_text_matches_the_repository_licence")]
    notices, notice_facts = notice_files([notice])
    files += notices
    facts_rows += notice_facts
    identity = f"{release.repository}:{block.documented_at}:{block.scene}" + (
        f":{block.ordinal}" if block.ordinal > 1 else "")
    stars = ((repository_facts.get(release.repository.lower()) or {}).get("stargazerCount")) or 0
    description = (f"{words(block.scene)}: a Manim Community {release.tag} example scene from "
                   f"{'the documentation of ' + block.documented_at if block.kind == DOCSTRING else block.path}, "
                   f"tested by rendering every frame. It shows {what_it_shows(block, facts)}.")
    supply = SupplyPackage(
        line=MANIM_SCENES, identity=identity, key=upstream_key(MANIM_SCENES, identity), kind="code_module",
        native_format=NATIVE_FORMAT, form="code_example", name=name, description=description,
        files=files, licence_expression=" AND ".join(dict.fromkeys([GENERATED_CODE_LICENCE, licence.spdx])),
        provenance=provenance("github_repository", release.repository, block.path, release.commit, facts_rows,
                              generator),
        placements=[{"harness": "reference", "path": f"scenes/{name}/", "basis": "documented_layout",
                     "scope": "project", "support": "unverified"}],
        effects=sorted(set(text_effects(item.text)) | {RENDER_EFFECT}), credentials=[],
        tests={"files": [f"test_{module}.py"], "command": f"python -m unittest test_{module}", "result": "passed",
               "tests_run": 1, "network": False,
               "renderer": {"manim": namespace.manim, "python": namespace.python},
               "known_wrong_control": "the scene's construct raising fails the test"},
        repository={"name": release.repository, "stars": stars, "tag": release.tag, "path": block.path,
                    "documented_at": block.documented_at, "scene": block.scene, "occurrence": block.ordinal,
                    "lines": [block.first_line, block.last_line]},
        generated_on=generated_on, comparison_text=identity)
    return build(supply)


__all__ = ["Block", "Namespace", "Release", "Runtime", "SceneRefused", "Verified", "build_package",
           "directive_blocks", "docstring_blocks", "failure_reason", "generate", "module_for", "mutant_text", "page_blocks", "read_namespace",
           "read_release", "read_scene", "release_blocks", "run_test", "scene_source", "test_text", "user_code"]
