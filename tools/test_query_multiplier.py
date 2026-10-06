"""Offline checks of the query multiplier, each with a known-wrong control that shows the check can fail.

No network: transports get fake openers and runners. Run under the memory cap:
    MEM_MAX=4G ~/.le-ci-tmp/tools/capped.sh env PYTHONPATH=src:tools python -m unittest tools.test_query_multiplier
"""
from __future__ import annotations

import gzip
import json
import math
import os
import shutil
import shlex
import signal
import subprocess
import sys
import tempfile
import textwrap
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for entry in (ROOT / "src", ROOT / "tools", ROOT):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from query_multiplier import importers  # noqa: E402
from query_multiplier.dimensions import DimensionError, load_library, read_library  # noqa: E402
from query_multiplier.evidence import Ledger  # noqa: E402
from query_multiplier.executors import (GitHubCode, GitHubRepositories, OllamaWebSearch, OpenAlexWorks,  # noqa: E402
                                        OpenverseImages, candidate_key, registry)
from query_multiplier.planner import PAD, PlanError, PlannedQuery, query_at, query_identity, read_plan  # noqa: E402
from query_multiplier.routing import licence_lead, route  # noqa: E402
from query_multiplier.runner import ProductStream, Run  # noqa: E402
from query_multiplier.transport import Answer, HostPolicy, RequestRefused, Transport, load_policy  # noqa: E402

SOURCE = {"title": "test vocabulary", "licence": "MIT"}


def value(identity, text, **attributes):
    return {"id": identity, "text": text, **({"attributes": attributes} if attributes else {})}


def small_library(*, rules=True):
    """Topics, formats, licences and geography small enough to enumerate the whole product."""
    document = {
        "record_type": "research_dimension_library/v1", "version": "test", "provenance": ["test"],
        "dimensions": [
            {"id": "sdg_target", "title": "targets", "kind": "topic", "null_share": 0, "source": SOURCE,
             "values": [value("sdg:6.1", "drinking water", goal="6"), value("sdg:6.3", "water quality", goal="6"),
                        value("sdg:11.2", "public transport", goal="11")]},
            {"id": "creative_domain", "title": "creative", "kind": "topic", "null_share": 0, "source": SOURCE,
             "values": [value("cd:shader", "shader"), value("cd:voxel", "voxel")]},
            {"id": "file_format", "title": "formats", "kind": "format", "null_share": 0, "source": SOURCE,
             "values": [value("csv", "csv", family="table", code="extension:csv"),
                        value("svg", "svg", family="image", code="svg extension:svg", openverse="svg"),
                        value("geojson", "geojson", family="geo", code="FeatureCollection extension:geojson")]},
            {"id": "licence", "title": "licences", "kind": "licence", "null_share": 0, "source": SOURCE,
             "values": [value("spdx:MIT", "mit", github="mit", hf="mit"),
                        value("spdx:CC0-1.0", "cc0", github="cc0-1.0", openverse="cc0", openalex="cc0"),
                        value("spdx:Apache-2.0", "apache 2.0", github="apache-2.0")]},
            {"id": "geography", "title": "geography", "kind": "geography", "null_share": 0, "source": SOURCE,
             "values": [value("iso:KE", "kenya", iso2="KE"), value("iso:PE", "peru", iso2="PE"),
                        value("m49:002", "africa", m49="002")]},
            {"id": "time_window", "title": "quarters", "kind": "time_window", "null_share": 0, "source": SOURCE,
             "values_from": {"loader": "quarters", "first": "2024q1", "last": "2024q4"}},
        ],
        "rules": [{"id": "media_formats_never_meet_public_policy_topics",
                   "if": {"dimension": "file_format", "attribute": "family", "in": ["image"]},
                   "require_null": ["sdg_target"], "reason": "test rule"}] if rules else []}
    return read_library(document)


def product(identity, executor, dimensions, **extra):
    return {"id": identity, "executor": executor, "weight": 1,
            "dimensions": [{"dimension": name, **({"null_share": share} if share is not None else {})} for name, share in dimensions],
            **extra}


def plan(*products):
    return {"record_type": "research_query_plan/v1", "engine": "factorized_multiplier", "products": list(products)}


class Temporary(unittest.TestCase):
    def setUp(self):
        base = os.environ.get("TMPDIR") or tempfile.gettempdir()
        self.folder = Path(tempfile.mkdtemp(prefix="query-multiplier-", dir=base))

    def tearDown(self):
        shutil.rmtree(self.folder, ignore_errors=True)

    def ledger(self, name="root", clock=None):
        kwargs = {"clock": clock} if clock else {}
        ledger = Ledger(self.folder / name, **kwargs)
        self.addCleanup(ledger.close)
        return ledger


def all_queries(product_, library, executor):
    out, reasons = [], {}
    for k in range(product_.total):
        query, reason = query_at(product_, k, library, executor)
        if query is None:
            reasons[reason] = reasons.get(reason, 0) + 1
        else:
            out.append(query)
    return out, reasons


class CompatibilityTests(unittest.TestCase):
    def test_an_incompatible_combination_is_skipped_with_its_reason(self):
        library = small_library()
        executors = registry()
        [built] = read_plan(plan(product("code", "github_code", [("file_format", None), ("sdg_target", 40)])), library, executors)
        queries, reasons = all_queries(built, library, executors["github_code"])
        combined = [q for q in queries if q.assignment["file_format"].id == "svg" and q.assignment["sdg_target"] is not None]
        self.assertEqual(combined, [])
        self.assertGreater(reasons.get("rule:media_formats_never_meet_public_policy_topics", 0), 0)
        # svg still runs on its own: the rule removes the combination, not the value.
        self.assertTrue(any(q.assignment["file_format"].id == "svg" for q in queries))

    def test_known_wrong_without_the_rule_the_combination_is_planned(self):
        library = small_library(rules=False)
        executors = registry()
        [built] = read_plan(plan(product("code", "github_code", [("file_format", None), ("sdg_target", 40)])), library, executors)
        queries, _ = all_queries(built, library, executors["github_code"])
        self.assertTrue(any(q.assignment["file_format"].id == "svg" and q.assignment["sdg_target"] is not None for q in queries))

    def test_a_value_the_executor_cannot_express_never_enters_the_product(self):
        library = small_library()
        executors = registry()
        [built] = read_plan(plan(product("images", "openverse_images", [("creative_domain", None), ("licence", 0)])), library, executors)
        axis = next(axis for axis in built.axes if axis.dimension.id == "licence")
        self.assertEqual(axis.values_used, 1)  # only CC0 has an Openverse rendering here
        self.assertEqual(axis.values_not_expressible, 2)
        queries, _ = all_queries(built, library, executors["openverse_images"])
        self.assertTrue(all(dict(q.request["params"])["license"] == "cc0" for q in queries))

    def test_an_executor_refuses_a_dimension_it_cannot_render(self):
        with self.assertRaises(PlanError):
            read_plan(plan(product("bad", "npm_search", [("geography", None)])), small_library(), registry())


