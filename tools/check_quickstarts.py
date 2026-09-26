"""Run each quickstart's documented connection, search and download against the live service.

Kind: development check of the hosted service, written for a nightly job.

Each quickstart page under ``docs/guides/`` tells one harness how to connect,
search and download. This check reads those pages and runs the same steps
against the running service, in the shape each harness sends them:

- Claude Code, Codex and OpenCode speak the Model Context Protocol over
  streamable HTTP at ``/mcp``: ``initialize``, ``notifications/initialized``,
  ``tools/list``, then ``tools/call`` for ``intelligence_search`` and
  ``provisioning_read``.
- Pi connects through the served extension, which asks the direct interface:
  ``/api/v1/session``, ``/api/v1/capabilities``, ``/api/v1/retrieval`` in the
  search mode the extension sends, a ``manifest`` by identity through
  ``/api/v1/provisioning`` and ``/api/v1/download``. A unit test holds the
  mode and the manifest record type to the extension source.
- The Baltor Harness page uses the direct interface with ``curl``:
  ``/api/v1/session``, then the page's own ``/api/v1/retrieval`` and
  ``/api/v1/download`` request bodies, sent as the page shows them with only
  the chosen identity, its digest and a new ``request_id`` filled in. A page
  whose download does not bind ``expected_digest`` and ``request_id`` fails
  before anything is sent.

Three page steps come first and hold the page itself to what the service
publishes: every service address in its snippets is on the published base,
the page names the first search, and the page shows the configuration and
the verification command of its harness exactly as the Get set up page shows
them. The recipes are read from ``/assets/client-recipes.json`` on the live
service, the record the Get set up page reads, with the endpoint placeholder
filled the way that page fills it. A JSON configuration must parse to the
same value; the Codex table must be the same TOML text, line for line, that
the page renders. A quickstart's identity is the identity of its recipe.

For every quickstart the record says, separately, whether each page step
passed, whether the service answered the connection, listed its operations,
answered the search, delivered the body and whether the delivered bytes carry
the digest the search promised. A quickstart passes only when every step
passes: a connection without a retrieval is not a pass. Each download uses a
new ``request_id``, so each is one measured unit on the diagnostic account.
No body text is kept.

Both paths answer a ``service_http_result/v1`` record whose ``result`` holds
the session, retrieval, manifest or body record; a protocol tool carries that
record as its structured content. The first run on September 26, 2026 read
the hits off the protocol wrapper instead of its ``result`` and reported no
hit for the three protocol quickstarts while the direct interface found five.
An answer that is not that wrapper now fails its step by name on either path,
and the unit tests hold the fixture to the live shape.

A request that does not complete, because the service cannot be reached, the
answer is cut off, it times out or the service answers with a redirect, fails
the step it belongs to with the method, the address and the reason, and the
run goes on to the next quickstart, so a run during an outage still writes its
dated record. A download whose answer never arrived may still have been
measured by the service, so its ``request_id`` is kept among the request
identities not confirmed instead of being counted either way.

The diagnostic key resolves from this workstation's system keyring through
``tools/operator_credentials.py``. It is sent only in the request header and
never printed, and any error text is scrubbed before it is recorded.

Run it once, writing a dated record under ``artifacts/quickstart-checks/``:

    PYTHONPATH=src:tools python tools/check_quickstarts.py --origin https://baltor.ai

The exit status is zero when every quickstart passed.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import http.client
import json
from pathlib import Path
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]
RECORD_TYPE = "quickstart_live_check/v1"
RECORD_DIRECTORY = "artifacts/quickstart-checks"
#: The first search every quickstart documents. A page that does not name it in a code span fails its page step.
QUERY = "review inputs"
PROTOCOL_PATH = "/mcp"
RETRIEVAL_REQUEST = "service_retrieval_request/v2"
PROVISIONING_REQUEST = "service_provisioning_request/v2"
SEARCH_TOOL, READ_TOOL = "intelligence_search", "provisioning_read"
REQUIRED_TOOLS = (SEARCH_TOOL, READ_TOOL)
DIGEST_HEADER, RECORD_HEADER = "x-content-sha256", "x-loop-engine-record-type"
DOWNLOAD_RECORD = "service_download/v1"
MANIFEST_RECORD = "provisioning_manifest/v3"
#: The search mode the served Pi extension sends, its SEARCH_MODE; a unit test holds the two to each other.
EXTENSION_SEARCH_MODE = "hybrid"
#: How many results the check asks for when the client, not the page, picks the number.
SEARCH_RESULTS = 5
#: The JSON body of a documented curl command, written between single quotes after -d.
CURL_BODY = re.compile(r"-d\s+'(\{[^']*\})'")
#: The values the Baltor Harness page asks the reader to replace in its download command.
PAGE_PLACEHOLDERS = {"identity": "ITEM-IDENTITY", "expected_digest": "SELECTED-DIGEST"}
#: The record every answer of the service is wrapped in, on both paths; its `result` holds the record asked for.
RESULT_WRAPPER = "service_http_result/v1"
#: The reviewed connection recipes the Get set up page shows, as the website serves them.
RECIPES_ADDRESS = "/assets/client-recipes.json"
RECIPES_RECORD = "website_client_recipes/v2"
#: A recipe value that the Get set up page replaces with its own origin followed by the protocol path.
ENDPOINT_PLACEHOLDER = "{{ENDPOINT}}"
#: A TOML key the Get set up page writes bare; any other key is written as a quoted string.
TOML_BARE_KEY = re.compile(r"^[A-Za-z0-9_-]+$")
#: The three ways a harness reaches the service, as the pages document them.
PROTOCOL, EXTENSION, DIRECT = "protocol", "extension", "direct"
#: An address in a snippet names the service when its path is one of these. Other addresses, such as a schema on
#: another site or the repository on GitHub, are outside the service and are not held to the published base.
SERVICE_PATHS = ("/mcp", "/api/", "/assets/")
ADDRESS = re.compile(r"https?://[^\s\"'`<>)\]]+")
FENCE = re.compile(r"^```")
CODE_SPAN = re.compile(r"`([^`\n]+)`")
DEFAULT_CREDENTIAL = "baltor-pilot-owner"
TIMEOUT = 60


@dataclass(frozen=True)
class Quickstart:
    #: The identity of the quickstart and of its recipe in the published client recipes.
    id: str
    harness: str
    page: str
    wire_path: str


QUICKSTARTS = (
    Quickstart("claude-code", "Claude Code", "docs/guides/quickstart-claude-code.md", PROTOCOL),
    Quickstart("codex", "Codex", "docs/guides/quickstart-codex.md", PROTOCOL),
    Quickstart("opencode", "OpenCode", "docs/guides/quickstart-opencode.md", PROTOCOL),
    Quickstart("pi", "Pi", "docs/guides/quickstart-pi.md", EXTENSION),
    Quickstart("baltor-harness", "Baltor Harness", "docs/guides/quickstart-baltor-harness.md", DIRECT),
)


class StepFailed(Exception):
    """One documented step did not do what the page says. The message is the detail recorded."""


class TransportFailed(StepFailed):
    """A request did not complete: no connection, a timeout, a cut-off answer or a refused redirect."""


class RefuseRedirect(urllib.request.HTTPRedirectHandler):
    """A redirect is never followed: the key would travel to the new address, and a sign-in page is not an answer."""

    def redirect_request(self, request, answer, code, message, headers, new_address):
        raise TransportFailed("redirect_refused: {} to {}".format(code, new_address[:120]))


def snippet_addresses(text: str) -> list:
    """Every web address inside the page's fenced blocks and code spans, in order."""
    found, inside = [], False
    for line in text.splitlines():
        if FENCE.match(line):
            inside = not inside
            continue
        if inside:
            found.extend(ADDRESS.findall(line))
        else:
            for span in CODE_SPAN.findall(line):
                found.extend(ADDRESS.findall(span))
    return found


