"""Offline durable accounting checks; no keyring, provider or external network."""
from contextlib import contextmanager, redirect_stdout
from dataclasses import replace
import hashlib
import http.client
from io import StringIO
import json
import multiprocessing
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest
from unittest.mock import patch

from loop_engine.core.capability_directory import CapabilityDirectory
from loop_engine.core.brave_search import HttpResponse, UrllibTransport
from loop_engine.core.library_ingestion.request_log import RequestBudget
from loop_engine.core.web_research_engines import WebResearchPolicy, WebResearchRequest, register_web_research
from loop_engine.core.web_research_quota import (AccountQuota, DurableSearchQuota, QuotaOutcome, QuotaRefused,
    SearchQuotaPolicy, reported_microusd)
from probe_web_research import load_quota_policy, main
from test_web_research_engines import QUERY, TOKEN, Wire, body, prepared

DIGEST = hashlib.sha256(b"offline request fixture").hexdigest()
EVIDENCE = hashlib.sha256(b"operator reconciliation fixture").hexdigest()


def limits(provider="exa", *, daily=10, window=60, maximum=10, cost=None, reserve=None):
    return AccountQuota(provider + ":shared-account", daily, window, maximum, cost, reserve)


def policy(*accounts):
    return SearchQuotaPolicy("offline-fixture-allowance", "1.0.0", accounts or (limits(),))


def outcome(*, status=200, cost=None, retry=None, zero=False):
    return QuotaOutcome(status, status == 200, cost, retry, zero, DIGEST if status is not None else None)


def process_reservation(path, record, start, results):
    """Contend on one file from separate interpreters, never on a shared Python lock."""
    store = DurableSearchQuota(Path(path), SearchQuotaPolicy.from_record(record), True, clock=lambda: 1000)
    start.wait(10)
    for _ in range(100):
        try:
            reservation = store.reserve("exa:shared-account", DIGEST)
            store.finish(reservation, outcome(cost=200))
            results.put("accepted")
            return
        except QuotaRefused as error:
            if str(error) != "quota_outcome_pending":
                results.put(str(error))
                return
            # No request was dispatched or reserved on this failed preflight.
            time.sleep(0.005)
    results.put("contention_timeout")


class DurableQuotaTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "accounting.sqlite"
        self.now = [1000.0]

    def store(self, rules=None, **kwargs):
        return DurableSearchQuota(self.path, rules or policy(), True, clock=lambda: self.now[0], **kwargs)

    def backend(self, provider, store, **kwargs):
        shared = WebResearchPolicy(RequestBudget(100), {provider + ":shared-account": RequestBudget(100)},
                                   time.monotonic() + 30, durable=store)
        return prepared(provider, policy=shared, **kwargs)

    def search(self, backend):
        return backend.search(WebResearchRequest(QUERY, "offline qualification"), access_mode="approved_external_read")

    def test_construction_discovery_and_denied_access_do_not_create_state_or_read_secrets(self):
        with patch("loop_engine.core.web_research_quota.sqlite3.connect", side_effect=AssertionError("no database effects")):
            store = self.store()
            backend, wire, secrets = self.backend("exa", store)
            directory = CapabilityDirectory()
            register_web_research(directory, config=backend.config, secret_provider=secrets, policy=backend.policy, transport=wire)
            directory.search_core("search public web")
            denied = backend.search(WebResearchRequest(QUERY, "fixture"))
            self.assertEqual(denied["error_code"], "internet_access_denied")
        self.assertFalse(self.path.exists())
        self.assertEqual((wire.calls, secrets.calls), ([], 0))
        denied_store = replace(store, allow_writes=False)
        backend, wire, secrets = self.backend("exa", denied_store)
        self.assertEqual(self.search(backend)["error_code"], "quota_accounting_write_grant_required")
        self.assertEqual((wire.calls, secrets.calls), ([], 0))
        self.assertFalse(self.path.exists())

    def test_default_real_transport_requires_durable_authority_before_secret_or_dispatch(self):
        backend, _, secrets = prepared("exa")
        for wire in (None, UrllibTransport()):
            default_backend = replace(backend, transport=wire)
            self.assertEqual(self.search(default_backend)["error_code"], "durable_quota_required")
        self.assertEqual((secrets.calls, backend.policy.total.used), (0, 0))

    def test_strict_policy_and_outcome_versions_bounds_and_unknown_numbers(self):
        rules = policy()
        self.assertEqual(SearchQuotaPolicy.from_record(rules.to_record()), rules)
        for changes in ({"record_type": "web_research_quota_policy/v9"}, {"day_timezone": "local"}, {"extra": True}):
            with self.assertRaises(QuotaRefused):
                SearchQuotaPolicy.from_record({**rules.to_record(), **changes})
        for changes in ({"daily_requests": True}, {"window_seconds": 0}, {"window_requests": 11},
                        {"daily_cost_microusd": 1}, {"account": "credential alias with spaces"}):
            with self.assertRaises(QuotaRefused):
                replace(limits(), **changes)
        with self.assertRaises(QuotaRefused):
            policy(limits(), limits())
        self.assertEqual(reported_microusd(0.0000001), 1)
        for value in (True, float("nan"), float("inf"), -1, 10 ** 400, "1"):
            self.assertIsNone(reported_microusd(value))
        for retry in (True, float("inf"), -1, 10 ** 400):
            with self.assertRaises(QuotaRefused):
                outcome(retry=retry)
        with self.assertRaises(QuotaRefused):
            replace(self.store(), clock=lambda: 10 ** 400).reserve("exa:shared-account", DIGEST)
        self.assertFalse(self.path.exists())

    def test_atomic_reservation_precedes_wire_and_metadata_store_excludes_content(self):
        store = self.store()
        backend, _, secrets = self.backend("exa", store)

        class InspectedWire(Wire):
            def get(inner, url, **kwargs):
                self.assertEqual(store.snapshot("exa:shared-account")["requests_reserved_today"], 1)
                self.assertEqual(len(store.snapshot("exa:shared-account")["unresolved_reservations"]), 1)
                return super().get(url, **kwargs)
        wire = InspectedWire(HttpResponse(200, {}, json.dumps(body("exa")).encode()))
        answer = self.search(replace(backend, transport=wire))
        self.assertTrue(answer["ok"])
        self.assertEqual((len(wire.calls), secrets.calls, answer["attempt_count"]), (1, 1, 1))
        view = store.snapshot("exa:shared-account")
        self.assertEqual((view["requests_reserved_today"], view["reported_cost_microusd_subtotal"]), (1, 7000))
        self.assertEqual((view["other_account_usage"], view["unresolved_reservations"]), ("unknown", []))
        for file in self.path.parent.iterdir():
            content = file.read_bytes()
            for absent in (TOKEN, QUERY, "Fixture source", "fixture excerpt", "https://example.invalid/documentation"):
                self.assertNotIn(absent.encode(), content)
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)

    def test_decoded_reflection_failure_still_charges_observed_cost_and_account_request(self):
        token = 'offline\\fixture"credential'
        rules = policy(limits(daily=1, maximum=1, cost=10000, reserve=10000))
        store = self.store(rules)
        document = body("exa")
        document["results"][0]["highlights"] = [token]
        backend, wire, secrets = self.backend("exa", store, raw=json.dumps(document).encode())
        secrets.values[backend.config.secret_ref] = token
        result = self.search(backend)
        self.assertEqual((result["ok"], result["error_code"], result["candidates"]),
                         (False, "credential_reflected_by_provider", []))
        self.assertEqual((result["attempt_count"], len(wire.calls)), (1, 1))
        view = self.store(rules).snapshot("exa:shared-account")
        self.assertEqual((view["requests_reserved_today"], view["reported_cost_microusd_subtotal"], view["unresolved_reservations"]), (1, 7000, []))
        self.assertEqual(view["refusal"], "quota_daily_requests_exhausted")
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute("SELECT state,outcome,actual_cost FROM reservations").fetchone(), ("completed", "failed_response", 7000))
        self.assertNotIn(token.encode(), self.path.read_bytes())

    def test_restart_new_key_and_instance_cannot_reset_daily_account_allowance(self):
        rules = policy(limits(daily=1, maximum=1))
        backend, _, _ = self.backend("exa", self.store(rules), alias="first-key")
        self.assertTrue(self.search(backend)["ok"])
        second, wire, secrets = self.backend("exa", self.store(rules), alias="replacement-key")
        denied = self.search(second)
        self.assertEqual(denied["error_code"], "quota_daily_requests_exhausted")
        self.assertEqual((wire.calls, secrets.calls, second.policy.total.used), ([], 0, 0))
        self.assertEqual(self.store(rules).snapshot("exa:shared-account")["requests_reserved_today"], 1)

    def test_day_rollover_and_rolling_window_do_not_reset_each_other(self):
        self.now[0] = 86399
        store = self.store(policy(limits(daily=2, maximum=1, window=60)))
        one = store.reserve("exa:shared-account", DIGEST)
        store.finish(one, outcome())
        self.now[0] = 86401
        self.assertEqual(store.refusal("exa:shared-account"), "quota_window_requests_exhausted")
        self.assertEqual(store.snapshot("exa:shared-account")["requests_reserved_today"], 0)
        self.now[0] = 86459
        self.assertEqual(store.refusal("exa:shared-account"), "")
        two = store.reserve("exa:shared-account", DIGEST)
        store.finish(two, outcome())
        self.now[0] = 86400
        self.assertEqual(store.refusal("exa:shared-account"), "quota_clock_regressed")

    def test_time_is_read_after_lock_acquisition_for_day_counts_and_cooldowns(self):
        store = self.store()
        self.now[0] = 86399
        transaction = DurableSearchQuota._transaction

        @contextmanager
        def delayed(owner, **kwargs):
            with transaction(owner, **kwargs) as db:
                self.now[0] += 2
                yield db

        with patch.object(DurableSearchQuota, "_transaction", delayed):
            reservation = store.reserve("exa:shared-account", DIGEST)
            store.finish(reservation, outcome(status=429, retry=5))
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute("SELECT reserved_at,day FROM reservations").fetchone(), (86401, 1))
            self.assertEqual(db.execute("SELECT until_at FROM holds").fetchone()[0], 86408)

    def test_eight_processes_share_one_atomic_daily_and_cost_ceiling(self):
        rules = policy(limits(daily=3, maximum=3, cost=600, reserve=200))
        context = multiprocessing.get_context("spawn")
        start, results = context.Event(), context.Queue()
        workers = [context.Process(target=process_reservation, args=(str(self.path), rules.to_record(), start, results)) for _ in range(8)]
        try:
            for worker in workers:
                worker.start()
            start.set()
            answers = [results.get(timeout=20) for _ in workers]
            for worker in workers:
                worker.join(5)
                self.assertEqual(worker.exitcode, 0)
            self.assertEqual(answers.count("accepted"), 3, answers)
            self.assertEqual(answers.count("quota_daily_requests_exhausted"), 5, answers)
            view = self.store(rules).snapshot("exa:shared-account")
            self.assertEqual((view["requests_reserved_today"], view["reported_cost_microusd_subtotal"]), (3, 600))
        finally:
            for worker in workers:
                if worker.is_alive():
                    worker.terminate()
                worker.join(5)
            results.close()

    def test_completed_reservation_is_idempotent_conflicts_are_refused(self):
        store = self.store()
        reservation = store.reserve("exa:shared-account", DIGEST)
        store.finish(reservation, outcome(cost=7000))
        store.finish(reservation, outcome(cost=7000))
        with self.assertRaisesRegex(QuotaRefused, "quota_completion_conflict"):
            store.finish(reservation, outcome(cost=6000))
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM events").fetchone()[0], 2)
        self.assertEqual(store.snapshot("exa:shared-account")["requests_reserved_today"], 1)

    def test_unknown_stored_lifecycle_is_refused_without_reflecting_record_text(self):
        store = self.store()
        reservation = store.reserve("exa:shared-account", DIGEST)
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE reservations SET state=? WHERE id=?", ("future-state-" + TOKEN, reservation))
        self.assertEqual(store.refusal("exa:shared-account"), "quota_record_state_invalid")
        backend, wire, secrets = self.backend("exa", store)
        result = self.search(backend)
        self.assertEqual(result["error_code"], "quota_record_state_invalid")
        self.assertNotIn(TOKEN, str(result))
        self.assertEqual((wire.calls, secrets.calls), ([], 0))

    def test_known_cost_reservation_bounds_and_unknown_cost_are_not_zero(self):
        rules = policy(limits(cost=15000, reserve=8000))
        store = self.store(rules)
        for _ in range(2):
            backend, _, _ = self.backend("exa", store)
            self.assertTrue(self.search(backend)["ok"])
        self.assertEqual(store.refusal("exa:shared-account"), "quota_daily_cost_exhausted")
        self.assertEqual(store.snapshot("exa:shared-account")["reported_cost_microusd_subtotal"], 14000)
        self.now[0] += 86400
        document = body("exa")
        document.pop("costDollars")
        backend, _, _ = self.backend("exa", store, raw=json.dumps(document).encode())
        self.assertTrue(self.search(backend)["ok"])
        self.assertEqual(store.refusal("exa:shared-account"), "quota_outcome_pending")
        view = store.snapshot("exa:shared-account")
        self.assertEqual((view["reported_cost_microusd_subtotal"], view["requests_with_unknown_cost"]), (0, 1))
        with self.assertRaisesRegex(QuotaRefused, "quota_reconciliation_cost_required"):
            store.reconcile(view["unresolved_reservations"][0], evidence_digest=EVIDENCE)
        store.reconcile(view["unresolved_reservations"][0], evidence_digest=EVIDENCE, actual_cost_microusd=7000)
        self.assertEqual(store.snapshot("exa:shared-account")["requests_reserved_today"], 1)
        self.assertEqual(store.refusal("exa:shared-account"), "")

    def test_cost_bound_exceeded_is_recorded_truthfully_and_holds_account(self):
        rules = policy(limits(cost=15000, reserve=6000))
        store = self.store(rules)
        backend, _, _ = self.backend("exa", store)
        self.assertTrue(self.search(backend)["ok"])
        self.assertEqual(store.refusal("exa:shared-account"), "quota_account_held")
        self.assertEqual(store.snapshot("exa:shared-account")["reported_cost_microusd_subtotal"], 7000)

    def test_rate_limit_cooldown_survives_restart_and_expires_without_retry(self):
        store = self.store()
        backend, wire, _ = self.backend("exa", store, status=429, headers={"Retry-After": "5"}, raw=b"refused")
        self.assertEqual(self.search(backend)["error_code"], "rate_limited")
        self.assertEqual(len(wire.calls), 1)
        self.now[0] += 4
        backend, wire, secrets = self.backend("exa", self.store(), alias="replacement-key")
        self.assertEqual(self.search(backend)["error_code"], "quota_cooldown_active")
        self.assertEqual((wire.calls, secrets.calls), ([], 0))
        self.now[0] += 1
        self.assertTrue(self.search(backend)["ok"])
        self.assertEqual(len(wire.calls), 1)

    def test_success_remaining_zero_obeys_all_brave_windows(self):
        rules = policy(limits("brave"))
        store = self.store(rules)
        backend, _, _ = self.backend("brave", store, headers={"X-RateLimit-Remaining": "0,0", "X-RateLimit-Reset": "1,45"})
        result = self.search(backend)
        self.assertTrue(result["ok"])
        self.assertEqual(result["retry_after_seconds"], 45)
        self.now[0] += 44
        self.assertEqual(self.store(rules).refusal("brave:shared-account"), "quota_cooldown_active")
        self.now[0] += 1
        self.assertEqual(self.store(rules).refusal("brave:shared-account"), "")

    def test_unknown_cooldown_or_access_refusal_never_expires_from_guesswork(self):
        for status, headers in ((200, {"X-RateLimit-Remaining": "0"}), (429, {}), (401, {}),
                                (200, {"X-RateLimit-Remaining": "0,0", "X-RateLimit-Reset": "1,unknown"})):
            with self.subTest(status=status, headers=headers), tempfile.TemporaryDirectory() as folder:
                rules = policy(limits("brave"))
                store = DurableSearchQuota(Path(folder) / "quota.sqlite", rules, True, clock=lambda: self.now[0])
                backend, _, _ = self.backend("brave", store, status=status, headers=headers)
                self.search(backend)
                self.now[0] += 86400
                self.assertEqual(store.refusal("brave:shared-account"), "quota_account_held")

    def test_unknown_protocol_outcome_survives_alias_restart_and_day_change_without_leak(self):
        for provider in ("brave", "exa", "tavily"):
            with self.subTest(provider=provider), tempfile.TemporaryDirectory() as folder:
                rules = policy(limits(provider))
                store = DurableSearchQuota(Path(folder) / "quota.sqlite", rules, True, clock=lambda: self.now[0])
                backend, wire, secrets = self.backend(provider, store)
                calls = []

                class BadOpener:
                    def open(self, request, timeout):
                        calls.append(request)
                        raise http.client.BadStatusLine("reflected " + TOKEN)
                wire = UrllibTransport(1024, BadOpener())
                directory = CapabilityDirectory()
                register_web_research(directory, config=backend.config, secret_provider=secrets, policy=backend.policy, transport=wire)
                result = directory.call("web_research_search", "search", request=WebResearchRequest(QUERY, "fixture"),
                                        access_mode="approved_external_read")
                self.assertEqual((result.value["error_code"], result.value["attempt_count"]), ("transport_failure", 1))
                self.assertEqual(len(calls), 1)
                self.assertNotIn(TOKEN, str(result))
                self.now[0] += 86400
                backend, wire, secrets = self.backend(provider, replace(store), alias="replacement-key")
                self.assertEqual(self.search(backend)["error_code"], "quota_outcome_pending")
                self.assertEqual((wire.calls, secrets.calls), ([], 0))
                self.assertNotIn(TOKEN.encode(), store.state_path.read_bytes())

    def test_process_cancellation_propagates_but_pending_reservation_blocks_another_call(self):
        store = self.store()
        backend, _, _ = self.backend("exa", store)

        class CancelledWire:
            def post(self, *args, **kwargs):
                raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):
            self.search(replace(backend, transport=CancelledWire()))
        self.assertEqual(self.store().refusal("exa:shared-account"), "quota_outcome_pending")
        self.assertEqual(store.snapshot("exa:shared-account")["requests_reserved_today"], 1)

    def test_explicit_reconciliation_keeps_original_reservation_and_immutable_event(self):
        store = self.store(policy(limits(daily=1, maximum=1)))
        reservation = store.reserve("exa:shared-account", DIGEST)
        store.finish(reservation, outcome(status=None))
        with self.assertRaisesRegex(QuotaRefused, "quota_reconciliation_evidence_required"):
            store.reconcile(reservation, evidence_digest="")
        store.reconcile(reservation, evidence_digest=EVIDENCE)
        self.assertEqual(store.refusal("exa:shared-account"), "quota_daily_requests_exhausted")
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM reservations").fetchone()[0], 1)
            self.assertEqual(db.execute("SELECT event_type FROM events ORDER BY sequence").fetchall(),
                             [("reserved",), ("completed",), ("reconciled",)])
        with self.assertRaisesRegex(QuotaRefused, "quota_reconciliation_state"):
            store.reconcile(reservation, evidence_digest=EVIDENCE)

    def test_completion_storage_failure_preserves_unknown_reservation_and_attempt_count(self):
        store = self.store()
        backend, wire, _ = self.backend("exa", store)
        with patch.object(DurableSearchQuota, "finish", side_effect=QuotaRefused("quota_state_unavailable")):
            result = self.search(backend)
        self.assertEqual((result["error_code"], result["attempt_count"], len(wire.calls)), ("quota_completion_unknown", 1, 1))
        self.assertEqual(result["candidates"], [])
        self.assertEqual(self.store().refusal("exa:shared-account"), "quota_outcome_pending")

    def test_waiting_for_accounting_cannot_dispatch_after_the_run_deadline(self):
        store = self.store()
        backend, wire, _ = self.backend("exa", store)
        reserve = DurableSearchQuota.reserve

        def delayed(owner, *args):
            reservation = reserve(owner, *args)
            backend.policy.deadline = time.monotonic() - 1
            return reservation

        with patch.object(DurableSearchQuota, "reserve", delayed):
            result = self.search(backend)
        self.assertEqual(result["error_code"], "research_deadline_exhausted_after_reservation")
        self.assertEqual((result["attempt_count"], wire.calls, backend.policy.total.used), (0, [], 1))
        self.assertEqual(store.refusal("exa:shared-account"), "quota_outcome_pending")

    def test_mutated_policy_path_or_grant_cannot_rebind_a_selected_engine(self):
        store = self.store()
        for change in (None, replace(store, state_path=self.path.with_name("other.sqlite")), replace(store, allow_writes=False)):
            backend, wire, secrets = self.backend("exa", store)
            backend.policy.durable = change
            self.assertEqual(self.search(backend)["error_code"], "quota_binding_changed")
            self.assertEqual((wire.calls, secrets.calls), ([], 0))
        self.assertFalse(self.path.exists())

    def test_edited_policy_cannot_reset_existing_store_or_counters(self):
        original = policy(limits(daily=1, maximum=1))
        store = self.store(original)
        reservation = store.reserve("exa:shared-account", DIGEST)
        store.finish(reservation, outcome())
        changed = self.store(policy(limits(daily=10, maximum=10)))
        self.assertEqual(changed.refusal("exa:shared-account"), "quota_policy_changed")
        with self.assertRaisesRegex(QuotaRefused, "quota_policy_changed"):
            changed.reserve("exa:shared-account", DIGEST)
        self.assertEqual(store.snapshot("exa:shared-account")["requests_reserved_today"], 1)

    def test_removed_guard_known_wrong_control_is_detected_by_restart_ceiling_assertion(self):
        store = self.store(policy(limits(daily=1, maximum=1)))
        one = store.reserve("exa:shared-account", DIGEST)
        store.finish(one, outcome())
        with self.assertRaisesRegex(QuotaRefused, "quota_daily_requests_exhausted"):
            store.reserve("exa:shared-account", DIGEST)
        # Mutant: deleting the transaction's admission decision authorizes a
        # second dispatch. The same assertion now fails, proving sensitivity.
        with patch.object(DurableSearchQuota, "_reason", return_value=""):
            with self.assertRaises(AssertionError):
                with self.assertRaises(QuotaRefused):
                    store.reserve("exa:shared-account", DIGEST)

    def test_foreign_version_symlink_public_file_and_nonhash_request_refused(self):
        store = self.store()
        with self.assertRaisesRegex(QuotaRefused, "quota_request_digest_invalid"):
            store.reserve("exa:shared-account", QUERY)
        self.assertFalse(self.path.exists())
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TABLE metadata(key TEXT PRIMARY KEY, value TEXT)")
            db.execute("INSERT INTO metadata VALUES('record_type','web_research_quota_store/v999')")
        self.path.chmod(0o600)
        self.assertEqual(store.refusal("exa:shared-account"), "quota_store_version")
        self.path.chmod(0o644)
        self.assertEqual(store.refusal("exa:shared-account"), "quota_file_not_private")
        alias = self.path.with_name("alias.sqlite")
        alias.symlink_to(self.path)
        self.assertEqual(replace(store, state_path=alias).refusal("exa:shared-account"), "quota_state_unavailable")