class FairRotationTests(unittest.TestCase):
    def setUp(self):
        self.library = small_library()
        self.executors = registry()
        [self.product] = read_plan(plan(product("repos", "github_repositories", [
            ("sdg_target", None), ("licence", 0), ("geography", 40), ("time_window", 30)])), self.library, self.executors)

    def test_no_combination_repeats_before_the_product_is_spent(self):
        seen = set()
        for k in range(self.product.total):
            assignment = self.product.assignment(k)
            if assignment is None:
                continue
            seen.add(tuple(sorted((name, getattr(v, "id", None)) for name, v in assignment.items())))
        sizes = [axis.size for axis in self.product.axes]
        self.assertTrue(all(math.gcd(a, b) == 1 for i, a in enumerate(sizes) for b in sizes[i + 1:]))
        distinct_virtual = math.prod(len({id(e) if e is not None else None for e in axis.entries}) for axis in self.product.axes)
        self.assertGreater(len(seen), 0)
        self.assertLessEqual(len(seen), distinct_virtual)

    def test_every_value_of_every_dimension_comes_round_within_its_length(self):
        for axis in self.product.axes:
            covered = {getattr(axis.entry(k), "id", "pad" if axis.entry(k) is PAD else None) for k in range(axis.size)}
            expected = ({value.id for value in axis.entries if value is not None and value is not PAD}
                        | ({None} if None in axis.entries else set()) | ({"pad"} if PAD in axis.entries else set()))
            self.assertEqual(covered, expected, axis.dimension.id)

    def test_null_values_stay_and_make_global_baseline_queries(self):
        queries, _ = all_queries(self.product, self.library, self.executors["github_repositories"])
        self.assertTrue(any(q.assignment["geography"] is None for q in queries))
        self.assertTrue(any(q.assignment["geography"] is not None for q in queries))
        baseline = next(q for q in queries if q.assignment["geography"] is None)
        self.assertNotIn('"kenya"', dict(baseline.request["params"])["q"])

    def test_known_wrong_lengths_sharing_a_factor_repeat_before_the_product_is_spent(self):
        # Two dimensions of lengths 4 and 6 (gcd 2): positions k and k + 12 coincide, so the residue map is not a
        # bijection of the 24 combinations; the planner's coprime padding is what prevents this.
        pairs = {(k % 4, k % 6) for k in range(24)}
        self.assertLess(len(pairs), 24)
        self.assertEqual(len({(k % 5, k % 6) for k in range(30)}), 30)


class HostTests(unittest.TestCase):
    class Opener:
        def __init__(self):
            self.calls = []

        def open(self, request, timeout):
            self.calls.append(request)
            raise AssertionError("nothing may be sent to a refused host")

    def executor_for(self, host):
        executor = OpenverseImages()
        executor.host = host
        return executor

    def test_a_forbidden_host_is_refused_before_any_request(self):
        opener = self.Opener()
        transport = Transport(load_policy(), opener=opener)
        executor = self.executor_for("www.google.com")
        request = {"method": "GET", "host": "www.google.com", "path": "/search", "params": [["q", "x"]], "body": None, "page": 1}
        with self.assertRaises(RequestRefused) as caught:
            transport.send(executor, request)
        self.assertEqual(caught.exception.code, "host_forbidden")
        self.assertEqual(opener.calls, [])
        for host in ("google.com", "scholar.google.com", "bing.com", "html.duckduckgo.com"):
            self.assertIsNotNone(load_policy().refusal(host), host)

    def test_known_wrong_a_policy_without_the_entry_lets_the_request_through(self):
        class Recording:
            def __init__(self):
                self.calls = []

            def open(self, request, timeout):
                self.calls.append(request.full_url)
                raise OSError("offline test")
        opener = Recording()
        transport = Transport(HostPolicy((), ()), opener=opener)
        executor = self.executor_for("www.google.com")
        request = {"method": "GET", "host": "www.google.com", "path": "/search", "params": [["q", "x"]], "body": None, "page": 1}
        answer = transport.send(executor, request)
        self.assertEqual(len(opener.calls), 1)
        self.assertIsNone(answer.status)

    def test_a_request_to_a_host_the_executor_did_not_declare_is_refused(self):
        transport = Transport(load_policy(), opener=self.Opener())
        request = {"method": "GET", "host": "example.org", "path": "/v1/images/", "params": [], "body": None, "page": 1}
        with self.assertRaises(RequestRefused) as caught:
            transport.send(OpenverseImages(), request)
        self.assertEqual(caught.exception.code, "host_not_declared_by_executor")

    def test_the_web_search_key_is_sent_but_never_stored(self):
        secret = "test-key-" + "x" * 24
        seen = {}

        class Opener:
            def open(self, request, timeout):
                seen.update(dict(request.header_items()))

                class Response:
                    status = 200
                    headers = {}

                    def read(self, size):
                        return json.dumps({"results": [{"title": "t", "url": "https://github.com/Owner/Repo"}]}).encode()

                    def __enter__(self):
                        return self

                    def __exit__(self, *args):
                        return False
                return Response()
        transport = Transport(load_policy(), opener=Opener(), environment={"OLLAMA_API_KEY": secret})
        executor = OllamaWebSearch()
        request = executor.text_request("water quality open data")
        answer = transport.send(executor, request)
        self.assertEqual(seen.get("Authorization"), "Bearer " + secret)
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as folder:
            ledger = Ledger(Path(folder) / "root")
            query = PlannedQuery("p", executor.executor_id, 0, {}, request, query_identity(executor.executor_id, request))
            ledger.plan(query)
            attempt = ledger.intent(query, "run", 1)
            record = ledger.store(attempt, query, request, answer)
            stored = gzip.decompress((ledger.root / record["path"]).read_bytes())
            database = (ledger.root / "state" / "ledger.sqlite").read_bytes()
            ledger.close()
        self.assertNotIn(secret.encode(), stored)
        self.assertNotIn(secret.encode(), database)
        self.assertNotIn(secret, json.dumps(request))

    def test_a_keyed_engine_without_its_key_sends_nothing(self):
        transport = Transport(load_policy(), opener=self.Opener(), environment={})
        executor = OllamaWebSearch()
        with self.assertRaises(RequestRefused) as caught:
            transport.send(executor, executor.text_request("x"))
        self.assertEqual(caught.exception.code, "key_not_in_environment")