def foreign_service_addresses(addresses, published_base: str) -> list:
    """The addresses that name the service and are not on the published base."""
    base = published_base.rstrip("/")
    foreign = []
    for address in addresses:
        path = urllib.parse.urlsplit(address).path or "/"
        if path.startswith(SERVICE_PATHS) and not address.startswith(base + "/"):
            foreign.append(address)
    return foreign


def documents_first_search(text: str) -> bool:
    """The page names the first search, in a code span, exactly as this check sends it."""
    return any(span.strip() == QUERY for span in CODE_SPAN.findall(text))


def fenced_blocks(text: str) -> list:
    """Every fenced block of the page as its language and its text, in order."""
    blocks, language, lines, inside = [], "", [], False
    for line in text.splitlines():
        if FENCE.match(line):
            if inside:
                blocks.append((language, "\n".join(lines)))
                lines = []
            else:
                language = line[3:].strip()
            inside = not inside
            continue
        if inside:
            lines.append(line)
    return blocks


def documented_request(text: str, path: str):
    """The JSON body of the page's curl command for one service address, exactly as the page shows it, or None."""
    for _language, content in fenced_blocks(text):
        for line in content.splitlines():
            found = CURL_BODY.search(line) if "curl" in line and path in line else None
            if found:
                try:
                    body = json.loads(found.group(1))
                except ValueError:
                    return None
                return body if isinstance(body, dict) else None
    return None


