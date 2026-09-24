"""Multiple separate OpenCode generation lanes over remote model endpoints.

Each lane is a fully separate OpenCode setup: its own configuration
directory (OPENCODE_CONFIG_DIR), its own data home (XDG_DATA_HOME), its
own working directory, and its own opencode.jsonc that names exactly one
remote provider. The declared providers are Ollama Cloud
(https://ollama.com/v1, key OLLAMA_API_KEY) and the owner's Tactical
Engineering endpoint (https://ai.tacticalengineering.net:6969/v1, key
TACTICAL_API_KEY, resolved from the system keyring through
tools/operator_credentials.py). No lane may name a local endpoint: a
provider whose base URL is not one of the two declared remote endpoints
is refused before any process starts.

The model supplies UTF-8 candidate file text only. The frozen idea
record from tools/harness_idea_matrix.py owns the method identity, the
known-wrong case, and the acceptance facets. Generated material is
candidate-only: nothing here stages, approves or serves an item, and no
lane may write outside its own run directory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

if __name__ == "__main__" and __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    sys.path.insert(0, str(Path(__file__).resolve().parent))

LANE_RECORD_TYPE = "opencode_generation_lane/v1"
LANE_RUN_RECORD_TYPE = "opencode_generation_lane_run/v1"

#: The only remote endpoints a lane may call. No local model, ever.
DECLARED_ENDPOINTS = {
    "ollama-cloud": {
        "base_url": "https://ollama.com/v1",
        "key_environment": "OLLAMA_API_KEY",
        "models": ("gpt-oss:20b", "gemma4:31b", "glm-5.3-flash", "kimi-k3",
                    "nemotron-3-nano:30b"),
    },
    "tactical": {
        # The owner's Tactical Engineering model server, which also answers
        # as iamretarded.net. The endpoint's Origin certificate is issued
        # for ai.iamretarded.net while the served hostname is
        # ai.tacticalengineering.net, so a Node harness cannot verify the
        # chain by hostname. The owner's documented approach for this
        # endpoint (recorded in the operator opencode configuration and
        # the capacity-measurement binding) is to run the harness with
        # hostname TLS verification disabled; the pinned Origin CA and
        # the pinned leaf digest in the binding record remain the trust
        # evidence. The lane sets NODE_TLS_REJECT_UNAUTHORIZED=0 for its
        # own subprocess only.
        "base_url": "https://ai.tacticalengineering.net:6969/v1",
        "key_environment": "TACTICAL_API_KEY",
        "credential_reference": "tactical-model-generation",
        "models": ("gemma-4-coding-abliterated",),
        "disable_node_tls_verification": True,
    },
}

FORBIDDEN_URL_PATTERNS = (re.compile(r"^https?://(localhost|127\.0\.0\.1|0\.0\.0\.0|::1)"),
                          re.compile(r":11434"))
OPENCODE_EXECUTABLE = Path.home() / ".opencode" / "bin" / "opencode"
MAX_IDEA_FILE_BYTES = 16 * 1024 * 1024
MAX_CANDIDATE_BYTES = 2 * 1024 * 1024
RUN_TIMEOUT_SECONDS = 900.0


class LaneError(ValueError):
    """A lane setup, provider, or run request is invalid."""


def refuse(code: str) -> None:
    raise LaneError(code)


def declared_endpoint(name: str) -> dict:
    if name not in DECLARED_ENDPOINTS:
        refuse("provider_not_declared")
    return DECLARED_ENDPOINTS[name]


def _resolve_key(provider: dict) -> str:
    """Resolve the provider key from the environment or the keyring.

    The Tactical key is resolved through the recorded operator credential
    path only inside the process that makes the call. No key is printed,
    written to a file, or placed in the run record.
    """
    environment = provider["key_environment"]
    value = os.environ.get(environment, "")
    if value:
        return value
    reference = provider.get("credential_reference")
    if not reference:
        refuse("credential_environment_missing")
    try:
        import importlib.util
        from loop_engine.tools import operator_credentials
    except ImportError:
        tools_root = Path(__file__).resolve().parent
        spec = importlib.util.spec_from_file_location(
            "operator_credentials", tools_root / "operator_credentials.py")
        if spec is None or spec.loader is None:
            refuse("credential_resolver_unavailable")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        operator_credentials = module
    manifest = Path(__file__).resolve().parent / "operator_credentials.json"
    if not manifest.is_file():
        refuse("credential_reference_manifest_missing")
    resolved = operator_credentials.resolve(
        reference, data=json.loads(manifest.read_text(encoding="utf-8")))
    value = resolved if isinstance(resolved, str) else getattr(resolved, "value", "")
    if not value:
        refuse("credential_unresolved")
    return value


@dataclass(frozen=True)
class Lane:
    """One separate OpenCode setup: configuration, data, provider, model."""

    lane_id: str
    provider: str
    model: str
    root: Path

    def __post_init__(self):
        endpoint = declared_endpoint(self.provider)
        if self.model not in endpoint["models"]:
            refuse("model_not_declared_for_provider")
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,63}", self.lane_id):
            refuse("lane_id_invalid")
        if self.root.exists() and self.root.is_symlink():
            refuse("lane_root_symlink_refused")

    @property
    def config_directory(self) -> Path:
        return self.root / "opencode-config"

    @property
    def data_home(self) -> Path:
        return self.root / "opencode-data"

    @property
    def workspace(self) -> Path:
        return self.root / "workspace"

    def write_config(self) -> None:
        """Materialize this lane's own opencode.jsonc and directories."""
        endpoint = declared_endpoint(self.provider)
        for directory in (self.root, self.config_directory, self.data_home,
                          self.workspace):
            directory.mkdir(parents=True, exist_ok=True)
        base_url = endpoint["base_url"]
        if any(pattern.search(base_url) for pattern in FORBIDDEN_URL_PATTERNS):
            refuse("local_endpoint_refused")
        provider_block = {
            "npm": "@ai-sdk/openai-compatible",
            "name": self.provider,
            "options": {"baseURL": base_url, "apiKey": "{env:%s}" % endpoint["key_environment"]},
            "models": {self.model: {"name": self.model}},
        }
        config = {
            "$schema": "https://opencode.ai/config.json",
            "provider": {self.provider: provider_block},
            "model": f"{self.provider}/{self.model}",
        }
        target = self.config_directory / "opencode.jsonc"
        target.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")

    def environment(self) -> dict[str, str]:
        """A scrubbed environment built from nothing, by allowlist."""
        endpoint = declared_endpoint(self.provider)
        allowlist = ("OLLAMA_API_KEY", "TACTICAL_API_KEY", "PATH", "HOME",
                     "TERM", "LANG")
        environment = {name: os.environ[name] for name in allowlist
                       if name in os.environ}
        environment[endpoint["key_environment"]] = _resolve_key(endpoint)
        if endpoint.get("disable_node_tls_verification"):
            # Owner-documented trust model for the Tactical Origin
            # certificate; see DECLARED_ENDPOINTS["tactical"].
            environment["NODE_TLS_REJECT_UNAUTHORIZED"] = "0"
        environment["OPENCODE_CONFIG_DIR"] = str(self.config_directory)
        environment["XDG_DATA_HOME"] = str(self.data_home)
        return environment