class FakeTransport:
    """Answers every request with a canned body; records what was sent."""

    def __init__(self, body: bytes, status: int = 200, policy=None):
        self.body, self.status, self.sent = body, status, []
        self.policy = policy or load_policy()

    def check(self, executor, request):
        Transport(self.policy).check(executor, request)

    def send(self, executor, request):
        self.check(executor, request)
        self.sent.append(request)
        return Answer(self.status, {}, self.body, 1.0, False, "", True, "https://" + request["host"] + request["path"])


def repo_rows(*names):
    return json.dumps({"total_count": len(names), "incomplete_results": False, "items": [
        {"full_name": name, "html_url": "https://github.com/" + name, "private": False, "visibility": "public",
         "license": {"spdx_id": "MIT"}, "language": "Python", "topics": [], "stargazers_count": 1,
         "description": "d", "default_branch": "main"} for name in names]}).encode()


class ExecutionTests(Temporary):
    def run_one(self, ledger, transport, *, store_fails=False):
        library = small_library()
        executors = registry()
        [built] = read_plan(plan(product("repos", "github_repositories", [("sdg_target", None), ("licence", 0)])), library, executors)
        run = Run(library=library, products=[built], executors=executors, transport=transport, ledger=ledger, minutes=1,
                  resolve_licences=False)
        lane = run.lanes[0]
        stream = lane.streams[0]
        query = stream.next()
        if store_fails:
            def failing(*args, **kwargs):
                raise OSError("disk full")
            original = ledger.store
            ledger.store = lambda *a, **k: original(*a, write=failing, **k)
        lane.attempt(query, stream)
        return query, lane

    def test_a_query_without_a_stored_response_does_not_count_as_executed(self):
        ledger = self.ledger()
        query, lane = self.run_one(ledger, FakeTransport(repo_rows("a/b")), store_fails=True)
        state = ledger.query_state(query.query_id)
        self.assertNotEqual(state[0], "executed")
        self.assertEqual(lane.stats["executed"], 0)
        self.assertEqual(ledger.scalar("select count(*) from candidates"), 0)
        attempt = ledger.rows("select state, error_class from attempts")[0]
        self.assertEqual(attempt[0], "not_stored")
        with self.assertRaises(RuntimeError):
            ledger.mark_executed(ledger.scalar("select attempt_id from attempts"), query, parse_status="ok",
                                 total_count=1, refresh_days=1)

    def test_known_wrong_the_same_flow_with_a_working_store_executes(self):
        ledger = self.ledger()
        query, lane = self.run_one(ledger, FakeTransport(repo_rows("a/b")))
        self.assertEqual(ledger.query_state(query.query_id)[0], "executed")
        self.assertEqual(lane.stats["executed"], 1)
        path = ledger.scalar("select evidence_path from attempts")
        self.assertTrue((ledger.root / path).is_file())

    def test_a_refused_or_failed_answer_is_stored_but_executes_nothing(self):
        ledger = self.ledger()
        query, lane = self.run_one(ledger, FakeTransport(b'{"message": "rate limited"}', status=429))
        self.assertNotEqual(ledger.query_state(query.query_id)[0], "executed")
        self.assertEqual(ledger.scalar("select state from attempts"), "closed")
        self.assertIsNotNone(ledger.hold("github_repositories"))

    def test_the_same_item_found_by_two_queries_is_one_candidate(self):
        ledger = self.ledger()
        library = small_library()
        executors = registry()
        [built] = read_plan(plan(product("repos", "github_repositories", [("sdg_target", None), ("licence", 0)])), library, executors)
        transport = FakeTransport(repo_rows("Owner/Shared", "owner/other-1"))
        run = Run(library=library, products=[built], executors=executors, transport=transport, ledger=ledger, minutes=1,
                  resolve_licences=False)
        lane, stream = run.lanes[0], run.lanes[0].streams[0]
        first, second = stream.next(), stream.next()
        self.assertNotEqual(first.query_id, second.query_id)
        lane.attempt(first, stream)
        transport.body = repo_rows("owner/shared", "owner/other-2")
        lane.attempt(second, stream)
        self.assertEqual(ledger.scalar("select count(*) from candidates where key='github:owner/shared'"), 1)
        self.assertEqual(ledger.scalar("select origins from candidates where key='github:owner/shared'"), 2)
        self.assertEqual(ledger.scalar("select count(*) from origins where key='github:owner/shared'"), 2)
        self.assertEqual(ledger.scalar("select count(*) from candidates"), 3)
        # A web result that names the same repository is the same candidate as well.
        self.assertEqual(candidate_key("https://github.com/Owner/Shared/tree/main/docs")[0], "github:owner/shared")

    def test_known_wrong_two_distinct_items_stay_two_candidates(self):
        self.assertNotEqual(candidate_key("https://github.com/owner/one")[0], candidate_key("https://github.com/owner/two")[0])

    def test_a_crash_after_storing_is_repaired_from_the_file_not_a_second_request(self):
        ledger = self.ledger()
        library = small_library()
        executors = registry()
        [built] = read_plan(plan(product("repos", "github_repositories", [("sdg_target", None), ("licence", 0)])), library, executors)
        transport = FakeTransport(repo_rows("x/y"))
        run = Run(library=library, products=[built], executors=executors, transport=transport, ledger=ledger, minutes=1,
                  resolve_licences=False)
        stream = run.lanes[0].streams[0]
        query = stream.next()
        ledger.plan(query)
        attempt = ledger.intent(query, run.run_id, 1)
        answer = transport.send(executors["github_repositories"], query.request)
        # The response file reached the disk, then the process died before the ledger said "stored".
        path = ledger.evidence_path(query.executor_id, attempt)
        path.parent.mkdir(parents=True, exist_ok=True)
        ledger.store(attempt, query, query.request, answer)
        with ledger.lock:
            ledger.db.execute("update attempts set state='intent' where attempt_id=?", (attempt,))
            ledger.db.commit()
        sent_before = len(transport.sent)
        summary = Run(library=library, products=[built], executors=executors, transport=transport, ledger=ledger,
                      minutes=1, resolve_licences=False).reconcile()
        self.assertEqual(summary["adopted_after_crash"], 1)
        self.assertEqual(len(transport.sent), sent_before)
        self.assertEqual(ledger.query_state(query.query_id)[0], "executed")
        self.assertEqual(ledger.scalar("select count(*) from candidates"), 1)

    def test_an_intent_with_nothing_stored_is_abandoned_and_the_query_stays_unexecuted(self):
        ledger = self.ledger()
        query = PlannedQuery("p", "github_repositories", 0, {}, {"method": "GET", "host": "api.github.com",
                             "path": "/search/repositories", "params": [["q", "x"]], "body": None, "page": 1}, "q1")
        ledger.plan(query)
        ledger.intent(query, "run", 1)
        summary = Run(library=small_library(), products=[], executors=registry(), transport=FakeTransport(b""),
                      ledger=ledger, minutes=1, resolve_licences=False).reconcile()
        self.assertEqual(summary["abandoned_intents"], 1)
        self.assertEqual(ledger.query_state("q1")[0], "planned")


