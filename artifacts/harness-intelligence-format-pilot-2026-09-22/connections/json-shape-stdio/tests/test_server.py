"""Local behavior and real stdio protocol checks for the candidate server."""

from __future__ import annotations

import asyncio
import json
import sys
import unittest
from pathlib import Path

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

SERVER = Path(__file__).resolve().parents[1] / "server.py"
sys.path.insert(0, str(SERVER.parent))
from server import inspect_json_shape


class JsonShapeBehavior(unittest.TestCase):
    def test_object_and_array_shapes_hide_values(self) -> None:
        self.assertEqual(
            inspect_json_shape('{"token":"sensitive-value","count":2}'),
            {"top_level_type": "object", "field_count": 2,
             "field_names": ["count", "token"], "field_names_truncated": False},
        )
        self.assertEqual(inspect_json_shape("[1,2,3]"),
                         {"top_level_type": "array", "item_count": 3})

    def test_invalid_and_overlarge_inputs_are_refused(self) -> None:
        with self.assertRaises(json.JSONDecodeError):
            inspect_json_shape("{not-json}")
        with self.assertRaisesRegex(ValueError, "nonstandard JSON constant"):
            inspect_json_shape('{"x":NaN}')
        with self.assertRaisesRegex(ValueError, "duplicate JSON object key"):
            inspect_json_shape('{"x":1,"x":2}')
        with self.assertRaisesRegex(ValueError, "input limit"):
            inspect_json_shape('"' + "x" * 65_536 + '"')


class JsonShapeStdioProtocol(unittest.IsolatedAsyncioTestCase):
    async def test_initialize_list_and_call_without_a_model(self) -> None:
        parameters = StdioServerParameters(command=sys.executable, args=[str(SERVER)])
        async with (
            stdio_client(parameters) as (reader, writer),
            ClientSession(reader, writer) as session,
        ):
            negotiated = await asyncio.wait_for(session.initialize(), timeout=10)
            self.assertEqual(negotiated.protocolVersion, "2025-11-25")
            listing = await asyncio.wait_for(session.list_tools(), timeout=10)
            names = [tool.name for tool in listing.tools]
            self.assertEqual(names, ["inspect_json_shape"])
            response = await asyncio.wait_for(
                session.call_tool("inspect_json_shape", {"document": '{"a":1}'}),
                timeout=10,
            )
            self.assertFalse(response.isError)
            self.assertIn("top_level_type", str(response.content))
            invalid = await asyncio.wait_for(
                session.call_tool("inspect_json_shape", {"document": '{"x":NaN}'}),
                timeout=10,
            )
            self.assertTrue(invalid.isError)
            duplicate = await asyncio.wait_for(
                session.call_tool("inspect_json_shape", {
                    "document": '{"sensitive-key-name":1,"sensitive-key-name":2}'
                }),
                timeout=10,
            )
            self.assertTrue(duplicate.isError)
            self.assertNotIn("sensitive-key-name", str(duplicate.content))


if __name__ == "__main__":
    unittest.main()
