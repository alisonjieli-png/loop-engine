"""Conformance kit for engine (d) of the catalogue search index slot: one release's index in D1, served by a Worker.

The Worker's own source (`edge/catalogue_search_worker.js`) runs here under Node's built-in SQLite, which has
FTS5, through `edge/local_worker_host.mjs`: D1 is a local SQLite file built from the same export statements an
import sends to D1, KV is a folder, and requests are signed with Ed25519 keys made for the run. Nothing leaves the
loopback interface. Each guard is shown twice: the known-wrong case is refused, and a removed-guard control
reruns the case against a copy of the Worker with the guard taken out and requires the check's own predicate to
fail.

```text
Kit
├── export          statement limit, build identity, the in-memory engine's float32 columns, refusals
├── edge client     pools read strictly, another build refused, https only, no redirect, signatures
├── exactness       pools equal to the in-memory engine's, with and without filters, both modes,
│                   on a published store release and on the 354 judged requests of examples/30_search_quality
├── retrieval       the Worker's service_retrieval_request/v2 answers equal the service's own answers for one
│                   enabled account with default library settings, refusals included
├── authority       unsigned, wrong-scope, stale and changed requests refused; a vector upload of another build
│                   or with a changed column writes nothing; a missing vector column is refused, never zero
└── controls        float32 sums, no lower-casing, rounding half up, no signature check, a missing column
                    scored as zero and an unchecked upload are each caught
```

Node 22.5 or later with `node:sqlite` is required for the Worker checks; without it they are reported as not
applicable with that requirement named, never as passed. The export and client checks need no Node.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import replace
import json
import math
from pathlib import Path
import random
import shutil
import sqlite3
import subprocess
import tempfile
from unittest.mock import patch

from . import catalogue_d1_index as d1
from .catalogue_schema import EMPTY_SCHEMA
from .records import ServiceRuntimeError

NODE_REQUIREMENT = "node>=22.5 with node:sqlite and FTS5"
EDGE_FOLDER = ("core", "service_runtime", "edge")
WORKER_FILE, HOST_FILE = "catalogue_search_worker.js", "local_worker_host.mjs"
CHECK_SCHEMA = {"record_type": "catalogue_attribute_schema/v1", "attributes": [
    {"name": "domain", "type": "keyword_list", "searchable": True, "filterable": True, "shown": True},
    {"name": "origin_layer", "type": "choice", "choices": ["context_intelligence", "code_intelligence"],
     "filterable": True, "shown": True},
    {"name": "effort", "type": "number", "filterable": True, "shown": True},
    {"name": "catalogued_on", "type": "date", "filterable": True, "shown": True},
    {"name": "batch", "type": "keyword", "visibility": "internal"}]}
WORDS = ("python", "script", "data", "table", "schema", "rust", "binary", "install", "hook", "git", "skill",
         "agent", "review", "test", "deploy", "cloud", "edge", "cache", "index", "search", "vector", "render",
         "video", "audio", "scene", "model", "prompt", "token", "csv", "json", "yaml", "lint", "format", "docs")
#: Removed-guard controls: each replaces one guard of the Worker's source in a copy, so a passing check proves the
#: guard is what holds it.
MUTATIONS = {
    "float32_sums": ("const scores = new Float64Array(build.entries);", "const scores = new Float32Array(build.entries);"),
    "no_lower_case": ('String(text ?? "").toLowerCase().match(TOKEN)', 'String(text ?? "").match(TOKEN)'),
    "round_half_up": ("[identity, pyRound(score, 5), [...modes].sort()]", "[identity, Number(score.toFixed(5)), [...modes].sort()]"),
    "no_signature_check": ('  if (!valid) throw new Refusal("unauthorized", 401);\n}', "}"),
    "missing_column_as_zero": ('    if (!buffer || buffer.byteLength !== 4 * build.entries) throw new Refusal("search_index_unavailable", 503);',
                               "    if (!buffer) continue;"),
    "unchecked_upload": ('    if (await sha256Hex(column) !== digests[dimension]) throw new Refusal("invalid_request", 400);\n', ""),
}


def _refused(action, code=None):
    try:
        action()
    except ServiceRuntimeError as error:
        return code is None or error.code == code
    except Exception:  # noqa: BLE001 - a crash is not a typed refusal
        return False
    return False


def node_runtime():
    """The node executable when it can run the Worker here, or None. Starts one short process."""
    executable = shutil.which("node")
    if executable is None:
        return None
    probe = ("import {DatabaseSync} from 'node:sqlite'; const d = new DatabaseSync(':memory:');"
             "d.exec(\"CREATE VIRTUAL TABLE t USING fts5(body, content='')\"); console.log('ready');")
    try:
        done = subprocess.run([executable, "--no-warnings", "--input-type=module", "-e", probe],
                              capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    return executable if done.returncode == 0 and done.stdout.strip() == "ready" else None


def edge_source(name):
    from importlib.resources import files
    return files("loop_engine").joinpath(*EDGE_FOLDER, name).read_text("utf-8")


def mutated_worker(name):
    old, new = MUTATIONS[name]
    source = edge_source(WORKER_FILE)
    if source.count(old) != 1:
        raise AssertionError(f"the control {name} no longer finds its guard in the Worker source")
    return source.replace(old, new)


def _signer():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    return d1.RequestSigner(Ed25519PrivateKey.generate())


class LocalEdge:
    """One export served by the Worker's own code under Node, with search and admin signers made for the run."""

    def __init__(self, root, export, *, node, worker_source=None, upload_vectors=True):
        self.root, self.export, self.node = Path(root), export, node
        self.root.mkdir(parents=True, exist_ok=True)
        self.search, self.admin, self.stranger = _signer(), _signer(), _signer()
        database = self.root / "index.sqlite"
        if not database.exists():
            connection = sqlite3.connect(database)
            d1.load_export_into_sqlite(export, connection)
            connection.close()
        self.kv = self.root / "kv"
        self.kv.mkdir(exist_ok=True)
        keys = self.root / "keys.json"
        keys.write_text(json.dumps([d1.public_key_entry(self.search.public_key_raw, ["search"]),
                                    d1.public_key_entry(self.admin.public_key_raw, ["admin"])]))
        worker = self.root / WORKER_FILE
        worker.write_text(worker_source if worker_source is not None else edge_source(WORKER_FILE), "utf-8")
        host = self.root / HOST_FILE
        host.write_text(edge_source(HOST_FILE), "utf-8")
        self.process = subprocess.Popen([node, "--no-warnings", str(host), "--worker", str(worker), "--db",
                                         str(database), "--kv", str(self.kv), "--keys", str(keys)],
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        line = self.process.stdout.readline().split()
        if len(line) != 2 or line[0] != "LISTENING":
            self.close()
            raise RuntimeError("the local Worker host did not start")
        self.base = f"http://127.0.0.1:{int(line[1])}"
        if upload_vectors:
            for start in range(0, d1.VECTOR_DIMENSIONS, 128):
                status, _answer = self.upload(range(start, start + 128))
                if status != 200:
                    self.close()
                    raise RuntimeError("the local Worker refused the vector upload")

    def transport(self, signer=None):
        return d1.WorkerTransport(self.base, signer or self.search, allow_loopback_http=True)

    def index(self, schema=EMPTY_SCHEMA):
        return d1.D1EdgeSearchIndex(self.transport(), schema)

    def raw(self, method, path, body=b"", headers=None, signer="search", now=None, sign_body=None):
        import urllib.error
        import urllib.request
        chosen = {"search": self.search, "admin": self.admin, "stranger": self.stranger}.get(signer)
        sent = dict(headers or {})
        if chosen is not None:
            sent["Authorization"] = chosen.header(method, path, body if sign_body is None else sign_body, now=now)
        request = urllib.request.Request(self.base + path, data=body if method == "POST" else None, method=method,
                                         headers=sent)
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read())

    def upload(self, dimensions, export=None, *, tamper=False):
        payload = d1.vector_upload_payload(export or self.export, dimensions)
        if tamper:
            payload = payload[:-1] + bytes([payload[-1] ^ 1])
        return self.raw("POST", "/v1/admin/vectors", payload, {"Content-Type": "application/octet-stream"},
                        signer="admin")

    def retrieval(self, payload, headers=None):
        body = json.dumps(payload).encode("utf-8") if not isinstance(payload, bytes) else payload
        return self.raw("POST", "/api/v1/retrieval", body, {"Content-Type": "application/json", **(headers or {})})

    def close(self):
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
def local_edge(root, export, **options):
    edge = LocalEdge(root, export, **options)
    try:
        yield edge
    finally:
        edge.close()