class DiskGuardTests(Temporary):
    def lane(self, minimum_free_bytes):
        library = small_library()
        executors = registry()
        [built] = read_plan(plan(product("repos", "github_repositories", [("sdg_target", None)])), library, executors)
        transport = FakeTransport(repo_rows("a/b"))
        run = Run(library=library, products=[built], executors=executors, transport=transport, ledger=self.ledger(),
                  minutes=1, resolve_licences=False, minimum_free_bytes=minimum_free_bytes)
        run.gate = {"core": {"remaining": 5000}, "search": {"remaining": 30}, "code_search": {"remaining": 10}}
        run.gate_read = 10 ** 12  # no allowance read in a unit test
        return run, run.lanes[0], transport

    def test_a_pass_stops_before_the_evidence_disk_runs_out(self):
        run, lane, transport = self.lane(10 ** 18)  # more free space than any disk has
        lane.loop()
        self.assertEqual(lane.done_reason, "disk_space_low")
        self.assertEqual(transport.sent, [])

    def test_known_wrong_with_room_on_the_disk_the_lane_sends(self):
        run, lane, transport = self.lane(0)
        self.assertEqual(lane.wait_reason(), "")


class LaneRefusalTests(Temporary):
    class Opener:
        def __init__(self):
            self.calls = 0

        def open(self, request, timeout):
            self.calls += 1

            class Response:
                status = 200
                headers = {}

                def read(self, size):
                    return json.dumps({"results": [{"title": "t", "url": "https://example.org/x"}]}).encode()

                def __enter__(self):
                    return self

                def __exit__(self, *args):
                    return False
            return Response()

    def lane(self, environment):
        library = small_library()
        executors = registry()
        [built] = read_plan(plan(product("web", "ollama_web_search", [("sdg_target", None), ("geography", 40)])), library, executors)
        ledger = self.ledger()
        opener = self.Opener()
        run = Run(library=library, products=[built], executors=executors, ledger=ledger, minutes=1, resolve_licences=False,
                  minimum_free_bytes=0,
                  transport=Transport(load_policy(), opener=opener, environment=environment))
        return run, run.lanes[0], ledger, opener

    def test_a_lane_refused_before_sending_stops_without_spending_its_cursor(self):
        run, lane, ledger, opener = self.lane({})
        lane.loop()
        self.assertEqual(lane.done_reason, "refused:key_not_in_environment")
        self.assertEqual(opener.calls, 0)
        self.assertIsNone(ledger.scalar("select next_k from cursors"))
        self.assertEqual(ledger.scalar("select count(*) from queries"), 0)

    def test_known_wrong_with_the_key_the_same_lane_sends_and_advances(self):
        run, lane, ledger, opener = self.lane({"OLLAMA_API_KEY": "k" * 32})
        stream = lane.streams[0]
        query = stream.next()
        lane.attempt(query, stream)
        self.assertEqual(opener.calls, 1)
        self.assertGreater(ledger.scalar("select next_k from cursors"), 0)


class ClockedLedger:
    def __init__(self, start):
        self.now = start

    def __call__(self):
        return self.now


class RefreshTests(Temporary):
    def test_an_executed_query_is_not_repeated_inside_its_period_and_returns_after_it(self):
        clock = ClockedLedger(datetime(2026, 10, 5, tzinfo=timezone.utc))
        ledger = self.ledger(clock=clock)
        query = PlannedQuery("p", "github_repositories", 0, {}, {"method": "GET", "host": "api.github.com",
                             "path": "/search/repositories", "params": [["q", "x"]], "body": None, "page": 1}, "q1")
        ledger.plan(query)
        attempt = ledger.intent(query, "run", 1)
        ledger.store(attempt, query, query.request, Answer(200, {}, repo_rows("a/b"), 1.0))
        ledger.mark_executed(attempt, query, parse_status="ok", total_count=1, refresh_days=30)
        self.assertIs(ledger.within_refresh("q1"), True)
        clock.now += timedelta(days=29)
        self.assertIs(ledger.within_refresh("q1"), True)
        clock.now += timedelta(days=2)
        self.assertIs(ledger.within_refresh("q1"), False)
        self.assertIsNone(ledger.within_refresh("never-planned"))


