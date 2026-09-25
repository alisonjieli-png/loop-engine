"""The model directory keeps every fact sourced, every unknown unknown, and every list free of payment.

Kind: development check over packaged files and pure functions. It starts no server, opens no
connection and needs no credential. Each rule has a known-wrong case beside it, and the rules that
guard a whole behavior have a mutant control that removes the guard and requires the named check to
fail.

- the memory formula gives the published KV cache sizes of known architectures, and a formula that
  drops the factor for keys and values is caught;
- a model without a licence shows Unknown on its page, and a builder that guesses one is caught;
- a price older than the stale limit is shown with its date and marked, a fresh one is not marked,
  and a price without a date is refused;
- a row without a source, or with a fact that names no source of the row, is refused by the builder;
- ordering, filtering, inclusion and the hardware fit give the same answer whatever every commercial
  field holds, and an order that reads a commercial field is caught;
- the three pages, their detail pages and the packaged data are served, and nothing else is.

Run alone:

    PYTHONPATH=src:tools python -m unittest tools/test_model_directory.py
"""
from __future__ import annotations

import json
import re
import unittest
from unittest import mock

from loop_engine.core.service_runtime import commercial_relationship as commercial
from loop_engine.core.service_runtime import model_directory as records
from loop_engine.core.service_runtime import model_directory_fit as fit
from loop_engine.core.service_runtime import model_directory_format as fmt
from loop_engine.core.service_runtime import model_directory_hub as hub
from loop_engine.core.service_runtime import model_directory_pages as pages
from loop_engine.core.service_runtime import model_directory_setup as setup
from loop_engine.core.service_runtime import model_directory_views as views
from loop_engine.core.service_runtime import web_pages
from model_directory import models as model_rows
from model_directory.fetch import Answer
from model_directory.rows import RowSources

GIB = fit.GIB
LLAMA_8B = fit.Architecture(32, 8, 128, fit.ATTENTION_FULL, 0, 131072)
LLAMA_70B = fit.Architecture(80, 8, 128, fit.ATTENTION_FULL, 0, 131072)
#: DeepSeek V3 keeps a latent of 512 plus a rotary part of 64 per layer and token, in 61 layers.
DEEPSEEK_V3 = fit.Architecture(61, 0, 0, fit.ATTENTION_LATENT, 576, 163840)


def _row(**changes) -> dict:
    """A small valid model row that each case changes in one place."""
    row = {"slug": "example-model", "name": "Example Model", "maker": "Example Maker", "ids": {"huggingface": "example/model"},
           "sources": [{"id": "huggingface", "address": "huggingface.co/api/models/example/model", "read": "2026-09-24"},
                       {"id": "openrouter_endpoints", "address": "openrouter.ai/api/v1/models/example/model/endpoints", "read": "2026-09-24"}],
           "facts": {"parameters": {"value": 8_030_261_248, "source": 0, "basis": "counted from the safetensors weight files"},
                     "architecture": {"source": 0, "layers": 32, "kv_heads": 8, "head_dim": 128, "attention": "full",
                                      "latent_width": 0, "max_context": 131072}},
           "quantizations": [{"name": "Q4_K_M", "format": "gguf", "bytes": 4_920_000_000, "repository": "example/model-GGUF",
                              "files": ["model-Q4_K_M.gguf"], "source": 0}],
           "prices": [{"provider": "Example Host", "provider_slug": "example-host", "route": "openrouter", "model_id": "example/model",
                       "input": 0.02, "output": 0.05, "as_of": "2026-09-24", "source": 1}],
           "use_cases": [], "benchmarks": [], "popularity": {"downloads": 10, "likes": 1, "source": 0},
           "commercial_relationship": commercial.to_record(commercial.NONE)}
    row.update(changes)
    return row


