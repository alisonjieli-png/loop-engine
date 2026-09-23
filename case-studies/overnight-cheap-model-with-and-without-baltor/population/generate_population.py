"""Generate the frozen population for the overnight cheap model study.

Six task families: phone numbers, email addresses, address lines, duplicate
company records, name capitalisation and website addresses. Every row starts
from a clean truth that this file declares, and a named case type describes
how the input differs from it. The seed only chooses fictional line numbers
and the row order, so the same seed always writes the same bytes.

The first four families extend the population of the data cleanup study
(`case-studies/data-cleanup-with-and-without-baltor/population/generate_population.py`)
with harder rows. Every row of that population is kept except one whose
truth was disputed in its report (`45 Kingsway Burnaby`). Names and websites
are new.

All data is synthetic. Telephone numbers use ranges reserved for fiction:
555-0100 to 555-0199 in North America, the Ofcom drama ranges in the United
Kingdom and the ACMA range (02) 5550 xxxx in Australia. Web addresses use the
names reserved by RFC 2606 and the documentation network of RFC 5737. People,
companies, email addresses and street numbers are invented. Street, city and
postal code formats follow real conventions.

Usage:

    python generate_population.py            # write the population files
    python generate_population.py --check    # exit 1 when a written file differs

Only the Python standard library is used.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SEED = 20260923
RECORD_TYPE = "overnight_population/v1"
FAMILIES = ("phones", "emails", "addresses", "duplicates", "names", "websites")


# ---------------------------------------------------------------------------
# Shared helpers


def csv_text(header, rows):
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(header)
    for row in rows:
        writer.writerow(row)
    return buffer.getvalue()


def json_text(value):
    return json.dumps(value, indent=1, ensure_ascii=True, sort_keys=False) + "\n"


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class LineNumbers:
    """Distinct fictional four digit line numbers from 0100 to 0199."""

    def __init__(self, rng):
        self._pool = [f"01{n:02d}" for n in range(100)]
        rng.shuffle(self._pool)

    def take(self):
        return self._pool.pop()


def value_row(case_type, variant, value, kind, expected, review, accepted=None):
    row = dict(case_type=case_type, variant=variant, input=value, kind=kind,
               expected=expected, review=review)
    if accepted is not None:
        row["accepted"] = accepted
    if kind == "keep" and expected != value:
        raise ValueError(f"a keep row must expect its input: {value!r}")
    if kind == "hold" and (expected != value or review != "yes"):
        raise ValueError(f"a hold row must expect its input with review yes: {value!r}")
    if kind == "change" and expected == value:
        raise ValueError(f"a change row must expect a different value: {value!r}")
    return row


# ---------------------------------------------------------------------------
# Family 1: phone numbers
#
# Clean truth: a country, a national number and an optional extension.
# Expected outcome kinds: change, keep, hold, alternatives.

NANP_AREAS = ("415", "212", "312", "617", "206", "303", "512", "416", "604", "514", "613")


def phone_rows(rng):
    lines = LineNumbers(rng)
    rows = []

    def area():
        return rng.choice(NANP_AREAS)

    def nanp(fixed_area=None):
        a, line = fixed_area or area(), lines.take()
        return a, line, f"+1{a}555{line}"

    def tail():
        """Three digits that follow a drama range prefix ending in 0."""
        return lines.take()[1:]

    add = rows.append
    # --- rows of the data cleanup study population --------------------------
    for template, variant in (
            ("({a}) 555-{l}", "parentheses_and_dash"), ("{a}-555-{l}", "dashes"),
            ("{a}.555.{l}", "dots"), ("{a}555{l}", "ten_bare_digits"),
            ("{a} 555 {l}", "spaces"), (" {a}-555-{l} ", "surrounding_spaces"),
            ("{a}\u2013555\u2013{l}", "unicode_dashes")):
        a, line, e164 = nanp()
        add(value_row("national_number_formatted", variant, template.format(a=a, l=line),
                      "change", e164, "no"))
    for template, variant in (
            ("1-{a}-555-{l}", "one_dash"), ("+1 {a} 555 {l}", "plus_one_spaces"),
            ("1 ({a}) 555-{l}", "one_parentheses"), ("+1-{a}-555-{l}", "plus_one_dashes"),
            ("1{a}555{l}", "eleven_bare_digits")):
        a, line, e164 = nanp()
        add(value_row("country_code_one_present", variant, template.format(a=a, l=line),
                      "change", e164, "no"))
    for variant in ("north_american", "canadian"):
        a, line, e164 = nanp("613" if variant == "canadian" else None)
        add(value_row("already_e164", variant, e164, "keep", e164, "no"))
    for variant, (code, prefix) in (("uk_london", ("20", "79460")), ("uk_mobile", ("7700", "900"))):
        value = f"+44{code}{prefix}{tail()}"
        add(value_row("already_e164", variant, value, "keep", value, "no"))
    for (template, variant), ext in zip((("{a}-555-{l} ext. {e}", "ext_period"),
                                         ("({a}) 555-{l} x{e}", "x_marker"),
                                         ("{a}.555.{l} extension {e}", "extension_word")),
                                        ("12", "305", "7")):
        a, line, e164 = nanp()
        add(value_row("extension", variant, template.format(a=a, l=line, e=ext), "change",
                      f"{e164} ext {ext}", "no"))
    london, mobile, manchester = tail(), tail(), tail()
    for value, expected, variant in (
            (f"+44 20 7946 0{london}", f"+442079460{london}", "uk_london"),
            (f"+44 7700 900{mobile}", f"+447700900{mobile}", "uk_mobile"),
            (f"+44 161 496 0{manchester}", f"+441614960{manchester}", "uk_manchester")):
        add(value_row("international_with_plus", variant, value, "change", expected, "no"))
    # The United Kingdom trunk prefix 0 is never dialled from abroad, so it is
    # not part of the E.164 form.
    london, bristol = tail(), tail()
    for value, expected, variant in (
            (f"+44 (0)20 7946 0{london}", f"+442079460{london}", "uk_london"),
            (f"+44 (0) 117 496 0{bristol}", f"+441174960{bristol}", "uk_bristol")):
        add(value_row("trunk_prefix_in_parentheses", variant, value, "change", expected, "no"))
    # 011 is the international call prefix used from the United States and Canada.
    london, mobile = tail(), tail()
    for value, expected, variant in (
            (f"011 44 20 7946 0{london}", f"+442079460{london}", "uk_london"),
            (f"011-44-7700-900{mobile}", f"+447700900{mobile}", "uk_mobile")):
        add(value_row("north_american_exit_prefix", variant, value, "change", expected, "no"))
    for value, variant in ((f"555-{lines.take()}", "seven_digits_dash"),
                           (f"555 {lines.take()}", "seven_digits_space")):
        add(value_row("hold_no_area_code", variant, value, "hold", value, "yes"))
    a = area()
    value = f"{a}-555-{lines.take()} / {a}-555-{lines.take()}"
    add(value_row("hold_two_numbers", "slash", value, "hold", value, "yes"))
    value = f"{area()}-555-{lines.take()[:3]}"
    add(value_row("hold_wrong_digit_count", "nine_digits", value, "hold", value, "yes"))
    value = f"{area()}-555-{lines.take()}9"
    add(value_row("hold_wrong_digit_count", "eleven_digits_no_leading_one", value, "hold",
                  value, "yes"))
    # North American area codes never start with 0 or 1.
    value = f"(015) 555-{lines.take()}"
    add(value_row("hold_invalid_area_code", "area_code_starts_with_zero", value, "hold",
                  value, "yes"))
    # +41 is Switzerland, whose national numbers have nine digits; this one has eight.
    value = f"+415 555 {lines.take()}"
    add(value_row("hold_plus_with_impossible_length", "plus_41_eight_digits", value, "hold",
                  value, "yes"))
    for value, variant in (("", "empty"), ("n/a", "n_a"), ("unknown", "unknown"), ("-", "dash")):
        add(value_row("null_marker", variant, value, "keep", value, "no"))
    # A letter O typed for a zero: holding it and repairing it are both accepted.
    a, line = area(), lines.take()
    value = f"{a}-555-{line[:2]}O{line[3]}"
    fixed = f"+1{a}555{line[:2]}0{line[3]}"
    add(value_row("letter_o_for_zero", "ocr_like", value, "alternatives", fixed, "no",
                  accepted=[[value, "yes"], [fixed, "no"]]))
    # --- harder rows added for this study -------------------------------------
    # 00 is the international call prefix used from most countries outside North America.
    leeds, mobile = tail(), tail()
    for value, expected, variant in (
            (f"00 44 113 496 0{leeds}", f"+441134960{leeds}", "uk_leeds"),
            (f"0044 7700 900{mobile}", f"+447700900{mobile}", "uk_mobile_joined")):
        add(value_row("exit_prefix_00", variant, value, "change", expected, "no"))
    # A number after +44 never starts with 0, so a written 0 is the trunk prefix.
    london, manchester = tail(), tail()
    for value, expected, variant in (
            (f"+44 020 7946 0{london}", f"+442079460{london}", "uk_london"),
            (f"+44 0161 496 0{manchester}", f"+441614960{manchester}", "uk_manchester")):
        add(value_row("trunk_prefix_after_country_code", variant, value, "change", expected,
                      "no"))
    mobile = tail()
    add(value_row("trunk_prefix_in_parentheses", "uk_mobile", f"+44 (0)7700 900{mobile}",
                  "change", f"+447700900{mobile}", "no"))
    sydney = lines.take()
    add(value_row("trunk_prefix_in_parentheses", "australia_sydney", f"+61 (0)2 5550 {sydney}",
                  "change", f"+6125550{sydney}", "no"))
    sydney = lines.take()
    add(value_row("international_with_plus", "australia_sydney", f"+61 2 5550 {sydney}",
                  "change", f"+6125550{sydney}", "no"))
    a, line, e164 = nanp("415")
    add(value_row("label_text", "tel_colon", f"Tel: ({a}) 555-{line}", "change", e164, "no"))
    a, line, e164 = nanp("312")
    add(value_row("label_text", "cell_word", f"cell {a}.555.{line}", "change", e164, "no"))
    london = tail()
    add(value_row("label_text", "office_international", f"Office: +44 20 7946 0{london}",
                  "change", f"+442079460{london}", "no"))
    a, line, e164 = nanp("212")
    add(value_row("extension", "upper_case_ext", f"({a}) 555-{line} EXT 204", "change",
                  f"{e164} ext 204", "no"))
    a, line, e164 = nanp("212")
    add(value_row("extension", "comma_before_ext", f"{a}-555-{line}, ext. 3", "change",
                  f"{e164} ext 3", "no"))
    london = tail()
    add(value_row("extension", "international_x", f"+44 20 7946 0{london} x12", "change",
                  f"+442079460{london} ext 12", "no"))
    a, line, e164 = nanp("415")
    wide = str.maketrans("0123456789-", "\uff10\uff11\uff12\uff13\uff14\uff15\uff16\uff17\uff18\uff19\uff0d")
    add(value_row("fullwidth_digits", "fullwidth", f"{a}-555-{line}".translate(wide), "change",
                  e164, "no"))
    a, line, e164 = nanp()
    add(value_row("national_number_formatted", "non_breaking_spaces",
                  f"{a}\u00a0555\u00a0{line}", "change", e164, "no"))
    a, line, e164 = nanp("416")
    add(value_row("country_code_one_present", "plus_one_parentheses_canada",
                  f"+1 ({a}) 555-{line}", "change", e164, "no"))
    a, line, e164 = nanp("415")
    add(value_row("already_e164", "with_extension", f"{e164} ext 7", "keep", f"{e164} ext 7",
                  "no"))
    # N11 codes such as 411 are service codes, never area codes.
    value = f"(411) 555-{lines.take()}"
    add(value_row("hold_invalid_area_code", "n11_service_code", value, "hold", value, "yes"))
    value = f"(155) 555-{lines.take()}"
    add(value_row("hold_invalid_area_code", "area_code_starts_with_one", value, "hold", value,
                  "yes"))
    value = f"+1 555 {lines.take()}"
    add(value_row("hold_plus_with_impossible_length", "plus_1_seven_digits", value, "hold",
                  value, "yes"))
    value = f"312-555-{lines.take()} or 312-555-{lines.take()}"
    add(value_row("hold_two_numbers", "or_word", value, "hold", value, "yes"))
    value = f"555-{lines.take()} ext 4"
    add(value_row("hold_no_area_code", "seven_digits_with_extension", value, "hold", value, "yes"))
    add(value_row("hold_placeholder", "all_zeros", "000-000-0000", "hold", "000-000-0000", "yes"))
    add(value_row("null_marker", "upper_case_n_a", "N/A", "keep", "N/A", "no"))
    return rows


PHONE_TASK = """Task: clean the `phone` column. The table has the columns `id` and `phone`. The customers are in the United States and Canada, so a number written without a country code has the country code 1.