#: File kinds a lane can generate. The default is the Agent Skills shape;
#: the others come from the registry survey of September 24, 2026 and
#: the harness file kinds research, and each has its own shape check.
FILE_KINDS = ("skill", "plugin_manifest", "harness_routing", "rules",
              "workflow", "hook", "subagent")

_KIND_PROMPTS = {
    "skill": (
        "Write one original harness method as a Markdown file with YAML "
        "frontmatter, following the Agent Skills specification. "
        "The frontmatter must name: name (the identity), description (when to "
        "use it), and license (MIT). The body must state: trigger, typed input, "
        "typed output, effects, stop condition, the known-wrong case, and an "
        "acceptance check."
    ),
    "plugin_manifest": (
        "Write one original portable Agent Plugins manifest as a single JSON "
        "object (no Markdown, no code fences). It must have: name (the "
        "identity), version (\"1.0.0\"), description, schema "
        "(\"https://agentplugins.io/schema/v1\"), and one \"skills\" array "
        "holding exactly one skill entry with a name and description, and one "
        "\"mcpServers\" object holding exactly one server entry with a command "
        "and no secrets (environment variable references only)."
    ),
    "harness_routing": (
        "Write one original harness routing file as a Markdown file with YAML "
        "frontmatter naming: name (the identity), description, license (MIT). "
        "The body is a progressive-disclosure routing table: three task "
        "patterns, and for each the subdirectory or subpackage a step should "
        "open, with one line of reason. No links to files that are not named."
    ),
    "rules": (
        "Write one original rules file as a Markdown file, no frontmatter, "
        "titled with a single # heading equal to the identity. Exactly three "
        "sections: '## Must never do', '## Must do', '## When unsure', each "
        "with two to four imperative rules for this one task domain."
    ),
    "workflow": (
        "Write one original reusable workflow recipe as a Markdown file with "
        "YAML frontmatter naming: name (the identity), description, license "
        "(MIT). The body must have '## Goal', '## When to run', '## Steps' "
        "(numbered), '## Success criteria', '## Failure controls'."
    ),
    "hook": (
        "Write one original Claude Code settings hook as a single JSON object "
        "(no Markdown, no code fences) with a top-level \"hooks\" key. Each "
        "event value is an array of objects with \"matcher\" and \"hooks\", "
        "where each hook names \"type\": \"command\" and a \"command\" that "
        "reads only files in the current project and never sends network "
        "traffic or writes outside the working directory."
    ),
    "subagent": (
        "Write one original subagent definition as a Markdown file with YAML "
        "frontmatter naming: name (the identity), description (when to use "
        "this subagent), tools (a list), model. The body must have "
        "'## How you work' and '## What you never do' sections."
    ),
}