# ---------------------------------------------------------------------------------------------- corpora ----

def _store_corpus(root, count=80, seed=20261005):
    """A published store release with tiers, effects and every filterable attribute type, and its read bundle."""
    from .catalogue_release_checks import Fixture
    fixture = Fixture(root)
    chooser = random.Random(seed)
    lines = []
    for number in range(count):
        identity = f"edge_item_{number:03d}"
        words = " ".join(chooser.choice(WORDS) for _word in range(chooser.randint(3, 9)))
        attributes = {"domain": sorted(chooser.sample(["data", "web", "ml", "ops", "docs"], chooser.randint(1, 3))),
                      "origin_layer": chooser.choice(["context_intelligence", "code_intelligence"]),
                      "batch": "edge-check"}
        if chooser.random() < 0.8:
            attributes["effort"] = chooser.choice([1, 2, 3, 4.5, 5])
        if chooser.random() < 0.8:
            attributes["catalogued_on"] = f"2026-09-{chooser.randint(1, 30):02d}"
        effects = chooser.choice([(), (), (), ("spawns_process",), ("network",), ("reads_fs", "writes_fs")])
        line = fixture.line(identity, f"# {identity}\n{words}\n", effects=effects, attributes=attributes,
                            purpose=f"{words.capitalize()} for {identity.replace('_', ' ')}")
        if chooser.random() < 0.35:
            line = {**line, "approval": {**line["approval"], "tier": "community"}}
        lines.append(line)
    fixture.publish(lines, schema=CHECK_SCHEMA)
    view = fixture.view()
    bundle = fixture.bundle(lines, schema=CHECK_SCHEMA)
    return fixture, view, bundle


