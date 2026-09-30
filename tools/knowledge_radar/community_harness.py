"""Bounded native web-research delegate, not a second runtime or approval route.

The command uses an existing ChatGPT login, no inherited API-key environment,
an empty working folder and disabled shell, app, plugin and sub-agent tools.
Its native search is a separate acquisition path from direct forum APIs.
One invocation may contain several model turns; reported usage stays distinct
from invocation count. Results remain unverified research, never components.
"""
from __future__ import annotations

import hashlib
import json
import re
import tempfile
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from loop_engine.core.library_ingestion.processes import (
    passthrough_environment,
    run_command,
)
from loop_engine.loop.loop_contract import LoopContract
from loop_engine.loop.loop_role import LoopRelationship, LoopRole, LoopRoleIdentity
from loop_engine.loop.recursive_loop import Loop, LoopConfig, StepOutcome

from .community_intake import public_url

ENGINE_ID, ENGINE_VERSION = "codex_web_research", "1.0.0"
PROMPT_FILE = Path(__file__).with_name("community-research-prompt-v1.txt")
PROMPT_VERSION = "community_research_prompt/v1"
NATIVE_AGENT_MESSAGE, NATIVE_REASONING, NATIVE_ERROR = "agent_message", "reasoning", "error"
COMPLETE = "complete"
TEXT = {"type": "string", "maxLength": 800}
STRINGS = {"type": "array", "items": TEXT, "maxItems": 8}
FINDING_SCHEMA = {"type": "object", "additionalProperties": False,
    "required": ["source_url", "title", "summary", "tools", "steps", "constraints", "linked_sources"],
    "properties": {"source_url": {"type": "string", "maxLength": 2048}, "title": {"type": "string", "maxLength": 200},
                   "summary": TEXT, "tools": STRINGS, "steps": STRINGS, "constraints": STRINGS,
                   "linked_sources": {"type": "array", "maxItems": 8, "items": {"type": "string", "maxLength": 2048}}}}
SCHEMA = {"type": "object", "additionalProperties": False, "required": ["findings", "limitations"],
          "properties": {"limitations": STRINGS, "findings": {"type": "array", "maxItems": 6, "items": FINDING_SCHEMA}}}


def command(workdir, schema, prompt):
    flags = ["codex", "--no-daemon", "--search", "-a", "never"]
    for feature in ("shell_tool", "unified_exec", "apps", "plugins", "hooks", "multi_agent", "computer_use",
                    "browser_use", "browser_use_external", "image_generation", "view_image", "goals", "sleep_tool"):
        flags += ["--disable", feature]
    return [*flags, "exec", "--ignore-user-config", "--ephemeral", "--sandbox", "read-only",
            "--skip-git-repo-check", "--json", "-C", str(workdir), "--output-schema", str(schema), prompt]