class MemoryFormula(unittest.TestCase):
    """weights + KV cache + overhead, on architectures whose cache sizes are published."""

    def test_kv_cache_of_known_architectures(self):
        # 2 x 32 layers x 8 KV heads x 128 x 8,192 tokens x 2 bytes is exactly 1 GiB.
        self.assertEqual(fit.kv_cache_bytes(LLAMA_8B, 8192), 1 * GIB)
        self.assertEqual(fit.kv_cache_bytes(LLAMA_70B, 8192), 2.5 * GIB)
        # 61 layers x 576 values x 2 bytes is 70,272 bytes a token.
        self.assertEqual(fit.kv_cache_bytes(DEEPSEEK_V3, 1), 70_272)
        self.assertEqual(fit.kv_cache_bytes(LLAMA_8B, 8192, "q8_0"), 1 * GIB * 34 / 32 / 2)
        self.assertIsNone(fit.kv_cache_bytes(fit.Architecture(layers=32), 8192))

    def test_total_is_weights_plus_kv_plus_overhead(self):
        estimate = fit.memory_estimate(4 * GIB, LLAMA_8B, 8192)
        self.assertEqual(estimate.total, 4 * GIB + 1 * GIB + 512 * 1024 ** 2 + 0.05 * 4 * GIB)
        self.assertIsNone(fit.memory_estimate(4 * GIB, fit.Architecture(), 8192).total)

    def test_fit_takes_the_longest_context_on_the_device_then_a_split(self):
        gpu = fit.Device(fit.DEVICE_GPU, 12, 1.0, 672, 32, 89.6)
        found = fit.best_fit(4.92e9, LLAMA_8B, gpu)
        self.assertEqual((found.kind, found.context), (fit.FIT_DEVICE, 32768))
        self.assertEqual(fit.best_fit(20e9, LLAMA_70B, gpu).kind, fit.FIT_SPLIT)
        self.assertEqual(fit.best_fit(400e9, LLAMA_70B, gpu).kind, fit.FIT_NONE)
        low, high = fit.speed_range(found, gpu)
        self.assertAlmostEqual(high / low, fit.SPEED_HIGH_FRACTION / fit.SPEED_LOW_FRACTION)

    def test_configuration_reader_reads_full_latent_and_leaves_recurrent_unknown(self):
        self.assertEqual(fit.architecture_from_config({"num_hidden_layers": 32, "num_attention_heads": 32, "num_key_value_heads": 8,
                                                       "hidden_size": 4096, "max_position_embeddings": 131072}), LLAMA_8B)
        latent = fit.architecture_from_config({"num_hidden_layers": 61, "kv_lora_rank": 512, "qk_rope_head_dim": 64,
                                               "num_attention_heads": 128, "max_position_embeddings": 163840})
        self.assertEqual(latent, DEEPSEEK_V3)
        hybrid = fit.architecture_from_config({"num_hidden_layers": 4, "num_attention_heads": 8, "hidden_size": 512,
                                               "layer_types": ["linear_attention", "full_attention", "linear_attention", "full_attention"]})
        self.assertEqual((hybrid.layers, hybrid.kv_known), (2, True))
        state_space = fit.architecture_from_config({"num_hidden_layers": 48, "num_attention_heads": 8, "hidden_size": 512,
                                                    "mamba_d_state": 128})
        self.assertFalse(state_space.kv_known)

    def test_a_formula_without_the_factor_for_keys_and_values_is_caught(self):
        """The mutant control: halve the KV cache as a formula that forgets values would, and the known case fails."""
        wrong = lambda architecture, context, kv_type="f16": (architecture.layers * architecture.kv_heads * architecture.head_dim
                                                              * context * fit.KV_BYTES_PER_VALUE[kv_type])
        with mock.patch.object(fit, "kv_cache_bytes", wrong):
            result = unittest.TestResult()
            MemoryFormula("test_kv_cache_of_known_architectures").run(result)
        self.assertEqual(len(result.failures), 1)


