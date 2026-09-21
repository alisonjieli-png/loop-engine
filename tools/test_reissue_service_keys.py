"""Reissuing a service key never shows it and never widens what it can do."""
from __future__ import annotations

import json
import unittest
import unittest.mock

import reissue_service_keys as reissue

KEY = "le_a_new_service_key_value_0123456789"
ADMIN = "le_the_administrator_credential_9876543210"


class Item:
    def __init__(self, value):
        self.value, self.writes = value, 0

    def get_secret(self):
        return self.value.encode()

    def set_secret(self, value):
        self.writes += 1
        self.value = value.decode() if isinstance(value, bytes) else value


class Saved:
    def __init__(self, items):
        self.items = items

    def search_items(self, attributes):
        return self.items.get(attributes["account"], [])


def saved_with(old="le_the_expired_value_000000000000000"):
    return Saved({"baltor-admin": [Item(ADMIN)], "pilot-owner": [Item(old)]})


def answer(status=200, token=KEY, key_id="abc123"):
    return status, {"record_type": "service_http_result/v1",
                    "result": {"token": token, "committed": True,
                               "key": {"key_id": key_id, "expires_at": 1790079305, "state": "active"}}}


class ReissueTests(unittest.TestCase):
    def test_the_new_key_is_stored_and_never_returned_or_printed(self):
        store = saved_with()
        calls = []

        def call(origin, path, token, body=None, timeout=30):
            calls.append({"origin": origin, "path": path, "token": token, "body": body})
            return answer()
        with unittest.mock.patch.object(reissue, "call", call):
            result = reissue.reissue("https://service.example", "service.example", "pilot-owner",
                                     "pilot-owner", "hosted verification", 3600, store)
        self.assertEqual(store.items["pilot-owner"][0].value, KEY)
        self.assertEqual(store.items["pilot-owner"][0].writes, 1)
        self.assertNotIn(KEY, json.dumps(result))
        self.assertIs(result["secret_printed"], False)
        self.assertEqual(calls[0]["token"], ADMIN, "the administrator credential authorises the request")
        self.assertEqual(calls[0]["body"]["scopes"], list(reissue.SCOPES))
        self.assertEqual(calls[0]["body"]["operation"], "issue")

    def test_two_reissues_never_reuse_one_request_identity(self):
        store, identities = saved_with(), []
        with unittest.mock.patch.object(reissue, "call",
                                        lambda o, p, t, body=None, timeout=30: (identities.append(body["request_id"]), answer())[1]):
            for _ in range(2):
                reissue.reissue("https://service.example", "service.example", "pilot-owner",
                                "pilot-owner", "hosted verification", 3600, store)
        self.assertEqual(len(set(identities)), 2)

    def test_a_refused_issue_leaves_the_saved_value_untouched(self):
        store = saved_with()
        with unittest.mock.patch.object(reissue, "call", lambda *a, **k: (403, {"error": {"code": "access_administration_forbidden"}})):
            with self.assertRaisesRegex(reissue.ReissueError, "access_administration_forbidden"):
                reissue.reissue("https://service.example", "service.example", "pilot-owner",
                                "pilot-owner", "hosted verification", 3600, store)
        self.assertEqual(store.items["pilot-owner"][0].writes, 0)

    def test_an_answer_without_a_key_is_refused_rather_than_stored(self):
        store = saved_with()
        with unittest.mock.patch.object(reissue, "call", lambda *a, **k: answer(token=None)):
            with self.assertRaisesRegex(reissue.ReissueError, "no_key_in_answer"):
                reissue.reissue("https://service.example", "service.example", "pilot-owner",
                                "pilot-owner", "hosted verification", 3600, store)
        self.assertEqual(store.items["pilot-owner"][0].writes, 0)

    def test_storage_that_does_not_confirm_is_reported_not_assumed(self):
        class Deaf(Item):
            def set_secret(self, value):
                self.writes += 1
        store = Saved({"baltor-admin": [Item(ADMIN)], "pilot-owner": [Deaf("old")]})
        with unittest.mock.patch.object(reissue, "call", lambda *a, **k: answer()):
            with self.assertRaisesRegex(reissue.ReissueError, "storage_not_confirmed"):
                reissue.reissue("https://service.example", "service.example", "pilot-owner",
                                "pilot-owner", "hosted verification", 3600, store)

    def test_an_ambiguous_or_missing_saved_account_is_refused(self):
        for items in ({"baltor-admin": [Item(ADMIN)], "pilot-owner": []},
                      {"baltor-admin": [Item(ADMIN)], "pilot-owner": [Item("a"), Item("b")]},
                      {"pilot-owner": [Item("a")]}):
            with self.assertRaises(reissue.ReissueError):
                with unittest.mock.patch.object(reissue, "call", lambda *a, **k: answer()):
                    reissue.reissue("https://service.example", "service.example", "pilot-owner",
                                    "pilot-owner", "hosted verification", 3600, Saved(items))

    def test_nothing_is_reissued_without_the_confirmation_flag(self):
        import io
        from contextlib import redirect_stdout
        with unittest.mock.patch.object(reissue, "reissue") as worker, redirect_stdout(io.StringIO()) as shown:
            code = reissue.main(["--origin", "https://service.example", "--account", "pilot-owner"])
        self.assertEqual(code, 0)
        worker.assert_not_called()
        self.assertIn('"dry_run": true', shown.getvalue())

    def test_an_address_that_is_not_an_exact_secure_origin_is_refused(self):
        for origin in ("http://service.example", "https://service.example/path",
                       "https://service.example?a=1", "not-an-address"):
            with self.assertRaises(SystemExit):
                reissue.main(["--origin", origin, "--account", "pilot-owner", "--confirm-reissue"])

    def test_a_lifetime_outside_the_supported_range_is_refused(self):
        for lifetime in ("10", "604801"):
            with self.assertRaises(SystemExit):
                reissue.main(["--origin", "https://service.example", "--account", "pilot-owner",
                              "--lifetime-seconds", lifetime, "--confirm-reissue"])

    def test_removing_the_scope_list_would_widen_the_key_and_is_detected(self):
        # Known-wrong control: a key issued with no scope list takes every
        # scope the tenant holds, including any added later.
        store, bodies = saved_with(), []
        with unittest.mock.patch.object(reissue, "SCOPES", ()), \
                unittest.mock.patch.object(reissue, "call",
                                           lambda o, p, t, body=None, timeout=30: (bodies.append(body), answer())[1]):
            reissue.reissue("https://service.example", "service.example", "pilot-owner",
                            "pilot-owner", "hosted verification", 3600, store)
        self.assertEqual(bodies[0]["scopes"], [], "the widened request is what this control detects")


if __name__ == "__main__":
    unittest.main()
