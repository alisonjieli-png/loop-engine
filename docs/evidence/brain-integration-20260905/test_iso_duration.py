"""Tests for iso_duration.parse_duration."""

import unittest

from iso_duration import parse_duration


class ParseDurationValidTests(unittest.TestCase):
    """Valid ISO-8601 duration strings."""

    def test_example_three_days_four_hours_five_minutes(self):
        self.assertEqual(parse_duration("P3DT4H5M"), 273900)

    def test_example_thirty_seconds(self):
        self.assertEqual(parse_duration("PT30S"), 30)

    def test_example_one_year_two_months_ten_days_two_hours_thirty_minutes(self):
        self.assertEqual(parse_duration("P1Y2M10DT2H30M"), 37593000)

    def test_one_year(self):
        self.assertEqual(parse_duration("P1Y"), 31536000)

    def test_one_month(self):
        self.assertEqual(parse_duration("P1M"), 2592000)

    def test_one_day(self):
        self.assertEqual(parse_duration("P1D"), 86400)

    def test_one_hour(self):
        self.assertEqual(parse_duration("PT1H"), 3600)

    def test_one_minute(self):
        self.assertEqual(parse_duration("PT1M"), 60)

    def test_one_second(self):
        self.assertEqual(parse_duration("PT1S"), 1)

    def test_zero_duration(self):
        self.assertEqual(parse_duration("P0D"), 0)

    def test_combined_duration(self):
        self.assertEqual(parse_duration("P1Y2M3DT4H5M6S"), 36993906)


class ParseDurationMalformedTests(unittest.TestCase):
    """Malformed ISO-8601 duration strings must raise ValueError."""

    def test_empty_string(self):
        with self.assertRaises(ValueError):
            parse_duration("")

    def test_bare_p(self):
        with self.assertRaises(ValueError):
            parse_duration("P")

    def test_bare_pt(self):
        with self.assertRaises(ValueError):
            parse_duration("PT")

    def test_t_without_time_component(self):
        with self.assertRaises(ValueError):
            parse_duration("P1DT")

    def test_weeks_not_supported(self):
        with self.assertRaises(ValueError):
            parse_duration("P1W")

    def test_fractional_seconds(self):
        with self.assertRaises(ValueError):
            parse_duration("PT0.5S")

    def test_negative_duration(self):
        with self.assertRaises(ValueError):
            parse_duration("-P1D")

    def test_missing_p_prefix(self):
        with self.assertRaises(ValueError):
            parse_duration("1D")

    def test_time_component_in_date_part(self):
        with self.assertRaises(ValueError):
            parse_duration("P1D2H")

    def test_day_in_time_part(self):
        with self.assertRaises(ValueError):
            parse_duration("PT1D")

    def test_duplicate_year(self):
        with self.assertRaises(ValueError):
            parse_duration("P1Y1Y")

    def test_duplicate_day(self):
        with self.assertRaises(ValueError):
            parse_duration("P1D2D")

    def test_leading_whitespace(self):
        with self.assertRaises(ValueError):
            parse_duration(" P1D")

    def test_trailing_whitespace(self):
        with self.assertRaises(ValueError):
            parse_duration("P1D ")


class ParseDurationRegressionTests(unittest.TestCase):
    """Regressions for reported defects: trailing newlines and non-strings."""

    def test_trailing_newline_after_seconds(self):
        with self.assertRaises(ValueError):
            parse_duration("PT30S\n")

    def test_trailing_newline_after_days(self):
        with self.assertRaises(ValueError):
            parse_duration("P1D\n")

    def test_none_raises_value_error(self):
        with self.assertRaises(ValueError):
            parse_duration(None)

    def test_int_raises_value_error(self):
        with self.assertRaises(ValueError):
            parse_duration(30)

    def test_float_raises_value_error(self):
        with self.assertRaises(ValueError):
            parse_duration(30.0)

    def test_bool_raises_value_error(self):
        with self.assertRaises(ValueError):
            parse_duration(True)

    def test_bytes_raises_value_error(self):
        with self.assertRaises(ValueError):
            parse_duration(b"P1D")

    def test_list_raises_value_error(self):
        with self.assertRaises(ValueError):
            parse_duration(["P1D"])

    def test_dict_raises_value_error(self):
        with self.assertRaises(ValueError):
            parse_duration({"P1D": 1})


if __name__ == "__main__":
    unittest.main()
