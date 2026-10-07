"""Conformance kit for the `static_content_network` engine of web page delivery: the website served at the edge.

The real service runs on a loopback socket as the origin. The export (`static_site_export`) renders the same
release's pages, and the edge Worker's own source (`edge/site_edge_worker.js`) serves them under Node through
`edge/local_worker_host.mjs`, with the export folder as its static assets. Every page, asset and hostname root
the edge serves is compared with the service's answer, byte for byte and header for header; requests the edge
does not serve must reach the origin unchanged; with the origin stopped, pages must keep serving and every other
request must get the service's own unavailable answer. Each guard has a removed-guard control: a copy of the
Worker with the guard taken out, which the check's own predicate must fail.

Node 22.5 or later is required for the Worker checks, which are reported as not applicable without it.
"""
from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path
import tempfile

from . import static_site_export as export_module
from .catalogue_d1_index_checks import edge_source, node_runtime

HOSTS = ("baltor.ai", "docs.baltor.ai", "redteam.baltor.ai", "deck.baltor.ai")
ALIAS = "edge.test"
#: The headers a reader's browser acts on; each must be the same at the edge as at the origin.
COMPARED_HEADERS = ("content-type", "content-security-policy", "x-frame-options", "referrer-policy",
                    "permissions-policy", "x-robots-tag", "cache-control", "etag", "x-content-type-options")
SITE_MUTATIONS = {
    "replace_robot_directives": ('  const prior = headers.get("x-robots-tag") || "";', '  const prior = "";'),
    "no_root_meta": ("  if (entry.head && root !== \"/\") bytes = withRootMeta(bytes, root);\n", ""),
    "no_page_headers": ("  const headers = new Headers(kind.headers);\n  headers.set(\"content-type\", entry.media_type);",
                        "  const headers = new Headers();\n  headers.set(\"content-type\", entry.media_type);"),
    "no_read_only_guard": ('  if ((aliased || env.ORIGIN_MODE !== "all") && request.method !== "GET" && request.method !== "HEAD") {',
                           "  if (false) {"),
    "no_unavailable_answer": ("  } catch {\n    return unavailable(request, env, manifest, aliased);\n  }",
                              "  } catch {\n    return new Response(\"origin failed\", { status: 500 });\n  }"),
}


def site_worker(mutation=None):
    source = edge_source("site_edge_worker.js")
    if mutation is None:
        return source
    old, new = SITE_MUTATIONS[mutation]
    if source.count(old) != 1:
        raise AssertionError(f"the control {mutation} no longer finds its guard in the Worker source")
    return source.replace(old, new)


class LocalSite:
    """The site Worker under Node with one export folder as its static assets, in front of `origin`."""

    def __init__(self, root, folder, export_id, origin, *, node, mode="all", source=None, loader_keys=None):
        import subprocess
        root = Path(root)
        root.mkdir(parents=True, exist_ok=True)
        worker, host = root / "site_edge_worker.js", root / "local_worker_host.mjs"
        worker.write_text(source if source is not None else site_worker(), "utf-8")
        host.write_text(edge_source("local_worker_host.mjs"), "utf-8")
        variables = root / "vars.json"
        values = {"ORIGIN": origin, "ORIGIN_MODE": mode, "EXPORT_ID": export_id,
                  "HOST_ALIASES": json.dumps({ALIAS: "baltor.ai"})}
        if loader_keys is not None:
            values["LOADER_KEYS"] = json.dumps(loader_keys)
        variables.write_text(json.dumps(values))
        # With a folder the Worker reads static assets; without one it reads the KV namespace a load wrote.
        store = ["--assets", str(folder)] if folder is not None else ["--kv", str(root / "kv"), "--kv-binding", "SITE"]
        if folder is None:
            (root / "kv").mkdir(exist_ok=True)
        self.kv = root / "kv"
        self.process = subprocess.Popen([node, "--no-warnings", str(host), "--worker", str(worker), *store,
                                         "--vars", str(variables)],
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        line = self.process.stdout.readline().split()
        if len(line) != 2 or line[0] != "LISTENING":
            self.close()
            raise RuntimeError("the local site Worker did not start")
        self.port = int(line[1])

    def close(self):
        import subprocess
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(10)
        for stream in (self.process.stdout, self.process.stderr):
            if stream is not None:
                stream.close()


@contextmanager
def local_site(*args, **kwargs):
    site = LocalSite(*args, **kwargs)
    try:
        yield site
    finally:
        site.close()


def _fetch(port, method, path, host, headers=None, body=None):
    import http.client
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=20)
    try:
        connection.request(method, path, body=body, headers={"Host": f"{host}:{port}", **(headers or {})})
        response = connection.getresponse()
        return response.status, {name.lower(): value for name, value in response.getheaders()}, response.read()
    finally:
        connection.close()


