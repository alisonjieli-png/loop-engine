"""Deterministic post-cutoff drift linters for coding harnesses.

Each linter inspects source text using Python AST and regular-expression
rules without network calls or model calls. Every linter returns a typed
post_cutoff_drift_report/v1 dictionary with line numbers, rule identifiers,
and exact replacement fixes.
"""
from __future__ import annotations

import ast
import re
from typing import Any

REPORT_RECORD_TYPE = "post_cutoff_drift_report/v1"
FINDING_RECORD_TYPE = "post_cutoff_drift_finding/v1"

RETIRED_MODEL_REPLACEMENTS: dict[str, str] = {
    "gpt-3.5-turbo": "gpt-5-mini",
    "gpt-3.5-turbo-16k": "gpt-5-mini",
    "gpt-4-0613": "gpt-5",
    "gpt-4-32k": "gpt-5",
    "text-davinci-003": "gpt-5-mini",
    "text-davinci-002": "gpt-5-mini",
    "code-davinci-002": "gpt-5-mini",
    "claude-2.1": "claude-sonnet-4-5",
    "claude-2.0": "claude-sonnet-4-5",
    "claude-instant-1": "claude-haiku-4-5",
    "claude-instant-1.2": "claude-haiku-4-5",
    "gemini-pro": "gemini-2.5-pro",
    "gemini-pro-vision": "gemini-2.5-pro",
    "gemini-1.0-pro": "gemini-2.5-pro",
}


def _make_finding(
    rule_id: str,
    line: int,
    matched_text: str,
    message: str,
    replacement: str,
    *,
    column: int = 1,
    severity: str = "error",
) -> dict[str, Any]:
    return {
        "record_type": FINDING_RECORD_TYPE,
        "rule_id": rule_id,
        "severity": severity,
        "line": int(max(1, line)),
        "column": int(max(1, column)),
        "matched_text": _redact_finding_text(matched_text.strip())[:200],
        "message": _redact_finding_text(message),
        "replacement": _redact_finding_text(replacement),
    }


def _make_report(linter: str, filename: str, findings: list[dict[str, Any]]) -> dict[str, Any]:
    ordered = sorted(findings, key=lambda item: (item["line"], item["column"], item["rule_id"]))
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    for item in ordered:
        key = (item["rule_id"], item["line"])
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    return {
        "record_type": REPORT_RECORD_TYPE,
        "linter": linter,
        "filename": str(filename),
        "passed": len(deduped) == 0,
        "finding_count": len(deduped),
        "findings": deduped,
    }