class DurableProbeTests(unittest.TestCase):
    def test_cli_requires_policy_state_and_accounting_grant_before_keyring(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            manifest = root / "references.json"
            manifest.write_text(json.dumps({"record_type": "operator_credential_references/v1", "api_keys": {"fixture": {
                "service": "exa", "account": "shared-account", "purpose": "bounded-research-search", "environment": "EXA_API_KEY"}}}))
            args = ["--provider", "exa", "--credential-ref", "fixture", "--credentials", str(manifest), "--query", QUERY]
            rules = root / "policy.json"
            rules.write_text(json.dumps(policy(limits(daily=1, maximum=1)).to_record()))
            flags = ["--authorize-network", "--authorize-accounting-writes", "--quota-policy", str(rules), "--quota-state", str(root / "state.sqlite")]
            for missing in ("--authorize-accounting-writes", "--quota-policy", "--quota-state"):
                selected = list(flags)
                index = selected.index(missing)
                del selected[index:index + (1 if missing == "--authorize-accounting-writes" else 2)]
                output = StringIO()
                with patch("probe_web_research.operator_credentials.resolve", side_effect=AssertionError("no keyring")), redirect_stdout(output):
                    self.assertEqual(main(args + selected), 2)
                self.assertEqual(json.loads(output.getvalue())["run_requests_reserved"], 0)
            wire = Wire(HttpResponse(200, {}, json.dumps(body("exa")).encode()))
            for expected in (0, 1):
                output = StringIO()
                with patch("probe_web_research.operator_credentials.resolve", return_value=TOKEN) as keys, \
                     patch("loop_engine.core.web_research_engines.UrllibTransport", return_value=wire), redirect_stdout(output):
                    self.assertEqual(main(args + flags), expected)
                result = json.loads(output.getvalue())
                self.assertEqual(result["accounting"]["requests_reserved_today"], 1)
                self.assertEqual(keys.call_count, 1 if expected == 0 else 0)
                for absent in (TOKEN, QUERY, "fixture excerpt", "Fixture source"):
                    self.assertNotIn(absent, output.getvalue())
            self.assertEqual(len(wire.calls), 1)

    def test_policy_loader_refuses_duplicate_oversized_and_unknown_fields(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "policy.json"
            for raw in ('{"record_type":"x","record_type":"y"}', " " * 65537, '{"unknown":true}'):
                path.write_text(raw)
                with self.assertRaises(ValueError):
                    load_quota_policy(path)


if __name__ == "__main__":
    unittest.main()
