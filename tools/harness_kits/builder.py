"""Build, verify, and safely materialize AgentFoundry multi-harness starter kits.

Every starter kit bundles:
- Target harness files for claude_code, codex, cursor, opencode, or all
- Linked AgentFeeds READING.md and profile.json compiled from curated collections
- A deterministic verifier script (verify_kit.py) with positive and known-wrong controls
- A CataloguePackage manifest with SHA-256 digests (approved=False, published=False, effects_granted=[])

All writes require explicit local write authorization and use descriptor-relative
O_NOFOLLOW operations to refuse symbolic links, path traversal, and overwrites.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import re
import stat
import sys
from typing import Any

_REPO_SRC = str(Path(__file__).resolve().parents[2] / "src")
if _REPO_SRC not in sys.path:
    sys.path.insert(0, _REPO_SRC)

from loop_engine.core.model_call_records import default_secret_patterns
from loop_engine.core.service_runtime.catalogue_packages import (
    PACKAGE_BODY,
    CataloguePackage,
    CataloguePackageFile,
    placement_path,
    sha256_hex,
)
from loop_engine.core.service_runtime.feed_profiles import (
    FeedProfileError,
    ProfileRequest,
    compile_files,
    current_directory,
    read_profile,
    validate as validate_feed_profile,
)

from .catalog import (
    HARNESS_CHOICES,
    STARTER_KIT_RECORD_TYPE,
    SUPPORTED_HARNESSES,
    StarterKitSpec,
    get_starter_kit_spec,
)
from .drift_linters import (
    check_llm_sdk_drift,
    check_mcp_server_safety,
    check_nextjs_react19_tailwind4_drift,
    check_pydantic_v2_fastapi_drift,
)

MANIFEST_FILENAME = "kit_manifest.json"
VERIFIER_FILENAME = "verify_kit.py"
FEED_PROFILE_PATH = "feeds/profile.json"
FEED_READING_PATH = "feeds/READING.md"

_FOLDER_NAME_RE = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}\Z")
_STEERING_RE = re.compile(
    r"(?i)(?:\b(?:ignore|disregard|forget|override)\b[^.\n]{0,40}\b(?:previous|prior|above|earlier|all|any)\b[^.\n]{0,20}\b(?:instructions?|prompts?|rules?|guidelines?)\b"
    r"|\b(?:grant|authorize|override|disable)\b[^.\n]{0,40}\b(?:all\s+permissions?|safeguards?|restrictions?)\b"
    r"|\b(?:approve\s+this\s+(?:item|skill|file|kit)|mark\s+(?:it|this)\s+(?:as\s+)?approved|you\s+are\s+now\s+in\s+developer\s+mode)\b"
    r"|\b(?:curl|wget|fetch|iwr|invoke-webrequest)\b[^\n|]*\|\s*(?:sudo\s+)?(?:ba|z|k|c|da|fi)?sh\b)"
)
_HARDCODED_SECRET_RE = re.compile(
    r"(?:sk-live-[A-Za-z0-9]{12,}|ghp_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]{10,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)"
)


class StarterKitError(ValueError):
    """Typed refusal raised when building, validating, or writing a starter kit fails."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def verify_no_unsafe_content(text: str, path_label: str = "<text>") -> None:
    """Refuse secrets, instruction-steering phrases, and em/en dashes."""
    if not isinstance(text, str):
        raise StarterKitError("starter_kit_text_invalid", f"{path_label}: expected string")
    if "\u2014" in text or "\u2013" in text:
        raise StarterKitError("starter_kit_forbidden_dash", f"{path_label}: contains em dash or en dash")
    if _STEERING_RE.search(text):
        raise StarterKitError("starter_kit_steering_refused", f"{path_label}: contains instruction-steering text")
    if _HARDCODED_SECRET_RE.search(text):
        raise StarterKitError("starter_kit_secret_refused", f"{path_label}: contains secret-shaped literal")
    for pattern in default_secret_patterns():
        if re.search(pattern, text):
            raise StarterKitError("starter_kit_secret_refused", f"{path_label}: matched secret pattern")


def _resolve_harnesses(harness: str) -> tuple[str, ...]:
    if not isinstance(harness, str) or harness not in HARNESS_CHOICES:
        raise StarterKitError("starter_kit_harness_invalid", f"expected one of {HARNESS_CHOICES}, got {harness!r}")
    if harness == "all":
        return SUPPORTED_HARNESSES
    return (harness,)


