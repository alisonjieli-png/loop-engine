"""Reissuing a service key never shows it and never widens what it can do."""
from __future__ import annotations

import json
import unittest
import unittest.mock

import reissue_service_keys as reissue

KEY = "le_a_new_service_key_value_0123456789"
ADMIN = "le_the_administrator_credential_9876543210"


class Item:
    def __init__(self, value, attributes=None):
        self.value, self.writes = value, 0
        self.attributes = dict(attributes or {"application": "loop-engine", "service": "service.example",
                                              "account": "pilot-owner", "purpose": "service-access"})

    def get_secret(self):
        return self.value.encode()

    def set_secret(self, value):
        self.writes += 1
        self.value = value.decode() if isinstance(value, bytes) else value

    def get_attributes(self):
        return dict(self.attributes)

    def set_attributes(self, attributes):
        self.attributes = dict(attributes)


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
                               "key": {"key_id": key_id, "expires_at": 1790079305, "created_at": 1789474505,
                                       "state": "active"}}}


NOW = 1_791_000_000
DAY = 86400


class Service:
    """The session and administration answers of the live service, over keys it holds by value.

    Every request is kept with the credential it carried, so a test can say which credential did what."""

    def __init__(self):
        self.keys, self.requests, self.issued = {}, [], 0
        self.administrator_refused = False
        #: A new key that the service records but then refuses, as a broken deployment might.
        self.refuse_new_keys = False

    def add(self, value, tenant, key_id, expires_at, label=reissue.LABEL, state="active", scopes=reissue.SCOPES):
        self.keys[value] = {"tenant_id": tenant, "key_id": key_id, "label": label, "scopes": list(scopes),
                            "created_at": expires_at - 7 * DAY, "expires_at": expires_at, "state": state}

    def row(self, key_id):
        return next(row for row in self.keys.values() if row["key_id"] == key_id)

    def call(self, origin, path, token, body=None, timeout=30):
        self.requests.append({"path": path, "token": token, "body": body})
        if path == reissue.SESSION_PATH:
            row = self.keys.get(token)
            if row is None or row["state"] != "active" or row["expires_at"] <= NOW or row.get("refused"):
                return 401, {"record_type": "service_http_error/v1", "error": {"code": "unauthorized"}}
            return 200, {"record_type": "service_http_result/v1", "result": {
                "record_type": reissue.SESSION_RECORD, "token_expires_at": None,
                "principal": {"tenant_id": row["tenant_id"], "key_id": row["key_id"], "scopes": row["scopes"]}}}
        if token != ADMIN or self.administrator_refused:
            return 401, {"record_type": "service_http_error/v1", "error": {"code": "unauthorized"}}
        if body is None:
            # The view names a key's state as the service does: revoked, else expired once past its expiry.
            rows = [{**row, "state": row["state"] if row["state"] == "revoked" else
                     "expired" if row["expires_at"] <= NOW else "active"} for row in self.keys.values()]
            return 200, {"record_type": "service_http_result/v1", "result": {
                "record_type": "service_access_options/v1", "tokens": rows}}
        if body["operation"] == "issue":
            self.issued += 1
            value, key_id = "le_issued_value_{:04d}_000000000000000000".format(self.issued), "{:032x}".format(self.issued)
            self.add(value, body["tenant_id"], key_id, NOW + body["lifetime_seconds"], label=body["label"],
                     scopes=body["scopes"])
            if self.refuse_new_keys:
                self.keys[value]["refused"] = True
            return 200, {"record_type": "service_http_result/v1", "result": {
                "token": value, "committed": True, "key": dict(self.keys[value])}}
        row = next((row for row in self.keys.values() if row["key_id"] == body["key_id"]
                    and row["tenant_id"] == body["tenant_id"]), None)
        if row is None:
            return 404, {"record_type": "service_http_error/v1", "error": {"code": "managed_access_token_not_found"}}
        row["state"] = "revoked"
        return 200, {"record_type": "service_http_result/v1", "result": {"committed": True, "key": dict(row)}}

    def posts(self, operation):
        return [request["body"] for request in self.requests if request["body"] and request["body"]["operation"] == operation]


