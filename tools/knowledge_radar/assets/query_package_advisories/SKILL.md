---
name: query-package-advisories
description: Asks the OSV.dev vulnerability database, at the moment of the call, which published advisories affect one exact version of one package in PyPI, npm, Go, crates.io, Maven, NuGet, RubyGems, Packagist, Hex or Pub. Returns each advisory identifier with its aliases, its publication and change dates, its severity entries as OSV gives them, the versions named as fixed for that package, and a link to the advisory page. Use it before you add, keep or upgrade a dependency, and when someone asks whether a version is affected. Use it instead of a remembered or stored advisory list, because advisories are added and changed every day.
license: MIT
metadata:
  asset_id: "query_package_advisories"
  asset_version: "1.0.0"
  kind: "tool"
  source_host: "api.osv.dev"
  source_format: "OSV API v1 query"
  observed_on: "2026-09-27"
---

# Query package advisories

## What it returns

The tool sends one query to the OSV.dev API when you call it:
`POST https://api.osv.dev/v1/query` with the package name, its ecosystem and
one exact version. For each advisory that OSV lists for that version it
returns:

- the OSV identifier and its aliases, for example a CVE identifier;
- the publication date and the date of the last change;
- the severity entries as OSV gives them, for example a CVSS vector;
- the versions that the advisory names as fixed for this package;
- the address of the advisory page on osv.dev.

It also returns the number of advisories, the address it read and the time it
read it. It does not return the free-text summary or details of an advisory.
Open the advisory page to read them. When OSV leaves a value out, the value is
null. The tool does not guess it.

## How to call it

Give one JSON object as the only argument. Run the command from the package
folder.

```text
python3 scripts/query_package_advisories.py '{"ecosystem": "PyPI", "name": "jinja2", "version": "2.4.1"}'
```

To read the JSON object from standard input instead, give `-` as the only
argument.

| Field | What to give |
|---|---|
| ecosystem | One of PyPI, npm, Go, crates.io, Maven, NuGet, RubyGems, Packagist, Hex or Pub, written exactly like this. |
| name | The package name as the ecosystem writes it, for example jinja2, @types/node, golang.org/x/net, serde_json, org.slf4j:slf4j-api, Newtonsoft.Json, rails, symfony/http-kernel, phoenix or http. |
| version | One exact version, for example 2.4.1, 1.0.0-beta.1 or v1.2.3. A range such as >=4.0.0 is refused. |

The request contract is [contracts/input.schema.json](contracts/input.schema.json).

Exit codes:

- 0: success. The tool prints the result.
- 2: the request is invalid, for example an ecosystem that is not on the
  list. The tool sends nothing.
- 3: OSV could not be read, or it answered in an unexpected shape.

On exit code 2 or 3 the tool prints only an error record, never a partial
result:

```json
{"record_type": "knowledge_radar_tool_error/v1", "code": "unsupported_ecosystem", "message": "ecosystem must be one of: PyPI, npm, Go, crates.io, Maven, NuGet, RubyGems, Packagist, Hex, Pub"}
```

Error codes: invalid_request, unsupported_ecosystem, source_unreachable,
source_http_error, source_too_large, redirect_refused,
unexpected_source_shape, too_many_pages and internal_error.

## Output fields

The result contract is [contracts/output.schema.json](contracts/output.schema.json).

| Field | Meaning |
|---|---|
| record_type | Always knowledge_radar_query_package_advisories_result/v1. |
| ecosystem, name, version | The package version that you asked about. |
| count | The number of entries in vulnerabilities. |
| vulnerabilities | One entry for each advisory identifier, in the order OSV returned them. |
| id | The OSV identifier, for example GHSA-462w-v97r-4m45 or PYSEC-2014-82. |
| aliases | Other identifiers of the same problem, or null when OSV gives none. |
| published | The publication time as OSV gives it, or null. |
| modified | The time of the last change as OSV gives it, or null. |
| severity | A list of entries with type (for example CVSS_V3) and score (the score string as given), or null when OSV gives none. The tool does not compute a number from a vector. |
| fixed_versions | The versions that ECOSYSTEM and SEMVER ranges name as fixed for the package you asked about, each once, in source order. Commit identifiers of GIT ranges are left out. The list is empty when OSV names no fixed version. |
| details_address | https://osv.dev/vulnerability/ followed by the identifier. |
| source | https://api.osv.dev/v1/query |
| observed_at | The UTC time of the read. |