def filled(value, endpoint: str):
    """A recipe configuration with each placeholder value replaced by the endpoint, as the Get set up page fills it."""
    if value == ENDPOINT_PLACEHOLDER:
        return endpoint
    if isinstance(value, list):
        return [filled(item, endpoint) for item in value]
    if isinstance(value, dict):
        return {name: filled(item, endpoint) for name, item in value.items()}
    return value


def toml_text(table: dict, path: tuple = ()) -> str:
    """The TOML text the Get set up page renders for a configuration: a table's settings first, then each inner table."""
    def key(name):
        return name if TOML_BARE_KEY.match(name) else json.dumps(name, ensure_ascii=False)
    own = [key(name) + " = " + json.dumps(item, ensure_ascii=False)
           for name, item in table.items() if not isinstance(item, dict)]
    blocks = [("[" + ".".join(key(part) for part in path) + "]\n" if path else "") + "\n".join(own)] if own else []
    blocks += [toml_text(item, path + (name,)) for name, item in table.items() if isinstance(item, dict)]
    return "\n\n".join(blocks)


def canonical(value) -> str:
    """One text for one JSON value, so that `true` and `1` stay different."""
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def published_recipe(recipes, identity: str):
    """The recipe the Get set up page shows for one harness, from the record the service serves, or None."""
    if not isinstance(recipes, dict) or recipes.get("record_type") != RECIPES_RECORD:
        return None
    return next((recipe for recipe in recipes.get("recipes") or []
                 if isinstance(recipe, dict) and recipe.get("id") == identity), None)


def recipe_disagreement(text: str, recipe: dict, endpoint: str) -> str:
    """Why the page does not show this recipe as the Get set up page does, or an empty text when it does."""
    wanted = filled(recipe.get("configuration"), endpoint)
    blocks = fenced_blocks(text)
    if recipe.get("format") == "toml":
        rendered = toml_text(wanted) if isinstance(wanted, dict) else None
        shown = rendered is not None and any(
            language == "toml" and content.strip() == rendered for language, content in blocks)
    else:
        shown = False
        for language, content in blocks:
            if language != "json":
                continue
            try:
                shown = canonical(json.loads(content)) == canonical(wanted)
            except ValueError:
                continue
            if shown:
                break
    if not shown:
        return "no {} block holds the {} configuration that Get set up shows".format(recipe.get("format"), recipe.get("id"))
    command = recipe.get("verification_command")
    if not any(line.strip() == command for _language, content in blocks for line in content.splitlines()):
        return "no block shows the verification command {!r}".format(command)
    return ""


def protocol_result(status: int, content_type: str, body: bytes, request_id):
    """The JSON-RPC result of one protocol answer, whether it came as JSON or as event-stream frames."""
    media = (content_type or "").split(";")[0].strip()
    text = body.decode("utf-8", "replace")
    try:
        if media == "application/json" or text.lstrip().startswith("{"):
            messages = [json.loads(text)]
        else:
            messages = []
            for frame in text.replace("\r\n", "\n").split("\n\n"):
                data = "\n".join(line[5:].lstrip() for line in frame.split("\n") if line.startswith("data:"))
                if data.strip():
                    messages.append(json.loads(data))
    except ValueError:
        raise StepFailed(f"the protocol answer is not JSON (status {status})") from None
    for message in messages:
        if isinstance(message, dict) and message.get("id") == request_id:
            if message.get("error"):
                error = message["error"]
                raise StepFailed("protocol error {} {}".format(error.get("code"), str(error.get("message"))[:120]))
            if not isinstance(message.get("result"), dict):
                raise StepFailed("the protocol answer carries no result")
            return message["result"]
    raise StepFailed(f"no protocol answer matched the request (status {status})")