def _store_export(view, bundle):
    entries, hits = d1.entries_from_bundle(bundle)
    profile = d1.edge_search_profile(release_id=view.release_id)
    return d1.export_index(entries, bundle.schema, release_id=view.release_id, content_digest=view.content_digest,
                           hits=hits, profile=profile, built_at=0)


def _judged_corpus():
    import sys
    from importlib.resources import files
    from .catalogue_search import IndexEntry, ReleaseSearchIndex, entry_text
    examples = Path(str(files("loop_engine"))).resolve().parents[1] / "examples" / "30_search_quality"
    if not (examples / "measure.py").is_file():
        return None
    if str(examples) not in sys.path:
        sys.path.insert(0, str(examples))
    import measure
    catalogue = measure.load_catalogue(measure.DEFAULT_CATALOGUE)
    judgements = measure.load_judgements(measure.DEFAULT_JUDGEMENTS, catalogue)
    items = sorted(catalogue.items.values(), key=lambda item: item.identity)
    entries = tuple(IndexEntry(item.identity, entry_text(item), {}) for item in items)
    return entries, ReleaseSearchIndex(entries, EMPTY_SCHEMA), judgements


# ------------------------------------------------------------------------------------------ the checks ----

def _export_checks(check):
    from .catalogue_schema import CatalogueAttributeSchema
    from .catalogue_search import IndexEntry, ReleaseSearchIndex
    entries = tuple(IndexEntry(f"item_{n:03d}", f"python data {n} " + "word " * (n % 7), {}) for n in range(40))
    export = d1.export_index(entries, EMPTY_SCHEMA, release_id="r", content_digest="0" * 64, built_at=0)
    body = {key: value for key, value in export.build.items() if key not in ("record_type", "build_id", "built_at")}
    check("an_export_keeps_every_statement_under_the_d1_limit_and_is_named_by_its_content",
          all(len(statement.encode()) <= d1.MAXIMUM_STATEMENT_BYTES for statement in export.statements)
          and export.build_id == d1._sha256(d1.canonical_json(body).encode())
          and export.statements[-1].startswith("INSERT INTO catalogue_index")
          and d1.export_index(entries, EMPTY_SCHEMA, release_id="r", content_digest="0" * 64,
                              built_at=7).build_id == export.build_id)
    memory = ReleaseSearchIndex(entries, EMPTY_SCHEMA)
    check("the_vector_columns_are_the_in_memory_engines_float32_columns",
          all(export.columns[d] == memory._columns[d].tobytes() for d in range(d1.VECTOR_DIMENSIONS))
          and export.build["vectors_digest"] == d1.vectors_digest(d1.column_digests(export.columns)))
    huge = (IndexEntry("huge", "x " * 60_000, {}),)
    internal = CatalogueAttributeSchema.from_dict({"record_type": "catalogue_attribute_schema/v1", "attributes": [
        {"name": "batch", "type": "keyword", "visibility": "internal"}]})
    check("an_export_refuses_a_row_over_the_statement_budget_duplicates_and_hits_out_of_step",
          _refused(lambda: d1.export_index(huge, EMPTY_SCHEMA, release_id="r", content_digest="0" * 64),
                   "search_index_invalid")
          and _refused(lambda: d1.export_index(entries + entries[:1], EMPTY_SCHEMA, release_id="r",
                                               content_digest="0" * 64), "search_index_invalid")
          and _refused(lambda: d1.export_index(entries, EMPTY_SCHEMA, release_id="r", content_digest="0" * 64,
                                               hits=({"reference": {"identity": "other"}},) * len(entries)),
                       "search_index_invalid")
          and d1.export_index(entries, internal, release_id="r", content_digest="0" * 64).build["filters"] == {})
    with patch.object(d1, "STATEMENT_BUDGET", 10 ** 9), patch.object(d1, "MAXIMUM_STATEMENT_BYTES", 10 ** 9):
        check("removed_statement_limits_are_detected",
              not _refused(lambda: d1.export_index(huge, EMPTY_SCHEMA, release_id="r", content_digest="0" * 64)))


