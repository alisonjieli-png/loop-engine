"""Generate the frozen population for the data cleanup demonstration.

The four task families are phone numbers, email addresses, address lines and
duplicate company records. Every row starts from a clean truth that this file
declares, and a named corruption turns it into the dirty input value. The
seed only chooses fictional line numbers and the row order, so the same seed
always writes the same bytes.

All data is synthetic. Telephone numbers use ranges reserved for fiction:
555-0100 to 555-0199 in North America, and the Ofcom drama ranges in the
United Kingdom. People, companies, email addresses and street numbers are
invented. Street, city and postal code formats follow real conventions.

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
SEED = 20260922
RECORD_TYPE = "data_cleanup_population/v1"


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


# ---------------------------------------------------------------------------
# Family 1: phone numbers
#
# Clean truth: a country, a national number and an optional extension.
# Expected outcome kinds: change, keep, hold, alternatives.

NANP_AREAS = ("415", "212", "312", "617", "206", "303", "512", "416", "604", "514", "613")
UK_DRAMA = (
    ("20", "7946 0", "London"),
    ("117", "496 0", "Bristol"),
    ("161", "496 0", "Manchester"),
    ("121", "496 0", "Birmingham"),
)


def phone_rows(rng):
    lines = LineNumbers(rng)
    areas = list(NANP_AREAS)
    rows = []

    def area():
        return rng.choice(areas)

    def nanp():
        a, line = area(), lines.take()
        return a, line, f"+1{a}555{line}"

    # Formatted national numbers.
    templates = (
        ("({a}) 555-{l}", "parentheses_and_dash"),
        ("{a}-555-{l}", "dashes"),
        ("{a}.555.{l}", "dots"),
        ("{a}555{l}", "ten_bare_digits"),
        ("{a} 555 {l}", "spaces"),
        (" {a}-555-{l} ", "surrounding_spaces"),
        ("{a}\u2013555\u2013{l}", "unicode_dashes"),
    )
    for template, variant in templates:
        a, line, e164 = nanp()
        rows.append(dict(case_type="national_number_formatted", variant=variant,
                         input=template.format(a=a, l=line), kind="change",
                         expected=e164, review="no"))
    # National numbers that already carry country code 1.
    templates = (
        ("1-{a}-555-{l}", "one_dash"),
        ("+1 {a} 555 {l}", "plus_one_spaces"),
        ("1 ({a}) 555-{l}", "one_parentheses"),
        ("+1-{a}-555-{l}", "plus_one_dashes"),
        ("1{a}555{l}", "eleven_bare_digits"),
    )
    for template, variant in templates:
        a, line, e164 = nanp()
        rows.append(dict(case_type="country_code_one_present", variant=variant,
                         input=template.format(a=a, l=line), kind="change",
                         expected=e164, review="no"))
    # Already correct values.
    for variant in ("north_american", "canadian"):
        a = "613" if variant == "canadian" else area()
        line = lines.take()
        value = f"+1{a}555{line}"
        rows.append(dict(case_type="already_e164", variant=variant, input=value,
                         kind="keep", expected=value, review="no"))
    for variant, (code, prefix) in (("uk_london", ("20", "79460")),
                                     ("uk_mobile", ("7700", "900"))):
        tail = lines.take()[1:] if variant == "uk_london" else lines.take()[1:]
        value = f"+44{code}{prefix}{tail}"
        rows.append(dict(case_type="already_e164", variant=variant, input=value,
                         kind="keep", expected=value, review="no"))
    # Extensions.
    templates = (
        ("{a}-555-{l} ext. {e}", "ext_period"),
        ("({a}) 555-{l} x{e}", "x_marker"),
        ("{a}.555.{l} extension {e}", "extension_word"),
    )
    for (template, variant), ext in zip(templates, ("12", "305", "7")):
        a, line, e164 = nanp()
        rows.append(dict(case_type="extension", variant=variant,
                         input=template.format(a=a, l=line, e=ext), kind="change",
                         expected=f"{e164} ext {ext}", review="no"))
    # International numbers written with a plus sign.
    london_tail, mobile_tail, manchester_tail = (lines.take()[1:] for _ in range(3))
    for value, expected, variant in (
            (f"+44 20 7946 0{london_tail}", f"+442079460{london_tail}", "uk_london"),
            (f"+44 7700 900{mobile_tail}", f"+447700900{mobile_tail}", "uk_mobile"),
            (f"+44 161 496 0{manchester_tail}", f"+441614960{manchester_tail}", "uk_manchester")):
        rows.append(dict(case_type="international_with_plus", variant=variant, input=value,
                         kind="change", expected=expected, review="no"))
    # The United Kingdom trunk prefix written in parentheses is never dialled
    # from abroad, so it is dropped from the E.164 form.
    london_tail, bristol_tail = (lines.take()[1:] for _ in range(2))
    for value, expected, variant in (
            (f"+44 (0)20 7946 0{london_tail}", f"+442079460{london_tail}", "uk_london"),
            (f"+44 (0) 117 496 0{bristol_tail}", f"+441174960{bristol_tail}", "uk_bristol")):
        rows.append(dict(case_type="trunk_prefix_in_parentheses", variant=variant,
                         input=value, kind="change", expected=expected, review="no"))
    # 011 is the international call prefix used from the United States and Canada.
    london_tail, mobile_tail = (lines.take()[1:] for _ in range(2))
    for value, expected, variant in (
            (f"011 44 20 7946 0{london_tail}", f"+442079460{london_tail}", "uk_london"),
            (f"011-44-7700-900{mobile_tail}", f"+447700900{mobile_tail}", "uk_mobile")):
        rows.append(dict(case_type="north_american_exit_prefix", variant=variant,
                         input=value, kind="change", expected=expected, review="no"))
    # Values that must be held: the correct number cannot be known.
    for value, variant in ((f"555-{lines.take()}", "seven_digits_dash"),
                           (f"555 {lines.take()}", "seven_digits_space")):
        rows.append(dict(case_type="hold_no_area_code", variant=variant, input=value,
                         kind="hold", expected=value, review="yes"))
    a = area()
    first, second = lines.take(), lines.take()
    value = f"{a}-555-{first} / {a}-555-{second}"
    rows.append(dict(case_type="hold_two_numbers", variant="slash", input=value,
                     kind="hold", expected=value, review="yes"))
    a = area()
    value = f"{a}-555-{lines.take()[:3]}"
    rows.append(dict(case_type="hold_wrong_digit_count", variant="nine_digits", input=value,
                     kind="hold", expected=value, review="yes"))
    a = area()
    value = f"{a}-555-{lines.take()}9"
    rows.append(dict(case_type="hold_wrong_digit_count", variant="eleven_digits_no_leading_one",
                     input=value, kind="hold", expected=value, review="yes"))
    # North American area codes never start with 0 or 1.
    value = f"(015) 555-{lines.take()}"
    rows.append(dict(case_type="hold_invalid_area_code", variant="area_code_starts_with_zero",
                     input=value, kind="hold", expected=value, review="yes"))
    # +41 is Switzerland, whose national numbers have nine digits; this one has eight.
    value = f"+415 555 {lines.take()}"
    rows.append(dict(case_type="hold_plus_with_impossible_length", variant="plus_41_eight_digits",
                     input=value, kind="hold", expected=value, review="yes"))
    # Null markers stay as they are.
    for value, variant in (("", "empty"), ("n/a", "n_a"), ("unknown", "unknown"), ("-", "dash")):
        rows.append(dict(case_type="null_marker", variant=variant, input=value, kind="keep",
                         expected=value, review="no"))
    # A letter O typed for a zero: holding it and repairing it are both accepted.
    a, line = area(), lines.take()
    value = f"{a}-555-{line[:2]}O{line[3]}"
    fixed = f"+1{a}555{line[:2]}0{line[3]}"
    rows.append(dict(case_type="letter_o_for_zero", variant="ocr_like", input=value,
                     kind="alternatives", expected=fixed, review="no",
                     accepted=[[value, "yes"], [fixed, "no"]]))
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
        rows.append(dict(case_type=case_type, variant=variant, input=value, kind=kind,
                         expected=expected, review=review))

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
    add("united_kingdom_flat_before_number", "Flat 3, 22 Queen Street, Cardiff CF10 2BU, United Kingdom",
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
    # Held rows: which words belong to which part cannot be decided with certainty.
    add("hold_street_or_city_boundary", "12 Main St West Springfield MA 01089",
        ("", "", "", "", "", "", ""), review="yes")
    add("hold_intersection", "Corner of Main St and 2nd Ave, Springfield, IL",
        ("", "", "", "", "", "", ""), review="yes")
    add("hold_not_an_address", "see notes",
        ("", "", "", "", "", "", ""), review="yes")
    add("hold_street_without_type_no_commas", "45 Kingsway Burnaby",
        ("", "", "", "", "", "", ""), review="yes")
    add("null_marker", "", ("", "", "", "", "", "", ""), kind="keep")
    add("null_marker", "n/a", ("", "", "", "", "", "", ""), kind="keep")
    rng.shuffle(rows)
    return rows


ADDRESS_TASK = """Task: split each address into parts. The table has the columns `id` and `address`; each address is one line of text.

