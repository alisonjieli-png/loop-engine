# Split an address line into components

Split one address line into house number, street, unit, city, region, postal code and country from declared patterns. Report what could not be placed. Never rewrite the address.

## When to use it

Use it before comparing addresses, before filling separate address columns, and before sending addresses to a service that needs components.

## Steps

1. Split the line into parts at commas and line breaks. An empty line gives no components, the reason `empty_address` and confidence 0.
2. In the first part, read a leading number with an optional letter as the house number (confidence 0.95). The rest is the street (0.9). Without a house number, record `house_number_not_found` and give the street confidence 0.4.
3. Inside the street, a unit keyword starts the unit (0.9). The keywords are data: `apt`, `apartment`, `suite`, `ste`, `unit`, `floor`, `fl`, `room`, `rm` and `#`.
4. Look for a postal code in every later part, using declared patterns for the United States, Canada and Great Britain (0.95). The country of the pattern is recorded as a label in the reason. It is not placed in the country component.
5. From what remains, read a single two letter token as the region, the next part as the city, and a city followed by a two letter token as city and region (0.8). A city without a postal code gets 0.7 and the reason `city_or_region_ambiguous`.
6. Read a later short part as the country (0.8, reason `country_from_position`). Keep anything else as a remainder.
7. The confidence of the whole result is the lowest component confidence.
8. Treat an external parser as an optional adapter. Map its labels to the components with a table that is data, and keep unmapped labels in the remainder. When the package is not installed, return no components, confidence 0 and an unavailable result.

## Checks

- `12 N Main St Apt 4B, Springfield, IL 62704, USA` gives all seven components at confidence 0.8.
- `77 Pine Road, Toronto ON M5V 2T6` gives city `Toronto`, region `ON` and postal code `M5V 2T6`, without a country.
- `Main Street, Springfield` gives street and city at 0.4, with `house_number_not_found` and `city_or_region_ambiguous`.
- An unknown parser name is refused.

## Known-wrong example

The optional parser is not installed. A wrapper falls back to its own patterns and still reports the name of the external parser. The reader trusts a quality that was never delivered. The correct result names the adapter, says that it is unavailable and returns no components.

## What to record

- The parser that was used and whether it was available.
- The components, the remainder, the reasons and the confidence for each line.

## Source

- `src/loop_engine/code_nodes/address_components.py`: `extract_components`, `extract_stdlib`, `map_labels` and the adapters for the `usaddress` and `postal` packages.

Licence: MIT. Compiled from revision f29bddc. The standard parser uses only the Python standard library. The two external packages are optional.