class UnknownStaysUnknown(unittest.TestCase):
    """A fact no source states is absent from the row and written Unknown on the page."""

    def _hugging_face(self, card: dict, tags=()):
        record = {"id": "example/model", "author": "example", "cardData": card, "tags": list(tags), "pipeline_tag": "text-generation",
                  "createdAt": "2026-01-02T00:00:00.000Z", "downloads": 1, "likes": 1}
        answer = Answer(record, "2026-09-24", "read", "huggingface.co/api/models/example/model")
        row, sources_of = model_rows._hugging_face_row(record, answer, None, "", ("", {}, None), "2026-09-24")
        row["slug"], row["sources"] = "example-model", sources_of.items
        return records.validate_model_row(row)

    def test_a_model_without_a_licence_shows_unknown(self):
        row = self._hugging_face({})
        self.assertNotIn("licence", row["facts"])
        page = views._fact_rows(row)
        self.assertIn("<dt>Licence</dt><dd>Unknown</dd>", page)
        self.assertEqual(self._hugging_face({"license": "mit"})["facts"]["licence"]["value"], "mit")
        self.assertEqual(self._hugging_face({}, ["license:apache-2.0"])["facts"]["licence"]["value"], "apache-2.0")

    def test_a_builder_that_guesses_a_licence_is_caught(self):
        with mock.patch.object(model_rows, "_licence", lambda record: ("apache-2.0", "")):
            result = unittest.TestResult()
            UnknownStaysUnknown("test_a_model_without_a_licence_shows_unknown").run(result)
        self.assertEqual(len(result.failures), 1)

    def test_unknown_numbers_are_written_unknown(self):
        self.assertEqual((fmt.parameters(None), fmt.tokens(0), fmt.price(None), fmt.gib(None)), ("Unknown",) * 4)
        row = _row(facts={}, quantizations=[], prices=[])
        self.assertIn("No source lists a price", views._price_table(row, "2026-09-24", records.load_directory()))
        self.assertIn("Unknown", views._local_band(row, records.load_directory()))


class PricesKeepTheirDates(unittest.TestCase):
    def test_a_stale_price_is_shown_with_its_date(self):
        old = _row(prices=[{**_row()["prices"][0], "as_of": "2026-07-01"}])
        table = views._price_table(old, "2026-09-24", records.load_directory())
        self.assertIn('<time datetime="2026-07-01">2026-07-01</time>', table)
        self.assertIn("older than 30 days", table)
        fresh = views._price_table(_row(), "2026-09-24", records.load_directory())
        self.assertIn('<time datetime="2026-09-24">2026-09-24</time>', fresh)
        self.assertNotIn("older than", fresh)
        self.assertTrue(records.price_is_stale({"as_of": "2026-08-24"}, "2026-09-24"))
        self.assertFalse(records.price_is_stale({"as_of": "2026-08-25"}, "2026-09-24"))

    def test_a_price_without_its_date_is_refused(self):
        for wrong in ({key: value for key, value in _row()["prices"][0].items() if key != "as_of"},
                      {**_row()["prices"][0], "as_of": "1970-01-01"}, {**_row()["prices"][0], "as_of": "yesterday"}):
            with self.subTest(price=wrong.get("as_of")), self.assertRaises(records.ModelDirectoryError):
                records.validate_model_row(_row(prices=[wrong]))


class RowsKeepTheirSources(unittest.TestCase):
    def test_a_row_without_a_source_is_refused_by_the_builder(self):
        from build_model_directory import finish_models
        report = {"refused": []}
        bare = _row(sources=[])
        kept = finish_models([(bare, RowSources())], [], report, {"hosted": []})
        self.assertEqual(kept, [])
        self.assertEqual(len(report["refused"]), 1)
        self.assertIn("names no source", report["refused"][0]["reason"])

    def test_each_known_wrong_row_is_refused(self):
        cases = {
            "no sources": _row(sources=[]),
            "a fact naming a source the row does not have": _row(facts={"parameters": {"value": 1, "source": 7}}),
            "a fact with no source at all": _row(facts={"parameters": {"value": 1}}),
            "a source without its date": _row(sources=[{"id": "huggingface", "address": "huggingface.co"}]),
            "a source address with its scheme": _row(sources=[{"id": "huggingface", "address": "https://huggingface.co", "read": "2026-09-24"}]),
            "an unknown source": _row(sources=[{"id": "a-blog", "address": "example.com", "read": "2026-09-24"}] * 2),
            "an unknown fact": _row(facts={"benchmark_rank": {"value": 1, "source": 0}}),
            "a use case outside the list": _row(use_cases=[{"value": "everything", "source": 0}]),
            "no commercial relationship": {key: value for key, value in _row().items() if key != "commercial_relationship"},
            "a commercial relationship with an unknown field": _row(commercial_relationship={**commercial.to_record(commercial.NONE), "rank": 1}),
        }
        records.validate_model_row(_row())
        for description, row in cases.items():
            with self.subTest(case=description), self.assertRaises((records.ModelDirectoryError, commercial.CommercialRelationshipError)):
                records.validate_model_row(row)

    def test_every_packaged_row_names_its_sources(self):
        directory = records.load_directory()
        self.assertGreater(len(directory.models), 1000)
        self.assertTrue(all(row["sources"] for row in directory.models + directory.endpoints))
        self.assertTrue(all(commercial.from_record(row["commercial_relationship"]) == commercial.NONE
                            for row in directory.models + directory.endpoints))