def _rules_markdown(spec: StarterKitSpec) -> list[str]:
    lines = ["## Post-cutoff anti-drift rules", ""]
    for rule in spec.post_cutoff_rules:
        lines.extend(
            [
                f"### Rule `{rule['rule_id']}`",
                f"- Do not write: `{rule['wrong_pattern']}`",
                f"- Write instead: `{rule['correct_pattern']}`",
                f"- Reason: {rule['rationale']}",
                "",
            ]
        )
    return lines


def _render_skill_markdown(spec: StarterKitSpec, harness_name: str) -> bytes:
    lines = [
        "---",
        f"name: {spec.kit_id}",
        f"description: {json.dumps(spec.description)}",
        "---",
        "",
        f"# {spec.title}",
        "",
        f"Target harness: `{harness_name}`.",
        f"Domain: `{spec.domain}`.",
        "",
        "## Outcome and scope",
        "",
        spec.description,
        "This starter kit grants no execution, network, or spending authority. Existing host permissions govern all actions.",
        "",
        *_rules_markdown(spec),
        "## Linked AgentFeeds reading profile",
        "",
        f"- Profile configuration: `{FEED_PROFILE_PATH}`",
        f"- Reading guide: `{FEED_READING_PATH}`",
        f"- Curated collections: {', '.join(f'`{cid}`' for cid in spec.feed_collections)}",
        "",
        "## Deterministic verification",
        "",
        "The bundled verifier checks its demonstration fixtures and linked feed bytes, not your finished task.",
        "Run the task's own tests separately. From the kit root, run:",
        "```bash",
        "python3 verify_kit.py",
        "```",
        "",
    ]
    text = "\n".join(lines)
    verify_no_unsafe_content(text, f"SKILL.md:{spec.kit_id}:{harness_name}")
    return text.encode("utf-8")


def _render_claude_md(spec: StarterKitSpec) -> bytes:
    lines = [
        f"# {spec.title} (Claude Code instructions)",
        "",
        spec.description,
        "",
        "## Authority boundary",
        "",
        "This file supplies passive project rules only. It grants no credentials, network access, or automatic tool execution.",
        "Read `.claude/skills/" + spec.kit_id + "/SKILL.md` when working on tasks in this domain.",
        "Read `" + FEED_READING_PATH + "` and validate `" + FEED_PROFILE_PATH + "` before citing external benchmarks or release notes.",
        "",
        *_rules_markdown(spec),
        "## Verification",
        "",
        "From the kit root, run `python3 verify_kit.py` to check bundled fixtures, not task completion.",
        "",
    ]
    text = "\n".join(lines)
    verify_no_unsafe_content(text, f"CLAUDE.md:{spec.kit_id}")
    return text.encode("utf-8")


def _render_agents_md(spec: StarterKitSpec) -> bytes:
    lines = [
        f"# {spec.title} (Codex AGENTS.md instructions)",
        "",
        spec.description,
        "",
        "## Authority boundary",
        "",
        "This file supplies passive project rules only. It grants no credentials, network access, or automatic tool execution.",
        "Load `.agents/skills/" + spec.kit_id + "/SKILL.md` for task-specific rules and patterns.",
        "Consult `" + FEED_READING_PATH + "` and `" + FEED_PROFILE_PATH + "` for curated source references.",
        "",
        *_rules_markdown(spec),
        "## Verification",
        "",
        "From the kit root, run `python3 verify_kit.py` to check bundled fixtures, not task completion.",
        "",
    ]
    text = "\n".join(lines)
    verify_no_unsafe_content(text, f"AGENTS.md:{spec.kit_id}")
    return text.encode("utf-8")


def _render_mcp_json(spec: StarterKitSpec) -> bytes:
    document = {
        "mcpServers": {
            "baltor": {
                "type": "http",
                "url": "https://baltor.ai/mcp",
            },
        }
    }
    text = json.dumps(document, indent=2, sort_keys=True) + "\n"
    verify_no_unsafe_content(text, f".mcp.json:{spec.kit_id}")
    return text.encode("utf-8")