_KIND_FILE_NAMES = {
    "skill": "SKILL.md",
    "plugin_manifest": "plugin.json",
    "harness_routing": "HARNESS.md",
    "rules": "rules.md",
    "workflow": "WORKFLOW.md",
    "hook": "hook.json",
    "subagent": "AGENT.md",
}


def _idea_file_kind(idea: dict) -> str:
    """The declared file kind of an idea, defaulting to the skill shape."""
    kind = idea.get("file_kind", "skill")
    if kind not in FILE_KINDS:
        refuse("file_kind_not_declared")
    return kind


def _render_prompt(idea: dict) -> str:
    applicability = idea["applicability"]
    kind = _idea_file_kind(idea)
    return (
        f"{_KIND_PROMPTS[kind]} "
        f"The identity is {idea['id']}: input datatype {idea['datatype']}, "
        f"operation {idea['operation']}, use case {idea['use_case']}. "
        f"Ground it in this real task statement: {applicability['task_reference']}. "
        "The known-wrong case it must catch is: "
        f"{idea['known_wrong']}. "
        "Write only the file content, no commentary. Never claim an "
        "effect the file cannot perform by itself."
    )


class LaneRunner:
    """Run one lane over one idea and record the call in a ledger."""

    def __init__(self, lane: Lane, executable: Path = OPENCODE_EXECUTABLE):
        self.lane = lane
        self.executable = executable
        self.runs_directory = lane.root / "runs"

    def write_idea(self, idea: dict) -> Path:
        if idea.get("record_type") != "harness_idea_record/v1":
            refuse("idea_record_unsupported")
        body = json.dumps(idea, indent=2, ensure_ascii=False).encode("utf-8")
        if len(body) > MAX_IDEA_FILE_BYTES:
            refuse("idea_record_too_large")
        self.lane.workspace.mkdir(parents=True, exist_ok=True)
        idea_path = self.lane.workspace / "idea.json"
        idea_path.write_bytes(body)
        return idea_path

    def run(self, idea: dict, ledger_path: Path) -> dict:
        """One model call per idea, recorded before dispatch, never repeated."""
        if not self.executable.is_file():
            refuse("opencode_executable_missing")
        self.runs_directory.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        run_id = f"{self.lane.lane_id}-{idea['id']}-{stamp}"
        record = {
            "record_type": LANE_RUN_RECORD_TYPE,
            "run_id": run_id,
            "lane_id": self.lane.lane_id,
            "provider": self.lane.provider,
            "base_url": declared_endpoint(self.lane.provider)["base_url"],
            "model": self.lane.model,
            "idea_id": idea["id"],
            "method_signature": idea["method_signature"],
            "started_at": stamp,
        }
        _append_jsonl(ledger_path, record)
        prompt = _render_prompt(idea)
        argv = [str(self.executable), "run", "--pure", "--format", "json",
                "--title", run_id, "--dir", str(self.lane.workspace), prompt]
        try:
            completed = subprocess.run(
                argv, capture_output=True, text=True, timeout=RUN_TIMEOUT_SECONDS,
                env=self.lane.environment(), cwd=str(self.lane.workspace))
        except subprocess.TimeoutExpired:
            record["outcome"] = "timeout"
            _append_jsonl(ledger_path, record)
            return record
        record["exit_code"] = completed.returncode
        record["artifact_files"] = _artifact_files(self.lane.workspace, idea)
        candidate = self.lane.workspace / "candidate.md"
        accepted = False
        if completed.returncode == 0:
            response_text = _strip_code_fence(_extract_message_text(completed.stdout))
            written_file = record["artifact_files"].get("skill_md")
            if written_file:
                body = Path(written_file).read_bytes()[:MAX_CANDIDATE_BYTES]
                candidate.write_bytes(body)
                response_text = body.decode("utf-8", "replace")
            if response_text:
                body = response_text.encode("utf-8")[:MAX_CANDIDATE_BYTES]
                candidate.write_bytes(body)
                record["candidate_sha256"] = hashlib.sha256(body).hexdigest()
                record["candidate_bytes"] = len(body)
                accepted = _looks_like_candidate(body.decode("utf-8", "replace"), idea)
                record["outcome"] = "candidate_written" if accepted else "response_not_candidate"
            else:
                record["outcome"] = "empty_response"
        else:
            record["outcome"] = "opencode_failed"
        record["finished_at"] = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        _append_jsonl(ledger_path, record)
        if not accepted:
            refuse("generation_did_not_produce_candidate" if completed.returncode == 0
                   else "opencode_run_failed")
        return record