def _same(edge, origin):
    """Equal status, bytes and browser-facing headers; the edge adds only its own mark."""
    return (edge[0] == origin[0] and edge[2] == origin[2]
            and all(edge[1].get(name) == origin[1].get(name) for name in COMPARED_HEADERS))


@contextmanager
def _platform_failure_origin(status):
    """A loopback origin that answers every request with a platform's HTML failure page and `status`."""
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    import threading

    class Failure(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 - the standard handler's name
            body = b"<!DOCTYPE html><html><body>origin unreachable</body></html>"
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=UTF-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):  # noqa: ANN002 - silence the standard handler
            pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), Failure)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


def _origin_service(root):
    from .http_test_fixtures import HttpDomainFixture, running_http
    root.mkdir(parents=True, exist_ok=True)
    fixture = HttpDomainFixture(root)
    return fixture, running_http(fixture, hostnames=HOSTS)


def _export_checks(check):
    from unittest.mock import patch
    export = export_module.export_site(include_model_details=False, hosts=HOSTS)
    check("the_export_reproduces_every_hostname_root_and_names_itself_by_its_content",
          export.manifest["roots"]["docs.baltor.ai"] == "/docs" and len(export.export_id) == 64
          and export_module.export_site(include_model_details=False, hosts=HOSTS).export_id == export.export_id)

    def misplaced(body, address):
        return body.replace(b"<head>", b"<head>" + export_module.ROOT_META.format(address=address).encode(), 1)
    with patch.object(export_module, "with_root_meta", misplaced):
        try:
            export_module.export_site(include_model_details=False, hosts=HOSTS)
            refused = False
        except export_module.StaticExportError:
            refused = True
    check("a_root_meta_tag_written_anywhere_else_stops_the_export", refused)