Write `output.csv` with the columns `id`, `house_number`, `street`, `unit`, `city`, `region`, `postal_code`, `country` and `review`, one row for each input row, in any order:
- Copy each part exactly as it is written in the address, with the same spelling, abbreviations, punctuation inside the part and capital letters. Do not expand, correct or translate anything, and do not add a part that is not written, such as a country that is not named.
- `street` is the street name with its type and direction, for example `N Main St`. `unit` is an apartment, suite, unit, flat, floor or room with its number, for example `Apt 4B`, `Flat 3` or `#12`. `region` is the state, province or county. A post office box goes in `street`, for example `PO Box 123`, with an empty `house_number`.
- Leave a part empty when the address does not contain it. For an empty value or a null marker such as `n/a`, leave every part empty and set `review` to `no`.
- When you cannot tell with certainty which part some words belong to, or the value is not a postal address, set `review` to `yes`. Otherwise set `review` to `no`."""


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
)

HARD_NEGATIVE_ENTITY_PAIRS = (
    ("bluebird_denver", "bluebird_seattle", "same_name_other_location"),
    ("summit_dental", "summit_rental", "one_letter_name_difference_nearby_address"),
    ("harbor_light", "crestline", "shared_floor_mailbox_and_switchboard"),
)
AMBIGUOUS_ENTITY_PAIRS = (
    ("globex", "globex_logistics", "related_names_same_address_and_phone"),
    ("keystone", "keystone_lincoln", "same_company_name_phone_and_email_other_address"),
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


def known_wrong_addresses(rows):
    header = ("id",) + ADDRESS_PARTS + ("review",)
    # The copied input puts the whole line in `street` and flags nothing.
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
    every_pair = [(a, b, "same") for i, a in enumerate(ids) for b in ids[i + 1:]]
    every_pair = [tuple(sorted(p[:2], key=int)) + ("same",) for p in every_pair]
    over_merge = csv_text(header, sorted(every_pair, key=lambda p: (int(p[0]), int(p[1]))))
    return {"copied-input.csv": copied, "all-null.csv": all_null, "shuffled.csv": shuffled,
            "every-pair-same.csv": over_merge}


# ---------------------------------------------------------------------------
# Assembly


def build():
    """Return {relative path: text} for every population file."""
    rng = random.Random(SEED)
    files = {}
    families = {}

    phones = phone_rows(rng)
    rng.shuffle(phones)
    for number, row in enumerate(phones, start=1):
        row["id"] = str(number)
    families["phones"] = dict(
        task=PHONE_TASK, input_header=("id", "phone"),
        input_rows=[(r["id"], r["input"]) for r in phones],
        truth=dict(output_columns=["id", "phone", "review"], value_column="phone", rows=phones),
        known_wrong=known_wrong_value_family(("id", "phone", "review"), phones))

    emails = email_rows(rng)
    for number, row in enumerate(emails, start=1):
        row["id"] = str(number)
    families["emails"] = dict(
        task=EMAIL_TASK, input_header=("id", "email"),
        input_rows=[(r["id"], r["input"]) for r in emails],
        truth=dict(output_columns=["id", "email", "review"], value_column="email", rows=emails),
        known_wrong=known_wrong_value_family(("id", "email", "review"), emails))

    addresses = address_rows(rng)
    for number, row in enumerate(addresses, start=1):
        row["id"] = str(number)
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

    manifest = {"record_type": RECORD_TYPE, "seed": SEED, "families": {}}
    for name, family in families.items():
        prompt = step_prompt(family["task"])
        input_text = csv_text(family["input_header"], family["input_rows"])
        truth = dict(record_type="data_cleanup_truth/v1", family=name, **family["truth"])
        truth_text = json_text(truth)
        files[f"{name}/input.csv"] = input_text
        files[f"{name}/truth.json"] = truth_text
        files[f"{name}/prompt.txt"] = prompt
        for fixture, text in family["known_wrong"].items():
            files[f"{name}/known-wrong/{fixture}"] = text
        manifest["families"][name] = {
            "rows": len(family["input_rows"]),
            "input_sha256": sha256_text(input_text),
            "truth_sha256": sha256_text(truth_text),
            "prompt_sha256": sha256_text(prompt),
            "known_wrong_sha256": {fixture: sha256_text(text)
                                   for fixture, text in sorted(family["known_wrong"].items())},
        }
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