def _render_codex_config_toml(spec: StarterKitSpec) -> bytes:
    lines = [
        f"# Codex configuration for starter kit: {spec.kit_id}",
        "# Passive configuration only; credentials come from the host environment.",
        "",
        "[mcp_servers.baltor]",
        "url = \"https://baltor.ai/mcp\"",
        "",
        "bearer_token_env_var = \"BALTOR_SERVICE_TOKEN\"",
        "enabled = false",
        "",
    ]
    text = "\n".join(lines)
    verify_no_unsafe_content(text, f"config.toml:{spec.kit_id}")
    return text.encode("utf-8")


def _render_cursor_mdc(spec: StarterKitSpec) -> bytes:
    lines = [
        "---",
        f"description: {json.dumps(spec.description)}",
        "globs: [\"**/*\"]",
        "alwaysApply: false",
        "---",
        "",
        f"# {spec.title}",
        "",
        spec.description,
        "",
        *_rules_markdown(spec),
        "## Reading profile and verification",
        "",
        f"- Reading profile: `{FEED_PROFILE_PATH}` and `{FEED_READING_PATH}`",
        f"- Verifier command: `python3 {VERIFIER_FILENAME}`",
        "",
    ]
    text = "\n".join(lines)
    verify_no_unsafe_content(text, f".cursor/rules/{spec.kit_id}.mdc")
    return text.encode("utf-8")


def _render_opencode_json(spec: StarterKitSpec) -> bytes:
    document = {
        "$schema": "https://opencode.ai/config.json",
        "mcp": {
            "baltor": {
                "type": "remote",
                "url": "https://baltor.ai/mcp",
                "enabled": False,
            }
        },
        "instructions": [
            FEED_READING_PATH,
            f".opencode/skills/{spec.kit_id}/SKILL.md",
        ],
    }
    text = json.dumps(document, indent=2, sort_keys=True) + "\n"
    verify_no_unsafe_content(text, f"opencode.json:{spec.kit_id}")
    return text.encode("utf-8")


def _render_verifier_script(spec: StarterKitSpec, feed_profile_digest: str, feed_reading_digest: str) -> bytes:
    """Generate a self-contained deterministic Python verifier script for the kit."""
    script = f'''"""Deterministic verifier for starter kit {spec.kit_id}.

Runs positive sample validation, planted known-wrong control checks, and
linked AgentFeeds profile digest verification without network or model calls.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sys

KIT_ID = {spec.kit_id!r}
LINKED_LINTER = {spec.linked_linter!r}
FORBIDDEN_TOKENS = {list(spec.forbidden_tokens)!r}
REQUIRED_TOKENS = {list(spec.required_tokens)!r}
POSITIVE_SAMPLE = {spec.positive_sample!r}
NEGATIVE_SAMPLE = {spec.negative_sample!r}
EXPECTED_FEED_PROFILE_DIGEST = {feed_profile_digest!r}
EXPECTED_FEED_READING_DIGEST = {feed_reading_digest!r}


def check_sample(sample_text: str) -> dict:
    violations = []
    for token in FORBIDDEN_TOKENS:
        found = token in sample_text
        if token in ("export var ", "onready var "):
            found = re.search(r"(?<!@)\\b" + re.escape(token), sample_text) is not None
        if found:
            violations.append(f"forbidden_token:{{token}}")
    missing = []
    for token in REQUIRED_TOKENS:
        if token not in sample_text:
            missing.append(f"missing_required_token:{{token}}")
    return {{
        "passed": len(violations) == 0 and len(missing) == 0,
        "violations": violations,
        "missing": missing,
    }}


def verify(kit_root: Path | None = None) -> dict:
    pos = check_sample(POSITIVE_SAMPLE)
    neg = check_sample(NEGATIVE_SAMPLE)
    checks = [
        {{"name": "positive_sample_passes", "passed": bool(pos["passed"]), "details": pos}},
        {{"name": "known_wrong_negative_sample_refused", "passed": not bool(neg["passed"]), "details": neg}},
    ]
    if kit_root is not None:
        root = Path(kit_root)
        profile_path = root / "feeds" / "profile.json"
        reading_path = root / "feeds" / "READING.md"
        if profile_path.is_file() and reading_path.is_file():
            p_digest = hashlib.sha256(profile_path.read_bytes()).hexdigest()
            r_digest = hashlib.sha256(reading_path.read_bytes()).hexdigest()
            checks.append({{
                "name": "feed_profile_digest_matches",
                "passed": p_digest == EXPECTED_FEED_PROFILE_DIGEST,
                "expected": EXPECTED_FEED_PROFILE_DIGEST,
                "actual": p_digest,
            }})
            checks.append({{
                "name": "feed_reading_digest_matches",
                "passed": r_digest == EXPECTED_FEED_READING_DIGEST,
                "expected": EXPECTED_FEED_READING_DIGEST,
                "actual": r_digest,
            }})
        else:
            checks.append({{"name": "linked_feed_files_present", "passed": False}})
    overall = all(item["passed"] for item in checks)
    return {{
        "record_type": "starter_kit_verification/v1",
        "kit_id": KIT_ID,
        "linked_linter": LINKED_LINTER,
        "passed": overall,
        "checks": checks,
    }}


def main() -> int:
    here = Path(__file__).resolve().parent
    result = verify(here)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
'''
    verify_no_unsafe_content(script, f"verify_kit.py:{spec.kit_id}")
    return script.encode("utf-8")


