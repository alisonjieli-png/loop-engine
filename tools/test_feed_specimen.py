"""The inline live notice reads the real feed contract; the research specimen never pretends to be a live result."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

from loop_engine.core.service_runtime import catalogue_feed as feed
from loop_engine.core.service_runtime import feed_source_collections, web_pages
from loop_engine.core.service_runtime.catalogue_release_checks import Fixture
from loop_engine.core.service_runtime.records import ServiceRuntimeError

ROOT = Path(__file__).resolve().parents[1]
ASSET = ROOT / "src/loop_engine/core/service_runtime/web_assets/feed-specimen.js"
ORIGIN = "https://feed.example.invalid"
JAVASCRIPT = r"""
import fs from 'node:fs';
const input=JSON.parse(fs.readFileSync(0,'utf8'));
const code=fs.readFileSync(process.argv[1],'utf8');
const module=await import('data:text/javascript;base64,'+Buffer.from(code).toString('base64'));
const results=[];
for(const candidate of input.candidates){
  try{const record=module.validateFeed(candidate,input.origin);
    results.push({accepted:true,notice_id:record.notice_id,summary:module.summaryText(record),markdown:module.snapshotMarkdown(candidate,input.origin)});
  }catch(error){results.push({accepted:false,code:error.message});}
}
let cancelled=0,read=0;
const stream=new ReadableStream({pull(controller){read++;controller.enqueue(new Uint8Array(module.MAXIMUM_FEED_BYTES));},cancel(){cancelled++;}});
let oversized;
try{await module.boundedText(new Response(stream,{headers:{'Content-Type':'application/feed+json'}}));oversized=false;}
catch(_){oversized=true;}
let declaredCancelled=0,declaredRead=0;
const declared=new ReadableStream({pull(){declaredRead++;},cancel(){declaredCancelled++;}});
let declaredRefused=false;
try{await module.boundedText(new Response(declared,{headers:{'Content-Type':'application/feed+json','Content-Length':String(module.MAXIMUM_FEED_BYTES+1)}}));}
catch(_){declaredRefused=true;}
const positive=await module.boundedText(new Response(JSON.stringify(input.candidates[0]),{headers:{'Content-Type':'application/feed+json'}}));
const refusals=[];
for(const response of [new Response('{}',{status:503,headers:{'Content-Type':'application/feed+json'}}),
                      new Response('{}',{headers:{'Content-Type':'text/html'}}),
                      new Response(new Uint8Array([255]),{headers:{'Content-Type':'application/feed+json'}})]){
  try{await module.boundedText(response);refusals.push(false);}catch(_){refusals.push(true);}
}
console.log(JSON.stringify({results,oversized,cancelled,read,declaredCancelled,declaredRead,declaredRefused,
  positive:JSON.parse(positive)._baltor??JSON.parse(positive).items[0]._baltor,refusals,timeout:module.READ_TIMEOUT_MS}));
