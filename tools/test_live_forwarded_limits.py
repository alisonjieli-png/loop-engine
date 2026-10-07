"""Scope and cadence controls for the separate-network refusal observer."""
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_live_forwarded_limits import ORIGINS, observe


class PeerObserver(unittest.TestCase):
    def test_wrong_origin_or_excessive_population_makes_no_request(self):
        opener = Mock()
        for origin, count, interval in (('https://example.com', 1, 5), (ORIGINS[0], 25, 5), (ORIGINS[0], 2, 0)):
            with self.assertRaises(ValueError):
                observe(origin, samples=count, interval=interval, opener=opener)
        opener.open.assert_not_called()

    def test_observer_does_not_claim_full_qualification(self):
        class Response:
            status = 401
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, maximum): return b'{}'
        opener = Mock()
        opener.open.return_value = Response()
        pause = Mock()
        result = observe(ORIGINS[0], samples=2, opener=opener, sleep=pause)
        self.assertTrue(result['all_individually_unauthorized'])
        self.assertEqual(result['qualification'], 'requires_overlapping_other_network_limit_record')
        self.assertEqual(opener.open.call_count, 2)
        pause.assert_called_once_with(5)


if __name__ == '__main__':
    unittest.main()