def renew(service, store, **options):
    settings = {"write": True, "revoke_replaced": True, "now": NOW, **options}
    with unittest.mock.patch.object(reissue, "call", service.call):
        return reissue.renew("https://service.example", "service.example", "pilot-owner", 7 * DAY, 4 * DAY,
                             store, **settings)


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

    def test_a_reissued_key_saves_its_facts_beside_it(self):
        store = saved_with()
        with unittest.mock.patch.object(reissue, "call", lambda *a, **k: answer()):
            reissue.reissue("https://service.example", "service.example", "pilot-owner",
                            "pilot-owner", "hosted verification", 3600, store)
        attributes = store.items["pilot-owner"][0].attributes
        self.assertEqual((attributes["key_id"], attributes["expires_at"], attributes["issued_at"]),
                         ("abc123", "1790079305", "1789474505"))
        self.assertEqual(attributes["account"], "pilot-owner", "the attributes the keyring searches by are kept")
        self.assertNotIn(KEY, json.dumps(attributes))


class RenewalTests(unittest.TestCase):
    """Renewal checks before it acts, keeps one active key per account and never leaves the saved key unusable."""

    def setUp(self):
        self.service = Service()
        self.store = saved_with("le_saved_value_000000000000000000000000")

    def saved(self):
        return self.store.items["pilot-owner"][0]

    def test_a_key_far_from_its_expiry_is_kept_and_described(self):
        self.service.add("le_saved_value_000000000000000000000000", "pilot-owner", "c" * 32, NOW + 6 * DAY)
        result = renew(self.service, self.store)
        self.assertEqual(result["action"], "kept")
        self.assertEqual(self.service.posts("issue"), [])
        self.assertEqual(self.saved().writes, 0, "the value is not touched")
        self.assertEqual(self.saved().attributes["key_id"], "c" * 32, "a key saved without facts gets them")
        self.assertEqual(self.saved().attributes["expires_at"], str(NOW + 6 * DAY))

    def test_a_key_inside_the_window_is_replaced_verified_and_then_revoked(self):
        self.service.add("le_saved_value_000000000000000000000000", "pilot-owner", "c" * 32, NOW + 2 * DAY)
        result = renew(self.service, self.store)
        self.assertEqual(result["action"], "renewed")
        new = self.saved().value
        self.assertNotEqual(new, "le_saved_value_000000000000000000000000")
        self.assertEqual(self.saved().attributes["key_id"], result["key_id"])
        self.assertEqual(self.saved().attributes["expires_at"], str(NOW + 7 * DAY))
        self.assertEqual(self.service.row("c" * 32)["state"], "revoked", "the replaced key is revoked")
        self.assertEqual(result["revoked"], ["c" * 32])
        order = [(request["path"], (request["body"] or {}).get("operation"), request["token"]) for request in self.service.requests]
        verified = order.index((reissue.SESSION_PATH, None, new))
        revoked = order.index((reissue.ADMIN_PATH, "revoke", ADMIN))
        self.assertLess(verified, revoked, "the new key is accepted by the service before the old one is revoked")
        self.assertNotIn(new, json.dumps(result))
        self.assertIs(result["secret_printed"], False)

    def test_a_refused_key_is_replaced_and_its_scopes_are_never_widened(self):
        self.store = saved_with("le_expired_value_00000000000000000000000")
        self.saved().attributes["key_id"] = "d" * 32
        self.service.add("le_expired_value_00000000000000000000000", "pilot-owner", "d" * 32, NOW - DAY,
                         scopes=("provisioning:metadata",))
        result = renew(self.service, self.store)
        self.assertEqual(result["action"], "renewed")
        self.assertFalse(result["saved_key_accepted"])
        self.assertEqual(self.service.posts("issue")[0]["scopes"], ["provisioning:metadata"],
                         "the new key holds the scopes of the key it replaces, not more")
        self.assertEqual(self.service.posts("revoke"), [], "an expired key needs no revocation")

    def test_other_active_keys_of_this_tool_are_revoked_and_other_labels_are_left_alone(self):
        self.service.add("le_saved_value_000000000000000000000000", "pilot-owner", "c" * 32, NOW + 6 * DAY)
        self.service.add("le_orphan_value_0000000000000000000000000", "pilot-owner", "e" * 32, NOW + 5 * DAY)
        self.service.add("le_acceptance_value_000000000000000000000", "pilot-owner", "f" * 32, NOW + DAY,
                         label="Live acceptance 1234")
        result = renew(self.service, self.store)
        self.assertEqual((result["action"], result["revoked"]), ("kept", ["e" * 32]))
        self.assertEqual(self.service.row("f" * 32)["state"], "active", "a key another check issued is not ours")

    def test_known_wrong_without_revoke_replaced_the_replaced_key_stays_active(self):
        # The control for the revocation above: the same renewal without the flag leaves two active keys.
        self.service.add("le_saved_value_000000000000000000000000", "pilot-owner", "c" * 32, NOW + 2 * DAY)
        result = renew(self.service, self.store, revoke_replaced=False)
        self.assertEqual((result["action"], result["revoked"]), ("renewed", []))
        active = [row for row in self.service.keys.values() if row["state"] == "active"]
        self.assertEqual(len(active), 2)

    def test_known_wrong_a_new_key_the_service_refuses_puts_the_earlier_value_back_and_is_revoked(self):
        self.service.add("le_saved_value_000000000000000000000000", "pilot-owner", "c" * 32, NOW + 2 * DAY)
        self.saved().attributes.update(key_id="c" * 32, expires_at=str(NOW + 2 * DAY), issued_at=str(NOW - 5 * DAY))
        before = self.saved().get_attributes()
        self.service.refuse_new_keys = True
        with self.assertRaisesRegex(reissue.ReissueError, "new_key_not_accepted"):
            renew(self.service, self.store)
        self.assertEqual(self.saved().value, "le_saved_value_000000000000000000000000")
        self.assertEqual(self.saved().get_attributes(), before)
        self.assertEqual(self.service.row("c" * 32)["state"], "active", "the key that still works is kept")
        self.assertEqual(self.service.row("{:032x}".format(1))["state"], "revoked", "no unsaved key stays active")

    def test_known_wrong_a_keyring_that_does_not_confirm_the_value_revokes_the_new_key(self):
        class Deaf(Item):
            def set_secret(self, value):
                self.writes += 1
        self.store = Saved({"baltor-admin": [Item(ADMIN)], "pilot-owner": [Deaf("le_saved_value_000000000000000000000000")]})
        self.service.add("le_saved_value_000000000000000000000000", "pilot-owner", "c" * 32, NOW + 2 * DAY)
        with self.assertRaisesRegex(reissue.ReissueError, "storage_not_confirmed"):
            renew(self.service, self.store)
        self.assertEqual(self.service.row("{:032x}".format(1))["state"], "revoked")
        self.assertEqual(self.service.row("c" * 32)["state"], "active")

    def test_a_dry_run_reads_and_reports_without_any_write(self):
        self.service.add("le_saved_value_000000000000000000000000", "pilot-owner", "c" * 32, NOW + 2 * DAY)
        self.service.add("le_orphan_value_0000000000000000000000000", "pilot-owner", "e" * 32, NOW + 5 * DAY)
        result = renew(self.service, self.store, write=False)
        self.assertEqual((result["would_renew"], sorted(result["would_revoke"])), (True, ["c" * 32, "e" * 32]))
        self.assertEqual([request for request in self.service.requests if request["body"]], [], "no POST at all")
        self.assertEqual((self.saved().writes, self.saved().attributes.get("key_id")), (0, None))

    def test_a_refused_administrator_has_its_own_failure_and_exit_status(self):
        self.service.add("le_saved_value_000000000000000000000000", "pilot-owner", "c" * 32, NOW + 2 * DAY)
        self.service.administrator_refused = True
        with self.assertRaisesRegex(reissue.ReissueError, "^administrator_credential_refused$"):
            renew(self.service, self.store)
        import io
        from contextlib import redirect_stdout
        with unittest.mock.patch.object(reissue, "collection", lambda: self.store), \
                unittest.mock.patch.object(reissue, "call", self.service.call), redirect_stdout(io.StringIO()) as shown:
            code = reissue.main(["--origin", "https://service.example", "--account", "pilot-owner",
                                 "--lifetime-seconds", str(7 * DAY), "--renew-within", str(4 * DAY),
                                 "--revoke-replaced", "--confirm-reissue"])
        self.assertEqual(code, reissue.EXIT_ADMINISTRATOR_REFUSED)
        printed = json.loads(shown.getvalue())
        self.assertEqual((printed["renewal_ok"], printed["renewal"][0]["refused"]), (False, "administrator_credential_refused"))

    def test_a_saved_key_of_another_account_is_refused_before_any_write(self):
        self.service.add("le_saved_value_000000000000000000000000", "pilot-boundary", "c" * 32, NOW + 6 * DAY)
        with self.assertRaisesRegex(reissue.ReissueError, "another_account"):
            renew(self.service, self.store)
        self.assertEqual([request for request in self.service.requests if request["body"]], [])

    def test_the_renewal_options_are_bounded(self):
        for arguments in (["--renew-within", str(7 * DAY), "--lifetime-seconds", str(7 * DAY)],
                          ["--renew-within", "-1"], ["--revoke-replaced"],
                          ["--account", "baltor-admin", "--renew-within", "60"]):
            with self.assertRaises(SystemExit):
                reissue.main(["--origin", "https://service.example", "--account", "pilot-owner", *arguments])


if __name__ == "__main__":
    unittest.main()
