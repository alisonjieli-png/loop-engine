"""Run bounded daily ideation, interrogation and native candidate preparation.

No approval, social posting, generated-code execution or publication occurs.
The existing community watcher supplies leads; the existing native factory
prepares complete packages for independent review.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for directory in (ROOT / "src", ROOT / "tools", ROOT):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

from knowledge_radar.expansion import ExpansionRequest, run


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library", type=Path, required=True)
    parser.add_argument("--maximum-work", type=int, default=8)
    parser.add_argument("--candidate-store", type=Path, help="Existing import/supply store for read-only reuse search.")
    parser.add_argument("--authorize-local-writes", action="store_true")
    parser.add_argument("--authorize-model-calls", action="store_true")
    args = parser.parse_args(argv)
    os.umask(0o077)
    result = run(ExpansionRequest(ROOT, args.library, args.maximum_work,
                                 args.authorize_local_writes, args.authorize_model_calls, args.candidate_store))
    print(json.dumps(result, indent=2))
    return 1 if result.get("status") == "accounting_blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