def _client_checks(check):
    build = "a" * 64
    good = {"record_type": d1.POOLS_RECORD_TYPE, "build_id": build, "mode": "hybrid",
            "pools": {"lexical": [["x", 1.5]], "vector": [["y", 0.5]]}, "exhausted": True}
    wrong = [{**good, "build_id": "b" * 64}, {**good, "extra": 1}, {**good, "pools": {"lexical": []}},
             {**good, "pools": {"lexical": [["x", 1.0], ["x", 0.5]], "vector": []}},
             {**good, "pools": {"lexical": [["x", math.inf]], "vector": []}},
             {**good, "pools": {"lexical": [["x", 1.0], ["y", 1.0], ["z", 1.0]], "vector": []}},
             {**good, "exhausted": "yes"}, {**good, "record_type": "catalogue_search_index_pools/v2"}]
    read = lambda answer: d1.read_pools(answer, build, mode="hybrid", pool=2, hybrid=True)  # noqa: E731
    check("a_pools_answer_is_read_strictly_and_another_build_is_refused",
          read(good) == ({"lexical": [("x", 1.5)], "vector": [("y", 0.5)]}, True)
          and _refused(lambda: read(wrong[0]), "search_index_changed")
          and all(_refused(lambda answer=answer: read(answer), "search_index_unavailable") for answer in wrong[1:]))
    signer = _signer()
    message = d1.signed_message("POST", "/v1/rank", 100, b"{}")
    check("a_signature_covers_the_method_path_time_and_body",
          len({message, d1.signed_message("GET", "/v1/rank", 100, b"{}"),
               d1.signed_message("POST", "/v1/rank?x=1", 100, b"{}"), d1.signed_message("POST", "/v1/rank", 101, b"{}"),
               d1.signed_message("POST", "/v1/rank", 100, b"{ }")}) == 5
          and signer.header("POST", "/v1/rank", b"{}", now=100).split(" ")[:4]
          == ["Baltor-Signature", "v1", d1.key_id(signer.public_key_raw), "100"])
    check("the_edge_client_reaches_one_https_origin_and_never_plain_http_elsewhere",
          all(_refused(lambda url=url: d1.WorkerTransport(url, signer), "search_engine_unavailable")
              for url in ("http://edge.example", "https://edge.example/path", "https://user:pw@edge.example",
                          "ftp://edge.example", "http://127.0.0.1:9", "https://edge.example?x=1"))
          and d1.WorkerTransport("https://edge.example", signer).origin == "https://edge.example"
          and d1.WorkerTransport("http://127.0.0.1:9", signer, allow_loopback_http=True).origin == "http://127.0.0.1:9")


