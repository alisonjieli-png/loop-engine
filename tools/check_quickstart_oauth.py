"""Connect Claude Code to the live service the way a customer does: OAuth, a public sign-up account, no key pasted.

Kind: development check of the hosted service, beside tools/check_quickstarts.py, written for a nightly job.

The token quickstarts sign with an operator-issued diagnostic key. A customer who adds ``https://baltor.ai/mcp``
to Claude Code without a header connects through OAuth instead: Claude Code reads the service's 401 challenge,
discovers the protected resource and its authorization server, registers itself, sends the person to the consent
page and exchanges the code for tokens it refreshes. This check runs that path with the installed Claude Code itself
and a checking account made through Baltor's own public sign-up, never a staff account. It makes no model call:
``claude mcp add``, ``login`` and ``list`` connect and authorize without a session.

Steps, in order, each recorded with what decided it:

1. ``account_ready``: the checking account exists. It is made once, with ``--create-account``, by
   ``tools/check_live_account_journeys.mjs --fresh-only``: Get started with a disposable inbox, the emailed link,
   the password and a new sign-in. Its ``fresh_account_journey/v1`` state, mode 0600, stays in the private state
   folder outside the repository and is reused after that.
2. ``challenge_names_the_resource``: a protocol request without a credential is answered 401 with a
   ``WWW-Authenticate`` challenge that names the protected-resource metadata on the published base.
3. ``discovery_matches``: that metadata names the resource and its authorization server, whose metadata offers
   S256 PKCE, dynamic registration of public clients, refresh and revocation.
4. ``claude_code_needs_authentication``: ``claude mcp list`` reports the server as needing authentication.
5. ``claude_code_authorization_requested``: ``claude mcp login baltor --no-browser``, in a pseudo-terminal, prints
   the authorization address: on the published base, the code flow, S256, the exact resource, a loopback redirect,
   only offered scopes, a client identity and a state.
6. ``consented``: ``tools/oauth_consent_browser.mjs`` signs in on the consent page with the checking account and
   allows the connection. The page names the client and the scopes; the redirect carries a code, the same state and
   the issuer, and goes to Claude Code's own loopback listener as a person's browser would. A redirect the listener
   did not take is pasted at Claude Code's prompt, and the record says which way it went.
7. ``claude_code_token_issued``: Claude Code exchanges the code and its credential store holds an access and a
   refresh token for the server; only their presence is recorded.
8. ``claude_code_connected``: ``claude mcp list`` reports the server connected.
9. ``connected``, ``listed``, ``searched``, ``downloaded``, ``digest_matches``: the token quickstart's protocol
   steps from tools/check_quickstarts.py, with the access token Claude Code holds.
10. ``refreshed``: the refresh token rotates the pair, the new access token is accepted and the old refresh token is
    refused when it is used again.
11. ``revoked``: revocation ends the delegation; the access token is refused afterwards. The delegation is revoked
    whenever tokens were issued, even after a failed step, so a run leaves no live grant behind.

The record holds no password, token, code or body text. The checking account takes a founding place when one is
free, as any new account does; the record names its access source.

    PYTHONPATH=src:tools python tools/check_quickstart_oauth.py --origin https://baltor.ai \\
        --state-dir ~/.le-safety/quickstart-oauth [--create-account]

Exit status: 0 when every step passed, 1 when one failed, 2 when the check could not start.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import select
import shutil
import struct
import subprocess
import sys
import termios
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_quickstarts as quickstarts  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RECORD_TYPE = "quickstart_oauth_check/v1"
RECORD_DIRECTORY = "artifacts/quickstart-checks"
SERVER = "baltor"
QUICKSTART = next(item for item in quickstarts.QUICKSTARTS if item.id == "claude-code")
JOURNEY_RECORD = "fresh_account_journey/v1"
ACCOUNT_FILE, CLAUDE_FOLDER, PROJECT_FOLDER, EVIDENCE_FOLDER = "account.json", "claude-config", "project", "evidence"
CHALLENGE = re.compile(r'Bearer\s+resource_metadata="([^"]+)"')
#: The query of an address printed in a terminal: everything up to a space, a quote, an angle bracket or a control code.
ADDRESS_QUERY = r"\?[^\s\"'<>\x07\x1b]+"
#: The only variables a child process inherits: what Claude Code, Node and Chrome need, never a key or a token.
INHERITED_ENVIRONMENT = ("HOME", "PATH", "LANG", "USER", "LOGNAME", "TMPDIR")
#: Terminal control sequences: colours and cursor moves, and operating-system commands such as hyperlinks.
TERMINAL_CODES = re.compile(r"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b[=>()][0-9A-Za-z]?")
#: What Claude Code prints once it waits for the redirect at its prompt.
PASTE_PROMPT = "paste the redirect url"
#: One-time values a transcript may echo, removed before anything is recorded.
SECRET_FIELDS = re.compile(r"((?:code|state|code_challenge|access_token|refresh_token)=)[^&\s\"']+")
ACCESS_PREFIX, REFRESH_PREFIX = "boat_", "bort_"
TIMEOUT = 60
LOGIN_SECONDS = 300
#: How long Claude Code's own listener may take to finish after the browser delivered the redirect to it.
LISTENER_SECONDS = 30
CONSENT_SECONDS = 180


class CheckFailed(Exception):
    """A step did not do what the customer path needs. The message is the detail recorded."""


class RefuseRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, answer, code, message, headers, new_address):
        raise CheckFailed("redirect_refused: {} to {}".format(code, new_address[:120]))


def plain(raw) -> str:
    """Terminal output as text: control sequences removed, carriage returns as line ends."""
    text = raw.decode("utf-8", "replace") if isinstance(raw, (bytes, bytearray)) else raw
    return TERMINAL_CODES.sub("", text).replace("\r\n", "\n").replace("\r", "\n")


def scrubbed(text: str, *secrets) -> str:
    """Text with one-time values and the given secrets removed, safe to record."""
    text = SECRET_FIELDS.sub(r"\1[removed]", text)
    for value in sorted((value for value in secrets if value), key=len, reverse=True):
        text = text.replace(value, "[removed]")
    return text


class Http:
    """Requests without a stored credential: no proxy, no redirect followed, and a count of calls."""

    def __init__(self, opener=None):
        self.opener = opener or urllib.request.build_opener(urllib.request.ProxyHandler({}), RefuseRedirect())
        self.calls = 0

    def request(self, method, url, *, json_body=None, form=None, headers=None):
        fields = {"Accept": "application/json", **(headers or {})}
        data = None
        if json_body is not None:
            data, fields["Content-Type"] = json.dumps(json_body).encode(), "application/json"
        elif form is not None:
            data, fields["Content-Type"] = urllib.parse.urlencode(form).encode(), "application/x-www-form-urlencoded"
        self.calls += 1
        request = urllib.request.Request(url, data=data, headers=fields, method=method)
        try:
            try:
                answer = self.opener.open(request, timeout=TIMEOUT)
            except urllib.error.HTTPError as error:
                answer = error
            with answer:
                return answer.status, {name.lower(): value for name, value in answer.headers.items()}, answer.read(2_000_000)
        except CheckFailed:
            raise
        except (OSError, ValueError) as error:
            raise CheckFailed("{} {} did not complete: {}".format(method, urllib.parse.urlsplit(url).path,
                                                                  type(error).__name__)) from None

    def json(self, method, url, **options):
        status, headers, raw = self.request(method, url, **options)
        try:
            return status, headers, json.loads(raw or b"null")
        except ValueError:
            return status, headers, None


def private_folder(path: Path) -> Path:
    """The state folder: a real directory owned by this user, readable by nobody else, outside the repository."""
    path = path.expanduser().resolve()
    if path == ROOT or ROOT in path.parents:
        raise CheckFailed("the state folder must be outside the repository")
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    held = path.lstat()
    if path.is_symlink() or held.st_uid != os.getuid() or held.st_mode & 0o077:
        raise CheckFailed("the state folder must belong to this user and be readable by nobody else")
    return path


def read_account(path: Path) -> dict:
    """The checking account's facts from its journey state, never its password."""
    held = path.lstat()
    if not path.is_file() or path.is_symlink() or held.st_mode & 0o077 or held.st_uid != os.getuid():
        raise CheckFailed("the account state must be a private regular file")
    state = json.loads(path.read_text(encoding="utf-8"))
    account = state.get("account") or {}
    address = (state.get("fresh") or {}).get("address")
    if (state.get("record_type") != JOURNEY_RECORD or state.get("stage") != "complete"
            or not isinstance(address, str) or not address.startswith("baltor-check-")
            or not isinstance(account.get("tenant_id"), str)):
        raise CheckFailed("the account state is not a completed public sign-up of a checking account")
    created = next((row.get("at") for row in state.get("history") or [] if row.get("event") == "complete"), None)
    return {"tenant_id": account["tenant_id"], "entitlement": account.get("entitlement"),
            "access_source": account.get("access_source"), "signed_up_at": created,
            "authentication_mode": account.get("authentication_mode")}


