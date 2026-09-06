import unittest
from seconds import to_seconds

class TestToSeconds(unittest.TestCase):
    def test_zero(self):
        self.assertEqual(to_seconds(0, 0), 0)

    def test_hours_only(self):
        self.assertEqual(to_seconds(1, 0), 3600)

    def test_hours_and_minutes(self):
        self.assertEqual(to_seconds(1, 30), 5400)

if __name__ == '__main__':
    unittest.main()