def _redirect_check(check):
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    import threading

    class Redirect(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 - the standard handler's name
            self.send_response(302)
            self.send_header("Location", "http://127.0.0.1:9/v1/index")
            self.end_headers()

        def log_message(self, *args):  # noqa: ANN002 - silence the standard handler
            pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), Redirect)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        transport = d1.WorkerTransport(f"http://127.0.0.1:{server.server_address[1]}", _signer(),
                                       allow_loopback_http=True)
        check("the_edge_client_never_follows_a_redirect",
              _refused(lambda: d1.D1EdgeSearchIndex(transport), "search_index_unavailable")
              or _refused(lambda: d1.D1EdgeSearchIndex(transport), "search_engine_unavailable"))
    finally:
        server.shutdown()
        server.server_close()


def _pools_equal(memory, edge, queries, conditions=()):
    """Every query's pools, identities, order and scores, in both modes, with each condition set."""
    for query in queries:
        for mode in ("lexical", "hybrid"):
            for chosen in conditions or (None,):
                pool = 10 * memory.policy.candidate_pool_multiplier
                left = memory.rank(query, mode=mode, pool=pool,
                                   eligible=memory.eligible(chosen) if chosen else None)
                right = edge.rank(query, mode=mode, pool=pool, eligible=edge.eligible(chosen) if chosen else None)
                if left != right:
                    return False
    return True


QUERIES = ("python script", "data table schema", "Rust binary install", "hook for git", "render video scene",
           "edge cache index", "token prompt model", "a", "zzzz", "csv json yaml lint", "deploy cloud test review",
           "PYTHON Data", "audio", "search vector", "docs format agent skill")


def _store_checks(check, root, node):
    from .catalogue_schema import CatalogueAttributeSchema
    fixture, view, bundle = _store_corpus(root / "store")
    export = _store_export(view, bundle)
    schema = CatalogueAttributeSchema.from_dict(CHECK_SCHEMA)
    memory = view.search_index()
    conditions = [(("domain", "any_of", ("data",)),), (("origin_layer", "any_of", ("code_intelligence",)),),
                  (("effort", "range", (2, 4.5)),), (("catalogued_on", "range", ("2026-09-10", None)),),
                  (("domain", "any_of", ("ml", "ops")), ("effort", "range", (None, 3)))]
    with local_edge(root / "edge", export, node=node) as edge:
        index = edge.index(schema)
        check("the_edge_worker_ranks_a_published_release_exactly_as_the_in_memory_engine",
              index.stats()["entries"] == len(memory.identities) and _pools_equal(memory, index, QUERIES)
              and _pools_equal(memory, index, QUERIES[:6], [list(chosen) for chosen in conditions]))
        _retrieval_checks(check, fixture, view, edge)
        _authority_checks(check, edge, export)
    with local_edge(root / "edge-float32", export, node=node, worker_source=mutated_worker("float32_sums")) as edge:
        check("removed_float64_sums_are_detected", not _pools_equal(memory, edge.index(schema), QUERIES))
    with local_edge(root / "edge-lower", export, node=node, worker_source=mutated_worker("no_lower_case")) as edge:
        check("removed_lower_casing_is_detected", not _pools_equal(memory, edge.index(schema), QUERIES))
    return fixture, view, export


def _service_answers(fixture, view, requests):
    """The service's own answers to the same retrieval requests, for the fixture's one entitled account."""
    import httpx
    from .http_test_fixtures import running_http

    class Domain:
        runtime = fixture.runtime
        provisioning = fixture.binding(view)
    answers = []
    with running_http(Domain) as (base, _service):
        with httpx.Client(base_url=base, trust_env=False, timeout=10) as client:
            for payload, headers in requests:
                content = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")
                response = client.post("/api/v1/retrieval", content=content,
                                       headers={"Authorization": "Bearer " + fixture.key.key,
                                                "Content-Type": "application/json", **headers})
                answers.append((response.status_code, response.json()))
    return answers