def check_llm_sdk_drift(source_text: str, filename: str = "<memory>") -> dict[str, Any]:
    """Check Python or TypeScript source text for post-cutoff LLM SDK drift.

    Catches:
    - Deprecated OpenAI openai.ChatCompletion.create and openai.Completion.create
    - Deprecated OpenAI client.beta.assistants API
    - Legacy Anthropic client.completions.create API
    - Deprecated google.generativeai import and configure calls
    - Retired model identifiers (gpt-3.5-turbo, claude-2.1, gemini-pro, text-davinci-003)
    """
    if not isinstance(source_text, str):
        raise TypeError("source_text must be a string")
    findings: list[dict[str, Any]] = []
    lines = source_text.splitlines()

    for idx, raw_line in enumerate(lines, start=1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("//"):
            continue

        match_chat = re.search(r"\bopenai\.(?:ChatCompletion|Completion)\.create\b", raw_line)
        if match_chat:
            findings.append(
                _make_finding(
                    "llm_sdk.openai_chat_completion_legacy",
                    idx,
                    match_chat.group(0),
                    "Legacy OpenAI ChatCompletion.create/Completion.create was removed in openai v1+.",
                    "from openai import OpenAI; client = OpenAI(); client.responses.create(model=\"gpt-5\", input=...)",
                    column=match_chat.start() + 1,
                )
            )

        match_assistants = re.search(r"\b(?:client|openai)\.beta\.assistants\b", raw_line)
        if match_assistants:
            findings.append(
                _make_finding(
                    "llm_sdk.openai_beta_assistants_deprecated",
                    idx,
                    match_assistants.group(0),
                    "OpenAI beta Assistants API is deprecated in favor of the Responses API.",
                    "client.responses.create(model=\"gpt-5\", tools=[...], input=...)",
                    column=match_assistants.start() + 1,
                )
            )

        match_anthropic = re.search(r"\b(?:client|anthropic)\.completions\.create\b", raw_line)
        if match_anthropic:
            findings.append(
                _make_finding(
                    "llm_sdk.anthropic_completions_legacy",
                    idx,
                    match_anthropic.group(0),
                    "Legacy Anthropic Text Completions API (completions.create) is retired.",
                    "client.messages.create(model=\"claude-sonnet-4-5\", max_tokens=1024, messages=[...])",
                    column=match_anthropic.start() + 1,
                )
            )

        match_google = re.search(
            r"(?:\bimport\s+google\.generativeai\b|\bfrom\s+google\.generativeai\b|\bfrom\s+google\s+import\s+generativeai\b|\bgenai\.GenerativeModel\b|\bgenai\.configure\b)",
            raw_line,
        )
        if match_google:
            findings.append(
                _make_finding(
                    "llm_sdk.google_generativeai_deprecated",
                    idx,
                    match_google.group(0),
                    "The google-generativeai package is deprecated; use the unified google-genai SDK.",
                    "from google import genai; client = genai.Client(); client.models.generate_content(model=\"gemini-2.5-pro\", contents=...)",
                    column=match_google.start() + 1,
                )
            )

        for retired_model, replacement_model in RETIRED_MODEL_REPLACEMENTS.items():
            pattern = re.compile(r"['\"]" + re.escape(retired_model) + r"['\"]")
            match_model = pattern.search(raw_line)
            if match_model:
                findings.append(
                    _make_finding(
                        "llm_sdk.retired_model_id",
                        idx,
                        match_model.group(0),
                        f"Historical model identifier '{retired_model}' requires a current availability check; this linter makes no provider call.",
                        "Select an available model for the existing route and budget; do not automatically replace it.",
                        column=match_model.start() + 1,
                    )
                )

    return _make_report("llm_sdk_drift", filename, findings)


def check_pydantic_v2_fastapi_drift(source_text: str, filename: str = "<memory>") -> dict[str, Any]:
    """Check Python source text for Pydantic v1 and deprecated FastAPI lifecycle drift.

    Catches:
    - Pydantic v1 @validator and @root_validator decorators
    - Pydantic v1 .dict(), .json(), .parse_obj(), and .from_orm() methods
    - Pydantic v1 class Config: and orm_mode = True
    - FastAPI @app.on_event("startup") and @app.on_event("shutdown")
    """
    if not isinstance(source_text, str):
        raise TypeError("source_text must be a string")
    findings: list[dict[str, Any]] = []
    lines = source_text.splitlines()

    for idx, raw_line in enumerate(lines, start=1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        match_val = re.search(r"@(?:pydantic\.)?validator\s*\(", raw_line)
        if match_val:
            findings.append(
                _make_finding(
                    "pydantic_v2.validator_decorator",
                    idx,
                    match_val.group(0),
                    "Pydantic v1 @validator is deprecated; use @field_validator in Pydantic v2.",
                    "@field_validator(\"field_name\", mode=\"after\")\n@classmethod",
                    column=match_val.start() + 1,
                )
            )

        match_root_val = re.search(r"@(?:pydantic\.)?root_validator\b", raw_line)
        if match_root_val:
            findings.append(
                _make_finding(
                    "pydantic_v2.root_validator_decorator",
                    idx,
                    match_root_val.group(0),
                    "Pydantic v1 @root_validator is deprecated; use @model_validator in Pydantic v2.",
                    "@model_validator(mode=\"after\")",
                    column=match_root_val.start() + 1,
                )
            )

        match_dict = re.search(r"\b([A-Za-z_][A-Za-z0-9_]*)\.dict\s*\(", raw_line)
        if match_dict:
            findings.append(
                _make_finding(
                    "pydantic_v2.model_dict_method",
                    idx,
                    match_dict.group(0),
                    "Pydantic v1 .dict() is deprecated; use .model_dump() in Pydantic v2.",
                    f"{match_dict.group(1)}.model_dump()",
                    column=match_dict.start() + 1,
                )
            )

        match_json = re.search(r"\b([A-Za-z_][A-Za-z0-9_]*)\.json\s*\(([^)]*)\)", raw_line)
        if match_json:
            receiver = match_json.group(1)
            args_text = match_json.group(2).strip()
            if receiver.lower() not in ("response", "resp", "res", "r", "request", "req", "httpx", "requests") or args_text:
                findings.append(
                    _make_finding(
                        "pydantic_v2.model_json_method",
                        idx,
                        f"{receiver}.json(...)",
                        "Pydantic v1 .json() on BaseModel is deprecated; use .model_dump_json() in Pydantic v2.",
                        f"{receiver}.model_dump_json(...)",
                        column=match_json.start() + 1,
                    )
                )

        match_parse_obj = re.search(r"\b([A-Za-z_][A-Za-z0-9_]*)\.parse_obj\s*\(", raw_line)
        if match_parse_obj:
            findings.append(
                _make_finding(
                    "pydantic_v2.parse_obj_method",
                    idx,
                    match_parse_obj.group(0),
                    "Pydantic v1 .parse_obj() is deprecated; use .model_validate() in Pydantic v2.",
                    f"{match_parse_obj.group(1)}.model_validate(...)",
                    column=match_parse_obj.start() + 1,
                )
            )

        match_from_orm = re.search(r"\b([A-Za-z_][A-Za-z0-9_]*)\.from_orm\s*\(", raw_line)
        if match_from_orm:
            findings.append(
                _make_finding(
                    "pydantic_v2.from_orm_method",
                    idx,
                    match_from_orm.group(0),
                    "Pydantic v1 .from_orm() is removed in v2; use .model_validate(obj, from_attributes=True).",
                    f"{match_from_orm.group(1)}.model_validate(..., from_attributes=True)",
                    column=match_from_orm.start() + 1,
                )
            )

        match_config = re.search(r"\bclass\s+Config\s*:", raw_line)
        if match_config:
            findings.append(
                _make_finding(
                    "pydantic_v2.class_config",
                    idx,
                    match_config.group(0),
                    "Pydantic v1 inner 'class Config:' is deprecated; use model_config = ConfigDict(...).",
                    "model_config = ConfigDict(...)",
                    column=match_config.start() + 1,
                )
            )

        match_orm = re.search(r"\borm_mode\s*=\s*True\b", raw_line)
        if match_orm:
            findings.append(
                _make_finding(
                    "pydantic_v2.orm_mode_setting",
                    idx,
                    match_orm.group(0),
                    "Pydantic v1 orm_mode = True is replaced by from_attributes=True in ConfigDict.",
                    "model_config = ConfigDict(from_attributes=True)",
                    column=match_orm.start() + 1,
                )
            )

        match_event = re.search(r"@([A-Za-z_][A-Za-z0-9_]*)\.on_event\s*\(\s*['\"](startup|shutdown)['\"]\s*\)", raw_line)
        if match_event:
            findings.append(
                _make_finding(
                    "fastapi.on_event_deprecated",
                    idx,
                    match_event.group(0),
                    f"FastAPI @{match_event.group(1)}.on_event(\"{match_event.group(2)}\") is deprecated; use a lifespan async context manager.",
                    "@asynccontextmanager\nasync def lifespan(app: FastAPI):\n    yield\napp = FastAPI(lifespan=lifespan)",
                    column=match_event.start() + 1,
                )
            )

    return _make_report("pydantic_v2_fastapi_drift", filename, findings)


def check_nextjs_react19_tailwind4_drift(source_text: str, filename: str = "<memory>") -> dict[str, Any]:
    """Check Next.js 15, React 19, and Tailwind CSS v4 source text for post-cutoff drift.

    Catches:
    - Next.js 15 synchronous cookies().get / set / delete / has calls without await
    - Next.js 15 synchronous headers().get / has / entries calls without await
    - React 19 deprecated useFormState hook (replaced by useActionState)
    - Tailwind CSS v3 @tailwind base / components / utilities directives (replaced by @import "tailwindcss";)
    """
    if not isinstance(source_text, str):
        raise TypeError("source_text must be a string")
    findings: list[dict[str, Any]] = []
    lines = source_text.splitlines()

    for idx, raw_line in enumerate(lines, start=1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("//"):
            continue

        match_cookies = re.search(r"(?<!await\s)\bcookies\s*\(\s*\)\s*\.\s*(get|getAll|set|delete|has)\b", raw_line)
        if match_cookies:
            method = match_cookies.group(1)
            findings.append(
                _make_finding(
                    "nextjs15.sync_cookies_access",
                    idx,
                    match_cookies.group(0),
                    "Next.js 15+ cookies() is an async Dynamic API and must be awaited before calling ." + method + "().",
                    f"(await cookies()).{method}(...)",
                    column=match_cookies.start() + 1,
                )
            )

        match_headers = re.search(r"(?<!await\s)\bheaders\s*\(\s*\)\s*\.\s*(get|has|entries|forEach|keys|values)\b", raw_line)
        if match_headers:
            method = match_headers.group(1)
            findings.append(
                _make_finding(
                    "nextjs15.sync_headers_access",
                    idx,
                    match_headers.group(0),
                    "Next.js 15+ headers() is an async Dynamic API and must be awaited before calling ." + method + "().",
                    f"(await headers()).{method}(...)",
                    column=match_headers.start() + 1,
                )
            )

        match_form_state = re.search(r"\buseFormState\b", raw_line)
        if match_form_state:
            findings.append(
                _make_finding(
                    "react19.use_form_state_deprecated",
                    idx,
                    match_form_state.group(0),
                    "React 19 replaced react-dom useFormState with useActionState imported from 'react'.",
                    "import { useActionState } from \"react\"; const [state, formAction, isPending] = useActionState(action, initialState);",
                    column=match_form_state.start() + 1,
                )
            )

        match_tailwind = re.search(r"@tailwind\s+(?:base|components|utilities)\s*;", raw_line)
        if match_tailwind:
            findings.append(
                _make_finding(
                    "tailwind4.legacy_tailwind_directives",
                    idx,
                    match_tailwind.group(0),
                    "Tailwind CSS v4 replaces @tailwind base/components/utilities directives with a single CSS import.",
                    "@import \"tailwindcss\";",
                    column=match_tailwind.start() + 1,
                )
            )

    return _make_report("nextjs_react19_tailwind4_drift", filename, findings)


_SECRET_ASSIGNMENT_RE = re.compile(
    r"""(?ix)
    (?:
        \b(?:api[_-]?key|secret[_-]?key|access[_-]?token|auth[_-]?token|bearer[_-]?token|client[_-]?secret|password)\s*=\s*['"][A-Za-z0-9_\-./+=]{8,}['"]
        |
        ['"]Bearer\s+[A-Za-z0-9_\-.]{10,}['"]
        |
        ['"](?:sk-[A-Za-z0-9_\-]{12,}|ghp_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9\-]{10,})['"]
    )
    """
)


def _redact_finding_text(text: str) -> str:
    """Never repeat recognized credentials through a non-secret finding field."""
    return _SECRET_ASSIGNMENT_RE.sub("[redacted credential]", text)


def _function_has_input_validation(func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Return True if a tool handler function validates its parameters via types and bounds checks."""
    args = [arg for arg in func_node.args.args if arg.arg not in ("self", "cls", "ctx", "context")]
    if not args:
        return True
    if any(arg.annotation is None for arg in args):
        return False

    for node in ast.walk(func_node):
        if isinstance(node, ast.Raise):
            return True
        if isinstance(node, ast.Compare):
            return True
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in (
                "isinstance",
                "len",
                "min",
                "max",
                "Field",
                "validate_call",
            ):
                return True
            if isinstance(node.func, ast.Attribute) and node.func.attr in (
                "model_validate",
                "fullmatch",
                "match",
                "validate",
                "resolve",
            ):
                return True
    return False


def _is_mcp_tool_function(func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Return True if the function is decorated as an MCP tool or named as a tool handler."""
    for dec in func_node.decorator_list:
        dec_text = ast.unparse(dec) if hasattr(ast, "unparse") else ""
        if "tool" in dec_text.lower():
            return True
    if func_node.name.startswith(("tool_", "handle_", "call_tool", "run_")):
        return True
    return False


def check_mcp_server_safety(source_text: str, filename: str = "<memory>") -> dict[str, Any]:
    """Check MCP server code for stdio corruption, shell injection, secrets, and missing input bounds.

    Catches:
    - print(...) calls without file=sys.stderr that corrupt stdio JSON-RPC frames
    - subprocess calls with shell=True or os.system(...) in tool handlers
    - Hardcoded bearer tokens or API keys
    - Tool handler functions missing parameter type annotations or input bounds validation
    """
    if not isinstance(source_text, str):
        raise TypeError("source_text must be a string")
    findings: list[dict[str, Any]] = []
    lines = source_text.splitlines()

    for idx, raw_line in enumerate(lines, start=1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        secret_match = _SECRET_ASSIGNMENT_RE.search(raw_line)
        if secret_match and "os.environ" not in raw_line and "getenv" not in raw_line:
            findings.append(
                _make_finding(
                    "mcp_safety.hardcoded_secret",
                    idx,
                    "[redacted credential assignment]",
                    "Hardcoded API key or bearer token detected in MCP server source.",
                    "os.environ[\"SERVICE_API_KEY\"]",
                    column=secret_match.start() + 1,
                )
            )

        shell_match = re.search(r"\bshell\s*=\s*True\b|\bos\.system\s*\(", raw_line)
        if shell_match:
            findings.append(
                _make_finding(
                    "mcp_safety.subprocess_shell_true",
                    idx,
                    shell_match.group(0),
                    "Subprocess execution with shell=True or os.system exposes MCP tools to command injection.",
                    "subprocess.run([executable, arg1], shell=False, check=True, timeout=30, capture_output=True)",
                    column=shell_match.start() + 1,
                )
            )

    try:
        tree = ast.parse(source_text, filename=filename)
    except SyntaxError as exc:
        findings.append(_make_finding("mcp_safety.source_syntax_invalid", exc.lineno or 1,
                                      "[source omitted]", "Python syntax is invalid; tool checks are incomplete.",
                                      "Repair the source syntax, then run the linter again."))
        for idx, raw_line in enumerate(lines, start=1):
            print_match = re.search(r"\bprint\s*\(", raw_line)
            if print_match and "stderr" not in raw_line:
                findings.append(
                    _make_finding(
                        "mcp_safety.stdio_print_pollution",
                        idx,
                        print_match.group(0),
                        "Direct print() to stdout corrupts MCP stdio JSON-RPC framing.",
                        "print(..., file=sys.stderr)",
                        column=print_match.start() + 1,
                    )
                )
        return _make_report("mcp_server_safety", filename, findings)

    tool_functions: list[ast.FunctionDef | ast.AsyncFunctionDef] = []
    all_functions: list[ast.FunctionDef | ast.AsyncFunctionDef] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "print":
                has_stderr = any(
                    kw.arg == "file" and "stderr" in (ast.unparse(kw.value) if hasattr(ast, "unparse") else "")
                    for kw in node.keywords
                )
                if not has_stderr:
                    findings.append(
                        _make_finding(
                            "mcp_safety.stdio_print_pollution",
                            getattr(node, "lineno", 1),
                            "print(...)",
                            "Direct print() to stdout corrupts MCP stdio JSON-RPC framing.",
                            "print(..., file=sys.stderr)",
                            column=getattr(node, "col_offset", 0) + 1,
                        )
                    )
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            all_functions.append(node)
            if _is_mcp_tool_function(node):
                tool_functions.append(node)

    candidates = tool_functions if tool_functions else all_functions
    for func in candidates:
        if not _function_has_input_validation(func):
            findings.append(
                _make_finding(
                    "mcp_safety.missing_input_validation",
                    getattr(func, "lineno", 1),
                    f"def {func.name}(...)",
                    f"MCP tool handler '{func.name}' lacks explicit parameter type annotations or bounds validation.",
                    f"def {func.name}(param: str) -> dict:\n    if not isinstance(param, str) or not (1 <= len(param) <= 1024):\n        raise ValueError(\"invalid_input_bounds\")",
                    column=getattr(func, "col_offset", 0) + 1,
                )
            )

    return _make_report("mcp_server_safety", filename, findings)


def run_all_drift_linters(source_text: str, filename: str = "<memory>") -> dict[str, Any]:
    """Run all four post-cutoff drift linters and return an aggregate summary."""
    reports = {
        "llm_sdk_drift": check_llm_sdk_drift(source_text, filename),
        "pydantic_v2_fastapi_drift": check_pydantic_v2_fastapi_drift(source_text, filename),
        "nextjs_react19_tailwind4_drift": check_nextjs_react19_tailwind4_drift(source_text, filename),
        "mcp_server_safety": check_mcp_server_safety(source_text, filename),
    }
    findings = [finding for report in reports.values() for finding in report["findings"]]
    return {
        "record_type": REPORT_RECORD_TYPE,
        "linter": "all",
        "filename": str(filename),
        "passed": len(findings) == 0,
        "finding_count": len(findings),
        "findings": findings,
        "reports": reports,
    }


__all__ = [
    "REPORT_RECORD_TYPE",
    "FINDING_RECORD_TYPE",
    "RETIRED_MODEL_REPLACEMENTS",
    "check_llm_sdk_drift",
    "check_pydantic_v2_fastapi_drift",
    "check_nextjs_react19_tailwind4_drift",
    "check_mcp_server_safety",
    "run_all_drift_linters",
]