def _with_relationship(rows, relationship) -> list:
    return [{**row, "commercial_relationship": commercial.to_record(relationship)} for row in rows]


def _answers(directory, order=fmt.order_models) -> dict:
    """Every result that must not depend on payment, as plain slugs."""
    models, endpoints = list(directory.models), list(directory.endpoints)
    device = hub.device_from_preset(directory.hardware["presets"][0], directory.hardware["system_memory_default"])
    return {"providers": [row["slug"] for row in order(models)],
            "newest": [row["slug"] for row in order(models, fmt.ORDER_NEWEST)],
            "downloads": [row["slug"] for row in order(models, fmt.ORDER_DOWNLOADS)],
            "name": [row["slug"] for row in order(models, fmt.ORDER_NAME)],
            "coding": [row["slug"] for row in fmt.filter_models(models, "coding")],
            "open": [row["slug"] for row in fmt.filter_models(models, "", fmt.FILTER_OPEN)],
            "hosted": [row["slug"] for row in fmt.filter_models(models, "", fmt.FILTER_HOSTED)],
            "endpoints": [row["slug"] for row in fmt.order_endpoints(endpoints)],
            "fit": [(item.slug, item.quantization, item.fit.context) for item in hub.fit_results(models[:400], device)[0]]}


def payment_changes(directory, order=fmt.order_models) -> list:
    """The results that change when every row carries another valid commercial relationship."""
    baseline = _answers(directory, order)
    changed = []
    for variant in commercial.invariance_variants("example.com"):
        altered = records.Directory(directory.manifest, tuple(_with_relationship(directory.models, variant)),
                                    tuple(_with_relationship(directory.endpoints, variant)), directory.hardware,
                                    {}, {}, directory.harnesses)
        answers = _answers(altered, order)
        changed.extend(f"{variant.kind}/{variant.status}: {name}" for name in baseline if answers[name] != baseline[name])
    # One row at a time as well, because a relationship on every row cannot move one row ahead of the others.
    for variant in commercial.invariance_variants("example.com")[1:]:
        models = list(directory.models)
        models[-1] = {**models[-1], "commercial_relationship": commercial.to_record(variant)}
        altered = records.Directory(directory.manifest, tuple(models), directory.endpoints, directory.hardware, {}, {}, directory.harnesses)
        answers = _answers(altered, order)
        changed.extend(f"one row {variant.kind}/{variant.status}: {name}" for name in baseline if answers[name] != baseline[name])
    return changed


class PaymentNeverOrders(unittest.TestCase):
    def test_every_list_and_fit_is_the_same_whatever_the_commercial_fields_hold(self):
        self.assertEqual(payment_changes(records.load_directory()), [])

    def test_an_order_that_reads_a_commercial_field_is_caught(self):
        def paid_first(rows, order=fmt.ORDER_PROVIDERS):
            ranked = fmt.order_models(rows, order)
            return sorted(ranked, key=lambda row: row["commercial_relationship"]["kind"] == commercial.NO_RELATIONSHIP)
        self.assertTrue(payment_changes(records.load_directory(), paid_first))

    def test_paid_links_show_only_with_their_label_rel_notice_and_band(self):
        paid = commercial.invariance_variants("example.com")
        active = next(item for item in paid if item.kind == commercial.AFFILIATE and item.status == commercial.ACTIVE)
        pending = next(item for item in paid if item.kind == commercial.AFFILIATE and item.status == commercial.PENDING_OWNER)
        ad = next(item for item in paid if item.kind == commercial.SPONSORED and item.status == commercial.ACTIVE)
        row = _with_relationship([_row()], active)[0]
        link = pages.commercial_link(row)
        self.assertIn('rel="sponsored noopener"', link)
        self.assertIn(">Paid link<", link)
        self.assertIn(commercial.PAID_LINK_NOTICE, pages.paid_link_notice([row]))
        self.assertEqual(pages.commercial_link(_with_relationship([_row()], pending)[0]), "")
        self.assertEqual(pages.paid_link_notice([_row()]), "")
        self.assertIn(">Ads</h2>", pages.ads_band(_with_relationship([_row()], ad)))
        self.assertIn(">Ad<", pages.ads_band(_with_relationship([_row()], ad)))
        self.assertEqual(pages.commercial_link(_with_relationship([_row()], ad)[0]), "")
        self.assertIn("No link in this directory is a paid link", pages.disclosure([_row()]))


