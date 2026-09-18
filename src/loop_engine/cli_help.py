"""Focused public CLI help without importing command implementations.

The root parser retains compatibility flags. This module presents the smaller
command-oriented interface that a new user sees.
"""
from __future__ import annotations


ROOT_HELP = """usage: loop-engine COMMAND [options]

Start here:
  configure       inspect provider keys without calling them
  doctor          check installation and local requirements
  solve           perform and verify a task
  runs            list saved product outcomes
  report          render one saved run
  records         query or revise scoped notes through a typed tool
  studio          inspect results and playback locally

Other commands:
  setup, task, models, extensions, settings, plugin, candidates, templates, profiles, export, evaluate, optimize

Run `loop-engine COMMAND --help` for focused help."""


COMMAND_HELP = {
    "--help": ROOT_HELP, "-h": ROOT_HELP,
    "records": """usage: loop-engine records --policy HOST_POLICY --backend sqlite|package-jsonl --artifact-root PATH [--database PATH | --shard PATH] [--approve-effect-digest DIGEST]

Read one JSON request from stdin: create, get, query, update, or retire. Host configuration fixes storage and scope. Mutations first return an exact effect plan and require matching explicit approval. No raw SQL, direct Markdown edits, or promotion authority.""",
    "configure": """usage: loop-engine configure [--format text|json]

Inspect provider key references and print the exact next probe. No provider is called.""",
    "doctor": """usage: loop-engine doctor [--format text|json]

Check installation, settings, Docker, extensions, and provider references without making a provider call.""",
    "setup": """usage: loop-engine setup [--format text|json]

Run the first-use walkthrough and one deterministic Loop. Provider steps are optional.""",
    "solve": """usage: loop-engine solve (--text TASK | --file PATH) [--quickstart] [--allow-model-failover] [--unattended] [options]

Perform and verify work. Quickstart uses LLM-first reasoning, asks material questions, and applies only explicitly configured numeric limits. Progress traces the exact prompt and model output to stderr by default; --quiet-model-io reduces it to event summaries.""",
    "studio": """usage: loop-engine studio [--runs-dir PATH] [--port PORT]

Open the local read-only interface for results, Loop activity, playback, and model calls.""",
    "runs": """usage: loop-engine runs [--runs-dir PATH] [--format text|json]

List saved runs and their product terminal states.""",
    "report": """usage: loop-engine report [RUN_ID|@last] [--runs-dir PATH] [--format text|markdown|html|json] [--out PATH]

Render one verified saved-run bundle.""",
    "task build": """usage: loop-engine task build (--text TASK | --file PATH) [provider options]

Orient and plan work. This command does not execute the requested product.""",
    "task compile": """usage: loop-engine task compile (--text TASK | --file PATH)

Compile task intake deterministically without solving it.""",
    "models": """usage: loop-engine models {inventory|routes|explain|benchmark|probe} [options]

Inspect routes without calls, or probe one exact route with explicit authority.
Probe flags: --authorize-model-calls --max-model-calls 1
Choose --allow-unbounded-total-tokens explicitly, or a qualified --max-total-tokens policy.""",
    "extensions": """usage: loop-engine extensions {discover|providers|capabilities|intelligence|plugins|skills} [options]

Inspect added files without executing them.""",
    "settings": """usage: loop-engine settings {init|show|check} [--settings-file PATH]

Create or inspect typed runtime settings.""",
    "plugin": """usage: loop-engine plugin {discover|resolve|inspect} [options]

Inspect or resolve passive plugin bundles through existing admission records.""",
    "export": """usage: loop-engine export solution SPEC --out DIR | loop-engine export verify DIR [--run-arguments JSON] [--format text|json]

Write a standalone solution package (source, tests, manifest with digests, Dockerfile, Kubernetes Job) from a JSON export specification, or verify an exported package in an isolated interpreter that cannot import loop_engine. The specification kind text_conformance builds a conformance solution from rules, a policy, and catalog files.""",
    "evaluate": """usage: loop-engine evaluate SUITE --solver-spec SPEC [--out PATH] [--format text|json]

Score a solver on a frozen evaluation suite (evaluation_suite/v1 JSON) with registered deterministic graders. The report carries the exact denominator, attempted, passed, failed, errored, per grader and per tag counts, and every failure. Solver kinds: text_conformance (rules, policy, catalog files, column) and recorded (outputs by case identifier). No model is called.""",
    "optimize": """usage: loop-engine optimize SUITE --solver-spec SPEC --space SPACE [--out PATH] [--format text|json]

Optimize a declared parameter space (axes with finite values, a strategy, a limit, and a holdout fraction) over a frozen suite. Every cell is counted as represented, dispatched, evaluated, and accepted separately; a cell is accepted only when it gains on the training side and does not lose on the held-out side. Sampling is never reported as exhaustive.""",
    "serve": """usage: loop-engine serve api --tenants PATH [--bind ADDRESS] [--port N] | loop-engine --new-tenant ID --tenants PATH

Serve the hosted service surface: GET health, POST conform, POST evaluate, GET usage under /v1. Every request carries the tenant key in the X-Loop-Engine-Key header; the tenants file holds key digests only. Metering records count verified completions, avoided model calls, optimize hours, and judgment depth with digests, never bodies. Minting a tenant prints its key once.""",
    "candidates": """usage: loop-engine candidates {list|review|promote|rollback} [options]

Inspect and govern learning candidates.""",
}


def command_help(argv: list[str]) -> str:
    """Return concise help only when a command help flag was requested."""
    if not argv or not any(value in ("-h", "--help") for value in argv):
        return ""
    grouped = {"task", "models", "extensions", "settings", "plugin",
               "candidates"}
    key = (" ".join(argv[:2]) if argv[0] in grouped and len(argv) > 1
           and not argv[1].startswith("-") else argv[0])
    return COMMAND_HELP.get(key, COMMAND_HELP.get(argv[0], ""))


__all__ = ("COMMAND_HELP", "ROOT_HELP", "command_help")
