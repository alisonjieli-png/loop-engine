"""Admit generated library components by independent qualification and sampled model review.

    PYTHONPATH=src:tools python tools/qualify_generated_components.py self-test --output SELF-TEST.json
    PYTHONPATH=src:tools python tools/qualify_generated_components.py qualify --store-root STORE \\
        --output-folder RUN [--line LINE] [--limit N] [--workers N] [--engine bwrap_rlimits] [--known-bundle B]
    PYTHONPATH=src:tools python tools/qualify_generated_components.py sample-review --qualification RUN \\
        --store-root STORE --ledger LEDGER --output REVIEW.json [--authorize-model-calls --call-ceiling N]
    PYTHONPATH=src:tools python tools/qualify_generated_components.py admit --qualification RUN \\
        --review REVIEW.json --store-root STORE --output FOLDER --recorded-at DATE

Qualification is deterministic and makes no model call. The sampled review asks one calibrated reviewer
from a family other than the producer's about a random sample of each generator batch; model calls need
--authorize-model-calls and stay within the declared ceilings, every call written to the review ledger.
Admission writes the qualified components of accepted batches as a reviewed folder the existing combine
and bundle tools read. See tools/component_qualification/README.md.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if __name__ == "__main__":
    sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "tools")]

from tools.component_qualification import checks, controls, qualify  # noqa: E402
from tools.component_qualification.components import StoreReader  # noqa: E402
from tools.component_qualification.sandbox import ENGINES, SandboxSettings  # noqa: E402


def _sandbox(options) -> SandboxSettings:
    return SandboxSettings(engine=options.engine, python=options.python)


def _known_digests(bundle: "Path | None") -> dict:
    """Served package digests of a release bundle, so a copy of a served component is refused."""
    if bundle is None:
        return {}
    known = {}
    with open(Path(bundle) / "items.jsonl", encoding="utf-8") as stream:
        for line in stream:
            reference = json.loads(line).get("reference") or {}
            if reference.get("digest"):
                known[reference["digest"]] = reference.get("identity", "served")
    return known


def command_self_test(options) -> dict:
    context = checks.QualificationContext.load(ROOT, sandbox_settings=_sandbox(options), work_root=options.work_root)
    record = controls.self_test(context, qualify.code_revision(ROOT))
    options.output.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n")
    return {"passed": record["passed"], "known_wrong_controls": len(record["known_wrong"]),
            "known_good_rows": len(record["known_good"]), "sha256": record["sha256"]}


def command_qualify(options) -> dict:
    reader = StoreReader(options.store_root)
    try:
        rows = reader.rows(lines=tuple(options.line), limit=options.limit)
    finally:
        reader.close()
    folder = options.output_folder
    folder.mkdir(parents=True, exist_ok=True)

    def progress(done, total, seconds):
        print(json.dumps({"progress": done, "of": total, "seconds": round(seconds, 1)}), flush=True)

    summary = qualify.qualify_rows(rows, repository=ROOT, store_root=options.store_root,
                                   sandbox_settings=_sandbox(options), work_root=options.work_root,
                                   workers=options.workers, known_digests=_known_digests(options.known_bundle),
                                   output=folder / "qualification.jsonl", progress=progress)
    (folder / "run.json").write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n")
    return {key: summary[key] for key in ("components", "qualified", "refused", "unreadable", "seconds",
                                          "throughput")}


def command_sample_review(options) -> dict:
    from tools.component_qualification import sampled_review
    return sampled_review.command(options, ROOT)


def command_admit(options) -> dict:
    from tools.component_qualification import admission
    return admission.command(options, ROOT)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("self-test", "qualify"):
        command = commands.add_parser(name)
        command.add_argument("--engine", choices=ENGINES, default="bwrap_rlimits")
        command.add_argument("--python", default="/usr/bin/python3", help="The interpreter inside the sandbox.")
        command.add_argument("--work-root", type=Path, required=True,
                             help="Where each package is written for its sandbox run; emptied after each run.")
        if name == "self-test":
            command.add_argument("--output", type=Path, required=True)
        else:
            command.add_argument("--store-root", type=Path, required=True)
            command.add_argument("--output-folder", type=Path, required=True)
            command.add_argument("--line", action="append", default=[])
            command.add_argument("--limit", type=int)
            command.add_argument("--workers", type=int, default=qualify.default_workers())
            command.add_argument("--known-bundle", type=Path,
                                 help="A release bundle whose served digests count as existing components.")
    review = commands.add_parser("sample-review")
    review.add_argument("--qualification", type=Path, required=True, help="A qualify run folder.")
    review.add_argument("--store-root", type=Path, required=True)
    review.add_argument("--ledger", type=Path, required=True)
    review.add_argument("--output", type=Path, required=True)
    review.add_argument("--history", type=Path, help="Earlier batch decisions (JSON lines), for observed rates.")
    review.add_argument("--reviewer", default="tactical.gemma-4-coding-abliterated")
    review.add_argument("--producer-family", default="anthropic",
                        help="The family whose model wrote the generators (they call no model themselves).")
    review.add_argument("--batch", action="append", default=[], help="Only these generator batches.")
    review.add_argument("--controls-per-call", type=int, default=1)
    review.add_argument("--call-ceiling", type=int, default=0)
    review.add_argument("--token-ceiling", type=int, default=0)
    review.add_argument("--calibrate", action="store_true",
                        help="First ask the reviewer about the frozen native controls, one at a time.")
    review.add_argument("--authorize-model-calls", action="store_true")
    review.add_argument("--seed", help="The sample seed; a fresh random seed when omitted (recorded either way).")
    admit = commands.add_parser("admit")
    admit.add_argument("--qualification", type=Path, required=True)
    admit.add_argument("--review", type=Path, required=True)
    admit.add_argument("--store-root", type=Path, required=True)
    admit.add_argument("--output", type=Path, required=True)
    admit.add_argument("--recorded-at", required=True)
    options = parser.parse_args(argv)
    handler = {"self-test": command_self_test, "qualify": command_qualify, "sample-review": command_sample_review,
               "admit": command_admit}[options.command]
    print(json.dumps(handler(options), sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
