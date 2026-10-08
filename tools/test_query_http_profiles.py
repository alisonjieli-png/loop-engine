"""Offline profile, wire-header, request-reuse and provider-budget controls."""
from __future__ import annotations

import copy
import gzip
import json
import os
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for entry in (ROOT / "src", ROOT / "tools", ROOT):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from loop_engine.core.web_fetch import WebHttpClientProfile  # noqa: E402
from query_multiplier.client_profiles import (CONFIGURATION, DEFAULT_PROFILE, ENVIRONMENT, HTTP_ACCESS,  # noqa: E402
    MAXIMUM_CONFIGURATION_BYTES, configure_executors, load_configuration, observation, validate_profile)
from query_multiplier.evidence import EVIDENCE, Ledger, SCHEMA  # noqa: E402
from query_multiplier.executors import registry  # noqa: E402
from query_multiplier.planner import PlannedQuery, query_identity, read_plan  # noqa: E402
from query_multiplier.runner import Run  # noqa: E402
from query_multiplier.transport import RequestRefused, Transport, load_policy  # noqa: E402
from tools.test_query_multiplier import Temporary, plan, product, small_library  # noqa: E402


def profile(language="en-US,en;q=0.9", user_agent="Baltor/1.0 research-client"):
    return WebHttpClientProfile("baltor-research", "1.0.0", user_agent, language)


def configuration(selected=None, executor="ollama_web_search"):
    return {"record_type": CONFIGURATION, "bindings": {executor: (selected or profile()).to_record()}}


class RecordingOpener:
    def __init__(self, status=200):
        self.calls = []
        self.status = status

    def open(self, request, timeout):
        self.calls.append(request)
        response = SimpleNamespace(status=self.status, headers={})
        response.read = lambda size: b'{"results":[{"url":"https://example.org/paper","title":"Paper"}]}'

        class Context:
            def __enter__(self):
                return response

            def __exit__(self, *args):
                return False
        return Context()


