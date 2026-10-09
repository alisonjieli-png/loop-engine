"""Locate the pinned native engines and run them in a bounded, isolated way.

The verifiers open real files in real engines: Godot 4 (GDScript tests headless, shaders and scenes under a virtual
display with the OpenGL compatibility renderer) and Blender (background mode, factory settings). An engine is found
through BALTOR_GODOT or BALTOR_BLENDER, then the pinned portable builds of the studio project, then PATH. Its binary
digest is computed once per (path, size, modification time) and recorded in every evidence record, so a reader can
tell exactly which build observed a pass.

Each run gets its own HOME and XDG folders inside the workspace (no user configuration is read or written), a wall
clock limit, and a memory-capped systemd scope when ``systemd-run --user`` is available.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

ENVIRONMENT_VARIABLES = {"godot": "BALTOR_GODOT", "blender": "BALTOR_BLENDER"}
#: The official portable builds, unpacked from archives checked against their published digests (Blender
#: blender-5.2.1-linux-x64.tar.xz SHA-256 a31f524f..., Godot 4.7.2-stable Linux x86_64 zip SHA-512 9aa00f7a...),
#: first on the fast system disk, then the studio project's copies on the shared USB drive.
PINNED = {"godot": ["~/.cache/baltor-creative/runtimes/Godot_v4.7.2-stable_linux.x86_64",
                    "~/social_videos/studio/.runtimes/Godot_v4.7.2-stable_linux.x86_64"],
          "blender": ["~/.cache/baltor-creative/runtimes/blender-5.2.1-linux-x64/blender",
                      "~/social_videos/studio/.runtimes/blender-5.2.1-linux-x64/blender"]}
ON_PATH = {"godot": ("godot4", "godot"), "blender": ("blender",)}
DIGEST_CACHE = Path("~/.cache/baltor-creative/engine-digests.json").expanduser()
VIRTUAL_SCREEN = "1280x720x24"


class EngineUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class Engine:
    name: str
    path: str
    version: str
    sha256: str

    def identity(self) -> dict:
        return {"name": self.name, "version": self.version, "binary_sha256": self.sha256}


def _digest(path: Path) -> str:
    stat = path.stat()
    key = f"{path}|{stat.st_size}|{stat.st_mtime_ns}"
    cache = {}
    if DIGEST_CACHE.is_file():
        try:
            cache = json.loads(DIGEST_CACHE.read_text())
        except (OSError, ValueError):
            cache = {}
    if key not in cache:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1 << 20), b""):
                digest.update(block)
        cache[key] = digest.hexdigest()
        DIGEST_CACHE.parent.mkdir(parents=True, exist_ok=True)
        temporary = DIGEST_CACHE.with_suffix(f".{os.getpid()}.tmp")
        temporary.write_text(json.dumps(cache, indent=1, sort_keys=True))
        temporary.replace(DIGEST_CACHE)
    return cache[key]


_LOCATED = {}


def locate(name: str) -> Engine:
    """The engine to use, or EngineUnavailable naming every place searched."""
    if name in _LOCATED:
        return _LOCATED[name]
    if name not in ENVIRONMENT_VARIABLES:
        raise EngineUnavailable(f"unknown engine {name}")
    candidates = []
    if os.environ.get(ENVIRONMENT_VARIABLES[name]):
        candidates.append(os.environ[ENVIRONMENT_VARIABLES[name]])
    candidates += [str(Path(path).expanduser()) for path in PINNED[name]]
    candidates += [found for found in (shutil.which(binary) for binary in ON_PATH[name]) if found]
    for candidate in candidates:
        path = Path(candidate)
        if path.is_file() and os.access(path, os.X_OK):
            with tempfile.TemporaryDirectory(prefix="baltor-engine-probe-") as probe_home:
                completed = subprocess.run([str(path), "--version"] if name == "godot" else
                                           [str(path), "--background", "--factory-startup", "--version"],
                                           capture_output=True, text=True, timeout=120,
                                           env=_isolated_environment(Path(probe_home)))
            lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
            version = next((line for line in lines if line[:1].isdigit() or line.startswith("Blender ")), "unknown")
            engine = Engine(name, str(path), version.replace("Blender ", ""), _digest(path))
            _LOCATED[name] = engine
            return engine
    raise EngineUnavailable(f"{name} not found; set {ENVIRONMENT_VARIABLES[name]} (searched {candidates})")


def _isolated_environment(home: Path) -> dict:
    return {"HOME": str(home), "XDG_CONFIG_HOME": str(home / ".config"), "XDG_DATA_HOME": str(home / ".local/share"),
            "XDG_CACHE_HOME": str(home / ".cache"), "XDG_RUNTIME_DIR": str(home / ".runtime"),
            "PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "TMPDIR": str(home / ".tmp")}


def run(engine: Engine, arguments: list, *, workspace: Path, timeout: int = 180, display: bool = False,
        memory: str = "3G", environment: "dict | None" = None) -> dict:
    """Run the engine with ``arguments`` in ``workspace`` and return what happened, never raising on a failure.

    ``display`` wraps the run in xvfb-run so Godot can open a real OpenGL context (Mesa llvmpipe on this host)."""
    workspace = Path(workspace)
    home = workspace / ".home"
    for folder in (home, home / ".config", home / ".local/share", home / ".cache", home / ".runtime", home / ".tmp"):
        folder.mkdir(parents=True, exist_ok=True)
    os.chmod(home / ".runtime", 0o700)
    command = [engine.path, *arguments]
    if display:
        if not shutil.which("xvfb-run"):
            return {"returncode": None, "timed_out": False, "seconds": 0.0, "stdout": "", "stderr": "",
                    "error": "xvfb-run is not installed", "command": command}
        command = ["xvfb-run", "-a", "-s", f"-screen 0 {VIRTUAL_SCREEN}", *command]
    if shutil.which("systemd-run"):
        probe = subprocess.run(["systemd-run", "--user", "--scope", "--quiet", "--collect", "true"],
                               capture_output=True, timeout=30)
        if probe.returncode == 0:
            command = ["systemd-run", "--user", "--scope", "--quiet", "--collect", "-p", f"MemoryMax={memory}",
                       "-p", "MemorySwapMax=256M", "--", *command]
    started = time.monotonic()
    env = _isolated_environment(home)
    if environment:
        env.update(environment)
    try:
        completed = subprocess.run(command, cwd=workspace, env=env, capture_output=True, text=True,
                                   errors="replace", timeout=timeout)
        outcome = {"returncode": completed.returncode, "timed_out": False, "stdout": completed.stdout[-20000:],
                   "stderr": completed.stderr[-20000:]}
    except subprocess.TimeoutExpired as error:
        outcome = {"returncode": None, "timed_out": True,
                   "stdout": (error.stdout or b"")[-20000:].decode("utf-8", "replace") if isinstance(error.stdout, bytes)
                   else (error.stdout or "")[-20000:],
                   "stderr": (error.stderr or b"")[-20000:].decode("utf-8", "replace") if isinstance(error.stderr, bytes)
                   else (error.stderr or "")[-20000:]}
    outcome["seconds"] = round(time.monotonic() - started, 3)
    outcome["command"] = [part if not part.startswith(str(Path.home())) else "~" + part[len(str(Path.home())):]
                          for part in command]
    return outcome


__all__ = ["Engine", "EngineUnavailable", "locate", "run", "VIRTUAL_SCREEN"]