class Service:
    """The live service as one harness reaches it: a bearer key, an origin and a count of calls."""

    def __init__(self, origin: str, key: str, opener=None):
        self.origin, self._key = origin.rstrip("/"), key
        self.opener = opener or urllib.request.build_opener(urllib.request.ProxyHandler({}), RefuseRedirect())
        self.calls = 0

    def exchange(self, path: str, body=None, headers=None):
        """Status, lower-cased headers and bytes of one request; a refused request is answered, not raised."""
        fields = {"Accept": "application/json", "Authorization": "Bearer " + self._key, **(headers or {})}
        data = None
        if body is not None:
            fields["Content-Type"] = "application/json"
            data = json.dumps(body).encode("utf-8")
        self.calls += 1
        request = urllib.request.Request(self.origin + path, data, fields)
        verb = "GET" if data is None else "POST"
        try:
            try:
                response = self.opener.open(request, timeout=TIMEOUT)
            except urllib.error.HTTPError as error:
                response = error
            with response:
                return response.status, {name.lower(): value for name, value in response.headers.items()}, response.read(8_000_000)
        except TransportFailed as failure:
            raise TransportFailed(f"{verb} {path} did not complete: {failure}") from None
        except (OSError, http.client.HTTPException) as error:
            reason = scrub("{}: {}".format(type(error).__name__, error), self._key)[:160]
            raise TransportFailed(f"{verb} {path} did not complete: {reason}") from None

    def json(self, path: str, body=None):
        status, _headers, raw = self.exchange(path, body)
        try:
            return status, json.loads(raw or b"null")
        except ValueError:
            return status, None

    def protocol(self, message: dict, version: str = None):
        """One protocol message. An `initialize` names its version in the message, every other one in the header."""
        headers = {"Accept": "application/json, text/event-stream"}
        if version:
            headers["MCP-Protocol-Version"] = version
        status, headers_out, raw = self.exchange(PROTOCOL_PATH, message, headers)
        if "id" not in message:
            return status, None
        if status != 200:
            raise StepFailed(f"{message['method']} answered {status}: {scrub(raw.decode('utf-8', 'replace')[:160], self._key)}")
        return status, protocol_result(status, headers_out.get("content-type", ""), raw, message["id"])


def scrub(text: str, key: str) -> str:
    return text.replace(key, "[credential suppressed]") if key else text


def result_of(answer):
    return answer.get("result") if isinstance(answer, dict) else None


def wrapped_result(status: int, answer, what: str) -> dict:
    """The record inside one direct answer: the `result` of its `service_http_result/v1` wrapper."""
    if status != 200:
        raise StepFailed(f"the {what} answered {status}")
    if not isinstance(answer, dict) or answer.get("record_type") != RESULT_WRAPPER or not isinstance(answer.get("result"), dict):
        named = answer.get("record_type") if isinstance(answer, dict) else type(answer).__name__
        raise StepFailed("the {} answered {!r}, not a {} record with a result".format(what, named, RESULT_WRAPPER))
    return answer["result"]


def choose_hit(hits, limit: int):
    """The first hit whose body this account may read and that fits the limit the path can deliver."""
    for hit in hits:
        reference = hit.get("reference") or {}
        if hit.get("body_allowed") is True and isinstance(hit.get("size_bytes"), int) \
                and hit["size_bytes"] <= limit and reference.get("identity") and reference.get("body_digest"):
            return hit
    return None


def new_request_id(quickstart: Quickstart, stamp: str) -> str:
    return "quickstart-{}-{}-{}".format(quickstart.id, stamp, uuid.uuid4().hex[:12])