Write `output.csv` with the columns `id`, `phone` and `review`, one row for each input row, in any order:
- Write each number in E.164 form: a plus sign, the country code and the rest of the number, with no spaces or punctuation, for example `+14155550123`.
- When a number has an extension, keep it after the number as a space, the word `ext`, a space and the extension digits, for example `+14155550123 ext 12`.
- Leave an empty value or a null marker such as `n/a` exactly as it is, with `review` set to `no`.
- When you cannot be certain what the correct E.164 number is, do not guess: copy the input value exactly as it is and set `review` to `yes`.
- Otherwise set `review` to `no`."""


# ---------------------------------------------------------------------------
# Family 2: email addresses


def email_rows(rng):
    rows = []

    def add(case_type, variant, value, kind, expected, review):
        rows.append(value_row(case_type, variant, value, kind, expected, review))

    # --- rows of the data cleanup study population --------------------------
    for value in ("ana.lopez@example.com", "j.smith@acmewidgets.com",
                  "info@northwind-traders.co.uk", "ops+billing@example.org",
                  "k.nguyen@riverbend.io"):
        add("valid_already_clean", "valid", value, "keep", value, "no")
    for value, variant in (("Ana.Lopez@Example.COM", "mixed_case"),
                           ("bob.chen @example.net", "space_inside"),
                           ("SALES@GLOBEX.CA", "upper_case"),
                           ("Info@Harbor-Freight-Supply.com", "mixed_case_domain")):
        add("case_or_spaces", variant, value, "change", value.replace(" ", "").lower(), "no")
    for value, expected, variant in (
            ("mailto:li.wei@example.com", "li.wei@example.com", "mailto_prefix"),
            ("<omar.haddad@example.org>", "omar.haddad@example.org", "angle_brackets"),
            ("Priya Nair <priya.nair@example.com>", "priya.nair@example.com", "display_name")):
        add("wrapper", variant, value, "change", expected, "no")
    for value, expected, variant in (
            ("john.smith at example dot com", "john.smith@example.com", "words"),
            ("mary.jones [at] example [dot] org", "mary.jones@example.org", "square_brackets"),
            ("lee.park(at)example(dot)net", "lee.park@example.net", "parentheses"),
            ("sam.okoro AT example DOT com", "sam.okoro@example.com", "upper_case_words")):
        add("spelled_out_symbols", variant, value, "change", expected, "no")
    for value, expected, variant in (
            ("pat.kim@@example.com", "pat.kim@example.com", "doubled_at"),
            ("rosa.diaz@example..com", "rosa.diaz@example.com", "doubled_dot"),
            ("tom.berg@example.com.", "tom.berg@example.com", "trailing_period"),
            ("ines.costa@example,com", "ines.costa@example.com", "comma_for_dot")):
        add("punctuation_slip", variant, value, "change", expected, "no")
    # A domain ending that does not exist cannot be the intended domain.
    for value, expected, variant in (
            ("maria.okafor@gmail.con", "maria.okafor@gmail.com", "con"),
            ("t.brennan@yahoo.cmo", "t.brennan@yahoo.com", "cmo"),
            ("eve.larsen@outlook.comm", "eve.larsen@outlook.com", "comm")):
        add("impossible_domain_ending", variant, value, "change", expected, "no")
    # A domain that could be real as written must not be rewritten on a guess.
    for value, variant in (("maria.okafor@gmail.co", "co_is_a_real_ending"),
                           ("dan.reyes@hotmial.com", "plausible_registered_domain"),
                           ("liz.moreau@gmail.cm", "cm_is_a_real_ending")):
        add("hold_plausible_real_domain", variant, value, "hold", value, "yes")
    for value, variant in (("ana.lopez@example.com; bo.lin@example.com", "semicolon"),
                           ("sales@globex.ca, support@globex.ca", "comma")):
        add("hold_two_addresses", variant, value, "hold", value, "yes")
    for value, variant in (("ana.lopez.example.com", "no_at_sign"),
                           ("@example.com", "no_local_part"),
                           ("bob.chen@example", "no_domain_ending")):
        add("hold_unrecoverable", variant, value, "hold", value, "yes")
    for value, variant in (("", "empty"), ("n/a", "n_a"), ("none", "none")):
        add("null_marker", variant, value, "keep", value, "no")
    add("invisible_character", "zero_width_space", "noor.ali@exa\u200bmple.com", "change",
        "noor.ali@example.com", "no")
    # --- harder rows added for this study -------------------------------------
    add("wrapper", "quoted_display_name_with_comma", '"Nair, Priya" <priya.nair@example.com>',
        "change", "priya.nair@example.com", "no")
    add("wrapper", "upper_case_mailto", "MAILTO:Grace.Ho@Example.org", "change",
        "grace.ho@example.org", "no")
    add("wrapper", "trailing_separator", "ana.ruiz@example.com;", "change",
        "ana.ruiz@example.com", "no")
    add("wrapper", "trailing_comment", "omar.farouk@example.net (work)", "change",
        "omar.farouk@example.net", "no")
    add("spelled_out_symbols", "only_at_spelled_out", "wen.zhou at example.com", "change",
        "wen.zhou@example.com", "no")
    add("spelled_out_symbols", "only_dot_spelled_out", "raj.patel@example dot org", "change",
        "raj.patel@example.org", "no")
    add("invisible_character", "soft_hyphen", "noor.haddad@exam\u00adple.com", "change",
        "noor.haddad@example.com", "no")
    add("invisible_character", "fullwidth_at_sign", "ines.moreau\uff20example.com", "change",
        "ines.moreau@example.com", "no")
    add("impossible_domain_ending", "con_second_provider", "chris.lee@outlook.con", "change",
        "chris.lee@outlook.com", "no")
    add("impossible_domain_ending", "cmo_second_provider", "pat.nolan@hotmail.cmo", "change",
        "pat.nolan@hotmail.com", "no")
    add("case_or_spaces", "mixed_case_subdomain", "Dana.White@Mail.Example.co.uk", "change",
        "dana.white@mail.example.co.uk", "no")
    add("valid_already_clean", "subdomain", "a.b@mail.example.co.uk", "keep",
        "a.b@mail.example.co.uk", "no")
    add("valid_already_clean", "internationalized_domain", "jose.garcia@m\u00fcnchen.example",
        "keep", "jose.garcia@m\u00fcnchen.example", "no")
    for value, variant in (("N/A", "upper_case_n_a"), ("-", "dash")):
        add("null_marker", variant, value, "keep", value, "no")
    for value, variant in ((".ana.silva@example.com", "leading_dot_in_local_part"),
                           ("ana silva@example.com", "space_inside_local_part"),
                           ('"john doe"@example.com', "quoted_local_part_with_space")):
        add("hold_unrecoverable", variant, value, "hold", value, "yes")
    for value, variant in (("dana.white@gmial.com", "plausible_registered_domain_gmial"),
                           ("eli.stone@yaho.com", "plausible_registered_domain_yaho"),
                           ("sam.ortiz@yahoo.co", "co_is_a_real_ending_second_provider")):
        add("hold_plausible_real_domain", variant, value, "hold", value, "yes")
    add("hold_two_addresses", "slash", "info@example.com / sales@example.com", "hold",
        "info@example.com / sales@example.com", "yes")
    rng.shuffle(rows)
    return rows


EMAIL_TASK = """Task: clean the `email` column. The table has the columns `id` and `email`.

