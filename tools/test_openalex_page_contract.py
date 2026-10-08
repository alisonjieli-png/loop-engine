"""Offline source-page-size, replay and shared-quota controls. No live OpenAlex calls."""
from datetime import datetime, timedelta, timezone
import json
import unittest

from tools import test_query_multiplier as fixtures
from tools.test_query_multiplier import (ClockedLedger, FakeTransport, Temporary,
                                         plan, product, small_library)
from query_multiplier.executors import OpenAlexWorks, registry
from query_multiplier.planner import PlannedQuery, query_identity, read_plan
from query_multiplier.runner import Run
from query_multiplier.transport import Answer, RequestRefused, Transport, load_policy


class OpenAlexPageContract(Temporary):
    def request(self, page=1):
        library = small_library()
        return OpenAlexWorks().render({"licence": library.dimension("licence").value("spdx:CC0-1.0")}, {}, page=page)

    def lane(self, ledger):
        library, executors = small_library(), registry()
        [built] = read_plan(plan(product("papers", "openalex_works", [("licence", 0)])), library, executors)
        wire = FakeTransport(b'{"meta":{"count":0},"results":[]}')
        run = Run(library=library, products=[built], executors=executors, ledger=ledger, transport=wire,
                  minutes=1, resolve_licences=False, learn=False, minimum_free_bytes=0)
        return run.lanes[0], wire

    def test_first_and_follow_pages_use_the_documented_maximum(self):
        executor = OpenAlexWorks()
        for page in (1, 2):
            request = self.request(page)
            self.assertEqual(dict(request["params"])["per-page"], "100")
            self.assertEqual(dict(request["params"])["page"], str(page))
            self.assertTrue(executor.request_compatible(request))
        self.assertEqual(executor.executor_version, "1.0.1")
        self.assertEqual((executor.daily_ceiling, executor.minimum_interval, executor.refresh_days,
                          executor.follow_pages, executor.cost_unit), (700, 4.0, 60, 2, "openalex_credit"))

    def test_old_oversized_ambiguous_and_malformed_requests_are_refused_before_dispatch(self):
        executor, opener = OpenAlexWorks(), fixtures.HostTests.Opener()
        transport = Transport(load_policy(), opener=opener)
        for sizes in ([], ["0"], ["101"], ["200"], ["-1"], ["100.0"], [True], ["１００"], ["1" * 1000], ["100", "200"]):
            request = self.request()
            request["params"] = [pair for pair in request["params"] if pair[0] != "per-page"]
            request["params"] += [["per-page", value] for value in sizes]
            with self.subTest(sizes=sizes), self.assertRaises(RequestRefused) as failure:
                transport.send(executor, request)
            self.assertEqual(failure.exception.code, "executor_request_incompatible")
        request = self.request();request["params"].append(["per_page", "100"])
        self.assertFalse(executor.request_compatible(request))
        request["params"] = [["per-page"]]
        self.assertFalse(executor.request_compatible(request))
        self.assertEqual(opener.calls, [])

    def test_removing_the_source_guard_admits_the_old_wrong_request(self):
        executor = OpenAlexWorks()
        request = self.request();request["params"] = [[key, "200" if key == "per-page" else value] for key, value in request["params"]]
        transport = Transport(load_policy(), opener=fixtures.HostTests.Opener())
        with self.assertRaises(RequestRefused):transport.check(executor, request)
        executor.request_compatible = lambda request: True
        transport.check(executor, request)  # known wrong: the old 200-row request is no longer refused

    def test_changed_request_and_product_get_new_identity(self):
        current = OpenAlexWorks();old = OpenAlexWorks();old.per_page = 200;old.executor_version = "1.0.0"
        library = small_library()
        assignment = {"licence": library.dimension("licence").value("spdx:CC0-1.0")}
        before, after = old.render(assignment, {}), current.render(assignment, {})
        self.assertNotEqual(query_identity(old.executor_id, before), query_identity(current.executor_id, after))
        source = plan(product("papers", "openalex_works", [("licence", 0)]))
        previous = read_plan(source, library, {old.executor_id: old})[0]
        revised = read_plan(source, library, {current.executor_id: current})[0]
        self.assertNotEqual(previous.digest, revised.digest)
        self.assertEqual(old.executor_id, current.executor_id)
        self.assertEqual((old.cost(before), current.cost(after)), (1, 1))

    def test_old_saved_evidence_is_retained_but_not_refreshed(self):
        clock = ClockedLedger(datetime(2026, 10, 8, tzinfo=timezone.utc))
        ledger = self.ledger(clock=clock)
        request = self.request();request["params"] = [[key, "200" if key == "per-page" else value] for key, value in request["params"]]
        query = PlannedQuery("papers", "openalex_works", 0, {}, request, query_identity("openalex_works", request))
        ledger.plan(query);attempt = ledger.intent(query, "historical_fixture", 1)
        saved = ledger.store(attempt, query, request, Answer(200, {}, b'{"meta":{"count":0},"results":[]}', 1.0))
        ledger.mark_executed(attempt, query, parse_status="empty", total_count=0, refresh_days=60)
        path = ledger.root / saved["path"];before = path.read_bytes()
        clock.now += timedelta(days=61)
        lane, wire = self.lane(ledger)
        self.assertIsNone(lane.due_refresh())
        self.assertEqual(lane.stats["refreshes_incompatible_request_skipped"], 1)
        self.assertEqual(wire.sent, [])
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(json.loads(ledger.rows("select request from queries where query_id=?", (query.query_id,))[0][0]), request)
        fresh = lane.streams[0].next()
        self.assertEqual(dict(fresh.request["params"])["per-page"], "100")
        self.assertNotEqual(fresh.query_id, query.query_id)
        # Removed-guard control: the same due record becomes eligible if source compatibility is ignored.
        lane.executor.request_compatible = lambda request: True
        self.assertEqual(lane.due_refresh()[0].query_id, query.query_id)

    def test_page_change_keeps_daily_ceiling_and_provider_hold_namespace(self):
        ledger = self.ledger("budget");lane, wire = self.lane(ledger)
        query = lane.streams[0].next();ledger.plan(query);ledger.intent(query, "quota_fixture", 700)
        self.assertEqual(lane.wait_reason(), "daily_ceiling_reached")
        self.assertEqual(ledger.usage("openalex_works"), (1, 700))
        self.assertEqual(ledger.usage("openalex_works:1.0.1"), (0, 0))  # wrong quota namespace would reset usage
        other = self.ledger("hold");held, other_wire = self.lane(other)
        other.set_hold("openalex_works", "rate_limited_429", datetime.now(timezone.utc) + timedelta(hours=1))
        self.assertEqual(held.wait_reason(), "held:rate_limited_429")
        self.assertEqual(wire.sent + other_wire.sent, [])


if __name__ == "__main__":unittest.main()
