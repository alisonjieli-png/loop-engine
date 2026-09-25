"""One small recorded call that says whether a reviewer installation can serve reviews now.

Written first for the Ollama Cloud allowance; the same probe serves the provider binding engine (the Tactical
endpoint), whose committed binding and operator credential reference it resolves inside this process only.

The call goes through the review panel's own ``model_gateway`` engine for one
declared installation, so it uses the same route policy, credential variable
and output allocation rules as a review. It sends one short prompt with no
candidate material. The record names the model, the reported model, the
usage exactly as reported, the outcome and the time. A spent allowance is the
outcome ``usage_limit_reached``; the panel then stops every installation that
shares the allowance, as it always does.

    PYTHONPATH=src:tools python artifacts/review-throughput-2026-09-24/probe_ollama_allowance.py \\
        --installation ollama.gpt-oss-120b --output artifacts/review-throughput-2026-09-24/probes/NAME.json
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
#: The checkout whose review panel is probed: the one holding this file, unless --repository names one.
ROOT = Path(sys.argv[sys.argv.index("--repository") + 1]).resolve() if "--repository" in sys.argv \
    else HERE.parents[1]
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "src"), str(ROOT)]

from candidate_review import configuration as config  # noqa: E402
from candidate_review import engines  # noqa: E402
from candidate_review.records import digest  # noqa: E402
from candidate_review.reviewers import CallAllowance, ReviewerContext, ReviewPrompt  # noqa: E402
from candidate_review.reviewers.gateway import listed_model_versions  # noqa: E402

RECORD_TYPE = "review_allowance_probe/v1"
SYSTEM = "You answer with one word."
USER = "Reply with the single word READY."


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repository", type=Path, default=ROOT, help="The checkout whose panel is probed.")
    parser.add_argument("--installation", required=True)
    parser.add_argument("--output-tokens", type=int, default=512)
    parser.add_argument("--output", type=Path, required=True)
    options = parser.parse_args(argv)
    panel = config.PanelConfiguration.from_dict(json.loads(
        (ROOT / "tools/candidate_review/resources/panel.json").read_text(encoding="utf-8")))
    installation = panel.installation(options.installation)
    started = datetime.now(timezone.utc)
    listing = listed_model_versions()
    from tools import operator_credentials
    engine = engines.build_reviewer(installation, panel.policy, ReviewerContext(
        model_listing=listing["models"] if listing["ok"] else None, repository=ROOT,
        credential_resolver=operator_credentials.resolve))
    availability = engine.availability()
    record = {"record_type": RECORD_TYPE, "started_at": started.isoformat().replace("+00:00", "Z"),
              "installation_id": installation.installation_id, "installation_sha256": installation.sha256,
              "family": installation.family, "model": installation.model, "quota_group": installation.quota_group,
              "listing": {"ok": listing["ok"], "http_status": listing["http_status"], "error": listing["error"],
                          "models_listed": len(listing["models"]),
                          "model_version": listing["models"].get(installation.model)},
              "available": availability.available, "availability_reason": availability.reason,
              "prompt_sha256": digest({"system": SYSTEM, "user": USER}), "call": None}
    if availability.available:
        attempt = engine.review(ReviewPrompt(SYSTEM, USER, digest({"system": SYSTEM, "user": USER}), 16),
                                CallAllowance(options.output_tokens, 120.0, 0.0))
        record["call"] = {"outcome": attempt.outcome, "reported_model": attempt.reported_model,
                          "answer": attempt.text[:40], "usage": attempt.usage.to_dict(),
                          "physical_model_calls": attempt.physical_model_calls,
                          "elapsed_seconds": attempt.elapsed_seconds, "error_detail": attempt.error_detail,
                          "retry_after_seconds": attempt.retry_after_seconds}
    record["allowance"] = ("spent" if record["call"] and record["call"]["outcome"] == "usage_limit_reached"
                           else "serving" if record["call"] and record["call"]["outcome"] == "answered"
                           else "unknown")
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.output.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"allowance": record["allowance"], "outcome": (record["call"] or {}).get("outcome"),
                      "available": record["available"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