def _site_checks(check, root, node):
    fixture, running = _origin_service(root / "origin")
    with running as (base, service):
        export = export_module.export_site(display_name=service.configuration.display_name,
                                           library_population=service.served_file_population(),
                                           include_model_details=False, hosts=HOSTS)
        folder = export_module.write_export(export, root / "export")
        origin_port = int(base.rsplit(":", 1)[1])
        static = [address for address in export.manifest["files"] if address != export_module.UNAVAILABLE_PAGE]
        heads = [address for address, entry in export.manifest["files"].items() if entry["head"]]
        with local_site(root / "edge", folder, export.export_id, base, node=node) as site:
            compared = [(_fetch(site.port, "GET", address, "baltor.ai"), _fetch(origin_port, "GET", address, "baltor.ai"))
                        for address in static]
            hosted = [(_fetch(site.port, "GET", address, host), _fetch(origin_port, "GET", address, host))
                      for host in HOSTS[1:] for address in ["/", *heads[:12]]]
            check("every_page_asset_and_hostname_root_the_edge_serves_equals_the_services_own_answer",
                  len(compared) > 100 and all(_same(*pair) for pair in compared + hosted)
                  and all(edge[1].get("x-baltor-edge", "").startswith("static") for edge, _origin in compared))
            asset = next(address for address, entry in export.manifest["files"].items() if entry["class"] == "asset")
            tag = _fetch(origin_port, "GET", asset, "baltor.ai")[1]["etag"]
            check("an_unchanged_asset_answers_not_modified_to_its_validator_as_the_service_does",
                  _fetch(site.port, "GET", asset, "baltor.ai", {"If-None-Match": tag})[0]
                  == _fetch(origin_port, "GET", asset, "baltor.ai", {"If-None-Match": tag})[0] == 304)
            request = json.dumps({"record_type": "service_retrieval_request/v2", "query": "alpha"}).encode()
            passed = [(_fetch(site.port, "GET", "/api/v1/capabilities", "baltor.ai"),
                       _fetch(origin_port, "GET", "/api/v1/capabilities", "baltor.ai")),
                      (_fetch(site.port, "POST", "/api/v1/retrieval", "baltor.ai",
                              {**fixture.headers(), "Content-Type": "application/json"}, request),
                       _fetch(origin_port, "POST", "/api/v1/retrieval", "baltor.ai",
                              {**fixture.headers(), "Content-Type": "application/json"}, request))]
            check("requests_the_edge_does_not_serve_reach_the_origin_unchanged",
                  all(edge[0] == origin[0] == 200 and json.loads(edge[2]) == json.loads(origin[2])
                      and edge[1].get("x-baltor-edge") == "origin" for edge, origin in passed))
            aliased = _fetch(site.port, "GET", "/pricing", ALIAS)
            check("a_hostname_the_site_map_does_not_name_is_shown_noindex",
                  aliased[0] == 200 and aliased[1].get("x-robots-tag") == "noindex"
                  and aliased[2] == compared[static.index("/pricing")][1][2])
            private_index = [(_fetch(site.port, "GET", address, ALIAS),
                              _fetch(origin_port, "GET", address, "baltor.ai"))
                             for address in ("/dot-context", "/dot-context.json", "/dot-feedback", "/dot-feedback.json")]
            check("alias_noindex_preserves_every_existing_robot_directive",
                  all(_same(*pair) for pair in private_index))
            check("aliased_preview_never_passes_changes_when_canonical_hosts_allow_them",
                  _fetch(site.port, "POST", "/api/v1/retrieval", ALIAS,
                         {**fixture.headers(), "Content-Type": "application/json"}, request)[0] == 403)
        with local_site(root / "edge-read-only", folder, export.export_id, base, node=node, mode="read_only") as site:
            refused = _fetch(site.port, "POST", "/api/v1/retrieval", "baltor.ai",
                             {**fixture.headers(), "Content-Type": "application/json"}, request)
            check("a_read_only_edge_never_passes_a_change_to_the_origin",
                  refused[0] == 403 and json.loads(refused[2])["error"]["code"] == "edge_prototype_read_only"
                  and _fetch(site.port, "GET", "/api/v1/capabilities", "baltor.ai")[0] == 200)
        with local_site(root / "edge-guard", folder, export.export_id, base, node=node, mode="read_only",
                        source=site_worker("no_read_only_guard")) as site:
            check("removed_read_only_guard_is_detected",
                  _fetch(site.port, "POST", "/api/v1/retrieval", "baltor.ai",
                         {**fixture.headers(), "Content-Type": "application/json"}, request)[0] == 200)
        for mutation, name in (("no_root_meta", "removed_root_meta_rule_is_detected"),
                               ("no_page_headers", "removed_page_headers_are_detected")):
            with local_site(root / f"edge-{mutation}", folder, export.export_id, base, node=node,
                            source=site_worker(mutation)) as site:
                probe = [(_fetch(site.port, "GET", address, host), _fetch(origin_port, "GET", address, host))
                         for host in HOSTS[:2] for address in ["/", "/pricing", "/docs"]]
                check(name, not all(_same(*pair) for pair in probe))
        with local_site(root / "edge-robot-control", folder, export.export_id, base, node=node,
                        source=site_worker("replace_robot_directives")) as site:
            check("removed_alias_robot_directive_preservation_is_detected",
                  not _same(_fetch(site.port, "GET", "/dot-context", ALIAS),
                            _fetch(origin_port, "GET", "/dot-context", "baltor.ai")))
        with local_site(root / "edge-alias-control", folder, export.export_id, base, node=node,
                        source=site_worker("no_read_only_guard")) as site:
            check("removed_aliased_preview_write_refusal_is_detected",
                  _fetch(site.port, "POST", "/api/v1/retrieval", ALIAS,
                         {**fixture.headers(), "Content-Type": "application/json"}, request)[0] == 200)
    # The origin is stopped now: the closed socket is what a release that rebuilds its view looks like from the edge.
    pages = ["/", "/pricing", "/docs", static[-1]]
    with local_site(root / "edge-down", folder, export.export_id, base, node=node) as site:
        down = [_fetch(site.port, "GET", address, "baltor.ai") for address in pages]
        api = _fetch(site.port, "GET", "/api/v1/capabilities", "baltor.ai")
        page = _fetch(site.port, "GET", "/library", "baltor.ai", {"Accept": "text/html"})
        record = json.loads(api[2]) if api[0] == 503 else {}
        check("with_the_origin_down_pages_keep_serving_and_other_requests_get_the_unavailable_answer",
              all(answer[0] == 200 for answer in down)
              and [answer[2] for answer in down] == [compared[static.index(address)][1][2] for address in pages]
              and api[0] == 503 and record.get("error", {}).get("code") == "service_unavailable"
              and api[1].get("retry-after") == "30" and page[0] == 503 and b"<html" in page[2].lower())
    with local_site(root / "edge-down-control", folder, export.export_id, base, node=node,
                    source=site_worker("no_unavailable_answer")) as site:
        check("removed_unavailable_answer_is_detected",
              _fetch(site.port, "GET", "/api/v1/capabilities", "baltor.ai")[0] != 503)
    # At the edge an origin that cannot be reached or resolved is not an exception: Cloudflare answers with its own
    # 52x page (530 for a name it cannot resolve, observed on October 5, 2026), which must not reach the reader.
    with _platform_failure_origin(530) as failing, local_site(root / "edge-530", folder, export.export_id, failing,
                                                              node=node) as site:
        answer = _fetch(site.port, "GET", "/api/v1/health", "baltor.ai")
        check("a_platform_failure_page_from_the_origin_becomes_the_services_unavailable_answer",
              answer[0] == 503 and json.loads(answer[2])["error"]["code"] == "service_unavailable")


