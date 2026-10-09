"""End-to-end proof of the Baltor app for ChatGPT on the deployed service, with the official MCP client.

    PYTHONPATH=src:tools python tools/check_chatgpt_app_live.py https://baltor.ai REPORT.json \\
        --account ~/baltor-private/<folder>/fresh-account-state.json --evidence ~/baltor-private/<folder>/run-1 \\
        [--expect-presentation] [--screens integrations/chatgpt-app/assets]

One fresh customer account, made through Baltor's own sign-up by `tools/check_live_account_journeys.mjs --fresh-only`
(its state file, mode 0600, outside the repository, names the address and password), connects the way an MCP client
does: OAuth discovery, dynamic client registration, an authorization request with an S256 proof key and the resource,
sign-in and explicit consent in a real browser (`tools/chatgpt_app_consent.mjs`), the code exchange with the issuer
checked by the client, then the protocol in both eras. It searches, opens a package, downloads exact files and checks
each file's SHA-256 against the digest the service published, finds and downloads a Public Good file, refreshes and
finally revokes its delegation, so no grant of the run stays live.

The run reads the OpenAI host presentation by sending `Baltor-Client-Profile: openai_apps`, which is what a client
registered with ChatGPT's redirect reads without a header. Before the release that serves it, the service answers in
the harness presentation; the run then projects the same answers with `chatgpt_app` and records
`presentation_served: false`, so the delivery proof stands and the presentation proof waits. `--expect-presentation`
makes that a failure. With `--screens`, the starter prompts' answers are rendered by
`tools/capture_chatgpt_app_screens.mjs` into the directory's 706-pixel screenshots, from the view the service served
or, before that release, from the packaged view, and the record says which.

The report is public-safe: no address, password, token, code, account identity or file content, only checks,
counts, catalogue identities and digests. The consent screenshots and raw answers stay in the private evidence folder.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from loop_engine.core.service_runtime import chatgpt_app  # noqa: E402

CALLBACK = "http://127.0.0.1:53682/callback"
CLIENT_NAME = "Baltor ChatGPT app check"
SCOPES = "provisioning:metadata provisioning:read"
#: The starter prompts of the submission package and the call each answers with, in order. Their answers are the
#: screenshots; the package's own check reads the same prompts from plugin.json.
STARTERS = (("search_library", "release notes from git commits"), ("get_package", "Blender 3D scene"),
            ("search_library", "code review subagent"))
PUBLIC_GOOD_QUERY = "water quality"
#: Results a starter search asks for: three cards fit one 706 by 860 pixel screenshot.
SCREEN_RESULTS = 3
HARNESS = {"search_library": "intelligence_search", "get_package": "provisioning_manifest",
           "download_package_files": "provisioning_read", "find_public_good_files": "public_good_files",
           "check_library_access": "provisioning_discover"}


class Run:
    def __init__(self):
        self.checks = []

    def check(self, name, passed, **detail):
        self.checks.append({"name": name, "passed": passed is True, **detail})
        return passed is True


def _private_file(path: Path):
    held = path.lstat()
    if not stat.S_ISREG(held.st_mode) or held.st_mode & 0o077 or held.st_uid != os.getuid():
        raise SystemExit(f"{path} must be a regular file readable by this user only")


def _digest(text: str, encoding: str) -> str:
    data = text.encode("utf-8") if encoding == "utf-8" else base64.b64decode(text)
    return hashlib.sha256(data).hexdigest()


class Store:
    def __init__(self):
        self.tokens = self.client = None

    async def get_tokens(self):
        return self.tokens

    async def set_tokens(self, tokens):
        self.tokens = tokens

    async def get_client_info(self):
        return self.client

    async def set_client_info(self, info):
        self.client = info


def discovery(run, origin):
    import httpx
    with httpx.Client(timeout=30, trust_env=False) as http:
        resource = http.get(origin + "/.well-known/oauth-protected-resource").json()
        resource_mcp = http.get(origin + "/.well-known/oauth-protected-resource/mcp").json()
        metadata = http.get(origin + "/.well-known/oauth-authorization-server").json()
        refused = http.post(origin + "/mcp", headers={"Accept": "application/json, text/event-stream"},
                            json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        challenge = http.get(origin + "/.well-known/openai-apps-challenge")
    run.check("protected_resource_metadata_names_the_mcp_resource_and_issuer",
              resource == resource_mcp and resource.get("resource") == origin + "/mcp"
              and resource.get("authorization_servers") == [metadata.get("issuer")])
    run.check("authorization_server_offers_pkce_s256_registration_and_public_clients",
              "S256" in metadata.get("code_challenge_methods_supported", ())
              and metadata.get("registration_endpoint") == origin + "/register"
              and "none" in metadata.get("token_endpoint_auth_methods_supported", ())
              and {"authorization_code", "refresh_token"} <= set(metadata.get("grant_types_supported", ())),
              issuer=metadata.get("issuer"), iss_parameter=metadata.get("authorization_response_iss_parameter_supported", False))
    run.check("an_unauthenticated_request_is_challenged_with_the_resource_metadata",
              refused.status_code == 401 and "resource_metadata=" in refused.headers.get("www-authenticate", ""))
    token = challenge.text if challenge.status_code == 200 else ""
    run.check("domain_verification_answer_is_one_plain_token_or_absent",
              (challenge.status_code == 200 and challenge.headers.get("content-type", "").startswith("text/plain")
               and token and token.strip() == token and "\n" not in token) or challenge.status_code == 404,
              status=challenge.status_code, served=challenge.status_code == 200)
    return metadata


async def connect(run, origin, account_path, evidence):
    import httpx2
    from mcp.client.auth import OAuthClientProvider
    from mcp.shared.auth import AuthorizationCodeResult, OAuthClientMetadata
    store, held = Store(), {}

    async def redirect(url):
        process = await asyncio.create_subprocess_exec(
            "node", str(ROOT / "tools" / "chatgpt_app_consent.mjs"), url, CALLBACK, str(account_path), str(evidence),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd=str(ROOT))
        out, err = await process.communicate()
        if process.returncode != 0:
            raise RuntimeError("consent failed: " + err.decode()[-800:])
        held["consent"] = json.loads(out.decode().strip().splitlines()[-1])
        query = parse_qs(urlsplit(url).query)
        held["authorization"] = {key: query.get(key, [""])[0] for key in ("response_type", "code_challenge_method",
                                                                             "resource", "scope")}

    async def callback():
        query = parse_qs(urlsplit(held["consent"]["callback_url"]).query)
        held["callback_parameters"] = sorted(query)
        return AuthorizationCodeResult(code=query["code"][0], state=query.get("state", [None])[0],
                                       iss=query.get("iss", [None])[0])

    auth = OAuthClientProvider(origin + "/mcp", OAuthClientMetadata(
        redirect_uris=[CALLBACK], client_name=CLIENT_NAME, grant_types=["authorization_code", "refresh_token"],
        response_types=["code"], token_endpoint_auth_method="none", scope=SCOPES), store,
        redirect_handler=redirect, callback_handler=callback)
    http = httpx2.AsyncClient(auth=auth, trust_env=False, timeout=90)
    return store, held, http


async def session(origin, http, headers, mode):
    import httpx2
    from mcp import Client
    from mcp.client.streamable_http import streamable_http_client
    http.headers.update(headers)
    return Client(streamable_http_client(origin + "/mcp", http_client=http), mode=mode)


def _dump(value):
    return value.model_dump(mode="json", by_alias=True, exclude_none=True)


async def present(client, served, name, arguments, origin, *, listed_files=None):
    """Call one app tool: through the served presentation, or through its harness tool and the same projection.

    Before the presentation is served, get_package's file list comes from the search answer that listed the item
    (`listed_files`), which carries the same package summary the presentation reads."""
    tool = chatgpt_app.TOOLS_BY_NAME[name]
    if served:
        result = await client.call_tool(name, arguments)
        return result.is_error, result.structured_content
    internal = chatgpt_app.internal_arguments(tool, arguments)
    result = await client.call_tool(HARNESS[name], internal)
    if result.is_error:
        return True, chatgpt_app.presented_refusal(result.structured_content, base_url=origin)
    output = result.structured_content
    package = None
    if name == "get_package" and listed_files is not None:
        package = {"files": [{"path": row["path"], "size_bytes": row["size_bytes"], "digest": row["sha256"],
                              "media_type": row.get("media_type"), "role": row.get("role")} for row in listed_files]}
    return False, chatgpt_app.presented_result(tool, arguments, output, base_url=origin, package=package)


async def flows(run, origin, client, served, raw):
    from jsonschema import Draft202012Validator
    shapes_ok, internal = True, []

    def shape(name, value):
        nonlocal shapes_ok
        errors = list(Draft202012Validator(chatgpt_app.TOOLS_BY_NAME[name].output_schema).iter_errors(value))
        shapes_ok = shapes_ok and not errors
        internal.extend(chatgpt_app.internal_fields_in(value))
        return value

    screens = []
    for index, (name, query) in enumerate(STARTERS, start=1):
        error, found = await present(client, served, "search_library", {"query": query, "limit": SCREEN_RESULTS}, origin)
        raw["starter_%d_search" % index] = found
        results = (found or {}).get("results", []) if not error else []
        run.check(f"starter_{index}_search_finds_items", bool(results), query=query, results=len(results))
        shape("search_library", found)
        if name == "search_library":
            screen = {"tool": name, "tool_input": {"query": query, "limit": SCREEN_RESULTS}, "structured_content": found}
            if results:
                # The view's "Show files" action asks for get_package over the bridge; its real answer is given to the
                # screenshot host so the action is checked with live data.
                error, follow = await present(client, served, "get_package", {
                    "identity": results[0]["identity"], "expected_digest": results[0]["expected_digest"]}, origin,
                    listed_files=results[0]["files"])
                if not error:
                    shape("get_package", follow)
                    screen["follow_up"] = follow
            screens.append(screen)
            continue
        top = results[0]
        error, package = await present(client, served, "get_package",
                                       {"identity": top["identity"], "expected_digest": top["expected_digest"]}, origin,
                                       listed_files=top["files"])
        raw["starter_%d_package" % index] = package
        run.check(f"starter_{index}_package_lists_its_files", not error and bool(package["package"]["files"]),
                  identity=top["identity"], files=len(package["package"]["files"]) if not error else 0)
        shape("get_package", package)
        screens.append({"tool": name, "tool_input": {"identity": top["identity"], "expected_digest": top["expected_digest"]},
                        "structured_content": package})
    # Download: the package of the second starter, with the effects it declares, as a person's consent would allow.
    item = raw["starter_2_package"]["package"]
    arguments = {"identity": item["identity"], "expected_digest": item["expected_digest"]}
    if item["effects_to_declare"]:
        # What a person's consent would allow: every effect the item declares, as the step's effects.
        arguments["authority_effects"] = sorted(set(item["declared_effects"]) - {"pure"})
    delivered, offset, pages = {}, None, 0
    while pages < 10:
        call = dict(arguments, **({"file_offset": offset} if offset is not None else {}))
        error, files = await present(client, served, "download_package_files", call, origin)
        pages += 1
        if error:
            run.check("download_package_files_delivers_the_package", False, refusal=files.get("error", {}).get("code"))
            break
        shape("download_package_files", files)
        for row in files["files"]:
            delivered[row["path"]] = row
        offset = files["next_file_offset"]
        if offset is None:
            break
    listed = {row["path"]: row["sha256"] for row in item["files"]}
    exact = all(_digest(row["content"], row["encoding"]) == row["sha256"] == listed.get(path, row["sha256"])
                for path, row in delivered.items())
    run.check("download_package_files_delivers_exact_files_whose_digests_match", bool(delivered) and exact,
              identity=item["identity"], files_delivered=len(delivered), files_listed=item["file_count"], pages=pages,
              digests=sorted((path, row["sha256"]) for path, row in delivered.items()))
    # Public Good: find a file and download exactly that file.
    error, public = await present(client, served, "find_public_good_files", {"query": PUBLIC_GOOD_QUERY, "page_size": 5},
                                  origin)
    shape("find_public_good_files", public)
    placement = next((row["placements"][0] for row in public.get("files", ()) if row["placements"]), None) if not error else None
    run.check("find_public_good_files_finds_files", placement is not None, query=PUBLIC_GOOD_QUERY,
              matches=public.get("matches") if not error else 0)
    if placement is not None:
        file_sha = next(row["sha256"] for row in public["files"] if row["placements"] and row["placements"][0] is placement)
        call = {"identity": placement["identity"], "expected_digest": placement["expected_digest"], "path": placement["path"]}
        error, one = await present(client, served, "download_package_files", call, origin)
        if error and one.get("error", {}).get("code") == "step_effects_required":
            call["authority_effects"] = sorted(set(one["error"]["details"]["declared_effects"]) - {"pure"})
            error, one = await present(client, served, "download_package_files", call, origin)
        good = (not error and len(one["files"]) == 1 and _digest(one["files"][0]["content"], one["files"][0]["encoding"])
                == one["files"][0]["sha256"] == file_sha)
        run.check("a_public_good_file_downloads_exactly", good, identity=placement["identity"], path=placement["path"],
                  sha256=file_sha, counted_as_download=None if error else one["counted_as_download"])
    error, access = await present(client, served, "check_library_access", {}, origin)
    shape("check_library_access", access)
    run.check("check_library_access_reports_the_account_reach", not error and access["items_available"] > 0,
              downloads_included=None if error else access["downloads_included"])
    error, missing = await present(client, served, "get_package", {"identity": "no_such_item_for_this_check"}, origin)
    run.check("an_unknown_identity_is_refused_in_the_same_code_without_internal_fields",
              error and missing["error"]["code"] == "item_unavailable" and not chatgpt_app.internal_fields_in(missing))
    run.check("every_answer_matches_its_output_schema", shapes_ok)
    run.check("no_answer_carries_an_internal_field", not internal, found=sorted(set(internal))[:10])
    return screens


async def main_async(arguments):
    run = Run()
    origin = arguments.origin.rstrip("/")
    account = Path(arguments.account).expanduser().resolve()
    _private_file(account)
    evidence = Path(arguments.evidence).expanduser().resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    os.chmod(evidence, 0o700)
    discovery(run, origin)
    store, held, http = await connect(run, origin, account, evidence)
    raw, screens, served = {}, [], False
    try:
        async with await session(origin, http, {chatgpt_app.PROFILE_HEADER_NAME: chatgpt_app.PROFILE}, "legacy") as client:
            consent = held.get("consent", {}).get("shown", {})
            run.check("oauth_consent_was_explicit_and_named_the_client_and_scopes",
                      consent.get("client_name") == CLIENT_NAME and len(consent.get("scopes", [])) >= 2,
                      sign_in_first=consent.get("sign_in_first"), scopes_shown=len(consent.get("scopes", [])),
                      phone_no_horizontal_overflow=consent.get("phone_no_horizontal_overflow"))
            run.check("authorization_used_s256_and_the_resource",
                      held["authorization"]["code_challenge_method"] == "S256"
                      and held["authorization"]["resource"] == origin + "/mcp",
                      callback_parameters=held.get("callback_parameters"))
            tools = await client.list_tools()
            names = [tool.name for tool in tools.tools]
            served = names == [tool.name for tool in chatgpt_app.TOOLS]
            problems = [problem for tool in tools.tools for problem in chatgpt_app.descriptor_problems(_dump(tool))]
            run.check("the_openai_host_presentation_is_served", served or not arguments.expect_presentation,
                      presentation_served=served, tools=names)
            view_html, view_source = None, "packaged"
            if served:
                run.check("every_advertised_tool_meets_the_directory_rules", not problems, problems=problems[:10])
                read = await client.read_resource(chatgpt_app.TEMPLATE_URI)
                content = read.contents[0]
                meta = _dump(content).get("_meta", {})
                run.check("the_view_resource_is_an_mcp_app_with_no_outside_domains",
                          content.mime_type == chatgpt_app.TEMPLATE_MIME_TYPE
                          and meta.get("ui", {}).get("csp") == {"connectDomains": [], "resourceDomains": []}
                          and meta.get("ui", {}).get("domain") == origin,
                          sha256=hashlib.sha256(content.text.encode()).hexdigest())
                view_html, view_source = content.text, "served"
            screens = await flows(run, origin, client, served, raw)
        async with await session(origin, http, {chatgpt_app.PROFILE_HEADER_NAME: chatgpt_app.PROFILE}, "2026-07-28") as client:
            listed = await client.list_tools()
            per_request = [tool.name for tool in listed.tools]
            error, found = await present(client, served, "search_library", {"query": STARTERS[0][1]}, origin)
            run.check("the_per_request_era_lists_and_searches_too", not error and found["results"]
                      and client.protocol_version == "2026-07-28", tools=len(per_request))
        http.headers.pop(chatgpt_app.PROFILE_HEADER_NAME, None)
        async with await session(origin, http, {}, "legacy") as client:
            harness = [tool.name for tool in (await client.list_tools()).tools]
            run.check("without_the_header_the_harness_presentation_is_unchanged", "provisioning_read" in harness,
                      tools=len(harness))
    finally:
        await http.aclose()
    tokens = store.tokens
    import httpx
    with httpx.Client(timeout=30, trust_env=False) as plain:
        refreshed = plain.post(origin + "/token", data={"grant_type": "refresh_token", "refresh_token": tokens.refresh_token,
                                                         "client_id": store.client.client_id, "resource": origin + "/mcp"})
        rotated = refreshed.json() if refreshed.status_code == 200 else {}
        reused = plain.post(origin + "/token", data={"grant_type": "refresh_token", "refresh_token": tokens.refresh_token,
                                                      "client_id": store.client.client_id, "resource": origin + "/mcp"})
        run.check("refresh_rotates_and_the_old_refresh_token_is_refused",
                  refreshed.status_code == 200 and reused.status_code == 400 and rotated.get("access_token") != tokens.access_token)
        revoked = plain.post(origin + "/revoke", data={"client_id": store.client.client_id,
                                                       "token": rotated.get("access_token", tokens.access_token)})
        after = plain.post(origin + "/mcp", headers={"Authorization": "Bearer " + rotated.get("access_token", ""),
                                                     "Accept": "application/json, text/event-stream"},
                           json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
        run.check("revocation_ends_the_delegation", revoked.status_code == 200 and after.status_code == 401)
    (evidence / "answers.json").write_text(json.dumps(raw, indent=1))
    os.chmod(evidence / "answers.json", 0o600)
    screens_report = None
    if arguments.screens:
        mark = base64.b64encode((ROOT / "integrations" / "chatgpt-app" / "assets" / "icon.png").read_bytes()).decode()
        cases = {"record_type": "chatgpt_app_screen_cases/v1", "view_source": view_source,
                 "view_html": view_html or chatgpt_app.template_html(), "mark_data_url": "data:image/png;base64," + mark,
                 "cases": [{**screen, "prompt": prompt} for screen, prompt in zip(screens, _starter_prompts())]}
        cases_path = evidence / "screen-cases.json"
        cases_path.write_text(json.dumps(cases))
        captured = subprocess.run(["node", str(ROOT / "tools" / "capture_chatgpt_app_screens.mjs"), str(cases_path),
                                   str(Path(arguments.screens).resolve())], capture_output=True, text=True, cwd=str(ROOT),
                                  timeout=300)
        screens_report = json.loads(captured.stdout.strip().splitlines()[-1]) if captured.stdout.strip() else None
        run.check("the_starter_prompt_screenshots_render_the_view_without_errors",
                  captured.returncode == 0 and screens_report and screens_report["all_passed"],
                  view_source=view_source, stderr=captured.stderr[-400:] if captured.returncode else "")
    report = {"record_type": "chatgpt_app_live_check/v1", "origin": origin,
              "observed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
              "presentation_served": served, "checks": run.checks,
              "passed": sum(row["passed"] for row in run.checks), "total": len(run.checks),
              "all_passed": all(row["passed"] for row in run.checks),
              "screens": [{key: row.get(key) for key in ("case", "label", "tool", "screenshot", "page_height",
                                                          "view_scrolls_sideways")} for row in (screens_report or {}).get("cases", [])],
              "limits": ("A real MCP client and a real browser on the live service, as a fresh customer account. "
                         "It is not ChatGPT itself: ChatGPT's own rendering, model choices and directory review are "
                         "checked by the owner in ChatGPT.")}
    return report


def _starter_prompts():
    manifest = json.loads((ROOT / "integrations" / "chatgpt-app" / "plugin.json").read_text())
    return manifest["extensions"]["com.openai"]["interface"]["defaultPrompt"]


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("origin")
    parser.add_argument("report")
    parser.add_argument("--account", required=True)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--expect-presentation", action="store_true")
    parser.add_argument("--screens")
    arguments = parser.parse_args()
    if chatgpt_app.https_address(arguments.origin) is None or Path(arguments.report).exists():
        parser.error("use an HTTPS origin and a new report path")
    report = asyncio.run(main_async(arguments))
    Path(arguments.report).write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({"passed": report["passed"], "total": report["total"], "all_passed": report["all_passed"],
                      "presentation_served": report["presentation_served"],
                      "failed": [row["name"] for row in report["checks"] if not row["passed"]]}))
    return 0 if report["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
