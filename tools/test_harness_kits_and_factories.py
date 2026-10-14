"""Comprehensive unit and integration tests for Track 3: AgentFoundry Starter Kits, Drift Linters and Supply Factories."""
from __future__ import annotations

from contextlib import redirect_stdout
from copy import deepcopy
from dataclasses import replace
import io
import json
from pathlib import Path
import tempfile
import unittest

import build_harness_starter_kit
from harness_kits import (
    HARNESS_CHOICES,
    STARTER_KIT_SPECS,
    SUPPORTED_HARNESSES,
    StarterKitError,
    build_starter_kit,
    check_llm_sdk_drift,
    check_mcp_server_safety,
    check_nextjs_react19_tailwind4_drift,
    check_pydantic_v2_fastapi_drift,
    check_starter_kit_folder,
    run_all_drift_linters,
    run_kit_verifier,
    write_starter_kit,
)
from supply_lines.regex_recipe_factory import (
    REGEX_RECIPES,
    build_all_regex_components,
    verify_regex_component,
)
from supply_lines.sql_query_recipe_factory import (
    CATEGORIES as SQL_CATEGORIES,
    SQL_QUERY_RECIPE_SPECS,
    build_all_sql_query_recipe_components,
    verify_sql_query_recipe_component,
)
from supply_lines.timezone_calendar_factory import (
    TIMEZONE_CALENDAR_SPECS,
    build_all_timezone_calendar_components,
    verify_timezone_calendar_component,
)
from supply_lines.unit_conversion_factory import (
    DIMENSIONS,
    UNIT_CONVERSION_SPECS,
    build_all_unit_conversion_components,
    verify_unit_conversion_component,
)


