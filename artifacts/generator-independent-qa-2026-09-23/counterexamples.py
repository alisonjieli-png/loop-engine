"""Independent read-only review of generator/provider source using marked fixtures."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

SOURCE = Path("/home/username/.le-codex-build/native-generation")
sys.path.insert(0, str(SOURCE))
sys.path.insert(0, str(SOURCE / "src"))
from tools.test_generate_original_native_candidates import GenerationTest, FakeGateway
from tools.test_provider_model_identity_reporting import Response, CAPACITY, MODEL
from loop_engine.core import ollama_client

HERE = Path(__file__).resolve().parent


def fixture():
    result = GenerationTest("test_native_tree_prepared_with_controller_digests_and_no_approval")
    result.setUp()
    return result


def main():
    rows = []
    context = fixture()
    try:
        gateway = FakeGateway()
        context.run_generation(gateway)
        items_path = context.root / "run/inspect_fixture.attempt-1/candidates/items.json"
        items = json.loads(items_path.read_text())
        items["items"][0]["producer"]["family"] = "different_family"
        items["items"][0]["reference"]["declared_effects"] = ["network"]
        items_path.write_text(json.dumps(items))
        try:
            result = context.run_generation(gateway)
            refusal = None
        except ValueError as error:
            result, refusal = None, str(error)
        rows.append({"case": "resume_changed_producer_and_effect_metadata", "expected": "refusal before any call",
                     "refusal": refusal, "candidate_count": result["candidate_count"] if result else None,
                     "model_fixture_calls": len(gateway.calls), "defect_reproduced": result is not None})
    finally:
        context.doCleanups()
    context = fixture()
    try:
        gateway = FakeGateway()
        context.run_generation(gateway)
        proposal_path = context.root / "run/inspect_fixture.attempt-1/proposals.json"
        proposal_path.write_text(proposal_path.read_text() + " ")
        try:
            context.run_generation(gateway)
            refusal = None
        except ValueError as error:
            refusal = str(error)
        rows.append({"case": "resume_changed_proposal_positive_guard", "refusal": refusal,
                     "model_fixture_calls": len(gateway.calls), "passed": refusal == "saved_proposal_changed"})
    finally:
        context.doCleanups()
    data = {"model": MODEL, "error": "temporarily unavailable", "message": {"content": ""},
            "prompt_eval_count": 11, "eval_count": 7, "done": True}
    with patch.object(ollama_client.urllib.request, "urlopen", return_value=Response(data)):
        answer = ollama_client.chat("fixture", model=MODEL, api_key="fixture-only", output_capability=CAPACITY)
    rows.append({"case": "provider_error_body_keeps_reported_usage", "expected_input_tokens": 11,
                 "expected_output_tokens": 7, "actual_input_tokens": answer.prompt_tokens,
                 "actual_output_tokens": answer.eval_tokens, "ok": answer.ok,
                 "defect_reproduced": (answer.prompt_tokens, answer.eval_tokens) != (11, 7)})
    data = {"error": "temporarily unavailable", "message": {"content": ""},
            "prompt_eval_count": 11, "eval_count": 7, "done": True}
    with patch.object(ollama_client.urllib.request, "urlopen", return_value=Response(data)):
        answer = ollama_client.chat("fixture", model=MODEL, api_key="fixture-only", output_capability=CAPACITY)
    rows.append({"case": "provider_error_body_without_identity_stays_unknown", "model": answer.model,
                 "ok": answer.ok, "passed": answer.model == "" and answer.ok is False})
    report = {"record_type": "original_generation_independent_qa/v1", "checks": rows,
              "source_sha256": {str(p): hashlib.sha256((SOURCE / p).read_bytes()).hexdigest() for p in
                  (Path("tools/generate_original_native_candidates.py"), Path("src/loop_engine/core/ollama_client.py"),
                   Path("src/loop_engine/core/model_gateway.py"))}, "provider_calls": 0, "approvals": 0}
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "counterexamples-initial.json"
    with path.open("x") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
