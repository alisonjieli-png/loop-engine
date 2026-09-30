"""Prepare original parametric reference candidates through the existing native factory."""
from __future__ import annotations

import argparse
from pathlib import Path

from tools.build_creative_components import build
from tools.procedural_assets.packaging import proposals


def main(argv=None):
    # Share the committed-source and confined-output preparation contract; no new admission path.
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--run-folder", type=Path, required=True)
    parser.add_argument("--authorize-preparation", action="store_true")
    args = parser.parse_args(argv)
    import json
    result = build(args.repository, args.run_folder, authorized=args.authorize_preparation, proposal_factory=proposals)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