Write `output.csv` with the columns `id`, `email` and `review`, one row for each input row, in any order:
- Write each address in lower case, without spaces, without a `mailto:` prefix, without angle brackets and without a display name.
- Repair an address only when the intended address is certain. For example, `ann at example dot com` is certainly `ann@example.com`.
- Leave an empty value or a null marker such as `n/a` exactly as it is, with `review` set to `no`.
- When a value holds more than one address, or you cannot be certain of the intended address, do not guess: copy the input value exactly as it is and set `review` to `yes`.
- Otherwise set `review` to `no`."""


# ---------------------------------------------------------------------------
# Family 3: address lines

ADDRESS_PARTS = ("house_number", "street", "unit", "city", "region", "postal_code", "country")


def address_rows(rng):
    rows = []

    def add(case_type, value, parts, review="no", kind="split"):
        expected = dict(zip(ADDRESS_PARTS, parts))
        for part_value in expected.values():
            if part_value and part_value not in value:
                raise ValueError(f"expected part {part_value!r} is not in {value!r}")
        rows.append(dict(case_type=case_type, input=value, kind=kind if review == "no" else "hold",
                         expected=expected, review=review))

    empty = ("", "", "", "", "", "", "")
    # --- rows of the data cleanup study population --------------------------
    add("united_states_full", "12 N Main St Apt 4B, Springfield, IL 62704, USA",
        ("12", "N Main St", "Apt 4B", "Springfield", "IL", "62704", "USA"))
    add("united_states", "845 Oak Avenue, Portland, OR 97205",
        ("845", "Oak Avenue", "", "Portland", "OR", "97205", ""))
    add("united_states_zip_plus_four", "3100 Lakeview Dr Suite 200, Austin, TX 78701-2243",
        ("3100", "Lakeview Dr", "Suite 200", "Austin", "TX", "78701-2243", ""))
    add("united_states_hash_unit", "77 Cedar Ln #12, Denver, CO 80202",
        ("77", "Cedar Ln", "#12", "Denver", "CO", "80202", ""))
    add("united_states_country_words", "1509 Pine St Unit 3, Seattle, WA 98101, United States",
        ("1509", "Pine St", "Unit 3", "Seattle", "WA", "98101", "United States"))
    add("house_number_with_letter", "22B Elm Ave, Boston, MA 02108",
        ("22B", "Elm Ave", "", "Boston", "MA", "02108", ""))
    add("region_written_in_full", "400 W Madison Blvd Fl 9, Chicago, Illinois 60606",
        ("400", "W Madison Blvd", "Fl 9", "Chicago", "Illinois", "60606", ""))
    add("united_states_suite_abbreviation", "18 Harbor Rd Ste 5, Madison, WI 53703",
        ("18", "Harbor Rd", "Ste 5", "Madison", "WI", "53703", ""))
    add("united_states", "2211 N Clark St Apt 3R, Chicago, IL 60614",
        ("2211", "N Clark St", "Apt 3R", "Chicago", "IL", "60614", ""))
    add("street_with_direction_suffix", "1600 Grand Ave NW, Washington, DC 20001",
        ("1600", "Grand Ave NW", "", "Washington", "DC", "20001", ""))
    add("canada_no_comma_before_province", "77 Pine Road, Toronto ON M5V 2T6",
        ("77", "Pine Road", "", "Toronto", "ON", "M5V 2T6", ""))
    add("canada_french_street", "1200 Rue Sainte-Catherine O, Montr\u00e9al, QC H3B 1K9, Canada",
        ("1200", "Rue Sainte-Catherine O", "", "Montr\u00e9al", "QC", "H3B 1K9", "Canada"))
    add("canada_postal_code_without_space", "905 Granville St Unit 1402, Vancouver, BC V6Z1L3",
        ("905", "Granville St", "Unit 1402", "Vancouver", "BC", "V6Z1L3", ""))
    add("canada_french_street", "16 Rue du Port, Qu\u00e9bec, QC G1K 4E3",
        ("16", "Rue du Port", "", "Qu\u00e9bec", "QC", "G1K 4E3", ""))
    add("united_kingdom", "10 High Street, Bristol BS1 4DJ",
        ("10", "High Street", "", "Bristol", "", "BS1 4DJ", ""))
    add("united_kingdom_flat_before_number",
        "Flat 3, 22 Queen Street, Cardiff CF10 2BU, United Kingdom",
        ("22", "Queen Street", "Flat 3", "Cardiff", "", "CF10 2BU", "United Kingdom"))
    add("united_kingdom_with_county", "5 Mill Lane, Ashford, Kent TN24 8AA",
        ("5", "Mill Lane", "", "Ashford", "Kent", "TN24 8AA", ""))
    add("united_kingdom_short_country", "31 Park Row, Leeds LS1 5JL, UK",
        ("31", "Park Row", "", "Leeds", "", "LS1 5JL", "UK"))
    add("post_office_box", "PO Box 482, Springfield, IL 62705",
        ("", "PO Box 482", "", "Springfield", "IL", "62705", ""))
    add("post_office_box_with_periods", "P.O. Box 77, Halifax, NS B3J 2K9",
        ("", "P.O. Box 77", "", "Halifax", "NS", "B3J 2K9", ""))
    add("no_commas", "350 Fifth Ave New York NY 10118",
        ("350", "Fifth Ave", "", "New York", "NY", "10118", ""))
    add("no_commas", "88 Elm St Springfield MA 01103",
        ("88", "Elm St", "", "Springfield", "MA", "01103", ""))
    add("no_house_number", "Main Street, Springfield",
        ("", "Main Street", "", "Springfield", "", "", ""))
    add("street_and_city_only", "742 Maple Terrace, Springfield",
        ("742", "Maple Terrace", "", "Springfield", "", "", ""))
    add("street_and_city_only", "58 Bay St, Toronto",
        ("58", "Bay St", "", "Toronto", "", "", ""))
    add("unit_before_number", "Suite 400, 88 Harbor Blvd, Long Beach, CA 90802",
        ("88", "Harbor Blvd", "Suite 400", "Long Beach", "CA", "90802", ""))
    add("hold_street_or_city_boundary", "12 Main St West Springfield MA 01089", empty,
        review="yes")
    add("hold_intersection", "Corner of Main St and 2nd Ave, Springfield, IL", empty,
        review="yes")
    add("hold_not_an_address", "see notes", empty, review="yes")
    add("null_marker", "", empty, kind="keep")
    add("null_marker", "n/a", empty, kind="keep")
    # --- harder rows added for this study -------------------------------------
    add("unit_with_period", "501 W 5th St Apt. 2, Austin, TX 78701",
        ("501", "W 5th St", "Apt. 2", "Austin", "TX", "78701", ""))
    add("unit_word_and_hash", "9 Birch Rd Unit #5, Burlington, VT 05401",
        ("9", "Birch Rd", "Unit #5", "Burlington", "VT", "05401", ""))
    add("ordinal_street", "221 E 42nd St, New York, NY 10017",
        ("221", "E 42nd St", "", "New York", "NY", "10017", ""))
    # Queens, New York: the hyphen is part of the house number.
    add("hyphenated_house_number_queens", "37-02 Main St, Flushing, NY 11354",
        ("37-02", "Main St", "", "Flushing", "NY", "11354", ""))
    add("fractional_house_number", "12 1/2 Oak St, Ithaca, NY 14850",
        ("12 1/2", "Oak St", "", "Ithaca", "NY", "14850", ""))
    # Canada Post: a unit number written before the civic number, joined by a hyphen.
    add("canada_unit_hyphen_civic_number", "12-345 King St W, Toronto, ON M5V 1K4",
        ("345", "King St W", "12", "Toronto", "ON", "M5V 1K4", ""))
    add("canada_french_boulevard",
        "1500 Boul Ren\u00e9-L\u00e9vesque O, Montr\u00e9al, QC H3G 1T7",
        ("1500", "Boul Ren\u00e9-L\u00e9vesque O", "", "Montr\u00e9al", "QC", "H3G 1T7", ""))
    add("street_type_first", "1188 Avenue of the Americas, New York, NY 10036",
        ("1188", "Avenue of the Americas", "", "New York", "NY", "10036", ""))
    add("numbered_highway", "4500 US Highway 1, Princeton, NJ 08540",
        ("4500", "US Highway 1", "", "Princeton", "NJ", "08540", ""))
    add("post_office_box_in_words", "Post Office Box 12, Bangor, ME 04402",
        ("", "Post Office Box 12", "", "Bangor", "ME", "04402", ""))
    add("united_kingdom_apartment_before_number", "Apartment 4, 7 Mill Lane, Ashford TN24 8AA",
        ("7", "Mill Lane", "Apartment 4", "Ashford", "", "TN24 8AA", ""))
    add("no_postal_code", "1509 Pine St, Seattle, WA",
        ("1509", "Pine St", "", "Seattle", "WA", "", ""))
    add("unit_after_comma", "400 W Madison St, Floor 9, Chicago, IL 60606",
        ("400", "W Madison St", "Floor 9", "Chicago", "IL", "60606", ""))
    add("no_commas_with_unit", "2211 N Clark St Apt 3R Chicago IL 60614",
        ("2211", "N Clark St", "Apt 3R", "Chicago", "IL", "60614", ""))
    add("canada_unit_word_before_number", "Unit 3, 15 Water St, Halifax, NS B3H 1A1",
        ("15", "Water St", "Unit 3", "Halifax", "NS", "B3H 1A1", ""))
    add("hold_building_name", "Rose Cottage, 5 Church Lane, Ashford TN23 1AB", empty,
        review="yes")
    add("hold_two_addresses", "77 Cedar Ln, Denver, CO 80202 / 80 Cedar Ln, Denver, CO 80202",
        empty, review="yes")
    rng.shuffle(rows)
    return rows


ADDRESS_TASK = """Task: split each address into parts. The table has the columns `id` and `address`; each address is one line of text.