class RefreshLaneTests(Temporary):
    def lane_with_one_execution(self, clock):
        ledger = self.ledger(clock=clock)
        library = small_library()
        executors = registry()
        [built] = read_plan(plan(product("repos", "github_repositories", [("sdg_target", None), ("licence", 0)])), library, executors)
        transport = FakeTransport(repo_rows("a/b"))
        run = Run(library=library, products=[built], executors=executors, transport=transport, ledger=ledger, minutes=1,
                  resolve_licences=False)
        lane = run.lanes[0]
        stream = lane.streams[0]
        first = stream.next()
        lane.attempt(first, stream)
        return lane, first, transport, ledger

    def test_a_due_query_is_refreshed_with_the_same_request(self):
        clock = ClockedLedger(datetime(2026, 10, 5, tzinfo=timezone.utc))
        lane, first, transport, ledger = self.lane_with_one_execution(clock)
        clock.now += timedelta(days=31)
        refreshed, _ = lane.due_refresh()
        self.assertEqual((refreshed.query_id, refreshed.request, refreshed.origin), (first.query_id, first.request, "refresh"))
        lane.attempt(refreshed, lane.streams[0])
        self.assertEqual(ledger.scalar("select executions from queries where query_id=?", (first.query_id,)), 2)
        self.assertEqual(len(transport.sent), 2)

    def test_known_wrong_a_query_inside_its_period_is_not_refreshed(self):
        clock = ClockedLedger(datetime(2026, 10, 5, tzinfo=timezone.utc))
        lane, first, transport, ledger = self.lane_with_one_execution(clock)
        clock.now += timedelta(days=29)
        self.assertIsNone(lane.due_refresh())
        self.assertEqual(len(transport.sent), 1)


class LearnedWeightTests(Temporary):
    def seed(self, ledger, product_id, executions, new_unique):
        with ledger.lock:
            for index in range(executions):
                ledger.db.execute("insert into queries(query_id, executor_id, product_id, k, page, parent_query_id, origin, "
                                  "assignment, request, planned_at, state, executions, new_unique, sequence) "
                                  "values(?,?,?,?,1,'','product','{}','{}','t','executed',1,?,?)",
                                  (f"{product_id}-{index}", "github_repositories", product_id, index, new_unique, index))
            ledger.db.commit()

    def runs(self, ledger):
        library = small_library()
        executors = registry()
        products = read_plan(plan(product("rich", "github_repositories", [("sdg_target", None)]),
                                  product("poor", "github_repositories", [("creative_domain", None)]),
                                  product("new", "github_repositories", [("geography", None)])), library, executors)
        return Run(library=library, products=products, executors=executors, transport=FakeTransport(b""), ledger=ledger,
                   minutes=1, resolve_licences=False)

    def test_products_share_requests_by_measured_yield_with_a_floor(self):
        ledger = self.ledger()
        self.seed(ledger, "rich", 30, 40)
        self.seed(ledger, "poor", 30, 0)
        self.seed(ledger, "new", 5, 90)  # too few executions to judge
        learned = self.runs(ledger).learned["github_repositories"]
        self.assertGreater(learned["rich"]["weight"], learned["rich"]["prior"])
        self.assertEqual(learned["poor"]["weight"], 1)  # never out of the rotation
        self.assertEqual(learned["new"]["weight"], learned["new"]["prior"])

    def test_known_wrong_without_measurements_every_product_keeps_its_prior(self):
        ledger = self.ledger()
        learned = self.runs(ledger).learned["github_repositories"]
        self.assertTrue(all(row["weight"] == row["prior"] for row in learned.values()))


CHILD = textwrap.dedent("""
    import os, signal, sys
    sys.path[:0] = [{src!r}, {tools!r}, {root!r}]
    from test_query_multiplier import small_library, plan, product
    from query_multiplier.executors import registry
    from query_multiplier.planner import read_plan
    from query_multiplier.evidence import Ledger
    from query_multiplier.runner import ProductStream
    from query_multiplier.transport import Answer
    library = small_library()
    executors = registry()
    [built] = read_plan(plan(product("repos", "github_repositories", [("sdg_target", None), ("licence", 0),
                                                                       ("time_window", 30)])), library, executors)
    ledger = Ledger({ledger!r})
    stream = ProductStream(built, library, executors["github_repositories"], ledger)
    for index in range(6):
        query = stream.next()
        if index == 5:
            print(query.k, query.query_id, flush=True)
            os.kill(os.getpid(), signal.SIGKILL)  # killed with this query in flight, before its cursor is saved
        ledger.plan(query)
        attempt = ledger.intent(query, "run", 1)
        ledger.store(attempt, query, query.request, Answer(200, {{}}, b'{{"items": []}}', 1.0))
        ledger.mark_executed(attempt, query, parse_status="empty", total_count=0, refresh_days=30)
        stream.save()
""")


class CursorTests(Temporary):
    def child(self, ledger_root):
        code = CHILD.format(src=str(ROOT / "src"), tools=str(ROOT / "tools"), root=str(ROOT), ledger=str(ledger_root))
        result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=120,
                                env={**os.environ, "PYTHONPATH": ""})
        self.assertEqual(result.returncode, -signal.SIGKILL, result.stderr[-2000:])
        k, query_id = result.stdout.split()
        return int(k), query_id

    def test_the_cursor_resumes_after_a_kill(self):
        root = self.folder / "root"
        in_flight_k, in_flight_id = self.child(root)
        ledger = self.ledger()
        library = small_library()
        executors = registry()
        [built] = read_plan(plan(product("repos", "github_repositories", [("sdg_target", None), ("licence", 0),
                                                                           ("time_window", 30)])), library, executors)
        stream = ProductStream(built, library, executors["github_repositories"], ledger)
        resumed = stream.next()
        self.assertEqual((resumed.k, resumed.query_id), (in_flight_k, in_flight_id))
        self.assertEqual(ledger.scalar("select count(*) from queries where state='executed'"), 5)
        # Nothing executed before the kill comes back inside its refresh period.
        executed = {row[0] for row in ledger.rows("select query_id from queries where state='executed'")}
        self.assertNotIn(resumed.query_id, executed)

    def test_known_wrong_a_fresh_ledger_starts_again_from_the_first_position(self):
        root = self.folder / "root"
        self.child(root)
        other = Ledger(self.folder / "other")
        self.addCleanup(other.close)
        library = small_library()
        executors = registry()
        [built] = read_plan(plan(product("repos", "github_repositories", [("sdg_target", None), ("licence", 0),
                                                                           ("time_window", 30)])), library, executors)
        first = ProductStream(built, library, executors["github_repositories"], other).next()
        self.assertEqual(first.k, next(k for k in range(built.total) if query_at(built, k, library, executors["github_repositories"])[0]))


