"""Run seven bounded source mutants in temporary copies, with a clean baseline."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
MUTANTS = (
    ("stale_binding_before_write", "if expected != actual:", "if False:"),
    ("externally_bound_payload_digest",
     'if total > MAX_BYTES or digest(canonical(rows).encode()) != expected["packet_content_sha256"]:',
     "if total > MAX_BYTES:"),
    ("first_actions_nonempty", "if not isinstance(value, list) or not 1 <= len(value) <= 20:",
     "if not isinstance(value, list) or len(value) > 20:"),
    ("native_style_allowlist", "if assignment.harness_style not in NATIVE_STYLES:", "if False:"),
    ("ancestor_symlink_refusal", "if part.is_symlink():", "if False:"),
    ("strict_integer_version", "if type(value) is not int or value < 1:",
     "if not isinstance(value, int) or value < 1:"),
    ("brief_secret_scan", "if any(re.search(pattern, text) for pattern in default_secret_patterns()):",
     "if False:"),
)


def main():
    source = (ROOT / "render_packet.py").read_text()
    tests = ROOT / "test_render_packet.py"
    environment = dict(os.environ, PYTHONPATH=str(REPO / "src"))
    results = []
    for name, old, new in (("unmodified", "", ""), *MUTANTS):
        if old and source.count(old) != 1:
            raise SystemExit("source changed; revise the explicit mutant before running it")
        with tempfile.TemporaryDirectory(prefix="baltor-packet-mutant-") as tmp:
            scratch = Path(tmp)
            shutil.copyfile(tests, scratch / tests.name)
            (scratch / "render_packet.py").write_text(source if not old else source.replace(old, new))
            run = subprocess.run(
                [sys.executable, "-m", "unittest", "discover", "-s", tmp, "-p", tests.name],
                cwd=tmp, env=environment, capture_output=True, text=True, timeout=30, check=False)
            results.append({"case": name, "exit_code": run.returncode,
                            "result_tail": run.stderr.splitlines()[-5:]})
            if name == "unmodified" and run.returncode:
                raise SystemExit("baseline failed; no mutant conclusion is valid")
    record = {"record_type": "focused_step_removed_guard_checks/v1",
              "renderer_sha256": hashlib.sha256(source.encode()).hexdigest(),
              "tests_sha256": hashlib.sha256(tests.read_bytes()).hexdigest(), "cases": results,
              "all_seven_mutants_detected": all(row["exit_code"] != 0 for row in results[1:])}
    target = ROOT / ("removed-guard-checks-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + ".json")
    with target.open("x") as stream:
        json.dump(record, stream, indent=2)
        stream.write("\n")
    print(target)
    if not record["all_seven_mutants_detected"]:
        raise SystemExit("a source mutant survived; keep the report and repair the check")


if __name__ == "__main__":
    main()