def run_kit_verifier(kit_bundle: dict[str, Any]) -> dict[str, Any]:
    """Check exact first-party bytes before running the trusted fixture verifier.

    This is not a sandbox for arbitrary downloaded code or a task acceptance check.
    Changed kits must be reviewed through the existing component qualification path.
    """
    if not isinstance(kit_bundle, dict) or not isinstance(kit_bundle.get("record"), dict):
        raise StarterKitError("starter_kit_bundle_invalid")
    try:
        spec = get_starter_kit_spec(kit_bundle.get("kit_id"))
    except (KeyError, TypeError):
        raise StarterKitError("starter_kit_unknown") from None
    record = kit_bundle["record"]
    if not isinstance(record.get("feed_profile"), dict):
        raise StarterKitError("starter_kit_bundle_invalid")
    harnesses = record.get("target_harnesses")
    if harnesses == list(SUPPORTED_HARNESSES):
        harness = "all"
    elif isinstance(harnesses, list) and len(harnesses) == 1 and harnesses[0] in SUPPORTED_HARNESSES:
        harness = harnesses[0]
    else:
        raise StarterKitError("starter_kit_harness_invalid")
    canonical = _build_starter_kit(spec.kit_id, harness=harness, as_of=record.get("feed_profile", {}).get("as_of"))
    comparable = {key: value for key, value in record.items() if key != "verification"}
    if comparable != canonical["record"] or kit_bundle.get("file_bodies") != canonical["file_bodies"]:
        raise StarterKitError("starter_kit_noncanonical_bytes")
    verifier_bytes = canonical["file_bodies"][VERIFIER_FILENAME]
    namespace: dict[str, Any] = {"__name__": "__verifier__"}
    exec(compile(verifier_bytes.decode("utf-8"), VERIFIER_FILENAME, "exec"), namespace)
    report = namespace["verify"](None)

    linter_map = {
        "pydantic_v2_fastapi_drift": check_pydantic_v2_fastapi_drift,
        "nextjs_react19_tailwind4_drift": check_nextjs_react19_tailwind4_drift,
        "mcp_server_safety": check_mcp_server_safety,
        "llm_sdk_drift": check_llm_sdk_drift,
    }
    if spec.linked_linter in linter_map:
        linter_fn = linter_map[spec.linked_linter]
        pos_lint = linter_fn(spec.positive_sample, f"{spec.kit_id}_positive.py")
        neg_lint = linter_fn(spec.negative_sample, f"{spec.kit_id}_negative.py")
        report["checks"].append(
            {
                "name": "linked_drift_linter_positive_clean",
                "passed": bool(pos_lint["passed"]),
                "finding_count": pos_lint["finding_count"],
            }
        )
        report["checks"].append(
            {
                "name": "linked_drift_linter_negative_caught",
                "passed": not bool(neg_lint["passed"]) and neg_lint["finding_count"] > 0,
                "finding_count": neg_lint["finding_count"],
            }
        )
        report["passed"] = all(item["passed"] for item in report["checks"])
    return report