def create_account(origin: str, folder: Path, node: str, environment: dict, evidence: Path) -> dict:
    """Make the checking account through Baltor's public sign-up with the existing fresh-only journey."""
    report = evidence / "fresh-account-journey.json"
    completed = subprocess.run([node, str(ROOT / "tools/check_live_account_journeys.mjs"), origin, str(report),
                                "--fresh-only"], cwd=ROOT, env={**environment, "BALTOR_JOURNEY_STATE": str(folder / ACCOUNT_FILE)},
                               capture_output=True, text=True, timeout=900)
    summary = completed.stdout.strip().splitlines()[-1:] or [""]
    try:
        outcome = json.loads(summary[0])
    except ValueError:
        outcome = {"all_passed": False, "failures": [scrubbed(completed.stderr[-300:])]}
    if completed.returncode != 0 or not outcome.get("all_passed"):
        raise CheckFailed("the public sign-up journey did not complete: " + ", ".join(outcome.get("failures") or [])[:300])
    return {"journey_report": str(report)}


def inherited_environment() -> dict:
    """The declared variables of this process's environment that a child may see."""
    return {name: os.environ[name] for name in INHERITED_ENVIRONMENT if name in os.environ}


def authorization_address(endpoint: str):
    """The pattern of an authorization address on the endpoint the authorization server publishes."""
    return re.compile(re.escape(endpoint) + ADDRESS_QUERY)


