"""Check the installed worker and actual fresh native processes without a provider.

The local broker returns declared fixture answers. This qualifies package,
launch, isolation and packet handling, not model quality or customer outcomes.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

IMAGE_PROFILE = ("--read-only", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
                 "--network", "none", "--tmpfs", "/tmp:rw,nosuid,size=512m", "--memory", "1g", "--pids-limit", "256")
PROFILE_ROOT = Path("/opt/baltor")
RESULT_RECORD = "baltor_worker_bundle_checks/v1"


def inside():
    from loop_engine.core.harness_process import HarnessProcessRequest, HarnessProcessSpec, run_harness_process
    from loop_engine.core.harness_recipe_catalog_checks import self_test as recipe_checks

    checks = []
    def check(name, passed, detail=""):
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    version = subprocess.run(["opencode", "--version"], text=True, capture_output=True, timeout=20, check=True)
    check("pinned_opencode_is_installed", version.stdout.strip() == "1.17.9", version.stdout.strip())
    release = recipe_checks()
    check("installed_recipe_contracts_and_module_digests_pass", release["all_passed"],
          str(release["passed"]) + "/" + str(release["total"]))
    for style in ("baltor", "opencode"):
        configuration = json.loads((PROFILE_ROOT / (style + "-harness.json")).read_text())
        try:
            spec = HarnessProcessSpec(configuration["harness_id"], configuration["package_version"],
                                      tuple(configuration["command_prefix"]), tuple(configuration["read_only_paths"]),
                                      configuration["style"], process_isolation=configuration["process_isolation"])
            identities, requests = [], []
            with tempfile.TemporaryDirectory(prefix="worker-native-") as temporary:
                root = Path(temporary)
                (root / "work").mkdir()
                (root / "AGENTS.md").write_text("WORKER_PARENT_CONTEXT_MUST_NOT_LOAD")
                for number in (1, 2):
                    marker = "WORKER_STEP_" + str(number) + "_ONLY"
                    prompt = "Return one short answer for this isolated assignment. " + marker
                    expected = "fixture answer " + str(number)
                    received = []

                    def broker(body, expected=expected):
                        received.append(body)
                        return {"id": "worker-fixture", "object": "chat.completion", "model": "fixture-model",
                                "choices": [{"index": 0, "message": {"role": "assistant", "content": expected},
                                             "finish_reason": "stop"}],
                                "usage": {"prompt_tokens": 12, "completion_tokens": 3, "total_tokens": 15}}

                    request = HarnessProcessRequest(spec, prompt, "fixture-model", 256, 128, 45,
                                                    str(root / "work"), socket_directory="/tmp", context_capacity=65536)
                    result = run_harness_process(request, broker)
                    identities.append(result.process_identity)
                    text = json.dumps(received)
                    check(style + "_step_" + str(number) + "_native_turn_returns_exact_broker_text",
                          result.ok and result.output == expected and len(received) == 1,
                          "errors=" + str(result.errors) + " stderr=" + result.stderr[-300:])
                    check(style + "_step_" + str(number) + "_loads_only_its_assignment",
                          marker in text and "WORKER_PARENT_CONTEXT_MUST_NOT_LOAD" not in text
                          and "WORKER_STEP_" + str(3-number) + "_ONLY" not in text)
                    requests.extend(received)
            check(style + "_starts_distinct_process_instances", len(set(identities)) == 2)
        except (OSError, RuntimeError, ValueError) as error:
            check(style + "_native_profile_available", False, str(error)[:400])
    return {"record_type": RESULT_RECORD, "total": len(checks), "passed": sum(row["passed"] for row in checks),
            "all_passed": all(row["passed"] for row in checks), "external_provider_calls": 0,
            "scope": "Installed software and two fresh text-only native turns per adapter, using a local fixture broker",
            "image_security_profile": list(IMAGE_PROFILE), "checks": checks}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--inside", action="store_true")
    parser.add_argument("--image")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if args.inside:
        record = inside()
    else:
        if not args.image or not args.output or args.output.exists() or not args.output.parent.is_dir():
            parser.error("an image and a new report path with an existing parent are required")
        script = Path(__file__).resolve()
        command = ["docker", "run", "--rm", *IMAGE_PROFILE, "--mount",
                   "type=bind,src=" + str(script) + ",dst=/opt/baltor/worker-check.py,readonly",
                   "--entrypoint", "python", args.image, "/opt/baltor/worker-check.py", "--inside"]
        result = subprocess.run(command, capture_output=True, text=True, timeout=180)
        try:
            record = json.loads(result.stdout)
        except ValueError:
            record = {"record_type": RESULT_RECORD, "all_passed": False, "external_provider_calls": 0,
                      "error": "worker check did not return JSON", "exit_code": result.returncode,
                      "diagnostic": result.stderr[-1000:]}
        with args.output.open("x") as stream:
            stream.write(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2))
    return 0 if record.get("all_passed") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
