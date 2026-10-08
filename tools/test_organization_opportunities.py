"""Positive and known-wrong controls for private organization evidence exports."""
from copy import deepcopy
from dataclasses import replace
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from knowledge_radar.opportunities import build_draft, export_jsonl, observation_digest, REQUEST_TYPE
from knowledge_radar.records import Observation
from loop_engine.core.library_ingestion.record_rules import LibraryRecordError
from export_organization_opportunities import main


class OrganizationOpportunities(unittest.TestCase):
    def setUp(self):
        self.observation = Observation("sample_program", "sample_program", "Sample organization programme",
            "https://sample.example/program", "curated_seed", "1.0.0", "Programs",
            "https://sample.example/program", "2026-10-07", facts={"programme": "Developer tools", "audience": "Founders"},
            last_verified_at="2026-10-07", review_after="2026-10-14")
        self.request = {"record_type": REQUEST_TYPE, "organization_id": "sample", "name": "Sample organization",
            "website": "https://sample.example/", "kind": "partner", "fit_hypothesis": "A tested integration may suit this programme.",
            "proposed_proof": "Reopen an example with a customer-controlled credential.",
            "unknowns": ["Interest is not established."],
            "evidence": [{"observation_key": self.observation.key, "observation_digest": observation_digest(self.observation),
                          "fact_keys": ["programme", "audience"]}], "contact_observation_key": self.observation.key}

    def build(self, request=None, observation=None, **kwargs):
        return build_draft(request or self.request, [observation or self.observation],
                           as_of=kwargs.pop("as_of", "2026-10-08"), suppressed_domains=kwargs.pop("suppressed_domains", [])).to_dict()

    def rebind(self, observation):
        request = deepcopy(self.request)
        request["evidence"][0]["observation_digest"] = observation_digest(observation)
        return request

    def test_exact_observed_facts_are_private_and_interest_is_unknown(self):
        value = self.build()
        self.assertEqual(value["evidence"][0]["facts"], self.observation.facts)
        self.assertEqual(value["freshness"], "current")
        self.assertEqual(value["review_state"], "needs_review")
        self.assertEqual(value["customer_interest"], "not_established")
        self.assertEqual(value["delivery_scope"], "private_draft")
        self.assertEqual(value["coverage"], "selected_observations_only")
        self.assertIs(value["outreach_authorized"], False)

    def test_fabricated_or_changed_evidence_mapping_is_refused(self):
        for field, value in [("observation_key", "invented"), ("observation_digest", "a" * 64), ("fact_keys", ["unobserved"] )]:
            request = deepcopy(self.request);request["evidence"][0][field] = value
            with self.subTest(field=field), self.assertRaises(LibraryRecordError):self.build(request)
        changed = replace(self.observation, facts={"programme": "Different", "audience": "Founders"})
        with self.assertRaisesRegex(LibraryRecordError, "evidence_binding_invalid"):self.build(observation=changed)

    def test_stale_evidence_cannot_claim_current_by_request_field(self):
        self.assertEqual(self.build(as_of="2026-10-14")["freshness"], "stale")
        request = {**self.request, "freshness": "current"}
        with self.assertRaises(LibraryRecordError):self.build(request, as_of="2026-10-14")

    def test_observation_time_does_not_replace_verification(self):
        observation = replace(self.observation, last_verified_at=None)
        self.assertEqual(self.build(self.rebind(observation), observation)["freshness"], "unverified")
        observation = replace(self.observation, review_after=None)
        self.assertEqual(self.build(self.rebind(observation), observation)["freshness"], "unverified")

    def test_future_observation_is_refused_and_future_effect_is_labelled(self):
        with self.assertRaisesRegex(LibraryRecordError, "future_observation"):self.build(as_of="2026-10-06")
        observation = replace(self.observation, effective_from="2026-10-10")
        self.assertEqual(self.build(self.rebind(observation), observation)["freshness"], "not_yet_effective")
        observation = replace(self.observation, observed_at="2026-10-07T99:99:99Z")
        with self.assertRaisesRegex(LibraryRecordError, "invalid_evidence_time"):self.build(self.rebind(observation), observation)

    def test_contact_is_an_observed_organization_page_not_a_guessed_route(self):
        for address in ("mailto:person@example.com", "javascript:alert(1)", "http://sample.example/program",
                        "https://sample.example/program?email=person", "https://sample.example@other.example/program",
                        "https://127.0.0.1/program", "https://sample.local/program", "https://other.example/program",
                        "https://localhost", "https://singlelabel", "https://sub.localhost/program"):
            observation = replace(self.observation, url=address)
            with self.subTest(address=address), self.assertRaises(LibraryRecordError):self.build(self.rebind(observation), observation)
        request = {**self.request, "contact_observation_key": "unseen"}
        with self.assertRaisesRegex(LibraryRecordError, "contact_binding_invalid"):self.build(request)
        self.assertIsNone(self.build({**self.request, "contact_observation_key": None})["contact_route"])

    def test_host_suppression_wins_and_cannot_be_overridden_by_source(self):
        observation = replace(self.observation, facts={**self.observation.facts, "outreach_authorized": True, "suppression": "allow"})
        request = self.rebind(observation)
        request["evidence"][0]["fact_keys"] += ["outreach_authorized", "suppression"]
        value = self.build(request, observation, suppressed_domains=["sample.example"])
        self.assertEqual(value["suppression"], "blocked")
        self.assertEqual(value["review_state"], "suppressed")
        self.assertIsNone(value["contact_route"])
        self.assertIs(value["outreach_authorized"], False)
        with self.assertRaises(LibraryRecordError):self.build({**self.request, "suppression": "allow"})

    def test_suppression_covers_subdomains(self):
        observation = replace(self.observation, url="https://programs.sample.example/program")
        request = {**self.rebind(observation), "website": "https://programs.sample.example/"}
        self.assertEqual(self.build(request, observation, suppressed_domains=["sample.example"])["suppression"], "blocked")
        self.assertEqual(self.build(request, observation, suppressed_domains=["other.example"])["suppression"], "not_listed")

    def test_personal_contact_fields_and_email_prose_are_refused(self):
        for name, value in [("employee_email", "unused"), ("programme", "Contact person@example.com")]:
            observation = replace(self.observation, facts={name: value})
            request = self.rebind(observation);request["evidence"][0]["fact_keys"] = [name]
            with self.assertRaisesRegex(LibraryRecordError, "personal_contact_refused"):self.build(request, observation)

    def test_shared_observation_reader_refuses_nested_personal_or_credential_values(self):
        for nested in ({"email": "person@example.com", "api_key": "not-a-real-key"}, ["person@example.com"]):
            observation = replace(self.observation, facts={"profile": nested})
            request = self.rebind(observation);request["evidence"][0]["fact_keys"] = ["profile"]
            with self.assertRaisesRegex(LibraryRecordError, "radar_observation_invalid"):self.build(request, observation)

    def test_string_credential_markers_are_refused_in_values_and_operator_text(self):
        for value in ("api_key=" + "not-a-real-key", "Bearer " + "not-a-real-key", "ｔｏｋｅｎ:" + "not-a-real-key"):
            observation = replace(self.observation, facts={"programme": value})
            request = self.rebind(observation);request["evidence"][0]["fact_keys"] = ["programme"]
            with self.assertRaisesRegex(LibraryRecordError, "credential_text_refused"):self.build(request, observation)
            with self.assertRaisesRegex(LibraryRecordError, "credential_text_refused"):self.build({**self.request, "fit_hypothesis": value})

    def test_versions_approval_fields_and_missing_unknowns_are_refused(self):
        for request in ({**self.request, "record_type": "organization_opportunity_request/v2"},
                        {**self.request, "outreach_authorized": True}, {**self.request, "unknowns": []}):
            with self.assertRaises(LibraryRecordError):self.build(request)
        with self.assertRaisesRegex(LibraryRecordError, "suppression_required"):self.build(suppressed_domains=None)

    def test_export_rejects_duplicate_organization_and_validates_whole_population(self):
        body = export_jsonl([self.request], [self.observation], as_of="2026-10-08", suppressed_domains=[])
        self.assertEqual(len(body.splitlines()), 1)
        for requests in ([self.request, self.request], [self.request, {**self.request, "unexpected": True}]):
            with self.assertRaises(LibraryRecordError):export_jsonl(requests, [self.observation], as_of="2026-10-08", suppressed_domains=[])

    def test_observation_duplicates_and_nonfinite_values_are_refused(self):
        with self.assertRaisesRegex(LibraryRecordError, "duplicate_observation"):
            build_draft(self.request, [self.observation, self.observation], as_of="2026-10-08", suppressed_domains=[])
        with self.assertRaisesRegex(LibraryRecordError, "non_json_value"):
            observation_digest(replace(self.observation, facts={"score": float("nan")}))

    def test_cli_requires_write_grant_protects_mode_and_never_overwrites(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            for name, value in [("requests", self.request), ("observations", self.observation.to_dict())]:
                (root/name).write_text(json.dumps(value)+"\n")
            (root/"suppression").write_text("[]")
            args = ["--requests", str(root/"requests"), "--observations", str(root/"observations"),
                    "--suppressed-domains", str(root/"suppression"), "--as-of", "2026-10-08"]
            self.assertEqual(main(args), 0)
            self.assertEqual(main(args+["--output", str(Path(__file__).resolve().parents[1]/"never-written-private-briefs.jsonl"),
                                       "--authorize-local-writes"]), 1)
            with self.assertRaises(SystemExit):main(args+["--output", str(root/"briefs")])
            write = args+["--output", str(root/"briefs"), "--authorize-local-writes"]
            self.assertEqual(main(write), 0)
            self.assertEqual(os.stat(root/"briefs").st_mode & 0o777, 0o600)
            before = (root/"briefs").read_bytes()
            self.assertEqual(main(write), 1)
            self.assertEqual((root/"briefs").read_bytes(), before)


if __name__ == "__main__":unittest.main()