def _comparable(status, answer):
    """An answer without the fields that differ by design: request references, the read scope and the backend."""
    if status != 200:
        error = dict(answer.get("error") or {})
        return status, answer.get("record_type"), error.get("code"), error.get("message"), error.get("next_action")
    result = dict(answer["result"])
    hits = [{key: value for key, value in hit.items() if key != "body_allowed"} for hit in result.pop("hits")]
    backend = sorted(result.pop("backend"))
    limitations = result.pop("limitations")
    return status, answer["record_type"], answer["operation"], hits, backend, limitations[:2], result


def _retrieval_requests():
    request = {"record_type": "service_retrieval_request/v2", "query": "python data script"}
    good = [({**request}, {}), ({**request, "mode": "hybrid", "top_n": 5}, {}),
            ({**request, "library_tiers": ["verified"]}, {}),
            ({**request, "authority_effects": ["pure", "reads_fs"]}, {}),
            ({**request, "filters": {"domain": {"any_of": ["data", "ml"]}, "effort": {"at_least": 2}}}, {}),
            ({**request, "filters": {"catalogued_on": {"at_most": "2026-09-15"}}, "mode": "hybrid"}, {}),
            ({**request, "query": "render video scene", "top_n": 3}, {"Baltor-Step-Effects": "network, spawns_process"}),
            ({**request, "query": "zzzz qqqq"}, {}),
            ({**request, "query": "a", "top_n": 50, "mode": "hybrid"}, {})]
    bad = [({**request, "record_type": "service_retrieval_request/v1"}, {}), ({**request, "query": "   "}, {}),
           ({**request, "mode": "semantic"}, {}), ({**request, "top_n": 0}, {}),
           (json.dumps({**request, "top_n": 1}).replace('"top_n": 1', '"top_n": 1.0').encode("utf-8"), {}),
           ({**request, "top_n": None}, {}), ({**request, "mode": None}, {}), ({**request, "surprise": 1}, {}),
           ({**request, "filters": []}, {}), ({**request, "filters": {"batch": {"equals": "edge-check"}}}, {}),
           ({**request, "filters": {"effort": {"any_of": ["x"]}}}, {}),
           ({**request, "filters": {"domain": {"at_least": "a"}}}, {}),
           ({**request, "library_tiers": ["community"]}, {}), ({**request, "library_tiers": []}, {}),
           ({**request, "authority_effects": ["flying"]}, {}), (request, {"Baltor-Step-Effects": "reads_fs, reads_fs"}),
           (b"[1, 2]", {}), (b"{not json", {}),
           ({**request, "query": "x" * 5000}, {})]
    return good, bad


def _retrieval_checks(check, fixture, view, edge):
    good, bad = _retrieval_requests()
    service = _service_answers(fixture, view, good + bad)
    edge_answers = [edge.retrieval(payload, headers) for payload, headers in good + bad]
    same = [_comparable(*left) == _comparable(*right) for left, right in zip(service, edge_answers)]
    check("the_edge_retrieval_answers_as_the_service_answers_one_enabled_account",
          all(same[:len(good)]) and all(status == 200 for status, _answer in service[:len(good)])
          and any(answer["result"]["hits"] for _status, answer in service[:len(good)])
          and all(hit["body_allowed"] is False for _status, answer in edge_answers[:len(good)]
                  for hit in answer["result"]["hits"]))
    check("the_edge_retrieval_refuses_as_the_service_refuses", all(same[len(good):])
          and all(status >= 400 for status, _answer in edge_answers[len(good):]))