Write `output.csv` with the columns `id`, `house_number`, `street`, `unit`, `city`, `region`, `postal_code`, `country` and `review`, one row for each input row, in any order:
- Copy each part exactly as it is written in the address, with the same spelling, abbreviations, punctuation inside the part and capital letters. Do not expand, correct or translate anything, and do not add a part that is not written, such as a country that is not named.
- `street` is the street name with its type and direction, for example `N Main St`. `unit` is an apartment, suite, unit, flat, floor or room with its number, for example `Apt 4B`, `Flat 3` or `#12`. `region` is the state, province or county. A post office box goes in `street`, for example `PO Box 123`, with an empty `house_number`.
- Leave a part empty when the address does not contain it. For an empty value or a null marker such as `n/a`, leave every part empty and set `review` to `no`.
- When you cannot tell with certainty which part some words belong to, or the value is not one postal address, set `review` to `yes`. Otherwise set `review` to `no`."""


# ---------------------------------------------------------------------------
# Family 4: duplicate company records
#
# Each entity is one company at one location. A duplicate is a copy of the
# same entity written differently. Hard negatives are different entities
# that share a name, a building, a mailbox or a switchboard. Ambiguous pairs
# might be one company at one location and are expected as `review`.

ENTITIES = (
    ("acme", "Acme Widgets Inc", "12 N Main St Ste 4, Springfield, IL 62704", "orders@acmewidgets.com", "(217) 555-0141"),
    ("northwind", "Northwind Traders LLC", "845 Oak Avenue, Portland, OR 97205", "info@northwindtraders.com", "(503) 555-0112"),
    ("bluebird_denver", "Bluebird Bakery", "77 Cedar Ln, Denver, CO 80202", "hello@bluebirdbakery.com", "(303) 555-0187"),
    ("bluebird_seattle", "Bluebird Bakery", "1509 Pine St, Seattle, WA 98101", "seattle@bluebirdbakery.com", "(206) 555-0165"),
    ("summit_dental", "Summit Dental Group", "3100 Lakeview Dr, Austin, TX 78701", "frontdesk@summitdental.com", "(512) 555-0133"),
    ("summit_rental", "Summit Rental Group", "3180 Lakeview Dr, Austin, TX 78701", "office@summitrental.com", "(512) 555-0177"),
    ("harbor_light", "Harbor Light Legal PC", "400 W Madison St Fl 9, Chicago, IL 60606", "reception@madisonsuites.com", "(312) 555-0190"),
    ("crestline", "Crestline Consulting LLC", "400 W Madison St Fl 9, Chicago, IL 60606", "reception@madisonsuites.com", "(312) 555-0190"),
    ("globex", "Globex Corporation", "1200 Industrial Pkwy, Columbus, OH 43215", "contact@globex.com", "(614) 555-0158"),
    ("globex_logistics", "Globex Logistics LLC", "1200 Industrial Pkwy, Columbus, OH 43215", "logistics@globex.com", "(614) 555-0158"),
    ("riverbend", "Riverbend Books", "58 Bay St, Toronto, ON M5J 2N8", "shop@riverbendbooks.ca", "(416) 555-0122"),
    ("pinecrest", "Pinecrest Veterinary Clinic", "22 Elm Ave, Boston, MA 02108", "care@pinecrestvet.com", "(617) 555-0104"),
    ("smith_sons", "Smith & Sons Hardware", "18 Harbor Rd, Madison, WI 53703", "sales@smithsonshardware.com", "(608) 555-0119"),
    ("orchard", "Orchard Street Dental", "905 Granville St, Vancouver, BC V6Z 1L3", "hello@orcharddental.ca", "(604) 555-0181"),
    ("keystone", "Keystone Plumbing Co", "2211 N Clark St, Chicago, IL 60614", "service@keystoneplumbing.com", "(312) 555-0126"),
    ("keystone_lincoln", "Keystone Plumbing Company", "2450 N Lincoln Ave, Chicago, IL 60614", "service@keystoneplumbing.com", "(312) 555-0126"),
    ("maple_leaf", "Maple Leaf Movers Ltd", "16 Rue du Port, Quebec, QC G1K 4E3", "info@mapleleafmovers.ca", "(418) 555-0143"),
    ("lakeside", "Lakeside Yoga Studio", "742 Maple Terrace, Springfield, IL 62701", "namaste@lakesideyoga.com", "(217) 555-0166"),
    ("cobalt", "Cobalt Analytics Inc", "88 Harbor Blvd Suite 400, Long Beach, CA 90802", "hello@cobaltanalytics.io", "(562) 555-0138"),
    ("redwood", "Redwood Family Dental", "1600 Grand Ave NW, Washington, DC 20001", "smile@redwooddental.com", "(202) 555-0129"),
    ("tidewater", "Tidewater Marine Supply", "31 Harbor St, Norfolk, VA 23510", "orders@tidewatermarine.com", "(757) 555-0170"),
    ("evergreen", "Evergreen Landscaping", "45 Kingsway, Burnaby, BC V5H 2A9", "info@evergreenlandscaping.ca", "(604) 555-0152"),
    ("granite", "Granite State Insurance Agency", "9 Market Sq, Portsmouth, NH 03801", "agents@granitestateins.com", "(603) 555-0111"),
    # Entities added for this study.
    ("pioneer_chicago", "Pioneer Print Shop", "1020 W Lake St, Chicago, IL 60607", "chicago@pioneerprint.com", "(312) 555-0131"),
    ("pioneer_evanston", "Pioneer Print Shop", "1602 Sherman Ave, Evanston, IL 60201", "evanston@pioneerprint.com", "(847) 555-0131"),
    ("atlas_movers", "Atlas Moving & Storage Inc", "5 Depot Rd, Albany, NY 12205", "moves@atlasmoving.com", "(518) 555-0149"),
    ("atlas_storage", "Atlas Self Storage LLC", "5 Depot Rd, Albany, NY 12205", "units@atlasselfstorage.com", "(518) 555-0150"),
    ("brightside_pediatrics", "Brightside Pediatrics", "700 Elm St Ste 210, Dallas, TX 75202", "office@brightsidepeds.com", "(214) 555-0161"),
    ("brightside_dental", "Brightside Dental", "700 Elm St Ste 305, Dallas, TX 75202", "smile@brightsidedental.com", "(214) 555-0162"),
    ("coastal_cafe", "Coastal Cafe", "12 Ocean Ave, Santa Cruz, CA 95060", "hi@coastalcafe.com", "(831) 555-0175"),
    ("north_star", "North Star Technologies Inc", "2600 Tech Pkwy, Raleigh, NC 27606", "info@northstartech.com", "(919) 555-0183"),
    ("greenleaf", "Greenleaf Garden Center", "450 County Rd 12, Ames, IA 50010", "shop@greenleafgarden.com", "(515) 555-0114"),
    ("st_louis_bread", "Saint Louis Bread Company", "88 Market St, St. Louis, MO 63101", "hello@stlbread.com", "(314) 555-0127"),
    ("liberty_group", "Liberty Insurance Group", "300 Main St, Hartford, CT 06103", "claims@libertyig.com", "(860) 555-0135"),
    ("liberty_agency", "Liberty Insurance Agency", "300 Main St Ste 400, Hartford, CT 06103", "agents@libertyia.com", "(860) 555-0136"),
)

# (entity, corruption named in the record, name, address, email, phone)
DUPLICATES = (
    ("acme", "upper_case_suffix_and_expanded_address", "ACME WIDGETS INC", "12 North Main Street Suite 4, Springfield, IL 62704", "Orders@AcmeWidgets.com", "217.555.0141"),
    ("acme", "long_suffix_periods_and_missing_email", "Acme Widgets, Incorporated", "12 N. Main St., Ste. 4, Springfield IL 62704", "", "(217) 555-0141"),
    ("northwind", "suffix_dropped_and_missing_phone", "Northwind Traders", "845 Oak Ave, Portland, OR 97205", "info@northwindtraders.com", ""),
    ("bluebird_denver", "split_word_and_street_type", "Blue Bird Bakery", "77 Cedar Lane, Denver, CO 80202", "hello@bluebirdbakery.com", "303-555-0187"),
    ("summit_dental", "abbreviated_word_and_street_type", "Summit Dental Grp", "3100 Lakeview Drive, Austin, TX 78701", "frontdesk@summitdental.com", "(512) 555-0133"),
    ("globex", "short_suffix_and_expanded_street_type", "Globex Corp.", "1200 Industrial Parkway, Columbus, OH 43215", "contact@globex.com", "614-555-0158"),
    ("riverbend", "expanded_street_and_missing_email", "Riverbend Books", "58 Bay Street, Toronto, ON M5J 2N8", "", "416 555 0122"),
    ("riverbend", "typo_and_postal_code_without_space", "Riverbnd Books", "58 Bay St., Toronto ON M5J2N8", "shop@riverbendbooks.ca", ""),
    ("pinecrest", "upper_case_email_and_international_phone", "Pinecrest Veterinary Clinic", "22 Elm Avenue, Boston, MA 02108", "CARE@PINECRESTVET.COM", "+1 617 555 0104"),
    ("smith_sons", "ampersand_as_word", "Smith and Sons Hardware", "18 Harbor Road, Madison, WI 53703", "sales@smithsonshardware.com", "608-555-0119"),
    ("keystone", "long_suffix_and_expanded_address", "Keystone Plumbing Company", "2211 North Clark Street, Chicago, IL 60614", "", "(312) 555-0126"),
    ("cobalt", "suffix_dropped_and_missing_phone", "Cobalt Analytics", "88 Harbor Blvd Ste 400, Long Beach, CA 90802", "hello@cobaltanalytics.io", ""),
    ("cobalt", "upper_case_and_expanded_address", "COBALT ANALYTICS INC.", "88 Harbor Boulevard, Suite 400, Long Beach, CA 90802", "", "562-555-0138"),
    ("tidewater", "typo_in_name", "Tidewater Marine Suply", "31 Harbor St, Norfolk, VA 23510", "orders@tidewatermarine.com", "(757) 555-0170"),
    ("granite", "abbreviated_word_and_missing_phone", "Granite State Insurance Agcy", "9 Market Square, Portsmouth, NH 03801", "agents@granitestateins.com", ""),
    # Duplicates added for this study.
    ("acme", "suite_omitted_and_extension", "Acme Widgets Inc", "12 N Main St, Springfield, IL 62704", "orders@acmewidgets.com", "(217) 555-0141 ext 3"),
    ("pioneer_chicago", "upper_case_name_and_expanded_address", "PIONEER PRINT SHOP", "1020 West Lake Street, Chicago, IL 60607", "Chicago@PioneerPrint.com", "312-555-0131"),
    ("atlas_movers", "ampersand_as_word_and_suffix_dropped", "Atlas Moving and Storage", "5 Depot Road, Albany, NY 12205", "", "(518) 555-0149"),
    ("brightside_pediatrics", "legal_suffix_added_and_missing_phone", "Brightside Pediatrics PLLC", "700 Elm Street Suite 210, Dallas, TX 75202", "office@brightsidepeds.com", ""),
    ("coastal_cafe", "accent_and_upper_case_email", "Coastal Caf\u00e9", "12 Ocean Avenue, Santa Cruz, CA 95060", "HI@COASTALCAFE.COM", "831.555.0175"),
    ("north_star", "joined_words_and_zip_plus_four", "Northstar Technologies", "2600 Tech Parkway, Raleigh, NC 27606-1234", "info@northstartech.com", ""),
    ("north_star", "shortened_word_and_international_phone", "North Star Tech Inc", "2600 Tech Pkwy, Raleigh NC 27606", "", "+1 919 555 0183"),
    ("greenleaf", "split_word_and_abbreviations", "Green Leaf Garden Ctr", "450 County Road 12, Ames, IA 50010", "shop@greenleafgarden.com", "(515) 555-0114"),
    ("st_louis_bread", "saint_abbreviated_and_short_suffix", "St. Louis Bread Co.", "88 Market Street, Saint Louis, MO 63101", "hello@stlbread.com", "314-555-0127"),
)

HARD_NEGATIVE_ENTITY_PAIRS = (
    ("bluebird_denver", "bluebird_seattle", "same_name_other_location"),
    ("summit_dental", "summit_rental", "one_letter_name_difference_nearby_address"),
    ("harbor_light", "crestline", "shared_floor_mailbox_and_switchboard"),
    ("pioneer_chicago", "pioneer_evanston", "same_name_other_location"),
    ("atlas_movers", "atlas_storage", "shared_address_different_companies"),
    ("brightside_pediatrics", "brightside_dental", "same_building_other_suite_other_company"),
)
AMBIGUOUS_ENTITY_PAIRS = (
    ("globex", "globex_logistics", "related_names_same_address_and_phone"),
    ("keystone", "keystone_lincoln", "same_company_name_phone_and_email_other_address"),
    ("liberty_group", "liberty_agency", "similar_names_same_building"),
)


def duplicate_rows(rng):
    records = [dict(entity=key, corruption="original", name=name, address=address,
                    email=email, phone=phone)
               for key, name, address, email, phone in ENTITIES]
    records += [dict(entity=key, corruption=corruption, name=name, address=address,
                     email=email, phone=phone)
                for key, corruption, name, address, email, phone in DUPLICATES]
    rng.shuffle(records)
    for number, record in enumerate(records, start=1):
        record["id"] = str(number)
    by_entity = {}
    for record in records:
        by_entity.setdefault(record["entity"], []).append(record["id"])

    def pairs_between(ids_a, ids_b):
        return sorted({tuple(sorted((a, b), key=int)) for a in ids_a for b in ids_b if a != b})

    duplicate_pairs = []
    for ids in by_entity.values():
        duplicate_pairs += pairs_between(ids, ids)
    duplicate_pairs = sorted(set(duplicate_pairs), key=lambda p: (int(p[0]), int(p[1])))
    hard_negative = []
    for left, right, reason in HARD_NEGATIVE_ENTITY_PAIRS:
        for pair in pairs_between(by_entity[left], by_entity[right]):
            hard_negative.append(dict(pair=list(pair), reason=reason))
    ambiguous = []
    for left, right, reason in AMBIGUOUS_ENTITY_PAIRS:
        for pair in pairs_between(by_entity[left], by_entity[right]):
            ambiguous.append(dict(pair=list(pair), reason=reason))
    return records, [list(p) for p in duplicate_pairs], hard_negative, ambiguous


DUPLICATE_TASK = """Task: find duplicate records. The table lists customer companies with the columns `id`, `name`, `address`, `email` and `phone`. Some companies were entered more than once, written differently.