def _build_starter_kit(
    kit_id: str,
    *,
    harness: str = "all",
    as_of: str | None = None,
    custom_override_text: str | None = None,
) -> dict[str, Any]:
    """Build a multi-harness starter kit bundle with CataloguePackage digests and AgentFeeds profile."""
    try:
        spec = get_starter_kit_spec(kit_id)
    except KeyError as exc:
        raise StarterKitError("starter_kit_unknown", str(exc)) from None

    if custom_override_text is not None:
        verify_no_unsafe_content(custom_override_text, "custom_override_text")

    harnesses = _resolve_harnesses(harness)
    directory = current_directory()
    reference_date = as_of if as_of is not None else datetime.now(timezone.utc).date().isoformat()

    try:
        profile_req = ProfileRequest(
            agent_label=spec.agent_label,
            collection_ids=spec.feed_collections,
            topics=(),
            report_format="markdown",
            mode="both",
            max_items=20,
            max_bytes=32768,
            max_age_days=30,
            on_stale="refuse",
            on_partial="refuse",
            as_of=reference_date,
        )
        feed_profile, feed_bodies, _feed_native = compile_files(profile_req, directory)
    except FeedProfileError as exc:
        raise StarterKitError(f"starter_kit_feed_profile_failed:{exc.code}", exc.code) from None

    file_specs: list[tuple[str, bytes, str, str]] = []
    setup = (
        "# Starter kit preview\n\n"
        "Use Python 3.10 or newer for the bundled fixture verifier. This is guidance and source material, "
        "not an installed application or a complete project. Install your chosen harness and its model access separately.\n\n"
        "Review files in this fresh folder before copying anything into an existing project. Never overwrite "
        "existing instructions, skills or configuration without comparing them.\n\n"
        "Codex reads .agents/skills and trusted-project .codex/config.toml. OpenCode reads opencode.json "
        "and .opencode/skills. Their optional Baltor connections start disabled. Enable a connection only "
        "after configuring your own account access. Claude Code's .mcp.json uses its interactive authorization. "
        "No verifier is registered as an MCP server.\n\n"
        "Run python3 verify_kit.py from this folder. A pass checks the bundled examples and feed digests, "
        "not your project or current provider availability. The feed files declare sources; they are not ingested news. "
        "Keep model choices, budgets and effect permissions with the host.\n\n"
        "Static drift findings are suggestions for the versions named in each kit, not universal migration requirements. "
        "Validate each suggestion against your installed dependency and official documentation.\n"
    ).encode("utf-8")
    file_specs.append(("README.md", setup, "text/markdown", "other"))
    file_specs.append(("LICENSE", (Path(__file__).resolve().parents[2] / "LICENSE").read_bytes(), "text/plain", "other"))

    feed_profile_bytes = feed_bodies["profile.json"]
    feed_reading_bytes = feed_bodies["READING.md"]
    verify_no_unsafe_content(feed_profile_bytes.decode("utf-8"), FEED_PROFILE_PATH)
    verify_no_unsafe_content(feed_reading_bytes.decode("utf-8"), FEED_READING_PATH)

    file_specs.append((FEED_PROFILE_PATH, feed_profile_bytes, "application/json", "configuration"))
    file_specs.append((FEED_READING_PATH, feed_reading_bytes, "text/markdown", "instruction_file"))

    if "claude_code" in harnesses:
        file_specs.append(
            (
                f".claude/skills/{spec.kit_id}/SKILL.md",
                _render_skill_markdown(spec, "claude_code"),
                "text/markdown",
                "skill_definition",
            )
        )
        file_specs.append(("CLAUDE.md", _render_claude_md(spec), "text/markdown", "instruction_file"))
        file_specs.append((".mcp.json", _render_mcp_json(spec), "application/json", "protocol_server_configuration"))

    if "codex" in harnesses:
        file_specs.append(
            (
                f".agents/skills/{spec.kit_id}/SKILL.md",
                _render_skill_markdown(spec, "codex"),
                "text/markdown",
                "skill_definition",
            )
        )
        file_specs.append(("AGENTS.md", _render_agents_md(spec), "text/markdown", "instruction_file"))
        file_specs.append((".codex/config.toml", _render_codex_config_toml(spec), "application/toml", "configuration"))

    if "cursor" in harnesses:
        file_specs.append(
            (
                f".cursor/rules/{spec.kit_id}.mdc",
                _render_cursor_mdc(spec),
                "text/markdown",
                "instruction_file",
            )
        )

    if "opencode" in harnesses:
        file_specs.append(("opencode.json", _render_opencode_json(spec), "application/json", "configuration"))
        file_specs.append((f".opencode/skills/{spec.kit_id}/SKILL.md", _render_skill_markdown(spec, "opencode"),
                           "text/markdown", "skill_definition"))

    verifier_bytes = _render_verifier_script(
        spec,
        sha256_hex(feed_profile_bytes),
        sha256_hex(feed_reading_bytes),
    )
    file_specs.append((VERIFIER_FILENAME, verifier_bytes, "text/x-python", "skill_script"))

    package_entries: list[CataloguePackageFile] = []
    file_bodies: dict[str, bytes] = {}
    for rel_path, data_bytes, mtype, role in file_specs:
        placement_path(rel_path)
        file_bodies[rel_path] = data_bytes
        package_entries.append(
            CataloguePackageFile(
                path=rel_path,
                digest=sha256_hex(data_bytes),
                size_bytes=len(data_bytes),
                media_type=mtype,
                role=role,
            )
        )

    catalogue_package = CataloguePackage(tuple(package_entries), PACKAGE_BODY)

    record = {
        "record_type": STARTER_KIT_RECORD_TYPE,
        "kit_id": spec.kit_id,
        "title": spec.title,
        "domain": spec.domain,
        "description": spec.description,
        "target_harnesses": list(harnesses),
        "linked_linter": spec.linked_linter,
        "post_cutoff_rules": [dict(rule) for rule in spec.post_cutoff_rules],
        "feed_profile": {
            "profile_digest": feed_profile["profile_digest"],
            "collections": list(spec.feed_collections),
            "as_of": reference_date,
            "files": [FEED_PROFILE_PATH, FEED_READING_PATH],
        },
        "verifier_script": VERIFIER_FILENAME,
        "catalogue_package": catalogue_package.to_dict(),
        "package_digest": catalogue_package.package_digest,
        "files": [entry.to_dict() for entry in catalogue_package.files],
        "payload_files": len(catalogue_package.files),
        "payload_bytes": sum(entry.size_bytes for entry in catalogue_package.files),
        "approved": False,
        "published": False,
        "effects_granted": [],
        "automatic_tool_execution": False,
        "scheduled": False,
        "hosted_settings_saved": False,
    }

    bundle = {
        "record": record,
        "kit_id": spec.kit_id,
        "catalogue_package": catalogue_package,
        "file_bodies": file_bodies,
    }
    return bundle


