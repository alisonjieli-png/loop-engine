"""Discover and invoke a Brave Web Search capability through a LoopRef."""

import argparse
import json
import os

from loop_engine import LoopLedger
from loop_engine.loop.capability_loops import run_capability_ref_as_loop
from loop_engine.static_architecture.brave_search import (
    BraveWebSearchRequest,
    HttpResponse,
    MappingSecretProvider,
    SequenceTransport,
    register_brave_search,
)
from loop_engine.static_architecture.capability_directory import (
    CapabilityDirectory,
)


def offline_fixture():
    body = {
        "type": "search",
        "query": {
            "original": "Python package supply chain security",
            "more_results_available": False,
        },
        "web": {
            "results": [{
                "title": "Software supply chain security guide",
                "url": "https://example.test/supply-chain-guide",
                "description": "A deterministic offline fixture.",
                "extra_snippets": ["Verify packages before installation."],
            }]
        },
    }
    response = HttpResponse(
        200,
        {
            "X-RateLimit-Limit": "1, 15000",
            "X-RateLimit-Remaining": "0, 14999",
            "X-RateLimit-Reset": "1, 1000",
        },
        json.dumps(body).encode(),
    )
    return (
        MappingSecretProvider({"env:BRAVE_SEARCH_API_KEY": "fixture-token"}),
        SequenceTransport([response]),
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--live",
        action="store_true",
        help="make one live Brave request using BRAVE_SEARCH_API_KEY",
    )
    args = parser.parse_args()

    directory = CapabilityDirectory()
    transport = None
    if args.live:
        if not os.environ.get("BRAVE_SEARCH_API_KEY"):
            raise SystemExit("BRAVE_SEARCH_API_KEY is required with --live")
        register_brave_search(directory)
    else:
        secrets, transport = offline_fixture()
        register_brave_search(
            directory, secret_provider=secrets, transport=transport)

    calls_before_discovery = (
        len(transport.requests) if transport is not None else "not observable"
    )
    refs = directory.search_static_architecture("search the current public web")
    selected = next(
        ref for ref in refs
        if ref.handshake.loop_id == "brave_web_search"
    )
    calls_after_discovery = (
        len(transport.requests) if transport is not None else "not observable"
    )

    ledger = LoopLedger()
    result = run_capability_ref_as_loop(
        directory,
        selected,
        "search",
        request=BraveWebSearchRequest(
            "Python package supply chain security",
            count=1,
            freshness="pm" if args.live else "",
            extra_snippets=True,
        ),
        access_mode="approved_external_read",
        ledger=ledger,
    )

    print("BRAVE STATIC ARCHITECTURE PLUGIN")
    print(f"  selected ref: {selected.loop_ref}")
    print(f"  calls before discovery: {calls_before_discovery}")
    print(f"  calls after discovery: {calls_after_discovery}")
    print(f"  capability loop: {result['loop_id']}")
    print(f"  model calls: {result['model_calls']}")
    print(f"  capability outcome: {result['capability_terminal_code']}")
    print(f"  persistable: {result['value'].get('persistable')}")
    for candidate in result["value"].get("candidates", ()):
        print(f"  source: {candidate['title']} | {candidate['url']}")


if __name__ == "__main__":
    main()
