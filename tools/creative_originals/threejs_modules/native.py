"""Native verifier of the threejs_modules family: run each module's own tests in Node, prove the tests catch a broken
module, and render the item's demo scene with three.js on a real WebGL 2 context in headless Chrome.

For one item:

1. copy the item's declared files and the family's shared files into the workspace, as the package holds them;
2. ``module_contract_static``: read the root ES module's exports without running it and compare them with the
   contract (names and kinds); the module and its demo import nothing;
3. ``node_tests_pass``: run every root ``test_*.mjs`` with ``node --test --test-reporter=tap``, the command the
   qualification sandbox uses, and require at least one passing test and no failed or cancelled one;
4. ``node_tests_catch_mutants``: replace the exports of each root module with ones that throw (qualification's own
   mutant builder and replacement text), one module at a time, and require the same tests to fail;
5. ``three_runtime_pinned``: the three.js files the page loads have the SHA-256 digests of the official 0.186.1 npm
   tarball;
6. open ``harness/page.html`` in headless Google Chrome with WebGL 2 on SwiftShader (through ANGLE), import the
   pinned three.js build, the module and the item's ``demo/scene.mjs``, let the demo build its scene and make its
   own checks, render it at 256 x 256 to the canvas and read the pixels back:

   * ``browser_page_clean``: the page returned a result with no exception, console error or WebGL warning, and
     ``gl.getError()`` was ``NO_ERROR`` after the last frame;
   * ``three_shaders_compiled``: three.js reported no shader compile or link error and built at least one program;
   * ``demo_checks_passed``: the demo made at least one check, and every check passed;
   * ``render_not_uniform``: some colour channel has a standard deviation of at least ``MINIMUM_DEVIATION`` and the
     most common colour covers at most ``MAXIMUM_MODE_SHARE`` of the frame;
   * ``render_differs_from_baseline``: when the demo declares a baseline scene (the same scene without the item's
     effect), at least ``MINIMUM_CHANGED_PIXELS`` pixels differ by ``CHANGE_THRESHOLD`` or more.

Chrome is driven through the DevTools protocol over a pipe (``--remote-debugging-pipe``: no port is opened), every
host name resolves to nothing, and the run sits in a memory-capped ``systemd-run --user`` scope when one is
available. The preview is the demo frame. A check that cannot run is a failed check, never a pass. Nothing here shows
behaviour on a hardware GPU, in another browser, with another three.js release or under WebGPU.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import threading
import time
from collections import namedtuple
from pathlib import Path

from tools.component_qualification.checks import POLICY_PATH, javascript_mutant
from tools.component_qualification.sandbox import default_node, parse_tap
from tools.creative_originals import pngio

FAMILY_DIRECTORY = Path(__file__).resolve().parent
HARNESS_DIRECTORY = FAMILY_DIRECTORY / "harness"
PAGE_TEMPLATE = HARNESS_DIRECTORY / "page.html"
HARNESS_SCRIPT = HARNESS_DIRECTORY / "run.mjs"
PASSED, FAILED = "passed", "failed"
RESOLUTION = 256
ENGINE_NAME = "webgl2_browser"

#: Where the browser is looked for: the BALTOR_CHROME variable, then Google Chrome stable, then Chrome for Testing.
CHROME_VARIABLE = "BALTOR_CHROME"
CHROME_CANDIDATES = ("/opt/google/chrome/chrome", "~/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome")
#: Where three.js is looked for: the BALTOR_THREE variable (an unpacked npm package folder), then the pinned copy.
THREE_VARIABLE = "BALTOR_THREE"
THREE_CANDIDATES = ("~/.cache/baltor-creative/runtimes/three-0.186.1/package",)
THREE_VERSION = "0.186.1"
THREE_REVISION = "186"
#: The files the page may load, with their SHA-256 digests in the official npm tarball three-0.186.1.tgz (SHA-512
#: integrity blFeqb49wRCSGUGj7gtpfnSGHy2lwDk94RhUmS1c/hTby70kvChbWpkJ4Pm1390LqzzvTmzgXKHPEafJwCb8jA==, SHA-256
#: 8cd068708ea44f2c73c944b1cead2ba2f0d5c15c8fc194e5700f4e4f4a033fe7), checked October 9, 2026.
THREE_FILES = {
    "build/three.module.js": "9052042d676cb0fdc1ddfefe193053f34b7ac0513a616fdac4535d49987812ea",
    "build/three.core.js": "9edde002b066a9a05676a6127f67735b62baf399bdea529f2f7e31657da769e6",
    "examples/jsm/loaders/GLTFLoader.js": "131c0f78c01d19368ae495caa65b3adaa10487810a36a05bb5901b769a35ac16",
    "examples/jsm/exporters/GLTFExporter.js": "d766b04f233fa8bc72bfaebacaac5ecb832c30ca3695ce8d84bbb7dccccdc842",
    "examples/jsm/utils/BufferGeometryUtils.js": "9fb63427ce6641fa14fd0baff9cc4d1b5f9c3d85fd084bf2e90e803c44ec1797",
    "examples/jsm/utils/SkeletonUtils.js": "b1632a703206c3d830de9fcbe515696770d04b71a15ee6b50afa6d2c3298c86f",
}
THREE_ENTRY = "build/three.module.js"
THREE_ADDON_FOLDER = "examples/jsm"
#: The addons a demo may ask for (contract.demo.addons); the harness maps each to its file.
ADDONS = ("GLTFLoader", "GLTFExporter")

CHROME_FLAGS = ("--headless", "--remote-debugging-pipe", "--no-first-run", "--no-default-browser-check",
                "--disable-extensions", "--disable-background-networking", "--disable-component-update",
                "--disable-sync", "--disable-default-apps", "--mute-audio", "--allow-file-access-from-files",
                "--enable-unsafe-swiftshader", "--use-angle=swiftshader", "--host-resolver-rules=MAP * ~NOTFOUND",
                f"--window-size={RESOLUTION},{RESOLUTION}")
#: The browser reads protocol messages on descriptor 3 and writes on 4; the shell maps them to our pipes.
PIPE_SHELL = 'exec "$@" 3<&0 4>&1 0</dev/null 1>/dev/null'
SEPARATOR = b"\0"
BROWSER_MEMORY = "2G"
NODE_TIMEOUT_SECONDS = 120
PAGE_TIMEOUT_SECONDS = 120
STARTUP_TIMEOUT_SECONDS = 60
CLOSE_TIMEOUT_SECONDS = 15
#: DevTools protocol methods and events used here.
CREATE_TARGET, ATTACH, ENABLE_RUNTIME, ENABLE_PAGE, ENABLE_LOG = (
    "Target.createTarget", "Target.attachToTarget", "Runtime.enable", "Page.enable", "Log.enable")
NAVIGATE, EVALUATE, CLOSE_BROWSER = "Page.navigate", "Runtime.evaluate", "Browser.close"
LOAD_EVENT, CONSOLE_EVENT, EXCEPTION_EVENT, LOG_EVENT = (
    "Page.loadEventFired", "Runtime.consoleAPICalled", "Runtime.exceptionThrown", "Log.entryAdded")
#: Console and log levels that fail the page check.
FAILING_LEVELS = frozenset({"error", "assert"})
WARNING_LEVELS = frozenset({"warning"})
#: A warning fails the page check when it comes from three.js or WebGL; other warnings are only recorded.
FAILING_WARNING = re.compile(r"THREE\.|WebGL|GL_INVALID|GL_OUT_OF_MEMORY|shader", re.IGNORECASE)
#: Messages that match FAILING_WARNING but do not concern the item, each with its reason. ANGLE reports every
#: synchronous readPixels as a performance stall; the verifier reads pixels back on purpose.
HARMLESS_MESSAGES = (
    re.compile(r"GL Driver Message \(OpenGL, Performance, [A-Z_]+, \w+\): GPU stall due to ReadPixels"),
)
AWAIT_RESULT = ("(async () => { for (let i = 0; i < 400 && !window.__baltorVerification; i += 1) {"
                " await new Promise((resolve) => setTimeout(resolve, 25)); }"
                " return window.__baltorVerification ? await window.__baltorVerification"
                " : {fatal: 'the page made no verification promise'}; })()")

MINIMUM_DEVIATION = 2.0
MAXIMUM_MODE_SHARE = 0.99
CHANGE_THRESHOLD = 10
MINIMUM_CHANGED_PIXELS = 256

#: The user session variables systemd-run --user needs to reach the user manager for the memory scope.
USER_BUS_VARIABLES = (RUNTIME_DIRECTORY_VARIABLE, BUS_ADDRESS_VARIABLE) = ("XDG_RUNTIME_DIR", "DBUS_SESSION_BUS_ADDRESS")
ENV_PROGRAM = "/usr/bin/env"
TEMPORARY_FOLDER_VARIABLE = "TMPDIR"
SHELL_PROGRAM = "/bin/sh"
SEARCH_PATH = "/usr/bin:/bin"
LOCALE = "C.UTF-8"
DIGEST_CACHE = Path("~/.cache/baltor-creative/threejs-engine-digests.json").expanduser()

#: Export declarations, read the way the qualification mutant builder reads them.
EXPORT_FUNCTION = re.compile(r"^export\s+(?:async\s+)?function\s*\*?\s*([A-Za-z_$][\w$]*)\s*\(", re.MULTILINE)
EXPORT_CLASS = re.compile(r"^export\s+class\s+([A-Za-z_$][\w$]*)", re.MULTILINE)
EXPORT_CONSTANT = re.compile(r"^export\s+const\s+([A-Za-z_$][\w$]*)\s*=", re.MULTILINE)
EXPORT_OTHER = re.compile(r"^export\s+(?:default\b|let\b|var\b|\{|\*)", re.MULTILINE)
IMPORT_STATEMENT = re.compile(r"^\s*import\b|\bimport\s*\(|\brequire\s*\(", re.MULTILINE)
KIND_FUNCTION, KIND_CLASS, KIND_CONSTANT = "function", "class", "constant"
TEST_PREFIX, MODULE_SUFFIX = "test_", ".mjs"
#: Keys of protocol messages and of the runtime table.
MESSAGE_ID, MESSAGE_ERROR, EXCEPTION_DETAILS = "id", "error", "exceptionDetails"
CHROME_KEY, NODE_KEY, SCOPE_KEY = "chrome", "node", "scope"

_LOCK = threading.Lock()
_FOUND = {}


class BrowserError(RuntimeError):
    """The browser could not be started, answered with an error or did not answer in time."""


#: A located runtime: its name, binary path, version line and binary SHA-256. (A named tuple, not a dataclass: the
#: verifier is loaded from its file without a module entry, which dataclasses need.)
Runtime = namedtuple("Runtime", "name path version sha256")


def _check(name: str, passed: bool, detail) -> dict:
    return {"name": name, "state": PASSED if passed else FAILED, "detail": detail}


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _cached_digest(path: Path) -> str:
    """SHA-256 of a large binary, cached by path, size and modification time (callers hold _LOCK)."""
    stat = path.stat()
    key = f"{path}|{stat.st_size}|{stat.st_mtime_ns}"
    cache = {}
    if DIGEST_CACHE.is_file():
        try:
            cache = json.loads(DIGEST_CACHE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            cache = {}
    if key not in cache:
        cache[key] = _file_digest(path)
        DIGEST_CACHE.parent.mkdir(parents=True, exist_ok=True)
        temporary = DIGEST_CACHE.with_name(f"{DIGEST_CACHE.name}.{os.getpid()}.{threading.get_ident()}.tmp")
        temporary.write_text(json.dumps(cache, indent=1, sort_keys=True), encoding="utf-8")
        temporary.replace(DIGEST_CACHE)
    return cache[key]


def _isolated_environment(home: Path) -> dict:
    for folder in (home, home / ".config", home / ".cache", home / ".local/share", home / ".runtime", home / ".tmp"):
        folder.mkdir(parents=True, exist_ok=True)
    os.chmod(home / ".runtime", 0o700)
    return {"HOME": str(home), "XDG_CONFIG_HOME": str(home / ".config"), "XDG_CACHE_HOME": str(home / ".cache"),
            "XDG_DATA_HOME": str(home / ".local/share"), "XDG_RUNTIME_DIR": str(home / ".runtime"),
            TEMPORARY_FOLDER_VARIABLE: str(home / ".tmp"), "PATH": SEARCH_PATH, "LANG": LOCALE}


def _version(path: str, home: Path) -> str:
    completed = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=60,
                               env=_isolated_environment(home))
    lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    return lines[-1] if lines else "unknown"


def locate_chrome(home: Path) -> Runtime:
    with _LOCK:
        if CHROME_KEY not in _FOUND:
            candidates = [path for path in [os.environ.get(CHROME_VARIABLE)] if path] + [
                str(Path(path).expanduser()) for path in CHROME_CANDIDATES]
            for candidate in candidates:
                path = Path(candidate) if candidate else None
                if path is not None and path.is_file() and os.access(path, os.X_OK):
                    _FOUND[CHROME_KEY] = Runtime(CHROME_KEY, str(path), _version(str(path), home),
                                                 _cached_digest(path))
                    break
            else:
                raise BrowserError(f"no browser found; set {CHROME_VARIABLE} (searched {[c for c in candidates if c]})")
        return _FOUND[CHROME_KEY]


def locate_node(home: Path) -> Runtime:
    with _LOCK:
        if NODE_KEY not in _FOUND:
            path = Path(default_node())
            if not (path.is_file() and os.access(path, os.X_OK)):
                raise FileNotFoundError(f"node is not installed at {path}")
            _FOUND[NODE_KEY] = Runtime(NODE_KEY, str(path), _version(str(path), home), _cached_digest(path))
        return _FOUND[NODE_KEY]


def locate_three() -> tuple:
    """(folder, problems): the pinned three.js package folder and every file whose digest differs from the pin."""
    candidates = [path for path in [os.environ.get(THREE_VARIABLE)] if path] + [
        str(Path(path).expanduser()) for path in THREE_CANDIDATES]
    for candidate in candidates:
        folder = Path(candidate) if candidate else None
        if folder is None or not (folder / THREE_ENTRY).is_file():
            continue
        with _LOCK:
            key = f"three|{folder}"
            if key not in _FOUND:
                problems = []
                for relative, expected in sorted(THREE_FILES.items()):
                    path = folder / relative
                    actual = _file_digest(path) if path.is_file() else None
                    if actual != expected:
                        problems.append({"file": relative, "sha256": actual})
                _FOUND[key] = problems
        return folder, list(_FOUND[key])
    return None, [{"error": f"three.js {THREE_VERSION} not found; set {THREE_VARIABLE}"}]


def _scope(command: list, environment: dict, home: Path, memory: str) -> tuple:
    """Wrap ``command`` in a memory-capped user scope when systemd-run can reach the user manager."""
    bus = {name: os.environ[name] for name in USER_BUS_VARIABLES if os.environ.get(name)}
    if not shutil.which("systemd-run") or len(bus) != len(USER_BUS_VARIABLES):
        return command, environment
    with _LOCK:
        if SCOPE_KEY not in _FOUND:
            probe = subprocess.run(["systemd-run", "--user", "--scope", "--quiet", "--collect", "true"],
                                   capture_output=True, timeout=30, env={**environment, **bus})
            _FOUND[SCOPE_KEY] = probe.returncode == 0
        if not _FOUND[SCOPE_KEY]:
            return command, environment
    wrapper = [ENV_PROGRAM, "-u", BUS_ADDRESS_VARIABLE, f"{RUNTIME_DIRECTORY_VARIABLE}={home / '.runtime'}"]
    scoped = ["systemd-run", "--user", "--scope", "--quiet", "--collect", "-p", f"MemoryMax={memory}",
              "-p", "MemorySwapMax=256M", "--", *wrapper, *command]
    return scoped, {**environment, **bus}


# ------------------------------------------------------------------------------------------------ static contract

def module_exports(text: str) -> dict:
    """Export name -> kind for the declarations a module may use; other export forms are reported by name."""
    found = {}
    for pattern, kind in ((EXPORT_FUNCTION, KIND_FUNCTION), (EXPORT_CLASS, KIND_CLASS),
                          (EXPORT_CONSTANT, KIND_CONSTANT)):
        for name in pattern.findall(text):
            found[name] = kind
    return found


def static_contract(package: Path, contract: dict) -> list:
    problems = []
    module = package / contract["module"]
    if not module.is_file():
        return [f"module {contract['module']} is missing"]
    text = module.read_text(encoding="utf-8")
    declared = {row["name"]: row["kind"] for row in contract["exports"]}
    actual = module_exports(text)
    if actual != declared:
        problems.append({"declared": declared, "exported": actual})
    if EXPORT_OTHER.search(text):
        problems.append("only export function, export class and export const declarations are allowed")
    demo = package / contract["demo"]["file"]
    for path in (module, demo):
        if not path.is_file():
            problems.append(f"{path.name} is missing")
        elif IMPORT_STATEMENT.search(path.read_text(encoding="utf-8")):
            problems.append(f"{path.relative_to(package)} imports another module")
    for name in contract["demo"].get("addons", []):
        if name not in ADDONS:
            problems.append(f"unknown addon {name}")
    return problems


# --------------------------------------------------------------------------------------------------- node tests

def root_modules(package: Path) -> tuple:
    """(modules, tests): root-level .mjs files, tests named test_*.mjs (the sandbox's own split)."""
    modules, tests = [], []
    for path in sorted(package.glob("*" + MODULE_SUFFIX)):
        (tests if path.name.startswith(TEST_PREFIX) else modules).append(path.name)
    return modules, tests


def run_node_tests(node: Runtime, package: Path, home: Path, tests: list) -> dict:
    try:
        completed = subprocess.run([node.path, "--test", "--test-reporter=tap", *tests], cwd=package,
                                   env=_isolated_environment(home), capture_output=True, text=True,
                                   timeout=NODE_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        return {"exit": None, "timed_out": True, "counts": None, "tail": ""}
    counts = parse_tap(completed.stdout)
    return {"exit": completed.returncode, "timed_out": False, "counts": counts,
            "tail": (completed.stdout + completed.stderr)[-1500:]}


def tests_passed(row: dict) -> bool:
    counts = row["counts"]
    return (row["exit"] == 0 and not row["timed_out"] and counts is not None and counts["pass"] >= 1
            and counts["fail"] == 0 and counts["cancelled"] == 0)


def mutation_replacement() -> str:
    policy = json.loads(Path(POLICY_PATH).read_text(encoding="utf-8"))
    return policy["mutation"]["javascript_replacement"]


# ------------------------------------------------------------------------------------------------------ browser

class DevToolsPipe:
    """A small Chrome DevTools protocol client over --remote-debugging-pipe.

    Each message is one JSON object followed by a NUL byte. A reader thread files responses by id and keeps every
    event, so console messages and exceptions are available after the run."""

    def __init__(self, process: subprocess.Popen) -> None:
        self.process = process
        self.responses, self.events = {}, []
        self.condition = threading.Condition()
        self.closed = False
        self.counter = 0
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()

    def _read(self) -> None:
        buffer = bytearray()
        stream = self.process.stdout
        while True:
            chunk = stream.read1(1 << 16)
            if not chunk:
                break
            buffer += chunk
            while True:
                end = buffer.find(SEPARATOR)
                if end < 0:
                    break
                message = bytes(buffer[:end])
                del buffer[:end + 1]
                try:
                    data = json.loads(message)
                except ValueError:
                    continue
                with self.condition:
                    if MESSAGE_ID in data:
                        self.responses[data[MESSAGE_ID]] = data
                    else:
                        self.events.append(data)
                    self.condition.notify_all()
        with self.condition:
            self.closed = True
            self.condition.notify_all()

    def send(self, method: str, params: "dict | None" = None, session: "str | None" = None,
             timeout: float = 30.0) -> dict:
        with self.condition:
            self.counter += 1
            number = self.counter
        message = {"id": number, "method": method, "params": params or {}}
        if session:
            message["sessionId"] = session
        try:
            self.process.stdin.write(json.dumps(message).encode("utf-8") + SEPARATOR)
            self.process.stdin.flush()
        except OSError as error:
            raise BrowserError(f"{method}: the browser closed its pipe ({type(error).__name__})") from None
        deadline = time.monotonic() + timeout
        with self.condition:
            while number not in self.responses:
                if self.closed:
                    raise BrowserError(f"{method}: the browser exited")
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise BrowserError(f"{method}: no answer within {timeout} s")
                self.condition.wait(remaining)
            response = self.responses.pop(number)
        if MESSAGE_ERROR in response:
            raise BrowserError(f"{method}: {response[MESSAGE_ERROR].get('message', '')}"[:400])
        return response.get("result", {})

    def wait_for(self, method: str, session: str, timeout: float) -> dict:
        deadline = time.monotonic() + timeout
        with self.condition:
            while True:
                for event in self.events:
                    if event.get("method") == method and event.get("sessionId") == session:
                        return event
                if self.closed:
                    raise BrowserError(f"the browser exited before {method}")
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise BrowserError(f"no {method} within {timeout} s")
                self.condition.wait(remaining)

    def page_messages(self) -> tuple:
        """(failures, warnings): console and log messages that fail the page, and the other warnings."""
        failures, warnings = [], []
        with self.condition:
            events = list(self.events)
        for event in events:
            method, params = event.get("method"), event.get("params", {})
            text, level = None, None
            if method == EXCEPTION_EVENT:
                details = params.get("exceptionDetails", {})
                text = (details.get("exception", {}).get("description") or details.get("text") or "exception")
                level = "error"
            elif method == CONSOLE_EVENT:
                level = params.get("type")
                text = " ".join(str(argument.get("value", argument.get("description", "")))
                                for argument in params.get("args", []))
            elif method == LOG_EVENT:
                entry = params.get("entry", {})
                level, text = entry.get("level"), entry.get("text", "")
            if text is None:
                continue
            text = text[:600]
            if any(pattern.search(text) for pattern in HARMLESS_MESSAGES):
                continue
            if level in FAILING_LEVELS or (level in WARNING_LEVELS and FAILING_WARNING.search(text)):
                failures.append(text)
            elif level in WARNING_LEVELS:
                warnings.append(text)
        return failures, warnings


def _page(workspace: Path, three: Path, config: dict) -> Path:
    import_map = {"imports": {"three": (three / THREE_ENTRY).as_uri(),
                              "three/addons/": (three / THREE_ADDON_FOLDER).as_uri() + "/"}}
    harness = workspace / "harness.mjs"
    shutil.copyfile(HARNESS_SCRIPT, harness)
    text = PAGE_TEMPLATE.read_text(encoding="utf-8")
    text = text.replace("IMPORT_MAP_JSON", json.dumps(import_map)).replace(
        "HARNESS_URL_JSON", json.dumps(harness.as_uri())).replace("CONFIG_JSON", json.dumps(config))
    page = workspace / "page.html"
    page.write_text(text, encoding="utf-8")
    return page


def run_page(chrome: Runtime, workspace: Path, page: Path) -> dict:
    """Open the page in a fresh headless browser and return the verification result and the page's messages."""
    home = workspace / ".browser-home"
    environment = _isolated_environment(home)
    # Chrome makes Unix sockets under TMPDIR; a workspace path can pass the 108-byte socket path limit, which makes
    # it stop on a failed CHECK (SIGTRAP). It keeps the system temporary folder.
    environment.pop(TEMPORARY_FOLDER_VARIABLE)
    command = [SHELL_PROGRAM, "-c", PIPE_SHELL, "sh", chrome.path, *CHROME_FLAGS,
               f"--user-data-dir={workspace / '.browser-profile'}", "about:blank"]
    command, environment = _scope(command, environment, home, BROWSER_MEMORY)
    log_path = workspace / "browser.log"
    with log_path.open("wb") as log:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log, cwd=workspace,
                                   env=environment, start_new_session=True)
        pipe = DevToolsPipe(process)
        try:
            target = pipe.send(CREATE_TARGET, {"url": "about:blank"}, timeout=STARTUP_TIMEOUT_SECONDS)["targetId"]
            session = pipe.send(ATTACH, {"targetId": target, "flatten": True})["sessionId"]
            for method in (ENABLE_RUNTIME, ENABLE_PAGE, ENABLE_LOG):
                pipe.send(method, session=session)
            pipe.send(NAVIGATE, {"url": page.as_uri()}, session=session)
            pipe.wait_for(LOAD_EVENT, session, PAGE_TIMEOUT_SECONDS)
            answer = pipe.send(EVALUATE, {"expression": AWAIT_RESULT, "awaitPromise": True, "returnByValue": True},
                               session=session, timeout=PAGE_TIMEOUT_SECONDS)
            failures, warnings = pipe.page_messages()
            if EXCEPTION_DETAILS in answer:
                failures.append(str(answer[EXCEPTION_DETAILS].get("text", "evaluation failed"))[:600])
            result = answer.get("result", {}).get("value")
            try:
                pipe.send(CLOSE_BROWSER, timeout=CLOSE_TIMEOUT_SECONDS)
            except BrowserError:
                pass
            process.wait(timeout=CLOSE_TIMEOUT_SECONDS)
            return {"result": result, "failures": failures, "warnings": warnings}
        finally:
            if process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait(timeout=CLOSE_TIMEOUT_SECONDS)


# -------------------------------------------------------------------------------------------------------- frames

def frame_rgb(encoded: str, size: int) -> bytes:
    """RGB rows top to bottom from the base64 RGBA rows WebGL reads bottom to top."""
    data = base64.b64decode(encoded)
    if len(data) != size * size * 4:
        raise ValueError(f"expected {size * size * 4} bytes, got {len(data)}")
    rows = []
    for row in range(size - 1, -1, -1):
        line = data[row * size * 4:(row + 1) * size * 4]
        rows.append(bytes(value for index, value in enumerate(line) if index % 4 != 3))
    return b"".join(rows)


def frame_statistics(rgb: bytes) -> dict:
    count = len(rgb) // 3
    sums, squares = [0, 0, 0], [0, 0, 0]
    colours = {}
    for index in range(count):
        pixel = rgb[index * 3:index * 3 + 3]
        colours[pixel] = colours.get(pixel, 0) + 1
        for channel in range(3):
            value = pixel[channel]
            sums[channel] += value
            squares[channel] += value * value
    deviation = [max(0.0, squares[k] / count - (sums[k] / count) ** 2) ** 0.5 for k in range(3)]
    return {"mean": [round(sums[k] / count, 2) for k in range(3)], "deviation": [round(d, 2) for d in deviation],
            "mode_share": round(max(colours.values()) / count, 4), "colours": len(colours)}


def changed_pixels(first: bytes, second: bytes) -> int:
    changed = 0
    for index in range(0, len(first), 3):
        if max(abs(first[index + k] - second[index + k]) for k in range(3)) >= CHANGE_THRESHOLD:
            changed += 1
    return changed


# -------------------------------------------------------------------------------------------------------- verify

def _copy_package(context, package: Path) -> None:
    package.mkdir(parents=True)
    for row in context.item["files"]:
        target = package / row["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(Path(context.item_dir) / row["path"], target)
    for row in context.family["shared_files"]:
        shutil.copyfile(Path(context.shared_dir) / row["path"], package / row["path"])
    # The shared contract test reads component.json; the verifier gives it the contract the card will carry.
    card = {"contract": context.item["contract"], "title": context.item["title"]}
    (package / "component.json").write_text(json.dumps(card, indent=2, sort_keys=True), encoding="utf-8")


def verify(context) -> dict:
    workspace = Path(context.workspace)
    contract = context.item["contract"]
    package = workspace / "package"
    _copy_package(context, package)
    checks = []

    problems = static_contract(package, contract)
    checks.append(_check("module_contract_static", not problems, {"problems": problems[:12]}))

    home = workspace / ".node-home"
    try:
        node = locate_node(home)
    except (OSError, subprocess.SubprocessError) as error:
        checks.append(_check("node_available", False, {"error": str(error)[:300]}))
        return {"engine": {}, "checks": checks, "preview": None}
    modules, tests = root_modules(package)
    row = run_node_tests(node, package, home, tests)
    checks.append(_check("node_tests_pass", tests_passed(row) and bool(modules),
                         {"modules": modules, "tests": tests, "counts": row["counts"], "exit": row["exit"],
                          "timed_out": row["timed_out"], **({} if tests_passed(row) else {"tail": row["tail"]})}))

    replacement = mutation_replacement()
    mutants = []
    for module in modules:
        text, replaced = javascript_mutant((package / module).read_text(encoding="utf-8"), replacement)
        copy = workspace / f"mutant_{Path(module).stem}"
        shutil.copytree(package, copy)
        (copy / module).write_text(text, encoding="utf-8")
        mutant = run_node_tests(node, copy, home, tests)
        caught = not mutant["timed_out"] and not tests_passed(mutant)
        mutants.append({"module": module, "exports_replaced": replaced, "caught": caught,
                        "failed_tests": (mutant["counts"] or {}).get("fail")})
    checks.append(_check("node_tests_catch_mutants",
                         bool(mutants) and all(entry["caught"] and entry["exports_replaced"] for entry in mutants),
                         {"mutants": mutants}))

    three, three_problems = locate_three()
    checks.append(_check("three_runtime_pinned", three is not None and not three_problems,
                         {"version": THREE_VERSION, "files": sorted(THREE_FILES), "problems": three_problems}))
    try:
        chrome = locate_chrome(workspace / ".probe-home")
    except (BrowserError, OSError, subprocess.SubprocessError) as error:
        checks.append(_check("browser_available", False, {"error": str(error)[:300]}))
        return {"engine": {}, "checks": checks, "preview": None}
    engine = {"name": ENGINE_NAME, "version": chrome.version, "binary_sha256": chrome.sha256,
              "three": THREE_VERSION, "node": node.version, "node_sha256": node.sha256}
    if three is None or three_problems:
        return {"engine": engine, "checks": checks, "preview": None}

    config = {"size": RESOLUTION, "module": (package / contract["module"]).as_uri(),
              "demo": (package / contract["demo"]["file"]).as_uri(), "addons": contract["demo"].get("addons", []),
              "item": context.item["identity"]}
    try:
        outcome = run_page(chrome, workspace, _page(workspace, three, config))
    except (BrowserError, OSError, subprocess.SubprocessError) as error:
        log = workspace / "browser.log"
        tail = log.read_text(encoding="utf-8", errors="replace")[-800:] if log.is_file() else ""
        checks.append(_check("browser_page_clean", False, {"error": str(error)[:400], "browser_log_tail": tail}))
        return {"engine": engine, "checks": checks, "preview": None}
    result = outcome["result"] if isinstance(outcome["result"], dict) else {"fatal": "no result object"}
    context_info = result.get("context", {})
    engine["renderer"] = f"{context_info.get('renderer', 'unknown')}; {context_info.get('version', '')}; headless"
    page_detail = {"failures": outcome["failures"][:8], "warnings": outcome["warnings"][:8],
                   "fatal": result.get("fatal"), "gl_error": result.get("glError"),
                   "three_revision": result.get("revision"), "webgl2": result.get("webgl2")}
    clean = (not outcome["failures"] and not result.get("fatal") and result.get("glError") == 0
             and result.get("revision") == THREE_REVISION and result.get("webgl2") is True)
    checks.append(_check("browser_page_clean", clean, page_detail))
    shader_errors = result.get("shaderErrors", [])
    checks.append(_check("three_shaders_compiled", not shader_errors and (result.get("programs") or 0) >= 1,
                         {"programs": result.get("programs"), "errors": shader_errors[:4],
                          "drawn": result.get("drawn")}))
    demo_checks = result.get("checks", [])
    checks.append(_check("demo_checks_passed", bool(demo_checks) and all(entry.get("passed") is True
                                                                         for entry in demo_checks),
                         {"checks": demo_checks[:24]}))
    preview = None
    if result.get("pixels"):
        try:
            rgb = frame_rgb(result["pixels"], RESOLUTION)
            statistics = frame_statistics(rgb)
            varied = (max(statistics["deviation"]) >= MINIMUM_DEVIATION
                      and statistics["mode_share"] <= MAXIMUM_MODE_SHARE)
            checks.append(_check("render_not_uniform", varied, statistics))
            if result.get("baseline"):
                changed = changed_pixels(rgb, frame_rgb(result["baseline"], RESOLUTION))
                checks.append(_check("render_differs_from_baseline", changed >= MINIMUM_CHANGED_PIXELS,
                                     {"changed_pixels": changed, "threshold": CHANGE_THRESHOLD}))
            preview = pngio.encode(RESOLUTION, RESOLUTION, rgb, 3)
        except (ValueError, pngio.PngError) as error:
            checks.append(_check("render_not_uniform", False, {"error": str(error)[:300]}))
    else:
        checks.append(_check("render_not_uniform", False, {"error": "no pixels"}))
    if any(check["state"] != PASSED for check in checks):
        preview = None
    return {"engine": engine, "checks": checks, "preview": preview}