def _authority_checks(check, edge, export):
    import time
    request = json.dumps({"record_type": "service_retrieval_request/v2", "query": "python"}).encode("utf-8")
    statuses = [edge.raw("POST", "/api/v1/retrieval", request, {"Content-Type": "application/json"}, signer=None)[0],
                edge.raw("POST", "/api/v1/retrieval", request, {"Content-Type": "application/json"},
                         signer="stranger")[0],
                edge.raw("POST", "/api/v1/retrieval", request, {"Content-Type": "application/json"},
                         now=time.time() - 3600)[0],
                edge.raw("POST", "/api/v1/retrieval", request, {"Content-Type": "application/json"},
                         sign_body=request + b" ")[0],
                edge.raw("POST", "/v1/admin/vectors", b"BALTORV1", {}, signer="search")[0],
                edge.raw("GET", "/v1/index", signer="admin")[0]]
    check("unsigned_foreign_stale_changed_and_wrong_scope_requests_are_refused",
          statuses == [401] * 6 and edge.raw("GET", "/v1/ping", signer=None)[0] == 200
          and edge.raw("GET", "/v1/index")[0] == 200)
    before = sorted((path.name, path.stat().st_mtime_ns) for path in edge.kv.iterdir())
    other = d1.export_index(tuple(replace(entry, text=entry.text + " changed") for entry in _entries_of(export)),
                            EMPTY_SCHEMA, release_id="other", content_digest="0" * 64, built_at=0)
    tampered, foreign = edge.upload([0, 1], tamper=True), edge.upload([0], other)
    after = sorted((path.name, path.stat().st_mtime_ns) for path in edge.kv.iterdir())
    check("a_vector_upload_of_another_build_or_with_a_changed_column_writes_nothing",
          tampered[0] == 400 and foreign[0] == 409 and before == after)


def _entries_of(export):
    connection = sqlite3.connect(":memory:")
    d1.load_export_into_sqlite(export, connection)
    from .catalogue_search import IndexEntry
    rows = connection.execute("SELECT position, identity FROM entries ORDER BY position").fetchall()
    return tuple(IndexEntry(identity, f"entry {position}", {}) for position, identity in rows)


def _missing_column_checks(check, root, export, node):
    from .catalogue_search import HYBRID_MODE

    def hybrid_refused(worker_source=None, folder="edge-missing"):
        with local_edge(root / folder, export, node=node, worker_source=worker_source) as edge:
            weights = d1_weights("python data")
            for path in edge.kv.iterdir():
                if path.name.endswith(f"_{weights[0]:03d}.bin"):
                    path.unlink()
            return _refused(lambda: edge.index(_schema_of(export)).rank("python data", mode=HYBRID_MODE, pool=10),
                            "search_index_unavailable")
    check("a_missing_vector_column_is_refused_never_scored_as_zero", hybrid_refused())
    check("removed_missing_column_rule_is_detected",
          not hybrid_refused(mutated_worker("missing_column_as_zero"), "edge-missing-control"))


def d1_weights(text):
    from ..retrieval import hash_vector
    return [dimension for dimension, weight in enumerate(hash_vector(text)) if weight]


def _schema_of(export):
    from .catalogue_schema import CatalogueAttributeSchema
    return CatalogueAttributeSchema.from_dict(export.build["schema"])


def _control_checks(check, root, export, node):
    request = json.dumps({"record_type": "service_retrieval_request/v2", "query": "python"}).encode("utf-8")
    with local_edge(root / "edge-unsigned", export, node=node, worker_source=mutated_worker("no_signature_check")) as edge:
        check("removed_signature_check_is_detected",
              edge.raw("POST", "/api/v1/retrieval", request, {"Content-Type": "application/json"},
                       sign_body=request + b" ")[0] == 200)
    with local_edge(root / "edge-upload", export, node=node, upload_vectors=False,
                    worker_source=mutated_worker("unchecked_upload")) as edge:
        check("removed_column_digest_rule_is_detected", edge.upload([0, 1], tamper=True)[0] == 200)


