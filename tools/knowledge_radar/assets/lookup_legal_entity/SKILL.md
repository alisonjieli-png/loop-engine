---
name: lookup-legal-entity
description: Looks up legal entities in the public GLEIF LEI database at the moment of the call, either by Legal Entity Identifier (LEI) or by legal name. Before it sends anything, it checks an LEI locally, including its ISO 17442 check digits, and refuses a bad one. For each record it returns the legal name, jurisdiction, legal form code, entity status, registration status, registration and renewal dates, the managing issuer and the address of the record on search.gleif.org. Use it when a task needs to confirm that a company or fund exists, to find its LEI, or to check whether its registration is current. Use it instead of a remembered or stored record, because registrations lapse and change.
license: MIT
metadata:
  asset_id: "lookup_legal_entity"
  asset_version: "1.0.0"
  kind: "tool"
  source_host: "api.gleif.org"
  source_format: "GLEIF API v1 lei-records"
  data_licence: "CC0 1.0"
  observed_on: "2026-09-27"
---

# Look up a legal entity

## What it returns

The tool reads the GLEIF API when you call it, in one of two ways:

- by LEI: `https://api.gleif.org/api/v1/lei-records/<LEI>` returns one record;
- by legal name: `https://api.gleif.org/api/v1/lei-records?filter[entity.legalName]=<name>&page[size]=<n>`
  returns up to n records, with n from 1 to 10.

For each record it returns the LEI, the legal name, the jurisdiction, the
legal form code, the entity status, the registration status, the first
registration date, the date of the last update, the next renewal date, the
LEI of the managing issuer and the address of the record on
search.gleif.org. It also returns the number of records, the number of
matches that GLEIF reports for a name search, the publication time of the
GLEIF data set, the address it read and the time it read it. When GLEIF leaves
a value out, the value is null. The tool does not guess it.

An LEI that GLEIF does not hold gives a count of 0 and an empty list. That is
an answer, not a failure.

## How to call it

Give one JSON object as the only argument. Run the command from the package
folder.

```text
python3 scripts/lookup_legal_entity.py '{"lei": "506700GE1G29325QX363"}'
python3 scripts/lookup_legal_entity.py '{"name": "Global Legal Entity Identifier Foundation", "page_size": 3}'
```

To read the JSON object from standard input instead, give `-` as the only
argument.

| Field | What to give |
|---|---|
| lei | A Legal Entity Identifier: 20 characters, 18 capital letters or digits and then 2 check digits. Give either lei or name. |
| name | A legal name to search for, 1 to 200 characters. Give either lei or name. |
| page_size | Only with name: how many records to return, from 1 to 10. The default is 5. |

The request contract is [contracts/input.schema.json](contracts/input.schema.json).

How the LEI is checked before any request: it must have 20 characters, 18
capital letters or digits and then 2 digits. Then each letter becomes a
number (A is 10, B is 11, and so on to Z, which is 35), the digits are joined
into one large number, and that number divided by 97 must leave the
remainder 1 (ISO 17442, which uses ISO 7064 MOD 97-10). An LEI that fails is
refused with the code invalid_lei, and nothing is sent. The check catches most
typing errors, but not all of them. Measured on 2026-09-27 on three registered
LEIs, it caught 1,931 of 1,944 changes of a single character and 52 of 53
swaps of two neighbouring characters. An LEI that passes the check can still be
one that GLEIF does not hold.

Exit codes:

- 0: success. The tool prints the result.
- 2: the request is invalid, for example an LEI with a wrong check digit. The
  tool sends nothing.
- 3: GLEIF could not be read, or it answered in an unexpected shape.

On exit code 2 or 3 the tool prints only an error record, never a partial
result:

```json
{"record_type": "knowledge_radar_tool_error/v1", "code": "invalid_lei", "message": "lei fails the ISO 17442 check digits (mod 97)"}
```

Error codes: invalid_request, invalid_lei, source_unreachable,
source_http_error, source_too_large, redirect_refused,
unexpected_source_shape and internal_error.

## Output fields

The result contract is [contracts/output.schema.json](contracts/output.schema.json).