def research(topic, runtime, *, authorized=False, timeout=180, runner=run_command):
    if not authorized:
        raise PermissionError("native_research_invocation_not_authorized")
    environment = passthrough_environment(("HOME", "PATH", "LANG", "XDG_RUNTIME_DIR", "DBUS_SESSION_BUS_ADDRESS", "CODEX_HOME"))
    auth = runner(("codex", "login", "status"), timeout_seconds=15, maximum_output_bytes=4096, environment=environment)
    if auth.exit_code != 0 or "Logged in using ChatGPT" not in (auth.stdout.decode("utf-8", "replace") + auth.stderr_tail):
        return {"status": "unavailable", "reason": "existing_subscription_login_not_confirmed", "invocations": 0}
    template = PROMPT_FILE.read_text(encoding="utf-8")
    if sorted(re.findall(r"\{\{(.*?)\}\}", template)) != ["domains", "query"]:
        raise ValueError("research_prompt_slots_invalid")
    slots = {"query": topic["query"], "domains": ", ".join(topic["domains"])}
    prompt = re.sub(r"\{\{(query|domains)\}\}", lambda match: slots[match.group(1)], template)
    usage, findings, limits, seen_tools = None, [], [], []
    status = "failed"
    with tempfile.TemporaryDirectory(prefix="baltor-community-research-") as temporary:
        workdir = Path(temporary)
        schema = workdir / "answer.schema.json"
        schema.write_text(json.dumps(SCHEMA), encoding="utf-8")
        contract = LoopContract("community_web_research/v1", execution_mode="model_led",
            input_roles=("community_research_topic/v1",), output_roles=("community_research_batch/v1",),
            effects=("reads_fs", "writes_fs", "reads_secret", "network", "spawns_process"),
            locality="local_machine", cost_class="metered", role="practitioner.research")
        loop = Loop("Research one bounded public community topic.", LoopConfig(framework="custom",
            custom_steps=("research",), allowable_modes=("non_deterministic",), preferred_modes=("non_deterministic",),
            delegated_modes=("non_deterministic",), exit_condition="accepted_success"), ledger=runtime.ledger,
            contract=contract, identity=LoopRoleIdentity(LoopRole.PRACTITIONER, "practitioner.research"),
            relationship=LoopRelationship.starting())
        held = {}

        def handler(_active, _step, _context):
            held["result"] = runner(command(workdir, schema, prompt), timeout_seconds=timeout,
                maximum_output_bytes=1024 * 1024, environment=environment, cwd=str(workdir))
            return StepOutcome(output="native research invocation ended", mode="non_deterministic", confidence=1.0)

        loop.run(handler=handler, max_steps=1)
        result = held["result"]
    messages, errors = [], []
    for line in result.stdout.decode("utf-8", "replace").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        if event.get("type") == "turn.completed":
            usage = event.get("usage")
        if event.get("type") in ("error", "turn.failed"):
            errors.append(str(event.get("message") or event.get("error") or ""))
        item = event.get("item") or {}
        if event.get("type") == "item.completed" and isinstance(item, dict):
            kind = item.get("type", "")
            if kind == NATIVE_AGENT_MESSAGE:
                messages.append(item.get("text", ""))
            elif kind not in (NATIVE_REASONING,):
                if kind == NATIVE_ERROR:
                    errors.append(str(item.get("message") or item.get("text") or item.get("error") or "native_tool_error"))
                else:
                    seen_tools.append(kind)
    error_text = " ".join(errors + [result.stderr_tail]).lower()
    reason = ("timeout" if result.timed_out else "usage_limit" if any(word in error_text for word in ("usage limit", "quota", "hit your limit"))
              else "output_limit" if result.truncated else "harness_failed")
    diagnostic = re.sub(r"(?i)(bearer\s+\S+|(?:sk|rk|pk)[_-]\S+|[A-Za-z0-9_-]{40,})", "[redacted]",
                        " ".join(errors + [result.stderr_tail]))[:350]
    forbidden_tools = set(seen_tools) - {"web_search", "web_search_call"}
    if forbidden_tools:
        reason = "unexpected_tool_use"
    if result.exit_code == 0 and not result.truncated and not errors and messages and not forbidden_tools:
        try:
            answer = json.loads(messages[-1])
            Draft202012Validator(SCHEMA).validate(answer)
            for row in answer["findings"]:
                row["source_url"] = public_url(row["source_url"])
                from urllib.parse import urlsplit
                host = urlsplit(row["source_url"]).hostname
                if not any(host == domain or host.endswith("." + domain) for domain in topic["domains"]):
                    raise ValueError("source_outside_topic")
                row["linked_sources"] = [public_url(value) for value in row["linked_sources"]]
            findings, limits = answer["findings"], answer["limitations"]
            status, reason = COMPLETE, ""
        except (ValueError, KeyError, ValidationError):
            reason = "answer_schema_or_scope_failed"
    return {"record_type": "community_research_batch/v1", "engine": ENGINE_ID, "engine_version": ENGINE_VERSION,
            "status": status, "reason": reason, "findings": findings, "limitations": limits,
            "diagnostic": diagnostic if status != COMPLETE else "",
            "prompt_version": PROMPT_VERSION, "prompt_template_sha256": hashlib.sha256(template.encode()).hexdigest(),
            "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
            "invocations": 1, "physical_model_calls": None, "reported_usage": usage, "reported_model": None,
            "observed_tool_kinds": sorted(set(seen_tools)), "elapsed_ms": result.elapsed_ms,
            "tool_page_limits": "task instructions; native event coverage does not prove an exact page count",
            "reproduced": False, "publication_approved": False, "loop_id": loop.loop_id}
