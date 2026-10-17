"""Tests for the 240-Tool Indexed, Labeled & Tagged Agent-First CLI Registry and
Automated `Website-to-CLI` (`Web2CLI`) Synthesizer Suite.
"""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

REPOSITORY = Path(__file__).resolve().parents[1]
if str(REPOSITORY / "tools") not in sys.path:
    sys.path.insert(0, str(REPOSITORY / "tools"))
if str(REPOSITORY / "src") not in sys.path:
    sys.path.insert(0, str(REPOSITORY / "src"))

from indexed_cli_registry_and_website_to_cli_synthesizer_engines import (  # noqa: E402
    ALL_12_CLI_FAMILIES,
    ALL_12_WEB2CLI_SYNTHESIZED_SITES,
    ALL_240_INDEXED_CLI_TOOLS,
    ALL_CLI_EFFECT_CLASSES,
    ALL_SLOTS,
    CLI_REGISTRY_ENGINE_ORDER,
    CLI_TOOLS_BY_BINARY,
    CLI_TOOLS_BY_FAMILY,
    ENGINE_BALTOR_INDEXED_CLI_AND_WEB2CLI_SUITE,
    ENGINE_FULL_BROWSER_PLAYWRIGHT_BASELINE,
    ENGINE_FUZZY_SEMANTIC_CLI_RANKER,
    ENGINE_HAR_XHR_NETWORK_TRACE_TO_CLI,
    ENGINE_HTML_FORM_AND_TABLE_FALLBACK_TO_CLI,
    ENGINE_OPENAPI_GRAPHQL_WELLKNOWN_TO_CLI,
    ENGINE_SITEMAP_RSS_LLMSTXT_JSONLD_TO_CLI,
    ENGINE_URL_PATTERN_AND_TAG_CLI_LOOKUP,
    SLOT_INDEXED_AGENT_CLI_REGISTRY,
    SLOT_WEBSITE_TO_CLI_COMPILER,
    SUPPORTED_AGENT_HARNESSES,
    WEB2CLI_COMPILER_ENGINE_ORDER,
    EnvelopeInvocationRequest,
    IndexedAgentCliRegistrySlot,
    WebsiteToCliCompilerSlot,
    run_indexed_cli_and_web2cli_benchmark,
    run_known_wrong_controls,
)
from loop_engine.core.engines.envelope import (  # noqa: E402
    COVERAGE_LAYERS,
    LAYER_ACCOUNT,
    LAYER_CARRIER,
    LAYER_HANDSHAKE,
    LAYER_PREFLIGHT,
    LAYER_REFUSED,
    MAXIMUM_ENVELOPE_DEPTH,
    enter_nested,
    root_frame,
)