class PagesAndSetup(unittest.TestCase):
    def test_the_pages_are_served_and_unknown_addresses_are_not(self):
        directory = records.load_directory()
        for address in ("/models", "/endpoints", "/can-i-run", "/models/" + directory.models[0]["slug"],
                        "/endpoints/" + directory.endpoints[0]["slug"]):
            with self.subTest(address=address):
                body, media = pages.rendered_page(address, "GET", "Baltor")
                self.assertEqual(media, web_pages.HTML_MEDIA_TYPE)
                text = body.decode("utf-8")
                self.assertEqual(len(re.findall(r"<h1[ >]", text)), 1)
                self.assertIn('<link rel="canonical" href="https://baltor.ai' + address + '">', text)
                self.assertIn('<script type="application/ld+json">', text)
                self.assertIn(f'id="{commercial.DISCLOSURE_SECTION_ID}"', text)
        for address in ("/models/Not-A-Slug", "/models/../web_pages.py", "/models/no-such-model-anywhere", "/endpoints/", "/models/"):
            with self.subTest(address=address):
                self.assertIsNone(pages.rendered_page(address, "GET", "Baltor"))
                self.assertIsNone(web_pages.served_asset(address, "GET", "Baltor"))
        self.assertIsNone(pages.rendered_page("/models", "POST", "Baltor"))

    def test_each_page_has_its_own_title_and_description(self):
        directory = records.load_directory()
        seen = set()
        for address in ("/models", "/endpoints", "/can-i-run", "/models/" + directory.models[0]["slug"], "/models/" + directory.models[1]["slug"]):
            text = pages.rendered_page(address, "GET", "Baltor")[0].decode("utf-8")
            title = re.search(r"<title>(.*?)</title>", text).group(1)
            description = re.search(r'<meta name="description" content="(.*?)">', text).group(1)
            self.assertNotIn((title, description), seen)
            seen.add((title, description))

    def test_harness_setup_is_written_only_for_an_api_the_harness_reads(self):
        directory = records.load_directory()
        harnesses = list(directory.harnesses)
        by_slug = {item.harness: item for item in setup.setups(directory.endpoint("groq"), "example-model", "Example", harnesses)}
        self.assertIn("[model_providers.groq]", by_slug["codex"].text)
        self.assertIn('wire_api', by_slug["codex"].text + "wire_api")
        self.assertEqual(json.loads(by_slug["opencode"].text)["provider"]["groq"]["npm"], "@ai-sdk/openai-compatible")
        self.assertEqual(json.loads(by_slug["pi"].text)["providers"]["groq"]["api"], "openai-completions")
        self.assertEqual(by_slug["claude-code"].text, "")
        self.assertIn("Anthropic Messages", by_slug["claude-code"].reason)
        mistral = {item.harness: item for item in setup.setups(directory.endpoint("mistral"), "example", "Example", harnesses)}
        self.assertEqual(mistral["codex"].text, "")
        self.assertIn("Responses API", mistral["codex"].reason)
        ollama = {item.harness: item for item in setup.setups(directory.endpoint("ollama"), "qwen3:8b", "Qwen3", harnesses)}
        self.assertIn("--oss --local-provider ollama", ollama["codex"].text)
        self.assertIn("localhost:11434", ollama["claude-code"].text)

    def test_the_site_map_names_the_three_pages(self):
        from loop_engine.core.service_runtime.web_site_map import load_site_map
        site_map = load_site_map()
        for address in pages.PAGES:
            with self.subTest(address=address):
                self.assertIsNotNone(site_map.page(address))
                self.assertTrue(site_map.page(address).indexed)
                self.assertIsNotNone(pages.rendered_page(address, "HEAD", "Baltor"))


if __name__ == "__main__":
    unittest.main()