def _artifact_files(workspace: Path, idea: dict) -> dict:
    """Map written candidate paths the harness itself produced, if any.

    Some models answer by writing a file in the workspace instead of
    replying with text. A file at the idea's native path for its declared
    file kind, or at the flat idea-named Markdown path, counts; nothing
    else does.
    """
    markers = {}
    file_name = _KIND_FILE_NAMES[_idea_file_kind(idea)]
    candidates = (
        workspace / idea["id"] / file_name,
        workspace / idea["id"] / "SKILL.md",
        workspace / f"{idea['id']}.md",
    )
    for candidate in candidates:
        if candidate.is_file() and not candidate.is_symlink():
            resolved = candidate.resolve()
            if str(resolved).startswith(str(workspace.resolve())):
                markers["skill_md"] = str(candidate)
                break
    return markers


def _extract_message_text(stdout: str) -> str:
    """Take the assistant text from the last JSON text event line."""
    text = ""
    for line in stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except ValueError:
            continue
        part = event.get("part", {})
        if event.get("type") == "text" and part.get("type") == "text":
            text = part.get("text", "")
    return text


def _looks_like_candidate(body: str, idea: dict) -> bool:
    """Deterministic shape check per declared file kind.

    Some models wrap the file in a fenced code block. A single such wrapper
    is stripped before the shape check; the recorded candidate keeps the
    stripped body so the file is a native document of its kind.
    """
    stripped = _strip_code_fence(body)
    kind = _idea_file_kind(idea)
    if kind == "plugin_manifest" or kind == "hook":
        try:
            value = json.loads(stripped)
        except ValueError:
            return False
        if not isinstance(value, dict):
            return False
        if kind == "plugin_manifest":
            return (value.get("name") == idea["id"]
                    and isinstance(value.get("description"), str) and value["description"]
                    and value.get("schema") == "https://agentplugins.io/schema/v1"
                    and isinstance(value.get("skills"), list) and len(value["skills"]) == 1
                    and isinstance(value.get("mcpServers"), dict))
        return ("hooks" in value and isinstance(value["hooks"], dict) and value["hooks"])
    if kind == "rules":
        return stripped.startswith(f"# {idea['id']}\n") and "## Must never do" in stripped
    if kind == "skill" or kind == "harness_routing" or kind == "workflow" or kind == "subagent":
        if not stripped.startswith("---"):
            return False
        end = stripped.find("\n---", 3)
        if end < 0:
            return False
        frontmatter = stripped[3:end]
        if f"name: {idea['id']}" not in frontmatter or "description:" not in frontmatter:
            return False
        if kind == "subagent":
            return "## How you work" in stripped and "## What you never do" in stripped
        if kind == "workflow":
            return "## Steps" in stripped and "## Success criteria" in stripped
        if kind == "harness_routing":
            return "## " in stripped[stripped.find("\n---", 3) + 4:]
        return "license:" in frontmatter
    refuse("file_kind_not_declared")


