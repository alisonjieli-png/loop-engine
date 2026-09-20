"""Offline discrimination checks for bounded service measurements."""
import unittest

from tools.measure_service_latency import percentile, summarize, validated_origin


class LatencyChecks(unittest.TestCase):
    def test_origin_refuses_credentials_paths_fragments_and_ambiguous_ports(self):
        self.assertEqual(validated_origin("https://service.example"), "service.example")
        for value in ("http://service.example", "https://user:secret@service.example", "https://service.example/",
                      "https://service.example?token=x", "https://service.example#fragment", "https://service.example:444"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validated_origin(value)

    def test_unknown_is_not_zero_and_nearest_rank_is_explicit(self):
        self.assertIsNone(percentile([], .95))
        self.assertEqual(percentile(list(range(1, 21)), .95), 19)
        self.assertEqual(percentile([10, 5, 2], .5), 5)

    def test_failure_and_cold_connection_are_not_hidden(self):
        result = summarize([{"total_ms": 900, "ok": True, "new_connection": True},
                            {"total_ms": 20, "ok": True, "new_connection": False},
                            {"total_ms": 20000, "ok": False, "new_connection": False}])
        self.assertEqual(result["attempted"], 3)
        self.assertEqual(result["failed"], 1)
        self.assertEqual(result["successful_p95_ms"], 900)
        self.assertEqual(result["reused_connection_successful_p95_ms"], 20)


if __name__ == "__main__":
    unittest.main()
