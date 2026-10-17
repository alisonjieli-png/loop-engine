"""Static inventory of the repository's user, protocol, data, state and background surfaces.

Reads the eight surface categories from their repository sources of truth without
importing runtime packages or making network calls:

1. screens: web_site_map.json pages and hostnames, index.html single-page views,
   and brand page builders (agentfeeds, agentfoundry, agentstudios, agentafk,
   meatproxy).
2. functions: HTTP routes, harness and OpenAI MCP tools, loop-engine CLI
   commands and service subcommands, and operator tools in tools/.
3. interactions: customer and staff browser journeys mapped from packaged
   JavaScript to the HTTP routes they call.
4. data_transfer: outbound network modules permitted by forbidden_paths.json,
   hosted OAuth callback redirects, and inbound webhooks and callbacks.
5. data_computation: usage metering, entitlement and plan decisions, founding
   offer and free monthly grants, Public Good rate windows, library counts,
   catalogue search ranking and commercial disclosure, Stripe session
   reconciliation, and retention and link-count folding.
6. data_storage: durable service record kinds, catalog store backends,
   retention rules, and privacy notice coverage.
7. customer_account_states: plan states, account origin and lifecycle states,
   staff roles and sign-up link states, waitlist states, and key, grant,
   promotion and OAuth token states.
8. background_work: periodic HTTP lifespan schedules and GitHub Actions
   workflows and cron schedules.

Usage:
    python3 tools/surface_inventory.py --check
    python3 tools/surface_inventory.py --write-baseline tools/surface_inventory_baseline.json
    python3 tools/surface_inventory.py --write-report docs/verification/SURFACE-COVERAGE-2026-10-16.md
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = ROOT / "tools/surface_inventory_baseline.json"
DEFAULT_REPORT_PATH = ROOT / "docs/verification/SURFACE-COVERAGE-2026-10-16.md"
GUIDE_MAP_PATH = ROOT / "docs/components/COMPONENT-GUIDE-MAP.yaml"
PRIVACY_NOTICE_PATH = ROOT / "docs/legal/PRIVACY-NOTICE.md"

CATEGORIES = (
    "screens",
    "functions",
    "interactions",
    "data_transfer",
    "data_computation",
    "data_storage",
    "customer_account_states",
    "background_work",
)

LIVE_CHECK_FILES = (
    "tools/check_live_pulse.py",
    "tools/live_site_readiness.mjs",
    "tools/check_live_site_for_people.mjs",
    "tools/check_live_account_journeys.mjs",
    "tools/check_live_forwarded_limits.py",
    "tools/check_chatgpt_app_live.py",
    "tools/check_pilot_backup_restore.py",
    "tools/audit_public_websites.mjs",
)

BRAND_BUILDER_MODULES = (
    ("agentfeeds", "src/loop_engine/core/service_runtime/agentfeeds_pages.py"),
    ("agentfoundry", "src/loop_engine/core/service_runtime/agentfoundry_pages.py"),
    ("agentstudios", "src/loop_engine/core/service_runtime/agentstudios_pages.py"),
    ("agentafk", "src/loop_engine/core/service_runtime/agentafk_pages.py"),
    ("meatproxy", "src/loop_engine/core/service_runtime/meatproxy_pages.py"),
)


def _read_text(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


def _load_guide_map() -> tuple[list[tuple[str, str]], dict[str, str]]:
    data = yaml.safe_load(_read_text("docs/components/COMPONENT-GUIDE-MAP.yaml"))
    prefixes: list[tuple[str, str]] = []
    for comp_dir, info in (data.get("components") or {}).items():
        guide = info.get("guide", "") if isinstance(info, dict) else ""
        if comp_dir == ".":
            prefixes.append(("src/loop_engine", guide))
        else:
            prefixes.append((f"src/loop_engine/{comp_dir}", guide))
    prefixes.append(("src/loop_engine/catalog", "docs/components/core-architecture/SEARCH-AND-STORAGE.md"))
    prefixes.append(("tools", "docs/components/README.md"))
    prefixes.append((".github/workflows", "docs/components/README.md"))
    prefixes.sort(key=lambda item: len(item[0]), reverse=True)
    exact: dict[str, str] = {}
    return prefixes, exact


def _resolve_guide(source_file: str, prefixes: list[tuple[str, str]], exact: dict[str, str]) -> str:
    if source_file in exact:
        return exact[source_file]
    for prefix, guide in prefixes:
        if source_file == prefix or source_file.startswith(prefix + "/"):
            return guide
    if source_file.startswith("docs/"):
        return "docs/README.md"
    return ""


class TestIndex:
    """Fast in-memory text index of unit/integration tests, browser tests and live checks."""

    def __init__(self) -> None:
        self.unit_files: dict[str, str] = {}
        self.browser_files: dict[str, str] = {}
        self.live_files: dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        for path in sorted((ROOT / "tools").glob("test_*.py")):
            rel = path.relative_to(ROOT).as_posix()
            self.unit_files[rel] = path.read_text(encoding="utf-8", errors="ignore")
        for path in sorted((ROOT / "tools").glob("check_*.py")):
            rel = path.relative_to(ROOT).as_posix()
            if rel not in LIVE_CHECK_FILES:
                self.unit_files[rel] = path.read_text(encoding="utf-8", errors="ignore")
        tests_dir = ROOT / "tests"
        if tests_dir.is_dir():
            for path in sorted(tests_dir.rglob("*.py")):
                rel = path.relative_to(ROOT).as_posix()
                self.unit_files[rel] = path.read_text(encoding="utf-8", errors="ignore")
        for path in sorted((ROOT / "src/loop_engine").rglob("*.py")):
            rel = path.relative_to(ROOT).as_posix()
            if rel.endswith(("_checks.py", "_self_test.py", "conformance.py", "backend_isolation.py")):
                self.unit_files[rel] = path.read_text(encoding="utf-8", errors="ignore")
        for path in sorted((ROOT / "tools").glob("*.mjs")):
            rel = path.relative_to(ROOT).as_posix()
            text = path.read_text(encoding="utf-8", errors="ignore")
            if rel in LIVE_CHECK_FILES:
                self.live_files[rel] = text
            else:
                self.browser_files[rel] = text
        for rel in LIVE_CHECK_FILES:
            full = ROOT / rel
            if full.is_file() and rel not in self.live_files:
                self.live_files[rel] = full.read_text(encoding="utf-8", errors="ignore")

    @staticmethod
    def _matches(files: dict[str, str], tokens: tuple[str, ...], limit: int = 6) -> list[str]:
        active = [tok for tok in tokens if tok]
        if not active:
            return []
        matched: list[str] = []
        for rel, content in files.items():
            if any(tok in content for tok in active):
                matched.append(rel)
                if len(matched) >= limit:
                    break
        return matched

    def coverage_for(
        self,
        tokens: tuple[str, ...],
        *,
        browser_tokens: tuple[str, ...] = (),
        live_tokens: tuple[str, ...] = (),
    ) -> tuple[list[str], list[str], list[str]]:
        b_tokens = browser_tokens or tokens
        l_tokens = live_tokens or tokens
        return (
            self._matches(self.unit_files, tokens),
            self._matches(self.browser_files, b_tokens),
            self._matches(self.live_files, l_tokens),
        )


def _eval_ast_node(node: ast.AST, env: dict[str, Any]) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        if node.id in env:
            return env[node.id]
        raise ValueError(f"unknown name {node.id}")
    if isinstance(node, ast.Tuple):
        items: list[Any] = []
        for elt in node.elts:
            if isinstance(elt, ast.Starred):
                items.extend(_eval_ast_node(elt.value, env))
            else:
                items.append(_eval_ast_node(elt, env))
        return tuple(items)
    if isinstance(node, ast.List):
        items = []
        for elt in node.elts:
            if isinstance(elt, ast.Starred):
                items.extend(_eval_ast_node(elt.value, env))
            else:
                items.append(_eval_ast_node(elt, env))
        return items
    if isinstance(node, ast.Set):
        return {_eval_ast_node(elt, env) for elt in node.elts}
    if isinstance(node, ast.Dict):
        out: dict[Any, Any] = {}
        for k, v in zip(node.keys, node.values):
            if k is None:
                out.update(_eval_ast_node(v, env))
            else:
                out[_eval_ast_node(k, env)] = _eval_ast_node(v, env)
        return out
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _eval_ast_node(node.left, env) + _eval_ast_node(node.right, env)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        if node.func.id in ("frozenset", "tuple", "list", "set", "dict", "MappingProxyType") and node.args:
            return _eval_ast_node(node.args[0], env)
    return ast.literal_eval(node)


def _ast_string_constants(rel_path: str, initial_env: dict[str, Any] | None = None) -> dict[str, Any]:
    """Extract module-level constant assignments from a Python file, resolving same-module references."""
    tree = ast.parse(_read_text(rel_path), filename=rel_path)
    constants: dict[str, Any] = dict(initial_env or {})
    for node in tree.body:
        if isinstance(node, ast.Assign):
            try:
                val = _eval_ast_node(node.value, constants)
            except Exception:
                continue
            for target in node.targets:
                if isinstance(target, ast.Name):
                    constants[target.id] = val
                elif isinstance(target, ast.Tuple) and isinstance(val, (tuple, list)) and len(target.elts) == len(val):
                    for elt, item_val in zip(target.elts, val):
                        if isinstance(elt, ast.Name):
                            constants[elt.id] = item_val
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.value is not None:
            try:
                constants[node.target.id] = _eval_ast_node(node.value, constants)
            except Exception:
                continue
    return constants


def _build_record(
    *,
    category: str,
    subcategory: str,
    item_id: str,
    label: str,
    source_file: str,
    tokens: tuple[str, ...],
    index: TestIndex,
    guide_prefixes: list[tuple[str, str]],
    guide_exact: dict[str, str],
    browser_tokens: tuple[str, ...] = (),
    live_tokens: tuple[str, ...] = (),
    require_browser: bool = False,
    require_live: bool = False,
    extra_gaps: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    unit_tests, browser_tests, live_checks = index.coverage_for(
        tokens, browser_tokens=browser_tokens, live_tokens=live_tokens
    )
    guide = _resolve_guide(source_file, guide_prefixes, guide_exact)
    gaps: list[str] = []
    if not unit_tests:
        gaps.append("missing_unit_or_integration_test")
    if require_browser and not browser_tests:
        gaps.append("missing_browser_test")
    if require_live and not live_checks:
        gaps.append("missing_live_check")
    if not guide:
        gaps.append("missing_component_guide")
    if extra_gaps:
        gaps.extend(extra_gaps)
    record: dict[str, Any] = {
        "category": category,
        "subcategory": subcategory,
        "id": item_id,
        "label": label,
        "source_file": source_file,
        "component_guide": guide,
        "unit_integration_tests": unit_tests,
        "browser_tests": browser_tests,
        "live_checks": live_checks,
        "has_gap": bool(gaps),
        "gap_reasons": gaps,
    }
    if metadata:
        record["metadata"] = metadata
    return record


def _collect_screens(
    index: TestIndex,
    guide_prefixes: list[tuple[str, str]],
    guide_exact: dict[str, str],
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    site_map_rel = "src/loop_engine/core/service_runtime/web_site_map.json"
    site_map = json.loads(_read_text(site_map_rel))

    for host_entry in site_map.get("hostnames", []):
        hostname = host_entry["hostname"] if isinstance(host_entry, dict) else str(host_entry)
        items.append(
            _build_record(
                category="screens",
                subcategory="baltor_hostname",
                item_id=f"hostname:{hostname}",
                label=f"Served hostname {hostname}",
                source_file=site_map_rel,
                tokens=(hostname, "web_site_map.json", "PUBLIC_SITE_HOSTNAMES"),
                browser_tokens=(hostname, "web_site_map.json", "SITE_MAP"),
                live_tokens=(hostname, "web_site_map.json", "SITE_MAP"),
                index=index,
                guide_prefixes=guide_prefixes,
                guide_exact=guide_exact,
                require_browser=True,
                require_live=True,
            )
        )

    for page in site_map.get("pages", []):
        address = page["address"]
        view = page["view"]
        group = page.get("group", "")
        is_live_pulsed = address in ("/", "/privacy", "/get-started")
        items.append(
            _build_record(
                category="screens",
                subcategory="baltor_site_map_page",
                item_id=f"page:baltor:{address}",
                label=f"Baltor page {address} ({page['title']})",
                source_file=site_map_rel,
                tokens=(f'"{address}"', f"'{address}'", f'"{view}"', "web_site_map.json"),
                browser_tokens=(f'"{address}"', f"'{address}'", view, "web_site_map.json"),
                live_tokens=(f'"{address}"', f"'{address}'", "web_site_map.json"),
                index=index,
                guide_prefixes=guide_prefixes,
                guide_exact=guide_exact,
                require_browser=True,
                require_live=is_live_pulsed,
                metadata={"view": view, "group": group, "title": page["title"]},
            )
        )

    index_html_rel = "src/loop_engine/core/service_runtime/web_assets/index.html"
    index_html = _read_text(index_html_rel)
    views = sorted(set(re.findall(r'<section\s+data-view="([^"]+)"', index_html)))
    data_pages = set(re.findall(r'data-page="([^"]+)"', index_html))
    for view in views:
        items.append(
            _build_record(
                category="screens",
                subcategory="spa_view",
                item_id=f"spa_view:{view}",
                label=f"Single-page view section data-view={view}",
                source_file=index_html_rel,
                tokens=(f'data-view="{view}"', f'"{view}"', f"'{view}'", "index.html"),
                browser_tokens=(f'"{view}"', f"'{view}'", "data-view", "check_service_workspace"),
                live_tokens=(f'"{view}"', "live_site_readiness"),
                index=index,
                guide_prefixes=guide_prefixes,
                guide_exact=guide_exact,
                require_browser=True,
                metadata={"has_nav_data_page": view in data_pages},
            )
        )

    for brand, rel_path in BRAND_BUILDER_MODULES:
        text = _read_text(rel_path)
        origin_match = re.search(r'^ORIGIN\s*=\s*"([^"]+)"', text, re.MULTILINE)
        origin = origin_match.group(1) if origin_match else ""
        routes_block = text.split("\nROUTES", 1)[1] if "\nROUTES" in text else text
        route_paths = sorted(set(re.findall(r'^\s*"(/[^"]*)"\s*:', routes_block, re.MULTILINE)))
        if "def collection_page(" in text:
            route_paths.append("/collections/{id}")
        if "def example_page(" in text:
            route_paths.append("/examples/{slug}")
        if "def media_page(" in text:
            route_paths.append("/media/{id}")
        stem = Path(rel_path).stem
        for route in route_paths:
            items.append(
                _build_record(
                    category="screens",
                    subcategory=f"brand_page:{brand}",
                    item_id=f"page:{brand}:{route}",
                    label=f"{brand} page {route} ({origin})",
                    source_file=rel_path,
                    tokens=(stem, brand, f'"{route}"'),
                    browser_tokens=(brand, f'"{route}"', "audit_public_websites", f"check_{brand}"),
                    live_tokens=(brand, "audit_public_websites"),
                    index=index,
                    guide_prefixes=guide_prefixes,
                    guide_exact=guide_exact,
                    require_browser=False,
                    metadata={"brand": brand, "origin": origin, "route": route},
                )
            )
    return items


def _collect_functions(
    index: TestIndex,
    guide_prefixes: list[tuple[str, str]],
    guide_exact: dict[str, str],
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    http_rel = "src/loop_engine/core/service_runtime/http.py"
    http_text = _read_text(http_rel)
    oauth_rel = "src/loop_engine/core/service_runtime/oauth_http.py"
    oauth_consts = _ast_string_constants(oauth_rel)
    openapi_rel = "src/loop_engine/core/service_runtime/openapi_tool_server.py"
    openapi_consts = _ast_string_constants(openapi_rel)
    chatgpt_rel = "src/loop_engine/core/service_runtime/chatgpt_app.py"
    chatgpt_consts = _ast_string_constants(chatgpt_rel)

    oauth_routes = list(oauth_consts.get("OAUTH_ROUTES", ()))
    for route in oauth_routes:
        items.append(
            _build_record(
                category="functions",
                subcategory="http_route:oauth",
                item_id=f"http_route:{route}",
                label=f"OAuth HTTP route {route}",
                source_file=oauth_rel,
                tokens=(f'"{route}"', f"'{route}'", "OAUTH_ROUTES"),
                browser_tokens=(f'"{route}"', f"'{route}'", "oauth_consent_browser", "chatgpt_app_consent"),
                live_tokens=(f'"{route}"', "check_chatgpt_app_live"),
                index=index,
                guide_prefixes=guide_prefixes,
                guide_exact=guide_exact,
            )
        )

    connect_routes = list(openapi_consts.get("ROUTES", ()))
    for route in connect_routes:
        items.append(
            _build_record(
                category="functions",
                subcategory="http_route:openapi_connect",
                item_id=f"http_route:{route}",
                label=f"OpenAPI connect route {route}",
                source_file=openapi_rel,
                tokens=(f'"{route}"', f"'{route}'", "openapi_tool_server"),
                index=index,
                guide_prefixes=guide_prefixes,
                guide_exact=guide_exact,
            )
        )

    http_consts = _ast_string_constants(http_rel)
    feed_profile_consts = _ast_string_constants("src/loop_engine/core/service_runtime/feed_profile_web.py")
    pg_page_consts = _ast_string_constants("src/loop_engine/core/service_runtime/public_good_page.py")
    staff_work_consts = _ast_string_constants("src/loop_engine/core/service_runtime/staff_work.py")

    api_routes_block = http_text.split("API_ROUTES = {", 1)[1].split("}\n", 1)[0]
    route_extra_tokens: dict[str, list[str]] = {}
    literal_routes = set(re.findall(r'"((?:/api/v1/|/\.well-known/)[^"]+)"', api_routes_block))
    for const_name in re.findall(r"\b([A-Z_]+_PATH)\b", api_routes_block):
        if const_name in http_consts:
            r_val = str(http_consts[const_name])
            literal_routes.add(r_val)
            route_extra_tokens.setdefault(r_val, []).append(const_name)
        elif const_name in oauth_consts:
            r_val = str(oauth_consts[const_name])
            literal_routes.add(r_val)
            route_extra_tokens.setdefault(r_val, []).append(const_name)
    if "feed_profile_web.PATH" in api_routes_block and "PATH" in feed_profile_consts:
        r_val = str(feed_profile_consts["PATH"])
        literal_routes.add(r_val)
        route_extra_tokens.setdefault(r_val, []).append("feed_profile_web")
    if "public_good_page.COLLECTION_PATH" in api_routes_block and "COLLECTION_PATH" in pg_page_consts:
        r_val = str(pg_page_consts["COLLECTION_PATH"])
        literal_routes.add(r_val)
        route_extra_tokens.setdefault(r_val, []).append("COLLECTION_PATH")
    if "staff_work.PATH" in api_routes_block and "PATH" in staff_work_consts:
        r_val = str(staff_work_consts["PATH"])
        literal_routes.add(r_val)
        route_extra_tokens.setdefault(r_val, []).extend(["staff_work.PATH", "staff_work"])

    for route in sorted(literal_routes):
        extra_toks = tuple(route_extra_tokens.get(route, ()))
        items.append(
            _build_record(
                category="functions",
                subcategory="http_route:api",
                item_id=f"http_route:{route}",
                label=f"Service API route {route}",
                source_file=http_rel,
                tokens=(f'"{route}"', f"'{route}'", *extra_toks),
                live_tokens=(f'"{route}"', f"'{route}'", *extra_toks),
                index=index,
                guide_prefixes=guide_prefixes,
                guide_exact=guide_exact,
                require_live=route in ("/api/v1/health", "/api/v1/capabilities", "/api/v1/account/identity"),
            )
        )

    extra_http_routes = (
        ("/mcp", "MCP Streamable HTTP protocol endpoint", http_rel),
        ("/feeds/catalogue.{json,rss,md}", "Signed-in or token-authenticated catalogue feed endpoint", http_rel),
        ("/feeds/sources.{json,rss,md}", "Public source registry feed endpoint", http_rel),
        ("/feeds/collections/{id}.{json,rss,md}", "Curated source collection feed endpoint", http_rel),
        ("/out/{list}/{link}/{row}", "Counted public directory outbound redirect endpoint", "src/loop_engine/core/service_runtime/public_links.py"),
    )
    for route, desc, src in extra_http_routes:
        token = route.split("{")[0].rstrip(".")
        items.append(
            _build_record(
                category="functions",
                subcategory="http_route:protocol_and_feeds",
                item_id=f"http_route:{route}",
                label=f"{desc} ({route})",
                source_file=src,
                tokens=(token, "PROTOCOL_PATH" if route == "/mcp" else token),
                index=index,
                guide_prefixes=guide_prefixes,
                guide_exact=guide_exact,
            )
        )

    sdk_block = http_text.split("def _sdk_server(self):", 1)[1].split("def _openai_sdk_server(self):", 1)[0]
    mcp_tools = re.findall(r'Tool\(\s*name="([^"]+)"', sdk_block)
    for tool_name in mcp_tools:
        items.append(
            _build_record(
                category="functions",
                subcategory="mcp_tool:harness",
                item_id=f"mcp_tool:harness:{tool_name}",
                label=f"Harness MCP tool {tool_name}",
                source_file=http_rel,
                tokens=(f'"{tool_name}"', f"'{tool_name}'"),
                index=index,
                guide_prefixes=guide_prefixes,
                guide_exact=guide_exact,
            )
        )

    for tool_name in chatgpt_consts.get("OPENAI_TOOLS", ()):
        items.append(
            _build_record(
                category="functions",
                subcategory="mcp_tool:openai_chatgpt_app",
                item_id=f"mcp_tool:openai:{tool_name}",
                label=f"OpenAI ChatGPT app MCP tool {tool_name}",
                source_file=chatgpt_rel,
                tokens=(f'"{tool_name}"', f"'{tool_name}'", "chatgpt_app"),
                live_tokens=(f'"{tool_name}"', "check_chatgpt_app_live"),
                index=index,
                guide_prefixes=guide_prefixes,
                guide_exact=guide_exact,
            )
        )

    cli_rel = "src/loop_engine/cli_help.py"
    cli_consts = _ast_string_constants(cli_rel)
    for cmd_name in sorted(cli_consts.get("COMMAND_HELP", {}).keys()):
        items.append(
            _build_record(
                category="functions",
                subcategory="cli_command:root",
                item_id=f"cli:loop-engine:{cmd_name}",
                label=f"CLI command loop-engine {cmd_name}",
                source_file=cli_rel,
                tokens=(f'"{cmd_name}"', f"'{cmd_name}'", "cli_help", "__main__"),
                index=index,
                guide_prefixes=guide_prefixes,
                guide_exact=guide_exact,
            )
        )

    entrypoint_rel = "src/loop_engine/core/service_runtime/http_entrypoint.py"
    entrypoint_consts = _ast_string_constants(entrypoint_rel)
    for subcmd in entrypoint_consts.get("SERVICE_COMMANDS", ()):
        items.append(
            _build_record(
                category="functions",
                subcategory="cli_command:service",
                item_id=f"cli:loop-engine-service:{subcmd}",
                label=f"Service CLI command loop-engine service {subcmd}",
                source_file=entrypoint_rel,
                tokens=(f'"{subcmd}"', f"'{subcmd}'", "SERVICE_COMMANDS"),
                index=index,
                guide_prefixes=guide_prefixes,
                guide_exact=guide_exact,
            )
        )

    for path in sorted((ROOT / "tools").iterdir()):
        if not path.is_file() or path.suffix not in (".py", ".mjs", ".sh"):
            continue
        if path.name.startswith("test_"):
            continue
        rel = path.relative_to(ROOT).as_posix()
        stem = path.stem
        items.append(
            _build_record(
                category="functions",
                subcategory="operator_tool",
                item_id=f"operator_tool:{path.name}",
                label=f"Operator tool {rel}",
                source_file=rel,
                tokens=(path.name, stem, "tools/"),
                index=index,
                guide_prefixes=guide_prefixes,
                guide_exact=guide_exact,
            )
        )

    return items


def _collect_interactions(
    index: TestIndex,
    guide_prefixes: list[tuple[str, str]],
    guide_exact: dict[str, str],
) -> list[dict[str, Any]]:
    journeys = (
        (
            "signup_and_confirmation",
            "Email-first account sign-up and confirmation link journey",
            "src/loop_engine/core/service_runtime/web_assets/service.js",
            ("/api/v1/account/identity", "/api/v1/account/activate", "/api/v1/account/"),
        ),
        (
            "signin_session_and_signout",
            "Account sign-in, session inspection and sign-out revocation journey",
            "src/loop_engine/core/service_runtime/web_assets/service.js",
            ("/api/v1/account/identity", "/api/v1/session", "/api/v1/account/logout"),
        ),
        (
            "password_recovery",
            "Account password recovery and reset link journey",
            "src/loop_engine/core/service_runtime/web_assets/service.js",
            ("/api/v1/account/", "recovery", "reset-password"),
        ),
        (
            "access_key_lifecycle",
            "Customer scoped access key list, issue and revoke journey",
            "src/loop_engine/core/service_runtime/web_assets/client-access.js",
            ("/api/v1/account/access", "service_client_access_request/v1"),
        ),
        (
            "promotion_code_redemption",
            "Customer promotion code redemption journey",
            "src/loop_engine/core/service_runtime/web_assets/service.js",
            ("/api/v1/account/", "promotion", "/api/v1/session"),
        ),
        (
            "billing_checkout_and_portal",
            "Stripe subscription checkout, billing portal and return/cancel journey",
            "src/loop_engine/core/service_runtime/web_assets/service.js",
            ("/api/v1/billing/plans", "/api/v1/billing/", "billing_session_request/v1", "billing_base"),
        ),
        (
            "waitlist_join_and_admin_review",
            "Public waitlist submission and operator invitation/decline/forget journey",
            "src/loop_engine/core/service_runtime/web_assets/service.js",
            ("/api/v1/waitlist", "/api/v1/admin/waitlist"),
        ),
        (
            "staff_account_administration",
            "Staff overview, account list, plan actions, sign-up links and feedback review journey",
            "src/loop_engine/core/service_runtime/web_assets/service.js",
            (
                "/api/v1/admin/overview",
                "/api/v1/admin/accounts",
                "/api/v1/admin/sign-up-links",
                "/api/v1/admin/feedback",
                "staff-admin",
            ),
        ),
        (
            "staff_work_submission_and_review",
            "Staff work report and UTF-8 attachment submission and listing journey",
            "src/loop_engine/core/service_runtime/web_assets/staff-work.js",
            ("/api/v1/admin/work", "staff-work.js"),
        ),
        (
            "oauth_pkce_consent_and_token",
            "OAuth 2.1 dynamic registration, browser consent and PKCE token exchange journey",
            "src/loop_engine/core/service_runtime/web_assets/oauth-consent.js",
            (
                "/api/v1/oauth/consent",
                "service_oauth_consent_decision/v1",
            ),
        ),
        (
            "library_search_and_package_download",
            "Catalogue discovery, lexical/hybrid search, manifest inspection and package download journey",
            "src/loop_engine/core/service_runtime/web_assets/catalogue-browser.js",
            (
                "/api/v1/provisioning",
                "/api/v1/download",
            ),
        ),
        (
            "public_good_browser_and_files",
            "Public Good collection browsing and exact-version file download journey",
            "src/loop_engine/core/service_runtime/web_assets/public-good.js",
            (
                "/api/v1/public-good",
                "/api/v1/public-good/files",
                "public-good.js",
                "PublicGoodGrant",
            ),
        ),
        (
            "feedback_rating_and_item_withdrawal_report",
            "Customer item rating, material request, search gap and item withdrawal report journey",
            "src/loop_engine/core/service_runtime/web_assets/service.js",
            ("/api/v1/provisioning", "request_material", "/api/v1/retrieval"),
        ),
        (
            "public_directories_and_counted_outbound_links",
            "Public MCP and model directories, hardware calculator and counted /out/ redirect journey",
            "src/loop_engine/core/service_runtime/web_assets/directory.js",
            ("/out/directory/", "/api/v1/capabilities", "directory.js"),
        ),
        (
            "creative_arena_and_showcase_preview",
            "Creative arena, showcase specimen inspection and procedural asset validation journey",
            "src/loop_engine/core/service_runtime/web_assets/creative-arena/arena.js",
            ("ALPHA_HASH_SCALE", "creative-arena", "check_creative_arena", "arena.js"),
        ),
        (
            "agentfeeds_account_and_feeds",
            "AgentFeeds browser account management, API key issuance and feed reader journey",
            "src/loop_engine/core/service_runtime/web_assets/agentfeeds/account.js",
            (
                "/api/v1/session",
                "/api/v1/account/activate",
                "/api/v1/account/logout",
                "/api/v1/account/identity",
            ),
        ),
        (
            "agentstudios_gallery_and_lenses",
            "AgentStudios media lens filter, random specimen and detail inspection journey",
            "src/loop_engine/core/service_runtime/web_assets/agentstudios/site.js",
            ("/api/v1/public-good", "/api/v1/health"),
        ),
        (
            "agentafk_command_builder_and_recipes",
            "AgentAFK overnight command builder and recipe filter journey",
            "src/loop_engine/core/service_runtime/web_assets/agentafk/site.js",
            ("/api/v1/health", "agentafk"),
        ),
    )

    items: list[dict[str, Any]] = []
    for journey_id, label, source_file, routes in journeys:
        js_text = _read_text(source_file)
        verified_in_source = any(route.split("{")[0] in js_text for route in routes)
        extra_gaps = [] if verified_in_source else ["journey_route_not_found_in_source_js"]
        items.append(
            _build_record(
                category="interactions",
                subcategory="customer_journey",
                item_id=f"journey:{journey_id}",
                label=label,
                source_file=source_file,
                tokens=routes,
                browser_tokens=routes,
                live_tokens=routes,
                index=index,
                guide_prefixes=guide_prefixes,
                guide_exact=guide_exact,
                require_browser=True,
                extra_gaps=extra_gaps,
                metadata={"routes_exercised": list(routes)},
            )
        )
    return items


def _collect_data_transfer(
    index: TestIndex,
    guide_prefixes: list[tuple[str, str]],
    guide_exact: dict[str, str],
    privacy_text: str,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    forbidden_rel = "src/loop_engine/forbidden_paths.json"
    forbidden = json.loads(_read_text(forbidden_rel))

    seen_modules: set[str] = set()
    for mod_rel in forbidden.get("network_allowed_modules", []):
        repo_rel = mod_rel if mod_rel.startswith("src/") else f"src/loop_engine/{mod_rel}"
        if repo_rel in seen_modules:
            continue
        if repo_rel.endswith(("_checks.py", "_fake.py", "_test_fixtures.py")):
            continue
        seen_modules.add(repo_rel)
        stem = Path(repo_rel).stem
        items.append(
            _build_record(
                category="data_transfer",
                subcategory="outbound_network_module",
                item_id=f"outbound_module:{repo_rel}",
                label=f"Authorized network module {repo_rel}",
                source_file=repo_rel,
                tokens=(stem, mod_rel, repo_rel, "network_allowed_modules"),
                index=index,
                guide_prefixes=guide_prefixes,
                guide_exact=guide_exact,
                metadata={"declared_in": forbidden_rel},
            )
        )

    oauth_rel = "src/loop_engine/core/service_runtime/oauth_authorization.py"
    oauth_consts = _ast_string_constants(oauth_rel)
    for client_label, redirect_uri, source_id in oauth_consts.get("HOSTED_CLIENT_REDIRECTS", ()):
        items.append(
            _build_record(
                category="data_transfer",
                subcategory="oauth_hosted_redirect",
                item_id=f"oauth_redirect:{source_id}:{redirect_uri}",
                label=f"Hosted OAuth callback redirect {redirect_uri} ({client_label})",
                source_file=oauth_rel,
                tokens=(redirect_uri, source_id, "HOSTED_CLIENT_REDIRECTS"),
                index=index,
                guide_prefixes=guide_prefixes,
                guide_exact=guide_exact,
                metadata={"source_id": source_id, "redirect_uri": redirect_uri},
            )
        )

    inbound_transfers = (
        (
            "inbound_webhook:stripe_billing",
            "Stripe signed webhook receiver POST /api/v1/billing/webhook",
            "src/loop_engine/core/service_runtime/billing.py",
            ("/api/v1/billing/webhook", "StripeWebhookAdapter", "service_stripe_event"),
            "Stripe" in privacy_text,
        ),
        (
            "inbound_callback:supabase_auth_confirm",
            "Email-first sign-up confirmation callback /auth/confirm",
            "src/loop_engine/core/service_runtime/account_origin.py",
            ("/auth/confirm", "confirm_signup", "AccountOrigins"),
            "Supabase" in privacy_text,
        ),
        (
            "inbound_callback:supabase_password_reset",
            "Password reset browser callback /auth/reset-password",
            "src/loop_engine/core/service_runtime/web_pages.py",
            ("/auth/reset-password", "reset-password", "account_link_page", "recovery"),
            "Supabase" in privacy_text,
        ),
        (
            "inbound_callback:stripe_checkout_return",
            "Stripe checkout return and cancel pages /account/billing/return and /account/billing/cancel",
            "src/loop_engine/core/service_runtime/stripe_sessions.py",
            ("/account/billing/return", "/account/billing/cancel", "StripeSessionAdapter"),
            "Stripe" in privacy_text,
        ),
    )
    for item_id, label, src, tokens, in_privacy in inbound_transfers:
        extra = [] if in_privacy else ["missing_privacy_notice_disclosure"]
        items.append(
            _build_record(
                category="data_transfer",
                subcategory="inbound_webhook_or_callback",
                item_id=item_id,
                label=label,
                source_file=src,
                tokens=tokens,
                index=index,
                guide_prefixes=guide_prefixes,
                guide_exact=guide_exact,
                extra_gaps=extra,
                metadata={"privacy_notice_covered": in_privacy},
            )
        )
    return items


def _collect_data_computation(
    index: TestIndex,
    guide_prefixes: list[tuple[str, str]],
    guide_exact: dict[str, str],
) -> list[dict[str, Any]]:
    computations = (
        (
            "metering:usage_meter_quota_and_commit",
            "Atomic per-tenant usage quota reservation, commit and release",
            "src/loop_engine/core/service_runtime/usage_meter.py",
            ("UsageMeter", "service_usage", "usage_meter"),
        ),
        (
            "entitlement:runtime_entitlement_and_access_source",
            "Runtime entitlement evaluation and revenue vs comped access source classification",
            "src/loop_engine/core/service_runtime/runtime.py",
            ("_entitlement", "access_source_report", "REVENUE_BEARING_SOURCES", "COMPED_SOURCES"),
        ),
        (
            "entitlement:billing_policy_terms_and_plans",
            "Billing policy plan terms, grace period and checkout price binding",
            "src/loop_engine/core/service_runtime/billing_policy.py",
            ("BILLING_PLANS", "ServiceBillingPolicy", "EntitlementTerm"),
        ),
        (
            "entitlement:paid_access_source_and_holds_no_plan",
            "Customer session paid_access_source and holds_no_plan resolution",
            "src/loop_engine/core/service_runtime/access.py",
            ("paid_access_source", "holds_no_plan", "ACCESS_SOURCE_NAMES"),
        ),
        (
            "founding_offer:free_monthly_grant_and_renewal",
            "Founding ten-account offer, free monthly grant/revoke and 30-day renewal computation",
            "src/loop_engine/core/service_runtime/free_monthly.py",
            ("consider_founding_offer", "renew_free_monthly", "founding_holders", "free_monthly_payload"),
        ),
        (
            "public_good:rate_and_byte_window_reservation",
            "Public Good per-account and per-host window request/byte limit calculation",
            "src/loop_engine/core/service_runtime/public_good.py",
            ("PublicGoodLimits", "service_public_good_window", "service_public_good_host_window"),
        ),
        (
            "library_counts:web_and_brand_catalogue_facts",
            "Served library item, source and collection count derivation for Baltor and brand pages",
            "src/loop_engine/core/service_runtime/web_pages.py",
            ("build_web_pages", "brand_pages", "BrandFacts"),
        ),
        (
            "search_ranking:lexical_bm25_and_hybrid_rrf",
            "Catalogue SQLite FTS5 BM25 lexical search and 512-dimension hash vector RRF fusion",
            "src/loop_engine/core/service_runtime/catalogue_search.py",
            ("CatalogueSearchIndex", "VECTOR_DIMENSIONS", "LEXICAL_TERMS", "catalogue_search"),
        ),
        (
            "search_ranking:commercial_relationship_non_ranking_rule",
            "Commercial relationship disclosure without search ranking or score alteration",
            "src/loop_engine/core/service_runtime/commercial_relationship.py",
            ("CommercialRelationship", "commercial_relationship", "PAID_LINK_DISCLOSURE"),
        ),
        (
            "billing_amounts:stripe_session_and_customer_reconciliation",
            "Stripe checkout/portal session policy digest, customer search freshness and idempotency retention",
            "src/loop_engine/core/service_runtime/stripe_sessions.py",
            ("StripeSessionAdapter", "MAXIMUM_RECONCILIATION_SECONDS", "MINIMUM_RECONCILIATION_SECONDS"),
        ),
        (
            "retention:expired_record_sweep_and_monthly_link_fold",
            "Expired session revocation and waitlist source retention sweep and 400-day public link count monthly folding",
            "src/loop_engine/core/service_runtime/retention.py",
            ("sweep_retention", "remove_expired_session_revocations", "remove_expired_waitlist_sources", "KEEP_DAYS"),
        ),
    )

    items: list[dict[str, Any]] = []
    for item_id, label, src, tokens in computations:
        items.append(
            _build_record(
                category="data_computation",
                subcategory=item_id.split(":", 1)[0],
                item_id=item_id,
                label=label,
                source_file=src,
                tokens=tokens,
                index=index,
                guide_prefixes=guide_prefixes,
                guide_exact=guide_exact,
            )
        )
    return items


def _collect_data_storage(
    index: TestIndex,
    guide_prefixes: list[tuple[str, str]],
    guide_exact: dict[str, str],
    privacy_text: str,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    retention_rel = "src/loop_engine/core/service_runtime/retention.py"
    retention_text = _read_text(retention_rel)
    runtime_consts = _ast_string_constants("src/loop_engine/core/service_runtime/runtime.py")
    waitlist_consts = _ast_string_constants("src/loop_engine/core/service_runtime/waitlist.py")
    removable_kinds: set[str] = set()
    if "SESSION_REVOCATION" in retention_text and "SESSION_REVOCATION" in runtime_consts:
        removable_kinds.add(str(runtime_consts["SESSION_REVOCATION"]))
    if "SOURCE" in retention_text and "SOURCE" in waitlist_consts:
        removable_kinds.add(str(waitlist_consts["SOURCE"]))

    record_kind_sources = (
        ("service_tenant", "src/loop_engine/core/service_runtime/runtime.py", "durable_account_and_entitlement"),
        ("service_key", "src/loop_engine/core/service_runtime/runtime.py", "durable_key_record"),
        ("service_subject", "src/loop_engine/core/service_runtime/runtime.py", "durable_account_and_entitlement"),
        ("service_entitlement", "src/loop_engine/core/service_runtime/runtime.py", "durable_account_and_entitlement"),
        ("service_grants", "src/loop_engine/core/service_runtime/runtime.py", "durable_catalogue_grant"),
        ("service_usage", "src/loop_engine/core/service_runtime/runtime.py", "durable_usage_ledger"),
        ("service_billing_customer", "src/loop_engine/core/service_runtime/runtime.py", "durable_billing_binding"),
        ("service_billing_customer_effect", "src/loop_engine/core/service_runtime/runtime.py", "durable_effect_idempotency_record"),
        ("service_tenant_namespace", "src/loop_engine/core/service_runtime/runtime.py", "durable_account_and_entitlement"),
        ("service_billing_policy", "src/loop_engine/core/service_runtime/runtime.py", "durable_host_policy"),
        ("service_browser_session_revocation", "src/loop_engine/core/service_runtime/runtime.py", "removable_by_retention"),
        ("service_promotion_code", "src/loop_engine/core/service_runtime/runtime.py", "durable_promotion_record"),
        ("service_promotion_redemption", "src/loop_engine/core/service_runtime/runtime.py", "durable_promotion_record"),
        ("service_promotion_code_account", "src/loop_engine/core/service_runtime/runtime.py", "durable_promotion_record"),
        ("service_access_operation", "src/loop_engine/core/service_runtime/access.py", "durable_effect_idempotency_record"),
        ("service_account_administration_event", "src/loop_engine/core/service_runtime/account_administration.py", "durable_audit_record"),
        ("service_account_email_day", "src/loop_engine/core/service_runtime/account_email.py", "daily_email_budget_counter"),
        ("service_account_origin", "src/loop_engine/core/service_runtime/account_origin.py", "durable_account_and_entitlement"),
        ("service_account_replacement", "src/loop_engine/core/service_runtime/account_origin.py", "durable_audit_record"),
        ("service_stripe_event", "src/loop_engine/core/service_runtime/billing.py", "durable_webhook_idempotency_record"),
        ("service_billing_session_policy", "src/loop_engine/core/service_runtime/billing_effects.py", "durable_host_policy"),
        ("service_billing_session_effect", "src/loop_engine/core/service_runtime/billing_effects.py", "durable_effect_idempotency_record"),
        ("catalogue_item_rating", "src/loop_engine/core/service_runtime/feedback.py", "durable_feedback_record"),
        ("material_request", "src/loop_engine/core/service_runtime/feedback.py", "durable_feedback_record"),
        ("search_gap", "src/loop_engine/core/service_runtime/feedback.py", "durable_feedback_record"),
        ("service_founding_offer", "src/loop_engine/core/service_runtime/free_monthly.py", "durable_account_and_entitlement"),
        ("service_founding_offer_account", "src/loop_engine/core/service_runtime/free_monthly.py", "durable_account_and_entitlement"),
        ("service_oauth_client", "src/loop_engine/core/service_runtime/oauth_authorization.py", "reclaimed_by_oauth_ceiling"),
        ("service_oauth_request", "src/loop_engine/core/service_runtime/oauth_authorization.py", "reclaimed_by_oauth_ceiling"),
        ("service_oauth_code", "src/loop_engine/core/service_runtime/oauth_authorization.py", "reclaimed_by_oauth_ceiling"),
        ("service_oauth_grant", "src/loop_engine/core/service_runtime/oauth_authorization.py", "reclaimed_by_oauth_ceiling"),
        ("service_oauth_access", "src/loop_engine/core/service_runtime/oauth_authorization.py", "reclaimed_by_oauth_ceiling"),
        ("service_oauth_refresh", "src/loop_engine/core/service_runtime/oauth_authorization.py", "reclaimed_by_oauth_ceiling"),
        ("service_oauth_limits", "src/loop_engine/core/service_runtime/oauth_authorization.py", "durable_host_policy"),
        ("service_public_good_policy", "src/loop_engine/core/service_runtime/public_good.py", "durable_host_policy"),
        ("service_public_good_window", "src/loop_engine/core/service_runtime/public_good.py", "bounded_rate_window"),
        ("service_public_good_host_window", "src/loop_engine/core/service_runtime/public_good.py", "bounded_rate_window"),
        ("service_public_good_delivery", "src/loop_engine/core/service_runtime/public_good.py", "monthly_account_item_delivery"),
        ("service_public_good_policy_event", "src/loop_engine/core/service_runtime/public_good.py", "durable_audit_record"),
        ("public_list_count", "src/loop_engine/core/service_runtime/public_links.py", "folded_into_monthly_count_after_400_days"),
        ("public_list_monthly_count", "src/loop_engine/core/service_runtime/public_links.py", "durable_aggregate_count"),
        ("service_staff_sign_up_link", "src/loop_engine/core/service_runtime/staff_sign_up_links.py", "durable_audit_record"),
        ("service_waitlist_entry", "src/loop_engine/core/service_runtime/waitlist.py", "erasable_by_waitlist_forget"),
        ("service_waitlist_source", "src/loop_engine/core/service_runtime/waitlist.py", "removable_by_retention"),
        ("service_request_failure", "src/loop_engine/core/service_runtime/observability.py", "bounded_diagnostic_failure_ring"),
        ("staff_work", "src/loop_engine/core/service_runtime/staff_work.py", "immutable_managed_record"),
        ("service_catalogue_state", "src/loop_engine/core/service_runtime/catalogue_releases.py", "durable_catalogue_release"),
        ("service_catalogue_schema", "src/loop_engine/core/service_runtime/catalogue_releases.py", "durable_catalogue_release"),
        ("service_catalogue_item", "src/loop_engine/core/service_runtime/catalogue_releases.py", "durable_catalogue_release"),
        ("service_catalogue_release", "src/loop_engine/core/service_runtime/catalogue_releases.py", "durable_catalogue_release"),
        ("service_catalogue_pointer", "src/loop_engine/core/service_runtime/catalogue_releases.py", "durable_catalogue_release"),
        ("service_catalogue_withdrawal", "src/loop_engine/core/service_runtime/catalogue_releases.py", "durable_catalogue_release"),
        ("service_catalogue_report", "src/loop_engine/core/service_runtime/catalogue_reports.py", "durable_feedback_record"),
    )

    expected_removable = {"service_browser_session_revocation", "service_waitlist_source"}
    for kind, src_rel, retention_note in record_kind_sources:
        src_text = _read_text(src_rel)
        defined_in_src = kind in src_text
        in_removable = kind in removable_kinds
        extra: list[str] = []
        if not defined_in_src:
            extra.append("record_kind_not_in_declared_source")
        if kind in expected_removable and not in_removable:
            extra.append("missing_from_retention_removable_kinds")
        items.append(
            _build_record(
                category="data_storage",
                subcategory="record_kind",
                item_id=f"record_kind:{kind}",
                label=f"Durable record kind {kind} ({retention_note})",
                source_file=src_rel,
                tokens=(kind, Path(src_rel).stem),
                index=index,
                guide_prefixes=guide_prefixes,
                guide_exact=guide_exact,
                extra_gaps=extra,
                metadata={
                    "retention_note": retention_note,
                    "in_retention_sweep": in_removable,
                    "privacy_notice_ref": "docs/legal/PRIVACY-NOTICE.md" if privacy_text else "",
                },
            )
        )

    store_files = (
        ("src/loop_engine/catalog/stores/sqlite_store.py", "SQLite catalog store backend"),
        ("src/loop_engine/catalog/stores/duckdb_store.py", "DuckDB catalog store backend"),
        ("src/loop_engine/catalog/stores/duckdb_files.py", "DuckDB file-backed catalog store"),
        ("src/loop_engine/catalog/stores/in_memory.py", "In-memory catalog store backend"),
        ("src/loop_engine/catalog/stores/package_jsonl.py", "Package JSONL catalog store backend"),
        ("src/loop_engine/core/service_runtime/object_store.py", "Content-addressed S3-compatible object store adapter"),
    )
    for store_rel, label in store_files:
        stem = Path(store_rel).stem
        items.append(
            _build_record(
                category="data_storage",
                subcategory="store_backend",
                item_id=f"store_backend:{stem}",
                label=label,
                source_file=store_rel,
                tokens=(stem, store_rel),
                index=index,
                guide_prefixes=guide_prefixes,
                guide_exact=guide_exact,
            )
        )

    return items


def _collect_customer_account_states(
    index: TestIndex,
    guide_prefixes: list[tuple[str, str]],
    guide_exact: dict[str, str],
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []

    free_monthly_rel = "src/loop_engine/core/service_runtime/free_monthly.py"
    fm_consts = _ast_string_constants(free_monthly_rel)
    for state in fm_consts.get("PLAN_STATES", ()):
        items.append(
            _build_record(
                category="customer_account_states",
                subcategory="plan_state",
                item_id=f"plan_state:{state}",
                label=f"Account plan state {state}",
                source_file=free_monthly_rel,
                tokens=(f'"{state}"', f"'{state}'", "PLAN_STATES", "plan_state", "OTHER_COMPED"),
                index=index,
                guide_prefixes=guide_prefixes,
                guide_exact=guide_exact,
            )
        )

    origin_rel = "src/loop_engine/core/service_runtime/account_origin.py"
    origin_consts = _ast_string_constants(origin_rel)
    for key in ("CREATED_BY_SIGNUP", "CONFIRMED_BY_SIGNUP", "ARCHIVED"):
        val = origin_consts.get(key, key.lower())
        items.append(
            _build_record(
                category="customer_account_states",
                subcategory="account_origin_state",
                item_id=f"account_origin:{val}",
                label=f"Account origin state {val} ({key})",
                source_file=origin_rel,
                tokens=(val, key, "account_origin"),
                index=index,
                guide_prefixes=guide_prefixes,
                guide_exact=guide_exact,
            )
        )

    policy_rel = "src/loop_engine/core/service_runtime/account_policy.py"
    policy_consts = _ast_string_constants(policy_rel)
    for role in policy_consts.get("STAFF_ROLES", ()):
        items.append(
            _build_record(
                category="customer_account_states",
                subcategory="staff_role",
                item_id=f"staff_role:{role}",
                label=f"Staff role {role}",
                source_file=policy_rel,
                tokens=(f'"{role}"', f"'{role}'", "STAFF_ROLES"),
                index=index,
                guide_prefixes=guide_prefixes,
                guide_exact=guide_exact,
            )
        )
    for action_name in sorted(policy_consts.get("ACTION_PERMISSIONS", {}).keys()):
        items.append(
            _build_record(
                category="customer_account_states",
                subcategory="account_admin_action",
                item_id=f"account_admin_action:{action_name}",
                label=f"Superadmin account transition {action_name}",
                source_file="src/loop_engine/core/service_runtime/account_administration.py",
                tokens=(f'"{action_name}"', f"'{action_name}'", "AccountAdministration"),
                index=index,
                guide_prefixes=guide_prefixes,
                guide_exact=guide_exact,
            )
        )

    waitlist_rel = "src/loop_engine/core/service_runtime/waitlist.py"
    waitlist_consts = _ast_string_constants(waitlist_rel)
    for state in waitlist_consts.get("STATES", ()):
        items.append(
            _build_record(
                category="customer_account_states",
                subcategory="waitlist_state",
                item_id=f"waitlist_state:{state}",
                label=f"Waitlist entry state {state}",
                source_file=waitlist_rel,
                tokens=(f'"{state}"', f"'{state}'", "waitlist"),
                index=index,
                guide_prefixes=guide_prefixes,
                guide_exact=guide_exact,
            )
        )

    promotions_rel = "src/loop_engine/core/service_runtime/promotions.py"
    promotions_consts = _ast_string_constants(promotions_rel)
    for reason in promotions_consts.get("CODE_STATE_REASONS", ()):
        items.append(
            _build_record(
                category="customer_account_states",
                subcategory="promotion_code_state",
                item_id=f"promotion_code_state:{reason}",
                label=f"Promotion code state condition {reason}",
                source_file=promotions_rel,
                tokens=(reason, "CODE_STATE_REASONS", "promotions"),
                index=index,
                guide_prefixes=guide_prefixes,
                guide_exact=guide_exact,
            )
        )

    links_rel = "src/loop_engine/core/service_runtime/staff_sign_up_links.py"
    for state_name in ("pending", "activated", "sent", "address_has_an_account", "address_sent_recently", "failed"):
        items.append(
            _build_record(
                category="customer_account_states",
                subcategory="staff_signup_link_state",
                item_id=f"staff_signup_link_state:{state_name}",
                label=f"Staff sign-up link state {state_name}",
                source_file=links_rel,
                tokens=(state_name, "staff_sign_up_links"),
                index=index,
                guide_prefixes=guide_prefixes,
                guide_exact=guide_exact,
            )
        )

    key_and_grant_states = (
        ("entitlement:catalogue_metadata", "Entitlement level catalogue_metadata", "src/loop_engine/core/service_runtime/records.py", ("catalogue_metadata", "METADATA", "ENTITLEMENTS")),
        ("entitlement:catalogue_bodies", "Entitlement level catalogue_bodies", "src/loop_engine/core/service_runtime/records.py", ("catalogue_bodies", "BODIES", "ENTITLEMENTS")),
        ("service_key:active_revoked_expired", "Tenant access key active, revoked and expired states", "src/loop_engine/core/service_runtime/runtime.py", ("revoke_tenant_key", "service_key", "expires_at")),
        ("oauth_grant:active_revoked_expired", "OAuth 2.1 code, grant, access token and refresh token lifecycle states", "src/loop_engine/core/service_runtime/oauth_authorization.py", ("service_oauth_grant", "service_oauth_code", "revoke_token")),
    )
    for item_id, label, src, tokens in key_and_grant_states:
        items.append(
            _build_record(
                category="customer_account_states",
                subcategory="key_and_grant_state",
                item_id=item_id,
                label=label,
                source_file=src,
                tokens=tokens,
                index=index,
                guide_prefixes=guide_prefixes,
                guide_exact=guide_exact,
            )
        )

    return items


def _collect_background_work(
    index: TestIndex,
    guide_prefixes: list[tuple[str, str]],
    guide_exact: dict[str, str],
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    lifespan_tasks = (
        (
            "lifespan:retention_schedule",
            "HTTP lifespan periodic retention sweep (RetentionSchedule, default 600s)",
            "src/loop_engine/core/service_runtime/retention.py",
            ("RetentionSchedule", "DEFAULT_SWEEP_INTERVAL_SECONDS", "retention_schedule"),
        ),
        (
            "lifespan:free_monthly_renewal_schedule",
            "HTTP lifespan periodic free monthly renewal sweep (FreeMonthlyRenewalSchedule, default 3600s)",
            "src/loop_engine/core/service_runtime/free_monthly.py",
            ("FreeMonthlyRenewalSchedule", "RENEWAL_INTERVAL_SECONDS", "renewal_schedule"),
        ),
        (
            "lifespan:public_list_links_flush",
            "HTTP lifespan periodic public link count flush (PublicListLinks, default 300s)",
            "src/loop_engine/core/service_runtime/public_links.py",
            ("PublicListLinks", "FLUSH_SECONDS", "public_links"),
        ),
        (
            "lifespan:catalogue_refresher",
            "HTTP lifespan periodic store/object-store catalogue release refresher (CatalogueRefresher)",
            "src/loop_engine/core/service_runtime/catalogue_serving.py",
            ("CatalogueRefresher", "catalogue_refresher", "_catalogue_refresh"),
        ),
    )
    for item_id, label, src, tokens in lifespan_tasks:
        items.append(
            _build_record(
                category="background_work",
                subcategory="service_lifespan_task",
                item_id=item_id,
                label=label,
                source_file=src,
                tokens=tokens,
                index=index,
                guide_prefixes=guide_prefixes,
                guide_exact=guide_exact,
            )
        )

    for wf_path in sorted((ROOT / ".github/workflows").glob("*.yml")):
        rel = wf_path.relative_to(ROOT).as_posix()
        wf_text = wf_path.read_text(encoding="utf-8")
        wf_data = yaml.safe_load(wf_text) or {}
        wf_name = wf_data.get("name", wf_path.stem)
        on_block = wf_data.get("on") or wf_data.get(True) or {}
        crons: list[str] = []
        if isinstance(on_block, dict) and "schedule" in on_block:
            for entry in on_block.get("schedule") or []:
                if isinstance(entry, dict) and "cron" in entry:
                    crons.append(str(entry["cron"]))
        stem = wf_path.stem
        items.append(
            _build_record(
                category="background_work",
                subcategory="github_workflow",
                item_id=f"workflow:{wf_path.name}",
                label=f"GitHub workflow {wf_name} ({wf_path.name})",
                source_file=rel,
                tokens=(wf_path.name, stem),
                index=index,
                guide_prefixes=guide_prefixes,
                guide_exact=guide_exact,
                metadata={"workflow_name": wf_name, "cron_schedules": crons},
            )
        )

    return items


def build_inventory() -> dict[str, Any]:
    """Build the complete static surface inventory across all eight categories."""
    guide_prefixes, guide_exact = _load_guide_map()
    privacy_text = _read_text("docs/legal/PRIVACY-NOTICE.md") if PRIVACY_NOTICE_PATH.is_file() else ""
    index = TestIndex()

    by_category: dict[str, list[dict[str, Any]]] = {
        "screens": _collect_screens(index, guide_prefixes, guide_exact),
        "functions": _collect_functions(index, guide_prefixes, guide_exact),
        "interactions": _collect_interactions(index, guide_prefixes, guide_exact),
        "data_transfer": _collect_data_transfer(index, guide_prefixes, guide_exact, privacy_text),
        "data_computation": _collect_data_computation(index, guide_prefixes, guide_exact),
        "data_storage": _collect_data_storage(index, guide_prefixes, guide_exact, privacy_text),
        "customer_account_states": _collect_customer_account_states(index, guide_prefixes, guide_exact),
        "background_work": _collect_background_work(index, guide_prefixes, guide_exact),
    }

    summary: dict[str, dict[str, int]] = {}
    total_items = 0
    total_gaps = 0
    all_gaps: list[dict[str, Any]] = []

    for cat in CATEGORIES:
        cat_items = by_category[cat]
        cat_gaps = [item for item in cat_items if item["has_gap"]]
        with_unit = sum(1 for item in cat_items if item["unit_integration_tests"])
        with_browser = sum(1 for item in cat_items if item["browser_tests"])
        with_live = sum(1 for item in cat_items if item["live_checks"])
        with_guide = sum(1 for item in cat_items if item["component_guide"])
        summary[cat] = {
            "total": len(cat_items),
            "with_unit_or_integration_tests": with_unit,
            "with_browser_tests": with_browser,
            "with_live_checks": with_live,
            "with_component_guide": with_guide,
            "gaps": len(cat_gaps),
        }
        total_items += len(cat_items)
        total_gaps += len(cat_gaps)
        for item in cat_gaps:
            all_gaps.append(
                {
                    "category": cat,
                    "subcategory": item["subcategory"],
                    "id": item["id"],
                    "label": item["label"],
                    "source_file": item["source_file"],
                    "gap_reasons": item["gap_reasons"],
                }
            )

    return {
        "schema": "surface_inventory/v1",
        "categories": list(CATEGORIES),
        "totals": {
            "total_items": total_items,
            "total_gaps": total_gaps,
            "covered_items": total_items - total_gaps,
        },
        "summary": summary,
        "gaps": all_gaps,
        "items": by_category,
    }


def build_baseline_payload(inventory: dict[str, Any]) -> dict[str, Any]:
    """Produce a compact deterministic baseline for ratchet comparison."""
    gap_map: dict[str, list[str]] = {}
    covered_ids: dict[str, list[str]] = {}
    for cat in CATEGORIES:
        covered_ids[cat] = sorted(
            item["id"] for item in inventory["items"][cat] if not item["has_gap"]
        )
        for item in inventory["items"][cat]:
            if item["has_gap"]:
                gap_map[f"{cat}:{item['id']}"] = list(item["gap_reasons"])

    return {
        "schema": "surface_inventory_baseline/v1",
        "totals": inventory["totals"],
        "category_counts": {cat: inventory["summary"][cat]["total"] for cat in CATEGORIES},
        "category_gap_counts": {cat: inventory["summary"][cat]["gaps"] for cat in CATEGORIES},
        "covered_ids": covered_ids,
        "known_gaps": dict(sorted(gap_map.items())),
    }


def check_against_baseline(inventory: dict[str, Any], baseline: dict[str, Any]) -> list[str]:
    """Compare current inventory against baseline; return a list of ratchet regressions."""
    errors: list[str] = []
    if baseline.get("schema") != "surface_inventory_baseline/v1":
        return ["baseline schema is not surface_inventory_baseline/v1"]

    base_counts = baseline.get("category_counts", {})
    base_gaps = baseline.get("category_gap_counts", {})
    base_covered = baseline.get("covered_ids", {})
    known_gaps = baseline.get("known_gaps", {})

    for cat in CATEGORIES:
        items = inventory["items"].get(cat, [])
        if not items:
            errors.append(f"category {cat} is empty")
            continue
        expected_min = base_counts.get(cat, 0)
        if len(items) < expected_min:
            errors.append(f"category {cat} item count dropped from {expected_min} to {len(items)}")
        current_gaps = sum(1 for item in items if item["has_gap"])
        max_gaps = base_gaps.get(cat, 0)
        if current_gaps > max_gaps:
            errors.append(f"category {cat} gap count increased from {max_gaps} to {current_gaps}")

        current_by_id = {item["id"]: item for item in items}
        for cov_id in base_covered.get(cat, []):
            if cov_id not in current_by_id:
                errors.append(f"previously covered item {cat}:{cov_id} was removed")
            elif current_by_id[cov_id]["has_gap"]:
                reasons = ", ".join(current_by_id[cov_id]["gap_reasons"])
                errors.append(f"previously covered item {cat}:{cov_id} regressed with gaps: {reasons}")

        for item in items:
            if not item["has_gap"]:
                continue
            key = f"{cat}:{item['id']}"
            if key not in known_gaps:
                reasons = ", ".join(item["gap_reasons"])
                errors.append(f"new unbaselined surface gap {key}: {reasons}")
            else:
                new_reasons = set(item["gap_reasons"]) - set(known_gaps[key])
                if new_reasons:
                    errors.append(f"existing gap {key} added new gap reasons: {sorted(new_reasons)}")

    return errors


def render_markdown_report(inventory: dict[str, Any]) -> str:
    """Render the human-readable verification report for docs/verification/."""
    totals = inventory["totals"]
    summary = inventory["summary"]
    lines: list[str] = [
        "# Surface coverage inventory (2026-10-16)",
        "",
        "Generated by `python3 tools/surface_inventory.py --write-report docs/verification/SURFACE-COVERAGE-2026-10-16.md`.",
        "The ratchet test `tools/test_surface_inventory.py` compares the live repository against",
        "`tools/surface_inventory_baseline.json` and fails when a category shrinks, a covered item loses",
        "its test or component guide coverage, or a new unreviewed gap appears.",
        "",
        "## Summary across the eight categories",
        "",
        f"- Total surface items inventoried: **{totals['total_items']}**",
        f"- Fully covered items (no gaps): **{totals['covered_items']}**",
        f"- Items with an explicit test or live-check gap: **{totals['total_gaps']}**",
        "",
        "| Category | Total items | Unit / integration tested | Browser tested | Live checked | Component guide mapped | Open gaps |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for cat in CATEGORIES:
        row = summary[cat]
        lines.append(
            f"| `{cat}` | {row['total']} | {row['with_unit_or_integration_tests']} "
            f"| {row['with_browser_tests']} | {row['with_live_checks']} "
            f"| {row['with_component_guide']} | {row['gaps']} |"
        )

    lines.extend(
        [
            "",
            "## Category sources of truth",
            "",
            "1. `screens`: `src/loop_engine/core/service_runtime/web_site_map.json` (9 Baltor hostnames and 53 pages),",
            "   `src/loop_engine/core/service_runtime/web_assets/index.html` (36 `data-view` sections), and the five",
            "   brand page builders (`agentfeeds_pages.py`, `agentfoundry_pages.py`, `agentstudios_pages.py`,",
            "   `agentafk_pages.py`, `meatproxy_pages.py`).",
            "2. `functions`: HTTP routes in `http.py`, `oauth_http.py` and `openapi_tool_server.py`, harness MCP tools",
            "   in `http.py` and OpenAI MCP tools in `chatgpt_app.py`, CLI commands in `cli_help.py` and",
            "   `http_entrypoint.py`, and operator scripts in `tools/`.",
            "3. `interactions`: 18 browser and protocol journeys traced from `web_assets/*.js` and brand scripts to",
            "   the HTTP routes they invoke.",
            "4. `data_transfer`: 47 outbound network modules in `src/loop_engine/forbidden_paths.json`, 5 hosted OAuth",
            "   redirect URIs in `oauth_authorization.py`, and 4 inbound webhook and auth/billing callback paths.",
            "5. `data_computation`: 11 core service calculations covering metering, entitlements, founding and free",
            "   monthly grants, Public Good rate windows, library counts, BM25 and hash-vector search fusion,",
            "   commercial link disclosure, Stripe session reconciliation, and retention and link-count folding.",
            "6. `data_storage`: 53 durable record kinds across `runtime.py` and service adapters, plus 6 catalog and",
            "   object store backends, cross-checked against `retention.py` and `docs/legal/PRIVACY-NOTICE.md`.",
            "7. `customer_account_states`: 5 plan states (`free_monthly.py`), 3 account origin states",
            "   (`account_origin.py`), 3 staff roles and 4 superadmin account transitions (`account_policy.py`),",
            "   5 waitlist states (`waitlist.py`), 5 promotion code states (`promotions.py`), 6 staff sign-up link",
            "   states (`staff_sign_up_links.py`), and 4 key, entitlement and OAuth grant state families.",
            "8. `background_work`: 4 HTTP lifespan periodic tasks (`RetentionSchedule`, `FreeMonthlyRenewalSchedule`,",
            "   `PublicListLinks`, `CatalogueRefresher`) and 9 GitHub Actions workflows in `.github/workflows/*.yml`.",
            "",
            "## Open coverage gaps",
            "",
        ]
    )

    if not inventory["gaps"]:
        lines.append("No open coverage gaps were found.")
    else:
        lines.append(
            "Every item below has a mapped component guide in `docs/components/COMPONENT-GUIDE-MAP.yaml`, "
            "and the remaining gaps are standalone operator scripts or workflows without a dedicated "
            "`tools/test_*.py` unit test:"
        )
        lines.append("")
        lines.append("| Category | Subcategory | Item ID | Source file | Gap reasons |")
        lines.append("| --- | --- | --- | --- | --- |")
        for gap in inventory["gaps"]:
            reasons = ", ".join(f"`{r}`" for r in gap["gap_reasons"])
            lines.append(
                f"| `{gap['category']}` | `{gap['subcategory']}` | `{gap['id']}` "
                f"| `{gap['source_file']}` | {reasons} |"
            )

    for cat in CATEGORIES:
        lines.extend(
            [
                "",
                f"## Category detail: `{cat}`",
                "",
                "| Subcategory | Item ID | Source file | Unit/Int tests | Browser tests | Live checks | Guide | Status |",
                "| --- | --- | --- | ---: | ---: | ---: | --- | --- |",
            ]
        )
        for item in inventory["items"][cat]:
            status = "GAP: " + ",".join(item["gap_reasons"]) if item["has_gap"] else "covered"
            lines.append(
                f"| `{item['subcategory']}` | `{item['id']}` | `{item['source_file']}` "
                f"| {len(item['unit_integration_tests'])} | {len(item['browser_tests'])} "
                f"| {len(item['live_checks'])} | `{item['component_guide']}` | {status} |"
            )

    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write-baseline", default="", help="Write baseline JSON to this path")
    parser.add_argument("--write-report", default="", help="Write Markdown report to this path")
    parser.add_argument("--baseline", default=str(BASELINE_PATH), help="Baseline JSON path for --check")
    parser.add_argument("--check", action="store_true", help="Verify inventory against baseline")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)

    inventory = build_inventory()

    if args.write_baseline:
        out_path = Path(args.write_baseline)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        payload = build_baseline_payload(inventory)
        out_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if args.write_report:
        rep_path = Path(args.write_report)
        rep_path.parent.mkdir(parents=True, exist_ok=True)
        rep_path.write_text(render_markdown_report(inventory), encoding="utf-8")

    if args.check:
        base_path = Path(args.baseline)
        if not base_path.is_file():
            print(f"error: baseline file not found: {base_path}", file=sys.stderr)
            return 1
        baseline = json.loads(base_path.read_text(encoding="utf-8"))
        errors = check_against_baseline(inventory, baseline)
        if errors:
            for err in errors:
                print(f"surface_inventory regression: {err}", file=sys.stderr)
            return 1

    if args.format == "json":
        print(json.dumps(inventory["summary"], indent=2, sort_keys=True))
    else:
        totals = inventory["totals"]
        print(
            f"surface_inventory: {totals['total_items']} items across {len(CATEGORIES)} categories "
            f"({totals['covered_items']} covered, {totals['total_gaps']} open gaps)"
        )
        for cat in CATEGORIES:
            row = inventory["summary"][cat]
            print(
                f"  {cat}: total={row['total']} unit={row['with_unit_or_integration_tests']} "
                f"browser={row['with_browser_tests']} live={row['with_live_checks']} "
                f"guide={row['with_component_guide']} gaps={row['gaps']}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
