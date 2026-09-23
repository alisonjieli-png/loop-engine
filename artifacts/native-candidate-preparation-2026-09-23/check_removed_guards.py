"""Run each discriminating check against a disposable native-preparer guard removal."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "tools/native_harness_candidates.py"
CASES = (
    ("payload_digest", "if len(body) != entry.size_bytes or hashlib.sha256(body).hexdigest() != entry.digest:",
     "if False:", "test_corrupt_payload_digest_refuses_before_output"),
    ("executable_effect", "if package.executable and EXECUTABLE_EFFECT not in effects:",
     "if False:", "test_executable_effect_cannot_be_omitted"),
    ("duplicate_package", "if package.package_digest in digests:",
     "if False:", "test_duplicate_package_under_new_identity_refuses_inflated_count"),
    ("full_inventory", "if found != expected:", "if False:",
     "test_staging_rechecks_changed_missing_and_extra_files"),
    ("canonical_document", "if body.stat().st_size != len(package.document()) or body.read_bytes() != package.document():",
     "if False:", "test_staging_rejects_forged_manifest_body_and_producer"),
    ("closed_effects", 'if any(effect not in EFFECTS for effect in effects) or ("pure" in effects and len(effects) > 1):',
     "if False:", "test_producer_method_is_required_and_staging_refuses_unknown_effect"),
)
WORKER = """
import importlib.util,sys,unittest
from pathlib import Path
root,mutant,method=sys.argv[1:]
sys.path.insert(0,root)
import tools.prepare_harness_candidates
spec=importlib.util.spec_from_file_location('tools.native_harness_candidates',mutant)
module=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=module
spec.loader.exec_module(module)
suite=unittest.defaultTestLoader.loadTestsFromName('tools.test_prepare_native_harness_candidates.NativeCandidatePreparerChecks.'+method)
result=unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
"""


def main():
    target = Path(sys.argv[1])
    if target.exists():
        raise ValueError("Use a new report path")
    text = SOURCE.read_text()
    output = []
    with tempfile.TemporaryDirectory(prefix="native-package-mutants-") as directory:
        for name, before, after, method in CASES:
            if text.count(before) != 1:
                raise ValueError("Mutation anchor must be exact and unique")
            baseline = subprocess.run([sys.executable, "-c", WORKER, str(ROOT), str(SOURCE), method],
                env={"PATH": os.environ["PATH"], "PYTHONPATH": str(ROOT / "src")},
                capture_output=True, text=True, check=False, timeout=30)
            path = Path(directory) / (name + ".py")
            path.write_text(text.replace(before, after, 1))
            result = subprocess.run([sys.executable, "-c", WORKER, str(ROOT), str(path), method],
                env={"PATH": os.environ["PATH"], "PYTHONPATH": str(ROOT / "src")},
                capture_output=True, text=True, check=False, timeout=30)
            output.append({"guard": name, "check": method, "baseline_exit": baseline.returncode,
                "mutant_exit": result.returncode, "detected": baseline.returncode == 0 and result.returncode != 0,
                "baseline_output": baseline.stdout + baseline.stderr,
                "mutant_output": result.stdout + result.stderr})
    target.write_text(json.dumps({"checks": output, "passed": all(row["detected"] for row in output)}, indent=2) + "\n")
    return 0 if all(row["detected"] for row in output) else 1


if __name__ == "__main__":
    raise SystemExit(main())