def claude_environment(folder: Path) -> dict:
    """Only what Claude Code needs, with its own configuration folder and no traffic beyond the connection."""
    return {**inherited_environment(), "CLAUDE_CONFIG_DIR": str(folder / CLAUDE_FOLDER), "TERM": "xterm-256color",
            "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1", "NO_COLOR": "1"}


def run_claude(claude: str, arguments: list, environment: dict, cwd: Path, timeout: int = 120):
    completed = subprocess.run([claude, *arguments], cwd=cwd, env=environment, capture_output=True, text=True,
                               timeout=timeout, stdin=subprocess.DEVNULL)
    return completed.returncode, plain(completed.stdout + completed.stderr)


def server_status(listing: str, endpoint: str):
    """The status `claude mcp list` prints for the server, or None when it lists no such server."""
    for line in listing.splitlines():
        if line.strip().startswith(SERVER + ":") and endpoint in line:
            return line.rsplit(" - ", 1)[-1].strip() if " - " in line else ""
    return None


def check_authorization_address(address: str, authorization_endpoint: str, resource: str, offered_scopes) -> dict:
    """The facts of the authorization request Claude Code built, or the reason it is not the published profile."""
    parts = urllib.parse.urlsplit(address)
    query = dict(urllib.parse.parse_qsl(parts.query, keep_blank_values=True))
    redirect = urllib.parse.urlsplit(query.get("redirect_uri", ""))
    scopes = query.get("scope", "").split()
    problems = []
    if urllib.parse.urlunsplit((parts.scheme, parts.netloc, parts.path, "", "")) != authorization_endpoint:
        problems.append("the address is not the published authorization endpoint")
    if query.get("response_type") != "code":
        problems.append("response_type is not code")
    if query.get("code_challenge_method") != "S256" or not re.fullmatch(r"[A-Za-z0-9_-]{43}", query.get("code_challenge", "")):
        problems.append("no S256 code challenge")
    if query.get("resource") != resource:
        problems.append("the resource is {!r}".format(query.get("resource")))
    if redirect.scheme != "http" or redirect.hostname not in ("localhost", "127.0.0.1", "::1") or not redirect.path:
        problems.append("the redirect is not a loopback address")
    if not scopes or set(scopes) - set(offered_scopes):
        problems.append("the scopes {} are not among those offered".format(" ".join(scopes)))
    if not query.get("client_id") or not query.get("state"):
        problems.append("no client identity or state")
    if problems:
        raise CheckFailed("; ".join(problems))
    return {"client_id": query["client_id"], "state": query["state"], "redirect_uri": query["redirect_uri"],
            "callback_prefix": "{}://{}{}".format(redirect.scheme, redirect.netloc, redirect.path), "scopes": scopes}