Write `output.csv` with the columns `id_a`, `id_b` and `decision`, one row for each pair of rows that may be the same company at the same location, with the smaller id in `id_a`:
- Set `decision` to `same` when you are certain that the two rows are the same company at the same location.
- Set `decision` to `review` when the two rows might be the same company at the same location but you cannot be certain.
- Do not list a pair that is two different companies, or the same company at two different locations.
- When three or more rows are the same company at the same location, list every pair among them."""


# ---------------------------------------------------------------------------
# Family 5: name capitalisation


def name_rows(rng):
    rows = []

    def add(case_type, variant, value, kind, expected, review):
        rows.append(value_row(case_type, variant, value, kind, expected, review))

    # People written entirely in capital letters or entirely in small letters.
    for value, expected, case_type in (
            ("MARY O'BRIEN", "Mary O'Brien", "apostrophe_prefix_o"),
            ("SEAN O'NEILL", "Sean O'Neill", "apostrophe_prefix_o"),
            ("D'ARCY FLYNN", "D'Arcy Flynn", "apostrophe_prefix_d"),
            ("JOHN MCDONALD", "John McDonald", "mc_prefix"),
            ("KATE MCCARTHY", "Kate McCarthy", "mc_prefix"),
            ("LEE-ANN SMITH-JONES", "Lee-Ann Smith-Jones", "hyphenated_name"),
            ("HENRY WALLACE III", "Henry Wallace III", "roman_numeral"),
            ("DAVID OKAFOR JR.", "David Okafor Jr.", "generational_suffix"),
            ("DR. AMY CHEN", "Dr. Amy Chen", "title_with_period"),
            ("JAMES T. MORROW", "James T. Morrow", "middle_initial"),
            ("\u00c9LODIE MARCHAND", "\u00c9lodie Marchand", "accented_capital"),
            ("S\u00d8REN KJ\u00c6R", "S\u00f8ren Kj\u00e6r", "letters_outside_ascii"),
            ("MACY GRAHAM", "Macy Graham", "mac_letters_in_a_first_name"),
            ("maria gonzalez", "Maria Gonzalez", "all_small_letters"),
            ("o'connor, patrick", "O'Connor, Patrick", "all_small_letters_surname_first")):
        add(case_type, "person", value, "change", expected, "no")
    # Companies written entirely in capital letters or entirely in small letters.
    for value, expected, case_type in (
            ("ACME WIDGETS INC", "Acme Widgets Inc", "legal_form_inc"),
            ("NORTHWIND TRADERS LLC", "Northwind Traders LLC", "legal_form_llc"),
            ("HARBOR LIGHT LEGAL PC", "Harbor Light Legal PC", "legal_form_pc"),
            ("GLOBEX CORPORATION OF AMERICA", "Globex Corporation of America", "minor_word_of"),
            ("SMITH AND SONS HARDWARE", "Smith and Sons Hardware", "minor_word_and"),
            ("THE CEDAR ROOM", "The Cedar Room", "minor_word_first"),
            ("FOR PAWS PET CARE", "For Paws Pet Care", "minor_word_first"),
            ("BAY AREA HVAC SERVICES", "Bay Area HVAC Services", "acronym"),
            ("JKL CONSULTING GROUP", "JKL Consulting Group", "initialism_without_vowels"),
            ("QRS LOGISTICS", "QRS Logistics", "initialism_without_vowels"),
            ("AJ HOME SERVICES", "AJ Home Services", "initials_two_letters"),
            ("U.S. FREIGHT BROKERS", "U.S. Freight Brokers", "initialism_with_periods"),
            ("3RD STREET DELI", "3rd Street Deli", "ordinal_number"),
            ("21ST CENTURY PLUMBING", "21st Century Plumbing", "ordinal_number"),
            ("A-1 AUTO REPAIR", "A-1 Auto Repair", "letter_and_digit_token"),
            ("E-Z STORAGE", "E-Z Storage", "single_letters_joined"),
            ("O'MALLEY'S PUB", "O'Malley's Pub", "possessive_after_prefix"),
            ("BOB'S BIKE SHOP", "Bob's Bike Shop", "possessive"),
            ("MCMASTER TOOL CO", "McMaster Tool Co", "mc_prefix"),
            ("MACHINE TOOLS OF OHIO INC", "Machine Tools of Ohio Inc", "mac_letters_in_a_word"),
            ("MACK'S DINER", "Mack's Diner", "mac_letters_in_a_word"),
            ("TOWN & COUNTRY REALTY", "Town & Country Realty", "ampersand"),
            ("blue river bakery", "Blue River Bakery", "all_small_letters")):
        add(case_type, "company", value, "change", expected, "no")
    # Values that already mix capital and small letters stay exactly as written.
    for value, variant in (("Acme Widgets", "standard"),
                           ("DataBridge Analytics", "inner_capital"),
                           ("eZone Games", "small_first_letter"),
                           ("McDonald Farms", "mc_prefix"),
                           ("van Houten Bakery", "particle_first"),
                           ("amy CHEN", "inconsistent_but_mixed")):
        add("mixed_case_kept", variant, value, "keep", value, "no")
    for value, variant in (("", "empty"), ("n/a", "n_a"), ("-", "dash")):
        add("null_marker", variant, value, "keep", value, "no")
    # The standard capitalisation cannot be known from the value alone.
    for value, case_type in (("ANGUS MACDONALD", "hold_mac_prefix"),
                             ("FIONA MACKENZIE", "hold_mac_prefix"),
                             ("ANNA VAN DER BERG", "hold_name_particle"),
                             ("JOS\u00c9 DE LA CRUZ", "hold_name_particle"),
                             ("MARIA DI NAPOLI", "hold_name_particle"),
                             ("JAMAL AL-SAYED", "hold_name_particle")):
        add(case_type, "person", value, "hold", value, "yes")
    rng.shuffle(rows)
    return rows


NAME_TASK = """Task: fix the capitalisation in the `name` column. The table has the columns `id` and `name`. Each value is the name of a person or of a company. Some values were typed entirely in capital letters or entirely in small letters.

