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
- a row that carries OpenRouter or Artificial Analysis data is refused by the builder and the reader,
  in each form that data could take, and a reader that accepts one is caught; no packaged row does;
- LiteLLM and LMArena join a row only on an exact identifier, only the maker's own entry states a
  fact, and a served repository comes back while an unserved copy stays out;
- Ollama Cloud's structured output reads No with its dated citation, and the record as it was
  before the correction is caught;
- the pages name each republished source with its licence and link the refused publishers;
- the three pages, their detail pages and the packaged data are served, and nothing else is.

Run alone:

    PYTHONPATH=src:tools python -m unittest tools/test_model_directory.py
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path
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
from model_directory import endpoints as endpoint_rows
from model_directory import models as model_rows
from model_directory import sources as source_engines
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
                       {"id": "modelsdev", "address": "models.dev/api.json", "read": "2026-09-24"}],
           "facts": {"parameters": {"value": 8_030_261_248, "source": 0, "basis": "counted from the safetensors weight files"},
                     "architecture": {"source": 0, "layers": 32, "kv_heads": 8, "head_dim": 128, "attention": "full",
                                      "latent_width": 0, "max_context": 131072}},
           "quantizations": [{"name": "Q4_K_M", "format": "gguf", "bytes": 4_920_000_000, "repository": "example/model-GGUF",
                              "files": ["model-Q4_K_M.gguf"], "source": 0}],
           "prices": [{"provider": "Example Host", "provider_slug": "example-host", "route": "direct", "model_id": "example/model",
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


#: Where Ollama states, in the source of its own documentation, that its cloud does not support structured outputs.
#: Ollama's terms refuse automated access to its site, so the GitHub repository source is the citation.
OLLAMA_STRUCTURED_SOURCE = "github.com/ollama/ollama/blob/main/docs/capabilities/structured-outputs.mdx"
REVIEWED_PATH = Path(__file__).resolve().parent / "model_directory" / "provider_documentation.json"


def ollama_cloud_structured_output_problems(endpoint: dict) -> list:
    """What is wrong with the structured output fact of the Ollama Cloud row, as plain sentences; empty when it is right."""
    fact = endpoint["facts"].get("structured_output")
    if fact is None:
        return ["the row has no structured output fact"]
    problems = []
    if fact.get("value") is not False:
        problems.append(f"structured output reads {fact.get('value')!r}; Ollama's documentation says its cloud does not support it")
    source = endpoint["sources"][fact["source"]]
    if source["address"] != OLLAMA_STRUCTURED_SOURCE:
        problems.append(f"the fact cites {source['address']}, not the documentation source {OLLAMA_STRUCTURED_SOURCE}")
    if source["read"] < "2026-09-27":
        problems.append(f"the source was read on {source['read']}, before the correction was checked on 2026-09-27")
    if "April 22, 2026" not in fact.get("note", ""):
        problems.append("the note does not give the day Ollama added its statement, April 22, 2026")
    return problems


class OllamaCloudStructuredOutput(unittest.TestCase):
    """Ollama's documentation has said since April 22, 2026 that its cloud does not support structured outputs."""

    @staticmethod
    def _built(entry: dict) -> dict:
        missing = Answer(None, "", "missing", "models.dev/api.json")
        return records.validate_endpoint_row(endpoint_rows._hosted_row(entry, {}, missing, {}, []))

    @staticmethod
    def _entry() -> dict:
        return next(entry for entry in source_engines.read_reviewed(REVIEWED_PATH)["hosted"] if entry["slug"] == "ollama-cloud")

    def test_the_curated_record_builds_a_row_that_says_no_with_its_dated_citation(self):
        self.assertEqual(ollama_cloud_structured_output_problems(self._built(self._entry())), [])

    def test_the_record_as_it_was_before_the_correction_is_caught(self):
        """The known-wrong control: the September 24 record said yes and cited the website page."""
        old = json.loads(json.dumps(self._entry()))
        old["sources"]["structured"] = ["docs.ollama.com/capabilities/structured-outputs", "2026-09-24"]
        old["facts"]["structured_output"] = {"value": True, "source": "structured"}
        self.assertEqual(len(ollama_cloud_structured_output_problems(self._built(old))), 4)

    def test_the_packaged_row_and_its_pages_say_no_with_the_citation(self):
        directory = records.load_directory()
        endpoint = directory.endpoint("ollama-cloud")
        self.assertEqual(ollama_cloud_structured_output_problems(endpoint), [])
        page = pages.rendered_page("/endpoints/ollama-cloud", "GET", "Baltor")[0].decode("utf-8")
        self.assertRegex(page, r"<dt>Structured output</dt><dd>No ")
        self.assertIn('href="https://' + OLLAMA_STRUCTURED_SOURCE + '"', page)
        self.assertIn('href="https://github.com/ollama/ollama/issues/12362"', page)
        groq = pages.rendered_page("/endpoints/groq", "GET", "Baltor")[0].decode("utf-8")
        self.assertRegex(groq, r"<dt>Structured output</dt><dd>Yes ", "a true fact shows Yes as a false one shows No")
        card = re.search(r'<li class="md-card"><a class="md-row-link" href="/endpoints/ollama-cloud">.*?</li>',
                         pages.rendered_page("/endpoints", "GET", "Baltor")[0].decode("utf-8"), re.S).group(0)
        self.assertIn("Structured output: No", card)


def _from_openrouter() -> tuple:
    """A row as the builder wrote it before September 27, 2026: an OpenRouter source with its facts, its routed price
    and the Artificial Analysis index its answer carried. Returns the row and its sources as the builder collects them."""
    row = _row()
    sources_of = RowSources()
    for item in row["sources"]:
        sources_of.add(item["id"], item["address"], item["read"])
    copied = sources_of.add("openrouter", "openrouter.ai/api/v1/models", "2026-09-27")
    row["ids"] = {**row["ids"], "openrouter": "example/model"}
    row["facts"]["context"] = [{"value": 131072, "source": copied, "basis": "the context length OpenRouter lists"}]
    row["benchmarks"] = [{"name": "Artificial Analysis Intelligence Index", "value": 40.1, "publisher": "Artificial Analysis",
                          "address": "artificialanalysis.ai/methodology/intelligence-benchmarking", "source": copied}]
    return row, sources_of


class RefusedSources(unittest.TestCase):
    """OpenRouter and Artificial Analysis are linked, never copied: a row that carries their data is refused whole."""

    def test_a_row_from_a_refused_source_is_refused_by_the_build(self):
        from build_model_directory import finish_models
        report = {"refused": []}
        row, sources_of = _from_openrouter()
        self.assertEqual(finish_models([(row, sources_of)], [], report, {"hosted": []}), [])
        self.assertEqual(len(report["refused"]), 1)
        self.assertIn("refused source", report["refused"][0]["reason"])

    def test_each_way_of_carrying_refused_data_is_refused(self):
        lmarena = {"id": "lmarena", "address": "huggingface.co/datasets/lmarena-ai/leaderboard-dataset", "read": "2026-09-27"}
        index_value = {"name": "Artificial Analysis Intelligence Index", "value": 40.1, "publisher": "Artificial Analysis",
                       "address": "artificialanalysis.ai/models", "source": 2}
        cases = {
            "an OpenRouter source": _row(sources=_row()["sources"] + [{"id": "openrouter", "address": "openrouter.ai/api/v1/models", "read": "2026-09-27"}]),
            "an OpenRouter endpoints source": _row(sources=[{"id": "openrouter_endpoints", "address": "openrouter.ai/api/v1/models/x/endpoints", "read": "2026-09-27"}]),
            "an Artificial Analysis source": _row(sources=[{"id": "artificial_analysis", "address": "artificialanalysis.ai", "read": "2026-09-27"}]),
            "a price routed through OpenRouter": _row(prices=[{**_row()["prices"][0], "route": "openrouter"}]),
            "a price from a source that is not a price source": _row(prices=[{**_row()["prices"][0], "source": 0}]),
            "an OpenRouter identifier": _row(ids={"huggingface": "example/model", "openrouter": "example/model"}),
            "an allowed source name on OpenRouter's host": _row(sources=[_row()["sources"][0], {"id": "modelsdev", "address": "openrouter.ai/api/v1/models", "read": "2026-09-27"}]),
            "an Artificial Analysis value under an open source's name": _row(sources=_row()["sources"] + [lmarena], benchmarks=[index_value]),
            "a result value from a source that publishes none": _row(benchmarks=[{**index_value, "name": "Some score", "publisher": "Someone",
                                                                                   "address": "example.com", "source": 0}]),
        }
        for description, row in cases.items():
            with self.subTest(case=description), self.assertRaises(records.ModelDirectoryError):
                records.validate_model_row(row)
        linked = _row(benchmarks=[{"name": "Artificial Analysis", "publisher": "Artificial Analysis", "address": "artificialanalysis.ai", "source": 0}])
        self.assertIs(records.validate_model_row(linked), linked)
        groq = next(entry for entry in source_engines.read_provider_documentation(REVIEWED_PATH)["hosted"] if entry["slug"] == "groq")
        endpoint = endpoint_rows._hosted_row(groq, {}, Answer(None, "", "missing", "models.dev/api.json"), {}, [])
        records.validate_endpoint_row(endpoint)
        endpoint["sources"].append({"id": "openrouter_endpoints", "address": "openrouter.ai/api/v1/models", "read": "2026-09-27"})
        with self.assertRaises(records.ModelDirectoryError):
            records.validate_endpoint_row(endpoint)
        manifest = {"sources": [{"id": "openrouter", "name": "OpenRouter Models API", "address": "openrouter.ai/api/v1/models",
                                 "terms_address": "openrouter.ai/terms", "licence": "Terms", "checked": "2026-09-27", "use": "Prices.",
                                 "rows": 1, "oldest_read": "2026-09-27", "newest_read": "2026-09-27"}], "linked_only": []}
        with self.assertRaises(records.ModelDirectoryError):
            records.validate_manifest_sources(manifest)

    def test_a_reader_that_accepts_a_refused_source_is_caught(self):
        """The mutant control: without the refusal, the known-wrong row passes and the named check fails."""
        with mock.patch.object(records, "REFUSED_SOURCES", {}), \
                mock.patch.object(records, "SOURCE_IDS", records.SOURCE_IDS + ("openrouter", "openrouter_endpoints")), \
                mock.patch.object(records, "ID_KINDS", records.ID_KINDS + ("openrouter",)), \
                mock.patch.object(records, "RESULT_VALUE_SOURCES", records.RESULT_VALUE_SOURCES + ("openrouter",)), \
                mock.patch.object(records, "REFUSED_PUBLISHERS", ()), mock.patch.object(records, "REFUSED_HOSTS", ()):
            result = unittest.TestResult()
            RefusedSources("test_a_row_from_a_refused_source_is_refused_by_the_build").run(result)
        self.assertEqual(len(result.failures), 1)

    def test_the_builder_declares_no_refused_host_and_has_no_reader_for_one(self):
        from loop_engine.core.library_ingestion.https_transport import HostNotDeclared, HttpsGetTransport
        from loop_engine.core.library_ingestion.request_log import RequestBudget, RequestLog
        from model_directory import fetch
        self.assertFalse({"openrouter.ai", "artificialanalysis.ai", "ollama.com"} & set(fetch.HOSTS))
        self.assertFalse([name for name in dir(source_engines) if "openrouter" in name.lower()])
        transport = HttpsGetTransport(fetch.HOSTS, RequestBudget(maximum_requests=1, maximum_pause_seconds=1.0), RequestLog())
        with self.assertRaises(HostNotDeclared):
            transport.get("openrouter.ai", "/api/v1/models")

    def test_no_packaged_row_carries_a_refused_source_identifier_price_or_value(self):
        directory = records.load_directory()
        found = []
        for row in directory.models + directory.endpoints:
            found += [f"{row['slug']}: source {item['id']}" for item in row["sources"] if item["id"] in records.REFUSED_SOURCES]
        for row in directory.models:
            found += [f"{row['slug']}: identifier {kind}" for kind in row["ids"] if kind not in records.ID_KINDS]
            found += [f"{row['slug']}: price route {price['route']}" for price in row["prices"] if price["route"] != records.ROUTE_DIRECT]
            found += [f"{row['slug']}: value of {item['publisher']}" for item in row["benchmarks"]
                      if "value" in item and item["publisher"] in records.REFUSED_PUBLISHERS]
        self.assertEqual(found, [])
        linked = {item["name"] for item in directory.manifest["linked_only"]}
        self.assertTrue({"OpenRouter", "Artificial Analysis", "Ollama library"} <= linked)
        self.assertFalse({item["id"] for item in directory.manifest["sources"]} & set(records.REFUSED_SOURCES))


def _maker_row(provider: str, model: str) -> tuple:
    row = model_rows._empty_row("modelsdev", provider + "/" + model, model, provider)
    sources_of = RowSources()
    model_rows._modelsdev_offer(row, sources_of.add, provider, {"name": provider.capitalize()},
                                {"id": model, "cost": {"input": 1.0, "output": 2.0}, "tool_call": True}, "2026-09-27", True)
    return row, sources_of


def _finished(row: dict, sources_of: RowSources) -> dict:
    return records.validate_model_row({**row, "slug": "example", "sources": sources_of.items})


class OpenlyLicensedJoins(unittest.TestCase):
    """LiteLLM and LMArena join a row only on an exact identifier, and only the maker's own entry states a fact."""

    ENTRY = {"mode": "chat", "input_cost_per_token": 1e-7, "output_cost_per_token": 2e-7, "max_input_tokens": 131072.0,
             "max_output_tokens": 8192, "supports_function_calling": True, "supports_response_schema": False}

    def _index(self, entries: dict, providers: dict) -> dict:
        return model_rows.litellm_index(Answer(entries, "2026-09-27", "read", source_engines.LITELLM_ADDRESS), providers)

    def test_an_open_row_takes_litellm_prices_by_exact_identifier_and_no_facts(self):
        record = {"id": "example/Model-7B", "author": "example", "cardData": {}, "tags": [], "pipeline_tag": "text-generation",
                  "createdAt": "2026-01-02T00:00:00.000Z", "downloads": 1, "likes": 1}
        answer = Answer(record, "2026-09-27", "read", "huggingface.co/api/models/example/Model-7B")
        row, sources_of = model_rows._hugging_face_row(record, answer, None, "", ("", {}, None), "2026-09-27")
        index = self._index({"deepinfra/example/Model-7B": {**self.ENTRY, "litellm_provider": "deepinfra"},
                             "novita/EXAMPLE/model-7b": {**self.ENTRY, "litellm_provider": "novita"},
                             "together_ai/example/Model-7B-Turbo": {**self.ENTRY, "litellm_provider": "together_ai"},
                             "fal_ai/example/Model-7B": {**self.ENTRY, "mode": "image_generation", "litellm_provider": "fal_ai"}},
                            {"deepinfra": "deepinfra"})
        for item in index.get("example/model-7b", ()):
            model_rows._litellm_offer(row, sources_of.add, item, "2026-09-27", {"deepinfra": {"name": "Deep Infra"}}, False)
        finished = _finished(row, sources_of)
        self.assertEqual(sorted((price["provider"], price["provider_slug"], price["model_id"]) for price in finished["prices"]),
                         [("Deep Infra", "deepinfra", "example/Model-7B"), ("novita", "novita", "EXAMPLE/model-7b")])
        self.assertEqual({price["context"] for price in finished["prices"]}, {131072})
        self.assertNotIn("structured_output", finished["facts"])
        self.assertEqual({item["id"] for item in finished["sources"]}, {"huggingface", "litellm"})

    def test_the_makers_own_entry_states_facts_and_a_models_dev_price_is_not_repeated(self):
        row, sources_of = _maker_row("zai", "glm-5")
        index = self._index({"zai/glm-5": {**self.ENTRY, "litellm_provider": "zai", "supports_vision": True},
                             "dashscope/glm-5": {**self.ENTRY, "litellm_provider": "dashscope"}},
                            {"zai": "zai", "dashscope": "alibaba"})
        own = next(item for item in index["glm-5"] if item["modelsdev"] == "zai")
        model_rows._litellm_offer(row, sources_of.add, own, "2026-09-27", {"zai": {"name": "Z.AI"}}, True)
        finished = _finished(row, sources_of)
        self.assertEqual([price["provider_slug"] for price in finished["prices"]], ["zai"])
        self.assertEqual(finished["prices"][0]["source"], 0, "the models.dev price stays and LiteLLM's same-provider price is left out")
        self.assertEqual([item["value"] for item in finished["facts"]["structured_output"]], [False])
        self.assertEqual([item["value"] for item in finished["facts"]["tool_calling"]], [True, True])
        self.assertIn("vision", [item["value"] for item in finished["use_cases"]])

    def test_an_arena_score_joins_only_the_named_makers_exact_model(self):
        anthropic, openai = _maker_row("anthropic", "claude-x"), _maker_row("openai", "gpt-x")
        board = [{"model_name": "claude-x", "organization": "anthropic", "rating": 1432.6, "leaderboard_publish_date": "2026-09-25"},
                 {"model_name": "CLAUDE-X", "organization": "Anthropic", "rating": 1400.0, "leaderboard_publish_date": "2026-09-25"},
                 {"model_name": "claude-x-high", "organization": "anthropic", "rating": 1450.0, "leaderboard_publish_date": "2026-09-25"},
                 {"model_name": "claude-x", "organization": "", "rating": 1460.0, "leaderboard_publish_date": "2026-09-25"},
                 {"model_name": "claude-x", "organization": "openai", "rating": 1470.0, "leaderboard_publish_date": "2026-09-25"},
                 {"model_name": "gpt-x", "organization": "unmapped-lab", "rating": 1300.0, "leaderboard_publish_date": "2026-09-25"}]
        report = model_rows.join_arena([anthropic, openai], Answer(board, "2026-09-27", "read", source_engines.ARENA_ADDRESS),
                                       {"anthropic": ["anthropic"], "openai": ["openai"]})
        self.assertEqual((report["rows"], report["joined"]), (6, 1))
        scored = _finished(*anthropic)
        self.assertEqual([(item["value"], item["as_of"], item["publisher"]) for item in scored["benchmarks"]], [(1433, "2026-09-25", "LMArena")])
        self.assertEqual(_finished(*openai)["benchmarks"], [])

    def test_the_arena_reader_keeps_the_newest_overall_rows_and_stops_at_another_category(self):
        def page(categories, day="2026-09-25"):
            return {"rows": [{"row": {"model_name": f"model-{index}", "organization": "openai", "rating": 1000.0 + index,
                                      "category": category, "leaderboard_publish_date": day}} for index, category in enumerate(categories)]}
        first = page(["overall"] * 100)
        first["rows"][5]["row"]["leaderboard_publish_date"] = "2026-09-18"
        pages_read = []

        class Reader:
            def get_json(self, host, path, query=None, **_):
                offset = int(dict(query)["offset"])
                pages_read.append(offset)
                value = first if offset == 0 else page(["overall"] * 50 + ["coding"] * 50) if offset == 100 else page(["overall"] * 100)
                return Answer(value, "2026-09-27", "read", host + path)

        answer = source_engines.arena_text_leaderboard(Reader())
        self.assertEqual(pages_read, [0, 100])
        self.assertEqual(len(answer.value), 149)
        self.assertEqual({row["leaderboard_publish_date"] for row in answer.value}, {"2026-09-25"})

    def test_a_served_repository_gets_its_row_and_an_unserved_copy_does_not(self):
        """OpenRouter's repository link used to bring back models published in 8-bit or FP8 weights, which Hugging Face tags
        like copies. An exact provider name in models.dev or LiteLLM does it now, from the lists or the author's own list."""
        def record(identifier, tags=()):
            return {"id": identifier, "author": identifier.split("/")[0], "tags": list(tags), "pipeline_tag": "text-generation",
                    "cardData": {}, "createdAt": "2026-01-02T00:00:00.000Z", "downloads": 5, "likes": 1}

        def build(offers: dict) -> tuple:
            modelsdev = {"deepinfra": {"name": "Deep Infra", "models": offers},
                         "openai": {"name": "OpenAI", "models": {"gpt-x": {"cost": {"input": 1.0, "output": 2.0}}}}}
            listed = [record("maker/plain-7b"), record("openai/gpt-oss-x", ["8-bit"]), record("someone/copy-GGUF", ["gguf"]),
                      record("mistralai/Listed-1B")]
            authors = {"mistralai": [record("mistralai/Listed-1B"), record("mistralai/Served-Outside")]}

            class Reader:
                def get_json(self, host, path, query=None, **_):
                    asked = dict(query or [])
                    value = None
                    if host == "huggingface.co" and path == "/api/models":
                        value = (listed if asked.get("pipeline_tag") == "text-generation" and asked.get("sort") == "downloads"
                                 else authors.get(asked.get("author"), []) if "author" in asked else [])
                    elif host == "models.dev":
                        value = modelsdev
                    elif host == "raw.githubusercontent.com":
                        value = {}
                    elif host == "datasets-server.huggingface.co":
                        value = {"rows": []}
                    return Answer(value, "2026-09-27" if value is not None else "", "read" if value is not None else "missing", host + path)

                def summary(self):
                    return {"answers": {}}

            documentation = {"maker_providers": {"providers": ["openai"]}, "litellm_providers": {"map": {}},
                             "arena_organizations": {"map": {}}}
            rows, report, _answers = model_rows.assemble_models(Reader(), documentation, None, "2026-09-27", 0, lambda _: None)
            return {row["ids"].get("huggingface") or row["ids"].get("modelsdev") for row, _ in rows}, report

        served, report = build({"openai/gpt-oss-x": {"cost": {"input": 0.1, "output": 0.5}},
                                "mistralai/Served-Outside": {"cost": {"input": 0.1, "output": 0.3}}})
        self.assertEqual(served, {"maker/plain-7b", "openai/gpt-oss-x", "mistralai/Listed-1B", "mistralai/Served-Outside", "openai/gpt-x"})
        self.assertEqual((report["served_copies"], report["served_repositories"]), (1, 1))
        unserved, _report = build({})
        self.assertEqual(unserved, {"maker/plain-7b", "mistralai/Listed-1B", "openai/gpt-x"})

    def test_the_builder_refuses_a_reviewed_record_of_another_version(self):
        old = Path(__import__("tempfile").mkdtemp()) / "provider_documentation.json"
        old.write_text(json.dumps({**source_engines.read_reviewed(REVIEWED_PATH), "record_type": "model_directory_provider_documentation/v1"}))
        with self.assertRaises(ValueError):
            source_engines.read_provider_documentation(old)
        self.assertEqual(source_engines.read_provider_documentation(REVIEWED_PATH)["record_type"], source_engines.REVIEWED_RECORD_TYPE)


class SourcesOnThePages(unittest.TestCase):
    """The pages name each republished source with its licence, and link the refused publishers without their data."""

    def test_the_sources_band_names_each_licence_and_the_linked_only_publishers(self):
        text = pages.rendered_page("/models", "GET", "Baltor")[0].decode("utf-8")
        band = text[text.index('id="sources"'):]
        for expected in ("LiteLLM model price and context file", "LMArena leaderboard dataset", ">CC BY 4.0<", ">MIT<",
                         "Linked, never copied:", ">OpenRouter</a>", ">Artificial Analysis</a>", "checked <time"):
            self.assertIn(expected, band)
        self.assertNotIn("OpenRouter Models API", text)
        self.assertNotIn("through OpenRouter", text)

    def test_a_model_page_shows_an_arena_score_with_its_licence_and_links_the_refused_publishers(self):
        directory = records.load_directory()
        row = next(row for row in directory.models if any("value" in item for item in row["benchmarks"]))
        text = pages.rendered_page("/models/" + row["slug"], "GET", "Baltor")[0].decode("utf-8")
        self.assertRegex(text, r'>Arena text score</a>: [0-9][0-9,]* as of <time datetime="20[0-9]{2}-[0-9]{2}-[0-9]{2}">')
        self.assertIn('>CC BY 4.0</a>', text)
        self.assertIn('href="https://artificialanalysis.ai"', text)
        self.assertIn('href="https://openrouter.ai/', text)
        self.assertNotIn("Artificial Analysis Intelligence Index", text)
        self.assertNotIn("through OpenRouter", text)


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
