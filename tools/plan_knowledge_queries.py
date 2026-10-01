"""Bounded query planning/reads over the existing knowledge radar; no model calls."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for entry in (ROOT / "src", ROOT / "tools", ROOT):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from knowledge_radar.query_matrix import default_matrix, read_matrix  # noqa: E402
from knowledge_radar.query_runs import tick  # noqa: E402
from knowledge_radar.records import read_contracts  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", required=True, type=Path, help="Existing private CommunityStore root, or a new private test root.")
    parser.add_argument("--matrix", type=Path, help="Explicit knowledge_radar_query_matrix/v1; default reuses existing idea/expansion vocabularies.")
    parser.add_argument("--country-inventory", type=Path, help="Versioned source-bound M49 inventory; replaces the explicitly limited pilot countries.")
    parser.add_argument("--page-size", type=int, default=10)
    parser.add_argument("--scan-limit", type=int, default=1000)
    parser.add_argument("--maximum-queries", type=int, default=5)
    parser.add_argument("--maximum-requests", type=int, default=5)
    parser.add_argument("--per-source", type=int, default=5)
    parser.add_argument("--authorize-local-writes", action="store_true")
    parser.add_argument("--authorize-network-reads", action="store_true", help="Authorize sending public, non-confidential query vocabulary only; heuristic input checks cannot infer confidentiality.")
    parser.add_argument("--execute-queued", action="store_true")
    options = parser.parse_args(argv)
    try:
        if options.matrix and options.matrix.stat().st_size > 512 * 1024:
            raise ValueError("matrix_bytes")
        if options.country_inventory and options.country_inventory.stat().st_size > 512 * 1024:
            raise ValueError("country_inventory_bytes")
        if options.matrix and options.country_inventory:
            raise ValueError("country_inventory_requires_default_matrix")
        countries = json.loads(options.country_inventory.read_bytes()) if options.country_inventory else None
        value = json.loads(options.matrix.read_bytes()) if options.matrix else default_matrix(ROOT, countries)
        contracts = read_contracts(json.loads((ROOT / "tools/knowledge_radar/source-contracts-v1.json").read_bytes()))
        matrix = read_matrix(value, contracts)
        result = tick(matrix, ROOT, options.state, writes_allowed=options.authorize_local_writes,
                      network_allowed=options.authorize_network_reads, execute=options.execute_queued,
                      page_size=options.page_size, scan_limit=options.scan_limit,
                      maximum_queries=options.maximum_queries, maximum_requests=options.maximum_requests,
                      per_source=options.per_source)
        print(json.dumps(result, sort_keys=True, ensure_ascii=False))
        return 0
    except (ValueError, PermissionError, OSError) as error:
        # A parser/type refusal has no raw source, credential or file body in diagnostics.
        print(json.dumps({"status": "refused", "error_class": type(error).__name__}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