def _function_checks(check, node):
    """The Worker's pure functions against Python's: tokens, CRC-32 buckets, hash vectors and rounding."""
    from ..retrieval import _tokens, hash_vector
    import zlib
    texts = ["Python script", "\u0130stanbul KELVIN \u212a data", "na\u00efve caf\u00e9 123abc", "", "  \t\n", "a" * 300,
             "x-y_z.w", "Hello\u00a0World", "\u01c5 \u01c6 \u01c4", "\ufb01le \ufb02ow", "\u03a3\u0391\u03a3 \u03c3\u03b1\u03c2", "Stra\u00dfe"]
    values = [0.015625, 0.123455, 0.1, 1 / 3, 0.0, 2.5e-05, 0.000125, 1 / 11 + 1 / 64, 0.03125, 0.0703125]
    script = ("const w = await import(process.argv[1]); const input = JSON.parse(process.argv[2]);"
              "console.log(JSON.stringify({tokens: input.texts.map(w.tokens), crc: input.texts.map(w.crc32),"
              "vectors: input.texts.map(w.hashVector), rounded: input.values.map(v => w.pyRound(v, 5)),"
              "mutated: input.values.map(v => Number(v.toFixed(5)))}));")
    with tempfile.TemporaryDirectory(prefix="edge-functions-") as folder:
        worker = Path(folder) / WORKER_FILE
        worker.write_text(edge_source(WORKER_FILE), "utf-8")
        done = subprocess.run([node, "--no-warnings", "--input-type=module", "-e", script, str(worker),
                               json.dumps({"texts": texts, "values": values})],
                              capture_output=True, text=True, timeout=60)
    answer = json.loads(done.stdout) if done.returncode == 0 else None
    expected_vectors = [[[d, w] for d, w in enumerate(hash_vector(text)) if w] for text in texts]
    check("the_workers_tokens_buckets_and_hash_vectors_equal_pythons_bit_for_bit",
          answer is not None and answer["tokens"] == [_tokens(text) for text in texts]
          and answer["crc"] == [zlib.crc32(text.encode("utf-8")) for text in texts]
          and answer["vectors"] == expected_vectors)
    check("the_workers_rounding_is_pythons_round_half_even_of_the_exact_value",
          answer is not None and answer["rounded"] == [round(value, 5) for value in values])
    check("round_half_up_is_detected_as_another_rounding",
          answer is not None and answer["mutated"] != [round(value, 5) for value in values])


def _judged_checks(check, root, node):
    """True when the judged requests ran; they live in the source checkout, not in an installed package."""
    from .catalogue_search import HYBRID_MODE, LEXICAL_MODE
    corpus = _judged_corpus()
    if corpus is None:
        return False
    entries, memory, judgements = corpus
    export = d1.export_index(entries, EMPTY_SCHEMA, release_id="starter", content_digest="0" * 64, built_at=0)
    with local_edge(root / "edge-judged", export, node=node) as edge:
        index = edge.index()
        pool = 10 * memory.policy.candidate_pool_multiplier
        differing = [judgement.query for judgement in judgements for mode in (LEXICAL_MODE, HYBRID_MODE)
                     if memory.rank(judgement.query, mode=mode, pool=pool) != index.rank(judgement.query, mode=mode,
                                                                                         pool=pool)]
    check("the_edge_worker_ranks_every_judged_request_exactly_as_the_in_memory_engine",
          len(judgements) >= 300 and differing == [])
    return True


def run_checks(check, root, *, node=None):
    """Run the kit; returns the requirements of the checks that could not run here, empty when all ran."""
    root = Path(root)
    _export_checks(check)
    _client_checks(check)
    _redirect_check(check)
    node = node or node_runtime()
    if node is None:
        return [NODE_REQUIREMENT]
    _function_checks(check, node)
    _fixture, _view, export = _store_checks(check, root, node)
    _missing_column_checks(check, root, export, node)
    _control_checks(check, root, export, node)
    return [] if _judged_checks(check, root, node) else ["examples/30_search_quality from a source checkout"]


def self_test():
    tests = []

    def check(name, passed):
        tests.append({"test": name, "passed": bool(passed),
                      "detail": "the Worker's own source under Node's SQLite on loopback; no network, no provider"})
    with tempfile.TemporaryDirectory(prefix="catalogue-d1-index-") as folder:
        missing = run_checks(check, Path(folder))
    for requirement in missing:
        tests.append({"test": "the_edge_worker_checks_that_need_" + ("node" if requirement == NODE_REQUIREMENT
                                                                     else "the_judged_requests"),
                      "passed": None, "not_tested": True, "outcome": "NOT_APPLICABLE",
                      "missing_optional_dependencies": [requirement],
                      "detail": "the checks that need this were not run here; every other check ran"})
    return {"tests": tests, "passed": sum(1 for row in tests if row["passed"]),
            "total": len(tests), "all_passed": all(row["passed"] is not False for row in tests)}
