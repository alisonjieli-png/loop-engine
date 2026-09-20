"""Reproduce in-flight metadata revocation with an actual loopback request.

Only temporary service records and fixture credentials are used. The output
contains counts and source identities, not credentials or returned bodies.
A reproduced counterexample is an open finding, not a passing product check.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import httpx

from loop_engine.core.service_runtime.http_test_fixtures import HttpDomainFixture, running_http
from loop_engine.core.retrieval import Retriever


def main():
    with TemporaryDirectory(prefix="publication-revocation-") as directory:
        fixture = HttpDomainFixture(Path(directory))
        with running_http(fixture) as (base, _service):
            original = Retriever.search
            def revoke_after_ranking(retriever, *args, **kwargs):
                result = original(retriever, *args, **kwargs)
                fixture.runtime.set_grants("alpha", ())
                return result
            payload = {"record_type": "service_retrieval_request/v1", "query": "Alpha", "top_n": 10}
            with httpx.Client(base_url=base, headers=fixture.headers(), trust_env=False) as client:
                with patch.object(Retriever, "search", revoke_after_ranking):
                    response = client.post("/api/v1/retrieval", json=payload)
                later = client.post("/api/v1/retrieval", json=payload)
            observed = {"initial_status": response.status_code,
                        "references_after_mid_query_revocation": len(response.json().get("result", {}).get("hits", [])),
                        "following_status": later.status_code,
                        "following_references": len(later.json().get("result", {}).get("hits", []))}
    root = Path(__file__).resolve().parents[2]
    paths = ("src/loop_engine/core/service_runtime/http.py", "src/loop_engine/core/service_runtime/provisioning.py",
             "src/loop_engine/core/service_runtime/runtime.py")
    result = {"record_type": "publication_revocation_probe/v1", "observation": observed,
              "counterexample_reproduced": observed["references_after_mid_query_revocation"] > 0,
              "bodies_tested": False, "external_provider_calls": 0,
              "disposition": "open_in_flight_metadata_consistency_finding",
              "source_sha256": {path: hashlib.sha256((root / path).read_bytes()).hexdigest() for path in paths}}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