class RenderingTests(unittest.TestCase):
    def setUp(self):
        self.library = small_library()

    def pick(self, dimension, identity):
        return self.library.dimension(dimension).value(identity)

    def test_github_repository_queries_carry_the_dork_qualifiers(self):
        request = GitHubRepositories().render({"sdg_target": self.pick("sdg_target", "sdg:6.3"),
                                               "licence": self.pick("licence", "spdx:MIT"),
                                               "time_window": self.pick("time_window", "2024q2")}, {})
        q = dict(request["params"])["q"]
        self.assertIn('"water quality"', q)
        self.assertIn("license:mit", q)
        self.assertIn("pushed:2024-04-01..2024-06-30", q)
        self.assertIn("is:public", q)

    def test_code_search_needs_a_keyword(self):
        self.assertEqual(GitHubCode().render({"file_format": self.pick("file_format", "csv")}, {}), "code_search_needs_a_keyword")
        request = GitHubCode().render({"file_format": self.pick("file_format", "csv"), "sdg_target": self.pick("sdg_target", "sdg:6.1")}, {})
        self.assertEqual(dict(request["params"])["q"], '"drinking water" extension:csv')

    def test_openalex_filters_cost_one_credit_and_a_search_ten(self):
        executor = OpenAlexWorks()
        filtered = executor.render({"licence": self.pick("licence", "spdx:CC0-1.0")}, {})
        searched = executor.render({"sdg_target": self.pick("sdg_target", "sdg:6.1")}, {})
        self.assertEqual((executor.cost(filtered), executor.cost(searched)), (1, 10))

    def test_a_private_or_mislabelled_repository_row_is_rejected(self):
        body = json.dumps({"total_count": 3, "items": [
            {"full_name": "a/b", "html_url": "https://github.com/a/b", "private": False},
            {"full_name": "a/c", "html_url": "https://github.com/a/c", "private": True},
            {"full_name": "a/d", "html_url": "https://evil.example/a/d", "private": False}]}).encode()
        parsed = GitHubRepositories().parse(200, body)
        self.assertEqual([item["key"] for item in parsed.items], ["github:a/b"])
        self.assertEqual((parsed.rejected, parsed.status), (2, "partial"))


class LicenceAndRouteTests(unittest.TestCase):
    def test_reported_licences_become_leads_and_only_allowlisted_ones_pass(self):
        cases = {"MIT": True, "mit": True, "apache-2.0": True, "https://creativecommons.org/publicdomain/zero/1.0/": True,
                 "http://creativecommons.org/licenses/by/4.0/legalcode": True, "MIT OR GPL-3.0": True,
                 "cc-by": False, "CC-BY-2.0": False, "GPL-3.0": False, "NOASSERTION": False, None: False,
                 "https://creativecommons.org/licenses/by-nc/4.0/": False}
        for reported, allowed in cases.items():
            self.assertEqual(licence_lead(reported)[1], allowed, reported)
        self.assertEqual(licence_lead("cc-by")[2], "version_not_reported")

    def test_files_route_to_their_lines(self):
        base = {"kind": "file", "title": "o/r/x", "extra": {"repository": "o/r", "commit": "a" * 40}}
        self.assertEqual(route({**base, "extra": {**base["extra"], "path": "api/openapi.yaml"}})[0], "openapi_sources")
        self.assertEqual(route({**base, "extra": {**base["extra"], "path": "schemas/order.schema.json"}})[0], "json_schema_sources")
        line, row = route({**base, "extra": {**base["extra"], "path": "data/codes.csv"}})
        self.assertEqual((line, row["row"][5]), ("data_tables", "csv_records"))
        self.assertEqual(route({**base, "extra": {**base["extra"], "path": "skills/x/SKILL.md"}})[0], "harness_file_pool")


class LibraryTests(unittest.TestCase):
    def test_a_sensitive_value_is_refused(self):
        document = {"record_type": "research_dimension_library/v1", "version": "t", "provenance": [], "rules": [],
                    "dimensions": [{"id": "algorithm", "title": "t", "kind": "topic", "null_share": 0, "source": SOURCE,
                                    "values": [value("a", "someone@example.org")]}]}
        with self.assertRaises(DimensionError):
            read_library(document)
        document["dimensions"][0]["values"] = [value("a", "dijkstra")]
        self.assertEqual(len(read_library(document).dimension("algorithm").values), 1)

    def test_the_shipped_library_loads_its_repository_tables(self):
        library = load_library(only={"sdg_goal", "sdg_target", "geography", "natural_language", "natural_language_endonym",
                                     "harness_kind", "step_function", "licence", "file_format", "time_window"})
        self.assertEqual(len(library.dimension("sdg_target").values), 169)
        self.assertEqual(len(library.dimension("sdg_goal").values), 17)
        self.assertGreaterEqual(len(library.dimension("geography").values), 280)
        endonyms = {value.text for value in library.dimension("natural_language_endonym").values}
        self.assertTrue({"castellano", "español"} & endonyms)
        self.assertTrue({"deutsch", "日本語", "kiswahili"} <= endonyms)
        self.assertEqual({value.attributes["spdx"] for value in library.dimension("licence").values},
                         {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "0BSD", "CC0-1.0", "CC-BY-4.0", "Unlicense"})

    @unittest.skipUnless((Path.home() / "loop-engine-data/onet/31.0/text/Task Statements.txt").is_file(), "O*NET tables absent")
    def test_the_default_plan_builds_millions_of_queries(self):
        from query_multiplier.planner import load_plan, plan_dimensions
        path = ROOT / "tools/query_multiplier/plans/default-v1.json"
        library = load_library(data_roots={"onet": str(Path.home() / "loop-engine-data/onet/31.0/text")},
                               only=plan_dimensions(path))
        products = load_plan(path, library, registry())
        self.assertGreater(sum(product.total for product in products), 1_000_000)