Write `output.csv` with the columns `id`, `name` and `review`, one row for each input row, in any order:
- Rewrite a value that is written entirely in capital letters or entirely in small letters in the standard capitalisation of English names: each word starts with a capital letter and continues in small letters, except where the standard written form of that word differs, for example `McDonald`, `O'Brien`, `IBM`, `LLC`, `of` inside a company name, or `3rd`.
- Keep every other character exactly as it is: spaces, punctuation, accents and word order.
- Keep a value that already mixes capital and small letters exactly as it is, with `review` set to `no`.
- Leave an empty value or a null marker such as `n/a` exactly as it is, with `review` set to `no`.
- When the standard capitalisation of a word in the value cannot be known from the value alone, for example `MACDONALD`, which is written both `MacDonald` and `Macdonald`, do not guess: copy the input value exactly as it is and set `review` to `yes`.
- Otherwise set `review` to `no`."""


# ---------------------------------------------------------------------------
# Family 6: website addresses
#
# Host names are reserved by RFC 2606 (example.com, example.org, example.net
# and the .example top level domain); 192.0.2.10 is in the RFC 5737
# documentation network.


def website_rows(rng):
    rows = []

    def add(case_type, variant, value, kind, expected, review):
        rows.append(value_row(case_type, variant, value, kind, expected, review))

    for value, expected, case_type, variant in (
            ("Example.COM", "https://example.com", "scheme_added", "mixed_case_host"),
            ("www.Example.org/About/", "https://www.example.org/About", "scheme_added",
             "www_and_trailing_slash"),
            ("example.com/path?Ref=ABC#Top", "https://example.com/path?Ref=ABC#Top",
             "scheme_added", "query_and_fragment_kept"),
            ("blog.example.net/2026/09/Post-Title/",
             "https://blog.example.net/2026/09/Post-Title", "scheme_added", "dated_path"),
            ("HTTP://WWW.EXAMPLE.NET/INDEX.HTML", "http://www.example.net/INDEX.HTML",
             "case_of_scheme_and_host", "upper_case_path_kept"),
            ("Https://Example.Com/About-Us/", "https://example.com/About-Us",
             "case_of_scheme_and_host", "title_case"),
            ("https://Shop.Example.com/Products/Blue-Widget/",
             "https://shop.example.com/Products/Blue-Widget", "case_of_scheme_and_host",
             "subdomain_path_case_kept"),
            ("http://Example.org/Search?Q=Red%20Shoes", "http://example.org/Search?Q=Red%20Shoes",
             "case_of_scheme_and_host", "percent_encoding_kept"),
            ("https://example.com/", "https://example.com", "trailing_slash", "root_path"),
            ("https://example.com/?q=Widgets", "https://example.com?q=Widgets", "trailing_slash",
             "before_query"),
            ("https://example.com/docs/#Intro", "https://example.com/docs#Intro", "trailing_slash",
             "before_fragment"),
            ("https://acme-widgets.example/Catalog/", "https://acme-widgets.example/Catalog",
             "trailing_slash", "reserved_top_level_domain"),
            ("http://example.com:80/Store", "http://example.com/Store", "default_port",
             "http_80"),
            ("https://example.com:443/", "https://example.com", "default_port", "https_443"),
            ("HTTPS://EXAMPLE.ORG:443/Blog/", "https://example.org/Blog", "default_port",
             "with_case_and_trailing_slash"),
            ("https://Example.com:8443/Portal/", "https://example.com:8443/Portal",
             "other_port_kept", "with_case_and_trailing_slash"),
            (" https://example.net ", "https://example.net", "surrounding_spaces", "both_ends")):
        add(case_type, variant, value, "change", expected, "no")
    for value, case_type, variant in (
            ("https://example.com", "already_standard", "root"),
            ("https://www.example.org/About", "already_standard", "www_kept"),
            ("https://example.com/Docs/Guide", "already_standard", "path_case"),
            ("http://example.com:8080/Admin", "other_port_kept", "http_8080"),
            ("http://example.org:443/Legacy", "other_port_kept", "port_443_with_http"),
            ("http://192.0.2.10/Status", "already_standard", "ip_address_host")):
        add(case_type, variant, value, "keep", value, "no")
    for value, variant in (("", "empty"), ("n/a", "n_a"), ("-", "dash")):
        add("null_marker", variant, value, "keep", value, "no")
    for value, case_type, variant in (
            ("https://exa mple.com", "hold_invalid", "space_inside"),
            ("https://example..com", "hold_invalid", "empty_label"),
            ("https://-example.com", "hold_invalid", "label_starts_with_hyphen"),
            ("www.example.com, www.example.org", "hold_not_one_address", "two_addresses"),
            ("mailto:info@example.com", "hold_not_one_address", "email_address"),
            ("see our facebook page", "hold_not_one_address", "text")):
        add(case_type, variant, value, "hold", value, "yes")
    rng.shuffle(rows)
    return rows


WEBSITE_TASK = """Task: clean the `website` column. The table has the columns `id` and `website`.