def check_callback(callback_url: str, request: dict, published_base: str):
    """The redirect the consent page returned must carry a code, the request's own state and the issuer."""
    parts = urllib.parse.urlsplit(callback_url)
    query = dict(urllib.parse.parse_qsl(parts.query))
    if "{}://{}{}".format(parts.scheme, parts.netloc, parts.path) != request["callback_prefix"]:
        raise CheckFailed("the consent page returned to another address")
    if query.get("error"):
        raise CheckFailed("the consent page returned the error " + query["error"][:40])
    if not query.get("code"):
        raise CheckFailed("the consent page returned no code")
    if query.get("state") != request["state"]:
        raise CheckFailed("the consent page returned another state")
    if query.get("iss") != published_base:
        raise CheckFailed("the consent page named the issuer {!r}".format(query.get("iss")))


def drive_login(command, environment, cwd, answer, *, address_pattern, seconds=LOGIN_SECONDS,
                listener_seconds=LISTENER_SECONDS):
    """Run Claude Code's login in a pseudo-terminal, as a person in a terminal does.

    `answer(address)` runs the consent for the authorization address Claude Code prints, the first match of
    `address_pattern`, and returns the redirect address, which the browser has already taken to Claude Code's own listener. When Claude Code is still waiting
    at its prompt after `listener_seconds`, the redirect is pasted there instead. Returns the exit status, the
    address, how the redirect arrived and the transcript text."""
    master, slave = os.openpty()
    # A wide terminal keeps the address on one line.
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 60, 4000, 0, 0))
    process = subprocess.Popen(command, stdin=slave, stdout=slave, stderr=slave, cwd=cwd, env=environment,
                               close_fds=True, start_new_session=True)
    os.close(slave)
    transcript, address, redirect, delivered_by, answered_at = bytearray(), None, None, None, None
    deadline = time.monotonic() + seconds
    try:
        while time.monotonic() < deadline:
            ready, _, _ = select.select([master], [], [], 0.25)
            if ready:
                try:
                    chunk = os.read(master, 65536)
                except OSError:
                    chunk = b""
                if not chunk:
                    break
                transcript.extend(chunk)
            elif process.poll() is not None:
                break
            text = plain(transcript)
            if address is None and PASTE_PROMPT in text.lower():
                found = address_pattern.search(text)
                if found is None:
                    break
                address = found.group(0)
                redirect = answer(address)
                answered_at = time.monotonic()
                if redirect is None:
                    break
                delivered_by = "listener"
            elif (redirect is not None and delivered_by == "listener" and process.poll() is None
                  and time.monotonic() - answered_at > listener_seconds):
                os.write(master, redirect.encode() + b"\r")
                delivered_by = "paste"
        if process.poll() is None:
            process.wait(timeout=max(1, deadline - time.monotonic()))
    except subprocess.TimeoutExpired:
        pass
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        try:
            while select.select([master], [], [], 0)[0]:
                chunk = os.read(master, 65536)
                if not chunk:
                    break
                transcript.extend(chunk)
        except OSError:
            pass
        os.close(master)
    return {"exit": process.returncode, "address": address, "redirect": redirect, "delivered_by": delivered_by,
            "text": plain(transcript)}