class ImportTests(Temporary):
    def test_queues_import_as_plans_deduplicated_with_every_origin(self):
        ledger = self.ledger()
        jsonl = self.folder / "planned.jsonl"
        jsonl.write_text("\n".join(json.dumps(row) for row in (
            {"query_id": "1", "query": "\"Kenya\" water quality toolkit", "sdg": 6, "m49": "404"},
            {"query_id": "2", "query": "\"kenya\"   WATER quality toolkit", "sdg": 6, "m49": "404"},
            {"query_id": "3", "query": "\"Peru\" public transport manual", "sdg": 11, "m49": "604"},
            {"query_id": "4", "query": "write to someone@example.org", "sdg": 1, "m49": "004"})))
        importer = importers.Importer(ledger)
        importers.import_sdg_planned_searches(importer, jsonl)
        summary = importers.summary(ledger)
        self.assertEqual(summary["distinct_strings"], 2)
        self.assertEqual(ledger.scalar("select origins from imported where query_text like '%Kenya%'"), 2)
        self.assertEqual(ledger.scalar("select count(*) from queries"), 0)  # plans, never executions
        self.assertEqual(sum(v for k, v in importer.counts.items() if k.endswith("refused_by_screen")), 1)


class ParserTests(unittest.TestCase):
    """Each engine's parse on a canned answer: identities, licences as reported, and nothing private kept."""

    def test_every_source_parses_its_own_answer_into_candidates(self):
        from query_multiplier.executors import (Arxiv, DataEuropaDatasets, DataGovDatasets, GbifDatasets,
                                                HuggingFaceDatasets, NpmSearch, OllamaWebSearch, OpenAlexWorks,
                                                OpenverseImages)
        cases = [
            (HuggingFaceDatasets(), json.dumps([{"id": "org/set", "tags": ["license:cc-by-4.0"], "private": False}]),
             "hf-dataset:org/set", "cc-by-4.0"),
            (OpenAlexWorks(), json.dumps({"meta": {"count": 1}, "results": [{"id": "https://openalex.org/W1", "doi": "https://doi.org/10.1/X",
                                                                         "type": "dataset", "best_oa_location": {"license": "cc0"}}]}),
             "doi:10.1/x", "cc0"),
            (OpenverseImages(), json.dumps({"result_count": 1, "results": [{"id": "abc", "license": "by", "license_version": "2.0",
                                                                           "foreign_landing_url": "https://example.org/p"}]}),
             "openverse:abc", "CC-BY-2.0"),
            (GbifDatasets(), json.dumps({"count": 1, "results": [{"key": "k1", "license": "http://creativecommons.org/publicdomain/zero/1.0/legalcode"}]}),
             "gbif-dataset:k1", "CC0-1.0"),
            (DataEuropaDatasets(), json.dumps({"result": {"count": 1, "results": [{"id": "d1", "title": {"en": "T"},
                "distributions": [{"license": {"resource": "https://creativecommons.org/licenses/by/4.0/"}, "format": {"id": "CSV"},
                                   "download_url": ["https://example.org/a.csv"]}]}]}}),
             "europa:d1", "https://creativecommons.org/licenses/by/4.0/"),
            (DataGovDatasets(), json.dumps({"results": [{"identifier": "id-1", "dcat": {"title": "T", "landingPage": ["a", "b"],
                                                                                         "license": "http://www.usa.gov/publicdomain/label/1.0/"}}]}),
             "datagov:id-1", "http://www.usa.gov/publicdomain/label/1.0/"),
            (NpmSearch(), json.dumps({"total": 1, "objects": [{"package": {"name": "pkg", "license": "MIT",
                "maintainers": [{"email": "someone@example.org"}], "links": {"repository": "https://github.com/o/r"}}}]}),
             "npm:pkg", "MIT"),
            (OllamaWebSearch(), json.dumps({"results": [{"title": "T", "url": "https://arxiv.org/abs/2401.01234v2", "content": "x"}]}),
             "doi:10.48550/arxiv.2401.01234", None),
        ]
        for executor, body, key, licence in cases:
            parsed = executor.parse(200, body.encode())
            self.assertEqual(parsed.status, "ok", executor.executor_id)
            self.assertEqual(parsed.items[0]["key"], key, executor.executor_id)
            self.assertEqual(parsed.items[0]["licence_reported"], licence, executor.executor_id)
            self.assertNotIn("someone@example.org", json.dumps(parsed.items))
        atom = (b'<feed xmlns="http://www.w3.org/2005/Atom" xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/" '
                b'xmlns:arxiv="http://arxiv.org/schemas/atom"><opensearch:totalResults>1</opensearch:totalResults>'
                b'<entry><id>http://arxiv.org/abs/2512.01465v2</id><title>T</title></entry></feed>')
        parsed = Arxiv().parse(200, atom)
        self.assertEqual((parsed.items[0]["key"], parsed.total_count), ("doi:10.48550/arxiv.2512.01465", 1))

    def test_known_wrong_a_failed_or_malformed_answer_executes_nothing(self):
        from query_multiplier.executors import HuggingFaceModels, NpmSearch
        self.assertEqual(NpmSearch().parse(200, b"<html>not json</html>").status, "failed")
        self.assertEqual(NpmSearch().parse(503, b"{}").status, "failed")
        self.assertEqual(HuggingFaceModels().parse(200, b"[]").status, "empty")


