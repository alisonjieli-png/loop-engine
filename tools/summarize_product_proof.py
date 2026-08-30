"""Create compact, secret-safe product evidence from full acceptance runs."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def _compact(value: dict) -> dict:
    providers = sorted({row.get("provider", "")
                        for row in value.get("model_usage", ()) if row.get("provider")})
    models = sorted({row.get("model", "")
                     for row in value.get("model_usage", ()) if row.get("model")})
    result = value.get("result") or {}
    commands = result.get("commands") or []
    return {
        "record_type": "product_task_evidence/v1",
        "original_task": value["compiled_task"]["original_input"],
        "terminal_code": value["terminal_code"],
        "summary": value["summary"], "run_id": value["run_id"],
        "providers": providers, "models": models,
        "loop_count": value["loop_count"],
        "model_call_count": value["model_calls"],
        "tool_call_count": value["tool_calls"],
        "workspace": value["workspace"],
        "artifacts": [{
            key: item.get(key) for key in (
                "path", "media_type", "byte_count", "digest", "verified",
                "verification_method")}
            for item in value.get("artifacts", ())],
        "verification": value["verification"],
        "graph_digest": value["graph_digest"],
        "manifest_digest": result.get("manifest_digest", ""),
        "run_history": value["run_history"],
        "elapsed_seconds": value["elapsed_seconds"],
        "limitations": value["limitations"],
        "command_results": [{
            key: item.get(key) for key in (
                "purpose", "command_kind", "expected_exit_codes", "exit_code",
                "expectation_met", "stdout", "stderr")}
            for item in commands],
        "assurance": value.get("assurance_profile", {}),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--acceptance-root", type=Path, required=True)
    parser.add_argument("--cli-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    output = args.output_root.resolve()
    output.mkdir(parents=True, exist_ok=True)
    names = {
        "task-a.json": "task-a.json", "task-b.json": "task-b.json",
        "task-c.json": "task-c.json", "task-d.json": "task-d-repair.json"}
    for source_name, target_name in names.items():
        value = json.loads((args.acceptance_root / source_name).read_text())
        (output / target_name).write_text(
            json.dumps(_compact(value), indent=2) + "\n")
    cli_text = json.loads((args.cli_root / "cli-acceptance.json").read_text())
    cli_file = json.loads((args.cli_root / "cli-file-acceptance.json").read_text())
    (output / "readme-quickstart.json").write_text(json.dumps({
        "record_type": "readme_quickstart_evidence/v1",
        "text_task": _compact(cli_text), "file_task": _compact(cli_file),
        "external_provider_proven": False,
        "limitations": [
            "CLI semantics used a local HTTP contract fixture.",
            "The authorized Ollama Cloud smoke was rate limited."],
    }, indent=2) + "\n")
    print(json.dumps({
        "record_type": "product_proof_export/v1",
        "files": sorted(names.values()) + ["readme-quickstart.json"]},
        indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
