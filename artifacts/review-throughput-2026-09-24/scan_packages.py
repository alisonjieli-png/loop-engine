"""Run NVIDIA SkillSpector in static mode over every package of a native candidate catalogue.

The Community tier needs every automated check, the safety scanners included.
This runs the review panel's own SkillSpector engine rules (the committed
``skillspector_static`` settings: static mode, no model, refuse at HIGH or
above, a partial scan tolerated only for a missing reference) on each exact
package tree, copied to a temporary folder so the scanner writes nothing
beside the candidates. It records, per package digest, the scanner's version,
whether it refused and the findings' rule names; it never copies text from a
finding.

    python artifacts/review-throughput-2026-09-24/scan_packages.py --catalogue CANDIDATES \\
        --program PATH/TO/skillspector --output SCAN.json --workers 8
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "src"), str(ROOT)]

from candidate_review.prechecks.skillspector import SkillSpectorStatic  # noqa: E402

RECORD_TYPE = "package_safety_scan/v1"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--catalogue", type=Path, required=True)
    parser.add_argument("--program", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=8)
    options = parser.parse_args(argv)
    panel = json.loads((ROOT / "tools/candidate_review/resources/panel.json").read_text())
    settings = dict(panel["precheck_engines"]["skillspector_static"], program=str(options.program))
    engine = SkillSpectorStatic(settings, None)
    version = engine.availability()
    items = json.loads((options.catalogue / "items.json").read_text())["items"]
    previous = json.loads(options.output.read_text())["packages"] if options.output.exists() else {}

    def scan(row):
        digest = row["reference"]["digest"]
        if digest in previous:
            return digest, previous[digest]
        with tempfile.TemporaryDirectory(prefix="package-scan-") as directory:
            tree = Path(directory) / "package"
            shutil.copytree(options.catalogue / row["package_root"], tree)
            report_path = Path(directory) / "report.json"
            try:
                finished = engine.program.run({"{skill_folder}": str(tree), "{report_path}": str(report_path)},
                                              Path(directory))
                report = json.loads(report_path.read_text())
                refusals, notes = engine._findings(report, finished.returncode)
            except subprocess.TimeoutExpired:
                refusals, notes = [("skillspector_incomplete", "the scan did not finish in time")], []
            except (OSError, ValueError):
                refusals, notes = [("skillspector_incomplete", "no readable report")], []
        return digest, {"identity": row["reference"]["identity"], "refused": bool(refusals),
                        "refusals": [code for code, _detail in refusals],
                        "notes": [detail for _code, detail in notes]}

    with ThreadPoolExecutor(max_workers=options.workers) as pool:
        results = dict(pool.map(scan, items))
    record = {"record_type": RECORD_TYPE, "catalogue": str(options.catalogue), "engine": "skillspector_static",
              "engine_version": version[2], "settings": {key: settings[key] for key in (
                  "arguments", "refuse_at_or_above", "tolerated_partial_reasons")},
              "packages": results, "scanned": len(results),
              "refused": sum(1 for value in results.values() if value["refused"])}
    options.output.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"scanned": record["scanned"], "refused": record["refused"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
