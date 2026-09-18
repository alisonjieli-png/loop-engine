"""Address component extraction with declared patterns and optional parser adapters.

The remaining member of the detection and correction family splits one
address line into house number, street, unit, city, region, postal code,
and country. The standard library parser works from declared data: unit
keywords, postal code patterns per country, and region codes it can only
recognize by shape. Every extraction names the components it found, the
reasons for what it could not place, and a confidence that is the weakest
named signal. Two optional parsers, usaddress and libpostal, enter as
adapters whose label maps are data; when the package is not installed the
result says so instead of guessing. The module grants no authority and
never rewrites the address it was given.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

COMPONENTS = ("house_number", "street", "unit", "city", "region", "postal_code", "country")
PARSERS = ("stdlib", "usaddress", "libpostal")
RECORD_TYPE = "address_components/v1"
#: Unit designators that mark the part after them as the unit; data, not branches.
UNIT_KEYWORDS = ("apt", "apartment", "suite", "ste", "unit", "floor", "fl", "room", "rm", "#")
#: Postal code shapes by country, tried in order; the country is a label, not a claim.
POSTAL_PATTERNS = (
    ("US", r"\d{5}(?:-\d{4})?"),
    ("CA", r"[A-Za-z]\d[A-Za-z] ?\d[A-Za-z]\d"),
    ("GB", r"[A-Za-z]{1,2}\d[A-Za-z\d]? ?\d[A-Za-z]{2}"),
)
#: usaddress and libpostal labels mapped to components; a label absent here is kept as a remainder.
USADDRESS_LABELS = (
    ("AddressNumber", "house_number"), ("StreetNamePreDirectional", "street"),
    ("StreetName", "street"), ("StreetNamePostType", "street"), ("StreetNamePostDirectional", "street"),
    ("OccupancyType", "unit"), ("OccupancyIdentifier", "unit"), ("PlaceName", "city"),
    ("StateName", "region"), ("ZipCode", "postal_code"), ("CountryName", "country"),
)
LIBPOSTAL_LABELS = (
    ("house_number", "house_number"), ("road", "street"), ("unit", "unit"), ("level", "unit"),
    ("city", "city"), ("state", "region"), ("postcode", "postal_code"), ("country", "country"),
)
HOUSE_NUMBER_CONFIDENCE = 0.95
STREET_CONFIDENCE = 0.9
UNIT_CONFIDENCE = 0.9
POSTAL_CONFIDENCE = 0.95
PLACE_CONFIDENCE = 0.8
AMBIGUOUS_PLACE_CONFIDENCE = 0.7
MISSING_STREET_CONFIDENCE = 0.4
_HOUSE_NUMBER = re.compile(r"^(?P<number>\d+[A-Za-z]?)\s+(?P<rest>.+)$")
_REGION_CODE = re.compile(r"^[A-Za-z]{2}$")


class AddressComponentsError(ValueError):
    """A parser name or adapter result is invalid."""


@dataclass(frozen=True)
class AddressComponents:
    """The components found in one address line, with reasons and a confidence."""

    parser: str
    components: dict
    remainder: str
    reasons: tuple[str, ...]
    confidence: float
    available: bool = True

    def to_dict(self) -> dict:
        return {"record_type": RECORD_TYPE, "parser": self.parser,
                "components": dict(self.components), "remainder": self.remainder,
                "reasons": list(self.reasons), "confidence": self.confidence,
                "available": self.available}

    def key(self) -> str:
        """A comparison key for duplicate detection: the components in order, casefolded."""
        return " ".join(str(self.components.get(name, "")).casefold().strip()
                        for name in COMPONENTS if self.components.get(name))


def _split_unit(text: str) -> tuple[str, str, list]:
    tokens = text.split()
    for index, token in enumerate(tokens):
        lowered = token.lower().rstrip(".")
        if lowered in UNIT_KEYWORDS and index + 1 < len(tokens):
            return " ".join(tokens[:index]), " ".join(tokens[index:]), [f"unit_keyword:{lowered}"]
        if token.startswith("#") and len(token) > 1:
            return " ".join(tokens[:index]), " ".join(tokens[index:]), ["unit_keyword:#"]
    return text, "", []


def _postal(text: str) -> tuple[str, str, str]:
    """The postal code found in a part, its country label, and the part without it."""
    for country, pattern in POSTAL_PATTERNS:
        match = re.search(rf"(?<![\w-])({pattern})(?![\w-])", text)
        if match:
            rest = (text[:match.start()] + " " + text[match.end():]).strip(" ,")
            return match.group(1).upper(), country, rest
    return "", "", text


def extract_stdlib(text: str) -> AddressComponents:
    """Components from declared patterns; nothing is guessed beyond them."""
    components, reasons, factors = {}, [], []
    parts = [part.strip() for part in str(text).replace("\n", ",").split(",") if part.strip()]
    if not parts:
        return AddressComponents(PARSERS[0], {}, "", ("empty_address",), 0.0)
    first = parts[0]
    match = _HOUSE_NUMBER.match(first)
    if match:
        components["house_number"] = match.group("number")
        factors.append(HOUSE_NUMBER_CONFIDENCE)
        street_text = match.group("rest")
    else:
        reasons.append("house_number_not_found")
        street_text = first
    street, unit, unit_reasons = _split_unit(street_text)
    if street:
        components["street"] = street
        factors.append(STREET_CONFIDENCE if match else MISSING_STREET_CONFIDENCE)
    else:
        reasons.append("street_not_found")
        factors.append(MISSING_STREET_CONFIDENCE)
    if unit:
        components["unit"] = unit
        factors.append(UNIT_CONFIDENCE)
        reasons.extend(unit_reasons)
    # The postal code is found first, in any later part, so a city placed
    # before it is not called ambiguous when the line does carry a code.
    rests = []
    for part in parts[1:]:
        postal, country, rest = _postal(part)
        if postal and "postal_code" not in components:
            components["postal_code"] = postal
            factors.append(POSTAL_CONFIDENCE)
            reasons.append(f"postal_pattern:{country}")
            rests.append(rest)
        else:
            rests.append(part)
    remainder = []
    for rest in rests:
        tokens = rest.split()
        if not tokens:
            continue
        if "region" not in components and len(tokens) == 1 and _REGION_CODE.match(tokens[0]):
            components["region"] = tokens[0].upper()
            factors.append(PLACE_CONFIDENCE)
        elif "city" not in components:
            if len(tokens) > 1 and _REGION_CODE.match(tokens[-1]) and "region" not in components:
                components["city"] = " ".join(tokens[:-1])
                components["region"] = tokens[-1].upper()
                factors.append(PLACE_CONFIDENCE)
            else:
                components["city"] = rest
                factors.append(PLACE_CONFIDENCE if "postal_code" in components else AMBIGUOUS_PLACE_CONFIDENCE)
                if "postal_code" not in components:
                    reasons.append("city_or_region_ambiguous")
        elif "country" not in components and len(tokens) <= 3:
            components["country"] = rest
            factors.append(PLACE_CONFIDENCE)
            reasons.append("country_from_position")
        else:
            remainder.append(rest)
    confidence = round(min(factors), 3) if factors else 0.0
    return AddressComponents(PARSERS[0], components, ", ".join(remainder), tuple(reasons), confidence)


def map_labels(labelled, label_map) -> tuple[dict, str]:
    """Components from (text, label) pairs an external parser returned, plus the unmapped remainder."""
    mapping = dict(label_map)
    components, remainder = {}, []
    for value, label in labelled:
        name = mapping.get(label)
        if name is None:
            remainder.append(str(value))
            continue
        components[name] = (components[name] + " " + str(value)).strip() if name in components else str(value)
    return components, " ".join(remainder)


def _adapter_result(parser: str, labelled, label_map) -> AddressComponents:
    components, remainder = map_labels(labelled, label_map)
    reasons = tuple(f"{parser}_label" for _ in ()) + (("remainder_unmapped",) if remainder else ())
    return AddressComponents(parser, components, remainder, reasons,
                             POSTAL_CONFIDENCE if components else 0.0)


def extract_usaddress(text: str) -> AddressComponents:
    """The usaddress adapter; reports unavailability instead of guessing when not installed."""
    try:
        import usaddress  # type: ignore
    except ImportError:
        return AddressComponents(PARSERS[1], {}, str(text), ("optional_adapter_unavailable:usaddress",),
                                 0.0, available=False)
    return _adapter_result(PARSERS[1], usaddress.parse(str(text)), USADDRESS_LABELS)


def extract_libpostal(text: str) -> AddressComponents:
    """The libpostal adapter through the postal package; unavailable when not installed."""
    try:
        from postal import parser  # type: ignore
    except ImportError:
        return AddressComponents(PARSERS[2], {}, str(text), ("optional_adapter_unavailable:postal",),
                                 0.0, available=False)
    return _adapter_result(PARSERS[2], parser.parse_address(str(text)), LIBPOSTAL_LABELS)


_EXTRACTORS = {PARSERS[0]: extract_stdlib, PARSERS[1]: extract_usaddress, PARSERS[2]: extract_libpostal}


def extract_components(text: str, *, parser: str = PARSERS[0]) -> AddressComponents:
    """Components from the named parser; an unknown parser is refused by name."""
    if parser not in _EXTRACTORS:
        raise AddressComponentsError(f"parser must be one of {PARSERS}")
    return _EXTRACTORS[parser](text)


def self_test() -> dict:
    """Declared patterns, ambiguity, adapter label maps, and honest unavailability."""
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    full = extract_components("12 N Main St Apt 4B, Springfield, IL 62704, USA")
    check("a_full_line_splits_into_every_component_with_a_weakest_signal_confidence",
          full.components == {"house_number": "12", "street": "N Main St", "unit": "Apt 4B",
                              "city": "Springfield", "postal_code": "62704", "region": "IL",
                              "country": "USA"}
          and full.confidence == PLACE_CONFIDENCE and "unit_keyword:apt" in full.reasons
          and "postal_pattern:US" in full.reasons and full.remainder == ""
          and full.to_dict()["record_type"] == RECORD_TYPE, str(full.to_dict()))
    canada = extract_components("77 Pine Road, Toronto ON M5V 2T6")
    britain = extract_components("10 Downing Street, London SW1A 2AA")
    check("canadian_and_british_postal_shapes_are_recognized_from_declared_patterns",
          canada.components.get("postal_code") == "M5V 2T6" and "postal_pattern:CA" in canada.reasons
          and canada.components.get("city") == "Toronto" and canada.components.get("region") == "ON"
          and "country" not in canada.components
          and britain.components.get("postal_code") == "SW1A 2AA" and "postal_pattern:GB" in britain.reasons
          and britain.components.get("city") == "London", str(canada.components) + str(britain.components))
    vague = extract_components("Main Street, Springfield")
    check("a_line_without_a_house_number_or_postal_code_says_what_it_could_not_place",
          "house_number" not in vague.components and vague.components.get("street") == "Main Street"
          and vague.components.get("city") == "Springfield"
          and "house_number_not_found" in vague.reasons and "city_or_region_ambiguous" in vague.reasons
          and vague.confidence == MISSING_STREET_CONFIDENCE
          and extract_components("").reasons == ("empty_address",))
    mapped, remainder = map_labels(
        (("12", "AddressNumber"), ("Main", "StreetName"), ("St", "StreetNamePostType"),
         ("Springfield", "PlaceName"), ("IL", "StateName"), ("62704", "ZipCode"), ("c/o", "Recipient")),
        USADDRESS_LABELS)
    check("an_external_parser_label_map_is_data_and_keeps_unmapped_labels_as_a_remainder",
          mapped == {"house_number": "12", "street": "Main St", "city": "Springfield",
                     "region": "IL", "postal_code": "62704"} and remainder == "c/o"
          and dict(LIBPOSTAL_LABELS)["postcode"] == "postal_code")
    adapter = extract_components("12 Main St", parser=PARSERS[1])
    check("an_optional_adapter_that_is_not_installed_reports_unavailability_instead_of_guessing",
          (adapter.available is False and adapter.components == {}
           and "optional_adapter_unavailable:usaddress" in adapter.reasons and adapter.confidence == 0.0)
          or (adapter.available is True and adapter.parser == PARSERS[1]), str(adapter.to_dict()))
    refused = False
    try:
        extract_components("12 Main St", parser="guess")
    except AddressComponentsError:
        refused = True
    check("an_unknown_parser_is_refused_by_name_and_keys_compare_components_in_order",
          refused and full.key() == "12 n main st apt 4b springfield il 62704 usa"
          and extract_components("12 N. Main St., Springfield, IL 62704").key().startswith("12 n. main st."))
    passed = sum(item["passed"] for item in tests)
    return {"record_type": "address_components_test/v1", "tests": tests, "passed": passed,
            "total": len(tests), "all_passed": passed == len(tests)}