def _loader_checks(check, root, node, export):
    """The KV store a prototype loads through the signed route serves what static assets serve."""
    from .catalogue_d1_index import RequestSigner, public_key_entry
    from .catalogue_d1_index_checks import _signer
    admin, stranger = _signer(), _signer()
    keys = [public_key_entry(admin.public_key_raw, ["admin"])]
    entries = export_module.kv_entries(export)
    # The operator sends bounded batches; one whole-site test upload can exceed
    # the edge's transport ceiling as the public assets grow.
    manifest, files = entries[0], entries[1:]
    groups, group, size = [], [], 0
    for entry in files + [manifest]:
        if group and size + len(entry[1]) > 8_000_000:
            groups.append(group)
            group, size = [], 0
        group.append(entry)
        size += len(entry[1])
    if group:
        groups.append(group)
    payloads = [export_module.load_payload(export.export_id, batch) for batch in groups]
    payload = payloads[0]

    def load(site, body, signer):
        assert isinstance(signer, RequestSigner)
        return _fetch(site.port, "POST", "/__edge/admin/files", "baltor.ai",
                      {"Authorization": signer.header("POST", "/__edge/admin/files", body),
                       "Content-Type": "application/octet-stream"}, body)
    tampered = payload[:-1] + bytes([payload[-1] ^ 1])
    with local_site(root / "edge-kv", None, export.export_id, "http://127.0.0.1:9", node=node,
                    loader_keys=keys) as site:
        refused = [load(site, tampered, admin)[0], load(site, payload, stranger)[0]]
        empty = not any(site.kv.iterdir())
        loaded = [load(site, batch, admin) for batch in payloads]
        pages = [_fetch(site.port, "GET", address, "baltor.ai") for address in ("/", "/pricing", "/docs")]
        expected = [export.files[export.manifest["files"][address]["sha256"]] for address in ("/", "/pricing", "/docs")]
        check("a_signed_load_into_kv_serves_the_same_pages_and_a_changed_or_foreign_load_writes_nothing",
              refused == [400, 401] and empty and all(answer[0] == 200 for answer in loaded)
              and [answer[2] for answer in pages] == expected and all(answer[0] == 200 for answer in pages))
    with local_site(root / "edge-kv-off", None, export.export_id, "http://127.0.0.1:9", node=node) as site:
        check("without_loader_keys_the_load_route_does_not_exist", load(site, payload, admin)[0] == 404)