"""


class FeedSpecimenTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory(prefix="feed-specimen-")
        self.addCleanup(self.temporary.cleanup)
        self.case = Fixture(Path(self.temporary.name))
        self.case.publish([self.case.line("private-package-identity", "PRIVATE BODY NEVER SHOWN")])
        self.record = feed.snapshot(self.case.runtime, self.case.view())
        self.document = feed.json_feed(self.record, ORIGIN)

    def javascript(self, candidates):
        node = shutil.which("node")
        if node is None:
            self.skipTest("Node is needed for the real browser-module contract tests")
        completed = subprocess.run([node, "--input-type=module", "-e", JAVASCRIPT, str(ASSET)],
                                   input=json.dumps({"origin": ORIGIN, "candidates": candidates}), text=True,
                                   capture_output=True, timeout=15, check=False)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return json.loads(completed.stdout)

    def test_real_snapshot_is_read_from_json_feed_envelope_and_markdown_matches_same_native_record(self):
        result = self.javascript([self.document])
        accepted = result["results"][0]
        self.assertTrue(accepted["accepted"])
        self.assertEqual(accepted["notice_id"], self.record["notice_id"])
        self.assertEqual(accepted["summary"], feed.summary_text(self.record))
        self.assertEqual(accepted["markdown"], feed.markdown(self.record, ORIGIN))
        self.assertEqual(result["positive"], self.record)
        self.assertNotIn("PRIVATE BODY", accepted["markdown"])

    def test_oversized_declared_and_streamed_bodies_cancel_and_http_utf8_failures_refuse(self):
        result = self.javascript([self.document])
        self.assertTrue(result["oversized"])
        self.assertEqual(result["cancelled"], 1)
        self.assertLessEqual(result["read"], 3)
        self.assertTrue(result["declaredRefused"])
        self.assertEqual(result["declaredCancelled"], 1)
        self.assertTrue(all(result["refusals"]))
        self.assertEqual(result["timeout"], 10000)

    def test_unknown_versions_conflicting_identity_invalid_dates_and_fabricated_counts_refuse(self):
        wrong = []
        for name, value in (("record_type", "catalogue_feed_snapshot/v2"), ("packages", True),
                            ("distinct_files", -1), ("catalogue_state_revision", 0),
                            ("notice_id", "different"), ("state_changed_at", "2026-02-31T00:00:00Z"),
                            ("coverage", "all_upstream_news")):
            document = deepcopy(self.document)
            document["items"][0]["_baltor"][name] = value
            wrong.append(document)
        document = deepcopy(self.document)
        document["items"][0]["_baltor"]["upstream_benchmark_score"] = 99
        wrong.append(document)
        document = deepcopy(self.document)
        document["items"][0]["content_text"] = "Invented impressive numbers"
        wrong.append(document)
        document = deepcopy(self.document)
        document["feed_url"] = "https://other.example.invalid/private"
        wrong.append(document)
        document = deepcopy(self.document)
        document["items"] *= 2
        wrong.append(document)
        result = self.javascript([self.document, *wrong])
        self.assertTrue(result["results"][0]["accepted"])
        self.assertTrue(all(not item["accepted"] for item in result["results"][1:]))

    def test_a_valid_zero_population_is_not_conflated_with_a_failed_refresh(self):
        zero = {**self.record, "packages": 0, "distinct_files": 0}
        document = feed.json_feed(zero, ORIGIN)
        result = self.javascript([document])
        self.assertTrue(result["results"][0]["accepted"])
        self.assertIn("0 packages and 0 distinct files", result["results"][0]["summary"])

    def test_static_page_has_no_count_guess_and_includes_versioned_same_origin_script(self):
        body, _media = feed.rendered_page("/feeds", "GET", "Baltor")
        text = body.decode()
        self.assertIn('id="catalogue-specimen-content" hidden', text)
        self.assertIn('id="catalogue-specimen-packages"></dd>', text)
        self.assertIn('type="module" src="/assets/feed-specimen.js?v=', text)
        self.assertIn("same notice displayed here", text)
        self.assertIn("JavaScript is needed for the inline notice", text)
        self.assertIn("/assets/feed-specimen.js", web_pages.CACHEABLE_WEB_ASSETS)
        self.assertLess(ASSET.stat().st_size, 16384)

    def assert_three_offerings(self, source):
        for wording in ("Compare the three offerings", "Agent Feeds", "Harness Files", "Overnight / AFK Work",
                        "Preview", "Your worker and model access", "No extra charge with Harness Files",
                        "$4.99 a month.", "$29 a month", "Free through December 31, 2026 (Eastern)",
                        "No automatic charge; a paid subscription requires your explicit opt-in."):
            self.assertTrue(wording in source, "Missing feed offering text: " + wording)
        self.assertIn('href="/overnight"', source)
        self.assertNotIn("Compare the two offerings", source)
        self.assertNotIn("$49.99", source)
        self.assertNotIn("$29.99", source)

    def test_feeds_page_names_three_available_offerings_without_changing_prices(self):
        body, _media = feed.rendered_page("/feeds", "GET", "Baltor")
        self.assert_three_offerings(body.decode())

    def test_feed_offering_check_detects_old_count_missing_preview_and_unactivated_prices(self):
        source = feed.page_body()
        for wrong in (source.replace("Compare the three offerings", "Compare the two offerings"),
                      source.replace("Overnight / AFK Work", "Other work"),
                      source.replace("Preview", ""), source.replace("$29 a month", "$49.99 a month"),
                      source.replace("No extra charge with Harness Files", "")):
            with self.assertRaises(AssertionError):
                self.assert_three_offerings(wrong)

    def test_research_example_names_assumptions_missing_measurements_provisional_choice_and_trigger(self):
        body = feed.decision_specimen_body()
        for label in ("curated example", "Example assumptions", "Publisher documentation", "What is not measured here",
                      "Provisional choice", "Review trigger", "not collected for this specimen"):
            self.assertIn(label, body)
        for identity in ("founder-stack", "model-cost", "retrieval-benchmarks", "developer-releases"):
            self.assertIn(f'href="#collection-{identity}"', body)
        self.assertNotIn("$", body)
        self.assertNotIn("%", body)
        current = feed_source_collections.directory()
        incomplete = type(current)(current.source_docs_checked_on, current.digest, current.limitations,
                                   current.sources, tuple(item for item in current.collections if item.id != "founder-stack"))
        with mock.patch.object(feed_source_collections, "directory", return_value=incomplete):
            with self.assertRaises(ServiceRuntimeError):
                feed.decision_specimen_body()


if __name__ == "__main__":
    unittest.main()