def run_quickstart(service: Service, quickstart: Quickstart, page_text: str, published_base: str,
                   capabilities: dict, stamp: str, recipes=None) -> dict:
    """Every documented step of one quickstart, in order, stopping at the first the service refuses."""
    steps, facts = [], {"request_id": None, "identity": None, "digest_prefix": None, "hits": 0,
                        "catalogue_release": None}
    calls_before = service.calls

    def step(name, passed, detail=""):
        steps.append({"name": name, "passed": bool(passed), "detail": detail})

    foreign = foreign_service_addresses(snippet_addresses(page_text), published_base)
    step("page_names_the_published_base", not foreign, "; ".join(foreign) if foreign else published_base)
    step("page_documents_the_first_search", documents_first_search(page_text), QUERY)
    recipe = published_recipe(recipes, quickstart.id)
    if recipe is None:
        step("page_matches_the_published_recipe", False, f"the service publishes no {quickstart.id} recipe")
    else:
        problem = recipe_disagreement(page_text, recipe, published_base + PROTOCOL_PATH)
        step("page_matches_the_published_recipe", not problem,
             problem or "the {} recipe reviewed {}".format(quickstart.id, recipes.get("reviewed_at")))
    try:
        if quickstart.wire_path == PROTOCOL:
            _run_protocol(service, quickstart, capabilities, stamp, step, facts)
        elif quickstart.wire_path == EXTENSION:
            _run_direct(service, quickstart, capabilities, stamp, step, facts, extension=True, page_text=page_text)
        else:
            _run_direct(service, quickstart, capabilities, stamp, step, facts, extension=False, page_text=page_text)
    except StepFailed as failure:
        steps[-1] = {**steps[-1], "passed": False, "detail": scrub(str(failure), service._key)[:300]}
    rows = _collapse(steps)
    return {"id": quickstart.id, "harness": quickstart.harness, "page": quickstart.page,
            "wire_path": quickstart.wire_path, "steps": rows, **facts,
            "http_calls": service.calls - calls_before, "passed": bool(rows) and all(row["passed"] for row in rows)}


def _run_protocol(service, quickstart, capabilities, stamp, step, facts):
    handshake = (capabilities.get("protocol") or {}).get("handshake_versions") or []
    if not handshake:
        step("connected", False, "the service names no handshake protocol version")
        raise StepFailed("the service names no handshake protocol version")
    version = handshake[0]
    step("connected", False, "initialize")
    _status, initialized = service.protocol({"jsonrpc": "2.0", "id": "qs-init", "method": "initialize",
        "params": {"protocolVersion": version, "capabilities": {},
                   "clientInfo": {"name": "baltor-quickstart-check", "version": "1.0.0"}}})
    if initialized.get("protocolVersion") != version:
        raise StepFailed("initialize answered version {!r}, not {!r}".format(initialized.get("protocolVersion"), version))
    status, _none = service.protocol({"jsonrpc": "2.0", "method": "notifications/initialized"}, version)
    if status not in (200, 202):
        raise StepFailed(f"notifications/initialized answered {status}")
    step_pass(step, "connected", f"protocol {version}")
    step("listed", False, "tools/list")
    _status, listed = service.protocol({"jsonrpc": "2.0", "id": "qs-list", "method": "tools/list", "params": {}}, version)
    names = [tool.get("name") for tool in listed.get("tools") or [] if isinstance(tool, dict)]
    missing = [name for name in REQUIRED_TOOLS if name not in names]
    if missing:
        raise StepFailed("the tool list lacks " + ", ".join(missing))
    step_pass(step, "listed", f"{len(names)} tools")
    step("searched", False, QUERY)
    _status, called = service.protocol({"jsonrpc": "2.0", "id": "qs-search", "method": "tools/call",
        "params": {"name": SEARCH_TOOL, "arguments": {"query": QUERY, "top_n": SEARCH_RESULTS}}}, version)
    found = _tool_output(called, SEARCH_TOOL)
    hits = found.get("hits") if isinstance(found, dict) else None
    if not isinstance(hits, list) or not hits:
        raise StepFailed("the search returned no hit")
    if found.get("bodies_loaded") is not False:
        raise StepFailed("the search loaded a body")
    facts["hits"], facts["catalogue_release"] = len(hits), found.get("catalogue_release")
    limit = int((capabilities.get("delivery") or {}).get("inline_body_bytes") or 0)
    hit = choose_hit(hits, limit)
    if hit is None:
        raise StepFailed(f"no hit is readable within the inline limit of {limit} bytes")
    step_pass(step, "searched", f"{len(hits)} hits")
    reference = hit["reference"]
    facts["identity"], facts["request_id"] = reference["identity"], new_request_id(quickstart, stamp)
    step("downloaded", False, reference["identity"])
    _status, read = service.protocol({"jsonrpc": "2.0", "id": "qs-read", "method": "tools/call",
        "params": {"name": READ_TOOL, "arguments": {"identity": reference["identity"], "request_id": facts["request_id"],
                                                     "expected_digest": reference["body_digest"]}}}, version)
    body_record = _tool_output(read, READ_TOOL)
    if not isinstance(body_record, dict) or not isinstance(body_record.get("body"), str):
        raise StepFailed("the read returned no body")
    if body_record.get("identity") != reference["identity"]:
        raise StepFailed("the read answered another identity")
    step_pass(step, "downloaded", "{} bytes, metered {}".format(len(body_record["body"].encode("utf-8")), body_record.get("metered")))
    actual = hashlib.sha256(body_record["body"].encode("utf-8")).hexdigest()
    facts["digest_prefix"] = actual[:12]
    step("digest_matches", actual == reference["body_digest"] == body_record.get("digest"),
         "sha256 {}… promised {}…".format(actual[:12], reference["body_digest"][:12]))