class HarnessKitsAndFactoriesTests(unittest.TestCase):
    def test_native_harness_layout_and_config_exclude_fake_mcp_server(self) -> None:
        kit = build_starter_kit(STARTER_KIT_SPECS[0].kit_id)
        bodies = kit["file_bodies"]
        self.assertIn(f".agents/skills/{kit['kit_id']}/SKILL.md", bodies)
        self.assertIn(f".opencode/skills/{kit['kit_id']}/SKILL.md", bodies)
        self.assertIn(".codex/config.toml", bodies)
        config = json.loads(bodies["opencode.json"])
        self.assertNotIn("starter_kit", config)
        self.assertIn(f".opencode/skills/{kit['kit_id']}/SKILL.md", config["instructions"])
        self.assertEqual(set(json.loads(bodies[".mcp.json"])["mcpServers"]), {"baltor"})
        self.assertNotIn(b"kit_verifier", bodies[".codex/config.toml"])
        self.assertFalse(config["mcp"]["baltor"]["enabled"])

    def test_kit_verifier_refuses_tampered_executable_before_execution(self) -> None:
        kit = build_starter_kit(STARTER_KIT_SPECS[0].kit_id)
        kit["file_bodies"]["verify_kit.py"] = b"raise RuntimeError('untrusted code ran')\n"
        with self.assertRaisesRegex(StarterKitError, "noncanonical"):
            run_kit_verifier(kit)

    def test_kit_writer_refuses_changed_bytes_before_creating_folder(self) -> None:
        kit = build_starter_kit(STARTER_KIT_SPECS[0].kit_id)
        kit["file_bodies"]["AGENTS.md"] += b"\nUnexpected local mutation.\n"
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(StarterKitError, "noncanonical"):
                write_starter_kit(temp, "kit", kit, authorized=True)
            self.assertEqual(list(Path(temp).iterdir()), [])

    def test_kit_refuses_forged_package_metadata(self) -> None:
        kit = build_starter_kit(STARTER_KIT_SPECS[0].kit_id)
        kit["record"]["package_digest"] = "0" * 64
        with self.assertRaisesRegex(StarterKitError, "noncanonical"):
            run_kit_verifier(kit)

    def test_custom_override_is_not_silently_ignored(self) -> None:
        with self.assertRaisesRegex(StarterKitError, "custom_override_not_supported"):
            build_starter_kit(STARTER_KIT_SPECS[0].kit_id, custom_override_text="My instructions")

    def test_generated_verifier_fails_missing_feed_files(self) -> None:
        kit = build_starter_kit(STARTER_KIT_SPECS[0].kit_id)
        namespace = {"__name__": "fixture"}
        # Exact first-party source only; this is not an untrusted-code executor.
        exec(compile(kit["file_bodies"]["verify_kit.py"], "verify_kit.py", "exec"), namespace)
        with tempfile.TemporaryDirectory() as temp:
            self.assertFalse(namespace["verify"](Path(temp))["passed"])

    def test_all_factory_verifiers_refuse_code_and_metadata_mutations(self) -> None:
        populations = [
            (build_all_regex_components(), verify_regex_component),
            (build_all_unit_conversion_components(), verify_unit_conversion_component),
            (build_all_timezone_calendar_components(), verify_timezone_calendar_component),
            (build_all_sql_query_recipe_components(), verify_sql_query_recipe_component),
        ]
        for population, verify in populations:
            original = population[0]
            self.assertFalse(original["admission_ready"])
            self.assertNotIn("record_type", original)
            for field in ("code", "digest", "files", "authority"):
                with self.subTest(factory=original["factory_id"], field=field):
                    changed = deepcopy(original)
                    if field == "code":
                        path = "pattern.py" if "pattern.py" in changed["file_bodies"] else "implement.py"
                        changed["file_bodies"][path] = b"raise RuntimeError('untrusted code ran')\n"
                    elif field == "digest":
                        changed["package_digest"] = "0" * 64
                    elif field == "files":
                        changed["file_bodies"]["extra.py"] = b"raise RuntimeError('untrusted code ran')\n"
                    else:
                        changed["approved"] = True
                    with self.assertRaisesRegex(ValueError, "noncanonical"):
                        verify(changed)

    def test_factories_refuse_unregistered_specs(self) -> None:
        from supply_lines.regex_recipe_factory import build_regex_component
        from supply_lines.unit_conversion_factory import build_unit_conversion_component
        from supply_lines.timezone_calendar_factory import build_timezone_calendar_component
        from supply_lines.sql_query_recipe_factory import build_sql_query_recipe_component
        for spec, build in [(REGEX_RECIPES[0], build_regex_component),
                            (UNIT_CONVERSION_SPECS[0], build_unit_conversion_component),
                            (TIMEZONE_CALENDAR_SPECS[0], build_timezone_calendar_component),
                            (SQL_QUERY_RECIPE_SPECS[0], build_sql_query_recipe_component)]:
            with self.assertRaisesRegex(ValueError, "unregistered_factory_spec"):
                build(replace(spec, title='Unreviewed input'))

    def test_unknown_regex_is_not_run_in_process(self) -> None:
        from supply_lines.regex_recipe_factory import check_redos_safety
        with self.assertRaisesRegex(ValueError, "requires_sandbox"):
            check_redos_safety("(a+)+$")

    def test_secret_linter_does_not_echo_credential(self) -> None:
        sample = "API_KEY = 'example-placeholder'"
        report = check_mcp_server_safety(sample)
        self.assertFalse(report["passed"])
        self.assertNotIn("example-placeholder", json.dumps(report))

    def test_combined_linter_never_echoes_json_call_argument_literals(self) -> None:
        marker = "review-placeholder-value"
        report = run_all_drift_linters("model.json(api_key=" + repr(marker) + ")")
        self.assertFalse(report["passed"])
        self.assertNotIn(marker, json.dumps(report))
        pydantic = check_pydantic_v2_fastapi_drift("model.json(api_key=" + repr(marker) + ")")
        self.assertEqual(pydantic["finding_count"], 1)
        self.assertNotIn(marker, json.dumps(pydantic))

    def test_finding_redaction_covers_message_match_and_replacement(self) -> None:
        from harness_kits.drift_linters import _make_finding
        marker = "review-placeholder-value"
        assignment = "api_key=" + repr(marker)
        finding = _make_finding("test.rule", 1, assignment, assignment, assignment)
        for field in ("matched_text", "message", "replacement"):
            self.assertIn("[redacted credential]", finding[field])
            self.assertNotIn(marker, finding[field])

    def test_kit_check_refuses_unlisted_native_instructions_and_entries(self) -> None:
        bundle = build_starter_kit(STARTER_KIT_SPECS[0].kit_id, harness="codex")
        variants = ("AGENTS.override.md", ".agents/skills/unlisted/SKILL.md", "unlisted-directory", "unlisted-symlink", "unlisted-fifo")
        import os
        for variant in variants:
            with self.subTest(variant=variant), tempfile.TemporaryDirectory() as temp:
                folder = write_starter_kit(temp, "kit", bundle, authorized=True)
                extra = folder / variant
                if variant == "unlisted-directory":
                    extra.mkdir()
                elif variant == "unlisted-symlink":
                    extra.symlink_to(folder / "AGENTS.md")
                elif variant == "unlisted-fifo":
                    os.mkfifo(extra)
                else:
                    extra.parent.mkdir(parents=True, exist_ok=True)
                    extra.write_text("Harmless unlisted review instructions.\n", encoding="utf-8")
                with self.assertRaisesRegex(StarterKitError, "unexpected|inventory"):
                    check_starter_kit_folder(folder)

    def test_invalid_python_is_not_a_clean_mcp_check(self) -> None:
        report = check_mcp_server_safety("def malformed(:\n")
        self.assertFalse(report["passed"])
        self.assertIn("mcp_safety.source_syntax_invalid", [item["rule_id"] for item in report["findings"]])

    def test_timezone_profile_refuses_oversized_or_malformed_inputs(self) -> None:
        from supply_lines.timezone_calendar_factory import execute_timezone_calendar
        for value in ("2026-01-01Z", "2026-01-01T12:00:00+03:00Z", "2026-01-01 12:00:00Z"):
            with self.assertRaises(ValueError):
                execute_timezone_calendar(TIMEZONE_CALENDAR_SPECS[0].component_id,
                                          utc_iso=value, tz_name="America/New_York")
        business = next(item for item in TIMEZONE_CALENDAR_SPECS if item.config.get("op") == "add_days")
        for value in (True, 3661, 10**10):
            with self.assertRaises(ValueError):
                execute_timezone_calendar(business.component_id, start_date="2026-01-01", business_days=value)

    def test_unit_conversion_refuses_nonfinite_results(self) -> None:
        from supply_lines.unit_conversion_factory import convert_units
        spec = next(item for item in UNIT_CONVERSION_SPECS if max(x[0] for x in item.units.values()) > 1)
        large = max(spec.units, key=lambda unit: spec.units[unit][0])
        small = min(spec.units, key=lambda unit: spec.units[unit][0])
        with self.assertRaisesRegex(ValueError, "not_finite"):
            convert_units(spec.component_id, 1.7e308, large, small)

    def test_historical_manifest_does_not_freeze_freshness_check(self) -> None:
        kit = build_starter_kit(STARTER_KIT_SPECS[0].kit_id)
        with tempfile.TemporaryDirectory() as temp:
            folder = write_starter_kit(temp, "kit", kit, authorized=True)
            with self.assertRaises(ValueError):
                check_starter_kit_folder(folder, as_of="2030-01-01")

    def test_post_cutoff_drift_linters_positive_and_known_wrong_controls(self) -> None:
        # 1. LLM SDK drift linter
        clean_llm = (
            "from openai import OpenAI\n"
            "from google import genai\n"
            "client = OpenAI()\n"
            "resp = client.responses.create(model='gpt-5.4-mini', input='hello')\n"
        )
        self.assertTrue(check_llm_sdk_drift(clean_llm, "clean_llm.py")["passed"])

        dirty_llm = (
            "import openai\n"
            "import google.generativeai as genai\n"
            "r1 = openai.ChatCompletion.create(model='gpt-3.5-turbo', messages=[])\n"
            "r2 = client.beta.assistants.create(model='claude-2.1')\n"
            "r3 = anthropic_client.completions.create(model='gemini-pro')\n"
        )
        llm_report = check_llm_sdk_drift(dirty_llm, "dirty_llm.py")
        self.assertFalse(llm_report["passed"])
        self.assertGreaterEqual(llm_report["finding_count"], 5)

        # 2. Pydantic v2 & FastAPI drift linter
        clean_pyd = (
            "from contextlib import asynccontextmanager\n"
            "from pydantic import BaseModel, ConfigDict, field_validator\n"
            "class Item(BaseModel):\n"
            "    model_config = ConfigDict(from_attributes=True)\n"
            "    name: str\n"
            "    @field_validator('name')\n"
            "    @classmethod\n"
            "    def check_name(cls, v: str) -> str:\n"
            "        return v.strip()\n"
        )
        self.assertTrue(check_pydantic_v2_fastapi_drift(clean_pyd, "clean_pyd.py")["passed"])

        dirty_pyd = (
            "from pydantic import BaseModel, validator, root_validator\n"
            "class User(BaseModel):\n"
            "    class Config:\n"
            "        orm_mode = True\n"
            "    @validator('name')\n"
            "    def v(cls, val): return val\n"
            "@app.on_event('startup')\n"
            "async def init_db():\n"
            "    data = User.parse_obj({}).dict()\n"
        )
        pyd_report = check_pydantic_v2_fastapi_drift(dirty_pyd, "dirty_pyd.py")
        self.assertFalse(pyd_report["passed"])
        self.assertGreaterEqual(pyd_report["finding_count"], 5)

        # 3. Next.js 15 / React 19 / Tailwind v4 drift linter
        clean_next = (
            "import { useActionState } from 'react';\n"
            "export async function Page() {\n"
            "  const cookieStore = await cookies();\n"
            "  return cookieStore.get('sid');\n"
            "}\n"
        )
        self.assertTrue(check_nextjs_react19_tailwind4_drift(clean_next, "page.tsx")["passed"])

        dirty_next = (
            "import { useFormState } from 'react-dom';\n"
            "export function Page() {\n"
            "  const sid = cookies().get('sid');\n"
            "  const h = headers().get('x-test');\n"
            "  return null;\n"
            "}\n"
        )
        next_report = check_nextjs_react19_tailwind4_drift(dirty_next, "page.tsx")
        self.assertFalse(next_report["passed"])
        self.assertGreaterEqual(next_report["finding_count"], 3)

        dirty_css = "@tailwind base;\n@tailwind components;\n@tailwind utilities;\n"
        css_report = check_nextjs_react19_tailwind4_drift(dirty_css, "globals.css")
        self.assertFalse(css_report["passed"])

        # 4. MCP server safety linter
        clean_mcp = (
            "import sys\n"
            "import subprocess\n"
            "def handle_tool(limit: int = 20) -> dict:\n"
            "    bounded = max(1, min(limit, 100))\n"
            "    sys.stderr.write('diagnostic log\\n')\n"
            "    subprocess.run(['git', 'status'], check=True)\n"
            "    return {'limit': bounded}\n"
        )
        self.assertTrue(check_mcp_server_safety(clean_mcp, "mcp_server.py")["passed"])

        dirty_mcp = (
            "import subprocess\n"
            "API_KEY = 'example-placeholder'\n"
            "def handle_tool(cmd: str):\n"
            "    print('debugging to stdout in stdio server')\n"
            "    subprocess.run(cmd, shell=True)\n"
        )
        mcp_report = check_mcp_server_safety(dirty_mcp, "mcp_server.py")
        self.assertFalse(mcp_report["passed"])
        self.assertGreaterEqual(mcp_report["finding_count"], 3)

        combined = run_all_drift_linters(dirty_pyd, "dirty_pyd.py")
        self.assertFalse(combined["passed"])

    def test_all_10_starter_kits_build_verify_and_enforce_confinement(self) -> None:
        self.assertEqual(len(STARTER_KIT_SPECS), 10)
        self.assertEqual(SUPPORTED_HARNESSES, ("claude_code", "codex", "cursor", "opencode"))
        self.assertIn("all", HARNESS_CHOICES)

        for spec in STARTER_KIT_SPECS:
            for harness in SUPPORTED_HARNESSES:
                built = build_starter_kit(spec.kit_id, harness=harness)
                rec = built["record"]
                self.assertEqual(rec["record_type"], "agent_foundry_starter_kit/v1")
                self.assertFalse(rec["approved"])
                self.assertFalse(rec["published"])
                self.assertEqual(rec["effects_granted"], [])
                v_res = run_kit_verifier(built)
                self.assertTrue(v_res["passed"], f"Kit {spec.kit_id} ({harness}) failed verifier: {v_res}")

        # Materialize and check folder with 'all' harnesses, plus CLI and symlink/grant refusals
        with tempfile.TemporaryDirectory() as tmp:
            root_dir = Path(tmp)
            bundle = build_starter_kit("python-modern-uv-pydantic2", harness="all")
            with self.assertRaises(PermissionError):
                write_starter_kit(root_dir, "kit_bundle", bundle, authorized=False)

            written_path = write_starter_kit(
                root_dir,
                "kit_bundle",
                bundle,
                authorized=True,
            )
            self.assertTrue(written_path.is_dir())
            checked = check_starter_kit_folder(written_path)
            self.assertEqual(checked["status"], "validated_starter_kit")

            # Symlink target must be refused
            symlink_root = Path(tmp) / "sym_root"
            symlink_root.symlink_to(root_dir)
            with self.assertRaises((StarterKitError, OSError)):
                write_starter_kit(symlink_root, "kit2", bundle, authorized=True)

            # CLI dry-run plan check
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = build_harness_starter_kit.main(
                    ["--kit", "mcp-server-authoring-and-security", "--harness", "claude_code"]
                )
            self.assertEqual(rc, 0)
            plan_doc = json.loads(buf.getvalue())
            self.assertEqual(plan_doc["kit_id"], "mcp-server-authoring-and-security")
            self.assertEqual(plan_doc["status"], "validated_only")

    def test_all_200_generated_supply_line_components_execute_and_verify(self) -> None:
        # 1. 50 Regex recipe components
        regex_comps = build_all_regex_components()
        self.assertEqual(len(regex_comps), 50)
        self.assertEqual(len(REGEX_RECIPES), 50)
        for comp in regex_comps:
            res = verify_regex_component(comp)
            self.assertTrue(res["passed"], f"Regex component failed: {res}")

        # 2. 60 Unit conversion components across 12 physical dimensions
        unit_comps = build_all_unit_conversion_components()
        self.assertEqual(len(unit_comps), 60)
        self.assertEqual(len(UNIT_CONVERSION_SPECS), 60)
        self.assertEqual(len(DIMENSIONS), 12)
        for comp in unit_comps:
            res = verify_unit_conversion_component(comp)
            self.assertTrue(res["passed"], f"Unit conversion component failed: {res}")

        # 3. 40 Timezone & calendar components
        tz_comps = build_all_timezone_calendar_components()
        self.assertEqual(len(tz_comps), 40)
        self.assertEqual(len(TIMEZONE_CALENDAR_SPECS), 40)
        for comp in tz_comps:
            res = verify_timezone_calendar_component(comp)
            self.assertTrue(res["passed"], f"Timezone component failed: {res}")

        # 4. 50 SQLite analytical query recipe components across 5 categories
        sql_comps = build_all_sql_query_recipe_components()
        self.assertEqual(len(sql_comps), 50)
        self.assertEqual(len(SQL_QUERY_RECIPE_SPECS), 50)
        self.assertEqual(len(SQL_CATEGORIES), 5)
        for comp in sql_comps:
            res = verify_sql_query_recipe_component(comp)
            self.assertTrue(res["passed"], f"SQL recipe component failed: {res}")

        total_components = len(regex_comps) + len(unit_comps) + len(tz_comps) + len(sql_comps)
        self.assertEqual(total_components, 200)

    def test_zero_em_or_en_dashes_across_all_track3_sources_and_generated_files(self) -> None:
        root = Path(__file__).resolve().parents[1]
        track3_files = [
            root / "tools" / "harness_kits" / "__init__.py",
            root / "tools" / "harness_kits" / "drift_linters.py",
            root / "tools" / "harness_kits" / "catalog.py",
            root / "tools" / "harness_kits" / "builder.py",
            root / "tools" / "build_harness_starter_kit.py",
            root / "tools" / "supply_lines" / "regex_recipe_factory.py",
            root / "tools" / "supply_lines" / "unit_conversion_factory.py",
            root / "tools" / "supply_lines" / "timezone_calendar_factory.py",
            root / "tools" / "supply_lines" / "sql_query_recipe_factory.py",
            root / "tools" / "test_harness_kits_and_factories.py",
        ]
        for path in track3_files:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("\u2014", text, f"Found em dash in {path}")
            self.assertNotIn("\u2013", text, f"Found en dash in {path}")


if __name__ == "__main__":
    unittest.main()