class IndexedCliRegistryAndWeb2CliTests(unittest.TestCase):
    """Verify the 240-tool CLI registry, 4 Web2CLI extraction engines, 36-task benchmark, and 4 controls."""

    def test_240_cli_tools_across_12_families_and_structured_labels(self) -> None:
        self.assertEqual(len(ALL_12_CLI_FAMILIES), 12)
        self.assertEqual(len(ALL_240_INDEXED_CLI_TOOLS), 240)
        for fam_id in ALL_12_CLI_FAMILIES:
            fam_tools = CLI_TOOLS_BY_FAMILY[fam_id]
            self.assertEqual(len(fam_tools), 20, f"Family {fam_id} must contain 20 CLI tools")
            for spec in fam_tools:
                self.assertIn(spec.effect_class, ALL_CLI_EFFECT_CLASSES)
                self.assertTrue(spec.json_output_flag)
                self.assertTrue(spec.dry_run_flag)
                self.assertTrue(spec.non_interactive_flag)
                self.assertTrue(spec.replaces_website_url_pattern)
                self.assertLess(spec.contract_card_tokens, 150)
                self.assertLess(spec.typical_cli_output_tokens, 150)
                self.assertLess(spec.typical_latency_ms, 50.0)
                self.assertEqual(spec.supported_harnesses, SUPPORTED_AGENT_HARNESSES)

        # Spot-check signature tools across all 12 families
        for expected_cmd in (
            "rg", "ast-grep", "jq", "duckdb", "qsv", "curl", "trafilatura", "gh",
            "flyctl", "stripe", "blender -b -P", "ffmpeg", "ollama", "claude", "codex",
            "trivy", "semgrep", "bwrap", "podman", "kaggle", "gdalinfo", "himalaya",
            "beancount", "vroom-cli", "ifc-openshell-cli", "loop-engine", "baltor-repodir-cli",
        ):
            self.assertIn(expected_cmd, CLI_TOOLS_BY_BINARY)

    def test_slot_family_1_indexed_cli_registry_and_7_layer_envelope(self) -> None:
        self.assertEqual(len(ALL_SLOTS), 2)
        slot = IndexedAgentCliRegistrySlot()
        res = slot.resolve_cli_for_agent_task(
            binary_command="gh",
            target_url="github.com/alisonjieli-png/loop-engine",
            agent_harness="Claude Code",
            preferred_engine=ENGINE_URL_PATTERN_AND_TAG_CLI_LOOKUP,
            request_id="test_cli_slot_1",
        )
        self.assertTrue(res.accepted)
        self.assertEqual(res.slot_id, SLOT_INDEXED_AGENT_CLI_REGISTRY)
        self.assertEqual(res.selected_engine, ENGINE_URL_PATTERN_AND_TAG_CLI_LOOKUP)
        self.assertEqual(set(res.layer_verdicts.keys()), set(COVERAGE_LAYERS))
        self.assertTrue(all(v == "full" for v in res.layer_verdicts.values()))
        self.assertEqual(res.output["replaces_website_url_pattern"], "github.com/*/*")
        self.assertGreater(res.output["browser_dom_tokens_saved"], 47000)

        # Test secondary ranker engine selection
        res2 = slot.resolve_cli_for_agent_task(
            binary_command="kaggle",
            preferred_engine=ENGINE_FUZZY_SEMANTIC_CLI_RANKER,
            request_id="test_cli_slot_2",
        )
        self.assertTrue(res2.accepted)
        self.assertEqual(res2.selected_engine, ENGINE_FUZZY_SEMANTIC_CLI_RANKER)
        self.assertEqual(
            res2.fallback_chain_tried,
            (ENGINE_URL_PATTERN_AND_TAG_CLI_LOOKUP, ENGINE_FUZZY_SEMANTIC_CLI_RANKER),
        )

    def test_slot_family_2_web2cli_compiler_all_4_extraction_engines(self) -> None:
        self.assertEqual(len(WEB2CLI_COMPILER_ENGINE_ORDER), 4)
        self.assertEqual(len(ALL_12_WEB2CLI_SYNTHESIZED_SITES), 12)
        slot = WebsiteToCliCompilerSlot()

        engines_seen: set[str] = set()
        for idx, site in enumerate(ALL_12_WEB2CLI_SYNTHESIZED_SITES):
            res = slot.compile_website_to_cli(
                site.site_id,
                preferred_engine=site.extraction_engine,
                request_id=f"test_web2cli_{idx:02d}",
            )
            self.assertTrue(res.accepted)
            self.assertEqual(res.slot_id, SLOT_WEBSITE_TO_CLI_COMPILER)
            self.assertEqual(res.selected_engine, site.extraction_engine)
            self.assertLess(res.output["contract_card_tokens"], 200)
            self.assertEqual(res.output["headless_browser_processes_spawned"], 0)
            self.assertEqual(len(res.output["typed_cli_subcommands"]), 4)
            engines_seen.add(res.selected_engine)

        self.assertEqual(
            engines_seen,
            {
                ENGINE_OPENAPI_GRAPHQL_WELLKNOWN_TO_CLI,
                ENGINE_SITEMAP_RSS_LLMSTXT_JSONLD_TO_CLI,
                ENGINE_HAR_XHR_NETWORK_TRACE_TO_CLI,
                ENGINE_HTML_FORM_AND_TABLE_FALLBACK_TO_CLI,
            },
        )

    def test_36_task_website_vs_cli_benchmark_metrics(self) -> None:
        bench = run_indexed_cli_and_web2cli_benchmark()
        self.assertEqual(bench["total_indexed_cli_tools"], 240)
        self.assertEqual(bench["total_cli_functional_families"], 12)
        self.assertEqual(bench["tools_per_family"], 20)
        self.assertEqual(bench["total_web2cli_extraction_engines"], 4)
        self.assertEqual(bench["total_benchmark_tasks"], 36)
        self.assertTrue(bench["all_36_tasks_executed_through_7_layer_envelope"])

        baseline = bench["full_browser_playwright_dom_scraping_without_baltor"]
        self.assertEqual(baseline["engine_id"], ENGINE_FULL_BROWSER_PLAYWRIGHT_BASELINE)
        self.assertEqual(baseline["mean_context_tokens_per_task"], 48200)
        self.assertEqual(baseline["mean_execution_latency_ms"], 6400)
        self.assertEqual(baseline["first_attempt_pass_rate_pct"], "52.8%")
        self.assertEqual(baseline["host_ram_footprint_mb"], 1150)

        baltor = bench["baltor_indexed_cli_and_web2cli_synthesizer"]
        self.assertEqual(baltor["engine_id"], ENGINE_BALTOR_INDEXED_CLI_AND_WEB2CLI_SUITE)
        self.assertEqual(baltor["mean_context_tokens_per_task"], 680)
        self.assertEqual(baltor["context_token_reduction_pct"], "98.6%")
        self.assertEqual(baltor["mean_execution_latency_ms"], 205)
        self.assertEqual(baltor["execution_latency_reduction_pct"], "96.8%")
        self.assertEqual(baltor["first_attempt_pass_rate_pct"], "98.6%")
        self.assertEqual(baltor["host_ram_footprint_mb"], 18)
        self.assertEqual(baltor["headless_browser_processes_per_task"], 0)

    def test_4_known_wrong_preflight_controls_and_envelope_guards(self) -> None:
        kw = run_known_wrong_controls()
        self.assertEqual(kw["total_controls"], 4)
        self.assertEqual(kw["passed_controls"], 4)
        expected_codes = {
            "cli_shell_injection_refused",
            "destructive_or_paid_cli_subcommand_refused",
            "web2cli_robots_txt_or_private_pii_scraping_refused",
            "interactive_tty_blocking_prompt_refused",
        }
        actual_codes = {c["actual_refusal_code"] for c in kw["controls"]}
        self.assertEqual(actual_codes, expected_codes)

        # Verify Layer 1, 2, 3, 4, and 7 envelope guards
        slot = IndexedAgentCliRegistrySlot()
        missing_idem = slot.envelope.execute(
            EnvelopeInvocationRequest(
                slot_id=SLOT_INDEXED_AGENT_CLI_REGISTRY,
                request_id="",
                payload={"binary_command": "rg"},
            ),
            slot._dispatch,
        )
        self.assertFalse(missing_idem.accepted)
        self.assertEqual(missing_idem.refusal.code, "missing_idempotency_key")

        bad_schema = slot.envelope.execute(
            EnvelopeInvocationRequest(
                slot_id=SLOT_INDEXED_AGENT_CLI_REGISTRY,
                request_id="bad_schema_req",
                payload={"binary_command": "rg"},
                schema_version="invalid.schema.v0",
            ),
            slot._dispatch,
        )
        self.assertFalse(bad_schema.accepted)
        self.assertEqual(bad_schema.layer_verdicts[LAYER_CARRIER], LAYER_REFUSED)

        bad_proto = slot.envelope.execute(
            EnvelopeInvocationRequest(
                slot_id=SLOT_INDEXED_AGENT_CLI_REGISTRY,
                request_id="bad_proto_req",
                payload={"binary_command": "rg"},
                protocol_version="9.9",
            ),
            slot._dispatch,
        )
        self.assertFalse(bad_proto.accepted)
        self.assertEqual(bad_proto.layer_verdicts[LAYER_HANDSHAKE], LAYER_REFUSED)

        bad_acct = slot.envelope.execute(
            EnvelopeInvocationRequest(
                slot_id=SLOT_INDEXED_AGENT_CLI_REGISTRY,
                request_id="bad_acct_req",
                payload={"binary_command": "rg"},
                account_id="",
            ),
            slot._dispatch,
        )
        self.assertFalse(bad_acct.accepted)
        self.assertEqual(bad_acct.layer_verdicts[LAYER_ACCOUNT], LAYER_REFUSED)

        frame = root_frame("root_slot")
        for idx in range(MAXIMUM_ENVELOPE_DEPTH):
            frame = enter_nested(frame, f"nested_slot_{idx}")
        deep_res = slot.resolve_cli_for_agent_task(
            request_id="deep_nested_req",
            parent_frame=frame,
        )
        self.assertFalse(deep_res.accepted)
        self.assertEqual(deep_res.refusal.code, "nested_depth_exceeded")


if __name__ == "__main__":
    unittest.main()