One problem can appear twice, under two identifiers. For example, in the
answer for jinja2 2.4.1 on 2026-09-27, GHSA-fqh9-2qgg-h84h and PYSEC-2014-82
describe the same problem, and their aliases link them. The tool keeps both,
because two records can name different fixed versions: that day the first
named 2.7.2 and the second named 2.7.3.

## Effects

- Network: HTTPS POST requests to api.osv.dev only. One request, and one more
  for each further page that OSV announces, at most five in total. The tool
  follows a redirect only when it stays on the same host and on https. It
  sends no credentials and no cookies.
- Files: Python reads the script. The test reads the fixtures in the
  verification folder. The tool reads no other file.
- Process: each call starts one Python process.
- Writes: nothing. The tool writes no file, no cache and no log.

## Source, terms and attribution

- Source: the OSV.dev API query endpoint, https://api.osv.dev/v1/query.
  Advisory pages are at https://osv.dev/vulnerability/ followed by the
  identifier.
- Observation on 2026-09-27: a query for PyPI jinja2 2.4.1 at 15:10:15 UTC
  answered with HTTP status 200 and 18 advisories, 9 GHSA records and 9 PYSEC
  records. A query for a PyPI name that does not exist answered with exactly
  `{}` at 15:34:00 UTC.
- The OSV FAQ, https://google.github.io/osv.dev/faq/, read on 2026-09-27,
  says that the API has no rate limit at present, and that it has a response
  size limit of 32 MiB over HTTP/1.1.
- OSV.dev imports advisories from other databases. In the recorded answer,
  each record linked to its source, the GitHub Advisory Database or the Python
  Packaging Advisory Database. The tool returns identifiers, dates, severity
  strings and version numbers, not advisory text. If you copy advisory text,
  name OSV.dev and check the terms of the database that the advisory comes
  from.
- Live check of the finished tool: on 2026-09-27 at 15:33:41 UTC,
  `python3 scripts/query_package_advisories.py '{"ecosystem": "PyPI", "name": "jinja2", "version": "2.4.1"}'`
  exited with 0 and reported 18 advisories. The first three were
  GHSA-462w-v97r-4m45 (fixed 2.10.1), GHSA-8r7q-cvjq-x353 (fixed 2.7.2) and
  GHSA-cpwx-vrp4-4pq7 (fixed 3.1.6). At 15:33:43 UTC the same command for
  the name baltor-radar-no-such-package exited with 0 and a count of 0.

## Limits

- Ten ecosystems only. Linux distributions and other ecosystems are refused.
- One exact version for each call. The tool does not read lock files or
  version ranges.
- The answer is only as complete as the data of OSV at the time of the call.
  An empty list means that OSV lists no advisory for that version at
  observed_at. It does not prove that the version is safe.
- A misspelled package name also gives an empty list, because OSV has no
  advisory for a name that it does not know. Check the spelling when the list
  is empty.
- Severity is passed on as given. The tool does not compute a CVSS base score,
  and it does not return severity labels from database-specific fields.
- An answer larger than 2 MB is refused with the code source_too_large. A
  version with some hundreds of advisories can reach this size. The tool waits
  at most 20 seconds for each page.
- The tool reads at most five pages. When OSV announces more, the tool ends
  with the code too_many_pages and returns no partial list.
- The tool keeps no cache. Call it again only when you need a newer answer.

## How to check it

From the package folder, run:

```text
python3 scripts/test_query_package_advisories.py
```

The test needs no network. It serves the recorded and hand-made answers that
[verification/cases.json](verification/cases.json) names to the tool, in
place of the network. It prints one line such as
`{"passed": 24, "failed": 0, "known_wrong_rejected": 2}` and exits 0 only when
every case passes. The cases include deliberately wrong expectations that the
test must reject (a commit identifier reported as a fixed version, and two
alias records merged into one), malformed answers and a refused connection
that must end with exit code 3, and invalid requests that must be refused
before any request is sent.