def build_starter_kit(kit_id: str, *, harness: str = "all", as_of: str | None = None,
                      custom_override_text: str | None = None) -> dict[str, Any]:
    """Build a local candidate; checks never approve publication or task completion."""
    if custom_override_text is not None:
        raise StarterKitError("starter_kit_custom_override_not_supported")
    bundle = _build_starter_kit(kit_id, harness=harness, as_of=as_of)
    verification = run_kit_verifier(bundle)
    if not verification["passed"]:
        raise StarterKitError("starter_kit_self_verification_failed", kit_id)
    bundle["record"]["verification"] = verification
    return bundle


def _open_directory_nofollow(path: Path) -> int:
    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY") or os.open not in os.supports_dir_fd:
        raise StarterKitError("starter_kit_posix_filesystem_required")
    raw_str = str(path)
    if ".." in Path(raw_str).parts:
        raise StarterKitError("starter_kit_path_traversal", raw_str)
    absolute = Path(raw_str).absolute()
    if ".." in absolute.parts:
        raise StarterKitError("starter_kit_path_traversal", str(absolute))
    descriptor = os.open(absolute.anchor, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for segment in absolute.parts[1:]:
            next_descriptor = os.open(segment, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = next_descriptor
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _ensure_subdir_nofollow(root_fd: int, parts: list[str]) -> int:
    current_fd = os.dup(root_fd)
    try:
        for segment in parts:
            if segment in ("", ".", "..") or segment.casefold() == ".git":
                raise StarterKitError("starter_kit_path_traversal", segment)
            try:
                os.mkdir(segment, mode=0o700, dir_fd=current_fd)
            except FileExistsError:
                pass
            next_fd = os.open(segment, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=current_fd)
            os.close(current_fd)
            current_fd = next_fd
        return current_fd
    except BaseException:
        os.close(current_fd)
        raise


def write_starter_kit(
    output_root: Path | str,
    folder_name: str,
    kit_bundle: dict[str, Any],
    *,
    authorized: bool = False,
) -> Path:
    """Confined write of a starter kit bundle into a new child folder under output_root."""
    if authorized is not True:
        raise PermissionError("local_write_grant_required")
    if not isinstance(folder_name, str) or not _FOLDER_NAME_RE.fullmatch(folder_name) or ".." in folder_name:
        raise StarterKitError("starter_kit_folder_name_invalid", str(folder_name))

    if not isinstance(kit_bundle, dict) or "record" not in kit_bundle or "file_bodies" not in kit_bundle:
        raise StarterKitError("starter_kit_bundle_invalid")
    record = kit_bundle["record"]
    if (
        record.get("record_type") != STARTER_KIT_RECORD_TYPE
        or record.get("approved") is not False
        or record.get("published") is not False
        or record.get("effects_granted") != []
    ):
        raise StarterKitError("starter_kit_authority_invalid")
    run_kit_verifier(kit_bundle)

    file_bodies: dict[str, bytes] = dict(kit_bundle["file_bodies"])
    for rel_path, body in file_bodies.items():
        placement_path(rel_path)
        if not isinstance(body, bytes):
            raise StarterKitError("starter_kit_file_bytes_invalid", rel_path)
        verify_no_unsafe_content(body.decode("utf-8"), rel_path)

    manifest_bytes = (json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")

    root_path = Path(output_root)
    if ".." in root_path.parts:
        raise StarterKitError("starter_kit_path_traversal", str(output_root))
    abs_root = root_path.absolute()
    if abs_root in (Path(abs_root.anchor), Path.home()):
        raise StarterKitError("starter_kit_explicit_root_required", str(abs_root))

    parent_fd = _open_directory_nofollow(abs_root)
    try:
        os.mkdir(folder_name, mode=0o700, dir_fd=parent_fd)
        kit_fd = os.open(folder_name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd)
        try:
            all_writes = {**file_bodies, MANIFEST_FILENAME: manifest_bytes}
            for rel_path, body in sorted(all_writes.items()):
                parts = rel_path.split("/")
                dir_parts, filename = parts[:-1], parts[-1]
                target_dir_fd = _ensure_subdir_nofollow(kit_fd, dir_parts) if dir_parts else os.dup(kit_fd)
                try:
                    fd = os.open(
                        filename,
                        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                        0o600,
                        dir_fd=target_dir_fd,
                    )
                    with os.fdopen(fd, "wb") as stream:
                        stream.write(body)
                        stream.flush()
                        os.fsync(stream.fileno())
                    os.fsync(target_dir_fd)
                finally:
                    os.close(target_dir_fd)
            os.fsync(kit_fd)
        finally:
            os.close(kit_fd)
        os.fsync(parent_fd)
    finally:
        os.close(parent_fd)
    return abs_root / folder_name


def _read_regular_file_nofollow(root_fd: int, rel_path: str, max_bytes: int = 1024 * 1024) -> bytes:
    placement_path(rel_path)
    parts = rel_path.split("/")
    current_fd = os.dup(root_fd)
    try:
        for segment in parts[:-1]:
            next_fd = os.open(segment, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=current_fd)
            os.close(current_fd)
            current_fd = next_fd
        file_fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_NONBLOCK", 0), dir_fd=current_fd)
        with os.fdopen(file_fd, "rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise StarterKitError("starter_kit_file_not_regular", rel_path)
            data = stream.read(max_bytes + 1)
            if len(data) > max_bytes:
                raise StarterKitError("starter_kit_file_too_large", rel_path)
            return data
    finally:
        os.close(current_fd)


def _check_exact_inventory(root_fd: int, expected_files: set[str]) -> None:
    """Check the fresh kit's exact tree without opening unlisted entries."""
    expected_directories: set[str] = set()
    for path in expected_files:
        parts = path.split("/")
        expected_directories.update("/".join(parts[:index]) for index in range(1, len(parts)))
    seen_files: set[str] = set()
    seen_directories: set[str] = set()
    ceiling = len(expected_files) + len(expected_directories)
    entries_seen = 0

    def inspect(directory_fd: int, prefix: str = "") -> None:
        nonlocal entries_seen
        with os.scandir(directory_fd) as entries:
            for entry in entries:
                entries_seen += 1
                if entries_seen > ceiling:
                    raise StarterKitError("starter_kit_inventory_limit")
                relative = prefix + entry.name
                if relative in expected_files:
                    info = entry.stat(follow_symlinks=False)
                    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                        raise StarterKitError("starter_kit_inventory_nonregular")
                    seen_files.add(relative)
                elif relative in expected_directories:
                    if not entry.is_dir(follow_symlinks=False):
                        raise StarterKitError("starter_kit_inventory_nondirectory")
                    child_fd = os.open(entry.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                       dir_fd=directory_fd)
                    try:
                        inspect(child_fd, relative + "/")
                    finally:
                        os.close(child_fd)
                    seen_directories.add(relative)
                else:
                    raise StarterKitError("starter_kit_unexpected_entry")

    inspect(root_fd)
    if seen_files != expected_files or seen_directories != expected_directories:
        raise StarterKitError("starter_kit_inventory_incomplete")


def check_starter_kit_folder(folder: Path | str, *, as_of: str | None = None) -> dict[str, Any]:
    """Validate an existing starter kit folder on disk without following symbolic links."""
    folder_path = Path(folder)
    kit_fd = _open_directory_nofollow(folder_path)
    try:
        try:
            manifest_raw = _read_regular_file_nofollow(kit_fd, MANIFEST_FILENAME)
            manifest = json.loads(manifest_raw.decode("utf-8"))
        except (OSError, ValueError) as exc:
            raise StarterKitError("starter_kit_manifest_invalid", str(exc)) from None

        if (
            not isinstance(manifest, dict)
            or manifest.get("record_type") != STARTER_KIT_RECORD_TYPE
            or manifest.get("approved") is not False
            or manifest.get("published") is not False
            or manifest.get("effects_granted") != []
        ):
            raise StarterKitError("starter_kit_manifest_authority_invalid")
        if not isinstance(manifest.get("feed_profile"), dict):
            raise StarterKitError("starter_kit_manifest_invalid")

        harnesses = manifest.get("target_harnesses")
        harness = "all" if harnesses == list(SUPPORTED_HARNESSES) else (
            harnesses[0] if isinstance(harnesses, list) and len(harnesses) == 1 else "")
        canonical = _build_starter_kit(manifest.get("kit_id"), harness=harness,
                                      as_of=manifest.get("feed_profile", {}).get("as_of"))
        if {k: v for k, v in manifest.items() if k != "verification"} != canonical["record"]:
            raise StarterKitError("starter_kit_noncanonical_manifest")
        _check_exact_inventory(kit_fd, set(canonical["file_bodies"]) | {MANIFEST_FILENAME})

        files_list = manifest.get("files")
        if not isinstance(files_list, list) or not files_list:
            raise StarterKitError("starter_kit_manifest_files_invalid")

        loaded_bodies: dict[str, bytes] = {}
        for entry in files_list:
            rel_path = entry.get("path")
            expected_digest = entry.get("digest")
            expected_size = entry.get("size_bytes")
            body = _read_regular_file_nofollow(kit_fd, rel_path)
            if len(body) != expected_size or sha256_hex(body) != expected_digest:
                raise StarterKitError("starter_kit_file_digest_mismatch", str(rel_path))
            verify_no_unsafe_content(body.decode("utf-8"), rel_path)
            loaded_bodies[rel_path] = body

        package = CataloguePackage.from_dict(manifest["catalogue_package"])
        if package.package_digest != manifest.get("package_digest"):
            raise StarterKitError("starter_kit_package_digest_mismatch")

        profile_doc = read_profile(loaded_bodies[FEED_PROFILE_PATH])
        ref_date = as_of or datetime.now(timezone.utc).date().isoformat()
        feed_report = validate_feed_profile(profile_doc, as_of=ref_date)

        verifier_report = run_kit_verifier(
            {
                "kit_id": manifest["kit_id"],
                "record": manifest,
                "file_bodies": loaded_bodies,
            }
        )
        if not verifier_report["passed"]:
            raise StarterKitError("starter_kit_verification_failed", manifest["kit_id"])

        return {
            "record_type": "agent_foundry_starter_kit_check/v1",
            "status": "validated_starter_kit",
            "kit_id": manifest["kit_id"],
            "package_digest": manifest["package_digest"],
            "files_checked": len(loaded_bodies),
            "feed_profile_status": feed_report["status"],
            "verification": verifier_report,
            "approved": False,
            "published": False,
            "effects_granted": [],
        }
    finally:
        os.close(kit_fd)


__all__ = [
    "MANIFEST_FILENAME",
    "VERIFIER_FILENAME",
    "FEED_PROFILE_PATH",
    "FEED_READING_PATH",
    "StarterKitError",
    "verify_no_unsafe_content",
    "build_starter_kit",
    "run_kit_verifier",
    "write_starter_kit",
    "check_starter_kit_folder",
]
