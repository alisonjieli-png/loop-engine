"""Inspect one complete added-file extension root without external calls."""
from __future__ import annotations

import json
from pathlib import Path

from loop_engine.core.extension_discovery import (
    ExtensionApplicationRequest, ExtensionDiscoveryRequest,
    apply_provider_extensions,
    discover_extensions_as_loop)
from loop_engine.core.runtime_settings import RuntimeSettings


def main() -> None:
    root = Path(__file__).resolve().parent / "example_extension"
    snapshot = discover_extensions_as_loop(ExtensionDiscoveryRequest(
        explicit_roots=(str(root),), include_defaults=False), environ={})
    application = apply_provider_extensions(ExtensionApplicationRequest(
        RuntimeSettings(), snapshot),
        {"EXAMPLE_GATEWAY_BASE_URL": "https://gateway.example/v1",
         "EXAMPLE_GATEWAY_API_KEY": "not-used-by-this-example"})
    print(json.dumps({
        "record_type": "drop_in_extension_example/v1",
        "snapshot_digest": snapshot.content_digest,
        "discovery_loop_id": snapshot.loop_id,
        "providers": len(snapshot.providers),
        "capability_candidates": len(snapshot.capabilities),
        "skill_candidates": len(snapshot.skills),
        "plugin_bundles": len(snapshot.plugins),
        "intelligence_candidates": len(snapshot.intelligence_entries),
        "activated_routes": list(application.activated_routes),
        "provider_calls_made": 0,
        "capability_code_executed": False,
    }, indent=2))


if __name__ == "__main__":
    main()