class ProfileConfigurationTests(Temporary):
    def write_json(self, name, value):
        path = self.folder / name
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def test_cli_path_wins_over_environment_and_no_setting_preserves_default(self):
        explicit = self.write_json("explicit.json", configuration(profile("fr-FR,fr;q=0.9")))
        inherited = self.write_json("inherited.json", configuration())
        self.assertEqual(load_configuration(explicit, environment={ENVIRONMENT: str(inherited)}),
                         configuration(profile("fr-FR,fr;q=0.9")))
        self.assertEqual(load_configuration(environment={ENVIRONMENT: str(inherited)}), configuration())
        self.assertIsNone(load_configuration(environment={}))
        # An explicitly malformed path never falls back to a valid environment file.
        with self.assertRaises(ValueError):
            load_configuration(" ", environment={ENVIRONMENT: str(inherited)})

    def test_the_shipped_profile_example_has_a_valid_exact_digest(self):
        executors = registry()
        configure_executors(load_configuration(ROOT / "tools/query_multiplier/profiles/baltor-research-en-v1.json"), executors)
        selected = executors["ollama_web_search"].http_client_profile
        self.assertEqual(selected.profile_id, "baltor-research-en")
        self.assertEqual(selected.accept_language, "en-US,en;q=0.9")

    def test_unknown_fields_versions_executors_and_unsupported_access_are_refused_atomically(self):
        cases = [dict(configuration(), record_type="research_query_http_profiles/v9"),
                 dict(configuration(), extra=True), configuration(executor="unknown"),
                 configuration(executor="github_code"), configuration(executor="pypi_search")]
        mixed = configuration()
        mixed["bindings"]["github_repositories"] = profile().to_record()
        cases.append(mixed)
        for value in cases:
            with self.subTest(value=value):
                executors = registry()
                with self.assertRaises(ValueError):
                    configure_executors(value, executors)
                self.assertTrue(all(engine.http_client_profile is None for engine in executors.values()))

    def test_digest_unknown_profile_fields_and_whitespace_are_refused(self):
        for change in ({"digest": "0" * 64}, {"unexpected": "value"},
                       {"record_type": "web_http_client_profile/v9"}):
            value = configuration()
            value["bindings"]["ollama_web_search"].update(change)
            with self.assertRaises(ValueError):
                configure_executors(value, registry())
        for selected in (profile(" "), profile("en-US "), profile(user_agent=" Baltor/1"),
                         profile(user_agent="Baltor/1 ")):
            with self.assertRaises(ValueError):
                configure_executors(configuration(selected), registry())

    def test_control_and_credential_values_cannot_enter_reports_or_headers(self):
        for text in ("Baltor/1\r\nAuthorization: bad", "Baltor/1\x7f", "Baltor/1 api_key=not-a-real-value",
                     "Baltor/1 Bearer not-a-real-value", "Baltor/1 token = not-a-real-value"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                profile(user_agent=text)
        for text in ("Mozilla/5.0", "Googlebot/1 Baltor/1", "CloudflareBrowserRenderingCrawler/1 Baltor/1"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                validate_profile(profile(user_agent=text))
        # A compatibility header still discloses whose client is making the request.
        validate_profile(profile(user_agent="Mozilla/5.0 (compatible; Baltor/1.0)"))

    def test_duplicate_json_fields_and_oversized_files_are_refused(self):
        path = self.folder / "duplicate.json"
        path.write_text('{"record_type":"x","record_type":"y"}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "duplicate_field"):
            load_configuration(path)
        path.write_bytes(b" " * (MAXIMUM_CONFIGURATION_BYTES + 1))
        with self.assertRaisesRegex(ValueError, "too_large"):
            load_configuration(path)
        path.write_text('{"bad":"private-material"', encoding="utf-8")
        with self.assertRaises(ValueError) as caught:
            load_configuration(path)
        self.assertNotIn("private-material", str(caught.exception))

    def test_cli_load_applies_config_before_building_digest_bound_products(self):
        from tools.run_query_multiplier import _load
        selected = profile("fr-FR")
        path = self.write_json("profiles.json", configuration(selected))
        options = SimpleNamespace(plan=str(self.write_json("plan.json", plan(product(
            "web", "ollama_web_search", [("sdg_target", None)])))), data_root=[], http_client_profiles=str(path))
        with patch("tools.run_query_multiplier.load_library", return_value=small_library()), \
                patch.dict(os.environ, {ENVIRONMENT: str(self.folder / "nonexistent.json")}):
            _, executors, products, _ = _load(options)
        self.assertEqual(executors["ollama_web_search"].http_client_profile, selected)
        self.assertEqual(products[0].executor_id, "ollama_web_search")


class WireProfileTests(Temporary):
    def test_every_supported_executor_sends_the_declared_headers(self):
        checked = []
        for name, executor in registry().items():
            if not executor.available or executor.access not in HTTP_ACCESS:
                continue
            selected = profile("de-DE,de;q=0.8")
            configure_executors(configuration(selected, name), {name: executor})
            opener = RecordingOpener()
            method = "POST" if executor.access == "https_post_key" else "GET"
            request = executor.request("/probe", [], page=1, method=method, body={})
            if name == "openalex_works":
                # Exercise its real page-size contract as well as the selected headers.
                request = executor.render({"licence": small_library().dimension("licence").value("spdx:CC0-1.0")}, {})
            answer = Transport(load_policy(), opener=opener, environment={"OLLAMA_API_KEY": "fixture-only"}).send(executor, request)
            sent = dict(opener.calls[0].header_items())
            self.assertEqual(sent["User-agent"], selected.user_agent)
            self.assertEqual(sent["Accept-language"], selected.accept_language)
            self.assertEqual(answer.extra["http_client"], observation(selected))
            self.assertEqual(answer.extra["http_client"]["client_realization"], "http_headers_only")
            checked.append(name)
        self.assertEqual(len(checked), 11)

    def test_the_default_headers_and_request_identity_stay_unchanged(self):
        executor = registry()["ollama_web_search"]
        request = executor.text_request("water quality")
        self.assertNotIn("http_client_profile", request)
        opener = RecordingOpener()
        answer = Transport(load_policy(), opener=opener, environment={"OLLAMA_API_KEY": "fixture-only"}).send(executor, request)
        headers = dict(opener.calls[0].header_items())
        self.assertEqual(headers["User-agent"], DEFAULT_PROFILE.user_agent)
        self.assertNotIn("Accept-language", headers)
        self.assertEqual(answer.extra["http_client"], observation(DEFAULT_PROFILE))

    def test_a_changed_request_profile_is_refused_before_dispatch(self):
        executor = registry()["ollama_web_search"]
        configure_executors(configuration(), {executor.executor_id: executor})
        request = executor.text_request("water quality")
        request["http_client_profile"] = profile("fr-FR").to_record()
        opener = RecordingOpener()
        transport = Transport(load_policy(), opener=opener, environment={"OLLAMA_API_KEY": "fixture-only"})
        with self.assertRaises(RequestRefused):
            transport.send(executor, request)
        self.assertEqual(opener.calls, [])
        # Removed-guard control: the wrong request reaches the transport;
        # the result/store binding still detects the discrepancy.
        with patch("query_multiplier.transport.request_profile_matches", return_value=True):
            answer = transport.send(executor, request)
        self.assertEqual(len(opener.calls), 1)
        ledger = self.ledger()
        query = PlannedQuery("p", executor.executor_id, 0, {}, request, query_identity(executor.executor_id, request))
        ledger.plan(query)
        attempt = ledger.intent(query, "r", 1)
        with self.assertRaisesRegex(ValueError, "observation_mismatch"):
            ledger.store(attempt, query, request, answer)

    def test_an_executor_cannot_override_the_declared_public_headers(self):
        executor = registry()["huggingface_models"]
        request = executor.request("/api/models", [], page=1)
        executor.static_headers = {"uSeR-aGeNt": "other"}
        opener = RecordingOpener()
        with self.assertRaises(RequestRefused):
            Transport(load_policy(), opener=opener).send(executor, request)
        self.assertEqual(opener.calls, [])


class ProfileReuseAndBudgetTests(Temporary):
    def lane(self, ledger, selected, *, status=200):
        executors = registry()
        configure_executors(configuration(selected), executors)
        library = small_library()
        [built] = read_plan(plan(product("web", "ollama_web_search", [("sdg_target", None)])), library, executors)
        opener = RecordingOpener(status)
        run = Run(library=library, products=[built], executors=executors, ledger=ledger, minutes=1,
                  resolve_licences=False, learn=False, minimum_free_bytes=0,
                  transport=Transport(load_policy(), opener=opener, environment={"OLLAMA_API_KEY": "fixture-only"}))
        return run.lanes[0], opener

    def test_profile_changes_isolate_reuse_but_keep_one_provider_budget(self):
        ledger = self.ledger()
        first, first_wire = self.lane(ledger, profile())
        first_query = first.streams[0].next()
        first.attempt(first_query, first.streams[0])
        self.assertEqual(ledger.query_state(first_query.query_id)[0], "executed")
        second, second_wire = self.lane(ledger, profile("fr-FR"))
        second_query = second.streams[0].next()
        self.assertEqual(first_query.request["body"], second_query.request["body"])
        self.assertNotEqual(first_query.query_id, second_query.query_id)
        self.assertIsNone(ledger.within_refresh(second_query.query_id))
        second.attempt(second_query, second.streams[0])
        self.assertEqual(ledger.usage("ollama_web_search"), (2, 2))
        self.assertEqual(len(first_wire.calls) + len(second_wire.calls), 2)
        # Known wrong: omitting the profile collapses these distinct requests.
        stripped_first = {k: v for k, v in first_query.request.items() if k != "http_client_profile"}
        stripped_second = {k: v for k, v in second_query.request.items() if k != "http_client_profile"}
        self.assertEqual(query_identity(first_query.executor_id, stripped_first),
                         query_identity(second_query.executor_id, stripped_second))
        evidence_path = ledger.root / ledger.scalar("select evidence_path from attempts order by rowid desc limit 1")
        evidence = ledger.read_evidence(evidence_path)
        self.assertEqual(evidence["record_type"], EVIDENCE)
        self.assertEqual(evidence["http_client"], observation(profile("fr-FR")))
        self.assertNotIn("fixture-only", json.dumps(evidence, default=str))

    def test_user_agent_change_also_has_a_distinct_request_identity(self):
        executor = registry()["ollama_web_search"]
        configure_executors(configuration(), {executor.executor_id: executor})
        first = executor.text_request("water quality")
        configure_executors(configuration(profile(user_agent="Baltor/2.0 research-client")), {executor.executor_id: executor})
        second = executor.text_request("water quality")
        self.assertNotEqual(query_identity(executor.executor_id, first), query_identity(executor.executor_id, second))

    def test_profile_change_cannot_clear_a_daily_ceiling_or_provider_hold(self):
        ledger = self.ledger()
        first, _ = self.lane(ledger, profile())
        query = first.streams[0].next()
        first.attempt(query, first.streams[0])
        second, wire = self.lane(ledger, profile("fr-FR"))
        second.executor.daily_ceiling = 1
        self.assertEqual(second.wait_reason(), "daily_ceiling_reached")
        # Wrong namespace control: a per-profile quota would wrongly show zero.
        self.assertEqual(ledger.usage("ollama_web_search:" + profile("fr-FR").to_record()["digest"]), (0, 0))
        second.executor.daily_ceiling = 300
        ledger.set_hold("ollama_web_search", "rate_limited_429", datetime.now(timezone.utc) + timedelta(hours=1))
        self.assertEqual(second.wait_reason(), "held:rate_limited_429")
        self.assertEqual(wire.calls, [])

    def test_refresh_never_dispatches_a_previous_profiles_saved_request(self):
        ledger = self.ledger()
        first, _ = self.lane(ledger, profile())
        query = first.streams[0].next()
        first.attempt(query, first.streams[0])
        ledger.db.execute("update queries set next_due_at='2020-01-01T00:00:00Z'")
        ledger.db.commit()
        second, wire = self.lane(ledger, profile("fr-FR"))
        self.assertIsNone(second.due_refresh())
        self.assertEqual(second.stats["refreshes_other_profile_skipped"], 1)
        same, _ = self.lane(ledger, profile())
        refreshed, _ = same.due_refresh()
        self.assertEqual(refreshed.query_id, query.query_id)
        self.assertEqual(wire.calls, [])

    def test_missing_or_tampered_observation_is_not_accepted_as_evidence(self):
        ledger = self.ledger()
        lane, _ = self.lane(ledger, profile())
        query = lane.streams[0].next()
        lane.attempt(query, lane.streams[0])
        path = ledger.root / ledger.scalar("select evidence_path from attempts limit 1")
        envelope = json.loads(gzip.decompress(path.read_bytes()))
        original = copy.deepcopy(envelope)
        for wrong in (None, observation(profile("fr-FR")), dict(observation(profile()), client_realization="full_browser")):
            envelope["http_client"] = wrong
            path.write_bytes(gzip.compress(json.dumps(envelope).encode()))
            with self.assertRaises(ValueError):
                ledger.read_evidence(path)
        original["record_type"] = "research_query_evidence/v1"
        path.write_bytes(gzip.compress(json.dumps(original).encode()))
        with self.assertRaisesRegex(ValueError, "evidence_version"):
            ledger.read_evidence(path)


class EvidenceUpgradeTests(Temporary):
    def old_ledger(self, state="folded"):
        """A v1 schema and completed cache, without using the new writer."""
        folder = self.folder / "v1"
        (folder / "state").mkdir(parents=True)
        old_schema = SCHEMA.replace(",\n  cache_evidence_contract text, cache_evidence_executions integer", "").replace(
            ", evidence_contract text", "")
        db = sqlite3.connect(folder / "state/ledger.sqlite")
        db.executescript(old_schema)
        executor = registry()["ollama_web_search"]
        request = executor.text_request("water quality")
        query_id = query_identity(executor.executor_id, request)
        db.execute("insert into queries(query_id, executor_id, product_id, k, page, origin, request, state, "
                   "executions, next_due_at, last_attempt_id) values(?,?,?,?,?,?,?,?,?,?,?)",
                   (query_id, executor.executor_id, "web", 0, 1, "product", json.dumps(request), "executed",
                    1, "2099-01-01T00:00:00Z", "old-attempt"))
        db.execute("insert into attempts(attempt_id, query_id, executor_id, state, cost) values(?,?,?,?,?)",
                   ("old-attempt", query_id, executor.executor_id, state, 1))
        db.execute("insert into daily_usage values(?,?,?,?)", (executor.executor_id,
                   datetime.now(timezone.utc).strftime("%Y-%m-%d"), 299, 299))
        db.commit()
        db.close()
        ledger = Ledger(folder)
        self.addCleanup(ledger.close)
        return ledger, executor, PlannedQuery("web", executor.executor_id, 0, {}, request, query_id)

    def test_completed_v1_cache_is_a_miss_and_new_v2_success_keeps_daily_usage(self):
        ledger, executor, query = self.old_ledger()
        self.assertEqual(ledger.query_state(query.query_id)[0], "executed")
        self.assertIsNone(ledger.within_refresh(query.query_id))
        self.assertEqual(ledger.usage(executor.executor_id), (299, 299))
        # Removed eligibility guard would silently reuse the old cache.
        with patch.object(ledger, "cache_eligible", return_value=True):
            self.assertIs(ledger.within_refresh(query.query_id), True)
        opener = RecordingOpener()
        run = Run(library=small_library(), products=[], executors={executor.executor_id: executor},
                  transport=Transport(load_policy(), opener=opener, environment={"OLLAMA_API_KEY": "fixture-only"}),
                  ledger=ledger, minutes=1, resolve_licences=False)
        self.assertEqual(run.reconcile()["abandoned_intents"], 0)
        ledger.plan(query)
        attempt = ledger.intent(query, "new-run", executor.cost(query.request))
        answer = run.transport.send(executor, query.request)
        ledger.store(attempt, query, query.request, answer)
        ledger.mark_executed(attempt, query, parse_status="ok", total_count=1, refresh_days=30)
        ledger.close_attempt(attempt)
        self.assertEqual(ledger.usage(executor.executor_id), (300, 300))
        self.assertIs(ledger.within_refresh(query.query_id), True)
        self.assertEqual(ledger.scalar("select state from attempts where attempt_id='old-attempt'"), "folded")
        self.assertEqual(ledger.scalar("select executions from queries where query_id=?", (query.query_id,)), 2)
        path = ledger.evidence_path(executor.executor_id, attempt)
        self.assertEqual(ledger.read_evidence(path)["record_type"], EVIDENCE)

    def test_unfinished_prior_writer_is_refused_before_reconciliation_or_dispatch(self):
        for state in ("intent", "stored"):
            with self.subTest(state=state):
                # One fixture ledger, preserving the unknown prior attempt.
                if state == "intent":
                    ledger, executor, query = self.old_ledger(state)
                else:
                    ledger.db.execute("update attempts set state='stored'")
                    ledger.db.commit()
                opener = RecordingOpener()
                run = Run(library=small_library(), products=[], executors={executor.executor_id: executor},
                          transport=Transport(load_policy(), opener=opener), ledger=ledger, minutes=1,
                          resolve_licences=False)
                with self.assertRaisesRegex(ValueError, "pinned_runner_reconciliation"):
                    run.execute()
                self.assertEqual(opener.calls, [])
                self.assertEqual(ledger.scalar("select state from attempts limit 1"), state)
                self.assertEqual(ledger.usage(executor.executor_id), (299, 299))

    def test_an_old_writer_cannot_keep_a_current_cache_label_after_its_later_success(self):
        ledger, _, query = self.old_ledger()
        ledger.db.execute("update queries set cache_evidence_contract=?, cache_evidence_executions=executions", (EVIDENCE,))
        ledger.db.commit()
        self.assertTrue(ledger.cache_eligible(query.query_id))
        # A v1 runner updates only its own columns. Its result remains history.
        ledger.db.execute("update queries set executions=executions+1")
        ledger.db.commit()
        self.assertIsNone(ledger.within_refresh(query.query_id))

    def test_prior_stored_evidence_cannot_be_promoted_as_a_current_execution(self):
        ledger, _, query = self.old_ledger("stored")
        with self.assertRaisesRegex(ValueError, "prior_evidence_contract"):
            ledger.mark_executed("old-attempt", query, parse_status="ok", total_count=1, refresh_days=30)
        self.assertIsNone(ledger.within_refresh(query.query_id))


if __name__ == "__main__":
    import unittest
    unittest.main()