| Field | Meaning |
|---|---|
| record_type | Always knowledge_radar_lookup_legal_entity_result/v1. |
| query | The checked request: the LEI, or the name and the page size that the tool used. |
| count | The number of entries in records. |
| total_matches | For a name search, the number of matching records that GLEIF reports. It can be larger than count. null for an LEI lookup. |
| golden_copy_published_at | The publication time of the GLEIF data set that answered, as GLEIF gives it. |
| records | The records, in the order GLEIF returned them. |
| lei | The Legal Entity Identifier of the record. |
| legal_name | The legal name. |
| jurisdiction | The jurisdiction code, for example CH or US-DE. |
| legal_form_id | The entity legal form code (ISO 20275), for example 2JZ4. |
| entity_status | For example ACTIVE or INACTIVE. |
| registration_status | For example ISSUED, LAPSED or RETIRED. |
| initial_registration_date | The first registration time. |
| last_update_date | The time of the last update of the record. |
| next_renewal_date | The time by which the registration must be renewed. |
| managing_lou | The LEI of the issuing organisation (Local Operating Unit) that manages the record. |
| record_address | https://search.gleif.org/#/record/ followed by the LEI. |
| source | The https address that the tool read. |
| observed_at | The UTC time of the read. |

## Effects

- Network: one HTTPS GET to api.gleif.org, and to no other host. The tool
  follows a redirect only when it stays on the same host and on https. It
  sends no credentials and no cookies.
- Files: Python reads the script. The test reads the fixtures in the
  verification folder. The tool reads no other file.
- Process: each call starts one Python process.
- Writes: nothing. The tool writes no file, no cache and no log.

## Source, terms and attribution

- Source: the GLEIF API, https://api.gleif.org/api/v1/lei-records, run by the
  Global Legal Entity Identifier Foundation.
- Licence: the GLEIF page LEI Data Terms of Use,
  https://www.gleif.org/en/meta/lei-data-terms-of-use, read on 2026-09-27,
  says that the data available through the access service are provided under
  the CC0 licence (CC0 1.0 Universal). The same page adds conditions that
  protect the Global LEI System. Read that page before you use the data in
  bulk.
- Observation on 2026-09-27: at 15:10:21 UTC the lookup of
  506700GE1G29325QX363 answered with HTTP status 200 and one record. At
  15:10:24 UTC the name search for Global Legal Entity Identifier Foundation
  with page size 3 answered with two records: the foundation and its
  Singapore branch. At 15:10:26 UTC the lookup of ZZZZ00RADARTEST00016, an
  identifier with valid check digits that is not registered, answered with
  HTTP status 404 and a JSON errors list.
- Live check of the finished tool: on 2026-09-27 at 15:33:47 UTC,
  `python3 scripts/lookup_legal_entity.py '{"lei": "506700GE1G29325QX363"}'`
  exited with 0 and reported one record: Global Legal Entity Identifier
  Foundation, jurisdiction CH, entity status ACTIVE, registration status
  ISSUED, next renewal 2027-03-15T00:00:00Z.

## Limits

- The name search uses the matching rules of GLEIF. The result can hold other
  names that contain the words you gave, such as a branch. Check the LEI and
  the legal name of each record before you use it.
- A name search returns at most 10 records and reads one page only. Use
  total_matches to see whether GLEIF holds more matches.
- The tool returns the fields listed above only. It does not return
  addresses, other names, ownership relationships with parent entities or the history of a
  record. Open record_address for those.
- GLEIF publishes its data set in regular runs. golden_copy_published_at tells
  you the time of the data set that answered.
- An answer larger than 2 MB is refused. The tool waits at most 20 seconds.
- The tool keeps no cache and sends one request for each call.

## How to check it

From the package folder, run:

```text
python3 scripts/test_lookup_legal_entity.py
```

The test needs no network. It serves the recorded and hand-made answers that
[verification/cases.json](verification/cases.json) names to the tool, in
place of the network. It prints one line such as
`{"passed": 29, "failed": 0, "known_wrong_rejected": 2}` and exits 0 only when
every case passes. The cases include LEIs with a wrong or swapped check digit
that must be refused before any request, deliberately wrong expectations that
the test must reject, and malformed answers and a refused connection that
must end with exit code 3.