def _strip_code_fence(body: str) -> str:
    """Remove one outer ```markdown fence if the whole body is wrapped."""
    text = body.strip()
    if not text.startswith("```"):
        return body
    first_newline = text.find("\n")
    if first_newline < 0:
        return body
    inner = text[first_newline + 1:]
    if inner.rstrip().endswith("```"):
        inner = inner.rstrip()[:-3]
    return inner.strip() + "\n"


def _append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")


def _default_lane_roots(base: Path) -> Path:
    return base / "opencode-generation-lanes"


def build_lanes(lane_root: Path, lane_specs: list[dict]) -> list[Lane]:
    """Build each declared lane as a separate OpenCode setup."""
    lanes = []
    for spec in lane_specs:
        lane = Lane(
            lane_id=spec["lane_id"],
            provider=spec["provider"],
            model=spec["model"],
            root=lane_root / spec["lane_id"],
        )
        lane.write_config()
        lanes.append(lane)
    if not lanes:
        refuse("no_lanes_declared")
    return lanes


DEFAULT_LANE_SPECS = [
    {"lane_id": "lane-ollama-gpt-oss-20b", "provider": "ollama-cloud", "model": "gpt-oss:20b"},
    {"lane_id": "lane-ollama-gemma4-31b", "provider": "ollama-cloud", "model": "gemma4:31b"},
    {"lane_id": "lane-ollama-glm-53-flash", "provider": "ollama-cloud", "model": "glm-5.3-flash"},
    {"lane_id": "lane-tactical-gemma4", "provider": "tactical", "model": "gemma-4-coding-abliterated"},
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--lane-root", required=True,
                        help="root directory that will hold the separate lanes")
    parser.add_argument("--ideas", required=True,
                        help="the idea batch JSON from tools/harness_idea_matrix.py")
    parser.add_argument("--limit", type=int, default=1,
                        help="how many ideas each lane generates this run")
    parser.add_argument("--lanes", default=None,
                        help="JSON file of lane specs; default is four lanes")
    args = parser.parse_args(argv)

    lane_root = Path(args.lane_root).absolute()
    if lane_root.exists() and lane_root.is_symlink():
        refuse("lane_root_symlink_refused")
    ideas_file = Path(args.ideas)
    if ideas_file.is_symlink() or not ideas_file.is_file():
        refuse("ideas_file_invalid")
    batch = json.loads(ideas_file.read_text(encoding="utf-8"))
    if batch.get("record_type") != "harness_idea_batch/v1":
        refuse("ideas_batch_unsupported")
    ideas = batch["ideas"][:max(0, args.limit)]
    if not ideas:
        refuse("no_ideas_selected")
    specs = DEFAULT_LANE_SPECS
    if args.lanes:
        loaded = json.loads(Path(args.lanes).read_text(encoding="utf-8"))
        if not isinstance(loaded, list) or not loaded:
            refuse("lane_specs_invalid")
        specs = loaded
    lanes = build_lanes(lane_root, specs)
    ledger_path = lane_root / "generation-ledger.jsonl"
    results = []
    for lane in lanes:
        runner = LaneRunner(lane)
        for idea in ideas:
            runner.write_idea(idea)
            results.append(runner.run(idea, ledger_path))
    print(json.dumps({"lanes": len(lanes), "ideas_per_lane": len(ideas),
                      "runs": results}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())