Write `output.csv` with the columns `id`, `website` and `review`, one row for each input row, in any order:
- Write each web address in one standard form: the scheme and the host name in small letters, because they are not case-sensitive; no default port (`:80` for `http`, `:443` for `https`); and no slash at the end of the path, so `https://example.com/` becomes `https://example.com`. Keep the rest of the path, the query and the fragment exactly as written, because they can be case-sensitive.
- When an address has no scheme, add `https://`.
- Keep `www.` when it is written, and do not add it.
- Leave an empty value or a null marker such as `n/a` exactly as it is, with `review` set to `no`.
- When a value is not one single web address, or it cannot be a valid address as written, for example because it has a space inside it or its host name is not valid, do not guess: copy the input value exactly as it is and set `review` to `yes`.
- Otherwise set `review` to `no`."""


STEP_RULES = """Rules for this step:
- Read `input.csv` and write `output.csv` in your working folder, as a comma-separated file with a header row and exactly the columns named above.
- Do not change `input.csv`.
- Work only inside your working folder. Python 3 with its standard library is available; no other Python packages are installed.
- When `output.csv` is complete, reply with the single word DONE."""


def step_prompt(task_text):
    return ("You are doing one data cleaning step. Your working folder holds the file `input.csv`.\n\n"
            + task_text + "\n\n" + STEP_RULES + "\n")


# ---------------------------------------------------------------------------
# Known-wrong outputs that the scorer must reject


def known_wrong_value_family(header, rows):
    """Copied input, all-null and shuffled outputs for a one-value family.

    The copied input is the output of a step that changed nothing and flagged
    nothing: every value as it came in, with `review` set to `no`.
    """
    copied = csv_text(header, [(r["id"], r["input"], "no") for r in rows])
    all_null = csv_text(header, [(r["id"],) + ("",) * (len(header) - 1) for r in rows])
    values = [r["expected"] for r in rows]
    reviews = [r["review"] for r in rows]
    order = list(range(len(rows)))
    random.Random(SEED + 1).shuffle(order)
    shuffled = csv_text(header, [(r["id"], values[order[i]], reviews[order[i]])
                                 for i, r in enumerate(rows)])
    return {"copied-input.csv": copied, "all-null.csv": all_null, "shuffled.csv": shuffled}


def known_wrong_names(rows):
    """The value family set, plus a generic title case of every value."""
    header = ("id", "name", "review")
    wrong = known_wrong_value_family(header, rows)
    wrong["python-title-case.csv"] = csv_text(header, [(r["id"], r["input"].title(), "no")
                                                       for r in rows])
    return wrong


def known_wrong_websites(rows):
    """The value family set, plus an output that writes every whole address in small letters."""
    header = ("id", "website", "review")
    wrong = known_wrong_value_family(header, rows)
    lowered = []
    for r in rows:
        value = r["expected"] if r["kind"] != "hold" else r["input"]
        lowered.append((r["id"], value.lower(), r["review"]))
    wrong["whole-address-lower-case.csv"] = csv_text(header, lowered)
    return wrong


def known_wrong_addresses(rows):
    header = ("id",) + ADDRESS_PARTS + ("review",)
    copied = csv_text(header, [(r["id"], "", r["input"], "", "", "", "", "", "no") for r in rows])
    all_null = csv_text(header, [(r["id"],) + ("",) * (len(header) - 1) for r in rows])
    order = list(range(len(rows)))
    random.Random(SEED + 1).shuffle(order)
    shuffled_rows = []
    for index, row in enumerate(rows):
        other = rows[order[index]]
        shuffled_rows.append((row["id"],) + tuple(other["expected"][p] for p in ADDRESS_PARTS)
                             + (other["review"],))
    return {"copied-input.csv": copied, "all-null.csv": all_null,
            "shuffled.csv": csv_text(header, shuffled_rows)}


def known_wrong_duplicates(records, duplicate_pairs):
    header = ("id_a", "id_b", "decision")
    copied = csv_text(("id", "name", "address", "email", "phone"),
                      [(r["id"], r["name"], r["address"], r["email"], r["phone"]) for r in records])
    all_null = csv_text(header, [("", "", "") for _ in duplicate_pairs])
    ids = [r["id"] for r in records]
    permuted = list(ids)
    random.Random(SEED + 1).shuffle(permuted)
    mapping = dict(zip(ids, permuted))
    shuffled_pairs = sorted({tuple(sorted((mapping[a], mapping[b]), key=int))
                             for a, b in duplicate_pairs}, key=lambda p: (int(p[0]), int(p[1])))
    shuffled = csv_text(header, [(a, b, "same") for a, b in shuffled_pairs])
    every_pair = [tuple(sorted((a, b), key=int)) + ("same",)
                  for i, a in enumerate(ids) for b in ids[i + 1:]]
    over_merge = csv_text(header, sorted(every_pair, key=lambda p: (int(p[0]), int(p[1]))))
    return {"copied-input.csv": copied, "all-null.csv": all_null, "shuffled.csv": shuffled,
            "every-pair-same.csv": over_merge}


# ---------------------------------------------------------------------------
# Assembly


def numbered(rows):
    for number, row in enumerate(rows, start=1):
        row["id"] = str(number)
    return rows


def value_family(task, column, rows, known_wrong):
    header = ("id", column)
    return dict(task=task, input_header=header,
                input_rows=[(r["id"], r["input"]) for r in rows],
                truth=dict(output_columns=["id", column, "review"], value_column=column, rows=rows),
                known_wrong=known_wrong)


def build():
    """Return {relative path: text} for every population file."""
    rng = random.Random(SEED)
    families = {}
    phones = phone_rows(rng)
    rng.shuffle(phones)
    phones = numbered(phones)
    families["phones"] = value_family(PHONE_TASK, "phone", phones,
                                      known_wrong_value_family(("id", "phone", "review"), phones))
    emails = numbered(email_rows(rng))
    families["emails"] = value_family(EMAIL_TASK, "email", emails,
                                      known_wrong_value_family(("id", "email", "review"), emails))
    addresses = numbered(address_rows(rng))
    families["addresses"] = dict(
        task=ADDRESS_TASK, input_header=("id", "address"),
        input_rows=[(r["id"], r["input"]) for r in addresses],
        truth=dict(output_columns=["id", *ADDRESS_PARTS, "review"], parts=list(ADDRESS_PARTS),
                   rows=addresses),
        known_wrong=known_wrong_addresses(addresses))
    records, duplicate_pairs, hard_negative, ambiguous = duplicate_rows(rng)
    families["duplicates"] = dict(
        task=DUPLICATE_TASK, input_header=("id", "name", "address", "email", "phone"),
        input_rows=[(r["id"], r["name"], r["address"], r["email"], r["phone"]) for r in records],
        truth=dict(output_columns=["id_a", "id_b", "decision"], rows=records,
                   duplicate_pairs=duplicate_pairs, hard_negative_pairs=hard_negative,
                   ambiguous_pairs=ambiguous),
        known_wrong=known_wrong_duplicates(records, duplicate_pairs))
    names = numbered(name_rows(rng))
    families["names"] = value_family(NAME_TASK, "name", names, known_wrong_names(names))
    websites = numbered(website_rows(rng))
    families["websites"] = value_family(WEBSITE_TASK, "website", websites,
                                        known_wrong_websites(websites))

    files = {}
    manifest = {"record_type": RECORD_TYPE, "seed": SEED, "families": {}}
    for name in FAMILIES:
        family = families[name]
        prompt = step_prompt(family["task"])
        input_text = csv_text(family["input_header"], family["input_rows"])
        truth = dict(record_type="overnight_truth/v1", family=name, **family["truth"])
        truth_text = json_text(truth)
        files[f"{name}/input.csv"] = input_text
        files[f"{name}/truth.json"] = truth_text
        files[f"{name}/prompt.txt"] = prompt
        for fixture, text in family["known_wrong"].items():
            files[f"{name}/known-wrong/{fixture}"] = text
        rows = family["truth"]["rows"]
        kinds = {}
        for row in rows:
            kinds[row.get("kind", "record")] = kinds.get(row.get("kind", "record"), 0) + 1
        entry = {
            "rows": len(family["input_rows"]),
            "rows_by_kind": dict(sorted(kinds.items())),
            "input_sha256": sha256_text(input_text),
            "truth_sha256": sha256_text(truth_text),
            "prompt_sha256": sha256_text(prompt),
            "known_wrong_sha256": {fixture: sha256_text(text)
                                   for fixture, text in sorted(family["known_wrong"].items())},
        }
        if name == "duplicates":
            entry.update(duplicate_pairs=len(family["truth"]["duplicate_pairs"]),
                         hard_negative_pairs=len(family["truth"]["hard_negative_pairs"]),
                         ambiguous_pairs=len(family["truth"]["ambiguous_pairs"]))
        manifest["families"][name] = entry
    files["manifest.json"] = json_text(manifest)
    return files


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true",
                        help="compare with the written files instead of writing")
    args = parser.parse_args(argv)
    files = build()
    stale = []
    for relative, text in sorted(files.items()):
        path = HERE / relative
        if args.check:
            if not path.is_file() or path.read_text(encoding="utf-8") != text:
                stale.append(relative)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
    if args.check:
        for relative in stale:
            print(f"differs: {relative}")
        return 1 if stale else 0
    print(json.dumps(json.loads(files["manifest.json"]), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
