---
name: fetch-reference-rates
description: Reads the euro foreign exchange reference rates that the European Central Bank publishes each working day, at the moment of the call, and returns the reference date and the rates you ask for against the base currency you choose. A rate between two currencies other than the euro is computed through the euro and rounded to 6 decimal places. The result says whether the rates are stale and carries the attribution that the bank asks for. Use it when a task needs a current reference exchange rate for reporting, estimates or data work. Use it instead of a remembered or stored rate, because the rates change every working day. The bank publishes these rates for information purposes only, so do not use them to price a transaction.
license: MIT
metadata:
  asset_id: "fetch_reference_rates"
  asset_version: "1.0.0"
  kind: "tool"
  source_host: "www.ecb.europa.eu"
  source_format: "eurofxref-daily.xml"
  observed_on: "2026-09-27"
---

# Fetch reference rates

## What it returns

The tool reads the daily file of the European Central Bank when you call it,
`https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml`. That file
holds, for one reference date, how many units of each currency one euro buys.
The tool returns:

- the reference date of the rates;
- the rates that you ask for, as units of each currency for one unit of your
  base currency;
- stale: true when the reference date is more than 4 calendar days before
  today (UTC), and false otherwise;
- the attribution text of the source;
- the address it read and the time it read it.

It never returns a stored rate.

How the rates are computed:

- With the base EUR, each rate is the published number.
- With another base, the rate of a currency S for the base B is the published
  rate of S divided by the published rate of B. For example, with USD 1.1403
  and JPY 179.70 for one euro, one US dollar is 179.70 / 1.1403 = 157.590108
  yen.
- The division uses decimal arithmetic and is rounded half up to 6 decimal
  places.

## How to call it

Give one JSON object as the only argument. Run the command from the package
folder.

```text
python3 scripts/fetch_reference_rates.py '{"base": "USD", "symbols": ["EUR", "JPY", "GBP"]}'
```

To read the JSON object from standard input instead, give `-` as the only
argument.

| Field | What to give |
|---|---|
| base | A three-letter currency code in capital letters, for example EUR or USD. Required. |
| symbols | A list of 1 to 40 currency codes, without repeats. Leave it out to get every published currency except the base. |

The request contract is [contracts/input.schema.json](contracts/input.schema.json).

Exit codes:

- 0: success. The tool prints the result.
- 2: the request is invalid. When the request is badly formed, the tool sends
  nothing. When a currency is well formed but the bank published no rate for
  it on the reference date, the tool ends after the read with the code
  currency_not_published.
- 3: the file could not be read, or it answered in an unexpected shape.

On exit code 2 or 3 the tool prints only an error record, never a partial
result:

```json
{"record_type": "knowledge_radar_tool_error/v1", "code": "currency_not_published", "message": "the European Central Bank published no rate for BGN on 2026-09-25"}
```

Error codes: invalid_request, currency_not_published, source_unreachable,
source_http_error, source_too_large, redirect_refused,
unexpected_source_shape and internal_error.

## Output fields

The result contract is [contracts/output.schema.json](contracts/output.schema.json).

| Field | Meaning |
|---|---|
| record_type | Always knowledge_radar_fetch_reference_rates_result/v1. |
| base | The base currency that you asked for. |
| reference_date | The day of the rates, as the bank gives it, written YYYY-MM-DD. |
| rates | An object from currency code to the units of that currency for one unit of the base. |
| stale | true when reference_date is more than 4 calendar days before the UTC date of observed_at. |
| attribution | Source: European Central Bank, euro foreign exchange reference rates. The reference rates are published for information purposes only. Using the rates for transaction purposes is strongly discouraged. |
| source | https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml |
| observed_at | The UTC time of the read. |

Show the attribution text wherever you show the rates.

## Effects

- Network: one HTTPS GET to www.ecb.europa.eu, and to no other host. The tool
  follows a redirect only when it stays on the same host and on https. It
  sends no credentials and no cookies.
- Files: Python reads the script. The test reads the fixtures in the
  verification folder. The tool reads no other file.
- Process: each call starts one Python process.
- Writes: nothing. The tool writes no file, no cache and no log.

## Source, terms and attribution

- Source: the daily euro foreign exchange reference rates file of the European
  Central Bank, https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml.
- Terms and attribution: the page of the bank on these rates,
  https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html,
  read on 2026-09-27, says: "The reference rates are published for
  information purposes only. Using the rates for transaction purposes is
  strongly discouraged." The same page says that the rates are usually updated
  at around 16:00 CET every working day, except on TARGET closing days. The
  tool puts the first two sentences into the attribution field of every
  result.
- Observation on 2026-09-27: at 15:10:17 UTC, a Sunday, the file answered
  with HTTP status 200, the reference date 2026-09-25 (a Friday) and 29
  currencies. There was no BGN rate, so a request with BGN ends with the code
  currency_not_published.
- Live check of the finished tool: on 2026-09-27 at 15:33:44 UTC,
  `python3 scripts/fetch_reference_rates.py '{"base": "USD", "symbols": ["EUR", "JPY", "GBP"]}'`
  exited with 0 and reported the reference date 2026-09-25, stale false, and
  the rates EUR 0.876962, JPY 157.590108 and GBP 0.754582.

## Limits

- Only the currencies that the bank publishes on the reference date: 29 on
  2026-09-27. Other currencies end with the code currency_not_published.
- One reference date only: the newest one. The tool does not read past rates.
- There are no new rates on weekends and on TARGET closing days, so a
  reference date one to four days old is normal. The stale flag turns true
  only after more than 4 calendar days.
- A rate is rounded to 6 decimal places, so a very small rate keeps few
  significant digits. For example, with the base IDR the rate for EUR is
  0.000049, which JSON may print as 4.9e-05.
- The rates are for information only. Do not use them to price, settle or
  book a transaction.
- An answer larger than 2 MB is refused. The tool waits at most 20 seconds.
- The tool keeps no cache and sends one request for each call.

## How to check it

From the package folder, run:

```text
python3 scripts/test_fetch_reference_rates.py
```

The test needs no network. It serves the recorded and hand-made answers that
[verification/cases.json](verification/cases.json) names to the tool, in
place of the network. It prints one line such as
`{"passed": 26, "failed": 0, "known_wrong_rejected": 2}` and exits 0 only when
every case passes. The expected cross rates were computed separately with
exact fractions. The cases include deliberately wrong expectations that the
test must reject (a cross rate computed the wrong way round, and weekend rates
marked stale), a value exactly half way between two results that must be
rounded up, malformed answers and a network timeout that must end with exit
code 3, and invalid requests that must be refused before any request is sent.
