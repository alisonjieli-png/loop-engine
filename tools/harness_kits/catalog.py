"""Catalog of the 10 AgentFoundry multi-harness starter kits.

Each starter kit provides post-cutoff anti-drift rules, harness skill and
instruction templates for Claude Code, Codex, Cursor, and OpenCode, a linked
AgentFeeds reading profile (READING.md and profile.json), and a deterministic
verifier script with positive and known-wrong controls.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

STARTER_KIT_RECORD_TYPE = "agent_foundry_starter_kit/v1"
SUPPORTED_HARNESSES = ("claude_code", "codex", "cursor", "opencode")
HARNESS_CHOICES = (*SUPPORTED_HARNESSES, "all")


@dataclass(frozen=True)
class StarterKitSpec:
    kit_id: str
    title: str
    domain: str
    description: str
    agent_label: str
    feed_collections: tuple[str, ...]
    linked_linter: str
    post_cutoff_rules: tuple[dict[str, str], ...]
    verification_commands: tuple[str, ...]
    positive_sample: str
    negative_sample: str
    forbidden_tokens: tuple[str, ...]
    required_tokens: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "kit_id": self.kit_id,
            "title": self.title,
            "domain": self.domain,
            "description": self.description,
            "agent_label": self.agent_label,
            "feed_collections": list(self.feed_collections),
            "linked_linter": self.linked_linter,
            "post_cutoff_rules": [dict(rule) for rule in self.post_cutoff_rules],
            "verification_commands": list(self.verification_commands),
            "forbidden_tokens": list(self.forbidden_tokens),
            "required_tokens": list(self.required_tokens),
        }


STARTER_KIT_SPECS: tuple[StarterKitSpec, ...] = (
    StarterKitSpec(
        kit_id="python-modern-uv-pydantic2",
        title="Python modern uv, Pydantic v2, and FastAPI lifespan starter kit",
        domain="backend_python",
        description=(
            "Prevents Pydantic v1 and FastAPI lifecycle training-cutoff drift while enforcing "
            "uv lockfile discipline, ConfigDict validation, and async lifespan context managers."
        ),
        agent_label="Python modern uv Pydantic2 builder",
        feed_collections=("developer-releases", "agent-framework-releases"),
        linked_linter="pydantic_v2_fastapi_drift",
        post_cutoff_rules=(
            {
                "rule_id": "pydantic_v2.field_validator",
                "wrong_pattern": "@validator(\"name\")",
                "correct_pattern": "@field_validator(\"name\", mode=\"after\")",
                "rationale": "Pydantic v2 replaces v1 @validator with @field_validator and explicit mode.",
            },
            {
                "rule_id": "pydantic_v2.model_dump",
                "wrong_pattern": "model.dict() / model.json() / Model.parse_obj(data)",
                "correct_pattern": "model.model_dump() / model.model_dump_json() / Model.model_validate(data)",
                "rationale": "Pydantic v2 standardizes serialization and validation under model_* methods.",
            },
            {
                "rule_id": "pydantic_v2.config_dict",
                "wrong_pattern": "class Config: orm_mode = True",
                "correct_pattern": "model_config = ConfigDict(from_attributes=True)",
                "rationale": "Pydantic v2 uses ConfigDict instead of an inner Config class.",
            },
            {
                "rule_id": "fastapi.lifespan_context",
                "wrong_pattern": "@app.on_event(\"startup\")",
                "correct_pattern": "@asynccontextmanager async def lifespan(app: FastAPI): yield",
                "rationale": "FastAPI deprecated on_event handlers in favor of a single lifespan context manager.",
            },
        ),
        verification_commands=(
            "uv run pytest -q",
            "python3 verify_kit.py",
        ),
        positive_sample=(
            "from contextlib import asynccontextmanager\n"
            "from pydantic import BaseModel, ConfigDict, field_validator\n\n"
            "class UserRecord(BaseModel):\n"
            "    model_config = ConfigDict(from_attributes=True)\n"
            "    name: str\n\n"
            "    @field_validator(\"name\", mode=\"after\")\n"
            "    @classmethod\n"
            "    def check_name(cls, v: str) -> str:\n"
            "        return v.strip()\n\n"
            "record = UserRecord.model_validate({\"name\": \"Ada\"})\n"
            "payload = record.model_dump()\n"
        ),
        negative_sample=(
            "from pydantic import BaseModel, validator\n\n"
            "class UserRecord(BaseModel):\n"
            "    name: str\n"
            "    class Config:\n"
            "        orm_mode = True\n"
            "    @validator(\"name\")\n"
            "    def check_name(cls, v):\n"
            "        return v\n\n"
            "payload = UserRecord.parse_obj({\"name\": \"Ada\"}).dict()\n"
        ),
        forbidden_tokens=("@validator(", "@root_validator", ".parse_obj(", ".from_orm(", "orm_mode = True", ".on_event("),
        required_tokens=("ConfigDict", "field_validator", "model_validate", "model_dump"),
    ),
    StarterKitSpec(
        kit_id="typescript-react19-nextjs15-tailwind4",
        title="TypeScript, React 19, Next.js 15 async APIs, and Tailwind v4 starter kit",
        domain="frontend_web",
        description=(
            "Eliminates Next.js 15 synchronous request API calls, React 18 useFormState hooks, "
            "and legacy Tailwind v3 directives in favor of awaited Dynamic APIs, useActionState, and @import tailwindcss."
        ),
        agent_label="Nextjs15 React19 Tailwind4 architect",
        feed_collections=("founder-stack", "developer-releases"),
        linked_linter="nextjs_react19_tailwind4_drift",
        post_cutoff_rules=(
            {
                "rule_id": "nextjs15.async_cookies_headers",
                "wrong_pattern": "const token = cookies().get(\"token\"); const host = headers().get(\"host\");",
                "correct_pattern": "const token = (await cookies()).get(\"token\"); const host = (await headers()).get(\"host\");",
                "rationale": "Next.js 15 made cookies(), headers(), params, and searchParams asynchronous.",
            },
            {
                "rule_id": "react19.use_action_state",
                "wrong_pattern": "import { useFormState } from \"react-dom\";",
                "correct_pattern": "import { useActionState } from \"react\";",
                "rationale": "React 19 replaces react-dom useFormState with useActionState in react.",
            },
            {
                "rule_id": "tailwind4.css_first_import",
                "wrong_pattern": "@tailwind base; @tailwind components; @tailwind utilities;",
                "correct_pattern": "@import \"tailwindcss\";",
                "rationale": "Tailwind CSS v4 uses CSS-first configuration via @import \"tailwindcss\";.",
            },
        ),
        verification_commands=(
            "python3 verify_kit.py",
        ),
        positive_sample=(
            "/* app/globals.css */\n"
            "@import \"tailwindcss\";\n\n"
            "// app/page.tsx\n"
            "import { useActionState } from \"react\";\n"
            "import { cookies, headers } from \"next/headers\";\n\n"
            "export async function readSession() {\n"
            "  const cookieStore = await cookies();\n"
            "  const headerStore = await headers();\n"
            "  return { token: cookieStore.get(\"session\"), ua: headerStore.get(\"user-agent\") };\n"
            "}\n"
        ),
        negative_sample=(
            "@tailwind base;\n"
            "@tailwind utilities;\n"
            "import { useFormState } from \"react-dom\";\n"
            "const token = cookies().get(\"session\");\n"
            "const ua = headers().get(\"user-agent\");\n"
        ),
        forbidden_tokens=("cookies().get", "headers().get", "useFormState", "@tailwind base;"),
        required_tokens=("@import \"tailwindcss\";", "useActionState", "await cookies()", "await headers()"),
    ),
    StarterKitSpec(
        kit_id="mcp-server-authoring-and-security",
        title="Model Context Protocol server authoring and security boundary starter kit",
        domain="protocol_servers",
        description=(
            "Enforces stdio JSON-RPC frame safety, stderr-only logging, shell-free subprocess execution, "
            "environment-sourced credentials, and strict input parameter bounds for MCP tool servers."
        ),
        agent_label="MCP server security reviewer",
        feed_collections=("mcp-services", "security-advisories"),
        linked_linter="mcp_server_safety",
        post_cutoff_rules=(
            {
                "rule_id": "mcp_safety.stdio_stderr_only",
                "wrong_pattern": "print(\"Starting MCP server\")",
                "correct_pattern": "print(\"Starting MCP server\", file=sys.stderr)",
                "rationale": "Stdout carries JSON-RPC 2.0 messages in stdio MCP transport; diagnostic text must use stderr.",
            },
            {
                "rule_id": "mcp_safety.no_shell_true",
                "wrong_pattern": "subprocess.run(cmd, shell=True)",
                "correct_pattern": "subprocess.run([binary, arg], shell=False, check=True, timeout=30)",
                "rationale": "Tool inputs come from untrusted context; shell=True enables command injection.",
            },
            {
                "rule_id": "mcp_safety.input_bounds_and_secrets",
                "wrong_pattern": "api_key = \"sk-live-...\" / def tool_search(query):",
                "correct_pattern": "api_key = os.environ[\"SERVICE_API_KEY\"] / def tool_search(query: str) -> dict:",
                "rationale": "MCP tools must validate parameter lengths and read secrets from environment variables only.",
            },
        ),
        verification_commands=(
            "python3 verify_kit.py",
        ),
        positive_sample=(
            "import os\n"
            "import subprocess\n"
            "import sys\n\n"
            "def tool_inspect_file(relative_path: str) -> dict:\n"
            "    if not isinstance(relative_path, str) or not (1 <= len(relative_path) <= 120) or \"..\" in relative_path:\n"
            "        raise ValueError(\"invalid_relative_path\")\n"
            "    print(\"inspecting path\", file=sys.stderr)\n"
            "    token_present = bool(os.environ.get(\"MCP_SERVICE_TOKEN\"))\n"
            "    proc = subprocess.run([\"stat\", \"-c\", \"%s\", relative_path], shell=False, capture_output=True, text=True, timeout=5)\n"
            "    return {\"ok\": proc.returncode == 0, \"token_configured\": token_present}\n"
        ),
        negative_sample=(
            "import subprocess\n"
            "API_KEY = \"example-placeholder\"\n"
            "def tool_inspect_file(relative_path):\n"
            "    print(\"inspecting\", relative_path)\n"
            "    subprocess.run(\"stat \" + relative_path, shell=True)\n"
        ),
        forbidden_tokens=("shell=True", "os.system(", "sk-live-"),
        required_tokens=("file=sys.stderr", "shell=False", "isinstance("),
    ),
    StarterKitSpec(
        kit_id="llm-sdk-responses-and-model-routing",
        title="LLM SDK Responses API, Messages API, and google-genai routing starter kit",
        domain="model_integration",
        description=(
            "Prevents legacy OpenAI ChatCompletion.create, beta Assistants, Anthropic completions.create, "
            "and deprecated google.generativeai imports while pinning current frontier and fast model identifiers."
        ),
        agent_label="LLM SDK routing engineer",
        feed_collections=("model-releases", "model-cost", "model-switch"),
        linked_linter="llm_sdk_drift",
        post_cutoff_rules=(
            {
                "rule_id": "llm_sdk.openai_responses_api",
                "wrong_pattern": "openai.ChatCompletion.create(...) or client.beta.assistants",
                "correct_pattern": "client = OpenAI(); client.responses.create(model=\"gpt-5-mini\", input=...)",
                "rationale": "OpenAI Responses API unifies chat completions and assistant tool loops.",
            },
            {
                "rule_id": "llm_sdk.anthropic_messages_api",
                "wrong_pattern": "client.completions.create(model=\"claude-2.1\", ...)",
                "correct_pattern": "client.messages.create(model=\"claude-sonnet-4-5\", max_tokens=1024, messages=[...])",
                "rationale": "Anthropic Messages API is required for Claude 4.5 models.",
            },
            {
                "rule_id": "llm_sdk.google_genai_unified",
                "wrong_pattern": "import google.generativeai as genai",
                "correct_pattern": "from google import genai; client = genai.Client()",
                "rationale": "Google replaced google-generativeai with the unified google-genai SDK.",
            },
        ),
        verification_commands=(
            "python3 verify_kit.py",
        ),
        positive_sample=(
            "from openai import OpenAI\n"
            "from anthropic import Anthropic\n"
            "from google import genai\n\n"
            "MODELS = {\n"
            "    \"openai_fast\": \"gpt-5-mini\",\n"
            "    \"anthropic_primary\": \"claude-sonnet-4-5\",\n"
            "    \"google_reasoning\": \"gemini-2.5-pro\",\n"
            "}\n"
        ),
        negative_sample=(
            "import openai\n"
            "import google.generativeai as genai\n"
            "resp = openai.ChatCompletion.create(model=\"gpt-3.5-turbo\", messages=[])\n"
        ),
        forbidden_tokens=("ChatCompletion.create", "client.beta.assistants", "client.completions.create", "import google.generativeai", "gpt-3.5-turbo", "claude-2.1"),
        required_tokens=("gpt-5-mini", "claude-sonnet-4-5", "from google import genai"),
    ),
    StarterKitSpec(
        kit_id="creative-godot4-scene-and-gdscript",
        title="Godot 4.x scene authoring and typed GDScript 2.0 starter kit",
        domain="creative_3d_games",
        description=(
            "Prevents Godot 3 to Godot 4 GDScript drift by enforcing CharacterBody3D/2D, @export and @onready "
            "annotations, Signal.connect callables, and instantiate() on PackedScene resources."
        ),
        agent_label="Godot4 scene and GDScript builder",
        feed_collections=("creative-engines", "creative-mcp-servers"),
        linked_linter="godot4_gdscript_drift",
        post_cutoff_rules=(
            {
                "rule_id": "godot4.annotations",
                "wrong_pattern": "export var speed = 10.0 / onready var sprite = $Sprite",
                "correct_pattern": "@export var speed: float = 10.0 / @onready var sprite: Sprite2D = $Sprite2D",
                "rationale": "GDScript 2.0 in Godot 4 uses @export and @onready annotations and renamed 2D/3D nodes.",
            },
            {
                "rule_id": "godot4.character_body",
                "wrong_pattern": "extends KinematicBody2D / move_and_slide(velocity)",
                "correct_pattern": "extends CharacterBody2D / move_and_slide()",
                "rationale": "Godot 4 replaced KinematicBody2D/3D with CharacterBody2D/3D using the built-in velocity property.",
            },
            {
                "rule_id": "godot4.packed_scene_instantiate",
                "wrong_pattern": "scene.instance()",
                "correct_pattern": "scene.instantiate()",
                "rationale": "PackedScene.instance() was renamed to PackedScene.instantiate() in Godot 4.",
            },
        ),
        verification_commands=(
            "python3 verify_kit.py",
        ),
        positive_sample=(
            "extends CharacterBody3D\n\n"
            "@export var move_speed: float = 6.5\n"
            "@onready var mesh_node: MeshInstance3D = $MeshInstance3D\n\n"
            "func _physics_process(delta: float) -> void:\n"
            "    velocity.x = move_speed\n"
            "    move_and_slide()\n"
        ),
        negative_sample=(
            "extends KinematicBody\n"
            "export var move_speed = 6.5\n"
            "onready var mesh_node = $Spatial\n"
            "func _physics_process(delta):\n"
            "    move_and_slide(velocity)\n"
        ),
        forbidden_tokens=("KinematicBody", "export var ", "onready var ", ".instance()"),
        required_tokens=("CharacterBody3D", "@export", "@onready", "move_and_slide()"),
    ),
    StarterKitSpec(
        kit_id="creative-blender-headless-python",
        title="Blender 4.x headless Python scene and Principled BSDF starter kit",
        domain="creative_3d_rendering",
        description=(
            "Prevents Blender 3.x shader and export API drift in headless bpy scripts by enforcing "
            "Blender 4.x Principled BSDF socket names, EEVEE Next engine identifiers, and glTF 2.0 export checks."
        ),
        agent_label="Blender4 headless Python technical artist",
        feed_collections=("creative-engines", "creative-mcp-servers"),
        linked_linter="blender4_headless_drift",
        post_cutoff_rules=(
            {
                "rule_id": "blender4.principled_bsdf_sockets",
                "wrong_pattern": "bsdf.inputs[\"Specular\"].default_value = 0.5 / bsdf.inputs[\"Transmission\"]",
                "correct_pattern": "bsdf.inputs[\"Specular IOR Level\"].default_value = 0.5 / bsdf.inputs[\"Transmission Weight\"]",
                "rationale": "Blender 4.0 overhauled Principled BSDF socket names (Specular IOR Level, Transmission Weight, Coat Weight).",
            },
            {
                "rule_id": "blender4.eevee_next_engine",
                "wrong_pattern": "scene.render.engine = \"BLENDER_EEVEE\"",
                "correct_pattern": "scene.render.engine = \"BLENDER_EEVEE_NEXT\"  # or \"CYCLES\"",
                "rationale": "Blender 4.2+ replaced legacy BLENDER_EEVEE with BLENDER_EEVEE_NEXT.",
            },
        ),
        verification_commands=(
            "python3 verify_kit.py",
        ),
        positive_sample=(
            "import bpy\n\n"
            "def configure_material(mat):\n"
            "    bsdf = mat.node_tree.nodes.get(\"Principled BSDF\")\n"
            "    bsdf.inputs[\"Base Color\"].default_value = (0.1, 0.4, 0.8, 1.0)\n"
            "    bsdf.inputs[\"Roughness\"].default_value = 0.25\n"
            "    bsdf.inputs[\"Specular IOR Level\"].default_value = 0.5\n"
            "    bsdf.inputs[\"Transmission Weight\"].default_value = 0.0\n"
        ),
        negative_sample=(
            "import bpy\n"
            "def configure_material(mat):\n"
            "    bsdf = mat.node_tree.nodes.get(\"Principled BSDF\")\n"
            "    bsdf.inputs[\"Specular\"].default_value = 0.5\n"
            "    bpy.context.scene.render.engine = \"BLENDER_EEVEE\"\n"
        ),
        forbidden_tokens=("inputs[\"Specular\"]", "inputs['Specular']", "BLENDER_EEVEE\""),
        required_tokens=("Specular IOR Level", "Transmission Weight", "Principled BSDF"),
    ),
    StarterKitSpec(
        kit_id="manim-and-parametric-svg-motion",
        title="Manim Community v0.19+ and parametric SVG motion starter kit",
        domain="creative_motion_graphics",
        description=(
            "Prevents legacy ManimGL / 3b1b syntax drift by enforcing Manim Community Edition Create, "
            "FadeIn, ValueTracker, Axes, and deterministic parametric SVG path generation."
        ),
        agent_label="Manim and parametric SVG motion designer",
        feed_collections=("creative-engines", "research-papers"),
        linked_linter="manim_ce_drift",
        post_cutoff_rules=(
            {
                "rule_id": "manim_ce.import_and_animations",
                "wrong_pattern": "from manimlib.imports import * / ShowCreation(mob)",
                "correct_pattern": "from manim import Scene, Create, FadeIn, Axes, ValueTracker",
                "rationale": "Manim Community Edition uses 'from manim import ...' and replaced ShowCreation with Create.",
            },
            {
                "rule_id": "manim_ce.axes_plot",
                "wrong_pattern": "axes.get_graph(lambda x: x**2)",
                "correct_pattern": "axes.plot(lambda x: x**2)",
                "rationale": "Manim Community replaced axes.get_graph() with axes.plot().",
            },
        ),
        verification_commands=(
            "python3 verify_kit.py",
        ),
        positive_sample=(
            "from manim import Axes, Create, FadeIn, Scene, ValueTracker\n\n"
            "class ParametricWaveScene(Scene):\n"
            "    def construct(self) -> None:\n"
            "        tracker = ValueTracker(1.0)\n"
            "        axes = Axes(x_range=[0, 6, 1], y_range=[-2, 2, 1])\n"
            "        curve = axes.plot(lambda x: x * 0.25)\n"
            "        self.play(Create(axes), Create(curve), FadeIn(tracker))\n"
        ),
        negative_sample=(
            "from manimlib.imports import *\n"
            "class LegacyScene(GraphScene):\n"
            "    def construct(self):\n"
            "        self.play(ShowCreation( self.get_graph(lambda x: x**2) ))\n"
        ),
        forbidden_tokens=("manimlib.imports", "ShowCreation(", ".get_graph(", "GraphScene"),
        required_tokens=("from manim import", "Create(", "axes.plot("),
    ),
    StarterKitSpec(
        kit_id="security-osv-and-supply-chain-watchdog",
        title="OSV vulnerability scanning, CISA KEV, and lockfile supply-chain watchdog starter kit",
        domain="security_supply_chain",
        description=(
            "Enforces pinned dependency digests, OSV batch query verification, CISA KEV cross-checking, "
            "and refusal of unpinned floating tags or install scripts with network side effects."
        ),
        agent_label="Security OSV supply chain watchdog",
        feed_collections=("security-advisories", "developer-releases"),
        linked_linter="supply_chain_safety",
        post_cutoff_rules=(
            {
                "rule_id": "supply_chain.pin_exact_versions",
                "wrong_pattern": "pip install package / FROM python:latest",
                "correct_pattern": "uv run --locked / FROM python@sha256:<64-hex-digest>",
                "rationale": "Floating versions and mutable container tags permit silent upstream compromise.",
            },
            {
                "rule_id": "supply_chain.osv_batch_verification",
                "wrong_pattern": "Unchecked third-party dependency addition",
                "correct_pattern": "Query https://api.osv.dev/v1/querybatch with exact package name, ecosystem, and version",
                "rationale": "Every dependency version must be checked against OSV and CISA KEV advisories before admission.",
            },
        ),
        verification_commands=(
            "python3 verify_kit.py",
        ),
        positive_sample=(
            "DEPENDENCY_LOCK = {\n"
            "    \"ecosystem\": \"PyPI\",\n"
            "    \"package\": \"pydantic\",\n"
            "    \"version\": \"2.10.6\",\n"
            "    \"sha256\": \"a\" * 64,\n"
            "    \"osv_endpoint\": \"https://api.osv.dev/v1/querybatch\",\n"
            "}\n"
        ),
        negative_sample=(
            "DOCKER_BASE = \"FROM python:latest\"\n"
        ),
        forbidden_tokens=(":latest", "| bash", "| sh", "--trusted-host"),
        required_tokens=("sha256", "https://api.osv.dev/v1/querybatch", "version"),
    ),
    StarterKitSpec(
        kit_id="sqlite-duckdb-and-local-first-data",
        title="SQLite WAL mode, parameterized analytical SQL, and local-first data starter kit",
        domain="local_first_data",
        description=(
            "Enforces SQLite WAL concurrency settings, strict foreign keys, bound query parameters, "
            "and deterministic analytical window queries without SQL string concatenation."
        ),
        agent_label="SQLite DuckDB local data engineer",
        feed_collections=("retrieval-benchmarks", "hardware-fit"),
        linked_linter="sqlite_local_data_safety",
        post_cutoff_rules=(
            {
                "rule_id": "sqlite.parameterized_queries_only",
                "wrong_pattern": "cursor.execute(f\"SELECT * FROM users WHERE id = '{user_id}'\")",
                "correct_pattern": "cursor.execute(\"SELECT * FROM users WHERE id = :user_id\", {\"user_id\": user_id})",
                "rationale": "Bound parameters prevent SQL injection and enable SQLite statement caching.",
            },
            {
                "rule_id": "sqlite.wal_and_foreign_keys",
                "wrong_pattern": "Default journal mode without busy_timeout or foreign_keys pragma",
                "correct_pattern": "PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL; PRAGMA foreign_keys=ON; PRAGMA busy_timeout=5000;",
                "rationale": "Local-first SQLite databases need WAL mode, foreign key enforcement, and a bounded busy timeout.",
            },
        ),
        verification_commands=(
            "python3 verify_kit.py",
        ),
        positive_sample=(
            "import sqlite3\n\n"
            "def open_local_db() -> sqlite3.Connection:\n"
            "    conn = sqlite3.connect(\":memory:\")\n"
            "    conn.execute(\"PRAGMA foreign_keys=ON;\")\n"
            "    conn.execute(\"PRAGMA busy_timeout=5000;\")\n"
            "    conn.execute(\"CREATE TABLE items (id INTEGER PRIMARY KEY, score REAL NOT NULL);\")\n"
            "    conn.execute(\"INSERT INTO items (id, score) VALUES (:id, :score)\", {\"id\": 1, \"score\": 9.5})\n"
            "    return conn\n"
        ),
        negative_sample=(
            "import sqlite3\n"
            "def unsafe_query(conn, user_input):\n"
            "    return conn.execute(f\"SELECT * FROM items WHERE id = {user_input}\").fetchall()\n"
        ),
        forbidden_tokens=("execute(f\"", "execute(f'", "PRAGMA foreign_keys=OFF"),
        required_tokens=("PRAGMA foreign_keys=ON", "PRAGMA busy_timeout=5000", ":id"),
    ),
    StarterKitSpec(
        kit_id="overnight-afk-dag-worker-and-verifier",
        title="Overnight AFK DAG worker, budget ceiling, and deterministic verifier starter kit",
        domain="autonomous_workflows",
        description=(
            "Configures bounded overnight task queues with explicit step budgets, immutable checkpoint "
            "records, idempotent effect guards, and mandatory known-wrong verification controls."
        ),
        agent_label="Overnight AFK DAG worker verifier",
        feed_collections=("coding-benchmarks", "coding-agent-releases"),
        linked_linter="overnight_dag_verifier",
        post_cutoff_rules=(
            {
                "rule_id": "overnight.bounded_budget_and_iterations",
                "wrong_pattern": "while True: run_agent_step()",
                "correct_pattern": "Explicit max_iterations, max_elapsed_seconds, and cost_ceiling_usd enforced before every step",
                "rationale": "Overnight runs must halt deterministically before exceeding declared time, token, or cost ceilings.",
            },
            {
                "rule_id": "overnight.known_wrong_control_required",
                "wrong_pattern": "Accepting step output when unit tests exit 0 without negative control verification",
                "correct_pattern": "Verify positive test cases pass AND planted known-wrong control assertions fail",
                "rationale": "A trivial or mocked verifier passes everything unless tested against a known-wrong control.",
            },
        ),
        verification_commands=(
            "python3 verify_kit.py",
        ),
        positive_sample=(
            "RUN_POLICY = {\n"
            "    \"record_type\": \"overnight_dag_policy/v1\",\n"
            "    \"max_iterations\": 25,\n"
            "    \"max_elapsed_seconds\": 3600,\n"
            "    \"require_known_wrong_control\": True,\n"
            "    \"effects_granted\": [],\n"
            "}\n"
        ),
        negative_sample=(
            "while True:\n"
            "    pass  # unbounded loop without max_iterations or known_wrong_control\n"
        ),
        forbidden_tokens=("while True:", "require_known_wrong_control\": False"),
        required_tokens=("max_iterations", "max_elapsed_seconds", "require_known_wrong_control"),
    ),
)

STARTER_KITS_BY_ID: dict[str, StarterKitSpec] = {spec.kit_id: spec for spec in STARTER_KIT_SPECS}


def get_starter_kit_spec(kit_id: str) -> StarterKitSpec:
    """Return the StarterKitSpec for kit_id, or raise KeyError with a clear message."""
    if not isinstance(kit_id, str) or kit_id not in STARTER_KITS_BY_ID:
        raise KeyError(f"unknown_starter_kit: {kit_id!r}")
    return STARTER_KITS_BY_ID[kit_id]


def list_starter_kits() -> list[dict[str, Any]]:
    """Return metadata summaries for all 10 starter kits."""
    return [spec.to_dict() for spec in STARTER_KIT_SPECS]


__all__ = [
    "STARTER_KIT_RECORD_TYPE",
    "SUPPORTED_HARNESSES",
    "HARNESS_CHOICES",
    "StarterKitSpec",
    "STARTER_KIT_SPECS",
    "STARTER_KITS_BY_ID",
    "get_starter_kit_spec",
    "list_starter_kits",
]