def _tool_output(called: dict, tool: str):
    """The record inside one protocol tool answer: the `result` of its `service_http_result/v1` wrapper."""
    if called.get("isError"):
        raise StepFailed("{} was refused: {}".format(tool, json.dumps(called.get("structuredContent"))[:160]))
    output = called.get("structuredContent")
    if output is None:
        for item in called.get("content") or []:
            if isinstance(item, dict) and item.get("type") == "text":
                try:
                    output = json.loads(item["text"])
                except ValueError:
                    raise StepFailed(f"{tool} answered text that is not JSON") from None
                break
    if not isinstance(output, dict) or output.get("record_type") != RESULT_WRAPPER:
        named = output.get("record_type") if isinstance(output, dict) else type(output).__name__
        raise StepFailed("{} answered {!r}, not a {} record".format(tool, named, RESULT_WRAPPER))
    if not isinstance(output.get("result"), dict):
        raise StepFailed(f"{tool} answered a {RESULT_WRAPPER} record with no result")
    return output["result"]


def _run_direct(service, quickstart, capabilities, stamp, step, facts, *, extension: bool, page_text: str):
    step("connected", False, "/api/v1/session")
    status, session = service.json("/api/v1/session")
    record = wrapped_result(status, session, "session")
    if record.get("record_type") != "service_session/v1":
        raise StepFailed("the session answered {!r}".format(record.get("record_type")))
    scopes = (record.get("principal") or {}).get("scopes") or []
    step_pass(step, "connected", "service_session/v1")
    step("listed", False, "/api/v1/capabilities")
    if extension:
        delivery, retrieval = capabilities.get("delivery") or {}, capabilities.get("retrieval") or {}
        if delivery.get("download_endpoint") != "/api/v1/download" or delivery.get("body_format") != "utf8_text":
            raise StepFailed("the capabilities name another delivery than the extension expects")
        if retrieval.get("request_record_type") != RETRIEVAL_REQUEST:
            raise StepFailed("the capabilities name another search request version than the page")
        step_pass(step, "listed", "download at /api/v1/download, search " + RETRIEVAL_REQUEST)
    else:
        missing = [scope for scope in ("provisioning:metadata", "provisioning:read") if scope not in scopes]
        if missing:
            raise StepFailed("the token lacks " + ", ".join(missing))
        step_pass(step, "listed", "scopes " + ", ".join(sorted(scopes)))
    step("searched", False, QUERY)
    if extension:
        ceiling = (capabilities.get("limits") or {}).get("search_results")
        top_n = min(SEARCH_RESULTS, ceiling) if isinstance(ceiling, int) and ceiling > 0 else SEARCH_RESULTS
        search = {"record_type": RETRIEVAL_REQUEST, "query": QUERY, "mode": EXTENSION_SEARCH_MODE, "top_n": top_n}
    else:
        search = documented_request(page_text, "/api/v1/retrieval")
        if search is None:
            raise StepFailed("the page shows no curl search request with a JSON body")
        if search.get("query") != QUERY:
            raise StepFailed("the page's search request does not ask for {!r}".format(QUERY))
    status, found = service.json("/api/v1/retrieval", search)
    answer = wrapped_result(status, found, "search")
    hits = answer.get("hits")
    if not isinstance(hits, list) or not hits:
        raise StepFailed(f"the search answered {status} with no hit")
    if answer.get("bodies_loaded") is not False:
        raise StepFailed("the search loaded a body")
    facts["hits"], facts["catalogue_release"] = len(hits), answer.get("catalogue_release")
    limit = int((capabilities.get("delivery") or {}).get("download_bytes") or 0)
    hit = choose_hit(hits, limit)
    if hit is None:
        raise StepFailed(f"no hit is readable within the download limit of {limit} bytes")
    step_pass(step, "searched", f"{len(hits)} hits")
    reference = hit["reference"]
    facts["identity"] = reference["identity"]
    if extension:
        step("manifest_matches", False, reference["identity"])
        status, shown = service.json("/api/v1/provisioning", {"record_type": PROVISIONING_REQUEST, "operation": "manifest",
                                                              "identity": reference["identity"]})
        manifest_record = wrapped_result(status, shown, "manifest")
        if manifest_record.get("record_type") != MANIFEST_RECORD or manifest_record.get("identity") != reference["identity"]:
            raise StepFailed("the manifest is not a {} record for {}".format(MANIFEST_RECORD, reference["identity"]))
        if manifest_record.get("digest") != reference["body_digest"]:
            raise StepFailed("the manifest answered another digest")
        step_pass(step, "manifest_matches", reference["body_digest"][:12] + "…")
    step("downloaded", False, reference["identity"])
    if extension:
        download = {"record_type": PROVISIONING_REQUEST, "operation": "read", "identity": reference["identity"],
                    "expected_digest": reference["body_digest"]}
    else:
        download = documented_request(page_text, "/api/v1/download")
        if download is None:
            raise StepFailed("the page shows no curl download request with a JSON body")
        unbound = [field for field, placeholder in PAGE_PLACEHOLDERS.items() if download.get(field) != placeholder]
        unbound += [] if download.get("request_id") else ["request_id"]
        if unbound:
            raise StepFailed("the page's download request does not bind " + ", ".join(unbound))
        download = {**download, "identity": reference["identity"], "expected_digest": reference["body_digest"]}
    facts["request_id"] = new_request_id(quickstart, stamp)
    status, headers, raw = service.exchange("/api/v1/download", {**download, "request_id": facts["request_id"]})
    if status != 200:
        raise StepFailed(f"the download answered {status}: {scrub(raw.decode('utf-8', 'replace')[:160], service._key)}")
    if headers.get(RECORD_HEADER) != DOWNLOAD_RECORD:
        raise StepFailed("the download names another record than " + DOWNLOAD_RECORD)
    step_pass(step, "downloaded", f"{len(raw)} bytes")
    actual = hashlib.sha256(raw).hexdigest()
    facts["digest_prefix"] = actual[:12]
    step("digest_matches", actual == reference["body_digest"] == headers.get(DIGEST_HEADER),
         "sha256 {}… promised {}… header {}…".format(actual[:12], reference["body_digest"][:12], (headers.get(DIGEST_HEADER) or "")[:12]))