class LicenceLaneTests(Temporary):
    def test_graphql_names_are_validated_before_any_process(self):
        from query_multiplier.transport import licence_query
        self.assertIn('repository(owner: "octo", name: "repo.js")', licence_query(["octo/repo.js"]))
        for bad in (['octo/repo") { x }'], ["-bad/name"], [], ["a/b"] * 51):
            with self.assertRaises(RequestRefused):
                licence_query(bad)

    def test_the_licence_lane_records_a_detected_licence_on_every_file_of_the_repository(self):
        from loop_engine.core.library_ingestion.processes import CommandResult
        from query_multiplier.runner import LicenceLane
        ledger = self.ledger()
        for key in ("github-file:octo/repo/api/openapi.yaml", "github-file:octo/repo/data/x.csv", "github-file:other/private/a.json"):
            with ledger.lock:
                ledger.db.execute("insert into candidates(key, url, kind, title, licence_reported, licence_field, licence_lead, "
                                  "allowlisted, licence_basis, route, first_query_id, first_executor, first_seen_at, first_day, origins, payload) "
                                  "values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,?)",
                                  (key, "u", "file", "t", None, "none", None, 0, "not_reported", "code_file_pool", "q", "github_code",
                                   "2026-10-05T00:00:00Z", "2026-10-05", "{}"))
                ledger.db.commit()
        answer = json.dumps({"data": {"r0": {"nameWithOwner": "octo/repo", "isPrivate": False, "isArchived": False,
                                             "licenseInfo": {"spdxId": "MIT"}},
                                      "r1": {"nameWithOwner": "other/private", "isPrivate": True, "licenseInfo": {"spdxId": "MIT"}}}})
        runner = lambda *a, **k: CommandResult(0, ("HTTP/2.0 200 OK\ncontent-type: application/json\n\n" + answer).encode(), "", 1.0, False, False)
        run = Run(library=small_library(), products=[], executors=registry(), ledger=ledger, minutes=1,
                  transport=Transport(load_policy(), runner=runner), resolve_licences=False)
        lane = LicenceLane(run)
        self.assertEqual(sorted(lane.pending()), ["octo/repo", "other/private"])
        lane.resolve(sorted(lane.pending()))
        rows = dict(ledger.rows("select key, allowlisted from candidates"))
        self.assertEqual(rows["github-file:octo/repo/api/openapi.yaml"], 1)
        self.assertEqual(rows["github-file:octo/repo/data/x.csv"], 1)
        # Known-wrong case in the same answer: a private repository's licence is never applied.
        self.assertEqual(rows["github-file:other/private/a.json"], 0)
        self.assertEqual(lane.pending(), [])
        self.assertEqual(ledger.scalar("select count(*) from attempts where state='folded'"), 1)


class ReportTests(Temporary):
    def test_the_report_keeps_counts_apart_and_compares_null_with_values(self):
        from query_multiplier.report import report
        ledger = self.ledger()
        library = small_library()
        executors = registry()
        [built] = read_plan(plan(product("repos", "github_repositories", [("sdg_target", None), ("licence", 0), ("geography", 50)])),
                            library, executors)
        transport = FakeTransport(repo_rows("a/one", "a/two"))
        run = Run(library=library, products=[built], executors=executors, transport=transport, ledger=ledger, minutes=1,
                  resolve_licences=False)
        lane, stream = run.lanes[0], run.lanes[0].streams[0]
        for index in range(6):
            transport.body = repo_rows(f"a/{index}", "a/shared")
            lane.attempt(stream.next(), stream)
        value = report(ledger, executors, bucket=2)
        lane_report = value["lanes"]["github_repositories"]
        self.assertEqual((lane_report["requests_sent"], lane_report["queries_executed"], lane_report["raw_results"]), (6, 6, 12))
        self.assertEqual(lane_report["new_unique_candidates"], 7)
        self.assertEqual(value["candidates"]["distinct"], 7)
        self.assertEqual(value["candidates"]["found_by_more_than_one_query"], 1)
        presence = value["yields"]["by_dimension_presence"]["geography"]
        self.assertEqual(sum(side["executions"] for side in presence.values()), 6)
        self.assertIsNotNone(value["projection"]["new_unique_per_day_upper"])


class ProposalTests(Temporary):
    def test_files_of_one_repository_become_one_row_with_every_path(self):
        from query_multiplier.routing import proposals
        ledger = self.ledger()
        for path in ("a/openapi.yaml", "b/openapi.json"):
            item = {"key": "github-file:o/r/" + path, "kind": "file", "title": "o/r/" + path,
                    "extra": {"repository": "o/r", "path": path, "commit": "c" * 40}}
            line, row = route(item)
            with ledger.lock:
                ledger.db.execute("insert into candidates(key, url, kind, title, licence_reported, licence_field, licence_lead, "
                                  "allowlisted, licence_basis, route, first_query_id, first_executor, first_seen_at, first_day, origins, payload) "
                                  "values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,?)",
                                  (item["key"], "u", "file", "t", "MIT", "f", "MIT", 1, "spdx_identifier", line, "q", "github_code",
                                   "2026-10-05T00:00:00Z", "2026-10-05", json.dumps({"proposal": row})))
                ledger.db.commit()
        value = proposals(ledger)
        rows = value["lines"]["openapi_sources"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(sorted(rows[0]["paths"]), ["a/openapi.yaml", "b/openapi.json"])
        self.assertEqual(len(rows[0]["evidence"]), 2)


class ScheduledCredentialBoundaryTests(unittest.TestCase):
    def test_wrapper_inherits_keys_without_executing_shell_profile_assignments(self):
        source = (ROOT / "tools/query_multiplier/scheduled-run.sh").read_text()
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            scripts = folder / "tools/query_multiplier"
            scripts.mkdir(parents=True)
            marker = folder / "profile-executed"
            (folder / ".bashrc").write_text('export OLLAMA_API_KEY="$(touch ' + shlex.quote(str(marker))
                                            + '; printf synthetic-fixture-key)"\n')
            probe = folder / "python-probe"
            probe.write_text("#!/usr/bin/env python3\nimport json,os\n"
                             "print(json.dumps({'key_present':'OLLAMA_API_KEY' in os.environ}))\n")
            probe.chmod(0o700)
            wrapper = scripts / "scheduled-run.sh"
            environment = {"HOME": str(folder), "PATH": os.environ["PATH"],
                           "QUERY_MULTIPLIER_ROOT": str(folder / "evidence"),
                           "QUERY_MULTIPLIER_PYTHON": str(probe)}
            for present in (False, True):
                wrapper.write_text(source)
                selected = {**environment, **({"OLLAMA_API_KEY": "inherited-fixture"} if present else {})}
                result = subprocess.run(["bash", str(wrapper)], env=selected, capture_output=True,
                                        text=True, timeout=10)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout), {"key_present": present})
                self.assertFalse(marker.exists())
            # Known wrong: even evaluating only an apparent export assignment executes its substitution.
            broken = source.replace('minutes="${QUERY_MULTIPLIER_MINUTES:-20}"',
                'eval "$(grep -E \'^export OLLAMA_API_KEY=\' \"$HOME/.bashrc\")"\n'
                'minutes="${QUERY_MULTIPLIER_MINUTES:-20}"')
            self.assertNotEqual(broken, source)
            wrapper.write_text(broken)
            result = subprocess.run(["bash", str(wrapper)], env=environment, capture_output=True,
                                    text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(marker.exists(), "the known-wrong wrapper must execute the seeded substitution")


if __name__ == "__main__":
    unittest.main()
