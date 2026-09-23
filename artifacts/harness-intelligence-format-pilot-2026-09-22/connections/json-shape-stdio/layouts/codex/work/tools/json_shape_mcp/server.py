"""Candidate-only, local read-only JSON shape tool over MCP stdio.

This tool does not read files, contact a network endpoint, write state, or
receive a credential. It is not installed in any active harness. The test
uses the pinned Python MCP SDK 1.29.0 and a local subprocess only.
"""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

MAX_DOCUMENT_BYTES = 65_536
MAX_KEY_NAMES = 100
server = FastMCP("baltor-candidate-json-shape")


def _reject_nonstandard_constant(value: str) -> None:
    raise ValueError(f"nonstandard JSON constant refused: {value}")


def _unique_object_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key refused")
        result[key] = value
    return result


@server.tool()
def inspect_json_shape(document: str) -> dict[str, object]:
    """Describe top-level JSON type and object keys without returning values."""
    if len(document.encode("utf-8")) > MAX_DOCUMENT_BYTES:
        raise ValueError("JSON document exceeds the candidate tool's 65536-byte input limit")
    parsed = json.loads(document, parse_constant=_reject_nonstandard_constant,
                        object_pairs_hook=_unique_object_keys)
    if isinstance(parsed, dict):
        keys = sorted(parsed)
        return {
            "top_level_type": "object",
            "field_count": len(keys),
            "field_names": keys[:MAX_KEY_NAMES],
            "field_names_truncated": len(keys) > MAX_KEY_NAMES,
        }
    if isinstance(parsed, list):
        return {"top_level_type": "array", "item_count": len(parsed)}
    if isinstance(parsed, str):
        kind = "string"
    elif isinstance(parsed, bool):
        kind = "boolean"
    elif parsed is None:
        kind = "null"
    else:
        kind = "number"
    return {"top_level_type": kind}


if __name__ == "__main__":
    server.run(transport="stdio")
