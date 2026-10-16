"""The systems.baltor.ai Worker answers every request with one fixed permanent redirect to the staff Systems view.

Kind: development check. It runs the real Worker module, src/loop_engine/core/service_runtime/edge/
systems_redirect_worker.js, under Node through the repository's own local Worker host (edge/local_worker_host.mjs)
behind a loopback listener, and sends it real HTTP requests. It opens no connection outside loopback and uploads
nothing; the provider upload is a separate step for the coordinating session. Roadmap S-6.35.11.

What every answer must hold, whatever the method, host, path, query, headers or body:

- status 301 and the Location https://baltor.ai/admin/systems, exactly: nothing a caller sent is copied into it, so
  the redirect cannot be pointed at another site or carry a caller's text;
- noindex, no caching, no body, no cookie, and no sign-in challenge: the HTTP sign-in stopgap of October 15 is gone,
  and the Systems view checks staff access at the service.

A known-wrong Worker that copies the request path into the Location fails the same rules.

Run:

    PYTHONPATH=src python -m unittest tools/test_systems_redirect_worker.py
"""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
EDGE = ROOT / "src" / "loop_engine" / "core" / "service_runtime" / "edge"
WORKER = EDGE / "systems_redirect_worker.js"
HOST = EDGE / "local_worker_host.mjs"
TARGET = "https://baltor.ai/admin/systems"
#: Requests a retired portal hostname may still receive: its old pages, assets, a form post, a sign-in attempt, a probe.
REQUESTS = (
    ("GET", "/", {}, None),
    ("GET", "/arr-dashboard?view=projection&next=https://evil.invalid/", {}, None),
    ("HEAD", "/investor-deck.html", {}, None),
    ("POST", "/api/login", {"Content-Type": "application/json"}, b'{"user":"owner","password":"not-a-real-one"}'),
    ("PUT", "/admin-mesh", {}, b"x"),
    ("DELETE", "/anything", {}, None),
    ("OPTIONS", "/", {"Origin": "https://evil.invalid", "Access-Control-Request-Method": "POST"}, None),
    ("GET", "//evil.invalid/%2e%2e/", {"Authorization": "Basic b3duZXI6bm90LWEtcmVhbC1vbmU="}, None),
    ("GET", "/", {"Host": "systems.baltor.ai", "Cookie": "session=not-a-real-one", "X-Forwarded-Host": "evil.invalid"},
     None),
)


@contextmanager
def running_worker(worker: Path):
    """The Worker module behind a loopback listener, through the repository's local Worker host."""
    with tempfile.TemporaryDirectory(prefix="systems-redirect-") as folder:
        host = Path(folder) / HOST.name
        host.write_text(HOST.read_text("utf-8"), "utf-8")
        process = subprocess.Popen(["node", "--no-warnings", str(host), "--worker", str(worker)],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            line = process.stdout.readline().strip()
            if not line.startswith("LISTENING "):
                raise RuntimeError("the local Worker host did not start: " + (line or process.stderr.read()))
            yield "http://127.0.0.1:" + line.split()[1]
        finally:
            process.terminate()
            process.wait(timeout=10)
            process.stdout.close()
            process.stderr.close()


def observe(base: str) -> list:
    """(request, status, headers, body) for every request above, as the Worker answered it over HTTP."""
    import http.client
    from urllib.parse import urlsplit
    split = urlsplit(base)
    answers = []
    for method, path, headers, body in REQUESTS:
        connection = http.client.HTTPConnection(split.hostname, split.port, timeout=10)
        try:
            connection.request(method, path, body=body, headers=headers)
            response = connection.getresponse()
            answers.append(((method, path), response.status, {name.lower(): value for name, value in response.getheaders()},
                            response.read()))
        finally:
            connection.close()
    return answers


def problems(answers: list) -> list:
    """Every way an answer departs from one fixed, uncached, unindexed permanent redirect."""
    found = []
    for request, status, headers, body in answers:
        def fault(text):
            found.append(f"{request[0]} {request[1]}: {text}")
        if status != 301:
            fault(f"status {status}")
        if headers.get("location") != TARGET:
            fault(f"Location {headers.get('location')!r}")
        if "noindex" not in headers.get("x-robots-tag", ""):
            fault("no noindex")
        if headers.get("cache-control") != "no-store":
            fault(f"Cache-Control {headers.get('cache-control')!r}")
        for name in ("set-cookie", "www-authenticate", "access-control-allow-origin"):
            if name in headers:
                fault(f"carries {name}")
        if body:
            fault("has a body")
    return found


@unittest.skipUnless(shutil.which("node"), "the Worker runs under Node, as at the edge")
class SystemsRedirectWorker(unittest.TestCase):

    def test_every_request_gets_the_same_fixed_permanent_redirect(self):
        with running_worker(WORKER) as base:
            answers = observe(base)
        self.assertEqual(len(answers), len(REQUESTS))
        self.assertEqual(problems(answers), [])

    def test_a_worker_that_copies_the_request_path_into_the_location_is_refused(self):
        source = WORKER.read_text("utf-8")
        reflected = source.replace(
            "export function handle() {\n  return new Response(null, { status: 301, headers: HEADERS });",
            "export function handle(request) {\n  return new Response(null, { status: 301, headers: { ...HEADERS, "
            "location: TARGET + new URL(request.url).pathname } });")
        reflected = reflected.replace("async fetch() {\n    return handle();", "async fetch(request) {\n    return handle(request);")
        self.assertNotEqual(reflected, source)
        with tempfile.TemporaryDirectory(prefix="systems-redirect-wrong-") as folder:
            wrong = Path(folder) / WORKER.name
            wrong.write_text(reflected, "utf-8")
            with running_worker(wrong) as base:
                found = problems(observe(base))
        # KNOWN_WRONG: the copied path shows in the Location of every request that names one.
        self.assertTrue(any("Location" in item for item in found), found)

    def test_the_worker_reads_no_binding_secret_or_request_field(self):
        source = WORKER.read_text("utf-8")
        code = "\n".join(line for line in source.splitlines() if not line.lstrip().startswith("//"))
        for word in ("env", "request", "headers.get", "url", "fetch(", "secret", "password", "Authorization"):
            with self.subTest(word=word):
                self.assertNotIn(word, code.replace("async fetch()", "").replace("TARGET", ""))
        self.assertIn('export const TARGET = "https://baltor.ai/admin/systems";', source)


if __name__ == "__main__":
    unittest.main()