def _proxy_safety_checks(check, root, node):
    """Exercise hostile inputs without a real upstream: the fetch stub records every attempted effect."""
    import subprocess
    script = r'''
import { pathToFileURL } from "node:url";
const { handle } = await import(pathToFileURL(process.argv[2]));
const env = { ORIGIN: "https://origin.example.invalid", ORIGIN_MODE: "all", EXPORT_ID: "test" };
const rows = [];
let calls = [];
globalThis.fetch = async (request) => {
  calls.push({ url: request.url, headers: Object.fromEntries(request.headers),
    body: await request.text(), redirect: request.redirect });
  return new Response("origin", { headers: { "cache-control": "public, max-age=900" } });
};
const record = (name, passed) => rows.push({ name, passed: Boolean(passed) });
let result = await handle(new Request("https://edge.example.invalid//other.example.invalid/api?x=1", {
  headers: { authorization: "fixture-credential", cookie: "fixture=cookie" }
}), env);
record("network_path_cannot_change_the_configured_origin", calls.length === 1 &&
  new URL(calls[0].url).origin === env.ORIGIN &&
  new URL(calls[0].url).pathname === "//other.example.invalid/api" && calls[0].headers.authorization === "fixture-credential");
record("dynamic_answers_are_never_cached", result.headers.get("cache-control") === "no-store");
calls = [];
await handle(new Request("https://edge.example.invalid/api", { method: "POST", body: "small",
  headers: { connection: "x-remove", "x-remove": "untrusted", "content-type": "text/plain" } }), env);
record("bounded_body_is_forwarded_once_with_manual_redirects_and_no_connection_tokens", calls.length === 1 &&
  calls[0].body === "small" && calls[0].redirect === "manual" && !calls[0].headers["x-remove"] && !calls[0].headers.connection);
calls = [];
result = await handle(new Request("https://edge.example.invalid/api", { method: "POST", body: "small",
  headers: { "content-length": "1048577" } }), env);
record("oversized_declared_body_is_refused_before_origin", result.status === 413 && calls.length === 0);
calls = [];
let cancelled = false, emitted = false;
const stream = new ReadableStream({
  pull(controller) { if (!emitted) { emitted = true; controller.enqueue(new Uint8Array(1048577)); } else controller.close(); },
  cancel() { cancelled = true; }
}, { highWaterMark: 0 });
result = await handle(new Request("https://edge.example.invalid/api", { method: "POST", body: stream, duplex: "half" }), env);
record("oversized_actual_stream_is_cancelled_without_any_origin_effect", result.status === 413 && calls.length === 0 && cancelled);
calls = [];
globalThis.fetch = async (request) => { calls.push(request.url); throw new Error("unknown upstream outcome"); };
result = await handle(new Request("https://edge.example.invalid/api", { method: "POST", body: "bounded" }), env);
const failed = await result.json();
record("uncertain_origin_effect_is_never_retried_or_claimed_uncommitted", calls.length === 1 && result.status === 503 &&
  failed.automatic_retry === false && failed.effect_commitment === "not_asserted");
let writes = 0;
result = await handle(new Request("https://edge.example.invalid/__edge/admin/files", { method: "POST", body: "small",
  headers: { "content-length": "10485761" } }), { ...env, LOADER_KEYS: "[]", SITE: { put() { writes++; } } });
record("oversized_admin_load_is_refused_before_storage", result.status === 413 && writes === 0);
process.stdout.write(JSON.stringify(rows));
'''
    source = site_worker()

    def run(name, content):
        worker = Path(root) / f"proxy-safety-{name}.mjs"
        worker.write_text(content, "utf-8")
        answer = subprocess.run([node, "--input-type=module", "-", str(worker)], input=script,
                                capture_output=True, text=True, timeout=30)
        if answer.returncode:
            raise AssertionError(answer.stderr)
        return {row["name"]: row["passed"] for row in json.loads(answer.stdout)}

    for name, passed in run("baseline", source).items():
        check(name, passed)
    controls = (
        ("origin", 'const target = new URL(env.ORIGIN);\n  target.pathname = url.pathname;\n  target.search = url.search;',
         'const target = new URL(url.pathname + url.search, env.ORIGIN);',
         "network_path_cannot_change_the_configured_origin"),
        ("body", 'if (size > maximum) {', 'if (false) {',
         "oversized_actual_stream_is_cancelled_without_any_origin_effect"),
        ("cache", 'answer.headers.set("cache-control", "no-store");', '', "dynamic_answers_are_never_cached"),
    )
    for name, old, new, predicate in controls:
        if source.count(old) != 1:
            raise AssertionError(f"the {name} safety control no longer finds its guard")
        check(f"removed_edge_{name}_guard_is_detected", not run(name, source.replace(old, new))[predicate])


def run_checks(check, root, *, node=None):
    """Run the kit; returns the requirements of the checks that could not run here, empty when all ran."""
    _export_checks(check)
    node = node or node_runtime()
    if node is None:
        from .catalogue_d1_index_checks import NODE_REQUIREMENT
        return [NODE_REQUIREMENT]
    _site_checks(check, Path(root), node)
    _loader_checks(check, Path(root), node, export_module.export_site(include_model_details=False, hosts=HOSTS))
    _proxy_safety_checks(check, Path(root), node)
    return []


def self_test():
    tests = []

    def check(name, passed):
        tests.append({"test": name, "passed": bool(passed),
                      "detail": "the edge Worker's own source under Node against the real service on loopback"})
    with tempfile.TemporaryDirectory(prefix="static-site-edge-") as folder:
        missing = run_checks(check, Path(folder))
    for requirement in missing:
        tests.append({"test": "the_site_edge_worker_checks_that_need_node", "passed": None, "not_tested": True,
                      "outcome": "NOT_APPLICABLE", "missing_optional_dependencies": [requirement],
                      "detail": "the export checks ran; the Worker checks need Node"})
    return {"tests": tests, "passed": sum(1 for row in tests if row["passed"]), "total": len(tests),
            "all_passed": all(row["passed"] is not False for row in tests)}