def claude_tokens(folder: Path, endpoint: str) -> dict:
    """The tokens Claude Code stored for the server, read only by this process and never recorded."""
    store = folder / CLAUDE_FOLDER / ".credentials.json"
    if not store.is_file():
        return {}
    entries = (json.loads(store.read_text(encoding="utf-8")) or {}).get("mcpOAuth") or {}
    for entry in entries.values():
        if isinstance(entry, dict) and entry.get("serverName") == SERVER and entry.get("serverUrl") == endpoint:
            return {"access": entry.get("accessToken") or "", "refresh": entry.get("refreshToken") or "",
                    "client_id": entry.get("clientId") or ""}
    return {}


def initialize(http: Http, endpoint: str, token: str, version: str) -> int:
    status, _headers, _raw = http.request("POST", endpoint, json_body={
        "jsonrpc": "2.0", "id": "qs-oauth-init", "method": "initialize",
        "params": {"protocolVersion": version, "capabilities": {},
                   "clientInfo": {"name": "baltor-quickstart-oauth-check", "version": "1.0.0"}}},
        headers={"Authorization": "Bearer " + token, "Accept": "application/json, text/event-stream"})
    return status


def run_check(origin: str, folder: Path, *, claude: str, node: str, create: bool = False, now: datetime = None,
              http: Http = None, consent=None, login=drive_login) -> dict:
    """Every step of the customer's OAuth connection through Claude Code, as one typed record."""
    now = now or datetime.now(timezone.utc)
    stamp = now.strftime("%Y%m%d")
    http = http or Http()
    rows, facts, secrets = [], {"account": None, "client": None, "consent": None, "callback_delivered_by": None,
                                "identity": None, "digest_prefix": None, "request_id": None,
                                "catalogue_release": None}, []
    tokens, endpoints = {}, {}

    def step(name, passed, detail=""):
        rows.append({"name": name, "passed": bool(passed), "detail": scrubbed(str(detail), *secrets)[:300]})
        return bool(passed)

    folder = private_folder(folder)
    for name in (CLAUDE_FOLDER, PROJECT_FOLDER, EVIDENCE_FOLDER):
        # Private in their own right, not only behind the private state folder; Claude Code would make its own 0775.
        (folder / name).mkdir(mode=0o700, exist_ok=True)
        os.chmod(folder / name, 0o700)
    evidence = folder / EVIDENCE_FOLDER / now.strftime("%Y%m%dT%H%M%SZ")
    evidence.mkdir(mode=0o700, exist_ok=True)
    environment = claude_environment(folder)
    published_base, version = origin.rstrip("/"), None
    endpoint = published_base + quickstarts.PROTOCOL_PATH
    try:
        account_path = folder / ACCOUNT_FILE
        if not account_path.exists():
            if not create:
                raise CheckFailed("no checking account yet; run once with --create-account")
            create_account(origin, folder, node, {name: value for name, value in environment.items()
                                                  if not name.startswith("CLAUDE")}, evidence)
        facts["account"] = read_account(account_path)
        step("account_ready", True, "{} signed up through Get started at {}, access {}".format(
            facts["account"]["tenant_id"][:20], facts["account"]["signed_up_at"], facts["account"]["access_source"]))

        # The published base is the one the service names for its protocol resource, as a client discovers it.
        _status, _headers, answer = http.json("GET", origin + "/api/v1/capabilities")
        capabilities = quickstarts.result_of(answer) or {}
        published_base = quickstarts.service_published_base(capabilities) or origin.rstrip("/")
        endpoint = published_base + quickstarts.PROTOCOL_PATH
        _status, _headers, recipes = http.json("GET", origin + quickstarts.RECIPES_ADDRESS)
        effects = quickstarts.declared_step_effects(quickstarts.published_recipe(recipes, QUICKSTART.id))
        version = ((capabilities.get("protocol") or {}).get("handshake_versions") or [None])[0]

        status, headers, _raw = http.request("POST", endpoint, json_body={
            "jsonrpc": "2.0", "id": "qs-oauth-anonymous", "method": "initialize",
            "params": {"protocolVersion": version, "capabilities": {}, "clientInfo": {"name": "probe", "version": "0"}}},
            headers={"Accept": "application/json, text/event-stream"})
        found = CHALLENGE.search(headers.get("www-authenticate", ""))
        metadata_address = found.group(1) if found else ""
        if status != 401 or not metadata_address.startswith(published_base + "/.well-known/oauth-protected-resource"):
            raise CheckFailed("a request without a credential answered {} with the challenge {!r}".format(
                status, headers.get("www-authenticate", "")[:120]))
        step("challenge_names_the_resource", True, metadata_address)

        _status, _headers, resource = http.json("GET", metadata_address)
        issuer = ((resource or {}).get("authorization_servers") or [None])[0]
        if (resource or {}).get("resource") != endpoint or issuer != published_base:
            raise CheckFailed("the resource metadata names {!r} at {!r}".format((resource or {}).get("resource"), issuer))
        _status, _headers, server = http.json("GET", issuer + "/.well-known/oauth-authorization-server")
        server = server or {}
        endpoints = {name: server.get(name + "_endpoint") for name in ("authorization", "token", "revocation")}
        wanted = {"issuer": server.get("issuer") == issuer,
                  "endpoints on the issuer": all(isinstance(address, str) and address.startswith(issuer + "/")
                                                 for address in endpoints.values()),
                  "S256": "S256" in (server.get("code_challenge_methods_supported") or []),
                  "registration": bool(server.get("registration_endpoint")),
                  "public clients": "none" in (server.get("token_endpoint_auth_methods_supported") or []),
                  "refresh": "refresh_token" in (server.get("grant_types_supported") or [])}
        missing = [name for name, held in wanted.items() if not held]
        if missing:
            raise CheckFailed("the authorization server metadata lacks " + ", ".join(missing))
        offered = (resource or {}).get("scopes_supported") or server.get("scopes_supported") or []
        step("discovery_matches", True, "issuer {}, scopes {}".format(issuer, " ".join(offered)))

        code, shown = run_claude(claude, ["mcp", "get", SERVER], environment, folder / PROJECT_FOLDER)
        if code != 0 or endpoint not in shown:
            run_claude(claude, ["mcp", "remove", SERVER, "--scope", "local"], environment, folder / PROJECT_FOLDER)
            arguments = ["mcp", "add", "--transport", "http", "--scope", "local", SERVER, endpoint]
            if effects:
                arguments += ["--header", quickstarts.STEP_EFFECTS_HEADER + ": " + effects]
            code, shown = run_claude(claude, arguments, environment, folder / PROJECT_FOLDER)
            if code != 0:
                raise CheckFailed("claude mcp add answered {}: {}".format(code, shown.strip()[-160:]))
        _code, listing = run_claude(claude, ["mcp", "list"], environment, folder / PROJECT_FOLDER)
        before = server_status(listing, endpoint)
        if before is None or "needs authentication" not in before.lower():
            raise CheckFailed("claude mcp list showed {!r} before signing in".format(before))
        step("claude_code_needs_authentication", True, before)

        outcome = {}

        def answer_consent(address):
            request = check_authorization_address(address, endpoints["authorization"], endpoint, offered)
            secrets.append(request["state"])
            facts["client"] = {"client_id_prefix": request["client_id"][:8], "redirect_uri": request["redirect_uri"],
                               "scopes_requested": request["scopes"]}
            outcome["request"] = request
            step("claude_code_authorization_requested", True, "client {}…, redirect {}, scopes {}".format(
                request["client_id"][:8], request["redirect_uri"], " ".join(request["scopes"])))
            consented = (consent or run_consent)(node, address, request["callback_prefix"], folder / ACCOUNT_FILE,
                                                 evidence)
            check_callback(consented["callback_url"], request, published_base)
            facts["consent"] = {key: consented["shown"].get(key) for key in
                                ("client_name", "destination", "scopes", "heading", "phone_no_horizontal_overflow")}
            step("consented", True, "client {!r}, {} scopes shown".format(consented["shown"].get("client_name"),
                                                                         len(consented["shown"].get("scopes") or [])))
            return consented["callback_url"]

        result = login([claude, "mcp", "login", SERVER, "--no-browser"], environment, folder / PROJECT_FOLDER,
                       answer_consent, address_pattern=authorization_address(endpoints["authorization"]))
        facts["callback_delivered_by"] = result["delivered_by"]
        if result["address"] is None:
            raise CheckFailed("claude mcp login printed no authorization address: " +
                              scrubbed(result["text"].strip()[-200:]))
        tokens = claude_tokens(folder, endpoint)
        secrets.extend(value for value in tokens.values() if value)
        if (result["exit"] != 0 or not tokens.get("access", "").startswith(ACCESS_PREFIX)
                or not tokens.get("refresh", "").startswith(REFRESH_PREFIX)):
            raise CheckFailed("claude mcp login exited {} and stored {} tokens: {}".format(
                result["exit"], "both" if tokens.get("access") and tokens.get("refresh") else "no",
                scrubbed(result["text"].strip()[-200:], *secrets)))
        step("claude_code_token_issued", True, "access and refresh token stored; redirect taken by {}".format(
            result["delivered_by"]))

        _code, listing = run_claude(claude, ["mcp", "list"], environment, folder / PROJECT_FOLDER)
        after = server_status(listing, endpoint)
        if after is None or "connected" not in after.lower():
            raise CheckFailed("claude mcp list showed {!r} after signing in".format(after))
        step("claude_code_connected", True, after)

        service = quickstarts.Service(published_base, tokens["access"])
        service.step_effects = effects or None
        protocol_rows, protocol_facts = quickstarts.protocol_steps(service, QUICKSTART, capabilities, stamp)
        http.calls += service.calls
        for row in protocol_rows:
            rows.append({**row, "detail": scrubbed(row["detail"], *secrets)[:300]})
        facts.update({key: protocol_facts.get(key) for key in ("identity", "digest_prefix", "request_id",
                                                               "catalogue_release")})
        if not all(row["passed"] for row in protocol_rows):
            raise CheckFailed(None)

        status, _headers, rotated = http.json("POST", endpoints["token"], form={
            "grant_type": "refresh_token", "refresh_token": tokens["refresh"], "client_id": tokens["client_id"],
            "resource": endpoint})
        rotated = rotated or {}
        if status != 200 or not str(rotated.get("access_token", "")).startswith(ACCESS_PREFIX):
            raise CheckFailed("the refresh answered {} {}".format(status, rotated.get("error", "")))
        previous, tokens = tokens, {**tokens, "access": rotated["access_token"], "refresh": rotated.get("refresh_token", "")}
        secrets.extend(value for value in (tokens["access"], tokens["refresh"]) if value)
        accepted = initialize(http, endpoint, tokens["access"], version)
        status, _headers, reused = http.json("POST", endpoints["token"], form={
            "grant_type": "refresh_token", "refresh_token": previous["refresh"], "client_id": tokens["client_id"],
            "resource": endpoint})
        if accepted != 200 or status != 400 or (reused or {}).get("error") != "invalid_grant" \
                or tokens["refresh"] == previous["refresh"]:
            raise CheckFailed("the new access token answered {}, and the old refresh token answered {} {}".format(
                accepted, status, (reused or {}).get("error")))
        step("refreshed", True, "the pair rotated; the old refresh token is refused with invalid_grant")
    except Exception as failure:  # noqa: BLE001 - every failure is recorded on the step it stopped
        if not (isinstance(failure, CheckFailed) and not (failure.args and failure.args[0])):
            step(_next_step(rows), False, failure if isinstance(failure, CheckFailed)
                 else "{}: {}".format(type(failure).__name__, failure))
    finally:
        if tokens.get("refresh") and tokens.get("client_id") and endpoints.get("revocation"):
            revoked = revoke(http, endpoints["revocation"], endpoint, tokens, version)
            step("revoked", revoked == "", revoked or "revocation ended the delegation; the access token is refused")
    passed = bool(rows) and all(row["passed"] for row in rows) and [row["name"] for row in rows] == STEPS
    return {"record_type": RECORD_TYPE, "checked_at": now.isoformat(), "origin": origin,
            "published_base": published_base, "harness": QUICKSTART.harness,
            "claude_code_version": claude_version(claude, environment, folder), **facts,
            "steps": rows, "passed": passed, "failed_step": next((row["name"] for row in rows if not row["passed"]), None),
            "usage_records_added": int(any(row["name"] == "downloaded" and row["passed"] for row in rows)),
            "http_calls": http.calls, "physical_model_calls": 0, "credential_printed": False,
            "body_text_kept": False, "checker_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}


#: Every step of a passing run, in order.
STEPS = ["account_ready", "challenge_names_the_resource", "discovery_matches", "claude_code_needs_authentication",
         "claude_code_authorization_requested", "consented", "claude_code_token_issued", "claude_code_connected",
         "connected", "listed", "searched", "downloaded", "digest_matches", "refreshed", "revoked"]


def _next_step(rows):
    """The first step of a passing run that this run has not recorded: the one a failure stopped."""
    done = {row["name"] for row in rows}
    return next((name for name in STEPS if name not in done and name != "revoked"), "revoked")


def revoke(http: Http, revocation_endpoint: str, endpoint: str, tokens: dict, version: str) -> str:
    """End the delegation and confirm the access token is refused; an empty text when both happened."""
    try:
        status, _headers, _raw = http.request("POST", revocation_endpoint, form={
            "token": tokens["refresh"], "token_type_hint": "refresh_token", "client_id": tokens["client_id"]})
        if status != 200:
            return "the revocation answered {}".format(status)
        refused = initialize(http, endpoint, tokens["access"], version)
        return "" if refused == 401 else "the access token answered {} after revocation".format(refused)
    except CheckFailed as failure:
        return str(failure)


def run_consent(node, address, callback_prefix, account_path, evidence):
    """The browser consent, delivered to Claude Code's own listener, through tools/oauth_consent_browser.mjs."""
    completed = subprocess.run([node, str(ROOT / "tools/oauth_consent_browser.mjs"), address, callback_prefix,
                                str(account_path), str(evidence), "approve", "deliver"], cwd=ROOT,
                               env=inherited_environment(),
                               capture_output=True, text=True, timeout=CONSENT_SECONDS)
    line = completed.stdout.strip().splitlines()[-1:] or [""]
    try:
        consented = json.loads(line[0])
    except ValueError:
        consented = None
    if completed.returncode != 0 or not isinstance(consented, dict) or not consented.get("callback_url"):
        reason = completed.stderr.strip().splitlines()[-1:] or ["no answer"]
        raise CheckFailed("the consent page did not complete: " + scrubbed(reason[0])[:200])
    return consented


def claude_version(claude, environment, folder):
    try:
        code, text = run_claude(claude, ["--version"], environment, folder / PROJECT_FOLDER, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    return text.strip().splitlines()[0][:60] if code == 0 and text.strip() else None


def record_path(directory: Path, now: datetime) -> Path:
    stem = "quickstart-oauth-check-" + now.strftime("%Y-%m-%d")
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


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--origin", required=True, help="The published HTTPS base, such as https://baltor.ai")
    parser.add_argument("--state-dir", type=Path, required=True,
                        help="A private folder outside the repository for the checking account and Claude Code's store")
    parser.add_argument("--record-dir", type=Path, default=ROOT / RECORD_DIRECTORY)
    parser.add_argument("--create-account", action="store_true",
                        help="Make the checking account through Baltor's public sign-up when none exists yet")
    parser.add_argument("--claude", default=shutil.which("claude") or "claude")
    parser.add_argument("--node", default=shutil.which("node") or "node")
    arguments = parser.parse_args(argv)
    origin = urllib.parse.urlsplit(arguments.origin)
    if (origin.scheme != "https" or not origin.hostname or origin.username or origin.password
            or origin.path not in ("", "/") or origin.query or origin.fragment):
        parser.error("an HTTPS origin with no path is required")
    now = datetime.now(timezone.utc)
    try:
        record = run_check(arguments.origin.rstrip("/"), arguments.state_dir, claude=arguments.claude,
                           node=arguments.node, create=arguments.create_account, now=now)
    except (CheckFailed, OSError, subprocess.SubprocessError) as error:
        print(json.dumps({"passed": False, "error": scrubbed(type(error).__name__ + ": " + str(error))[:200]}))
        return 2
    path = write_record(record, arguments.record_dir, now)
    print(json.dumps({"passed": record["passed"], "failed_step": record["failed_step"], "origin": record["origin"],
                      "callback_delivered_by": record["callback_delivered_by"],
                      "usage_records_added": record["usage_records_added"], "record": str(path)}))
    return 0 if record["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