def step_pass(step, name, detail):
    """Add the passed row of one step; `_collapse` keeps it in place of the pending row."""
    step(name, True, detail)


def _collapse(steps: list) -> list:
    """One row for each step: a pending row is replaced by the row that decided it."""
    rows = {}
    for row in steps:
        rows[row["name"]] = row
    return list(rows.values())


def run_all(origin: str, key: str, *, published_base: str = None, repository: Path = ROOT, opener=None,
            page_texts: dict = None, now: datetime = None, account: str = "") -> dict:
    """Every quickstart against one service, as one typed record."""
    now = now or datetime.now(timezone.utc)
    stamp = now.strftime("%Y%m%d")
    published_base = (published_base or origin).rstrip("/")
    service = Service(origin, key, opener)
    status, answer, capabilities_error = _fetch(service, "/api/v1/capabilities")
    capabilities = result_of(answer) or {}
    recipes_status, recipes, recipes_error = _fetch(service, RECIPES_ADDRESS)
    if recipes_status != 200 or not isinstance(recipes, dict):
        recipes = None
    rows = []
    for quickstart in QUICKSTARTS:
        if page_texts and quickstart.id in page_texts:
            text = page_texts[quickstart.id]
        else:
            path = repository / quickstart.page
            text = path.read_text(encoding="utf-8") if path.is_file() else ""
        rows.append(run_quickstart(service, quickstart, text, published_base, capabilities, stamp, recipes))
    downloads = [row["request_id"] for row in rows if _delivered(row)]
    #: Sent but not delivered: refused, cut off or unanswered. A refusal is not measured; a cut-off answer may be.
    not_confirmed = [row["request_id"] for row in rows if row["request_id"] and not _delivered(row)]
    return {"record_type": RECORD_TYPE, "checked_at": now.isoformat(), "origin": origin,
            "published_base": published_base, "account": account, "query": QUERY,
            "capabilities_status": status, "capabilities_error": capabilities_error,
            "recipes_status": recipes_status, "recipes_error": recipes_error,
            "recipes_record_type": (recipes or {}).get("record_type"),
            "recipes_reviewed_at": (recipes or {}).get("reviewed_at"),
            "catalogue_release": next((row["catalogue_release"] for row in rows if row["catalogue_release"]), None),
            "protocol_versions": (capabilities.get("protocol") or {}).get("versions"),
            "served_items": (capabilities.get("library") or {}).get("served_items"),
            "quickstarts": rows, "passed": all(row["passed"] for row in rows),
            "quickstarts_passed": sum(row["passed"] for row in rows), "quickstarts_planned": len(QUICKSTARTS),
            "usage_records_added": len(downloads), "request_ids": downloads,
            "request_ids_not_confirmed": not_confirmed,
            "http_calls": service.calls, "physical_model_calls": 0,
            "credential_printed": False, "body_text_kept": False,
            "checker_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}


def _fetch(service: Service, path: str):
    """Status, JSON answer and the reason a request did not complete, which stays None when it did."""
    try:
        status, answer = service.json(path)
    except TransportFailed as failure:
        return None, None, scrub(str(failure), service._key)[:300]
    return status, answer, None


def _delivered(row: dict) -> bool:
    return any(step["name"] == "downloaded" and step["passed"] for step in row["steps"])


def record_path(directory: Path, now: datetime) -> Path:
    """A new file for today: the date, then -2, -3 and so on when a record of the day exists already."""
    stem = "quickstart-check-" + now.strftime("%Y-%m-%d")
    candidate, number = directory / (stem + ".json"), 1
    while candidate.exists():
        number += 1
        candidate = directory / f"{stem}-{number}.json"
    return candidate


def write_record(record: dict, directory: Path, now: datetime) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = record_path(directory, now)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(record, stream, indent=1, sort_keys=True, ensure_ascii=False)
        stream.write("\n")
    return path


def summary(record: dict) -> dict:
    return {"passed": record["passed"], "quickstarts_passed": record["quickstarts_passed"],
            "quickstarts_planned": record["quickstarts_planned"], "origin": record["origin"],
            "usage_records_added": record["usage_records_added"],
            "failed": [{"id": row["id"], "step": next((step["name"] for step in row["steps"] if not step["passed"]), None)}
                       for row in record["quickstarts"] if not row["passed"]]}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--origin", required=True, help="The HTTPS origin of the live service, such as https://baltor.ai")
    parser.add_argument("--credential-ref", default=DEFAULT_CREDENTIAL,
                        help="The keyring reference in tools/operator_credentials.json that holds the diagnostic key")
    parser.add_argument("--record-dir", type=Path, default=ROOT / RECORD_DIRECTORY)
    parser.add_argument("--repository", type=Path, default=ROOT)
    arguments = parser.parse_args(argv)
    origin = urllib.parse.urlsplit(arguments.origin)
    if (origin.scheme != "https" or not origin.hostname or origin.username or origin.password
            or origin.path not in ("", "/") or origin.query or origin.fragment):
        parser.error("an HTTPS origin with no path is required")
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import operator_credentials
    references = operator_credentials.references()
    spec = references["api_keys"].get(arguments.credential_ref)
    if spec is None or spec.get("purpose") != "service-access":
        parser.error("the credential reference must name a service-access key")
    try:
        key = operator_credentials.resolve(arguments.credential_ref, data=references)
    except Exception as error:  # noqa: BLE001 - the reason is the sanitized code, never a value
        print(json.dumps({"passed": False, "credential": arguments.credential_ref,
                          "error": type(error).__name__ + ": " + str(error)[:120]}))
        return 2
    now = datetime.now(timezone.utc)
    record = run_all(arguments.origin, key, repository=arguments.repository.resolve(), now=now,
                     account=spec.get("account", ""))
    path = write_record(record, arguments.record_dir, now)
    print(json.dumps({**summary(record), "record": str(path)}))
    return 0 if record["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
